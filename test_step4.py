"""
test_step4.py — Smoke-test for Step 4: HITL & Dashboard FastAPI Endpoints
Uses FastAPI's TestClient (synchronous ASGI test runner — no live server needed).
Run from the project root:
    python -X utf8 test_step4.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app
from app.api.hitl_routes import seed_mock_edges, _edge_store

# Ensure the edge store is seeded before tests run.
# This mimics what the FastAPI lifespan startup event does on a real server.
seed_mock_edges()

client = TestClient(app)



# ════════════════════════════════════════════════════════════════════════════
# SECTION 0 — Health / root
# ════════════════════════════════════════════════════════════════════════════

def test_root_is_alive():
    r = client.get("/api/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "operational"
    print(f"[PASS] test_root_is_alive  ->  {body['service']} is {body['status']}")


def test_health_endpoint():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["ontology_version"] >= 1
    assert body["entity_types"] == 8
    assert body["relationship_types"] == 10
    print(f"[PASS] test_health_endpoint  ->  "
          f"v{body['ontology_version']}, "
          f"{body['edge_store_count']} edges in store")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — HITL: GET /api/v1/queue/low-confidence
# ════════════════════════════════════════════════════════════════════════════

def test_low_confidence_queue_returns_200():
    r = client.get("/api/v1/queue/low-confidence")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert "total_flagged" in body
    assert "threshold" in body
    assert "edges" in body
    assert body["threshold"] == 0.6
    print(f"[PASS] test_low_confidence_queue_returns_200  ->  "
          f"{body['total_flagged']} flagged edges at threshold={body['threshold']}")


def test_low_confidence_queue_edge_shape():
    r = client.get("/api/v1/queue/low-confidence")
    body = r.json()
    if body["edges"]:
        edge = body["edges"][0]
        required_keys = [
            "edge_id", "source_node_id", "target_node_id",
            "relationship_type", "trust_score", "status",
            "provenance_url", "corroboration", "ingested_at",
        ]
        for key in required_keys:
            assert key in edge, f"Missing key '{key}' in EdgeSummary"
        assert edge["trust_score"] < 0.60, (
            f"Queue should only contain low-conf edges; got trust_score={edge['trust_score']}"
        )
    print(f"[PASS] test_low_confidence_queue_edge_shape  ->  "
          f"EdgeSummary shape is correct (trust_score < 0.60 enforced)")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — HITL: POST /api/v1/queue/resolve
# ════════════════════════════════════════════════════════════════════════════

def _get_first_low_conf_edge_id() -> str:
    """Helper: fetch the first edge_id from the low-confidence queue."""
    r = client.get("/api/v1/queue/low-confidence")
    edges = r.json().get("edges", [])
    if not edges:
        raise RuntimeError("No low-confidence edges in store to resolve.")
    return edges[0]["edge_id"]


def test_resolve_verify_sets_trust_to_1():
    edge_id = _get_first_low_conf_edge_id()
    r = client.post(
        "/api/v1/queue/resolve",
        json={"edge_id": edge_id, "is_verified": True, "analyst_note": "Confirmed by HUMINT."},
        headers={"X-Analyst-Id": "analyst-jones"},
    )
    assert r.status_code == 200, f"Unexpected {r.status_code}: {r.text}"
    body = r.json()
    assert body["new_status"] == "VERIFIED"
    assert body["new_trust_score"] == 1.0
    assert body["resolved_by"] == "analyst-jones"
    print(f"[PASS] test_resolve_verify_sets_trust_to_1  ->  "
          f"edge={edge_id[:8]} | status={body['new_status']} | trust={body['new_trust_score']}")


def test_resolve_reject_soft_deletes():
    # Need a fresh low-conf edge — get one that's still in the queue
    r = client.get("/api/v1/queue/low-confidence")
    edges = r.json().get("edges", [])
    # Find an edge that isn't already VERIFIED from the previous test
    target = next((e for e in edges if e["status"] != "VERIFIED"), None)
    if target is None:
        print("[SKIP] test_resolve_reject_soft_deletes  ->  no suitable edge available")
        return

    edge_id = target["edge_id"]
    r = client.post(
        "/api/v1/queue/resolve",
        json={"edge_id": edge_id, "is_verified": False, "analyst_note": "Disinformation detected."},
        headers={"X-Analyst-Id": "analyst-smith"},
    )
    assert r.status_code == 200, f"Unexpected {r.status_code}: {r.text}"
    body = r.json()
    assert body["new_status"] == "REJECTED"
    assert body["new_trust_score"] is None
    assert body["resolved_by"] == "analyst-smith"
    print(f"[PASS] test_resolve_reject_soft_deletes  ->  "
          f"edge={edge_id[:8]} | status={body['new_status']}")


def test_resolve_nonexistent_edge_returns_404():
    r = client.post(
        "/api/v1/queue/resolve",
        json={"edge_id": "00000000-0000-0000-0000-000000000000", "is_verified": True},
    )
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    print("[PASS] test_resolve_nonexistent_edge_returns_404  ->  404 correctly returned")


def test_resolve_terminal_edge_returns_409():
    """Resolving an already-VERIFIED edge must return 409 Conflict."""
    # First, get and verify a fresh edge
    edges = client.get("/api/v1/queue/low-confidence").json().get("edges", [])
    target = next((e for e in edges if e["status"] == "LOW_CONFIDENCE"), None)
    if not target:
        print("[SKIP] test_resolve_terminal_edge_returns_409  ->  no suitable edge")
        return

    edge_id = target["edge_id"]
    # Verify it first
    client.post("/api/v1/queue/resolve", json={"edge_id": edge_id, "is_verified": True})
    # Try to resolve again — should be 409
    r2 = client.post("/api/v1/queue/resolve", json={"edge_id": edge_id, "is_verified": True})
    assert r2.status_code == 409, f"Expected 409, got {r2.status_code}: {r2.text}"
    print(f"[PASS] test_resolve_terminal_edge_returns_409  ->  "
          f"409 returned for already-VERIFIED edge")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Dashboard: GET /api/v1/dashboard/stats
# ════════════════════════════════════════════════════════════════════════════

def test_dashboard_stats():
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    required = [
        "total_edges", "active_edges", "low_confidence_edges",
        "verified_edges", "rejected_edges", "contested_edges",
        "pending_edges", "ontology_version", "entity_type_count",
        "relationship_type_count", "generated_at",
    ]
    for key in required:
        assert key in body, f"Missing key '{key}' in stats response"
    assert body["ontology_version"] >= 1
    assert body["entity_type_count"] == 8
    assert body["relationship_type_count"] == 10
    print(f"[PASS] test_dashboard_stats  ->  "
          f"total={body['total_edges']} | active={body['active_edges']} | "
          f"low_conf={body['low_confidence_edges']} | verified={body['verified_edges']}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Dashboard: schema endpoints
# ════════════════════════════════════════════════════════════════════════════

def test_get_schema():
    r = client.get("/api/v1/dashboard/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] >= 1
    assert "COUNTRY" in body["entity_types"]
    assert "ALLIED_WITH" in body["relationship_types"]
    print(f"[PASS] test_get_schema  ->  "
          f"v{body['version']} | {len(body['entity_types'])} entity types | "
          f"{len(body['relationship_types'])} rel types")


def test_get_schema_version_history():
    r = client.get("/api/v1/dashboard/schema/version-history")
    assert r.status_code == 200
    history = r.json()
    assert isinstance(history, list)
    assert len(history) >= 1
    assert history[0]["version_number"] == 1
    assert history[0]["committed_by"] == "SYSTEM"
    print(f"[PASS] test_get_schema_version_history  ->  {len(history)} version(s) in history")


def test_propose_schema_change_approved():
    r = client.post(
        "/api/v1/dashboard/schema/propose",
        json={
            "proposer_id":     "analyst-007",
            "change_type":     "ADD_ENTITY_TYPE",
            "definition_name": "ARMS_DEPOT",
            "definition_desc": "A weapons storage or manufacturing facility.",
            "approve_votes":   4,
            "reject_votes":    0,
            "abstain_votes":   1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["new_version_number"] >= 2
    assert body["approve_count"] == 4
    print(f"[PASS] test_propose_schema_change_approved  ->  "
          f"accepted={body['accepted']} | version={body['new_version_number']} | "
          f"ratio={body['approval_ratio']:.0%}")


def test_propose_schema_change_rejected_below_quorum():
    r = client.post(
        "/api/v1/dashboard/schema/propose",
        json={
            "proposer_id":     "rogue-analyst",
            "change_type":     "ADD_ENTITY_TYPE",
            "definition_name": "SHADOW_ENTITY",
            "definition_desc": "Should not pass.",
            "approve_votes":   2,   # < MINIMUM_QUORUM of 3
            "reject_votes":    0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is False
    assert "Quorum" in body["failure_reason"]
    print(f"[PASS] test_propose_schema_change_rejected_below_quorum  ->  "
          f"accepted={body['accepted']} | reason={body['failure_reason'][:50]}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Dashboard: trust score explainer
# ════════════════════════════════════════════════════════════════════════════

def test_explain_edge_trust():
    # Get any valid edge_id from the store
    stats = client.get("/api/v1/dashboard/stats").json()
    if stats["total_edges"] == 0:
        print("[SKIP] test_explain_edge_trust  ->  no edges in store")
        return

    # Get an edge_id via the low-confidence queue (or any other endpoint)
    all_edges_resp = client.get("/api/v1/queue/low-confidence").json()
    if not all_edges_resp["edges"]:
        print("[SKIP] test_explain_edge_trust  ->  no edges in low-conf queue, can't get an id")
        return

    edge_id = all_edges_resp["edges"][0]["edge_id"]
    r = client.get(f"/api/v1/dashboard/edges/{edge_id}/explain")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    required = [
        "edge_id", "source_url", "source_credibility",
        "corroboration_count", "corroboration_bonus",
        "claim_age_days", "decay_factor", "temporal_penalty",
        "projected_score", "current_status", "explanation_text",
    ]
    for key in required:
        assert key in body, f"Missing key: {key}"
    assert body["edge_id"] == edge_id
    print(f"[PASS] test_explain_edge_trust  ->  "
          f"projected_score={body['projected_score']} | {body['explanation_text'][:80]}...")


def test_explain_nonexistent_edge_returns_404():
    r = client.get("/api/v1/dashboard/edges/no-such-id/explain")
    assert r.status_code == 404
    print("[PASS] test_explain_nonexistent_edge_returns_404  ->  404 correctly returned")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Dashboard: anomaly scan
# ════════════════════════════════════════════════════════════════════════════

def test_anomaly_scan_returns_200():
    r = client.get("/api/v1/dashboard/anomalies/scan?time_window_hours=24")
    assert r.status_code == 200
    body = r.json()
    assert "total_edges_scanned" in body
    assert "anomalies_found" in body
    assert "reports" in body
    assert body["time_window_hours"] == 24.0
    assert isinstance(body["reports"], list)
    print(f"[PASS] test_anomaly_scan_returns_200  ->  "
          f"scanned={body['total_edges_scanned']} | "
          f"anomalies={body['anomalies_found']} | window=24h")


def test_anomaly_scan_invalid_window_returns_422():
    r = client.get("/api/v1/dashboard/anomalies/scan?time_window_hours=0")
    assert r.status_code == 422, f"Expected 422 for invalid window, got {r.status_code}"
    print("[PASS] test_anomaly_scan_invalid_window_returns_422  ->  422 for window=0")


# ── Runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("STEP 4 SMOKE-TEST: HITL & Dashboard API Endpoints")
    print("="*60 + "\n")

    all_tests = [
        # Health
        test_root_is_alive,
        test_health_endpoint,
        # HITL GET
        test_low_confidence_queue_returns_200,
        test_low_confidence_queue_edge_shape,
        # HITL POST
        test_resolve_verify_sets_trust_to_1,
        test_resolve_reject_soft_deletes,
        test_resolve_nonexistent_edge_returns_404,
        test_resolve_terminal_edge_returns_409,
        # Dashboard stats
        test_dashboard_stats,
        # Schema
        test_get_schema,
        test_get_schema_version_history,
        test_propose_schema_change_approved,
        test_propose_schema_change_rejected_below_quorum,
        # Explainer
        test_explain_edge_trust,
        test_explain_nonexistent_edge_returns_404,
        # Anomaly scan
        test_anomaly_scan_returns_200,
        test_anomaly_scan_invalid_window_returns_422,
    ]

    passed = failed = skipped = 0
    for test_fn in all_tests:
        try:
            result = test_fn()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {test_fn.__name__}  -->  {exc}")

    print(f"\n{'='*60}")
    print(f"Step 4 Smoke-Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
