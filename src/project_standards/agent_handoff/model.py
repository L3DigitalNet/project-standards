"""Typed boundaries shared by agent-handoff planning, validation, and reporting."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class StartupMode(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class Harness(StrEnum):
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"


def _validate_profile(startup: StartupMode, harnesses: tuple[Harness, ...]) -> None:
    if len(set(harnesses)) != len(harnesses):
        raise ValueError("harnesses must be unique")
    if startup is StartupMode.AUTOMATIC and not harnesses:
        raise ValueError("automatic startup requires at least one harness")
    if startup is StartupMode.MANUAL and harnesses:
        raise ValueError("manual startup requires an empty harness list")


class AgentHandoffConfig(BaseModel):
    """The strict agent_handoff namespace owned inside project configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["1.0"]
    startup: StartupMode
    harnesses: tuple[Harness, ...]

    @model_validator(mode="after")
    def _profile_is_consistent(self) -> Self:
        _validate_profile(self.startup, self.harnesses)
        return self


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Literal["error", "warning"]
    path: str
    locus: str
    message: str
    guidance: str
    line: int | None = None
    column: int | None = None
    observed: int | None = None
    limit: int | None = None

    def __post_init__(self) -> None:
        for name, value, minimum in (
            ("line", self.line, 1),
            ("column", self.column, 1),
            ("observed", self.observed, 0),
            ("limit", self.limit, 1),
        ):
            if value is not None and (type(value) is not int or value < minimum):
                raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")

    @property
    def sort_key(self) -> tuple[object, ...]:
        return (
            self.path,
            self.line if self.line is not None else -1,
            self.column if self.column is not None else -1,
            self.code,
            self.locus,
            self.message,
            self.observed if self.observed is not None else -1,
            self.limit if self.limit is not None else -1,
        )

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "locus": self.locus,
            "message": self.message,
            "guidance": self.guidance,
        }
        result.update(
            (name, value)
            for name, value in (
                ("line", self.line),
                ("column", self.column),
                ("observed", self.observed),
                ("limit", self.limit),
            )
            if value is not None
        )
        return result


class ChangeKind(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PlannedChange:
    kind: ChangeKind
    path: str
    source: str | None = None
    precondition_sha256: str | None = None

    def __post_init__(self) -> None:
        if (
            self.precondition_sha256 is not None
            and _SHA256_RE.fullmatch(self.precondition_sha256) is None
        ):
            raise ValueError("precondition must be a lowercase SHA-256 digest")

    @property
    def sort_key(self) -> tuple[str, str]:
        return (self.path, self.kind.value)

    def to_dict(self) -> dict[str, str]:
        result = {"kind": self.kind.value, "path": self.path}
        if self.source is not None:
            result["source"] = self.source
        if self.precondition_sha256 is not None:
            result["precondition_sha256"] = self.precondition_sha256
        return result


class _ReportFinding(BaseModel):
    """Closed serialized finding shape for the current report envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    severity: Literal["error", "warning"]
    path: str
    locus: str
    message: str
    guidance: str
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    observed: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=1)


class _ReportChange(BaseModel):
    """Closed serialized change shape for the current report envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ChangeKind
    path: str
    source: str | None = None
    precondition_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class _ReportSummary(BaseModel):
    """Closed aggregate counts for the current report envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    blocked: int = Field(ge=0)
    created: int = Field(ge=0)
    errors: int = Field(ge=0)
    skipped: int = Field(ge=0)
    updated: int = Field(ge=0)
    warnings: int = Field(ge=0)


class OperationReportEnvelope(BaseModel):
    """Closed Agent Handoff report schema recognized by current consumers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.1"]
    repository: str
    standard_version: str
    changes: list[_ReportChange]
    findings: list[_ReportFinding]
    summary: _ReportSummary


@dataclass(frozen=True)
class OperationReport:
    repository: str
    standard_version: str
    changes: tuple[PlannedChange, ...] = ()
    findings: tuple[Finding, ...] = ()
    schema_version: Literal["1.1"] = field(default="1.1", init=False)

    @property
    def blocked(self) -> bool:
        """Whether errors or explicitly blocked changes prohibit success."""
        return any(finding.severity == "error" for finding in self.findings) or any(
            change.kind is ChangeKind.BLOCKED for change in self.changes
        )

    def to_dict(self) -> dict[str, object]:
        changes = sorted(self.changes, key=lambda change: change.sort_key)
        findings = sorted(self.findings, key=lambda finding: finding.sort_key)
        envelope = OperationReportEnvelope.model_validate(
            {
                "schema_version": self.schema_version,
                "repository": self.repository,
                "standard_version": self.standard_version,
                "changes": [change.to_dict() for change in changes],
                "findings": [finding.to_dict() for finding in findings],
                "summary": {
                    "blocked": sum(change.kind is ChangeKind.BLOCKED for change in changes),
                    "created": sum(change.kind is ChangeKind.CREATE for change in changes),
                    "errors": sum(finding.severity == "error" for finding in findings),
                    "skipped": sum(change.kind is ChangeKind.SKIP for change in changes),
                    "updated": sum(change.kind is ChangeKind.UPDATE for change in changes),
                    "warnings": sum(finding.severity == "warning" for finding in findings),
                },
            }
        )
        return envelope.model_dump(mode="json", exclude_none=True)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"


def emit_report(report: OperationReport, *, as_json: bool) -> int:
    if as_json:
        print(report.to_json(), end="")
    else:
        for change in sorted(report.changes, key=lambda item: item.sort_key):
            print(f"{change.kind.value}: {change.path}")
        for finding in sorted(report.findings, key=lambda item: item.sort_key):
            location = finding.path
            if finding.line is not None:
                location = f"{location}:{finding.line}"
                if finding.column is not None:
                    location = f"{location}:{finding.column}"
            details: list[str] = []
            details.append(f"locus: {finding.locus}")
            if finding.observed is not None:
                details.append(f"observed: {finding.observed}")
            if finding.limit is not None:
                details.append(f"limit: {finding.limit}")
            suffix = f" ({'; '.join(details)})" if details else ""
            print(
                f"{finding.severity}: {location}: {finding.message}{suffix}",
                file=sys.stderr,
            )
    return 1 if report.blocked else 0


class ProvenanceLock(BaseModel):
    """Hashes for standard-managed artifacts and normalized integration entries."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    standard: Literal["agent-handoff"] = "agent-handoff"
    standard_version: Literal["1.0"] = Field(
        validation_alias=AliasChoices("standard_version", "version"),
        serialization_alias="version",
    )
    startup: StartupMode
    harnesses: tuple[Harness, ...]
    managed: dict[str, str]

    @field_validator("managed")
    @classmethod
    def _managed_hashes_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        for path, digest in value.items():
            if not path:
                raise ValueError("managed path must not be empty")
            if _SHA256_RE.fullmatch(digest) is None:
                raise ValueError(f"managed hash for {path!r} must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def _profile_is_consistent(self) -> Self:
        _validate_profile(self.startup, self.harnesses)
        return self

    def to_json(self) -> str:
        payload = self.model_dump(mode="json", by_alias=True)
        payload["managed"] = dict(sorted(self.managed.items()))
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
