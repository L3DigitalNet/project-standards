# Repository Hygiene and Maintenance Review

## Executive summary

The repository is structurally healthy at commit `2b10da727158d3a50fb21c5cfcf526c4c52ee24d`: package manifests, graph relationships, schemas, payload projections, catalog rendering, dependency locks, Python statics, Markdown tooling, Git objects, and tracked symlinks all pass their applicable checks. No tracked cache/build leakage, dependency vulnerability, secret, case-colliding path, broken symlink, or immutable predecessor mutation was found.

Three maintenance priorities dominate the review:

1. The root dogfood catalog was committed ahead of its central lock, leaving the repository unable to reconcile or run root-dependent validation and making the hosted standards-graph workflow red.
2. `README.md` presents Agent Handoff 1.8 as the current consumer payload beside instructions that install v5.13.0, although that immutable tag contains only Agent Handoff 1.7.
3. The retained Agent Handoff implementation plan materially predates the current specification and status model; its live retirement work should transfer to the current open-issue program at an owner-approved lifecycle checkpoint.

The local release gate also validates compatibility against a second wheel build instead of the prepared candidate artifact. That weakens exact-artifact evidence but is independent of the current catalog-lineage blocker.

## Review header

| Field | Value |
| --- | --- |
| Repository | `project-standards` |
| Branch | `testing` |
| Anchored commit | `2b10da727158d3a50fb21c5cfcf526c4c52ee24d` |
| Date | 2026-08-01 |
| Mode | Read-only audit; report is the only repository write |
| Scope | Git/layout, Python maintainability, tests/CI, docs/governance, dependencies/security, standards/control plane |
| Python simplification scope | 122 tracked `src/project_standards/**/*.py` files excluding immutable `payloads/**` |
| Reviewers | Coordinator plus six disjoint Terra audit lanes and one fresh adversarial findings review |

The review preserved immutable package history, archived evidence, active plans, generated projections, and ignored local work. It did not reconcile, publish, delete, upgrade, or reformat any audited source.

## Baseline

### Passing evidence

- Local `testing` and `origin/testing` were byte-identical at the anchor before review.
- `git fsck --full --no-reflogs` found no corruption; the repository object store is approximately 18 MiB.
- Ruff formatting, Ruff lint, and strict BasedPyright passed with zero diagnostics.
- The focused CLI/document contract suite passed 668 tests; two root-dependent tests failed only on the catalog/lock inconsistency described in HYG-001.
- A separate Python-maintenance characterization set passed 87 tests.
- `uv lock --check` passed.
- `pip-audit` and `npm audit --package-lock-only` reported zero known vulnerabilities. The local, unpublished `project-standards` distribution was correctly unavailable to PyPI audit lookup.
- Package validation, graph validation, generated-schema checking, payload-projection checking, and rendered-catalog checking passed.
- All 1,282 tracked symlinks resolve within the repository; none are dangling or escape the root.
- The catalog and source inventory agree on 56 advertised immutable versions across nine package families. Since v5.13.0, predecessor version directories are unchanged; Agent Handoff 1.8 is the only new versioned payload.
- Prettier and markdownlint pass the configured corpus.

### Known non-pass evidence

- `project-standards reconcile --check --repo . --json` exits 2 with `CP-CONTROL-STATE` because the lock does not identify the current catalog digest.
- The hosted `Validate standards graph` run for the anchor, run `30711087567`, failed at `packages check-release --baseline v5.13.0`: the proposed tool version remains 5.13.0 and therefore does not advance beyond the released baseline.
- Broad documentation validation reports 176 errors and 40 warnings across all `docs/`. Most are preserved archived designs, append-only evidence, or the owner-approved Usage Documentation transcript delete candidate. One maintained-document failure survives triage as HYG-005.
- A complete fast or full repository gate cannot be treated as authoritative until HYG-001 restores consistent root control-plane state.

## Coverage

| Surface | Coverage and method |
| --- | --- |
| Git and artifacts | Tracked/ignored inventory, modes, object integrity, object sizes, branches, tags, symlinks, case collisions, cache/build leakage |
| Python | 122/122 in-scope modules inventoried and parsed; callers, registrations, tests, history, typing, duplication, and security boundaries inspected |
| Tests and CI | `tests/`, pytest/coverage configuration, compatibility fixtures, `scripts/verify.sh`, all GitHub workflows, action/dependency update policy |
| Documentation | README, maintained specs/plans, indexes, handoff authorities, archive/future boundaries, local-link and heading diagnostics |
| Dependencies and release | Python and Node manifests/locks, live advisory audits, action pins, packaging metadata, release preparation and classification |
| Standards/control plane | Catalog, config, lock, package graph, schemas, providers, projection, regression ledger, immutable predecessor history |

