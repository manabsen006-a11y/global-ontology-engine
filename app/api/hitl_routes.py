"""
app/api/hitl_routes.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global Ontology Engine — Human-in-the-Loop (HITL) API Routes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This module exposes two FastAPI endpoints that form the Human-in-the-Loop
review pipeline:

  GET  /api/v1/queue/low-confidence
       Returns all graph edges whose computed trust score is below the
       LOW_CONFIDENCE_THRESHOLD (0.60), along with their provenance details,
       so a human analyst can triage them.

  POST /api/v1/queue/resolve
       Allows an analyst to make a final decision on a flagged edge:
         • is_verified = True  → trust score set to 1.0, status → VERIFIED
         • is_verified = False → edge removed from the active graph entirely
                                 (status → REJECTED, soft-delete)

Design notes:
  • The "database" is an in-memory `EdgeStore` singleton (see `_edge_store`
    below).  In production, replace all `_edge_store` operations with
    Neo4j driver calls using `edge.to_neo4j_properties()`.
  • All endpoints return structured Pydantic response models for OpenAPI
    compatibility and downstream JS/React client consumption.
  • Analyst identity is passed via the `X-Analyst-Id` header (mock auth).
    In production, replace with a proper JWT / OAuth2 dependency.

Neo4j plug-in points are marked with:  # ← NEO4J: replace with driver call
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.models.ontology_models import (
    EdgeStatus,
    EdgeSummary,
    GraphEdge,
    RelationshipType,
)
from app.services.provenance_engine import (
    LOW_CONFIDENCE_THRESHOLD,
    calculate_dynamic_trust,
    get_low_confidence_edges,
)

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1/queue", tags=["HITL Review Queue"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# In-memory Edge Store (mock database layer)
# ─────────────────────────────────────────────────────────────────────────────

class _EdgeStore:
    """
    Thread-unsafe in-memory store for `GraphEdge` objects.

    This mimics the Neo4j graph's edge collection for development / testing.
    In production, all reads/writes should be replaced with Cypher queries
    via `neo4j.Session`.

    Plug-in replacement:
        Every method in this class corresponds to a Cypher operation:

        get_all()        →  MATCH ()-[r:*]-() RETURN r
        get_by_id()      →  MATCH ()-[r {edge_id: $id}]-() RETURN r
        upsert()         →  MERGE (s)-[r {edge_id: $id}]->(t) SET r += $props
        soft_delete()    →  MATCH ()-[r {edge_id: $id}]-() SET r.status = 'REJECTED'
    """

    def __init__(self) -> None:
        self._edges: Dict[str, GraphEdge] = {}

    def upsert(self, edge: GraphEdge) -> None:
        """Add or update an edge in the store."""
        self._edges[edge.edge_id] = edge
        # ← NEO4J: replace with driver call using edge.to_neo4j_properties()

    def get_all(self) -> List[GraphEdge]:
        """Return all edges currently in the store."""
        return list(self._edges.values())
        # ← NEO4J: MATCH ()-[r]-() RETURN r

    def get_by_id(self, edge_id: str) -> Optional[GraphEdge]:
        """Retrieve a single edge by its UUID."""
        return self._edges.get(edge_id)
        # ← NEO4J: MATCH ()-[r {edge_id: $edge_id}]-() RETURN r LIMIT 1

    def soft_delete(self, edge_id: str) -> None:
        """
        Mark an edge as REJECTED (soft-delete).  The record is retained for
        the audit trail but excluded from active graph queries.
        """
        edge = self._edges.get(edge_id)
        if edge:
            edge.status = EdgeStatus.REJECTED
        # ← NEO4J: MATCH ()-[r {edge_id: $edge_id}]-() SET r.status = 'REJECTED'

    def count(self) -> int:
        return len(self._edges)


# Module-level singleton.  Import and use this in other modules or replace
# with a dependency-injected Neo4j session in production.
_edge_store = _EdgeStore()


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Pydantic models
# ─────────────────────────────────────────────────────────────────────────────

class LowConfidenceQueueResponse(BaseModel):
    """
    Response body for GET /api/v1/queue/low-confidence.

    Attributes:
        total_flagged:   Total number of edges below the trust threshold.
        threshold:       The trust score threshold used for flagging (0.60).
        edges:           Lightweight edge summaries for each flagged edge.
    """
    total_flagged: int = Field(description="Total number of low-confidence edges in the queue.")
    threshold:     float = Field(description="Trust score threshold applied to build this queue.")
    edges:         List[EdgeSummary] = Field(description="Summarised details of each flagged edge.")

    model_config = {"json_schema_extra": {
        "example": {
            "total_flagged": 2,
            "threshold": 0.6,
            "edges": [{
                "edge_id": "abc-123",
                "source_node_id": "node-a",
                "target_node_id": "node-b",
                "relationship_type": "ALLIED_WITH",
                "trust_score": 0.42,
                "status": "LOW_CONFIDENCE",
                "provenance_url": "https://example.com/article",
                "corroboration": 1,
                "ingested_at": "2024-01-01T00:00:00Z",
            }],
        }
    }}


class ResolveRequest(BaseModel):
    """
    Request body for POST /api/v1/queue/resolve.

    Attributes:
        edge_id:     UUID of the graph edge to resolve.
        is_verified: True → mark as VERIFIED (trust=1.0).
                     False → mark as REJECTED (soft-delete from active graph).
        analyst_note: Optional free-text note explaining the decision.
    """
    edge_id:      str  = Field(..., description="UUID of the edge being resolved.")
    is_verified:  bool = Field(
        ...,
        description=(
            "Resolution decision. True = edge is confirmed valid (trust → 1.0, "
            "status → VERIFIED). False = edge is a false positive (status → REJECTED, "
            "removed from active graph)."
        ),
    )
    analyst_note: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Optional free-text reasoning for the resolution decision.",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "edge_id": "abc-123",
            "is_verified": True,
            "analyst_note": "Confirmed by three independent embassy cables.",
        }
    }}


class ResolveResponse(BaseModel):
    """
    Response body for POST /api/v1/queue/resolve.

    Attributes:
        edge_id:     The resolved edge's UUID.
        action:      Human-readable description of the action taken.
        new_status:  The edge's status after resolution.
        new_trust_score: The edge's trust score after resolution (None if rejected).
        resolved_by: Analyst ID from the request header.
        resolved_at: UTC timestamp of the resolution.
    """
    edge_id:         str
    action:          str
    new_status:      EdgeStatus
    new_trust_score: Optional[float]
    resolved_by:     str
    resolved_at:     datetime


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/low-confidence",
    response_model=LowConfidenceQueueResponse,
    summary="Fetch the HITL review queue (low-confidence edges)",
    description=(
        "Returns all graph edges whose computed trust score is below the "
        f"low-confidence threshold ({LOW_CONFIDENCE_THRESHOLD:.2f}). "
        "Analysts use this queue to manually verify or reject edges before "
        "they are promoted to the active knowledge graph."
    ),
    responses={
        200: {"description": "Queue returned successfully (may be empty)."},
        500: {"description": "Internal error fetching edges from the store."},
    },
)
def get_low_confidence_queue() -> LowConfidenceQueueResponse:
    """
    Retrieve all edges that are below the trust threshold and require human
    analyst review.

    The function:
      1. Fetches all edges from the store (in production: Neo4j query).
      2. Re-scores any PENDING edges that have not yet been evaluated.
      3. Filters to those with trust_score < LOW_CONFIDENCE_THRESHOLD.
      4. Returns them as lightweight `EdgeSummary` objects.

    Returns:
        LowConfidenceQueueResponse with the count and edge summaries.
    """
    try:
        all_edges = _edge_store.get_all()

        # Re-score any PENDING edges that slipped through without scoring.
        for edge in all_edges:
            if edge.trust_score is None and edge.status == EdgeStatus.PENDING:
                try:
                    calculate_dynamic_trust(edge)
                except ValueError:
                    pass  # Terminal-state edges: skip silently

        # Filter to low-confidence candidates.
        low_conf_edges = get_low_confidence_edges(all_edges, LOW_CONFIDENCE_THRESHOLD)

        # Build lightweight summaries (avoids exposing raw_text_snippet over API).
        summaries = [EdgeSummary.from_edge(e) for e in low_conf_edges]

        logger.info(
            "GET /low-confidence | total_edges=%d | flagged=%d | threshold=%.2f",
            len(all_edges), len(summaries), LOW_CONFIDENCE_THRESHOLD,
        )

        return LowConfidenceQueueResponse(
            total_flagged=len(summaries),
            threshold=LOW_CONFIDENCE_THRESHOLD,
            edges=summaries,
        )

    except Exception as exc:
        logger.exception("Error building low-confidence queue: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch low-confidence queue: {str(exc)}",
        )


@router.post(
    "/resolve",
    response_model=ResolveResponse,
    summary="Resolve a flagged edge (HITL decision)",
    description=(
        "Allows a human analyst to make a final decision on a low-confidence or "
        "contested-narrative edge.\n\n"
        "- **is_verified = true**: Edge is confirmed valid. Trust score is set to 1.0 "
        "and status changes to VERIFIED.\n"
        "- **is_verified = false**: Edge is a false positive. It is soft-deleted from "
        "the active graph (status → REJECTED) but retained for the audit trail."
    ),
    responses={
        200: {"description": "Edge resolved successfully."},
        404: {"description": "Edge not found in the store."},
        409: {"description": "Edge is already in a terminal state (VERIFIED/REJECTED)."},
        500: {"description": "Internal error during resolution."},
    },
)
def resolve_edge(
    body: ResolveRequest,
    x_analyst_id: str = Header(
        default="anonymous",
        description=(
            "Analyst username or ID performing the resolution. "
            "Pass via X-Analyst-Id HTTP header. "
            "In production, extracted from JWT claims."
        ),
    ),
) -> ResolveResponse:
    """
    Human analyst resolution of a flagged graph edge.

    Side-effects:
      - If is_verified=True:
          edge.trust_score = 1.0
          edge.status      = VERIFIED
          edge.resolved_by = analyst_id
          edge.resolved_at = now (UTC)
      - If is_verified=False:
          edge.status      = REJECTED
          edge.resolved_by = analyst_id
          edge.resolved_at = now (UTC)
          (edge is soft-deleted by the store)

    In production, writes are flushed to Neo4j via `edge.to_neo4j_properties()`.

    Args:
        body:          ResolveRequest payload from the analyst.
        x_analyst_id:  Analyst identifier from the X-Analyst-Id header.

    Returns:
        ResolveResponse confirming the action taken and the new edge state.

    Raises:
        404: If the edge_id is not found in the store.
        409: If the edge is already VERIFIED or REJECTED (terminal state).
    """
    now_utc = datetime.now(timezone.utc)

    # ── Look up the edge ───────────────────────────────────────────────────
    edge = _edge_store.get_by_id(body.edge_id)
    if edge is None:
        logger.warning(
            "POST /resolve | edge_id=%s NOT FOUND | analyst=%s",
            body.edge_id[:8], x_analyst_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge '{body.edge_id}' not found in the active store.",
        )

    # ── Guard: already in a terminal state ────────────────────────────────
    if edge.status in (EdgeStatus.VERIFIED, EdgeStatus.REJECTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Edge '{body.edge_id}' is already in terminal state "
                f"'{edge.status.value}'. No further action required."
            ),
        )

    # ── Apply resolution ──────────────────────────────────────────────────
    edge.resolved_by = x_analyst_id
    edge.resolved_at = now_utc

    if body.is_verified:
        # Analyst confirms the edge is valid: max trust, promote to VERIFIED.
        edge.trust_score = 1.0
        edge.status      = EdgeStatus.VERIFIED
        action           = (
            f"Edge VERIFIED by analyst '{x_analyst_id}'. "
            f"Trust score set to 1.0. "
            + (f"Note: {body.analyst_note}" if body.analyst_note else "")
        )
        _edge_store.upsert(edge)
        # ← NEO4J: session.run("MATCH ()-[r {edge_id: $id}]-() SET r.trust_score=1.0, r.status='VERIFIED'", ...)

        logger.info(
            "HITL RESOLVE | VERIFIED | edge_id=%s | analyst=%s | trust=1.0",
            body.edge_id[:8], x_analyst_id,
        )
    else:
        # Analyst rejects the edge: soft-delete from active graph.
        _edge_store.soft_delete(body.edge_id)
        # ← NEO4J: session.run("MATCH ()-[r {edge_id: $id}]-() SET r.status='REJECTED'", ...)

        action = (
            f"Edge REJECTED (false positive) by analyst '{x_analyst_id}'. "
            f"Removed from active graph; retained in audit trail. "
            + (f"Note: {body.analyst_note}" if body.analyst_note else "")
        )
        logger.info(
            "HITL RESOLVE | REJECTED | edge_id=%s | analyst=%s",
            body.edge_id[:8], x_analyst_id,
        )

    return ResolveResponse(
        edge_id=body.edge_id,
        action=action,
        new_status=edge.status,
        new_trust_score=edge.trust_score if body.is_verified else None,
        resolved_by=x_analyst_id,
        resolved_at=now_utc,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Utility: seed the store with mock data (used by main.py on startup)
# ─────────────────────────────────────────────────────────────────────────────

def seed_mock_edges() -> None:
    """
    Populate the in-memory edge store with a realistic set of mock edges
    covering a range of trust scores and statuses.

    Called by `main.py` on startup via FastAPI's `lifespan` event.
    Remove in production — replace with a Neo4j data load.
    """
    from datetime import timedelta
    from app.models.ontology_models import (
        GraphNode, NodeType, ProvenanceMetadata, SourceType,
    )

    def _node(ntype: NodeType, name: str) -> GraphNode:
        return GraphNode(node_type=ntype, name=name)

    def _prov(cred: float, corr: int, days: float, decay: float = 0.01,
              stype: SourceType = SourceType.NEWS_ARTICLE, lang: str = "en") -> ProvenanceMetadata:
        return ProvenanceMetadata(
            source_url=f"https://example-source.io/{cred}-{days}d",
            source_type=stype,
            author_or_outlet="Mock Intelligence Feed",
            source_credibility_score=cred,
            corroboration_count=corr,
            timestamp=datetime.now(timezone.utc) - timedelta(days=days),
            temporal_decay_factor=decay,
            language_code=lang,
        )

    mock_edges = [
        # Very low confidence — HITL queue candidate
        GraphEdge(
            source_node_id=_node(NodeType.COUNTRY, "Ruritania").node_id,
            target_node_id=_node(NodeType.COUNTRY, "Borduria").node_id,
            relationship_type=RelationshipType.CONFLICT_WITH,
            provenance=_prov(0.20, 1, 45, 0.02, SourceType.SOCIAL_MEDIA),
            raw_text_snippet="Ruritanian army attacking Bordurian border posts.",
        ),
        # Moderate-low — HITL queue candidate
        GraphEdge(
            source_node_id=_node(NodeType.COUNTRY, "Syldavia").node_id,
            target_node_id=_node(NodeType.ORGANIZATION, "OTAN-X").node_id,
            relationship_type=RelationshipType.ALLIED_WITH,
            provenance=_prov(0.40, 2, 20, 0.015),
        ),
        # Moderate — should be ACTIVE after scoring
        GraphEdge(
            source_node_id=_node(NodeType.COUNTRY, "Freedonia").node_id,
            target_node_id=_node(NodeType.COUNTRY, "Sylvania").node_id,
            relationship_type=RelationshipType.TRADES_WITH,
            provenance=_prov(0.65, 4, 5, 0.005, SourceType.GOVERNMENT_DOC),
        ),
        # High confidence — should be ACTIVE
        GraphEdge(
            source_node_id=_node(NodeType.COUNTRY, "Grand Fenwick").node_id,
            target_node_id=_node(NodeType.TREATY, "Fenwick Accord").node_id,
            relationship_type=RelationshipType.SIGNED_TREATY,
            provenance=_prov(0.92, 6, 1, 0.001, SourceType.GOVERNMENT_DOC),
        ),
        # Claimed region — contested
        GraphEdge(
            source_node_id=_node(NodeType.COUNTRY, "Zubrowka").node_id,
            target_node_id=_node(NodeType.REGION, "North Luggnagg").node_id,
            relationship_type=RelationshipType.HAS_CLAIM_OVER,
            provenance=_prov(0.30, 1, 10, 0.02, SourceType.SOCIAL_MEDIA, "zb"),
            raw_text_snippet="Zubrowka troops occupy North Luggnagg territory.",
        ),
    ]

    for edge in mock_edges:
        try:
            calculate_dynamic_trust(edge)
        except ValueError:
            pass
        _edge_store.upsert(edge)

    logger.info("Mock edge store seeded with %d edges.", len(mock_edges))
