"""
app/services/provenance_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global Ontology Engine — Confidence & Provenance Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This module is the authoritative source for computing and updating the
**trust score** on every `GraphEdge` in the Knowledge Graph.

Core responsibilities:
  1. `calculate_dynamic_trust(edge)` — compute a temporally-decayed,
     corroboration-boosted confidence score from provenance metadata.
  2. `batch_score_edges(edges)` — efficiently score a list of edges,
     updating their `trust_score` and `status` in place.
  3. `explain_trust_score(edge)` — return a human-readable breakdown of
     how the score was derived (used by the Nexus dashboard).

Algorithm overview
──────────────────
The trust score is a float in [0.0, 1.0] derived in three stages:

  Stage 1 — Base credibility
    base = provenance.source_credibility_score

  Stage 2 — Corroboration bonus
    bonus = CORROBORATION_BONUS_RATE × log2(corroboration_count)
    (logarithmic: first few independent sources add most value; the
    benefit of the 100th source is much less than the 2nd.)

  Stage 3 — Temporal decay penalty
    age_days = (now_utc − provenance.timestamp).total_seconds() / 86400
    penalty  = provenance.temporal_decay_factor × age_days
    (Linear decay; configurable per-edge via temporal_decay_factor.)

  Final score = clamp(base + bonus − penalty, 0.0, 1.0)

Status assignment after scoring:
  ≥ 0.85         → ACTIVE  (high confidence)
  0.60 – 0.84    → ACTIVE  (acceptable confidence)
  < 0.60         → LOW_CONFIDENCE  (queued for human review)

Plug-in points for Neo4j persistence:
  After scoring, call `edge.to_neo4j_properties()` and upsert to Neo4j:
    session.run(
        "MATCH (s {node_id:$source_node_id}),(t {node_id:$target_node_id})"
        "MERGE (s)-[r:%s {edge_id:$edge_id}]->(t) SET r += $props"
        % edge.relationship_type.value,
        props=edge.to_neo4j_properties()
    )
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.models.ontology_models import (
    EdgeStatus,
    GraphEdge,
    TrustScoreResult,
)

# ─────────────────────────────────────────────────────────────────────────────
# Module-level logger
# ─────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ─────────────────────────────────────────────────────────────────────────────
# Tuneable hyperparameters
# ─────────────────────────────────────────────────────────────────────────────

# Multiplier applied to the log2 of the corroboration count.
# A value of 0.10 means that 4 independent sources give a +0.20 bonus (log2(4)=2).
CORROBORATION_BONUS_RATE: float = 0.10

# Edges with a final trust score below this threshold are quarantined in the
# HITL review queue rather than activated in the live graph.
LOW_CONFIDENCE_THRESHOLD: float = 0.60

# Minimum trust score to be considered "high confidence" (used for logging).
HIGH_CONFIDENCE_THRESHOLD: float = 0.85

# Maximum possible bonus from corroboration (caps the logarithmic curve).
MAX_CORROBORATION_BONUS: float = 0.30


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _current_utc_now() -> datetime:
    """
    Return the current time in UTC.
    Isolated into its own function so that unit tests can monkey-patch it
    (i.e., freeze time for deterministic trust-score assertions).
    """
    return datetime.now(timezone.utc)


def _compute_age_days(timestamp: datetime) -> float:
    """
    Compute the age of a source claim in fractional days relative to now (UTC).

    Args:
        timestamp: UTC datetime of when the source document was published.

    Returns:
        A non-negative float representing the claim's age in days.
        Returns 0.0 if the timestamp is somehow in the future (clock skew or
        pre-publication embargo dates).
    """
    now = _current_utc_now()

    # Ensure the stored timestamp is timezone-aware before subtraction.
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    delta = now - timestamp
    age_seconds = delta.total_seconds()

    # Guard against negative values (future-dated sources).
    return max(0.0, age_seconds / 86_400.0)


def _compute_corroboration_bonus(corroboration_count: int) -> float:
    """
    Compute a logarithmic bonus reward for multi-source corroboration.

    The log2 scale ensures diminishing returns:
      count=1  → bonus = 0.00  (no bonus for a single source)
      count=2  → bonus = 0.10  (first corroboration adds meaningful value)
      count=4  → bonus = 0.20
      count=8  → bonus = 0.30  (capped even if count grows further)

    Args:
        corroboration_count: Number of independent sources confirming the claim.

    Returns:
        A float bonus in [0.0, MAX_CORROBORATION_BONUS].
    """
    if corroboration_count <= 1:
        return 0.0  # No bonus for a lone, uncorroborated claim.

    raw_bonus = CORROBORATION_BONUS_RATE * math.log2(corroboration_count)
    return min(raw_bonus, MAX_CORROBORATION_BONUS)


def _compute_temporal_penalty(age_days: float, decay_factor: float) -> float:
    """
    Compute the linear temporal decay penalty for an edge.

    Formula: penalty = age_days × temporal_decay_factor

    The penalty is hard-capped at 1.0 to avoid producing negative trust scores
    (the downstream clamp handles this too, but it's cleaner to be explicit).

    Args:
        age_days:     Claim age in fractional days (from `_compute_age_days()`).
        decay_factor: Per-day decay rate from `ProvenanceMetadata`.

    Returns:
        A float penalty ≥ 0.0.
    """
    return min(age_days * decay_factor, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Primary public API
# ─────────────────────────────────────────────────────────────────────────────

def calculate_dynamic_trust(edge: GraphEdge) -> TrustScoreResult:
    """
    Calculate the final, temporally-decayed confidence score for a `GraphEdge`
    and **mutate** the edge's `trust_score` and `status` fields in place.

    This is the single authoritative function for trust scoring.  Every
    ingestion pipeline, re-scoring job, and HITL override flow should call
    through this function to ensure consistent behaviour.

    Algorithm (full detail):
    ╔══════════════════════════════════════════════════════════════════════╗
    ║  final_score = clamp(                                               ║
    ║      source_credibility_score                                       ║
    ║      + CORROBORATION_BONUS_RATE × log2(corroboration_count)        ║
    ║      − temporal_decay_factor × age_in_days,                        ║
    ║      min=0.0, max=1.0                                               ║
    ║  )                                                                   ║
    ╚══════════════════════════════════════════════════════════════════════╝

    Side-effects:
        • Sets `edge.trust_score` to the computed value.
        • Sets `edge.status` to LOW_CONFIDENCE if score < 0.60, else ACTIVE.
          (Does NOT override VERIFIED or REJECTED edges — those are terminal
          states managed by the HITL API.)

    Args:
        edge: A mutable `GraphEdge` instance to score.

    Returns:
        A `TrustScoreResult` with a full breakdown of contributing factors.
        This result is also used by the Nexus dashboard for score explanations.

    Raises:
        ValueError: If the edge is in a terminal HITL state (VERIFIED /
                    REJECTED) and should not be re-scored automatically.

    Example:
        >>> from app.models.ontology_models import *
        >>> from datetime import datetime, timezone, timedelta
        >>> prov = ProvenanceMetadata(
        ...     source_url="https://reuters.com/article/1",
        ...     source_credibility_score=0.80,
        ...     corroboration_count=4,
        ...     timestamp=datetime.now(timezone.utc) - timedelta(days=10),
        ...     temporal_decay_factor=0.01,
        ... )
        >>> edge = GraphEdge(
        ...     source_node_id="node-a", target_node_id="node-b",
        ...     relationship_type=RelationshipType.ALLIED_WITH,
        ...     provenance=prov,
        ... )
        >>> result = calculate_dynamic_trust(edge)
        >>> print(f"Trust: {result.final_trust_score:.3f}")
        Trust: 0.800   # 0.80 + 0.20(bonus) − 0.10(decay) = 0.90 → clamped
    """
    prov = edge.provenance

    # ── Guard: do not auto-rescore terminal HITL states ────────────────────
    if edge.status in (EdgeStatus.VERIFIED, EdgeStatus.REJECTED):
        raise ValueError(
            f"Edge '{edge.edge_id}' is in terminal state '{edge.status.value}'. "
            "Trust recalculation is blocked to preserve HITL override integrity. "
            "Use the HITL API to modify VERIFIED/REJECTED edges."
        )

    # ── Stage 1: Base credibility ──────────────────────────────────────────
    base_credibility: float = prov.source_credibility_score

    # ── Stage 2: Corroboration bonus ──────────────────────────────────────
    corroboration_bonus: float = _compute_corroboration_bonus(
        prov.corroboration_count
    )

    # ── Stage 3: Temporal penalty ─────────────────────────────────────────
    age_days: float = _compute_age_days(prov.timestamp)
    temporal_penalty: float = _compute_temporal_penalty(
        age_days, prov.temporal_decay_factor
    )

    # ── Final score: combine and clamp to [0.0, 1.0] ──────────────────────
    raw_score: float = base_credibility + corroboration_bonus - temporal_penalty
    final_score: float = max(0.0, min(1.0, raw_score))

    # ── Apply result to the edge (in-place mutation) ──────────────────────
    edge.trust_score = final_score

    # Update status only if the edge is not in a locked HITL state.
    # CONTESTED_NARRATIVE status is preserved (it was set by the adversarial
    # detector); trust can still be recalculated and the status updated.
    if edge.status not in (EdgeStatus.CONTESTED_NARRATIVE,):
        if final_score < LOW_CONFIDENCE_THRESHOLD:
            edge.status = EdgeStatus.LOW_CONFIDENCE
        else:
            edge.status = EdgeStatus.ACTIVE

    # ── Build structured result for logging / API ─────────────────────────
    result = TrustScoreResult(
        edge_id=edge.edge_id,
        raw_credibility=base_credibility,
        corroboration_bonus=corroboration_bonus,
        temporal_penalty=temporal_penalty,
        final_trust_score=final_score,
        age_days=age_days,
        calculation_timestamp=_current_utc_now(),
    )

    # ── Logging ───────────────────────────────────────────────────────────
    log_level = (
        logging.DEBUG if final_score >= HIGH_CONFIDENCE_THRESHOLD
        else logging.INFO if final_score >= LOW_CONFIDENCE_THRESHOLD
        else logging.WARNING
    )
    logger.log(
        log_level,
        "Trust scored | edge_id=%s | credibility=%.3f | corr_bonus=%.3f | "
        "temporal_penalty=%.3f (age=%.1fd) | final=%.3f | status=%s",
        edge.edge_id,
        base_credibility,
        corroboration_bonus,
        temporal_penalty,
        age_days,
        final_score,
        edge.status.value,
    )

    return result


def batch_score_edges(edges: List[GraphEdge]) -> List[TrustScoreResult]:
    """
    Score a batch of `GraphEdge` objects, skipping terminal HITL states.

    This function is intended to be called by the ingestion pipeline after
    a bulk NLP extraction run.  Failed individual edges are logged but do
    NOT abort the entire batch.

    Args:
        edges: List of mutable `GraphEdge` instances to score.

    Returns:
        List of `TrustScoreResult` objects (one per successfully scored edge).
        Edges in VERIFIED / REJECTED states are silently skipped.
    """
    results: List[TrustScoreResult] = []

    for edge in edges:
        # Skip terminal states without raising an exception in batch mode.
        if edge.status in (EdgeStatus.VERIFIED, EdgeStatus.REJECTED):
            logger.debug(
                "batch_score_edges: skipping terminal edge '%s' (status=%s)",
                edge.edge_id, edge.status.value,
            )
            continue

        try:
            result = calculate_dynamic_trust(edge)
            results.append(result)
        except Exception as exc:
            logger.error(
                "batch_score_edges: failed to score edge '%s': %s",
                edge.edge_id, exc,
            )

    logger.info(
        "batch_score_edges: scored %d / %d edges.",
        len(results), len(edges),
    )
    return results


def explain_trust_score(edge: GraphEdge) -> Dict[str, object]:
    """
    Return a human-readable dictionary explaining how the trust score for
    a given edge was (or would be) derived.  Designed for the Nexus dashboard
    "Score Explainer" panel.

    If the edge has already been scored (trust_score is not None), the
    explanation reflects the *current* stored parameters.  If not scored,
    it performs a preview calculation WITHOUT mutating the edge.

    Args:
        edge: A `GraphEdge` instance (may be scored or pending).

    Returns:
        A dictionary with the following keys:
            edge_id, source_url, source_credibility, corroboration_count,
            corroboration_bonus, claim_age_days, decay_factor,
            temporal_penalty, projected_score, current_status,
            explanation_text
    """
    prov = edge.provenance
    base     = prov.source_credibility_score
    bonus    = _compute_corroboration_bonus(prov.corroboration_count)
    age_days = _compute_age_days(prov.timestamp)
    penalty  = _compute_temporal_penalty(age_days, prov.temporal_decay_factor)
    projected = max(0.0, min(1.0, base + bonus - penalty))

    # Generate prose explanation for the dashboard tooltip.
    explanation_parts: List[str] = [
        f"Source credibility of '{prov.author_or_outlet or prov.source_url}' "
        f"contributes a base score of {base:.2f}.",
    ]
    if bonus > 0:
        explanation_parts.append(
            f"Corroboration across {prov.corroboration_count} sources adds "
            f"a bonus of +{bonus:.3f}."
        )
    else:
        explanation_parts.append(
            "No corroboration bonus (only one known source)."
        )
    explanation_parts.append(
        f"Temporal decay: claim is {age_days:.1f} days old at a decay rate of "
        f"{prov.temporal_decay_factor:.4f}/day → penalty of -{penalty:.3f}."
    )
    explanation_parts.append(
        f"Final projected score: {projected:.3f} "
        f"({'HIGH' if projected >= HIGH_CONFIDENCE_THRESHOLD else 'ACCEPTABLE' if projected >= LOW_CONFIDENCE_THRESHOLD else 'LOW'} confidence)."
    )

    return {
        "edge_id":              edge.edge_id,
        "source_url":           prov.source_url,
        "source_credibility":   base,
        "corroboration_count":  prov.corroboration_count,
        "corroboration_bonus":  round(bonus, 4),
        "claim_age_days":       round(age_days, 2),
        "decay_factor":         prov.temporal_decay_factor,
        "temporal_penalty":     round(penalty, 4),
        "projected_score":      round(projected, 4),
        "current_status":       edge.status.value,
        "explanation_text":     " ".join(explanation_parts),
    }


def get_low_confidence_edges(
    edges: List[GraphEdge],
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> List[GraphEdge]:
    """
    Filter and return all edges whose trust score is below `threshold`.

    This is used by the HITL API endpoint `GET /api/v1/queue/low-confidence`
    to build the analyst review queue.

    Args:
        edges:     List of `GraphEdge` instances (must already be scored).
        threshold: Score cutoff. Defaults to `LOW_CONFIDENCE_THRESHOLD` (0.60).

    Returns:
        Filtered list of edges with trust_score < threshold.
        Edges not yet scored (trust_score is None) are also included because
        they have not been validated at all.
    """
    low_conf: List[GraphEdge] = []
    for edge in edges:
        if edge.trust_score is None or edge.trust_score < threshold:
            low_conf.append(edge)
    return low_conf


# ─────────────────────────────────────────────────────────────────────────────
# Mock Neo4j persistence stub
# (Replace with actual neo4j driver calls once the database is provisioned)
# ─────────────────────────────────────────────────────────────────────────────

class _MockNeo4jSession:
    """
    Stub class mimicking the interface of `neo4j.Session`.
    Used for local development and unit tests without a live Neo4j instance.

    To plug in the real driver:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            persist_edge_to_graph(edge, session)
    """

    def run(self, query: str, **kwargs) -> None:
        """Simulate running a Cypher query by logging it."""
        logger.debug("[MockNeo4j] Cypher: %s | params: %s", query.strip(), kwargs)


# Module-level singleton mock session.  Swap this out for a real driver session.
_MOCK_SESSION = _MockNeo4jSession()


def persist_edge_to_graph(edge: GraphEdge, session=None) -> None:
    """
    Persist a scored `GraphEdge` to the graph database.

    Currently operates against the mock session.  To connect to a live Neo4j
    instance, inject a `neo4j.Session` object via the `session` argument.

    Plug-in point:
        Replace `_MOCK_SESSION` with a real session from:
            GraphDatabase.driver(...).session()

    Args:
        edge:    The fully-scored `GraphEdge` to persist.
        session: Optional real `neo4j.Session`. Falls back to mock if None.
    """
    db_session = session or _MOCK_SESSION
    props = edge.to_neo4j_properties()
    cypher = (
        f"MATCH (s:OntologyEntity {{node_id: $source_node_id}}), "
        f"      (t:OntologyEntity {{node_id: $target_node_id}}) "
        f"MERGE (s)-[r:{edge.relationship_type.value} {{edge_id: $edge_id}}]->(t) "
        f"SET r += $props"
    )
    db_session.run(cypher, **props)
    logger.info("Persisted edge '%s' to graph (status=%s).", edge.edge_id, edge.status.value)