## Actionable findings

### HYG-001 — Restore catalog lineage before the 5.14 dogfood refresh

- **Severity:** High; release blocker.
- **Evidence:** `.standards/catalog.toml` advertises Agent Handoff 1.8 and digest `36a577…`, while `.standards/lock.toml` still authenticates the released v5.13 catalog digest `7c543f…` and Agent Handoff 1.7. Commit `a435b50c` advanced the catalog without the lock. Reconciliation, Agent Handoff validation, and drift checking fail before their domain work begins.
- **Impact:** root dogfood validation is unavailable, root-dependent tests fail, and the hosted standards-graph workflow has remained red since the catalog advance.
- **Safe action:** preserve the current work on `testing`, then perform the approved release path on clean `main`. Restore only `.standards/catalog.toml` byte-for-byte from immutable `v5.13.0`, prepare the 5.14.0 release identity, build/extract a fresh intermediate candidate, preview reconciliation, and apply the normal transaction to publish the successor catalog, managed registrations, and lock. Never hand-edit the lock or predecessor payloads. Rebuild the exact release commit and run the complete release gate afterward.
- **Independent review:** approved and narrowed to this exact lineage-restoration sequence. A disposable simulation produced only `.claude/settings.json`, `.codex/config.toml`, `.standards/catalog.toml`, and `.standards/lock.toml` as reconciliation outputs.

### HYG-002 — Separate published Agent Handoff 1.7 from the 1.8 candidate in README

- **Severity:** High; user-facing release accuracy.
- **Evidence:** `README.md:119-121` and `README.md:168-176` name Agent Handoff 1.8 as the current standard and payload. `README.md:137-144` tells consumers to install immutable v5.13.0. That tag contains Agent Handoff only through 1.7; `docs/specs/README.md:12` correctly calls 1.8 a verified candidate pending release preparation.
- **Impact:** a consumer following one page can expect a payload that the documented installation cannot provide.
- **Safe action:** until 5.14.0 is published, keep the public current-payload table at 1.7 and label 1.8 links explicitly as `testing` candidate material. Switch the public-current table atomically with the release.
- **Independent review:** approved as distinct from HYG-001: this is the public-document consequence, not the control-plane cause.

### HYG-003 — Retire or reclassify the stale Agent Handoff implementation plan

- **Severity:** High; competing execution authority.
- **Evidence:** `docs/plans/2026-07-09-agent-handoff-standard-package.md:3-18` still describes SPEC-DPEY rev 0.5, package 1.0, the retired engine checkout, and an unchecked historical implementation workflow. `docs/handoff/specs-plans.md:38-39` records approved rev 0.9, released 1.7, verified 1.8, Tasks 1-17 complete, and Task 18 retirement in progress. T32 in `docs/plans/2026-08-01-open-issue-resolution-program-plan.md` is the proposed successor for that remaining work after an owner-approved lifecycle transfer.
- **Impact:** an implementing agent can select the wrong plan, version model, command surface, and task state.
- **Safe action:** at an owner-approved lifecycle checkpoint, move the remaining retirement work wholly to T32, update durable pointers, and delete the completed historical plan under the repository's completed-plan policy. Do not retroactively mark its obsolete checklist complete.
- **Independent review:** approved; removal remains owner-gated because it changes plan lifecycle.

### HYG-004 — Make the local gate reuse the prepared candidate wheel

- **Severity:** Medium; release-evidence integrity.
- **Evidence:** `scripts/verify.sh:58,100-105,156,245-254` requires only an extracted `build/wheel-runtime` and never exports `PROJECT_STANDARDS_COMPATIBILITY_WHEEL`. `tests/package_compatibility/conftest.py:40-58` builds a new wheel whenever that variable is absent. Hosted `check.yml:58-70` correctly selects one wheel, exports it, and extracts that same artifact.
- **Impact:** local ordinary tests and compatibility tests can validate different wheel builds; CI may become the first exact-artifact parity check.
- **Safe action:** make `verify.sh` resolve exactly one prepared wheel, fail on zero or multiple candidates, and export its absolute path before any lane starts. Preserve the existing extracted runtime as `PYTHONPATH`.
- **Independent review:** approved at Medium; this is an exact-artifact gap, not proof of a current product defect.

### HYG-005 — Replace the maintained specification's deleted-plan link

