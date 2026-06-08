"""The adopt engine: resolve manifests into a safe, deduplicated action plan and execute it."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from project_standards.adopt.errors import ManifestError, UsageError, WriteError
from project_standards.adopt.manifest import (
    BUNDLES_DIR,
    Artifact,
    available_standards,
    load_manifest,
)


def major_ref() -> str:
    """`v<major>` derived from the installed package version (never hardcoded)."""
    try:
        full = version("project-standards")
    except PackageNotFoundError as exc:  # pragma: no cover - exercised via monkeypatch
        raise ManifestError("cannot resolve project-standards version for @vN ref") from exc
    return "v" + full.split(".")[0]


def resolve_source(artifact: Artifact, standard_id: str, bundles_dir: Path = BUNDLES_DIR) -> Path:
    """Absolute path to an artifact's source, validated to live inside `bundles/`.

    Absolute or `..`-traversing source/shared, or a path that escapes the bundle tree,
    or an absent file -> ManifestError (exit 3).
    """
    rel = artifact.shared if artifact.shared is not None else artifact.source
    assert rel is not None  # guaranteed by manifest validation
    if rel.startswith("/") or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ManifestError(f"unsafe source path {rel!r} in {standard_id}")
    base = bundles_dir if artifact.shared is not None else bundles_dir / standard_id
    resolved = (base / rel).resolve()
    root = bundles_dir.resolve()
    if root not in resolved.parents and resolved != root:
        raise ManifestError(f"source {rel!r} escapes bundle tree in {standard_id}")
    if not resolved.is_file():
        raise ManifestError(f"source template missing: {resolved}")
    return resolved


@dataclass(frozen=True)
class Action:
    """A resolved, ready-to-execute unit. `fragment` actions are reported, never written."""

    kind: str
    source_path: Path
    dest: str | None  # relative dest for file/workflow-caller
    target: str | None  # relative target for fragment
    standards: tuple[str, ...]  # contributing standard ids (for reporting)


def build_plan(standard_ids: list[str], *, bundles_dir: Path = BUNDLES_DIR) -> list[Action]:
    """Flatten requested standards into one deduplicated, source-resolved action list.

    Unknown id or two *owned* artifacts targeting one dest -> UsageError (exit 2).
    A *shared* source referenced by multiple standards collapses to one action.
    """
    known = set(available_standards(bundles_dir))
    unknown = [s for s in standard_ids if s not in known]
    if unknown:
        raise UsageError(f"unknown standard(s): {', '.join(sorted(unknown))}")

    # Collision is purely about the destination: two artifacts (of ANY kind) that
    # would write the same dest from DIFFERENT sources is an authoring bug. The same
    # source (a shared file referenced by two standards) dedupes to one action.
    write_actions: dict[str, Action] = {}  # dest -> Action (file / workflow-caller)
    fragment_actions: list[Action] = []  # fragments are reported; multiple per target allowed
    for sid in standard_ids:
        manifest = load_manifest(sid, bundles_dir)
        for art in manifest.artifacts:
            src = resolve_source(art, sid, bundles_dir)
            if art.kind == "fragment":
                assert art.target is not None
                fragment_actions.append(
                    Action(
                        kind="fragment",
                        source_path=src,
                        dest=None,
                        target=art.target,
                        standards=(sid,),
                    )
                )
                continue
            assert art.dest is not None
            existing = write_actions.get(art.dest)
            if existing is not None:
                if str(existing.source_path) != str(src):
                    raise UsageError(
                        f"destination collision at {art.dest!r}: "
                        f"{existing.standards[0]} and {sid} supply different sources"
                    )
                write_actions[art.dest] = Action(
                    kind=existing.kind,
                    source_path=existing.source_path,
                    dest=existing.dest,
                    target=None,
                    standards=(*existing.standards, sid),
                )
                continue
            write_actions[art.dest] = Action(
                kind=art.kind, source_path=src, dest=art.dest, target=None, standards=(sid,)
            )
    return list(write_actions.values()) + fragment_actions


_REF_PLACEHOLDER = "{{ref}}"


@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)
    symlink_skipped: list[str] = field(default_factory=list)
    # target -> list of fragment snippets (multiple standards may contribute to one target).
    fragments: dict[str, list[str]] = field(default_factory=dict)


def _require_safe_relative(rel: str) -> None:
    """Reject absolute paths and `..` traversal (exit 2)."""
    if rel.startswith("/") or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise UsageError(f"unsafe path: {rel!r}")


def validate_dest(rel: str, dest_root: Path) -> Path:
    """Absolute destination that does NOT follow a final symlink, contained under dest_root.

    Critically, the leaf is left UNRESOLVED: `Path.resolve()` follows symlinks, which would
    make `is_symlink()` inspect the link's target instead of the link. Containment is checked
    lexically with `os.path.normpath` (no filesystem access, no symlink following); `..` and
    absolute paths are already rejected above.
    """
    _require_safe_relative(rel)
    root = dest_root.resolve()
    candidate = root / rel  # leaf unresolved -> a symlink leaf stays detectable
    normalized = Path(os.path.normpath(candidate))
    if root != normalized and root not in normalized.parents:
        raise UsageError(f"destination escapes --dest: {rel!r}")
    return candidate


def _has_symlinked_ancestor(abs_dest: Path, root: Path) -> bool:
    """True if any EXISTING directory between root (exclusive) and the leaf is a symlink.

    A symlinked parent (e.g. `--dest/linkdir -> /elsewhere`) could let a write escape `--dest`
    even when the leaf itself is not a symlink. `is_symlink()` is False for non-existent paths,
    so only real symlinked ancestors trip this.
    """
    for parent in abs_dest.parents:
        if parent == root:
            break
        if parent.is_symlink():
            return True
    return False


def _read_bytes(path: Path) -> bytes:
    """Source read, mapping recoverable I/O failure to WriteError (exit 1)."""
    try:
        return path.read_bytes()
    except OSError as exc:
        raise WriteError(f"cannot read source {path}: {exc}") from exc


def _render(action: Action, ref: str) -> bytes:
    """Bytes to write for a file/workflow-caller action ({{ref}} substituted for callers)."""
    data = _read_bytes(action.source_path)
    if action.kind == "workflow-caller":
        data = data.replace(_REF_PLACEHOLDER.encode(), ref.encode())
    return data


def _atomic_write(target: Path, data: bytes) -> None:
    """Write to a temp file in the target's directory, then os.replace into place.

    EVERY filesystem step (mkdir, mkstemp, write, replace) is inside the guard so a
    recoverable failure surfaces as WriteError (exit 1), never a raw traceback. The
    temp file is cleaned up on any failure; an existing destination is left intact.
    """
    tmp: Path | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".adopt-", suffix=".tmp")
        tmp = Path(tmp_name)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        # Module-level os.replace (not Path.replace) so the failure-injection test can
        # monkeypatch this exact atomic-rename call.
        os.replace(tmp, target)  # noqa: PTH105
    except OSError as exc:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise WriteError(f"failed writing {target}: {exc}") from exc


def execute_plan(plan: list[Action], dest_root: Path, *, force: bool, dry_run: bool) -> Report:
    """Classify and execute each action; accumulate fragments (multiple per target)."""
    ref = major_ref()
    report = Report()
    for action in plan:
        if action.kind == "fragment":
            assert action.target is not None
            _require_safe_relative(action.target)  # target safety even though never written
            try:
                snippet = action.source_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise WriteError(f"cannot read fragment {action.source_path}: {exc}") from exc
            report.fragments.setdefault(action.target, []).append(snippet)
            continue
        assert action.dest is not None
        abs_dest = validate_dest(action.dest, dest_root)
        if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, dest_root.resolve()):
            report.symlink_skipped.append(
                action.dest
            )  # never write through a symlinked leaf OR parent
            continue
        exists = abs_dest.exists()
        if exists and not force:
            report.skipped.append(action.dest)
            continue
        rendered = _render(action, ref)  # may raise WriteError on unreadable source
        if not dry_run:
            _atomic_write(abs_dest, rendered)
        (report.overwritten if exists else report.created).append(action.dest)
    return report
