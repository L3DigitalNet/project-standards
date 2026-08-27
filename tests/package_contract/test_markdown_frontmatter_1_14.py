"""Package-contract proof for the Markdown Frontmatter 1.14 reach-and-provenance successor.

1.14 answers the 2026-08-26 skill usage review. Three findings drive payload
bytes. F1: the package contributed only to the CI caller, so a consumer
repository carried no standing statement that its Markdown is governed — the
skill reached roughly 5% of the sessions that wrote frontmatter. 1.14 adds the
`AGENTS.md`/`CLAUDE.md` instruction block every sibling package already ships.
F5: the shipped placeholder id token `xxxxxx` satisfies `^[0-9a-z]{6}$`, so a
template copied verbatim produced a schema-valid but meaningless id; the
exemplars move to `XXXXXX`, which fails validation loudly, and the validator's
own token pattern is deliberately untouched. F2/F4/F7/F11 are skill prose:
console-script provenance, the dual install path, `validate-id --fix` as the
bulk route, and `--scaffold` promoted to the default path for a new document.

The tests below pin what a future edit could silently undo: the byte boundary
against 1.13, the contribution declarations and their rendered block, the
placeholder inversion, and the prose claims a reader would act on.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import cast

from project_standards.control_plane.adapters.markdown import MarkdownBlockAdapter
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PREDECESSOR = _FAMILY / "versions/1.13"
_SUCCESSOR = _FAMILY / "versions/1.14"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-frontmatter/1.14"
_PREDECESSOR_DIGEST = "sha256:40cbd73ee6f8c28cd0d5b7befbfd8c54c277c00563627f5d0d3c9d9a36dcf0b9"
_SKILL = _SUCCESSOR / "skills/markdown-frontmatter/SKILL.md"

# Every exemplar carrying the placeholder id, plus the prose that explains the
# change, plus the manifest. `config.schema.json` is deliberately absent: the
# `harnesses` option the new contributions gate on already shipped in 1.13.
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "artifacts/agent-summary.md",
        "field-values.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/markdown-frontmatter/SKILL.md",
        "structure.md",
        "templates/concept.md",
        "templates/frontmatter-minimal.yml",
        "templates/frontmatter-standard.yml",
        "templates/note.md",
        "templates/repo-pages/README.directory.template.md",
        "templates/repository-frontmatter-adr.md",
        "templates/research.md",
        "templates/runbook.md",
        "templates/spec.md",
    }
)
_SUCCESSOR_ADDITIONS = frozenset({"agents-instructions.md", "claude-instructions.md"})
# The one file that must keep the lowercase placeholder: it is a byte-locked
# capture of the retired v4 skill, and rewriting it would break the legacy
# signature digest that recognizes an unmigrated consumer.
_LEGACY_REFERENCE = "resources/legacy-markdown-frontmatter-skill.md"


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def _contributions(root: Path) -> dict[str, dict[str, object]]:
    manifest = tomllib.loads((root / "payload.toml").read_text(encoding="utf-8"))
    entries = cast("list[dict[str, object]]", manifest["contributions"])
    return {cast("str", entry["id"]): entry for entry in entries}


def _block_body(relative: str) -> str:
    """Return the managed block the planner would extract from a contribution source.

    Goes through the real adapter rather than string-slicing, so a malformed
    envelope fails here instead of at a consumer's first reconcile.
    """
    state = MarkdownBlockAdapter().inspect(
        (_SUCCESSOR / relative).read_bytes(), ("block:markdown-frontmatter",)
    )
    assert len(state.units) == 1
    return cast("bytes", state.units[0].value).decode("utf-8")


def test_markdown_frontmatter_1_14__successor__changes_only_the_reviewed_surface() -> None:
    """Preserve every released byte outside the exemplars, prose, and manifest."""
    assert _SUCCESSOR.is_dir(), "the 1.14 candidate must exist before contract verification"

    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() - predecessor_files.keys() == _SUCCESSOR_ADDITIONS
    assert predecessor_files.keys() - successor_files.keys() == set()
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

    # The rendered validation workflows and the provider are the package's most
    # drift-prone outputs; a documentation-and-reach release must not move a byte
    # of either. The provider matters twice over: F5 explicitly forbids widening
    # or narrowing the id-token regex to accommodate the new placeholder.
    # `templates/frontmatter-*.yml` are exemplars, not workflow YAML: they carry
    # the placeholder id and are expected to move with the rest of the exemplars.
    for relative in successor_files:
        if relative.startswith("templates/"):
            continue
        if relative.endswith((".yml", ".yaml")) or relative == "providers/frontmatter.py":
            assert (
                successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
            )


def test_markdown_frontmatter_1_14__instruction_blocks__reach_both_harnesses() -> None:
    """F1 option (a): one managed block per harness, gated like the sibling packages."""
    contributions = _contributions(_SUCCESSOR)

    expected = {
        "agents-instructions": ("AGENTS.md", "agents-instructions.md", "codex"),
        "claude-instructions": ("CLAUDE.md", "claude-instructions.md", "claude-code"),
    }
    for contribution_id, (target, source, harness) in expected.items():
        entry = contributions[contribution_id]
        assert entry["target"] == target
        assert entry["adapter"] == "markdown-block"
        assert entry["scope"] == "block:markdown-frontmatter"
        assert entry["policy"] == "managed"
        assert entry["source"] == source
        assert entry["when_any"] == [{"option": "harnesses", "contains": harness}]
        # Static content, so no option can change the rendered unit. The empty
        # list is not the same as omitting the key, which means "unknown".
        assert entry["governing_options"] == []
        assert "provider" not in entry

    # The two blocks share one semantic address, so a consumer selecting both
    # harnesses gets the same block ID in two different files, never a collision.
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    addresses = {
        (contribution.target.original, contribution.scope)
        for contribution in manifest.contributions
        if contribution.adapter.value == "markdown-block"
    }
    assert addresses == {
        ("AGENTS.md", "block:markdown-frontmatter"),
        ("CLAUDE.md", "block:markdown-frontmatter"),
    }

    affected = {
        migration.to_endpoint.value: migration.affected for migration in manifest.migrations
    }
    assert "contribution:agents-instructions" in affected["package:1.14"]
    assert "contribution:claude-instructions" in affected["package:1.14"]


def test_markdown_frontmatter_1_14__instruction_blocks__say_what_an_agent_needs() -> None:
    """The block is the whole reach fix; an empty or misdirected one buys nothing."""
    agents = _block_body("agents-instructions.md")
    claude = _block_body("claude-instructions.md")

    for body, own_tree, other_tree in (
        (agents, ".agents/skills/markdown-frontmatter/", ".claude/skills/markdown-frontmatter/"),
        (claude, ".claude/skills/markdown-frontmatter/", ".agents/skills/markdown-frontmatter/"),
    ):
        # Each harness reads only its own skill tree, so pointing an agent at the
        # other one sends it to a path its harness will not load.
        assert own_tree in body
        assert other_tree not in body
        assert "new-doc-id --scaffold --doc-type" in body
        assert "project-standards validate" in body
        assert "never carry frontmatter" in body
        assert len(body.splitlines()) <= 12

    # The two differ only in the skill path: one edit must not drift the harnesses apart.
    assert (
        agents.replace(
            ".agents/skills/markdown-frontmatter/", ".claude/skills/markdown-frontmatter/"
        )
        == claude
    )


def test_markdown_frontmatter_1_14__placeholder_token__fails_validation_by_construction() -> None:
    """F5: every shipped exemplar carries a token the validator must reject."""
    token = re.compile(r"^[0-9a-z]{6}$", re.ASCII)
    assert token.fullmatch("xxxxxx") is not None, "the old placeholder was a valid token"
    assert token.fullmatch("XXXXXX") is None, "the new placeholder must fail id validation"

    lowercase = {
        relative
        for relative, path in _files(_SUCCESSOR).items()
        if relative != _LEGACY_REFERENCE and "xxxxxx" in path.read_text(encoding="utf-8")
    }
    assert lowercase == set()
    assert "xxxxxx" in (_SUCCESSOR / _LEGACY_REFERENCE).read_text(encoding="utf-8")

    # At least the required-fields block, the standard pages, and every template.
    uppercase = {
        relative
        for relative, path in _files(_SUCCESSOR).items()
        if "XXXXXX" in path.read_text(encoding="utf-8")
    }
    assert "skills/markdown-frontmatter/SKILL.md" in uppercase
    assert "structure.md" in uppercase
    assert "field-values.md" in uppercase
    assert {relative for relative in uppercase if relative.startswith("templates/")} == {
        "templates/concept.md",
        "templates/frontmatter-minimal.yml",
        "templates/frontmatter-standard.yml",
        "templates/note.md",
        "templates/repo-pages/README.directory.template.md",
        "templates/repository-frontmatter-adr.md",
        "templates/research.md",
        "templates/runbook.md",
        "templates/spec.md",
    }

    # The generator draws from `[0-9a-z]` and so can never emit the placeholder:
    # a scaffolded document is real from the first write, not a repair candidate.
    generator = (_SUCCESSOR / "skills/markdown-frontmatter/scripts/new-doc-id").read_text(
        encoding="utf-8"
    )
    assert "tr -dc '0-9a-z'" in generator
    assert "XXXXXX" not in generator


def test_markdown_frontmatter_1_14__skill__states_console_script_provenance() -> None:
    """F2: agents invented `project-standards validate-id` and a skill-local script."""
    skill = _SKILL.read_text(encoding="utf-8")
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_bytes().decode("utf-8"))
    scripts = cast("dict[str, str]", pyproject["project"]["scripts"])

    for command in ("validate-id", "format-frontmatter", "validate-frontmatter"):
        assert command in scripts, "the skill may only name commands the distribution installs"
        assert command in skill
    assert "console scripts installed by the `project-standards` distribution" in skill
    assert "not** `project-standards` subcommands" in skill
    assert "holds `new-doc-id` alone" in skill
    # No repository-local runner form: `uv run` and the wheel-runtime PYTHONPATH
    # are this repository's conventions, not the package's contract.
    assert "uv run" not in skill
    assert "PYTHONPATH" not in skill


def test_markdown_frontmatter_1_14__skill__leads_with_scaffold() -> None:
    """F11: `--scaffold` was third in the usage block and used in 2.5% of calls."""
    skill = _SKILL.read_text(encoding="utf-8")
    lines = skill.splitlines()

    scaffold = next(
        i for i, line in enumerate(lines) if line.startswith("scripts/new-doc-id --scaffold")
    )
    bare = next(
        i
        for i, line in enumerate(lines)
        if line.startswith("scripts/new-doc-id ") and "--" not in line
    )
    assert scaffold < bare, "the scaffold form must precede the bare-id repair forms"

    # The `REPLACE:` warning is the one thing promoting `--scaffold` could trade
    # away — a scaffolded block ships a placeholder description if it is missed.
    replace = next(i for i, line in enumerate(lines) if "REPLACE:" in line)
    assert 0 < replace - scaffold <= 12
    assert "`validate-id --fix`" in skill, "F7: the bulk id route must be named"


def test_markdown_frontmatter_1_14__skill__matches_the_shipped_install_layout() -> None:
    """F4: 1.13 shipped a skill claiming a single `.agents/` install path."""
    skill = _SKILL.read_text(encoding="utf-8")
    artifacts = tomllib.loads((_SUCCESSOR / "payload.toml").read_text(encoding="utf-8"))[
        "artifacts"
    ]
    targets = {cast("str", entry["target"]) for entry in cast("list[dict[str, object]]", artifacts)}

    assert ".agents/skills/markdown-frontmatter/SKILL.md" in targets
    assert ".claude/skills/markdown-frontmatter/SKILL.md" in targets
    assert "`.agents/skills/markdown-frontmatter` (Codex CLI)" in skill
    assert "`.claude/skills/markdown-frontmatter` (Claude Code)" in skill
    assert "neither copy may be edited or deleted to deduplicate" in skill

    # Trigger clarity: a packaged SKILL.md's own manifest header is harness
    # metadata, and an agent must not "fix" it into a managed-document profile.
    assert "Agent-Skills manifest metadata for the harness" in skill


def test_markdown_frontmatter_1_14__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.14"
    assert indexed["1.14"].digest == integrity.aggregate_digest
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.14"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-frontmatter"
    }
    assert roles["1.13"] == "retained"
    assert roles["1.14"] == "default"
    assert (
        "| [`markdown-frontmatter`](markdown-frontmatter/README.md) | active | 1.14 | "
        "default | consumer |"
    ) in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_markdown_frontmatter_1_14__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.13."""
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    successor_text = {
        relative: path.read_text(encoding="utf-8")
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".md", ".py", ".yaml", ".yml"}
    }
    # `README.md` narrates the release history and names 1.13 deliberately.
    stale = {
        relative
        for relative, text in successor_text.items()
        if re.search(r"(?<!\d)1\.13(?!\d)", text) and relative != "README.md"
    }
    assert stale == set(), "1.14 payload files still reference the 1.13 predecessor"

    released = {
        relative
        for relative, text in successor_text.items()
        if "v5.23.0" in text and relative != _LEGACY_REFERENCE
    }
    assert released == set(), "1.14 payload files still pin the v5.23.0 release tag"


def test_markdown_frontmatter_1_14__payload_projection__matches_successor() -> None:
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
