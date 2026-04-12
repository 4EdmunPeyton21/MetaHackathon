# ============================================================================
# PII Redactor Environment — Production Dockerfile
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
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# -- Copy application code ----------------------------------------------------
# We copy the pii_redactor_env package into the container
COPY pii_redactor_env /app/pii_redactor_env/
COPY tasks /app/tasks/
COPY openenv.yaml /app/openenv.yaml
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md

# -- Install the package in editable mode ------------------------------------
RUN pip install --no-cache-dir -e .

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
