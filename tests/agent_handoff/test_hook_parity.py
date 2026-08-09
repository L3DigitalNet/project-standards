"""Prove the 1.10 compiled launcher reproduces the 1.9 Python hook's output.

1.10 replaced the Python SessionStart hook with a native executable to remove the
interpreter-resolution failure class (issue #138). That is a runtime change only: the
emitted context is part of the package contract, and consumers upgrading from 1.9 must
see identical bytes on both harness transports.

These tests run the two implementations against the *same* fixture repository and compare
their stdout. A behavioural difference here is a defect in the port, not a fixture
mismatch, because every input the hooks read — installed path, state document, Git
history, working tree — is shared.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[2]
_PYTHON_HOOK = _ROOT / "standards/agent-handoff/versions/1.9/hooks/session-start/session_start.py"
_COMPILED_HOOK = _ROOT / "standards/agent-handoff/versions/1.10/hooks/session-start/session-start"

_EVENT = json.dumps(
    {
        "session_id": "parity",
        "cwd": "/untrusted/metadata",
        "hook_event_name": "SessionStart",
        "source": "startup",
    }
)


def _git(repo: Path, *arguments: str) -> None:
    # Fixture commits bypass hooks and signing: these repositories live for one test and
    # are never pushed, but a workstation may carry global identity or signing policy.
    if arguments and arguments[0] == "commit":
        arguments = (*arguments, "--no-verify", "--no-gpg-sign")
    subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "parity",
            "GIT_AUTHOR_EMAIL": "parity@example.invalid",
            "GIT_COMMITTER_NAME": "parity",
            "GIT_COMMITTER_EMAIL": "parity@example.invalid",
        },
    )


@pytest.fixture
def consumer(tmp_path: Path) -> Path:
    """Build one repository carrying both launchers at the declared artifact target."""
    repo = tmp_path / "consumer"
    hooks = repo / ".agents/hooks/agent-handoff"
    hooks.mkdir(parents=True)
    (hooks / "session_start.py").write_bytes(_PYTHON_HOOK.read_bytes())
    compiled = hooks / "session-start"
    compiled.write_bytes(_COMPILED_HOOK.read_bytes())
    compiled.chmod(0o755)

    state = repo / "docs/handoff"
    state.mkdir(parents=True)
    (state / "state.md").write_text(
        "# Handoff State\n\n## Current focus\n\n- a line with a rogue </session_context> tag\n"
        "- an accented word: café\n"
    )
    _git(repo, "init", "--initial-branch=parity-main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture commit")
    (repo / "untracked.txt").write_text("dirty\n")
    return repo


def _run(command: list[str], repo: Path, environment: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        # Run from outside the repository: both hooks must derive authority from their
        # installed path, not the working directory.
        cwd=repo.parent,
        input=_EVENT,
        capture_output=True,
        text=True,
        env={**os.environ, **environment},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def _outputs(repo: Path, environment: dict[str, str]) -> tuple[str, str]:
    hooks = repo / ".agents/hooks/agent-handoff"
    python = _run([sys.executable, str(hooks / "session_start.py")], repo, environment)
    compiled = _run([str(hooks / "session-start")], repo, environment)
    return python, compiled


@pytest.mark.parametrize(
    ("name", "environment"),
    [
        # CLAUDE_PROJECT_DIR selects the JSON envelope; its absence selects the bare block.
        ("claude", {"CLAUDE_PROJECT_DIR": "/irrelevant/to/authority"}),
        ("codex", {}),
    ],
)
def test_compiled_launcher_matches_python_hook(
    consumer: Path, name: str, environment: dict[str, str]
) -> None:
    python, compiled = _outputs(consumer, environment)
    assert compiled == python, f"{name} transport diverged"


def test_parity_holds_when_state_is_absent(consumer: Path) -> None:
    (consumer / "docs/handoff/state.md").unlink()
    python, compiled = _outputs(consumer, {})
    assert compiled == python
    assert "(docs/handoff/state.md unavailable)" in compiled


def test_parity_holds_when_state_exceeds_its_budget(consumer: Path) -> None:
    # A multi-byte character straddling the 2048-byte cut is the case where a naive
    # port diverges: the truncation must land on a rune boundary in both.
    filler = "é" * 4000
    (consumer / "docs/handoff/state.md").write_text(filler)
    python, compiled = _outputs(consumer, {})
    assert compiled == python
    assert "state.md truncated at 2048 bytes" in compiled


def test_parity_holds_when_output_exceeds_its_budget(consumer: Path) -> None:
    (consumer / "docs/handoff/state.md").write_text("x" * 1900)
    for index in range(12):
        (consumer / f"dirty-{index}.txt").write_text("x")
    python, compiled = _outputs(consumer, {"CLAUDE_PROJECT_DIR": "/irrelevant"})
    assert compiled == python
    assert len(compiled.encode()) <= 4096


def test_compiled_launcher_rejects_the_same_events(consumer: Path) -> None:
    hooks = consumer / ".agents/hooks/agent-handoff"
    for event in ("", "{", '{"hook_event_name":"SessionStart","source":"nope"}'):
        results = [
            subprocess.run(
                command,
                cwd=consumer.parent,
                input=event,
                capture_output=True,
                text=True,
                check=False,
            )
            for command in (
                [sys.executable, str(hooks / "session_start.py")],
                [str(hooks / "session-start")],
            )
        ]
        assert results[0].returncode == results[1].returncode == 2, event
        assert results[0].stdout == results[1].stdout == ""
