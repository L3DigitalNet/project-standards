---
schema_version: '1.1'
id: 'decision-si7ids-project-spec-conformance-plan-input'
title: 'Project Specification conformance linting design'
description: 'Approved design for successor-only Project Specification conformance linting that makes shared boilerplate and mandatory phrasing drift visible.'
doc_type: 'decision'
status: 'active'
created: '2026-08-10'
updated: '2026-08-10'
tags:
  - 'standard'
  - 'validation'
aliases: []
related: []
---

# Project Specification conformance linting design

## Status and provenance

- Status: `approved`
- Operation: `create`
- Decision owner: user
- Created and approved: `2026-08-10`
- Revision: initial approved design
- Prior design brief: none
- Working-state source: `.project-pipeline/project-spec-conformance/design-discovery/` (removed after promotion)

This brief is the approved design authority for the #62 successor payload. It preserves every Project Specification 1.8 payload byte and its behavior. The successor payload is the only activation point for this design.

## Problem and intended outcome

Project Specification tooling validates structure but does not verify its documented shared-boilerplate guarantee. Issue #62 records five recurring prose-divergence classes across nine otherwise valid specifications and 196 mandatory requirement rows that do not use the prescribed wording. The result is a structurally green document that can silently diverge from the canonical contract.

The outcome is profile-aware conformance linting that makes that divergence visible immediately, allows already-adopted consumers to repair without an ordinary-lint breaking change, and gives downstream specification authoring a complete behavior contract without requiring it to invent policy.

## Current context

- Version 1.8 documents shared boilerplate as an interchangeability guarantee but explicitly says that it is not machine-checked.
- The Light, Standard, and Full profiles share exact Lifecycle and Quality prose. Their Appendix A, B, and D blocks are profile-specific, while each is structurally locatable from its selected profile template.
- Existing lint findings are warnings: ordinary lint exits successfully with warnings, while `--strict` exits 1 when warnings are present. Validation errors already exit 1.
- Existing parsing, section slicing, template-block reconciliation, and finding fields support the required comparison and reporting boundaries. There is no existing conformance waiver, suppression, frontmatter key, or per-rule configuration surface.
- The current roadmap groups #62 with #55 in the approved feature phase, and separately places #143 in the Project Specification conformance release grouping. If that scheduling relationship remains current at release planning, one successor Project Specification payload cut includes both issues. #143 does not change this design's behavior.

## Scope

### In scope

- Successor-only checks for the documented shared-boilerplate surfaces and mandatory requirement phrasing covered by #62.
- Exact comparison semantics, diagnostic identity and loci, warning-first compatibility, strict behavior, clean-run coverage evidence, and the valid-tailoring boundary.
- Successor tooling notes and adoption guidance that identify the checked surfaces, repair them, describe strict-mode impact, and disclose additive JSON compatibility.
- Immutable predecessor preservation.

### Non-goals

- Changing Project Specification 1.8 bytes or behavior.
- A generalized lint severity or configuration framework.
- Fuzzy matching, automatic prose repair, a new parser, and inline document suppression syntax.
- Treating #143 as conformance-lint behavior.

### Deferred considerations

- Per-rule suppression or configuration, unless an approved valid-tailoring case later requires an exception inside a checked canonical surface.
- Unconditional validation errors, automatic repair, and promotion of warning severity after ecosystem evidence supports a separately approved successor contract.

## Constraints, assumptions, and agent-applied defaults

### Constraints

- The comparison is profile-aware: a document is compared only with the immutable successor template for its selected profile.
- Lifecycle and Quality are byte-exact canonical prose. Appendix A, B, and D are first isolated structurally, then compared with the selected profile's canonical block.
- Each mandatory requirement row is independently checked to ensure its normative statement begins with the exact phrase `The system shall`.
- Findings remain warnings in ordinary lint, and existing strict lint makes any warning exit 1.
- The successor must not retain tooling notes that say these conformance checks are absent.

