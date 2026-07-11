"""Strict V2 payload identity and package-option schema boundaries."""

from __future__ import annotations

import copy
import json
import math
import tomllib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Protocol, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from pydantic import Field, StringConstraints, ValidationError, field_validator, model_validator

from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import KebabId, StrictModel
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
    validate_path_collection,
)

type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class _SchemaValidationError(Protocol):
    @property
    def path(self) -> Iterable[object]: ...


class _SchemaValidator(Protocol):
    def iter_errors(self, instance: JsonValue) -> Iterator[_SchemaValidationError]: ...


ResourceId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
CapabilityId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$"),
]
MediaType = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*$"),
]


class PayloadAvailability(StrEnum):
    """Whether a payload is selectable by consumers or catalog-only."""

    CONSUMER = "consumer"
    REFERENCE_ONLY = "reference-only"
    INTERNAL = "internal"


class PayloadIdentity(StrictModel):
    """Exact package identity carried by one immutable payload."""

    standard: KebabId
    version: PackageVersion
    availability: PayloadAvailability


class ConfigDeclaration(StrictModel):
    """Bind package options to one declared schema resource."""

    schema_resource: ResourceId


def _sorted_unique(values: list[str], *, kind: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{kind} list contains a duplicate {kind}")
    return sorted(values)


class CapabilityDeclaration(StrictModel):
    """Version-specific behavior supplied by and requested from the platform."""

    provides: list[CapabilityId]
    consumes_platform: list[CapabilityId]

    @field_validator("provides", "consumes_platform")
    @classmethod
    def _unique_sorted_capabilities(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, kind="capability")


class RelationDeclaration(StrictModel):
    """Explicit package-family relationships; independence is the empty default."""

    companions: list[KebabId] = Field(default_factory=list)
    extends: list[KebabId] = Field(default_factory=list)
    conflicts: list[KebabId] = Field(default_factory=list)

    @field_validator("companions", "extends", "conflicts")
    @classmethod
    def _unique_sorted_relations(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, kind="relation")


class ResourceDeclaration(StrictModel):
    """Address one immutable payload-relative resource by stable metadata."""

    id: ResourceId
    role: ResourceId
    path: SafeRelativePath
    media_type: MediaType
    digest: Sha256Digest


class PayloadManifest(StrictModel):
    """The Task 3 payload slice; later tasks add outputs and execution contracts."""

    schema_version: Literal["1.0"]
    payload: PayloadIdentity
    config: ConfigDeclaration
    capabilities: CapabilityDeclaration
    relations: RelationDeclaration = Field(default_factory=RelationDeclaration)
    resources: list[ResourceDeclaration] = Field(min_length=1)

    @model_validator(mode="after")
    def _resource_identity_and_config_schema(self) -> PayloadManifest:
        ids: set[str] = set()
        for resource in self.resources:
            if resource.id in ids:
                raise ValueError("payload contains a duplicate resource ID")
            ids.add(resource.id)
        validate_path_collection(resource.path for resource in self.resources)

        schema_matches = [
            resource for resource in self.resources if resource.id == self.config.schema_resource
        ]
        if len(schema_matches) != 1 or schema_matches[0].role != "config-schema":
            raise ValueError("config schema_resource must identify one config-schema resource")
        return self


def _validation_summary(exc: ValidationError) -> str:
    summaries: list[str] = []
    for error in exc.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        location = ".".join(str(part) for part in error["loc"])
        summaries.append(f"{location or '<root>'}: {error['msg']}")
    return "; ".join(summaries)


def load_payload_manifest(path: Path) -> PayloadManifest:
    """Load one payload manifest and validate its version-qualified identity."""
    if path.name != "payload.toml":
        raise PackageContractError("payload manifest path must end in payload.toml")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PackageContractError(f"cannot read payload manifest {path}") from exc
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PackageContractError(f"payload manifest {path} is not valid TOML") from exc
    try:
        manifest = PayloadManifest.model_validate(raw)
    except ValidationError as exc:
        summary = _validation_summary(exc)
        raise PackageContractError(
            f"payload manifest {path} violates the V2 contract: {summary}"
        ) from exc

    version_dir = path.parent
    versions_dir = version_dir.parent
    standard_dir = versions_dir.parent
    if versions_dir.name != "versions":
        raise PackageContractError("payload manifest is not inside a versions directory")
    if manifest.payload.standard != standard_dir.name:
        raise PackageContractError("payload standard identity does not match its family directory")
    if manifest.payload.version.value != version_dir.name:
        raise PackageContractError("payload version does not match its version directory")
    return manifest


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PackageContractError("option schema contains a non-finite JSON number")
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in cast("list[object]", value)]
    if isinstance(value, dict):
        result: JsonObject = {}
        for key, item in cast("dict[object, object]", value).items():
            if not isinstance(key, str):
                raise PackageContractError("option schema contains a non-string object key")
            result[key] = _json_value(item)
        return result
    raise PackageContractError("option schema contains a non-JSON value")


