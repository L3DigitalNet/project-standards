"""Descriptor-relative, read-once snapshots of declared repository targets."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.package_contract.paths import (
    SafeRelativePath,
    Sha256Digest,
    validate_path_collection,
)

_READ_SIZE = 1024 * 1024


class EntryKind(StrEnum):
    """Filesystem states relevant to planning without following links."""

    MISSING = "missing"
    REGULAR = "regular"
    SYMLINK = "symlink"
    DIRECTORY = "directory"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class SnapshotEntry:
    """Exact bytes and metadata observed for one declared target."""

    path: SafeRelativePath
    kind: EntryKind
    content: bytes | None
    mode: str | None
    link_target: str | None
    content_digest: Sha256Digest | None
    precondition_digest: Sha256Digest


def _digest(content: bytes) -> Sha256Digest:
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")


def _precondition(
    kind: EntryKind,
    *,
    mode: str | None = None,
    content: bytes | None = None,
    link_target: str | None = None,
) -> Sha256Digest:
    digest = hashlib.sha256()
    digest.update(kind.value.encode("ascii"))
    digest.update(b"\0")
    digest.update((mode or "").encode("ascii"))
    digest.update(b"\0")
    if content is not None:
        digest.update(content)
    elif link_target is not None:
        digest.update(link_target.encode("utf-8", errors="surrogateescape"))
    return Sha256Digest(f"sha256:{digest.hexdigest()}")


def _safe_root(repo: Path) -> Path:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise ControlPlaneError("repository root must be a regular directory")
        return repo.resolve(strict=True)
    except OSError as exc:
        raise ControlPlaneError("repository root could not be resolved") from exc


def _preflight_ancestors(root: Path, targets: tuple[SafeRelativePath, ...]) -> None:
    for target in targets:
        current = root
        for part in target.normalized.parts[:-1]:
            current /= part
            try:
                metadata = current.lstat()
            except FileNotFoundError:
                break
            except OSError as exc:
                raise ControlPlaneError("snapshot ancestor could not be inspected") from exc
            if stat.S_ISLNK(metadata.st_mode):
                raise ControlPlaneError("snapshot target has a symlink ancestor")
            if not stat.S_ISDIR(metadata.st_mode):
                raise ControlPlaneError("snapshot target has a non-directory ancestor")


def _parent_descriptor(root_descriptor: int, parent: PurePosixPath) -> int | None:
    descriptor = os.dup(root_descriptor)
    try:
        for part in parent.parts:
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                os.close(descriptor)
                return None
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError as exc:
        os.close(descriptor)
        raise ControlPlaneError("snapshot target ancestor changed during capture") from exc


def _mode(metadata: os.stat_result) -> str:
    permissions = stat.S_IMODE(metadata.st_mode)
    if permissions > 0o777:
        raise ControlPlaneError("snapshot target has unsupported special mode bits")
    return f"0{permissions:03o}"


def _regular_entry(
    path: SafeRelativePath,
    parent_descriptor: int,
    name: str,
) -> SnapshotEntry:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise ControlPlaneError("snapshot target could not be opened safely") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ControlPlaneError("snapshot target changed type during capture")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, _READ_SIZE):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise ControlPlaneError("snapshot target could not be read") from exc
    finally:
        os.close(descriptor)
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise ControlPlaneError("snapshot target changed while being read")
    content = b"".join(chunks)
    mode = _mode(after)
    return SnapshotEntry(
        path=path,
        kind=EntryKind.REGULAR,
        content=content,
        mode=mode,
        link_target=None,
        content_digest=_digest(content),
        precondition_digest=_precondition(EntryKind.REGULAR, mode=mode, content=content),
    )


def _read_entry(
    root_descriptor: int,
    path: SafeRelativePath,
) -> SnapshotEntry:
    parent_descriptor = _parent_descriptor(root_descriptor, path.normalized.parent)
    if parent_descriptor is None:
        return SnapshotEntry(
            path,
            EntryKind.MISSING,
            None,
            None,
            None,
            None,
            _precondition(EntryKind.MISSING),
        )
    name = path.normalized.name
    try:
        try:
            metadata = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return SnapshotEntry(
                path,
                EntryKind.MISSING,
                None,
                None,
                None,
                None,
                _precondition(EntryKind.MISSING),
            )
        if stat.S_ISREG(metadata.st_mode):
            return _regular_entry(path, parent_descriptor, name)
        if stat.S_ISLNK(metadata.st_mode):
            target = os.readlink(name, dir_fd=parent_descriptor)
            return SnapshotEntry(
                path,
                EntryKind.SYMLINK,
                None,
                None,
                target,
                None,
                _precondition(EntryKind.SYMLINK, link_target=target),
            )
        kind = EntryKind.DIRECTORY if stat.S_ISDIR(metadata.st_mode) else EntryKind.OTHER
        return SnapshotEntry(
            path,
            kind,
            None,
            None,
            None,
            None,
            _precondition(kind),
        )
    except OSError as exc:
        raise ControlPlaneError("snapshot target could not be inspected") from exc
    finally:
        os.close(parent_descriptor)


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    """Read each declared target once and retain apply-time preconditions."""

    root: Path
    targets: tuple[SafeRelativePath, ...]
    entries: tuple[SnapshotEntry, ...]

    @classmethod
    def capture(
        cls,
        repo: Path,
        targets: tuple[SafeRelativePath, ...],
    ) -> RepositorySnapshot:
        root = _safe_root(repo)
        try:
            normalized = validate_path_collection(targets)
        except ValueError as exc:
            raise ControlPlaneError("snapshot target collection contains a collision") from exc
        ordered = tuple(sorted(normalized, key=lambda item: item.original.encode("utf-8")))
        # Preflight every ancestor before the first content read: otherwise an
        # escape discovered late could leave earlier provider inputs observable.
        _preflight_ancestors(root, ordered)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            root_descriptor = os.open(root, flags)
        except OSError as exc:
            raise ControlPlaneError("repository root could not be opened safely") from exc
        try:
            entries = tuple(_read_entry(root_descriptor, target) for target in ordered)
        finally:
            os.close(root_descriptor)
        return cls(root, ordered, entries)

    def entry(self, path: SafeRelativePath) -> SnapshotEntry:
        for entry in self.entries:
            if entry.path == path:
                return entry
        raise ControlPlaneError(f"target was not declared in snapshot: {path.original}")

    def assert_current(self) -> None:
        """Fail when any target no longer matches this snapshot's precondition."""
        current = RepositorySnapshot.capture(self.root, self.targets)
        for expected, observed in zip(self.entries, current.entries, strict=True):
            if expected.precondition_digest != observed.precondition_digest:
                raise ControlPlaneError(f"snapshot precondition changed: {expected.path.original}")
