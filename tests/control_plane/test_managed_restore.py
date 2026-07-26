from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_lock,
    render_catalog,
    render_empty_config,
    render_lock,
)
from project_standards.control_plane.executor import (
    ManagedRestoreApplyRequest,
    apply_managed_restore,
)
from project_standards.control_plane.planner import (
    ManagedRestorePlan,
    PlannerRequest,
    plan_managed_restore,
    plan_reconciliation,
)
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
)
from project_standards.control_plane.resolution import ResolutionRequest
from project_standards.package_contract.paths import Sha256Digest
from project_standards.package_contract.payload import ProviderEffect
from tests.control_plane.planner_helpers import (
    ContributionFixture,
    digest,
    locked_unit,
    previous_lock,
    resolution_request,
    write_payload,
)

_CURRENT_SECRET = b"api_token = current-secret-value\n"
_DESIRED_SECRET = b"api_token = desired-secret-value\n"
_RACED_SECRET = b"api_token = raced-secret-value\n"
_FORBIDDEN_TEXT = (
    "api_token",
    "current-secret-value",
    "desired-secret-value",
    "raced-secret-value",
)


@dataclass(frozen=True)
class _RestoreFixture:
    repo: Path
    planner: PlannerRequest
    target: Path


def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes]]:
    snapshot: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = ("symlink", path.readlink().as_posix().encode())
        elif path.is_dir():
            snapshot[relative] = ("directory", b"")
        else:
            snapshot[relative] = ("file", path.read_bytes())
    return snapshot


def _render_fixture_config(standard_ids: tuple[str, ...]) -> bytes:
    text = render_empty_config("5").decode().rstrip()
    for standard_id in standard_ids:
        text += f'\n\n[standards.{standard_id}]\nenabled = true\nversion = "latest"'
    return f"{text}\n".encode()


def _persist_authorities(
    control: Path,
    resolution: ResolutionRequest,
) -> ResolutionRequest:
    config = _render_fixture_config(tuple(sorted(resolution.desired.standards)))
    catalog = bind_catalog_digest(resolution.catalog)
    header = resolution.previous_lock.project_standards.model_copy(
        update={
            "catalog_digest": catalog.project_standards.digest,
            "config_digest": Sha256Digest(digest(config)),
        }
    )
    lock = resolution.previous_lock.model_copy(update={"project_standards": header})
    (control / "config.toml").write_bytes(config)
    (control / "catalog.toml").write_bytes(render_catalog(catalog))
    rendered_lock = render_lock(lock)
    (control / "lock.toml").write_bytes(rendered_lock)
    return replace(
        resolution,
        catalog=catalog,
        previous_lock=parse_lock(rendered_lock),
    )


def _managed_fixture(
    tmp_path: Path,
    *,
    current: bytes | None = _CURRENT_SECRET,
    desired: bytes = _DESIRED_SECRET,
    target_name: str = "tool.txt",
) -> _RestoreFixture:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[{"id": "tool", "target": target_name, "content": desired}],
    )
    lock = previous_lock(
        locked_unit(
            path=target_name,
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=digest(desired),
            content_digest=digest(desired),
        )
    )
    resolution = _persist_authorities(
        control,
        resolution_request((payload,), previous_lock=lock),
    )
    target = repo / target_name
    if current is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(current)
        target.chmod(0o644)
    return _RestoreFixture(
        repo=repo,
        planner=PlannerRequest(repo, resolution, (payload,)),
        target=target,
    )


def _managed_provider_fixture(
    tmp_path: Path,
    desired_state: dict[str, bytes],
) -> _RestoreFixture:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "tool",
                "target": "tool.txt",
                "adapter": "whole-file",
                "scope": "$file",
                "provider": "render-tool",
            }
        ],
        render_providers=["render-tool"],
    )

    def render(_invocation: ProviderInvocation) -> ProviderResult:
        return ProviderResult(ProviderEffect.CONTENT, content=desired_state["content"])

    lock = previous_lock(
        locked_unit(
            path="tool.txt",
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=digest(_DESIRED_SECRET),
            content_digest=digest(_DESIRED_SECRET),
        )
    )
    resolution = _persist_authorities(
        control,
        resolution_request((payload,), previous_lock=lock),
    )
    target = repo / "tool.txt"
    target.write_bytes(_CURRENT_SECRET)
    return _RestoreFixture(
        repo=repo,
        planner=PlannerRequest(
            repo,
            resolution,
            (payload,),
            provider_runner=render,
        ),
        target=target,
    )


