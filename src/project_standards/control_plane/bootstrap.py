"""Exact, neutral, and recoverable initialization of consumer control-plane state."""

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from project_standards.control_plane.codec import (
    parse_catalog,
    parse_config,
    parse_lock,
    render_catalog,
    render_empty_config,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.locking import (
    LockedControlDirectory,
    LockMode,
    control_plane_lock,
    reserved_temporary_name,
)
from project_standards.control_plane.models import CentralLock
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.snapshot import safe_repository_root
from project_standards.package_contract.payload import JsonValue

_CONTROL_FILES = ("config.toml", "catalog.toml", "lock.toml")


@dataclass(frozen=True, slots=True)
class InitializationResult:
    """Report whether this call created the neutral scaffold."""

    repo: Path
    created: bool
    files: tuple[str, ...] = _CONTROL_FILES


def _expected_bytes(
    major: CatalogMajor,
    distribution: InstalledDistribution,
) -> tuple[bytes, bytes, bytes]:
    try:
        catalog = distribution.consumer_catalog(major)
    except ValueError as exc:
        raise ControlPlaneError(
            "installed distribution cannot supply the requested catalog"
        ) from exc
    config_content = render_empty_config(major)
    config = parse_config(config_content)
    config_value = cast(JsonValue, config.model_dump(mode="json"))
    lock = CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.1",
                "catalog": major.value,
                "release": distribution.tool_release.value,
                "catalog_digest": catalog.project_standards.digest.value,
                "config_digest": semantic_digest(config_value).value,
            },
            "standards": {},
            "accepted_tracks": {},
            "artifacts": [],
            "referenced_inputs": [],
        }
    )
    return config_content, render_catalog(catalog), render_lock(lock)


def _stage_file(
    control: LockedControlDirectory,
    name: str,
    content: bytes,
) -> str:
    """Durably stage one complete file without publishing its canonical name."""
    temporary = reserved_temporary_name()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(temporary, flags, 0o600, dir_fd=control.descriptor)
    except OSError as exc:
        raise OSError(f"could not create staged {name}") from exc
    try:
        os.fchmod(descriptor, 0o644)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError(f"could not write staged {name}")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        with suppress(OSError):
            os.unlink(temporary, dir_fd=control.descriptor)
        raise
    os.close(descriptor)
    return temporary


def _remove_staged(control: LockedControlDirectory, names: list[str]) -> None:
    for name in names:
        try:
            os.unlink(name, dir_fd=control.descriptor)
        except FileNotFoundError:
            continue


def _existing_result(
    repo: Path,
    control: LockedControlDirectory,
    expected: tuple[bytes, bytes, bytes],
) -> InitializationResult:
    kinds = {name: control.file_kind(name) for name in _CONTROL_FILES}
    if "unsafe" in kinds.values():
        raise ControlPlaneError("existing control plane contains an unsafe file entry")
    if "missing" in kinds.values():
        raise ControlPlaneError("existing control plane is incomplete")
    try:
        actual = (
            parse_config(control.read_bytes("config.toml")),
            parse_catalog(control.read_bytes("catalog.toml")),
            parse_lock(control.read_bytes("lock.toml")),
        )
        wanted = (
            parse_config(expected[0]),
            parse_catalog(expected[1]),
            parse_lock(expected[2]),
        )
    except ValueError as exc:
        raise ControlPlaneError("existing control plane is not canonical") from exc
    if actual != wanted:
        raise ControlPlaneError(
            "repository is already initialized with different desired or applied state"
        )
    if not control.is_current():
        raise ControlPlaneError("control-plane directory changed during initialization")
    return InitializationResult(repo=repo, created=False)


def initialize_control_plane(
    repo: Path,
    catalog_major: CatalogMajor | str,
    *,
    distribution: InstalledDistribution | None = None,
) -> InitializationResult:
    """Create or confirm the exact three-file neutral consumer scaffold.

    A failure before the first canonical name is published removes a directory
    created solely by this call. Once publication starts, any partial scaffold
    remains visible for explicit incomplete-state recovery rather than being
    silently rolled back after reviewers may have observed it.
    """
    normalized = safe_repository_root(repo)
    major = (
        catalog_major if isinstance(catalog_major, CatalogMajor) else CatalogMajor(catalog_major)
    )
    legacy = normalized / ".project-standards.yml"
    if legacy.exists() or legacy.is_symlink():
        raise ControlPlaneError("legacy standards authority blocks plain initialization")
    selected_distribution = distribution or InstalledDistribution.current()
    expected = _expected_bytes(major, selected_distribution)
    control_path = normalized / ".standards"
    if control_path.is_symlink():
        raise ControlPlaneError("control-plane directory cannot be a symlink")

    created = False
    try:
        control_path.mkdir(mode=0o755)
        created = True
    except FileExistsError:
        if control_path.is_symlink() or not control_path.is_dir():
            raise ControlPlaneError("control-plane path is not a regular directory") from None
    except OSError as exc:
        raise ControlPlaneError("control-plane directory could not be created") from exc

    published = 0
    try:
        with control_plane_lock(normalized, LockMode.WRITE) as control:
            if legacy.exists() or legacy.is_symlink():
                raise ControlPlaneError("legacy standards authority appeared during initialization")
            if not created:
                return _existing_result(normalized, control, expected)

            staged: list[str] = []
            try:
                for name, content in zip(_CONTROL_FILES, expected, strict=True):
                    staged.append(_stage_file(control, name, content))
            except OSError as exc:
                _remove_staged(control, staged)
                raise ControlPlaneError("could not stage the neutral control plane") from exc
            if not control.is_current():
                _remove_staged(control, staged)
                raise ControlPlaneError("control-plane directory changed before publication")

            # Lock is published last because it claims the config/catalog pair is
            # authoritative; reversing this order would expose applied-state claims
            # before their inputs exist.
            try:
                for temporary, name in zip(staged, _CONTROL_FILES, strict=True):
                    os.replace(
                        temporary,
                        name,
                        src_dir_fd=control.descriptor,
                        dst_dir_fd=control.descriptor,
                    )
                    published += 1
                    os.fsync(control.descriptor)
            except OSError as exc:
                _remove_staged(control, staged[published:])
                raise ControlPlaneError("could not publish the neutral control plane") from exc
            return InitializationResult(repo=normalized, created=True)
    except BaseException:
        # Only a call-owned empty directory is removable. A published file or a
        # concurrent entry turns this into explicit incomplete state for recovery.
        if created and published == 0:
            with suppress(OSError):
                control_path.rmdir()
        raise
