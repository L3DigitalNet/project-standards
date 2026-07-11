"""Strict V2 payload identity and package-option schema boundaries."""

from __future__ import annotations

import copy
import json
import math
import re
import tomllib
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Protocol, cast
from urllib.parse import unquote_to_bytes

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
PosixMode = Annotated[str, StringConstraints(pattern=r"^0[0-7]{3}$")]
SharedIdentity = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(?:[./_-][a-z0-9]+)*$"),
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


class ArtifactPolicy(StrEnum):
    """Lifecycle policies supported by managed package outputs."""

    MANAGED = "managed"
    CREATE_ONLY = "create-only"


class AdapterKind(StrEnum):
    """Semantic container adapters supported by the V1 contribution contract."""

    WHOLE_FILE = "whole-file"
    TOML = "toml"
    JSON = "json"
    JSONC = "jsonc"
    YAML = "yaml"
    EDITORCONFIG = "editorconfig"
    MARKDOWN_BLOCK = "markdown-block"


class WholeArtifactDeclaration(StrictModel):
    """Declare exclusive ownership of one complete repository file."""

    id: ResourceId
    target: SafeRelativePath
    source: SafeRelativePath
    digest: Sha256Digest
    policy: ArtifactPolicy
    mode: PosixMode | None = None


@dataclass(frozen=True, slots=True)
class SemanticAddress:
    """Identify the smallest normalized semantic unit owned by a contribution."""

    target: SafeRelativePath
    adapter: AdapterKind
    scope: str


_BAD_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-F]{2})")
_COMPONENT_DELIMITERS = frozenset("%#=")


def _canonical_component(value: str) -> str:
    if not value or _BAD_PERCENT_ESCAPE.search(value):
        raise ValueError("selector component is empty or has an invalid percent escape")
    try:
        decoded = unquote_to_bytes(value).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("selector component is not valid percent-encoded UTF-8") from exc
    if not decoded.isprintable() or unicodedata.normalize("NFC", decoded) != decoded:
        raise ValueError("selector component is not canonical printable UTF-8")
    canonical_parts: list[str] = []
    for character in decoded:
        if character not in _COMPONENT_DELIMITERS:
            canonical_parts.append(character)
            continue
        canonical_parts.extend(f"%{byte:02X}" for byte in character.encode("utf-8"))
    canonical = "".join(canonical_parts)
    if canonical != value:
        raise ValueError("selector component must use canonical percent encoding")
    return canonical


def _json_pointer(value: str) -> str:
    if not value.startswith("/") or not value.isprintable():
        raise ValueError("selector must contain a non-root RFC 6901 JSON Pointer")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("JSON Pointer must use NFC spelling")
    for segment in value.split("/")[1:]:
        index = 0
        while index < len(segment):
            if segment[index] == "~":
                if index + 1 >= len(segment) or segment[index + 1] not in {"0", "1"}:
                    raise ValueError("JSON Pointer contains an invalid RFC 6901 escape")
                index += 2
            else:
                index += 1
    return value


def _keyed_set_scope(body: str) -> str:
    if "#" not in body:
        raise ValueError("keyed-set selector requires an identity key and value")
    pointer, binding = body.rsplit("#", 1)
    if "=" not in binding:
        raise ValueError("keyed-set selector requires an identity key and value")
    key, identity = binding.split("=", 1)
    return f"keyed-set:{_json_pointer(pointer)}#{_canonical_component(key)}={_canonical_component(identity)}"


def normalize_scope(adapter: AdapterKind, scope: str) -> str:
    """Validate and return one canonical selector for its declared adapter."""
    if adapter is AdapterKind.WHOLE_FILE:
        if scope != "$file":
            raise ValueError("whole-file adapter requires the $file selector")
        return scope

    if adapter is AdapterKind.TOML:
        for prefix in ("key:", "table:"):
            if scope.startswith(prefix):
                return f"{prefix}{_json_pointer(scope.removeprefix(prefix))}"
        raise ValueError("TOML selector must own one key or table")

    if adapter in {AdapterKind.JSON, AdapterKind.JSONC, AdapterKind.YAML}:
        if scope.startswith("key:"):
            return f"key:{_json_pointer(scope.removeprefix('key:'))}"
        if scope.startswith("keyed-set:"):
            return _keyed_set_scope(scope.removeprefix("keyed-set:"))
        if adapter in {AdapterKind.JSON, AdapterKind.JSONC} and scope.startswith("set:"):
            body = scope.removeprefix("set:")
            marker = "#value="
            if marker not in body:
                raise ValueError("set selector requires a stable value identity")
            pointer, identity = body.rsplit(marker, 1)
            return f"set:{_json_pointer(pointer)}{marker}{_canonical_component(identity)}"
        raise ValueError("structured selector is not supported by its adapter")

    if adapter is AdapterKind.EDITORCONFIG:
        if not scope.startswith("property:") or "#" not in scope:
            raise ValueError("EditorConfig selector requires a section/property pair")
        section, key = scope.removeprefix("property:").rsplit("#", 1)
        return f"property:{_canonical_component(section)}#{_canonical_component(key)}"

    if adapter is AdapterKind.MARKDOWN_BLOCK:
        if not scope.startswith("block:"):
            raise ValueError("Markdown selector requires one block ID")
        return f"block:{_canonical_component(scope.removeprefix('block:'))}"

    raise ValueError("unknown semantic adapter")


