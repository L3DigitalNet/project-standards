"""Tests for the Markdown frontmatter validator.

See ``tests/README.md`` for the testing strategy these cases implement.

Organisation (the three layers from the strategy doc):

  * Numbered cases 1-15 — the original spec-mapped schema/config cases. Cases 1-14
    exercise schema behaviour through ``validate_file``; case 15 covers config
    include/exclude resolution through ``main``.
  * "Schema V1.1" section — the additive 1.1.0 surface (the optional ``consumer``
    enum and the widened ``schema_version`` enum), sitting after the numbered
    schema cases. ``MINIMAL``/``STANDARD`` stay pinned at ``1.0`` so the rest of
    the suite doubles as backward-compatibility coverage.
  * "Unit" section — pure helpers in isolation (``parse_frontmatter``,
    ``_coerce_dates``, ``resolve_schema_path``, ``find_bundled_schema``,
    ``load_config``) including their malformed-input fallbacks.
  * "Integration" section — the ``main`` CLI exit-code contract (0/1/2) and flags.
  * "Contract / dogfood" section — the shipped ``examples/`` and bundled schema.

Exit-code contract for ``validate-frontmatter`` (asserted in the Integration section):
  0 = all matched files valid (or nothing matched); 1 = validation errors;
  2 = operator error (schema missing / unreadable / not a valid JSON Schema).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from tools.validate_frontmatter import (
    collect_paths,
    find_bundled_schema,
    load_config,
    main,
    parse_frontmatter,
    resolve_schema_path,
    validate_file,
)

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
def test_missing_frontmatter_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    errors = _check(tmp_path, validator, "# No frontmatter here\n\nJust prose.\n")
    assert errors
    assert "no frontmatter" in errors[0]


# 4.
def test_frontmatter_not_at_top_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    content = _doc(MINIMAL, leading="Some intro paragraph.\n\n")
    errors = _check(tmp_path, validator, content)
    assert errors
    assert "no frontmatter" in errors[0]


# 5.
def test_missing_required_field_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = dict(MINIMAL)
    del meta["title"]
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("title" in e for e in errors)


# 6.
def test_invalid_doc_type_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**MINIMAL, "doc_type": "blogpost"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("doc_type" in e for e in errors)


# 7.
def test_invalid_status_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "status": "published"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("status" in e for e in errors)


# 8.
def test_invalid_confidence_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**STANDARD, "confidence": "very-high"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("confidence" in e for e in errors)


# 9.
def test_invalid_date_format_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**MINIMAL, "created": "06/02/2026"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("created" in e for e in errors)


# 10.
def test_unknown_top_level_field_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**MINIMAL, "category": "misc"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert errors


# 11.
def test_project_extension_passes(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**STANDARD, "project": {"service": "netbox", "env": "home-lab"}}
    assert _check(tmp_path, validator, _doc(meta)) == []


# 12.
def test_publish_extension_passes(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**STANDARD, "publish": {"slug": "test", "draft": False}}
    assert _check(tmp_path, validator, _doc(meta)) == []


# 13.
def test_duplicate_tags_fail(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**MINIMAL, "tags": ["infra", "infra"]}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("tags" in e for e in errors)


# 14.
def test_invalid_tag_format_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**MINIMAL, "tags": ["Not Kebab"]}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("tags" in e for e in errors)


# ===========================================================================
# Schema V1.1 — additive surface (release 1.1.0, Path A)
#
# Two changes: schema_version gains "1.1" (keeping "1.0"), and `consumer` is a
# new OPTIONAL standard-profile enum. These cases pin both the new acceptances
# and the still-rejected neighbours. No link-pattern cases: Path A ships the
# repo-root link rule as convention only, not schema-enforced (deferred to 2.0.0).
# ===========================================================================


def test_schema_version_1_1_accepted(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**STANDARD, "schema_version": "1.1", "consumer": "agent"}
    assert _check(tmp_path, validator, _doc(meta)) == []


def test_schema_version_1_0_still_accepted(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    # Backward-compat contract for a minor bump: 1.0 documents must stay valid.
    assert _check(tmp_path, validator, _doc({**MINIMAL, "schema_version": "1.0"})) == []


def test_schema_version_unknown_value_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    errors = _check(tmp_path, validator, _doc({**MINIMAL, "schema_version": "1.2"}))
    assert any("schema_version" in e for e in errors)


@pytest.mark.parametrize("value", ["user", "agent", "mix", "unknown"])
def test_consumer_enum_values_accepted(
    tmp_path: Path, validator: Draft202012Validator, value: str
) -> None:
    meta = {**STANDARD, "schema_version": "1.1", "consumer": value}
    assert _check(tmp_path, validator, _doc(meta)) == []


def test_consumer_invalid_value_fails(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = {**STANDARD, "schema_version": "1.1", "consumer": "robot"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("consumer" in e for e in errors)


def test_consumer_is_optional(tmp_path: Path, validator: Draft202012Validator) -> None:
    # consumer absent from an otherwise-standard 1.1 document must still pass.
    assert (
        _check(tmp_path, validator, _doc({**STANDARD, "schema_version": "1.1"})) == []
    )


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


def test_exclude_dir_glob_matches_nested_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `dir/**` exclude must drop files beneath it on every Python version.

    Regression guard: Path.glob's `**` matches files on 3.13+ but only directories on
    <=3.12, so glob-based exclusion silently leaked nested files (e.g. docs/decisions/*)
    on older interpreters. fnmatch-based exclusion is version-independent.
    """
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "keep.md").write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "decisions" / "adr.md").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    got = [
        p.as_posix()
        for p in collect_paths([], None, ["docs/**/*.md"], ["docs/decisions/**"])
    ]
    assert got == ["docs/keep.md"]


