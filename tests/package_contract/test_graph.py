from __future__ import annotations

import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

from project_standards.cli import main
from project_standards.package_contract import graph as package_graph
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
)
from project_standards.package_contract.family import (
    FamilyManifest,
    FamilyStatus,
    StandardIdentity,
    VersionIndexEntry,
)
from project_standards.package_contract.graph import validate_package_graph
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    ContributionDeclaration,
    ExtensionDeclaration,
    ExtensionPathPolicy,
    LegacyStateDeclaration,
    MigrationDeclaration,
    MigrationMode,
    PayloadAvailability,
    PayloadIdentity,
    PayloadManifest,
    ProviderDeclaration,
    ProviderEffect,
    ProviderKind,
    ProviderOperation,
    ProviderPhase,
    RelationDeclaration,
    RelationEvidenceDeclaration,
    RelationEvidenceKind,
    ResourceDeclaration,
    WholeArtifactDeclaration,
)
from project_standards.package_contract.repository import (
    LoadedFamily,
    LoadedPayload,
    PackageRepository,
    SchemaPropertyScope,
    build_package_repository,
)
from tests.package_contract.helpers import (
    assert_schema_payload_references,
    copy_minimal_repository,
    refresh_declared_file_digest,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"
_DIGEST = Sha256Digest("sha256:1ec8d07e07de0defe61804181b75e9139a7d6e9ed8540f677138efa8d2335dcb")
_OTHER_DIGEST = Sha256Digest(
    "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)


def _base_payload() -> LoadedPayload:
    return build_package_repository(_FIXTURE).payloads[0]


def _declare_json_schema(
    repository: Path,
    *,
    resource_id: str,
    relative_path: str,
    content: str,
) -> Path:
    payload_root = repository / "standards/demo/versions/1.2"
    schema_path = payload_root / relative_path
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(content, encoding="utf-8")
    payload_path = payload_root / "payload.toml"
    with payload_path.open("a", encoding="utf-8") as payload_file:
        payload_file.write(
            f'''\n[[resources]]
id = "{resource_id}"
role = "provider-input"
path = "{relative_path}"
media_type = "application/schema+json"
digest = "sha256:{"0" * 64}"
'''
        )
    refresh_declared_file_digest(repository / "standards/demo", relative_path)
    return schema_path


def _schema(properties: dict[str, object]) -> str:
    return json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": properties,
        }
    )


def _manifest(
    standard_id: str,
    *,
    version: str = "1.2",
    relations: RelationDeclaration | None = None,
    artifacts: list[WholeArtifactDeclaration] | None = None,
    contributions: list[ContributionDeclaration] | None = None,
    migrations: list[MigrationDeclaration] | None = None,
) -> PayloadManifest:
    base = _base_payload().manifest
    resolved_relations = relations or RelationDeclaration()
    evidence_pairs = [
        (RelationEvidenceKind.EXTENDS, target) for target in resolved_relations.extends
    ] + [(RelationEvidenceKind.CONFLICTS, target) for target in resolved_relations.conflicts]
    evidence = [
        RelationEvidenceDeclaration(
            kind=kind,
            target=target,
            resource=f"{kind.value}-{target}-adr",
        )
        for kind, target in evidence_pairs
    ]
    evidence_resources = [
        ResourceDeclaration(
            id=item.resource,
            role="relation-evidence",
            path=SafeRelativePath.parse(f"decisions/{item.resource}.md"),
            media_type="text/markdown",
            digest=_DIGEST,
        )
        for item in evidence
    ]
    return base.model_copy(
        update={
            "payload": PayloadIdentity(
                standard=standard_id,
                version=PackageVersion(version),
                availability=base.payload.availability,
            ),
            "relations": resolved_relations,
            "relation_evidence": evidence,
            "resources": [*base.resources, *evidence_resources],
            "artifacts": artifacts or [],
            "contributions": contributions or [],
            "migrations": migrations or [],
        }
    )


