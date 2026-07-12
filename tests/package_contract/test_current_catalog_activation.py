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
        "sha256:e764da40443b48508c593798a9b5b04ae418cb24f8ac31afa1c5706c3eac6bb7",
    ),
    "agent-handoff": (
        "Agent Handoff Standard",
        "Repository-local, lifetime-routed project knowledge and bounded agent session continuity.",
        "active",
        "1.1",
        "default",
        "sha256:38f523980e18ce9fbfbae23a9a797a6aec863e368269e2fb59365ce82282c891",
    ),
    "cli-documentation": (
        "CLI Documentation Standard",
        "Profile-based user-facing CLI help, usage-reference, man-page, and drift-check documentation.",
        "active",
        "1.1",
        "default",
        "sha256:eab56ef2c1135a31f5525d951c137937b0a748f8a55b3d17222828189848c457",
    ),
    "markdown-frontmatter": (
        "Markdown Frontmatter Standard",
        "Canonical metadata, ID, and reference validation for managed Markdown documents.",
        "active",
        "1.2",
        "default",
        "sha256:ba2bce2d7344db187444c2eaff9f276e5c878afa81bdb97c63133a00d2cd353d",
    ),
    "markdown-tooling": (
        "Markdown Tooling Standard",
        "Prettier, markdownlint, EditorConfig, and CI tooling for Markdown and adjacent structured text.",
        "active",
        "1.2",
        "default",
        "sha256:07649cbf7140c9a430b66f315dba2855fba33696eb8edba274a15a7b1cfdf558",
    ),
    "project-spec": (
        "Project Specification Standard",
        "Tiered, stable-ID, CLI-validated project specification format and tooling.",
        "active",
        "1.1",
        "default",
        "sha256:0999323cc5782b5d312348b70d6fbe4c809969f2510c888acafd22a5cd815c76",
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
        "sha256:7e473510b8acbacc434be3edf73b8b9c14a3a47042020375286689311d767dfa",
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
