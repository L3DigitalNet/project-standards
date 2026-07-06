# Spec-Validator External References & Token Hygiene — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the project-spec ID validator to distinguish a spec's own mintable IDs from tokens it merely references (external namespaces, ADR ids, SPDX license identifiers), fixing issue #3 (F1–F4) without breaking any currently-passing spec.

**Architecture:** Introduce a third token category — "referenced, not owned" — as a **skip set** applied at the single scan point in `parse_document`. The skip set is assembled from built-in prefixes (`NOT_AN_ID`, a new `BUILTIN_REFERENCE_PREFIXES` holding `ADR`), a shape rule (version/SPDX tokens whose digits are followed by `.`+digit), and a new opt-in config key `spec.reference_prefixes`. Only pass/fail gates (`validate`/`lint`, and `upgrade` via a new opt-in `--config`) consume the config-derived prefixes.

**Tech Stack:** Python ≥3.14, `uv` for env/commands, Ruff (format+lint), BasedPyright (strict), pytest + coverage (branch, `fail_under=85`), pip-audit. Docs linted with Prettier + markdownlint-cli2.

## Global Constraints

- **Python floor:** `requires-python = ">=3.14"` — unchanged; do not lower.
- **Loosening only:** no change may turn a currently-passing spec into a failure. The dogfooded `standards/project-spec/examples/spec.example.md` must validate unchanged.
- **Opt-in, never default-load for new surfaces:** `upgrade`'s new `--config` defaults to `None` (do not load). `extract` and `next` gain **no** flag and never read config.
- **Config errors → exit 2** (`ConfigError`); validation findings keep their existing `SV-*` codes. The `--json` machine contract is the finding `code`, not its `message`.
- **Verification gate (must be green before done):** `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`, plus `uv run validate-frontmatter --config .project-standards.yml` and `uv run project-standards spec validate --config .project-standards.yml`. Branch coverage stays ≥ `fail_under = 85`.
- **Never** add frontmatter to `CLAUDE.md`, `AGENTS.md`, `.claude/**`.
- **Docs must be Prettier + markdownlint clean** (`.md` under tracked paths); run `npx --no-install prettier --write <f>` then `npx --no-install markdownlint-cli2 <f>`.
- **Commit style:** conventional commits; commits are signed automatically (GPG configured). Work stays on the `testing` branch; do **not** tag or cut the release (that is a separate user-gated step).
- **Run all Python via `uv run`** — a bare `python` invocation is refused by the repo wrapper.

---

### Task 1: Zero-config skip set in `parse_document`

Adds the built-in reference prefix (`ADR`), the broadened license denylist, and the dot-version shape rule, plus the (still-empty-by-default) `reference_prefixes` parameter. This is the core scan change; every later task builds on it.

**Files:**

- Modify: `src/project_standards/specs/registry.py` (the `NOT_AN_ID` set; add `BUILTIN_REFERENCE_PREFIXES`)
- Modify: `src/project_standards/specs/document.py` (`parse_document` signature + scan loop, import)
- Test: `tests/test_spec_document.py`

**Interfaces:**

- Consumes: nothing from other tasks.
- Produces:
  - `registry.BUILTIN_REFERENCE_PREFIXES: frozenset[str]` (contains `"ADR"`).
  - `document.parse_document(path: str, text: str, reference_prefixes: frozenset[str] = frozenset()) -> SpecDocument` — tokens whose prefix is in `NOT_AN_ID`, `BUILTIN_REFERENCE_PREFIXES`, or `reference_prefixes`, or whose digits are immediately followed by `.`+digit, are **not** recorded in `used_ids`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_spec_document.py`:

```python
from project_standards.specs.document import parse_document


def _body(text: str) -> str:
    # parse_document needs frontmatter to split; a minimal fence is enough here.
    return "---\nspec_id: SPEC-0001\n---\n" + text


