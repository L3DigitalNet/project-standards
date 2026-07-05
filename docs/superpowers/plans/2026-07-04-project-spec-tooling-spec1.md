# Project-Spec Tooling (Spec #1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `project-standards spec validate|lint|extract|next` — read-only spec tooling over a shared registry core parsed from the bundled project-spec templates.

**Architecture:** A new `src/project_standards/specs/` subpackage. `registry.py` parses the three bundled canonical templates into a frozen `Registry`; `document.py` parses a consumer spec into a `SpecDocument`; four command modules diff document-against-registry (`validate`, `lint`) or slice/scan a single document (`extract`, `next`). A nested `spec` group is early-dispatched from the existing `cli.py`. `check_specs.py` is deleted and its checks move into the pytest gate.

**Tech Stack:** Python ≥3.14, `uv_build`, PyYAML, pytest + coverage (branch, `fail_under=85`), Ruff, BasedPyright strict. No new runtime dependencies.

## Global Constraints

- Python `>=3.14`; Ruff `target-version = py314`, line-length 100, double quotes, space indent.
- No new runtime dependencies (PyYAML + stdlib only). No new `[project.scripts]` entry point — `spec` is a subcommand of the existing `project-standards` console script.
- Exit codes everywhere: `0` ok · `1` findings/no-match · `2` bad invocation/config. Never a traceback on bad input.
- The bundled templates under `src/project_standards/specs/templates/` MUST stay byte-identical to `standards/project-spec/templates/` (dogfood guard).
- `--json` output shape is frozen by the spec (§ "`--json` output contract"); only the `SV-*`/`SL-*` code spellings are chosen during implementation.
- Every task ends green on the full gate: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`.
- Spec reference: `docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md`.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `src/project_standards/specs/__init__.py` | Package marker; re-export `load_registry`, `parse_document`. |
| `src/project_standards/specs/templates/*.md` | Byte-identical copies of the 3 canonical templates (ship in wheel). |
| `src/project_standards/specs/model.py` | Frozen dataclasses: `Registry`, `Finding`, `SpecDocument`. |
| `src/project_standards/specs/registry.py` | Parsing primitives + `load_registry()` building `Registry` from the 3 templates. |
| `src/project_standards/specs/document.py` | `parse_document()` → `SpecDocument`. |
| `src/project_standards/specs/config.py` | `load_spec_config()` reads the `spec:` block; `collect_spec_paths()`. |
| `src/project_standards/specs/commands/validate.py` | `validate_document()` → `list[Finding]` (integrity gate). |
| `src/project_standards/specs/commands/lint.py` | `lint_document()` → `list[Finding]` (advisory). |
| `src/project_standards/specs/commands/extract.py` | `extract_slice()` → slice result. |
| `src/project_standards/specs/commands/next_id.py` | `next_id()` → next free ID. |
| `src/project_standards/specs/cli.py` | `run(argv)` — `spec` subparser dispatch + `--json` rendering. |
| `src/project_standards/cli.py` | Add early-dispatch for `argv[0] == "spec"`. |
| `.github/workflows/validate-specs.yml` | Reusable `workflow_call` running `spec validate`. |
| `tests/test_spec_*.py` | Unit + integration tests per task. |
| `tests/test_template_conformance.py` | Maintainer dogfood (replaces `check_specs.py` per-file half). |
| `tests/test_template_interchangeability.py` | Cross-tier Defined-In identity (replaces cross-file half). |

---

## Task 1: Package skeleton, bundled templates, and packaging guard

**Files:**

- Create: `src/project_standards/specs/__init__.py`
- Create: `src/project_standards/specs/templates/spec-full-template.md` (copy)
- Create: `src/project_standards/specs/templates/spec-standard-template.md` (copy)
- Create: `src/project_standards/specs/templates/spec-light-template.md` (copy)
- Create: `tests/test_spec_packaging.py`

**Interfaces:**

- Produces: the package directory and `TEMPLATES_DIR` location every later task resolves templates from.

- [ ] **Step 1: Copy the templates into the package**

```bash
mkdir -p src/project_standards/specs/templates
cp standards/project-spec/templates/spec-full-template.md \
   standards/project-spec/templates/spec-standard-template.md \
   standards/project-spec/templates/spec-light-template.md \
   src/project_standards/specs/templates/
touch src/project_standards/specs/__init__.py
```

- [ ] **Step 2: Write the failing byte-identical + packaging test**

```python
# tests/test_spec_packaging.py
"""The bundled spec templates must ship in the wheel AND stay byte-identical
to the canonical copies under standards/project-spec/templates/."""

from __future__ import annotations

from pathlib import Path

import pytest

_TIERS = ("light", "standard", "full")
_PKG = Path(__file__).resolve().parent.parent / "src" / "project_standards" / "specs" / "templates"
_CANON = Path(__file__).resolve().parent.parent / "standards" / "project-spec" / "templates"


@pytest.mark.parametrize("tier", _TIERS)
def test_bundled_template_is_byte_identical(tier: str) -> None:
    name = f"spec-{tier}-template.md"
    assert (_PKG / name).read_bytes() == (_CANON / name).read_bytes()
```

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run pytest tests/test_spec_packaging.py -v` Expected: 3 PASS (the copies exist and match).

- [ ] **Step 4: Add a wheel-inclusion check**

Append to `tests/test_spec_packaging.py`:

```python
def test_templates_resolve_from_package_root() -> None:
    # uv_build ships everything under the module tree; assert the runtime lookup
    # path (Path(__file__)-relative, the same idiom as the bundled schema) exists.
    from project_standards import specs

    tdir = Path(specs.__file__).resolve().parent / "templates"
    assert sorted(p.name for p in tdir.glob("*.md")) == [
        "spec-full-template.md",
        "spec-light-template.md",
        "spec-standard-template.md",
    ]
```

- [ ] **Step 5: Run + commit**

Run: `uv run pytest tests/test_spec_packaging.py -v` → 4 PASS.

```bash
git add src/project_standards/specs/__init__.py src/project_standards/specs/templates tests/test_spec_packaging.py
git commit -m "feat(spec): bundle project-spec templates into the package with a byte-identical guard"
```

---

## Task 2: Parsing primitives + `Registry` model

Lift the proven primitives from `standards/project-spec/resources/check_specs.py` verbatim (they are already ruff-clean and tested-by-use), then build the `Registry`.

**Files:**

- Create: `src/project_standards/specs/model.py`
- Create: `src/project_standards/specs/registry.py`
- Create: `tests/test_spec_registry.py`

**Interfaces:**

- Produces:
  - `model.Registry` (frozen) with fields: `canonical_sections: frozenset[str]`, `section_titles: dict[str, str]`, `appendices: dict[str, frozenset[str]]` (per tier), `full_only_appendices: frozenset[str]`, `prefix_defined_in: dict[str, str]`, `frontmatter_keys: tuple[str, ...]`, `tier_sections: dict[str, frozenset[str]]`, `tier_prefixes: dict[str, frozenset[str]]`, `sentinel: str`, `spec_id_pattern: str`.
  - `registry.load_registry() -> Registry` (module-cached).
  - Primitives: `gh_slug`, `split_front_matter`, `headings`, `section_numbers`, `numkey`, `ID_TOKEN`, `NOT_AN_ID`, `TEMPLATES_DIR`, `TIER_FILES`.

- [ ] **Step 1: Write `model.py`**

```python
# src/project_standards/specs/model.py
"""Frozen data shapes shared across the spec tooling.

Registry = the canonical rules parsed once from the bundled templates.
Finding  = one validate/lint result (the frozen --json record).
SpecDocument = a parsed consumer spec (the thing under test).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Registry:
    canonical_sections: frozenset[str]
    section_titles: dict[str, str]
    appendices: dict[str, frozenset[str]]
    full_only_appendices: frozenset[str]
    prefix_defined_in: dict[str, str]
    frontmatter_keys: tuple[str, ...]
    tier_sections: dict[str, frozenset[str]]
    tier_prefixes: dict[str, frozenset[str]]
    sentinel: str
    spec_id_pattern: str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # "error" | "warning"
    message: str
    line: int | None = None
    locus: str | None = None


@dataclass
class SpecDocument:
    path: str
    profile: str | None
    frontmatter_keys: list[str]
    frontmatter: dict[str, str]  # first-level scalar values as raw strings
    body: str
    sections: list[tuple[str, int]]  # (number, line)
    slugs: frozenset[str]
    used_ids: dict[str, list[tuple[str, int]]]  # prefix -> [(full_id, line)]
    declared_prefixes: dict[str, str]  # prefix -> "Defined In" text
```

- [ ] **Step 2: Write `registry.py` primitives + parser**

Copy `gh_slug`, `split_front_matter`, `headings`, `section_numbers`, `numkey`, `ID_TOKEN`, and `NOT_AN_ID` verbatim from `check_specs.py` (lines 77–116 and the module constants), then add:

```python
# src/project_standards/specs/registry.py  (head)
"""Parse the three bundled canonical templates into the Registry.

Primitives are lifted verbatim from the retired resources/check_specs.py so the
consumer tooling and the maintainer tests share ONE rule extraction.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from project_standards.specs.model import Registry

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TIER_FILES = {
    "light": "spec-light-template.md",
    "standard": "spec-standard-template.md",
    "full": "spec-full-template.md",
}
SENTINEL = "SPEC-____"
SPEC_ID_PATTERN = r"^SPEC-[0-9A-Z]{4}$"

# --- primitives (verbatim from check_specs.py) ---------------------------
ID_TOKEN = re.compile(r"\b([A-Z]{1,4})-([0-9]+)\b")
NOT_AN_ID = {"HTTP", "HTTPS", "AES", "ISO", "IEC", "IEEE", "SHA", "RPO", "RTO", "UTF", "TLS", "API"}
# gh_slug, split_front_matter, headings, section_numbers, numkey: paste from check_specs.py
```

Then the builder:

```python
def _appendix_letters(body: str) -> list[str]:
    return re.findall(r"^## Appendix ([A-Z]):", body, re.M)


def _declared_prefixes(body: str) -> dict[str, str]:
    apx = re.search(r"## Appendix A:.*?(?=\n## |\Z)", body, re.S)
    declared: dict[str, str] = {}
    if apx:
        for row in re.finditer(
            r"^\|\s*`([A-Z]{1,4})-`\s*\|[^|]*\|\s*([^|]+?)\s*\|", apx.group(0), re.M
        ):
            declared[row.group(1)] = row.group(2).strip()
    return declared


@cache
def load_registry() -> Registry:
    tier_body: dict[str, str] = {}
    tier_fm: dict[str, str] = {}
    for tier, fname in TIER_FILES.items():
        fm, body = split_front_matter((TEMPLATES_DIR / fname).read_text(encoding="utf-8"))
        tier_body[tier] = body
        tier_fm[tier] = fm

    full = tier_body["full"]
    full_secs = section_numbers(headings(full))
    canonical = frozenset(n for n, _ in full_secs)
    titles = {
        n: t for (n, _), (_lvl, t, _ln) in zip(full_secs, _section_headings(full), strict=False)
    }

    tier_sections = {
        tier: frozenset(n for n, _ in section_numbers(headings(body)))
        for tier, body in tier_body.items()
    }
    appendices = {tier: frozenset(_appendix_letters(body)) for tier, body in tier_body.items()}
    tier_prefixes = {
        tier: frozenset(_declared_prefixes(body)) for tier, body in tier_body.items()
    }
    prefix_defined_in = _declared_prefixes(full)

    return Registry(
        canonical_sections=canonical,
        section_titles=titles,
        appendices=appendices,
        full_only_appendices=appendices["full"] - appendices["standard"],
        prefix_defined_in=prefix_defined_in,
        frontmatter_keys=tuple(_fm_keys(tier_fm["full"])),
        tier_sections=tier_sections,
        tier_prefixes=tier_prefixes,
        sentinel=SENTINEL,
        spec_id_pattern=SPEC_ID_PATTERN,
    )
```

Add helper `_fm_keys` (copy `fm_keys` from `check_specs.py`) and `_section_headings(body)` returning the numbered `headings()` entries in order (the `[hs for hs in headings(body) if section_numbers-matches]`); implement it by filtering `headings()` with the same regex `section_numbers` uses so titles align with numbers.

- [ ] **Step 3: Write failing registry invariant tests**

```python
# tests/test_spec_registry.py
from __future__ import annotations

from project_standards.specs.registry import load_registry


def test_canonical_sections_include_full_ladder() -> None:
    reg = load_registry()
    for n in ("1", "2", "7", "7.1", "17", "21"):
        assert n in reg.canonical_sections
    assert reg.tier_sections["light"] <= reg.tier_sections["standard"]
    assert reg.tier_sections["standard"] <= reg.tier_sections["full"]


def test_prefix_defined_in_and_tier_availability() -> None:
    reg = load_registry()
    assert reg.prefix_defined_in["FR"].startswith("7.1") or "7.1" in reg.prefix_defined_in["FR"]
    # R- is a Full-only risk id; must NOT be available at light/standard.
    assert "R" in reg.tier_prefixes["full"]
    assert "R" not in reg.tier_prefixes["standard"]
    assert "R" not in reg.tier_prefixes["light"]


def test_appendix_c_is_full_only() -> None:
    reg = load_registry()
    assert "C" in reg.full_only_appendices
    assert reg.frontmatter_keys[0] == "spec_id"
    assert reg.sentinel == "SPEC-____"
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_spec_registry.py -v` Expected: 3 PASS. If `FR`'s Defined-In assertion fails, print `reg.prefix_defined_in["FR"]` and adjust the assertion to the exact string (e.g. `"§7.1"`); do not weaken the R-tier assertions.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/model.py src/project_standards/specs/registry.py tests/test_spec_registry.py
git commit -m "feat(spec): registry parser deriving canonical rules from the bundled templates"
```

---

## Task 3: Consumer document parser

**Files:**

- Create: `src/project_standards/specs/document.py`
- Create: `tests/fixtures/specs/valid_light.md`, `tests/fixtures/specs/valid_standard.md`
- Create: `tests/test_spec_document.py`

**Interfaces:**

- Consumes: primitives from `registry.py`.
- Produces: `document.parse_document(path: str, text: str) -> SpecDocument`.

- [ ] **Step 1: Create a minimal valid fixture per tier**

Create `tests/fixtures/specs/valid_light.md` by copying the bundled Light template, then editing the frontmatter so it is a _filled_ consumer spec: replace `spec_id: SPEC-____` with `spec_id: SPEC-7F3Q`, and delete every `<angle-bracket>` placeholder / `> **Template instructions...` block and the `YYYY-MM-DD` dates (use `2026-07-04`). Do the same for `valid_standard.md` from the Standard template. Keep the canonical section numbers and IDs intact.

- [ ] **Step 2: Write `document.py`**

```python
# src/project_standards/specs/document.py
"""Parse a consumer spec into a SpecDocument (the thing validate/lint check)."""

from __future__ import annotations

import re

from project_standards.specs.model import SpecDocument
from project_standards.specs.registry import (
    ID_TOKEN,
    NOT_AN_ID,
    gh_slug,
    headings,
    section_numbers,
    split_front_matter,
)

_DECLARE_ROW = re.compile(r"^\|\s*`([A-Z]{1,4})-`\s*\|[^|]*\|\s*([^|]+?)\s*\|", re.M)


def _scalar_frontmatter(fm: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(\S.*?)\s*$", fm, re.M):
        out.setdefault(m.group(1), m.group(2))
    return out


def _fm_key_order(fm: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*):", fm, re.M)]


def parse_document(path: str, text: str) -> SpecDocument:
    fm, body = split_front_matter(text)
    hs = headings(body)
    scalars = _scalar_frontmatter(fm)
    used: dict[str, list[tuple[str, int]]] = {}
    for m in ID_TOKEN.finditer(body):
        pfx = m.group(1)
        if pfx in NOT_AN_ID:
            continue
        line = body[: m.start()].count("\n") + 1
        used.setdefault(pfx, []).append((f"{pfx}-{m.group(2)}", line))
    apx = re.search(r"## Appendix A:.*?(?=\n## |\Z)", body, re.S)
    declared = {r.group(1): r.group(2).strip() for r in _DECLARE_ROW.finditer(apx.group(0))} if apx else {}
    return SpecDocument(
        path=path,
        profile=scalars.get("profile"),
        frontmatter_keys=_fm_key_order(fm),
        frontmatter=scalars,
        body=body,
        sections=section_numbers(hs),
        slugs=frozenset(gh_slug(t) for _lvl, t, _ln in hs),
        used_ids=used,
        declared_prefixes=declared,
    )
```

- [ ] **Step 3: Write failing test**

```python
# tests/test_spec_document.py
from __future__ import annotations

from pathlib import Path

from project_standards.specs.document import parse_document

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def test_parse_valid_light() -> None:
    doc = parse_document("valid_light.md", (_FIX / "valid_light.md").read_text(encoding="utf-8"))
    assert doc.profile == "light"
    assert doc.frontmatter["spec_id"] == "SPEC-7F3Q"
    assert "FR" in doc.used_ids
    assert doc.frontmatter_keys[0] == "spec_id"
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_spec_document.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/document.py tests/fixtures/specs tests/test_spec_document.py
git commit -m "feat(spec): consumer spec document parser + valid fixtures"
```

---

## Task 4: `spec:` config + discovery

**Files:**

- Create: `src/project_standards/specs/config.py`
- Create: `tests/test_spec_config.py`

**Interfaces:**

- Consumes: `validate_frontmatter._glob_files`, `collect_paths` semantics, `ConfigError`.
- Produces:
  - `config.SpecConfig` (frozen) with `include: list[str]`, `exclude: list[str]`.
  - `config.load_spec_config(path: Path) -> SpecConfig`.
  - `config.collect_spec_paths(explicit: list[Path], cfg: SpecConfig) -> list[Path]` — raises `DiscoveryError` (subclass of `ConfigError`) when no source resolves any file.

- [ ] **Step 1: Write `config.py`**

```python
# src/project_standards/specs/config.py
"""Read the `spec:` block from .project-standards.yml and resolve target files.

Kept schema-separate from markdown.frontmatter.* — the two never share keys.
Reuses the frontmatter validator's globbing so exclude semantics stay identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from project_standards.validate_frontmatter import (
    ConfigError,
    _as_str_list,
    _glob_files,
    collect_paths,
)


class DiscoveryError(ConfigError):
    """No spec source resolved any file — exit 2 (never a vacuous green run)."""


@dataclass(frozen=True)
class SpecConfig:
    include: list[str]
    exclude: list[str]
    present: bool  # whether a `spec:` block existed at all


def load_spec_config(path: Path) -> SpecConfig:
    include: list[str] = []
    exclude: list[str] = []
    present = False
    if path.exists():
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(f"cannot read config {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ConfigError(f"cannot parse config {path}: {exc}") from exc
        if isinstance(raw, dict):
            block = cast("dict[str, Any]", raw).get("spec")
            if isinstance(block, dict):
                present = True
                b = cast("dict[str, Any]", block)
                include = _as_str_list(b.get("include"))
                exclude = _as_str_list(b.get("exclude"))
    return SpecConfig(include=include, exclude=exclude, present=present)


def collect_spec_paths(explicit: list[Path], cfg: SpecConfig) -> list[Path]:
    if not explicit and not cfg.present:
        raise DiscoveryError("no `spec:` config block and no paths given")
    paths = collect_paths(explicit, None, cfg.include, cfg.exclude)
    if not paths:
        raise DiscoveryError("spec discovery matched no files")
    return paths
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_spec_config.py
from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.config import DiscoveryError, collect_spec_paths, load_spec_config


def _write(tmp: Path, body: str) -> Path:
    cfg = tmp / ".project-standards.yml"
    cfg.write_text(body, encoding="utf-8")
    return cfg


def test_missing_spec_block_no_paths_raises(tmp_path: Path) -> None:
    cfg = load_spec_config(_write(tmp_path, "markdown:\n  frontmatter:\n    include: []\n"))
    assert cfg.present is False
    with pytest.raises(DiscoveryError):
        collect_spec_paths([], cfg)


def test_zero_match_include_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = load_spec_config(_write(tmp_path, "spec:\n  include:\n    - docs/specs/**/*.md\n"))
    assert cfg.present is True
    with pytest.raises(DiscoveryError):
        collect_spec_paths([], cfg)


