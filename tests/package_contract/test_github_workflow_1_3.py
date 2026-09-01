"""Package-contract proof for the GitHub Workflow 1.3 dual skill-tree successor.

1.3 exists because Claude Code discovers project skills only under
`.claude/skills/` and has never read `.agents/skills/`, which is Codex's
convention, so the packaged skill was invisible to Claude Code (issue #170). The
cut adds a second installed copy of each skill file and changes nothing else.

This family is the one where the shared-source contract earns its keep: the
`gh-workflow` binary is ~9.7 MB, so declaring the second target against the same
source is what keeps the payload from doubling for bytes that are identical by
contract. `test_github_workflow_1_3__successor__adds_no_packaged_file` is the
assertion that would catch a regression back to a duplicated on-disk copy.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path
from types import ModuleType
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_PREDECESSOR = _FAMILY / "versions/1.2"
_SUCCESSOR = _FAMILY / "versions/1.3"
_PROJECTION = _ROOT / "src/project_standards/payloads/github-workflow/1.3"
_PREDECESSOR_DIGEST = "sha256:06041b632e15eee8258d7eaf311dfd0560f15d54d34ed2ac44076a069228d13f"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        # Issue #171: the artifact registry covers both installed trees.
        "providers/gh_workflow.py",
        "schemas/provider-input.schema.json",
        # Frontmatter `version` and the platform sentence both name the package
        # version; the binary itself is byte-identical to 1.1's.
        "skills/github-workflow/SKILL.md",
    }
)
_TOOL_BINARY_SOURCE = "skills/github-workflow/bin/gh-workflow"


def _load_provider(relative: str, name: str) -> ModuleType:
    """Import a payload provider by path.

    Payload providers are delivered bytes, not importable package modules, so the
    control plane loads them by location too — reaching them any other way would
    test a copy the runtime never executes.
    """
    path = _SUCCESSOR / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _artifacts(root: Path) -> dict[str, dict[str, str]]:
    manifest = tomllib.loads((root / "payload.toml").read_text(encoding="utf-8"))
    entries = cast("list[dict[str, str]]", manifest["artifacts"])
    return {entry["id"]: entry for entry in entries}


def test_github_workflow_1_3__successor__adds_no_packaged_file() -> None:
    """Preserve every released byte, and add the second tree by declaration only."""
    assert _SUCCESSOR.is_dir(), "the 1.3 candidate must exist before contract verification"

    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert len(predecessor_files) == 20
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

    # The 9.7 MB binary is the reason a duplicated source tree was rejected.
    assert (
        successor_files[_TOOL_BINARY_SOURCE].read_bytes()
        == predecessor_files[_TOOL_BINARY_SOURCE].read_bytes()
    )


def test_github_workflow_1_3__skill_artifacts__install_both_trees_from_one_source() -> None:
    artifacts = _artifacts(_SUCCESSOR)
    agents_ids = [
        artifact_id
        for artifact_id, entry in artifacts.items()
        if entry["target"].startswith(".agents/skills/github-workflow/")
    ]

    assert len(agents_ids) == 9
    for agents_id in agents_ids:
        agents_entry = artifacts[agents_id]
        claude_entry = artifacts[f"{agents_id}-claude"]
        assert agents_entry["source"] == claude_entry["source"]
        assert agents_entry["digest"] == claude_entry["digest"]
        assert agents_entry["policy"] == claude_entry["policy"] == "managed"
        # Mode and harness gating travel with the pair: the Codex companion is
        # conditional and the binary is 0755 in both trees, so a copy that dropped
        # either would install an unusable or unexpected file.
        assert agents_entry.get("mode") == claude_entry.get("mode")
        assert agents_entry.get("when_any") == claude_entry.get("when_any")
        assert claude_entry["target"] == agents_entry["target"].replace(
            ".agents/skills/", ".claude/skills/", 1
        )

    assert artifacts["tool-binary-claude"]["mode"] == "0755"


def test_github_workflow_1_3__identity__is_complete_and_retained() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.3"
    assert indexed["1.3"].digest == integrity.aggregate_digest

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "github-workflow"
    }
    assert roles["1.2"] == "retained"
    # Superseded by 1.4 but still advertised: withdrawing an advertised package is a
    # catalog-major transition (ADR 0024), so the entry stays and only the role moves.
    assert roles["1.3"] == "retained"


def test_github_workflow_1_3__size_guard_guidance__exempts_both_binary_copies() -> None:
    """Issue #170: one exemption per installed copy, still path-anchored."""
    for guide in (_SUCCESSOR / "adopt.md", _FAMILY / "adopt.md"):
        text = guide.read_text(encoding="utf-8")
        assert r"exclude: ^\.(agents|claude)/skills/github-workflow/bin/gh-workflow$" in text
        assert ".claude/skills/github-workflow/bin/gh-workflow (9695 KB) exceeds 1024 KB." in text
        # The two rejected escapes stay named as rejected.
        assert "--maxkb" in text
        assert "--no-verify" in text


def test_github_workflow_1_3__payload_projection__matches_successor() -> None:
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


def test_github_workflow_1_3__provider_registry__covers_every_declared_skill_target() -> None:
    """Issue #171: the provider's drift table and the payload cannot drift apart.

    The provider expands one relative-path table over both skill roots, so a root
    dropped from `_SKILL_ROOTS` — the exact shape of the original defect — silently
    stops reporting drift for a whole tree while every other test still passes. This
    compares its expanded keys against the payload's own declarations, which is the
    only place the two representations meet.
    """
    provider = _load_provider("providers/gh_workflow.py", "gh_workflow_1_3")
    declared = {
        artifact["target"]: artifact["id"]
        for artifact in _artifacts(_SUCCESSOR).values()
        if "/skills/github-workflow/" in artifact["target"]
    }
    registry = cast(
        "dict[str, tuple[str, str | None, str | None]]",
        provider._ARTIFACTS,  # pyright: ignore[reportPrivateUsage]  # payload-internal table
    )

    assert {path: entry[0] for path, entry in registry.items()} == declared


def test_github_workflow_1_3__provider_registry__pairs_agree_on_mode_and_gate() -> None:
    """A copy that lost its harness gate or its mode would install wrong, not absent."""
    provider = _load_provider("providers/gh_workflow.py", "gh_workflow_1_3_pairs")
    registry = cast(
        "dict[str, tuple[str, str | None, str | None]]",
        provider._ARTIFACTS,  # pyright: ignore[reportPrivateUsage]  # payload-internal table
    )

    for path, (identity, mode, gate) in registry.items():
        if not path.startswith(".agents/"):
            continue
        twin_path = path.replace(".agents/skills/", ".claude/skills/", 1)
        twin_identity, twin_mode, twin_gate = registry[twin_path]
        assert twin_identity == f"{identity}-claude"
        assert (twin_mode, twin_gate) == (mode, gate)
