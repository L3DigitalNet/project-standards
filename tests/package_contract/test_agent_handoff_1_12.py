"""Package-contract proof for the Agent Handoff 1.12 documentation successor.

The cut corrects two current-behavior instructions without changing a runtime
surface. The exhaustive predecessor comparison is the guard against accidentally
rewriting historical migration evidence or turning this candidate into an implicit
activation.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.11"
_SUCCESSOR = _FAMILY / "versions/1.12"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.12"
_PREDECESSOR_DIGEST = "sha256:570cc7cf345fc953d535e1fab8f7ad52bcea5d81eaf3d5a3641d1b40580c9ea2"
_HOOK_SOURCE = "hooks/session-start/session-start"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "payload.toml",
        "resources/legacy-migration.md",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_LEGACY_INTEGRATION_RESOURCES = {
    "legacy-claude-source": "resources/integration/claude-session-start.json",
    "legacy-codex-source": "resources/integration/codex-session-start.toml",
}


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def _manifest_resources(root: Path) -> dict[str, tuple[str, str]]:
    manifest = tomllib.loads((root / "payload.toml").read_text(encoding="utf-8"))
    resources = cast("list[dict[str, str]]", manifest["resources"])
    return {resource["id"]: (resource["role"], resource["path"]) for resource in resources}


def test_agent_handoff_1_12__successor__has_exact_documentation_delta() -> None:
    """Preserve every runtime and historical byte outside the approved six paths."""
    assert _SUCCESSOR.is_dir(), "the 1.12 candidate must exist before contract verification"

    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert len(predecessor_files) == 43
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

    predecessor_resources = _manifest_resources(_PREDECESSOR)
    successor_resources = _manifest_resources(_SUCCESSOR)
    for resource_id, path in _LEGACY_INTEGRATION_RESOURCES.items():
        assert successor_resources[resource_id] == ("legacy-reference", path)
        assert successor_resources[resource_id] == predecessor_resources[resource_id]
        assert (_SUCCESSOR / path).read_bytes() == (_PREDECESSOR / path).read_bytes()


def test_agent_handoff_1_12__identity__is_complete_and_retained() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.12"
    assert indexed["1.12"].digest == integrity.aggregate_digest
    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        "legacy:v4-agent-handoff"
    }
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.12"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }
    assert roles["1.11"] == "retained"
    assert roles["1.12"] == "retained"
    assert roles["1.13"] == "retained"
    assert roles["1.14"] == "retained"
    # Which later version currently holds `default` is not asserted here: that role
    # moves on every later cut in this family. See test_catalog_roles.py for the
    # family-wide, catalog-derived invariant.
    assert "| [`agent-handoff`](agent-handoff/README.md) | active | 1.12 | retained |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_agent_handoff_1_12__guidance__pins_the_two_approved_corrections() -> None:
    adoption = (_SUCCESSOR / "adopt.md").read_text(encoding="utf-8")
    legacy = (_SUCCESSOR / "resources/legacy-migration.md").read_text(encoding="utf-8")

    assert adoption.splitlines()[0] == "# Adopt Agent Handoff 1.12"
    assert "clean V5-native" in adoption
    assert "unchanged superseded" in adoption
    assert "CP-MODIFIED-MANAGED" in adoption
    assert "git rm .agents/hooks/agent-handoff/session_start.py" not in adoption
    assert "created_container=False" not in adoption

    current_target = (
        "confirming both selected harnesses reference `.agents/hooks/agent-handoff/session-start`"
    )
    assert legacy.count(current_target) == 1
    assert legacy.count("`.claude/hooks/session_start.py` or `.codex/hooks/session_start.py`") == 1
    assert "reference `.agents/hooks/agent-handoff/session_start.py`" not in legacy


def test_agent_handoff_1_12__launcher_and_projection__preserve_package_bytes() -> None:
    launcher = _SUCCESSOR / _HOOK_SOURCE
    assert launcher.read_bytes() == (_PREDECESSOR / _HOOK_SOURCE).read_bytes()
    assert launcher.stat().st_mode & 0o111

    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def test_agent_handoff_1_12__mutable_navigation__names_the_new_authority() -> None:
    expected_links = {
        _FAMILY / "README.md": "versions/1.15/README.md",
        _FAMILY / "adopt.md": "versions/1.15/adopt.md",
        _FAMILY / "agent-summary.md": "versions/1.15/agent-summary.md",
    }
    for path, expected_link in expected_links.items():
        content = path.read_text(encoding="utf-8")
        assert expected_link in content
        assert "versions/1.12/" not in content
