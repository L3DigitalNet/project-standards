# HANDOFF — project-standards

> ## How this document works (permanent — read before editing)
>
> `working/HANDOFF.md` is the **single living handoff** for this repo: the one
> place a new session looks to learn the current state and the next action. It is
> intentionally short and always-current — a snapshot, not an append-only log.
>
> **Lifecycle**
>
> - **Session start:** read this file first, then read only what it points you to.
> - **During work:** keep _Current state_ and _Next action_ true to reality.
> - **Session end:** update those sections so the next session can start cold.
> - **When a body of work ships:** move its detailed planning docs to
>   `working/archive/<version>/`, leave a one-line pointer here, and reset
>   _Next action_ to the next piece of work.
>
> **Structure** — keep these sections, in order: _Current state_ · _Next action_ ·
> _Locked decisions_ · _Key files_ · _Constraints_ · _Open questions_. Detailed
> step-by-step records do **not** live here — they live under
> `working/archive/<version>/`.
>
> **Scope** — a self-contained, repo-local convention (one file plus an archive
> folder). Deliberately **not** the workstation v3 handoff system; see
> [`../AGENTS.md`](../AGENTS.md).

---

## Current state — V1.1 (`1.1.0`) ready to release

Repo: `/home/chris/projects/project-standards`. **Branch:** `testing` (all V1.1
work; `main` stays stable). As of 2026-06-03:

Implementation **and** the pre-release review are complete and committed on
`testing`; the full gate is green (`validate-frontmatter` ✓ 8, `pytest` 66,
`ruff` clean at line-length 88, `pyright` 0). Everything except the release
mechanics (Steps 9–10) is done.

The detailed 10-step plan and per-step decision records are archived at
[`archive/v1.1.0/`](archive/v1.1.0/) — start at
[`archive/v1.1.0/plans/00-overview.md`](archive/v1.1.0/plans/00-overview.md).

| Step | State |
| --- | --- |
| 1 scoping → 7 changelog | ✅ committed on `testing` |
| 6 migration | ⛔ skipped (Path A — no link migration) |
| Pre-release review + fixes | ✅ README staleness, schema key-order, dogfood uniformity; ruff line-length 88 split into its own commit |
| 8 verify gate | ✅ green (re-run on the release commit) |
| 9 release | ⏳ **needs user** |
| 10 post-release | ⏳ |

## Next action — cut the release (Step 9, needs user)

1. **Integrate `testing → main`** (merge vs rebase — see
   `superpowers:finishing-a-development-branch`). The release commit + tags
   belong on `main`.
2. **Release commit on `main`:** bump `pyproject.toml` `1.0.2` → `1.1.0`;
   regenerate `uv.lock`; change the `CHANGELOG.md` heading
   `## [1.1.0] — unreleased` → `## [1.1.0] — <date>`.
3. **Tag + push — outward-facing, explicit user approval:** annotated
   GPG-signed `v1.1.0` (key `9375AFEFA6F841B0`); move `v1` by delete-and-re-push
   (never `--force`; the `release-pipeline` guard is server-side); push commit +
   tags to `github.com/L3DigitalNet/project-standards`.
4. **Step 10 — post-release:** confirm the tag resolves and
   `uvx … @v1` / `uv tool install` picks up `1.1.0`; optional downstream `@v1`
   smoke test.

## Locked decisions (do not relitigate)

- **Path A → `1.1.0`** (additive minor): `consumer` + the `'1.1'` enum widening
  are both MINOR-class.
- Add `consumer`, enum `user | agent | mix | unknown`. **Keep `license`.**
- Link form (repo-root-relative paths) is **documented convention only** this
  release — _not_ schema-enforced. Path-pattern enforcement is deferred to a
  future `2.0.0` (it would be breaking: 7 in-repo docs use bare-id links).
- `schema_version` (the metadata-schema version) is **distinct** from the repo
  release tag (`vMAJOR.MINOR.PATCH`); the latter is governed by
  [`../standards/versioning.md`](../standards/versioning.md).
- Every managed doc in this repo now declares `schema_version: '1.1'`.

## Key files

| Path | Role |
| --- | --- |
| `working/HANDOFF.md` | this file — the living handoff |
| [`archive/v1.1.0/`](archive/v1.1.0/) | frozen V1.1 plans, converged proposal, `consumer` provenance |
| `schemas/markdown-frontmatter.schema.json` | authoritative machine contract (V1.1 applied) |
| `standards/markdown-frontmatter.md` | the published standard (promoted to V1.1) |
| `standards/versioning.md` | release ritual + previously-passing rule (authoritative) |
| `CHANGELOG.md` | carries `## [1.1.0] — unreleased`; date it in the release commit |
| `pyproject.toml` | bump `1.0.2` → `1.1.0` at release |

## Constraints to respect (from `AGENTS.md` + `standards/versioning.md`)

- The JSON schema is **authoritative**; update it first, prose follows.
- **Previously-passing rule:** any change that can fail a previously-passing doc → MAJOR.
- One version tags all four components (standard, schema, validator, workflow).
- Release: annotated **GPG-signed**, immutable full-version tag; move `vN` by
  delete-and-re-push (**never `git push --force`**); bump `pyproject.toml` +
  regenerate `uv.lock`; Keep a Changelog format.
- Green gate before tagging: `validate-frontmatter`, `pytest`, `ruff check`, `pyright`.
- **Dogfood:** managed Markdown here must validate; never add frontmatter to
  `CLAUDE.md` / `AGENTS.md` / `.claude/**`.

## Open questions

- ~~Q1–Q3~~ resolved during the build (see `archive/v1.1.0/plans/`).
- **Q4 (Step 9):** confirm the GPG key + the server-side `release-pipeline` guard
  behaviour before moving the `v1` tag.
