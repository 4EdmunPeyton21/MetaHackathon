"""
pii_redactor_env/tasks/task_registry.py
----------------------------------------
Central registry mapping task IDs to their grader functions and seed data.

Each entry contains:
  - ``name``:          Human-readable task name (for logging / UI).
  - ``seed_data_dir``: Relative path to the seed data directory.
  - ``max_steps``:     Maximum steps allowed for this task.
  - ``grader``:        Callable(workspace_dir, baseline_dir) -> float [0.0, 1.0].
"""

from __future__ import annotations

from typing import Any, Callable

from pii_redactor_env.tasks.grader_easy import grade_easy
from pii_redactor_env.tasks.grader_medium import grade_medium
from pii_redactor_env.tasks.grader_hard import grade_hard


TASK_REGISTRY: dict[str, dict[str, Any]] = {
    "easy": {
        "name": "Redact Credit Card Numbers from CSV",
        "seed_data_dir": "data/easy",
        "max_steps": 15,
        "grader": grade_easy,
    },
    "medium": {
        "name": "Redact SSNs from Chat Logs",
        "seed_data_dir": "data/medium",
        "max_steps": 20,
        "grader": grade_medium,
    },
    "hard": {
        "name": "Redact Mixed PII from Nested JSON",
        "seed_data_dir": "data/hard",
        "max_steps": 30,
        "grader": grade_hard,
    },
}
