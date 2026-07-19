from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.package_contract import PackageContractError
from project_standards.package_contract.payload import (
    LegacySignatureDeclaration,
    MaterializationPredicate,
    PackageOptionSchema,
    PayloadAvailability,
    PayloadManifest,
    load_option_schema,
    load_payload_manifest,
)
from tests.control_plane.planner_helpers import write_payload

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/package_contract"
_VALID_PAYLOAD = _FIXTURES / "valid/minimal/standards/demo/versions/1.2/payload.toml"
_VALID_SCHEMA = _VALID_PAYLOAD.parent / "config.schema.json"
_INVALID_PAYLOADS = _FIXTURES / "invalid/payload"


def _digest(character: str = "0") -> str:
    return f"sha256:{character * 64}"


def test_materialization_predicate_accepts_canonical_option_pointer() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/type_checker/name", "equals": "basedpyright"}
    )

    assert predicate.matches({"type_checker": {"name": "basedpyright", "mode": "strict"}})
    assert not predicate.matches({"type_checker": {"name": "pyright", "mode": "strict"}})


def test_materialization_predicate_pointer_misses_fail_closed() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/type_checker/name", "equals": "basedpyright"}
    )

    assert not predicate.matches({})
    assert not predicate.matches({"type_checker": "basedpyright"})
    assert not predicate.matches({"type_checker": {"mode": "strict"}})


def test_materialization_predicate_contains_matches_nested_arrays() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/coverage/patch", "contains": "subprocess"}
    )

    assert predicate.matches({"coverage": {"patch": ["subprocess"]}})
    assert not predicate.matches({"coverage": {"patch": []}})
    assert not predicate.matches({"coverage": {}})


def test_materialization_predicate_equals_stays_type_exact_at_nested_leaves() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/coverage/parallel", "equals": True}
    )

    assert predicate.matches({"coverage": {"parallel": True}})
    assert not predicate.matches({"coverage": {"parallel": 1}})


@pytest.mark.parametrize(
    "option",
    [
        "/type_checker",
        "/type_checker/",
        "//name",
        "/type_checker/~1name",
        "/type_checker/0",
        "/Type_Checker/name",
        "/type_checker/naïve",
        "type_checker/name",
    ],
)
def test_materialization_predicate_rejects_noncanonical_pointers(option: str) -> None:
    with pytest.raises(ValidationError):
        MaterializationPredicate.model_validate({"option": option, "equals": "x"})


def test_materialization_predicate_top_level_spelling_is_unchanged() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "workflow_ownership", "equals": "managed"}
    )

    assert predicate.matches({"workflow_ownership": "managed"})
    assert not predicate.matches({"workflow_ownership": "consumer-owned"})


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


def _whole_file_signature(**overrides: object) -> dict[str, object]:
    signature: dict[str, object] = {
        "id": "legacy-workflow",
        "kind": "whole-file",
        "targets": [".github/workflows/check.yml"],
        "known_content_digests": [_digest("a")],
    }
    signature.update(overrides)
    return signature


def test_owner_resolution_pointer_is_canonical_and_target_specific() -> None:
    signature = LegacySignatureDeclaration.model_validate(
        _whole_file_signature(consumer_owned_intent_pointer="/python_tooling/workflow_ownership")
    )

    assert signature.consumer_owned_intent_pointer == ("/python_tooling/workflow_ownership")


def test_owner_resolution_schema_description_distinguishes_package_history() -> None:
    schema = LegacySignatureDeclaration.model_json_schema()

    assert schema["description"] == (
        "Declare exact package-history bytes and an optional target-bound "
        "consumer-owned preservation exception."
    )


@pytest.mark.parametrize(
    "update",
    [
        {
            "kind": "bounded-block",
            "format": "yaml",
            "begin": "# begin",
            "end": "# end",
        },
        {"targets": ["one.yml", "two.yml"]},
        {"consumer_owned_intent_pointer": "python_tooling/workflow_ownership"},
        {"consumer_owned_intent_pointer": "/python_tooling/~2workflow"},
    ],
)
def test_owner_resolution_declaration_rejects_ambiguous_shapes(
    update: dict[str, object],
) -> None:
    values = _whole_file_signature(
        consumer_owned_intent_pointer="/python_tooling/workflow_ownership"
    )
    values.update(update)

    with pytest.raises(ValidationError):
        LegacySignatureDeclaration.model_validate(values)


