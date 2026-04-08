import json
import os
import re

PII_PATTERNS = {
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}

def _contains_pii(text: str) -> bool:
    for pattern in PII_PATTERNS.values():
        if pattern.search(text): return True
    return False

def _count_pii_matches(text: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in PII_PATTERNS.values())

def _collect_string_values(obj, path=""):
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items(): results.extend(_collect_string_values(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, item in enumerate(obj): results.extend(_collect_string_values(item, f"{path}[{i}]"))
    elif isinstance(obj, str):
        results.append((path, obj))
    return results

def _collect_key_paths(obj, path=""):
    paths = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            paths.add(new_path)
            paths.update(_collect_key_paths(v, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj): paths.update(_collect_key_paths(item, f"{path}[{i}]"))
    return paths

def _get_by_path(obj, path):
    try:
        parts = re.split(r"\.|\[(\d+)\]", path)
        parts = [p for p in parts if p]
        current = obj
        for part in parts:
            current = current[int(part)] if part.isdigit() else current[part]
        return current
    except: return None

def grade_hard(workspace_dir: str, baseline_dir: str) -> float:
    redacted_path = os.path.join(workspace_dir, "records.json")
    baseline_path = os.path.join(baseline_dir, "records.json")

    if not os.path.exists(redacted_path): return 0.0

    try:
        with open(redacted_path, "r", encoding="utf-8") as f: redacted_data = json.load(f)
        with open(baseline_path, "r", encoding="utf-8") as f: baseline_data = json.load(f)
    except: return 0.0

    baseline_strings = _collect_string_values(baseline_data)
    redacted_strings = _collect_string_values(redacted_data)

    baseline_pii_count = sum(_count_pii_matches(val) for _, val in baseline_strings)
    redacted_pii_count = sum(_count_pii_matches(val) for _, val in redacted_strings)
    pii_removal_score = 1.0 - (redacted_pii_count / baseline_pii_count) if baseline_pii_count > 0 else 1.0
    pii_removal_score = max(0.0, pii_removal_score)

    baseline_keys = _collect_key_paths(baseline_data)
    redacted_keys = _collect_key_paths(redacted_data)
    structure_score = len(baseline_keys & redacted_keys) / len(baseline_keys) if baseline_keys else 1.0

    total_non_pii = 0
    preserved_non_pii = 0
    for path, value in baseline_strings:
        if not _contains_pii(value):
            total_non_pii += 1
            redacted_val = _get_by_path(redacted_data, path)
            if isinstance(redacted_val, str) and redacted_val.strip() == value.strip(): preserved_non_pii += 1
    value_preservation_score = preserved_non_pii / total_non_pii if total_non_pii > 0 else 1.0

    final_score = 0.40 * pii_removal_score + 0.25 * structure_score + 0.25 * value_preservation_score + 0.10 * 1.0
    return round(min(1.0, max(0.0, final_score)), 4)
