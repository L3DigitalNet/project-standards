"""Pin the GitHub Workflow 1.9 admission model and its enforcement.

1.9 answers two defects with one cut, because payload bytes are immutable and both
edit the same admission prose (ADR 0031).

Issue #203: 1.8's admission rule attached to "the default branch", which in a
repository whose work lands on a long-lived integration branch is reached only by
fast-forward — so the obligation attached at no moment at all, and the package shipped
no executable enforcement of any kind. Measured over this repository's own history the
rule had zero compliance.

Issue #218: T0 condition 1 requires every hunk to be a prose repair, so an Agent
Handoff closeout could never qualify, and the repository grew a hand-written carve-out
that is exactly the repository-configurable middle ground the standard forbids.

The assertions below are organized around what could silently regress. The four
classes and their trailers are asserted on the *rendered* managed block and on the
delivered reference, because those are the two surfaces an agent actually reads, and
the block is the one a delegated worker is guaranteed to see. The classifier itself is
proven by running the committed binary — first over this repository's own history,
where a clean report would disprove the control, then over a synthetic repository
where every commit is admitted and removing one trailer flips the verdict.

The binary is executed here, unlike in the predecessor suites, which read it only as
bytes. That is the point of the cut: a classifier nobody runs is the gap #203 names.
The runs are guarded by a linux/amd64 skip, since the payload ships that build only.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
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
_V18 = _FAMILY / "versions/1.8"
_V19 = _FAMILY / "versions/1.9"
_PROJECTION_19 = _ROOT / "src/project_standards/payloads/github-workflow/1.9"

_REFERENCES = "skills/github-workflow/references"
_PR_STANDARD = f"{_REFERENCES}/pr-standard.md"
_SKILL = "skills/github-workflow/SKILL.md"
_BINARY = "skills/github-workflow/bin/gh-workflow"

# NFR-006 and NFR-003, both unchanged. 1.9 adds an eleventh subcommand and a four-class
# admission rule to files that had 22 and 8 bytes of headroom, so both budgets were paid
# for by displacement rather than raised: SKILL.md dropped the lifecycle preconditions
# that `pr-standard.md` states and `ready`/`merge` enforce, and the block dropped the
# `Wait for CI` row, the one route that mutates nothing. Measured at this cut: SKILL.md
# 70 lines / 11,997 B, rendered block 2,394 B at a 39-character login.
_SKILL_MAX_LINES = 70
_SKILL_MAX_BYTES = 12000
_BLOCK_MAX_BYTES = 2400
_MAX_LOGIN = "a" * 39

# The four `Workflow-Admission` trailer values ADR 0031 D1 defines. `PR #N` is written
# by `merge` rather than by an author, which is why it is the only one carrying a
# number, and why it is the class a subject heuristic cannot reconstruct.
_TRAILER_KEY = "Workflow-Admission"
_CLASS_TRAILERS = ("T0", "PR #N", "handoff", "release")

# The exempt path set, fixed by the standard (ADR 0031 D2). It appears in three places
# that must agree: this test, the delivered reference, and the compiled binary.
_HANDOFF_PATHS = ("docs/handoff/**", "docs/STATUS.md", "docs/TODO.md")

# The four options 1.9 adds, each a scalar so the tool's bounded `policy.toml` reader is
# unchanged, and each with the default that makes an unconfigured consumer behave as 1.8.
_ADMISSION_OPTIONS = {
    "integration_branch": "",
    "release_subject_prefix": "",
    "admission_floor": "",
    "handoff_admission": "agent-handoff",
}

_V18_AGGREGATE = "sha256:f98d80968f74cacec42711b82265f692368917130365097fe72c29ed0e6356a4"

# The predecessor is advertised and therefore immutable: a byte change anywhere in it is
# a released-payload mutation, not a diff to review (issue #218 criterion 1). Modes are
# asserted alongside the digests because this family is the one payload with an
# executable in it — the binary is 0755 and everything else is 0644, and a projection or
# a repack that flattens that ships a tool the consumer cannot run.
_V18_FILES = {
    "README.md": (0o644, "ffebd8ed57efc81dc55317482d651205fdd69181550837e0aa6f1ced110732fd"),
    "adopt.md": (0o644, "a0adf449b9063e274314b585064cff178960fdc43a05ca05a3b065e38b7fe565"),
    "agent-summary.md": (
        0o644,
        "db4d1076ad8f9ea14536023c68c44f5912dc85edc7a202876c0e0d605258baa6",
    ),
    "config.schema.json": (
        0o644,
        "526d70a62acd7f6663d0b315de87664e50eb8c4b418f965511139def003c388d",
    ),
    "payload.toml": (0o644, "ad8d97979c4082c4cba1160da4f380b20bf3864c1ca54a6c8daf9e29ea50ffe6"),
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
        "a1f010addc7928c230e1d0f9c253cedc5b41973b2ea966261c13d38304fa96af",
    ),
    _SKILL: (0o644, "c6613142866ccf4465b3524dd0b1826ccf7f366130d9026ba28a8d64782e83da"),
    "skills/github-workflow/agents/openai.yaml": (
        0o644,
        "b4a95c41144530b3694e71ab4662de3031bca3c7ef9b9b7a963a5038003998f1",
    ),
    _BINARY: (0o755, "1d118602d768ff2ef5ceba0a377a616f8f4560dc915e10d93a38c201798f0579"),
    f"{_REFERENCES}/field-vocabulary.md": (
        0o644,
        "4600470727d00ea16c0cde3233175b9aaf830ec3dec57fd1f7bf4b7523b7993c",
    ),
    f"{_REFERENCES}/issue-structure.md": (
        0o644,
        "1a0d0c7fbcc01a3e9d255e1c1f2cad83d85fc28be6766e758baf66544068f465",
    ),
    f"{_REFERENCES}/org-schema.yaml": (
        0o644,
        "b8170049e40fd944a3dd78a8b7ab9d153feda90b6df42445863fae5ece03da99",
    ),
    _PR_STANDARD: (0o644, "cfc4253c8b95c9da4c73c3131df1a522f10cc943b571bd56a6a3e9939f448a7c"),
    f"{_REFERENCES}/review-checklist.md": (
        0o644,
        "95ca943ecfc018b7b07f942b7c452cca1a218fc9a7068a951080d363062a808b",
    ),
    f"{_REFERENCES}/summary-format.md": (
        0o644,
        "6e26f8d19e37f41babb7b1da9ff5aa3779e9caf3a1636c999ec276d078dbcb65",
    ),
}

# Both harnesses selected, so every managed block and the policy render are reachable.
_CONFIG: JsonObject = {"organization": "ExampleOrg", "harnesses": ["claude-code", "codex"]}

_LINUX_AMD64 = platform.system() == "Linux" and platform.machine() in {"x86_64", "amd64"}
_requires_binary = pytest.mark.skipif(
    not _LINUX_AMD64, reason="the payload ships a linux/amd64 build of gh-workflow only"
)


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


def _render(root: Path, planned: JsonObject, config: JsonObject | None = None) -> bytes:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="github-workflow",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=_options(root, config),
            snapshots={"planned_contribution": planned},
        )
    )
    assert result.content is not None
    return result.content


def _render_block(root: Path, config: JsonObject | None = None) -> bytes:
    return _render(
        root,
        {
            "id": "instructions-claude",
            "target": "CLAUDE.md",
            "adapter": AdapterKind.MARKDOWN_BLOCK.value,
            "scope": "block:github-workflow",
        },
        config,
    )


def _render_policy(root: Path, config: JsonObject | None = None) -> bytes:
    return _render(
        root,
        {
            "id": "policy",
            "target": ".standards/packages/github-workflow/policy.toml",
            "adapter": AdapterKind.WHOLE_FILE.value,
            "scope": "$file",
        },
        config,
    )


def _block_body(root: Path, login: str = "ExampleOrg") -> str:
    """Return just the block's inner content, as the provider composes it.

    The rendered document carries Prettier range markers and managed begin/end markers
    that the adapter re-emits; the *body* is what NFR-003 budgets and what an agent
    reads, so it is what the assertions below measure.
    """
    document = _render_block(root, {"organization": login, "harnesses": ["claude-code"]}).decode(
        "utf-8"
    )
    body = document.split("<!-- BEGIN project-standards:github-workflow -->\n", 1)[1]
    return body.split("<!-- END project-standards:github-workflow -->", 1)[0]


# ---------------------------------------------------------------------------
# The four classes, on every surface that states them
# ---------------------------------------------------------------------------


def test_github_workflow_1_9__pr_standard__states_the_branch_and_admission_classes() -> None:
    """The reference an author reads before choosing a route (ADR 0031 D1)."""
    text = (_V19 / _PR_STANDARD).read_text(encoding="utf-8")

    for trailer in _CLASS_TRAILERS:
        assert f"`{_TRAILER_KEY}: {trailer}`" in text, f"pr-standard.md omits the {trailer} trailer"
    for option in ("integration_branch", "release_subject_prefix", "admission_floor"):
        assert f"`{option}`" in text
    for path in _HANDOFF_PATHS:
        assert path in text, f"pr-standard.md does not name the exempt path {path}"

    # The mixed-commit rule is #218's own protection against the exemption becoming a
    # wrapper, so it is asserted as a stated rule, not inferred from the path list.
    assert "mixed commit is not a handoff commit" in text.lower()

    # ADR 0031 deletes the orphaned `construction branch` phrase rather than defining
    # it: under D1 the integration branch is governed, which is the opposite of what an
    # undefined "construction branch" implied.
    assert "construction branch" not in text
    assert "There are exactly two admission classes" not in text

    # The coverage gap is stated rather than implied away: 1.9 ships no CI workflow.
    assert "Nothing runs it for you." in text


def test_github_workflow_1_9__skill__routes_admission_and_states_the_four_classes() -> None:
    text = (_V19 / _SKILL).read_text(encoding="utf-8")

    assert "  version: '1.9'" in text
    assert "`admission --branch B [--since REF] [--offline]`" in text
    assert "exactly one of four classes" in text
    assert "not a handoff commit" in text
    assert "A change reaches the default branch one of exactly two ways" not in text


def test_github_workflow_1_9__skill__stays_one_read_within_its_budget() -> None:
    """NFR-006's ceilings and SKILL.md's self-declared line count."""
    skill = (_V19 / _SKILL).read_text(encoding="utf-8")
    lines = skill.splitlines()

    assert len(lines) <= _SKILL_MAX_LINES
    assert len(skill.encode("utf-8")) <= _SKILL_MAX_BYTES

    declared = re.search(r"^  lines: (\d+)$", skill, re.MULTILINE)
    assert declared is not None and int(declared.group(1)) == len(lines)


def test_github_workflow_1_9__managed_block__names_the_classes_and_the_exemption() -> None:
    """Issue #218 criterion 3, asserted on the rendered text an agent actually sees.

    The block is the only package-owned text a delegated worker is guaranteed to read,
    so a rule stated only in `SKILL.md` or `pr-standard.md` does not reach the sessions
    that most need it. That is why the exempt paths are enumerated here rather than
    pointed at.
    """
    body = _block_body(_V19)

    assert f"`{_TRAILER_KEY}` trailer" in body
    for trailer in ("`T0`", "`PR #N`", "`handoff`", "`release`"):
        assert trailer in body, f"the managed block does not name the {trailer} class"
    for path in _HANDOFF_PATHS:
        assert f"`{path}`" in body, f"the managed block does not name the exempt path {path}"
    assert "mixing handoff and other paths is not handoff" in body

    # The 1.8 bullet claimed T0 was the only direct-push class; leaving it beside the
    # new one would state both the two-class and the four-class rule at once.
    assert "is the only autonomous direct push" not in body
    assert "`admission --branch B" in body


def test_github_workflow_1_9__managed_block__stays_within_its_budget() -> None:
    """NFR-003 at the maximum valid login, which is where the ceiling actually binds."""
    assert len(_block_body(_V19, _MAX_LOGIN).encode("utf-8")) <= _BLOCK_MAX_BYTES
    # The measurement varies with the login length, so the ceiling is asserted rather
    # than an equality — but the maximum login must be the largest case.
    assert len(_block_body(_V19, "ExampleOrg").encode("utf-8")) <= len(
        _block_body(_V19, _MAX_LOGIN).encode("utf-8")
    )


# ---------------------------------------------------------------------------
# The four configuration options
# ---------------------------------------------------------------------------


def test_github_workflow_1_9__config_schema__adds_four_defaulted_scalars() -> None:
    """Every new option is optional, scalar, and defaulted (ADR 0031 D1).

    Scalar because the tool parses `policy.toml` with a bounded reader that accepts only
    double-quoted assignments; optional and defaulted because an upgrade from 1.8 that
    changes no configuration must behave exactly as 1.8 did.
    """
    schema = cast(
        "dict[str, object]", json.loads((_V19 / "config.schema.json").read_text(encoding="utf-8"))
    )
    properties = cast("dict[str, dict[str, object]]", schema["properties"])
    required = cast("list[str]", schema["required"])

    assert sorted(required) == ["harnesses", "organization"]
    for name, default in _ADMISSION_OPTIONS.items():
        assert name in properties, f"config.schema.json omits {name}"
        assert properties[name].get("default") == default
        assert name not in required

    assert properties["handoff_admission"]["enum"] == ["agent-handoff", "none"]


def test_github_workflow_1_9__rendered_policy__carries_the_options_as_quoted_scalars() -> None:
    """The rendered file the tool reads, in the only shape its parser accepts."""
    default_policy = _render_policy(_V19).decode("utf-8")
    for name, default in _ADMISSION_OPTIONS.items():
        assert f'{name} = "{default}"' in default_policy

    configured = _render_policy(
        _V19,
        {
            "organization": "ExampleOrg",
            "harnesses": ["codex"],
            "integration_branch": "testing",
            "release_subject_prefix": "release: prepare v",
            "admission_floor": "9c47907f",
            "handoff_admission": "none",
        },
    ).decode("utf-8")
    assert 'integration_branch = "testing"' in configured
    assert 'release_subject_prefix = "release: prepare v"' in configured
    assert 'admission_floor = "9c47907f"' in configured
    assert 'handoff_admission = "none"' in configured

    # No placeholder may survive rendering: an unreplaced `@name@` reaches the consumer
    # as a literal the tool would parse as a real configured value.
    assert "@" not in configured

    assert 'package_version = "1.9"' in default_policy


def test_github_workflow_1_9__organization__refuses_a_login_the_shipped_tool_cannot_load() -> None:
    """Close the render/load asymmetry: `a--b` was accepted here and refused there.

    `ghapi.ValidateLogin` in the shipped binary rejects a doubled hyphen, and it is the
    function that reads the rendered `policy.toml`. Through 1.8 the provider's own check
    omitted that rule, so a consumer could configure `a--b`, watch reconcile report
    success, and then have every subcommand refuse the file it had just written. Both
    boundaries now state the same grammar, and both are asserted here because a schema
    that admits what the provider refuses is the same defect in the other direction.
    """
    schema = cast(
        "dict[str, object]", json.loads((_V19 / "config.schema.json").read_text(encoding="utf-8"))
    )
    pattern = cast("dict[str, dict[str, object]]", schema["properties"])["organization"]["pattern"]
    compiled = re.compile(cast("str", pattern))

    for accepted in ("L3DigitalNet", "a-b", "a", _MAX_LOGIN):
        assert compiled.match(accepted), f"the schema refuses the valid login {accepted}"
    for refused in ("a--b", "-ab", "ab-", "a_b", "a.b"):
        assert not compiled.match(refused), f"the schema accepts the invalid login {refused}"

    # The schema is the outer layer, and it is the one a consumer actually reaches:
    # option resolution refuses `a--b` before any provider runs.
    with pytest.raises(PackageContractError):
        _options(_V19, {"organization": "a--b", "harnesses": ["codex"]})

    # The provider is the inner layer, reached here by handing it an effective config
    # the schema would have rejected. It must refuse independently, because it is what
    # composes the bytes and a future caller could resolve options some other way.
    # The control plane redacts a provider's own message and reports only the exception
    # class, so the assertion is on the refusal and its classification; the message text
    # itself is covered by the provider's own grammar, asserted through the schema above.
    with pytest.raises(ControlPlaneError, match=r"provider failed with ValueError"):
        invoke_provider(
            ProviderInvocation(
                repo=_V19,
                payload=_payload(_V19),
                standard_id="github-workflow",
                version=_payload(_V19).manifest.payload.version,
                provider_id="render-semantic",
                operation=ProviderOperation.RENDER,
                effective_config={"organization": "a--b", "harnesses": ["codex"]},
                snapshots={
                    "planned_contribution": {
                        "id": "policy",
                        "target": ".standards/packages/github-workflow/policy.toml",
                        "adapter": AdapterKind.WHOLE_FILE.value,
                        "scope": "$file",
                    }
                },
            )
        )


# ---------------------------------------------------------------------------
# The classifier, run
# ---------------------------------------------------------------------------


def _run_binary(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the committed 1.9 binary, never a locally built one.

    The point of these cases is that the *shipped bytes* enforce the rule, so the
    payload's own executable is invoked rather than `go run`.
    """
    return subprocess.run(
        [str(_V19 / _BINARY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@_requires_binary
def test_github_workflow_1_9__classifier__flags_this_repository_own_history() -> None:
    """The non-vacuity proof #203 requires, run over the corpus that motivated it.

    ADR 0031 measured 283 unadmitted commits of 362 over `9c47907f..3bda3cf4` with no
    floor. The exact count moves with every commit this repository makes, so the
    assertion is on the *shape* — a large majority unadmitted, a nonzero exit — rather
    than on a number that would have to be edited on every unrelated commit. A clean
    report here would disprove the control, which is the failure this case exists to
    catch.

    `--offline` because the suite must not depend on GitHub authentication or on
    network reachability.
    """
    result = _run_binary(
        ["admission", "--branch", "HEAD", "--since", "9c47907f", "--offline", "--output", "json"],
        cwd=_ROOT,
    )
    if result.returncode == 2 and "reading commits" in result.stdout + result.stderr:
        pytest.skip("the checkout does not contain the 9c47907f epoch")

    assert result.returncode == 1, (
        "the classifier reports this repository's own history as fully admitted; "
        f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}"
    )
    report = cast("dict[str, object]", json.loads(result.stdout))
    counts = cast("dict[str, int]", report["counts"])
    commits = cast("int", report["commits"])

    assert commits > 300, f"the corpus is smaller than the measured epoch: {commits}"
    assert counts["unadmitted"] > 200, f"too few unadmitted commits to be the 1.8 corpus: {counts}"
    # Handoff-only commits exist in this history and are reported as *undeclared*
    # rather than admitted, because the trailer never existed before this cut.
    assert counts["handoff"] == 0
    assert counts["t0"] == 0


@_requires_binary
def test_github_workflow_1_9__classifier__admits_a_clean_corpus_and_fails_when_one_trailer_goes(
    tmp_path: Path,
) -> None:
    """The negative control: the same corpus, one trailer removed, opposite verdict.

    A compliance check that only ever runs against a non-compliant corpus proves it can
    say no. This proves it can say yes, and that the yes is load-bearing.
    """
    repo = tmp_path / "corpus"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=testing")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "commit.gpgsign", "false")
    # A developer's global core.hooksPath is inherited by every `git init`; this
    # workstation's global pre-commit hook refuses any author email but the owner's,
    # which would fail this fixture locally and pass it on CI.
    hooks = repo / ".empty-hooks"
    hooks.mkdir()
    _git(repo, "config", "core.hooksPath", str(hooks))

    _commit(repo, "chore: seed", {"README.md": "seed\n"})
    base = _git(repo, "rev-parse", "HEAD").strip()
    _commit(repo, f"fix: typo\n\n{_TRAILER_KEY}: T0\n", {"README.md": "seed.\n"})
    _commit(repo, f"feat: work\n\n{_TRAILER_KEY}: PR #7\n", {"src/app.py": "x = 1\n"})
    _commit(
        repo,
        f"docs(handoff): close out\n\n{_TRAILER_KEY}: handoff\n",
        {"docs/handoff/state.md": "state\n"},
    )
    _commit(
        repo,
        f"release: prepare v1.0.0\n\n{_TRAILER_KEY}: release\n",
        {"pyproject.toml": "[project]\n"},
    )

    clean = _run_binary(["admission", "--branch", "testing", "--since", base, "--offline"], repo)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "0 unadmitted" in clean.stdout

    # #218 criterion 2 on live bytes: a *mixed* commit is refused even though it
    # declares the handoff class and touches a handoff path.
    _commit(
        repo,
        f"docs(handoff): close out and fix a bug\n\n{_TRAILER_KEY}: handoff\n",
        {"docs/handoff/state.md": "state 2\n", "src/app.py": "x = 2\n"},
    )
    mixed = _run_binary(["admission", "--branch", "testing", "--since", base, "--offline"], repo)
    assert mixed.returncode == 1
    assert "GHW-ADMISSION-HANDOFF-MIXED" in mixed.stdout


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"},
    ).stdout


def _commit(repo: Path, message: str, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


@_requires_binary
def test_github_workflow_1_9__binary__reports_the_version_it_ships_with() -> None:
    """NFR-005: the stamp, the payload directory, and the build script move together."""
    result = _run_binary(["help"], _ROOT)

    assert "1.9" in result.stdout + result.stderr
    assert "admission" in result.stdout + result.stderr


def test_github_workflow_1_9__build_script__targets_this_version() -> None:
    """The reproducible build must name the payload under development, not a released one.

    `scripts/build-gh-workflow.sh` is the single definition of how the committed bytes
    are produced, and `make go-verify-binary` re-runs it to prove the committed binary
    still matches this commit's Go source. A script left pointing at a released payload
    would rebuild over immutable bytes and stamp them with the wrong version, and
    `go-verify-binary` would still pass because it compares the file it just wrote.
    """
    build_script = (_ROOT / "scripts/build-gh-workflow.sh").read_text(encoding="utf-8")

    assert f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.9/{_BINARY}"' in (
        build_script
    )
    assert 'ARTIFACT_LDFLAGS="-buildid= -X main.version=1.9"' in build_script


def test_github_workflow_1_9__binary__is_declared_by_the_payload_it_ships_in() -> None:
    """A rebuilt executable is only delivered if the manifest declares its digest.

    Both artifact rows point at the same source, because reconcile installs the tool
    under `.agents/` and `.claude/`; a digest that agrees with only one of them, or with
    the 1.8 bytes, ships a tool integrity refuses to write.
    """
    committed = _V19 / _BINARY
    digest = f"sha256:{hashlib.sha256(committed.read_bytes()).hexdigest()}"
    manifest = tomllib.loads((_V19 / "payload.toml").read_text(encoding="utf-8"))
    artifacts = {
        entry["id"]: entry for entry in cast("list[dict[str, str]]", manifest["artifacts"])
    }

    assert committed.read_bytes() != (_V18 / _BINARY).read_bytes()
    for artifact_id in ("tool-binary", "tool-binary-claude"):
        assert artifacts[artifact_id]["source"] == _BINARY
        assert artifacts[artifact_id]["digest"] == digest
        assert artifacts[artifact_id]["mode"] == "0755"
    assert stat.S_IMODE(committed.stat().st_mode) == 0o755


def test_github_workflow_1_9__binary__carries_the_admission_vocabulary() -> None:
    """The exempt path set and the finding codes, read from the bytes that ship.

    This is the cross-file contract the standard depends on: the same three paths are
    named in `pr-standard.md`, in the rendered managed block, and in the compiled
    classifier. A change to any one of them without the others produces a tool that
    enforces a different rule from the one it delivers. Go concatenates its string
    literals into one unterminated table, so each assertion is containment.
    """
    binary = (_V19 / _BINARY).read_bytes()

    assert b"docs/handoff/" in binary
    assert b"docs/STATUS.md" in binary
    assert b"docs/TODO.md" in binary
    for code in (
        b"GHW-ADMISSION-MISSING",
        b"GHW-ADMISSION-HANDOFF-MIXED",
        b"GHW-ADMISSION-HANDOFF-UNDECLARED",
        b"GHW-ADMISSION-HANDOFF-DISABLED",
    ):
        assert code in binary
    # The predecessor shipped no classifier at all, which is the gap #203 measured.
    assert b"GHW-ADMISSION-MISSING" not in (_V18 / _BINARY).read_bytes()


# ---------------------------------------------------------------------------
# Payload integrity, immutability, and activation
# ---------------------------------------------------------------------------


def test_github_workflow_1_9__predecessor_tree_and_activation_stay_exact() -> None:
    """Issue #218 criterion 1: 1.8 is advertised, so its bytes may not move."""
    actual = {
        path.relative_to(_V18).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in payload_tree(_V18)
        if path.is_file()
    }
    assert actual == _V18_FILES
    assert (
        validate_payload_integrity(
            _V18, load_payload_manifest(_V18 / "payload.toml")
        ).aggregate_digest.value
        == _V18_AGGREGATE
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
        **{f"1.{minor}": "retained" for minor in range(9)},
        "1.9": "default",
    }


def test_github_workflow_1_9__delivered_units__move_only_the_admission_surfaces() -> None:
    """A feature release still has to say which files it touched, and prove the rest.

    Everything outside this set must survive byte-for-byte from 1.8, which is what
    turns "1.9 changes admission" into a checkable claim rather than a summary.
    """
    changed = frozenset(
        {
            "README.md",
            "adopt.md",
            "agent-summary.md",
            "config.schema.json",
            "payload.toml",
            "providers/gh_workflow.py",
            "resources/policy.toml",
            "schemas/provider-input.schema.json",
            _SKILL,
            _BINARY,
            _PR_STANDARD,
        }
    )
    predecessor_files = _files(_V18)
    successor_files = _files(_V19)

    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - changed:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()


def test_github_workflow_1_9__machine_readable_payload__carries_no_stale_1_8_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.8.

    The sweep covers the declarative files, where a surviving `1.8` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown is excluded because README and
    adopt.md carry this cut's account of what changed, which cannot be written without
    naming 1.8.
    """
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        relative
        for relative, path in _files(_V19).items()
        if path.suffix in {".json", ".toml", ".yml", ".yaml"}
        and re.search(
            r"(?<![\d.])1[.-]8(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()
    assert load_payload_manifest(_V19 / "payload.toml").payload.version.value == "1.9"


def test_github_workflow_1_9__projection_and_index__are_complete() -> None:
    source_files = set(_files(_V19))
    projected_files = {
        path.relative_to(_PROJECTION_19).as_posix()
        for path in payload_tree(_PROJECTION_19)
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_19 / relative).resolve() == (_V19 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in payload_tree(_PROJECTION_19) if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.9"]["payload"] == "versions/1.9/payload.toml"
    assert versions["1.9"]["digest"] == _payload(_V19).integrity.aggregate_digest.value
    assert "github-workflow@1.9" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_github_workflow_1_9__records_what_the_cut_changed() -> None:
    """The delivered prose has to name the defect, or an adopter cannot tell why to move."""
    readme = (_V19 / "README.md").read_text(encoding="utf-8")
    assert "# GitHub Workflow Standard 1.9" in readme
    assert "### What 1.9 changed" in readme
    assert "integration_branch" in readme

    adopt = (_V19 / "adopt.md").read_text(encoding="utf-8")
    assert "# Adopt GitHub Workflow 1.9" in adopt
    assert "### Upgrading from 1.8" in adopt
    assert "handoff_admission" in adopt
    assert "# GitHub Workflow 1.9 summary" in (_V19 / "agent-summary.md").read_text(
        encoding="utf-8"
    )
