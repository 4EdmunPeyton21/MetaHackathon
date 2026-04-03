"""
pii_redactor_env/inference/inference.py
----------------------------------------
Baseline inference agent for the PII Redactor environment.

Runs an agentic loop: observe → think (LLM) → act → grade.

CRITICAL: This script emits the EXACT log lines required by the
Meta × Hugging Face OpenEnv competition spec:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>

Usage:
    python -m pii_redactor_env.inference.inference --task easy
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Optional

import requests

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from pii_redactor_env.inference.config import (
    API_BASE_URL,
    API_KEY_ENV_VAR,
    BENCHMARK_NAME,
    ENV_BASE_URL,
    MAX_STEPS,
    MODEL_NAME,
    STEP_TIMEOUT_SECONDS,
)
from pii_redactor_env.inference.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

def _get_openai_client() -> Any:
    """Initialize and return an OpenAI client."""
    if OpenAI is None:
        raise RuntimeError(
            "openai package not installed. Run: pip install openai"
        )
    api_key = os.getenv(API_KEY_ENV_VAR)
    if not api_key:
        raise RuntimeError(
            f"Environment variable {API_KEY_ENV_VAR} is not set. "
            f"Export your OpenAI API key before running inference."
        )
    return OpenAI(api_key=api_key, base_url=API_BASE_URL)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = MODEL_NAME,
) -> str:
    """
    Send a prompt to the LLM and return the raw response text.

    Args:
        system_prompt: The system message defining the agent's role.
        user_prompt: The user message with current observation context.
        model: The model identifier (e.g., ``gpt-4o``).

    Returns:
        Raw response text from the LLM (expected to be a JSON action).
    """
    client = _get_openai_client()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        # Return a safe fallback action on API error
        return json.dumps({
            "action_type": "bash",
            "command": f"echo 'LLM API error: {str(e)[:100]}'"
        })


# ---------------------------------------------------------------------------
# Environment HTTP interaction
# ---------------------------------------------------------------------------

def env_reset(task_id: str) -> dict:
    """
    Call the environment's reset endpoint via HTTP.

    Args:
        task_id: One of ``"easy"``, ``"medium"``, ``"hard"``.

    Returns:
        Initial observation dict from the environment.
    """
    url = f"{ENV_BASE_URL}/reset"
    try:
        resp = requests.post(url, json={"task_id": task_id}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Failed to reset environment: {str(e)}",
            "exit_code": 1,
            "file_tree": [],
            "done": False,
            "reward": None,
            "error": str(e),
        }


def env_step(action: dict) -> dict:
    """
    Call the environment's step endpoint via HTTP.

    Args:
        action: Dict with ``action_type`` and ``command``.

    Returns:
        Observation dict from the environment.
    """
    url = f"{ENV_BASE_URL}/step"
    try:
        resp = requests.post(url, json=action, timeout=STEP_TIMEOUT_SECONDS + 10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Failed to step environment: {str(e)}",
            "exit_code": 1,
            "file_tree": [],
            "done": False,
            "reward": None,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Action parsing
# ---------------------------------------------------------------------------

def _parse_action(llm_response: str) -> dict:
    """
    Parse the LLM response into an action dict.
    Handles JSON wrapped in markdown code fences.
    """
    text = llm_response.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last line (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        action = json.loads(text)
        # Validate required keys
        if "action_type" not in action:
            action["action_type"] = "bash"
        if "command" not in action:
            action["command"] = "echo 'No command provided'"
        return action
    except json.JSONDecodeError:
        # Fallback: treat entire response as a bash command
        return {"action_type": "bash", "command": text[:500]}


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run_agent(task_id: str = "easy") -> None:
    """
    Run the baseline inference agent for a single task episode.

    Prints the competition-required [START], [STEP], [END] log lines.
    """
    task_name = task_id
    rewards: list[float] = []

    # ── [START] ──────────────────────────────────────────────
    print(f"[START] task={task_name} env={BENCHMARK_NAME} model={MODEL_NAME}")
    sys.stdout.flush()

    # ── Reset environment ────────────────────────────────────
    obs = env_reset(task_id)
    done = obs.get("done", False)
    step = 0

    # ── Agent loop ───────────────────────────────────────────
    while not done and step < MAX_STEPS:
        step += 1

        # Format prompt with current observation
        file_tree_str = "\n".join(obs.get("file_tree", [])) or "(empty)"
        reward_display = obs.get("reward")
        if reward_display is None:
            reward_display = "N/A"
        else:
            reward_display = f"{reward_display:.2f}"

        user_prompt = USER_PROMPT_TEMPLATE.format(
            task_name=task_name,
            step=step,
            max_steps=MAX_STEPS,
            file_tree=file_tree_str,
            stdout=obs.get("stdout", "")[:2000],
            stderr=obs.get("stderr", "")[:1000],
            exit_code=obs.get("exit_code", 0),
            reward=reward_display,
        )

        # Get LLM action
        llm_response = call_llm(SYSTEM_PROMPT, user_prompt)

        # Parse action
        action = _parse_action(llm_response)
        action_str = action.get("command", "")[:80]  # truncate for logging

        # Execute action in environment
        obs = env_step(action)

        reward = obs.get("reward", 0.0) or 0.0
        done = obs.get("done", False)
        error = obs.get("error", None)
        rewards.append(float(reward))

        # ── [STEP] ──────────────────────────────────────────
        error_str = error if error else "null"
        print(
            f"[STEP] step={step} "
            f"action={action_str} "
            f"reward={reward:.2f} "
            f"done={str(done).lower()} "
            f"error={error_str}"
        )
        sys.stdout.flush()

    # ── [END] ────────────────────────────────────────────────
    final_score = rewards[-1] if rewards else 0.0
    success = final_score >= 1.0
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} "
        f"steps={step} "
        f"score={final_score:.3f} "
        f"rewards={rewards_str}"
    )
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI args and run the agent."""
    parser = argparse.ArgumentParser(
        description="PII Redactor baseline inference agent"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="easy",
        choices=["easy", "medium", "hard"],
        help="Task difficulty to run (default: easy)",
    )
    args = parser.parse_args()
    run_agent(task_id=args.task)


if __name__ == "__main__":
    main()
