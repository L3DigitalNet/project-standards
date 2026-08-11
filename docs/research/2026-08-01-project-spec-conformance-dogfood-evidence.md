---
schema_version: '1.1'
id: 'research-2zxxmq-project-specification-1-9-conformance-dogfood-evidence'
title: 'Project Specification 1.9 Conformance Dogfood Evidence'
description: 'EV-001: sanitized activation, semantic-preservation, and targeted verification evidence for the Project Specification 1.9 dogfood migration.'
doc_type: 'research'
status: 'active'
created: '2026-08-11'
updated: '2026-08-11'
reviewed: '2026-08-11'
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'project-spec'
  - 'conformance'
  - 'dogfood'
  - 'verification-evidence'
aliases:
  - 'EV-001'
related:
  - 'docs/plans/2026-08-01-project-spec-conformance-plan.md'
  - 'docs/specs/2026-08-01-project-spec-conformance-plan-input.md'
  - 'standards/project-spec/versions/1.9/README.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Specification 1.9 Conformance Dogfood Evidence

EV-001 for plan `2026-08-01/project-spec-conformance` revision 3 task T5, requirement REQ-007, and proof PV-T5-001. This record retains the expensive migration evidence without credentials, private consumer data, unbounded logs, or internal reasoning.

## Prerequisite and continuation checkpoints

- The Project Specification portion of the runner-label advisory checkpoint was verified at `a7f01cd42adec93b18738f50df98bce8f6a76dfd` before any conformance migration write. Its Project Specification 1.9 aggregate is `sha256:47c13ac506df6b8f053e1e2daffc4f12d060e9884a431f511d41d984deb789d8`.
- T4 first froze the selected corpus on base `a7f01cd4`, then carried the exact candidate through `095aec56`. T5 restored all 16 candidate paths byte-for-byte after advancing to integrated base `ef12c72db62cc0263471c9cce6c66ff5c632474c`.
- GitHub Workflow 1.2 remains indexed but unadvertised. Catalog activation changes only Project Specification: 1.8 is retained and 1.9 is default, current family authority, and the repository's resolved selection.

## Selected corpus and strict RED

The configured selected set remained exactly 10 paths. The example was already clean and stayed byte-identical at `sha256:997c23a6321b118a7e2cfd34291134a880a4a523e07d4b0f9f7aa7d413d6946e`. The other nine documents produced 406 exact successor findings before repair: 366 mandatory-row findings and 40 shared-surface findings.

The pre-edit inventory aggregate is `sha256:20e6b5c79c80061141f6b08446f33322b8e342094da7ba34cf41ecf4b8cfe2f7`; the repaired inventory aggregate is `sha256:053e588a8d7fb4cc92a5dd9f836a9e339c1f05709bd7db08f9d7d7e7647cf28a`.

| Selected document | Profile | Pre-edit SHA-256 | Repaired SHA-256 | Rows | Surfaces | Semantic review |
| --- | --- | --- | --- | --: | --: | --- |
| `docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` | full | `16300c686c994c5ecc82a55b12e6867850eab8fcd8af0f0f91f6112154c58883` | `4eec545ebf5fe1c89b8490480a71b7562c56c7edfa08d8a107883cd35703d701` | 39 | 5 | Pass |
| `docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` | full | `dab44343bc39176d7dc64342285937cce5c3376e9b6179b65c064af840b5a6eb` | `6e344f983e4fe085f7dbaf26a5db0b3c10f2291b1ac8ceb1760eb1a783cf56e1` | 61 | 5 | Pass |
| `docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` | full | `7d466d8a0f425c059476a04a0fc36e1da2e134efaa02ac37a9bb0c8baf8bc8c1` | `d8305b3c8f4c4210579db86018ef50b67d9b51e3f4d422c9e1439a9b56ed7499` | 41 | 4 | Pass |
| `docs/specs/2026-07-09-agent-handoff-standard-package.md` | full | `27a8015310f1a2db6f96dffd61352ee84896eb79188fc93c10a967611f29542a` | `bcb707ad299eef87719f9580bbfa3eb5009744b41846ef59590ae33fdd13b57f` | 42 | 5 | Pass |
| `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md` | full | `6f9f337eeb35fbc05982fdde26271f6765f4cbac423176c287e39f8c996b4f89` | `5159208b7eff49a09db5fc3a803e52922401a1fd047da05acebd4143fc9ae4e2` | 54 | 5 | Pass |
| `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` | full | `b36e2e68130f3b4ac61f87d073aba703b47b0b3940493b8bb1c7c8f264d54413` | `635f3a4507123e88a5b80eed99c14817f720c8cb08ccfb54bcd4fe023099082c` | 54 | 5 | Pass |
| `docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md` | standard | `37f9feeb4df243b33533f4cc5c002a5d67f9025bfa207475d96d674eac7cb88f` | `ee3d0ef03297c19f8bb8c56c1492a1f79edd7922fcd3d1493133878dedb52125` | 32 | 5 | Pass |
| `docs/specs/2026-07-27-v5-validation-fidelity-correction-train-spec.md` | standard | `65160217f4b6eef4244ae40a4444a17578e4644656e2fcd05b7b2a8a5a71a100` | `950d382db8cf679fa23738ad93bf6c92de3a8254f7aa64a6fa31be94ca57c8e9` | 29 | 5 | Pass |
| `docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md` | light | `d4681c5fbcaced25437f4d932ba82a00755e57f790f8d85cef843aafb915346d` | `207a78176d672615c41cf523f978fec06248e282e0c0faed8a5de84588332ac3` | 14 | 1 | Pass |

