---
plan_format: 3
title: 'ADR Amendment Validation Implementation Plan'
slug: 'adr-amendment-validation'
status: active
revision: 5
revises_revision: 4
revision_reason: 'authorize only the full-gate-discovered current-catalog baseline, README current ADR references, and dogfood current-version parameter'
pause_reason: ''
source: 'issue L3DigitalNet/project-standards#163; verified 2026-08-10 triage and repository evidence'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-11
owners:
  - 'Project Standards maintainers'
  - 'Coding agents under human review'
---

# ADR Amendment Validation Implementation Plan

> **Definition, not state.** Plan authoring generated no `.project-pipeline` state. During execution, the orchestrator alone generates and mutates ephemeral state under `.project-pipeline/2026-08-10-adr-amendment-validation/execution/`.

## 1. Objective

Ship ADR 1.6 with an independent, default-off `validate_amendments` option that checks reciprocal `project.amends` / `project.amended_by` relationships and rejects an amendment of a superseded record. First produce a complete, unadvertised candidate whose provider reports stable, actionable findings without changing any default 1.5 consumer result; then, after the v5.19 ADR-writing set is frozen and reconciled, activate 1.6 in Catalog 5, opt this repository into the guardrail, and prove the final corpus plus tagged released corpora remain green. Preserve every ADR 1.5 byte, mode, digest, optional-field behavior, and create-only consumer artifact.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `issue:L3DigitalNet/project-standards#163` | normative | Outcome, two validation families, stable finding requirement, optional-field compatibility, successor-cut constraint, released-corpus evaluation, and explicit non-goals. The 2026-08-10 owner comment establishes the existing document-snapshot seam and identifies the separate-option decision. | 2026-08-10 | §§1, 3–13; T1–T2 |
| `request` | normative | Select the evidence-backed long-term design: add a new default-false option instead of silently broadening `require_sections`; deliver an unadvertised candidate followed by activation and final verification. Revision 3 authorizes the reconciliation-required tracked Catalog 5 snapshot; revision 4 authorizes only the stale predecessor activation assertions exposed by T2's focused proof; revision 5 authorizes only the three stale current-release consumer assertions exposed by T2's direct-local full gate. | 2026-08-11 | §§1, 3–13; T1–T2 |
| `repo:standards/adr/versions/1.5/README.md#amendment-workflow` | decision | Reciprocal amendment vocabulary, active-versus-superseded distinction, optional fields, no prose inference, and accepted-text preservation. | `e24f50ef` | §§3–7, 9–12; T1 |
| `repo:standards/adr/versions/1.5/providers/adr.py::run_validate` | current-state evidence | One provider receives the complete immutable document array, gates all validation on `require_sections`, emits three existing finding codes, sorts findings deterministically, and hard-codes one section-oriented hint. | `e24f50ef` | §§4–7, 9; T1 |
| `repo:src/project_standards/control_plane/provider_inputs.py::_frontmatter_input` | current-state evidence | The ADR command already captures the repository Markdown corpus into one `snapshots.documents` array; no control-plane or provider-input construction change is needed. | `e24f50ef` | §§3–5, 9; T1 |
| `repo:standards/adr/versions/1.5/config.schema.json` | current-state evidence | The closed option object currently contains `contract_version` and default-false `require_sections`; a new option must be declared explicitly. | `e24f50ef` | §§4–6, 9; T1 |
| `repo:standards/adr/versions/1.5/schemas/findings.schema.json` | current-state evidence | Finding `code`, `identity`, `message`, and `hint` are open strings, so new stable codes require no output-schema revision. | `e24f50ef` | §§4–7, 9; T1 |
| `repo:standards/adr/versions/1.5/payload.toml` | current-state evidence | Complete 1.5 resource/provider/artifact/legacy inventory and self-version contract that 1.6 must preserve or refresh explicitly. | `e24f50ef` | §§4–7, 9; T1 |
| `repo:tests/package_contract/test_adr_1_5.py` | current-state evidence | Predecessor immutability, option/provider compatibility, provider invocation, identity, projection, and activation proof pattern. Its current activation assertions pin the pre-1.6 state—1.5 default and mutable navigation on 1.5—so T2 must update only those expectations after the authorized successor activation. | `fb6f1079` | §§4–7, 9–12; T1–T2 |
| `repo:docs/plans/2026-08-10-v519-adr-corpus-corrections-plan.md#phase-p4-corpus-wide-link-and-path-reconciliation` | decision | The release-wide corpus freeze and T4 checkpoint own the last v5.19 ADR-writing sweep, including #157, #142, and any later-settled ADR work. | revision 1 | §§3, 5–7, 9–12; T2 entry gate |
| `repo:catalogs/5.toml` | current-state evidence | Catalog 5 package rows and current ADR 1.5 default role; T2 owns the atomic 1.6 default/1.5 retained transition. | `e24f50ef` | §§4–6, 9–12; T2 |
| `repo:.standards/config.toml` | operational evidence | Producer self-host selection is `latest`, with only section validation enabled before T2. | `e24f50ef` | §§4–7, 9–12; T2 |
| `repo:.standards/catalog.toml` | operational evidence | The committed consumer Catalog 5 snapshot is an apply-owned reconciliation target. The revision-2 T2 preview exposed one required refresh after ADR 1.6 activation, so revision 3 authorizes only that generated snapshot/provenance delta. | `6c98c13e` | §§3–7, 9–12; T2 |
| `repo:.standards/lock.toml` | operational evidence | Generated current resolution selects ADR 1.5 and records the catalog/config/package inventory T2 must reconcile without hand editing. | `e24f50ef` | §§4–7, 9–12; T2 |
| `repo:standards/adr/README.md` | current-state evidence | Mutable family landing page identifies 1.5 as current authority; it changes only at activation. | `e24f50ef` | §§4–6, 9; T2 |
| `repo:standards/README.md` | current-state evidence | Mutable standards index exposes current package version and role; it changes only at activation. | `e24f50ef` | §§4–6, 9; T2 |
| `repo:docs/handoff/deployed.md` | operational evidence | Signed v5.17.0 and v5.18.0 tags provide immutable pre-amendment and first-amendment-vocabulary corpora for compatibility evaluation. | 2026-08-10 | §§6–7, 9, 12; T1–T2 |
| `repo:docs/handoff/conventions.md#18-match-verification-to-the-changed-surface` | operational evidence | Candidate payload/test changes require a current candidate runtime and fast repository gate; final release-prep content uses the full serial battery. Both repository gates include Git-history-backed issue-regression validation and therefore run direct-local. | 2026-08-10 | §§7, 9–12; T1–T2 |
| `repo:docs/handoff/conventions.md#22-rexec-v02-is-a-remote-only-root-configured-execution-path` | operational evidence | CPU-intensive synchronized-tree-compatible focused/package/static checks run through rexec v0.2; Git/index/history and both repository gates remain direct-local because `.git` is never synchronized. | 2026-08-10 | §§3, 7, 9, 12; T1–T2 |
| `repo:tests/issue_regressions/ledger.py::_historical_issue_tables` | current-state evidence | The repository verification suite reads ledger history through `git log --follow`, so `scripts/verify.sh` and `scripts/verify.sh --full` require the authoritative local Git checkout. | `e24f50ef` | §§3, 7, 9, 12; T1–T2 |
| `repo:tests/package_contract/test_current_catalog_activation.py::_BASELINE_REF` | current-state evidence | Release-activation regression derives successor targets relative to one historical baseline. It still compares against v5.17.0 while `_RELEASE_VERSION` already names 5.18.0, so ADR 1.6 is misclassified as a fifth v5.18 activation target. | full-gate ordinary receipt 2026-08-11 | §§3–7, 9–12; T2 |
| `repo:README.md` | current-state evidence | Human-facing ADR standard and current-consumer references still name 1.5 after the authorized 1.6 activation; only those four reference lines and adjoining current-package prose are stale. | full-gate ordinary receipt 2026-08-11 | §§3–7, 9–12; T2 |
| `repo:tests/test_adopt_dogfood.py::test_current_adoption_guides_use_v5_packages_not_v1_fragments` | current-state evidence | The current-adoption-guide parameter still selects ADR 1.5 after mutable navigation moved to 1.6. | full-gate ordinary receipt 2026-08-11 | §§3–7, 9–12; T2 |

