# Project-Spec Tooling (Spec #2) — `spec new` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `project-standards spec new` — a guarded-generative command that scaffolds a conformant spec from a chosen profile, so the first file the tool writes already passes `validate`.

**Architecture:** A new `src/project_standards/specs/commands/new.py` holds pure, injectable helpers (`emit_scalar`, `check_field`, `mint_spec_id`, `scaffold`) plus `NewOptions`. `config.py` gains a tolerant `collect_existing_spec_ids`. The impure file-writing shell (`_run_new`) lives in `specs/cli.py`, wired into the existing `_VERBS` dispatch behind a JSON-aware argument parser. Every nondeterministic input (today's date, the RNG, the existing-id set) is resolved in the shell and passed into the pure core.

**Tech Stack:** Python ≥3.14, `uv_build`, PyYAML, pytest + coverage (branch, `fail_under=85`), Ruff, BasedPyright strict. No new runtime dependencies.

## Global Constraints

- Python `>=3.14`; Ruff `target-version = py314`, line-length 100, double quotes, space indent.
- No new runtime dependencies (PyYAML + stdlib only). No new `[project.scripts]` entry point — `new` is a verb of the existing `spec` group.
- Exit codes: `0` ok · `2` any refusal/usage/validation failure. **`new` never returns exit 1** (exit 1 is reserved for `validate`/`lint` findings). Never a traceback, and never a bare argparse `SystemExit`, on bad input.
- Output must pass `validate` as a runtime post-condition (fail-closed self-validation) — spec invariant **I1**. A parse failure of the generated text also maps to `self_validation_failed`, never the outer group's exit-1 parse path.
- `--json` is mandatory on **every** outcome, **including argparse-level failures** (README §5 universal contract) — invariant **I7**. In `--json` mode stdout carries exactly one JSON object and nothing else.
- Writes are atomic (temp file + `os.replace`); symlink targets, non-regular targets, and symlinked parent directories are refused; file mode mirrors `adopt/engine._atomic_write` (preserve on overwrite, umask-respecting `0o666` for new); the write guarantee is scoped to the destination file (**I8**).
- The `--json` `code` slug set is frozen by the spec: `usage`, `exists`, `not_regular_file`, `symlinked_parent`, `flag_conflict`, `bad_id`, `id_collision`, `bad_field_value`, `id_exhausted`, `config_error`, `mkdir_failed`, `write_failed`, `self_validation_failed`.
- Every task ends green on the full gate: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`. **Run `ruff check` + `basedpyright` after every task that adds tests**, not only at the end.
- Spec reference: `docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md`.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `src/project_standards/specs/commands/new.py` | Pure core: `NewOptions`, `emit_scalar`, `check_field`, `mint_spec_id`, `scaffold` + typed errors `FieldValueError`, `SpecIdExhausted`. No I/O. |
| `src/project_standards/specs/config.py` | Add `collect_existing_spec_ids(cfg)` — tolerant discovery for the collision set. |
| `src/project_standards/specs/cli.py` | Add `_run_new` shell, `NewError`, the JSON-aware `_NewArgParser`; register `"new"` in `_VERBS`; update `_USAGE`. |
| `src/project_standards/cli.py` | Update the top-level `spec` help string to mention `new`. |
| `tests/test_spec_new.py` | Unit tests for the pure core. |
| `tests/test_spec_new_discovery.py` | Unit tests for `collect_existing_spec_ids`. |
| `tests/test_spec_new_cli.py` | CLI/integration tests (flag matrix, write safety, file mode, `--json` slug matrix, dogfood). |

---

## Task 1: Value grammar + YAML-safe emission (`emit_scalar`, `check_field`)

**Files:**

- Create: `src/project_standards/specs/commands/new.py`
- Create: `tests/test_spec_new.py`

**Interfaces:**

- Produces:
  - `FieldValueError(ValueError)` — a `--title`/`--owner`/`--implementer` value violates the grammar.
  - `check_field(flag: str, value: str, *, is_title: bool) -> None` — raises `FieldValueError` on empty, control chars, or (title only) a backtick.
  - `emit_scalar(value: str) -> str` — a single-quoted, YAML-safe scalar with no trailing newline.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec_new.py
"""Unit tests for the pure `spec new` core (no I/O, injected nondeterminism)."""

from __future__ import annotations

import pytest
import yaml

from project_standards.specs.commands.new import (
    FieldValueError,
    check_field,
    emit_scalar,
)


@pytest.mark.parametrize("value", ["O'Brien", "Ratio 1:2", "weight #1", "café", "a `b`", "  spaced  "])
def test_emit_scalar_round_trips(value: str) -> None:
    rendered = emit_scalar(value)
    assert yaml.safe_load(f"x: {rendered}") == {"x": value}


@pytest.mark.parametrize("value", ["", "line\none", "tab\there", "cr\rhere"])
def test_check_field_rejects_bad_values(value: str) -> None:
    with pytest.raises(FieldValueError):
        check_field("owner", value, is_title=False)


def test_check_field_title_rejects_backtick_but_owner_allows_it() -> None:
    with pytest.raises(FieldValueError):
        check_field("title", "Use `uv`", is_title=True)
    check_field("owner", "team `core`", is_title=False)  # no raise


def test_check_field_accepts_ordinary_values() -> None:
    check_field("title", "Checkout Service", is_title=True)
    check_field("implementer", "coding agent", is_title=False)
```

Import only what this task uses (`pytest`, `yaml`, the three names under test). Tasks 2 and 4 add `import random`/`import re` and `from datetime import date` to this top block as they introduce the tests that use them — each import lands with its first consumer, so every task stays free of both unused-import (F401) and E402.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spec_new.py -v`
Expected: FAIL with `ModuleNotFoundError: project_standards.specs.commands.new`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/project_standards/specs/commands/new.py
"""Pure core for the guarded-generative `spec new` command.

Every function here is deterministic given its arguments — the date, the RNG, and
the existing-id set are injected by the cli.py shell, never read internally — so the
scaffold logic is unit-testable without a clock, RNG seed, or filesystem. The impure
file-writing shell lives in project_standards.specs.cli._run_new.
"""

from __future__ import annotations

import re

import yaml

# C0 (U+0000–U+001F) and C1 (U+007F–U+009F) control ranges. A newline or other control
# character in a flag value would corrupt the emitted frontmatter line, so reject early.
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class FieldValueError(ValueError):
    """A --title/--owner/--implementer value violates the accepted grammar (exit 2)."""


def check_field(flag: str, value: str, *, is_title: bool) -> None:
    if value == "":
        raise FieldValueError(f"--{flag} must not be empty")
    if _CONTROL.search(value):
        raise FieldValueError(f"--{flag} must not contain control characters")
    # Owner/implementer land only in YAML frontmatter (emit_scalar makes any char safe);
    # the title is ALSO substituted into the H1 Markdown code span (# `<title>` — ...),
    # where a backtick would break the span, so only --title excludes it.
    if is_title and "`" in value:
        raise FieldValueError("--title must not contain a backtick (it lands in the H1 code span)")


def emit_scalar(value: str) -> str:
    """Render a string as a single-quoted YAML scalar, matching the template style.

    Delegated to PyYAML rather than hand-quoted so apostrophes, colons, '#', backticks,
    and non-ASCII are escaped correctly. width is set very high to prevent line folding
    of long values inside a frontmatter line.
    """
    dumped = yaml.safe_dump(value, default_style="'", allow_unicode=True, width=1_000_000)
    return dumped.strip()
```

`new.py` imports only what Task 1 uses (`re`, `yaml`). Task 2 adds `import random` and `from collections.abc import Container` to this top block; Task 4 adds `from dataclasses import dataclass` and `from datetime import date`. Each import arrives with its first consumer, so Task 1 stays free of unused-import (F401) warnings under the strict gate.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_new.py -v && uv run ruff check src/project_standards/specs/commands/new.py tests/test_spec_new.py && uv run basedpyright src/project_standards/specs/commands/new.py tests/test_spec_new.py`
Expected: tests PASS; Ruff and BasedPyright clean.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/new.py tests/test_spec_new.py
git commit -m "feat(spec): value grammar + YAML-safe scalar emission for spec new"
```

---

## Task 2: Bounded `spec_id` minting

**Files:**

- Modify: `src/project_standards/specs/commands/new.py`
- Modify: `tests/test_spec_new.py`

**Interfaces:**

- Produces:
  - `SpecIdExhausted(RuntimeError)` — minting hit the attempt cap.
  - `mint_spec_id(rng: random.Random, existing_ids: Container[str], *, attempts: int = 1000) -> str` — a fresh `SPEC-XXXX` not in `existing_ids`.

- [ ] **Step 1: Write the failing test**

```python
# 1) Merge into the TOP import block of tests/test_spec_new.py — never below code (E402).
#    Ruff sorts them among the existing imports:
import random
import re

from project_standards.specs.commands.new import SpecIdExhausted, mint_spec_id
from project_standards.specs.registry import SPEC_ID_PATTERN


# 2) Append these test functions to the end of the file:
def test_mint_matches_pattern_and_is_deterministic_per_seed() -> None:
    first = mint_spec_id(random.Random(0), set())
    again = mint_spec_id(random.Random(0), set())
    assert re.match(SPEC_ID_PATTERN, first)
    assert first == again  # same seed, same id -> injected RNG is the only nondeterminism


def test_mint_retries_past_a_collision() -> None:
    taken = mint_spec_id(random.Random(0), set())
    other = mint_spec_id(random.Random(0), {taken})
    assert other != taken
    assert re.match(SPEC_ID_PATTERN, other)


def test_mint_exhaustion_raises() -> None:
    # Reproduce the seed-0 first candidate, then demand a fresh id in exactly 1 attempt
    # while that id is already taken -> the single attempt collides -> exhausted.
    taken = mint_spec_id(random.Random(0), set())
    with pytest.raises(SpecIdExhausted):
        mint_spec_id(random.Random(0), {taken}, attempts=1)
```

Using a real `random.Random` (not a hand-rolled stub) keeps the call type-correct under BasedPyright strict — no fake-RNG protocol needed.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spec_new.py -k mint -v`
Expected: FAIL with `ImportError: cannot import name 'mint_spec_id'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/project_standards/specs/commands/new.py
# first add to the top import block: `import random` and `from collections.abc import Container`

_ID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # base36, matching ^SPEC-[0-9A-Z]{4}$
_MINT_ATTEMPTS = 1000


class SpecIdExhausted(RuntimeError):
    """mint_spec_id could not find a free id within the attempt cap (advise --id)."""


def mint_spec_id(
    rng: random.Random, existing_ids: Container[str], *, attempts: int = _MINT_ATTEMPTS
) -> str:
    for _ in range(attempts):
        candidate = "SPEC-" + "".join(rng.choice(_ID_ALPHABET) for _ in range(4))
        if candidate not in existing_ids:
            return candidate
    raise SpecIdExhausted(
        f"could not mint a unique spec_id in {attempts} attempts; pass --id SPEC-XXXX"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_new.py -k mint -v && uv run ruff check src/project_standards/specs/commands/new.py tests/test_spec_new.py && uv run basedpyright src/project_standards/specs/commands/new.py tests/test_spec_new.py`
Expected: tests PASS; Ruff and BasedPyright clean.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/new.py tests/test_spec_new.py
git commit -m "feat(spec): bounded-retry spec_id minting"
```

---

## Task 3: Tolerant discovery — `collect_existing_spec_ids`

**Files:**

- Modify: `src/project_standards/specs/config.py`
- Create: `tests/test_spec_new_discovery.py`

**Interfaces:**

- Consumes: `SpecConfig`, `collect_spec_paths`, `DiscoveryError`, `ConfigError` (this module); `parse_document`, `SpecParseError` (document module).
- Produces: `collect_existing_spec_ids(cfg: SpecConfig) -> set[str]` — the spec_ids already used in the repo, tolerating an empty corpus but propagating real config errors.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec_new_discovery.py
"""collect_existing_spec_ids: tolerant of an empty corpus, strict on broken config."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs import config as cfgmod
from project_standards.specs.config import (
    ConfigError,
    SpecConfig,
    collect_existing_spec_ids,
    load_spec_config,
)


def _cfg(tmp: Path, body: str) -> SpecConfig:
    p = tmp / ".project-standards.yml"
    p.write_text(body, encoding="utf-8")
    return load_spec_config(p)


def test_no_spec_block_yields_empty_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert collect_existing_spec_ids(_cfg(tmp_path, "markdown:\n  frontmatter: {}\n")) == set()


def test_zero_match_include_yields_empty_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = _cfg(tmp_path, "spec:\n  include:\n    - docs/specs/**/*.md\n")
    assert collect_existing_spec_ids(cfg) == set()


def test_collects_ids_and_skips_malformed_neighbor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "good.md").write_text(
        "---\nspec_id: SPEC-7F3Q\n---\n# t\n", encoding="utf-8"
    )
    # Unterminated frontmatter fence -> SpecParseError -> skipped, not fatal.
    (tmp_path / "docs" / "bad.md").write_text(
        "---\nspec_id: SPEC-9Z9Z\n# no close\n", encoding="utf-8"
    )
    cfg = _cfg(tmp_path, "spec:\n  include:\n    - docs/*.md\n")
    assert collect_existing_spec_ids(cfg) == {"SPEC-7F3Q"}


def test_non_discovery_configerror_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only DiscoveryError becomes an empty set; every OTHER ConfigError still propagates.
    def _boom(explicit: list[Path], cfg: SpecConfig) -> list[Path]:
        raise ConfigError("boom")

    monkeypatch.setattr(cfgmod, "collect_spec_paths", _boom)
    with pytest.raises(ConfigError):
        collect_existing_spec_ids(SpecConfig(include=["x"], exclude=[], present=True))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spec_new_discovery.py -v`
Expected: FAIL with `ImportError: cannot import name 'collect_existing_spec_ids'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/project_standards/specs/config.py
# new import at the top (grouped with the existing imports):
#   from project_standards.specs.document import SpecParseError, parse_document


def collect_existing_spec_ids(cfg: SpecConfig) -> set[str]:
    """Best-effort set of spec_ids already used in the repo, for `new`'s collision check.

    Unlike collect_spec_paths (which raises DiscoveryError on an empty corpus so
    validate/lint never pass vacuously), `new` MUST tolerate an empty corpus — a repo
    legitimately has zero specs before the first `new`. So a DiscoveryError becomes an
    empty set, while every OTHER ConfigError (unreadable / unparseable config) still
    propagates and the shell maps it to exit 2. A spec that cannot be parsed is skipped,
    so duplicate detection is best-effort over the parseable corpus.
    """
    try:
        paths = collect_spec_paths([], cfg)
    except DiscoveryError:
        return set()
    ids: set[str] = set()
    for path in paths:
        try:
            doc = parse_document(str(path), path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SpecParseError):
            continue
        spec_id = doc.frontmatter.get("spec_id")
        if spec_id:
            ids.add(spec_id)
    return ids
```

Add `from project_standards.specs.document import SpecParseError, parse_document` to `config.py`'s import block. This is acyclic: `document` imports only `registry` + `model`, neither of which imports `config`. (`DiscoveryError` and `collect_spec_paths` are already defined above in this module.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_new_discovery.py -v && uv run ruff check src/project_standards/specs/config.py tests/test_spec_new_discovery.py && uv run basedpyright src/project_standards/specs/config.py tests/test_spec_new_discovery.py`
Expected: tests PASS; Ruff and BasedPyright clean.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/config.py tests/test_spec_new_discovery.py
git commit -m "feat(spec): tolerant collect_existing_spec_ids discovery for new"
```

---

## Task 4: `scaffold` — the pure assembler

**Files:**

- Modify: `src/project_standards/specs/commands/new.py`
- Modify: `tests/test_spec_new.py`

**Interfaces:**

- Consumes: `emit_scalar` (Task 1); `TEMPLATES_DIR`, `TIER_FILES` (registry); `parse_document`, `validate_document` (property test).
- Produces:
  - `NewOptions` (frozen) with `profile: str`, `spec_id: str` (already resolved — minted or `--id`), `title: str | None`, `owner: str | None`, `implementer: str | None`.
  - `scaffold(template_text: str, opts: NewOptions, *, today: date) -> str` — the filled scaffold.

Minting is a separate pure function (Task 2) the shell calls to resolve `opts.spec_id`, so `scaffold` needs no RNG — keeping both functions individually testable while satisfying spec invariant I5 (all nondeterminism injected).

- [ ] **Step 1: Write the failing test**

```python
# 1) Merge into the TOP import block of tests/test_spec_new.py — never below code (E402):
from datetime import date

from project_standards.specs.commands.new import NewOptions, scaffold
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES, load_registry


# 2) Append this helper + test functions to the end of the file:
_TODAY = date(2026, 7, 4)


def _template(tier: str) -> str:
    return (TEMPLATES_DIR / TIER_FILES[tier]).read_text(encoding="utf-8")


def _opts(
    tier: str,
    *,
    spec_id: str = "SPEC-7F3Q",
    title: str | None = None,
    owner: str | None = None,
    implementer: str | None = None,
) -> NewOptions:
    return NewOptions(
        profile=tier, spec_id=spec_id, title=title, owner=owner, implementer=implementer
    )


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_scaffold_fills_machine_fields_and_drops_sentinel_comment(tier: str) -> None:
    out = scaffold(_template(tier), _opts(tier), today=_TODAY)
    assert "spec_id: SPEC-7F3Q\n" in out
    assert "SPEC-____" not in out
    assert "created: '2026-07-04'\n" in out
    assert "last_reviewed: '2026-07-04'\n" in out


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_scaffold_keeps_placeholders_when_flags_omitted(tier: str) -> None:
    out = scaffold(_template(tier), _opts(tier), today=_TODAY)
    assert "title: '<Project / Feature Name>'\n" in out
    assert "owner: '<person or team>'\n" in out


def test_scaffold_fills_provided_fields_and_rewrites_h1() -> None:
    out = scaffold(
        _template("standard"),
        _opts("standard", title="Checkout Service", owner="Payments team"),
        today=_TODAY,
    )
    assert "title: 'Checkout Service'\n" in out
    assert "owner: 'Payments team'\n" in out
    assert "# `Checkout Service` — Specification (Standard)\n" in out


def test_scaffold_only_rewrites_h1_with_title() -> None:
    out = scaffold(_template("standard"), _opts("standard"), today=_TODAY)
    assert "# `<Project / Feature Name>` — Specification (Standard)\n" in out


@pytest.mark.parametrize("tier", list(TIER_FILES))
@pytest.mark.parametrize("filled", [False, True])
def test_scaffold_output_validates_clean(tier: str, filled: bool) -> None:
    opts = (
        _opts(tier, title="T", owner="O", implementer="I") if filled else _opts(tier)
    )
    out = scaffold(_template(tier), opts, today=_TODAY)
    findings = validate_document(parse_document("new.md", out), load_registry())
    assert findings == []  # spec invariant I1


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_scaffold_leaves_body_below_frontmatter_untouched(tier: str) -> None:
    template = _template(tier)
    out = scaffold(template, _opts(tier), today=_TODAY)
    # No --title -> even the H1 is unchanged, so from the first '## ' heading onward the
    # output is byte-identical to the template (I4).
    marker = "\n## "
    assert template[template.index(marker):] == out[out.index(marker):]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spec_new.py -k scaffold -v`
Expected: FAIL with `ImportError: cannot import name 'NewOptions'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/project_standards/specs/commands/new.py
# first add to the top import block: `from dataclasses import dataclass` and `from datetime import date`


@dataclass(frozen=True)
class NewOptions:
    profile: str
    spec_id: str  # already resolved by the shell (minted or --id); never the sentinel
    title: str | None
    owner: str | None
    implementer: str | None


_FM_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
_H1 = re.compile(r"^(#\s+`)[^`]*(`)")


def _rewrite_frontmatter(text: str, replacements: dict[str, str]) -> str:
    """Replace whole frontmatter lines whose key is in `replacements`, inside the first
    `---`…`---` block only. Replacing the whole line drops any trailing inline comment
    (e.g. the spec_id placeholder note), which is intended."""
    out: list[str] = []
    seen_open = False
    in_fm = False
    for line in text.splitlines(keepends=True):
        if line.rstrip("\n") == "---":
            if not seen_open:
                seen_open, in_fm = True, True
            elif in_fm:
                in_fm = False
            out.append(line)
            continue
        if in_fm:
            m = _FM_KEY.match(line)
            if m and m.group(1) in replacements:
                nl = "\n" if line.endswith("\n") else ""
                out.append(replacements[m.group(1)] + nl)
                continue
        out.append(line)
    return "".join(out)


def _rewrite_h1(text: str, title: str) -> str:
    """Substitute the back-ticked name in the first `# \\`…\\` — Specification (T)` line.
    title is backtick-free by grammar (check_field), so the code span stays well-formed."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if _H1.match(line):
            lines[i] = _H1.sub(lambda m: m.group(1) + title + m.group(2), line, count=1)
            break
    return "".join(lines)


def scaffold(template_text: str, opts: NewOptions, *, today: date) -> str:
    iso = today.isoformat()
    replacements: dict[str, str] = {
        "spec_id": f"spec_id: {opts.spec_id}",
        "created": f"created: '{iso}'",
        "last_reviewed": f"last_reviewed: '{iso}'",
    }
    if opts.title is not None:
        replacements["title"] = f"title: {emit_scalar(opts.title)}"
    if opts.owner is not None:
        replacements["owner"] = f"owner: {emit_scalar(opts.owner)}"
    if opts.implementer is not None:
        replacements["implementer"] = f"implementer: {emit_scalar(opts.implementer)}"
    text = _rewrite_frontmatter(template_text, replacements)
    if opts.title is not None:
        text = _rewrite_h1(text, opts.title)
    return text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_new.py -v && uv run ruff check src/project_standards/specs/commands/new.py tests/test_spec_new.py && uv run basedpyright src/project_standards/specs/commands/new.py tests/test_spec_new.py`
Expected: tests PASS; Ruff and BasedPyright clean.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/new.py tests/test_spec_new.py
git commit -m "feat(spec): scaffold assembler (frontmatter rewrite + H1) — validates clean"
```

---

## Task 5: `_run_new` shell — JSON-aware parser, matrix, discovery, self-validate, `--stdout`

Delivers a fully working `--stdout` command (no file writing yet — Task 6), independently testable end-to-end via `--stdout`. The parser is JSON-aware so even argparse-level failures honor the `--json`/exit-2 contract (I6/I7).

**Files:**

- Modify: `src/project_standards/specs/cli.py`
- Modify: `src/project_standards/cli.py`
- Create: `tests/test_spec_new_cli.py`

**Interfaces:**

- Consumes: `NewOptions`, `scaffold`, `mint_spec_id`, `check_field`, `FieldValueError`, `SpecIdExhausted` (new module); `collect_existing_spec_ids`, `load_spec_config`, `ConfigError` (config); `parse_document`, `SpecParseError`, `validate_document`, `load_registry`, `SPEC_ID_PATTERN`, `TEMPLATES_DIR`, `TIER_FILES` (existing).
- Produces: `_run_new(argv: list[str]) -> int`, registered under `_VERBS["new"]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec_new_cli.py
"""CLI/integration tests for `project-standards spec new`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.specs.cli import run


def _one_json(captured: str) -> dict[str, object]:
    lines = [ln for ln in captured.splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected exactly one JSON line, got: {captured!r}"
    obj: dict[str, object] = json.loads(lines[0])
    return obj


def test_stdout_prints_valid_spec_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    rc = run(["new", "--profile", "light", "--stdout", "--id", "SPEC-7F3Q"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "spec_id: SPEC-7F3Q" in out
    assert set(tmp_path.iterdir()) == before  # I3: nothing created


def test_stdout_json_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = run(["new", "--profile", "full", "--stdout", "--json", "--id", "SPEC-AB12"])
    payload = _one_json(capsys.readouterr().out)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["spec_id"] == "SPEC-AB12"
    assert payload["profile"] == "full"
    assert payload["path"] is None and payload["written"] is False
    assert isinstance(payload["content"], str) and payload["content"].startswith("---\n")


@pytest.mark.parametrize(
    "argv",
    [
        ["new", "--profile", "light", "--stdout", "out.md"],  # PATH + --stdout
        ["new", "--profile", "light"],                         # neither PATH nor --stdout
        ["new", "--profile", "light", "--stdout", "--force"],  # --force with --stdout
    ],
)
def test_flag_conflicts_exit_2(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(argv) == 2


@pytest.mark.parametrize(
    "argv",
    [
        ["new", "--stdout", "--json"],                       # missing required --profile
        ["new", "--profile", "medium", "--stdout", "--json"],  # invalid --profile choice
        ["new", "--profile", "light", "--stdout", "--json", "--bogus"],  # unknown flag
    ],
)
def test_argparse_failures_are_json_and_never_systemexit(
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = run(argv)  # must NOT raise SystemExit
    payload = _one_json(capsys.readouterr().out)
    assert rc == 2
    assert payload["ok"] is False and payload["code"] == "usage"


def test_bad_id_and_bad_field_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(["new", "--profile", "light", "--stdout", "--id", "SPEC-lower"]) == 2
    assert run(["new", "--profile", "light", "--stdout", "--title", "has\nnewline"]) == 2
    capsys.readouterr()  # drain stderr from the two non-json runs above
    rc = run(["new", "--profile", "light", "--stdout", "--json", "--id", "nope"])
    payload = _one_json(capsys.readouterr().out)
    assert rc == 2 and payload["code"] == "bad_id"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spec_new_cli.py -v`
Expected: FAIL — `run(["new", ...])` returns 2 with `unknown spec verb 'new'` (not yet registered); rc-0 and payload assertions fail.

- [ ] **Step 3: Write minimal implementation**

Add to `src/project_standards/specs/cli.py`. New imports (extend the existing `config`/`registry`/`document` import lines rather than duplicating them):

```python
import random
from datetime import date
from typing import NoReturn

from project_standards.specs.commands.new import (
    FieldValueError,
    NewOptions,
    SpecIdExhausted,
    check_field,
    mint_spec_id,
    scaffold,
)
from project_standards.specs.config import (
    ConfigError,
    collect_existing_spec_ids,
    collect_spec_paths,
    load_spec_config,
)
from project_standards.specs.document import SpecParseError, parse_document
from project_standards.specs.registry import (
    SPEC_ID_PATTERN,
    TEMPLATES_DIR,
    TIER_FILES,
    load_registry,
)
```

Then, in the module body:

```python
import re


class _ArgparseError(Exception):
    """Raised by _NewArgParser.error so a bad invocation reaches the JSON wrapper
    instead of argparse's default sys.exit(2) + stderr (which would bypass I7)."""


class _NewArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)


class NewError(Exception):
    """A `spec new` refusal/usage/validation failure. Carries the frozen JSON `code`."""

    def __init__(self, code: str, message: str, findings: list[dict[str, object]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.findings = findings or []


def _emit_new_failure(json_mode: bool, err: NewError) -> int:
    if json_mode:
        obj: dict[str, object] = {"ok": False, "error": err.message, "code": err.code}
        if err.findings:
            obj["findings"] = err.findings
        print(json.dumps(obj))
    else:
        print(f"error: {err.message}", file=sys.stderr)
    return 2


def _resolve_new_options(args: argparse.Namespace) -> tuple[NewOptions, str]:
    """Validate flags, resolve the spec_id (mint or --id); return (opts, template_text).
    Raises NewError for every exit-2 condition."""
    for flag, value, is_title in (
        ("title", args.title, True),
        ("owner", args.owner, False),
        ("implementer", args.implementer, False),
    ):
        if value is not None:
            try:
                check_field(flag, value, is_title=is_title)
            except FieldValueError as exc:
                raise NewError("bad_field_value", str(exc)) from exc

    try:
        cfg = load_spec_config(args.config)
        existing_ids = collect_existing_spec_ids(cfg)
    except ConfigError as exc:
        raise NewError("config_error", str(exc)) from exc

    if args.spec_id is not None:
        if not re.match(SPEC_ID_PATTERN, args.spec_id):
            raise NewError("bad_id", f"--id {args.spec_id!r} does not match {SPEC_ID_PATTERN}")
        if args.spec_id in existing_ids:
            raise NewError("id_collision", f"--id {args.spec_id} is already used in this repo")
        spec_id = args.spec_id
    else:
        try:
            spec_id = mint_spec_id(random.Random(), existing_ids)
        except SpecIdExhausted as exc:
            raise NewError("id_exhausted", str(exc)) from exc

    opts = NewOptions(
        profile=args.profile,
        spec_id=spec_id,
        title=args.title,
        owner=args.owner,
        implementer=args.implementer,
    )
    template_text = (TEMPLATES_DIR / TIER_FILES[args.profile]).read_text(encoding="utf-8")
    return opts, template_text


def _run_new(argv: list[str]) -> int:
    json_mode = "--json" in argv  # known even if parsing fails, so usage errors stay JSON (I7)
    ap = _NewArgParser(prog="project-standards spec new")
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--profile", required=True, choices=("light", "standard", "full"))
    ap.add_argument("--id", dest="spec_id")
    ap.add_argument("--title")
    ap.add_argument("--owner")
    ap.add_argument("--implementer")
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)

    try:
        try:
            args = ap.parse_args(argv)
        except _ArgparseError as exc:
            raise NewError("usage", str(exc)) from exc

        if args.path is not None and args.stdout:
            raise NewError("flag_conflict", "--stdout writes to stdout; do not also pass PATH")
        if args.path is None and not args.stdout:
            raise NewError("flag_conflict", "PATH is required unless --stdout")
        if args.stdout and args.force:
            raise NewError("flag_conflict", "--force has no meaning with --stdout")

        opts, template_text = _resolve_new_options(args)
        text = scaffold(template_text, opts, today=date.today())

        # Fail-closed self-validation (I1): never emit a spec validate would reject, and
        # map a parse failure of our OWN output to self_validation_failed (not exit 1).
        try:
            doc = parse_document("<new>", text)
        except SpecParseError as exc:
            raise NewError("self_validation_failed", f"generated scaffold did not parse: {exc}") from exc
        findings = validate_document(doc, load_registry())
        if findings:
            raise NewError(
                "self_validation_failed",
                "generated scaffold failed self-validation",
                [dataclasses.asdict(f) for f in findings],
            )

        if args.stdout:
            if args.json:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "spec_id": opts.spec_id,
                            "profile": opts.profile,
                            "path": None,
                            "written": False,
                            "content": text,
                        }
                    )
                )
            else:
                sys.stdout.write(text)
            return 0

        return _write_new_file(args, opts, text)  # Task 6
    except NewError as err:
        return _emit_new_failure(json_mode, err)
```

Temporary stub so the module imports and `--stdout` tests pass (Task 6 replaces it):

```python
def _write_new_file(args: argparse.Namespace, opts: NewOptions, text: str) -> int:
    raise NewError("write_failed", "file writing not yet implemented")  # replaced in Task 6
```

Register the verb and refresh usage:

```python
_VERBS: dict[str, Callable[[list[str]], int]] = {
    "validate": _run_validate,
    "lint": _run_lint,
    "extract": _run_extract,
    "next": _run_next,
    "new": _run_new,
}

_USAGE = "usage: project-standards spec {validate|lint|extract|next|new} ..."
```

In `src/project_standards/cli.py`, update the advertised help:

```python
    sub.add_parser("spec", help="validate|lint|extract|next|new over project specs")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_new_cli.py -v && uv run ruff check src/project_standards/specs/cli.py src/project_standards/cli.py tests/test_spec_new_cli.py && uv run basedpyright src/project_standards/specs/cli.py`
Expected: tests PASS (all `--stdout`, flag-matrix, argparse-JSON, and failure-payload cases); Ruff and BasedPyright clean. File-writing tests come in Task 6.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/cli.py src/project_standards/cli.py tests/test_spec_new_cli.py
git commit -m "feat(spec): spec new shell — JSON-aware parser, matrix, discovery, self-validate, --stdout"
```

---

## Task 6: File write + safety + mode (`_write_new_file`)

**Files:**

- Modify: `src/project_standards/specs/cli.py`
- Modify: `tests/test_spec_new_cli.py`

**Interfaces:**

- Consumes: `NewError`, `NewOptions` (this module).
- Produces: `_write_new_file(args, opts, text) -> int` — atomic write with target-type, parent-chain, refuse/force, mkdir, and mode-preservation safety (mirrors `adopt/engine._atomic_write`).

- [ ] **Step 1: Write the failing test**

```python
# 1) Merge into the TOP import block of tests/test_spec_new_cli.py — never below code (E402);
#    `os` and `stat` are used by the mode tests:
import os
import stat


# 2) Append these test functions to the end of the file:
def test_writes_new_file_that_validates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "docs" / "specs" / "checkout.md"  # parents auto-created
    assert run(["new", "--profile", "standard", "--id", "SPEC-7F3Q", str(target)]) == 0
    assert target.is_file()
    assert run(["validate", str(target)]) == 0  # I1 end-to-end


def test_refuse_existing_then_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    target.write_text("PRIOR WORK\n", encoding="utf-8")
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(target)]) == 2  # I2
    assert target.read_text(encoding="utf-8") == "PRIOR WORK\n"  # untouched
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(target)]) == 0
    assert "spec_id: SPEC-7F3Q" in target.read_text(encoding="utf-8")


def test_directory_and_symlink_targets_refused_even_with_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "adir"
    d.mkdir()
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(d)]) == 2
    link = tmp_path / "link.md"
    link.symlink_to(tmp_path / "real.md")
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(link)]) == 2
    assert not (tmp_path / "real.md").exists()  # symlink not followed


def test_symlinked_parent_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    rc = run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(tmp_path / "link" / "s.md")])
    assert rc == 2
    assert not (outside / "s.md").exists()


def test_parent_that_is_a_file_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "afile").write_text("x", encoding="utf-8")
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(tmp_path / "afile" / "s.md")]) == 2


def test_write_leaves_no_temp_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(target)]) == 0
    assert [p.name for p in tmp_path.iterdir()] == ["s.md"]  # no leftover .spec-new-*.tmp


def test_new_file_mode_is_umask_respecting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(target)])
    mask = os.umask(0)
    os.umask(mask)
    assert stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(0o666 & ~mask)  # not 0600


def test_force_overwrite_preserves_target_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    target.write_text("old\n", encoding="utf-8")
    target.chmod(0o640)
    run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(target)])
    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_write_json_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--json", str(target)])
    payload = _one_json(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "spec_id": "SPEC-7F3Q",
        "profile": "light",
        "path": str(target),
        "written": True,
        "overwritten": False,
    }
```

Both `os` and `stat` were intentionally omitted from earlier tasks to keep those tasks import-clean; they arrive here with their first consumers (the mode tests).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spec_new_cli.py -k "write or refuse or symlink or parent or directory or mode" -v`
Expected: FAIL — the Task 5 stub raises `NewError("write_failed")`, so every write case exits 2 (including those that should be 0).

- [ ] **Step 3: Write minimal implementation**

Replace the Task 5 stub in `src/project_standards/specs/cli.py`. Add imports `import contextlib`, `import os`, `import stat`, `import tempfile` at the top:

```python
def _parent_chain_has_symlink(target: Path) -> bool:
    # Path.exists()/is_file() follow symlinks, so a symlinked PARENT (docs/link/spec.md)
    # could redirect the write outside the tree. Refuse a symlink anywhere in the chain.
    return any(parent.is_symlink() for parent in target.parents)


def _target_type_conflict(target: Path) -> bool:
    if target.is_symlink():  # includes broken symlinks (never followed for writes)
        return True
    return os.path.lexists(target) and not target.is_file()  # dir / fifo / device / socket


def _write_new_file(args: argparse.Namespace, opts: NewOptions, text: str) -> int:
    target: Path = args.path
    if _target_type_conflict(target):
        raise NewError("not_regular_file", f"refusing to write non-regular target: {target}")
    if _parent_chain_has_symlink(target):
        raise NewError(
            "symlinked_parent", f"refusing to write through a symlinked parent: {target}"
        )
    overwritten = target.is_file()
    if overwritten and not args.force:
        raise NewError("exists", f"refusing to overwrite existing file: {target} (use --force)")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise NewError("mkdir_failed", f"cannot create parent directory for {target}: {exc}") from exc

    tmp: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".spec-new-", suffix=".tmp")
        tmp = Path(tmp_name)
        # Mode (mirrors adopt/engine._atomic_write): preserve on overwrite; umask-respecting
        # 0o666 for a new file, so the result is not left at mkstemp's owner-only 0600.
        if target.exists():
            with contextlib.suppress(OSError):
                tmp.chmod(target.stat().st_mode & 0o777)
        else:
            mask = os.umask(0)
            os.umask(mask)
            with contextlib.suppress(OSError):
                tmp.chmod(stat.S_IMODE(0o666 & ~mask))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, target)  # atomic same-filesystem rename (I8)  # noqa: PTH105
    except OSError as exc:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise NewError("write_failed", f"cannot write {target}: {exc}") from exc
    except BaseException:
        # Full parity with adopt/engine._atomic_write: also clean up on interruption /
        # unexpected non-OSError (KeyboardInterrupt, generator-throw), then re-raise as-is.
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "spec_id": opts.spec_id,
                    "profile": opts.profile,
                    "path": str(target),
                    "written": True,
                    "overwritten": overwritten,
                }
            )
        )
    else:
        print(f"wrote {target}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_new_cli.py -v && uv run ruff check src/project_standards/specs/cli.py tests/test_spec_new_cli.py && uv run basedpyright src/project_standards/specs/cli.py`
Expected: tests PASS; Ruff and BasedPyright clean. (Mode tests are POSIX-behavioral; the repo CI runs on Linux.)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/cli.py tests/test_spec_new_cli.py
git commit -m "feat(spec): spec new atomic write + target/parent safety + mode preservation"
```

---

## Task 7: `--json` failure-code coverage (every frozen slug)

Proves each frozen `code` slug is actually emitted by some path, so the consumer JSON contract cannot silently drift. Hard-to-trigger slugs (`id_exhausted`, `mkdir_failed`, `write_failed`, `self_validation_failed`) are forced via monkeypatch rather than host state.

**Files:**

- Modify: `tests/test_spec_new_cli.py`

**Interfaces:**

- Consumes: `run`, and the `project_standards.specs.cli` module for monkeypatching internal call points.

- [ ] **Step 1: Write the failing test**

```python
# 1) Merge into the TOP import block of tests/test_spec_new_cli.py — never below code (E402):
from project_standards.specs import cli as spec_cli
from project_standards.specs.commands.new import SpecIdExhausted


# 2) Append these helpers + test functions to the end of the file:
def _json_code(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = run(argv)
    payload = _one_json(capsys.readouterr().out)
    assert payload["ok"] is False
    return rc, str(payload["code"])


def test_json_codes_for_arg_and_field_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    cases = {
        "usage": ["new", "--stdout", "--json"],  # missing --profile
        "flag_conflict": ["new", "--profile", "light", "--json", "--stdout", "x.md"],
        "bad_id": ["new", "--profile", "light", "--stdout", "--json", "--id", "nope"],
        "bad_field_value": ["new", "--profile", "light", "--stdout", "--json", "--title", "a\nb"],
    }
    for expected, argv in cases.items():
        rc, code = _json_code(argv, capsys)
        assert (rc, code) == (2, expected)


def test_json_code_config_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    bad = tmp_path / "bad.yml"
    bad.write_text("spec: [unterminated\n", encoding="utf-8")
    rc, code = _json_code(
        ["new", "--profile", "light", "--stdout", "--json", "--config", str(bad)], capsys
    )
    assert (rc, code) == (2, "config_error")


def test_json_code_id_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "e.md").write_text("---\nspec_id: SPEC-7F3Q\n---\n# t\n", encoding="utf-8")
    (tmp_path / ".project-standards.yml").write_text(
        "spec:\n  include:\n    - docs/*.md\n", encoding="utf-8"
    )
    rc, code = _json_code(
        ["new", "--profile", "light", "--stdout", "--json", "--id", "SPEC-7F3Q"], capsys
    )
    assert (rc, code) == (2, "id_collision")


def test_json_codes_for_write_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / "e.md"
    existing.write_text("x\n", encoding="utf-8")
    d = tmp_path / "d"
    d.mkdir()
    (tmp_path / "afile").write_text("x", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "plink").symlink_to(outside, target_is_directory=True)
    cases = {
        "exists": ["new", "--profile", "light", "--json", "--id", "SPEC-7F3Q", str(existing)],
        "not_regular_file": ["new", "--profile", "light", "--json", "--force", "--id", "SPEC-7F3Q", str(d)],
        "mkdir_failed": ["new", "--profile", "light", "--json", "--id", "SPEC-7F3Q", str(tmp_path / "afile" / "s.md")],
        "symlinked_parent": ["new", "--profile", "light", "--json", "--id", "SPEC-7F3Q", str(tmp_path / "plink" / "s.md")],
    }
    for expected, argv in cases.items():
        rc, code = _json_code(argv, capsys)
        assert (rc, code) == (2, expected)


def test_json_code_id_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    def _boom(rng: object, existing: object) -> str:
        raise SpecIdExhausted("forced")

    monkeypatch.setattr(spec_cli, "mint_spec_id", _boom)
    rc, code = _json_code(["new", "--profile", "light", "--stdout", "--json"], capsys)
    assert (rc, code) == (2, "id_exhausted")


def test_json_code_self_validation_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    def _malformed(template_text: str, opts: object, *, today: object) -> str:
        return "---\nnot a real spec\n"  # unterminated fence -> SpecParseError on self-validate

    monkeypatch.setattr(spec_cli, "scaffold", _malformed)
    rc, code = _json_code(
        ["new", "--profile", "light", "--stdout", "--json", "--id", "SPEC-7F3Q"], capsys
    )
    assert (rc, code) == (2, "self_validation_failed")


def test_json_code_write_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    def _boom(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(spec_cli.os, "replace", _boom)
    rc, code = _json_code(
        ["new", "--profile", "light", "--json", "--id", "SPEC-7F3Q", str(tmp_path / "s.md")], capsys
    )
    assert (rc, code) == (2, "write_failed")
    assert [p.name for p in tmp_path.iterdir()] == []  # temp cleaned up, no destination left


def test_write_cleanup_on_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # CR-NEW-001: a non-OSError (KeyboardInterrupt) after temp creation must still remove
    # the temp file and leave no destination — full parity with adopt/engine._atomic_write.
    monkeypatch.chdir(tmp_path)

    def _boom(src: object, dst: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(spec_cli.os, "replace", _boom)
    with pytest.raises(KeyboardInterrupt):
        run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(tmp_path / "s.md")])
    assert [p.name for p in tmp_path.iterdir()] == []  # temp cleaned up, destination untouched
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `uv run pytest tests/test_spec_new_cli.py -k json_code -v`
Expected: PASS if Tasks 5–6 emit the correct slugs. A failure here means a path emits the wrong `code` (or non-JSON) — fix the shell, not the test.

- [ ] **Step 3: (implementation already complete)**

No new production code — this task hardens the JSON contract. If a slug is wrong, correct the corresponding `NewError(...)` in `cli.py`.

- [ ] **Step 4: Run to verify**

Run: `uv run pytest tests/test_spec_new_cli.py -v && uv run ruff check tests/test_spec_new_cli.py && uv run basedpyright tests/test_spec_new_cli.py`
Expected: PASS; Ruff and BasedPyright clean.

- [ ] **Step 5: Commit**

```bash
git add tests/test_spec_new_cli.py
git commit -m "test(spec): assert every frozen --json code slug for spec new"
```

---

## Task 8: Dogfood + full-gate green

**Files:**

- Modify: `tests/test_spec_new_cli.py`

**Interfaces:**

- Consumes: the full `new` → `validate` pipeline.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_spec_new_cli.py
@pytest.mark.parametrize("tier", ["light", "standard", "full"])
def test_dogfood_new_then_validate(
    tier: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / f"{tier}.md"
    assert run(["new", "--profile", tier, str(target)]) == 0  # minted id, no --id
    assert run(["validate", str(target)]) == 0  # still validates
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_new_cli.py -k dogfood -v`
Expected: PASS. If any tier fails, a scaffold/validate mismatch is surfaced end-to-end — fix in `new.py`.

- [ ] **Step 3: Run the full gate**

Run:

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

Expected: all green; branch coverage ≥ `fail_under`. If Ruff reports import-sort/format issues from the incremental additions, run `uv run ruff format . && uv run ruff check --fix .` and re-run.

- [ ] **Step 4: Dogfood the repo's own frontmatter validator (non-negotiable)**

Run: `uv run validate-frontmatter --config .project-standards.yml`
Expected: PASS (this plan touches no managed Markdown frontmatter).

- [ ] **Step 5: Commit**

```bash
git add tests/test_spec_new_cli.py
git commit -m "test(spec): dogfood new -> validate across all three tiers"
```

---

## Self-Review notes (coverage of the spec)

- **CLI surface & flag matrix (spec C1):** Task 5 (JSON-aware parser + three conflict raises); `test_flag_conflicts_exit_2`, `test_argparse_failures_are_json_and_never_systemexit`.
- **Module layout & reuse (spec C2):** Tasks 1–6 create exactly the files the spec lists.
- **Fill operation + value grammar (spec C3):** Tasks 1 & 4; H1 rewrite only with `--title`; backtick-in-title rejection.
- **Minting & tolerant discovery (spec C4):** Tasks 2 & 3; bounded retries + `SpecIdExhausted`; `DiscoveryError`→empty while other `ConfigError`→exit 2 (`test_non_discovery_configerror_propagates`); malformed neighbor skipped.
- **Write model & safety (spec C5):** Task 6; atomic temp+`os.replace`, target-type + parent-chain symlink refusal, mkdir, refuse/force, **mode preservation**, and **`BaseException` temp cleanup** — full parity with `adopt/engine._atomic_write` (interruption test in Task 7).
- **Error handling, exit codes & `--json` contract (spec C6):** Tasks 5–7. **Every frozen `code` slug is asserted in Task 7** (`usage`, `flag_conflict`, `bad_id`, `bad_field_value`, `config_error`, `id_collision`, `id_exhausted`, `self_validation_failed`, `exists`, `not_regular_file`, `symlinked_parent`, `mkdir_failed`, `write_failed`). Parser failures route through the JSON wrapper (CR-001); self-validation catches `SpecParseError` (CR-003).
- **Invariants I1–I8:** I1 (scaffold property test + dogfood), I2/I3 (CLI tests), I4 (body-untouched test), I5 (seeded-RNG determinism), I6 (no `SystemExit`/traceback; every failure returns 2), I7 (JSON on every outcome incl. argparse), I8 (no-temp-left + atomic replace + mode).
- **Static gate cleanliness (CR-002):** every test snippet imports what it uses (`re`, `os`, `stat`), has no unused imports, annotates helpers (`_cfg -> SpecConfig`), and uses a real `random.Random` (no untyped RNG fake); each implementation task re-runs `ruff check` + `basedpyright`.
- **Out of scope (documented decisions):** bundled-template read failure is an install-integrity concern already guarded by Spec #1's `test_spec_packaging` (byte-identical + wheel-inclusion), so `new` does not add a runtime slug for it. Versioning/CHANGELOG are spec Non-goals (the CHANGELOG entry is separately owed in `TODO.md`).
```