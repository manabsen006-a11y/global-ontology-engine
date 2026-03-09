"""
app/governance/version_control.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global Ontology Engine — Ontology Governance & Schema Version Control
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This module implements the governance layer for the Knowledge Graph's own
schema — who gets to add new entity types and relationship definitions, under
what conditions, and with full auditability.

Core concepts:
  • OntologyRegistry   — the live, versioned dictionary of accepted entity
                         types and relationship definitions.
  • SchemaVersion      — a complete, immutable snapshot of the ontology at a
                         point in time.  Each commit creates a new version.
  • SchemaChangeProposal — a pending change submitted for committee review.
  • propose_schema_change() — the governance gate: a proposed change is only
                              committed if committee votes meet the threshold.
  • rollback()         — revert the registry to any previous version by
                         version number (full audit trail preserved).

Governance model:
  ┌────────────────────────────────────────────────────────────────┐
  │  Researcher submits SchemaChangeProposal                       │
  │       ↓                                                        │
  │  Committee members cast VoteRecord votes (APPROVE / REJECT)    │
  │       ↓                                                        │
  │  propose_schema_change() tallies votes:                        │
  │    approval_ratio = approvals / total_cast                     │
  │    if approval_ratio >= APPROVAL_THRESHOLD (0.66):             │
  │       → commit new SchemaVersion,  bump version number         │
  │    else:                                                        │
  │       → reject, log, keep current version                      │
  │       ↓                                                        │
  │  Previous version stored in `_version_history` for rollback    │
  └────────────────────────────────────────────────────────────────┘

Persistence plug-in point:
  The registry currently stores versions in memory.  To persist to disk or a
  database, override `_save_version()` and `_load_versions()` in a subclass,
  or swap the `_version_history` list for a SQLAlchemy model / Redis list.
"""

from __future__ import annotations

import copy
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Module logger
# ─────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# ─────────────────────────────────────────────────────────────────────────────
# Governance configuration
# ─────────────────────────────────────────────────────────────────────────────

# Minimum share of cast votes that must be APPROVE for a change to pass.
# 0.66 ≈ two-thirds majority (default UN Security Council style threshold).
APPROVAL_THRESHOLD: float = 0.66

# Minimum number of votes that must be cast for a vote to be valid.
# Prevents a single rogue voter from changing the ontology.
MINIMUM_QUORUM: int = 3


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class ChangeType(str, Enum):
    """The type of schema modification being proposed."""
    ADD_ENTITY_TYPE       = "ADD_ENTITY_TYPE"
    REMOVE_ENTITY_TYPE    = "REMOVE_ENTITY_TYPE"
    ADD_RELATIONSHIP_TYPE = "ADD_RELATIONSHIP_TYPE"
    REMOVE_RELATIONSHIP_TYPE = "REMOVE_RELATIONSHIP_TYPE"
    MODIFY_ENTITY_TYPE    = "MODIFY_ENTITY_TYPE"
    MODIFY_RELATIONSHIP_TYPE = "MODIFY_RELATIONSHIP_TYPE"


class VoteDecision(str, Enum):
    """A committee member's ballot decision."""
    APPROVE = "APPROVE"
    REJECT  = "REJECT"
    ABSTAIN = "ABSTAIN"  # Counted in quorum but not in approval ratio


class ProposalStatus(str, Enum):
    """Lifecycle status of a SchemaChangeProposal."""
    PENDING   = "PENDING"    # Awaiting votes
    APPROVED  = "APPROVED"   # Passed and committed
    REJECTED  = "REJECTED"   # Failed vote threshold
    WITHDRAWN = "WITHDRAWN"  # Proposer withdrew before vote


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EntityTypeDefinition:
    """
    Full definition of a node/entity type in the ontology.

    Attributes:
        name:           Controlled vocabulary name (e.g., "COUNTRY").
        description:    Human-readable explanation of what this entity represents.
        required_props: Property keys that every node of this type MUST carry.
        optional_props: Property keys that nodes of this type MAY carry.
        examples:       Canonical example entity names for documentation.
    """
    name:           str
    description:    str
    required_props: List[str] = field(default_factory=list)
    optional_props: List[str] = field(default_factory=list)
    examples:       List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "description":    self.description,
            "required_props": self.required_props,
            "optional_props": self.optional_props,
            "examples":       self.examples,
        }