Conflict precedence: the explicit request resolves issue #163's embedded option-design choice in favor of an independent default-false option. The issue defines validation behavior; ADR 1.5 defines relationship semantics; current code and tests establish only the starting seam and preservation surface. The release-wide ADR corpus plan owns the final corpus freeze and wins over an earlier inventory.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- Add `validate_amendments`, a top-level ADR option of type boolean with default `false`, independently composable with `require_sections`.
- When enabled, validate both directions of every amendment relationship over the complete captured ADR corpus and report a missing reciprocal member with stable code `ADR-AMEND-ONEWAY`.
- When enabled, report each `project.amends` edge whose target record has `status: superseded` with stable code `ADR-AMEND-SUPERSEDED`.
- Make amendment findings name the involved record IDs, identify the offending or missing field deterministically, point at a useful record path, and carry a relationship-specific repair hint.
- Cut a complete ADR 1.6 consumer payload, focused contract, family index/digest, source projection, generated catalog facts, and Unreleased changelog entry while ADR 1.5 remains default and byte-immutable.
- Evaluate the candidate against focused negative controls, every compatible ADR 1.5 payload document, the current post-#159/#160/#161 corpus, and the immutable v5.17.0/v5.18.0 repository ADR corpora.
- After the external v5.19 corpus-freeze checkpoint, activate 1.6, repoint mutable family navigation, enable the new option in this repository, reconcile the tracked consumer-catalog snapshot, lock, and managed state, and prove the frozen corpus has zero amendment findings.
- Align only the three full-gate-discovered current-release consumers with that activation: the catalog-activation baseline reference, README's four ADR-current reference lines plus adjoining current-package prose, and the dogfood current-adoption-guide ADR parameter.

### 3.2 Out of Scope and Deferred

- No inference of amendment relationships, scope, or authority from prose, blockquotes, links, `related`, or `### Amendments` content.
- No validation of amendment-note placement or body form and no new required heading or frontmatter field.
- No change to Markdown Frontmatter schemas, reference validation, duplicate-ID policy, control-plane snapshot construction, provider protocol, or findings schema.
- No modification of ADR 1.5 or any earlier immutable payload, and no rewrite of consumer-authored ADRs or an existing create-only `docs/adr/adr.template.md`.
- No package-to-package migration edge: default behavior is unchanged, both amendment fields remain optional, and the additive option resolves false until a consumer opts in.
- No release-version bump, publication, tag movement, GitHub issue mutation/closure, or Agent Handoff mutation. The parent v5.19 release workflow owns those actions after this plan's activated checkpoint.
- No claim that arbitrary private downstream corpora have been inspected. Default-off compatibility is contract proof; the direct corpus audit is bounded to this repository's immutable released tags and final v5.19 corpus.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | ADR 1.6 provider/config/documentation behavior; the complete unadvertised payload, digest, projection, generated catalog contribution, focused package contract, changelog entry, and tagged-corpus compatibility procedure. |
| T2 owns / aggregates | Catalog/default activation, mutable ADR-family and standards navigation, this repository's dogfood option/config/tracked catalog snapshot/lock, final form of the shared catalog document, ADR 1.5/1.6 activation assertions, current-release catalog/README/dogfood consumers, frozen-corpus proof, and final full qualification. |
| Depends on | Integrated #159/#160/#161 checkpoints before T1 corpus proof; the release coordinator's final ADR-writing-set declaration and completed corpus-correction T4 checkpoint before T2. |
| Does not own | Control-plane input construction, Markdown Frontmatter validation, ADR corpus authoring/correction, v5.19 release metadata/publication, downstream consumer configuration, or GitHub lifecycle state. |
| Must preserve | Every ADR 1.5 and earlier byte/mode/digest and every ADR 1.5 provider/predecessor behavior assertion; absent/empty amendment-field validity; default provider results; three-section behavior; deterministic existing findings; legacy migration semantics; create-only scaffold ownership; `_RELEASE_VERSION = "5.18.0"`; and unrelated bytes in README, source catalog, tracked catalog snapshot, config, lock, tests, and managed content. |

### 3.4 Constraints and Authorization

