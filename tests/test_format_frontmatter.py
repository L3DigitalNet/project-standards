import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import project_standards.format_frontmatter as format_frontmatter
from project_standards.format_frontmatter import (
    Entry,
    _leading_run,  # pyright: ignore[reportPrivateUsage]
    _split_value_comment,  # pyright: ignore[reportPrivateUsage]
    _today_iso,  # pyright: ignore[reportPrivateUsage]
    format_text,
    main,
    tokenize,
)
from project_standards.validate_frontmatter import ConfigError

CLEAN = (
    "---\n"
    "schema_version: '1.1'\n"
    "id: 'note-a3f9zk-x'\n"
    "title: 'X'\n"
    "description: 'A doc.'\n"
    "doc_type: 'note'\n"
    "status: 'draft'\n"
    "created: '2026-06-08'\n"
    "updated: '2026-06-08'\n"
    "tags: []\n"
    "aliases: []\n"
    "related: []\n"
    "---\n"
    "# Body\n"
)


def _clear_schema_enum_cache() -> None:
    loader = getattr(format_frontmatter, "_valid_doc_types", None)
    if loader is not None:
        loader.cache_clear()


@pytest.mark.parametrize("schema_state", ["missing", "corrupt", "invalid_utf8"])
def test_help__broken_schema__remains_available(
    tmp_path: Path,
    schema_state: str,
) -> None:
    isolated_src = tmp_path / "src"
    package = isolated_src / "project_standards"
    shutil.copytree(Path(__file__).parents[1] / "src" / "project_standards", package)
    schema = package / "schemas" / "markdown-frontmatter.schema.json"
    if schema_state == "missing":
        schema.unlink()
    elif schema_state == "corrupt":
        schema.write_text("{", encoding="utf-8")
    else:
        schema.write_bytes(b"\xff")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(isolated_src)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import project_standards.frontmatter_authoring\n"
            "from project_standards.format_frontmatter import main\n"
            "main(['--help'])\n",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage: format-frontmatter" in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("schema_state", ["missing", "corrupt", "invalid_utf8"])
def test_format_text__broken_schema__raises_config_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    schema_state: str,
) -> None:
    schema = tmp_path / "markdown-frontmatter.schema.json"
    if schema_state == "corrupt":
        schema.write_text("{", encoding="utf-8")
    elif schema_state == "invalid_utf8":
        schema.write_bytes(b"\xff")
    _clear_schema_enum_cache()
    monkeypatch.setattr(format_frontmatter, "_SCHEMA_PATH", schema)
    source = CLEAN.replace("doc_type: 'note'", "doc_type: 'invalid'")

    try:
        with pytest.raises(ConfigError, match="cannot load doc_type enum"):
            format_text(source, path=Path("docs/research/example.md"))
    finally:
        _clear_schema_enum_cache()


def test_format_text__schema_read__uses_explicit_utf8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encodings: list[str | None] = []

    class SchemaText:
        def read_text(self, *, encoding: str | None = None) -> str:
            encodings.append(encoding)
            return '{"properties": {"doc_type": {"enum": ["note", "research"]}}}'

    _clear_schema_enum_cache()
    monkeypatch.setattr(format_frontmatter, "_SCHEMA_PATH", SchemaText())
    source = CLEAN.replace("doc_type: 'note'", "doc_type: 'invalid'")

    try:
        new, changed, warnings = format_text(
            source,
            path=Path("docs/research/example.md"),
        )
    finally:
        _clear_schema_enum_cache()

    assert changed is True
    assert warnings == []
    assert "doc_type: 'research'" in new
    assert encodings == ["utf-8"]


def test_clean_input_is_byte_identical() -> None:
    # format_text returns (new_text, changed, warnings). Already-canonical -> no change.
    new, changed, _warnings = format_text(CLEAN, path=None)
    assert new == CLEAN
    assert changed is False


def test_no_frontmatter_is_noop() -> None:
    body = "# Just a body\n\nNo frontmatter here.\n"
    new, changed, _warnings = format_text(body, path=None)
    assert new == body
    assert changed is False


def test_comment_block_preserved_on_roundtrip() -> None:
    src = CLEAN.replace("id: 'note-a3f9zk-x'\n", "id: 'note-a3f9zk-x'  # frozen at creation\n")
    new, changed, _warnings = format_text(src, path=None)
    assert "# frozen at creation" in new
    assert changed is False


def test_duplicate_top_level_key_is_refused() -> None:
    # PyYAML silently keeps the last duplicate; the formatter must NOT rewrite such a
    # block (it would erase the human-visible conflict). It skips with a warning. (CR-002)
    src = CLEAN.replace("tags: []\n", "tags: []\ntags: ['x']\n")
    new, changed, warnings = format_text(src, path=None)
    assert new == src
    assert changed is False
    assert any("duplicate" in w for w in warnings)


