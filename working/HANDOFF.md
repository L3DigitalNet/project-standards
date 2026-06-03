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

## Current state — `1.2.0` released

Repo: `/home/chris/projects/project-standards`. **Branch:** `testing` (dev; `main`
holds releases, moving tag `v1` tracks the newest). As of 2026-06-03 the published
line is:

| Tag | What shipped |
| --- | --- |
| `v1.0.x` | initial Markdown Frontmatter + ADR + Versioning standards, validator, reusable workflow |
| `v1.1.0` | optional `consumer` field; `schema_version` enum widened to accept `1.1` |
| `v1.2.0` | `standards/adoption.md` (agent onboarding/compliance procedure); `standards-ref` pinning hardened (workflow default `main`→`v1`); validator no longer crashes on malformed YAML; README/standard/versioning doc fixes |

Gate green: `validate-frontmatter` ✓ 9, `pytest` 70, `ruff` clean @ line-length 88,
`pyright` 0. Per-release planning is archived under [`archive/`](archive/) (one
folder per release; start at the version's `README.md`).

## Next action — none pending

`1.2.0` is shipped and verified. No open work item. The only thing on the radar is
the **`2.0.0`** under _Future work_ — undertake deliberately, not by default.

## Locked decisions / standing context (do not relitigate)

- **Link form is convention, not enforced.** Repo-root-relative paths are a
  documented SHOULD; the schema does **not** check link shape. Enforcing it is the
  headline **`2.0.0`** change (breaking — in-repo and consumer docs use bare-id
  links), requiring a major bump + migration notes.
- **`standards-ref` must track the `@vN` workflow pin.** The reusable workflow now
  defaults it to `v1`; consumers should still set it explicitly. Documented in
  `README.md` and `standards/adoption.md`.
- **One tag ships four components** (standard, schema, validator, workflow); classify
  every release by the previously-passing rule in
  [`../standards/versioning.md`](../standards/versioning.md). A default/behaviour
  change that _cannot_ fail a previously-passing caller is **MINOR** (the
  classification table now states this explicitly).
- Every managed doc in this repo declares `schema_version: '1.1'`.

## Key files

| Path | Role |
| --- | --- |
| `working/HANDOFF.md` | this file — the living handoff |
| [`archive/`](archive/) | frozen per-release planning docs (`v1.1.0/`, …) |
| `standards/markdown-frontmatter.md` | the published standard |
| `standards/adoption.md` | agent onboarding & compliance procedure (hand to consuming repos) |
| `standards/versioning.md` | release ritual + change classification (authoritative) |
| `schemas/markdown-frontmatter.schema.json` | authoritative machine contract |
| `tools/validate_frontmatter.py` · `tests/` | validator CLI + tests |
| `.github/workflows/validate-markdown-frontmatter.yml` | reusable workflow consumers call |
| `CHANGELOG.md` · `pyproject.toml` | changelog + package version (bump at release) |

## Constraints / release ritual (from `AGENTS.md` + `standards/versioning.md`)

- The JSON schema is **authoritative**; update it first, prose follows.
- **Previously-passing rule:** any change that can fail a previously-passing
  consumer doc or workflow run → MAJOR.
- Release: bump `pyproject.toml` + regen `uv.lock`; date the `CHANGELOG.md` section;
  green gate; fast-forward `main` to `testing`; annotated **GPG-signed** immutable
  `vMAJOR.MINOR.PATCH` tag (key `9375AFEFA6F841B0`); move `v1` by
  **delete-and-re-push** (never `--force`; the server-side `release-pipeline-tags`
  ruleset allows the `v1` move, blocks `v*.*.*` deletion); push `main` + `testing` +
  tags; verify `uvx … @v1` resolves the new version.
- **Dogfood:** managed Markdown here must validate; never add frontmatter to
  `CLAUDE.md` / `AGENTS.md` / `.claude/**`.

## Open questions

- None open.

## Future work

- **`2.0.0` (deliberate, breaking):** enforce repo-root-relative link patterns in the
  schema; migrate in-repo bare-id links; write consumer migration notes; bump to `@v2`.
