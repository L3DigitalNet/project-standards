"""Package-contract proof for the GitHub Workflow 1.5 guidance cut.

1.5 does two things no earlier cut in this family did: it removes a published
subcommand (`ledger`, and with it the generated `docs/GH-WORKFLOWS.md`), and it
rewrites the skill guidance against measured session behavior instead of adding to
it. Both are failure-prone in the same direction — a copied payload that keeps the
predecessor's prose still reads as correct, and a shrunk document silently grows
back on the next edit — so the assertions below pin the *budgets and the absences*,
not the wording.

The removal itself is proven where it lives: the binary's registry is asserted in
cmd/gh-workflow's own tests, and this file only checks that the payload's shipped
bytes and prose agree with it. The provider's managed-target registry is likewise
proven where it lives — `test_provider_registry.py` asserts that agreement for every
advertised payload (issue #194), so nothing here restates it per family.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from types import ModuleType
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.module_loading import load_module_from_path
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_PREDECESSOR = _FAMILY / "versions/1.4"
_SUCCESSOR = _FAMILY / "versions/1.5"
_PROJECTION = _ROOT / "src/project_standards/payloads/github-workflow/1.5"
_PREDECESSOR_DIGEST = "sha256:6bd63f74d43baf8a49bc87c28b6a25fb1aa2d0bfdf185229b74e7b685dee522e"
_BUILD_SCRIPT = _ROOT / "scripts/build-gh-workflow.sh"
_TOOL_BINARY_SOURCE = "skills/github-workflow/bin/gh-workflow"
_SKILL_SOURCE = "skills/github-workflow/SKILL.md"
_VOCABULARY_SOURCE = "skills/github-workflow/references/field-vocabulary.md"

# The eight that survive, in registration order from `gh-workflow help`.
_SUBCOMMANDS = ("audit", "check", "close", "new", "receipt", "reopen", "set", "summary")

# Budgets, not targets. SKILL.md's whole design claim is that one read lands the
# complete routing surface; field-vocabulary.md's is that only the two vocabularies
# the tool cannot state in a refusal are worth standing context. Both regress by
# accretion, one paragraph at a time, which is why they are asserted as ceilings.
_SKILL_MAX_LINES = 70
_VOCABULARY_MAX_LINES = 30
# NFR-006 1.11 (D10, owner decision 2026-08-26): the byte ceilings were raised from
# 6,500/2,000 B. The original figures assumed ~93 B/line; the content FR-024 and
# FR-005 mandate for these files runs ~160 B/line, so 1.5's measured output
# (11,176 B / 2,918 B) exceeded the original ceilings despite meeting the line
# ceilings. Line ceilings are unchanged.
_SKILL_MAX_BYTES = 12000
_VOCABULARY_MAX_BYTES = 3200

# The managed block's length varies with the organization login, so the assertion is
# a ceiling. The rendered body measures 2,183 B for `L3DigitalNet`.
_BLOCK_MAX_BYTES = 2400


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _artifacts(root: Path) -> dict[str, dict[str, str]]:
    manifest = tomllib.loads((root / "payload.toml").read_text(encoding="utf-8"))
    entries = cast("list[dict[str, str]]", manifest["artifacts"])
    return {entry["id"]: entry for entry in entries}


def _text(relative: str) -> str:
    return (_SUCCESSOR / relative).read_text(encoding="utf-8")


def _load_provider(name: str) -> ModuleType:
    """Import this version's provider by path.

    The provider is payload bytes rather than an importable module, so it is loaded
    from its declared path; importing `standards....providers.gh_workflow` would
    depend on a package layout the payload deliberately does not have.
    """
    return load_module_from_path(name, _SUCCESSOR / "providers/gh_workflow.py")


def _block_body() -> str:
    """Render the managed block the way the control plane does, without a reconcile."""
    module = _load_provider("gh_workflow_1_5")
    return cast("str", module._block_body("ExampleOrg"))  # pyright: ignore[reportPrivateUsage]


def test_github_workflow_1_5__predecessor__keeps_its_released_bytes() -> None:
    """1.4 is published, so the cut may only add a sibling directory."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST


def test_github_workflow_1_5__identity__is_complete_and_indexed() -> None:
    """1.5's own rows, which stay exact after 1.6 took the family default."""
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.5"
    assert indexed["1.5"].digest == integrity.aggregate_digest
    # Published predecessor rows are immutable selectors, not moving aliases.
    assert indexed["1.4"].digest.value == _PREDECESSOR_DIGEST

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "github-workflow"
    }
    assert roles["1.4"] == "retained"
    # 1.6 succeeded 1.5 as the family default; a published version's row only ever
    # moves from `default` to `retained`, never back and never off the catalog.
    assert roles["1.5"] == "retained"
    assert "| [`github-workflow`](github-workflow/README.md) | active | 1.5 | retained |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_github_workflow_1_5__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.4."""
    stale = {
        relative
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".yaml"}
        and re.search(r"(?<!\d)1\.4(?!\d)", path.read_text(encoding="utf-8"))
    }
    assert stale == set(), "1.5 payload files still reference the 1.4 predecessor"


def test_github_workflow_1_5__tool_binary__is_declared_for_this_version() -> None:
    """Pin the payload's declaration of the committed bytes.

    The build-script half of the original three-way contract moved to the 1.6 proof
    when that cut retargeted `scripts/build-gh-workflow.sh`: the script can only
    reproduce the current version, by design (see its own header), so 1.5's bytes are
    held by the declared digest here and by the release baseline comparison.
    """
    committed = _SUCCESSOR / _TOOL_BINARY_SOURCE
    digest = f"sha256:{hashlib.sha256(committed.read_bytes()).hexdigest()}"

    for artifact_id in ("tool-binary", "tool-binary-claude"):
        entry = _artifacts(_SUCCESSOR)[artifact_id]
        assert entry["source"] == _TOOL_BINARY_SOURCE
        assert entry["digest"] == digest
        assert entry["mode"] == "0755"
    assert committed.stat().st_mode & 0o777 == 0o755

    # A cut that advertised a removed subcommand while shipping the predecessor's
    # executable would pass every prose assertion below.
    assert committed.read_bytes() != (_PREDECESSOR / _TOOL_BINARY_SOURCE).read_bytes()


def test_github_workflow_1_5__payload_prose__describes_eight_subcommands_and_no_ledger() -> None:
    """The removal is consumer-visible, so no shipped byte may still promise the feature.

    The split is between guidance and history. The skill, its references, and the
    Codex companion are read *to act*, so a surviving mention there routes an agent
    at a subcommand that exits 2. The three package documents are read to understand
    a version, so they must state the removal rather than omit it — a copied
    paragraph nobody reread is exactly how this cut fails.
    """
    guidance = {
        relative: path
        for relative, path in _files(_SUCCESSOR).items()
        if relative.startswith("skills/") and path.suffix in {".md", ".yaml"}
    }
    assert _SKILL_SOURCE in guidance
    for relative, path in guidance.items():
        text = path.read_text(encoding="utf-8")
        assert "ledger" not in text.lower(), f"{relative} still routes at the ledger"
        assert "GH-WORKFLOWS" not in text, f"{relative} still names the generated ledger file"

    for relative in ("README.md", "agent-summary.md", "adopt.md"):
        text = _text(relative)
        assert "ledger" in text.lower() and any(
            marker in text for marker in ("is gone", "removes", "removed")
        ), f"{relative} does not tell an upgrading consumer the ledger is gone"
        assert "nine subcommands" not in text

    for relative in ("README.md", "agent-summary.md"):
        text = _text(relative)
        assert "eight" in text and "subcommands" in text, relative
        for subcommand in _SUBCOMMANDS:
            assert f"`{subcommand}`" in text, f"{relative} omits `{subcommand}`"


