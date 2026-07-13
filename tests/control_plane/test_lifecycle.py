from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from project_standards.control_plane.codec import parse_lock, render_lock
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.models import AcceptedTrack, CentralLock, LockedUnit
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.resolution import ResolutionRequest
from tests.control_plane.planner_helpers import (
    ContributionFixture,
    digest,
    locked_unit,
    previous_lock,
    resolution_request,
    write_payload,
)


def _materialize(repo: Path, plan: ReconciliationPlan) -> None:
    assert plan.applicable
    targets = {target.target: target for target in plan.targets}
    for action in plan.actions:
        path = repo / action.target
        if action.kind is ActionKind.REMOVE:
            path.unlink(missing_ok=True)
            continue
        if action.kind not in {ActionKind.CREATE, ActionKind.UPDATE}:
            continue
        target = targets[action.target]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(target.content)
        if target.mode is not None:
            path.chmod(int(target.mode, 8))
    for relative in plan.namespace_prunes:
        path = repo / relative
        for directory in sorted(path.rglob("*"), reverse=True):
            if directory.is_dir():
                directory.rmdir()
        path.rmdir()


def _enable_only(request: ResolutionRequest, *enabled: str) -> ResolutionRequest:
    desired = request.desired.model_copy(
        update={
            "standards": {
                standard_id: package.model_copy(update={"enabled": standard_id in enabled})
                for standard_id, package in request.desired.standards.items()
            }
        }
    )
    return replace(request, desired=desired)


def _assert_no_mutating_actions(plan: ReconciliationPlan) -> None:
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in plan.actions
    )


def test_shared_lock_requires_and_round_trips_stable_identity() -> None:
    row = locked_unit(
        path=".editorconfig",
        adapter="editorconfig",
        scope="property:*#indent_size",
        owners=["alpha", "beta"],
        semantic_digest=digest(b"4"),
        content_digest=digest(b"4"),
    )

    with pytest.raises(ValidationError, match="shared_identity"):
        LockedUnit.model_validate(row)

    row["shared_identity"] = "indent-size"
    lock = previous_lock(row)

    assert parse_lock(render_lock(lock)) == lock
    assert b'shared_identity = "indent-size"' in render_lock(lock)


def test_package_namespace_rejects_undeclared_content_and_duplicate_lock(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    namespace = repo / ".standards/packages/demo"
    namespace.mkdir(parents=True)
    (namespace / "extra.txt").write_text("consumer\n", encoding="utf-8")
    (namespace / "lock.toml").write_text("duplicate = true\n", encoding="utf-8")
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "state",
                "target": ".standards/packages/demo/state.txt",
                "content": b"state\n",
            }
        ],
    )

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=resolution_request((payload,)),
            payloads=(payload,),
        )
    )

    assert not plan.applicable
    assert {finding.code for finding in plan.findings} == {
        "CP-DUPLICATE-PACKAGE-LOCK",
        "CP-UNDECLARED-PACKAGE-CONTENT",
    }
    assert plan.namespace_prunes == ()


def test_disabled_package_prunes_only_safely_emptied_namespace(tmp_path: Path) -> None:
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
    resolution = resolution_request((payload,), previous_lock=lock)
    disabled = resolution.desired.model_copy(
        update={
            "standards": {
                "demo": resolution.desired.standards["demo"].model_copy(update={"enabled": False})
            }
        }
    )

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=replace(resolution, desired=disabled),
            payloads=(payload,),
        )
    )

    assert plan.applicable
    assert plan.namespace_prunes == (".standards/packages/demo",)


def test_disable_removes_applied_state_but_retains_accepted_track(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(tmp_path / "payload", "demo")
    base = previous_lock().model_copy(
        update={
            "accepted_tracks": {
                "demo": AcceptedTrack(major=2, authorized_catalog=CatalogMajor("5"))
            }
        }
    )
    resolution = resolution_request((payload,), previous_lock=base)
    disabled = resolution.desired.model_copy(
        update={
            "standards": {
                "demo": resolution.desired.standards["demo"].model_copy(update={"enabled": False})
            }
        }
    )

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=replace(resolution, desired=disabled),
            payloads=(payload,),
        )
    )

    assert plan.next_lock.standards == {}
    assert plan.next_lock.accepted_tracks == {"demo": base.accepted_tracks["demo"]}


def test_package_namespace_path_is_owned_by_matching_standard() -> None:
    row = locked_unit(
        path=".standards/packages/alpha/state.txt",
        adapter="whole-file",
        scope="$file",
        owners=["beta"],
        semantic_digest=digest(b"state\n"),
        content_digest=digest(b"state\n"),
    )

    with pytest.raises(ValidationError, match="package namespace"):
        LockedUnit.model_validate(row)


