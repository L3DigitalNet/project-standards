from __future__ import annotations

import json
import shutil
from pathlib import Path

from project_standards.package_contract import validate_package_repository
from project_standards.package_contract.projection import (
    plan_payload_projection,
    sync_payload_projection,
)
from project_standards.package_contract.repository import build_package_repository

_ROOT = Path(__file__).resolve().parents[2]

_PACKAGES = {
    "adr": (
        "Architecture Decision Record (ADR) Standard",
        "MADR-based architecture decision records with project-standard frontmatter and optional section validation.",
        "active",
        "1.1",
        "default",
        "sha256:82e9e3ae5d50a641b4b47366ef5d66fd85b13555ffda0d9ac1c99aadd1c6c719",
    ),
    "agent-handoff": (
        "Agent Handoff Standard",
        "Repository-local, lifetime-routed project knowledge and bounded agent session continuity.",
        "active",
        "1.1",
        "default",
        "sha256:e5e300e761c3b95bb36a95d0e001c2fa428c21843e15cdbf66202327fdb6ded1",
    ),
    "cli-documentation": (
        "CLI Documentation Standard",
        "Profile-based user-facing CLI help, usage-reference, man-page, and drift-check documentation.",
        "active",
        "1.1",
        "default",
        "sha256:dee2af37fbc2fed53b55a35209c55e4babd3f1ff2cedcef64da04222da3786d6",
    ),
    "markdown-frontmatter": (
        "Markdown Frontmatter Standard",
        "Canonical metadata, ID, and reference validation for managed Markdown documents.",
        "active",
        "1.2",
        "default",
        "sha256:d93fa30ea330f0a5b6b094c120a89887f40e78605a8505ddeadc0288ff83afbd",
    ),
    "markdown-tooling": (
        "Markdown Tooling Standard",
        "Prettier, markdownlint, EditorConfig, and CI tooling for Markdown and adjacent structured text.",
        "active",
        "1.2",
        "default",
        "sha256:3b64ef577a2ab580c48411b67064fb15b9d520dc25fd228fec58e571ac85b490",
    ),
    "project-spec": (
        "Project Specification Standard",
        "Tiered, stable-ID, CLI-validated project specification format and tooling.",
        "active",
        "1.1",
        "default",
        "sha256:0b1ff8db74ffc18ead98ec3e38e8c5c4b7684fe8e68d62c1ea988a830e0db9c0",
    ),
    "python-coding": (
        "Python Coding Standard",
        "Reference guidance for Python code shape, boundaries, typing, tests, and agent behavior.",
        "draft",
        "0.5",
        "reference-only",
        "sha256:d427ddb6ad6f04f010c2ef897d7668c577bda7f1c0d2b50c943dd56fa98634bc",
    ),
    "python-tooling": (
        "Python Tooling SSOT Standard",
        "uv, Ruff, BasedPyright, pytest/coverage, pip-audit, CI, and agent-instruction tooling for Python projects.",
        "active",
        "1.1",
        "default",
        "sha256:1aec6e56e107bfaeb6b82e0ca0d8da42ba36ff092314a26c26c6bb465b7db081",
    ),
    "standard-bundle-authoring": (
        "Standard Bundle Authoring Standard",
        "The contract every standard bundle in this repository must declare.",
        "active",
        "2.0",
        "internal",
        "sha256:5f60155d4678d46d85793e18907d5d423965ef1dffed923e9ebef1a84f12519e",
    ),
}


def _family_source(standard_id: str) -> str:
    name, summary, status, version, _role, digest = _PACKAGES[standard_id]
    return (
        'schema_version = "2.0"\n\n'
        "[standard]\n"
        f"id = {json.dumps(standard_id)}\n"
        f"name = {json.dumps(name)}\n"
        f"summary = {json.dumps(summary)}\n"
        f"status = {json.dumps(status)}\n\n"
        "[[versions]]\n"
        f"version = {json.dumps(version)}\n"
        f"payload = {json.dumps(f'versions/{version}/payload.toml')}\n"
        f"digest = {json.dumps(digest)}\n"
    )


def _catalog_source() -> str:
    lines = ['schema_version = "1.0"', "catalog_major = 5", ""]
    for standard_id, (_name, _summary, _status, version, role, digest) in sorted(_PACKAGES.items()):
        lines.extend(
            [
                "[[packages]]",
                f"id = {json.dumps(standard_id)}",
                f"version = {json.dumps(version)}",
                f"digest = {json.dumps(digest)}",
                f"role = {json.dumps(role)}",
                "",
            ]
        )
    return "\n".join(lines)


def test_isolated_nine_family_repository_validates_before_root_activation(
    tmp_path: Path,
) -> None:
    isolated = tmp_path / "repository"
    for standard_id, (_name, _summary, _status, version, _role, _digest) in _PACKAGES.items():
        source = _ROOT / "standards" / standard_id
        target = isolated / "standards" / standard_id
        target.mkdir(parents=True)
        shutil.copyfile(source / "README.md", target / "README.md")
        shutil.copytree(source / "versions" / version, target / "versions" / version)
        (target / "standard.toml").write_text(_family_source(standard_id), encoding="utf-8")
    catalog = isolated / "catalogs/5.toml"
    catalog.parent.mkdir()
    catalog.write_text(_catalog_source(), encoding="utf-8")

    repository = build_package_repository(isolated, catalog_major=5)

    assert repository.findings == ()
    assert validate_package_repository(repository) == ()
    assert len(repository.families) == len(_PACKAGES)
    assert len(repository.payloads) == len(_PACKAGES)
    assert repository.catalog is not None


def test_repository_root_activates_exact_catalog_and_relative_projections() -> None:
    repository = build_package_repository(_ROOT, catalog_major=5)

    assert repository.findings == ()
    assert repository.catalog is not None
    assert {
        (entry.id, entry.version.value, entry.role.value, entry.digest.value)
        for entry in repository.catalog.packages
    } == {
        (standard_id, values[3], values[4], values[5]) for standard_id, values in _PACKAGES.items()
    }
    assert not (_ROOT / ".standards").exists()
    assert sync_payload_projection(_ROOT, check=True) == ()
    for link in plan_payload_projection(_ROOT).links:
        assert link.destination.is_symlink()
        assert not link.destination.readlink().is_absolute()
        assert link.destination.resolve(strict=True).read_bytes() == link.source.read_bytes()
