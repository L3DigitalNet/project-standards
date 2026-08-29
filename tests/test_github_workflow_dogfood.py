"""Dogfood delivery proofs for the `github-workflow` package (SPEC-GHW1 §3.2, EC-005).

A fixture consumer is bootstrapped, configured, and reconciled against the real
family, then compared with the target tree recorded under
`tests/fixtures/github_workflow/expected/` for each harness selection. That is the
only way to prove EC-005: harness gating lives in `when_any` predicates the payload
declares, so nothing short of an actual reconcile shows which artifacts a
single-harness consumer really receives.

One arrangement is worth stating up front.

*Only pinned modes are asserted.* The payload pins `0755` on the committed binary
and nothing else; every other artifact is created under the consumer's umask, so
demanding `0644` would fail a legitimate `0664` checkout instead of catching a
defect. The fixtures carry the pinned modes only, for that reason.

`validate` and `drift-check` have no generic dispatcher yet, so the provider tests
invoke them directly through `invoke_selected_provider` with a `capture_command_snapshot`
plus `managed_unit_snapshot` input — the same shape the control plane builds for
agent-handoff. `verify` needs no such wiring: the executor dispatches it post-apply
and `ApplyResult.verification_findings` carries its verdict.
"""

from __future__ import annotations

import hashlib
import socket
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, cast

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.command_resolution import (
    capture_command_snapshot,
    invoke_selected_provider,
    managed_unit_snapshot,
    resolve_selected_package,
)
from project_standards.control_plane.diagnostics import ControlFinding
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_payload_manifest,
)
from tests.installed_package import copy_installed_package
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[1]
_FAMILY = _ROOT / "standards/github-workflow"
_VERSION = "1.0"
_PAYLOAD = _FAMILY / f"versions/{_VERSION}"
_FIXTURES = _ROOT / "tests/fixtures/github_workflow"
_SKILL_ROOT = ".agents/skills/github-workflow"
# Both installed skill roots, `.agents/` first so it matches the payload's
# unsuffixed artifact ids (issue #170).
_SKILL_ROOTS = (_SKILL_ROOT, ".claude/skills/github-workflow")
# The first version that installs the second tree; the expected-tree fixtures
# above still describe 1.0, so only the symmetry test selects this one.
_DUAL_TREE_VERSION = "1.3"
# The first version that scopes a skill unit to one root: `agents/openai.yaml` is
# declared under `.agents/` only (issue #175).
_ROOT_SCOPED_VERSION = "1.5"
_POLICY_TARGET = ".standards/packages/github-workflow/policy.toml"
_BLOCK_BEGIN = "<!-- BEGIN project-standards:github-workflow -->"
_BLOCK_END = "<!-- END project-standards:github-workflow -->"

# Never a real login. The provider interpolates this into policy.toml and into the
# instruction block, so a fixture that borrowed the owning organization's name would
# make the NFR-001 payload scan unreadable at a glance.
_ORGANIZATION = "example-fixture-org"

# Harness selections, keyed by the expected-tree fixture that describes each.
_SELECTIONS: dict[str, tuple[str, ...]] = {
    "both": ("claude-code", "codex"),
    "claude-code": ("claude-code",),
    "codex": ("codex",),
}

# The consumer paths the findings providers read come from the selected payload's
# own declarations, exactly as `control_plane.provider_inputs` builds them. Reading
# them from the manifest rather than restating them keeps this harness from becoming
# a third path table that has to be edited before it can see a newly delivered file
# — the failure mode issue #171 fixed, where the `.claude/skills/` copies existed but
# nothing sampled them. Declared-not-globbed still holds: a provider that stopped
# reporting a missing artifact cannot pass, because the snapshot is built from what
# the payload promises rather than from what happens to be on disk.


@dataclass(frozen=True, slots=True)
class _ExpectedTree:
    """The target consumer state one harness selection must reconcile to."""

    files: tuple[str, ...]
    modes: Mapping[str, str]
    blocks: tuple[str, ...]
    blockless: tuple[str, ...]


def _expected_tree(selection: str) -> _ExpectedTree:
    document = tomllib.loads((_FIXTURES / f"expected/{selection}.toml").read_text(encoding="utf-8"))
    return _ExpectedTree(
        files=tuple(cast("list[str]", document["files"])),
        modes=cast("dict[str, str]", document["modes"]),
        blocks=tuple(cast("list[str]", document["blocks"])),
        blockless=tuple(cast("list[str]", document["blockless"])),
    )


