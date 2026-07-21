from __future__ import annotations

import json
import stat
import tomllib
from pathlib import Path
from typing import Protocol, cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from project_standards.package_contract import PackageContractError
from project_standards.package_contract.catalog import CatalogSource
from project_standards.package_contract.family import FamilyManifest
from project_standards.package_contract.payload import PayloadManifest
from project_standards.package_contract.schemas import (
    SCHEMA_BASE,
    atomic_write,
    build_schema_documents,
    generate_package_schemas,
    package_schema_bytes,
    package_schema_documents,
    serialize_schema_documents,
)

_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_DIR = _ROOT / "src/project_standards/schemas"
_FIXTURES = _ROOT / "tests/fixtures/package_contract"
_MODELS: dict[str, type[BaseModel]] = {
    "standard-family.schema.json": FamilyManifest,
    "standard-payload.schema.json": PayloadManifest,
    "standards-catalog-source.schema.json": CatalogSource,
}
_VALID_FIXTURES = {
    "standard-family.schema.json": [_FIXTURES / "valid/minimal/standards/demo/standard.toml"],
    "standard-payload.schema.json": [
        _FIXTURES / "valid/minimal/standards/demo/versions/1.2/payload.toml"
    ],
    "standards-catalog-source.schema.json": [_FIXTURES / "valid/minimal/catalogs/5.toml"],
}
_INVALID_FIXTURES = {
    "standard-family.schema.json": sorted((_FIXTURES / "invalid/family").glob("*.toml")),
    "standard-payload.schema.json": sorted((_FIXTURES / "invalid/payload").glob("*.toml")),
    "standards-catalog-source.schema.json": sorted((_FIXTURES / "invalid/catalog").glob("*.toml")),
}
_MODEL_ONLY = {
    "invalid/family/duplicate-version.toml",
    "invalid/family/unsafe-payload.toml",
}


class _SchemaValidator(Protocol):
    def validate(self, instance: object) -> None: ...


def _load_toml(path: Path) -> dict[str, object]:
    return cast("dict[str, object]", tomllib.loads(path.read_text(encoding="utf-8")))


def _walk_objects(value: object) -> None:
    if isinstance(value, dict):
        mapping = cast("dict[str, object]", value)
        if mapping.get("type") == "object" and "properties" in mapping:
            assert mapping.get("additionalProperties") is False
        for nested in mapping.values():
            _walk_objects(nested)
    elif isinstance(value, list):
        for nested in cast("list[object]", value):
            _walk_objects(nested)


def _validator(schema: dict[str, object]) -> _SchemaValidator:
    return cast("_SchemaValidator", Draft202012Validator(schema))


def test_shared_schema_builders__package_models__match_package_outputs() -> None:
    documents = build_schema_documents(tuple(_MODELS.items()), SCHEMA_BASE)

    assert documents == package_schema_documents()
    assert serialize_schema_documents(documents) == package_schema_bytes()


def test_generated_schema_documents_are_closed_draft_2020_12_contracts() -> None:
    schemas = package_schema_documents()

    assert set(schemas) == set(_MODELS)
    for name, schema in schemas.items():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        schema_id = schema["$id"]
        assert isinstance(schema_id, str)
        assert schema_id.endswith(f"/src/project_standards/schemas/{name}")
        assert schema["additionalProperties"] is False
        definitions = cast("dict[str, object]", schema.get("$defs", {}))
        assert list(definitions) == sorted(definitions)
        _walk_objects(schema)
        Draft202012Validator.check_schema(schema)


def test_payload_schema_exposes_optional_owner_resolution_pointer() -> None:
    schema = package_schema_documents()["standard-payload.schema.json"]
    definitions = cast("dict[str, object]", schema["$defs"])
    signature = cast("dict[str, object]", definitions["LegacySignatureDeclaration"])
    properties = cast("dict[str, object]", signature["properties"])

    assert "consumer_owned_intent_pointer" in properties
    assert "consumer_owned_intent_pointer" not in cast("list[str]", signature["required"])


