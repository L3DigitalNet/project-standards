"""Package-contract proof for the Agent Handoff 1.15 openai-sidecar gating successor.

1.15 exists because `agents/openai.yaml` is a Codex-only skill descriptor: Claude
Code has no equivalent sidecar convention and never reads it, so installing a
`.claude/skills/agent-handoff/agents/openai.yaml` copy unconditionally served a
harness that cannot use it (issue #175, cross-package design drift found on the
v5.20.0 train). The cut removes that declared artifact entirely and gates the
remaining `.agents/skills/agent-handoff/agents/openai.yaml` copy on the consumer
having selected Codex, mirroring the pattern github-workflow 1.4 already uses for
the same descriptor. The provider carries the other half of that cut: its drift
registry is expanded per unit so the openai sidecar is demanded only under
`.agents/` and only for a Codex consumer. Nothing else changes: `SKILL.md`, the
hook, policy, templates, and every other artifact target are byte-identical to 1.14.

That registry-versus-payload agreement is asserted catalog-wide in
`test_provider_registry.py` (issue #194) rather than per family, so this file proves
only what is specific to the 1.15 cut.
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
_PREDECESSOR = _FAMILY / "versions/1.14"
_SUCCESSOR = _FAMILY / "versions/1.15"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.15"
_PREDECESSOR_DIGEST = "sha256:87f39801ca47f9c0575034e0d15b5c19f64f7ecb63f3e154fcd41e0b0341189f"
_SUCCESSOR_CHANGES = frozenset(
    {
        # Version constants every cut advances.
        "payload.toml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
        # Documentation of the gating change for readers who never open payload.toml.
        "README.md",
        "adopt.md",
        # The drift registry has to agree with the gated declaration (issue #175).
        "providers/agent_handoff.py",
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _artifacts(root: Path) -> dict[str, dict[str, object]]:
    manifest = tomllib.loads((root / "payload.toml").read_text(encoding="utf-8"))
    entries = cast("list[dict[str, object]]", manifest["artifacts"])
    return {cast("str", entry["id"]): entry for entry in entries}


def test_agent_handoff_1_15__successor__changes_only_the_gating_declaration() -> None:
    """Preserve every runtime, template, policy, and historical byte outside gating."""
    assert _SUCCESSOR.is_dir(), "the 1.15 candidate must exist before contract verification"

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


def test_agent_handoff_1_15__openai_sidecar__installs_only_under_codex_gating() -> None:
    """Pin the #175 fix: no Claude Code artifact, and the Codex copy is gated."""
    artifacts = _artifacts(_SUCCESSOR)

    assert "skill-openai-claude" not in artifacts

    skill_openai = artifacts["skill-openai"]
    assert skill_openai["target"] == ".agents/skills/agent-handoff/agents/openai.yaml"
    assert skill_openai["source"] == "skills/agent-handoff/agents/openai.yaml"
    assert skill_openai["when_any"] == [{"option": "harnesses", "contains": "codex"}]

    # The SKILL.md pair is unaffected: still two managed, ungated, byte-identical
    # copies, because Claude Code does read `.claude/skills/agent-handoff/SKILL.md`.
    skill_agents = artifacts["skill"]
    skill_claude = artifacts["skill-claude"]
    assert skill_agents["source"] == skill_claude["source"]
    assert skill_agents["digest"] == skill_claude["digest"]
    assert "when_any" not in skill_claude

    declared_targets = {cast("str", entry["target"]) for entry in artifacts.values()}
    assert ".claude/skills/agent-handoff/agents/openai.yaml" not in declared_targets

    # The disable mutation's affected-artifact list must not still name the removed
    # artifact id, or a disable would reference something the payload no longer
    # declares.
    manifest_text = (_SUCCESSOR / "payload.toml").read_text(encoding="utf-8")
    assert "artifact:skill-openai-claude" not in manifest_text


def test_agent_handoff_1_15__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.15"
    assert indexed["1.15"].digest == integrity.aggregate_digest
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.15"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }
    assert roles["1.14"] == "retained"
    assert roles["1.15"] == "retained"
    assert "| [`agent-handoff`](agent-handoff/README.md) | active | 1.17 | default |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_agent_handoff_1_15__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: schema constants left pointing at 1.14."""
    successor_text = {
        relative: path.read_text(encoding="utf-8")
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".md", ".py", ".yaml"}
    }
    stale = {
        relative
        for relative, text in successor_text.items()
        if re.search(r"(?<!\d)1\.14(?!\d)", text) and relative != "adopt.md"
    }
    assert stale == set(), "1.15 payload files still reference the 1.14 predecessor"


def test_agent_handoff_1_15__payload_projection__matches_successor() -> None:
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
