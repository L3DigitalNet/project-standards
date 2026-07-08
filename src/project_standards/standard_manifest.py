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

import re
from enum import StrEnum
from pathlib import PurePosixPath
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


_RESOURCE_ID_RE = re.compile(r"^[a-z0-9]+([_-][a-z0-9]+)*$")


def _is_safe_bundle_path(value: str) -> bool:
    """A bundle-relative path with no traversal, absolute, or Windows-drive/backslash escape."""
    if not value or "\\" in value or re.match(r"^[A-Za-z]:", value):
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and ".." not in p.parts


class ResourcesTable(BaseModel):
    """The `[resources]` table: the ONE intentionally open mapping (not a `_Table`).

    `readme` is required; any other key is an arbitrary URI-safe resource ID whose
    value is a bundle-relative path. Extras are TYPED as str via `__pydantic_extra__`
    so a non-string TOML value (int, array, table) is rejected by Pydantic rather
    than silently coerced (Codex review CR-001) — do not revert to `str(value)`.
    """

    model_config = ConfigDict(extra="allow")
    # BaseModel declares `Dict[str, Any] | None`; pydantic's documented pattern for
    # typed extras narrows this, which basedpyright strict flags as an incompatible
    # override (dict is invariant). The narrowing is intentional (see class
    # docstring), so the override warning is expected, not a bug.
    __pydantic_extra__: dict[str, str]  # pyright: ignore[reportIncompatibleVariableOverride]

    readme: str

    @model_validator(mode="after")
    def _validate_ids_and_paths(self) -> ResourcesTable:
        for key, value in self.as_dict().items():
            if not _RESOURCE_ID_RE.match(key):
                msg = f"resource id {key!r} is not a URI-safe token"
                raise ValueError(msg)
            if not _is_safe_bundle_path(value):
                msg = f"resource {key!r} path {value!r} is not a safe bundle-relative path"
                raise ValueError(msg)
        return self

    def as_dict(self) -> dict[str, str]:
        return {"readme": self.readme, **self.__pydantic_extra__}
