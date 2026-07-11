"""Symlink-only projection from canonical payloads into installed package data."""

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from project_standards.package_contract.diagnostics import (
    PackageContractError,
    PackageFinding,
    sort_findings,
)
from project_standards.package_contract.discovery import discover_v2_families
from project_standards.package_contract.repository import build_package_repository


@dataclass(frozen=True, slots=True)
class ProjectionLink:
    """One exact runtime member and its canonical source file."""

    relative_path: str
    destination: Path
    source: Path
    target: str
    standard_id: str
    version: str


@dataclass(frozen=True, slots=True)
class ProjectionPlan:
    """Complete deterministic projection for every indexed V2 payload file."""

    root: Path
    projection_root: Path
    links: tuple[ProjectionLink, ...]


def _safe_root(root: Path) -> Path:
    try:
        if root.is_symlink() or not root.is_dir():
            raise PackageContractError("projection root must be a regular directory")
        return root.resolve(strict=True)
    except OSError as exc:
        raise PackageContractError("projection root could not be resolved") from exc


def _projection_root(root: Path) -> Path:
    projection = root / "src/project_standards/payloads"
    try:
        for path in (
            root / "src",
            root / "src/project_standards",
            projection,
        ):
            if path.is_symlink():
                raise PackageContractError("projection path cannot contain a directory symlink")
    except OSError as exc:
        raise PackageContractError("projection path could not be inspected") from exc
    return projection


def plan_payload_projection(root: Path) -> ProjectionPlan:
    """Plan exact relative file links without modifying source or projection trees."""
    normalized_root = _safe_root(root)
    projection = _projection_root(normalized_root)
    discovery = discover_v2_families(normalized_root)
    if discovery.findings:
        raise PackageContractError("V2 family discovery is not clean enough to project")
    if not discovery.paths:
        return ProjectionPlan(normalized_root, projection, ())

    allowlist = [path.parent.name for path in discovery.paths]
    repository = build_package_repository(
        normalized_root,
        family_allowlist=allowlist,
    )
    if repository.findings:
        raise PackageContractError("V2 package repository is not clean enough to project")

    links: list[ProjectionLink] = []
    for payload in repository.payloads:
        standard_id = payload.manifest.payload.standard
        version = payload.manifest.payload.version.value
        canonical_root = normalized_root / f"standards/{standard_id}/versions/{version}"
        runtime_root = projection / standard_id / version
        for entry in payload.integrity.inventory:
            relative_file = entry.path.normalized.as_posix()
            source = canonical_root / entry.path.normalized
            destination = runtime_root / entry.path.normalized
            target = Path(os.path.relpath(source, start=destination.parent)).as_posix()
            links.append(
                ProjectionLink(
                    relative_path=f"{standard_id}/{version}/{relative_file}",
                    destination=destination,
                    source=source,
                    target=target,
                    standard_id=standard_id,
                    version=version,
                )
            )
    return ProjectionPlan(
        normalized_root,
        projection,
        tuple(sorted(links, key=lambda link: link.relative_path.encode("utf-8"))),
    )


def _finding(code: str, plan: ProjectionPlan, path: Path, message: str) -> PackageFinding:
    try:
        relative = path.relative_to(plan.projection_root)
        parts = relative.parts
    except ValueError:
        relative = path.relative_to(plan.root)
        parts = ()
    return PackageFinding(
        code=code,
        severity="error",
        standard_id=parts[0] if len(parts) >= 1 else "project-standards",
        version=parts[1] if len(parts) >= 2 else "",
        path=path.relative_to(plan.root).as_posix(),
        identity="payload-projection",
        message=message,
        hint="regenerate the symlink-only installed payload projection",
    )