def test_enable_update_disable_and_reenable_package_local_artifact(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    v1 = write_payload(
        tmp_path / "v1",
        "demo",
        version="1.0",
        artifacts=[
            {
                "id": "state",
                "target": ".standards/packages/demo/state.txt",
                "content": b"one\n",
            }
        ],
    )
    first = plan_reconciliation(PlannerRequest(repo, resolution_request((v1,)), (v1,)))
    assert first.actions[0].kind is ActionKind.CREATE
    _materialize(repo, first)

    v2 = write_payload(
        tmp_path / "v2",
        "demo",
        version="1.1",
        artifacts=[
            {
                "id": "state",
                "target": ".standards/packages/demo/state.txt",
                "content": b"two\n",
            }
        ],
    )
    second_request = resolution_request((v2,), previous_lock=first.next_lock)
    second = plan_reconciliation(PlannerRequest(repo, second_request, (v2,)))
    assert second.actions[0].kind is ActionKind.UPDATE
    _materialize(repo, second)
    assert (repo / ".standards/packages/demo/state.txt").read_bytes() == b"two\n"

    disabled_request = _enable_only(resolution_request((v2,), previous_lock=second.next_lock))
    disabled = plan_reconciliation(PlannerRequest(repo, disabled_request, (v2,)))
    assert disabled.actions[0].kind is ActionKind.REMOVE
    assert disabled.next_lock.standards == {}
    assert disabled.namespace_prunes == (".standards/packages/demo",)
    _materialize(repo, disabled)
    assert not (repo / ".standards/packages/demo").exists()

    reenabled_request = resolution_request((v2,), previous_lock=disabled.next_lock)
    reenabled = plan_reconciliation(PlannerRequest(repo, reenabled_request, (v2,)))
    assert reenabled.actions[0].kind is ActionKind.CREATE
    assert set(reenabled.next_lock.standards) == {"demo"}


def test_conditional_units_transition_across_pointer_predicate_flips(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "alpha-table",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/alpha",
                "content": b'[tool.alpha]\nmode = "on"\n',
                "when_any": [{"option": "/engine/name", "equals": "alpha"}],
            },
            {
                "id": "beta-table",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/beta",
                "content": b'[tool.beta]\nmode = "on"\n',
                "when_any": [{"option": "/engine/name", "equals": "beta"}],
            },
        ],
        option_properties={
            "engine": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"name": {"enum": ["alpha", "beta"]}},
                "required": ["name"],
            }
        },
    )

    def _request(name: str, previous: CentralLock | None = None) -> ResolutionRequest:
        return resolution_request(
            (payload,),
            configs={"demo": {"engine": {"name": name}}},
            previous_lock=previous,
        )

    def _scopes(plan: ReconciliationPlan) -> set[str]:
        return {unit.scope for unit in plan.next_lock.artifacts}

    first = plan_reconciliation(PlannerRequest(repo, _request("alpha"), (payload,)))
    assert _scopes(first) == {"table:/tool/alpha"}
    _materialize(repo, first)

    converged = plan_reconciliation(
        PlannerRequest(repo, _request("alpha", first.next_lock), (payload,))
    )
    _assert_no_mutating_actions(converged)

    to_beta = plan_reconciliation(
        PlannerRequest(repo, _request("beta", first.next_lock), (payload,))
    )
    assert _scopes(to_beta) == {"table:/tool/beta"}
    assert {unit.kind for unit in to_beta.units} >= {ActionKind.REMOVE, ActionKind.CREATE}
    _materialize(repo, to_beta)
    assert "[tool.alpha]" not in (repo / "config.toml").read_text(encoding="utf-8")

    back = plan_reconciliation(
        PlannerRequest(repo, _request("alpha", to_beta.next_lock), (payload,))
    )
    assert _scopes(back) == {"table:/tool/alpha"}
    _materialize(repo, back)

    settled = plan_reconciliation(
        PlannerRequest(repo, _request("alpha", back.next_lock), (payload,))
    )
    _assert_no_mutating_actions(settled)


