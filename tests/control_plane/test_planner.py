from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from project_standards.control_plane.adapters.toml import TomlAdapter
from project_standards.control_plane.diagnostics import ActionKind, ControlAction
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
) -> PlannerRequest:
    return PlannerRequest(
        repo=repo,
        resolution=resolution_request(
            payloads,
            configs=configs,
            previous_lock=lock,
        ),
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


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("adopt", ActionKind.ADOPT),
        ("update", ActionKind.UPDATE),
        ("repair", ActionKind.CREATE),
        ("no-op", ActionKind.NOOP),
    ],
)
def test_whole_file_lifecycle_classification(
    tmp_path: Path,
    case: str,
    expected: ActionKind,
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
    assert _action(plan, "tool.txt").kind is expected


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
    assert _action(plan, "tool.sh").kind is ActionKind.UPDATE
    assert plan.targets[0].mode == "0755"


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
    assert _action(plan, "tool.txt").kind is expected


def test_disabled_package_with_already_missing_file_only_updates_lock(
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
    assert _action(plan, "tool.txt").kind is ActionKind.NOOP
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
    assert plan.proposed_content("settings.json") == b'{"generated": 7}\n'
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

    assert baseline.proposed_content("settings.json") == b'{"alpha": 1, "zeta": 2}\n'
