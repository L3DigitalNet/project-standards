"""Package contract for the unadvertised Project Specification 1.9 candidate."""

from __future__ import annotations

import hashlib
import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import pytest
from jsonschema import Draft202012Validator

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
_FAMILY = _ROOT / "standards/project-spec"
_PREDECESSOR = _FAMILY / "versions/1.8"
_SUCCESSOR = _FAMILY / "versions/1.9"
_PROJECTION = _ROOT / "src/project_standards/payloads/project-spec/1.9"
_PREDECESSOR_DIGEST = "sha256:dc7c7f7c91d70717675c0de5bcd5759b498c6431db62f38f51ea060637a286d2"
_CHECKS = ["shared-boilerplate", "mandatory-phrasing"]
_LABELS = ["self-hosted", "linux", "x64", "l3digital-private"]
_PRE_ADVISORY_PROVIDER_SIZE = 20_308
_PRE_ADVISORY_PROVIDER_DIGEST = "d894ed525d6d5e112224d125e720d345deceffd0225d8654b88c9becc75cffb4"
_PROTECTED_SCHEMA_DIGESTS = {
    "config.schema.json": "dfff3b479f7f01780f993eb996c8a6775d0704771005c5902cda4cced7bb1f54",
    "schemas/content.schema.json": "8573fb58c93ae69bfda3d44d9cf8ff08a53a7b8b811e704995cd689c17fb7ef9",
    "schemas/extract.schema.json": "15766b81530941941b6c05cda749380dc49cc59827632fc82535c01dcc4fcbdf",
    "schemas/findings.schema.json": "48e903190fe18088a74c6fe476256856ac7d0805af40292d43b49c4c5ef2dbc6",
    "schemas/id-next.schema.json": "fdfb0d10a39767e703482d53479218d0f5aac94280761d1e094e350e84e1f3b9",
    "schemas/lint-findings.schema.json": "3fbcf25c3cfe4cb650439ea9e4b89587d9ee23c1fad244d561635f26fad1f88a",
    "schemas/migration-report.schema.json": "47dbb07fea721a046a03f66a84a00167827f6d011fcea170353c99e711b7a310",
    "schemas/mutation-plan.schema.json": "8c4fa5da614ef247d9f21d58f2a4bc533ed7b8205cb8221f1559c9893fdd57fd",
    "schemas/spec-full.schema.json": "a141f360e29aa84ad923678fd5aa9b557016df5bbbf73b6be7efb8274201d734",
    "schemas/spec-light.schema.json": "ffc2bb6a20a56b677297b5776e353a603d68874c1237e799ccc0c43d851420a7",
    "schemas/spec-standard.schema.json": "6bfe16cda38079fb18527a6fc35a4dc74415843f1d7caa319b4f3209536bf504",
}


class _JsonObjectValidator(Protocol):
    def is_valid(self, instance: JsonObject) -> bool: ...


_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "providers/project_spec.py",
        "resources/tooling-notes.md",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


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


def _verify(config: JsonObject) -> tuple[ControlFinding, ...]:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="project-spec",
            version=payload.manifest.payload.version,
            provider_id="verify-runner-labels",
            operation=ProviderOperation.VERIFY,
            effective_config=config,
            snapshots={},
        )
    )
    return result.findings


def test_project_spec_1_9__is_complete_and_preserves_every_1_8_byte() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys() | {
        "schemas/lint-findings.schema.json"
    }
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for successor in successor_files.values():
        assert successor.stat().st_mode & 0o7777 == 0o644

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.9"
    assert indexed["1.9"].digest == integrity.aggregate_digest
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-9"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.9"]


def test_project_spec_1_9__schemas_fix_successor_identity_and_lint_coverage() -> None:
    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )
    findings = json.loads(
        (_SUCCESSOR / "schemas/lint-findings.schema.json").read_text(encoding="utf-8")
    )

    assert provider_input["properties"]["version"]["const"] == "1.9"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.9"
    assert findings["properties"]["checks"] == {
        "type": "array",
        "prefixItems": [{"const": check} for check in _CHECKS],
        "items": False,
        "minItems": 2,
        "maxItems": 2,
    }
    assert set(findings["required"]) == {"findings", "checks"}
    assert (_SUCCESSOR / "schemas/findings.schema.json").read_bytes() == (
        _PREDECESSOR / "schemas/findings.schema.json"
    ).read_bytes()


