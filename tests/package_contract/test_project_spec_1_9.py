"""Package contract for the unadvertised Project Specification 1.9 candidate."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-spec"
_PREDECESSOR = _FAMILY / "versions/1.8"
_SUCCESSOR = _FAMILY / "versions/1.9"
_PROJECTION = _ROOT / "src/project_standards/payloads/project-spec/1.9"
_PREDECESSOR_DIGEST = "sha256:dc7c7f7c91d70717675c0de5bcd5759b498c6431db62f38f51ea060637a286d2"
_CHECKS = ["shared-boilerplate", "mandatory-phrasing"]
_SUCCESSOR_CHANGES = frozenset(
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
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def test_project_spec_1_9__is_complete_and_preserves_every_1_8_byte() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys() | {
        "schemas/lint-findings.schema.json"
    }
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for successor in successor_files.values():
        assert successor.stat().st_mode & 0o7777 == 0o644

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.9"
    assert indexed["1.9"].digest == integrity.aggregate_digest
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-9"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.9"]


def test_project_spec_1_9__schemas_fix_successor_identity_and_lint_coverage() -> None:
    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )
    findings = json.loads(
        (_SUCCESSOR / "schemas/lint-findings.schema.json").read_text(encoding="utf-8")
    )

    assert provider_input["properties"]["version"]["const"] == "1.9"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.9"
    assert findings["properties"]["checks"] == {
        "type": "array",
        "prefixItems": [{"const": check} for check in _CHECKS],
        "items": False,
        "minItems": 2,
        "maxItems": 2,
    }
    assert set(findings["required"]) == {"findings", "checks"}
    assert (_SUCCESSOR / "schemas/findings.schema.json").read_bytes() == (
        _PREDECESSOR / "schemas/findings.schema.json"
    ).read_bytes()


def test_project_spec_1_9__identity_and_conformance_guidance_are_complete() -> None:
    expected = {
        "README.md": (
            "- **Package version:** `1.9`",
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
            "shared-boilerplate",
            "mandatory-phrasing",
        ),
        "adopt.md": (
            "# Adopt Project Specification 1.9",
            "project-standards standards enable project-spec --version 1.9",
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
            "additive",
            "semantic review",
        ),
        "agent-summary.md": (
            "# Project Specification 1.9 summary",
            "Package version `1.9`",
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
        ),
        "resources/tooling-notes.md": (
            "`SL-BOILERPLATE`",
            "`SL-REQUIREMENT-PHRASING`",
            "shared-boilerplate",
            "mandatory-phrasing",
        ),
    }
    for relative, fragments in expected.items():
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in document, (relative, fragment)
    tooling = (_SUCCESSOR / "resources/tooling-notes.md").read_text(encoding="utf-8")
    assert "Shared **boilerplate is identical** (spec-lifecycle paragraph" not in tooling


def test_project_spec_1_9__projection_and_unadvertised_catalog_role_are_exact() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "project-spec"
    }
    assert roles["1.8"] == "default"
    assert "1.9" not in roles

    generated = (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
    assert "| [`project-spec`](project-spec/README.md) | active | 1.9 | unadvertised |" in generated

    selected = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    assert selected["standards"]["project-spec"]["resolved"] == "1.8"
