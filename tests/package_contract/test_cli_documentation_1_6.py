from __future__ import annotations

import base64
import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/cli-documentation"
_PREDECESSOR = _FAMILY / "versions/1.5"
_SUCCESSOR = _FAMILY / "versions/1.6"
_PREDECESSOR_DIGEST = "sha256:90bd59f457ec467da0990bbf89667f534753768be79530c7bfdde9c791d3b618"
_SUCCESSOR_DIGEST = "sha256:7c6e609bdccdf526cb1426b817b26efcc5622552138ac5e826d917aad91c09ba"
_CHANGED_RESOURCES = {
    "README.md",
    "adopt.md",
    "agent-summary.md",
    "config.schema.json",
    "payload.toml",
    "providers/cli_documentation.py",
    "resources/research-notes.md",
    "schemas/migration-report.schema.json",
    "schemas/provider-input.schema.json",
    "templates/readme-single-file.md",
    "templates/usage-doc.md",
}


def _payload_at(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _go_config() -> JsonObject:
    payload = _payload_at(_SUCCESSOR)
    return load_option_schema(_SUCCESSOR, payload.manifest).resolve_options(
        {
            "profile": "packaged",
            "command_name": "configured-name-is-inert",
            "workflow_path": ".github/workflows/cli-docs-check.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "go",
                "setup": "go",
            },
        }
    )


def _invoke(
    provider_id: str,
    operation: ProviderOperation,
    config: JsonObject,
    *,
    snapshots: JsonObject | None = None,
):
    payload = _payload_at(_SUCCESSOR)
    return invoke_provider(
        ProviderInvocation(
            repo=_ROOT,
            payload=payload,
            standard_id="cli-documentation",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=operation,
            effective_config=config,
            snapshots=snapshots or {},
        )
    )


def _workflow_steps() -> tuple[bytes, list[dict[str, object]]]:
    result = _invoke("render-workflow", ProviderOperation.RENDER, _go_config())
    assert result.effect is ProviderEffect.CONTENT
    assert result.content is not None
    document = yaml.safe_load(result.content)
    return result.content, document["jobs"]["cli-docs-check"]["steps"]


def test_cli_docs_1_6__predecessor_is_immutable_and_successor_is_indexed() -> None:
    predecessor = _payload_at(_PREDECESSOR)
    successor = _payload_at(_SUCCESSOR)
    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix()
        for path in payload_tree(_PREDECESSOR)
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix()
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }

    assert predecessor.integrity.aggregate_digest.value == _PREDECESSOR_DIGEST
    assert successor.integrity.aggregate_digest.value == _SUCCESSOR_DIGEST
    assert predecessor_files == successor_files
    for relative in predecessor_files - _CHANGED_RESOURCES:
        assert (_PREDECESSOR / relative).read_bytes() == (_SUCCESSOR / relative).read_bytes()

    family = tomllib.loads((_FAMILY / "standard.toml").read_text())
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text())
    versions = {entry["version"]: entry["digest"] for entry in family["versions"]}
    roles = {
        entry["version"]: entry["role"]
        for entry in catalog["packages"]
        if entry["id"] == "cli-documentation"
    }
    assert versions["1.6"] == _SUCCESSOR_DIGEST
    assert roles["1.5"] == "retained"
    assert roles["1.6"] == "default"

    manifest = tomllib.loads((_SUCCESSOR / "payload.toml").read_text())
    assert manifest["payload"]["version"] == "1.6"
    assert manifest["migrations"][0]["id"] == "legacy-v4-to-1-6"
    assert manifest["migrations"][0]["to"] == "package:1.6"


def test_cli_docs_1_6__schema_accepts_only_matched_ci_toolchains() -> None:
    payload = _payload_at(_SUCCESSOR)
    schema = load_option_schema(_SUCCESSOR, payload.manifest)

    assert _go_config()["ci"] == {
        "enabled": True,
        "runner": "ubuntu-latest",
        "language": "go",
        "setup": "go",
    }
    invalid: tuple[JsonObject, ...] = (
        {
            "workflow_path": "ci.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "go",
                "setup": "uv",
            },
        },
        {
            "workflow_path": "ci.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "python",
                "setup": "go",
            },
        },
        {
            "workflow_path": "ci.yml",
            "ci": {
                "enabled": True,
                "runner": "ubuntu-latest",
                "language": "generic",
                "setup": "go",
            },
        },
        {
            "ci": {
                "enabled": False,
                "runner": "ubuntu-latest",
                "language": "go",
                "setup": "go",
            }
        },
    )
    for config in invalid:
        with pytest.raises(PackageContractError, match="package options violate schema"):
            schema.resolve_options(config)


