# CLI Documentation Standard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the CLI documentation research draft as the repo's sixth fully adoptable standard (`cli-documentation`), with a normative bundle, adopt-engine registration, `--version` on every installed command, a dogfooded `docs/usage.md`, and tests — ready for a v4.3.0 release.

**Architecture:** Content-first, then code (spec decision 8). The research monolith at `standards/cli-framework/cli-documentation-standards.md` is exploded into a five-part bundle under `standards/cli-documentation/`; registration (registry + bundle manifest + config block) lands atomically in one task because `_assert_registry_bundle_parity` (exit 2) forbids intermediate states. Spec: `docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md` (approved, codex-converged round 3).

**Tech Stack:** Python 3.14 / uv / argparse; pytest + coverage; Prettier + markdownlint-cli2; TOML adopt manifests; `importlib.metadata` for versions.

## Global Constraints

- Standard id is exactly `cli-documentation`; config/registry key `cli_documentation`; contract version `"1.0"` (spec decisions 2, 9).
- Every commit must leave the gate green: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run pytest tests/coherence` plus `npx prettier --check .` and `npx markdownlint-cli2` clean (repo non-negotiable; run the relevant subset per task, the full gate in the final task).
- Never add frontmatter to `CLAUDE.md`, `AGENTS.md`, or `.claude/**` (repo non-negotiable).
- All new Markdown must pass Prettier + markdownlint. **Escape pipes inside code spans in tables** (`\|`) — unescaped pipes split GFM cells (bit this project twice already).
- No Unicode private-use-area characters (U+E000–U+F8FF) in any authored file — research-export artifact check (spec acceptance).
- `project-standards` CLI surface: 10 leaf commands (`validate`, `fix`, `adopt`, `list` + `spec` group's `validate`/`lint`/`extract`/`next`/`new`/`upgrade`) plus the `spec` group overview; seven `[project.scripts]` console scripts, all public.
- Working branch `testing`; commit after every task; do **not** merge to `main` (release is a separate user decision).
- New docs carry canonical frontmatter (`schema_version: '1.1'`) except `templates/**` (excluded placeholders).

---

### Task 1: Rename the bundle directory

**Files:**

- Rename: `standards/cli-framework/` → `standards/cli-documentation/` (contains only `cli-documentation-standards.md`)
- Modify: `.project-standards.yml` (interim exclude path)

**Interfaces:**

- Produces: `standards/cli-documentation/` as the bundle root every later task writes into. The draft file `standards/cli-documentation/cli-documentation-standards.md` is the content source for Tasks 2–5 and is deleted in Task 5.

- [ ] **Step 1: Rename via git so history follows**

```bash
git mv standards/cli-framework standards/cli-documentation
```

- [ ] **Step 2: Update the interim exclude in `.project-standards.yml`**

Replace the exclude line and its comment (currently references `cli-framework` and "TODO Phase 0/3"):

```yaml
# cli-documentation is mid-integration (spec 2026-07-07). INTERIM: remove once the
# governing doc gains canonical frontmatter (plan Task 6) so the bundle validates
# like every other adoptable bundle. Until then it has no frontmatter, so exclude it.
- 'standards/cli-documentation/**'
```

- [ ] **Step 3: Verify the gate subset**

Run: `uv run validate-frontmatter --config .project-standards.yml && npx prettier --check . && npx markdownlint-cli2` Expected: `✓ 19 file(s) validated`, Prettier clean, markdownlint `0 error(s)`.

- [ ] **Step 4: Commit**

```bash
git add -A standards/ .project-standards.yml
git commit -m "refactor(cli-docs): rename bundle dir to standards/cli-documentation (decided id)"
```

---

### Task 2: Author the normative `README.md`

**Files:**

- Create: `standards/cli-documentation/README.md`
- Read (content source): `standards/cli-documentation/cli-documentation-standards.md`, `docs/research/2026-07-07-cli-usage-docs-packaged-src-layout-python.md`
- Read (house-style models): `standards/project-spec/README.md`, `standards/python-tooling/README.md`

**Interfaces:**

- Produces: the governing standard document. Section numbering below is referenced verbatim by `adopt.md` (Task 4), templates (Task 3), and `docs/usage.md` (Task 8).

- [ ] **Step 1: Write the document skeleton with frontmatter**

Frontmatter (exact; key order matters to the validator):

```yaml
---
schema_version: '1.1'
id: 'reference-k7w3qd-cli-documentation-standard'
title: 'CLI Documentation Standard'
description: 'Tiered, profile-based standard for user-facing CLI usage documentation: help text, usage references, man pages, and CI drift prevention.'
doc_type: 'reference'
status: 'active'
created: '2026-07-07'
updated: '2026-07-07'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'cli'
  - 'documentation'
  - 'standard'
aliases:
  - 'cli-docs-standard'
related:
  - 'standards/cli-documentation/adopt.md'
  - 'standards/cli-documentation/resources/research-notes.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---
```

Then the header block (mirror `project-spec/README.md` lines 29–37): H1 `CLI Documentation Standard`, status line ("Active — registered for adoption; contract version 1.0"), owner, last updated, last source check `2026-07-07`, scope sentence. Then a Table of Contents, then these numbered sections:

1. Evidence convention (`[S##]` register, policy-vs-fact split — copy the convention wording pattern from `python-coding/README.md` "Evidence convention")
2. Requirement language (RFC 2119 — copy the wording pattern from `python-coding/README.md` "Requirement language")
3. Version assumptions (Python 3.14 argparse colors by default; Click rewraps by width; tool pins are template defaults to recheck)
4. Purpose
5. Scope & sibling relations (Markdown Tooling formats the docs; Python Tooling owns the toolchain; Project Spec owns pre-implementation definition; Markdown Frontmatter governs managed-doc metadata)
6. Profiles — the three-profile ladder **exactly as spec §1**, including: the profile table (Script / Packaged / Packaged-deep), the recorded-adopter-judgment rule, the selection signals, the every-leaf-command MUST, the grouped-page provision, and the public-unless-classified-internal rule for `[project.scripts]` keys
7. Usage-doc structure & notation — man-style section registry table + GitHub-CLI synopsis notation table (port from draft lines ~78–126; keep the `\|` escapes)
8. Help-text boundary (port the draft's boundary table; help generated from the parser, never hand-written)
9. Option entries (the required-fields table from the draft; the worked `--format` example)
10. Examples (task-first, copy-paste-safe, safety-biased rules from the draft)
11. Packaged CLIs — entry-point name is the command contract; `prog` discipline (`__main__.py` and entry point share `main()`); man page SHOULD-if-practical with the wheels/`MANPATH` rationale; generated per-command docs for the deep profile; multi-entry-point layout (one page per installed command, grouped-page provision) — sourced from `docs/research/2026-07-07-cli-usage-docs-packaged-src-layout-python.md` §§1–3, 5
12. CI drift prevention — mandated checks (installed-wrapper smoke from a built artifact; inventory parity; option/exit-code parity pass) + snapshot rules (normalize `NO_COLOR` + width; never assert argparse section headings)
13. Accessibility & localization (no color-only meaning; `NO_COLOR`; prose translates, command surface never)
14. Templates (table pointing at `templates/usage-doc.md`, `templates/readme-single-file.md`, `templates/cli-docs-check.yml`)
15. Adoption (pointer to `adopt.md`)
16. Exceptions process (one paragraph: exceptions are recorded in the adopter's usage doc or repo docs, mirroring `project-spec` §7's shape)
17. Update process / review cadence (mirror `project-spec` §8's shape)
18. Source register — the draft's curated register re-keyed `[1]`→`[S01]` … `[18]`→`[S18]`, each entry with its link from the draft's "Source links" subsection; add the packaged-half research report as `[S19]`

Rewrite every ported claim in requirement language (MUST/SHOULD/MAY). Delete all "Executive Summary" / "Bottom line" / "Observation—Inference—Recommendation" framing — argument goes to Task 5's resources file, rules stay here.

- [ ] **Step 2: Byte-level artifact check**

Run: `grep -cP '[\x{E000}-\x{F8FF}]' standards/cli-documentation/README.md` Expected: `0`

- [ ] **Step 3: Lint**

Run: `npx prettier --write standards/cli-documentation/README.md && npx prettier --check standards/cli-documentation/README.md && npx markdownlint-cli2 standards/cli-documentation/README.md` Expected: Prettier clean (stable on second run), markdownlint `0 error(s)`.

- [ ] **Step 4: Commit**

```bash
git add standards/cli-documentation/README.md
git commit -m "feat(cli-docs): author normative CLI Documentation Standard README"
```

---

### Task 3: Author the templates

**Files:**

- Create: `standards/cli-documentation/templates/usage-doc.md`
- Create: `standards/cli-documentation/templates/readme-single-file.md`
- Create: `standards/cli-documentation/templates/cli-docs-check.yml`

**Interfaces:**

- Produces: `usage-doc.md` and `cli-docs-check.yml` are byte-copied into the bundle in Task 10 (byte-identity tested); `readme-single-file.md` is manual-copy only (spec decision 6).

- [ ] **Step 1: `usage-doc.md`** — port the draft's "Reusable Markdown template for canonical usage docs" block (draft ~line 198) as a standalone file. NO frontmatter (templates are excluded placeholders). Fold in the option-entry block and task-first example block from the draft as in-template examples. Remove the stray blank lines before closing fences if any survive the port. Placeholders use `toolname` / `<file>` style exactly as the draft.

- [ ] **Step 2: `readme-single-file.md`** — port the draft's "Compact single-file README template" block (draft ~line 315) as a standalone file, same rules.

- [ ] **Step 3: `cli-docs-check.yml`** — the copy-adopt CI workflow (new content; the draft only sketches checks):

```yaml
# CLI documentation drift checks — copy-adopt template from the CLI Documentation
# Standard (project-standards). Edit the env block for your tool, then delete this header.
name: cli-docs-check

on:
  push:
    branches: [main]
  pull_request:

env:
  # Your installed command name ([project.scripts] key), not the module path.
  TOOL: toolname
  NO_COLOR: '1'

jobs:
  cli-docs-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      # SHA-pinned per this repo's action-hardening policy (docs/handoff/bugs/001-setup-uv-
      # v8-tag-withdrawn.md: moving tags broke CI once). Re-verify the pin when copying.
      - uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
      - name: Build and install the wheel into a clean venv
        run: |
          uv build --wheel --out-dir dist/
          uv venv .cli-docs-venv
          uv pip install --python .cli-docs-venv dist/*.whl
      - name: Smoke the installed wrapper
        run: |
          .cli-docs-venv/bin/"$TOOL" --help
          .cli-docs-venv/bin/"$TOOL" --version
      # Optional: add normalized help-snapshot or docs-parity steps per the
      # standard's CI section (fix terminal width, keep NO_COLOR set).
```

- [ ] **Step 4: Lint + verify templates stay excluded from frontmatter validation**

Run: `npx prettier --write standards/cli-documentation/templates/ && npx markdownlint-cli2 "standards/cli-documentation/templates/*.md" && uv run validate-frontmatter --config .project-standards.yml` Expected: lint clean; validator still `✓ 19 file(s)` (templates excluded by `standards/**/templates/**`).

- [ ] **Step 5: Commit**

```bash
git add standards/cli-documentation/templates/
git commit -m "feat(cli-docs): add usage-doc, single-file README, and CI check templates"
```

---

### Task 4: Author `adopt.md`

**Files:**

- Create: `standards/cli-documentation/adopt.md`
- Read (model): `standards/markdown-tooling/adopt.md`

**Interfaces:**

- Consumes: README section numbers from Task 2; template filenames from Task 3.
- Produces: the runbook `project-standards adopt cli-documentation` guidance points at (Task 10's manifest materializes what §"What adopt materializes" describes).

- [ ] **Step 1: Write the runbook** with canonical frontmatter (`doc_type: 'runbook'`, id `runbook-m2x8fp-adopt-cli-documentation`, related → `README.md`, same key order as Task 2). Sections:

1. Choose a profile (decision table keyed to README §6's signals; record the choice in your usage doc)
2. What `adopt` materializes vs what you copy manually — table: `docs/usage.md` scaffold (adopt), `.github/workflows/cli-docs-check.yml` (adopt), `cli_documentation` config fragment (adopt, printed not written), `templates/readme-single-file.md` (manual copy for Script-profile repos)
3. Fill the usage scaffold (entry-point name in `NAME`/`SYNOPSIS`; every leaf command; option-entry required fields per README §9)
4. Wire the CI workflow (edit the `TOOL` env; keep `NO_COLOR`)
5. Authoring and review checklist — port the draft's "Authoring and review checklist" table (~line 430) verbatim, plus three new rows: "Every `[project.scripts]` key documented or classified internal?", "Installed-wrapper smoke test present?", "Option/exit-code sections checked against normalized `--help`?"
6. Conformance summary per profile (three-row table: what a Script / Packaged / Packaged-deep repo must show)

- [ ] **Step 2: Lint** (same commands as Task 3 step 4; validator count unchanged — still under the interim exclude until Task 6).

- [ ] **Step 3: Commit**

```bash
git add standards/cli-documentation/adopt.md
git commit -m "feat(cli-docs): add adoption runbook"
```

---

### Task 5: Author `resources/research-notes.md`; delete the draft monolith

**Files:**

- Create: `standards/cli-documentation/resources/research-notes.md`
- Delete: `standards/cli-documentation/cli-documentation-standards.md`

**Interfaces:**

- Consumes: everything Tasks 2–4 did **not** port from the draft.
- Produces: the standard's rationale record; the draft file ceases to exist (git history preserves it — spec §3).

- [ ] **Step 1: Write the resources file** with canonical frontmatter (`doc_type: 'reference'`, id `reference-p4n9tk-cli-documentation-research-notes`, related → `../README.md` and the two `docs/research/` reports). Content — the draft's argumentative material, lightly edited for flow, explicitly labeled as rationale not rules:

- Standards landscape table (draft §"Standards landscape")
- The four standards details worth policy (draft "A few standards details matter…")
- Tooling comparison: help2man / argparse-manpage / sphinx-click / sphinx-argparse (+ the packaged-half additions: sphinxcontrib-typer, mkdocs-click, mkdocs-typer2, sphinx-argparse-cli, pytest-console-scripts, python-cli-test-helpers)
- The localization/versioning/accessibility Observation→Inference→Recommendation triad (draft §"Localization, versioning, changelogs, and accessibility")
- Man-pages-in-wheels rationale (from the packaged research §3)
- Open questions: versioned-docs hosting; PEP 772 man-page formalization
- Pointers: `docs/research/2026-07-07-cli-usage-docs-packaged-src-layout-python.md` and the original draft's git history (`git log --follow -- standards/cli-documentation/cli-documentation-standards.md`)

- [ ] **Step 2: Verify nothing normative was lost** — diff-read the draft one final time against Tasks 2–5 outputs: every draft section must now live in README (rules), adopt.md (checklist), templates/ (scaffolds), or resources/ (rationale). Then:

```bash
git rm standards/cli-documentation/cli-documentation-standards.md
```

- [ ] **Step 3: Lint + artifact check**

Run: `npx prettier --write standards/cli-documentation/resources/ && npx markdownlint-cli2 "standards/cli-documentation/**/*.md" && grep -rcP '[\x{E000}-\x{F8FF}]' standards/cli-documentation/ | grep -v ':0' || echo CLEAN` Expected: lint clean; `CLEAN`.

