"""
pii_redactor_env/tasks/grader_medium.py
----------------------------------------
Deterministic grader for Task 2 (Medium): Redact SSNs from Chat Logs.

Grading Logic (returns float 0.0 – 1.0):
=========================================

1. **SSN Removal (50%)**: regex scan → 1.0 if zero SSN matches remain
2. **Message Structure Preservation (25%)**: line count + format check
3. **No Over-Redaction (25%)**: non-SSN numbers still present

Final = 0.50 * ssn_removal + 0.25 * structure + 0.25 * no_over_redaction
"""

from __future__ import annotations

import os
import re

# SSN pattern: exactly 3-2-4 digits with dashes
SSN_PATTERN: re.Pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Chat message format: [HH:MM:SS] username: message
MESSAGE_FORMAT: re.Pattern = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]\s+\w+:")

# Non-SSN numeric tokens to check for over-redaction:
# Order IDs (#12345), extension numbers, dollar amounts, counts, product IDs
NON_SSN_PATTERNS: list[re.Pattern] = [
    re.compile(r"#\d{4,}"),                    # Order/ticket IDs like #78432
    re.compile(r"\b\d{1,2}\.\d+ million\b"),   # Dollar amounts like 2.3 million
    re.compile(r"\b\d{3,4} (tickets|records)\b"),  # Counts like "147 tickets"
    re.compile(r"PRD-\d+"),                    # Product IDs
    re.compile(r"(?<!-)\b\d{4}\b"),            # 4-digit numbers (extensions, dates, times) not part of SSN
]


def _find_ssns(text: str) -> list[str]:
    """Find all SSN-pattern matches in text."""
    return SSN_PATTERN.findall(text)


def _find_non_ssn_numbers(text: str) -> set[str]:
    """Find all non-SSN numeric tokens that should be preserved."""
    tokens: set[str] = set()
    for pattern in NON_SSN_PATTERNS:
        tokens.update(pattern.findall(text))
    return tokens


def grade_medium(workspace_dir: str, baseline_dir: str) -> float:
    """
    Grade the agent's SSN redaction from chat logs.

    Args:
        workspace_dir: Path containing the redacted ``chat_logs.txt``.
        baseline_dir:  Path containing the original ``chat_logs.txt``.

    Returns:
        Score between 0.0 and 1.0.
    """
    redacted_path = os.path.join(workspace_dir, "chat_logs.txt")
    baseline_path = os.path.join(baseline_dir, "chat_logs.txt")

    # --- Guard: file must exist ---
    if not os.path.exists(redacted_path):
        return 0.0

    try:
        with open(redacted_path, "r", encoding="utf-8") as f:
            redacted_text = f.read()
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_text = f.read()
    except Exception:
        return 0.0

    redacted_lines = [l for l in redacted_text.strip().splitlines() if l.strip()]
    baseline_lines = [l for l in baseline_text.strip().splitlines() if l.strip()]

    # ── Component 1: SSN Removal (50%) ──────────────────────
    baseline_ssns = _find_ssns(baseline_text)
    redacted_ssns = _find_ssns(redacted_text)

    baseline_ssn_count = len(baseline_ssns)
    redacted_ssn_count = len(redacted_ssns)

    if baseline_ssn_count > 0:
        ssn_removal_score = 1.0 - (redacted_ssn_count / baseline_ssn_count)
    else:
        ssn_removal_score = 1.0
    ssn_removal_score = max(0.0, ssn_removal_score)

    # ── Component 2: Message Structure Preservation (25%) ───
    if not baseline_lines:
        structure_score = 0.0
    else:
        # Check line count
        line_count_ok = len(redacted_lines) == len(baseline_lines)

        # Check format preservation (each line still matches [HH:MM:SS] user: ...)
        preserved_format = 0
        for line in redacted_lines:
            if MESSAGE_FORMAT.match(line):
                preserved_format += 1

        format_ratio = preserved_format / len(baseline_lines) if baseline_lines else 0.0
        structure_score = 0.5 * (1.0 if line_count_ok else 0.0) + 0.5 * format_ratio

    # ── Component 3: No Over-Redaction (25%) ────────────────
    baseline_non_ssn = _find_non_ssn_numbers(baseline_text)

    if not baseline_non_ssn:
        over_redaction_score = 1.0
    else:
        preserved = 0
        for token in baseline_non_ssn:
            if token in redacted_text:
                preserved += 1
        over_redaction_score = preserved / len(baseline_non_ssn)

    # ── Final weighted score ────────────────────────────────
    final_score = (
        0.50 * ssn_removal_score
        + 0.25 * structure_score
        + 0.25 * over_redaction_score
    )
    return round(min(1.0, max(0.0, final_score)), 4)
