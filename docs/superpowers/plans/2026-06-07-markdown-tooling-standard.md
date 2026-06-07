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
- `tests/test_validate_frontmatter.py` — new tests; fix the two direct `Registry(...)` constructions and the parametrized malformed-registry fixtures.
- `.project-standards.yml` — select `python_tooling` + `markdown_tooling` contract versions (dogfood every standard the repo defines).

Modified — docs/navigation:

- `standards/markdown-frontmatter/README.md` — `related:` entry + in-body cross-link.
- `standards/markdown-frontmatter/adopt.md` — fix stale `lint-markdown.yml@v1` → `@v2` (two refs).
- `standards/README.md` — index-table row.
- `README.md` (root) — Standards section + Consuming section.
- `meta/versioning.md` — per-standard contract-version row + change-classification row.

Modified — config + bookkeeping:

- `.github/workflows/lint-markdown.yml` — example-comment `@v1` → `@v2`.
- `.vscode/settings.json` — `[markdown]` gains `editor.formatOnSave` (Prettier; no markdownlint code action).
- `CHANGELOG.md` — `[Unreleased] / Added` entry.
- `docs/handoff/specs-plans.md`, `docs/handoff/state.md`, `docs/handoff/architecture.md` — session bookkeeping.
- `AGENTS.md`, `CLAUDE.md` — refresh the stale repo-purpose line (prose only; these files never carry frontmatter).

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

- [ ] **Step 6: Update the parametrized malformed-registry fixtures**

`load_registry` now requires a `markdown_tooling` object and checks it **first**, so every existing payload in `test_load_registry_malformed_raises` (`tests/test_validate_frontmatter.py` ≈ lines 452-484) that targets a _later_ branch (non-string default, `frontmatter.versions`, `adr.versions`, `python_tooling.versions`) would otherwise raise the new missing-object error before reaching its intended branch. Fix every payload **except** the first (the dedicated `{"frontmatter": {}, "adr": {}}` missing-object case, whose `"missing frontmatter/adr/python_tooling"` match is still a substring of the new message): insert a valid `markdown_tooling` object into each. Concretely, in payloads 2 through 8, add this immediately before the payload's closing `}`:

```text
, "markdown_tooling": {"default": "1.0", "versions": ["1.0"]}
```

Then add one new parametrized case (so the `markdown_tooling.versions` branch is itself covered) to the `parametrize` list:

```python
        (
            '{"frontmatter": {"default": "1.1", "versions": {"1.1": "markdown-frontmatter"}}, "adr": {"default": "1.0", "versions": {"1.0": {"supports_frontmatter": ["1.1"]}}}, "python_tooling": {"default": "1.0", "versions": ["1.0"]}, "markdown_tooling": {"default": "1.0", "versions": {}}}',
            "markdown_tooling.versions is not a list",
        ),
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validate_frontmatter.py -q` Expected: PASS (all tests, including the two new registry tests, the new malformed case, and the two edited constructions). If any malformed case now fails with the missing-`markdown_tooling` message, a payload was missed in Step 6 — add the object to it.

- [ ] **Step 8: Commit**

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

Run: `uv run pytest tests/test_validate_frontmatter.py -k "markdown_tooling and not registry" -v` Expected: 4 selected; FAIL — `AttributeError: 'ProjectConfig' object has no attribute 'markdown_tooling_version'` and the unknown-version test exits 0 instead of 2. (The `and not registry` filter excludes the two Task 1 registry tests, which already pass.)

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

