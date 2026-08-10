"""Pin the unadvertised Python Tooling 1.14 VS Code task-prefix contract."""

from __future__ import annotations

import hashlib
import json
import stat
import tomllib
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.models import CentralLock
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.control_plane.planner_helpers import resolution_request

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V113 = _FAMILY / "versions/1.13"
_V114 = _FAMILY / "versions/1.14"
_PROJECTION_114 = _ROOT / "src/project_standards/payloads/python-tooling/1.14"

_TASK_LABELS = ("audit", "check", "fix", "test", "typecheck")
_TASK_TARGET = ".vscode/tasks.json"
_TASK_PREFIX = "python: "
_TASK_OPTION = "/vscode/task_prefix"
_V113_AGGREGATE = "sha256:1bb7b7d11e41fccb6faa658d97130b01c754b36faf69cff508a6908c199e36d8"

_V113_FILES = {
    "README.md": "60a97fa7aa73113da02fef29f0917b0b1287b9599e7c8a8d984a159d4328f292",
    "adopt.md": "cbb2c80f80eb72078f0dfe4752f07b469281ddfabe186ef93cef961d7e3772f9",
    "agent-summary.md": "d8330029e15eec986a38cd731d486b9ffacb71f55d0ca36f78e1de194cc9b401",
    "build-backend.md": "3e83b6ed2763d369537d59e9f0baad47ddeb6c9cbe77537478c9b1069c937083",
    "config.schema.json": "4831e2fc070219bdf733b59746381e4d8e70aa561324e324bc7ff3ccb13ec1c9",
    "payload.toml": "2702395d9a03d24b34666e742f66a977048db568df2c579be4af9defbd3632e7",
    "providers/python_tooling.py": (
        "0ed853fecfa6e4a582f4f5364dbe147776f7dcb337e6a340d27be8ffaee582a6"
    ),
    "resources/check.py": "04930fcc2fc4f9f82af40591a1ea68e8a791c9bc0c8732749439b34afe04091a",
    "resources/check.yml": "2fad10f0328e2c475fce19e4a4db59f8f8e94ab075bb327890e27256284bafcb",
    "resources/python-version": (
        "a876e0b10411037a012498b9fe18d9bc1df32ed8b722a13564dc944ddcfd9135"
    ),
    "schemas/config-transform-input.schema.json": (
        "d779ac15c07d3e0d9b4b48f0cb04291ca57135d5282a971c7711d9c66c9f9aef"
    ),
    "schemas/config-transform-report.schema.json": (
        "524bc593b7c8635f1a46f267b9d2029f6c54546a0f4fa3200dec97fa8eb810fc"
    ),
    "schemas/content.schema.json": (
        "760d819048c1f2a153e72227c940f36eed96deb5e2336e802f34caa37ccf14b3"
    ),
    "schemas/findings.schema.json": (
        "c838f02865d72e8d2aa4d6640e1fb50d03187122571752d1c75970f93ffb1066"
    ),
    "schemas/migration-report.schema.json": (
        "1c3da7195d020c3aadb87fa00a679346c1df68019ed1933dcc99b77bee154b42"
    ),
    "schemas/provider-input.schema.json": (
        "9a681ef36519edcb91e1c3717fe70e96dc8f38e4fc5aa3f851cb22cf9d6fe8d9"
    ),
}


def _require_candidate() -> None:
    assert _V114.is_dir(), "python-tooling payload 1.14 is not authored yet"
    assert (_V114 / "payload.toml").is_file(), "python-tooling 1.14 has no manifest"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, *, task_prefix: str | None = None) -> JsonObject:
    configured: JsonObject = {}
    if task_prefix is not None:
        configured = {"vscode": {"task_prefix": task_prefix}}
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(configured)


def _task_scope(label: str) -> str:
    return f"keyed-set:/tasks#label={label}"


def _render_task(root: Path, label: str, config: JsonObject) -> JsonObject:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={
                "planned_contribution": {
                    "id": "task-under-test",
                    "target": _TASK_TARGET,
                    "adapter": AdapterKind.JSONC.value,
                    "scope": _task_scope(label),
                }
            },
        )
    )
    assert result.effect is ProviderEffect.CONTENT
    assert result.content is not None
    return cast("JsonObject", json.loads(result.content))