### Assumptions

- The documented shared-boilerplate guarantee means its checked surfaces are not ordinary tailoring points.
- A consumer that treats JSON output as an exact key set may need to accept the successor's additive `checks` field.

### Agent-applied defaults

- Reuse the existing document parser, section slicing, template-block reconciliation, finding schema, and strict-mode boundary rather than introducing a parallel parser or severity model.

## Selected design

The successor Project Specification payload adds two profile-aware lint families:

- `SL-BOILERPLATE` reports drift in shared canonical prose. Its `locus` identifies the affected canonical surface: Lifecycle, Quality, or the structurally isolated Appendix A, B, or D block.
- `SL-REQUIREMENT-PHRASING` reports a mandatory requirement row whose normative statement does not begin with `The system shall`. Its `locus` identifies the requirement ID, and `line` identifies the physical row.

Both families are warnings in ordinary lint. They become an exit-1 condition through the existing `--strict` behavior; they are not validation errors. There is no opt-in mode, waiver, suppression, per-rule configuration, fuzzy comparison, or automatic repair.

Lifecycle and Quality use byte-exact comparison because their shared content is identical across profiles. Appendix A, B, and D are not compared as a whole-document text fragment: the lint first isolates the appropriate lettered block in the document and then compares it with the corresponding block in the selected profile's immutable successor template. This preserves the profile-specific appendix content and titles while retaining exact canonical comparison.

A legitimately tailored document may change only content that the Standard already permits it to tailor outside the checked surfaces. It remains conformant when those changes leave every checked canonical surface and mandatory phrase intact. No document-local exception mechanism weakens that boundary.

Clean human output explicitly names both executed check families. Successor JSON adds, for each document, `checks: ["shared-boilerplate", "mandatory-phrasing"]`. The field is additive; existing consumers of the other JSON fields remain compatible unless they reject unknown keys.

Successor adoption guidance names the exact repair surfaces: restore canonical Lifecycle and Quality prose, restore the selected profile's Appendix A, B, or D block, and use `The system shall` in mandatory requirement rows. It also explains that ordinary lint emits warnings while strict lint exits 1 until repairs are made.

## Migration and compatibility

Existing consumers receive visible warning findings on ordinary lint rather than an unconditional failure. Strict consumers can begin failing when their documents diverge; they repair the named surface or mandatory row to restore a clean result. This is an intentional advisory-to-strict rollout using the established lint contract, not a new severity mode.

The JSON `checks` array is additive and makes successful execution observable even when there are no findings. Consumers that parse only known fields are unaffected; consumers that require an exact JSON key set need a compatible parser update. Human clean output also changes to name both check families.

Project Specification 1.8 remains exactly selectable and unchanged. The future payload cut may co-deliver #143 only if release planning still groups it with this successor; that release choice does not expand the #62 behavior defined here.

## Consequential decisions

### D1: Advisory-to-strict conformance rollout

- Status: `approved` (user, 2026-08-10)
- Decision: add profile-aware conformance findings as ordinary-lint warnings and reuse `--strict` for exit 1.
- Context and evidence: existing lint already has the required warning/strict contract, while existing consumers demonstrably diverge. Immediate validation errors would be a breaking successor upgrade.
- Agent recommendation: advisory-to-strict, to make divergence visible without hiding it behind a new opt-in surface or breaking ordinary lint.
- User disposition: approved the recommended advisory-to-strict option.
- Rationale and consequences: all consumers see drift; strict consumers enforce it and may need repair before returning clean.
- Reversibility and residual risk: a later successor can promote mature findings after ecosystem evidence. Until then, overly broad boundaries could create warning noise, so comparison remains narrow and profile-aware.
- Reopen when: an approved change to the existing strict-lint contract or to existing-consumer compatibility requires a different rollout.

### D2: Canonical tailoring boundary

