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
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Protocol, cast
from urllib.parse import unquote_to_bytes

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from pydantic import (
    Field,
    GetCoreSchemaHandler,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import CoreSchema, core_schema
from referencing.exceptions import Unresolvable

from project_standards.package_contract.diagnostics import (
    PackageContractError,
    validation_summary,
)
from project_standards.package_contract.family import KebabId, StrictModel
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
    validate_json_pointer,
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

    def evolve(self, **changes: object) -> _SchemaValidator: ...


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
OptionName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")]
OptionPointer = Annotated[
    str,
    StringConstraints(pattern=r"^(?:/[a-z][a-z0-9]*(?:_[a-z0-9]+)*){2,}$"),
]
AffectedIdentity = Annotated[
    str,
    StringConstraints(
        pattern=r"^(?:config:\*|artifact:[a-z0-9]+(?:-[a-z0-9]+)*|contribution:[a-z0-9]+(?:-[a-z0-9]+)*)$"
    ),
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


class RelationEvidenceKind(StrEnum):
    """Relationship kinds whose composition constraints require an ADR."""

    EXTENDS = "extends"
    CONFLICTS = "conflicts"


class RelationEvidenceDeclaration(StrictModel):
    """Bind one constraining relationship to immutable decision evidence."""

    kind: RelationEvidenceKind
    target: KebabId
    resource: ResourceId


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


class MaterializationPredicate(StrictModel):
    """Match a bare top-level option or an absolute nested option pointer."""

    option: OptionName | OptionPointer = Field(
        description=(
            "Bare top-level option name or absolute multi-segment option pointer; "
            "single-segment pointers are noncanonical."
        )
    )
    equals: bool | int | float | str | None = None
    contains: bool | int | float | str | None = None

    @model_validator(mode="after")
    def _one_operator(self) -> MaterializationPredicate:
        if (self.equals is None) == (self.contains is None):
            raise ValueError("materialization predicate requires exactly one operator")
        return self

    def _observed(self, config: Mapping[str, JsonValue]) -> JsonValue | None:
        if not self.option.startswith("/"):
            return config.get(self.option)
        node: object = config
        for segment in self.option.split("/")[1:]:
            if not isinstance(node, Mapping):
                return None
            node = node.get(segment)
        return cast("JsonValue | None", node)

    def matches(self, config: Mapping[str, JsonValue]) -> bool:
        """Return whether the resolved option satisfies this closed predicate."""
        observed = self._observed(config)
        if self.equals is not None:
            return type(observed) is type(self.equals) and observed == self.equals
        return isinstance(observed, list) and any(
            type(item) is type(self.contains) and item == self.contains for item in observed
        )


class ConditionalMaterialization(StrictModel):
    """Allow a declaration to exist only for selected resolved profiles."""

    when_any: list[MaterializationPredicate] = Field(default_factory=list)

    def materializes(self, config: Mapping[str, JsonValue]) -> bool:
        """Return whether the declaration belongs in the desired virtual tree."""
        return not self.when_any or any(predicate.matches(config) for predicate in self.when_any)


class AdapterKind(StrEnum):
    """Semantic container adapters supported by the V1 contribution contract."""

    WHOLE_FILE = "whole-file"
    TOML = "toml"
    JSON = "json"
    JSONC = "jsonc"
    YAML = "yaml"
    EDITORCONFIG = "editorconfig"
    MARKDOWN_BLOCK = "markdown-block"


class WholeArtifactDeclaration(ConditionalMaterialization):
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
        if scope.startswith("keyed-set:"):
            return _keyed_set_scope(scope.removeprefix("keyed-set:"))
        raise ValueError("TOML selector must own one key, table, or keyed-set entry")

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


class ContributionDeclaration(ConditionalMaterialization):
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


class ProviderOperation(StrEnum):
    VALIDATE = "validate"
    VERIFY = "verify"
    FIX = "fix"
    LINT = "lint"
    DRIFT_CHECK = "drift-check"
    ID_NEXT = "id-next"
    EXTRACT = "extract"
    RENDER = "render"
    SCAFFOLD = "scaffold"
    UPGRADE = "upgrade"
    MIGRATE = "migrate"
    SEMANTIC_REVIEW = "semantic-review"


class ProviderKind(StrEnum):
    PYTHON = "python"
    COMMAND = "command"
    WORKFLOW = "workflow"
    DOCUMENTATION_ONLY = "documentation-only"


class ProviderPhase(StrEnum):
    PLAN = "plan"
    INSPECT = "inspect"
    VALIDATE = "validate"
    VERIFY = "verify"
    AUTHORING = "authoring"


class ProviderEffect(StrEnum):
    FINDINGS = "findings"
    CONTENT = "content"
    MUTATION_PLAN = "mutation-plan"
    MIGRATION_REPORT = "migration-report"


_OPERATION_CONTRACT: dict[ProviderOperation, tuple[ProviderPhase, ProviderEffect]] = {
    ProviderOperation.VALIDATE: (ProviderPhase.VALIDATE, ProviderEffect.FINDINGS),
    ProviderOperation.VERIFY: (ProviderPhase.VERIFY, ProviderEffect.FINDINGS),
    ProviderOperation.FIX: (ProviderPhase.AUTHORING, ProviderEffect.MUTATION_PLAN),
    ProviderOperation.LINT: (ProviderPhase.VALIDATE, ProviderEffect.FINDINGS),
    ProviderOperation.DRIFT_CHECK: (ProviderPhase.VALIDATE, ProviderEffect.FINDINGS),
    ProviderOperation.ID_NEXT: (ProviderPhase.INSPECT, ProviderEffect.CONTENT),
    ProviderOperation.EXTRACT: (ProviderPhase.INSPECT, ProviderEffect.CONTENT),
    ProviderOperation.RENDER: (ProviderPhase.PLAN, ProviderEffect.CONTENT),
    ProviderOperation.SCAFFOLD: (ProviderPhase.AUTHORING, ProviderEffect.MUTATION_PLAN),
    ProviderOperation.UPGRADE: (ProviderPhase.AUTHORING, ProviderEffect.MUTATION_PLAN),
    ProviderOperation.MIGRATE: (ProviderPhase.PLAN, ProviderEffect.MIGRATION_REPORT),
    ProviderOperation.SEMANTIC_REVIEW: (ProviderPhase.VALIDATE, ProviderEffect.FINDINGS),
}

_PAYLOAD_ENTRYPOINT = re.compile(r"^payload:([a-z0-9]+(?:-[a-z0-9]+)*)#([A-Za-z_][A-Za-z0-9_]*)$")


class ProviderDeclaration(StrictModel):
    """Declare one phase-bounded provider implemented by payload resources."""

    id: ResourceId
    operation: ProviderOperation
    kind: ProviderKind
    phase: ProviderPhase
    effect: ProviderEffect
    entrypoint: str | None = None
    input_schema: ResourceId | None = None
    output_schema: ResourceId | None = None
    resources: list[ResourceId]

    @field_validator("resources")
    @classmethod
    def _unique_sorted_resources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, kind="provider resource")

    @model_validator(mode="after")
    def _closed_execution_contract(self) -> ProviderDeclaration:
        expected = _OPERATION_CONTRACT[self.operation]
        if (self.phase, self.effect) != expected:
            raise ValueError("provider operation has an invalid phase/effect contract")
        if self.kind is ProviderKind.DOCUMENTATION_ONLY:
            if any(
                value is not None
                for value in (self.entrypoint, self.input_schema, self.output_schema)
            ):
                raise ValueError("documentation-only provider cannot declare execution fields")
            return self
        if self.entrypoint is None or _PAYLOAD_ENTRYPOINT.fullmatch(self.entrypoint) is None:
            raise ValueError("executable provider requires a payload-qualified entrypoint")
        if self.input_schema is None or self.output_schema is None:
            raise ValueError("executable provider requires input and output schemas")
        return self

    @property
    def entrypoint_resource(self) -> str | None:
        """Return the version-scoped implementation resource, when executable."""
        if self.entrypoint is None:
            return None
        match = _PAYLOAD_ENTRYPOINT.fullmatch(self.entrypoint)
        return match.group(1) if match is not None else None


class ExtensionPathPolicy(StrEnum):
    REPOSITORY_RELATIVE = "repository-relative"


class ExtensionDeclaration(StrictModel):
    """Bind one package option to a consumer-owned repository input."""

    id: ResourceId
    option: OptionName
    media_type: MediaType
    path_policy: ExtensionPathPolicy
    preferred_root: str | None = None

    @field_validator("preferred_root")
    @classmethod
    def _safe_extension_root(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.endswith("/"):
            raise ValueError("extension preferred_root must be a directory path ending in slash")
        normalized = SafeRelativePath.parse(value[:-1]).original
        if not normalized.startswith(".standards/extensions/"):
            raise ValueError("extension preferred_root must use .standards/extensions")
        return value


_MIGRATION_ENDPOINT = re.compile(
    r"^(?:package:(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)|legacy:([a-z0-9]+(?:-[a-z0-9]+)*))$"
)


@dataclass(frozen=True, slots=True)
class MigrationEndpoint:
    """Represent one exact package version or registered legacy-state endpoint."""

    value: str
    package_version: PackageVersion | None = field(init=False)
    legacy_state: str | None = field(init=False)

    def __post_init__(self) -> None:
        match = _MIGRATION_ENDPOINT.fullmatch(self.value)
        if match is None:
            raise ValueError("migration endpoint must be package:VERSION or legacy:STATE")
        package_version = (
            PackageVersion(f"{match.group(1)}.{match.group(2)}")
            if match.group(1) is not None
            else None
        )
        object.__setattr__(self, "package_version", package_version)
        object.__setattr__(self, "legacy_state", match.group(3))

    @classmethod
    def _from_string(cls, value: str) -> MigrationEndpoint:
        return cls(value)

    @staticmethod
    def _to_string(value: MigrationEndpoint) -> str:
        return value.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[MigrationEndpoint],
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        string_schema = core_schema.str_schema(pattern=_MIGRATION_ENDPOINT.pattern, strict=True)
        validated = core_schema.no_info_after_validator_function(cls._from_string, string_schema)
        return core_schema.json_or_python_schema(
            json_schema=validated,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(cls), validated]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._to_string,
                return_schema=core_schema.str_schema(),
                when_used="always",
            ),
        )


