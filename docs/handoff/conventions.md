# Conventions

LLM-targeted pattern library for this repo. Check this file before adding a persistent pattern; add new patterns here before session end.

## Quick Reference

| # | Title | Applies when |
| --- | --- | --- |
| 1 | Dogfood the standards | Editing managed Markdown (`standards/**`, `meta/**`, `CHANGELOG.md`) |
| 2 | Never frontmatter agent-instruction files | Touching `CLAUDE.md`, `AGENTS.md`, `.claude/**` |
| 3 | Keep the toolchain green | Changing the validator or its tests |
| 4 | The schema is a versioned contract | Changing the schema or controlled vocabularies |
| 5 | Python tooling follows the SSOT standard | Adding or changing Python tooling, CI gate, or layout |
| 6 | Standards live in per-standard bundles | Adding/moving a standard, template, or example |
| 7 | Style gates exclude generated/template content | Wiring or debugging markdownlint / Prettier / frontmatter gates |
| 8 | `except A, B:` is ruff-canonical — NOT a Python-2 bug | Reviewing/fixing multi-exception clauses in `src/` |
| 9 | Doc-embedded scaffolds are byte-locked to their bundle twin | Editing a copy-paste scaffold fence inside a standard doc |

## 1. Dogfood the standards

**Applies when:** editing managed Markdown here — `standards/**` (bundle `README.md`, `adopt.md`, examples), `meta/**`, `CHANGELOG.md`. Per-standard `templates/` and the `standards/README.md` index are excluded.

**Rule:** managed Markdown carries canonical frontmatter and must validate; run the validator before finishing.

**Code:**

```bash
uv run validate-frontmatter --config .project-standards.yml
```

**Why:** this repo is the source of the standard; if its own managed docs don't validate, the standard isn't credible.

**Sources:** pre-v3 `AGENTS.md` "General" section.

**Related:** 2, 4.

## 2. Never add frontmatter to agent-instruction files

**Applies when:** touching `CLAUDE.md`, `AGENTS.md`, or anything under `.claude/`, `.agents/`, `.codex/`.

**Rule:** these are harness configuration, not managed documents — never add frontmatter. They are excluded from validation in `.project-standards.yml`.

**Why:** frontmatter on a harness file is meaningless and would fail the schema's date/id patterns.

**Sources:** pre-v3 `AGENTS.md`; `.project-standards.yml`.

**Related:** 1.

## 3. Keep the toolchain green

**Applies when:** changing the validator (`src/project_standards/`) or its tests.

**Rule:** run all six before committing — every one must pass.

**Code:**

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

**Why:** `main` must stay releasable; consumers pin to tags.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 4.

## 4. The schema is a versioned contract

**Applies when:** changing `src/project_standards/schemas/markdown-frontmatter.schema.json` or the controlled vocabularies.

**Rule:** update `standards/`, templates, examples, tests, and `CHANGELOG.md` together, then cut a new tag (minor = additive, major = breaking).

**Why:** consumers pin to tags; a silent schema change breaks them.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 1, 3.

## 5. Python tooling follows the SSOT standard

**Applies when:** adding or changing Python tooling, the CI gate, package layout, or agent instructions for Python projects.

**Rule:** follow `standards/python-tooling/README.md` — `uv_build` backend, `src/` layout, `basedpyright` strict, branch coverage (`fail_under = 85`), `pip-audit`, and the six-step gate.

**Why:** ensures every Python project in this ecosystem is recoverable, repeatable, and self-explaining for agents.

**Sources:** `standards/python-tooling/README.md` (adopted 2026-06-06).

**Related:** 3.

## 6. Standards live in per-standard bundles

**Applies when:** adding, moving, or renaming a standard, template, or example.

**Rule:** each governing standard is a self-contained bundle — `standards/<name>/{README.md, adopt.md, templates/, examples/}` (`templates/`/`examples/` optional; Python-tooling is doc-only). The standard doc is always `README.md`; repo-meta (versioning) lives in `meta/`, not `standards/`. A new standard = copy the anatomy documented in `standards/README.md`.

**Why:** keeps each standard browseable and independently adoptable, and makes adding the next one mechanical.

**Sources:** `standards/README.md`; `docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md`.

**Related:** 1, 5.

## 7. Style gates exclude generated/template content

**Applies when:** wiring or debugging a repo-wide style gate — markdownlint (`lint-markdown.yml`), Prettier (`format.yml`), or frontmatter validation (`validate-markdown-frontmatter.yml`).

