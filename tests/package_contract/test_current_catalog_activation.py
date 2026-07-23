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
        "1.2",
        "default",
        "sha256:5b36e6f63a2477f2c7c5bcef647edc8b674366eb64937aba646aefc65d8a6f21",
    ),
    "agent-handoff": (
        "Agent Handoff Standard",
        "Repository-local, lifetime-routed project knowledge and bounded agent session continuity.",
        "active",
        "1.4",
        "default",
        "sha256:17bdc8b25c6cc6ac644057a85f55ed244adf88b58f4ad052d68222d20c24120a",
    ),
    "cli-documentation": (
        "CLI Documentation Standard",
        "Profile-based user-facing CLI help, usage-reference, man-page, and drift-check documentation.",
        "active",
        "1.3",
        "default",
        "sha256:2c15f700fd343327b675295579220572fea9f2735386da5aa266d38839a7f9c4",
    ),
    "markdown-frontmatter": (
        "Markdown Frontmatter Standard",
        "Canonical metadata, ID, and reference validation for managed Markdown documents.",
        "active",
        "1.5",
        "default",
        "sha256:b31b9a97edb48334bbb6af2988272baf071449a457a303e218dbb8c6436a540c",
    ),
    "markdown-tooling": (
        "Markdown Tooling Standard",
        "Prettier, markdownlint, EditorConfig, and CI tooling for Markdown and adjacent structured text.",
        "active",
        "1.8",
        "default",
        "sha256:22ebe7b95ca82daa276746c9bf3f0688d15ce4b47314b7e4abea206df7212783",
    ),
    "project-spec": (
        "Project Specification Standard",
        "Tiered, stable-ID, CLI-validated project specification format and tooling.",
        "active",
        "1.4",
        "default",
        "sha256:8ea9d9a5f82156c1f177defa4bd78d5f55693013ced2ab9d07cabce63969e845",
    ),
    "python-coding": (
        "Python Coding Standard",
        "Reference guidance for Python code shape, boundaries, typing, tests, and agent behavior.",
        "draft",
        "0.6",
        "reference-only",
        "sha256:a4c4d6f0d61f81beeabefe48a8ef29f9789b55d7159ab01bb64b1da8417db14d",
    ),
    "python-tooling": (
        "Python Tooling SSOT Standard",
        "uv, Ruff, BasedPyright, pytest/coverage, pip-audit, CI, and agent-instruction tooling for Python projects.",
        "active",
        "1.8",
        "default",
        "sha256:7397498723a1f683b09037c233e1872df825cd70a27c514a45bb2bacf24cb312",
    ),
    "standard-bundle-authoring": (
        "Standard Bundle Authoring Standard",
        "The contract every standard bundle in this repository must declare.",
        "active",
        "2.5",
        "internal",
        "sha256:3eb5d86979755372bbe851b06b82235410378cba71c6f1b9dbc7c49557623c4d",
    ),
}

