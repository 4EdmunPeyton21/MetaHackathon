# ============================================================================
# PII Redactor Environment — Production Dockerfile
# ============================================================================
# Builds a containerized OpenEnv environment for the Data Privacy Compliance
# Agent. Designed to:
#   • Boot within the 600-second Hugging Face Spaces timeout
#   • Expose port 7860 for the FastAPI server
#   • Include Python 3.11, system utils, and all seed data
# ============================================================================

FROM python:3.11-slim AS base

# -- System dependencies -----------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# -- Working directory --------------------------------------------------------
WORKDIR /app

# -- Install Python dependencies first (layer caching) -----------------------
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# -- Copy application code ----------------------------------------------------
COPY . /app/pii_redactor_env/

# -- Create output directories ------------------------------------------------
RUN mkdir -p /app/pii_redactor_env/outputs/logs /app/pii_redactor_env/outputs/evals

# -- Set Python path so imports work ------------------------------------------
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# -- Health check (Hugging Face expects /health to respond) -------------------
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# -- Expose the Hugging Face Spaces default port ------------------------------
EXPOSE 7860

# -- Start the FastAPI server -------------------------------------------------
CMD ["uvicorn", "pii_redactor_env.server.app:app", "--host", "0.0.0.0", "--port", "7860"]
