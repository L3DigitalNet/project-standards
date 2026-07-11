from __future__ import annotations

import base64
import hashlib
import re
import shutil
import subprocess
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request, run_render
from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import apply_legacy_migration, plan_legacy_migration
from project_standards.control_plane.models import DesiredPackage
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract import (
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.planner_helpers import resolution_request
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/cli-documentation"
_PAYLOAD = _ROOT / "standards/cli-documentation/versions/1.1"
_ROOT_V1_DIGEST = "722d4dae32d6a163e31bd69cfd37e23cf61b9bbc316a50b33305f7704002ba98"
_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    return InstalledPayload(_PAYLOAD, manifest, validate_payload_integrity(_PAYLOAD, manifest))


def _isolated_repository(tmp_path: Path) -> Path:
    root = copy_minimal_repository(tmp_path)
    family = root / "standards/cli-documentation"
    shutil.copytree(_FAMILY, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "cli-documentation"
name = "CLI Documentation Standard"
summary = "Profile-based usage references and optional workflow verification."
status = "active"

[[versions]]
version = "1.1"
payload = "versions/1.1/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    return root


def _installed_distribution(tmp_path: Path) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    fixture.mkdir()
    repository = _isolated_repository(fixture)
    payload = _payload()
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "cli-documentation"
version = "1.1"
digest = "{payload.integrity.aggregate_digest.value}"
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


def _invocation(
    provider_id: str,
    operation: ProviderOperation,
    config: JsonObject,
    *,
    snapshots: JsonObject | None = None,
) -> ProviderInvocation:
    payload = _payload()
    return ProviderInvocation(
        repo=_PAYLOAD,
        payload=payload,
        standard_id="cli-documentation",
        version=payload.manifest.payload.version,
        provider_id=provider_id,
        operation=operation,
        effective_config=config,
        snapshots=snapshots or {},
    )


def test_cli_documentation_payload_has_closed_neutral_options_and_providers() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    schema = load_option_schema(_PAYLOAD, manifest)

    assert schema.resolve_options({}) == {
        "contract_version": "1.0",
        "profile": "script",
        "command_name": None,
        "workflow_path": None,
        "ci": {
            "enabled": False,
            "runner": None,
            "language": None,
            "setup": None,
        },
    }
    with pytest.raises(PackageContractError, match="package options violate schema"):
        schema.resolve_options({"unknown": True})

    assert {
        provider.id: (provider.operation, provider.effect) for provider in manifest.providers
    } == {
        "render-workflow": (ProviderOperation.RENDER, ProviderEffect.CONTENT),
        "verify-workflow": (ProviderOperation.VERIFY, ProviderEffect.FINDINGS),
        "migrate-legacy": (ProviderOperation.MIGRATE, ProviderEffect.MIGRATION_REPORT),
    }


def test_cli_documentation_options_validate_profiles_and_ci_assumptions() -> None:
    payload = _payload()
    schema = load_option_schema(_PAYLOAD, payload.manifest)

    python = schema.resolve_options(
        {
            "profile": "packaged",
            "command_name": "toolname",
            "workflow_path": ".github/workflows/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "python",
                "setup": "uv",
            },
        }
    )
    generic = schema.resolve_options(
        {
            "profile": "script",
            "command_name": "toolname",
            "workflow_path": "ci/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "custom-runner",
                "language": "generic",
                "setup": "none",
            },
        }
    )
    assert python["ci"] == {
        "enabled": True,
        "runner": "ubuntu-latest",
        "language": "python",
        "setup": "uv",
    }
    assert generic["ci"] == {
        "enabled": True,
        "runner": "custom-runner",
        "language": "generic",
        "setup": "none",
    }
    assert python["workflow_path"] == ".github/workflows/cli-docs-check.yml"
    assert generic["workflow_path"] == "ci/cli-docs-check.yml"

    invalid: tuple[JsonObject, ...] = (
        {"profile": "packaged", "command_name": None},
        {"command_name": ""},
        {"ci": {"enabled": True}},
        {
            "command_name": "toolname",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "python",
                "setup": "uv",
            },
        },
        {
            "command_name": "toolname",
            "workflow_path": "ci.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "generic",
                "setup": "uv",
            },
        },
        {
            "workflow_path": "ci.yml",
            "ci": {
                "enabled": False,
                "runner": "ubuntu-latest",
                "language": None,
                "setup": None,
            },
        },
    )
    for options in invalid:
        with pytest.raises(PackageContractError, match="package options violate schema"):
            schema.resolve_options(options)


