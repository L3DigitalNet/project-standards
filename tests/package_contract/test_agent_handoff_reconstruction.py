from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import cast

import pytest

from project_standards.agent_handoff.model import Harness, StartupMode
from project_standards.agent_handoff.planning import apply_adoption, plan_adoption
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import (
    ApplyRequest,
    apply_authoring_plan,
    apply_reconciliation,
)
from project_standards.control_plane.migration import apply_legacy_migration, plan_legacy_migration
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.control_plane.snapshot import RepositorySnapshot
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    JsonObject,
    JsonValue,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PAYLOAD = _FAMILY / "versions/1.1"


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    return InstalledPayload(_PAYLOAD, manifest, validate_payload_integrity(_PAYLOAD, manifest))


def _options(**overrides: object) -> JsonObject:
    payload = _payload()
    schema = load_option_schema(_PAYLOAD, payload.manifest)
    return schema.resolve_options(cast("JsonObject", overrides))


def _render(
    target: str,
    adapter: AdapterKind,
    scope: str,
    config: JsonObject,
) -> str:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_PAYLOAD,
            payload=payload,
            standard_id="agent-handoff",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={
                "planned_contribution": {
                    "id": "test-unit",
                    "target": target,
                    "adapter": adapter.value,
                    "scope": scope,
                }
            },
        )
    )
    assert result.effect is ProviderEffect.CONTENT
    assert result.content is not None
    return result.content.decode()


def _invoke(
    provider_id: str,
    operation: ProviderOperation,
    config: JsonObject,
    repo: Path,
    snapshots: JsonObject,
    *,
    payload: InstalledPayload | None = None,
):
    selected = payload or _payload()
    return invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=selected,
            standard_id="agent-handoff",
            version=selected.manifest.payload.version,
            provider_id=provider_id,
            operation=operation,
            effective_config=config,
            snapshots=snapshots,
        )
    )


def _content_snapshot(content: bytes, *, mode: str | None = None) -> JsonObject:
    return {
        "kind": "regular",
        "content_digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "content_base64": base64.b64encode(content).decode("ascii"),
        "mode": mode,
    }


def _valid_handoff_snapshots(config: JsonObject) -> JsonObject:
    snapshots: JsonObject = {}
    manifest = _payload().manifest
    managed_units: list[JsonValue] = []
    for artifact in manifest.artifacts:
        if not artifact.materializes(config):
            continue
        snapshots[artifact.target.original] = _content_snapshot(
            (_PAYLOAD / artifact.source.normalized).read_bytes(),
            mode=artifact.mode,
        )
    snapshots["docs/handoff/sessions"] = {"kind": "directory"}
    snapshots["docs/handoff/bugs"] = {"kind": "directory"}
    for contribution in manifest.contributions:
        if not contribution.materializes(config):
            continue
        rendered = _render(
            contribution.target.original,
            contribution.adapter,
            contribution.scope,
            config,
        ).encode()
        snapshots[contribution.target.original] = _content_snapshot(rendered)
        managed_units.append(
            {
                "target": contribution.target.original,
                "adapter": contribution.adapter.value,
                "scope": contribution.scope,
            }
        )
    snapshots["managed_units"] = managed_units
    return snapshots


def _installed_distribution(tmp_path: Path) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    repository = copy_minimal_repository(fixture)
    family = repository / "standards/agent-handoff"
    shutil.copytree(_FAMILY, family)
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    integrity = validate_payload_integrity(_PAYLOAD, manifest)
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "agent-handoff"
name = "Agent Handoff"
summary = "Repository-local agent continuity."
status = "active"

[[versions]]
version = "1.1"
payload = "versions/1.1/payload.toml"
digest = "{integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "agent-handoff"
version = "1.1"
digest = "{integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def test_agent_handoff_options_are_closed_and_profiles_are_consistent() -> None:
    assert _options() == {
        "contract_version": "1.1",
        "startup": "automatic",
        "harnesses": ["claude-code", "codex"],
    }
    assert _options(contract_version="1.0")["contract_version"] == "1.0"
    assert _options(startup="manual", harnesses=[]) == {
        "contract_version": "1.1",
        "startup": "manual",
        "harnesses": [],
    }
    assert _options(startup="automatic", harnesses=["codex"])["harnesses"] == ["codex"]

    invalid: tuple[JsonObject, ...] = (
        {"unknown": True},
        {"contract_version": "2.0"},
        {"startup": "manual", "harnesses": ["codex"]},
        {"startup": "automatic", "harnesses": []},
        {"startup": "automatic", "harnesses": ["codex", "codex"]},
        {"startup": "automatic", "harnesses": ["unknown"]},
    )
    payload = _payload()
    schema = load_option_schema(_PAYLOAD, payload.manifest)
    for options in invalid:
        with pytest.raises(PackageContractError, match="package options violate schema"):
            schema.resolve_options(options)


