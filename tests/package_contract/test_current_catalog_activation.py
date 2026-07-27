from __future__ import annotations

import json
import re
import tomllib
from functools import cache
from pathlib import Path

from project_standards.control_plane.codec import parse_catalog
from project_standards.package_contract import (
    PackageRepository,
    validate_package_repository,
)
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    render_consumer_catalog,
)
from project_standards.package_contract.payload import PayloadAvailability
from project_standards.package_contract.projection import (
    plan_payload_projection,
    sync_payload_projection,
)
from project_standards.package_contract.release import load_git_release_snapshot
from project_standards.package_contract.release_consistency import (
    validate_release_consistency,
)
from project_standards.package_contract.repository import (
    LoadedFamily,
    LoadedPayload,
    build_package_repository,
)
from project_standards.standards_graph import StandardsGraph, render_catalog

_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_REF = "v5.8.0"
_RELEASE_VERSION = "5.9.0"


def _repository() -> PackageRepository:
    repository = build_package_repository(_ROOT, catalog_major=5)
    assert repository.findings == ()
    assert repository.catalog is not None
    return repository


def _family(repository: PackageRepository, standard_id: str) -> LoadedFamily:
    return next(
        family for family in repository.families if family.manifest.standard.id == standard_id
    )


def _activation_targets(repository: PackageRepository) -> dict[str, LoadedPayload]:
    baseline = _baseline_catalog_identities()
    successors = [
        payload
        for family in repository.families
        for payload in family.payloads
        if (
            payload.manifest.payload.standard,
            payload.manifest.payload.version.value,
        )
        not in baseline
    ]
    targets = {payload.manifest.payload.standard: payload for payload in successors}
    assert len(targets) == len(successors)
    return targets


@cache
def _baseline_catalog_identities() -> frozenset[tuple[str, str]]:
    return frozenset((entry.id, entry.version.value) for entry in _baseline_catalog_entries())


@cache
def _baseline_catalog_entries() -> tuple[CatalogPackageEntry, ...]:
    snapshot = load_git_release_snapshot(_ROOT, _BASELINE_REF, 5)
    return tuple(snapshot.catalog.packages)


def _activation_ids(
    targets: dict[str, LoadedPayload],
    availability: PayloadAvailability,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            standard_id
            for standard_id, payload in targets.items()
            if payload.manifest.payload.availability is availability
        )
    )


def _catalog_entries(
    repository: PackageRepository,
) -> dict[tuple[str, str], CatalogPackageEntry]:
    assert repository.catalog is not None
    return {(entry.id, entry.version.value): entry for entry in repository.catalog.packages}


def _target_role(payload: LoadedPayload) -> CatalogRole:
    availability = payload.manifest.payload.availability
    if availability is PayloadAvailability.CONSUMER:
        return CatalogRole.DEFAULT
    assert availability is PayloadAvailability.INTERNAL
    return CatalogRole.INTERNAL


def test_catalog_activation__five_staged_successors__become_canonical_rows() -> None:
    repository = _repository()
    targets = _activation_targets(repository)
    entries = _catalog_entries(repository)
    consumer_ids = set(_activation_ids(targets, PayloadAvailability.CONSUMER))
    expected = {
        (
            entry.id,
            entry.version.value,
            (
                CatalogRole.RETAINED
                if entry.id in consumer_ids and entry.role is CatalogRole.DEFAULT
                else entry.role
            ),
            entry.digest,
        )
        for entry in _baseline_catalog_entries()
    }
    expected.update(
        (
            standard_id,
            payload.manifest.payload.version.value,
            _target_role(payload),
            payload.integrity.aggregate_digest,
        )
        for standard_id, payload in targets.items()
    )
    actual = {
        (entry.id, entry.version.value, entry.role, entry.digest) for entry in entries.values()
    }

    assert actual == expected


def test_catalog_activation__consumer_predecessors__remain_retained_with_family_digests() -> None:
    repository = _repository()
    targets = _activation_targets(repository)
    entries = _catalog_entries(repository)

    for standard_id in _activation_ids(targets, PayloadAvailability.CONSUMER):
        family = _family(repository, standard_id)
        target_version = targets[standard_id].manifest.payload.version
        expected_versions = {
            indexed.version.value: indexed.digest for indexed in family.manifest.versions
        }
        actual = {
            version: entry
            for (entry_id, version), entry in entries.items()
            if entry_id == standard_id
        }

        assert set(actual) == set(expected_versions), standard_id
        assert actual[target_version.value].role is CatalogRole.DEFAULT, standard_id
        assert all(
            entry.role is CatalogRole.RETAINED and entry.digest == expected_versions[version]
            for version, entry in actual.items()
            if version != target_version.value
        ), standard_id