def _write_consumer(repo: Path, *, consumer_task: bool = False) -> None:
    repo.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "example-package"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n',
        encoding="utf-8",
    )
    if consumer_task:
        target = repo / _TASK_TARGET
        target.parent.mkdir(parents=True)
        target.write_text(
            json.dumps(
                {
                    "version": "2.0.0",
                    "tasks": [
                        {
                            "label": "consumer: docs",
                            "type": "shell",
                            "command": "make docs",
                            "problemMatcher": [],
                        }
                    ],
                },
                indent="\t",
            )
            + "\n",
            encoding="utf-8",
        )


def _request(
    repo: Path,
    payloads: tuple[InstalledPayload, ...],
    *,
    task_prefix: str | None = None,
    previous_lock: CentralLock | None = None,
) -> PlannerRequest:
    config: JsonObject = {}
    if task_prefix is not None:
        config = {"vscode": {"task_prefix": task_prefix}}
    return PlannerRequest(
        repo,
        resolution_request(
            payloads,
            configs={"python-tooling": config},
            previous_lock=previous_lock,
        ),
        payloads,
    )


def _apply_initial(
    repo: Path,
    payload: InstalledPayload,
    *,
    task_prefix: str | None = None,
) -> ReconciliationPlan:
    request = _request(repo, (payload,), task_prefix=task_prefix)
    control = repo / ".standards"
    control.mkdir(exist_ok=True)
    (control / "lock.toml").write_bytes(render_lock(request.resolution.previous_lock))
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    return plan


def _task_units(plan: ReconciliationPlan) -> tuple[tuple[ActionKind, str], ...]:
    return tuple(
        (unit.kind, unit.scope)
        for unit in plan.units
        if unit.target == _TASK_TARGET and unit.scope.startswith("keyed-set:")
    )


def _read_tasks(repo: Path) -> list[JsonObject]:
    document = cast("JsonObject", json.loads((repo / _TASK_TARGET).read_bytes()))
    return cast("list[JsonObject]", document["tasks"])


def _write_tasks(repo: Path, tasks: list[JsonObject]) -> None:
    (repo / _TASK_TARGET).write_text(
        json.dumps({"version": "2.0.0", "tasks": tasks}, indent="\t") + "\n",
        encoding="utf-8",
    )


def test_python_tooling_1_14__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        path.relative_to(_V113).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in _V113.rglob("*")
        if path.is_file()
    }
    assert actual == {path: (0o644, digest) for path, digest in _V113_FILES.items()}
    assert (
        validate_payload_integrity(
            _V113, load_payload_manifest(_V113 / "payload.toml")
        ).aggregate_digest.value
        == _V113_AGGREGATE
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "python-tooling"
    }
    assert roles == {
        **{f"1.{minor}": "retained" for minor in range(1, 13)},
        "1.13": "default",
    }
    desired = tomllib.loads((_ROOT / ".standards/config.toml").read_text(encoding="utf-8"))
    locked = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    desired_standard = cast(
        "dict[str, object]", cast("dict[str, object]", desired["standards"])["python-tooling"]
    )
    locked_standard = cast(
        "dict[str, object]", cast("dict[str, object]", locked["standards"])["python-tooling"]
    )
    assert desired_standard["version"] == "latest"
    assert locked_standard["resolved"] == "1.13"


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param("python:", id="missing-space"),
        pytest.param("Python: ", id="wrong-case"),
        pytest.param("python - ", id="wrong-punctuation"),
        pytest.param(" python: ", id="leading-space"),
        pytest.param('python: "', id="quote"),
        pytest.param("python: \\", id="backslash"),
        pytest.param("python: \n", id="newline"),
        pytest.param("python: \x00", id="control-character"),
        pytest.param("python: extra ", id="suffix"),
    ],
)
def test_python_tooling_1_14__task_prefix_schema_is_closed(invalid: str) -> None:
    _require_candidate()
    schema = load_option_schema(_V114, _payload(_V114).manifest)
    resolved = schema.resolve_options({})
    vscode = cast("JsonObject", resolved["vscode"])
    assert vscode["task_prefix"] == ""
    option = cast(
        "JsonObject",
        cast(
            "JsonObject",
            cast("JsonObject", schema.document["properties"])["vscode"],
        )["properties"],
    )["task_prefix"]
    assert option == {"enum": ["", _TASK_PREFIX], "default": ""}
    with pytest.raises(PackageContractError, match="package options violate schema"):
        schema.resolve_options({"vscode": {"task_prefix": invalid}})


