"""
pii_redactor_env/tasks/grader_hard.py
--------------------------------------
Deterministic grader for Task 3 (Hard): Redact Mixed PII from Nested JSON.

Grading Logic (returns float 0.0 – 1.0):
=========================================

1. **PII Removal (40%)**: recursive scan for CC, SSN, email, phone
2. **JSON Structural Integrity (25%)**: all key paths preserved
3. **Non-PII Value Preservation (25%)**: non-PII leaf values unchanged
4. **Array Length Preservation (10%)**: arrays maintain their lengths

Final = 0.40 * pii + 0.25 * structure + 0.25 * values + 0.10 * arrays
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

# Combined super-pattern for all PII types for performance
SUPER_PII_PATTERN: re.Pattern = re.compile(
    r"(?P<cc>\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b)|"
    r"(?P<ssn>\b\d{3}-\d{2}-\d{4}\b)|"
    r"(?P<email>[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})|"
    r"(?P<phone>\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b)"
)


def _contains_pii(text: str) -> bool:
    """Check if a string contains any PII pattern using optimized super-pattern."""
    return bool(SUPER_PII_PATTERN.search(text))


def _count_pii_matches(text: str) -> int:
    """Count total PII pattern matches in a string using optimized super-pattern."""
    return len(SUPER_PII_PATTERN.findall(text))


def _collect_string_values(obj: Any, path: str = "") -> list[tuple[str, str]]:
    """
    Recursively collect all (path, string_value) pairs from a nested structure.
    """
    results: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            results.extend(_collect_string_values(value, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.extend(_collect_string_values(item, new_path))
    elif isinstance(obj, str):
        results.append((path, obj))
    return results


def _collect_key_paths(obj: Any, path: str = "") -> set[str]:
    """Recursively collect all key paths in a nested structure."""
    paths: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            paths.add(new_path)
            paths.update(_collect_key_paths(value, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            paths.update(_collect_key_paths(item, new_path))
    return paths


def _collect_arrays(obj: Any, path: str = "") -> list[tuple[str, int]]:
    """Recursively collect all (path, array_length) pairs."""
    results: list[tuple[str, int]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            results.extend(_collect_arrays(value, new_path))
    elif isinstance(obj, list):
        results.append((path, len(obj)))
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.extend(_collect_arrays(item, new_path))
    return results


def _get_by_path(obj: Any, path: str) -> Any:
    """Navigate a nested object by dot/bracket path. Returns None on miss."""
    try:
        parts = re.split(r"\.|\[(\d+)\]", path)
        parts = [p for p in parts if p is not None and p != ""]
        current = obj
        for part in parts:
            if part.isdigit():
                current = current[int(part)]
            else:
                current = current[part]
        return current
    except (KeyError, IndexError, TypeError):
        return None


def grade_hard(workspace_dir: str, baseline_dir: str) -> float:
    """
    Grade the agent's mixed PII redaction from deeply nested JSON.

    Args:
        workspace_dir: Path containing the redacted ``records.json``.
        baseline_dir:  Path containing the original ``records.json``.

    Returns:
        Score between 0.0 and 1.0.
    """
    redacted_path = os.path.join(workspace_dir, "records.json")
    baseline_path = os.path.join(baseline_dir, "records.json")

    # --- Guard: file must exist and be valid JSON ---
    if not os.path.exists(redacted_path):
        return 0.0

    try:
        with open(redacted_path, "r", encoding="utf-8") as f:
            redacted_data = json.load(f)
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)
    except (json.JSONDecodeError, Exception):
        return 0.0

    # ── Component 1: PII Removal (40%) ──────────────────────
    baseline_strings = _collect_string_values(baseline_data)
    redacted_strings = _collect_string_values(redacted_data)

    baseline_pii_count = sum(_count_pii_matches(val) for _, val in baseline_strings)
    redacted_pii_count = sum(_count_pii_matches(val) for _, val in redacted_strings)

    if baseline_pii_count > 0:
        pii_removal_score = 1.0 - (redacted_pii_count / baseline_pii_count)
    else:
        pii_removal_score = 1.0
    pii_removal_score = max(0.0, pii_removal_score)

    # ── Component 2: JSON Structural Integrity (25%) ────────
    baseline_keys = _collect_key_paths(baseline_data)
    redacted_keys = _collect_key_paths(redacted_data)

    if baseline_keys:
        matching_keys = baseline_keys & redacted_keys
        structure_score = len(matching_keys) / len(baseline_keys)
    else:
        structure_score = 1.0

    # ── Component 3: Non-PII Value Preservation (25%) ───────
    total_non_pii = 0
    preserved_non_pii = 0

    for path, value in baseline_strings:
        if not _contains_pii(value):
            total_non_pii += 1
            redacted_value = _get_by_path(redacted_data, path)
            if isinstance(redacted_value, str) and redacted_value.strip() == value.strip():
                preserved_non_pii += 1

    if total_non_pii > 0:
        value_preservation_score = preserved_non_pii / total_non_pii
    else:
        value_preservation_score = 1.0

    # ── Component 4: Array Length Preservation (10%) ────────
    baseline_arrays = _collect_arrays(baseline_data)
    if baseline_arrays:
        matching_arrays = 0
        for path, length in baseline_arrays:
            redacted_arr = _get_by_path(redacted_data, path)
            if isinstance(redacted_arr, list) and len(redacted_arr) == length:
                matching_arrays += 1
        array_score = matching_arrays / len(baseline_arrays)
    else:
        array_score = 1.0

    # ── Final weighted score ────────────────────────────────
    final_score = (
        0.40 * pii_removal_score
        + 0.25 * structure_score
        + 0.25 * value_preservation_score
        + 0.10 * array_score
    )
    return round(min(1.0, max(0.0, final_score)), 4)


def _collect_string_values(obj: Any, path: str = "") -> list[tuple[str, str]]:
    """
    Recursively collect all (path, string_value) pairs from a nested structure.
    """
    results: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            results.extend(_collect_string_values(value, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.extend(_collect_string_values(item, new_path))
    elif isinstance(obj, str):
        results.append((path, obj))
    return results


def _collect_key_paths(obj: Any, path: str = "") -> set[str]:
    """Recursively collect all key paths in a nested structure."""
    paths: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            paths.add(new_path)
            paths.update(_collect_key_paths(value, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            paths.update(_collect_key_paths(item, new_path))
    return paths


def _collect_arrays(obj: Any, path: str = "") -> list[tuple[str, int]]:
    """Recursively collect all (path, array_length) pairs."""
    results: list[tuple[str, int]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            results.extend(_collect_arrays(value, new_path))
    elif isinstance(obj, list):
        results.append((path, len(obj)))
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.extend(_collect_arrays(item, new_path))
    return results


def _get_by_path(obj: Any, path: str) -> Any:
    """Navigate a nested object by dot/bracket path. Returns None on miss."""
    try:
        parts = re.split(r"\.|\[(\d+)\]", path)
        parts = [p for p in parts if p is not None and p != ""]
        current = obj
        for part in parts:
            if part.isdigit():
                current = current[int(part)]
            else:
                current = current[part]
        return current
    except (KeyError, IndexError, TypeError):
        return None


def grade_hard(workspace_dir: str, baseline_dir: str) -> float:
    """
    Grade the agent's mixed PII redaction from deeply nested JSON.

    Args:
        workspace_dir: Path containing the redacted ``records.json``.
        baseline_dir:  Path containing the original ``records.json``.

    Returns:
        Score between 0.0 and 1.0.
    """
    redacted_path = os.path.join(workspace_dir, "records.json")
    baseline_path = os.path.join(baseline_dir, "records.json")

    # --- Guard: file must exist and be valid JSON ---
    if not os.path.exists(redacted_path):
        return 0.0

    try:
        with open(redacted_path, "r", encoding="utf-8") as f:
            redacted_data = json.load(f)
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)
    except (json.JSONDecodeError, Exception):
        return 0.0

    # ── Component 1: PII Removal (40%) ──────────────────────
    baseline_strings = _collect_string_values(baseline_data)
    redacted_strings = _collect_string_values(redacted_data)

    baseline_pii_count = sum(_count_pii_matches(val) for _, val in baseline_strings)
    redacted_pii_count = sum(_count_pii_matches(val) for _, val in redacted_strings)

    if baseline_pii_count > 0:
        pii_removal_score = 1.0 - (redacted_pii_count / baseline_pii_count)
    else:
        pii_removal_score = 1.0
    pii_removal_score = max(0.0, pii_removal_score)

    # ── Component 2: JSON Structural Integrity (25%) ────────
    baseline_keys = _collect_key_paths(baseline_data)
    redacted_keys = _collect_key_paths(redacted_data)

    if baseline_keys:
        matching_keys = baseline_keys & redacted_keys
        structure_score = len(matching_keys) / len(baseline_keys)
    else:
        structure_score = 1.0

    # ── Component 3: Non-PII Value Preservation (25%) ───────
    total_non_pii = 0
    preserved_non_pii = 0

    for path, value in baseline_strings:
        if not _contains_pii(value):
            total_non_pii += 1
            redacted_value = _get_by_path(redacted_data, path)
            if isinstance(redacted_value, str) and redacted_value.strip() == value.strip():
                preserved_non_pii += 1

    if total_non_pii > 0:
        value_preservation_score = preserved_non_pii / total_non_pii
    else:
        value_preservation_score = 1.0

    # ── Component 4: Array Length Preservation (10%) ────────
    baseline_arrays = _collect_arrays(baseline_data)
    if baseline_arrays:
        matching_arrays = 0
        for path, length in baseline_arrays:
            redacted_arr = _get_by_path(redacted_data, path)
            if isinstance(redacted_arr, list) and len(redacted_arr) == length:
                matching_arrays += 1
        array_score = matching_arrays / len(baseline_arrays)
    else:
        array_score = 1.0

    # ── Final weighted score ────────────────────────────────
    final_score = (
        0.40 * pii_removal_score
        + 0.25 * structure_score
        + 0.25 * value_preservation_score
        + 0.10 * array_score
    )
    return round(min(1.0, max(0.0, final_score)), 4)
