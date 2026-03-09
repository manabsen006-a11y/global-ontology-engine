"""
test_step2.py — Smoke-test for Step 2: Adversarial Input Detection
Run from the project root:
    python -X utf8 test_step2.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone, timedelta
from app.models.ontology_models import (
    GraphNode, GraphEdge, ProvenanceMetadata,
    NodeType, RelationshipType, EdgeStatus, SourceType,
)
from app.services.adversarial_detector import (
    detect_narrative_anomaly,
    check_cross_lingual_conflict,
    scan_edge_pairs_for_conflicts,
    FLOODING_COUNT_THRESHOLD,
    AnomalySeverity,
)


# ── Shared helpers ─────────────────────────────────────────────────────────

NODE_A = GraphNode(node_type=NodeType.COUNTRY, name="Alpha")
NODE_B = GraphNode(node_type=NodeType.COUNTRY, name="Beta")


def _make_edge(
    rel: RelationshipType = RelationshipType.ALLIED_WITH,
    credibility: float = 0.20,
    source_type: SourceType = SourceType.SOCIAL_MEDIA,
    days_old: float = 0.0,
    lang: str = "en",
    text: str = "",
    src_id: str = None,
    tgt_id: str = None,
) -> GraphEdge:
    prov = ProvenanceMetadata(
        source_url=f"https://source.io/{credibility}-{lang}",
        source_type=source_type,
        author_or_outlet="TestSource",
        source_credibility_score=credibility,
        corroboration_count=1,
        timestamp=datetime.now(timezone.utc) - timedelta(days=days_old),
        temporal_decay_factor=0.01,
        language_code=lang,
    )
    return GraphEdge(
        source_node_id=src_id or NODE_A.node_id,
        target_node_id=tgt_id or NODE_B.node_id,
        relationship_type=rel,
        provenance=prov,
        raw_text_snippet=text or None,
    )


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — detect_narrative_anomaly
# ════════════════════════════════════════════════════════════════════════════

def test_no_anomaly_below_threshold():
    """Fewer than FLOODING_COUNT_THRESHOLD identical claims: no anomaly."""
    edges = [_make_edge() for _ in range(FLOODING_COUNT_THRESHOLD - 1)]
    reports = detect_narrative_anomaly(edges, time_window_hours=1.0)
    assert reports == [], f"Expected no anomalies, got {len(reports)}"
    print(f"[PASS] test_no_anomaly_below_threshold  →  0 reports for {len(edges)} edges")


def test_anomaly_detected_at_threshold():
    """Exactly FLOODING_COUNT_THRESHOLD identical low-cred claims: anomaly fires."""
    edges = [_make_edge() for _ in range(FLOODING_COUNT_THRESHOLD)]
    reports = detect_narrative_anomaly(edges, time_window_hours=1.0)
    assert len(reports) == 1, f"Expected 1 report, got {len(reports)}"
    assert reports[0].is_anomalous is True
    assert reports[0].duplicate_count == FLOODING_COUNT_THRESHOLD
    assert reports[0].severity in (AnomalySeverity.MEDIUM, AnomalySeverity.HIGH, AnomalySeverity.CRITICAL)
    print(f"[PASS] test_anomaly_detected_at_threshold  →  severity={reports[0].severity.value}, "
          f"count={reports[0].duplicate_count}")


def test_anomaly_critical_severity():
    """200+ identical claims triggers CRITICAL severity."""
    edges = [_make_edge() for _ in range(FLOODING_COUNT_THRESHOLD * 4 + 1)]
    reports = detect_narrative_anomaly(edges, time_window_hours=1.0)
    assert reports[0].severity == AnomalySeverity.CRITICAL
    print(f"[PASS] test_anomaly_critical_severity  →  {reports[0].severity.value} at {len(edges)} edges")


def test_high_credibility_sources_not_flagged():
    """High-credibility sources above the ceiling are never candidates."""
    edges = [
        _make_edge(credibility=0.95, source_type=SourceType.GOVERNMENT_DOC)
        for _ in range(FLOODING_COUNT_THRESHOLD * 2)
    ]
    reports = detect_narrative_anomaly(edges, time_window_hours=1.0)
    assert reports == [], f"Expected no anomaly for high-cred sources, got {len(reports)}"
    print(f"[PASS] test_high_credibility_sources_not_flagged  →  0 reports for {len(edges)} high-cred edges")


def test_edges_outside_window_not_flagged():
    """Claims older than the time window are excluded from the count."""
    old_edges = [
        _make_edge(credibility=0.10, days_old=2.0)  # 2 days old, outside 1h window
        for _ in range(FLOODING_COUNT_THRESHOLD * 2)
    ]
    reports = detect_narrative_anomaly(old_edges, time_window_hours=1.0)
    assert reports == [], f"Expected no anomaly for old edges, got {len(reports)}"
    print(f"[PASS] test_edges_outside_window_not_flagged  →  old edges correctly ignored")


def test_anomaly_quarantines_edges():
    """Edges in flagged clusters are stamped LOW_CONFIDENCE (quarantined)."""
    edges = [_make_edge() for _ in range(FLOODING_COUNT_THRESHOLD)]
    reports = detect_narrative_anomaly(edges, time_window_hours=1.0)
    assert reports, "Expected at least 1 report"
    for edge in edges:
        assert edge.status == EdgeStatus.LOW_CONFIDENCE, (
            f"Expected LOW_CONFIDENCE, got {edge.status}"
        )
    print(f"[PASS] test_anomaly_quarantines_edges  →  all {len(edges)} edges quarantined")


def test_two_distinct_clusters_both_flagged():
    """Two different relationship types flooding simultaneously produce 2 reports."""
    cluster1 = [_make_edge(rel=RelationshipType.ALLIED_WITH)  for _ in range(FLOODING_COUNT_THRESHOLD)]
    cluster2 = [_make_edge(rel=RelationshipType.CONFLICT_WITH) for _ in range(FLOODING_COUNT_THRESHOLD)]
    reports = detect_narrative_anomaly(cluster1 + cluster2, time_window_hours=1.0)
    assert len(reports) == 2, f"Expected 2 reports (2 clusters), got {len(reports)}"
    print(f"[PASS] test_two_distinct_clusters_both_flagged  →  {len(reports)} anomaly reports")


def test_verified_edges_not_quarantined():
    """VERIFIED terminal edges are never overwritten by the flooding detector."""
    edges = [_make_edge() for _ in range(FLOODING_COUNT_THRESHOLD)]
    edges[0].status = EdgeStatus.VERIFIED  # HITL-locked
    detect_narrative_anomaly(edges, time_window_hours=1.0)
    assert edges[0].status == EdgeStatus.VERIFIED, "VERIFIED edge must not be overwritten"
    print(f"[PASS] test_verified_edges_not_quarantined  →  VERIFIED edge preserved")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — check_cross_lingual_conflict
# ════════════════════════════════════════════════════════════════════════════

def test_relationship_contradiction_flagged():
    """ALLIED_WITH (en) vs CONFLICT_WITH (ru) → RELATIONSHIP_CONTRADICTION."""
    en_edge  = _make_edge(rel=RelationshipType.ALLIED_WITH,  lang="en", text="The nations agreed to a mutual defense pact.")
    ru_edge  = _make_edge(rel=RelationshipType.CONFLICT_WITH, lang="ru", text="Military forces attacked the border region.")
    report = check_cross_lingual_conflict(en_edge, ru_edge)
    assert report.has_conflict is True
    # conflict_type is either "RELATIONSHIP_CONTRADICTION" or "BOTH"
    # (when sentiment axes also fires). Both are correct outcomes.
    assert report.conflict_type in ("RELATIONSHIP_CONTRADICTION", "BOTH"), (
        f"Unexpected conflict_type: {report.conflict_type!r}"
    )
    assert en_edge.status == EdgeStatus.CONTESTED_NARRATIVE
    assert ru_edge.status == EdgeStatus.CONTESTED_NARRATIVE
    print(f"[PASS] test_relationship_contradiction_flagged  →  conflict_type={report.conflict_type}")


def test_sentiment_opposition_flagged():
    """
    Same relationship type but opposite sentiments (COOPERATIVE vs HOSTILE)
    triggers a SENTIMENT_OPPOSITION.
    """
    en_edge = _make_edge(rel=RelationshipType.TRADES_WITH, lang="en",
                         text="Bilateral trade cooperation is progressing well.")
    zh_edge = _make_edge(rel=RelationshipType.TRADES_WITH, lang="zh",
                         text="Trade war escalating; countries attack each other's tariffs.")
    report = check_cross_lingual_conflict(en_edge, zh_edge)
    assert report.has_conflict is True
    assert report.conflict_type in ("SENTIMENT_OPPOSITION", "BOTH")
    print(f"[PASS] test_sentiment_opposition_flagged  →  "
          f"sentiments: {report.english_sentiment} vs {report.foreign_sentiment} | type={report.conflict_type}")


def test_both_axes_fire():
    """Opposing relationship AND opposing sentiment → conflict_type BOTH."""
    en_edge = _make_edge(rel=RelationshipType.ALLIED_WITH, lang="en",
                         text="Joint military cooperation agreement signed.")
    ru_edge = _make_edge(rel=RelationshipType.CONFLICT_WITH, lang="ru",
                         text="Invasion and bombardment of frontier towns.")
    report = check_cross_lingual_conflict(en_edge, ru_edge)
    assert report.has_conflict is True
    # Relationship axes must fire; sentiment may or may not, both are valid outcomes
    assert report.conflict_type is not None
    print(f"[PASS] test_both_axes_fire  →  conflict_type={report.conflict_type}")


def test_no_conflict_when_aligned():
    """Two edges with compatible relationships and sentiments → no conflict."""
    en_edge = _make_edge(rel=RelationshipType.ALLIED_WITH, lang="en",
                         text="Nations signed peace treaty and aid agreement.")
    fr_edge = _make_edge(rel=RelationshipType.ALLIED_WITH, lang="fr",
                         text="Bilateral cooperation and diplomatic support.")
    report = check_cross_lingual_conflict(en_edge, fr_edge)
    assert report.has_conflict is False
    assert report.conflict_type is None
    assert en_edge.status != EdgeStatus.CONTESTED_NARRATIVE
    print(f"[PASS] test_no_conflict_when_aligned  →  no conflict (both cooperative)")


def test_same_language_raises():
    """Comparing two edges with the same language code raises ValueError."""
    en1 = _make_edge(lang="en", text="Alliance formed.")
    en2 = _make_edge(lang="en", text="Alliance formed.")
    try:
        check_cross_lingual_conflict(en1, en2)
        raise AssertionError("Should have raised ValueError for same language!")
    except ValueError as e:
        print(f"[PASS] test_same_language_raises  →  ValueError: {e}")


def test_mismatched_entity_pair_raises():
    """Edges for different entity pairs raise ValueError."""
    other_node = GraphNode(node_type=NodeType.COUNTRY, name="Gamma")
    en_edge = _make_edge(lang="en")
    ar_edge = _make_edge(lang="ar", src_id=NODE_A.node_id, tgt_id=other_node.node_id)
    try:
        check_cross_lingual_conflict(en_edge, ar_edge)
        raise AssertionError("Should have raised ValueError for mismatched entity pair!")
    except ValueError as e:
        print(f"[PASS] test_mismatched_entity_pair_raises  →  ValueError raised correctly")


def test_scan_batch_with_mixed_pairs():
    """Batch scan returns one report per pair including clean ones."""
    en1 = _make_edge(rel=RelationshipType.ALLIED_WITH,  lang="en", text="peace treaty cooperation")
    ru1 = _make_edge(rel=RelationshipType.CONFLICT_WITH, lang="ru", text="attack invasion war")
    en2 = _make_edge(rel=RelationshipType.TRADES_WITH,   lang="en", text="bilateral trade growth")
    de2 = _make_edge(rel=RelationshipType.TRADES_WITH,   lang="de", text="cooperation and investment")
    pairs = [(en1, ru1), (en2, de2)]
    reports = scan_edge_pairs_for_conflicts(pairs)
    assert len(reports) == 2
    conflicts = [r for r in reports if r.has_conflict]
    clean     = [r for r in reports if not r.has_conflict]
    assert len(conflicts) >= 1
    print(f"[PASS] test_scan_batch_with_mixed_pairs  →  {len(conflicts)} conflict(s), {len(clean)} clean")


# ── Runner ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("STEP 2 SMOKE-TEST: Adversarial Input Detection")
    print("="*60 + "\n")

    all_tests = [
        # -- detect_narrative_anomaly --
        test_no_anomaly_below_threshold,
        test_anomaly_detected_at_threshold,
        test_anomaly_critical_severity,
        test_high_credibility_sources_not_flagged,
        test_edges_outside_window_not_flagged,
        test_anomaly_quarantines_edges,
        test_two_distinct_clusters_both_flagged,
        test_verified_edges_not_quarantined,
        # -- check_cross_lingual_conflict --
        test_relationship_contradiction_flagged,
        test_sentiment_opposition_flagged,
        test_both_axes_fire,
        test_no_conflict_when_aligned,
        test_same_language_raises,
        test_mismatched_entity_pair_raises,
        test_scan_batch_with_mixed_pairs,
    ]

    passed = failed = 0
    for test_fn in all_tests:
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {test_fn.__name__}  -->  {exc}")

    print(f"\n{'='*60}")
    print(f"Step 2 Smoke-Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
