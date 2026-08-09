"""Render, validate, verify, drift-check, and refresh GitHub Workflow payload data.

Two of this package's consumer outputs cannot be pinned to a payload digest because
they are rendered from consumer configuration: the bounded Markdown block in the
agent-instruction files, and `.standards/packages/github-workflow/policy.toml`. This
module is the single authority for both shapes, so render and the three findings
operations agree by construction rather than by imitation.

The package deliberately declares no `scaffold` and no `migrate` provider (spec
FR-012): every delivered artifact is `managed`, so ordinary reconcile already owns
each byte, and the family has no legacy predecessor to import. Nothing here opens a
socket or imports a network client — reconcile, drift-check, and upgrade are offline
and deterministic (spec C-002, NFR-004).
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from typing import cast

# Repository-relative homes of every delivered artifact. The skill reads the policy
# from this exact path and the tool defaults to it (`internal/ghworkflow/cli`
# DefaultPolicyPath), so the three must move together.
_SKILL_ROOT = ".agents/skills/github-workflow"
_POLICY_TARGET = ".standards/packages/github-workflow/policy.toml"
_BLOCK_MARKER = "github-workflow"
_BLOCK_SCOPE = f"block:{_BLOCK_MARKER}"

_PRETTIER_START = "<!-- prettier-ignore-start -->"
_PRETTIER_END = "<!-- prettier-ignore-end -->"
_BLOCK_BEGIN = f"<!-- BEGIN project-standards:{_BLOCK_MARKER} -->"
_BLOCK_END = f"<!-- END project-standards:{_BLOCK_MARKER} -->"

_SUPPORTED_HARNESSES = frozenset({"claude-code", "codex"})

# Every whole-file artifact, keyed by its consumer target: (payload artifact id,
# required mode, harness that must be selected for it to materialize). The mode is
# asserted only where the payload pins one — an ordinary artifact inherits the
# consumer umask, so demanding `0644` would report drift on a legitimate `0664` tree.
_ARTIFACTS: dict[str, tuple[str, str | None, str | None]] = {
    f"{_SKILL_ROOT}/SKILL.md": ("skill", None, None),
    f"{_SKILL_ROOT}/agents/openai.yaml": ("skill-openai", None, "codex"),
    f"{_SKILL_ROOT}/bin/gh-workflow": ("tool-binary", "0755", None),
    f"{_SKILL_ROOT}/references/field-vocabulary.md": ("reference-field-vocabulary", None, None),
    f"{_SKILL_ROOT}/references/issue-structure.md": ("reference-issue-structure", None, None),
    f"{_SKILL_ROOT}/references/org-schema.yaml": ("reference-org-schema", None, None),
    f"{_SKILL_ROOT}/references/pr-standard.md": ("reference-pr-standard", None, None),
    f"{_SKILL_ROOT}/references/review-checklist.md": ("reference-review-checklist", None, None),
    f"{_SKILL_ROOT}/references/summary-format.md": ("reference-summary-format", None, None),
}

# Harness → (instruction file, payload contribution id). Codex reads AGENTS.md and
# Claude Code reads CLAUDE.md; a harness the consumer did not select receives nothing.
_BLOCKS: dict[str, tuple[str, str]] = {
    "claude-code": ("CLAUDE.md", "claude-instructions"),
    "codex": ("AGENTS.md", "agents-instructions"),
}


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _config(request: Mapping[str, object]) -> Mapping[str, object]:
    return _table(request.get("config"), name="config")


def _snapshots(request: Mapping[str, object]) -> Mapping[str, object]:
    return _table(request.get("snapshots"), name="snapshots")


def _version(request: Mapping[str, object]) -> str:
    version = request.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("request omitted the package version")
    return version


def _harnesses(config: Mapping[str, object]) -> frozenset[str]:
    raw = config.get("harnesses")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("config.harnesses must be a string array")
    values = cast("list[object] | tuple[object, ...]", raw)
    if not all(isinstance(item, str) for item in values):
        raise ValueError("config.harnesses must be a string array")
    selected = frozenset(cast("list[str] | tuple[str, ...]", values))
    if not selected or not selected.issubset(_SUPPORTED_HARNESSES):
        raise ValueError("config.harnesses contains an unsupported harness")
    return selected


def _organization(config: Mapping[str, object]) -> str:
    """Return the configured login, refusing anything outside GitHub's alphabet.

    This is a containment boundary, not a convenience check. The value is
    interpolated into a TOML string and into Markdown prose, and the tool later
    interpolates it into an API request path; the tool's own reader refuses quotes,
    backslashes, and non-login characters, so a value that would produce a policy
    file the tool cannot parse is rejected here, while rendering, rather than
    written and discovered at audit time.
    """
    value = config.get("organization")
    if not isinstance(value, str) or not value:
        raise ValueError("config.organization must be a nonempty string")
    if len(value) > 39 or value.startswith("-") or value.endswith("-"):
        raise ValueError("config.organization is not a valid GitHub login")
    if not all(
        character.isascii() and (character.isalnum() or character == "-") for character in value
    ):
        raise ValueError("config.organization is not a valid GitHub login")
    return value


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _block_body(organization: str) -> str:
    """Return the block's inner content: the skill mandate and standing invariants.

    Twelve content lines by design (spec NFR-003). This text is loaded by every
    session in a consuming repository whether or not GitHub work is in scope, so it
    carries only the rules that are expensive to violate when the skill was never
    loaded — the five standing invariants of the Glossary — and never the field
    vocabulary or issue-body structure, which live behind the skill's references.
    """
    return (
        "<!-- markdownlint-disable MD025 -->\n"
        "# GitHub Workflow\n"
        "\n"
        "Load the repo-local `github-workflow` skill before creating or mutating GitHub "
        "work state — issues, field values, pull requests, lifecycle transitions, "
        "milestones — before triage, and before an organization-schema audit. This "
        f"repository's work belongs to the `{organization}` organization. These rules "
        "bind even when the skill was never loaded:\n"
        "\n"
        "- Never infer readiness: an open issue is not `Ready` until acceptance criteria "
        "exist and it was deliberately admitted to the executable queue.\n"
        "- Never promote your own `Execution mode`, and never create, rename, or retire "
        "an organization issue type, field, or value — that schema is human-applied.\n"
        "- A nontrivial pull request links the issue that governs it.\n"
        "- Keep terminal state synchronized: `Done` closes as completed, `Dropped` closes "
        "as not planned, and a reopened issue returns to a nonterminal `Workflow` value "
        "in the same action.\n"
        "- Durable follow-up work discovered while implementing becomes an issue before "
        "the session ends.\n"
        "\n"
        "<!-- markdownlint-enable MD025 -->\n"
    )


def _block_document(organization: str) -> str:
    """Wrap the block body in the exact envelope the Markdown adapter parses.

    The control plane does not hand a bare fragment to the adapter: it calls
    `inspect()` on whatever a render provider returns and requires the declared scope
    to be found inside it, so the provider must emit a complete document — Prettier
    range markers, managed begin/end markers, and the blank lines between them. The
    adapter re-emits this same envelope when it writes the consumer file, so any
    drift in this shape becomes an unparseable managed block rather than a diff.
    """
    return (
        f"{_PRETTIER_START}\n"
        "\n"
        f"{_BLOCK_BEGIN}\n"
        f"{_block_body(organization)}"
        f"{_BLOCK_END}\n"
        "\n"
        f"{_PRETTIER_END}\n"
    )


def _policy_document(resources: Mapping[str, bytes], organization: str, version: str) -> str:
    """Fill the pinned policy template; the payload owns every other byte (DR-002)."""
    template = resources.get("policy-template")
    if template is None:
        raise ValueError("render requires the policy template resource")
    return (
        template.decode("utf-8")
        .replace("@organization@", organization)
        .replace("@package_version@", version)
    )


def run_render_semantic(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, str]:
    """Render one bounded contribution from consumer configuration."""
    config = _config(request)
    planned = _table(_snapshots(request).get("planned_contribution"), name="planned contribution")
    target = planned.get("target")
    adapter = planned.get("adapter")
    scope = planned.get("scope")
    organization = _organization(config)
    if adapter == "markdown-block" and scope == _BLOCK_SCOPE:
        return {"content": _block_document(organization)}
    if adapter == "whole-file" and target == _POLICY_TARGET:
        return {"content": _policy_document(resources, organization, _version(request))}
    raise ValueError("unsupported GitHub Workflow semantic contribution")


def _finding(
    code: str,
    path: str,
    identity: str,
    message: str,
    hint: str,
) -> dict[str, object]:
    """Build one findings-schema entry.

    Every rule this package owns reports an exact-byte or presence mismatch against
    an immutable payload, so there is no advisory tier to express and no severity
    parameter to pass. Nothing here locates a line or a locus either: the remedy is
    always to reconcile the whole unit, never to edit one position in it.
    """
    return {
        "code": code,
        "severity": "error",
        "path": path,
        "identity": identity,
        "message": message,
        "hint": hint,
        "line": None,
        "locus": None,
    }


_RECONCILE_HINT = "reconcile the selected GitHub Workflow package"
_PROFILE_HINT = "reconcile after changing the selected harnesses"


def _entry(snapshots: Mapping[str, object], path: str) -> Mapping[str, object]:
    state = snapshots.get(path)
    if not isinstance(state, Mapping):
        return {}
    return _table(cast("Mapping[str, object]", state), name=path)


def _content(entry: Mapping[str, object]) -> bytes | None:
    """Decode a snapshot's captured bytes, when the caller captured any.

    Callers differ on purpose: post-apply verification and the command snapshot both
    carry `content_base64`, while the planner's snapshot carries digests only. Every
    check that needs real bytes therefore degrades to a digest comparison rather than
    inventing content it was not given.
    """
    encoded = entry.get("content_base64")
    if entry.get("kind") != "regular" or not isinstance(encoded, str):
        return None
    try:
        return base64.b64decode(encoded, validate=True)
    except ValueError:
        return None


def _units(snapshots: Mapping[str, object]) -> dict[tuple[str, str], Mapping[str, object]]:
    """Index the caller's lock-bound managed units by (target, scope).

    These are the digests the control plane recorded when it published the package,
    so they are the only expected-byte authority available to a provider: a payload
    path may be declared once, as an artifact source or as a resource but never both,
    so the delivered skill, references, and binary are unreachable as provider
    resources and cannot be re-hashed here.
    """
    raw = snapshots.get("managed_units")
    if not isinstance(raw, (list, tuple)):
        return {}
    indexed: dict[tuple[str, str], Mapping[str, object]] = {}
    for item in cast("list[object] | tuple[object, ...]", raw):
        if not isinstance(item, Mapping):
            continue
        unit = cast("Mapping[str, object]", item)
        target = unit.get("target")
        scope = unit.get("scope")
        if isinstance(target, str) and isinstance(scope, str):
            indexed[(target, scope)] = unit
    return indexed


def _whole_file_findings(
    path: str,
    identity: str,
    entry: Mapping[str, object],
    mode: str | None,
    units: Mapping[tuple[str, str], Mapping[str, object]],
) -> list[dict[str, object]]:
    if entry.get("kind") != "regular":
        return [
            _finding(
                "GHW-DRIFT",
                path,
                identity,
                "managed GitHub Workflow artifact is missing or is not a regular file",
                _RECONCILE_HINT,
            )
        ]
    if mode is not None and entry.get("mode") != mode:
        return [
            _finding(
                "GHW-DRIFT",
                path,
                identity,
                "managed GitHub Workflow artifact does not carry its pinned mode",
                _RECONCILE_HINT,
            )
        ]
    unit = units.get((path, "$file"))
    expected = unit.get("content_digest") if unit is not None else None
    if isinstance(expected, str) and entry.get("content_digest") != expected:
        return [
            _finding(
                "GHW-DRIFT",
                path,
                identity,
                "managed GitHub Workflow bytes differ from the published package",
                _RECONCILE_HINT,
            )
        ]
    return []


def _rendered_findings(
    path: str,
    identity: str,
    entry: Mapping[str, object],
    expected: bytes,
) -> list[dict[str, object]]:
    """Compare one rendered whole-file target against a fresh render of itself."""
    if entry.get("kind") != "regular":
        return [
            _finding(
                "GHW-DRIFT",
                path,
                identity,
                "rendered GitHub Workflow artifact is missing or is not a regular file",
                _RECONCILE_HINT,
            )
        ]
    observed = _content(entry)
    digest = entry.get("content_digest")
    if observed is not None:
        matches = observed == expected
    elif isinstance(digest, str):
        matches = digest == _digest(expected)
    else:
        # The caller captured neither bytes nor a digest for a file it says is
        # regular. Nothing here can distinguish drift from an incomplete snapshot,
        # so stay silent rather than manufacture a finding.
        return []
    if matches:
        return []
    return [
        _finding(
            "GHW-DRIFT",
            path,
            identity,
            "rendered GitHub Workflow artifact does not match the configured package",
            _RECONCILE_HINT,
        )
    ]


def _observed_block(content: bytes) -> str | None:
    """Return the managed block's inner text, or `None` when the file carries none.

    Deliberately a bounded marker scan rather than a Markdown parse: the provider
    only ever answers "is this package's block present and current", and the adapter
    already rejects malformed or duplicated envelopes before a file reaches here.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return None
    lines = text.replace("\r\n", "\n").split("\n")
    try:
        begin = lines.index(_BLOCK_BEGIN)
        end = lines.index(_BLOCK_END, begin + 1)
    except ValueError:
        return None
    return "".join(f"{line}\n" for line in lines[begin + 1 : end])


