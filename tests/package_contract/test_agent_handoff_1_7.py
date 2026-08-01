"""agent-handoff 1.7 registration and the issue #94 credential-checker correction.

1.6's `AH-SECRET-LITERAL` finding is emitted once per document with `line = None`,
so an operator is told a selected handoff document "contains credential-shaped
literal material" and has to hunt for it by eye. The reporter of #94 concluded
their `TOKEN=$(...)` example was the trigger; it was not (`$` is an allowed
reference prefix), which is exactly the failure mode an unlocatable finding
produces. The reproducible false positive is the OTHER command-substitution
form: a backtick right-hand side stores nothing either, but 1.6 flags it, and the
same normalization gap flags a credential reference an author wrapped in a
Markdown code span even though the engine's `_is_reference` strips backticks
before deciding.

1.7 therefore (a) treats `$( ... )` and REFERENCE-NAMING backtick command
substitution as runtime acquisition, (b) strips a wrapping code span before
applying the reference policy, and (c) reports one finding per offending line
carrying that line number, with a message that says which rule matched.

A backtick span is only an acquisition when one of its tokens passes the
reference policy, because a genuine retrieval command names its source
(`bao kv get ... secret/apps/x`, `credential-helper read env:CRED`). Requiring
merely that the span contain whitespace would exempt
``TOKEN=`printf '%s' 'literal'` `` -- a literal written as a command argument,
which is laundering, not acquisition.
"""

from __future__ import annotations

import base64
import hashlib
import json
import tomllib
from pathlib import Path
from typing import cast

import pytest

from project_standards.agent_handoff.policy import check_secret_references, load_policy
from project_standards.control_plane.diagnostics import ControlFinding
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.6"
_SUCCESSOR = _FAMILY / "versions/1.7"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.7"
_PREDECESSOR_DIGEST = "sha256:97041fb9a47c28cf0e2dd38c2de32be827af4b079de3943d6b74675bf52d81f8"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "payload.toml",
        "providers/agent_handoff.py",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_CREDENTIALS = "docs/handoff/credentials.md"


def _successor() -> InstalledPayload:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    return InstalledPayload(_SUCCESSOR, manifest, validate_payload_integrity(_SUCCESSOR, manifest))


def _credential_findings(body: str, repo: Path) -> list[ControlFinding]:
    """Return the AH-SECRET-LITERAL findings for one fenced credentials example.

    The document is otherwise conformant, and only this path is snapshotted, so
    every returned finding is attributable to a line of `body`.
    """
    payload = _successor()
    schema = load_option_schema(payload.root, payload.manifest)
    text = (
        "# Credentials\n\n"
        "## Quick Reference\n\n"
        "- Store references only.\n\n"
        "## 1. Retrieval\n\n"
        "```bash\n"
        f"{body}\n"
        "```\n"
    )
    content = text.encode()
    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="agent-handoff",
            version=payload.manifest.payload.version,
            provider_id="validate",
            operation=ProviderOperation.VALIDATE,
            effective_config=schema.resolve_options(cast("JsonObject", {})),
            snapshots={
                _CREDENTIALS: {
                    "kind": "regular",
                    "content_digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
                    "content_base64": base64.b64encode(content).decode("ascii"),
                    "mode": None,
                }
            },
        )
    )
    return [finding for finding in result.findings if finding.code == "AH-SECRET-LITERAL"]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "TOKEN=$(grep '<credential-name>' /path/to/credential-reference)",
            id="dollar-paren-substitution",
        ),
        pytest.param(
            'TOKEN="$(credential-helper read env:CREDENTIAL_NAME)"',
            id="quoted-dollar-paren-substitution",
        ),
        pytest.param(
            "TOKEN=`credential-helper read env:CREDENTIAL_NAME`",
            id="backtick-substitution",
        ),
        pytest.param(
            "token: `bao kv get -field=value secret/apps/example`",
            id="backtick-substitution-colon-form",
        ),
        pytest.param(
            "token: `secret/apps/example`",
            id="reference-inside-a-markdown-code-span",
        ),
        pytest.param("token: env:EXAMPLE_TOKEN", id="bare-reference"),
    ],
)
def test_agent_handoff_1_7__runtime_acquisition__is_not_literal_material(
    tmp_path: Path, body: str
) -> None:
    """A right-hand side that acquires or names a credential stores none (issue #94)."""
    assert _credential_findings(body, tmp_path) == []


@pytest.mark.parametrize(
    ("body", "message"),
    [
        pytest.param(
            'token = "literal-secret-value"',
            "line assigns credential-shaped literal material to a blocked label",
            id="blocked-assignment",
        ),
        pytest.param(
            "token: `literal-secret-value`",
            "line assigns credential-shaped literal material to a blocked label",
            id="blocked-assignment-inside-a-code-span",
        ),
        pytest.param(
            "-----BEGIN PRIVATE KEY-----",
            "line contains a private-key header",
            id="private-key-header",
        ),
        pytest.param(
            "aws_id AKIAIOSFODNN7EXAMPLE trailing",
            "line contains an access-key pattern",
            id="access-key-pattern",
        ),
        pytest.param(
            "TOKEN=`printf '%s' 'synth-live-7Jm9Qv2Nk4Rx8Pz6'`",
            "line assigns credential-shaped literal material to a blocked label",
            id="backtick-printf-laundering",
        ),
        pytest.param(
            "password: `echo correct-horse-battery-staple`",
            "line assigns credential-shaped literal material to a blocked label",
            id="backtick-echo-laundering",
        ),
    ],
)
def test_agent_handoff_1_7__literal_material__names_its_line(
    tmp_path: Path, body: str, message: str
) -> None:
    """Every retained detection reports the offending line, not just the document."""
    findings = _credential_findings(body, tmp_path)

    assert [(finding.line, finding.message) for finding in findings] == [(10, message)]
    assert all(finding.locus == "credentials" for finding in findings)
    assert all("literal-secret-value" not in finding.message for finding in findings)


