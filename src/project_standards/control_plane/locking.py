"""Non-blocking advisory locks on the consumer control-plane directory."""

from __future__ import annotations

import errno
import fcntl
import os
import stat
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class LockMode(StrEnum):
    """Shared read or exclusive mutation access to consumer state."""

    READ = "read"
    WRITE = "write"


class ControlPlaneBusyError(RuntimeError):
    """Report lock contention through the stable control-plane diagnostic code."""

    code = "CP-BUSY"


@dataclass(frozen=True, slots=True)
class LockedControlDirectory:
    """A locked directory descriptor used for race-safe relative state reads."""

    path: Path
    descriptor: int

    def file_kind(self, name: str) -> str:
        """Classify one direct child without following links."""
        if not name or "/" in name or name in {".", ".."}:
            raise ValueError("control-plane filename must be one direct child")
        try:
            mode = os.stat(
                name,
                dir_fd=self.descriptor,
                follow_symlinks=False,
            ).st_mode
        except FileNotFoundError:
            return "missing"
        except OSError as exc:
            raise ValueError("control-plane file could not be inspected") from exc
        return "regular" if stat.S_ISREG(mode) else "unsafe"

    def read_bytes(self, name: str) -> bytes:
        """Read one regular direct child through the locked directory descriptor."""
        if self.file_kind(name) != "regular":
            raise ValueError("control-plane file is not a safe regular file")
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            descriptor = os.open(name, flags, dir_fd=self.descriptor)
        except OSError as exc:
            raise ValueError("control-plane file could not be opened safely") from exc
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("control-plane file is not regular")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(descriptor)

    def is_current(self) -> bool:
        """Return whether the repository path still names this locked directory."""
        try:
            opened = os.fstat(self.descriptor)
            current = self.path.stat(follow_symlinks=False)
        except OSError:
            return False
        return (
            stat.S_ISDIR(current.st_mode)
            and opened.st_dev == current.st_dev
            and opened.st_ino == current.st_ino
        )


def _control_directory(repo: Path) -> Path:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise ValueError("repository root must be a regular directory")
        normalized = repo.resolve(strict=True)
        control = normalized / ".standards"
        if control.is_symlink():
            raise ValueError("control-plane directory cannot be a symlink")
        if not control.is_dir():
            raise ValueError("control-plane directory does not exist")
        return control
    except OSError as exc:
        raise ValueError("control-plane directory could not be inspected") from exc


@contextmanager
def control_plane_lock(repo: Path, mode: LockMode) -> Generator[LockedControlDirectory]:
    """Hold a shared or exclusive non-blocking lock on `.standards/` itself."""
    control = _control_directory(repo)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(control, flags)
    except OSError as exc:
        raise ValueError("control-plane directory could not be opened safely") from exc
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ValueError("control-plane lock target is not a directory")
        operation = fcntl.LOCK_SH if mode is LockMode.READ else fcntl.LOCK_EX
        try:
            fcntl.flock(descriptor, operation | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                raise ControlPlaneBusyError(
                    "CP-BUSY: another standards operation holds the repository lock"
                ) from exc
            raise ValueError("control-plane directory could not be locked") from exc
        try:
            yield LockedControlDirectory(control, descriptor)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)