def _block_findings(
    request: Mapping[str, object],
    harnesses: frozenset[str],
    organization: str,
) -> list[dict[str, object]]:
    snapshots = _snapshots(request)
    units = _units(snapshots)
    expected = _block_body(organization)
    findings: list[dict[str, object]] = []
    for harness, (path, identity) in _BLOCKS.items():
        entry = _entry(snapshots, path)
        observed = _content(entry)
        present = None if observed is None else _observed_block(observed)
        if harness not in harnesses:
            # A block for an unselected harness is stale ownership, not tampering:
            # the consumer dropped the harness and reconcile has not run since.
            if present is not None:
                findings.append(
                    _finding(
                        "GHW-PROFILE-DRIFT",
                        path,
                        identity,
                        "GitHub Workflow block exists for an unselected harness",
                        _PROFILE_HINT,
                    )
                )
            continue
        if observed is None:
            unit = units.get((path, _BLOCK_SCOPE))
            recorded = unit.get("semantic_digest") if unit is not None else None
            if isinstance(recorded, str) and recorded != _digest(expected.encode("utf-8")):
                findings.append(
                    _finding(
                        "GHW-DRIFT",
                        path,
                        identity,
                        "recorded GitHub Workflow block does not match the configured package",
                        _RECONCILE_HINT,
                    )
                )
            continue
        if present != expected:
            findings.append(
                _finding(
                    "GHW-DRIFT",
                    path,
                    identity,
                    "GitHub Workflow block is missing or differs from the configured package",
                    _RECONCILE_HINT,
                )
            )
    return findings