Run: `uv run pytest tests/test_validate_frontmatter.py -k "markdown_tooling and not registry" -v` Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add src/project_standards/validate_frontmatter.py tests/test_validate_frontmatter.py
git commit -m "feat(validator): validate markdown_tooling.version (exit 2 on unknown)"
```

---

## Task 3: Dogfood every standard's contract version + code gate green

This repo defines four standards; per the dogfood directive it now **selects** a contract version for every one of them in its own `.project-standards.yml`. Today the file selects only `markdown.frontmatter.version` and `markdown.adr.version`; `python_tooling` was never selected here. This task closes that gap (adding both `python_tooling` and `markdown_tooling`) so the validated-label path runs against this repo on every CI run.

**Files:**

- Modify: `.project-standards.yml`

- [ ] **Step 1: Prove a no-`markdown_tooling` config is byte-identical (regression)**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: `✓  12 file(s) validated` (unchanged — at this point the config has no `markdown_tooling`/`python_tooling` keys, so behaviour is identical to before this work; the version keys are added in Step 2).

- [ ] **Step 2: Select all four contract versions (dogfood)**

In `.project-standards.yml`, the `markdown.frontmatter.version: "1.1"` and `markdown.adr.version: "1.0"` keys already exist. Add two **top-level** blocks (siblings of `markdown:`, not nested under it — `load_config` reads `python_tooling`/`markdown_tooling` at the document root) at the end of the file:

```yaml
# Contract-version selections for the copy-adopted standards this repo defines.
# Both are validated-if-present metadata only (a known version => no output, no
# behaviour change; an unknown version => exit 2). Selected here to dogfood every
# standard the repo ships. python_tooling enforcement is the verification gate;
# markdown_tooling enforcement is the lint-markdown workflow.
python_tooling:
  version: '1.0'

markdown_tooling:
  version: '1.0'
```

- [ ] **Step 3: Verify the dogfooded config still validates**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: `✓  12 file(s) validated` — the same file count (version keys add no managed files), now with both labels validated as known versions on every run. No `python_tooling`/`markdown_tooling` text appears in stdout/stderr.

- [ ] **Step 4: Run the full Python gate**

Run:

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

Expected: all pass; coverage ≥ 85% branch. If `ruff format --check` complains, run `uv run ruff format .` and re-run. If coverage dropped on the new branches, confirm Task 1/2 tests cover the unknown-version and registry-missing paths (they do) and re-run.

- [ ] **Step 5: Commit**

```bash
git add .project-standards.yml
git commit -m "chore: dogfood python_tooling + markdown_tooling contract versions"
```

If Step 4 also made `src/`/`tests/` fixups, stage and commit those too with a separate `chore: keep gate green` message.

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

- Modify: `standards/markdown-frontmatter/README.md:20-22` (frontmatter `related:`) and the "Files that never carry frontmatter" prose area.
- Modify: `standards/markdown-frontmatter/adopt.md:132,137` (stale `lint-markdown.yml@v1` → `@v2`).

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

- [ ] **Step 3: Fix the stale lint-markdown `@v1` in the Frontmatter adopt guide**

`standards/markdown-frontmatter/adopt.md` is a governed consumer-facing doc that still pins the new lint workflow at the wrong major tag (it first ships in `2.0.0`). Change both occurrences of `lint-markdown.yml@v1` to `lint-markdown.yml@v2`:

- ≈ line 132 — the `uses:` line in the `lint-markdown` job snippet.
- ≈ line 137 — the prose "your only pin is `lint-markdown.yml@v1`".

Leave every `validate-markdown-frontmatter.yml@v1` reference in this file unchanged — that workflow genuinely shipped in v1.x; only the `lint-markdown.yml` pins are wrong.

- [ ] **Step 4: Validate, lint, format**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "standards/markdown-frontmatter/README.md" "standards/markdown-frontmatter/adopt.md"
npx prettier --check "standards/markdown-frontmatter/README.md" "standards/markdown-frontmatter/adopt.md"
```

Expected: all clean (`✓  14 file(s) validated`).

- [ ] **Step 5: Commit**

```bash
git add standards/markdown-frontmatter/README.md standards/markdown-frontmatter/adopt.md
git commit -m "docs(markdown-frontmatter): link to Markdown Tooling Standard; fix stale lint-markdown @v1"
```

---

## Task 7: Register in the navigation maps (`standards/README.md` + root `README.md`)

