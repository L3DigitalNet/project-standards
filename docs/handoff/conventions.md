# Conventions

LLM-targeted pattern library for this repo. Check this file before adding a persistent pattern; add new patterns here before session end.

## Quick Reference

| # | Title | Applies when |
| --- | --- | --- |
| 1 | Dogfood the standards | Editing local managed Markdown declared in `.project-standards.yml` |
| 2 | Never frontmatter agent-instruction files | Touching `CLAUDE.md`, `AGENTS.md`, `.claude/**` |
| 3 | Keep the toolchain green | Changing the validator or its tests |
| 4 | The schema is a versioned contract | Changing the schema or controlled vocabularies |
| 5 | Python tooling follows the SSOT standard | Adding or changing Python tooling, CI gate, or layout |
| 6 | Standards live in per-standard bundles | Adding/moving a standard, template, or example |
| 7 | Style gates exclude generated/template content | Wiring or debugging markdownlint / Prettier / frontmatter gates |
| 8 | `except A, B:` is ruff-canonical — NOT a Python-2 bug | Reviewing/fixing multi-exception clauses in `src/` |
| 9 | Doc-embedded scaffolds are byte-locked to their bundle twin | Editing a copy-paste scaffold fence inside a standard doc |
| 10 | V1 and V2 manifests coexist through a preamble boundary | Discovering package-family indexes during the V5 migration |
| 11 | Installed V2 payloads use a symlink-only source projection | Adding or packaging canonical versioned payloads |

## 1. Dogfood the standards

**Applies when:** editing local managed Markdown declared in `.project-standards.yml` — currently `CHANGELOG.md`, `UPGRADING.md`, `docs/usage.md`, `docs/workflows/**/*.md`, `meta/**/*.md`, and `docs/adr/**/*.md`.

**Rule:** local managed Markdown carries canonical frontmatter and must validate; run the validator before finishing. Standard-package content under `standards/**` is deliberately excluded by ADR 0015 so this repo does not ship repo-local metadata inside reusable standards. Intentional frontmatter artifacts there may still exist in examples, templates, and skill metadata because they teach or implement the standard rather than describe this repository's local document lifecycle.

**Code:**

```bash
uv run validate-frontmatter --config .project-standards.yml
```

**Why:** this repo is the source of the standard; if its own managed local docs don't validate, the standard isn't credible. Published standard packages have a different boundary: they must be reusable without carrying project-standards-specific document metadata.

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

**Rule:** machine-generated or template Markdown is **excluded** from style gates, not reformatted. Draw one boundary and mirror it across gates:

- `.project-standards.yml` excludes `docs/handoff/**` from frontmatter validation.
- `.markdownlint-cli2.jsonc` ignores `docs/codex-reviews/**` and `docs/handoff/**`; verify local and CI behavior.
- `.prettierignore` mirrors the markdownlint ignore boundary.

**Why:** codex review transcripts, v3 handoff state, and shipped templates change mechanically. Style-linting them creates churn and false red CI.

**Gotchas for in-scope docs:**

- MD031 conflicts with Prettier on list-nested fences; scope-disable locally unless changing the standard.
- MD051 can disagree with GitHub on emoji anchors; scope-disable only the affected link.
- Inline disables in lists must stay adjacent to their target after Prettier.

**Sources:** 2026-06-09 session (markdownlint scoping + authored-doc cleanup, `ec2b517`).

**Related:** 1, 2, 5.

## 8. `except A, B:` is ruff-canonical — NOT a Python-2 bug

`ruff format` 0.15 rewrites a parenthesized multi-exception clause `except (A, B):` to the bare-tuple form `except A, B:` (verified empirically — it strips the parens as redundant on Python ≥3.14). Both are identical Python-3 tuple-catches — NOT the removed Py2 `except Exc, name` binding (confirmed via AST: `handler.name is None`). So `except OSError, FrontmatterParseError:` in `validate_references.py`/`validate_id.py` and `except KeyError, TypeError:` in `sync_vscode_colors.py` are **intentional and gate-canonical**: parenthesizing them fails `ruff format --check` and is auto-reverted.

**Why:** reviewers (codex, manual) repeatedly mis-flag the comma form as a Python-2 syntax bug and try to "fix" it; the fix never sticks because ruff owns the style. Do not re-flag or re-fix it.

**Sources:** 2026-06-09 round-3 release-readiness review.

**Related:** 3.

## 9. Doc-embedded scaffolds are byte-locked to their bundle twin

**Applies when:** editing a copy-paste scaffold fence inside a standard doc or adding a new one.

**Rule:** a scaffold that exists both as a fenced block in a standard doc and as an adopt bundle artifact is one artifact with two representations. Keep them in sync via a drift test in `tests/test_adopt_dogfood.py`.

Use byte equality for verbatim blocks and semantic TOML/YAML comparison when the doc intentionally adds illustrative content.

For YAML fences:

- Author with spaces; tabs from Markdown editor settings make YAML unparseable.
- Put a bare `<!-- prettier-ignore -->` before verbatim YAML fences so Prettier does not rewrite quote style.
- TOML fences need no guard because Prettier has no TOML parser.

**Why:** manual copy-adopters use the doc block, the CLI ships the bundle; drift means the two adoption paths deliver different (or broken) tooling.

**Sources:** 2026-07-01 python-tooling review and same-day markdown-standards sweep.

**Related:** 1, 5, 6.

## 10. V1 and V2 manifests coexist through a preamble boundary

**Applies when:** discovering `standards/{id}/standard.toml` while V1 and V2 package data coexist during the V5 migration.

**Rule:** V2 discovery may inspect only the bounded beginning of a regular `standard.toml` and selects a family only when that preamble declares `schema_version = "2.0"`. It must not parse a V1 manifest and reinterpret its fields as V2 facts. An explicit family allowlist still requires the selected path to be a regular file and reports a missing family instead of falling back to V1 behavior.

**Why:** the migration keeps the operational V1 runtime intact until current packages are reconstructed. A format probe provides one deterministic authority boundary without merging V1 and V2 models or requiring package-ID exceptions.

**Sources:** `project_standards.package_contract.discovery`; SPEC-BA02 foundation implementation.

**Related:** 4, 6, 11.

## 11. Installed V2 payloads use a symlink-only source projection

**Applies when:** adding canonical files under `standards/{id}/versions/{version}/` or changing package-data build behavior.

**Rule:** authored payload bytes exist only under the canonical version directory. `src/project_standards/payloads/{id}/{version}/` may contain relative file symlinks and directories, never regular files or directory symlinks. Regenerate with `project-standards standards sync-payload-projection --root .`; use `--check` in validation. The build must prove direct-wheel and sdist-to-wheel members are byte-identical to canonical payloads.

**Why:** `uv_build` needs package data under `src/`, while authors and release checks need one editable authority. Relative file links provide the build path without creating a second maintained payload tree.

**Sources:** `project_standards.package_contract.projection`; SPEC-BA02 FR-034 and IR-007.

**Related:** 3, 4, 6, 10.
