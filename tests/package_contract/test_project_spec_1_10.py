"""Package contract for the Project Specification 1.10 payload.

1.10 exists for one reason: to put the shipped templates back in agreement with
`project_standards.specs.registry.TEMPLATES_DIR`, the corpus every registry in this
repository is derived from (issue #199). The equality assertion below is therefore
the point of the module, and it is written against the payload catalog 5 currently
advertises as `default` rather than against a hardcoded `versions/1.10` path — a
future cut that copies 1.10's templates forward without re-syncing them has to fail
here, which is exactly how 1.9's divergence went unnoticed for two source edits.

Two consumers read a template corpus and they are not the same one. Unselected
`spec new` / `spec upgrade` read `TEMPLATES_DIR` directly; the selected V5 path
invokes `providers/project_spec.py`, which builds its registry from the payload's
own `template-*` resources. Only the selected path runs the `SL-BOILERPLATE`
conformance check, so a divergence never produced a self-inconsistent lint — it
produced two corpora that silently disagreed about what canonical text is, and a
document scaffolded through one path but linted through the other. Keeping the two
byte-identical collapses that back to one answer.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-spec"
_PREDECESSOR = _FAMILY / "versions/1.9"
_SUCCESSOR = _FAMILY / "versions/1.10"
_PROJECTION = _ROOT / "src/project_standards/payloads/project-spec/1.10"
_PREDECESSOR_DIGEST = "sha256:980f922a3980de82e1302db6d2d22ec88ca2457b2affd64876ada4dc09ab669e"

# The three templates carry the whole consumer-visible change; every other file that
# differs from 1.9 differs only by the version stamp, which
# `test_project_spec_1_10__non_template_bytes__differ_from_1_9_only_by_the_version_stamp`
# proves mechanically rather than by digest bookkeeping.
_TEMPLATE_CHANGES = frozenset(f"templates/{filename}" for filename in TIER_FILES.values())
_STAMP_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "providers/project_spec.py",
        "resources/tooling-notes.md",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _catalog_roles() -> dict[str, str]:
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    return {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "project-spec"
    }


def test_project_spec_1_10__default_payload_templates__equal_the_canonical_registry_source() -> (
    None
):
    """The acceptance criterion of issue #199, asserted for whatever version is default.

    Resolving the version from the catalog instead of naming 1.10 is deliberate: the
    drift this pins reappears the moment a cut copies templates forward, which is a
    copy no version-specific test would be looking at.
    """
    default = next(version for version, role in _catalog_roles().items() if role == "default")
    templates = _FAMILY / f"versions/{default}/templates"

    for filename in TIER_FILES.values():
        assert (templates / filename).read_bytes() == (TEMPLATES_DIR / filename).read_bytes(), (
            f"project-spec@{default} ships a {filename} the linter's canonical registry"
            " would not accept"
        )
    assert {path.name for path in templates.iterdir()} == set(TIER_FILES.values())


def test_project_spec_1_10__is_complete_and_preserves_every_unchanged_1_9_byte() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _TEMPLATE_CHANGES - _STAMP_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for successor in successor_files.values():
        assert successor.stat().st_mode & 0o7777 == 0o644

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.10"
    assert indexed["1.10"].digest == integrity.aggregate_digest
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-10"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.10"]


def test_project_spec_1_10__non_template_bytes__differ_from_1_9_only_by_the_version_stamp() -> None:
    """No behavior rides along with the template correction.

    Rewriting the successor's own version token back to the predecessor's must
    reproduce 1.9 exactly. Prose that genuinely describes 1.10 — the README's "What
    1.10 changed" section and the adopt guide's upgrade paragraph — is exempted by
    name, so any *other* edit smuggled into this cut fails here.
    """
    narrative = {"README.md", "adopt.md", "agent-summary.md", "payload.toml"}
    for relative in _STAMP_CHANGES - narrative:
        successor = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        predecessor = (_PREDECESSOR / relative).read_text(encoding="utf-8")
        assert successor.replace("1.10", "1.9") == predecessor, relative


# README, adopt, and agent-summary name 1.9 on purpose — they carry this cut's account
# of what changed and why, which cannot be written without naming the predecessor. Every
# other payload file is a stamp surface where a surviving `1.9` is drift.
_PREDECESSOR_NARRATIVE = frozenset({"README.md", "adopt.md", "agent-summary.md"})


def test_project_spec_1_10__carries_no_stale_predecessor_stamp() -> None:
    stale = {
        relative
        for relative, path in _files(_SUCCESSOR).items()
        if relative not in _TEMPLATE_CHANGES
        and relative not in _PREDECESSOR_NARRATIVE
        and "1.9" in path.read_text(encoding="utf-8")
    }
    assert stale == set(), "1.10 payload files still stamp the 1.9 predecessor"

    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )
    assert provider_input["properties"]["version"]["const"] == "1.10"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.10"


def test_project_spec_1_10__records_what_the_cut_changed() -> None:
    readme = (_SUCCESSOR / "README.md").read_text(encoding="utf-8")
    assert "- **Package version:** `1.10`" in readme
    assert "### What 1.10 changed" in readme
    assert "src/project_standards/specs/templates/" in readme
    assert "SL-BOILERPLATE" in readme

    adopt = (_SUCCESSOR / "adopt.md").read_text(encoding="utf-8")
    assert "# Adopt Project Specification 1.10" in adopt
    assert "project-standards standards enable project-spec --version 1.10" in adopt
    assert "Upgrading from 1.9 closes one source of unrepairable warnings." in adopt

    summary = (_SUCCESSOR / "agent-summary.md").read_text(encoding="utf-8")
    assert "# Project Specification 1.10 summary" in summary
    assert "byte-identical to this repository's canonical template source" in summary


def test_project_spec_1_10__projection_and_catalog_activation_are_exact() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]

    # A released role only ever advances to `retained` (ADR 0024): 1.10 held
    # `default` from the 5.25.0 activation until 1.11 took it, and both rows must
    # stay advertised so an exact pin keeps resolving. Which version currently holds
    # `default` is asserted catalog-derived in test_catalog_roles.py.
    roles = _catalog_roles()
    assert roles["1.9"] == "retained"
    assert roles["1.10"] == "retained"

    generated = (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
    assert "| [`project-spec`](project-spec/README.md) | active | 1.10 | retained |" in generated


def test_project_spec_1_10__catalog_default__is_what_this_repository_dogfoods() -> None:
    """`.standards/` must resolve the family's catalog default, and still offer 1.10.

    `.standards/catalog.toml` and `.standards/lock.toml` are rewritten by
    `reconcile --apply` during release preparation, not by the cut, so this is red
    between a cut and its release commit by design — that gap is the thing it
    catches. The expected version is read from `catalogs/5.toml` rather than
    written out, because the assertion is "producer and consumer agree", not "the
    consumer is on 1.10": hardcoding the latter broke this module on the two cuts
    after 1.10 without any producer/consumer disagreement existing.

    The 1.10-specific half is availability: a retained payload stays selectable by
    exact pin, so it must survive in `available` after losing the default.
    """
    default = next(version for version, role in _catalog_roles().items() if role == "default")

    consumer_catalog = tomllib.loads(
        (_ROOT / ".standards/catalog.toml").read_text(encoding="utf-8")
    )
    selection = consumer_catalog["standards"]["project-spec"]
    assert selection["default"] == default
    assert {default, "1.10"} <= set(selection["available"])

    lock = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    assert lock["standards"]["project-spec"]["resolved"] == default