def test_explicit_path_bypasses_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "a.md"
    spec.write_text("x", encoding="utf-8")
    cfg = load_spec_config(_write(tmp_path, "markdown:\n  frontmatter: {}\n"))
    assert collect_spec_paths([spec], cfg) == [spec]
```

- [ ] **Step 3: Run to verify pass**

Run: `uv run pytest tests/test_spec_config.py -v` → 3 PASS.

- [ ] **Step 4: Verify the reused helpers are importable**

Confirm `_as_str_list`, `_glob_files`, `collect_paths`, `ConfigError` exist in `validate_frontmatter.py` (they do — lines 565, 376, 391, 71). If Ruff flags the unused `_glob_files` import, remove it (only `collect_paths` is used).

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/config.py tests/test_spec_config.py
git commit -m "feat(spec): spec: config block + non-vacuous discovery"
```

---

## Task 5: `validate` — the integrity gate

The largest task: port `check_specs.check_file`'s per-file logic into a consumer validator, adapting frontmatter semantics (reject the sentinel; require the real pattern) and adding tier-prefix + Defined-In-identity checks.

**Files:**

- Create: `src/project_standards/specs/commands/__init__.py`
- Create: `src/project_standards/specs/commands/validate.py`
- Create: `tests/fixtures/specs/bad_*.md` (one per rule)
- Create: `tests/test_spec_validate.py`