def test_agent_handoff_manifest_separates_consumer_knowledge_and_managed_state() -> None:
    manifest = _payload().manifest
    create_only = {
        artifact.target.original
        for artifact in manifest.artifacts
        if artifact.policy is ArtifactPolicy.CREATE_ONLY
    }
    assert create_only == {
        "docs/STATUS.md",
        "docs/TODO.md",
        "docs/handoff/architecture.md",
        "docs/handoff/bugs/.gitkeep",
        "docs/handoff/conventions.md",
        "docs/handoff/credentials.md",
        "docs/handoff/deployed.md",
        "docs/handoff/sessions/.gitkeep",
        "docs/handoff/specs-plans.md",
        "docs/handoff/state.md",
    }
    managed = {
        artifact.target.original
        for artifact in manifest.artifacts
        if artifact.policy is ArtifactPolicy.MANAGED
    }
    assert ".standards/packages/agent-handoff/policy.toml" in managed
    assert ".agents/agent-handoff/manifest.json" not in managed
    assert {
        ".agents/hooks/agent-handoff/session_start.py",
        ".agents/skills/agent-handoff/SKILL.md",
        ".agents/skills/agent-handoff/agents/openai.yaml",
    }.issubset(managed)

    scopes = {(item.target.original, item.adapter, item.scope) for item in manifest.contributions}
    assert ("AGENTS.md", AdapterKind.MARKDOWN_BLOCK, "block:agent-handoff") in scopes
    assert ("CLAUDE.md", AdapterKind.MARKDOWN_BLOCK, "block:agent-handoff") in scopes
    assert (
        ".claude/settings.json",
        AdapterKind.JSONC,
        "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
    ) in scopes
    assert (
        ".codex/config.toml",
        AdapterKind.TOML,
        "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
    ) in scopes

    declarations = {item.id: item for item in (*manifest.artifacts, *manifest.contributions)}
    assert declarations["hook"].when_any[0].option == "startup"
    assert declarations["claude-session-start"].when_any[0].contains == "claude-code"
    assert declarations["codex-session-start"].when_any[0].contains == "codex"


def test_agent_handoff_profile_renders_bounded_active_integrations() -> None:
    config = _options()
    claude = json.loads(
        _render(
            ".claude/settings.json",
            AdapterKind.JSONC,
            "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
            config,
        )
    )
    handlers = claude["hooks"]["SessionStart"][0]["hooks"]
    assert ".agents/hooks/agent-handoff/session_start.py" in handlers[0]["command"]
    codex = _render(
        ".codex/config.toml",
        AdapterKind.TOML,
        "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
        config,
    )
    assert "session_start.py" in codex
    assert "[[hooks.SessionStart]]" in codex

    instructions = _render(
        "AGENTS.md",
        AdapterKind.MARKDOWN_BLOCK,
        "block:agent-handoff",
        config,
    )
    assert "BEGIN project-standards:agent-handoff" in instructions
    assert "BEGIN agent-handoff managed instructions" not in instructions


def test_agent_handoff_fresh_reconcile_preserves_knowledge_and_converges(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    (repo / "docs").mkdir(parents=True)
    status = b"# Consumer status\n\nPreserve this knowledge.\n"
    (repo / "docs/STATUS.md").write_bytes(status)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "agent-handoff", True)

    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success, result

    assert (repo / "docs/STATUS.md").read_bytes() == status
    assert (repo / "docs/TODO.md").exists()
    assert (repo / ".agents/hooks/agent-handoff/session_start.py").stat().st_mode & 0o777 == 0o755
    assert (repo / ".agents/skills/agent-handoff/SKILL.md").exists()
    assert (repo / ".standards/packages/agent-handoff/policy.toml").exists()
    assert not (repo / ".agents/agent-handoff/manifest.json").exists()
    assert "BEGIN project-standards:agent-handoff" in (repo / "AGENTS.md").read_text(
        encoding="utf-8"
    )

    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