@pytest.mark.parametrize("prefix", ["", _TASK_PREFIX])
def test_python_tooling_1_14__exactly_one_literal_task_set_materializes(prefix: str) -> None:
    _require_candidate()
    payload = _payload(_V114)
    config = _options(_V114, task_prefix=prefix)
    declared = [
        item for item in payload.manifest.contributions if item.target.original == _TASK_TARGET
    ]
    tasks = [item for item in declared if item.scope.startswith("keyed-set:")]
    materialized = [item for item in tasks if item.materializes(config)]

    assert len(tasks) == 10
    assert [item.scope for item in materialized] == [
        _task_scope(f"{prefix}{label}") for label in _TASK_LABELS
    ]
    assert all(item.governing_options == [_TASK_OPTION] for item in tasks)
    assert all(len(item.when_any) == 1 for item in tasks)
    assert {item.when_any[0].option for item in tasks} == {_TASK_OPTION}


@pytest.mark.parametrize("label", _TASK_LABELS)
def test_python_tooling_1_14__task_rendering_changes_only_the_label(label: str) -> None:
    _require_candidate()
    predecessor = _render_task(_V113, label, _options(_V113))
    default = _render_task(_V114, label, _options(_V114))
    prefixed = _render_task(
        _V114, f"{_TASK_PREFIX}{label}", _options(_V114, task_prefix=_TASK_PREFIX)
    )

    assert default == predecessor
    [default_task] = cast("list[JsonObject]", default["tasks"])
    [prefixed_task] = cast("list[JsonObject]", prefixed["tasks"])
    assert prefixed_task["label"] == f"{_TASK_PREFIX}{label}"
    assert {key: value for key, value in prefixed_task.items() if key != "label"} == {
        key: value for key, value in default_task.items() if key != "label"
    }


@pytest.mark.parametrize(
    "label",
    [
        pytest.param("Python: check", id="wrong-prefix-case"),
        pytest.param("prefix check", id="valid-suffix-wrong-prefix"),
        pytest.param("python: check extra", id="valid-prefix-extra-suffix"),
        pytest.param("python: ../check", id="escaping-shape"),
        pytest.param("python: ", id="missing-base-label"),
        pytest.param("check", id="inactive-default-label"),
    ],
)
def test_python_tooling_1_14__provider_rejects_nonselected_scope(label: str) -> None:
    _require_candidate()
    with pytest.raises(ControlPlaneError, match="provider failed with ValueError"):
        _render_task(_V114, label, _options(_V114, task_prefix=_TASK_PREFIX))


def test_python_tooling_1_14__default_output_matches_1_13_and_is_a_fixed_point(
    tmp_path: Path,
) -> None:
    _require_candidate()
    predecessor_repo = tmp_path / "predecessor"
    successor_repo = tmp_path / "successor"
    _write_consumer(predecessor_repo)
    _write_consumer(successor_repo)
    predecessor = _payload(_V113)
    successor = _payload(_V114)
    _apply_initial(predecessor_repo, predecessor)
    first = _apply_initial(successor_repo, successor)

    assert (successor_repo / _TASK_TARGET).read_bytes() == (
        predecessor_repo / _TASK_TARGET
    ).read_bytes()
    request = _request(successor_repo, (successor,), previous_lock=first.next_lock)
    second = plan_reconciliation(request)
    result = apply_reconciliation(ApplyRequest(request, second))
    assert second.applicable, second.findings
    assert result.success
    assert result.applied_action_ids == ()


def test_python_tooling_1_14__clean_prefix_switch_removes_five_and_creates_five(
    tmp_path: Path,
) -> None:
    _require_candidate()
    repo = tmp_path / "consumer"
    _write_consumer(repo, consumer_task=True)
    predecessor = _payload(_V113)
    successor = _payload(_V114)
    initial = _apply_initial(repo, predecessor)

    request = _request(
        repo,
        (predecessor, successor),
        task_prefix=_TASK_PREFIX,
        previous_lock=initial.next_lock,
    )
    first = plan_reconciliation(request)
    second = plan_reconciliation(request)

    assert first.applicable, first.findings
    units = _task_units(first)
    assert units == _task_units(second)
    assert [scope for kind, scope in units if kind is ActionKind.REMOVE] == [
        _task_scope(label) for label in _TASK_LABELS
    ]
    assert [scope for kind, scope in units if kind is ActionKind.CREATE] == [
        _task_scope(f"{_TASK_PREFIX}{label}") for label in _TASK_LABELS
    ]
    assert apply_reconciliation(ApplyRequest(request, first)).success
    labels = {cast("str", task["label"]) for task in _read_tasks(repo)}
    assert labels == {"consumer: docs", *(f"{_TASK_PREFIX}{label}" for label in _TASK_LABELS)}


