# HANDOFF — Frontmatter Standard V1.1 release work

> **New session: start here.** Read this file, then
> [`plans/00-overview.md`](plans/00-overview.md) (the release plan) and
> [`schema/schema.frontmatter.md`](schema/schema.frontmatter.md) (the converged spec).
> Repo: `/home/chris/projects/project-standards`. Today is 2026-06-03.
> **Branch:** all V1.1 release work happens on the `testing` branch (created 2026-06-03);
> `main` stays stable. Verify with `git switch testing` before starting.

## Where we are

We have spent this session reviewing and polishing a **proposed v1.1 of the Markdown
Frontmatter Standard** to convergence (multi-pass: internal consistency, doc↔schema
cross-checks, layout, live-code verification, spelling). The spec is now internally
consistent and self-converged — **no substantive findings remain.**

All work lives in **`working/` (untracked, local only)**. **Nothing in the real repo
(`schemas/`, `standards/`, `templates/`, `examples/`, `tests/`, `CHANGELOG.md`,
`pyproject.toml`) has been changed.** This is still 100% pre-implementation.

## The next action

Begin **Step 1 of the release plan: release scoping & version classification** — a
**decision gate** that fixes the version number. Detail doc `plans/01-scoping.md` is
**not yet written**; writing/working it is the next task.

### ⚠️ The decision that blocks everything

"V1.1" and "enforce link patterns in the schema" cannot both be true:

- Adding `consumer` is **additive → `1.1.0`** (minor).
- Adding link-path `items.pattern`s to `related`/`supersedes`/etc. **tightens a rule**,
  and existing repo docs already violate it (`standards/adr.md` uses a bare ID
  `markdown-frontmatter-standard` in `related`). Per `standards/versioning.md`'s
  **previously-passing rule**, that is **breaking → `2.0.0`**.

Two paths to choose from (this is open question Q1):

- **Path A — `1.1.0`:** ship `consumer` + links as *documented convention only* (no
  schema pattern yet); defer pattern enforcement to a future `2.0.0`. Would require
  softening the spec's "enforced by the validator" link claim to "by convention."
- **Path B — `2.0.0`:** enforce link patterns now + migrate every in-repo doc to path
  form + write consumer migration notes.

**Do not start Step 2 (schema edits) until this is decided.**

## Decisions already locked (do not relitigate)

- Add `consumer` field, enum `user | agent | mix | unknown`.
- **Keep `license`** (re-added; removing it would be breaking — this is why the release
  is additive, not a removal).
- Links use **repo-root-relative paths**, extension included (Option A); `applies_to` is
  exempt (free-form scope identifiers, not links).
- `schema_version` value moves `1.0 → 1.1`.
- `schema_version` (metadata-schema version) is **distinct** from the repo release tag
  (`vMAJOR.MINOR.PATCH`); the latter is governed by `standards/versioning.md`.

## Key files

| Path | Role |
| --- | --- |
| `working/HANDOFF.md` | this file |
| `working/plans/00-overview.md` | **the release plan** — 10 steps, sequencing, open questions |
| `working/schema/schema.frontmatter.md` | the converged spec (titled "PROPOSED V1.1") |
| `working/schema/IMPLEMENTATION-NOTE.md` | superseded by the plan; kept for reference |
| `schemas/markdown-frontmatter.schema.json` | the authoritative machine contract (unchanged; edit first in Step 2) |
| `standards/markdown-frontmatter.md` | the current published standard (v1.0) to promote into |
| `standards/versioning.md` | release ritual + previously-passing rule (authoritative) |
| `.project-standards.yml` | validator config (include/exclude globs) |
| `tools/validate_frontmatter.py` | the validator (frontmatter only; exit codes 0/1/2) |
| `CHANGELOG.md`, `pyproject.toml` | touched only at release (Steps 7, 9) |

## Constraints to respect (from `AGENTS.md` + `standards/versioning.md`)

- The JSON schema is **authoritative**; update it first, prose follows.
- **Previously-passing rule:** any change that can fail a previously-passing doc → MAJOR.
- One version tags all four components (standard, schema, validator, workflow).
- Release: annotated **GPG-signed**, immutable full-version tag; move `vN` by
  delete-and-re-push (**never `git push --force`** — `release-pipeline` guard blocks it);
  bump `pyproject.toml` + regenerate `uv.lock`; Keep a Changelog format.
- Green gate before tagging: `uv run validate-frontmatter --config .project-standards.yml`,
  `uv run pytest`, `uv run ruff check .`, `uv run pyright`.
- **Dogfood:** managed Markdown here must validate; never add frontmatter to
  `CLAUDE.md`/`AGENTS.md`/`.claude/**`.

## Open questions (parked for per-step planning)

- **Q1 (Step 1):** Path A (`1.1.0`, convention-only links) or Path B (`2.0.0`, enforced links)?
- **Q2 (Step 3):** Does the spec *replace* `standards/markdown-frontmatter.md` or merge in?
  Which new sections (Versioning, Validation) stay vs defer to `versioning.md` / `README.md`?
- **Q3 (Step 5):** Existing `tests/` fixtures pattern to extend, or a new invalid-cases corpus?
- **Q4 (Step 9):** Confirm GPG key + `release-pipeline` guard behavior before the `vN` tag move.

## Suggested first move in the new session

1. Read this file + `plans/00-overview.md`.
2. Resolve **Q1** (Path A vs B) with the user — it gates everything.
3. Write `plans/01-scoping.md` capturing the decision + rationale + resulting version.