def test_cli_docs_1_6__go_workflow_builds_and_checks_selected_executable() -> None:
    content, steps = _workflow_steps()
    rendered = content.decode()

    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7" in rendered
    assert "actions/setup-go@b7ad1dad31e06c5925ef5d2fc7ad053ef454303e # v7.0.0" in rendered
    assert "go-version-file: go.mod" in rendered
    assert "CLI_DOCS_GO_PACKAGE: ${{ vars.CLI_DOCS_GO_PACKAGE }}" in rendered
    assert 'go build -trimpath -o "$install_dir/$CLI_DOCS_COMMAND"' in rendered
    assert '"$command_path" --help' in rendered
    assert '"$command_path" --version' in rendered
    assert "go run" not in rendered
    assert "go install" not in rendered
    assert "configured-name-is-inert" not in rendered
    assert [step.get("name") for step in steps].count("Validate command selection") == 1


@pytest.mark.parametrize(
    "package",
    [".", "./cmd/toolname", "./cmd/Tool_1.2", "./internal/tools/tool-name"],
)
def test_cli_docs_1_6__go_package_selector_accepts_one_explicit_package(
    package: str,
) -> None:
    _, steps = _workflow_steps()
    validate = next(step for step in steps if step.get("name") == "Validate command selection")
    completed = subprocess.run(
        ("bash", "-euo", "pipefail", "-c", str(validate["run"])),
        env={**os.environ, "CLI_DOCS_COMMAND": "toolname", "CLI_DOCS_GO_PACKAGE": package},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    "package",
    [
        "",
        "/abs/cmd/toolname",
        "../cmd/toolname",
        "./../cmd/toolname",
        "./cmd/...",
        "./cmd/tool name",
        "./cmd/tool;echo",
        "$(id)",
        "./cmd/one ./cmd/two",
    ],
)
def test_cli_docs_1_6__go_package_selector_rejects_ambiguous_or_unsafe_input(
    package: str,
) -> None:
    _, steps = _workflow_steps()
    validate = next(step for step in steps if step.get("name") == "Validate command selection")
    completed = subprocess.run(
        ("bash", "-euo", "pipefail", "-c", str(validate["run"])),
        env={**os.environ, "CLI_DOCS_COMMAND": "toolname", "CLI_DOCS_GO_PACKAGE": package},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert (
        "CLI_DOCS_GO_PACKAGE must be . or one explicit ./relative/package path" in completed.stderr
    )


def test_cli_docs_1_6__go_workflow_verification_detects_drift() -> None:
    content, _ = _workflow_steps()
    workflow_path = ".github/workflows/cli-docs-check.yml"

    def snapshot_for(workflow: bytes) -> JsonObject:
        return {
            "referenced_input_content": [
                {
                    "standard_id": "cli-documentation",
                    "extension_id": "workflow",
                    "path": workflow_path,
                    "content_base64": base64.b64encode(workflow).decode(),
                }
            ]
        }

    exact = _invoke(
        "verify-workflow",
        ProviderOperation.VERIFY,
        _go_config(),
        snapshots=snapshot_for(content),
    )
    assert exact.findings == ()

    drift = _invoke(
        "verify-workflow",
        ProviderOperation.VERIFY,
        _go_config(),
        snapshots=snapshot_for(content + b"# drift\n"),
    )
    assert [finding.code for finding in drift.findings] == ["CLI-DOCS-DRIFT"]


def test_cli_docs_1_6__provider_identity_schemas_match_selected_version() -> None:
    provider_input = json.loads((_SUCCESSOR / "schemas/provider-input.schema.json").read_text())
    migration_report = json.loads((_SUCCESSOR / "schemas/migration-report.schema.json").read_text())

    assert provider_input["properties"]["version"]["const"] == "1.6"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == ("1.6")