def _json_object(value: object) -> JsonObject:
    parsed = _json_value(value)
    if not isinstance(parsed, dict):
        raise PackageContractError("option schema root must be a JSON object")
    return parsed


def _object_properties(schema: Mapping[str, JsonValue]) -> JsonObject:
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise PackageContractError("option schema properties must be an object")
    return properties


def _required_names(schema: Mapping[str, JsonValue]) -> set[str]:
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise PackageContractError("option schema required must be a string array")
    names = cast("list[str]", required)
    if len(names) != len(set(names)):
        raise PackageContractError("option schema required contains a duplicate name")
    return set(names)


def _validate_default_contract(schema: Mapping[str, JsonValue], *, location: str) -> None:
    properties = _object_properties(schema)
    required = _required_names(schema)
    if not required.issubset(properties):
        raise PackageContractError("option schema required names must exist in properties")
    for name, child in properties.items():
        if not isinstance(child, dict):
            raise PackageContractError("option schema property definitions must be objects")
        if name not in required and "default" not in child:
            raise PackageContractError(
                f"option schema property {location}{name} must be required or have a default"
            )
        if child.get("type") == "object":
            _validate_default_contract(child, location=f"{location}{name}.")


def _apply_defaults(schema: Mapping[str, JsonValue], configured: JsonObject) -> JsonObject:
    effective = copy.deepcopy(configured)
    for name, child in _object_properties(schema).items():
        if not isinstance(child, dict):
            continue
        if name not in effective and "default" in child:
            effective[name] = copy.deepcopy(child["default"])
        value = effective.get(name)
        if child.get("type") == "object" and isinstance(value, dict):
            effective[name] = _apply_defaults(child, value)
    return effective


def _validate_declared_defaults(schema: Mapping[str, JsonValue]) -> None:
    for child in _object_properties(schema).values():
        if not isinstance(child, dict):
            continue
        if "default" in child:
            validator = cast("_SchemaValidator", Draft202012Validator(child))
            if next(validator.iter_errors(child["default"]), None) is not None:
                raise PackageContractError("option schema contains an invalid default")
        if child.get("type") == "object":
            _validate_declared_defaults(child)


def _schema_error_location(error_path: Iterable[object]) -> str:
    parts = [str(part) for part in error_path]
    return ".".join(parts) or "<root>"


@dataclass(frozen=True, slots=True)
class PackageOptionSchema:
    """Preserve raw option-schema bytes beside their validated JSON document."""

    standard_id: str
    raw_bytes: bytes
    document: JsonObject

    @property
    def namespace(self) -> str:
        """Return the only consumer-config namespace this schema may validate."""
        return f"standards.{self.standard_id}.config"

    def resolve_options(self, configured: Mapping[str, JsonValue]) -> JsonObject:
        """Apply declared defaults, then validate and return effective options."""
        configured_object = _json_object(dict(configured))
        effective = _apply_defaults(self.document, configured_object)
        validator = cast("_SchemaValidator", Draft202012Validator(self.document))
        errors = sorted(
            validator.iter_errors(effective),
            key=lambda error: tuple(str(part) for part in error.path),
        )
        if errors:
            location = _schema_error_location(errors[0].path)
            raise PackageContractError(f"package options violate schema at {location}")
        return effective


def load_option_schema(
    payload_dir: Path,
    manifest: PayloadManifest,
) -> PackageOptionSchema:
    """Load and validate the package option schema selected by a payload."""
    resource = next(
        item for item in manifest.resources if item.id == manifest.config.schema_resource
    )
    schema_path = payload_dir / resource.path.normalized
    try:
        root = payload_dir.resolve(strict=True)
        resolved = schema_path.resolve(strict=True)
        if not resolved.is_relative_to(root) or schema_path.is_symlink() or not resolved.is_file():
            raise PackageContractError("option schema is not a contained regular file")
        raw_bytes = resolved.read_bytes()
        parsed = cast("object", json.loads(raw_bytes.decode("utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageContractError("option schema could not be read as UTF-8 JSON") from exc

    document = _json_object(parsed)
    if document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise PackageContractError("option schema must declare JSON Schema Draft 2020-12")
    if document.get("type") != "object" or document.get("additionalProperties") is not False:
        raise PackageContractError("option schema root must be a closed object")
    _validate_default_contract(document, location="")
    try:
        Draft202012Validator.check_schema(document)
    except JsonSchemaError as exc:
        raise PackageContractError("option schema is not a valid Draft 2020-12 schema") from exc
    _validate_declared_defaults(document)

    return PackageOptionSchema(
        standard_id=manifest.payload.standard,
        raw_bytes=raw_bytes,
        document=document,
    )
