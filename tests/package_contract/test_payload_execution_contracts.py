from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from project_standards.package_contract import PackageContractError
from project_standards.package_contract.payload import (
    LegacySignatureDeclaration,
    MigrationDeclaration,
    MigrationEndpoint,
    PackageOptionSchema,
    PayloadManifest,
    ProviderDeclaration,
    load_option_schema,
)

_PAYLOAD_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures/package_contract/valid/minimal/standards/demo/versions/1.2/payload.toml"
)


def _payload_data() -> dict[str, object]:
    return tomllib.loads(_PAYLOAD_PATH.read_text(encoding="utf-8"))


def _resources(data: dict[str, object]) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", data["resources"])


def _add_resource(
    data: dict[str, object], resource_id: str, path: str, *, role: str = "provider-resource"
) -> None:
    _resources(data).append(
        {
            "id": resource_id,
            "role": role,
            "path": path,
            "media_type": "application/json",
            "digest": f"sha256:{'a' * 64}",
        }
    )


def _provider(
    *,
    provider_id: str = "render-config",
    operation: str = "render",
    kind: str = "python",
    phase: str = "plan",
    effect: str = "content",
    entrypoint: str | None = "payload:provider-code#render",
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": provider_id,
        "operation": operation,
        "kind": kind,
        "phase": phase,
        "effect": effect,
        "input_schema": "provider-input",
        "output_schema": "provider-output",
        "resources": ["provider-data"],
    }
    if entrypoint is not None:
        result["entrypoint"] = entrypoint
    return result


@pytest.mark.parametrize(
    ("operation", "phase", "effect"),
    [
        ("validate", "validate", "findings"),
        ("verify", "verify", "findings"),
        ("lint", "validate", "findings"),
        ("drift-check", "validate", "findings"),
        ("semantic-review", "validate", "findings"),
        ("id-next", "inspect", "content"),
        ("extract", "inspect", "content"),
        ("render", "plan", "content"),
        ("migrate", "plan", "mutation-plan"),
        ("fix", "authoring", "mutation-plan"),
        ("scaffold", "authoring", "mutation-plan"),
        ("upgrade", "authoring", "mutation-plan"),
    ],
)
def test_provider_accepts_every_closed_operation_mapping(
    operation: str, phase: str, effect: str
) -> None:
    provider = ProviderDeclaration.model_validate(
        _provider(operation=operation, phase=phase, effect=effect)
    )

    assert provider.operation.value == operation
    assert provider.phase.value == phase
    assert provider.effect.value == effect


@pytest.mark.parametrize(
    "override",
    [
        {"phase": "inspect"},
        {"effect": "findings"},
        {"kind": "python", "entrypoint": None},
        {"entrypoint": "global.module:render"},
        {"entrypoint": "payload:provider-code"},
        {"entrypoint": "payload:provider-code#bad-symbol!"},
        {"resources": ["provider-data", "provider-data"]},
    ],
)
def test_provider_rejects_invalid_mapping_entrypoint_or_resources(
    override: dict[str, object],
) -> None:
    payload = _provider()
    payload.update(override)
    if override.get("entrypoint", "present") is None:
        payload.pop("entrypoint", None)

    with pytest.raises(ValidationError):
        ProviderDeclaration.model_validate(payload)


def test_documentation_only_provider_has_no_executable_contract() -> None:
    provider = ProviderDeclaration.model_validate(
        {
            "id": "semantic-guidance",
            "operation": "semantic-review",
            "kind": "documentation-only",
            "phase": "validate",
            "effect": "findings",
            "resources": [],
        }
    )

    assert provider.entrypoint is None
    assert provider.input_schema is None
    assert provider.output_schema is None


def test_payload_provider_references_only_declared_payload_resources() -> None:
    data = _payload_data()
    for resource_id, path in (
        ("provider-code", "providers/render.py"),
        ("provider-input", "schemas/provider-input.json"),
        ("provider-output", "schemas/provider-output.json"),
        ("provider-data", "resources/provider-data.json"),
    ):
        _add_resource(data, resource_id, path)
    data["providers"] = [_provider()]

    manifest = PayloadManifest.model_validate(data)
    assert manifest.providers[0].id == "render-config"

    missing = _payload_data()
    missing["providers"] = [_provider()]
    with pytest.raises(ValidationError, match="undeclared resource"):
        PayloadManifest.model_validate(missing)


