# Release Plan — Markdown Frontmatter Standard (overview)

**Status:** master plan. Each step below gets its own detail document (`NN-*.md`) in this directory; this file stays at summary altitude and is the index.

**Supersedes:** [`../schema/IMPLEMENTATION-NOTE.md`](../schema/IMPLEMENTATION-NOTE.md) — its checklist is absorbed into Step 2 and Step 7 here.

**Goal:** take the converged proposal at [`../schema/schema.frontmatter.md`](../schema/schema.frontmatter.md) (currently "PROPOSED V1.1") through to a tagged, published release of all four shipped components (standard, JSON schema, validator CLI, reusable workflow).

---

## Current state

- The proposal text is internally consistent and self-converged (multi-pass review complete).
- Design decisions already locked: add `consumer` (enum `user|agent|mix|unknown`); retain `license`; links are repo-root-relative paths (Option A); `schema_version` moves `1.0 → 1.1`; `applies_to` exempt from the link rule.
- **Nothing in `schemas/`, `standards/`, `templates/`, `examples/`, `tests/`, or `CHANGELOG.md` has been touched yet.** All changes still live in `working/`.

## Guiding constraints (from `standards/versioning.md` + `AGENTS.md`)

1. **Previously-passing rule.** If any change can turn a previously-passing consumer document or workflow run into a failure, the release is **MAJOR** — no exceptions, even for bug fixes.
2. **One version, four components.** Standard, schema, validator, and workflow ship together under one `vMAJOR.MINOR.PATCH` tag.
3. **The schema is authoritative.** Update it first; prose follows it.
4. **Release mechanics.** Annotated, GPG-signed, immutable full-version tags; the moving `vN` tag advances by delete-and-re-push (never `git push --force` — blocked by the `release-pipeline` guard). Bump `pyproject.toml` + regenerate `uv.lock`. Keep a Changelog format; MAJOR releases carry migration notes.
5. **Green gate.** `validate-frontmatter`, `pytest`, `ruff`, `pyright` all pass before tagging.

---

## ⚠️ Step 1 is a decision gate that sets the version number

> **RESOLVED 2026-06-03 → Path A, target `1.1.0`.** Decision record: [`01-scoping.md`](01-scoping.md). The analysis below is retained for context.

The release cannot be both "1.1" and "enforces link patterns":

- `consumer` alone is **additive → `1.1.0`** (minor).
- Adding `items.pattern` to `related`/`supersedes`/`depends_on`/`superseded_by` **tightens a rule**, and in-repo docs already use non-path forms (e.g. `standards/adr.md` → `related: ['markdown-frontmatter-standard']`). Tightening that pattern fails a previously-passing doc → **breaking → `2.0.0`**.

Resolve this **before** any file changes. Two viable shapes (decide in Step 1):

- **Path A — Minor `1.1.0`.** Ship `consumer` + the link rule as documented _convention_ only (no schema pattern yet). Defer pattern enforcement to a future `2.0.0`. Requires softening the proposal's "enforced by the validator" claim for links to "by convention."
- **Path B — Major `2.0.0`.** Ship `consumer` _and_ the enforcing link patterns now, migrate all in-repo docs to path form, and write consumer migration notes.

