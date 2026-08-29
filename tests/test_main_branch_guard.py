"""Behavioral tests for the tracked `main` branch-commit guard.

Every case runs against a throwaway repository whose `core.hooksPath` points at
its own hooks directory. That is not decoration: the workstation's user-global
`core.hooksPath` would otherwise decide whether repo-local hooks run at all, so
without it these tests would assert the developer's machine configuration
instead of the guard.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_GUARD_SOURCE = _ROOT / "scripts/githooks/main-branch-guard"
_INSTALLER_SOURCE = _ROOT / "scripts/install-githooks.sh"
_REFUSAL_NEEDLE = "refusing to commit on `main`"


def _run(
    *arguments: str,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    # HOME and the XDG root are redirected so a user-global hook or Git config
    # cannot reach into the fixture repository.
    environment["HOME"] = str(cwd)
    environment["XDG_CONFIG_HOME"] = str(cwd / ".xdg")
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment.pop("PROJECT_STANDARDS_RELEASE_COMMIT", None)
    environment.pop("PROJECT_STANDARDS_MAIN_COMMIT_OVERRIDE", None)
    environment.update(env or {})
    return subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        capture_output=True,
        encoding="utf-8",
    )


def _git(
    *arguments: str,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return _run("git", *arguments, cwd=cwd, env=env)


def _check(
    *arguments: str,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = _run(*arguments, cwd=cwd, env=env)
    assert result.returncode == 0, f"{arguments} failed:\n{result.stdout}\n{result.stderr}"
    return result


def _commit(
    message: str,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    (cwd / "work.txt").write_text(message, encoding="utf-8")
    _check("git", "add", "work.txt", cwd=cwd)
    return _git("commit", "-m", message, cwd=cwd, env=env)


@pytest.fixture
def guarded_repository(tmp_path: Path) -> Path:
    """Create a repo on `testing` with `main` branched and the guard installed.

    The scripts are copied rather than symlinked so the fixture exercises the
    same "tracked file inside the checkout" arrangement the installer assumes.
    """
    repository = tmp_path / "repo"
    (repository / "scripts/githooks").mkdir(parents=True)
    shutil.copy2(_GUARD_SOURCE, repository / "scripts/githooks/main-branch-guard")
    shutil.copy2(_INSTALLER_SOURCE, repository / "scripts/install-githooks.sh")

    _check("git", "init", "-q", "-b", "testing", ".", cwd=repository)
    _check("git", "config", "user.email", "guard@example.invalid", cwd=repository)
    _check("git", "config", "user.name", "Guard Fixture", cwd=repository)
    _check("git", "add", "-A", cwd=repository)
    _check(
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-q",
        "-m",
        "chore: seed",
        cwd=repository,
    )
    _check("git", "branch", "main", cwd=repository)
    # Absolute, because a relative hooksPath resolves against each worktree's own
    # top level and would make the linked-worktree case silently hookless.
    _check("git", "config", "core.hooksPath", str(repository / ".git/hooks"), cwd=repository)
    _check("./scripts/install-githooks.sh", cwd=repository)
    return repository


def test_install_githooks__writes_managed_adapters_into_the_common_hooks_directory(
    guarded_repository: Path,
) -> None:
    for hook_name in ("pre-commit", "commit-msg"):
        hook_path = guarded_repository / ".git/hooks" / hook_name
        assert os.access(hook_path, os.X_OK)
        assert "# project-standards-managed-hook: v1" in hook_path.read_text(encoding="utf-8")


def test_install_githooks__is_idempotent_and_preserves_an_unmanaged_predecessor(
    guarded_repository: Path,
) -> None:
    hook_path = guarded_repository / ".git/hooks/pre-commit"
    backup_path = guarded_repository / ".git/hooks/pre-commit.project-standards-original"
    hook_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook_path.chmod(0o755)

    _check("./scripts/install-githooks.sh", cwd=guarded_repository)
    assert backup_path.read_text(encoding="utf-8") == "#!/bin/sh\nexit 0\n"

    # A managed adapter is replaced in place: rerunning must not bury the real
    # predecessor under a backup of the adapter that superseded it.
    _check("./scripts/install-githooks.sh", cwd=guarded_repository)
    assert backup_path.read_text(encoding="utf-8") == "#!/bin/sh\nexit 0\n"


def test_guard__allows_an_ordinary_commit_on_testing(guarded_repository: Path) -> None:
    result = _commit("feat: work on the development branch", cwd=guarded_repository)

    assert result.returncode == 0, result.stderr


def test_guard__refuses_a_development_commit_on_main(guarded_repository: Path) -> None:
    _check("git", "checkout", "-q", "main", cwd=guarded_repository)

    result = _commit("feat: work that belongs on testing", cwd=guarded_repository)

    assert result.returncode != 0
    assert _REFUSAL_NEEDLE in result.stderr
    assert "development lands on `testing`" in result.stderr
    assert "PROJECT_STANDARDS_MAIN_COMMIT_OVERRIDE=1" in result.stderr
    assert _git("log", "-1", "--pretty=%s", cwd=guarded_repository).stdout.strip() == "chore: seed"


def test_guard__allows_the_release_prep_commit_on_main(guarded_repository: Path) -> None:
    _check("git", "checkout", "-q", "main", cwd=guarded_repository)

    # Both variables together are the release path: pre-commit cannot see a
    # message, so the operator declares the release, and commit-msg then holds
    # them to it by checking the message actually starts with "release:".
    result = _commit(
        "release: prepare v0.0.0",
        cwd=guarded_repository,
        env={"PROJECT_STANDARDS_RELEASE_COMMIT": "1"},
    )

    assert result.returncode == 0, result.stderr


def test_guard__refuses_a_non_release_message_declared_as_a_release(
    guarded_repository: Path,
) -> None:
    _check("git", "checkout", "-q", "main", cwd=guarded_repository)

    result = _commit(
        "feat: smuggled onto main",
        cwd=guarded_repository,
        env={"PROJECT_STANDARDS_RELEASE_COMMIT": "1"},
    )

    assert result.returncode != 0
    assert "(commit-msg)" in result.stderr


def test_guard__commit_msg_role_accepts_a_release_subject_under_a_comment_block(
    guarded_repository: Path, tmp_path: Path
) -> None:
    # `git commit -v` and commit templates put comment lines above the subject,
    # so the subject is the first non-comment, non-blank line — not line 1.
    _check("git", "checkout", "-q", "main", cwd=guarded_repository)
    message_file = tmp_path / "COMMIT_EDITMSG"
    message_file.write_text(
        "# Please enter the commit message\n\nrelease: prepare v0.0.0\n", encoding="utf-8"
    )

    result = _run(
        "./scripts/githooks/main-branch-guard",
        "commit-msg",
        str(message_file),
        cwd=guarded_repository,
    )

    assert result.returncode == 0, result.stderr


def test_guard__override_allows_the_commit_and_prints_a_loud_notice(
    guarded_repository: Path,
) -> None:
    _check("git", "checkout", "-q", "main", cwd=guarded_repository)

    result = _commit(
        "feat: deliberate exception",
        cwd=guarded_repository,
        env={"PROJECT_STANDARDS_MAIN_COMMIT_OVERRIDE": "1"},
    )

    assert result.returncode == 0, result.stderr
    assert "main-branch guard bypassed" in result.stderr
    assert (
        _git("log", "-1", "--pretty=%s", cwd=guarded_repository).stdout.strip()
        == "feat: deliberate exception"
    )


def test_guard__refuses_a_commit_on_main_from_a_linked_worktree(
    guarded_repository: Path, tmp_path: Path
) -> None:
    # A linked worktree has a private git-dir but shares the common hooks
    # directory; resolving --git-dir instead of --git-common-dir anywhere in the
    # chain would leave every worktree unguarded.
    linked = tmp_path / "linked"
    _check("git", "worktree", "add", "-q", str(linked), "main", cwd=guarded_repository)

    result = _commit("feat: worktree bypass attempt", cwd=linked)

    assert result.returncode != 0
    assert _REFUSAL_NEEDLE in result.stderr


def test_guard__does_not_block_a_fast_forward_merge_into_main(
    guarded_repository: Path,
) -> None:
    _check("git", "checkout", "-q", "testing", cwd=guarded_repository)
    assert _commit("feat: released work", cwd=guarded_repository).returncode == 0
    _check("git", "checkout", "-q", "main", cwd=guarded_repository)

    result = _git("merge", "--ff-only", "testing", cwd=guarded_repository)

    assert result.returncode == 0, result.stderr
    assert (
        _git("log", "-1", "--pretty=%s", cwd=guarded_repository).stdout.strip()
        == "feat: released work"
    )


def test_guard__is_reached_through_a_chaining_global_pre_commit_hook(
    guarded_repository: Path, tmp_path: Path
) -> None:
    # Mirrors the workstation's user-global pre-commit, which owns core.hooksPath
    # and dispatches to $(git rev-parse --git-common-dir)/hooks/pre-commit. That
    # chain is the only path by which a repo-local hook runs here, so it is the
    # arrangement the guard must survive.
    global_hooks = tmp_path / "global-hooks"
    global_hooks.mkdir()
    dispatcher = global_hooks / "pre-commit"
    dispatcher.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'local_hook="$(git rev-parse --git-common-dir)/hooks/pre-commit"\n'
        '[[ -x "$local_hook" ]] && exec "$local_hook" "$@"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    dispatcher.chmod(0o755)
    _check("git", "config", "core.hooksPath", str(global_hooks), cwd=guarded_repository)
    _check("git", "checkout", "-q", "main", cwd=guarded_repository)

    result = _commit("feat: reached through the global dispatcher", cwd=guarded_repository)

    assert result.returncode != 0
    assert _REFUSAL_NEEDLE in result.stderr
