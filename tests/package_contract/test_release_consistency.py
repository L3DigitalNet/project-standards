from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from project_standards.package_contract import (
    PackageFinding,
    PackageRepository,
    build_package_repository,
    finding_sort_key,
)
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
    render_consumer_catalog,
)
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.release_consistency import (
    validate_release_consistency,
)
from project_standards.standards_graph import StandardsGraph, render_catalog

_ROOT = Path(__file__).resolve().parents[2]
_PAYLOAD_TEMPLATE = (
    _ROOT / "tests/fixtures/package_contract/valid/minimal/standards/demo/versions/1.2"
)
_DISTRIBUTION_VERSION = "9.4.0"
_HISTORICAL_MARKER = "<!-- release-consistency: historical project-spec -->"
_INVENTORY_MARKER = "<!-- release-consistency: inventory standard-bundle-authoring catalog -->"
_LIVE_SHALLOW_FAMILY_CORPUS = {
    "standards/adr/README.md",
    "standards/adr/adopt.md",
    "standards/adr/agent-summary.md",
    "standards/agent-handoff/README.md",
    "standards/agent-handoff/adopt.md",
    "standards/agent-handoff/agent-summary.md",
    "standards/cli-documentation/README.md",
    "standards/cli-documentation/adopt.md",
    "standards/cli-documentation/agent-summary.md",
    "standards/markdown-frontmatter/README.md",
    "standards/markdown-frontmatter/adopt.md",
    "standards/markdown-frontmatter/agent-summary.md",
    "standards/markdown-frontmatter/field-values.md",
    "standards/markdown-frontmatter/structure.md",
    "standards/markdown-tooling/README.md",
    "standards/markdown-tooling/adopt.md",
    "standards/markdown-tooling/agent-summary.md",
    "standards/project-spec/README.md",
    "standards/project-spec/adopt.md",
    "standards/project-spec/agent-summary.md",
    "standards/python-coding/README.md",
    "standards/python-coding/agent-summary.md",
    "standards/python-tooling/README.md",
    "standards/python-tooling/adopt.md",
    "standards/python-tooling/agent-summary.md",
    "standards/python-tooling/build-backend.md",
    "standards/standard-bundle-authoring/README.md",
    "standards/standard-bundle-authoring/agent-summary.md",
}


@dataclass(frozen=True, slots=True)
class ReleaseConsistencyFixture:
    root: Path
    repository: PackageRepository
    distribution_version: str
    default_version: str
    internal_version: str

    def validate(self) -> tuple[PackageFinding, ...]:
        return validate_release_consistency(
            self.root,
            self.repository,
            distribution_version=self.distribution_version,
        )

    def commit(self, message: str = "fixture mutation") -> None:
        _commit(self.root, message)


