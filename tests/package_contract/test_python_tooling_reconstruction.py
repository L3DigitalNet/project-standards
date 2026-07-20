from __future__ import annotations

import ast
import json
import os
import shlex
import shutil
import subprocess
import sys
import tomllib
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import (
    MigrationReport,
    apply_legacy_migration,
    plan_legacy_migration,
)
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.planner_helpers import resolution_request, write_payload
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_PAYLOAD = _FAMILY / "versions/1.1"
_RELEASE_CURRENT_PRESERVED_CONTAINERS = {
    "legacy-agents": (
        "AGENTS.md",
        "sha256:b7b00e3bf4a74e47a19418979925260f73098734c805148ee31384f3e6571b2b",
    ),
    "legacy-claude": (
        "CLAUDE.md",
        "sha256:8c9ba6563c70ea051ad36f2054d41f36aa048ce61d813d100d4e7b25d5e05de0",
    ),
    "legacy-vscode-settings": (
        ".vscode/settings.json",
        "sha256:22f598ebf1f24e29041289891b3c56131f0acc4dddfed802d92a6a3802eab55f",
    ),
    "legacy-vscode-tasks": (
        ".vscode/tasks.json",
        "sha256:cf4aa30c3e2bfb1d69d0cfb7953d1e351db0e6ab06c5812f48cf9eface79a9f7",
    ),
}


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    return InstalledPayload(_PAYLOAD, manifest, validate_payload_integrity(_PAYLOAD, manifest))


def _options(**overrides: object) -> JsonObject:
    payload = _payload()
    schema = load_option_schema(_PAYLOAD, payload.manifest)
    return schema.resolve_options(cast("JsonObject", overrides))


def _render(
    scope: str,
    adapter: AdapterKind,
    config: JsonObject,
    *,
    target: str = "pyproject.toml",
) -> str:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_PAYLOAD,
            payload=payload,
            standard_id="python-tooling",
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


def _migration_report(
    payload: InstalledPayload,
    *,
    workflow_ownership: str,
    known: bool,
    digest: str,
) -> MigrationReport:
    result = invoke_provider(
        ProviderInvocation(
            repo=payload.root,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="migrate-legacy",
            operation=ProviderOperation.MIGRATE,
            effective_config={},
            snapshots={
                "legacy_config": {
                    "standards_version": "v4",
                    "python_tooling": {
                        "version": "1.0",
                        "workflow_ownership": workflow_ownership,
                    },
                },
                "legacy_signatures": {
                    "legacy-check-workflow": {
                        ".github/workflows/check.yml": {
                            "known": known,
                            "digest": digest,
                        }
                    }
                },
            },
        )
    )
    assert result.migration_report is not None
    return result.migration_report


def _legacy_container_report(
    payload: InstalledPayload,
    *,
    signature_id: str,
    target: str,
    digest: str,
) -> MigrationReport:
    result = invoke_provider(
        ProviderInvocation(
            repo=payload.root,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="migrate-legacy",
            operation=ProviderOperation.MIGRATE,
            effective_config={},
            snapshots={
                "legacy_config": {
                    "standards_version": "v4",
                    "python_tooling": {"version": "1.0"},
                },
                "legacy_signatures": {
                    signature_id: {
                        target: {
                            "known": True,
                            "digest": digest,
                        }
                    }
                },
            },
        )
    )
    assert result.migration_report is not None
    return result.migration_report


def _installed_distribution(
    tmp_path: Path,
    *,
    include_markdown: bool = False,
    version: str = "1.1",
) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    repository = copy_minimal_repository(fixture)
    families = [("python-tooling", _FAMILY / f"versions/{version}", version)]
    if include_markdown:
        families.append(
            (
                "markdown-tooling",
                _ROOT / "standards/markdown-tooling/versions/1.2",
                "1.2",
            )
        )

    catalog_entries: list[str] = []
    for standard_id, payload_root, version in families:
        family = repository / f"standards/{standard_id}"
        shutil.copytree(payload_root.parent.parent, family)
        manifest = load_payload_manifest(payload_root / "payload.toml")
        integrity = validate_payload_integrity(payload_root, manifest)
        (family / "standard.toml").write_text(
            f'''schema_version = "2.0"

[standard]
id = "{standard_id}"
name = "{standard_id.replace("-", " ").title()}"
summary = "Isolated compatibility family."
status = "active"

[[versions]]
version = "{version}"
payload = "versions/{version}/payload.toml"
digest = "{integrity.aggregate_digest.value}"
''',
            encoding="utf-8",
        )
        catalog_entries.append(
            f'''[[packages]]
id = "{standard_id}"
version = "{version}"
digest = "{integrity.aggregate_digest.value}"
role = "default"
'''
        )

    (repository / "catalogs/5.toml").write_text(
        'schema_version = "1.0"\ncatalog_major = 5\n\n' + "\n".join(catalog_entries),
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _write_checker_config(repo: Path, checker: str) -> None:
    (repo / ".standards/config.toml").write_text(
        f'''[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.python-tooling]
enabled = true
version = "latest"

[standards.python-tooling.config.type_checker]
name = "{checker}"
mode = "strict"
''',
        encoding="utf-8",
    )


def _assert_no_mutating_actions(plan: ReconciliationPlan) -> None:
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in plan.actions
    )


def _assert_checker_state(repo: Path, plan: ReconciliationPlan, selected: str) -> None:
    other = "pyright" if selected == "basedpyright" else "basedpyright"
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tool = cast("dict[str, object]", data["tool"])
    assert selected in tool
    assert other not in tool
    scopes = {
        unit.scope
        for unit in plan.next_lock.artifacts
        if unit.path.original == "pyproject.toml" and unit.scope.startswith("table:/tool/")
    }
    assert f"table:/tool/{selected}" in scopes
    assert f"table:/tool/{other}" not in scopes


def test_python_tooling_declares_conditional_checker_tables() -> None:
    declarations = {item.id: item for item in _payload().manifest.contributions}

    for contribution_id, selected in (
        ("basedpyright-config", "basedpyright"),
        ("pyright-config", "pyright"),
    ):
        predicates = declarations[contribution_id].when_any
        assert [item.option for item in predicates] == ["/type_checker/name"]
        assert [item.equals for item in predicates] == [selected]

    for name in ("basedpyright", "pyright"):
        config = _options(type_checker={"name": name, "mode": "strict"})
        materialized = [
            contribution_id
            for contribution_id in ("basedpyright-config", "pyright-config")
            if declarations[contribution_id].materializes(config)
        ]
        assert materialized == [f"{name}-config"]


