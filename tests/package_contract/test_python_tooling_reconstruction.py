from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import tomllib
import zipfile
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
from project_standards.control_plane.migration import apply_legacy_migration, plan_legacy_migration
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
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


def _installed_distribution(
    tmp_path: Path,
    *,
    include_markdown: bool = False,
) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    repository = copy_minimal_repository(fixture)
    families = [("python-tooling", _PAYLOAD, "1.1")]
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
        "ruff": {"line_length": 100},
        "type_checker": {"name": "basedpyright", "mode": "strict"},
        "pytest": {"fail_under": 85},
        "pip_audit": {"ignore_vulnerabilities": []},
        "ci": {"enabled": True, "performance": True},
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
        pip_audit={"ignore_vulnerabilities": ["GHSA-abcd-1234-efgh"]},
        ci={"enabled": False, "performance": False},
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
        {"pip_audit": {"enabled": False}},
        {"vscode": {"enabled": False}},
        {"agent_instructions": {"enabled": False}},
    )
    payload = _payload()
    schema = load_option_schema(_PAYLOAD, payload.manifest)
    for options in invalid:
        with pytest.raises(PackageContractError, match="package options violate schema"):
            schema.resolve_options(options)


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
    ("checker", "mode", "command", "active_table", "inactive_table"),
    [
        ("basedpyright", "strict", "uv run basedpyright", "basedpyright", "pyright"),
        ("pyright", "standard", "uv run pyright", "pyright", "basedpyright"),
    ],
)
def test_type_checker_selection_fans_out_to_all_declared_surfaces(
    checker: str,
    mode: str,
    command: str,
    active_table: str,
    inactive_table: str,
) -> None:
    config = _options(type_checker={"name": checker, "mode": mode})

    dependencies = _render("key:/dependency-groups/dev", AdapterKind.TOML, config)
    active = _render(f"table:/tool/{active_table}", AdapterKind.TOML, config)
    inactive = _render(f"table:/tool/{inactive_table}", AdapterKind.TOML, config)
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
    assert 'typeCheckingMode = "off"' in inactive
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
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))

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
    assert pyproject["tool"]["pyright"]["typeCheckingMode"] == "off"
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
    assert pyproject["tool"]["basedpyright"]["typeCheckingMode"] == "off"
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
    extensions = json.loads((repo / ".vscode/extensions.json").read_text(encoding="utf-8"))
    assert "detachhead.basedpyright" in extensions["recommendations"]

    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


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