**Files:**

- Modify: `standards/README.md:5-9` (index table)
- Modify: `README.md:16` (layout tree), `:49-54` (Standards section), `:74-76` (Consuming section)

- [ ] **Step 1: Add the standards-index row**

`standards/README.md` has a four-column index table (`| Standard | What it governs | Bundle | Adopt |`) with three body rows (Markdown Frontmatter, ADR, Python Tooling SSOT). Add a fourth body row immediately after the Python Tooling SSOT row — keep it on **one physical line** (shown here in a plain block so it is copied verbatim, one row, four cells):

```text
| Markdown Tooling | Markdown/structured-text linting + formatting (markdownlint, Prettier, EditorConfig) | [markdown-tooling/](markdown-tooling/) | [adopt](markdown-tooling/adopt.md) |
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

- [ ] **Step 5: Fix the stale "two Markdown standards" prose**

The Consuming intro (`README.md` ≈ line 58) currently reads "The two **Markdown standards** share one mechanism; **Python Tooling** adopts on its own." That undercounts now. Change that sentence to:

```text
The two **Markdown frontmatter standards** (Frontmatter + ADR) share one mechanism; **Python Tooling** and **Markdown Tooling** each adopt on their own.
```

(The existing `### Markdown standards (Frontmatter + ADR)` consuming heading stays — it still names exactly the two that share the validate-frontmatter workflow.)

- [ ] **Step 6: Lint + format (root README is excluded from frontmatter validation)**

Run:

```bash
npx markdownlint-cli2 "README.md" "standards/README.md"
npx prettier --check "README.md" "standards/README.md"
```

Expected: `0 error(s)` and Prettier clean. (Both files are excluded from `validate-frontmatter` by `.project-standards.yml`, so no frontmatter check applies.)

- [ ] **Step 7: Commit**

```bash
git add README.md standards/README.md
git commit -m "docs: register Markdown Tooling Standard in the navigation maps"
```

---

## Task 8: Document the contract version in `meta/versioning.md`

**Files:**

- Modify: `meta/versioning.md` — per-standard table (≈ line 60), change-classification table (≈ line 86), and the stale prose at ≈ lines 33, 35, 70-73.

- [ ] **Step 1: Add the per-standard contract-version row**

In the "Per-standard contract versions" table, immediately after the Python Tooling row, add this one physical row (four cells; shown in a plain block so it copies verbatim):

```text
| Markdown Tooling | `1.0` | `markdown_tooling.version` (optional) | no — copy-adopted label, metadata only |
```

- [ ] **Step 2: Relabel the change-classification row to cover both copy-adopted standards**

In the change-classification table, the row whose first cell is `| **Python Tooling standard** (copy-adopted) |` — change only that first cell to:

```text
| **Python / Markdown Tooling standards** (copy-adopted) |
```

(The MAJOR/MINOR/PATCH cell contents apply unchanged to both.)

- [ ] **Step 3: Fix the stale standard-count prose**

The doc still says "three standards" and "two Markdown standards". Make three replacements:

a. In the "ships **several components under one version number**" paragraph, change `three standards — the [Markdown Frontmatter](../standards/markdown-frontmatter/README.md), [ADR](../standards/adr/README.md), and [Python Tooling SSOT](../standards/python-tooling/README.md) standards —` to:

```text
four standards — the [Markdown Frontmatter](../standards/markdown-frontmatter/README.md), [ADR](../standards/adr/README.md), [Python Tooling SSOT](../standards/python-tooling/README.md), and [Markdown Tooling](../standards/markdown-tooling/README.md) standards —
```

b. Replace the "enforced automatically / copy-adopted / All three" sentence pair with:

```text
The two Markdown frontmatter standards (Frontmatter and ADR) are **enforced automatically**: a consumer pins the workflow and the validator checks its documents on every run. The Python Tooling and Markdown Tooling standards are **copy-adopted** — a consumer copies their scaffolds (and, for Markdown Tooling, optionally opts into the `lint-markdown.yml` workflow), so they are never inherited automatically and a change to them cannot newly-fail a consumer on its own. All four still ship under the same release tag.
```

