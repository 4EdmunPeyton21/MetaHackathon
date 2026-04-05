---
title: The Data Privacy Compliance Agent (PII Redactor)
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: bsd-3-clause
---

# 🛡️ The Data Privacy Compliance Agent (PII Redactor)

**Domain**: Data Engineering & Security  
**Submission for**: Meta x Hugging Face OpenEnv Hackathon

The **PII Redactor** environment challenges AI agents to act as Data Engineers tasked with cleaning sensitive customer datasets. The agent must navigate a workspace, inspect messy files (CSV, unstructured text, nested JSON), and execute Python scripts to permanently redact Personally Identifiable Information (PII) without corrupting non-sensitive data.

---

## 🚀 Mission Overview

In a world of strict data regulations (GDPR, CCPA), companies must sanitize data before sharing it with analysts or LLMs. This environment tests an agent's ability to:
1. **Identify PII**: Recognise Credit Cards, SSNs, Emails, and Phone Numbers in various formats.
2. **Execute Precisely**: Write robust Python scripts using regex to redact only what is necessary.
3. **Ensure Integrity**: Maintain JSON structures, CSV row counts, and preserve non-sensitive numeric data (like Order IDs or timestamps).

### Tasks (Increasing Difficulty)
- **Easy**: Redact 16-digit credit card numbers from a simple 500-row CSV.
- **Medium**: Mask Social Security Numbers hidden inside unstructured plain-text chat logs while preserving dates and extensions.
- **Hard**: Recursively sanitize a complex, deeply nested JSON structure containing variable key names and mixed PII types.

---

## 🛠️ Action & Observation Space

- **Action Space**:
  - `bash`: Explore the file system (`ls`, `head`, `grep`).
  - `python`: Execute multi-line scripts to process and overwrite files in-place.
- **Observation Space**: Standard output (`stdout`), standard error (`stderr`), process exit codes, and a recursive snapshot of the workspace file tree.

---

## 📊 Evaluation & Grading

Each task is evaluated by a deterministic grader returning a score from **0.0 to 1.0**:
- **PII Removal (40-50%)**: Thoroughness of redaction using regex validation.
- **Structural Integrity (25%)**: Ensuring file formats and record counts remain intact.
- **Non-PII Preservation (25%)**: Penalizing "over-redaction" of non-sensitive data.

---

## 🏃 Getting Started

### Prerequisites
```bash
pip install -r requirements.txt
```

### Running the Environment Locally
```bash
export PYTHONPATH=$PYTHONPATH:.
uvicorn pii_redactor_env.server.app:app --port 7860
```

### Running the Baseline Agent
```bash
export OPENAI_API_KEY="your-key-here"
python -m pii_redactor_env.inference.inference --task easy
```

---

## 🏗️ Architecture
```text
/
├── openenv.yaml         # Environment metadata
├── Dockerfile           # Production container setup
├── requirements.txt     # Dependencies
└── pii_redactor_env/    # Core Package
    ├── server/          # FastAPI & WebSocket implementation
    ├── tasks/           # Grader logic and task registry
    ├── data/            # Seed data and generation scripts
    ├── inference/       # Baseline LLM inference script
    └── models.py        # Pydantic schemas
```
