from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane import cli as control_cli
from project_standards.control_plane.catalog_refresh import CatalogAdvance
from project_standards.control_plane.codec import (
    content_digest,
    parse_config,
    parse_lock,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlPlaneConfigurationError,
    ControlPlaneError,
)
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import (
    LegacyClaim,
    MigratedPackage,
    MigrationFinding,
    MigrationReport,
)
from project_standards.control_plane.models import (
    AppliedPackage,
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
)
from project_standards.control_plane.planner import (
    PlannerRequest,
    plan_reconciliation,
)
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
)
from project_standards.control_plane.resolution import (
    DeclaredTransition,
    MajorAuthorization,
    ResolutionPayload,
    ResolutionRequest,
)
from project_standards.control_plane.state import ControlPlaneState, StateKind
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    PayloadManifest,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
)
from tests.control_plane.planner_helpers import locked_unit, previous_lock, write_payload

_CONFIG = b"""# preserve this consumer comment
[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.demo]
enabled = true
version = "latest"
config = { additional_source_roots = [{ path = "src" }], ci = { enabled = true } }
"""

_CONFIG_WITHOUT_CI = _CONFIG.replace(b", ci = { enabled = true }", b"")
_CONFIG_WITH_EXPLICIT_TARGET_ENUM = _CONFIG.replace(
    b"ci = { enabled = true }",
    b"ci = { enabled = true, performance = true }",
)
_SOURCE_COMPATIBLE_CONFIG = _CONFIG_WITH_EXPLICIT_TARGET_ENUM.replace(
    b'[{ path = "src" }]',
    b'["src"]',
)

_TRANSFORMED_CONFIG: JsonObject = {
    "additional_source_roots": [{"path": "src"}],
    "ci": {
        "enabled": True,
        "performance": True,
    },
}

_SOURCE_EFFECTIVE: JsonObject = {
    "additional_source_roots": [],
    "ci": {
        "enabled": True,
        "performance": True,
    },
}


def _options(
    performance_default: bool,
    *,
    target_roots: bool,
    roots_default: bool = True,
    performance_enum: tuple[bool, ...] | None = None,
) -> dict[str, object]:
    performance: dict[str, object] = {
        "type": "boolean",
        "default": performance_default,
    }
    if performance_enum is not None:
        performance["enum"] = list(performance_enum)
    roots: dict[str, object] = {
        "type": "array",
        "items": (
            {
                "oneOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                ]
            }
            if target_roots
            else {"type": "string"}
        ),
    }
    if roots_default:
        roots["default"] = []
    return {
        "additional_source_roots": roots,
        "ci": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "default": True,
                },
                "performance": performance,
            },
            "required": [],
            "default": {},
        },
    }


def _target_with_transform(
    payload: InstalledPayload,
    *,
    source_version: str = "1.0",
    target_version: str = "1.1",
    transform_count: int = 1,
) -> InstalledPayload:
    document = payload.manifest.model_dump(mode="json", by_alias=True)
    document["providers"] = [
        {
            "id": "migrate-config",
            "operation": "migrate",
            "kind": "documentation-only",
            "phase": "plan",
            "effect": "migration-report",
            "resources": [],
        }
    ]
    document["migrations"] = [
        {
            "id": (
                f"demo-{source_version.replace('.', '-')}-to-{target_version.replace('.', '-')}"
                if index == 0
                else f"demo-alternate-{index}"
            ),
            "from": f"package:{source_version}",
            "to": f"package:{target_version}",
            "mode": "automatic",
            "provider": "migrate-config",
            "reversible": False,
            "affected": ["config:*"],
            "signatures": [],
            "configuration_transform": ["/ci/performance"],
        }
        for index in range(transform_count)
    ]
    manifest = PayloadManifest.model_validate(document)
    return InstalledPayload(
        payload.root,
        manifest,
        validate_payload_integrity(payload.root, manifest),
    )


def _target_without_transform(
    payload: InstalledPayload,
    *,
    manual: bool,
) -> InstalledPayload:
    document = payload.manifest.model_dump(mode="json", by_alias=True)
    migration: dict[str, object] = {
        "id": "demo-1-0-to-1-1",
        "from": "package:1.0",
        "to": "package:1.1",
        "mode": "manual" if manual else "automatic",
        "reversible": False,
        "affected": ["config:*"],
        "signatures": [],
    }
    if manual:
        migration["instructions"] = "README.md"
    else:
        migration["provider"] = "migrate-config"
    document["migrations"] = [migration]
    manifest = PayloadManifest.model_validate(document)
    return InstalledPayload(
        payload.root,
        manifest,
        validate_payload_integrity(payload.root, manifest),
    )


