# Markdown Tooling Standard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new governed standard bundle, `standards/markdown-tooling/`, that documents the recommended linting/formatting tools and settings (Prettier for all the files it supports, markdownlint for Markdown, EditorConfig as the floor), backed by a validated `markdown_tooling` contract version, and cross-linked from the Markdown Frontmatter standard.

**Architecture:** The bundle folder is doc-only (`README.md` + `adopt.md`); the contract-version _label_ is enforced in `src/` exactly like `python_tooling.version` (registry → validator → tests). Markdown is the anchor; Prettier's reach over `md`/`json`/`jsonc`/`yaml` is stated to match the `prettier .` command so coverage and command cannot diverge. DEC-9 is preserved: markdownlint ships a reusable workflow and a seedable rule set; Prettier is copy-adopt with no workflow.

**Tech Stack:** Python 3.13 (uv, ruff, basedpyright, pytest, coverage, pip-audit), the `validate-frontmatter` CLI, markdownlint-cli2 + Prettier (Node), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md` (brainstormed + 3 audit rounds; 7 findings resolved).

---

## File structure

Created:

- `standards/markdown-tooling/README.md` — the governing standard (source-backed, 18 sections).
- `standards/markdown-tooling/adopt.md` — the adoption runbook (`doc_type: runbook`).

Modified — code (the validated `markdown_tooling` label):

- `src/project_standards/schemas/registry.json` — add the `markdown_tooling` entry.
- `src/project_standards/registry.py` — parse + expose it; add `is_known_markdown_tooling`.
- `src/project_standards/validate_frontmatter.py` — read `markdown_tooling.version`; exit 2 on unknown.
- `tests/test_validate_frontmatter.py` — new tests; update the two direct `Registry(...)` constructions.

Modified — docs/navigation:

- `standards/markdown-frontmatter/README.md` — `related:` entry + in-body cross-link.
- `standards/README.md` — index-table row.
- `README.md` (root) — Standards section + Consuming section.
- `meta/versioning.md` — per-standard contract-version row + change-classification row.

Modified — config + bookkeeping:

- `.github/workflows/lint-markdown.yml` — example-comment `@v1` → `@v2`.
- `.vscode/settings.json` — `[markdown]` gains `editor.formatOnSave` (Prettier; no markdownlint code action).
- `CHANGELOG.md` — `[Unreleased] / Added` entry.
- `docs/handoff/specs-plans.md`, `docs/handoff/state.md`, `docs/handoff/architecture.md` — session bookkeeping.

Each task ends in its own commit. Run all commands from the repo root `/home/chris/projects/project-standards`.

---

## Task 1: Registry support for `markdown_tooling`

**Files:**

- Modify: `src/project_standards/schemas/registry.json`
- Modify: `src/project_standards/registry.py:38-143`
- Test: `tests/test_validate_frontmatter.py` (add tests + fix two existing `Registry(...)` calls at lines 1059 and 1191)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validate_frontmatter.py`:

```python
def test_registry_exposes_markdown_tooling() -> None:
    reg = load_registry()
    assert reg.markdown_tooling_default == "1.0"
    assert reg.is_known_markdown_tooling("1.0") is True
    assert reg.is_known_markdown_tooling("9.9") is False


def test_load_registry_requires_markdown_tooling(tmp_path: Path) -> None:
    bad = tmp_path / "registry.json"
    bad.write_text(
        '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}},'
        ' "adr": {"default": "1.0", "versions": {"1.0": {"supports_frontmatter": ["1.1"]}}},'
        ' "python_tooling": {"default": "1.0", "versions": ["1.0"]}}',
        encoding="utf-8",
    )
    with pytest.raises(RegistryError):
        load_registry(bad)
```

Confirm the imports at the top of the test module include `load_registry` and `RegistryError` (they are already imported for existing registry tests; add them to the existing `from project_standards.registry import ...` line if missing).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_validate_frontmatter.py::test_registry_exposes_markdown_tooling tests/test_validate_frontmatter.py::test_load_registry_requires_markdown_tooling -v` Expected: FAIL — `AttributeError: 'Registry' object has no attribute 'markdown_tooling_default'` (and the second test fails because the current `load_registry` does not require `markdown_tooling`).

- [ ] **Step 3: Add the registry entry**

Replace the entire contents of `src/project_standards/schemas/registry.json` with (tabs, to match the repo's Prettier style):

```json
{
	"frontmatter": { "default": "1.1", "versions": { "1.1": "markdown-frontmatter" } },
	"adr": {
		"default": "1.0",
		"versions": { "1.0": { "supports_frontmatter": ["1.1"] } }
	},
	"python_tooling": { "default": "1.0", "versions": ["1.0"] },
	"markdown_tooling": { "default": "1.0", "versions": ["1.0"] }
}
```

- [ ] **Step 4: Teach `registry.py` about `markdown_tooling`**

In `src/project_standards/registry.py`, add two parameters to `Registry.__init__` (after `python_tooling_versions`) and store them:

```python
    def __init__(
        self,
        *,
        frontmatter_default: str,
        frontmatter_versions: dict[str, str],
        adr_default: str,
        adr_supports: dict[str, list[str]],
        python_tooling_default: str,
        python_tooling_versions: list[str],
        markdown_tooling_default: str,
        markdown_tooling_versions: list[str],
    ) -> None:
        self.frontmatter_default = frontmatter_default
        self.frontmatter_versions = frontmatter_versions
        self.adr_default = adr_default
        self.adr_supports = adr_supports
        self.python_tooling_default = python_tooling_default
        self.python_tooling_versions = python_tooling_versions
        self.markdown_tooling_default = markdown_tooling_default
        self.markdown_tooling_versions = markdown_tooling_versions
