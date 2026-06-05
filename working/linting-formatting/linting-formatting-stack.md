# Linting / Formatting Stack — Working Document

> Scratch/working doc (lives under `working/**`, excluded from frontmatter validation). Goal: pin down the **exact** linting + formatting stack required for (a) frontmatter validation to pass today, and (b) the upcoming ADR/MADR standard. Gather first, decide later. Status: **information-gathering**. No repo files changed yet.

---

## Decisions made (2026-06-04 session)

Recorded with trails so a future session inherits the reasoning, not just the verdict.

### DEC-1 — Target **MADR 4.0** (resolves D5 / O5)

- **Chosen:** the upcoming ADR standard targets **MADR 4.0** (upstream current, released 2024-09-17).
- **Rejected:** MADR 3.0 (what the repo's current templates/`standards/adr.md` informally follow). Reason: 4.0 is the upstream current release; the `source:` link in `standards/adr.md` (`adr.github.io/madr/`) already serves 4.0; and the repo's four templates already mirror 4.0's bare/minimal split.
- **Load-bearing assumption — NOW `verified`** (read `adr/madr` `@4.0.0`: changelog + all templates + `.markdownlint.yml`, 2026-06-04). The deltas are enumerated in §3.5 below. Severity downgrades `component-swap → config-tweak`: our **body structure already IS MADR 4.0** (identical section set and minimal subset). Remaining deltas are small.
  - **Process correction (mark, don't bury):** §3.1/§3.4 earlier tagged the repo "MADR 3.0-flavored." That was `inferred` and **wrong**. Per the 4.0.0 changelog, _Confirmation_, `decision-makers`, and the bare/minimal template split are all **4.0.0** additions — which the repo already uses. The repo was already ~4.0, not 3.0. Corrected here from primary source rather than after an objection.
- **Re-eval trigger:** MADR ships a 5.x with breaking section changes.

### DEC-2 — ADR Manager extension is an **optional convenience**, not a conformance target (resolves O6)

- **Chosen:** `stevenchen.vscode-adr-manager` is treated as an optional authoring aid. The standard is **not** shaped to satisfy it. Conflicts C1–C5 are therefore **non-blocking**.
- **Rejected:** conformance target (shaping filename/sections/metadata so the extension can list/round-trip our ADRs). Reasons: (a) it targets **MADR 2.1.2** — two majors behind our DEC-1 choice; (b) it is a **v0.1.8 prototype** (Bachelor-thesis output, README self-describes as "a prototype … aimed at generating feedback"); (c) it is **editor-only with no CLI**, so it can never serve as a CI gate regardless; (d) constraining a _standards-source-of-truth_ repo to one third-party editor inverts the dependency direction.
- **Evidence status:** "targets 2.1.2" `verified` (extension README) · "editor-only / no CLI" `verified` (`package.json` contributes only webview commands) · "title-case + required-section checks exist" `verified` (`titleCase`/section strings present in `dist/extension.js`) · "stale/prototype" `verified` (engine target `vscode ^1.67.0` ≈ April 2022, v0.1.8, repo `adr/vscode-adr-manager`). The C1 "leading-digit filename" detail stays `inferred` (README prose; minified regex not isolated) — moot now that the extension is demoted.
- **Residual (accepted limitation):** the extension will not auto-list our `adr-NNNN-…` files (its recognition wants a leading digit), and won't parse our canonical frontmatter. Acceptable — it's a convenience, not a gate.
- **Re-eval trigger:** the extension (or another MADR tool) ships **MADR 4 support + a CLI** usable in CI. At that point reconsider as an optional CI lint, not a conformance target.

> **Knock-on for the filename question (was O4/D4):** with the extension demoted, the filename driver is no longer "match the extension." It becomes "match **upstream MADR 4**," whose templates use `NNNN-title.md` (no `adr-` prefix) — which _also_ differs from our current `adr-NNNN-short-title.md`. So O4 survives, but reframed: **align our filename to MADR 4 vs keep the `adr-` prefix.** Not decided yet.

### DEC-3 — Stack-B linter is **markdownlint-cli2** (Node, via `npx`), not PyMarkdown (resolves O1)

- **Chosen:** wire Stack B with **`markdownlint-cli2`** — the DavidAnson reference engine MADR itself uses — invoked via `npx` in a dedicated CI step (and a documented local command). No committed Node project required.
- **Rejected — PyMarkdown (Python, `pymarkdownlnt`):** despite avoiding a Node runtime, it **does not read `.markdownlint.json`** (uses `.pymarkdown` / `pyproject.toml [tool.pymarkdown]`) and implements **MD025 differently** (front-matter title is a _key name_ that forces all headings to ≥ H2). Decisive reason: **this repo publishes `.markdownlint.json` as part of the standard.** Linting our own repo with an engine that can't consume that artifact — and whose MD025 model clashes with our "frontmatter `title:` + body `# H1`" docs — breaks config-artifact integrity and parity with consumers (and MADR).
- **Rejected — `mdformat`:** it's a _formatter_, not a linter; it answers **D2**, not O1. (`inferred` from its category; not load-bearing here.)
- **Evidence (all `verified`, primary source, 2026-06-04):**
  - `markdownlint-cli2` reads `.markdownlint.json` natively (its README's config-file list). → zero config migration; the published config _is_ the linter input.
  - MADR 4.0 ships a markdownlint config (`.markdownlint.yml`) → same engine, same rule IDs, same MD025/MD024 semantics our `.markdownlint.json` was authored against.
  - PyMarkdown MD024 supports `siblings_only` ✅ but MD025 `front_matter_title` is a key-name model (per its `rule_md025.md`), **not** the DavidAnson regex/`""`-disables model.
- **Counter-case (surfaced, not deferred):** this puts a **Node runtime in the local dev loop** — every other repo command is `uv run …`; markdown lint would be `npx markdownlint-cli2 …`. Real ergonomic seam in a pure-Python/uv repo, and bare `npx` floats the version. Mitigations: pin `markdownlint-cli2@<version>` in the CI invocation (or add a minimal `package.json` devDep + lockfile if we want full reproducibility); treat local lint as optional since the editor already runs it. Accepted because the alternative is worse _for a standards repo_ (config the repo can't dogfood).
- **Sub-decisions still open (within "yes, markdownlint-cli2"):**
  - **How to pin:** `npx markdownlint-cli2@X` (simple) vs committed `package.json`+lockfile (reproducible, adds a Node lockfile to the tree) vs pre-commit mirror.
  - **Consumer inheritance:** add markdown lint as a **separate** step / reusable workflow so consumers opt in to Node, rather than inheriting it through the existing `validate-markdown-frontmatter.yml` (which installs only the uv tool). GitHub-hosted runners ship Node, so an opt-in `npx` step needs no consumer Node setup.
- **Re-eval trigger:** PyMarkdown adds native `.markdownlint.json` ingestion _and_ DavidAnson- compatible MD025, **or** the repo gains a Node toolchain for other reasons (then a committed devDep is the natural pin).

---

## 0. The core distinction (read this first)

"Linting/formatting for frontmatter" is really **two independent stacks** that are easy to conflate. Keeping them separate is the single most important framing for the decisions below.

| Stack | What it checks | Engine | Enforced today? |
| --- | --- | --- | --- |
| **A. Frontmatter validation** | The YAML metadata block: required keys, enums, date/id patterns, `additionalProperties:false` | Python (`jsonschema` + `pyyaml`) | ✅ Yes — CI + local |
| **B. Markdown lint/format** | The Markdown _body_: heading levels, list style, line rules, whitespace | `.markdownlint.json` config exists | ❌ **No** — config present, never executed |

Stack A is fully wired and green. Stack B is a **config file with no runner** — there is no CI step, no pre-commit hook, and no Node toolchain in the repo that invokes markdownlint. Today, "validation passes" means **only Stack A**. Stack B is latent.

The ADR/MADR work pulls on **both** stacks plus a **third, semantic** layer (MADR body structure: required sections, chosen-option-in-considered-options), which neither stack currently covers.

---

## 1. Stack A — Frontmatter validation (current, working)

### Runtime dependencies (what must be installed to validate)

| Dependency | Pin (`pyproject.toml`) | Role |
| --- | --- | --- |
| Python | `requires-python = ">=3.11"` | Floor; CI matrix tests `3.11`, `3.13`, `3.14` |
| `jsonschema` | `>=4.23.0` | `Draft202012Validator` — validates the parsed mapping |
| `pyyaml` | `>=6.0.2` | `yaml.safe_load` parses the frontmatter block |

That is the **entire** runtime closure. No Node, no external binaries.

### Files that make up Stack A

| File | Role |
| --- | --- |
| `tools/validate_frontmatter.py` | The validator; exposed as console script `validate-frontmatter` |
| `schemas/markdown-frontmatter.schema.json` | The contract (JSON Schema Draft 2020-12) |
| `.project-standards.yml` | Declares `schema`, `required`, `include`, `exclude` globs |
| `.github/workflows/validate-markdown-frontmatter.yml` | Runtime CI gate + reusable workflow for consumers |

### How it runs

```bash
uv run validate-frontmatter --config .project-standards.yml
```

- **Schema resolution order:** `--schema` path > config `markdown.frontmatter.schema` (bundled name or path) > bundled `markdown-frontmatter`.
- **Path selection:** explicit files/`--glob` win; else config `include`; else all `**/*.md`. `exclude` always applied via `fnmatchcase` on posix paths (deliberately _not_ `Path.glob`, to dodge the 3.12→3.13 `**` semantics change — there's a regression test pinning this, which is why the CI matrix brackets 3.13/3.14).
- **Exit codes:** `0` ok / none matched · `1` validation failure · `2` config/schema error.
- **Date coercion:** unquoted YAML dates parse to `datetime.date`; `_coerce_dates` converts to ISO strings before schema check, so authors can write quoted or unquoted dates.

### What the schema actually enforces (the "must pass" rules)

- **11 required keys:** `schema_version, id, title, description, doc_type, status, created, updated, tags, aliases, related`.
- `additionalProperties: false` at top level — unknown keys **fail**. Project-specific data must go under the sanctioned objects `project` / `x_project` / `publish`.
- Enums: `schema_version ∈ {1.0, 1.1}`, `doc_type` (14 values incl. `adr`), `status` (7 values), `consumer`, `confidence`, `visibility`.
- Patterns: `id ^[a-z0-9][a-z0-9._-]*$`; `tags` items `^[a-z0-9][a-z0-9-]*$`; dates `^\d{4}-\d{2}-\d{2}$`.
- `uniqueItems` on all arrays.

### Conventions the validator does NOT enforce (authoring rules only)

These are in `standards/markdown-frontmatter.md` but **not** machine-checked — relevant because a future "formatter" could enforce them, and because they're easy to assume are gated when they aren't:

- **Canonical key order** (24-key ordering) — documented, not validated.
- **String values MUST be quoted** — validator checks semantics, not quote style.
- **Block-style non-empty lists / `[]` empty lists** — style, not validated.
- `description` one-line / ≤280 chars / no Markdown — convention only.
- Link form (repo-root-relative paths) — convention only; planned to harden in `2.0.0`.

> **Decision seed:** several "rules" in the standard (key order, quoting, list style) are exactly what a YAML/Markdown _formatter_ would normalize. If we want them enforced rather than merely documented, that's a Stack-B (or new) tool, not the schema.

### Stack A's own dev/test gate (separate from runtime)

`.github/workflows/tests.yml` gates the validator's _code_ (never inherited by consumers):

| Tool      | Pin         | Config                                                    |
| --------- | ----------- | --------------------------------------------------------- |
| `pytest`  | `>=8.3.0`   | `testpaths=["tests"]`, `-ra -q`                           |
| `ruff`    | `>=0.9.0`   | `select = [E,F,I,B,UP,SIM]`, line-length 88, target py311 |
| `pyright` | `>=1.1.390` | `typeCheckingMode = "strict"`, include `tools`,`tests`    |

Local gate (from `AGENTS.md`): `uv run pytest && uv run ruff check . && uv run pyright`.

---

## 2. Stack B — Markdown lint/format (config present, NOT enforced)

### What exists

`.markdownlint.json` (tracked):

```json
{
	"MD013": false, // no line-length limit
	"MD024": { "siblings_only": true }, // allow dup headings if not siblings
	"MD025": { "front_matter_title": "" } // frontmatter `title:` counts as the H1
}
```

These three choices are **frontmatter/ADR-aware**:

- `MD025 front_matter_title: ""` **disables** front-matter-title detection (verified against DavidAnson `doc/md025.md`: _"To disable the use of front matter by this rule, specify `""`"_). With the rule's **default** regex (`^\s*title\s*[:=]`), a doc carrying both a frontmatter `title:` **and** a body `# H1` would be seen as _two_ titles and **fail** MD025 — so setting `""` is load-bearing: it makes the body `# H1` the single recognized title. _(Correction: an earlier draft of this file said the rule makes the frontmatter `title:` "count as the H1" — that's the inverted mechanism. Net effect — managed docs don't trip MD025 — is the same; corrected here from primary source.)_
- `MD024 siblings_only` is needed by MADR: option names repeat under both _Considered Options_ and _Pros and Cons of the Options_, and "Good, because / Bad, because" patterns recur. Siblings rule lets non-adjacent duplicate headings coexist.
- `MD013 false` avoids fighting long prose/table lines (the standards docs have wide tables).

### What's missing (the gap)

- **No runner.** `grep` finds zero references to `markdownlint` in any workflow, hook, or `package.json`. The repo has **no Node toolchain at all** (no `package.json`, `package-lock.json`, `node_modules`, `.nvmrc`).
- So `.markdownlint.json` is currently consumed **only** by an editor (the markdownlint VS Code extension), if a contributor happens to have it. It is **advisory**, not gating.

### Why this matters for the decision

Upstream MADR **uses markdownlint** as its Markdown linter (per `github.com/adr/madr`: _"MADR uses markdownlint as Linter for Markdown files"_). So adopting markdownlint-in-CI would:

1. Align us with upstream MADR tooling, and
2. Finally make Stack B real.

But it introduces a **Node toolchain** into a so-far pure-Python repo — a real cost (see §4 options, incl. the Python-native `mdformat`/`pymarkdown` alternatives that avoid Node).

---

## 3. The ADR / MADR dimension

### 3.1 What the project already ships (already ~MADR 4.0 — see §3.5)

- `standards/adr.md` — adopts **MADR** as the body format, layered on canonical frontmatter.
- `examples/adr.example.md` — a fully-worked, schema-valid ADR.
- 4 templates: `templates/adr.md`, `adr-minimal.md`, `adr-bare.md`, `adr-bare-minimal.md`.

The body structure used (Context and Problem Statement / Decision Drivers / Considered Options / Decision Outcome → Consequences + Confirmation / Pros and Cons / More Information, with "Good/Neutral/Bad, because" bullets) is **MADR 3.0**. The metadata is mapped onto canonical frontmatter rather than MADR-native keys:

| MADR field                     | Project's canonical home                     |
| ------------------------------ | -------------------------------------------- |
| `status` (proposed/accepted/…) | top-level `status` enum (mapped via a table) |
| `date`                         | `created` / `updated`                        |
| `decision-makers`              | `project.decision_makers`                    |
| `consulted`                    | `project.consulted`                          |
| `informed`                     | `project.informed`                           |

### 3.2 The installed "ADR Manager" — what it actually is

`stevenchen.vscode-adr-manager-0.1.8` (VS Code extension; `adrManager.*` settings).

- **Based on MADR `2.1.2`** (its own README) — i.e. the **pre-frontmatter** MADR generation, though its `dist` straddles `deciders` _and_ `decision-makers`.
- **ADR directory** defaults to `docs/decisions` (matches `standards/adr.md`). ✅
- It does its **own linting** in-editor (the `adrManager.showDiagnostics` setting):
  - missing title header / missing required sub-headers (Context and Problem Statement, Considered Options, Decision Outcome)
  - empty required section
  - **headings/subheadings not in Title Case**
  - **chosen option not present in the Considered Options list**
- It only _recognizes_ a file as an ADR if the **filename** matches MADR's convention: `NNNN{-,_}…title.md` — **starts with the zero-padded number**, kebab/snake, no special chars.

### 3.3 Conflicts to resolve (the heart of the decision)

| # | Project standard | ADR Manager extension | Tension |
| --- | --- | --- | --- |
| C1 **Filename** | `adr-NNNN-short-title.md` (prefixed `adr-`) | regex requires name to **start with a digit** (`NNNN-…`) | Project ADRs **won't be listed/parsed** by the extension. Either drop the `adr-` filename prefix, or accept the extension can't manage our files. |
| C2 **Metadata model** | canonical YAML frontmatter (`doc_type`, mapped `status` enum, `project.*` roles) | MADR-native inline/`2.1.2` metadata (`status:`, `date:`, `deciders`) | Extension's webview round-trip won't understand our frontmatter; may flag/garble on edit. |
| C3 **MADR version** | MADR **3.0** body (Confirmation, decision-makers, Good/Bad-because) | built for MADR **2.1.2** | Section set & metadata keys differ; "no tooling supports MADR 3.0.0" per adr.github.io. |
| C4 **Title-case headings** | our headings are sentence-style ("Context and Problem Statement" ok; but e.g. "Pros and Cons of the Options") | extension flags non-Title-Case headings | Cosmetic but will produce editor diagnostics; also a markdownlint MD003/heading concern if we ever add a case rule. |
| C5 **Enforcement locus** | CI (Python validator) | editor-only diagnostics (not CI) | The extension's MADR-structure checks are **not** reproducible in CI; if we want body-structure gating it must be built/added separately. |

> **Framing for the decision:** the extension is a **convenience authoring/visualization tool**, not an enforcement gate. The project's enforcement gate is the Python validator + (future) markdownlint. These can coexist **if** we either (a) align our filename/section conventions closely enough that the extension still recognizes our ADRs, or (b) explicitly treat the extension as optional and not a conformance target.

### 3.4 MADR version cheat-sheet (for accuracy)

Corrected from the `adr/madr` CHANGELOG (primary source):

- **2.1.x** — no YAML frontmatter; metadata inline (`Deciders`, `Status`). What the installed extension targets.
- **3.0.0** (2022-10-09) — _added_ optional YAML frontmatter; added a **"Validation"** section and `consulted`/`informed`; merged Positive/Negative Consequences into **"Consequences"** with the "Good/Neutral/Bad, because" grammar.
- **4.0.0** (2024-09-17) — renamed **"Validation" → "Confirmation"** (sub-section of Decision Outcome); renamed **"Deciders" → `decision-makers`**; `status` must be a quoted string with **no link** (identifier only); added the **bare/minimal** template split; placeholders are one-liners. **These 4.0 features are exactly what the repo already uses** — hence the repo is ~4.0, not 3.0.

### 3.5 MADR 4.0 conformance deltas (verified against `adr/madr@4.0.0`)

Source read 2026-06-04: changelog + `adr-template.md`, `adr-template-minimal.md`, `adr-template-bare.md`, `adr-template-bare-minimal.md`, `.markdownlint.yml`.

**Body structure — already conformant, no change needed.** MADR 4.0's section set is: Context and Problem Statement (req) · Decision Drivers (opt) · Considered Options (req) · Decision Outcome (req) → ### Consequences (opt) + ### Confirmation (opt) · Pros and Cons of the Options (opt) → per-option Good/Neutral/Bad · More Information (opt). Minimal = Context / Considered Options / Decision Outcome / ### Consequences. **Our `templates/adr.md` and `adr-minimal.md` match these exactly.** ✅

**Deltas, graded by severity (none is `re-architecture`):**

| # | Item | MADR 4.0 (upstream) | Our repo | Verdict / severity |
| --- | --- | --- | --- | --- |
| Δ1 | **Metadata model** | native frontmatter: `status` `date` `decision-makers` `consulted` `informed` | canonical frontmatter + map to `status` enum, `created`/`updated`, `project.{decision_makers,consulted,informed}` | **Intentional divergence — keep.** Documented mapping in `standards/adr.md`. Not a delta to "fix". All 5 native fields are covered by the mapping. |
| Δ2 | **`status` value** | free MADR vocab, quoted, _no link_ (identifier only) | canonical `status` enum; MADR word optionally in body prose; supersession via `superseded_by` (identifier) | **Conformant in spirit.** 4.0's "no link in status" matches our identifier-only `superseded_by`. Keep. |
| Δ3 | **markdownlint `MD024`** | `MD024: false` (fully off) | `MD024: { siblings_only: true }` | `config-tweak` / **decide in O1.** Ours is stricter; could flag repeated _sibling_ headings (e.g. "Examples", per-option blocks) that MADR allows. Consider matching `false`, or keep stricter deliberately. |
| Δ4 | **markdownlint `MD025`** | not set (MADR frontmatter has no `title:`) | `MD025: { front_matter_title: "" }` | **Necessary divergence — keep.** Our frontmatter _does_ carry `title:`; the rule prevents a false "multiple H1". |
| Δ5 | **One-sentence-per-line** | MADR's stated reason for `MD013: false` | we set `MD013: false` too, but no SPL authoring convention | `config-tweak` / optional. Adopt SPL convention or not — independent of passing. |
| Δ6 | **Filename** | `NNNN-title.md` (e.g. `0000-use-madr.md`) | `adr-NNNN-short-title.md` | `config-tweak` / **= O4.** Open. |
| Δ7 | **Name expansion** | "Markdown **Architectural** Decision Records" (4.0 reverted "Any") | `standards/adr.md` says "Markdown **Any** Decision Records" | trivial doc-text fix. |
| Δ8 | **Bare-template placeholders** | `<!-- … -->` HTML comments | empty sections + bullet stubs | cosmetic; ours is arguably cleaner. Optional alignment. |

**Net:** adopting MADR 4.0 is **not** a re-architecture. Body/templates already conform; the work is a handful of `config-tweak`/doc edits (Δ3, Δ5–Δ8) plus _preserving_ the two deliberate divergences (Δ1, Δ4). DEC-1's assumption is discharged.

---

## 4. Decisions to make (with the options on the table)

### D1 — ✅ RESOLVED: engine = `markdownlint-cli2` (Node, via `npx`). See **DEC-3** for the full trail.

Options as evaluated (kept for the record):

- **Option A — markdownlint-cli2 (Node). ✅ CHOSEN.** Reference engine MADR uses; reads `.markdownlint.json` natively (the artifact we publish); 100% rule/MD025 parity. Cost: Node in the local dev loop (mitigated — runner-provided, editor already lints).
- **Option B — `pymarkdownlnt` (Python). ✗ Rejected.** No `.markdownlint.json` ingestion; divergent MD025 model; breaks config-artifact integrity for a standards repo. (`mdformat` is a _formatter_ → belongs to **D2**, not here.)
- **Option C — leave editor-only. ✗ Rejected** (implicitly, by choosing to wire CI): keeps Stack B advisory and lets managed/ADR Markdown drift.

Remaining sub-decisions (pin strategy, consumer opt-in) are listed under DEC-3.

### D2 — Frontmatter style rules: enforce? and how? (O2 — researched 2026-06-04)

Three documented-but-unenforced rules are in scope: **canonical key order** (the 24-key order), **string values quoted**, **block-style non-empty lists / `[]` empty**.

**Mechanism survey (primary sources read):**

| Mechanism | Key order | Quoting | List style | New dep / cost | Verdict |
| --- | --- | --- | --- | --- | --- |
| **yamllint** | ❌ alphabetical only (`key-ordering` can't do a custom order) | ✅ `quoted-strings: {required: true}` | partial | new dep, **GPLv3** in an Apache-2.0 repo | **Reject** — misses the main gap (custom order); license friction |
| **mdformat + `mdformat-frontmatter`** | ❌ (plugin explicitly _passes frontmatter through_ untouched) | ❌ | ❌ | Node-free, but it's a _body_ formatter | **Reject for frontmatter**; revisit only for body formatting |
| **Prettier** | ❌ (reorders nothing) | ~ | ~ | Node | Reject |
| **Extend our Python validator (lint pass)** | ✅ `list(meta.keys())` vs canonical (safe_load preserves order) | ✅ via `yaml.compose()` `ScalarNode.style` | ✅ via `SequenceNode.flow_style` | **zero new deps** (pyyaml already in) | **Recommended** |

**Verified capability (runtime observation, not inference):** `yaml.compose()` exposes `ScalarNode.style` (`None` = unquoted, `'`/`"` = quoted) and `SequenceNode.flow_style` (`True` = inline `[]`, `False` = block); `yaml.safe_load()` returns an insertion-ordered dict. → All three rules are detectable inside the validator with **only pyyaml**, no new dependency, no GPL entanglement, and it **dogfoods** the published tool.

**Preliminary recommendation (pending your call — this has a policy axis, not just a mechanism axis):** add an **opt-in style-lint pass** to the validator (config flag, e.g. `markdown.frontmatter.style: strict`, default **off**) that checks key order + quoting + list style. **Lint, not auto-format** (flag violations; don't rewrite authored files).

**Counter-cases / consequences to weigh BEFORE locking:**

- 🔴 **Versioning.** Per `standards/versioning.md`, _tightening what passes is a MAJOR bump._ Turning these conventions into hard checks would fail some previously-valid docs → a `2.0.0` unless it's **opt-in/default-off** (additive → minor). The default-off flag is what keeps it a minor; that's the crux of the recommendation, not a footnote.
- 🟡 **Owned code + edge cases.** "All strings quoted" via node styles must special-case values YAML parses as non-strings (unquoted dates → `date` objects; `schema_version: 1.1` unquoted → float). The validator already coerces dates; a style pass needs to flag _unquoted_ identifier- like scalars specifically. More tests we own vs. delegating to a maintained linter.
- 🟢 **"Do nothing" is legitimate.** The standard already labels these "authoring rules," not machine-enforced. Keeping them as convention is a valid choice (less churn, the schema stays the sole gate).

Decision still yours: **(a)** enforce via opt-in validator lint pass _(recommended)_ · **(b)** enforce via yamllint for quoting only + leave order as convention · **(c)** keep all three as documented convention (status quo).

#### DEC-4 — O2 resolved: keep all three as documented **convention** (option c)

- **Chosen (you, 2026-06-04):** key order, quoting, list style stay **authoring conventions** in `standards/markdown-frontmatter.md`. The **schema remains the sole CI gate.** No new lint pass, no new dependency.
- **Rejected:** (a) opt-in validator lint pass and (b) yamllint-for-quoting — to avoid added owned-code/test surface, sidestep the major-bump/opt-in-flag complexity, and keep the validator's remit strictly _schema validity_, not style.
- **Re-eval trigger:** if real-world frontmatter drift (mis-ordered keys, unquoted scalars) becomes recurring in managed docs, revisit (a) — the capability is verified and ready (pyyaml node styles), so it's a low-cost future add.

### D3 — ADR body-structure enforcement: CI or editor-only?

The MADR section-presence + chosen-option checks live only in the extension (editor, now demoted by DEC-2). Question (O3): make them a CI gate, or leave to editor + review?

**Build-vs-adopt (primary sources, 2026-06-04):** there is **no off-the-shelf CI validator for plain MADR 4.0** to inherit:

- Upstream `adr/madr` ships **no semantic validator** — markdownlint for _style_ only; it's a template project, not a checker.
- `zircote/structured-madr` has a GitHub Action validator + JSON Schema, but for **Structured MADR** — a heavier variant with required _audit_/_risk_ sections. Adopting it = adopting that format, which **conflicts with DEC-1** (plain MADR 4.0).
- `log4brains` is an ADR _publisher_ (static site), not a section validator.

→ Enforcing ADR body structure in CI means **we build it** (extend the validator), since adopting means taking on a mismatched format.

**Options:**

- **(a) Editor + review (status quo, recommended).** Stack A stays a _frontmatter_ validator; markdownlint-cli2 (DEC-3) handles style; ADR section presence is caught by the editor extension's diagnostics + PR review. Consistent with DEC-4's lightweight lean (schema is the sole semantic gate; don't grow the validator's remit).
- **(b) Minimal opt-in validator check.** Default-off flag; for `doc_type: adr` only, assert the **3 truly-required** MADR sections exist (`## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`). Respects MADR's optional-sections philosophy; default-off keeps it a minor bump. More owned code + tests.
- **(c) Full structural check** (chosen-option ∈ considered options, etc.). Highest fidelity; most code; risks fighting MADR's "short → large record" flexibility. Not recommended.

**Counter-case to (a):** without a CI gate, a malformed ADR (e.g., missing Decision Outcome) can merge. Mitigations: the schema already pins `doc_type: adr`; the standard documents the required sections; the editor extension + reviewers catch structure. If structural drift becomes real, (b) is the ready escalation — same default-off pattern as DEC-4.

**Recommendation:** **(a)**, escalate to **(b)** only if drift appears. (Your call.)

#### DEC-5 — O3 resolved: **minimal opt-in validator section-check (option b)**

- **Chosen (you, 2026-06-04):** extend the validator with a **default-off** check that — for `doc_type: adr` only — asserts the **3 MADR-required `##` sections** are present: `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`.
- **Rejected:** (a) editor+review only (a malformed ADR could merge with no CI gate); (c) full structural check incl. chosen-option ∈ considered-options (most code; fights MADR's short→large flexibility).
- **Scope guardrails (verified against MADR 4.0):** check ONLY the 3 required sections — `Consequences`, `Confirmation`, `Decision Drivers`, `Pros and Cons`, `More Information` are **optional** in MADR 4.0 and must NOT be required. Exact title-case heading match.
- **Build, not adopt** (per D3 survey): no off-the-shelf plain-MADR-4.0 validator fits; this is a small addition to our own validator (it already has the file text).
- **Versioning:** new config key + default-off = **additive → minor** bump. Flipping it to default-on or required later = major.
- **Implementation notes (future — not built this session):** new config namespace (body-level, not frontmatter), e.g. `markdown.adr.require_sections: true` (default `false`); scan headings when `doc_type == adr` and flag on; emit per-missing-section errors; add tests + CHANGELOG + `standards/adr.md` note. Keep it under a _separate_ config key from `markdown.frontmatter.*` so the validator's frontmatter remit stays conceptually distinct.
- **Re-eval trigger:** false-positives on legitimate short ADRs → loosen; or demand for chosen-option validation → consider (c).

#### DEC-6 — O4 resolved: **hybrid filename/id (option b)**

- **Chosen (you, 2026-06-04):** ADR **filename** follows MADR 4 — `NNNN-short-title.md` (in `docs/decisions/`); ADR **id** keeps the prefix — `adr-NNNN-short-title` — for self- identification in cross-repo `related:` graphs.
- **Rejected:** (a) full align (loses `adr-` id self-identification); (c) status quo (filename diverges from upstream MADR).
- **Consequence — documented exception required:** this **breaks the current "filename == id" rule.** ADRs become the sanctioned exception (id is `adr-`-prefixed; filename is not).
- **Implementation notes (future — not edited this session):**
  - `standards/adr.md`: change filename convention to `NNNN-short-title.md`; keep `id: adr-NNNN-short-title`; add an explicit "ADRs are the one exception to filename==id, because the id carries `adr-` for global disambiguation while the filename follows MADR" note.
  - `standards/adr.md` directory tree: `adr-0001-…md` → `0001-…md` (and `0002-…`).
  - Templates: keep `id: 'adr-0000-short-title'`; add a filename-guidance comment (`save as 0000-short-title.md`).
  - `examples/adr.example.md`: `id` stays `adr-0001-…` (its filename is illustrative, unaffected).
- **Versioning:** ships with the (new, additive) ADR standard → minor; the filename==id change scopes to ADRs only, doesn't touch existing doc types.
- **Re-eval trigger:** if the filename≠id split causes tooling/author confusion, revisit (a).

#### DEC-7 — S1 resolved: CI uses **`markdownlint-cli2-action@v23`** (refines DEC-3)

- **Chosen (2026-06-04):** in CI, run **`DavidAnson/markdownlint-cli2-action@v23`** with `globs: '**/*.md'`. Verified: it ships its own Node runtime (`runs: node24`), **auto-reads the repo's `.markdownlint.json`**, and pins by major tag — **no committed `package.json`/lockfile**. This refines DEC-3's "npx step" to the official action (cleaner, pinned, cached).
  - Local (optional): `npx markdownlint-cli2 "**/*.md"` — convenience only; the editor already lints.
- **Rejected:** committed `package.json`+lockfile (adds Node-project files to a Python+config repo, muddies identity/packaging, no gain the action lacks); pre-commit mirror (repo has no pre-commit framework — not worth introducing one).
- **Consistency:** matches the repo's existing major-tag action pins (`actions/checkout@v6`, `astral-sh/setup-uv@v7`). Add the `github-actions` ecosystem to Dependabot to bump `@v23`.
- **Re-eval trigger:** need immutable pins → switch action refs to full SHAs.

#### DEC-8 — S2 resolved: **separate opt-in reusable workflow** `lint-markdown.yml`

- **Chosen (2026-06-04):** add a **second** reusable workflow `.github/workflows/lint-markdown.yml`, structured like `validate-markdown-frontmatter.yml` (self-runs on push/PR for this repo **+** `workflow_call` for consumers). Consumers **opt in** via `uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v1`; it lints the caller repo's Markdown against the caller's `.markdownlint.json` (seeded from our published config).
- **Rejected:** folding markdown lint into the existing frontmatter workflow — would force Node lint + our body-style rules on **frontmatter-only** consumers. Keeping them separate preserves the §0 two-stacks separation and lets each be adopted independently.
- **Versioning:** new reusable workflow = additive → minor; it joins the versioned shipped surface (standard + schema + validator + workflow**s**).
- **Re-eval trigger:** if essentially all consumers adopt both, consider a combined umbrella workflow that calls both — without removing the standalone ones.

### D4 — ADR filename + id convention (O4)

The extension driver is gone (DEC-2). The live tension is **upstream MADR-4 alignment** vs **cross-repo id clarity**. This is **greenfield** — the ADR standard isn't shipped and no consumer has ADRs yet, so there is **no migration cost** either way. Decide now while it's free.

**Facts:**

- MADR 4.0 filename: `NNNN-title.md` (e.g. `0000-use-madr.md`) — no prefix; lives in `docs/decisions/`.
- Our `standards/adr.md` today: filename `adr-NNNN-short-title.md`, `id: adr-NNNN-short-title`, rule "**filename matches the id**".
- Schema `id` pattern `^[a-z0-9][a-z0-9._-]*$` accepts **both** `0001-…` and `adr-0001-…`. No schema change needed for either choice.

**Trade-off:**

|  | Align to MADR 4 (`NNNN-title.md`) | Keep `adr-` prefix |
| --- | --- | --- |
| Upstream familiarity | ✅ matches MADR/tooling | ✗ diverges (Δ6) |
| Self-identifying in a flat list / grep | ✗ relies on `docs/decisions/` dir for context | ✅ `ls adr-*`, greppable |
| `id` clarity in cross-repo `related:` refs | ✗ bare `0001-…` is ambiguous globally | ✅ `adr-0001-…` is self-describing |
| Collision with other `NNNN-` numbered files | possible (if a repo numbers other docs) | avoided |

**Three coherent options:**

- **(a) Full align:** filename `NNNN-title.md`, `id: NNNN-title`. Pure MADR; keeps "filename == id".
- **(b) Hybrid:** filename `NNNN-title.md` (MADR-aligned) **but** `id: adr-NNNN-title` (self-identifying global id). Cost: breaks the "filename == id" rule → needs a documented exception for ADRs.
- **(c) Status quo:** filename + id both `adr-NNNN-title`. Keeps "filename == id"; diverges from upstream filename (Δ6 stays).

**Lean:** DEC-1 chose upstream alignment and IDs are load-bearing in this repo's cross-doc `related:` model — which points at **(b) hybrid** (MADR filename, `adr-` id). But it adds a filename≠id exception. If "filename == id" simplicity matters more, **(c)** is the low-friction keep. **(a)** is purest-MADR but gives up the id self-identification the repo leans on. Your call.

### D5 — ✅ RESOLVED: target MADR 4.0 (see DEC-1)

Remaining work: enumerate the 3.0→4.0 section/metadata deltas and apply them to `standards/adr.md`, the 4 templates, and `examples/adr.example.md`.

---

## 5. Dependency / requirements summary

### Already required (installed, working)

- Python ≥3.11; `uv` (runner); `jsonschema>=4.23.0`; `pyyaml>=6.0.2`.
- Dev: `pytest>=8.3.0`, `ruff>=0.9.0`, `pyright>=1.1.390`.

### Potentially required (pending decisions)

| If we choose… | New dependency | Toolchain added |
| --- | --- | --- |
| markdownlint in CI (D1-A) | `markdownlint-cli2` | **Node** (new) |
| Python-native lint (D1-B) | `pymarkdownlnt` or `mdformat` | none (uv) |
| ADR structure in CI (D3) | _(none — extend our validator)_ | none |
| Key-order/quote formatting (D2) | custom tool _(none off-the-shelf)_ | none |

### Reference material gathered

- Upstream MADR repo (uses markdownlint): `https://github.com/adr/madr`
- MADR docs / version notes: `https://adr.github.io/madr/`, releases page (2.1.2 → 3.0 → 4.0)
- Installed extension: `stevenchen.vscode-adr-manager-0.1.8`, MADR 2.1.2, dir `docs/decisions`
- Project sources of truth: `standards/adr.md`, `standards/markdown-frontmatter.md`, `schemas/markdown-frontmatter.schema.json`, `.project-standards.yml`, `.markdownlint.json`

---

## 6. Question ledger

All six original questions are resolved (2026-06-04):

| Q      | Resolution                                     | Trail |
| ------ | ---------------------------------------------- | ----- |
| **O1** | markdownlint-cli2 (Node, `npx`)                | DEC-3 |
| **O2** | keep frontmatter style as convention           | DEC-4 |
| **O3** | minimal opt-in validator section-check         | DEC-5 |
| **O4** | hybrid filename/id (MADR filename + `adr-` id) | DEC-6 |
| **O5** | MADR 4.0                                       | DEC-1 |
| **O6** | extension = optional convenience               | DEC-2 |

### Sub-decisions — RESOLVED

- **S1** ✅ → CI uses `markdownlint-cli2-action@v23`; no committed Node project (DEC-7).
- **S2** ✅ → separate opt-in reusable workflow `lint-markdown.yml` (DEC-8).

**Nothing left open.** All eight decisions (DEC-1…DEC-8) are made and trailed.

### Implementation backlog (decisions made; edits NOT yet applied — still gather/decide mode)

- DEC-1/§3.5: apply 4.0 config-tweaks — `.markdownlint.json` MD024 (Δ3), "Any"→"Architectural" doc text (Δ7), optional SPL/bare-placeholder alignment (Δ5/Δ8).
- DEC-3 + DEC-7: add `.github/workflows/lint-markdown.yml` using `markdownlint-cli2-action@v23` (self-run + `workflow_call`); add `github-actions` to Dependabot. Resolves the §2 Stack-B gap.
- DEC-5: extend validator with default-off `markdown.adr.require_sections` check + tests + CHANGELOG + `standards/adr.md` note.
- DEC-6: `standards/adr.md` filename/id convention + directory tree + template filename comments.
- DEC-8: document the opt-in `lint-markdown.yml` consumption in `README.md` alongside the frontmatter workflow.
