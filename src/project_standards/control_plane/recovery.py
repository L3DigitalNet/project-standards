"""Plan and explicitly apply sanctioned incomplete-state recovery.

User-owned configuration is never inferred. Catalog bytes come only from the
matching installed distribution, while lock reconstruction starts from empty
applied and authorization partitions and succeeds only when ordinary planning
can prove every selected payload and live artifact unambiguously.
"""

from __future__ import annotations

import hashlib
import os
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from project_standards.control_plane.catalog_refresh import CATALOG_REFRESH_BACKUP
from project_standards.control_plane.codec import (
    parse_catalog,
    parse_config,
    parse_lock,
    render_catalog,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.diagnostics import ControlFinding, ControlPlaneError
from project_standards.control_plane.distribution import (
    InstalledDistribution,
    declared_transitions,
    resolution_payloads,
)
from project_standards.control_plane.executor import (
    ApplyRequest,
    ApplyResult,
    apply_reconciliation,
)
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockedControlDirectory,
    LockMode,
    control_plane_lock,
    is_reserved_temporary_name,
    reserved_temporary_name,
)
from project_standards.control_plane.models import CentralLock, LockHeader
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.resolution import (
    MajorAuthorization,
    ResolutionRequest,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.payload import JsonValue


class RecoveryKind(StrEnum):
    """Sanctioned or refused incomplete-state recovery classes."""

    MISSING_CONFIG = "missing-config"
    MISSING_CATALOG = "missing-catalog"
    MISSING_LOCK = "missing-lock"
    CATALOG_REFRESH = "catalog-refresh"
    UNRECOVERABLE = "unrecoverable"


@dataclass(frozen=True, slots=True)
class RecoveryRequest:
    """Bind an incomplete repository to its trusted installed distribution."""

    repo: Path
    distribution: InstalledDistribution
    allowed_majors: frozenset[MajorAuthorization] = frozenset()


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """Describe one read-only incomplete-state recovery decision."""

    applicable: bool
    kind: RecoveryKind
    findings: tuple[ControlFinding, ...]
    target: str | None = None
    proposed_content: bytes | None = None
    reconciliation: ReconciliationPlan | None = None
    planner: PlannerRequest | None = None
    authority_preconditions: tuple[tuple[str, str], ...] = ()
    cleanup_targets: tuple[str, ...] = ()


def _finding(code: str, message: str, hint: str) -> ControlFinding:
    return ControlFinding(
        code=code,
        severity="error",
        standard_id="project-standards",
        version="",
        path=".standards",
        identity="$recovery",
        message=message,
        hint=hint,
    )


def _refused(kind: RecoveryKind, code: str, message: str, hint: str) -> RecoveryPlan:
    return RecoveryPlan(False, kind, (_finding(code, message, hint),))


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _replace_catalog_atomically(
    control: LockedControlDirectory,
    temporary: str,
    content: bytes,
    *,
    zero_write_message: str,
) -> None:
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=control.descriptor,
    )
    try:
        os.fchmod(descriptor, 0o644)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError(zero_write_message)
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(
        temporary,
        "catalog.toml",
        src_dir_fd=control.descriptor,
        dst_dir_fd=control.descriptor,
    )