def test_extension_binds_one_path_option_and_preferred_consumer_root(tmp_path: Path) -> None:
    document = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {"extra_rules_file": {"type": "string"}},
        "required": ["extra_rules_file"],
    }
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    (payload_dir / "config.schema.json").write_text(json.dumps(document), encoding="utf-8")
    data = _payload_data()
    data["extensions"] = [
        {
            "id": "extra-rules",
            "option": "extra_rules_file",
            "media_type": "application/toml",
            "path_policy": "repository-relative",
            "preferred_root": ".standards/extensions/demo/",
        }
    ]
    manifest = PayloadManifest.model_validate(data)

    schema = load_option_schema(payload_dir, manifest)

    assert isinstance(schema, PackageOptionSchema)
    assert manifest.extensions[0].preferred_root == ".standards/extensions/demo/"


@pytest.mark.parametrize(
    "extension",
    [
        {
            "id": "extra-rules",
            "option": "missing_option",
            "media_type": "application/toml",
            "path_policy": "repository-relative",
        },
        {
            "id": "extra-rules",
            "option": "extra_rules_file",
            "media_type": "application/toml",
            "path_policy": "absolute",
        },
        {
            "id": "extra-rules",
            "option": "extra_rules_file",
            "media_type": "application/toml",
            "path_policy": "repository-relative",
            "preferred_root": ".standards/packages/demo/",
        },
        {
            "id": "extra-rules",
            "option": "extra_rules_file",
            "media_type": "application/toml",
            "path_policy": "repository-relative",
            "preferred_root": ".standards/extensions/other/",
        },
    ],
)
def test_extension_rejects_unknown_option_policy_or_wrong_namespace(
    tmp_path: Path, extension: dict[str, object]
) -> None:
    data = _payload_data()
    data["extensions"] = [extension]
    if extension["option"] == "missing_option":
        manifest = PayloadManifest.model_validate(data)
        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        payload_dir.joinpath("config.schema.json").write_bytes(
            _PAYLOAD_PATH.with_name("config.schema.json").read_bytes()
        )
        with pytest.raises(PackageContractError, match="extension option"):
            load_option_schema(payload_dir, manifest)
    else:
        with pytest.raises(ValidationError):
            PayloadManifest.model_validate(data)


def test_extension_preferred_root_must_not_overlap_a_managed_output() -> None:
    data = _payload_data()
    data["extensions"] = [
        {
            "id": "extra-rules",
            "option": "contract_version",
            "media_type": "application/toml",
            "path_policy": "repository-relative",
            "preferred_root": ".standards/extensions/demo/",
        }
    ]
    data["artifacts"] = [
        {
            "id": "bad-output",
            "target": ".standards/extensions/demo/generated.toml",
            "source": "artifacts/generated.toml",
            "digest": f"sha256:{'b' * 64}",
            "policy": "managed",
        }
    ]

    with pytest.raises(ValidationError, match="extension root"):
        PayloadManifest.model_validate(data)


def test_migration_endpoint_accepts_typed_package_and_legacy_states() -> None:
    package = MigrationEndpoint("package:2.10")
    legacy = MigrationEndpoint("legacy:v4-python-tooling")

    assert package.package_version is not None
    assert package.package_version.value == "2.10"
    assert legacy.legacy_state == "v4-python-tooling"


@pytest.mark.parametrize(
    "value",
    ["", "2.0", "package:2", "package:02.0", "legacy:", "legacy:Bad_State"],
)
def test_migration_endpoint_rejects_unknown_or_noncanonical_forms(value: str) -> None:
    with pytest.raises(ValueError):
        MigrationEndpoint(value)


def test_automatic_migration_declares_provider_effects_and_exact_legacy_signature() -> None:
    signature = {
        "id": "agent-handoff-instructions-v1",
        "kind": "bounded-block",
        "format": "markdown",
        "targets": ["CLAUDE.md", "AGENTS.md"],
        "begin": "<!-- BEGIN agent-handoff managed instructions -->",
        "end": "<!-- END agent-handoff managed instructions -->",
        "known_content_digests": [f"sha256:{'a' * 64}"],
    }
    migration = MigrationDeclaration.model_validate(
        {
            "id": "legacy-v4-to-1-2",
            "from": "legacy:v4-demo",
            "to": "package:1.2",
            "mode": "automatic",
            "provider": "migrate-v4",
            "reversible": True,
            "affected": ["config:*", "contribution:instructions"],
            "signatures": ["agent-handoff-instructions-v1"],
        }
    )
    legacy = LegacySignatureDeclaration.model_validate(signature)

    assert migration.from_endpoint.legacy_state == "v4-demo"
    assert migration.to_endpoint.package_version == MigrationEndpoint("package:1.2").package_version
    assert legacy.begin == "<!-- BEGIN agent-handoff managed instructions -->"
    assert legacy.end == "<!-- END agent-handoff managed instructions -->"
    assert [target.original for target in legacy.targets] == ["AGENTS.md", "CLAUDE.md"]