@pytest.mark.parametrize(
    ("selected", "requested"),
    [("basedpyright", "pyright"), ("pyright", "basedpyright")],
)
def test_python_tooling_provider_refuses_non_selected_checker_table(
    selected: str,
    requested: str,
) -> None:
    config = _options(type_checker={"name": selected, "mode": "strict"})

    with pytest.raises(ControlPlaneError) as exc_info:
        _render(f"table:/tool/{requested}", AdapterKind.TOML, config)

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "non-selected checker table must not be rendered"


def test_python_tooling_selected_checker_table_rendering_is_unchanged() -> None:
    assert _render("table:/tool/basedpyright", AdapterKind.TOML, _options()) == (
        "[tool.basedpyright]\n"
        'include = ["src", "tests"]\n'
        'typeCheckingMode = "strict"\n'
        'pythonVersion = "3.14"\n'
        'pythonPlatform = "All"\n'
        "failOnWarnings = true\n"
    )


@pytest.mark.parametrize("checker", ["basedpyright", "pyright"])
def test_python_tooling_plan_materializes_exactly_one_checker_scope(
    tmp_path: Path,
    checker: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _payload()
    request = resolution_request(
        (payload,),
        configs={"python-tooling": {"type_checker": {"name": checker, "mode": "strict"}}},
    )
    plan = plan_reconciliation(PlannerRequest(repo, request, (payload,)))

    scopes = {
        unit.scope for unit in plan.next_lock.artifacts if unit.path.original == "pyproject.toml"
    }
    other = "pyright" if checker == "basedpyright" else "basedpyright"
    assert f"table:/tool/{checker}" in scopes
    assert f"table:/tool/{other}" not in scopes


def _legacy_python_tooling_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        'standards_version: "v4"\npython_tooling:\n  version: "1.0"\n',
        encoding="utf-8",
    )
    legacy = _ROOT / "src/project_standards/bundles"
    sources = {
        ".python-version": legacy / "python-tooling/python-version",
        ".github/workflows/check.yml": legacy / "python-tooling/check.yml",
        "scripts/check.py": legacy / "python-tooling/check.py",
        "AGENTS.md": legacy / "python-tooling/AGENTS.md",
        "CLAUDE.md": legacy / "python-tooling/CLAUDE.md",
        ".vscode/settings.json": legacy / "python-tooling/vscode-settings.json",
        ".vscode/tasks.json": legacy / "python-tooling/vscode-tasks.json",
        ".editorconfig": legacy / "_shared/editorconfig",
        ".vscode/extensions.json": legacy / "_shared/vscode-extensions.json",
    }
    for target, source in sources.items():
        destination = repo / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return repo


def test_python_tooling_options_are_closed_and_fully_defaulted() -> None:
    assert _options() == {
        "contract_version": "1.1",
        "python_version": "3.14",
        "build_backend": "uv_build",
        "source_layout": "src",
        "additional_dev_dependencies": [],
        "ruff": {
            "line_length": 100,
            "extend_exclude": [".claude", ".agents", ".codex", ".continue"],
        },
        "type_checker": {"name": "basedpyright", "mode": "strict"},
        "pytest": {"fail_under": 85, "markers": [], "coverage_exclude_also": []},
        "coverage": {"parallel": False, "patch": []},
        "pip_audit": {"ignore_vulnerabilities": []},
        "ci": {"enabled": True, "performance": True},
        "workflow_ownership": "managed",
        "vscode": {"format_on_save": True},
        "agent_instructions": {"include_fix_commands": True},
    }

    configured = _options(
        python_version="3.13",
        build_backend="hatchling",
        source_layout="flat",
        ruff={"line_length": 88},
        type_checker={"name": "pyright", "mode": "standard"},
        pytest={"fail_under": 92},
        coverage={"parallel": True, "patch": ["subprocess"]},
        pip_audit={"ignore_vulnerabilities": ["GHSA-abcd-1234-efgh"]},
        ci={"enabled": False, "performance": False},
        workflow_ownership="consumer-owned",
        vscode={"format_on_save": False},
        agent_instructions={"include_fix_commands": False},
    )
    assert configured["type_checker"] == {"name": "pyright", "mode": "standard"}
    assert configured["build_backend"] == "hatchling"
    dependencies = _render("key:/dependency-groups/dev", AdapterKind.TOML, configured)
    assert all(tool in dependencies for tool in ("ruff", "pytest", "coverage", "pip-audit"))
    assert '"ruff>=0.14.11"' in dependencies
    audit = json.loads(_render("keyed-set:/tasks#label=audit", AdapterKind.JSONC, configured))
    assert audit["tasks"][0]["command"] == ("uv run pip-audit --ignore-vuln GHSA-abcd-1234-efgh")
    format_on_save = json.loads(
        _render(
            "key:/[python]/editor.formatOnSave",
            AdapterKind.JSONC,
            configured,
            target=".vscode/settings.json",
        )
    )
    assert format_on_save["[python]"]["editor.formatOnSave"] is False
    instructions = _render(
        "block:python-tooling",
        AdapterKind.MARKDOWN_BLOCK,
        configured,
        target="AGENTS.md",
    )
    assert "uv run ruff check . --fix" not in instructions
    assert _options(contract_version="1.0")["contract_version"] == "1.0"

    invalid: tuple[JsonObject, ...] = (
        {"unknown": True},
        {"contract_version": "2.0"},
        {"python_version": "3"},
        {"python_version": "3.16"},
        {"python_version": "3.99"},
        {"build_backend": "poetry"},
        {"source_layout": "custom"},
        {"type_checker": {"name": "mypy", "mode": "strict"}},
        {"ruff": {"line_length": 20}},
        {"ruff": {"enabled": False, "line_length": 100}},
        {"pytest": {"fail_under": 101}},
        {"pytest": {"enabled": False, "fail_under": 85}},
        {"coverage": {"parallel": False, "patch": ["subprocess"]}},
        {"coverage": {"patch": ["subprocess"]}},
        {"coverage": {"parallel": True, "patch": ["unknown"]}},
        {"coverage": {"parallel": True, "patch": ["subprocess", "subprocess"]}},
        {"pip_audit": {"enabled": False}},
        {"workflow_ownership": "shared"},
        {"vscode": {"enabled": False}},
        {"agent_instructions": {"enabled": False}},
    )
    payload = _payload()
    schema = load_option_schema(_PAYLOAD, payload.manifest)
    for options in invalid:
        with pytest.raises(PackageContractError, match="package options violate schema"):
            schema.resolve_options(options)


def test_additional_dev_dependencies_accept_version_comparators() -> None:
    configured = _options(additional_dev_dependencies=["pytest-xdist>=3.8", "pyright==1.1.411"])

    assert configured["additional_dev_dependencies"] == [
        "pytest-xdist>=3.8",
        "pyright==1.1.411",
    ]