- [ ] **Step 4: Commit**

```bash
git add -A standards/cli-documentation/
git commit -m "feat(cli-docs): park research rationale in resources/; retire the draft monolith"
```

---

### Task 6: Remove the interim exclude — bundle prose validates

**Files:**

- Modify: `.project-standards.yml` (delete the Task-1 exclude block)

- [ ] **Step 1: Delete the `standards/cli-documentation/**`exclude and its comment** from`.project-standards.yml`.

- [ ] **Step 2: Validate**

Run: `uv run validate-frontmatter --config .project-standards.yml && uv run project-standards validate` Expected: `✓ 22 file(s) validated` (19 + README + adopt.md + research-notes.md; templates still excluded). Both exit 0. If ids fail the format check, run `uv run project-standards fix` and re-validate.

- [ ] **Step 3: Commit**

```bash
git add .project-standards.yml
git commit -m "feat(cli-docs): validate bundle prose (drop interim frontmatter exclude)"
```

---

### Task 7: `--version` on every installed command (TDD)

**Files:**

- Create: `src/project_standards/_version.py`
- Create: `tests/test_version_flag.py`
- Modify: `src/project_standards/cli.py` (early dispatch + argparse advertisement)
- Modify: `src/project_standards/validate_frontmatter.py`, `validate_id.py`, `format_frontmatter.py`, `validate_references.py` (argparse mains)
- Modify: `src/project_standards/sync_vscode_colors.py`, `sync_standards_include.py` (raw-`sys.argv` mains)

