"""markdown-tooling 1.8 legacy byte-form acceptance (5.8.0 FR-005 / issue #27).

A consumer that adopted markdown-tooling before the ``adopt`` CLI existed can
hold a ``.markdownlint.json`` that is parsed-JSON-equal to the shipped artifact
yet serialized with literal UTF-8 CJK punctuation instead of the shipped
``\\uXXXX`` escapes. That literal byte form hashes to a distinct digest, so the
1.7 ``legacy-markdownlint-config`` signature (escaped digest only) treats it as a
modified file and hard-blocks migration. 1.8 adds the literal digest to the
signature lineage so either byte form migrates cleanly to managed ownership of
the current shipped escaped bytes.

These tests exercise the real signature-matching path through
``plan_legacy_migration`` rather than a provider-level snapshot, so the accepted
digest set is what actually gates the outcome.
"""

from __future__ import annotations

import hashlib
import json
import shutil
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
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.projection import sync_payload_projection
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
# Resource sources come from a shipped version so their bytes match the legacy
# signatures' known digests; only ``.markdownlint.json`` is the variable under
# test. The released editorconfig differs from the payload's revised legacy copy,
# so it is drawn from the pinned release fixture like the reconstruction suite.
_RESOURCE_VERSION = _FAMILY / "versions/1.8"
_RELEASED_EDITORCONFIG = _ROOT / "tests/fixtures/legacy_releases/v4.3.0/editorconfig"

_SHIPPED_MARKDOWNLINT = _RESOURCE_VERSION / "artifacts/markdownlint.json"
_OBSERVED_LITERAL = _ROOT / "tests/fixtures/observed_consumers/markdownlint-literal-cjk.json"
_OBSERVED_LITERAL_DIGEST = "sha256:4c1c089d0552a6118f6a8b7d85bae1bd762da41d601d1c489bdb9143f6a2d548"
_SHIPPED_ESCAPED_DIGEST = "sha256:51204b5170e47da3716d3870d36ef1eb4b28a27d7289c65f7f1457943c499793"
_MARKDOWNLINT_BLOCK_CODES = {
    "CP-CONSUMER-CONFLICT",
    "CP-MIGRATION-LEGACY-DIGEST",
    "MT-LEGACY-MODIFIED",
}


def test_observed_fixture_digest_and_parsed_equality() -> None:
    """The observed fixture is the pinned literal-form digest and equal JSON (TC-T8-001).

    Guards both halves of the acceptance premise: the fixture reproduces the exact
    digest the 1.8 signature now accepts, and it decodes to the same JSON as the
    shipped escaped artifact (so accepting it does not admit a semantically
    different config).
    """
    literal_bytes = _OBSERVED_LITERAL.read_bytes()
    assert "sha256:" + hashlib.sha256(literal_bytes).hexdigest() == _OBSERVED_LITERAL_DIGEST

    shipped_bytes = _SHIPPED_MARKDOWNLINT.read_bytes()
    assert "sha256:" + hashlib.sha256(shipped_bytes).hexdigest() == _SHIPPED_ESCAPED_DIGEST
    assert literal_bytes != shipped_bytes
    assert json.loads(literal_bytes.decode("utf-8")) == json.loads(shipped_bytes.decode("utf-8"))


def test_observed_fixture_provenance_is_sanitized() -> None:
    """The provenance note carries digest and dates but no consumer identity (TC-T8-003).

    The fixture is recovered from a real working tree, so its note must record
    enough to reproduce the behavior (digest, recovery date, adoption date) while
    leaking no repository name, path, or owner.
    """
    note = (_OBSERVED_LITERAL.parent / "README.md").read_text(encoding="utf-8")
    assert _OBSERVED_LITERAL_DIGEST in note
    assert "2026-07-22" in note  # recovery date
    assert "2026-06-07" in note  # adoption-commit date

    lowered = note.lower()
    for identifier in ("homelab", "/home/chris", "github.com/", "l3digitalnet", "luminous3d"):
        assert identifier not in lowered, f"provenance note leaks identifier: {identifier!r}"


def _installed_distribution(tmp_path: Path, *, version: str) -> InstalledDistribution:
    """Build a single-version markdown-tooling distribution at ``version``.

    Mirrors the reconstruction suite's helper: the family tree is copied whole,
    then a minimal standard.toml/catalog advertise only ``version`` as default so
    the legacy migration resolves against exactly the signature set under test.
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
    """Rebuild a released v4 markdown-tooling consumer with a chosen config byte form.

    Every artifact other than ``.markdownlint.json`` is a byte form the legacy
    signatures already know, so the migration outcome turns solely on which
    ``.markdownlint.json`` bytes are supplied.
    """
    repo = tmp_path / "consumer"
    repo.mkdir(parents=True)
    (repo / ".project-standards.yml").write_text(
        'standards_version: "v4"\nmarkdown_tooling:\n  version: "1.1"\n',
        encoding="utf-8",
    )
    sources = {
        ".markdownlint.json": markdownlint,
        ".prettierrc.json": _RESOURCE_VERSION / "artifacts/prettierrc.json",
        ".editorconfig": _RELEASED_EDITORCONFIG,
        ".vscode/extensions.json": _RESOURCE_VERSION / "resources/legacy-vscode-extensions.json",
        ".github/workflows/lint-markdown.yml": (
            _RESOURCE_VERSION / "resources/legacy-lint-markdown.caller.yml"
        ),
        ".github/workflows/format.yml": _RESOURCE_VERSION / "resources/legacy-format.caller.yml",
    }
    for target, source in sources.items():
        destination = repo / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return repo


def test_literal_form_blocks_under_1_7_signature(tmp_path: Path) -> None:
    """Characterize the 1.7 behavior: the escaped form migrates, the literal blocks.

    This pins the pre-fix authority so the 1.8 fix is a strict widening of the
    accepted set rather than a change to how the escaped form is handled.
    """
    escaped_repo = _v4_consumer(tmp_path / "escaped", markdownlint=_SHIPPED_MARKDOWNLINT)
    escaped_distribution = _installed_distribution(tmp_path / "escaped", version="1.7")
    escaped_plan = plan_legacy_migration(escaped_repo, escaped_distribution, "5")
    assert escaped_plan.applicable, escaped_plan.findings
    assert [f for f in escaped_plan.findings if f.path == ".markdownlint.json"] == []

    literal_repo = _v4_consumer(tmp_path / "literal", markdownlint=_OBSERVED_LITERAL)
    literal_distribution = _installed_distribution(tmp_path / "literal", version="1.7")
    literal_plan = plan_legacy_migration(literal_repo, literal_distribution, "5")
    assert not literal_plan.applicable
    assert {
        finding.code for finding in literal_plan.findings if finding.path == ".markdownlint.json"
    } == _MARKDOWNLINT_BLOCK_CODES


@pytest.mark.parametrize(
    "markdownlint",
    [
        pytest.param(_SHIPPED_MARKDOWNLINT, id="shipped-escaped"),
        pytest.param(_OBSERVED_LITERAL, id="observed-literal"),
    ],
)
def test_both_byte_forms_migrate_cleanly_on_1_8(tmp_path: Path, markdownlint: Path) -> None:
    """Both byte forms migrate cleanly under 1.8 to managed escaped ownership (TC-T8-002).

    The literal leg is the fix: 1.8 accepts the observed digest, so the file no
    longer blocks. Both legs converge on the current shipped escaped bytes and a
    stable reconciliation with no further work on that file.
    """
    repo = _v4_consumer(tmp_path, markdownlint=markdownlint)
    distribution = _installed_distribution(tmp_path, version="1.8")

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