def test_github_workflow_1_5__skill__is_one_read_carrying_the_whole_flag_surface() -> None:
    """SKILL.md's budget, its completeness claim, and the two mandates 1.5 dropped."""
    skill = _text(_SKILL_SOURCE)
    lines = skill.splitlines()

    assert len(lines) <= _SKILL_MAX_LINES
    assert len(skill.encode("utf-8")) <= _SKILL_MAX_BYTES
    assert "  version: '1.5'" in skill
    # A hand-maintained count goes stale silently; assert it against the file itself.
    declared = re.search(r"^  lines: (\d+)$", skill, re.MULTILINE)
    assert declared is not None and int(declared.group(1)) == len(lines)

    for subcommand in _SUBCOMMANDS:
        assert f"`{subcommand} " in skill or f"`{subcommand}`" in skill, subcommand
    # F5: `set --type` is the retype route and was missed in a 157-line file.
    assert "`set --issue N --type T`" in skill
    # F6: the CI-wait forms agents reinvented as poll loops.
    assert "gh pr checks N --watch --fail-fast" in skill
    assert "gh run watch RUN_ID --exit-status" in skill

    assert "This table is complete" in skill
    # F8: the two mandates the corpus showed costing calls and preventing nothing.
    assert "Check the binary once per session" not in skill
    assert "consult the tool's own help" not in skill
    assert "frozen at 1.1" not in skill

    # The relaxed self-definition rules (owner decision, 2026-08-26).
    assert "you also admit it" in skill
    assert "Unattended agent" in skill


def test_github_workflow_1_5__field_vocabulary__keeps_only_what_a_refusal_cannot_say() -> None:
    """The two vocabularies that bind before the tool can refuse anything."""
    vocabulary = _text(_VOCABULARY_SOURCE)

    assert len(vocabulary.splitlines()) <= _VOCABULARY_MAX_LINES
    assert len(vocabulary.encode("utf-8")) <= _VOCABULARY_MAX_BYTES
    assert "## Workflow" in vocabulary
    assert "## Field pinning" in vocabulary
    for value in ("Inbox", "Needs definition", "Ready", "In progress", "Blocked", "Dropped"):
        assert f"**{value}**" in vocabulary
    # Deleted: every value set the binary names in its own refusal.
    assert "## Priority" not in vocabulary
    assert "## Fields not to create" not in vocabulary
    # The review-depth ladder moved rather than vanished.
    assert "R4" in _text("skills/github-workflow/references/review-checklist.md")


def test_github_workflow_1_5__managed_block__routes_without_a_skill_load() -> None:
    """The block is the only package text a delegated worker is guaranteed to see."""
    body = _block_body()

    assert len(body.encode("utf-8")) <= _BLOCK_MAX_BYTES
    assert "`ExampleOrg`" in body, "the organization must stay config-rendered (NFR-001)"
    for subcommand in _SUBCOMMANDS:
        assert subcommand in body, subcommand
    for rule in (
        "admit work to `Ready` yourself",
        "`Unattended agent` is the operator's grant",
        "Never create, rename, or retire an organization issue type",
        "links the issue that governs it",
        "Keep terminal state synchronized",
        "becomes an issue before the session ends",
    ):
        assert rule in body, rule
    # The escaped pipe keeps the alternation inside one table cell.
    assert "--as done\\|dropped" in body


def test_github_workflow_1_5__openai_companion__is_declared_under_agents_only() -> None:
    """Issue #175: the `.claude/` copy was bytes no harness could read."""
    artifacts = _artifacts(_SUCCESSOR)

    assert "skill-openai-claude" not in artifacts
    entry = artifacts["skill-openai"]
    assert entry["target"] == ".agents/skills/github-workflow/agents/openai.yaml"
    assert entry["when_any"] == [{"option": "harnesses", "contains": "codex"}]
    # Every other skill file still lands in both trees.
    assert artifacts["skill-claude"]["target"] == ".claude/skills/github-workflow/SKILL.md"


def test_github_workflow_1_5__upgrade_provider__reports_the_orphaned_ledger_file() -> None:
    """Nothing deletes a consumer file silently, so the upgrade plan has to say it."""
    module = _load_provider("gh_workflow_1_5_upgrade")

    cases: tuple[tuple[str, dict[str, object]], ...] = (
        ("unobserved", {}),
        ("observed", {"docs/GH-WORKFLOWS.md": {"kind": "regular"}}),
    )
    for name, snapshots in cases:
        diagnostic = cast(
            "dict[str, object]",
            module._orphaned_ledger_diagnostic(snapshots),  # pyright: ignore[reportPrivateUsage]
        )
        assert diagnostic["severity"] == "warning", name
        assert diagnostic["path"] == "docs/GH-WORKFLOWS.md", name
        assert diagnostic["refusal"] is False, name
        assert "delete it" in cast("str", diagnostic["message"]), name


def test_github_workflow_1_5__payload_projection__matches_successor() -> None:
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