**Interfaces:**

- Produces: `project_standards._version.package_version() -> str` (returns the installed distribution version, e.g. `"4.2.0"`); every console script exits 0 on `--version` printing `<prog> <version>`. Task 11's smoke test and Task 8's usage doc rely on this.

- [ ] **Step 1: Write the failing tests**

```python
"""--version contract for every installed command (spec §8, codex SA-002)."""

from __future__ import annotations

import pytest

from project_standards import (
    cli,
    format_frontmatter,
    sync_standards_include,
    sync_vscode_colors,
    validate_frontmatter,
    validate_id,
    validate_references,
)
from project_standards._version import package_version


def test_package_version_is_nonempty_pep440ish() -> None:
    v = package_version()
    assert v and v[0].isdigit()


def test_cli_version_flag_prints_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--version"]) == 0
    out = capsys.readouterr().out
    assert out.strip() == f"project-standards {package_version()}"


@pytest.mark.parametrize(
    "module",
    [validate_frontmatter, validate_id, format_frontmatter, validate_references],
)
def test_argparse_mains_version_flag(module, capsys: pytest.CaptureFixture[str]) -> None:
    # In-process prog varies with sys.argv[0]; the EXACT "<script> <version>" contract
    # is asserted against the installed wrappers in tests/test_installed_wrappers.py
    # (codex CR-004) — here we only prove the flag exists and exits 0.
    with pytest.raises(SystemExit) as exc:
        module.main(["--version"])
    assert exc.value.code == 0
    assert package_version() in capsys.readouterr().out


@pytest.mark.parametrize("module", [sync_vscode_colors, sync_standards_include])
def test_sync_mains_version_flag(
    module, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", [module.__name__, "--version"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 0
    assert package_version() in capsys.readouterr().out
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_version_flag.py -v` Expected: FAIL — `ModuleNotFoundError: No module named 'project_standards._version'`.

