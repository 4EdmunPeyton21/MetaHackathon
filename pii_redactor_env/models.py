"""
pii_redactor_env/models.py
--------------------------
Pydantic schemas defining the data contract between client and server.

Action space: The agent submits bash commands or Python scripts.
Observation space: stdout, stderr, file tree snapshot, and task completion info.
State: Episode metadata — current task, step count, done flag.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from openenv.core.env_server.interfaces import Action, Observation, State


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    """The type of action the agent is submitting."""
    BASH = "bash"
    PYTHON = "python"


class PIIAction(Action):
    """
    An action the agent submits to the environment.

    The agent may either run a bash command (e.g. ``ls``, ``head -5 file.csv``)
    or execute a multi-line Python script that processes the workspace files.

    Attributes:
        action_type: Whether this is a ``bash`` command or ``python`` script.
        command: The bash command string, OR the full Python script source code.
    """

    action_type: ActionType = ActionType.BASH
    command: str = ""


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class PIIObservation(Observation):
    """
    The observation returned to the agent after each step.

    Attributes:
        stdout: Captured standard output from the executed command/script.
        stderr: Captured standard error from the executed command/script.
        exit_code: Process exit code (0 = success).
        file_tree: A list of relative file paths currently in the workspace.
        done: Whether the episode has ended (max steps reached or agent quit).
        reward: The grader score for the current state (0.0 – 1.0), or None
                if grading has not been triggered yet.
        error: Human-readable error message if the action was invalid.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    file_tree: list[str] = []
    done: bool = False
    reward: Optional[float] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class PIIState(State):
    """
    Server-side episode state exposed via the ``state()`` API.

    Attributes:
        task_id: The current task identifier (``easy``, ``medium``, ``hard``).
        task_name: Human-readable task name for logging.
        current_step: Number of steps taken so far in this episode.
        max_steps: Maximum steps allowed for this task before auto-termination.
        done: Whether the episode has ended.
        last_reward: Most recent grader score, or None if not yet graded.
        workspace_path: Absolute path to the ephemeral workspace directory.
    """

    task_id: str = "easy"
    task_name: str = ""
    current_step: int = 0
    max_steps: int = 15
    done: bool = False
    last_reward: Optional[float] = None
    workspace_path: str = ""
