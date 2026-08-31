"""Pin the GitHub Workflow 1.8 `Change risk` vocabulary correction.

Issue #202: 1.7 shipped `Change risk: R2` as the Standalone example in
`pr-standard.md`, while the Ready gate accepted only the four full spellings
`org-schema.yaml` declares. A PR body copied from the shipped example was therefore
refused by the package that shipped it. The refusal was also unhelpful: the accepted
values lived in the finding's Remediation, and `writeHumanEnvelope` in
`internal/ghworkflow/cli/envelope.go` prints a finding's Message and discards its
Remediation (the FR-030 compressed view), so an operator who never asked for JSON saw
the constraint without the vocabulary that satisfies it.

The correction has three ends that must agree — `org-schema.yaml`, the reference
prose, and the compiled binary's message — so the assertions below derive the expected
set from `org-schema.yaml` and compare the other two against it rather than restating
four literals in a fourth place. A future value added to the field, or a spelling that
drifts in either direction, fails here instead of at an operator's Ready gate.

The binary is read as bytes and never executed: this suite must stay runnable on any
platform, and the payload ships a linux/amd64 static build. Go concatenates its string
literals into one unterminated table, so every binary assertion is containment of a
literal, not extraction of a delimited string.

Nothing else in 1.8 moves — no option, no rendered `policy.toml` byte beyond the
version stamp it interpolates, no subcommand — which is the second contract here.
"""

from __future__ import annotations

import hashlib
import re
import stat
import tomllib
from pathlib import Path
from typing import cast

import yaml

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_V17 = _FAMILY / "versions/1.7"
_V18 = _FAMILY / "versions/1.8"
_PROJECTION_18 = _ROOT / "src/project_standards/payloads/github-workflow/1.8"

_REFERENCES = "skills/github-workflow/references"
_PR_STANDARD = f"{_REFERENCES}/pr-standard.md"
_REVIEW_CHECKLIST = f"{_REFERENCES}/review-checklist.md"
_ORG_SCHEMA = f"{_REFERENCES}/org-schema.yaml"
_BINARY = "skills/github-workflow/bin/gh-workflow"

# The 1.8 message format string, and the fixed 1.7 sentence it replaced. Both are read
# from the committed binary, so this pair is what proves the shipped executable is the
# rebuilt one rather than the predecessor's bytes copied forward.
_MESSAGE_FORMAT = b"the `Change risk:` value is not one of %s"
_MESSAGE_FORMAT_1_7 = b"not one of the four accepted values"

_V17_AGGREGATE = "sha256:9758d1dab58643cb6f8461bd11dd139233c346e37e54c5580ba6a1cd4a17c17a"