```

Add the lookup method directly after `is_known_python_tooling`:

```python
    def is_known_markdown_tooling(self, version: str) -> bool:
        return version in self.markdown_tooling_versions
```

In `load_registry`, extend the required-objects fetch and parse the new list. Change:

```python
    fm = data.get("frontmatter")
    adr = data.get("adr")
    pt = data.get("python_tooling")
    if not isinstance(fm, dict) or not isinstance(adr, dict) or not isinstance(pt, dict):
        raise RegistryError(f"registry {path} missing frontmatter/adr/python_tooling objects")
    fm_d = cast("dict[str, Any]", fm)
    adr_d = cast("dict[str, Any]", adr)
    pt_d = cast("dict[str, Any]", pt)
```

to:

```python
    fm = data.get("frontmatter")
    adr = data.get("adr")
    pt = data.get("python_tooling")
    mt = data.get("markdown_tooling")
    if (
        not isinstance(fm, dict)
        or not isinstance(adr, dict)
        or not isinstance(pt, dict)
        or not isinstance(mt, dict)
    ):
        raise RegistryError(
            f"registry {path} missing frontmatter/adr/python_tooling/markdown_tooling objects"
        )
    fm_d = cast("dict[str, Any]", fm)
    adr_d = cast("dict[str, Any]", adr)
    pt_d = cast("dict[str, Any]", pt)
    mt_d = cast("dict[str, Any]", mt)
```

Extend the defaults check. Change:

```python
    fm_default = fm_d.get("default")
    adr_default = adr_d.get("default")
    pt_default = pt_d.get("default")
    if (
        not isinstance(fm_default, str)
        or not isinstance(adr_default, str)
        or not isinstance(pt_default, str)
    ):
        raise RegistryError(f"registry {path} has a non-string default")
```

to:

```python
    fm_default = fm_d.get("default")
    adr_default = adr_d.get("default")
    pt_default = pt_d.get("default")
    mt_default = mt_d.get("default")
    if (
        not isinstance(fm_default, str)
        or not isinstance(adr_default, str)
        or not isinstance(pt_default, str)
        or not isinstance(mt_default, str)
    ):
        raise RegistryError(f"registry {path} has a non-string default")
```

After the `pt_versions` block, add the `mt_versions` parse:

```python
    pt_versions_raw = pt_d.get("versions")
    if not isinstance(pt_versions_raw, list):
        raise RegistryError("registry python_tooling.versions is not a list")
    pt_versions = [str(v) for v in cast("list[Any]", pt_versions_raw)]

    mt_versions_raw = mt_d.get("versions")
    if not isinstance(mt_versions_raw, list):
        raise RegistryError("registry markdown_tooling.versions is not a list")
    mt_versions = [str(v) for v in cast("list[Any]", mt_versions_raw)]
```

Extend the `return Registry(...)` to pass the new fields:

```python
    return Registry(
        frontmatter_default=fm_default,
        frontmatter_versions=fm_versions,
        adr_default=adr_default,
        adr_supports=adr_supports,
        python_tooling_default=pt_default,
        python_tooling_versions=pt_versions,
        markdown_tooling_default=mt_default,
        markdown_tooling_versions=mt_versions,
    )