def _deny_network(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("github-workflow reconcile attempted network access")


@pytest.fixture(scope="module", autouse=True)
def deny_network_access() -> Iterator[None]:
    """Fail the test rather than the network if anything here opens a socket (NFR-004).

    Module-scoped and autouse so it is installed before the shared `distribution` and
    `reconciled` fixtures build anything; a function-scoped guard would leave the
    reconciles that happen during module-scoped setup unwatched.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "socket", _deny_network)
        patch.setattr(socket, "create_connection", _deny_network)
        yield


@pytest.fixture(scope="module")
def distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    """Project the repository's own package tree exactly as it ships.

    Nothing is synthesized here: catalog 5 advertises `github-workflow` 1.0, so this
    is the real distribution a consumer resolves against, and the reconciles below
    are the real thing rather than a rehearsal. An earlier revision appended a
    catalog row because the family was still unadvertised; keeping that would now
    declare the package twice.

    Dereferencing matters: the projection under `src/project_standards/payloads` is
    a symlink farm into `standards/`, and the distribution must contain real bytes —
    including the committed binary at its tracked 0755 — for reconcile to deliver
    anything. `copy_installed_package` guarantees exactly that while sharing the
    dereferenced bytes across fixtures; see its module docstring for the no-write
    contract that sharing imposes on `payloads/`.
    """
    installed = tmp_path_factory.mktemp("github-workflow-distribution") / "project_standards"
    copy_installed_package(installed)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _reconcile(repo: Path, distribution: InstalledDistribution) -> tuple[ControlFinding, ...]:
    """Plan and apply one reconciliation, returning the post-apply verify findings."""
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success, result.error_code
    return result.verification_findings


def _consumer(
    root: Path,
    distribution: InstalledDistribution,
    harnesses: tuple[str, ...],
    version: str = _VERSION,
) -> Path:
    """Seed, configure, and reconcile one fixture consumer repository.

    `version` pins the selection explicitly rather than resolving `latest`, so the
    expected-tree fixtures below keep describing the exact payload they were
    recorded against. The dual-skill-tree test overrides it, because the second
    tree only exists from 1.3 onward.
    """
    repo = root / "consumer"
    repo.mkdir(parents=True)
    # Consumer-owned prose already in the instruction files: reconcile must insert
    # the managed block beside it, not replace the file.
    for name in ("AGENTS", "CLAUDE"):
        (repo / f"{name}.md").write_text(
            (_FIXTURES / f"seed/{name}.txt").read_text(encoding="utf-8"), encoding="utf-8"
        )
    initialize_control_plane(repo, "5", distribution=distribution)
    config = repo / ".standards/config.toml"
    selection = ", ".join(f'"{harness}"' for harness in harnesses)
    config.write_text(
        config.read_text(encoding="utf-8")
        + "\n[standards.github-workflow]\n"
        + "enabled = true\n"
        + f'version = "{version}"\n\n'
        + "[standards.github-workflow.config]\n"
        + f'organization = "{_ORGANIZATION}"\n'
        + f"harnesses = [{selection}]\n",
        encoding="utf-8",
    )
    assert _reconcile(repo, distribution) == ()
    return repo


@pytest.fixture(scope="module")
def reconciled(
    tmp_path_factory: pytest.TempPathFactory,
    distribution: InstalledDistribution,
) -> Mapping[str, Path]:
    """One reconciled consumer per harness selection, shared by read-only tests.

    A reconcile costs seconds, and the inspection tests below only read. Tests that
    seed drift must NOT use this fixture — they build their own consumer, because a
    tamper here would leak into every later test in the module.
    """
    root = tmp_path_factory.mktemp("github-workflow-consumers")
    return {
        selection: _consumer(root / selection, distribution, harnesses)
        for selection, harnesses in _SELECTIONS.items()
    }


def _delivered_files(repo: Path) -> tuple[str, ...]:
    """List package-owned whole-file paths, excluding control-plane state.

    `.standards/catalog.toml`, `config.toml`, and `lock.toml` belong to the control
    plane and exist for every consumer regardless of selection, so including them
    would put three constants in every expected-tree fixture and prove nothing.
    """
    control_state = {".standards/catalog.toml", ".standards/config.toml", ".standards/lock.toml"}
    found: list[str] = []
    for path in payload_tree(repo):
        if not path.is_file():
            continue
        relative = path.relative_to(repo).as_posix()
        if relative in control_state or relative in {"AGENTS.md", "CLAUDE.md"}:
            continue
        found.append(relative)
    return tuple(sorted(found))


def _block_body(path: Path) -> str | None:
    """Return the managed block's inner text, or None when the file carries none."""
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").split("\n")
    if _BLOCK_BEGIN not in lines or _BLOCK_END not in lines:
        return None
    begin = lines.index(_BLOCK_BEGIN)
    return "\n".join(lines[begin + 1 : lines.index(_BLOCK_END, begin + 1)])


def _tree_digests(repo: Path) -> dict[str, str]:
    return {
        relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest()
        for relative in _delivered_files(repo)
    }


# ---------------------------------------------------------------------------
# EC-005: the delivered tree per harness selection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("selection", sorted(_SELECTIONS), ids=sorted(_SELECTIONS))
def test_github_workflow_dogfood__reconcile__reproduces_the_target_tree(
    reconciled: Mapping[str, Path],
    selection: str,
) -> None:
    assert _delivered_files(reconciled[selection]) == _expected_tree(selection).files


@pytest.mark.parametrize("selection", sorted(_SELECTIONS), ids=sorted(_SELECTIONS))
def test_github_workflow_dogfood__delivered_artifacts__carry_their_pinned_modes(
    reconciled: Mapping[str, Path],
    selection: str,
) -> None:
    # The binary is the only artifact whose mode the payload pins, and an executable
    # bit lost in delivery makes the skill's tool unusable while every digest still
    # matches — a failure no content check would ever see.
    expected = _expected_tree(selection)
    repo = reconciled[selection]

    observed = {
        relative: format((repo / relative).stat().st_mode & 0o777, "04o")
        for relative in expected.modes
    }
    assert observed == dict(expected.modes)


@pytest.mark.parametrize("selection", sorted(_SELECTIONS), ids=sorted(_SELECTIONS))
def test_github_workflow_dogfood__instruction_blocks__land_only_in_selected_harnesses(
    reconciled: Mapping[str, Path],
    selection: str,
) -> None:
    expected = _expected_tree(selection)
    repo = reconciled[selection]

    for name in expected.blocks:
        body = _block_body(repo / name)
        assert body is not None, f"{name} carries no managed block"
        assert _ORGANIZATION in body
    for name in expected.blockless:
        assert _block_body(repo / name) is None, f"{name} carries an unexpected managed block"


@pytest.mark.parametrize("selection", sorted(_SELECTIONS), ids=sorted(_SELECTIONS))
def test_github_workflow_dogfood__consumer_prose__survives_block_insertion(
    reconciled: Mapping[str, Path],
    selection: str,
) -> None:
    repo = reconciled[selection]

    for name in ("AGENTS", "CLAUDE"):
        seeded = (_FIXTURES / f"seed/{name}.txt").read_text(encoding="utf-8")
        assert seeded in (repo / f"{name}.md").read_text(encoding="utf-8")


def test_github_workflow_dogfood__rendered_policy__carries_the_configured_organization(
    reconciled: Mapping[str, Path],
) -> None:
    rendered = tomllib.loads((reconciled["both"] / _POLICY_TARGET).read_text(encoding="utf-8"))

    assert rendered == {"organization": _ORGANIZATION, "package_version": _VERSION}


# ---------------------------------------------------------------------------
# NFR-004: offline determinism
# ---------------------------------------------------------------------------


def test_github_workflow_dogfood__independent_reconciles__produce_identical_bytes(
    tmp_path: Path,
    distribution: InstalledDistribution,
) -> None:
    # Two consumers, same configuration, no shared state. Byte equality across them
    # is the determinism claim; a no-op second reconcile of one repository would
    # only prove that nothing happened.
    first = _consumer(tmp_path / "a", distribution, _SELECTIONS["both"])
    second = _consumer(tmp_path / "b", distribution, _SELECTIONS["both"])

    assert _tree_digests(first) == _tree_digests(second)
    assert _block_body(first / "CLAUDE.md") == _block_body(second / "CLAUDE.md")


def test_github_workflow_dogfood__reconciling_a_clean_consumer__changes_nothing(
    tmp_path: Path,
    distribution: InstalledDistribution,
) -> None:
    repo = _consumer(tmp_path, distribution, _SELECTIONS["both"])
    before = _tree_digests(repo)

    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    if plan.applicable:
        assert apply_reconciliation(ApplyRequest(request, plan)).success

    assert _tree_digests(repo) == before


# ---------------------------------------------------------------------------
# Provider behavior: validate / verify / drift-check
# ---------------------------------------------------------------------------


def _findings(
    repo: Path,
    distribution: InstalledDistribution,
    operation: ProviderOperation,
) -> tuple[ControlFinding, ...]:
    """Invoke one findings provider directly with the input the control plane builds."""
    selected = resolve_selected_package(repo, "github-workflow", distribution)
    assert selected is not None
    manifest = selected.payload.manifest
    declared = sorted(
        {artifact.target.original for artifact in manifest.artifacts}
        | {contribution.target.original for contribution in manifest.contributions},
        key=str.encode,
    )
    snapshots: JsonObject = capture_command_snapshot(selected.repo, tuple(declared))
    # The providers read expected digests from the lock rather than re-hashing
    # payload resources: github-workflow declares the delivered files as artifact
    # sources only, so their bytes never reach a provider as resources.
    snapshots["managed_units"] = managed_unit_snapshot(selected.lock, "github-workflow")
    return invoke_selected_provider(selected, operation, snapshots).findings


_FINDINGS_OPERATIONS = (
    ProviderOperation.VALIDATE,
    ProviderOperation.VERIFY,
    ProviderOperation.DRIFT_CHECK,
)


@pytest.mark.parametrize("selection", sorted(_SELECTIONS), ids=sorted(_SELECTIONS))
def test_github_workflow_dogfood__clean_consumer__reports_no_findings(
    reconciled: Mapping[str, Path],
    distribution: InstalledDistribution,
    selection: str,
) -> None:
    repo = reconciled[selection]

    assert {
        operation: _findings(repo, distribution, operation) for operation in _FINDINGS_OPERATIONS
    } == dict.fromkeys(_FINDINGS_OPERATIONS, ())


def _tamper_payload_bytes(repo: Path) -> None:
    (repo / f"{_SKILL_ROOT}/SKILL.md").write_text("tampered\n", encoding="utf-8")


def _tamper_pinned_mode(repo: Path) -> None:
    (repo / f"{_SKILL_ROOT}/bin/gh-workflow").chmod(0o644)


def _tamper_missing_artifact(repo: Path) -> None:
    (repo / f"{_SKILL_ROOT}/references/org-schema.yaml").unlink()


def _tamper_rendered_policy(repo: Path) -> None:
    policy = repo / _POLICY_TARGET
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(_ORGANIZATION, "someone-else"),
        encoding="utf-8",
    )