def test_conditional_units_disable_and_reenable_retained_selection(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "beta-table",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/beta",
                "content": b'[tool.beta]\nmode = "on"\n',
                "when_any": [{"option": "/engine/name", "equals": "beta"}],
            }
        ],
        option_properties={
            "engine": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"name": {"const": "beta"}},
                "required": ["name"],
            }
        },
    )
    selected = resolution_request(
        (payload,),
        configs={"demo": {"engine": {"name": "beta"}}},
    )
    first = plan_reconciliation(PlannerRequest(repo, selected, (payload,)))
    _materialize(repo, first)

    disabled_request = _enable_only(
        resolution_request(
            (payload,),
            configs={"demo": {"engine": {"name": "beta"}}},
            previous_lock=first.next_lock,
        )
    )
    disabled = plan_reconciliation(PlannerRequest(repo, disabled_request, (payload,)))
    assert {unit.kind for unit in disabled.units} == {ActionKind.REMOVE}
    assert disabled.next_lock.artifacts == []
    _materialize(repo, disabled)
    assert not (repo / "config.toml").exists()

    reenabled_request = resolution_request(
        (payload,),
        configs={"demo": {"engine": {"name": "beta"}}},
        previous_lock=disabled.next_lock,
    )
    reenabled = plan_reconciliation(PlannerRequest(repo, reenabled_request, (payload,)))
    assert {unit.scope for unit in reenabled.next_lock.artifacts} == {"table:/tool/beta"}
    _materialize(repo, reenabled)

    converged = plan_reconciliation(
        PlannerRequest(
            repo,
            resolution_request(
                (payload,),
                configs={"demo": {"engine": {"name": "beta"}}},
                previous_lock=reenabled.next_lock,
            ),
            (payload,),
        )
    )
    _assert_no_mutating_actions(converged)


def test_shared_owner_removal_then_last_reference_removal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    contribution: ContributionFixture = {
        "id": "indent",
        "target": ".editorconfig",
        "adapter": "editorconfig",
        "scope": "property:*#indent_size",
        "content": b"[*]\nindent_size = 4\n",
        "shared_identity": "indent-size",
    }
    alpha = write_payload(tmp_path / "alpha", "alpha", contributions=[contribution])
    beta = write_payload(tmp_path / "beta", "beta", contributions=[contribution])
    first = plan_reconciliation(
        PlannerRequest(repo, resolution_request((alpha, beta)), (alpha, beta))
    )
    _materialize(repo, first)
    assert first.next_lock.artifacts[0].owners == ("alpha", "beta")

    alpha_only_request = _enable_only(
        resolution_request((alpha, beta), previous_lock=first.next_lock),
        "alpha",
    )
    alpha_only = plan_reconciliation(PlannerRequest(repo, alpha_only_request, (alpha, beta)))
    assert alpha_only.actions[0].kind is ActionKind.PRESERVE
    assert alpha_only.next_lock.artifacts[0].owners == ("alpha",)
    assert alpha_only.next_lock.artifacts[0].shared_identity == "indent-size"

    none_request = _enable_only(
        resolution_request((alpha, beta), previous_lock=alpha_only.next_lock)
    )
    none = plan_reconciliation(PlannerRequest(repo, none_request, (alpha, beta)))
    assert none.units[0].kind is ActionKind.REMOVE
    assert none.next_lock.artifacts == []


def test_create_only_and_modified_package_local_content_are_preserved(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    path = repo / ".standards/packages/demo/state.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"consumer edit\n")
    path.chmod(0o644)
    payload = write_payload(tmp_path / "payload", "demo")
    create_only_row = locked_unit(
        path=".standards/packages/demo/state.txt",
        adapter="whole-file",
        scope="$file",
        owners=["demo"],
        semantic_digest=digest(b"consumer edit\n"),
        content_digest=digest(b"consumer edit\n"),
    )
    create_only_row["policy"] = "create-only"
    lock = previous_lock(create_only_row)
    request = _enable_only(resolution_request((payload,), previous_lock=lock))

    preserved = plan_reconciliation(PlannerRequest(repo, request, (payload,)))

    assert preserved.applicable
    assert preserved.actions[0].kind is ActionKind.PRESERVE
    assert preserved.namespace_prunes == ()

    managed_row = dict(create_only_row)
    managed_row["policy"] = "managed"
    managed_row["semantic_digest"] = digest(b"original\n")
    managed_row["content_digest"] = digest(b"original\n")
    modified_lock = previous_lock(managed_row)
    modified_request = _enable_only(resolution_request((payload,), previous_lock=modified_lock))

    modified = plan_reconciliation(PlannerRequest(repo, modified_request, (payload,)))

    assert not modified.applicable
    assert "CP-MODIFIED-MANAGED" in {finding.code for finding in modified.findings}


def test_reenable_latest_fails_closed_when_accepted_track_is_unavailable(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(tmp_path / "payload", "demo")
    lock = previous_lock().model_copy(
        update={
            "accepted_tracks": {
                "demo": AcceptedTrack(major=2, authorized_catalog=CatalogMajor("5"))
            }
        }
    )

    with pytest.raises(ControlPlaneError, match="accepted major 2 is unavailable"):
        plan_reconciliation(
            PlannerRequest(
                repo,
                resolution_request((payload,), previous_lock=lock),
                (payload,),
            )
        )