def test_reorder_to_canonical_order() -> None:
    src = (
        "---\n"
        "title: 'X'\n"
        "schema_version: '1.1'\n"
        "doc_type: 'note'\n"
        "id: 'note-a3f9zk-x'\n"
        "description: 'A doc.'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
    new, changed, _ = format_text(src, path=None)
    keys = [ln.split(":")[0] for ln in new.splitlines() if ln and not ln.startswith("-")]
    assert keys[:4] == ["schema_version", "id", "title", "description"]
    assert changed is True


def test_unknown_key_sorts_after_known_keys() -> None:
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "custom_thing: 'x'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
    new, _, warnings = format_text(src, path=None)
    lines = [ln for ln in new.splitlines() if ":" in ln]
    assert lines.index("custom_thing: 'x'") > lines.index("related: []")
    assert any("custom_thing" in w for w in warnings)


def _doc(*, title: str = "X", extra: str = "", tags_line: str = "tags: []") -> str:
    # tags_line lets a test vary the tags entry WITHOUT appending a second `tags:`
    # (which would create a duplicate key the formatter now refuses — CR-002).
    return (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        f"title: {title}\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        f"{tags_line}\n"
        "aliases: []\n"
        "related: []\n"
        f"{extra}"
        "---\n"
    )


def test_unquoted_scalars_get_single_quoted() -> None:
    src = (
        "---\n"
        "schema_version: 1.1\n"  # identifier-like number -> '1.1'
        "id: 'note-a3f9zk-x'\n"
        "title: X\n"  # bare string -> 'X'
        "description: A doc.\n"
        "doc_type: note\n"
        "status: draft\n"
        "created: 2026-06-08\n"  # unquoted date -> '2026-06-08'
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
    new, changed, _ = format_text(src, path=None)
    assert "schema_version: '1.1'" in new
    assert "title: 'X'" in new
    assert "created: '2026-06-08'" in new
    assert "doc_type: 'note'" in new
    assert changed is True


def test_null_license_stays_null() -> None:
    src = _doc(extra="license: null\n")  # helper defined below
    new, _, _ = format_text(src, path=None)
    assert "license: null" in new
    assert "license: 'null'" not in new


def test_escape_free_double_quoted_still_normalizes_to_single() -> None:
    # TC-T1-003: FR-008 narrows the old "double always becomes single" rule to
    # escape-free input. `"Hello"` has no apostrophe, so single and double cost the
    # same; the tie resolves to single. (Apostrophe-bearing double-quoted scalars are
    # now preserved — see test_minimal_double_quoted_scalar_is_preserved.)
    src = _doc(title='"Hello"')
    new, _, _ = format_text(src, path=None)
    assert "title: 'Hello'" in new


@pytest.mark.parametrize("token", ["on", "off", "Yes", "No"])
def test_boolean_like_scalar_kept_as_string(token: str) -> None:
    # `title: on` must become `title: 'on'`, NOT 'true' (CR-NEW-001).
    src = _doc(title=token)
    new, _, _ = format_text(src, path=None)
    assert f"title: '{token}'" in new


def test_hash_in_plain_scalar_is_not_a_comment() -> None:
    # `C#` has no whitespace before '#', so it is scalar content, not a comment (CR-NEW-003).
    src = _doc(title="C# guide")
    new, _, _ = format_text(src, path=None)
    assert "title: 'C# guide'" in new


def test_url_fragment_preserved() -> None:
    src = _doc(title="http://example.com/p#frag")
    new, _, _ = format_text(src, path=None)
    assert "title: 'http://example.com/p#frag'" in new


def test_real_inline_comment_preserved_on_scalar() -> None:
    src = _doc(title="X  # keep me")  # whitespace + '#' IS a real comment
    new, _, _ = format_text(src, path=None)
    assert "title: 'X'  # keep me" in new


def test_flow_list_becomes_block_and_dedupes() -> None:
    src = _doc(tags_line="tags: ['a', 'b', 'a']")
    new, changed, _ = format_text(src, path=None)
    assert "tags:\n  - 'a'\n  - 'b'\n" in new
    assert new.count("- 'a'") == 1
    assert changed is True


def test_empty_block_list_becomes_flow_empty() -> None:
    src = _doc(tags_line="tags:")  # key with no value and no items -> tags: []
    new, _, _ = format_text(src, path=None)
    assert "tags: []" in new


def test_boolean_like_list_items_kept_as_strings() -> None:
    # list items must not be coerced (BaseLoader); [on, off, yes, no] stay strings (CR-NEW-001).
    src = _doc(tags_line="tags: [on, off, yes, no]")
    new, _, _ = format_text(src, path=None)
    assert "- 'on'" in new and "- 'off'" in new and "- 'yes'" in new and "- 'no'" in new
    assert "True" not in new and "False" not in new


def test_block_list_as_last_field_no_trailing_blank_line() -> None:
    # When a non-empty block list is the LAST frontmatter field, the formatter must not
    # insert a blank line before the closing fence (item_eol would force '\n' on the last
    # item whose newline the close fence already owns). Byte-identical + idempotent.
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related:\n"
        "  - 'CHANGELOG.md'\n"
        "  - 'meta/versioning.md'\n"
        "---\n"
        "# Body\n"
    )
    new, changed, _warnings = format_text(src, path=None)
    assert "'meta/versioning.md'\n---\n" in new  # last item then close fence, no blank
    assert "\n\n---\n" not in new  # no blank line before the closing fence
    assert changed is False  # already canonical -> byte-identical
    twice, changed2, _ = format_text(new, path=None)
    assert twice == new and changed2 is False  # idempotent


def test_inline_comment_preserved_on_flow_list() -> None:
    src = _doc(tags_line="tags: [a, b]  # keep")  # CR-NEW-004
    new, _, _ = format_text(src, path=None)
    assert "tags:  # keep" in new  # comment moves to the block key line
    assert "- 'a'" in new and "- 'b'" in new


def test_inline_comment_preserved_on_empty_list() -> None:
    src = _doc(tags_line="tags: []  # keep")  # CR-NEW-004
    new, _, _ = format_text(src, path=None)
    assert "tags: []  # keep" in new


def test_hash_inside_quoted_list_item_not_a_comment() -> None:
    src = _doc(extra="source: ['Issue #123']\n")  # CR-NEW-005: '#' inside quote is literal
    new, _, _ = format_text(src, path=Path("docs/x.md"))
    assert "- 'Issue #123'" in new  # whole item preserved, '#' kept
    assert "source: []" not in new  # not emptied / mis-split


def test_real_comment_after_quoted_list_item_preserved() -> None:
    src = _doc(extra="source: ['Issue #123']  # keep\n")  # CR-NEW-005
    new, _, _ = format_text(src, path=Path("docs/x.md"))
    assert "- 'Issue #123'" in new
    assert "source:  # keep" in new


def test_type_renamed_to_doc_type_when_absent() -> None:
    src = _doc().replace("doc_type: 'note'\n", "type: 'note'\n")
    new, changed, _ = format_text(src, path=None)
    assert "doc_type: 'note'" in new
    assert "\ntype:" not in new
    assert changed is True


def test_both_type_and_doc_type_present_warns_keeps_both() -> None:
    src = _doc(extra="type: 'x'\n")
    new, _, warnings = format_text(src, path=None)
    assert "doc_type: 'note'" in new
    assert any("type" in w.lower() for w in warnings)


def test_missing_required_arrays_injected() -> None:
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "---\n"
    )
    new, changed, _ = format_text(src, path=None)
    assert "tags: []" in new and "aliases: []" in new and "related: []" in new
    assert changed is True