Everything downstream (schema diff, CHANGELOG classification, migration scope, the proposal's own title and Versioning section) depends on this choice.

---

## Steps

| # | Step | Primary outputs | Detail doc |
| --- | --- | --- | --- |
| 1 | Release scoping & version classification | Locked scope + target version + rationale | `01-scoping.md` |
| 2 | Update the JSON schema | `schemas/markdown-frontmatter.schema.json` | `02-schema.md` |
| 3 | Promote the standard prose | `standards/markdown-frontmatter.md` | `03-standard.md` |
| 4 | Update templates & examples | `templates/**`, `examples/**` | `04-templates-examples.md` |
| 5 | Update validator tests (TDD) | `tests/**` | `05-tests.md` |
| 6 | Migrate in-repo docs (conditional) | Existing managed docs, consumer migration notes | `06-migration.md` |
| 7 | Update the changelog | `CHANGELOG.md` | `07-changelog.md` |
| 8 | Local verification gate | Green `validate`/`pytest`/`ruff`/`pyright` | `08-verify.md` |
| 9 | Cut the release | Version bump, `uv.lock`, signed tags, push | `09-release.md` |
| 10 | Post-release verification | Tag/install resolves; consumer smoke test | `10-post-release.md` |

### Step 1 — Release scoping & version classification _(decision gate)_

Decide Path A vs Path B above; fix the target version; record the classification rationale per the previously-passing rule. **Blocks all other steps.**

### Step 2 — Update the JSON schema _(authoritative; do first)_

Add `consumer` property + enum; add `"1.1"` to the `schema_version` enum; narrow the `visibility` description; keep `license`/`applies_to`. Add link `items.pattern`s **only if Step 1 = Path B**. Re-validate the schema as Draft 2020-12.

### Step 3 — Promote the standard prose

Reconcile the finalized proposal with the existing `standards/markdown-frontmatter.md`: decide what merges, what the proposal's new sections (Versioning, Validation) should defer to (`versioning.md`, `README.md`) vs restate, and ensure the standard's own frontmatter validates (its `schema_version` becomes `'1.1'`). Drop the `(PROPOSED …)` title.

### Step 4 — Update templates & examples

Add `consumer` and `schema_version: '1.1'` to `templates/**`; update `examples/**` worked docs. Remember: `templates/**` is excluded from validation (placeholders); `examples/**` is validated and must pass.

### Step 5 — Update validator tests (TDD)

Write failing tests first for every new/changed constraint: `consumer` enum accept/reject, `schema_version: '1.1'` accepted while `'1.0'` still valid, and (Path B) link-pattern accept path / reject bare-id / reject absolute / reject section-link.

### Step 6 — Migrate in-repo docs _(only if Step 1 = Path B)_

Sweep `standards/`, `examples/`, `CHANGELOG.md` for non-path `related`/`supersedes` values and convert them; capture a consumer-facing migration recipe for the changelog.

### Step 7 — Update the changelog

Move `## [Unreleased]` into `## [vTARGET] — YYYY-MM-DD` (Keep a Changelog). `Added:` `consumer`. `Changed:` link form / `visibility` description. Path B adds a **migration** subsection.

### Step 8 — Local verification gate

Run `uv run validate-frontmatter --config .project-standards.yml`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`. All green, or loop back.

### Step 9 — Cut the release

Bump `pyproject.toml`; regenerate `uv.lock`; commit; create the annotated GPG-signed `vTARGET` tag; advance the moving `vN` tag by delete-and-re-push; push commit and tags.

### Step 10 — Post-release verification

Confirm the tag resolves and `uv tool install` picks up the matching version; optionally run a downstream consumer against `@vN` to confirm the workflow still passes.

---

## Sequencing & dependencies

```text
1 (gate) ─▶ 2 (schema) ─▶ 3 (standard) ─▶ 4 (templates/examples)
                       └▶ 5 (tests)        └▶ 6 (migration, Path B only)
                                                   └▶ 7 (changelog) ─▶ 8 (verify) ─▶ 9 (release) ─▶ 10 (post)
```

- Step 2 precedes 3–5: the schema is the contract the prose, examples, and tests describe.
- Steps 3, 4, 5 can proceed in parallel once Step 2 lands.
- Step 6 exists only under Path B and must complete before Step 8 can go green.
- Step 8 is a hard gate before Step 9; Step 9 before Step 10.

## Open questions to resolve during per-step planning

- ~~**Q1 (Step 1):** Path A or Path B?~~ **RESOLVED 2026-06-03 → Path A (`1.1.0`).** Decision record: [`01-scoping.md`](01-scoping.md). Step 6 (migration) does not run.
- **Q2 (Step 3):** Does the proposal _replace_ `standards/markdown-frontmatter.md`, or merge into it? Which new sections stay vs defer to `versioning.md` / `README.md`?
- **Q3 (Step 5):** Is there an existing fixtures pattern in `tests/` to extend, or do we add a new invalid-cases corpus?
- **Q4 (Step 9):** Confirm the GPG signing key and the `release-pipeline` guard behavior before attempting the `vN` tag move.
