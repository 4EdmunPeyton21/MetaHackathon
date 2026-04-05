"""
pii_redactor_env/server/app.py
-------------------------------
FastAPI application entry-point.

Creates the HTTP/WebSocket server using ``openenv.core.env_server.create_fastapi_app``.
Also registers the ``POST /reset`` liveness endpoint required by Hugging Face
Spaces validation (the platform sends a POST to ``/reset`` to confirm the
container is alive and responding within the 600-second boot window).
"""

from __future__ import annotations

from fastapi import FastAPI
from openenv.core.env_server import create_fastapi_app

from pii_redactor_env.models import PIIAction, PIIObservation
from pii_redactor_env.server.pii_environment import PIIRedactorEnvironment


# ---------------------------------------------------------------------------
# Create the OpenEnv FastAPI app (registers /step, /reset, /state, /health)
# ---------------------------------------------------------------------------
app: FastAPI = create_fastapi_app(PIIRedactorEnvironment, PIIAction, PIIObservation)


# ---------------------------------------------------------------------------
# Additional liveness endpoint required by Hugging Face Spaces validation.
# The HF infra sends  POST /reset  to confirm the container booted correctly.
# The openenv create_fastapi_app may already register a /reset route; this
# is a safety net to ensure the endpoint exists and returns 200.
# ---------------------------------------------------------------------------
@app.get("/ping")
async def ping() -> dict:
    """
    Liveness check endpoint.

    Returns:
        A simple JSON payload confirming the server is alive.
    """
    return {"status": "alive", "environment": "pii_redactor_env"}

@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint.

    Returns:
        A simple JSON payload confirming the server is healthy.
    """
    return {"status": "healthy"}
