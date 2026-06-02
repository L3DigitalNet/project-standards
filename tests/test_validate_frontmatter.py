"""Tests for the Markdown frontmatter validator.

The 15 numbered cases map directly to the test requirements in the standard's
implementation spec. Cases 1-14 exercise schema behaviour through `validate_file`;
case 15 exercises config include/exclude resolution through `main`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from tools.validate_frontmatter import main, validate_file

_REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = _REPO_ROOT / "schemas" / "markdown-frontmatter.schema.json"

# Canonical valid frontmatter, kept as dicts so individual tests can mutate one field.
MINIMAL: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "test-doc",
    "title": "Test Doc",
    "description": "A test document.",
    "doc_type": "note",
    "status": "draft",
    "created": "2026-06-02",
    "updated": "2026-06-02",
    "tags": [],
    "aliases": [],
    "related": [],
}

STANDARD: dict[str, Any] = {
    **MINIMAL,
    "reviewed": None,
    "owner": "",
    "source": [],
    "confidence": "unknown",
    "visibility": "internal",
    "license": None,
}


@pytest.fixture
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _doc(meta: dict[str, Any], *, body: str = "# Test Doc\n", leading: str = "") -> str:
    """Render a Markdown document with `meta` as a YAML frontmatter block."""
    front = yaml.safe_dump(meta, sort_keys=False)
    return f"{leading}---\n{front}---\n\n{body}"


def _write(tmp_path: Path, content: str, name: str = "doc.md") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _check(tmp_path: Path, validator: Draft202012Validator, content: str) -> list[str]:
    path = _write(tmp_path, content)
    return validate_file(path, validator, require_frontmatter=True)


# 1.
def test_valid_minimal_passes(tmp_path: Path, validator: Draft202012Validator) -> None:
    assert _check(tmp_path, validator, _doc(MINIMAL)) == []


# 2.
def test_valid_standard_passes(tmp_path: Path, validator: Draft202012Validator) -> None:
    assert _check(tmp_path, validator, _doc(STANDARD)) == []


# 3.
def test_missing_frontmatter_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    errors = _check(tmp_path, validator, "# No frontmatter here\n\nJust prose.\n")
    assert errors
    assert "no frontmatter" in errors[0]


# 4.
def test_frontmatter_not_at_top_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    content = _doc(MINIMAL, leading="Some intro paragraph.\n\n")
    errors = _check(tmp_path, validator, content)
    assert errors
    assert "no frontmatter" in errors[0]


# 5.
def test_missing_required_field_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = dict(MINIMAL)
    del meta["title"]
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("title" in e for e in errors)


# 6.
def test_invalid_doc_type_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "doc_type": "blogpost"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("doc_type" in e for e in errors)


# 7.
def test_invalid_status_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "status": "published"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("status" in e for e in errors)


# 8.
def test_invalid_confidence_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**STANDARD, "confidence": "very-high"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("confidence" in e for e in errors)


# 9.
def test_invalid_date_format_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "created": "06/02/2026"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("created" in e for e in errors)


# 10.
def test_unknown_top_level_field_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "category": "misc"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert errors


# 11.
def test_project_extension_passes(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**STANDARD, "project": {"service": "netbox", "env": "home-lab"}}
    assert _check(tmp_path, validator, _doc(meta)) == []


# 12.
def test_publish_extension_passes(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**STANDARD, "publish": {"slug": "test", "draft": False}}
    assert _check(tmp_path, validator, _doc(meta)) == []


# 13.
def test_duplicate_tags_fail(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "tags": ["infra", "infra"]}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("tags" in e for e in errors)


# 14.
def test_invalid_tag_format_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "tags": ["Not Kebab"]}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("tags" in e for e in errors)


# 15.
@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A temp repo with a valid and an invalid doc, with cwd set to it."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "good.md").write_text(_doc(MINIMAL), encoding="utf-8")
    bad = {**MINIMAL, "doc_type": "nonsense"}
    (docs / "bad.md").write_text(_doc(bad), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def _write_config(root: Path, include: list[str], exclude: list[str]) -> Path:
    config = {
        "markdown": {
            "frontmatter": {
                "schema": "markdown-frontmatter",
                "required": True,
                "include": include,
                "exclude": exclude,
            }
        }
    }
    path = root / ".project-standards.yml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def test_config_include_only_good_passes(workspace: Path) -> None:
    _write_config(workspace, include=["docs/good.md"], exclude=[])
    assert main(["--config", ".project-standards.yml", "--quiet"]) == 0


def test_config_exclude_drops_bad(workspace: Path) -> None:
    _write_config(workspace, include=["docs/*.md"], exclude=["docs/bad.md"])
    assert main(["--config", ".project-standards.yml", "--quiet"]) == 0


def test_config_include_bad_fails(workspace: Path) -> None:
    _write_config(workspace, include=["docs/*.md"], exclude=[])
    assert main(["--config", ".project-standards.yml", "--quiet"]) == 1