**Interfaces:**

- Consumes: `Registry`, `SpecDocument`, `Finding`.
- Produces: `validate.validate_document(doc: SpecDocument, reg: Registry) -> list[Finding]` (empty = pass).

- [ ] **Step 1: Write `validate.py`**

```python
# src/project_standards/specs/commands/validate.py
"""Deterministic integrity gate: does this SpecDocument conform to the Registry?

Every finding here is severity="error"; a non-empty list means exit 1.
Ported from check_specs.check_file, minus the maintainer sentinel expectation.
"""

from __future__ import annotations

import re

from project_standards.specs.model import Finding, Registry, SpecDocument
from project_standards.specs.registry import numkey

_OMIT = re.compile(r"§(\d+)\s*[–-]\s*§?(\d+)")
_OMIT_SINGLE = re.compile(r"§(\d+)")
_SECTION_REF = re.compile(r"§\s?([0-9]+(?:\.[0-9]+)*)")
_ANCHOR = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")


def _f(code: str, message: str, line: int | None = None, locus: str | None = None) -> Finding:
    return Finding(code=code, severity="error", message=message, line=line, locus=locus)


def validate_document(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    out += _check_frontmatter(doc, reg)
    out += _check_sections(doc, reg)
    out += _check_appendices(doc, reg)
    out += _check_references(doc, reg)
    out += _check_ids(doc, reg)
    out += _check_tables(doc)
    return out


def _check_frontmatter(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    if tuple(doc.frontmatter_keys) != reg.frontmatter_keys:
        out.append(_f("SV-FM-KEYS", f"frontmatter keys {doc.frontmatter_keys} != {list(reg.frontmatter_keys)}"))
    spec_id = doc.frontmatter.get("spec_id", "")
    if spec_id == reg.sentinel:
        out.append(_f("SV-SENTINEL", "spec_id is the unfilled sentinel SPEC-____", locus="spec_id"))
    elif not re.match(reg.spec_id_pattern, spec_id):
        out.append(_f("SV-SPEC-ID", f"spec_id {spec_id!r} does not match {reg.spec_id_pattern}", locus="spec_id"))
    status = doc.frontmatter.get("status")
    if status not in {"draft", "review", "approved", "superseded"}:
        out.append(_f("SV-STATUS", f"status {status!r} not in draft|review|approved|superseded", locus="status"))
    if doc.profile not in reg.tier_sections:
        out.append(_f("SV-PROFILE", f"profile {doc.profile!r} not in light|standard|full", locus="profile"))
    return out


def _check_sections(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    for n, ln in doc.sections:
        if n not in reg.canonical_sections:
            out.append(_f("SV-SECTION", f"§{n} is not in the canonical registry", line=ln, locus=f"§{n}"))
    order = [numkey(n) for n, _ in doc.sections]
    if order != sorted(order):
        out.append(_f("SV-ORDER", "section headings are not in ascending numeric order"))
    covered: set[int] = set()
    for line in doc.body.splitlines():
        if line.lstrip().startswith(">") and "tier" in line and "omitted" in line:
            for a, b in _OMIT.findall(line):
                covered.update(range(int(a), int(b) + 1))
            covered.update(int(x) for x in _OMIT_SINGLE.findall(line))
    canon_top = {int(n) for n in reg.canonical_sections if "." not in n}
    present_top = {int(n) for n, _ in doc.sections if "." not in n}
    for n in sorted(canon_top - present_top):
        if n not in covered:
            out.append(_f("SV-GAP", f"gap at §{n} is not annotated with an omission note", locus=f"§{n}"))
    return out


def _check_appendices(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    apps = re.findall(r"^## Appendix ([A-Z]):", doc.body, re.M)
    if apps != sorted(apps):
        out.append(_f("SV-APX-ORDER", f"appendix letters not ascending: {apps}"))
    for required in ("A", "B", "D"):
        if required not in apps:
            out.append(_f("SV-APX-MISSING", f"Appendix {required} missing"))
    full_only = reg.full_only_appendices
    if doc.profile == "full":
        for letter in full_only:
            if letter not in apps:
                out.append(_f("SV-APX-FULL", f"Full must contain Appendix {letter}"))
    else:
        for letter in full_only:
            if letter in apps:
                out.append(_f("SV-APX-FULLONLY", f"Appendix {letter} is Full-only", locus=letter))
    return out


def _check_references(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    for m in _SECTION_REF.finditer(doc.body):
        ref = m.group(1)
        if ref not in reg.canonical_sections and ref.split(".")[0] not in reg.canonical_sections:
            ln = doc.body[: m.start()].count("\n") + 1
            out.append(_f("SV-XREF", f"§{ref} not in canonical registry", line=ln, locus=f"§{ref}"))
    for m in _ANCHOR.finditer(doc.body):
        if m.group(2) not in doc.slugs:
            ln = doc.body[: m.start()].count("\n") + 1
            out.append(_f("SV-ANCHOR", f"dead anchor #{m.group(2)}", line=ln, locus=m.group(2)))
    return out


def _check_ids(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    seen: set[str] = set()
    tier_ok = reg.tier_prefixes.get(doc.profile or "", frozenset())
    for pfx, occurrences in doc.used_ids.items():
        for full_id, ln in occurrences:
            digits = full_id.split("-", 1)[1]
            ok = (pfx == "MS" and len(digits) == 1) or (pfx != "MS" and len(digits) == 3)
            if not ok:
                out.append(_f("SV-ID-FMT", f"{full_id} bad width", line=ln, locus=full_id))
            if full_id in seen:
                out.append(_f("SV-ID-DUP", f"duplicate id {full_id}", line=ln, locus=full_id))
            seen.add(full_id)
        if pfx not in doc.declared_prefixes:
            out.append(_f("SV-ID-UNDECLARED", f"prefix {pfx}- used but not in Appendix A", locus=f"{pfx}-"))
        elif pfx not in tier_ok:
            out.append(_f("SV-ID-TIER", f"prefix {pfx}- not valid at {doc.profile} tier", locus=f"{pfx}-"))
    for pfx, definedin in doc.declared_prefixes.items():
        canon = reg.prefix_defined_in.get(pfx)
        if canon is not None and definedin != canon:
            out.append(_f("SV-ID-DEFINED", f"{pfx}- Defined In {definedin!r} != canonical {canon!r}", locus=f"{pfx}-"))
    return out


def _check_tables(doc: SpecDocument) -> list[Finding]:
    out: list[Finding] = []
    lines = doc.body.splitlines()
    i = 0
    while i < len(lines):
        if (
            lines[i].strip().startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])
        ):
            cols = lines[i].count("|")
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                if j != i + 1 and lines[j].count("|") != cols:
                    out.append(_f("SV-TABLE", f"L{j + 1}: {lines[j].count('|')} pipes vs header {cols}", line=j + 1))
                j += 1
            i = j
        else:
            i += 1
    return out
```