c. In the "Component-level version markers" section, change `Two **component-level markers** version individual pieces of the repository and are deliberately **decoupled** from the release version — neither is itself a release number:` to start with `Three` and `none is itself a release number:`, then add a third bullet after the Python Tooling contract-version bullet:

```text
- The **Markdown Tooling contract version** — the `1.0` label in the [Markdown Tooling standard](../standards/markdown-tooling/README.md) — is a copy-adopted label like the Python Tooling one: validated as a known version when selected, but it does not enforce the standard's body rules (the `lint-markdown.yml` workflow does) and is not a release version.
```

- [ ] **Step 4: Lint, format, validate (`meta/` is frontmatter-validated)**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "meta/versioning.md"
npx prettier --check "meta/versioning.md"
```

Expected: all clean.

- [ ] **Step 5: Commit**

```bash
git add meta/versioning.md
git commit -m "docs(versioning): record markdown_tooling + refresh standard counts"
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

- [ ] **Step 2: Fix the stale `@v1` in the existing Stack B bullet**

The existing `[Unreleased]` "Opt-in Markdown body linting (Stack B)" bullet still references the old major tag twice — in the `uses:` example and in the trailing "Additive — pin" note. That workflow first ships in `2.0.0`, so in **that bullet only**, change both occurrences of `@v1` to `@v2`. Do **not** touch the other `@v1` references in older released sections — they document the frontmatter workflow and `standards-ref`, which genuinely shipped in v1.x.

- [ ] **Step 3: Validate, lint, format**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx markdownlint-cli2 "CHANGELOG.md"
npx prettier --check "CHANGELOG.md"
```

Expected: all clean (`CHANGELOG.md` is in the validator include).

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record the Markdown Tooling Standard; fix stale lint-markdown @v1"
```

---

## Task 11: Handoff bookkeeping

**Files:**

- Modify: `docs/handoff/specs-plans.md` (table), `docs/handoff/architecture.md:9` + `:3`, `docs/handoff/state.md` (bullets + Last updated)

These files are under `docs/handoff/**`, which `.project-standards.yml` excludes from frontmatter validation — but they are still linted by markdownlint and formatted by Prettier.

- [ ] **Step 1: Add specs-plans rows**

In `docs/handoff/specs-plans.md`, add two table rows (each on its **own physical line**, three cells; shown in a plain block so they copy verbatim as two separate rows):

