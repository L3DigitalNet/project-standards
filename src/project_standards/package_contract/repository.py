"""Load-only repository boundary for version-qualified V2 package facts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from project_standards.package_contract.catalog import (
    CatalogSource,
    load_catalog_source,
    validate_catalog_source,
)
from project_standards.package_contract.diagnostics import (
    PackageContractError,
    PackageFinding,
    sort_findings,
)
from project_standards.package_contract.discovery import discover_v2_families
from project_standards.package_contract.family import FamilyManifest, load_family_manifest
from project_standards.package_contract.integrity import (
    PayloadIntegrity,
    validate_payload_integrity,
)
from project_standards.package_contract.payload import (
    PackageOptionSchema,
    PayloadManifest,
    load_option_schema,
    load_payload_manifest,
)


@dataclass(frozen=True, slots=True)
class LoadedPayload:
    """One fully loaded and integrity-checked package payload."""

    manifest: PayloadManifest
    integrity: PayloadIntegrity
    option_schema: PackageOptionSchema


@dataclass(frozen=True, slots=True)
class LoadedFamily:
    """One family index and the indexed payloads that loaded successfully."""

    manifest: FamilyManifest
    payloads: tuple[LoadedPayload, ...]


@dataclass(frozen=True, slots=True)
class PackageRepository:
    """Deterministic normalized package facts and aggregated load findings."""

    root: Path
    families: tuple[LoadedFamily, ...]
    catalog: CatalogSource | None
    findings: tuple[PackageFinding, ...]

    @property
    def payloads(self) -> tuple[LoadedPayload, ...]:
        return tuple(payload for family in self.families for payload in family.payloads)

    @property
    def family_map(self) -> dict[str, FamilyManifest]:
        return {family.manifest.standard.id: family.manifest for family in self.families}

    @property
    def payload_map(self) -> dict[tuple[str, str], PayloadManifest]:
        return {
            (
                payload.manifest.payload.standard,
                payload.manifest.payload.version.value,
            ): payload.manifest
            for payload in self.payloads
        }


def _finding(
    code: str,
    standard_id: str,
    version: str,
    path: str,
    identity: str,
    message: str,
) -> PackageFinding:
    return PackageFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path=path,
        identity=identity,
        message=message,
        hint="repair the declared V2 package source and rerun repository validation",
    )


def build_package_repository(
    root: Path,
    *,
    catalog_major: int | None = None,
    family_allowlist: Iterable[str] | None = None,
) -> PackageRepository:
    """Load declared V2 sources without interpreting V1 manifests or unindexed trees."""
    discovery = discover_v2_families(root, family_allowlist=family_allowlist)
    findings = list(discovery.findings)
    loaded_families: list[LoadedFamily] = []
    for family_path in discovery.paths:
        standard_id = family_path.parent.name
        relative_family_path = f"standards/{standard_id}/standard.toml"
        try:
            manifest = load_family_manifest(family_path)
        except PackageContractError as exc:
            findings.append(
                _finding(
                    "PC-FAMILY-LOAD",
                    standard_id,
                    "",
                    relative_family_path,
                    "family",
                    str(exc),
                )
            )
            continue

        loaded_payloads: list[LoadedPayload] = []
        for version_entry in manifest.versions:
            version = version_entry.version.value
            relative_payload_path = (
                f"standards/{standard_id}/{version_entry.payload.normalized.as_posix()}"
            )
            payload_path = family_path.parent / version_entry.payload.normalized
            try:
                payload_manifest = load_payload_manifest(payload_path)
            except PackageContractError as exc:
                findings.append(
                    _finding(
                        "PC-PAYLOAD-LOAD",
                        standard_id,
                        version,
                        relative_payload_path,
                        "payload",
                        str(exc),
                    )
                )
                continue
            try:
                integrity = validate_payload_integrity(
                    payload_path.parent,
                    payload_manifest,
                    expected_digest=version_entry.digest,
                )
            except PackageContractError as exc:
                findings.append(
                    _finding(
                        "PC-INTEGRITY",
                        standard_id,
                        version,
                        relative_payload_path,
                        "payload-inventory",
                        str(exc),
                    )
                )
                continue
            try:
                option_schema = load_option_schema(payload_path.parent, payload_manifest)
            except PackageContractError as exc:
                findings.append(
                    _finding(
                        "PC-OPTIONS",
                        standard_id,
                        version,
                        relative_payload_path,
                        "config-schema",
                        str(exc),
                    )
                )
                continue
            loaded_payloads.append(
                LoadedPayload(
                    manifest=payload_manifest,
                    integrity=integrity,
                    option_schema=option_schema,
                )
            )
        loaded_families.append(LoadedFamily(manifest, tuple(loaded_payloads)))

    if not loaded_families:
        findings.append(
            _finding(
                "PC-NO-FAMILIES",
                "project-standards",
                "",
                "standards",
                "repository",
                "repository contains no loadable V2 package family",
            )
        )

    catalog: CatalogSource | None = None
    if catalog_major is not None:
        catalog_path = root / f"catalogs/{catalog_major}.toml"
        try:
            candidate_catalog = load_catalog_source(catalog_path)
            validate_catalog_source(
                candidate_catalog,
                {family.manifest.standard.id: family.manifest for family in loaded_families},
                {
                    (
                        payload.manifest.payload.standard,
                        payload.manifest.payload.version.value,
                    ): payload.manifest
                    for family in loaded_families
                    for payload in family.payloads
                },
            )
            catalog = candidate_catalog
        except PackageContractError as exc:
            findings.append(
                _finding(
                    "PC-CATALOG-INVALID",
                    "project-standards",
                    "",
                    f"catalogs/{catalog_major}.toml",
                    "catalog",
                    str(exc),
                )
            )

    ordered_families = tuple(
        sorted(loaded_families, key=lambda family: family.manifest.standard.id)
    )
    return PackageRepository(
        root=root,
        families=ordered_families,
        catalog=catalog,
        findings=tuple(sort_findings(findings)),
    )
