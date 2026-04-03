"""
pii_redactor_env/server/pii_environment.py
-------------------------------------------
Core environment class implementing the OpenEnv ``Environment`` interface.

This is the brain of the PII Redactor. It manages:
  • Episode lifecycle (reset / step / state)
  • Ephemeral workspace provisioning via ``WorkspaceManager``
  • Sandboxed command execution via ``Executor``
  • Grading via the task registry
"""

from __future__ import annotations

import uuid
from typing import Optional

from openenv.core.env_server import Environment

from pii_redactor_env.models import (
    ActionType,
    PIIAction,
    PIIObservation,
    PIIState,
)
from pii_redactor_env.server.executor import Executor
from pii_redactor_env.server.workspace import WorkspaceManager
from pii_redactor_env.tasks.task_registry import TASK_REGISTRY


class PIIRedactorEnvironment(Environment):
    """
    OpenEnv ``Environment`` subclass for the PII Redactor.

    Lifecycle
    ---------
    1. ``reset(task_id)`` — copies seed data into a fresh ephemeral workspace,
       resets episode counters, returns the initial observation (file tree).
    2. ``step(action)``  — executes the agent's bash/python command inside the
       workspace, captures output, optionally runs the grader, returns obs.
    3. ``state``         — property returning the current ``PIIState``.
    """

    def __init__(self) -> None:
        super().__init__()
        self._state: PIIState = PIIState()
        self._workspace: Optional[WorkspaceManager] = None
        self._executor: Executor = Executor()

    # ------------------------------------------------------------------
    # reset()
    # ------------------------------------------------------------------
    def reset(self, task_id: str = "easy") -> PIIObservation:
        """
        Initialize a new episode for the given task.

        Implementation plan:
        1. Look up ``task_id`` in ``TASK_REGISTRY`` to get the seed-data
           directory path and the max-steps limit.
        2. Create a new ``WorkspaceManager`` that deep-copies the seed data
           into a fresh temporary directory (``/tmp/workspace_<uuid>/``).
        3. Reset ``PIIState`` with a new ``episode_id``, zero step count,
           and the workspace path.
        4. Return an initial ``PIIObservation`` containing the file tree
           of the fresh workspace (so the agent knows what files exist).

        Args:
            task_id: One of ``"easy"``, ``"medium"``, ``"hard"``.

        Returns:
            Initial observation with the workspace file tree.
        """
        # --- validate task ---
        if task_id not in TASK_REGISTRY:
            return PIIObservation(
                stderr=f"Unknown task_id: {task_id}. Choose from: {list(TASK_REGISTRY.keys())}",
                exit_code=1,
                error=f"Invalid task_id: {task_id}",
            )

        task_info = TASK_REGISTRY[task_id]

        # --- provision workspace ---
        self._workspace = WorkspaceManager(seed_data_dir=task_info["seed_data_dir"])
        self._workspace.provision()

        # --- reset state ---
        self._state = PIIState(
            episode_id=str(uuid.uuid4()),
            task_id=task_id,
            task_name=task_info["name"],
            current_step=0,
            max_steps=task_info["max_steps"],
            done=False,
            last_reward=None,
            workspace_path=self._workspace.workspace_dir,
        )

        # --- build initial observation ---
        file_tree = self._workspace.get_file_tree()
        return PIIObservation(
            stdout="Environment reset. Workspace is ready.",
            stderr="",
            exit_code=0,
            file_tree=file_tree,
            done=False,
            reward=None,
            error=None,
        )

    # ------------------------------------------------------------------
    # step()
    # ------------------------------------------------------------------
    def step(self, action: PIIAction) -> PIIObservation:
        """
        Execute the agent's action and return the resulting observation.

        Implementation plan:
        1. Check if the episode is already done; if so, return an error obs.
        2. Increment ``current_step``.
        3. Dispatch to ``Executor``:
           - If ``action.action_type == BASH``: run the command via
             ``subprocess.run(bash -c <command>, cwd=workspace)``.
           - If ``action.action_type == PYTHON``: write the script to a temp
             file inside the workspace and run ``python <script.py>``.
        4. Capture stdout, stderr, and exit_code.
        5. Run the grader to compute the current reward score.
        6. If ``current_step >= max_steps``, set ``done = True``.
        7. Update ``PIIState`` and return the observation.

        Args:
            action: The agent's bash command or Python script.

        Returns:
            Observation with command output, updated file tree, and reward.
        """
        # --- guard: episode already ended ---
        if self._state.done:
            return PIIObservation(
                stderr="Episode has ended. Call reset() to start a new one.",
                exit_code=1,
                done=True,
                reward=self._state.last_reward,
                error="Episode already done.",
            )

        if self._workspace is None:
            return PIIObservation(
                stderr="No workspace. Call reset() first.",
                exit_code=1,
                error="Workspace not initialized.",
            )

        # --- increment step ---
        self._state.current_step += 1

        # --- execute action ---
        exec_result = self._executor.execute(
            action_type=action.action_type,
            command=action.command,
            workspace_dir=self._workspace.workspace_dir,
        )

        # --- run grader ---
        task_info = TASK_REGISTRY[self._state.task_id]
        grader_fn = task_info["grader"]
        reward = grader_fn(
            workspace_dir=self._workspace.workspace_dir,
            baseline_dir=self._workspace.seed_data_dir,
        )
        self._state.last_reward = reward

        # --- check termination ---
        if self._state.current_step >= self._state.max_steps:
            self._state.done = True

        if reward is not None and reward >= 1.0:
            self._state.done = True

        # --- build observation ---
        file_tree = self._workspace.get_file_tree()
        return PIIObservation(
            stdout=exec_result["stdout"],
            stderr=exec_result["stderr"],
            exit_code=exec_result["exit_code"],
            file_tree=file_tree,
            done=self._state.done,
            reward=reward,
            error=None,
        )

    # ------------------------------------------------------------------
    # state property
    # ------------------------------------------------------------------
    @property
    def state(self) -> PIIState:
        """
        Return the current episode state.

        This is called by the OpenEnv framework to populate the ``/state``
        HTTP endpoint.  It exposes episode metadata (task, step count,
        done flag, last reward) but NOT the full observation or file contents.

        Returns:
            Current PIIState instance.
        """
        return self._state