# Catalog 5 also retains superseded advertised versions: removing an advertised
# entry requires a catalog-major transition (ADR 0024), so replaced payloads stay
# listed beside their successors. Only the activation test compares the full
# catalog entry set; the per-family tests above track current authority only.
_RETAINED_CATALOG_ENTRIES = {
    # 5.8.0 FR-013: T10 flipped python-tooling 1.8 to default; the superseded 1.7
    # predecessor stays advertised as retained (removal needs a catalog-major bump).
    (
        "python-tooling",
        "1.7",
        "retained",
        "sha256:6ffff0fe5b82d15b1a30e23cb49dd0fba7ff8766a42bbf31f83eabb16e63e92b",
    ),
    (
        "python-tooling",
        "1.6",
        "retained",
        "sha256:78e9f7737e78990bdb32b559b87d3ba4f975ddf4b0d0bd5f1ecac1e772da1e5b",
    ),
    (
        "python-tooling",
        "1.5",
        "retained",
        "sha256:734c2b975c01307ed0a27a14c8a391ca4e73334180275d50012076b506021de3",
    ),
    (
        "standard-bundle-authoring",
        "2.4",
        "internal",
        "sha256:b2bdf94dffb7c8536debca60fdb4eb557cfcc364e47165a2634dccf002ca099f",
    ),
    (
        "agent-handoff",
        "1.3",
        "retained",
        "sha256:3e6e53f9ba889b7f68624c1c3861c5e26ac889a6025c4fb7b819b49e140d1f78",
    ),
    # 5.8.0 FR-013: T10 flipped markdown-tooling 1.8 to default; the superseded 1.7
    # predecessor stays advertised as retained (removal needs a catalog-major bump).
    (
        "markdown-tooling",
        "1.7",
        "retained",
        "sha256:87376b5d4c3ce027ca3db249d5d27bb7a1bc6d2e7f843b7074f8f73d2a084c10",
    ),
    (
        "markdown-tooling",
        "1.6",
        "retained",
        "sha256:cf123371ac92c23942a37a5765b99d1af4f3c2481e2b75c2a239b6b17bc1ba8b",
    ),
    (
        "project-spec",
        "1.3",
        "retained",
        "sha256:56de712072c586549c68cdadfe4598b63d9d7d3ea7cb4f7727fd48c6ef4084a6",
    ),
    (
        "standard-bundle-authoring",
        "2.3",
        "internal",
        "sha256:dbe940f518534224ccf58956a3ce02660f99be20cf161241308444eddccee7d5",
    ),
    (
        "markdown-tooling",
        "1.5",
        "retained",
        "sha256:2f06b126747822b330ed0239630b0dad413afb9f8c56380d72848403a9c23091",
    ),
    (
        "python-tooling",
        "1.4",
        "retained",
        "sha256:6cece71c53909b6dcd04a50e873ce16eb98aa800203b186e472439f7986c3e5e",
    ),
    (
        "adr",
        "1.1",
        "retained",
        "sha256:82e9e3ae5d50a641b4b47366ef5d66fd85b13555ffda0d9ac1c99aadd1c6c719",
    ),
    (
        "markdown-frontmatter",
        "1.2",
        "retained",
        "sha256:e1e2ac7d41fb2b7be8772717292d5d8afadcbe878a70d562e82d7f4c1bdd606c",
    ),
    (
        "markdown-tooling",
        "1.2",
        "retained",
        "sha256:0d4f89403c4b4c4a2d1dc9c579deddf717f5e01d1c424cac4a103ecb03be12ae",
    ),
    (
        "project-spec",
        "1.1",
        "retained",
        "sha256:ed1445342d72836707dd455fd5771f28b71b53acbb1499e4f9250e33f548d36e",
    ),
    (
        "python-coding",
        "0.5",
        "reference-only",
        "sha256:c027af45f85e84717e7ce9909adcd71363745e688538bd88a303dd813a351d80",
    ),
    (
        "python-tooling",
        "1.1",
        "retained",
        "sha256:bf36d035e20c3533546f4c0aebfad6b737902aa79cb7bad2566b017925ac910e",
    ),
    (
        "cli-documentation",
        "1.1",
        "retained",
        "sha256:a6aa0b4a9e0f2247a0795dac3073a55e72d9047581493e1326eeb42d43442445",
    ),
    (
        "agent-handoff",
        "1.1",
        "retained",
        "sha256:e5e300e761c3b95bb36a95d0e001c2fa428c21843e15cdbf66202327fdb6ded1",
    ),
    (
        "agent-handoff",
        "1.2",
        "retained",
        "sha256:197d9c6877781abf1a9f0a3d3f37092413600ebaff604371ae10c7405925cf5b",
    ),
    (
        "standard-bundle-authoring",
        "2.0",
        "internal",
        "sha256:5fec499e321fc4d20ea9ddb50f6dceae1da800dd66d909ebea2dbd23e84597ca",
    ),
    (
        "standard-bundle-authoring",
        "2.1",
        "internal",
        "sha256:480d81333159337279a493896478298ba3d46c72ca4e6b09205438435017705b",
    ),
    (
        "markdown-tooling",
        "1.3",
        "retained",
        "sha256:e6bf4dafb75f1c87a5ce763a3f52c98749fdff4902cd1e1beb13eebaff12deca",
    ),
    (
        "markdown-frontmatter",
        "1.3",
        "retained",
        "sha256:97327fffde61fd981c08949292c504a930f4fe6786af455cb1f6c7d204dc7c43",
    ),
    # 5.8.0 FR-013: T10 flipped markdown-frontmatter 1.5 to default; the superseded
    # 1.4 predecessor stays advertised as retained (removal needs a catalog-major bump).
    (
        "markdown-frontmatter",
        "1.4",
        "retained",
        "sha256:a981a54cb6c6a36e2bfb73eca61c9b84100da67b072cd07c7c4ffea4b0593647",
    ),
    (
        "python-tooling",
        "1.2",
        "retained",
        "sha256:04264e67678708fd5f1f44a7145f3a1e23acfb14b72a6cba1dad61ca5a6ace84",
    ),
    (
        "markdown-tooling",
        "1.4",
        "retained",
        "sha256:31a4bfd502cf332a68a20b3682b83ec8a797d58c4b7f565cbfe6043cf787c8b5",
    ),
    (
        "python-tooling",
        "1.3",
        "retained",
        "sha256:3da255cdc757f55aaa4983a5e7c24593be5bf2fcc1406f5f817265602186769b",
    ),
    (
        "cli-documentation",
        "1.2",
        "retained",
        "sha256:edde1a4011314a9b05f372731a8d50e3b5a0663d39369089256d442430e4943c",
    ),
    (
        "project-spec",
        "1.2",
        "retained",
        "sha256:d5474ab7035937ac96d0551ecf9c076a71752e9e18dcfe14789d960933418c47",
    ),
    (
        "standard-bundle-authoring",
        "2.2",
        "internal",
        "sha256:538d8afa6760bddd3f4be13b7b001257f028f94df4385a42e3aba5a19559bc83",
    ),
}


