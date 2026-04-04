"""
pii_redactor_env/tests/test_e2e.py
------------------------------------
End-to-end test: connects to the server via WebSocket, runs a scripted
agent (no LLM needed), and verifies the grader produces a non-zero score.

Prerequisites:
    1. Server must be running:
       uvicorn pii_redactor_env.server.app:app --port 7860
    2. websockets must be installed:
       pip install websockets

Run:
    python tests/test_e2e.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import websockets
except ImportError:
    print("ERROR: websockets package required. Run: pip install websockets")
    sys.exit(1)


WS_URL = os.getenv("ENV_WS_URL", "ws://localhost:7860/ws")


# ── Response parsing helper ───────────────────────────────────

def parse_ws_response(response: dict) -> dict:
    """
    Parse an OpenEnv WebSocket response into a flat observation dict.

    The WS protocol wraps observations as:
        {"type": "observation", "data": {"observation": {...}, "reward": ..., "done": ...}}

    This function flattens it to:
        {"stdout": ..., "file_tree": ..., "reward": ..., "done": ...}
    """
    data = response.get("data", {})

    # The actual observation fields are nested under data.observation
    inner_obs = data.get("observation", {})

    # Merge reward/done from top-level data with the inner observation
    result = dict(inner_obs)
    if "reward" in data:
        result["reward"] = data["reward"]
    if "done" in data:
        result["done"] = data["done"]

    return result


# ── Scripted redaction commands for each task ─────────────────

EASY_REDACTION_SCRIPT = r'''
import re, csv, os

path = "customers.csv"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Redact credit card numbers
cc_pat = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")
content = cc_pat.sub("[REDACTED_CC]", content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Redacted {path} successfully")
'''

MEDIUM_REDACTION_SCRIPT = r'''
import re

path = "chat_logs.txt"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Redact SSNs only (format: XXX-XX-XXXX)
ssn_pat = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
content = ssn_pat.sub("[REDACTED_SSN]", content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Redacted {path} successfully")
'''

HARD_REDACTION_SCRIPT = r'''
import re

path = "records.json"
with open(path, "r", encoding="utf-8") as f:
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

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Redacted {path} successfully")
'''

TASK_SCRIPTS = {
    "easy": EASY_REDACTION_SCRIPT,
    "medium": MEDIUM_REDACTION_SCRIPT,
    "hard": HARD_REDACTION_SCRIPT,
}


async def run_e2e_test(task_id: str = "easy") -> float:
    """
    Run a scripted end-to-end test for the given task.

    Returns:
        Final grader score (0.0 - 1.0).
    """
    print(f"\n{'='*60}")
    print(f"  E2E TEST: task={task_id}")
    print(f"{'='*60}")

    async with websockets.connect(WS_URL) as ws:
        # -- Step 1: Reset --
        reset_msg = json.dumps({
            "type": "reset",
            "data": {"task_id": task_id},
        })
        await ws.send(reset_msg)
        raw = json.loads(await ws.recv())
        obs = parse_ws_response(raw)
        print(f"  Reset OK. Files: {obs.get('file_tree', [])}")

        # -- Step 2: Inspect files (bash ls) --
        step_msg = json.dumps({
            "type": "step",
            "data": {"action_type": "bash", "command": "ls -la"},
        })
        await ws.send(step_msg)
        raw = json.loads(await ws.recv())
        obs = parse_ws_response(raw)
        print(f"  ls output: {obs.get('stdout', '')[:200]}")
        print(f"  Reward after ls: {obs.get('reward', 'N/A')}")

        # -- Step 3: Run redaction script --
        script = TASK_SCRIPTS[task_id]
        step_msg = json.dumps({
            "type": "step",
            "data": {"action_type": "python", "command": script},
        })
        await ws.send(step_msg)
        raw = json.loads(await ws.recv())
        obs = parse_ws_response(raw)
        print(f"  Redaction stdout: {obs.get('stdout', '')[:200]}")
        print(f"  Redaction stderr: {obs.get('stderr', '')[:200]}")

        reward = obs.get("reward", 0.0) or 0.0
        done = obs.get("done", False)
        print(f"  Final reward: {reward:.4f}")
        print(f"  Done: {done}")

        # -- Close session --
        close_msg = json.dumps({"type": "close", "data": {}})
        await ws.send(close_msg)

    return reward


async def run_all_e2e():
    """Run E2E tests for all three tasks."""
    results = {}
    for task in ["easy", "medium", "hard"]:
        try:
            score = await run_e2e_test(task)
            results[task] = score
        except Exception as e:
            print(f"  [ERROR]: {task} -- {e}")
            results[task] = -1.0

    print(f"\n{'='*60}")
    print("  E2E RESULTS SUMMARY")
    print(f"{'='*60}")

    all_pass = True
    for task, score in results.items():
        if score < 0:
            status = "[ERROR]"
            all_pass = False
        elif score >= 0.85:
            status = "[PASS]"
        else:
            status = "[FAIL]"
            all_pass = False
        print(f"  {status}: {task} -- score={score:.4f}")

    print(f"{'='*60}")
    return all_pass


if __name__ == "__main__":
    success = asyncio.run(run_all_e2e())
    sys.exit(0 if success else 1)
