from __future__ import annotations

import base64
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

import project_standards.control_plane.executor as executor
from project_standards.control_plane.codec import content_digest, parse_lock, render_lock
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlFinding,
    findings_to_jsonable,
)
from project_standards.control_plane.executor import (
    ApplyRequest,
    ApplyResult,
    apply_reconciliation,
)
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
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
    materialize_referenced_input_snapshots,
)
from project_standards.package_contract.payload import ProviderEffect, ProviderOperation
from tests.control_plane.planner_helpers import (
    digest,
    locked_unit,
    previous_lock,
    resolution_request,
    write_payload,
)

type FaultHook = Callable[[str, str], None]


def _fixture(
    tmp_path: Path,
    *,
    verify: bool = False,
) -> tuple[Path, PlannerRequest, ReconciliationPlan]:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {"id": "alpha", "target": "alpha.txt", "content": b"alpha\n"},
            {"id": "beta", "target": "nested/beta.txt", "content": b"beta\n"},
        ],
        verify_providers=["verify-demo"] if verify else (),
    )
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, (payload,))
    return repo, planner, plan_reconciliation(planner)


def _apply(
    planner: PlannerRequest,
    plan: ReconciliationPlan,
    *,
    fault_hook: FaultHook | None = None,
    verification_runner: Callable[[ProviderInvocation], ProviderResult] | None = None,
) -> ApplyResult:
    return apply_reconciliation(
        ApplyRequest(
            planner=planner,
            expected_plan=plan,
            fault_hook=fault_hook,
            verification_runner=verification_runner,
        )
    )


def test_stage_bytes_stages_exact_content_mode_and_temporary_name(tmp_path: Path) -> None:
    parent_descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    temporary: str | None = None
    try:
        temporary = executor._stage_bytes(  # pyright: ignore[reportPrivateUsage]
            parent_descriptor,
            b"staged\n",
            "0640",
        )
        staged = tmp_path / temporary

        assert temporary.startswith(".project-standards-")
        assert temporary.endswith(".tmp")
        assert staged.read_bytes() == b"staged\n"
        assert stat.S_IMODE(staged.stat().st_mode) == 0o640
    finally:
        if temporary is not None:
            with suppress(OSError):
                os.unlink(temporary, dir_fd=parent_descriptor)
        os.close(parent_descriptor)


