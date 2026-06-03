# Step 4 — Update templates & examples

> **Depends on:** [`02-schema.md`](02-schema.md). Targets: `templates/**` (excluded from validation — placeholders) and `examples/**` (validated, must pass).

## What was done

A deterministic per-file transform (quote-style-preserving) bumped `schema_version` `1.0` → `1.1` everywhere and inserted `consumer` at its canonical position (after `owner`, before `tags`) in every **standard-profile** file.

**Profile rule applied:** `consumer` is optional and belongs to the standard profile, so it was added only to files that carry `owner`. The one **minimal-profile** file, `templates/frontmatter-minimal.yml`, has no `owner` and received the version bump only.

| File group | schema_version | consumer |
| --- | --- | --- |
| `templates/frontmatter-minimal.yml` | → `1.1` | — (minimal profile) |
| `templates/frontmatter-standard.yml`, `templates/{note,concept,runbook,spec,research}.md`, `templates/adr*.md` (4) | → `1.1` | `unknown` (scaffolds don't presume) |
| `examples/adr.example.md` | → `1.1` | `user` |
| `examples/concept.example.md` | → `1.1` | `mix` |
| `examples/note.example.md` | → `1.1` | `agent` |
| `examples/runbook.example.md` | → `1.1` | `user` |

The four examples use **varied** `consumer` values on purpose — they are worked documents and should demonstrate three of the four enum values (`user`, `mix`, `agent`) rather than a uniform default.

**Quote style preserved per file:** double-quoted files (`*.yml`, `note/concept/runbook/spec/research.md`) emit `"1.1"` / `"unknown"`; single-quoted files (`adr*.md`, all examples) emit `'1.1'` / `'user'` etc. No incidental quote churn.

**No link rewrites (Path A):** examples keep their bare-ID `related` values (`immutable-infrastructure`, `adr-0001-…`). This is consistent with the SHOULD-not-MUST link wording promoted into the standard in Step 3 — the corpus does not contradict the standard.

## Verification

- `git diff` confirmed: only `schema_version` lines changed + one inserted `consumer` line per standard-profile file, at canonical position, correct quote style.
- `validate-frontmatter` ✓ 8 files — examples pass at `1.1` with `consumer`. (Templates are excluded by config, as intended.)
