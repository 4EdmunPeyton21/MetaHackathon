import os
import re

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
MESSAGE_FORMAT = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]\s+\w+:")
NON_SSN_PATTERNS = [
    re.compile(r"#\d{4,}"),
    re.compile(r"\b\d{1,2}\.\d+ million\b"),
    re.compile(r"\b\d{3,4} (tickets|records)\b"),
    re.compile(r"PRD-\d+"),
    re.compile(r"(?<!-)\b\d{4}\b"),
]

def _find_ssns(text: str) -> list[str]:
    return SSN_PATTERN.findall(text)

def _find_non_ssn_numbers(text: str) -> set[str]:
    tokens = set()
    for pattern in NON_SSN_PATTERNS:
        tokens.update(pattern.findall(text))
    return tokens

def grade_medium(workspace_dir: str, baseline_dir: str) -> float:
    redacted_path = os.path.join(workspace_dir, "chat_logs.txt")
    baseline_path = os.path.join(baseline_dir, "chat_logs.txt")

    if not os.path.exists(redacted_path):
        return 0.0

    try:
        with open(redacted_path, "r", encoding="utf-8") as f: redacted_text = f.read()
        with open(baseline_path, "r", encoding="utf-8") as f: baseline_text = f.read()
    except Exception:
        return 0.0

    redacted_lines = [l for l in redacted_text.strip().splitlines() if l.strip()]
    baseline_lines = [l for l in baseline_text.strip().splitlines() if l.strip()]

    baseline_ssn_count = len(_find_ssns(baseline_text))
    redacted_ssn_count = len(_find_ssns(redacted_text))

    ssn_removal_score = 1.0 - (redacted_ssn_count / baseline_ssn_count) if baseline_ssn_count > 0 else 1.0
    ssn_removal_score = max(0.0, ssn_removal_score)

    if not baseline_lines:
        structure_score = 0.0
    else:
        line_count_ok = len(redacted_lines) == len(baseline_lines)
        preserved_format = sum(1 for line in redacted_lines if MESSAGE_FORMAT.match(line))
        format_ratio = preserved_format / len(baseline_lines)
        structure_score = 0.5 * (1.0 if line_count_ok else 0.0) + 0.5 * format_ratio

    baseline_non_ssn = _find_non_ssn_numbers(baseline_text)
    over_redaction_score = sum(1 for token in baseline_non_ssn if token in redacted_text) / len(baseline_non_ssn) if baseline_non_ssn else 1.0

    final_score = 0.50 * ssn_removal_score + 0.25 * structure_score + 0.25 * over_redaction_score
    return round(min(1.0, max(0.0, final_score)), 4)
