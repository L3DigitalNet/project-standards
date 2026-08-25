"""Descriptor traversal that proves every control-plane path stays in the repository.

The control plane reads and writes consumer files only through descriptors
obtained by descending from an already-verified repository-root descriptor, one
component at a time with `O_NOFOLLOW`. That guarantees no managed byte can land
outside the checkout even while the tree is being modified underneath the tool.

The traversal here keeps that guarantee while allowing an ancestor symlink whose
destination is itself inside the repository, because forbidding such links
outright made `reconcile` unusable on repositories that legitimately track them
(issue #179 — `.claude/skills/<name>` symlinked to `.agents/skills/<name>`).
Containment, not the absence of links, is the property worth enforcing: a link
that leaves the root is still rejected, and rejection stays the default for
anything the walk cannot prove.

A followed link is never handed to the kernel to resolve. Instead the link text
is rewritten into a root-relative path and the walk restarts from the root
descriptor, re-opening every component with `O_NOFOLLOW`. The rejected
alternative — dropping `O_NOFOLLOW` for the link component and checking the
result afterwards — would let the kernel traverse a path the tool has not
verified, and its after-the-fact check is racy by construction.

In-root destination policy (issue #187): staying inside the checkout is not
sufficient. A committed link on a declared target's parent path could redirect a
managed write into `.git/` or `.standards/` — publisher-controlled bytes landing
on Git's own state or on the control plane's authority, with the lock still
recording the declared spelling rather than where the bytes went. The policy
implemented here is a DENY-LIST: a physical destination whose first component is
`.git` or `.standards` is refused whenever it differs from the declared path, on
both the read and the write path. The alternative policy — "physical must equal
declared unless the link is lock-declared" — is rejected: it would refuse every
legitimate in-root link the moment it is first seen (there is no lock record
before the first reconcile), which is exactly the usability failure #179 fixed,
and it would push symlink topology into the lock schema, making the lock a
mutable trust anchor for a property the walk can decide on its own.

The deny-list is deliberately spelled as a path component and not as an inode
identity, so a `.git` FILE (the gitdir pointer a linked worktree uses) is refused
by the same rule as a `.git` directory.

Path containment is not device containment: a bind mount or an overlay can make
an in-root path resolve to storage outside the checkout, and no path-based walk
can observe that, so it stays out of this module's model.
"""

from __future__ import annotations

import errno
import os
import stat
from collections import deque
from enum import StrEnum
from pathlib import Path, PurePosixPath

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC

# Bounds a chain of links that resolve through one another; without it a cycle
# (`a -> b`, `b -> a`) would spin forever inside the walk. The value mirrors the
# customary kernel limit rather than any property of this tool.
_MAX_LINKS_FOLLOWED = 40

# Roots a redirected write must never reach: Git's own state and the control
# plane's authority. `.standards/` was until now protected only incidentally, by
# `locking.py` refusing a symlinked control directory and by the planner's
# namespace pruning; neither of those sees a link that redirects some other
# declared target into it, so containment states the rule itself.
_PROTECTED_ROOTS = frozenset({".git", ".standards"})

# The one diagnostic code for a refused in-root destination. Both report paths
# use this constant so the read and write halves of the policy stay one
# vocabulary; grep here before renaming it.
CONTAINMENT_DESTINATION_CODE = "CP-CONTAINMENT-DESTINATION"


class ContainmentFailure(StrEnum):
    """Why a traversal could not be proven to stay inside the repository root."""

    ESCAPE = "escape"
    NOT_DIRECTORY = "not-directory"
    LOOP = "loop"
    UNSAFE = "unsafe"
    DESTINATION = "destination"


class ContainmentError(Exception):
    """Signal a traversal that must not proceed.

    Callers own the user-facing wording and diagnostic code: this module is
    shared by the snapshot (read) and executor (write) paths, which report
    through different error channels. Match on `reason`, never on `str(exc)`.

    `declared` and `physical` are populated for DESTINATION alone, because that
    is the one failure whose message has to name both spellings for an operator
    to find the offending link; they stay None for every other reason.
    """

    def __init__(
        self,
        reason: ContainmentFailure,
        *,
        declared: PurePosixPath | None = None,
        physical: PurePosixPath | None = None,
    ) -> None:
        super().__init__(reason.value)
        self.reason: ContainmentFailure = reason
        self.declared: PurePosixPath | None = declared
        self.physical: PurePosixPath | None = physical