def test_success_stages_replaces_verifies_and_writes_lock_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, planner, plan = _fixture(tmp_path, verify=True)
    events: list[tuple[str, str]] = []
    replacements: list[tuple[str, str]] = []
    original_replace = os.replace

    def tracked_replace(
        source: str,
        target: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        replacements.append((source, target))
        original_replace(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    def hook(phase: str, identity: str) -> None:
        events.append((phase, identity))

    def verify(invocation: ProviderInvocation) -> ProviderResult:
        assert (repo / "alpha.txt").read_bytes() == b"alpha\n"
        assert (repo / "nested/beta.txt").read_bytes() == b"beta\n"
        assert parse_lock((repo / ".standards/lock.toml").read_bytes()) == (
            parse_lock(render_lock(planner.resolution.previous_lock))
        )
        return ProviderResult(ProviderEffect.FINDINGS, findings=())

    monkeypatch.setattr(os, "replace", tracked_replace)

    result = _apply(
        planner,
        plan,
        fault_hook=hook,
        verification_runner=verify,
    )

    assert result.success
    assert result.applied_action_ids == ("alpha.txt", "nested/beta.txt")
    assert result.lock_written
    assert parse_lock((repo / ".standards/lock.toml").read_bytes()) == plan.next_lock
    assert events[-1] == ("published", ".standards/lock.toml")
    assert replacements[-1][1] == "lock.toml"
    assert all(source.startswith(".project-standards-") for source, _target in replacements)
    assert not list(repo.rglob(".project-standards-*.tmp"))


@pytest.mark.parametrize("replace_before_lock", [False, True])
def test_apply_accepts_canonical_1_0_lock_and_rechecks_its_exact_bytes(
    tmp_path: Path,
    replace_before_lock: bool,
) -> None:
    repo, planner, _initial_plan = _fixture(tmp_path)
    lock_path = repo / ".standards/lock.toml"
    legacy_content = lock_path.read_bytes().replace(
        b'schema_version = "1.1"',
        b'schema_version = "1.0"',
        1,
    )
    lock_path.write_bytes(legacy_content)
    legacy = parse_lock(legacy_content)
    planner = replace(
        planner,
        resolution=replace(planner.resolution, previous_lock=legacy),
    )
    plan = plan_reconciliation(planner)

    def replace_semantically_equivalent_lock(phase: str, identity: str) -> None:
        if replace_before_lock and phase == "lock" and identity == ".standards/lock.toml":
            lock_path.write_bytes(render_lock(legacy))

    result = _apply(planner, plan, fault_hook=replace_semantically_equivalent_lock)

    assert not list(repo.rglob(".project-standards-*.tmp"))
    if replace_before_lock:
        assert not result.success
        assert result.error_code == "CP-PRECONDITION"
        return
    assert result.success
    assert result.lock_written
    written = lock_path.read_bytes()
    assert written.startswith(b'[project_standards]\nschema_version = "1.1"\n')
    assert parse_lock(written) == plan.next_lock


@pytest.mark.parametrize("mask", [0o022, 0o027])
def test_reconciliation_default_mode_is_independent_of_process_umask(
    tmp_path: Path,
    mask: int,
) -> None:
    repo, planner, plan = _fixture(tmp_path)

    previous = os.umask(mask)
    try:
        result = _apply(planner, plan)
    finally:
        os.umask(previous)

    assert result.success
    assert stat.S_IMODE((repo / "alpha.txt").stat().st_mode) == 0o644
    assert stat.S_IMODE((repo / "nested/beta.txt").stat().st_mode) == 0o644


def test_apply_create__missing_target_with_undeclared_mode__uses_default_mode(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "tool",
                "target": "tool.sh",
                "content": b"#!/bin/sh\n",
                "mode": None,
            }
        ],
    )
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, (payload,))
    plan = plan_reconciliation(planner)

    result = _apply(planner, plan)

    assert result.success
    assert stat.S_IMODE((repo / "tool.sh").stat().st_mode) == 0o644


def test_verification_receives_lock_declared_referenced_inputs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    referenced = repo / "consumer/workflow.yml"
    referenced.parent.mkdir()
    referenced.write_text("name: consumer\n", encoding="utf-8")
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        extensions=[
            {
                "id": "workflow",
                "option": "workflow_path",
                "media_type": "text/yaml",
                "path_policy": "repository-relative",
            }
        ],
        verify_providers=["verify-demo"],
    )
    resolution = resolution_request(
        (payload,),
        configs={"demo": {"workflow_path": "consumer/workflow.yml"}},
    )
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, (payload,))
    plan = plan_reconciliation(planner)

    def verify(invocation: ProviderInvocation) -> ProviderResult:
        assert invocation.snapshots["referenced_inputs"] == [
            {
                "standard_id": "demo",
                "extension_id": "workflow",
                "path": "consumer/workflow.yml",
                "digest": plan.next_lock.referenced_inputs[0].digest.value,
            }
        ]
        return ProviderResult(ProviderEffect.FINDINGS, findings=())

    result = _apply(planner, plan, verification_runner=verify)

    assert result.success


