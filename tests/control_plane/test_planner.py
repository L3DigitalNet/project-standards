from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from project_standards.control_plane.adapters.toml import TomlAdapter
from project_standards.control_plane.codec import parse_lock, render_lock
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlAction,
    ControlFinding,
    findings_to_jsonable,
)
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.models import CentralLock
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
)
from project_standards.control_plane.resolution import DeclaredTransition
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import JsonValue, ProviderEffect
from tests.control_plane.planner_helpers import (
    ContributionFixture,
    digest,
    locked_unit,
    previous_lock,
    resolution_request,
    write_payload,
)


def _request(
    repo: Path,
    payloads: Sequence[InstalledPayload],
    *,
    lock: CentralLock | None = None,
    configs: Mapping[str, Mapping[str, JsonValue]] | None = None,
    provider_runner: Callable[[ProviderInvocation], ProviderResult] | None = None,
    transition_paths: frozenset[DeclaredTransition] = frozenset(),
) -> PlannerRequest:
    resolution = resolution_request(
        payloads,
        configs=configs,
        previous_lock=lock,
    )
    return PlannerRequest(
        repo=repo,
        resolution=replace(resolution, transition_paths=transition_paths),
        payloads=tuple(payloads),
        provider_runner=provider_runner,
    )


def _action(plan: ReconciliationPlan, target: str) -> ControlAction:
    return next(action for action in plan.actions if action.target == target)