def _payloads(
    tmp_path: Path,
    *,
    transform_count: int = 1,
    source_performance_default: bool = True,
    target_performance_default: bool = False,
    source_performance_enum: tuple[bool, ...] | None = None,
    target_performance_enum: tuple[bool, ...] | None = None,
    source_roots_default: bool = True,
) -> tuple[InstalledPayload, InstalledPayload]:
    source = write_payload(
        tmp_path / "demo-1.0",
        "demo",
        version="1.0",
        option_properties=_options(
            performance_default=source_performance_default,
            target_roots=False,
            roots_default=source_roots_default,
            performance_enum=source_performance_enum,
        ),
    )
    target = _target_with_transform(
        write_payload(
            tmp_path / "demo-1.1",
            "demo",
            version="1.1",
            artifacts=[
                {
                    "id": "result",
                    "target": "generated.txt",
                    "content": b"selected 1.1\n",
                }
            ],
            option_properties=_options(
                performance_default=target_performance_default,
                target_roots=True,
                performance_enum=target_performance_enum,
            ),
        ),
        transform_count=transform_count,
    )
    return source, target


def _catalog(source: InstalledPayload, target: InstalledPayload) -> ConsumerCatalog:
    return ConsumerCatalog.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "digest": f"sha256:{'a' * 64}",
            },
            "standards": {
                "demo": {
                    "status": "active",
                    "available": ["1.0", "1.1"],
                    "default": "1.1",
                    "candidates": [],
                    "versions": {
                        "1.0": {
                            "channel": "retained",
                            "availability": "consumer",
                            "payload_digest": source.integrity.aggregate_digest.value,
                        },
                        "1.1": {
                            "channel": "stable",
                            "availability": "consumer",
                            "payload_digest": target.integrity.aggregate_digest.value,
                        },
                    },
                }
            },
        }
    )


def _applied(
    payload: InstalledPayload,
    effective_config: JsonObject,
) -> AppliedPackage:
    return AppliedPackage.model_validate(
        {
            "requested": "latest",
            "resolved": payload.manifest.payload.version.value,
            "selection": "stable",
            "payload_digest": payload.integrity.aggregate_digest.value,
            "effective_config_digest": semantic_digest(cast(JsonValue, effective_config)).value,
        }
    )


def _lock(
    desired: DesiredConfig,
    *,
    applied: AppliedPackage | None,
) -> CentralLock:
    base = previous_lock()
    header = base.project_standards.model_copy(
        update={"config_digest": semantic_digest(cast(JsonValue, desired.model_dump(mode="json")))}
    )
    return base.model_copy(
        update={
            "project_standards": header,
            "standards": {} if applied is None else {"demo": applied},
        }
    )


def _resolution(
    source: InstalledPayload,
    target: InstalledPayload,
    desired: DesiredConfig,
    lock: CentralLock,
) -> ResolutionRequest:
    payloads = tuple(
        ResolutionPayload(
            standard_id="demo",
            version=payload.manifest.payload.version,
            payload_digest=payload.integrity.aggregate_digest,
            option_schema=load_option_schema(payload.root, payload.manifest),
        )
        for payload in (source, target)
    )
    return ResolutionRequest(
        desired=desired,
        catalog=_catalog(source, target),
        previous_lock=lock,
        allowed_majors=frozenset(),
        payloads=payloads,
        transition_paths=frozenset(
            {
                DeclaredTransition(
                    "demo",
                    PackageVersion("1.0"),
                    PackageVersion("1.1"),
                )
            }
        ),
    )


def _runner(
    calls: list[ProviderInvocation],
    behavior: Callable[[ProviderInvocation, int], ProviderResult] | None = None,
) -> Callable[[ProviderInvocation], ProviderResult]:
    def run(invocation: ProviderInvocation) -> ProviderResult:
        calls.append(invocation)
        if behavior is not None:
            return behavior(invocation, len(calls))
        transform = cast(
            JsonObject,
            invocation.snapshots["configuration_transform"],
        )
        raw_config = cast(JsonObject, transform["raw_config"])
        recognized = [] if raw_config == _TRANSFORMED_CONFIG else ["/ci/performance"]
        report = MigrationReport(
            schema_version="1.0",
            package=MigratedPackage.model_validate(
                {
                    "standard_id": "demo",
                    "version": "1.1",
                    "selector": "latest",
                    "config": _TRANSFORMED_CONFIG,
                    "recognized_settings": recognized,
                }
            ),
        )
        return ProviderResult(
            effect=ProviderEffect.MIGRATION_REPORT,
            migration_report=report,
        )

    return run


def _provider_result(
    config: JsonObject,
    *,
    standard_id: str = "demo",
    version: str = "1.1",
    selector: str = "latest",
    recognized_settings: tuple[str, ...] = (),
    claims: tuple[LegacyClaim, ...] = (),
    findings: tuple[MigrationFinding, ...] = (),
) -> ProviderResult:
    return ProviderResult(
        effect=ProviderEffect.MIGRATION_REPORT,
        migration_report=MigrationReport(
            schema_version="1.0",
            package=MigratedPackage.model_validate(
                {
                    "standard_id": standard_id,
                    "version": version,
                    "selector": selector,
                    "config": config,
                    "recognized_settings": recognized_settings,
                }
            ),
            claims=claims,
            findings=findings,
        ),
    )


