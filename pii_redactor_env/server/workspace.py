"""
pii_redactor_env/server/workspace.py
-------------------------------------
Workspace manager for ephemeral episode directories.

Responsibilities:
  • Deep-copy seed data into a fresh temp directory on ``provision()``.
  • Provide a file-tree listing of the workspace.
  • Clean up temp directories when episodes end.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


class WorkspaceManager:
    """
    Manages an ephemeral workspace directory for a single episode.

    On ``provision()``, the seed data for the current task is deep-copied
    into a new temporary directory. The agent's commands run inside this
    directory. When the episode ends (or a new ``reset()`` is called),
    the previous workspace can be cleaned up.

    Attributes:
        seed_data_dir: Path to the source seed data (e.g., ``data/easy/``).
        workspace_dir: Path to the provisioned ephemeral workspace.
    """

    def __init__(self, seed_data_dir: str) -> None:
        """
        Args:
            seed_data_dir: Absolute or relative path to the seed data directory
                           for the current task.
        """
        self.seed_data_dir: str = seed_data_dir
        self.workspace_dir: str = ""

    def provision(self) -> str:
        """
        Create a fresh workspace by deep-copying seed data.

        Implementation plan:
        1. Create a new temp directory: ``/tmp/pii_workspace_<uuid>/``
        2. Use ``shutil.copytree()`` to recursively copy all files from
           ``self.seed_data_dir`` into the new workspace.
        3. Store the workspace path in ``self.workspace_dir``.
        4. Return the workspace path.

        Returns:
            Absolute path to the provisioned workspace directory.
        """
        # Resolve the seed data directory relative to this file's location
        base_dir = Path(__file__).resolve().parent.parent
        seed_path = base_dir / self.seed_data_dir

        # Create a unique temp workspace
        workspace = tempfile.mkdtemp(prefix="pii_workspace_")

        # Deep-copy seed data into workspace
        if seed_path.is_dir():
            # Copy contents of seed dir into workspace root
            for item in seed_path.iterdir():
                dest = os.path.join(workspace, item.name)
                if item.is_dir():
                    shutil.copytree(str(item), dest)
                else:
                    shutil.copy2(str(item), dest)

        self.workspace_dir = workspace
        return workspace

    def get_file_tree(self) -> list[str]:
        """
        Return a list of relative file paths in the workspace.

        Implementation plan:
        1. Walk ``self.workspace_dir`` using ``os.walk()``.
        2. For each file, compute its path relative to the workspace root.
        3. Exclude hidden files (``.*``) and ``_agent_script.py`` (temp).
        4. Return sorted list of relative paths.

        Returns:
            Sorted list of relative file paths.
        """
        if not self.workspace_dir or not os.path.isdir(self.workspace_dir):
            return []

        file_tree: list[str] = []
        for root, dirs, files in os.walk(self.workspace_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if fname.startswith(".") or fname == "_agent_script.py":
                    continue
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, self.workspace_dir)
                file_tree.append(rel_path)

        return sorted(file_tree)

    def cleanup(self) -> None:
        """
        Remove the ephemeral workspace directory.

        Called when a new episode starts (via ``reset()``) or when the
        environment is shutting down.
        """
        if self.workspace_dir and os.path.isdir(self.workspace_dir):
            shutil.rmtree(self.workspace_dir, ignore_errors=True)
            self.workspace_dir = ""
