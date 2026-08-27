"""Package-contract proof for the Project Toolbox 1.1 openai-sidecar gating successor.

1.1 exists because `agents/openai.yaml` is a Codex-only skill descriptor: Claude
Code has no equivalent sidecar convention and never reads it, so installing a
`.claude/skills/project-toolbox/agents/openai.yaml` copy unconditionally served a
harness that cannot use it (issue #175, cross-package design drift found on the
v5.20.0 train). 1.0 shipped before this family had any harness-selection option,
so 1.1 adopts a `harnesses` config option — copied from `agent-handoff@1.15`'s
definition — and removes the declared Claude artifact for `openai.yaml` while
gating the remaining Codex copy on `harnesses` containing `codex`. `SKILL.md` is
unaffected: it still installs to both trees unconditionally, since Claude Code
does read `.claude/skills/project-toolbox/SKILL.md`. The default selects both
harnesses, so a repository that sets nothing keeps the Codex `openai.yaml` copy
and only loses the Claude-side one on reconcile.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-toolbox"
_PREDECESSOR = _FAMILY / "versions/1.0"
_SUCCESSOR = _FAMILY / "versions/1.1"
_PROJECTION = _ROOT / "src/project_standards/payloads/project-toolbox/1.1"
_PREDECESSOR_DIGEST = "sha256:48020eacd25a34578b6cc9c2cd7314af14bc6a808bd6d21531df29726c754bf8"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "config.schema.json",
        "payload.toml",
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


def test_project_toolbox_1_1__successor__changes_only_the_gating_declaration() -> None:
    """Preserve every released byte outside the option addition and its docs."""
    assert _SUCCESSOR.is_dir(), "the 1.1 candidate must exist before contract verification"

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

    # The workflow documents and both skill bodies are untouched: a gating-only
    # option addition must not perturb a single byte of the operator-facing text.
    assert (_SUCCESSOR / "workflows/repo-housekeeping.md").read_bytes() == (
        _PREDECESSOR / "workflows/repo-housekeeping.md"
    ).read_bytes()
    assert (_SUCCESSOR / "workflows/drift-detection.md").read_bytes() == (
        _PREDECESSOR / "workflows/drift-detection.md"
    ).read_bytes()
    assert (_SUCCESSOR / "skills/project-toolbox/SKILL.md").read_bytes() == (
        _PREDECESSOR / "skills/project-toolbox/SKILL.md"
    ).read_bytes()
    assert (_SUCCESSOR / "skills/project-toolbox/agents/openai.yaml").read_bytes() == (
        _PREDECESSOR / "skills/project-toolbox/agents/openai.yaml"
    ).read_bytes()


def test_project_toolbox_1_1__harnesses_option__mirrors_agent_handoff() -> None:
    """The copied option must match agent-handoff@1.15's definition verbatim.

    Only `type`, `items`, `uniqueItems`, and `default` are compared — the `allOf`
    conditional agent-handoff ties to its own `startup` option has no counterpart
    here and is correctly not copied.
    """
    schema = json.loads((_SUCCESSOR / "config.schema.json").read_text(encoding="utf-8"))
    ah_schema = json.loads(
        (_ROOT / "standards/agent-handoff/versions/1.15/config.schema.json").read_text(
            encoding="utf-8"
        )
    )
    harnesses = cast("dict[str, object]", schema["properties"]["harnesses"])
    ah_harnesses = cast("dict[str, object]", ah_schema["properties"]["harnesses"])

    for key in ("type", "items", "uniqueItems"):
        assert harnesses[key] == ah_harnesses[key]
    # Both harnesses selected by default: a consumer that sets nothing must see
    # no behavior change except the dropped `.claude/.../openai.yaml` artifact.
    assert harnesses["default"] == ["claude-code", "codex"] == ah_harnesses["default"]


def test_project_toolbox_1_1__openai_sidecar__installs_only_under_codex_gating() -> None:
    """Pin the #175 fix: no Claude Code artifact, and the Codex copy is gated."""
    artifacts = _artifacts(_SUCCESSOR)

    assert "skill-openai-claude" not in artifacts

    skill_openai = artifacts["skill-openai"]
    assert skill_openai["target"] == ".agents/skills/project-toolbox/agents/openai.yaml"
    assert skill_openai["source"] == "skills/project-toolbox/agents/openai.yaml"
    assert skill_openai["when_any"] == [{"option": "harnesses", "contains": "codex"}]

    # SKILL.md is unaffected: still an ungated, byte-identical pair.
    skill_agents = artifacts["skill"]
    skill_claude = artifacts["skill-claude"]
    assert skill_agents["source"] == skill_claude["source"]
    assert skill_agents["digest"] == skill_claude["digest"]
    assert "when_any" not in skill_claude
    assert skill_claude["target"] == cast("str", skill_agents["target"]).replace(
        ".agents/skills/", ".claude/skills/", 1
    )

    declared_targets = {cast("str", entry["target"]) for entry in artifacts.values()}
    assert ".claude/skills/project-toolbox/agents/openai.yaml" not in declared_targets

    # The disable mutation's affected-artifact list must not still name the
    # removed artifact id, or a disable would reference something the payload
    # no longer declares.
    manifest_text = (_SUCCESSOR / "payload.toml").read_text(encoding="utf-8")
    assert "artifact:skill-openai-claude" not in manifest_text


def test_project_toolbox_1_1__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.1"
    assert indexed["1.1"].digest == integrity.aggregate_digest

    # `[[migrations]]` tracks a legacy pre-catalog state, not a package-version
    # bump; this family has never had one, so it stays empty even now that 1.1
    # has an in-repo predecessor (payload.toml's own comment records this).
    assert manifest.migrations == []

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "project-toolbox"
    }
    assert roles["1.0"] == "retained"
    assert roles["1.1"] == "default"
    assert (
        "| [`project-toolbox`](project-toolbox/README.md) | active | 1.1 | default | consumer |"
    ) in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_project_toolbox_1_1__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: schema constants left pointing at 1.0."""
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    successor_text = {
        relative: path.read_text(encoding="utf-8")
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".md", ".yaml", ".yml"}
    }
    # Excluded, each for a documented reason rather than an unaudited gap:
    #   adopt.md / README.md — narrate the 1.0 -> 1.1 history in prose.
    #   payload.toml         — `schema_version = "1.0"` is the payload-manifest
    #                          schema's own version, unrelated to the package.
    #   skills/.../SKILL.md  — the skill's `metadata.version` is the skill's own
    #                          semver, independent of the package version (it
    #                          stays constant across ordinary package cuts too).
    _EXPECTED_1_0_MENTIONS = {
        "adopt.md",
        "README.md",
        "payload.toml",
        "skills/project-toolbox/SKILL.md",
    }
    stale = {
        relative
        for relative, text in successor_text.items()
        if re.search(r"(?<!\d)1\.0(?!\d)", text) and relative not in _EXPECTED_1_0_MENTIONS
    }
    assert stale == set(), "1.1 payload files still reference the 1.0 predecessor"


def test_project_toolbox_1_1__payload_projection__matches_successor() -> None:
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