def test_verification_receives_only_its_package_referenced_inputs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    for standard_id in ("alpha", "beta"):
        referenced = repo / f"consumer/{standard_id}.yml"
        referenced.parent.mkdir(exist_ok=True)
        referenced.write_text(f"name: {standard_id}\n", encoding="utf-8")
    payloads = tuple(
        write_payload(
            tmp_path / f"payload-{standard_id}",
            standard_id,
            extensions=[
                {
                    "id": "workflow",
                    "option": "workflow_path",
                    "media_type": "text/yaml",
                    "path_policy": "repository-relative",
                }
            ],
            verify_providers=[f"verify-{standard_id}"],
        )
        for standard_id in ("alpha", "beta")
    )
    resolution = resolution_request(
        payloads,
        configs={
            standard_id: {"workflow_path": f"consumer/{standard_id}.yml"}
            for standard_id in ("alpha", "beta")
        },
    )
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, payloads)
    plan = plan_reconciliation(planner)
    observed: dict[str, object] = {}

    def verify(invocation: ProviderInvocation) -> ProviderResult:
        referenced_inputs = invocation.snapshots["referenced_inputs"]
        observed[invocation.standard_id] = referenced_inputs
        assert isinstance(referenced_inputs, list)
        standard_ids: list[object] = []
        for item in referenced_inputs:
            assert isinstance(item, dict)
            standard_ids.append(item["standard_id"])
        assert standard_ids == [invocation.standard_id]
        beta = repo / "consumer/beta.yml"
        if invocation.standard_id == "alpha":
            beta.write_text("name: changed-beta\n", encoding="utf-8")
        materialized = materialize_referenced_input_snapshots(
            repo,
            invocation.snapshots,
            standard_id=invocation.standard_id,
            config=invocation.effective_config,
            extensions=invocation.payload.manifest.extensions,
        )
        if invocation.standard_id == "alpha":
            beta.write_text("name: beta\n", encoding="utf-8")
        content = materialized["referenced_input_content"]
        assert isinstance(content, list)
        assert len(content) == 1
        entry = content[0]
        assert isinstance(entry, dict)
        encoded = entry["content_base64"]
        assert isinstance(encoded, str)
        assert base64.b64decode(encoded) == f"name: {invocation.standard_id}\n".encode()
        return ProviderResult(ProviderEffect.FINDINGS, findings=())

    result = _apply(planner, plan, verification_runner=verify)

    assert result.success
    assert set(observed) == {"alpha", "beta"}


@pytest.mark.parametrize(
    ("phase", "identity", "expected_applied"),
    [
        ("stage", "alpha.txt", ()),
        ("stage", "nested/beta.txt", ()),
        ("precondition", "alpha.txt", ()),
        ("publish", "alpha.txt", ()),
        ("precondition", "nested/beta.txt", ("alpha.txt",)),
        ("verify", "verify-demo", ("alpha.txt", "nested/beta.txt")),
        ("lock", ".standards/lock.toml", ("alpha.txt", "nested/beta.txt")),
    ],
)
def test_failure_returns_exact_published_prefix_and_preserves_previous_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    identity: str,
    expected_applied: tuple[str, ...],
) -> None:
    repo, planner, plan = _fixture(tmp_path, verify=True)
    previous = (repo / ".standards/lock.toml").read_bytes()
    original_open_parent = executor._open_parent  # pyright: ignore[reportPrivateUsage]
    parent_descriptors: list[int] = []

    def tracked_open_parent(
        root: Path,
        root_descriptor: int,
        parent: PurePosixPath,
        created: list[PurePosixPath],
    ) -> int:
        descriptor = original_open_parent(root, root_descriptor, parent, created)
        parent_descriptors.append(descriptor)
        return descriptor

    monkeypatch.setattr(executor, "_open_parent", tracked_open_parent)

    def fault(observed_phase: str, observed_identity: str) -> None:
        if (observed_phase, observed_identity) == (phase, identity):
            raise PermissionError("injected")

    result = _apply(
        planner,
        plan,
        fault_hook=fault,
        verification_runner=lambda _invocation: ProviderResult(
            ProviderEffect.FINDINGS,
            findings=(),
        ),
    )
    leaked_descriptors: list[int] = []
    for descriptor in parent_descriptors:
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        leaked_descriptors.append(descriptor)
    for descriptor in leaked_descriptors:
        with suppress(OSError):
            os.close(descriptor)

    assert not result.success
    assert result.applied_action_ids == expected_applied
    assert not result.lock_written
    assert (repo / ".standards/lock.toml").read_bytes() == previous
    assert (list(repo.rglob(".project-standards-*.tmp")), leaked_descriptors) == ([], [])


@pytest.mark.parametrize("race", ["content", "symlink"])
def test_destination_race_or_symlink_swap_fails_before_publication(
    tmp_path: Path,
    race: str,
) -> None:
    repo, planner, plan = _fixture(tmp_path)

    def fault(phase: str, identity: str) -> None:
        if (phase, identity) != ("precondition", "alpha.txt"):
            return
        path = repo / identity
        if race == "content":
            path.write_bytes(b"raced\n")
        else:
            path.symlink_to(tmp_path / "outside")

    result = _apply(planner, plan, fault_hook=fault)

    assert not result.success
    assert result.error_code == "CP-PRECONDITION"
    assert result.applied_action_ids == ()
    if race == "symlink":
        assert (repo / "alpha.txt").is_symlink()