def test_planner_composes_complete_virtual_tree_and_next_lock(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_bytes(b"[project]\nname = 'consumer'\n")
    alpha = write_payload(
        tmp_path / "alpha",
        "alpha",
        artifacts=[
            {"id": "tool", "target": "tools/alpha.py", "content": b"alpha\n"},
            {
                "id": "report",
                "target": ".standards/packages/alpha/report.md",
                "content": b"report\n",
            },
        ],
        contributions=[
            {
                "id": "line-length",
                "target": "pyproject.toml",
                "adapter": "toml",
                "scope": "key:/tool/ruff/line-length",
                "content": b"[tool.ruff]\nline-length = 100\n",
            }
        ],
        verify_providers=["verify-alpha"],
    )
    beta = write_payload(
        tmp_path / "beta",
        "beta",
        contributions=[
            {
                "id": "branch",
                "target": "pyproject.toml",
                "adapter": "toml",
                "scope": "key:/tool/coverage/branch",
                "content": b"[tool.coverage]\nbranch = true\n",
            }
        ],
    )

    plan = plan_reconciliation(_request(repo, (beta, alpha)))

    assert plan.applicable
    assert plan.findings == ()
    assert {action.target for action in plan.actions} == {
        ".standards/packages/alpha/report.md",
        "pyproject.toml",
        "tools/alpha.py",
    }
    assert _action(plan, "pyproject.toml").kind is ActionKind.UPDATE
    composed = plan.proposed_content("pyproject.toml")
    assert composed.startswith(b"[project]\nname = 'consumer'\n")
    assert b"[tool.coverage]\nbranch = true\n" in composed
    assert b"[tool.ruff]\nline-length = 100\n" in composed
    assert len(plan.next_lock.artifacts) == 4
    assert [request.provider_id for request in plan.verification_requests] == ["verify-alpha"]
    assert len(plan.preconditions) == 3
    public = plan.to_jsonable()
    assert json.dumps(public, sort_keys=True)
    assert "alpha\\n" not in json.dumps(public, sort_keys=True)
    assert (repo / "tools/alpha.py").exists() is False


@pytest.mark.parametrize("adapter", ["json", "jsonc"])
def test_fresh_json_family_target_is_prettier_clean(
    tmp_path: Path,
    adapter: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "demo",
        "demo",
        contributions=[
            {
                "id": "tasks",
                "target": ".vscode/tasks.json",
                "adapter": adapter,
                "scope": "key:/tasks",
                "content": (
                    b'{"tasks":[{"label":"Project standards: check","type":"shell",'
                    b'"command":"uv run project-standards reconcile --check",'
                    b'"problemMatcher":[]}]}'
                ),
            }
        ],
    )

    plan = plan_reconciliation(_request(repo, (payload,)))

    assert plan.applicable
    assert plan.proposed_content(".vscode/tasks.json") == (
        b'{\n\t"tasks": [\n\t\t{\n\t\t\t"label": "Project standards: check",\n'
        b'\t\t\t"type": "shell",\n\t\t\t"command": '
        b'"uv run project-standards reconcile --check",\n'
        b'\t\t\t"problemMatcher": []\n\t\t}\n\t]\n}\n'
    )


def test_true_noop_action_uses_comparable_content_digests(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "demo",
        "demo",
        contributions=[
            {
                "id": "setting",
                "target": "settings.json",
                "adapter": "json",
                "scope": "key:/tool/enabled",
                "content": b'{"tool": {"enabled": true}}\n',
            }
        ],
    )
    initial = plan_reconciliation(_request(repo, (payload,)))
    content = initial.proposed_content("settings.json")
    (repo / "settings.json").write_bytes(content)

    settled = plan_reconciliation(_request(repo, (payload,), lock=initial.next_lock))

    action = _action(settled, "settings.json")
    assert action.kind is ActionKind.NOOP
    assert action.before_digest == digest(content)
    assert action.after_digest == digest(content)


@pytest.mark.parametrize(
    ("case", "expected", "expected_summary"),
    [
        ("adopt", ActionKind.ADOPT, "adopt matching managed units"),
        ("update", ActionKind.UPDATE, "update managed units in target"),
        ("repair", ActionKind.CREATE, "create composed target"),
        ("no-op", ActionKind.NOOP, "target already matches managed units"),
    ],
)
def test_whole_file_lifecycle_classification(
    tmp_path: Path,
    case: str,
    expected: ActionKind,
    expected_summary: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[{"id": "tool", "target": "tool.txt", "content": b"desired\n"}],
    )
    lock = None
    if case == "adopt":
        (repo / "tool.txt").write_bytes(b"desired\n")
    else:
        live = b"desired\n" if case == "no-op" else b"old\n"
        if case != "repair":
            (repo / "tool.txt").write_bytes(live)
            (repo / "tool.txt").chmod(0o644)
        recorded = b"desired\n" if case == "repair" else live
        lock = previous_lock(
            locked_unit(
                path="tool.txt",
                adapter="whole-file",
                scope="$file",
                owners=["demo"],
                semantic_digest=digest(recorded),
                content_digest=digest(recorded),
            )
        )

    plan = plan_reconciliation(_request(repo, (payload,), lock=lock))

    assert plan.applicable
    action = _action(plan, "tool.txt")
    assert action.kind is expected
    assert expected_summary in action.summary


def test_whole_file_mode_only_change_is_an_update(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "tool.sh"
    path.write_bytes(b"#!/bin/sh\n")
    path.chmod(0o644)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "tool",
                "target": "tool.sh",
                "content": b"#!/bin/sh\n",
                "mode": "0755",
            }
        ],
    )
    lock = previous_lock(
        locked_unit(
            path="tool.sh",
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=digest(b"#!/bin/sh\n"),
            content_digest=digest(b"#!/bin/sh\n"),
        )
    )

    plan = plan_reconciliation(_request(repo, (payload,), lock=lock))

    assert plan.applicable
    action = _action(plan, "tool.sh")
    assert action.kind is ActionKind.UPDATE
    assert action.before_mode == "0644"
    assert action.after_mode == "0755"
    assert plan.targets[0].mode == "0755"


def test_whole_file_update__undeclared_mode__preserves_observed_mode(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "tool.sh"
    installed = b"#!/bin/sh\necho old\n"
    desired = b"#!/bin/sh\necho new\n"
    path.write_bytes(installed)
    path.chmod(0o755)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "tool",
                "target": "tool.sh",
                "content": desired,
                "mode": None,
            }
        ],
    )
    lock = previous_lock(
        {
            **locked_unit(
                path="tool.sh",
                adapter="whole-file",
                scope="$file",
                owners=["demo"],
                semantic_digest=digest(installed),
                content_digest=digest(installed),
            ),
            "mode": None,
        }
    )

    plan = plan_reconciliation(_request(repo, (payload,), lock=lock))

    assert plan.applicable
    assert _action(plan, "tool.sh").kind is ActionKind.UPDATE
    target = next(item for item in plan.targets if item.target == "tool.sh")
    assert target.mode == "0755"


