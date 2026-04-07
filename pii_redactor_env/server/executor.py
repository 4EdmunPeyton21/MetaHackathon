"""
pii_redactor_env/server/executor.py
------------------------------------
Sandboxed command executor.

Refactored to use ``asyncio.create_subprocess_exec`` for non-blocking execution.
This allows the environment to handle multiple concurrent requests efficiently.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from pii_redactor_env.models import ActionType


class Executor:
    """
    Executes agent commands in a sandboxed subprocess asynchronously.
    """

    DEFAULT_TIMEOUT_SECONDS: int = 60
    MAX_OUTPUT_BYTES: int = 50_000

    async def execute(
        self,
        action_type: ActionType,
        command: str,
        workspace_dir: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Run a bash command or Python script inside the workspace asynchronously.
        """
        _timeout = timeout or self.DEFAULT_TIMEOUT_SECONDS

        try:
            if action_type == ActionType.BASH:
                process = await asyncio.create_subprocess_exec(
                    "bash", "-c", command,
                    cwd=workspace_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            elif action_type == ActionType.PYTHON:
                script_path = os.path.join(workspace_dir, "_agent_script.py")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(command)
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        "python", script_path,
                        cwd=workspace_dir,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                except Exception as e:
                    if os.path.exists(script_path):
                        os.remove(script_path)
                    raise e
            else:
                return {
                    "stdout": "",
                    "stderr": f"Unknown action_type: {action_type}",
                    "exit_code": 1,
                }

            try:
                # Wait for the process to complete with a timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=_timeout
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                exit_code = process.returncode
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()
                return {
                    "stdout": "",
                    "stderr": f"Command timed out after {_timeout} seconds.",
                    "exit_code": 124,
                }
            finally:
                # Clean up the temp script if it was created
                if action_type == ActionType.PYTHON:
                    script_path = os.path.join(workspace_dir, "_agent_script.py")
                    if os.path.exists(script_path):
                        os.remove(script_path)

            return {
                "stdout": self._truncate(stdout),
                "stderr": self._truncate(stderr),
                "exit_code": exit_code if exit_code is not None else 1,
            }

        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": 1,
            }

    def _truncate(self, text: str) -> str:
        """Truncate output to MAX_OUTPUT_BYTES."""
        if len(text) > self.MAX_OUTPUT_BYTES:
            return text[: self.MAX_OUTPUT_BYTES] + "\n... [output truncated]"
        return text
