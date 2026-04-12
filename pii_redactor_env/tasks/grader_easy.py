import csv
import os
import re

CC_PATTERNS = [
    re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    re.compile(r"\b\d{16}\b"),
]

NON_PII_COLUMNS = {"id", "first_name", "last_name", "address"}

def _count_cc_matches(text: str) -> int:
    count = 0
    for pattern in CC_PATTERNS:
        count += len(pattern.findall(text))
    return count

def _read_csv(filepath: str) -> list[dict[str, str]]:
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)

def grade_easy(workspace_dir: str, baseline_dir: str) -> float:
    redacted_path = os.path.join(workspace_dir, "customers.csv")
    baseline_path = os.path.join(baseline_dir, "customers.csv")

    if not os.path.exists(redacted_path):
        return 0.01

    try:
        redacted_rows = _read_csv(redacted_path)
        baseline_rows = _read_csv(baseline_path)
    except Exception:
        return 0.01

    baseline_cc_count = 0
    for row in baseline_rows:
        for value in row.values():
            baseline_cc_count += _count_cc_matches(value)

    redacted_cc_count = 0
    for row in redacted_rows:
        for value in row.values():
            redacted_cc_count += _count_cc_matches(value)

    if baseline_cc_count > 0:
        pii_removal_score = 1.0 - (redacted_cc_count / baseline_cc_count)
    else:
        pii_removal_score = 1.0
    pii_removal_score = max(0.0, pii_removal_score)

    row_preservation_score = 1.0 if len(redacted_rows) == len(baseline_rows) else 0.0

    if not baseline_rows or not redacted_rows:
        integrity_score = 0.0
    else:
        total_non_pii_cells = 0
        matching_cells = 0
        fieldnames = set(baseline_rows[0].keys())
        non_pii_cols = fieldnames & NON_PII_COLUMNS

        for i, baseline_row in enumerate(baseline_rows):
            if i >= len(redacted_rows): break
            redacted_row = redacted_rows[i]
            for col in non_pii_cols:
                total_non_pii_cells += 1
                if baseline_row.get(col, "").strip() == redacted_row.get(col, "").strip():
                    matching_cells += 1
        integrity_score = matching_cells / total_non_pii_cells if total_non_pii_cells > 0 else 1.0

    final_score = 0.50 * pii_removal_score + 0.25 * row_preservation_score + 0.25 * integrity_score
    return round(min(0.99, max(0.01, final_score)), 4)