@dataclass
class RelationshipTypeDefinition:
    """
    Full definition of a directed edge/relationship type in the ontology.

    Attributes:
        name:            Controlled vocabulary name (e.g., "ALLIED_WITH").
        description:     Human-readable meaning of this relationship.
        allowed_sources: List of entity types that may appear as source nodes.
        allowed_targets: List of entity types that may appear as target nodes.
        is_symmetric:    True if A→B implies B→A (e.g., ALLIED_WITH).
        properties:      Optional metadata keys carried on edges of this type.
    """
    name:            str
    description:     str
    allowed_sources: List[str] = field(default_factory=list)
    allowed_targets: List[str] = field(default_factory=list)
    is_symmetric:    bool = False
    properties:      List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":            self.name,
            "description":     self.description,
            "allowed_sources": self.allowed_sources,
            "allowed_targets": self.allowed_targets,
            "is_symmetric":    self.is_symmetric,
            "properties":      self.properties,
        }


@dataclass
class VoteRecord:
    """
    A single committee member's vote on a schema change proposal.

    Attributes:
        voter_id:   Unique identifier of the committee member (username or UUID).
        decision:   APPROVE, REJECT, or ABSTAIN.
        rationale:  Optional free-text reasoning provided by the voter.
        cast_at:    UTC time the vote was recorded.
    """
    voter_id:  str
    decision:  VoteDecision
    rationale: Optional[str] = None
    cast_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SchemaVersion:
    """
    An immutable snapshot of the full ontology schema at a specific version.

    Stored in `OntologyRegistry._version_history` to enable rollback.
    Each commit increments `version_number` by 1 from the previous version.

    Attributes:
        version_number:    Monotonically increasing integer (starts at 1).
        version_id:        UUID-4 string uniquely identifying this snapshot.
        entity_types:      Dict mapping type name → EntityTypeDefinition.
        relationship_types: Dict mapping type name → RelationshipTypeDefinition.
        committed_at:      UTC time of this version's commit.
        committed_by:      Proposer who submitted the change.
        change_summary:    Human-readable description of what changed.
        proposal_id:       ID of the SchemaChangeProposal that triggered this commit.
        approval_ratio:    Recorded approval ratio at time of commit.
    """
    version_number:     int
    version_id:         str
    entity_types:       Dict[str, EntityTypeDefinition]
    relationship_types: Dict[str, RelationshipTypeDefinition]
    committed_at:       datetime
    committed_by:       str
    change_summary:     str
    proposal_id:        str
    approval_ratio:     float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this version to a JSON-safe dictionary (for persistence)."""
        return {
            "version_number":     self.version_number,
            "version_id":         self.version_id,
            "entity_types":       {k: v.to_dict() for k, v in self.entity_types.items()},
            "relationship_types": {k: v.to_dict() for k, v in self.relationship_types.items()},
            "committed_at":       self.committed_at.isoformat(),
            "committed_by":       self.committed_by,
            "change_summary":     self.change_summary,
            "proposal_id":        self.proposal_id,
            "approval_ratio":     self.approval_ratio,
        }


@dataclass
class SchemaChangeProposal:
    """
    A formal request to modify the live ontology schema.

    Created by researchers/engineers and submitted to `propose_schema_change()`.

    Attributes:
        proposal_id:    UUID-4 identifier for this proposal.
        proposer_id:    Username or ID of the submitter.
        change_type:    Category of schema modification.
        new_definition: The EntityTypeDefinition or RelationshipTypeDefinition
                        to add/modify, or the string name of the type to remove.
        description:    Human-readable rationale for the proposed change.
        status:         Lifecycle status (PENDING → APPROVED / REJECTED).
        submitted_at:   UTC time of submission.
        resolved_at:    UTC time of final decision (None if still PENDING).
    """
    proposer_id:    str
    change_type:    ChangeType
    new_definition: Any    # EntityTypeDefinition | RelationshipTypeDefinition | str (for REMOVE)
    description:    str
    proposal_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    status:         ProposalStatus = ProposalStatus.PENDING
    submitted_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at:    Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# VoteResult helper
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VoteResult:
    """
    Structured outcome returned by `propose_schema_change()`.

    Attributes:
        accepted:          True if the change passed committee vote and was committed.
        proposal_id:       ID of the evaluated proposal.
        new_version_number: Version number of the committed schema (None if rejected).
        total_votes:       Total number of votes cast (including abstentions).
        approve_count:     Number of APPROVE votes.
        reject_count:      Number of REJECT votes.
        abstain_count:     Number of ABSTAIN votes.
        approval_ratio:    approve_count / (approve_count + reject_count).
        quorum_met:        True if vote count >= MINIMUM_QUORUM.
        failure_reason:    Human-readable reason if rejected (None if accepted).
        message:           Summary message for the dashboard.
    """
    accepted:           bool
    proposal_id:        str
    new_version_number: Optional[int]
    total_votes:        int
    approve_count:      int
    reject_count:       int
    abstain_count:      int
    approval_ratio:     float
    quorum_met:         bool
    failure_reason:     Optional[str]
    message:            str


# ─────────────────────────────────────────────────────────────────────────────
# OntologyRegistry — the main governance class
# ─────────────────────────────────────────────────────────────────────────────

class OntologyRegistry:
    """
    The authoritative, versioned repository of accepted entity types and
    relationship definitions for the Global Ontology Knowledge Graph.

    Lifecycle:
        registry = OntologyRegistry()           # Bootstrapped with defaults
        proposal = SchemaChangeProposal(...)     # Researcher proposes a change
        votes    = [VoteRecord(...), ...]        # Committee members vote
        result   = registry.propose_schema_change(proposal, votes)
        if result.accepted:
            print(f"Committed as version {result.new_version_number}")
        registry.rollback(to_version=1)          # Revert if needed

    Thread safety:
        This implementation is NOT thread-safe.  In production, wrap mutation
        methods with a `threading.Lock` or use a database-backed implementation.

    Persistence:
        To persist, override `_save_version()` to write each version snapshot
        to a database or JSON file.  On startup, call `_load_versions()` to
        restore from the persisted store.
    """

    def __init__(self) -> None:
        """
        Bootstrap the registry with the canonical set of entity types and
        relationship definitions defined in `ontology_models.py`.
        """
        # ── Active schema (mutable, always reflects current version) ───────
        self.entity_types:        Dict[str, EntityTypeDefinition]        = {}
        self.relationship_types:  Dict[str, RelationshipTypeDefinition]  = {}
        self._current_version:    int = 0

        # ── Immutable audit trail of all committed versions ─────────────────
        # Index 0 = the bootstrap (v1), index N-1 = latest version.
        self._version_history:    List[SchemaVersion] = []

        # ── Pending proposals (not yet resolved) ────────────────────────────
        self._proposals:          Dict[str, SchemaChangeProposal] = {}

        # Seed the registry with the default ontology.
        self._bootstrap_default_schema()

    # ── Bootstrapping ──────────────────────────────────────────────────────

    def _bootstrap_default_schema(self) -> None:
        """
        Load the canonical default entity and relationship types derived from
        the enumerations in `ontology_models.py`.  This creates version 1.
        """
        default_entities: Dict[str, EntityTypeDefinition] = {
            "COUNTRY": EntityTypeDefinition(
                name="COUNTRY",
                description="A sovereign nation-state recognised under international law.",
                required_props=["iso_code", "name"],
                optional_props=["gdp_usd", "population", "capital", "un_member"],
                examples=["United States", "Germany", "Japan"],
            ),
            "ORGANIZATION": EntityTypeDefinition(
                name="ORGANIZATION",
                description="An intergovernmental body, NGO, corporation, or military alliance.",
                required_props=["name", "org_type"],
                optional_props=["founding_year", "hq_country", "member_states"],
                examples=["NATO", "UN Security Council", "World Bank"],
            ),
            "PERSON": EntityTypeDefinition(
                name="PERSON",
                description="A named individual with geopolitical significance.",
                required_props=["name"],
                optional_props=["role", "nationality", "date_of_birth", "affiliation"],
                examples=["Angela Merkel", "Xi Jinping", "António Guterres"],
            ),
            "EVENT": EntityTypeDefinition(
                name="EVENT",
                description="A discrete geopolitical, economic, or military occurrence.",
                required_props=["name", "date"],
                optional_props=["location", "participants", "outcome"],
                examples=["2022 Russian Invasion of Ukraine", "G20 Summit 2023"],
            ),
            "TREATY": EntityTypeDefinition(
                name="TREATY",
                description="A formal binding agreement between two or more states.",
                required_props=["name", "signed_date"],
                optional_props=["parties", "ratification_date", "expiry_date"],
                examples=["Treaty of Lisbon", "Paris Climate Agreement"],
            ),
            "RESOURCE": EntityTypeDefinition(
                name="RESOURCE",
                description="A natural, energy, or economic resource of geopolitical significance.",
                required_props=["name", "resource_type"],
                optional_props=["global_reserve_pct", "major_producers"],
                examples=["Crude Oil", "Lithium", "Natural Gas"],
            ),
            "REGION": EntityTypeDefinition(
                name="REGION",
                description="A sub-national or trans-national geographic region.",
                required_props=["name"],
                optional_props=["parent_country", "geo_coordinates", "status"],
                examples=["Crimea", "Western Sahara", "South China Sea"],
            ),
            "POLICY": EntityTypeDefinition(
                name="POLICY",
                description="A formal government policy, doctrine, or legislative act.",
                required_props=["name", "issuing_entity"],
                optional_props=["effective_date", "scope", "status"],
                examples=["Monroe Doctrine", "Belt and Road Initiative"],
            ),
        }

        default_relationships: Dict[str, RelationshipTypeDefinition] = {
            "ALLIED_WITH": RelationshipTypeDefinition(
                name="ALLIED_WITH",
                description="Formal military or political alliance between two entities.",
                allowed_sources=["COUNTRY", "ORGANIZATION"],
                allowed_targets=["COUNTRY", "ORGANIZATION"],
                is_symmetric=True,
                properties=["treaty_ref", "since_date"],
            ),
            "CONTROLS": RelationshipTypeDefinition(
                name="CONTROLS",
                description="Entity exerts sovereign or de-facto administrative control.",
                allowed_sources=["COUNTRY", "ORGANIZATION", "PERSON"],
                allowed_targets=["REGION", "RESOURCE", "ORGANIZATION"],
                is_symmetric=False,
                properties=["since_date", "control_type"],
            ),
            "SANCTIONED_BY": RelationshipTypeDefinition(
                name="SANCTIONED_BY",
                description="Entity is subject to economic or diplomatic sanctions.",
                allowed_sources=["COUNTRY", "PERSON", "ORGANIZATION"],
                allowed_targets=["COUNTRY", "ORGANIZATION"],
                is_symmetric=False,
                properties=["sanction_type", "effective_date", "lifted_date"],
            ),
            "TRADES_WITH": RelationshipTypeDefinition(
                name="TRADES_WITH",
                description="Significant bilateral trade relationship exists.",
                allowed_sources=["COUNTRY"],
                allowed_targets=["COUNTRY"],
                is_symmetric=True,
                properties=["annual_volume_usd", "primary_goods"],
            ),
            "SIGNED_TREATY": RelationshipTypeDefinition(
                name="SIGNED_TREATY",
                description="Entity is a signatory to a treaty.",
                allowed_sources=["COUNTRY", "ORGANIZATION"],
                allowed_targets=["TREATY"],
                is_symmetric=False,
                properties=["signed_date", "ratified"],
            ),
            "HOLDS_OFFICE_IN": RelationshipTypeDefinition(
                name="HOLDS_OFFICE_IN",
                description="Person holds or held an official position within an entity.",
                allowed_sources=["PERSON"],
                allowed_targets=["COUNTRY", "ORGANIZATION"],
                is_symmetric=False,
                properties=["title", "since_date", "until_date"],
            ),
            "CONFLICT_WITH": RelationshipTypeDefinition(
                name="CONFLICT_WITH",
                description="Active armed conflict or state of war between entities.",
                allowed_sources=["COUNTRY", "ORGANIZATION"],
                allowed_targets=["COUNTRY", "ORGANIZATION"],
                is_symmetric=True,
                properties=["conflict_type", "start_date", "end_date", "casualties"],
            ),
            "DEPENDS_ON": RelationshipTypeDefinition(
                name="DEPENDS_ON",
                description="Entity is economically or strategically dependent on another.",
                allowed_sources=["COUNTRY", "ORGANIZATION"],
                allowed_targets=["COUNTRY", "RESOURCE", "ORGANIZATION"],
                is_symmetric=False,
                properties=["dependency_type", "dependency_pct"],
            ),
            "INFLUENCES": RelationshipTypeDefinition(
                name="INFLUENCES",
                description="Entity exerts significant political, economic, or cultural influence.",
                allowed_sources=["COUNTRY", "PERSON", "ORGANIZATION"],
                allowed_targets=["COUNTRY", "ORGANIZATION", "POLICY"],
                is_symmetric=False,
                properties=["influence_domain", "influence_score"],
            ),
            "HAS_CLAIM_OVER": RelationshipTypeDefinition(
                name="HAS_CLAIM_OVER",
                description="Entity asserts a territorial or resource claim (contested or uncontested).",
                allowed_sources=["COUNTRY", "ORGANIZATION"],
                allowed_targets=["REGION", "RESOURCE"],
                is_symmetric=False,
                properties=["claim_basis", "recognition_status"],
            ),
        }

        # Apply to live schema
        self.entity_types       = default_entities
        self.relationship_types = default_relationships
        self._current_version   = 1

        # Commit as the genesis version (no proposal, no votes required)
        genesis = SchemaVersion(
            version_number=1,
            version_id=str(uuid.uuid4()),
            entity_types=copy.deepcopy(self.entity_types),
            relationship_types=copy.deepcopy(self.relationship_types),
            committed_at=datetime.now(timezone.utc),
            committed_by="SYSTEM",
            change_summary="Bootstrap: canonical geopolitical ontology v1.0.",
            proposal_id="BOOTSTRAP",
            approval_ratio=1.0,
        )
        self._version_history.append(genesis)
        logger.info(
            "OntologyRegistry bootstrapped: v1 | %d entity types | %d relationship types.",
            len(self.entity_types), len(self.relationship_types),
        )

    # ── Public read API ────────────────────────────────────────────────────

    @property
    def current_version(self) -> int:
        """The monotonic version number of the currently active schema."""
        return self._current_version

    def get_entity_definition(self, name: str) -> Optional[EntityTypeDefinition]:
        """Look up an entity type definition by name. Returns None if not found."""
        return self.entity_types.get(name)

    def get_relationship_definition(self, name: str) -> Optional[RelationshipTypeDefinition]:
        """Look up a relationship type definition by name. Returns None if not found."""
        return self.relationship_types.get(name)

    def list_entity_types(self) -> List[str]:
        """Return a sorted list of all accepted entity type names."""
        return sorted(self.entity_types.keys())

    def list_relationship_types(self) -> List[str]:
        """Return a sorted list of all accepted relationship type names."""
        return sorted(self.relationship_types.keys())

    def get_version_history(self) -> List[Dict[str, Any]]:
        """
        Return the full version history as a list of serialisable dictionaries.
        Used by the Nexus dashboard's changelog panel.
        """
        return [v.to_dict() for v in self._version_history]

    def get_version_snapshot(self, version_number: int) -> Optional[SchemaVersion]:
        """
        Retrieve the schema snapshot for a specific version number.

        Args:
            version_number: 1-indexed version to retrieve.

        Returns:
            `SchemaVersion` or None if the version number is out of range.
        """
        if 1 <= version_number <= len(self._version_history):
            return self._version_history[version_number - 1]
        return None

    # ── Core governance method ─────────────────────────────────────────────

    def propose_schema_change(
        self,
        proposal: SchemaChangeProposal,
        committee_votes: List[VoteRecord],
    ) -> VoteResult:
        """
        Evaluate a schema change proposal against committee votes and, if the
        vote passes, commit the change as a new versioned schema snapshot.

        Governance rules (all must pass):
          1. QUORUM   — At least `MINIMUM_QUORUM` votes must be cast.
          2. MAJORITY — Approvals / (Approvals + Rejections) >= APPROVAL_THRESHOLD.
              (Abstentions count toward quorum but NOT toward the ratio.)
          3. VALIDITY — The proposed definition must be structurally sound
              (e.g., not a duplicate, not an attempt to remove a type still in use).

        If all rules pass:
          • The new definition/removal is applied to the live `entity_types` or
            `relationship_types` dictionary.
          • A new `SchemaVersion` snapshot is committed to `_version_history`.
          • The version number is incremented.
          • The proposal status is set to APPROVED.

        If any rule fails:
          • The live schema is NOT modified.
          • The proposal status is set to REJECTED.
          • The failure reason is returned in the `VoteResult`.

        Args:
            proposal:         A `SchemaChangeProposal` object submitted for review.
            committee_votes:  List of `VoteRecord` ballots from committee members.

        Returns:
            A `VoteResult` dataclass with full vote tally and outcome details.

        Side-effects:
            • Mutates `proposal.status` and `proposal.resolved_at`.
            • If approved: mutates `self.entity_types` / `self.relationship_types`
              and appends to `self._version_history`.
        """
        now_utc = datetime.now(timezone.utc)

        # Register the proposal (idempotent if already registered)
        self._proposals[proposal.proposal_id] = proposal

        # ── Step 1: Tally votes ────────────────────────────────────────────
        approve_count = sum(1 for v in committee_votes if v.decision == VoteDecision.APPROVE)
        reject_count  = sum(1 for v in committee_votes if v.decision == VoteDecision.REJECT)
        abstain_count = sum(1 for v in committee_votes if v.decision == VoteDecision.ABSTAIN)
        total_votes   = len(committee_votes)

        # Approval ratio only considers non-abstaining votes to prevent
        # mass abstention from gaming the threshold.
        decisive_votes = approve_count + reject_count
        approval_ratio = (approve_count / decisive_votes) if decisive_votes > 0 else 0.0

        logger.info(
            "propose_schema_change | proposal=%s | change=%s | "
            "votes: %d approve, %d reject, %d abstain | ratio=%.2f",
            proposal.proposal_id[:8], proposal.change_type.value,
            approve_count, reject_count, abstain_count, approval_ratio,
        )

        # ── Step 2: Quorum check ──────────────────────────────────────────
        quorum_met = total_votes >= MINIMUM_QUORUM
        if not quorum_met:
            failure_reason = (
                f"Quorum not met: {total_votes} vote(s) cast, "
                f"minimum required is {MINIMUM_QUORUM}."
            )
            return self._reject_proposal(
                proposal, now_utc, failure_reason,
                total_votes, approve_count, reject_count, abstain_count,
                approval_ratio, quorum_met=False,
            )

        # ── Step 3: Majority threshold check ──────────────────────────────
        if approval_ratio < APPROVAL_THRESHOLD:
            failure_reason = (
                f"Approval threshold not met: {approval_ratio:.1%} approval "
                f"({approve_count} of {decisive_votes} decisive votes). "
                f"Required: {APPROVAL_THRESHOLD:.1%}."
            )
            return self._reject_proposal(
                proposal, now_utc, failure_reason,
                total_votes, approve_count, reject_count, abstain_count,
                approval_ratio, quorum_met=True,
            )

        # ── Step 4: Structural validity check ────────────────────────────
        validity_error = self._validate_proposal(proposal)
        if validity_error:
            return self._reject_proposal(
                proposal, now_utc, f"Validation failed: {validity_error}",
                total_votes, approve_count, reject_count, abstain_count,
                approval_ratio, quorum_met=True,
            )

        # ── Step 5: All checks passed — commit the change ─────────────────
        self._apply_change(proposal)
        new_version_number = self._current_version

        # Build change summary for the changelog
        change_summary = (
            f"[{proposal.change_type.value}] by {proposal.proposer_id}: "
            f"{proposal.description} "
            f"(approved {approve_count}/{decisive_votes}, ratio={approval_ratio:.1%})"
        )

        # Snapshot the post-change schema and commit to history
        new_version = SchemaVersion(
            version_number=new_version_number,
            version_id=str(uuid.uuid4()),
            entity_types=copy.deepcopy(self.entity_types),
            relationship_types=copy.deepcopy(self.relationship_types),
            committed_at=now_utc,
            committed_by=proposal.proposer_id,
            change_summary=change_summary,
            proposal_id=proposal.proposal_id,
            approval_ratio=approval_ratio,
        )
        self._version_history.append(new_version)

        # Update proposal lifecycle
        proposal.status      = ProposalStatus.APPROVED
        proposal.resolved_at = now_utc

        message = (
            f"Schema change APPROVED and committed as version {new_version_number}. "
            f"Vote: {approve_count} approve, {reject_count} reject, "
            f"{abstain_count} abstain ({approval_ratio:.1%} approval)."
        )
        logger.info(
            "Schema change COMMITTED | version=%d | proposal=%s | %s",
            new_version_number, proposal.proposal_id[:8], change_summary,
        )

        return VoteResult(
            accepted=True,
            proposal_id=proposal.proposal_id,
            new_version_number=new_version_number,
            total_votes=total_votes,
            approve_count=approve_count,
            reject_count=reject_count,
            abstain_count=abstain_count,
            approval_ratio=approval_ratio,
            quorum_met=True,
            failure_reason=None,
            message=message,
        )

    # ── Rollback ──────────────────────────────────────────────────────────

    def rollback(self, to_version: int) -> SchemaVersion:
        """
        Revert the live schema to any previously committed version.

        The rollback itself is recorded as a NEW version (not a destructive
        rewrite) so that the full audit trail — including the decision to roll
        back — is preserved.

        Args:
            to_version: The version number to restore.  Must be in
                        [1, current_version - 1].

        Returns:
            The `SchemaVersion` that was restored (the new committed version).

        Raises:
            ValueError: If `to_version` is invalid or refers to the current version.
        """
        if to_version < 1 or to_version >= self._current_version:
            raise ValueError(
                f"Cannot rollback to version {to_version}. "
                f"Valid range is [1, {self._current_version - 1}]. "
                f"(Current version is {self._current_version}; "
                "rollback to the current version is a no-op.)"
            )

        target_snapshot = self._version_history[to_version - 1]

        # Restore the live schema from the snapshot's deep-copied data.
        self.entity_types       = copy.deepcopy(target_snapshot.entity_types)
        self.relationship_types = copy.deepcopy(target_snapshot.relationship_types)
        self._current_version  += 1

        rollback_version = SchemaVersion(
            version_number=self._current_version,
            version_id=str(uuid.uuid4()),
            entity_types=copy.deepcopy(self.entity_types),
            relationship_types=copy.deepcopy(self.relationship_types),
            committed_at=datetime.now(timezone.utc),
            committed_by="SYSTEM_ROLLBACK",
            change_summary=(
                f"ROLLBACK to v{to_version}: "
                f"'{target_snapshot.change_summary}'. "
                f"Previous version was v{self._current_version - 1}."
            ),
            proposal_id="ROLLBACK",
            approval_ratio=1.0,
        )
        self._version_history.append(rollback_version)

        logger.warning(
            "ROLLBACK | restored v%d -> new v%d | entity_types=%d | relationship_types=%d",
            to_version, self._current_version,
            len(self.entity_types), len(self.relationship_types),
        )

        return rollback_version

    # ── Internal helpers ──────────────────────────────────────────────────

    def _validate_proposal(self, proposal: SchemaChangeProposal) -> Optional[str]:
        """
        Run structural validation on a proposal before committing.

        Returns:
            None if valid, or an error string describing the problem.
        """
        ct = proposal.change_type

        if ct == ChangeType.ADD_ENTITY_TYPE:
            if not isinstance(proposal.new_definition, EntityTypeDefinition):
                return "ADD_ENTITY_TYPE requires an EntityTypeDefinition instance."
            if proposal.new_definition.name in self.entity_types:
                return (
                    f"Entity type '{proposal.new_definition.name}' already exists. "
                    "Use MODIFY_ENTITY_TYPE to update it."
                )

        elif ct == ChangeType.ADD_RELATIONSHIP_TYPE:
            if not isinstance(proposal.new_definition, RelationshipTypeDefinition):
                return "ADD_RELATIONSHIP_TYPE requires a RelationshipTypeDefinition instance."
            if proposal.new_definition.name in self.relationship_types:
                return (
                    f"Relationship type '{proposal.new_definition.name}' already exists. "
                    "Use MODIFY_RELATIONSHIP_TYPE to update it."
                )

        elif ct == ChangeType.REMOVE_ENTITY_TYPE:
            if not isinstance(proposal.new_definition, str):
                return "REMOVE_ENTITY_TYPE requires a string type name."
            if proposal.new_definition not in self.entity_types:
                return f"Entity type '{proposal.new_definition}' does not exist."

        elif ct == ChangeType.REMOVE_RELATIONSHIP_TYPE:
            if not isinstance(proposal.new_definition, str):
                return "REMOVE_RELATIONSHIP_TYPE requires a string type name."
            if proposal.new_definition not in self.relationship_types:
                return f"Relationship type '{proposal.new_definition}' does not exist."

        elif ct in (ChangeType.MODIFY_ENTITY_TYPE, ChangeType.MODIFY_RELATIONSHIP_TYPE):
            if not hasattr(proposal.new_definition, "name"):
                return f"{ct.value} requires a definition object with a 'name' attribute."

        return None  # Valid

    def _apply_change(self, proposal: SchemaChangeProposal) -> None:
        """
        Apply the validated schema change to the live dictionaries and
        increment the version counter.  Called only after all checks pass.
        """
        ct  = proposal.change_type
        new = proposal.new_definition

        if ct == ChangeType.ADD_ENTITY_TYPE:
            self.entity_types[new.name] = new

        elif ct == ChangeType.MODIFY_ENTITY_TYPE:
            self.entity_types[new.name] = new

        elif ct == ChangeType.REMOVE_ENTITY_TYPE:
            del self.entity_types[new]

        elif ct == ChangeType.ADD_RELATIONSHIP_TYPE:
            self.relationship_types[new.name] = new

        elif ct == ChangeType.MODIFY_RELATIONSHIP_TYPE:
            self.relationship_types[new.name] = new

        elif ct == ChangeType.REMOVE_RELATIONSHIP_TYPE:
            del self.relationship_types[new]

        self._current_version += 1

    def _reject_proposal(
        self,
        proposal: SchemaChangeProposal,
        now_utc: datetime,
        failure_reason: str,
        total_votes: int,
        approve_count: int,
        reject_count: int,
        abstain_count: int,
        approval_ratio: float,
        quorum_met: bool,
    ) -> VoteResult:
        """
        Mark a proposal as rejected and return a VoteResult with failure details.
        """
        proposal.status      = ProposalStatus.REJECTED
        proposal.resolved_at = now_utc

        message = (
            f"Schema change REJECTED. Reason: {failure_reason} "
            f"Vote: {approve_count} approve, {reject_count} reject, "
            f"{abstain_count} abstain."
        )
        logger.warning(
            "Schema change REJECTED | proposal=%s | reason=%s",
            proposal.proposal_id[:8], failure_reason,
        )

        return VoteResult(
            accepted=False,
            proposal_id=proposal.proposal_id,
            new_version_number=None,
            total_votes=total_votes,
            approve_count=approve_count,
            reject_count=reject_count,
            abstain_count=abstain_count,
            approval_ratio=approval_ratio,
            quorum_met=quorum_met,
            failure_reason=failure_reason,
            message=message,
        )

    # ── Persistence stubs (plug-in points) ────────────────────────────────

    def _save_version(self, version: SchemaVersion) -> None:
        """
        Persist a committed schema version to durable storage.

        Plug-in point: replace this stub with a real implementation:
            # Option A — JSON file
            with open(f"ontology_v{version.version_number}.json", "w") as f:
                json.dump(version.to_dict(), f, indent=2, default=str)

            # Option B — PostgreSQL via SQLAlchemy
            db.session.add(SchemaVersionORM(**version.to_dict()))
            db.session.commit()

            # Option C — Neo4j (store schema versions as graph nodes)
            session.run(
                "MERGE (v:SchemaVersion {version_id: $vid}) SET v += $props",
                vid=version.version_id, props=version.to_dict()
            )
        """
        logger.debug(
            "[_save_version STUB] Would persist v%d (%s).",
            version.version_number, version.version_id,
        )

    def _load_versions(self) -> List[SchemaVersion]:
        """
        Load previously committed schema versions from durable storage on startup.

        Plug-in point: replace this stub to hydrate `_version_history` from a
        database, JSON files, or a graph database query on startup.

        Returns:
            List of `SchemaVersion` objects (empty in mock mode).
        """
        logger.debug("[_load_versions STUB] No persistent store configured; returning empty.")
        return []

    def export_schema_json(self) -> str:
        """
        Export the current live schema as a formatted JSON string.
        Useful for schema diffing, documentation generation, or Neo4j imports.
        """
        snapshot = {
            "version":            self._current_version,
            "entity_types":       {k: v.to_dict() for k, v in self.entity_types.items()},
            "relationship_types": {k: v.to_dict() for k, v in self.relationship_types.items()},
            "exported_at":        datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(snapshot, indent=2, default=str)
