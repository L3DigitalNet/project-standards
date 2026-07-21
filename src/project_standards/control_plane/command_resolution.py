"""Shared repository authority and selected-package resolution for public commands."""

from __future__ import annotations

import base64
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import (
    ControlPlaneConfigurationError,
    ControlPlaneError,
)
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.locking import LockMode, control_plane_lock
from project_standards.control_plane.models import CentralLock, ConsumerCatalog, DesiredConfig
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
)
from project_standards.control_plane.resolution import resolve_packages
from project_standards.control_plane.snapshot import RepositorySnapshot
from project_standards.control_plane.state import (
    ControlPlaneState,
    StateKind,
    detect_control_plane_state,
    load_locked_control_plane_state,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.paths import PackageVersion, SafeRelativePath
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    PayloadAvailability,
    ProviderOperation,
)


class CommandResolutionError(ValueError):
    """Report an unusable command authority or package selection."""


class CommandConfigurationError(CommandResolutionError):
    """Report invalid selected-package configuration to public commands."""


class _CompanionAbsentError(CommandResolutionError):
    """Report a package missing from or disabled in unified configuration."""


_legacy_warning_emitted = False


def reset_legacy_authority_warning() -> None:
    """Start one embedded top-level command's warning scope."""
    global _legacy_warning_emitted
    _legacy_warning_emitted = False


def explicit_legacy_argument(argv: list[str]) -> Path | None:
    """Extract the last syntactically complete explicit config option."""
    selected: Path | None = None
    for index, argument in enumerate(argv):
        if argument == "--config" and index + 1 < len(argv):
            selected = Path(argv[index + 1])
        elif argument.startswith("--config="):
            value = argument.removeprefix("--config=")
            if not value:
                raise CommandResolutionError("--config requires a non-empty path")
            selected = Path(value)
    return selected


def emit_legacy_authority_warning() -> None:
    """Emit the process-wide v5 fallback warning at most once."""
    global _legacy_warning_emitted
    if _legacy_warning_emitted:
        return
    print(
        "warning: legacy .project-standards.yml remains read-only; "
        "migrate before using the V5 control plane",
        file=sys.stderr,
    )
    _legacy_warning_emitted = True


@dataclass(frozen=True, slots=True)
class SelectedCommandPackage:
    """Exact installed payload and validated options selected for one command."""

    repo: Path
    payload: InstalledPayload
    resolved: PackageVersion
    effective_config: JsonObject
    lock: CentralLock
    state: ControlPlaneState
    distribution: InstalledDistribution


def capture_command_snapshot(repo: Path, paths: tuple[str, ...]) -> JsonObject:
    """Capture declared command inputs once and return their JSON-safe states."""
    targets = tuple(SafeRelativePath.parse(path) for path in paths)
    snapshot = RepositorySnapshot.capture(repo, targets)
    return {
        entry.path.original: {
            "kind": entry.kind.value,
            "content_digest": entry.content_digest.value if entry.content_digest else None,
            "content_base64": (
                base64.b64encode(entry.content).decode("ascii")
                if entry.content is not None
                else None
            ),
            "mode": entry.mode,
            "precondition_digest": entry.precondition_digest.value,
        }
        for entry in snapshot.entries
    }


def managed_unit_snapshot(lock: CentralLock, standard_id: str) -> list[JsonValue]:
    """Return lock-bound semantic units owned by one selected package."""
    return [
        {
            "target": unit.path.original,
            "adapter": unit.adapter.value,
            "scope": unit.scope,
            "semantic_digest": unit.semantic_digest.value,
            "content_digest": unit.content_digest.value,
            "mode": unit.mode,
        }
        for unit in lock.artifacts
        if standard_id in unit.owners
    ]


