"""
pii_redactor_env/server/pii_environment.py
-------------------------------------------
Core environment class implementing the OpenEnv ``Environment`` interface.

This is the brain of the PII Redactor. It manages:
  • Episode lifecycle (reset / step / state)
  • Ephemeral workspace provisioning via ``WorkspaceManager``
  • Sandboxed command execution via ``Executor``
  • Grading via the task registry

IMPORTANT: The OpenEnv HTTPEnvServer creates a NEW environment instance
per HTTP request. Only the WebSocket endpoint (/ws) persists state across
calls. The reset() and step() signatures MUST match the base class.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

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

    Lifecycle (via WebSocket /ws endpoint for stateful sessions)
    -------------------------------------------------------------
    1. ``reset(task_id=...)`` — copies seed data into a fresh ephemeral workspace,
       resets episode counters, returns the initial observation (file tree).
    2. ``step(action)``  — executes the agent's bash/python command inside the
       workspace, captures output, runs the grader, returns obs.
    3. ``state``         — property returning the current ``PIIState``.
    """

    # Enable concurrent WebSocket sessions (each gets its own instance)
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self) -> None:
        super().__init__()
        self._state: PIIState = PIIState()
        self._workspace: Optional[WorkspaceManager] = None
        self._executor: Executor = Executor()

    # ------------------------------------------------------------------
    # reset() — signature matches base class Environment.reset()
    # ------------------------------------------------------------------
    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> PIIObservation:
        """
        Initialize a new episode for the given task.

        Args:
            seed: Optional random seed. If provided, seed data is regenerated.
            episode_id: Optional episode ID for tracking.
            **kwargs: Must include ``task_id`` (one of "easy", "medium", "hard").

        Returns:
            Initial observation with the workspace file tree.
        """
        task_id = kwargs.get("task_id", "easy")

        # --- validate task ---
        if task_id not in TASK_REGISTRY:
            return PIIObservation(
                stderr=f"Unknown task_id: {task_id}. Choose from: {list(TASK_REGISTRY.keys())}",
                exit_code=1,
                error=f"Invalid task_id: {task_id}",
            )

        task_info = TASK_REGISTRY[task_id]

        # --- Optional: Regenerate data if seed is provided ---
        if seed is not None:
            try:
                from pii_redactor_env.data import generate_seed_data
                import random
                import faker
                # Set global seeds for regeneration
                random.seed(seed)
                faker.Faker.seed(seed)
                
                if task_id == "easy":
                    generate_seed_data.generate_easy_csv()
                elif task_id == "medium":
                    generate_seed_data.generate_medium_chat()
                elif task_id == "hard":
                    generate_seed_data.generate_hard_json()
            except Exception as e:
                # Log error but continue with existing static seed data
                pass

        # --- cleanup previous workspace if any ---
        if self._workspace is not None:
            self._workspace.cleanup()

        # --- provision workspace ---
        self._workspace = WorkspaceManager(seed_data_dir=task_info["seed_data_dir"])
        self._workspace.provision()

        # --- reset state ---
        self._state = PIIState(
            episode_id=episode_id or str(uuid.uuid4()),
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
    # step() — signature matches base class Environment.step()
    # ------------------------------------------------------------------
    def step(
        self,
        action: PIIAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> PIIObservation:
        """
        Execute the agent's action and return the resulting observation.
        Uses asyncio.run() to execute the asynchronous executor from this
        synchronous method (FastAPI runs this in a thread pool).
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

        # --- execute action asynchronously via asyncio.run ---
        exec_timeout = int(timeout_s) if timeout_s else None
        
        import asyncio
        try:
            exec_result = asyncio.run(self._executor.execute(
                action_type=action.action_type,
                command=action.command,
                workspace_dir=self._workspace.workspace_dir,
                timeout=exec_timeout,
            ))
        except RuntimeError:
            # Fallback for cases where an event loop is already running in this thread
            loop = asyncio.new_event_loop()
            try:
                exec_result = loop.run_until_complete(self._executor.execute(
                    action_type=action.action_type,
                    command=action.command,
                    workspace_dir=self._workspace.workspace_dir,
                    timeout=exec_timeout,
                ))
            finally:
                loop.close()

        # --- run grader ---
        task_info = TASK_REGISTRY[self._state.task_id]
        grader_fn = task_info["grader"]
        try:
            reward = grader_fn(
                workspace_dir=self._workspace.workspace_dir,
                baseline_dir=self._workspace.abs_seed_data_dir,
            )
        except Exception as e:
            reward = 0.0

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
        """Return the current episode state."""
        return self._state

    # ------------------------------------------------------------------
    # close() — cleanup resources
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Clean up the ephemeral workspace when the session ends."""
        if self._workspace is not None:
            self._workspace.cleanup()
            self._workspace = None
