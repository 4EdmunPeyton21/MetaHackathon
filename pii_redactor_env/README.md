# 🛡️ PII Redactor Environment

> **Data Privacy Compliance Agent** — An OpenEnv environment for the Meta × Hugging Face OpenEnv AI Hackathon 2026

## Overview

The **PII Redactor Environment** simulates the real-world task of a Data Engineer or Privacy Officer who must sanitize sensitive customer data to comply with regulations like GDPR or CCPA. 

An AI agent is given a directory of messy, simulated customer data (CSVs, text logs, nested JSONs). The agent must write and execute Python scripts or use bash commands to **permanently redact PII** (credit cards, SSNs, emails, phone numbers) without corrupting non-sensitive data or altering the file structure.

## Action / Observation Space

### Action Space (`PIIAction`)
The agent submits actions as a JSON object:
- `action_type`: Either `"bash"` (for exploration/verification) or `"python"` (for processing).
- `command`: The shell command or full Python script to execute.

### Observation Space (`PIIObservation`)
After each step, the agent receives:
- `stdout` / `stderr`: Output from the executed command.
- `exit_code`: Status of the execution (0 for success).
- `file_tree`: List of all files currently in the workspace.
- `reward`: Current task score (0.0 to 1.0) based on redaction success and data integrity.
- `done`: Boolean indicating if the episode has ended.

## Tasks & Graders

| ID | Difficulty | Description | PII Types |
|----|-----------|-------------|-----------|
| `easy` | ⭐ | Redact Credit Cards from CSV | 16-digit Credit Card numbers |
| `medium` | ⭐⭐ | Redact SSNs from Chat Logs | `XXX-XX-XXXX` formatted SSNs |
| `hard` | ⭐⭐⭐ | Mixed PII from Nested JSON | CCs, SSNs, Emails, Phone Numbers |

### Grading Criteria
Each task uses a deterministic grader that calculates a score from **0.0 to 1.0**:
- **Redaction Success (40-50%)**: Percentage of PII successfully removed.
- **Structural Integrity (25%)**: Ensuring file formats, row counts, and JSON nesting remain intact.
- **Non-PII Preservation (25%)**: Verifying that non-sensitive data (IDs, names, etc.) is not accidentally redacted.

## Quick Start

### Installation
```bash
pip install -e .
```

### Run Server Locally
```bash
uvicorn pii_redactor_env.server.app:app --host 0.0.0.0 --port 7860
```

### Run Baseline Inference
```bash
# Requires OPENAI_API_KEY
python -m pii_redactor_env.inference.inference --task easy
```

## Baseline Scores

The following scores represent the performance of a scripted redaction agent (baseline) against the environment.

| Task | Model | Score | Success Rate |
|------|-------|-------|--------------|
| Easy | Scripted (Regex) | 1.000 | 100% |
| Medium | Scripted (Regex) | 1.000 | 100% |
| Hard | Scripted (Regex) | 1.000 | 100% |

## Architecture

- `pii_redactor_env/models.py`: Pydantic schemas for actions, observations, and state.
- `pii_redactor_env/server/`: FastAPI server and sandboxed execution logic.
- `pii_redactor_env/tasks/`: Deterministic graders for each difficulty level.
- `pii_redactor_env/data/`: Synthetic data generation and seed datasets.
- `pii_redactor_env/client.py`: Typed client for easy environment interaction.

## License

BSD-3-Clause
