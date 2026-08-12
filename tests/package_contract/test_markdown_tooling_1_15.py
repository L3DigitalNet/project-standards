"""Contract for the Markdown Tooling 1.15 runner-label reachability advisory.

The successor changes verification only: rendering and option defaults remain
the 1.14 contract, while each enabled verify provider reports when selected
labels cannot cross the managed caller's ``workflow_call`` boundary.
"""

from __future__ import annotations

import hashlib
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, cast

import pytest

from project_standards.control_plane.diagnostics import ControlFinding
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_PREDECESSOR = _FAMILY / "versions/1.14"
_SUCCESSOR = _FAMILY / "versions/1.15"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-tooling/1.15"
_PREDECESSOR_DIGEST = "sha256:25a8b52890c056f50fc424a76fe63d46fac68bdeee0c7e79d58ab440c9520999"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "providers/markdown_tooling.py",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_LABELS = ["self-hosted", "linux", "x64", "l3digital-private"]
_Tool = Literal["lint", "format"]


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    return InstalledPayload(
        _SUCCESSOR,
        manifest,
        validate_payload_integrity(_SUCCESSOR, manifest),
    )


def _options(selected: Mapping[str, object] | None = None) -> JsonObject:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    schema = load_option_schema(_SUCCESSOR, manifest)
    return schema.resolve_options(selected or {})  # type: ignore[arg-type]


def _render(provider_id: str, config: JsonObject) -> bytes:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={},
        )
    )
    assert result.content is not None
    return result.content


def _snapshot(content: bytes) -> JsonObject:
    return {
        "kind": "regular",
        "content_digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
    }


def _clean_snapshots(tool: _Tool, config: JsonObject) -> JsonObject:
    if tool == "lint":
        workflow_name = "lint-markdown"
        config_path = ".markdownlint.json"
        config_resource = "resources/markdownlint.json"
        render_provider = "render-lint-caller"
        self_host_resource = "resources/self-host-lint-markdown.yml"
    else:
        workflow_name = "format"
        config_path = ".prettierrc.json"
        config_resource = "resources/prettierrc.json"
        render_provider = "render-format-caller"
        self_host_resource = "resources/self-host-format.yml"

    workflow = (
        (_SUCCESSOR / self_host_resource).read_bytes()
        if config["workflow_mode"] == "self-hosted"
        else _render(render_provider, config)
    )
    return {
        config_path: _snapshot((_SUCCESSOR / config_resource).read_bytes()),
        f".github/workflows/{workflow_name}.yml": _snapshot(workflow),
    }


def _verify(
    tool: _Tool,
    config: JsonObject,
    snapshots: JsonObject | None = None,
) -> tuple[ControlFinding, ...]:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id=f"verify-{tool}",
            operation=ProviderOperation.VERIFY,
            effective_config=config,
            snapshots=snapshots if snapshots is not None else _clean_snapshots(tool, config),
        )
    )
    return result.findings


def test_markdown_tooling_1_15__successor__preserves_1_14_and_indexes_complete_payload() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    indexed = {
        entry.version.value: entry
        for entry in load_family_manifest(_FAMILY / "standard.toml").versions
    }
    assert manifest.payload.version.value == "1.15"
    assert indexed["1.15"].digest == integrity.aggregate_digest
    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        "package:1.7",
        "package:1.8",
        "package:1.9",
        "package:1.10",
        "package:1.11",
        "package:1.12",
        "legacy:v4-markdown-tooling",
    }
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.15"}
    assert "legacy-v4-to-1-15" in {migration.id for migration in manifest.migrations}
    for document in ("README.md", "adopt.md", "agent-summary.md"):
        guidance = (_SUCCESSOR / document).read_text(encoding="utf-8")
        assert "consumer-owned" in guidance
        assert "self-hosted" in guidance
        assert "non-fatal" in guidance