def test_direct_config_upgrade__applied_edge__plans_redacted_config_first_transform(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    control = repo / ".standards"
    control.mkdir(parents=True)
    config_path = control / "config.toml"
    config_path.write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path)
    lock = _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE))
    calls: list[ProviderInvocation] = []

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(source, target, desired, lock),
            payloads=(source, target),
            provider_runner=_runner(calls),
        )
    )

    assert plan.applicable, plan.findings
    assert [
        (
            invocation.standard_id,
            invocation.version.value,
            invocation.provider_id,
            invocation.operation,
            invocation.effective_config,
        )
        for invocation in calls
    ] == [
        (
            "demo",
            "1.1",
            "migrate-config",
            ProviderOperation.MIGRATE,
            _SOURCE_EFFECTIVE,
        ),
        (
            "demo",
            "1.1",
            "migrate-config",
            ProviderOperation.MIGRATE,
            _SOURCE_EFFECTIVE,
        ),
    ]
    transform_snapshot = cast(
        JsonObject,
        calls[0].snapshots["configuration_transform"],
    )
    assert transform_snapshot["raw_config"] == desired.standards["demo"].config
    assert transform_snapshot["declared_pointers"] == ["/ci/performance"]
    assert [action.target for action in plan.actions[:2]] == [
        ".standards/config.toml",
        "generated.txt",
    ]
    assert [target.target for target in plan.targets[:2]] == [
        ".standards/config.toml",
        "generated.txt",
    ]
    config_action = plan.actions[0]
    transformed = plan.proposed_content(".standards/config.toml")
    transformed_desired = parse_config(transformed)
    assert transformed_desired.standards["demo"].config == _TRANSFORMED_CONFIG
    assert transformed.replace(b", performance = true", b"", 1) == _CONFIG
    assert config_action.before_digest == content_digest(_CONFIG).value
    assert config_action.after_digest == content_digest(transformed).value
    assert plan.next_lock.project_standards.config_digest == semantic_digest(
        cast(JsonValue, transformed_desired.model_dump(mode="json"))
    )

    assert len(plan.configuration_transforms) == 1
    evidence = plan.configuration_transforms[0]
    assert (
        evidence.standard_id,
        evidence.migration_id,
        evidence.source,
        evidence.target,
        evidence.provider_id,
        evidence.declared_pointers,
        evidence.changed_pointers,
        evidence.before_digest,
        evidence.after_digest,
    ) == (
        "demo",
        "demo-1-0-to-1-1",
        "1.0",
        "1.1",
        "migrate-config",
        ("/ci/performance",),
        ("/ci/performance",),
        semantic_digest(
            cast(
                JsonValue,
                {
                    "additional_source_roots": [{"path": "src"}],
                    "ci": {"enabled": True},
                },
            )
        ).value,
        semantic_digest(cast(JsonValue, _TRANSFORMED_CONFIG)).value,
    )
    public_evidence = cast(
        "list[dict[str, JsonValue]]",
        plan.to_jsonable()["configuration_transforms"],
    )
    assert public_evidence == [asdict(evidence)]
    assert "true" not in json.dumps(public_evidence).casefold()
    assert "false" not in json.dumps(public_evidence).casefold()

    config_path.write_bytes(transformed)
    (repo / "generated.txt").write_bytes(plan.proposed_content("generated.txt"))
    settled = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(
                source,
                target,
                transformed_desired,
                plan.next_lock,
            ),
            payloads=(source, target),
            provider_runner=_runner(calls),
        )
    )

    assert settled.applicable, settled.findings
    assert settled.configuration_transforms == ()
    assert all(action.target != ".standards/config.toml" for action in settled.actions)
    assert all(action.kind is ActionKind.NOOP for action in settled.actions)
    assert settled.next_lock == plan.next_lock
    assert len(calls) == 2


def test_direct_config_upgrade__empty_diff__upgrades_without_config_action(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "empty-diff"
    control = repo / ".standards"
    control.mkdir(parents=True)
    config_path = control / "config.toml"
    config_path.write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / "empty-diff")
    lock = _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE))
    calls: list[ProviderInvocation] = []

    def unchanged(invocation: ProviderInvocation, _call: int) -> ProviderResult:
        snapshot = cast(JsonObject, invocation.snapshots["configuration_transform"])
        return _provider_result(
            cast(JsonObject, snapshot["raw_config"]),
            recognized_settings=(),
        )

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(source, target, desired, lock),
            payloads=(source, target),
            provider_runner=_runner(calls, unchanged),
        )
    )

    assert plan.applicable, plan.findings
    assert len(calls) == 2
    assert config_path.read_bytes() == _CONFIG
    assert all(action.target != ".standards/config.toml" for action in plan.actions)
    assert all(target.target != ".standards/config.toml" for target in plan.targets)
    assert plan.next_lock.standards["demo"].resolved == PackageVersion("1.1")
    assert plan.next_lock.project_standards.config_digest == lock.project_standards.config_digest
    assert any(action.target == "generated.txt" for action in plan.actions)
    (evidence,) = plan.configuration_transforms
    assert evidence.changed_pointers == ()
    assert evidence.before_digest == evidence.after_digest
    public = cast(
        "list[dict[str, JsonValue]]",
        plan.to_jsonable()["configuration_transforms"],
    )
    assert public == [asdict(evidence)]
    assert "true" not in json.dumps(public).casefold()
    assert "false" not in json.dumps(public).casefold()


