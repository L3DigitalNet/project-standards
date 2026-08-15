"""Package-contract proof for the Agent Handoff 1.13 dual skill-tree successor.

1.13 exists because Claude Code discovers project skills only under
`.claude/skills/` and has never read `.agents/skills/`, which is Codex's
convention, so the packaged skill was invisible to Claude Code (issue #170). The
cut adds a second installed copy of each skill file and changes nothing else.

Two properties carry the weight here. The exhaustive predecessor comparison
guards against rewriting historical migration evidence while adding artifacts.
The paired-artifact assertion pins the actual contract: the two targets must
resolve to one packaged source and one digest, because a pair that drifts would
serve different instructions to the two harnesses without either copy looking
wrong on its own.
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.12"
_SUCCESSOR = _FAMILY / "versions/1.13"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.13"
_PREDECESSOR_DIGEST = "sha256:176dceeca8b02df1eebd468eec26bc0e2713ed17cd67f4ff0651646795e43b7f"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        # SKILL.md gains the second owned tree in its ownership list, and the
        # provider-resource copy is byte-locked to it.
        "provider-resources/managed/skill.md",
        # Issue #171: the drift and upgrade registries cover both installed trees.
        "providers/agent_handoff.py",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
        "skills/agent-handoff/SKILL.md",
    }
)
# Each pair is (Codex artifact id, Claude Code artifact id).
_SKILL_PAIRS = (("skill", "skill-claude"), ("skill-openai", "skill-openai-claude"))


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def _artifacts(root: Path) -> dict[str, dict[str, str]]:
    manifest = tomllib.loads((root / "payload.toml").read_text(encoding="utf-8"))
    entries = cast("list[dict[str, str]]", manifest["artifacts"])
    return {entry["id"]: entry for entry in entries}


def test_agent_handoff_1_13__successor__adds_only_the_claude_skill_tree() -> None:
    """Preserve every runtime and historical byte outside the approved paths."""
    assert _SUCCESSOR.is_dir(), "the 1.13 candidate must exist before contract verification"

    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert len(predecessor_files) == 43
    # No packaged file is added: the second tree is declared, never duplicated on
    # disk, which is the whole reason the payload contract had to allow one source
    # to back several targets.
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


def test_agent_handoff_1_13__skill_artifacts__install_both_trees_from_one_source() -> None:
    artifacts = _artifacts(_SUCCESSOR)

    for agents_id, claude_id in _SKILL_PAIRS:
        agents_entry = artifacts[agents_id]
        claude_entry = artifacts[claude_id]
        assert agents_entry["source"] == claude_entry["source"]
        assert agents_entry["digest"] == claude_entry["digest"]
        assert agents_entry["policy"] == claude_entry["policy"] == "managed"
        assert agents_entry.get("mode") == claude_entry.get("mode")
        assert agents_entry["target"].startswith(".agents/skills/agent-handoff/")
        assert claude_entry["target"] == agents_entry["target"].replace(
            ".agents/skills/", ".claude/skills/", 1
        )

    # Every declared skill source must resolve to real bytes matching its digest;
    # validate_payload_integrity is what proves the shared-source declaration is
    # accepted rather than silently collapsing one of the pair.
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    inventory = {entry.path.normalized.as_posix() for entry in integrity.inventory}
    assert "skills/agent-handoff/SKILL.md" in inventory


def test_agent_handoff_1_13__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.13"
    assert indexed["1.13"].digest == integrity.aggregate_digest
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.13"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }
    assert roles["1.12"] == "retained"
    assert roles["1.13"] == "default"
    assert "| [`agent-handoff`](agent-handoff/README.md) | active | 1.13 | default |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_agent_handoff_1_13__payload_projection__matches_successor() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def _load_provider(name: str) -> ModuleType:
    """Import the payload provider by path, the way the control plane loads it."""
    spec = importlib.util.spec_from_file_location(name, _SUCCESSOR / "providers/agent_handoff.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_handoff_1_13__provider_registries__cover_both_installed_skill_trees() -> None:
    """Issue #171: drift and upgrade coverage reaches the `.claude/` copy too.

    Before the fix `_MANAGED` held only the `.agents/` paths, so a tampered
    `.claude/skills/agent-handoff/SKILL.md` produced no finding at all — a silence
    indistinguishable from a clean tree. Both maps are asserted because they answer
    different questions: `_MANAGED` decides what drift-check inspects, and
    `_UPGRADE_TARGETS` decides what an operator is allowed to repair.
    """
    provider = _load_provider("agent_handoff_1_13")
    managed = cast("dict[str, str]", provider._MANAGED)  # pyright: ignore[reportPrivateUsage]
    upgrades = cast(
        "dict[str, tuple[str, str]]",
        provider._UPGRADE_TARGETS,  # pyright: ignore[reportPrivateUsage]
    )
    declared = {artifact["target"] for artifact in _artifacts(_SUCCESSOR).values()}

    skill_targets = {path for path in managed if "/skills/agent-handoff/" in path}
    assert skill_targets == {path for path in declared if "/skills/agent-handoff/" in path}
    # Both copies compare against the same packaged resource: that shared expectation
    # is what turns an accidental divergence between the trees into a finding.
    for path in skill_targets:
        twin = (
            path.replace(".agents/skills/", ".claude/skills/", 1)
            if path.startswith(".agents/")
            else path.replace(".claude/skills/", ".agents/skills/", 1)
        )
        assert managed[twin] == managed[path]

    assert set(upgrades) == skill_targets
    assert {mode for _resource, mode in upgrades.values()} == {"0644"}

    # Every registry path must still be something the payload actually installs.
    assert set(managed) <= declared
