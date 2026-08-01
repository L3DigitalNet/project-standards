"""markdown-tooling 1.11 registration and the issue #100 legacy-digest acceptance.

`legacy-markdownlint-config` accepted the v2/v3/v4 shipped bytes and the observed
literal-UTF-8 form (#27), but never the bytes markdown-tooling itself currently
ships. Since 1.9 the shipped rule set carries `"MD060": false`, so a V4 consumer
whose only local deviation was that same value — a deviation upstream has since
adopted as its own default — held a file the planner already planned to `adopt`
while the migration provider called it modified, and migration exited 1. The two
documented remedies were both wrong: regress the file to a superseded rule value,
or take `consumer-owned` on a file that already equals the managed value.

1.11 appends the currently shipped digest, the same remedy #10 and #27 received.
These tests drive the real signature-matching path through `plan_legacy_migration`
so the accepted digest set is what actually gates the outcome, and pin the 1.10
behavior first so the 1.11 result is attributable to the appended digest.
"""

from __future__ import annotations

import hashlib
import shutil
import tomllib
from pathlib import Path

import pytest

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.migration import (
    apply_legacy_migration,
    plan_legacy_migration,
)
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.projection import sync_payload_projection
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_PREDECESSOR = _FAMILY / "versions/1.10"
_SUCCESSOR = _FAMILY / "versions/1.11"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-tooling/1.11"
_PREDECESSOR_DIGEST = "sha256:db6b97d120ac9f31ab589c2d48926acb5713b840738dd13b6460d34632e4fc9b"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)

_RELEASED_EDITORCONFIG = _ROOT / "tests/fixtures/legacy_releases/v4.3.0/editorconfig"
_SHIPPED_MARKDOWNLINT = _SUCCESSOR / "artifacts/markdownlint.json"
_SHIPPED_DIGEST = "sha256:c6a0217de8adbab6e24038f98577de8fa2f90062b873cc97b6bd2c09f89dba2b"
_OBSERVED_LITERAL = _ROOT / "tests/fixtures/observed_consumers/markdownlint-literal-cjk.json"
_MARKDOWNLINT_BLOCK_CODES = {
    "CP-MIGRATION-LEGACY-DIGEST",
    "MT-LEGACY-MODIFIED",
}


def _installed_distribution(tmp_path: Path, *, version: str) -> InstalledDistribution:
    """Build a single-version markdown-tooling distribution at `version`.

    The family tree is copied whole, then a minimal standard.toml/catalog
    advertise only `version` as default, so the legacy migration resolves against
    exactly the signature set under test.
    """
    fixture = tmp_path / f"distribution-{version}"
    repository = copy_minimal_repository(fixture)
    family = repository / "standards/markdown-tooling"
    shutil.copytree(_FAMILY, family)
    payload_root = _FAMILY / "versions" / version
    manifest = load_payload_manifest(payload_root / "payload.toml")
    integrity = validate_payload_integrity(payload_root, manifest)
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "markdown-tooling"
name = "Markdown Tooling Standard"
summary = "Prettier and markdownlint with semantic editor configuration."
status = "active"

[[versions]]
version = "{version}"
payload = "versions/{version}/payload.toml"
digest = "{integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "markdown-tooling"
version = "{version}"
digest = "{integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _v4_consumer(tmp_path: Path, *, markdownlint: Path) -> Path:
    """Rebuild a released v4 consumer whose only variable is `.markdownlint.json`."""
    repo = tmp_path / "consumer"
    repo.mkdir(parents=True)
    (repo / ".project-standards.yml").write_text(
        'standards_version: "v4"\nmarkdown_tooling:\n  version: "1.1"\n',
        encoding="utf-8",
    )
    sources = {
        ".markdownlint.json": markdownlint,
        ".prettierrc.json": _SUCCESSOR / "artifacts/prettierrc.json",
        ".editorconfig": _RELEASED_EDITORCONFIG,
        ".vscode/extensions.json": _SUCCESSOR / "resources/legacy-vscode-extensions.json",
        ".github/workflows/lint-markdown.yml": (
            _SUCCESSOR / "resources/legacy-lint-markdown.caller.yml"
        ),
        ".github/workflows/format.yml": _SUCCESSOR / "resources/legacy-format.caller.yml",
    }
    for target, source in sources.items():
        destination = repo / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return repo


