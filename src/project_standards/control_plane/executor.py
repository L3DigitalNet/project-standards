"""Apply reviewed reconciliation plans through the sole repository writer.

Every artifact is staged before the first publication. The previous central
lock remains authoritative until all target replacements and read-only
verification providers succeed; only then is the staged lock published.
Failures deliberately leave any already-published artifact prefix visible so
the next planner can classify and repair the incomplete transition.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from project_standards.control_plane.catalog_refresh import CATALOG_REFRESH_BACKUP
from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlAction,
    ControlFinding,
    ControlPlaneError,
    sort_findings,
)
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockedControlDirectory,
    LockMode,
    control_plane_lock,
)
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
)
from project_standards.control_plane.schemas import MutationPlanSchema
from project_standards.control_plane.snapshot import (
    EntryKind,
    RepositorySnapshot,
    SnapshotEntry,
)
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderEffect,
    ProviderOperation,
)

if TYPE_CHECKING:
    from project_standards.control_plane.migration import LegacyMigrationPlan

type FaultHook = Callable[[str, str], None]
type VerificationRunner = Callable[[ProviderInvocation], ProviderResult]

_MUTATING_ACTIONS = frozenset({ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE})


@dataclass(frozen=True, slots=True)
class ApplyRequest:
    """Bind the inputs and reviewed plan authorized for one apply attempt."""

    planner: PlannerRequest
    expected_plan: ReconciliationPlan
    fault_hook: FaultHook | None = None
    verification_runner: VerificationRunner | None = None
    missing_lock_repair: bool = False
    authority_preconditions: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ApplyResult:
    """Report the exact mutation prefix completed by one apply attempt."""

    success: bool
    applied_action_ids: tuple[str, ...]
    lock_written: bool
    error_code: str | None = None
    verification_findings: tuple[ControlFinding, ...] = ()


@dataclass(frozen=True, slots=True)
class AuthoringApplyResult:
    """Report the exact target prefix completed by one authoring plan."""

    success: bool
    applied_targets: tuple[str, ...]
    error_code: str | None = None


@dataclass(slots=True)
class _StagedTarget:
    target: str
    source_descriptor: int
    parent_descriptor: int
    temporary: str
    destination: str


class _ApplyFailure(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        findings: tuple[ControlFinding, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.findings = findings


def _fault(request: ApplyRequest, phase: str, identity: str) -> None:
    if request.fault_hook is not None:
        request.fault_hook(phase, identity)


def reconciliation_fingerprint(plan: ReconciliationPlan) -> str:
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            plan.to_jsonable(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    )
    for target in plan.targets:
        digest.update(target.target.encode("utf-8"))
        digest.update(b"\0")
        digest.update((target.mode or "").encode("ascii"))
        digest.update(b"\0")
        digest.update(target.content)
        digest.update(b"\n")
    return digest.hexdigest()


def _open_repository(repo: Path) -> tuple[Path, int]:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise _ApplyFailure("CP-APPLY-PATH", "repository root is unsafe")
        root = repo.resolve(strict=True)
        descriptor = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
    except OSError as exc:
        raise _ApplyFailure("CP-APPLY-PATH", "repository root could not be opened") from exc
    return root, descriptor


def _open_parent(
    root_descriptor: int,
    parent: PurePosixPath,
    created: list[PurePosixPath],
) -> int:
    descriptor = os.dup(root_descriptor)
    traversed = PurePosixPath()
    try:
        for part in parent.parts:
            traversed /= part
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                try:
                    os.mkdir(part, mode=0o755, dir_fd=descriptor)
                    created.append(traversed)
                    child = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=descriptor,
                    )
                except OSError as exc:
                    raise _ApplyFailure(
                        "CP-APPLY-PATH",
                        "target parent could not be created safely",
                    ) from exc
            except OSError as exc:
                raise _ApplyFailure(
                    "CP-APPLY-PATH",
                    "target parent is not a safe directory",
                ) from exc
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _stage_bytes(
    parent_descriptor: int,
    destination: str,
    content: bytes,
    mode: str | None,
) -> str:
    temporary = f".project-standards-{secrets.token_hex(8)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(temporary, flags, 0o600, dir_fd=parent_descriptor)
    except OSError as exc:
        raise _ApplyFailure("CP-APPLY-STAGE", "target could not be staged") from exc
    try:
        os.fchmod(descriptor, int(mode or "0644", 8))
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError("zero-byte staged write")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except BaseException as exc:
        os.close(descriptor)
        with suppress(OSError):
            os.unlink(temporary, dir_fd=parent_descriptor)
        if isinstance(exc, _ApplyFailure):
            raise
        raise _ApplyFailure("CP-APPLY-STAGE", "target bytes could not be staged") from exc
    os.close(descriptor)
    return temporary


def _stage_targets(
    request: ApplyRequest,
    plan: ReconciliationPlan,
    root_descriptor: int,
    created: list[PurePosixPath],
    *,
    staging_descriptor: int | None = None,
) -> dict[str, _StagedTarget]:
    targets = {target.target: target for target in plan.targets}
    staged: dict[str, _StagedTarget] = {}
    for action in plan.actions:
        if action.kind not in {ActionKind.CREATE, ActionKind.UPDATE}:
            continue
        _fault(request, "stage", action.target)
        relative = SafeRelativePath.parse(action.target)
        parent_descriptor = _open_parent(root_descriptor, relative.normalized.parent, created)
        source_descriptor = (
            staging_descriptor if staging_descriptor is not None else parent_descriptor
        )
        target = targets[action.target]
        try:
            if os.fstat(source_descriptor).st_dev != os.fstat(parent_descriptor).st_dev:
                raise _ApplyFailure(
                    "CP-APPLY-STAGE",
                    "catalog refresh targets must share the control-plane filesystem",
                )
            temporary = _stage_bytes(
                source_descriptor,
                relative.normalized.name,
                target.content,
                target.mode,
            )
        except BaseException:
            os.close(parent_descriptor)
            raise
        staged[action.target] = _StagedTarget(
            action.target,
            source_descriptor,
            parent_descriptor,
            temporary,
            relative.normalized.name,
        )
    return staged


def _cleanup_staged(
    staged: dict[str, _StagedTarget],
    root: Path,
    created: list[PurePosixPath],
) -> None:
    for item in staged.values():
        with suppress(OSError):
            os.unlink(item.temporary, dir_fd=item.source_descriptor)
        with suppress(OSError):
            os.close(item.parent_descriptor)
    for relative in sorted(created, key=lambda item: len(item.parts), reverse=True):
        with suppress(OSError):
            (root / relative).rmdir()


def _authoring_entries(
    repo: Path,
    plan: MutationPlanSchema,
) -> dict[str, SnapshotEntry]:
    targets = tuple(action.target for action in plan.actions)
    if len(targets) != len(set(targets)):
        raise _ApplyFailure("CP-AUTHORING-PLAN", "authoring plan repeats a target")
    if any(
        action.adapter.value != "whole-file" or action.scope != "$file" for action in plan.actions
    ):
        raise _ApplyFailure(
            "CP-AUTHORING-PLAN",
            "authoring executor requires complete whole-file actions",
        )
    snapshot = RepositorySnapshot.capture(repo, targets)
    entries = {entry.path.original: entry for entry in snapshot.entries}
    for action in plan.actions:
        entry = entries[action.target.original]
        if entry.precondition_digest != action.precondition_digest:
            raise _ApplyFailure("CP-PRECONDITION", "authoring target changed after planning")
        if action.kind is ActionKind.CREATE and entry.kind is not EntryKind.MISSING:
            raise _ApplyFailure("CP-PRECONDITION", "authoring create target already exists")
        if (
            action.kind in {ActionKind.UPDATE, ActionKind.REMOVE}
            and entry.kind is not EntryKind.REGULAR
        ):
            raise _ApplyFailure("CP-PRECONDITION", "authoring target is not a regular file")
    return entries


def apply_authoring_plan(repo: Path, plan: MutationPlanSchema) -> AuthoringApplyResult:
    """Apply one complete provider plan through contained, preconditioned replacements."""
    applied: list[str] = []
    staged: dict[str, _StagedTarget] = {}
    created: list[PurePosixPath] = []
    root: Path | None = None
    root_descriptor: int | None = None
    try:
        root, root_descriptor = _open_repository(repo)
        entries = _authoring_entries(root, plan)
        for action in plan.actions:
            if action.kind is ActionKind.REMOVE:
                continue
            relative = action.target
            parent_descriptor = _open_parent(
                root_descriptor,
                relative.normalized.parent,
                created,
            )
            entry = entries[relative.original]
            mode = action.mode or entry.mode or "0644"
            try:
                temporary = _stage_bytes(
                    parent_descriptor,
                    relative.normalized.name,
                    action.content_bytes or b"",
                    mode,
                )
            except BaseException:
                os.close(parent_descriptor)
                raise
            staged[relative.original] = _StagedTarget(
                relative.original,
                parent_descriptor,
                parent_descriptor,
                temporary,
                relative.normalized.name,
            )

        # All target snapshots are rechecked before the first publication, so a
        # stale action cannot leave an earlier action applied as a partial fix.
        _authoring_entries(root, plan)
        for action in plan.actions:
            relative = action.target
            item = staged.get(relative.original)
            if item is not None:
                _assert_parent_current(root, relative.normalized.parent, item.parent_descriptor)
            if action.kind is ActionKind.REMOVE:
                parent_descriptor = _open_parent(
                    root_descriptor,
                    relative.normalized.parent,
                    [],
                )
                try:
                    os.unlink(relative.normalized.name, dir_fd=parent_descriptor)
                    os.fsync(parent_descriptor)
                except OSError as exc:
                    raise _ApplyFailure(
                        "CP-AUTHORING-PUBLISH",
                        "authoring target removal failed",
                    ) from exc
                finally:
                    os.close(parent_descriptor)
            else:
                if item is None:
                    raise _ApplyFailure(
                        "CP-AUTHORING-PLAN",
                        "authoring replacement was not staged",
                    )
                try:
                    os.replace(
                        item.temporary,
                        item.destination,
                        src_dir_fd=item.source_descriptor,
                        dst_dir_fd=item.parent_descriptor,
                    )
                    os.fsync(item.parent_descriptor)
                except OSError as exc:
                    raise _ApplyFailure(
                        "CP-AUTHORING-PUBLISH",
                        "authoring target replacement failed",
                    ) from exc
            applied.append(relative.original)
        return AuthoringApplyResult(True, tuple(applied))
    except _ApplyFailure as exc:
        return AuthoringApplyResult(False, tuple(applied), exc.code)
    except ControlPlaneError, OSError, ValueError:
        return AuthoringApplyResult(False, tuple(applied), "CP-AUTHORING-PLAN")
    finally:
        if root is not None:
            _cleanup_staged(staged, root, created)
        if root_descriptor is not None:
            os.close(root_descriptor)


def _precondition(plan: ReconciliationPlan, target: str) -> str:
    for item in plan.preconditions:
        if item.target == target:
            return item.digest
    raise _ApplyFailure("CP-STALE-PLAN", "plan omitted a target precondition")


def _assert_precondition(repo: Path, plan: ReconciliationPlan, target: str) -> None:
    relative = SafeRelativePath.parse(target)
    observed = RepositorySnapshot.capture(repo, (relative,)).entry(relative)
    if observed.precondition_digest.value != _precondition(plan, target):
        raise _ApplyFailure("CP-PRECONDITION", "target changed after planning")


def _assert_parent_current(
    repo: Path,
    parent: PurePosixPath,
    descriptor: int,
) -> None:
    try:
        opened = os.fstat(descriptor)
        current = (repo / parent).stat(follow_symlinks=False)
    except OSError as exc:
        raise _ApplyFailure("CP-PRECONDITION", "target parent changed after staging") from exc
    if (
        not stat.S_ISDIR(current.st_mode)
        or opened.st_dev != current.st_dev
        or opened.st_ino != current.st_ino
    ):
        raise _ApplyFailure("CP-PRECONDITION", "target parent changed after staging")


def _publish_targets(
    request: ApplyRequest,
    plan: ReconciliationPlan,
    staged: dict[str, _StagedTarget],
    applied: list[str],
    root_descriptor: int,
) -> None:
    for action in plan.actions:
        if action.kind not in _MUTATING_ACTIONS:
            continue
        _fault(request, "precondition", action.target)
        _assert_precondition(request.planner.repo, plan, action.target)
        if action.target in staged:
            _assert_parent_current(
                request.planner.repo,
                SafeRelativePath.parse(action.target).normalized.parent,
                staged[action.target].parent_descriptor,
            )
        _fault(request, "publish", action.target)
        relative = SafeRelativePath.parse(action.target)
        if action.kind is ActionKind.REMOVE:
            parent = _open_parent(
                root_descriptor,
                relative.normalized.parent,
                [],
            )
            try:
                os.unlink(relative.normalized.name, dir_fd=parent)
                os.fsync(parent)
            except OSError as exc:
                raise _ApplyFailure("CP-APPLY-PUBLISH", "target removal failed") from exc
            finally:
                os.close(parent)
        else:
            item = staged[action.target]
            try:
                os.replace(
                    item.temporary,
                    item.destination,
                    src_dir_fd=item.source_descriptor,
                    dst_dir_fd=item.parent_descriptor,
                )
                os.fsync(item.parent_descriptor)
            except OSError as exc:
                raise _ApplyFailure("CP-APPLY-PUBLISH", "target replacement failed") from exc
        applied.append(action.target)
        _fault(request, "published", action.target)
    for namespace in plan.namespace_prunes:
        path = request.planner.repo / namespace
        try:
            for directory in sorted(path.rglob("*"), reverse=True):
                if directory.is_dir():
                    directory.rmdir()
            path.rmdir()
        except OSError as exc:
            raise _ApplyFailure("CP-APPLY-PUBLISH", "namespace pruning failed") from exc
        applied.append(f"prune:{namespace}")


def _verification_snapshot(
    repo: Path,
    plan: ReconciliationPlan,
    standard_id: str,
) -> JsonObject:
    targets = tuple(SafeRelativePath.parse(item.target) for item in plan.preconditions)
    snapshot = RepositorySnapshot.capture(repo, targets)
    result: JsonObject = {
        entry.path.original: {
            "kind": entry.kind.value,
            "content_digest": entry.content_digest.value if entry.content_digest else None,
            "mode": entry.mode,
        }
        for entry in snapshot.entries
    }
    result["referenced_inputs"] = [
        {
            "standard_id": item.standard_id,
            "extension_id": item.extension_id,
            "path": item.path.original,
            "digest": item.digest.value,
        }
        for item in plan.next_lock.referenced_inputs
        if item.standard_id == standard_id
    ]
    return result


def _selected_payloads(request: ApplyRequest) -> dict[tuple[str, str], InstalledPayload]:
    return {
        (payload.manifest.payload.standard, payload.manifest.payload.version.value): payload
        for payload in request.planner.payloads
    }


def _verify(
    request: ApplyRequest,
    plan: ReconciliationPlan,
) -> tuple[ControlFinding, ...]:
    if not plan.verification_requests:
        return ()
    runner = request.verification_runner or invoke_provider
    packages = {item.standard_id: item for item in plan.resolution.packages}
    payloads = _selected_payloads(request)
    findings: list[ControlFinding] = []
    for verification in plan.verification_requests:
        package = packages[verification.standard_id]
        payload = payloads[(verification.standard_id, verification.version)]
        try:
            _fault(request, "verify", verification.provider_id)
            result = runner(
                ProviderInvocation(
                    repo=request.planner.repo,
                    payload=payload,
                    standard_id=verification.standard_id,
                    version=package.applied.resolved,
                    provider_id=verification.provider_id,
                    operation=ProviderOperation.VERIFY,
                    effective_config=package.effective_config,
                    snapshots=_verification_snapshot(
                        request.planner.repo,
                        plan,
                        verification.standard_id,
                    ),
                )
            )
        except BaseException as exc:
            raise _ApplyFailure("CP-VERIFY", "verification provider failed") from exc
        if result.effect is not ProviderEffect.FINDINGS:
            raise _ApplyFailure("CP-VERIFY", "verification provider returned wrong effect")
        findings.extend(result.findings)
    ordered = tuple(sort_findings(findings))
    if any(finding.severity == "error" for finding in ordered):
        raise _ApplyFailure(
            "CP-VERIFY",
            "post-apply verification reported an error",
            findings=ordered,
        )
    return ordered


def _restore_catalog_before_lock(
    control: LockedControlDirectory,
    backup: str,
    committed: bytes,
    applied: list[str],
) -> None:
    """Restore committed catalog authority after a handled pre-lock failure."""
    if (
        control.file_kind("catalog.toml") == "regular"
        and control.read_bytes("catalog.toml") == committed
    ):
        with suppress(OSError):
            os.unlink(backup, dir_fd=control.descriptor)
        return
    try:
        os.replace(
            backup,
            "catalog.toml",
            src_dir_fd=control.descriptor,
            dst_dir_fd=control.descriptor,
        )
        os.fsync(control.descriptor)
    except OSError as exc:
        raise _ApplyFailure(
            "CP-CATALOG-ROLLBACK",
            "committed catalog could not be restored after apply failure",
        ) from exc
    with suppress(ValueError):
        applied.remove(".standards/catalog.toml")


def _apply_locked(
    request: ApplyRequest,
    control: LockedControlDirectory,
) -> ApplyResult:
    applied: list[str] = []
    verification_findings: tuple[ControlFinding, ...] = ()
    staged: dict[str, _StagedTarget] = {}
    created: list[PurePosixPath] = []
    catalog_backup_temporary: str | None = None
    catalog_backup_published = False
    committed_catalog: bytes | None = None
    lock_published = False
    root, root_descriptor = _open_repository(request.planner.repo)
    try:
        expected_lock = render_lock(request.planner.resolution.previous_lock)
        lock_kind = control.file_kind("lock.toml")
        if request.missing_lock_repair:
            if lock_kind != "missing":
                return ApplyResult(False, (), False, "CP-STALE-PLAN")
            live_lock: bytes | None = None
        else:
            if lock_kind != "regular" or control.read_bytes("lock.toml") != expected_lock:
                return ApplyResult(False, (), False, "CP-STALE-PLAN")
            live_lock = expected_lock
        for name, expected_digest in request.authority_preconditions:
            if control.file_kind(name) != "regular":
                return ApplyResult(False, (), False, "CP-STALE-PLAN")
            actual = hashlib.sha256(control.read_bytes(name)).hexdigest()
            if actual != expected_digest:
                return ApplyResult(False, (), False, "CP-STALE-PLAN")
        current = plan_reconciliation(request.planner)
        if (
            not request.expected_plan.applicable
            or not current.applicable
            or reconciliation_fingerprint(current)
            != reconciliation_fingerprint(request.expected_plan)
        ):
            return ApplyResult(False, (), False, "CP-STALE-PLAN")
        plan = current
        new_lock = render_lock(plan.next_lock)
        lock_changed = live_lock != new_lock
        lock_temporary: str | None = None
        try:
            refresh = plan.catalog_refresh
            if refresh is not None and refresh.changed:
                if control.file_kind(CATALOG_REFRESH_BACKUP) != "missing":
                    raise _ApplyFailure(
                        "CP-STALE-PLAN",
                        "catalog refresh recovery evidence already exists",
                    )
                committed_catalog = control.read_bytes("catalog.toml")
                catalog_backup_temporary = _stage_bytes(
                    control.descriptor,
                    "catalog.toml",
                    committed_catalog,
                    "0644",
                )
                _fault(
                    request,
                    "publish",
                    f".standards/{CATALOG_REFRESH_BACKUP}",
                )
                os.replace(
                    catalog_backup_temporary,
                    CATALOG_REFRESH_BACKUP,
                    src_dir_fd=control.descriptor,
                    dst_dir_fd=control.descriptor,
                )
                os.fsync(control.descriptor)
                catalog_backup_temporary = None
                catalog_backup_published = True
                _fault(
                    request,
                    "published",
                    f".standards/{CATALOG_REFRESH_BACKUP}",
                )
            lock_temporary = (
                _stage_bytes(control.descriptor, "lock.toml", new_lock, "0644")
                if lock_changed
                else None
            )
            staged = _stage_targets(
                request,
                plan,
                root_descriptor,
                created,
                staging_descriptor=(
                    control.descriptor if refresh is not None and refresh.changed else None
                ),
            )
            _publish_targets(request, plan, staged, applied, root_descriptor)
            verification_findings = _verify(request, plan)
            if lock_temporary is not None:
                _fault(request, "lock", ".standards/lock.toml")
                if request.missing_lock_repair:
                    lock_current = control.file_kind("lock.toml") == "missing"
                else:
                    lock_current = control.read_bytes("lock.toml") == expected_lock
                if not lock_current or not control.is_current():
                    raise _ApplyFailure("CP-PRECONDITION", "central lock changed during apply")
                os.replace(
                    lock_temporary,
                    "lock.toml",
                    src_dir_fd=control.descriptor,
                    dst_dir_fd=control.descriptor,
                )
                os.fsync(control.descriptor)
                lock_published = True
                lock_temporary = None
                _fault(request, "published", ".standards/lock.toml")
            return ApplyResult(
                True,
                tuple(applied),
                lock_changed,
                verification_findings=verification_findings,
            )
        except _ApplyFailure as exc:
            if not lock_published and catalog_backup_published and committed_catalog is not None:
                try:
                    _restore_catalog_before_lock(
                        control,
                        CATALOG_REFRESH_BACKUP,
                        committed_catalog,
                        applied,
                    )
                    catalog_backup_published = False
                except _ApplyFailure as rollback:
                    return ApplyResult(
                        False,
                        tuple(applied),
                        False,
                        rollback.code,
                        exc.findings or verification_findings,
                    )
            return ApplyResult(
                False,
                tuple(applied),
                lock_published,
                exc.code,
                exc.findings or verification_findings,
            )
        except BaseException:
            if not lock_published and catalog_backup_published and committed_catalog is not None:
                try:
                    _restore_catalog_before_lock(
                        control,
                        CATALOG_REFRESH_BACKUP,
                        committed_catalog,
                        applied,
                    )
                    catalog_backup_published = False
                except _ApplyFailure as rollback:
                    return ApplyResult(False, tuple(applied), False, rollback.code)
            return ApplyResult(
                False,
                tuple(applied),
                lock_published,
                "CP-APPLY-FAILED",
            )
        finally:
            if lock_temporary is not None:
                with suppress(OSError):
                    os.unlink(lock_temporary, dir_fd=control.descriptor)
            if catalog_backup_temporary is not None:
                with suppress(OSError):
                    os.unlink(catalog_backup_temporary, dir_fd=control.descriptor)
            if lock_published and catalog_backup_published:
                with suppress(OSError):
                    os.unlink(CATALOG_REFRESH_BACKUP, dir_fd=control.descriptor)
                    os.fsync(control.descriptor)
    finally:
        os.close(root_descriptor)
        _cleanup_staged(staged, root, created)


def apply_reconciliation(request: ApplyRequest) -> ApplyResult:
    """Apply one reviewed plan exactly once under the exclusive control lock."""
    try:
        with control_plane_lock(request.planner.repo, LockMode.WRITE) as control:
            return _apply_locked(request, control)
    except ControlPlaneBusyError:
        return ApplyResult(False, (), False, "CP-BUSY")
    except (_ApplyFailure, ControlPlaneError, ValueError, OSError) as exc:
        code = exc.code if isinstance(exc, _ApplyFailure) else "CP-APPLY-FAILED"
        return ApplyResult(False, (), False, code)


def _migration_plan_current(plan: LegacyMigrationPlan) -> bool:
    from project_standards.control_plane.migration import (
        legacy_migration_content_fingerprint,
        plan_legacy_migration,
    )

    if plan.repo != plan.planner.repo or not plan.applicable:
        return False
    if plan.reconciliation_fingerprint != reconciliation_fingerprint(plan.reconciliation):
        return False
    if plan.content_fingerprint != legacy_migration_content_fingerprint(
        plan.repo,
        plan.reconciliation_fingerprint,
        plan.legacy_preconditions,
        plan.config_content,
        plan.catalog_content,
        plan.lock_content,
    ):
        return False
    try:
        if plan.repo.resolve(strict=True) != plan.repo:
            return False
        installed = plan.distribution.load_catalog(
            plan.catalog.project_standards.catalog,
        )
        if (
            plan.distribution.consumer_catalog(plan.catalog.project_standards.catalog)
            != plan.catalog
        ):
            return False
    except ControlPlaneError, OSError, ValueError:
        return False
    expected_lineage = tuple(
        (
            payload.manifest.payload.standard,
            payload.manifest.payload.version.value,
            payload.integrity.aggregate_digest.value,
        )
        for payload in plan.planner.payloads
    )
    installed_lineage = tuple(
        (
            payload.manifest.payload.standard,
            payload.manifest.payload.version.value,
            payload.integrity.aggregate_digest.value,
        )
        for payload in installed.payloads
    )
    if installed_lineage != expected_lineage:
        return False
    if (plan.repo / ".standards").exists() or (plan.repo / ".standards").is_symlink():
        return True
    try:
        current = plan_legacy_migration(
            plan.repo,
            plan.distribution,
            plan.catalog.project_standards.catalog,
        )
    except ControlPlaneError, OSError, ValueError:
        return False
    current_lineage = tuple(
        (
            payload.manifest.payload.standard,
            payload.manifest.payload.version.value,
            payload.integrity.aggregate_digest.value,
        )
        for payload in current.planner.payloads
    )
    return (
        current.applicable
        and current.repo == plan.repo
        and current.to_jsonable() == plan.to_jsonable()
        and current.config_content == plan.config_content
        and current.catalog_content == plan.catalog_content
        and current.lock_content == plan.lock_content
        and current.legacy_preconditions == plan.legacy_preconditions
        and reconciliation_fingerprint(current.reconciliation)
        == reconciliation_fingerprint(plan.reconciliation)
        and current_lineage == expected_lineage
    )


def _legacy_preconditions_current(
    plan: LegacyMigrationPlan,
    *,
    allow_removed: bool,
) -> bool:
    paths = tuple(SafeRelativePath.parse(path) for path, _digest in plan.legacy_preconditions)
    try:
        snapshot = RepositorySnapshot.capture(plan.repo, paths)
    except ControlPlaneError, OSError, ValueError:
        return False
    removable = {action.target for action in plan.legacy_removals}
    for path, digest in plan.legacy_preconditions:
        entry = snapshot.entry(SafeRelativePath.parse(path))
        if entry.kind is EntryKind.MISSING and allow_removed and path in removable:
            continue
        if entry.content_digest != digest:
            return False
    return True


def _remaining_reconciliation(plan: LegacyMigrationPlan) -> ReconciliationPlan:
    targets = {target.target: target for target in plan.reconciliation.targets}
    remaining: list[ControlAction] = []
    for action in plan.reconciliation.actions:
        if action.kind not in _MUTATING_ACTIONS:
            continue
        relative = SafeRelativePath.parse(action.target)
        observed = RepositorySnapshot.capture(plan.repo, (relative,)).entry(relative)
        if action.kind is ActionKind.REMOVE:
            if observed.kind is EntryKind.MISSING:
                continue
        else:
            target = targets[action.target]
            desired = hashlib.sha256(target.content).hexdigest()
            desired_digest = f"sha256:{desired}"
            desired_mode = target.mode
            if (
                observed.content_digest is not None
                and observed.content_digest.value == desired_digest
                and (desired_mode is None or observed.mode == desired_mode)
            ):
                continue
        if observed.precondition_digest.value != _precondition(
            plan.reconciliation,
            action.target,
        ):
            raise _ApplyFailure(
                "CP-STALE-PLAN",
                "migration target differs from both its preview and proposed state",
            )
        remaining.append(action)
    names = {action.target for action in remaining}
    prunes = tuple(
        namespace
        for namespace in plan.reconciliation.namespace_prunes
        if (plan.repo / namespace).exists()
    )
    return replace(
        plan.reconciliation,
        actions=tuple(remaining),
        targets=tuple(target for target in plan.reconciliation.targets if target.target in names),
        namespace_prunes=prunes,
    )


def _publish_control_file(
    request: ApplyRequest,
    control: LockedControlDirectory,
    temporary: str,
    destination: str,
) -> None:
    _fault(request, "publish", f".standards/{destination}")
    if control.file_kind(destination) != "missing" or not control.is_current():
        raise _ApplyFailure("CP-PRECONDITION", "migration control state changed during apply")
    try:
        os.replace(
            temporary,
            destination,
            src_dir_fd=control.descriptor,
            dst_dir_fd=control.descriptor,
        )
        os.fsync(control.descriptor)
    except OSError as exc:
        raise _ApplyFailure("CP-APPLY-PUBLISH", "control file replacement failed") from exc
    _fault(request, "published", f".standards/{destination}")


def _remove_legacy(
    request: ApplyRequest,
    plan: LegacyMigrationPlan,
    root_descriptor: int,
    applied: list[str],
) -> None:
    expected = dict(plan.legacy_preconditions)
    for action in plan.legacy_removals:
        _fault(request, "remove", action.target)
        relative = SafeRelativePath.parse(action.target)
        snapshot = RepositorySnapshot.capture(plan.repo, (relative,)).entry(relative)
        if snapshot.kind is EntryKind.MISSING:
            continue
        if snapshot.content_digest != expected.get(action.target):
            raise _ApplyFailure("CP-PRECONDITION", "legacy state changed during apply")
        parent = _open_parent(root_descriptor, relative.normalized.parent, [])
        try:
            os.unlink(relative.normalized.name, dir_fd=parent)
            os.fsync(parent)
        except OSError as exc:
            raise _ApplyFailure("CP-MIGRATION-REMOVE", "legacy state removal failed") from exc
        finally:
            os.close(parent)
        applied.append(action.target)
        _fault(request, "removed", action.target)


def apply_legacy_migration(
    plan: LegacyMigrationPlan,
    *,
    fault_hook: FaultHook | None = None,
    verification_runner: VerificationRunner | None = None,
) -> ApplyResult:
    """Publish one exact migration plan and retire legacy authority after verification."""
    if not _migration_plan_current(plan):
        return ApplyResult(False, (), False, "CP-STALE-PLAN")

    control_path = plan.repo / ".standards"
    created_control = False
    if control_path.is_symlink():
        return ApplyResult(False, (), False, "CP-APPLY-PATH")
    if not control_path.exists():
        try:
            control_path.mkdir(mode=0o755)
            created_control = True
        except OSError:
            return ApplyResult(False, (), False, "CP-APPLY-PATH")
    elif not control_path.is_dir():
        return ApplyResult(False, (), False, "CP-APPLY-PATH")

    request = ApplyRequest(
        planner=plan.planner,
        expected_plan=plan.reconciliation,
        fault_hook=fault_hook,
        verification_runner=verification_runner,
    )
    applied: list[str] = []
    verification_findings: tuple[ControlFinding, ...] = ()
    staged: dict[str, _StagedTarget] = {}
    control_staged: dict[str, str] = {}
    created: list[PurePosixPath] = []
    published = False
    lock_written = False
    root: Path | None = None
    root_descriptor: int | None = None
    control_cleanup_descriptor: int | None = None
    try:
        with control_plane_lock(plan.repo, LockMode.WRITE) as control:
            control_cleanup_descriptor = os.dup(control.descriptor)
            lock_kind = control.file_kind("lock.toml")
            if lock_kind not in {"missing", "regular"}:
                raise _ApplyFailure("CP-STALE-PLAN", "migration central lock is unsafe")
            if lock_kind == "regular":
                if control.read_bytes("lock.toml") != plan.lock_content:
                    raise _ApplyFailure("CP-STALE-PLAN", "migration central lock is unexpected")
                lock_written = True
            intent_name = ".migration-lock.toml"
            intent_kind = control.file_kind(intent_name)
            if intent_kind not in {"missing", "regular"}:
                raise _ApplyFailure("CP-STALE-PLAN", "migration recovery intent is unsafe")
            intent_ready = intent_kind == "regular"
            if intent_ready and control.read_bytes(intent_name) != plan.lock_content:
                raise _ApplyFailure("CP-STALE-PLAN", "migration recovery intent is unexpected")
            if lock_written and intent_ready:
                raise _ApplyFailure("CP-STALE-PLAN", "migration has duplicate lock state")
            if not _legacy_preconditions_current(plan, allow_removed=lock_written):
                raise _ApplyFailure("CP-STALE-PLAN", "legacy state changed after planning")
            root, root_descriptor = _open_repository(plan.repo)
            _fault(request, "before-staging", "$migration")
            for name, content in (
                ("config.toml", plan.config_content),
                ("catalog.toml", plan.catalog_content),
                ("lock.toml", plan.lock_content),
            ):
                if name == "lock.toml" and (lock_written or intent_ready):
                    continue
                kind = control.file_kind(name)
                if kind == "regular":
                    if control.read_bytes(name) != content:
                        raise _ApplyFailure(
                            "CP-STALE-PLAN",
                            "migration control file differs from its proposed state",
                        )
                    continue
                if kind != "missing":
                    raise _ApplyFailure("CP-STALE-PLAN", "migration control file is unsafe")
                control_staged[name] = _stage_bytes(
                    control.descriptor,
                    name,
                    content,
                    "0644",
                )
            remaining = _remaining_reconciliation(plan)
            staged = _stage_targets(
                request,
                remaining,
                root_descriptor,
                created,
            )
            if (
                not _legacy_preconditions_current(plan, allow_removed=lock_written)
                or not control.is_current()
            ):
                raise _ApplyFailure("CP-PRECONDITION", "migration authority changed after staging")

            if not lock_written and not intent_ready:
                _fault(request, "intent", f".standards/{intent_name}")
                if control.file_kind(intent_name) != "missing" or not control.is_current():
                    raise _ApplyFailure("CP-PRECONDITION", "migration intent changed during apply")
                try:
                    os.replace(
                        control_staged["lock.toml"],
                        intent_name,
                        src_dir_fd=control.descriptor,
                        dst_dir_fd=control.descriptor,
                    )
                    os.fsync(control.descriptor)
                except OSError as exc:
                    raise _ApplyFailure(
                        "CP-APPLY-PUBLISH",
                        "migration recovery intent could not be published",
                    ) from exc
                intent_ready = True
                published = True
                _fault(request, "published", f".standards/{intent_name}")

            _publish_targets(
                request,
                remaining,
                staged,
                applied,
                root_descriptor,
            )
            published = published or bool(applied)
            for name in ("config.toml", "catalog.toml"):
                if name not in control_staged:
                    continue
                _publish_control_file(request, control, control_staged[name], name)
                published = True
                applied.append(f".standards/{name}")

            verification_findings = _verify(request, plan.reconciliation)

            if not lock_written:
                _fault(request, "lock", ".standards/lock.toml")
                if control.file_kind("lock.toml") != "missing" or not control.is_current():
                    raise _ApplyFailure("CP-PRECONDITION", "central lock changed during migration")
                try:
                    os.replace(
                        intent_name,
                        "lock.toml",
                        src_dir_fd=control.descriptor,
                        dst_dir_fd=control.descriptor,
                    )
                    os.fsync(control.descriptor)
                except OSError as exc:
                    raise _ApplyFailure(
                        "CP-APPLY-PUBLISH",
                        "central lock replacement failed",
                    ) from exc
                lock_written = True
                applied.append(".standards/lock.toml")
                _fault(request, "published", ".standards/lock.toml")

            _remove_legacy(request, plan, root_descriptor, applied)
            return ApplyResult(
                True,
                tuple(applied),
                True,
                verification_findings=verification_findings,
            )
    except ControlPlaneBusyError:
        return ApplyResult(False, tuple(applied), lock_written, "CP-BUSY")
    except _ApplyFailure as exc:
        return ApplyResult(
            False,
            tuple(applied),
            lock_written,
            exc.code,
            exc.findings or verification_findings,
        )
    except ControlPlaneError, OSError, ValueError:
        return ApplyResult(False, tuple(applied), lock_written, "CP-APPLY-FAILED")
    except BaseException:
        return ApplyResult(False, tuple(applied), lock_written, "CP-APPLY-FAILED")
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)
        if root is not None:
            _cleanup_staged(staged, root, created)
        if control_cleanup_descriptor is not None:
            for temporary in control_staged.values():
                with suppress(OSError):
                    os.unlink(temporary, dir_fd=control_cleanup_descriptor)
            os.close(control_cleanup_descriptor)
        if created_control and not published:
            with suppress(OSError):
                control_path.rmdir()
