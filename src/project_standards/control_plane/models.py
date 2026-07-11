"""Strict desired, catalog, and applied-state models for the control plane."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from project_standards.control_plane.paths import CatalogMajor
from project_standards.package_contract.family import FamilyStatus, KebabId, StrictModel
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    JsonValue,
    PayloadAvailability,
    PosixMode,
    SharedIdentity,
    normalize_scope,
)

type VersionSelector = Literal["latest"] | PackageVersion

ToolRelease = Annotated[
    str,
    StringConstraints(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"),
]

_FORBIDDEN_CONFIG_KEYS = frozenset(
    {
        "api_key",
        "artifact_url",
        "command",
        "credential",
        "entrypoint",
        "executable",
        "password",
        "script",
        "secret",
        "token",
        "url",
    }
)


def _validate_config_boundary(value: JsonValue, *, path: tuple[str, ...] = ()) -> None:
    """Reject executable, remote-source, and secret-shaped desired-state values."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.casefold().replace("-", "_")
            if normalized in _FORBIDDEN_CONFIG_KEYS or normalized.endswith(
                ("_password", "_secret", "_token", "_url")
            ):
                location = ".".join((*path, key))
                raise ValueError(f"config key {location!r} is not allowed")
            _validate_config_boundary(child, path=(*path, key))
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_config_boundary(child, path=(*path, str(index)))
        return
    if isinstance(value, str) and value.casefold().startswith(("http://", "https://")):
        location = ".".join(path) or "<root>"
        raise ValueError(f"remote URL at config path {location!r} is not allowed")


def _sorted_mapping[T](value: dict[str, T]) -> dict[str, T]:
    return dict(sorted(value.items()))


class ControlHeader(StrictModel):
    """Consumer-owned schema and catalog-major intent."""

    schema_version: Literal["1.0"]
    catalog: CatalogMajor