def test_payload_rejects_reused_owner_resolution_pointer() -> None:
    data = _payload_data()
    data["legacy_signatures"] = [
        _whole_file_signature(
            id="first-workflow",
            targets=["first.yml"],
            consumer_owned_intent_pointer="/demo/workflow_ownership",
        ),
        _whole_file_signature(
            id="second-workflow",
            targets=["second.yml"],
            consumer_owned_intent_pointer="/demo/workflow_ownership",
        ),
    ]

    with pytest.raises(ValidationError, match="reuses a consumer-owned intent pointer"):
        PayloadManifest.model_validate(data)


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


def _add_relation_evidence(data: dict[str, object]) -> None:
    relations = cast("dict[str, object]", data["relations"])
    resources = cast("list[dict[str, object]]", data["resources"])
    relations["extends"] = ["base-standard"]
    resources.append(
        {
            "id": "base-standard-extension-adr",
            "role": "relation-evidence",
            "path": "decisions/base-standard-extension.md",
            "media_type": "text/markdown",
            "digest": _digest("4"),
        }
    )
    data["relation_evidence"] = [
        {
            "kind": "extends",
            "target": "base-standard",
            "resource": "base-standard-extension-adr",
        }
    ]


def test_payload_accepts_payload_owned_relation_evidence() -> None:
    data = _payload_data()
    _add_relation_evidence(data)

    manifest = PayloadManifest.model_validate(data)

    assert manifest.relation_evidence[0].target == "base-standard"
    assert manifest.relation_evidence[0].resource == "base-standard-extension-adr"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing", "exactly match"),
        ("orphan", "exactly match"),
        ("duplicate", "duplicate relation evidence"),
        ("missing-resource", "relation-evidence resource"),
        ("wrong-role", "relation-evidence resource"),
        ("wrong-media", "relation-evidence resource"),
    ],
)
def test_payload_rejects_missing_or_invalid_relation_evidence(mutation: str, expected: str) -> None:
    data = _payload_data()
    _add_relation_evidence(data)
    evidence = cast("list[dict[str, object]]", data["relation_evidence"])
    relations = cast("dict[str, object]", data["relations"])
    resources = cast("list[dict[str, object]]", data["resources"])
    if mutation == "missing":
        evidence.clear()
    elif mutation == "orphan":
        relations["extends"] = []
    elif mutation == "duplicate":
        evidence.append(dict(evidence[0]))
    elif mutation == "missing-resource":
        evidence[0]["resource"] = "unknown"
    else:
        resource = resources[-1]
        if mutation == "wrong-role":
            resource["role"] = "decision"
        else:
            resource["media_type"] = "application/json"

    with pytest.raises(ValidationError, match=expected):
        PayloadManifest.model_validate(data)


def _add_legacy_state_migration(data: dict[str, object]) -> None:
    data["legacy_states"] = [{"id": "v4-demo"}]
    data["migrations"] = [
        {
            "id": "legacy-v4-to-1",
            "from": "legacy:v4-demo",
            "to": "package:1.2",
            "mode": "manual",
            "instructions": "README.md",
            "reversible": False,
            "affected": ["config:*"],
            "signatures": [],
        }
    ]


def test_payload_accepts_an_explicit_registered_legacy_state() -> None:
    data = _payload_data()
    _add_legacy_state_migration(data)

    manifest = PayloadManifest.model_validate(data)

    assert manifest.legacy_states[0].id == "v4-demo"
    assert manifest.migrations[0].from_endpoint.legacy_state == "v4-demo"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("unknown", "registered legacy state"),
        ("unused", "unused legacy state"),
        ("duplicate", "duplicate legacy state"),
    ],
)
def test_payload_rejects_unknown_unused_or_duplicate_legacy_states(
    mutation: str, expected: str
) -> None:
    data = _payload_data()
    _add_legacy_state_migration(data)
    states = cast("list[dict[str, object]]", data["legacy_states"])
    migrations = cast("list[dict[str, object]]", data["migrations"])
    if mutation == "unknown":
        migrations[0]["from"] = "legacy:unknown"
    elif mutation == "unused":
        states.append({"id": "unused"})
    else:
        states.append({"id": "v4-demo"})

    with pytest.raises(ValidationError, match=expected):
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


