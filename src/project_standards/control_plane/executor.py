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
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import (
    ActionKind,
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
from project_standards.control_plane.snapshot import RepositorySnapshot
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderEffect,
    ProviderOperation,
)

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


@dataclass(slots=True)
class _StagedTarget:
    target: str
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


def _plan_fingerprint(plan: ReconciliationPlan) -> str:
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
) -> dict[str, _StagedTarget]:
    targets = {target.target: target for target in plan.targets}
    staged: dict[str, _StagedTarget] = {}
    for action in plan.actions:
        if action.kind not in {ActionKind.CREATE, ActionKind.UPDATE}:
            continue
        _fault(request, "stage", action.target)
        relative = SafeRelativePath.parse(action.target)
        parent_descriptor = _open_parent(root_descriptor, relative.normalized.parent, created)
        target = targets[action.target]
        try:
            temporary = _stage_bytes(
                parent_descriptor,
                relative.normalized.name,
                target.content,
                target.mode,
            )
        except BaseException:
            os.close(parent_descriptor)
            raise
        staged[action.target] = _StagedTarget(
            action.target,
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
            os.unlink(item.temporary, dir_fd=item.parent_descriptor)
        with suppress(OSError):
            os.close(item.parent_descriptor)
    for relative in sorted(created, key=lambda item: len(item.parts), reverse=True):
        with suppress(OSError):
            (root / relative).rmdir()


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
                    src_dir_fd=item.parent_descriptor,
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


def _verification_snapshot(repo: Path, plan: ReconciliationPlan) -> JsonObject:
    targets = tuple(SafeRelativePath.parse(item.target) for item in plan.preconditions)
    snapshot = RepositorySnapshot.capture(repo, targets)
    return {
        entry.path.original: {
            "kind": entry.kind.value,
            "content_digest": entry.content_digest.value if entry.content_digest else None,
            "mode": entry.mode,
        }
        for entry in snapshot.entries
    }


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
    snapshots = _verification_snapshot(request.planner.repo, plan)
    findings: list[ControlFinding] = []
    for verification in plan.verification_requests:
        _fault(request, "verify", verification.provider_id)
        package = packages[verification.standard_id]
        payload = payloads[(verification.standard_id, verification.version)]
        try:
            result = runner(
                ProviderInvocation(
                    repo=request.planner.repo,
                    payload=payload,
                    standard_id=verification.standard_id,
                    version=package.applied.resolved,
                    provider_id=verification.provider_id,
                    operation=ProviderOperation.VERIFY,
                    effective_config=package.effective_config,
                    snapshots=snapshots,
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


def _apply_locked(
    request: ApplyRequest,
    control: LockedControlDirectory,
) -> ApplyResult:
    applied: list[str] = []
    verification_findings: tuple[ControlFinding, ...] = ()
    staged: dict[str, _StagedTarget] = {}
    created: list[PurePosixPath] = []
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
            or _plan_fingerprint(current) != _plan_fingerprint(request.expected_plan)
        ):
            return ApplyResult(False, (), False, "CP-STALE-PLAN")
        plan = current
        new_lock = render_lock(plan.next_lock)
        lock_changed = live_lock != new_lock
        lock_temporary: str | None = None
        try:
            lock_temporary = (
                _stage_bytes(control.descriptor, "lock.toml", new_lock, "0644")
                if lock_changed
                else None
            )
            staged = _stage_targets(request, plan, root_descriptor, created)
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
                _fault(request, "published", ".standards/lock.toml")
                lock_temporary = None
            return ApplyResult(
                True,
                tuple(applied),
                lock_changed,
                verification_findings=verification_findings,
            )
        except _ApplyFailure as exc:
            return ApplyResult(
                False,
                tuple(applied),
                False,
                exc.code,
                exc.findings or verification_findings,
            )
        except BaseException:
            return ApplyResult(False, tuple(applied), False, "CP-APPLY-FAILED")
        finally:
            if lock_temporary is not None:
                with suppress(OSError):
                    os.unlink(lock_temporary, dir_fd=control.descriptor)
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
