# Design: Markdown Tooling Standard

**Date:** 2026-06-06 **Status:** approved (brainstorming complete; revised after spec audit round 1; awaiting implementation plan) **Author:** session 2026-06-06

## Problem / Goal

This repo defines a deliberately **tool-neutral** Markdown Frontmatter Standard (`standards/markdown-frontmatter/README.md`, line 35: "not an Obsidian/Hugo/Jekyll/Quarto schema"). It governs the YAML metadata block and says nothing about how the Markdown _body_ — or the JSON/YAML config files that live alongside docs — should be linted or formatted. Yet the repo already runs a complete toolchain for exactly that: Prettier (formatter, repo-wide over `md`/`json`/`jsonc`/`yaml`) + markdownlint-cli2 (Markdown linter) + EditorConfig (floor). That toolchain's design is recorded only as a scratch decision trail (`docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`, DEC-1…9) and as comments inside the config files. There is no **governing reference** a reader or downstream consumer can adopt.

The goal is a new governed standard — the tool-specific complement to the tool-neutral Frontmatter standard — that documents the recommended linting/formatting tools and their settings for Markdown and the structured-text/config files Prettier handles, is cross-linked from the Frontmatter standard, and follows the established per-standard bundle pattern so it adopts and versions like the others.

Task provenance: originated as a user TODO item ("Add an instruction/reference page explaining recommended linting and formatting tools and settings for markdown files, linked from the markdown frontmatter page") and is being actioned this session. The literal TODO line has since been cleared from `TODO.md`; this spec is the system of record for the request.

## Decisions (locked during brainstorming + audit round 1)

1. **Form = a new governed standard bundle** — sibling to `markdown-frontmatter/`, `adr/`, `python-tooling/`. The bundle folder is doc-only (`README.md` + `adopt.md`); the contract-version support lives in `src/` (like the frontmatter schema/validator), so "doc-only bundle" refers to the folder, not the standard's full footprint.
2. **Name/identity (kept after broadening)** — folder `standards/markdown-tooling/`; `id: markdown-tooling-standard`; title "Markdown Tooling Standard"; registry key `markdown_tooling`; contract version `1.0`. Markdown stays the anchor (it is the marquee concern and the only half that ships a linter + reusable workflow); a **Scope** section states the formatter's broader reach.
3. **Scope = broadened beyond Markdown body (audit SA-003).** The standard governs: **Prettier** formatting of every file type Prettier supports that a repo contains (the command is `prettier .`, **not** a closed extension list — so the coverage statement and the command cannot diverge; in this repo that resolves to `md`/`json`/`jsonc`/`yaml`); **markdownlint** structural linting of Markdown only; **EditorConfig** as the cross-editor floor. It is the "non-Python structured-text" tooling standard — complementary to the Python Tooling standard (ruff owns `.py`, which Prettier does not process) and the Frontmatter standard (YAML metadata _semantics_).
4. **Contract version = a fully validated label (audit SA-001).** `markdown_tooling.version` is recognized end-to-end like `python_tooling.version`: registered in `registry.json`, read by `registry.py`, and validated by `validate_frontmatter.py` (an unknown value exits `2`). A bare JSON key with no code would be silently inert and is explicitly rejected as a design.
5. **Evidence style = source-backed `[S##]`** with a dated Source register and a policy-vs-fact split — full parity with `python-tooling/README.md`.
6. **Section scope = full `python-tooling` parity** — CI reusable workflow, VS Code standard, agent instruction block, and non-default-tools + exceptions all included.
7. **Prettier treatment = recommend + document config, preserving DEC-9.** Prettier is recommended and its config documented as a **copy-adopt scaffold**; it ships **no reusable workflow** and is **not** a seeded/enforced artifact the way the markdownlint rule set is. (Broadening the file-scope is orthogonal to DEC-9, which is about shipping mechanics, not file coverage.)
8. **Consumer workflow pins `@v2` (audit SA-002).** `lint-markdown.yml` first ships in the locked `2.0.0` release; per the documented per-major moving-tag convention (`meta/versioning.md` §"Consuming"), new-in-2.0 surfaces must be referenced `@v2`, never `@v1`.
9. **Consolidate, do not re-decide.** The standard cites the DEC-3/4/7/8/9 trail as settled rationale; it does not reopen those choices.

## Background: what already exists (ground truth)

The standard documents reality. The repo's current toolchain:

| Artifact | Role | Status today |
| --- | --- | --- |
| `.markdownlint.json` | markdownlint rule set — **fully explicit** (53 rules @ v0.40.0 defaults, 13 deliberate deviations) | Published/seedable artifact; guarded by `tests/test_markdownlint_config.py` |
| `.markdownlint-cli2.jsonc` | Local runner config (`globs`, `gitignore: true`) | **NOT** part of the published standard — repo-local only |
| `.prettierrc.json` | Prettier config (tabs, `proseWrap: never`, `*.md` → `singleQuote`, `*.jsonc` → `trailingComma: none`, `printWidth: 88`) | Repo-local (DEC-9); pinned via `package.json` devDep `prettier 3.8.3` |
| `.editorconfig` | Cross-editor floor (charset, EOL, indent; `*.md` preserves trailing whitespace for hard breaks) | Recommended copy |
| `.github/workflows/lint-markdown.yml` | Reusable Markdown linter (`DavidAnson/markdownlint-cli2-action@v23`, `workflow_call` inputs `globs`/`config`) | Wired; separate from frontmatter validation (DEC-8). **Note:** its example comment (line 30) currently mis-pins `@v1` — corrected by this work (SA-002). |
| `.github/workflows/format.yml` | This repo's **repo-local** Prettier CI (`prettier --check .` over all Prettier-supported files; `md`/`json`/`jsonc`/`yaml`/config here); not a reusable workflow | Repo-local dogfood, no `workflow_call` (DEC-9) |
| `.vscode/settings.json` | `[markdown]`/`[json]`/`[jsonc]`/`[yaml]` → `esbenp.prettier-vscode`; `[python]` has `formatOnSave` but `[markdown]` does **not** | Present; gains Markdown `formatOnSave` via this work (SA-005) |
| `.vscode/extensions.json` | Recommends `esbenp.prettier-vscode` + `DavidAnson.vscode-markdownlint` | Present |

The decision trail (DEC-3/4/7/8/9) that produced these lives in `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`.

## Design

### 1. Bundle layout

```text
standards/markdown-tooling/
├── README.md      # the governing standard (source-backed)
└── adopt.md       # adoption runbook (doc_type: runbook)
```

Both files carry conformant frontmatter (`doc_type: reference` for README, `runbook` for adopt) because they fall under the validator's `standards/**/*.md` include. The contract-version support (decision 4) lives in `src/`, not the bundle.

### 2. The spine — formatter + linter + floor, and the published/repo-local asymmetry

| Tool | Owns | File coverage | Shipped to consumers? | Enforcement surface |
| --- | --- | --- | --- | --- |
| **Prettier** | Formatting: whitespace, wrapping, list/marker spacing, fence & emphasis style, JSON/YAML shape | all Prettier-supported files via `prettier .` (`md`/`json`/`jsonc`/`yaml` here) | ❌ copy-adopt config only (DEC-9) | None shipped — local/editor + the consumer's own CI |
| **markdownlint** (`markdownlint-cli2`) | Markdown structure: headings, lists, links, fences, inline rules | `md` only | ✅ `.markdownlint.json` is the seedable artifact | Reusable workflow `lint-markdown.yml` (`@v2`) |
| **EditorConfig** | The floor under both: charset, EOL, final newline, indent | all files | Recommended copy | Editor-native |

**Division of labor across the three standards:** ruff owns `.py` (Python Tooling standard); Prettier owns the non-Python structured text it supports (`md`/`json`/`jsonc`/`yaml` in this repo); markdownlint adds Markdown-only structural linting; the Frontmatter standard owns YAML _metadata semantics_ (key order, enums) which Prettier deliberately does **not** touch (DEC-4: Prettier reorders nothing and is not the frontmatter gate).

**Why the 13 markdownlint deviations exist:** Prettier owns physical formatting, so the markdownlint rules that would duplicate or contradict it are turned **off** (MD009 trailing whitespace, MD010 hard tabs, MD013 line length, MD030 list-marker spacing, MD032 blanks-around-lists) or **aligned** to Prettier's output (MD003 atx, MD004 dash, MD048 backtick fences, MD049 underscore italics, MD050 asterisk bold). The rest are semantic: MD024 off (MADR 4.0 allows duplicate option headings), MD025 frontmatter-title handling, MD029 off. The two tools are tuned **not to fight**.

### 3. `README.md` section outline (with content notes)

Numbered sections, `python-tooling` parity:

