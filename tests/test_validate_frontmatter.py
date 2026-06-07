"""Tests for the Markdown frontmatter validator.

See ``tests/README.md`` for the testing strategy these cases implement.

Organisation (the three layers from the strategy doc):

  * Numbered cases 1-14, plus a workspace fixture — the original spec-mapped
    schema/config cases. Cases 1-14 exercise schema behaviour through
    ``validate_file``; the ``# 15.`` marker sits on a fixture covering config
    include/exclude resolution through ``main``.
  * "Schema V1.1" section — the additive 1.1.0 surface (the optional ``consumer``
    enum and the widened ``schema_version`` enum), sitting after the numbered
    schema cases. ``MINIMAL``/``STANDARD`` stay pinned at ``1.0`` so the rest of
    the suite doubles as backward-compatibility coverage.
  * "Unit" section — pure helpers in isolation (``parse_frontmatter``,
    ``_coerce_dates``, ``resolve_schema_path``, ``find_bundled_schema``,
    ``load_config``) including their malformed-input fallbacks.
  * "Integration" section — the ``main`` CLI exit-code contract (0/1/2) and flags.
  * "Contract / dogfood" section — the shipped ``standards/*/examples/`` and bundled schema.

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

import project_standards.validate_frontmatter as _vf
from project_standards.validate_frontmatter import (
    collect_paths,
    find_bundled_schema,
    load_config,
    main,
    missing_adr_sections,
    parse_frontmatter,
    resolve_schema_path,
    validate_file,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(_vf.__file__).parent / "schemas" / "markdown-frontmatter.schema.json"

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


# ===========================================================================
# Schema V1.1 — additive surface (release 1.1.0, Path A)
#
# Two changes: schema_version gains "1.1" (keeping "1.0"), and `consumer` is a
# new OPTIONAL standard-profile enum. These cases pin both the new acceptances
# and the still-rejected neighbours. No link-pattern cases: Path A ships the
# repo-root link rule as convention only, not schema-enforced (deferred to 2.0.0).
# ===========================================================================


def test_schema_version_1_1_accepted(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**STANDARD, "schema_version": "1.1", "consumer": "agent"}
    assert _check(tmp_path, validator, _doc(meta)) == []


def test_schema_version_1_0_still_accepted(tmp_path: Path, validator: Draft202012Validator) -> None:
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


def test_consumer_invalid_value_fails(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = {**STANDARD, "schema_version": "1.1", "consumer": "robot"}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("consumer" in e for e in errors)


def test_consumer_is_optional(tmp_path: Path, validator: Draft202012Validator) -> None:
    # consumer absent from an otherwise-standard 1.1 document must still pass.
    assert _check(tmp_path, validator, _doc({**STANDARD, "schema_version": "1.1"})) == []


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

    got = [p.as_posix() for p in collect_paths([], None, ["docs/**/*.md"], ["docs/decisions/**"])]
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
    assert resolve_schema_path("schemas/custom.schema.json") == Path("schemas/custom.schema.json")


def test_find_bundled_schema_resolves_real_schema() -> None:
    assert find_bundled_schema("markdown-frontmatter").is_file()


def test_find_bundled_schema_missing_returns_canonical_path() -> None:
    # Unknown name: return the canonical source path (not raise) so the caller
    # surfaces a clear read error against the expected location.
    resolved = find_bundled_schema("does-not-exist")
    assert resolved.name == "does-not-exist.schema.json"
    assert not resolved.exists()


# ===========================================================================
# Unit — registry (bundled contract-version registry; see registry.py)
# ===========================================================================

from project_standards.registry import RegistryError, load_registry  # noqa: E402


def test_load_registry_real_file() -> None:
    reg = load_registry()
    assert reg.frontmatter_default == "1.1"
    assert reg.frontmatter_schema_name("1.1") == "markdown-frontmatter"
    assert reg.adr_default == "1.0"
    assert reg.adr_supported_frontmatter("1.0") == ["1.1"]
    assert reg.is_known_python_tooling("1.0") is True
    assert reg.is_known_python_tooling("9.9") is False


def test_registry_unknown_frontmatter_version_raises() -> None:
    reg = load_registry()
    with pytest.raises(RegistryError, match="unknown frontmatter version"):
        reg.frontmatter_schema_name("2.0")


def test_registry_unknown_adr_version_raises() -> None:
    reg = load_registry()
    with pytest.raises(RegistryError, match="unknown adr version"):
        reg.adr_supported_frontmatter("2.0")


def test_load_registry_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="cannot load registry"):
        load_registry(tmp_path / "nope.json")


def test_load_registry_non_object_raises(tmp_path: Path) -> None:
    bad = tmp_path / "registry.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(RegistryError, match="not a JSON object"):
        load_registry(bad)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (
            '{"frontmatter": {}, "adr": {}}',
            "missing frontmatter/adr/python_tooling/markdown_tooling",
        ),
        (
            '{"frontmatter": {"default": 1, "versions": {}}, "adr": {"default": "1.0", "versions": {}}, "python_tooling": {"default": "1.0", "versions": []}, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}}',
            "non-string default",
        ),
        (
            '{"frontmatter": {"default": "1.1", "versions": []}, "adr": {"default": "1.0", "versions": {}}, "python_tooling": {"default": "1.0", "versions": []}, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}}',
            "frontmatter.versions is not an object",
        ),
        (
            '{"frontmatter": {"default": "1.1", "versions": {"1.1": 9}}, "adr": {"default": "1.0", "versions": {}}, "python_tooling": {"default": "1.0", "versions": []}, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}}',
            "frontmatter.versions.1.1 is not a string",
        ),
        (
            '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}}, "adr": {"default": "1.0", "versions": []}, "python_tooling": {"default": "1.0", "versions": []}, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}}',
            "adr.versions is not an object",
        ),
        (
            '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}}, "adr": {"default": "1.0", "versions": {"1.0": []}}, "python_tooling": {"default": "1.0", "versions": []}, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}}',
            "adr.versions.1.0 is not an object",
        ),
        (
            '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}}, "adr": {"default": "1.0", "versions": {"1.0": {"supports_frontmatter": 5}}}, "python_tooling": {"default": "1.0", "versions": []}, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}}',
            "supports_frontmatter is not a list",
        ),
        (
            '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}}, "adr": {"default": "1.0", "versions": {"1.0": {"supports_frontmatter": ["1.1"]}}}, "python_tooling": {"default": "1.0", "versions": {}}, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}}',
            "python_tooling.versions is not a list",
        ),
        (
            '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}}, "adr": {"default": "1.0", "versions": {"1.0": {"supports_frontmatter": ["1.1"]}}}, "python_tooling": {"default": "1.0", "versions": ["1.0"]}, "markdown_tooling": {"default": "1.0", "versions": {}}}',
            "markdown_tooling.versions is not a list",
        ),
    ],
)
def test_load_registry_malformed_raises(tmp_path: Path, payload: str, match: str) -> None:
    bad = tmp_path / "registry.json"
    bad.write_text(payload, encoding="utf-8")
    with pytest.raises(RegistryError, match=match):
        load_registry(bad)


# ===========================================================================
# Unit — effective schema resolution (precedence + ambiguity guard)
# ===========================================================================

from project_standards.validate_frontmatter import (  # noqa: E402
    ConfigError,
    resolve_effective_schema,
)


def _cfg(**kw: Any) -> _vf.ProjectConfig:
    base: dict[str, Any] = {
        "schema": None,
        "include": [],
        "exclude": [],
        "required": True,
        "require_adr_sections": False,
    }
    base.update(kw)
    return _vf.ProjectConfig(**base)


def test_effective_schema_cli_wins() -> None:
    reg = load_registry()
    cfg = _cfg(schema="markdown-frontmatter", frontmatter_version="1.1")
    assert resolve_effective_schema(Path("/x/custom.json"), cfg, reg) == Path("/x/custom.json")


def test_effective_schema_custom_path_bypasses_version() -> None:
    reg = load_registry()
    cfg = _cfg(schema="./my/custom.schema.json")
    assert resolve_effective_schema(None, cfg, reg) == Path("./my/custom.schema.json")


def test_effective_schema_custom_path_and_version_is_config_error() -> None:
    reg = load_registry()
    cfg = _cfg(schema="./my/custom.schema.json", frontmatter_version="1.1")
    with pytest.raises(ConfigError, match="not both"):
        resolve_effective_schema(None, cfg, reg)


def test_effective_schema_version_resolves_to_bundled() -> None:
    reg = load_registry()
    cfg = _cfg(frontmatter_version="1.1")
    assert resolve_effective_schema(None, cfg, reg).name == "markdown-frontmatter.schema.json"


def test_effective_schema_unknown_version_raises() -> None:
    reg = load_registry()
    cfg = _cfg(frontmatter_version="2.0")
    with pytest.raises(RegistryError, match="unknown frontmatter version"):
        resolve_effective_schema(None, cfg, reg)


def test_effective_schema_bundled_name_default() -> None:
    reg = load_registry()
    assert resolve_effective_schema(None, _cfg(), reg).name == "markdown-frontmatter.schema.json"


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


def test_load_config_reads_version_keys(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".project-standards.yml"
    cfg_path.write_text(
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '1.1'\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n"
        "python_tooling:\n"
        "  version: '1.0'\n",
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    assert cfg.frontmatter_version == "1.1"
    assert cfg.adr_version == "1.0"
    assert cfg.python_tooling_version == "1.0"
    assert cfg.require_adr_sections is True


def test_load_config_version_keys_default_none(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".project-standards.yml"
    cfg_path.write_text("markdown:\n  frontmatter:\n    required: true\n", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.frontmatter_version is None
    assert cfg.adr_version is None
    assert cfg.python_tooling_version is None


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
    path.write_text("markdown:\n  frontmatter:\n    include: not-a-list\n", encoding="utf-8")
    assert load_config(path).include == []


# markdown.adr.require_sections — a SEPARATE config key from markdown.frontmatter.*,
# default off, so the opt-in ADR body-structure check (DEC-5) is additive: a config
# that never mentions it (or no config at all) leaves the check disabled.
def test_load_config_adr_require_sections_default_false(tmp_path: Path) -> None:
    path = _write_config(tmp_path, include=["docs/*.md"], exclude=[])
    assert load_config(path).require_adr_sections is False


def test_load_config_missing_file_adr_require_sections_false(tmp_path: Path) -> None:
    assert load_config(tmp_path / "nope.yml").require_adr_sections is False


def test_load_config_adr_require_sections_true_is_honoured(tmp_path: Path) -> None:
    path = tmp_path / ".project-standards.yml"
    body = {"markdown": {"adr": {"require_sections": True}}}
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    assert load_config(path).require_adr_sections is True


# ===========================================================================
# Unit — validate_file edge cases
# ===========================================================================


def test_no_require_frontmatter_skips_missing(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    path = _write(tmp_path, "# No frontmatter\n\nProse.\n")
    assert validate_file(path, validator, require_frontmatter=False) == []


def test_unreadable_path_reports_error(tmp_path: Path, validator: Draft202012Validator) -> None:
    # A directory cannot be read as text, which reaches the OSError branch and
    # reports a "cannot read file" error.
    target = tmp_path / "is-a-dir.md"
    target.mkdir()
    errors = validate_file(target, validator, require_frontmatter=True)
    assert len(errors) == 1
    assert "cannot read file" in errors[0]


def test_error_message_includes_field_path(tmp_path: Path, validator: Draft202012Validator) -> None:
    # An item-level failure must name the indexed path (tags.0), proving the
    # field-formatting in validate_file walks error.path correctly.
    meta = {**MINIMAL, "tags": ["Not Kebab"]}
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("[tags.0]" in e for e in errors)


def test_root_level_error_labelled_root(tmp_path: Path, validator: Draft202012Validator) -> None:
    meta = dict(MINIMAL)
    del meta["title"]
    errors = _check(tmp_path, validator, _doc(meta))
    assert any("[(root)]" in e and "required" in e for e in errors)


# --- validate_file x the opt-in ADR section check (DEC-5) --------------------


def test_validate_file_adr_sections_off_by_default(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    # An ADR missing Decision Outcome passes when require_adr_sections is not set:
    # the check is additive and must not change behaviour for existing callers.
    text = _adr_text(
        "## Context and Problem Statement",
        "## Considered Options",
        frontmatter=True,
    )
    path = _write(tmp_path, text)
    assert validate_file(path, validator, require_frontmatter=True) == []


def test_validate_file_adr_sections_flags_missing_when_enabled(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    text = _adr_text(
        "## Context and Problem Statement",
        "## Considered Options",
        frontmatter=True,
    )
    path = _write(tmp_path, text)
    errors = validate_file(path, validator, require_frontmatter=True, require_adr_sections=True)
    assert any("Decision Outcome" in e for e in errors)


def test_validate_file_complete_adr_passes_with_check_enabled(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    text = _adr_text(*_ALL_ADR_SECTIONS, frontmatter=True)
    path = _write(tmp_path, text)
    assert validate_file(path, validator, require_frontmatter=True, require_adr_sections=True) == []


def test_validate_file_adr_check_only_applies_to_adr_doc_type(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    # A non-ADR document (doc_type: note) lacking those headings is not an ADR;
    # the section check must skip it entirely even when enabled.
    text = _doc(MINIMAL, body="# Note\n\nProse only — no ADR sections here.\n")
    path = _write(tmp_path, text)
    assert validate_file(path, validator, require_frontmatter=True, require_adr_sections=True) == []


# ===========================================================================
# Unit — missing_adr_sections (DEC-5 ADR body-structure check)
#
# A pure helper: given a document's text, return the MADR-required level-2
# sections that are absent, in canonical order. Only the THREE truly-required
# MADR 4.0 sections are checked — Context and Problem Statement / Considered
# Options / Decision Outcome. Consequences, Confirmation, Decision Drivers,
# Pros and Cons, and More Information are OPTIONAL and must never be demanded.
# ===========================================================================

_ALL_ADR_SECTIONS = (
    "## Context and Problem Statement",
    "## Considered Options",
    "## Decision Outcome",
)


def _adr_text(*headings: str, frontmatter: bool = False) -> str:
    """Render an ADR body from the given heading lines (each with stub prose)."""
    body = "\n\n".join(f"{h}\n\nstub prose." for h in headings) + "\n"
    if frontmatter:
        return _doc({**MINIMAL, "doc_type": "adr"}, body=body)
    return f"# ADR 0001: Title\n\n{body}"


def test_missing_adr_sections_none_when_all_present() -> None:
    assert missing_adr_sections(_adr_text(*_ALL_ADR_SECTIONS)) == []


def test_missing_adr_sections_reports_absent_one() -> None:
    text = _adr_text("## Context and Problem Statement", "## Considered Options")
    assert missing_adr_sections(text) == ["Decision Outcome"]


def test_missing_adr_sections_orders_by_canonical_sequence() -> None:
    # Two missing -> reported in MADR section order, not document/discovery order.
    assert missing_adr_sections(_adr_text("## Considered Options")) == [
        "Context and Problem Statement",
        "Decision Outcome",
    ]


def test_missing_adr_sections_is_case_sensitive() -> None:
    # MADR titles are fixed strings; a lower-cased heading does not satisfy them.
    text = _adr_text(
        "## context and problem statement",
        "## Considered Options",
        "## Decision Outcome",
    )
    assert missing_adr_sections(text) == ["Context and Problem Statement"]


def test_missing_adr_sections_ignores_level_3_headings() -> None:
    # A required section must be a level-2 (`##`) heading, not a sub-heading.
    text = _adr_text(
        "## Context and Problem Statement",
        "## Considered Options",
        "### Decision Outcome",
    )
    assert missing_adr_sections(text) == ["Decision Outcome"]


def test_missing_adr_sections_ignores_optional_sections() -> None:
    # Optional MADR sections present, a required one absent: only the required one
    # is reported (optional sections are never demanded, never penalised).
    text = _adr_text(
        "## Context and Problem Statement",
        "## Decision Drivers",
        "## Considered Options",
        "## Consequences",
    )
    assert missing_adr_sections(text) == ["Decision Outcome"]


def test_missing_adr_sections_ignores_headings_in_code_fences() -> None:
    # A `## Decision Outcome` shown inside a fenced code block (e.g. a template
    # snippet) is illustrative, not the document's own section.
    text = (
        "## Context and Problem Statement\n\nx\n\n"
        "## Considered Options\n\nx\n\n"
        "```markdown\n## Decision Outcome\n```\n"
    )
    assert missing_adr_sections(text) == ["Decision Outcome"]


def test_main_missing_schema_file_returns_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--schema", "nonexistent.json", "--quiet"]) == 2


def test_main_invalid_schema_returns_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Valid JSON, but not a valid Draft 2020-12 schema (`type` must be a known type).
    bad = tmp_path / "bad.schema.json"
    bad.write_text(json.dumps({"type": "banana"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["--schema", str(bad), "--quiet"]) == 2


def test_main_no_files_matched_returns_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_main_glob_flag_collects_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def _write_adr_config(root: Path, *, require_sections: bool) -> None:
    cfg: dict[str, Any] = {
        "markdown": {
            "frontmatter": {"schema": "markdown-frontmatter", "include": ["adr.md"]},
            "adr": {"require_sections": require_sections},
        }
    }
    (root / ".project-standards.yml").write_text(
        yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8"
    )


def test_main_adr_require_sections_fails_incomplete_adr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # require_sections on + an ADR missing Decision Outcome -> exit 1.
    text = _adr_text(
        "## Context and Problem Statement",
        "## Considered Options",
        frontmatter=True,
    )
    _write(tmp_path, text, name="adr.md")
    _write_adr_config(tmp_path, require_sections=True)
    monkeypatch.chdir(tmp_path)
    assert main(["--config", ".project-standards.yml", "--quiet"]) == 1


def test_main_adr_require_sections_off_passes_incomplete_adr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Same incomplete ADR, check disabled -> exit 0 (additive default).
    text = _adr_text(
        "## Context and Problem Statement",
        "## Considered Options",
        frontmatter=True,
    )
    _write(tmp_path, text, name="adr.md")
    _write_adr_config(tmp_path, require_sections=False)
    monkeypatch.chdir(tmp_path)
    assert main(["--config", ".project-standards.yml", "--quiet"]) == 0


def test_main_adr_require_sections_passes_complete_adr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, _adr_text(*_ALL_ADR_SECTIONS, frontmatter=True), name="adr.md")
    _write_adr_config(tmp_path, require_sections=True)
    monkeypatch.chdir(tmp_path)
    assert main(["--config", ".project-standards.yml", "--quiet"]) == 0


# ===========================================================================
# Crash-safety / robustness (1.2.0)
#
# Malformed YAML must surface as a clean error + the documented exit code, never
# an uncaught traceback — a single downstream typo should not crash the tool.
# Plus: the bundled schema must resolve in the *installed wheel* layout, not only
# from a source checkout (the contract every `uv tool install` consumer relies on).
# ===========================================================================


def test_malformed_yaml_frontmatter_is_reported_not_raised(
    tmp_path: Path, validator: Draft202012Validator
) -> None:
    # An unterminated flow sequence is a YAML *syntax* error (distinct from a
    # non-mapping or absent block). It must become one clean error, not a traceback.
    content = "---\nid: [unclosed\n---\n\n# Doc\n"
    errors = _check(tmp_path, validator, content)
    assert len(errors) == 1
    assert "YAML" in errors[0]


def test_main_malformed_yaml_frontmatter_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "---\nid: [unclosed\n---\n\n# Doc\n", name="bad.md")
    monkeypatch.chdir(tmp_path)
    assert main(["bad.md", "--schema", str(SCHEMA_PATH), "--quiet"]) == 1


def test_main_malformed_config_returns_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A broken config is an operator error -> exit 2, not a crash.
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown: [unclosed\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["--config", ".project-standards.yml", "--quiet"]) == 2


def test_find_bundled_schema_resolves_from_package_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The schema ships inside the package (project_standards/schemas/). Simulate an
    # installed layout and confirm find_bundled_schema resolves <package>/schemas/.
    from project_standards import validate_frontmatter as vf

    pkg = tmp_path / "project_standards"
    (pkg / "schemas").mkdir(parents=True)
    schema = pkg / "schemas" / "markdown-frontmatter.schema.json"
    schema.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(vf, "__file__", str(pkg / "validate_frontmatter.py"))
    assert vf.find_bundled_schema("markdown-frontmatter") == schema


# ===========================================================================
# Contract / dogfood — the shipped artifacts must stay valid for consumers
# ===========================================================================

EXAMPLE_FILES = sorted(_REPO_ROOT.glob("standards/*/examples/*.md"))


def test_examples_directory_is_not_empty() -> None:
    # Guard the parametrization below: an empty glob would make the dogfood test
    # vacuously pass, hiding a missing examples/ directory.
    assert EXAMPLE_FILES, "expected worked examples under standards/*/examples/"


@pytest.mark.parametrize("example", EXAMPLE_FILES, ids=[p.name for p in EXAMPLE_FILES])
def test_shipped_example_validates(example: Path, validator: Draft202012Validator) -> None:
    assert validate_file(example, validator, require_frontmatter=True) == []


def test_bundled_schema_is_valid_draft2020() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Raises SchemaError if the shipped contract is itself malformed.
    Draft202012Validator.check_schema(schema)  # pyright: ignore[reportUnknownMemberType]


def test_registry_file_is_bundled_with_package() -> None:
    # The registry resolves relative to the package, so it ships in the wheel.
    reg_path = Path(_vf.__file__).parent / "schemas" / "registry.json"
    assert reg_path.is_file()
    # Every frontmatter version maps to a schema file that also ships.
    reg = load_registry()
    for name in reg.frontmatter_versions.values():
        assert (Path(_vf.__file__).parent / "schemas" / f"{name}.schema.json").is_file()


# ===========================================================================
# Integration — FM->ADR compatibility gate + python_tooling metadata check
# ===========================================================================

from project_standards.validate_frontmatter import frontmatter_adr_incompatibility  # noqa: E402


def _write_versioned_config(root: Path, body: str) -> Path:
    path = root / ".project-standards.yml"
    path.write_text(body, encoding="utf-8")
    return path


def test_main_unknown_frontmatter_version_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    # 2.0 is not bundled: schema resolution catches it BEFORE the compat gate, so
    # the message names the unknown version rather than a misleading compat error.
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '2.0'\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n",
    )
    rc = main(["--config", ".project-standards.yml"])
    assert rc == 2
    assert "unknown frontmatter version" in capsys.readouterr().err


def test_compat_gate_flags_known_incompatible_pair() -> None:
    # Test the gate with a KNOWN incompatible pair via a constructed registry that
    # bundles a 2.0 contract — no real 2.0 schema file needed. This proves the gate
    # itself, independent of which versions happen to ship today.
    from project_standards.registry import Registry

    reg = Registry(
        frontmatter_default="1.1",
        frontmatter_versions={"1.1": "markdown-frontmatter", "2.0": "markdown-frontmatter-2.0"},
        adr_default="1.0",
        adr_supports={"1.0": ["1.1"]},
        python_tooling_default="1.0",
        python_tooling_versions=["1.0"],
        markdown_tooling_default="1.0",
        markdown_tooling_versions=["1.0"],
    )
    cfg = _cfg(frontmatter_version="2.0", adr_version="1.0", require_adr_sections=True)
    msg = frontmatter_adr_incompatibility(cfg, reg)
    assert msg is not None
    assert "ADR 1.0 supports Frontmatter ['1.1']" in msg
    assert "configured frontmatter.version is 2.0" in msg


def test_compat_gate_ok_for_defaults() -> None:
    reg = load_registry()
    assert frontmatter_adr_incompatibility(_cfg(require_adr_sections=True), reg) is None


def test_main_compatible_combo_validates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc(MINIMAL), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '1.1'\n"
        "    include: ['doc.md']\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_main_custom_schema_bypasses_compat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # A custom schema + require_sections must not trip the FM->ADR gate.
    import shutil

    shutil.copy(SCHEMA_PATH, tmp_path / "custom.schema.json")
    (tmp_path / "doc.md").write_text(_doc(MINIMAL), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    schema: './custom.schema.json'\n"
        "    include: ['doc.md']\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_no_version_config_passes_legacy_1_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc({**MINIMAL, "schema_version": "1.0"}), encoding="utf-8")
    _write_versioned_config(tmp_path, "markdown:\n  frontmatter:\n    include: ['doc.md']\n")
    assert main(["--config", ".project-standards.yml"]) == 0


def test_no_version_config_passes_legacy_1_0_adr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    adr_meta = {**MINIMAL, "schema_version": "1.0", "doc_type": "adr"}
    body = (
        "# ADR\n\n## Context and Problem Statement\nx\n\n"
        "## Considered Options\nx\n\n## Decision Outcome\nx\n"
    )
    (tmp_path / "adr.md").write_text(_doc(adr_meta, body=body), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n  frontmatter:\n    include: ['adr.md']\n  adr:\n    require_sections: true\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_explicit_fm_version_1_1_accepts_1_0_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc({**MINIMAL, "schema_version": "1.0"}), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n  frontmatter:\n    version: '1.1'\n    include: ['doc.md']\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_python_tooling_version_emits_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc(MINIMAL), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n  frontmatter:\n    include: ['doc.md']\npython_tooling:\n  version: '1.0'\n",
    )
    rc = main(["--config", ".project-standards.yml"])
    out = capsys.readouterr()
    assert rc == 0
    assert out.out == "✓  1 file(s) validated\n"
    assert "python_tooling" not in out.out
    assert "python_tooling" not in out.err


def test_unknown_python_tooling_version_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_versioned_config(tmp_path, "python_tooling:\n  version: '9.9'\n")
    rc = main(["--config", ".project-standards.yml"])
    assert rc == 2
    assert "unknown python_tooling.version" in capsys.readouterr().err


def test_main_incompatible_combo_via_registry_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A KNOWN-but-incompatible pair: a registry that bundles FM 2.0, with ADR 1.0
    # supporting only FM 1.1. Reaches the main-level compat-gate error branch that
    # the shipped registry can't (it has no 2.0 yet). monkeypatch load_registry so
    # resolution accepts 2.0 and the gate then rejects the pair.
    from project_standards.registry import Registry

    fake = Registry(
        frontmatter_default="1.1",
        frontmatter_versions={"1.1": "markdown-frontmatter", "2.0": "markdown-frontmatter"},
        adr_default="1.0",
        adr_supports={"1.0": ["1.1"]},
        python_tooling_default="1.0",
        python_tooling_versions=["1.0"],
        markdown_tooling_default="1.0",
        markdown_tooling_versions=["1.0"],
    )
    monkeypatch.setattr(_vf, "load_registry", lambda: fake)
    monkeypatch.chdir(tmp_path)
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '2.0'\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n",
    )
    rc = main(["--config", ".project-standards.yml"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "ADR 1.0 supports Frontmatter ['1.1']" in err
    assert "configured frontmatter.version is 2.0" in err


def test_main_registry_load_failure_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _boom() -> object:
        raise RegistryError("cannot load registry /nope/registry.json: boom")

    monkeypatch.setattr(_vf, "load_registry", _boom)
    monkeypatch.chdir(tmp_path)
    _write_versioned_config(tmp_path, "markdown:\n  frontmatter:\n    required: true\n")
    rc = main(["--config", ".project-standards.yml"])
    assert rc == 2
    assert "cannot load registry" in capsys.readouterr().err


def test_registry_exposes_markdown_tooling() -> None:
    reg = load_registry()
    assert reg.markdown_tooling_default == "1.0"
    assert reg.is_known_markdown_tooling("1.0") is True
    assert reg.is_known_markdown_tooling("9.9") is False


def test_load_registry_requires_markdown_tooling(tmp_path: Path) -> None:
    bad = tmp_path / "registry.json"
    bad.write_text(
        '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}},'
        ' "adr": {"default": "1.0", "versions": {"1.0": {"supports_frontmatter": ["1.1"]}}},'
        ' "python_tooling": {"default": "1.0", "versions": ["1.0"]}}',
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="markdown_tooling"):
        load_registry(bad)