# ===========================================================================
# Unit — parse_frontmatter
#
# The block detector and YAML loader. Its contract: return a mapping for a valid
# leading frontmatter block, or None for anything else (no block, a non-mapping
# block, an unterminated block). None is what makes "no frontmatter found" work.
# ===========================================================================


def test_parse_returns_mapping() -> None:
    assert parse_frontmatter("---\nid: x\ntitle: T\n---\n\nbody\n") == {
        "id": "x",
        "title": "T",
    }


def test_parse_no_block_returns_none() -> None:
    assert parse_frontmatter("# Just a heading\n\nProse.\n") is None


def test_parse_block_not_at_top_returns_none() -> None:
    # A leading line before the fence means it is not frontmatter (\A anchor).
    assert parse_frontmatter("intro\n\n---\nid: x\n---\n") is None


def test_parse_unterminated_block_returns_none() -> None:
    assert parse_frontmatter("---\nid: x\ntitle: T\n") is None


def test_parse_non_mapping_block_returns_none() -> None:
    # A YAML list is valid YAML but not a frontmatter mapping.
    assert parse_frontmatter("---\n- a\n- b\n---\n") is None


def test_parse_scalar_block_returns_none() -> None:
    assert parse_frontmatter("---\njust a bare string\n---\n") is None


def test_parse_empty_block_returns_none() -> None:
    # safe_load("") is None, which is not a mapping.
    assert parse_frontmatter("---\n\n---\n") is None


def test_parse_crlf_line_endings() -> None:
    # Authoring on Windows / a CRLF editor must still parse (regex allows \r?\n).
    crlf = _doc(MINIMAL).replace("\n", "\r\n")
    parsed = parse_frontmatter(crlf)
    assert parsed is not None
    assert parsed["id"] == MINIMAL["id"]


