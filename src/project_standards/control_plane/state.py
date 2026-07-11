"""Locked detection and loading of consumer control-plane authority state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from project_standards.control_plane.codec import parse_catalog, parse_config, parse_lock
from project_standards.control_plane.distribution import ParsedToolRelease
from project_standards.control_plane.locking import (
    LockedControlDirectory,
    LockMode,
    control_plane_lock,
)
from project_standards.control_plane.models import CentralLock, ConsumerCatalog, DesiredConfig


class StateKind(StrEnum):
    """Mutually exclusive authority and compatibility states for one repository."""

    UNINITIALIZED = "uninitialized"
    LEGACY_ONLY = "legacy-only"
    INCOMPLETE = "incomplete"
    DUAL_AUTHORITY = "dual-authority"
    MALFORMED = "malformed"
    INCONSISTENT = "inconsistent"
    TOOL_MISMATCH = "tool-mismatch"
    NEWER_RELEASE = "newer-release"
    INITIALIZED = "initialized"


@dataclass(frozen=True, slots=True)
class ControlPlaneState:
    """Loaded state facts or a content-safe reason they are unavailable."""

    kind: StateKind
    repo: Path
    config: DesiredConfig | None = None
    catalog: ConsumerCatalog | None = None
    lock: CentralLock | None = None
    detail: str | None = None


def _safe_repo(repo: Path) -> Path:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise ValueError("repository root must be a regular directory")
        return repo.resolve(strict=True)
    except OSError as exc:
        raise ValueError("repository root could not be resolved") from exc


def _state(kind: StateKind, repo: Path, detail: str | None = None) -> ControlPlaneState:
    return ControlPlaneState(kind=kind, repo=repo, detail=detail)


def _load_initialized_state(
    repo: Path,
    tool: ParsedToolRelease,
    control: LockedControlDirectory,
) -> ControlPlaneState:
    legacy = repo / ".project-standards.yml"
    if legacy.exists() or legacy.is_symlink():
        return _state(
            StateKind.DUAL_AUTHORITY,
            repo,
            "legacy and unified configuration authorities both exist",
        )

    try:
        kinds = {
            name: control.file_kind(name) for name in ("config.toml", "catalog.toml", "lock.toml")
        }
    except ValueError:
        return _state(StateKind.MALFORMED, repo, "control-plane files could not be inspected")
    if "unsafe" in kinds.values():
        return _state(
            StateKind.MALFORMED,
            repo,
            "control plane contains an unsafe required-file entry",
        )
    missing = [name for name, kind in kinds.items() if kind == "missing"]
    if missing:
        return _state(
            StateKind.INCOMPLETE,
            repo,
            "control plane is missing one or more required regular files",
        )

    try:
        config = parse_config(control.read_bytes("config.toml"))
        catalog = parse_catalog(control.read_bytes("catalog.toml"))
        lock = parse_lock(control.read_bytes("lock.toml"))
    except ValueError:
        return _state(
            StateKind.MALFORMED,
            repo,
            "one or more control-plane files are invalid",
        )
    if not control.is_current():
        return _state(
            StateKind.MALFORMED,
            repo,
            "control-plane directory changed while state was being read",
        )

    majors = {
        config.project_standards.catalog.major,
        catalog.project_standards.catalog.major,
        lock.project_standards.catalog.major,
    }
    if len(majors) != 1:
        return ControlPlaneState(
            kind=StateKind.INCONSISTENT,
            repo=repo,
            config=config,
            catalog=catalog,
            lock=lock,
            detail="control-plane files disagree on the catalog major",
        )
    selected_major = next(iter(majors))
    if lock.project_standards.catalog_digest != catalog.project_standards.digest:
        return ControlPlaneState(
            kind=StateKind.INCONSISTENT,
            repo=repo,
            config=config,
            catalog=catalog,
            lock=lock,
            detail="central lock does not identify the current catalog digest",
        )
    if tool.major != selected_major:
        return ControlPlaneState(
            kind=StateKind.TOOL_MISMATCH,
            repo=repo,
            config=config,
            catalog=catalog,
            lock=lock,
            detail="installed tool major does not match configured catalog major",
        )

    catalog_release = ParsedToolRelease(catalog.project_standards.release)
    lock_release = ParsedToolRelease(lock.project_standards.release)
    if max(catalog_release.sort_key, lock_release.sort_key) > tool.sort_key:
        return ControlPlaneState(
            kind=StateKind.NEWER_RELEASE,
            repo=repo,
            config=config,
            catalog=catalog,
            lock=lock,
            detail="control-plane state was written by a newer tool release",
        )
    return ControlPlaneState(
        kind=StateKind.INITIALIZED,
        repo=repo,
        config=config,
        catalog=catalog,
        lock=lock,
    )


def detect_control_plane_state(repo: Path, *, tool_release: str) -> ControlPlaneState:
    """Detect authority and load unified files only while holding a shared lock."""
    normalized = _safe_repo(repo)
    tool = ParsedToolRelease(tool_release)
    control = normalized / ".standards"

    # Absence cannot be locked. Recheck after inspecting legacy authority so an
    # init that publishes the directory concurrently causes a locked retry.
    for _attempt in range(2):
        if control.exists() or control.is_symlink():
            try:
                with control_plane_lock(normalized, LockMode.READ) as locked:
                    return _load_initialized_state(normalized, tool, locked)
            except ValueError:
                return _state(
                    StateKind.MALFORMED,
                    normalized,
                    "control-plane directory is not a safe regular directory",
                )
        legacy = normalized / ".project-standards.yml"
        legacy_exists = legacy.exists() or legacy.is_symlink()
        if not control.exists() and not control.is_symlink():
            kind = StateKind.LEGACY_ONLY if legacy_exists else StateKind.UNINITIALIZED
            return _state(kind, normalized)
    return _state(StateKind.MALFORMED, normalized, "control-plane state changed during detection")