- Status: `approved` (user, 2026-08-10)
- Decision: no document-local waiver exists for either lint family. Legitimate tailoring changes only Standard-sanctioned surrounding content while retaining checked canonical surfaces.
- Context and evidence: Version 1.8 names these surfaces shared boilerplate, and its only parseable exception syntax covers omission of whole conditional sections, not conformance exceptions.
- Agent recommendation: retain the canonical boundary because no approved valid exception exists inside a checked surface.
- User disposition: approved the recommended canonical-boundary option.
- Rationale and consequences: strict outcomes stay deterministic and the documented shared guarantee remains meaningful. A future valid exception requires an explicit successor contract.
- Reversibility and residual risk: adding an approved exception later is possible, but consumers cannot suppress a finding now merely because a local variation is preferred.
- Reopen when: the Project Specification Standard explicitly permits tailoring within a checked canonical surface.

### D3: Diagnostic families and clean-run coverage

- Status: `approved` (user, 2026-08-10)
- Decision: use `SL-BOILERPLATE` and `SL-REQUIREMENT-PHRASING`; use `locus` for surface or requirement identity and `line` for the physical mandatory-row location. Name both families in clean human output and add the two-entry `checks` array to successor JSON.
- Context and evidence: existing findings already provide `line` and `locus`, but existing clean human and JSON output cannot prove that either new check ran.
- Agent recommendation: two families, because shared-prose restoration and row-phrasing repair are distinct workflows and need stable, compact identity.
- User disposition: approved the recommended two-family design.
- Rationale and consequences: the public vocabulary stays bounded while successful check coverage becomes observable. Strict JSON consumers may need to accept the additive field.
- Reversibility and residual risk: these codes and the additive field become successor public contracts. A later independently configurable behavior would need a reviewed extension.
- Reopen when: a check family needs independent severity, suppression, or compatibility policy.

### Integrated design approval

- Status: `approved` (user, 2026-08-10)
- Decision: approve the assembled successor-only contract: immutable predecessor preservation, exact checked surfaces, advisory-to-strict rollout, canonical tailoring boundary, two finding families, and explicit human/JSON clean-run coverage.
- Context and evidence: all three consequential decisions were independently approved, and the integrated review reconciled the release boundary with additive JSON compatibility.
- User disposition: approved the integrated design as the minimum sufficient contract for #62.
- Reopen when: material evidence exposes a contradiction or a required behavior cannot satisfy the approved constraints.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Explicit opt-in conformance checks | It preserves a silent ordinary green result and introduces a second operating mode. |
| Unconditional validation errors | It breaks existing consumers before they can stage repairs. |
| Fuzzy prose matching | It makes a documented exact guarantee subjective and weakens deterministic repair. |
| Frontmatter waiver list or inline suppression | No valid exception exists; either introduces a lasting exception vocabulary and makes the shared guarantee voluntary. |
| Per-surface diagnostic codes | It creates a larger permanent taxonomy without independent policy needs. |
| One generic conformance code | It conflates block restoration and mandatory-row repair. |
| New parser | Existing parsing and reconciliation boundaries already locate the required surfaces. |
| Automatic repair | It risks rewriting authored prose and exceeds the evidence-backed need. |

## Complexity disposition

### Retained

- Profile-aware exact comparison and separate mandatory-phrasing diagnostics, because the observed divergence classes require both without fuzzy matching.
- Two stable codes plus human and JSON clean-run coverage, because clean execution must be visible without informational findings.

### Deferred

- Per-rule suppression or configuration, unconditional validation errors, automatic repair, and severity promotion. Reconsider each only when an approved valid exception, compatible enforcement policy, or ecosystem evidence demonstrates its need.

### Rejected

- Fuzzy matching, per-surface codes, one generic code, a second parser, and inline suppression syntax. Each adds permanent complexity without a current requirement.

### Preserved extension seams

- Existing finding codes, `locus`, strict mode, and additive JSON coverage can support a later, separately approved exception or policy change without generalizing this baseline.

## Unresolved decisions

