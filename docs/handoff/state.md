# State

**Last updated:** 2026-07-01

## State at a glance

- **Handoff system resynced to engine v3.4 (2026-07-01):** SessionStart hooks (`.claude/`, `.codex/`) and `.codex/config.toml` byte-matched to canonical; root `STATUS.md` created (3.3 requirement); `TODO.md` section renamed to the required `## Agent Tracked Tasks`; `docs/handoff/specs-plans.md` backfilled to index `docs/superpowers/specs/README.md`. `validate-layout.sh` clean apart from local `python3`-shim false positives on the JSON/TOML checks (independently confirmed valid via `uv run python3`).
- **2026-06-12 validator review + coverage passes complete** — 55/58 findings implemented, coverage 93%→100% (584 tests). Full detail: `STATUS.md` and `docs/handoff/sessions/2026-06.md`.
- **Strictness bumps still need a CHANGELOG note before next release** — tracked in `TODO.md` (F29/F30/F37/F41/F46/F3/F4).
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` is ~58 commits ahead of `main` with the unreleased validator fixes.

## Active incidents

- _None._ Full gate green: 584 tests, 100% cov, basedpyright 0/0/0, prettier/markdownlint/dogfood clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; `staging` is deleted. Do not merge `testing` into `main` without a release decision.
