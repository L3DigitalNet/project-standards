# Ownership-Relinquishment Contract Convergence Audit

## Executive summary

This convergence audit reviews the ownership-relinquishment contract after the seven findings in [`2026-07-12-1741-ownership-relinquishment-contract-audit.md`](2026-07-12-1741-ownership-relinquishment-contract-audit.md) were reconciled. The reviewed target state is ADR 0023, SPEC-CP01 rev 0.10, SPEC-BA02 rev 0.11, the Python Tooling parallel-coverage design, the supporting migration research, and the live status/task/handoff surfaces.

**Verdict: Ready for implementation planning and test-driven implementation.** All seven prior findings are resolved. No significant safety, fail-open, backward-compatibility, traceability, or live-state contradiction remains. One minor documentation-synchronization advisory found during convergence was added to the implementation file map, verification sequence, and acceptance criteria, then independently rechecked as closed at the design gate.

This verdict does not claim implementation or release readiness. The live engine, models, schemas, providers, and shipping package documentation still implement the old fail-closed behavior. FR-037 and FR-038 remain Not Started until the approved changes and tests land.

## Scope and method

The audit compared intended behavior with current implementation seams rather than treating document agreement as sufficient evidence.

Reviewed contract artifacts:

- `docs/adr/adr-0023-unified-consumer-standards-control-plane.md`;
- `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md` rev 0.10;
- `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` rev 0.11;
- `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`;
- `docs/research/2026-07-12-python-tooling-consumer-owned-workflow-migration.md`;
- `docs/STATUS.md`, `docs/TODO.md`, `docs/specs/README.md`, and `docs/handoff/**` state surfaces.

Current-state implementation anchors:

- payload declarations and payload-wide validation in `src/project_standards/package_contract/payload.py`;
- generated strict payload and migration-report schemas under `src/project_standards/schemas/`;
- claim validation, signature inspection, planning, adopted-unit, removal, and stale-plan paths in `src/project_standards/control_plane/migration.py`;
- the shipping CLI Documentation known consumer-owned preserve claim;
- Python Tooling's current migration provider and versioned provider-output schema.

The primary audit and an independent read-only verifier each checked the prior finding ledger, then adversarially probed misdirected claims, omitted claims, known-history compatibility, bounded-block refusal, managed/destructive transitions, resolved-target materialization, and stale-plan/no-lock behavior.

## Prior-finding reconciliation

| ID | Prior severity | Disposition | Convergence evidence |
| --- | --- | --- | --- |
| SAFETY-01 | Major | Resolved | CP01 FR-037 and BA02 FR-037 place `consumer_owned_intent_pointer` in the trusted payload's single-target whole-file signature declaration. The claim must echo the pointer, signature, and target; the engine validates equality instead of trusting the provider's target choice. |
| BC-01 | Major | Resolved | CP01 DR-006/EC-018 and BA02 DR-006/EC-013 scope `intent_pointer` only to the unrecognized-whole-file exception. Known-history `consumer-owned`/`preserve` claims remain valid without the field, matching the shipping CLI Documentation provider. |
| REF-01 | Major | Resolved | STATUS, TODO, specs-plans, state, and the latest session pointer all place convergence and implementation before refreshed evidence and atomic source-root migration. |
| TRACE-01 | Minor | Resolved | CP01's blanket Must-completion checkbox is reopened and explicitly names FR-037/FR-038 as pending; the traceability row remains Not Started. |
| SAFETY-02 | Minor | Resolved | CP01 and BA02 require hold-and-emit-unless-cleared behavior. Every unknown observation without a fully valid FR-037 claim, including one omitted by the provider, retains `CP-MIGRATION-LEGACY-DIGEST`. |
| TRACE-02 | Minor | Resolved | BA02 traces the amended portion of DR-006 with FR-037 as Not Started while retaining the implemented base migration-graph row as Passing. |
| COH-01 | Nit | Resolved | ADR 0023 now requires both the exact observed target and digest, matching CP01 and BA02. |

## Engine-verifiability assessment

The revised proof is target-specific and implementable through existing generic seams:

1. The immutable selected payload statically binds one canonical pointer to one single-target `whole-file` signature.
2. Payload validation rejects the declaration on bounded-block or multi-target signatures and rejects pointer reuse across signature targets in one payload.
3. Raw pre-default migration input must explicitly contain the bound pointer with literal value `consumer-owned`.
4. The provider must report that pointer as recognized and echo it in the claim.
5. The claim's standard, signature, target, and digest must match the engine-owned observation and the static declaration.
6. The claim must use `ownership = "consumer-owned"` and `disposition = "preserve"`.
7. The resolved payload must materialize no artifact or contribution at the target.
8. A valid claim clears only its exact held unknown-digest finding; every rejected or absent claim leaves the finding in place.
9. Preserve disposition continues to bypass adopted-unit, removal, package-unit, and lock-import paths.
10. Preview exposes the unvalidated path/digest, and apply remains bound to the previewed path, file type, and bytes.

This closes the original provider-self-certification defect. A provider cannot cite one recognized owner setting and relinquish a different file because the target is fixed by the payload declaration and compared by the engine.

## Backward-compatibility assessment

Both new fields are optional at the data-model level:

- `consumer_owned_intent_pointer` appears only on payload signatures eligible for the new exception;
- claim `intent_pointer` appears only when an unknown whole-file observation invokes that exception.

Existing known-history claims retain their current shape. The canonical regression case is CLI Documentation's known `.github/workflows/cli-docs-check.yml` claim, which remains `consumer-owned`/`preserve` without either new field. Unknown managed, destructive, shared, package-lock, and bounded-block claims still require declared known content and fail closed.

## Convergence advisory

### ADV-001: Synchronize authoring and generated descriptions during implementation

The shipping Standard Bundle Authoring 2.0 README currently states that all unknown or modified legacy bytes block automatic migration. Current model and generated-schema descriptions likewise describe every disposition or claim as exactly recognized package history. Those statements accurately describe the live pre-implementation engine but would become incomplete after FR-037 lands.

The Python Tooling design now explicitly includes:

- the Standard Bundle Authoring 2.0 README and legacy-signature template;
- `LegacySignatureDeclaration`, `LegacyDisposition`, and `LegacyClaim` descriptions;
- generated standard-payload and migration-report schema descriptions;
- payload and Standard Bundle Authoring self-hosting/reconstruction tests;
- a verification step and acceptance criterion requiring the narrow exception to be distinguished from arbitrary unknown-byte acceptance.

**Disposition: Closed at the design gate.** These are implementation obligations, not an unresolved contract decision. The independent follow-up found no remaining omitted surface.

## New-finding ledger

No open findings remain. The convergence advisory above is incorporated into the approved implementation scope.

## Implementation boundary and next gate

The next distinct artifact is an implementation plan covering the generic payload/model/schema work, migration-engine TDD, Python Tooling options/provider/payload changes, authoring-document synchronization, generated integrity updates, disposable release evidence, and the atomic root-script migration boundary.

That plan requires its own plan-flow review. Implementation should begin only after the plan maps every FR-037/FR-038 acceptance criterion and the Python Tooling design's verification rows. The repository is not release-ready until implementation, source/wheel parity, the optimized full gate, refreshed disposable release evidence, and the atomic v5 source-root migration all pass.

## Final verdict

**Ready.** The ownership-relinquishment contract has converged and is ready for implementation planning and TDD. It is not yet implemented or release-ready.
