# Frontmatter Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the 2.1.0 frontmatter suite — `format-frontmatter` (autoformatter), `validate-references` (opt-in semantic validators), and the ergonomics (`project-standards fix`, extended `validate`, `--stdin`, pre-commit hooks) — building on the converged spec `docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`.

**Architecture:** Three sub-projects sharing the existing `collect_paths`/`load_config`/`parse_frontmatter` helpers. A is a line-based block tokenizer + ordered transforms + per-line-ending-preserving reserializer (extends the `validate_id --fix` technique; no new runtime dependency). B is a repo-wide index pass with five checks, opt-in via config. C wires A+B into `project-standards fix`/`validate`, the reusable workflow, and `.pre-commit-hooks.yaml`.

**Tech Stack:** Python ≥3.14, `argparse`, `PyYAML` (already a dep, parse-only), `jsonschema` (already a dep), `pytest`/`coverage`/`ruff`/`basedpyright` toolchain.

**Toolchain gate (run after every phase):**
```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

---

## File structure

| File | Responsibility | Phase |
|---|---|---|
| `src/project_standards/id_format.py` | **Create** — shared `slugify()` + `random_token()` (extracted from `validate_id`) | 0 |
| `src/project_standards/validate_id.py` | **Modify** — import `slugify`/token-gen from `id_format` (remove local copies) | 0 |
| `src/project_standards/validate_frontmatter.py` | **Modify** — `ProjectConfig`/`load_config` gain `references_enabled` | 0 |
| `pyproject.toml` | **Modify** — add `format-frontmatter`, `validate-references` console scripts | A/B |
| `src/project_standards/format_frontmatter.py` | **Create** — tokenizer, transforms, serializer, CLI | A |
| `tests/test_format_frontmatter.py` | **Create** — A's tests | A |
| `src/project_standards/validate_references.py` | **Create** — repo index + 5 checks + CLI | B |
| `tests/test_validate_references.py` | **Create** — B's tests | B |
| `src/project_standards/cli.py` | **Modify** — `fix` subcommand; `validate` also runs references | C |
| `.github/workflows/validate-markdown-frontmatter.yml` | **Modify** — add `validate-references` step | C |
| `.pre-commit-hooks.yaml` | **Create** — mutating + check-only hook ids | C |
| `tests/test_cli_fix.py`, `tests/test_precommit_hooks.py` | **Create** — C's tests | C |

---

## Phase 0 — Shared foundation

### Task 0.1: Extract `id_format.py` (shared slugify + token generator)

**Files:**
- Create: `src/project_standards/id_format.py`
- Test: `tests/test_id_format.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_id_format.py
import re
from project_standards.id_format import slugify, random_token


def test_slugify_basic():
    assert slugify("Tailscale ACL tag ordering gotcha") == "tailscale-acl-tag-ordering-gotcha"


def test_slugify_strips_accents_and_punctuation():
    assert slugify("Standards Adoption & Compliance Procedure") == "standards-adoption-compliance-procedure"
    assert slugify("café déjà") == "cafe-deja"


def test_slugify_empty_for_symbol_only():
    assert slugify("!!!") == ""


def test_random_token_is_six_base36_chars():
    tok = random_token()
    assert re.fullmatch(r"[0-9a-z]{6}", tok)


def test_random_token_varies():
    assert len({random_token() for _ in range(50)}) > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_id_format.py -v`
Expected: FAIL — `ModuleNotFoundError: project_standards.id_format`

- [ ] **Step 3: Write minimal implementation**

```python
# src/project_standards/id_format.py
"""Shared id-token helpers used by validate_id (id validation/fix) and
format_frontmatter (scaffold). One copy so the two tools cannot drift."""

from __future__ import annotations

import re
import secrets
import string
import unicodedata

# Base-36 alphabet (digits + lowercase letters) for the 6-char id token.
_BASE36_CHARS = string.digits + string.ascii_lowercase


def slugify(text: str) -> str:
    """Lowercase kebab-case slug: strip accents to ASCII, lowercase, collapse
    every run of non-alphanumerics to a single hyphen, trim leading/trailing."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def random_token(length: int = 6) -> str:
    """A cryptographically-random base-36 token (default 6 chars)."""
    return "".join(secrets.choice(_BASE36_CHARS) for _ in range(length))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_id_format.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/id_format.py tests/test_id_format.py
git commit -m "feat(id_format): extract shared slugify + token generator"
```

### Task 0.2: Point `validate_id` at the shared helpers (no behavior change)

**Files:**
- Modify: `src/project_standards/validate_id.py` (the `slugify` def at lines 99-120; the `_BASE36_CHARS` constant at line 72; the token generation at line 322)

- [ ] **Step 1: Run the existing suite to capture the green baseline**

Run: `uv run pytest tests/test_validate_id.py -q`
Expected: PASS (existing tests green — this is the regression guard)

- [ ] **Step 2: Replace the local copies with imports**

In `src/project_standards/validate_id.py`, delete the local `slugify` function and the `_BASE36_CHARS` constant, and add to the imports block:

```python
from project_standards.id_format import random_token, slugify
```

Replace the token line in `fix_file` (was `token = "".join(secrets.choice(_BASE36_CHARS) for _ in range(6))`) with:

```python
    token = random_token()
```

Remove the now-unused `secrets`, `string`, and `unicodedata` imports if nothing else uses them (check with `ruff check`).

- [ ] **Step 3: Run the suite to verify no behavior change**

Run: `uv run pytest tests/test_validate_id.py -q && uv run ruff check src/project_standards/validate_id.py`
Expected: PASS, ruff clean (no unused imports)

- [ ] **Step 4: Commit**

```bash
git add src/project_standards/validate_id.py
git commit -m "refactor(validate_id): use shared id_format helpers"
```

### Task 0.3: Config gains `markdown.frontmatter.references.enabled`

**Files:**
- Modify: `src/project_standards/validate_frontmatter.py` (`ProjectConfig.__init__` lines 285-306; `load_config` frontmatter block lines 397-407)
- Test: `tests/test_validate_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_validate_frontmatter.py
from project_standards.validate_frontmatter import load_config


def test_references_enabled_defaults_false(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    assert load_config(cfg).references_enabled is False


def test_references_enabled_true(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n"
    )
    assert load_config(cfg).references_enabled is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate_frontmatter.py -k references -v`
Expected: FAIL — `AttributeError: 'ProjectConfig' object has no attribute 'references_enabled'`

- [ ] **Step 3: Implement**

In `ProjectConfig.__init__`, add a keyword parameter `references_enabled: bool = False` and `self.references_enabled = references_enabled`. In `load_config`, inside the `if isinstance(frontmatter, dict):` block, add:

```python
                    references = fm.get("references")
                    references_enabled = (
                        bool(references.get("enabled", False))
                        if isinstance(references, dict)
                        else False
                    )
```

Initialise `references_enabled = False` near the other defaults at the top of `load_config`, and pass `references_enabled=references_enabled` into the `ProjectConfig(...)` constructor call.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validate_frontmatter.py -k references -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/validate_frontmatter.py tests/test_validate_frontmatter.py
git commit -m "feat(config): add markdown.frontmatter.references.enabled"
```

### Task 0.4: Make `schema_value_is_path` public (strict-basedpyright safe)

> The new `format_frontmatter` and `validate_references` modules need the custom-schema predicate. Importing the private `_schema_value_is_path` into production code fails this repo's `strict` + `failOnWarnings` basedpyright (`reportPrivateUsage`), and adding `# pyright: ignore` in production is undesirable (codex CR-003). Promote it to a public name.

**Files:**
- Modify: `src/project_standards/validate_frontmatter.py` (def at line 77; callers at lines 94, 325, 352)

- [ ] **Step 1: Rename and update internal callers**

In `src/project_standards/validate_frontmatter.py`, rename `def _schema_value_is_path(` → `def schema_value_is_path(` and update the three internal call sites (in `resolve_schema_path`, `resolve_effective_schema`, `frontmatter_adr_incompatibility`) to the public name. No behavior change.

- [ ] **Step 2: Run the existing suite (regression guard)**

Run: `uv run pytest tests/test_validate_frontmatter.py -q && uv run basedpyright src/project_standards/validate_frontmatter.py`
Expected: PASS; basedpyright clean.

- [ ] **Step 3: Commit**

```bash
git add src/project_standards/validate_frontmatter.py
git commit -m "refactor(validate_frontmatter): make schema_value_is_path public"
```

> **Note for all later tasks:** new modules import `schema_value_is_path` (public), never the underscore name.

### Task 0.5: Reject duplicate top-level keys in `parse_frontmatter`

> PyYAML's `safe_load` silently keeps the *last* of duplicate mapping keys, so the whole suite could report clean while a file's frontmatter visibly conflicts (codex CR-002). Make `parse_frontmatter` reject duplicates so `validate-frontmatter` (and thus `project-standards validate`/`fix`) errors on them. **Invariant note:** duplicate mapping keys are invalid YAML 1.1; this can only fire on already-broken documents, so it surfaces a latent bug rather than breaking a valid consumer setup — a justified, narrow exception to "no new failures." The formatter's tokenizer also refuses such blocks (A1) as defense-in-depth.

**Files:**
- Modify: `src/project_standards/validate_frontmatter.py` (`parse_frontmatter` at lines 123-134)
- Test: `tests/test_validate_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from project_standards.validate_frontmatter import parse_frontmatter, FrontmatterParseError


def test_duplicate_top_level_key_rejected():
    with pytest.raises(FrontmatterParseError):
        parse_frontmatter("---\ntags: []\ntags: ['x']\n---\n# body\n")


def test_unique_keys_still_parse():
    meta = parse_frontmatter("---\nid: 'x'\ntags: []\n---\n# body\n")
    assert meta == {"id": "x", "tags": []}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate_frontmatter.py -k duplicate_top_level_key -v`
Expected: FAIL — `safe_load` silently collapses, no error raised

- [ ] **Step 3: Implement a unique-key loader**

In `src/project_standards/validate_frontmatter.py`, add near the parsing section:

```python
class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (PyYAML otherwise keeps the
    last silently). Frontmatter with a duplicate key is a bug, not a valid doc."""