def _tamper_managed_block(repo: Path) -> None:
    claude = repo / "CLAUDE.md"
    claude.write_text(
        claude.read_text(encoding="utf-8").replace(
            "A nontrivial pull request links the issue that governs it.",
            "Pull requests need no issue.",
        ),
        encoding="utf-8",
    )


_TAMPERS: dict[str, tuple[str, str]] = {
    "payload-artifact-bytes": ("GHW-DRIFT", f"{_SKILL_ROOT}/SKILL.md"),
    "pinned-artifact-mode": ("GHW-DRIFT", f"{_SKILL_ROOT}/bin/gh-workflow"),
    "missing-artifact": ("GHW-DRIFT", f"{_SKILL_ROOT}/references/org-schema.yaml"),
    "rendered-policy": ("GHW-DRIFT", _POLICY_TARGET),
    "managed-block": ("GHW-DRIFT", "CLAUDE.md"),
}


@pytest.mark.parametrize("kind", sorted(_TAMPERS), ids=sorted(_TAMPERS))
def test_github_workflow_dogfood__seeded_tamper__is_reported_per_artifact_class(
    tmp_path: Path,
    distribution: InstalledDistribution,
    kind: str,
) -> None:
    # One tamper per class the providers classify differently — verbatim payload
    # bytes, a pinned mode, an absent file, a rendered file, and a bounded block —
    # because a provider that only compared content digests would pass four of them.
    # All three findings operations are asserted against a single reconcile: they
    # share one implementation, so what matters is that each is reachable and agrees.
    seeds = {
        "payload-artifact-bytes": _tamper_payload_bytes,
        "pinned-artifact-mode": _tamper_pinned_mode,
        "missing-artifact": _tamper_missing_artifact,
        "rendered-policy": _tamper_rendered_policy,
        "managed-block": _tamper_managed_block,
    }
    expected = [_TAMPERS[kind]]
    repo = _consumer(tmp_path, distribution, _SELECTIONS["both"])

    seeds[kind](repo)

    observed = {
        operation: [
            (finding.code, finding.path) for finding in _findings(repo, distribution, operation)
        ]
        for operation in _FINDINGS_OPERATIONS
    }
    assert observed == dict.fromkeys(_FINDINGS_OPERATIONS, expected)