def _plan(fixture: _RestoreFixture, target: str = "tool.txt") -> ManagedRestorePlan:
    plan = plan_managed_restore(fixture.planner, target)
    assert plan.applicable, plan.findings
    assert plan.preview is not None
    return plan


def _assert_only_target_changed(
    before: dict[str, tuple[str, bytes]],
    after: dict[str, tuple[str, bytes]],
    target: str,
) -> None:
    assert {key: value for key, value in before.items() if key != target} == {
        key: value for key, value in after.items() if key != target
    }


@pytest.mark.parametrize(
    ("current", "action", "current_state"),
    [
        (_CURRENT_SECRET, "overwrite", digest(_CURRENT_SECRET)),
        (None, "recreate", "absent"),
        (_DESIRED_SECRET, "noop", digest(_DESIRED_SECRET)),
    ],
    ids=["divergent", "absent", "already-desired"],
)
def test_tc_t7_002_restore_preview_apply_and_fixed_point(
    tmp_path: Path,
    current: bytes | None,
    action: str,
    current_state: str,
) -> None:
    fixture = _managed_fixture(tmp_path, current=current)
    before_preview = _tree_snapshot(fixture.repo)

    plan = _plan(fixture)

    assert _tree_snapshot(fixture.repo) == before_preview
    assert plan.preview is not None
    assert plan.preview.target == "tool.txt"
    assert plan.preview.owner == "demo"
    assert plan.preview.current_state == current_state
    assert plan.preview.lock_digest == digest(_DESIRED_SECRET)
    assert plan.preview.desired_digest == digest(_DESIRED_SECRET)
    assert plan.preview.action == action
    assert (
        plan.preview.apply_command
        == "project-standards reconcile --restore-managed tool.txt --apply"
    )

    result = apply_managed_restore(
        ManagedRestoreApplyRequest(planner=fixture.planner, expected_plan=plan)
    )

    assert result.success
    assert result.action == action
    assert result.target == "tool.txt"
    assert result.superseded_state == current_state
    assert result.resulting_digest == digest(_DESIRED_SECRET)
    after_apply = _tree_snapshot(fixture.repo)
    _assert_only_target_changed(before_preview, after_apply, "tool.txt")
    assert fixture.target.read_bytes() == _DESIRED_SECRET
    if action == "noop":
        assert after_apply == before_preview

    repeated = _plan(fixture)
    assert repeated.preview is not None
    assert repeated.preview.action == "noop"
    reconciled = plan_reconciliation(fixture.planner)
    assert reconciled.applicable
    assert not any(item.severity == "error" for item in reconciled.findings)


@pytest.mark.parametrize(
    "race",
    ["current-changed", "absent-appeared", "lock-changed", "desired-changed"],
)
def test_tc_t7_003_restore_apply_rejects_stale_preconditions(
    tmp_path: Path,
    race: str,
) -> None:
    desired_state = {"content": _DESIRED_SECRET}
    if race == "desired-changed":
        fixture = _managed_provider_fixture(tmp_path, desired_state)
    else:
        fixture = _managed_fixture(
            tmp_path,
            current=None if race == "absent-appeared" else _CURRENT_SECRET,
        )
    plan = _plan(fixture)
    apply_planner = fixture.planner
    if race in {"current-changed", "absent-appeared"}:
        fixture.target.write_bytes(_RACED_SECRET)
    elif race == "lock-changed":
        stale_unit = fixture.planner.resolution.previous_lock.artifacts[0].model_copy(
            update={
                "semantic_digest": Sha256Digest(digest(_RACED_SECRET)),
                "content_digest": Sha256Digest(digest(_RACED_SECRET)),
            }
        )
        stale_lock = fixture.planner.resolution.previous_lock.model_copy(
            update={"artifacts": [stale_unit]}
        )
        (fixture.repo / ".standards/lock.toml").write_bytes(render_lock(stale_lock))
    else:
        desired_state["content"] = _RACED_SECRET
    raced = _tree_snapshot(fixture.repo)

    result = apply_managed_restore(
        ManagedRestoreApplyRequest(planner=apply_planner, expected_plan=plan)
    )

    assert not result.success
    assert result.error_code == "CP-STALE-PLAN"
    assert _tree_snapshot(fixture.repo) == raced


