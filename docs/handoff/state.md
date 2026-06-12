# State

**Last updated:** 2026-06-12

## State at a glance

- **`3.0.0` RELEASED on `main` 2026-06-12.** Tags `v3.0.0` (signed annotated) + `v3` (moving) published; `v2` frozen at `3ece2c9`; GitHub release live. `deployed.md` updated. `staging` branch deleted; `testing` fast-forwarded to `main` (`2320d37`).
- **Standards-corpus review 2026-06-12** (5 parallel reviewers over `standards/`): 7 🔴 + 12 🟡 fixed — frontmatter adopt-guide id rules, python-tooling §8 GFM table (bug 002), `__future__` drop, python-coding draft acknowledged, pytest floor →9.0.
- Version `3.0.0` (MAJOR): `validate-id` now in consumer CI + duplicate-key rejection. `2.0.0` shipped 2026-06-07; `main` holds releases; handoff-system-v3.

## Active incidents

- _None._ v3.0.0 published and clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; `staging` is deleted (no longer used for this release).
