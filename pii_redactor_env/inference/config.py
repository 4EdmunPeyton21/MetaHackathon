"""
pii_redactor_env/inference/config.py
-------------------------------------
Configuration constants for the baseline inference agent.
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Model / API
# ---------------------------------------------------------------------------
MODEL_NAME: str = os.getenv("OPENAI_MODEL", "gpt-4o")
API_BASE_URL: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
API_KEY_ENV_VAR: str = "OPENAI_API_KEY"

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------
MAX_STEPS: int = 30          # Hard cap across all tasks
STEP_TIMEOUT_SECONDS: int = 60
BENCHMARK_NAME: str = "pii_redactor_env"

# ---------------------------------------------------------------------------
# Environment connection
# ---------------------------------------------------------------------------
ENV_BASE_URL: str = os.getenv("ENV_BASE_URL", "http://localhost:7860")
