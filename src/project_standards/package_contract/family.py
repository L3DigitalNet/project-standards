"""Strict V2 package-family model and one-manifest loading boundary."""

from __future__ import annotations

import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)

KebabId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class StrictModel(BaseModel):
    """Reject undeclared contract fields and prevent model-field reassignment."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class FamilyStatus(StrEnum):
    """Lifecycle states shared by every package family."""

    DRAFT = "draft"
    REVIEW = "review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class StandardIdentity(StrictModel):
    """Stable identity and lifecycle metadata for one package family."""

    id: KebabId
    name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    status: FamilyStatus


class VersionIndexEntry(StrictModel):
    """Bind one exact package version to its manifest and aggregate digest."""

    version: PackageVersion
    payload: SafeRelativePath
    digest: Sha256Digest

    @model_validator(mode="after")
    def _canonical_payload_path(self) -> VersionIndexEntry:
        expected = f"versions/{self.version.value}/payload.toml"
        if self.payload.original != expected:
            raise ValueError("version entry must use its canonical payload path")
        return self


class FamilyManifest(StrictModel):
    """The complete strict `standards/{id}/standard.toml` V2 family index."""

    schema_version: Literal["2.0"]
    standard: StandardIdentity
    versions: list[VersionIndexEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_sorted_versions(self) -> FamilyManifest:
        seen: set[str] = set()
        for entry in self.versions:
            value = entry.version.value
            if value in seen:
                raise ValueError("family index contains a duplicate package version")
            seen.add(value)
        ordered = sorted(self.versions, key=lambda entry: entry.version.sort_key)
        object.__setattr__(self, "versions", ordered)
        return self


def _validation_summary(exc: ValidationError) -> str:
    """Return structural diagnostics without echoing untrusted input values."""
    summaries: list[str] = []
    for error in exc.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        location = ".".join(str(part) for part in error["loc"])
        summaries.append(f"{location or '<root>'}: {error['msg']}")
    return "; ".join(summaries)


def load_family_manifest(path: Path) -> FamilyManifest:
    """Load one V2 family index and wrap every boundary failure.

    The loader validates only family-owned files and declarations. Payload file
    discovery and inventory validation belong to later repository-level stages.
    """
    if path.name != "standard.toml":
        raise PackageContractError("family index path must end in standard.toml")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PackageContractError(f"cannot read family index {path}") from exc
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PackageContractError(f"family index {path} is not valid TOML") from exc
    try:
        manifest = FamilyManifest.model_validate(raw)
    except ValidationError as exc:
        summary = _validation_summary(exc)
        raise PackageContractError(
            f"family index {path} violates the V2 contract: {summary}"
        ) from exc

    if manifest.standard.id != path.parent.name:
        raise PackageContractError("family standard ID does not match its directory identity")

    readme = path.parent / "README.md"
    try:
        if readme.is_symlink() or not readme.is_file():
            raise PackageContractError("family directory must contain a regular README.md")
    except OSError as exc:
        raise PackageContractError("family README.md could not be inspected") from exc
    return manifest
