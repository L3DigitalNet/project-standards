"""Load-only repository boundary for version-qualified V2 package facts."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

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
    # `None` is reserved for synthetic callers that have no filesystem boundary;
    # `build_package_repository` always supplies a tuple, even when it is empty.
    schema_property_scopes: tuple[SchemaPropertyScope, ...] | None = None


@dataclass(frozen=True, slots=True)
class SchemaPropertyScope:
    """Immutable schema literals from one JSON Schema `properties` scope."""

    resource_path: str
    pointer: str
    property_names: tuple[str, ...]
    standard_id_pinned: bool
    standard_id: str | None
    version_schema_present: bool
    version: str | None
    migration_ids: tuple[str, ...]
    sources: tuple[str, ...]
    targets: tuple[str, ...]
    selectors: tuple[str, ...]
    provider_id: str | None


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


def _literal_values(node: object) -> tuple[str, ...]:
    if not isinstance(node, dict):
        return ()
    mapping = cast("dict[str, object]", node)
    values: list[object] = []
    if "const" in mapping:
        values.append(mapping["const"])
    enum = mapping.get("enum")
    if isinstance(enum, list):
        values.extend(cast("list[object]", enum))
    for keyword in ("anyOf", "oneOf", "allOf"):
        branches = mapping.get(keyword)
        if isinstance(branches, list):
            for branch in cast("list[object]", branches):
                values.extend(_literal_values(branch))
    return tuple(value for value in values if isinstance(value, str))


def _pointer_segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _schema_property_scopes(
    resource_path: str, document: object
) -> tuple[SchemaPropertyScope, ...]:
    scopes: list[SchemaPropertyScope] = []

    def walk(node: object, pointer: str) -> None:
        if isinstance(node, list):
            for index, item in enumerate(cast("list[object]", node)):
                walk(item, f"{pointer}/{index}")
            return
        if not isinstance(node, dict):
            return
        mapping = cast("dict[str, object]", node)
        properties = mapping.get("properties")
        if isinstance(properties, dict):
            property_map = cast("dict[str, object]", properties)
            standard_id_schema = property_map.get("standard_id")
            standard_id_pinned = isinstance(standard_id_schema, dict) and (
                "const" in standard_id_schema
            )
            standard_id_value = (
                cast("dict[str, object]", standard_id_schema).get("const")
                if standard_id_pinned
                else None
            )
            version_schema = property_map.get("version")
            version_value = (
                cast("dict[str, object]", version_schema).get("const")
                if isinstance(version_schema, dict)
                else None
            )
            provider_schema = property_map.get("provider_id")
            provider_value = (
                cast("dict[str, object]", provider_schema).get("const")
                if isinstance(provider_schema, dict)
                else None
            )
            scopes.append(
                SchemaPropertyScope(
                    resource_path=resource_path,
                    pointer=f"{pointer}/properties",
                    property_names=tuple(sorted(property_map)),
                    standard_id_pinned=standard_id_pinned,
                    standard_id=standard_id_value if isinstance(standard_id_value, str) else None,
                    version_schema_present=isinstance(version_schema, dict),
                    version=version_value if isinstance(version_value, str) else None,
                    migration_ids=_literal_values(property_map.get("migration_id")),
                    sources=_literal_values(property_map.get("source")),
                    targets=_literal_values(property_map.get("target")),
                    selectors=_literal_values(property_map.get("selector")),
                    provider_id=provider_value if isinstance(provider_value, str) else None,
                )
            )
        for key, value in mapping.items():
            walk(value, f"{pointer}/{_pointer_segment(key)}")

    walk(document, "")
    return tuple(scopes)


def _load_schema_property_scopes(
    payload_root: Path,
    manifest: PayloadManifest,
    *,
    standard_id: str,
    version: str,
) -> tuple[tuple[SchemaPropertyScope, ...], list[PackageFinding]]:
    scopes: list[SchemaPropertyScope] = []
    findings: list[PackageFinding] = []
    for resource in manifest.resources:
        relative = resource.path.normalized.as_posix()
        if not relative.endswith(".json"):
            continue
        try:
            document = cast(
                "object",
                json.loads((payload_root / relative).read_text(encoding="utf-8")),
            )
        except OSError, UnicodeError, json.JSONDecodeError:
            findings.append(
                _finding(
                    "PC-SCHEMA-JSON",
                    standard_id,
                    version,
                    f"standards/{standard_id}/versions/{version}/{relative}",
                    f"schema:{relative}",
                    "declared JSON schema is not readable valid JSON",
                )
            )
            continue
        scopes.extend(_schema_property_scopes(relative, document))
    return tuple(scopes), findings


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
            schema_property_scopes, schema_findings = _load_schema_property_scopes(
                payload_path.parent,
                payload_manifest,
                standard_id=standard_id,
                version=version,
            )
            findings.extend(schema_findings)
            loaded_payloads.append(
                LoadedPayload(
                    manifest=payload_manifest,
                    integrity=integrity,
                    option_schema=option_schema,
                    schema_property_scopes=schema_property_scopes,
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