@pytest.mark.parametrize(
    ("tool", "workflow_path", "ownership_key"),
    [
        pytest.param(
            "lint",
            ".github/workflows/lint-markdown.yml",
            "lint_workflow_ownership",
            id="lint",
        ),
        pytest.param(
            "format",
            ".github/workflows/format.yml",
            "format_workflow_ownership",
            id="format",
        ),
    ],
)
@pytest.mark.parametrize(
    ("mode", "ownership", "reason", "remedy"),
    [
        pytest.param(
            "caller",
            "consumer-owned",
            "consumer-owned",
            "pass runner-labels",
            id="consumer-owned-caller",
        ),
        pytest.param(
            "self-hosted",
            "managed",
            "self-hosted",
            "pin its runs-on",
            id="direct-self-hosted",
        ),
    ],
)
def test_markdown_tooling_1_15__unreachable_labels__warn_for_each_enabled_caller(
    tool: _Tool,
    workflow_path: str,
    ownership_key: str,
    mode: str,
    ownership: str,
    reason: str,
    remedy: str,
) -> None:
    config = _options(
        {
            "workflow_mode": mode,
            ownership_key: ownership,
            "runner_labels": _LABELS,
        }
    )

    findings = _verify(tool, config)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MT-RUNNER-LABELS-UNREACHABLE"
    assert finding.severity == "warning"
    assert finding.standard_id == "markdown-tooling"
    assert finding.version == "1.15"
    assert finding.path == workflow_path
    assert finding.identity == "$file"
    assert reason in finding.message
    assert remedy in finding.hint


@pytest.mark.parametrize(
    "selected",
    [
        pytest.param({"runner_labels": []}, id="managed-empty"),
        pytest.param(
            {"runner_labels": [], "lint_workflow_ownership": "consumer-owned"},
            id="consumer-owned-empty",
        ),
        pytest.param(
            {"runner_labels": [], "workflow_mode": "self-hosted"},
            id="self-hosted-empty",
        ),
        pytest.param({"runner_labels": _LABELS}, id="managed-caller-reachable"),
    ],
)
def test_markdown_tooling_1_15__reachable_or_empty_labels__stay_silent(
    selected: Mapping[str, object],
) -> None:
    config = _options(selected)
    assert _verify("lint", config) == ()
    assert _verify("format", config) == ()


@pytest.mark.parametrize(
    ("tool", "selected"),
    [
        pytest.param(
            "lint",
            {
                "lint": False,
                "ci": {"lint_caller": False, "format_caller": True},
                "lint_workflow_ownership": "consumer-owned",
                "runner_labels": _LABELS,
            },
            id="lint",
        ),
        pytest.param(
            "format",
            {
                "format": False,
                "ci": {"lint_caller": True, "format_caller": False},
                "format_workflow_ownership": "consumer-owned",
                "runner_labels": _LABELS,
            },
            id="format",
        ),
    ],
)
def test_markdown_tooling_1_15__disabled_tool__stays_silent(
    tool: _Tool,
    selected: Mapping[str, object],
) -> None:
    assert _verify(tool, _options(selected)) == ()


def test_markdown_tooling_1_15__mixed_ownership__warns_only_for_affected_tool() -> None:
    mixed = _options(
        {
            "lint_workflow_ownership": "consumer-owned",
            "format_workflow_ownership": "managed",
            "runner_labels": _LABELS,
        }
    )
    assert [finding.code for finding in _verify("lint", mixed)] == ["MT-RUNNER-LABELS-UNREACHABLE"]
    assert _verify("format", mixed) == ()


@pytest.mark.parametrize(
    ("tool", "config_path", "ownership_key"),
    [
        pytest.param("lint", ".markdownlint.json", "lint_workflow_ownership", id="lint"),
        pytest.param("format", ".prettierrc.json", "format_workflow_ownership", id="format"),
    ],
)
def test_markdown_tooling_1_15__drift_and_unreachable_labels__retain_both_findings(
    tool: _Tool,
    config_path: str,
    ownership_key: str,
) -> None:
    config = _options({ownership_key: "consumer-owned", "runner_labels": _LABELS})
    snapshots = _clean_snapshots(tool, config)
    snapshots[config_path] = {"kind": "absent"}

    findings = _verify(tool, config, snapshots)

    assert [(finding.code, finding.severity) for finding in findings] == [
        ("MT-RUNNER-LABELS-UNREACHABLE", "warning"),
        (f"MT-{tool.upper()}-DRIFT", "error"),
    ]


def test_markdown_tooling_1_15__projection_and_catalog__stay_complete_and_default() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    advertised_versions = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-tooling"
    }
    assert advertised_versions["1.14"] == "retained"
    assert advertised_versions["1.15"] == "default"
    assert (
        "| [`markdown-tooling`](markdown-tooling/README.md) | active | 1.15 | default | consumer |"
    ) in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