def _family_source(standard_id: str) -> str:
    name, summary, status, version, _role, digest = _PACKAGES[standard_id]
    source = (
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
    if standard_id == "python-tooling":
        source += (
            "\n[[versions]]\n"
            'version = "1.4"\n'
            'payload = "versions/1.4/payload.toml"\n'
            'digest = "sha256:6cece71c53909b6dcd04a50e873ce16eb98aa800203b186e472439f7986c3e5e"\n'
            "\n[[versions]]\n"
            'version = "1.5"\n'
            'payload = "versions/1.5/payload.toml"\n'
            'digest = "sha256:734c2b975c01307ed0a27a14c8a391ca4e73334180275d50012076b506021de3"\n'
            "\n[[versions]]\n"
            'version = "1.6"\n'
            'payload = "versions/1.6/payload.toml"\n'
            'digest = "sha256:78e9f7737e78990bdb32b559b87d3ba4f975ddf4b0d0bd5f1ecac1e772da1e5b"\n'
            # 1.7 is the now-retained predecessor of the 1.8 default (FR-013); the
            # isolated multi-version family accumulates it so resolution stays covered.
            "\n[[versions]]\n"
            'version = "1.7"\n'
            'payload = "versions/1.7/payload.toml"\n'
            'digest = "sha256:6ffff0fe5b82d15b1a30e23cb49dd0fba7ff8766a42bbf31f83eabb16e63e92b"\n'
        )
    if standard_id == "markdown-tooling":
        # The 1.8 default's correction migration declares from = "package:1.7", so the
        # isolated family must advertise the retained 1.7 predecessor as its endpoint.
        source += (
            "\n[[versions]]\n"
            'version = "1.7"\n'
            'payload = "versions/1.7/payload.toml"\n'
            'digest = "sha256:87376b5d4c3ce027ca3db249d5d27bb7a1bc6d2e7f843b7074f8f73d2a084c10"\n'
        )
    if standard_id == "markdown-frontmatter":
        # The 1.5 default's correction migration declares from = "package:1.4", so the
        # isolated family must advertise the retained 1.4 predecessor as its endpoint.
        source += (
            "\n[[versions]]\n"
            'version = "1.4"\n'
            'payload = "versions/1.4/payload.toml"\n'
            'digest = "sha256:a981a54cb6c6a36e2bfb73eca61c9b84100da67b072cd07c7c4ffea4b0593647"\n'
        )
    return source


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
        if standard_id == "python-tooling":
            shutil.copytree(source / "versions/1.4", target / "versions/1.4")
            shutil.copytree(source / "versions/1.5", target / "versions/1.5")
            shutil.copytree(source / "versions/1.6", target / "versions/1.6")
            shutil.copytree(source / "versions/1.7", target / "versions/1.7")
        if standard_id == "markdown-tooling":
            shutil.copytree(source / "versions/1.7", target / "versions/1.7")
        if standard_id == "markdown-frontmatter":
            shutil.copytree(source / "versions/1.4", target / "versions/1.4")
        (target / "standard.toml").write_text(_family_source(standard_id), encoding="utf-8")
    catalog = isolated / "catalogs/5.toml"
    catalog.parent.mkdir()
    catalog.write_text(_catalog_source(), encoding="utf-8")

    repository = build_package_repository(isolated, catalog_major=5)

    assert repository.findings == ()
    assert validate_package_repository(repository) == ()
    assert len(repository.families) == len(_PACKAGES)
    # Each advancing family carries the retained predecessor its correction migration
    # names: python-tooling 1.4-1.7 (4), markdown-tooling 1.7 (1), markdown-frontmatter
    # 1.4 (1) — six extra payloads beyond one default per family.
    assert len(repository.payloads) == len(_PACKAGES) + 6
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


def test_standard_bundle_authoring_2_2_is_internal_and_advertised() -> None:
    repository = build_package_repository(_ROOT, catalog_major=5)
    family = next(
        item
        for item in repository.families
        if item.manifest.standard.id == "standard-bundle-authoring"
    )

    assert "2.2" in {entry.version.value for entry in family.manifest.versions}
    payload = next(item for item in family.payloads if item.manifest.payload.version.value == "2.2")
    assert payload.manifest.payload.availability.value == "internal"
    assert repository.catalog is not None
    assert (
        "standard-bundle-authoring",
        "2.2",
        "internal",
    ) in {
        (entry.id, entry.version.value, entry.role.value) for entry in repository.catalog.packages
    }


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
