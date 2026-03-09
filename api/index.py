"""
api/index.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vercel Serverless Entry Point for the Global Ontology Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vercel's Python runtime expects a file in /api that exports an
ASGI/WSGI-compatible `app` object.  We import directly from main.py
which already constructs and configures the FastAPI application.

The in-memory edge store is seeded on the first cold-start invocation
via FastAPI's lifespan event (registered in main.py).
"""
import sys
import os

# Make sure the project root is on the Python path so that
# "from app.xxx import yyy" imports resolve correctly inside Vercel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app   # noqa: F401  — Vercel discovers `app` from this module
