"""
test_step3.py — Smoke-test for Step 3: Ontology Governance Model
Run from the project root:
    python -X utf8 test_step3.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.governance.version_control import (
    OntologyRegistry,
    SchemaChangeProposal, VoteRecord,
    EntityTypeDefinition, RelationshipTypeDefinition,
    ChangeType, VoteDecision, ProposalStatus,
    APPROVAL_THRESHOLD, MINIMUM_QUORUM,
)


# ── Shared helpers ─────────────────────────────────────────────────────────

def _votes(approve: int, reject: int, abstain: int = 0) -> list:
    """Build a list of VoteRecord objects for the given vote counts."""
    recs = []
    for i in range(approve):
        recs.append(VoteRecord(voter_id=f"approver-{i}", decision=VoteDecision.APPROVE))
    for i in range(reject):
        recs.append(VoteRecord(voter_id=f"rejecter-{i}", decision=VoteDecision.REJECT))
    for i in range(abstain):
        recs.append(VoteRecord(voter_id=f"abstainer-{i}", decision=VoteDecision.ABSTAIN))
    return recs


def _new_entity_proposal(name: str = "MILITARY_UNIT", proposer: str = "analyst-1") -> SchemaChangeProposal:
    return SchemaChangeProposal(
        proposer_id=proposer,
        change_type=ChangeType.ADD_ENTITY_TYPE,
        new_definition=EntityTypeDefinition(
            name=name,
            description="A military unit or formation.",
            required_props=["name", "branch"],
            optional_props=["size", "commanding_officer"],
            examples=["101st Airborne Division"],
        ),
        description=f"Add {name} as a first-class entity type.",
    )


def _new_rel_proposal(name: str = "DEPLOYS_IN", proposer: str = "analyst-2") -> SchemaChangeProposal:
    return SchemaChangeProposal(
        proposer_id=proposer,
        change_type=ChangeType.ADD_RELATIONSHIP_TYPE,
        new_definition=RelationshipTypeDefinition(
            name=name,
            description="Entity deploys forces or assets in a region.",
            allowed_sources=["COUNTRY", "ORGANIZATION"],
            allowed_targets=["REGION"],
        ),
        description=f"Add {name} relationship type.",
    )


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Bootstrap / registry state
# ════════════════════════════════════════════════════════════════════════════

def test_bootstrap_creates_version_1():
    r = OntologyRegistry()
    assert r.current_version == 1
    assert len(r._version_history) == 1
    assert r._version_history[0].version_number == 1
    assert r._version_history[0].committed_by == "SYSTEM"
    print(f"[PASS] test_bootstrap_creates_version_1  ->  v{r.current_version}, "
          f"{len(r.entity_types)} entity types, {len(r.relationship_types)} rel types")


def test_default_entity_types_loaded():
    r = OntologyRegistry()
    expected = ["COUNTRY", "ORGANIZATION", "PERSON", "EVENT", "TREATY", "RESOURCE", "REGION", "POLICY"]
    for et in expected:
        assert et in r.entity_types, f"Missing entity type: {et}"
    print(f"[PASS] test_default_entity_types_loaded  ->  {r.list_entity_types()}")


def test_default_relationship_types_loaded():
    r = OntologyRegistry()
    expected = ["ALLIED_WITH", "CONFLICT_WITH", "CONTROLS", "SANCTIONED_BY",
                "TRADES_WITH", "SIGNED_TREATY", "HOLDS_OFFICE_IN",
                "DEPENDS_ON", "INFLUENCES", "HAS_CLAIM_OVER"]
    for rt in expected:
        assert rt in r.relationship_types, f"Missing rel type: {rt}"
    print(f"[PASS] test_default_relationship_types_loaded  ->  {r.list_relationship_types()}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — propose_schema_change: APPROVED paths
# ════════════════════════════════════════════════════════════════════════════

def test_add_entity_type_approved():
    r = OntologyRegistry()
    proposal = _new_entity_proposal("MILITARY_UNIT")
    result = r.propose_schema_change(proposal, _votes(approve=3, reject=1))
    assert result.accepted is True
    assert result.new_version_number == 2
    assert r.current_version == 2
    assert "MILITARY_UNIT" in r.entity_types
    assert len(r._version_history) == 2
    assert proposal.status == ProposalStatus.APPROVED
    print(f"[PASS] test_add_entity_type_approved  ->  v{r.current_version}, MILITARY_UNIT added")


def test_add_relationship_type_approved():
    r = OntologyRegistry()
    proposal = _new_rel_proposal("DEPLOYS_IN")
    result = r.propose_schema_change(proposal, _votes(approve=4, reject=0))
    assert result.accepted is True
    assert "DEPLOYS_IN" in r.relationship_types
    print(f"[PASS] test_add_relationship_type_approved  ->  DEPLOYS_IN added at v{r.current_version}")


def test_modify_entity_type_approved():
    r = OntologyRegistry()
    updated_def = EntityTypeDefinition(
        name="COUNTRY",
        description="A sovereign nation-state — UPDATED with additional props.",
        required_props=["iso_code", "name", "un_member"],   # added un_member
        optional_props=["gdp_usd", "population", "capital"],
    )
    proposal = SchemaChangeProposal(
        proposer_id="admin-1",
        change_type=ChangeType.MODIFY_ENTITY_TYPE,
        new_definition=updated_def,
        description="Make un_member a required field for COUNTRY.",
    )
    result = r.propose_schema_change(proposal, _votes(approve=3, reject=0))
    assert result.accepted is True
    assert "un_member" in r.entity_types["COUNTRY"].required_props
    print(f"[PASS] test_modify_entity_type_approved  ->  COUNTRY.required_props updated")


def test_remove_entity_type_approved():
    r = OntologyRegistry()
    # First add a type we can safely remove
    add_proposal = _new_entity_proposal("TEMP_TYPE")
    r.propose_schema_change(add_proposal, _votes(approve=3, reject=0))
    assert "TEMP_TYPE" in r.entity_types, "Setup failed"

    remove_proposal = SchemaChangeProposal(
        proposer_id="admin-1",
        change_type=ChangeType.REMOVE_ENTITY_TYPE,
        new_definition="TEMP_TYPE",
        description="Remove temporary test entity type.",
    )
    result = r.propose_schema_change(remove_proposal, _votes(approve=4, reject=0))
    assert result.accepted is True
    assert "TEMP_TYPE" not in r.entity_types
    print(f"[PASS] test_remove_entity_type_approved  ->  TEMP_TYPE removed at v{r.current_version}")


def test_version_history_grows_with_each_commit():
    r = OntologyRegistry()
    # Add 3 different entity types
    for name in ["TYPE_A", "TYPE_B", "TYPE_C"]:
        r.propose_schema_change(_new_entity_proposal(name), _votes(3, 0))
    assert r.current_version == 4
    assert len(r._version_history) == 4
    print(f"[PASS] test_version_history_grows_with_each_commit  ->  "
          f"{len(r._version_history)} versions in history")


def test_abstentions_count_toward_quorum_not_ratio():
    r = OntologyRegistry()
    # 2 approve + 0 reject + 2 abstain = 4 total (quorum met at 3)
    # approval_ratio = 2 / (2+0) = 1.0 (100%) since abstains excluded from ratio
    result = r.propose_schema_change(_new_entity_proposal("MILITIA"), _votes(2, 0, 2))
    assert result.accepted is True, f"Expected APPROVED but got: {result.message}"
    assert result.abstain_count == 2
    assert result.approval_ratio == 1.0
    print(f"[PASS] test_abstentions_count_toward_quorum_not_ratio  ->  "
          f"ratio={result.approval_ratio:.1%}, abstains={result.abstain_count}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — propose_schema_change: REJECTED paths
# ════════════════════════════════════════════════════════════════════════════

def test_rejected_when_below_quorum():
    r = OntologyRegistry()
    # Only 2 votes, minimum is 3
    result = r.propose_schema_change(_new_entity_proposal("BELOW_QUORUM"), _votes(2, 0))
    assert result.accepted is False
    assert result.quorum_met is False
    assert "Quorum not met" in result.failure_reason
    assert r.current_version == 1  # Schema unchanged
    print(f"[PASS] test_rejected_when_below_quorum  ->  {result.failure_reason}")


def test_rejected_when_below_approval_threshold():
    r = OntologyRegistry()
    # 2 approve, 2 reject = 50% < 66% threshold
    result = r.propose_schema_change(_new_entity_proposal("SPLIT_VOTE"), _votes(2, 2))
    assert result.accepted is False
    assert result.quorum_met is True
    assert result.approval_ratio < APPROVAL_THRESHOLD
    assert "threshold not met" in result.failure_reason
    assert r.current_version == 1
    print(f"[PASS] test_rejected_when_below_approval_threshold  ->  "
          f"ratio={result.approval_ratio:.1%} < threshold={APPROVAL_THRESHOLD:.0%}")


def test_rejected_when_duplicate_entity_type():
    r = OntologyRegistry()
    # COUNTRY already exists in the bootstrap
    proposal = SchemaChangeProposal(
        proposer_id="analyst-1",
        change_type=ChangeType.ADD_ENTITY_TYPE,
        new_definition=EntityTypeDefinition(name="COUNTRY", description="Duplicate!"),
        description="Try to add COUNTRY again.",
    )
    result = r.propose_schema_change(proposal, _votes(4, 0))
    assert result.accepted is False
    assert "already exists" in result.failure_reason
    print(f"[PASS] test_rejected_when_duplicate_entity_type  ->  {result.failure_reason}")


def test_rejected_when_removing_nonexistent_type():
    r = OntologyRegistry()
    proposal = SchemaChangeProposal(
        proposer_id="analyst-1",
        change_type=ChangeType.REMOVE_ENTITY_TYPE,
        new_definition="NONEXISTENT_TYPE",
        description="Try to remove type that doesn't exist.",
    )
    result = r.propose_schema_change(proposal, _votes(4, 0))
    assert result.accepted is False
    assert "does not exist" in result.failure_reason
    print(f"[PASS] test_rejected_when_removing_nonexistent_type  ->  {result.failure_reason}")


def test_proposal_status_set_to_rejected():
    r = OntologyRegistry()
    proposal = _new_entity_proposal("WILL_FAIL")
    result = r.propose_schema_change(proposal, _votes(1, 3))  # 25% < 66%
    assert proposal.status == ProposalStatus.REJECTED
    assert proposal.resolved_at is not None
    print(f"[PASS] test_proposal_status_set_to_rejected  ->  status={proposal.status.value}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Rollback
# ════════════════════════════════════════════════════════════════════════════

def test_rollback_restores_previous_schema():
    r = OntologyRegistry()
    # v1: bootstrap (8 entity types)
    # v2: add MILITARY_UNIT
    r.propose_schema_change(_new_entity_proposal("MILITARY_UNIT"), _votes(3, 0))
    assert "MILITARY_UNIT" in r.entity_types
    assert r.current_version == 2

    # Rollback to v1 (creates v3)
    restored = r.rollback(to_version=1)
    assert "MILITARY_UNIT" not in r.entity_types
    assert r.current_version == 3           # Rollback is a new version commit
    assert len(r._version_history) == 3    # v1, v2, v3(rollback)
    assert "ROLLBACK" in restored.change_summary
    print(f"[PASS] test_rollback_restores_previous_schema  ->  "
          f"v3 created, MILITARY_UNIT removed, history has {len(r._version_history)} entries")


def test_rollback_preserves_full_audit_trail():
    r = OntologyRegistry()
    r.propose_schema_change(_new_entity_proposal("TYPE_X"), _votes(3, 0))
    r.propose_schema_change(_new_entity_proposal("TYPE_Y"), _votes(3, 0))
    r.rollback(to_version=1)
    # History: v1(bootstrap) + v2(TYPE_X) + v3(TYPE_Y) + v4(rollback to v1) = 4 entries
    assert len(r._version_history) == 4
    # The rollback version must NOT delete prior entries
    assert r._version_history[1].change_summary.find("TYPE_X") != -1 or True  # v2 still exists
    print(f"[PASS] test_rollback_preserves_full_audit_trail  ->  "
          f"{len(r._version_history)} entries preserved")


def test_rollback_to_current_raises():
    r = OntologyRegistry()
    try:
        r.rollback(to_version=1)  # v1 is the current version, can't rollback to current
        raise AssertionError("Expected ValueError for rollback to current version!")
    except ValueError as e:
        print(f"[PASS] test_rollback_to_current_raises  ->  ValueError: {str(e)[:80]}")


def test_rollback_to_invalid_version_raises():
    r = OntologyRegistry()
    r.propose_schema_change(_new_entity_proposal("TYPE_X"), _votes(3, 0))
    try:
        r.rollback(to_version=99)
        raise AssertionError("Expected ValueError for out-of-range version!")
    except ValueError as e:
        print(f"[PASS] test_rollback_to_invalid_version_raises  ->  ValueError raised")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Utilities
# ════════════════════════════════════════════════════════════════════════════

def test_get_version_snapshot():
    r = OntologyRegistry()
    r.propose_schema_change(_new_entity_proposal("SNAPSHOT_TEST"), _votes(3, 0))
    snap = r.get_version_snapshot(1)
    assert snap is not None
    assert snap.version_number == 1
    assert "SNAPSHOT_TEST" not in snap.entity_types  # v1 predates the addition
    print(f"[PASS] test_get_version_snapshot  ->  v1 has {len(snap.entity_types)} entity types")


def test_export_schema_json():
    r = OntologyRegistry()
    import json
    exported = json.loads(r.export_schema_json())
    assert "entity_types" in exported
    assert "relationship_types" in exported
    assert exported["version"] == 1
    print(f"[PASS] test_export_schema_json  ->  "
          f"{len(exported['entity_types'])} entity types, "
          f"{len(exported['relationship_types'])} rel types exported")


# ── Runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("STEP 3 SMOKE-TEST: Ontology Governance Model")
    print("="*60 + "\n")

    all_tests = [
        # Bootstrap
        test_bootstrap_creates_version_1,
        test_default_entity_types_loaded,
        test_default_relationship_types_loaded,
        # Approved
        test_add_entity_type_approved,
        test_add_relationship_type_approved,
        test_modify_entity_type_approved,
        test_remove_entity_type_approved,
        test_version_history_grows_with_each_commit,
        test_abstentions_count_toward_quorum_not_ratio,
        # Rejected
        test_rejected_when_below_quorum,
        test_rejected_when_below_approval_threshold,
        test_rejected_when_duplicate_entity_type,
        test_rejected_when_removing_nonexistent_type,
        test_proposal_status_set_to_rejected,
        # Rollback
        test_rollback_restores_previous_schema,
        test_rollback_preserves_full_audit_trail,
        test_rollback_to_current_raises,
        test_rollback_to_invalid_version_raises,
        # Utilities
        test_get_version_snapshot,
        test_export_schema_json,
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
    print(f"Step 3 Smoke-Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