- **Severity:** Medium; maintained navigation.
- **Evidence:** `docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md:694` links to nonexistent `docs/plans/2026-07-25-v5-adoption-integrity-correction-train-plan.md`. `docs/handoff/specs-plans.md:23` records that the completed plan was removed under policy.
- **Impact:** the maintained specification advertises a nonexistent current implementation plan.
- **Safe action:** replace the link with the durable completion authority and/or the retained release and audit evidence. Do not recreate the completed plan.
- **Independent review:** approved with certainty.

### HYG-006 — Reconcile the MCP roadmap lifecycle with the shipped server

- **Severity:** Medium; locked-spec lifecycle accuracy.
- **Evidence:** `docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md:58,130` says server implementation may begin at T2. `docs/handoff/specs-plans.md:21-22` records that the read-only server shipped in v5.12.0.
- **Impact:** the locked roadmap can reopen already-completed work and obscures which controlled-write and remote-transport phases remain genuinely deferred.
- **Safe action:** authorize a controlled successor revision that records the completed delivery while preserving historical sequencing requirements and the separately deferred phases.
- **Independent review:** approved; do not silently edit the locked spec.

### HYG-007 — Add recurring Node dependency maintenance

- **Severity:** Medium for update coverage; an npm-audit required gate is an owner policy choice.
- **Evidence:** `.github/dependabot.yml` configures only `github-actions`. `package-lock.json` contains 87 development dependency entries, but no npm Dependabot lane exists. Current `npm audit` is clean.
- **Impact:** future Node tooling updates and advisories can remain unnoticed until manual review.
- **Safe action:** add an `npm` Dependabot entry for the repository root. Separately decide whether `npm audit --package-lock-only` should become a required hosted gate; its network and advisory semantics deserve an explicit policy choice.
- **Current external basis:** GitHub's current [Dependabot configuration documentation](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuring-dependabot-version-updates) explicitly supports independent `npm` and `github-actions` ecosystems.
- **Independent review:** approved after splitting update automation from the optional required gate.

### HYG-008 — Add executable orchestration coverage for `verify.sh`

- **Severity:** Medium; gate-maintenance coverage.
- **Evidence:** `VERIFY_SMOKE=1` exists to exercise lane plumbing, but `tests/test_repository_test_gate.py` asserts only hosted `check.yml`; no test invokes or validates local `verify.sh` orchestration.
- **Impact:** environment propagation, lane order, candidate selection, and aggregate failure handling can drift independently from hosted CI, as HYG-004 demonstrates.
- **Safe action:** add a hermetic shell-orchestration test using fake executables and smoke mode, or extract the plan/environment construction to a small testable helper. Assert fast/full ordering, candidate-wheel propagation, and nonzero aggregate behavior.
- **Independent review:** approved as the durable regression for HYG-004.

### HYG-009 — Decide whether to harden external action pins

- **Severity:** Low; accepted supply-chain policy choice, not a demonstrated defect.
- **Evidence:** workflows use mutable major tags for `actions/checkout`, `actions/setup-node`, `actions/setup-python`, and `DavidAnson/markdownlint-cli2-action`; `astral-sh/setup-uv` alone is SHA-pinned. Dependabot already maintains GitHub Actions weekly, and jobs use read-only repository permissions.
- **Impact:** the audited commit does not identify the exact bytes executed when a major tag moves.
- **Safe action:** either record continued acceptance of trusted major tags, or pin every external action to a verified 40-character SHA with an adjacent version comment and add an invariant test. Keep Dependabot maintaining the pins.
- **Current external basis:** GitHub's current [secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use) identifies a full-length commit SHA as the immutable action reference while acknowledging trusted tags as a common convenience tradeoff.
- **Independent review:** narrowed from Medium to Low because the current major-tag policy is explicit and maintained.

### HYG-010 — Normalize accidental executable modes only across mutable surfaces

- **Severity:** Low; source/package hygiene.
- **Evidence:** `src/project_standards/__init__.py` and 27 Markdown resource/template paths carry mode `100755` without shebangs. Many Markdown paths are historical immutable Project Spec payloads.
- **Impact:** misleading checkout/archive permissions and unnecessary executable resource modes.
- **Safe action:** normalize the mutable `src/project_standards/__init__.py` mode if no packaging contract relies on it. For Markdown resources, first determine which current/successor authorities may change modes; never bulk-chmod immutable advertised versions or projections.
- **Independent review:** approved only with the immutable-history restriction.

## Behavior-preserving simplification findings

### S-001 — Consolidate Agent Handoff's optional-reader primitive

