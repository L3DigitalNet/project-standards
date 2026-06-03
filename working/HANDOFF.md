# HANDOFF — Frontmatter Standard V1.1 release work

> **New session: start here.** Read this file, then [`plans/00-overview.md`](plans/00-overview.md) (the release plan) and [`schema/schema.frontmatter.md`](schema/schema.frontmatter.md) (the converged spec). Repo: `/home/chris/projects/project-standards`. Today is 2026-06-03. **Branch:** all V1.1 release work happens on the `testing` branch (created 2026-06-03); `main` stays stable. Verify with `git switch testing` before starting.

## Where we are

**Steps 1–5 of the release plan are DONE and committed on `testing`** (target `1.1.0`, Path A). The implementation is complete and the full toolchain is green (`validate-frontmatter` ✓ 8, `pytest` 66, `ruff` clean, `pyright` 0). What remains is the changelog + the release mechanics (tag/push), which need user-driven decisions.

Commits this session (newest first): `b7dfe81` Step 5 tests · `6974867` Step 4 templates/examples · `ef1aeb1` Step 3 standard · `3f1e0ff` Step 2 schema · `d09ec58` Step 1 scoping. Each step's decision record is in `plans/0N-*.md`.

| Step | State | Notes |
| --- | --- | --- |
| 1 scoping | ✅ | Path A, `1.1.0` |
| 2 schema | ✅ | `consumer` + `'1.1'` enum + narrowed `visibility`; no link patterns |
| 3 standard | ✅ | promoted wholesale; links→SHOULD/convention; Versioning/Validation trimmed to pointers |
| 4 templates/examples | ✅ | `1.1` + `consumer` everywhere; examples use varied values; minimal yml version-only |
| 5 tests | ✅ | +9 additive cases; fixtures stay `1.0` for back-compat coverage |
| 6 migration | ⛔ skipped | Path A — no link migration |
| 7 changelog | ⏳ next | see release findings below |
| 8 verify gate | ⏳ | already green; re-run on the release commit |
| 9 release | ⏳ user | bump + uv.lock + GPG tag + move `v1` + push |
| 10 post-release | ⏳ | tag/install resolves; consumer smoke test |

## The next action

**Step 7 (changelog), then the release sequence (8–10).** Three findings refine how:

1. **`[Unreleased]` already has two pre-existing entries** (Apache-2.0 `LICENSE` add; versioning-standard force-push wording). Both additive/non-breaking. Step 7 must fold these into the `[v1.1.0]` section **together with** the new frontmatter entries (`Added: consumer`; `Changed: visibility` description + link rule now stated as convention; `schema_version` `1.1`).
2. **The `release-pipeline` guard is server-side** (no local pre-push hook — only `.sample` files). Tag move uses delete-and-re-push, never `--force`. Confirm against the GitHub ruleset (Q4).
3. **Release requires integrating `testing → main`.** The work is on `testing`; the release commit + `v1.1.0` tag + moved `v1` belong on `main`. Decide merge vs rebase (consider `superpowers:finishing-a-development-branch`). Pushing an org repo (`github.com/L3DigitalNet/project-standards`) + moving the `v1` tag is **outward-facing — needs explicit user approval.**

### ✅ Step 1 decision (was the gate): Path A — `1.1.0` (minor)

Full rationale + evidence in `plans/01-scoping.md`.

- **Target version `1.1.0`** (current release `1.0.2` on moving tag `v1`).
- `consumer` (additive) + `'1.1'` enum widening are both MINOR-class.
- The repo-root link rule ships as **documented convention only** — no schema `items.pattern` this release. Enforcing it would tighten a rule and newly-fail **7** currently-passing managed docs, making it MAJOR → deferred to a future `2.0.0`.

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