@pytest.mark.parametrize(
    ("workflow_ownership", "ci", "expect_workflow"),
    [
        ("managed", {"enabled": True, "performance": True}, True),
        ("consumer-owned", {"enabled": True, "performance": True}, False),
        ("consumer-owned", {"enabled": False, "performance": False}, False),
    ],
)
def test_python_tooling_workflow_ownership_controls_only_the_workflow(
    tmp_path: Path,
    workflow_ownership: str,
    ci: JsonObject,
    expect_workflow: bool,
) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    repo.mkdir()
    request = resolution_request(
        (payload,),
        configs={
            "python-tooling": {
                "workflow_ownership": workflow_ownership,
                "ci": ci,
            }
        },
    )

    plan = plan_reconciliation(PlannerRequest(repo, request, (payload,)))

    paths = {unit.path.original for unit in plan.next_lock.artifacts}
    assert ".python-version" in paths
    assert "scripts/check.py" in paths
    assert (".github/workflows/check.yml" in paths) is expect_workflow


def test_python_tooling_consumer_owned_verification_omits_the_workflow() -> None:
    payload = _payload()
    config = _options(workflow_ownership="consumer-owned")
    snapshots: JsonObject = {}
    for target in (".python-version", "scripts/check.py"):
        content = _render("$file", AdapterKind.WHOLE_FILE, config, target=target).encode()
        snapshots[target] = {
            "kind": "regular",
            "content_digest": f"sha256:{sha256(content).hexdigest()}",
        }
    result = invoke_provider(
        ProviderInvocation(
            repo=_PAYLOAD,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="verify-toolchain",
            operation=ProviderOperation.VERIFY,
            effective_config=config,
            snapshots=snapshots,
        )
    )

    assert result.findings == ()


def test_python_tooling_known_consumer_owned_workflow_claim_is_field_free() -> None:
    payload = _payload()
    signature = next(
        item for item in payload.manifest.legacy_signatures if item.id == "legacy-check-workflow"
    )
    report = _migration_report(
        payload,
        workflow_ownership="consumer-owned",
        known=True,
        digest=signature.known_content_digests[0].value,
    )

    assert report.package.config["workflow_ownership"] == "consumer-owned"
    assert "/python_tooling/workflow_ownership" in report.package.recognized_settings
    assert len(report.claims) == 1
    claim = report.claims[0]
    assert claim.ownership == "consumer-owned"
    assert claim.disposition.value == "preserve"
    assert claim.intent_pointer is None
    assert report.findings == ()


def test_python_tooling_unknown_consumer_owned_workflow_claim_binds_intent() -> None:
    report = _migration_report(
        _payload(),
        workflow_ownership="consumer-owned",
        known=False,
        digest=f"sha256:{'f' * 64}",
    )

    assert len(report.claims) == 1
    claim = report.claims[0]
    assert claim.ownership == "consumer-owned"
    assert claim.disposition.value == "preserve"
    assert claim.intent_pointer == "/python_tooling/workflow_ownership"
    assert report.findings == ()


def test_python_tooling_unknown_managed_workflow_remains_blocked() -> None:
    report = _migration_report(
        _payload(),
        workflow_ownership="managed",
        known=False,
        digest=f"sha256:{'f' * 64}",
    )

    assert report.claims == ()
    assert [(finding.code, finding.path.original) for finding in report.findings] == [
        ("PT-LEGACY-MODIFIED", ".github/workflows/check.yml")
    ]


def test_python_tooling_release_current_preserved_container_contract_is_exact() -> None:
    payload = _payload()
    signatures = {signature.id: signature for signature in payload.manifest.legacy_signatures}
    for signature_id, (_target, digest) in _RELEASE_CURRENT_PRESERVED_CONTAINERS.items():
        assert digest in {known.value for known in signatures[signature_id].known_content_digests}

    provider_module = ast.parse(
        (_PAYLOAD / "providers/python_tooling.py").read_text(encoding="utf-8")
    )
    assignment = next(
        node
        for node in provider_module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_PRESERVED_CONTAINER_DIGESTS"
            for target in node.targets
        )
    )
    preserved = cast("set[str]", ast.literal_eval(assignment.value))

    assert preserved == {
        digest for _target, digest in _RELEASE_CURRENT_PRESERVED_CONTAINERS.values()
    }


@pytest.mark.parametrize(
    ("signature_id", "target", "digest"),
    [
        (signature_id, target, digest)
        for signature_id, (target, digest) in _RELEASE_CURRENT_PRESERVED_CONTAINERS.items()
    ],
)
def test_python_tooling_release_current_containers_are_preserved(
    signature_id: str,
    target: str,
    digest: str,
) -> None:
    report = _legacy_container_report(
        _payload(),
        signature_id=signature_id,
        target=target,
        digest=digest,
    )

    assert report.findings == ()
    assert len(report.claims) == 1
    claim = report.claims[0]
    assert claim.signature_id == signature_id
    assert claim.target.original == target
    assert claim.observed_digest.value == digest
    assert claim.disposition.value == "preserve"


@pytest.mark.parametrize(
    ("signature_id", "target", "current_digest"),
    [
        (signature_id, target, digest)
        for signature_id, (target, digest) in _RELEASE_CURRENT_PRESERVED_CONTAINERS.items()
    ],
)
def test_python_tooling_older_standard_owned_container_histories_still_retire(
    signature_id: str,
    target: str,
    current_digest: str,
) -> None:
    payload = _payload()
    signature = next(item for item in payload.manifest.legacy_signatures if item.id == signature_id)
    older_digests = [
        digest.value for digest in signature.known_content_digests if digest.value != current_digest
    ]
    assert older_digests

    for digest in older_digests:
        report = _legacy_container_report(
            payload,
            signature_id=signature_id,
            target=target,
            digest=digest,
        )
        assert report.findings == ()
        assert len(report.claims) == 1
        claim = report.claims[0]
        assert claim.signature_id == signature_id
        assert claim.target.original == target
        assert claim.observed_digest.value == digest
        assert claim.disposition.value == "remove"


def test_python_tooling_subprocess_patch_selects_coverage_7_10_floor() -> None:
    default_dependencies = _render(
        "key:/dependency-groups/dev",
        AdapterKind.TOML,
        _options(),
    )
    patched_dependencies = _render(
        "key:/dependency-groups/dev",
        AdapterKind.TOML,
        _options(coverage={"parallel": True, "patch": ["subprocess"]}),
    )

    assert '"coverage[toml]"' in default_dependencies
    assert '"coverage[toml]>=7.10.0"' not in default_dependencies
    assert '"coverage[toml]>=7.10.0"' in patched_dependencies


def test_python_tooling_coverage_run_renders_canonical_parallel_patch_order() -> None:
    rendered = _render(
        "table:/tool/coverage/run",
        AdapterKind.TOML,
        _options(coverage={"parallel": True, "patch": ["subprocess"]}),
    )

    assert rendered == (
        "[tool.coverage.run]\n"
        "branch = true\n"
        "parallel = true\n"
        'patch = ["subprocess"]\n'
        'source = ["src"]\n'
    )


