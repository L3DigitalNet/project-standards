from __future__ import annotations

import os
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
            planner.resolution.previous_lock
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
