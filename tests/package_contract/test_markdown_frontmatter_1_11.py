"""Contract for the Markdown Frontmatter 1.11 runner-label advisory.

The successor adds one config-only verify provider. Non-empty labels warn when
consumer ownership or direct self-hosted mode bypasses the managed caller input;
empty labels and a managed caller remain silent. Rendering, document operations,
configuration defaults, and the released 1.10 payload stay unchanged.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest
import yaml

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
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PREDECESSOR = _FAMILY / "versions/1.10"
_SUCCESSOR = _FAMILY / "versions/1.11"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-frontmatter/1.11"
_PREDECESSOR_DIGEST = "sha256:d893620234a47e02dd2252a933829520b4366fb64cc802fc1f7c83a762dce111"
_WORKFLOW_RESOURCE = "resources/self-host-validate-markdown-frontmatter.yml"
_CALLER_JOB_RESOURCE = "workflow-job.yml"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "artifacts/agent-summary.md",
        "payload.toml",
        "providers/frontmatter.py",
        "schemas/provider-input.schema.json",
        "skills/markdown-frontmatter/SKILL.md",
    }
)
_LABELS = ["self-hosted", "linux", "x64", "l3digital-private"]


def _render(root: Path, config: JsonObject) -> bytes:
    manifest = load_payload_manifest(root / "payload.toml")
    payload = InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="render-workflow-job",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={},
        )
    )
    assert result.content is not None
    return result.content


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    return InstalledPayload(
        _SUCCESSOR,
        manifest,
        validate_payload_integrity(_SUCCESSOR, manifest),
    )


def _verify(config: JsonObject) -> tuple[ControlFinding, ...]:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=payload.manifest.payload.version,
            provider_id="verify-runner-labels",
            operation=ProviderOperation.VERIFY,
            effective_config=config,
            snapshots={},
        )
    )
    return result.findings


def _options(root: Path, selected: Mapping[str, object] | None = None) -> JsonObject:
    manifest = load_payload_manifest(root / "payload.toml")
    schema = load_option_schema(root, manifest)
    return schema.resolve_options(selected or {})  # type: ignore[arg-type]


def test_markdown_frontmatter_1_11__successor__preserves_1_10_and_indexes_complete_payload() -> (
    None
):
    """Only advisory code, identity prose, and its provider envelope change."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.11"
    assert indexed["1.11"].digest == integrity.aggregate_digest
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-11"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.11"]

    predecessor_schema = json.loads((_PREDECESSOR / "config.schema.json").read_text())
    successor_schema = json.loads((_SUCCESSOR / "config.schema.json").read_text())
    assert successor_schema == predecessor_schema


def test_markdown_frontmatter_1_11__former_provider_code__is_an_exact_prefix() -> None:
    """The advisory is appended so every former provider implementation stays exact."""
    predecessor = (_PREDECESSOR / "providers/frontmatter.py").read_bytes()
    successor = (_SUCCESSOR / "providers/frontmatter.py").read_bytes()
    assert successor.startswith(predecessor)


def test_markdown_frontmatter_1_11__self_hosted_resource__is_unchanged_from_1_10() -> None:
    """The advisory changes verification, not the direct workflow bytes."""
    successor = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()
    assert successor == (_PREDECESSOR / _WORKFLOW_RESOURCE).read_bytes()

    text = successor.decode("utf-8")
    assert "runner-labels:" in text
    assert "runs-on: ${{ inputs.runner-labels && fromJSON(inputs.runner-labels) ||" in text


def test_markdown_frontmatter_1_11__option_surface__is_unchanged() -> None:
    """No configuration key, type, or default changes in the advisory cut."""
    predecessor_defaults = _options(_PREDECESSOR)
    successor_defaults = _options(_SUCCESSOR)

    assert successor_defaults == predecessor_defaults
    assert _options(_SUCCESSOR, {"runner_labels": _LABELS})["runner_labels"] == _LABELS


def test_markdown_frontmatter_1_11__empty_selection__renders_the_1_10_job_bytes() -> None:
    """The default caller render must still be the static resource, byte for byte."""
    static_bytes = (_PREDECESSOR / _CALLER_JOB_RESOURCE).read_bytes()
    predecessor = _render(_PREDECESSOR, _options(_PREDECESSOR))
    assert predecessor == static_bytes

    assert _render(_SUCCESSOR, _options(_SUCCESSOR)) == static_bytes
    assert _render(_SUCCESSOR, _options(_SUCCESSOR, {"runner_labels": []})) == static_bytes
    assert b"runner-labels" not in static_bytes
    assert b"with:" not in static_bytes


def test_markdown_frontmatter_1_11__selected_labels__compose_into_the_frontmatter_job() -> None:
    """The composed job passes the labels as a JSON string the callee can `fromJSON`."""
    rendered = _render(_SUCCESSOR, _options(_SUCCESSOR, {"runner_labels": _LABELS}))
    job = yaml.safe_load(rendered)["jobs"]["frontmatter"]

    assert isinstance(job["with"]["runner-labels"], str)
    assert json.loads(job["with"]["runner-labels"]) == _LABELS
    # The contribution's existing keys are untouched; only `with:` is appended.
    assert job["name"] == "Frontmatter"
    assert job["uses"].endswith("/validate-markdown-frontmatter.yml@v5")
    assert rendered.startswith((_PREDECESSOR / _CALLER_JOB_RESOURCE).read_bytes())