def test_agent_handoff_1_7__multiple_offending_lines__are_reported_separately(
    tmp_path: Path,
) -> None:
    """One finding per line: 1.6 collapsed a whole document into a single locus."""
    body = (
        'token = "first-literal"\n'
        "TOKEN=$(credential-helper read env:SAFE)\n"
        'password = "second-literal"'
    )

    findings = _credential_findings(body, tmp_path)

    assert [finding.line for finding in findings] == [10, 12]


_PARITY_CASES = (
    "TOKEN=$(grep '<credential-name>' /path/to/credential-reference)",
    'TOKEN="$(credential-helper read env:CREDENTIAL_NAME)"',
    "TOKEN=`credential-helper read env:CREDENTIAL_NAME`",
    "token: `bao kv get -field=value secret/apps/example`",
    "token: `secret/apps/example`",
    "token: `abc123literal`",
    "TOKEN=`printf '%s' 'synth-live-7Jm9Qv2Nk4Rx8Pz6'`",
    "password: `echo correct-horse-battery-staple`",
    'token = "literal-secret-value"',
    "token: env:EXAMPLE_TOKEN",
    "-----BEGIN PRIVATE KEY-----",
    "aws_id AKIAIOSFODNN7EXAMPLE trailing",
)


@pytest.mark.parametrize("line", _PARITY_CASES, ids=lambda value: value[:34])
def test_agent_handoff_1_7__credential_exemption__matches_the_engine(
    tmp_path: Path, line: str
) -> None:
    """Engine and provider must agree on WHICH lines are literal material (issue #94).

    The engine's `check_secret_references` is the version-independent fallback and
    carries a duplicate of the payload's runtime-acquisition rule, because a
    payload cannot be imported from the engine. Duplication without a parity proof
    is how the two drifted in the first place, so every case the payload tests
    pin is replayed against both implementations here. Only the flagged/clean
    verdict is compared: the two deliberately differ in message prose and in how
    many findings a document yields.
    """
    policy = load_policy(_SUCCESSOR / "resources/policy.toml")

    engine_flagged = bool(check_secret_references(_CREDENTIALS, f"{line}\n", policy))
    provider_flagged = bool(_credential_findings(line, tmp_path))

    assert engine_flagged == provider_flagged


def test_agent_handoff_1_7__decoy_reference_tokens__are_an_accepted_residual(
    tmp_path: Path,
) -> None:
    """A decoy reference token defeats the runtime-acquisition rule — accepted.

    ``TOKEN=`printf '%s%.0s' 'literal' env:DECOY` `` is exempt in both
    implementations because one token passes the reference policy while the
    command emits only the embedded literal (Codex round-2 review, 2026-07-31).
    Accepted rather than fixed: the checker guards against accidental credential
    storage, a deliberately constructed decoy sits outside that threat model, and
    the identical decoy already passes through the long-released ``$( ... )``
    exemption, so the backtick surface adds no marginal exposure. Every static
    rule short of rejecting all command forms is decoyable, and rejecting them
    all resurrects the issue #94 false positives. This test documents the
    residual so it cannot silently become load-bearing; it is not a contract
    that the form must stay exempt.
    """
    line = "TOKEN=`printf '%s%.0s' 'synth-live-7Jm9Qv2Nk4Rx8Pz6' env:DECOY`"
    policy = load_policy(_SUCCESSOR / "resources/policy.toml")

    assert not check_secret_references(_CREDENTIALS, f"{line}\n", policy)
    assert not _credential_findings(line, tmp_path)


def test_agent_handoff_1_7__provider_schemas__bind_the_successor_identity() -> None:
    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )

    assert provider_input["properties"]["version"]["const"] == "1.7"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.7"


def test_agent_handoff_1_7__activated_successor__is_complete_default_and_immutable() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()

    successor_manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    successor_integrity = validate_payload_integrity(_SUCCESSOR, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert successor_manifest.payload.version.value == "1.7"
    assert successor_manifest.payload.availability.value == "consumer"
    assert indexed["1.7"].digest == successor_integrity.aggregate_digest
    assert any(
        migration.to_endpoint.value == "package:1.7" for migration in successor_manifest.migrations
    )

    # Catalog 5 retains 1.7 after 1.8 becomes the default. The dogfood lock tracks
    # the new default only after release-prep reconciliation, so that assertion
    # stays in tests/agent_handoff/test_packaging.py rather than here.
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "agent-handoff"
    }
    assert roles[successor_manifest.payload.version.value] == "retained"
    assert roles[predecessor_manifest.payload.version.value] == "retained"


def test_agent_handoff_1_7__provider_input_family__is_declared_for_composite_dispatch() -> None:
    """TC-T14-004's precondition: the payload keeps the seam-served family identity.

    `provider_dispatch_input` keys on the standard id plus the operation, so a new
    provider-bearing payload is seam-served only while it stays in the
    `agent-handoff` family and keeps declaring validate/verify/drift-check. A
    renamed standard or a dropped operation would silently fall back to generic
    empty input, which is the defect that canary exists to catch.
    """
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    declared = {provider.operation.value for provider in manifest.providers}

    assert manifest.payload.standard == "agent-handoff"
    assert {"validate", "verify", "drift-check"} <= declared


def test_agent_handoff_1_7__payload_projection__matches_complete_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