1. **Evidence convention** — source-backed facts cite `[S##]`; policy decisions called out as local standards; version pins are template defaults to recheck.
2. **Purpose & scope** — governs Markdown linting + Prettier formatting of all Prettier-supported files (`md`/`json`/`jsonc`/`yaml` in this repo) + the EditorConfig floor; the complement to the tool-neutral Frontmatter standard and the Python Tooling standard. Out of scope: `.py` (ruff) and YAML frontmatter _semantics_ (the Frontmatter schema/validator).
3. **Core contract** — two command pairs:
   - Check (non-mutating): `npx prettier --check .` + `npx markdownlint-cli2 "**/*.md"`
   - Fix (mutating): `npx prettier --write .` + `npx markdownlint-cli2 --fix "**/*.md"`
   - `prettier .` formats every file type Prettier supports that it finds (respecting `.gitignore`/`.prettierignore`), so the contract's coverage is "whatever Prettier supports," not a fixed extension list — the command can't contradict the coverage statement; in this repo it resolves to `md`/`json`/`jsonc`/`yaml` (matches `format.yml`). markdownlint is Markdown-only. Note pinning: this repo pins Prettier via `package.json`; CI pins the markdownlint action `@v23`; `npx` shown for portability.
4. **Standard stack** table — Prettier, `markdownlint-cli2`, `markdownlint-cli2-action`, EditorConfig — each row: tool / source-backed basis / policy. Plus a **Node-runtime note**: no committed Node project is required for the linter (runners ship Node; the action ships its own Node24); Prettier, if pinned reproducibly, uses a minimal `package.json`. Frontmatter-only consumers never inherit the linter toolchain (DEC-8).
5. **Published vs repo-local artifacts** — the §2 asymmetry, citing DEC-9: the markdownlint rule set ships + has a reusable workflow; Prettier is copy-adopt with no reusable workflow; `format.yml` is this repo's repo-local Prettier CI; `.markdownlint-cli2.jsonc` is repo-local runner config, never shipped.
6. **Formatter — Prettier** — `.prettierrc.json` explained: `useTabs: true`/`tabWidth: 2`, `printWidth: 88`, `proseWrap: never` (so MD013 can stay off — the linchpin of the no-fight design), `endOfLine: lf`, the `*.md` → `singleQuote: true` and `*.jsonc` → `trailingComma: none` overrides. Recommend-and-copy framing; explicit DEC-9 note that this is a copy-adopt scaffold, not a shipped/enforced artifact.
7. **Linter — markdownlint** — why the config is **fully explicit** (a consumer seeding it gets deterministic linting regardless of their editor/global settings; any rule a future markdownlint version adds lands at its default via `default: true` rather than silently off). The **13 deviations** table with per-rule rationale. The **MD043 sentinel trap**: stated explicitly, `headings: []` means "require zero headings"; `true` is the correct inert form — guarded by `test_markdownlint_config.py`.
8. **Frontmatter coupling** — the cross-link rationale: `MD025`/`MD041`/`MD001` key off `front_matter_title`; this repo's model is frontmatter `title:` + a body `# H1`, so MD025 uses the DavidAnson `""`-disable model while MD041/MD001 use the `title:` regex. This is **why PyMarkdown was rejected** (DEC-3): it can't read `.markdownlint.json` and implements MD025 as a key-name model that forces all headings to ≥ H2, clashing with our docs. Links to `standards/markdown-frontmatter/README.md`.
9. **`.editorconfig`** — the Markdown specifics: `[*.md] trim_trailing_whitespace = false` because two trailing spaces are a Markdown hard line break that Prettier preserves; stripping them would make editor and Prettier disagree on save.
10. **VS Code standard** — recommend `esbenp.prettier-vscode` (default formatter for `md`/`json`/`jsonc`/`yaml`) + `DavidAnson.vscode-markdownlint` (diagnostics); one-formatter-authority rule (Prettier formats on save; markdownlint only diagnoses — **no** markdownlint fix-on-save code action, so the two never both mutate a file on save). Documents this repo's actual `.vscode/settings.json` after it gains `[markdown]` `formatOnSave` for Prettier (SA-005), so the section is true dogfood, not aspirational. Mirrors `python-tooling` §13.
11. **CI reusable workflow** — document `lint-markdown.yml`: the action, the `workflow_call` `globs`/`config` inputs, the consumer opt-in snippet pinned **`@v2`**, and the deliberate separation from the frontmatter workflow (DEC-8). Note Prettier ships no reusable workflow (DEC-9) — a consumer wanting Prettier CI wires their own.
12. **Agent instruction block** — copy-paste fix-pass + check-only contract for these file types, parallel to `python-tooling` §16's `AGENTS.md` block.
13. **Non-default tools** — PyMarkdown (DEC-3 rejection), remark-lint, dprint, mdformat, Vale — each with a one-line rationale; framed as a per-project add-prohibition, not a workstation uninstall order (mirrors `python-tooling` §3).
14. **Exceptions process** — ADR-based, pointing to the ADR Standard, mirroring `python-tooling` §20.
15. **Update process / review cadence** — when to recheck (tool releases, rule-set changes, action version bumps).
16. **Source coverage map** — section → source-IDs table.
17. **Source register** — dated `[S##]` table (see §6 of this spec for the source list).
18. **Citation reference-link definitions** — `[S01]: #NN-source-register` block (GFM can't anchor table rows), matching `python-tooling`.

### 4. `adopt.md` (runbook)

Steps, mirroring `python-tooling/adopt.md`'s shape:

1. Seed `.markdownlint.json` (the rule set) and `.editorconfig` from this repo.
2. Optionally copy `.prettierrc.json`; pin Prettier via a minimal `package.json` devDep **or** run via `npx prettier@<version>`.
3. Wire the reusable linter: add a job that calls `lint-markdown.yml@v2` (snippet).
4. Add the two VS Code recommendations.
5. Select the contract version in `.project-standards.yml` (`markdown_tooling.version: '1.0'`); it is validated-if-present metadata only — it runs no check by itself (the markdownlint workflow is the enforcement). For consumers this step is optional; **this repo selects it to dogfood** (see §7).
6. Run the check contract (§3 of the standard) to confirm clean.
7. Need an exception? Record an ADR (→ ADR Standard).

State plainly: the linter half ships a reusable workflow but **no Python validator runs over Markdown bodies**; the formatter half is copy-adopt only; the contract version is a validated label, not a gate.

### 5. Contract-version support (the `src/` work — audit SA-001)

To make `markdown_tooling.version` behave exactly like `python_tooling.version`:

- **`src/project_standards/schemas/registry.json`** — add `"markdown_tooling": { "default": "1.0", "versions": ["1.0"] }`.
- **`src/project_standards/registry.py`** — add `markdown_tooling_default` + `markdown_tooling_versions` to `Registry.__init__`, an `is_known_markdown_tooling()` method (mirror `is_known_python_tooling`, registry.py:73-74), and parse + require the `markdown_tooling` object in `load_registry` (mirror the `python_tooling` list handling, registry.py:100-134).
- **`src/project_standards/validate_frontmatter.py`** — add `markdown_tooling_version` to `ProjectConfig` (mirror `python_tooling_version`, line 293/302), parse it in `load_config`, and add the unknown-version guard returning exit `2` (mirror lines 483-491). Metadata only: validated-if-present, never emitted.
- **Tests (`tests/`)** — mandatory, not optional: `markdown_tooling.version: '1.0'` validates clean; `'9.9'` exits `2` with an "unknown markdown_tooling.version" message; a config with no `markdown_tooling` key validates byte-identically to current behavior; the registry-shape tests accept the new required object. Mirror `tests/test_validate_frontmatter.py:579` and `:1172` and any registry-shape test.

**Dogfood directive:** this repo selects a contract version for **every standard it defines** — so its `.project-standards.yml` adds **both** `markdown_tooling.version: '1.0'` and `python_tooling.version: '1.0'`, alongside the existing `markdown.frontmatter.version`/`markdown.adr.version`. Before this work `python_tooling` was registered + validated but **not** selected here; that gap is closed so the repo is a complete worked example and the validated-label code path runs against this repo on every CI run. (For downstream consumers, selecting either copy-adopt label remains optional.)

### 6. Sources to (re)check during spec→standard authoring

The dated Source register requires a live recheck of current official docs. Anticipated source set:

- Prettier — options (`proseWrap`, `printWidth`, `useTabs`, overrides), configuration discovery, CLI.
- markdownlint (DavidAnson) — `Rules.md` (MD001/003/004/009/010/013/024/025/029/030/032/041/043/048/049/050), `.markdownlint.json` schema, `default` behavior.
- `markdownlint-cli2` — config discovery (auto-reads `.markdownlint.json`), `globs`, `gitignore`.
- `markdownlint-cli2-action` — bundled Node24 runtime, config auto-discovery, version pinning, non-recursive default globs.
- EditorConfig — properties and `root`/glob behavior.
- `esbenp.prettier-vscode` + `DavidAnson.vscode-markdownlint` — extension behavior/settings.
- AGENTS.md / Claude Code memory (reuse `python-tooling`'s S30–S32 where applicable).
- MADR 4.0's own `.markdownlint.yml` (DEC-3 evidence: same engine/rule-IDs, `MD024: false`).

### 7. Repo touchpoints (multi-file change list)

| File | Change |
| --- | --- |
| `standards/markdown-tooling/README.md` | **NEW** — the standard |
| `standards/markdown-tooling/adopt.md` | **NEW** — adoption runbook |
| `src/project_standards/schemas/registry.json` | add `markdown_tooling` (SA-001) |
| `src/project_standards/registry.py` | add `markdown_tooling` parsing + `is_known_markdown_tooling` (SA-001) |
| `src/project_standards/validate_frontmatter.py` | parse + validate `markdown_tooling.version`, exit 2 on unknown (SA-001) |
| `tests/test_validate_frontmatter.py` (+ registry-shape test) | mandatory tests for the validated label (SA-001) |
| `meta/versioning.md` | document the new standard's contract version + its release-level rules (mirror the Python Tooling row) |
| `standards/README.md` | add index row |
| `README.md` (root) | add the new standard to the standards + consuming sections (SA-004) |
| `standards/markdown-frontmatter/README.md` | add `related:` entry + in-body cross-link (satisfies the TODO's "linked from the markdown frontmatter page") |
| `.github/workflows/lint-markdown.yml` | fix the stale `@v1` example comment → `@v2` (SA-002) |
| `.vscode/settings.json` | add `[markdown]` `editor.formatOnSave: true` (**Prettier only**) to dogfood the VS Code section; **no** markdownlint fix-on-save code action — markdownlint stays diagnostics-only, preserving one-formatter-authority (SA-005, SA-NEW-001) |
| `CHANGELOG.md` | additive entry under the unreleased section (rides the locked `2.0.0`) |
| `docs/handoff/specs-plans.md` | add design + plan rows |
| `docs/handoff/state.md` | reflect the new standard in the at-a-glance bullets |
| `docs/handoff/architecture.md` | add the standard to the component list |

### 8. Acceptance criteria

#### Bundle & docs

- `standards/markdown-tooling/{README.md,adopt.md}` exist, carry conformant frontmatter, and pass `uv run validate-frontmatter --config .project-standards.yml`.
- `standards/README.md` and root `README.md` both list the new standard (standards table + consuming section).
- `standards/markdown-frontmatter/README.md` links to the new standard via `related:` and an in-body reference.

#### Validated contract label

- `registry.json` contains `markdown_tooling` with `default: "1.0"` and `versions: ["1.0"]`.
- A `.project-standards.yml` containing `markdown_tooling.version: "1.0"` → exit `0`.
- `markdown_tooling.version: "9.9"` → exit `2`, stderr contains `unknown markdown_tooling.version`.
- A config omitting `markdown_tooling` validates identically to pre-change behavior (regression test green).
- This repo's `.project-standards.yml` selects all four contract versions (`markdown.frontmatter.version` `1.1`, `markdown.adr.version` `1.0`, `python_tooling.version` `1.0`, `markdown_tooling.version` `1.0`) and `validate-frontmatter` passes — dogfooding every standard the repo defines.

#### Formatter / linter scope

- The standard's documented Prettier coverage is stated as "all Prettier-supported files" — matching the `prettier --check .` command, with `md`/`json`/`jsonc`/`yaml` named as this repo's resolved set — so the coverage statement and the command do not diverge (no closed extension list the command could contradict).
- markdownlint is documented Markdown-only (`markdownlint-cli2 "**/*.md"`).
- The standard documents Prettier as copy-adopt with no reusable workflow (DEC-9 intact).

#### Release pins

- Every consumer `uses:` snippet in `README.md` / `adopt.md` for `lint-markdown.yml` pins `@v2`.
- `lint-markdown.yml`'s example comment no longer references `@v1`.
- No documented `uses:` ref points at a tag that lacks the referenced workflow.

#### VS Code dogfood

- `.vscode/settings.json` `[markdown]` block sets `editor.formatOnSave: true` (Prettier) and adds **no** markdownlint fix-on-save code action (diagnostics-only); the README VS Code section matches the file.

#### Source register

- Every `[S##]` marker in the new README resolves to a Source register row dated the authoring day, with a live-checked URL.

#### Gate green (repo non-negotiable)

- `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit` all pass.
- `uv run validate-frontmatter --config .project-standards.yml` passes.
- `npx prettier --check .` and `npx markdownlint-cli2 "**/*.md"` pass.

## Versioning & release interplay

- The new standard's contract version starts at `1.0` (registry `markdown_tooling`).
- Adding a standard + a new bundled contract version is **additive** = a MINOR tool release (`meta/versioning.md` §"two-plane"). But the next release is **already locked to `2.0.0`** (the `requires-python` floor change), so this rides that release — no new release-level decision.
- `lint-markdown.yml` first appears in `2.0.0`; consumer snippets therefore pin `@v2` (the per-major moving tag the release ritual will create), per `meta/versioning.md` §"Consuming".
- **Dogfooding:** this repo's `.project-standards.yml` selects all four standards' contract versions (`markdown.frontmatter.version` `1.1`, `markdown.adr.version` `1.0`, `python_tooling.version` `1.0`, `markdown_tooling.version` `1.0`). The two copy-adopt labels (`python_tooling`, `markdown_tooling`) are metadata-only — validated as known versions on every run, emitting nothing and changing no file-validation outcome.

## Non-goals

- **No new validator over document bodies / no schema.** Markdown body linting is enforced (downstream) only by the existing reusable markdownlint workflow; the contract version is a validated _label_, not a body gate.
- **Not reopening DEC-1/2/5/6** (ADR/MADR-specific) — only the lint/format decisions (DEC-3/4/7/8/9) are consolidated.
- **No changes to rule-set/formatter _semantics_.** `.markdownlint.json`, `.prettierrc.json`, and `.editorconfig` rule values are documented as-is. The only config edits in scope are the `.vscode/settings.json` `[markdown]` `formatOnSave` addition for Prettier (SA-005; **no** markdownlint code action — SA-NEW-001) and the `lint-markdown.yml` example-comment tag fix (SA-002) — neither changes what the tools enforce. If authoring surfaces a genuine rule bug, it is raised separately, not silently changed here.
- **No re-architecture of `.markdownlint-cli2.jsonc` or `format.yml`** — both stay repo-local; the standard explains why they are not shipped.

## Open questions

None blocking. Resolved across brainstorming + audit rounds 1–2: form (bundle), name (`markdown-tooling`, kept after broadening), scope (Prettier governs all the files it supports, stated to match the `prettier .` command), evidence style (source-backed), section scope (full parity), Prettier treatment (recommend + copy-adopt, DEC-9 preserved), contract version (fully validated label), consumer tag (`@v2`), VS Code authority (Prettier formats on save; markdownlint diagnoses only).

## Audit trail

- **Round 1 (2026-06-06):** external adversarial spec audit — 3 blocking (SA-001 inert registry key, SA-002 `@v1` unresolvable, SA-003 Prettier scope) + 3 non-blocking (SA-004 root README, SA-005 VS Code dogfood, SA-006 stale provenance). All six verified against the codebase and resolved: SA-001 → full validated label (decision 4, §5); SA-002 → `@v2` + comment fix (decision 8); SA-003 → broaden scope (decision 3); SA-004/005/006 → touchpoints + provenance fix. Acceptance criteria (§8) added per the audit's "missing considerations."
- **Post-approval directive (2026-06-07):** user directed that this repo dogfood **every** standard it defines. The spec's earlier "do not select `markdown_tooling` in this repo's `.project-standards.yml` (mirror `python_tooling`)" stance is reversed: this repo now selects all four contract versions, and the previously-unselected `python_tooling.version` is added too. Reflected in §4 step 5, §5, §7, and §8.
- **Round 2 (2026-06-06):** follow-up audit confirmed SA-001/002/004/005/006 resolved; flagged SA-003 **partially** resolved (coverage stated as a closed `md/json/jsonc/yaml` set while the command `prettier .` formats every supported file) and new SA-NEW-001 (the added markdownlint code-action would make markdownlint a fixer, breaking one-formatter-authority). Both resolved here: SA-003 → coverage restated as "all Prettier-supported files" so command and coverage cannot diverge (decision 3, §2/§3, §8 AC); SA-NEW-001 → markdownlint stays diagnostics-only, no fix-on-save code action (§3 item 10, §7, §8 AC, non-goals).
