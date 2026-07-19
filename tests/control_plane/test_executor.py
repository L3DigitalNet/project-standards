from __future__ import annotations

import base64
import os
import stat
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from project_standards.control_plane.codec import parse_lock, render_lock
from project_standards.control_plane.diagnostics import ControlFinding
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
from project_standards.package_contract.payload import ProviderEffect
from tests.control_plane.planner_helpers import resolution_request, write_payload

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
        ("precondition", "alpha.txt", ()),
        ("publish", "alpha.txt", ()),
        ("precondition", "nested/beta.txt", ("alpha.txt",)),
        ("verify", "verify-demo", ("alpha.txt", "nested/beta.txt")),
        ("lock", ".standards/lock.toml", ("alpha.txt", "nested/beta.txt")),
    ],
)
def test_failure_returns_exact_published_prefix_and_preserves_previous_lock(
    tmp_path: Path,
    phase: str,
    identity: str,
    expected_applied: tuple[str, ...],
) -> None:
    repo, planner, plan = _fixture(tmp_path, verify=True)
    previous = (repo / ".standards/lock.toml").read_bytes()

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

    assert not result.success
    assert result.applied_action_ids == expected_applied
    assert not result.lock_written
    assert (repo / ".standards/lock.toml").read_bytes() == previous
    assert not list(repo.rglob(".project-standards-*.tmp"))


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
