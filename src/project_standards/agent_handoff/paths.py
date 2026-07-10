"""Confine consumer filesystem and Git access to one resolved repository root."""

from __future__ import annotations

import os
import secrets
import stat as stat_module
import subprocess
from collections.abc import Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_GIT_TIMEOUT_SECONDS = 2.0
_GIT_REPOSITORY_OVERRIDE_PREFIXES = ("--git-dir", "--work-tree", "--namespace")


class RepositoryBoundaryError(ValueError):
    """A requested consumer access is invalid or escapes repository authority."""


def _reject_symlink_chain(root: Path, target: Path) -> None:
    current = root
    for part in target.relative_to(root).parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise RepositoryBoundaryError(f"cannot inspect consumer path {current}") from exc
        if stat_module.S_ISLNK(metadata.st_mode):
            raise RepositoryBoundaryError(f"consumer path contains a symlink: {current}")


@contextmanager
def _open_parent_directory(
    root: Path, parts: tuple[str, ...], *, create: bool
) -> Generator[tuple[int, str]]:
    """Hold no-follow directory descriptors so concurrent path swaps cannot escape root."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current_fd = os.open(root, flags)
    try:
        for part in parts[:-1]:
            if create:
                with suppress(FileExistsError):
                    os.mkdir(part, dir_fd=current_fd)
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        yield current_fd, parts[-1]
    finally:
        os.close(current_fd)


@dataclass(frozen=True)
class RepositoryRoot:
    """Resolved maximum authority for all consumer data and subprocess access."""

    path: Path

    def __post_init__(self) -> None:
        try:
            resolved = self.path.resolve(strict=True)
            if not resolved.is_dir():
                raise RepositoryBoundaryError(f"repository root is not a directory: {resolved}")
        except RepositoryBoundaryError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise RepositoryBoundaryError("cannot resolve repository root") from exc
        object.__setattr__(self, "path", resolved)

    @classmethod
    def from_input(cls, path: Path) -> RepositoryRoot:
        """Use the containing Git root when available, otherwise the explicit directory."""
        explicit = cls(path)
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=explicit.path,
                check=False,
                capture_output=True,
                text=True,
                timeout=_GIT_TIMEOUT_SECONDS,
                shell=False,
            )
        except OSError, subprocess.TimeoutExpired:
            return explicit
        if completed.returncode != 0:
            return explicit
        output = completed.stdout.strip()
        if not output:
            return explicit
        try:
            git_root = Path(output).resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RepositoryBoundaryError("Git returned an invalid repository root") from exc
        if not explicit.path.is_relative_to(git_root):
            raise RepositoryBoundaryError("Git root does not contain the explicit input path")
        return cls(git_root)

    def consumer_path(self, relative: str) -> Path:
        """Return one contained, non-symlinked consumer path without following its leaf."""
        if "\x00" in relative:
            raise RepositoryBoundaryError("consumer path contains a null byte")
        if not relative or relative == "." or "\\" in relative:
            raise RepositoryBoundaryError(f"unsafe consumer path: {relative!r}")
        candidate = PurePosixPath(relative)
        if candidate.is_absolute() or ".." in candidate.parts or candidate.parts[0].endswith(":"):
            raise RepositoryBoundaryError(f"unsafe consumer path: {relative!r}")
        target = self.path.joinpath(*candidate.parts)
        _reject_symlink_chain(self.path, target)
        return target

    def read_bytes(self, relative: str) -> bytes:
        target = self.consumer_path(relative)
        parts = target.relative_to(self.path).parts
        try:
            with _open_parent_directory(self.path, parts, create=False) as (parent_fd, leaf):
                descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
                with os.fdopen(descriptor, "rb") as stream:
                    return stream.read()
        except OSError as exc:
            raise RepositoryBoundaryError(f"cannot read consumer path {target}") from exc

    def stat(self, relative: str) -> os.stat_result:
        target = self.consumer_path(relative)
        parts = target.relative_to(self.path).parts
        try:
            with _open_parent_directory(self.path, parts, create=False) as (parent_fd, leaf):
                metadata = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
                if stat_module.S_ISLNK(metadata.st_mode):
                    raise RepositoryBoundaryError(f"consumer path contains a symlink: {target}")
                return metadata
        except RepositoryBoundaryError:
            raise
        except OSError as exc:
            raise RepositoryBoundaryError(f"cannot stat consumer path {target}") from exc

    def write_bytes(self, relative: str, data: bytes) -> None:
        target = self.consumer_path(relative)
        parts = target.relative_to(self.path).parts
        temporary_name: str | None = None
        try:
            with _open_parent_directory(self.path, parts, create=True) as (parent_fd, leaf):
                try:
                    metadata = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    metadata = None
                if metadata is not None and stat_module.S_ISLNK(metadata.st_mode):
                    raise RepositoryBoundaryError(f"consumer path contains a symlink: {target}")

                for _attempt in range(10):
                    temporary_name = f".agent-handoff-{secrets.token_hex(8)}.tmp"
                    try:
                        descriptor = os.open(
                            temporary_name,
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                            0o666,
                            dir_fd=parent_fd,
                        )
                        break
                    except FileExistsError:
                        continue
                else:
                    raise RepositoryBoundaryError("cannot allocate contained staging file")

                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(
                        temporary_name,
                        leaf,
                        src_dir_fd=parent_fd,
                        dst_dir_fd=parent_fd,
                    )
                    temporary_name = None
                finally:
                    if temporary_name is not None:
                        with suppress(OSError):
                            os.unlink(temporary_name, dir_fd=parent_fd)
        except RepositoryBoundaryError:
            raise
        except OSError as exc:
            raise RepositoryBoundaryError(f"cannot write consumer path {target}") from exc

    def run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a fixed-argument Git command from the repository root with a fixed timeout."""
        if not args:
            raise RepositoryBoundaryError("Git command requires arguments")
        if any(
            argument == "-C" or argument.startswith(_GIT_REPOSITORY_OVERRIDE_PREFIXES)
            for argument in args
        ):
            raise RepositoryBoundaryError("Git repository override arguments are forbidden")
        try:
            return subprocess.run(
                ["git", *args],
                cwd=self.path,
                check=False,
                capture_output=True,
                text=True,
                timeout=_GIT_TIMEOUT_SECONDS,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RepositoryBoundaryError("Git command failed before completion") from exc
