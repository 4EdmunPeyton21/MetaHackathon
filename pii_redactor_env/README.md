# PII Redactor Environment

> **Data Privacy Compliance Benchmark** — An OpenEnv environment for the Meta x Hugging Face OpenEnv Hackathon 2026

## Overview

The PII Redactor Environment is designed to simulate the responsibilities of a Data Engineer or Privacy Officer tasked with sanitizing sensitive data. This environment evaluates the performance of AI agents in ensuring regulatory compliance (e.g., GDPR, CCPA) by identifying and removing Personally Identifiable Information (PII) from diverse datasets.

Agents are provided with simulated customer data in various formats, including CSV, unstructured text logs, and nested JSON files. The objective is to implement precise redactions (e.g., credit card numbers, SSNs, emails, and phone numbers) while maintaining data integrity for all non-sensitive information.

## Action and Observation Space

### Action Space (`PIIAction`)
Actions are submitted as JSON objects with the following parameters:
- **action_type**: Specifies the execution environment, either `"bash"` for system-level operations or `"python"` for script-based data processing.
- **command**: The specific shell command or Python source code to be executed within the workspace.

### Observation Space (`PIIObservation`)
The environment returns detailed feedback after each execution step:
- **stdout / stderr**: Standard output and error streams captured from the execution.
- **exit_code**: The process exit status (0 indicates successful execution).
- **file_tree**: A comprehensive list of relative file paths within the current workspace.
- **reward**: A performance score (0.0 to 1.0) derived from redaction accuracy and structural integrity.
- **done**: A boolean flag indicating the termination of the current episode.

## Tasks and Evaluation

The environment features three standardized tasks with increasing levels of complexity:

| Task ID | Difficulty | Objective | PII Focus |
| :--- | :--- | :--- | :--- |
| easy | Level 1 | Redact credit card numbers from a structured CSV file. | 16-digit CC numbers |
| medium | Level 2 | Extract and mask SSNs from unstructured chat transcripts. | XXX-XX-XXXX format |
| hard | Level 3 | Sanitize mixed PII from deeply nested JSON structures. | CC, SSN, Email, Phone |

### Grading Criteria
Performance is evaluated using a deterministic scoring system (0.0 to 1.0) based on:
- **Redaction Success (40-50%)**: Measured by the effective removal of all targeted PII.
- **Structural Integrity (25%)**: Ensures that file formats, row counts, and data schemas remain intact.
- **Non-PII Preservation (25%)**: Penalizes the inadvertent redaction of non-sensitive data points (e.g., IDs, product codes).

## Local Setup and Usage

### Package Installation
Install the package in development mode using the following command:
```bash
pip install -e .
```

### Server Execution
Launch the FastAPI server locally:
```bash
uvicorn pii_redactor_env.server.app:app --host 0.0.0.0 --port 7860
```

### Baseline Evaluation
Execute the baseline inference agent (OpenAI API key required):
```bash
python -m pii_redactor_env.inference.inference --task easy
```

## Baseline Performance Metrics

The following scores represent the results achieved by a scripted regex-based baseline agent:

| Task | Methodology | Performance Score | Success Rate |
| :--- | :--- | :--- | :--- |
| Easy | Scripted Regex | 1.000 | 100% |
| Medium | Scripted Regex | 1.000 | 100% |
| Hard | Scripted Regex | 1.000 | 100% |

## Technical Architecture

- **pii_redactor_env/models.py**: Definitions for Action, Observation, and State schemas.
- **pii_redactor_env/server/**: Implementation of the FastAPI server and execution logic.
- **pii_redactor_env/tasks/**: Deterministic grading logic for each benchmark task.
- **pii_redactor_env/data/**: Synthetic data generation scripts and seed datasets.
- **pii_redactor_env/client.py**: Standardized client for environment interaction.

## License

This project is licensed under the BSD-3-Clause License.