def test_direct_config_upgrade__missing_container__adds_only_declared_leaf(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "missing-container"
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG_WITHOUT_CI)
    desired = parse_config(_CONFIG_WITHOUT_CI)
    source, target = _payloads(tmp_path / "missing-container")
    source_effective: JsonObject = {
        "additional_source_roots": [],
        "ci": {"enabled": True, "performance": True},
    }
    lock = _lock(desired, applied=_applied(source, source_effective))
    calls: list[ProviderInvocation] = []
    expected: JsonObject = {
        "additional_source_roots": [{"path": "src"}],
        "ci": {"performance": True},
    }

    def add_leaf(invocation: ProviderInvocation, call: int) -> ProviderResult:
        snapshot = cast(JsonObject, invocation.snapshots["configuration_transform"])
        raw = cast(JsonObject, snapshot["raw_config"])
        if call == 1:
            return _provider_result(
                expected,
                recognized_settings=("/ci/performance",),
            )
        assert raw == expected
        return _provider_result(expected)

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(source, target, desired, lock),
            payloads=(source, target),
            provider_runner=_runner(calls, add_leaf),
        )
    )

    assert len(calls) == 2
    assert plan.configuration_transforms[0].changed_pointers == ("/ci/performance",)
    transformed = parse_config(plan.proposed_content(".standards/config.toml"))
    assert transformed.standards["demo"].config == expected


def test_direct_config_upgrade__explicit_target_only_enum__remains_authoritative(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "explicit-target-enum"
    control = repo / ".standards"
    control.mkdir(parents=True)
    config_path = control / "config.toml"
    config_path.write_bytes(_CONFIG_WITH_EXPLICIT_TARGET_ENUM)
    desired = parse_config(_CONFIG_WITH_EXPLICIT_TARGET_ENUM)
    source, target = _payloads(
        tmp_path / "explicit-target-enum",
        source_performance_default=False,
        target_performance_default=False,
        source_performance_enum=(False,),
        target_performance_enum=(False, True),
    )
    source_effective: JsonObject = {
        "additional_source_roots": [],
        "ci": {"enabled": True, "performance": False},
    }
    lock = _lock(desired, applied=_applied(source, source_effective))
    calls: list[ProviderInvocation] = []

    def preserve(invocation: ProviderInvocation, _call: int) -> ProviderResult:
        snapshot = cast(JsonObject, invocation.snapshots["configuration_transform"])
        return _provider_result(cast(JsonObject, snapshot["raw_config"]))

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(source, target, desired, lock),
            payloads=(source, target),
            provider_runner=_runner(calls, preserve),
        )
    )

    assert len(calls) == 2
    assert plan.configuration_transforms[0].changed_pointers == ()
    assert all(action.target != ".standards/config.toml" for action in plan.actions)
    assert config_path.read_bytes() == _CONFIG_WITH_EXPLICIT_TARGET_ENUM


def test_direct_config_upgrade__stale_config_fails_before_publication(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "stale-config"
    control = repo / ".standards"
    control.mkdir(parents=True)
    config_path = control / "config.toml"
    config_path.write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / "stale-config")
    lock = _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE))
    lock_content = render_lock(lock)
    (control / "lock.toml").write_bytes(lock_content)
    calls: list[ProviderInvocation] = []
    planner = PlannerRequest(
        repo=repo,
        resolution=_resolution(source, target, desired, lock),
        payloads=(source, target),
        provider_runner=_runner(calls),
    )
    plan = plan_reconciliation(planner)
    concurrent = _CONFIG + b"# concurrent owner edit\n"

    def race(phase: str, identity: str) -> None:
        if (phase, identity) == ("precondition", ".standards/config.toml"):
            config_path.write_bytes(concurrent)

    result = apply_reconciliation(ApplyRequest(planner, plan, fault_hook=race))

    assert not result.success
    assert result.error_code == "CP-PRECONDITION"
    assert result.applied_action_ids == ()
    assert not result.lock_written
    assert config_path.read_bytes() == concurrent
    assert (control / "lock.toml").read_bytes() == lock_content
    assert not (repo / "generated.txt").exists()