# _coerce_dates is exercised here through the public surface: YAML safe_load turns
# an unquoted date into a datetime.date, which parse_frontmatter must hand back as
# an ISO string so the string-typed schema accepts it.
def test_parse_coerces_unquoted_dates_to_iso_strings() -> None:
    parsed = parse_frontmatter("---\ncreated: 2026-06-02\n---\n")
    assert parsed is not None
    assert parsed == {"created": "2026-06-02"}
    assert isinstance(parsed["created"], str)


def test_parse_coerces_dates_nested() -> None:
    text = "---\ndates:\n  - 2026-06-02\nmeta:\n  reviewed: 2025-01-01\n---\n"
    assert parse_frontmatter(text) == {
        "dates": ["2026-06-02"],
        "meta": {"reviewed": "2025-01-01"},
    }


# ===========================================================================
# Unit — schema resolution (resolve_schema_path / find_bundled_schema)
#
# A bare token is a bundled schema *name*; anything with a separator or a .json
# suffix is a filesystem *path*. This is what lets a config say either
# schema: markdown-frontmatter   or   schema: ./my/custom.schema.json
# ===========================================================================


def test_resolve_bare_name_is_bundled_schema() -> None:
    resolved = resolve_schema_path("markdown-frontmatter")
    assert resolved.name == "markdown-frontmatter.schema.json"
    assert resolved.is_file()


def test_resolve_none_defaults_to_bundled() -> None:
    assert resolve_schema_path(None).name == "markdown-frontmatter.schema.json"


def test_resolve_json_suffix_is_treated_as_path() -> None:
    assert resolve_schema_path("custom.json") == Path("custom.json")


def test_resolve_value_with_separator_is_treated_as_path() -> None:
    assert resolve_schema_path("schemas/custom.schema.json") == Path(
        "schemas/custom.schema.json"
    )


def test_find_bundled_schema_resolves_real_schema() -> None:
    assert find_bundled_schema("markdown-frontmatter").is_file()


def test_find_bundled_schema_missing_returns_canonical_path() -> None:
    # Unknown name: return the canonical source path (not raise) so the caller
    # surfaces a clear read error against the expected location.
    resolved = find_bundled_schema("does-not-exist")
    assert resolved.name == "does-not-exist.schema.json"
    assert not resolved.exists()


# ===========================================================================
# Unit — load_config
#
# Reads the nested markdown.frontmatter section. Every branch must degrade to safe
# defaults (required=True, empty include/exclude, schema=None) rather than raise,
# because a missing or malformed config should not crash CI — it should fall back
# to "validate everything, require frontmatter".
# ===========================================================================


def test_load_config_missing_file_uses_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nope.yml")
    assert cfg.required is True
    assert cfg.schema is None
    assert cfg.include == []
    assert cfg.exclude == []


def test_load_config_full(tmp_path: Path) -> None:
    path = _write_config(tmp_path, include=["docs/*.md"], exclude=["docs/x.md"])
    cfg = load_config(path)
    assert cfg.schema == "markdown-frontmatter"
    assert cfg.required is True
    assert cfg.include == ["docs/*.md"]
    assert cfg.exclude == ["docs/x.md"]


def test_load_config_required_false_is_honoured(tmp_path: Path) -> None:
    path = tmp_path / ".project-standards.yml"
    body = {"markdown": {"frontmatter": {"required": False}}}
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    assert load_config(path).required is False


def test_load_config_top_level_not_mapping_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / ".project-standards.yml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    assert load_config(path).required is True


def test_load_config_partial_nesting_uses_defaults(tmp_path: Path) -> None:
    # `markdown` present but no `frontmatter` child — must not crash.
    path = tmp_path / ".project-standards.yml"
    path.write_text("markdown:\n  other: 1\n", encoding="utf-8")
    cfg = load_config(path)
    assert cfg.include == [] and cfg.schema is None


# _as_str_list is covered here through the public surface: a non-list `include`
# value must coerce to an empty list rather than propagate a wrong type.
def test_load_config_non_list_include_coerced_to_empty(tmp_path: Path) -> None:
    path = tmp_path / ".project-standards.yml"
    path.write_text(
        "markdown:\n  frontmatter:\n    include: not-a-list\n", encoding="utf-8"
    )
    assert load_config(path).include == []