def _repository(
    manifests: list[PayloadManifest],
    catalog_entries: list[CatalogPackageEntry] | None = None,
) -> PackageRepository:
    base = _base_payload()
    grouped: dict[str, list[PayloadManifest]] = {}
    for manifest in manifests:
        grouped.setdefault(manifest.payload.standard, []).append(manifest)
    families: list[LoadedFamily] = []
    for standard_id, payloads in grouped.items():
        versions = [
            VersionIndexEntry(
                version=payload.payload.version,
                payload=SafeRelativePath.parse(
                    f"versions/{payload.payload.version.value}/payload.toml"
                ),
                digest=_DIGEST,
            )
            for payload in payloads
        ]
        family = FamilyManifest(
            schema_version="2.0",
            standard=StandardIdentity(
                id=standard_id,
                name=standard_id,
                summary="Synthetic graph fixture",
                status=FamilyStatus.ACTIVE,
            ),
            versions=versions,
        )
        loaded = tuple(
            LoadedPayload(payload, base.integrity, base.option_schema) for payload in payloads
        )
        families.append(LoadedFamily(family, loaded))
    catalog = (
        CatalogSource(schema_version="1.0", catalog_major=5, packages=catalog_entries)
        if catalog_entries is not None
        else None
    )
    return PackageRepository(root=Path(), families=tuple(families), catalog=catalog, findings=())


def _catalog_entry(
    version: str,
    role: CatalogRole,
    standard_id: str = "alpha",
) -> CatalogPackageEntry:
    return CatalogPackageEntry(
        id=standard_id, version=PackageVersion(version), digest=_DIGEST, role=role
    )


def _contribution(
    contribution_id: str,
    scope: str,
    *,
    shared_identity: str | None = None,
    digest: Sha256Digest = _DIGEST,
) -> ContributionDeclaration:
    return ContributionDeclaration(
        id=contribution_id,
        target=SafeRelativePath.parse("pyproject.toml"),
        adapter=AdapterKind.TOML,
        scope=scope,
        policy=ArtifactPolicy.MANAGED,
        source=SafeRelativePath.parse("README.md"),
        source_digest=digest,
        shared_identity=shared_identity,
    )


def _migration(
    migration_id: str,
    from_endpoint: str,
    to_endpoint: str,
    *,
    reversible: bool,
    affected: list[str] | None = None,
) -> MigrationDeclaration:
    return MigrationDeclaration.model_validate(
        {
            "id": migration_id,
            "from": from_endpoint,
            "to": to_endpoint,
            "mode": MigrationMode.MANUAL,
            "instructions": "README.md",
            "reversible": reversible,
            "affected": affected or ["config:*"],
        }
    )


def _automatic_migration(
    migration_id: str,
    from_endpoint: str,
    to_endpoint: str,
    provider: str,
) -> MigrationDeclaration:
    return MigrationDeclaration.model_validate(
        {
            "id": migration_id,
            "from": from_endpoint,
            "to": to_endpoint,
            "mode": MigrationMode.AUTOMATIC,
            "provider": provider,
            "reversible": False,
            "affected": ["config:*"],
        }
    )


def test_builder_backed_graph_reports_stale_schema_literals_in_stable_order(
    tmp_path: Path,
) -> None:
    repository_root = copy_minimal_repository(tmp_path)
    _declare_json_schema(
        repository_root,
        resource_id="stale-references",
        relative_path="schemas/stale-references.schema.json",
        content=_schema(
            {
                "standard_id": {"const": "demo"},
                "version": {"const": "1.1"},
                "migration_id": {"enum": ["missing-b", "missing-a"]},
            }
        ),
    )

    findings = assert_schema_payload_references(build_package_repository(repository_root))

    assert [finding.code for finding in findings] == [
        "PC-SCHEMA-PAYLOAD-REFERENCE",
        "PC-SCHEMA-PAYLOAD-REFERENCE",
    ]
    assert [finding.identity for finding in findings] == [
        "schema:schemas/stale-references.schema.json#/properties/migration_id",
        "schema:schemas/stale-references.schema.json#/properties/version",
    ]
    assert "undeclared migrations ['missing-a', 'missing-b']" in findings[0].message
    assert "payload version 1.2" in findings[1].message