def _link_text(descriptor: int, name: str) -> str | None:
    """Return the raw link text of `name`, or None when it is not a symlink."""
    try:
        metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except OSError as exc:
        raise ContainmentError(ContainmentFailure.UNSAFE) from exc
    if not stat.S_ISLNK(metadata.st_mode):
        return None
    try:
        return os.readlink(name, dir_fd=descriptor)
    except OSError as exc:
        raise ContainmentError(ContainmentFailure.UNSAFE) from exc


def _relocated_parts(root: Path, parent: PurePosixPath, link: str) -> tuple[str, ...]:
    """Rewrite one link into the root-relative path the walk restarts from.

    `parent` is the physical path of the directory holding the link, so a
    relative link is joined onto it. Resolving `..` lexically is exact here
    precisely because every component of `parent` was opened with `O_NOFOLLOW`
    and is therefore a real directory, never a link whose parent differs from
    its lexical one; the invariant breaks if a caller ever seeds `parent` from
    an unverified path.
    """
    text = PurePosixPath(link)
    if text.is_absolute():
        # An absolute link is resolved through the filesystem only to decide
        # containment; the parts returned are re-walked with `O_NOFOLLOW`, so a
        # resolution that no longer holds fails the walk instead of being trusted.
        #
        # `Path.resolve` is retained deliberately over a lexical normalization:
        # the two are NOT equivalent, because the absolute link text may itself
        # traverse further symlinks (a `/var/...` target under a `/var -> …`
        # link) that only the filesystem can collapse, and root itself is a
        # resolved path, so a lexical compare would reject legitimate links.
        # The accepted cost is a side channel: resolving stats components
        # outside the repository, which can trigger an autofs mount or reveal
        # existence through timing. It reads nothing and decides nothing but
        # containment, and the destination is re-opened from the root
        # descriptor afterwards.
        resolved = Path(link).resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise ContainmentError(ContainmentFailure.ESCAPE)
        return resolved.relative_to(root).parts
    parts = list(parent.parts)
    for part in text.parts:
        if part == ".":
            continue
        if part == "..":
            if not parts:
                raise ContainmentError(ContainmentFailure.ESCAPE)
            parts.pop()
            continue
        parts.append(part)
    return tuple(parts)


def open_contained_directory(
    root_descriptor: int,
    root: Path,
    relative: PurePosixPath,
    *,
    create: bool = False,
    created: list[PurePosixPath] | None = None,
) -> int | None:
    """Open `relative` under the repository root and return its descriptor.

    Returns None when a component is absent and `create` is false; with `create`
    set, missing directories are made with mode 0o755 and each one's physical
    path relative to the root is appended to `created` so a caller can roll the
    creation back. Raises ContainmentError for anything else — an escape, a
    non-directory component, a link cycle, an unusable component, or an in-root
    destination a link moved into a protected root (`.git/`, `.standards/`).

    The returned descriptor is the caller's to close.
    """
    descriptor, _physical = _walk(root_descriptor, root, relative, create=create, created=created)
    return descriptor


def resolve_contained_directory(
    root_descriptor: int,
    root: Path,
    relative: PurePosixPath,
) -> PurePosixPath:
    """Return the physical root-relative path that `relative` names.

    "Physical" means every ancestor symlink has been rewritten into the path it
    designates, so two declared paths that the consumer has collapsed onto one
    directory — `.claude/skills/<name>` symlinked to `.agents/skills/<name>` —
    resolve to the same value. Callers use that equality to recognize aliased
    targets before planning a write; see `snapshot.resolved_target_paths`.

    Resolution creates nothing and needs no existing path: components below the
    first absent one cannot be links, so they are already physical and are
    appended verbatim. Containment is enforced exactly as it is for an opened
    walk — an escape, a cycle, a non-directory component, or a destination in a
    protected root raises.
    """
    descriptor, physical = _walk(root_descriptor, root, relative)
    if descriptor is not None:
        os.close(descriptor)
    return physical