class ContributionDeclaration(StrictModel):
    """Declare ownership of one normalized semantic unit in a shared file."""

    id: ResourceId
    target: SafeRelativePath
    adapter: AdapterKind
    scope: str
    policy: ArtifactPolicy
    source: SafeRelativePath | None = None
    source_digest: Sha256Digest | None = None
    provider: ResourceId | None = None
    shared_identity: SharedIdentity | None = None

    @model_validator(mode="after")
    def _source_and_scope_contract(self) -> ContributionDeclaration:
        has_source = self.source is not None
        has_provider = self.provider is not None
        if has_source == has_provider:
            raise ValueError("contribution requires exactly one source or provider")
        if has_source != (self.source_digest is not None):
            raise ValueError("static contribution source and source_digest must appear together")
        object.__setattr__(self, "scope", normalize_scope(self.adapter, self.scope))
        return self

    @property
    def address(self) -> SemanticAddress:
        """Return the normalized ownership address used for overlap checks."""
        return SemanticAddress(self.target, self.adapter, self.scope)


def _scope_parts(scope: str) -> tuple[str, str, str]:
    kind, body = scope.split(":", 1) if ":" in scope else (scope, "")
    if kind == "set":
        pointer, identity = body.rsplit("#value=", 1)
        return (kind, pointer, identity)
    if kind == "keyed-set":
        pointer, identity = body.rsplit("#", 1)
        return (kind, pointer, identity)
    if kind in {"key", "table"}:
        return (kind, body, "")
    return (kind, body, "")


def _pointer_contains(parent: str, child: str) -> bool:
    return parent == child or child.startswith(f"{parent}/")


def _scopes_overlap(left: ContributionDeclaration, right: ContributionDeclaration) -> bool:
    if left.scope == right.scope:
        return True
    if left.adapter is AdapterKind.WHOLE_FILE or right.adapter is AdapterKind.WHOLE_FILE:
        return True
    if left.adapter in {AdapterKind.EDITORCONFIG, AdapterKind.MARKDOWN_BLOCK}:
        return False

    left_kind, left_pointer, _ = _scope_parts(left.scope)
    right_kind, right_pointer, _ = _scope_parts(right.scope)
    owner_kinds = {"key", "table"}
    if left_kind in owner_kinds and _pointer_contains(left_pointer, right_pointer):
        return True
    if right_kind in owner_kinds and _pointer_contains(right_pointer, left_pointer):
        return True
    return left_pointer == right_pointer and left_kind != right_kind


class PayloadManifest(StrictModel):
    """The declarative payload contract; later tasks add execution declarations."""

    schema_version: Literal["1.0"]
    payload: PayloadIdentity
    config: ConfigDeclaration
    capabilities: CapabilityDeclaration
    relations: RelationDeclaration = Field(default_factory=RelationDeclaration)
    resources: list[ResourceDeclaration] = Field(min_length=1)
    artifacts: list[WholeArtifactDeclaration] = Field(default_factory=list)
    contributions: list[ContributionDeclaration] = Field(default_factory=list)

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

        required_media = {
            "canonical-standard": "text/markdown",
            "agent-summary": "text/markdown",
            "config-schema": "application/schema+json",
            "adoption-guide": "text/markdown",
        }
        role_counts = Counter(resource.role for resource in self.resources)
        required_roles = {"canonical-standard", "agent-summary", "config-schema"}
        if any(role_counts[role] == 0 for role in required_roles):
            raise ValueError("payload is missing a required resource role")
        if any(role_counts[role] != 1 for role in required_roles):
            raise ValueError("payload must declare exactly one of each required resource role")
        has_adoption = role_counts["adoption-guide"] > 0
        if role_counts["adoption-guide"] > 1:
            raise ValueError("payload must declare exactly one adoption-guide when present")
        if self.payload.availability is PayloadAvailability.CONSUMER and not has_adoption:
            raise ValueError("consumer payload requires an adoption-guide resource")
        if self.payload.availability is not PayloadAvailability.CONSUMER and has_adoption:
            raise ValueError("non-consumer payload must not declare an adoption-guide resource")
        for resource in self.resources:
            expected_media = required_media.get(resource.role)
            if expected_media is not None and resource.media_type != expected_media:
                raise ValueError("required resource role has the wrong media type")

        artifact_ids: set[str] = set()
        artifact_targets: set[str] = set()
        for artifact in self.artifacts:
            if artifact.id in artifact_ids:
                raise ValueError("payload contains a duplicate artifact ID")
            artifact_ids.add(artifact.id)
            target = artifact.target.normalized.as_posix()
            if target in artifact_targets:
                raise ValueError("whole artifacts overlap one repository target")
            artifact_targets.add(target)

        contribution_ids: set[str] = set()
        shared: dict[str, tuple[object, ...]] = {}
        for index, contribution in enumerate(self.contributions):
            if contribution.id in contribution_ids:
                raise ValueError("payload contains a duplicate contribution ID")
            contribution_ids.add(contribution.id)
            target = contribution.target.normalized.as_posix()
            if target in artifact_targets:
                raise ValueError("whole artifact overlaps a semantic contribution target")
            for other in self.contributions[:index]:
                if other.target != contribution.target:
                    continue
                if other.adapter is not contribution.adapter:
                    raise ValueError("one semantic target declares more than one adapter")
                if _scopes_overlap(other, contribution):
                    raise ValueError("semantic contribution scopes overlap")
            if contribution.shared_identity is not None:
                signature = (
                    target,
                    contribution.adapter.value,
                    contribution.scope,
                    contribution.source.original if contribution.source else None,
                    contribution.source_digest.value if contribution.source_digest else None,
                    contribution.provider,
                    contribution.policy.value,
                )
                previous = shared.setdefault(contribution.shared_identity, signature)
                if previous != signature:
                    raise ValueError("shared identity declarations do not normalize identically")
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