class MigrationMode(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class MigrationDeclaration(StrictModel):
    """Declare one bounded package or legacy-state transition."""

    id: ResourceId
    from_endpoint: MigrationEndpoint = Field(alias="from")
    to_endpoint: MigrationEndpoint = Field(alias="to")
    mode: MigrationMode
    provider: ResourceId | None = None
    instructions: SafeRelativePath | None = None
    reversible: bool
    affected: list[AffectedIdentity] = Field(min_length=1)
    signatures: list[ResourceId] = Field(default_factory=list)

    @field_validator("affected", "signatures")
    @classmethod
    def _unique_sorted_references(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, kind="migration reference")

    @model_validator(mode="after")
    def _mode_contract(self) -> MigrationDeclaration:
        if self.from_endpoint == self.to_endpoint:
            raise ValueError("migration endpoints must differ")
        if self.mode is MigrationMode.AUTOMATIC:
            if self.provider is None or self.instructions is not None:
                raise ValueError("automatic migration requires only a provider")
        elif self.instructions is None or self.provider is not None:
            raise ValueError("manual migration requires only instructions")
        return self


class LegacySignatureKind(StrEnum):
    WHOLE_FILE = "whole-file"
    BOUNDED_BLOCK = "bounded-block"


class LegacySignatureFormat(StrEnum):
    MARKDOWN = "markdown"
    TOML = "toml"
    YAML = "yaml"


class LegacySignatureDeclaration(StrictModel):
    """Declare exact package-history bytes and an optional target-bound consumer-owned preservation exception."""

    id: ResourceId
    kind: LegacySignatureKind
    format: LegacySignatureFormat | None = None
    targets: list[SafeRelativePath] = Field(min_length=1)
    begin: str | None = None
    end: str | None = None
    known_content_digests: list[Sha256Digest] = Field(min_length=1)
    consumer_owned_intent_pointer: str | None = None
    # "preserve" authorizes migration to keep unrecognized bytes at the target when
    # the package manages the file through bounded units only — steady-state
    # reconciliation then takes over the managed units inside the preserved file.
    unknown_content_disposition: Literal["preserve"] | None = None

    @field_validator("consumer_owned_intent_pointer")
    @classmethod
    def _canonical_owner_intent_pointer(cls, value: str | None) -> str | None:
        return None if value is None else validate_json_pointer(value)

    @model_validator(mode="after")
    def _signature_shape(self) -> LegacySignatureDeclaration:
        validate_path_collection(self.targets)
        object.__setattr__(
            self,
            "targets",
            sorted(self.targets, key=lambda target: target.normalized.as_posix()),
        )
        digests = [digest.value for digest in self.known_content_digests]
        if len(digests) != len(set(digests)):
            raise ValueError("legacy signature contains a duplicate content digest")
        object.__setattr__(
            self,
            "known_content_digests",
            sorted(self.known_content_digests, key=lambda digest: digest.value),
        )
        if (
            self.unknown_content_disposition is not None
            and self.consumer_owned_intent_pointer is not None
        ):
            raise ValueError(
                "unknown-content preservation and consumer-owned intent are mutually exclusive"
            )
        if self.kind is LegacySignatureKind.WHOLE_FILE:
            if any(value is not None for value in (self.format, self.begin, self.end)):
                raise ValueError("whole-file legacy signature cannot declare block fields")
            if self.consumer_owned_intent_pointer is not None and len(self.targets) != 1:
                raise ValueError("consumer-owned intent requires one whole-file legacy target")
            return self
        if self.consumer_owned_intent_pointer is not None:
            raise ValueError("consumer-owned intent requires one whole-file legacy target")
        if self.unknown_content_disposition is not None:
            raise ValueError("unknown-content preservation requires a whole-file legacy signature")
        if self.format is None or self.begin is None or self.end is None:
            raise ValueError("bounded-block legacy signature requires format and delimiters")
        if (
            not self.begin
            or not self.end
            or self.begin == self.end
            or any(character in self.begin + self.end for character in "\r\n")
        ):
            raise ValueError("legacy block delimiters must be distinct nonempty single lines")
        return self


class LegacyStateDeclaration(StrictModel):
    """Register one package-local conceptual state accepted by migrations."""

    id: ResourceId


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


def contributions_overlap(left: ContributionDeclaration, right: ContributionDeclaration) -> bool:
    """Return whether two normalized declarations claim intersecting semantic units."""
    if left.target != right.target:
        return False
    if left.adapter is not right.adapter:
        return True
    return _scopes_overlap(left, right)


class PayloadManifest(StrictModel):
    """The declarative payload contract; later tasks add execution declarations."""

    schema_version: Literal["1.0"]
    payload: PayloadIdentity
    config: ConfigDeclaration
    capabilities: CapabilityDeclaration
    relations: RelationDeclaration = Field(default_factory=RelationDeclaration)
    relation_evidence: list[RelationEvidenceDeclaration] = Field(default_factory=list)
    resources: list[ResourceDeclaration] = Field(min_length=1)
    artifacts: list[WholeArtifactDeclaration] = Field(default_factory=list)
    contributions: list[ContributionDeclaration] = Field(default_factory=list)
    providers: list[ProviderDeclaration] = Field(default_factory=list)
    extensions: list[ExtensionDeclaration] = Field(default_factory=list)
    legacy_states: list[LegacyStateDeclaration] = Field(default_factory=list)
    migrations: list[MigrationDeclaration] = Field(default_factory=list)
    legacy_signatures: list[LegacySignatureDeclaration] = Field(default_factory=list)

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

        evidence_keys = [
            (evidence.kind.value, evidence.target) for evidence in self.relation_evidence
        ]
        if len(evidence_keys) != len(set(evidence_keys)):
            raise ValueError("payload contains duplicate relation evidence")
        expected_evidence = {
            (RelationEvidenceKind.EXTENDS.value, target) for target in self.relations.extends
        } | {(RelationEvidenceKind.CONFLICTS.value, target) for target in self.relations.conflicts}
        if set(evidence_keys) != expected_evidence:
            raise ValueError("relation evidence must exactly match extends and conflicts relations")
        resources_by_id = {resource.id: resource for resource in self.resources}
        for evidence in self.relation_evidence:
            resource = resources_by_id.get(evidence.resource)
            if (
                resource is None
                or resource.role != "relation-evidence"
                or resource.media_type != "text/markdown"
            ):
                raise ValueError(
                    "relation evidence must identify a Markdown relation-evidence resource"
                )

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
                if contributions_overlap(other, contribution):
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

        resource_ids = {resource.id for resource in self.resources}
        resource_paths = {resource.path.original for resource in self.resources}
        provider_ids: set[str] = set()
        provider_by_id: dict[str, ProviderDeclaration] = {}
        for provider in self.providers:
            if provider.id in provider_ids:
                raise ValueError("payload contains a duplicate provider ID")
            provider_ids.add(provider.id)
            provider_by_id[provider.id] = provider
            referenced = {
                provider.entrypoint_resource,
                provider.input_schema,
                provider.output_schema,
                *provider.resources,
            }
            missing = {item for item in referenced if item is not None} - resource_ids
            if missing:
                raise ValueError("provider references an undeclared resource")
        for contribution in self.contributions:
            if contribution.provider is not None:
                provider = provider_by_id.get(contribution.provider)
                if provider is None or provider.operation is not ProviderOperation.RENDER:
                    raise ValueError("contribution provider must identify a render provider")

        extension_ids: set[str] = set()
        extension_roots: list[str] = []
        expected_extension_root = f".standards/extensions/{self.payload.standard}/"
        for extension in self.extensions:
            if extension.id in extension_ids:
                raise ValueError("payload contains a duplicate extension ID")
            extension_ids.add(extension.id)
            if extension.preferred_root is not None:
                if extension.preferred_root != expected_extension_root:
                    raise ValueError("extension preferred_root must match the package namespace")
                extension_roots.append(extension.preferred_root.removesuffix("/"))
        output_targets = artifact_targets | {
            contribution.target.normalized.as_posix() for contribution in self.contributions
        }
        if any(
            target == root or target.startswith(f"{root}/")
            for root in extension_roots
            for target in output_targets
        ):
            raise ValueError("managed output overlaps a consumer-owned extension root")

        signature_ids: set[str] = set()
        intent_pointers: set[str] = set()
        for signature in self.legacy_signatures:
            if signature.id in signature_ids:
                raise ValueError("payload contains a duplicate legacy signature ID")
            signature_ids.add(signature.id)
            pointer = signature.consumer_owned_intent_pointer
            if pointer is None:
                continue
            if pointer in intent_pointers:
                raise ValueError("payload reuses a consumer-owned intent pointer")
            intent_pointers.add(pointer)

        legacy_state_ids: set[str] = set()
        for state in self.legacy_states:
            if state.id in legacy_state_ids:
                raise ValueError("payload contains a duplicate legacy state")
            legacy_state_ids.add(state.id)

        migration_ids: set[str] = set()
        used_legacy_states: set[str] = set()
        for migration in self.migrations:
            if migration.id in migration_ids:
                raise ValueError("payload contains a duplicate migration ID")
            migration_ids.add(migration.id)
            endpoints = (migration.from_endpoint, migration.to_endpoint)
            if not any(endpoint.package_version == self.payload.version for endpoint in endpoints):
                raise ValueError("migration must connect to the containing payload version")
            for endpoint in endpoints:
                if endpoint.legacy_state is None:
                    continue
                if endpoint.legacy_state not in legacy_state_ids:
                    raise ValueError("migration references an unregistered legacy state")
                used_legacy_states.add(endpoint.legacy_state)
            if migration.provider is not None:
                provider = provider_by_id.get(migration.provider)
                if (
                    provider is None
                    or provider.operation is not ProviderOperation.MIGRATE
                    or provider.effect is not ProviderEffect.MIGRATION_REPORT
                ):
                    raise ValueError("automatic migration must identify a migrate provider")
            if (
                migration.instructions is not None
                and migration.instructions.original not in resource_paths
            ):
                raise ValueError("manual migration instructions must be a declared resource")
            if not set(migration.signatures).issubset(signature_ids):
                raise ValueError("migration references an unknown legacy signature")
        if legacy_state_ids - used_legacy_states:
            raise ValueError("payload contains an unused legacy state")
        return self


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
        summary = validation_summary(exc)
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


def _validate_declared_defaults(
    schema: Mapping[str, JsonValue],
    root_validator: _SchemaValidator,
) -> None:
    for child in _object_properties(schema).values():
        if not isinstance(child, dict):
            continue
        if "default" in child:
            try:
                validator = root_validator.evolve(schema=child)
                invalid = next(validator.iter_errors(child["default"]), None)
            except Unresolvable as exc:
                raise PackageContractError(
                    "option schema default cannot be validated against a $ref property"
                ) from exc
            if invalid is not None:
                raise PackageContractError("option schema contains an invalid default")
        if child.get("type") == "object":
            _validate_declared_defaults(child, root_validator)


def _validate_extension_options(
    schema: Mapping[str, JsonValue],
    extensions: Iterable[ExtensionDeclaration],
) -> None:
    properties = _object_properties(schema)
    for extension in extensions:
        option_schema = properties.get(extension.option)
        if not isinstance(option_schema, dict):
            raise PackageContractError(
                "extension option must identify a declared string package option"
            )
        option_type = option_schema.get("type")
        nullable_string = isinstance(option_type, list) and set(option_type) == {
            "null",
            "string",
        }
        if option_type != "string" and not nullable_string:
            raise PackageContractError(
                "extension option must identify a declared string package option"
            )


def _validate_predicate_options(
    document: Mapping[str, JsonValue],
    manifest: PayloadManifest,
) -> None:
    for declaration in (*manifest.artifacts, *manifest.contributions):
        for predicate in declaration.when_any:
            option = predicate.option
            segments = option.split("/")[1:] if option.startswith("/") else [option]
            node: Mapping[str, JsonValue] = document
            for index, segment in enumerate(segments):
                child = _object_properties(node).get(segment)
                if not isinstance(child, dict):
                    raise PackageContractError(
                        f"materialization predicate names an undeclared option path: {option}"
                    )
                if index + 1 < len(segments) and child.get("type") != "object":
                    raise PackageContractError(
                        f"materialization predicate traverses a non-object option: {option}"
                    )
                node = child


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
        try:
            errors = sorted(
                validator.iter_errors(effective),
                key=lambda error: tuple(str(part) for part in error.path),
            )
        except Unresolvable as exc:
            raise PackageContractError(
                "package options schema contains an unresolvable reference"
            ) from exc
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
    root_validator = cast("_SchemaValidator", Draft202012Validator(document))
    _validate_declared_defaults(document, root_validator)
    _validate_extension_options(document, manifest.extensions)
    _validate_predicate_options(document, manifest)

    return PackageOptionSchema(
        standard_id=manifest.payload.standard,
        raw_bytes=raw_bytes,
        document=document,
    )