# The predecessor is advertised and therefore immutable: a byte change anywhere in it
# is a released-payload mutation, not a diff to review. Modes are asserted alongside
# the digests because this family is the one payload with an executable in it — the
# binary is 0755 and everything else is 0644, and a projection or a repack that
# flattens that ships a tool the consumer cannot run.
_V17_FILES = {
    "README.md": (0o644, "c67af002ac8af7ffe17146740152175ca09cb789c31abbfa463e564af33c381b"),
    "adopt.md": (0o644, "f899f12b71fe328147b561f7a329b8f0549ac037aa69c9a5bbb5f7d6a2ee9ef8"),
    "agent-summary.md": (
        0o644,
        "1512529795483d9ce284b960c07f4917c75a0c6aedd352e11bcc15575fe42846",
    ),
    "config.schema.json": (
        0o644,
        "526d70a62acd7f6663d0b315de87664e50eb8c4b418f965511139def003c388d",
    ),
    "payload.toml": (0o644, "14bb54760f42278f17100e6ae0b515c58bcd04a30e8fe1f05cad539e50913894"),
    "providers/gh_workflow.py": (
        0o644,
        "048306e479515747b56ea982dca80e8664db04888b8c3e424ee6fa9e91555061",
    ),
    "resources/policy.toml": (
        0o644,
        "b50a3cda7a9d73d64158867fdd27ebabddfb06f41f9d17e413f7085fa085614a",
    ),
    "schemas/cli-envelope.schema.json": (
        0o644,
        "0e3e480bfb441f7f506d290f83f884a775071563875ed3088d0bc981cf10328a",
    ),
    "schemas/content.schema.json": (
        0o644,
        "b283a32e612daa98b218bab151ecb1c91ac32b2558038e491f95dae4f8042206",
    ),
    "schemas/findings.schema.json": (
        0o644,
        "caa57b52481e734fed06c9e07de74dfbfd2c954ceaa63233e129d479f74d8fa5",
    ),
    "schemas/mutation-plan.schema.json": (
        0o644,
        "8c4fa5da614ef247d9f21d58f2a4bc533ed7b8205cb8221f1559c9893fdd57fd",
    ),
    "schemas/provider-input.schema.json": (
        0o644,
        "8bdffc61ca6baf3e892c91f5ca6fff0de0efda63da56fcd6f8d3fd384a276433",
    ),
    "skills/github-workflow/SKILL.md": (
        0o644,
        "84366ea0f27cd5de06aa1eb6c36650998d23bb1d9e5928492c99cd13abc1267b",
    ),
    "skills/github-workflow/agents/openai.yaml": (
        0o644,
        "b4a95c41144530b3694e71ab4662de3031bca3c7ef9b9b7a963a5038003998f1",
    ),
    "skills/github-workflow/bin/gh-workflow": (
        0o755,
        "bf677a6760e7a857f09515932bf967abf2de91dab99c2c182b261b574d013981",
    ),
    "skills/github-workflow/references/field-vocabulary.md": (
        0o644,
        "4600470727d00ea16c0cde3233175b9aaf830ec3dec57fd1f7bf4b7523b7993c",
    ),
    "skills/github-workflow/references/issue-structure.md": (
        0o644,
        "1a0d0c7fbcc01a3e9d255e1c1f2cad83d85fc28be6766e758baf66544068f465",
    ),
    "skills/github-workflow/references/org-schema.yaml": (
        0o644,
        "b8170049e40fd944a3dd78a8b7ab9d153feda90b6df42445863fae5ece03da99",
    ),
    "skills/github-workflow/references/pr-standard.md": (
        0o644,
        "021c0d1d84c3ebc35628289bdc09ed9882823e17719ffc05ab89f423886c18ac",
    ),
    "skills/github-workflow/references/review-checklist.md": (
        0o644,
        "a34f733f54abc09a0a1e5943f9504d0339dad787866ff176a5ad7443bfaecd50",
    ),
    "skills/github-workflow/references/summary-format.md": (
        0o644,
        "6e26f8d19e37f41babb7b1da9ff5aa3779e9caf3a1636c999ec276d078dbcb65",
    ),
}

# The files 1.8 is allowed to touch: the two corrected references, the rebuilt binary,
# the skill's frontmatter version, the three prose surfaces that carry the cut's own
# account, and the two machine-readable stamps. Every other payload file must survive
# byte-for-byte, which is what turns "a correction release" into a checkable claim.
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/github-workflow/SKILL.md",
        _BINARY,
        _PR_STANDARD,
        _REVIEW_CHECKLIST,
    }
)

# Both harnesses selected, so every managed block and the policy render are reachable.
_CONFIG: JsonObject = {"organization": "ExampleOrg", "harnesses": ["claude-code", "codex"]}


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, selected: JsonObject | None = None) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(selected or _CONFIG)


def _render(root: Path, planned: JsonObject) -> bytes:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="github-workflow",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=_options(root),
            snapshots={"planned_contribution": planned},
        )
    )
    assert result.content is not None
    return result.content


def _render_block(root: Path) -> bytes:
    return _render(
        root,
        {
            "id": "instructions-claude",
            "target": "CLAUDE.md",
            "adapter": AdapterKind.MARKDOWN_BLOCK.value,
            "scope": "block:github-workflow",
        },
    )


