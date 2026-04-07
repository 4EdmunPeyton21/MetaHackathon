"""
pii_redactor_env/tasks/grader_easy.py
--------------------------------------
Deterministic grader for Task 1 (Easy): Redact Credit Card Numbers from CSV.

Grading Logic (returns float 0.0 – 1.0):
=========================================

1. **PII Removal (50%)**: regex scan for CC patterns → 1.0 if zero matches
2. **Row Count Preservation (25%)**: redacted row count == baseline row count
3. **Non-PII Data Integrity (25%)**: non-PII cells unchanged

Final = 0.50 * pii_removal + 0.25 * row_preservation + 0.25 * integrity
"""

from __future__ import annotations

import csv
import os
import re
from typing import Optional

# Credit card regex patterns combined into a single super-pattern for speed
SUPER_PATTERN: re.Pattern = re.compile(
    r"\b(?:\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}|\d{16})\b"
)

# Columns that are never PII (used for integrity checking)
NON_PII_COLUMNS: set[str] = {"id", "first_name", "last_name", "address"}


def _count_cc_matches(text: str) -> int:
    """Count all credit card pattern matches in a string using the optimized super-pattern."""
    return len(SUPER_PATTERN.findall(text))


def _read_csv(filepath: str) -> list[dict[str, str]]:
    """Read a CSV file into a list of dicts."""
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def grade_easy(workspace_dir: str, baseline_dir: str) -> float:
    """
    Grade the agent's CSV credit-card redaction.

    Args:
        workspace_dir: Path containing the redacted ``customers.csv``.
        baseline_dir:  Path containing the original ``customers.csv``.

    Returns:
        Score between 0.0 and 1.0.
    """
    redacted_path = os.path.join(workspace_dir, "customers.csv")
    baseline_path = os.path.join(baseline_dir, "customers.csv")

    # --- Guard: file must exist ---
    if not os.path.exists(redacted_path):
        return 0.0

    try:
        redacted_rows = _read_csv(redacted_path)
        baseline_rows = _read_csv(baseline_path)
    except Exception:
        return 0.0

    # ── Component 1: PII Removal (50%) ──────────────────────
    # Count CC matches in baseline (total PII to redact)
    baseline_cc_count = 0
    for row in baseline_rows:
        for value in row.values():
            baseline_cc_count += _count_cc_matches(value)

    # Count CC matches remaining in redacted file
    redacted_cc_count = 0
    for row in redacted_rows:
        for value in row.values():
            redacted_cc_count += _count_cc_matches(value)

    if baseline_cc_count > 0:
        pii_removal_score = 1.0 - (redacted_cc_count / baseline_cc_count)
    else:
        pii_removal_score = 1.0  # No PII to redact
    pii_removal_score = max(0.0, pii_removal_score)

    # ── Component 2: Row Count Preservation (25%) ───────────
    row_preservation_score = 1.0 if len(redacted_rows) == len(baseline_rows) else 0.0

    # ── Component 3: Non-PII Data Integrity (25%) ───────────
    if not baseline_rows or not redacted_rows:
        integrity_score = 0.0
    else:
        total_non_pii_cells = 0
        matching_cells = 0

        fieldnames = set(baseline_rows[0].keys()) if baseline_rows else set()
        non_pii_cols = fieldnames & NON_PII_COLUMNS

        for i, baseline_row in enumerate(baseline_rows):
            if i >= len(redacted_rows):
                break
            redacted_row = redacted_rows[i]
            for col in non_pii_cols:
                total_non_pii_cells += 1
                baseline_val = baseline_row.get(col, "")
                redacted_val = redacted_row.get(col, "")
                if baseline_val.strip() == redacted_val.strip():
                    matching_cells += 1

        if total_non_pii_cells > 0:
            integrity_score = matching_cells / total_non_pii_cells
        else:
            integrity_score = 1.0

    # ── Final weighted score ────────────────────────────────
    final_score = (
        0.50 * pii_removal_score
        + 0.25 * row_preservation_score
        + 0.25 * integrity_score
    )
    return round(min(1.0, max(0.0, final_score)), 4)
