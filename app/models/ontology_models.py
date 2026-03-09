"""
app/models/ontology_models.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global Ontology Engine — Core Data Models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This module defines the canonical Pydantic v2 data structures used throughout
the Global Ontology Engine.  Every entity placed into the Knowledge Graph is
described by a `GraphNode`, every relationship by a `GraphEdge`, and every
piece of relationship metadata by a `ProvenanceMetadata` object.

Design principles:
  • Immutability by default  – models use `model_config = ConfigDict(frozen=True)`
    so that instances cannot be accidentally mutated after creation.
  • Strict validation      – all numeric fields carry explicit range validators
    so that corrupt data is rejected at the boundary.
  • Neo4j-ready            – string IDs are formatted as UUID-4 strings to
    serve as Neo4j `elementId` tags once the live driver is plugged in.
  • OpenAPI-compatible     – every field carries a `description` used by
    FastAPI's /docs UI.

Relationships to other modules:
  ┌─────────────────────────────────────────────────┐
  │  ontology_models.py  ←─ imported by:            │
  │    • services/provenance_engine.py               │
  │    • services/adversarial_detector.py            │
  │    • governance/version_control.py               │
  │    • api/hitl_routes.py                          │
  └─────────────────────────────────────────────────┘
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    """
    The set of first-class ontology entity types accepted by the registry.
    Extend via `OntologyRegistry.propose_schema_change()` in version_control.py.
    """
    COUNTRY        = "COUNTRY"
    ORGANIZATION   = "ORGANIZATION"
    PERSON         = "PERSON"
    EVENT          = "EVENT"
    TREATY         = "TREATY"
    RESOURCE       = "RESOURCE"
    REGION         = "REGION"
    POLICY         = "POLICY"


class RelationshipType(str, Enum):
    """
    Canonical edge/relationship types in the geopolitical knowledge graph.
    Every `GraphEdge` must carry one of these types.  New types must pass
    committee review through `OntologyRegistry.propose_schema_change()`.
    """
    ALLIED_WITH         = "ALLIED_WITH"
    CONTROLS            = "CONTROLS"
    SANCTIONED_BY       = "SANCTIONED_BY"
    TRADES_WITH         = "TRADES_WITH"
    SIGNED_TREATY       = "SIGNED_TREATY"
    HOLDS_OFFICE_IN     = "HOLDS_OFFICE_IN"
    CONFLICT_WITH       = "CONFLICT_WITH"
    DEPENDS_ON          = "DEPENDS_ON"
    INFLUENCES          = "INFLUENCES"
    HAS_CLAIM_OVER      = "HAS_CLAIM_OVER"


class EdgeStatus(str, Enum):
    """
    Lifecycle / epistemic status of a `GraphEdge`.

    PENDING           – freshly ingested, awaiting trust calculation.
    ACTIVE            – passed automated checks; used in queries.
    LOW_CONFIDENCE    – trust score < 0.60; queued for human review.
    CONTESTED_NARRATIVE – two source languages contradict each other.
    VERIFIED          – a human analyst has manually confirmed the edge.
    REJECTED          – deleted from active graph; retained for audit trail.
    """
    PENDING              = "PENDING"
    ACTIVE               = "ACTIVE"
    LOW_CONFIDENCE       = "LOW_CONFIDENCE"
    CONTESTED_NARRATIVE  = "CONTESTED_NARRATIVE"
    VERIFIED             = "VERIFIED"
    REJECTED             = "REJECTED"


class SourceType(str, Enum):
    """
    Category of the original data source that produced the relationship claim.
    Used by the Provenance Engine to inform baseline credibility expectations.
    """
    NEWS_ARTICLE     = "NEWS_ARTICLE"
    GOVERNMENT_DOC   = "GOVERNMENT_DOC"
    ACADEMIC_PAPER   = "ACADEMIC_PAPER"
    SOCIAL_MEDIA     = "SOCIAL_MEDIA"
    NGO_REPORT       = "NGO_REPORT"
    INTELLIGENCE_FEED = "INTELLIGENCE_FEED"
    SYNTHETIC        = "SYNTHETIC"          # LLM-generated / mock


# ─────────────────────────────────────────────────────────────────────────────
# ProvenanceMetadata
# ─────────────────────────────────────────────────────────────────────────────

class ProvenanceMetadata(BaseModel):
    """
    Provenance record attached to every `GraphEdge`.

    This object answers the questions:
      • WHERE did the claim come from?      → source_url, source_type
      • HOW credible is that source?        → source_credibility_score
      • HOW many sources agree?             → corroboration_count
      • WHEN was the claim made?            → timestamp
      • HOW much should age discount it?    → temporal_decay_factor

    The `temporal_decay_factor` is set by the ingestion pipeline based on the
    source type and age, but the `provenance_engine.calculate_dynamic_trust()`
    function is the single source of truth for the *final* trust score.
    """

    model_config = ConfigDict(frozen=True)  # Immutable after creation

    # ── Source identity ───────────────────────────────────────────────────
    source_url: str = Field(
        ...,
        description="Canonical URL or URN of the original source document.",
        examples=["https://reuters.com/article/xyz"],
    )
    source_type: SourceType = Field(
        default=SourceType.NEWS_ARTICLE,
        description="Category of the source (news, government, academic, …).",
    )
    author_or_outlet: Optional[str] = Field(
        default=None,
        description="Human-readable name of author, outlet, or agency.",
        examples=["Reuters", "Associated Press", "US State Department"],
    )

    # ── Credibility ───────────────────────────────────────────────────────
    source_credibility_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Credibility of the originating source on a [0.0, 1.0] scale. "
            "0.0 = completely unreliable / unknown, 1.0 = highest trust "
            "(e.g., peer-reviewed official government document)."
        ),
        examples=[0.85, 0.45, 0.10],
    )

    # ── Corroboration ─────────────────────────────────────────────────────
    corroboration_count: int = Field(
        default=1,
        ge=1,
        description=(
            "Number of independent sources that make the same relationship "
            "claim. Minimum is 1 (the source itself). Used by the trust "
            "function to apply a corroboration bonus."
        ),
        examples=[1, 3, 12],
    )

    # ── Temporality ───────────────────────────────────────────────────────
    timestamp: datetime = Field(
        ...,
        description=(
            "UTC datetime at which the source document was published or the "
            "claim was first recorded. Used to calculate temporal decay."
        ),
    )
    temporal_decay_factor: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description=(
            "Rate at which the trust score decays per day of age. "
            "A value of 0.01 means 1% per day. "
            "Set by the ingestion pipeline; higher for volatile claim types "
            "(e.g., battle-front positions) and lower for stable facts "
            "(e.g., treaty ratification dates)."
        ),
        examples=[0.01, 0.05, 0.001],
    )

    # ── Language & narrative ──────────────────────────────────────────────
    language_code: str = Field(
        default="en",
        min_length=2,
        max_length=5,
        description="ISO 639-1 / BCP-47 language code of the source document.",
        examples=["en", "zh", "ru", "ar"],
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v: Any) -> datetime:
        """
        Accept naive datetimes and treat them as UTC for consistency.
        If a timezone-aware datetime is provided, convert it to UTC.
        """
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        if isinstance(v, datetime):
            if v.tzinfo is None:
                # Treat naive datetimes as UTC
                return v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc)
        return v


# ─────────────────────────────────────────────────────────────────────────────
# GraphNode
# ─────────────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """
    Represents a vertex (entity) in the Global Ontology Knowledge Graph.

    In Neo4j this maps to a labelled node where:
      • `node_id`   → the node's UUID property / elementId
      • `node_type` → the primary Neo4j label
      • `name`      → the display / search name

    Example Neo4j Cypher equivalent:
        MERGE (n:COUNTRY {node_id: $node_id, name: $name})
        SET n += $properties
    """

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique UUID-4 identifier for this graph node.",
    )
    node_type: NodeType = Field(
        ...,
        description="Ontology-controlled entity type label.",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Human-readable canonical name for the entity.",
        examples=["United States", "NATO", "Vladimir Putin", "Treaty of Lisbon"],
    )
    aliases: List[str] = Field(
        default_factory=list,
        description=(
            "Alternative names, abbreviations, or transliterations for the "
            "entity. Used for cross-lingual entity resolution."
        ),
        examples=[["USA", "America", "US"]],
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Flexible property bag for type-specific attributes. "
            "E.g., for COUNTRY: {'iso_code': 'US', 'gdp_usd': 25e12}. "
            "Stored as JSON properties on the Neo4j node."
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this node record was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the last update to this node record.",
    )

    def neo4j_labels(self) -> List[str]:
        """
        Return the Neo4j labels to apply to this node.
        Always includes the canonical 'OntologyEntity' base label plus the
        specific `node_type` label for efficient label-based querying.

        Usage (when Neo4j driver is available):
            labels = node.neo4j_labels()  # → ["OntologyEntity", "COUNTRY"]
            # Pass to driver's create_node() call
        """
        return ["OntologyEntity", self.node_type.value]

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """
        Serialize this node to a flat dictionary suitable for Neo4j property
        setting. Nested dicts (properties bag) are JSON-encoded.

        Plug-in point: pass the returned dict to
            session.run("CREATE (n:OntologyEntity) SET n += $props", props=...)
        """
        import json
        return {
            "node_id":    self.node_id,
            "node_type":  self.node_type.value,
            "name":       self.name,
            "aliases":    self.aliases,
            "properties": json.dumps(self.properties),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# GraphEdge
# ─────────────────────────────────────────────────────────────────────────────

class GraphEdge(BaseModel):
    """
    Represents a directed relationship (edge) in the Knowledge Graph.

    Design notes:
      • Directed: source_node → [relationship_type] → target_node
      • Every edge carries a `ProvenanceMetadata` object (mandatory).
      • `trust_score` is computed lazily by `provenance_engine.calculate_dynamic_trust()`
        and written back; it starts as `None` until first calculation.
      • `status` is managed by the lifecycle pipeline:
          ingestion → PENDING → (trust engine) → ACTIVE or LOW_CONFIDENCE
                                               → (human review) → VERIFIED / REJECTED

    Neo4j Cypher equivalent:
        MATCH (s:OntologyEntity {node_id: $source_id})
        MATCH (t:OntologyEntity {node_id: $target_id})
        MERGE (s)-[r:ALLIED_WITH {edge_id: $edge_id}]->(t)
        SET r += $edge_properties
    """

    model_config = ConfigDict(frozen=False)  # Mutable: trust_score and status updated in-place

    edge_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique UUID-4 identifier for this graph edge.",
    )

    # ── Topology ──────────────────────────────────────────────────────────
    source_node_id: str = Field(
        ...,
        description="UUID of the source (head) GraphNode.",
    )
    target_node_id: str = Field(
        ...,
        description="UUID of the target (tail) GraphNode.",
    )
    relationship_type: RelationshipType = Field(
        ...,
        description="Ontology-controlled type of the directed relationship.",
    )

    # ── Provenance (mandatory) ────────────────────────────────────────────
    provenance: ProvenanceMetadata = Field(
        ...,
        description=(
            "Full provenance record for this relationship claim. "
            "This is the primary input to the trust scoring engine."
        ),
    )

    # ── Computed trust (lifecycle-managed) ───────────────────────────────
    trust_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Computed confidence score in [0.0, 1.0]. Initially None until "
            "`calculate_dynamic_trust()` is called. Written back by the "
            "provenance engine after each ingestion cycle."
        ),
    )

    # ── Lifecycle status ──────────────────────────────────────────────────
    status: EdgeStatus = Field(
        default=EdgeStatus.PENDING,
        description="Current lifecycle / epistemic status of this edge.",
    )

    # ── Optional narrative ────────────────────────────────────────────────
    description: Optional[str] = Field(
        default=None,
        max_length=2048,
        description=(
            "Free-text description or verbatim excerpt from the source document "
            "describing this relationship."
        ),
    )
    raw_text_snippet: Optional[str] = Field(
        default=None,
        max_length=4096,
        description=(
            "Raw text from the NLP extraction pipeline that produced this edge. "
            "Stored for auditability and LLM re-evaluation if contested."
        ),
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this edge was ingested into the system.",
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        description=(
            "UTC timestamp of when a human analyst resolved this edge via "
            "the HITL API. None if not yet reviewed."
        ),
    )
    resolved_by: Optional[str] = Field(
        default=None,
        description="Analyst username or ID who resolved this edge.",
    )

    @model_validator(mode="after")
    def source_and_target_must_differ(self) -> "GraphEdge":
        """
        Self-loops are semantically invalid in this ontology.
        An entity cannot have a geopolitical relationship *with itself*.
        """
        if self.source_node_id == self.target_node_id:
            raise ValueError(
                f"GraphEdge source and target must be different nodes. "
                f"Got source_node_id == target_node_id == '{self.source_node_id}'."
            )
        return self

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """
        Serialize this edge to a flat property dictionary for Neo4j.

        Plug-in point:
            props = edge.to_neo4j_properties()
            session.run(
                "MATCH (s {node_id: $source_node_id}), (t {node_id: $target_node_id})"
                "MERGE (s)-[r:%s {edge_id: $edge_id}]->(t)"
                "SET r += $props" % edge.relationship_type.value,
                **props
            )
        """
        return {
            "edge_id":           self.edge_id,
            "source_node_id":    self.source_node_id,
            "target_node_id":    self.target_node_id,
            "relationship_type": self.relationship_type.value,
            "trust_score":       self.trust_score,
            "status":            self.status.value,
            "ingested_at":       self.ingested_at.isoformat(),
            "resolved_at":       self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by":       self.resolved_by,
            # Flatten provenance for Neo4j property storage
            "prov_source_url":            self.provenance.source_url,
            "prov_source_type":           self.provenance.source_type.value,
            "prov_author_or_outlet":      self.provenance.author_or_outlet,
            "prov_credibility_score":     self.provenance.source_credibility_score,
            "prov_corroboration_count":   self.provenance.corroboration_count,
            "prov_timestamp":             self.provenance.timestamp.isoformat(),
            "prov_temporal_decay_factor": self.provenance.temporal_decay_factor,
            "prov_language_code":         self.provenance.language_code,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Convenience response / API schemas (used by FastAPI routes)
# ─────────────────────────────────────────────────────────────────────────────

class TrustScoreResult(BaseModel):
    """
    Return value of `calculate_dynamic_trust()`.
    Carries both the final score and its constituent components for
    explainability (displayed in the Nexus dashboard).
    """
    edge_id:               str
    raw_credibility:       float   = Field(description="Source credibility score (unmodified).")
    corroboration_bonus:   float   = Field(description="Bonus applied for multiple corroborating sources.")
    temporal_penalty:      float   = Field(description="Penalty applied due to age of the claim.")
    final_trust_score:     float   = Field(description="Clamped final trust score in [0.0, 1.0].")
    age_days:              float   = Field(description="Age of the source claim in days at time of calculation.")
    calculation_timestamp: datetime = Field(description="UTC time at which trust was calculated.")


class EdgeSummary(BaseModel):
    """
    Lightweight edge summary returned by the HITL queue endpoint.
    Avoids exposing large raw_text_snippet fields over the API.
    """
    edge_id:           str
    source_node_id:    str
    target_node_id:    str
    relationship_type: RelationshipType
    trust_score:       Optional[float]
    status:            EdgeStatus
    provenance_url:    str
    corroboration:     int
    ingested_at:       datetime

    @classmethod
    def from_edge(cls, edge: GraphEdge) -> "EdgeSummary":
        """
        Factory method: build an EdgeSummary from a full GraphEdge object.
        Used in the HITL routes to keep API payloads slim.
        """
        return cls(
            edge_id=edge.edge_id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            relationship_type=edge.relationship_type,
            trust_score=edge.trust_score,
            status=edge.status,
            provenance_url=edge.provenance.source_url,
            corroboration=edge.provenance.corroboration_count,
            ingested_at=edge.ingested_at,
        )
