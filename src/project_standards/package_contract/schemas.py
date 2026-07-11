"""Canonical JSON Schema generation and checked-in drift enforcement."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from project_standards.package_contract.catalog import CatalogSource
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import FamilyManifest
from project_standards.package_contract.payload import PayloadManifest

type SchemaDocument = dict[str, object]

_SCHEMA_BASE = (
    "https://raw.githubusercontent.com/L3DigitalNet/project-standards/main/"
    "src/project_standards/schemas"
)
_SCHEMA_MODELS: tuple[tuple[str, type[BaseModel]], ...] = (
    ("standard-family.schema.json", FamilyManifest),
    ("standard-payload.schema.json", PayloadManifest),
    ("standards-catalog-source.schema.json", CatalogSource),
)


def _close_objects(value: object) -> object:
    if isinstance(value, dict):
        source = cast("dict[str, object]", value)
        closed = {key: _close_objects(nested) for key, nested in source.items()}
        if closed.get("type") == "object" and "properties" in closed:
            closed["additionalProperties"] = False
        return closed
    if isinstance(value, list):
        return [_close_objects(nested) for nested in cast("list[object]", value)]
    return value


def package_schema_documents() -> dict[str, SchemaDocument]:
    """Return strict Draft 2020-12 schemas in stable filename order."""
    schemas: dict[str, SchemaDocument] = {}
    for name, model in _SCHEMA_MODELS:
        raw = cast("SchemaDocument", _close_objects(model.model_json_schema()))
        definitions = raw.get("$defs")
        if isinstance(definitions, dict):
            raw["$defs"] = {
                key: definitions[key] for key in sorted(cast("dict[str, object]", definitions))
            }
        schemas[name] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{_SCHEMA_BASE}/{name}",
            **raw,
        }
    return schemas


def package_schema_bytes() -> dict[str, bytes]:
    """Serialize every schema with sorted keys, two-space indent, and final newline."""
    return {
        name: (json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        for name, schema in package_schema_documents().items()
    }


def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o644)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


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
        _atomic_write(output / name, content)
    return True
