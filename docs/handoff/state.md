# State

**Last updated:** 2026-06-06

## State at a glance

- `1.3.0` is feature-complete on `testing` (DEC-1…9) but **unreleased** — the release ritual was deliberately out of scope. `main` holds releases; the moving `v1` tag tracks the newest. Exact delta: `git log main..testing`.
- Gate green post-restructure (2026-06-06): pytest 105, coverage 96% branch, ruff + basedpyright + pip-audit clean, prettier `--check .` clean, validate-frontmatter ✓ 12. The six-step gate is in `conventions.md` §3.
- Repo migrated to handoff-system-v3 on 2026-06-05 (this layout).
- Python Tooling SSOT standard adopted 2026-06-06 (`standards/python-tooling/README.md`); validator moved to `src/project_standards/` with schema bundled inside the package.
- Standards restructured into per-standard bundles 2026-06-06: `standards/<name>/{README,adopt,templates,examples}` + `meta/versioning.md`, with a `standards/README.md` index; consumer contract unchanged. Spec+plan in `docs/superpowers/`.
- Consistency review + self-conformance audit 2026-06-06: repo now **fully conforms to all four standards** (frontmatter/ADR/python-tooling/versioning). Fixed AGENTS.md staleness, ADR canonical key order, quoted frontmatter list items, repo-root-relative `related` links.

## Active incidents

- None.

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. Next obvious work: run the release ritual (cut tag, move `v1`, fast-forward `main`). ⚠️ `requires-python` `>=3.11`→`>=3.13` is breaking for CLI consumers, so the release is **LOCKED as `2.0.0`** (not `1.3.0`) per `meta/versioning.md` (see `CHANGELOG.md` + `deployed.md`). See `deployed.md`.
