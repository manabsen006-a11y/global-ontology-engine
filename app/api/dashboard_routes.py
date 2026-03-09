"""
app/api/dashboard_routes.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global Ontology Engine — Nexus Dashboard API Routes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This module exposes the endpoints powering the "Nexus" analyst dashboard —
the primary UI from which operators monitor knowledge graph health, review
the ontology schema, explore trust score explanations, and check for
adversarial anomalies.

Endpoints:
  GET  /api/v1/dashboard/stats
       High-level health statistics for the Nexus landing page widget.

  GET  /api/v1/dashboard/schema
       Current ontology schema (entity types + relationship definitions)
       at the active version, used to populate the schema explorer panel.

  GET  /api/v1/dashboard/schema/version-history
       Full changelog of all committed schema versions (audit trail panel).

  POST /api/v1/dashboard/schema/propose
       Submit a new schema change proposal for committee review.
       Votes are accepted in the same payload for the mock implementation.

  GET  /api/v1/dashboard/edges/{edge_id}/explain
       Retrieve a human-readable trust score breakdown for a specific edge
       (the "Score Explainer" tooltip in the Nexus graph view).

  GET  /api/v1/dashboard/anomalies/scan
       Trigger a live adversarial scan over all stored edges and return
       the anomaly reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.governance.version_control import (
    ChangeType,
    EntityTypeDefinition,
    OntologyRegistry,
    RelationshipTypeDefinition,
    SchemaChangeProposal,
    VoteDecision,
    VoteRecord,
    VoteResult,
)
from app.models.ontology_models import EdgeStatus
from app.services.adversarial_detector import (
    AnomalyReport,
    detect_narrative_anomaly,
)
from app.services.provenance_engine import explain_trust_score

# ─────────────────────────────────────────────────────────────────────────────
# Router and module-level singletons
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1/dashboard", tags=["Nexus Dashboard"])
logger = logging.getLogger(__name__)

# Shared registry singleton — injected from main.py on startup.
# In production: use FastAPI's dependency injection (Depends) to provide
# a request-scoped registry backed by Neo4j.
_registry: OntologyRegistry = OntologyRegistry()


def get_registry() -> OntologyRegistry:
    """Return the shared OntologyRegistry singleton."""
    return _registry


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    """Landing-page health statistics widget payload."""
    total_edges:           int   = Field(description="Total edges in the active graph.")
    active_edges:          int   = Field(description="Edges with status ACTIVE.")
    low_confidence_edges:  int   = Field(description="Edges below the trust threshold (queued for HITL).")
    verified_edges:        int   = Field(description="Edges manually confirmed by analysts.")
    rejected_edges:        int   = Field(description="Edges soft-deleted as false positives.")
    contested_edges:       int   = Field(description="Edges flagged CONTESTED_NARRATIVE.")
    pending_edges:         int   = Field(description="Edges not yet scored.")
    ontology_version:      int   = Field(description="Current active ontology schema version.")
    entity_type_count:     int   = Field(description="Number of accepted entity types.")
    relationship_type_count: int = Field(description="Number of accepted relationship types.")
    generated_at:          datetime


class SchemaResponse(BaseModel):
    """Active ontology schema payload for the schema explorer panel."""
    version:            int
    entity_types:       Dict[str, Any]
    relationship_types: Dict[str, Any]
    fetched_at:         datetime


class ProposeSchemaRequest(BaseModel):
    """
    Request body to submit a schema change proposal with committee votes.

    In production the votes would be submitted separately (one per committee
    member via an authenticated endpoint).  For the mock API they are
    bundled in the same request for simplicity.
    """
    proposer_id:    str        = Field(..., description="ID of the submitting researcher.")
    change_type:    ChangeType = Field(..., description="Type of schema change.")
    definition_name: str       = Field(..., description="Name of the entity/relationship type.")
    definition_desc: str       = Field(default="", description="Description of the new/modified type.")
    approve_votes:  int        = Field(default=3, ge=0, description="Simulated approve vote count.")
    reject_votes:   int        = Field(default=0, ge=0, description="Simulated reject vote count.")
    abstain_votes:  int        = Field(default=0, ge=0, description="Simulated abstain vote count.")

    model_config = {"json_schema_extra": {
        "example": {
            "proposer_id": "analyst-007",
            "change_type": "ADD_ENTITY_TYPE",
            "definition_name": "MILITARY_UNIT",
            "definition_desc": "A named military formation or unit.",
            "approve_votes": 4,
            "reject_votes": 0,
            "abstain_votes": 1,
        }
    }}


class TrustExplainResponse(BaseModel):
    """Trust score explanation for the Nexus graph-view tooltip."""
    edge_id:            str
    source_url:         str
    source_credibility: float
    corroboration_count: int
    corroboration_bonus: float
    claim_age_days:     float
    decay_factor:       float
    temporal_penalty:   float
    projected_score:    float
    current_status:     str
    explanation_text:   str


class AnomalyScanResponse(BaseModel):
    """Result of a live adversarial scan over all stored edges."""
    total_edges_scanned: int
    anomalies_found:     int
    time_window_hours:   float
    reports:             List[Dict[str, Any]]
    scanned_at:          datetime


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Knowledge graph & ontology health statistics",
)
def get_dashboard_stats() -> DashboardStats:
    """
    Return a snapshot of key health metrics for the Nexus dashboard landing page.

    Counts edges by status from the HITL store and reads schema metadata
    from the shared OntologyRegistry.

    Neo4j plug-in: replace `_edge_store.get_all()` with:
        MATCH ()-[r]-() RETURN r.status, count(r) AS cnt GROUP BY r.status
    """
    # Import the shared edge store from the HITL module.
    from app.api.hitl_routes import _edge_store

    all_edges = _edge_store.get_all()
    status_counts = {s: 0 for s in EdgeStatus}
    for edge in all_edges:
        status_counts[edge.status] = status_counts.get(edge.status, 0) + 1

    reg = get_registry()

    return DashboardStats(
        total_edges=len(all_edges),
        active_edges=status_counts.get(EdgeStatus.ACTIVE, 0),
        low_confidence_edges=status_counts.get(EdgeStatus.LOW_CONFIDENCE, 0),
        verified_edges=status_counts.get(EdgeStatus.VERIFIED, 0),
        rejected_edges=status_counts.get(EdgeStatus.REJECTED, 0),
        contested_edges=status_counts.get(EdgeStatus.CONTESTED_NARRATIVE, 0),
        pending_edges=status_counts.get(EdgeStatus.PENDING, 0),
        ontology_version=reg.current_version,
        entity_type_count=len(reg.entity_types),
        relationship_type_count=len(reg.relationship_types),
        generated_at=datetime.now(timezone.utc),
    )


@router.get(
    "/schema",
    response_model=SchemaResponse,
    summary="Fetch the active ontology schema",
)
def get_schema() -> SchemaResponse:
    """
    Return the full set of accepted entity types and relationship definitions
    at the current version.  Used to populate the schema explorer panel in the
    Nexus UI and to validate incoming NLP extraction results.
    """
    reg = get_registry()
    return SchemaResponse(
        version=reg.current_version,
        entity_types={k: v.to_dict() for k, v in reg.entity_types.items()},
        relationship_types={k: v.to_dict() for k, v in reg.relationship_types.items()},
        fetched_at=datetime.now(timezone.utc),
    )


@router.get(
    "/schema/version-history",
    response_model=List[Dict[str, Any]],
    summary="Fetch the ontology schema version changelog",
)
def get_schema_version_history() -> List[Dict[str, Any]]:
    """
    Return all committed schema versions in chronological order.
    Displayed in the Nexus "Schema Changelog" audit panel.
    Each entry includes the proposer, approval ratio, and change summary.
    """
    reg = get_registry()
    history = reg.get_version_history()
    logger.info(
        "GET /schema/version-history | %d versions returned", len(history)
    )
    return history


@router.post(
    "/schema/propose",
    response_model=VoteResult,
    summary="Submit a schema change proposal with committee votes",
    description=(
        "Submit a governance proposal to add or modify an ontology entity type "
        "or relationship type. The mock payload includes simulated vote counts. "
        "In production, votes are submitted separately via authenticated committee "
        "member endpoints and the proposal is resolved asynchronously."
    ),
    responses={
        200: {"description": "Proposal evaluated. Check `accepted` field for outcome."},
        422: {"description": "Invalid request body."},
    },
)
def propose_schema_change(body: ProposeSchemaRequest) -> VoteResult:
    """
    Evaluate a schema change proposal against mock committee votes.

    The endpoint builds a `SchemaChangeProposal` and a list of `VoteRecord`
    objects from the request payload, then delegates to
    `OntologyRegistry.propose_schema_change()` for governance evaluation.

    Supported change types:
      ADD_ENTITY_TYPE, ADD_RELATIONSHIP_TYPE,
      MODIFY_ENTITY_TYPE, MODIFY_RELATIONSHIP_TYPE,
      REMOVE_ENTITY_TYPE, REMOVE_RELATIONSHIP_TYPE
    """
    reg = get_registry()

    # Build the definition object from the request body.
    if body.change_type in (ChangeType.ADD_ENTITY_TYPE, ChangeType.MODIFY_ENTITY_TYPE):
        definition: Any = EntityTypeDefinition(
            name=body.definition_name,
            description=body.definition_desc or f"Auto-generated definition for {body.definition_name}.",
        )
    elif body.change_type in (ChangeType.ADD_RELATIONSHIP_TYPE, ChangeType.MODIFY_RELATIONSHIP_TYPE):
        definition = RelationshipTypeDefinition(
            name=body.definition_name,
            description=body.definition_desc or f"Auto-generated definition for {body.definition_name}.",
        )
    else:
        # REMOVE types: pass the name as a plain string.
        definition = body.definition_name

    proposal = SchemaChangeProposal(
        proposer_id=body.proposer_id,
        change_type=body.change_type,
        new_definition=definition,
        description=body.definition_desc or f"Proposal to {body.change_type.value} '{body.definition_name}'.",
    )

    # Build mock vote records.
    votes: List[VoteRecord] = []
    for i in range(body.approve_votes):
        votes.append(VoteRecord(voter_id=f"committee-approver-{i}", decision=VoteDecision.APPROVE))
    for i in range(body.reject_votes):
        votes.append(VoteRecord(voter_id=f"committee-rejecter-{i}", decision=VoteDecision.REJECT))
    for i in range(body.abstain_votes):
        votes.append(VoteRecord(voter_id=f"committee-abstainer-{i}", decision=VoteDecision.ABSTAIN))

    result = reg.propose_schema_change(proposal, votes)

    logger.info(
        "POST /schema/propose | change=%s | name=%s | accepted=%s | version=%s",
        body.change_type.value, body.definition_name,
        result.accepted, result.new_version_number,
    )
    return result


@router.get(
    "/edges/{edge_id}/explain",
    response_model=TrustExplainResponse,
    summary="Explain trust score components for a specific edge",
    description=(
        "Returns a full breakdown of how the trust score for a given edge was "
        "calculated — base credibility, corroboration bonus, temporal decay "
        "penalty — along with a human-readable prose explanation. "
        "Displayed as a tooltip in the Nexus graph view."
    ),
    responses={
        200: {"description": "Explanation returned successfully."},
        404: {"description": "Edge not found."},
    },
)
def explain_edge_trust(edge_id: str) -> TrustExplainResponse:
    """
    Fetch a trust score explanation for a single graph edge.

    Args:
        edge_id: The UUID of the edge to explain (path parameter).

    Returns:
        TrustExplainResponse with all score components and explanation text.

    Raises:
        404 if the edge is not found in the active store.
    """
    from app.api.hitl_routes import _edge_store

    edge = _edge_store.get_by_id(edge_id)
    if edge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge '{edge_id}' not found.",
        )

    explanation = explain_trust_score(edge)
    return TrustExplainResponse(**explanation)


@router.get(
    "/anomalies/scan",
    response_model=AnomalyScanResponse,
    summary="Run a live adversarial anomaly scan over all stored edges",
    description=(
        "Triggers `detect_narrative_anomaly()` over all edges currently in the "
        "edge store and returns the full list of anomaly reports. "
        "Use the `time_window_hours` query parameter to adjust the detection window."
    ),
)
def scan_for_anomalies(
    time_window_hours: float = Query(
        default=1.0,
        ge=0.1,
        le=168.0,
        description="Look-back window in hours for the flooding detector (0.1 – 168).",
    ),
) -> AnomalyScanResponse:
    """
    Run the adversarial narrative flooding detector over all stored edges.

    Returns a list of `AnomalyReport` objects for any clusters that exceed
    the flooding threshold within the specified time window.

    Neo4j plug-in: replace `_edge_store.get_all()` with a time-windowed query:
        MATCH ()-[r]-() WHERE r.prov_timestamp >= $cutoff RETURN r
    """
    from app.api.hitl_routes import _edge_store

    all_edges = _edge_store.get_all()
    reports: List[AnomalyReport] = detect_narrative_anomaly(
        all_edges, time_window_hours=time_window_hours
    )

    serialised = []
    for r in reports:
        serialised.append({
            "is_anomalous":          r.is_anomalous,
            "severity":              r.severity.value,
            "flagged_cluster_key":   r.flagged_cluster_key,
            "duplicate_count":       r.duplicate_count,
            "time_window_hours":     r.time_window_hours,
            "offending_source_urls": r.offending_source_urls,
            "offending_edge_ids":    r.offending_edge_ids[:5],  # truncate for API response
            "detected_at":           r.detected_at.isoformat(),
            "message":               r.message,
        })

    logger.info(
        "GET /anomalies/scan | window=%.1fh | edges=%d | anomalies=%d",
        time_window_hours, len(all_edges), len(reports),
    )

    return AnomalyScanResponse(
        total_edges_scanned=len(all_edges),
        anomalies_found=len(reports),
        time_window_hours=time_window_hours,
        reports=serialised,
        scanned_at=datetime.now(timezone.utc),
    )
