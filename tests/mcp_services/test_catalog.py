"""Catalog and descriptor behavior of the SDK-free facade over V2 package facts.

Covers TC-T2-001 (generation distinctness and explicit ordering), TC-T2-003's
cached-read half (validated catalog reuse without repository scanning),
TC-T2-005 (V2 descriptor facts), and TC-T2-006 (exact relationship semantics).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from project_standards.control_plane.distribution import InstalledCatalog, InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.package_contract.repository import build_package_repository
from tests.mcp_services.helpers import FULL_FIXTURE, build_installed_tree, import_mcp_services

_TOOL_RELEASE_5 = "5.1.0"
_TOOL_RELEASE_6 = "6.0.0"


def test_catalog_generation_and_package_order_are_explicit(tmp_path: Path) -> None:
    services = import_mcp_services()
    installed = build_installed_tree(tmp_path, alternate_major=6)

    facade_5 = services.McpServiceFacade.from_installed(
        InstalledDistribution(installed, tool_release=_TOOL_RELEASE_5), CatalogMajor("5")
    )
    facade_6 = services.McpServiceFacade.from_installed(
        InstalledDistribution(installed, tool_release=_TOOL_RELEASE_6), CatalogMajor("6")
    )

    catalog_5 = facade_5.catalog()
    catalog_6 = facade_6.catalog()
    assert catalog_5.catalog_major == 5
    assert catalog_6.catalog_major == 6
    assert [
        (descriptor.standard_id, descriptor.package_version) for descriptor in catalog_5.standards
    ] == [
        ("alpha", "1.0"),
        ("alpha", "2.0"),
        ("alpha", "3.0"),
        ("beta", "1.0"),
        ("gamma", "1.0"),
    ]

    # The alternate generation declares fewer packages, so a facade that merges
    # generations, aliases one onto the other, or restamps the requested major
    # onto Catalog 5 fails these exact ordered projections.
    assert [
        (descriptor.standard_id, descriptor.package_version) for descriptor in catalog_6.standards
    ] == [
        ("alpha", "2.0"),
        ("alpha", "3.0"),
        ("gamma", "1.0"),
    ]
    assert catalog_5 != catalog_6
    with pytest.raises(services.ServiceError):
        facade_6.standard("beta", "1.0")

    # Collections are immutable: the catalog exposes tuples, and descriptor
    # fields reject assignment instead of drifting after construction.
    first_standard = catalog_5.standards[0]
    assert isinstance(catalog_5.standards, tuple)
    with pytest.raises(Exception, match="frozen"):
        first_standard.standard_id = "hijacked"

    # Exact-version lookup accepts declared versions and rejects everything else
    # with a structured, fully populated not-found failure — never fuzzy
    # resolution.
    assert facade_5.standard("alpha", "2.0").package_version == "2.0"
    with pytest.raises(services.ServiceError) as unknown_version:
        facade_5.standard("alpha", "9.9")
    error = unknown_version.value
    assert error.code == "standard-not-found"
    assert error.standard_id == "alpha"
    assert error.version == "9.9"
    assert error.severity == "error"
    assert error.message
    assert error.remediation
    with pytest.raises(services.ServiceError) as unknown_standard:
        facade_5.standard("delta", "1.0")
    assert unknown_standard.value.code == "standard-not-found"


def test_common_installed_reads_reuse_validated_catalog_without_repo_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    services = import_mcp_services()
    installed = build_installed_tree(tmp_path)

    # The installed catalog authority must be entered exactly once, at
    # construction: package facts never come from ad-hoc file parsing (FR-015)
    # and never require a second validation pass per read (NFR-007).
    load_calls: list[str] = []
    original = InstalledDistribution.load_catalog

    def _spy(
        self: InstalledDistribution,
        catalog: CatalogMajor | str,
        *,
        recorded_release: str | None = None,
    ) -> InstalledCatalog:
        load_calls.append(str(catalog))
        return original(self, catalog, recorded_release=recorded_release)

    monkeypatch.setattr(InstalledDistribution, "load_catalog", _spy)
    facade = services.McpServiceFacade.from_installed(
        InstalledDistribution(installed, tool_release=_TOOL_RELEASE_5), CatalogMajor("5")
    )
    assert len(load_calls) == 1
    first = facade.catalog()

    # Removing the installed tree proves two invariants at once: catalog and
    # descriptor reads serve immutable validated facts without re-scanning the
    # filesystem, while resource reads never serve cached bytes that would
    # bypass the per-read declaration/containment/digest recheck.
    shutil.rmtree(installed)

    assert facade.catalog() == first
    assert facade.standard("alpha", "2.0").standard_id == "alpha"
    assert len(load_calls) == 1
    with pytest.raises(services.ServiceError) as blocked:
        facade.resource("alpha", "2.0", "readme")
    assert blocked.value.code == "resource-integrity"


def test_descriptor_uses_v2_package_facts(tmp_path: Path) -> None:
    services = import_mcp_services()
    installed = build_installed_tree(tmp_path)
    facade = services.McpServiceFacade.from_installed(
        InstalledDistribution(installed, tool_release=_TOOL_RELEASE_5), CatalogMajor("5")
    )

    alpha = facade.standard("alpha", "2.0")
    assert alpha.standard_id == "alpha"
    assert alpha.title == "Alpha"
    assert alpha.status == "active"
    assert alpha.package_version == "2.0"
    assert alpha.exposure == "consumer"
    assert alpha.capabilities == ("alpha.render", "alpha.validate")
    assert [
        (provider.provider_id, provider.operation, provider.kind, provider.phase, provider.effect)
        for provider in alpha.providers
    ] == [
        ("migrate-alpha", "migrate", "python", "plan", "migration-report"),
        ("render-alpha", "render", "python", "plan", "content"),
    ]
    assert {resource.resource_id for resource in alpha.resources} == {
        "readme",
        "agent-summary",
        "config-schema",
        "adopt",
        "provider-code",
        "provider-input",
        "provider-output",
        "relation-beta",
        "migration-guide",
        "legacy-reference",
    }

    # Exposure and lifecycle status come from validated V2 payload/family facts,
    # never from catalog prose or directory naming.
    beta = facade.standard("beta", "1.0")
    assert (beta.exposure, beta.status, beta.title) == ("reference-only", "active", "Beta")
    gamma = facade.standard("gamma", "1.0")
    assert (gamma.exposure, gamma.status, gamma.title) == ("internal", "review", "Gamma")

    # Every descriptor of every catalog entry maps its own validated manifest:
    # the V2 source declarations are an independent per-payload oracle, so one
    # payload's facts copied across descriptors cannot pass.
    oracle = build_package_repository(FULL_FIXTURE, catalog_major=5)
    families = oracle.family_map
    for (standard_id, version), manifest in oracle.payload_map.items():
        descriptor = facade.standard(standard_id, version)
        family = families[standard_id]
        assert descriptor.title == family.standard.name
        assert descriptor.status == family.standard.status.value
        assert descriptor.exposure == manifest.payload.availability.value
        assert descriptor.capabilities == tuple(manifest.capabilities.provides)
        assert [
            (provider.provider_id, provider.operation, provider.kind, provider.effect)
            for provider in descriptor.providers
        ] == [
            (declared.id, declared.operation.value, declared.kind.value, declared.effect.value)
            for declared in sorted(manifest.providers, key=lambda item: item.id)
        ]
        assert {resource.resource_id for resource in descriptor.resources} == {
            declared.id for declared in manifest.resources
        }

    # The catalog embeds the same descriptor values instead of a parallel model.
    catalog = facade.catalog()
    embedded = {
        (descriptor.standard_id, descriptor.package_version): descriptor
        for descriptor in catalog.standards
    }
    assert embedded[("alpha", "2.0")] == alpha
    assert embedded[("gamma", "1.0")] == gamma


def test_provider_descriptors_preserve_declared_execution_contract(tmp_path: Path) -> None:
    """TC-T13-001: descriptors preserve the full declared execution contract.

    FULL_FIXTURE only declares executable (``kind="python"``) providers — see
    notes.md T13.1 for the absent documentation-only counterpart — so this
    proves the executable mapping is exact and never re-derived: entrypoint,
    both schema references, and the resource set must equal the already
    validated ``ProviderDeclaration`` facts field-by-field, with deterministic
    (sorted unique) resource ordering.
    """
    services = import_mcp_services()
    installed = build_installed_tree(tmp_path)
    facade = services.McpServiceFacade.from_installed(
        InstalledDistribution(installed, tool_release=_TOOL_RELEASE_5), CatalogMajor("5")
    )

    oracle = build_package_repository(FULL_FIXTURE, catalog_major=5)
    checked_providers = 0
    for (standard_id, version), manifest in oracle.payload_map.items():
        descriptor = facade.standard(standard_id, version)
        by_id = {provider.provider_id: provider for provider in descriptor.providers}
        for declared in manifest.providers:
            mapped = by_id[declared.id]
            assert mapped.entrypoint == declared.entrypoint
            assert mapped.input_schema == declared.input_schema
            assert mapped.output_schema == declared.output_schema
            assert mapped.resources == tuple(sorted(declared.resources))
            assert isinstance(mapped.resources, tuple)
            checked_providers += 1

    # alpha 2.0 declares render-alpha and migrate-alpha; alpha 3.0 declares
    # migrate-alpha. If the fixture stops declaring any provider this count
    # silently drops to zero and the loop above proves nothing.
    assert checked_providers == 3


def test_relationships_preserve_v2_declarations_and_empty_independence(
    tmp_path: Path,
) -> None:
    services = import_mcp_services()
    installed = build_installed_tree(tmp_path)
    facade = services.McpServiceFacade.from_installed(
        InstalledDistribution(installed, tool_release=_TOOL_RELEASE_5), CatalogMajor("5")
    )

    declared = facade.standard("alpha", "2.0").relationships
    assert declared.companions == ("gamma",)
    assert declared.extends == ("beta",)
    assert declared.conflicts == ()

    # Independence is the empty default: nothing is inferred from naming, shared
    # capabilities, catalog adjacency, or migration lineage — alpha 3.0 declares
    # a migration from 2.0 yet must stay relation-free.
    for standard_id, version in (
        ("alpha", "1.0"),
        ("alpha", "3.0"),
        ("beta", "1.0"),
        ("gamma", "1.0"),
    ):
        relationships = facade.standard(standard_id, version).relationships
        assert relationships.companions == ()
        assert relationships.extends == ()
        assert relationships.conflicts == ()
