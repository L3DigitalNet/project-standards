"""Exact package-resource services behind the SDK-free facade (T2, §5.5).

The facade composes the existing authoritative boundaries — installed
construction goes through ``InstalledDistribution.load_catalog``, which eagerly
validates every selected family, payload declaration, payload byte, and
aggregate digest; source construction accepts an already validated
``PackageRepository``. Both paths feed one mapper, so equivalent bytes expose
identical stable facts (NFR-010) and no parallel package semantics exist
(FR-015). Only immutable catalog/descriptor facts are cached on an instance;
resource bytes are re-verified on every read and never cached.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_services.models import (
    CatalogDescriptor,
    ProviderDescriptor,
    RelationshipSet,
    ResourceContent,
    ResourceDescriptor,
    ServiceError,
    StandardDescriptor,
)
from project_standards.package_contract.catalog import CatalogSource
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import FamilyManifest
from project_standards.package_contract.payload import PayloadManifest, ResourceDeclaration
from project_standards.package_contract.repository import PackageRepository

_CONSTRUCTION_REMEDIATION = (
    "repair or reinstall the standards distribution and rebuild the facade; "
    "no partial catalog is served"
)
_LOOKUP_REMEDIATION = "list the installed catalog and use a declared ID and exact version"
_INTEGRITY_REMEDIATION = (
    "reinstall the standards distribution; resource bytes must match their "
    "declared digest from inside the payload"
)


@dataclass(frozen=True, slots=True)
class _PayloadSource:
    """One validated payload manifest bound to its resolved on-disk root."""

    manifest: PayloadManifest
    root: Path


@dataclass(frozen=True, slots=True)
class _StandardEntry:
    """Immutable per-version facade state: descriptor plus read-time facts.

    This is the single owner of all cached facts for one exact version — the
    mapped descriptor, the per-resource descriptor index, the declarations that
    drive read-time verification, and the resolved payload root. Resource bytes
    are deliberately absent: only re-verifiable filesystem reads produce them.
    """

    descriptor: StandardDescriptor
    payload_root: Path
    declarations: dict[str, ResourceDeclaration]
    resource_descriptors: dict[str, ResourceDescriptor]


def _resolved_payload_root(root: Path, standard_id: str, version: str, *, boundary: Path) -> Path:
    """Resolve one payload root and require it to stay inside its distribution.

    ``boundary`` is the resolved distribution/repository root; a payload root
    whose resolution escapes it (an ancestor symlink pointing elsewhere) would
    silently move the trusted containment anchor, so it aborts construction.
    """
    try:
        if root.is_symlink() or not root.is_dir():
            raise PackageContractError("payload root is not a regular directory")
        resolved = root.resolve(strict=True)
        if not resolved.is_relative_to(boundary):
            raise PackageContractError("payload root escapes its distribution boundary")
        return resolved
    except OSError as exc:
        raise ServiceError(
            code="catalog-invalid",
            message=f"payload directory for {standard_id} {version} could not be resolved",
            remediation=_CONSTRUCTION_REMEDIATION,
            standard_id=standard_id,
            version=version,
        ) from exc
    except PackageContractError as exc:
        raise ServiceError(
            code="catalog-invalid",
            message=f"payload directory for {standard_id} {version} is not a regular directory",
            remediation=_CONSTRUCTION_REMEDIATION,
            standard_id=standard_id,
            version=version,
        ) from exc


def _standard_descriptor(
    family: FamilyManifest,
    manifest: PayloadManifest,
) -> StandardDescriptor:
    standard_id = manifest.payload.standard
    version = manifest.payload.version.value
    resources = tuple(
        ResourceDescriptor(
            uri=f"standards://{standard_id}/{version}/resources/{declaration.id}",
            resource_id=declaration.id,
            role=declaration.role,
            media_type=declaration.media_type,
            digest=declaration.digest.value,
            standard_id=standard_id,
            package_version=version,
        )
        for declaration in sorted(manifest.resources, key=lambda item: item.id)
    )
    providers = tuple(
        ProviderDescriptor(
            provider_id=declaration.id,
            operation=declaration.operation.value,
            kind=declaration.kind.value,
            phase=declaration.phase.value,
            effect=declaration.effect.value,
        )
        for declaration in sorted(manifest.providers, key=lambda item: item.id)
    )
    return StandardDescriptor(
        standard_id=standard_id,
        title=family.standard.name,
        status=family.standard.status.value,
        package_version=version,
        exposure=manifest.payload.availability.value,
        capabilities=tuple(manifest.capabilities.provides),
        relationships=RelationshipSet(
            companions=tuple(manifest.relations.companions),
            extends=tuple(manifest.relations.extends),
            conflicts=tuple(manifest.relations.conflicts),
        ),
        resources=resources,
        providers=providers,
    )


def _build_entries(
    source: CatalogSource,
    families: dict[str, FamilyManifest],
    payloads: dict[tuple[str, str], _PayloadSource],
    boundary: Path,
) -> dict[tuple[str, str], _StandardEntry]:
    entries: dict[tuple[str, str], _StandardEntry] = {}
    for entry in source.packages:
        key = (entry.id, entry.version.value)
        family = families.get(entry.id)
        payload = payloads.get(key)
        if family is None or payload is None:
            raise ServiceError(
                code="catalog-invalid",
                message=f"catalog entry {entry.id} {entry.version.value} has no validated payload",
                remediation=_CONSTRUCTION_REMEDIATION,
                standard_id=entry.id,
                version=entry.version.value,
            )
        descriptor = _standard_descriptor(family, payload.manifest)
        entries[key] = _StandardEntry(
            descriptor=descriptor,
            payload_root=_resolved_payload_root(
                payload.root, entry.id, entry.version.value, boundary=boundary
            ),
            declarations={
                declaration.id: declaration for declaration in payload.manifest.resources
            },
            resource_descriptors={item.resource_id: item for item in descriptor.resources},
        )
    return entries


class McpServiceFacade:
    """Typed, SDK-independent service facade over validated package facts.

    T2 supplies construction and the exact package/resource reads; consumer
    inspection, reconciliation, and provider dispatch are added by later tasks
    behind this same class (§5.5 frozen interface table).
    """

    def __init__(
        self,
        *,
        catalog: CatalogDescriptor,
        entries: dict[tuple[str, str], _StandardEntry],
    ) -> None:
        self._catalog = catalog
        self._entries = entries

    @classmethod
    def from_installed(
        cls,
        distribution: InstalledDistribution,
        catalog: CatalogMajor,
    ) -> McpServiceFacade:
        """Build production state from one eagerly validated installed catalog."""
        try:
            installed = distribution.load_catalog(catalog)
        except PackageContractError as exc:
            # The distribution boundary raises one unstructured message per
            # failure; per-item identity is not available in structured form,
            # so the §5.5 "affected standard when applicable" fields stay unset.
            raise ServiceError(
                code="catalog-invalid",
                message=f"installed catalog {catalog.value} failed validation: {exc}",
                remediation=_CONSTRUCTION_REMEDIATION,
            ) from exc
        payloads = {
            (payload.manifest.payload.standard, payload.manifest.payload.version.value): (
                _PayloadSource(manifest=payload.manifest, root=payload.root)
            )
            for payload in installed.payloads
        }
        return cls._from_validated(
            installed.source, installed.family_map, payloads, distribution.package_root
        )

    @classmethod
    def from_source(
        cls,
        repository: PackageRepository,
        catalog: CatalogMajor,
    ) -> McpServiceFacade:
        """Build development/test state from an already validated repository."""
        if repository.findings:
            # Findings are pre-sorted by the repository loader, so surfacing the
            # first one keeps the structured identity fields deterministic.
            first = repository.findings[0]
            raise ServiceError(
                code="catalog-invalid",
                message=(
                    f"source repository reports {len(repository.findings)} package load "
                    f"findings; first: {first.code}: {first.message}"
                ),
                remediation=_CONSTRUCTION_REMEDIATION,
                standard_id=first.standard_id or None,
                version=first.version or None,
                path=first.path or None,
            )
        if repository.catalog is None or repository.catalog.catalog_major != catalog.major:
            raise ServiceError(
                code="catalog-invalid",
                message=f"source repository does not carry validated catalog {catalog.value}",
                remediation=_CONSTRUCTION_REMEDIATION,
            )
        try:
            repository_root = repository.root.resolve(strict=True)
        except OSError as exc:
            raise ServiceError(
                code="catalog-invalid",
                message="source repository root could not be resolved",
                remediation=_CONSTRUCTION_REMEDIATION,
            ) from exc
        payloads: dict[tuple[str, str], _PayloadSource] = {}
        for family in repository.families:
            # Not layout guessing: VersionIndexEntry pins every payload to the
            # canonical standards/{id}/versions/{version}/ shape, and discovery
            # accepts family indexes only at standards/{id}/standard.toml.
            family_root = repository_root / "standards" / family.manifest.standard.id
            for payload in family.payloads:
                identity = payload.manifest.payload
                payloads[(identity.standard, identity.version.value)] = _PayloadSource(
                    manifest=payload.manifest,
                    root=family_root / "versions" / identity.version.value,
                )
        return cls._from_validated(
            repository.catalog, repository.family_map, payloads, repository_root
        )

    @classmethod
    def _from_validated(
        cls,
        source: CatalogSource,
        families: dict[str, FamilyManifest],
        payloads: dict[tuple[str, str], _PayloadSource],
        boundary: Path,
    ) -> McpServiceFacade:
        entries = _build_entries(source, families, payloads, boundary)
        descriptor = CatalogDescriptor(
            catalog_major=source.catalog_major,
            standards=tuple(
                entries[(entry.id, entry.version.value)].descriptor for entry in source.packages
            ),
        )
        return cls(catalog=descriptor, entries=entries)

    def catalog(self) -> CatalogDescriptor:
        """Return the immutable generation-qualified catalog descriptor."""
        return self._catalog

    def standard(self, standard_id: str, version: str) -> StandardDescriptor:
        """Return one exact V2-derived descriptor or a structured not-found."""
        return self._entry(standard_id, version).descriptor

    def resource(self, standard_id: str, version: str, resource_id: str) -> ResourceContent:
        """Return one declared resource after re-verifying it end to end.

        Every read rechecks the selected declaration, the contained path, and
        the current byte digest — cached descriptor facts never stand in for
        the bytes, so post-startup tampering always fails closed (FR-006).
        """
        entry = self._entry(standard_id, version)
        declaration = entry.declarations.get(resource_id)
        if declaration is None:
            raise ServiceError(
                code="resource-not-found",
                message=f"{standard_id} {version} declares no resource {resource_id!r}",
                remediation=_LOOKUP_REMEDIATION,
                standard_id=standard_id,
                version=version,
            )
        data = self._verified_bytes(entry, declaration, standard_id, version)
        return ResourceContent(descriptor=entry.resource_descriptors[resource_id], data=data)

    def _entry(self, standard_id: str, version: str) -> _StandardEntry:
        entry = self._entries.get((standard_id, version))
        if entry is None:
            raise ServiceError(
                code="standard-not-found",
                message=f"catalog {self._catalog.catalog_major} does not declare "
                f"{standard_id} {version}",
                remediation=_LOOKUP_REMEDIATION,
                standard_id=standard_id,
                version=version,
            )
        return entry

    def _verified_bytes(
        self,
        entry: _StandardEntry,
        declaration: ResourceDeclaration,
        standard_id: str,
        version: str,
    ) -> bytes:
        relative = declaration.path.normalized
        target = entry.payload_root / relative

        def _integrity_error(reason: str) -> ServiceError:
            return ServiceError(
                code="resource-integrity",
                message=f"resource {declaration.id!r} of {standard_id} {version} {reason}",
                remediation=_INTEGRITY_REMEDIATION,
                standard_id=standard_id,
                version=version,
                path=relative.as_posix(),
            )

        try:
            if target.is_symlink():
                raise _integrity_error("is a symlink; bytes must live inside the payload")
            resolved = target.resolve(strict=True)
            if not resolved.is_relative_to(entry.payload_root):
                raise _integrity_error("escapes its payload directory")
            # Check and read the same open object: O_NOFOLLOW rejects a symlink
            # swapped in after the checks above, O_NONBLOCK keeps a swapped-in
            # FIFO from hanging the open, and fstat on the descriptor — not the
            # pathname — proves the thing actually being read is a regular file.
            descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise _integrity_error("is not a regular file")
                with open(descriptor, "rb", closefd=False) as stream:
                    data = stream.read()
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise _integrity_error("could not be read from the payload") from exc
        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
        if digest != declaration.digest.value:
            raise _integrity_error("bytes do not match the declared digest")
        return data
