---
title: PII Redactor Environment
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: bsd-3-clause
---

# PII Redactor Environment

**Domain**: Data Engineering & Information Security  
**Project Type**: OpenEnv Benchmark for Meta x Hugging Face Hackathon 2026

The PII Redactor environment provides a standardized platform for evaluating AI agents on their ability to perform automated data sanitization. In this environment, an agent assumes the role of a Data Engineer responsible for identifying and redacting Personally Identifiable Information (PII) across diverse datasets, including CSV files, unstructured chat logs, and deeply nested JSON structures.

The core objective is to ensure regulatory compliance by removing sensitive data while maintaining the structural and contextual integrity of the non-sensitive information.

---

## Environment Objectives

This benchmark evaluates an agent's capability across three primary dimensions:

1.  **PII Identification**: Accurately identifying sensitive data such as Credit Card numbers, Social Security Numbers (SSNs), email addresses, and phone numbers in varied formats.
2.  **Precise Execution**: Generating and executing robust scripts (e.g., Python/Regex) to perform targeted redactions.
3.  **Data Integrity**: Ensuring that file structures, record counts, and non-sensitive numeric data remain unchanged throughout the process.

### Task Difficulty Levels
-   **Easy**: Redaction of 16-digit credit card numbers from a structured CSV dataset.
-   **Medium**: Extraction and masking of Social Security Numbers from unstructured text-based chat transcripts.
-   **Hard**: Recursive sanitization of complex, multi-level JSON objects containing mixed PII types.

---

## Action and Observation Space

### Action Space
Agents interact with the environment through two primary action types:
-   **Bash**: For environment exploration, file inspection, and verification of results.
-   **Python**: For executing comprehensive data processing scripts that modify files in-place.

### Observation Space
The environment provides feedback after each action, including:
-   Standard output (stdout) and standard error (stderr).
-   Process exit codes indicating success or failure.
-   A recursive snapshot of the current workspace file tree.

---

## Evaluation and Scoring

Performance is measured using deterministic graders that provide a score between 0.0 and 1.0 based on the following weighted criteria:

-   **Redaction Accuracy (40-50%)**: The proportion of PII successfully identified and removed.
-   **Structural Integrity (25%)**: Verification that the underlying file format and record count are preserved.
-   **Non-PII Preservation (25%)**: Ensuring that non-sensitive data points remain intact.

---

## Getting Started

### Prerequisites
Install the required dependencies using the following command:
```bash
pip install -r requirements.txt
```

### Local Environment Execution
To run the environment server locally:
```bash
export PYTHONPATH=$PYTHONPATH:.
uvicorn pii_redactor_env.server.app:app --port 7860
```

### Baseline Agent Execution
To run the baseline inference agent (requires a valid OpenAI API key):
```bash
export OPENAI_API_KEY="your_api_key_here"
python -m pii_redactor_env.inference.inference --task easy
```

---

## Project Architecture
```text
/
├── openenv.yaml         # Environment configuration and metadata
├── Dockerfile           # Containerization configuration
├── requirements.txt     # Project dependencies
└── pii_redactor_env/    # Core package directory
    ├── server/          # FastAPI and WebSocket implementation
    ├── tasks/           # Deterministic graders and task definitions
    ├── data/            # Synthetic datasets and generation logic
    ├── inference/       # Baseline LLM inference implementation
    └── models.py        # Pydantic data models
```
