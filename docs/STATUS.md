# Project Status

## Current snapshot

- `main` remains the released v4.3.0 line; `testing` carries the unreleased v5.0.0 standards-platform work.
- Seven standards are released or staged: the six v4 standards plus Agent Handoff v1 for the v5 release.
- Agent Handoff v1 package and dogfood adoption are integrated on `testing` at `93296d6`; the 1,373-test acceptance gate and four installed-wheel probes pass.
- The package is repository-local: shared hook, skill, provenance lock, state, status, and tasks all remain inside the adopting repo.
- ADRs 0017-0022 define standard-package adoption, lifecycle, provenance, versioning, skills, and hook installation.
- SPEC-MT01 Steps 00-06 are complete; Step 07 remains the MCP-readiness gate before SPEC-MS01 server work.
- Pre-Step-07 remediation (`70b20ee`…`342a802`) reconciles SPEC-MT01 traceability, v5 migration guidance, and numbered bug-record targeting.
- The dedicated graph/catalog workflow covers pull requests plus pushes to `testing` and `main`; its first hosted run awaits the next branch push.
- All 13 `docs/future-standards/` drafts pass broad Prettier and markdownlint checks; they remain provisional and unregistered.
- The release freeze remains active until v5.0.0; versioned changes accumulate under CHANGELOG `[Unreleased]`.
- Durable implementation history is in `docs/handoff/sessions/2026-07.md`; active work is in `docs/TODO.md`.
- Nineteen known consumers validate on v1 branches; six concrete-evidence default branches, a published v5 wheel check, the final dependency search, and owner approval remain.
- `progressive-apparel` is the first migrated consumer (`2b062b6`); its Codex-only profile validates cleanly on `main`.
- `doc-proc-scripts` is migrated (`e1db276`); its full 532-test, 100%-coverage gate and Codex profile pass on `main`.
- `cc-usage-monitor` is migrated (`81d464d`); its full 150-test gate and dual Claude/Codex profile pass on `main`.
- `control-center` is migrated (`1be92ec`); its full 283-test gate and dual profile pass on `main` after two vulnerable locks were refreshed.
- `website-aboutme` validates on `testing` (`ab6bc3d`) with a clean Astro build; branch policy still requires integration to `main`.
- `Markdown-Keeper` is migrated (`d373df1`); 174 unit tests and the dual profile pass on `main`.
- `HomeBase` is migrated (`ec3df46`); 466 tests and the dual profile pass on `main`.
- `Russ-Estate-Paperwork` is migrated (`ab71b83`); the dual profile passes and current task metadata no longer carries financial identifiers.
- `star-trek-retro-remake` is migrated (`9d4e19e`); 11,212 tests, strict mypy, Ruff, and five import contracts pass on `main`.
- `agent-pseudocode` is migrated (`21ade51`); 48 tests, Ruff, BasedPyright, three pseudocode checks, and the dual profile pass on `main`.
- `Claude-Code-Plugins` is migrated (`0fdbd98`); marketplace validation, npm audit, targeted Markdown, and the dual profile pass on `main`.
- `dotfiles` is migrated (`baf8705`); its complete 170-test `make check` gate and the dual profile pass on `main`.
- `finances` is migrated (`f3e1d01`); Ruff, 361 PostgreSQL-backed tests, an empty legacy report, and the dual profile pass on `main`.
- `homelab` is migrated (`ceba125`); changed-doc frontmatter and Markdown, npm audit, llm-wiki citations, and the dual profile pass on `main`.
- `website-l3digital.net` validates on `testing` (`87dabc2`) with a clean Astro build; branch policy still requires integration to `main`.
- `docmend` validates on `dev` (`1657e2e`) with 619 tests, 97% coverage, and its full local gate; branch policy still requires integration to `main`.
- `hw-radar` validates on `dev` (`cbe77be`) with 357 tests, 93% coverage, and its full local gate; branch policy still requires integration to `main`.
- The `projects` workspace meta-repo is migrated (`3da7641`); its dual profile, 298 tests, and full local gate pass on `main`.
