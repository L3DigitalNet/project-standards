"""Package-contract proof for the Markdown Frontmatter 1.12 dual skill-tree successor.

1.12 exists because Claude Code discovers project skills only under
`.claude/skills/` and has never read `.agents/skills/`, which is Codex's
convention, so the packaged skill was invisible to Claude Code (issue #170). The
cut adds a second installed copy of each skill file and changes nothing else —
no field, controlled vocabulary, rendered workflow byte, or existing target moves.

The exclusion assertion matters as much as the artifact pairing: this package
validates managed-document frontmatter, and its own installed `SKILL.md` carries
agent-skill metadata instead. A `.claude/**` tree that escaped the default
`exclude` would make the package fail its own corpus on files it just installed.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PREDECESSOR = _FAMILY / "versions/1.11"
_SUCCESSOR = _FAMILY / "versions/1.12"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-frontmatter/1.12"
_PREDECESSOR_DIGEST = "sha256:7eb63ac167668b5b0e0d5d79fbb83ae256c8bb73be5153e9ce81f9d8442fa32f"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        # The installed package summary names both trees for the consuming agent.
        "artifacts/agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/markdown-frontmatter/SKILL.md",
    }
)
_SKILL_PAIRS = (
    ("skill", "skill-claude"),
    ("skill-openai", "skill-openai-claude"),
    ("skill-new-doc-id", "skill-new-doc-id-claude"),
)


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


def test_markdown_frontmatter_1_12__successor__adds_only_the_claude_skill_tree() -> None:
    """Preserve every released byte, and add the second tree by declaration only."""
    assert _SUCCESSOR.is_dir(), "the 1.12 candidate must exist before contract verification"

    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert len(predecessor_files) == 39
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

    # The rendered validation workflows are the package's most drift-prone output;
    # 1.12 must not perturb a single byte of them.
    for relative in successor_files:
        if relative.endswith((".yml", ".yaml")):
            assert (
                successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
            )


def test_markdown_frontmatter_1_12__skill_artifacts__install_both_trees_from_one_source() -> None:
    artifacts = _artifacts(_SUCCESSOR)

    for agents_id, claude_id in _SKILL_PAIRS:
        agents_entry = artifacts[agents_id]
        claude_entry = artifacts[claude_id]
        assert agents_entry["source"] == claude_entry["source"]
        assert agents_entry["digest"] == claude_entry["digest"]
        assert agents_entry["policy"] == claude_entry["policy"] == "managed"
        assert agents_entry.get("mode") == claude_entry.get("mode")
        assert claude_entry["target"] == agents_entry["target"].replace(
            ".agents/skills/", ".claude/skills/", 1
        )

    # `new-doc-id` is executable; a copy installed 0644 would be a silently broken
    # helper rather than a visible failure.
    assert artifacts["skill-new-doc-id-claude"]["mode"] == "0755"


def test_markdown_frontmatter_1_12__default_exclude__covers_both_installed_trees() -> None:
    schema = json.loads((_SUCCESSOR / "config.schema.json").read_text(encoding="utf-8"))
    excluded = schema["properties"]["exclude"]["default"]

    assert ".agents/**" in excluded
    assert ".claude/**" in excluded


def test_markdown_frontmatter_1_12__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.12"
    assert indexed["1.12"].digest == integrity.aggregate_digest
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.12"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-frontmatter"
    }
    assert roles["1.11"] == "retained"
    assert roles["1.12"] == "default"
    assert (
        "| [`markdown-frontmatter`](markdown-frontmatter/README.md) | active | 1.12 | "
        "default | consumer |"
    ) in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_markdown_frontmatter_1_12__payload_projection__matches_successor() -> None:
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
