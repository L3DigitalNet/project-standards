"""Package-contract proof for the GitHub Workflow 1.6 finding-disposition cut.

1.6 is a one-rule cut: the standing invariant that made discovered durable work an
issue before the session ends is replaced by the owner's disposition rule (fix it
here, file it upstream, or ask). That shape is the risky one. Almost every byte is
copied from 1.5, so the failure modes are the copy's — a version stamp left at the
predecessor, a rule replaced in one of its two homes, a managed block quietly pushed
past its budget by longer prose — not a behavioral regression. The assertions below
pin exactly those: the stamps, both homes of the rule, the absence of the withdrawn
one, and the budgets.

Two facts this file deliberately does not restate. The provider's managed-target
registry is proven for every advertised payload by `test_provider_registry.py`
(issue #194), and the removed-`ledger` prose contract is proven for 1.5's bytes by
`test_github_workflow_1_5.py`; 1.6 inherits both and the ledger-prose assertions are
repeated here only because a copied paragraph is what a copied payload gets wrong.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import tomllib
from pathlib import Path
from types import ModuleType
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_PREDECESSOR = _FAMILY / "versions/1.5"
_SUCCESSOR = _FAMILY / "versions/1.6"
_PROJECTION = _ROOT / "src/project_standards/payloads/github-workflow/1.6"
_PREDECESSOR_DIGEST = "sha256:cb91ea5899362690402729633ac547017a5dd262b87a64ea45d3a253b6d93dc8"
_BUILD_SCRIPT = _ROOT / "scripts/build-gh-workflow.sh"
_TOOL_BINARY_SOURCE = "skills/github-workflow/bin/gh-workflow"
_SKILL_SOURCE = "skills/github-workflow/SKILL.md"

# Unchanged from 1.5, in registration order from `gh-workflow help`.
_SUBCOMMANDS = ("audit", "check", "close", "new", "receipt", "reopen", "set", "summary")

# Budgets inherited from 1.5 (NFR-006 1.11, NFR-003). They are ceilings, not targets,
# and 1.6 spends most of the remaining headroom: the rule it adds is longer than the
# one it removes. Measured at this cut: SKILL.md 70 lines / 11,711 B, and the rendered
# block 2,397 B for `ExampleOrg`. A successor that adds prose to either without moving
# a ceiling deliberately will fail here rather than ship an over-budget read.
_SKILL_MAX_LINES = 70
_SKILL_MAX_BYTES = 12000
_BLOCK_MAX_BYTES = 2400

# The withdrawn invariant, in the wording each home carried through 1.5. Asserting the
# absence is the half that a copied payload fails: adding the new rule beside the old
# one leaves two contradictory instructions and every assertion below still passes.
_WITHDRAWN = "becomes an issue before the session ends"


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
    source = _SUCCESSOR / "providers/gh_workflow.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _block_body() -> str:
    """Render the managed block the way the control plane does, without a reconcile."""
    module = _load_provider("gh_workflow_1_6")
    return cast("str", module._block_body("ExampleOrg"))  # pyright: ignore[reportPrivateUsage]


def test_github_workflow_1_6__predecessor__keeps_its_released_bytes() -> None:
    """1.5 is published, so the cut may only add a sibling directory."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST


def test_github_workflow_1_6__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.6"
    assert indexed["1.6"].digest == integrity.aggregate_digest
    # Published predecessor rows are immutable selectors, not moving aliases.
    assert indexed["1.5"].digest.value == _PREDECESSOR_DIGEST

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "github-workflow"
    }
    assert roles["1.5"] == "retained"
    assert roles["1.6"] == "default"
    assert "| [`github-workflow`](github-workflow/README.md) | active | 1.6 | default |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_github_workflow_1_6__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.5."""
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        relative
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".yaml"}
        and re.search(r"(?<!\d)1\.5(?!\d)", path.read_text(encoding="utf-8"))
    }
    assert stale == set(), "1.6 payload files still reference the 1.5 predecessor"


