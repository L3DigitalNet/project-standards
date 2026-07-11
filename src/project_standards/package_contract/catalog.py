"""Catalog-major channel declarations and deterministic consumer catalog facts."""

from __future__ import annotations

import json
import os
import tempfile
import tomllib
from collections import defaultdict
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import (
    FamilyManifest,
    KebabId,
    StrictModel,
)
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import (
    PayloadAvailability,
    PayloadManifest,
)


class CatalogRole(StrEnum):
    """Catalog-major selection role assigned to one exact payload."""

    DEFAULT = "default"
    RETAINED = "retained"
    CANDIDATE = "candidate"
    REFERENCE_ONLY = "reference-only"
    INTERNAL = "internal"


class CatalogPackageEntry(StrictModel):
    """Bind one indexed package version and digest to a catalog role."""

    id: KebabId
    version: PackageVersion
    digest: Sha256Digest
    role: CatalogRole


class CatalogSource(StrictModel):
    """Strict author-owned source for one catalog major."""

    schema_version: Literal["1.0"]
    catalog_major: int = Field(ge=1)
    packages: list[CatalogPackageEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_sorted_entries(self) -> CatalogSource:
        keys = [(entry.id, entry.version.value) for entry in self.packages]
        if len(keys) != len(set(keys)):
            raise ValueError("catalog contains a duplicate package/version entry")
        ordered = sorted(
            self.packages,
            key=lambda entry: (entry.id, entry.version.sort_key),
        )
        object.__setattr__(self, "packages", ordered)
        return self


def _validation_summary(exc: ValidationError) -> str:
    summaries: list[str] = []
    for error in exc.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        location = ".".join(str(part) for part in error["loc"])
        summaries.append(f"{location or '<root>'}: {error['msg']}")
    return "; ".join(summaries)


def load_catalog_source(path: Path) -> CatalogSource:
    """Load one `catalogs/{catalog-major}.toml` declaration."""
    if path.parent.name != "catalogs":
        raise PackageContractError("catalog source must be inside a catalogs directory")
    try:
        path_major = int(path.stem)
    except ValueError as exc:
        raise PackageContractError("catalog source filename must be its catalog major") from exc
    if path.suffix != ".toml":
        raise PackageContractError("catalog source must use a .toml filename")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PackageContractError(f"cannot read catalog source {path}") from exc
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PackageContractError(f"catalog source {path} is not valid TOML") from exc
    try:
        source = CatalogSource.model_validate(raw)
    except ValidationError as exc:
        raise PackageContractError(
            f"catalog source {path} violates the V2 contract: {_validation_summary(exc)}"
        ) from exc
    if source.catalog_major != path_major:
        raise PackageContractError("catalog major does not match its filename")
    return source


def validate_catalog_source(
    source: CatalogSource,
    families: Mapping[str, FamilyManifest],
    payloads: Mapping[tuple[str, str], PayloadManifest],
) -> CatalogSource:
    """Cross-check roles against exact indexed payload identities and availability."""
    by_standard: dict[str, list[CatalogPackageEntry]] = defaultdict(list)
    for entry in source.packages:
        family = families.get(entry.id)
        if family is None or family.standard.id != entry.id:
            raise PackageContractError(
                f"catalog {source.catalog_major}: unknown package {entry.id}"
            )
        indexed = next(
            (version for version in family.versions if version.version == entry.version),
            None,
        )
        if indexed is None:
            raise PackageContractError(
                f"catalog {source.catalog_major}: unknown package version "
                f"{entry.id}@{entry.version.value}"
            )
        if indexed.digest != entry.digest:
            raise PackageContractError(
                f"catalog {source.catalog_major}: digest mismatch for "
                f"{entry.id}@{entry.version.value}"
            )
        payload = payloads.get((entry.id, entry.version.value))
        if payload is None:
            raise PackageContractError(
                f"catalog {source.catalog_major}: payload is unavailable for "
                f"{entry.id}@{entry.version.value}"
            )
        if payload.payload.standard != entry.id or payload.payload.version != entry.version:
            raise PackageContractError(
                f"catalog {source.catalog_major}: payload identity mismatch for "
                f"{entry.id}@{entry.version.value}"
            )
        _validate_role_availability(source.catalog_major, entry, payload)
        by_standard[entry.id].append(entry)

    for standard_id, entries in sorted(by_standard.items()):
        consumer_entries = [
            entry
            for entry in entries
            if payloads[(entry.id, entry.version.value)].payload.availability
            is PayloadAvailability.CONSUMER
        ]
        if not consumer_entries:
            continue
        defaults = [entry for entry in consumer_entries if entry.role is CatalogRole.DEFAULT]
        if len(defaults) != 1:
            raise PackageContractError(
                f"catalog {source.catalog_major}: consumer package {standard_id} "
                "must have exactly one default"
            )
        default_major = defaults[0].version.major
        if any(
            entry.role is CatalogRole.CANDIDATE and entry.version.major == default_major
            for entry in consumer_entries
        ):
            raise PackageContractError(
                f"catalog {source.catalog_major}: candidate for {standard_id} "
                "must use a non-default package major"
            )
    return source


def _validate_role_availability(
    catalog_major: int,
    entry: CatalogPackageEntry,
    payload: PayloadManifest,
) -> None:
    allowed = {
        PayloadAvailability.CONSUMER: frozenset(
            {CatalogRole.DEFAULT, CatalogRole.RETAINED, CatalogRole.CANDIDATE}
        ),
        PayloadAvailability.REFERENCE_ONLY: frozenset({CatalogRole.REFERENCE_ONLY}),
        PayloadAvailability.INTERNAL: frozenset({CatalogRole.INTERNAL}),
    }[payload.payload.availability]
    if entry.role not in allowed:
        raise PackageContractError(
            f"catalog {catalog_major}: role {entry.role.value} disagrees with "
            f"payload availability for {entry.id}@{entry.version.value}"
        )


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def render_consumer_catalog(
    source: CatalogSource,
    families: Mapping[str, FamilyManifest],
    payloads: Mapping[tuple[str, str], PayloadManifest],
    *,
    tool_release: str,
) -> bytes:
    """Render the deterministic package/channel subset of the CP01 catalog."""
    validated = validate_catalog_source(source, families, payloads)
    grouped: dict[str, list[CatalogPackageEntry]] = defaultdict(list)
    for entry in validated.packages:
        grouped[entry.id].append(entry)

    lines = [
        "[project_standards]",
        'schema_version = "1.0"',
        f'catalog = "{validated.catalog_major}"',
        f"release = {_toml_string(tool_release)}",
        "",
    ]
    channel_names = {
        CatalogRole.DEFAULT: "stable",
        CatalogRole.RETAINED: "retained",
        CatalogRole.CANDIDATE: "breaking-candidate",
        CatalogRole.REFERENCE_ONLY: "reference-only",
        CatalogRole.INTERNAL: "internal",
    }
    for standard_id, entries in sorted(grouped.items()):
        family = families[standard_id]
        available = [entry.version.value for entry in entries]
        defaults = [entry.version.value for entry in entries if entry.role is CatalogRole.DEFAULT]
        candidates = [
            entry.version.value for entry in entries if entry.role is CatalogRole.CANDIDATE
        ]
        lines.extend(
            [
                f"[standards.{standard_id}]",
                f"status = {_toml_string(family.standard.status.value)}",
                f"available = {_toml_array(available)}",
            ]
        )
        if defaults:
            lines.append(f"default = {_toml_string(defaults[0])}")
        lines.append(f"candidates = {_toml_array(candidates)}")
        lines.append("")
        for entry in entries:
            version = entry.version.value
            availability = payloads[(standard_id, version)].payload.availability.value
            lines.extend(
                [
                    f"[standards.{standard_id}.versions.{_toml_string(version)}]",
                    f"channel = {_toml_string(channel_names[entry.role])}",
                    f"availability = {_toml_string(availability)}",
                    f"payload_digest = {_toml_string(entry.digest.value)}",
                    "",
                ]
            )
    return ("\n".join(lines).rstrip() + "\n").encode()


def write_consumer_catalog(output: Path, content: bytes, *, check: bool) -> bool:
    """Compare read-only in check mode, otherwise atomically replace one chosen path."""
    if check:
        try:
            return output.read_bytes() == content
        except OSError:
            return False

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        dir=output.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o644)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return True
