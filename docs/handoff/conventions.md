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
| 14 | Move TMPDIR, basetemp, and COVERAGE_FILE off /tmp and the repo root | Running a whole-battery pytest |
| 15 | Go tooling follows the neutral coexistence ADR | Adding or changing Go tooling, CI, or source |
| 16 | Ownership decides Python lint scope, not byte-locking | Vendoring a file, or triaging a lint finding on immutable bytes |

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

**Rule:** run `scripts/verify.sh` before committing; every lane must pass. Intermediate legs of a train run the fast gate; the serial battery runs after the last content change and at release prep.

**Code:**

```bash
uv sync --all-groups --locked
npm ci
uv run project-standards standards sync-payload-projection --root . --check --json
uv build --clear --wheel --out-dir build/release-wheel
rm -rf -- build/wheel-runtime
uv run python -m zipfile -e build/release-wheel/project_standards-X.Y.Z-py3-none-any.whl build/wheel-runtime
scripts/verify.sh          # fast gate: concurrent lanes, then performance alone
scripts/verify.sh --full   # legacy serial battery / release-prep cross-check
```

**Why:** `main` must stay releasable; consumers pin to tags. The isolated, cleared wheel directory and fresh runtime extraction keep the candidate wheel that the gates import identical to the release commit being proved.

Direct commands used to keep the lanes visible without a repository-specific orchestrator, but the 2026-07-31 wall-clock spike made concurrency worth 5.3× and the environment it needs (§14, per-lane basetemps, lane ordering) too easy to get wrong by hand.

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

**Rule:** follow `standards/python-tooling/versions/1.10/README.md` — `uv_build` backend, `src/` layout, `basedpyright` strict, branch coverage (`fail_under = 85`), `pip-audit`, and the six-step gate.

**Why:** ensures every Python project in this ecosystem is recoverable, repeatable, and self-explaining for agents.

**Sources:** `standards/python-tooling/versions/1.10/README.md` (adopted 2026-06-06; current payload selected 2026-07-27).

**Related:** 3.

## 6. Standards live in V2 families

**Applies when:** adding, moving, or renaming a standard, template, or example.

**Rule:** each governing standard is a self-contained V2 family.

- `standards/<name>/standard.toml` indexes immutable `versions/<major.minor>/` payloads.
- The family-root `README.md` is a mutable landing page.
- Each payload declares its manifest, canonical documentation, resources, providers, schemas, and other package data.
- Repository policy such as versioning lives in `meta/`, not a package.

Follow the Standard Bundle Authoring 2.6 workflow when adding a family or payload.

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

`ruff format` 0.15 rewrites a parenthesized multi-exception clause `except (A, B):` to the bare-tuple form `except A, B:` (verified empirically — it strips the parens as redundant on Python ≥3.14). Both are identical Python-3 tuple-catches — NOT the removed Py2 `except Exc, name` binding (confirmed via AST: `handler.name is None`).

So `except OSError, FrontmatterParseError:` in `validate_references.py`/`validate_id.py` and `except KeyError, TypeError:` in `sync_vscode_colors.py` are **intentional and gate-canonical**: parenthesizing them fails `ruff format --check` and is auto-reverted.

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

**Rule:** authored payload bytes exist only under the canonical version directory. `src/project_standards/payloads/{id}/{version}/` may contain relative file symlinks and directories, never regular files or directory symlinks.

Regenerate with `project-standards standards sync-payload-projection --root .`; use `--check` in validation. The build must prove direct-wheel and sdist-to-wheel members are byte-identical to canonical payloads.

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

## 14. Whole-battery runs move TMPDIR, basetemp, and COVERAGE_FILE off /tmp and off the repo root

**Applies when:** running any whole-battery pytest (ordinary, compatibility, performance).

**Rule:** `scripts/verify.sh` sets these; do it by hand only for ad-hoc runs.

- `TMPDIR` and `--basetemp` under one non-`/tmp` root, cleaned at run start; `COVERAGE_FILE` outside the repository.
- Fast path: the 4M-inode tmpfs at `/mnt/pytesttmp` (persistent systemd unit); fallback when unmounted: disk-backed under `~/.cache`.

**Why:**

- The MCP fixture suites exhaust the 1,048,576-inode `/tmp` by inodes, not bytes; nested pytest bypasses a parent `--basetemp`, so `TMPDIR` must be exported.
- T12 (2026-07-31): `/tmp` inodes fell 56,480 → 16,672 with both redirects, costing 22:30 disk-backed vs 16:00 tmpfs — accepted after the 2026-07-29 ENOSPC kill.
- Ceiling since measured: 768,844 inodes sequential, ~465,000 concurrent — marginal for default `/tmp`, 5× headroom on the 4M tmpfs.
- In-root, xdist workers' `.coverage.<host>.<pid>` files raced the read-only digest proof and the wheel-source `copytree` (spike R6/R7, root-caused in R8).

**Sources:** MCP plan §14 close-out (J-P/P14); `.workflow/lessons/tmpfs-seal-hygiene-enospc.md`; the 2026-07-31 release-gate wall-clock spike.

**Related:** 3, 13.

## 15. Go tooling follows the neutral coexistence ADR

**Applies when:** adding or changing Go tooling, CI, module boundaries, or source.

**Rule:** follow ADR 0027. Go and Python are neutral supported peers. `go.mod` owns the root module and toolchain, the root `Makefile` owns canonical Go commands, and local users, VS Code, and CI delegate to `make go-check`. Install pinned third-party executables under ignored `.tools/`; keep `go vet` first-party and `govulncheck` module-tracked.

Do not infer permission for Python migration, freeze, retirement, or language preference from the Go lane. A second module or workspace requires a separately justified ownership or distribution boundary.

**Why:** tooling readiness is an architectural prerequisite for safe Go work, but it does not settle which language is appropriate for future components.

**Sources:** ADR 0027; `go.mod`; `Makefile`; `.golangci.yml`.

**Related:** 3, 5, 6.

## 16. Ownership decides Python lint scope, not byte-locking

**Applies when:** vendoring a file, or triaging a Ruff finding against uneditable bytes.

**Rule:** ask who owns the standard governing the bytes, not whether the bytes are frozen.

- Foreign vendored bytes are excluded in the commit that lands them. `scripts/plan.py` is the byte-identical `plan-authoring` bridge from `agent-configs`.
- A finding on it is unfixable here and proves nothing about these standards; it is the only `scripts/` entry in `[tool.ruff] extend-exclude`.
- Bytes governed by a standard this repository owns stay in scope even when immutable: `standards/**` payloads and the deployed `scripts/check.py`.
- Verify identity with `cmp -s` against the source after any tooling change.

**Why:** the dogfood exists so a change to one standard cannot silently break another. Suppressing a finding on a released payload's provider blinds the repository to its own cross-standard breakage.

**Gotcha:** BasedPyright never covered `scripts/` — `[tool.basedpyright] include` is `src` and `tests`. Confirm a gate's real scope before recording a blocker; a false one stalled the v5.15.0 preflight.

**Sources:** 2026-08-04 session; `pyproject.toml`; `e1ea40a6`.

**Related:** 1, 5, 7, 11.