def test_parent_directory_rename_after_staging_blocks_detached_publication(
    tmp_path: Path,
) -> None:
    repo, planner, plan = _fixture(tmp_path)

    def fault(phase: str, identity: str) -> None:
        if (phase, identity) != ("precondition", "nested/beta.txt"):
            return
        (repo / "nested").rename(repo / "detached")
        (repo / "nested").mkdir()

    result = _apply(planner, plan, fault_hook=fault)

    assert not result.success
    assert result.error_code == "CP-PRECONDITION"
    assert result.applied_action_ids == ("alpha.txt",)
    assert not (repo / "nested/beta.txt").exists()
    assert not (repo / "detached/beta.txt").exists()


def test_stale_plan_reuse_is_rejected_before_staging(tmp_path: Path) -> None:
    repo, planner, plan = _fixture(tmp_path)
    (repo / "alpha.txt").write_bytes(b"consumer\n")

    result = _apply(planner, plan)

    assert not result.success
    assert result.error_code == "CP-STALE-PLAN"
    assert result.applied_action_ids == ()
    assert not list(repo.rglob(".project-standards-*.tmp"))


def test_verification_error_keeps_prior_lock_after_artifacts_publish(tmp_path: Path) -> None:
    repo, planner, plan = _fixture(tmp_path, verify=True)
    previous = (repo / ".standards/lock.toml").read_bytes()
    finding = ControlFinding(
        code="DEMO-VERIFY",
        severity="error",
        standard_id="demo",
        version="1.0",
        path="alpha.txt",
        identity="$file",
        message="verification failed",
        hint="repair the generated content",
    )

    result = _apply(
        planner,
        plan,
        verification_runner=lambda _invocation: ProviderResult(
            ProviderEffect.FINDINGS,
            findings=(finding,),
        ),
    )

    assert not result.success
    assert result.error_code == "CP-VERIFY"
    assert result.applied_action_ids == ("alpha.txt", "nested/beta.txt")
    assert result.verification_findings == (finding,)
    assert (repo / ".standards/lock.toml").read_bytes() == previous


def test_warning_only_conflict_free_plan_retains_apply_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, planner, plan = _fixture(tmp_path)
    warning = ControlFinding(
        code="DEMO-WARNING",
        severity="warning",
        standard_id="demo",
        version="1.0",
        path="alpha.txt",
        identity="$file",
        message="review generated content",
        hint="no action is required",
    )
    warning_plan = replace(plan, applicable=True, findings=(warning,))

    def current_plan(_request: PlannerRequest) -> ReconciliationPlan:
        return warning_plan

    monkeypatch.setattr(executor, "plan_reconciliation", current_plan)

    result = _apply(planner, warning_plan)

    assert result.success
    assert result.applied_action_ids == ("alpha.txt", "nested/beta.txt")
    assert (repo / "alpha.txt").read_bytes() == b"alpha\n"
    assert (repo / "nested/beta.txt").read_bytes() == b"beta\n"


def test_executor_holds_exclusive_lock_through_verification(tmp_path: Path) -> None:
    repo, planner, plan = _fixture(tmp_path, verify=True)

    def verify(_invocation: ProviderInvocation) -> ProviderResult:
        with pytest.raises(ControlPlaneBusyError), control_plane_lock(repo, LockMode.READ):
            pass
        return ProviderResult(ProviderEffect.FINDINGS, findings=())

    result = _apply(planner, plan, verification_runner=verify)

    assert result.success


def test_successful_second_apply_is_noop_without_lock_rewrite(tmp_path: Path) -> None:
    repo, planner, plan = _fixture(tmp_path)
    first = _apply(planner, plan)
    assert first.success
    lock_path = repo / ".standards/lock.toml"
    before = lock_path.stat().st_mtime_ns
    second_resolution = resolution_request(
        planner.payloads,
        previous_lock=plan.next_lock,
    )
    second_planner = PlannerRequest(repo, second_resolution, planner.payloads)
    second_plan = plan_reconciliation(second_planner)

    second = _apply(second_planner, second_plan)

    assert second.success
    assert second.applied_action_ids == ()
    assert not second.lock_written
    assert lock_path.stat().st_mtime_ns == before


