from pathlib import Path

import pytest

from project_standards.format_frontmatter import format_text

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


def test_clean_input_is_byte_identical():
    # format_text returns (new_text, changed, warnings). Already-canonical -> no change.
    new, changed, warnings = format_text(CLEAN, path=None)
    assert new == CLEAN
    assert changed is False


def test_no_frontmatter_is_noop():
    body = "# Just a body\n\nNo frontmatter here.\n"
    new, changed, warnings = format_text(body, path=None)
    assert new == body
    assert changed is False


def test_comment_block_preserved_on_roundtrip():
    src = CLEAN.replace("id: 'note-a3f9zk-x'\n", "id: 'note-a3f9zk-x'  # frozen at creation\n")
    new, changed, warnings = format_text(src, path=None)
    assert "# frozen at creation" in new
    assert changed is False


def test_duplicate_top_level_key_is_refused():
    # PyYAML silently keeps the last duplicate; the formatter must NOT rewrite such a
    # block (it would erase the human-visible conflict). It skips with a warning. (CR-002)
    src = CLEAN.replace("tags: []\n", "tags: []\ntags: ['x']\n")
    new, changed, warnings = format_text(src, path=None)
    assert new == src
    assert changed is False
    assert any("duplicate" in w for w in warnings)


def test_reorder_to_canonical_order():
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


def test_unknown_key_sorts_after_known_keys():
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


def test_unquoted_scalars_get_single_quoted():
    src = (
        "---\n"
        "schema_version: 1.1\n"          # identifier-like number -> '1.1'
        "id: 'note-a3f9zk-x'\n"
        "title: X\n"                       # bare string -> 'X'
        "description: A doc.\n"
        "doc_type: note\n"
        "status: draft\n"
        "created: 2026-06-08\n"            # unquoted date -> '2026-06-08'
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


def test_null_license_stays_null():
    src = _doc(extra="license: null\n")  # helper defined below
    new, _, _ = format_text(src, path=None)
    assert "license: null" in new
    assert "license: 'null'" not in new


def test_double_quoted_becomes_single_quoted():
    src = _doc(title='"Hello"')
    new, _, _ = format_text(src, path=None)
    assert "title: 'Hello'" in new


@pytest.mark.parametrize("token", ["on", "off", "Yes", "No"])
def test_boolean_like_scalar_kept_as_string(token: str) -> None:
    # `title: on` must become `title: 'on'`, NOT 'true' (CR-NEW-001).
    src = _doc(title=token)
    new, _, _ = format_text(src, path=None)
    assert f"title: '{token}'" in new


def test_hash_in_plain_scalar_is_not_a_comment():
    # `C#` has no whitespace before '#', so it is scalar content, not a comment (CR-NEW-003).
    src = _doc(title="C# guide")
    new, _, _ = format_text(src, path=None)
    assert "title: 'C# guide'" in new


def test_url_fragment_preserved():
    src = _doc(title="http://example.com/p#frag")
    new, _, _ = format_text(src, path=None)
    assert "title: 'http://example.com/p#frag'" in new


def test_real_inline_comment_preserved_on_scalar():
    src = _doc(title="X  # keep me")  # whitespace + '#' IS a real comment
    new, _, _ = format_text(src, path=None)
    assert "title: 'X'  # keep me" in new


def test_flow_list_becomes_block_and_dedupes():
    src = _doc(tags_line="tags: ['a', 'b', 'a']")
    new, changed, _ = format_text(src, path=None)
    assert "tags:\n  - 'a'\n  - 'b'\n" in new
    assert new.count("- 'a'") == 1
    assert changed is True


def test_empty_block_list_becomes_flow_empty():
    src = _doc(tags_line="tags:")  # key with no value and no items -> tags: []
    new, _, _ = format_text(src, path=None)
    assert "tags: []" in new


def test_boolean_like_list_items_kept_as_strings():
    # list items must not be coerced (BaseLoader); [on, off, yes, no] stay strings (CR-NEW-001).
    src = _doc(tags_line="tags: [on, off, yes, no]")
    new, _, _ = format_text(src, path=None)
    assert "- 'on'" in new and "- 'off'" in new and "- 'yes'" in new and "- 'no'" in new
    assert "True" not in new and "False" not in new


def test_inline_comment_preserved_on_flow_list():
    src = _doc(tags_line="tags: [a, b]  # keep")  # CR-NEW-004
    new, _, _ = format_text(src, path=None)
    assert "tags:  # keep" in new  # comment moves to the block key line
    assert "- 'a'" in new and "- 'b'" in new


def test_inline_comment_preserved_on_empty_list():
    src = _doc(tags_line="tags: []  # keep")  # CR-NEW-004
    new, _, _ = format_text(src, path=None)
    assert "tags: []  # keep" in new


def test_hash_inside_quoted_list_item_not_a_comment():
    src = _doc(extra="source: ['Issue #123']\n")  # CR-NEW-005: '#' inside quote is literal
    new, _, _ = format_text(src, path=Path("docs/x.md"))
    assert "- 'Issue #123'" in new  # whole item preserved, '#' kept
    assert "source: []" not in new  # not emptied / mis-split


def test_real_comment_after_quoted_list_item_preserved():
    src = _doc(extra="source: ['Issue #123']  # keep\n")  # CR-NEW-005
    new, _, _ = format_text(src, path=Path("docs/x.md"))
    assert "- 'Issue #123'" in new
    assert "source:  # keep" in new