def test_cli_documentation_uses_inert_command_name_not_config_entrypoint() -> None:
    with pytest.raises(ValidationError, match=r"entrypoint.*not allowed"):
        DesiredPackage.model_validate(
            {
                "enabled": True,
                "version": "latest",
                "config": {"entrypoint": "toolname"},
            }
        )


def test_cli_documentation_declares_only_create_only_usage_ownership() -> None:
    manifest = _payload().manifest

    assert [(item.target.original, item.policy.value) for item in manifest.artifacts] == [
        ("docs/usage.md", "create-only")
    ]
    assert manifest.contributions == []
    assert manifest.relations.companions == []
    assert [
        (extension.id, extension.option, extension.media_type) for extension in manifest.extensions
    ] == [("workflow", "workflow_path", "text/yaml")]
    assert all(
        ".github/workflows" not in artifact.target.original for artifact in manifest.artifacts
    )
    verify = next(provider for provider in manifest.providers if provider.id == "verify-workflow")
    legacy = next(resource for resource in manifest.resources if resource.id == "legacy-workflow")
    signature = next(item for item in manifest.legacy_signatures if item.id == "legacy-workflow")
    assert verify.resources == ["legacy-workflow"]
    assert legacy.digest == signature.known_content_digests[0]
    assert (_PAYLOAD / legacy.path.normalized).read_bytes() == (
        _ROOT / "src/project_standards/bundles/cli-documentation/cli-docs-check.yml"
    ).read_bytes()


def test_cli_documentation_renders_python_and_non_python_workflows() -> None:
    python_config: JsonObject = {
        "contract_version": "1.0",
        "profile": "packaged",
        "command_name": "docs-name-a",
        "workflow_path": ".github/workflows/cli-docs-check.yml",
        "ci": {
            "enabled": True,
            "runner": "ubuntu-latest",
            "language": "python",
            "setup": "uv",
        },
    }
    generic_config: JsonObject = {
        "contract_version": "1.0",
        "profile": "script",
        "command_name": "generic-docs-name",
        "workflow_path": "ci/cli-docs-check.yml",
        "ci": {
            "enabled": True,
            "runner": "self-hosted",
            "language": "generic",
            "setup": "none",
        },
    }

    python = invoke_provider(
        _invocation("render-workflow", ProviderOperation.RENDER, python_config)
    )
    python_other_name = invoke_provider(
        _invocation(
            "render-workflow",
            ProviderOperation.RENDER,
            {**python_config, "command_name": "docs-name-b"},
        )
    )
    generic = invoke_provider(
        _invocation("render-workflow", ProviderOperation.RENDER, generic_config)
    )
    disabled = invoke_provider(
        _invocation(
            "render-workflow",
            ProviderOperation.RENDER,
            {
                "contract_version": "1.0",
                "profile": "script",
                "command_name": None,
                "workflow_path": None,
                "ci": {"enabled": False},
            },
        )
    )

    assert python.content is not None
    assert python.content == python_other_name.content
    assert b"docs-name-a" not in python.content
    assert b"docs-name-b" not in python.content
    assert b"CLI_DOCS_COMMAND: ${{ vars.CLI_DOCS_COMMAND }}" in python.content
    assert b"setup-uv@" in python.content
    assert b"uv build --wheel --out-dir dist/" in python.content
    assert b"uv venv .cli-docs-venv" in python.content
    assert b"uv pip install --python .cli-docs-venv dist/*.whl" in python.content
    assert b'".cli-docs-venv/bin/$CLI_DOCS_COMMAND" --help' in python.content
    assert generic.content is not None
    assert b"self-hosted" in generic.content
    assert b'command -v -- "$CLI_DOCS_COMMAND"' in generic.content
    assert b"setup-uv" not in generic.content
    assert disabled.content == b""