def test_remove_action_uses_atomic_unlink_path(tmp_path: Path) -> None:
    repo, planner, plan = _fixture(tmp_path)
    assert _apply(planner, plan).success
    resolution = resolution_request(planner.payloads, previous_lock=plan.next_lock)
    disabled = resolution.desired.model_copy(
        update={
            "standards": {
                "demo": resolution.desired.standards["demo"].model_copy(update={"enabled": False})
            }
        }
    )
    remove_planner = PlannerRequest(
        repo,
        replace(resolution, desired=disabled),
        planner.payloads,
    )
    remove_plan = plan_reconciliation(remove_planner)

    result = _apply(remove_planner, remove_plan)

    assert result.success
    assert result.applied_action_ids == ("alpha.txt", "nested/beta.txt")
    assert not (repo / "alpha.txt").exists()
    assert not (repo / "nested/beta.txt").exists()


def test_namespace_prune_symlink_swap_race_does_not_delete_outside(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    target = repo / ".standards/packages/demo/state.txt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"state\n")
    target.chmod(0o644)
    payload = write_payload(tmp_path / "payload", "demo")
    lock = previous_lock(
        locked_unit(
            path=".standards/packages/demo/state.txt",
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=digest(b"state\n"),
            content_digest=digest(b"state\n"),
        )
    )
    (repo / ".standards/lock.toml").write_bytes(render_lock(lock))
    resolution = resolution_request((payload,), previous_lock=lock)
    disabled = resolution.desired.model_copy(
        update={
            "standards": {
                "demo": resolution.desired.standards["demo"].model_copy(update={"enabled": False})
            }
        }
    )
    planner = PlannerRequest(
        repo,
        replace(resolution, desired=disabled),
        (payload,),
    )
    plan = plan_reconciliation(planner)
    namespace = repo / ".standards/packages/demo"
    detached = repo / ".standards/packages/detached"
    outside_child = tmp_path / "outside/empty"
    outside_child.mkdir(parents=True)

    def swap_after_removal(phase: str, identity: str) -> None:
        if (phase, identity) != (
            "published",
            ".standards/packages/demo/state.txt",
        ):
            return
        namespace.rename(detached)
        namespace.symlink_to(outside_child.parent, target_is_directory=True)

    result = _apply(planner, plan, fault_hook=swap_after_removal)

    assert not result.success
    assert result.error_code == "CP-APPLY-PUBLISH"
    assert result.applied_action_ids == (".standards/packages/demo/state.txt",)
    assert outside_child.is_dir()
    assert detached.is_dir()


def test_keyboard_interrupt_reports_already_published_prefix(tmp_path: Path) -> None:
    _repo, planner, plan = _fixture(tmp_path)

    def interrupt(phase: str, identity: str) -> None:
        if (phase, identity) == ("published", "alpha.txt"):
            raise KeyboardInterrupt

    result = _apply(planner, plan, fault_hook=interrupt)

    assert not result.success
    assert result.error_code == "CP-APPLY-FAILED"
    assert result.applied_action_ids == ("alpha.txt",)


@pytest.mark.parametrize("behavior", ["exception", "wrong-effect"])
def test_verification_provider_contract_failure_is_not_retried(
    tmp_path: Path,
    behavior: str,
) -> None:
    _repo, planner, plan = _fixture(tmp_path, verify=True)
    calls = 0

    def verify(_invocation: ProviderInvocation) -> ProviderResult:
        nonlocal calls
        calls += 1
        if behavior == "exception":
            raise RuntimeError("injected")
        return ProviderResult(ProviderEffect.CONTENT, content=b"wrong")

    result = _apply(planner, plan, verification_runner=verify)

    assert not result.success
    assert result.error_code == "CP-VERIFY"
    assert calls == 1


def test_low_level_staged_write_failure_cleans_up_and_returns_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, planner, plan = _fixture(tmp_path)

    def zero_write(_descriptor: int, _content: memoryview) -> int:
        return 0

    monkeypatch.setattr(os, "write", zero_write)

    result = _apply(planner, plan)

    assert not result.success
    assert result.error_code == "CP-APPLY-STAGE"
    assert not list(repo.rglob(".project-standards-*.tmp"))


def test_apply_converges_after_a_create_only_file_is_deleted(tmp_path: Path) -> None:
    """Applying a consumer-deleted create-only artifact records its absence (issue #70).

    Nothing is staged for the deleted target, but the planner still publishes it
    as a `PlannedTarget` because `_locked_after` reads that entry to build the
    `create_only_absences` record. Post-apply verification must therefore accept
    an unpublished no-op over a missing path; treating it as a changed published
    target failed every apply with `CP-VERIFY` and left the drift permanent.
    """
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "notes",
                "target": "notes.md",
                "content": b"installed\n",
                "policy": "create-only",
            }
        ],
    )
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, (payload,))
    installed = plan_reconciliation(planner)
    assert _apply(planner, installed).success

    (repo / "notes.md").unlink()
    deleted_resolution = resolution_request((payload,), previous_lock=installed.next_lock)
    deleted_planner = PlannerRequest(repo, deleted_resolution, (payload,))
    deleted = plan_reconciliation(deleted_planner)

    result = _apply(deleted_planner, deleted)

    assert result.success, result.error_code
    assert result.lock_written
    written = parse_lock((control / "lock.toml").read_bytes())
    assert [item.path.original for item in written.create_only_absences] == ["notes.md"]
    assert written.artifacts == []
    assert not (repo / "notes.md").exists()

    settled_resolution = resolution_request((payload,), previous_lock=written)
    settled = plan_reconciliation(PlannerRequest(repo, settled_resolution, (payload,)))

    # Convergence: with the absence recorded, `reconcile --check` no longer
    # reports lock drift for the deletion the consumer already made.
    assert settled.next_lock == written


