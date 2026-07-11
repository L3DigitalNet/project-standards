from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from project_standards.package_contract import PackageContractError
from project_standards.package_contract.payload import (
    PackageOptionSchema,
    PayloadAvailability,
    PayloadManifest,
    load_option_schema,
    load_payload_manifest,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/package_contract"
_VALID_PAYLOAD = _FIXTURES / "valid/minimal/standards/demo/versions/1.2/payload.toml"
_VALID_SCHEMA = _VALID_PAYLOAD.parent / "config.schema.json"
_INVALID_PAYLOADS = _FIXTURES / "invalid/payload"


def _digest(character: str = "0") -> str:
    return f"sha256:{character * 64}"


def _payload_data() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "payload": {
            "standard": "demo",
            "version": "1.2",
            "availability": "consumer",
        },
        "config": {"schema_resource": "config-schema"},
        "capabilities": {
            "provides": ["demo.validate"],
            "consumes_platform": ["project-standards.reconcile"],
        },
        "relations": {
            "companions": ["python-coding"],
            "extends": [],
            "conflicts": [],
        },
        "resources": [
            {
                "id": "readme",
                "role": "canonical-standard",
                "path": "README.md",
                "media_type": "text/markdown",
                "digest": _digest(),
            },
            {
                "id": "agent-summary",
                "role": "agent-summary",
                "path": "agent-summary.md",
                "media_type": "text/markdown",
                "digest": _digest("1"),
            },
            {
                "id": "config-schema",
                "role": "config-schema",
                "path": "config.schema.json",
                "media_type": "application/schema+json",
                "digest": _digest("2"),
            },
            {
                "id": "adopt",
                "role": "adoption-guide",
                "path": "adopt.md",
                "media_type": "text/markdown",
                "digest": _digest("3"),
            },
        ],
    }


def test_payload_manifest_accepts_identity_options_capabilities_and_relations() -> None:
    manifest = PayloadManifest.model_validate(_payload_data())

    assert manifest.payload.standard == "demo"
    assert manifest.payload.version.value == "1.2"
    assert manifest.payload.availability is PayloadAvailability.CONSUMER
    assert manifest.config.schema_resource == "config-schema"
    assert manifest.capabilities.provides == ["demo.validate"]
    assert manifest.relations.companions == ["python-coding"]


@pytest.mark.parametrize(
    "fixture_path",
    sorted(_INVALID_PAYLOADS.glob("*.toml")),
    ids=lambda path: path.stem,
)
def test_invalid_payload_fixtures_are_rejected(fixture_path: Path) -> None:
    data = tomllib.loads(fixture_path.read_text(encoding="utf-8"))

    with pytest.raises(ValidationError):
        PayloadManifest.model_validate(data)


def test_payload_relations_and_capabilities_are_unique_and_sorted() -> None:
    data = _payload_data()
    capabilities = data["capabilities"]
    relations = data["relations"]
    assert isinstance(capabilities, dict)
    assert isinstance(relations, dict)
    capabilities["provides"] = ["z.last", "a.first"]
    relations["companions"] = ["z-standard", "a-standard"]

    forward = PayloadManifest.model_validate(data)
    capabilities["provides"] = list(reversed(capabilities["provides"]))
    relations["companions"] = list(reversed(relations["companions"]))
    reverse = PayloadManifest.model_validate(data)

    assert forward == reverse
    assert forward.capabilities.provides == ["a.first", "z.last"]
    assert forward.relations.companions == ["a-standard", "z-standard"]


def test_payload_rejects_duplicate_capability_or_relation() -> None:
    data = _payload_data()
    capabilities = data["capabilities"]
    assert isinstance(capabilities, dict)
    capabilities["provides"] = ["demo.validate", "demo.validate"]

    with pytest.raises(ValidationError, match="duplicate capability"):
        PayloadManifest.model_validate(data)


def test_load_payload_manifest_validates_directory_identity() -> None:
    manifest = load_payload_manifest(_VALID_PAYLOAD)

    assert manifest.payload.standard == "demo"
    assert manifest.payload.version.value == "1.2"