def test_schema_version_injected_when_missing() -> None:
    src = _doc().replace("schema_version: '1.1'\n", "")
    new, _, _ = format_text(src, path=None)
    assert "schema_version: '1.1'" in new


def test_doc_type_filled_from_readme_path_when_missing() -> None:
    src = _doc().replace("doc_type: 'note'\n", "")  # no doc_type
    new, _, _ = format_text(src, path=Path("README.md"))
    assert "doc_type: 'index'" in new


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(Path("docs/research/x.md"), id="root"),
        pytest.param(Path("project/docs/research/x.md"), id="nested"),
    ],
)
def test_doc_type_research_under_docs_research_when_invalid(path: Path) -> None:
    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'bogus'\n")
    new, _, _ = format_text(src, path=path)
    assert "doc_type: 'research'" in new


def test_doc_type_research_rule_rejects_prefix_lookalike() -> None:
    src = _doc().replace("doc_type: 'note'\n", "")

    new, _, _ = format_text(src, path=Path("old-docs/research/n.md"))

    assert "doc_type: 'research'" not in new


def test_valid_doc_type_never_overridden_by_path() -> None:
    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'reference'\n")
    new, _, _ = format_text(src, path=Path("README.md"))
    assert "doc_type: 'reference'" in new  # SA-001: valid value preserved
    assert "doc_type: 'index'" not in new


def test_denylisted_paths_are_refused() -> None:
    from project_standards.format_frontmatter import is_denylisted

    assert is_denylisted(Path("CLAUDE.md"))
    assert is_denylisted(Path("sub/AGENTS.md"))
    assert is_denylisted(Path(".claude/settings.md"))
    assert is_denylisted(Path("x/.codex/y.md"))
    assert not is_denylisted(Path("docs/note.md"))


def test_extension_object_nested_bytes_preserved() -> None:
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "project:\n"
        "  team: 'platform'\n"
        "  nested:\n"
        "    deep: 1\n"
        "---\n"
    )
    new, changed, warnings = format_text(src, path=None)
    assert "project:\n  team: 'platform'\n  nested:\n    deep: 1\n" in new
    assert changed is False
    assert warnings == []


def test_crlf_line_endings_preserved() -> None:
    src = _doc().replace("\n", "\r\n")
    src = src.replace("title: X\r\n", "title: X\r\n") if "title: X" in src else src
    # Force one change (unquoted) and assert CRLF survives on unchanged lines.
    src = src.replace("title: 'X'\r\n", "title: X\r\n")
    new, _changed, _ = format_text(src, path=None)
    assert "\r\n" in new
    assert "\n\n" not in new.replace("\r\n", "")  # no stray bare LFs introduced
    assert "title: 'X'\r\n" in new


def test_scaffold_injects_schema_valid_block() -> None:
    body = "# Real Title\n\nSome content.\n"
    new, changed, _ = format_text(
        body, path=Path("docs/guide.md"), scaffold=True, today="2026-06-08"
    )
    assert new.startswith("---\n")
    assert "title: 'Real Title'" in new
    assert "doc_type: 'note'" in new  # no path rule -> note
    assert "created: '2026-06-08'" in new and "updated: '2026-06-08'" in new
    assert "description: 'TODO:" in new  # placeholder, schema-valid
    assert "# Real Title" in new  # body preserved
    assert changed is True


def test_scaffold_disabled_leaves_body_untouched() -> None:
    body = "# Title\n\nContent.\n"
    new, changed, _ = format_text(body, path=Path("docs/guide.md"), scaffold=False)
    assert new == body and changed is False


def test_scaffold_uses_path_doc_type_rule() -> None:
    new, _, _ = format_text("# R\n", path=Path("README.md"), scaffold=True, today="2026-06-08")
    assert "doc_type: 'index'" in new


def _run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "project_standards.format_frontmatter", *args],
        capture_output=True,
        text=True,
        **kw,  # type: ignore[call-overload]
    )


def test_check_exits_1_when_would_change(tmp_path: Path) -> None:
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 1


