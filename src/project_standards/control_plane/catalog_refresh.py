"""Plan same-major installed catalog refreshes without repository writes.

This boundary validates tool/catalog lineage and package-release policy before
ordinary reconciliation is allowed to resolve against installed payload facts.
It returns only catalog identities and selection changes; repository bytes stay
owned by the planner and executor.
"""

from __future__ import annotations

from dataclasses import dataclass

from project_standards.control_plane.codec import render_catalog
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import ParsedToolRelease
from project_standards.control_plane.models import (
    CatalogChannel,
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
)
from project_standards.control_plane.resolution import (
    consumer_versions,
    select_catalog_version,
)
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
)
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.release import (
    ReleaseClassification,
    ReleasedPayload,
    ReleaseSnapshot,
    ToolVersions,
    classify_catalog_diff,
)

CATALOG_REFRESH_BACKUP = ".catalog-refresh.previous.toml"


@dataclass(frozen=True, slots=True)
class CatalogLineage:
    """Identify one canonical consumer catalog without retaining its bytes."""

    catalog: str
    release: str
    digest: Sha256Digest


@dataclass(frozen=True, slots=True)
class CatalogSelectionChange:
    """Describe one enabled package selection changed by catalog refresh."""

    standard_id: str
    previous: PackageVersion | None
    current: PackageVersion


@dataclass(frozen=True, slots=True)
class CatalogRefreshPlan:
    """Carry validated refresh lineage and executor-private catalog snapshots."""

    changed: bool
    before: CatalogLineage
    after: CatalogLineage
    classification: ReleaseClassification
    affected_selections: tuple[CatalogSelectionChange, ...]
    committed: ConsumerCatalog
    installed: ConsumerCatalog


def _lineage(catalog: ConsumerCatalog) -> CatalogLineage:
    header = catalog.project_standards
    return CatalogLineage(header.catalog.value, header.release, header.digest)


def _role(channel: CatalogChannel) -> CatalogRole:
    return {
        CatalogChannel.STABLE: CatalogRole.DEFAULT,
        CatalogChannel.RETAINED: CatalogRole.RETAINED,
        CatalogChannel.CANDIDATE: CatalogRole.CANDIDATE,
        CatalogChannel.REFERENCE_ONLY: CatalogRole.REFERENCE_ONLY,
        CatalogChannel.INTERNAL: CatalogRole.INTERNAL,
    }[channel]


def _release_snapshot(catalog: ConsumerCatalog) -> ReleaseSnapshot:
    entries: list[CatalogPackageEntry] = []
    payloads: list[ReleasedPayload] = []
    for standard_id, standard in catalog.standards.items():
        for version in standard.available:
            catalog_version = standard.versions[version.value]
            entries.append(
                CatalogPackageEntry(
                    id=standard_id,
                    version=version,
                    digest=catalog_version.payload_digest,
                    role=_role(catalog_version.channel),
                )
            )
            # Consumer catalogs retain the immutable aggregate identity but not
            # the underlying inventory. InstalledDistribution verifies those
            # bytes before this pure catalog-policy boundary is called.
            payloads.append(
                ReleasedPayload(
                    standard_id=standard_id,
                    version=version,
                    aggregate_digest=catalog_version.payload_digest,
                    files=(),
                )
            )
    return ReleaseSnapshot(
        catalog=CatalogSource(
            schema_version="1.0",
            catalog_major=catalog.project_standards.catalog.major,
            packages=entries,
        ),
        payloads=tuple(payloads),
    )


