"""Shared fixtures for agent-handoff tests that need real Git history.

The baseline (`--since`) and delta features are thin wrappers over Git's own
range and diff semantics, so they are exercised against a real repository
rather than a mocked `run_git`: a stubbed diff would pin this suite to our
assumptions about Git's output instead of to Git's behavior.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class GitRepo:
    """A throwaway repository with a fixed identity and no user configuration."""

    root: Path
    environment: dict[str, str]

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
            env=self.environment,
        )
        return completed.stdout

    def write(self, relative: str, text: str) -> None:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "--no-verify", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> GitRepo:
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    root = tmp_path / "repo"
    root.mkdir()
    repository = GitRepo(root=root, environment=environment)
    repository.git("init", "-q", "-b", "main")
    return repository
