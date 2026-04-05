"""
pii_redactor_env/inference/config.py
-------------------------------------
Configuration constants for the baseline inference agent.
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Model / API — Standard competition environment variables
# ---------------------------------------------------------------------------
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
# The hackathon requires using HF_TOKEN for authentication
API_KEY_ENV_VAR: str = "HF_TOKEN"

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------
MAX_STEPS: int = 30          # Hard cap across all tasks
STEP_TIMEOUT_SECONDS: int = 60
BENCHMARK_NAME: str = "pii_redactor_env"

# ---------------------------------------------------------------------------
# Environment connection (WebSocket — stateful sessions)
# ---------------------------------------------------------------------------
# Points to the live Hugging Face Space by default if ENV_WS_URL is set
ENV_WS_URL: str = os.getenv("ENV_WS_URL", "ws://localhost:7860/ws")
