"""
pii_redactor_env/tests/test_graders.py
---------------------------------------
Unit tests for all three graders.

Run: python -m pytest tests/test_graders.py -v
     or: python tests/test_graders.py
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import tempfile
import sys

# Allow running as standalone script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pii_redactor_env.tasks.grader_easy import grade_easy
from pii_redactor_env.tasks.grader_medium import grade_medium
from pii_redactor_env.tasks.grader_hard import grade_hard


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _get_data_dir(task: str) -> str:
    """Get absolute path to seed data directory."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "data", task)


def _make_workspace(task: str) -> str:
    """Copy seed data to a temp workspace and return the path."""
    seed_dir = _get_data_dir(task)
    workspace = tempfile.mkdtemp(prefix=f"test_{task}_")
    for item in os.listdir(seed_dir):
        src = os.path.join(seed_dir, item)
        dst = os.path.join(workspace, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    return workspace


# ═══════════════════════════════════════════════════════════════
# EASY: CSV Credit Card Redaction
# ═══════════════════════════════════════════════════════════════

def test_easy_unredacted_scores_low():
    """Unredacted data should score low (PII still present)."""
    workspace = _make_workspace("easy")
    baseline = _get_data_dir("easy")
    try:
        score = grade_easy(workspace, baseline)
        print(f"  Easy unredacted: {score:.4f}")
        # PII removal = 0.0, row preservation = 1.0, integrity = 1.0
        # Expected: 0.50*0.0 + 0.25*1.0 + 0.25*1.0 = 0.50
        assert 0.45 <= score <= 0.55, f"Expected ~0.50 but got {score}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_easy_perfect_redaction():
    """Perfectly redacted data should score ~1.0."""
    workspace = _make_workspace("easy")
    baseline = _get_data_dir("easy")
    try:
        # Redact all credit card patterns
        csv_path = os.path.join(workspace, "customers.csv")
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace CC patterns with redaction placeholder
        cc_pat = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")
        content = cc_pat.sub("[REDACTED_CC]", content)

        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(content)

        score = grade_easy(workspace, baseline)
        print(f"  Easy perfect redaction: {score:.4f}")
        assert score >= 0.95, f"Expected >= 0.95 but got {score}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_easy_missing_file():
    """Missing file should score 0.0."""
    workspace = tempfile.mkdtemp(prefix="test_empty_")
    baseline = _get_data_dir("easy")
    try:
        score = grade_easy(workspace, baseline)
        print(f"  Easy missing file: {score:.4f}")
        assert score == 0.0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# MEDIUM: Chat Log SSN Redaction
# ═══════════════════════════════════════════════════════════════

def test_medium_unredacted_scores_low():
    """Unredacted chat logs should score low."""
    workspace = _make_workspace("medium")
    baseline = _get_data_dir("medium")
    try:
        score = grade_medium(workspace, baseline)
        print(f"  Medium unredacted: {score:.4f}")
        # SSN removal = 0, structure = 1.0, over-redaction = 1.0
        # Expected ~0.50
        assert 0.45 <= score <= 0.55, f"Expected ~0.50 but got {score}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_medium_perfect_redaction():
    """Perfectly redacted chat logs should score ~1.0."""
    workspace = _make_workspace("medium")
    baseline = _get_data_dir("medium")
    try:
        chat_path = os.path.join(workspace, "chat_logs.txt")
        with open(chat_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace only SSNs
        ssn_pat = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        content = ssn_pat.sub("[REDACTED_SSN]", content)

        with open(chat_path, "w", encoding="utf-8") as f:
            f.write(content)

        score = grade_medium(workspace, baseline)
        print(f"  Medium perfect redaction: {score:.4f}")
        assert score >= 0.90, f"Expected >= 0.90 but got {score}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_medium_missing_file():
    """Missing file should score 0.0."""
    workspace = tempfile.mkdtemp(prefix="test_empty_")
    baseline = _get_data_dir("medium")
    try:
        score = grade_medium(workspace, baseline)
        print(f"  Medium missing file: {score:.4f}")
        assert score == 0.0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# HARD: Nested JSON Mixed PII Redaction
# ═══════════════════════════════════════════════════════════════

def test_hard_unredacted_scores_low():
    """Unredacted JSON should score low."""
    workspace = _make_workspace("hard")
    baseline = _get_data_dir("hard")
    try:
        score = grade_hard(workspace, baseline)
        print(f"  Hard unredacted: {score:.4f}")
        # PII removal = 0, structure + values + arrays = all 1.0
        # Expected: 0.40*0 + 0.25*1 + 0.25*1 + 0.10*1 = 0.60
        assert 0.55 <= score <= 0.65, f"Expected ~0.60 but got {score}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_hard_perfect_redaction():
    """Perfectly redacted JSON should score high."""
    workspace = _make_workspace("hard")
    baseline = _get_data_dir("hard")
    try:
        json_path = os.path.join(workspace, "records.json")
        with open(json_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Redact all PII types
        cc_pat = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")
        ssn_pat = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        email_pat = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        phone_pat = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

        content = cc_pat.sub("[REDACTED_CC]", content)
        content = ssn_pat.sub("[REDACTED_SSN]", content)
        content = email_pat.sub("[REDACTED_EMAIL]", content)
        content = phone_pat.sub("[REDACTED_PHONE]", content)

        with open(json_path, "w", encoding="utf-8") as f:
            f.write(content)

        score = grade_hard(workspace, baseline)
        print(f"  Hard perfect redaction: {score:.4f}")
        assert score >= 0.85, f"Expected >= 0.85 but got {score}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_hard_missing_file():
    """Missing file should score 0.0."""
    workspace = tempfile.mkdtemp(prefix="test_empty_")
    baseline = _get_data_dir("hard")
    try:
        score = grade_hard(workspace, baseline)
        print(f"  Hard missing file: {score:.4f}")
        assert score == 0.0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_hard_corrupted_json():
    """Corrupted JSON should score 0.0."""
    workspace = tempfile.mkdtemp(prefix="test_corrupt_")
    baseline = _get_data_dir("hard")
    try:
        # Write invalid JSON
        json_path = os.path.join(workspace, "records.json")
        with open(json_path, "w") as f:
            f.write("NOT VALID JSON {{{")

        score = grade_hard(workspace, baseline)
        print(f"  Hard corrupted JSON: {score:.4f}")
        assert score == 0.0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# Run all tests
# ═══════════════════════════════════════════════════════════════

def run_all():
    """Run all grader tests and print results."""
    tests = [
        ("EASY: Unredacted baseline", test_easy_unredacted_scores_low),
        ("EASY: Perfect redaction", test_easy_perfect_redaction),
        ("EASY: Missing file", test_easy_missing_file),
        ("MEDIUM: Unredacted baseline", test_medium_unredacted_scores_low),
        ("MEDIUM: Perfect redaction", test_medium_perfect_redaction),
        ("MEDIUM: Missing file", test_medium_missing_file),
        ("HARD: Unredacted baseline", test_hard_unredacted_scores_low),
        ("HARD: Perfect redaction", test_hard_perfect_redaction),
        ("HARD: Missing file", test_hard_missing_file),
        ("HARD: Corrupted JSON", test_hard_corrupted_json),
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("  GRADER UNIT TESTS")
    print("=" * 60)

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [PASS]: {name}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL]: {name} -- {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR]: {name} -- {e}")
            failed += 1

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
