"""Generated JSON Schemas for consumer state and public plan/provider envelopes."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.migration import MigrationReport
from project_standards.control_plane.models import (
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
)
from project_standards.package_contract._write import atomic_write
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import KebabId, StrictModel
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
    digest_of,
)
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonValue,
    PosixMode,
    ProviderOperation,
    normalize_scope,
)
from project_standards.package_contract.schemas import (
    SCHEMA_BASE,
    SchemaDocument,
    build_schema_documents,
    serialize_schema_documents,
)


class ProviderInputSchema(StrictModel):
    """JSON-safe immutable facts supplied to one selected package provider."""

    schema_version: Literal["1.0"]
    standard_id: KebabId
    version: PackageVersion
    operation: ProviderOperation
    config: dict[str, JsonValue] = Field(default_factory=dict)
    resources: dict[KebabId, Sha256Digest] = Field(default_factory=dict)
    snapshots: dict[str, JsonValue] = Field(default_factory=dict)


class MutationActionSchema(StrictModel):
    """One bounded repository mutation returned to the platform executor."""

    kind: ActionKind
    target: SafeRelativePath
    adapter: AdapterKind
    scope: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    precondition_digest: Sha256Digest
    content_digest: Sha256Digest | None = None
    content_base64: str | None = None
    mode: PosixMode | None = None

    @model_validator(mode="after")
    def _complete_bounded_action(self) -> MutationActionSchema:
        if self.kind not in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}:
            raise ValueError("mutation plan action must mutate one bounded target")
        object.__setattr__(self, "scope", normalize_scope(self.adapter, self.scope))
        if self.kind is ActionKind.REMOVE:
            if self.content_digest is not None or self.content_base64 is not None:
                raise ValueError("mutation plan removal cannot carry replacement content")
            if self.mode is not None:
                raise ValueError("mutation plan removal cannot carry a replacement mode")
            return self
        if self.content_digest is None or self.content_base64 is None:
            raise ValueError("mutation plan replacement requires complete content")
        try:
            content = base64.b64decode(self.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("mutation plan content must be canonical base64") from exc
        if base64.b64encode(content).decode("ascii") != self.content_base64:
            raise ValueError("mutation plan content must be canonical base64")
        digest = digest_of(content).value
        if digest != self.content_digest.value:
            raise ValueError("mutation plan content does not match its digest")
        return self

    @property
    def content_bytes(self) -> bytes | None:
        """Return validated replacement bytes, or no bytes for removal."""
        if self.content_base64 is None:
            return None
        return base64.b64decode(self.content_base64, validate=True)


class MutationDiagnosticSchema(StrictModel):
    """Content-safe package diagnostic accompanying an authoring plan."""

    code: str
    severity: Literal["error", "warning"]
    path: SafeRelativePath
    message: str
    refusal: bool = False


class MutationPlanSchema(StrictModel):
    """Typed mutation intent and diagnostics returned by a package provider."""

    schema_version: Literal["1.0"]
    standard_id: KebabId
    version: PackageVersion
    actions: list[MutationActionSchema] = Field(default_factory=list)
    diagnostics: list[MutationDiagnosticSchema] = Field(default_factory=list)


class PublicFindingSchema(StrictModel):
    """Content-safe finding fields included in public reconciliation output."""

    code: str
    severity: Literal["error", "warning"]
    standard_id: str
    version: str
    path: str
    identity: str
    message: str
    hint: str


class PublicActionSchema(StrictModel):
    """Content-safe action fields included in public reconciliation output."""

    kind: ActionKind
    target: str
    adapter: str
    scope: str
    standard_id: str
    summary: str
    before_digest: str | None = None
    after_digest: str | None = None
    before_mode: PosixMode | None = None
    after_mode: PosixMode | None = None


class ReconciliationPlanSchema(StrictModel):
    """Stable JSON surface for a complete reconciliation preview."""

    schema_version: Literal["1.0"]
    applicable: bool
    findings: list[PublicFindingSchema] = Field(default_factory=list)
    actions: list[PublicActionSchema] = Field(default_factory=list)
    proposed_lock: CentralLock


_SCHEMA_MODELS: tuple[tuple[str, type[BaseModel]], ...] = (
    ("consumer-catalog.schema.json", ConsumerCatalog),
    ("consumer-config.schema.json", DesiredConfig),
    ("consumer-lock.schema.json", CentralLock),
    ("migration-report.schema.json", MigrationReport),
    ("mutation-plan.schema.json", MutationPlanSchema),
    ("provider-input.schema.json", ProviderInputSchema),
    ("reconciliation-plan.schema.json", ReconciliationPlanSchema),
)


def control_plane_schema_documents() -> dict[str, SchemaDocument]:
    """Return all strict control-plane schemas in stable filename order."""
    return build_schema_documents(_SCHEMA_MODELS, SCHEMA_BASE)


def control_plane_schema_bytes() -> dict[str, bytes]:
    """Serialize schemas with stable keys, two-space indent, and a final newline."""
    return serialize_schema_documents(control_plane_schema_documents())


def generate_control_plane_schemas(root: Path, *, check: bool) -> bool:
    """Write canonical control-plane schemas or compare them read-only."""
    try:
        if root.is_symlink() or not root.is_dir():
            raise PackageContractError("schema generation root must be a regular directory")
        output = root / "src/project_standards/schemas"
        ancestors = (root / "src", root / "src/project_standards", output)
        if any(path.is_symlink() for path in ancestors):
            raise PackageContractError("schema output path cannot contain a symlink")
        if not check:
            output.mkdir(parents=True, exist_ok=True)
        expected = control_plane_schema_bytes()
        if any((output / name).is_symlink() for name in expected):
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
    try:
        for name, content in expected.items():
            atomic_write(output / name, content)
    except OSError as exc:
        raise PackageContractError("control-plane schemas could not be written") from exc
    return True