- [ ] **Step 3: Implement the helper**

```python
"""Shared --version support for every installed console script (spec §8).

One helper, one distribution name: all seven [project.scripts] wrappers report the
same package version, satisfying the CLI Documentation Standard's Script-tier MUST.
"""

from __future__ import annotations

from importlib.metadata import version as _dist_version


def package_version() -> str:
    return _dist_version("project-standards")
```

- [ ] **Step 4: Wire the seven entry points**

`cli.py` — insert immediately after `args_list = list(...)` in `main()`:

```python
    if args_list and args_list[0] == "--version":
        from project_standards._version import package_version

        print(f"project-standards {package_version()}")
        return 0
```

Also advertise it on the argparse parser (after `parser = argparse.ArgumentParser(prog="project-standards")`):

```python
    parser.add_argument(
        "--version", action="store_true", help="print the package version and exit"
    )
```

(The early dispatch handles the real behavior; the argparse flag only makes `--help` honest.)

Each argparse main (`validate_frontmatter.py`, `validate_id.py`, `format_frontmatter.py`, `validate_references.py`) — add to its parser, adjacent to the existing argument definitions:

```python
    from project_standards._version import package_version

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {package_version()}"
    )
```

(Import at module top per house import style; shown inline here only for adjacency.)

Each sync main (`sync_vscode_colors.py`, `sync_standards_include.py`) — first lines of `main()`:

```python
    if "--version" in sys.argv[1:]:
        from project_standards._version import package_version

        print(f"{Path(sys.argv[0]).name} {package_version()}")
        raise SystemExit(0)
```

- [ ] **Step 5: Run tests + type/lint gate subset**

