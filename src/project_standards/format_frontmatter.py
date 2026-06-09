"""Autoformatter for managed Markdown frontmatter (the write-side companion to
validate-frontmatter). Tokenizes the leading YAML block into per-key entries,
applies deterministic transforms, and re-emits the block preserving comments and
per-line endings (same technique as validate_id --fix). Never touches `id` and
never edits the document body."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Leading frontmatter block; groups: open fence, body (between fences), close fence.
_FM_RE = re.compile(r"\A(---[ \t]*\r?\n)(.*?)(\r?\n---[ \t]*(?:\r?\n|$))", re.DOTALL)
# A top-level (column 0) mapping key line: `key:` optionally followed by a value.
_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "markdown-frontmatter.schema.json"
VALID_DOC_TYPES: frozenset[str] = frozenset(
    json.loads(_SCHEMA_PATH.read_text())["properties"]["doc_type"]["enum"]
)

CANONICAL_ORDER: tuple[str, ...] = (
    "schema_version", "id", "title", "description", "doc_type", "status",
    "created", "updated", "reviewed", "owner", "consumer", "tags", "aliases",
    "related", "supersedes", "superseded_by", "depends_on", "applies_to",
    "source", "confidence", "visibility", "license", "publish", "project",
    "x_project",
)


@dataclass
class Entry:
    """One top-level frontmatter key and the exact source lines it owns.

    `lines` holds every physical source line for this entry WITH its original
    line ending: any leading comment/blank run, the `key:` line (incl. an inline
    `# comment`), and indented continuation lines (block list or nested mapping).
    `key` is None only for a trailing comment/blank run after the last key."""

    key: str | None
    lines: list[str] = field(default_factory=list)


def _split_keepends(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def tokenize(body: str) -> tuple[list[Entry], str | None]:
    """Split the between-fences `body` into Entry objects.

    Returns (entries, None) on success, or ([], reason) if the block contains a
    construct unsafe to reorder/reserialize (anchors, merge keys, a non-key line
    at column 0). Nested mappings and block lists are supported (carried opaquely
    as continuation lines)."""
    lines = _split_keepends(body)
    entries: list[Entry] = []
    pending: list[str] = []  # leading comment/blank lines for the next key
    seen: set[str] = set()   # duplicate top-level keys are unsafe to reorder (CR-002)
    i = 0
    while i < len(lines):
        line = lines[i]
        content = line.rstrip("\r\n")
        stripped = content.lstrip(" \t")
        if stripped == "" or stripped.startswith("#"):
            pending.append(line)
            i += 1
            continue
        m = _TOP_KEY_RE.match(content)
        if not m:
            return [], f"unrecognized top-level line: {content!r}"
        key = m.group(1)
        value = m.group(2).lstrip()
        if value[:1] in ("&", "*") or value.startswith("<<") or value[:1] in ("|", ">"):
            return [], f"unsupported YAML construct on key {key!r}"
        if key in seen:
            return [], f"duplicate top-level key {key!r} (refusing to rewrite)"
        seen.add(key)
        entry = Entry(key=key, lines=[*pending, line])
        pending = []
        i += 1
        # Gather indented continuation lines (block list items / nested mapping).
        while i < len(lines):
            nxt = lines[i]
            ncontent = nxt.rstrip("\r\n")
            if ncontent.lstrip(" \t") == "":
                break  # blank line ends the entry; becomes leading run of next
            if nxt[:1] in (" ", "\t"):
                entry.lines.append(nxt)
                i += 1
                continue
            break
        entries.append(entry)
    if pending:
        entries.append(Entry(key=None, lines=pending))
    return entries, None


_ORDER_INDEX = {key: i for i, key in enumerate(CANONICAL_ORDER)}


def reorder(entries: list[Entry], warnings: list[str]) -> list[Entry]:
    """Stable sort entries into CANONICAL_ORDER. Unknown keys keep their relative
    order after all known keys; a trailing comment-only entry (key=None) stays last.
    Unknown keys also emit a warn-only message (never deleted)."""
    def sort_key(item: tuple[int, Entry]) -> tuple[int, int]:
        idx, entry = item
        if entry.key is None:
            return (len(CANONICAL_ORDER) + 1, idx)  # trailing comments last
        if entry.key in _ORDER_INDEX:
            return (_ORDER_INDEX[entry.key], 0)
        warnings.append(f"unknown frontmatter key '{entry.key}' (kept; not in schema)")
        return (len(CANONICAL_ORDER), idx)

    return [e for _, e in sorted(enumerate(entries), key=sort_key)]


def serialize(entries: list[Entry]) -> str:
    """Concatenate entries' source lines verbatim.

    The regex design absorbs the final `\\n` of the body into `close_fence`, so
    the very last physical line of `body` arrives without a trailing newline.  When
    reordering moves that entry to a non-tail position, we must ensure it still
    ends with a newline so the following entry starts on a new line.  If the entry
    stays last, we leave it unchanged to preserve byte-identity on round-trips."""
    parts: list[str] = []
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        for j, line in enumerate(entry.lines):
            is_last_line = j == len(entry.lines) - 1
            if is_last_line and not is_last and line and not line.endswith(("\n", "\r\n")):
                parts.append(line + "\n")
            else:
                parts.append(line)
    return "".join(parts)


def format_text(text: str, *, path: Path | None) -> tuple[str, bool, list[str]]:
    """Format the frontmatter block of `text`. Returns (new_text, changed, warnings).

    `path` informs path-based transforms (added in later tasks); None disables them
    (stdin mode). This skeleton only round-trips, so output == input for now."""
    warnings: list[str] = []
    match = _FM_RE.match(text)
    if match is None:
        return text, False, warnings
    open_fence, body, close_fence = match.group(1), match.group(2), match.group(3)
    rest = text[match.end():]
    entries, reason = tokenize(body)
    if reason is not None:
        warnings.append(f"skipped (unsupported frontmatter): {reason}")
        return text, False, warnings
    entries = reorder(entries, warnings)
    new_body = serialize(entries)
    new_text = open_fence + new_body + close_fence + rest
    changed = new_text != text
    return new_text, changed, warnings