def _preconditions(
    control: LockedControlDirectory,
    names: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple((name, _digest(control.read_bytes(name))) for name in names)


def _catalog_recovery(
    request: RecoveryRequest,
    control: LockedControlDirectory,
) -> RecoveryPlan:
    try:
        config = parse_config(control.read_bytes("config.toml"))
        previous = parse_lock(control.read_bytes("lock.toml"))
        request.distribution.load_catalog(
            config.project_standards.catalog,
            recorded_release=previous.project_standards.release,
        )
        catalog = request.distribution.consumer_catalog(config.project_standards.catalog)
    except ValueError, PackageContractError:
        return _refused(
            RecoveryKind.MISSING_CATALOG,
            "CP-RECOVERY-DISTRIBUTION",
            "installed distribution cannot reproduce the missing catalog",
            "restore the matching tool release or catalog from version control",
        )
    if (
        previous.project_standards.catalog != config.project_standards.catalog
        or previous.project_standards.catalog_digest != catalog.project_standards.digest
    ):
        return _refused(
            RecoveryKind.MISSING_CATALOG,
            "CP-RECOVERY-DISTRIBUTION",
            "installed catalog does not match retained control-plane lineage",
            "restore the matching catalog snapshot from version control",
        )
    return RecoveryPlan(
        True,
        RecoveryKind.MISSING_CATALOG,
        (),
        target=".standards/catalog.toml",
        proposed_content=render_catalog(catalog),
        authority_preconditions=_preconditions(control, ("config.toml", "lock.toml")),
    )


def _lock_recovery(
    request: RecoveryRequest,
    control: LockedControlDirectory,
) -> RecoveryPlan:
    try:
        config = parse_config(control.read_bytes("config.toml"))
        catalog = parse_catalog(control.read_bytes("catalog.toml"))
        installed = request.distribution.load_catalog(
            config.project_standards.catalog,
            recorded_release=catalog.project_standards.release,
        )
        expected_catalog = request.distribution.consumer_catalog(config.project_standards.catalog)
        if catalog != expected_catalog:
            raise ControlPlaneError("catalog does not match installed distribution")
        empty_lock = CentralLock(
            project_standards=LockHeader(
                schema_version="1.1",
                catalog=catalog.project_standards.catalog,
                release=catalog.project_standards.release,
                catalog_digest=catalog.project_standards.digest,
                config_digest=semantic_digest(cast(JsonValue, config.model_dump(mode="json"))),
            ),
        )
        resolution = ResolutionRequest(
            desired=config,
            catalog=catalog,
            previous_lock=empty_lock,
            allowed_majors=request.allowed_majors,
            payloads=resolution_payloads(installed),
            transition_paths=declared_transitions(installed),
        )
        planner = PlannerRequest(request.repo, resolution, installed.payloads)
        reconciliation = plan_reconciliation(planner)
    except ValueError, PackageContractError, ControlPlaneError:
        return _refused(
            RecoveryKind.MISSING_LOCK,
            "CP-RECOVERY-AUTH",
            "missing lock cannot be reconstructed from current evidence",
            "restore the lock or supply required candidate authorization",
        )
    if not reconciliation.applicable:
        return RecoveryPlan(
            False,
            RecoveryKind.MISSING_LOCK,
            reconciliation.findings,
            reconciliation=reconciliation,
            planner=planner,
            authority_preconditions=_preconditions(
                control,
                ("config.toml", "catalog.toml"),
            ),
        )
    return RecoveryPlan(
        True,
        RecoveryKind.MISSING_LOCK,
        (),
        target=".standards/lock.toml",
        proposed_content=render_lock(reconciliation.next_lock),
        reconciliation=reconciliation,
        planner=planner,
        authority_preconditions=_preconditions(control, ("config.toml", "catalog.toml")),
    )


def _catalog_refresh_recovery(
    control: LockedControlDirectory,
) -> RecoveryPlan:
    try:
        config = parse_config(control.read_bytes("config.toml"))
        catalog = parse_catalog(control.read_bytes("catalog.toml"))
        previous = parse_catalog(control.read_bytes(CATALOG_REFRESH_BACKUP))
        lock = parse_lock(control.read_bytes("lock.toml"))
    except ValueError:
        return _refused(
            RecoveryKind.CATALOG_REFRESH,
            "CP-RECOVERY-CATALOG-REFRESH",
            "catalog refresh recovery evidence is invalid",
            "restore catalog and lock authorities from version control",
        )
    majors = {
        config.project_standards.catalog,
        catalog.project_standards.catalog,
        previous.project_standards.catalog,
        lock.project_standards.catalog,
    }
    if len(majors) != 1:
        return _refused(
            RecoveryKind.CATALOG_REFRESH,
            "CP-RECOVERY-CATALOG-REFRESH",
            "catalog refresh recovery evidence disagrees on catalog major",
            "restore matching catalog and lock authorities from version control",
        )
    lock_lineage = (
        lock.project_standards.release,
        lock.project_standards.catalog_digest,
    )
    current_lineage = (
        catalog.project_standards.release,
        catalog.project_standards.digest,
    )
    previous_lineage = (
        previous.project_standards.release,
        previous.project_standards.digest,
    )
    # Enumerate through the locked directory descriptor. Path.iterdir() would
    # reopen the pathname and lose the rename-race protection held by recovery.
    names = os.listdir(control.descriptor)  # noqa: PTH208
    temporaries = tuple(
        sorted(
            name
            for name in names
            if is_reserved_temporary_name(name) and control.file_kind(name) == "regular"
        )
    )
    preconditions = _preconditions(
        control,
        (
            "config.toml",
            "catalog.toml",
            "lock.toml",
            CATALOG_REFRESH_BACKUP,
            *temporaries,
        ),
    )
    cleanup = (*temporaries, CATALOG_REFRESH_BACKUP)
    if current_lineage == lock_lineage:
        return RecoveryPlan(
            True,
            RecoveryKind.CATALOG_REFRESH,
            (),
            target=f".standards/{CATALOG_REFRESH_BACKUP}",
            authority_preconditions=preconditions,
            cleanup_targets=cleanup,
        )
    if previous_lineage == lock_lineage:
        return RecoveryPlan(
            True,
            RecoveryKind.CATALOG_REFRESH,
            (),
            target=".standards/catalog.toml",
            proposed_content=render_catalog(previous),
            authority_preconditions=preconditions,
            cleanup_targets=cleanup,
        )
    return _refused(
        RecoveryKind.CATALOG_REFRESH,
        "CP-RECOVERY-CATALOG-REFRESH",
        "neither live nor backed-up catalog matches retained lock lineage",
        "restore matching catalog and lock authorities from version control",
    )


def _plan_locked(
    request: RecoveryRequest,
    control: LockedControlDirectory,
) -> RecoveryPlan:
    backup_kind = control.file_kind(CATALOG_REFRESH_BACKUP)
    if backup_kind == "unsafe":
        return _refused(
            RecoveryKind.UNRECOVERABLE,
            "CP-RECOVERY-UNSAFE",
            "catalog refresh backup is unsafe",
            "restore safe control-plane files from version control",
        )
    if backup_kind == "regular":
        return _catalog_refresh_recovery(control)
    kinds = {name: control.file_kind(name) for name in ("config.toml", "catalog.toml", "lock.toml")}
    if "unsafe" in kinds.values():
        return _refused(
            RecoveryKind.UNRECOVERABLE,
            "CP-RECOVERY-UNSAFE",
            "control plane contains an unsafe required-file entry",
            "restore safe regular files from version control",
        )
    missing = tuple(name for name, kind in kinds.items() if kind == "missing")
    if "config.toml" in missing:
        return _refused(
            RecoveryKind.MISSING_CONFIG,
            "CP-MISSING-CONFIG",
            "user-owned desired configuration is missing",
            "restore config.toml or run an explicit legacy migration",
        )
    if len(missing) != 1:
        return _refused(
            RecoveryKind.UNRECOVERABLE,
            "CP-RECOVERY-INCOMPLETE",
            "control plane does not have one sanctioned missing-file case",
            "restore the incomplete authorities from version control",
        )
    if missing[0] == "catalog.toml":
        return _catalog_recovery(request, control)
    if missing[0] == "lock.toml":
        return _lock_recovery(request, control)
    return _refused(
        RecoveryKind.UNRECOVERABLE,
        "CP-RECOVERY-INCOMPLETE",
        "control plane recovery case is unsupported",
        "restore the missing authority from version control",
    )


def plan_recovery(request: RecoveryRequest) -> RecoveryPlan:
    """Plan recovery under a shared lock without writing any repository path."""
    try:
        with control_plane_lock(request.repo, LockMode.READ) as control:
            return _plan_locked(request, control)
    except ControlPlaneBusyError as exc:
        return _refused(
            RecoveryKind.UNRECOVERABLE,
            exc.code,
            str(exc),
            "retry after the concurrent standards operation completes",
        )
    except ValueError, OSError:
        return _refused(
            RecoveryKind.UNRECOVERABLE,
            "CP-RECOVERY-UNSAFE",
            "control-plane directory could not be inspected safely",
            "restore a regular .standards directory",
        )


def _publish_catalog(
    request: RecoveryRequest,
    plan: RecoveryPlan,
) -> ApplyResult:
    content = plan.proposed_content
    if content is None:
        return ApplyResult(False, (), False, "CP-RECOVERY-INCOMPLETE")
    applied: list[str] = []
    try:
        with control_plane_lock(request.repo, LockMode.WRITE) as control:
            if control.file_kind("catalog.toml") != "missing":
                return ApplyResult(False, (), False, "CP-STALE-PLAN")
            for name, expected in plan.authority_preconditions:
                if (
                    control.file_kind(name) != "regular"
                    or _digest(control.read_bytes(name)) != expected
                ):
                    return ApplyResult(False, (), False, "CP-STALE-PLAN")
            temporary = reserved_temporary_name()
            try:
                _replace_catalog_atomically(
                    control,
                    temporary,
                    content,
                    zero_write_message="zero-byte catalog write",
                )
                applied.append(".standards/catalog.toml")
                os.fsync(control.descriptor)
            finally:
                with suppress(OSError):
                    os.unlink(temporary, dir_fd=control.descriptor)
            return ApplyResult(True, tuple(applied), False)
    except ControlPlaneBusyError:
        return ApplyResult(False, (), False, "CP-BUSY")
    except ValueError, OSError:
        return ApplyResult(False, tuple(applied), False, "CP-RECOVERY-APPLY")


def _publish_catalog_refresh_recovery(
    request: RecoveryRequest,
    plan: RecoveryPlan,
) -> ApplyResult:
    cleanup = plan.cleanup_targets
    if CATALOG_REFRESH_BACKUP not in cleanup:
        return ApplyResult(False, (), False, "CP-RECOVERY-INCOMPLETE")
    applied: list[str] = []
    try:
        with control_plane_lock(request.repo, LockMode.WRITE) as control:
            for name, expected in plan.authority_preconditions:
                if (
                    control.file_kind(name) != "regular"
                    or _digest(control.read_bytes(name)) != expected
                ):
                    return ApplyResult(False, (), False, "CP-STALE-PLAN")
            temporary: str | None = None
            try:
                if plan.proposed_content is not None:
                    temporary = reserved_temporary_name()
                    _replace_catalog_atomically(
                        control,
                        temporary,
                        plan.proposed_content,
                        zero_write_message="zero-byte catalog recovery write",
                    )
                    applied.append(".standards/catalog.toml")
                    temporary = None
                    os.fsync(control.descriptor)
                for name in cleanup:
                    os.unlink(name, dir_fd=control.descriptor)
                    applied.append(f"remove:.standards/{name}")
                os.fsync(control.descriptor)
            finally:
                if temporary is not None:
                    with suppress(OSError):
                        os.unlink(temporary, dir_fd=control.descriptor)
            return ApplyResult(True, tuple(applied), False)
    except ControlPlaneBusyError:
        return ApplyResult(False, (), False, "CP-BUSY")
    except ValueError, OSError:
        return ApplyResult(False, tuple(applied), False, "CP-RECOVERY-APPLY")


def apply_recovery(
    request: RecoveryRequest,
    plan: RecoveryPlan,
    *,
    apply: bool,
    repair_state: bool,
) -> ApplyResult:
    """Apply a current recovery plan only with both explicit authorizations."""
    if not apply or not repair_state:
        return ApplyResult(False, (), False, "CP-REPAIR-AUTH")
    if not plan.applicable:
        code = plan.findings[0].code if plan.findings else "CP-RECOVERY-INCOMPLETE"
        return ApplyResult(False, (), False, code)
    if plan.kind is RecoveryKind.MISSING_CATALOG:
        return _publish_catalog(request, plan)
    if plan.kind is RecoveryKind.CATALOG_REFRESH:
        return _publish_catalog_refresh_recovery(request, plan)
    if (
        plan.kind is RecoveryKind.MISSING_LOCK
        and plan.planner is not None
        and plan.reconciliation is not None
    ):
        return apply_reconciliation(
            ApplyRequest(
                planner=plan.planner,
                expected_plan=plan.reconciliation,
                missing_lock_repair=True,
                authority_preconditions=plan.authority_preconditions,
            )
        )
    return ApplyResult(False, (), False, "CP-RECOVERY-INCOMPLETE")
