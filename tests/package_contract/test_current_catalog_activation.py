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
        "1.2",
        "default",
        "sha256:197d9c6877781abf1a9f0a3d3f37092413600ebaff604371ae10c7405925cf5b",
    ),
    "cli-documentation": (
        "CLI Documentation Standard",
        "Profile-based user-facing CLI help, usage-reference, man-page, and drift-check documentation.",
        "active",
        "1.1",
        "default",
        "sha256:a6aa0b4a9e0f2247a0795dac3073a55e72d9047581493e1326eeb42d43442445",
    ),
    "markdown-frontmatter": (
        "Markdown Frontmatter Standard",
        "Canonical metadata, ID, and reference validation for managed Markdown documents.",
        "active",
        "1.2",
        "default",
        "sha256:e1e2ac7d41fb2b7be8772717292d5d8afadcbe878a70d562e82d7f4c1bdd606c",
    ),
    "markdown-tooling": (
        "Markdown Tooling Standard",
        "Prettier, markdownlint, EditorConfig, and CI tooling for Markdown and adjacent structured text.",
        "active",
        "1.2",
        "default",
        "sha256:0d4f89403c4b4c4a2d1dc9c579deddf717f5e01d1c424cac4a103ecb03be12ae",
    ),
    "project-spec": (
        "Project Specification Standard",
        "Tiered, stable-ID, CLI-validated project specification format and tooling.",
        "active",
        "1.1",
        "default",
        "sha256:ed1445342d72836707dd455fd5771f28b71b53acbb1499e4f9250e33f548d36e",
    ),
    "python-coding": (
        "Python Coding Standard",
        "Reference guidance for Python code shape, boundaries, typing, tests, and agent behavior.",
        "draft",
        "0.5",
        "reference-only",
        "sha256:c027af45f85e84717e7ce9909adcd71363745e688538bd88a303dd813a351d80",
    ),
    "python-tooling": (
        "Python Tooling SSOT Standard",
        "uv, Ruff, BasedPyright, pytest/coverage, pip-audit, CI, and agent-instruction tooling for Python projects.",
        "active",
        "1.1",
        "default",
        "sha256:bf36d035e20c3533546f4c0aebfad6b737902aa79cb7bad2566b017925ac910e",
    ),
    "standard-bundle-authoring": (
        "Standard Bundle Authoring Standard",
        "The contract every standard bundle in this repository must declare.",
        "active",
        "2.1",
        "internal",
        "sha256:480d81333159337279a493896478298ba3d46c72ca4e6b09205438435017705b",
    ),
}

# Catalog 5 also retains superseded advertised versions: removing an advertised
# entry requires a catalog-major transition (ADR 0024), so replaced payloads stay
# listed beside their successors. Only the activation test compares the full
# catalog entry set; the per-family tests above track current authority only.
_RETAINED_CATALOG_ENTRIES = {
    (
        "agent-handoff",
        "1.1",
        "retained",
        "sha256:e5e300e761c3b95bb36a95d0e001c2fa428c21843e15cdbf66202327fdb6ded1",
    ),
    (
        "standard-bundle-authoring",
        "2.0",
        "internal",
        "sha256:5fec499e321fc4d20ea9ddb50f6dceae1da800dd66d909ebea2dbd23e84597ca",
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
    } | _RETAINED_CATALOG_ENTRIES
    assert not (_ROOT / ".project-standards.yml").exists()
    assert all(
        (_ROOT / ".standards" / name).is_file()
        for name in ("catalog.toml", "config.toml", "lock.toml")
    )
    assert sync_payload_projection(_ROOT, check=True) == ()
    for link in plan_payload_projection(_ROOT).links:
        assert link.destination.is_symlink()
        assert not link.destination.readlink().is_absolute()
        assert link.destination.resolve(strict=True).read_bytes() == link.source.read_bytes()


def test_catalog_agent_summaries_link_to_their_canonical_standard() -> None:
    for standard_id, (_name, _summary, _status, version, _role, _digest) in _PACKAGES.items():
        summary = (
            _ROOT / "standards" / standard_id / "versions" / version / "agent-summary.md"
        ).read_text(encoding="utf-8")

        assert "(README.md)" in summary, standard_id
        assert "authoritative" in summary, standard_id


def test_mutable_family_navigation_defers_to_immutable_payload_authority() -> None:
    for standard_id, (_name, _summary, _status, version, _role, _digest) in _PACKAGES.items():
        family = _ROOT / "standards" / standard_id
        payload = family / "versions" / version
        root_readme = (family / "README.md").read_text(encoding="utf-8")
        root_summary = (family / "agent-summary.md").read_text(encoding="utf-8")

        assert f"versions/{version}/README.md" in root_readme, standard_id
        assert f"versions/{version}/agent-summary.md" in root_readme, standard_id
        assert f"versions/{version}/README.md" in root_summary, standard_id
        assert f"versions/{version}/agent-summary.md" in root_summary, standard_id
        assert (family / "README.md").read_bytes() != (payload / "README.md").read_bytes()
        assert (family / "agent-summary.md").read_bytes() != (
            payload / "agent-summary.md"
        ).read_bytes()
