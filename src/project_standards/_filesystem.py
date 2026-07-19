"""Private descriptor-relative filesystem mutations shared by bounded writers.

The helpers in this module keep every mutable path component behind an open
directory descriptor. Callers must supply a trusted root descriptor and a
validated relative path; there is deliberately no path-based fallback because
re-resolving a name would reopen the symlink-swap window these operations close.
"""

from __future__ import annotations

import os
import secrets
import stat
from collections.abc import Generator
from contextlib import contextmanager, suppress
from pathlib import Path, PurePosixPath


class _ParentDirectoryError(OSError):
    """A parent component could not be opened or created without following links."""


class _PublishedCleanupError(OSError):
    """Publication succeeded, but its staging alias could not be removed."""

    temporary: str
    cause: OSError

    def __init__(self, temporary: str, cause: OSError) -> None:
        super().__init__(cause.errno, str(cause))
        self.temporary = temporary
        self.cause = cause


def _require_relative(relative: PurePosixPath) -> None:
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(f"unsafe descriptor-relative path: {relative}")


@contextmanager
def _directory_descriptor(  # pyright: ignore[reportUnusedFunction]
    root: Path,
) -> Generator[int]:
    """Open one trusted directory root without following its final component."""
    descriptor = os.open(
        root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _parent_error(part: str, cause: OSError) -> _ParentDirectoryError:
    return _ParentDirectoryError(
        cause.errno,
        f"parent component {part!r} is not a safe directory: {cause}",
    )


def _open_parent_descriptor(
    root_descriptor: int,
    relative: PurePosixPath,
    *,
    create: bool,
) -> int:
    descriptor = os.dup(root_descriptor)
    try:
        for part in relative.parent.parts:
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            except FileNotFoundError as exc:
                if not create:
                    raise _parent_error(part, exc) from exc
                try:
                    os.mkdir(part, mode=0o777, dir_fd=descriptor)
                except FileExistsError:
                    # A concurrent creator is acceptable only if the no-follow
                    # open below proves that the new entry is a real directory.
                    pass
                except OSError as mkdir_exc:
                    raise _parent_error(part, mkdir_exc) from mkdir_exc
                try:
                    child = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=descriptor,
                    )
                except OSError as open_exc:
                    raise _parent_error(part, open_exc) from open_exc
            except OSError as exc:
                raise _parent_error(part, exc) from exc
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _destination_mode(
    parent_descriptor: int,
    destination: str,
    requested: int | None,
) -> tuple[int, bool]:
    if requested is not None:
        return stat.S_IMODE(requested), True
    try:
        current = os.stat(
            destination,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return 0o666, False
    if stat.S_ISREG(current.st_mode):
        return stat.S_IMODE(current.st_mode), True
    return 0o666, False


def _write_bytes(  # pyright: ignore[reportUnusedFunction]
    root_descriptor: int,
    relative: PurePosixPath,
    content: bytes,
    *,
    mode: int | None,
    replace: bool,
    temporary_prefix: str,
) -> bool:
    """Publish bytes below ``root_descriptor`` without following path components.

    Replacement uses descriptor-relative rename. No-clobber publication uses a
    hard link so a concurrently created destination wins atomically; no
    check-then-replace sequence or weaker path-based fallback is permitted.
    """
    _require_relative(relative)
    parent_descriptor = _open_parent_descriptor(
        root_descriptor,
        relative,
        create=True,
    )
    temporary: str | None = None
    staging_descriptor: int | None = None
    try:
        destination = relative.name
        destination_mode, set_exact_mode = _destination_mode(
            parent_descriptor,
            destination,
            mode,
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        while staging_descriptor is None:
            temporary = f"{temporary_prefix}{secrets.token_hex(8)}.tmp"
            try:
                staging_descriptor = os.open(
                    temporary,
                    flags,
                    destination_mode,
                    dir_fd=parent_descriptor,
                )
            except FileExistsError:
                continue
        assert temporary is not None
        staged_name = temporary
        if set_exact_mode:
            # These writers historically treat chmod as best-effort; publication
            # must not gain a new failure mode merely from sharing the safe path.
            with suppress(OSError):
                os.fchmod(staging_descriptor, destination_mode)
        stream = os.fdopen(staging_descriptor, "wb")
        staging_descriptor = None
        with stream:
            stream.write(content)

        if replace:
            os.replace(
                staged_name,
                destination,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            temporary = None
            return True

        try:
            os.link(
                staged_name,
                destination,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileExistsError:
            os.unlink(staged_name, dir_fd=parent_descriptor)
            temporary = None
            return False
        try:
            os.unlink(staged_name, dir_fd=parent_descriptor)
        except OSError as exc:
            raise _PublishedCleanupError(staged_name, exc) from exc
        temporary = None
        return True
    finally:
        if staging_descriptor is not None:
            with suppress(OSError):
                os.close(staging_descriptor)
        if temporary is not None:
            with suppress(OSError):
                os.unlink(temporary, dir_fd=parent_descriptor)
        os.close(parent_descriptor)


def _prune_empty_directory(  # pyright: ignore[reportUnusedFunction]
    root_descriptor: int,
    relative: PurePosixPath,
) -> None:
    """Remove an empty directory tree without following or unlinking any entry."""
    _require_relative(relative)
    parent_descriptor = _open_parent_descriptor(
        root_descriptor,
        relative,
        create=False,
    )
    directory_descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            relative.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
        # fwalk pins each visited directory while yielding it. rmdir is the only
        # mutation: files, links, and nonempty directories therefore make pruning
        # fail closed instead of being followed or recursively deleted.
        for _path, directory_names, _file_names, descriptor in os.fwalk(
            ".",
            topdown=False,
            follow_symlinks=False,
            dir_fd=directory_descriptor,
        ):
            for directory_name in directory_names:
                os.rmdir(directory_name, dir_fd=descriptor)
        os.close(directory_descriptor)
        directory_descriptor = None
        os.rmdir(relative.name, dir_fd=parent_descriptor)
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        os.close(parent_descriptor)