def _construct_no_duplicates(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[str, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_no_duplicates
)
```

In `parse_frontmatter`, replace `yaml.safe_load(match.group(1))` with `yaml.load(match.group(1), Loader=_UniqueKeyLoader)`. The `ConstructorError` is a `yaml.YAMLError`, so the existing `except yaml.YAMLError` already converts it to `FrontmatterParseError`.

- [ ] **Step 4: Run tests (new + existing regression guard)**

Run: `uv run pytest tests/test_validate_frontmatter.py -q`
Expected: PASS — the new tests pass and no existing fixture regresses (if one does, it had a real duplicate key)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/validate_frontmatter.py tests/test_validate_frontmatter.py
git commit -m "feat(validate): reject duplicate top-level frontmatter keys"
```

---

## Phase A — `format-frontmatter`

> Build the module test-first: Task A1 establishes the parse→entries→reserialize skeleton that is a **no-op on already-clean input** (proving byte-identity). Tasks A2–A9 each add exactly one transform. The idempotence property test (A10) then holds by construction.

### Task A1: Block tokenizer + byte-identical round-trip skeleton

**Files:**
- Create: `src/project_standards/format_frontmatter.py`
- Test: `tests/test_format_frontmatter.py`
- Modify: `pyproject.toml` (add the console script)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_format_frontmatter.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -v`
Expected: FAIL — `ModuleNotFoundError: project_standards.format_frontmatter`

- [ ] **Step 3: Write the skeleton implementation**

```python
# src/project_standards/format_frontmatter.py
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


def serialize(entries: list[Entry]) -> str:
    """Concatenate entries' source lines verbatim (round-trip with no transforms)."""
    return "".join(line for entry in entries for line in entry.lines)


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
    new_body = serialize(entries)
    new_text = open_fence + new_body + close_fence + rest
    changed = new_text != text
    return new_text, changed, warnings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Add the console script entry point**

In `pyproject.toml` under `[project.scripts]`, add (a `main` is added in Task A9; the entry is wired now so the import path is reserved):

```toml
format-frontmatter = "project_standards.format_frontmatter:main"
```

Do NOT run `uv sync` yet — `main` does not exist until A9; adding the line now keeps the diff with the code that needs it. (If your executor validates entry points on sync, defer this step to A9.)

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py pyproject.toml
git commit -m "feat(format): block tokenizer + byte-identical round-trip skeleton"
```

### Task A2: Canonical key reorder

**Files:**
- Modify: `src/project_standards/format_frontmatter.py` (add `reorder`, call it in `format_text`)
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
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
    assert keys[:5] == ["---", "schema_version", "id", "title", "description"]
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -k "reorder or unknown_key" -v`
Expected: FAIL — keys not reordered / no warning emitted

- [ ] **Step 3: Implement**

Add to `format_frontmatter.py`:

```python
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
```

In `format_text`, replace `new_body = serialize(entries)` with:

```python
    entries = reorder(entries, warnings)
    new_body = serialize(entries)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -k "reorder or unknown_key" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py
git commit -m "feat(format): canonical key reorder (unknown keys warn, kept last)"
```

### Task A3: Quote normalization for scalar values

**Files:**
- Modify: `src/project_standards/format_frontmatter.py`
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
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
def test_boolean_like_scalar_kept_as_string(token):
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
```

Add this helper near the top of the test file (used by several tests):

```python
def _doc(*, title="X", extra="", tags_line="tags: []"):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -k "quoted or null_license" -v`
Expected: FAIL — values not requoted

- [ ] **Step 3: Implement**

Add to `format_frontmatter.py` (uses `yaml`, already a dependency):

```python
import yaml


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
        m.group("indent") + m.group("key") + sep + _emit_single_quoted(text_value)
        + comment + m.group("eol")
    )


def requote(entries: list[Entry]) -> None:
    """In place: single-quote the scalar value on each single-line scalar entry.
    Multi-line entries (lists, nested mappings) are left for their own transforms."""
    for entry in entries:
        if entry.key is None or len(entry.lines) != 1:
            continue
        entry.lines[0] = _requote_scalar_line(entry.lines[0], entry.key)