def _empty_managed_fixture(tmp_path: Path) -> tuple[Path, PlannerRequest, ReconciliationPlan]:
    """Build a managed whole-file artifact whose declared content is zero bytes."""
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[{"id": "marker", "target": "py.typed", "content": b""}],
    )
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, (payload,))
    return repo, planner, plan_reconciliation(planner)


def test_apply_creates_an_empty_managed_artifact_and_locks_it_live(
    tmp_path: Path,
) -> None:
    """An empty managed declaration converges in one apply (issue #77).

    The planner now decides CREATE over a missing path by unit action rather
    than rendered truthiness, so a zero-byte managed artifact (`py.typed`,
    `.gitkeep`, an empty `__init__.py`) is staged, written, and locked live in
    a single cycle. The f476c41 verification predicate is untouched: any plan
    that still records a live artifact it never staged keeps failing closed.
    """
    repo, planner, plan = _empty_managed_fixture(tmp_path)
    assert not (repo / "py.typed").exists()
    assert next(action for action in plan.actions if action.target == "py.typed").kind is (
        ActionKind.CREATE
    )
    assert [unit.path.original for unit in plan.next_lock.artifacts] == ["py.typed"]

    result = _apply(planner, plan)

    assert result.success
    assert result.lock_written
    assert (repo / "py.typed").read_bytes() == b""
    published = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert [unit.path.original for unit in published.artifacts] == ["py.typed"]