def _assert_destination(declared: PurePosixPath, physical: PurePosixPath) -> None:
    """Refuse a link-redirected destination that lands in a protected root.

    The comparison against `declared` is what keeps the control plane able to
    write its own `.standards/` state and any legitimately declared `.git`
    target: those reach their destination with no link followed, so the physical
    path is the declared one. Only a destination the consumer's links MOVED into
    a protected root is refused — see the module docstring for why this is a
    deny-list rather than a physical-equals-declared rule.
    """
    parts = physical.parts
    if parts and parts[0] in _PROTECTED_ROOTS and physical != declared:
        raise ContainmentError(
            ContainmentFailure.DESTINATION,
            declared=declared,
            physical=physical,
        )


def _walk(
    root_descriptor: int,
    root: Path,
    relative: PurePosixPath,
    *,
    create: bool = False,
    created: list[PurePosixPath] | None = None,
) -> tuple[int | None, PurePosixPath]:
    """Descend one path component at a time, returning the descriptor and physical path.

    This is the single implementation of the containment rules; both public
    entry points delegate here so the opening and resolving callers can never
    disagree about what "inside the repository" means — including the in-root
    destination policy, which therefore binds the read path exactly as it binds
    the write path.
    """
    descriptor = os.dup(root_descriptor)
    physical = PurePosixPath()
    pending = deque(relative.parts)
    followed = 0
    try:
        while pending:
            part = pending.popleft()
            try:
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    os.close(descriptor)
                    # Nothing below an absent component exists, so no remaining
                    # component can be a link: the lexical join is already the
                    # physical path a later creation would materialize.
                    return None, physical.joinpath(part, *pending)
                child = _create_child(descriptor, part, physical, created)
            except OSError as exc:
                # Linux reports ENOTDIR — not ELOOP — when O_DIRECTORY and
                # O_NOFOLLOW meet a symlink, exactly as it does for a regular
                # file, so the two cases are only distinguishable by an lstat.
                if exc.errno not in {errno.ENOTDIR, errno.ELOOP}:
                    raise ContainmentError(ContainmentFailure.UNSAFE) from exc
                link = _link_text(descriptor, part)
                if link is None:
                    raise ContainmentError(ContainmentFailure.NOT_DIRECTORY) from exc
                followed += 1
                if followed > _MAX_LINKS_FOLLOWED:
                    raise ContainmentError(ContainmentFailure.LOOP) from exc
                relocated = _relocated_parts(root, physical, link)
                # Judge the destination before anything under it is opened: the
                # relocated prefix plus the untouched tail is exactly the path
                # this walk would end at, so a forbidden root is refused without
                # ever handing `.git/` or `.standards/` to `os.open`.
                _assert_destination(relative, PurePosixPath(*relocated, *pending))
                pending.extendleft(reversed(relocated))
                # Duplicate before closing: if `os.dup` failed after the close,
                # `descriptor` would name a closed — and possibly already
                # reused — number that the handler below would close again.
                replacement = os.dup(root_descriptor)
                os.close(descriptor)
                descriptor = replacement
                physical = PurePosixPath()
                continue
            os.close(descriptor)
            descriptor = child
            physical = physical / part
        return descriptor, physical
    except BaseException:
        os.close(descriptor)
        raise


def _create_child(
    descriptor: int,
    part: str,
    physical: PurePosixPath,
    created: list[PurePosixPath] | None,
) -> int:
    """Create one missing directory component and open it safely."""
    try:
        os.mkdir(part, mode=0o755, dir_fd=descriptor)
    except FileExistsError:
        # A concurrent creator won the race; the open below still proves the
        # component is a real directory rather than a link someone slipped in.
        pass
    except OSError as exc:
        raise ContainmentError(ContainmentFailure.UNSAFE) from exc
    else:
        if created is not None:
            created.append(physical / part)
    try:
        return os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
    except OSError as exc:
        raise ContainmentError(ContainmentFailure.UNSAFE) from exc
