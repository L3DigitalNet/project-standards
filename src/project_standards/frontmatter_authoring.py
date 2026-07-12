"""Plan frontmatter authoring changes from immutable repository snapshots."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.schemas import (
    MutationActionSchema,
    MutationPlanSchema,
)
from project_standards.control_plane.snapshot import (
    EntryKind,
    RepositorySnapshot,
    SnapshotEntry,
)
from project_standards.format_frontmatter import VALID_DOC_TYPES, format_text
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import AdapterKind
from project_standards.validate_frontmatter import FrontmatterParseError, parse_frontmatter
from project_standards.validate_id import plan_fix_content


@dataclass(frozen=True, slots=True)
class FrontmatterAuthoringPlan:
    """Complete fix plan plus content-safe command reporting facts."""

    plan: MutationPlanSchema
    formatted_paths: tuple[str, ...]
    fixed_ids: tuple[tuple[str, str], ...]
    warnings: tuple[tuple[str, str], ...]
    refused_paths: tuple[str, ...]


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _targets(repo: Path, paths: tuple[Path, ...]) -> tuple[SafeRelativePath, ...]:
    root = repo.resolve(strict=True)
    try:
        relative = tuple(path.relative_to(root) if path.is_absolute() else path for path in paths)
        return tuple(SafeRelativePath.parse(path.as_posix()) for path in relative)
    except (OSError, ValueError) as exc:
        raise ControlPlaneError("frontmatter authoring path must be repository-relative") from exc


def _existing_ids(entries: tuple[SnapshotEntry, ...]) -> set[str]:
    result: set[str] = set()
    for entry in entries:
        if entry.kind is not EntryKind.REGULAR or entry.content is None:
            continue
        try:
            metadata = parse_frontmatter(entry.content.decode("utf-8-sig"))
        except UnicodeDecodeError, FrontmatterParseError:
            continue
        if isinstance(metadata, dict):
            document_id = metadata.get("id")
            if isinstance(document_id, str) and document_id:
                result.add(document_id)
    return result


def _plan_entries(
    entries: tuple[SnapshotEntry, ...],
    *,
    version: PackageVersion,
    format_documents: bool,
    repair_ids: bool,
    valid_doc_types: frozenset[str],
    token_factory: Callable[[], str] | None,
    today: str | None = None,
    bump_updated: bool = False,
) -> FrontmatterAuthoringPlan:
    existing_ids = _existing_ids(entries)
    actions: list[MutationActionSchema] = []
    formatted: list[str] = []
    fixed: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    refused: list[str] = []

    for entry in entries:
        target = entry.path.original
        if entry.kind is not EntryKind.REGULAR or entry.content is None:
            warnings.append((target, "cannot fix a path that is not a regular file"))
            refused.append(target)
            continue
        try:
            text = entry.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            warnings.append((target, "file is not valid UTF-8"))
            continue
        if format_documents:
            formatted_text, changed, format_warnings = format_text(
                text,
                path=Path(target),
                scaffold=True,
                today=today,
                bump_updated=bump_updated,
                token_factory=token_factory,
            )
        else:
            formatted_text, changed, format_warnings = text, False, []
        warnings.extend((target, warning) for warning in format_warnings)
        formatted_bytes = formatted_text.encode("utf-8")
        replacement = formatted_bytes
        if repair_ids:
            replacement, result = plan_fix_content(
                formatted_bytes,
                valid_doc_types,
                existing_ids,
                token_factory=token_factory,
            )
            if result.new_id is not None:
                existing_ids.add(result.new_id)
                fixed.append((target, result.new_id))
            elif result.skip_reason is not None and result.skip_reason != "id is already valid":
                warnings.append((target, result.skip_reason))
        if not changed and replacement == entry.content:
            continue
        if changed:
            formatted.append(target)
        actions.append(
            MutationActionSchema(
                kind=ActionKind.UPDATE,
                target=entry.path,
                adapter=AdapterKind.WHOLE_FILE,
                scope="$file",
                summary=(
                    "format frontmatter and repair its document id"
                    if repair_ids
                    else "format frontmatter"
                ),
                precondition_digest=entry.precondition_digest,
                content_digest=Sha256Digest(_digest(replacement)),
                content_base64=base64.b64encode(replacement).decode("ascii"),
                mode=entry.mode,
            )
        )
    return FrontmatterAuthoringPlan(
        MutationPlanSchema(
            schema_version="1.0",
            standard_id="markdown-frontmatter",
            version=version,
            actions=actions,
        ),
        tuple(formatted),
        tuple(fixed),
        tuple(warnings),
        tuple(refused),
    )


def _plan_frontmatter(
    repo: Path,
    paths: tuple[Path, ...],
    *,
    version: PackageVersion,
    format_documents: bool,
    repair_ids: bool,
    valid_doc_types: frozenset[str] = VALID_DOC_TYPES,
    token_factory: Callable[[], str] | None,
    today: str | None = None,
    bump_updated: bool = False,
) -> FrontmatterAuthoringPlan:
    targets = _targets(repo, paths)
    snapshot = RepositorySnapshot.capture(repo, targets)
    return _plan_entries(
        snapshot.entries,
        version=version,
        format_documents=format_documents,
        repair_ids=repair_ids,
        valid_doc_types=valid_doc_types,
        token_factory=token_factory,
        today=today,
        bump_updated=bump_updated,
    )


def plan_frontmatter_fix_entries(
    entries: tuple[SnapshotEntry, ...],
    *,
    version: PackageVersion,
    token_factory: Callable[[], str] | None,
    today: str,
) -> FrontmatterAuthoringPlan:
    """Return a deterministic fix plan from provider-supplied immutable entries."""
    return _plan_entries(
        entries,
        version=version,
        format_documents=True,
        repair_ids=True,
        valid_doc_types=VALID_DOC_TYPES,
        token_factory=token_factory,
        today=today,
    )


def plan_frontmatter_format_entries(
    entries: tuple[SnapshotEntry, ...],
    *,
    version: PackageVersion,
    token_factory: Callable[[], str] | None,
    today: str,
    bump_updated: bool,
) -> FrontmatterAuthoringPlan:
    """Return a format-only plan from provider-supplied immutable entries."""
    return _plan_entries(
        entries,
        version=version,
        format_documents=True,
        repair_ids=False,
        valid_doc_types=VALID_DOC_TYPES,
        token_factory=token_factory,
        today=today,
        bump_updated=bump_updated,
    )


def plan_frontmatter_id_fix_entries(
    entries: tuple[SnapshotEntry, ...],
    *,
    version: PackageVersion,
    valid_doc_types: frozenset[str],
    token_factory: Callable[[], str] | None,
) -> FrontmatterAuthoringPlan:
    """Return an ID-only plan from provider-supplied immutable entries."""
    return _plan_entries(
        entries,
        version=version,
        format_documents=False,
        repair_ids=True,
        valid_doc_types=valid_doc_types,
        token_factory=token_factory,
    )


def plan_frontmatter_format(
    repo: Path,
    paths: tuple[Path, ...],
    *,
    version: PackageVersion,
    token_factory: Callable[[], str] | None = None,
    today: str | None = None,
    bump_updated: bool = False,
) -> FrontmatterAuthoringPlan:
    """Return a complete formatting plan without changing live files."""
    return _plan_frontmatter(
        repo,
        paths,
        version=version,
        format_documents=True,
        repair_ids=False,
        valid_doc_types=VALID_DOC_TYPES,
        token_factory=token_factory,
        today=today,
        bump_updated=bump_updated,
    )


def plan_frontmatter_fix(
    repo: Path,
    paths: tuple[Path, ...],
    *,
    version: PackageVersion,
    token_factory: Callable[[], str] | None = None,
    today: str | None = None,
    bump_updated: bool = False,
) -> FrontmatterAuthoringPlan:
    """Return one combined format-and-id plan without changing live files."""
    return _plan_frontmatter(
        repo,
        paths,
        version=version,
        format_documents=True,
        repair_ids=True,
        valid_doc_types=VALID_DOC_TYPES,
        token_factory=token_factory,
        today=today,
        bump_updated=bump_updated,
    )


def plan_frontmatter_id_fix(
    repo: Path,
    paths: tuple[Path, ...],
    *,
    version: PackageVersion,
    valid_doc_types: frozenset[str],
    token_factory: Callable[[], str] | None = None,
) -> FrontmatterAuthoringPlan:
    """Return an ID-only repair plan without formatting other frontmatter bytes."""
    return _plan_frontmatter(
        repo,
        paths,
        version=version,
        format_documents=False,
        repair_ids=True,
        valid_doc_types=valid_doc_types,
        token_factory=token_factory,
    )