def _rendered_coverage_commands(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if '"coverage"' in line]


def test_python_tooling_parallel_commands_render_erase_run_combine_report() -> None:
    workflow = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        _options(coverage={"parallel": True, "patch": ["subprocess"]}),
        target=".github/workflows/check.yml",
    )
    commands = [
        line.removeprefix("        run: ") for line in workflow.splitlines() if "coverage" in line
    ]

    assert commands == [
        "uv run coverage erase",
        "uv run coverage run --parallel-mode -m pytest -m 'not performance'",
        "uv run coverage combine",
        "uv run coverage report",
    ]


def test_python_tooling_parallel_local_commands_match_ci_coverage_lifecycle() -> None:
    config = _options(coverage={"parallel": True, "patch": ["subprocess"]})
    workflow = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        config,
        target=".github/workflows/check.yml",
    )
    script = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        config,
        target="scripts/check.py",
    )
    workflow_phases = [
        shlex.split(line.removeprefix("        run: "))[3]
        for line in workflow.splitlines()
        if "coverage" in line
    ]
    script_phases = [
        cast("tuple[str, ...]", ast.literal_eval(line.rstrip(",")))[3]
        for line in _rendered_coverage_commands(script)
    ]

    assert workflow_phases == ["erase", "run", "combine", "report"]
    assert script_phases == workflow_phases