def test_option_schema_default_resolves_local_root_ref(tmp_path: Path) -> None:
    document = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {"mode": {"type": "string", "enum": ["safe"]}},
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mode": {"$ref": "#/$defs/mode", "default": "safe"},
        },
    }
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    (payload_dir / "config.schema.json").write_text(json.dumps(document), encoding="utf-8")

    schema = load_option_schema(
        payload_dir,
        PayloadManifest.model_validate(_payload_data()),
    )

    assert schema.resolve_options({}) == {"mode": "safe"}


def test_option_schema_missing_ref_is_controlled_for_defaults_and_options(
    tmp_path: Path,
) -> None:
    base = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
    }
    default_dir = tmp_path / "default"
    default_dir.mkdir()
    default_document = {
        **base,
        "properties": {
            "mode": {"$ref": "#/$defs/missing", "default": "safe"},
        },
    }
    (default_dir / "config.schema.json").write_text(
        json.dumps(default_document),
        encoding="utf-8",
    )

    with pytest.raises(
        PackageContractError,
        match=r"option schema default cannot be validated against a \$ref property",
    ):
        load_option_schema(
            default_dir,
            PayloadManifest.model_validate(_payload_data()),
        )

    options_dir = tmp_path / "options"
    options_dir.mkdir()
    options_document = {
        **base,
        "properties": {"mode": {"$ref": "#/$defs/missing"}},
        "required": ["mode"],
    }
    (options_dir / "config.schema.json").write_text(
        json.dumps(options_document),
        encoding="utf-8",
    )
    schema = load_option_schema(
        options_dir,
        PayloadManifest.model_validate(_payload_data()),
    )

    with pytest.raises(
        PackageContractError,
        match="package options schema contains an unresolvable reference",
    ):
        schema.resolve_options({"mode": "safe"})


_ENGINE_SCHEMA: dict[str, object] = {
    "engine": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"name": {"enum": ["alpha", "beta"]}},
        "required": ["name"],
    }
}


def _predicate_payload(tmp_path: Path, option: str) -> InstalledPayload:
    return write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "conditional",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/alpha",
                "content": b'[tool.alpha]\nmode = "on"\n',
                "when_any": [{"option": option, "equals": "alpha"}],
            }
        ],
        option_properties=_ENGINE_SCHEMA,
    )


def test_option_schema_accepts_predicates_naming_declared_paths(tmp_path: Path) -> None:
    payload = _predicate_payload(tmp_path, "/engine/name")

    load_option_schema(payload.root, payload.manifest)


@pytest.mark.parametrize("option", ["undeclared", "/engine/nmae"])
def test_option_schema_rejects_predicate_naming_undeclared_path(
    tmp_path: Path,
    option: str,
) -> None:
    payload = _predicate_payload(tmp_path, option)

    with pytest.raises(PackageContractError, match="undeclared option path"):
        load_option_schema(payload.root, payload.manifest)


def test_option_schema_rejects_artifact_predicate_naming_undeclared_path(
    tmp_path: Path,
) -> None:
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[
            {
                "id": "conditional",
                "target": "config.txt",
                "content": b"configured\n",
                "when_any": [{"option": "/engine/nmae", "equals": "alpha"}],
            }
        ],
        option_properties=_ENGINE_SCHEMA,
    )

    with pytest.raises(PackageContractError, match="undeclared option path"):
        load_option_schema(payload.root, payload.manifest)


@pytest.mark.parametrize(
    "engine_schema",
    [
        {"type": ["object", "null"], "properties": {"name": {"type": "string"}}},
        {"anyOf": [{"type": "object"}, {"type": "null"}]},
        {"oneOf": [{"type": "object"}]},
        {"allOf": [{"type": "object"}]},
        {"$ref": "#/$defs/engine"},
        {"properties": {"name": {"type": "string"}}},
    ],
)
def test_option_schema_rejects_predicate_through_non_object_intermediate(
    tmp_path: Path,
    engine_schema: dict[str, object],
) -> None:
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "conditional",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/alpha",
                "content": b'[tool.alpha]\nmode = "on"\n',
                "when_any": [{"option": "/engine/name", "equals": "alpha"}],
            }
        ],
        option_properties={"engine": engine_schema},
    )

    with pytest.raises(PackageContractError, match="non-object option"):
        load_option_schema(payload.root, payload.manifest)


def test_every_shipped_payload_satisfies_the_predicate_option_contract() -> None:
    for manifest_path in sorted(
        Path(__file__).resolve().parents[2].glob("standards/*/versions/*/payload.toml")
    ):
        manifest = load_payload_manifest(manifest_path)
        load_option_schema(manifest_path.parent, manifest)