@pytest.mark.parametrize("enabled", [True, False])
def test_edited_create_only_file_is_preserved_on_reapply_and_disable(
    tmp_path: Path,
    enabled: bool,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    installed = b"installed\n"
    edited = b"consumer edit\n"
    path = repo / "usage.md"
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "usage",
                "target": "usage.md",
                "content": installed,
                "policy": "create-only",
            }
        ],
    )
    initial = plan_reconciliation(_request(repo, (payload,)))
    path.write_bytes(initial.proposed_content("usage.md"))
    path.write_bytes(edited)
    lock = initial.next_lock
    resolution = resolution_request((payload,), previous_lock=lock)
    if not enabled:
        desired = resolution.desired.model_copy(
            update={
                "standards": {
                    "demo": resolution.desired.standards["demo"].model_copy(
                        update={"enabled": False}
                    )
                }
            }
        )
        resolution = replace(resolution, desired=desired)

    plan = plan_reconciliation(
        PlannerRequest(repo=repo, resolution=resolution, payloads=(payload,))
    )

    assert plan.applicable
    assert plan.findings == ()
    assert _action(plan, "usage.md").kind is ActionKind.PRESERVE
    assert plan.proposed_content("usage.md") == edited
    if enabled:
        assert plan.next_lock == lock


def test_preexisting_create_only_file_is_preserved_without_a_lock(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    edited = b"consumer edit\n"
    (repo / "usage.md").write_bytes(edited)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "usage",
                "target": "usage.md",
                "content": b"package template\n",
                "policy": "create-only",
            }
        ],
    )

    plan = plan_reconciliation(_request(repo, (payload,)))

    assert plan.applicable
    assert plan.findings == ()
    assert _action(plan, "usage.md").kind is ActionKind.PRESERVE
    assert plan.proposed_content("usage.md") == edited


def test_deleted_create_only_unit_moves_to_absence_and_is_not_resurrected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "settings.json"
    consumer_content = b'{"consumer": true}\n'
    target.write_bytes(consumer_content)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "tool-setting",
                "target": "settings.json",
                "adapter": "json",
                "scope": "key:/tool/enabled",
                "content": b'{"tool": {"enabled": true}}\n',
                "policy": "create-only",
            }
        ],
    )
    installed = plan_reconciliation(_request(repo, (payload,)))
    target.write_bytes(installed.proposed_content("settings.json"))
    target.write_bytes(consumer_content)

    deleted = plan_reconciliation(_request(repo, (payload,), lock=installed.next_lock))

    assert deleted.applicable
    assert _action(deleted, "settings.json").kind is ActionKind.PRESERVE
    assert deleted.next_lock.project_standards.schema_version == "1.1"
    assert deleted.next_lock.artifacts == []
    assert len(deleted.next_lock.create_only_absences) == 1
    absence = deleted.next_lock.create_only_absences[0]
    assert absence.natural_key == ("settings.json", "json", "key:/tool/enabled")
    assert absence.owners == ("demo",)
    assert absence.versions == {"demo": PackageVersion("1.0")}

    settled = plan_reconciliation(_request(repo, (payload,), lock=deleted.next_lock))

    assert settled.applicable
    assert _action(settled, "settings.json").kind is ActionKind.PRESERVE
    assert settled.next_lock.artifacts == []
    assert settled.next_lock.create_only_absences == [absence]
    assert settled.proposed_content("settings.json") == consumer_content


