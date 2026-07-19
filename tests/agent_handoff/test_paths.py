from __future__ import annotations

import os
import stat
import subprocess
from contextlib import suppress
from os import PathLike
from pathlib import Path

import pytest

from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot


@pytest.mark.parametrize(
    "relative",
    ["/etc/passwd", "../outside", "docs/../../outside", "docs\\STATUS.md", "C:/x", "", "."],
)
def test_consumer_path_rejects_unsafe_lexical_path(tmp_path: Path, relative: str) -> None:
    with pytest.raises(RepositoryBoundaryError):
        RepositoryRoot(tmp_path).consumer_path(relative)


def test_consumer_path_rejects_null_byte(tmp_path: Path) -> None:
    with pytest.raises(RepositoryBoundaryError, match="null byte"):
        RepositoryRoot(tmp_path).consumer_path("docs/bad\x00.md")


def test_consumer_path_rejects_symlink_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    (repo / "docs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RepositoryBoundaryError, match="symlink"):
        RepositoryRoot(repo).consumer_path("docs/STATUS.md")


def test_consumer_path_rejects_symlink_leaf_even_when_target_is_inside(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "real.md").write_text("inside\n", encoding="utf-8")
    (repo / "link.md").symlink_to(repo / "real.md")

    with pytest.raises(RepositoryBoundaryError, match="symlink"):
        RepositoryRoot(repo).consumer_path("link.md")


def test_contained_helpers_access_only_repository_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    root = RepositoryRoot(repo)
    original_open = os.open
    observed: list[str | bytes] = []

    def guarded_open(
        path: str | bytes | PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if isinstance(path, Path):
            assert path.resolve() == root.path
        elif isinstance(path, str) and path.startswith("/"):
            assert Path(path).resolve() == root.path
        else:
            assert dir_fd is not None
        observed.append(os.fspath(path))
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr("project_standards.agent_handoff.paths.os.open", guarded_open)

    root.write_bytes("docs/state.md", b"state\n")

    assert root.read_bytes("docs/state.md") == b"state\n"
    assert root.stat("docs/state.md").st_size == 6
    assert observed


@pytest.mark.parametrize(
    "expected_mode",
    [
        pytest.param(0o600, id="ordinary-mode"),
        pytest.param(0o4755, id="setuid-mode"),
        pytest.param(0o2755, id="setgid-mode"),
    ],
)
def test_write_bytes__existing_file__preserves_mode(tmp_path: Path, expected_mode: int) -> None:
    root = RepositoryRoot(tmp_path)
    target = root.consumer_path("state.md")
    target.write_bytes(b"before\n")
    target.chmod(expected_mode)
    assert stat.S_IMODE(target.stat().st_mode) == expected_mode

    root.write_bytes("state.md", b"after\n")

    assert target.read_bytes() == b"after\n"
    assert stat.S_IMODE(target.stat().st_mode) == expected_mode


def test_write_bytes__new_file__respects_umask_mode(tmp_path: Path) -> None:
    target = tmp_path / "state.md"

    previous_umask = os.umask(0o077)
    try:
        RepositoryRoot(tmp_path).write_bytes("state.md", b"state\n")
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_read_wraps_unreadable_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = RepositoryRoot(tmp_path)
    path = root.consumer_path("state.md")
    path.write_text("state\n", encoding="utf-8")

    original_open = os.open

    def deny_leaf(
        path: str | bytes | PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == "state.md":
            raise PermissionError("secret detail")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr("project_standards.agent_handoff.paths.os.open", deny_leaf)

    with pytest.raises(RepositoryBoundaryError, match="cannot read consumer path") as exc_info:
        root.read_bytes("state.md")
    assert "secret detail" not in str(exc_info.value)


def test_write_cannot_escape_when_parent_is_replaced_by_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    outside.mkdir()
    root = RepositoryRoot(repo)
    original_write = Path.write_bytes

    def racing_write(path: Path, data: bytes) -> int:
        docs.rmdir()
        docs.symlink_to(outside, target_is_directory=True)
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", racing_write)

    with suppress(RepositoryBoundaryError):
        root.write_bytes("docs/state.md", b"state\n")
    assert not (outside / "state.md").exists()


def test_from_input_uses_git_root_for_repository_subdirectory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    subdir = repo / "nested"
    subdir.mkdir(parents=True)
    observed: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["args"] = args
        observed.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout=f"{repo}\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    root = RepositoryRoot.from_input(subdir)

    assert root.path == repo.resolve()
    assert observed["cwd"] == subdir.resolve()
    assert observed["timeout"] == 2.0
    assert observed["shell"] is False


def test_from_input_preserves_explicit_non_git_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "not-git"
    target.mkdir()

    def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 128, stdout="", stderr="not a repository")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert RepositoryRoot.from_input(target).path == target.resolve()


def test_git_runner_uses_fixed_root_timeout_and_argument_array(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = RepositoryRoot(tmp_path)
    observed: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["args"] = args
        observed.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="main\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    completed = root.run_git("branch", "--show-current")

    assert completed.stdout == "main\n"
    assert observed["args"] == ["git", "branch", "--show-current"]
    assert observed["cwd"] == root.path
    assert observed["timeout"] == 2.0
    assert observed["shell"] is False


@pytest.mark.parametrize("args", [("-C", "/tmp"), ("--git-dir=/tmp/x", "status")])
def test_git_runner_rejects_repository_override_arguments(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    with pytest.raises(RepositoryBoundaryError, match="repository override"):
        RepositoryRoot(tmp_path).run_git(*args)