def test_write_formats_in_place_atomically(tmp_path: Path) -> None:
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    r = _run(["--write", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 0
    assert "title: 'X'" in f.read_text()


def test_stdin_mode_round_trips() -> None:
    r = _run(["--stdin"], input=_doc(title="X").replace("title: 'X'", "title: X"))
    assert r.returncode == 0
    assert "title: 'X'" in r.stdout


def test_custom_schema_skips(tmp_path: Path) -> None:
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['*.md']\n"
    )
    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 0
    assert "custom schema" in (r.stdout + r.stderr).lower()


@pytest.mark.parametrize("conflict", [["x.md"], ["--glob", "*.md"], ["--write"]])
def test_stdin_conflicts_exit_2(conflict: list[str]) -> None:
    r = _run(["--stdin", *conflict], input="---\ntitle: 'X'\n---\n")
    assert r.returncode == 2
    assert "stdin" in (r.stdout + r.stderr).lower()


CASES = [
    _doc(title="X").replace("title: 'X'", "title: X"),
    _doc(tags_line="tags: ['b','a','b']"),
    _doc().replace("schema_version: '1.1'\n", ""),
    _doc().replace("doc_type: 'note'\n", "type: 'note'\n"),
]


@pytest.mark.parametrize("src", CASES)
def test_format_is_idempotent(src: str) -> None:
    once, _, _ = format_text(src, path=Path("docs/x.md"))
    twice, changed2, _ = format_text(once, path=Path("docs/x.md"))
    assert twice == once
    assert changed2 is False


# ---------------------------------------------------------------------------
# In-process unit tests for tokenize() / _split_value_comment / _leading_run
# ---------------------------------------------------------------------------


def test_tokenize_blank_and_comment_lines_become_pending() -> None:
    # Covers lines 97-100 (blank/comment append to pending) and 126-127
    # (pending flushed as a trailing key=None Entry at end).
    body = "# top comment\n\ntitle: 'X'\n# tail\n"
    entries, reason = tokenize(body)
    assert reason is None
    # first entry should carry the leading comment and blank
    assert entries[0].key == "title"
    assert any("# top comment" in ln for ln in entries[0].lines)
    # trailing comment entry
    last = entries[-1]
    assert last.key is None
    assert any("# tail" in ln for ln in last.lines)


def test_tokenize_unrecognized_line_returns_reason() -> None:
    # Covers line 103 — a line at column 0 that doesn't match key: syntax
    # (e.g. a bare list item `- x` or a number-prefixed key)
    body = "- orphan-list-item\n"
    entries, reason = tokenize(body)
    assert entries == []
    assert reason is not None and "unrecognized" in reason


def test_tokenize_unsupported_yaml_constructs() -> None:
    # Covers line 107 — anchor, alias, block scalar
    for bad_val in ("&anchor value", "*alias", "<< merge", "| block"):
        body = f"title: {bad_val}\n"
        entries, reason = tokenize(body)
        assert entries == [], f"expected empty for {bad_val!r}"
        assert reason is not None and "unsupported" in reason, f"bad reason for {bad_val!r}"


@pytest.mark.parametrize(
    "fragment",
    [
        pytest.param("project:\n  &team team: platform\n", id="mapping-key"),
        pytest.param("project:\n  team: &team platform\n", id="mapping-value"),
        pytest.param("source: [&source guide, *source]\n", id="flow-list"),
        pytest.param(
            "source:\n  - &source guide\n  - *source\n",
            id="block-list",
        ),
    ],
)
def test_anchor_or_alias_anywhere_in_frontmatter_warns_and_preserves_bytes(
    fragment: str,
) -> None:
    src = _doc(extra=fragment)

    new, changed, warnings = format_text(src, path=Path("docs/example.md"))

    assert new == src
    assert changed is False
    assert any("skipped (unsupported frontmatter)" in warning for warning in warnings)


def test_tokenize_blank_line_breaks_continuation() -> None:
    # Covers line 119 — blank line inside a nested entry ends continuation
    body = "tags:\n  - 'a'\n\ntitle: 'X'\n"
    entries, reason = tokenize(body)
    assert reason is None
    tag_entry = next(e for e in entries if e.key == "tags")
    # blank line is NOT included in the tag entry's lines (it ends it)
    assert not any(ln.strip() == "" for ln in tag_entry.lines)


def test_split_value_comment_single_quoted_with_escaped_quote() -> None:
    # Covers lines 154-155 — escaped '' inside single-quoted scalar
    val, comment = _split_value_comment(" 'it''s here'  # note")
    assert val.strip() == "'it''s here'"
    assert "# note" in comment


def test_split_value_comment_double_quoted_with_escape() -> None:
    # Covers lines 158-159 — backslash escape inside double-quoted scalar
    val, comment = _split_value_comment(' "foo\\"bar"  # cmt')
    assert val.strip().startswith('"')
    assert "# cmt" in comment


def test_split_value_comment_unterminated_single_quote() -> None:
    # Covers line 163 — unterminated quote: whole rest returned as value
    val, comment = _split_value_comment(" 'unterminated")
    assert comment == ""
    assert "unterminated" in val


def test_split_value_comment_flow_list_with_inner_double_quote() -> None:
    # Covers lines 173-174 and 177-178 — quote tracking inside flow list
    val, comment = _split_value_comment(' ["foo\\"bar", \'baz\']  # keep')
    assert val.strip().startswith("[")
    assert "]" in val
    assert "# keep" in comment


def test_split_value_comment_flow_list_inner_single_quote_double_escape() -> None:
    # Covers line 175-176 — '' escape inside single-quoted flow list item
    val, comment = _split_value_comment(" ['it''s']")
    assert val.strip() == "['it''s']"
    assert comment == ""


def test_split_value_comment_unbalanced_brackets() -> None:
    # Covers line 191 — unbalanced brackets: no comment extracted
    _val, comment = _split_value_comment(" [open but no close")
    assert comment == ""


def test_leading_run_counts_only_prefix_blanks_and_comments() -> None:
    # Covers lines 256-262 — _leading_run returns count of leading blank/comment lines
    entry = Entry(key="tags", lines=["# comment\n", "\n", "tags:\n", "  - 'a'\n"])
    assert _leading_run(entry) == 2


def test_normalize_lists_yaml_error_is_skipped() -> None:
    # Covers lines 276-277 — yaml.YAMLError during load → continue (no crash)
    # Build an entry whose lines produce invalid YAML when joined
    entry = Entry(key="tags", lines=["tags: [\n", "  broken yaml\n"])
    from project_standards.format_frontmatter import normalize_lists

    normalize_lists([entry])  # must not raise
    # lines unchanged (skipped)
    assert entry.lines[0] == "tags: [\n"


def test_normalize_lists_non_dict_load_skipped() -> None:
    # The joined entry lines parse as a YAML list, not a mapping -> `not isinstance(
    # loaded, dict)` is True and the entry is left untouched. Defensive guard: tokenize
    # only ever builds `key:` entries, so this cannot arise in production; assert it via
    # a direct Entry construction so the guard's contract is locked.
    entry = Entry(key="tags", lines=["- list-item\n"])
    from project_standards.format_frontmatter import normalize_lists

    normalize_lists([entry])
    assert entry.lines == ["- list-item\n"]  # unchanged (non-dict load skipped)


def test_normalize_lists_scalar_where_list_expected_is_left() -> None:
    # Covers line 282 — value is a scalar (not list/None/empty) -> left for validator
    entry = Entry(key="tags", lines=["tags: not-a-list\n"])
    from project_standards.format_frontmatter import normalize_lists

    normalize_lists([entry])
    assert "not-a-list" in entry.lines[0]


def test_reorder_trailing_comment_entry_stays_last() -> None:
    # Covers line 330 — trailing comment-only Entry (key=None) sort key
    from project_standards.format_frontmatter import reorder

    e_title = Entry(key="title", lines=["title: 'X'\n"])
    e_tail = Entry(key=None, lines=["# trailing\n"])
    warnings: list[str] = []
    result = reorder([e_tail, e_title], warnings)
    assert result[-1].key is None


def test_today_iso_returns_valid_date() -> None:
    # Covers line 444 — _today_iso() returns today's ISO date string
    import datetime as _dt

    result = _today_iso()
    parsed = _dt.date.fromisoformat(result)
    assert parsed == _dt.date.today()


def test_scaffold_no_path_is_noop() -> None:
    # Covers line 485 — scaffold=True but path=None -> returns text unchanged
    body = "# Title\n\nContent.\n"
    new, changed, _ = format_text(body, path=None, scaffold=True)
    assert new == body
    assert changed is False


def test_bump_updated_sets_new_date() -> None:
    # Covers lines 512-519 — bump_updated rewrites updated: when block changes
    src = _doc(title="X").replace("title: 'X'", "title: X")  # unquoted -> will change
    new, changed, _ = format_text(src, path=None, bump_updated=True, today="2099-01-01")
    assert changed is True
    assert "updated: '2099-01-01'" in new


def test_bump_updated_noop_when_already_formatted() -> None:
    # bump_updated only fires when the block actually changes; clean input -> no change
    new, changed, _ = format_text(CLEAN, path=None, bump_updated=True, today="2099-01-01")
    assert changed is False
    assert "updated: '2099-01-01'" not in new


def test_bump_updated_with_leading_comment_on_updated_field() -> None:
    # Regression: bump_updated previously guarded `len(entry.lines) == 1`, skipping an
    # `updated:` entry that has a leading comment (len > 1). It must rewrite the date
    # AND preserve the comment intact (fix A from round-3 review).
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: X\n"  # unquoted -> will trigger a change
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "# last reviewed date\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
    new, changed, _ = format_text(src, path=None, bump_updated=True, today="2026-06-09")
    assert changed is True
    # The comment must survive
    assert "# last reviewed date" in new
    # The date must be updated
    assert "updated: '2026-06-09'" in new


# ---------------------------------------------------------------------------
# In-process main() tests — CLI coverage
# ---------------------------------------------------------------------------


def _cfg(tmp_path: Path, *, include: str = "['**/*.md']", extra: str = "") -> Path:
    """Write a minimal .project-standards.yml and return its path."""
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(f"markdown:\n  frontmatter:\n    include: {include}\n{extra}")
    return cfg


@pytest.mark.parametrize("schema_state", ["missing", "corrupt", "invalid_utf8"])
def test_main_check__broken_schema__reports_clean_config_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    schema_state: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    document = tmp_path / "docs" / "research" / "example.md"
    document.parent.mkdir(parents=True)
    document.write_text(
        CLEAN.replace("doc_type: 'note'", "doc_type: 'invalid'"),
        encoding="utf-8",
    )
    config = _cfg(tmp_path)
    schema = tmp_path / "broken.schema.json"
    if schema_state == "corrupt":
        schema.write_text("{", encoding="utf-8")
    elif schema_state == "invalid_utf8":
        schema.write_bytes(b"\xff")
    _clear_schema_enum_cache()
    monkeypatch.setattr(
        format_frontmatter,
        "_SCHEMA_PATH",
        schema,
    )

    try:
        result = main(["--check", "--config", str(config), str(document)])
    finally:
        _clear_schema_enum_cache()

    captured = capsys.readouterr()
    assert result == 2
    assert "error: cannot load doc_type enum" in captured.err
    assert "Traceback" not in captured.err


def test_main_check_exits_1_when_file_would_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--config", str(cfg), str(f)])
    assert rc == 1


def test_main_check_exits_0_when_already_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "clean.md"
    f.write_text(CLEAN)
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--config", str(cfg), str(f)])
    assert rc == 0


def test_main_write_rewrites_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    assert "title: 'X'" in f.read_text()


def test_main_write_preserves_file_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Exercises _atomic_write: set a non-default mode, assert it survives the rewrite
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    f.chmod(0o644)
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    mode = f.stat().st_mode & 0o777
    assert mode == 0o644


def test_main_write_preserves_executable_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A non-default mode (0o755) must survive the atomic rewrite
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    f.chmod(0o755)
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    assert (f.stat().st_mode & 0o777) == 0o755


def test_main_stdin_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    src = _doc(title="X").replace("title: 'X'", "title: X")
    monkeypatch.setattr("sys.stdin", io.StringIO(src))
    cfg = _cfg(tmp_path)
    rc = main(["--stdin", "--config", str(cfg)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "title: 'X'" in out


def test_main_stdin_with_file_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
    with pytest.raises(SystemExit) as exc:
        main(["--stdin", "x.md"])
    assert exc.value.code == 2


def test_main_stdin_with_glob_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
    with pytest.raises(SystemExit) as exc:
        main(["--stdin", "--glob", "*.md"])
    assert exc.value.code == 2


def test_main_stdin_with_write_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
    with pytest.raises(SystemExit) as exc:
        main(["--stdin", "--write"])
    assert exc.value.code == 2


def test_main_custom_schema_via_config_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(
        tmp_path,
        extra="",
    )
    # Write config with a custom schema path
    cfg.write_text(
        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['**/*.md']\n"
    )
    rc = main(["--check", "--config", str(cfg), str(f)])
    assert rc == 0
    out, err = capsys.readouterr()
    assert "custom schema" in (out + err).lower()


def test_main_custom_schema_via_flag_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    # Pass a --schema flag pointing to a non-existent custom path
    rc = main(["--check", "--config", str(cfg), "--schema", "custom/x.json", str(f)])
    assert rc == 0
    out, err = capsys.readouterr()
    assert "custom schema" in (out + err).lower()


def test_main_typo_config_path_exits_2_not_silent_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A typo'd --config must fail loudly, not silently fall back to defaults and write."""
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    rc = main(["--write", "--config", str(tmp_path / "no-such-config.yml"), str(f)])
    assert rc == 2
    _out, err = capsys.readouterr()
    assert "config file not found" in err.lower()
    assert f.read_text() == _doc(title="X").replace("title: 'X'", "title: X")


def test_main_non_utf8_file_reports_error_not_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_bytes(b"\xff\xfe garbage not utf-8 \x00\x81")
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--config", str(cfg), str(f)])
    assert rc == 1
    _out, err = capsys.readouterr()
    assert "cannot read" in err.lower()


def test_main_write_refuses_a_leaf_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path / "outside.md"
    original = _doc(title="X").replace("title: 'X'", "title: X")
    outside.write_text(original)
    link = tmp_path / "doc.md"
    link.symlink_to(outside)
    cfg = _cfg(tmp_path)

    rc = main(["--write", "--config", str(cfg), str(link)])

    assert rc == 2
    assert outside.read_text() == original
    assert "not a regular file" in capsys.readouterr().err


def test_main_malformed_config_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".project-standards.yml"
    # Invalid YAML: tab character at start of line where not allowed
    cfg.write_text("markdown:\n\t frontmatter: bad\n")
    rc = main(["--check", "--config", str(cfg)])
    assert rc == 2
    _out, err = capsys.readouterr()
    assert "error" in err.lower()


def test_main_denylisted_file_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # CLAUDE.md with a frontmatter block that would be changed if processed
    f = tmp_path / "CLAUDE.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    # Pass the denylist file explicitly as a positional arg
    rc = main(["--check", "--config", str(cfg), str(f)])
    # denylisted -> skipped -> no change detected -> 0
    assert rc == 0


def test_main_duplicate_key_warning_sets_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    # Frontmatter with a duplicate key: tokenize returns reason "duplicate top-level key"
    src = CLEAN.replace("tags: []\n", "tags: []\ntags: ['x']\n")
    f = tmp_path / "dup.md"
    f.write_text(src)
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--config", str(cfg), str(f)])
    _out, err = capsys.readouterr()
    assert "duplicate" in err.lower()
    # unparseable flag set -> returns 1 regardless of any_change
    assert rc == 1


def test_main_bump_updated_with_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # File with unquoted title so it will change; existing updated date in the past
    f = tmp_path / "d.md"
    old_content = _doc(title="X").replace("title: 'X'", "title: X")
    # Replace the updated date with an obviously old value
    old_content = old_content.replace("updated: '2026-06-08'", "updated: '2020-01-01'")
    f.write_text(old_content)
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--bump-updated", "--config", str(cfg), str(f)])
    assert rc == 0
    new_content = f.read_text()
    # updated: must have changed from the old placeholder
    assert "updated: '2020-01-01'" not in new_content
    assert "updated:" in new_content


def test_main_write_scaffold_on_no_frontmatter_docs_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # A .md file under docs/ with no frontmatter: --write triggers scaffold
    docs = tmp_path / "docs"
    docs.mkdir()
    f = docs / "guide.md"
    f.write_text("# Guide Title\n\nSome content.\n")
    cfg = _cfg(tmp_path, include="['docs/**/*.md']")
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    content = f.read_text()
    assert content.startswith("---\n")
    assert "title: 'Guide Title'" in content
    assert "doc_type: 'note'" in content


def test_main_write_quiet_suppresses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--quiet", "--config", str(cfg), str(f)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert out == ""


def test_main_check_quiet_suppresses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--quiet", "--config", str(cfg), str(f)])
    assert rc == 1
    out, _ = capsys.readouterr()
    assert out == ""


def test_malformed_double_quoted_scalar_does_not_crash() -> None:
    # An invalid double-quoted YAML escape must NOT crash the formatter (codex P3) —
    # it can't safely re-quote, so it leaves the line for the validator to reject.
    src = _doc(title='"bad \\q"')
    new, _changed, _warnings = format_text(src, path=None)
    assert 'title: "bad \\q"' in new  # line preserved, no traceback


def test_scalar_with_leading_comment_is_requoted() -> None:
    # A leading comment bundles into the key's entry; requote must still quote the
    # scalar (codex P2) rather than skip the whole entry as a multi-line value.
    src = _doc(title="X").replace("title: X", "# keep this note\ntitle: X")
    new, _changed, _warnings = format_text(src, path=None)
    assert "# keep this note" in new
    assert "title: 'X'" in new


def test_block_list_item_comment_is_preserved() -> None:
    # Re-rendering a block list would drop per-item comments (codex P2); a comment-
    # bearing list is left untouched so the authored note survives.
    src = _doc(tags_line="tags:\n  - 'a'  # why a\n  - 'b'")
    new, _changed, _warnings = format_text(src, path=None)
    assert "# why a" in new
    assert "- 'a'" in new and "- 'b'" in new


def test_valid_commented_doc_type_not_overridden_by_path() -> None:
    # SA-001: a VALID doc_type carrying an inline comment must be parsed correctly and
    # kept, not misread as invalid and overwritten by the path rule (codex round-2 P2).
    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'reference'  # intentional\n")
    new, _changed, _warnings = format_text(src, path=Path("README.md"))
    assert "doc_type: 'reference'" in new
    assert "# intentional" in new
    assert "doc_type: 'index'" not in new


def test_rename_type_preserves_leading_comment() -> None:
    # type->doc_type rename must rewrite only the key line, not a leading
    # `# type: ...` comment (codex round-2 P3).
    src = _doc().replace("doc_type: 'note'\n", "# type: legacy alias\ntype: 'note'\n")
    new, _changed, _warnings = format_text(src, path=None)
    assert "doc_type: 'note'" in new
    assert "# type: legacy alias" in new
    assert "# doc_type: legacy alias" not in new


def test_stdin_fails_on_duplicate_keys() -> None:
    # stdin mode must mirror file mode: duplicate top-level keys -> non-zero exit
    # (codex round-2 P2 — it previously discarded warnings and always exited 0).
    dup = _doc().replace("tags: []\n", "tags: []\ntags: ['x']\n")
    r = _run(["--stdin"], input=dup)
    assert r.returncode == 1
    assert "duplicate" in (r.stdout + r.stderr).lower()


# ---------------------------------------------------------------------------
# Helper edge cases: nested brackets, key mismatch, comment-only entries
# ---------------------------------------------------------------------------


def test_split_value_comment_nested_brackets() -> None:
    value, comment = _split_value_comment("[['a'], 'b']  # keep")
    assert value == "[['a'], 'b']"
    assert comment == "  # keep"


def test_requote_scalar_line_other_key_left_alone() -> None:
    from project_standards.format_frontmatter import (
        _requote_scalar_line,  # pyright: ignore[reportPrivateUsage]
    )

    assert _requote_scalar_line("status: draft\n", "title") == "status: draft\n"


def test_leading_run_counts_comment_only_entry() -> None:
    entry = Entry(key=None, lines=["# trailing comment\n", "\n"])
    assert _leading_run(entry) == 2


def test_block_list_item_comment_ignores_non_item_lines() -> None:
    from project_standards.format_frontmatter import (
        _block_list_has_item_comment,  # pyright: ignore[reportPrivateUsage]
    )

    assert _block_list_has_item_comment(["tags:\n", "  not-an-item\n", "  - 'a'\n"]) is False


def test_requote_skips_keyless_entry() -> None:
    from project_standards.format_frontmatter import requote

    entry = Entry(key=None, lines=["# only a comment\n"])
    requote([entry])
    assert entry.lines == ["# only a comment\n"]


# ---------------------------------------------------------------------------
# format_text: denylist refusal, block-scalar updated under --bump-updated
# ---------------------------------------------------------------------------


def test_format_text_refuses_denylisted_path() -> None:
    new, changed, warnings = format_text("# CLAUDE\n", path=Path("CLAUDE.md"))
    assert new == "# CLAUDE\n"
    assert changed is False
    assert any("denylisted" in w for w in warnings)


def test_bump_updated_skips_multiline_updated(tmp_path: Path) -> None:
    # A multi-line `updated:` value (block scalars are rejected by tokenize, but
    # a nested mapping passes) must not be bumped — rewriting just the key line
    # would orphan the continuation — while the rest still gets formatted.
    text = "---\nid: 'note-a3f9zk-x'\ntitle: needs quoting\nupdated:\n  nested: '2026-01-01'\n---\n"
    new, changed, _warnings = format_text(
        text, path=tmp_path / "n.md", bump_updated=True, today="2026-06-12"
    )
    assert changed is True
    assert "title: 'needs quoting'\n" in new
    assert "updated:\n  nested: '2026-01-01'\n" in new


# ---------------------------------------------------------------------------
# main(): quiet schema note, stdin failures, config errors, unreadable files
# ---------------------------------------------------------------------------


def test_main_custom_schema_quiet_suppresses_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    schema = tmp_path / "custom.json"
    schema.write_text("{}")
    rc = main(["--schema", str(schema), "--quiet"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""


def test_main_stdin_duplicate_key_warns_and_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # stdin mode mirrors file mode's exit-code contract: a refused
    # (duplicate-key) block must fail while passing the input through unchanged.
    monkeypatch.chdir(tmp_path)
    doc = "---\nid: 'a'\nid: 'b'\n---\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(doc))
    rc = main(["--stdin"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "<stdin>:" in captured.err
    assert captured.out == doc


def test_main_missing_explicit_file_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["nope.md"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "error:" in captured.err


def test_main_unreadable_file_reported_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "locked.md"
    f.write_text(CLEAN)
    f.chmod(0o000)
    try:
        rc = main([f.name])
    finally:
        f.chmod(0o644)
    captured = capsys.readouterr()
    assert rc == 1
    assert "cannot read" in captured.err


# ---------------------------------------------------------------------------
# 5.8.0 FR-008: minimal-escape scalar emitter (TC-T1-001..007). The emitter picks
# the quote style needing fewer escapes (single-cost = count of `'`; double-cost =
# count of `"` plus `\`; ties -> single), and forces double quotes for control
# characters so they round-trip losslessly. Every 5.7.0 single-quoted spelling is
# preserved verbatim (previously-passing rule).
# ---------------------------------------------------------------------------


def test_minimal_double_quoted_scalar_is_preserved() -> None:
    # TC-T1-001: `"Apple's"` needs no double-quote escape but a single-quoted
    # spelling would double the apostrophe, so the emitter keeps it double-quoted.
    # It is already minimal -> byte-identical, no reformat (Prettier agrees).
    src = _doc(title='"Apple\'s"')
    new, changed, _ = format_text(src, path=None)
    assert 'title: "Apple\'s"' in new
    assert changed is False


def test_control_character_scalar_round_trips_losslessly() -> None:
    # TC-T1-004: a double-quoted scalar decoding to control characters must re-emit
    # with the YAML escape table, never as literal control bytes inside single
    # quotes (which produced broken multiline YAML before FR-008).
    src = _doc(title='"a\\nb"')  # source: a \ n b  -> decodes to a<newline>b
    new, _changed, _ = format_text(src, path=None)
    assert 'title: "a\\nb"' in new  # escaped \n, not a literal newline
    parsed = yaml.safe_load(new.split("---\n", 2)[1])
    assert parsed["title"] == "a\nb"


def test_unquoted_apostrophe_scalar_emits_minimal_double() -> None:
    # TC-T1-005: an unquoted plain scalar carrying an apostrophe quotes in the
    # minimal style (double, no escape); the parsed value is unchanged.
    src = _doc(title="Apple's plan")
    new, _changed, _ = format_text(src, path=None)
    assert 'title: "Apple\'s plan"' in new
    parsed = yaml.safe_load(new.split("---\n", 2)[1])
    assert parsed["title"] == "Apple's plan"


def test_emitter_contract_table() -> None:
    # TC-T1-006: the full emitter contract, exercised through _requote_scalar_line
    # (its only production caller for key-line scalars). Each row is
    # (input `key: value` line, expected output line) for key `title`.
    from project_standards.format_frontmatter import (
        _requote_scalar_line,  # pyright: ignore[reportPrivateUsage]
    )

    # Behavior-changing rows (RED before FR-008): double-preservation branches and
    # the control-character escape set (\n \t \r \xNN \\ \").
    behavior_changing = [
        # double strictly cheaper (one apostrophe, no double-quote) -> preserved
        ('title: "Apple\'s"\n', 'title: "Apple\'s"\n'),
        # unquoted apostrophe -> minimal double
        ("title: Apple's plan\n", 'title: "Apple\'s plan"\n'),
        # two apostrophes vs one backslash: double still wins; the `\` is escaped
        ("title: \"a'b'c\\\\d\"\n", "title: \"a'b'c\\\\d\"\n"),
        # control-character escape set
        ('title: "a\\tb"\n', 'title: "a\\tb"\n'),
        ('title: "a\\rb"\n', 'title: "a\\rb"\n'),
        ('title: "a\\nb"\n', 'title: "a\\nb"\n'),
        ('title: "a\\x07b"\n', 'title: "a\\x07b"\n'),
    ]
    for line, expected in behavior_changing:
        assert _requote_scalar_line(line, "title") == expected, line

    # Unchanged-behavior rows (tie rule + cheaper-single) — these already held in
    # 5.7.0 and must keep holding (previously-passing rule).
    unchanged = [
        # escape-free double-quoted -> single (tie: both costs 0)
        ('title: "Hello"\n', "title: 'Hello'\n"),
        # plain unquoted, no quotes -> single
        ("title: Hello\n", "title: 'Hello'\n"),
        # double-quoting needs MORE escapes than single -> single wins
        ('title: "say \\"hi\\""\n', "title: 'say \"hi\"'\n"),
        # already single-quoted (doubled apostrophe) -> verbatim idempotent bypass
        ("title: 'Apple''s'\n", "title: 'Apple''s'\n"),
    ]
    for line, expected in unchanged:
        assert _requote_scalar_line(line, "title") == expected, line

    # Exclusions: null and flow lists are left for their own transforms; block
    # scalars never reach the emitter because tokenize refuses to reserialize them.
    assert _requote_scalar_line("license: null\n", "license") == "license: null\n"
    assert _requote_scalar_line("tags: ['a']\n", "tags") == "tags: ['a']\n"
    entries, reason = tokenize("title: |\n  block\n")
    assert entries == [] and reason is not None


def test_legacy_single_quoted_spelling_stays_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # TC-T1-002: a 5.7.0 doubled-apostrophe single-quoted scalar is the frozen
    # canonical spelling; the emitter's single-quote bypass keeps it byte-identical
    # and the CLI gate exits 0 (never flip pass -> fail).
    src = _doc(title="'Apple''s'")
    new, changed, _ = format_text(src, path=None)
    assert "title: 'Apple''s'" in new
    assert changed is False

    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(src)
    cfg = _cfg(tmp_path)
    assert main(["--check", "--config", str(cfg), str(f)]) == 0


# A frozen corpus of 5.7.0-canonical documents: one per accepted key-line scalar
# class (plain single-quoted, doubled-apostrophe single-quoted, explicit null,
# inline comment, block list). The new emitter must leave every one byte-identical.
_FROZEN_5_7_0_CORPUS = [
    (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'Plain Title'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
        "# Body\n"
    ),
    (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'  # frozen at creation\n"
        "title: 'Apple''s'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "license: null\n"
        "---\n"
        "# Body\n"
    ),
    (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related:\n"
        "  - 'CHANGELOG.md'\n"
        "  - 'meta/versioning.md'\n"
        "---\n"
        "# Body\n"
    ),
]


def test_frozen_5_7_0_corpus_stays_green_both_routings(tmp_path: Path) -> None:
    """TC-T1-007: every 5.7.0-canonical document reports no reformatting and stays
    byte-identical through both current-default and exact markdown-frontmatter 1.4
    routing. The scalar emitter is engine-level: the version-selected provider path
    (`plan_frontmatter_format(..., version=...)`) calls the same module-level
    `format_text` regardless of the pinned version, so byte identity through the 1.4
    provider path and through `format_text` proves the shared emitter for both."""
    # Current-default routing: the module-level engine.
    for doc in _FROZEN_5_7_0_CORPUS:
        new, changed, warnings = format_text(doc, path=None)
        assert new == doc, doc
        assert changed is False
        assert warnings == []

    # Exact markdown-frontmatter 1.4 routing: the version-selected provider path.
    from project_standards.frontmatter_authoring import plan_frontmatter_format
    from project_standards.package_contract.paths import PackageVersion

    names: list[Path] = []
    for index, doc in enumerate(_FROZEN_5_7_0_CORPUS):
        name = f"note{index}.md"  # no README/index/docs-research rule -> no doc_type change
        (tmp_path / name).write_text(doc, encoding="utf-8")
        names.append(Path(name))
    plan = plan_frontmatter_format(tmp_path, tuple(names), version=PackageVersion("1.4"))
    assert plan.formatted_paths == ()  # zero reformat reports
    assert not plan.plan.actions  # byte identity -> no mutation actions


def test_main_stdin_non_refusal_warning_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Warnings other than the duplicate-key refusal (here: an unsupported YAML
    # construct) are reported but are not failures in stdin mode.
    monkeypatch.chdir(tmp_path)
    doc = "---\nid: >-\n  'a'\n---\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(doc))
    rc = main(["--stdin"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "<stdin>:" in captured.err
    assert captured.out == doc