def test_legacy_lock_infers_absence_only_for_matching_version_and_config(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "settings.json").write_bytes(b"{}\n")
    contribution: ContributionFixture = {
        "id": "shared-setting",
        "target": "settings.json",
        "adapter": "json",
        "scope": "key:/tool/enabled",
        "content": b'{"tool": {"enabled": true}}\n',
        "policy": "create-only",
        "shared_identity": "tool-enabled",
    }
    alpha = write_payload(
        tmp_path / "alpha",
        "alpha",
        version="1.1",
        contributions=[contribution],
    )
    beta = write_payload(
        tmp_path / "beta",
        "beta",
        version="1.1",
        contributions=[contribution],
    )
    seeded = plan_reconciliation(_request(repo, (alpha, beta))).next_lock
    legacy_header = seeded.project_standards.model_copy(update={"schema_version": "1.0"})
    damaged = seeded.model_copy(
        update={
            "project_standards": legacy_header,
            "artifacts": [],
            "create_only_absences": [],
        }
    )
    legacy_content = render_lock(damaged).replace(
        b'schema_version = "1.1"',
        b'schema_version = "1.0"',
        1,
    )
    legacy = parse_lock(legacy_content)

    matching = plan_reconciliation(_request(repo, (alpha, beta), lock=legacy))

    assert matching.applicable
    assert _action(matching, "settings.json").kind is ActionKind.PRESERVE
    assert matching.next_lock.artifacts == []
    assert matching.next_lock.create_only_absences[0].owners == ("alpha", "beta")

    alpha_only_request = _request(repo, (alpha, beta), lock=matching.next_lock)
    alpha_only_desired = alpha_only_request.resolution.desired.model_copy(
        update={
            "standards": {
                **alpha_only_request.resolution.desired.standards,
                "beta": alpha_only_request.resolution.desired.standards["beta"].model_copy(
                    update={"enabled": False}
                ),
            }
        }
    )
    alpha_only = plan_reconciliation(
        replace(
            alpha_only_request,
            resolution=replace(
                alpha_only_request.resolution,
                desired=alpha_only_desired,
            ),
        )
    )
    refreshed = alpha_only.next_lock.create_only_absences[0]
    assert refreshed.owners == ("alpha",)
    assert refreshed.versions == {"alpha": PackageVersion("1.1")}

    current_header = legacy.project_standards.model_copy(update={"release": "5.1.0"})
    current_lock = legacy.model_copy(update={"project_standards": current_header})
    current_request = _request(repo, (alpha, beta), lock=current_lock)
    current_catalog_header = current_request.resolution.catalog.project_standards.model_copy(
        update={"release": "5.1.0"}
    )
    current_catalog = current_request.resolution.catalog.model_copy(
        update={"project_standards": current_catalog_header}
    )
    current = plan_reconciliation(
        replace(
            current_request,
            resolution=replace(current_request.resolution, catalog=current_catalog),
        )
    )
    assert _action(current, "settings.json").kind is ActionKind.UPDATE
    assert current.next_lock.create_only_absences == []

    beta_applied = legacy.standards["beta"]
    drifted_records = (
        beta_applied.model_copy(update={"resolved": PackageVersion("1.0")}),
        beta_applied.model_copy(
            update={"effective_config_digest": Sha256Digest(f"sha256:{'f' * 64}")}
        ),
    )
    for drifted_beta in drifted_records:
        drifted = legacy.model_copy(
            update={"standards": {**legacy.standards, "beta": drifted_beta}}
        )

        plan = plan_reconciliation(_request(repo, (alpha, beta), lock=drifted))

        assert plan.applicable
        assert _action(plan, "settings.json").kind is ActionKind.UPDATE
        assert plan.next_lock.create_only_absences == []