def test_github_workflow_dogfood__skill_tree_tamper__is_reported_in_either_root(
    tmp_path: Path,
    distribution: InstalledDistribution,
) -> None:
    """Issue #171: the two installed skill trees get identical provider coverage.

    Asserted as an equivalence rather than two independent expectations, because the
    defect this pins was not a wrong finding but a missing one: before the fix the
    `.claude/` copy produced an empty findings list that looked exactly like a clean
    tree. Normalizing the root away and comparing the two results is what makes
    "reported at all" and "reported the same way" one assertion.
    """
    relative = "references/pr-standard.md"
    observed: dict[str, list[tuple[str, str, str]]] = {}
    for root in _SKILL_ROOTS:
        repo = _consumer(
            tmp_path / root.replace("/", "_"),
            distribution,
            _SELECTIONS["both"],
            version=_DUAL_TREE_VERSION,
        )
        (repo / f"{root}/{relative}").write_text("tampered\n", encoding="utf-8")

        observed[root] = [
            (
                finding.code,
                finding.path.replace(f"{root}/", "", 1),
                # The identity is the payload artifact id, which differs by design:
                # the `.claude/` copy carries the `-claude` suffix. Normalizing it
                # keeps that intended difference from hiding an unintended one.
                finding.identity.removesuffix("-claude"),
            )
            for finding in _findings(repo, distribution, ProviderOperation.DRIFT_CHECK)
        ]

    agents_root, claude_root = _SKILL_ROOTS
    assert observed[agents_root] == [("GHW-DRIFT", relative, "reference-pr-standard")]
    assert observed[claude_root] == observed[agents_root]