def test_markdown_frontmatter_1_11__self_hosted_mode__ignores_the_caller_option() -> None:
    """A self-hosted repository receives the same-commit job, labels or not."""
    expected = (_SUCCESSOR / "workflow-job.self-hosted.yml").read_bytes()
    assert _render(_SUCCESSOR, _options(_SUCCESSOR, {"workflow_mode": "self-hosted"})) == expected
    assert (
        _render(
            _SUCCESSOR,
            _options(_SUCCESSOR, {"workflow_mode": "self-hosted", "runner_labels": _LABELS}),
        )
        == expected
    )


def test_markdown_frontmatter_1_11__identity_references__name_the_successor() -> None:
    """Every self-identifying string names 1.11.

    A blanket "predecessor absent" assertion would be wrong here: `README.md` and
    `adopt.md` deliberately narrate what 1.9 did, because that is what a reader
    upgrading from it needs. Only the identity positions are pinned.
    """
    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    assert provider_input["properties"]["version"]["const"] == "1.11"

    identities = {
        "README.md": ("**Package version:** `1.11`.",),
        "adopt.md": (
            "# Adopt Markdown Frontmatter 1.11",
            "project-standards standards enable markdown-frontmatter --version 1.11",
            '\nversion = "1.11"\n',
        ),
        "agent-summary.md": ("Package: `markdown-frontmatter@1.11`.",),
        "artifacts/agent-summary.md": ("Package: `markdown-frontmatter@1.11`.",),
    }
    for relative, expected in identities.items():
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        for fragment in expected:
            assert fragment in document, (relative, fragment)

    # The distributed artifact and skill link into this exact payload directory.
    #
    # The permalinks these two ship are fixed `blob/vN.N.N` references, so they
    # name the release that first carries this payload, not a moving major.
    for relative in ("artifacts/agent-summary.md", "skills/markdown-frontmatter/SKILL.md"):
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "markdown-frontmatter/versions/1.11" in document
        assert "/v5.19.0/" in document


def test_markdown_frontmatter_1_11__payload_projection__matches_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
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


def test_markdown_frontmatter_1_11__catalog_role_and_navigation_are_current() -> None:
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    advertised_versions = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-frontmatter"
    }
    assert advertised_versions["1.10"] == "retained"
    assert advertised_versions["1.11"] == "retained"
    assert advertised_versions["1.12"] == "default"
    assert (
        "| [`markdown-frontmatter`](markdown-frontmatter/README.md) | active | 1.11 | "
        "retained | consumer |"
    ) in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")

    expected_links = {
        _FAMILY / "README.md": "versions/1.12/README.md",
        _FAMILY / "adopt.md": "versions/1.12/adopt.md",
        _FAMILY / "agent-summary.md": "versions/1.12/agent-summary.md",
    }
    for path, expected_link in expected_links.items():
        assert expected_link in path.read_text(encoding="utf-8")


def test_markdown_frontmatter_1_11__manifest__declares_one_config_only_verify_provider() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    verify_providers = [
        provider
        for provider in manifest.providers
        if provider.operation is ProviderOperation.VERIFY
    ]

    assert len(verify_providers) == 1
    provider = verify_providers[0]
    assert provider.id == "verify-runner-labels"
    assert provider.phase.value == "verify"
    assert provider.effect.value == "findings"
    assert provider.entrypoint == "payload:provider-code#run_verify_runner_labels"
    assert provider.resources == []


@pytest.mark.parametrize(
    ("selected", "reason", "remedy"),
    [
        pytest.param(
            {"workflow_ownership": "consumer-owned", "runner_labels": _LABELS},
            "consumer-owned",
            "pass runner-labels",
            id="consumer-owned-caller",
        ),
        pytest.param(
            {"workflow_mode": "self-hosted", "runner_labels": _LABELS},
            "self-hosted",
            "pin its runs-on",
            id="direct-self-hosted",
        ),
    ],
)
def test_markdown_frontmatter_1_11__unreachable_labels__emit_one_warning(
    selected: Mapping[str, object],
    reason: str,
    remedy: str,
) -> None:
    findings = _verify(_options(_SUCCESSOR, selected))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "FM-RUNNER-LABELS-UNREACHABLE"
    assert finding.severity == "warning"
    assert finding.standard_id == "markdown-frontmatter"
    assert finding.version == "1.11"
    assert finding.path == ".github/workflows/validate-standards.yml"
    assert finding.identity == "key:/jobs/frontmatter"
    assert reason in finding.message
    assert remedy in finding.hint


@pytest.mark.parametrize(
    "selected",
    [
        pytest.param({}, id="managed-empty"),
        pytest.param(
            {"workflow_ownership": "consumer-owned", "runner_labels": []},
            id="consumer-owned-empty",
        ),
        pytest.param(
            {"workflow_mode": "self-hosted", "runner_labels": []},
            id="self-hosted-empty",
        ),
        pytest.param({"runner_labels": _LABELS}, id="managed-caller-reachable"),
    ],
)
def test_markdown_frontmatter_1_11__reachable_or_empty_labels__stay_silent(
    selected: Mapping[str, object],
) -> None:
    assert _verify(_options(_SUCCESSOR, selected)) == ()
