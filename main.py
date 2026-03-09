"""
main.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global Ontology Engine — FastAPI Application Entry Point
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Starts the FastAPI application, registers all routers, and seeds the
in-memory edge store with mock data on startup.

Run with:
    uvicorn main:app --reload --port 8000

Then visit:
    http://localhost:8000/docs       — Swagger UI (try all endpoints live)
    http://localhost:8000/redoc      — ReDoc API docs
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.hitl_routes import router as hitl_router, seed_mock_edges
from app.api.dashboard_routes import router as dashboard_router

# ─────────────────────────────────────────────────────────────────────────────
# Logging configuration
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
logger = logging.getLogger("ontology_engine")


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan events (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Startup:
      • Seeds the in-memory edge store with mock data.
      • In production: initialise Neo4j driver, run schema migration checks.

    Shutdown:
      • In production: close Neo4j driver connection pool.
    """
    logger.info("=" * 60)
    logger.info("Global Ontology Engine — starting up")
    logger.info("=" * 60)

    # Seed mock edge data for development / demo purposes.
    seed_mock_edges()

    logger.info("Startup complete. API is ready.")
    yield  # Application runs here

    logger.info("Global Ontology Engine — shutting down.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Global Ontology Engine — Nexus API",
    description=(
        "AI-powered Knowledge Graph for geopolitical and economic intelligence data.\n\n"
        "## Sub-systems\n"
        "- **Confidence & Provenance Layer** — Dynamic trust scoring with temporal decay\n"
        "- **Adversarial Detector** — Narrative flooding and cross-lingual conflict detection\n"
        "- **Ontology Governance** — Committee-gated schema versioning with rollback\n"
        "- **HITL Queue** — Human analyst review and override of low-confidence edges\n"
        "- **Nexus Dashboard** — Health stats, schema explorer, score explainer, anomaly scanner\n\n"
        "### Neo4j Integration\n"
        "All database operations are currently mocked. "
        "Look for `# ← NEO4J:` comments in the source for plug-in points."
    ),
    version="1.0.0",
    contact={
        "name":  "AI Summit Engineering",
        "email": "engineering@ai-summit.io",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────────────────────────
# CORS Middleware
# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Restrict in production: ["https://nexus.yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Register routers
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(hitl_router)
app.include_router(dashboard_router)


# ─────────────────────────────────────────────────────────────────────────────
# Root health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="Root health check")
def root():
    """
    Simple ping endpoint confirming the service is alive.
    Used by load balancers and uptime monitors.
    """
    return {
        "service":   "Global Ontology Engine",
        "status":    "operational",
        "docs":      "/docs",
        "version":   "1.0.0",
    }


@app.get("/health", tags=["Health"], summary="Detailed health check")
def health():
    """
    Detailed health check returning sub-system status.
    In production, test Neo4j connectivity here and return 503 if down.
    """
    from app.api.hitl_routes import _edge_store
    from app.api.dashboard_routes import get_registry

    reg = get_registry()
    return {
        "status":              "healthy",
        "edge_store_count":    _edge_store.count(),
        "ontology_version":    reg.current_version,
        "entity_types":        len(reg.entity_types),
        "relationship_types":  len(reg.relationship_types),
        "neo4j":               "mock (not connected)",  # Replace with live ping
    }