```text
| Markdown Tooling Standard design | `docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md` | approved (audit r3) |
| Markdown Tooling Standard plan | `docs/superpowers/plans/2026-06-07-markdown-tooling-standard.md` | in progress |
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

- [ ] **Step 4: Refresh the agent-facing repo-purpose lines**

`AGENTS.md` and `CLAUDE.md` are loaded early in every session and currently undercount **and** mis-describe the standards (both say "enforces the Markdown ones with a Python validator" — but Markdown Tooling is **not** validator-enforced: its body rules are markdownlint/Prettier and only its metadata label is validator-recognized). Edit prose only — these files **never** carry frontmatter. Distinguish the three enforcement mechanisms: validator-enforced (Frontmatter, ADR), copy-adopt + optional `lint-markdown.yml` (Markdown Tooling), copy-adopt scaffolds (Python Tooling).

In `AGENTS.md` (≈ line 11), replace the entire `This repository is the **single source of truth** … See [README.md](README.md) for the full surface.` paragraph with:

```text
This repository is the **single source of truth** for reusable standards shared across projects. It _defines_ four standards: **Markdown Frontmatter** and **ADR** (enforced by a Python validator that downstream repos run via a reusable CI workflow), **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig scaffolds plus an optional reusable `lint-markdown.yml`), and **Python Tooling SSOT** (copy-adopt scaffolds). Other repositories _consume_ them by config + workflow (the validator-enforced ones) or by copying scaffolds (the copy-adopt ones), rather than vendoring copies. See [README.md](README.md) for the full surface.
```

In `CLAUDE.md` (≈ line 5), the purpose line is stale (it reads "the Markdown Frontmatter, ADR, and versioning standards … enforces them with a Python validator"). Replace the whole `**Purpose:**` line with:

```text
**Purpose:** single source of truth for reusable standards — defines four: **Markdown Frontmatter** and **ADR** (enforced by a Python validator downstream repos run via a reusable CI workflow), **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig + optional `lint-markdown.yml`), and **Python Tooling SSOT** (copy-adopt scaffolds).
```

- [ ] **Step 5: Lint + format**

Run:

```bash
npx markdownlint-cli2 "docs/handoff/specs-plans.md" "docs/handoff/architecture.md" "docs/handoff/state.md" "AGENTS.md" "CLAUDE.md"
npx prettier --check "docs/handoff/specs-plans.md" "docs/handoff/architecture.md" "docs/handoff/state.md" "AGENTS.md" "CLAUDE.md"
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add docs/handoff/specs-plans.md docs/handoff/architecture.md docs/handoff/state.md AGENTS.md CLAUDE.md
git commit -m "docs(handoff,agents): record the Markdown Tooling Standard"
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
# Unknown version exits 2 — reliable, because the guard returns BEFORE file
# collection (a bare temp config is fine here; it never reaches collect_paths):
printf 'markdown_tooling:\n  version: "9.9"\n' > /tmp/bad.yml && uv run validate-frontmatter --config /tmp/bad.yml; echo "exit=$? (expect 2 + 'unknown markdown_tooling.version')"
# Known version passes: proven by the DOGFOODED real config below (it selects
# markdown_tooling.version: "1.0" and validates clean). Do NOT use a bare temp
# config for the pass case — with no `include` it falls back to scanning every
# **/*.md in the repo (collect_paths else-branch), so it cannot isolate the label.
grep -nE "version:|python_tooling:|markdown_tooling:" .project-standards.yml
uv run validate-frontmatter --config .project-standards.yml
# Release pins: FAIL (non-zero) if any stale @v1 lint-markdown ref survives in governed
# consumer-facing docs — scans ALL of standards/ (incl. markdown-frontmatter/adopt.md),
# README, CHANGELOG, and the workflow. (Historical docs/superpowers/** trail is left as-is.)
if grep -rn "lint-markdown.yml@v1" standards README.md CHANGELOG.md .github/workflows/lint-markdown.yml; then
  echo "FAIL: stale lint-markdown @v1 reference(s) above"; false
else
  echo "OK: no stale lint-markdown @v1"