def test_cli_documentation_verify_provider_reports_snapshot_drift() -> None:
    config: JsonObject = {
        "contract_version": "1.0",
        "profile": "packaged",
        "command_name": "toolname",
        "workflow_path": ".github/workflows/cli-docs-check.yml",
        "ci": {
            "enabled": True,
            "runner": "ubuntu-latest",
            "language": "python",
            "setup": "uv",
        },
    }
    rendered = invoke_provider(
        _invocation("render-workflow", ProviderOperation.RENDER, config)
    ).content
    assert rendered is not None

    def snapshots(content: bytes) -> JsonObject:
        return {
            "referenced_input_content": [
                {
                    "standard_id": "cli-documentation",
                    "extension_id": "workflow",
                    "path": ".github/workflows/cli-docs-check.yml",
                    "digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
                    "content_base64": base64.b64encode(content).decode("ascii"),
                }
            ]
        }

    clean = invoke_provider(
        _invocation(
            "verify-workflow",
            ProviderOperation.VERIFY,
            config,
            snapshots=snapshots(rendered),
        )
    )
    legacy = invoke_provider(
        _invocation(
            "verify-workflow",
            ProviderOperation.VERIFY,
            config,
            snapshots=snapshots((_PAYLOAD / "resources/legacy-cli-docs-check.yml").read_bytes()),
        )
    )
    drift = invoke_provider(
        _invocation(
            "verify-workflow",
            ProviderOperation.VERIFY,
            config,
            snapshots=snapshots(b"name: consumer edit\n"),
        )
    )

    assert clean.findings == ()
    assert legacy.findings == ()
    assert [finding.code for finding in drift.findings] == ["CLI-DOCS-DRIFT"]


@pytest.mark.parametrize(
    "config",
    [
        {
            "contract_version": "1.0",
            "profile": "packaged",
            "command_name": "toolname",
            "workflow_path": "ci/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "python",
                "setup": "uv",
            },
        },
        {
            "contract_version": "1.0",
            "profile": "packaged",
            "command_name": "toolname",
            "workflow_path": ".github/workflows/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "self-hosted",
                "language": "python",
                "setup": "uv",
            },
        },
        {
            "contract_version": "1.0",
            "profile": "packaged",
            "command_name": "toolname",
            "workflow_path": ".github/workflows/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "generic",
                "setup": "none",
            },
        },
        {
            "contract_version": "1.0",
            "profile": "script",
            "command_name": "toolname",
            "workflow_path": ".github/workflows/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "python",
                "setup": "uv",
            },
        },
        {
            "contract_version": "1.0",
            "profile": "packaged",
            "command_name": "another-tool",
            "workflow_path": ".github/workflows/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "python",
                "setup": "uv",
            },
        },
    ],
)
def test_cli_documentation_rejects_legacy_bytes_outside_exact_migrated_state(
    config: JsonObject,
) -> None:
    workflow_path = config["workflow_path"]
    assert isinstance(workflow_path, str)
    legacy = (_PAYLOAD / "resources/legacy-cli-docs-check.yml").read_bytes()
    snapshots: JsonObject = {
        "referenced_input_content": [
            {
                "standard_id": "cli-documentation",
                "extension_id": "workflow",
                "path": workflow_path,
                "digest": f"sha256:{hashlib.sha256(legacy).hexdigest()}",
                "content_base64": base64.b64encode(legacy).decode("ascii"),
            }
        ]
    }

    result = invoke_provider(
        _invocation(
            "verify-workflow",
            ProviderOperation.VERIFY,
            config,
            snapshots=snapshots,
        )
    )

    assert [finding.code for finding in result.findings] == ["CLI-DOCS-DRIFT"]


def test_cli_documentation_legacy_provider_maps_exact_and_ambiguous_states() -> None:
    manifest = _payload().manifest
    digests = {
        signature.id: signature.known_content_digests[0].value
        for signature in manifest.legacy_signatures
    }
    snapshots: JsonObject = {
        "legacy_config": {
            "standards_version": "v4",
            "cli_documentation": {"version": "1.0"},
        },
        "legacy_signatures": {
            "legacy-usage": {"docs/usage.md": {"known": False, "digest": f"sha256:{'1' * 64}"}},
            "legacy-workflow": {
                ".github/workflows/cli-docs-check.yml": {
                    "known": True,
                    "digest": digests["legacy-workflow"],
                }
            },
        },
    }

    result = invoke_provider(
        _invocation(
            "migrate-legacy",
            ProviderOperation.MIGRATE,
            {},
            snapshots=snapshots,
        )
    )

    assert result.migration_report is not None
    report = result.migration_report
    assert report.package.config == {
        "contract_version": "1.0",
        "profile": "packaged",
        "command_name": "toolname",
        "workflow_path": ".github/workflows/cli-docs-check.yml",
        "ci": {
            "enabled": True,
            "runner": "ubuntu-latest",
            "language": "python",
            "setup": "uv",
        },
    }
    assert report.package.recognized_settings == ("/cli_documentation/version",)
    assert [(claim.signature_id, claim.disposition.value) for claim in report.claims] == [
        ("legacy-workflow", "preserve")
    ]