Run: `uv run pytest tests/test_version_flag.py tests/test_cli_fix.py tests/test_adopt_cli.py -v && uv run ruff format --check . && uv run ruff check . && uv run basedpyright` Expected: all PASS, 0 issues.

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/_version.py src/project_standards/*.py tests/test_version_flag.py
git commit -m "feat(cli): add --version to all seven installed commands via shared helper"
```

---

### Task 8: Dogfood `docs/usage.md` + include glob + parity pass

**Files:**

- Create: `docs/usage.md`
- Modify: `.project-standards.yml` (add `docs/usage.md` to `include:`)

**Interfaces:**

- Consumes: Task 3's `usage-doc.md` template structure; Task 7's `--version`.
- Produces: the authoritative usage reference for this repo; source for Task 9's example and Task 11's inventory guard (which asserts headings of the form `` ### `command` ``).

- [ ] **Step 1: Capture ground truth** — for every command, capture normalized help:

```bash
NO_COLOR=1 COLUMNS=100 uv run project-standards --help
NO_COLOR=1 COLUMNS=100 uv run project-standards validate --help
NO_COLOR=1 COLUMNS=100 uv run project-standards fix --help
NO_COLOR=1 COLUMNS=100 uv run project-standards spec --help
# ...and: spec validate|lint|extract|next|new|upgrade --help, adopt --help, list --help,
# then each standalone: validate-frontmatter --help, validate-id --help,
# sync-vscode-colors --help (positional-only; document argv contract from source),
# sync-standards-include --help, format-frontmatter --help, validate-references --help
```

- [ ] **Step 2: Author `docs/usage.md`** from the Task 3 template. Frontmatter: `doc_type: 'reference'`, id `reference-u6b3wn-project-standards-cli-usage`, related → `standards/cli-documentation/README.md`. Required structure (Packaged profile, README §6; grouped-page provision):

- `NAME` — `project-standards` keyed to the entry-point name
- `SYNOPSIS` — GitHub-CLI notation, `--` and `{a \| b}` escaping rules
- `DESCRIPTION` — profile selection recorded here: "Packaged (10 leaf commands + `spec` group overview; single page maintainable)"
- `OPTIONS` / commands — one `` ### `command` `` heading per leaf: `validate`, `fix`, `adopt`, `list`, plus `` ### `spec` `` (group overview) and `` ### `spec validate` `` … `` ### `spec upgrade` `` (6 verbs); every option entry carries the README §9 required fields (spelling, value syntax, meaning, default, conflicts, scope)
- `EXIT STATUS` — 0 / 1 (validation findings) / 2 (usage, config, registry/bundle drift) / 3 where applicable (per-command notes)
- `ENVIRONMENT` — whatever Step 1 shows the commands actually read (`NO_COLOR` at minimum via argparse defaults); if a command reads nothing, say so
- `EXAMPLES` — task-first, copy-pasteable (`uv run project-standards validate --config .project-standards.yml`, `... adopt markdown-tooling --dry-run`, `... spec new docs/specs/my-feature.md`)
- **Standalone commands** — one `` ### `name` `` complete entry per standalone script (`validate-frontmatter`, `validate-id`, `sync-vscode-colors`, `sync-standards-include`, `format-frontmatter`, `validate-references`): NAME line, SYNOPSIS, options, exit codes, cross-reference to the unified equivalent where one exists (`validate-frontmatter` ↔ `project-standards validate`; `format-frontmatter`+`validate-id --fix` ↔ `project-standards fix`)
- `SEE ALSO` — `standards/cli-documentation/README.md`, `src/project_standards/README.md`

**Option/exit-code parity pass (spec §8, codex SA-NEW-003):** as each entry is written, check its OPTIONS and EXIT STATUS against the Step 1 captures and the module source. Make the evidence durable (codex plan-review note): list every checked command in the commit **body** (one line per command, e.g. `parity: spec validate — options+exit codes vs --help: OK`), and end with the trailer `Parity-pass: all 18 command entries (root project-standards + 4 top-level leaves + spec overview + 6 spec verbs + 6 standalone) checked against normalized --help; manual assertions: <list or none>`. The commit message is the review artifact — do not keep the raw captures as repo files.

- [ ] **Step 3: Add to include globs** in `.project-standards.yml`:

```yaml
include:
  - 'CHANGELOG.md'
  - 'UPGRADING.md'
  - 'docs/usage.md'
  - 'standards/**/*.md'
  - 'meta/**/*.md'
```

- [ ] **Step 4: Verify it is actually validated**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: `✓ 23 file(s) validated` (22 + docs/usage.md). Also run `uv run validate-frontmatter docs/usage.md --config .project-standards.yml` — exit 0.

- [ ] **Step 5: Lint + commit**

```bash
npx prettier --write docs/usage.md && npx markdownlint-cli2 docs/usage.md
git add docs/usage.md .project-standards.yml
git commit -m "feat(cli-docs): dogfood docs/usage.md for the full installed-command set

Parity-pass: all 18 command entries (root project-standards + 4 top-level leaves + spec overview + 6 spec verbs + 6 standalone) checked against normalized --help; manual assertions: none"
```

---

### Task 9: `examples/usage.example.md`

**Files:**

- Create: `standards/cli-documentation/examples/usage.example.md`

**Interfaces:**

- Consumes: `docs/usage.md` (Task 8).

- [ ] **Step 1: Derive the example** — copy `docs/usage.md`, trim to: NAME, SYNOPSIS, DESCRIPTION, the four top-level leaf entries, EXIT STATUS, two EXAMPLES, one standalone-command entry, SEE ALSO. New frontmatter id `reference-e8r2vy-cli-usage-worked-example`, description noting it is the standard's worked example, related → `../README.md`. Also add `standards/cli-documentation/examples/usage.example.md` to the `related:` list in `standards/cli-documentation/README.md` (deferred from Task 2 so the reference never dangles).

- [ ] **Step 2: Validate + lint**

Run: `uv run validate-frontmatter --config .project-standards.yml && npx prettier --write standards/cli-documentation/examples/ && npx markdownlint-cli2 "standards/cli-documentation/examples/*.md"` Expected: `✓ 24 file(s) validated`; lint clean.

- [ ] **Step 3: Commit**

```bash
git add standards/cli-documentation/examples/ standards/cli-documentation/README.md
git commit -m "feat(cli-docs): add validated worked example"
git status --short   # expect: empty (codex CR-003 — the README related-list edit must not be left dirty)
```

---

### Task 10: Register the standard end-to-end (atomic: registry + validator + CLI + bundle + config)

**Files:**

- Modify: `src/project_standards/schemas/registry.json`
- Modify: `src/project_standards/registry.py`
- Modify: `src/project_standards/validate_frontmatter.py`
- Modify: `src/project_standards/cli.py:36-49`
- Create: `src/project_standards/bundles/cli-documentation/adopt.toml`
- Create: `src/project_standards/bundles/cli-documentation/usage-doc.md` (byte copy of `standards/cli-documentation/templates/usage-doc.md`)
- Create: `src/project_standards/bundles/cli-documentation/cli-docs-check.yml` (byte copy of `standards/cli-documentation/templates/cli-docs-check.yml`)
- Create: `src/project_standards/bundles/cli-documentation/config.cli-documentation.yml` (fragment source)
- Modify: `.project-standards.yml` (contract block)
- Create: `tests/test_registry_cli_documentation.py`
- Modify: `tests/test_adopt_manifest.py` (four → five), `tests/test_adopt_dogfood.py` (`_DOGFOOD` map), `tests/test_adopt_packaging.py` (wheel contents)

**Interfaces:**

- Consumes: Task 3 template files (byte-copied).
- Produces: `Registry.cli_documentation_default: str`, `Registry.is_known_cli_documentation(version) -> bool`; config field `Config.cli_documentation_version: str | None`; `project-standards adopt cli-documentation` materializes `docs/usage.md` + `.github/workflows/cli-docs-check.yml` and reports the config fragment.

This task is atomic because `_assert_registry_bundle_parity` (cli.py:67) exits 2 whenever registry and `bundles/` disagree — a bundle without a contract, or vice versa, breaks `list`/`adopt` and their tests mid-sequence.

- [ ] **Step 1: Write the failing tests** — `tests/test_registry_cli_documentation.py` (model: `tests/test_registry_markdown_tooling.py`):

```python
"""cli_documentation contract-version registration (spec §7/§9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.registry import load_registry
from project_standards import validate_frontmatter

# The include pattern deliberately matches nothing: an EMPTY include list is falsy and
# falls back to _default_corpus() (validate_frontmatter.py:423-427 `elif include_patterns:`),
# which would validate the whole repo (codex CR-001). The version gate runs BEFORE path
# collection, so a no-match run still exercises it; zero files exits 0 with
# "no files matched" on stderr (validate_frontmatter.py:832-835).
_CONFIG_KNOWN = """\
markdown:
  frontmatter:
    version: "1.1"
    schema: "markdown-frontmatter"
    include:
      - "no-such-path/**/*.md"