def test_project_spec_1_9__provider_input_operation_enum_adds_only_verify() -> None:
    schema = cast(
        "JsonObject",
        json.loads((_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")),
    )
    predecessor = cast(
        "JsonObject",
        json.loads(
            (_PREDECESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
        ),
    )
    properties = cast("JsonObject", schema["properties"])
    operation_schema = cast("JsonObject", properties["operation"])
    predecessor_properties = cast("JsonObject", predecessor["properties"])
    predecessor_operation = cast("JsonObject", predecessor_properties["operation"])
    prior_operations = cast("list[str]", predecessor_operation["enum"])
    assert operation_schema["enum"] == [*prior_operations, "verify"]

    validator = cast("_JsonObjectValidator", Draft202012Validator(schema))
    base_input: JsonObject = {
        "schema_version": "1.0",
        "standard_id": "project-spec",
        "version": "1.9",
        "config": {},
        "resources": {},
        "snapshots": {},
    }
    for operation in (*prior_operations, "verify"):
        candidate: JsonObject = {**base_input, "operation": operation}
        assert validator.is_valid(candidate)
    unknown: JsonObject = {**base_input, "operation": "unknown"}
    assert not validator.is_valid(unknown)


def test_project_spec_1_9__preserves_conformance_provider_and_schema_corpus() -> None:
    provider = (_SUCCESSOR / "providers/project_spec.py").read_bytes()
    assert (
        hashlib.sha256(provider[:_PRE_ADVISORY_PROVIDER_SIZE]).hexdigest()
        == _PRE_ADVISORY_PROVIDER_DIGEST
    )
    for relative, expected in _PROTECTED_SCHEMA_DIGESTS.items():
        assert hashlib.sha256((_SUCCESSOR / relative).read_bytes()).hexdigest() == expected


def test_project_spec_1_9__identity_and_conformance_guidance_are_complete() -> None:
    expected = {
        "README.md": (
            "- **Package version:** `1.9`",
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
            "shared-boilerplate",
            "mandatory-phrasing",
        ),
        "adopt.md": (
            "# Adopt Project Specification 1.9",
            "project-standards standards enable project-spec --version 1.9",
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
            "additive",
            "semantic review",
        ),
        "agent-summary.md": (
            "# Project Specification 1.9 summary",
            "Package version `1.9`",
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
        ),
        "resources/tooling-notes.md": (
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
            "shared-boilerplate",
            "mandatory-phrasing",
        ),
    }
    for relative, fragments in expected.items():
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in document, (relative, fragment)
    tooling = (_SUCCESSOR / "resources/tooling-notes.md").read_text(encoding="utf-8")
    assert "Shared **boilerplate is identical** (spec-lifecycle paragraph" not in tooling


def test_project_spec_1_9__projection_and_unadvertised_catalog_role_are_exact() -> None:
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
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "project-spec"
    }
    assert roles["1.8"] == "retained"
    assert roles["1.9"] == "default"

    generated = (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
    assert "| [`project-spec`](project-spec/README.md) | active | 1.9 | default |" in generated

    selected = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    assert selected["standards"]["project-spec"]["resolved"] == "1.9"


def test_project_spec_1_9__manifest_declares_one_config_only_verify_provider() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    verify_providers = [
        provider
        for provider in manifest.providers
        if provider.operation is ProviderOperation.VERIFY
    ]

    assert len(verify_providers) == 1
    provider = verify_providers[0]
    assert provider.id == "verify-runner-labels"
    assert provider.phase.value == "verify"
    assert provider.effect.value == "findings"
    assert provider.entrypoint == "payload:provider-code#run_verify_runner_labels"
    assert provider.resources == []


@pytest.mark.parametrize(
    ("selected", "reason", "remedy"),
    [
        pytest.param(
            {"workflow_ownership": "consumer-owned", "runner_labels": _LABELS},
            "consumer-owned",
            "pass runner-labels",
            id="consumer-owned-caller",
        ),
        pytest.param(
            {"workflow_mode": "self-hosted", "runner_labels": _LABELS},
            "self-hosted",
            "pin its runs-on",
            id="direct-self-hosted",
        ),
    ],
)
def test_project_spec_1_9__unreachable_runner_labels_emit_one_warning(
    selected: Mapping[str, object],
    reason: str,
    remedy: str,
) -> None:
    findings = _verify(_options(selected))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "PS-RUNNER-LABELS-UNREACHABLE"
    assert finding.severity == "warning"
    assert finding.standard_id == "project-spec"
    assert finding.version == "1.9"
    assert finding.path == ".github/workflows/validate-specs.yml"
    assert finding.identity == "$file"
    assert reason in finding.message
    assert remedy in finding.hint


@pytest.mark.parametrize(
    "selected",
    [
        pytest.param({}, id="managed-empty"),
        pytest.param(
            {"workflow_ownership": "consumer-owned", "runner_labels": []},
            id="consumer-owned-empty",
        ),
        pytest.param(
            {"workflow_mode": "self-hosted", "runner_labels": []},
            id="self-hosted-empty",
        ),
        pytest.param({"runner_labels": _LABELS}, id="managed-caller-reachable"),
    ],
)
def test_project_spec_1_9__reachable_or_empty_runner_labels_stay_silent(
    selected: Mapping[str, object],
) -> None:
    assert _verify(_options(selected)) == ()
