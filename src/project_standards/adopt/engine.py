"""The adopt engine: resolve manifests into a safe, deduplicated action plan and execute it."""

from __future__ import annotations

import contextlib
import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from project_standards.adopt.errors import ManifestError, UsageError, WriteError
from project_standards.adopt.manifest import (
    BUNDLES_DIR,
    Artifact,
    InstallPolicy,
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
    mode: int | None = None  # optional POSIX permissions for written artifacts
    install_policy: InstallPolicy = InstallPolicy.MANAGED
    precondition_sha256: str | None = None
    require_absent: bool = False


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
                        install_policy=art.install_policy,
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
                if existing.mode != art.mode:
                    raise UsageError(
                        f"destination collision at {art.dest!r}: "
                        f"{existing.standards[0]} and {sid} use different modes"
                    )
                if existing.install_policy is not art.install_policy:
                    raise UsageError(
                        f"destination collision at {art.dest!r}: "
                        f"{existing.standards[0]} and {sid} use different install policies"
                    )
                write_actions[art.dest] = Action(
                    kind=existing.kind,
                    source_path=existing.source_path,
                    dest=existing.dest,
                    target=None,
                    standards=(*existing.standards, sid),
                    mode=existing.mode,
                    install_policy=existing.install_policy,
                )
                continue
            write_actions[art.dest] = Action(
                kind=art.kind,
                source_path=src,
                dest=art.dest,
                target=None,
                standards=(sid,),
                mode=art.mode,
                install_policy=art.install_policy,
            )
    return list(write_actions.values()) + fragment_actions


_REF_PLACEHOLDER = "{{ref}}"


@dataclass
class Report:
    """Accumulated outcome of execute_plan: what was written, skipped, or reported.

    Fragment actions are never written to disk — they are collected here so the caller
    can print guidance. Multiple standards may contribute to the same fragment target,
    so `fragments` holds a list of snippets per target key rather than a single string.
    """

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


def render_action(action: Action, ref: str | None = None) -> bytes:
    """Bytes to write for a file/workflow-caller action ({{ref}} substituted for callers)."""
    resolved_ref = major_ref() if ref is None else ref
    data = _read_bytes(action.source_path)
    if action.kind == "workflow-caller":
        data = data.replace(_REF_PLACEHOLDER.encode(), resolved_ref.encode())
    return data


def _check_precondition(action: Action, target: Path) -> None:
    if action.require_absent:
        if target.exists() or target.is_symlink():
            raise WriteError(f"destination changed after preflight: {target}")
        return
    if action.precondition_sha256 is None:
        return
    try:
        current = target.read_bytes()
    except OSError as exc:
        raise WriteError(f"cannot recheck destination {target}: {exc}") from exc
    if hashlib.sha256(current).hexdigest() != action.precondition_sha256:
        raise WriteError(f"destination changed after preflight: {target}")


def _atomic_write(
    target: Path, data: bytes, mode: int | None = None, *, replace: bool = True
) -> bool:
    """Stage data beside target, then install it atomically.

    EVERY filesystem step (mkdir, mkstemp, write, publish) is inside the guard so a
    recoverable failure surfaces as WriteError (exit 1), never a raw traceback. Staging
    cleanup is always attempted, including after KeyboardInterrupt / generator-throw.
    Persistent cleanup failure is explicitly reported and may leave the staging alias
    beside an installed destination for manual removal; an existing destination remains
    intact when publication fails.

    Return ``False`` only when a non-replacing install loses a destination-creation
    race. Managed installs use atomic replacement; create-only installs use an atomic
    hard-link operation that cannot overwrite a destination created after classification.
    Create-only publication therefore requires hard-link support in the destination
    filesystem; unsupported link operations fail cleanly instead of falling back to a
    non-atomic write.

    Mode: if overwriting an existing file, copy its permissions. For a new file, use
    a umask-respecting 0o666 (same behaviour as open()), avoiding the mkstemp default
    of 0600 which would leave adopted files owner-only.
    """
    tmp: Path | None = None
    published = False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".adopt-", suffix=".tmp")
        tmp = Path(tmp_name)
        # Set permissions BEFORE writing data so the file never exists world-readable
        # with content, but also never stays at 0600 after the write.
        if mode is not None:
            with contextlib.suppress(OSError):
                tmp.chmod(stat.S_IMODE(mode))
        elif target.exists():
            # Preserve the existing file's mode (copy-on-overwrite).
            with contextlib.suppress(OSError):
                tmp.chmod(target.stat().st_mode & 0o777)
        else:
            # New file: apply umask so the result behaves like a normal file creation.
            mask = os.umask(0)
            os.umask(mask)
            with contextlib.suppress(OSError):
                tmp.chmod(stat.S_IMODE(0o666 & ~mask))
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        if replace:
            # Module-level os.replace (not Path.replace) so the failure-injection test can
            # monkeypatch this exact atomic-rename call.
            os.replace(tmp, target)  # noqa: PTH105
        else:
            try:
                # Both paths share a directory/filesystem. link(2) publishes the staged
                # inode atomically but returns EEXIST instead of replacing consumer content.
                # Filesystems without hard-link support fail closed through WriteError.
                os.link(tmp, target)
                published = True
            except FileExistsError:
                tmp.unlink(missing_ok=True)
                return False
            tmp.unlink()
        return True
    except OSError as exc:
        if tmp is not None:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)
        if published:
            raise WriteError(
                f"destination {target} was installed but staging cleanup failed for {tmp}: {exc}"
            ) from exc
        raise WriteError(f"failed writing {target}: {exc}") from exc
    except BaseException:
        if tmp is not None:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)
        raise


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
        if not dry_run and action.require_absent and exists:
            _check_precondition(action, abs_dest)
        if exists and action.install_policy is InstallPolicy.CREATE_ONLY:
            report.skipped.append(action.dest)
            continue
        if exists and not force:
            report.skipped.append(action.dest)
            continue
        rendered = render_action(action, ref)  # may raise WriteError on unreadable source
        if not dry_run:
            _check_precondition(action, abs_dest)
            installed = _atomic_write(
                abs_dest,
                rendered,
                action.mode,
                replace=action.install_policy is InstallPolicy.MANAGED,
            )
            if not installed:
                report.skipped.append(action.dest)
                continue
        (report.overwritten if exists else report.created).append(action.dest)
    return report


def format_report(report: Report) -> str:
    """Human-readable summary; fragments grouped under per-target headings."""
    lines: list[str] = []
    for label, items in (
        ("Created", report.created),
        ("Skipped (already present)", report.skipped),
        ("Overwritten", report.overwritten),
        ("Skipped (symlink, not written)", report.symlink_skipped),
    ):
        if items:
            lines.append(f"{label}:")
            lines.extend(f"  {p}" for p in items)
    for target, snippets in report.fragments.items():
        lines.append(f"\nAdd these sections to `{target}`:")
        for snippet in snippets:
            lines.append(snippet.rstrip("\n"))
    return "\n".join(lines)