def test_direct_config_upgrade__published_config_prefix__resumes_to_fixed_point(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "resume"
    control = repo / ".standards"
    control.mkdir(parents=True)
    config_path = control / "config.toml"
    config_path.write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / "resume")
    source_lock = _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE))
    source_lock_content = render_lock(source_lock)
    lock_path = control / "lock.toml"
    lock_path.write_bytes(source_lock_content)
    calls: list[ProviderInvocation] = []
    planner = PlannerRequest(
        repo=repo,
        resolution=_resolution(source, target, desired, source_lock),
        payloads=(source, target),
        provider_runner=_runner(calls),
    )
    plan = plan_reconciliation(planner)

    def interrupt_after_config(phase: str, identity: str) -> None:
        if (phase, identity) == ("precondition", "generated.txt"):
            raise PermissionError("injected after config publication")

    interrupted = apply_reconciliation(
        ApplyRequest(planner, plan, fault_hook=interrupt_after_config)
    )

    assert not interrupted.success
    assert interrupted.applied_action_ids == (".standards/config.toml",)
    assert not interrupted.lock_written
    transformed = config_path.read_bytes()
    assert transformed != _CONFIG
    assert lock_path.read_bytes() == source_lock_content
    assert not (repo / "generated.txt").exists()

    transformed_desired = parse_config(transformed)
    resume_calls: list[ProviderInvocation] = []
    resume_planner = PlannerRequest(
        repo=repo,
        resolution=_resolution(
            source,
            target,
            transformed_desired,
            source_lock,
        ),
        payloads=(source, target),
        provider_runner=_runner(resume_calls),
    )
    resume_plan = plan_reconciliation(resume_planner)

    assert len(resume_calls) == 2
    assert resume_plan.configuration_transforms[0].changed_pointers == ()
    assert all(action.target != ".standards/config.toml" for action in resume_plan.actions)
    resumed = apply_reconciliation(ApplyRequest(resume_planner, resume_plan))
    assert resumed.success
    assert resumed.applied_action_ids == ("generated.txt",)
    assert resumed.lock_written
    assert config_path.read_bytes() == transformed

    final_lock = parse_lock(lock_path.read_bytes())
    final_plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(
                source,
                target,
                transformed_desired,
                final_lock,
            ),
            payloads=(source, target),
            provider_runner=_runner([]),
        )
    )
    assert final_plan.configuration_transforms == ()
    assert all(action.kind is ActionKind.NOOP for action in final_plan.actions)
    assert final_plan.next_lock == final_lock


def test_direct_config_upgrade__cli_check_matches_programmatic_plan(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "cli-check"
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / "cli-check")
    lock = _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE))
    (control / "lock.toml").write_bytes(render_lock(lock))
    planner = PlannerRequest(
        repo=repo,
        resolution=_resolution(source, target, desired, lock),
        payloads=(source, target),
        provider_runner=_runner([]),
    )
    programmatic = plan_reconciliation(planner)
    distribution_root = tmp_path / "distribution"
    distribution_root.mkdir()
    distribution = InstalledDistribution(distribution_root, tool_release="5.9.0")

    def initialized_state(_repo: Path, *, tool_release: str) -> ControlPlaneState:
        assert tool_release == "5.9.0"
        return ControlPlaneState(StateKind.INITIALIZED, repo)

    def synthetic_planner(
        _repo: Path,
        _distribution: InstalledDistribution,
        _allowed_majors: frozenset[MajorAuthorization],
        *,
        state: ControlPlaneState | None = None,
        advance: CatalogAdvance = CatalogAdvance.NON_ADVANCING,
    ) -> PlannerRequest:
        assert state is None
        assert advance is CatalogAdvance.NON_ADVANCING
        return planner

    monkeypatch.setattr(
        control_cli,
        "detect_control_plane_state",
        initialized_state,
    )
    monkeypatch.setattr(
        control_cli,
        "build_planner_request",
        synthetic_planner,
    )

    exit_code = control_cli.run(
        ["--repo", str(repo), "--check", "--json"],
        distribution=distribution,
    )
    emitted = cast("dict[str, object]", json.loads(capsys.readouterr().out))

    assert exit_code == 1
    assert emitted["mode"] == "check"
    assert emitted["drift"] is True
    assert emitted["plan"] == json.loads(json.dumps(programmatic.to_jsonable()))