- `validate_amendments = false` is binding. Reusing `require_sections`, turning the new validation on by default, or coupling the two booleans would violate the approved compatibility design.
- The provider evaluates only documents present in the one immutable `snapshots.documents` request. A referenced ID absent from that complete corpus fails reciprocal lookup under `ADR-AMEND-ONEWAY`; it does not create a third validation family.
- Relationship-shape/frontmatter-schema defects remain owned by the Markdown Frontmatter companion. This task must not invent a second metadata schema or new shape-finding taxonomy.
- Existing `ADR-PATH`, `ADR-PARSE`, and `ADR-SECTION` semantics and deterministic sort order remain stable; refactoring `_finding` may parameterize hints only as needed for accurate repair guidance.
- The 1.6 input schema changes only its self-version constant from `1.5` to `1.6`; the findings and migration-report schemas remain byte-identical to 1.5.
- `contract_version` remains `1.0`; the optional default-off check adds no required ADR content. The legacy migration continues to recognize only released V4 settings and targets package 1.6.
- T1 leaves Catalog 5, `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, family-root current-authority pages, and release metadata unchanged. T2 may mutate those activation surfaces only after its external entry gate; the tracked catalog snapshot may change only to the candidate-wheel Catalog 5 rendering required by reconciliation.
- CPU-intensive synchronized-tree-compatible focused pytest, package validators, Ruff, and BasedPyright run through rexec v0.2. Both `scripts/verify.sh` and `scripts/verify.sh --full` run direct-local with `PYTHONPATH="$PWD/build/wheel-runtime"` because their issue-regression ledger reads Git history/tags. Git-tag extraction, corpus materialization, `git diff`, `git ls-files`, and Git-tracked Markdown selection also run direct-local. Reconciliation applies direct-local because it mutates the authoritative checkout.
- T2's revision-2 acceptance fingerprint is preserved byte-for-byte. Its inherited phrase “final rexec full gates” names the aggregate qualification set, not the execution location; this section, T2.6, and PV-T2-001 bind the full repository gate to direct-local execution and only the synchronized-tree-compatible focused/package/static checks to rexec.
- T2 may update `tests/package_contract/test_adr_1_5.py` only where its activation assertions must reflect the already-authorized successor state: 1.5 is retained and exact-selectable, while Catalog 5 default/current and mutable navigation point to 1.6. Provider, payload, compatibility, and predecessor behavior assertions remain exact.
- T2 may update `tests/package_contract/test_current_catalog_activation.py` only by advancing `_BASELINE_REF` from `v5.17.0` to `v5.18.0`; `_RELEASE_VERSION` remains `5.18.0`, making ADR 1.6 the sole post-baseline activation target while preserving every other release assertion.
- T2 may update `README.md` only in the four current ADR reference lines around the ADR Standard block and Current consumer packages table, plus the adjoining current-package prose needed to distinguish 1.5's amendment vocabulary from 1.6's optional validation. Every unrelated README byte remains exact.
- T2 may update `tests/test_adopt_dogfood.py` only by changing the current-guide parameter `("adr", "1.5")` to `("adr", "1.6")`; every other parameter and assertion remains exact.
- One repository gate may run at a time. T1 runs the fast gate after its final candidate content change; T2 runs the full serial gate after the final activation/content change and before its checkpoint.

## 4. Current State and Target State

### 4.1 Current State

- ADR 1.5 is indexed, projected, Catalog 5 default, selected by this repository through `version = "latest"`, and configured with `require_sections = true`.
- Its closed option schema has no amendment-validation switch. `run_validate` returns immediately unless section validation is enabled, then parses each regular ADR snapshot and emits only path, parse, and missing-section findings.
- The provider already receives the complete repository Markdown corpus in one invocation; ADR-specific selection is implemented by `_frontmatter_input`, so cross-document validation needs no engine or input-schema-shape change.
- The finding schema accepts new string codes. The provider helper's one hard-coded template hint is unsuitable for a missing reciprocal relationship.
- The current corpus has reciprocal amendment fields and no amendment of a superseded record. The issue's owner measured 13 amendment edges across 11 records with zero problems before later v5.19 ADR additions; integrated #159/#160/#161 work must be remeasured rather than assumed.
- ADR 1.5's package contract proves 1.4 records remain valid, the option/provider surface stayed additive, all payload identities/digests/projection agree, and 1.5 activation is coherent.
- Revision-2 T2 stopped before apply when candidate-wheel reconciliation previewed exactly one out-of-claim action: `update .standards/catalog.toml — refresh catalog 5 from 5.18.0 to 5.18.0`. At that boundary, its seven already claimed authored edits were preserved while `.standards/catalog.toml`, `.standards/lock.toml`, and `standards/catalog.md` remained untouched.
- Revision-3 T2 reached an exact ten-path reconciliation fixed point and proved the second preview/apply is a no-op. The focused command `rexec -- uv run pytest tests/package_contract/test_adr_1_6.py tests/package_contract/test_adr_1_5.py -q` then returned `31 passed, 2 failed`: ADR 1.6 tests passed, while only the unclaimed ADR 1.5 activation assertions still expected 1.5 as default and mutable navigation to 1.5. T2 stopped without an out-of-scope edit or full gate.
- Revision-4 T2 corrected those two activation assertions and reached an exact staged eleven-path candidate. The sole direct-local `PYTHONPATH="$PWD/build/wheel-runtime" scripts/verify.sh --full` exited 1 after 77:02. Statics passed in 1:00 (Ruff 606, BasedPyright 0/0/0, Prettier green, markdownlint 1,796/0, pip-audit green); ordinary returned `8 failed, 4,935 passed, 146 deselected in 1958.58s` after 32:41; compatibility passed 141 tests in 2559.77s after 42:40; performance passed 5 with 5,084 deselected in 38.15s after 0:39; and coverage reporting passed in 0:02 at 21,957 statements, 1,912 misses, 8,098 branches, 969 partials, and 90%. Six ordinary failures expected four activation targets but observed five because `_BASELINE_REF` remained v5.17.0; the seventh current-catalog node emitted four `PC-RELEASE-PACKAGE-CURRENT` findings from README's stale ADR 1.5 references/current-package prose; the eighth was the stale `("adr", "1.5")` dogfood parameter. The worker made no out-of-claim edit, rerun, or commit; its eleven staged paths remained exact with no unstaged/untracked path, `git diff --check` green, cached binary-diff SHA-256 `8de13d82034a50d7a211b0b3ee69f7667a35f3afbad2e16e59572387c22f1b4a`, and ADR 1.6 aggregate `sha256:12b9490be7cf3284bfb7f510b03b2cd555ab7c57f0a7628c9f95c659c241ba42`.

### 4.2 Target State

ADR 1.6 is a complete Catalog 5 default package. Its provider keeps section validation independent while an explicit `validate_amendments = true` performs a deterministic corpus-wide relationship pass. A one-way or dangling edge reports `ADR-AMEND-ONEWAY`; an `amends` edge to a superseded target reports `ADR-AMEND-SUPERSEDED`; messages and hints identify the records and repair the relationship rather than recommending a template rewrite.

The package is first reviewable as an exact-selectable unadvertised candidate. Only after the final v5.19 ADR corpus is frozen and corrected does T2 make 1.6 default, retain 1.5, repoint mutable family and root README documentation, opt this repository into the new guardrail, reconcile the tracked consumer-catalog snapshot and lock from the same candidate runtime, and advance only the release/dogfood assertions whose meaning is “current after v5.18.0.” The tagged v5.17/v5.18 corpora, every 1.5-compatible payload document, and the final v5.19 corpus prove the new default cannot regress released consumers and the opt-in check accepts known-good amendment populations.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Config | `contract_version`, `require_sections`; closed object. | Add boolean `validate_amendments`, default `false`. | Existing selections resolve to the same effective behavior; unknown keys remain invalid. |
| Provider gate | All validation is gated by `require_sections`. | Parse when either option is enabled; run section and amendment passes independently. | Both false returns no findings; section-only results stay exact. |
| Reciprocity | Author guidance only. | Both directions and missing targets produce `ADR-AMEND-ONEWAY`. | No prose inference or required fields. |
| Supersession | Author guidance only. | `amends` target with `status: superseded` produces `ADR-AMEND-SUPERSEDED`. | Supersession fields/status rules remain owned elsewhere. |
| Findings | Section-oriented codes/hint and deterministic sort. | Two stable codes and relationship-specific messages/hints. | Existing finding bytes/order for existing cases. |
| Package | 1.5 default and immutable. | 1.6 complete, first unadvertised, then default; 1.5 retained. | 1.5 tree, digest, modes, artifacts, and migration behavior. |
| Dogfood | Current corpus checks required sections only. | Final frozen corpus also checks amendment consistency. | Existing scaffold bytes and unrelated standards state. |
| Release impact | No machine amendment guard. | Default-off and tagged-corpus proof demonstrate non-regression; opt-in released/current corpora remain green. | No assertion about uninspected private corpora. |
| Current-release consumers | Activation baseline, root README references/prose, and dogfood current-guide parameter still describe the pre-1.6 state. | Baseline advances to v5.18.0 while release remains 5.18.0; only current ADR references/prose and the ADR guide parameter move to 1.6. | Every unrelated release assertion, README byte, dogfood parameter, and test assertion remains exact. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| ADR option contract | Section-check enablement. | Independent section and amendment enablement. | `standards/adr/versions/1.6/config.schema.json` | T1 |
| ADR provider | Per-document section validation. | Existing section pass plus one corpus index and two relationship checks. | `standards/adr/versions/1.6/providers/adr.py::run_validate` | T1 |
| Provider schemas | 1.5 request identity and open finding strings. | 1.6 request identity; otherwise unchanged schema bytes. | `schemas/provider-input.schema.json`; findings/migration schemas | T1 |
| Immutable package | ADR 1.5 complete/default. | ADR 1.6 complete/unadvertised with exact predecessor preservation. | `standards/adr/versions/1.6/**`; `standard.toml`; projection | T1 |
| Package proof | ADR 1.5 successor and activation contract. | ADR 1.6 behavior, compatibility, integrity, non-activation, then activation contract. | `tests/package_contract/test_adr_1_6.py` | T2 aggregator; T1 contributor |
| Catalog/navigation | 1.5 default/current family authority. | T1 renders 1.6 unadvertised; T2 makes 1.6 default and repoints mutable navigation. | `catalogs/5.toml`; `standards/catalog.md`; family roots; `standards/README.md` | T2 |
| Repository dogfood | Latest resolves 1.5 with sections enabled. | Latest resolves 1.6 with both checks enabled and a reconciled Catalog 5 snapshot/lock. | `.standards/config.toml`; `.standards/catalog.toml`; `.standards/lock.toml` | T2 |
| Corpus compatibility | Issue measurement only. | Reproducible focused, current, v5.17.0, and v5.18.0 proof. | candidate provider; immutable Git tags; final corpus | T1 producer; T2 final aggregator |
| Current-release assertions | v5.17.0 baseline and ADR 1.5 README/dogfood references predate the activated successor. | Treat v5.18.0 as the activation baseline, ADR 1.6 as the sole post-baseline target, and 1.6 as current in root guidance. | `tests/package_contract/test_current_catalog_activation.py`; `README.md`; `tests/test_adopt_dogfood.py` | T2 |

### 5.2 Control and Data Flow

The control plane continues to capture the repository corpus once and passes immutable snapshots to the selected ADR provider. When both booleans are false, the provider returns the existing empty result. Otherwise it parses ADR records once, preserves existing path/parse handling, runs the three-section check only when requested, and—when amendment validation is requested—indexes ADRs by canonical `id` and compares each declared relationship with its counterpart. The relationship pass neither reads the filesystem nor infers prose. T2 changes only package selection and self-host configuration; the data shape and provider boundary remain unchanged.

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Add the two opt-in relationship findings with exact silent controls. | PV-T1-001 | T1 |
| Architecture / dependency direction | yes | Keep validation inside the version-selected provider over existing snapshots; no control-plane dependency moves. | PV-T1-001 | T1 |
| Public / cross-task interface | yes | Add one default-false config key and two stable finding codes; input/output shapes otherwise remain exact. | PV-T1-001 | T1 |
| Data / state | no | No persistent application state; only immutable payload and generated repository projections change. | PV-T1-001 | T1 |
| Configuration | yes | T1 declares the option; T2 explicitly enables it in this repository and reconciles the lock. | PV-T1-001, PV-T2-001 | T1, T2 |
| Security / trust | yes | Provider remains pure over captured bytes and performs no filesystem, subprocess, or network access. | PV-T1-001 | T1 |
| Compatibility / migration | yes | Default-off behavior, tagged corpora, exact 1.5 bytes, and unchanged legacy semantics prove additive MINOR compatibility. | PV-T1-001, PV-T2-001 | T1, T2 |
| Operations / deployment | yes | Separate unadvertised candidate from Catalog 5/self-host activation; publication remains external. | PV-T1-001, PV-T2-001 | T1, T2 |
| Documentation | yes | Versioned docs describe the option/codes and mutable navigation follows activation. | PV-T1-001, PV-T2-001 | T1, T2 |
| Release/current assertions | yes | Advance only the baseline constant, four root ADR-current reference lines plus adjoining prose, and one dogfood parameter; exact diff rejects every unrelated byte. | PV-T2-001 | T2 |
| Durable evidence | no | Committed tests, immutable tags, and repeatable commands reproduce all evidence; verbose output remains ephemeral. | PV-T1-001, PV-T2-001 | T1, T2 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Name the new option `validate_amendments` and default it to `false`. | One option owns the full amendment-consistency concept; independence prevents existing section-check consumers from becoming red and leaves room for future amendment checks without another gate. | request; issue #163 | T1–T2 |
| D-002 | Keep `require_sections` and `validate_amendments` independent; parse once when either is true. | The checks govern unrelated contracts but share immutable document decoding. | request; current provider | T1 |
| D-003 | Use `ADR-AMEND-ONEWAY` for missing inverse membership or an absent referenced record, and `ADR-AMEND-SUPERSEDED` for an `amends` target whose status is superseded. | These are the issue's two validation families; stable codes need no findings-schema change. | issue #163 | T1 |
| D-004 | Emit one deterministic finding per failed directed obligation, with the missing/offending field and both IDs represented in identity/message. | A maintainer must know which record to edit; one-sided relationships must not double-report the same missing membership. | issue #163; current finding contract | T1 |
| D-005 | Cut 1.6 as an additive MINOR with `contract_version = "1.0"` and no package-to-package migration edge. | Optional default-off validation changes no existing effective behavior or required document shape. | issue #163; ADR 1.5; versioning contract | T1 |
| D-006 | Require the final release-wide ADR corpus checkpoint before activation, not before candidate construction. | Provider/package work is file-disjoint, but activation proof must observe the final corpus it will guard. | issue #163 triage; corpus-corrections plan | T1–T2 |
| D-007 | Audit immutable v5.17.0/v5.18.0 corpora and run fast/full repository gates direct-local; keep only synchronized-tree-compatible focused/package/static checks on rexec v0.2. | The tags bracket absence and first use of amendment fields, while the repository gates' issue-regression ledger reads Git history; `.git` cannot exist on the worker. | issue #163; rexec v0.2 convention; issue-regression ledger | T1–T2 |
| D-008 | Treat v5.18.0 as the release-activation baseline while keeping `_RELEASE_VERSION = "5.18.0"`, and update only root README/current-guide surfaces that explicitly track the active ADR payload. | The full-gate failures are stale consumer expectations, not ADR 1.6 behavior defects: the baseline delta must contain only ADR 1.6, while current human and dogfood navigation must follow the activated package. | direct-local full-gate ordinary receipt; request | T2 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | ADR 1.6 shall add only one config option, `validate_amendments: boolean = false`; it shall be independent of `require_sections`, retain `contract_version = "1.0"`, and keep unknown options invalid. | request; issue #163 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| REQ-002 | With amendment validation enabled, every missing inverse `amends`/`amended_by` membership and every referenced record absent from the complete corpus shall yield one deterministic `ADR-AMEND-ONEWAY` error naming both IDs or the missing target and identifying the field to repair. | issue #163 | Must | T1 | T1 | PV-T1-001 |
| REQ-003 | With amendment validation enabled, each `amends` edge to a record whose status is `superseded` shall yield `ADR-AMEND-SUPERSEDED`, naming source and target and pointing at the offending relationship. | issue #163; ADR 1.5 | Must | T1 | T1 | PV-T1-001 |
| REQ-004 | Existing path, parse, and three-section findings and deterministic ordering shall remain unchanged; amendment messages/hints shall be relationship-specific; no prose, note-placement, semantic-scope, duplicate-ID, or metadata-shape validator shall be added. | issue #163; 1.5 provider/findings contract | Must | T1 | T1 | PV-T1-001 |
| REQ-005 | ADR 1.6 shall be a complete V2 consumer payload with self-consistent identity, digests, schemas, legacy route, projection, docs, and focused contract; every ADR 1.5 byte/mode/digest and every unchanged 1.6 predecessor file shall be pinned. | issue #163; V2 package contract | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| REQ-006 | Default/absent `validate_amendments`, empty/absent relationship fields, every compatible 1.5 payload document, and v5.17.0/v5.18.0 tagged corpora shall produce no new findings; enabling the option on known-good released/current amendment populations shall produce no amendment finding. | issue #163 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| REQ-007 | T1 shall leave 1.6 complete and unadvertised while 1.5 remains default/current and `.standards` state remains unchanged. | request; catalog channel contract | Must | T1 | T1 | PV-T1-001 |
| REQ-008 | After the final v5.19 ADR-writing set and corpus-correction T4 checkpoint, T2 shall make 1.6 Catalog 5 default, retain 1.5, repoint mutable navigation, explicitly enable amendment validation, reconcile the lock, and obtain zero amendment findings over the frozen corpus without changing the create-only scaffold. | request; corpus-corrections plan | Must | T2 | T2 | PV-T2-001 |
| REQ-009 | Synchronized-tree-compatible focused/package/static checks shall run through rexec v0.2; Git-dependent release-corpus, diff, tracked-Markdown, and fast/full repository gates shall run direct-local with the candidate `PYTHONPATH`; T1 shall run the fast gate and T2 the final full gate after their last content changes. | request; repository conventions; issue-regression ledger | Must | T2 | T1, T2 | PV-T1-001, PV-T2-001 |

## 7. Verification and Evidence Strategy

- **Provider/contract layer:** correct-reason RED and GREEN in `tests/package_contract/test_adr_1_6.py` cover both relationship directions, a dangling target, a superseded target, stable codes/paths/identities/messages/hints/order, independent option combinations, silent controls, unchanged section cases, provider purity, and package identity.
- **Predecessor oracle:** ADR 1.5's aggregate digest, complete file/mode tree, option/provider behavior, examples/templates, migration schema, and artifact policy establish the immutable compatibility baseline. Its activation assertions follow the mutable catalog state: after T2, 1.5 is retained/exact-selectable and 1.6 owns current/default navigation, without changing predecessor behavior.
- **Released-corpus oracle:** direct-local Git-tag extraction of `v5.17.0` and `v5.18.0` supplies immutable before/after amendment-vocabulary corpora. The candidate is invoked once with its resolved default and once with amendment validation enabled; both populations must have zero new/amendment findings. Git operations and repository gates stay local; synchronized-tree-compatible provider/package/static checks stay on rexec.
- **Current-corpus oracle:** before T1 checkpoint, remeasure the post-#159/#160/#161 documents and prove zero amendment findings; before T2, consume the release coordinator's frozen checkpoint inventory and rerun over the complete post-correction v5.19 corpus. On T2 recovery, retain the pre-apply preview receipt that identified `.standards/catalog.toml` as the sole out-of-claim reconciliation target and confirm the three not-yet-applied generated surfaces remain unchanged before resuming.
- **Negative controls:** remove each reciprocal side independently; reference an absent ID; change an `amends` target to `status: superseded`; couple amendment validation to `require_sections`; enable it by default; restore the generic template hint; mutate one 1.5 byte; stale one 1.6 self-version/digest/link; advertise 1.6 during T1; leave 1.5 default during T2; keep `_BASELINE_REF` at v5.17.0; change `_RELEASE_VERSION`; retain any root README/current-guide 1.5 reference; or alter an unrelated byte in any of the three newly claimed files. Each oracle must fail for the intended reason before restoration.
- **Package layer:** after projection generation/bootstrap, run the focused contract and the five package validators: `validate-packages`, `validate-graph --require-all-manifests`, `generate-package-schemas --check`, `sync-payload-projection --check`, and `render-catalog --check`.
- **Documentation/static layer:** run scoped new-file and Git-tracked Prettier/markdownlint checks, `git diff --check`, rexec Ruff/BasedPyright/package validation, and candidate-wheel `project-standards validate` after T2 dogfood activation. Git/index-selected Markdown checks remain direct-local. The final name-status/diff census requires exactly fourteen paths: the revision-4 eleven-path candidate plus `tests/package_contract/test_current_catalog_activation.py`, `README.md`, and `tests/test_adopt_dogfood.py`. Within the new claims, permit only `_BASELINE_REF = "v5.18.0"` with `_RELEASE_VERSION = "5.18.0"` unchanged, the four root ADR-current reference lines and adjoining current-package prose, and `("adr", "1.6")`; reject every other path or unrelated byte.
- **Repository layer:** T1 runs one fast `PYTHONPATH="$PWD/build/wheel-runtime" scripts/verify.sh` direct-local after its last candidate content change. T2 reruns bootstrap after activation/reconciliation and runs one final `PYTHONPATH="$PWD/build/wheel-runtime" scripts/verify.sh --full` direct-local after the last content change. Both gates require local Git history for the issue-regression ledger; neither substitutes for task-level behavior proof.
- **Evidence:** repeatable output is ephemeral under the generated execution directory. Retain the revision-5 full-gate receipt: one direct-local candidate-PYTHONPATH `--full` invocation, exit 1 in 77:02; statics exit 0 in 1:00; ordinary exit 1 with `8 failed, 4,935 passed, 146 deselected in 1958.58s` after 32:41; compatibility exit 0 with 141 passed in 2559.77s after 42:40; performance exit 0 with 5 passed/5,084 deselected in 38.15s after 0:39; coverage-report exit 0 in 0:02 with 90% total coverage. Preserve the eleven-path/no-extra-work receipt and binary-diff digest above. Each checkpoint records tag names, corpus counts/edge counts, aggregate digest, exact commands, exit codes, and concise result summaries; no secret or private downstream content is retained.
- **Late failure:** revision 2 blocked T2 before apply on the catalog-snapshot claim omission; revision 3 resumed, reached an exact reconciliation fixed point, then blocked on the predecessor-test claim after the focused `31 passed, 2 failed` receipt; revision 4 reached the exact staged eleven-path candidate, then the final full gate exposed only the three current-release consumer omissions recorded above. Revision 5 resumes from that preserved candidate and authorizes no other correction. Any later failure blocks the owning task, appends a correction task with `corrects`/`discovered_from`, completes its checkpoint, and reruns the failed focused proof plus the applicable fast/full final gate.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Build and prove the unadvertised ADR 1.6 candidate | active | brownfield-behavior | P1 | None | REQ-001–REQ-007, REQ-009 | PV-T1-001 | no / T2 shared aggregate paths |
| T2 | Activate, dogfood, and fully qualify ADR 1.6 | active | configuration | P2 | T1 | REQ-001, REQ-005–REQ-006, REQ-008–REQ-009 | PV-T2-001 | no / T1 shared aggregate paths |

## 9. Implementation Tasks

### Phase P1: Unadvertised Provider and Package Candidate

#### T1: Build and prove the unadvertised ADR 1.6 candidate

- **disposition:** active
- **outcome:** One complete exact-selectable ADR 1.6 candidate adds the independent default-off amendment guard, passes focused behavior/released-corpus/package proof, preserves ADR 1.5 exactly, and remains unadvertised with no self-host or release activation.
- **work_type:** brownfield-behavior
- **checkpoint:** one green candidate commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-009]
- **proof:** [PV-T1-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#163, repo:standards/adr/versions/1.5/README.md#amendment-workflow, repo:standards/adr/versions/1.5/providers/adr.py::run_validate, repo:standards/adr/versions/1.5/config.schema.json, repo:standards/adr/versions/1.5/payload.toml, repo:tests/package_contract/test_adr_1_5.py::test_adr_1_5__successor__preserves_1_4_and_indexes_complete_payload, repo:src/project_standards/control_plane/provider_inputs.py::_frontmatter_input, repo:docs/handoff/deployed.md]
- **consumes:** [ADR 1.5 immutable payload and relationship contract, existing complete document-snapshot seam, post-#159/#160/#161 corpus, v5.17.0 and v5.18.0 tag corpora]
- **produces:** [adr-amendment-validation-v1, complete unadvertised adr-1.6-candidate, adr-1.6-released-corpus-compatibility-v1]
- **preserves:** [all 1.5 and earlier payload bytes/modes/digests, existing provider findings/order/section semantics, optional fields, contract version, legacy settings and artifact ownership, catalog/default/root/config/lock/release state]
- **invariants:** [one immutable snapshot input, no filesystem or prose inference, independent booleans, one finding per failed directed relationship obligation, relationship-specific hints, missing target uses one-way code, no new output schema or migration edge, 1.6 unadvertised]
- **executor_discretion:** [private index/helper names, stable textual identity serialization, fixture organization, and single-pass implementation details that preserve the binding finding semantics]
- **files:** [`standards/adr/versions/1.6/**` (create complete payload; owner T1), `src/project_standards/payloads/adr/1.6/**` (create generated relative file symlinks; owner T1), `standards/adr/standard.toml` (modify family index/digest; owner T1), `tests/package_contract/test_adr_1_6.py` (create then contribute behavior/non-activation proof; owner T2), `standards/catalog.md` (regenerate unadvertised facts; owner T2), `CHANGELOG.md` (modify Unreleased entry; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** [T2]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** if the candidate cannot preserve default behavior, 1.5 bytes, provider purity, or released-corpus compatibility, remove only uncommitted 1.6/projection additions and restore shared aggregate files to the T1 base; do not advertise, weaken the oracle, edit a tag/predecessor, or checkpoint a partial payload
- **acceptance:** PV-T1-001 proves correct-reason RED, both stable relationship finding families and silent controls, exact independent option behavior, accurate hints/order, complete 1.6 identities/digests/projection/docs/migration, exact 1.5 preservation, zero new findings over compatible 1.5 and tagged/current corpora, unadvertised/default-state preservation, and green package/Markdown/static/fast gates
- **sub-tasks:**
  - **T1.1 CHARACTERIZE** — pin the 1.5 tree/digest/modes, effective options, provider section/path/parse outputs, migration/artifact contracts, current catalog/root/self-host state, and post-#159/#160/#161 corpus counts/edges; verify tag availability and base ancestry direct-local.
  - **T1.2 Verify Baseline** — run the existing ADR 1.5 focused contract and a direct-local v5.17.0/v5.18.0 corpus inventory; confirm the baseline is green and do not reinterpret a pre-existing finding as candidate behavior.
  - **T1.3 SCAFFOLD** — copy 1.5 to a structurally coherent unadvertised 1.6 candidate, update only identity/config/manifest facts needed to invoke the unchanged provider with `validate_amendments`, and add the focused test shell; do not implement relationship semantics yet.
  - **T1.4 RED** — add focused cases for forward and reverse one-way edges, a missing target, and a superseded target plus option-independence/default controls.
  - **T1.5 Verify RED** — through rexec run the focused cases and confirm they fail because the unchanged provider emits neither required stable code; import, schema, digest, fixture, environment, or section failures do not establish RED.
  - **T1.6 GREEN** — implement the two checks inside the 1.6 provider, parameterize repair hints, finish docs/config/manifest/self-version changes, preserve unchanged predecessor bytes, generate relative source projection and catalog facts, and record the Unreleased entry.
  - **T1.7 Verify GREEN** — through rexec run the complete focused test matrix, predecessor regression, remote Ruff/BasedPyright, and five package validators; direct-local, extract the two tagged corpora to a bounded temporary directory and invoke the candidate with default and opt-in configurations, recording counts and zero-finding results before deleting temporary content.
  - **T1.8 REFACTOR** — assess one-pass parsing/indexing and finding construction for duplication without widening validation scope; keep every focused result exact.
  - **T1.9 Verify Task** — rerun remote bootstrap after final payload bytes; execute PV-T1-001 with focused/package/static work on rexec and corpus/Git/index checks direct-local; run scoped Markdown, `git diff --check`, authorized name-status/diff inspection, and one direct-local candidate-PYTHONPATH fast repository gate; validate this plan and commit with required trailers.

### Phase P2: Catalog Activation and Final Corpus Qualification

#### T2: Activate, dogfood, and fully qualify ADR 1.6

- **disposition:** active
- **outcome:** After the release-wide ADR corpus freeze, ADR 1.6 is Catalog 5 default/current family authority, this repository explicitly dogfoods amendment validation, its lock and managed state are reconciled, the frozen corpus has zero amendment findings, and the final full repository gate is green without publishing the release.
- **work_type:** configuration
- **checkpoint:** one green activation/final-qualification commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T1]
- **dependency_reason:** consumes T1's complete `adr-amendment-validation-v1` and unadvertised 1.6 payload; an external entry gate additionally consumes the release coordinator's settled ADR-writing set and completed corpus-correction T4 checkpoint before any activation write
- **requirements:** [REQ-001, REQ-005, REQ-006, REQ-008, REQ-009]
- **proof:** [PV-T2-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#163, repo:docs/plans/2026-08-10-v519-adr-corpus-corrections-plan.md#phase-p4-corpus-wide-link-and-path-reconciliation, repo:catalogs/5.toml, repo:.standards/config.toml, repo:.standards/catalog.toml, repo:.standards/lock.toml, repo:standards/adr/README.md, repo:standards/README.md, repo:tests/package_contract/test_adr_1_5.py::test_adr_1_5__catalog_role__selects_the_successor_as_default, repo:tests/package_contract/test_adr_1_5.py::test_adr_1_5__mutable_navigation__names_the_new_authority, repo:tests/package_contract/test_current_catalog_activation.py::_BASELINE_REF, repo:README.md, repo:tests/test_adopt_dogfood.py::test_current_adoption_guides_use_v5_packages_not_v1_fragments]
- **consumes:** [complete unadvertised adr-1.6-candidate, adr-amendment-validation-v1, adr-1.6-released-corpus-compatibility-v1, release-wide-v5.19-adr-corpus-freeze-v1, corpus-correction T4 checkpoint, current Catalog 5 source and tracked consumer snapshot, current self-host state]
- **produces:** [catalog-5-adr-1.6-activation-v1, self-hosted-adr-amendment-guard-v1, adr-1.6-final-qualification-checkpoint-v1]
- **preserves:** [all 1.6 payload bytes from T1, all 1.5 and earlier bytes/digests/roles except 1.5 default-to-retained role, ADR 1.5 provider/payload/compatibility/predecessor test behavior outside the two activation assertions, `_RELEASE_VERSION = "5.18.0"` and every release-activation assertion except the baseline constant, all README bytes outside the four ADR-current reference lines and adjoining current-package prose, all dogfood parameters/assertions except the ADR current-guide version, unrelated source-catalog/config/tracked-catalog-snapshot/lock/test/managed bytes, consumer-authored ADR/scaffold bytes, release version/tags/GitHub state]
- **invariants:** [external corpus freeze before writes, 1.6 default and 1.5 retained atomically, ADR 1.5 remains exact-selectable while mutable current/default navigation points to 1.6, `version = "latest"` plus explicit `validate_amendments = true`, reconcile only after candidate runtime contains 1.6, `.standards/catalog.toml` equals the candidate-rendered Catalog 5 snapshot and changes only for activation/provenance, v5.18.0 is the fixed activation baseline and release version so ADR 1.6 is the sole post-baseline target, root README and dogfood current-guide references point to 1.6, create-only scaffold unchanged, zero amendment findings, second reconcile no-op, final full gate last]
- **executor_discretion:** [concise mutable navigation wording and ordering of read-only prechecks, provided every named authority and preservation assertion remains exact]
- **files:** [`catalogs/5.toml` (modify ADR roles/1.6 entry; owner T2), `standards/adr/README.md` (modify current authority; owner T2), `standards/adr/adopt.md` (modify current adoption; owner T2), `standards/adr/agent-summary.md` (modify current summary; owner T2), `standards/README.md` (modify ADR table row; owner T2), `.standards/config.toml` (modify ADR option only; owner T2), `.standards/catalog.toml` (reconcile only the candidate-rendered Catalog 5 snapshot/provenance required by ADR 1.6 activation; owner T2), `.standards/lock.toml` (reconcile generated selection/config/inventory; owner T2), `standards/catalog.md` (regenerate activated facts; owner T2), `tests/package_contract/test_adr_1_6.py` (modify activation assertions; owner T2), `tests/package_contract/test_adr_1_5.py` (modify only predecessor activation assertions: 1.5 retained/exact-selectable and mutable current/default navigation on 1.6; owner T2), `tests/package_contract/test_current_catalog_activation.py` (modify only `_BASELINE_REF` from v5.17.0 to v5.18.0; owner T2), `README.md` (modify only four current ADR reference lines and adjoining current-package prose from 1.5 to 1.6; owner T2), `tests/test_adopt_dogfood.py` (modify only current-guide parameter `("adr", "1.5")` to `("adr", "1.6")`; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** [T1]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** resume only after revision 5 is active, the original eleven staged paths are byte-exact, and the complete failed full-gate receipt is retained; add only the three newly claimed deltas, then rerun focused checks before restarting the full gate. If the ordinary failures do not collapse from the recorded six baseline, one README, and one dogfood cause, stop rather than broadening claims. If pre-commit activation, reconciliation, corpus, focused, or full-gate proof fails, restore the complete fourteen-path activation set together to the T1 checkpoint or forward-repair under an appended correction task—never change `_RELEASE_VERSION`, another release assertion, predecessor/provider behavior, an unrelated README/dogfood byte, or frozen ADR merely to silence proof
- **acceptance:** PV-T2-001 proves the external freeze/checkpoint preceded activation; exactly 1.6 is default and 1.5 retained; family/self-host/lock/catalog facts agree; `validate_amendments = true` is effective; reconcile repeats as a no-op; current and tagged corpora pass; scaffold and unrelated state remain exact; and all package, candidate-wheel, Markdown/static, and final rexec full gates pass
- **sub-tasks:**
  - **T2.1 PRECHECK** — on recovery, verify revision 5 owns all fourteen paths; retain the exact ten-path fixed-point and `31 passed, 2 failed` focused receipts plus the 77:02 full-gate lane/count/coverage receipt; and prove the original eleven staged paths remain byte-exact with no out-of-claim edit/rerun/commit, no unstaged/untracked path, green diff check, binary-diff SHA-256 `8de13d82034a50d7a211b0b3ee69f7667a35f3afbad2e16e59572387c22f1b4a`, and ADR aggregate `sha256:12b9490be7cf3284bfb7f510b03b2cd555ab7c57f0a7628c9f95c659c241ba42`; obtain the release coordinator's final ADR-writing-set and checkpoint inventory; verify the corpus-corrections T4 checkpoint and T1 checkpoint/digest, no concurrent owner of shared activation files, and a current candidate runtime containing 1.6.
  - **T2.2 PROVE ABSENCE** — direct-local, show Catalog 5/latest/root/self-host still select 1.5, 1.6 is unadvertised, and amendment validation is not effective; through rexec prove the frozen corpus itself passes the T1 provider when explicitly enabled.
  - **T2.3 APPLY** — preserve the staged eleven-path activation candidate; change only `_BASELINE_REF` to v5.18.0, the four root README ADR-current reference lines plus adjoining current-package prose to 1.6, and the dogfood ADR guide parameter to 1.6. Keep `_RELEASE_VERSION = "5.18.0"` and every unrelated byte exact.
  - **T2.4 VERIFY** — inspect resolved config/tracked catalog snapshot/lock and provider request; rerun the exact focused ADR 1.6/1.5 command and require all 33 tests to pass, with 1.5 retained/exact-selectable and mutable current/default navigation on 1.6; prove the activation target set contains only ADR 1.6 relative to v5.18.0, all root README current ADR links/prose resolve to 1.6, and the dogfood current-guide matrix selects 1.6; require zero frozen-corpus findings, exact catalog/family identities, a candidate-rendered snapshot limited to activation/provenance facts, unchanged scaffold/predecessor behavior/unrelated release/README/dogfood/config/managed bytes, and green package/documentation checks.
  - **T2.5 PROVE IDEMPOTENCY** — preview and reapply reconciliation using the same candidate runtime; require no plan, tracked catalog target, lock, or managed-byte change and rerun the direct-local tagged-corpus compatibility procedure.
  - **T2.6 Verify Task** — rerun remote bootstrap after the three final content corrections; execute PV-T2-001 with the focused ADR 1.6/1.5/current-catalog/dogfood tests, all five package validators, and Ruff/BasedPyright on rexec, candidate-wheel `project-standards validate`, permitted direct-local Git-tracked Markdown/diff/tag/corpus checks, and one final direct-local `PYTHONPATH="$PWD/build/wheel-runtime" scripts/verify.sh --full`; inspect the exact fourteen-path authorized diff and field-check all bounded deltas, validate this plan/checkpoint, and commit with required trailers.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 verifies the required #159/#160/#161 ancestors and current corpus, then lands the complete 1.6 package as unadvertised without touching activation/self-host state.
2. The release coordinator completes the v5.19 ADR-writing set and the corpus-corrections plan's T4 checkpoint. T2 blocks until both the declared set and checkpoint inventory are available.
3. Revision 4 reaches the exact staged eleven-path activation candidate and begins the direct-local full gate; its ordinary lane exposes only the three stale current-release consumers recorded by revision 5, while no out-of-claim edit, rerun, or commit follows.
4. After revision 5 activates, T2 preserves those eleven paths, applies only the baseline/README/dogfood deltas, proves the exact fourteen-path surface, reruns the bounded focused checks, and then restarts the final full gate direct-local.
5. The parent v5.19 release workflow may consume T2's validated checkpoint for release metadata, hosted CI, publication, and synchronized issue closure; this plan grants no such action itself.

### 10.2 Package and Configuration Transition

- Required: yes; immutable package successor plus Catalog 5/default and producer-self-host transition.
- Compatibility period: T1 keeps 1.5 default and 1.6 unadvertised. T2 keeps 1.5 retained/exact-selectable while making 1.6 default; a consumer without the new key resolves `false` and retains its prior validation result.
- Idempotency: schema defaults are deterministic; package projection, tracked consumer-catalog snapshot, and human catalog rendering are generated fixed points; reconciliation is run twice and the second preview/apply must produce no change.
- Point of no return: external release publication, which this plan does not perform. Before publication, restore the complete T2 activation checkpoint or append a forward correction.
- Rollback / forward repair: before the T2 checkpoint, restore all fourteen activation/config/tracked-catalog-snapshot/lock/navigation/current-release assertion files together to T1; after a checkpoint, preserve history and append a correction. Never edit ADR 1.5 payload/provider behavior, `_RELEASE_VERSION`, unrelated README/dogfood assertions, immutable tags, or consumer ADRs to manufacture green.
- Recovery proof: PV-T1-001 preserves predecessor/default compatibility and PV-T2-001 proves the exact ten-path fixed point, bounded predecessor-test correction, preserved staged eleven-path candidate, three full-gate-discovered corrections, exact fourteen-path result, pre-activation corpus validity, atomic source-catalog/config/tracked-snapshot/lock agreement, idempotent reconciliation, and final qualification.

### 10.3 Late Failure and Correction

A failure in T1 prevents candidate completion and activation. Revision 2 left the valid unadvertised candidate and seven claimed T2 authored edits intact while T2 blocked before reconciliation apply; revision 3 authorized the sole previewed tracked-catalog target and reached an exact ten-path fixed point; revision 4 authorized the two stale predecessor activation assertions and reached the exact staged eleven-path candidate; revision 5 authorizes only the catalog-baseline, root README, and dogfood current-guide deltas exposed by the full gate's eight ordinary failures. A final corpus or integration failure creates an append-only correction task owned by the responsible surface, with `corrects` and `discovered_from`; after its checkpoint, rerun the failed provider/package proof and the direct-local full T2 gate. An authority change to relationship semantics returns to issue/ADR ownership through a plan revision rather than silently changing stable codes or option defaults.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | One directed mismatch is double-reported or attached to the wrong record. | medium | medium | Define one finding per missing directed obligation; assert exact paths/IDs/order for forward, reverse, and dangling controls. | provider owner / T1 |
| R-002 | The new check accidentally rides `require_sections` and turns existing opted-in consumers red. | medium | high | Separate option/default contract, four option-combination tests, tagged-corpus default proof, and activation only after opt-in corpus proof. | package owner / T1–T2 |
| R-003 | A relationship hint tells the user to replace an ADR from a template. | medium | medium | Parameterize hints and assert relationship-specific repair instructions in focused tests. | provider owner / T1 |
| R-004 | Candidate identity/digests/projection drift, an accidental catalog row advertises 1.6 early, or predecessor tests continue pinning the pre-activation default/navigation state. | low | high | Exact predecessor/delta and non-activation controls plus five package validators and generated catalog check; after T2 activation, update only the predecessor activation expectations and rerun both focused contracts. | package owner / T1–T2 |
| R-005 | The corpus changes after measurement and activation enforces against a stale population. | medium | high | External final writing-set declaration and corpus-corrections T4 checkpoint are hard T2 entry gates; rerun the corpus proof immediately before activation. | release coordinator / T2 |
| R-006 | Git-dependent released-corpus proof is mistakenly offloaded and audits an empty worker history. | low | high | Keep tag/ancestry/archive commands direct-local, verify tag object availability, and use rexec only after corpus bytes are materialized or for non-Git checks. | verifier / T1–T2 |
| R-007 | Activation mutates the create-only scaffold or unrelated managed state. | low | high | Snapshot digests/name-status before reconcile, authorize only the candidate-rendered `.standards/catalog.toml` delta plus existing exact claims, rerun no-op reconciliation, and fail on any extra path or unrelated snapshot byte. | activation owner / T2 |
| R-008 | Broadly updating release, README, or dogfood assertions hides a real regression or rewrites unrelated current-package truth. | medium | high | Authorize one baseline constant, four ADR-current README lines plus adjoining package prose, and one ADR guide parameter; preserve `_RELEASE_VERSION` and mechanically reject every other byte/path. | activation owner / T2 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | The complete ADR corpus continues to arrive in one `snapshots.documents` call. | If the control-plane contract changes before T1, stop and revise the plan; do not add provider filesystem access. |
| A-002 | v5.17.0 and v5.18.0 tags remain locally available and immutable. | Fetch/verify tags only under separately authorized repository workflow; if unavailable, block released-corpus proof rather than substitute current files. |
| A-003 | The final v5.19 ADR-writing set can be frozen before T2. | T1 may complete unadvertised; T2 remains blocked without weakening or sampling the final corpus gate. |

### 11.3 Open Questions

None.

## 12. Final Verification

- Every REQ-001–REQ-009 row maps to a completed owning task and passing Appendix B proof; checkpoint trailers validate against revision 1 and the exact task-definition digest.
- `validate_amendments` resolves false by default, composes independently with `require_sections`, and is true in the final repository effective config/lock only after T2.
- Exact forward/reverse/dangling/superseded negative controls emit the two stable codes with deterministic actionable fields; absent/empty/valid controls and existing path/parse/section cases remain exact.
- ADR 1.6 identities, aggregate digest, resources, schemas, legacy route, artifact, projection, docs, family index, catalog, and changelog agree; every ADR 1.5 and earlier byte/mode/digest remains exact.
- The v5.17.0 and v5.18.0 tagged corpora pass default and opt-in compatibility procedures, and the final frozen v5.19 corpus produces zero amendment findings under the activated option.
- Catalog 5 marks 1.6 default and 1.5 retained/exact-selectable; mutable family, standards, root README, and dogfood current-guide navigation names 1.6; the predecessor activation assertions agree without changing ADR 1.5 provider/payload behavior; `_BASELINE_REF` and `_RELEASE_VERSION` both equal v5.18.0/5.18.0 respectively so ADR 1.6 is the sole post-baseline target; `.standards` config/tracked Catalog 5 snapshot/lock resolves 1.6 and both enabled checks; the snapshot contains only candidate-rendered activation/provenance deltas, and the existing create-only scaffold is byte-identical.
- The five package validators, candidate-wheel project validation, focused/provider/predecessor tests, scoped and Git-tracked Markdown checks, Ruff, BasedPyright, `git diff --check`, T1 fast gate, and T2 final full gate all pass in the declared locations: synchronized-tree-compatible focused/package/static checks on rexec v0.2, and tag/corpus/Git/index plus both candidate-PYTHONPATH repository gates direct-local.
- Reconciliation's second preview/apply is a no-op, the focused ADR 1.6/1.5 command reports 33 passed, the final diff contains exactly fourteen plan-authorized paths and only the bounded tracked-snapshot, predecessor, baseline, README, and dogfood deltas, and no unrelated config/catalog/test/scaffold byte, release metadata/tag/GitHub/handoff/publication mutation, or unresolved correction remains.

## 13. Close-out

- **Completed:** record T1's unadvertised and T2's activated checkpoint commits, the final ADR 1.6 aggregate digest, and the final effective config/lock facts.
- **Decisions / deviations harvested:** retain D-001–D-008 and record any approved deviation in the owning issue/plan before execution state is removed; do not rewrite the issue's behavior to match an implementation shortcut.
- **Risks closed / accepted:** close R-001–R-008 from focused/package/corpus/full-gate proof or file a bounded follow-up owned outside release publication.
- **Deferred/discovered work filed:** prose/note validation, unrelated metadata-shape or duplicate-ID behavior, arbitrary downstream corpus opt-in, release publication, and GitHub closure remain with their named owners or new issues.
- **Source/ADR/handoff reconciliation:** update versioned and mutable package docs within T1/T2; the parent release closeout owns status, handoff, release evidence, and issue terminal state after publication.
- **Scratch teardown:** harvest task/checkpoint/digest/tag-corpus summaries; remove only this plan's generated execution/authoring state after no irreplaceable evidence remains.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `adr-amendment-validation-v1` | T1 | T2; ADR consumers | `require_sections` alone gates all parsing. | `validate_amendments: bool = false`; when true, both reciprocal directions and superseded targets are checked over one snapshot corpus. | `ADR-AMEND-ONEWAY`, `ADR-AMEND-SUPERSEDED`; one deterministic error per failed directed obligation. | Independent from sections; optional fields; no prose/filesystem access; existing findings/order exact. | issue #163; ADR 1.5 provider/config |
| `adr-1.6-package-v1` | T1 | T2; Catalog 5 | 1.5 complete/default. | 1.6 complete/unadvertised, then default; 1.5 retained. | Any digest/schema/projection/legacy/artifact mismatch blocks. | 1.5 byte/mode/digest immutable; `contract_version` 1.0; no package migration edge. | V2 package contract; issue #163 |
| `adr-1.6-released-corpus-compatibility-v1` | T1 | T2; release workflow | Issue measurement, no executable candidate proof. | Tagged v5.17/v5.18 and current/frozen corpora pass default and opt-in procedures with recorded counts. | Missing tag, nonzero new/amendment finding, or stale corpus blocks. | Git tag reads local only; default-off is the general consumer compatibility guarantee. | issue #163; deployed release record |
| `catalog-5-adr-1.6-activation-v1` | T2 | parent v5.19 release | 1.5 default/root/self-host with matching committed Catalog 5 snapshot and lock; current-release assertions still use the pre-1.6 baseline/navigation. | 1.6 default/root/self-host with both checks true; 1.5 retained; tracked snapshot and lock reconciled from the candidate runtime; v5.18.0 baseline and root/dogfood current references make 1.6 the sole successor target. | Missing corpus-freeze/T4 checkpoint, reconcile drift, extra path or unrelated snapshot/release/README/dogfood byte, or failed full gate blocks. | Atomic activation; `_RELEASE_VERSION`, create-only scaffold, and unrelated config/test/docs/managed bytes preserved; no publication authority. | request; corpus-corrections plan; Catalog 5; full-gate ordinary receipt |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-009 | T1 | direct provider, V2 package contract, tagged/current corpus compatibility, fast qualification | issue #163 acceptance; ADR 1.5 relationship rules; immutable 1.5 tree/digest; existing provider outputs; v5.17/v5.18 tag bytes | Run `tests/package_contract/test_adr_1_6.py`, 1.5 regression, five package validators, Ruff, and BasedPyright through rexec; direct-local extract/invoke both tags and run scoped/Git-tracked Markdown plus diff checks; run one direct-local `PYTHONPATH="$PWD/build/wheel-runtime" scripts/verify.sh`. | Exact stable findings and silent controls pass; 1.6 is complete/unadvertised; 1.5 and tagged/current compatible corpora remain green; all gates pass. | Remove either reciprocal side; use absent ID; supersede target; couple/default-enable option; restore generic hint; mutate 1.5; stale schema/digest/projection; advertise 1.6. Each focused oracle fails for the intended reason. | bootstrapped rexec worker for synchronized-tree-compatible CPU work; authoritative local Git checkout for tag/diff/fast-gate checks | ephemeral |
| PV-T2-001 | REQ-001, REQ-005, REQ-006, REQ-008, REQ-009 | T2 | configuration | T1 checkpoint/digest; release coordinator's final writing-set and corpus-correction T4 checkpoint; Catalog 5 source and tracked consumer snapshot; ADR 1.5 predecessor contract; candidate-wheel provider; immutable tag bytes; full-gate failure partition | Confirm the staged eleven-path candidate and complete failed-gate receipt; change only `_BASELINE_REF`, four root ADR-current lines plus adjoining prose, and the dogfood ADR parameter; require focused ADR/current-catalog/dogfood checks green; field-check the exact fourteen-path diff; run package/static checks through rexec and candidate-wheel/Markdown checks in their declared locations; direct-local rerun tags/diff and `PYTHONPATH="$PWD/build/wheel-runtime" scripts/verify.sh --full`. | 1.6 default/current/self-hosted and the sole post-v5.18.0 activation target; 1.5 retained/exact-selectable with provider/predecessor behavior exact; root README/dogfood navigation names 1.6; source catalog, tracked snapshot, config, lock, and mutable navigation agree; both checks effective; frozen/tagged corpora zero; scaffold/unrelated state exact; second reconcile no-op; all gates pass. | Keep any of the eight stale expectations; change `_RELEASE_VERSION`, another release assertion, unrelated README/dogfood byte, or ADR 1.5 provider/payload behavior; omit freeze/option/lock/root/snapshot update; add an unclaimed path; inject one-way/superseded edge; mutate scaffold/unrelated config; stale runtime; break no-op. Each gate blocks before checkpoint. | authoritative local checkout for activation/Git/full gate; bootstrapped rexec worker for synchronized-tree-compatible CPU checks | ephemeral |

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Amendment prose, note placement, or semantic-scope validation | Issue #163 and ADR 1.5 explicitly exclude prose inference; machine enforcement would require new approved semantics. | A separately accepted issue/spec defines an objective non-prose-inference contract. |
| Metadata field-shape and duplicate-ID findings in the ADR provider | Markdown Frontmatter/reference validation owns these concerns; adding a second schema/taxonomy is outside the two-check outcome. | Evidence shows the companion boundary cannot protect a supported ADR-only workflow and an owner approves new behavior. |
| Arbitrary downstream repository opt-in and corpus repair | The option is intentionally consumer-controlled and this plan has no authority over private consumer ADRs. | A consumer enables `validate_amendments` and files a concrete compatibility defect or requests migration assistance. |
| v5.19 release publication and issue #163 closure | This plan ends at an activated, fully qualified local checkpoint. | Parent release workflow verifies hosted CI/assets/tag/remote parity and synchronizes terminal GitHub state. |