```

- [ ] **Step 5: Fix the two existing direct `Registry(...)` constructions in the tests**

`Registry.__init__` now requires the two new keyword args, so both hand-built registries in `tests/test_validate_frontmatter.py` must pass them. In `test_compat_gate_flags_known_incompatible_pair` (≈ line 1059) and `test_main_incompatible_combo_via_registry_exits_2` (≈ line 1191), add these two lines immediately after the `python_tooling_versions=["1.0"],` line inside each `Registry(` call:

```python
        markdown_tooling_default="1.0",
        markdown_tooling_versions=["1.0"],
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validate_frontmatter.py -q` Expected: PASS (all tests, including the two new ones and the two edited constructions).

- [ ] **Step 7: Commit**

```bash
git add src/project_standards/schemas/registry.json src/project_standards/registry.py tests/test_validate_frontmatter.py
git commit -m "feat(registry): add markdown_tooling contract version"
```

---

## Task 2: Validate `markdown_tooling.version` in the CLI

**Files:**

- Modify: `src/project_standards/validate_frontmatter.py:283-302` (ProjectConfig), `:366-418` (load_config), `:483-491` (main guard)
- Test: `tests/test_validate_frontmatter.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validate_frontmatter.py`:

```python
def test_load_config_reads_markdown_tooling_version(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".project-standards.yml"
    cfg_path.write_text("markdown_tooling:\n  version: '1.0'\n", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.markdown_tooling_version == "1.0"


def test_load_config_markdown_tooling_defaults_none(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".project-standards.yml"
    cfg_path.write_text("markdown:\n  frontmatter:\n    required: true\n", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.markdown_tooling_version is None


def test_known_markdown_tooling_version_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc(MINIMAL), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n  frontmatter:\n    include: ['doc.md']\nmarkdown_tooling:\n  version: '1.0'\n",
    )
    rc = main(["--config", ".project-standards.yml"])
    out = capsys.readouterr()
    assert rc == 0
    assert out.out == "✓  1 file(s) validated\n"
    assert "markdown_tooling" not in out.out
    assert "markdown_tooling" not in out.err


def test_unknown_markdown_tooling_version_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_versioned_config(tmp_path, "markdown_tooling:\n  version: '9.9'\n")
    rc = main(["--config", ".project-standards.yml"])
    assert rc == 2
    assert "unknown markdown_tooling.version" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_validate_frontmatter.py -k markdown_tooling -v` Expected: FAIL — `AttributeError: 'ProjectConfig' object has no attribute 'markdown_tooling_version'` and the unknown-version test exits 0 instead of 2.

- [ ] **Step 3: Add the `ProjectConfig` field**

In `src/project_standards/validate_frontmatter.py`, add the parameter to `ProjectConfig.__init__` (after `python_tooling_version`) and store it:

```python
        python_tooling_version: str | None = None,
        markdown_tooling_version: str | None = None,
    ) -> None:
        self.schema = schema
        self.include = include
        self.exclude = exclude
        self.required = required
        self.require_adr_sections = require_adr_sections
        self.frontmatter_version = frontmatter_version
        self.adr_version = adr_version
        self.python_tooling_version = python_tooling_version
        self.markdown_tooling_version = markdown_tooling_version
```

- [ ] **Step 4: Parse it in `load_config`**

Add a local default near the other version locals:

```python
    python_tooling_version: str | None = None
    markdown_tooling_version: str | None = None
```

Add the parse block immediately after the existing `python_tooling` block:

```python
            python_tooling = raw_dict.get("python_tooling")
            if isinstance(python_tooling, dict):
                pt_dict = cast("dict[str, Any]", python_tooling)
                pt_version_val = pt_dict.get("version")
                python_tooling_version = str(pt_version_val) if pt_version_val is not None else None
            markdown_tooling = raw_dict.get("markdown_tooling")
            if isinstance(markdown_tooling, dict):
                mt_dict = cast("dict[str, Any]", markdown_tooling)
                mt_version_val = mt_dict.get("version")
                markdown_tooling_version = (
                    str(mt_version_val) if mt_version_val is not None else None
                )
```

Pass it into the returned `ProjectConfig`:

```python
        python_tooling_version=python_tooling_version,
        markdown_tooling_version=markdown_tooling_version,
    )
```

- [ ] **Step 5: Add the unknown-version guard in `main`**

Immediately after the existing `python_tooling.version` guard (the block ending in `return 2`), add:

```python
    # markdown_tooling.version is metadata only: validated if present, never emitted.
    if config.markdown_tooling_version is not None and not registry.is_known_markdown_tooling(
        config.markdown_tooling_version
    ):
        print(
            f"error: unknown markdown_tooling.version {config.markdown_tooling_version!r}",
            file=sys.stderr,
        )
        return 2
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validate_frontmatter.py -k markdown_tooling -v` Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add src/project_standards/validate_frontmatter.py tests/test_validate_frontmatter.py
git commit -m "feat(validator): validate markdown_tooling.version (exit 2 on unknown)"
```

---

## Task 3: Code gate green (no-version regression + full toolchain)

**Files:** none expected (verification; fix only if a check fails).

- [ ] **Step 1: Prove a no-`markdown_tooling` config is byte-identical**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: `✓  12 file(s) validated` (unchanged from before this work — this repo's config has no `markdown_tooling` key, so behaviour is identical).

- [ ] **Step 2: Run the full Python gate**

Run:

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

Expected: all pass; coverage ≥ 85% branch. If `ruff format --check` complains, run `uv run ruff format .` and re-run. If coverage dropped on the new branches, confirm Task 1/2 tests cover the unknown-version and registry-missing paths (they do) and re-run.

- [ ] **Step 3: Commit (only if Step 2 made fixups)**

```bash
git add -u src/ tests/
git commit -m "chore: keep gate green after markdown_tooling label"
```

If nothing changed, skip this commit.

---

## Task 4: Create the standard — `standards/markdown-tooling/README.md`

**Files:**

- Create: `standards/markdown-tooling/README.md`

This file is **source-backed** (decision 5). Write each section per the spec's §3 content notes; cite current official docs with `[S##]` markers resolved by a dated Source register. Before writing the prose, **recheck the live docs** listed in spec §6 and date every Source-register row `2026-06-07`. The configs below are embedded **verbatim from this repo** — do not paraphrase them.

- [ ] **Step 1: Write the frontmatter + body**

Start the file with this exact frontmatter (canonical key order; `validate-frontmatter` will enforce it):

```yaml
---
schema_version: '1.1'
id: 'markdown-tooling-standard'
title: 'Markdown Tooling Standard'
description: 'Recommended linting/formatting tools and settings for Markdown and adjacent structured-text files: markdownlint, Prettier, and EditorConfig.'
doc_type: 'reference'
status: 'active'
created: '2026-06-07'
updated: '2026-06-07'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'markdown'
  - 'linting'
  - 'formatting'
  - 'prettier'
  - 'markdownlint'
  - 'standard'
aliases:
  - 'markdown-tooling-standard'
related:
  - 'standards/markdown-frontmatter/README.md'
  - 'meta/versioning.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---
```

Then write the 18 sections from spec §3 (Evidence convention; Purpose & scope; Core contract; Standard stack; Published vs repo-local artifacts; Formatter — Prettier; Linter — markdownlint; Frontmatter coupling; `.editorconfig`; VS Code standard; CI reusable workflow; Agent instruction block; Non-default tools; Exceptions process; Update process; Source coverage map; Source register; Citation reference-link definitions). Use the embedded artifacts in the following steps verbatim.

- [ ] **Step 2: Embed the core contract (section "Core contract") exactly**

````markdown
Check (non-mutating):

```bash
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Fix (mutating):

```bash
npx prettier --write .
npx markdownlint-cli2 --fix "**/*.md"
```

`prettier .` formats every file type Prettier supports that it finds (respecting `.gitignore`/`.prettierignore`) — the coverage is "whatever Prettier supports," not a fixed extension list, so the command cannot diverge from the coverage statement; in this repo it resolves to `md`/`json`/`jsonc`/`yaml`. markdownlint is Markdown-only. Pin versions: pin Prettier in `package.json` (or `npx prettier@<v>`) and the markdownlint action `@v23` in CI.
````

- [ ] **Step 3: Embed the 13 markdownlint deviations (section "Linter — markdownlint") exactly**

These are the 13 deliberate deviations from markdownlint v0.40.0 defaults (the rest of `.markdownlint.json` states every other rule at its default for determinism). Render as a table with the rationale column:

````text
MD003 {style: atx}        — align headings to Prettier (ATX)
MD004 {style: dash}       — align bullets to Prettier (-)
MD009 false               — Prettier owns trailing whitespace
MD010 false               — Prettier owns hard tabs
MD013 false               — Prettier owns line length (proseWrap: never)
MD024 false               — MADR 4.0 allows duplicate option headings
MD025 {front_matter_title: "", level: 1}  — frontmatter title is not an H1
MD029 false               — ordered-list prefix style not enforced
MD030 false               — Prettier owns list-marker spacing
MD032 false               — Prettier owns blanks around lists
MD048 {style: backtick}   — align fences to Prettier (```)
MD049 {style: underscore} — align emphasis to Prettier (_italic_)
MD050 {style: asterisk}   — align strong to Prettier (**bold**)
````

Add the **MD043 sentinel trap** note: the config sets `MD043: true` (inert). Stated as `MD043: { headings: [] }` it would mean "require exactly zero headings" and flag every heading; `true` is the correct inert form. This is guarded by `tests/test_markdownlint_config.py`.

State that `.markdownlint.json` is **fully explicit** (`default: true` plus all ~53 rules) so a consumer seeding it gets deterministic linting and any rule a future markdownlint version adds lands at its default rather than silently off.

- [ ] **Step 4: Embed the Prettier settings (section "Formatter — Prettier") exactly**

Document these `.prettierrc.json` values and why each matters:

```text
printWidth: 88
useTabs: true, tabWidth: 2
endOfLine: lf
semi: false, singleQuote: false, trailingComma: es5
proseWrap: never        — the linchpin: lets markdownlint MD013 stay off; the two tools don't fight
overrides:
  *.md   -> { singleQuote: true }
  *.jsonc -> { trailingComma: none }
```

Add the DEC-9 note: this config is a **copy-adopt scaffold**, not a shipped/enforced artifact — Prettier ships no reusable workflow (contrast the markdownlint rule set).

- [ ] **Step 5: Embed the EditorConfig note, VS Code section, CI snippet, and agent block exactly**

`.editorconfig` (section "`.editorconfig`"): note `[*.md] trim_trailing_whitespace = false` — two trailing spaces are a Markdown hard line break Prettier preserves; stripping them would make editor and Prettier disagree on save.

VS Code (section "VS Code standard"): recommend the two extensions and state the one-formatter-authority rule (Prettier formats on save; markdownlint **only diagnoses** — no markdownlint fix-on-save code action):

```json
{ "recommendations": ["esbenp.prettier-vscode", "DavidAnson.vscode-markdownlint"] }
```

```json
{
	"[markdown]": {
		"editor.defaultFormatter": "esbenp.prettier-vscode",
		"editor.formatOnSave": true
	}
}
```

CI reusable workflow (section "CI reusable workflow") — consumer opt-in snippet, pinned `@v2`:

```yaml
jobs:
  lint-markdown:
    uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v2
    with:
      globs: '**/*.md'
```

Note the `workflow_call` inputs (`globs`, `config`) and the DEC-8 separation from `validate-markdown-frontmatter.yml` (frontmatter-only consumers never inherit Node). Note Prettier ships no reusable workflow (DEC-9) — a consumer wanting Prettier CI wires their own.

Agent instruction block (section "Agent instruction block") — embed verbatim:

````markdown
# Markdown Tooling — Agent Instructions

## Fix pass (mutating)

```bash
npx prettier --write .
npx markdownlint-cli2 --fix "**/*.md"
```

## Verification (non-mutating)

```bash
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

## Rules

- Prettier owns formatting for every file type it supports; do not fight its output.
- markdownlint owns Markdown structure; fix violations rather than disabling rules.
- Do not add a second Markdown formatter or a second language server.
- markdownlint is diagnostics-only in the editor; Prettier formats on save.
````

- [ ] **Step 6: Write the remaining sections + Source register**

- **Frontmatter coupling:** `MD025`/`MD041`/`MD001` key off `front_matter_title`; this repo's model is frontmatter `title:` + body `# H1`, so MD025 uses the DavidAnson `""`-disable model while MD041/MD001 use the `title:` regex. PyMarkdown was rejected (DEC-3): it cannot read `.markdownlint.json` and models MD025 as a key-name that forces all headings to ≥ H2. Link to `standards/markdown-frontmatter/README.md`.
- **Non-default tools:** PyMarkdown, remark-lint, dprint, mdformat, Vale — one line each; per-project add-prohibition, not a workstation uninstall order.
- **Exceptions process:** ADR-based; point to `standards/adr/README.md`.
- **Source coverage map** + **Source register**: one dated row per `[S##]` used (live-checked 2026-06-07; sources from spec §6: Prettier options/config, markdownlint Rules, markdownlint-cli2, markdownlint-cli2-action, EditorConfig, the two VS Code extensions, MADR 4.0 `.markdownlint.yml`). End with the `[S01]: #NN-source-register` citation-link-definition block (GFM cannot anchor table rows).

- [ ] **Step 7: Validate, lint, format**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "standards/markdown-tooling/README.md"
npx prettier --check "standards/markdown-tooling/README.md"
```

Expected: validate-frontmatter now reports `✓  13 file(s) validated`; markdownlint `0 error(s)`; Prettier clean. If Prettier reports issues, run `npx prettier --write "standards/markdown-tooling/README.md"`.

- [ ] **Step 8: Commit**

```bash
git add standards/markdown-tooling/README.md
git commit -m "docs(markdown-tooling): add the Markdown Tooling Standard"
```

---

## Task 5: Create the adoption runbook — `standards/markdown-tooling/adopt.md`

**Files:**

- Create: `standards/markdown-tooling/adopt.md`

- [ ] **Step 1: Write the file**

Frontmatter (exact):

```yaml
---
schema_version: '1.1'
id: 'markdown-tooling-adoption'
title: 'Adopt the Markdown Tooling Standard'
description: 'How to adopt the Markdown Tooling Standard: seed the markdownlint rule set and EditorConfig, copy the Prettier config, and wire the reusable lint workflow.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-07'
updated: '2026-06-07'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - 'adoption'
  - 'markdown'
  - 'linting'
  - 'formatting'
aliases: []
related:
  - 'standards/markdown-tooling/README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---
```

Body — the runbook steps (from spec §4):

````markdown
# Adopt the Markdown Tooling Standard

The **linter** half ships a reusable workflow and a seedable rule set; the **formatter** half (Prettier) is copy-adopt with no workflow. The contract version is a validated label, not a body gate.

## Steps

1. **Seed the rule set + floor.** Copy `.markdownlint.json` (the markdownlint rule set) and `.editorconfig` from this repo.
2. **Copy the formatter config (optional).** Copy `.prettierrc.json`; pin Prettier via a minimal `package.json` devDep or run `npx prettier@<version>`.
3. **Wire the reusable linter.** Add a job calling the workflow:

   ```yaml
   jobs:
     lint-markdown:
       uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v2
       with:
         globs: '**/*.md'
   ```

4. **Add the VS Code recommendations:** `esbenp.prettier-vscode` + `DavidAnson.vscode-markdownlint`.
5. **Select the contract version (optional)** in `.project-standards.yml`:

   ```yaml
   markdown_tooling:
     version: '1.0'
   ```

   This is validated-if-present metadata only — it runs no check by itself; the markdownlint workflow is the enforcement.

6. **Run the check contract** (standard "Core contract") to confirm clean.
7. **Need an exception?** Record an ADR; see the [ADR Standard](../adr/README.md).
````

- [ ] **Step 2: Validate, lint, format**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "standards/markdown-tooling/adopt.md"
npx prettier --check "standards/markdown-tooling/adopt.md"
```

Expected: validate-frontmatter `✓  14 file(s) validated`; markdownlint `0 error(s)`; Prettier clean.

- [ ] **Step 3: Commit**

```bash
git add standards/markdown-tooling/adopt.md
git commit -m "docs(markdown-tooling): add adoption runbook"
```

---

## Task 6: Cross-link from the Frontmatter standard (the TODO's core ask)

**Files:**

- Modify: `standards/markdown-frontmatter/README.md:20-22` (frontmatter `related:`) and the "Versioning and compatibility" prose area.

- [ ] **Step 1: Add the `related:` entry**

In the frontmatter block of `standards/markdown-frontmatter/README.md`, change:

```yaml
related:
  - 'src/project_standards/schemas/markdown-frontmatter.schema.json'
  - 'meta/versioning.md'
```

to:

```yaml
related:
  - 'src/project_standards/schemas/markdown-frontmatter.schema.json'
  - 'meta/versioning.md'
  - 'standards/markdown-tooling/README.md'
```

- [ ] **Step 2: Add an in-body cross-link**

Immediately after the "Files that never carry frontmatter" subsection (the paragraph ending "…render a frontmatter table on its landing page."), add a new paragraph:

```markdown
This standard is deliberately tool-neutral about the Markdown _body_. How a document's body and adjacent config files are formatted and linted (Prettier, markdownlint, EditorConfig) is governed by the companion [Markdown Tooling Standard](../markdown-tooling/README.md).
```

- [ ] **Step 3: Validate, lint, format**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "standards/markdown-frontmatter/README.md"
npx prettier --check "standards/markdown-frontmatter/README.md"
```

Expected: all clean (`✓  14 file(s) validated`).

- [ ] **Step 4: Commit**

```bash
git add standards/markdown-frontmatter/README.md
git commit -m "docs(markdown-frontmatter): link to the Markdown Tooling Standard"
```

---

## Task 7: Register in the navigation maps (`standards/README.md` + root `README.md`)

**Files:**

- Modify: `standards/README.md:5-9` (index table)
- Modify: `README.md:16` (layout tree), `:49-54` (Standards section), `:74-76` (Consuming section)

- [ ] **Step 1: Add the standards-index row**

In `standards/README.md`, change the table body:

```markdown
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) | | ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) | | Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |
```

to add a fourth row:

```markdown
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) | | ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) | | Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) | | Markdown Tooling | Markdown/structured-text linting + formatting (markdownlint, Prettier, EditorConfig) | [markdown-tooling/](markdown-tooling/) | [adopt](markdown-tooling/adopt.md) |
```

- [ ] **Step 2: Add the bundle to the root README layout tree**

In `README.md`, change the line:

```text
│   └── python-tooling/        #   standard + adopt (doc-only)
```

to:

```text
│   ├── python-tooling/        #   standard + adopt (doc-only)
│   └── markdown-tooling/      #   standard + adopt (doc-only)
```

- [ ] **Step 3: Add the root README Standards subsection**

After the "Python Tooling SSOT Standard" subsection (ending at the `adopt.md` bullet, before `## Consuming the standards`), add:

```markdown
### Markdown Tooling Standard

The recommended linting/formatting tools and settings for Markdown and the structured-text files Prettier handles (`json`/`jsonc`/`yaml`): **markdownlint** for Markdown structure, **Prettier** for formatting, and **EditorConfig** as the floor. The tool-specific complement to the tool-neutral Frontmatter standard; markdownlint ships a reusable workflow + seedable rule set, while Prettier is copy-adopt (no workflow).

- **Standard:** [`standards/markdown-tooling/README.md`](standards/markdown-tooling/README.md)
- **Adopt:** [`adopt.md`](standards/markdown-tooling/adopt.md)
```

- [ ] **Step 4: Add the root README Consuming subsection**

After the "Python Tooling SSOT" consuming subsection (ending "…run the verification gate. See [...]."), before "### Pin to a release tag, not `main`", add:

```markdown
### Markdown Tooling

Seed `.markdownlint.json` + `.editorconfig`, copy `.prettierrc.json`, and opt into the reusable `lint-markdown.yml@v2` workflow. See [`standards/markdown-tooling/adopt.md`](standards/markdown-tooling/adopt.md).
```

- [ ] **Step 5: Lint + format (root README is excluded from frontmatter validation)**

Run:

```bash
npx markdownlint-cli2 "README.md" "standards/README.md"
npx prettier --check "README.md" "standards/README.md"
```

