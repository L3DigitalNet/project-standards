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

## Current state — `1.3.0` feature-complete on `testing` (DEC-1…9), unreleased

Repo: `/home/chris/projects/project-standards`. **Branch:** `testing` (dev; `main` holds releases, moving tag `v1` tracks the newest). `testing` carries the **entire `1.3.0` line** ahead of `main` — implemented but **not yet released** (release was deliberately out of this session's scope). For the exact set: `git log main..testing`. Published + pending line:

| Tag | What shipped |
| --- | --- |
| `v1.0.x` | initial Markdown Frontmatter + ADR + Versioning standards, validator, reusable workflow |
| `v1.1.0` | optional `consumer` field; `schema_version` enum widened to accept `1.1` |
| `v1.2.0` | `standards/adoption.md`; `standards-ref` pinning hardened (workflow default `main`→`v1`); validator crash-safety; doc fixes |
| `1.3.0` _(pending, on `testing`)_ | opt-in Markdown-lint workflow + ADR section validator + MADR-4 ADR conventions + the full formatting/linting stack — see below |

**Gate green** (verified 2026-06-05): `pytest` **105**, `ruff` clean, `pyright` 0, `validate-frontmatter` ✓ 9, `markdownlint` 0, `prettier --check .` clean.

### What `1.3.0` delivers (all on `testing`, additive → MINOR)

The 2026-06-04 planning session locked **DEC-1…DEC-8**; the 2026-06-05 session implemented them, revised DEC-6→**DEC-6b**, and added **DEC-9**. Decision trails in [`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md); per-commit detail in `git log main..testing`.

- **Stack-B Markdown linting (DEC-3/7/8):** opt-in reusable `lint-markdown.yml` (`markdownlint-cli2-action@v23`) + `.markdownlint-cli2.jsonc` local parity + `github-actions` Dependabot.
- **MADR 4.0 ADR conventions (DEC-1/6b):** `MD024`→`false`; "Any"→"Architectural" name fix; ADR id `adr-NNNN-repo-name-title` (globally unique) with filename `adr-NNNN-title.md`.
- **Opt-in ADR section check (DEC-5):** default-off `markdown.adr.require_sections` in the validator (built TDD, +18 tests); `standards/adr.md` reconciled to 3 required sections; dogfooded in this repo's `.project-standards.yml`.
- **Formatting stack (DEC-9 + tooling):** Prettier as the repo-local formatter with a `format.yml` CI gate; `.editorconfig` floor; `.markdownlint.json` made **fully explicit (53 rules)** for consumer determinism, guarded by `tests/test_markdownlint_config.py`.
- **CHANGELOG:** every change accumulated under `[Unreleased]` (rename to `[1.3.0]` at release).

## Next action — release `1.3.0` when ready (feature-complete, unreleased)

Nothing is half-done: all DEC-1…9 work is committed and green on `testing`. The next action is the **`1.3.0` release ritual** (full steps in _Constraints_ below) whenever you choose to ship:

1. Rename CHANGELOG `[Unreleased]` → `[1.3.0] — <date>`.
2. Bump `pyproject.toml` to `1.3.0`; regen `uv.lock`; refresh the `standards_version` snapshots in `.project-standards.yml` + the README example if desired.
3. Green gate → fast-forward `main` to `testing` → GPG-signed annotated `v1.3.0` tag → move `v1` (delete-and-re-push, never `--force`) → push `main` + `testing` + tags → verify `uvx … @v1` resolves.
4. At release, move the active planning doc (`linting-formatting-stack.md`) to `archive/v1.3.0/` and reset this section to the next work.

Deferred (not blocking release): **pre-commit hooks** — the one unpicked stack gap (see _Future work_).

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

Nine decisions, primary-source-settled. Do **not** relitigate; trails in [`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md).

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
| DEC-9 | Prettier = the repo's **formatter**, repo-local (not shipped); owns whitespace markdownlint defers; `proseWrap: never` |

## Key files

| Path | Role |
| --- | --- |
| `working/HANDOFF.md` | this file — the living handoff |
| [`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md) | **active planning doc** — DEC-1…9 trails (backlog now implemented; archive to `archive/v1.3.0/` at release) |
| [`../.markdownlint.json`](../.markdownlint.json) · [`../tests/test_markdownlint_config.py`](../tests/test_markdownlint_config.py) | the single full explicit markdownlint config + its invariant guard test |
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

- **`1.3.0` is implemented on `testing`** (see _Current state_) — only the release ritual remains (see _Next action_).
- **Pre-commit hooks (deferred, optional):** the one unpicked formatting-stack gap — a pre-commit framework running prettier + markdownlint + the validator + the config guard at commit time, to catch issues (and editor corruption) locally before CI.
- **`2.0.0` (deliberate, breaking):** enforce repo-root-relative link patterns in the schema; migrate in-repo bare-id links; consumer migration notes; bump to `@v2`.