def test_catalog_activation__internal_family__keeps_every_indexed_version_internal() -> None:
    repository = _repository()
    targets = _activation_targets(repository)
    entries = _catalog_entries(repository)

    for standard_id in _activation_ids(targets, PayloadAvailability.INTERNAL):
        family = _family(repository, standard_id)
        expected_versions = {
            indexed.version.value: indexed.digest for indexed in family.manifest.versions
        }
        actual = {
            version: entry
            for (entry_id, version), entry in entries.items()
            if entry_id == standard_id
        }

        assert targets[standard_id].manifest.payload.version.value == max(
            expected_versions,
            key=lambda value: next(
                indexed.version.sort_key
                for indexed in family.manifest.versions
                if indexed.version.value == value
            ),
        )
        assert set(actual) == set(expected_versions), standard_id
        assert all(
            entry.role is CatalogRole.INTERNAL and entry.digest == expected_versions[version]
            for version, entry in actual.items()
        ), standard_id


def test_catalog_activation__internal_exact_versions__stay_visible_but_not_selectable() -> None:
    repository = _repository()
    targets = _activation_targets(repository)
    assert repository.catalog is not None
    catalog = parse_catalog(
        render_consumer_catalog(
            repository.catalog,
            repository.family_map,
            repository.payload_map,
            tool_release=_RELEASE_VERSION,
        )
    )

    for standard_id in _activation_ids(targets, PayloadAvailability.INTERNAL):
        family = _family(repository, standard_id)
        expected_versions = [indexed.version for indexed in family.manifest.versions]
        standard = catalog.standards[standard_id]

        assert standard.available == expected_versions
        assert standard.default is None
        assert standard.candidates == []
        assert all(
            standard.versions[version.value].availability is PayloadAvailability.INTERNAL
            and standard.versions[version.value].channel.value == "internal"
            for version in expected_versions
        )


def test_catalog_activation__candidate_references__match_derived_current_versions() -> None:
    repository = _repository()

    assert (
        validate_release_consistency(
            _ROOT,
            repository,
            distribution_version=_RELEASE_VERSION,
        )
        == ()
    )


def test_catalog_activation__human_catalog__renders_candidate_roles() -> None:
    repository = _repository()
    targets = _activation_targets(repository)
    graph = StandardsGraph(
        root=_ROOT,
        standards=(),
        missing_manifest_dirs=(),
        package_repository=repository,
    )
    rendered = render_catalog(graph)

    assert (_ROOT / "standards/catalog.md").read_text(encoding="utf-8") == rendered
    for standard_id, payload in targets.items():
        family = _family(repository, standard_id)
        identity = payload.manifest.payload
        expected_prefix = (
            f"| [`{standard_id}`]({standard_id}/README.md) | "
            f"{family.manifest.standard.status.value} | {identity.version.value} | "
            f"{_target_role(payload).value} | {identity.availability.value} |"
        )
        assert expected_prefix in rendered


def test_catalog_activation__consumer_catalog_projection__selects_derived_defaults() -> None:
    repository = _repository()
    targets = _activation_targets(repository)
    assert repository.catalog is not None
    expected = render_consumer_catalog(
        repository.catalog,
        repository.family_map,
        repository.payload_map,
        tool_release=_RELEASE_VERSION,
    )
    actual_path = _ROOT / ".standards/catalog.toml"
    actual = parse_catalog(actual_path.read_bytes())

    assert actual_path.read_bytes() == expected
    for standard_id in _activation_ids(targets, PayloadAvailability.CONSUMER):
        assert (
            actual.standards[standard_id].default == targets[standard_id].manifest.payload.version
        )


def test_catalog_activation__canonical_payload_projection__stays_relative_and_current() -> None:
    assert sync_payload_projection(_ROOT, check=True) == ()
    for link in plan_payload_projection(_ROOT).links:
        assert link.destination.is_symlink()
        assert not link.destination.readlink().is_absolute()
        assert link.destination.resolve(strict=True).read_bytes() == link.source.read_bytes()


def test_catalog_activation__release_metadata__uses_one_exact_version() -> None:
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((_ROOT / "uv.lock").read_text(encoding="utf-8"))
    consumer_catalog = tomllib.loads(
        (_ROOT / ".standards/catalog.toml").read_text(encoding="utf-8")
    )
    consumer_lock = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    project_lock = next(
        package for package in lock["package"] if package["name"] == pyproject["project"]["name"]
    )
    observed = {
        "pyproject.toml": pyproject["project"]["version"],
        "uv.lock": project_lock["version"],
        ".standards/catalog.toml": consumer_catalog["project_standards"]["release"],
        ".standards/lock.toml": consumer_lock["project_standards"]["release"],
    }

    assert observed == dict.fromkeys(observed, _RELEASE_VERSION)


def test_catalog_activation__release_changelog__has_dated_candidate_section() -> None:
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert re.search(
        rf"^## \[{re.escape(_RELEASE_VERSION)}\] — \d{{4}}-\d{{2}}-\d{{2}}$",
        changelog,
        flags=re.MULTILINE,
    )


def test_catalog_activation__managed_root_configuration__preserves_effective_gates() -> None:
    markdownlint = json.loads((_ROOT / ".markdownlint.json").read_text(encoding="utf-8"))
    desired = tomllib.loads((_ROOT / ".standards/config.toml").read_text(encoding="utf-8"))

    assert markdownlint["MD060"] is False
    assert desired["standards"]["python-tooling"]["config"]["ci"] == {"performance": True}


def test_catalog_activation__repository__remains_package_contract_valid() -> None:
    repository = _repository()

    assert validate_package_repository(repository) == ()