**Rule:** machine-generated or template Markdown is **excluded** from style gates, not reformatted. Draw the exclusion boundary once and mirror it across gates:

- `.project-standards.yml` excludes `docs/handoff/**` from frontmatter validation.
- `.markdownlint-cli2.jsonc` `ignores` excludes `docs/codex-reviews/**` + `docs/handoff/**` (config `ignores` apply in both the local bare run and the CI `markdownlint-cli2-action` run, which passes globs explicitly — verify both).
- Prettier honors `.prettierignore`, which mirrors the markdownlint `ignores` (`docs/codex-reviews/`, `docs/handoff/`) — added 2026-06-09 (`281afe4`); `format.yml` is green (authored docs are formatted, generated transcripts ignored).

**Why:** codex review transcripts and v3 handoff state regenerate constantly, and the bundles ship with intentional placeholders. Style-linting them is churn that keeps CI permanently red on content no human authored to a style bar.

**Gotchas (when a doc IS in scope and a rule fights Prettier):**

- markdownlint **MD031** (blanks around fences) conflicts with Prettier on **list-nested** fences — Prettier keeps them tight because it owns blank-line placement (cf. the existing MD032 exclusion). Scope-disable MD031 around the block, or disable it globally as Prettier-owned (a rule-set/contract change: `.markdownlint.json` + `tests/test_markdownlint_config.py` + standard doc + CHANGELOG).
- markdownlint **MD051** (link fragments) anchor algorithm diverges from GitHub's on **emoji** headings — scope-disable on the affected link; it resolves on GitHub. Keep MD051 enabled (it catches real stale TOC links).
- Inline disables in lists survive Prettier only if the directive stays adjacent to its target — verify with a `prettier --write` + markdownlint pass after adding them.

**Sources:** 2026-06-09 session (markdownlint scoping + authored-doc cleanup, `ec2b517`).

**Related:** 1, 2, 5.

## 8. `except A, B:` is ruff-canonical — NOT a Python-2 bug

`ruff format` 0.15 rewrites a parenthesized multi-exception clause `except (A, B):` to the bare-tuple form `except A, B:` (verified empirically — it strips the parens as redundant on Python ≥3.14). Both are identical Python-3 tuple-catches — NOT the removed Py2 `except Exc, name` binding (confirmed via AST: `handler.name is None`). So `except OSError, FrontmatterParseError:` in `validate_references.py`/`validate_id.py` and `except KeyError, TypeError:` in `sync_vscode_colors.py` are **intentional and gate-canonical**: parenthesizing them fails `ruff format --check` and is auto-reverted.

**Why:** reviewers (codex, manual) repeatedly mis-flag the comma form as a Python-2 syntax bug and try to "fix" it; the fix never sticks because ruff owns the style. Do not re-flag or re-fix it.

**Sources:** 2026-06-09 round-3 release-readiness review.

**Related:** 3.

## 9. Doc-embedded scaffolds are byte-locked to their bundle twin

**Applies when:** editing a copy-paste scaffold fence inside a standard doc (e.g. python-tooling §15 `check.yml`, §6 pyproject baseline; markdown-frontmatter adopt.md starter + caller; markdown-tooling §6 prettierrc) or adding a new one.

**Rule:** a scaffold that exists both as a fenced block in a standard doc and as an adopt bundle artifact is ONE artifact with two representations. Keep them in sync via a drift test in `tests/test_adopt_dogfood.py` (byte-equality for verbatim blocks; semantic TOML/YAML comparison when the doc adds illustrative content). For **YAML** fences two extra hazards apply:

- The shared `.editorconfig` defaults Markdown to tab indentation — tabs inside a YAML fence make the scaffold unparseable (this shipped broken for weeks; caught 2026-07-01). Author fences with spaces.
- Prettier's `embeddedLanguageFormatting: "auto"` DOES reformat yaml fences in Markdown, and the `**/*.md` override (`singleQuote: true`) rewrites their quote style — silently breaking byte-equality with the bundle. Put a bare `<!-- prettier-ignore -->` (no trailing text — Prettier ignores the directive if anything follows it in the comment) on the line before the fence. Prettier does NOT format toml fences (no TOML parser), so TOML needs no guard.

**Why:** manual copy-adopters use the doc block, the CLI ships the bundle; drift means the two adoption paths deliver different (or broken) tooling.

**Sources:** 2026-07-01 python-tooling standard review (tab-YAML §15 defect + Prettier embedded-formatting verification); same-day markdown-standards sweep (starter example had silently lost `**/*.template.md` to unguarded drift).

**Related:** 1, 5, 6.