def _run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(
        ["git", "-C", root, *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )


def _commit(root: Path, message: str) -> None:
    _run_git(root, "add", "-A")
    _run_git(
        root,
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        message,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_payload(
    family: Path,
    *,
    standard_id: str,
    standard_name: str,
    version: str,
    availability: str,
) -> str:
    payload_root = family / f"versions/{version}"
    shutil.copytree(_PAYLOAD_TEMPLATE, payload_root)
    payload_path = payload_root / "payload.toml"
    payload_text = payload_path.read_text(encoding="utf-8")
    payload_text = payload_text.replace('standard = "demo"', f'standard = "{standard_id}"')
    payload_text = payload_text.replace('version = "1.2"', f'version = "{version}"')
    payload_text = payload_text.replace(
        'availability = "consumer"',
        f'availability = "{availability}"',
    )
    if availability == "internal":
        payload_text = re.sub(
            r'\n\[\[resources\]\]\nid = "adopt"\nrole = "adoption-guide"\n'
            r'path = "adopt\.md"\nmedia_type = "text/markdown"\n'
            r'digest = "sha256:[0-9a-f]{64}"\n?',
            "\n",
            payload_text,
        )
        (payload_root / "adopt.md").unlink()
    payload_path.write_text(payload_text, encoding="utf-8")

    for document in ("README.md", "adopt.md", "agent-summary.md"):
        path = payload_root / document
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("Demo 1.2", f"{standard_name} {version}"),
            encoding="utf-8",
        )

    manifest = load_payload_manifest(payload_path)
    payload_text = payload_path.read_text(encoding="utf-8")
    for resource in manifest.resources:
        resource_digest = hashlib.sha256(
            (payload_root / resource.path.normalized).read_bytes()
        ).hexdigest()
        pattern = re.compile(
            rf'(path = "{re.escape(resource.path.original)}"\n'
            rf'media_type = "[^"]+"\ndigest = ")sha256:[0-9a-f]{{64}}(")'
        )
        payload_text, replacements = pattern.subn(
            rf"\g<1>sha256:{resource_digest}\2",
            payload_text,
            count=1,
        )
        assert replacements == 1
    payload_path.write_text(payload_text, encoding="utf-8")
    manifest = load_payload_manifest(payload_path)
    return validate_payload_integrity(payload_root, manifest).aggregate_digest.value


def _write_family(
    root: Path,
    *,
    standard_id: str,
    standard_name: str,
    versions: tuple[str, ...],
    availability: str,
) -> dict[str, str]:
    family = root / f"standards/{standard_id}"
    family.mkdir(parents=True)
    digests = {
        version: _write_payload(
            family,
            standard_id=standard_id,
            standard_name=standard_name,
            version=version,
            availability=availability,
        )
        for version in versions
    }
    entries = "\n\n".join(
        (
            "[[versions]]\n"
            f'version = "{version}"\n'
            f'payload = "versions/{version}/payload.toml"\n'
            f'digest = "{digests[version]}"'
        )
        for version in versions
    )
    _write(
        family / "standard.toml",
        (
            'schema_version = "2.0"\n\n'
            "[standard]\n"
            f'id = "{standard_id}"\n'
            f'name = "{standard_name}"\n'
            'summary = "Synthetic release-consistency fixture."\n'
            'status = "active"\n\n'
            f"{entries}\n"
        ),
    )
    return digests


def _catalog_version(
    catalog: CatalogSource,
    standard_id: str,
    role: CatalogRole,
) -> str:
    matching = [
        entry.version
        for entry in catalog.packages
        if entry.id == standard_id and entry.role is role
    ]
    assert matching
    return max(matching, key=lambda version: version.sort_key).value


def _catalog_inventory(catalog: CatalogSource, standard_id: str) -> str:
    versions = [entry.version for entry in catalog.packages if entry.id == standard_id]
    return ", ".join(
        f"`{standard_id}@{version.value}`"
        for version in sorted(versions, key=lambda version: version.sort_key)
    )


def _build_release_fixture(tmp_path: Path) -> ReleaseConsistencyFixture:
    root = tmp_path / "repository"
    root.mkdir()

    project_spec_digests = _write_family(
        root,
        standard_id="project-spec",
        standard_name="Project Specification",
        versions=("1.4",),
        availability="consumer",
    )
    internal_digests = _write_family(
        root,
        standard_id="standard-bundle-authoring",
        standard_name="Standard Bundle Authoring",
        versions=("2.4", "2.6", "2.10", "2.11"),
        availability="internal",
    )
    catalog = CatalogSource(
        schema_version="1.0",
        catalog_major=5,
        packages=[
            CatalogPackageEntry.model_validate(
                {
                    "id": "project-spec",
                    "version": "1.4",
                    "digest": project_spec_digests["1.4"],
                    "role": "default",
                }
            ),
            *[
                CatalogPackageEntry.model_validate(
                    {
                        "id": "standard-bundle-authoring",
                        "version": version,
                        "digest": internal_digests[version],
                        "role": "internal",
                    }
                )
                for version in ("2.4", "2.6", "2.10")
            ],
        ],
    )
    default_version = _catalog_version(catalog, "project-spec", CatalogRole.DEFAULT)
    internal_version = _catalog_version(
        catalog,
        "standard-bundle-authoring",
        CatalogRole.INTERNAL,
    )

    catalog_lines = [
        'schema_version = "1.0"',
        "catalog_major = 5",
        "",
    ]
    for entry in catalog.packages:
        catalog_lines.extend(
            [
                "[[packages]]",
                f'id = "{entry.id}"',
                f'version = "{entry.version.value}"',
                f'digest = "{entry.digest.value}"',
                f'role = "{entry.role.value}"',
                "",
            ]
        )
    _write(root / "catalogs/5.toml", "\n".join(catalog_lines))

    _write(
        root / "pyproject.toml",
        (
            "[project]\n"
            'name = "project-standards"\n'
            f'version = "{_DISTRIBUTION_VERSION}"\n'
            'requires-python = ">=3.14"\n'
        ),
    )
    _write(
        root / "README.md",
        (
            f"# Project Standards {_DISTRIBUTION_VERSION}\n\n"
            f'Install `"project-standards@v{_DISTRIBUTION_VERSION}"`; '
            f"`project-standards --version` reports "
            f"`project-standards {_DISTRIBUTION_VERSION}`.\n\n"
            f"Internal authority: Standard Bundle Authoring {internal_version} "
            f"([standard](standards/standard-bundle-authoring/versions/"
            f"{internal_version}/README.md)).\n"
        ),
    )
    _write(
        root / "UPGRADING.md",
        (
            f"# Upgrade to Project Standards {_DISTRIBUTION_VERSION}\n\n"
            f'uv tool install "git+https://example.invalid/'
            f'project-standards@v{_DISTRIBUTION_VERSION}"\n\n'
            f"Confirm `project-standards {_DISTRIBUTION_VERSION}`.\n"
        ),
    )
    _write(
        root / "AGENTS.md",
        (f"# Fixture instructions\n\nUse internal Standard Bundle Authoring {internal_version}.\n"),
    )
    _write(
        root / "standards/README.md",
        (
            "# Standards\n\n"
            f"Project Specification {default_version}: "
            f"[standard](project-spec/versions/{default_version}/README.md).\n\n"
            f"Standard Bundle Authoring {internal_version}: "
            f"[standard](standard-bundle-authoring/versions/"
            f"{internal_version}/README.md).\n"
        ),
    )
    _write(
        root / "standards/project-spec/README.md",
        (
            "# Project Specification Standard\n\n"
            f"Current prose: Project Specification {default_version}.\n\n"
            f"Current link: [standard](versions/{default_version}/README.md).\n\n"
            f"project-standards standards enable project-spec --version {default_version}\n"
        ),
    )
    _write(
        root / "standards/project-spec/adopt.md",
        (
            "# Adopt Project Specification\n\n"
            f"Current adoption guide: [guide](versions/{default_version}/adopt.md).\n\n"
            f"project-standards standards enable project-spec --version {default_version}\n"
        ),
    )
    _write(
        root / "standards/project-spec/agent-summary.md",
        (
            "# Project Specification agent summary\n\n"
            f"Resolve exact selector `project-spec@{default_version}`.\n"
        ),
    )
    _write(
        root / "standards/project-spec/reference.md",
        (
            "# Project Specification quick reference\n\n"
            f"The current package is project-spec version {default_version}.\n\n"
            f"{_HISTORICAL_MARKER}\n"
            "Historical permalink: "
            "[Project Specification 1.2](versions/1.2/README.md).\n"
        ),
    )
    historical_payload = root / "standards/project-spec/versions/1.2"
    historical_payload.mkdir()
    _write(
        historical_payload / "README.md",
        "# Project Specification 1.2\n\nImmutable historical payload.\n",
    )
    _write(
        historical_payload / "adopt.md",
        "# Adopt Project Specification 1.2\n\nImmutable historical payload.\n",
    )

    _write(
        root / "standards/standard-bundle-authoring/README.md",
        (
            "# Standard Bundle Authoring\n\n"
            f"Current internal package: Standard Bundle Authoring {internal_version}.\n"
        ),
    )
    _write(
        root / "standards/standard-bundle-authoring/agent-summary.md",
        (
            "# Standard Bundle Authoring agent summary\n\n"
            f"Use `standard-bundle-authoring@{internal_version}`.\n"
        ),
    )

    inventory = _catalog_inventory(catalog, "standard-bundle-authoring")
    _write(
        root / "docs/specs/current-release.md",
        (
            "# Current release specification\n\n"
            "## Revision History\n\n"
            "| Revision | Historical package |\n"
            "| --- | --- |\n"
            "| 0.1 | Project Specification 1.2 |\n\n"
            "<!-- release-consistency: historical-characterization project-spec -->\n"
            "Project Specification 1.2 characterized the previous behavior.\n\n"
            f"{_INVENTORY_MARKER}\n"
            f"Canonical internal inventory: {inventory}.\n\n"
            "<!-- release-consistency: catalog-range standard-bundle-authoring -->\n"
            "The supported catalog range began at Standard Bundle Authoring 2.4.\n"
        ),
    )
    _write(
        root / "docs/plans/current-release.md",
        (
            "# Current release plan\n\n"
            "## Deviations\n\n"
            "| Date | Historical package |\n"
            "| --- | --- |\n"
            "| 2026-01-01 | Project Specification 1.2 |\n"
        ),
    )
    _write(
        root / "docs/specs/archive/old-release.md",
        "# Archived specification\n\nProject Specification 1.2.\n",
    )
    _write(
        root / "docs/handoff/sessions/2026-01.md",
        "# Session history\n\nProject Specification 1.2.\n",
    )
    _write(
        root / "CHANGELOG.md",
        "# Changelog\n\n## 1.2.0\n\nProject Specification 1.2.\n",
    )

    repository = build_package_repository(root, catalog_major=5)
    assert repository.findings == ()
    graph = StandardsGraph(
        root=root,
        standards=(),
        missing_manifest_dirs=(),
        package_repository=repository,
    )
    _write(root / "standards/catalog.md", render_catalog(graph))
    assert repository.catalog is not None
    _write(
        root / ".standards/catalog.toml",
        render_consumer_catalog(
            repository.catalog,
            repository.family_map,
            repository.payload_map,
            tool_release=_DISTRIBUTION_VERSION,
        ).decode(),
    )

    _run_git(root, "init", "-q")
    _commit(root, "exact candidate")
    return ReleaseConsistencyFixture(
        root=root,
        repository=repository,
        distribution_version=_DISTRIBUTION_VERSION,
        default_version=default_version,
        internal_version=internal_version,
    )


@pytest.fixture
def release_fixture(tmp_path: Path) -> ReleaseConsistencyFixture:
    return _build_release_fixture(tmp_path)


def _replace_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _finding_paths(fixture: ReleaseConsistencyFixture) -> set[str]:
    return {finding.path for finding in fixture.validate()}


def test_release_consistency__exact_candidate__passes(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    assert release_fixture.validate() == ()


def test_release_consistency__distribution_metadata__matches_validated_version(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    _replace_text(
        release_fixture.root / "pyproject.toml",
        f'version = "{release_fixture.distribution_version}"',
        'version = "9.3.0"',
    )
    release_fixture.commit()

    findings = release_fixture.validate()

    assert "PC-RELEASE-DISTRIBUTION-VERSION" in {finding.code for finding in findings}
    assert "pyproject.toml" in {finding.path for finding in findings}


@pytest.mark.parametrize(
    ("path", "current_form"),
    [
        pytest.param("README.md", "Project Standards {version}", id="readme-prose"),
        pytest.param("README.md", "project-standards@v{version}", id="readme-pin"),
        pytest.param(
            "README.md",
            "project-standards {version}",
            id="readme-version-output",
        ),
        pytest.param(
            "UPGRADING.md",
            "Project Standards {version}",
            id="upgrading-prose",
        ),
        pytest.param(
            "UPGRADING.md",
            "project-standards@v{version}",
            id="upgrading-pin",
        ),
        pytest.param(
            "UPGRADING.md",
            "project-standards {version}",
            id="upgrading-version-output",
        ),
    ],
)
def test_release_consistency__stale_project_release_form__reports_document(
    release_fixture: ReleaseConsistencyFixture,
    path: str,
    current_form: str,
) -> None:
    current = current_form.format(version=release_fixture.distribution_version)
    _replace_text(
        release_fixture.root / path,
        current,
        current.replace(release_fixture.distribution_version, "9.3.0"),
    )
    release_fixture.commit()

    assert path in _finding_paths(release_fixture)


@pytest.mark.parametrize(
    ("path", "current_form"),
    [
        pytest.param(
            "standards/project-spec/README.md",
            "Current prose: Project Specification {version}",
            id="readme",
        ),
        pytest.param(
            "standards/project-spec/adopt.md",
            "versions/{version}/adopt.md",
            id="adopt",
        ),
        pytest.param(
            "standards/project-spec/agent-summary.md",
            "project-spec@{version}",
            id="agent-summary",
        ),
        pytest.param(
            "standards/project-spec/reference.md",
            "current package is project-spec version {version}",
            id="fourth-shallow-document",
        ),
        pytest.param(
            "standards/project-spec/README.md",
            "versions/{version}/README.md",
            id="versioned-link",
        ),
        pytest.param(
            "standards/project-spec/agent-summary.md",
            "project-spec@{version}",
            id="exact-selector",
        ),
        pytest.param(
            "standards/project-spec/adopt.md",
            "enable project-spec --version {version}",
            id="enable-command",
        ),
    ],
)
def test_release_consistency__stale_default_family_form__reports_document(
    release_fixture: ReleaseConsistencyFixture,
    path: str,
    current_form: str,
) -> None:
    current = current_form.format(version=release_fixture.default_version)
    stale = current.replace(release_fixture.default_version, "1.2")
    _replace_text(release_fixture.root / path, current, stale)
    release_fixture.commit()

    assert path in _finding_paths(release_fixture)


def test_release_consistency__internal_versions__use_numeric_catalog_maximum(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    assert release_fixture.internal_version == "2.10"
    family = release_fixture.repository.family_map["standard-bundle-authoring"]
    assert family.versions[-1].version.value == "2.11"

    assert release_fixture.validate() == ()


def test_release_consistency__missing_canonical_internal_row__reports_diagnostic(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    assert release_fixture.repository.catalog is not None
    consumer_only = CatalogSource(
        schema_version="1.0",
        catalog_major=release_fixture.repository.catalog.catalog_major,
        packages=[
            entry
            for entry in release_fixture.repository.catalog.packages
            if entry.id == "project-spec"
        ],
    )
    repository = replace(release_fixture.repository, catalog=consumer_only)

    findings = validate_release_consistency(
        release_fixture.root,
        repository,
        distribution_version=release_fixture.distribution_version,
    )

    assert "PC-RELEASE-INTERNAL-CURRENT-MISSING" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("README.md", id="root-readme"),
        pytest.param("standards/README.md", id="standards-readme"),
        pytest.param("AGENTS.md", id="agents"),
        pytest.param(
            "standards/standard-bundle-authoring/README.md",
            id="family-readme",
        ),
        pytest.param(
            "standards/standard-bundle-authoring/agent-summary.md",
            id="family-agent-summary",
        ),
    ],
)
def test_release_consistency__older_catalogued_internal_reference__reports_document(
    release_fixture: ReleaseConsistencyFixture,
    path: str,
) -> None:
    target = release_fixture.root / path
    _replace_text(
        target,
        release_fixture.internal_version,
        "2.6",
    )
    release_fixture.commit()

    assert path in _finding_paths(release_fixture)


def test_release_consistency__root_bare_internal_package_form__is_enforced(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    readme = release_fixture.root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + f"\n**Internal package `{release_fixture.internal_version}`:** current authority.\n",
        encoding="utf-8",
    )
    _replace_text(
        readme,
        f"Internal package `{release_fixture.internal_version}`",
        "Internal package `2.6`",
    )
    release_fixture.commit()

    assert "README.md" in _finding_paths(release_fixture)


def test_release_consistency__historical_marker__preserves_older_reference(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    assert release_fixture.validate() == ()


def test_release_consistency__removed_historical_marker__reports_reference(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    reference = release_fixture.root / "standards/project-spec/reference.md"
    _replace_text(reference, f"{_HISTORICAL_MARKER}\n", "")
    release_fixture.commit()

    assert "standards/project-spec/reference.md" in _finding_paths(release_fixture)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        pytest.param(
            "`standard-bundle-authoring@2.6`, ",
            "",
            id="missing-version",
        ),
        pytest.param(
            "`standard-bundle-authoring@2.6`, ",
            "`standard-bundle-authoring@2.6`, `standard-bundle-authoring@2.9`, ",
            id="extra-version",
        ),
    ],
)
def test_release_consistency__catalog_inventory_drift__reports_inventory(
    release_fixture: ReleaseConsistencyFixture,
    old: str,
    new: str,
) -> None:
    inventory = release_fixture.root / "docs/specs/current-release.md"
    _replace_text(inventory, old, new)
    release_fixture.commit()

    assert "docs/specs/current-release.md" in _finding_paths(release_fixture)


def test_release_consistency__structural_history_classes__pass(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    historical_paths = {
        "standards/project-spec/versions/1.2/README.md",
        "docs/specs/archive/old-release.md",
        "CHANGELOG.md",
        "docs/handoff/sessions/2026-01.md",
        "docs/specs/current-release.md",
        "docs/plans/current-release.md",
    }
    tracked = set(_run_git(release_fixture.root, "ls-files").stdout.splitlines())
    assert historical_paths <= tracked

    assert release_fixture.validate() == ()


def test_release_consistency__unclassified_mutable_path__fails_closed(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    _write(
        release_fixture.root / "docs/notes/current.md",
        "# Current notes\n\nUse Standard Bundle Authoring 2.4.\n",
    )
    release_fixture.commit()

    findings = release_fixture.validate()

    assert "docs/notes/current.md" in {finding.path for finding in findings}
    assert "PC-RELEASE-PATH-UNCLASSIFIED" in {finding.code for finding in findings}


def test_release_consistency__repository_sweep__is_internal_family_only(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    _write(
        release_fixture.root / "docs/notes/consumer-history.md",
        "# Consumer history\n\nUse Project Specification 1.2.\n",
    )
    release_fixture.commit()

    assert release_fixture.validate() == ()


def test_release_consistency__source_readme__is_in_internal_sweep(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    path = "src/project_standards/README.md"
    _write(
        release_fixture.root / path,
        "# Developer guide\n\nUse Standard Bundle Authoring 2.4.\n",
    )
    release_fixture.commit()

    assert path in _finding_paths(release_fixture)


@pytest.mark.parametrize(
    "marker",
    [
        pytest.param(
            "<!-- release-consistency: historical project-spec -->",
            id="mismatched-historical-family",
        ),
        pytest.param(
            "<!-- release-consistency: inventory project-spec catalog -->",
            id="inventory-does-not-hide-other-family",
        ),
    ],
)
def test_release_consistency__classification_marker__applies_only_to_its_family(
    release_fixture: ReleaseConsistencyFixture,
    marker: str,
) -> None:
    _write(
        release_fixture.root / "docs/notes/current.md",
        f"# Current notes\n\n{marker}\nUse Standard Bundle Authoring 2.4.\n",
    )
    release_fixture.commit()

    findings = release_fixture.validate()

    assert "docs/notes/current.md" in {finding.path for finding in findings}
    assert any(finding.standard_id == "standard-bundle-authoring" for finding in findings)


def test_release_consistency__unclassified_live_spec_body__fails_closed(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    specification = release_fixture.root / "docs/specs/current-release.md"
    specification.write_text(
        specification.read_text(encoding="utf-8")
        + "\n## Current authority\n\nStandard Bundle Authoring 2.4 is current.\n",
        encoding="utf-8",
    )
    release_fixture.commit()

    findings = release_fixture.validate()

    assert "docs/specs/current-release.md" in {finding.path for finding in findings}
    assert "PC-RELEASE-PATH-UNCLASSIFIED" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    ("path", "prefix", "reference"),
    [
        pytest.param(
            "docs/specs/standard-bundle-authoring.md",
            "# Standard Bundle Authoring history\n\n",
            "Standard Bundle Authoring 2.4 is current.\n",
            id="matching-spec-filename",
        ),
        pytest.param(
            "docs/plans/completed.md",
            "---\nstatus: complete\n---\n\n# Completed plan\n\n",
            "Standard Bundle Authoring 2.4 is current.\n",
            id="completed-plan",
        ),
        pytest.param(
            "docs/plans/staged.md",
            "# Staged plan\n\n",
            "Standard Bundle Authoring 2.11 is current.\n",
            id="family-indexed-uncatalogued-version",
        ),
    ],
)
def test_release_consistency__document_metadata__cannot_classify_current_assertion(
    release_fixture: ReleaseConsistencyFixture,
    path: str,
    prefix: str,
    reference: str,
) -> None:
    _write(release_fixture.root / path, prefix + reference)
    release_fixture.commit()

    findings = release_fixture.validate()

    assert path in {finding.path for finding in findings}
    assert "PC-RELEASE-PATH-UNCLASSIFIED" in {finding.code for finding in findings}


def test_release_consistency__characterized_document_digest__uses_raw_bytes(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    path = "docs/plans/2026-07-25-v5-adoption-integrity-correction-train-plan.md"
    content = (_ROOT / path).read_bytes()
    target = release_fixture.root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    release_fixture.commit()
    target.write_bytes(content.replace(b"\n", b"\r\n"))

    findings = release_fixture.validate()

    assert path in {finding.path for finding in findings}
    assert "PC-RELEASE-PATH-UNCLASSIFIED" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param("missing", id="missing"),
        pytest.param("escaping", id="escaping"),
        pytest.param("symlink", id="symlink"),
    ],
)
def test_release_consistency__unsafe_current_link__reports_link(
    release_fixture: ReleaseConsistencyFixture,
    failure: str,
) -> None:
    readme = release_fixture.root / "standards/project-spec/README.md"
    target = (
        release_fixture.root
        / f"standards/project-spec/versions/{release_fixture.default_version}/README.md"
    )
    if failure == "missing":
        target.unlink()
    elif failure == "escaping":
        _replace_text(
            readme,
            f"versions/{release_fixture.default_version}/README.md",
            "../../../outside.md",
        )
    else:
        target.unlink()
        target.symlink_to("../../../../README.md")
    release_fixture.commit()

    assert "standards/project-spec/README.md" in _finding_paths(release_fixture)


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param("invalid-utf8", id="invalid-utf8"),
        pytest.param("missing", id="missing"),
        pytest.param("symlink", id="symlink"),
    ],
)
def test_release_consistency__unreadable_required_surface__is_deterministic(
    release_fixture: ReleaseConsistencyFixture,
    failure: str,
) -> None:
    readme = release_fixture.root / "README.md"
    if failure == "invalid-utf8":
        readme.write_bytes(b"\xff")
    elif failure == "missing":
        readme.unlink()
    else:
        readme.unlink()
        readme.symlink_to("UPGRADING.md")
    release_fixture.commit()

    first = release_fixture.validate()
    second = release_fixture.validate()

    assert first
    assert first == second
    assert "README.md" in {finding.path for finding in first}


def test_release_consistency__symlinked_required_surface_ancestor__is_rejected(
    release_fixture: ReleaseConsistencyFixture,
    tmp_path: Path,
) -> None:
    family = release_fixture.root / "standards/project-spec"
    outside = tmp_path / "outside-project-spec"
    family.rename(outside)
    family.symlink_to(outside, target_is_directory=True)

    findings = release_fixture.validate()

    assert "standards/project-spec/README.md" in {finding.path for finding in findings}
    assert "PC-RELEASE-CORPUS" in {finding.code for finding in findings}


def test_release_consistency__multiple_findings__are_sorted_and_redacted(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    secret_line = "Current prose: Project Specification 1.2 token-super-secret"
    readme = release_fixture.root / "standards/project-spec/README.md"
    _replace_text(
        readme,
        f"Current prose: Project Specification {release_fixture.default_version}",
        secret_line,
    )
    _replace_text(
        release_fixture.root / "README.md",
        f"Project Standards {release_fixture.distribution_version}",
        "Project Standards 9.3.0",
    )
    release_fixture.commit()

    findings = release_fixture.validate()

    assert findings == tuple(sorted(findings, key=finding_sort_key))
    assert all(
        "token-super-secret"
        not in " ".join(
            (
                finding.identity,
                finding.message,
                finding.hint,
            )
        )
        for finding in findings
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("standards/catalog.md", id="human-catalog"),
        pytest.param(".standards/catalog.toml", id="consumer-catalog"),
    ],
)
def test_release_consistency__catalog_projection_drift__reports_projection(
    release_fixture: ReleaseConsistencyFixture,
    path: str,
) -> None:
    catalog = release_fixture.root / path
    catalog.write_text(
        catalog.read_text(encoding="utf-8") + "\nUnrendered drift.\n",
        encoding="utf-8",
    )
    release_fixture.commit()

    assert path in _finding_paths(release_fixture)


def test_release_consistency__live_shallow_family_corpus__is_exact_and_immutable_disjoint() -> None:
    tracked = _run_git(_ROOT, "ls-files", "standards").stdout.splitlines()
    shallow = {path for path in tracked if path.endswith(".md") and len(Path(path).parts) == 3}

    assert shallow == _LIVE_SHALLOW_FAMILY_CORPUS
    assert all("/versions/" not in path for path in shallow)


def test_release_consistency__known_repository_regressions__reports_four_mismatches(
    release_fixture: ReleaseConsistencyFixture,
) -> None:
    _replace_text(
        release_fixture.root / "README.md",
        release_fixture.internal_version,
        "2.4",
    )
    project_readme = release_fixture.root / "standards/project-spec/README.md"
    _replace_text(
        project_readme,
        f"Current prose: Project Specification {release_fixture.default_version}",
        "Current prose: Project Specification 1.2",
    )
    _replace_text(
        project_readme,
        f"enable project-spec --version {release_fixture.default_version}",
        "enable project-spec --version 1.2",
    )
    _replace_text(
        release_fixture.root / "standards/project-spec/adopt.md",
        f"enable project-spec --version {release_fixture.default_version}",
        "enable project-spec --version 1.2",
    )
    release_fixture.commit()

    findings = release_fixture.validate()
    regression_paths = [
        finding.path
        for finding in findings
        if finding.path
        in {
            "README.md",
            "standards/project-spec/README.md",
            "standards/project-spec/adopt.md",
        }
    ]

    assert regression_paths.count("README.md") == 1
    assert regression_paths.count("standards/project-spec/README.md") == 2
    assert regression_paths.count("standards/project-spec/adopt.md") == 1