def test_payload_schema_documents_materialization_option_spellings() -> None:
    schema = package_schema_documents()["standard-payload.schema.json"]
    definitions = cast("dict[str, object]", schema["$defs"])
    predicate = cast("dict[str, object]", definitions["MaterializationPredicate"])
    properties = cast("dict[str, object]", predicate["properties"])
    option = cast("dict[str, object]", properties["option"])

    assert option["description"] == (
        "Bare top-level option name or absolute multi-segment option pointer; "
        "single-segment pointers are noncanonical."
    )
    assert len(cast("list[object]", option["anyOf"])) == 2


def test_generated_schema_bytes_are_canonical_and_checked_in() -> None:
    first = package_schema_bytes()
    second = package_schema_bytes()

    assert first == second
    for name, content in first.items():
        assert content.endswith(b"\n")
        assert json.loads(content) == package_schema_documents()[name]
        assert (_SCHEMA_DIR / name).read_bytes() == content


def test_prettier_does_not_own_generated_schema_or_fixture_bytes() -> None:
    ignores = set(Path(".prettierignore").read_text(encoding="utf-8").splitlines())

    assert {
        "src/project_standards/schemas/standard-family.schema.json",
        "src/project_standards/schemas/standard-payload.schema.json",
        "src/project_standards/schemas/standards-catalog-source.schema.json",
        "tests/fixtures/package_contract/",
    } <= ignores


@pytest.mark.parametrize("schema_name", sorted(_MODELS))
def test_valid_toml_fixtures_pass_their_generated_schema(schema_name: str) -> None:
    validator = _validator(package_schema_documents()[schema_name])

    for fixture in _VALID_FIXTURES[schema_name]:
        validator.validate(_load_toml(fixture))


@pytest.mark.parametrize("schema_name", sorted(_MODELS))
def test_every_invalid_toml_fixture_has_locked_model_and_schema_behavior(
    schema_name: str,
) -> None:
    model = _MODELS[schema_name]
    validator = _validator(package_schema_documents()[schema_name])

    for fixture in _INVALID_FIXTURES[schema_name]:
        document = _load_toml(fixture)
        with pytest.raises(PydanticValidationError):
            model.model_validate(document)
        relative = fixture.relative_to(_FIXTURES).as_posix()
        if relative in _MODEL_ONLY:
            validator.validate(document)
        else:
            with pytest.raises(JsonSchemaValidationError):
                validator.validate(document)


def test_schema_generation_writes_then_checks_without_mutating_stale_output(
    tmp_path: Path,
) -> None:
    assert generate_package_schemas(tmp_path, check=False)
    generated = tmp_path / "src/project_standards/schemas"
    expected = {path.name: path.read_bytes() for path in generated.iterdir()}
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o644 for path in generated.iterdir())
    assert not list(generated.glob(".*.schema.json.*"))
    assert generate_package_schemas(tmp_path, check=True)

    stale_path = generated / "standard-payload.schema.json"
    stale_path.write_bytes(stale_path.read_bytes() + b" ")
    stale = {path.name: path.read_bytes() for path in generated.iterdir()}

    assert not generate_package_schemas(tmp_path, check=True)
    assert {path.name: path.read_bytes() for path in generated.iterdir()} == stale
    assert generate_package_schemas(tmp_path, check=False)
    assert {path.name: path.read_bytes() for path in generated.iterdir()} == expected


def test_atomic_write__fsync_failure__cleans_staged_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "schema.json"

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr("project_standards.package_contract._write.os.fsync", fail_fsync)

    with pytest.raises(OSError, match="injected fsync failure"):
        atomic_write(target, b"{}\n")

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_schema_generation_rejects_symlinked_output_ancestors(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "src").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PackageContractError, match="symlink"):
        generate_package_schemas(tmp_path, check=False)

    assert not (outside / "project_standards").exists()
