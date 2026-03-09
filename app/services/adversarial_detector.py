"""
app/services/adversarial_detector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global Ontology Engine — Adversarial Input Detection Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This module guards the Knowledge Graph against two classes of adversarial
data manipulation:

  1. NARRATIVE FLOODING  (`detect_narrative_anomaly`)
     Detects coordinated inauthentic behaviour: a burst of identical
     relationship claims from low-credibility sources within a short
     time window — the hallmark of a disinformation injection campaign.

  2. CROSS-LINGUAL NARRATIVE CONFLICT  (`check_cross_lingual_conflict`)
     Detects when two edges describing the *same* geopolitical event in
     different languages carry contradictory relationship types or
     opposing sentiment polarities — a signal of state-sponsored
     translation manipulation or genuine intelligence disagreement.

Design approach:
  • Both functions operate purely on in-memory `GraphEdge` objects so they
    can be used in a streaming ingestion pipeline without a DB round-trip.
  • LLM sentiment analysis is mocked via `_mock_llm_sentiment_analysis()`.
    The function signature and return contract are production-ready for
    drop-in replacement with a real LangChain / OpenAI call.
  • All anomalies are returned as structured `AnomalyReport` / `ConflictReport`
    dataclasses so the HITL API and Nexus dashboard can consume them directly.

Module relationships:
  ┌───────────────────────────────────────────────────────────┐
  │  adversarial_detector.py  is called by:                   │
  │    • The ingestion pipeline (post NLP extraction)         │
  │    • api/hitl_routes.py  (conflict summaries)             │
  │    • api/dashboard_routes.py  (anomaly visualisation)     │
  └───────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.models.ontology_models import (
    EdgeStatus,
    GraphEdge,
    RelationshipType,
    SourceType,
)

# ─────────────────────────────────────────────────────────────────────────────
# Module logger
# ─────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# ─────────────────────────────────────────────────────────────────────────────
# Tuneable thresholds (centralised for easy operator adjustment)
# ─────────────────────────────────────────────────────────────────────────────

# Maximum number of identical low-credibility claims allowed per time window
# before the batch is flagged as a flooding attack.
FLOODING_COUNT_THRESHOLD: int = 50

# Source credibility ceiling below which a source is considered "low credibility".
LOW_CREDIBILITY_CEILING: float = 0.40

# Relationship types that are considered DIRECT OPPOSITES of each other.
# Used by the cross-lingual conflict checker.
_OPPOSING_RELATIONSHIPS: Dict[RelationshipType, RelationshipType] = {
    RelationshipType.ALLIED_WITH:     RelationshipType.CONFLICT_WITH,
    RelationshipType.CONFLICT_WITH:   RelationshipType.ALLIED_WITH,
    RelationshipType.SANCTIONED_BY:   RelationshipType.TRADES_WITH,
    RelationshipType.TRADES_WITH:     RelationshipType.SANCTIONED_BY,
    RelationshipType.CONTROLS:        RelationshipType.HAS_CLAIM_OVER,
    RelationshipType.HAS_CLAIM_OVER:  RelationshipType.CONTROLS,
}

# Sentiment values that are considered opposed (used for cross-lingual check).
_OPPOSING_SENTIMENTS: Dict[str, str] = {
    "POSITIVE":  "NEGATIVE",
    "NEGATIVE":  "POSITIVE",
    "HOSTILE":   "COOPERATIVE",
    "COOPERATIVE": "HOSTILE",
}


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclasses
# ─────────────────────────────────────────────────────────────────────────────

class AnomalySeverity(str, Enum):
    """Severity levels for anomaly reports."""
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AnomalyReport:
    """
    Structured result returned by `detect_narrative_anomaly()`.

    Fields:
        is_anomalous        – True if a flooding threshold was exceeded.
        severity            – Operator-actionable severity level.
        flagged_cluster_key – Canonical hash of the repeated relationship claim.
        duplicate_count     – Number of duplicate low-credibility claims found.
        time_window_hours   – The window that was evaluated (from caller).
        offending_source_urls – URLs of the low-credibility sources.
        offending_edge_ids  – IDs of the edges that formed the spike.
        detected_at         – UTC timestamp of detection.
        message             – Human-readable description for the dashboard.
    """
    is_anomalous:          bool
    severity:              AnomalySeverity
    flagged_cluster_key:   Optional[str]
    duplicate_count:       int
    time_window_hours:     float
    offending_source_urls: List[str] = field(default_factory=list)
    offending_edge_ids:    List[str] = field(default_factory=list)
    detected_at:           datetime  = field(default_factory=lambda: datetime.now(timezone.utc))
    message:               str       = ""


@dataclass
class ConflictReport:
    """
    Structured result returned by `check_cross_lingual_conflict()`.

    Fields:
        has_conflict            – True if the two edges contradict each other.
        conflict_type           – "RELATIONSHIP_CONTRADICTION", "SENTIMENT_OPPOSITION",
                                  or "BOTH".
        edge_english_id         – ID of the English-language edge.
        edge_foreign_id         – ID of the foreign-language edge.
        english_relationship    – Relationship type on the English edge.
        foreign_relationship    – Relationship type on the foreign edge.
        english_sentiment       – Mock-derived sentiment of the English text.
        foreign_sentiment       – Mock-derived sentiment of the foreign text.
        language_pair           – e.g., "en vs zh".
        resolution_suggestion   – Automated recommendation for the analyst.
        detected_at             – UTC timestamp of detection.
    """
    has_conflict:            bool
    conflict_type:           Optional[str]
    edge_english_id:         str
    edge_foreign_id:         str
    english_relationship:    RelationshipType
    foreign_relationship:    RelationshipType
    english_sentiment:       str
    foreign_sentiment:       str
    language_pair:           str
    resolution_suggestion:   str
    detected_at:             datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────────────────────────────────────
# LLM mock stub
# ─────────────────────────────────────────────────────────────────────────────

def _mock_llm_sentiment_analysis(text: Optional[str], language_code: str) -> str:
    """
    Mock function simulating an LLM-based sentiment / stance extraction call.

    In production, replace this function body with a real LangChain chain:

        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        _llm = ChatOpenAI(model="gpt-4o", temperature=0)
        _prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a geopolitical analyst. Classify the stance "
                       "of the following text as: POSITIVE, NEGATIVE, NEUTRAL, "
                       "HOSTILE, or COOPERATIVE. Reply with ONLY the label."),
            ("human", "{text}"),
        ])
        chain = _prompt | _llm
        result = chain.invoke({"text": text or ""})
        return result.content.strip().upper()

    The mock uses simple keyword heuristics so the adversarial detector
    remains fully functional without an API key during development.

    Args:
        text:          Source text snippet to analyse. May be None.
        language_code: ISO 639-1 code of the text (e.g., "en", "zh", "ru").

    Returns:
        One of: "POSITIVE", "NEGATIVE", "NEUTRAL", "HOSTILE", "COOPERATIVE".
    """
    if not text:
        logger.debug(
            "_mock_llm_sentiment_analysis: no text provided (lang=%s), defaulting to NEUTRAL.",
            language_code,
        )
        return "NEUTRAL"

    text_lower = text.lower()

    # Hostile / negative signals
    if any(kw in text_lower for kw in [
        "attack", "invade", "sanction", "condemn", "conflict", "war",
        "aggression", "denounce", "hostile", "blockade", "threaten",
        "siege", "occupation", "bombardment",
    ]):
        return "HOSTILE"

    # Cooperative / positive signals
    if any(kw in text_lower for kw in [
        "cooperat", "agree", "treaty", "partner", "alliance", "aid",
        "support", "collaborat", "peace", "diplomatic", "mutual",
        "joint", "bilateral", "assist",
    ]):
        return "COOPERATIVE"

    # Negative signals (economic / political)
    if any(kw in text_lower for kw in [
        "reject", "expel", "protest", "withdraw", "ban", "tariff",
        "dispute", "accuse", "crisis",
    ]):
        return "NEGATIVE"

    # Positive signals
    if any(kw in text_lower for kw in [
        "celebrat", "welcom", "promot", "invest", "grow", "prosper",
        "progress", "success",
    ]):
        return "POSITIVE"

    logger.debug(
        "_mock_llm_sentiment_analysis: no keyword match (lang=%s), returning NEUTRAL.",
        language_code,
    )
    return "NEUTRAL"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _edge_cluster_key(edge: GraphEdge) -> str:
    """
    Produce a canonical, hashable key that identifies a *type* of relationship
    claim regardless of which source reported it.

    Two edges are "identical claims" if they assert the same relationship
    between the same pair of entities (direction matters).  The key ignores
    provenance details so we can count how many sources repeat the claim.

    Format: SHA-256 of "src_id|rel_type|tgt_id"
    Using a hash keeps keys fixed-length and avoids separator injection issues.
    """
    raw = f"{edge.source_node_id}|{edge.relationship_type.value}|{edge.target_node_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _is_low_credibility(edge: GraphEdge) -> bool:
    """
    Return True if the edge's source falls below the LOW_CREDIBILITY_CEILING.

    Source types that are structurally untrustworthy (SOCIAL_MEDIA, SYNTHETIC)
    are also considered low credibility regardless of their numeric score.
    """
    low_cred_types = {SourceType.SOCIAL_MEDIA, SourceType.SYNTHETIC}
    if edge.provenance.source_type in low_cred_types:
        return True
    return edge.provenance.source_credibility_score < LOW_CREDIBILITY_CEILING


def _within_time_window(edge: GraphEdge, cutoff: datetime) -> bool:
    """
    Return True if the edge's provenance timestamp falls at or after `cutoff`.
    """
    ts = edge.provenance.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts >= cutoff


def _severity_from_count(count: int) -> AnomalySeverity:
    """
    Map a duplicate count to an operator-actionable severity level.

    Thresholds (relative to FLOODING_COUNT_THRESHOLD = 50):
      50 – 99    → MEDIUM  (worth investigating)
      100 – 199  → HIGH    (likely coordinated)
      200+       → CRITICAL (active campaign)
    """
    if count < FLOODING_COUNT_THRESHOLD * 2:
        return AnomalySeverity.MEDIUM
    elif count < FLOODING_COUNT_THRESHOLD * 4:
        return AnomalySeverity.HIGH
    return AnomalySeverity.CRITICAL


# ─────────────────────────────────────────────────────────────────────────────
# Primary public API — Function 1
# ─────────────────────────────────────────────────────────────────────────────

def detect_narrative_anomaly(
    incoming_edges: List[GraphEdge],
    time_window_hours: float = 1.0,
) -> List[AnomalyReport]:
    """
    Detect coordinated narrative flooding: an abnormal spike of identical
    relationship claims from low-credibility sources within a time window.

    This is the primary defence against disinformation injection campaigns,
    where adversarial actors submit hundreds of near-identical claims to
    force a false relationship into the Knowledge Graph via sheer volume.

    Detection logic:
    ┌──────────────────────────────────────────────────────────────┐
    │ 1. Compute the time window cutoff = now − time_window_hours  │
    │ 2. Filter edges: only those WITHIN the window AND from       │
    │    low-credibility sources are candidates.                   │
    │ 3. Group candidate edges by their `_edge_cluster_key` —      │
    │    edges asserting the same (src → rel → tgt) triple.       │
    │ 4. Any cluster with count ≥ FLOODING_COUNT_THRESHOLD (50)    │
    │    triggers an AnomalyReport flagged as high severity.       │
    │ 5. All flagged edge statuses are set to LOW_CONFIDENCE so    │
    │    they enter the HITL review queue immediately.             │
    └──────────────────────────────────────────────────────────────┘

    Args:
        incoming_edges:    Batch of newly-ingested `GraphEdge` objects to scan.
        time_window_hours: Look-back window in hours (default: 1 hour).

    Returns:
        List of `AnomalyReport` objects — one per flagged cluster.
        Returns an empty list if no anomalies are detected.

    Side-effects:
        Mutates `edge.status` to `LOW_CONFIDENCE` on all edges belonging
        to a flagged cluster (so they surface in the HITL review queue).

    Example:
        >>> reports = detect_narrative_anomaly(ingested_edges, time_window_hours=1.0)
        >>> if reports:
        ...     for r in reports:
        ...         print(r.message)  # → "ALERT: 72 identical claims from low-cred sources..."
    """
    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc - timedelta(hours=time_window_hours)

    # ── Step 1: Filter to recent low-credibility candidates ───────────────
    candidates: List[GraphEdge] = [
        e for e in incoming_edges
        if _is_low_credibility(e) and _within_time_window(e, cutoff)
    ]

    logger.debug(
        "detect_narrative_anomaly: %d / %d edges are recent low-credibility candidates "
        "(window=%.1fh, cutoff=%s).",
        len(candidates), len(incoming_edges), time_window_hours, cutoff.isoformat(),
    )

    if not candidates:
        return []

    # ── Step 2: Cluster by identical (source_node, rel_type, target_node) ─
    # clusters maps cluster_key → list of edges asserting that triple
    clusters: Dict[str, List[GraphEdge]] = defaultdict(list)
    for edge in candidates:
        key = _edge_cluster_key(edge)
        clusters[key].append(edge)

    # ── Step 3: Evaluate each cluster against the flooding threshold ───────
    reports: List[AnomalyReport] = []

    for cluster_key, cluster_edges in clusters.items():
        count = len(cluster_edges)
        if count < FLOODING_COUNT_THRESHOLD:
            logger.debug(
                "detect_narrative_anomaly: cluster %s...%s has %d edges (below threshold %d). OK.",
                cluster_key[:8], cluster_key[-4:], count, FLOODING_COUNT_THRESHOLD,
            )
            continue

        # ── Threshold exceeded: flag this cluster ─────────────────────────
        severity = _severity_from_count(count)

        # Collect metadata for the report
        source_urls = list({e.provenance.source_url for e in cluster_edges})
        edge_ids    = [e.edge_id for e in cluster_edges]

        # Derive a readable label for the cluster from the first edge
        sample = cluster_edges[0]
        relation_label = (
            f"({sample.source_node_id[:8]}...) "
            f"--[{sample.relationship_type.value}]--> "
            f"({sample.target_node_id[:8]}...)"
        )

        message = (
            f"ALERT [{severity.value}]: {count} near-identical assertions of "
            f"'{relation_label}' detected from {len(source_urls)} low-credibility "
            f"source(s) within the last {time_window_hours:.1f}h. "
            f"Possible coordinated narrative injection campaign. "
            f"All {count} edges quarantined in LOW_CONFIDENCE queue."
        )

        # ── Side-effect: quarantine all edges in the cluster ──────────────
        for edge in cluster_edges:
            if edge.status not in (EdgeStatus.VERIFIED, EdgeStatus.REJECTED):
                edge.status = EdgeStatus.LOW_CONFIDENCE

        report = AnomalyReport(
            is_anomalous=True,
            severity=severity,
            flagged_cluster_key=cluster_key,
            duplicate_count=count,
            time_window_hours=time_window_hours,
            offending_source_urls=source_urls,
            offending_edge_ids=edge_ids,
            detected_at=now_utc,
            message=message,
        )
        reports.append(report)

        logger.warning(
            "ANOMALY DETECTED | severity=%s | cluster=%s...%s | count=%d | sources=%d",
            severity.value, cluster_key[:8], cluster_key[-4:],
            count, len(source_urls),
        )

    if not reports:
        logger.info(
            "detect_narrative_anomaly: no flooding anomalies found across %d clusters.",
            len(clusters),
        )

    return reports


# ─────────────────────────────────────────────────────────────────────────────
# Primary public API — Function 2
# ─────────────────────────────────────────────────────────────────────────────

def check_cross_lingual_conflict(
    edge_english: GraphEdge,
    edge_foreign_lang: GraphEdge,
) -> ConflictReport:
    """
    Detect whether two edges describing the *same* geopolitical event in
    different languages carry contradictory claims.

    This catches a specific class of information warfare: a narrative that
    appears diplomatically cooperative in English-language sources but
    openly hostile in domestic-language sources (or vice versa).

    Contradiction is detected on TWO axes:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ Axis 1 — RELATIONSHIP CONTRADICTION                                 │
    │   The two edges must link the same source→target node pair.         │
    │   If one claims ALLIED_WITH and the other CONFLICT_WITH, that is    │
    │   a direct semantic opposition per `_OPPOSING_RELATIONSHIPS`.       │
    │                                                                     │
    │ Axis 2 — SENTIMENT OPPOSITION                                       │
    │   LLM sentiment analysis (mocked) is run on each edge's            │
    │   `raw_text_snippet`. If one snippet is COOPERATIVE and the other   │
    │   HOSTILE (or POSITIVE vs NEGATIVE), the narratives are opposed.   │
    └─────────────────────────────────────────────────────────────────────┘

    If EITHER axis fires, the status of BOTH edges is set to
    `EdgeStatus.CONTESTED_NARRATIVE` so they surface for human review.

    Args:
        edge_english:      The English-language edge for this event.
        edge_foreign_lang: The foreign-language edge for the same event.

    Returns:
        A `ConflictReport` dataclass.  `has_conflict` is True if a
        contradiction was found on at least one axis.

    Side-effects:
        If a conflict is detected:
          • Both edges' `status` is set to `EdgeStatus.CONTESTED_NARRATIVE`.
          • A WARNING-level log entry is emitted.

    Raises:
        ValueError: If both edges share the same language code (can't compare).
        ValueError: If the two edges do not describe the same entity pair.

    Example:
        >>> report = check_cross_lingual_conflict(en_edge, ru_edge)
        >>> if report.has_conflict:
        ...     print(report.conflict_type)      # → "BOTH"
        ...     print(report.resolution_suggestion)
    """
    # ── Guard: same-language comparison is a caller error ─────────────────
    if edge_english.provenance.language_code == edge_foreign_lang.provenance.language_code:
        raise ValueError(
            f"cross_lingual_conflict check requires two DIFFERENT language codes. "
            f"Both edges have language='{edge_english.provenance.language_code}'."
        )

    # ── Guard: edges must describe the same entity pair ───────────────────
    same_direction = (
        edge_english.source_node_id == edge_foreign_lang.source_node_id
        and edge_english.target_node_id == edge_foreign_lang.target_node_id
    )
    reverse_direction = (
        edge_english.source_node_id == edge_foreign_lang.target_node_id
        and edge_english.target_node_id == edge_foreign_lang.source_node_id
    )
    if not (same_direction or reverse_direction):
        raise ValueError(
            f"Both edges must connect the same entity pair. "
            f"English: {edge_english.source_node_id[:8]}→{edge_english.target_node_id[:8]} | "
            f"Foreign: {edge_foreign_lang.source_node_id[:8]}→{edge_foreign_lang.target_node_id[:8]}"
        )

    lang_pair = (
        f"{edge_english.provenance.language_code} vs "
        f"{edge_foreign_lang.provenance.language_code}"
    )

    logger.debug(
        "check_cross_lingual_conflict | edges: %s (lang=%s) vs %s (lang=%s)",
        edge_english.edge_id[:8],
        edge_english.provenance.language_code,
        edge_foreign_lang.edge_id[:8],
        edge_foreign_lang.provenance.language_code,
    )

    # ── Axis 1: Relationship type contradiction ────────────────────────────
    rel_en  = edge_english.relationship_type
    rel_for = edge_foreign_lang.relationship_type

    relationship_contradicts = (
        _OPPOSING_RELATIONSHIPS.get(rel_en) == rel_for
        or _OPPOSING_RELATIONSHIPS.get(rel_for) == rel_en
    )

    # ── Axis 2: Sentiment opposition via (mock) LLM ───────────────────────
    sentiment_en  = _mock_llm_sentiment_analysis(
        edge_english.raw_text_snippet,
        edge_english.provenance.language_code,
    )
    sentiment_for = _mock_llm_sentiment_analysis(
        edge_foreign_lang.raw_text_snippet,
        edge_foreign_lang.provenance.language_code,
    )

    sentiment_contradicts = (
        _OPPOSING_SENTIMENTS.get(sentiment_en) == sentiment_for
        or _OPPOSING_SENTIMENTS.get(sentiment_for) == sentiment_en
    )

    # ── Determine conflict type ────────────────────────────────────────────
    has_conflict = relationship_contradicts or sentiment_contradicts

    if relationship_contradicts and sentiment_contradicts:
        conflict_type = "BOTH"
    elif relationship_contradicts:
        conflict_type = "RELATIONSHIP_CONTRADICTION"
    elif sentiment_contradicts:
        conflict_type = "SENTIMENT_OPPOSITION"
    else:
        conflict_type = None

    # ── Resolution suggestion ──────────────────────────────────────────────
    if not has_conflict:
        resolution_suggestion = (
            "No conflict detected. Edges may be safely promoted to ACTIVE "
            "after standard trust scoring."
        )
    else:
        resolution_suggestion = (
            f"[{conflict_type}] "
            f"English source ({edge_english.provenance.author_or_outlet or edge_english.provenance.source_url}) "
            f"reports '{rel_en.value}' with sentiment '{sentiment_en}'. "
            f"Foreign source ({edge_foreign_lang.provenance.author_or_outlet or edge_foreign_lang.provenance.source_url}, "
            f"lang={edge_foreign_lang.provenance.language_code}) "
            f"reports '{rel_for.value}' with sentiment '{sentiment_for}'. "
            f"Recommend: (1) Escalate to senior analyst. "
            f"(2) Cross-reference with third-party {lang_pair.split(' vs ')[1].upper()}-language source. "
            f"(3) Tag both edges CONTESTED_NARRATIVE pending review."
        )

    # ── Side-effect: stamp CONTESTED_NARRATIVE on both edges ──────────────
    if has_conflict:
        for contested_edge in (edge_english, edge_foreign_lang):
            if contested_edge.status not in (EdgeStatus.VERIFIED, EdgeStatus.REJECTED):
                contested_edge.status = EdgeStatus.CONTESTED_NARRATIVE

        logger.warning(
            "CROSS-LINGUAL CONFLICT | type=%s | lang_pair=%s | "
            "en_rel=%s (sent=%s) | for_rel=%s (sent=%s) | "
            "edges=[%s, %s]",
            conflict_type, lang_pair,
            rel_en.value, sentiment_en,
            rel_for.value, sentiment_for,
            edge_english.edge_id[:8],
            edge_foreign_lang.edge_id[:8],
        )
    else:
        logger.debug(
            "check_cross_lingual_conflict: no conflict | lang_pair=%s | "
            "rel: %s vs %s | sentiment: %s vs %s",
            lang_pair, rel_en.value, rel_for.value, sentiment_en, sentiment_for,
        )

    return ConflictReport(
        has_conflict=has_conflict,
        conflict_type=conflict_type,
        edge_english_id=edge_english.edge_id,
        edge_foreign_id=edge_foreign_lang.edge_id,
        english_relationship=rel_en,
        foreign_relationship=rel_for,
        english_sentiment=sentiment_en,
        foreign_sentiment=sentiment_for,
        language_pair=lang_pair,
        resolution_suggestion=resolution_suggestion,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience batch wrapper
# ─────────────────────────────────────────────────────────────────────────────

def scan_edge_pairs_for_conflicts(
    edge_pairs: List[Tuple[GraphEdge, GraphEdge]],
) -> List[ConflictReport]:
    """
    Run `check_cross_lingual_conflict` over a list of edge pairs.

    Intended to be called after entity-linking has grouped edges that
    describe the same real-world event across multiple language sources.

    Invalid pairs (same language, mismatched entity pairs) are logged and
    skipped so they do not abort the entire batch.

    Args:
        edge_pairs: List of (english_edge, foreign_edge) tuples.

    Returns:
        List of ConflictReport for ALL pairs (both conflicting and clean).
        Use `[r for r in results if r.has_conflict]` to get only conflicts.
    """
    reports: List[ConflictReport] = []
    for en_edge, for_edge in edge_pairs:
        try:
            report = check_cross_lingual_conflict(en_edge, for_edge)
            reports.append(report)
        except ValueError as exc:
            logger.warning(
                "scan_edge_pairs_for_conflicts: skipping invalid pair "
                "(%s, %s): %s",
                en_edge.edge_id[:8], for_edge.edge_id[:8], exc,
            )
    return reports
