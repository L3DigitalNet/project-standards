# Step 1 — Release scoping & version classification (DECISION RECORD)

> **Status:** RESOLVED 2026-06-03. This is the decision gate; it fixes the target version and unblocks Steps 2–10. Parent plan: [`00-overview.md`](00-overview.md). Spec under release: [`../schema/schema.frontmatter.md`](../schema/schema.frontmatter.md).

## Decision

**Path A — ship as `1.1.0` (minor).** Resolves open question **Q1**.

- Add the optional `consumer` field (enum `user | agent | mix | unknown`).
- Add `'1.1'` to the `schema_version` enum (keep `'1.0'` accepted).
- Treat the repo-root-relative link rule as **documented convention only**. Do **not** add `items.pattern` to `related` / `supersedes` / `superseded_by` / `depends_on` in the schema this release.
- No in-repo doc migration. No consumer migration notes.

**Target version: `1.1.0`** (current release is `1.0.2` on moving tag `v1`; `pyproject.toml` = `1.0.2`). Flows to `@v1` consumers automatically.

## Why minor and not major (classification rationale)

The governing test is the **previously-passing rule** in [`../../standards/versioning.md`](../../standards/versioning.md): _if any change can turn a previously-passing consumer document into a failure, the release is MAJOR — without exception._

| Candidate change | Effect on a previously-passing doc | Class |
| --- | --- | --- |
| Add optional `consumer` field | Cannot fail anything — optional, absent = valid | MINOR |
| Add `'1.1'` to `schema_version` enum | Widens an enum; `'1.0'` still valid | MINOR |
| Add `items.pattern` to link fields | **Fails 7 currently-passing managed docs** (see below) | **MAJOR** |

Because the link pattern is the _only_ candidate that crosses into MAJOR, and we explicitly drop it from this release, the worst-case impact of any remaining change is additive. The release is therefore **`1.1.0`**.

### The blast radius we are avoiding (evidence for the major classification)

A tightened link pattern would newly-fail every managed doc that currently uses a bare-ID (non-path) value in a link field. Verified inventory across the validator's `include` globs (`CHANGELOG.md`, `standards/**`, `examples/**`):

| Doc | Field | Non-path value(s) |
| --- | --- | --- |
| `standards/adr.md` | `related` | `markdown-frontmatter-standard` |
| `standards/versioning.md` | `related` | `markdown-frontmatter-standard`, `adr-standard` |
| `CHANGELOG.md` | `related` | `markdown-frontmatter-standard` |
| `examples/note.example.md` | `related` | `immutable-infrastructure` |
| `examples/concept.example.md` | `related` | `adr-0001-use-postgresql-for-persistent-storage` |
| `examples/adr.example.md` | `related` | `immutable-infrastructure` |
| `examples/runbook.example.md` | `related` | `adr-0001-use-postgresql-for-persistent-storage` |

That is **7 managed docs** (the original handoff cited only one). The four `examples/**` docs additionally point at _illustrative_ IDs that are not real files in this repo, so a pattern that only checks path **shape** (the most a JSON Schema regex can do — the frontmatter-only validator cannot check file existence) would still leave those examples reading dishonestly until rewritten to real paths. Both facts make Path B materially more expensive than the handoff implied and reinforce deferring enforcement.

## Scope locked for this release

**In scope (additive only):**

1. `consumer` property + enum in the schema.
2. `'1.1'` added to the `schema_version` enum.
3. `schema_version` value set to `'1.1'` in this repo's managed docs and templates.
4. Narrowed `visibility` description (non-normative wording; PATCH-class on its own).
5. Standard prose promoted from the proposal, with the link section reworded (see required edit below).

**Out of scope (deferred to a future `2.0.0`):**

- Any `items.pattern` enforcement on link fields.
- Section-level (`#`) link support.
- Migrating in-repo docs to path form.

## Required edit this decision forces on the spec

The converged proposal currently over-claims enforcement. Before promotion (Step 3) it must be softened to match Path A:

- `../schema/schema.frontmatter.md:336` —

  > "In frontmatter this form is enforced by `tools/validate_frontmatter.py`; in document bodies it is a convention the validator does not check."

  Under Path A the link form is **convention everywhere** (frontmatter included); the validator does not enforce it. Reword to say so, and note that path-shape enforcement is planned for a future major release. Re-scan the rest of the **Links and related documents** section for any other "enforced"/"MUST … the validator rejects" phrasing about link form and downgrade it to convention.

- Drop the `(PROPOSED V1.1)` qualifier from the title at promotion time (Step 3).

## Impact on downstream steps

- **Step 2 (schema):** add `consumer` + enum, add `'1.1'` to `schema_version` enum, narrow `visibility` description. **Do not** add link patterns.
- **Step 4 (templates/examples):** add `consumer` + `schema_version: '1.1'`. No link rewrites required (Path A).
- **Step 5 (tests):** test `consumer` enum accept/reject and `schema_version` `'1.1'` accepted while `'1.0'` still valid. **No** link-pattern tests this release.
- **Step 6 (migration):** **does not run** (Path A). Remove from the critical path.
- **Step 7 (changelog):** `Added: consumer`. `Changed:` `visibility` description wording (and the link rule now stated as convention). **No** migration subsection.
- **Steps 3, 8, 9, 10:** unchanged in shape; classification is `1.1.0`.

## Remaining open questions (unchanged by this decision)

- **Q2 (Step 3):** Does the proposal replace `standards/markdown-frontmatter.md` or merge in? Which new sections defer to `versioning.md` / `README.md`?
- **Q3 (Step 5):** Extend existing `tests/` fixtures, or add a new corpus?
- **Q4 (Step 9):** Confirm GPG key + `release-pipeline` guard before the `v1` tag move.