def _render_policy(root: Path) -> bytes:
    return _render(
        root,
        {
            "id": "policy",
            "target": ".standards/packages/github-workflow/policy.toml",
            "adapter": AdapterKind.WHOLE_FILE.value,
            "scope": "$file",
        },
    )


def _accepted_risks(root: Path) -> list[str]:
    """Return the `Change risk` values the organization schema declares.

    This is the vocabulary's single source of truth: the Ready gate validates against
    it, and every other statement of the four values in this package — the reference
    prose and the binary's own refusal message — is a projection of it. Reading it
    here rather than hardcoding the four spellings is what makes a divergence fail.
    """
    schema = cast("dict[str, object]", yaml.safe_load((root / _ORG_SCHEMA).read_text("utf-8")))
    fields = cast("dict[str, dict[str, object]]", schema["issue_fields"])
    return cast("list[str]", fields["Change risk"]["values"])


def _declared_risks(text: str) -> list[str]:
    """Return every `Change risk: VALUE` declaration a reference document shows."""
    return re.findall(r"^Change risk: (.+)$", text, re.MULTILINE)


def test_github_workflow_1_8__pr_standard_example__is_a_value_the_ready_gate_accepts() -> None:
    """The defect itself: the shipped example was refused by the shipped gate.

    Asserted against the schema's vocabulary rather than against `R2 Moderate`, so the
    example and the accepted set cannot drift apart in either direction.
    """
    accepted = _accepted_risks(_V18)
    declarations = _declared_risks((_V18 / _PR_STANDARD).read_text(encoding="utf-8"))

    assert declarations, "pr-standard.md no longer shows a `Change risk:` declaration"
    for value in declarations:
        assert value in accepted, f"pr-standard.md shows an unaccepted risk value: {value}"


def test_github_workflow_1_8__reference_prose__states_the_whole_vocabulary() -> None:
    """All four spellings, in both documents an author and a reviewer read.

    `pr-standard.md` tells the author what to write and `review-checklist.md` tells the
    reviewer what each value costs; a value present in one and abbreviated in the other
    reintroduces the same mismatch at a different desk.
    """
    accepted = _accepted_risks(_V18)
    assert len(accepted) == 4

    for relative in (_PR_STANDARD, _REVIEW_CHECKLIST):
        text = (_V18 / relative).read_text(encoding="utf-8")
        for value in accepted:
            assert value in text, f"{relative} omits the accepted value {value}"

    # The ladder table's cells are the risk labels themselves, so a bare `**R2**` row
    # is the review-side spelling of the defect.
    checklist = (_V18 / _REVIEW_CHECKLIST).read_text(encoding="utf-8")
    for value in accepted:
        assert f"**`{value}`**" in checklist, f"the risk ladder does not spell {value} in full"
        assert f"| **{value.split()[0]}** |" not in checklist


def test_github_workflow_1_8__predecessor_reference__still_shows_the_refused_example() -> None:
    """Guard the fix against a silent revert, and 1.7 against a backport.

    1.7 is advertised and immutable, so its bare `Change risk: R2` stays wrong there;
    the repair is a new version. This assertion is also the record of what the defect
    was, which the corrected file no longer shows.
    """
    text = (_V17 / _PR_STANDARD).read_text(encoding="utf-8")

    assert _declared_risks(text) == ["R2"]
    assert "R2" not in _accepted_risks(_V17)


def test_github_workflow_1_8__binary__carries_the_vocabulary_in_the_message() -> None:
    """The half of the fix an operator sees, proven on the bytes that ship.

    The human envelope prints Message and drops Remediation, so the format string
    below is the only place the accepted values can reach an operator who never asks
    for JSON. Its 1.7 predecessor — a fixed sentence that named a count instead of the
    values — must be gone, or the payload is carrying the old executable.
    """
    binary = (_V18 / _BINARY).read_bytes()

    assert _MESSAGE_FORMAT in binary
    assert _MESSAGE_FORMAT_1_7 not in binary
    assert _MESSAGE_FORMAT not in (_V17 / _BINARY).read_bytes()
    assert _MESSAGE_FORMAT_1_7 in (_V17 / _BINARY).read_bytes()


