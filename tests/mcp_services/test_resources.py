"""Resource integrity, construction fail-closed, and installed/source parity.

Covers TC-T2-002 (construction aborts on any invalid element; reads recheck
declaration/containment/digest), TC-T2-003's parity half (installed and source
construction expose equivalent stably ordered facts), and TC-T2-007 (resource
descriptors preserve every declared field behind a canonical four-segment URI).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.package_contract.repository import build_package_repository
from tests.mcp_services.helpers import (
    FULL_FIXTURE,
    build_installed_tree,
    build_source_tree,
    import_mcp_services,
)

_TOOL_RELEASE = "5.1.0"

# Representative invalid-element classes across catalog positions: corrupt
# payload bytes in the first and last selected payloads, invalid family
# metadata, and a catalog entry disagreeing with its family index digest. Each
# must abort construction entirely — no partial catalog (§5.5 from_installed).
_INSTALLED_CORRUPTIONS: list[tuple[str, str, str]] = [
    ("first-payload-bytes", "payloads/alpha/1.0/README.md", "append"),
    ("last-payload-bytes", "payloads/gamma/1.0/workflow.yml", "append"),
    ("middle-payload-bytes", "payloads/beta/1.0/agent-summary.md", "append"),
    ("family-metadata", "families/alpha/standard.toml", "break-toml"),
    ("catalog-digest-disagreement", "catalogs/5.toml", "flip-digest"),
]


def _corrupt(installed: Path, target: str, mode: str) -> None:
    path = installed / target
    if mode == "append":
        path.write_bytes(path.read_bytes() + b"tampered\n")
    elif mode == "break-toml":
        path.write_text(
            path.read_text(encoding="utf-8").replace('status = "active"', 'status = "bogus"'),
            encoding="utf-8",
        )
    else:
        text = path.read_text(encoding="utf-8")
        first_digest = text.index("sha256:")
        flipped = "0" if text[first_digest + 7] != "0" else "1"
        path.write_text(
            text[: first_digest + 7] + flipped + text[first_digest + 8 :], encoding="utf-8"
        )


@pytest.mark.parametrize(
    ("label", "target", "mode"),
    _INSTALLED_CORRUPTIONS,
    ids=[label for label, _, _ in _INSTALLED_CORRUPTIONS],
)
def test_facade_rejects_any_invalid_installed_payload_at_construction(
    tmp_path: Path, label: str, target: str, mode: str
) -> None:
    services = import_mcp_services()

    installed = build_installed_tree(tmp_path)
    _corrupt(installed, target, mode)
    with pytest.raises(services.ServiceError) as installed_error:
        services.McpServiceFacade.from_installed(
            InstalledDistribution(installed, tool_release=_TOOL_RELEASE), CatalogMajor("5")
        )
    error = installed_error.value
    assert error.code == "catalog-invalid"
    assert error.severity == "error"
    assert error.message
    assert error.remediation

    # Source construction accepts only an already validated repository: load
    # findings, a missing catalog, and a generation mismatch each fail closed.
    source_tree = build_source_tree(tmp_path / "source")
    tampered = source_tree / "standards/beta/versions/1.0/agent-summary.md"
    tampered.write_bytes(tampered.read_bytes() + b"tampered\n")
    with_findings = build_package_repository(source_tree, catalog_major=5)
    assert with_findings.findings
    with pytest.raises(services.ServiceError) as findings_error:
        services.McpServiceFacade.from_source(with_findings, CatalogMajor("5"))
    assert findings_error.value.code == "catalog-invalid"

    valid = build_package_repository(FULL_FIXTURE, catalog_major=5)
    without_catalog = build_package_repository(FULL_FIXTURE)
    with pytest.raises(services.ServiceError):
        services.McpServiceFacade.from_source(without_catalog, CatalogMajor("5"))
    with pytest.raises(services.ServiceError):
        services.McpServiceFacade.from_source(valid, CatalogMajor("6"))


def test_resource_read_rechecks_declaration_containment_and_digest(
    tmp_path: Path,
) -> None:
    services = import_mcp_services()
    installed = build_installed_tree(tmp_path)
    facade = services.McpServiceFacade.from_installed(
        InstalledDistribution(installed, tool_release=_TOOL_RELEASE), CatalogMajor("5")
    )
    payload_file = installed / "payloads/alpha/2.0/README.md"
    original = payload_file.read_bytes()

    content = facade.resource("alpha", "2.0", "readme")
    assert type(content.data) is bytes
    assert content.data == original
    declared_readme = next(
        resource
        for resource in facade.standard("alpha", "2.0").resources
        if resource.resource_id == "readme"
    )
    assert content.descriptor == declared_readme
    assert content.descriptor.resource_id == "readme"
    assert content.descriptor.uri == "standards://alpha/2.0/resources/readme"
    assert content.descriptor.digest == f"sha256:{hashlib.sha256(original).hexdigest()}"

    # Only declared resource IDs are addressable; path-shaped inputs — declared
    # relative paths, absolute paths, traversal — are never accepted (FR-006).
    for rejected in ("does-not-exist", "README.md", "/etc/passwd", "../../etc/passwd", ""):
        with pytest.raises(services.ServiceError) as undeclared:
            facade.resource("alpha", "2.0", rejected)
        assert undeclared.value.code == "resource-not-found"
    with pytest.raises(services.ServiceError) as unknown_version:
        facade.resource("alpha", "9.9", "readme")
    assert unknown_version.value.code == "standard-not-found"

    # The digest recheck runs on every read against current bytes, after the
    # eager startup validation and regardless of any earlier successful read.
    payload_file.write_bytes(original + b"drift\n")
    with pytest.raises(services.ServiceError) as drifted:
        facade.resource("alpha", "2.0", "readme")
    error = drifted.value
    assert error.code == "resource-integrity"
    assert error.standard_id == "alpha"
    assert error.version == "2.0"
    assert error.path == "README.md"
    assert error.severity == "error"
    assert error.message
    assert error.remediation
    payload_file.write_bytes(original)
    assert facade.resource("alpha", "2.0", "readme").data == original

    # Containment: a symlinked resource is rejected even when the target bytes
    # would satisfy the digest, because bytes must come from inside the payload.
    outside = tmp_path / "outside-copy.md"
    outside.write_bytes(original)
    payload_file.unlink()
    payload_file.symlink_to(outside)
    with pytest.raises(services.ServiceError) as escaped:
        facade.resource("alpha", "2.0", "readme")
    assert escaped.value.code == "resource-integrity"

    # A FIFO swapped in for the resource must fail closed without hanging the
    # read — the facade checks the object it actually opened, not the pathname.
    payload_file.unlink()
    os.mkfifo(payload_file)
    with pytest.raises(services.ServiceError) as swapped:
        facade.resource("alpha", "2.0", "readme")
    assert swapped.value.code == "resource-integrity"

    payload_file.unlink()
    with pytest.raises(services.ServiceError) as missing:
        facade.resource("alpha", "2.0", "readme")
    assert missing.value.code == "resource-integrity"


def test_source_and_installed_facades_are_equivalent_and_stably_ordered(
    tmp_path: Path,
) -> None:
    services = import_mcp_services()
    installed_facade = services.McpServiceFacade.from_installed(
        InstalledDistribution(build_installed_tree(tmp_path), tool_release=_TOOL_RELEASE),
        CatalogMajor("5"),
    )
    source_facade = services.McpServiceFacade.from_source(
        build_package_repository(FULL_FIXTURE, catalog_major=5), CatalogMajor("5")
    )

    # Equivalent bytes must expose identical stable facts through either
    # construction path (NFR-010): same DTO values, same stable ordering by the
    # documented explicit key (resource/provider IDs, DR-009).
    installed_catalog = installed_facade.catalog()
    assert installed_catalog == source_facade.catalog()
    for descriptor in installed_catalog.standards:
        assert [resource.resource_id for resource in descriptor.resources] == sorted(
            resource.resource_id for resource in descriptor.resources
        )
        assert [provider.provider_id for provider in descriptor.providers] == sorted(
            provider.provider_id for provider in descriptor.providers
        )
        for resource in descriptor.resources:
            installed_read = installed_facade.resource(
                descriptor.standard_id, descriptor.package_version, resource.resource_id
            )
            source_read = source_facade.resource(
                descriptor.standard_id, descriptor.package_version, resource.resource_id
            )
            assert installed_read == source_read
            assert type(installed_read.data) is bytes


def test_resource_descriptor_preserves_declared_fields(tmp_path: Path) -> None:
    services = import_mcp_services()
    facade = services.McpServiceFacade.from_installed(
        InstalledDistribution(build_installed_tree(tmp_path), tool_release=_TOOL_RELEASE),
        CatalogMajor("5"),
    )

    # The V2 payload declarations are the oracle: every descriptor preserves the
    # declared identity fields exactly and adds only the canonical URI.
    oracle = build_package_repository(FULL_FIXTURE, catalog_major=5)
    for (standard_id, version), manifest in oracle.payload_map.items():
        descriptor = facade.standard(standard_id, version)
        declared = {declaration.id: declaration for declaration in manifest.resources}
        assert {resource.resource_id for resource in descriptor.resources} == set(declared)
        for resource in descriptor.resources:
            declaration = declared[resource.resource_id]
            assert resource.uri == (
                f"standards://{standard_id}/{version}/resources/{resource.resource_id}"
            )
            assert resource.standard_id == standard_id
            assert resource.package_version == version
            assert resource.role == declaration.role
            assert resource.media_type == declaration.media_type
            assert resource.digest == declaration.digest.value
