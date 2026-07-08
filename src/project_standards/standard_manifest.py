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

import json
import re
import tomllib
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
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
    """A bundle-relative path with no traversal, absolute, Windows-drive/backslash escape, or null byte.

    The null-byte check matters even though `PurePosixPath` is pure string
    manipulation and would otherwise happily accept it: an embedded null byte
    passed on to a real filesystem call (`Path.resolve()`, `Path.exists()`, ...)
    raises a raw `ValueError` from the stdlib, not something this module controls.
    Rejecting it here, at model-validation time, turns that into a
    `pydantic.ValidationError` for every `ResourcesTable` consumer, not just the
    loader's post-check (which also guards its own filesystem calls — see
    `load_standard_manifest`).
    """
    if not value or "\x00" in value or "\\" in value or re.match(r"^[A-Za-z]:", value):
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


class AuthorityBlock(_Table):
    """One `[[authority]]` entry: an owner's exclusive claim over a target/concern pair."""

    domain: str = Field(min_length=1)
    target: str = Field(min_length=1)
    concern: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    mutates: bool


OperationToken = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]

_PY_ENTRYPOINT_RE = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*:[a-zA-Z_][a-zA-Z0-9_]*$"
)
_TOKEN_ENTRYPOINT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_entrypoint(kind: ProviderKind, value: str) -> None:
    """Per-kind entrypoint grammar: reject filesystem-path shapes, then check the kind's token form."""
    if "/" in value or "\\" in value or ".." in value or re.match(r"^[A-Za-z]:[\\/]", value):
        msg = f"entrypoint {value!r} looks like a filesystem path"
        raise ValueError(msg)
    if kind is ProviderKind.PYTHON:
        if not _PY_ENTRYPOINT_RE.match(value):
            msg = f"python entrypoint {value!r} must be module.path:object"
            raise ValueError(msg)
    elif not _TOKEN_ENTRYPOINT_RE.match(value):
        msg = f"{kind.value} entrypoint {value!r} must be a bare safe token"
        raise ValueError(msg)


class ProviderBlock(_Table):
    """One `[[providers]]` entry: an operation this standard mechanizes, and how to invoke it."""

    operation: OperationToken
    kind: ProviderKind
    optional: bool
    entrypoint: str | None = None
    input_schema: str | None = None
    output_schema: str | None = None

    @model_validator(mode="after")
    def _entrypoint_by_kind(self) -> ProviderBlock:
        if self.kind is ProviderKind.DOCUMENTATION_ONLY:
            if self.entrypoint is not None:
                msg = "documentation-only provider must not declare an entrypoint"
                raise ValueError(msg)
            return self
        if not self.entrypoint:
            msg = f"{self.kind.value} provider requires an entrypoint"
            raise ValueError(msg)
        _validate_entrypoint(self.kind, self.entrypoint)
        return self


class StandardManifest(_Table):
    """The top-level `standard.toml` document: all required and optional tables.

    Subclasses `_Table` (`extra="forbid"`) so an unrecognized top-level table name
    is rejected here rather than silently ignored. Field names are load-bearing for
    Step 04's loader (`manifest.standard.id`, `manifest.resources.as_dict()`).
    """

    standard: StandardTable
    versions: VersionsTable
    config: ConfigTable
    capabilities: CapabilitiesTable
    resources: ResourcesTable
    relations: RelationsTable = Field(default_factory=RelationsTable)
    authority: list[AuthorityBlock] = Field(default_factory=list)
    providers: list[ProviderBlock] = Field(default_factory=list)

    @model_validator(mode="after")
    def _adopt_conditional(self) -> StandardManifest:
        if self.standard.adoption is AdoptionMode.NONE and "adopt" in self.resources.as_dict():
            msg = 'adoption = "none" must not declare an `adopt` resource'
            raise ValueError(msg)
        return self


_SCHEMA_ID = (
    "https://raw.githubusercontent.com/L3DigitalNet/project-standards/main"
    "/src/project_standards/schemas/standard.schema.json"
)


def standard_schema() -> dict[str, object]:
    """The JSON Schema for standard.toml, generated from StandardManifest."""
    body = StandardManifest.model_json_schema()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": _SCHEMA_ID,
        **body,
    }


def standard_schema_json() -> str:
    """Canonical serialization: preserve key order (no sort_keys), 2-space indent, trailing newline."""
    return json.dumps(standard_schema(), indent=2, ensure_ascii=False) + "\n"


def load_standard_manifest(path: Path) -> StandardManifest:
    """Parse and validate one standard.toml, returning the typed model.

    Raises StandardManifestError (only) on read/parse/validation/containment failure —
    no raw TOMLDecodeError/OSError/ValidationError crosses this boundary.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"cannot read {path}: {exc}"
        raise StandardManifestError(msg) from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        msg = f"{path} is not valid TOML: {exc}"
        raise StandardManifestError(msg) from exc
    try:
        manifest = StandardManifest.model_validate(data)
    except ValidationError as exc:
        msg = f"{path} violates the standard.toml contract:\n{exc}"
        raise StandardManifestError(msg) from exc

    bundle_dir = path.parent
    if manifest.standard.id != bundle_dir.name:
        msg = f"standard id {manifest.standard.id!r} != bundle directory {bundle_dir.name!r}"
        raise StandardManifestError(msg)

    # `_is_safe_bundle_path` rejects the shapes we know about (traversal, absolute,
    # null byte, ...) at model-validation time, but the filesystem calls below can
    # still raise for reasons that check can't anticipate (broken symlink,
    # permission denied mid-path, a null byte that slipped through some other
    # `ResourcesTable` construction path, ...). Wrap the whole post-check block so
    # any such OSError/ValueError is turned into a StandardManifestError rather than
    # crossing this function's boundary raw.
    try:
        base = bundle_dir.resolve()
        for key, value in manifest.resources.as_dict().items():
            target = (bundle_dir / value).resolve()
            if not target.is_relative_to(base):
                msg = (
                    f"resource {key!r} path {value!r} escapes bundle directory {bundle_dir.name!r}"
                )
                raise StandardManifestError(msg)
            if not target.exists():
                msg = (
                    f"resource {key!r} path {value!r} does not exist in bundle {bundle_dir.name!r}"
                )
                raise StandardManifestError(msg)
    except (OSError, ValueError) as exc:
        if isinstance(exc, StandardManifestError):
            raise
        msg = f"{path} resource paths could not be resolved: {exc}"
        raise StandardManifestError(msg) from exc
    return manifest