def invoke_selected_provider(
    selected: SelectedCommandPackage,
    operation: ProviderOperation,
    snapshots: JsonObject,
    *,
    provider_id: str | None = None,
    effective_config: JsonObject | None = None,
) -> ProviderResult:
    """Invoke exactly one provider declared by the selected immutable payload."""
    providers = [
        provider
        for provider in selected.payload.manifest.providers
        if provider.operation is operation and (provider_id is None or provider.id == provider_id)
    ]
    if len(providers) != 1:
        label = provider_id or operation.value
        raise CommandResolutionError(
            f"selected package must declare exactly one provider for {label}"
        )
    provider = providers[0]
    try:
        return invoke_provider(
            ProviderInvocation(
                repo=selected.repo,
                payload=selected.payload,
                standard_id=selected.payload.manifest.payload.standard,
                version=selected.resolved,
                provider_id=provider.id,
                operation=operation,
                effective_config=(
                    selected.effective_config if effective_config is None else effective_config
                ),
                snapshots=snapshots,
            )
        )
    except (ControlPlaneError, PackageContractError, OSError, ValueError) as exc:
        raise CommandResolutionError(str(exc)) from exc


def _validate_applied_state(
    standard_id: str,
    state_config: DesiredConfig,
    state_catalog: ConsumerCatalog,
    state_lock: CentralLock,
) -> None:
    """Reject stale or tampered applied state before selecting command code."""
    desired = state_config.standards.get(standard_id)
    applied = state_lock.standards.get(standard_id)
    if desired is None or not desired.enabled:
        return
    if applied is None:
        raise CommandResolutionError(f"enabled package is absent from lock: {standard_id}")
    if applied.requested != desired.version:
        raise CommandResolutionError(f"lock selector disagrees with config: {standard_id}")
    if not isinstance(desired.version, str) and applied.resolved != desired.version:
        raise CommandResolutionError(f"lock does not preserve exact pin: {standard_id}")
    standard = state_catalog.standards.get(standard_id)
    entry = standard.versions.get(applied.resolved.value) if standard is not None else None
    if entry is None or entry.availability is not PayloadAvailability.CONSUMER:
        raise CommandResolutionError(f"lock selects an unavailable version: {standard_id}")
    if entry.payload_digest != applied.payload_digest:
        raise CommandResolutionError(f"lock payload digest disagrees with catalog: {standard_id}")


def _resolve_state(
    state: ControlPlaneState,
    installed: InstalledDistribution,
    standard_id: str,
    explicit_legacy: Path | None,
    *,
    require_reconciled: bool,
) -> SelectedCommandPackage | None:
    if state.kind is StateKind.LEGACY_ONLY:
        emit_legacy_authority_warning()
        return None
    if state.kind is StateKind.UNINITIALIZED:
        return None
    if state.kind is StateKind.MALFORMED and state.malformed_file == "config.toml":
        raise CommandConfigurationError(state.detail or "control-plane config is invalid")
    if state.kind is StateKind.INCOMPLETE and "config.toml" in state.missing_files:
        raise CommandConfigurationError(state.detail or "control-plane config is missing")
    if (
        state.kind is not StateKind.INITIALIZED
        or state.config is None
        or state.catalog is None
        or state.lock is None
    ):
        raise CommandResolutionError(state.detail or f"control-plane state is {state.kind.value}")
    if explicit_legacy is not None:
        raise CommandResolutionError(
            "explicit legacy override is incompatible with unified authority"
        )
    desired = state.config.standards.get(standard_id)
    if desired is None:
        raise _CompanionAbsentError(f"package is not present in unified config: {standard_id}")
    if not desired.enabled:
        raise _CompanionAbsentError(f"package is disabled in unified config: {standard_id}")
    if require_reconciled:
        _validate_applied_state(standard_id, state.config, state.catalog, state.lock)
    planner = build_planner_request(
        state.repo,
        installed,
        frozenset(),
        state=state,
    )
    resolution = resolve_packages(planner.resolution)
    selected = next(
        (item for item in resolution.packages if item.standard_id == standard_id),
        None,
    )
    if selected is None:
        raise CommandResolutionError(f"package has no selected payload: {standard_id}")
    payload = next(
        (
            item
            for item in planner.payloads
            if item.manifest.payload.standard == standard_id
            and item.manifest.payload.version == selected.applied.resolved
        ),
        None,
    )
    if payload is None:
        raise CommandResolutionError(f"selected package payload is unavailable: {standard_id}")
    if require_reconciled:
        applied = state.lock.standards[standard_id]
        desired_digest = semantic_digest(state.config.model_dump(mode="json"))
        if state.lock.project_standards.config_digest != desired_digest:
            raise CommandResolutionError("unified config has not been reconciled")
        if (
            selected.applied.resolved != applied.resolved
            or selected.applied.payload_digest != applied.payload_digest
            or selected.applied.effective_config_digest != applied.effective_config_digest
        ):
            raise CommandResolutionError(
                f"selected command package is not reconciled: {standard_id}"
            )
    return SelectedCommandPackage(
        state.repo,
        payload,
        selected.applied.resolved,
        selected.effective_config,
        state.lock,
        state,
        installed,
    )