- [ ] **Step 2: Create one bad fixture per rule**

From `tests/fixtures/specs/valid_standard.md`, make single-mutation copies under `tests/fixtures/specs/`:

- `bad_sentinel.md` — `spec_id: SPEC-____`
- `bad_spec_id.md` — `spec_id: SPEC-123`
- `bad_dup_id.md` — a duplicated `FR-001` row
- `bad_undeclared.md` — introduce a `ZZ-001` in the body
- `bad_tier_prefix.md` — a Full-only `R-001` in a `profile: standard` spec (also add `R-` to its Appendix A so the failure is SV-ID-TIER, not SV-ID-UNDECLARED)
- `bad_gap.md` — delete one omission-note blockquote
- `bad_anchor.md` — change an intra-doc link target to `#nope`
- `bad_table.md` — drop a `|` from one table row

- [ ] **Step 3: Write failing tests (valid passes, each bad → its code)**

```python
# tests/test_spec_validate.py
from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _codes(name: str) -> set[str]:
    doc = parse_document(name, (_FIX / name).read_text(encoding="utf-8"))
    return {f.code for f in validate_document(doc, load_registry())}


@pytest.mark.parametrize("name", ["valid_light.md", "valid_standard.md"])
def test_valid_specs_pass(name: str) -> None:
    assert _codes(name) == set()


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("bad_sentinel.md", "SV-SENTINEL"),
        ("bad_spec_id.md", "SV-SPEC-ID"),
        ("bad_dup_id.md", "SV-ID-DUP"),
        ("bad_undeclared.md", "SV-ID-UNDECLARED"),
        ("bad_tier_prefix.md", "SV-ID-TIER"),
        ("bad_gap.md", "SV-GAP"),
        ("bad_anchor.md", "SV-ANCHOR"),
        ("bad_table.md", "SV-TABLE"),
    ],
)
def test_bad_fixture_reports_code(name: str, code: str) -> None:
    assert code in _codes(name)
```