@pytest.mark.parametrize(
    ("resource_id", "relative_path", "document", "identity"),
    [
        pytest.param(
            "provider-input",
            "schemas/provider-input.schema.json",
            _schema(
                {
                    "standard_id": {"const": "demo"},
                    "version": {"const": "1.1"},
                }
            ),
            "schema:schemas/provider-input.schema.json#/properties/version",
            id="provider-input-version-const",
        ),
        pytest.param(
            "migration-report",
            "schemas/migration-report.schema.json",
            json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "package": {
                            "type": "object",
                            "properties": {
                                "standard_id": {"const": "demo"},
                                "version": {"const": "1.1"},
                            },
                        }
                    },
                }
            ),
            ("schema:schemas/migration-report.schema.json#/properties/package/properties/version"),
            id="nested-migration-report-version-const",
        ),
        pytest.param(
            "config-transform-input",
            "schemas/config-transform-input.schema.json",
            json.dumps(
                {
                    "type": "object",
                    "$defs": {
                        "configurationTransform": {
                            "type": "object",
                            "properties": {
                                "migration_id": {"enum": ["upgrade-1-1-to-1-2"]},
                                "source": {"enum": ["package:1.1"]},
                            },
                        }
                    },
                }
            ),
            (
                "schema:schemas/config-transform-input.schema.json"
                "#/$defs/configurationTransform/properties/migration_id"
            ),
            id="configuration-transform-migration-enum",
        ),
    ],
)
def test_graph_rejects_historical_stale_schema_shapes_without_family_wiring(
    tmp_path: Path,
    resource_id: str,
    relative_path: str,
    document: str,
    identity: str,
) -> None:
    repository_root = copy_minimal_repository(tmp_path)
    _declare_json_schema(
        repository_root,
        resource_id=resource_id,
        relative_path=relative_path,
        content=document,
    )

    findings = validate_package_graph(build_package_repository(repository_root))

    assert identity in [finding.identity for finding in findings]


def test_graph_accepts_manifest_declared_predecessor_schema_edges() -> None:
    repository = build_package_repository(
        Path.cwd(),
        family_allowlist={"python-tooling"},
    )

    assert any(
        source.startswith("package:") and source != f"package:{payload.manifest.payload.version}"
        for payload in repository.payloads
        for scope in payload.schema_property_scopes or ()
        for source in scope.sources
    )
    assert not [
        finding
        for finding in validate_package_graph(repository)
        if finding.code == "PC-SCHEMA-PAYLOAD-REFERENCE"
    ]


def test_provider_scoped_schema_literals_must_match_that_providers_edges() -> None:
    manifest = _manifest(
        "alpha",
        migrations=[
            _automatic_migration("edge-a", "package:1.0", "package:1.2", "provider-a"),
            _automatic_migration("edge-b", "package:1.1", "package:1.2", "provider-b"),
        ],
    )
    scope = SchemaPropertyScope(
        resource_path="schemas/config-transform-input.schema.json",
        pointer="/$defs/configurationTransform/properties",
        property_names=("migration_id", "provider_id", "source", "target"),
        standard_id_pinned=False,
        standard_id=None,
        version_schema_present=False,
        version=None,
        migration_ids=("edge-b",),
        sources=("package:1.1",),
        targets=("package:1.2",),
        selectors=(),
        provider_id="provider-a",
    )
    repository = _repository([manifest])
    payload = replace(repository.payloads[0], schema_property_scopes=(scope,))
    repository = replace(
        repository,
        families=(replace(repository.families[0], payloads=(payload,)),),
    )

    findings = [
        finding
        for finding in validate_package_graph(repository)
        if finding.code == "PC-SCHEMA-PAYLOAD-REFERENCE"
    ]

    assert [finding.identity for finding in findings] == [
        (
            "schema:schemas/config-transform-input.schema.json"
            "#/$defs/configurationTransform/properties/migration_id"
        ),
        (
            "schema:schemas/config-transform-input.schema.json"
            "#/$defs/configurationTransform/properties/source"
        ),
    ]
    assert all(
        "does not enumerate provider 'provider-a'" in finding.message for finding in findings
    )


def test_malformed_declared_json_is_a_normalized_finding(tmp_path: Path) -> None:
    repository_root = copy_minimal_repository(tmp_path)
    _declare_json_schema(
        repository_root,
        resource_id="malformed-schema",
        relative_path="schemas/malformed.schema.json",
        content="{",
    )

    repository = build_package_repository(repository_root)

    assert [finding.code for finding in repository.findings] == ["PC-SCHEMA-JSON"]
    assert repository.findings[0].identity == "schema:schemas/malformed.schema.json"
    assert validate_package_graph(repository) == repository.findings


def test_builder_populates_schema_facts_but_synthetic_payloads_may_omit_them() -> None:
    builder_payload = _base_payload()
    synthetic = _repository([_manifest("alpha")])

    assert builder_payload.schema_property_scopes is not None
    assert synthetic.payloads[0].schema_property_scopes is None
    assert validate_package_graph(synthetic) == ()


