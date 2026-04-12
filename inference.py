"""
Inference Script — PII Redactor Environment
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    LOCAL_IMAGE_NAME The name of the local image to use for the environment if you are using from_docker_image()

- Defaults are set only for API_BASE_URL and MODEL_NAME:
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

STDOUT FORMAT
- The script must emit exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw last_action_error string, or null if none.
    - All fields on a single line with no newlines within a line.
    - Each tasks should return score in [0, 1]
"""

import asyncio
import json
import os
import textwrap
from typing import List, Optional

from openai import OpenAI

from pii_redactor_env.client import PIIRedactorEnv
from pii_redactor_env.models import PIIAction

IMAGE_NAME = os.getenv("IMAGE_NAME")  # If you are using docker image
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
TASK_NAME = os.getenv("PII_REDACTOR_TASK", "easy")
BENCHMARK = os.getenv("PII_REDACTOR_BENCHMARK", "pii_redactor_env")
MAX_STEPS = 15
TEMPERATURE = 0.2
MAX_TOKENS = 2048
SUCCESS_SCORE_THRESHOLD = 0.5

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a Data Engineer specializing in PII redaction. You are working
    inside a sandboxed Linux environment with bash access.
    
    Your task is to find and redact Personally Identifiable Information (PII)
    from data files. PII types include: credit card numbers, Social Security
    Numbers (SSNs), email addresses, and phone numbers.
    
    Rules:
    - Use bash commands to read, process, and write files.
    - Replace PII with [REDACTED] placeholders.
    - Preserve the file structure, formatting, and all non-PII data.
    - Do not delete rows, change column order, or alter non-PII values.
    
    Reply with a JSON object containing:
    {
      "action_type": "bash",
      "command": "<your bash command>"
    }
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def build_user_prompt(task_name: str, step: int, max_steps: int,
                      file_tree: str, stdout: str, stderr: str,
                      exit_code: int, reward: float) -> str:
    return textwrap.dedent(
        f"""
        Task: {task_name}
        Step: {step}/{max_steps}
        
        Current file tree:
        {file_tree}
        
        Last command output (stdout):
        {stdout[:2000]}
        
        Last command errors (stderr):
        {stderr[:1000]}
        
        Last exit code: {exit_code}
        Current reward: {reward:.2f}
        
        Decide your next action. Reply with a JSON object:
        {{"action_type": "bash", "command": "<your command>"}}
        """
    ).strip()


def parse_action(llm_response: str) -> PIIAction:
    """Parse the LLM response into a PIIAction."""
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


def get_model_action(client: OpenAI, task_name: str, step: int, max_steps: int,
                     file_tree: str, stdout: str, stderr: str,
                     exit_code: int, reward: float) -> PIIAction:
    user_prompt = build_user_prompt(task_name, step, max_steps,
                                    file_tree, stdout, stderr,
                                    exit_code, reward)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        return parse_action(text) if text else PIIAction(action_type="bash", command="ls")
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return PIIAction(action_type="bash", command="ls")


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = await PIIRedactorEnv.from_docker_image(IMAGE_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task_id=TASK_NAME)
        obs = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            file_tree_str = "\n".join(obs.file_tree) if obs.file_tree else "(empty)"
            reward_display = result.reward if result.reward is not None else 0.0

            action = get_model_action(
                client, TASK_NAME, step, MAX_STEPS,
                file_tree_str,
                obs.stdout[:2000],
                obs.stderr[:1000],
                obs.exit_code,
                reward_display,
            )

            # Remove newlines from action command for single-line log emission
            action_command_clean = action.command.replace("\n", " ")[:100]

            result = await env.step(action)
            obs = result.observation
            reward = result.reward or 0.0
            done = result.done
            error = obs.error

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_command_clean, reward=reward, done=done, error=error)

            if done:
                break

        score = rewards[-1] if rewards else 0.0
        score = min(max(score, 0.0), 1.0)  # clamp to [0, 1]
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error (container cleanup): {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())
