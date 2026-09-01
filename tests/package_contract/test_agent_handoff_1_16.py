"""Package-contract proof for the Agent Handoff 1.16 provider-registry citation successor.

1.16 exists to correct a stale test citation: the cross-file contract comment
above `_SKILL_TARGETS` in the provider named a per-family registry test
(`tests/package_contract/test_agent_handoff_1_15.py`) as the place that pins the
skill-target/`payload.toml` agreement, but that equality is asserted catalog-wide
in `tests/package_contract/test_provider_registry.py` (issue #194) rather than per
family — the same fact 1.15's own file header already states. 1.16 re-cites the
comment to name the generic test (issue #196). Nothing else changes: every option,
policy value, template, hook, provider behavior, contribution, and artifact target
is byte-identical to 1.15.

That registry-versus-payload agreement is asserted catalog-wide in
`test_provider_registry.py` (issue #194) rather than per family, so this file
proves only what is specific to the 1.16 cut.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.15"
_SUCCESSOR = _FAMILY / "versions/1.16"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.16"
_PREDECESSOR_DIGEST = "sha256:96a8ed59dbbc870fd6d1335d557f48798ff3d63544cab673b4bcd789a2d5e8d3"
_SUCCESSOR_CHANGES = frozenset(
    {
        # Version constants every cut advances.
        "payload.toml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
        # Documentation of the citation fix for readers who never open payload.toml.
        "README.md",
        "adopt.md",
        # The only content change: the comment cites the generic registry test.
        "providers/agent_handoff.py",
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def test_agent_handoff_1_16__successor__changes_only_the_test_citation() -> None:
    """Preserve every runtime, template, policy, and historical byte outside the comment."""
    assert _SUCCESSOR.is_dir(), "the 1.16 candidate must exist before contract verification"

    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys()
    changed = {
        relative
        for relative in predecessor_files
        if successor_files[relative].read_bytes() != predecessor_files[relative].read_bytes()
    }
    assert changed == _SUCCESSOR_CHANGES
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o777 == predecessor.stat().st_mode & 0o777
        )

    assert (_SUCCESSOR / "resources/policy.toml").read_bytes() == (
        _PREDECESSOR / "resources/policy.toml"
    ).read_bytes()
    assert (_SUCCESSOR / "skills/agent-handoff/SKILL.md").read_bytes() == (
        _PREDECESSOR / "skills/agent-handoff/SKILL.md"
    ).read_bytes()


def test_agent_handoff_1_16__provider_comment__cites_the_generic_registry_test() -> None:
    """Pin the #196 fix: the cross-file contract comment names the catalog-wide test."""
    provider_text = (_SUCCESSOR / "providers/agent_handoff.py").read_text(encoding="utf-8")
    assert "tests/package_contract/test_provider_registry.py" in provider_text
    assert "tests/package_contract/test_agent_handoff_1_15.py" not in provider_text
    assert "tests/package_contract/test_agent_handoff_1_16.py" not in provider_text


def test_agent_handoff_1_16__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.16"
    assert indexed["1.16"].digest == integrity.aggregate_digest
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.16"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }
    assert roles["1.15"] == "retained"
    assert roles["1.16"] == "retained"
    assert "| [`agent-handoff`](agent-handoff/README.md) | active | 1.17 | default |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_agent_handoff_1_16__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: schema constants left pointing at 1.15."""
    successor_text = {
        relative: path.read_text(encoding="utf-8")
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".md", ".py", ".yaml"}
    }
    stale = {
        relative
        for relative, text in successor_text.items()
        if re.search(r"(?<!\d)1\.15(?!\d)", text)
        and relative not in {"adopt.md", "README.md", "providers/agent_handoff.py"}
    }
    assert stale == set(), "1.16 payload files still reference the 1.15 predecessor"


def test_agent_handoff_1_16__payload_projection__matches_successor() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
