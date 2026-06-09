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
from typing import Any, cast

import yaml

# Leading frontmatter block; groups: open fence, body (between fences), close fence.
_FM_RE = re.compile(r"\A(---[ \t]*\r?\n)(.*?)(\r?\n---[ \t]*(?:\r?\n|$))", re.DOTALL)
# A top-level (column 0) mapping key line: `key:` optionally followed by a value.
_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "markdown-frontmatter.schema.json"
VALID_DOC_TYPES: frozenset[str] = frozenset(
    json.loads(_SCHEMA_PATH.read_text())["properties"]["doc_type"]["enum"]
)

CANONICAL_ORDER: tuple[str, ...] = (
    "schema_version",
    "id",
    "title",
    "description",
    "doc_type",
    "status",
    "created",
    "updated",
    "reviewed",
    "owner",
    "consumer",
    "tags",
    "aliases",
    "related",
    "supersedes",
    "superseded_by",
    "depends_on",
    "applies_to",
    "source",
    "confidence",
    "visibility",
    "license",
    "publish",
    "project",
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
    seen: set[str] = set()  # duplicate top-level keys are unsafe to reorder (CR-002)
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


def _emit_single_quoted(value: str) -> str:
    """YAML single-quoted scalar: wrap in quotes, double internal single-quotes."""
    return "'" + value.replace("'", "''") + "'"


_NULL_TOKENS = frozenset({"null", "Null", "NULL", "~"})


def _split_value_comment(rest: str) -> tuple[str, str]:
    """Split the text after `key:` into (raw_value, comment). A YAML inline comment
    begins only at whitespace + '#' (CR-NEW-003); a bare '#' (e.g. `C# guide`,
    `http://x/#frag`), a '#' inside a quoted scalar, or a '#' inside a quoted flow-list
    item (e.g. `['Issue #123']` — CR-NEW-005) is literal. `comment` keeps its leading
    whitespace (e.g. '  # note') so it round-trips, or is ''."""
    stripped = rest.lstrip(" \t")
    lead = rest[: len(rest) - len(stripped)]
    if stripped[:1] in ("'", '"'):
        quote = stripped[0]
        i = 1
        while i < len(stripped):
            ch = stripped[i]
            if quote == "'" and ch == "'":
                if stripped[i : i + 2] == "''":  # escaped single quote
                    i += 2
                    continue
                return lead + stripped[: i + 1], stripped[i + 1 :]
            if quote == '"' and ch == "\\":
                i += 2
                continue
            if quote == '"' and ch == '"':
                return lead + stripped[: i + 1], stripped[i + 1 :]
            i += 1
        return rest, ""  # unterminated quote -> treat whole as value (left as-is upstream)
    if stripped[:1] == "[":  # flow list: scan to the matching ], honoring quotes
        depth = 0
        in_quote = ""
        i = 0
        while i < len(stripped):
            ch = stripped[i]
            if in_quote:
                if in_quote == "'" and ch == "'":
                    if stripped[i : i + 2] == "''":
                        i += 2
                        continue
                    in_quote = ""
                elif in_quote == '"' and ch == "\\":
                    i += 2
                    continue
                elif in_quote == '"' and ch == '"':
                    in_quote = ""
            elif ch in ("'", '"'):
                in_quote = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    tail = stripped[i + 1 :]
                    return lead + stripped[: i + 1], (tail if re.match(r"\s+#", tail) else "")
            i += 1
        return rest, ""  # unbalanced brackets -> no comment
    m = re.search(r"(\s+#.*)$", rest)  # plain scalar: comment = whitespace then '#' to end
    if m:
        return rest[: m.start()], rest[m.start() :]
    return rest, ""


def _requote_scalar_line(line: str, key: str) -> str:
    """Re-quote the scalar value on a `key: value` line WITHOUT resolving its YAML type
    (CR-NEW-001): the author's literal text is single-quoted, so `on`/`off`/`1.1`/a date
    keep their exact characters. Indentation, an inline `# comment` (split at a real
    whitespace-`#` boundary — CR-NEW-003), and the line ending are preserved; explicit
    `null`/`~`, empty values, and flow lists are left untouched."""
    m = re.match(
        r"^(?P<indent>[ \t]*)(?P<key>" + re.escape(key) + r":)(?P<sep>[ \t]*)"
        r"(?P<rest>.*)(?P<eol>\r?\n?)$",
        line,
    )
    if m is None:
        return line
    value_raw, comment = _split_value_comment(m.group("rest"))
    raw = value_raw.strip()
    if raw == "" or raw.startswith("["):
        return line  # empty or flow list -> handled by normalize_lists
    if raw in _NULL_TOKENS:
        return line  # explicit null stays null
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return line  # already single-quoted -> idempotent
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        decoded = yaml.safe_load(raw)  # explicit quotes -> intended string, no type guess
        text_value = decoded if isinstance(decoded, str) else raw
    else:
        text_value = raw  # unquoted plain scalar: quote the RAW text, never resolve it
    sep = m.group("sep") or " "
    return (
        m.group("indent")
        + m.group("key")
        + sep
        + _emit_single_quoted(text_value)
        + comment
        + m.group("eol")
    )


def _line_ending(line: str) -> str:
    """Return the line ending of `line`, or '' if the line has no trailing newline.

    The regex design absorbs the final newline of the frontmatter body into the
    close-fence group, so the very last physical line of `body` arrives without a
    trailing newline.  Returning '' here lets callers preserve that absent newline
    on the key line; item lines in a block list always use '\n'."""
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


# The array-typed fields in the schema; only these are list-normalized.
_LIST_FIELDS = ("tags", "aliases", "related", "supersedes", "depends_on", "applies_to", "source")


def _leading_run(entry: Entry) -> int:
    """Count of leading comment/blank lines before the entry's `key:` line."""
    n = 0
    for ln in entry.lines:
        stripped = ln.rstrip("\r\n").lstrip(" \t")
        if stripped == "" or stripped.startswith("#"):
            n += 1
        else:
            break
    return n


def normalize_lists(entries: list[Entry]) -> None:
    """In place: render each list-typed field as canonical block style (single-quoted
    items, duplicates removed first-wins); an empty/absent value becomes `key: []`.
    Values are read with yaml.BaseLoader so list items are NEVER type-coerced — e.g.
    `[on, off]` stays the strings 'on'/'off', not booleans (CR-NEW-001)."""
    for entry in entries:
        if entry.key not in _LIST_FIELDS:
            continue
        lead = _leading_run(entry)
        try:
            loaded = yaml.load("".join(entry.lines[lead:]), Loader=yaml.BaseLoader)  # pyright: ignore[reportUnknownMemberType]
        except yaml.YAMLError:
            continue
        if not isinstance(loaded, dict) or entry.key not in loaded:
            continue
        value: Any = cast(Any, loaded)[entry.key]  # BaseLoader dict values are untyped
        if not (value is None or value == "" or isinstance(value, list)):
            continue  # a scalar where a list belongs -> leave for the validator
        key_line = entry.lines[lead]
        eol = _line_ending(entry.lines[-1])
        # Indent by slice (NOT re.match(...).group(0), which basedpyright-strict flags — CR-NEW-002).
        indent = key_line[: len(key_line) - len(key_line.lstrip(" \t"))]
        after_colon = key_line.rstrip("\r\n").split(":", 1)[1] if ":" in key_line else ""
        inline = _split_value_comment(after_colon)[
            1
        ]  # comment after [], [a], or bare key (CR-NEW-004)
        leading = entry.lines[:lead]
        raw_items: list[Any] = cast(list[Any], value) if isinstance(value, list) else []
        items: list[str] = [str(x) for x in raw_items]
        seen: list[str] = []
        for item in items:
            if item not in seen:
                seen.append(item)
        # item_eol: block-list items always need a real newline; fall back to '\n'
        # when the key line has no trailing newline (last entry in body — the regex
        # design absorbs that newline into close_fence).
        item_eol = eol or "\n"
        if not seen:
            entry.lines = [*leading, f"{indent}{entry.key}: []{inline}{eol}"]
        else:
            rendered = [f"{indent}{entry.key}:{inline}{item_eol}"]
            rendered += [f"{indent}  - {_emit_single_quoted(s)}{item_eol}" for s in seen]
            entry.lines = [*leading, *rendered]


def requote(entries: list[Entry]) -> None:
    """In place: single-quote the scalar value on each single-line scalar entry.
    Multi-line entries (lists, nested mappings) are left for their own transforms."""
    for entry in entries:
        if entry.key is None or len(entry.lines) != 1:
            continue
        entry.lines[0] = _requote_scalar_line(entry.lines[0], entry.key)


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


BUNDLED_SCHEMA_VERSION = "1.1"  # matches registry frontmatter_default; see Task A9 note
REQUIRED_ARRAYS = ("tags", "aliases", "related")


def _keys(entries: list[Entry]) -> set[str]:
    return {e.key for e in entries if e.key is not None}


def rename_type(entries: list[Entry], warnings: list[str]) -> None:
    present = _keys(entries)
    if "doc_type" in present:
        if "type" in present:
            warnings.append("both 'type' and 'doc_type' present; kept 'doc_type', left 'type'")
        return
    for entry in entries:
        if entry.key == "type":
            entry.key = "doc_type"
            entry.lines = [re.sub(r"\btype:", "doc_type:", ln, count=1) for ln in entry.lines]
            return


def _new_scalar_entry(key: str, value: str, eol: str) -> Entry:
    return Entry(key=key, lines=[f"{key}: {_emit_single_quoted(value)}{eol}"])


def _new_empty_list_entry(key: str, eol: str) -> Entry:
    return Entry(key=key, lines=[f"{key}: []{eol}"])


def inject_defaults(entries: list[Entry]) -> None:
    """Add schema_version and any missing required arrays. Reorder (A2) places them."""
    eol = _line_ending(entries[0].lines[-1]) if entries and entries[0].lines else "\n"
    present = _keys(entries)
    if "schema_version" not in present:
        entries.append(_new_scalar_entry("schema_version", BUNDLED_SCHEMA_VERSION, eol))
    for key in REQUIRED_ARRAYS:
        if key not in present:
            entries.append(_new_empty_list_entry(key, eol))


def format_text(text: str, *, path: Path | None) -> tuple[str, bool, list[str]]:
    """Format the frontmatter block of `text`. Returns (new_text, changed, warnings).

    `path` informs path-based transforms (added in later tasks); None disables them
    (stdin mode). This skeleton only round-trips, so output == input for now."""
    warnings: list[str] = []
    match = _FM_RE.match(text)
    if match is None:
        return text, False, warnings
    open_fence, body, close_fence = match.group(1), match.group(2), match.group(3)
    rest = text[match.end() :]
    entries, reason = tokenize(body)
    if reason is not None:
        warnings.append(f"skipped (unsupported frontmatter): {reason}")
        return text, False, warnings
    rename_type(entries, warnings)
    inject_defaults(entries)
    normalize_lists(entries)
    requote(entries)
    entries = reorder(entries, warnings)
    new_body = serialize(entries)
    new_text = open_fence + new_body + close_fence + rest
    changed = new_text != text
    return new_text, changed, warnings
