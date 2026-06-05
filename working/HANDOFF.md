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

**2026-06-04 planning session (design only — nothing implemented).** Scoped the
linting/formatting stack and the upcoming **ADR/MADR** standard. Produced **8 locked
decisions** (DEC-1…DEC-8) with full trails in
[`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md).
**No `standards/`, `schemas/`, `tools/`, or `.github/` files were changed.** Repo
remains at `1.2.0`, gate still green.

## Next action — review `.markdownlint.json`, then implement the DEC backlog

User is reviewing [`../.markdownlint.json`](../.markdownlint.json) before any Stack-B
work. **Hold all implementation until then.** When cleared, the next body of work is
the **ADR/MADR-4 standard + Stack-B linting** (a `1.3.0`-shaped *additive* release —
see _Future work_). The apply-order backlog is the bottom of the decisions doc
("Implementation backlog"). Two flagged risks: (a) the new lint workflow self-running
would lint never-linted managed docs → possible red CI, so wire it `workflow_call`-only
first or fix violations in the same change; (b) the `.markdownlint.json` MD024 tweak
(Δ3) is part of that review.

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

### Linting/formatting + MADR-4 decisions (2026-06-04 — trails in the decisions doc)

Eight decisions, settled with primary-source evidence. Do **not** relitigate; if
revisiting, read the trail + re-eval trigger in
[`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md).

| # | Decision |
| --- | --- |
| DEC-1 | ADR standard targets **MADR 4.0** (repo body/templates already conform; deltas are config-tweaks) |
| DEC-2 | `vscode-adr-manager` extension = **optional convenience**, not a conformance target |
| DEC-3 | Stack-B linter = **markdownlint-cli2** (reference engine; reads our published `.markdownlint.json`) |
| DEC-4 | Frontmatter key-order/quoting/list-style stay **documented convention** (schema = sole gate) |
| DEC-5 | **Opt-in, default-off** validator check for the 3 required ADR sections (`markdown.adr.require_sections`) |
| DEC-6 | **Hybrid** ADR naming: filename `NNNN-title.md` (MADR) + id `adr-NNNN-title` → documented filename≠id exception |
| DEC-7 | CI uses **`markdownlint-cli2-action@v23`**; no committed Node project (refines DEC-3) |
| DEC-8 | **Separate opt-in** reusable workflow `lint-markdown.yml` (don't fold into the frontmatter workflow) |

Cross-cutting: Stack B (markdownlint) is currently a **config file with no runner** —
not wired into CI today. The above wires it; default-off / opt-in keeps the release
**additive (minor)**.

## Key files

| Path | Role |
| --- | --- |
| `working/HANDOFF.md` | this file — the living handoff |
| [`linting-formatting/linting-formatting-stack.md`](linting-formatting/linting-formatting-stack.md) | **active planning doc** — DEC-1…8 trails + implementation backlog |
| [`../.markdownlint.json`](../.markdownlint.json) | Stack-B config (under user review before wiring) |
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

- None. All eight 2026-06-04 decisions are settled; the only pending item is the
  user's review of `.markdownlint.json` (a human gate, not an open design question).

## Future work

- **`1.3.0` (additive — ADR/MADR-4 + Stack-B linting):** implement DEC-1…DEC-8 per the
  decisions doc's backlog — MADR-4 doc tweaks, `lint-markdown.yml` + `markdownlint-cli2-action`,
  opt-in `markdown.adr.require_sections` validator check (+ tests), ADR filename/id convention.
  All default-off / opt-in / additive → MINOR. Gated on the `.markdownlint.json` review.
- **`2.0.0` (deliberate, breaking):** enforce repo-root-relative link patterns in the
  schema; migrate in-repo bare-id links; write consumer migration notes; bump to `@v2`.
