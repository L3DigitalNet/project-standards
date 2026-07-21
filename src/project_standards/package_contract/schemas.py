"""Canonical JSON Schema generation and checked-in drift enforcement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from project_standards.package_contract._write import atomic_write
from project_standards.package_contract.catalog import CatalogSource
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import FamilyManifest
from project_standards.package_contract.payload import PayloadManifest

type SchemaDocument = dict[str, object]

SCHEMA_BASE = (
    "https://raw.githubusercontent.com/L3DigitalNet/project-standards/main/"
    "src/project_standards/schemas"
)
_SCHEMA_MODELS: tuple[tuple[str, type[BaseModel]], ...] = (
    ("standard-family.schema.json", FamilyManifest),
    ("standard-payload.schema.json", PayloadManifest),
    ("standards-catalog-source.schema.json", CatalogSource),
)


def close_objects(value: object) -> object:
    if isinstance(value, dict):
        source = cast("dict[str, object]", value)
        closed = {key: close_objects(nested) for key, nested in source.items()}
        if closed.get("type") == "object" and "properties" in closed:
            closed["additionalProperties"] = False
        return closed
    if isinstance(value, list):
        return [close_objects(nested) for nested in cast("list[object]", value)]
    return value


def build_schema_documents(
    models: tuple[tuple[str, type[BaseModel]], ...],
    base: str,
) -> dict[str, SchemaDocument]:
    """Return strict Draft 2020-12 schemas in stable filename order."""
    schemas: dict[str, SchemaDocument] = {}
    for name, model in models:
        raw = cast("SchemaDocument", close_objects(model.model_json_schema()))
        definitions = raw.get("$defs")
        if isinstance(definitions, dict):
            raw["$defs"] = {
                key: definitions[key] for key in sorted(cast("dict[str, object]", definitions))
            }
        schemas[name] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{base}/{name}",
            **raw,
        }
    return schemas


def serialize_schema_documents(documents: dict[str, SchemaDocument]) -> dict[str, bytes]:
    """Serialize every schema with sorted keys, two-space indent, and final newline."""
    return {
        name: (json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        for name, schema in documents.items()
    }


def package_schema_documents() -> dict[str, SchemaDocument]:
    """Return strict package schemas in stable filename order."""
    return build_schema_documents(_SCHEMA_MODELS, SCHEMA_BASE)


def package_schema_bytes() -> dict[str, bytes]:
    """Serialize package schemas with canonical JSON formatting."""
    return serialize_schema_documents(package_schema_documents())


def generate_package_schemas(root: Path, *, check: bool) -> bool:
    """Write canonical schemas, or compare them without mutation in check mode."""
    try:
        if root.is_symlink() or not root.is_dir():
            raise PackageContractError("schema generation root must be a regular directory")
    except OSError as exc:
        raise PackageContractError("schema generation root could not be inspected") from exc

    output = root / "src/project_standards/schemas"
    try:
        output_ancestors = (
            root / "src",
            root / "src/project_standards",
            output,
        )
        if any(path.is_symlink() for path in output_ancestors):
            raise PackageContractError("schema output path cannot contain a symlink")
        if not check:
            output.mkdir(parents=True, exist_ok=True)
        expected = package_schema_bytes()
        for name in expected:
            if (output / name).is_symlink():
                raise PackageContractError("schema output file cannot be a symlink")
    except OSError as exc:
        raise PackageContractError("schema output path could not be prepared") from exc

    if check:
        try:
            return all(
                (output / name).read_bytes() == content for name, content in expected.items()
            )
        except OSError:
            return False

    for name, content in expected.items():
        atomic_write(output / name, content)
    return True
