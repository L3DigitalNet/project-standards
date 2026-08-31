---
schema_version: '1.1'
id: 'res-g5y9d3-deferred-tooling-release-evidence'
title: 'EV-008: v5.16.0 Deferred Tooling Successor Release Evidence'
description: 'Durable qualification and publication evidence for the v5.16.0 release (plan task T36).'
doc_type: 'research'
status: 'active'
created: '2026-08-05'
updated: '2026-08-31'
reviewed: '2026-08-05'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'release'
  - 'evidence'
aliases:
  - 'EV-008'
related:
  - 'Open-Issue Resolution Program Plan (docs/plans/2026-08-01-open-issue-resolution-program-plan.md, deleted under the completed-plan policy in 923cb63d)'
  - 'docs/research/2026-08-01-v5-15-release-evidence.md'
  - 'meta/versioning.md'
  - 'CHANGELOG.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# EV-008: v5.16.0 Deferred Tooling Successor Release Evidence

EV-008 for plan `2026-08-01/open-issue-resolution-program` task T36 (operational, REQ-900, TC-T36-001). T36's outcome widened in practice from the two deferred tooling successors (#88/#99) to the full owner-directed v5.16.0 defect cycle: four successor payloads, two engine fixes, and the supersession of all six open dependency pull requests.

## Verified state

- Tagged release commit: `8a2d1b9a6e22824c50112a116fc5e02666e4891c` on `main` (fast-forward lineage from `testing`; no merge commit). The full local battery ran green on exactly this tree (statics, ordinary, compatibility, performance, coverage-combine, coverage-report — exit 0), and the complete hosted fleet including `Check` concluded `success` on `8a2d1b9a`.
- Tags: `v5.16.0` (annotated tag object `8f93871e4e0430101359464471c85f07ff5b885f`, GPG-signed) and `v5` advanced as a re-created annotated tag (object `d83c0817aba5d47a010577099e08ca34bf8404db`), both dereferencing to `8a2d1b9a`.
- Release assets, byte-verified by download and sha256 comparison against the worktree build: `project_standards-5.16.0-py3-none-any.whl` `02f51b1287119589dc220aa687df3f6f98c383fab9eb01cd38f02651737af817`; `project_standards-5.16.0.tar.gz` `bf3875f9c47996b989c862d364e365f73a282280a375cb2d2a05acfde1d21700`. Release created with `--verify-tag --latest`; `isDraft: false`.
- Installed-route probe: `uvx --refresh --from "git+https://github.com/L3DigitalNet/project-standards@v5.16.0" project-standards --version` reports `project-standards 5.16.0`.

## Successor payloads and predecessor immutability

- Activated defaults: markdown-tooling `1.13` (`sha256:271cfbb5e5abde80439cb1f90b9d2eb55720fd52bff3d78f51057efa72aabfba`), markdown-frontmatter `1.9` (`sha256:5f08a86214605fb25db4bc48f78ccb68bae52a707506e0adf28117d3ae1d76a5`), python-tooling `1.12` (`sha256:7595019e39b209fb700817b0563aa2e5db50d368c3c5042eeb714e234076de5f`), project-spec `1.7` (`sha256:2d012e3de7699dc44bdf4ee8605cf350caca3ba05b0c490b8ff795ce5014df8f`); prior defaults flipped to `retained` and remain advertised/selectable.
- Predecessor bytes: a fresh-context adversarial verification over `40b8a0a5..7ccdbc95` confirmed no released payload bytes changed anywhere in the range (every `standards/**` diff is a pure `[[versions]]` append) and independently recomputed all four aggregates from a clean archive. v5.15.0's own registration/immutability suites stayed green throughout, including `test_markdown_tooling_bounded_format_scope.py`'s pinned `1.12` aggregate control.

## Contract proofs (TC-T36-001)

- Bounded Prettier corpus (#88, T16 checkpoint `50d0c364` + residual `ee2ac280`): real-Prettier set-parity proofs against a git-initialized mixed corpus — undeclared languages, `.gitignore` scratch, and `.git/info/exclude` scratch never traversed; declared format exclusions carried as `:(glob,exclude)` pathspecs; the repository's own managed instruction blocks now carry the bounded commands (dogfood).
- Ruff plugin-ownership contract (#99, T19 checkpoint `229a4bc1`): eleven leaf-addressable units, eleven-row proof file green source-side and in both battery runs; the `1-11-to-1-12` migration edge relocks the whole-table predecessor without `CP-LOCK-INCONSISTENT`; installed-route validation via the release reconcile below.
- Source / candidate / installed convergence: producer-mode `reconcile --apply` at the release boundary applied 11 mutations (four managed root workflows re-rendered, managed instruction blocks and `scripts/check.py` updated, catalog/lock refreshed 5.15.0 -> 5.16.0 listing all four package advances in the default preview — issue #126's fix observing its own release); a fresh reconcile plan afterwards contains zero mutating actions and `project-standards validate` reports all 36 files clean.

## Publication and closures (authorized)

- Authorization: owner task statement of 2026-08-05 plus the explicit `5.16.0` selection in the session's bounded-choice question; recorded in the execution log before any external effect.
- Closed as completed with evidence comments: #88, #99, #108, #114, #115, #117, #118, #119, #121, #126. Closed as superseded with commit references: PRs #33, #110, #111, #112, #113, #125. Annotated as deliberately deferred (feature scope): #55, #62, #116. Post-release open state: exactly those three deferrals, zero open pull requests.
