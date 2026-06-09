# State

**Last updated:** 2026-06-09

## State at a glance

- **Full `3.0.0` release state STAGED + GREEN on `staging`; NOT tagged, NOT on `main`.** `staging` (cut from `testing`) holds the atomic v2→v3 contract bump in one signed commit (`afb3618`): `pyproject`+`uv.lock`→3.0.0 and ALL consumer pins→`@v3` (workflow `standards-ref` default `v3`, starter, `.project-standards.yml`, README, `meta/versioning`, 4 adopt guides, markdown-tooling/README, build-backend). `major_ref()`→`v3`; caller-stub dogfood renders `@v3`. Payload: adopt CLI + hardened `validate-id` + frontmatter suite (`format-frontmatter`, `validate-references` opt-in, `project-standards fix`, `.pre-commit-hooks.yaml`, `validate` runs all 3). 441 tests, 92% cov, basedpyright 0/0/0; ruff/prettier/markdownlint/pip-audit + dogfood clean.
- **DEFERRED to the all-at-once `main` push (explicit user go ONLY):** signed tag `v3.0.0`; create moving `v3`; freeze `v2` (still the live moving 2.x tag until then); fast-forward `main`; GitHub release; flip `deployed.md` staged→published. Full checklist in `TODO.md`.
- Version `3.0.0` (MAJOR): `validate-id` now in consumer CI + duplicate-key rejection (two previously-passing-rule triggers). `docs/python-backend.md` keeps illustrative `@v2` (scratch/advisory, not consumer-facing, out of validation scope) — intentional. `2.0.0` shipped 2026-06-07; `main` holds releases; repo on handoff-system-v3.

## Active incidents

- _None._ Full gate green at 3.0.0 on `staging`.

## Session instructions

1. Live state auto-injected by the SessionStart hook; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. **Final push (user go):** fast-forward `main`→`staging`, then tag/freeze/release per `TODO.md`. The contract bump is already committed on `staging` (`afb3618`).
