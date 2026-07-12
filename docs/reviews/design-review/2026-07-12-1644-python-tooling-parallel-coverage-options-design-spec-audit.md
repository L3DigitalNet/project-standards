# Specification Audit (Follow-up, Round 4 — Convergence) — Python Tooling Parallel Coverage Options Design

Audited document: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md` Prior audits:

- `docs/reviews/design-review/2026-07-12-1557-...-spec-audit.md` (round 1)
- `docs/reviews/design-review/2026-07-12-1617-...-spec-audit.md` (round 2)
- `docs/reviews/design-review/2026-07-12-1634-...-spec-audit.md` (round 3) Reconciliation commit referenced by the user: `c904910`

## Executive summary

Convergence reached. The three round-3 findings (SA-NEW-004, -005, -006) are resolved, and each resolution was verified against actual repository evidence rather than accepted on the text alone:

- **SA-NEW-004** (migration must classify the workflow as `preserve`): the design now recognizes `/python_tooling/workflow_ownership` as a migration input, resolves it before signature classification, and emits a claim with `ownership = "consumer-owned"`, `disposition = "preserve"`. This is not only architecturally consistent with `run_migrate` (which builds config before the signature loop) but is **exactly the pairing the control-plane engine enforces**: `control_plane/migration.py:184` allows `"consumer-owned": frozenset({PRESERVE})`, and the claim schema (`migration-report.schema.json:21`) already lists `consumer-owned` in its ownership enum.
- **SA-NEW-005** (name collision): the option is renamed `workflow_ownership` with a clear note that it is a distinct ownership axis from the cross-package `workflow_mode` delivery axis. Usage is consistent throughout the spec; the residual `workflow_mode` mentions correctly reference the other packages.
- **SA-NEW-006** (inert `ci.*`): documented as managed-workflow-only, kept schema-valid in both modes for config round-trip stability, with a dedicated acceptance criterion.

No new findings, no regressions. All ten findings from rounds 1-3 plus the three round-3 findings are resolved. Acceptance criteria now map one-to-one onto every obligation, including the false-positive-closing checks (end-to-end subprocess measurement; preserve claim with unchanged workflow bytes). No new internet research was required.

## Verdict

**No significant findings remain.** The audit/fix loop can stop; the specification is ready for the authoring agent to use as the basis for planning/implementation.

## Audit loop status

- Audit type: Follow-up audit (convergence)
- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Prior audit issue count: 13 total across rounds 1-3 (SA-001–SA-007, SA-NEW-001–006)
- Resolved issue count: 3 this round (SA-NEW-004, SA-NEW-005, SA-NEW-006); 13 cumulative
- Still open issue count: 0
- Partially resolved issue count: 0
- New issue count: 0
- Regression count: 0
- Significant findings remaining: No

## Adversarial review performed

- **Prior-fix retest against the engine, not just the text:** verified the proposed migration claim (`consumer-owned` / `preserve`) is a legal, engine-enforced pairing; verified `consumer-owned` is a valid ownership enum value; verified the `when_any` predicate keyword is real; verified `workflow_ownership` naming is applied consistently.
- **Regression pass:** confirmed the rename and the new migration/verify wiring did not disturb the coverage-option resolutions (SA-001–SA-007, SA-NEW-001–003) or the `_DEFAULT_CONFIG` static-source guard.
- **New-issue hunt:** probed the migration-input ergonomics for general consumers, the interaction of `run_verify`'s conditional skip with the default-config static guard, and whether any nested-option predicate was implied (none — the only predicate is on the flat top-level `workflow_ownership`).
- Not re-executed: no coverage run or migration was performed (read-only); operability and preserve-vs-adopt behavior are asserted from provider/engine code plus the design's required tests.

## Prior findings status

### SA-NEW-004: Migration-time provisioning of workflow ownership; `preserve` wiring

- Previous severity: Medium
- Current status: Resolved
- Evidence:
  - Spec line 56 / 102 / 113 — `/python_tooling/workflow_ownership` is a recognized migration input, "resolve[d] … before signature classification," emitting a claim with `ownership = "consumer-owned"` and `disposition = "preserve"` "in the same provider call."
  - Repository confirmation: `run_migrate` builds `config` from the legacy namespace before the signature loop (`python_tooling.py:609-666`), so the classifier can consult the resolved value; the claim schema permits `consumer-owned` (`schemas/migration-report.schema.json:21`) with `preserve` (`:23`); and the engine's `_safe_disposition` **requires** exactly this pairing — `"consumer-owned": frozenset({LegacyDisposition.PRESERVE})` (`control_plane/migration.py:184-188`). The managed/adopt path that would replace the file (`migration.py:1106`) is not taken for a consumer-owned/preserve claim.
  - Testable: Verification step 4 (spec line 154) and acceptance criteria (spec lines 172-173) require the recognition and the preserve claim with unchanged workflow bytes.
- Remaining action for the authoring agent: None.

### SA-NEW-005: `workflow_mode` name/vocabulary collision

- Previous severity: Medium
- Current status: Resolved
- Evidence: Spec line 26 renames the option `workflow_ownership` and states it "avoids colliding with Markdown Tooling and Project Specification's `workflow_mode = "caller" | "self-hosted"` delivery axis" — accurate against `standards/project-spec/versions/1.1/config.schema.json:7` and the matching markdown-tooling option. Spec-wide usage is consistent (`workflow_ownership` for this package's option; `workflow_mode` only where the other packages are named).
- Remaining action for the authoring agent: None.

### SA-NEW-006: `ci.*` options silently inert under consumer-owned

- Previous severity: Low
- Current status: Resolved
- Evidence: Spec line 67 keeps `ci.*` schema-valid in both modes "for config round-trip stability" while documenting managed-only effect; spec line 107 states they are "intentionally inert when the workflow is consumer-owned"; acceptance criterion (spec line 175) validates the documentation and the no-effect behavior. Matches provider reality — `ci.enabled`/`ci.performance` feed only `_workflow` (`python_tooling.py:197,224-230`).
- Remaining action for the authoring agent: None.

## New blocking issues

None found.

## New non-blocking issues

None found.

## Regressions

None found. The coverage-option core (SA-001–SA-007, SA-NEW-001–003) is intact in the revised text; the rename and the migration/verify additions did not alter the coverage schema, provider rendering, dependency floor, parallel-aware gate, or the `_DEFAULT_CONFIG` guard (which now carries the default `workflow_ownership = "managed"`, keeping default-consumer byte-identity active).

## Remaining ambiguities and decisions needed

None blocking. One non-actionable observation for completeness: because `workflow_ownership` is a v5-only concept, it is not present in a genuine v4 legacy config, so the migration-time recognition path (`/python_tooling/workflow_ownership`) matters chiefly for this repository's disposable fixture and for any consumer whose migration input carries it; other consumers default to `managed` at migration and can select `consumer-owned` in their v5 `.standards/config.toml` at reconcile time. This matches the design's scope (preserve this repo's optimized workflow through the atomic migration) and needs no change.

## Internet research performed

None this round. The external coverage.py facts (7.14.0 auto-combine; 7.10.0 `[run] patch`) were established and cited in rounds 1-2 and remain unchanged; all round-4 verification rests on repository evidence.

## Read-only validation performed

- Read the revised spec in full — confirmed the SA-NEW-004/-005/-006 resolutions, the round-3 disposition block (spec lines 54-59), and one-to-one acceptance-criteria coverage (spec lines 165-179).
- Read `standards/python-tooling/versions/1.1/schemas/migration-report.schema.json` — confirmed `ownership` enum includes `consumer-owned` and `disposition` enum includes `preserve`.
- Grepped `src/project_standards/control_plane/migration.py` — confirmed `"consumer-owned": frozenset({PRESERVE})` enforcement (`:184-188`) and the managed/adopt replacement path (`:1106`) that a preserve claim avoids.
- Grepped `standards/agent-handoff/versions/1.1/payload.toml` — confirmed the predicate keyword is literally `when_any` (multiple uses), matching the design's wording.
- Grepped the spec for `workflow_mode`/`workflow_ownership` — confirmed consistent naming and that the only `workflow_mode` references are the cross-package distinctions.
- Re-read `providers/python_tooling.py` (`run_migrate`, `run_verify`, `_SIGNATURES`, `_DEFAULT_CONFIG`) — confirmed the migration builds config before signature classification, `run_verify` receives `config` (so it can conditionally skip `check.yml`), and the default config gate remains intact.

## Recommended planning/implementation validation

To be run by the authoring agent after implementation (several write artifacts — run only after implementation):

- `uv run pytest tests/package_contract/test_python_tooling_reconstruction.py` — options, rendering, cross-field rejection (incl. omitted `parallel`), workflow-ownership materialization, migration recognition + preserve claim.
- `uv run pytest tests/package_compatibility/test_release_candidate.py` — atomic-migration preservation incl. the consumer-owned workflow and parallel-aware subprocess evidence.
- `uv run pytest tests/test_adopt_dogfood.py` — twin contract before/at migration.
- `uv run project-standards validate --config .project-standards.yml` — dogfood gate.
- Package/graph/projection/source-wheel gates and `uv run python scripts/run_repository_tests.py` — full gate.

## Final recommendation

No significant findings remain; the audit/fix loop can stop. The authoring agent may use the specification as the basis for planning/implementation as written. Proceed to the convergence milestone / implementation planning per the project's TODO.

## Review ledger for next loop

- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Audit round: 4 (convergence)
- Open issue IDs: none
- Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007, SA-NEW-001, SA-NEW-002, SA-NEW-003, SA-NEW-004, SA-NEW-005, SA-NEW-006
- Superseded issue IDs: none
- Significant findings remaining: No
- Next audit should focus on: nothing — the loop is complete. If implementation diverges from the spec, a plan-flow (`CR-*`) review of the implementation plan or code would be the next distinct step.
