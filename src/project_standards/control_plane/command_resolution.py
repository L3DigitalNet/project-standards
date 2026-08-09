"""Shared repository authority and selected-package resolution for public commands."""

from __future__ import annotations

import base64
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import (
    ControlPlaneConfigurationError,
    ControlPlaneError,
)
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.locking import LockMode, control_plane_lock
from project_standards.control_plane.models import (
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
    LockedUnit,
)
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
from project_standards.package_contract.catalog import CatalogRole
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.paths import PackageVersion, SafeRelativePath
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    JsonValue,
    PayloadAvailability,
    ProviderOperation,
    load_option_schema,
)


class CommandResolutionError(ControlPlaneError):
    """Report an unusable command authority or package selection."""


class CommandConfigurationError(CommandResolutionError):
    """Report invalid selected-package configuration to public commands."""


class _CompanionAbsentError(CommandResolutionError):
    """Report a package missing from or disabled in unified configuration."""


_legacy_warning_emitted = False
_disclosed_read_bases: set[str] = set()


def reset_legacy_authority_warning() -> None:
    """Start one embedded top-level command's warning scope.

    Read-basis disclosures share this scope: `project-standards validate` fans
    one command out across three validators that each resolve authority, and a
    consumer must see one note per invocation rather than one per validator.
    """
    global _legacy_warning_emitted
    _legacy_warning_emitted = False
    _disclosed_read_bases.clear()


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
    """Emit the process-wide legacy-authority note at most once.

    Factual, not imperative (5.8.0 FR-011 / issue #30): UPGRADING.md §2
    directs consumers to run read-only commands (e.g. `agent-handoff
    size-report`/`shape-check`) against legacy authority *before* migrating.
    The prior "migrate before using" wording contradicted that documented
    workflow at the exact moment it told consumers to follow it.
    """
    global _legacy_warning_emitted
    if _legacy_warning_emitted:
        return
    print(
        "note: reading legacy .project-standards.yml authority; "
        "the V5 control plane takes over after migration",
        file=sys.stderr,
    )
    _legacy_warning_emitted = True


def _disclose_read_basis(note: str) -> None:
    """Name the authority a read-only command resolved, at most once per scope."""
    if note in _disclosed_read_bases:
        return
    print(f"note: {note}", file=sys.stderr)
    _disclosed_read_bases.add(note)


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
    return [_locked_unit_json(unit) for unit in lock.artifacts if standard_id in unit.owners]


def managed_markdown_unit_snapshot(lock: CentralLock) -> list[JsonValue]:
    """Return every lock-bound Markdown block across all selected packages."""
    return [
        _locked_unit_json(unit)
        for unit in lock.artifacts
        if unit.adapter is AdapterKind.MARKDOWN_BLOCK
    ]


def _locked_unit_json(unit: LockedUnit) -> JsonValue:
    return {
        "target": unit.path.original,
        "adapter": unit.adapter.value,
        "scope": unit.scope,
        "semantic_digest": unit.semantic_digest.value,
        "content_digest": unit.content_digest.value,
        "mode": unit.mode,
    }


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
    except ControlPlaneError as exc:
        raise CommandResolutionError(
            exc.message,
            path=exc.path,
            line=exc.line,
            column=exc.column,
            locus=exc.locus,
            observed=exc.observed,
            limit=exc.limit,
        ) from exc
    except (PackageContractError, OSError, ValueError) as exc:
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


def resolve_locked_authority(
    state: ControlPlaneState,
    installed: InstalledDistribution,
    standard_id: str,
) -> SelectedCommandPackage | None:
    """Resolve one package from authenticated applied-lock facts, or return None.

    This is the read-only authority (issue #91). Ordinary resolution replays the
    installed catalog, so a consumer whose lock is internally consistent but
    older than the freshly installed tool resolves a *newer* selection than the
    lock records and every read-only command refuses as "not reconciled" —
    exactly at the pre-change inventory the migration runbook prescribes. The
    lock already names the payload the repository is running, so a command that
    only reads can answer from it and leave advancing the selection to
    reconciliation.

    Authority is granted only when the lock authenticates completely: the
    unified config digest still matches the lock, the installed distribution
    still carries the locked version, its verified payload bytes hash to the
    locked payload digest, and the locked options re-resolve to the locked
    effective-config digest under that payload's own schema. Any failure returns
    None rather than raising, so the caller falls through to ordinary resolution
    and the existing refusal — "unified config has not been reconciled",
    "configured package options are invalid", a payload/catalog disagreement —
    stays the single diagnostic for that condition.
    """
    config = state.config
    catalog = state.catalog
    lock = state.lock
    if config is None or catalog is None or lock is None:
        return None
    desired = config.standards.get(standard_id)
    applied = lock.standards.get(standard_id)
    if desired is None or applied is None:
        return None
    if lock.project_standards.config_digest != semantic_digest(config.model_dump(mode="json")):
        return None
    try:
        installed_catalog = installed.load_catalog(
            config.project_standards.catalog,
            recorded_release=catalog.project_standards.release,
        )
    except PackageContractError:
        return None
    payload = installed_catalog.payload_map.get((standard_id, applied.resolved.value))
    if payload is None or payload.integrity.aggregate_digest != applied.payload_digest:
        return None
    try:
        schema = load_option_schema(payload.root, payload.manifest)
        effective = schema.resolve_options(desired.config)
    except PackageContractError:
        return None
    if semantic_digest(cast("JsonValue", effective)) != applied.effective_config_digest:
        return None
    return SelectedCommandPackage(
        state.repo,
        payload,
        applied.resolved,
        effective,
        lock,
        state,
        installed,
    )


