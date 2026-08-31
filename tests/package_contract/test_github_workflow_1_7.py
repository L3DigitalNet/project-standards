"""Package-contract proof for the GitHub Workflow 1.7 admission cut.

1.7 is the largest cut this family has taken: admission becomes T0-or-pull-request,
every PR declares one governing relationship, `ready` and `merge` join the surface as
paired operations, and one finding model feeds `check`, `receipt`, and `summary`. The
payload half of that lands as prose in files with no executable behavior of their own,
so the failure modes are documentary — a routing table that still shows eight
subcommands, a rule stated in the skill but not in the always-injected block, a budget
quietly exceeded because the new content is longer than what it replaced.

Two boundaries this file deliberately observes. The binary assertions read the digest
from `payload.toml` rather than pinning bytes, so declaration and committed executable
are held to each other whichever one an edit touches. And the family, catalog, and
projection assertions are written as an equivalence — advertised if and only if
projected — which was a real invariant before 1.7 was advertised and is the full check
now that it is.

1.7 is a retained predecessor: 1.8 took the default and `scripts/build-gh-workflow.sh`
moved with it, so nothing here claims 1.7 is the version the repository currently builds.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path
from types import ModuleType
from typing import cast

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_PREDECESSOR = _FAMILY / "versions/1.6"
_SUCCESSOR = _FAMILY / "versions/1.7"
_PROJECTION = _ROOT / "src/project_standards/payloads/github-workflow/1.7"
_PREDECESSOR_DIGEST = "sha256:ff4430c5c4b2335a5c9c5e06c0b6527d1d97eb8a929023c4b1e654553bc9922d"
_BUILD_SCRIPT = _ROOT / "scripts/build-gh-workflow.sh"
_TOOL_BINARY_SOURCE = "skills/github-workflow/bin/gh-workflow"
_SKILL_SOURCE = "skills/github-workflow/SKILL.md"
_REFERENCES = "skills/github-workflow/references"

# IR-005: ten subcommands, alphabetical here so a missing one is obvious at a glance.
# `ready` and `merge` are the two 1.7 adds; the other eight keep their 1.6 spellings.
_SUBCOMMANDS = (
    "audit",
    "check",
    "close",
    "merge",
    "new",
    "ready",
    "receipt",
    "reopen",
    "set",
    "summary",
)

# NFR-006 and NFR-003 ceilings, unchanged from 1.5 while the content inside them grew
# again. Measured at this cut: SKILL.md 69 lines / 11,978 B, field-vocabulary.md 30
# lines / 3,111 B, and the rendered block 2,363 B for `ExampleOrg` against 2,392 B at a
# 39-character login — GitHub's maximum, and the only measurement that proves the
# ceiling. Eight bytes of block headroom remain, so 1.8 prose has to displace prose.
_SKILL_MAX_LINES = 70
_SKILL_MAX_BYTES = 12000
_VOCABULARY_MAX_LINES = 30
_VOCABULARY_MAX_BYTES = 3200
_BLOCK_MAX_BYTES = 2400
_MAX_LOGIN = "a" * 39

# FR-030 categories in their one display order. Order is the assertion: a renderer or a
# reference that lists them alphabetically buries `Blocked` behind `Disposition
# required` in every attention list.
_CATEGORIES = (
    "Blocked",
    "Needs definition",
    "PR admission blocked",
    "Synchronization required",
    "Disposition required",
    "Target date passed",
)


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
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _block_body(organization: str = "ExampleOrg") -> str:
    """Render the managed block the way the control plane does, without a reconcile."""
    module = _load_provider("gh_workflow_1_7")
    return cast("str", module._block_body(organization))  # pyright: ignore[reportPrivateUsage]


def _advertised_versions() -> set[str]:
    family = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    return {entry["version"] for entry in cast("list[dict[str, str]]", family["versions"])}


def test_github_workflow_1_7__predecessor__keeps_its_released_bytes() -> None:
    """1.6 is published, so the cut may only add a sibling directory."""
    manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    integrity = validate_payload_integrity(_PREDECESSOR, manifest)
    assert integrity.aggregate_digest.value == _PREDECESSOR_DIGEST


def test_github_workflow_1_7__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    assert manifest.payload.version.value == "1.7"

    family = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    rows = {entry["version"]: entry for entry in cast("list[dict[str, str]]", family["versions"])}
    # Published predecessor rows are immutable selectors, not moving aliases.
    assert rows["1.6"]["digest"] == _PREDECESSOR_DIGEST
    # Advertising 1.7 is the build leg's step; when it happens the row must carry this
    # payload's actual aggregate rather than a digest copied from a stale rebuild.
    if "1.7" in rows:
        assert rows["1.7"]["digest"] == integrity.aggregate_digest.value


def test_github_workflow_1_7__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.6."""
    stale = {
        relative
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".yaml"}
        and re.search(r"(?<!\d)1\.6(?!\d)", path.read_text(encoding="utf-8"))
    }
    assert stale == set(), "1.7 payload files still reference the 1.6 predecessor"


