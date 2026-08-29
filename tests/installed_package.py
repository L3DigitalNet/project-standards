"""Materialize this repository's source package as an installed distribution
without re-copying the payload projection into every test's scratch directory.

`src/project_standards/payloads` is a symlink farm into `standards/`, so a
fixture that wants a real installed distribution must dereference it: reconcile
delivers payload file *content*, and `validate_payload_integrity` digests every
manifest-listed file, so a pruned or still-symlinked projection fails integrity
outright rather than degrading. Dereferencing costs ~109 MiB per copy against
~2.8 MiB of actual Python source, because the seven `github-workflow` and six
`agent-handoff` `bin/` binaries are ~89 MiB of committed bytes and every catalog
version keeps its own.

That per-copy cost overran the gate's 16 GiB tmpfs when github-workflow 1.6 added
a seventh ~9.9 MiB binary: the ordinary lane's `--basetemp` reached 14 GiB and
fixtures began failing inside `shutil.copytree` with ENOSPC. `copy_installed_package`
dereferences the farm ONCE per run into a shared tree and hardlinks it into each
destination, so N distributions cost ~109 MiB + N x ~2.8 MiB instead of N x ~109 MiB.

A hardlink is byte- and mode-identical to a copy because the destination entry is
the same inode — the tracked 0755 on `bin/gh-workflow` is the original mode rather
than a reproduction of it. The contract that makes the sharing safe:

    Nothing may write to, truncate, or chmod a file beneath a returned tree's
    `payloads/`. Such a write reaches through the link into the shared tree and
    therefore into every other test's distribution.

Deleting is fine — unlink drops one link, not the bytes. A fixture that must tamper
with payload bytes (`tests/mcp_server/test_transport.py::tampered_runtime`) keeps a
plain `shutil.copytree` and does not call this helper.

Requirements: the destination must sit on the same filesystem as `TMPDIR`, which
holds under `scripts/verify.sh` (both live on the `/mnt/pytesttmp` tmpfs) and under
a default pytest basetemp. A cross-device destination degrades to a full real copy
instead of failing, so correctness never depends on that layout — only the size win
does.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_PACKAGE = _ROOT / "src/project_standards"
_PAYLOADS = "payloads"

# Resolved once per process; every xdist worker pays one signature walk (~30 ms)
# and at most one of them pays for the materialization.
_shared_payloads: Path | None = None


def _payload_signature() -> str:
    """Digest the dereferenced projection's identity, size, mode and mtime.

    Keys the shared tree by content so a stale materialization can never be
    served: `TMPDIR` outlives a single pytest session, and a session that
    re-projects `standards/` (or checks out a different revision) must not
    inherit the previous run's bytes.

    `followlinks=True` is load-bearing — pathlib's `**` stopped recursing through
    directory symlinks in 3.13, and the projection reaches its payload trees
    through exactly such links.
    """
    digest = hashlib.sha256()
    for directory, subdirectories, filenames in os.walk(
        _SOURCE_PACKAGE / _PAYLOADS, followlinks=True
    ):
        subdirectories.sort()
        for name in sorted(filenames):
            path = Path(directory, name)
            status = path.stat()
            relative = path.relative_to(_SOURCE_PACKAGE).as_posix()
            digest.update(
                f"{relative}\0{status.st_size}\0{status.st_mode}\0{status.st_mtime_ns}\0".encode()
            )
    return digest.hexdigest()[:16]


def _materialize_shared_payloads() -> Path:
    """Dereference the projection once per run into a content-keyed shared tree."""
    global _shared_payloads
    if _shared_payloads is not None:
        return _shared_payloads

    root = Path(tempfile.gettempdir()) / f"project-standards-payloads-{_payload_signature()}"
    # The lock file is deliberately a sibling rather than a child of `root`:
    # `root` appears atomically via `os.replace` below, so it can hold nothing
    # that a concurrent worker must create first.
    lock_path = root.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as handle:
        # Serializes the ~0.2 s materialization across xdist workers, which
        # otherwise all start it at once and transiently multiply the 109 MiB
        # this whole module exists to spend only once.
        fcntl.flock(handle, fcntl.LOCK_EX)
        if not root.is_dir():
            staging = Path(tempfile.mkdtemp(dir=str(root.parent), prefix=f"{root.name}."))
            build = Path(staging, _PAYLOADS)
            shutil.copytree(_SOURCE_PACKAGE / _PAYLOADS, build, symlinks=False)
            # Publish by rename so `root.is_dir()` is never true for a partial
            # tree, even if this process dies mid-copy: readers see the complete
            # tree or nothing.
            build.replace(root)
            shutil.rmtree(staging, ignore_errors=True)
    _shared_payloads = root
    return root


def _link_tree(source: Path, destination: Path) -> None:
    """Reproduce `source` at `destination` with files hardlinked, directories copied.

    Raises `OSError` with `EXDEV` when the two live on different filesystems; the
    caller degrades to a real copy rather than propagating that.
    """
    destination.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        target = destination / entry.name
        if entry.is_dir():
            _link_tree(entry, target)
        else:
            os.link(entry, target)
    # After the children, not before: creating each entry bumps the directory's
    # own mtime, so copying the stat first would leave it wrong.
    shutil.copystat(source, destination)


def copy_installed_package(destination: Path) -> Path:
    """Copy the source package to `destination`, sharing the payload projection.

    Equivalent to `shutil.copytree(src/project_standards, destination,
    symlinks=False)` for everything a test can observe — same files, same bytes,
    same modes, no symlinks left in the projection — but the payload trees are
    hardlinks into a per-run shared materialization. Read the module docstring's
    no-write contract before pointing a mutating fixture at this.

    Returns `destination`.
    """

    def ignore(directory: str, _names: list[str]) -> set[str]:
        # Prune only the projection root, never a `payloads` directory that some
        # payload's own resource tree happens to contain.
        return {_PAYLOADS} if Path(directory) == _SOURCE_PACKAGE else set()

    shutil.copytree(_SOURCE_PACKAGE, destination, symlinks=False, ignore=ignore)
    try:
        _link_tree(_materialize_shared_payloads(), destination / _PAYLOADS)
    except OSError:
        # Cross-device destination, or a shared tree reaped underneath us. Either
        # way the expensive-but-always-correct path still produces the exact tree
        # the caller asked for.
        shutil.rmtree(destination / _PAYLOADS, ignore_errors=True)
        shutil.copytree(_SOURCE_PACKAGE / _PAYLOADS, destination / _PAYLOADS, symlinks=False)
    return destination