def _resolve_catalog_default(
    state: ControlPlaneState,
    installed: InstalledDistribution,
    standard_id: str,
) -> SelectedCommandPackage | None:
    """Resolve the catalog default for a package the repository has not selected.

    This is the pre-enable inventory authority (issue #130). A repository-wide
    read-only inventory — Agent Handoff's `legacy-report` is the whole class —
    answers a question about the *repository*, not about a selection: the
    migration runbook prescribes it before the enable/route decision precisely
    so the evidence can inform that decision. Refusing until the package is
    enabled inverted that order and made a consumer commit to the package to
    see whether adopting it was safe.

    Only the serializer comes from the payload, so the version that formats the
    report is the version `version = "latest"` would resolve to: the catalog
    default for the configured major. Nothing is written, nothing is locked, and
    the basis is disclosed. Any failure to reach that payload returns None so the
    caller falls through to the existing absent-package refusal — the fallback
    must never be a *different* diagnostic for the same broken state.
    """
    config = state.config
    catalog = state.catalog
    lock = state.lock
    if config is None or catalog is None or lock is None:
        return None
    try:
        installed_catalog = installed.load_catalog(
            config.project_standards.catalog,
            recorded_release=catalog.project_standards.release,
        )
    except PackageContractError:
        return None
    default = next(
        (
            entry
            for entry in installed_catalog.source.packages
            if entry.id == standard_id and entry.role is CatalogRole.DEFAULT
        ),
        None,
    )
    if default is None:
        return None
    payload = installed_catalog.payload_map.get((standard_id, default.version.value))
    if payload is None:
        return None
    try:
        schema = load_option_schema(payload.root, payload.manifest)
        effective = schema.resolve_options({})
    except PackageContractError:
        return None
    _disclose_read_basis(
        f"reading the installed catalog default: {standard_id}@{default.version.value}; "
        "the package is not selected in .standards/config.toml, so this report is "
        "repository evidence only and applies nothing"
    )
    return SelectedCommandPackage(
        state.repo,
        payload,
        default.version,
        effective,
        lock,
        state,
        installed,
    )