def _resolve_state_for_command(
    state: ControlPlaneState,
    installed: InstalledDistribution,
    standard_id: str,
    explicit_legacy: Path | None,
    *,
    require_reconciled: bool,
) -> SelectedCommandPackage | None:
    """Normalize package/config failures at every public command boundary."""
    try:
        return _resolve_state(
            state,
            installed,
            standard_id,
            explicit_legacy,
            require_reconciled=require_reconciled,
        )
    except CommandResolutionError:
        raise
    except ControlPlaneConfigurationError as exc:
        raise CommandConfigurationError(str(exc)) from exc
    except (ControlPlaneError, PackageContractError, OSError, ValueError) as exc:
        raise CommandResolutionError(str(exc)) from exc


def resolve_enabled_companion(
    selected: SelectedCommandPackage,
    standard_id: str,
) -> SelectedCommandPackage | None:
    """Resolve another enabled package from the same retained authority generation."""
    try:
        return _resolve_state_for_command(
            selected.state,
            selected.distribution,
            standard_id,
            None,
            require_reconciled=True,
        )
    except _CompanionAbsentError:
        return None


@contextmanager
def selected_command(
    repo: Path,
    standard_id: str,
    distribution: InstalledDistribution | None = None,
    *,
    mode: LockMode,
    explicit_legacy: Path | None = None,
    require_reconciled: bool = True,
) -> Generator[SelectedCommandPackage | None]:
    """Resolve and retain one authority generation for a complete public command."""
    installed = distribution or InstalledDistribution.current()
    try:
        initial = detect_control_plane_state(repo, tool_release=installed.tool_release.value)
    except ValueError as exc:
        raise CommandConfigurationError(str(exc)) from exc
    if initial.kind is not StateKind.INITIALIZED:
        yield _resolve_state_for_command(
            initial,
            installed,
            standard_id,
            explicit_legacy,
            require_reconciled=require_reconciled,
        )
        return
    with control_plane_lock(initial.repo, mode) as control:
        state = load_locked_control_plane_state(
            initial.repo,
            tool_release=installed.tool_release.value,
            control=control,
        )
        yield _resolve_state_for_command(
            state,
            installed,
            standard_id,
            explicit_legacy,
            require_reconciled=require_reconciled,
        )


def reenter_selected_command(
    arguments: list[str],
    *,
    standard_id: str,
    mode: LockMode,
    reenter: Callable[[list[str], SelectedCommandPackage], int],
) -> int | None:
    """Acquire the selected-command lock and re-enter the command under it.

    Help and version requests bypass resolution. Return no outcome when the
    repository has no selected package, so the caller can continue unlocked.
    """
    if any(option in arguments for option in {"--help", "-h", "--version"}):
        return None
    try:
        with selected_command(
            Path.cwd(),
            standard_id,
            mode=mode,
            explicit_legacy=explicit_legacy_argument(arguments),
        ) as selected:
            if selected is not None:
                return reenter(arguments, selected)
    except (CommandResolutionError, OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return None


def resolve_selected_package(
    repo: Path,
    standard_id: str,
    distribution: InstalledDistribution | None = None,
    *,
    explicit_legacy: Path | None = None,
) -> SelectedCommandPackage | None:
    """Resolve unified command facts, or return the bounded legacy fallback state."""
    installed = distribution or InstalledDistribution.current()
    state = detect_control_plane_state(repo, tool_release=installed.tool_release.value)
    return _resolve_state_for_command(
        state,
        installed,
        standard_id,
        explicit_legacy,
        require_reconciled=True,
    )