def test_markdown_tooling_1_11__shipped_bytes__are_the_declared_third_digest() -> None:
    """The appended digest must be the payload's own artifact, not a transcription."""
    shipped = _SHIPPED_MARKDOWNLINT.read_bytes()
    assert "sha256:" + hashlib.sha256(shipped).hexdigest() == _SHIPPED_DIGEST
    assert (_SUCCESSOR / "resources/markdownlint.json").read_bytes() == shipped

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    signature = next(
        item for item in manifest.legacy_signatures if item.id == "legacy-markdownlint-config"
    )
    accepted = {digest.value for digest in signature.known_content_digests}

    assert _SHIPPED_DIGEST in accepted
    assert len(accepted) == 3
    # The payload model forbids pairing unknown-content preservation with a
    # consumer-owned intent pointer; widening the digest history must not have
    # reached for the other escape.
    assert signature.consumer_owned_intent_pointer is not None
    assert signature.unknown_content_disposition is None


def test_markdown_tooling_1_11__shipped_form__blocks_under_the_1_10_signature(
    tmp_path: Path,
) -> None:
    """Characterize 1.10: the file the planner would adopt is called modified."""
    repo = _v4_consumer(tmp_path, markdownlint=_SHIPPED_MARKDOWNLINT)
    distribution = _installed_distribution(tmp_path, version="1.10")

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert {
        finding.code for finding in plan.findings if finding.path == ".markdownlint.json"
    } >= _MARKDOWNLINT_BLOCK_CODES


@pytest.mark.parametrize(
    "markdownlint",
    [
        pytest.param(_SHIPPED_MARKDOWNLINT, id="currently-shipped"),
        pytest.param(_OBSERVED_LITERAL, id="observed-literal-from-issue-27"),
    ],
)
def test_markdown_tooling_1_11__accepted_forms__migrate_cleanly(
    tmp_path: Path, markdownlint: Path
) -> None:
    """1.11 accepts the shipped bytes without withdrawing the #27 form."""
    repo = _v4_consumer(tmp_path, markdownlint=markdownlint)
    distribution = _installed_distribution(tmp_path, version="1.11")

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    assert [finding for finding in plan.findings if finding.path == ".markdownlint.json"] == []
    assert apply_legacy_migration(plan).success
    assert (repo / ".markdownlint.json").read_bytes() == _SHIPPED_MARKDOWNLINT.read_bytes()

    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        and action.target == ".markdownlint.json"
        for action in second.actions
    )


def test_markdown_tooling_1_11__managed_bytes__are_unchanged_from_1_10() -> None:
    """Only the acceptance envelope and prose move; every rendered byte is frozen."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()

    successor_manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    successor_integrity = validate_payload_integrity(_SUCCESSOR, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert successor_manifest.payload.version.value == "1.11"
    assert successor_manifest.payload.availability.value == "consumer"
    assert indexed["1.11"].digest == successor_integrity.aggregate_digest
    assert any(
        migration.to_endpoint.value == "package:1.11" for migration in successor_manifest.migrations
    )
    assert {
        migration.from_endpoint.value
        for migration in successor_manifest.migrations
        if migration.to_endpoint.value == "package:1.11"
    } == {"package:1.7", "package:1.8", "package:1.9", "package:1.10", "legacy:v4-markdown-tooling"}


def test_markdown_tooling_1_11__catalog_role__retains_predecessor() -> None:
    """Catalog 5 must retain 1.11 after selecting its successor.

    The payload can be complete and valid while the catalog still selects its
    predecessor; only this row makes the successor the default a consumer on
    `version = "latest"` resolves to.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "markdown-tooling"
    }

    assert roles["1.11"] == "retained"
    assert roles["1.12"] == "default"
    assert roles["1.10"] == "retained"


def test_markdown_tooling_1_11__payload_projection__matches_complete_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
