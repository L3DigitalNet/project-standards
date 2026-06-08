"""The adopt engine: resolve manifests into a safe, deduplicated action plan and execute it."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from project_standards.adopt.errors import ManifestError, UsageError
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