def test_github_workflow_1_7__configuration__is_byte_identical_to_the_predecessor() -> None:
    """FR-035: 1.7 changes no consumer configuration key.

    Asserted on the bytes rather than on the prose, because the claim adopt.md makes to
    an upgrading consumer — that the upgrade is a version bump — is false the moment
    either file diverges, and a schema edit is exactly the kind of change that looks
    harmless in a diff.
    """
    for relative in ("config.schema.json", "resources/policy.toml"):
        assert (_SUCCESSOR / relative).read_bytes() == (_PREDECESSOR / relative).read_bytes()


def test_github_workflow_1_7__tool_binary__is_declared_for_this_version() -> None:
    """Pin the payload's declaration of the committed 1.7 executable.

    The build-script half of the contract moved on with 1.8: `scripts/build-gh-workflow.sh`
    targets the successor from the moment it is cut and can no longer reproduce 1.7 (see
    the script's own header). What 1.7 still owns is the negative — a script pointed back
    here would rebuild over released bytes — plus the declared digest. The positive pin
    travels with whichever cut is under development.
    """
    committed = _SUCCESSOR / _TOOL_BINARY_SOURCE
    digest = f"sha256:{hashlib.sha256(committed.read_bytes()).hexdigest()}"

    for artifact_id in ("tool-binary", "tool-binary-claude"):
        entry = _artifacts(_SUCCESSOR)[artifact_id]
        assert entry["source"] == _TOOL_BINARY_SOURCE
        # Read the expected digest from the payload rather than pinning a literal: this
        # assertion has to keep proving that the declaration and the committed bytes
        # agree, whichever of the two the next edit touches.
        assert entry["digest"] == digest
        assert entry["mode"] == "0755"
    assert committed.stat().st_mode & 0o777 == 0o755

    build_script = _BUILD_SCRIPT.read_text(encoding="utf-8")
    assert (
        f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.7/{_TOOL_BINARY_SOURCE}"'
        not in build_script
    )
    assert 'ARTIFACT_LDFLAGS="-buildid= -X main.version=1.7"' not in build_script


def test_github_workflow_1_7__surface__is_ten_subcommands_everywhere_it_is_stated() -> None:
    """IR-005's surface, in all four places a consumer or an agent can read it.

    The four homes are written to different budgets and different audiences, so they are
    checked for the subcommand names rather than for shared phrasing. `ledger` stays
    absent: it was removed at 1.5 and a copied payload is how it comes back.
    """
    skill = _text(_SKILL_SOURCE)
    body = _block_body()
    readme = _text("README.md")
    summary = _text("agent-summary.md")

    for subcommand in _SUBCOMMANDS:
        assert f"`{subcommand} " in skill or f"`{subcommand}`" in skill, subcommand
        assert subcommand in body, subcommand
        assert f"`{subcommand}`" in readme, f"README.md omits `{subcommand}`"
        assert f"`{subcommand}`" in summary, f"agent-summary.md omits `{subcommand}`"

    for relative, text in (("README.md", readme), ("agent-summary.md", summary)):
        assert "ten" in text and "subcommands" in text, relative
        assert "eight non-interactive subcommands" not in text, relative

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

    # The PR routes are the ones a reader most easily leaves at their 1.6 spelling.
    for route in ("check --pr N", "receipt --pr N", "ready --pr N", "merge --pr N", "close --pr N"):
        assert route in skill, f"SKILL.md omits the {route} route"


