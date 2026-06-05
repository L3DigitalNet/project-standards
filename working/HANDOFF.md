# HANDOFF — project-standards

> ## How this document works (permanent — read before editing)
>
> `working/HANDOFF.md` is the **single living handoff** for this repo: the one place a new session looks to learn the current state and the next action. It is intentionally short and always-current — a snapshot, not an append-only log.
>
> **Lifecycle**
>
> - **Session start:** read this file first, then read only what it points you to.
> - **During work:** keep _Current state_ and _Next action_ true to reality.
> - **Session end:** update those sections so the next session can start cold.
> - **When a body of work ships:** move its detailed planning docs to `working/archive/<version>/`, leave a one-line pointer here, and reset _Next action_ to the next piece of work.
>
> **Structure** — keep these sections, in order: _Current state_ · _Next action_ · _Locked decisions_ · _Key files_ · _Constraints_ · _Open questions_. Detailed step-by-step records do **not** live here — they live under `working/archive/<version>/`.
>
> **Scope** — a self-contained, repo-local convention (one file plus an archive folder). Deliberately **not** the workstation v3 handoff system; see [`../AGENTS.md`](../AGENTS.md).

---

## Current state — `1.2.0` released; formatting layer committed (`f0ef89a`, unreleased)

Repo: `/home/chris/projects/project-standards`. **Branch:** `testing` (dev; `main` holds releases, moving tag `v1` tracks the newest). Published line:

| Tag | What shipped |
| --- | --- |
| `v1.0.x` | initial Markdown Frontmatter + ADR + Versioning standards, validator, reusable workflow |
| `v1.1.0` | optional `consumer` field; `schema_version` enum widened to accept `1.1` |
| `v1.2.0` | `standards/adoption.md`; `standards-ref` pinning hardened (workflow default `main`→`v1`); validator no longer crashes on malformed YAML; doc fixes |

Gate green: `validate-frontmatter` ✓ 9, `pytest` 70, `ruff` clean @ 88, `pyright` 0. Per-release planning archived under [`archive/`](archive/).

