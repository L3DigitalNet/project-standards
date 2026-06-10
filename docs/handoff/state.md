# State

**Last updated:** 2026-06-09

## State at a glance

- **Full `3.0.0` release state STAGED, REVIEWED + GREEN on `staging`; NOT tagged, NOT on `main`.** HEAD `415ccee`. The atomic v2→v3 contract bump is one signed commit (`afb3618`): `pyproject`+`uv.lock`→3.0.0 and ALL consumer pins→`@v3`; `major_ref()`→`v3`. Payload: adopt CLI + hardened `validate-id` + frontmatter suite (`format-frontmatter`, `validate-references` opt-in, `project-standards fix`, `.pre-commit-hooks.yaml`, `validate` runs all 3). 441 tests, 92% cov, basedpyright 0/0/0; ruff/prettier/markdownlint/pip-audit + dogfood clean.
- **Readiness round 6 CONVERGED — zero blockers** (4 parallel reviewers: pins / adopt-delivery / narrative / version-integrity; both MAJOR breaking claims code-verified). Round fixes: dogfood test now guards the full "pin BOTH" invariant (`399cb79`); `adopt` delivers the caller as `validate-standards.yml` to match the docs (`415ccee`).
- **DEFERRED to the all-at-once `main` push (explicit user go ONLY) — the next-session action:** signed tag `v3.0.0`; moving `v3`; freeze `v2` (live moving 2.x tag until then); fast-forward `main`; GitHub release; flip `deployed.md` staged→published. Checklist in `TODO.md`.
- Version `3.0.0` (MAJOR): `validate-id` now in consumer CI + duplicate-key rejection. `2.0.0` shipped 2026-06-07; `main` holds releases; handoff-system-v3.

## Active incidents

- _None._ Full gate green at 3.0.0 on `staging`.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. **Next session = execute the release:** fast-forward `main`→`staging`, then tag/freeze/release per `TODO.md`. Contract bump already on `staging` (`afb3618`).