@pytest.mark.parametrize(
    ("failure", "error_type", "message"),
    [
        pytest.param("exception", ControlPlaneError, "provider failed", id="exception"),
        pytest.param("wrong-effect", ControlPlaneError, "wrong effect", id="wrong-effect"),
        pytest.param("identity", ControlPlaneError, "identity", id="identity"),
        pytest.param("claim", ControlPlaneError, "legacy evidence", id="claim"),
        pytest.param("finding", ControlPlaneError, "legacy evidence", id="finding"),
        pytest.param(
            "recognized-pointer",
            ControlPlaneError,
            "outside its declaration",
            id="recognized-pointer",
        ),
        pytest.param(
            "target-invalid",
            PackageContractError,
            "package options violate schema",
            id="target-invalid",
        ),
        pytest.param(
            "malicious-replacement",
            ControlPlaneError,
            "cannot remove",
            id="malicious-replacement",
        ),
        pytest.param(
            "non-idempotent",
            ControlPlaneError,
            "not idempotent",
            id="non-idempotent",
        ),
    ],
)
def test_direct_config_upgrade__invalid_provider_result__fails_before_writes(
    tmp_path: Path,
    failure: str,
    error_type: type[Exception],
    message: str,
) -> None:
    repo = tmp_path / failure
    control = repo / ".standards"
    control.mkdir(parents=True)
    config_path = control / "config.toml"
    config_path.write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / failure)
    lock = _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE))
    calls: list[ProviderInvocation] = []

    def invalid(_invocation: ProviderInvocation, call: int) -> ProviderResult:
        if failure == "exception":
            raise ControlPlaneError("provider failed with RuntimeError")
        if failure == "wrong-effect":
            return ProviderResult(ProviderEffect.CONTENT, content=b"unexpected")
        if failure == "identity":
            return _provider_result(
                _TRANSFORMED_CONFIG,
                standard_id="other",
                recognized_settings=("/ci/performance",),
            )
        if failure == "claim":
            claim = LegacyClaim.model_validate(
                {
                    "signature_id": "legacy-demo",
                    "target": "legacy.txt",
                    "observed_digest": f"sha256:{'a' * 64}",
                    "ownership": "managed",
                    "disposition": "preserve",
                }
            )
            return _provider_result(
                _TRANSFORMED_CONFIG,
                recognized_settings=("/ci/performance",),
                claims=(claim,),
            )
        if failure == "finding":
            finding = MigrationFinding.model_validate(
                {
                    "code": "DEMO-INVALID",
                    "severity": "error",
                    "path": "legacy.txt",
                    "identity": "legacy-demo",
                }
            )
            return _provider_result(
                _TRANSFORMED_CONFIG,
                recognized_settings=("/ci/performance",),
                findings=(finding,),
            )
        if failure == "recognized-pointer":
            return _provider_result(
                _TRANSFORMED_CONFIG,
                recognized_settings=("/ci/enabled",),
            )
        if failure == "target-invalid":
            invalid_target: JsonObject = {
                "additional_source_roots": [{"path": "src"}],
                "ci": {"enabled": True, "performance": "invalid"},
            }
            return _provider_result(
                invalid_target,
                recognized_settings=("/ci/performance",),
            )
        if failure == "malicious-replacement":
            return _provider_result(
                {"ci": {"performance": True}},
                recognized_settings=("/ci/performance",),
            )
        assert failure == "non-idempotent"
        if call == 1:
            return _provider_result(
                _TRANSFORMED_CONFIG,
                recognized_settings=("/ci/performance",),
            )
        changed_again: JsonObject = {
            "additional_source_roots": [{"path": "src"}],
            "ci": {"enabled": True, "performance": False},
        }
        return _provider_result(
            changed_again,
            recognized_settings=("/ci/performance",),
        )

    with pytest.raises(error_type, match=message):
        plan_reconciliation(
            PlannerRequest(
                repo=repo,
                resolution=_resolution(source, target, desired, lock),
                payloads=(source, target),
                provider_runner=_runner(calls, invalid),
            )
        )

    assert len(calls) == (2 if failure == "non-idempotent" else 1)
    assert config_path.read_bytes() == _CONFIG
    assert not (repo / "generated.txt").exists()


@pytest.mark.parametrize("authority", ["missing-source", "digest-mismatch"])
def test_direct_config_upgrade__inexact_source_authority__fails_before_provider(
    tmp_path: Path,
    authority: str,
) -> None:
    repo = tmp_path / authority
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / authority)
    applied = _applied(source, _SOURCE_EFFECTIVE)
    planner_payloads = (source, target)
    if authority == "missing-source":
        planner_payloads = (target,)
    else:
        applied = applied.model_copy(update={"payload_digest": Sha256Digest(f"sha256:{'f' * 64}")})
    calls: list[ProviderInvocation] = []

    with pytest.raises(ControlPlaneError, match="exact authoritative applied package evidence"):
        plan_reconciliation(
            PlannerRequest(
                repo=repo,
                resolution=_resolution(
                    source,
                    target,
                    desired,
                    _lock(desired, applied=applied),
                ),
                payloads=planner_payloads,
                provider_runner=_runner(calls),
            )
        )

    assert calls == []