def test_agent_handoff_post_publish_semantic_tamper_blocks_lock(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "agent-handoff", True)
    previous_lock = (repo / ".standards/lock.toml").read_bytes()
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)

    def tamper(phase: str, identity: str) -> None:
        if (phase, identity) == ("published", "AGENTS.md"):
            (repo / "AGENTS.md").write_text("tampered after publication\n", encoding="utf-8")

    result = apply_reconciliation(ApplyRequest(request, plan, fault_hook=tamper))

    assert not result.success
    assert result.error_code == "CP-VERIFY"
    assert not result.lock_written
    assert (repo / ".standards/lock.toml").read_bytes() == previous_lock


def test_agent_handoff_scaffold_and_upgrade_return_executor_only_typed_plans(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    target = "docs/handoff/state.md"
    entry = RepositorySnapshot.capture(repo, (SafeRelativePath.parse(target),)).entries[0]
    scaffold = _invoke(
        "scaffold",
        ProviderOperation.SCAFFOLD,
        _options(),
        repo,
        {
            "authoring": {
                "target": target,
                "kind": entry.kind.value,
                "precondition_digest": entry.precondition_digest.value,
                "mode": entry.mode,
                "overwrite": False,
                "resource_id": "template-state",
            }
        },
    )
    assert scaffold.effect is ProviderEffect.MUTATION_PLAN
    assert scaffold.mutation_plan is not None
    assert not (repo / target).exists()
    assert apply_authoring_plan(repo, scaffold.mutation_plan).success
    assert (repo / target).read_bytes() == (
        _PAYLOAD / "provider-resources/templates/state.md"
    ).read_bytes()

    skill = repo / ".agents/skills/agent-handoff/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("old managed skill\n", encoding="utf-8")
    relative_skill = ".agents/skills/agent-handoff/SKILL.md"
    current = RepositorySnapshot.capture(repo, (SafeRelativePath.parse(relative_skill),)).entries[0]
    upgrade = _invoke(
        "upgrade",
        ProviderOperation.UPGRADE,
        _options(),
        repo,
        {
            "authoring": {
                "target": relative_skill,
                "kind": current.kind.value,
                "precondition_digest": current.precondition_digest.value,
                "mode": current.mode,
                "overwrite": True,
                "resource_id": "skill",
            }
        },
    )
    assert upgrade.mutation_plan is not None
    assert skill.read_text(encoding="utf-8") == "old managed skill\n"
    assert apply_authoring_plan(repo, upgrade.mutation_plan).success
    assert skill.read_bytes() == (_PAYLOAD / "provider-resources/managed/skill.md").read_bytes()


@pytest.mark.parametrize(
    ("provider_id", "authoring"),
    [
        (
            "scaffold",
            {
                "target": "README.md",
                "kind": "missing",
                "precondition_digest": f"sha256:{'0' * 64}",
                "mode": None,
                "overwrite": False,
                "resource_id": "template-state",
            },
        ),
        (
            "scaffold",
            {
                "target": "docs/handoff/state.md",
                "kind": "missing",
                "precondition_digest": f"sha256:{'0' * 64}",
                "mode": None,
                "overwrite": False,
                "resource_id": "template-status",
            },
        ),
        (
            "upgrade",
            {
                "target": ".agents/hooks/agent-handoff/session_start.py",
                "kind": "regular",
                "precondition_digest": f"sha256:{'1' * 64}",
                "mode": "0644",
                "overwrite": True,
                "resource_id": "hook",
            },
        ),
    ],
)
def test_agent_handoff_authoring_rejects_unbound_targets_resources_and_modes(
    tmp_path: Path,
    provider_id: str,
    authoring: JsonObject,
) -> None:
    operation = (
        ProviderOperation.SCAFFOLD if provider_id == "scaffold" else ProviderOperation.UPGRADE
    )
    with pytest.raises(ControlPlaneError, match="provider failed with ValueError"):
        _invoke(provider_id, operation, _options(), tmp_path, {"authoring": authoring})


def test_agent_handoff_validate_enforces_layout_shape_credentials_and_integrations(
    tmp_path: Path,
) -> None:
    config = _options()
    valid = _invoke(
        "validate",
        ProviderOperation.VALIDATE,
        config,
        tmp_path,
        _valid_handoff_snapshots(config),
    )
    assert valid.findings == ()

    invalid = _valid_handoff_snapshots(config)
    invalid.pop("docs/TODO.md")
    invalid["docs/handoff/state.md"] = _content_snapshot(b"# State\n" + b"x" * 2200)
    invalid["docs/handoff/credentials.md"] = _content_snapshot(
        b'# Credentials\n\ntoken = "literal-secret-value"\n'
    )
    invalid["AGENTS.md"] = _content_snapshot(
        b"<!-- BEGIN project-standards:agent-handoff -->\nmalformed\n"
    )
    invalid[".claude/settings.json"] = _content_snapshot(
        b'{"hooks":{"SessionStart":[{"matcher":"startup|resume|clear|compact",'
        b'"hooks":[{"type":"command","command":"echo wrong","timeout":10,'
        b'"statusMessage":"Loading agent handoff state..."}]}]}}'
    )
    invalid[".codex/config.toml"] = _content_snapshot(
        b'[[hooks.SessionStart]]\nmatcher = "startup|resume|clear|compact"\n'
        b'[[hooks.SessionStart.hooks]]\ntype = "command"\ncommand = "echo wrong"\n'
        b'timeout = 10\nstatusMessage = "Loading agent handoff state..."\n'
    )
    result = _invoke(
        "validate",
        ProviderOperation.VALIDATE,
        config,
        tmp_path,
        invalid,
    )

    assert {
        "AH-LAYOUT-TODO-MISSING",
        "AH-SIZE-CAP",
        "AH-SECRET-LITERAL",
        "AH-INSTRUCTIONS-INVALID",
        "AH-CLAUDE-CONFIG-INVALID",
        "AH-CODEX-CONFIG-INVALID",
    }.issubset({finding.code for finding in result.findings})

    shape_invalid = _valid_handoff_snapshots(config)
    shape_invalid["docs/handoff/state.md"] = _content_snapshot(
        b"# Session State\n\n## Current focus\n\nNarrative is forbidden here.\n\n"
        b"## Active incidents\n\n- None.\n\n## Historical notes\n\n- Stale.\n"
    )
    shaped = _invoke(
        "validate",
        ProviderOperation.VALIDATE,
        config,
        tmp_path,
        shape_invalid,
    )
    assert "AH-SHAPE" in {finding.code for finding in shaped.findings}
    assert "AH-SIZE-CAP" not in {finding.code for finding in shaped.findings}


@pytest.mark.parametrize(
    ("config", "stale_paths"),
    [
        (
            _options(startup="manual", harnesses=[]),
            (
                ".agents/hooks/agent-handoff/session_start.py",
                ".codex/config.toml",
            ),
        ),
        (
            _options(startup="automatic", harnesses=["claude-code"]),
            ("AGENTS.md", ".codex/config.toml"),
        ),
        (
            _options(startup="automatic", harnesses=["codex"]),
            ("CLAUDE.md", ".claude/settings.json"),
        ),
    ],
)
def test_agent_handoff_drift_rejects_stale_inactive_profile_units(
    tmp_path: Path,
    config: JsonObject,
    stale_paths: tuple[str, ...],
) -> None:
    snapshots = _valid_handoff_snapshots(config)
    all_active = _valid_handoff_snapshots(_options())
    for path in stale_paths:
        snapshots[path] = all_active[path]

    drift = _invoke(
        "drift-check",
        ProviderOperation.DRIFT_CHECK,
        config,
        tmp_path,
        snapshots,
    )

    profile_findings = [finding for finding in drift.findings if finding.code == "AH-PROFILE-DRIFT"]
    assert {finding.path for finding in profile_findings} == set(stale_paths)


def test_agent_handoff_drift_and_extract_providers_are_read_only(tmp_path: Path) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    before = tuple(repo.iterdir())
    drift = _invoke(
        "drift-check",
        ProviderOperation.DRIFT_CHECK,
        _options(),
        repo,
        {
            path: {"kind": "missing", "content_digest": None, "mode": None}
            for path in (
                ".agents/hooks/agent-handoff/session_start.py",
                ".agents/skills/agent-handoff/SKILL.md",
                ".agents/skills/agent-handoff/agents/openai.yaml",
                ".standards/packages/agent-handoff/policy.toml",
            )
        },
    )
    assert {
        "AH-DRIFT",
        "AH-INSTRUCTIONS-INVALID",
        "AH-CLAUDE-CONFIG-INVALID",
        "AH-CODEX-CONFIG-INVALID",
    } == {finding.code for finding in drift.findings}
    extracted = _invoke(
        "extract",
        ProviderOperation.EXTRACT,
        _options(),
        repo,
        {"legacy_evidence": {"paths": ["docs/state.md"], "status": "review"}},
    )
    assert extracted.content is not None
    assert json.loads(extracted.content) == {
        "paths": ["docs/state.md"],
        "status": "review",
    }
    assert tuple(repo.iterdir()) == before


@pytest.mark.parametrize(
    ("startup", "harnesses", "claude_active", "codex_active"),
    [
        ("manual", [], False, False),
        ("automatic", ["claude-code"], True, False),
        ("automatic", ["codex"], False, True),
        ("automatic", ["claude-code", "codex"], True, True),
    ],
)
def test_agent_handoff_real_reconcile_supports_every_profile(
    tmp_path: Path,
    startup: str,
    harnesses: list[str],
    claude_active: bool,
    codex_active: bool,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    codex_path = repo / ".codex/config.toml"
    codex_path.parent.mkdir(parents=True)
    codex_path.write_text(
        """model = "consumer-model"

[[hooks.SessionStart]]
matcher = "consumer-event"
[[hooks.SessionStart.hooks]]
type = "command"
command = "echo consumer"
""",
        encoding="utf-8",
    )
    harnesses_toml = json.dumps(harnesses)
    (repo / ".standards/config.toml").write_text(
        f'''[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.agent-handoff]
enabled = true
version = "latest"

[standards.agent-handoff.config]
contract_version = "1.1"
startup = "{startup}"
harnesses = {harnesses_toml}
''',
        encoding="utf-8",
    )
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success

    hook = repo / ".agents/hooks/agent-handoff/session_start.py"
    assert hook.exists() is (startup == "automatic")
    claude_path = repo / ".claude/settings.json"
    assert claude_path.exists() is ("claude-code" in harnesses)
    if claude_path.exists():
        claude = json.loads(claude_path.read_text(encoding="utf-8"))
        assert bool(claude["hooks"]["SessionStart"][0]["hooks"]) is claude_active
    codex = codex_path.read_text(encoding="utf-8")
    assert ("session_start.py" in codex) is codex_active
    assert 'matcher = "consumer-event"' in codex
    assert 'command = "echo consumer"' in codex
    assert (repo / "AGENTS.md").exists() is (startup == "manual" or "codex" in harnesses)
    assert (repo / "CLAUDE.md").exists() is ("claude-code" in harnesses)


def test_agent_handoff_profile_transition_prunes_package_created_containers(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "agent-handoff", True)
    request = build_planner_request(repo, distribution, frozenset())
    assert apply_reconciliation(ApplyRequest(request, plan_reconciliation(request))).success

    (repo / ".standards/config.toml").write_text(
        """[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.agent-handoff]
enabled = true
version = "latest"

[standards.agent-handoff.config]
contract_version = "1.1"
startup = "manual"
harnesses = []
""",
        encoding="utf-8",
    )
    transition_request = build_planner_request(repo, distribution, frozenset())
    transition = plan_reconciliation(transition_request)
    assert transition.applicable, transition.findings
    assert apply_reconciliation(ApplyRequest(transition_request, transition)).success

    assert (repo / "AGENTS.md").exists()
    for path in (
        "CLAUDE.md",
        ".claude/settings.json",
        ".codex/config.toml",
        ".agents/hooks/agent-handoff/session_start.py",
    ):
        assert not (repo / path).exists(), path


def test_agent_handoff_disable_and_reenable_preserve_consumer_knowledge(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    codex = repo / ".codex/config.toml"
    codex.parent.mkdir(parents=True)
    consumer_hook = (
        '[[hooks.SessionStart]]\nmatcher = "consumer-event"\n'
        '[[hooks.SessionStart.hooks]]\ntype = "command"\ncommand = "echo consumer"\n'
    )
    codex.write_text(consumer_hook, encoding="utf-8")
    set_standard_enabled(repo, "agent-handoff", True)
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    state = repo / "docs/handoff/state.md"
    state.write_bytes(b"# Consumer state\n\nActive incident.\n")

    set_standard_enabled(repo, "agent-handoff", False)
    disable_request = build_planner_request(repo, distribution, frozenset())
    disable = plan_reconciliation(disable_request)
    assert disable.applicable, disable.findings
    assert apply_reconciliation(ApplyRequest(disable_request, disable)).success
    assert state.read_bytes() == b"# Consumer state\n\nActive incident.\n"
    assert not (repo / ".agents/skills/agent-handoff/SKILL.md").exists()
    assert not (repo / ".standards/packages/agent-handoff").exists()
    assert codex.read_text(encoding="utf-8").strip() == consumer_hook.strip()
    assert "project-standards:agent-handoff" not in (
        (repo / "AGENTS.md").read_text(encoding="utf-8") if (repo / "AGENTS.md").exists() else ""
    )

    set_standard_enabled(repo, "agent-handoff", True)
    enable_request = build_planner_request(repo, distribution, frozenset())
    enable = plan_reconciliation(enable_request)
    assert enable.applicable, enable.findings
    assert apply_reconciliation(ApplyRequest(enable_request, enable)).success
    assert state.read_bytes() == b"# Consumer state\n\nActive incident.\n"
    assert (repo / ".agents/skills/agent-handoff/SKILL.md").exists()
    assert "echo consumer" in codex.read_text(encoding="utf-8")
    assert "session_start.py" in codex.read_text(encoding="utf-8")


def test_agent_handoff_real_v4_migration_retires_lock_and_preserves_consumer_bytes(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    report = apply_adoption(
        plan_adoption(
            repository=repo,
            standard_ids=("agent-handoff",),
            startup=StartupMode.AUTOMATIC,
            harnesses=(Harness.CLAUDE_CODE, Harness.CODEX),
        ),
        dry_run=False,
    )
    assert not report.blocked
    project_config = repo / ".project-standards.yml"
    project_config.write_text(
        'standards_version: "v4"\n\n' + project_config.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    status = repo / "docs/STATUS.md"
    status.write_bytes(b"# Consumer knowledge\n\nNever replace this.\n")
    agents = repo / "AGENTS.md"
    agents.write_text(
        "Consumer instructions before.\n\n"
        + agents.read_text(encoding="utf-8")
        + "\nConsumer instructions after.\n",
        encoding="utf-8",
    )
    codex = repo / ".codex/config.toml"
    codex.write_text(
        'model = "consumer-model"\n\n' + codex.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    claude = repo / ".claude/settings.json"
    settings = json.loads(claude.read_text(encoding="utf-8"))
    settings["consumerSetting"] = True
    settings["hooks"]["SessionStart"].append(
        {
            "matcher": "consumer-event",
            "hooks": [{"type": "command", "command": "echo consumer"}],
        }
    )
    claude.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    migration = plan_legacy_migration(repo, distribution, "5")
    assert migration.applicable, migration.findings
    result = apply_legacy_migration(migration)
    assert result.success, result

    assert not (repo / ".project-standards.yml").exists()
    assert not (repo / ".agents/agent-handoff/manifest.json").exists()
    assert status.read_bytes() == b"# Consumer knowledge\n\nNever replace this.\n"
    instructions = agents.read_text(encoding="utf-8")
    assert "Consumer instructions before." in instructions
    assert "Consumer instructions after." in instructions
    assert "BEGIN project-standards:agent-handoff" in instructions
    assert "BEGIN agent-handoff managed instructions" not in instructions
    codex_text = codex.read_text(encoding="utf-8")
    assert 'model = "consumer-model"' in codex_text
    assert "BEGIN agent-handoff managed codex hook" not in codex_text
    assert "session_start.py" in codex_text
    migrated_settings = json.loads(claude.read_text(encoding="utf-8"))
    assert migrated_settings["consumerSetting"] is True
    assert any(
        group["matcher"] == "consumer-event" for group in migrated_settings["hooks"]["SessionStart"]
    )

    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


@pytest.mark.parametrize("mutation", ["version", "path", "digest"])
def test_agent_handoff_unknown_legacy_lock_facts_block_without_writes(
    tmp_path: Path,
    mutation: str,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    report = apply_adoption(
        plan_adoption(
            repository=repo,
            standard_ids=("agent-handoff",),
            startup=StartupMode.AUTOMATIC,
            harnesses=(Harness.CODEX,),
        ),
        dry_run=False,
    )
    assert not report.blocked
    project_config = repo / ".project-standards.yml"
    project_config.write_text(
        'standards_version: "v4"\n\n' + project_config.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    lock_path = repo / ".agents/agent-handoff/manifest.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if mutation == "version":
        lock["version"] = "9.9"
    elif mutation == "path":
        lock["managed"]["../outside"] = "0" * 64
    else:
        first = next(iter(lock["managed"]))
        lock["managed"][first] = "0" * 64
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    migration = plan_legacy_migration(repo, distribution, "5")
    assert not migration.applicable
    assert any(
        finding.code in {"AH-LEGACY-MODIFIED", "CP-MIGRATION-LEGACY-DIGEST"}
        and finding.path == ".agents/agent-handoff/manifest.json"
        for finding in migration.findings
    )
    assert not (repo / ".standards").exists()
    assert project_config.exists()


def test_agent_handoff_modified_managed_skill_blocks_migration_without_writes(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    report = apply_adoption(
        plan_adoption(
            repository=repo,
            standard_ids=("agent-handoff",),
            startup=StartupMode.MANUAL,
            harnesses=(),
        ),
        dry_run=False,
    )
    assert not report.blocked
    project_config = repo / ".project-standards.yml"
    project_config.write_text(
        'standards_version: "v4"\n\n' + project_config.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    skill = repo / ".agents/skills/agent-handoff/SKILL.md"
    skill.write_bytes(skill.read_bytes() + b"\nConsumer modification.\n")

    migration = plan_legacy_migration(repo, distribution, "5")
    assert not migration.applicable
    assert any(finding.path == str(skill.relative_to(repo)) for finding in migration.findings)
    assert not (repo / ".standards").exists()


def test_agent_handoff_payload_is_byte_identical_in_built_wheel(tmp_path: Path) -> None:
    project = copy_minimal_repository(tmp_path)
    family = project / "standards/agent-handoff"
    shutil.copytree(_FAMILY, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "agent-handoff"
name = "Agent Handoff"
summary = "Repository-local agent continuity."
status = "active"

[[versions]]
version = "1.1"
payload = "versions/1.1/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    package = project / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """[project]
name = "project-standards"
version = "5.0.0"
requires-python = ">=3.14"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**"]
""",
        encoding="utf-8",
    )
    assert sync_payload_projection(project, check=False) == ()
    distribution = project / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(distribution)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (wheel,) = distribution.glob("*.whl")
    prefix = "project_standards/payloads/agent-handoff/1.1/"
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
        extracted = tmp_path / "extracted"
        archive.extractall(extracted)
    source_files = {
        path.relative_to(_PAYLOAD).as_posix(): path.read_bytes()
        for path in _PAYLOAD.rglob("*")
        if path.is_file()
    }
    assert wheel_files == source_files

    installed_root = extracted / prefix
    installed_manifest = payload.manifest
    installed_payload = InstalledPayload(
        installed_root,
        installed_manifest,
        validate_payload_integrity(installed_root, installed_manifest),
    )
    with pytest.raises(ControlPlaneError, match="provider failed with ValueError"):
        _invoke(
            "scaffold",
            ProviderOperation.SCAFFOLD,
            _options(),
            tmp_path,
            {
                "authoring": {
                    "target": "README.md",
                    "kind": "missing",
                    "precondition_digest": f"sha256:{'0' * 64}",
                    "mode": None,
                    "overwrite": False,
                    "resource_id": "template-state",
                }
            },
            payload=installed_payload,
        )
    installed_validation = _invoke(
        "validate",
        ProviderOperation.VALIDATE,
        _options(),
        tmp_path,
        {},
        payload=installed_payload,
    )
    assert "AH-LAYOUT-STATUS-MISSING" in {finding.code for finding in installed_validation.findings}
    installed_shape_snapshots = _valid_handoff_snapshots(_options())
    installed_shape_snapshots["docs/handoff/state.md"] = _content_snapshot(
        b"# Session State\n\n## Current focus\n\nParagraph not allowed.\n\n"
        b"## Active incidents\n\n- None.\n\n## Extra\n\n- Invalid.\n"
    )
    installed_shape = _invoke(
        "validate",
        ProviderOperation.VALIDATE,
        _options(),
        tmp_path,
        installed_shape_snapshots,
        payload=installed_payload,
    )
    assert "AH-SHAPE" in {finding.code for finding in installed_shape.findings}


def test_agent_handoff_root_v1_manifest_is_unchanged() -> None:
    digest = hashlib.sha256((_FAMILY / "standard.toml").read_bytes()).hexdigest()
    assert digest == "14ee5d6ff52d33281859b7bf4d98fd5c31ff2f01a378dd0641bb6774068a9861"
