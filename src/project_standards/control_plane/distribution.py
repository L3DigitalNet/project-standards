"""Offline access to catalog and payload facts embedded in the installed wheel."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from pydantic import ValidationError

import project_standards
from project_standards._version import package_version
from project_standards.control_plane.diagnostics import validation_summary
from project_standards.control_plane.paths import CatalogMajor
from project_standards.package_contract.catalog import (
    CatalogRole,
    CatalogSource,
    load_catalog_source,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import (
    PayloadIntegrity,
    validate_payload_integrity,
)
from project_standards.package_contract.payload import (
    PayloadAvailability,
    PayloadManifest,
)

_TOOL_RELEASE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
    re.ASCII,
)


@dataclass(frozen=True, slots=True)
class ParsedToolRelease:
    """Canonical SemVer release used for installed/catalog lineage checks."""

    value: str
    major: int = field(init=False)
    minor: int = field(init=False)
    patch: int = field(init=False)

    def __post_init__(self) -> None:
        match = _TOOL_RELEASE.fullmatch(self.value)
        if match is None:
            raise PackageContractError("tool release must be canonical MAJOR.MINOR.PATCH")
        object.__setattr__(self, "major", int(match.group(1)))
        object.__setattr__(self, "minor", int(match.group(2)))
        object.__setattr__(self, "patch", int(match.group(3)))

    @property
    def sort_key(self) -> tuple[int, int, int]:
        """Return numeric SemVer components for lineage comparisons."""
        return (self.major, self.minor, self.patch)


@dataclass(frozen=True, slots=True)
class InstalledPayload:
    """One integrity-checked payload selected by an embedded catalog entry."""

    root: Path
    manifest: PayloadManifest
    integrity: PayloadIntegrity


@dataclass(frozen=True, slots=True)
class InstalledCatalog:
    """One embedded catalog source and all of its verified payloads."""

    source: CatalogSource
    payloads: tuple[InstalledPayload, ...]

    @property
    def payload_map(self) -> dict[tuple[str, str], InstalledPayload]:
        """Return verified payloads keyed by exact standard and version."""
        return {
            (
                payload.manifest.payload.standard,
                payload.manifest.payload.version.value,
            ): payload
            for payload in self.payloads
        }


def _load_installed_payload(path: Path) -> PayloadManifest:
    manifest_path = path / "payload.toml"
    try:
        if path.is_symlink() or not path.is_dir():
            raise PackageContractError("catalog payload is unavailable from the installation")
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise PackageContractError("catalog payload manifest is unavailable")
        text = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PackageContractError("catalog payload manifest could not be read") from exc
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PackageContractError("catalog payload manifest is not valid TOML") from exc
    try:
        manifest = PayloadManifest.model_validate(raw)
    except ValidationError as exc:
        raise PackageContractError(
            f"catalog payload manifest violates its schema: {validation_summary(exc)}"
        ) from exc
    if manifest.payload.standard != path.parent.name:
        raise PackageContractError("installed payload standard identity does not match its path")
    if manifest.payload.version.value != path.name:
        raise PackageContractError("installed payload version does not match its path")
    return manifest


def _validate_role(entry_role: CatalogRole, availability: PayloadAvailability) -> None:
    allowed = {
        PayloadAvailability.CONSUMER: frozenset(
            {CatalogRole.DEFAULT, CatalogRole.RETAINED, CatalogRole.CANDIDATE}
        ),
        PayloadAvailability.REFERENCE_ONLY: frozenset({CatalogRole.REFERENCE_ONLY}),
        PayloadAvailability.INTERNAL: frozenset({CatalogRole.INTERNAL}),
    }[availability]
    if entry_role not in allowed:
        raise PackageContractError("installed payload availability disagrees with catalog role")


@dataclass(frozen=True, slots=True)
class InstalledDistribution:
    """The sole production boundary for embedded catalog and payload content."""

    package_root: Path
    tool_release: ParsedToolRelease

    def __init__(self, package_root: Path, *, tool_release: str) -> None:
        try:
            if package_root.is_symlink() or not package_root.is_dir():
                raise PackageContractError(
                    "installed project_standards root must be a regular directory"
                )
            normalized = package_root.resolve(strict=True)
        except OSError as exc:
            raise PackageContractError("installed package root could not be resolved") from exc
        object.__setattr__(self, "package_root", normalized)
        object.__setattr__(self, "tool_release", ParsedToolRelease(tool_release))

    @classmethod
    def current(cls) -> InstalledDistribution:
        """Resolve the active distribution through the standard resource API."""
        resource_root = resources.files(project_standards)
        if not isinstance(resource_root, Path):
            raise PackageContractError(
                "installed project_standards resources require a filesystem-backed wheel"
            )
        return cls(resource_root, tool_release=package_version())

    def load_catalog(
        self,
        catalog: CatalogMajor | str,
        *,
        recorded_release: str | None = None,
    ) -> InstalledCatalog:
        """Load one compatible catalog and verify every selected payload byte."""
        major = catalog if isinstance(catalog, CatalogMajor) else CatalogMajor(catalog)
        if self.tool_release.major != major.major:
            raise PackageContractError(
                "installed tool major does not match the requested catalog major"
            )
        if recorded_release is not None:
            recorded = ParsedToolRelease(recorded_release)
            if recorded.major != major.major:
                raise PackageContractError("recorded release is outside the catalog major")
            if recorded.sort_key > self.tool_release.sort_key:
                raise PackageContractError(
                    "recorded catalog release is newer than the installed tool release"
                )

        source_path = self.package_root / f"catalogs/{major.value}.toml"
        try:
            if source_path.is_symlink() or not source_path.is_file():
                raise PackageContractError("installed catalog projection is unavailable")
        except OSError as exc:
            raise PackageContractError(
                "installed catalog projection could not be inspected"
            ) from exc
        source = load_catalog_source(source_path)
        if source.catalog_major != major.major:
            raise PackageContractError("installed catalog identity does not match the request")

        payloads: list[InstalledPayload] = []
        for entry in source.packages:
            payload_root = self.package_root / "payloads" / entry.id / entry.version.value
            manifest = _load_installed_payload(payload_root)
            if manifest.payload.standard != entry.id or manifest.payload.version != entry.version:
                raise PackageContractError("installed payload identity disagrees with catalog")
            _validate_role(entry.role, manifest.payload.availability)
            integrity = validate_payload_integrity(
                payload_root,
                manifest,
                expected_digest=entry.digest,
            )
            payloads.append(InstalledPayload(payload_root, manifest, integrity))
        return InstalledCatalog(source, tuple(payloads))