def _selection_changes(
    installed: ConsumerCatalog,
    desired: DesiredConfig,
    lock: CentralLock,
) -> tuple[CatalogSelectionChange, ...]:
    changes: list[CatalogSelectionChange] = []
    for standard_id, desired_package in desired.standards.items():
        standard = installed.standards.get(standard_id)
        if standard is None:
            raise ControlPlaneError(
                f"desired standard is unavailable after catalog refresh: {standard_id}"
            )
        selected, _target_major = select_catalog_version(
            standard_id,
            desired_package,
            standard,
            lock.accepted_tracks.get(standard_id),
            set(),
        )
        if not desired_package.enabled:
            continue
        previous = lock.standards.get(standard_id)
        previous_version = previous.resolved if previous is not None else None
        if (
            isinstance(desired_package.version, str)
            and previous_version is not None
            and previous_version.major == selected.major
            and selected.sort_key < previous_version.sort_key
        ):
            raise ControlPlaneError(
                f"catalog refresh would downgrade the selected package: {standard_id}"
            )
        if previous_version != selected:
            changes.append(CatalogSelectionChange(standard_id, previous_version, selected))

    # Tracks survive disablement and even an absent desired record. Validate
    # every retained authorization so publishing a new catalog cannot strand it.
    for standard_id, track in lock.accepted_tracks.items():
        standard = installed.standards.get(standard_id)
        if standard is None or not consumer_versions(standard, track.major):
            raise ControlPlaneError(
                f"accepted major {track.major} is unavailable after catalog refresh: {standard_id}"
            )
    return tuple(sorted(changes, key=lambda item: item.standard_id))


def _validate_lineage(
    committed: ConsumerCatalog,
    installed: ConsumerCatalog,
    desired: DesiredConfig,
    lock: CentralLock,
) -> tuple[bytes, bytes, ParsedToolRelease, ParsedToolRelease]:
    committed_bytes = render_catalog(committed)
    installed_bytes = render_catalog(installed)
    committed_header = committed.project_standards
    installed_header = installed.project_standards
    lock_header = lock.project_standards
    if desired.project_standards.catalog != committed_header.catalog:
        raise ControlPlaneError("desired and committed catalog majors do not match")
    if (
        lock_header.catalog != committed_header.catalog
        or lock_header.release != committed_header.release
        or lock_header.catalog_digest != committed_header.digest
    ):
        raise ControlPlaneError("central lock does not match the committed catalog lineage")
    if installed_header.catalog != committed_header.catalog:
        raise ControlPlaneError("installed and committed catalog majors do not match")
    previous_release = ParsedToolRelease(committed_header.release)
    current_release = ParsedToolRelease(installed_header.release)
    if current_release.sort_key < previous_release.sort_key:
        raise ControlPlaneError("installed catalog release is older than the committed catalog")
    if current_release.sort_key == previous_release.sort_key and installed_bytes != committed_bytes:
        raise ControlPlaneError("catalog changed but its tool release did not advance")
    return committed_bytes, installed_bytes, previous_release, current_release


def plan_catalog_refresh(
    committed: ConsumerCatalog,
    installed: ConsumerCatalog,
    desired: DesiredConfig,
    lock: CentralLock,
) -> CatalogRefreshPlan:
    """Validate and describe one installed same-major catalog refresh.

    Invalid release lineage, incompatible catalog changes, and selections that
    the installed snapshot cannot honor raise before any repository plan exists.
    """
    committed_bytes, installed_bytes, previous_release, current_release = _validate_lineage(
        committed,
        installed,
        desired,
        lock,
    )
    changes = _selection_changes(installed, desired, lock)
    if installed_bytes == committed_bytes:
        classification = ReleaseClassification.PATCH
    else:
        diff = classify_catalog_diff(
            _release_snapshot(committed),
            _release_snapshot(installed),
            ToolVersions(previous_release.value, current_release.value),
        )
        if diff.classification in {
            ReleaseClassification.MAJOR,
            ReleaseClassification.FORBIDDEN,
        }:
            codes = ", ".join(finding.code for finding in diff.findings) or "major change"
            raise ControlPlaneError(f"catalog refresh violates package release policy: {codes}")
        classification = diff.classification
    return CatalogRefreshPlan(
        changed=installed_bytes != committed_bytes,
        before=_lineage(committed),
        after=_lineage(installed),
        classification=classification,
        affected_selections=changes,
        committed=committed,
        installed=installed,
    )
