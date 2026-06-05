# Implementation Note — Frontmatter Standard V1.1

**Superseded by** the release plan at [`../plans/00-overview.md`](../plans/00-overview.md) — this note's checklist is now Step 2 (schema) and Step 7 (changelog) there. Kept for reference.

**Status:** proposal is in polishing; schema/standards implementation NOT yet started. Source of truth for the proposed changes: [`schema.frontmatter.md`](schema.frontmatter.md) (titled "PROPOSED V1.1").

> Do this only after polishing `schema.frontmatter.md` is finished. V1.1 touches the real versioned contract, so it lands as one reviewable changeset following the AGENTS.md versioning ritual (schema + standards + templates + examples + tests + CHANGELOG + tag), not piecemeal.

## What V1.1 is

Additive minor release. One new field (`consumer`); `license` retained (do **not** remove it — removal would be breaking and would invalidate existing docs that set `license:`).

## Required changes to `schemas/markdown-frontmatter.schema.json`

1. **Add `consumer`** — `{"type": "string", "enum": ["user", "agent", "mix", "unknown"]}`.
2. **Extend `schema_version` enum** to `["1.0", "1.1"]` (keep `1.0` so older docs stay valid).
3. **Add repo-root-relative path patterns** (`items.pattern`, no leading `/`, extension required) to `related`, `supersedes`, `depends_on`, and a string-or-null path pattern to `superseded_by`. Rewrite their descriptions from "Document IDs" → "repo-root-relative path." This is what makes the proposal's "enforced by `tools/validate_frontmatter.py`" claim true.
4. **Narrow `visibility` description** — drop "Intended audience or," leaving "exposure level" (now that `consumer` owns audience).
5. **Leave `license` and `applies_to` unchanged** (`applies_to` = free-form scope identifiers, not links).

## Downstream (same changeset)

- Mirror all of the above into `standards/markdown-frontmatter.md` (add `consumer` field + controlled values, the path-form link rule, narrowed `visibility` description).
- Update templates/examples to carry `schema_version: '1.1'` and the `consumer` field.
- Add a `CHANGELOG.md` entry; cut tag `v1.1.0`.
- Run `uv run validate-frontmatter --config .project-standards.yml`, `uv run pytest`, `uv run ruff check .`, `uv run pyright` — all green before tagging.
