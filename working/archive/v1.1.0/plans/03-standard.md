# Step 3 — Promote the standard prose

> **Depends on:** [`02-schema.md`](02-schema.md) (schema is the contract this prose describes). Resolves **Q2**. Target file: `standards/markdown-frontmatter.md`.

## Q2 decision (user, 2026-06-03)

- **Q2a — Promote mode:** **replace wholesale.** The converged proposal is a strict superset of the old standard; the old body is fully subsumed.
- **Q2b — Versioning/Validation sections:** **trim to pointers.** Keep only standard-specific content; defer release mechanics to `standards/versioning.md` and consumption/CI to `README.md`.

## What was done

Replaced the body of `standards/markdown-frontmatter.md` with the promoted proposal body, preserving and updating the existing frontmatter block:

- **Frontmatter block kept + updated:** `schema_version` `'1.0'` → `'1.1'`; `updated` → `'2026-06-03'`; added `consumer: 'mix'` (dogfoods the new field; the standard is read by humans and agents); added `'standards/versioning.md'` to `related` (now cross-linked, path form). `related` already used path form (`schemas/markdown-frontmatter.schema.json`).
- **Title de-PROPOSED:** `# Markdown Frontmatter Standard (PROPOSED V1.1)` → `# Markdown Frontmatter Standard`.
- **Links section softened to convention (Path A, the Step 1 required edit):** removed the "enforced by `tools/validate_frontmatter.py`" claim; downgraded **MUST** → **SHOULD/recommended/discouraged**; added an explicit paragraph stating the validator does not check link form and that schema-enforced patterns are planned for `2.0.0`. Modal verb matched to enforcement reality so the un-migrated example docs (Step 6 cancelled) don't textually violate the standard.
- **Versioning and compatibility trimmed:** kept the `schema_version`-vs-release-tag distinction (lives nowhere else); deferred classification mechanics + previously-passing rule + tagging + consumption to `versioning.md`.
- **Validation trimmed:** kept what has no other home (the run command, **exit codes**); deferred the full flag list to `validate-frontmatter --help` and config/CI/tag-pinning to `README.md#consuming-the-standards`.

## Content-loss guard (replace-wholesale safety)

Confirmed every normative item in the old `## Formatting Rules` bullet list has a home in the promoted text: dates/quoting/null → **Scalar value rules**; empty lists → **List rules**; tags → **Tags**; IDs / `doc_type` / relationship-fields-only-when-needed → **Formatting rules**; `publish` namespace → **Extensions**. No old-only normative content dropped. (The one intentional refinement: old "use `null` for unknown scalars" → new "prefer omitting optional fields or an empty list," a converged-review decision, not a loss.)

## Verification

- `validate-frontmatter` ✓ 8 files (promoted standard passes at `1.1` + `consumer`).
- Spot-checks: no `PROPOSED` in file; no "enforced by `tools/validate`" link claim; `schema_version: '1.1'` and `consumer` present in own frontmatter and in every example block.

## Note for later steps

- **Step 4 (templates/examples):** the example docs keep bare-ID `related` — consistent with the SHOULD-not-MUST wording chosen here. Only add `consumer` + bump `schema_version` to `'1.1'`; no link rewrites.
- **`README.md` anchor dependency:** the Validation pointer targets `README.md#consuming-the-standards`. If that heading is ever renamed, fix this link.