def _resolve_state(
    state: ControlPlaneState,
    installed: InstalledDistribution,
    standard_id: str,
    explicit_legacy: Path | None,
    *,
    require_reconciled: bool,
    read_authority: bool,
    unselected_inventory: bool = False,
) -> SelectedCommandPackage | None:
    if state.kind is StateKind.LEGACY_ONLY:
        emit_legacy_authority_warning()
        return None
    if state.kind is StateKind.UNINITIALIZED:
        return None
    if state.kind is StateKind.MALFORMED and state.malformed_file == "config.toml":
        raise CommandConfigurationError(
            state.detail or "control-plane config is invalid",
            path=".standards/config.toml",
            line=state.line,
            column=state.column,
        )
    if state.kind is StateKind.MALFORMED:
        raise CommandResolutionError(
            state.detail or "control-plane state is malformed",
            path=(
                f".standards/{state.malformed_file}" if state.malformed_file is not None else None
            ),
            line=state.line,
            column=state.column,
        )
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
        # `read_authority` is the writer test, not a preference: an unselected
        # package owns no lock entry, so nothing could authenticate a write.
        unselected = (
            _resolve_catalog_default(state, installed, standard_id)
            if unselected_inventory and read_authority
            else None
        )
        if unselected is not None:
            return unselected
        raise _CompanionAbsentError(f"package is not present in unified config: {standard_id}")
    if not desired.enabled:
        raise _CompanionAbsentError(f"package is disabled in unified config: {standard_id}")
    # Issue #101: a read-only command may report on the desired selection while
    # the package is enabled but has never been locked. That window is the normal
    # state between `standards enable` and `reconcile --apply`, not a fault, and
    # it is exactly where UPGRADING.md §2 places the size and shape checkpoint:
    # a pre-existing hard-cap violation must be routed to its durable owner
    # before eager state is written, so refusing here put the documented check
    # after the write it exists to prevent. Nothing is applied; the basis is
    # disclosed below. A package that *is* locked keeps its full reconciliation
    # requirement, so an unreconciled config edit still cannot take effect
    # silently over an authenticated basis.
    desired_basis = (
        require_reconciled and read_authority and standard_id not in state.lock.standards
    )
    if require_reconciled and not desired_basis:
        _validate_applied_state(standard_id, state.config, state.catalog, state.lock)
        if read_authority:
            locked = resolve_locked_authority(state, installed, standard_id)
            if locked is not None:
                if state.catalog.project_standards.release != installed.tool_release.value:
                    # Disclose only across a release skew. Same release means the
                    # installed catalog projection is byte-identical to the
                    # committed one (catalog_refresh enforces that lineage), so
                    # the locked basis is also the current one and a note on
                    # every ordinary command would be noise.
                    _disclose_read_basis(
                        f"reading the applied lock: {standard_id}@{locked.resolved.value}; "
                        f"installed release {installed.tool_release.value} is not reconciled "
                        "into this repository yet"
                    )
                return locked
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
    if desired_basis:
        _disclose_read_basis(
            f"reading the not-yet-applied selection: "
            f"{standard_id}@{selected.applied.resolved.value}; "
            "it is enabled but absent from .standards/lock.toml until "
            "project-standards reconcile --apply locks it"
        )
    if require_reconciled and not desired_basis:
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
    read_authority: bool = False,
    unselected_inventory: bool = False,
) -> SelectedCommandPackage | None:
    """Normalize package/config failures at every public command boundary."""
    try:
        return _resolve_state(
            state,
            installed,
            standard_id,
            explicit_legacy,
            require_reconciled=require_reconciled,
            read_authority=read_authority,
            unselected_inventory=unselected_inventory,
        )
    except CommandResolutionError:
        raise
    except ControlPlaneConfigurationError as exc:
        raise CommandConfigurationError(
            exc.message,
            path=exc.path,
            line=exc.line,
            column=exc.column,
            locus=exc.locus,
            observed=exc.observed,
            limit=exc.limit,
        ) from exc
    except ControlPlaneError as exc:
        raise CommandResolutionError(
            exc.message,
            path=exc.path,
            line=exc.line,
            column=exc.column,
            locus=exc.locus,
            observed=exc.observed,
            limit=exc.limit,
        ) from exc
    except (PackageContractError, OSError, ValueError) as exc:
        raise CommandResolutionError(str(exc)) from exc


def resolve_enabled_companion(
    selected: SelectedCommandPackage,
    standard_id: str,
) -> SelectedCommandPackage | None:
    """Resolve another enabled package from the same retained authority generation.

    Companions are dispatched for validation only, so they carry the same
    read authority as the primary: a companion that refused where the primary
    resolved would fail the whole command for a repository the primary just
    proved readable.
    """
    try:
        return _resolve_state_for_command(
            selected.state,
            selected.distribution,
            standard_id,
            None,
            require_reconciled=True,
            read_authority=True,
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
    unselected_inventory: bool = False,
) -> Generator[SelectedCommandPackage | None]:
    """Resolve and retain one authority generation for a complete public command.

    `mode` decides read authority as well as the control-plane lock: a command
    that takes only a read lock is exactly a command that will not write, and
    those may resolve from the applied lock (see `resolve_locked_authority`).
    A writer keeps requiring a fully reconciled selection, because it renders
    repository bytes and must not do so from a superseded basis.

    `unselected_inventory` opts one command into answering for a package the
    repository has not selected (see `_resolve_catalog_default`). It is valid
    only where the answer is derived from repository state rather than from the
    selection, so a caller that reports on managed artifacts must leave it off:
    a package that owns no locked units cannot be conformant or drifted, and
    reporting it as clean would be a false negative, not an inventory.
    """
    installed = distribution or InstalledDistribution.current()
    try:
        initial = detect_control_plane_state(repo, tool_release=installed.tool_release.value)
    except ValueError as exc:
        raise CommandConfigurationError(str(exc)) from exc
    read_authority = mode is LockMode.READ
    if initial.kind is not StateKind.INITIALIZED:
        yield _resolve_state_for_command(
            initial,
            installed,
            standard_id,
            explicit_legacy,
            require_reconciled=require_reconciled,
            read_authority=read_authority,
            unselected_inventory=unselected_inventory,
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
            read_authority=read_authority,
            unselected_inventory=unselected_inventory,
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
    """Resolve unified command facts, or return the bounded legacy fallback state.

    Read authority by construction: this entry point takes no control-plane lock
    and serves the validators, which only report.
    """
    installed = distribution or InstalledDistribution.current()
    state = detect_control_plane_state(repo, tool_release=installed.tool_release.value)
    return _resolve_state_for_command(
        state,
        installed,
        standard_id,
        explicit_legacy,
        require_reconciled=True,
        read_authority=True,
    )
