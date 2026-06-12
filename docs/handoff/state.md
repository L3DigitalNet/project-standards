# State

**Last updated:** 2026-06-12

## State at a glance

- **Full `3.0.0` release state STAGED, REVIEWED + GREEN on `staging`; NOT tagged, NOT on `main`.** HEAD `c0e5dc3`. Atomic v2→v3 contract bump in one signed commit (`afb3618`): `pyproject`+`uv.lock`→3.0.0, ALL consumer pins→`@v3`, `major_ref()`→`v3`. Payload: adopt CLI + hardened `validate-id` + frontmatter suite. 441 tests, 92% cov, basedpyright 0/0/0; ruff/prettier/markdownlint/pip-audit + dogfood clean. Readiness rounds 1–6 converged.
- **Standards-corpus review 2026-06-12** (5 parallel reviewers over `standards/`): 7 🔴 + 12 🟡 fixed in 6 commits (`5fac8ae`…`c0e5dc3`) — frontmatter adopt-guide id rules now match `validate-id`; python-tooling §8 GFM table (bug 002) + script counts + missing TOC; `__future__` import dropped from check.py (coding-standard conflict); **python-coding draft (0.4) now acknowledged in root README/CHANGELOG/AGENTS/CLAUDE/versioning/architecture** as reference-only + unregistered; pytest floor →9.0. Gate re-verified green.
- **DEFERRED to the all-at-once `main` push (explicit user go ONLY) — the next-session action:** signed tag `v3.0.0`; moving `v3`; freeze `v2` (live moving 2.x tag until then); fast-forward `main`; GitHub release; flip `deployed.md` staged→published. Checklist in `TODO.md`.
- Version `3.0.0` (MAJOR): `validate-id` now in consumer CI + duplicate-key rejection. `2.0.0` shipped 2026-06-07; `main` holds releases; handoff-system-v3.

## Active incidents

- _None._ Full gate green at 3.0.0 on `staging`.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. **Next session = execute the release:** fast-forward `main`→`staging`, then tag/freeze/release per `TODO.md`. Contract bump already on `staging` (`afb3618`).