def test_cli_documentation_fresh_apply_disable_and_second_apply_preserve_usage(
    tmp_path: Path,
) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    control = repo / ".standards"
    control.mkdir(parents=True)
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    request = PlannerRequest(repo, resolution, (payload,))
    first = plan_reconciliation(request)

    assert all(".github/workflows" not in action.target for action in first.actions)
    assert first.next_lock.referenced_inputs == []
    assert apply_reconciliation(ApplyRequest(request, first)).success
    usage = repo / "docs/usage.md"
    assert usage.read_bytes() == (_PAYLOAD / "templates/usage-doc.md").read_bytes()
    usage.write_text("# Consumer usage\n", encoding="utf-8")

    second_resolution = resolution_request((payload,), previous_lock=first.next_lock)
    second = plan_reconciliation(PlannerRequest(repo, second_resolution, (payload,)))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )

    disabled_package = second_resolution.desired.standards["cli-documentation"].model_copy(
        update={"enabled": False}
    )
    disabled_desired = second_resolution.desired.model_copy(
        update={"standards": {"cli-documentation": disabled_package}}
    )
    disabled_resolution = replace(second_resolution, desired=disabled_desired)
    disabled_request = PlannerRequest(repo, disabled_resolution, (payload,))
    disabled = plan_reconciliation(disabled_request)
    assert disabled.applicable, disabled.findings
    assert any(
        action.kind is ActionKind.PRESERVE and action.target == "docs/usage.md"
        for action in disabled.actions
    )
    assert apply_reconciliation(ApplyRequest(disabled_request, disabled)).success
    assert usage.read_text(encoding="utf-8") == "# Consumer usage\n"


def test_cli_documentation_real_apply_verifies_workflow_and_rejects_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    control = repo / ".standards"
    workflow_path = ".github/workflows/cli-docs-check.yml"
    (control / "config.toml").write_text(
        """[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.cli-documentation]
enabled = true
version = "latest"

[standards.cli-documentation.config]
contract_version = "1.0"
profile = "packaged"
command_name = "documentation-only-name"
workflow_path = ".github/workflows/cli-docs-check.yml"

[standards.cli-documentation.config.ci]
enabled = true
runner = "ubuntu-latest"
language = "python"
setup = "uv"
""",
        encoding="utf-8",
    )
    assert not (repo / workflow_path).exists()
    assert (
        run_render(
            [
                "cli-documentation",
                "render-workflow",
                "--repo",
                str(repo),
            ],
            distribution=distribution,
        )
        == 0
    )
    rendered = capsys.readouterr().out.encode()
    workflow = repo / workflow_path
    workflow.parent.mkdir(parents=True)
    workflow.write_bytes(rendered)
    request = build_planner_request(repo, distribution, frozenset())
    first = plan_reconciliation(request)

    assert first.applicable, first.findings
    assert [item.path.original for item in first.next_lock.referenced_inputs] == [workflow_path]
    assert apply_reconciliation(ApplyRequest(request, first)).success

    second_request = build_planner_request(repo, distribution, frozenset())
    second = plan_reconciliation(second_request)
    second_result = apply_reconciliation(ApplyRequest(second_request, second))
    assert second_result.success
    assert not second_result.lock_written

    workflow.write_text("name: consumer edit\n", encoding="utf-8")
    drift_request = build_planner_request(repo, distribution, frozenset())
    drift = plan_reconciliation(drift_request)
    prior_lock = (control / "lock.toml").read_bytes()
    drift_result = apply_reconciliation(ApplyRequest(drift_request, drift))

    assert drift.applicable, drift.findings
    assert not drift_result.success
    assert drift_result.error_code == "CP-VERIFY"
    assert [finding.code for finding in drift_result.verification_findings] == ["CLI-DOCS-DRIFT"]
    assert (control / "lock.toml").read_bytes() == prior_lock
    assert workflow.read_text(encoding="utf-8") == "name: consumer edit\n"

    set_standard_enabled(repo, "cli-documentation", False)
    disabled_request = build_planner_request(repo, distribution, frozenset())
    disabled = plan_reconciliation(disabled_request)
    assert disabled.next_lock.referenced_inputs == []
    assert apply_reconciliation(ApplyRequest(disabled_request, disabled)).success
    assert workflow.read_text(encoding="utf-8") == "name: consumer edit\n"