## Repair and semantic-preservation proof

- Every reported requirement keeps its exact ID, original normative clause, rationale, acceptance text, and priority. The only requirement-cell addition is the fixed opening `The system shall satisfy the following requirement:`, followed by one space before the unchanged original clause.
- Every reported Lifecycle, Quality, Appendix A, Appendix B, or Appendix D locus now equals the immutable canonical 1.9 surface for its selected profile. No unreported requirement row changed.
- Each changed specification has exactly one dated revision row. Where a tailored lifecycle line was restored to canonical form, that row preserves the complete prior lifecycle record verbatim; approved and superseded lifecycle meaning therefore remains reviewable.
- A deterministic reverse comparison removed only the new revision row, the fixed requirement opening, and the canonical replacement at each reported surface. Every reconstructed document then matched its pre-edit bytes exactly. The comparison covered all 366 rows and 40 surfaces.

## Activation and convergence

- The generated human catalog matches its renderer. Project Specification 1.9 is `default`; 1.8 is `retained`; GitHub Workflow 1.2 remains `unadvertised`.
- Candidate-runtime producer reconcile reported zero findings and advanced the repository selection from 1.8 to 1.9 while regenerating only `.standards/catalog.toml` and `.standards/lock.toml` within this task's control-state scope.
- The immediate second reconcile reported `drift: false`, no mutating action, no finding, and an unchanged catalog digest.
- The blocked T4 package-contract node was corrected in T5 only at its four stale activation assertions. SHA-256 checks prove every byte before and after that function remained unchanged.

## Targeted qualification

Source-selected, extracted-candidate, and local-wheel-installed strict lint each processed all 10 documents with zero findings and explicit `shared-boilerplate` plus `mandatory-phrasing` coverage. Strict validation processed the same 10 documents with zero findings through all three routes.

- The T1–T3 focused regressions plus the complete Project Specification 1.9 package-contract file passed 196 tests.
- The corrected activation node and every other T5-owned assertion passed. The five package, graph, schema, projection, and generated-catalog validators passed.
- Scoped Prettier, markdownlint, evidence frontmatter validation, Ruff, and BasedPyright passed. Candidate-runtime reconcile remained a zero-finding no-op with `drift: false`.
- An independent read-only semantic verifier confirmed all nine reconstructed documents exact after masking only the 406 reported repairs and nine revision rows. It also confirmed the two example projections unchanged and every byte outside the corrected activation node exact.

One deliberately extra release-current diagnostic run found three stale Project Specification 1.8 links in root `README.md` and one pre-existing unclassified Standard Bundle Authoring 2.0 reference in the selected V2 authoring specification. T5 does not claim those release-current surfaces or the generic release-consistency node. The release coordinator explicitly retained them for the final integrated release-current sweep after all package activations; they do not alter this task's strict-clean selected corpus or package activation proof.

No repository-wide `scripts/verify.sh` invocation ran in T4 or T5. The final integrated release coordinator owns the single repository-wide gate.