Expected: `0 error(s)` and Prettier clean. (Both files are excluded from `validate-frontmatter` by `.project-standards.yml`, so no frontmatter check applies.)

- [ ] **Step 6: Commit**

```bash
git add README.md standards/README.md
git commit -m "docs: register Markdown Tooling Standard in the navigation maps"
```

---

## Task 8: Document the contract version in `meta/versioning.md`

**Files:**

- Modify: `meta/versioning.md:56-60` (per-standard table), `:81-88` (change-classification table)

- [ ] **Step 1: Add the per-standard contract-version row**

In the "Per-standard contract versions" table, after the Python Tooling row, add:

```markdown
| Markdown Tooling | `1.0` | `markdown_tooling.version` (optional) | no — copy-adopted label, metadata only |
```

- [ ] **Step 2: Note Markdown Tooling in the change-classification table**

The existing "Python Tooling standard (copy-adopted)" row and the "Bundled contract set" row already cover the copy-adopted + bundled-version semantics. Update the **Python Tooling standard** row label to cover both copy-adopted standards by changing its first cell:

```markdown
| **Python Tooling standard** (copy-adopted) |
```

to:

```markdown
| **Python / Markdown Tooling standards** (copy-adopted) |
```

(The cell contents — MAJOR/MINOR/PATCH descriptions of raising a tool floor, adding an optional scaffold/tool, and editorial revisions — apply unchanged to both.)