def test_cli_documentation_real_migration_preserves_edited_usage_ambiguity(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        """standards_version: v4
cli_documentation:
  version: "1.0"
""",
        encoding="utf-8",
    )
    usage = repo / "docs/usage.md"
    usage.parent.mkdir(parents=True)
    edited = b"# Consumer-authored usage\n"
    usage.write_bytes(edited)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert {finding.code for finding in plan.findings} == {"CP-MIGRATION-LEGACY-DIGEST"}
    assert usage.read_bytes() == edited
    assert (repo / ".project-standards.yml").is_file()


def test_cli_documentation_real_legacy_migration_preserves_files_and_converges(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        """standards_version: v4
cli_documentation:
  version: "1.0"
""",
        encoding="utf-8",
    )
    usage = repo / "docs/usage.md"
    usage.parent.mkdir(parents=True)
    shutil.copy2(_ROOT / "src/project_standards/bundles/cli-documentation/usage-doc.md", usage)
    workflow = repo / ".github/workflows/cli-docs-check.yml"
    workflow.parent.mkdir(parents=True)
    shutil.copy2(
        _ROOT / "src/project_standards/bundles/cli-documentation/cli-docs-check.yml",
        workflow,
    )
    usage_before = usage.read_bytes()
    workflow_before = workflow.read_bytes()

    plan = plan_legacy_migration(repo, distribution, "5")
    assert plan.applicable, plan.findings
    assert [item.path.original for item in plan.reconciliation.next_lock.referenced_inputs] == [
        ".github/workflows/cli-docs-check.yml"
    ]
    assert apply_legacy_migration(plan).success
    assert not (repo / ".project-standards.yml").exists()
    assert usage.read_bytes() == usage_before
    assert workflow.read_bytes() == workflow_before

    second_request = build_planner_request(repo, distribution, frozenset())
    second = plan_reconciliation(second_request)
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )
    assert apply_reconciliation(ApplyRequest(second_request, second)).success

    workflow.write_text("name: arbitrary edit\n", encoding="utf-8")
    drift_request = build_planner_request(repo, distribution, frozenset())
    drift = plan_reconciliation(drift_request)
    drift_result = apply_reconciliation(ApplyRequest(drift_request, drift))
    assert not drift_result.success
    assert drift_result.error_code == "CP-VERIFY"


def test_cli_documentation_selected_provider_rejects_wrong_payload_version() -> None:
    invocation = _invocation(
        "render-workflow",
        ProviderOperation.RENDER,
        {
            "contract_version": "1.0",
            "profile": "script",
            "command_name": None,
            "ci": {"enabled": False},
        },
    )

    with pytest.raises(ControlPlaneError, match="selected package"):
        invoke_provider(replace(invocation, version=PackageVersion("1.0")))


def test_cli_documentation_validates_in_isolated_v2_family(tmp_path: Path) -> None:
    repository = build_package_repository(
        _isolated_repository(tmp_path),
        family_allowlist={"cli-documentation"},
    )

    assert validate_package_repository(repository) == ()


def test_cli_documentation_payload_docs_have_only_relocatable_local_links() -> None:
    root = _PAYLOAD.resolve()
    for document in _PAYLOAD.rglob("*.md"):
        for raw in _LINK.findall(document.read_text(encoding="utf-8")):
            path_text = raw.split("#", maxsplit=1)[0]
            if not path_text or "://" in path_text:
                continue
            target = (document.parent / path_text).resolve()
            assert target.is_relative_to(root), raw
            assert target.exists(), raw


def test_cli_documentation_adoption_guide_publishes_without_clobbering() -> None:
    guide = (_PAYLOAD / "adopt.md").read_text(encoding="utf-8")

    assert "scratch=$(mktemp" in guide
    assert "trap 'rm -f -- \"$scratch\"' EXIT" in guide
    assert 'actionlint "$scratch"' in guide
    assert '(set -o noclobber; cat -- "$scratch" >"$workflow_path")' in guide
    assert (
        'project-standards render cli-documentation render-workflow --repo . >"$workflow_path"'
    ) not in guide
    assert "not automatic rollback" in guide


def test_cli_documentation_payload_is_byte_identical_in_built_wheel(tmp_path: Path) -> None:
    project = _isolated_repository(tmp_path)
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
    prefix = "project_standards/payloads/cli-documentation/1.1/"
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


def test_cli_documentation_root_v1_manifest_is_unchanged() -> None:
    digest = hashlib.sha256((_FAMILY / "standard.toml").read_bytes()).hexdigest()
    assert digest == _ROOT_V1_DIGEST
