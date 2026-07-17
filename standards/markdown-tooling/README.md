# Markdown Tooling Standard

- **Status:** Source-checked standard, contract version `1.1` (a copy-adopted label; selected by consumers via `markdown_tooling.version` — see [`meta/versioning.md`](../../meta/versioning.md))
- **Owner:** Project standards / repository template
- **Last updated:** 2026-07-05
- **Last source check:** 2026-06-07
- **Scope:** Markdown and the structured-text/config files Prettier supports, across CLI, VS Code, and CI.

---

## Table of Contents

- [Markdown Tooling Standard](#markdown-tooling-standard)
  - [Table of Contents](#table-of-contents)
  - [1. Evidence convention](#1-evidence-convention)
  - [2. Purpose \& scope](#2-purpose--scope)
  - [3. Core contract](#3-core-contract)
  - [4. Standard stack](#4-standard-stack)
  - [5. Published vs repo-local artifacts](#5-published-vs-repo-local-artifacts)
  - [6. Formatter — Prettier](#6-formatter--prettier)
  - [7. Linter — markdownlint](#7-linter--markdownlint)
    - [The MD043 sentinel trap](#the-md043-sentinel-trap)
    - [MD060 and Prettier table alignment](#md060-and-prettier-table-alignment)
  - [8. Frontmatter coupling](#8-frontmatter-coupling)
  - [9. `.editorconfig`](#9-editorconfig)
  - [10. VS Code standard](#10-vs-code-standard)
    - [One-formatter-authority rule](#one-formatter-authority-rule)
  - [11. CI reusable workflow](#11-ci-reusable-workflow)
  - [12. Agent instruction block](#12-agent-instruction-block)
  - [13. Non-default tools](#13-non-default-tools)
  - [14. Exceptions process](#14-exceptions-process)
  - [15. Update process / review cadence](#15-update-process--review-cadence)
  - [16. Source coverage map](#16-source-coverage-map)
  - [17. Source register](#17-source-register)

## 1. Evidence convention

This document separates **source-backed facts** from **project policy decisions**.

- Source-backed facts cite source IDs such as `[S04]`.
- Every source ID is listed in [Source register](#17-source-register), with `Last checked: 2026-06-07`.
- Policy decisions are explicitly local standards for this project ecosystem. They may be informed by sources, but the final choice is a standard, not a claim that the source mandates it.
- Version pins in examples are template defaults and must be rechecked when the standard is reviewed.

---

## 2. Purpose & scope

This document defines the recommended linting and formatting tools and settings for **Markdown and the adjacent structured-text files** in a repository. It is the tool-specific complement to the deliberately tool-neutral [Markdown Frontmatter Standard](../markdown-frontmatter/README.md) (which governs the YAML metadata block) and a sibling to the [Python Tooling Standard](../python-tooling/README.md) (which governs `.py`).

The standard governs three layers:

- **Prettier** — formatting of **every file type Prettier supports** that a repo contains. The command is `prettier .`, which recursively finds supported files by extension and well-known filename [S02], so the coverage statement is "whatever Prettier supports," not a closed extension list — the command can never diverge from the coverage statement. In this repo that resolves to `md` / `json` / `jsonc` / `yaml`.
- **markdownlint** — structural linting of **Markdown only** (headings, lists, links, fences, inline rules) [S04].
- **EditorConfig** — the cross-editor **floor** under both: charset, line endings, final newline, indentation [S07].

Out of scope:

- `.py` source — owned by ruff under the Python Tooling Standard. Prettier does not process Python.
- YAML frontmatter **semantics** — key order, enums, and the schema are owned by the Markdown Frontmatter Standard and its validator. Prettier formats the frontmatter block's whitespace/quoting but never reorders or gates its keys.

Policy decision: this is the "non-Python structured-text" tooling standard. ruff owns `.py`; Prettier owns the non-Python structured text it supports; markdownlint adds Markdown-only structure; the Frontmatter standard owns metadata semantics.

---

## 3. Core contract

Two command pairs prove and repair a repository.

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

How the commands resolve:

- `prettier .` treats the path as a directory and **recursively finds every supported file** in it, based on file extensions and well-known filenames Prettier associates with supported languages [S02]. By default it looks for `./.gitignore` and `./.prettierignore` and skips matching files [S02], and it ignores `node_modules` [S02]. Because the command formats "all files supported by Prettier," its coverage and the coverage statement in §2 cannot diverge — there is no closed extension list the command could contradict. In this repo it resolves to `md` / `json` / `jsonc` / `yaml` (matching `format.yml`).
- `markdownlint-cli2 "**/*.md"` is **Markdown-only** and applies fixes directly to files when `--fix` is passed, with no backups [S03].

Version pinning:

- This repo pins Prettier via `package.json` (a committed dev dependency); CI installs it from the lockfile.
- CI pins the markdownlint action at `@v23` [S05].
- `npx` is shown above for portability; a consumer that wants reproducible local runs pins the version (`npx prettier@<version>` or a `package.json` devDep).

Policy decision: work over these file types is not complete until the check contract passes, unless the final response explicitly reports what failed and why.

---

## 4. Standard stack

| Tool | Source-backed basis | Policy |
| --- | --- | --- |
| **Prettier** | Opinionated formatter; reads `.prettierrc.json` discovered up the file tree, supports per-file `overrides`, and recursively formats all supported files via `prettier .`. [S01], [S02] | Prettier owns physical formatting of all the structured-text it supports (`md`/`json`/`jsonc`/`yaml` here). Copy-adopt config **plus** a reusable opt-in workflow (`format.yml` + `format.caller.yml`; DEC-10) that enforces `prettier --check .` repo-wide. |
| **`markdownlint-cli2`** | Markdown linter that auto-discovers `.markdownlint-cli2.jsonc` / `.markdownlint.json` up the tree, accepts globs on the CLI, honors `gitignore`, and applies `--fix` in place. [S03], [S04] | markdownlint owns Markdown-only structural linting. The rule set (`.markdownlint.json`) is the seedable artifact. |
| **`markdownlint-cli2-action`** | GitHub Action running on its own bundled **Node 24** (`using: node24`) [S06]; globs newline-delimited, default glob the non-recursive `*.{md,markdown}`, pinned by major tag (`@v24`) [S05]. | The reusable CI surface for the linter half. Pin the action by major tag; pass `globs` explicitly. |
| **EditorConfig** | Cross-editor style file; `root = true` stops the upward search; supports `charset`, `end_of_line`, `indent_style`/`indent_size`, `insert_final_newline`, `trim_trailing_whitespace`; `[glob]` sections match by filepath. [S07] | The floor under both tools. Recommended copy. |

Node-runtime note: **no committed Node project is required for the linter.** GitHub runners ship Node, and the action ships its own Node 24 runtime [S06]. Prettier, if pinned reproducibly, uses a minimal `package.json` (this repo does exactly that). Frontmatter-only consumers — those that adopt only the Markdown Frontmatter Standard's validator — never inherit this linter/formatter toolchain, because it is wired as a separate opt-in workflow (DEC-8: a separate opt-in lint workflow so frontmatter-only consumers don't inherit a Node/markdownlint toolchain).

---

## 5. Published vs repo-local artifacts

Both halves of this standard now ship a reusable workflow (DEC-10); the remaining asymmetry is only which config is a copy-adopt seed.

| Artifact | Role | Shipped to consumers? |
| --- | --- | --- |
| `.markdownlint.json` | The markdownlint **rule set** | ✅ Yes — the seedable artifact a consumer copies. |
| `.github/workflows/lint-markdown.yml` | Reusable markdownlint **workflow** (`@v4`) | ✅ Yes — callable via `workflow_call`. |
| `.prettierrc.json` | Prettier **config** | ✅ Copy-adopt config, enforced via the reusable `format.yml`. |
| `.github/workflows/format.yml` | Reusable Prettier **workflow** (`@v4`) | ✅ Yes — dual-role, callable via `workflow_call` (opt-in `format.caller.yml`). |
| `.markdownlint-cli2.jsonc` | **Repo-local** runner config (`globs`, `gitignore`) | ❌ Never shipped — controls which files a bare local run lints. |

Policy decision (DEC-10): both the markdownlint rule set and the Prettier config ship, and **both** now have a reusable workflow (`lint-markdown.yml`, `format.yml`). Prettier enforcement is opt-in — adopt `format.caller.yml` (or `uses: …/format.yml@v4`), and set `prettier: false` to defer it (the whole job skips). `.markdownlint-cli2.jsonc` exists so a bare `npx markdownlint-cli2` locally matches CI (same files, `.gitignore` honored) — it is not part of the published standard; the artifact consumers seed is `.markdownlint.json`, which `markdownlint-cli2` auto-merges [S03].

---

## 6. Formatter — Prettier

Prettier owns physical formatting: whitespace, wrapping, list/marker spacing, fence and emphasis style, and JSON/YAML shape. The config is `.prettierrc.json`:

<!-- This fence must stay byte-identical to the adopt bundle's prettierrc.json
(guarded by test_adopt_dogfood.py). The bare prettier-ignore keeps Prettier's
embedded formatting from ever reshaping the block. -->
<!-- prettier-ignore -->
```json
{
	"$schema": "https://json.schemastore.org/prettierrc.json",
	"printWidth": 88,
	"tabWidth": 2,
	"useTabs": true,
	"endOfLine": "lf",
	"semi": false,
	"singleQuote": false,
	"jsxSingleQuote": false,
	"quoteProps": "consistent",
	"trailingComma": "es5",
	"arrowParens": "always",
	"bracketSpacing": true,
	"bracketSameLine": false,
	"singleAttributePerLine": false,
	"objectWrap": "collapse",
	"proseWrap": "never",
	"htmlWhitespaceSensitivity": "css",
	"experimentalTernaries": false,
	"experimentalOperatorPosition": "end",
	"embeddedLanguageFormatting": "auto",
	"vueIndentScriptAndStyle": false,
	"requirePragma": false,
	"insertPragma": false,
	"overrides": [
		{ "files": "**/*.jsonc", "options": { "trailingComma": "none" } },
		{ "files": "**/*.md", "options": { "singleQuote": true } }
	]
}
```

The load-bearing values:

- `useTabs: true` / `tabWidth: 2` — indent with tabs, two columns wide [S01]. (Tabs render at the reader's preferred width and keep diffs small.)
- `printWidth: 88` — the wrap target. It is a guideline, not a hard limit; Prettier may emit shorter or longer lines [S01]. Policy decision: the value `88` is a project choice, not a source mandate — it keeps Markdown's wrap target in the same range as the Python/ruff line length so the ecosystem's tools agree on a width.
- `proseWrap: never` — **the linchpin.** With `"never"`, each prose block is placed on a single line and Prettier never re-wraps Markdown prose [S01]. This is why markdownlint's MD013 (line length) can stay **off** (§7): nothing wraps prose, so there is no line-length rule to fight. Note: Prettier's `proseWrap` default is `"preserve"` [S01], so a consumer who copies the config but omits `proseWrap: never` gets different behavior and breaks the MD013-off pairing — copy this option explicitly.
- `endOfLine: lf` — Unix line endings [S01].
- Overrides: `*.md` → `singleQuote: true` (single quotes inside Markdown, e.g. in embedded code), and `*.jsonc` → `trailingComma: none` (JSON-with-comments tolerates no trailing commas). Prettier applies per-file overrides via the `overrides` field, each with a `files` matcher and its own `options` [S02].

Prettier discovers this file by searching up the tree from each formatted file; `.prettierrc.json` is one of the recognized names [S02].

Policy decision (DEC-10): `.prettierrc.json` is a copy-adopt config **and** Prettier is now a shipped, enforceable artifact via the opt-in reusable `format.yml` (adopted as `format.caller.yml`, pinned Prettier `3.8.3`, `prettier: false` to defer). Copy the config, then enforce it in CI by adopting the workflow — no hand-rolled Prettier job needed. (Supersedes DEC-9's "copy-adopt scaffold, not shipped or enforced" clause.)

---

## 7. Linter — markdownlint

The repo's `.markdownlint.json` states **every** rule explicitly — `default: true` plus all 53 rules at their v0.40.0 defaults, with 13 deliberate deviations. Setting `default: true` enables all rules at their defaults; later keys override individual rules [S08].

Why fully explicit rather than a sparse override list:

- A consumer who seeds their config from this one gets **deterministic** linting regardless of their own editor/global markdownlint settings.
- Any rule a **future** markdownlint version adds lands at its default via `default: true` rather than silently off — the opposite of the failure mode where a new rule appears disabled because nobody enumerated it.

The 13 deliberate deviations:

| Rule | Value | Rationale |
| --- | --- | --- |
| MD003 (heading-style) | `{ "style": "atx" }` | Align headings to Prettier's ATX output (`#` headings). [S08] |
| MD004 (ul-style) | `{ "style": "dash" }` | Align bullets to Prettier's `-` marker. [S08] |
| MD009 (trailing-spaces) | `false` | Prettier owns trailing whitespace; disabling avoids fighting it. [S08] |
| MD010 (hard-tabs) | `false` | Prettier emits tabs (`useTabs: true`); the hard-tab rule would flag them. [S08] |
| MD013 (line-length) | `false` | Prettier owns line length; with `proseWrap: never` there is nothing to enforce (§6). [S08] |
| MD024 (duplicate-headings) | `false` | Match MADR 4.0, which allows duplicate option headings (its own config sets `MD024: false`). [S08], [S09] |
| MD025 (single-h1) | `{ "front_matter_title": "", "level": 1 }` | This repo's frontmatter `title:` is **not** an H1; the `""` disable model keeps MD025 from counting it (§8). [S08] |
| MD029 (ol-prefix) | `false` | Ordered-list prefix style not enforced. [S08] |
| MD030 (list-marker-space) | `false` | Prettier owns list-marker spacing. [S08] |
| MD032 (blanks-around-lists) | `false` | Prettier owns blank lines around lists. [S08] |
| MD048 (code-fence-style) | `{ "style": "backtick" }` | Align fences to Prettier's backtick fences. [S08] |
| MD049 (emphasis-style) | `{ "style": "underscore" }` | Align italics to Prettier's `_italic_`. [S08] |
| MD050 (strong-style) | `{ "style": "asterisk" }` | Align bold to Prettier's `**bold**`. [S08] |

Five of these turn **off** rules Prettier already owns (MD009, MD010, MD013, MD030, MD032); five **align** style rules to Prettier's exact output (MD003, MD004, MD048, MD049, MD050); three are semantic (MD024 for MADR, MD025 for frontmatter, MD029). The two tools are tuned **not to fight**: Prettier formats, markdownlint checks structure, and no rule contradicts the formatter's output.

### The MD043 sentinel trap

MD043 (required-headings) is configured by a `headings` array [S08]. Its schema default for that array is `[]` (empty) — which, stated explicitly, means "**require exactly zero headings**" and would flag every heading in every file. The correct **inert** form is `"MD043": true`, which leaves the rule enabled at its real default (no required structure). This repo uses `true`, and the trap is guarded by `tests/test_markdownlint_config.py` (`test_md043_stays_inert` plus a defensive check that no rule anywhere carries an empty `headings: []`).

### MD060 and Prettier table alignment

MD060 (table-column-style) is pinned to `{ "style": "any", "aligned_delimiter": false }` [S08]. This is not a gap — Prettier reflows Markdown tables to its own column widths and delimiter alignment, and `style: "any"` tells markdownlint to accept whichever alignment Prettier produces rather than enforcing a competing convention. A live repro of prettier@3 and markdownlint-cli2 over this repo's Markdown under the shipped config confirms zero MD060 findings; do not tighten this setting without re-running that repro.

---

## 8. Frontmatter coupling

Three markdownlint rules key off the document's frontmatter title, which is **why** this standard cross-links the [Markdown Frontmatter Standard](../markdown-frontmatter/README.md):

- **MD025 (single-h1)** and **MD041 (first-line-h1)** both accept a `front_matter_title` parameter so a YAML title is recognized as the document title [S08].
- **MD001 (heading-increment)** then reasons about heading levels relative to that title [S08].

This repo's model is **frontmatter `title:` plus a body `# H1`** — the body still opens with a real H1 heading. The config threads that needle:

- MD025 uses the DavidAnson `""`-disable model (`"front_matter_title": ""`) so the frontmatter `title:` is **not** counted as a competing H1 — the single H1 is the body heading.
- MD041 and MD001 use the title **regex** (`"front_matter_title": "^\\s*title\\s*[:=]"`) so the presence of a `title:` line satisfies "document has a title" without forcing the body's first line.

Why **PyMarkdown was rejected** (DEC-3): PyMarkdown is a different engine that **cannot read `.markdownlint.json`** (so the shipped rule set could not be its config), and it models MD025 as a key-name forcing all body headings to be ≥ H2 — which clashes directly with this repo's frontmatter-`title:` + body-`# H1` model. DavidAnson markdownlint, by contrast, reads the shipped JSON config and supports the `""`/regex `front_matter_title` handling above.

---

## 9. `.editorconfig`

EditorConfig is the floor under both tools — every editor agrees on charset, line endings, final newline, and indentation before Prettier or markdownlint runs [S07]. The Markdown-specific line:

```ini
[*.md]
indent_style = space
indent_size = 2
trim_trailing_whitespace = false
```

Prettier's Markdown printer aligns nested list content with spaces even when `useTabs` is enabled, because CommonMark list indentation is column-sensitive. The Markdown override therefore uses two spaces, matching MD007's configured `indent: 2`, so typed indentation, formatting, and linting agree.

Two trailing spaces are a **Markdown hard line break**, which Prettier preserves. Stripping them on save (the EditorConfig default for `trim_trailing_whitespace`) would make the editor and Prettier disagree: the editor would delete the break, Prettier would expect it. `trim_trailing_whitespace = false` for `[*.md]` keeps them. EditorConfig supports these properties and the `[*.md]` glob-section targeting [S07].

---

## 10. VS Code standard

Recommend two extensions (`.vscode/extensions.json`):

- `esbenp.prettier-vscode` — the default formatter for `md` / `json` / `jsonc` / `yaml`. It reads `.prettierrc`, respects `editor.formatOnSave`, and prefers a locally installed Prettier over its bundled copy [S10].
- `DavidAnson.vscode-markdownlint` — Markdown **diagnostics**. Rule violations surface as editor warnings; it reads `.markdownlint.json` [S11].

Note: the CLI adopt path delivers `.vscode/extensions.json` as a 9-extension superset shared with the python-tooling bundle — the two Markdown extensions above plus the seven Python-toolchain extensions documented in the [Python Tooling Standard](../python-tooling/README.md) §13. Markdown-only adopters receive (and may trim) that shared file; these two are the ones this standard requires.

### One-formatter-authority rule

Exactly one tool may mutate a file on save. Prettier formats on save; **markdownlint only diagnoses.** The markdownlint extension _can_ act as a fixer, but only via an explicit opt-in code action (`source.codeActionsOnSave` → `source.fixAll.markdownlint`); by default it does not fix and only reports warnings [S11]. This standard deliberately does **not** enable that code action, so the two tools never both mutate a file on save — Prettier is the sole formatter, markdownlint is diagnostics-only.

This repo's `.vscode/settings.json` `[markdown]` block (and the adjacent structured-text blocks):

```json
{
	"[markdown]": {
		"editor.defaultFormatter": "esbenp.prettier-vscode",
		"editor.formatOnSave": true
	},
	"[json]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
	"[jsonc]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
	"[yaml]": { "editor.defaultFormatter": "esbenp.prettier-vscode" }
}
```

Format-on-save is enabled (for Prettier) only on `[markdown]` — this standard's primary surface — while `[json]`/`[jsonc]`/`[yaml]` are formatted via CI or on demand. This asymmetry is deliberate, not an oversight: Markdown is edited most and benefits most from save-time formatting; the config files change rarely and are caught by the check contract (§3) and CI.

Policy decision: editor tooling must not create overlapping authorities for the same concern. Prettier is the format authority for these file types across VS Code, CLI, and CI; markdownlint is the diagnostics authority. There is no markdownlint fix-on-save code action in this standard.

Both authorities are CI-enforceable, neither advisory-only: markdownlint is authoritative over Markdown body structure (enforced via `lint-markdown.yml`), and Prettier is authoritative over physical formatting of every supported file (enforced via the opt-in `format.yml`; DEC-10).

---

## 11. CI reusable workflow

The linter half ships as a reusable workflow, `.github/workflows/lint-markdown.yml`. It runs `DavidAnson/markdownlint-cli2-action@v24` [S05], which executes on its own bundled Node 24 [S06] — so a consumer needs no committed Node project. Its `workflow_call` inputs:

- `globs` — newline-delimited glob(s) of Markdown to lint (default `**/*.md`). Passed explicitly because the action's own default glob is the non-recursive `*.{md,markdown}` [S06].
- `config` — path to a base config file; empty means no `--config` flag is passed, so the underlying `markdownlint-cli2` auto-discovers config from the caller's repo (its own `.markdownlint.json` / `.markdownlint-cli2.jsonc`) [S03].

Consumer opt-in (pin `@v5`):

```yaml
jobs:
  lint-markdown:
    uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v5
    with:
      globs: '**/*.md'
```

Pin `@v4` (the current major), **not** `@v1`: this workflow first ships in the locked `2.0.0` release, so no `uses:` ref should point at a tag that predates the workflow (see `meta/versioning.md` §"Consuming").

The linter is deliberately separate from the frontmatter-validation workflow (DEC-8): a frontmatter-only consumer never inherits a Node/markdownlint toolchain. Prettier now **also** ships a reusable workflow (`format.yml`, DEC-10) — dual-role and adopted opt-in via `format.caller.yml`; set `prettier: false` to defer enforcement (the whole job skips).

---

## 12. Agent instruction block

Copy this into `AGENTS.md` (or the canonical instruction source it points to) for repositories that adopt this standard. It is the Markdown/structured-text parallel to the Python Tooling Standard's agent block.

````markdown
# Markdown & Structured-Text Tooling

This repository follows the Markdown Tooling Standard. Prettier formats every file type it supports (`md`/`json`/`jsonc`/`yaml` here); markdownlint lints Markdown structure only. Do not introduce a competing formatter or linter.

## Fix pass

When changing Markdown, JSON, JSONC, or YAML, run the fix pass first:

```bash
npx prettier --write .
npx markdownlint-cli2 --fix "**/*.md"
```

## Check contract

Before considering work complete, run the non-mutating check:

```bash
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Do not claim completion if either command fails.

## Rules

- Prettier owns physical formatting. Do not fight its output or hand-format.
- markdownlint owns Markdown structure. Do not disable a rule to silence a warning — fix the Markdown.
- Do not edit `.prettierrc.json` or `.markdownlint.json` to bypass a check without a documented ADR exception.
````

---

## 13. Non-default tools

These tools are not part of the baseline unless a project-specific exception is documented:

- **PyMarkdown** — a separate Markdown linter that cannot read `.markdownlint.json` and models MD025 incompatibly with this repo's frontmatter model (DEC-3, §8).
- **remark-lint** — a different (remark/unified) Markdown linter; overlaps markdownlint and produces competing structure feedback.
- **dprint** — an alternative multi-language formatter; overlaps Prettier.
- **mdformat** — a Python Markdown formatter; overlaps Prettier on Markdown.
- **Vale** — a prose/style linter (a different concern from structural linting); add only when a project explicitly wants prose-style enforcement.

Policy decision: this is a **per-project add prohibition**, not a workstation uninstall order. A machine may carry any of these for other projects; the rule is simply not to add them to a repo that follows this standard, because overlapping tools produce contradictory feedback for coding agents.

---

## 14. Exceptions process

A project may deviate only when the exception is documented as a conformant ADR. Create or update a file under `docs/adr/`, using a zero-padded numeric sequence number for `NNNN`:

```text
docs/adr/adr-NNNN-markdown-tooling-exception.md
```

The ADR Standard ([`standards/adr/README.md`](../adr/README.md)) is the authority for the exact ADR shape — `id`, filename, frontmatter, and MADR section structure. Map the exception into MADR's required level-2 sections (Context and Problem Statement, Considered Options, Decision Outcome with a Consequences subsection).

Examples of valid exceptions: an existing project standardized on remark-lint; a docs pipeline that requires `proseWrap: always`; a repo that genuinely needs MD013 enforced. Examples of invalid exceptions: disabling a markdownlint rule to avoid fixing Markdown; swapping the formatter on style preference.

---

## 15. Update process / review cadence

Review this standard when:

- Prettier releases a version that changes default options or Markdown/JSON/YAML behavior materially.
- markdownlint adds or changes rules (the rule set is `default: true`, so a new rule lands enabled — re-verify it does not conflict with Prettier).
- `markdownlint-cli2-action` bumps its major version or bundled Node runtime.
- EditorConfig changes property semantics.
- The two VS Code extensions change formatter/diagnostic behavior materially.
- MADR changes its own `.markdownlint` config (the MD024 basis, §7).

Review cadence:

- Light review: quarterly.
- Full review: annually.
- Immediate review: after a toolchain-breaking change or an action version bump.

---

## 16. Source coverage map

| Section                           | Source IDs used                                 |
| --------------------------------- | ----------------------------------------------- |
| Purpose & scope                   | [S02], [S04], [S07]                             |
| Core contract                     | [S02], [S03], [S05]                             |
| Standard stack                    | [S01], [S02], [S03], [S04], [S05], [S06], [S07] |
| Published vs repo-local artifacts | [S03]                                           |
| Formatter — Prettier              | [S01], [S02]                                    |
| Linter — markdownlint             | [S08], [S09]                                    |
| Frontmatter coupling              | [S08]                                           |
| `.editorconfig`                   | [S07]                                           |
| VS Code standard                  | [S10], [S11]                                    |
| CI reusable workflow              | [S05], [S06]                                    |

---

## 17. Source register

| ID | Source | URL | What it supports | Last checked |
| --- | --- | --- | --- | --- |
| S01 | Prettier: Options | [https://prettier.io/docs/options](https://prettier.io/docs/options) | Prettier configuration options (`printWidth`, `proseWrap` incl. its `"preserve"` default and `"never"` value, `useTabs`, `tabWidth`, `endOfLine` `lf` default, quote/trailing-comma options, `overrides`, and the other options in the embedded config) | 2026-06-07 |
| S02 | Prettier: Configuration & CLI | [https://prettier.io/docs/configuration](https://prettier.io/docs/configuration) and [https://prettier.io/docs/cli](https://prettier.io/docs/cli) | Config discovery up the file tree, `.prettierrc.json` recognition, `overrides` (`files`/`options`), `prettier .` recursive file selection by extension, `.gitignore`/`.prettierignore` defaults, `node_modules` skip | 2026-06-07 |
| S03 | markdownlint-cli2 (DavidAnson) | [https://github.com/DavidAnson/markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2) | Config auto-discovery (`.markdownlint-cli2.jsonc` then `.markdownlint.json`), CLI globs, `gitignore` option, `--fix` in-place behavior | 2026-06-07 |
| S04 | markdownlint (DavidAnson) | [https://github.com/DavidAnson/markdownlint](https://github.com/DavidAnson/markdownlint) | Markdown-only linting; `default` rule sets the baseline for all rules; the markdownlint rule set (IDs MD001–MD060; 53 active rules in v0.40.0); config schema | 2026-06-07 |
| S05 | markdownlint-cli2-action: README | [https://github.com/DavidAnson/markdownlint-cli2-action](https://github.com/DavidAnson/markdownlint-cli2-action) | Action usage, `@v23` major-tag pinning, inputs (`globs`, `config`, `fix`), default glob `*.{md,markdown}` | 2026-06-07 |
| S06 | markdownlint-cli2-action: `action.yml` | [https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/main/action.yml](https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/main/action.yml) | `runs.using: node24` (the action's bundled Node 24 runtime) | 2026-06-07 |
| S07 | EditorConfig specification | [https://spec.editorconfig.org/](https://spec.editorconfig.org/) | `root`, `charset`, `end_of_line`, `indent_style`/`indent_size`, `insert_final_newline`, `trim_trailing_whitespace`, `[glob]` section matching | 2026-06-07 |
| S08 | markdownlint: `Rules.md` | [https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md) | MD001/003/004/009/010/013/024/025/029/030/032/041/043/048/049/050 behavior and parameters (`front_matter_title`, `headings`, style values) | 2026-06-07 |
| S09 | MADR 4.0: `.markdownlint.yml` | [https://github.com/adr/madr/blob/develop/.markdownlint.yml](https://github.com/adr/madr/blob/develop/.markdownlint.yml) | MADR's own config sets `MD024: false` (and `MD013: false`) — the basis for this repo's MD024 deviation | 2026-06-07 |
| S10 | Prettier VS Code extension | [https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode) | Acts as `editor.defaultFormatter` for md/json/yaml, respects `editor.formatOnSave`, reads `.prettierrc`, prefers local Prettier | 2026-06-07 |
| S11 | markdownlint VS Code extension | [https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) | Diagnostics-by-default (warnings), reads `.markdownlint.json`; fixing requires explicit opt-in (`source.fixAll.markdownlint` code action) | 2026-06-07 |

---

<!-- Citation reference-link definitions: every [Sxx] marker in the body and in the source coverage map resolves to the Source register (section 17). GFM cannot anchor individual table rows, so all citations jump to the section. -->

[S01]: #17-source-register
[S02]: #17-source-register
[S03]: #17-source-register
[S04]: #17-source-register
[S05]: #17-source-register
[S06]: #17-source-register
[S07]: #17-source-register
[S08]: #17-source-register
[S09]: #17-source-register
[S10]: #17-source-register
[S11]: #17-source-register
