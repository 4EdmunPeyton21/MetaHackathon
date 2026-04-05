"""
pii_redactor_env/inference/inference.py
----------------------------------------
Baseline inference agent for the PII Redactor environment.

Uses the **PIIRedactorEnv** client to communicate with the server.
The client handles the WebSocket lifecycle and type conversions.

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
import asyncio
import json
import os
import sys
from typing import Any, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from pii_redactor_env.client import PIIRedactorEnv
from pii_redactor_env.models import PIIAction
from pii_redactor_env.inference.config import (
    API_BASE_URL,
    API_KEY_ENV_VAR,
    BENCHMARK_NAME,
    ENV_WS_URL,
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
        return json.dumps({
            "action_type": "bash",
            "command": f"echo 'LLM API error: {str(e)[:100]}'"
        })


# ---------------------------------------------------------------------------
# Action parsing
# ---------------------------------------------------------------------------

def _parse_action(llm_response: str) -> PIIAction:
    """
    Parse the LLM response into a PIIAction.
    Handles JSON wrapped in markdown code fences.
    """
    text = llm_response.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        action_dict = json.loads(text)
        return PIIAction(**action_dict)
    except Exception:
        # Fallback to bash if parsing fails
        return PIIAction(action_type="bash", command=text[:500])


# ---------------------------------------------------------------------------
# Main agent loop (async)
# ---------------------------------------------------------------------------

async def run_agent_async(task_id: str = "easy") -> None:
    """
    Run the baseline inference agent for a single task episode.

    Prints the competition-required [START], [STEP], [END] log lines.
    """
    task_name = task_id
    rewards: list[float] = []

    # ── [START] ──────────────────────────────────────────────
    print(f"[START] task={task_name} env={BENCHMARK_NAME} model={MODEL_NAME}")
    sys.stdout.flush()

    # ── Connect via Client ──────────────────────────────────
    # Map WebSocket URL to Base HTTP URL for the client if needed, 
    # but PIIRedactorEnv handles ws:// internally if passed as base_url?
    # Actually OpenEnv EnvClient expects the HTTP base URL and derives /ws.
    base_url = ENV_WS_URL.replace("ws://", "http://").replace("/ws", "")
    
    async with PIIRedactorEnv(base_url=base_url) as client:

        # ── Reset environment ────────────────────────────────
        result = await client.reset(task_id=task_id)
        obs = result.observation
        done = result.done
        step = 0

        # ── Agent loop ───────────────────────────────────────
        while not done and step < MAX_STEPS:
            step += 1

            # Format prompt with current observation
            file_tree_str = "\n".join(obs.file_tree) or "(empty)"
            reward_display = result.reward if result.reward is not None else 0.0

            user_prompt = USER_PROMPT_TEMPLATE.format(
                task_name=task_name,
                step=step,
                max_steps=MAX_STEPS,
                file_tree=file_tree_str,
                stdout=obs.stdout[:2000],
                stderr=obs.stderr[:1000],
                exit_code=obs.exit_code,
                reward=f"{reward_display:.2f}",
            )

            # Get LLM action
            llm_response = call_llm(SYSTEM_PROMPT, user_prompt)

            # Parse action
            action = _parse_action(llm_response)
            # Remove newlines from action command for single-line log emission
            action_command_clean = action.command.replace("\n", " ")[:100]

            # Execute action in environment
            result = await client.step(action)
            obs = result.observation
            reward = result.reward or 0.0
            done = result.done
            error = obs.error
            rewards.append(float(reward))

            # ── [STEP] ──────────────────────────────────────
            error_str = error if error else "null"
            print(
                f"[STEP] step={step} "
                f"action={action_command_clean} "
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


def run_agent(task_id: str = "easy") -> None:
    """Sync wrapper for the async agent loop."""
    asyncio.run(run_agent_async(task_id))


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