def test_payload_accepts_a_complete_automatic_legacy_migration() -> None:
    data = _payload_data()
    for resource_id, path in (
        ("migrate-code", "providers/migrate.py"),
        ("migrate-input", "schemas/migrate-input.json"),
        ("migrate-output", "schemas/migrate-output.json"),
    ):
        _add_resource(data, resource_id, path)
    data["providers"] = [
        _provider(
            provider_id="migrate-v4",
            operation="migrate",
            phase="plan",
            effect="mutation-plan",
            entrypoint="payload:migrate-code#migrate",
        )
        | {
            "input_schema": "migrate-input",
            "output_schema": "migrate-output",
            "resources": [],
        }
    ]
    data["legacy_signatures"] = [
        {
            "id": "legacy-config-v1",
            "kind": "bounded-block",
            "format": "yaml",
            "targets": [".project-standards.yml"],
            "begin": "# BEGIN demo managed config",
            "end": "# END demo managed config",
            "known_content_digests": [f"sha256:{'d' * 64}"],
        }
    ]
    data["migrations"] = [
        {
            "id": "legacy-v4-to-1-2",
            "from": "legacy:v4-demo",
            "to": "package:1.2",
            "mode": "automatic",
            "provider": "migrate-v4",
            "reversible": True,
            "affected": ["config:*"],
            "signatures": ["legacy-config-v1"],
        }
    ]

    manifest = PayloadManifest.model_validate(data)

    assert manifest.migrations[0].provider == "migrate-v4"
    assert manifest.legacy_signatures[0].id == "legacy-config-v1"


def test_payload_requires_manual_migration_instructions_to_be_a_declared_resource() -> None:
    data = _payload_data()
    data["migrations"] = [
        {
            "id": "1-2-to-2-0",
            "from": "package:1.2",
            "to": "package:2.0",
            "mode": "manual",
            "instructions": "migrations/manual.md",
            "reversible": False,
            "affected": ["config:*"],
        }
    ]

    with pytest.raises(ValidationError, match="declared resource"):
        PayloadManifest.model_validate(data)


@pytest.mark.parametrize(
    "signature",
    [
        {
            "id": "agent-handoff-codex-hook-v1",
            "kind": "bounded-block",
            "format": "toml",
            "targets": [".codex/config.toml"],
            "begin": "# BEGIN agent-handoff managed codex hook",
            "end": "# END agent-handoff managed codex hook",
            "known_content_digests": [f"sha256:{'b' * 64}"],
        },
        {
            "id": "agent-handoff-project-config-v1",
            "kind": "bounded-block",
            "format": "yaml",
            "targets": [".project-standards.yml"],
            "begin": "# BEGIN agent-handoff managed config",
            "end": "# END agent-handoff managed config",
            "known_content_digests": [f"sha256:{'c' * 64}"],
        },
    ],
)
def test_exact_agent_handoff_toml_and_yaml_legacy_signatures(
    signature: dict[str, object],
) -> None:
    parsed = LegacySignatureDeclaration.model_validate(signature)
    assert parsed.begin == signature["begin"]
    assert parsed.end == signature["end"]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "id": "bad-auto",
            "from": "legacy:v4-demo",
            "to": "package:1.2",
            "mode": "automatic",
            "instructions": "migrations/manual.md",
            "reversible": False,
            "affected": ["config:*"],
        },
        {
            "id": "bad-manual",
            "from": "package:1.2",
            "to": "package:2.0",
            "mode": "manual",
            "provider": "migrate-v2",
            "reversible": False,
            "affected": ["config:*"],
        },
        {
            "id": "unrelated",
            "from": "package:2.0",
            "to": "package:3.0",
            "mode": "manual",
            "instructions": "migrations/manual.md",
            "reversible": False,
            "affected": ["config:*"],
        },
    ],
)
def test_migration_rejects_wrong_mode_contract_or_unrelated_payload(
    payload: dict[str, object],
) -> None:
    if payload["id"] == "unrelated":
        data = _payload_data()
        data["migrations"] = [payload]
        with pytest.raises(ValidationError, match="containing payload version"):
            PayloadManifest.model_validate(data)
    else:
        with pytest.raises(ValidationError):
            MigrationDeclaration.model_validate(payload)
