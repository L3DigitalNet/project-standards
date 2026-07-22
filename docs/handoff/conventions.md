# Conventions

LLM-targeted pattern library for this repo. Check this file before adding a persistent pattern; add new patterns here before session end.

## Quick Reference

| # | Title | Applies when |
| --- | --- | --- |
| 1 | Dogfood the standards | Editing local managed Markdown declared in `.standards/config.toml` |
| 2 | Never frontmatter agent-instruction files | Touching `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, or `.codex/**` |
| 3 | Keep the toolchain green | Changing the validator or its tests |
| 4 | The schema is a versioned contract | Changing the schema or controlled vocabularies |
| 5 | Python tooling follows the SSOT standard | Adding or changing Python tooling, CI gate, or layout |
| 6 | Standards live in V2 families | Adding/moving a standard, template, or example |
| 7 | Style gates exclude generated/template content | Wiring or debugging markdownlint / Prettier / frontmatter gates |
| 8 | `except A, B:` is ruff-canonical — NOT a Python-2 bug | Reviewing/fixing multi-exception clauses in `src/` |
| 9 | Doc-embedded scaffolds are byte-locked to their bundle twin | Editing a copy-paste scaffold fence inside a standard doc |
| 10 | V2 family indexes are canonical | Discovering current packages or inspecting V1 migration input |
| 11 | Installed V2 payloads use a symlink-only source projection | Adding or packaging canonical versioned payloads |
| 12 | Managed Markdown ranges use paired Prettier guards | Composing formatter-stable package blocks in consumer Markdown |
| 13 | Keep documentation-only closeout proportional | Closing a documentation-only session |

## 1. Dogfood the standards

**Applies when:** editing local managed Markdown selected by `.standards/config.toml`.

**Rule:** local managed Markdown carries canonical frontmatter and must validate. ADR 0015 excludes reusable `standards/**` package content; intentional templates, examples, and skill metadata may still contain frontmatter as package data.

**Code:**

After building and extracting the candidate wheel as required by the repository toolchain gate:

```bash
PYTHONPATH="$PWD/build/wheel-runtime" uv run project-standards validate
```

**Why:** the repository must dogfood local metadata without shipping that repository-specific metadata in reusable packages.

**Sources:** pre-v3 `AGENTS.md` "General" section.

**Related:** 2, 4.

## 2. Never add frontmatter to agent-instruction files

**Applies when:** touching `CLAUDE.md`, `AGENTS.md`, or anything under `.claude/`, `.agents/`, `.codex/`.

**Rule:** these are harness configuration, not managed documents — never add frontmatter. They are excluded through the Markdown Frontmatter options in `.standards/config.toml`.

**Why:** frontmatter on a harness file is meaningless and would fail the schema's date/id patterns.

**Sources:** pre-v3 `AGENTS.md`; `.standards/config.toml`.

**Related:** 1.

## 3. Keep the toolchain green

**Applies when:** changing the validator (`src/project_standards/`) or its tests.

**Rule:** run the complete gate before committing; every phase must pass.

**Code:**

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv build --wheel --out-dir dist
python -m zipfile -e dist/project_standards-*.whl build/wheel-runtime
export PYTHONPATH="$PWD/build/wheel-runtime"
uv run coverage erase
uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"
uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0
uv run pytest -m performance
uv run coverage report
uv run pip-audit
```

**Why:** `main` must stay releasable; consumers pin to tags. Direct commands keep the ordinary, compatibility, performance, and coverage responsibilities visible without a repository-specific orchestrator.

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

**Rule:** follow `standards/python-tooling/versions/1.2/README.md` — `uv_build` backend, `src/` layout, `basedpyright` strict, branch coverage (`fail_under = 85`), `pip-audit`, and the six-step gate.

**Why:** ensures every Python project in this ecosystem is recoverable, repeatable, and self-explaining for agents.

**Sources:** `standards/python-tooling/versions/1.2/README.md` (adopted 2026-06-06; current payload selected 2026-07-20).

**Related:** 3.

## 6. Standards live in V2 families

**Applies when:** adding, moving, or renaming a standard, template, or example.

**Rule:** each governing standard is a self-contained V2 family.

- `standards/<name>/standard.toml` indexes immutable `versions/<major.minor>/` payloads.
- The family-root `README.md` is a mutable landing page.
- Each payload declares its manifest, canonical documentation, resources, providers, schemas, and other package data.
- Repository policy such as versioning lives in `meta/`, not a package.

Follow the Standard Bundle Authoring 2.5 workflow when adding a family or payload.

**Why:** keeps each standard browseable and independently adoptable, and makes adding the next one mechanical.

**Sources:** `standards/README.md`; `docs/specs/archive/2026-06-06-standards-bundle-restructure-design.md`.

**Related:** 1, 5.

## 7. Style gates exclude generated/template content

**Applies when:** wiring or debugging a repo-wide style gate — markdownlint (`lint-markdown.yml`), Prettier (`format.yml`), or frontmatter validation (`validate-markdown-frontmatter.yml`).

**Rule:** machine-generated or template Markdown is **excluded** from style gates, not reformatted. Draw one boundary and mirror it across gates:

- `.standards/config.toml` excludes `docs/handoff/**` from frontmatter validation.
- `.markdownlint-cli2.jsonc` ignores append-only `docs/handoff/**`; verify local and CI behavior.
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

**Rule:** when package documentation embeds a declared payload resource verbatim, treat both representations as one artifact and add a focused package-contract drift test.

Use byte equality for verbatim blocks and semantic TOML/YAML comparison when the doc intentionally adds illustrative content.

For YAML fences:

- Author with spaces; tabs from Markdown editor settings make YAML unparseable.
- Put a bare `<!-- prettier-ignore -->` before verbatim YAML fences so Prettier does not rewrite quote style.
- TOML fences need no guard because Prettier has no TOML parser.

**Why:** readers may use the documented scaffold while package providers materialize its declared payload resource; drift would make those two representations deliver different or broken tooling.

**Sources:** 2026-07-01 python-tooling review and same-day markdown-standards sweep.

**Related:** 1, 5, 6.

## 10. V2 family indexes are canonical

**Applies when:** discovering `standards/{id}/standard.toml` or inspecting legacy package material.

**Rule:** current package discovery selects only regular family indexes whose bounded preamble declares `schema_version = "2.0"`. Never reinterpret a V1 manifest as V2 facts or fall back from a missing V2 family to V1 runtime behavior. V1 manifests, `adopt.toml`, `registry.json`, and copy-adopt resources are migration or compatibility evidence only.

**Why:** Catalog 5 has one deterministic package-authority boundary. The bounded format probe preserves explicit legacy migration without creating parallel current authorities or package-ID exceptions.

**Sources:** `project_standards.package_contract.discovery`; SPEC-BA02 foundation implementation.

**Related:** 4, 6, 11.

## 11. Installed V2 payloads use a symlink-only source projection

**Applies when:** adding canonical files under `standards/{id}/versions/{version}/` or changing package-data build behavior.

**Rule:** authored payload bytes exist only under the canonical version directory. `src/project_standards/payloads/{id}/{version}/` may contain relative file symlinks and directories, never regular files or directory symlinks. Regenerate with `project-standards standards sync-payload-projection --root .`; use `--check` in validation. The build must prove direct-wheel and sdist-to-wheel members are byte-identical to canonical payloads.

**Why:** `uv_build` needs package data under `src/`, while authors and release checks need one editable authority. Relative file links provide the build path without creating a second maintained payload tree.

**Sources:** `project_standards.package_contract.projection`; SPEC-BA02 FR-034 and IR-007.

**Related:** 3, 4, 6, 10.

## 12. Managed Markdown ranges use paired Prettier guards

**Applies when:** a standards package owns one bounded block inside consumer Markdown.

**Rule:** wrap each exact `BEGIN project-standards:BLOCK_ID` / `END project-standards:BLOCK_ID` block in top-level `<!-- prettier-ignore-start -->` and `<!-- prettier-ignore-end -->` comments. Keep a blank line before each Prettier range marker. The Markdown adapter rejects inline, nested, duplicate, orphaned, or partially guarded layouts.

```markdown
<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:example -->
Managed bytes stay formatter-stable.
<!-- END project-standards:example -->

<!-- prettier-ignore-end -->
```

Use the existing bare `<!-- prettier-ignore -->` convention only for one following Markdown node, such as a byte-locked YAML fence. It does not protect a multi-node managed range.

**Why:** Prettier 3.8.3 preserves the managed bytes only when the range markers are top-level and correctly separated. The adapter test runs the pinned formatter and verifies that the block digest and raw bytes remain unchanged.

**Sources:** Prettier range-ignore documentation; SPEC-CP01 Task 13 verification fixture.

**Related:** 3, 7, 9.

## 13. Keep documentation-only closeout proportional

**Applies when:** the diff contains only documentation, handoff records, and directly regenerated lock or provenance metadata. Any implementation, test, workflow, package, schema, dependency, or build change excludes this fast path.

**Rule:** validate only the changed surfaces:

- format and lint the changed documents where covered;
- validate managed Markdown and run applicable handoff checks;
- check eager-document shape or size and reconcile changed provenance;
- `git diff --check`, a clean post-commit worktree, and local/remote branch parity after push.

Do not run or wait for implementation and release gates or hosted `Check` solely for this closeout. An automatically triggered full workflow is not a blocker; inspect it only when branch policy requires it or it reports a relevant failure.

Use the affected focused or full gate when documentation changes a byte-locked scaffold, executable interface, or package contract.

**Why:** validation should be proportional to the changed surface.

**Sources:** 2026-07-20 session closeout correction.

**Related:** 1, 3, 7, 9.
