# Project Status

This is the human-facing completion summary for the project. Agents maintain it so the project builder can re-orient quickly.

## Completed

- `3.0.0` released on `main` (2026-06-12; tags `v3.0.0`/`v3`; `v2` frozen at `3ece2c9`; GitHub release live).
- Handoff system resynced to engine v3.4 (2026-07-01): SessionStart hooks, `.codex/config.toml`, this file, and `TODO.md`'s section headings brought current; `docs/handoff/specs-plans.md` backfilled to index `docs/superpowers/specs/README.md`.
- Python Tooling standard review + fixes (2026-07-01): the §15 CI-workflow scaffold was invalid YAML (tab-indented) — repaired and byte-locked to the bundle artifact with drift tests; ruff floor raised to `>=0.14` (0.9–0.13 can't run `py314` non-preview); dead `pytest-cov` dropped from all dev groups; adopt CLI now delivers the full `.vscode/` trio (settings/tasks were silently missing); audit-note trail backfilled. 587 tests, 100% coverage.
- **project-spec tooling Spec #1 (read-only) + Spec #2 (`new`) + Spec #3 (`upgrade`) implemented (2026-07-04–05):** full `validate|lint|extract|next|new|upgrade` command surface, reusable `validate-specs.yml`, three fail-closed gates on `upgrade`, byte-exact tier-promotion round-trip oracle.
- **`project-spec` (5th standard) REGISTERED (2026-07-05):** three 🟡 correctness bugs + two 🟢 cleanups from `/code-review high spec` fixed (TDD); adoption docs (`adopt.md`) written in full, including CI wiring for the previously-undocumented `validate-specs.yml` reusable workflow; standard registered — `spec:` config block live, real frontmatter added to README/adopt.md/resources, a dogfood example (`examples/spec.example.md`) added and locked in by its own test, top-level `README.md`/`standards/README.md`/`meta/versioning.md` updated. Five standards now live (was four + one draft).
- **Residual `format-frontmatter`/`cli.py` gaps fixed (2026-07-05):** typo'd `--config` now exits 2 instead of silently formatting under defaults; non-UTF-8 input now reports a clean per-file error instead of a traceback; `validate --help`'s `--glob` text corrected to match real replace-not-additive semantics.
- **CHANGELOG caught up + version classified (2026-07-05):** `project-spec` registration entry (MINOR) and the accumulated validator-strictness-bump entry (six independently-MAJOR items + a MAJOR tool-floor raise + one confirmed-PATCH item) both added to `[Unreleased]`. **Conclusion: the next release off `testing` is MAJOR (v4.0.0)** — a release is classified by its worst change.

## Current State

- **Five standards now registered:** Markdown Frontmatter, ADR, Markdown Tooling, Python Tooling SSOT (all as before), plus **Project Specification** (newly registered 2026-07-05) — a live CLI (`project-standards spec ...`) rather than copy-adopt, with its own reusable CI workflow. **Python Coding** remains the sole in-development draft (unregistered, excluded from validation/adopt).
- `testing` is ahead of `main` carrying the `project-spec` registration (MINOR) plus validator/config strictness bumps and a Python Tooling floor raise (each independently MAJOR) — **next release will be v4.0.0**, not yet cut.

## Recent Changes

- [2026-06-12] 55/58 validator findings implemented; coverage 93% → 100%; `3.0.0` released on `main`.
- [2026-07-01] Handoff-system-v3 resynced; Python Tooling + Markdown standards reviewed and fixed; full cross-standard consistency review (all four standards adopt collision-free).
- [2026-07-04–05] project-spec tooling Spec #1/#2/#3 implemented — full `validate|lint|extract|next|new|upgrade` surface.
- [2026-07-05] project-spec bug/cleanup fixes, `format-frontmatter`/`cli.py` residual fixes, adoption docs written, standard **registered**, CHANGELOG caught up with a resolved MAJOR/MINOR classification. Full gate: 790 tests, 98% coverage.

## Notes For The Builder

- **Next release is MAJOR (v4.0.0)** whenever cut — see `[Unreleased]` in `CHANGELOG.md` for the full itemization and the release-requirements checklist in `meta/versioning.md` for the cutting procedure (migration notes belong in that commit).
- Two informational, explicitly non-blocking items remain in `TODO.md` (`spec new` symlink/TOCTOU edge cases; OpenAPI version pin) — revisit only if their trigger conditions arise.
