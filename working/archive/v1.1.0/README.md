# Archive — v1.1.0 release planning

Frozen planning record for the **v1.1.0** release of the Markdown Frontmatter Standard (the additive `consumer` field + `schema_version` `1.1`). These are working documents, archived once the work shipped; they are **not** governing artifacts. The authoritative outputs live in the repo proper (`schemas/`, `standards/`, `templates/`, `examples/`, `tests/`, `CHANGELOG.md`).

## Contents

- `plans/00-overview.md` — the 10-step release plan and sequencing.
- `plans/01-scoping.md` — the decision gate: Path A (`1.1.0`), with the classification rationale and the 7-doc blast radius that ruling avoided.
- `plans/02-schema.md` … `plans/07-changelog.md` — per-step decision records (schema, standard prose, templates/examples, tests, changelog). There is no `06`: Step 6 (link migration) was cancelled under Path A.
- `schema/schema.frontmatter.md` — the converged proposal text that was promoted into `standards/markdown-frontmatter.md`.
- `schema/IMPLEMENTATION-NOTE.md` — the earliest implementation note, superseded by `plans/00-overview.md`.

## Provenance: where `consumer` came from

The `consumer` field originated from a one-line user request captured in a root-level `NOTES.md` (since removed, as the idea has shipped):

> add "audience" as schema field: all, user, agent

V1.1 implements exactly this — renamed `audience` → `consumer` to avoid publishing-tool collisions, with controlled values `user | agent | mix | unknown` (`all` → `mix`, plus `unknown` for the unset case).