@pytest.mark.parametrize("replacement", ["symlink", "directory"])
def test_tc_t7_003_restore_apply_rejects_post_preview_target_type_race(
    tmp_path: Path,
    replacement: str,
) -> None:
    fixture = _managed_fixture(tmp_path)
    plan = _plan(fixture)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(_RACED_SECRET)

    def replace_target(phase: str, _target: str) -> None:
        if phase != "precondition":
            return
        fixture.target.unlink()
        if replacement == "symlink":
            fixture.target.symlink_to(outside)
        else:
            fixture.target.mkdir()

    result = apply_managed_restore(
        ManagedRestoreApplyRequest(
            planner=fixture.planner,
            expected_plan=plan,
            fault_hook=replace_target,
        )
    )

    assert not result.success
    assert result.error_code == "CP-STALE-PLAN"
    if replacement == "symlink":
        assert fixture.target.is_symlink()
        assert fixture.target.readlink() == outside
    else:
        assert fixture.target.is_dir()
    assert outside.read_bytes() == _RACED_SECRET
    assert not any(path.name.startswith(".project-standards-") for path in fixture.repo.rglob("*"))


def test_tc_t7_003_restore_rejects_absent_target_with_missing_parent(
    tmp_path: Path,
) -> None:
    fixture = _managed_fixture(
        tmp_path,
        current=None,
        target_name="missing/tool.txt",
    )

    plan = plan_managed_restore(fixture.planner, "missing/tool.txt")

    assert not plan.applicable
    assert plan.preview is None
    assert plan.findings[0].code == "CP-RESTORE-PATH"
    assert not (fixture.repo / "missing").exists()


def test_tc_t7_003_restore_apply_rejects_parent_identity_race_without_creating_it(
    tmp_path: Path,
) -> None:
    fixture = _managed_fixture(tmp_path, target_name="nested/tool.txt")
    plan = _plan(fixture, "nested/tool.txt")
    parent = fixture.target.parent
    moved_parent = fixture.repo / "moved-parent"

    def move_parent(phase: str, _target: str) -> None:
        if phase == "precondition":
            parent.rename(moved_parent)

    result = apply_managed_restore(
        ManagedRestoreApplyRequest(
            planner=fixture.planner,
            expected_plan=plan,
            fault_hook=move_parent,
        )
    )

    assert not result.success
    assert result.error_code == "CP-STALE-PLAN"
    assert not parent.exists()
    assert (moved_parent / "tool.txt").read_bytes() == _CURRENT_SECRET
    assert not any(path.name.startswith(".project-standards-") for path in moved_parent.rglob("*"))