def test_validate_graph_cli_reports_schema_findings_and_exit_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = copy_minimal_repository(tmp_path)
    _declare_json_schema(
        repository_root,
        resource_id="cli-stale-reference",
        relative_path="schemas/cli-stale-reference.schema.json",
        content=_schema(
            {
                "standard_id": {"const": "demo"},
                "version": {"const": "1.1"},
            }
        ),
    )
    (repository_root / "catalogs/5.toml").unlink()

    exit_code = main(["standards", "validate-graph", "--root", str(repository_root), "--json"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["ok"] is False
    assert [finding["code"] for finding in output["findings"]] == ["PC-SCHEMA-PAYLOAD-REFERENCE"]
    assert [finding["path"] for finding in output["findings"]] == [
        "standards/demo/versions/1.2/schemas/cli-stale-reference.schema.json"
    ]
    assert "must pin payload version 1.2" in output["findings"][0]["message"]


def test_graph_reports_missing_and_self_relation_targets() -> None:
    alpha = _manifest(
        "alpha",
        relations=RelationDeclaration(companions=["missing"], extends=["alpha"]),
    )

    findings = validate_package_graph(_repository([alpha]))

    assert {finding.code for finding in findings} == {
        "PC-RELATION-MISSING",
        "PC-RELATION-SELF",
    }


def test_graph_rejects_extends_cycles() -> None:
    alpha = _manifest("alpha", relations=RelationDeclaration(extends=["beta"]))
    beta = _manifest("beta", relations=RelationDeclaration(extends=["alpha"]))

    findings = validate_package_graph(_repository([beta, alpha]))

    assert [finding.code for finding in findings] == [
        "PC-RELATION-CYCLE",
        "PC-RELATION-CYCLE",
    ]
    assert {finding.version for finding in findings} == {"1.2"}


def test_graph_requires_payload_owned_evidence_for_extends_and_conflicts() -> None:
    alpha = _manifest("alpha", relations=RelationDeclaration(extends=["beta"]))
    alpha = alpha.model_copy(update={"relation_evidence": []})
    beta = _manifest("beta")

    findings = validate_package_graph(_repository([alpha, beta]))

    assert [finding.code for finding in findings] == ["PC-RELATION-EVIDENCE"]


def test_graph_rejects_package_ids_disguised_as_platform_capabilities() -> None:
    alpha = _manifest("alpha")
    beta = _manifest("beta")
    alpha = alpha.model_copy(
        update={
            "capabilities": alpha.capabilities.model_copy(update={"consumes_platform": ["beta"]})
        }
    )

    findings = validate_package_graph(_repository([alpha, beta]))

    assert [finding.code for finding in findings] == ["PC-HIDDEN-REQUIREMENT"]


def test_graph_rejects_cross_package_whole_and_semantic_output_overlap() -> None:
    artifact = WholeArtifactDeclaration(
        id="whole",
        target=SafeRelativePath.parse("pyproject.toml"),
        source=SafeRelativePath.parse("README.md"),
        digest=_DIGEST,
        policy=ArtifactPolicy.MANAGED,
    )
    alpha = _manifest("alpha", artifacts=[artifact])
    beta = _manifest("beta", contributions=[_contribution("ruff", "table:/tool/ruff")])

    findings = validate_package_graph(_repository([alpha, beta]))

    assert [finding.code for finding in findings] == [
        "PC-OUTPUT-OVERLAP",
        "PC-OUTPUT-OVERLAP",
    ]
    assert {finding.standard_id for finding in findings} == {"alpha", "beta"}


def test_graph_rejects_parent_child_scopes_without_shared_precedence() -> None:
    alpha = _manifest("alpha", contributions=[_contribution("tool", "table:/tool")])
    beta = _manifest("beta", contributions=[_contribution("ruff", "table:/tool/ruff")])

    findings = validate_package_graph(_repository([alpha, beta]))

    assert [finding.code for finding in findings] == [
        "PC-OUTPUT-OVERLAP",
        "PC-OUTPUT-OVERLAP",
    ]


def test_identical_shared_identity_is_accepted_but_disagreement_is_rejected() -> None:
    alpha = _manifest(
        "alpha",
        contributions=[_contribution("ruff", "table:/tool/ruff", shared_identity="ruff")],
    )
    matching = _manifest(
        "beta",
        contributions=[_contribution("ruff", "table:/tool/ruff", shared_identity="ruff")],
    )
    mismatch = _manifest(
        "beta",
        contributions=[
            _contribution(
                "ruff",
                "table:/tool/ruff",
                shared_identity="ruff",
                digest=_OTHER_DIGEST,
            )
        ],
    )

    assert validate_package_graph(_repository([alpha, matching])) == ()
    findings = validate_package_graph(_repository([alpha, mismatch]))
    assert [finding.code for finding in findings] == [
        "PC-SHARED-IDENTITY-MISMATCH",
        "PC-SHARED-IDENTITY-MISMATCH",
    ]
    assert {finding.standard_id for finding in findings} == {"alpha", "beta"}


def test_shared_identity_may_evolve_between_versions_of_one_family() -> None:
    alpha_v1 = _manifest(
        "alpha",
        version="1.2",
        contributions=[_contribution("ruff", "table:/tool/ruff", shared_identity="ruff")],
    )
    alpha_v2 = _manifest(
        "alpha",
        version="2.0",
        contributions=[
            _contribution(
                "ruff",
                "table:/tool/ruff",
                shared_identity="ruff",
                digest=_OTHER_DIGEST,
            )
        ],
    )

    assert validate_package_graph(_repository([alpha_v1, alpha_v2])) == ()


def test_graph_rejects_outputs_inside_another_packages_extension_root() -> None:
    alpha = _manifest("alpha").model_copy(
        update={
            "extensions": [
                ExtensionDeclaration(
                    id="custom-input",
                    option="custom_input",
                    media_type="application/toml",
                    path_policy=ExtensionPathPolicy.REPOSITORY_RELATIVE,
                    preferred_root=".standards/extensions/alpha/",
                )
            ]
        }
    )
    artifact = WholeArtifactDeclaration(
        id="intrusion",
        target=SafeRelativePath.parse(".standards/extensions/alpha/generated.toml"),
        source=SafeRelativePath.parse("README.md"),
        digest=_DIGEST,
        policy=ArtifactPolicy.MANAGED,
    )
    beta = _manifest("beta", artifacts=[artifact])

    findings = validate_package_graph(_repository([alpha, beta]))

    assert [finding.code for finding in findings] == [
        "PC-EXTENSION-OUTPUT-OVERLAP",
        "PC-EXTENSION-OUTPUT-OVERLAP",
    ]


def test_graph_rejects_unknown_migration_endpoints_and_affected_identities() -> None:
    migration = _migration(
        "from-missing",
        "package:9.9",
        "package:1.2",
        reversible=False,
        affected=["artifact:missing"],
    )
    alpha = _manifest("alpha", migrations=[migration])

    findings = validate_package_graph(_repository([alpha]))

    assert {finding.code for finding in findings} == {
        "PC-MIGRATION-ENDPOINT",
        "PC-MIGRATION-AFFECTED",
    }


def test_graph_rejects_unregistered_legacy_state_endpoints() -> None:
    migration = _migration(
        "legacy",
        "legacy:v4-alpha",
        "package:1.2",
        reversible=False,
    )
    alpha = _manifest("alpha", migrations=[migration])

    findings = validate_package_graph(_repository([alpha]))

    assert [finding.code for finding in findings] == ["PC-MIGRATION-ENDPOINT"]

    registered = alpha.model_copy(update={"legacy_states": [LegacyStateDeclaration(id="v4-alpha")]})
    assert validate_package_graph(_repository([registered])) == ()


@pytest.mark.parametrize(
    "role",
    [
        pytest.param(CatalogRole.CANDIDATE, id="candidate"),
        pytest.param(CatalogRole.RETAINED, id="retained"),
    ],
)
def test_migration_paths__consumer_role_on_another_major__are_required(
    role: CatalogRole,
) -> None:
    alpha_v1 = _manifest("alpha", version="1.2")
    alpha_v2 = _manifest("alpha", version="2.0")
    repository = _repository(
        [alpha_v1, alpha_v2],
        [
            _catalog_entry("1.2", CatalogRole.DEFAULT),
            _catalog_entry("2.0", role),
        ],
    )

    findings = validate_package_graph(repository)

    assert [finding.code for finding in findings] == [
        "PC-MIGRATION-ENTRY",
        "PC-MIGRATION-EXIT",
    ]


@pytest.mark.parametrize(
    ("role", "availability"),
    [
        pytest.param(
            CatalogRole.INTERNAL,
            PayloadAvailability.INTERNAL,
            id="internal",
        ),
        pytest.param(
            CatalogRole.REFERENCE_ONLY,
            PayloadAvailability.REFERENCE_ONLY,
            id="reference-only",
        ),
    ],
)
def test_migration_paths__nonconsumer_role_on_another_major__are_not_required(
    role: CatalogRole,
    availability: PayloadAvailability,
) -> None:
    alpha_v1 = _manifest("alpha", version="1.2")
    alpha_v2 = _manifest("alpha", version="2.0")
    alpha_v2 = alpha_v2.model_copy(
        update={"payload": alpha_v2.payload.model_copy(update={"availability": availability})}
    )
    repository = _repository(
        [alpha_v1, alpha_v2],
        [
            _catalog_entry("1.2", CatalogRole.DEFAULT),
            _catalog_entry("2.0", role),
        ],
    )

    assert validate_package_graph(repository) == ()


def test_reversible_candidate_migration_supplies_entry_and_exit_paths() -> None:
    alpha_v1 = _manifest("alpha", version="1.2")
    alpha_v2 = _manifest(
        "alpha",
        version="2.0",
        migrations=[
            _migration(
                "candidate",
                "package:1.2",
                "package:2.0",
                reversible=True,
            )
        ],
    )
    repository = _repository(
        [alpha_v1, alpha_v2],
        [
            _catalog_entry("1.2", CatalogRole.DEFAULT),
            _catalog_entry("2.0", CatalogRole.CANDIDATE),
        ],
    )

    assert validate_package_graph(repository) == ()


def test_graph_rechecks_catalog_role_consistency() -> None:
    alpha = _manifest("alpha")
    invalid_catalog = [_catalog_entry("1.2", CatalogRole.INTERNAL)]

    findings = validate_package_graph(_repository([alpha], invalid_catalog))

    assert [finding.code for finding in findings] == ["PC-CATALOG-GRAPH"]


def test_unknown_package_needs_no_shared_code_branch_and_order_is_irrelevant() -> None:
    novel = _manifest("novel-package")
    alpha = _manifest("alpha")
    first = validate_package_graph(_repository([novel, alpha]))
    second = validate_package_graph(_repository([alpha, novel]))

    assert first == second == ()
    assert "novel-package" not in inspect.getsource(package_graph)


def test_graph_is_deterministic_across_all_declaration_orders() -> None:
    first_contribution = _contribution("ruff", "table:/tool/ruff")
    second_contribution = ContributionDeclaration(
        id="editor",
        target=SafeRelativePath.parse(".editorconfig"),
        adapter=AdapterKind.EDITORCONFIG,
        scope="property:$global#root",
        policy=ArtifactPolicy.MANAGED,
        source=SafeRelativePath.parse("README.md"),
        source_digest=_DIGEST,
    )
    providers = [
        ProviderDeclaration(
            id=provider_id,
            operation=ProviderOperation.VALIDATE,
            kind=ProviderKind.DOCUMENTATION_ONLY,
            phase=ProviderPhase.VALIDATE,
            effect=ProviderEffect.FINDINGS,
            resources=[],
        )
        for provider_id in ("z-provider", "a-provider")
    ]
    migrations = [
        _migration("forward", "package:1.2", "package:2.0", reversible=True),
        _migration("legacy", "legacy:v4-alpha", "package:2.0", reversible=False),
    ]
    alpha_v1 = _manifest("alpha", version="1.2")
    alpha_v2 = _manifest(
        "alpha",
        version="2.0",
        contributions=[first_contribution, second_contribution],
        migrations=migrations,
    ).model_copy(
        update={
            "providers": providers,
            "legacy_states": [LegacyStateDeclaration(id="v4-alpha")],
        }
    )
    beta = _manifest("beta")
    reversed_alpha_v2 = alpha_v2.model_copy(
        update={
            "contributions": list(reversed(alpha_v2.contributions)),
            "providers": list(reversed(alpha_v2.providers)),
            "migrations": list(reversed(alpha_v2.migrations)),
            "resources": list(reversed(alpha_v2.resources)),
        }
    )

    forward = validate_package_graph(_repository([beta, alpha_v2, alpha_v1]))
    reverse = validate_package_graph(_repository([alpha_v1, reversed_alpha_v2, beta]))

    assert forward == reverse == ()