- [ ] **Step 3: Lint + format + validate (`meta/**` is frontmatter-validated)\*\*

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "meta/versioning.md"
npx prettier --check "meta/versioning.md"
```

Expected: all clean.

- [ ] **Step 4: Commit**

```bash
git add meta/versioning.md
git commit -m "docs(versioning): record the markdown_tooling contract version"
```

---

## Task 9: Config fixes (`lint-markdown.yml` tag + VS Code dogfood)

**Files:**

- Modify: `.github/workflows/lint-markdown.yml:30`
- Modify: `.vscode/settings.json:16`

- [ ] **Step 1: Fix the stale `@v1` example comment**

In `.github/workflows/lint-markdown.yml`, change line 30:

```text
  #       uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v1
```

to:

```text
  #       uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v2
```

(This workflow first ships in `2.0.0`; per the per-major moving-tag convention a consumer pins `@v2`, never `@v1`.)

- [ ] **Step 2: Dogfood Markdown format-on-save (Prettier only)**

In `.vscode/settings.json`, change:

```json
	"[markdown]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
```

to:

```json
	"[markdown]": {
		"editor.defaultFormatter": "esbenp.prettier-vscode",
		"editor.formatOnSave": true
	},
```

Do **not** add a markdownlint code action — markdownlint stays diagnostics-only, preserving one-formatter-authority (SA-NEW-001).

- [ ] **Step 3: Format-check the edited files**

Run: `npx prettier --check ".vscode/settings.json" ".github/workflows/lint-markdown.yml"` Expected: clean. If not, run `npx prettier --write` on the reported file. (`.vscode/` and `.github/` are outside `validate-frontmatter`'s include and markdownlint's `*.md` glob, so only Prettier applies.)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/lint-markdown.yml .vscode/settings.json
git commit -m "fix(ci,vscode): pin lint-markdown example @v2; dogfood Markdown format-on-save"
```

