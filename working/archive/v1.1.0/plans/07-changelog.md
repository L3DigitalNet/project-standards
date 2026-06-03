# Step 7 — Update the changelog

> **Depends on:** Steps 2–5. Target: `CHANGELOG.md` (a managed doc — must validate). Step 6 skipped (Path A), so this follows Step 5 directly.

## What was done

- **Renamed `## [Unreleased]` → `## [1.1.0] — unreleased`.** Per the user's instruction, the section is version-labelled but **un-dated**; Step 9 swaps `unreleased` → the release date in the same commit as the version bump (satisfies `standards/versioning.md` step 4).
- **Folded in the two pre-existing `[Unreleased]` entries** (Apache-2.0 `LICENSE`; versioning-standard force-push wording) — they ship *in* 1.1.0, so they belong in this section, not orphaned.
- **Added the new V1.1 entries:**
  - _Added_ — `consumer` frontmatter field (headline feature).
  - _Changed_ — `schema_version` enum widened to `1.1`; standard promoted to V1.1 (new sections + trimmed Versioning/Validation); `visibility` description narrowed; link form documented as convention (not enforced until `2.0.0`).
- **Bumped `CHANGELOG.md`'s own frontmatter** `schema_version` `'1.0'` → `'1.1'` (it is the managed doc being edited, and it announces the 1.1 bump). `updated` was already `2026-06-03`. Kept its bare-ID `related` value (Path A — no link migration).

## Verification

- `validate-frontmatter --config .project-standards.yml` — ✓ 8 files (CHANGELOG passes at `1.1`).

## ⚠️ Flagged for the release step (NOT done here — out of "changelog" scope)

Two other in-repo **managed docs still declare `schema_version: '1.0'`**: `standards/versioning.md` and `standards/adr.md`. They remain valid (the enum keeps `1.0`), but the released repo would then ship a 1.1 standard while two of its own governing docs still declare the old version — uneven dogfooding.

**Recommendation:** bump both to `schema_version: '1.1'` (and refresh `updated`) as part of the Step 9 release commit, so every shipped managed doc uniformly declares the version it conforms to. `consumer` is optional and need not be added to them. No link rewrites (Path A). Decision left to the user per the "changelog now, pause" scope.

## Remaining before release (Steps 8–10)

- **Step 8:** re-run the green gate on the release commit.
- **Step 9 (needs user):** integrate `testing → main`; bump `pyproject.toml` `1.0.2` → `1.1.0`; regenerate `uv.lock`; date the changelog section; GPG-sign `v1.1.0`; move `v1` by delete-and-re-push; push. Confirm Q4 (GPG key `9375AFEFA6F841B0`; server-side `release-pipeline` guard).
- **Step 10:** confirm the tag resolves and `uv tool install` picks up `1.1.0`; optional downstream `@v1` smoke test.
