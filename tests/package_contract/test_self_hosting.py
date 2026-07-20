from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path

from jsonschema import Draft202012Validator

from project_standards.package_contract import (
    PackageVersion,
    Sha256Digest,
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
    validate_catalog_source,
)
from project_standards.package_contract.cli import run_standards
from project_standards.package_contract.family import FamilyManifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    ContributionDeclaration,
    ExtensionDeclaration,
    LegacySignatureDeclaration,
    MigrationDeclaration,
    PayloadAvailability,
    PayloadManifest,
    ProviderDeclaration,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from project_standards.package_contract.release import (
    ReleaseClassification,
    ReleasedPayload,
    ReleaseSnapshot,
    ToolVersions,
    classify_catalog_diff,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/standard-bundle-authoring"
_PAYLOAD = _FAMILY / "versions/2.0"
_PAYLOAD_2_2 = _FAMILY / "versions/2.2"
_SPEC = _ROOT / "docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md"
_TEMPLATE_NAMES = {
    "catalog.toml",
    "config.schema.json",
    "contribution.toml",
    "extension.toml",
    "legacy-signature.toml",
    "migration.toml",
    "payload.toml",
    "provider.toml",
    "standard.toml",
}


def test_standard_bundle_authoring_2_2_requires_python_3_14() -> None:
    assert _PAYLOAD_2_2.is_dir()
    documents = (
        (_PAYLOAD_2_2 / "README.md").read_text(encoding="utf-8"),
        (_PAYLOAD_2_2 / "agent-summary.md").read_text(encoding="utf-8"),
        _SPEC.read_text(encoding="utf-8"),
    )

    for document in documents:
        assert "consumer-side Python" in document
        assert "Python 3.14" in document


def test_standard_bundle_authoring_2_2_declares_artifact_mode_contract() -> None:
    assert _PAYLOAD_2_2.is_dir()
    documents = (
        (_PAYLOAD_2_2 / "README.md").read_text(encoding="utf-8"),
        (_PAYLOAD_2_2 / "agent-summary.md").read_text(encoding="utf-8"),
        _SPEC.read_text(encoding="utf-8"),
    )

    for document in documents:
        assert "declared artifact mode" in document
        assert "consumer contract" in document
        assert "source-tree executable bits" in document


def _isolated_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    family = root / "standards/standard-bundle-authoring"
    shutil.copytree(_FAMILY, family)
    manifest = load_payload_manifest(family / "versions/2.0/payload.toml")
    integrity = validate_payload_integrity(family / "versions/2.0", manifest)
    template = (family / "versions/2.0/templates/standard.toml").read_text(encoding="utf-8")
    family_index = (
        template.replace("example-standard", "standard-bundle-authoring")
        .replace("Example Standard", "Standard Bundle Authoring")
        .replace(
            "One sentence describing the stable package family.",
            "The internal contract for immutable standard packages and catalog publication.",
        )
        .replace('status = "draft"', 'status = "active"')
        .replace('version = "1.0"', 'version = "2.0"')
        .replace("versions/1.0/payload.toml", "versions/2.0/payload.toml")
        .replace(
            "sha256:0000000000000000000000000000000000000000000000000000000000000000",
            integrity.aggregate_digest.value,
        )
    )
    (family / "standard.toml").write_text(family_index, encoding="utf-8")
    return root


def test_authoring_v2_self_hosts_one_internal_payload(tmp_path: Path) -> None:
    root = _isolated_repository(tmp_path)
    repository = build_package_repository(
        root,
        family_allowlist=frozenset({"standard-bundle-authoring"}),
    )

    assert validate_package_repository(repository) == ()
    assert len(repository.families) == 1
    family = repository.families[0]
    assert family.manifest.standard.id == "standard-bundle-authoring"
    assert [entry.version.value for entry in family.manifest.versions] == ["2.0"]
    assert len(family.payloads) == 1

    payload = family.payloads[0]
    assert payload.manifest.payload.availability is PayloadAvailability.INTERNAL
    assert payload.manifest.artifacts == []
    assert payload.manifest.contributions == []
    assert payload.manifest.extensions == []
    assert payload.manifest.migrations == []
    assert payload.manifest.legacy_signatures == []
    assert payload.manifest.providers == []


def test_authoring_v2_payload_contains_closed_options_and_all_templates() -> None:
    assert _PAYLOAD.is_dir()
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    resources = {resource.path.original: resource for resource in manifest.resources}

    assert {resource.role for resource in manifest.resources} >= {
        "canonical-standard",
        "agent-summary",
        "config-schema",
        "family-template",
        "payload-template",
        "catalog-template",
        "provider-template",
        "contribution-template",
        "extension-template",
        "migration-template",
        "legacy-signature-template",
    }
    assert {path.name for path in (_PAYLOAD / "templates").iterdir()} == _TEMPLATE_NAMES
    assert set(resources) >= {
        "README.md",
        "agent-summary.md",
        "config.schema.json",
        *(f"templates/{name}" for name in _TEMPLATE_NAMES),
    }

    option_schema = json.loads((_PAYLOAD / "config.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(option_schema)
    assert option_schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {},
    }


def test_authoring_templates_are_strict_v2_copy_starts() -> None:
    templates = _PAYLOAD / "templates"
    assert (_FAMILY / "templates/standard.toml").read_bytes() == (
        templates / "standard.toml"
    ).read_bytes()
    family = tomllib.loads((templates / "standard.toml").read_text(encoding="utf-8"))
    payload = tomllib.loads((templates / "payload.toml").read_text(encoding="utf-8"))
    catalog = tomllib.loads((templates / "catalog.toml").read_text(encoding="utf-8"))
    provider = tomllib.loads((templates / "provider.toml").read_text(encoding="utf-8"))
    contribution = tomllib.loads((templates / "contribution.toml").read_text(encoding="utf-8"))
    extension = tomllib.loads((templates / "extension.toml").read_text(encoding="utf-8"))
    migration = tomllib.loads((templates / "migration.toml").read_text(encoding="utf-8"))
    signature = tomllib.loads((templates / "legacy-signature.toml").read_text(encoding="utf-8"))

    assert family["schema_version"] == "2.0"
    assert set(family) == {"schema_version", "standard", "versions"}
    FamilyManifest.model_validate(family)
    assert payload["schema_version"] == "1.0"
    assert payload["payload"]["availability"] in {"consumer", "reference-only", "internal"}
    PayloadManifest.model_validate(payload)
    assert catalog["schema_version"] == "1.0"
    assert set(catalog["packages"][0]) == {"id", "version", "digest", "role"}
    CatalogSource.model_validate(catalog)
    assert provider["providers"][0]["entrypoint"].startswith("payload:")
    assert {
        (item["operation"], item["phase"], item["effect"]) for item in provider["providers"]
    } >= {
        ("render", "plan", "content"),
        ("migrate", "plan", "migration-report"),
        ("semantic-review", "validate", "findings"),
    }
    for declaration in provider["providers"]:
        ProviderDeclaration.model_validate(declaration)
    assert {"id", "target", "adapter", "scope", "policy"} <= set(contribution["contributions"][0])
    for declaration in contribution["contributions"]:
        ContributionDeclaration.model_validate(declaration)
    assert extension["extensions"][0]["path_policy"] == "repository-relative"
    ExtensionDeclaration.model_validate(extension["extensions"][0])
    assert migration["migrations"][0]["from"].startswith(("package:", "legacy:"))
    for declaration in migration["migrations"]:
        MigrationDeclaration.model_validate(declaration)
    assert signature["legacy_signatures"][0]["known_content_digests"]
    LegacySignatureDeclaration.model_validate(signature["legacy_signatures"][0])

    schema_template = json.loads((templates / "config.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema_template)
    assert schema_template["additionalProperties"] is False
    assert schema_template["properties"][extension["extensions"][0]["option"]]["type"] == "string"


def test_authoring_surfaces_bound_consumer_owned_preservation() -> None:
    guide = (_PAYLOAD / "README.md").read_text(encoding="utf-8")
    template = (_PAYLOAD / "templates/legacy-signature.toml").read_text(encoding="utf-8")

    assert "exact package-history bytes through `known_content_digests`" in guide
    assert "ownership-acquiring, locking, or destructive transition" in guide
    assert "single-target whole-file signature" in guide
    assert "`consumer_owned_intent_pointer`" in guide
    assert "literal `consumer-owned` value through that pointer" in guide
    assert "never adds observed bytes to package history" in guide
    assert '# kind = "whole-file"' in template
    assert '# targets = [".github/workflows/check.yml"]' in template
    assert '# consumer_owned_intent_pointer = "/example_standard/workflow_ownership"' in template
    assert 'supply literal "consumer-owned" through that pointer' in template


def test_authoring_surfaces_bounded_takeover_preservation() -> None:
    payload = _FAMILY / "versions/2.3"
    guide = (payload / "README.md").read_text(encoding="utf-8")
    template = (payload / "templates/legacy-signature.toml").read_text(encoding="utf-8")

    assert "every byte-version each supported release actually shipped" in guide
    assert '`unknown_content_disposition = "preserve"`' in guide
    assert "mutually exclusive with `consumer_owned_intent_pointer`" in guide
    assert "`CP-MIGRATION-BOUNDED-TAKEOVER` warning" in guide
    assert "no whole-file declaration materializes" in guide
    assert '# unknown_content_disposition = "preserve"' in template
    assert "Mutually exclusive with consumer_owned_intent_pointer" in template


def test_authoring_workflow_validates_indexes_catalogs_and_projects(tmp_path: Path) -> None:
    assert _PAYLOAD.is_dir()
    root = _isolated_repository(tmp_path)
    repository = build_package_repository(
        root,
        family_allowlist=frozenset({"standard-bundle-authoring"}),
    )
    assert validate_package_repository(repository) == ()
    assert run_standards(["validate-packages", "--root", str(root)]) == 0
    family = repository.families[0]
    payload = family.payloads[0]

    integrity = validate_payload_integrity(
        _PAYLOAD,
        payload.manifest,
        expected_digest=family.manifest.versions[0].digest,
    )
    catalog = CatalogSource(
        schema_version="1.0",
        catalog_major=5,
        packages=[
            CatalogPackageEntry(
                id="standard-bundle-authoring",
                version=PackageVersion("2.0"),
                digest=integrity.aggregate_digest,
                role=CatalogRole.INTERNAL,
            )
        ],
    )
    assert (
        validate_catalog_source(
            catalog,
            repository.family_map,
            repository.payload_map,
        )
        == catalog
    )

    (root / "src/project_standards").mkdir(parents=True)
    assert sync_payload_projection(root, check=False) == ()
    assert sync_payload_projection(root, check=True) == ()
    projected = root / "src/project_standards/payloads/standard-bundle-authoring/2.0"
    assert projected.is_dir()
    assert all(path.is_symlink() for path in projected.rglob("*") if path.is_file())


def test_authoring_payload_is_byte_identical_in_the_built_wheel(tmp_path: Path) -> None:
    assert _PAYLOAD.is_dir()
    project = _isolated_repository(tmp_path)
    package = project / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """[project]
name = "project-standards"
version = "5.0.0"
requires-python = ">=3.14"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**"]
""",
        encoding="utf-8",
    )
    assert sync_payload_projection(project, check=False) == ()
    distribution = project / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(distribution)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (wheel,) = distribution.glob("*.whl")
    prefix = "project_standards/payloads/standard-bundle-authoring/2.0/"
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
    source_files = {
        path.relative_to(_PAYLOAD).as_posix(): path.read_bytes()
        for path in _PAYLOAD.rglob("*")
        if path.is_file()
    }
    assert wheel_files == source_files


def test_authoring_payload_participates_in_immutable_baseline_checks(tmp_path: Path) -> None:
    root = _isolated_repository(tmp_path)
    repository = build_package_repository(
        root,
        family_allowlist=frozenset({"standard-bundle-authoring"}),
    )
    family = repository.families[0]
    payload = family.payloads[0]
    entry = CatalogPackageEntry(
        id="standard-bundle-authoring",
        version=PackageVersion("2.0"),
        digest=payload.integrity.aggregate_digest,
        role=CatalogRole.INTERNAL,
    )
    catalog = CatalogSource(schema_version="1.0", catalog_major=5, packages=[entry])
    released = ReleasedPayload(
        standard_id="standard-bundle-authoring",
        version=payload.manifest.payload.version,
        aggregate_digest=payload.integrity.aggregate_digest,
        files=payload.integrity.inventory,
    )
    baseline = ReleaseSnapshot(catalog=catalog, payloads=(released,))

    unchanged = classify_catalog_diff(
        baseline,
        baseline,
        ToolVersions(previous="5.0.0", current="5.0.1"),
    )
    assert unchanged.classification is ReleaseClassification.PATCH

    mutated = ReleasedPayload(
        standard_id=released.standard_id,
        version=released.version,
        aggregate_digest=Sha256Digest(
            "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        ),
        files=released.files,
    )
    rejected = classify_catalog_diff(
        baseline,
        ReleaseSnapshot(catalog=catalog, payloads=(mutated,)),
        ToolVersions(previous="5.0.0", current="5.0.1"),
    )
    assert rejected.classification is ReleaseClassification.FORBIDDEN
    assert {finding.code for finding in rejected.findings} >= {"PC-RELEASE-PAYLOAD-MUTATED"}
