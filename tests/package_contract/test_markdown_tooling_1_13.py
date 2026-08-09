"""Markdown Tooling 1.13 bounds the documented command scope and repins its workflows.

1.13 renders the local verification recipe from the same declared corpus the CI
caller selects (issues #88, #114, #119) and advances the self-hosted workflows to
`runner-labels`, setup-node 7.0.0, and the enforced prettier 3.9.6 pin. The two
configuration resources and the config schema stay byte-identical to 1.12, so the
allow-list below is the whole behavioural surface of the cut.

The root workflow byte-parity rows below are the release-prep contract: they turn
green only once the producer-mode reconcile re-renders `.github/workflows/` from
this payload. Before that they legitimately fail, because CP-MODIFIED-MANAGED
forbids advancing an installed copy ahead of its package.
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

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_PREDECESSOR = _FAMILY / "versions/1.12"
_SUCCESSOR = _FAMILY / "versions/1.13"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-tooling/1.13"
_PREDECESSOR_DIGEST = "sha256:105d742c188f78cd908cd715a396722912d031114ea1e5e6445d1dc879a1e7b8"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "providers/markdown_tooling.py",
        "resources/self-host-format.yml",
        "resources/self-host-lint-markdown.yml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_WORKFLOWS = {
    "resources/self-host-lint-markdown.yml": _ROOT / ".github/workflows/lint-markdown.yml",
    "resources/self-host-format.yml": _ROOT / ".github/workflows/format.yml",
}
# Widened from the 1.12 form: the reviewed pins this cut adopts carry dotted
# version comments (`# v7.0.0`, `# v9.0.0`), which `# v[0-9]+` alone rejects.
_FULL_SHA_ACTION_REFERENCE = re.compile(r"^[^@]+@[0-9a-f]{40}(?: # v[0-9]+(?:\.[0-9]+)*)?$")


def _sha256(path: Path) -> str:
    """Return the package-contract digest for `path`'s raw bytes."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_markdown_tooling_1_13__root_workflows__come_from_pinned_successor_resources() -> None:
    """The package source must exactly match its managed root workflow outputs."""
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    resources = {resource.path.normalized.as_posix(): resource for resource in manifest.resources}

    for resource_path, root_workflow in _WORKFLOWS.items():
        source = _SUCCESSOR / resource_path
        assert source.read_bytes() == root_workflow.read_bytes()
        assert resources[resource_path].digest.value == _sha256(source)
        references = [
            reference.strip().removeprefix("uses: ")
            for reference in source.read_text(encoding="utf-8").splitlines()
            if reference.lstrip().startswith("uses: ")
        ]
        assert references
        assert all(_FULL_SHA_ACTION_REFERENCE.fullmatch(reference) for reference in references)


def test_markdown_tooling_1_13__self_hosted_workflows__accept_caller_runner_labels() -> None:
    """Both self-hosted workflows expose the optional runner selection input."""
    for resource_path in _WORKFLOWS:
        text = (_SUCCESSOR / resource_path).read_text(encoding="utf-8")
        assert "runner-labels:" in text, resource_path


def test_markdown_tooling_1_13__successor__preserves_1_12_and_indexes_complete_payload() -> None:
    """Only the bounded-scope prose, provider, workflow, and schema bytes change."""
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
            successor_files[relative].stat().st_mode & 0o777 == predecessor.stat().st_mode & 0o777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.13"
    assert indexed["1.13"].digest == integrity.aggregate_digest
    assert {
        migration.from_endpoint.value
        for migration in manifest.migrations
        if migration.to_endpoint.value == "package:1.13"
    } == {
        "package:1.7",
        "package:1.8",
        "package:1.9",
        "package:1.10",
        "package:1.11",
        "package:1.12",
        "legacy:v4-markdown-tooling",
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.13"
        # The bounded-command recipe (issue #88) is rendered into the managed
        # instruction block, so every inbound edge must relock both containers —
        # including 1.12's, whose workflow callers are otherwise unchanged.
        assert {
            "contribution:agents-instructions",
            "contribution:claude-instructions",
        } <= set(migration.affected)


def test_markdown_tooling_1_13__catalog_role__stays_retained_behind_the_successor() -> None:
    """1.13 keeps an advertised, non-default row once 1.14 takes the default.

    `test_markdown_tooling_1_14__catalog_role__selects_the_successor_as_default`
    owns the default assertion from the 5.17.0 activation onward. What 1.13 owes
    a consumer holding an exact pin is that promoting its successor neither
    removes its row nor changes its digest.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-tooling"
    }

    assert roles["1.13"] == "retained"
    assert roles["1.12"] == "retained"
    assert roles["1.11"] == "retained"


def test_markdown_tooling_1_13__payload_projection__matches_successor() -> None:
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


def test_markdown_tooling_1_13__family_index__keeps_the_retained_version_selectable() -> None:
    """Naming 1.14 as the current authority must not drop 1.13 from the family index.

    Family navigation now points at 1.14 (see `test_markdown_tooling_1_14`); what
    1.13 still owes a consumer holding an exact pin is an advertised,
    digest-bound row.
    """
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert indexed["1.13"].digest == integrity.aggregate_digest
