"""Contract for the Markdown Frontmatter 1.10 caller-runner-selection successor.

1.9 added `runner-labels` to the SELF-HOSTED workflow resource. 1.10 makes the same
selection reachable from `caller` mode (issue #132) through the additive
`runner_labels` option, composed into the `jobs.frontmatter` fragment that this
package contributes to the shared `validate-standards.yml`.

That fragment was a static resource through 1.9. 1.10 makes the caller branch
dynamic, which is exactly why the byte-identity row below is load-bearing: with an
empty selection — the default — `run_render_workflow` must still return the
unmodified `workflow-job.yml` bytes, or reconciliation would rewrite the composed
job for every consumer that did not select a runner.

Catalog role and root-workflow parity are deliberately absent here; both are
release-prep contracts that batch with the rest of the release.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import yaml

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
_PREDECESSOR = _FAMILY / "versions/1.9"
_SUCCESSOR = _FAMILY / "versions/1.10"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-frontmatter/1.10"
_PREDECESSOR_DIGEST = "sha256:5f08a86214605fb25db4bc48f78ccb68bae52a707506e0adf28117d3ae1d76a5"
_WORKFLOW_RESOURCE = "resources/self-host-validate-markdown-frontmatter.yml"
_CALLER_JOB_RESOURCE = "workflow-job.yml"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "artifacts/agent-summary.md",
        "config.schema.json",
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


def _options(root: Path, selected: Mapping[str, object] | None = None) -> JsonObject:
    manifest = load_payload_manifest(root / "payload.toml")
    schema = load_option_schema(root, manifest)
    return schema.resolve_options(selected or {})  # type: ignore[arg-type]


def test_markdown_frontmatter_1_10__successor__preserves_1_9_and_indexes_complete_payload() -> None:
    """Only the option surface, provider, identity prose, and skill links change."""
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

    assert manifest.payload.version.value == "1.10"
    assert indexed["1.10"].digest == integrity.aggregate_digest
    # An additive option with an empty default moves nothing between artifact
    # targets, so 1.10 declares no package-to-package edge — only the legacy route.
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-10"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.10"]


def test_markdown_frontmatter_1_10__self_hosted_resource__is_unchanged_from_1_9() -> None:
    """1.10 touches only the caller path; the 1.9 workflow bytes carry forward."""
    successor = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()
    assert successor == (_PREDECESSOR / _WORKFLOW_RESOURCE).read_bytes()

    text = successor.decode("utf-8")
    assert "runner-labels:" in text
    assert "runs-on: ${{ inputs.runner-labels && fromJSON(inputs.runner-labels) ||" in text


def test_markdown_frontmatter_1_10__option_surface__adds_only_a_closed_runner_selection() -> None:
    """`runner_labels` is typed, closed, and defaults to the empty selection."""
    predecessor_defaults = _options(_PREDECESSOR)
    successor_defaults = _options(_SUCCESSOR)

    assert successor_defaults == {**predecessor_defaults, "runner_labels": []}
    assert _options(_SUCCESSOR, {"runner_labels": _LABELS})["runner_labels"] == _LABELS


def test_markdown_frontmatter_1_10__empty_selection__renders_the_1_9_job_bytes() -> None:
    """The default caller render must still be the static resource, byte for byte."""
    static_bytes = (_PREDECESSOR / _CALLER_JOB_RESOURCE).read_bytes()
    predecessor = _render(_PREDECESSOR, _options(_PREDECESSOR))
    assert predecessor == static_bytes

    assert _render(_SUCCESSOR, _options(_SUCCESSOR)) == static_bytes
    assert _render(_SUCCESSOR, _options(_SUCCESSOR, {"runner_labels": []})) == static_bytes
    assert b"runner-labels" not in static_bytes
    assert b"with:" not in static_bytes


def test_markdown_frontmatter_1_10__selected_labels__compose_into_the_frontmatter_job() -> None:
    """The composed job passes the labels as a JSON string the callee can `fromJSON`."""
    rendered = _render(_SUCCESSOR, _options(_SUCCESSOR, {"runner_labels": _LABELS}))
    job = yaml.safe_load(rendered)["jobs"]["frontmatter"]

    assert isinstance(job["with"]["runner-labels"], str)
    assert json.loads(job["with"]["runner-labels"]) == _LABELS
    # The contribution's existing keys are untouched; only `with:` is appended.
    assert job["name"] == "Frontmatter"
    assert job["uses"].endswith("/validate-markdown-frontmatter.yml@v5")
    assert rendered.startswith((_PREDECESSOR / _CALLER_JOB_RESOURCE).read_bytes())


def test_markdown_frontmatter_1_10__self_hosted_mode__ignores_the_caller_option() -> None:
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


def test_markdown_frontmatter_1_10__identity_references__name_the_successor() -> None:
    """Every self-identifying string names 1.10.

    A blanket "predecessor absent" assertion would be wrong here: `README.md` and
    `adopt.md` deliberately narrate what 1.9 did, because that is what a reader
    upgrading from it needs. Only the identity positions are pinned.
    """
    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    assert provider_input["properties"]["version"]["const"] == "1.10"

    identities = {
        "README.md": ("**Package version:** `1.10`.",),
        "adopt.md": (
            "# Adopt Markdown Frontmatter 1.10",
            "project-standards standards enable markdown-frontmatter --version 1.10",
            '\nversion = "1.10"\n',
        ),
        "agent-summary.md": ("Package: `markdown-frontmatter@1.10`.",),
        "artifacts/agent-summary.md": ("Package: `markdown-frontmatter@1.10`.",),
    }
    for relative, expected in identities.items():
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        for fragment in expected:
            assert fragment in document, (relative, fragment)

    # The distributed artifact and skill link into this exact payload directory.
    for relative in ("artifacts/agent-summary.md", "skills/markdown-frontmatter/SKILL.md"):
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "markdown-frontmatter/versions/1.9" not in document
        assert "markdown-frontmatter/versions/1.10" in document


def test_markdown_frontmatter_1_10__payload_projection__matches_successor() -> None:
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
