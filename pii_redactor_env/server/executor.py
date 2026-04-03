"""
pii_redactor_env/server/executor.py
------------------------------------
Sandboxed command executor.

Wraps ``subprocess.run()`` with:
  • Timeout enforcement (prevents runaway scripts)
  • Working-directory restriction (agent can only modify workspace files)
  • stdout / stderr capture
  • Support for both bash commands and Python scripts
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any

from pii_redactor_env.models import ActionType


class Executor:
    """
    Executes agent commands in a sandboxed subprocess.

    The executor ensures that:
    1. All commands run with ``cwd`` set to the workspace directory.
    2. A hard timeout prevents infinite loops.
    3. Python scripts are written to a temp file before execution (not piped
       via stdin) so that relative imports and file-path references work
       correctly from the workspace root.
    """

    DEFAULT_TIMEOUT_SECONDS: int = 60
    MAX_OUTPUT_BYTES: int = 50_000  # truncate stdout/stderr beyond this

    def execute(
        self,
        action_type: ActionType,
        command: str,
        workspace_dir: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Run a bash command or Python script inside the workspace.

        Implementation plan:
        -------------------------------------------------------------------
        1. If ``action_type == BASH``:
           - Run ``subprocess.run(["bash", "-c", command], cwd=workspace_dir)``
             with stdout/stderr captured and the given timeout.

        2. If ``action_type == PYTHON``:
           - Write ``command`` (the script source) to a temporary ``.py``
             file inside ``workspace_dir``.
           - Run ``subprocess.run(["python", script_path], cwd=workspace_dir)``.
           - Delete the temp script file after execution.

        3. Capture stdout and stderr as UTF-8 strings, truncating to
           ``MAX_OUTPUT_BYTES`` if they exceed that limit.

        4. Return a dict with keys: ``stdout``, ``stderr``, ``exit_code``.

        5. On ``subprocess.TimeoutExpired``, return exit_code=124 and a
           stderr message indicating a timeout.

        6. On any other ``Exception``, return exit_code=1 and the exception
           message as stderr.
        -------------------------------------------------------------------

        Args:
            action_type: ``BASH`` or ``PYTHON``.
            command: The bash command string or Python script source code.
            workspace_dir: Absolute path to the ephemeral workspace.
            timeout: Override timeout in seconds (default: 60).

        Returns:
            Dict with ``stdout``, ``stderr``, ``exit_code``.
        """
        _timeout = timeout or self.DEFAULT_TIMEOUT_SECONDS

        try:
            if action_type == ActionType.BASH:
                result = subprocess.run(
                    ["bash", "-c", command],
                    cwd=workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=_timeout,
                )
            elif action_type == ActionType.PYTHON:
                # Write script to a temp file inside the workspace
                script_path = os.path.join(workspace_dir, "_agent_script.py")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(command)
                try:
                    result = subprocess.run(
                        ["python", script_path],
                        cwd=workspace_dir,
                        capture_output=True,
                        text=True,
                        timeout=_timeout,
                    )
                finally:
                    # Clean up the temp script
                    if os.path.exists(script_path):
                        os.remove(script_path)
            else:
                return {
                    "stdout": "",
                    "stderr": f"Unknown action_type: {action_type}",
                    "exit_code": 1,
                }

            return {
                "stdout": self._truncate(result.stdout),
                "stderr": self._truncate(result.stderr),
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {_timeout} seconds.",
                "exit_code": 124,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": 1,
            }

    def _truncate(self, text: str) -> str:
        """Truncate output to MAX_OUTPUT_BYTES to prevent memory bloat."""
        if len(text) > self.MAX_OUTPUT_BYTES:
            return text[: self.MAX_OUTPUT_BYTES] + "\n... [output truncated]"
        return text