---

## Task 10: CHANGELOG entry

**Files:**

- Modify: `CHANGELOG.md:36` (end of `[Unreleased] / Added`)

- [ ] **Step 1: Add the entry**

After the "Per-standard contract versions." bullet in `## [Unreleased] / ### Added`, add:

```markdown
- **Markdown Tooling Standard (`standards/markdown-tooling/`).** A new governed bundle documenting the recommended linting/formatting tools and settings for Markdown and the structured-text files Prettier handles: **markdownlint** (the seedable `.markdownlint.json` rule set + the reusable `lint-markdown.yml@v2` workflow), **Prettier** (copy-adopt formatter config; no reusable workflow, DEC-9), and **EditorConfig**. Source-backed, parallel to the Python Tooling standard, and cross-linked from the tool-neutral Frontmatter standard. Adds a validated `markdown_tooling` contract version (`1.0`) to `registry.json`, recognized by the validator (`markdown_tooling.version`; unknown values exit 2) like `python_tooling.version`. Additive — MINOR.
```

Also bump the frontmatter `updated:` field from `'2026-06-06'` to `'2026-06-07'`.

- [ ] **Step 2: Validate, lint, format**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "CHANGELOG.md"
npx prettier --check "CHANGELOG.md"
```

Expected: all clean (`CHANGELOG.md` is in the validator include).

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record the Markdown Tooling Standard"
```

---

## Task 11: Handoff bookkeeping

**Files:**

- Modify: `docs/handoff/specs-plans.md` (table), `docs/handoff/architecture.md:9` + `:3`, `docs/handoff/state.md` (bullets + Last updated)

These files are under `docs/handoff/**`, which `.project-standards.yml` excludes from frontmatter validation — but they are still linted by markdownlint and formatted by Prettier.

- [ ] **Step 1: Add specs-plans rows**

In `docs/handoff/specs-plans.md`, add two rows to the table:

```markdown
| Markdown Tooling Standard design | `docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md` | approved (audit r3) | | Markdown Tooling Standard plan | `docs/superpowers/plans/2026-06-07-markdown-tooling-standard.md` | in progress |
```

