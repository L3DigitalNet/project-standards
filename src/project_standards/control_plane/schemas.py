"""Generated JSON Schemas for consumer state and public plan/provider envelopes."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from itertools import pairwise
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, Field, model_validator

from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.migration import MigrationReport
from project_standards.control_plane.models import (
    AcceptedTrack,
    AppliedPackage,
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
    ToolRelease,
    UnitProvenance,
)
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.resolution import TrackTransitionKind
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
    ConfigJsonPointer,
    JsonValue,
    PosixMode,
    ProviderOperation,
    ResourceId,
    SharedIdentity,
    normalize_scope,
)
from project_standards.package_contract.release import ReleaseClassification
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


class ProjectSpecImportSnapshotSchema(StrictModel):
    """One immutable source or target identity retained by an import plan."""

    path: SafeRelativePath
    digest: Sha256Digest


PROJECT_SPEC_IMPORT_DIAGNOSTICS: dict[str, tuple[str, str]] = {
    "SPEC-IMPORT-PREAMBLE": (
        "preamble",
        "Source block precedes the first recognized heading; owner placement is required.",
    ),
    "SPEC-IMPORT-UNMAPPED": (
        "unmapped",
        "Source heading has no exact canonical destination; owner placement is required.",
    ),
    "SPEC-IMPORT-DUPLICATE": (
        "duplicate",
        "Multiple source blocks select one canonical destination; owner placement is required.",
    ),
}


class ProjectSpecImportDiagnosticSchema(StrictModel):
    """Content-safe owner-decision diagnostic for one reviewed source block."""

    code: Literal[
        "SPEC-IMPORT-PREAMBLE",
        "SPEC-IMPORT-UNMAPPED",
        "SPEC-IMPORT-DUPLICATE",
    ]
    ordinal: int = Field(ge=0)
    classification: Literal["preamble", "unmapped", "duplicate"]
    message: str = Field(min_length=1)

    @model_validator(mode="after")
    def _content_safe_message(self) -> ProjectSpecImportDiagnosticSchema:
        if (self.classification, self.message) != PROJECT_SPEC_IMPORT_DIAGNOSTICS[self.code]:
            raise ValueError("import diagnostic must use its content-safe canonical form")
        return self


class ProjectSpecImportBlockSchema(StrictModel):
    """One source byte range and its exact target-byte preservation location."""

    ordinal: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    source_digest: Sha256Digest
    disposition: Literal["mapped", "review"]
    destination: str | None = None
    diagnostic_code: str | None = None
    target_start: int = Field(ge=0)
    target_end: int = Field(gt=0)
    fence: str = Field(pattern=r"^`{3,}$")

    @model_validator(mode="after")
    def _complete_disposition(self) -> ProjectSpecImportBlockSchema:
        if self.start >= self.end or self.target_start >= self.target_end:
            raise ValueError("import block ranges must be non-empty")
        if self.disposition == "mapped":
            if self.destination is None or self.diagnostic_code is not None:
                raise ValueError("mapped import block requires only a destination")
        elif self.destination is not None or self.diagnostic_code is None:
            raise ValueError("review import block requires only a diagnostic code")
        return self


class ProjectSpecImportReportSchema(StrictModel):
    """Closed deterministic preservation report for one legacy-spec import."""

    schema_version: Literal["project-spec-import-plan-v1"]
    source_snapshot: ProjectSpecImportSnapshotSchema
    target_snapshot: ProjectSpecImportSnapshotSchema
    spec_id: str = Field(pattern=r"^SPEC-[0-9A-Z]{4}$")
    source_size: int = Field(ge=0)
    blocks: list[ProjectSpecImportBlockSchema] = Field(default_factory=list)
    diagnostics: list[ProjectSpecImportDiagnosticSchema] = Field(default_factory=list)
    target_content_digest: Sha256Digest
    target_content_base64: str
    plan_digest: Sha256Digest

    @model_validator(mode="after")
    def _validate_preservation(self) -> ProjectSpecImportReportSchema:
        try:
            target = base64.b64decode(self.target_content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("import target content must be canonical base64") from exc
        if base64.b64encode(target).decode("ascii") != self.target_content_base64:
            raise ValueError("import target content must be canonical base64")
        if digest_of(target) != self.target_content_digest:
            raise ValueError("import target content does not match its digest")

        cursor = 0
        recovered: list[bytes] = []
        reviews: list[tuple[int, str]] = []
        target_ranges: list[tuple[int, int]] = []
        for ordinal, block in enumerate(self.blocks):
            if block.ordinal != ordinal or block.start != cursor:
                raise ValueError("import source partition has a gap, overlap, or duplicate")
            if block.end - block.start != block.target_end - block.target_start:
                raise ValueError(
                    "import source partition range differs from preserved target range"
                )
            if block.target_end > len(target):
                raise ValueError("import block target range exceeds target content")
            raw = target[block.target_start : block.target_end]
            if digest_of(raw) != block.source_digest:
                raise ValueError("import block bytes do not match their digest")
            if block.fence.encode("ascii") in raw:
                raise ValueError("import block bytes can close their preservation fence")
            fence = block.fence.encode("ascii")
            prefix_start = block.target_start - len(fence) - 1
            suffix = (b"" if raw.endswith((b"\n", b"\r")) else b"\n") + fence + b"\n"
            if (
                prefix_start < 0
                or target[prefix_start : block.target_start] != fence + b"\n"
                or target[block.target_end : block.target_end + len(suffix)] != suffix
            ):
                raise ValueError("import block is not bounded by its preservation fence")
            recovered.append(raw)
            target_ranges.append((block.target_start, block.target_end))
            cursor = block.end
            if block.disposition == "review":
                assert block.diagnostic_code is not None
                reviews.append((block.ordinal, block.diagnostic_code))
        if cursor != self.source_size:
            raise ValueError("import source partition does not cover the source")
        if digest_of(b"".join(recovered)) != self.source_snapshot.digest:
            raise ValueError("recovered import source does not match its snapshot")
        ordered_ranges = sorted(target_ranges)
        if any(left[1] > right[0] for left, right in pairwise(ordered_ranges)):
            raise ValueError("import target block ranges overlap or duplicate content")
        if reviews != [(item.ordinal, item.code) for item in self.diagnostics]:
            raise ValueError("import review diagnostics do not match reviewed blocks")
        return self


class MutationPlanSchema(StrictModel):
    """Typed mutation intent and diagnostics returned by a package provider."""

    schema_version: Literal["1.0"]
    standard_id: KebabId
    version: PackageVersion
    actions: list[MutationActionSchema] = Field(default_factory=list)
    diagnostics: list[MutationDiagnosticSchema] = Field(default_factory=list)
    import_report: ProjectSpecImportReportSchema | None = None

    @model_validator(mode="after")
    def _validate_import_report(self) -> MutationPlanSchema:
        report = self.import_report
        if report is None:
            return self
        if len(self.actions) != 1:
            raise ValueError("import mutation plan requires exactly one target action")
        action = self.actions[0]
        if (
            action.target != report.target_snapshot.path
            or action.precondition_digest != report.target_snapshot.digest
            or action.content_digest != report.target_content_digest
            or action.content_base64 != report.target_content_base64
        ):
            raise ValueError("import report does not match its target action")
        expected_diagnostics = [
            (
                item.code,
                "warning",
                report.source_snapshot.path,
                item.message,
                False,
            )
            for item in report.diagnostics
        ]
        actual_diagnostics = [
            (item.code, item.severity, item.path, item.message, item.refusal)
            for item in self.diagnostics
        ]
        if actual_diagnostics != expected_diagnostics:
            raise ValueError("import plan diagnostics do not match its content-safe report")
        expected = canonical_mutation_plan_digest(self)
        if report.plan_digest != expected:
            raise ValueError("import plan digest does not match the canonical plan")
        return self


def canonical_mutation_plan_digest(plan: MutationPlanSchema | dict[str, object]) -> Sha256Digest:
    """Digest every mutation-plan field except the digest value being computed."""
    raw = (
        cast("dict[str, object]", plan.model_dump(mode="json"))
        if isinstance(plan, MutationPlanSchema)
        else plan
    )
    canonical = dict(raw)
    report_value = canonical.get("import_report")
    if not isinstance(report_value, dict):
        raise ValueError("canonical import plan digest requires an import report")
    report = dict(cast("dict[str, object]", report_value))
    report.pop("plan_digest", None)
    canonical["import_report"] = report

    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return Sha256Digest(f"sha256:{hashlib.sha256(encoded).hexdigest()}")


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
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    locus: str | None = None
    observed: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=1)
    expected: JsonValue | None = None
    actual: JsonValue | None = None
    expected_digest: str | None = None
    actual_digest: str | None = None
    governing_options: list[str] | None = None
    first_difference_line: int | None = Field(default=None, ge=1)
    first_difference_expected: str | None = None


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


class PublicConfigurationTransformSchema(StrictModel):
    """Value-redacted identity and digest evidence for one package config transform."""

    standard_id: KebabId
    migration_id: ResourceId
    source: PackageVersion
    target: PackageVersion
    provider_id: ResourceId
    declared_pointers: list[ConfigJsonPointer] = Field(min_length=1)
    changed_pointers: list[ConfigJsonPointer] = Field(default_factory=list)
    before_digest: Sha256Digest
    after_digest: Sha256Digest


class PublicPlannedUnitSchema(StrictModel):
    """One public semantic-unit transition with package provenance."""

    kind: ActionKind
    target: SafeRelativePath
    adapter: AdapterKind
    scope: str = Field(min_length=1)
    owners: list[KebabId]
    shared_identity: SharedIdentity | None
    versions: dict[KebabId, PackageVersion]
    provenance: UnitProvenance
    before_digest: Sha256Digest | None
    after_digest: Sha256Digest | None


class PublicTargetPreconditionSchema(StrictModel):
    """One target identity bound to the snapshot observed during planning."""

    target: SafeRelativePath
    digest: Sha256Digest


class PublicResolvedPackageSchema(StrictModel):
    """One package selection and its public applied-state facts."""

    standard_id: KebabId
    applied: AppliedPackage


class PublicTrackTransitionSchema(StrictModel):
    """One accepted-major authorization transition."""

    standard_id: KebabId
    kind: TrackTransitionKind
    previous: AcceptedTrack | None
    current: AcceptedTrack | None


class PublicResolutionSchema(StrictModel):
    """Public package selections and accepted-major transitions."""

    packages: list[PublicResolvedPackageSchema] = Field(default_factory=list)
    track_transitions: list[PublicTrackTransitionSchema] = Field(default_factory=list)


class PublicVerificationRequestSchema(StrictModel):
    """One package verification provider deferred until apply."""

    standard_id: KebabId
    version: PackageVersion
    provider_id: ResourceId


class PublicProviderNoticeSchema(StrictModel):
    """One content-safe notice emitted by a package provider."""

    standard_id: KebabId
    version: PackageVersion
    provider_id: ResourceId
    message: str


class PublicCatalogLineageSchema(StrictModel):
    """One catalog identity in a planned installed-catalog refresh."""

    catalog: CatalogMajor
    release: ToolRelease
    digest: Sha256Digest


class PublicCatalogSelectionChangeSchema(StrictModel):
    """One enabled package selection changed by catalog refresh."""

    standard_id: KebabId
    previous: PackageVersion | None
    current: PackageVersion


class PublicCatalogRefreshSchema(StrictModel):
    """Public lineage and selection facts for an installed-catalog refresh."""

    changed: bool
    classification: ReleaseClassification
    before: PublicCatalogLineageSchema
    after: PublicCatalogLineageSchema
    affected_selections: list[PublicCatalogSelectionChangeSchema] = Field(default_factory=list)


class ReconciliationPlanSchema(StrictModel):
    """Stable JSON surface for a complete reconciliation preview."""

    schema_version: Literal["1.1", "1.2", "1.3"]
    applicable: bool
    actions: list[PublicActionSchema] = Field(default_factory=list)
    configuration_transforms: list[PublicConfigurationTransformSchema] = Field(default_factory=list)
    units: list[PublicPlannedUnitSchema] = Field(default_factory=list)
    findings: list[PublicFindingSchema] = Field(default_factory=list)
    preconditions: list[PublicTargetPreconditionSchema] = Field(default_factory=list)
    resolution: PublicResolutionSchema = Field(default_factory=PublicResolutionSchema)
    verification_requests: list[PublicVerificationRequestSchema] = Field(default_factory=list)
    provider_notices: list[PublicProviderNoticeSchema] = Field(default_factory=list)
    namespace_prunes: list[SafeRelativePath] = Field(default_factory=list)
    catalog_refresh: PublicCatalogRefreshSchema | None = None
    next_lock: CentralLock | None = None
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