# ===========================================================================
# Unit — validate_file edge cases
# ===========================================================================


def test_no_require_frontmatter_skips_missing(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    path = _write(tmp_path, "# No frontmatter\n\nProse.\n")
    assert validate_file(path, validator, require_frontmatter=False) == []


def test_unreadable_path_reports_error(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    # A directory cannot be read as text, which reaches the OSError branch and
    # reports a "cannot read file" error.
    target = tmp_path / "is-a-dir.md"
    target.mkdir()
    errors = validate_file(target, validator, require_frontmatter=True)
    assert len(errors) == 1
    assert "cannot read file" in errors[0]


def test_error_message_includes_field_path(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    # An item-level failure must name the indexed path (tags.0), proving the
    # field-formatting in validate_file walks error.path correctly.
    meta = {**MINIMAL, "tags": ["Not Kebab"]}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("[tags.0]" in e for e in errors)


def test_root_level_error_labelled_root(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    meta = dict(MINIMAL)
    del meta["title"]
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("[(root)]" in e and "required" in e for e in errors)


# ===========================================================================
# Integration — the main() CLI exit-code contract (0 / 1 / 2) and flags
# ===========================================================================


def test_main_missing_schema_file_returns_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--schema", "nonexistent.json", "--quiet"]) == 2


def test_main_invalid_schema_returns_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Valid JSON, but not a valid Draft 2020-12 schema (`type` must be a known type).
    bad = tmp_path / "bad.schema.json"
    bad.write_text(json.dumps({"type": "banana"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["--schema", str(bad), "--quiet"]) == 2


def test_main_no_files_matched_returns_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--quiet"]) == 0


def test_main_valid_explicit_file_returns_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, _doc(MINIMAL), name="good.md")
    monkeypatch.chdir(tmp_path)
    assert main(["good.md", "--schema", str(SCHEMA_PATH), "--quiet"]) == 0


def test_main_invalid_explicit_file_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, _doc({**MINIMAL, "doc_type": "nonsense"}), name="bad.md")
    monkeypatch.chdir(tmp_path)
    assert main(["bad.md", "--schema", str(SCHEMA_PATH), "--quiet"]) == 1


def test_main_glob_flag_collects_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, _doc(MINIMAL), name="a.md")
    monkeypatch.chdir(tmp_path)
    assert main(["--glob", "*.md", "--schema", str(SCHEMA_PATH), "--quiet"]) == 0


def test_main_no_require_frontmatter_flag_passes_plain_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "# No frontmatter\n", name="plain.md")
    monkeypatch.chdir(tmp_path)
    args = [
        "plain.md",
        "--schema",
        str(SCHEMA_PATH),
        "--no-require-frontmatter",
        "--quiet",
    ]
    assert main(args) == 0


# ===========================================================================
# Contract / dogfood — the shipped artifacts must stay valid for consumers
# ===========================================================================

EXAMPLE_FILES = sorted((_REPO_ROOT / "examples").glob("*.md"))


def test_examples_directory_is_not_empty() -> None:
    # Guard the parametrization below: an empty glob would make the dogfood test
    # vacuously pass, hiding a missing examples/ directory.
    assert EXAMPLE_FILES, "expected worked examples under examples/"


@pytest.mark.parametrize("example", EXAMPLE_FILES, ids=[p.name for p in EXAMPLE_FILES])
def test_shipped_example_validates(
    example: Path, validator: Draft202012Validator
) -> None:
    assert validate_file(example, validator, require_frontmatter=True) == []


def test_bundled_schema_is_valid_draft2020() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Raises SchemaError if the shipped contract is itself malformed.
    Draft202012Validator.check_schema(schema)  # pyright: ignore[reportUnknownMemberType]