@pytest.mark.parametrize("created", [True, False])
def test_disabled_package_removes_created_and_preserves_adopted_file(
    tmp_path: Path,
    created: bool,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    content = b"installed\n"
    path = repo / "tool.txt"
    path.write_bytes(content)
    path.chmod(0o644)
    payload = write_payload(tmp_path / "payload", "demo")
    lock = previous_lock(
        locked_unit(
            path="tool.txt",
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=digest(content),
            content_digest=digest(content),
            created_container=created,
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
    request = PlannerRequest(
        repo=repo,
        resolution=replace(resolution, desired=disabled),
        payloads=(payload,),
    )

    plan = plan_reconciliation(request)

    expected = ActionKind.REMOVE if created else ActionKind.PRESERVE
    action = _action(plan, "tool.txt")
    assert action.kind is expected
    expected_summary = (
        "remove managed target" if created else "preserve consumer bytes outside managed changes"
    )
    assert expected_summary in action.summary


def test_disabled_package_with_already_missing_target_only_updates_lock(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    content = b"installed\n"
    payload = write_payload(tmp_path / "payload", "demo")
    lock = previous_lock(
        locked_unit(
            path="tool.txt",
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=digest(content),
            content_digest=digest(content),
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
    action = _action(plan, "tool.txt")
    assert action.kind is ActionKind.NOOP
    assert action.after_digest is None
    assert plan.next_lock.artifacts == []


def test_shared_equal_unit_combines_owners_and_last_reference_stays_materialized(
    tmp_path: Path,
) -> None:
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

    plan = plan_reconciliation(_request(repo, (alpha, beta)))

    assert plan.applicable
    assert plan.proposed_content(".editorconfig") == b"[*]\nindent_size = 4\n"
    unit = plan.next_lock.artifacts[0]
    assert unit.owners == ("alpha", "beta")


def test_shared_identity_cannot_refer_to_different_addresses(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    alpha = write_payload(
        tmp_path / "alpha",
        "alpha",
        contributions=[
            {
                "id": "indent",
                "target": ".editorconfig",
                "adapter": "editorconfig",
                "scope": "property:*#indent_size",
                "content": b"[*]\nindent_size = 4\n",
                "shared_identity": "indent-size",
            }
        ],
    )
    beta = write_payload(
        tmp_path / "beta",
        "beta",
        contributions=[
            {
                "id": "indent",
                "target": ".editorconfig",
                "adapter": "editorconfig",
                "scope": "property:*.py#indent_size",
                "content": b"[*.py]\nindent_size = 4\n",
                "shared_identity": "indent-size",
            }
        ],
    )

    plan = plan_reconciliation(_request(repo, (alpha, beta)))

    assert not plan.applicable
    assert "CP-SHARED-CONFLICT" in {finding.code for finding in plan.findings}


def test_provider_output_extension_input_and_package_local_output_are_planned(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    extension = repo / ".standards/extensions/demo/settings.json"
    extension.parent.mkdir(parents=True)
    extension.write_bytes(b'{"consumer": true}\n')
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
        contributions=[
            {
                "id": "provider-key",
                "target": "settings.json",
                "adapter": "json",
                "scope": "key:/generated",
                "provider": "render-settings",
            }
        ],
        extensions=[
            {
                "id": "settings",
                "option": "settings_path",
                "media_type": "application/json",
                "path_policy": "repository-relative",
                "preferred_root": ".standards/extensions/demo/",
            }
        ],
        render_providers=["render-settings"],
    )
    calls: list[ProviderInvocation] = []

    def render(invocation: ProviderInvocation) -> ProviderResult:
        calls.append(invocation)
        return ProviderResult(ProviderEffect.CONTENT, content=b'{"generated": 7}\n')

    plan = plan_reconciliation(
        _request(
            repo,
            (payload,),
            configs={"demo": {"settings_path": extension.relative_to(repo).as_posix()}},
            provider_runner=render,
        )
    )

    assert plan.applicable
    assert plan.proposed_content("settings.json") == b'{ "generated": 7 }\n'
    assert plan.proposed_content(".standards/packages/demo/state.txt") == b"state\n"
    assert len(plan.next_lock.referenced_inputs) == 1
    assert plan.next_lock.referenced_inputs[0].digest.value == digest(extension.read_bytes())
    assert len(calls) == 1
    assert calls[0].snapshots["referenced_inputs"] == [
        {
            "standard_id": "demo",
            "extension_id": "settings",
            "path": ".standards/extensions/demo/settings.json",
            "digest": digest(extension.read_bytes()),
        }
    ]


def test_render_providers_receive_only_package_local_referenced_inputs(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payloads: list[InstalledPayload] = []
    configs: dict[str, dict[str, JsonValue]] = {}
    for standard_id in ("alpha", "beta"):
        extension = repo / f"config/{standard_id}.json"
        extension.parent.mkdir(exist_ok=True)
        extension.write_text(f'{{"package": "{standard_id}"}}\n', encoding="utf-8")
        payloads.append(
            write_payload(
                tmp_path / standard_id,
                standard_id,
                contributions=[
                    {
                        "id": "provider-key",
                        "target": f"generated/{standard_id}.json",
                        "adapter": "json",
                        "scope": "key:/generated",
                        "provider": f"render-{standard_id}",
                    }
                ],
                extensions=[
                    {
                        "id": "settings",
                        "option": "settings_path",
                        "media_type": "application/json",
                        "path_policy": "repository-relative",
                    }
                ],
                render_providers=[f"render-{standard_id}"],
            )
        )
        configs[standard_id] = {"settings_path": extension.relative_to(repo).as_posix()}
    calls: list[ProviderInvocation] = []

    def render(invocation: ProviderInvocation) -> ProviderResult:
        calls.append(invocation)
        return ProviderResult(ProviderEffect.CONTENT, content=b'{"generated": true}\n')

    plan = plan_reconciliation(_request(repo, payloads, configs=configs, provider_runner=render))

    assert plan.applicable
    assert len(calls) == 2
    for invocation in calls:
        referenced = invocation.snapshots["referenced_inputs"]
        assert isinstance(referenced, list)
        assert len(referenced) == 1
        item = referenced[0]
        assert isinstance(item, dict)
        assert item["standard_id"] == invocation.standard_id


def test_overlapping_historical_lock_scopes_block_before_render(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    content = b"[tool.demo]\nvalue = 1\n"
    (repo / "pyproject.toml").write_bytes(content)
    adapter = TomlAdapter()
    state = adapter.inspect(
        content,
        ("table:/tool/demo", "key:/tool/demo/value"),
    )
    units = {unit.scope: unit for unit in state.units}
    lock = previous_lock(
        locked_unit(
            path="pyproject.toml",
            adapter="toml",
            scope="table:/tool/demo",
            owners=["demo"],
            semantic_digest=units["table:/tool/demo"].semantic_digest.value,
            content_digest=digest(units["table:/tool/demo"].raw),
        ),
        locked_unit(
            path="pyproject.toml",
            adapter="toml",
            scope="key:/tool/demo/value",
            owners=["demo"],
            semantic_digest=units["key:/tool/demo/value"].semantic_digest.value,
            content_digest=digest(units["key:/tool/demo/value"].raw),
        ),
    )
    payload = write_payload(tmp_path / "payload", "demo")

    plan = plan_reconciliation(_request(repo, (payload,), lock=lock))

    assert not plan.applicable
    assert "CP-LOCK-INCONSISTENT" in {finding.code for finding in plan.findings}


def test_declared_version_transition_replaces_parent_scope_with_child_key(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    content = b"[tool.demo]\nowned = 1\nconsumer = 2\n"
    (repo / "pyproject.toml").write_bytes(content)
    adapter = TomlAdapter()
    table = adapter.inspect(content, ("table:/tool/demo",)).units[0]
    lock = previous_lock(
        locked_unit(
            path="pyproject.toml",
            adapter="toml",
            scope="table:/tool/demo",
            owners=["demo"],
            semantic_digest=table.semantic_digest.value,
            content_digest=digest(table.raw),
        )
    )
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        version="1.1",
        contributions=[
            {
                "id": "owned",
                "target": "pyproject.toml",
                "adapter": "toml",
                "scope": "key:/tool/demo/owned",
                "content": b"[tool.demo]\nowned = 1\n",
            }
        ],
    )
    transition = DeclaredTransition("demo", PackageVersion("1.0"), PackageVersion("1.1"))

    plan = plan_reconciliation(
        _request(repo, (payload,), lock=lock, transition_paths=frozenset({transition}))
    )

    assert plan.applicable, plan.findings
    assert plan.proposed_content("pyproject.toml") == content
    managed = [
        unit.scope for unit in plan.next_lock.artifacts if unit.path.original == "pyproject.toml"
    ]
    assert managed == ["key:/tool/demo/owned"]


@pytest.mark.parametrize(
    ("scenario", "code"),
    [
        ("package-overlap", "CP-PACKAGE-OVERLAP"),
        ("adapter-conflict", "CP-ADAPTER-CONFLICT"),
        ("shared-conflict", "CP-SHARED-CONFLICT"),
        ("consumer-conflict", "CP-CONSUMER-CONFLICT"),
        ("malformed", "CP-MALFORMED-CONTAINER"),
        ("modified-managed", "CP-MODIFIED-MANAGED"),
    ],
)
def test_every_conflict_class_blocks_the_complete_plan(
    tmp_path: Path,
    scenario: str,
    code: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    lock = None
    alpha: InstalledPayload | None = None
    beta: InstalledPayload | None = None
    if scenario == "package-overlap":
        alpha = write_payload(
            tmp_path / "alpha",
            "alpha",
            artifacts=[{"id": "same", "target": "same.txt", "content": b"a\n"}],
        )
        beta = write_payload(
            tmp_path / "beta",
            "beta",
            artifacts=[{"id": "same", "target": "same.txt", "content": b"b\n"}],
        )
    else:
        first: ContributionFixture = {
            "id": "value",
            "target": "shared.toml",
            "adapter": "toml",
            "scope": "key:/tool/demo/value",
            "content": b"[tool.demo]\nvalue = 1\n",
        }
        second = first.copy()
        if scenario == "adapter-conflict":
            second.update(
                adapter="json",
                scope="key:/tool/demo/other",
                content=b'{"tool": {"demo": {"other": 2}}}\n',
            )
        elif scenario == "shared-conflict":
            first["shared_identity"] = "demo-value"
            second["shared_identity"] = "demo-value"
            second["content"] = b"[tool.demo]\nvalue = 2\n"
        elif scenario in {"consumer-conflict", "malformed", "modified-managed"}:
            alpha = write_payload(tmp_path / "alpha", "alpha", contributions=[first])
            beta = None
            if scenario == "consumer-conflict":
                (repo / "shared.toml").write_bytes(b"[tool.demo]\nvalue = 9\n")
            elif scenario == "malformed":
                (repo / "shared.toml").write_bytes(b"not = [toml")
            else:
                live = b"[tool.demo]\nvalue = 9\n"
                (repo / "shared.toml").write_bytes(live)
                desired_digest = f"sha256:{hashlib.sha256(b'1').hexdigest()}"
                lock = previous_lock(
                    locked_unit(
                        path="shared.toml",
                        adapter="toml",
                        scope="key:/tool/demo/value",
                        owners=["alpha"],
                        semantic_digest=desired_digest,
                        content_digest=digest(b"1"),
                    )
                )
        if scenario not in {"consumer-conflict", "malformed", "modified-managed"}:
            alpha = write_payload(tmp_path / "alpha", "alpha", contributions=[first])
            beta = write_payload(tmp_path / "beta", "beta", contributions=[second])
    assert alpha is not None
    payloads = (alpha,) if beta is None else (alpha, beta)

    plan = plan_reconciliation(_request(repo, payloads, lock=lock))

    assert not plan.applicable
    assert code in {finding.code for finding in plan.findings}
    assert (repo / "shared.toml").read_bytes() if (repo / "shared.toml").exists() else True


def test_canonical_order_controls_placement_never_value_selection(tmp_path: Path) -> None:
    baseline_repo = tmp_path / "baseline"
    baseline_repo.mkdir()
    alpha = write_payload(
        tmp_path / "alpha",
        "alpha",
        contributions=[
            {
                "id": "zeta",
                "target": "settings.json",
                "adapter": "json",
                "scope": "key:/zeta",
                "content": b'{"zeta": 2}\n',
            }
        ],
    )
    beta = write_payload(
        tmp_path / "beta",
        "beta",
        contributions=[
            {
                "id": "alpha",
                "target": "settings.json",
                "adapter": "json",
                "scope": "key:/alpha",
                "content": b'{"alpha": 1}\n',
            }
        ],
    )
    baseline = plan_reconciliation(_request(baseline_repo, (alpha, beta)))
    baseline_json = json.dumps(baseline.to_jsonable(), sort_keys=True, separators=(",", ":"))
    baseline_bytes = tuple((item.target, item.content) for item in baseline.targets)
    generator = random.Random(20260711)

    for index in range(100):
        repo = tmp_path / f"permutation-{index}"
        repo.mkdir()
        ordered = [alpha, beta]
        generator.shuffle(ordered)
        resolution = resolution_request(ordered)
        resolution_payloads = list(resolution.payloads)
        generator.shuffle(resolution_payloads)
        request = PlannerRequest(
            repo=repo,
            resolution=replace(resolution, payloads=tuple(resolution_payloads)),
            payloads=tuple(ordered),
        )

        plan = plan_reconciliation(request)

        assert (
            json.dumps(plan.to_jsonable(), sort_keys=True, separators=(",", ":")) == baseline_json
        )
        assert tuple((item.target, item.content) for item in plan.targets) == baseline_bytes

    assert baseline.proposed_content("settings.json") == b'{ "alpha": 1, "zeta": 2 }\n'


def _conflict_setup(
    tmp_path: Path,
    *,
    governing: list[str] | None = None,
    option_properties: Mapping[str, object] | None = None,
) -> tuple[Path, InstalledPayload]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "shared.toml").write_bytes(b"[tool.demo]\nvalue = 2\n")
    contribution: ContributionFixture = {
        "id": "value",
        "target": "shared.toml",
        "adapter": "toml",
        "scope": "key:/tool/demo/value",
        "content": b"[tool.demo]\nvalue = 1\n",
    }
    if governing is not None:
        contribution["governing_options"] = governing
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[contribution],
        option_properties=option_properties,
    )
    return repo, payload


def _consumer_conflict(plan: ReconciliationPlan) -> ControlFinding:
    return next(finding for finding in plan.findings if finding.code == "CP-CONSUMER-CONFLICT")


def test_consumer_conflict_finding_carries_expected_actual_values_and_digests(
    tmp_path: Path,
) -> None:
    repo, payload = _conflict_setup(tmp_path)

    plan = plan_reconciliation(_request(repo, (payload,)))
    finding = _consumer_conflict(plan)

    assert finding.expected == 1
    assert finding.actual == 2
    assert finding.expected_digest is not None and finding.expected_digest.startswith("sha256:")
    assert finding.actual_digest is not None and finding.actual_digest.startswith("sha256:")
    assert finding.expected_digest != finding.actual_digest
    assert finding.governing_options is None
    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )
    assert jsonable["expected"] == 1
    assert jsonable["actual"] == 2
    assert "governing_options" not in jsonable


def test_consumer_conflict_finding_lists_declared_governing_options(tmp_path: Path) -> None:
    repo, payload = _conflict_setup(
        tmp_path,
        governing=["mode"],
        option_properties={"mode": {"type": "string", "default": "on"}},
    )

    plan = plan_reconciliation(_request(repo, (payload,)))
    finding = _consumer_conflict(plan)

    assert finding.governing_options == ("mode",)
    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )
    assert jsonable["governing_options"] == ["mode"]


def test_consumer_conflict_finding_states_no_declared_governing_option(tmp_path: Path) -> None:
    repo, payload = _conflict_setup(tmp_path, governing=[])

    plan = plan_reconciliation(_request(repo, (payload,)))
    finding = _consumer_conflict(plan)

    assert finding.governing_options == ()
    assert "no declared package option governs this unit" in finding.hint
    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )
    assert jsonable["governing_options"] == []


def test_whole_file_conflict_finding_carries_digests_without_values(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tool.txt").write_bytes(b"consumer\n")
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[{"id": "tool", "target": "tool.txt", "content": b"managed\n"}],
    )

    plan = plan_reconciliation(_request(repo, (payload,)))
    finding = _consumer_conflict(plan)

    assert finding.expected is None
    assert finding.actual is None
    assert finding.expected_digest == digest(b"managed\n")
    assert finding.actual_digest == digest(b"consumer\n")


def test_consumer_conflict_finding_preserves_json_null_values(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "settings.json").write_bytes(b'{"tool": {"demo": {"value": 2}}}\n')
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "value",
                "target": "settings.json",
                "adapter": "json",
                "scope": "key:/tool/demo/value",
                "content": b'{"tool": {"demo": {"value": null}}}\n',
            }
        ],
    )

    plan = plan_reconciliation(_request(repo, (payload,)))
    finding = _consumer_conflict(plan)

    assert finding.actual == 2
    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )
    assert "expected" in jsonable and jsonable["expected"] is None
    assert jsonable["actual"] == 2
    assert "null_values" not in jsonable