def test_python_tooling_1_14__already_renamed_requires_restore_then_adopts(
    tmp_path: Path,
) -> None:
    _require_candidate()
    repo = tmp_path / "consumer"
    _write_consumer(repo)
    predecessor = _payload(_V113)
    successor = _payload(_V114)
    initial = _apply_initial(repo, predecessor)
    original = _read_tasks(repo)
    renamed = [
        {**task, "label": f"{_TASK_PREFIX}{task['label']}"}
        for task in original
        if task["label"] in _TASK_LABELS
    ]
    _write_tasks(repo, renamed)

    request = _request(
        repo,
        (predecessor, successor),
        task_prefix=_TASK_PREFIX,
        previous_lock=initial.next_lock,
    )
    blocked = plan_reconciliation(request)
    missing = [finding for finding in blocked.findings if finding.code == "CP-MODIFIED-MANAGED"]
    assert not blocked.applicable
    assert [finding.identity for finding in missing] == [
        _task_scope(label) for label in _TASK_LABELS
    ]
    assert all(finding.governing_options == (_TASK_OPTION,) for finding in missing)

    restored = [*renamed, *original]
    _write_tasks(repo, restored)
    accepted = plan_reconciliation(request)
    assert accepted.applicable, accepted.findings
    units = _task_units(accepted)
    assert [scope for kind, scope in units if kind is ActionKind.REMOVE] == [
        _task_scope(label) for label in _TASK_LABELS
    ]
    assert [scope for kind, scope in units if kind is ActionKind.ADOPT] == [
        _task_scope(f"{_TASK_PREFIX}{label}") for label in _TASK_LABELS
    ]


def test_python_tooling_1_14__modified_old_task_still_fails_closed(tmp_path: Path) -> None:
    _require_candidate()
    repo = tmp_path / "consumer"
    _write_consumer(repo)
    predecessor = _payload(_V113)
    successor = _payload(_V114)
    initial = _apply_initial(repo, predecessor)
    tasks = _read_tasks(repo)
    tasks[0] = {**tasks[0], "command": "consumer changed this"}
    _write_tasks(repo, tasks)

    request = _request(
        repo,
        (predecessor, successor),
        task_prefix=_TASK_PREFIX,
        previous_lock=initial.next_lock,
    )
    plan = plan_reconciliation(request)

    assert not plan.applicable
    assert "CP-MODIFIED-MANAGED" in {finding.code for finding in plan.findings}


def test_python_tooling_1_14__versioned_guidance_matches_verified_migrations() -> None:
    _require_candidate()
    readme = (_V114 / "README.md").read_text(encoding="utf-8")
    adopt = (_V114 / "adopt.md").read_text(encoding="utf-8")
    summary = (_V114 / "agent-summary.md").read_text(encoding="utf-8")

    for label in _TASK_LABELS:
        assert f"`{label}`" in readme
    assert "`vscode.task_prefix`" in readme
    assert 'task_prefix = "python: "' in adopt
    assert "restore" in adopt.lower()
    assert "ADOPT" in adopt
    assert "REMOVE" in adopt
    assert "`/vscode/task_prefix`" in summary


def test_python_tooling_1_14__source_projection_and_unadvertised_catalog_are_complete() -> None:
    _require_candidate()
    source_files = {
        path.relative_to(_V114).as_posix() for path in _V114.rglob("*") if path.is_file()
    }
    projected_files = {
        path.relative_to(_PROJECTION_114).as_posix()
        for path in _PROJECTION_114.rglob("*")
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_114 / relative).resolve() == (_V114 / relative).resolve()
        for relative in source_files
    )

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.14"]["payload"] == "versions/1.14/payload.toml"
    assert versions["1.14"]["digest"] == _payload(_V114).integrity.aggregate_digest.value

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    advertised = [
        item
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "python-tooling"
    ]
    assert not [item for item in advertised if item["version"] == "1.14"]
    assert next(item for item in advertised if item["version"] == "1.13")["role"] == "default"
    assert "python-tooling@1.14" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_python_tooling_1_14__projection_contains_only_symlinks() -> None:
    _require_candidate()
    assert _PROJECTION_114.is_dir()
    assert not [
        path for path in _PROJECTION_114.rglob("*") if path.is_file() and not path.is_symlink()
    ]
    assert all(path.readlink() for path in _PROJECTION_114.rglob("*") if path.is_symlink())