- **Definitions:** `src/project_standards/agent_handoff/planning.py:98` and `src/project_standards/agent_handoff/validation.py:88`.
- **Calls:** 16 total across planning and validation.
- **Change:** move the byte-identical helper to `agent_handoff/paths.py` as a private shared primitive; import it from both consumers and delete the copies.
- **Contract:** preserve `consumer_path()` → `exists()` → secure `read_bytes()` exactly. Absence must remain distinct from repository-boundary or read failure.
- **Characterization:** add direct present/absent coverage to `tests/agent_handoff/test_paths.py`; retain planning and validation suites.
- **Benefit/confidence:** removes duplicated boundary knowledge; High confidence, Low blast radius.
- **Independent review:** approved but deferred until after release-lineage work.

### S-002 — Centralize shared adapter newline and line-start rules

- **Definitions:** newline helpers in `editorconfig.py:178`, `jsonc.py:910`, `markdown.py:239`, `toml.py:722`, and `yaml.py:427`; line-start helpers in `jsonc.py:914` and `yaml.py:435`.
- **Calls:** 28 total across five adapters.
- **Change:** add `newline_for(text)` and `line_start(text, index)` to `control_plane/adapters/base.py`; remove the seven local copies.
- **Contract:** preserve the mixed-ending rule: CRLF only when CRLF is present and no bare LF remains; otherwise LF. Do not reduce it to a simple CRLF containment check.
- **Characterization:** add CRLF, LF, no-newline, and mixed-ending cases to `tests/control_plane/test_adapters_base.py`; retain byte-exact adapter suites.
- **Benefit/confidence:** one owner for repeated byte-layout rules; High confidence, Medium blast radius.
- **Independent review:** approved but deferred until after release-lineage work.

## Retained, manual, and blocked items

| ID | Disposition | Reason |
| --- | --- | --- |
| D-001 | Retain immutable payload/projection duplication | Advertised versions are permanent contract data; Git stores identical blobs once. |
| D-002 | Do not mass-fix 176 broad documentation diagnostics | Most belong to archived designs, append-only evidence, or the approved transcript delete candidate. HYG-005 is the maintained survivor. |
| D-003 | Keep `control_plane/provider_inputs.py` deferred | Current payload schemas do not declare read shapes; retirement needs an approved successor-payload/schema program. |
| D-004 | Keep testing-branch CI triggers | `tests/README.md` explicitly makes standards-graph the only hosted testing-branch gate; local verification remains required. |
| D-005 | Retain timing gates | No demonstrated flake was found; collect timings before changing thresholds or adding retries. |
| J-001 | Delete four merged local branches | `review-remediation-5.1` and three unattached `worktree-agent-*` branches are merged; delete only after owner retention confirmation. |
| J-002 | Prune unreachable local Git objects | Recovery debris is small (9.30 MiB packed store); use ordinary reflog expiry/GC only after confirming no recovery need. |
| J-003 | Clean ignored local artifacts | `.scratch` is 631 MiB and `build` is 143 MiB, but both hold active/recent evidence. Remove only after the owning plans harvest required proof. |
| B-001 | Complete fast/full repository gate | Blocked by HYG-001; focused/statics/package evidence is recorded instead. |

## Implementation sequence

1. Complete HYG-001 under the existing T1.6 release gate; re-establish green root and hosted control-plane evidence.
2. Resolve HYG-002 in the same release-preparation change so public documentation and installable artifacts agree.
3. Take the owner lifecycle decisions for HYG-003 and HYG-006; apply HYG-005 independently because it does not require a spec/plan lifecycle choice.
4. Implement HYG-004 and HYG-008 together, test first, then rerun fast and full candidate gates.
5. Decide supply-chain policy for HYG-007 and HYG-009; keep each as a separate, reviewable workflow change.
6. Address HYG-010 and simplifications S-001/S-002 only after release work, one finding at a time with their characterization tests.
7. Perform optional local cleanup J-001–J-003 only after explicit retention decisions.

## Tool limitations and final audit

- The broad documentation helper scans historical and future material outside the repository's governed include set; every diagnostic was therefore triaged against lifecycle authority instead of treated as an automatic defect.
- No optional clone/dead-code scanner was installed. The previous whole-engine simplification report was used as historical evidence, while this review re-inventoried all 122 current in-scope modules and promoted only independently verified candidates.
- Live dependency audits are point-in-time evidence, not proof against future advisories.
- Hosted evidence was inspected for the pushed anchor only where a workflow actually ran; testing intentionally triggers only the standards-graph workflow.
- The adversarial review rejected local scratch size/tooling noise as a repository defect, narrowed action pinning to a policy decision, and preserved all immutable/history boundaries.