```

In `format_text`, call `requote(entries)` **before** `reorder(...)`:

```python
    requote(entries)
    entries = reorder(entries, warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -k "quoted or null_license" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py
git commit -m "feat(format): single-quote scalar values (null/lists preserved)"
```

### Task A4: List normalization (block style, `[]`, dedupe)

**Files:**
- Modify: `src/project_standards/format_frontmatter.py`
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -k "flow_list or empty_block" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

Add to `format_frontmatter.py`:

```python
def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return "\n"


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
            loaded = yaml.load("".join(entry.lines[lead:]), Loader=yaml.BaseLoader)
        except yaml.YAMLError:
            continue
        if not isinstance(loaded, dict) or entry.key not in loaded:
            continue
        value = loaded[entry.key]
        if not (value is None or value == "" or isinstance(value, list)):
            continue  # a scalar where a list belongs -> leave for the validator
        key_line = entry.lines[lead]
        eol = _line_ending(entry.lines[-1])
        # Indent by slice (NOT re.match(...).group(0), which basedpyright-strict flags — CR-NEW-002).
        indent = key_line[: len(key_line) - len(key_line.lstrip(" \t"))]
        after_colon = key_line.rstrip("\r\n").split(":", 1)[1] if ":" in key_line else ""
        inline = _split_value_comment(after_colon)[1]  # comment after [], [a], or bare key (CR-NEW-004)
        leading = entry.lines[:lead]
        items: list[str] = value if isinstance(value, list) else []
        seen: list[str] = []
        for item in items:
            s = item if isinstance(item, str) else str(item)
            if s not in seen:
                seen.append(s)
        if not seen:
            entry.lines = [*leading, f"{indent}{entry.key}: []{inline}{eol}"]
        else:
            rendered = [f"{indent}{entry.key}:{inline}{eol}"]
            rendered += [f"{indent}  - {_emit_single_quoted(s)}{eol}" for s in seen]
            entry.lines = [*leading, *rendered]
```

In `format_text`, call `normalize_lists(entries)` **before** `requote(entries)`:

```python
    normalize_lists(entries)
    requote(entries)
    entries = reorder(entries, warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -k "flow_list or empty_block" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py
git commit -m "feat(format): normalize lists to block style, dedupe, empty -> []"
```

### Task A5: `type`→`doc_type` rename + inject missing required arrays + `schema_version`

**Files:**
- Modify: `src/project_standards/format_frontmatter.py`
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
def test_type_renamed_to_doc_type_when_absent():
    src = _doc().replace("doc_type: 'note'\n", "type: 'note'\n")
    new, changed, _ = format_text(src, path=None)
    assert "doc_type: 'note'" in new
    assert "\ntype:" not in new
    assert changed is True


def test_both_type_and_doc_type_present_warns_keeps_both():
    src = _doc(extra="type: 'x'\n")
    new, _, warnings = format_text(src, path=None)
    assert "doc_type: 'note'" in new
    assert any("type" in w.lower() for w in warnings)


def test_missing_required_arrays_injected():
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


def test_schema_version_injected_when_missing():
    src = _doc().replace("schema_version: '1.1'\n", "")
    new, _, _ = format_text(src, path=None)
    assert "schema_version: '1.1'" in new
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -k "type_renamed or both_type or required_arrays or schema_version_injected" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

Add to `format_frontmatter.py` (the bundled contract version is read from the schema's own `$id`/version is fixed at `'1.1'` for this contract — sourced from the registry default in production; hard-coded constant here keeps the formatter dependency-free):

```python
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
```

In `format_text`, call these **before** `normalize_lists` (so injected lists get normalized formatting and rename happens before reorder):

```python
    rename_type(entries, warnings)
    inject_defaults(entries)
    normalize_lists(entries)
    requote(entries)
    entries = reorder(entries, warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -k "type_renamed or both_type or required_arrays or schema_version_injected" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py
git commit -m "feat(format): type->doc_type rename, inject schema_version + arrays"
```

### Task A6: Path-based `doc_type` inference (fill/correct-only) + denylist

**Files:**
- Modify: `src/project_standards/format_frontmatter.py`
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
def test_doc_type_filled_from_readme_path_when_missing():
    src = _doc().replace("doc_type: 'note'\n", "")  # no doc_type
    new, _, _ = format_text(src, path=Path("README.md"))
    assert "doc_type: 'index'" in new


def test_doc_type_research_under_docs_research_when_invalid():
    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'bogus'\n")
    new, _, _ = format_text(src, path=Path("docs/research/x.md"))
    assert "doc_type: 'research'" in new


def test_valid_doc_type_never_overridden_by_path():
    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'reference'\n")
    new, _, _ = format_text(src, path=Path("README.md"))
    assert "doc_type: 'reference'" in new   # SA-001: valid value preserved
    assert "doc_type: 'index'" not in new


def test_denylisted_paths_are_refused():
    from project_standards.format_frontmatter import is_denylisted
    assert is_denylisted(Path("CLAUDE.md"))
    assert is_denylisted(Path("sub/AGENTS.md"))
    assert is_denylisted(Path(".claude/settings.md"))
    assert is_denylisted(Path("x/.codex/y.md"))
    assert not is_denylisted(Path("docs/note.md"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -k "doc_type_filled or research_under or never_overridden or denylisted" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
_NEVER_NAMES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
_NEVER_DIRS = {".claude", ".agents", ".codex"}


def is_denylisted(path: Path) -> bool:
    """Files that must NEVER carry frontmatter (harness config). Overrides include
    and scaffold, independent of config — defense-in-depth over consumer exclude."""
    if path.name in _NEVER_NAMES:
        return True
    return any(part in _NEVER_DIRS for part in path.parts)


def _infer_doc_type(path: Path) -> str | None:
    """The standard's path rules. None = no rule applies."""
    posix = path.as_posix()
    if "docs/research/" in posix or posix.startswith("docs/research/"):
        return "research"
    if path.name in ("README.md", "index.md"):
        return "index"
    return None


def infer_doc_type(entries: list[Entry], path: Path | None) -> None:
    """Fill/correct-only (SA-001): set doc_type from the path rule ONLY when the
    current value is missing or not a valid enum value. A valid value is kept."""
    if path is None:
        return
    inferred = _infer_doc_type(path)
    if inferred is None:
        return
    eol = _line_ending(entries[0].lines[-1]) if entries and entries[0].lines else "\n"
    for entry in entries:
        if entry.key == "doc_type":
            current = entry.lines[-1].split(":", 1)[1].strip().strip("'\"")
            if current in VALID_DOC_TYPES:
                return  # valid -> never override
            entry.lines = [f"doc_type: {_emit_single_quoted(inferred)}{eol}"]
            return
    entries.append(_new_scalar_entry("doc_type", inferred, eol))
```

In `format_text`, call `infer_doc_type(entries, path)` **after** `rename_type` and **before** `inject_defaults`. Also guard the whole function: at the top of `format_text`, if `path is not None and is_denylisted(path)`, return `(text, False, ["refused (denylisted): never add frontmatter to this file"])`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -k "doc_type_filled or research_under or never_overridden or denylisted" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py
git commit -m "feat(format): fill/correct-only doc_type inference + denylist"
```

### Task A7: Extension-object opacity + CRLF preservation

**Files:**
- Modify: `src/project_standards/format_frontmatter.py` (no new transform — verify the entry model already preserves them)
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
def test_extension_object_nested_bytes_preserved():
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


def test_crlf_line_endings_preserved():
    src = _doc().replace("\n", "\r\n")
    src = src.replace("title: X\r\n", "title: X\r\n") if "title: X" in src else src
    # Force one change (unquoted) and assert CRLF survives on unchanged lines.
    src = src.replace("title: 'X'\r\n", "title: X\r\n")
    new, changed, _ = format_text(src, path=None)
    assert "\r\n" in new
    assert "\n\n" not in new.replace("\r\n", "")  # no stray bare LFs introduced
    assert "title: 'X'\r\n" in new
```

- [ ] **Step 2: Run test to verify it (likely) fails, then diagnose**

Run: `uv run pytest tests/test_format_frontmatter.py -k "extension_object or crlf" -v`
Expected: the extension test should PASS already (entries carry nested lines opaquely); the CRLF test may FAIL if `requote`/`normalize` lost the `\r`. If so, fix `_line_ending`/regex `eol` capture to retain `\r\n`.

- [ ] **Step 3: Fix any CRLF regressions**

Ensure `_requote_scalar_line`'s `eol` group captures `\r?\n?` and is re-emitted verbatim (already in A3). Ensure `normalize_lists` uses `_line_ending(entry.lines[-1])` per entry. No body re-encoding anywhere — only string concatenation.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -k "extension_object or crlf" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py
git commit -m "test(format): extension-object opacity + CRLF preservation"
```

### Task A8: Scaffold a block into a no-frontmatter file

**Files:**
- Modify: `src/project_standards/format_frontmatter.py`
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing test**

```python
def test_scaffold_injects_schema_valid_block():
    body = "# Real Title\n\nSome content.\n"
    new, changed, _ = format_text(body, path=Path("docs/guide.md"), scaffold=True, today="2026-06-08")
    assert new.startswith("---\n")
    assert "title: 'Real Title'" in new
    assert "doc_type: 'note'" in new          # no path rule -> note
    assert "created: '2026-06-08'" in new and "updated: '2026-06-08'" in new
    assert "description: 'TODO:" in new        # placeholder, schema-valid
    assert "# Real Title" in new               # body preserved
    assert changed is True


def test_scaffold_disabled_leaves_body_untouched():
    body = "# Title\n\nContent.\n"
    new, changed, _ = format_text(body, path=Path("docs/guide.md"), scaffold=False)
    assert new == body and changed is False


def test_scaffold_uses_path_doc_type_rule():
    new, _, _ = format_text("# R\n", path=Path("README.md"), scaffold=True, today="2026-06-08")
    assert "doc_type: 'index'" in new
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -k scaffold -v`
Expected: FAIL — `format_text() got an unexpected keyword argument 'scaffold'`

- [ ] **Step 3: Implement**

Change the `format_text` signature to `format_text(text, *, path, scaffold=False, today=None, bump_updated=False)`. Add the scaffold builder and a `--bump-updated` hook:

```python
from project_standards.id_format import random_token, slugify

_H1_RE = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)


def _build_scaffold(body_text: str, path: Path, today: str) -> str:
    h1 = _H1_RE.search(body_text)
    title = h1.group(1) if h1 else path.stem.replace("-", " ").replace("_", " ").title()
    doc_type = _infer_doc_type(path) or "note"
    slug = slugify(title) or slugify(path.stem) or "untitled"
    new_id = f"{doc_type}-{random_token()}-{slug}"
    return (
        "---\n"
        f"schema_version: {_emit_single_quoted(BUNDLED_SCHEMA_VERSION)}\n"
        f"id: {_emit_single_quoted(new_id)}\n"
        f"title: {_emit_single_quoted(title)}\n"
        "description: 'TODO: one-sentence description.'\n"
        f"doc_type: {_emit_single_quoted(doc_type)}\n"
        "status: 'draft'\n"
        f"created: {_emit_single_quoted(today)}\n"
        f"updated: {_emit_single_quoted(today)}\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
```

In `format_text`, after the denylist guard and the `_FM_RE` match: if `match is None`:

```python
    if match is None:
        if scaffold and path is not None and not is_denylisted(path):
            stamp = today or _today_iso()
            return _build_scaffold(text, path, stamp) + text, True, [
                f"scaffolded: {path} — fill in title/description"
            ]
        return text, False, warnings
```

Add a `_today_iso()` helper that returns `datetime.date.today().isoformat()` (import `datetime`). For the `--bump-updated` path, after computing `new_text`/`changed` for an existing block: if `bump_updated and changed`, replace the `updated:` entry value with `today or _today_iso()` and recompute `new_text`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format_frontmatter.py -k scaffold -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py
git commit -m "feat(format): scaffold schema-valid block into no-frontmatter files"
```

### Task A9: CLI (`main`), `--check`/`--write`/`--stdin`, custom-schema skip, atomic write

**Files:**
- Modify: `src/project_standards/format_frontmatter.py`
- Test: `tests/test_format_frontmatter.py` (append)
- Modify: `pyproject.toml` (ensure console script present from A1)

- [ ] **Step 1: Write the failing test**

```python
import subprocess, sys


def _run(args, **kw):
    return subprocess.run([sys.executable, "-m", "project_standards.format_frontmatter", *args],
                          capture_output=True, text=True, **kw)


def test_check_exits_1_when_would_change(tmp_path):
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 1


def test_write_formats_in_place_atomically(tmp_path):
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    r = _run(["--write", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 0
    assert "title: 'X'" in f.read_text()


def test_stdin_mode_round_trips():
    r = _run(["--stdin"], input=_doc(title="X").replace("title: 'X'", "title: X"))
    assert r.returncode == 0
    assert "title: 'X'" in r.stdout


def test_custom_schema_skips(tmp_path):
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['*.md']\n")
    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 0
    assert "custom schema" in (r.stdout + r.stderr).lower()


@pytest.mark.parametrize("conflict", [["x.md"], ["--glob", "*.md"], ["--write"]])
def test_stdin_conflicts_exit_2(conflict):
    r = _run(["--stdin", *conflict], input="---\ntitle: 'X'\n---\n")
    assert r.returncode == 2
    assert "stdin" in (r.stdout + r.stderr).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_frontmatter.py -k "check_exits or write_formats or stdin_mode or custom_schema_skips" -v`
Expected: FAIL — no `main`/`__main__`

- [ ] **Step 3: Implement the CLI**

```python
import argparse
import os
import sys
import tempfile

from project_standards.validate_frontmatter import (
    ConfigError, collect_paths, load_config, schema_value_is_path,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")


def _atomic_write(path: Path, data: str) -> None:
    """Write atomically AND preserve the original file's permission bits (codex
    missing-consideration): mkstemp creates 0600, so copy the source mode first."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(data)
        try:
            os.chmod(tmp, path.stat().st_mode & 0o777)
        except OSError:
            pass
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="format-frontmatter", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--glob", metavar="PATTERN")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--bump-updated", action="store_true")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args(argv)

    # SA-spec: --stdin reads one document and writes stdout; it is incompatible with a
    # file set or in-place write. Enforce it (parser.error exits 2) — CR-005.
    if args.stdin and (args.files or args.glob or args.write):
        parser.error("--stdin cannot be combined with FILE, --glob, or --write")

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.schema is not None or schema_value_is_path(config.schema):
        if not args.quiet:
            print("note: custom schema in use; skipping frontmatter formatting")
        return 0

    if args.stdin:
        text = sys.stdin.read()
        new, _changed, _warn = format_text(text, path=None, bump_updated=args.bump_updated)
        sys.stdout.write(new)
        return 0

    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
    write = args.write  # default is check-mode
    any_change = False
    unparseable = False
    for path in paths:
        if is_denylisted(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"{path}: cannot read: {exc}", file=sys.stderr)
            unparseable = True
            continue
        new, changed, warnings = format_text(
            text, path=path, scaffold=write, bump_updated=args.bump_updated
        )
        for w in warnings:
            print(f"{path}: {w}", file=sys.stderr)
            # A duplicate-key block is refused (not rewritten) AND must fail the gate (CR-002).
            if "duplicate top-level key" in w:
                unparseable = True
        if changed:
            any_change = True
            if write:
                _atomic_write(path, new)
                if not args.quiet:
                    print(f"formatted: {path}")
            elif not args.quiet:
                print(f"would reformat: {path}")
    if write:
        return 1 if unparseable else 0
    return 1 if (any_change or unparseable) else 0


if __name__ == "__main__":
    sys.exit(main())
```

Ensure the `[project.scripts]` entry from A1 is present, then `uv sync` to register the console script.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv sync && uv run pytest tests/test_format_frontmatter.py -k "check_exits or write_formats or stdin_mode or custom_schema_skips" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/format_frontmatter.py tests/test_format_frontmatter.py pyproject.toml uv.lock
git commit -m "feat(format): CLI (--check/--write/--stdin), custom-schema skip, atomic write"
```

### Task A10: Idempotence property test + dogfood check

**Files:**
- Test: `tests/test_format_frontmatter.py` (append)

- [ ] **Step 1: Write the failing/guard test**

```python
CASES = [
    _doc(title="X").replace("title: 'X'", "title: X"),
    _doc(tags_line="tags: ['b','a','b']"),
    _doc().replace("schema_version: '1.1'\n", ""),
    _doc().replace("doc_type: 'note'\n", "type: 'note'\n"),
]


@pytest.mark.parametrize("src", CASES)
def test_format_is_idempotent(src):
    once, _, _ = format_text(src, path=Path("docs/x.md"))
    twice, changed2, _ = format_text(once, path=Path("docs/x.md"))
    assert twice == once
    assert changed2 is False
```

- [ ] **Step 2: Run test**

Run: `uv run pytest tests/test_format_frontmatter.py -k idempotent -v`
Expected: PASS (4 passed) — fix any transform that is not stable until it does

- [ ] **Step 3: Dogfood the repo**

Run: `uv run format-frontmatter --check --config .project-standards.yml`
Expected: exit 0 (the repo's managed docs are already canonical). If any file would reformat, inspect — a true cleanup is fine to apply with `--write`; a wrongful change is a transform bug to fix.

- [ ] **Step 4: Run the full toolchain gate**

Run the gate command from the top of this plan.
Expected: all green; coverage ≥ 91%.

- [ ] **Step 5: Commit**

```bash
git add tests/test_format_frontmatter.py
git commit -m "test(format): idempotence property + dogfood clean"
```

---

## Phase B — `validate-references`

### Task B1: Repo index + id-uniqueness check + CLI skeleton

**Files:**
- Create: `src/project_standards/validate_references.py`
- Test: `tests/test_validate_references.py`
- Modify: `pyproject.toml` (`validate-references` console script)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate_references.py
from pathlib import Path
from project_standards.validate_references import build_index, check_id_uniqueness


def _write(p: Path, **fm):
    body = "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# B\n"
    p.write_text(body)


def test_duplicate_id_is_error(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'", created="'2026-01-01'", updated="'2026-01-02'")
    _write(tmp_path / "b.md", id="'note-aaaaaa-x'", doc_type="'note'", created="'2026-01-01'", updated="'2026-01-02'")
    index = build_index([tmp_path / "a.md", tmp_path / "b.md"])
    errors = check_id_uniqueness(index)
    assert len(errors) == 1
    assert "note-aaaaaa-x" in errors[0]


def test_unique_ids_no_error(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'", created="'2026-01-01'", updated="'2026-01-02'")
    _write(tmp_path / "b.md", id="'note-bbbbbb-y'", doc_type="'note'", created="'2026-01-01'", updated="'2026-01-02'")
    index = build_index([tmp_path / "a.md", tmp_path / "b.md"])
    assert check_id_uniqueness(index) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate_references.py -v`
Expected: FAIL — module missing

- [ ] **Step 3: Implement the index + first check + CLI**

```python
# src/project_standards/validate_references.py
"""Opt-in cross-file frontmatter checks the JSON Schema cannot express: id
uniqueness, referential integrity, supersede reciprocity, date ordering, ADR
sequence. Repo-wide pass; warnings never fail the build, errors do."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from project_standards.validate_frontmatter import (
    ConfigError, FrontmatterParseError, collect_paths, load_config,
    parse_frontmatter, schema_value_is_path,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")
_REF_FIELDS = ("related", "depends_on", "supersedes", "superseded_by")  # NOT applies_to


@dataclass
class Doc:
    path: Path
    meta: dict[str, Any]


@dataclass
class Index:
    docs: list[Doc] = field(default_factory=list)
    by_id: dict[str, list[Path]] = field(default_factory=dict)
    ids: set[str] = field(default_factory=set)


def build_index(paths: list[Path]) -> Index:
    index = Index()
    for path in paths:
        try:
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, FrontmatterParseError):
            continue
        if not isinstance(meta, dict):
            continue
        doc = Doc(path=path, meta=meta)
        index.docs.append(doc)
        doc_id = meta.get("id")
        if isinstance(doc_id, str) and doc_id:
            index.by_id.setdefault(doc_id, []).append(path)
            index.ids.add(doc_id)
    return index


def check_id_uniqueness(index: Index) -> list[str]:
    errors: list[str] = []
    for doc_id, paths in sorted(index.by_id.items()):
        if len(paths) > 1:
            joined = ", ".join(str(p) for p in sorted(paths))
            errors.append(f"[error] duplicate id '{doc_id}' in: {joined}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-references", description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--glob", metavar="PATTERN")
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not config.references_enabled:
        return 0  # opt-in: disabled -> no checks
    if args.schema is not None or schema_value_is_path(config.schema):
        if not args.quiet:
            print("note: custom schema in use; skipping reference validation")
        return 0

    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
    index = build_index(paths)
    errors: list[str] = []
    warnings: list[str] = []
    errors += check_id_uniqueness(index)
    # B2-B4 append more checks here.

    for w in warnings:
        print(w, file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        print(f"\n✗  {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"✓  references valid ({len(index.docs)} docs, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Add `validate-references = "project_standards.validate_references:main"` to `[project.scripts]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validate_references.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/validate_references.py tests/test_validate_references.py pyproject.toml
git commit -m "feat(references): repo index + id-uniqueness check + CLI skeleton"
```

### Task B2: Date ordering check (`created ≤ updated`, `reviewed ≥ created`)

**Files:**
- Modify: `src/project_standards/validate_references.py`
- Test: `tests/test_validate_references.py` (append)

- [ ] **Step 1: Write the failing test**

```python
from project_standards.validate_references import check_dates, build_index


def test_created_after_updated_is_error(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-02-01'", updated="'2026-01-01'")
    errors = check_dates(build_index([tmp_path / "a.md"]))
    assert any("created" in e and "updated" in e for e in errors)


def test_reviewed_before_created_is_error(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-02-01'", updated="'2026-02-02'", reviewed="'2026-01-01'")
    errors = check_dates(build_index([tmp_path / "a.md"]))
    assert any("reviewed" in e for e in errors)


def test_valid_dates_no_error(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-02-01'", reviewed="'2026-02-02'")
    assert check_dates(build_index([tmp_path / "a.md"])) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate_references.py -k dates -v`
Expected: FAIL — `check_dates` missing

- [ ] **Step 3: Implement**

```python
def check_dates(index: Index) -> list[str]:
    errors: list[str] = []
    for doc in index.docs:
        created = doc.meta.get("created")
        updated = doc.meta.get("updated")
        reviewed = doc.meta.get("reviewed")
        if isinstance(created, str) and isinstance(updated, str) and created > updated:
            errors.append(f"[error] {doc.path}: created '{created}' is after updated '{updated}'")
        if isinstance(reviewed, str) and isinstance(created, str) and reviewed < created:
            errors.append(f"[error] {doc.path}: reviewed '{reviewed}' is before created '{created}'")
    return errors
```

(ISO `YYYY-MM-DD` strings compare correctly lexicographically; `parse_frontmatter` already coerces dates to ISO strings.) Wire `errors += check_dates(index)` in `main`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validate_references.py -k dates -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/validate_references.py tests/test_validate_references.py
git commit -m "feat(references): date-ordering check (created<=updated, reviewed>=created)"
```

### Task B3: Referential integrity (warning) + null/anchor/path rules

**Files:**
- Modify: `src/project_standards/validate_references.py`
- Test: `tests/test_validate_references.py` (append)

- [ ] **Step 1: Write the failing test**

```python
from project_standards.validate_references import check_references, build_index


def test_dangling_reference_is_warning(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'",
           related="['note-zzzzzz-missing']")
    warnings = check_references(build_index([tmp_path / "a.md"]), tmp_path)
    assert len(warnings) == 1
    assert "[warning]" in warnings[0]


def test_reference_to_existing_path_resolves(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "arch.md").write_text("# A\n")
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'",
           related="['docs/arch.md']")
    assert check_references(build_index([tmp_path / "a.md"]), tmp_path) == []


def test_reference_to_known_id_resolves(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'", related="['note-bbbbbb-y']")
    _write(tmp_path / "b.md", id="'note-bbbbbb-y'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'")
    assert check_references(build_index([tmp_path / "a.md", tmp_path / "b.md"]), tmp_path) == []


def test_null_superseded_by_not_flagged(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'", superseded_by="null")
    assert check_references(build_index([tmp_path / "a.md"]), tmp_path) == []


def test_anchor_and_absolute_paths_do_not_resolve(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'",
           related="['docs/arch.md#section', '/abs/x.md']")
    warnings = check_references(build_index([tmp_path / "a.md"]), tmp_path)
    assert len(warnings) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate_references.py -k "reference or null_superseded or anchor" -v`
Expected: FAIL — `check_references` missing

- [ ] **Step 3: Implement**

```python
def _ref_values(meta: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field_name in _REF_FIELDS:
        val = meta.get(field_name)
        if val is None:
            continue
        if isinstance(val, str):
            values.append(val)
        elif isinstance(val, list):
            values.extend(v for v in val if isinstance(v, str) and v)
    return values


def _resolves(ref: str, index: Index, repo_root: Path) -> bool:
    if ref in index.ids:  # exact id match
        return True
    if "#" in ref:  # section anchors are not document references (standard)
        return False
    if ref.startswith("/") or ref.startswith("../") or "/../" in ref:
        return False
    return (repo_root / ref).is_file()


def check_references(index: Index, repo_root: Path) -> list[str]:
    warnings: list[str] = []
    for doc in index.docs:
        for ref in _ref_values(doc.meta):
            if not _resolves(ref, index, repo_root):
                warnings.append(f"[warning] {doc.path}: unresolved reference '{ref}'")
    return warnings
```

Wire in `main`: `warnings += check_references(index, Path.cwd())` (cwd is the repo root for the config-driven run).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validate_references.py -k "reference or null_superseded or anchor" -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/validate_references.py tests/test_validate_references.py
git commit -m "feat(references): referential-integrity warnings (paths/ids, null/anchors)"
```

### Task B4: Supersede reciprocity (warning) + ADR sequence (error)

**Files:**
- Modify: `src/project_standards/validate_references.py`
- Test: `tests/test_validate_references.py` (append)

- [ ] **Step 1: Write the failing test**

```python
from project_standards.validate_references import check_reciprocity, check_adr_sequence, build_index


def test_missing_supersede_reciprocity_warns(tmp_path):
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'", superseded_by="'note-bbbbbb-y'")
    _write(tmp_path / "b.md", id="'note-bbbbbb-y'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'")  # no supersedes back
    warnings = check_reciprocity(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert any("reciprocal" in w or "supersedes" in w for w in warnings)


def test_reverse_supersede_reciprocity_warns(tmp_path):
    # B.supersedes A but A lacks superseded_by -> the OTHER direction (CR-004).
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'")  # no superseded_by back
    _write(tmp_path / "b.md", id="'note-bbbbbb-y'", doc_type="'note'",
           created="'2026-01-01'", updated="'2026-01-02'", supersedes="['note-aaaaaa-x']")
    warnings = check_reciprocity(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert any("superseded_by" in w for w in warnings)


def test_duplicate_adr_number_is_error(tmp_path):
    _write(tmp_path / "a.md", id="'adr-0001-repo-one'", doc_type="'adr'",
           created="'2026-01-01'", updated="'2026-01-02'")
    _write(tmp_path / "b.md", id="'adr-0001-repo-two'", doc_type="'adr'",
           created="'2026-01-01'", updated="'2026-01-02'")
    errors = check_adr_sequence(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert any("0001" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate_references.py -k "reciprocity or adr_number" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
import re as _re

_ADR_NUM_RE = _re.compile(r"^adr-([0-9]{4,})-")


def _as_list(val: Any) -> list[str]:
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [v for v in val if isinstance(v, str)]
    return []


def check_reciprocity(index: Index) -> list[str]:
    """Both directions of the supersede invariant (CR-004): A.superseded_by=B requires
    B.supersedes=A, AND A.supersedes=B requires B.superseded_by=A. Only checked when
    the counterpart doc is local (cross-repo ids can't be inspected)."""
    warnings: list[str] = []
    supersedes_map = {d.meta.get("id"): set(_as_list(d.meta.get("supersedes")))
                      for d in index.docs if isinstance(d.meta.get("id"), str)}
    superseded_by_map = {d.meta.get("id"): set(_as_list(d.meta.get("superseded_by")))
                         for d in index.docs if isinstance(d.meta.get("id"), str)}
    for doc in index.docs:
        a_id = doc.meta.get("id")
        for b_id in _as_list(doc.meta.get("superseded_by")):
            if b_id in supersedes_map and a_id not in supersedes_map[b_id]:
                warnings.append(
                    f"[warning] {doc.path}: '{a_id}' is superseded_by '{b_id}', "
                    f"but '{b_id}' does not list it in supersedes"
                )
        for b_id in _as_list(doc.meta.get("supersedes")):
            if b_id in superseded_by_map and a_id not in superseded_by_map[b_id]:
                warnings.append(
                    f"[warning] {doc.path}: '{a_id}' supersedes '{b_id}', "
                    f"but '{b_id}' does not list it in superseded_by"
                )
    return warnings


def check_adr_sequence(index: Index) -> list[str]:
    by_num: dict[str, list[str]] = {}
    for doc in index.docs:
        if doc.meta.get("doc_type") != "adr":
            continue
        doc_id = doc.meta.get("id")
        if not isinstance(doc_id, str):
            continue
        m = _ADR_NUM_RE.match(doc_id)
        if m:
            by_num.setdefault(m.group(1), []).append(doc_id)
    return [
        f"[error] duplicate ADR number {num}: {', '.join(sorted(ids))}"
        for num, ids in sorted(by_num.items()) if len(ids) > 1
    ]
```

Wire both in `main`: `warnings += check_reciprocity(index)` and `errors += check_adr_sequence(index)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validate_references.py -k "reciprocity or adr_number" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit + dogfood**

```bash
uv sync
# enable references on a scratch config to dogfood this repo:
uv run validate-references --config .project-standards.yml || true   # disabled by default -> exit 0
git add src/project_standards/validate_references.py tests/test_validate_references.py uv.lock
git commit -m "feat(references): supersede reciprocity (warn) + ADR sequence (error)"
```

### Task B5: Compatibility flags + opt-in gate tests

**Files:**
- Test: `tests/test_validate_references.py` (append)

- [ ] **Step 1: Write the test**

```python
import subprocess, sys


def _run_refs(args, cwd):
    return subprocess.run([sys.executable, "-m", "project_standards.validate_references", *args],
                          capture_output=True, text=True, cwd=cwd)


def test_disabled_by_default_exits_0(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    _write(tmp_path / "a.md", id="'note-aaaaaa-x'", doc_type="'note'",
           created="'2026-02-01'", updated="'2026-01-01'")  # bad dates, but disabled
    r = _run_refs(["--config", str(cfg)], tmp_path)
    assert r.returncode == 0


def test_forwarded_schema_flag_skips_not_errors(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n")
    r = _run_refs(["--schema", "custom.json", "--quiet", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0


def test_no_require_frontmatter_is_accepted(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n")
    r = _run_refs(["--no-require-frontmatter", "--quiet", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0
```

- [ ] **Step 2: Run test**

Run: `uv run pytest tests/test_validate_references.py -k "disabled_by_default or forwarded_schema or no_require" -v`
Expected: PASS (3 passed) — these exercise the flags already added in B1; fix the parser if any flag errors

- [ ] **Step 3: Toolchain gate**

Run the full gate command. Expected: green; coverage ≥ 91%.

- [ ] **Step 4: Commit**

```bash
git add tests/test_validate_references.py
git commit -m "test(references): opt-in gate + forwarded-flag compatibility"
```

---

## Phase C — Ergonomics

### Task C1: `project-standards validate` also runs references

**Files:**
- Modify: `src/project_standards/cli.py` (the `validate` early-dispatch at lines 136-185)
- Test: `tests/test_cli_fix.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_fix.py
import subprocess, sys
from pathlib import Path


def _ps(args, cwd):
    return subprocess.run([sys.executable, "-m", "project_standards.cli", *args],
                          capture_output=True, text=True, cwd=cwd)


def _doc(p: Path, **fm):
    p.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# B\n")


def test_validate_runs_references_when_enabled(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n")
    # duplicate id -> references error -> validate must fail
    _doc(tmp_path / "a.md", schema_version="'1.1'", id="'note-aaaaaa-x'", title="'A'",
         description="'d'", doc_type="'note'", status="'draft'", created="'2026-01-01'",
         updated="'2026-01-02'", tags="[]", aliases="[]", related="[]")
    _doc(tmp_path / "b.md", schema_version="'1.1'", id="'note-aaaaaa-x'", title="'B'",
         description="'d'", doc_type="'note'", status="'draft'", created="'2026-01-01'",
         updated="'2026-01-02'", tags="[]", aliases="[]", related="[]")
    r = _ps(["validate", "--config", str(cfg)], tmp_path)
    assert r.returncode == 1
    assert "duplicate id" in (r.stdout + r.stderr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_fix.py -k validate_runs_references -v`
Expected: FAIL — references not run by `validate`

- [ ] **Step 3: Implement**

In `cli.py`, add `validate_references` to the imports:

```python
from project_standards import validate_frontmatter, validate_id, validate_references
```

In the `validate` early-dispatch (after computing `rc_frontmatter` and `rc_id`), add:

```python
        rc_refs = validate_references.main(validator_args)
        return max(rc_frontmatter, rc_id, rc_refs)
```

(`validate_references.main` self-gates on `references_enabled`, so this is a no-op when disabled — preserving current behavior.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_fix.py -k validate_runs_references -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/cli.py tests/test_cli_fix.py
git commit -m "feat(cli): validate also runs validate-references (self-gated)"
```

### Task C2: `project-standards fix` subcommand (format → id-fix → final validate)

**Files:**
- Modify: `src/project_standards/cli.py`
- Test: `tests/test_cli_fix.py` (append)

- [ ] **Step 1: Write the failing test**

```python
def test_fix_leaves_validate_clean_for_type_and_bad_id(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    # `type` instead of doc_type AND an invalid id: format fixes doc_type, then id-fix fixes id.
    (tmp_path / "a.md").write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'wrong'\n"
        "title: 'Hello World'\n"
        "description: 'd'\n"
        "type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-02'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# B\n"
    )
    r = _ps(["fix", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0
    text = (tmp_path / "a.md").read_text()
    assert "doc_type: 'note'" in text
    assert "id: 'note-" in text  # id regenerated from doc_type+title
    # postcondition: a follow-up validate is clean
    assert _ps(["validate", "--config", str(cfg)], tmp_path).returncode == 0


def _full(did="a", doc_id="note-aaaaaa-x"):
    return (
        "---\n"
        "schema_version: '1.1'\n"
        f"id: '{doc_id}'\n"
        f"title: '{did}'\n"
        "description: 'd'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-02'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# B\n"
    )


def test_fix_fails_on_reference_error_when_enabled(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n")
    # Both docs are schema-valid and id-valid, but share an id -> ONLY a reference error.
    (tmp_path / "a.md").write_text(_full("a"))
    (tmp_path / "b.md").write_text(_full("b"))  # same id -> duplicate
    r = _ps(["fix", "--config", str(cfg)], tmp_path)
    assert r.returncode == 1  # CR-001: final validate (incl. references) catches the dup id


def test_fix_skips_under_custom_schema(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['*.md']\n")
    before = "---\ntitle: X\n---\n# B\n"
    (tmp_path / "a.md").write_text(before)
    r = _ps(["fix", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "a.md").read_text() == before  # CR-001: no writes under custom schema


def test_fix_skips_with_schema_flag(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    before = "---\ntitle: X\n---\n# B\n"
    (tmp_path / "a.md").write_text(before)
    r = _ps(["fix", "--schema", "custom.json", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "a.md").read_text() == before  # CR-001: forwarded --schema -> skip


def test_validate_fails_on_duplicate_keys(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    (tmp_path / "a.md").write_text(
        "---\nschema_version: '1.1'\nid: 'note-aaaaaa-x'\ntitle: 'A'\n"
        "description: 'd'\ndoc_type: 'note'\nstatus: 'draft'\ncreated: '2026-01-01'\n"
        "updated: '2026-01-02'\ntags: []\ntags: ['dup']\naliases: []\nrelated: []\n---\n# B\n"
    )
    r = _ps(["validate", "--config", str(cfg)], tmp_path)
    assert r.returncode == 1  # CR-002: duplicate key -> parse error -> validate fails
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_fix.py -k fix_leaves_validate_clean -v`
Expected: FAIL — `fix` is not a subcommand

- [ ] **Step 3: Implement**

In `cli.py`, add `format_frontmatter` to imports (alongside `validate_references` from C1), add a small `--config` extractor, and add an early-dispatch for `fix` mirroring `validate` (place it right after the `validate` block, before the argparse parser is built):

```python
from pathlib import Path  # if not already imported


def _extract_config_path(args: list[str]) -> Path:
    """Pull the --config value out of a forwarded argv (default .project-standards.yml)."""
    for i, a in enumerate(args):
        if a == "--config" and i + 1 < len(args):
            return Path(args[i + 1])
        if a.startswith("--config="):
            return Path(a.split("=", 1)[1])
    return Path(".project-standards.yml")


def _has_schema_flag(args: list[str]) -> bool:
    """True if a forwarded argv passes --schema (custom-schema mode) — CR-001."""
    return any(a == "--schema" or a.startswith("--schema=") for a in args)
```

```python
    if args_list and args_list[0] == "fix":
        fix_args = args_list[1:]
        if "--help" in fix_args or "-h" in fix_args:
            print("usage: project-standards fix [FILE ...] [--config PATH] [--glob PATTERN] [--quiet]\n"
                  "Format frontmatter (--write), fix ids, then re-validate (incl. references).\n"
                  "Skips entirely under a custom schema.")
            return 0
        # Custom-schema preflight (CR-001): fix is bundled-only, like format/validate-id.
        try:
            fix_cfg = validate_frontmatter.load_config(_extract_config_path(fix_args))
        except validate_frontmatter.ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if _has_schema_flag(fix_args) or validate_frontmatter.schema_value_is_path(fix_cfg.schema):
            print("note: custom schema in use; skipping fix", file=sys.stderr)
            return 0
        rc_format = format_frontmatter.main(["--write", *fix_args])
        rc_idfix = validate_id.main(["--fix", *fix_args])
        # Final postcondition = the SAME contract as `project-standards validate`,
        # references included, so a "successful" fix cannot hide a reference error (CR-001).
        rc_check = max(
            validate_frontmatter.main(fix_args),
            validate_id.main(fix_args),
            validate_references.main(fix_args),
        )
        return max(rc_format, rc_idfix, rc_check)
```

Register a `fix` subparser (for `--help` advertising) alongside the `validate` one:

```python
    sub.add_parser("fix", help="format frontmatter + fix ids, then re-validate")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_fix.py -k fix_leaves_validate_clean -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/cli.py tests/test_cli_fix.py
git commit -m "feat(cli): project-standards fix (format -> id-fix -> final validate)"
```

### Task C3: Reusable workflow runs `validate-references`

**Files:**
- Modify: `.github/workflows/validate-markdown-frontmatter.yml`
- Test: `tests/test_precommit_hooks.py` (create — also used by C4)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_precommit_hooks.py
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[1]


def test_workflow_invokes_validate_references():
    wf = (REPO / ".github/workflows/validate-markdown-frontmatter.yml").read_text()
    assert "validate-references" in wf
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_precommit_hooks.py -k workflow -v`
Expected: FAIL — workflow has no references step

- [ ] **Step 3: Implement**

In `.github/workflows/validate-markdown-frontmatter.yml`, mirror the existing `validate-id` steps with a `validate-references` step for both branches (the `github.repository == 'L3DigitalNet/project-standards'` `uv run` branch and the consumer `uvx`/installed branch). Example (internal branch):

```yaml
      - name: Validate references
        if: github.repository == 'L3DigitalNet/project-standards'
        run: uv run validate-references --config "${{ inputs.config-path || '.project-standards.yml' }}"
```

And the consumer branch:

```yaml
      - name: Validate references
        if: github.repository != 'L3DigitalNet/project-standards'
        run: validate-references --config "${{ inputs.config-path || '.project-standards.yml' }}"
```

(`validate-references` self-gates on `references.enabled`, so it is a no-op exit 0 unless the consumer opted in.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_precommit_hooks.py -k workflow -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/validate-markdown-frontmatter.yml tests/test_precommit_hooks.py
git commit -m "feat(ci): reusable workflow runs validate-references (self-gated)"
```

### Task C4: `.pre-commit-hooks.yaml`

**Files:**
- Create: `.pre-commit-hooks.yaml`
- Test: `tests/test_precommit_hooks.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import tomllib


def test_hook_entries_map_to_console_scripts():
    hooks = yaml.safe_load((REPO / ".pre-commit-hooks.yaml").read_text())
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["scripts"]
    ids = {h["id"] for h in hooks}
    assert {"format-frontmatter-fix", "format-frontmatter-check",
            "validate-frontmatter", "validate-references"} <= ids
    for h in hooks:
        # entry's first token is the console-script name
        assert h["entry"].split()[0] in scripts
        assert h["language"] == "python"


def test_references_hook_runs_whole_repo():
    hooks = {h["id"]: h for h in yaml.safe_load((REPO / ".pre-commit-hooks.yaml").read_text())}
    assert hooks["validate-references"]["pass_filenames"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_precommit_hooks.py -k "hook_entries or whole_repo" -v`
Expected: FAIL — file missing

- [ ] **Step 3: Implement**

```yaml
# .pre-commit-hooks.yaml — consumers reference this repo + a pinned rev.
# Per-file hooks take staged markdown; validate-references needs the whole repo.
- id: format-frontmatter-fix
  name: format frontmatter (write)
  entry: format-frontmatter --write
  language: python
  language_version: python3.14
  types: [markdown]
- id: format-frontmatter-check
  name: format frontmatter (check)
  entry: format-frontmatter --check
  language: python
  language_version: python3.14
  types: [markdown]
- id: validate-id-fix
  name: validate id (fix)
  entry: validate-id --fix
  language: python
  language_version: python3.14
  types: [markdown]
- id: validate-id-check
  name: validate id (check)
  entry: validate-id
  language: python
  language_version: python3.14
  types: [markdown]
- id: validate-frontmatter
  name: validate frontmatter schema
  entry: validate-frontmatter
  language: python
  language_version: python3.14
  types: [markdown]
- id: validate-references
  name: validate cross-file references
  entry: validate-references
  language: python
  language_version: python3.14
  types: [markdown]
  pass_filenames: false
```

- [ ] **Step 4: Run tests + validate the manifest (works on the untracked file)**

Run: `uv run pytest tests/test_precommit_hooks.py -k "hook_entries or whole_repo" -v`
Expected: PASS

`validate-manifest` reads the explicit local path, so it works before the file is tracked. `pre-commit` is not a repo dependency, so `uvx` runs it without declaring one:
```bash
uvx pre-commit validate-manifest .pre-commit-hooks.yaml
```
Expected: manifest valid.

- [ ] **Step 5: Commit (so `try-repo` can see the manifest)**

```bash
git add .pre-commit-hooks.yaml tests/test_precommit_hooks.py
git commit -m "feat(pre-commit): ship .pre-commit-hooks.yaml (fix + check ids)"
```

- [ ] **Step 6: Smoke-test the hook via `try-repo` (AFTER the commit)**

`try-repo` clones the repo's **tracked** state, so a newly created untracked manifest would be invisible — it must run after Step 5's commit (CR-006):
```bash
uvx pre-commit try-repo . format-frontmatter-check --all-files
```
Expected: the check hook installs (against Python 3.14 per `language_version`) and runs.

### Task C5: Documentation + final gate

**Files:**
- Modify: `standards/markdown-frontmatter/README.md`, `standards/markdown-frontmatter/adopt.md`, `src/project_standards/README.md`, `CHANGELOG.md`

- [ ] **Step 1: Update the standard docs**

Document `format-frontmatter` (modes, transforms, denylist, scaffold), `validate-references` (opt-in config + checks), `project-standards fix`, and the pre-commit hooks. Add a `references` block to the adopt.md config example. Add a dated `CHANGELOG.md` entry under a new `2.1.0` heading covering the formatter + references + fix + adopt CLI + validate-id.

- [ ] **Step 2: Dogfood + full gate**

Run:
```bash
uv run format-frontmatter --check --config .project-standards.yml
uv run project-standards validate --config .project-standards.yml
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```
Expected: all green; coverage ≥ 91%; `format-frontmatter --check` clean on the repo.

- [ ] **Step 3: Commit**

```bash
git add standards/markdown-frontmatter/README.md standards/markdown-frontmatter/adopt.md src/project_standards/README.md CHANGELOG.md
git commit -m "docs: document frontmatter formatter, references, and fix for 2.1.0"
```

> **Release (E3) is a separate, user-gated step** — version bump + `uv.lock` + dated changelog in one commit, signed tag `v2.1.0`, move `v2`, update `deployed.md`. Do NOT cut the release as part of this plan; it ships once the whole suite (this plan) plus the already-implemented adopt CLI + validate-id are green and the user gives the go.

---

## Self-review

**Spec coverage:** A (tokenizer A1, reorder A2, quoting A3, lists A4, rename/inject A5, inference+denylist A6, extension/CRLF A7, scaffold A8, CLI+custom-schema+atomic A9, idempotence+dogfood A10) ✓ · B (id-uniqueness B1, dates B2, references B3, reciprocity+ADR B4, flags/opt-in B5) ✓ · C (validate-extension C1, fix C2, workflow C3, pre-commit C4, docs C5) ✓ · Decisions 1–14 + SA-001…008 + SA-NEW-001…003 each map to a task. Phase 0 resolves the shared-`slugify` open question.

**Placeholder scan:** no TBD/TODO-as-instruction; the only literal `TODO:` is the scaffold placeholder *string* (intended output). Every code step shows real code; every command shows expected result.

**Type consistency:** `format_text(text, *, path, scaffold=False, today=None, bump_updated=False) -> (str, bool, list[str])` is consistent A1→A10 and C2. `Entry(key, lines)`, `Index(docs, by_id, ids)`, `Doc(path, meta)` are used consistently. Check names: `build_index`, `check_id_uniqueness`, `check_dates`, `check_references`, `check_reciprocity`, `check_adr_sequence` — all referenced consistently in B and C. `is_denylisted`, `_infer_doc_type`, `_emit_single_quoted`, `_line_ending` consistent across A tasks. The custom-schema predicate is the **public** `schema_value_is_path` (Task 0.4) everywhere.

**Codex plan-review round 1 applied (CR-001…006):** CR-001 — `fix` final postcondition now calls all three validators (incl. references) + a custom-schema preflight (C2). CR-002 — tokenizer refuses duplicate top-level keys (A1) and the `_doc` fixtures no longer create duplicate `tags:`. CR-003 — `schema_value_is_path` made public (Task 0.4) so no private import / `# pyright: ignore` in production. CR-004 — `check_reciprocity` checks both directions. CR-005 — `--stdin` mutual exclusions enforced (exit 2). CR-006 — pre-commit smoke runs via `uvx`. Plus: atomic write preserves mode bits; list-key inline comments preserved.

**Codex plan-review round 2 applied (CR-NEW-001/002, CR-001/002 fully):** CR-NEW-001 — the formatter no longer round-trips values through PyYAML's type resolver; scalars quote raw text and lists load via `yaml.BaseLoader`, so `on`/`off`/`yes`/`no`/`1.1` keep their literal characters (tests added for scalars and list items). CR-NEW-002 — `normalize_lists` derives indent by string slice, not `re.match(...).group(0)`, avoiding the strict-basedpyright optional-match deref. CR-001 (full) — `fix` now also skips on a forwarded `--schema` flag. CR-002 (full) — new Task 0.5 makes `parse_frontmatter` reject duplicate keys (so `validate`/`fix` error), the formatter also fails the gate on them, with CLI tests proving duplicates cannot pass.

**Codex plan-review round 3 applied (CR-NEW-003/004, CR-006 full):** CR-NEW-003 — scalar requoting now splits the inline comment only at a real whitespace-`#` boundary via `_split_value_comment`, so `C# guide` and `http://x/#frag` are preserved (tests added). CR-NEW-004 — `normalize_lists` reuses the same splitter, so comments on `tags: [] # keep` / `tags: [a] # keep` survive (tests added). CR-006 (full) — `try-repo` runs after the manifest is committed (it clones tracked state); `validate-manifest` stays pre-commit.

**Codex plan-review round 4 — converged (verdict: needs minor):** 10/10 prior issues resolved, 0 regressions. Applied the one residual non-blocking fix: CR-NEW-005 — `_split_value_comment` is now bracket/quote-aware so a `#` inside a quoted flow-list item (`source: ['Issue #123']`) is not misread as a comment (tests added). No blocking findings remain across four plan-review rounds.