def _findings(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> list[dict[str, object]]:
    """Report every delivered artifact and contribution that is not as published."""
    config = _config(request)
    snapshots = _snapshots(request)
    harnesses = _harnesses(config)
    organization = _organization(config)
    units = _units(snapshots)
    findings: list[dict[str, object]] = []

    for path, (identity, mode, gate) in _ARTIFACTS.items():
        entry = _entry(snapshots, path)
        if gate is not None and gate not in harnesses:
            if entry.get("kind") == "regular":
                findings.append(
                    _finding(
                        "GHW-PROFILE-DRIFT",
                        path,
                        identity,
                        "GitHub Workflow artifact exists for an unselected harness",
                        _PROFILE_HINT,
                    )
                )
            continue
        findings.extend(_whole_file_findings(path, identity, entry, mode, units))

    findings.extend(
        _rendered_findings(
            _POLICY_TARGET,
            "policy",
            _entry(snapshots, _POLICY_TARGET),
            _policy_document(resources, organization, _version(request)).encode("utf-8"),
        )
    )
    findings.extend(_block_findings(request, harnesses, organization))
    return findings


def run_validate(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Validate delivered artifacts, rendered policy, and the managed blocks."""
    return {"findings": _findings(request, resources)}


def run_verify(request: Mapping[str, object], resources: Mapping[str, bytes]) -> dict[str, object]:
    """Verify post-apply that every declared unit was published as planned."""
    return {"findings": _findings(request, resources)}


def run_drift_check(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Report standard-owned artifact and contribution drift."""
    return {"findings": _findings(request, resources)}


def run_upgrade(request: Mapping[str, object], resources: Mapping[str, bytes]) -> dict[str, object]:
    """Return a typed refresh plan for the rendered consumer policy.

    Upgrade is bounded to `policy.toml` because it is the only delivered file whose
    correct bytes depend on something reconcile cannot copy: the package version and
    the consumer's configured organization. Every other artifact is a verbatim
    payload byte-copy that ordinary reconcile already refreshes, and the managed
    block lives inside a consumer-owned file that no whole-file action may rewrite.
    """
    authoring = _table(_snapshots(request).get("authoring"), name="authoring")
    target = authoring.get("target")
    precondition = authoring.get("precondition_digest")
    mode = authoring.get("mode")
    if target != _POLICY_TARGET:
        raise ValueError("upgrade target is not the rendered GitHub Workflow policy")
    if authoring.get("kind") != "regular" or authoring.get("overwrite") is not True:
        raise ValueError("upgrade requires explicit verified overwrite authorization")
    if not isinstance(precondition, str) or mode is not None:
        raise ValueError("authoring snapshot omitted precondition or pinned an unexpected mode")
    content = _policy_document(
        resources, _organization(_config(request)), _version(request)
    ).encode("utf-8")
    action: dict[str, object] = {
        "kind": "update",
        "target": _POLICY_TARGET,
        "adapter": "whole-file",
        "scope": "$file",
        "summary": f"render GitHub Workflow policy to {_POLICY_TARGET}",
        "precondition_digest": precondition,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "content_digest": _digest(content),
        "mode": None,
    }
    return {
        "schema_version": "1.0",
        "standard_id": "github-workflow",
        "version": _version(request),
        "actions": [action],
    }