def test_apply_converges_a_deleted_create_only_target_whose_policy_turned_managed(
    tmp_path: Path,
) -> None:
    """A create-only→managed flip over a deleted file converges in one apply (issue #76).

    The desired payload policy now governs classification, so the absent unit
    plans CREATE instead of PRESERVE-from-history: the managed bytes are
    recreated, the lock records them live, and no second apply cycle is needed.
    Only a path the plan records as a create-only absence skips verification.
    """
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    create_only = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "notes",
                "target": "notes.md",
                "content": b"installed\n",
                "policy": "create-only",
            }
        ],
    )
    resolution = resolution_request((create_only,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, (create_only,))
    installed = plan_reconciliation(planner)
    assert _apply(planner, installed).success

    (repo / "notes.md").unlink()
    managed = write_payload(
        tmp_path / "managed",
        "demo",
        version="1.1",
        artifacts=[{"id": "notes", "target": "notes.md", "content": b"installed\n"}],
    )
    flipped_resolution = resolution_request((managed,), previous_lock=installed.next_lock)
    flipped_planner = PlannerRequest(repo, flipped_resolution, (managed,))
    flipped = plan_reconciliation(flipped_planner)
    assert flipped.next_lock.create_only_absences == []
    assert [unit.path.original for unit in flipped.next_lock.artifacts] == ["notes.md"]

    result = _apply(flipped_planner, flipped)

    assert result.success
    assert result.lock_written
    assert (repo / "notes.md").read_bytes() == b"installed\n"
    published = parse_lock((control / "lock.toml").read_bytes())
    assert [unit.path.original for unit in published.artifacts] == ["notes.md"]
    assert published.create_only_absences == []


def test_cp_verify_names_the_missing_locked_target_and_its_mismatch_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A locked no-op target deleted before verification is named in the finding (issue #195).

    The v5.23.0 release-prep failure this pins reported a bare `CP-VERIFY` with no
    path, and the offending file was identified only by instrumenting the executor
    by hand. `ApplyResult` carries no failure message, so the finding attached to
    the refusal is the only channel that reaches both the human report and
    `--json`; asserting on `verification_findings` is therefore asserting on what
    an operator actually sees. The deletion happens at the end of
    `_publish_targets` — the last step before `_verify` — because that is the real
    window: the plan is re-derived under the control lock, so an earlier deletion
    would simply be planned around.
    """
    repo, planner, plan = _fixture(tmp_path)
    assert _apply(planner, plan).success

    settled_resolution = resolution_request((planner.payloads[0],), previous_lock=plan.next_lock)
    settled_planner = PlannerRequest(repo, settled_resolution, planner.payloads)
    settled = plan_reconciliation(settled_planner)
    assert all(action.kind is ActionKind.NOOP for action in settled.actions)
    assert "alpha.txt" in {unit.path.original for unit in settled.next_lock.artifacts}

    published = executor._publish_targets  # pyright: ignore[reportPrivateUsage]

    def publish_then_delete(*args: object, **kwargs: object) -> object:
        outcome = published(*args, **kwargs)  # pyright: ignore[reportCallIssue, reportArgumentType]
        (repo / "alpha.txt").unlink()
        return outcome

    monkeypatch.setattr(executor, "_publish_targets", publish_then_delete)

    result = _apply(settled_planner, settled)

    assert not result.success
    assert result.error_code == "CP-VERIFY"
    assert len(result.verification_findings) == 1
    finding = result.verification_findings[0]
    assert finding.code == "CP-VERIFY"
    assert finding.severity == "error"
    assert finding.path == "alpha.txt"
    assert finding.locus == "missing"
    assert finding.message == (
        "published target is absent from the repository (mismatch kind: missing)"
    )
    # The JSON report carries the same path and kind, so `--json` consumers need
    # no separate enrichment path.
    payload = findings_to_jsonable(result.verification_findings)
    assert payload[0]["path"] == "alpha.txt"
    assert payload[0]["locus"] == "missing"


def test_cp_verify_names_a_content_mismatch_with_both_digests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The non-missing kinds are named too, with content evidence kept to digests.

    Consumer bytes never enter a finding, so the content kind publishes the
    planned and observed digests rather than either body.
    """
    repo, planner, plan = _fixture(tmp_path)
    published = executor._publish_targets  # pyright: ignore[reportPrivateUsage]

    def publish_then_overwrite(*args: object, **kwargs: object) -> object:
        outcome = published(*args, **kwargs)  # pyright: ignore[reportCallIssue, reportArgumentType]
        (repo / "alpha.txt").write_bytes(b"overwritten by the consumer\n")
        return outcome

    monkeypatch.setattr(executor, "_publish_targets", publish_then_overwrite)

    result = _apply(planner, plan)

    assert result.error_code == "CP-VERIFY"
    finding = result.verification_findings[0]
    assert finding.path == "alpha.txt"
    assert finding.locus == "content"
    assert finding.expected_digest == content_digest(b"alpha\n").value
    assert finding.actual_digest == content_digest(b"overwritten by the consumer\n").value


def test_apply_refuses_a_disclaimed_target_that_reappears_before_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recreated create-only file must still fail CP-VERIFY (issue #70 guard).

    `_disclaimed_targets` licenses skipping a published-target check, but the skip
    is conditional: the path must actually be missing. Nothing else in the suite
    exercises that condition, so replacing the missing-kind assertion with an
    unconditional `continue` stays green while publishing a lock whose recorded
    absence contradicts the file on disk. The window is real — the consumer
    restores the file after the plan is re-derived under the control lock and
    before verification reads the tree — so it is reproduced here by recreating
    the file at the end of `_publish_targets`, the last step before `_verify`.
    """
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "notes",
                "target": "notes.md",
                "content": b"installed\n",
                "policy": "create-only",
            }
        ],
    )
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    planner = PlannerRequest(repo, resolution, (payload,))
    installed = plan_reconciliation(planner)
    assert _apply(planner, installed).success

    (repo / "notes.md").unlink()
    deleted_resolution = resolution_request((payload,), previous_lock=installed.next_lock)
    deleted_planner = PlannerRequest(repo, deleted_resolution, (payload,))
    deleted = plan_reconciliation(deleted_planner)
    assert [item.path.original for item in deleted.next_lock.create_only_absences] == ["notes.md"]

    published = executor._publish_targets  # pyright: ignore[reportPrivateUsage]

    def publish_then_recreate(*args: object, **kwargs: object) -> object:
        outcome = published(*args, **kwargs)  # pyright: ignore[reportCallIssue, reportArgumentType]
        (repo / "notes.md").write_bytes(b"recreated by the consumer\n")
        return outcome

    monkeypatch.setattr(executor, "_publish_targets", publish_then_recreate)

    result = _apply(deleted_planner, deleted)

    assert not result.success
    assert result.error_code == "CP-VERIFY"
    assert not result.lock_written
    # The prior lock survives, so no recorded absence contradicts the live file.
    assert parse_lock((control / "lock.toml").read_bytes()) == installed.next_lock
    assert (repo / "notes.md").read_bytes() == b"recreated by the consumer\n"


def test_verification_dispatch_reaches_the_seam_through_its_deferred_import(
    tmp_path: Path,
) -> None:
    """Pin the deferred-import contract at `executor._verify` (T15 review F5).

    `provider_inputs` imports `command_resolution`, which imports
    `control_plane.cli`, which imports this module — so the seam is reachable
    only from inside the call. The rationale alone is not a guard: a later edit
    can hoist that import to module scope and the comment would still read true.
    This exercises the real verification path and asserts the dispatched
    snapshots ARE the seam's output, so the import both runs and returns the one
    authoritative shape.
    """
    from project_standards.control_plane.provider_inputs import provider_dispatch_input

    repo, planner, plan = _fixture(tmp_path, verify=True)
    assert plan.verification_requests, "the verify fixture must declare a verification request"
    request = plan.verification_requests[0]
    seen: list[ProviderInvocation] = []

    def verify(invocation: ProviderInvocation) -> ProviderResult:
        seen.append(invocation)
        return ProviderResult(ProviderEffect.FINDINGS, findings=())

    result = _apply(planner, plan, verification_runner=verify)

    assert result.success
    assert [item.provider_id for item in seen] == [request.provider_id]
    assert seen[0].snapshots == provider_dispatch_input(
        None,
        ProviderOperation.VERIFY,
        repo=repo,
        standard_id=request.standard_id,
        plan=plan,
        provider_id=request.provider_id,
    )


def test_deferred_seam_import_is_cycle_safe_in_a_fresh_interpreter() -> None:
    """Import the three modules in every order that could expose a cycle.

    In-process assertions cannot see this: by the time the suite runs, every
    module is already in `sys.modules`, so a module-scope cycle would import
    cleanly here and fail only for the first real caller. Each order below runs
    in its own interpreter with an empty module table.
    """
    orders = (
        ("provider_inputs", "command_resolution", "executor"),
        ("executor", "provider_inputs", "command_resolution"),
        ("command_resolution", "executor", "provider_inputs"),
    )
    for order in orders:
        program = "\n".join(f"import project_standards.control_plane.{name}" for name in order)
        completed = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, f"{order}: {completed.stderr}"
        assert not completed.stderr, f"{order}: {completed.stderr}"
