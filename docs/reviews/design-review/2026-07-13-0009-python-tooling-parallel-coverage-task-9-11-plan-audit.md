# Python Tooling Parallel Coverage Tasks 9 and 11 Plan Audit

## Executive summary

The amended release-integration steps in [`docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md`](../../superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md) were freshly audited against the converged checker-table materialization design, the parallel-coverage design, SPEC-CP01, SPEC-BA02, and the live implementation.

**Final verdict: Ready.** No specification backtrack is required. A read-only Fable-max review found six execution-mechanics defects; all six were reconciled, and a read-only delta review verified every correction against the plan and repository code. One final Low advisory widened the release-time legacy-command sweep to include the active commands in `docs/usage.md` and `docs/handoff/conventions.md`.

## Audit scope

- Exact `pyright==1.1.411` carry-through across both migration intents, the provider-rendered development group, `.standards/config.toml`, and `uv.lock`.
- Guarded `/dependency-groups/dev` pre-alignment through the extracted installed provider.
- Exact source and semantic preconditions, refusal-before-write behavior, and bounded TOML mutation.
- Frozen post-checker predecessor reconstruction and exact-union overlay membership.
- Pre-atomic and reconstructed post-atomic release-patch equivalence.
- Preview/apply exit behavior, installed-provider provenance, locked offline sync, next-lock assertions, fixed-point convergence, and both complete-gate oracle selections.
- TDD ordering and operator-executable commands.

## Reconciled findings

| ID | Severity | Resolution |
| --- | --- | --- |
| PA9-11-001 | High | The disposable generated gate now removes release-only `PYTHONPATH`, so coverage measures the checkout's `src/`; only extracted-distribution CLI subprocesses retain that path. |
| PA9-11-002 | Medium | Both source shapes now reconstruct and commit the frozen predecessor before deriving the patch checkout, source snapshot, and replay baseline; changed paths and evidence digests must match. |
| PA9-11-003 | Medium | Task 11 now defines and exports the extraction paths, uses `uv run --no-sync`, records preview exit 1 as expected, and requires apply exit 0. |
| PA9-11-004 | Medium | The release-time unified-authority sweep includes `AGENTS.md`, `CLAUDE.md`, `docs/usage.md`, and `docs/handoff/conventions.md`; remaining matches must be classified as intentional history or migration examples. |
| PA9-11-005 | Low | Overlay/predecessor tests and guarded-alignment tests now have separate, accurate RED runs before their implementations. |
| PA9-11-006 | Low | Lock refresh, lock check, and offline sync run inside the disposable checkout; the dual checker oracle reruns separately at the repository root. |

## Verified contract facts

- The frozen `pyproject.toml` and `uv.lock` post-version digests recompute from checker integration commit `26fb984`.
- The reviewed eight-entry predecessor development group matches the post-checker root bytes.
- The installed-provider APIs, TOML adapter operations, next-lock fields, and dual complete-gate oracle named by the plan exist in the live implementation.
- Provider rendering necessarily changes the predecessor unit while retaining `pyright==1.1.411`, so the mutation-occurred assertion is meaningful.
- The amended normative order matches the checker design: restore predecessor, set release version, build and extract, inject intent only, resolve and render through the installed provider, guarded rewrite, preview/apply, then refresh and check the lock.

## Validation

The amended plan passed:

```bash
git diff --check
npx prettier --check docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
npx markdownlint-cli2 docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
python /home/chris/.agents/skills/technical-writer/scripts/docctl.py validate docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
```

No implementation tests were run during this plan-only audit. Tasks 9 and 11 remain unexecuted; the prior converged audit remains authoritative for unchanged Tasks 1–8 and 10.
