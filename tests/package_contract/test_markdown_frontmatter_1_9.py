"""Markdown Frontmatter 1.9 adds caller runner selection and the setup-uv 9 pin.

1.9 supersedes 1.8 as the source of the managed self-hosted validation workflow:
the workflow gains an optional `runner-labels` `workflow_call` input allocated
from the caller's context and advances `astral-sh/setup-uv` to 9.0.0 with
`prune-cache: true`, preserving the v8 cache behaviour deliberately rather than
inheriting the action's flipped default. 1.8's bytes are untouched.

1.9 is a retained predecessor, so nothing here claims it is the payload the repository
currently renders `.github/workflows/` from. That claim follows the catalog default and
lives in `test_markdown_frontmatter_reconstruction.py`.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PREDECESSOR = _FAMILY / "versions/1.8"
_SUCCESSOR = _FAMILY / "versions/1.9"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-frontmatter/1.9"
_PREDECESSOR_DIGEST = "sha256:79410e07c98f8f9fcc69e1c31b8b2971134c8d19b855fe81008c296fb6850470"
_WORKFLOW_RESOURCE = "resources/self-host-validate-markdown-frontmatter.yml"
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
# Widened from the 1.8-era form: the reviewed pins this cut adopts carry dotted
# version comments (`# v9.0.0`), which `# v[0-9]+` alone rejects.
_FULL_SHA_ACTION_REFERENCE = re.compile(r"^[^@]+@[0-9a-f]{40}(?: # v[0-9]+(?:\.[0-9]+)*)?$")


def test_markdown_frontmatter_1_9__successor__is_complete_and_preserves_1_8() -> None:
    """A released predecessor stays byte-stable while its successor is complete."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in payload_tree(_PREDECESSOR)
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }

    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o777 == predecessor.stat().st_mode & 0o777
        )


def test_markdown_frontmatter_1_9__workflow_resource__pins_the_reviewed_actions() -> None:
    """The resource ships the pins 1.9 was cut for, declared as a managed artifact.

    Byte-parity with the repository's own `.github/workflows/` copy is deliberately not
    asserted here any more. That copy is package-managed and the reconcile rewrites it
    from whichever payload the catalog marks default, so the parity claim follows the
    default rather than 1.9; `test_frontmatter_root_workflow_is_the_v5_public_endpoint`
    in `test_markdown_frontmatter_reconstruction.py` owns it and derives the version.
    What stays 1.9's own is the reviewed `setup-uv` 9.0.0 pin with `prune-cache: true`
    and the `runner-labels` input — released bytes that may never move.
    """
    workflow = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()

    text = workflow.decode("utf-8")
    references = [
        reference.strip().removeprefix("uses: ")
        for reference in text.splitlines()
        if reference.lstrip().startswith("uses: ")
    ]
    assert references
    assert all(_FULL_SHA_ACTION_REFERENCE.fullmatch(reference) for reference in references)
    assert "uses: astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0" in text
    assert "prune-cache: true" in text
    assert "runner-labels:" in text

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    artifact = next(item for item in manifest.artifacts if item.id == "self-host-workflow")
    assert artifact.target.original == ".github/workflows/validate-markdown-frontmatter.yml"
    assert artifact.source.original == _WORKFLOW_RESOURCE
    assert artifact.policy.value == "managed"
    assert artifact.digest.value == f"sha256:{hashlib.sha256(workflow).hexdigest()}"
    assert [(item.option, item.equals) for item in artifact.when_any] == [
        ("workflow_mode", "self-hosted")
    ]


def test_markdown_frontmatter_1_9__identity_references__name_the_successor() -> None:
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
        assert "1.8" not in text, relative
        assert "1.9" in text, relative

    # The permalinks these two ship are fixed `blob/vN.N.N` references, so they
    # name the release that first carries this payload, not a moving major.
    for relative in (
        "artifacts/agent-summary.md",
        "skills/markdown-frontmatter/SKILL.md",
    ):
        text = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "/v5.14.0/" not in text, relative
        assert "/v5.16.0/" in text, relative


def test_markdown_frontmatter_1_9__family_index__matches_the_payload_digest() -> None:
    """The mutable family entry pins the successor's complete immutable inventory."""
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")

    assert manifest.payload.version.value == "1.9"
    assert manifest.payload.availability.value == "consumer"
    assert {
        migration.from_endpoint.value
        for migration in manifest.migrations
        if migration.to_endpoint.value == "package:1.9"
    } == {"legacy:v4-markdown-frontmatter"}
    assert any(migration.id == "legacy-v4-to-1-9" for migration in manifest.migrations)


def test_markdown_frontmatter_1_9__catalog_role__stays_retained_behind_the_successor() -> None:
    """1.9 keeps an advertised, non-default row once 1.10 takes the default.

    `test_markdown_frontmatter_1_10__catalog_role__selects_the_successor_as_default`
    owns the default assertion from the 5.17.0 activation onward.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-frontmatter"
    }

    assert roles["1.9"] == "retained"
    assert roles["1.8"] == "retained"
    assert roles["1.7"] == "retained"


def test_markdown_frontmatter_1_9__payload_projection__matches_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }
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


def test_markdown_frontmatter_1_9__family_index__keeps_the_retained_version_selectable() -> None:
    """Naming 1.10 as the current authority must not drop 1.9 from the family index.

    Family navigation now points at 1.10 (see `test_markdown_frontmatter_1_10`);
    what 1.9 still owes a consumer holding an exact pin is an advertised,
    digest-bound row.
    """
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert indexed["1.9"].digest == integrity.aggregate_digest