**2026-06-04 planning session (design only).** Scoped the linting/formatting stack + ADR/MADR standard → **8 locked decisions** (DEC-1…DEC-8); see [`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md). No `standards/`/`schemas/`/`tools/`/`.github/` changes.

**2026-06-05 session — Stack-B markdownlint config + a new Prettier layer (committed as `f0ef89a` on `testing`; not yet released, repo still `1.2.0`).** The `.markdownlint.json` review gate is **cleared** and the formatting wiring is now committed:

- **`.markdownlint.json` expanded** from 3 rules to the **13 non-default rules** extracted from the workstation's global VS Code `markdownlint.config`: MD003 atx / MD004 dash / MD048 backtick / MD049 underscore / MD050 asterisk (align to Prettier); MD009/010/013/030/032 disabled (Prettier owns that formatting); MD029 off; MD024 `siblings_only:true`→**`false`** (Δ3, 2026-06-05, match MADR); MD025 `front_matter_title:""`. Repo Markdown lints **0 errors** (markdownlint v0.40.0 via cached `markdownlint-cli2` v0.22.1).
- **New Prettier formatting layer** (NOT in DEC-1…8 — see Open questions): repo-local [`../.prettierrc.json`](../.prettierrc.json) (`$schema`-pinned; mirrors the workstation Prettier settings) + **Prettier 3.8.3 pinned** as a local dev dependency (`../package.json` `private:true`, `../package-lock.json`, `node_modules/` gitignored). Overrides: `**/*.jsonc → trailingComma:none`, `**/*.md → singleQuote:true` (Prettier formats frontmatter in the repo's single-quote style — no churn on existing files).
- **Reference configs (`linting-formatting/markdownlint.{yaml,jsonc}`) were used to develop the full rule catalog, then deleted** once the root `../.markdownlint.json` became the single explicit config (2026-06-05). `linting-formatting/markdownlint-config-schema.json` (the v0.40.0 config schema) remains as the generation source / reference.
- **Normalized:** `CHANGELOG.md` MD049 emphasis (`*cannot*`→`_cannot_`); 5 templates' frontmatter (concept/note/research/runbook/spec) → single quotes. The 3 ADR templates were left as-authored (prose untouched).

## Next action — last `1.3.0` backlog item: #5 (README), then release

**Backlog item #2 (DEC-3 + DEC-7) is DONE** (2026-06-05, uncommitted→see below): `lint-markdown.yml` reusable workflow + `.markdownlint-cli2.jsonc` runner config + `github-actions` Dependabot, with the lint scope settled (**lint everything incl. `working/`**; the 5 pre-existing errors fixed). CHANGELOG `[Unreleased]` section started. Remaining for the `1.3.0` additive release (backlog at the bottom of the decisions doc):

- ✅ **#1 (DEC-1/§3.5) DONE (2026-06-05):** `.markdownlint.json` MD024 → `false` (Δ3, match MADR); "Any"→"Architectural" in `standards/adr.md` (Δ7, verified vs upstream). SPL declined (proseWrap:never); bare-placeholders kept.
- ✅ **#3 (DEC-5) DONE (2026-06-05):** validator gained default-off `markdown.adr.require_sections` (pure `missing_adr_sections` helper + `doc_type: adr` gate; `FrontmatterConfig`→`ProjectConfig`). 17 new tests, TDD, 87 green; ruff + pyright clean. Reconciled the Consequences-required finding (`standards/adr.md` now lists 3 required, matching MADR 4.0/templates). Enabled in `.project-standards.yml` (dogfood; verified it fires on a broken example).
- ✅ **#4 (DEC-6b) DONE (2026-06-05):** ADR id → `adr-NNNN-repo-name-title` (repo-name = cross-repo global uniqueness); filename stays `adr-NNNN-title.md` (no repo-name). Updated `standards/adr.md` (ID section + note + tree + frontmatter sample), 4 templates, and the worked example + its 2 inbound `related:` refs. Revised the original DEC-6 (MADR-bare filename) per a new "ids unique across many repos" requirement. No validator change.
- ✅ **#5 (DEC-8) DONE (2026-06-05):** `README.md` gained a "### 3. Optional — Markdown body linting" subsection (lint-markdown.yml `uses:` + seed-`.markdownlint.json` guidance) + a `markdown.adr.require_sections` config note. **All 5 backlog items complete** → ready for the `1.3.0` release ritual.

Then release `1.3.0` per the ritual (rename `[Unreleased]`→`[1.3.0]`, bump `pyproject.toml`, regen `uv.lock`, GPG-signed tag, move `v1`).

## Locked decisions / standing context (do not relitigate)

- **Link form is convention, not enforced.** Repo-root-relative paths are a documented SHOULD; the schema does not check link shape. Enforcing it is the headline **`2.0.0`** change (breaking) requiring a major bump + migration notes.
- **`standards-ref` must track the `@vN` workflow pin** (workflow now defaults it to `v1`).
- **One tag ships four components** (standard, schema, validator, workflow); classify by the previously-passing rule in [`../standards/versioning.md`](../standards/versioning.md).
- Every managed doc declares `schema_version: '1.1'`.
- **Frontmatter quote style is single quotes** (2026-06-05) — the repo was mixed (examples single, 5 templates double); Prettier `*.md singleQuote:true` is now the tiebreaker, and the standard already allows either (validator is quote-agnostic). Authored single-quoted.
- **Prettier ships as a committed dev-dependency** (2026-06-05, `f0ef89a`) — `package.json` + `package-lock.json` pin Prettier 3.8.3; `node_modules/` gitignored. Intentional and **scoped to Prettier only**: DEC-3/DEC-7 still keep the _markdownlint_ runner out of any committed Node project (CI via `markdownlint-cli2-action`). The two stacks are independent, so this does **not** reopen DEC-7. (Resolves the former "committed-Node vs DEC-7" open question.)
- **`proseWrap: never` for `*.md`, accepted as-is** (2026-06-05) — Prettier collapses prose paragraphs to single physical lines. The 5 then-nonconformant files (3 ADR templates, `tests/README.md`, 1 archived plan) were **pre-formatted** so the churn is captured now, not sprung on a future edit. Published `standards/`/`examples/` were already conformant (zero churn). **Consequence:** do not adopt MADR one-sentence-per-line (Δ5) without first switching this to `preserve` — `never` actively fights SPL.
- **Markdown-lint covers ALL tracked Markdown incl. `working/`** (2026-06-05) — chosen over excluding scratch. `lint-markdown.yml` lints `**/*.md`; the 5 then-pre-existing errors were fixed (MD040 fence languages in `tests/README.md` + `00-overview.md`; MD026 trailing-period heading + a labeled empty table cell for MD060 in the decisions doc). Local parity comes from `../.markdownlint-cli2.jsonc` (`gitignore: true`, so `.venv/`/caches are skipped). **Consequence:** scratch/planning docs under `working/` must stay markdownlint-clean.
- **`.markdownlint.json` is fully explicit — all 53 rules, not 13 overrides** (2026-06-05) — chosen so a consumer's linting can't be shadowed by their own editor/global markdownlint settings, and to pin against default drift across markdownlint versions. Generated from the v0.40.0 config **schema** (authoritative defaults) + the 13 customizations; verified schema-valid and behaviour-identical (repo lints 0 either way). **`MD043` MUST stay `true` (inert)** — its schema default `headings: []` is a sentinel that, stated explicitly, demands zero headings (fired 36 errors). [`tests/test_markdownlint_config.py`](../tests/test_markdownlint_config.py) guards this (MD043 inert + the 13 customisations + full-explicit, not sparse). **Consequence (load-bearing):** the explicit values track a markdownlint version, so the `markdownlint-cli2-action@v23` pin matters — re-generate/re-verify the config on every markdownlint upgrade.
- **`.editorconfig` + Prettier CI** (2026-06-05) — `.editorconfig` is the editor-agnostic whitespace floor (tabs for md/json, 4-space Python/TOML, 2-space YAML, markdown keeps trailing whitespace for hard breaks). `.github/workflows/format.yml` runs `prettier --check .` (repo-local dev gate, not reusable — Prettier is repo-scoped, not part of the published standard). Prettier honors `.gitignore`, so no `.prettierignore` is needed.

### Linting/formatting + MADR-4 decisions (2026-06-04 — trails in the decisions doc)

Eight decisions, primary-source-settled. Do **not** relitigate; trails in [`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md).

| # | Decision |
| --- | --- |
| DEC-1 | ADR standard targets **MADR 4.0** |
| DEC-2 | `vscode-adr-manager` = optional convenience, not a conformance target |
| DEC-3 | Stack-B linter = **markdownlint-cli2** (reads our published `.markdownlint.json`) |
| DEC-4 | Frontmatter key-order/quoting/list-style stay documented convention (schema = sole gate) |
| DEC-5 | Opt-in, default-off validator check for the 3 required ADR sections |
| DEC-6 | ADR naming — **revised DEC-6b (2026-06-05):** filename `adr-NNNN-title.md`; id `adr-NNNN-repo-name-title` (repo-name = cross-repo uniqueness) |
| DEC-7 | CI uses `markdownlint-cli2-action@v23`; **no committed Node project** (refines DEC-3) |
| DEC-8 | Separate opt-in reusable workflow `lint-markdown.yml` |

## Key files

| Path | Role |
| --- | --- |
| `working/HANDOFF.md` | this file — the living handoff |
| [`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md) | **active planning doc** — DEC-1…8 trails + implementation backlog |
| [`../.markdownlint.json`](../.markdownlint.json) · [`../tests/test_markdownlint_config.py`](../tests/test_markdownlint_config.py) | the single full explicit markdownlint config + its invariant guard test |
| `linting-formatting/markdownlint-config-schema.json` | v0.40.0 config schema — generation source for the explicit config |
| [`../.prettierrc.json`](../.prettierrc.json) | repo Prettier config (`$schema`; `*.jsonc`→`trailingComma:none`, `*.md`→`singleQuote:true`) |
| `../package.json` · `../package-lock.json` | pins Prettier **3.8.3** dev-only (`node_modules/` gitignored) |
| [`archive/`](archive/) | frozen per-release planning docs |
| `standards/markdown-frontmatter.md` · `standards/adoption.md` · `standards/versioning.md` | published standards |
| `schemas/markdown-frontmatter.schema.json` · `tools/validate_frontmatter.py` · `tests/` | machine contract + validator + tests |
| `.github/workflows/validate-markdown-frontmatter.yml` | reusable frontmatter (Stack A) workflow consumers call |
| `.github/workflows/lint-markdown.yml` | **NEW 2026-06-05** — reusable Markdown-body (Stack B) workflow; `markdownlint-cli2-action@v23`, `globs '**/*.md'` |
| [`../.markdownlint-cli2.jsonc`](../.markdownlint-cli2.jsonc) | **NEW** — local-runner scope (`gitignore:true` + `globs`); rules still in `../.markdownlint.json` |
| `.github/dependabot.yml` | **NEW** — `github-actions` ecosystem (bumps the action pins) |
| `CHANGELOG.md` · `pyproject.toml` | changelog + package version (bump at release) |

## Constraints / release ritual (from `AGENTS.md` + `standards/versioning.md`)

- The JSON schema is **authoritative**; update it first, prose follows.
- **Previously-passing rule:** any change that can fail a previously-passing consumer doc or workflow run → MAJOR.
- Release: bump `pyproject.toml` + regen `uv.lock`; date the `CHANGELOG.md` section; green gate; fast-forward `main` to `testing`; annotated **GPG-signed** immutable `vMAJOR.MINOR.PATCH` tag (key `9375AFEFA6F841B0`); move `v1` by **delete-and-re-push** (never `--force`); push `main` + `testing` + tags; verify `uvx … @v1` resolves.
- **Dogfood:** managed Markdown here must validate; never add frontmatter to `CLAUDE.md` / `AGENTS.md` / `.claude/**`.

## Open questions

_None open._ (The Markdown-lint CI scope question is resolved — see _Locked decisions_: lint **all** tracked Markdown incl. `working/`; scratch docs stay lint-clean.)

## Future work

- **`1.3.0` (additive — ADR/MADR-4 + Stack-B linting):** implement DEC-1…DEC-8 per the decisions doc's backlog — MADR-4 doc tweaks, `lint-markdown.yml` + `markdownlint-cli2-action`, opt-in `markdown.adr.require_sections` validator check (+ tests), ADR filename/id convention. All default-off / opt-in → MINOR.
- **`2.0.0` (deliberate, breaking):** enforce repo-root-relative link patterns in the schema; migrate in-repo bare-id links; consumer migration notes; bump to `@v2`.
