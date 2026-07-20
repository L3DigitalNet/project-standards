"""Contract tests for the Markdown Frontmatter standard-owned skill."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from project_standards.id_format import slugify

_REPO = Path(__file__).resolve().parent.parent
_SKILL = _REPO / "standards" / "markdown-frontmatter" / "skills" / "markdown-frontmatter"
_LEGACY_SKILL = (
    _REPO
    / "standards"
    / "markdown-frontmatter"
    / "versions"
    / "1.2"
    / "resources"
    / "legacy-markdown-frontmatter-skill.md"
)
_NEW_DOC_ID = _SKILL / "scripts" / "new-doc-id"


def _run_new_doc_id(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(_NEW_DOC_ID), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_skill_points_at_current_standard_pages() -> None:
    text = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    versioned_skill = (
        _REPO
        / "standards"
        / "markdown-frontmatter"
        / "versions"
        / "1.3"
        / "skills"
        / "markdown-frontmatter"
        / "SKILL.md"
    )
    assert (_SKILL / "SKILL.md").read_bytes() == versioned_skill.read_bytes()
    assert "markdown-frontmatter@1.3" in text
    assert "versions/1.3" in text
    assert "schema_version: '1.1'" in text
    assert "structure.md" in text
    assert "field-values.md" in text
    assert "V5 CI workflow" in text
    assert "project-standards@v4" not in text
    assert ".project-standards.yml" not in text
    legacy_text = _LEGACY_SKILL.read_text(encoding="utf-8")
    assert "project-standards@v4" in legacy_text
    assert ".project-standards.yml" in legacy_text
    assert "infrastructure" in text and "network" in text and "it" in text


def test_new_doc_id_generates_doc_type_prefixed_id() -> None:
    proc = _run_new_doc_id("--doc-type", "runbook", "Restart Netbox.md")
    assert proc.returncode == 0, proc.stderr
    assert re.fullmatch(r"runbook-[0-9a-z]{6}-restart-netbox\n", proc.stdout)


@pytest.mark.parametrize(
    "name",
    [
        "Café Notes & MTU.md",
        "Architecture Decision Record (ADR) Standard",
        "Standards Adoption and Compliance Procedure for Very Long Repository Documentation Titles",
    ],
)
def test_new_doc_id_slug_matches_shared_id_format(name: str) -> None:
    proc = _run_new_doc_id("--doc-type", "note", name)
    assert proc.returncode == 0, proc.stderr
    match = re.fullmatch(r"note-[0-9a-z]{6}-(?P<slug>[a-z0-9-]+)\n", proc.stdout)
    assert match is not None
    title = name.removesuffix(".md")
    assert match.group("slug") == slugify(title)


def test_new_doc_id_scaffold_is_canonical_and_quoted() -> None:
    proc = _run_new_doc_id("--scaffold", "--doc-type", "research", "--status", "active", "MTU")
    assert proc.returncode == 0, proc.stderr
    keys = re.findall(r"^([a-z_]+):", proc.stdout, flags=re.MULTILINE)
    assert keys == [
        "schema_version",
        "id",
        "title",
        "description",
        "doc_type",
        "status",
        "created",
        "updated",
        "tags",
        "aliases",
        "related",
    ]
    assert "schema_version: '1.1'" in proc.stdout
    assert "doc_type: 'research'" in proc.stdout
    assert "status: 'active'" in proc.stdout
    assert "tags: []" in proc.stdout


def test_new_doc_id_rejects_empty_slug() -> None:
    proc = _run_new_doc_id("///...")
    assert proc.returncode == 2


def test_new_doc_id_rejects_invalid_controlled_values() -> None:
    bad_doc_type = _run_new_doc_id("--doc-type", "readme", "overview")
    assert bad_doc_type.returncode == 2
    assert "invalid doc_type" in bad_doc_type.stderr

    bad_status = _run_new_doc_id("--status", "ready", "overview")
    assert bad_status.returncode == 2
    assert "invalid status" in bad_status.stderr


def test_new_doc_id_rejects_adr_doc_type() -> None:
    proc = _run_new_doc_id("--doc-type", "adr", "Router Upgrade")
    assert proc.returncode == 2
    assert "do not use this script for ADR ids" in proc.stderr