def test_skip_set_zero_config():
    doc = parse_document(
        "t.md",
        _body(
            "Refs adr-0001-x and ADR-0001. Licenses MPL-2.0, LGPL-2.1, CC-BY-4.0, GPL-3. "
            "Own id FR-007 and a sentence end FR-008. Version-shaped FR-1.2 here."
        ),
    )
    prefixes = set(doc.used_ids)
    # ADR (built-in ref) and the license families are never recorded:
    assert "ADR" not in prefixes
    assert prefixes.isdisjoint({"MPL", "LGPL", "BY", "GPL"})
    # Real spec-local ids survive, including one at a sentence boundary:
    assert [fid for fid, _ in doc.used_ids["FR"]] == ["FR-007", "FR-008"]
    # The version-shaped token FR-1.2 is skipped (dot+digit), so FR-1 is absent:
    assert "FR-1" not in [fid for fid, _ in doc.used_ids["FR"]]


def test_reference_prefixes_param_skips_configured():
    doc = parse_document("t.md", _body("Backlog RQ-123 and GAP-56."), frozenset({"RQ", "GAP"}))
    assert "RQ" not in doc.used_ids
    assert "GAP" not in doc.used_ids
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_spec_document.py::test_skip_set_zero_config tests/test_spec_document.py::test_reference_prefixes_param_skips_configured -v` Expected: FAIL — `test_skip_set_zero_config` records `ADR`/`MPL`/etc.; the param test errors with `parse_document() takes 2 positional arguments but 3 were given`.

- [ ] **Step 3: Broaden `NOT_AN_ID` and add the built-in reference set (`registry.py`)**

In `src/project_standards/specs/registry.py`, extend the `NOT_AN_ID` set with the common SPDX license family prefixes and add the new constant immediately after it:

```python
NOT_AN_ID = {
    "HTTP",
    "AES",
    "SHA",
    "UTF",
    "ISO",
    "IEEE",
    "IEC",
    "WCAG",
    "RPO",
    "RTO",
    "PII",
    "API",
    "URL",
    "SPEC",
    "TLS",
    "CSRF",
    "CORS",
    "SSO",
    "WAL",
    "PITR",
    # SPDX license family prefixes that share the ID_TOKEN shape. MIT/NTP are
    # deliberately omitted — a zero-version license like MIT-0 is indistinguishable
    # from a spec-local id by shape, so a consumer lists it in spec.reference_prefixes.
    "GPL",
    "LGPL",
    "AGPL",
    "MPL",
    "BSD",
    "EPL",
    "BY",  # from CC-BY-4.0, which ID_TOKEN tokenizes as BY-4
}

