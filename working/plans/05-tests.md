# Step 5 — Update validator tests (additive)

> **Depends on:** [`02-schema.md`](02-schema.md). Resolves **Q3**. Target: `tests/test_validate_frontmatter.py` (extend the existing file).

## Q3 decision (user, 2026-06-03)

**Extend the existing file.** Add cases into `tests/test_validate_frontmatter.py` using its base-fixture (`MINIMAL`/`STANDARD` dicts) + `_check` helper pattern. No new corpus/fixtures directory — that scaffolding isn't warranted for an additive release.

## What was done

Added a **"Schema V1.1 — additive surface"** section after the numbered schema cases (1-14), with 6 test functions (one parametrized ×4) = **9 new cases**:

- `test_schema_version_1_1_accepted` — `1.1` + `consumer` accepted.
- `test_schema_version_1_0_still_accepted` — backward-compat: `1.0` still valid.
- `test_schema_version_unknown_value_fails` — `1.2` rejected on enum.
- `test_consumer_enum_values_accepted[user|agent|mix|unknown]` — all four enum values accepted (parametrized).
- `test_consumer_invalid_value_fails` — `robot` rejected on enum.
- `test_consumer_is_optional` — `consumer` omitted from an otherwise-standard `1.1` doc still passes.

Updated the module docstring's "Organisation" block to describe the new section.

**No link-pattern tests** — Path A ships the link rule as convention only, not schema-enforced (deferred to `2.0.0`).

## Two deliberate design choices

- **`MINIMAL`/`STANDARD` stay pinned at `schema_version: "1.0"`.** Not bumped to `1.1`. This turns the entire pre-existing suite into free backward-compatibility coverage — every test re-proves a `1.0` document still validates, which is precisely the contract a minor release must protect.
- **Characterization, not red-green.** Step 2 already shipped the schema, so these cases pass on arrival. They pin the new surface against future regression rather than driving implementation. (Per `01-scoping.md`, the suite never went red — there were no Step-2 reds to fix; Step 5 is pure addition.)

## Verification (full toolchain — this is effectively a Step 8 dry run)

- `pytest` — all pass (66 cases incl. the 9 new ones); `-k "consumer or schema_version"` selects 9, all green.
- `ruff check .` — clean.
- `pyright` — 0 errors, 0 warnings.
- `validate-frontmatter --config .project-standards.yml` — ✓ 8 files (from Steps 3-4).
