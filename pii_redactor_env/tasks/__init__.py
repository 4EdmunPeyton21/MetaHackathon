from __future__ import annotations
from typing import Any
from pii_redactor_env.tasks.grader_easy import grade_easy
from pii_redactor_env.tasks.grader_medium import grade_medium
from pii_redactor_env.tasks.grader_hard import grade_hard

TASK_REGISTRY: dict[str, dict[str, Any]] = {
    "easy": {
        "id": "easy",
        "name": "Redact Credit Card Numbers from CSV",
        "seed_data_dir": "data/easy",
        "max_steps": 15,
        "grader": grade_easy,
    },
    "medium": {
        "id": "medium",
        "name": "Redact SSNs from Chat Logs",
        "seed_data_dir": "data/medium",
        "max_steps": 20,
        "grader": grade_medium,
    },
    "hard": {
        "id": "hard",
        "name": "Redact Mixed PII from Nested JSON",
        "seed_data_dir": "data/hard",
        "max_steps": 30,
        "grader": grade_hard,
    },
}

# The validator might look for a list of tasks named 'TASKS' or similar
TASKS = list(TASK_REGISTRY.values())