cli_documentation:
  version: "{version}"
"""


def test_registry_bundles_cli_documentation_default() -> None:
    reg = load_registry()
    assert reg.cli_documentation_default == "1.0"
    assert reg.is_known_cli_documentation("1.0")
    assert not reg.is_known_cli_documentation("9.9")


def _run_with_config(tmp_path: Path, version_yaml: str) -> int:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(version_yaml, encoding="utf-8")
    return validate_frontmatter.main(["--config", str(cfg)])


def test_known_version_accepted_silently(tmp_path: Path) -> None:
    assert _run_with_config(tmp_path, _CONFIG_KNOWN.format(version="1.0")) == 0


def test_unknown_version_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run_with_config(tmp_path, _CONFIG_KNOWN.format(version="9.9")) == 2
    assert "unknown cli_documentation.version" in capsys.readouterr().err


def test_non_string_version_exits_2(tmp_path: Path) -> None:
    bad = _CONFIG_KNOWN.replace('version: "{version}"', "version: 1.0")  # bare float
    assert _run_with_config(tmp_path, bad) == 2


def test_dogfood_config_selects_1_0() -> None:
    cfg = validate_frontmatter.load_config(Path(".project-standards.yml"))
    assert cfg.cli_documentation_version == "1.0"
```

Also update, in the same step: `tests/test_adopt_manifest.py::test_available_standards_lists_four_released_excludes_shared` → rename to `..._five_...`, expected set gains `"cli-documentation"`; `tests/test_adopt_dogfood.py::_DOGFOOD` gains:

```python
    "cli-documentation/usage-doc.md": "standards/cli-documentation/templates/usage-doc.md",
    "cli-documentation/cli-docs-check.yml": "standards/cli-documentation/templates/cli-docs-check.yml",
```

and `tests/test_adopt_packaging.py::test_wheel_contains_bundles_and_manifests` asserts `project_standards/bundles/cli-documentation/adopt.toml` (match its existing assertion style).

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_registry_cli_documentation.py tests/test_adopt_manifest.py tests/test_adopt_dogfood.py -x` Expected: FAIL — `AttributeError: ... 'cli_documentation_default'` first.

- [ ] **Step 3: Implement — registry.json**

```json
	"markdown_tooling": { "default": "1.1", "versions": ["1.0", "1.1"] },
	"cli_documentation": { "default": "1.0", "versions": ["1.0"] }
```

- [ ] **Step 4: Implement — `registry.py`** (mirror the `markdown_tooling` plumbing exactly): constructor kwargs `cli_documentation_default: str` + `cli_documentation_versions: list[str]`; attributes; method

```python
    def is_known_cli_documentation(self, version: str) -> bool:
        return version in self.cli_documentation_versions
```

`load_registry`: read `cd = data.get("cli_documentation")` alongside `mt`, same isinstance checks, `cd_default` non-string check, `cd_versions` list parse, cross-field default-in-versions check, pass both to `Registry(...)`. Update the module docstring's standard enumeration.

- [ ] **Step 5: Implement — `validate_frontmatter.py`**: add `cli_documentation_version: str | None = None` to the `Config` dataclass/init (lines ~481–493, ~598), parse `raw_dict.get("cli_documentation")` beside `markdown_tooling` (~647), include in `needs_registry` (~751), and add the gate (mirror the markdown_tooling block at ~779):

```python
    if (
        registry is not None
        and config.cli_documentation_version is not None
        and not registry.is_known_cli_documentation(config.cli_documentation_version)
    ):
        print(
            f"error: unknown cli_documentation.version {config.cli_documentation_version!r}",
            file=sys.stderr,
        )
        return 2
```

- [ ] **Step 6: Implement — `cli.py`**: add `"cli-documentation": registry.cli_documentation_default,` to `_contract_version`'s map and `"cli-documentation",` to `_REGISTRY_STANDARD_IDS`.

- [ ] **Step 7: Implement — the bundle.** Byte-copy the two templates (`cp` exactly, no edits), write the fragment source `config.cli-documentation.yml`:

```yaml
cli_documentation:
  version: '1.0'
```

and `adopt.toml`:

```toml
[standard]
id = "cli-documentation"

[[artifact]]
kind = "file"
owner = true
source = "usage-doc.md"
dest = "docs/usage.md"

[[artifact]]
kind = "file"
owner = true
source = "cli-docs-check.yml"
dest = ".github/workflows/cli-docs-check.yml"

[[artifact]]
kind = "fragment"
owner = true
source = "config.cli-documentation.yml"
target = ".project-standards.yml"
```

- [ ] **Step 8: Implement — dogfood config block.** Add to `.project-standards.yml` (top level, after the `markdown_tooling`/`python_tooling` blocks — match their placement):

```yaml
cli_documentation:
  version: '1.0'
```

- [ ] **Step 9: Adopt-behavior verification** (spec §7 semantics — created / skipped / fragment):

Run: `uv run project-standards list && uv run project-standards adopt cli-documentation --dry-run` Expected: `list` shows `cli-documentation (contract 1.0)` with 3 artifacts, exit 0 (parity holds). Dry run reports `docs/usage.md` as **Skipped (already present)** (Task 8 wrote the real one), `.github/workflows/cli-docs-check.yml` under **Created**, and the fragment under "Add these sections to `.project-standards.yml`". If `tests/test_adopt_cli.py` or `tests/test_adopt_engine.py` hardcode standard counts/ids, update them in this step.

- [ ] **Step 10: Full test pass**

Run: `uv run coverage run -m pytest && uv run coverage report && uv run ruff format --check . && uv run ruff check . && uv run basedpyright` Expected: all pass; coverage ≥ existing threshold (98%).

- [ ] **Step 11: Commit**

```bash
git add src/project_standards/ tests/ .project-standards.yml
git commit -m "feat(cli-docs): register cli-documentation standard (registry, validator gate, CLI, bundle, dogfood config)"
```

---

### Task 11: Installed-wrapper smoke + inventory-parity guards (TDD)

**Files:**

- Create: `tests/test_installed_wrappers.py`
- Create: `tests/test_usage_doc_inventory.py`

**Interfaces:**

- Consumes: Task 7 `--version`; Task 8 `docs/usage.md`; `specs/cli.py:_VERBS`.

- [ ] **Step 1: Write the inventory-parity test**

```python
"""docs/usage.md inventory parity (spec §8/§9): every installed command and
every project-standards parser leaf must have a heading entry."""

from __future__ import annotations

import tomllib
from pathlib import Path

from project_standards.specs.cli import _VERBS

_USAGE = Path("docs/usage.md").read_text(encoding="utf-8")

# Top-level leaves are argparse-registered in cli.py; keep in sync with the parser.
_TOP_LEVEL_LEAVES = ("validate", "fix", "adopt", "list")


def _has_entry(name: str) -> bool:
    return f"### `{name}`" in _USAGE


def test_every_console_script_documented() -> None:
    scripts = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "scripts"
    ]
    missing = [name for name in scripts if not _has_entry(name)]
    assert not missing, f"console scripts missing from docs/usage.md: {missing}"


def test_every_top_level_leaf_documented() -> None:
    missing = [name for name in _TOP_LEVEL_LEAVES if not _has_entry(name)]
    assert not missing, f"top-level commands missing from docs/usage.md: {missing}"


def test_spec_group_and_every_verb_documented() -> None:
    assert _has_entry("spec"), "spec group overview missing"
    missing = [v for v in _VERBS if not _has_entry(f"spec {v}")]
    assert not missing, f"spec verbs missing from docs/usage.md: {missing}"
```

(If Task 8's headings differ — e.g. `` ### `project-standards validate` `` — adjust `_has_entry` to the authored convention once, in this test, and keep usage.md and the test consistent.)

- [ ] **Step 2: Write the installed-wrapper smoke test**

```python
"""Installed-wrapper smoke (spec §8, codex SA-005 + SA-NEW-001): build the wheel,
install into a throwaway venv, run every console script via the installed wrapper.
Slowest test in the suite alongside test_adopt_packaging."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

