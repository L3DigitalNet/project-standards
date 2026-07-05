# `spec upgrade` (Spec #3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `project-standards spec upgrade SRC --to {standard|full}` — additive tier promotion that splices the target tier's missing canonical sections/subsections into a `validate`-clean spec while preserving every author byte.

**Architecture:** A pure splice core (`specs/commands/upgrade.py`, `str -> str`, no I/O, no RNG, no clock) plus an impure CLI shell (`specs/cli.py::_run_upgrade`). Source-as-spine: the source's authored blocks are copied as **raw text** (never re-serialized); only missing units and canonical filler come from the target-tier bundled template. Two fail-closed gates bracket the splice — the source must be `validate`-clean before, and the spliced output must be `validate`-clean before any write.

**Tech Stack:** Python 3.14, argparse, PyYAML (via existing `emit_scalar`), pytest + coverage, ruff, basedpyright. Reuses `new.py` (`_rewrite_frontmatter`) and `cli.py` (`NewError`, `_emit_new_failure`, `_NewArgParser`/`_ArgparseError`, `_parent_chain_has_symlink`, `_target_type_conflict`, and the atomic-write core extracted in Task 7).

## Global Constraints

- Full gate must stay green: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`. Branch coverage must stay ≥ the repo `fail_under`.
- Dogfood before finishing: `uv run validate-frontmatter --config .project-standards.yml` must pass.
- Never add frontmatter to `CLAUDE.md`, `AGENTS.md`, or `.claude/**`.
- `project-spec` stays an **unregistered draft**: `standards/project-spec/**` is excluded from frontmatter validation; do not register it in this plan.
- Every command outcome supports `--json`; stdout carries exactly one JSON object in that mode. Exit codes: `0` success, `2` refusal/usage. There is **no exit-1 path** for `upgrade`.
- Frozen `--json` `code` slugs (extend `new`'s set): new — `source_not_found`, `source_read_error`, `source_invalid`, `source_not_upgradeable`, `not_upgradeable`; reused — `usage`, `flag_conflict`, `exists`, `not_regular_file`, `symlinked_parent`, `mkdir_failed`, `write_failed`, `self_validation_failed`. **No `config_error`** — `upgrade` reads no repo config (no `--config` flag).
- Additive-only: `--to light` is invalid; same-tier and downgrade refuse with `not_upgradeable`.
- Invariants to satisfy (from the design): U1 output validates, U2 author bytes verbatim, U3 tier fixture round-trip byte-identical, U4 preview writes nothing, U5 additive-only, U6 fail-closed both ends, U7 atomic + symlink/non-regular refusal, U8 no tracebacks, U9 `--json` on every outcome.

**Reference:** design at `docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md`.

---

### Task 1: Aligned fixture triple (the U3 oracle)

The single most important artifact: three fixtures with **identical author-filled cells** across the tiers they share, so `upgrade(light) == standard` and `upgrade(standard) == full` become byte-equality tests. Every later splice task is validated against these.

**Files:**
- Create: `tests/fixtures/specs/upgrade_light.md`
- Create: `tests/fixtures/specs/upgrade_standard.md`
- Create: `tests/fixtures/specs/upgrade_full.md`
- Test: `tests/test_spec_upgrade_fixtures.py`

**Interfaces:**
- Produces: three validate-clean fixtures used by Tasks 7, 9, 10. `upgrade_light.md` has `profile: light`; `upgrade_standard.md` `profile: standard`; `upgrade_full.md` `profile: full`.

Construction rule (critical for U3): start each fixture from the corresponding bundled template (`standards/project-spec/templates/spec-<tier>-template.md`). Fill the SAME author cells (title, spec_id `SPEC-UP01`, owner, a couple of `FR-0xx` rows, a Deviations row, etc.) in every tier. In the higher-tier fixtures, leave the **target-only sections as pristine template stubs** (do not author new prose into §3, §4, §8… in `upgrade_standard.md`) — because `upgrade(light)` cannot invent content the light source never had; U3 only holds if the new sections are byte-identical to the target template's stubs. Two subtleties the U3 round-trip (Task 6) will otherwise surface:
- **Preamble parity.** `upgrade` keeps the source's preamble (everything before `## Revision History`: the H1 and any intro blockquotes) and only rewrites the H1 tier word. So the three fixtures must share a **byte-identical preamble except the `(Light|Standard|Full)` H1 suffix** — author one canonical preamble and reuse it. (The tier templates' own preambles differ in wording; do not copy each template's preamble verbatim, or U3 will mismatch.) Delete the templates' "delete before publishing" instruction blockquotes in all three identically.
- **Canonical Appendices A/B/D.** These are template-owned and tier-variant; keep each fixture's Appendix A/B/D exactly as its tier template's (do not edit them), or the precheck (Task 8) will reject the fixture and the round-trip's Appendix B comparison will fail.

- [ ] **Step 1: Author `upgrade_full.md` first** (the superset), from `spec-full-template.md`, filling the shared author cells and deleting the template-instruction blockquotes.

- [ ] **Step 2: Derive `upgrade_standard.md`** from `spec-standard-template.md`: same frontmatter/title/author cells; for every section Standard shares with Full, paste the identical author cells; leave Standard's own sections that are template stubs in Full as the same stubs.

- [ ] **Step 3: Derive `upgrade_light.md`** from `spec-light-template.md`: same frontmatter/title; author cells only in the sections Light has (§1, §2, §7.1, §17.1, §21, Deviations).

- [ ] **Step 4: Write the fixture-validity test**

```python
# tests/test_spec_upgrade_fixtures.py
from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


@pytest.mark.parametrize(
    ("name", "profile"),
    [("upgrade_light.md", "light"), ("upgrade_standard.md", "standard"), ("upgrade_full.md", "full")],
)
def test_upgrade_fixture_is_valid_at_its_tier(name: str, profile: str) -> None:
    doc = parse_document(name, (_FIX / name).read_text(encoding="utf-8"))
    assert doc.profile == profile
    assert validate_document(doc, load_registry()) == []
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/test_spec_upgrade_fixtures.py -v`
Expected: 3 PASS. If a fixture reports findings, fix the fixture (it must be validate-clean) until green.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/specs/upgrade_light.md tests/fixtures/specs/upgrade_standard.md tests/fixtures/specs/upgrade_full.md tests/test_spec_upgrade_fixtures.py
git commit -m "test(spec): aligned light/standard/full fixture triple for upgrade round-trip"
```

---

### Task 2: Frontmatter profile + H1 tier-suffix rewrites

The two trivial in-place rewrites. `profile:` reuses `new`'s `_rewrite_frontmatter`; the H1 suffix (`— Specification (Light)` → `(Standard)`) needs a new rewriter because `new._rewrite_h1` only touches the back-ticked project name, never the suffix.

**Files:**
- Create: `src/project_standards/specs/commands/upgrade.py`
- Test: `tests/test_spec_upgrade.py`

**Interfaces:**
- Consumes: `project_standards.specs.commands.new._rewrite_frontmatter(text, {"profile": "profile: standard"})`.
- Produces: `_set_profile(text: str, tier: str) -> str`; `_rewrite_h1_suffix(text: str, tier: str) -> str`. `tier ∈ {"standard","full"}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_spec_upgrade.py
from __future__ import annotations

from project_standards.specs.commands.upgrade import _rewrite_h1_suffix, _set_profile


def test_set_profile_rewrites_only_the_profile_line() -> None:
    text = "---\nspec_id: SPEC-UP01\nprofile: light\nowner: 'me'\n---\n\nbody\n"
    out = _set_profile(text, "standard")
    assert "profile: standard\n" in out
    assert "spec_id: SPEC-UP01\n" in out  # other frontmatter untouched
    assert "owner: 'me'\n" in out
    assert out.endswith("body\n")


def test_rewrite_h1_suffix_changes_tier_word_only() -> None:
    text = "# `My Project` — Specification (Light)\n\n## 1. Purpose\n"
    out = _rewrite_h1_suffix(text, "standard")
    assert out.startswith("# `My Project` — Specification (Standard)\n")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade.py -v`
Expected: FAIL — `ImportError` / `AttributeError` (module/functions absent).

- [ ] **Step 3: Write minimal implementation**

```python
# src/project_standards/specs/commands/upgrade.py
"""Pure splice core for the additive `spec upgrade` command.

Source-as-spine: the source's authored blocks are copied verbatim as raw text;
only missing canonical units and tier-owned filler come from the target-tier
template. All functions are deterministic in their arguments (no RNG, clock, or
I/O); the impure shell is project_standards.specs.cli._run_upgrade.
"""

from __future__ import annotations

import re

from project_standards.specs.commands.new import _rewrite_frontmatter

_TIER_WORD = {"light": "Light", "standard": "Standard", "full": "Full"}
_H1_SUFFIX = re.compile(r"(#\s+`[^`]*`\s+—\s+Specification\s+\()(Light|Standard|Full)(\))")


def _set_profile(text: str, tier: str) -> str:
    return _rewrite_frontmatter(text, {"profile": f"profile: {tier}"})


def _rewrite_h1_suffix(text: str, tier: str) -> str:
    word = _TIER_WORD[tier]
    return _H1_SUFFIX.sub(lambda m: m.group(1) + word + m.group(3), text, count=1)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_spec_upgrade.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/upgrade.py tests/test_spec_upgrade.py
git commit -m "feat(spec): upgrade profile + H1 tier-suffix rewrites"
```

---

### Task 3: Section segmentation + canonical unit diff

Segment a body into top-level (`##`) blocks keyed by canonical identity, and compute which top-level units the target has that the source lacks. This drives insertion ordering.

**Files:**
- Modify: `src/project_standards/specs/commands/upgrade.py`
- Test: `tests/test_spec_upgrade.py`

**Interfaces:**
- Produces:
  - `_block_key(heading_text: str) -> str` — `"7"` for `7. Requirements`, `"appendix-A"` for `Appendix A: …`, else the gh-slug (`"references"`, `"deviations-log"`).
  - `_top_blocks(body: str) -> list[tuple[str, str]]` — ordered `(key, block_text)`; `block_text` spans a `## ` heading through just before the next `## ` (trailing filler included). Text before the first `## ` is returned under key `""` (the preamble).
  - `_present_top_keys(body: str) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_top_blocks_splits_on_h2_and_keys_by_canonical_identity() -> None:
    body = (
        "# `T` — Specification (Light)\n\npreamble\n\n"
        "## 1. Purpose\n\np\n\n"
        "## References\n\nr\n\n"
        "## Appendix A: ID Conventions\n\na\n"
    )
    from project_standards.specs.commands.upgrade import _top_blocks

    blocks = _top_blocks(body)
    keys = [k for k, _ in blocks]
    assert keys == ["", "1", "references", "appendix-A"]
    assert blocks[1][1].startswith("## 1. Purpose")
    assert blocks[0][1].startswith("# `T`")  # preamble preserved under key ""


def test_present_top_keys_lists_numbered_sections() -> None:
    from project_standards.specs.commands.upgrade import _present_top_keys

    body = "## 1. Purpose\n\n## 2. Scope\n\n## 7. Requirements\n"
    assert _present_top_keys(body) == ["1", "2", "7"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade.py -k "top_blocks or present_top" -v`
Expected: FAIL — functions absent.

- [ ] **Step 3: Write minimal implementation** (append to `upgrade.py`)

```python
from project_standards.specs.registry import gh_slug  # add to imports

_H2_LINE = re.compile(r"^## (.+)$", re.M)
_NUM = re.compile(r"^(\d+)\.")
_APX = re.compile(r"^Appendix ([A-Z]):")


def _block_key(heading_text: str) -> str:
    if m := _NUM.match(heading_text):
        return m.group(1)
    if m := _APX.match(heading_text):
        return f"appendix-{m.group(1)}"
    return gh_slug(heading_text)


def _top_blocks(body: str) -> list[tuple[str, str]]:
    starts = [(m.start(), m.group(1)) for m in _H2_LINE.finditer(body)]
    out: list[tuple[str, str]] = []
    if not starts or starts[0][0] > 0:
        out.append(("", body[: starts[0][0] if starts else len(body)]))
    for i, (pos, heading) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(body)
        out.append((_block_key(heading), body[pos:end]))
    return out


def _present_top_keys(body: str) -> list[str]:
    return [k for k, _ in _top_blocks(body) if k and not k.startswith("appendix-")]
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_spec_upgrade.py -k "top_blocks or present_top" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/upgrade.py tests/test_spec_upgrade.py
git commit -m "feat(spec): upgrade section segmentation + canonical block keys"
```

---

### Task 4: Merge top-level blocks (missing-section insertion)

Walk the target template's block order; for each block, emit the **source's** block when the source has that key (author-owned, verbatim), otherwise the **target's** block (missing unit or tier-owned filler). This inserts every missing whole section at its canonical position in one pass.

**Files:**
- Modify: `src/project_standards/specs/commands/upgrade.py`
- Test: `tests/test_spec_upgrade.py`

**Interfaces:**
- Consumes: `_top_blocks`.
- Produces: `_merge_top(source_body: str, target_body: str) -> str`. Preamble (`""`) is taken from the **source** (author's H1/title; the tier suffix is fixed separately by `_rewrite_h1_suffix`), except when the source preamble is empty. Appendix keys (`appendix-A`, `appendix-D`) present in both are taken from the **target** (tier-owned — see Task 6); everything else shared comes from the source.

- [ ] **Step 1: Write the failing test**

```python
def test_merge_top_inserts_missing_section_and_keeps_author_block() -> None:
    from project_standards.specs.commands.upgrade import _merge_top

    source = "# `T` — Specification (Light)\n\n## 1. Purpose\n\nAUTHORED\n\n## 7. Requirements\n\nFR stuff\n"
    target = (
        "# `X` — Specification (Standard)\n\n## 1. Purpose\n\nstub\n\n"
        "## 3. Context\n\ncontext stub\n\n## 7. Requirements\n\nreq stub\n"
    )
    out = _merge_top(source, target)
    assert "AUTHORED" in out          # source's §1 kept verbatim
    assert "FR stuff" in out          # source's §7 kept verbatim
    assert "## 3. Context" in out     # target's §3 inserted
    assert "context stub" in out
    assert out.index("## 1. Purpose") < out.index("## 3. Context") < out.index("## 7. Requirements")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_spec_upgrade.py -k merge_top -v`
Expected: FAIL — `_merge_top` absent.

- [ ] **Step 3: Write minimal implementation** (append)

```python
# Appendices A, B, and D are all tier-variant canonical boilerplate — taken from
# the target tier, never the source. (Appendix C is Full-only, so it arrives as a
# missing unit, not a template-owned replacement.) The upgradeability precheck
# (Task 8) guarantees the source's A/B/D are canonical, so nothing author-written
# is lost by replacing them.
_TEMPLATE_OWNED = {"appendix-A", "appendix-B", "appendix-D"}


def _merge_top(source_body: str, target_body: str) -> str:
    source_map = dict(_top_blocks(source_body))
    out: list[str] = []
    for key, target_text in _top_blocks(target_body):
        if key in source_map and key not in _TEMPLATE_OWNED:
            out.append(source_map[key])
        else:
            out.append(target_text)  # missing unit, tier-owned appendix, or target preamble
    return "".join(out)
```

Note: the preamble key `""` is in `source_map` (source has one) and not template-owned, so the source preamble is kept — its stale `(Light)` suffix is corrected by `_rewrite_h1_suffix` in Task 2. **The U3 round-trip in Task 6 is the real acceptance test** — expect to refine trailing-filler handling (stale omission notes at the tail of shared blocks; see Task 5) before it is byte-exact.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_spec_upgrade.py -k merge_top -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/upgrade.py tests/test_spec_upgrade.py
git commit -m "feat(spec): upgrade merge inserts missing top-level sections"
```

---

### Task 5: Reconcile filler — strip filled omission notes, insert subsections

Two residual mismatches after Task 4, both inside **shared** blocks:
1. A shared block's trailing filler may carry a now-obsolete whole-section omission note (e.g. §2's block tail holds `> **Sections §3–§6 … omitted**`, but §3–§6 are now present) — strip it.
2. A shared section may gain subsections (§7 gains §7.2–§7.4; §17 gains §17.2–§17.3; §8/§18/§19 on standard→full) and carry a stale reduction-note intro (`> At the Light profile, Requirements is functional-only …`) — replace the shared block's body with the **target** block's body while re-injecting the source's authored subsections.

**Files:**
- Modify: `src/project_standards/specs/commands/upgrade.py`
- Test: `tests/test_spec_upgrade.py`

**Interfaces:**
- Consumes: `_top_blocks`, `_block_key`.
- Produces: `_reconcile_shared(source_block: str, target_block: str) -> str` — used by `_merge_top` for shared, non-template-owned keys. Recurses on `### ` subsections with the same "source body if present, else target" rule, and always takes the pre-first-subsection intro filler and trailing filler from the **target** block (so stale omission/reduction notes are dropped and the target's canonical notes are used).

- [ ] **Step 1: Write the failing tests**

```python
def test_reconcile_drops_stale_omission_note_tail() -> None:
    from project_standards.specs.commands.upgrade import _reconcile_shared

    source = "## 2. Scope\n\nAUTHORED scope\n\n---\n\n> **Sections §3–§6 are Standard/Full-tier** and are intentionally omitted at the Light profile.\n\n"
    target = "## 2. Scope\n\nscope stub\n\n---\n\n"
    out = _reconcile_shared(source, target)
    assert "AUTHORED scope" in out            # author body kept
    assert "intentionally omitted" not in out  # stale tail dropped (target tail used)


def test_reconcile_inserts_missing_subsections_and_drops_reduction_note() -> None:
    from project_standards.specs.commands.upgrade import _reconcile_shared

    source = "## 7. Requirements\n\n> At the Light profile, Requirements is functional-only (§7.1). §7.2–§7.4 are Standard-tier.\n\n### 7.1 Functional Requirements\n\nAUTHORED FR TABLE\n\n"
    target = "## 7. Requirements\n\n> **Quality rule:** one testable statement.\n\n### 7.1 Functional Requirements\n\nstub\n\n### 7.2 Non-Functional Requirements\n\nnfr stub\n\n"
    out = _reconcile_shared(source, target)
    assert "AUTHORED FR TABLE" in out   # source §7.1 kept
    assert "### 7.2 Non-Functional" in out  # target §7.2 inserted
    assert "functional-only" not in out  # reduction note dropped
    assert "Quality rule" in out         # target intro used
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade.py -k reconcile -v`
Expected: FAIL — `_reconcile_shared` absent.

- [ ] **Step 3: Write minimal implementation** (append). This mirrors `_merge_top` one level down, keyed on `### ` subsection headings, with intro/tail filler always from the target.

```python
_H3_LINE = re.compile(r"^### (.+)$", re.M)


def _sub_blocks(block: str) -> list[tuple[str, str]]:
    starts = [(m.start(), m.group(1)) for m in _H3_LINE.finditer(block)]
    out: list[tuple[str, str]] = []
    intro_end = starts[0][0] if starts else len(block)
    out.append(("", block[:intro_end]))  # heading + pre-first-subsection intro filler
    for i, (pos, heading) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(block)
        out.append((_block_key(heading), block[pos:end]))
    return out


def _reconcile_shared(source_block: str, target_block: str) -> str:
    src_subs = dict(_sub_blocks(source_block))
    tgt_subs = _sub_blocks(target_block)
    if len(tgt_subs) == 1:
        # No subsection structure: keep the author body, take only the trailing filler
        # (dividers / now-stale omission notes) from the target block.
        return _swap_tail(source_block, target_block)
    out: list[str] = []
    for key, tgt_text in tgt_subs:
        if key == "":
            out.append(tgt_text)  # target's heading + intro (drops stale reduction note)
        elif key in src_subs:
            out.append(src_subs[key])  # author subsection verbatim
        else:
            out.append(tgt_text)  # target's inserted subsection
    return "".join(out)


def _swap_tail(source_block: str, target_block: str) -> str:
    """Return the source block with its trailing filler replaced by the target's.

    Trailing filler = the maximal suffix of blank / `---` / omission-note (`> … tier …
    omitted`) lines. This is where stale whole-section omission notes live.
    """
    def split(block: str) -> tuple[str, str]:
        lines = block.splitlines(keepends=True)
        i = len(lines)
        while i > 0 and _is_filler(lines[i - 1]):
            i -= 1
        return "".join(lines[:i]), "".join(lines[i:])

    src_body, _src_tail = split(source_block)
    _tgt_body, tgt_tail = split(target_block)
    return src_body + tgt_tail


def _is_filler(line: str) -> bool:
    s = line.strip()
    if s in ("", "---"):
        return True
    return s.startswith(">") and "tier" in s and "omitted" in s
```

Then update `_merge_top` (Task 4) to call `_reconcile_shared` for shared non-template-owned keys other than the preamble:

```python
        if key == "":
            out.append(source_map[key])            # preamble from source
        elif key in source_map and key not in _TEMPLATE_OWNED:
            out.append(_reconcile_shared(source_map[key], target_text))
        else:
            out.append(target_text)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_spec_upgrade.py -k "reconcile or merge_top" -v`
Expected: PASS. (`_swap_tail`'s `_is_filler` heuristic may need widening once the U3 round-trip runs in Task 6 — an author body legitimately ending in a blockquote is rare but is the known risk; U3 will surface it.)

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/upgrade.py tests/test_spec_upgrade.py
git commit -m "feat(spec): upgrade reconciles filler + inserts subsections"
```

---

### Task 6: `upgrade_text` orchestration + U3 round-trip (acceptance oracle)

Compose the pieces into the public `upgrade_text`, then hold it to the fixture round-trip: upgrading a tier fixture must reproduce the next fixture byte-for-byte. This is where the byte-details from Tasks 4–5 get forced correct.

**Files:**
- Modify: `src/project_standards/specs/commands/upgrade.py`
- Test: `tests/test_spec_upgrade.py`

**Interfaces:**
- Produces: `upgrade_text(source_text: str, target_template_text: str, *, target_tier: str) -> str`.

- [ ] **Step 1: Write the failing tests** (the U3 oracle + output-validates property)

```python
from pathlib import Path

import pytest

from project_standards.specs.commands.upgrade import upgrade_text
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES, load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _tmpl(tier: str) -> str:
    return (TEMPLATES_DIR / TIER_FILES[tier]).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("src", "tier", "want"),
    [
        ("upgrade_light.md", "standard", "upgrade_standard.md"),
        ("upgrade_light.md", "full", "upgrade_full.md"),
        ("upgrade_standard.md", "full", "upgrade_full.md"),
    ],
)
def test_upgrade_round_trip_is_byte_identical_to_target_fixture(src: str, tier: str, want: str) -> None:
    out = upgrade_text((_FIX / src).read_text(encoding="utf-8"), _tmpl(tier), target_tier=tier)
    assert out == (_FIX / want).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("src", "tier"),
    [("upgrade_light.md", "standard"), ("upgrade_light.md", "full"), ("upgrade_standard.md", "full")],
)
def test_upgrade_output_validates(src: str, tier: str) -> None:
    out = upgrade_text((_FIX / src).read_text(encoding="utf-8"), _tmpl(tier), target_tier=tier)
    assert validate_document(parse_document("<out>", out), load_registry()) == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade.py -k "round_trip or output_validates" -v`
Expected: FAIL — `upgrade_text` absent (then, once defined, likely byte-diffs to iterate on).

- [ ] **Step 3: Write minimal implementation** (append). Split frontmatter from body, merge the bodies, then apply the profile + H1 rewrites to the whole text.

```python
from project_standards.specs.registry import split_front_matter  # add to imports


def upgrade_text(source_text: str, target_template_text: str, *, target_tier: str) -> str:
    src_fm, src_body = split_front_matter(source_text)
    _tgt_fm, tgt_body = split_front_matter(target_template_text)
    merged_body = _merge_top(src_body, tgt_body)
    text = f"---\n{src_fm}\n---\n{merged_body}"  # source frontmatter preserved verbatim
    text = _set_profile(text, target_tier)
    return _rewrite_h1_suffix(text, target_tier)
```

- [ ] **Step 4: Run and iterate to green**

Run: `uv run pytest tests/test_spec_upgrade.py -k "round_trip or output_validates" -v`
Expected: iterate. Use the assertion diff to fix byte mismatches — most will be trailing-filler spacing (`_is_filler` / `_swap_tail`), the frontmatter fence reconstruction (`split_front_matter` strips the fences; confirm `f"---\n{src_fm}\n---\n"` reproduces them exactly, including whether `src_fm` retains a trailing newline), and preamble handling. Do **not** weaken the byte-equality assertion — fix the code. When all three round-trips and all three output-validate cases are green, proceed.

- [ ] **Step 5: Run the full pure-splice suite**

Run: `uv run pytest tests/test_spec_upgrade.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/specs/commands/upgrade.py tests/test_spec_upgrade.py
git commit -m "feat(spec): upgrade_text orchestration + byte-exact round-trip"
```

---

### Task 7: Extract the shared atomic-write helper

`upgrade` needs `new`'s safety + atomic-write core but a different JSON payload and overwrite-as-normal semantics. Extract the core so both commands share one audited implementation; `new`'s existing tests are the refactor's safety net.

**Files:**
- Modify: `src/project_standards/specs/cli.py` (`_write_new_file` → thin wrapper over a new `_safe_atomic_write`)
- Test: existing `tests/test_spec_new_cli.py` (must stay green — no new test needed for the pure refactor)

**Interfaces:**
- Produces: `_safe_atomic_write(target: Path, text: str, *, force: bool) -> bool` — runs the target-type + parent-chain refusals, the overwrite gate, `mkdir(parents=True)`, and the `mkstemp`+`os.replace` atomic write with mode preservation; returns `overwritten`. Raises `NewError` for `not_regular_file` / `symlinked_parent` / `exists` / `mkdir_failed` / `write_failed`.
- Consumes (unchanged): `_target_type_conflict`, `_parent_chain_has_symlink`.

- [ ] **Step 1: Extract the helper** — move the body of `_write_new_file` (cli.py:264-308, everything up to and including `os.replace`) into `_safe_atomic_write(target, text, *, force)`, returning `overwritten`. Keep the exact comments (mode preservation, BaseException cleanup).

```python
def _safe_atomic_write(target: Path, text: str, *, force: bool) -> bool:
    if _target_type_conflict(target):
        raise NewError("not_regular_file", f"refusing to write non-regular target: {target}")
    if _parent_chain_has_symlink(target):
        raise NewError("symlinked_parent", f"refusing to write through a symlinked parent: {target}")
    overwritten = target.is_file()
    if overwritten and not force:
        raise NewError("exists", f"refusing to overwrite existing file: {target} (use --force)")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise NewError("mkdir_failed", f"cannot create parent directory for {target}: {exc}") from exc
    tmp: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".spec-write-", suffix=".tmp")
        tmp = Path(tmp_name)
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
        os.replace(tmp, target)  # noqa: PTH105
    except OSError as exc:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise NewError("write_failed", f"cannot write {target}: {exc}") from exc
    except BaseException:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise
    return overwritten
```

- [ ] **Step 2: Rewrite `_write_new_file` to call it**

```python
def _write_new_file(args: argparse.Namespace, opts: NewOptions, text: str) -> int:
    overwritten = _safe_atomic_write(args.path, text, force=args.force)
    if args.json:
        print(json.dumps({"ok": True, "spec_id": opts.spec_id, "profile": opts.profile,
                          "path": str(args.path), "written": True, "overwritten": overwritten}))
    else:
        print(f"wrote {args.path}")
    return 0
```

- [ ] **Step 3: Run new's suite to verify the refactor is behavior-preserving**

Run: `uv run pytest tests/test_spec_new_cli.py tests/test_spec_new.py -v`
Expected: all PASS (temp-file prefix changed `.spec-new-`→`.spec-write-`; if a test asserts the prefix, update it to `.spec-write-`).

- [ ] **Step 4: Commit**

```bash
git add src/project_standards/specs/cli.py tests/test_spec_new_cli.py
git commit -m "refactor(spec): extract _safe_atomic_write shared by new and upgrade"
```

---

### Task 8: Upgradeability precheck + CLI shell (flag matrix, gates, tier direction)

Two deliverables that ship together: (a) the pure `check_upgradeable` precheck (design decision 10 — refuses a `validate`-clean-but-non-canonical source before splicing), and (b) the impure `_run_upgrade` shell that wires all three fail-closed gates (`validate`, precheck, output self-validate), the flag matrix, and preview delivery. `-i`/`-o` delivery lands in Task 9.

`check_upgradeable` is implemented by **reshaping the source to its *own* tier** with the same `_merge_top` engine and requiring the identity: a source whose scaffolding (gaps, notes, Appendices A/B/D, subsection membership) is canonical reshapes to itself; any deviation (gap prose, edited appendix, non-canonical subsection) makes the reshape differ, so it is refused. This reuses proven code and needs no separate parser.

**Files:**
- Modify: `src/project_standards/specs/commands/upgrade.py` (add `check_upgradeable`)
- Modify: `src/project_standards/specs/cli.py`
- Test: `tests/test_spec_upgrade.py` (pure precheck), `tests/test_spec_upgrade_cli.py` (shell)

**Interfaces:**
- Consumes: `_merge_top`, `split_front_matter` (for `check_upgradeable`); `upgrade_text`, `NewError`, `_emit_new_failure`, `_NewArgParser`, `_ArgparseError`, `_read`, `load_registry`, `parse_document`, `validate_document`, `TEMPLATES_DIR`, `TIER_FILES`, `ConfigError` (for `_run_upgrade`). **No `--config` / `load_spec_config`** — `upgrade` reads no repo config (design SA-005).
- Produces: `check_upgradeable(source_text: str, source_tier_template: str) -> str | None` (deviation message or `None`); `_run_upgrade(argv) -> int`; registered as `"upgrade"` in `_VERBS`; `_USAGE` updated.

- [ ] **Step 1: Write the failing precheck tests** (pure, in `tests/test_spec_upgrade.py`)

```python
def test_check_upgradeable_accepts_a_canonical_source() -> None:
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    assert check_upgradeable(light, _tmpl("light")) is None


def test_check_upgradeable_rejects_gap_prose() -> None:
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace("## 7. Requirements", "Author prose in a gap.\n\n## 7. Requirements", 1)
    assert check_upgradeable(tampered, _tmpl("light")) is not None


def test_check_upgradeable_rejects_non_canonical_subsection() -> None:
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace("## 17. ", "### 7.3 Interface Requirements\n\nx\n\n## 17. ", 1)
    assert check_upgradeable(tampered, _tmpl("light")) is not None


def test_check_upgradeable_rejects_edited_appendix_b() -> None:
    # Appendix B is template-owned (SA-NEW-001); an author edit makes the reshape differ.
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace(
        "### B.1 Implementation Rules", "### B.1 Implementation Rules\n\nAuthor-added rule.", 1)
    assert check_upgradeable(tampered, _tmpl("light")) is not None
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade.py -k check_upgradeable -v`
Expected: FAIL — `check_upgradeable` absent.

- [ ] **Step 3: Implement `check_upgradeable`** (append to `upgrade.py`)

```python
def check_upgradeable(source_text: str, source_tier_template: str) -> str | None:
    """Return a deviation message if the source's scaffolding is not canonical for its
    tier, else None. Enforces design decision 10: everything outside authored section
    bodies (gaps, notes, Appendices A/B/D, subsection membership) must match the
    source-tier template. Implemented as a reshape-to-own-tier identity check — a
    canonical source reshapes to itself; any deviation changes the reshape."""
    _sfm, src_body = split_front_matter(source_text)
    _tfm, tmpl_body = split_front_matter(source_tier_template)
    if _merge_top(src_body, tmpl_body) != src_body:
        return (
            "source scaffolding is not canonical for its tier (author prose in a gap, "
            "an edited Appendix A/B/D, or a non-canonical subsection); restore the "
            "template structure before upgrading"
        )
    return None
```

- [ ] **Step 4: Run to verify the precheck tests pass**

Run: `uv run pytest tests/test_spec_upgrade.py -k check_upgradeable -v`
Expected: PASS. (If a canonical fixture spuriously fails — e.g. `_is_filler` over-trims an author body ending in a blockquote — that is the known Task 5 risk; tighten `_is_filler` so the canonical source reshapes to identity.)

- [ ] **Step 5: Write the failing CLI tests**

```python
# tests/test_spec_upgrade_cli.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.specs.cli import run

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _run(argv: list[str]) -> int:
    return run(["upgrade", *argv])


def test_missing_to_flag_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    rc = _run([str(_FIX / "upgrade_light.md"), "--json"])
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["code"] == "usage"


def test_downgrade_target_light_is_usage_error(tmp_path: Path) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_standard.md").read_text(), encoding="utf-8")
    assert _run([str(src), "--to", "light", "--json"]) == 2  # argparse rejects --to light


def test_same_tier_is_not_upgradeable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_standard.md").read_text(), encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "not_upgradeable"


def test_invalid_source_is_refused_with_findings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "s.md"
    src.write_text("---\nprofile: light\n---\n\nnot a real spec\n", encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_invalid" and obj["findings"]


def test_gap_prose_source_is_not_upgradeable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Validate-clean (gap prose does not trip validate) but non-canonical → precheck refuses.
    src = tmp_path / "s.md"
    tampered = (_FIX / "upgrade_light.md").read_text().replace(
        "## 7. Requirements", "Author prose in a gap.\n\n## 7. Requirements", 1)
    src.write_text(tampered, encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_not_upgradeable"


def test_preview_prints_upgraded_doc_and_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "s.md"
    original = (_FIX / "upgrade_light.md").read_text()
    src.write_text(original, encoding="utf-8")
    rc = _run([str(src), "--to", "standard"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "profile: standard" in out
    assert src.read_text(encoding="utf-8") == original  # U4: source untouched


def test_missing_source_file(capsys: pytest.CaptureFixture[str]) -> None:
    rc = _run(["nope.md", "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_not_found"
```

- [ ] **Step 6: Run to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade_cli.py -v`
Expected: FAIL — unknown verb `upgrade`.

- [ ] **Step 7: Write the CLI implementation** (add to `cli.py`; import `upgrade_text` and `check_upgradeable`)

```python
from project_standards.specs.commands.upgrade import check_upgradeable, upgrade_text  # add to imports

_TIER_ORDER = {"light": 0, "standard": 1, "full": 2}


def _upgrade_output(text: str, *, json_mode: bool, source_profile: str, target_tier: str,
                    spec_id: str, path: str | None, mode: str, written: bool) -> None:
    if json_mode:
        obj: dict[str, object] = {"ok": True, "spec_id": spec_id, "from_profile": source_profile,
                                  "to_profile": target_tier, "path": path, "written": written, "mode": mode}
        if mode == "stdout":
            obj["content"] = text
        print(json.dumps(obj))
    elif mode == "stdout":
        sys.stdout.write(text)
    else:
        print(f"wrote {path}")


def _run_upgrade(argv: list[str]) -> int:
    json_mode = "--json" in argv
    ap = _NewArgParser(prog="project-standards spec upgrade")
    ap.add_argument("src", type=Path)
    ap.add_argument("--to", required=True, choices=("standard", "full"))
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--output", "-o", type=Path)
    ap.add_argument("--in-place", "-i", action="store_true", dest="in_place")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    try:
        try:
            args = ap.parse_args(argv)
        except _ArgparseError as exc:
            raise NewError("usage", str(exc)) from exc

        # Flag matrix (Task 9 tests -i/-o cases; wire it all here).
        if args.in_place and args.output is not None:
            raise NewError("flag_conflict", "choose one of --in-place or --output")
        if args.in_place and args.stdout:
            raise NewError("flag_conflict", "--stdout previews; do not also pass --in-place")
        if args.stdout and args.output is not None:
            raise NewError("flag_conflict", "choose one of --stdout or --output")
        if args.force and not args.output:
            raise NewError("flag_conflict", "--force only applies to --output")

        if not args.src.is_file():
            raise NewError("source_not_found", f"source spec not found: {args.src}")
        try:
            source_text = _read(args.src)
        except (SpecParseError, ConfigError) as exc:  # _read wraps OSError/decode errors
            raise NewError("source_read_error", str(exc)) from exc

        reg = load_registry()
        try:
            src_doc = parse_document(str(args.src), source_text)
        except SpecParseError as exc:
            raise NewError("source_read_error", str(exc)) from exc

        # Gate 1: validate-clean.
        findings = validate_document(src_doc, reg)
        if findings:
            raise NewError("source_invalid",
                           f"source has {len(findings)} validation finding(s); fix them before upgrading",
                           [dataclasses.asdict(f) for f in findings])

        # Tier direction (additive-only). profile is a valid tier here (validate passed).
        source_profile = src_doc.profile or ""
        if _TIER_ORDER.get(source_profile, -1) >= _TIER_ORDER[args.to]:
            raise NewError("not_upgradeable",
                           f"cannot upgrade profile {source_profile!r} to {args.to}: additive-only")

        # Gate 2: upgradeability precheck (design decision 10).
        source_template = (TEMPLATES_DIR / TIER_FILES[source_profile]).read_text(encoding="utf-8")
        deviation = check_upgradeable(source_text, source_template)
        if deviation is not None:
            raise NewError("source_not_upgradeable", deviation)

        template_text = (TEMPLATES_DIR / TIER_FILES[args.to]).read_text(encoding="utf-8")
        upgraded = upgrade_text(source_text, template_text, target_tier=args.to)

        # Gate 3: output self-validation (fail-closed, U6).
        try:
            out_doc = parse_document("<upgrade>", upgraded)
        except SpecParseError as exc:
            raise NewError("self_validation_failed", f"upgraded spec did not parse: {exc}") from exc
        out_findings = validate_document(out_doc, reg)
        if out_findings:
            raise NewError("self_validation_failed", "upgraded spec failed self-validation",
                           [dataclasses.asdict(f) for f in out_findings])

        return _deliver_upgrade(args, upgraded, source_profile=source_profile,
                                spec_id=src_doc.frontmatter.get("spec_id", ""))
    except NewError as err:
        return _emit_new_failure(json_mode, err)


def _deliver_upgrade(args: argparse.Namespace, text: str, *, source_profile: str, spec_id: str) -> int:
    # Task 9 fills in -i / -o; this task ships preview only.
    _upgrade_output(text, json_mode=args.json, source_profile=source_profile, target_tier=args.to,
                    spec_id=spec_id, path=None, mode="stdout", written=False)
    return 0
```

Register the verb and update usage:

```python
_USAGE = "usage: project-standards spec {validate|lint|extract|next|new|upgrade} ..."
# in _VERBS:
    "upgrade": _run_upgrade,
```

- [ ] **Step 8: Run to verify they pass**

Run: `uv run pytest tests/test_spec_upgrade.py tests/test_spec_upgrade_cli.py -v`
Expected: PASS (the `-i`/`-o` tests come in Task 9).

- [ ] **Step 9: Commit**

```bash
git add src/project_standards/specs/commands/upgrade.py src/project_standards/specs/cli.py tests/test_spec_upgrade.py tests/test_spec_upgrade_cli.py
git commit -m "feat(spec): upgrade precheck + CLI shell — three gates, tier direction, preview"
```

---

### Task 9: Write model — `-i` in-place and `-o` output delivery

Fill in `_deliver_upgrade`: `-i` atomically rewrites the source (overwrite-as-normal, mode preserved); `-o OUT` writes a new file (refuse-if-exists unless `--force`); `-o` resolving to the source is a conflict.

**Files:**
- Modify: `src/project_standards/specs/cli.py`
- Test: `tests/test_spec_upgrade_cli.py`

**Interfaces:**
- Consumes: `_safe_atomic_write` (Task 7); `os.path.samefile`.

- [ ] **Step 1: Write the failing tests**

```python
def test_in_place_rewrites_source_and_preserves_mode(tmp_path: Path) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    src.chmod(0o640)
    rc = _run([str(src), "--to", "standard", "-i"])
    assert rc == 0
    assert "profile: standard" in src.read_text(encoding="utf-8")
    assert (src.stat().st_mode & 0o777) == 0o640  # mode preserved


def test_output_refuses_existing_without_force(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    out = tmp_path / "out.md"
    out.write_text("existing\n", encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "-o", str(out), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "exists"
    rc2 = _run([str(src), "--to", "standard", "-o", str(out), "--force"])
    assert rc2 == 0 and "profile: standard" in out.read_text(encoding="utf-8")


def test_output_equal_to_source_is_conflict(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "-o", str(src), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "flag_conflict"


def test_json_success_payload_for_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    out = tmp_path / "out.md"
    rc = _run([str(src), "--to", "full", "-o", str(out), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 0 and obj["ok"] and obj["mode"] == "output"
    assert obj["from_profile"] == "light" and obj["to_profile"] == "full" and obj["written"] is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade_cli.py -k "in_place or output or json_success" -v`
Expected: FAIL — `_deliver_upgrade` only previews.

- [ ] **Step 3: Rewrite `_deliver_upgrade`**

```python
def _deliver_upgrade(args: argparse.Namespace, text: str, *, source_profile: str, spec_id: str) -> int:
    if args.in_place:
        target, mode = args.src, "in_place"
    elif args.output is not None:
        if args.output.exists() and args.src.exists() and os.path.samefile(args.output, args.src):
            raise NewError("flag_conflict", "output equals source; use --in-place")
        target, mode = args.output, "output"
    else:
        _upgrade_output(text, json_mode=args.json, source_profile=source_profile, target_tier=args.to,
                        spec_id=spec_id, path=None, mode="stdout", written=False)
        return 0
    # -i overwrites the source as the normal path; -o refuses an existing target unless --force.
    _safe_atomic_write(target, text, force=args.force or args.in_place)
    _upgrade_output(text, json_mode=args.json, source_profile=source_profile, target_tier=args.to,
                    spec_id=spec_id, path=str(target), mode=mode, written=True)
    return 0
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_spec_upgrade_cli.py -v`
Expected: all PASS.

- [ ] **Step 5: Add symlink-refusal coverage** (mirror `test_spec_new_cli.py`): a symlinked `-o` target and a symlinked in-tree parent → refused (`not_regular_file` / `symlinked_parent`) even with `--force`; assert via the `_safe_atomic_write` path. Run and commit.

```bash
git add src/project_standards/specs/cli.py tests/test_spec_upgrade_cli.py
git commit -m "feat(spec): upgrade -i in-place + -o output delivery with atomic safety"
```

---

### Task 10: Help string, package docs, dogfood, and full gate

**Files:**
- Modify: `src/project_standards/cli.py:245` (the `spec` group help string)
- Modify: `src/project_standards/README.md` (CLI table `:30-44` — document the `spec` group)
- Test: `tests/test_spec_upgrade_cli.py` (dogfood)

**Interfaces:** none new.

- [ ] **Step 1: Update the top-level help** — add `upgrade` to the `spec` subcommand advertisement at `src/project_standards/cli.py:245` (currently lists `validate|lint|extract|next|new`). Match the existing wording.

- [ ] **Step 1b: Update the package developer README (design SA-006)** — `src/project_standards/README.md`'s CLI table (`:30-44`) omits the nested `project-standards spec` command group entirely. Add a row (or short subsection) documenting the `spec` group's six verbs (`validate|lint|extract|next|new|upgrade`) so developer-facing docs are not left stale. (`src/**` is **not** in the frontmatter validator's `include`, so this README carries no frontmatter — a plain edit, no frontmatter to add.)

- [ ] **Step 2: Write the dogfood test**

```python
def test_dogfood_upgrade_then_validate_is_clean(tmp_path: Path) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    out = tmp_path / "up.md"
    assert _run([str(src), "--to", "full", "-o", str(out)]) == 0
    from project_standards.specs.cli import run as _run_group
    assert _run_group(["validate", str(out)]) == 0  # end-to-end U1
```

- [ ] **Step 3: Run the dogfood test**

Run: `uv run pytest tests/test_spec_upgrade_cli.py::test_dogfood_upgrade_then_validate_is_clean -v`
Expected: PASS.

- [ ] **Step 4: Run the full gate**

Run:
```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && \
uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && \
uv run validate-frontmatter --config .project-standards.yml
```
Expected: all green; branch coverage ≥ `fail_under`. Add targeted tests for any uncovered `upgrade.py`/`_run_upgrade` branch (e.g. `source_read_error` on a non-UTF-8 source, `mkdir_failed`, `write_failed`) until coverage holds.

- [ ] **Step 5: Update handoff docs** — mark Spec #3 implemented in `docs/handoff/specs-plans.md` and refresh `docs/handoff/state.md` (per the handoff-system-v3 ritual). Note in `TODO.md` that the `upgrade` command surface now needs a CHANGELOG line when `project-spec` is registered/released, and that the v1-core tool surface is complete.

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/cli.py src/project_standards/README.md tests/test_spec_upgrade_cli.py docs/handoff/specs-plans.md docs/handoff/state.md TODO.md
git commit -m "feat(spec): register upgrade in help + package README + dogfood; complete v1-core tool surface"
```

---

## Self-Review

**Spec coverage:** CLI surface + flag matrix → Task 8/9. Tier rules/direction → Task 8. **Triply-fail-closed pipeline (validate + upgradeability precheck + output self-validate) → Task 8.** Upgradeability precheck (decision 10, `source_not_upgradeable`, Codex SA-001/002/003) → Task 8 (`check_upgradeable`, pure reshape-identity). Appendix A/B/D template-owned (SA-NEW-001) → Task 4 (`_TEMPLATE_OWNED`) + Task 6 U3 covers Appendix B byte-for-byte. Splice/unit-ownership/three passes → Tasks 2–6. Canonical-position subsection insertion (SA-002) → Task 5. Module layout → Tasks 2 (new module), 7 (extract), 8 (shell + precheck). Write model + safety → Tasks 7, 9. No config coupling (SA-005) → Task 8 (no `--config`). Error/`--json` contract incl. `source_not_upgradeable` → Tasks 8, 9. Package README (SA-006) → Task 10 Step 1b. Testing (U1–U9) → U1 Task 6/10, U2 Tasks 4–6, U3 Task 6, U4 Task 8, U5 Task 8, U6 Task 8 (all three gates), U7 Tasks 7/9, U8 Tasks 8/9, U9 Tasks 8/9. Non-goals (no downgrade, no placeholder-fill, no revision entry, no non-canonical-scaffold merge) → enforced by additive-only + template-owned + precheck. Versioning/docs → Task 10 Steps 1b/5.

**Placeholder scan:** none — every code step shows real code; the one deliberate iteration point (Task 6 Step 4, byte-tuning against U3) is a TDD convergence loop against a concrete oracle, not a placeholder.

**Type consistency:** `upgrade_text(source_text, target_template_text, *, target_tier)` used identically in Tasks 6, 8. `_safe_atomic_write(target, text, *, force) -> bool` defined Task 7, consumed Tasks 7, 9. `_merge_top`/`_reconcile_shared`/`_top_blocks`/`_sub_blocks` signatures consistent across Tasks 3–6. `NewError(code, message, findings)` reused with the frozen slug set throughout.

**Known risk (surfaced, not hidden):** `_swap_tail`/`_is_filler` (Task 5) trims a trailing run of blank/`---`/omission-note lines; an author section whose body legitimately ends in a `>`-blockquote note containing "tier"+"omitted" would be over-trimmed. This is rare and is caught by the U3 round-trip (Task 6) and output self-validation (Task 8). If it bites, refine `_is_filler` to only treat a blockquote as filler when the target block's tail confirms it.