@pytest.mark.parametrize(
    ("patch", "expect_child_capture"),
    [(["subprocess"], True), ([], False)],
)
def test_python_tooling_generated_gate_subprocess_only_capture_oracle(
    tmp_path: Path,
    patch: list[str],
    expect_child_capture: bool,
) -> None:
    repo = tmp_path / "scratch-consumer"
    repo.mkdir()
    (repo / "tests").mkdir()
    config = _options(
        source_layout="flat",
        pytest={"fail_under": 0},
        coverage={"parallel": True, "patch": patch},
        ci={"enabled": True, "performance": False},
    )
    pyproject = "\n".join(
        _render(scope, AdapterKind.TOML, config).rstrip()
        for scope in (
            "table:/build-system",
            "key:/dependency-groups/dev",
            "table:/tool/ruff",
            "table:/tool/basedpyright",
            "table:/tool/pytest/ini_options",
            "table:/tool/coverage/run",
            "table:/tool/coverage/report",
        )
    )
    (repo / "pyproject.toml").write_text(pyproject + "\n", encoding="utf-8")
    (repo / "child_only.py").write_text(
        """def main() -> None:
    print("child-only execution")


if __name__ == "__main__":
    main()
""",
        encoding="utf-8",
    )
    (repo / "tests/test_child_process.py").write_text(
        """import subprocess
import sys


def test_child_process() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "child_only"],
        check=False,
    )
    assert completed.returncode == 0
""",
        encoding="utf-8",
    )
    script = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        config,
        target="scripts/check.py",
    )
    script_path = repo / "scripts/check.py"
    script_path.parent.mkdir()
    script_path.write_text(script, encoding="utf-8")
    environment = {
        **os.environ,
        "COVERAGE_FILE": str(repo / ".coverage"),
        "UV_OFFLINE": "1",
        "UV_PROJECT": str(_ROOT),
    }

    result = subprocess.run(
        [sys.executable, "scripts/check.py"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0 and "cache" in output.lower():
        pytest.fail(f"offline subprocess oracle is missing a locked cache entry:\n{output}")
    assert result.returncode == 0, output
    subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
        cwd=repo,
        env=environment,
        check=True,
    )
    report = json.loads((repo / "coverage.json").read_text(encoding="utf-8"))
    files = cast("dict[str, object]", report["files"])
    child = cast(
        "dict[str, object]",
        next(info for path, info in files.items() if path.endswith("child_only.py")),
    )
    summary = cast("dict[str, object]", child["summary"])
    captured = summary["covered_lines"] != 0

    assert captured is expect_child_capture
    assert not list(repo.glob(".coverage.*"))


@pytest.mark.parametrize("checker", ["basedpyright", "pyright"])
def test_python_tooling_reconciled_complete_gate_oracle(
    tmp_path: Path,
    checker: str,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / "src/consumer_pkg").mkdir(parents=True)
    (repo / "src/consumer_pkg/__init__.py").write_text(
        'GREETING: str = "materialized"\n', encoding="utf-8"
    )
    (repo / "tests").mkdir()
    (repo / "tests/test_consumer_pkg.py").write_text(
        """from consumer_pkg import GREETING


def test_greeting() -> None:
    assert GREETING == "materialized"
""",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        """[project]
name = "consumer-pkg"
version = "0.1.0"
requires-python = ">=3.14"
""",
        encoding="utf-8",
    )
    initialize_control_plane(repo, "5", distribution=distribution)
    (repo / ".standards/config.toml").write_text(
        f'''[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.python-tooling]
enabled = true
version = "latest"

[standards.python-tooling.config.type_checker]
name = "{checker}"
mode = "strict"

[standards.python-tooling.config.pytest]
fail_under = 0

[standards.python-tooling.config.ci]
enabled = true
performance = false
''',
        encoding="utf-8",
    )
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success

    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tool = cast("dict[str, object]", data["tool"])
    other = "pyright" if checker == "basedpyright" else "basedpyright"
    assert checker in tool
    assert other not in tool

    # This oracle proves generated command/config execution with the root's
    # locked tools. PYTHONPATH supplies scratch source without claiming to
    # prove consumer dependency installation.
    pyright_cache = repo / ".pyright-cache"
    environment = {
        **os.environ,
        "COVERAGE_FILE": str(repo / ".coverage"),
        "UV_OFFLINE": "1",
        "npm_config_offline": "true",
        "PYRIGHT_PYTHON_CACHE_DIR": str(pyright_cache),
        "PYRIGHT_PYTHON_IGNORE_WARNINGS": "true",
        "PYRIGHT_PYTHON_USE_BUNDLED_PYRIGHT": "true",
        "UV_PROJECT": str(_ROOT),
        "PYTHONPATH": str(repo / "src"),
    }
    runtime = subprocess.run(
        ["uv", "run", checker, "--version"],
        cwd=_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert runtime.returncode == 0, runtime.stdout + runtime.stderr
    assert not pyright_cache.exists()
    probe = subprocess.run(
        [sys.executable, "-c", "import consumer_pkg"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr

    # uv and the Pyright wrapper are offline here. The generated pip-audit
    # phase still queries its configured vulnerability service by contract.
    result = subprocess.run(
        [sys.executable, "scripts/check.py"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
        cwd=repo,
        env=environment,
        check=True,
    )
    report = json.loads((repo / "coverage.json").read_text(encoding="utf-8"))
    files = cast("dict[str, object]", report["files"])
    assert any(path.endswith("src/consumer_pkg/__init__.py") for path in files)


def test_python_tooling_manifest_uses_only_bounded_shared_container_units() -> None:
    manifest = _payload().manifest
    assert manifest.payload.standard == "python-tooling"
    assert manifest.payload.version.value == "1.1"
    assert manifest.relations.companions == ["python-coding"]

    whole_shared = {
        contribution.target.original
        for contribution in manifest.contributions
        if contribution.adapter is AdapterKind.WHOLE_FILE
        and contribution.target.original
        in {
            "AGENTS.md",
            "CLAUDE.md",
            "pyproject.toml",
            ".editorconfig",
            ".vscode/extensions.json",
            ".vscode/settings.json",
            ".vscode/tasks.json",
        }
    }
    assert whole_shared == set()
    assert not {artifact.target.original for artifact in manifest.artifacts} & {
        "AGENTS.md",
        "CLAUDE.md",
        "pyproject.toml",
        ".editorconfig",
        ".vscode/extensions.json",
        ".vscode/settings.json",
        ".vscode/tasks.json",
    }

    scopes = {(item.target.original, item.adapter, item.scope) for item in manifest.contributions}
    assert ("pyproject.toml", AdapterKind.TOML, "table:/build-system") in scopes
    assert ("pyproject.toml", AdapterKind.TOML, "key:/dependency-groups/dev") in scopes
    assert ("pyproject.toml", AdapterKind.TOML, "table:/tool/ruff") in scopes
    assert ("pyproject.toml", AdapterKind.TOML, "table:/tool/basedpyright") in scopes
    assert ("pyproject.toml", AdapterKind.TOML, "table:/tool/pyright") in scopes
    assert (
        ".vscode/tasks.json",
        AdapterKind.JSONC,
        "keyed-set:/tasks#label=typecheck",
    ) in scopes
    assert (".vscode/tasks.json", AdapterKind.JSONC, "key:/version") in scopes
    assert (
        ".vscode/extensions.json",
        AdapterKind.JSONC,
        "set:/recommendations#value=detachhead.basedpyright",
    ) in scopes
    assert ("AGENTS.md", AdapterKind.MARKDOWN_BLOCK, "block:python-tooling") in scopes
    assert ("CLAUDE.md", AdapterKind.MARKDOWN_BLOCK, "block:python-tooling") in scopes


@pytest.mark.parametrize(
    ("checker", "mode", "command", "active_table"),
    [
        ("basedpyright", "strict", "uv run basedpyright", "basedpyright"),
        ("pyright", "standard", "uv run pyright", "pyright"),
    ],
)
def test_type_checker_selection_fans_out_to_all_declared_surfaces(
    checker: str,
    mode: str,
    command: str,
    active_table: str,
) -> None:
    config = _options(type_checker={"name": checker, "mode": mode})

    dependencies = _render("key:/dependency-groups/dev", AdapterKind.TOML, config)
    active = _render(f"table:/tool/{active_table}", AdapterKind.TOML, config)
    task = json.loads(_render("keyed-set:/tasks#label=typecheck", AdapterKind.JSONC, config))
    instructions = _render("block:python-tooling", AdapterKind.MARKDOWN_BLOCK, config)
    workflow = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        config,
        target=".github/workflows/check.yml",
    )

    assert f'"{checker}"' in dependencies
    assert f'typeCheckingMode = "{mode}"' in active
    assert task["tasks"][0]["command"] == command
    assert command in instructions
    assert command in workflow


def test_workflow_quotes_the_multiword_pytest_marker_as_one_shell_argument() -> None:
    workflow = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        _options(),
        target=".github/workflows/check.yml",
    )
    command = next(
        line.removeprefix("        run: ")
        for line in workflow.splitlines()
        if "coverage run -m pytest" in line
    )
    argv = shlex.split(command)
    marker_index = argv.index("-m", argv.index("pytest") + 1)
    assert argv[marker_index + 1] == "not performance"
    assert "performance" not in argv[marker_index + 2 :]


def test_workflow_renderer_uses_reviewed_action_runtime_versions() -> None:
    workflow = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        _options(),
        target=".github/workflows/check.yml",
    )

    assert "actions/checkout@v7" in workflow
    assert "astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990" in workflow


@pytest.mark.parametrize(
    ("scope", "original"),
    [
        (
            "table:/build-system",
            b'[build-system]\nrequires = ["consumer-backend"]\nbuild-backend = "consumer"\n',
        ),
        (
            "key:/dependency-groups/dev",
            b'[dependency-groups]\ndev = ["consumer-tool"]\n',
        ),
        ("table:/tool/ruff", b"[tool.ruff]\nline-length = 88\n"),
        (
            "table:/tool/basedpyright",
            b'[tool.basedpyright]\ntypeCheckingMode = "basic"\n',
        ),
        ("table:/tool/pyright", b'[tool.pyright]\ntypeCheckingMode = "strict"\n'),
        ("table:/tool/pytest/ini_options", b"[tool.pytest.ini_options]\naddopts = []\n"),
        ("table:/tool/coverage/run", b"[tool.coverage.run]\nbranch = false\n"),
        ("table:/tool/coverage/report", b"[tool.coverage.report]\nfail_under = 1\n"),
    ],
)
def test_python_tooling_preflights_every_conflicting_consumer_toml_scope_before_writes(
    tmp_path: Path,
    scope: str,
    original: bytes,
) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / "pyproject.toml").write_bytes(original)
    configs: dict[str, JsonObject] | None = None
    if scope == "table:/tool/pyright":
        configs = {"python-tooling": {"type_checker": {"name": "pyright", "mode": "strict"}}}
    request = PlannerRequest(
        repo,
        resolution_request((payload,), configs=configs),
        (payload,),
    )

    plan = plan_reconciliation(request)

    assert not plan.applicable
    assert (repo / "pyproject.toml").read_bytes() == original
    assert any(
        finding.path == "pyproject.toml" and finding.identity == scope for finding in plan.findings
    )
    assert not (repo / ".python-version").exists()


def test_python_tooling_rejects_consumer_parent_scope_collision_before_writes(
    tmp_path: Path,
) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    repo.mkdir()
    original = b'tool = "consumer-owned scalar"\n'
    (repo / "pyproject.toml").write_bytes(original)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))

    with pytest.raises(ControlPlaneError):
        plan_reconciliation(request)

    assert (repo / "pyproject.toml").read_bytes() == original
    assert not (repo / ".python-version").exists()