import pytest

_SCRIPTS = tuple(
    tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
)


@pytest.fixture(scope="module")
def installed_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("wheel-smoke")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp)], check=True, capture_output=True
    )
    (wheel,) = tmp.glob("*.whl")
    venv = tmp / "venv"
    subprocess.run(["uv", "venv", str(venv)], check=True, capture_output=True)
    subprocess.run(
        ["uv", "pip", "install", "--python", str(venv / "bin" / "python"), str(wheel)],
        check=True,
        capture_output=True,
    )
    return venv


def _run(venv: Path, cmd: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NO_COLOR": "1", "COLUMNS": "100"}
    return subprocess.run(
        [str(venv / "bin" / cmd), *args], capture_output=True, text=True, env=env
    )


@pytest.mark.parametrize("script", _SCRIPTS)
def test_wrapper_help_exits_zero(installed_venv: Path, script: str) -> None:
    proc = _run(installed_venv, script, "--help")
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("script", _SCRIPTS)
def test_wrapper_version_prints_exact_contract(installed_venv: Path, script: str) -> None:
    # The standard's contract is EXACT "<script-name> <version>" (codex CR-004): the
    # installed wrapper name is sys.argv[0], so argparse %(prog)s, the sync mains'
    # Path(sys.argv[0]).name, and cli.py's literal all resolve to the script name here.
    from project_standards._version import package_version

    proc = _run(installed_venv, script, "--version")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == f"{script} {package_version()}"


def test_nested_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "spec", "validate", "--help")
    assert proc.returncode == 0, proc.stderr