- [ ] **Step 4: Run + iterate on fixtures**

Run: `uv run pytest tests/test_spec_validate.py -v`. If a valid fixture emits findings, fix the _fixture_ (it was not fully filled), not the validator. If a bad fixture emits extra codes that is fine — the test only asserts the target code is present.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/__init__.py src/project_standards/specs/commands/validate.py tests/fixtures/specs/bad_*.md tests/test_spec_validate.py
git commit -m "feat(spec): validate integrity gate + single-rule fixtures"
```

---

## Task 6: `lint` — advisory authoring quality

**Files:**

- Create: `src/project_standards/specs/commands/lint.py`
- Create: `tests/fixtures/specs/draft_placeholders.md`, `tests/fixtures/specs/approved_light.md`
- Create: `tests/test_spec_lint.py`

**Interfaces:**

- Consumes: `Registry`, `SpecDocument`, `Finding`.
- Produces: `lint.lint_document(doc: SpecDocument, reg: Registry) -> list[Finding]` (all severity `warning`).

- [ ] **Step 1: Write `lint.py`**

```python
# src/project_standards/specs/commands/lint.py
"""Advisory authoring-quality warnings on a spec that already passes validate.

Every finding is severity="warning"; exit stays 0 unless the caller passes
--strict. Placeholders/guidance and traceability only — integrity lives in validate.
"""

from __future__ import annotations

import re

from project_standards.specs.model import Finding, Registry, SpecDocument

_ANGLE = re.compile(r"<[^>\n]+>")
_GUIDANCE = "> **Template instructions"


def _w(code: str, message: str, line: int | None = None, locus: str | None = None) -> Finding:
    return Finding(code=code, severity="warning", message=message, line=line, locus=locus)