# Prefixes that are real IDs in ANOTHER namespace (not spec-local), always exempt
# from the ID checks. Kept separate from NOT_AN_ID (which means "not an ID at all")
# so the two intents stay legible. ADR ids are minted by the sibling ADR standard.
BUILTIN_REFERENCE_PREFIXES = frozenset({"ADR"})
```

- [ ] **Step 4: Add the parameter and skip predicate (`document.py`)**

In `src/project_standards/specs/document.py`, add `BUILTIN_REFERENCE_PREFIXES` to the registry import block:

```python
from project_standards.specs.registry import (
    BUILTIN_REFERENCE_PREFIXES,
    ID_TOKEN,
    NOT_AN_ID,
    declared_prefixes,
    gh_slug,
    headings,
    numkey,
    section_numbers,
```

Change the `parse_document` signature and the scan loop:

```python
def parse_document(
    path: str, text: str, reference_prefixes: frozenset[str] = frozenset()
) -> SpecDocument:
    """Parse a consumer spec into a SpecDocument.

    reference_prefixes are external namespaces the spec cites but does not own; like
    NOT_AN_ID and the built-in reference prefixes they are skipped in the ID scan.
    """
```

Replace the existing token loop body:

```python
    for m in ID_TOKEN.finditer(body):
        pfx = m.group(1)
        if pfx in NOT_AN_ID or pfx in BUILTIN_REFERENCE_PREFIXES or pfx in reference_prefixes:
            continue
        # Version/SPDX shape: digits immediately followed by ".<digit>" (MPL-2.0, FR-1.2).
        # A real id at a sentence end (FR-007.) is "."+space, never "."+digit, so it survives.
        tail = body[m.end() : m.end() + 2]
        if len(tail) == 2 and tail[0] == "." and tail[1].isdigit():
            continue
        line = bisect.bisect_left(nl_offsets, m.start()) + 1
        used.setdefault(pfx, []).append((f"{pfx}-{m.group(2)}", line))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_spec_document.py -v` Expected: PASS (both new tests and every existing document test).

- [ ] **Step 6: Run the full spec suite for regressions**

Run: `uv run pytest tests/ -k spec -q` Expected: PASS. If a pre-existing fixture used a `NOT_AN_ID`-shaped token as a real id, investigate — but none of the added prefixes (`GPL`/`MPL`/…/`ADR`) are canonical spec prefixes, so no regression is expected.

- [ ] **Step 7: Commit**

```bash
git add src/project_standards/specs/registry.py src/project_standards/specs/document.py tests/test_spec_document.py
git commit -m "feat(spec): skip external/reference and license-shaped tokens in ID scan"
```

---

### Task 2: `spec.reference_prefixes` config key + validation

Adds the config surface and its validation (shape + canonical-prefix collision), then confirms it flows into `parse_document`.

**Files:**

- Modify: `src/project_standards/specs/config.py` (`SpecConfig`, `load_spec_config`, new validation helper)
- Test: `tests/test_spec_config.py`

**Interfaces:**

- Consumes: `parse_document(..., reference_prefixes)` from Task 1; `registry.load_registry().prefix_defined_in` for the canonical set.
- Produces: `SpecConfig.reference_prefixes: list[str]` (default `[]`, validated); `load_spec_config(path)` raises `ConfigError` on a malformed or canonical-colliding entry.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_spec_config.py`:

```python
import pytest

from project_standards.specs.config import load_spec_config
from project_standards.validate_frontmatter import ConfigError


def _write(tmp_path, body):
    p = tmp_path / ".project-standards.yml"
    p.write_text(body, encoding="utf-8")
    return p


def test_reference_prefixes_parsed(tmp_path):
    cfg = load_spec_config(
        _write(tmp_path, "spec:\n  include: ['x/**']\n  reference_prefixes: ['RQ', 'GAP']\n")
    )
    assert cfg.reference_prefixes == ["RQ", "GAP"]


def test_reference_prefixes_default_empty(tmp_path):
    cfg = load_spec_config(_write(tmp_path, "spec:\n  include: ['x/**']\n"))
    assert cfg.reference_prefixes == []


def test_reference_prefixes_bad_shape_rejected(tmp_path):
    with pytest.raises(ConfigError, match="1-4 uppercase"):
        load_spec_config(_write(tmp_path, "spec:\n  reference_prefixes: ['rq']\n"))


def test_reference_prefixes_canonical_collision_rejected(tmp_path):
    with pytest.raises(ConfigError, match="canonical spec-local prefix"):
        load_spec_config(_write(tmp_path, "spec:\n  reference_prefixes: ['FR']\n"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_spec_config.py -k reference_prefixes -v` Expected: FAIL — `SpecConfig` has no `reference_prefixes` attribute.

- [ ] **Step 3: Add the field, import, and validation helper (`config.py`)**

In `src/project_standards/specs/config.py`, update the imports at the top:

```python
import re
from dataclasses import dataclass, field
```

and add the registry import beside the existing document import:

```python
from project_standards.specs.registry import load_registry
```

Add the field to `SpecConfig`:

```python
@dataclass(frozen=True)
class SpecConfig:
    include: list[str]
    exclude: list[str]
    present: bool
    reference_prefixes: list[str] = field(default_factory=list)
```

Add the validation helper above `load_spec_config`:

```python
_PREFIX_RE = re.compile(r"^[A-Z]{1,4}$")


def _validate_reference_prefixes(prefixes: list[str]) -> list[str]:
    """Reject malformed prefixes and ones that shadow a canonical spec-local prefix.

    A canonical collision (e.g. listing 'FR') would silently disable validation of the
    consumer's own requirement IDs, so it is a hard error, not a warning.
    """
    canonical = set(load_registry().prefix_defined_in)
    for pfx in prefixes:
        if not _PREFIX_RE.match(pfx):
            raise ConfigError(
                f"spec.reference_prefixes entry {pfx!r} must be 1-4 uppercase letters"
            )
        if pfx in canonical:
            raise ConfigError(
                f"spec.reference_prefixes entry {pfx!r} is a canonical spec-local prefix; "
                "listing it would disable validation of your own IDs"
            )
    return prefixes
```

- [ ] **Step 4: Parse the key in `load_spec_config`**

In `load_spec_config`, inside the `if isinstance(block, dict):` branch, add the parse+validate line and thread it into the return. The branch becomes:

```python
            if isinstance(block, dict):
                present = True
                b = cast("dict[str, Any]", block)
                include = _str_list(b.get("include"))
                exclude = _str_list(b.get("exclude"))
                reference_prefixes = _validate_reference_prefixes(
                    _str_list(b.get("reference_prefixes"))
                )
```

Initialize the local beside `include`/`exclude` at the top of the function (`reference_prefixes: list[str] = []`) and pass it in the return:

```python
    return SpecConfig(
        include=include, exclude=exclude, present=present, reference_prefixes=reference_prefixes
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_spec_config.py -v` Expected: PASS (new and existing config tests).

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/specs/config.py tests/test_spec_config.py
git commit -m "feat(spec): add validated spec.reference_prefixes config key"
```

---

### Task 3: Reword the `SV-ID-UNDECLARED` message

Replaces the dead-end message ("used but not in Appendix A" → declare → `SV-ID-TIER`) with one that names the real resolution. Code stays `SV-ID-UNDECLARED` (the machine contract).

**Files:**

- Modify: `src/project_standards/specs/commands/validate.py:149-152`
- Test: `tests/test_spec_validate.py`

**Interfaces:**

- Consumes: nothing new.
- Produces: `SV-ID-UNDECLARED` findings whose `message` mentions `spec.reference_prefixes`; the `code` is unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_spec_validate.py`:

```python
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry


def test_undeclared_message_names_reference_prefixes():
    doc = parse_document(
        "t.md", "---\nspec_id: SPEC-0001\n---\nBody cites RQ-123 as an id.\n"
    )
    findings = validate_document(doc, load_registry())
    undeclared = [f for f in findings if f.code == "SV-ID-UNDECLARED" and f.locus == "RQ-"]
    assert undeclared, "expected an SV-ID-UNDECLARED for RQ-"
    assert "spec.reference_prefixes" in undeclared[0].message
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_spec_validate.py::test_undeclared_message_names_reference_prefixes -v` Expected: FAIL — the current message is "prefix RQ- used but not in Appendix A".

- [ ] **Step 3: Reword the message (`validate.py`)**

In `src/project_standards/specs/commands/validate.py`, replace the `SV-ID-UNDECLARED` emission:

```python
        if pfx not in doc.declared_prefixes:
            out.append(
                _f(
                    "SV-ID-UNDECLARED",
                    f"prefix {pfx}- is not a canonical spec-local prefix. If it names an "
                    "external namespace (backlog, tickets, another spec), add it to "
                    "spec.reference_prefixes; otherwise declare it in Appendix A with a "
                    "canonical prefix.",
                    locus=f"{pfx}-",
                )
            )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_spec_validate.py -v` Expected: PASS. If an existing test asserted the old message text verbatim, update that assertion to match the new wording (the `code` assertions stay unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/commands/validate.py tests/test_spec_validate.py
git commit -m "feat(spec): SV-ID-UNDECLARED points to spec.reference_prefixes"
```

---

### Task 4: Thread reference prefixes into `validate`/`lint` and `new`

Wires the config-derived prefixes into the two already-config-aware pass/fail gates and the `new` self-check.

**Files:**

- Modify: `src/project_standards/specs/cli.py:87` (`_run_setwide`), `:370` (`_run_new` self-check)
- Test: `tests/test_spec_cli.py`

**Interfaces:**

- Consumes: `SpecConfig.reference_prefixes` (Task 2), `parse_document(..., reference_prefixes)` (Task 1).
- Produces: `validate`/`lint` honor `spec.reference_prefixes` from the resolved config.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_spec_cli.py` (adapt the import of the command entrypoint to the file's existing helper — this uses `run` from `project_standards.specs.cli`):

```python
from project_standards.specs.cli import run


def test_validate_honors_reference_prefixes(tmp_path):
    spec = tmp_path / "s.md"
    spec.write_text(
        "---\nspec_id: SPEC-0001\n---\n# 1. Overview\nCites RQ-123.\n", encoding="utf-8"
    )
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "spec:\n  include: ['s.md']\n  reference_prefixes: ['RQ']\n", encoding="utf-8"
    )
    rc = run(["validate", str(spec), "--config", str(cfg)])
    assert rc == 0  # RQ-123 is a declared external reference, not a bad id
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_spec_cli.py::test_validate_honors_reference_prefixes -v` Expected: FAIL with rc == 1 (RQ-123 currently trips `SV-ID-UNDECLARED`).

- [ ] **Step 3: Thread the prefixes in `_run_setwide` (`cli.py:87`)**

Change the scan call inside the `for path in paths:` loop:

```python
            results.append(
                (
                    path,
                    fn(
                        parse_document(
                            str(path), _read(path), frozenset(cfg.reference_prefixes)
                        ),
                        reg,
                    ),
                )
            )
```

- [ ] **Step 4: Thread the prefixes in `_run_new` self-check (`cli.py:370`)**

The generated scaffold is validated against config-aware rules for consistency. `_run_new` already loads `--config` (default `.project-standards.yml`), so this adds no new default-load surface:

```python
            doc = parse_document(
                "<new>", text, frozenset(load_spec_config(args.config).reference_prefixes)
            )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_spec_cli.py -v` Expected: PASS (new test plus existing CLI tests).

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/specs/cli.py tests/test_spec_cli.py
git commit -m "feat(spec): validate/lint/new honor spec.reference_prefixes"
```

---

### Task 5: Opt-in `--config` on `upgrade` (SA-001 + compatibility)

`upgrade` re-validates the source and its own output, so a spec that validates with `reference_prefixes` must upgrade with them too — via an **opt-in** flag that defaults to not loading config (preserving v4.0.0 default behavior).

**Files:**

- Modify: `src/project_standards/specs/cli.py:472-548` (`_run_upgrade`)
- Test: `tests/test_spec_upgrade_cli.py`

**Interfaces:**

- Consumes: `load_spec_config` (Task 2), `parse_document(..., reference_prefixes)` (Task 1).
- Produces: `upgrade` accepts an optional `--config PATH`; when passed, its source and output validation honor `reference_prefixes`. With no `--config`, behavior is byte-identical to v4.0.0.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_spec_upgrade_cli.py` (reuse the file's existing `_run` helper and `_FIX` fixtures directory; the upgrade fixtures live under `tests/fixtures/specs/`):

```python
def test_upgrade_honors_reference_prefixes(tmp_path):
    # A standard-tier spec that cites an external RQ-123; without config it fails
    # source validation, with config it upgrades cleanly.
    src = tmp_path / "s.md"
    base = (_FIX / "upgrade_standard.md").read_text(encoding="utf-8")
    src.write_text(base.replace("## 1.", "Cites RQ-123.\n\n## 1.", 1), encoding="utf-8")
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("spec:\n  reference_prefixes: ['RQ']\n", encoding="utf-8")
    rc = _run([str(src), "--to", "full", "--stdout", "--config", str(cfg)])
    assert rc == 0


def test_upgrade_without_config_ignores_malformed_config(tmp_path, monkeypatch):
    # Guards SA-NEW-001: no --config means config is never read, even a broken one present.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".project-standards.yml").write_text("spec: [not, a, mapping\n", encoding="utf-8")
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(encoding="utf-8"), encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--stdout"])
    assert rc == 0  # unchanged v4.0.0 behavior; the malformed config is never loaded
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_spec_upgrade_cli.py -k "reference_prefixes or malformed_config" -v` Expected: FAIL — `upgrade` has no `--config` flag, so argparse rejects it (rc 2) in the first test.

- [ ] **Step 3: Add the flag and resolve prefixes (`cli.py`)**

In `_run_upgrade`, add the flag beside the other `ap.add_argument(...)` lines:

```python
    ap.add_argument("--config", type=Path, default=None)
```

After `reg = load_registry()` (currently line 505), resolve the prefixes, converting a config error into the command's JSON-safe failure path:

```python
        try:
            refs = (
                frozenset(load_spec_config(args.config).reference_prefixes)
                if args.config is not None
                else frozenset()
            )
        except ConfigError as exc:
            raise NewError("config_error", str(exc)) from exc
```

- [ ] **Step 4: Pass `refs` to both `parse_document` calls**

Source parse (currently line 507):

```python
            src_doc = parse_document(str(args.src), source_text, refs)
```

Output self-validation parse (currently line 539):

```python
            out_doc = parse_document("<upgrade>", upgraded, refs)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_spec_upgrade_cli.py -v` Expected: PASS (new tests and all existing upgrade tests, which pass no `--config` and are unaffected).

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/specs/cli.py tests/test_spec_upgrade_cli.py
git commit -m "feat(spec): opt-in --config on upgrade honors reference_prefixes"
```

---

### Task 6: Seed the ADR example in the §8.3 template row (four files)

The `ADR` column in §8.3 currently shows `<link if durable>`, which primes consumers to write the non-conforming uppercase `ADR-0001`. Seed it with the ADR standard's real lowercase form. The row lives in both the **standard** and **full** templates, each a byte-identical `src`/`standards` pair.

**Files:**

- Modify: `src/project_standards/specs/templates/spec-full-template.md`
- Modify: `src/project_standards/specs/templates/spec-standard-template.md`
- Modify: `standards/project-spec/templates/spec-full-template.md`
- Modify: `standards/project-spec/templates/spec-standard-template.md`
- Test: `tests/test_spec_packaging.py` (existing byte-identity guard)

**Interfaces:**

- Consumes: nothing.
- Produces: template §8.3 example row shows `` `adr-0001-repo-short-title` `` in the ADR column.

- [ ] **Step 1: Confirm the current row and the parity guard**

Run: `grep -n "link if durable" src/project_standards/specs/templates/spec-standard-template.md standards/project-spec/templates/spec-standard-template.md src/project_standards/specs/templates/spec-full-template.md standards/project-spec/templates/spec-full-template.md` Expected: one matching row per file — the `D-001` example row ending in the durable-link placeholder cell.

- [ ] **Step 2: Edit all four files identically**

In each of the four files, replace the final cell of the `D-001` example row. Change:

```text
| D-001 | `<decision>` | `<why>` | `<alternatives and why rejected>` | `<link if durable>` |
```

to:

```text
| D-001 | `<decision>` | `<why>` | `<alternatives and why rejected>` | `adr-0001-repo-short-title` |
```

(The lowercase `adr-NNNN-…` form is the ADR standard's canonical id; the uppercase-only `ID_TOKEN` never records it, so it validates with no config.)

- [ ] **Step 3: Verify byte-identity and that templates still validate**

Run: `uv run pytest tests/test_spec_packaging.py -v` Expected: PASS — `test_bundled_template_is_byte_identical` confirms each `src` copy matches its `standards` copy. If it fails, the two copies of a tier diverged; re-copy so each pair is identical.

- [ ] **Step 4: Run the new/upgrade suites for golden drift**

Run: `uv run pytest tests/ -k "new or upgrade" -q` Expected: PASS. `test_spec_upgrade_fixtures.py` only parses+validates fixtures (the lowercase example still validates). If a `new`/`upgrade` test asserts generated output containing the old `<link if durable>` text, update that expected substring to `adr-0001-repo-short-title`.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/specs/templates/spec-full-template.md src/project_standards/specs/templates/spec-standard-template.md standards/project-spec/templates/spec-full-template.md standards/project-spec/templates/spec-standard-template.md
git commit -m "docs(spec): model the ADR column with a real adr-0001 example"
```

---

### Task 7: Document the namespace split + config example (README)

Make the uppercase-mintable vs. lowercase/listed-reference split discoverable, with a copy-pasteable config snippet — so none of this requires reading validator source.

**Files:**

- Modify: `standards/project-spec/README.md`
- Test: manual gate (frontmatter validator + Prettier + markdownlint)

**Interfaces:**

- Consumes: nothing.
- Produces: README section documenting `spec.reference_prefixes`, the built-in `ADR`, and the scoped license handling.

- [ ] **Step 1: Add the documentation**

In `standards/project-spec/README.md`, in the section covering IDs / Appendix A (find it with `grep -n "Appendix A\|reference\|prefix" standards/project-spec/README.md`), add prose describing the namespace split and the config key. Include this snippet:

````markdown
#### External references vs. spec-local IDs

Uppercase `PFX-NNN` tokens are **spec-local IDs** you mint — they must be declared in Appendix A and are width- and tier-checked. Tokens you only **reference** are exempt:

- Lowercase ids such as an ADR's `adr-0001-…` are ignored automatically.
- The `ADR` prefix is a built-in reference, so `ADR-0001` is accepted too.
- Common versioned license identifiers (`MPL-2.0`, `LGPL-2.1`, `CC-BY-4.0`, `GPL-3`) are ignored. A zero-version SPDX id like `MIT-0` shares an ID's shape — list its family in `reference_prefixes`.
- Any other external namespace (a backlog `RQ-123`, a gap log `GAP-56`, tickets) goes in `spec.reference_prefixes`:

```yaml
spec:
  include:
    - 'docs/specs/**/*.md'
  reference_prefixes: ['RQ', 'GAP', 'MIT'] # cited, not minted here
```

Reference prefixes are exempt from the Appendix-A, width, and tier checks. A prefix that collides with a canonical spec-local prefix (e.g. `FR`) is rejected — that would disable validation of your own IDs. Only `validate`, `lint`, and `upgrade --config` read this key; `extract` and `next` never load config.
````

- [ ] **Step 2: Format and lint the doc**

Run:

```bash
npx --no-install prettier --write standards/project-spec/README.md
npx --no-install markdownlint-cli2 standards/project-spec/README.md
```

Expected: Prettier reports clean; markdownlint `Summary: 0 error(s)`. Fix any reported issue.

- [ ] **Step 3: Verify frontmatter still validates**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: exit 0 — the README's existing frontmatter is untouched and still conforms.

- [ ] **Step 4: Commit**

```bash
git add standards/project-spec/README.md
git commit -m "docs(spec): document reference_prefixes and the ID namespace split"
```

---

### Task 8: Release prep — CHANGELOG + version bump (v4.1.0)

Records the change as a minor release. **Does not tag or publish** — cutting the release (git tag, moving `v4`, GitHub release) is a separate user-gated step per the repo's release discipline.

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml:3` (`version`)
- Modify: `uv.lock` (regenerated)
- Test: full gate

**Interfaces:**

- Consumes: nothing.
- Produces: a `[4.1.0]` changelog entry and `version = "4.1.0"`.

- [ ] **Step 1: Add the CHANGELOG entry**

In `CHANGELOG.md`, add a new section above the most recent release (keep the frontmatter and heading structure; bump `updated:` to `2026-07-06`):

```markdown
## [4.1.0] - 2026-07-06

### Added

- **Project Specification:** `spec.reference_prefixes` config key — declare external ID namespaces (backlog, tickets, ADRs) the spec cites but does not mint, exempting them from the Appendix-A, width, and tier checks. Validated for shape and rejected on collision with a canonical spec-local prefix.
- **Project Specification:** opt-in `--config` on `spec upgrade` so it honors `reference_prefixes` during source and output validation. Defaults to not loading config, so existing `upgrade` invocations are unchanged.

### Changed

- **Project Specification:** the ID scan now skips the sibling ADR standard's ids (built-in `ADR` reference prefix; lowercase `adr-…` was already ignored) and common versioned SPDX license identifiers (`MPL-2.0`, `LGPL-2.1`, `CC-BY-4.0`, `GPL-3`, …). Zero-version SPDX ids (`MIT-0`) use `reference_prefixes`.
- **Project Specification:** `SV-ID-UNDECLARED` now names `spec.reference_prefixes` as the resolution instead of dead-ending at Appendix A.
- **Project Specification:** the §8.3 template `ADR` column models a real `adr-0001-…` example.

All changes are a backward-compatible loosening (a previously-passing spec cannot newly fail); `@v4` consumers inherit them automatically.
```

- [ ] **Step 2: Bump the version**

In `pyproject.toml`, change line 3:

```toml
version = "4.1.0"
```

- [ ] **Step 3: Regenerate the lockfile**

Run: `uv lock` Expected: `uv.lock` updates the project version to 4.1.0 with no dependency changes.

- [ ] **Step 4: Run the full verification gate**

Run:

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit \
  && uv run validate-frontmatter --config .project-standards.yml \
  && uv run project-standards spec validate --config .project-standards.yml
```

Expected: all green; branch coverage ≥ 85; dogfood spec validates.

- [ ] **Step 5: Format/lint the changed docs**

Run:

```bash
npx --no-install prettier --check CHANGELOG.md
npx --no-install markdownlint-cli2 CHANGELOG.md
```

Expected: clean. Run `prettier --write` first if needed.

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md pyproject.toml uv.lock
git commit -m "release: prepare v4.1.0 (spec reference prefixes + token hygiene)"
```

---

## Self-Review

**Spec coverage:**

- F1 → Task 1 (built-in `ADR`) + Task 6 (template example) + Task 7 (docs). ✅
- F2 → Task 2 (config key) + Task 4 (validate/lint wiring) + Task 5 (upgrade). ✅
- F3 → Task 1 (referenced tokens of any width are skipped; canonical width unchanged). ✅
- F4 → Task 1 (dot-rule + broadened `NOT_AN_ID`); `MIT-0`/`NTP-0` via Task 2's `reference_prefixes`. ✅
- Error message (F2 dead-end) → Task 3. ✅
- SA-NEW-001 (opt-in, no default-load) → Task 5 (`--config` defaults to `None`; compat test). ✅
- SA-NEW-002 (`extract`/`next` excluded) → not wired (documented in spec Component 3); no task needed. ✅
- SA-NEW-003 (`next` inherits global skips intentionally) → covered by Task 1's `FR-1.2` assertion. ✅
- Versioning (minor) → Task 8. ✅

**Placeholder scan:** No TBD/TODO; every code step shows literal code and exact `uv run`/`git` commands. ✅

**Type consistency:** `parse_document(path, text, reference_prefixes: frozenset[str] = frozenset())` is defined in Task 1 and called with a `frozenset(...)` in Tasks 4 and 5. `SpecConfig.reference_prefixes: list[str]` (Task 2) is converted to `frozenset` at every call site. `BUILTIN_REFERENCE_PREFIXES` is a `frozenset[str]`. Consistent. ✅
