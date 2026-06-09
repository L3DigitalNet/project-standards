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