def lint_document(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    for i, line in enumerate(doc.body.splitlines(), start=1):
        if _ANGLE.search(line):
            out.append(_w("SL-PLACEHOLDER", "unfilled <angle-bracket> placeholder", line=i))
        if line.lstrip().startswith(_GUIDANCE):
            out.append(_w("SL-GUIDANCE", "template guidance not deleted", line=i))
    if doc.frontmatter.get("status") == "approved":
        out += _traceability(doc, reg)
    return out


def _traceability(doc: SpecDocument, reg: Registry) -> list[Finding]:
    has_matrix = "17.3" in reg.tier_sections.get(doc.profile or "", frozenset())
    if has_matrix:
        # Standard/Full: every Must FR should appear in the §17.3 matrix.
        matrix = _section_body(doc.body, "17.3")
        missing = [fid for fid, _ in doc.used_ids.get("FR", []) if fid not in matrix]
        return [_w("SL-TRACE", f"Must requirement {fid} not mapped in §17.3", locus=fid) for fid in dict.fromkeys(missing)]
    # Light: no §17.3 — flag unchecked §17.1 DoD items instead.
    dod = _section_body(doc.body, "17.1")
    return [_w("SL-DOD", "unchecked Definition-of-Done item in §17.1")] if "- [ ]" in dod else []


def _section_body(body: str, number: str) -> str:
    m = re.search(rf"^#+\s*{re.escape(number)}\b.*?(?=^#+\s|\Z)", body, re.M | re.S)
    return m.group(0) if m else ""
```

- [ ] **Step 2: Create fixtures**

- `draft_placeholders.md` — copy the Light template unchanged (`status: draft`, retains `<...>` + guidance).
- `approved_light.md` — copy `valid_light.md`, set `status: approved`, ensure §17.1 has an unchecked `- [ ]` item.

- [ ] **Step 3: Write failing tests**

```python
# tests/test_spec_lint.py
from __future__ import annotations

from pathlib import Path

from project_standards.specs.commands.lint import lint_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _codes(name: str) -> set[str]:
    doc = parse_document(name, (_FIX / name).read_text(encoding="utf-8"))
    return {f.code for f in lint_document(doc, load_registry())}


def test_draft_placeholders_warn() -> None:
    assert "SL-PLACEHOLDER" in _codes("draft_placeholders.md")


def test_approved_light_flags_dod_not_matrix() -> None:
    codes = _codes("approved_light.md")
    assert "SL-DOD" in codes
    assert "SL-TRACE" not in codes  # Light must never be failed for lacking §17.3


def test_valid_light_is_clean() -> None:
    assert _codes("valid_light.md") == set()
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_spec_lint.py -v`. If `valid_light.md` warns on `SL-PLACEHOLDER`, remove the residual `<...>` token from the fixture (a leftover placeholder is exactly what lint should catch).

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/lint.py tests/fixtures/specs/draft_placeholders.md tests/fixtures/specs/approved_light.md tests/test_spec_lint.py
git commit -m "feat(spec): advisory lint (placeholders, guidance, traceability)"
```

---

## Task 7: `extract`

**Files:**

- Create: `src/project_standards/specs/commands/extract.py`
- Create: `tests/test_spec_extract.py`

**Interfaces:**

- Produces: `extract.extract_slice(doc: SpecDocument, selector: str) -> ExtractResult` where `@dataclass(frozen=True) class ExtractResult: kind: str; found: bool; markdown: str | None; selector: str`. Selector grammar: `FR-013` (id row), `§7` / `§7.1` (section), `Appendix B` (appendix), else heading-text match.

- [ ] **Step 1: Write `extract.py`**

```python
# src/project_standards/specs/commands/extract.py
"""Print one slice of a spec (id row / section / appendix / heading) as markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass

from project_standards.specs.model import SpecDocument
from project_standards.specs.registry import ID_TOKEN


@dataclass(frozen=True)
class ExtractResult:
    kind: str
    found: bool
    markdown: str | None
    selector: str


def _section_slice(body: str, number: str) -> str | None:
    m = re.search(rf"^#+\s*{re.escape(number)}\b.*?(?=^#+\s|\Z)", body, re.M | re.S)
    return m.group(0).rstrip() if m else None


def _appendix_slice(body: str, letter: str) -> str | None:
    m = re.search(rf"^## Appendix {re.escape(letter)}:.*?(?=^## |\Z)", body, re.M | re.S)
    return m.group(0).rstrip() if m else None


def _id_row(body: str, spec_id: str) -> str | None:
    for line in body.splitlines():
        if line.lstrip().startswith("|") and re.search(rf"\b{re.escape(spec_id)}\b", line):
            return line.strip()
    return None


def extract_slice(doc: SpecDocument, selector: str) -> ExtractResult:
    body = doc.body
    if ID_TOKEN.fullmatch(selector):
        return ExtractResult("id", (r := _id_row(body, selector)) is not None, r, selector)
    if selector.startswith("§"):
        return ExtractResult("section", (r := _section_slice(body, selector[1:])) is not None, r, selector)
    if selector.lower().startswith("appendix "):
        letter = selector.split()[1].upper()
        return ExtractResult("appendix", (r := _appendix_slice(body, letter)) is not None, r, selector)
    m = re.search(rf"^#+\s.*{re.escape(selector)}.*?(?=^#+\s|\Z)", body, re.M | re.S)
    return ExtractResult("heading", m is not None, m.group(0).rstrip() if m else None, selector)
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_spec_extract.py
from __future__ import annotations

from pathlib import Path

from project_standards.specs.commands.extract import extract_slice
from project_standards.specs.document import parse_document

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _doc():
    return parse_document("valid_standard.md", (_FIX / "valid_standard.md").read_text(encoding="utf-8"))


def test_extract_section_found() -> None:
    r = extract_slice(_doc(), "§7")
    assert r.found and r.kind == "section" and r.markdown
    assert r.markdown.lstrip().startswith("#")


def test_extract_appendix_found() -> None:
    assert extract_slice(_doc(), "Appendix B").found


def test_extract_missing_id_not_found() -> None:
    r = extract_slice(_doc(), "FR-999")
    assert not r.found and r.markdown is None
```

- [ ] **Step 3: Run to verify pass**

Run: `uv run pytest tests/test_spec_extract.py -v` → 3 PASS.

- [ ] **Step 4: Commit**

```bash
git add src/project_standards/specs/commands/extract.py tests/test_spec_extract.py
git commit -m "feat(spec): extract slices (id/section/appendix/heading)"
```

---

## Task 8: `next`

**Files:**

- Create: `src/project_standards/specs/commands/next_id.py`
- Create: `tests/test_spec_next.py`

**Interfaces:**

- Consumes: `SpecDocument`, `Registry`.
- Produces: `next_id.next_free_id(doc: SpecDocument, reg: Registry, prefix: str) -> str`; raises `ValueError` on an unknown/tier-invalid prefix.

- [ ] **Step 1: Write `next_id.py`**

```python
# src/project_standards/specs/commands/next_id.py
"""Compute the next free ID for a prefix, honoring the width rules."""

from __future__ import annotations

from project_standards.specs.model import Registry, SpecDocument


def next_free_id(doc: SpecDocument, reg: Registry, prefix: str) -> str:
    prefix = prefix.rstrip("-").upper()
    tier_ok = reg.tier_prefixes.get(doc.profile or "full", frozenset())
    if prefix not in reg.prefix_defined_in:
        raise ValueError(f"unknown prefix {prefix!r}")
    if prefix not in tier_ok:
        raise ValueError(f"prefix {prefix!r} not valid at {doc.profile} tier")
    used = doc.used_ids.get(prefix, [])
    highest = max((int(fid.split("-", 1)[1]) for fid, _ in used), default=0)
    nxt = highest + 1
    return f"{prefix}-{nxt}" if prefix == "MS" else f"{prefix}-{nxt:03d}"
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_spec_next.py
from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.next_id import next_free_id
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _doc(name: str = "valid_standard.md"):
    return parse_document(name, (_FIX / name).read_text(encoding="utf-8"))


def test_next_fr_is_zero_padded() -> None:
    nid = next_free_id(_doc(), load_registry(), "FR")
    assert nid.startswith("FR-") and len(nid.split("-")[1]) == 3


def test_unknown_prefix_raises() -> None:
    with pytest.raises(ValueError, match="unknown prefix"):
        next_free_id(_doc(), load_registry(), "ZZ")


def test_ms_is_single_digit() -> None:
    nid = next_free_id(_doc(), load_registry(), "MS")
    assert nid.startswith("MS-") and len(nid.split("-")[1]) == 1
```

- [ ] **Step 3: Run to verify pass**

Run: `uv run pytest tests/test_spec_next.py -v`. If `MS` raises tier-invalid on the Standard fixture, use `valid_standard.md` (Standard has `MS-`); adjust only if the registry shows `MS` absent there.

- [ ] **Step 4: Commit**

```bash
git add src/project_standards/specs/commands/next_id.py tests/test_spec_next.py
git commit -m "feat(spec): next-free-id assignment with width + tier rules"
```

---

## Task 9: CLI wiring + `--json` rendering

**Files:**

- Create: `src/project_standards/specs/cli.py`
- Modify: `src/project_standards/cli.py` (add early-dispatch)
- Create: `tests/test_spec_cli.py`

**Interfaces:**

- Consumes: all four command functions, `load_registry`, `parse_document`, `load_spec_config`, `collect_spec_paths`.
- Produces: `specs.cli.run(argv: list[str]) -> int`; wired so `project_standards.cli.main(["spec", ...])` reaches it.

- [ ] **Step 1: Write `specs/cli.py`**

```python
# src/project_standards/specs/cli.py
"""`project-standards spec <verb>` dispatch + --json rendering.

Sits inside its own error boundary: ConfigError/DiscoveryError -> exit 2,
unreadable/again-bad input -> located message, never a traceback.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from project_standards.specs.commands.extract import extract_slice
from project_standards.specs.commands.lint import lint_document
from project_standards.specs.commands.next_id import next_free_id
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.config import ConfigError, collect_spec_paths, load_spec_config
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_DEFAULT_CONFIG = Path(".project-standards.yml")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"cannot read spec {path}: {exc}") from exc


def _findings_payload(results: list[tuple[Path, list]]) -> list[dict[str, object]]:
    return [
        {"file": str(p), "ok": not fs, "findings": [dataclasses.asdict(f) for f in fs]}
        for p, fs in results
    ]


def _run_setwide(argv: list[str], *, lint: bool) -> int:
    ap = argparse.ArgumentParser(prog=f"project-standards spec {'lint' if lint else 'validate'}")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    reg = load_registry()
    cfg = load_spec_config(args.config)
    paths = collect_spec_paths(args.files, cfg)
    results = [
        (p, (lint_document if lint else validate_document)(parse_document(str(p), _read(p)), reg))
        for p in paths
    ]
    if args.json:
        print(json.dumps(_findings_payload(results), indent=2))
    else:
        for p, fs in results:
            print(f"{'WARN' if lint else 'FAIL' if fs else 'OK  '} {p}")
            for f in fs:
                print(f"   [{f.code}] {f.message}" + (f" (L{f.line})" if f.line else ""))
    any_findings = any(fs for _, fs in results)
    if lint:
        return 1 if (any_findings and args.strict) else 0
    return 1 if any_findings else 0


def _run_extract(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec extract")
    ap.add_argument("file", type=Path)
    ap.add_argument("selector")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = parse_document(str(args.file), _read(args.file))
    r = extract_slice(doc, args.selector)
    if args.json:
        print(json.dumps({"file": str(args.file), "selector": r.selector, "kind": r.kind, "found": r.found, "markdown": r.markdown}))
    elif r.found:
        print(r.markdown)
    else:
        print(f"no match for {r.selector!r}", file=sys.stderr)
    return 0 if r.found else 1


def _run_next(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec next")
    ap.add_argument("file", type=Path)
    ap.add_argument("prefix")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = parse_document(str(args.file), _read(args.file))
    try:
        nid = next_free_id(doc, load_registry(), args.prefix)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"file": str(args.file), "prefix": args.prefix.rstrip('-').upper(), "next_id": nid}) if args.json else nid)
    return 0


_VERBS = {"validate": lambda a: _run_setwide(a, lint=False), "lint": lambda a: _run_setwide(a, lint=True), "extract": _run_extract, "next": _run_next}


def run(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print("usage: project-standards spec {validate|lint|extract|next} ...", file=sys.stderr)
        return 0 if argv[:1] in ([], ["-h"], ["--help"]) else 2
    verb, rest = argv[0], argv[1:]
    if verb not in _VERBS:
        print(f"error: unknown spec verb {verb!r}", file=sys.stderr)
        return 2
    try:
        return _VERBS[verb](rest)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
```

- [ ] **Step 2: Add early-dispatch to `cli.py`**

In `src/project_standards/cli.py`, immediately after the `fix` early-dispatch block (before `parser = argparse.ArgumentParser(...)`), add:

```python
    if args_list and args_list[0] == "spec":
        from project_standards.specs.cli import run as _spec_run

        return _spec_run(args_list[1:])
```

And register it for `--help` visibility with the other `sub.add_parser` calls:

```python
    sub.add_parser("spec", help="validate|lint|extract|next over project specs")
```

- [ ] **Step 3: Write failing integration tests**

```python
# tests/test_spec_cli.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.cli import main

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def test_spec_validate_valid_exit0(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["spec", "validate", str(_FIX / "valid_standard.md")]) == 0


def test_spec_validate_bad_exit1_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["spec", "validate", "--json", str(_FIX / "bad_dup_id.md")])
    data = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert any(f["code"] == "SV-ID-DUP" for f in data[0]["findings"])


def test_spec_missing_config_exit2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["spec", "validate"]) == 2


def test_spec_next_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["spec", "next", "--json", str(_FIX / "valid_standard.md"), "FR"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["next_id"].startswith("FR-")
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_spec_cli.py -v` → 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/cli.py src/project_standards/cli.py tests/test_spec_cli.py
git commit -m "feat(spec): wire the spec subcommand group into the CLI with --json"
```

---

## Task 10: Retire `check_specs.py` into the pytest gate + doc reconciliation

**Files:**

- Delete: `standards/project-spec/resources/check_specs.py`
- Create: `tests/test_template_conformance.py`
- Create: `tests/test_template_interchangeability.py`
- Modify: `standards/project-spec/resources/tooling-notes.md` (§8 demote #4/#5; §11 reference update)
- Modify: `standards/project-spec/README.md` (§5 lint/validate reconciliation; §8/§9 references)

**Interfaces:**

- Consumes: `load_registry`, `parse_document`, `validate_document`.

- [ ] **Step 1: Write the maintainer conformance test (expects the sentinel)**

```python
# tests/test_template_conformance.py
"""Maintainer dogfood: the 3 bundled templates are structurally sound.

A template is deliberately NOT a valid consumer spec (it carries SPEC-____ and
<angle-bracket> placeholders). So we assert every validate finding is one of the
KNOWN template-only findings (sentinel + placeholders), never a structural one.
"""

from __future__ import annotations

import pytest

from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES, load_registry

_ALLOWED = {"SV-SENTINEL"}  # the intentional unfilled sentinel; nothing else


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_template_has_no_structural_findings(tier: str) -> None:
    path = TEMPLATES_DIR / TIER_FILES[tier]
    doc = parse_document(str(path), path.read_text(encoding="utf-8"))
    codes = {f.code for f in validate_document(doc, load_registry())}
    assert codes <= _ALLOWED, f"unexpected structural findings: {codes - _ALLOWED}"
```

- [ ] **Step 2: Run — this is the acid test of the whole registry**

Run: `uv run pytest tests/test_template_conformance.py -v` Expected: 3 PASS. If a template emits e.g. `SV-XREF` or `SV-GAP`, the registry parser has a real bug (or `_ALLOWED` is too narrow because the templates legitimately contain `<...>` in prose) — debug the parser/validator, do NOT widen `_ALLOWED` beyond the genuinely intentional sentinel. (If placeholder angle-brackets in _prose_ trip a validate check, that check is wrong — validate must not inspect `<...>`; only lint does.)

- [ ] **Step 3: Write the interchangeability test (cross-tier Defined-In identity)**

```python
# tests/test_template_interchangeability.py
"""The one cross-file guarantee check_specs.py owned: a shared ID prefix resolves
to the SAME 'Defined In' section in every tier that declares it (G2/G3)."""

from __future__ import annotations

from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES, _declared_prefixes, split_front_matter


def test_defined_in_identical_across_tiers() -> None:
    per_tier = {}
    for tier, fname in TIER_FILES.items():
        _fm, body = split_front_matter((TEMPLATES_DIR / fname).read_text(encoding="utf-8"))
        per_tier[tier] = _declared_prefixes(body)
    shared = set(per_tier["light"]) & set(per_tier["standard"]) & set(per_tier["full"])
    for pfx in shared:
        values = {per_tier[t][pfx] for t in TIER_FILES}
        assert len(values) == 1, f"{pfx}- Defined In differs across tiers: {values}"
```

- [ ] **Step 4: Delete the script and update docs**

```bash
git rm standards/project-spec/resources/check_specs.py
```

In `standards/project-spec/resources/tooling-notes.md`:

- §8 guarantees #4 ("shared example IDs identical") and #5 ("shared boilerplate identical"): append to each `— documented convention, **not currently machine-checked**.`
- §11: replace the `check_specs.py` paragraph with a pointer to `project-standards spec validate` (consumer) and `tests/test_template_conformance.py` + `tests/test_template_interchangeability.py` (maintainer).

In `standards/project-spec/README.md`:

- §5 `validate`/`lint` capability bullets: move ID uniqueness, `used ⊆ declared`, and sentinel detection into the `validate` description; leave `<angle-bracket>`/guidance placeholders + traceability under `lint`.
- §8/§9: replace `resources/check_specs.py` links with the two maintainer tests + the `spec validate` command.

- [ ] **Step 5: Run gate + Prettier + commit**

```bash
uv run pytest tests/test_template_conformance.py tests/test_template_interchangeability.py -v
npx prettier --write standards/project-spec/README.md standards/project-spec/resources/tooling-notes.md
npx markdownlint-cli2 standards/project-spec/README.md standards/project-spec/resources/tooling-notes.md
git add -A standards/project-spec tests/test_template_conformance.py tests/test_template_interchangeability.py
git commit -m "refactor(spec): retire check_specs.py into the pytest gate; reconcile docs"
```

(Note: `git add -A` here is scoped to the named paths, satisfying the repo's explicit-add rule.)

---

## Task 11: Reusable `validate-specs.yml` workflow

**Files:**

- Create: `.github/workflows/validate-specs.yml`
- Create: `tests/test_validate_specs_workflow.py`

- [ ] **Step 1: Write the workflow (mirror `validate-markdown-frontmatter.yml`)**

```yaml
# .github/workflows/validate-specs.yml
name: Validate Specs

on:
  push:
    branches: ['main']
    paths: ['**/*.md', 'src/**', '.project-standards.yml', 'pyproject.toml']
  pull_request:
    paths: ['**/*.md', 'src/**', '.project-standards.yml', 'pyproject.toml']
  workflow_call:
    inputs:
      config-path:
        description: 'Path to the project standards config file in the calling repo.'
        required: false
        type: string
        default: '.project-standards.yml'
      standards-ref:
        description: 'project-standards git ref to install from (match your uses: @vN pin).'
        required: false
        type: string
        default: 'v3'
      strict-lint:
        description: 'Also run `spec lint --strict` (fail on advisory warnings).'
        required: false
        type: boolean
        default: false

jobs:
  validate-specs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Install project-standards
        run: uv tool install "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v3' }}"
      - name: Validate specs
        run: project-standards spec validate --config "${{ inputs.config-path || '.project-standards.yml' }}"
      - name: Lint specs (strict, optional)
        if: ${{ inputs.strict-lint }}
        run: project-standards spec lint --strict --config "${{ inputs.config-path || '.project-standards.yml' }}"
```

- [ ] **Step 2: Write a presence/shape test (mirror existing workflow tests)**

```python
# tests/test_validate_specs_workflow.py
from __future__ import annotations

from pathlib import Path

import yaml

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "validate-specs.yml"


def test_workflow_exposes_workflow_call_with_config_and_ref() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    call = data[True]["workflow_call"]  # PyYAML parses bare `on:` key as boolean True
    assert set(call["inputs"]) >= {"config-path", "standards-ref", "strict-lint"}


def test_workflow_runs_spec_validate() -> None:
    assert "spec validate" in _WF.read_text(encoding="utf-8")
```

- [ ] **Step 3: Run to verify pass**

Run: `uv run pytest tests/test_validate_specs_workflow.py -v` → 2 PASS. (If `data[True]` KeyErrors, the repo's other workflow tests show the exact idiom for the parsed `on:` key — match it.)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/validate-specs.yml tests/test_validate_specs_workflow.py
git commit -m "feat(spec): reusable validate-specs.yml workflow"
```

---

## Task 12: Full-gate green + coverage top-up

**Files:**

- Modify: any `specs/**` module or test needing coverage lines.

- [ ] **Step 1: Run the whole gate**

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

- [ ] **Step 2: Fix formatting/type/coverage gaps**

Run `uv run ruff format .` for any format diff. For `basedpyright` strict errors in `specs/**`, add precise annotations (no `Any` leaks; the `cast` idiom from `validate_frontmatter.py` is the house pattern). If `coverage report` shows an uncovered branch in a command module, add the specific fixture/assert that exercises it (e.g. a `bad_undeclared.md` case for the `SV-ID-UNDECLARED` branch).

- [ ] **Step 3: Re-run the gate to confirm green**

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

Expected: all pass, coverage ≥ 85%, dogfood (`uv run validate-frontmatter --config .project-standards.yml`) still clean (the new `.md` fixtures live under `tests/` and `standards/**/templates/**`, both already excluded from the frontmatter validator).

- [ ] **Step 4: Final commit**

```bash
git add -A src/project_standards/specs tests
git commit -m "chore(spec): full-gate green for spec tooling (spec #1)"
```

---

## Self-Review

**Spec coverage:** validate (Task 5) ✓ · lint (Task 6) ✓ · extract (Task 7) ✓ · next (Task 8) ✓ · registry core single source (Tasks 2–3) ✓ · `spec:` discovery + non-vacuous exit-2 (Task 4) ✓ · `--json` frozen shape (Task 9) ✓ · sentinel + real-`spec_id` rejection (Task 5, `_check_frontmatter`) ✓ · Light traceability exemption (Task 6, `_traceability`) ✓ · tier-invalid prefix (Task 5, `SV-ID-TIER`) ✓ · Defined-In identity (Task 10 interchangeability test) ✓ · check_specs.py retirement + doc reconciliation incl. tooling-notes §8 demotion & README §5 (Task 10) ✓ · CI workflow (Task 11) ✓ · wheel packaging (Task 1) ✓ · never-traceback error boundary (Task 9 `_read`/`run`) ✓.

**Type consistency:** `Finding(code, severity, message, line, locus)` used identically in validate/lint/cli. `SpecDocument` fields (`used_ids: dict[str, list[tuple[str,int]]]`, `declared_prefixes`, `sections`) consumed consistently. `Registry` field names (`tier_prefixes`, `prefix_defined_in`, `canonical_sections`, `full_only_appendices`) match across registry/validate/next.

**Open items deferred to execution (documented, not placeholders):** exact `FR`-Defined-In string (Task 2 Step 4 tells the implementer to read + match it); `extract` duplicate/partial-heading disambiguation (spec Open Question — first-match is the coded default; tighten only if a fixture demands); the parsed `on:` YAML key idiom (Task 11 points at the repo's existing workflow tests).
