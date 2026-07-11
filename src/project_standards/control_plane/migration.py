"""Typed, content-safe reports returned by legacy-migration providers."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import ConfigDict, Field, ValidationError, field_validator, model_validator

from project_standards.control_plane.diagnostics import validation_summary
from project_standards.control_plane.models import DesiredPackage, VersionSelector
from project_standards.package_contract.family import KebabId, StrictModel
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import JsonValue

type LegacyOwnership = Literal[
    "managed",
    "create-only",
    "shared",
    "consumer-owned",
    "package-lock",
]


class LegacyDisposition(StrEnum):
    """Proposed treatment of one exactly recognized legacy object."""

    ADOPT = "adopt"
    PRESERVE = "preserve"
    REMOVE = "remove"
    IMPORT_LOCK = "import-lock"


def _validate_json_pointer(value: str) -> str:
    if not value.startswith("/"):
        raise ValueError("recognized setting must be an absolute JSON pointer")
    index = 0
    while index < len(value):
        if value[index] != "~":
            index += 1
            continue
        if index + 1 >= len(value) or value[index + 1] not in {"0", "1"}:
            raise ValueError("recognized setting contains a noncanonical JSON pointer escape")
        index += 2
    return value


class MigratedPackage(StrictModel):
    """Validated desired-state contribution produced for one selected payload."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    standard_id: KebabId
    version: PackageVersion
    selector: VersionSelector
    config: dict[str, JsonValue] = Field(default_factory=dict)
    recognized_settings: tuple[str, ...] = ()

    @field_validator("config")
    @classmethod
    def _safe_config(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        try:
            validated = DesiredPackage(enabled=True, version="latest", config=value)
        except ValidationError as exc:
            raise ValueError(
                f"migrated package config is invalid: {validation_summary(exc)}"
            ) from exc
        return validated.config

    @field_validator("recognized_settings")
    @classmethod
    def _canonical_settings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        validated = [_validate_json_pointer(item) for item in value]
        if len(validated) != len(set(validated)):
            raise ValueError("recognized setting paths must be unique")
        return tuple(sorted(validated))

    @model_validator(mode="after")
    def _selector_matches_resolved_version(self) -> MigratedPackage:
        if isinstance(self.selector, PackageVersion) and self.selector != self.version:
            raise ValueError("exact migration selector must match the resolved payload version")
        return self


class LegacyClaim(StrictModel):
    """Identify one legacy signature match without retaining its source bytes."""

    signature_id: KebabId
    target: SafeRelativePath
    observed_digest: Sha256Digest
    ownership: LegacyOwnership
    disposition: LegacyDisposition

    @model_validator(mode="after")
    def _safe_disposition(self) -> LegacyClaim:
        allowed: dict[LegacyOwnership, frozenset[LegacyDisposition]] = {
            "managed": frozenset(
                {
                    LegacyDisposition.ADOPT,
                    LegacyDisposition.PRESERVE,
                    LegacyDisposition.REMOVE,
                }
            ),
            "create-only": frozenset({LegacyDisposition.PRESERVE}),
            "shared": frozenset({LegacyDisposition.ADOPT, LegacyDisposition.PRESERVE}),
            "consumer-owned": frozenset({LegacyDisposition.PRESERVE}),
            "package-lock": frozenset({LegacyDisposition.IMPORT_LOCK}),
        }
        if self.disposition not in allowed[self.ownership]:
            raise ValueError("legacy claim disposition is not valid for its ownership class")
        return self


class MigrationFinding(StrictModel):
    """Content-free warning or error about one recognized migration identity."""

    code: str = Field(pattern=r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
    severity: Literal["error", "warning"]
    path: SafeRelativePath
    identity: KebabId


def _claim_sort_key(claim: LegacyClaim) -> tuple[str, ...]:
    return (
        claim.signature_id,
        claim.target.original,
        claim.observed_digest.value,
        claim.ownership,
        claim.disposition.value,
    )


def _finding_sort_key(finding: MigrationFinding) -> tuple[str, ...]:
    return (
        finding.identity,
        finding.path.original,
        finding.code,
        finding.severity,
    )


class MigrationReport(StrictModel):
    """One deterministic, schema-valid result from a selected migrate provider."""

    schema_version: Literal["1.0"]
    package: MigratedPackage
    claims: tuple[LegacyClaim, ...] = ()
    findings: tuple[MigrationFinding, ...] = ()

    @model_validator(mode="after")
    def _normalize_entries(self) -> MigrationReport:
        identities = [(claim.signature_id, claim.target.original) for claim in self.claims]
        if len(identities) != len(set(identities)):
            raise ValueError("migration report contains a duplicate legacy claim")
        object.__setattr__(self, "claims", tuple(sorted(self.claims, key=_claim_sort_key)))
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(self.findings, key=_finding_sort_key)),
        )
        return self


def migration_report_to_jsonable(report: MigrationReport) -> dict[str, object]:
    """Return stable public fields while withholding migrated option values."""
    selector = report.package.selector
    selector_value = selector.value if isinstance(selector, PackageVersion) else selector
    return {
        "schema_version": report.schema_version,
        "package": {
            "standard_id": report.package.standard_id,
            "version": report.package.version.value,
            "selector": selector_value,
            "recognized_settings": list(report.package.recognized_settings),
        },
        "claims": [
            {
                "signature_id": claim.signature_id,
                "target": claim.target.original,
                "observed_digest": claim.observed_digest.value,
                "ownership": claim.ownership,
                "disposition": claim.disposition.value,
            }
            for claim in report.claims
        ],
        "findings": [
            {
                "code": finding.code,
                "severity": finding.severity,
                "path": finding.path.original,
                "identity": finding.identity,
            }
            for finding in report.findings
        ],
    }


def render_migration_report(report: MigrationReport) -> str:
    """Render deterministic human evidence without option or source values."""
    selector = report.package.selector
    selector_value = selector.value if isinstance(selector, PackageVersion) else selector
    lines = [
        f"package {report.package.standard_id}@{report.package.version.value} ({selector_value})",
    ]
    lines.extend(f"setting {path}" for path in report.package.recognized_settings)
    lines.extend(
        "claim "
        f"{claim.signature_id} {claim.target.original} {claim.observed_digest.value} "
        f"{claim.ownership} {claim.disposition.value}"
        for claim in report.claims
    )
    lines.extend(
        f"finding {finding.severity} {finding.code} {finding.path.original} {finding.identity}"
        for finding in report.findings
    )
    return "\n".join(lines) + "\n"
