from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockMode,
    control_plane_lock,
    is_reserved_temporary_name,
    reserved_temporary_name,
)

_HOLDER = """
import sys
from pathlib import Path
from project_standards.control_plane.locking import LockMode, control_plane_lock

repo = Path(sys.argv[1])
mode = LockMode(sys.argv[2])
with control_plane_lock(repo, mode):
    print("READY", flush=True)
    sys.stdin.read(1)
"""


def test_reserved_temporary_names_have_one_bounded_namespace() -> None:
    generated = reserved_temporary_name()

    assert len(generated) == len(".project-standards-") + 16 + len(".tmp")
    assert generated.startswith(".project-standards-")
    assert generated.endswith(".tmp")
    assert is_reserved_temporary_name(generated)

    for user_name in (
        ".config.toml.0123456789abcdef.tmp",
        ".project-standards-0123456789abcde.tmp",
        ".project-standards-0123456789abcdef0.tmp",
        ".project-standards-0123456789abcdeg.tmp",
        "project-standards-0123456789abcdef.tmp",
    ):
        assert not is_reserved_temporary_name(user_name)


def _start_holder(repo: Path, mode: LockMode) -> subprocess.Popen[str]:
    process = subprocess.Popen(
        [sys.executable, "-c", _HOLDER, str(repo), mode.value],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    assert process.stdout.readline() == "READY\n"
    return process


def _stop_holder(process: subprocess.Popen[str]) -> None:
    if process.stdin is not None:
        process.stdin.write("x")
        process.stdin.flush()
    assert process.wait(timeout=5) == 0


def test_concurrent_readers_share_the_directory_lock(tmp_path: Path) -> None:
    (tmp_path / ".standards").mkdir()
    holder = _start_holder(tmp_path, LockMode.READ)
    try:
        with control_plane_lock(tmp_path, LockMode.READ):
            assert list((tmp_path / ".standards").iterdir()) == []
    finally:
        _stop_holder(holder)


@pytest.mark.parametrize(
    ("held", "requested"),
    [
        (LockMode.WRITE, LockMode.READ),
        (LockMode.READ, LockMode.WRITE),
        (LockMode.WRITE, LockMode.WRITE),
    ],
)
def test_conflicting_locks_fail_immediately_with_stable_code(
    tmp_path: Path,
    held: LockMode,
    requested: LockMode,
) -> None:
    (tmp_path / ".standards").mkdir()
    holder = _start_holder(tmp_path, held)
    try:
        with (
            pytest.raises(ControlPlaneBusyError) as exc_info,
            control_plane_lock(tmp_path, requested),
        ):
            pytest.fail("conflicting lock unexpectedly succeeded")
        assert exc_info.value.code == "CP-BUSY"
    finally:
        _stop_holder(holder)


def test_process_exit_releases_lock_without_an_artifact(tmp_path: Path) -> None:
    control = tmp_path / ".standards"
    control.mkdir()
    holder = _start_holder(tmp_path, LockMode.WRITE)
    holder.kill()
    assert holder.wait(timeout=5) != 0

    with control_plane_lock(tmp_path, LockMode.WRITE):
        assert list(control.iterdir()) == []


def test_lock_rejects_missing_or_symlinked_control_directory(tmp_path: Path) -> None:
    with (
        pytest.raises(ValueError, match="directory"),
        control_plane_lock(tmp_path, LockMode.READ),
    ):
        pytest.fail("missing directory unexpectedly locked")

    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / ".standards").symlink_to(target, target_is_directory=True)
    with (
        pytest.raises(ValueError, match="symlink"),
        control_plane_lock(tmp_path, LockMode.READ),
    ):
        pytest.fail("symlinked directory unexpectedly locked")