def test_github_workflow_1_7__skill__stays_one_read_within_its_budget() -> None:
    """NFR-006's ceilings and SKILL.md's self-declared line count."""
    skill = _text(_SKILL_SOURCE)
    lines = skill.splitlines()

    assert len(lines) <= _SKILL_MAX_LINES
    assert len(skill.encode("utf-8")) <= _SKILL_MAX_BYTES
    assert "  version: '1.7'" in skill
    # A hand-maintained count goes stale silently; assert it against the file itself.
    declared = re.search(r"^  lines: (\d+)$", skill, re.MULTILINE)
    assert declared is not None and int(declared.group(1)) == len(lines)
    assert f"about {len(lines)} lines" in _text("skills/github-workflow/agents/openai.yaml")

    vocabulary = _text(f"{_REFERENCES}/field-vocabulary.md")
    assert len(vocabulary.splitlines()) <= _VOCABULARY_MAX_LINES
    assert len(vocabulary.encode("utf-8")) <= _VOCABULARY_MAX_BYTES
    # FR-005/DEV-009: the pointer at a README no consumer receives is gone for good.
    assert "README.md" not in vocabulary

    assert "This table is complete" in skill
    # FR-002: the skill states its own reduced load boundary, because a skill that still
    # claims to be mandatory before every mutation cancels the block's whole purpose.
    assert "routes ordinary mutations and summaries on its own" in skill
    # FR-009 and the three contiguous terminal refusals, retained verbatim from 1.6.
    assert "An operator instruction is sufficient authority." in skill
    refusals = [line for line in lines if line.startswith("- **Refuse ")]
    assert [line.split("**")[1] for line in refusals] == [
        "Refuse to mutate organization schema.",
        "Refuse field-shadowing labels.",
        "Refuse to bypass enforcement.",
    ]
    assert lines.index(refusals[0]) + 2 == lines.index(refusals[2]), (
        "the three refusals must stay contiguous"
    )


def test_github_workflow_1_7__managed_block__carries_the_whole_high_frequency_contract() -> None:
    """FR-007 and NFR-003: everything a session that never loads a skill must know.

    Each element is asserted by the phrase the block actually uses. That is the point of
    the test — the block is the only package text a delegated worker is guaranteed to
    see, so an element dropped to make room for another is invisible until a worker
    routes around the package in production.
    """
    body = _block_body()
    assert len(body.encode("utf-8")) <= _BLOCK_MAX_BYTES
    assert len(_block_body(_MAX_LOGIN).encode("utf-8")) <= _BLOCK_MAX_BYTES
    assert "`ExampleOrg`" in body, "the organization must stay config-rendered (NFR-001)"

    for element in (
        "An operator instruction is sufficient authority",
        "is the only autonomous direct push",
        "`Workflow-Admission: T0`",
        "all other work starts as a draft PR",
        "`Final: #N`, `Supporting: #N`, or `Standalone`",
        "## Governing work",
        "open state never implies `Ready`",
        "Keep terminal state paired",
        "Never create shadow state labels, mutate organization schema through this package, "
        "or bypass live enforcement",
        "needs no issue",
        "--output human|json",
    ):
        assert element in body, f"the block omits: {element}"

    # The escaped pipe keeps the alternation inside one table cell.
    assert "--as done\\|dropped" in body
    # NFR-003 keeps the block free of what the skill owns: no flag table, no vocabulary,
    # no exit-code list, no body schema.
    for excluded in ("--policy", "--repo owner/name", "Exit codes", "Needs definition", "exit `2`"):
        assert excluded not in body, f"the block should not carry: {excluded}"