@pytest.mark.parametrize(
    ("standard", "version", "message"),
    [
        ("wrong-standard", "1.2", "standard identity"),
        ("demo", "9.9", "version directory"),
    ],
)
def test_load_payload_manifest_rejects_identity_mismatch(
    tmp_path: Path, standard: str, version: str, message: str
) -> None:
    payload_dir = tmp_path / "standards/demo/versions/1.2"
    payload_dir.mkdir(parents=True)
    source = _VALID_PAYLOAD.read_text(encoding="utf-8")
    source = source.replace('standard = "demo"', f'standard = "{standard}"')
    source = source.replace('version = "1.2"', f'version = "{version}"')
    payload_path = payload_dir / "payload.toml"
    payload_path.write_text(source, encoding="utf-8")

    with pytest.raises(PackageContractError, match=message):
        load_payload_manifest(payload_path)


def test_load_payload_manifest_wraps_invalid_utf8(tmp_path: Path) -> None:
    payload_dir = tmp_path / "standards/demo/versions/1.2"
    payload_dir.mkdir(parents=True)
    payload_path = payload_dir / "payload.toml"
    payload_path.write_bytes(b"\xff\xfe")

    with pytest.raises(PackageContractError) as exc_info:
        load_payload_manifest(payload_path)

    assert exc_info.type is PackageContractError


def test_option_schema_preserves_raw_bytes_and_parsed_document() -> None:
    manifest = load_payload_manifest(_VALID_PAYLOAD)
    schema = load_option_schema(_VALID_PAYLOAD.parent, manifest)

    assert isinstance(schema, PackageOptionSchema)
    assert schema.raw_bytes == _VALID_SCHEMA.read_bytes()
    assert schema.document == json.loads(schema.raw_bytes)
    assert schema.namespace == "standards.demo.config"


def test_option_schema_applies_deterministic_defaults_and_keeps_contract_version_ordinary() -> None:
    schema = load_option_schema(_VALID_PAYLOAD.parent, load_payload_manifest(_VALID_PAYLOAD))

    assert schema.resolve_options({}) == {
        "contract_version": "2026.1",
        "strict": True,
    }
    assert schema.resolve_options({"contract_version": "2027.1"}) == {
        "contract_version": "2027.1",
        "strict": True,
    }


def test_option_schema_rejects_unknown_or_invalid_options() -> None:
    schema = load_option_schema(_VALID_PAYLOAD.parent, load_payload_manifest(_VALID_PAYLOAD))

    with pytest.raises(PackageContractError, match="package options"):
        schema.resolve_options({"unknown": True})
    with pytest.raises(PackageContractError, match="package options"):
        schema.resolve_options({"strict": "yes"})


@pytest.mark.parametrize(
    "document",
    [
        {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"},
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": {"optional_without_default": {"type": "string"}},
        },
        {
            "$schema": "https://json-schema.org/draft/2019-09/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
    ],
)
def test_option_schema_rejects_open_incomplete_or_wrong_draft_documents(
    tmp_path: Path, document: dict[str, object]
) -> None:
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    (payload_dir / "config.schema.json").write_text(json.dumps(document), encoding="utf-8")
    manifest = PayloadManifest.model_validate(_payload_data())

    with pytest.raises(PackageContractError, match="option schema"):
        load_option_schema(payload_dir, manifest)


def test_option_schema_rejects_missing_required_option_without_default(tmp_path: Path) -> None:
    document = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {"required_value": {"type": "string"}},
        "required": ["required_value"],
    }
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    (payload_dir / "config.schema.json").write_text(json.dumps(document), encoding="utf-8")
    schema = load_option_schema(payload_dir, PayloadManifest.model_validate(_payload_data()))

    with pytest.raises(PackageContractError, match="package options"):
        schema.resolve_options({})


def test_option_schema_rejects_a_default_that_violates_its_property_schema(
    tmp_path: Path,
) -> None:
    document = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {"count": {"type": "integer", "default": "not-an-integer"}},
    }
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    (payload_dir / "config.schema.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(PackageContractError, match="default"):
        load_option_schema(payload_dir, PayloadManifest.model_validate(_payload_data()))