### Blocking

None.

### Non-blocking

- Exact downstream diagnostic message wording may be finalized during specification authoring or implementation. It cannot change codes, loci, severity, checked surfaces, exit behavior, or repair guidance.

## Downstream impact

- The open-issue program's implementation phase consumes this approved brief. It must demonstrate canonical, divergent, legitimately tailored, and immutable predecessor documents under the approved behavior.
- The successor Project Specification payload requires synchronized tooling notes, templates, lint behavior, clean human output, JSON output, and adoption guidance. Those implementation surfaces are downstream work, not a decomposition in this brief.
- Release planning decides whether #143 shares the same successor payload cut; it must not alter the #62 conformance contract.

## Sources

| Source | Classification | Material finding |
| --- | --- | --- |
| `docs/plans/2026-08-01-open-issue-resolution-program-plan.md` | repository decision | The approved program assigns #62 a design boundary requiring explicit byte-exact, structural, advisory, and existing-consumer treatment. |
| `https://github.com/L3DigitalNet/project-standards/issues/62` | repository decision | Five shared-prose divergence classes and mandatory phrasing must become visible with negative coverage. |
| `standards/project-spec/versions/1.8/resources/tooling-notes.md` | current state | The documented shared-boilerplate guarantee is not machine-checked; profile and appendix distinctions define the comparison boundary. |
| `standards/project-spec/versions/1.8/templates/` | current state | Lifecycle and Quality are shared; Appendix A, B, and D are profile-specific canonical blocks; mandatory rows use `The system shall`. |
| `src/project_standards/specs/document.py` and `src/project_standards/specs/commands/upgrade.py` | current state | Existing parsing, section slicing, and template-block reconciliation supply the implementation boundary. |
| `src/project_standards/specs/commands/lint.py`, `src/project_standards/specs/cli.py`, and `src/project_standards/specs/commands/validate.py` | current state | Warning/strict behavior and the absence of a per-surface waiver support the selected rollout and tailoring boundary. |
| `ROADMAP.md` | repository schedule | #143 is separately grouped in the Project Specification conformance release context and may share a successor payload cut without changing this design. |

## Spec-authoring handoff

- Design brief: `docs/specs/2026-08-01-project-spec-conformance-plan-input.md`
- Operation: `create`
- Status: `approved`
- Problem and outcome: expose documented shared-boilerplate and mandatory-phrasing divergence without changing immutable predecessors or breaking ordinary lint.
- Scope boundary: successor-only profile-aware conformance linting for #62; no new configuration, waiver, suppression, fuzzy matching, repair, parser, or #143 behavior.
- Selected design: two warning families compare exact Lifecycle and Quality prose, structurally isolated profile-specific Appendix A, B, and D blocks, and mandatory `The system shall` rows; existing strict lint exits 1; clean human/JSON output names executed coverage.
- Approved consequential decisions:
  - advisory-to-strict warning rollout;
  - canonical tailoring boundary with no document-local exception;
  - two diagnostic families with `locus`/`line` identity and additive JSON coverage;
  - integrated design approval of the coherent successor-only contract.
- Agent-applied defaults:
  - reuse existing parser, slicing, reconciliation, finding schema, and strict-mode boundary.
- Assumptions:
  - shared-boilerplate surfaces are not ordinary tailoring points;
  - exact-key JSON consumers may need to accept the additive `checks` field.
- Blocking decisions: none
- Non-blocking matters:
  - downstream message wording may vary only within the approved diagnostic contract.
- Downstream impact:
  - the open-issue program's implementation phase formalizes and proves canonical, divergent, tailored, and predecessor behavior;
  - release planning may co-deliver #143 without changing this design.
- Material source artifacts:
  - `docs/plans/2026-08-01-open-issue-resolution-program-plan.md`
  - `standards/project-spec/versions/1.8/resources/tooling-notes.md`
  - `standards/project-spec/versions/1.8/templates/`
