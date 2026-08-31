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

# These two constants move on different commits, and swapping one early turns this
# module red for a reason unrelated to the change under test.
#
# `_BASELINE_REF` is the released catalog the staged activation is measured
# against. It moves in the commit that stages a new activation, because
# `_activation_targets` derives successors as "in the current catalog, absent from
# the baseline" and then requires exactly one per family — leaving it behind after a
# second activation is staged makes two generations of the same family collide as
# `assert len(targets) == len(successors)`.
#
# `_RELEASE_VERSION` is the release literal, asserted against `pyproject.toml`,
# `uv.lock`, both `.standards/` release fields, and the dated CHANGELOG heading. It
# moves only in the release commit that bumps those files; `scripts/release_prep.py`
# reports this file in its version-reference sweep for exactly that reason.
_BASELINE_REF = "v5.26.0"
_RELEASE_VERSION = "5.27.0"


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
    assert repository.catalog is not None
    current = {(entry.id, entry.version.value) for entry in repository.catalog.packages}
    successors = [
        payload
        for family in repository.families
        for payload in family.payloads
        if (
            payload.manifest.payload.standard,
            payload.manifest.payload.version.value,
        )
        not in baseline
        and (
            payload.manifest.payload.standard,
            payload.manifest.payload.version.value,
        )
        in current
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


def test_catalog_activation__staged_successors__become_canonical_rows() -> None:
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
            indexed.version.value: indexed.digest
            for indexed in family.manifest.versions
            if (standard_id, indexed.version.value) in entries
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
            indexed.version.value: indexed.digest
            for indexed in family.manifest.versions
            if (standard_id, indexed.version.value) in entries
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
    entries = _catalog_entries(repository)
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
        expected_versions = [
            indexed.version
            for indexed in family.manifest.versions
            if (standard_id, indexed.version.value) in entries
        ]
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


def test_catalog_activation__github_workflow_1_8__is_current_and_records_transport_boundary() -> (
    None
):
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = [
        (package["version"], package["role"])
        for package in catalog["packages"]
        if package["id"] == "github-workflow"
    ]
    assert roles == [
        ("1.0", "retained"),
        ("1.1", "retained"),
        ("1.2", "retained"),
        ("1.3", "retained"),
        ("1.4", "retained"),
        ("1.5", "retained"),
        ("1.6", "retained"),
        ("1.7", "retained"),
        ("1.8", "default"),
    ]

    consumer_catalog = tomllib.loads(
        (_ROOT / ".standards/catalog.toml").read_text(encoding="utf-8")
    )
    selection = consumer_catalog["standards"]["github-workflow"]
    assert selection["available"] == [
        "1.0",
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "1.5",
        "1.6",
        "1.7",
        "1.8",
    ]
    assert selection["default"] == "1.8"

    consumer_lock = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    assert consumer_lock["standards"]["github-workflow"]["resolved"] == "1.8"

    current_references = {
        "standards/github-workflow/README.md": "versions/1.8/README.md",
        "standards/github-workflow/adopt.md": "versions/1.8/adopt.md",
        "standards/github-workflow/agent-summary.md": "versions/1.8/agent-summary.md",
        "standards/README.md": "| 1.8 | default | [github-workflow/]",
    }
    for relative, expected in current_references.items():
        assert expected in (_ROOT / relative).read_text(encoding="utf-8")

    # The transport boundary was established by 1.2 and its CHANGELOG line is
    # immutable history, so this still reads the 1.2 entry: no successor has changed
    # the transport, and re-asserting the claim under a later heading would demand a
    # CHANGELOG entry that does not exist until the release commit.
    changelog_entry = next(
        line
        for line in (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("- **GitHub Workflow 1.2")
    )
    assert "MCP-first proposal is retired" in changelog_entry
    assert "`gh`-issued-token, REST-only boundary" in changelog_entry
    assert "no MCP read or mutation path" in changelog_entry
    assert "no `issue_read` body-escaping procedure" in changelog_entry


def test_catalog_activation__managed_root_configuration__preserves_effective_gates() -> None:
    markdownlint = json.loads((_ROOT / ".markdownlint.json").read_text(encoding="utf-8"))
    desired = tomllib.loads((_ROOT / ".standards/config.toml").read_text(encoding="utf-8"))

    assert markdownlint["MD060"] is False
    assert desired["standards"]["python-tooling"]["config"]["ci"] == {"performance": True}


def test_catalog_activation__repository__remains_package_contract_valid() -> None:
    repository = _repository()

    assert validate_package_repository(repository) == ()
