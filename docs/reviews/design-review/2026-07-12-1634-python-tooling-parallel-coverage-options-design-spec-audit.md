# Specification Audit (Follow-up, Round 3) — Python Tooling Parallel Coverage Options Design

Audited document: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md` Prior audits:

- `docs/reviews/design-review/2026-07-12-1557-...-spec-audit.md` (round 1)
- `docs/reviews/design-review/2026-07-12-1617-...-spec-audit.md` (round 2) Reconciliation commit referenced by the user: `4a253d7`

## Executive summary

The three round-2 findings (SA-NEW-001, -002, -003) are resolved: the dogfood twin is retired only at atomic migration with separate frozen-V1/current-V2 checks; the schema conditional now requires `parallel` to be **present and true** (omission rejected); and the subprocess-patch rationale now rests on coverage.py's public requirement rather than an internal-behavior claim.

To resolve SA-NEW-001's workflow-preservation need, the revision adds a general top-level `workflow_mode = "managed" | "consumer-owned"` option (default `managed`). The mechanism is sound in outline — it reuses the real payload predicate mechanism (confirmed in `agent-handoff` payload) and the round-2 acceptance criteria are extended to cover it. But auditing the new option surfaced **two Medium findings**, both about the new option rather than the coverage work:

1. **SA-NEW-004 (Medium):** the design says migration classifies the workflow as `preserve` in consumer-owned mode, but never specifies how `workflow_mode` reaches the migration classifier. `run_migrate` derives config only from the legacy namespace and recognizes `/python_tooling/coverage` only — not `/python_tooling/workflow_mode`. Without wiring, the `check-workflow` signature defaults to `adopt` and the migration replaces the optimized workflow — the exact outcome Alternative #5 rejects.
2. **SA-NEW-005 (Medium):** `workflow_mode` already exists as a top-level option in Project Specification and Markdown Tooling with values `caller | self-hosted` (a _delivery_ axis, always managed). Python Tooling reuses the same name for a different _ownership_ axis (`managed | consumer-owned`). The design cites this as precedent, but it actually diverges from it — a cross-package vocabulary collision.

Plus one Low (SA-NEW-006): `ci.*` options become silently inert under `consumer-owned`.

No blocking (Critical/High) findings remain. New internet research was not required this round (the coverage.py facts were settled in rounds 1-2); all round-3 findings rest on repository evidence.

## Verdict

**Needs minor specification correction before planning/implementation.**

## Audit loop status

- Audit type: Follow-up audit
- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Prior audit issue count: 10 total across rounds 1-2 (SA-001–SA-007 resolved in round 2; SA-NEW-001–003 carried into round 2)
- Resolved issue count: 3 this round (SA-NEW-001, SA-NEW-002, SA-NEW-003)
- Still open issue count: 0
- Partially resolved issue count: 0
- New issue count: 3 (SA-NEW-004 Medium, SA-NEW-005 Medium, SA-NEW-006 Low)
- Regression count: 0
- Significant findings remaining: Yes (two Medium)

## Adversarial review performed

- **Prior-fix retest:** verified SA-NEW-001/-002/-003 corrections against the revised text and the underlying repo contracts.
- **New-option audit (workflow_mode):** falsified three claims the design makes for it — the "precedent in Markdown Tooling and Project Specification," the "existing flat `when_any` predicate," and "migration classifies … as consumer-owned with preserve."
- **Migration-flow trace:** re-read `run_migrate`'s inputs to determine whether it can see `workflow_mode` at classification time.
- **Cross-package consistency:** compared the new option's name/vocabulary against the same-named options already shipped in two packages.
- **Interaction check:** examined `workflow_mode = consumer-owned` against the existing `ci.enabled`/`ci.performance` options.
- Not re-executed: no coverage run or migration was performed (read-only). Operability of the parallel gate and the preserve-vs-adopt migration path are asserted from provider code
  - payload evidence and are correctly delegated to the design's required tests.

## Prior findings status

### SA-NEW-001: Atomic-migration replacement of `scripts/check.py` collides with the dogfood twin

- Previous severity: Medium
- Current status: Resolved
- Evidence: Round-2 disposition (spec line 49) and the Workflow/Files/Verification sections now specify: the coverage-option implementation keeps the V1 bundle/root-script twin frozen; atomic migration "retire[s] only the obsolete root-script `_DOGFOOD` mapping; retain a frozen V1 bundle digest check and add current V2 root-rendering evidence" (spec lines 126, 150); acceptance criterion (spec line 166) requires retiring the twin assertion "without changing frozen V1 bytes, and prove[s] the new root script matches current V2 rendering." This matches the actual contract in `tests/test_adopt_dogfood.py` (`_DOGFOOD["python-tooling/check.py"] = "scripts/check.py"`). Separately, `workflow_mode = consumer-owned` preserves the repo's optimized `check.yml` (see SA-NEW-004 for the residual migration-wiring gap).
- Remaining action for the authoring agent: None for the twin itself.

### SA-NEW-002: Cross-field schema rule must guard an _omitted_ `parallel`

- Previous severity: Low
- Current status: Resolved
- Evidence: Spec lines 21, 58, 130, 160 now state the conditional "requires an explicitly present `parallel = true`; the schema rejects both false and omitted values," and Verification step 1 (spec line 142) adds a failing test "including omitted `parallel`." This closes the raw-input/default-ordering hole, consistent with the repo's `required`-in-`if` precedent (`standards/markdown-tooling/versions/1.2/config.schema.json:67,73`).
- Remaining action for the authoring agent: None.

### SA-NEW-003: "Coverage.py forces parallel mode internally" is questionable

- Previous severity: Low
- Current status: Resolved
- Evidence: Spec line 21 now says the rule "follows coverage.py's public subprocess guidance and does not rely on version-specific internal post-processing," and the round-2 disposition (spec line 51) reframes the internal behavior as "may force parallel" while the package "follows the public requirement for explicit parallel configuration and does not rely on that internal behavior." Accurate.
- Remaining action for the authoring agent: None.

## New blocking issues

None found.

## New non-blocking issues

### SA-NEW-004: Migration-time provisioning of `workflow_mode` is unspecified; `preserve` is not wired

- Severity: Medium
- Status: Confirmed
- Adversarial angle: The new option's migration path — the design states the intent but not the mechanism, and the mechanism is non-trivial given `run_migrate`'s inputs.
- Spec reference: "Workflow ownership" (spec line 95) — "migration classifies a recognized legacy workflow as `consumer-owned` with `preserve` disposition instead of adopting it"; "Legacy migration" (spec lines 102-110) which recognizes only `/python_tooling/coverage` and declares `workflow_mode = "consumer-owned"` in the fixture; Alternative #5 (spec line 35).
- Finding: `run_migrate(request, _resources)` builds the migrated config solely from the legacy namespace (`snapshots.legacy_config.python_tooling`) and recognizes a fixed key set — `version`, `additional_dev_dependencies`, `ruff`, `pytest` today, plus `coverage` per this design. It has **no** access to a pre-selected v5 config. The `check-workflow` disposition is produced from the static `_SIGNATURES` map (`"legacy-check-workflow": (".github/workflows/check.yml", "managed", "adopt")`) and `_PRESERVED_CONTAINER_DIGESTS`. For the migration to emit a `preserve` claim, `run_migrate` must learn the selected `workflow_mode` — which means recognizing `/python_tooling/workflow_mode` as a migration input (the design's Legacy migration section does not list it) and having the signature classifier consult it. As written, the fixture's `workflow_mode = "consumer-owned"` has no specified path into the classifier, so `check.yml` falls to the default `adopt` and the migration replaces the optimized workflow — precisely the regression Alternative #5 rejects. The release assertion (spec lines 146, 165) is a safety net that would _catch_ this, but the design should specify the mechanism rather than leave it to be discovered by a failing test.
- Repository evidence:
  - `standards/python-tooling/versions/1.1/providers/python_tooling.py:601-666` (`run_migrate` reads legacy_config/signatures only; recognized-keys loop at `:614`).
  - `python_tooling.py:579-589` (`_SIGNATURES`; `legacy-check-workflow` → `adopt`).
  - Spec line 104 recognizes `/python_tooling/coverage` only.
- External research evidence: Not applicable.
- Why it matters: Without the wiring, the migration silently regresses the very optimization this work exists to protect; with it, the design is coherent.
- Recommended action for the authoring agent: State explicitly that (a) `/python_tooling/workflow_mode` is a recognized migration input (add it to the recognized keys alongside `coverage`), and (b) the signature classifier resolves the `check-workflow` disposition to `preserve` when the resolved `workflow_mode = "consumer-owned"`. If the intended path is different (e.g., the migration receives the selected v5 config), specify that architecture change instead.
- Suggested validation (run only after implementation): a migration test asserting that with `workflow_mode = "consumer-owned"`, the `check-workflow` claim disposition is `preserve` and the optimized `check.yml` bytes are unchanged.

### SA-NEW-005: `workflow_mode` name/vocabulary collides with the two packages cited as precedent

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Repository-fit — the precedent cited to justify the option actually contradicts it.
- Spec reference: Spec line 26 — "a top-level `workflow_mode = "managed" | "consumer-owned"` option … follows … the top-level workflow-mode precedent in Markdown Tooling and Project Specification."
- Finding: Both cited packages already define a top-level option literally named `workflow_mode`, but with the values `["caller", "self-hosted"]` and default `"caller"` (`standards/project-spec/versions/1.1/config.schema.json:7`; `standards/markdown-tooling/versions/1.2/config.schema.json`). That is a _delivery_ axis: in both `caller` and `self-hosted` the workflow remains package-managed. Python Tooling's proposed `workflow_mode = "managed" | "consumer-owned"` is a different _ownership_ axis whose `consumer-owned` value means the package renders/locks/verifies nothing. Reusing the same option name across the ecosystem with an incompatible value set (and a different meaning) is a cross-package least-surprise and maintainability problem: a user who knows `workflow_mode = "caller"` from project-spec will find it invalid in python-tooling. The novel, risky part — a value where the package owns nothing — has no actual precedent among the cited options.
- Repository evidence: `standards/project-spec/versions/1.1/config.schema.json:7` (`"workflow_mode": { "enum": ["caller", "self-hosted"], "default": "caller" }`); `standards/markdown-tooling/versions/1.2/config.schema.json` (same option/values); Python Tooling currently renders a single inline `check.yml` with no caller/self-hosted choice.
- External research evidence: Not applicable.
- Why it matters: Option names are a stable, cross-package contract; shipping the same name with divergent vocabulary invites confusion and future churn (renaming later is a breaking config change).
- Recommended action for the authoring agent: Choose one — (a) name Python Tooling's option distinctly (e.g., `workflow_ownership`) to signal it is a different axis; (b) align the vocabulary with the ecosystem, e.g. extend the shared set so a package can express `self-hosted` (managed inline) vs a new `consumer-owned`/`external` value; or (c) if reuse is intentional, state explicitly why the same name carries a different vocabulary here and correct the "follows the precedent" wording, which currently overstates alignment.
- Suggested validation: schema review confirming the chosen name/values are consistent with (or deliberately distinct from) the other packages.

### SA-NEW-006: `ci.*` options are silently inert under `workflow_mode = "consumer-owned"`

- Severity: Low
- Status: Confirmed
- Adversarial angle: Option-interaction coherence.
- Spec reference: "Workflow ownership" (spec lines 92-100); existing `ci` object in `config.schema.json:92-100`.
- Finding: The existing `ci.enabled` (workflow trigger) and `ci.performance` (whether the performance gate is appended in `_commands`) shape only the generated `.github/workflows/ check.yml`. When `workflow_mode = "consumer-owned"`, that contribution is not materialized, so both `ci.*` toggles have no effect (and `scripts/check.py`, which stays managed, is driven by `_local_commands`, not `ci.performance`). The design does not note that `ci.*` becomes inert in consumer-owned mode.
- Repository evidence: `python_tooling.py:197-198` (`ci.performance` gates the CI-only performance command); `python_tooling.py:224-230` (`ci.enabled` gates the trigger); both feed `_workflow` only.
- External research evidence: Not applicable.
- Why it matters: A silently-inert option is a minor footgun — a consumer may set `ci.performance = true` under consumer-owned mode and wrongly expect it to matter.
- Recommended action for the authoring agent: Document that `ci.*` options apply only in `managed` workflow mode; optionally note it in the README option semantics.
- Suggested validation: documentation-only.

## Regressions

None found. The round-1/round-2 coverage-option resolutions (SA-001–SA-007, SA-NEW-001–003) remain intact in the revised text; adding `workflow_mode` did not disturb the coverage schema, provider rendering rules, dependency floor, or the parallel-aware gate.

## Remaining ambiguities and decisions needed

- **How `workflow_mode` reaches the migration classifier (SA-NEW-004).** Blocking for the migration step; the release assertion catches a failure but the mechanism should be specified.
- **Option name/vocabulary for the ownership axis (SA-NEW-005).** A naming decision to make before implementation, since it is a stable config contract.
- **Verification exclusion wiring.** The design says verification "excludes the workflow from managed whole-file drift checks" (spec line 96), but `run_verify` currently hardcodes the three whole-file targets (`python_tooling.py:556`). `run_verify` receives `config`, so it can read `workflow_mode` — this is implementable, but the authoring agent should confirm the hardcoded loop is made conditional. Non-blocking (design states the intent).

## Internet research performed

None this round. The external coverage.py facts (7.14.0 auto-combine; 7.10.0 `[run] patch`) were established and cited in rounds 1-2 and are unchanged; all round-3 findings rest on repository evidence.

## Read-only validation performed

- Read the revised spec in full — confirmed the SA-NEW-001/-002/-003 resolutions and the new `workflow_mode` sections (Approved approach, Contract changes → Workflow ownership, Failure behavior, Files, Verification, Acceptance criteria).
- Read `standards/project-spec/versions/1.1/config.schema.json` — confirmed a top-level `workflow_mode` with `["caller","self-hosted"]` (SA-NEW-005).
- Grepped `standards/markdown-tooling` and `standards/project-spec` — confirmed the same `workflow_mode = caller|self-hosted` shape in both.
- Read `standards/agent-handoff/versions/1.1/payload.toml` — confirmed the predicate mechanism (`[{ option = "…", equals/contains = "…" }]`) exists and gates contributions on config option values, substantiating the design's conditional-materialization claim.
- Re-read `providers/python_tooling.py` (`run_migrate`, `_SIGNATURES`, `run_verify`) — confirmed `run_migrate` sees only legacy_config/signatures and that `check-workflow` defaults to `adopt`; and that `run_verify` hardcodes the three whole-file targets (SA-NEW-004, verification-wiring note).
- Read `.project-standards.yml` — confirmed the repo currently selects `python_tooling: version: "1.0"` (no coverage/workflow_mode yet; both arrive at the atomic V5 migration).

## Recommended planning/implementation validation

- `uv run pytest tests/package_contract/test_python_tooling_reconstruction.py` — option, rendering, rejection (incl. omitted `parallel`), workflow-mode materialization, migration (run only after implementation).
- `uv run pytest tests/package_compatibility/test_release_candidate.py` — atomic-migration preservation incl. the preserved consumer-owned workflow, and the parallel-aware subprocess evidence (run only after implementation).
- `uv run pytest tests/test_adopt_dogfood.py` — twin contract before/at migration (run only after implementation).
- New migration test: with `workflow_mode = consumer-owned`, assert the `check-workflow` claim disposition is `preserve` and `check.yml` bytes are unchanged (SA-NEW-004; run only after implementation).
- Package/graph/projection/source-wheel gates and `uv run python scripts/run_repository_tests.py` (run only after implementation; writes coverage data).

## Final recommendation

The authoring agent should revise the specification using the findings above — SA-NEW-004 (specify how `workflow_mode` reaches the migration classifier so the optimized workflow is actually preserved) and SA-NEW-005 (resolve the `workflow_mode` name/vocabulary collision) — plus the SA-NEW-006 documentation note. No blocking findings remain; the coverage-option core (SA-001–SA-007, SA-NEW-001–003) is fully resolved and the design is otherwise ready to plan against once the two Medium items are settled.

## Review ledger for next loop

- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Audit round: 3
- Open issue IDs: SA-NEW-004, SA-NEW-005, SA-NEW-006
- Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007, SA-NEW-001, SA-NEW-002, SA-NEW-003
- Superseded issue IDs: none
- Significant findings remaining: Yes (two Medium: SA-NEW-004, SA-NEW-005)
- Next audit should focus on: the migration wiring that produces a `preserve` disposition for the consumer-owned workflow (SA-NEW-004), the option name/vocabulary decision (SA-NEW-005), and confirmation that `run_verify`'s whole-file loop is made conditional on `workflow_mode`.