def test_github_workflow_1_8__binary__spells_exactly_the_schema_vocabulary() -> None:
    """The third end of the contract: the compiled `Risks` slice and the schema agree.

    The message interpolates a list derived from the Go `Risks` slice, so the four
    values reach the operator only if the binary carries those exact spellings. The
    reverse direction — no *other* risk-shaped token — is checked as prefix
    compatibility rather than exact extraction: Go packs string literals into one
    unterminated table, so a genuine value is routinely followed by unrelated bytes
    (`R3 Highblockerversion`) or truncated by them, while a wrong spelling such as
    `R2 Medium` is neither a prefix nor an extension of any accepted value.
    """
    accepted = _accepted_risks(_V18)
    binary = (_V18 / _BINARY).read_bytes()

    for value in accepted:
        assert value.encode("utf-8") in binary, f"the binary does not carry {value}"

    for found in {match.decode("utf-8") for match in re.findall(rb"R[1-9] [A-Z][a-z]+", binary)}:
        assert any(found.startswith(value) or value.startswith(found) for value in accepted), (
            f"the binary carries a risk spelling outside the schema vocabulary: {found}"
        )


def test_github_workflow_1_8__binary__is_declared_by_the_payload_it_ships_in() -> None:
    """A rebuilt executable is only delivered if the manifest declares its digest.

    Both artifact rows point at the same source, because reconcile installs the tool
    under `.agents/` and `.claude/`; a digest that agrees with only one of them, or
    with the 1.7 bytes, ships a tool integrity refuses to write.
    """
    committed = _V18 / _BINARY
    digest = f"sha256:{hashlib.sha256(committed.read_bytes()).hexdigest()}"
    manifest = tomllib.loads((_V18 / "payload.toml").read_text(encoding="utf-8"))
    artifacts = {
        entry["id"]: entry for entry in cast("list[dict[str, str]]", manifest["artifacts"])
    }

    assert committed.read_bytes() != (_V17 / _BINARY).read_bytes()
    for artifact_id in ("tool-binary", "tool-binary-claude"):
        assert artifacts[artifact_id]["source"] == _BINARY
        assert artifacts[artifact_id]["digest"] == digest
        assert artifacts[artifact_id]["mode"] == "0755"
    assert stat.S_IMODE(committed.stat().st_mode) == 0o755


def test_github_workflow_1_8__build_script__targets_this_version() -> None:
    """The reproducible build must name the payload under development, not a released one.

    `scripts/build-gh-workflow.sh` is the single definition of how the committed bytes
    are produced, and `make go-verify-binary` re-runs it to prove the committed binary
    still matches this commit's Go source. Both halves of that proof are pinned to one
    version: the output path decides which payload gets overwritten, and the
    `main.version` stamp lands inside the bytes. A script left pointing at a released
    payload would rebuild over immutable bytes and stamp them with the wrong version,
    and `go-verify-binary` would still pass because it compares the file it just wrote.

    Every predecessor proof asserts only the negative — that the script no longer names
    *it*. Those negatives are individually true and collectively vacuous: nothing caught
    that this positive pin was dropped when the 1.7 test's copy became stale at this cut.
    The positive assertion travels with whichever version is current and belongs here.
    """
    build_script = (_ROOT / "scripts/build-gh-workflow.sh").read_text(encoding="utf-8")

    assert f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.8/{_BINARY}"' in (
        build_script
    )
    assert 'ARTIFACT_LDFLAGS="-buildid= -X main.version=1.8"' in build_script


def test_github_workflow_1_8__delivered_units__move_only_the_two_references() -> None:
    """A correction release must not carry a payload rebuild along with it."""
    predecessor_files = _files(_V17)
    successor_files = _files(_V18)

    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()

    # SKILL.md is in the changed set only for its frontmatter version; the routing
    # table, the refusals, and the budget it declares are 1.7's.
    skill = (_V18 / "skills/github-workflow/SKILL.md").read_text(encoding="utf-8")
    assert "  version: '1.8'" in skill
    assert skill.replace("version: '1.8'", "version: '1.7'") == (
        _V17 / "skills/github-workflow/SKILL.md"
    ).read_text(encoding="utf-8")