def test_github_workflow_dogfood__root_scoped_companion__leaves_a_clean_consumer(
    tmp_path: Path,
    distribution: InstalledDistribution,
) -> None:
    """Issue #175: nothing may demand a `.claude/` copy the payload never installs.

    This reconciles 1.5 rather than inspecting a table, because the defect was only
    visible end to end: the payload dropped `skill-openai-claude`, the provider kept
    expanding the unit over both roots, and every reconcile of a correct tree then
    reported GHW-DRIFT for a file no reconcile had ever written. A Codex-selecting
    consumer is used so the harness gate cannot mask the missing target.
    """
    repo = _consumer(tmp_path, distribution, _SELECTIONS["both"], version=_ROOT_SCOPED_VERSION)

    assert (repo / f"{_SKILL_ROOT}/agents/openai.yaml").is_file()
    assert not (repo / ".claude/skills/github-workflow/agents/openai.yaml").exists()
    assert _findings(repo, distribution, ProviderOperation.DRIFT_CHECK) == ()


def test_github_workflow_dogfood__unselected_harness_artifact__is_profile_drift(
    tmp_path: Path,
    distribution: InstalledDistribution,
) -> None:
    # EC-005's failure mode after a harness is dropped: the Codex companion is stale
    # ownership rather than tampering, so it gets its own code and its own hint.
    repo = _consumer(tmp_path, distribution, _SELECTIONS["claude-code"])
    stray = repo / f"{_SKILL_ROOT}/agents/openai.yaml"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("name: stale\n", encoding="utf-8")

    findings = _findings(repo, distribution, ProviderOperation.DRIFT_CHECK)

    assert [(finding.code, finding.path) for finding in findings] == [
        ("GHW-PROFILE-DRIFT", f"{_SKILL_ROOT}/agents/openai.yaml")
    ]


def test_github_workflow_dogfood__unselected_harness_block__is_profile_drift(
    tmp_path: Path,
    distribution: InstalledDistribution,
) -> None:
    repo = _consumer(tmp_path, distribution, _SELECTIONS["codex"])
    claude = repo / "CLAUDE.md"
    agents_text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    claude.write_text(agents_text, encoding="utf-8")

    findings = _findings(repo, distribution, ProviderOperation.DRIFT_CHECK)

    assert [(finding.code, finding.path) for finding in findings] == [
        ("GHW-PROFILE-DRIFT", "CLAUDE.md")
    ]


def test_github_workflow_dogfood__delivered_bytes__match_the_payload_sources(
    reconciled: Mapping[str, Path],
) -> None:
    # Delivery is a verbatim copy for every artifact; only policy.toml and the
    # instruction blocks are rendered. Comparing against the payload sources catches
    # a delivery path that normalized, re-encoded, or truncated bytes en route.
    repo = reconciled["both"]
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")

    for artifact in manifest.artifacts:
        delivered = repo / artifact.target.original
        assert delivered.read_bytes() == (_PAYLOAD / artifact.source.original).read_bytes()