def projection_findings(root: Path) -> tuple[PackageFinding, ...]:
    """Return projection drift findings without modifying any filesystem entry."""
    plan = plan_payload_projection(root)
    expected = {link.destination: link for link in plan.links}
    canonical_roots = {
        plan.root / f"standards/{link.standard_id}/versions/{link.version}" for link in plan.links
    }
    findings: list[PackageFinding] = []
    valid: set[Path] = set()
    try:
        entries = (
            sorted(
                plan.projection_root.rglob("*"),
                key=lambda path: path.as_posix().encode("utf-8"),
            )
            if plan.projection_root.is_dir()
            else []
        )
    except OSError as exc:
        raise PackageContractError("projection tree could not be enumerated") from exc

    for entry in entries:
        if entry.is_symlink():
            raw_target = entry.readlink()
            if raw_target.is_absolute():
                findings.append(
                    _finding(
                        "PC-PROJECTION-ABSOLUTE",
                        plan,
                        entry,
                        "projection file link must use a relative target",
                    )
                )
            try:
                resolved = entry.resolve(strict=True)
            except OSError, RuntimeError:
                findings.append(
                    _finding(
                        "PC-PROJECTION-BROKEN",
                        plan,
                        entry,
                        "projection contains a broken file link",
                    )
                )
                continue
            if resolved.is_dir():
                findings.append(
                    _finding(
                        "PC-PROJECTION-DIRECTORY-LINK",
                        plan,
                        entry,
                        "projection contains a directory symlink",
                    )
                )
                continue
            if not any(resolved.is_relative_to(root_path) for root_path in canonical_roots):
                findings.append(
                    _finding(
                        "PC-PROJECTION-OUTSIDE",
                        plan,
                        entry,
                        "projection link leaves canonical payload roots",
                    )
                )
            planned = expected.get(entry)
            if planned is None:
                findings.append(
                    _finding(
                        "PC-PROJECTION-EXTRA",
                        plan,
                        entry,
                        "projection contains an undeclared file link",
                    )
                )
            elif (
                not raw_target.is_absolute()
                and resolved == planned.source.resolve(strict=True)
                and raw_target.as_posix() == planned.target
            ):
                valid.add(entry)
            else:
                findings.append(
                    _finding(
                        "PC-PROJECTION-WRONG-TARGET",
                        plan,
                        entry,
                        "projection link does not identify its exact canonical source",
                    )
                )
            continue
        if entry.is_dir():
            continue
        findings.append(
            _finding(
                "PC-PROJECTION-NONLINK",
                plan,
                entry,
                "projection contains a regular or unsupported file instead of a symlink",
            )
        )

    for missing in sorted(set(expected) - valid, key=lambda path: path.as_posix()):
        if not missing.exists() and not missing.is_symlink():
            findings.append(
                _finding(
                    "PC-PROJECTION-MISSING",
                    plan,
                    missing,
                    "projection is missing a declared payload file link",
                )
            )
    return tuple(sort_findings(findings))


def _remove_empty_directories(projection_root: Path) -> None:
    if not projection_root.is_dir():
        return
    directories = sorted(
        (path for path in projection_root.rglob("*") if path.is_dir() and not path.is_symlink()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        with suppress(OSError):
            directory.rmdir()
    with suppress(OSError):
        projection_root.rmdir()


def sync_payload_projection(
    root: Path,
    *,
    check: bool,
) -> tuple[PackageFinding, ...]:
    """Check read-only, or reconcile only projection symlinks and empty directories."""
    plan = plan_payload_projection(root)
    findings = projection_findings(plan.root)
    if check or not findings:
        return findings
    blocking = {
        "PC-PROJECTION-NONLINK",
        "PC-PROJECTION-DIRECTORY-LINK",
    }
    if any(finding.code in blocking for finding in findings):
        raise PackageContractError(
            "projection contains a regular file or directory symlink and was not modified"
        )

    expected = {link.destination: link for link in plan.links}
    if plan.projection_root.is_dir():
        for entry in sorted(plan.projection_root.rglob("*"), reverse=True):
            if entry.is_symlink() and entry not in expected:
                entry.unlink()
    for link in plan.links:
        link.destination.parent.mkdir(parents=True, exist_ok=True)
        if link.destination.is_symlink():
            if link.destination.readlink().as_posix() == link.target:
                continue
            link.destination.unlink()
        elif link.destination.exists():
            raise PackageContractError(
                f"projection destination is a regular file: {link.relative_path}"
            )
        link.destination.symlink_to(link.target)
    _remove_empty_directories(plan.projection_root)
    return projection_findings(plan.root)
