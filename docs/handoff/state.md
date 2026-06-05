# State

**Last updated:** 2026-06-05

## State at a glance

- `1.3.0` is feature-complete on `testing` (DEC-1…9) but **unreleased** — the release ritual was deliberately out of scope. `main` holds releases; the moving `v1` tag tracks the newest. Exact delta: `git log main..testing`.
- Gate green (verified 2026-06-05): pytest **105**, ruff clean, pyright 0, validate-frontmatter ✓ 9, markdownlint 0, prettier `--check .` clean.
- Repo migrated to handoff-system-v3 on 2026-06-05 (this layout).

## Active incidents

- None.

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. Next obvious work: run the `1.3.0` release ritual (cut tag, move `v1`, fast-forward `main`). See `deployed.md`.
