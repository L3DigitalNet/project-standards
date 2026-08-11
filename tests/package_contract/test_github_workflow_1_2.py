"""Contract for the unadvertised GitHub Workflow 1.2 guidance candidate."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_PREDECESSOR = _FAMILY / "versions/1.1"
_SUCCESSOR = _FAMILY / "versions/1.2"
_PROJECTION = _ROOT / "src/project_standards/payloads/github-workflow/1.2"
_VERSION_1_0_DIGEST = "sha256:65afb66cd3aaf1e0fa9bb896e63b2275290e93aa8fff6d4e0fb5129b9fb99d86"
_PREDECESSOR_DIGEST = "sha256:a6ad7da622a3f7f56f87521be787c7f36761e476029ed2ac009c32db82a5fad6"
_BINARY = "skills/github-workflow/bin/gh-workflow"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/github-workflow/SKILL.md",
        "skills/github-workflow/references/field-vocabulary.md",
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def test_github_workflow_1_2__successor__preserves_predecessors_and_indexes_payload() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777
        )

    successor_manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    successor_integrity = validate_payload_integrity(_SUCCESSOR, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert successor_manifest.payload.version.value == "1.2"
    assert indexed["1.2"].digest == successor_integrity.aggregate_digest
    # Published predecessor rows are immutable selectors, not moving aliases.
    assert indexed["1.1"].digest.value == _PREDECESSOR_DIGEST
    assert indexed["1.0"].digest.value == _VERSION_1_0_DIGEST

    predecessor_schema = json.loads(
        (_PREDECESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    successor_schema = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    predecessor_schema["properties"]["version"]["const"] = "1.2"
    assert successor_schema == predecessor_schema


def test_github_workflow_1_2__label_guidance__routes_categories_and_refuses_state() -> None:
    skill = (_SUCCESSOR / "skills/github-workflow/SKILL.md").read_text(encoding="utf-8")
    vocabulary = (_SUCCESSOR / "skills/github-workflow/references/field-vocabulary.md").read_text(
        encoding="utf-8"
    )

    for namespace in ("`area/*`", "`concern/*`", "`source/*`"):
        assert namespace in skill
        assert namespace in vocabulary
    for namespace in (
        "`priority/*`",
        "`status/*`",
        "`size/*`",
        "`severity/*`",
        "`risk/*`",
        "`agent-ready`",
    ):
        assert namespace in skill
        assert namespace in vocabulary
    assert "optional categorization" in vocabulary
    assert "Refuse" in skill


def test_github_workflow_1_2__field_guidance__gives_all_six_pairwise_counterexamples() -> None:
    vocabulary = (_SUCCESSOR / "skills/github-workflow/references/field-vocabulary.md").read_text(
        encoding="utf-8"
    )
    expected_pairs = (
        "**Priority and Size:**",
        "**Priority and Change risk:**",
        "**Priority and Severity:**",
        "**Size and Change risk:**",
        "**Size and Severity:**",
        "**Change risk and Severity:**",
    )

    for pair in expected_pairs:
        assert pair in vocabulary


def test_github_workflow_1_2__transport_boundary__retires_mcp_first_without_a_path() -> None:
    readme = (_SUCCESSOR / "README.md").read_text(encoding="utf-8")

    assert "MCP-first proposal is retired" in readme
    assert "GitHub REST API only" in readme
    assert "operator's existing `gh` authentication" in readme
    assert "no MCP read or mutation path" in readme
    assert "no `issue_read` body-escaping procedure" in readme
    for unsupported_procedure in ("HTML-escaped", "tag-stripped", "round-trip the body"):
        assert unsupported_procedure not in readme


def test_github_workflow_1_2__binary__is_the_exact_executable_predecessor_artifact() -> None:
    predecessor = _PREDECESSOR / _BINARY
    successor = _SUCCESSOR / _BINARY

    assert successor.read_bytes() == predecessor.read_bytes()
    assert successor.stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777 == 0o755
    (declared,) = [
        artifact
        for artifact in load_payload_manifest(_SUCCESSOR / "payload.toml").artifacts
        if artifact.source.original == _BINARY
    ]
    assert declared.mode == "0755"


def test_github_workflow_1_2__projection_and_catalog__stay_complete_and_unadvertised() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
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

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = [
        (package["version"], package["role"])
        for package in catalog["packages"]
        if package["id"] == "github-workflow"
    ]
    assert roles == [("1.0", "retained"), ("1.1", "retained"), ("1.2", "default")]
    for document in ("README.md", "adopt.md", "agent-summary.md"):
        family_navigation = (_FAMILY / document).read_text(encoding="utf-8")
        assert "versions/1.2/" in family_navigation
        assert "versions/1.1/" not in family_navigation
