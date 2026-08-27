"""Markdown Tooling 1.12 pins the managed self-hosted workflow sources.

The repository workflows are package-managed outputs.  A root-only action-pin
change is therefore drift until an immutable successor contains the same bytes.
These tests keep the 1.11 release immutable while proving the new payload is the
source of truth for both root workflows.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_PREDECESSOR = _FAMILY / "versions/1.11"
_SUCCESSOR = _FAMILY / "versions/1.12"
_PREDECESSOR_DIGEST = "sha256:3bf59aa23a857174bfcaf604de07318b61ec177b9fab1f016ad4c6516e4ff882"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "resources/self-host-format.yml",
        "resources/self-host-lint-markdown.yml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_WORKFLOWS = (
    "resources/self-host-lint-markdown.yml",
    "resources/self-host-format.yml",
)
_FULL_SHA_ACTION_REFERENCE = re.compile(r"^[^@]+@[0-9a-f]{40}(?: # v[0-9]+)?$")


def _sha256(path: Path) -> str:
    """Return the package-contract digest for `path`'s raw bytes."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_markdown_tooling_1_12__workflow_resources__stay_digest_bound_and_sha_pinned() -> None:
    """1.12's byte-frozen workflow resources stay integrity-bound and fully SHA-pinned.

    1.13 supersedes these resources as the root workflows' source (runner-labels
    inputs, setup-node 7.0.0, the enforced prettier 3.9.6 pin); 1.12 stays
    advertised/retained with its own bytes unchanged, so this no longer asserts
    equality with the live root workflows.
    """
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    resources = {resource.path.normalized.as_posix(): resource for resource in manifest.resources}

    for resource_path in _WORKFLOWS:
        source = _SUCCESSOR / resource_path
        assert resources[resource_path].digest.value == _sha256(source)
        references = [
            reference.strip().removeprefix("uses: ")
            for reference in source.read_text(encoding="utf-8").splitlines()
            if reference.lstrip().startswith("uses: ")
        ]
        assert references
        assert all(_FULL_SHA_ACTION_REFERENCE.fullmatch(reference) for reference in references)


def test_markdown_tooling_1_12__successor__preserves_1_11_and_indexes_complete_payload() -> None:
    """Only the new workflow sources, migration metadata, and versioned prose change."""
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

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.12"
    assert indexed["1.12"].digest == integrity.aggregate_digest
    assert {
        migration.from_endpoint.value
        for migration in manifest.migrations
        if migration.to_endpoint.value == "package:1.12"
    } == {
        "package:1.7",
        "package:1.8",
        "package:1.9",
        "package:1.10",
        "package:1.11",
        "legacy:v4-markdown-tooling",
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.12"
        assert {
            "contribution:format-caller",
            "contribution:lint-caller",
        } <= set(migration.affected)


def test_markdown_tooling_1_12__family_index__keeps_the_retained_version_selectable() -> None:
    """Naming 1.13 as the current authority must not drop 1.12 from the family index.

    Family navigation now points at 1.13 (see `test_markdown_tooling_1_13`); what
    1.12 still owes a consumer holding an exact pin is an advertised,
    digest-bound row.
    """
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert indexed["1.12"].digest == integrity.aggregate_digest
