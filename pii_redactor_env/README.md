# 🛡️ PII Redactor Environment

> **Data Privacy Compliance Agent** — An OpenEnv environment for the Meta × Hugging Face OpenEnv AI Hackathon 2026

## Overview

An AI agent acts as a **Data Engineer** given a directory of messy, simulated customer data (CSVs, text logs, nested JSONs). The agent must write and execute Python scripts to **permanently redact PII** (credit cards, SSNs, emails, phone numbers) without corrupting non-sensitive data.

## Tasks

| ID | Difficulty | Description |
|----|-----------|-------------|
| `easy` | ⭐ | Redact credit card numbers from a flat CSV file |
| `medium` | ⭐⭐ | Redact SSNs from free-form chat log transcripts |
| `hard` | ⭐⭐⭐ | Redact mixed PII from deeply nested JSON structures |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run server locally
uvicorn pii_redactor_env.server.app:app --host 0.0.0.0 --port 7860

# Run baseline inference agent
python -m pii_redactor_env.inference.inference
```

## Action / Observation Space

- **Action**: Bash commands or Python scripts to execute in the sandboxed workspace
- **Observation**: stdout, stderr, file tree state, and task completion status

## Architecture

```
pii_redactor_env/
├── models.py          # Pydantic schemas (PIIAction, PIIObservation, PIIState)
├── client.py          # EnvClient for agent/training framework integration
├── server/            # FastAPI server + environment logic (runs in Docker)
├── tasks/             # Deterministic graders for each difficulty level
├── data/              # Pre-generated synthetic PII datasets
└── inference/         # Baseline OpenAI-client agent loop
```

## License

BSD-3-Clause
