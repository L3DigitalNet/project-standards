# Step 2 — Update the JSON schema (authoritative)

> **Depends on:** [`01-scoping.md`](01-scoping.md) (Path A, target `1.1.0`). The schema is the contract Steps 3–5 describe, so it changes first. Target file: `schemas/markdown-frontmatter.schema.json` (JSON Schema Draft 2020-12).

## Exact changes (all additive under Path A)

1. **Widen `schema_version` enum.** `["1.0"]` → `["1.0", "1.1"]`. Keeps every existing `1.0` document valid; lets `1.1` documents validate.
2. **Add the optional `consumer` property.** `{"type": "string", "enum": ["user", "agent", "mix", "unknown"], "description": "Intended reader/consumer of the document."}`. Placed after `owner` and before `tags` to match the standard's canonical key order. Not added to `required`, so its absence never fails a document.
3. **Narrow the `visibility` description.** `"Intended audience or exposure level."` → `"Exposure level."` — `consumer` now owns the audience dimension, so `visibility` is purely the exposure axis. Description-only; the `enum` is unchanged, so no document's pass/fail outcome moves.

## Explicitly NOT done this step (deferred to `2.0.0`)

- **No `items.pattern` on `related` / `supersedes` / `depends_on` / `superseded_by`.** Adding it would tighten a rule and newly-fail 7 managed docs (see `01-scoping.md`). The link rule stays documented convention only.
- **No rewrite of the link-field descriptions** (`related` keeps "Related document IDs or relative paths," etc.). Aligning that prose toward the path convention is a non-breaking wording choice better made in Step 3 alongside the standard text, and is flagged there — not folded into the contract here.

## Verification for this step

- The file parses as JSON and is a structurally valid Draft 2020-12 schema (compiles under `jsonschema`).
- Sanity-validate a `consumer: 'agent'` + `schema_version: '1.1'` document against the edited schema (accepts), and a `consumer: 'robot'` document (rejects on enum), and a `schema_version: '1.2'` document (rejects on enum).

## Result (verified 2026-06-03)

All three edits applied. Verification ran clean:

- **Schema compiles** as Draft 2020-12 (`Draft202012Validator.check_schema`).
- **Probes behave as designed:** `consumer:'agent'`+`schema_version:'1.1'` accepted; `consumer` omitted accepted; `schema_version:'1.0'` still accepted; `consumer:'robot'` rejected on enum; `schema_version:'1.2'` rejected on enum; bare-id `related` still accepted (confirms Path A breaks nothing).
- **Whole toolchain green even before Step 5:** `validate-frontmatter` ✓ 8 files; `pytest` 57 passed; `ruff` clean; `pyright` 0 errors.

**Finding that simplifies Step 5:** the existing suite did **not** pin the old `schema_version` enum nor assert that `consumer` is rejected as an unknown property — so nothing went red. **Step 5 is therefore purely additive** (new accept/reject cases for `consumer` and `schema_version:'1.1'`), not a test-migration. No fix-the-reds work is owed.