```

Note: `sync-vscode-colors --help`/`sync-standards-include --help` — these mains take raw positionals; if `--help` currently falls through to the file-existence check and exits non-zero, add the same early-`sys.argv` intercept for `--help` as Task 7 added for `--version` (print a one-paragraph usage string, exit 0) and document it in `docs/usage.md`. The standard's Script-tier MUST covers `--help` too.

- [ ] **Step 3: Run both**

Run: `uv run pytest tests/test_usage_doc_inventory.py tests/test_installed_wrappers.py -v` Expected: PASS (fix usage.md headings or the sync-main `--help` gap if red — that is the guard doing its job).

- [ ] **Step 4: Full suite + commit**

```bash
uv run coverage run -m pytest && uv run coverage report
git add tests/test_usage_doc_inventory.py tests/test_installed_wrappers.py src/ docs/usage.md
git commit -m "test(cli-docs): installed-wrapper smoke + usage-doc inventory parity guards"
```

---

### Task 12: Docs propagation (seven surfaces)

**Files:**

- Modify: `standards/README.md`, `README.md` (root), `CLAUDE.md` (root), `docs/handoff/architecture.md`, `docs/handoff/specs-plans.md`, `src/project_standards/README.md`, `STATUS.md`

**Interfaces:**

- Consumes: everything shipped in Tasks 1–11. Each surface already carries a parallel row/entry for the five released standards — mirror it.

- [ ] **Step 1: `standards/README.md`** — add the table row `| CLI Documentation | User-facing CLI usage docs: help text, usage references, man pages, CI drift checks | [cli-documentation/](cli-documentation/) | [adopt](cli-documentation/adopt.md) |`; update the "Bundle anatomy" prose: the README-only note still says "currently just python-coding/" (verify unchanged) and the anatomy block gains a `resources/` line (`OPTIONAL — rationale/research notes (validated)`), citing `project-spec/` and `cli-documentation/` as holders.
- [ ] **Step 2: Root `README.md`** — intro "single source of truth" enumeration (five → six), ToC entry, directory tree, a `### CLI Documentation Standard` subsection (mirror the Markdown Tooling subsection's length: what it governs, profile ladder in one sentence, adopt command), adoption map row.
- [ ] **Step 3: Root `CLAUDE.md`** — Purpose line: "defines five" → "defines six", add **CLI Documentation** (profile-tiered usage-doc standard, adopt-materialized scaffolds + validator-registered `cli_documentation` contract) to the enumerated list.
- [ ] **Step 4: `docs/handoff/architecture.md`** — component-graph standards list gains the sixth standard; remove any standing-backlog line about the CLI-docs draft.
- [ ] **Step 5: `docs/handoff/specs-plans.md`** — add spec + plan pointer rows (`docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md` approved codex r3; this plan).
- [ ] **Step 6: `src/project_standards/README.md`** (codex SA-NEW-002) — add a top note: "**Usage reference:** user-facing CLI documentation lives in [`docs/usage.md`](../../docs/usage.md); this file documents implementation internals." Refresh stale facts: console-script list (`--version` now universal), registry keys (+`cli_documentation`), bundle list (+`cli-documentation`), config example (+`cli_documentation:` block), "Adding a new standard" checklist (verify it matches what Tasks 1–11 actually required; amend where it drifted).
- [ ] **Step 7: `STATUS.md`** — at-a-glance: sixth standard integrated on `testing`, pending release decision.
- [ ] **Step 8: Verify + commit**

```bash
uv run validate-frontmatter --config .project-standards.yml && npx prettier --write . && npx markdownlint-cli2
rg -n "cli-framework" --glob '!docs/codex-reviews/**' --glob '!docs/superpowers/**' --glob '!docs/research/**' --glob '!docs/handoff/sessions/**' --glob '!TODO.md'
```

Expected: validator ✓; lint clean; the `rg` sweep returns **no hits** (historical-provenance globs excluded per spec SA-006 criterion).

```bash
git add standards/README.md README.md CLAUDE.md docs/handoff/ src/project_standards/README.md STATUS.md
git commit -m "docs(cli-docs): register sixth standard across all doc surfaces"
git status --short   # expect: empty — seven surfaces touched, none left dirty
```

---

### Task 13: Changelog, upgrading note, TODO closeout, full gate

**Files:**

- Modify: `CHANGELOG.md`, `UPGRADING.md`, `TODO.md`, `docs/handoff/state.md`

- [ ] **Step 1: `CHANGELOG.md`** — v4.3.0 (Unreleased or dated per house convention) entry under `Added`: the `cli-documentation` standard (bundle, adopt artifacts, `cli_documentation 1.0` contract), `--version` on all seven commands, `docs/usage.md`; under `Changed`: `src/project_standards/README.md` repositioned.
- [ ] **Step 2: `UPGRADING.md`** — one note: "v4.3.0: no action required. Caveat: the validator now recognizes `cli_documentation.version`; a config that already carried that key with an unrecognized value (previously ignored) now exits 2. No known such configs."
- [ ] **Step 3: `TODO.md`** — mark the CLI-docs integration phases done (Phases 1–8 subsumed by this spec/plan; leave the release decision noted as pending).
- [ ] **Step 4: `docs/handoff/state.md`** — update per handoff conventions (sixth standard on `testing`; release pending).
- [ ] **Step 5: Full gate (all of it, verbatim)**

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit \
  && uv run pytest tests/coherence \
  && npx prettier --check . && npx markdownlint-cli2 \
  && uv run validate-frontmatter --config .project-standards.yml \
  && uv run project-standards validate
```

Expected: everything green (`tests/coherence` needs `npm ci` done once).

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md UPGRADING.md TODO.md docs/handoff/state.md
git commit -m "docs(release): stage v4.3.0 notes for cli-documentation standard"
```

- [ ] **Step 7: Clean-tree check**

Run: `git status --short` Expected: empty (also re-check after Task 12 — multi-surface tasks are where files get left dirty).

**Release itself (tagging, `main` merge, GitHub release, `v4` tag move, and the `pyproject.toml`/`uv.lock` version bump to 4.3.0) is NOT part of this plan** — it is a user decision per `docs/handoff/state.md` session instructions and `meta/versioning.md`. Until that release commit, `--version` printing `4.2.0` on `testing` is **expected and correct** (codex note); `docs/usage.md` must therefore not embed a concrete version string in example output.