def test_python_tooling_composes_with_markdown_and_handoff_blocks_on_real_apply(
    tmp_path: Path,
) -> None:
    python = _payload()
    markdown_root = _ROOT / "standards/markdown-tooling/versions/1.2"
    markdown_manifest = load_payload_manifest(markdown_root / "payload.toml")
    markdown = InstalledPayload(
        markdown_root,
        markdown_manifest,
        validate_payload_integrity(markdown_root, markdown_manifest),
    )
    handoff = write_payload(
        tmp_path / "agent-handoff",
        "agent-handoff",
        contributions=(
            {
                "id": "agents-instructions",
                "target": "AGENTS.md",
                "adapter": "markdown-block",
                "scope": "block:agent-handoff",
                "content": (
                    b"<!-- prettier-ignore-start -->\n\n"
                    b"<!-- BEGIN project-standards:agent-handoff -->\n"
                    b"Use the repository handoff.\n"
                    b"<!-- END project-standards:agent-handoff -->\n\n"
                    b"<!-- prettier-ignore-end -->\n"
                ),
            },
            {
                "id": "claude-instructions",
                "target": "CLAUDE.md",
                "adapter": "markdown-block",
                "scope": "block:agent-handoff",
                "content": (
                    b"<!-- prettier-ignore-start -->\n\n"
                    b"<!-- BEGIN project-standards:agent-handoff -->\n"
                    b"Use the repository handoff.\n"
                    b"<!-- END project-standards:agent-handoff -->\n\n"
                    b"<!-- prettier-ignore-end -->\n"
                ),
            },
        ),
    )
    payloads = (python, markdown, handoff)
    repo = tmp_path / "consumer"
    repo.mkdir()
    request = PlannerRequest(repo, resolution_request(payloads), payloads)
    control = repo / ".standards"
    control.mkdir()
    (control / "lock.toml").write_bytes(render_lock(request.resolution.previous_lock))
    plan = plan_reconciliation(request)

    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.count("BEGIN project-standards:python-tooling") == 1
    assert agents.count("BEGIN project-standards:markdown-tooling") == 1
    assert agents.count("BEGIN project-standards:agent-handoff") == 1
    editorconfig = (repo / ".editorconfig").read_text(encoding="utf-8")
    assert editorconfig.count("root = true") == 1
    assert "[*.py]" in editorconfig and "[*.md]" in editorconfig
    extensions = json.loads((repo / ".vscode/extensions.json").read_text(encoding="utf-8"))
    assert {
        "ms-python.python",
        "charliermarsh.ruff",
        "detachhead.basedpyright",
        "esbenp.prettier-vscode",
        "DavidAnson.vscode-markdownlint",
    }.issubset(set(extensions["recommendations"]))
    tasks = json.loads((repo / ".vscode/tasks.json").read_text(encoding="utf-8"))
    assert tasks["version"] == "2.0.0"


def test_python_tooling_fresh_apply_second_apply_drift_and_disable(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "python-tooling", True)

    first_request = build_planner_request(repo, distribution, frozenset())
    first = plan_reconciliation(first_request)
    assert first.applicable, first.findings
    assert apply_reconciliation(ApplyRequest(first_request, first)).success

    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["build-system"]["build-backend"] == "uv_build"
    assert pyproject["tool"]["basedpyright"]["typeCheckingMode"] == "strict"
    assert "pyright" not in pyproject["tool"]
    assert "basedpyright" in pyproject["dependency-groups"]["dev"]
    assert (repo / ".python-version").read_text(encoding="utf-8") == "3.14\n"

    second_request = build_planner_request(repo, distribution, frozenset())
    second = plan_reconciliation(second_request)
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )

    workflow = repo / ".github/workflows/check.yml"
    clean_workflow = workflow.read_bytes()
    workflow.write_bytes(clean_workflow + b"# consumer drift\n")
    drift = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert not drift.applicable
    assert any(finding.path == ".github/workflows/check.yml" for finding in drift.findings)
    workflow.write_bytes(clean_workflow)

    set_standard_enabled(repo, "python-tooling", False)
    disable_request = build_planner_request(repo, distribution, frozenset())
    disable = plan_reconciliation(disable_request)
    assert disable.applicable, disable.findings
    assert apply_reconciliation(ApplyRequest(disable_request, disable)).success
    assert not (repo / ".python-version").exists()
    assert not (repo / ".github/workflows/check.yml").exists()
    assert not (repo / "scripts/check.py").exists()
    assert "python-tooling" not in (
        (repo / "AGENTS.md").read_text(encoding="utf-8") if (repo / "AGENTS.md").exists() else ""
    )


