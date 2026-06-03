# HANDOFF — Frontmatter Standard V1.1 release work

> **New session: start here.** Read this file, then [`plans/00-overview.md`](plans/00-overview.md) (the release plan) and [`schema/schema.frontmatter.md`](schema/schema.frontmatter.md) (the converged spec). Repo: `/home/chris/projects/project-standards`. Today is 2026-06-03. **Branch:** all V1.1 release work happens on the `testing` branch (created 2026-06-03); `main` stays stable. Verify with `git switch testing` before starting.

## Where we are

We have spent this session reviewing and polishing a **proposed v1.1 of the Markdown Frontmatter Standard** to convergence (multi-pass: internal consistency, doc↔schema cross-checks, layout, live-code verification, spelling). The spec is now internally consistent and self-converged — **no substantive findings remain.**

All work lives in **`working/` (untracked, local only)**. **Nothing in the real repo (`schemas/`, `standards/`, `templates/`, `examples/`, `tests/`, `CHANGELOG.md`, `pyproject.toml`) has been changed.** This is still 100% pre-implementation.

## The next action

Begin **Step 2 of the release plan: update the JSON schema** (authoritative, do first). Step 1 is **DONE** — see [`plans/01-scoping.md`](plans/01-scoping.md). Detail doc `plans/02-schema.md` is **not yet written**.

Step 2 scope (Path A): add the optional `consumer` property + enum (`user|agent|mix|unknown`); add `'1.1'` to the `schema_version` enum (keep `'1.0'`); narrow the `visibility` description. **Do NOT** add `items.pattern` to link fields — that is the deferred breaking change.

### ✅ Step 1 decision (was the gate): Path A — `1.1.0` (minor)

Resolved 2026-06-03 with the user. Full rationale + evidence in `plans/01-scoping.md`.

- **Target version `1.1.0`** (current release `1.0.2` on moving tag `v1`).
- `consumer` (additive) + `'1.1'` enum widening are both MINOR-class.
- The repo-root link rule ships as **documented convention only** — no schema `items.pattern` this release. Enforcing it would tighten a rule and newly-fail **7** currently-passing managed docs (`standards/adr.md`, `standards/versioning.md`, `CHANGELOG.md`, and all four `examples/*.example.md`), making it MAJOR → deferred to a future `2.0.0`.
- **Spec edit this forces (do in Step 3):** soften the "enforced by the validator" link claim at `schema/schema.frontmatter.md:336` to "by convention," and drop the `(PROPOSED V1.1)` title qualifier.
- **Step 6 (migration) does not run** under Path A.

## Decisions already locked (do not relitigate)

- Add `consumer` field, enum `user | agent | mix | unknown`.
- **Keep `license`** (re-added; removing it would be breaking — this is why the release is additive, not a removal).
- Links use **repo-root-relative paths**, extension included (Option A); `applies_to` is exempt (free-form scope identifiers, not links).
- `schema_version` value moves `1.0 → 1.1`.
- `schema_version` (metadata-schema version) is **distinct** from the repo release tag (`vMAJOR.MINOR.PATCH`); the latter is governed by `standards/versioning.md`.

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
- Release: annotated **GPG-signed**, immutable full-version tag; move `vN` by delete-and-re-push (**never `git push --force`** — `release-pipeline` guard blocks it); bump `pyproject.toml` + regenerate `uv.lock`; Keep a Changelog format.
- Green gate before tagging: `uv run validate-frontmatter --config .project-standards.yml`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`.
- **Dogfood:** managed Markdown here must validate; never add frontmatter to `CLAUDE.md`/`AGENTS.md`/`.claude/**`.

## Open questions (parked for per-step planning)

- ~~**Q1 (Step 1):** Path A or Path B?~~ **RESOLVED → Path A (`1.1.0`).** See `plans/01-scoping.md`.
- **Q2 (Step 3):** Does the spec _replace_ `standards/markdown-frontmatter.md` or merge in? Which new sections (Versioning, Validation) stay vs defer to `versioning.md` / `README.md`?
- **Q3 (Step 5):** Existing `tests/` fixtures pattern to extend, or a new invalid-cases corpus?
- **Q4 (Step 9):** Confirm GPG key + `release-pipeline` guard behavior before the `vN` tag move.

## Suggested first move in the new session

1. Read this file + `plans/00-overview.md` + `plans/01-scoping.md` (the locked decision).
2. Write `plans/02-schema.md`, then edit `schemas/markdown-frontmatter.schema.json`: add `consumer` + enum, add `'1.1'` to the `schema_version` enum, narrow the `visibility` description. No link patterns.
3. Re-validate the schema as Draft 2020-12, then proceed to Steps 3–5.