def test_github_workflow_1_8__rendered_units__are_the_predecessor_bytes() -> None:
    """FR-035's claim to an upgrading consumer: the upgrade is a version bump.

    The managed block must be byte-identical, since reconcile compares bytes and any
    difference rewrites every consumer's instruction file. The policy render is
    identical apart from the `package_version` stamp it interpolates from the payload
    identity — that stamp is what an upgrade is *for*, so it is normalized away rather
    than exempted wholesale.
    """
    assert _options(_V18) == _options(_V17)
    assert _render_block(_V18) == _render_block(_V17)

    policy = _render_policy(_V18)
    assert policy.replace(b'"1.8"', b'"1.7"') == _render_policy(_V17)
    assert b'package_version = "1.8"' in policy
    assert (_V18 / "resources/policy.toml").read_bytes() == (
        _V17 / "resources/policy.toml"
    ).read_bytes()
    assert (_V18 / "config.schema.json").read_bytes() == (_V17 / "config.schema.json").read_bytes()


def test_github_workflow_1_8__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        path.relative_to(_V17).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in payload_tree(_V17)
        if path.is_file()
    }
    assert actual == _V17_FILES
    assert (
        validate_payload_integrity(
            _V17, load_payload_manifest(_V17 / "payload.toml")
        ).aggregate_digest.value
        == _V17_AGGREGATE
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "github-workflow"
    }
    # Withdrawing an advertised package is a catalog-major transition (ADR 0024), so
    # every predecessor stays advertised and only its role moves to `retained`.
    assert roles == {
        **{f"1.{minor}": "retained" for minor in range(8)},
        "1.8": "default",
    }


def test_github_workflow_1_8__records_what_the_cut_changed() -> None:
    """The delivered prose has to name the defect, or an adopter cannot tell why to move."""
    readme = (_V18 / "README.md").read_text(encoding="utf-8")
    assert "# GitHub Workflow Standard 1.8" in readme
    assert "### What 1.8 changed" in readme
    assert "GHW-PR-READY-RISK-INVALID" in readme

    adopt = (_V18 / "adopt.md").read_text(encoding="utf-8")
    assert "# Adopt GitHub Workflow 1.8" in adopt
    assert "### Upgrading from 1.7" in adopt
    assert "# GitHub Workflow 1.8 summary" in (_V18 / "agent-summary.md").read_text(
        encoding="utf-8"
    )


def test_github_workflow_1_8__machine_readable_payload__carries_no_stale_1_7_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.7.

    The sweep covers the declarative files, where a surviving `1.7` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown is excluded because README and
    adopt.md carry this cut's account of what changed, which cannot be written without
    naming 1.7.
    """
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        relative
        for relative, path in _files(_V18).items()
        if path.suffix in {".json", ".toml", ".yml", ".yaml"}
        and re.search(
            r"(?<![\d.])1[.-]7(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()
    assert load_payload_manifest(_V18 / "payload.toml").payload.version.value == "1.8"


def test_github_workflow_1_8__projection_and_index__are_complete() -> None:
    source_files = set(_files(_V18))
    projected_files = {
        path.relative_to(_PROJECTION_18).as_posix()
        for path in payload_tree(_PROJECTION_18)
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_18 / relative).resolve() == (_V18 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in payload_tree(_PROJECTION_18) if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.8"]["payload"] == "versions/1.8/payload.toml"
    assert versions["1.8"]["digest"] == _payload(_V18).integrity.aggregate_digest.value
    assert "github-workflow@1.8" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_github_workflow_1_8__mutable_navigation__names_the_new_authority() -> None:
    for name in ("README.md", "adopt.md", "agent-summary.md"):
        content = (_FAMILY / name).read_text(encoding="utf-8")
        assert "versions/1.8/" in content
        assert "versions/1.7/" not in content