def test_python_tooling_real_apply_uses_selected_pyright_everywhere(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    (repo / ".standards/config.toml").write_text(
        """[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.python-tooling]
enabled = true
version = "latest"

[standards.python-tooling.config.type_checker]
name = "pyright"
mode = "standard"
""",
        encoding="utf-8",
    )

    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success

    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    assert "pyright" in pyproject["dependency-groups"]["dev"]
    assert "basedpyright" not in pyproject["dependency-groups"]["dev"]
    assert pyproject["tool"]["pyright"]["typeCheckingMode"] == "standard"
    assert "basedpyright" not in pyproject["tool"]
    workflow = (repo / ".github/workflows/check.yml").read_text(encoding="utf-8")
    assert "run: uv run pyright" in workflow
    assert "run: uv run basedpyright" not in workflow
    tasks = json.loads((repo / ".vscode/tasks.json").read_text(encoding="utf-8"))
    typecheck = next(task for task in tasks["tasks"] if task["label"] == "typecheck")
    assert typecheck["command"] == "uv run pyright"
    settings = json.loads((repo / ".vscode/settings.json").read_text(encoding="utf-8"))
    assert settings["python.analysis.typeCheckingMode"] == "standard"
    assert settings["basedpyright.analysis.typeCheckingMode"] == "off"
    assert "Use pyright in standard mode" in (repo / "AGENTS.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("first", ["basedpyright", "pyright"])
def test_python_tooling_real_checker_transitions_preserve_locks(
    tmp_path: Path,
    first: str,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    second = "pyright" if first == "basedpyright" else "basedpyright"
    previous: str | None = None

    for selected in (first, second, first):
        _write_checker_config(repo, selected)
        request = build_planner_request(repo, distribution, frozenset())
        plan = plan_reconciliation(request)
        assert plan.applicable, plan.findings
        if previous is not None:
            checker_units = {
                unit.kind
                for unit in plan.units
                if unit.target == "pyproject.toml"
                and unit.scope
                in {
                    "table:/tool/basedpyright",
                    "table:/tool/pyright",
                }
            }
            assert checker_units == {ActionKind.REMOVE, ActionKind.CREATE}
        assert apply_reconciliation(ApplyRequest(request, plan)).success
        _assert_checker_state(repo, plan, selected)

        converged = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
        _assert_no_mutating_actions(converged)
        previous = selected


def test_python_tooling_real_disable_and_reenable_retains_pyright_selection(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    _write_checker_config(repo, "pyright")

    first_request = build_planner_request(repo, distribution, frozenset())
    first = plan_reconciliation(first_request)
    assert first.applicable, first.findings
    assert apply_reconciliation(ApplyRequest(first_request, first)).success
    _assert_checker_state(repo, first, "pyright")

    set_standard_enabled(repo, "python-tooling", False)
    disable_request = build_planner_request(repo, distribution, frozenset())
    disabled = plan_reconciliation(disable_request)
    assert disabled.applicable, disabled.findings
    assert any(
        unit.kind is ActionKind.REMOVE
        and unit.target == "pyproject.toml"
        and unit.scope == "table:/tool/pyright"
        for unit in disabled.units
    )
    assert not {
        unit.scope
        for unit in disabled.next_lock.artifacts
        if unit.scope in {"table:/tool/basedpyright", "table:/tool/pyright"}
    }
    assert apply_reconciliation(ApplyRequest(disable_request, disabled)).success

    set_standard_enabled(repo, "python-tooling", True)
    reenable_request = build_planner_request(repo, distribution, frozenset())
    reenabled = plan_reconciliation(reenable_request)
    assert reenabled.applicable, reenabled.findings
    assert apply_reconciliation(ApplyRequest(reenable_request, reenabled)).success
    _assert_checker_state(repo, reenabled, "pyright")

    converged = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    _assert_no_mutating_actions(converged)


def test_python_tooling_disable_preserves_markdown_shared_units(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path, include_markdown=True)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "python-tooling", True)
    set_standard_enabled(repo, "markdown-tooling", True)
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success

    set_standard_enabled(repo, "python-tooling", False)
    disable_request = build_planner_request(repo, distribution, frozenset())
    disable = plan_reconciliation(disable_request)
    assert disable.applicable, disable.findings
    assert apply_reconciliation(ApplyRequest(disable_request, disable)).success

    editorconfig = (repo / ".editorconfig").read_text(encoding="utf-8")
    assert "root = true" in editorconfig
    assert "[*.md]" in editorconfig
    assert "[*.py]\nindent_style" not in editorconfig
    assert "[*.py]\nindent_size" not in editorconfig
    extensions = json.loads((repo / ".vscode/extensions.json").read_text(encoding="utf-8"))
    assert "esbenp.prettier-vscode" in extensions["recommendations"]
    assert "ms-python.python" not in extensions["recommendations"]
    assert "detachhead.basedpyright" not in extensions["recommendations"]


def test_python_tooling_real_v4_migration_applies_and_converges(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = _legacy_python_tooling_repo(tmp_path)

    migration = plan_legacy_migration(repo, distribution, "5")
    assert migration.applicable, migration.findings
    replacement_targets = {target.target for target in migration.reconciliation.targets}
    assert not replacement_targets & {action.target for action in migration.legacy_removals}
    result = apply_legacy_migration(migration)
    assert result.success, result
    assert not (repo / ".project-standards.yml").exists()
    config = tomllib.loads((repo / ".standards/config.toml").read_text(encoding="utf-8"))
    assert config["standards"]["python-tooling"]["config"]["contract_version"] == "1.0"
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "BEGIN project-standards:python-tooling" in agents
    assert "# Python Project Agent Instructions" not in agents
    tasks = json.loads((repo / ".vscode/tasks.json").read_text(encoding="utf-8"))
    assert tasks["version"] == "2.0.0"
    assert [task["label"] for task in tasks["tasks"]] == [
        "audit",
        "check",
        "fix",
        "test",
        "typecheck",
    ]
    assert "[tool.ruff]" in (repo / "pyproject.toml").read_text(encoding="utf-8")
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tables = [name for name in ("basedpyright", "pyright") if name in pyproject.get("tool", {})]
    assert tables == ["basedpyright"]
    extensions = json.loads((repo / ".vscode/extensions.json").read_text(encoding="utf-8"))
    assert "detachhead.basedpyright" in extensions["recommendations"]

    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


def test_python_tooling_consumer_owned_workflow_survives_migration_lifecycle(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = _legacy_python_tooling_repo(tmp_path)
    legacy_config = repo / ".project-standards.yml"
    legacy_config.write_text(
        legacy_config.read_text(encoding="utf-8").replace(
            '  version: "1.0"\n',
            '  version: "1.0"\n  workflow_ownership: "consumer-owned"\n',
        ),
        encoding="utf-8",
    )
    workflow = repo / ".github/workflows/check.yml"
    workflow.write_bytes(workflow.read_bytes() + b"# consumer optimization\n")
    consumer_bytes = workflow.read_bytes()

    migration = plan_legacy_migration(repo, distribution, "5")

    assert migration.applicable, migration.findings
    assert apply_legacy_migration(migration).success
    assert workflow.read_bytes() == consumer_bytes
    config = tomllib.loads((repo / ".standards/config.toml").read_text(encoding="utf-8"))
    assert config["standards"]["python-tooling"]["config"]["workflow_ownership"] == "consumer-owned"
    lock_paths = {unit.path.original for unit in migration.reconciliation.next_lock.artifacts}
    assert ".github/workflows/check.yml" not in lock_paths

    set_standard_enabled(repo, "python-tooling", False)
    disable_request = build_planner_request(repo, distribution, frozenset())
    disable = plan_reconciliation(disable_request)
    assert disable.applicable, disable.findings
    assert apply_reconciliation(ApplyRequest(disable_request, disable)).success
    assert workflow.read_bytes() == consumer_bytes

    set_standard_enabled(repo, "python-tooling", True)
    reenable_request = build_planner_request(repo, distribution, frozenset())
    reenable = plan_reconciliation(reenable_request)
    assert reenable.applicable, reenable.findings
    assert apply_reconciliation(ApplyRequest(reenable_request, reenable)).success
    assert workflow.read_bytes() == consumer_bytes
    assert not any(
        unit.path.original == ".github/workflows/check.yml" for unit in reenable.next_lock.artifacts
    )
    _assert_no_mutating_actions(
        plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    )


@pytest.mark.parametrize("known", [True, False])
def test_python_tooling_consumer_owned_migration_matches_extracted_wheel(
    tmp_path: Path,
    *,
    known: bool,
) -> None:
    source = _payload()
    distribution = _installed_distribution(tmp_path)
    installed = distribution.load_catalog("5").payload_map[("python-tooling", "1.1")]
    signature = next(
        item for item in source.manifest.legacy_signatures if item.id == "legacy-check-workflow"
    )

    digest = signature.known_content_digests[0].value if known else f"sha256:{'f' * 64}"
    source_report = _migration_report(
        source,
        workflow_ownership="consumer-owned",
        known=known,
        digest=digest,
    )
    installed_report = _migration_report(
        installed,
        workflow_ownership="consumer-owned",
        known=known,
        digest=digest,
    )

    assert installed_report == source_report


_RELEASED = _ROOT / "tests/fixtures/legacy_releases"


def _released_v4_repo(tmp_path: Path) -> Path:
    """Rebuild a consumer exactly as the released v4.3.0 CLI left it.

    The current-tree v1 bundles were revised after the v4 releases, so tests
    that copy them cannot see the bytes real consumers hold; these fixtures pin
    the released artifact bytes, including the "v3" platform tag v4 wrote.
    """
    repo = _legacy_python_tooling_repo(tmp_path)
    (repo / ".project-standards.yml").write_text(
        'standards_version: "v3"\npython_tooling:\n  version: "1.0"\n',
        encoding="utf-8",
    )
    shutil.copy2(_RELEASED / "v4.3.0/editorconfig", repo / ".editorconfig")
    shutil.copy2(_RELEASED / "v4.3.0/check.yml", repo / ".github/workflows/check.yml")
    return repo


def test_python_tooling_released_v4_bytes_migrate_and_apply(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path, version="1.3")
    repo = _released_v4_repo(tmp_path)

    migration = plan_legacy_migration(repo, distribution, "5")

    assert migration.applicable, migration.findings
    assert apply_legacy_migration(migration).success
    assert not (repo / ".project-standards.yml").exists()
    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    _assert_no_mutating_actions(second)


def test_python_tooling_released_v3_check_script_is_recognized(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path, version="1.3")
    repo = _released_v4_repo(tmp_path)
    shutil.copy2(_RELEASED / "v3.0.0/check.py", repo / "scripts/check.py")

    migration = plan_legacy_migration(repo, distribution, "5")

    assert migration.applicable, migration.findings


def test_python_tooling_consumer_content_survives_bounded_takeover(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path, version="1.3")
    repo = _released_v4_repo(tmp_path)
    claude = repo / "CLAUDE.md"
    claude.write_bytes(claude.read_bytes() + b"\n## Consumer notes\n\nKeep me.\n")
    editorconfig = repo / ".editorconfig"
    editorconfig.write_bytes(editorconfig.read_bytes() + b"\n[*.rs]\nindent_size = 4\n")

    migration = plan_legacy_migration(repo, distribution, "5")

    assert migration.applicable, migration.findings
    takeover = {
        finding.path
        for finding in migration.findings
        if finding.code == "CP-MIGRATION-BOUNDED-TAKEOVER"
    }
    assert takeover == {"CLAUDE.md", ".editorconfig"}
    assert apply_legacy_migration(migration).success
    merged = claude.read_text(encoding="utf-8")
    assert "Keep me." in merged
    assert "BEGIN project-standards:python-tooling" in merged
    assert "[*.rs]" in editorconfig.read_text(encoding="utf-8")


def test_python_tooling_customized_check_script_relinquishes_with_script_ownership(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path, version="1.4")
    repo = _released_v4_repo(tmp_path)
    (repo / ".project-standards.yml").write_text(
        'standards_version: "v3"\n'
        "python_tooling:\n"
        '  version: "1.0"\n'
        '  script_ownership: "consumer-owned"\n',
        encoding="utf-8",
    )
    script = repo / "scripts/check.py"
    customized = script.read_bytes() + b"\n# repo-specific audit stage\n"
    script.write_bytes(customized)

    migration = plan_legacy_migration(repo, distribution, "5")

    assert migration.applicable, migration.findings
    claim = next(
        item for item in migration.reports[0].claims if item.target.original == "scripts/check.py"
    )
    assert claim.ownership == "consumer-owned"
    assert claim.intent_pointer == "/python_tooling/script_ownership"
    assert apply_legacy_migration(migration).success
    assert script.read_bytes() == customized
    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    _assert_no_mutating_actions(second)
    assert script.read_bytes() == customized


def test_python_tooling_pristine_check_script_relinquishes_without_owner_evidence(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path, version="1.4")
    repo = _released_v4_repo(tmp_path)
    (repo / ".project-standards.yml").write_text(
        'standards_version: "v3"\n'
        "python_tooling:\n"
        '  version: "1.0"\n'
        '  script_ownership: "consumer-owned"\n',
        encoding="utf-8",
    )
    pristine = (repo / "scripts/check.py").read_bytes()

    migration = plan_legacy_migration(repo, distribution, "5")

    assert migration.applicable, migration.findings
    claim = next(
        item for item in migration.reports[0].claims if item.target.original == "scripts/check.py"
    )
    assert claim.ownership == "consumer-owned"
    assert claim.intent_pointer is None
    assert apply_legacy_migration(migration).success
    assert (repo / "scripts/check.py").read_bytes() == pristine


def test_python_tooling_customized_check_script_blocks_without_relinquishment(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path, version="1.4")
    repo = _released_v4_repo(tmp_path)
    script = repo / "scripts/check.py"
    script.write_bytes(script.read_bytes() + b"\n# repo-specific audit stage\n")

    migration = plan_legacy_migration(repo, distribution, "5")

    assert not migration.applicable
    assert {
        finding.code for finding in migration.findings if finding.path == "scripts/check.py"
    } >= {"CP-MIGRATION-LEGACY-DIGEST", "PT-LEGACY-MODIFIED"}


def test_python_tooling_modified_legacy_file_blocks_migration_without_writes(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = _legacy_python_tooling_repo(tmp_path)
    agents = repo / "AGENTS.md"
    agents.write_bytes(agents.read_bytes() + b"\nConsumer modification.\n")

    migration = plan_legacy_migration(repo, distribution, "5")

    assert not migration.applicable
    assert any(
        finding.code == "PT-LEGACY-MODIFIED" and finding.path == "AGENTS.md"
        for finding in migration.findings
    )
    assert not (repo / ".standards").exists()
    assert (repo / ".project-standards.yml").exists()


def test_python_tooling_payload_is_byte_identical_in_built_wheel(tmp_path: Path) -> None:
    project = copy_minimal_repository(tmp_path)
    family = project / "standards/python-tooling"
    shutil.copytree(_FAMILY, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "python-tooling"
name = "Python Tooling"
summary = "A reproducible Python project toolchain."
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
    prefix = "project_standards/payloads/python-tooling/1.1/"
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
    source_files = {
        path.relative_to(_PAYLOAD).as_posix(): path.read_bytes()
        for path in _PAYLOAD.rglob("*")
        if path.is_file()
    }
    assert wheel_files == source_files


def test_python_tooling_adoption_requires_lock_refresh_and_commit() -> None:
    adoption = (_PAYLOAD / "adopt.md").read_text(encoding="utf-8")
    assert "uv lock" in adoption
    assert "uv.lock" in adoption