def test_direct_config_upgrade__combined_successor_edit__requires_upgrade_then_adopt(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "upgrade-then-adopt"
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG_WITH_EXPLICIT_TARGET_ENUM)
    source_desired = parse_config(_SOURCE_COMPATIBLE_CONFIG)
    combined_desired = parse_config(_CONFIG_WITH_EXPLICIT_TARGET_ENUM)
    source, target = _payloads(
        tmp_path / "upgrade-then-adopt",
        source_roots_default=False,
    )
    source_schema = load_option_schema(source.root, source.manifest)
    source_effective = source_schema.resolve_options(source_desired.standards["demo"].config)
    source_lock = _lock(
        source_desired,
        applied=_applied(source, source_effective),
    )
    calls: list[ProviderInvocation] = []

    with pytest.raises(
        ControlPlaneError,
        match="reconcile the package upgrade first, then adopt the successor-only value",
    ):
        plan_reconciliation(
            PlannerRequest(
                repo=repo,
                resolution=_resolution(
                    source,
                    target,
                    combined_desired,
                    source_lock,
                ),
                payloads=(source, target),
                provider_runner=_runner(calls),
            )
        )

    assert calls == []
    assert (
        combined_desired.standards["demo"].config["ci"]
        == source_desired.standards["demo"].config["ci"]
    )

    config_path = control / "config.toml"
    lock_path = control / "lock.toml"
    config_path.write_bytes(_SOURCE_COMPATIBLE_CONFIG)
    lock_path.write_bytes(render_lock(source_lock))

    def unchanged(invocation: ProviderInvocation, _call: int) -> ProviderResult:
        snapshot = cast(JsonObject, invocation.snapshots["configuration_transform"])
        return _provider_result(
            cast(JsonObject, snapshot["raw_config"]),
            recognized_settings=(),
        )

    upgrade_planner = PlannerRequest(
        repo=repo,
        resolution=_resolution(source, target, source_desired, source_lock),
        payloads=(source, target),
        provider_runner=_runner([], unchanged),
    )
    upgraded = apply_reconciliation(
        ApplyRequest(upgrade_planner, plan_reconciliation(upgrade_planner))
    )
    assert upgraded.success

    upgraded_lock = parse_lock(lock_path.read_bytes())
    config_path.write_bytes(_CONFIG_WITH_EXPLICIT_TARGET_ENUM)
    adopt_planner = PlannerRequest(
        repo=repo,
        resolution=_resolution(source, target, combined_desired, upgraded_lock),
        payloads=(source, target),
        provider_runner=_runner([]),
    )
    adopted = apply_reconciliation(ApplyRequest(adopt_planner, plan_reconciliation(adopt_planner)))
    assert adopted.success

    final_lock = parse_lock(lock_path.read_bytes())
    settled = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(source, target, combined_desired, final_lock),
            payloads=(source, target),
            provider_runner=_runner([]),
        )
    )
    assert settled.configuration_transforms == ()
    assert all(action.kind is ActionKind.NOOP for action in settled.actions)
    assert parse_config(config_path.read_bytes()) == combined_desired


def test_direct_config_upgrade__multiple_applicable_transforms__fails_before_provider(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "multiple"
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / "multiple", transform_count=2)
    calls: list[ProviderInvocation] = []

    with pytest.raises(ControlPlaneError, match="more than one applicable config transform"):
        plan_reconciliation(
            PlannerRequest(
                repo=repo,
                resolution=_resolution(
                    source,
                    target,
                    desired,
                    _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE)),
                ),
                payloads=(source, target),
                provider_runner=_runner(calls),
            )
        )

    assert calls == []


@pytest.mark.parametrize("prior", ["fresh", "same-version"])
def test_direct_config_upgrade__inapplicable_prior__does_not_invoke_transform(
    tmp_path: Path,
    prior: str,
) -> None:
    repo = tmp_path / prior
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / prior)
    applied = (
        None
        if prior == "fresh"
        else _applied(
            target,
            {
                "ci": {
                    "enabled": True,
                    "performance": False,
                }
            },
        )
    )
    calls: list[ProviderInvocation] = []

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(source, target, desired, _lock(desired, applied=applied)),
            payloads=(source, target),
            provider_runner=_runner(calls),
        )
    )

    assert plan.applicable, plan.findings
    assert calls == []
    assert plan.configuration_transforms == ()
    assert all(action.target != ".standards/config.toml" for action in plan.actions)


@pytest.mark.parametrize(
    "edge",
    [
        pytest.param("automatic", id="non-opted-direct"),
        pytest.param("manual", id="manual-edge"),
    ],
)
def test_direct_config_upgrade__non_transform_edge__bypasses_provider(
    tmp_path: Path,
    edge: str,
) -> None:
    repo = tmp_path / edge
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source, opted_target = _payloads(tmp_path / edge)
    target = _target_without_transform(opted_target, manual=edge == "manual")
    calls: list[ProviderInvocation] = []

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=_resolution(
                source,
                target,
                desired,
                _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE)),
            ),
            payloads=(source, target),
            provider_runner=_runner(calls),
        )
    )

    assert plan.applicable, plan.findings
    assert calls == []
    assert plan.configuration_transforms == ()
    assert all(action.target != ".standards/config.toml" for action in plan.actions)