class DesiredPackage(StrictModel):
    """Desired enablement, payload selector, and package-owned options."""

    enabled: bool
    version: VersionSelector
    config: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("config")
    @classmethod
    def _safe_config(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_config_boundary(value)
        return _sorted_mapping(value)


class DesiredConfig(StrictModel):
    """Complete consumer-owned desired state."""

    project_standards: ControlHeader
    standards: dict[KebabId, DesiredPackage] = Field(default_factory=dict)

    @field_validator("standards")
    @classmethod
    def _sorted_standards(
        cls,
        value: dict[str, DesiredPackage],
    ) -> dict[str, DesiredPackage]:
        return _sorted_mapping(value)


class CatalogHeader(ControlHeader):
    """Installed tool release and self-digest for one catalog snapshot."""

    release: ToolRelease
    digest: Sha256Digest


class CatalogChannel(StrEnum):
    """Resolution channel assigned to one advertised payload."""

    STABLE = "stable"
    RETAINED = "retained"
    CANDIDATE = "breaking-candidate"
    REFERENCE_ONLY = "reference-only"
    INTERNAL = "internal"


class CatalogVersion(StrictModel):
    """Channel, availability, and payload identity for one exact version."""

    channel: CatalogChannel
    availability: PayloadAvailability
    payload_digest: Sha256Digest


class CatalogStandard(StrictModel):
    """Complete version index for one standard in a catalog snapshot."""

    status: FamilyStatus
    available: list[PackageVersion] = Field(min_length=1)
    default: PackageVersion | None = None
    candidates: list[PackageVersion] = Field(default_factory=list)
    versions: dict[str, CatalogVersion] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent_version_index(self) -> CatalogStandard:
        available_values = [version.value for version in self.available]
        if len(available_values) != len(set(available_values)):
            raise ValueError("catalog standard contains a duplicate available version")
        candidate_values = [version.value for version in self.candidates]
        if len(candidate_values) != len(set(candidate_values)):
            raise ValueError("catalog standard contains a duplicate candidate version")
        if self.default is not None and self.default.value not in available_values:
            raise ValueError("catalog default must be an available version")
        if any(value not in available_values for value in candidate_values):
            raise ValueError("catalog candidates must be available versions")
        if self.default is not None and any(
            candidate.major == self.default.major for candidate in self.candidates
        ):
            raise ValueError("catalog candidates must use a non-default package major")
        if set(self.versions) != set(available_values):
            raise ValueError("catalog version records must exactly match available versions")
        consumer_channels = {
            CatalogChannel.STABLE,
            CatalogChannel.RETAINED,
            CatalogChannel.CANDIDATE,
        }
        consumer_versions: list[str] = []
        channel_candidates: list[str] = []
        for version, entry in self.versions.items():
            if entry.availability is PayloadAvailability.CONSUMER:
                consumer_versions.append(version)
                if entry.channel not in consumer_channels:
                    raise ValueError("consumer payload must use a consumer channel")
            elif (
                entry.availability is PayloadAvailability.REFERENCE_ONLY
                and entry.channel is not CatalogChannel.REFERENCE_ONLY
            ):
                raise ValueError("reference-only payload must use its matching channel")
            elif (
                entry.availability is PayloadAvailability.INTERNAL
                and entry.channel is not CatalogChannel.INTERNAL
            ):
                raise ValueError("internal payload must use its matching channel")
            if entry.channel is CatalogChannel.CANDIDATE:
                channel_candidates.append(version)
        if consumer_versions and self.default is None:
            raise ValueError("consumer package must declare one default version")
        if not consumer_versions and self.default is not None:
            raise ValueError("non-consumer package cannot declare a default version")
        if self.default is not None:
            default_entry = self.versions[self.default.value]
            if default_entry.channel is not CatalogChannel.STABLE:
                raise ValueError("catalog default must use the stable channel")
        if set(candidate_values) != set(channel_candidates):
            raise ValueError("candidate index must exactly match candidate channels")
        ordered_available = sorted(self.available, key=lambda item: item.sort_key)
        ordered_candidates = sorted(self.candidates, key=lambda item: item.sort_key)
        ordered_versions = dict(
            sorted(
                self.versions.items(),
                key=lambda item: PackageVersion(item[0]).sort_key,
            )
        )
        object.__setattr__(self, "available", ordered_available)
        object.__setattr__(self, "candidates", ordered_candidates)
        object.__setattr__(self, "versions", ordered_versions)
        return self


class ConsumerCatalog(StrictModel):
    """Tool-owned complete catalog snapshot."""

    project_standards: CatalogHeader
    standards: dict[KebabId, CatalogStandard]

    @field_validator("standards")
    @classmethod
    def _sorted_standards(
        cls,
        value: dict[str, CatalogStandard],
    ) -> dict[str, CatalogStandard]:
        return _sorted_mapping(value)


class LockHeader(ControlHeader):
    """Digests binding applied state to one tool release, catalog, and config."""

    release: ToolRelease
    catalog_digest: Sha256Digest
    config_digest: Sha256Digest


class SelectionKind(StrEnum):
    """Resolution channel recorded for an applied package."""

    STABLE = "stable"
    RETAINED = "retained"
    CANDIDATE = "breaking-candidate"
    EXACT = "exact"


class AppliedPackage(StrictModel):
    """Resolved facts for one enabled package; authorization lives elsewhere."""

    requested: VersionSelector
    resolved: PackageVersion
    selection: SelectionKind
    payload_digest: Sha256Digest
    effective_config_digest: Sha256Digest


class AcceptedTrack(StrictModel):
    """Durable authorization evidence for one non-default package major."""

    major: int = Field(ge=1)
    authorized_catalog: CatalogMajor


class UnitProvenance(StrEnum):
    """Origin of an applied semantic unit's materialized value."""

    SOURCE = "source"
    PROVIDER = "provider"
    GENERATED = "generated"
    PACKAGE = "package"
    EXTERNAL = "external"


class LockedUnit(StrictModel):
    """Central ownership and drift record for one normalized semantic unit."""

    path: SafeRelativePath
    adapter: AdapterKind
    scope: str = Field(min_length=1)
    owners: tuple[KebabId, ...] = Field(min_length=1)
    shared_identity: SharedIdentity | None = None
    versions: dict[KebabId, PackageVersion]
    provenance: UnitProvenance
    policy: ArtifactPolicy
    semantic_digest: Sha256Digest
    content_digest: Sha256Digest
    mode: PosixMode | None = None
    created_container: bool

    @model_validator(mode="after")
    def _consistent_ownership(self) -> LockedUnit:
        if len(self.owners) != len(set(self.owners)):
            raise ValueError("locked unit contains a duplicate owner")
        if set(self.versions) != set(self.owners):
            raise ValueError("locked unit version keys must exactly match owners")
        if len(self.owners) > 1 and self.shared_identity is None:
            raise ValueError("shared_identity is required for several owners")
        if len(self.owners) > 1 and self.adapter is AdapterKind.WHOLE_FILE:
            raise ValueError("whole-file units cannot have shared owners")
        package_prefix = ".standards/packages/"
        if self.path.original.startswith(package_prefix):
            namespace = self.path.original.removeprefix(package_prefix).split("/", 1)[0]
            if self.owners != (namespace,):
                raise ValueError("package namespace must be owned by its matching standard")
        ordered_owners = tuple(sorted(self.owners))
        object.__setattr__(self, "owners", ordered_owners)
        object.__setattr__(self, "versions", _sorted_mapping(self.versions))
        object.__setattr__(self, "scope", normalize_scope(self.adapter, self.scope))
        return self

    @property
    def natural_key(self) -> tuple[str, str, str]:
        """Return the normalized identity used for lock ordering and uniqueness."""
        return (self.path.original, self.adapter.value, self.scope)


class LockedInput(StrictModel):
    """Consumer-owned referenced input tracked without managed ownership."""

    standard_id: KebabId
    extension_id: KebabId
    path: SafeRelativePath
    digest: Sha256Digest

    @property
    def natural_key(self) -> tuple[str, str, str]:
        """Return the input identity used for lock ordering and uniqueness."""
        return (self.standard_id, self.extension_id, self.path.original)


class CentralLock(StrictModel):
    """Complete tool-owned applied, authorization, ownership, and input state."""

    project_standards: LockHeader
    standards: dict[KebabId, AppliedPackage] = Field(default_factory=dict)
    accepted_tracks: dict[KebabId, AcceptedTrack] = Field(default_factory=dict)
    artifacts: list[LockedUnit] = Field(default_factory=list)
    referenced_inputs: list[LockedInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_sorted_collections(self) -> CentralLock:
        artifact_keys = [artifact.natural_key for artifact in self.artifacts]
        if len(artifact_keys) != len(set(artifact_keys)):
            raise ValueError("central lock contains a duplicate artifact unit")
        input_keys = [item.natural_key for item in self.referenced_inputs]
        if len(input_keys) != len(set(input_keys)):
            raise ValueError("central lock contains a duplicate referenced input")
        object.__setattr__(self, "standards", _sorted_mapping(self.standards))
        object.__setattr__(
            self,
            "accepted_tracks",
            _sorted_mapping(self.accepted_tracks),
        )
        object.__setattr__(
            self,
            "artifacts",
            sorted(self.artifacts, key=lambda item: item.natural_key),
        )
        object.__setattr__(
            self,
            "referenced_inputs",
            sorted(self.referenced_inputs, key=lambda item: item.natural_key),
        )
        return self
