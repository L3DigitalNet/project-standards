"""Markdown Frontmatter 1.8 packages the pinned self-hosted workflow successor."""

from __future__ import annotations

import hashlib
import stat
import subprocess
from pathlib import Path

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PREDECESSOR = _FAMILY / "versions/1.7"
_SUCCESSOR = _FAMILY / "versions/1.8"
_WORKFLOW_RESOURCE = "resources/self-host-validate-markdown-frontmatter.yml"
_RELEASED_BASELINE = "v5.13.0"
_CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "artifacts/agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/markdown-frontmatter/SKILL.md",
        _WORKFLOW_RESOURCE,
    }
)


def test_markdown_frontmatter_1_8__successor__is_complete_and_preserves_1_7() -> None:
    """A released predecessor stays byte-stable while its successor is complete."""
    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path.read_bytes()
        for path in _PREDECESSOR.rglob("*")
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }

    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative] == predecessor_files[relative]


def test_markdown_frontmatter_1_8__predecessor__matches_the_released_baseline() -> None:
    """The local 1.7 predecessor remains byte- and mode-identical to v5.13.0."""
    predecessor_prefix = _PREDECESSOR.relative_to(_ROOT).as_posix()
    released_paths = set(
        subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", _RELEASED_BASELINE, "--", predecessor_prefix],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    )
    local_paths = {
        path.relative_to(_ROOT).as_posix() for path in _PREDECESSOR.rglob("*") if path.is_file()
    }
    assert local_paths == released_paths

    for path in _PREDECESSOR.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(_ROOT).as_posix()
        tree_entry = subprocess.run(
            ["git", "ls-tree", _RELEASED_BASELINE, "--", relative],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert tree_entry, relative
        released_mode = tree_entry.split(maxsplit=1)[0]
        local_mode = f"100{stat.S_IMODE(path.stat().st_mode):03o}"
        assert local_mode == released_mode, relative
        released_bytes = subprocess.run(
            ["git", "show", f"{_RELEASED_BASELINE}:{relative}"],
            cwd=_ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert path.read_bytes() == released_bytes, relative


def test_markdown_frontmatter_1_8__workflow_resource__retains_the_reviewed_checkout_pin() -> None:
    """1.8's byte-frozen resource still carries the reviewed checkout SHA pin.

    1.9 supersedes this resource as the root workflow's source (runner-labels
    input, setup-uv v9 bump); 1.8 stays advertised/retained with its own bytes
    unchanged, so this no longer asserts equality with the live root workflow.
    """
    workflow = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()
    text = workflow.decode("utf-8")
    assert f"uses: actions/checkout@{_CHECKOUT_SHA} # v7" in text
    assert "uses: actions/checkout@v7" not in text

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    artifact = next(item for item in manifest.artifacts if item.id == "self-host-workflow")
    assert artifact.target.original == ".github/workflows/validate-markdown-frontmatter.yml"
    assert artifact.source.original == _WORKFLOW_RESOURCE
    assert artifact.policy.value == "managed"
    assert artifact.digest.value == f"sha256:{hashlib.sha256(workflow).hexdigest()}"
    assert [(item.option, item.equals) for item in artifact.when_any] == [
        ("workflow_mode", "self-hosted")
    ]


def test_markdown_frontmatter_1_8__identity_references__name_the_successor() -> None:
    """Versioned manifest, schema, and documentation cannot retain the predecessor ID."""
    identity_files = (
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "artifacts/agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/markdown-frontmatter/SKILL.md",
    )

    for relative in identity_files:
        text = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "1.7" not in text, relative
        assert "1.8" in text, relative

    for relative in (
        "artifacts/agent-summary.md",
        "skills/markdown-frontmatter/SKILL.md",
    ):
        text = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "/v5.12.0/" not in text, relative
        assert "/v5.14.0/" in text, relative


def test_markdown_frontmatter_1_8__family_index__matches_the_payload_digest() -> None:
    """The mutable family entry pins the successor's complete immutable inventory."""
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.8"
    assert manifest.payload.availability.value == "consumer"
    assert any(migration.id == "legacy-v4-to-1-8" for migration in manifest.migrations)
    assert any(migration.to_endpoint.value == "package:1.8" for migration in manifest.migrations)
    assert indexed["1.8"].digest == integrity.aggregate_digest


def test_markdown_frontmatter_1_8__family_navigation__selects_the_successor() -> None:
    """Mutable family documents identify the versioned authority without catalog edits."""
    for relative in ("README.md", "adopt.md", "agent-summary.md"):
        text = (_FAMILY / relative).read_text(encoding="utf-8")
        assert "markdown-frontmatter@1.8" in text
        assert "versions/1.8/" in text
        assert "1.7" not in text