def test_direct_config_upgrade__multi_hop_path__bypasses_provider(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "multi-hop"
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG)
    desired = parse_config(_CONFIG)
    source = write_payload(
        tmp_path / "multi-hop" / "demo-1.0",
        "demo",
        version="1.0",
        option_properties=_options(performance_default=True, target_roots=False),
    )
    intermediate = write_payload(
        tmp_path / "multi-hop" / "demo-1.1",
        "demo",
        version="1.1",
        option_properties=_options(performance_default=True, target_roots=True),
    )
    target = _target_with_transform(
        write_payload(
            tmp_path / "multi-hop" / "demo-1.2",
            "demo",
            version="1.2",
            artifacts=[
                {
                    "id": "result",
                    "target": "generated.txt",
                    "content": b"selected 1.2\n",
                }
            ],
            option_properties=_options(performance_default=False, target_roots=True),
        ),
        source_version="1.1",
        target_version="1.2",
    )
    payloads = (source, intermediate, target)
    catalog = ConsumerCatalog.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "digest": f"sha256:{'a' * 64}",
            },
            "standards": {
                "demo": {
                    "status": "active",
                    "available": ["1.0", "1.1", "1.2"],
                    "default": "1.2",
                    "candidates": [],
                    "versions": {
                        version.manifest.payload.version.value: {
                            "channel": "stable" if version is target else "retained",
                            "availability": "consumer",
                            "payload_digest": version.integrity.aggregate_digest.value,
                        }
                        for version in payloads
                    },
                }
            },
        }
    )
    lock = _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE))
    resolution = ResolutionRequest(
        desired=desired,
        catalog=catalog,
        previous_lock=lock,
        allowed_majors=frozenset(),
        payloads=tuple(
            ResolutionPayload(
                standard_id="demo",
                version=payload.manifest.payload.version,
                payload_digest=payload.integrity.aggregate_digest,
                option_schema=load_option_schema(payload.root, payload.manifest),
            )
            for payload in payloads
        ),
        transition_paths=frozenset(
            {
                DeclaredTransition(
                    "demo",
                    PackageVersion("1.0"),
                    PackageVersion("1.1"),
                ),
                DeclaredTransition(
                    "demo",
                    PackageVersion("1.1"),
                    PackageVersion("1.2"),
                ),
            }
        ),
    )
    calls: list[ProviderInvocation] = []

    plan = plan_reconciliation(
        PlannerRequest(
            repo=repo,
            resolution=resolution,
            payloads=payloads,
            provider_runner=_runner(calls),
        )
    )

    assert plan.applicable, plan.findings
    assert calls == []
    assert plan.configuration_transforms == ()
    assert all(action.target != ".standards/config.toml" for action in plan.actions)


def test_direct_config_upgrade__inferred_only_authority__fails_before_provider(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "inferred-only"
    control = repo / ".standards"
    control.mkdir(parents=True)
    (control / "config.toml").write_bytes(_CONFIG)
    existing = b"selected 1.0\n"
    (repo / "generated.txt").write_bytes(existing)
    desired = parse_config(_CONFIG)
    source, target = _payloads(tmp_path / "inferred-only")
    recorded = content_digest(existing).value
    lock_document = _lock(desired, applied=None).model_dump(mode="json")
    lock_document["artifacts"] = [
        locked_unit(
            path="generated.txt",
            adapter="whole-file",
            scope="$file",
            owners=["demo"],
            semantic_digest=recorded,
            content_digest=recorded,
        )
    ]
    lock = CentralLock.model_validate(lock_document)
    calls: list[ProviderInvocation] = []

    with pytest.raises(ControlPlaneError):
        plan_reconciliation(
            PlannerRequest(
                repo=repo,
                resolution=_resolution(source, target, desired, lock),
                payloads=(source, target),
                provider_runner=_runner(calls),
            )
        )

    assert calls == []


def test_direct_config_upgrade__raw_target_invalid__fails_before_provider(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "raw-target-invalid"
    control = repo / ".standards"
    control.mkdir(parents=True)
    invalid_config = _CONFIG.replace(
        b"ci = { enabled = true }",
        b'ci = { enabled = true, performance = "invalid" }',
    )
    (control / "config.toml").write_bytes(invalid_config)
    desired = parse_config(invalid_config)
    source, target = _payloads(tmp_path / "raw-target-invalid")
    calls: list[ProviderInvocation] = []

    with pytest.raises(
        ControlPlaneConfigurationError,
        match="configured package options are invalid",
    ):
        plan_reconciliation(
            PlannerRequest(
                repo=repo,
                resolution=_resolution(
                    source,
                    target,
                    desired,
                    _lock(desired, applied=_applied(source, _SOURCE_EFFECTIVE)),
                ),
                payloads=(source, target),
                provider_runner=_runner(calls),
            )
        )

    assert calls == []


def test_direct_config_upgrade__explicit_declared_pointer_change__is_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "explicit-declared-pointer"
    control = repo / ".standards"
    control.mkdir(parents=True)
    explicit_config = _CONFIG.replace(
        b"ci = { enabled = true }",
        b"ci = { enabled = true, performance = false }",
    )
    (control / "config.toml").write_bytes(explicit_config)
    desired = parse_config(explicit_config)
    source, target = _payloads(tmp_path / "explicit-declared-pointer")
    source_effective: JsonObject = {
        "additional_source_roots": [],
        "ci": {"enabled": True, "performance": False},
    }
    calls: list[ProviderInvocation] = []

    def alter_explicit(_invocation: ProviderInvocation, _call: int) -> ProviderResult:
        return _provider_result(
            _TRANSFORMED_CONFIG,
            recognized_settings=("/ci/performance",),
        )

    with pytest.raises(ControlPlaneError, match="changed an explicit consumer option"):
        plan_reconciliation(
            PlannerRequest(
                repo=repo,
                resolution=_resolution(
                    source,
                    target,
                    desired,
                    _lock(desired, applied=_applied(source, source_effective)),
                ),
                payloads=(source, target),
                provider_runner=_runner(calls, alter_explicit),
            )
        )

    assert len(calls) == 1