Update its `**Last updated:**` line to `2026-06-07`.

- [ ] **Step 2: Update architecture.md**

In `docs/handoff/architecture.md`, change the `standards/` component line:

```text
├── standards/          -> governing standards, one bundle each (markdown-frontmatter, adr, python-tooling) + README index
```

to:

```text
├── standards/          -> governing standards, one bundle each (markdown-frontmatter, adr, python-tooling, markdown-tooling) + README index
```

Update `**Last updated:**` to `2026-06-07`.

- [ ] **Step 3: Update state.md**

In `docs/handoff/state.md`, update `**Last updated:**` to `2026-06-07` and add a bullet under "State at a glance":

```markdown
- **Markdown Tooling Standard** added on `testing` 2026-06-07: new `standards/markdown-tooling/` bundle (markdownlint + Prettier + EditorConfig), validated `markdown_tooling` contract version `1.0`, cross-linked from the Frontmatter standard. Spec+plan in `docs/superpowers/`. Rides the locked `2.0.0`.
```

Keep the file ≤ 2048 bytes — if it would exceed, trim the oldest at-a-glance bullet into `sessions/`.

- [ ] **Step 4: Lint + format**

Run:

```bash
npx markdownlint-cli2 "docs/handoff/specs-plans.md" "docs/handoff/architecture.md" "docs/handoff/state.md"
npx prettier --check "docs/handoff/specs-plans.md" "docs/handoff/architecture.md" "docs/handoff/state.md"
```

Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add docs/handoff/specs-plans.md docs/handoff/architecture.md docs/handoff/state.md
git commit -m "docs(handoff): record the Markdown Tooling Standard"
```

---

## Task 12: Final verification — full gate + acceptance-criteria sweep

**Files:** none expected.

- [ ] **Step 1: Run the complete repo gate**

Run:

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
uv run validate-frontmatter --config .project-standards.yml
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Expected: every command passes; `validate-frontmatter` reports `✓  14 file(s) validated`; markdownlint `0 error(s)`; Prettier clean.

- [ ] **Step 2: Verify the acceptance criteria (spec §8)**

Confirm each:

```bash
# Validated label: known passes, unknown exits 2, no-key unchanged
printf 'markdown_tooling:\n  version: "1.0"\n' > /tmp/ok.yml && uv run validate-frontmatter --config /tmp/ok.yml; echo "exit=$?"
printf 'markdown_tooling:\n  version: "9.9"\n' > /tmp/bad.yml && uv run validate-frontmatter --config /tmp/bad.yml; echo "exit=$? (expect 2 + 'unknown markdown_tooling.version')"
# Release pins: no @v1 left in the markdown-tooling docs or the workflow example
grep -rn "lint-markdown.yml@v1" standards/markdown-tooling/ .github/workflows/lint-markdown.yml README.md || echo "no stale @v1 — good"
```

Expected: `ok.yml` → `exit=0`; `bad.yml` → `exit=2` with the unknown-version message; the grep prints "no stale @v1 — good".

- [ ] **Step 3: Confirm the working tree is clean and review the branch delta**

Run: `git status --short && git log --oneline main..testing | head -20` Expected: clean tree (only the user's untracked `TODO.md` may remain); the new commits present.

- [ ] **Step 4: Finishing the branch**

REQUIRED SUB-SKILL: invoke `superpowers:finishing-a-development-branch` to decide integration (this repo is single-developer; the likely path is fast-forwarding `testing` per the deferred release ritual — do not run the release ritual here unless asked).

---

## Self-review

**Spec coverage** (spec §7 touchpoints → task):

- README.md (standard) → Task 4; adopt.md → Task 5.
- registry.json / registry.py / validate_frontmatter.py / tests → Tasks 1–2.
- meta/versioning.md → Task 8; standards/README.md + root README.md → Task 7; frontmatter cross-link → Task 6.
- lint-markdown.yml + .vscode/settings.json → Task 9.
- CHANGELOG.md → Task 10; specs-plans/state/architecture → Task 11.
- Acceptance criteria (spec §8) → Task 12. Gate-green → Tasks 3 + 12. No touchpoint is unaddressed.

**Placeholder scan:** the two NEW prose docs (Task 4 README, Task 5 adopt) embed every config/snippet verbatim and reference spec §3/§4 for section content; the only non-verbatim work is the source-backed prose + the live source recheck, which is defined, bounded, and gated by validate-frontmatter + markdownlint + Prettier. No "TBD"/"handle errors"/"similar to" placeholders elsewhere.

**Type/name consistency:** `markdown_tooling_default` / `markdown_tooling_versions` / `is_known_markdown_tooling` (registry.py) and `markdown_tooling_version` (ProjectConfig) are used identically across Tasks 1–2 and the tests; the registry key `markdown_tooling`, the config key `markdown_tooling.version`, and the contract version `1.0` match the spec and `registry.json`. The two direct `Registry(...)` test constructions are updated in Task 1, the same task that makes the params required.
