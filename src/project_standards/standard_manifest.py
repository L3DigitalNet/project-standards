"""Typed model and loader for a single standard.toml manifest (SPEC-MT01 Step 03).

Mechanizes the Standard Bundle Authoring Standard (SPEC-BA01) contract for ONE
manifest: validate its shape and single-manifest self-consistency, and expose the
data as a typed object. Cross-standard rules — authority conflicts, namespace
duplicate-ownership across standards, relationship-graph acyclicity, extends-needs-
an-ADR, hidden-dependency rejection — are Step 04's standards-graph validator.

This module intentionally omits `from __future__ import annotations`: its field
annotations are resolved at runtime by Pydantic, and the future import would turn
them into strings Pydantic must re-resolve (python-coding annotations guidance).
"""

from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class StandardManifestError(ValueError):
    """standard.toml is missing, unreadable, malformed, or violates the contract.

    The single error type load_standard_manifest raises; it wraps
    tomllib.TOMLDecodeError, OSError, and pydantic.ValidationError so no raw parser
    or I/O traceback crosses the boundary. Maps to exit code 2 at the future Step 04
    CLI boundary.
    """


class AdoptionMode(StrEnum):
    VALIDATOR = "validator"
    COPY_ADOPT = "copy-adopt"
    CLI = "cli"
    REFERENCE_ONLY = "reference-only"
    NONE = "none"


class LifecycleStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class ProviderKind(StrEnum):
    PYTHON = "python"
    COMMAND = "command"
    WORKFLOW = "workflow"
    DOCUMENTATION_ONLY = "documentation-only"


class _Table(BaseModel):
    """Fixed-shape table base: unknown keys are rejected (catches the reserved `requires` key)."""

    model_config = ConfigDict(extra="forbid")


KebabId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]


class StandardTable(_Table):
    """The `[standard]` table: a manifest's identity and lifecycle status."""

    id: KebabId
    name: str = Field(min_length=1)
    status: LifecycleStatus
    summary: str = Field(min_length=1)
    adoption: AdoptionMode


class VersionsTable(_Table):
    """The `[versions]` table: supported version list plus the currently-latest one."""

    supported: list[str]
    latest: str

    @model_validator(mode="after")
    def _latest_in_supported(self) -> VersionsTable:
        if self.supported and self.latest and self.latest not in self.supported:
            msg = f"latest {self.latest!r} is not in supported {self.supported}"
            raise ValueError(msg)
        return self


_RESERVED_NAMESPACES = frozenset({"standards_version"})
DottedPath = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9]+(_[a-z0-9]+)*(\.[a-z0-9]+(_[a-z0-9]+)*)*$")
]


class ConfigTable(_Table):
    """The `[config]` table: dotted namespaces this standard owns in consumer repo config."""

    namespaces: list[DottedPath]

    @field_validator("namespaces")
    @classmethod
    def _no_reserved_or_duplicate(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        for ns in value:
            if ns in _RESERVED_NAMESPACES:
                msg = f"namespace {ns!r} is a reserved repo-meta key, not standard-owned"
                raise ValueError(msg)
            if ns in seen:
                msg = f"duplicate namespace {ns!r} within manifest"
                raise ValueError(msg)
            seen.add(ns)
        return value


class CapabilitiesTable(_Table):
    """The `[capabilities]` table: what this standard provides and what platform features it needs."""

    provides: list[str]
    consumes_platform: list[str]


class RelationsTable(_Table):
    """The `[relations]` table: this standard's ties to other standards.

    All fields are optional lists; a stray `requires` key is rejected by
    `_Table`'s `extra="forbid"` — dependency requirements are Step 04's
    standards-graph concern, not a single-manifest field.
    """

    companions: list[str] = Field(default_factory=list)
    extends: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