def test_github_workflow_1_6__tool_binary__is_declared_and_built_for_this_version() -> None:
    """Pin the three-way contract between the committed bytes, the payload, and the build."""
    committed = _SUCCESSOR / _TOOL_BINARY_SOURCE
    digest = f"sha256:{hashlib.sha256(committed.read_bytes()).hexdigest()}"

    for artifact_id in ("tool-binary", "tool-binary-claude"):
        entry = _artifacts(_SUCCESSOR)[artifact_id]
        assert entry["source"] == _TOOL_BINARY_SOURCE
        assert entry["digest"] == digest
        assert entry["mode"] == "0755"
    assert committed.stat().st_mode & 0o777 == 0o755

    # The Go source is unchanged at this cut, so only the `-X main.version` stamp
    # distinguishes the two builds — which is exactly why shipping the predecessor's
    # executable would otherwise be invisible here.
    assert committed.read_bytes() != (_PREDECESSOR / _TOOL_BINARY_SOURCE).read_bytes()

    build_script = _BUILD_SCRIPT.read_text(encoding="utf-8")
    assert (
        f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.6/{_TOOL_BINARY_SOURCE}"'
        in build_script
    )
    assert 'ARTIFACT_LDFLAGS="-buildid= -X main.version=1.6"' in build_script


def test_github_workflow_1_6__finding_disposition__replaces_the_follow_up_invariant() -> None:
    """The whole cut: one rule, in both homes, with the one it replaces gone from both.

    The block and SKILL.md are separate homes on purpose — the block binds a delegated
    worker that never loads a skill — so a cut that updated one and copied the other
    would ship a package that contradicts itself depending on what the session read.
    """
    skill = _text(_SKILL_SOURCE)
    body = _block_body()

    for name, text in (("SKILL.md", skill), ("managed block", body)):
        assert _WITHDRAWN not in text, f"{name} still carries the withdrawn invariant"
        # The three dispositions, each in the wording its home ships.
        assert "no issue" in text, name
        assert "owning repository" in text or "in that codebase" in text, name
        assert "separate session" in text, name

    assert "**Not every finding needs an issue.**" in skill
    assert "A related finding you can address this session gets no issue" in body

    # NFR-001: no packaged guidance names an organization — the consumer's own login
    # reaches the block only through configuration. The rule's upstream-filing clause
    # is the newest place that could have hardcoded one, and it says "the organization"
    # precisely so it does not have to. Scoped to guidance and the rendered block: the
    # JSON Schemas carry a `$id` URL under the publishing repository, which is a
    # distribution address rather than a claim about the consumer.
    guidance = {
        relative: path
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".md", ".yaml"}
    }
    for relative, path in {**guidance, "<rendered block>": None}.items():
        text = body if path is None else path.read_text(encoding="utf-8")
        assert "L3DigitalNet" not in text, relative


def test_github_workflow_1_6__skill__stays_one_read_within_its_budget() -> None:
    """SKILL.md's budget and its self-declared line count, which the new bullet moves."""
    skill = _text(_SKILL_SOURCE)
    lines = skill.splitlines()

    assert len(lines) <= _SKILL_MAX_LINES
    assert len(skill.encode("utf-8")) <= _SKILL_MAX_BYTES
    assert "  version: '1.6'" in skill
    # A hand-maintained count goes stale silently; assert it against the file itself.
    declared = re.search(r"^  lines: (\d+)$", skill, re.MULTILINE)
    assert declared is not None and int(declared.group(1)) == len(lines)
    # The block advertises that same read length to sessions that never open the file.
    assert f"~{len(lines)} lines" in _block_body()

    assert "This table is complete" in skill
    for subcommand in _SUBCOMMANDS:
        assert f"`{subcommand} " in skill or f"`{subcommand}`" in skill, subcommand


def test_github_workflow_1_6__managed_block__still_routes_without_a_skill_load() -> None:
    """1.5's block contract, re-proven against prose that grew."""
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
    ):
        assert rule in body, rule
    # The escaped pipe keeps the alternation inside one table cell.
    assert "--as done\\|dropped" in body


def test_github_workflow_1_6__payload_prose__still_describes_eight_subcommands() -> None:
    """The 1.5 removal is still consumer-visible from 1.6, and the copy has to say so."""
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

    for relative in ("README.md", "agent-summary.md"):
        text = _text(relative)
        assert "eight" in text and "subcommands" in text, relative
        assert "nine subcommands" not in text, relative
        for subcommand in _SUBCOMMANDS:
            assert f"`{subcommand}`" in text, f"{relative} omits `{subcommand}`"


def test_github_workflow_1_6__payload_projection__matches_successor() -> None:
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