def test_github_workflow_1_7__references__carry_the_admission_and_finding_model() -> None:
    """The reference surface FR-006, FR-026-FR-030, and FR-035 assign to 1.7."""
    pr_standard = _text(f"{_REFERENCES}/pr-standard.md")
    summary_format = _text(f"{_REFERENCES}/summary-format.md")
    issue_structure = _text(f"{_REFERENCES}/issue-structure.md")
    review_checklist = _text(f"{_REFERENCES}/review-checklist.md")

    # FR-026. The trailer is a literal that commits are matched against, so it is pinned
    # exactly rather than by paraphrase, and the audit route is what makes the trailer
    # worth writing at all.
    assert "Workflow-Admission: T0" in pr_standard
    assert "git log --grep 'Workflow-Admission: T0'" in pr_standard
    for surface in ("Executable source and tests", "dependencies and lockfiles", "code blocks"):
        assert surface in pr_standard, f"the protected-surface list omits: {surface}"
    assert "at most 3 files and at most 30 added-plus-deleted lines" in pr_standard

    # FR-027 and FR-028: the declaration grammar and the four required sections.
    assert "## Governing work" in pr_standard
    for declaration in ("`Final: #N`", "`Supporting: #N`", "`Standalone`"):
        assert declaration in pr_standard
    assert "at most one open Final" in pr_standard
    assert "exact `Closes #N` on a Final PR" in pr_standard
    for section in ("## Summary", "## Governing work", "## Acceptance coverage", "## Verification"):
        assert section in pr_standard
    assert "Change risk: R2" in pr_standard
    for control in (
        "a plan agreed before implementation",
        "a recovery or rollback procedure",
        "negative testing",
        "independent verification",
    ):
        assert control in pr_standard, f"the R4 evidence list omits: {control}"
    assert "Change risk" in review_checklist and "R4" in review_checklist

    # FR-029: the lifecycle-coherence rules a merge must not invent for itself.
    for rule in (
        "sole lifecycle authority",
        "Refused while the Issue is `Blocked`",
        "never authorizes `Done`",
        "Final-Disposition",
    ):
        assert rule in pr_standard, f"the lifecycle contract omits: {rule}"

    # FR-035: repair-on-touch, and no proactive migration scan or ledger.
    assert "repaired when it is next touched" in pr_standard

    # FR-017/FR-030: six categories, in display order, plus observed-state filtering.
    positions = [summary_format.index(f"**{category}**") for category in _CATEGORIES]
    assert positions == sorted(positions), "summary-format.md lists the categories out of order"
    for filtering in ("Structural findings only", "Post-merge and disposition findings"):
        assert filtering in summary_format
    # FR-018: the receipt stopped being creation ceremony.
    assert "projection of observed state, not a creation ceremony" in summary_format
    assert "Created {kind}" not in summary_format
    # DR-004: the envelope members, named where an agent relaying JSON can see them.
    for member in ('"schema_version"', '"command"', '"result"', '"gate"', '"findings"', '"steps"'):
        assert member in summary_format, f"the envelope summary omits {member}"
    assert "operational-failure" in summary_format

    # FR-023/DEV-020: the acceptance heading the parser reads is stated as machine-significant.
    assert "`## Acceptance criteria` is machine-significant" in issue_structure


def test_github_workflow_1_7__envelope_schema__matches_the_documented_vocabulary() -> None:
    """DR-004: the machine-readable envelope and the reference that explains it agree.

    The schema's authority is `internal/ghworkflow/cli/envelope.go` and
    `internal/ghworkflow/relation/model.go`, which this payload cannot import. What is
    checkable here is that the payload does not contradict itself — the categories the
    schema accepts are the six the summary reference lists, in the same order, and the
    result and step vocabularies are the ones the guidance names.
    """
    schema = json.loads(_text("schemas/cli-envelope.schema.json"))
    properties = cast("dict[str, dict[str, object]]", schema["properties"])
    finding = cast(
        "dict[str, dict[str, object]]",
        cast("dict[str, object]", properties["findings"]["items"])["properties"],
    )

    assert finding["category"]["enum"] == list(_CATEGORIES)
    assert properties["result"]["enum"] == [
        "clear",
        "domain-finding",
        "usage",
        "operational-failure",
    ]
    assert finding["phase"]["enum"] == ["structural", "ready", "merge", "post-merge"]
    assert cast(
        "dict[str, dict[str, object]]",
        cast("dict[str, object]", properties["steps"]["items"])["properties"],
    )["status"]["enum"] == ["completed", "skipped", "pending", "failed"]

    # findings.schema.json stays the control-plane provider contract. Overwriting it
    # with the DR-004 envelope would make every validate, verify, and drift-check run
    # fail output-schema validation, because those providers return `{"findings": [...]}`
    # with the provider finding shape, not this envelope.
    provider_findings = json.loads(_text("schemas/findings.schema.json"))
    assert provider_findings["required"] == ["findings"]


def test_github_workflow_1_7__guidance__names_no_organization() -> None:
    """NFR-001: the consumer's own login reaches the block only through configuration.

    Scoped to guidance and the rendered block. The payload's JSON Schemas may carry a
    `$id` under the publishing repository, which is a distribution address rather than a
    claim about the consumer.
    """
    guidance = {
        relative: path
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".md", ".yaml"}
    }
    for relative, path in guidance.items():
        assert "L3DigitalNet" not in path.read_text(encoding="utf-8"), relative
    assert "L3DigitalNet" not in _block_body(_MAX_LOGIN)


def test_github_workflow_1_7__payload_projection__tracks_advertisement() -> None:
    """The runtime projection exists exactly when the family advertises the version.

    Both halves are failures: an advertised version with no projection is a payload the
    installed distribution cannot read, and a projection for an unadvertised version is
    stale bytes that no manifest keeps honest. Until the build leg advertises 1.7, this
    proves the second half.
    """
    advertised = "1.7" in _advertised_versions()
    assert _PROJECTION.exists() == advertised, (
        "standard.toml and the payload projection disagree about 1.7"
    )
    if not advertised:
        return

    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
