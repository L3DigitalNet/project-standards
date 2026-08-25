"""Descriptor-relative, read-once snapshots of declared repository targets."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from project_standards.control_plane.codec import content_digest
from project_standards.control_plane.containment import (
    ContainmentError,
    ContainmentFailure,
    open_contained_directory,
    resolve_contained_directory,
)
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


def safe_repository_root(repo: Path) -> Path:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise ControlPlaneError("repository root must be a regular directory")
        return repo.resolve(strict=True)
    except OSError as exc:
        raise ControlPlaneError("repository root could not be resolved") from exc


# A tracked symlink whose destination stays inside the checkout is ordinary
# repository content, not an attack: rejecting it outright made `reconcile`
# unusable on such repositories (issue #179). Only an escape, a non-directory
# component, a link cycle, or an uninspectable component still fails.
_ANCESTOR_MESSAGES = {
    # The wording keeps the word "symlink": an escape can only arise through a
    # link, and CLI surfaces that wrap this message are asserted on it.
    ContainmentFailure.ESCAPE: "snapshot target has a symlink ancestor escaping the repository",
    ContainmentFailure.NOT_DIRECTORY: "snapshot target has a non-directory ancestor",
    ContainmentFailure.LOOP: "snapshot target has a cyclic symlink ancestor",
    ContainmentFailure.UNSAFE: "snapshot target ancestor could not be inspected safely",
}


def _ancestor_error(exc: ContainmentError) -> ControlPlaneError:
    return ControlPlaneError(_ANCESTOR_MESSAGES[exc.reason])


def _preflight_ancestors(
    root: Path,
    root_descriptor: int,
    targets: tuple[SafeRelativePath, ...],
) -> None:
    """Prove every declared target's ancestry is contained before reading bytes."""
    for target in targets:
        try:
            descriptor = open_contained_directory(
                root_descriptor,
                root,
                target.normalized.parent,
            )
        except ContainmentError as exc:
            raise _ancestor_error(exc) from exc
        if descriptor is not None:
            os.close(descriptor)


def resolved_target_paths(
    repo: Path,
    targets: tuple[SafeRelativePath, ...],
) -> dict[str, PurePosixPath]:
    """Map each declared target to the physical file it names inside the repository.

    Two declared targets that map to the same value are one file under two
    names, because the consumer collapsed their directories with a symlink —
    Agent Handoff and GitHub Workflow declare byte-identical twins under
    `.agents/skills/<name>` and `.claude/skills/<name>`, and a consumer that
    links one at the other leaves the control plane planning two writes against
    a single inode (issue #179 follow-up).

    Only the parent is resolved: a target whose LEAF is a symlink is not an
    alias, because publication replaces that leaf (`os.replace` on the link
    itself) rather than writing through it, so the link's destination keeps its
    own bytes and preconditions.

    Raises ControlPlaneError with the same wording as capture for any ancestry
    that cannot be proven contained.
    """
    root = safe_repository_root(repo)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        root_descriptor = os.open(root, flags)
    except OSError as exc:
        raise ControlPlaneError("repository root could not be opened safely") from exc
    try:
        resolved: dict[str, PurePosixPath] = {}
        for target in targets:
            try:
                parent = resolve_contained_directory(
                    root_descriptor,
                    root,
                    target.normalized.parent,
                )
            except ContainmentError as exc:
                raise _ancestor_error(exc) from exc
            resolved[target.original] = parent / target.normalized.name
        return resolved
    finally:
        os.close(root_descriptor)


def _parent_descriptor(root: Path, root_descriptor: int, parent: PurePosixPath) -> int | None:
    try:
        return open_contained_directory(root_descriptor, root, parent)
    except ContainmentError as exc:
        # The preflight already accepted this ancestry, so reaching here means
        # the tree changed underneath the capture; report the containment reason
        # rather than a generic race message so the cause stays legible.
        raise _ancestor_error(exc) from exc


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
        content_digest=content_digest(content),
        precondition_digest=_precondition(EntryKind.REGULAR, mode=mode, content=content),
    )


def _directory_inventory(descriptor: int) -> bytes:
    """Encode the immediate child names and entry types of an open directory."""
    inventory = bytearray()
    for name in sorted(os.listdir(descriptor), key=os.fsencode):
        encoded_name = os.fsencode(name)
        metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        entry_type = stat.S_IFMT(metadata.st_mode)
        inventory.extend(len(encoded_name).to_bytes(8, "big"))
        inventory.extend(encoded_name)
        inventory.extend(entry_type.to_bytes(4, "big"))
    return bytes(inventory)


def _directory_entry(
    path: SafeRelativePath,
    parent_descriptor: int,
    name: str,
) -> SnapshotEntry:
    """Capture directory mode and immediate membership through one safe descriptor."""
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise ControlPlaneError("snapshot directory could not be opened safely") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISDIR(before.st_mode):
            raise ControlPlaneError("snapshot target changed type during capture")
        inventory = _directory_inventory(descriptor)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise ControlPlaneError("snapshot directory changed during capture") from exc
    finally:
        os.close(descriptor)
    stable_fields = ("st_dev", "st_ino", "st_mtime_ns", "st_mode")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise ControlPlaneError("snapshot directory changed during capture")
    permissions = stat.S_IMODE(after.st_mode)
    # Provider-facing modes stay within the regular-file `0NNN` contract, while
    # the precondition also binds directory-only sticky/set-id bits.
    mode = f"0{permissions & 0o777:03o}"
    precondition_mode = f"{permissions:04o}"
    return SnapshotEntry(
        path=path,
        kind=EntryKind.DIRECTORY,
        content=None,
        mode=mode,
        link_target=None,
        content_digest=None,
        precondition_digest=_precondition(
            EntryKind.DIRECTORY,
            mode=precondition_mode,
            content=inventory,
        ),
    )


def _read_entry(
    root: Path,
    root_descriptor: int,
    path: SafeRelativePath,
) -> SnapshotEntry:
    parent_descriptor = _parent_descriptor(root, root_descriptor, path.normalized.parent)
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
        if stat.S_ISDIR(metadata.st_mode):
            return _directory_entry(path, parent_descriptor, name)
        kind = EntryKind.OTHER
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
        root = safe_repository_root(repo)
        try:
            normalized = validate_path_collection(targets)
        except ValueError as exc:
            raise ControlPlaneError("snapshot target collection contains a collision") from exc
        ordered = tuple(sorted(normalized, key=lambda item: item.original.encode("utf-8")))
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            root_descriptor = os.open(root, flags)
        except OSError as exc:
            raise ControlPlaneError("repository root could not be opened safely") from exc
        try:
            # Preflight every ancestor before the first content read: otherwise an
            # escape discovered late could leave earlier provider inputs observable.
            _preflight_ancestors(root, root_descriptor, ordered)
            entries = tuple(_read_entry(root, root_descriptor, target) for target in ordered)
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
