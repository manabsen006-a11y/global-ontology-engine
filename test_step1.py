"""
test_step1.py — Smoke-test for Step 1: Confidence & Provenance Layer
Run from the project root:
    python test_step1.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone, timedelta

from app.models.ontology_models import (
    GraphNode, GraphEdge, ProvenanceMetadata,
    NodeType, RelationshipType, EdgeStatus, SourceType,
)
from app.services.provenance_engine import (
    calculate_dynamic_trust,
    batch_score_edges,
    explain_trust_score,
    get_low_confidence_edges,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_prov(
    credibility: float,
    corroboration: int,
    days_old: float,
    decay: float = 0.01,
    lang: str = "en",
) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        source_url=f"https://example.com/article-{credibility}-{days_old}d",
        source_type=SourceType.NEWS_ARTICLE,
        author_or_outlet="Test Outlet",
        source_credibility_score=credibility,
        corroboration_count=corroboration,
        timestamp=datetime.now(timezone.utc) - timedelta(days=days_old),
        temporal_decay_factor=decay,
        language_code=lang,
    )


def _make_edge(prov: ProvenanceMetadata) -> GraphEdge:
    node_a = GraphNode(node_type=NodeType.COUNTRY, name="Country A")
    node_b = GraphNode(node_type=NodeType.COUNTRY, name="Country B")
    return GraphEdge(
        source_node_id=node_a.node_id,
        target_node_id=node_b.node_id,
        relationship_type=RelationshipType.ALLIED_WITH,
        provenance=prov,
    )


# ── Test 1: High-confidence edge ──────────────────────────────────────────

def test_high_confidence():
    prov = _make_prov(credibility=0.90, corroboration=8, days_old=5, decay=0.01)
    edge = _make_edge(prov)
    result = calculate_dynamic_trust(edge)

    # base=0.90, bonus=log2(8)*0.10=0.30(capped), penalty=5*0.01=0.05 → 1.15 clamped to 1.0
    assert edge.status == EdgeStatus.ACTIVE, f"Expected ACTIVE, got {edge.status}"
    assert edge.trust_score == 1.0, f"Expected 1.0, got {edge.trust_score}"
    assert result.final_trust_score == 1.0
    print(f"[PASS] test_high_confidence → score={edge.trust_score:.3f}, status={edge.status.value}")


# ── Test 2: Low-confidence edge (flagged for HITL) ───────────────────────

def test_low_confidence():
    prov = _make_prov(credibility=0.35, corroboration=1, days_old=30, decay=0.02)
    edge = _make_edge(prov)
    result = calculate_dynamic_trust(edge)

    # base=0.35, bonus=0 (count=1), penalty=30*0.02=0.60 → -0.25 → clamped 0.0
    assert edge.status == EdgeStatus.LOW_CONFIDENCE, f"Expected LOW_CONFIDENCE, got {edge.status}"
    assert edge.trust_score < 0.60, f"Expected <0.60, got {edge.trust_score}"
    print(f"[PASS] test_low_confidence → score={edge.trust_score:.3f}, status={edge.status.value}")


# ── Test 3: Moderate-confidence edge with corroboration ──────────────────

def test_medium_confidence_with_corroboration():
    prov = _make_prov(credibility=0.55, corroboration=4, days_old=2, decay=0.01)
    edge = _make_edge(prov)
    result = calculate_dynamic_trust(edge)

    # base=0.55, bonus=log2(4)*0.10=0.20, penalty=2*0.01=0.02 → 0.73
    assert edge.trust_score is not None
    assert 0.60 <= edge.trust_score <= 1.0, f"Expected >=0.60, got {edge.trust_score}"
    assert edge.status == EdgeStatus.ACTIVE
    print(f"[PASS] test_medium_confidence_with_corroboration → score={edge.trust_score:.3f}")


# ── Test 4: Self-loop validation ──────────────────────────────────────────

def test_self_loop_rejected():
    prov = _make_prov(credibility=0.80, corroboration=1, days_old=1, decay=0.01)
    try:
        same_id = "same-uuid-1234"
        bad_edge = GraphEdge(
            source_node_id=same_id,
            target_node_id=same_id,
            relationship_type=RelationshipType.ALLIED_WITH,
            provenance=prov,
        )
        raise AssertionError("Should have raised ValueError for self-loop!")
    except ValueError as e:
        print(f"[PASS] test_self_loop_rejected → raised ValueError: {e}")


# ── Test 5: Terminal state guard ──────────────────────────────────────────

def test_verified_edge_not_rescored():
    prov = _make_prov(credibility=0.80, corroboration=2, days_old=1, decay=0.01)
    edge = _make_edge(prov)
    edge.status = EdgeStatus.VERIFIED
    edge.trust_score = 1.0  # HITL set it
    try:
        calculate_dynamic_trust(edge)
        raise AssertionError("Should have raised ValueError for VERIFIED edge!")
    except ValueError as e:
        print(f"[PASS] test_verified_edge_not_rescored → raised ValueError: {e}")


# ── Test 6: Batch scoring ─────────────────────────────────────────────────

def test_batch_scoring():
    edges = [
        _make_edge(_make_prov(0.90, 3, 1, 0.01)),
        _make_edge(_make_prov(0.30, 1, 60, 0.01)),
        _make_edge(_make_prov(0.70, 2, 5, 0.005)),
    ]
    # Mark one as VERIFIED → should be skipped
    edges[2].status = EdgeStatus.VERIFIED
    results = batch_score_edges(edges)
    assert len(results) == 2, f"Expected 2 results (1 skipped), got {len(results)}"
    print(f"[PASS] test_batch_scoring → scored {len(results)} edges (1 VERIFIED skipped)")


# ── Test 7: explain_trust_score  ──────────────────────────────────────────

def test_explain():
    prov = _make_prov(credibility=0.65, corroboration=3, days_old=7, decay=0.01)
    edge = _make_edge(prov)
    calculate_dynamic_trust(edge)
    explanation = explain_trust_score(edge)
    assert "explanation_text" in explanation
    assert "projected_score" in explanation
    print(f"[PASS] test_explain → projected_score={explanation['projected_score']}")
    print(f"       Explanation: {explanation['explanation_text']}")


# ── Test 8: Low-confidence filter ────────────────────────────────────────

def test_get_low_confidence_edges():
    edges = [
        _make_edge(_make_prov(0.90, 4, 1)),
        _make_edge(_make_prov(0.30, 1, 60, 0.02)),
        _make_edge(_make_prov(0.50, 1, 20, 0.01)),
    ]
    batch_score_edges(edges)
    low_conf = get_low_confidence_edges(edges)
    # Second and third edges should be low confidence
    assert len(low_conf) >= 1, f"Expected at least 1 low-confidence edge, got {len(low_conf)}"
    for e in low_conf:
        assert e.trust_score is None or e.trust_score < 0.60
    print(f"[PASS] test_get_low_confidence_edges → {len(low_conf)} low-confidence edge(s) found")


# ── Neo4j property serialization ─────────────────────────────────────────

def test_neo4j_properties():
    prov = _make_prov(0.75, 2, 3)
    edge = _make_edge(prov)
    calculate_dynamic_trust(edge)
    props = edge.to_neo4j_properties()
    required_keys = [
        "edge_id", "source_node_id", "target_node_id", "relationship_type",
        "trust_score", "status", "prov_source_url", "prov_credibility_score",
        "prov_corroboration_count", "prov_timestamp",
    ]
    for key in required_keys:
        assert key in props, f"Missing Neo4j property key: '{key}'"
    print(f"[PASS] test_neo4j_properties → {len(props)} properties serialized correctly")


# ── Runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_high_confidence,
        test_low_confidence,
        test_medium_confidence_with_corroboration,
        test_self_loop_rejected,
        test_verified_edge_not_rescored,
        test_batch_scoring,
        test_explain,
        test_get_low_confidence_edges,
        test_neo4j_properties,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {test_fn.__name__} → {exc}")

    print(f"\n{'='*60}")
    print(f"Step 1 Smoke-Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