fi
```

Expected: `bad.yml` → `exit=2` with the unknown-version message; the grep shows `markdown.frontmatter.version`/`markdown.adr.version`/`python_tooling`/`markdown_tooling` all present and the real config validates (`✓  14 file(s) validated`, which exercises the known-`markdown_tooling.version` pass path); the stale-pin block prints `OK: no stale lint-markdown @v1` (and exits non-zero if any were found).

- [ ] **Step 3: Confirm the working tree is clean and review the branch delta**

Run: `git status --short && git log --oneline main..testing | head -20` Expected: clean tree (only the user's untracked `TODO.md` may remain); the new commits present.

- [ ] **Step 4: Finishing the branch**

REQUIRED SUB-SKILL: invoke `superpowers:finishing-a-development-branch` to decide integration (this repo is single-developer; the likely path is fast-forwarding `testing` per the deferred release ritual — do not run the release ritual here unless asked).

---

## Self-review

**Spec coverage** (spec §7 touchpoints → task):

- README.md (standard) → Task 4; adopt.md → Task 5.
- registry.json / registry.py / validate_frontmatter.py / tests → Tasks 1–2.
- `.project-standards.yml` (dogfood: select all four contract versions) → Task 3.
- meta/versioning.md → Task 8; standards/README.md + root README.md → Task 7; frontmatter cross-link → Task 6.
- lint-markdown.yml + .vscode/settings.json → Task 9.
- CHANGELOG.md → Task 10; specs-plans/state/architecture → Task 11.
- Acceptance criteria (spec §8) → Task 12. Gate-green → Tasks 3 + 12. No touchpoint is unaddressed.

**Placeholder scan:** the two NEW prose docs (Task 4 README, Task 5 adopt) embed every config/snippet verbatim and reference spec §3/§4 for section content; the only non-verbatim work is the source-backed prose + the live source recheck, which is defined, bounded, and gated by validate-frontmatter + markdownlint + Prettier. No "TBD"/"handle errors"/"similar to" placeholders elsewhere.

**Type/name consistency:** `markdown_tooling_default` / `markdown_tooling_versions` / `is_known_markdown_tooling` (registry.py) and `markdown_tooling_version` (ProjectConfig) are used identically across Tasks 1–2 and the tests; the registry key `markdown_tooling`, the config key `markdown_tooling.version`, and the contract version `1.0` match the spec and `registry.json`. The two direct `Registry(...)` test constructions are updated in Task 1, the same task that makes the params required.

**Plan-audit rounds 1–4 (2026-06-07) + dogfood directive — folded in:**

- CR-001 (registry blast radius): Task 1 Step 6 now updates the parametrized malformed-registry fixtures and adds a `markdown_tooling.versions` case, so Task 1's own pytest gate stays green.
- CR-002 (stale `@v1`): Task 10 Step 2 fixes the existing CHANGELOG Stack B bullet; Task 12's stale-pin check now fails on a match and includes `CHANGELOG.md`.
- CR-003 (stale prose): Task 7 Step 5 fixes the README "two Markdown standards" sentence; Task 8 Step 3 fixes the `meta/versioning.md` "three standards / two Markdown / Two component-level markers" prose.
- CR-004 (collapsed tables): Task 7/8/11 table snippets are now plain `text` blocks (single physical rows), immune to Prettier reflow.
- Task 2's test selector is `-k "markdown_tooling and not registry"` so its count (4) is unambiguous.
- Dogfood directive: Task 3 now selects all four standards' contract versions in `.project-standards.yml` (adding the previously-unselected `python_tooling` and the new `markdown_tooling`); spec §4/§5/§7/§8 updated to match.
- CR-NEW-001 (round 2): Task 12's acceptance check no longer uses a bare `/tmp/ok.yml` for the pass case (it would fall back to scanning the whole repo via `collect_paths`); the known-version pass is proven by the dogfooded real config, and the unknown-version exit-2 case keeps its temp config (the guard returns before collection).
- CR-NEW-002 (round 2): Task 11 Step 4 refreshes the stale repo-purpose lines in `AGENTS.md` ("three standards") and `CLAUDE.md` (which also misnamed the set), prose-only and frontmatter-free.
- CR-NEW-002 precision (round 3): Task 11 Step 4's replacement wording now distinguishes the three enforcement mechanisms — validator-enforced (Frontmatter, ADR) vs copy-adopt + optional `lint-markdown.yml` (Markdown Tooling) vs copy-adopt scaffolds (Python Tooling) — instead of lumping all "Markdown ones" under the Python validator; it replaces the full stale sentence in both files, not just the count.
- CR-NEW-003 (round 4): Task 6 Step 3 fixes the two stale `lint-markdown.yml@v1` refs in the governed `standards/markdown-frontmatter/adopt.md` (leaving its correct `validate-markdown-frontmatter.yml@v1` refs), and Task 12's stale-pin sweep is widened from `standards/markdown-tooling/` to all of `standards/` so no governed consumer-facing doc can keep a wrong pin. The historical `docs/superpowers/specs/2026-06-04-…` `@v1` decision-trail reference is intentionally left as-is.