def _ineligible_fixture(tmp_path: Path, kind: str) -> _RestoreFixture:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    target = repo / "tool.txt"
    target.write_bytes(_CURRENT_SECRET)
    if kind in {"partial", "shared"}:
        contribution: ContributionFixture = {
            "id": "value",
            "target": "tool.txt",
            "adapter": "toml",
            "scope": "key:/tool/demo/value",
            "content": b"[tool.demo]\nvalue = 1\n",
        }
        if kind == "shared":
            contribution["shared_identity"] = "demo-value"
            alpha = write_payload(tmp_path / "alpha", "alpha", contributions=[contribution])
            beta = write_payload(tmp_path / "beta", "beta", contributions=[contribution])
            payloads = (alpha, beta)
            lock_row = {
                **locked_unit(
                    path="tool.txt",
                    adapter="toml",
                    scope="key:/tool/demo/value",
                    owners=["alpha", "beta"],
                    semantic_digest=digest(b"1"),
                    content_digest=digest(_CURRENT_SECRET),
                ),
                "shared_identity": "demo-value",
            }
        else:
            payloads = (write_payload(tmp_path / "payload", "demo", contributions=[contribution]),)
            lock_row = locked_unit(
                path="tool.txt",
                adapter="toml",
                scope="key:/tool/demo/value",
                owners=["demo"],
                semantic_digest=digest(b"1"),
                content_digest=digest(_CURRENT_SECRET),
            )
    else:
        policy = "create-only" if kind == "create-only" else "managed"
        payloads = (
            write_payload(
                tmp_path / "payload",
                "demo",
                artifacts=[
                    {
                        "id": "tool",
                        "target": "tool.txt",
                        "content": _DESIRED_SECRET,
                        "policy": policy,
                    }
                ],
            ),
        )
        lock_row = locked_unit(
            path="tool.txt",
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=digest(_DESIRED_SECRET),
            content_digest=digest(_DESIRED_SECRET),
        )
        if kind == "create-only":
            lock_row["policy"] = "create-only"
    lock = previous_lock() if kind == "no-lock" else previous_lock(lock_row)
    resolution = _persist_authorities(
        control,
        resolution_request(payloads, previous_lock=lock),
    )
    return _RestoreFixture(
        repo,
        PlannerRequest(repo, resolution, payloads),
        target,
    )


@pytest.mark.parametrize("kind", ["no-lock", "create-only", "partial", "shared"])
def test_tc_t7_003_restore_rejects_ineligible_authority(
    tmp_path: Path,
    kind: str,
) -> None:
    fixture = _ineligible_fixture(tmp_path, kind)
    before = _tree_snapshot(fixture.repo)

    plan = plan_managed_restore(fixture.planner, "tool.txt")

    assert not plan.applicable
    assert plan.preview is None
    assert plan.findings
    result = apply_managed_restore(
        ManagedRestoreApplyRequest(planner=fixture.planner, expected_plan=plan)
    )
    assert not result.success
    assert result.error_code is not None
    assert _tree_snapshot(fixture.repo) == before


@pytest.mark.parametrize(
    "kind",
    ["symlink", "directory", "glob", "absolute", "traversal"],
)
def test_tc_t7_003_restore_rejects_unsafe_path(tmp_path: Path, kind: str) -> None:
    fixture = _managed_fixture(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(_RACED_SECRET)
    target = "tool.txt"
    if kind == "symlink":
        fixture.target.unlink()
        fixture.target.symlink_to(outside)
    elif kind == "directory":
        target = "directory"
        (fixture.repo / target).mkdir()
    elif kind == "glob":
        target = "tool*.txt"
    elif kind == "absolute":
        target = str(outside)
    else:
        target = "../outside.txt"
    before = _tree_snapshot(fixture.repo)

    plan = plan_managed_restore(fixture.planner, target)

    assert not plan.applicable
    assert plan.preview is None
    assert plan.findings
    result = apply_managed_restore(
        ManagedRestoreApplyRequest(planner=fixture.planner, expected_plan=plan)
    )
    assert not result.success
    assert result.error_code is not None
    assert _tree_snapshot(fixture.repo) == before
    assert outside.read_bytes() == _RACED_SECRET


def test_tc_t7_003_restore_evidence_redacts_consumer_content(tmp_path: Path) -> None:
    fixture = _managed_fixture(tmp_path)
    plan = _plan(fixture)
    preview_text = json.dumps(plan.to_jsonable(), sort_keys=True)
    fixture.target.write_bytes(_RACED_SECRET)

    result = apply_managed_restore(
        ManagedRestoreApplyRequest(planner=fixture.planner, expected_plan=plan)
    )
    evidence = "\n".join(
        (
            preview_text,
            json.dumps(result.to_jsonable(), sort_keys=True),
            *(str(finding) for finding in result.findings),
        )
    )

    assert not result.success
    assert "tool.txt" in evidence
    assert digest(_CURRENT_SECRET) in evidence
    assert digest(_DESIRED_SECRET) in evidence
    assert all(secret not in evidence for secret in _FORBIDDEN_TEXT)
