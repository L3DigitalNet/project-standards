# Review: Consumer Standards Control Plane Specification (SPEC-CP01)

**Spec:** `docs/superpowers/specs/2026-07-10-consumer-standards-control-plane-spec.md` (rev 0.1, draft, Full profile) **Review target state:** commit `40d30a0` (spec as committed; working tree changes touch only `docs/TODO.md` and `docs/workflows/`, not the spec) **Workflow:** `docs/workflows/review-spec.md` **Reviewer:** session 2026-07-10

## Round 1

### Verdict

**APPROVE AFTER REVISION** — no blocking findings. Every factual claim checked against the repository held, and the spec passes its own validators. Five 🟡 completeness gaps would force the implementer or planner to invent semantics the spec should own (partial control-plane state, legacy-file disposal, candidate de-authorization, the apply concurrency lock, and `.standards/packages/**` commit policy), plus two 🟢 polish items.

### Method

The spec (all 1,130 lines) was read end to end before recording findings. Every factual claim was then verified live against the repository, not from memory or the spec's own citations: the ADR inventory, standards-package inventory and `standard.toml` fields, `adopt.toml` artifact destinations and kinds, provider counts, config namespaces, the aggregate-apply code path, CLI subcommands, reference-link targets, spec-index entries, and both repo validators (`uv run project-standards spec validate` → OK; `uv run validate-frontmatter --config .project-standards.yml` → 31 files pass).

### Verified and held (do not re-check in later rounds)

- All 21 ADR paths in `related.adrs` exist in `docs/adr/` (0001–0022; see F6 for the 0009 omission). ADR 0023/0024 do not yet exist, consistent with "New ADR" dispositions.
- §3.1 "Five packages currently target `.project-standards.yml`" — exactly five: `adr`, `cli-documentation`, `agent-handoff`, `project-spec` (fragment `target =`), and `markdown-frontmatter` (whole-file `dest =`), per `src/project_standards/bundles/*/adopt.toml`. The markdown-frontmatter whole-config ownership claim in the migration matrix also holds.
- §3.1 `AGENTS.md` collision — `python-tooling` ships `AGENTS.md` as a whole `file` (`bundles/python-tooling/adopt.toml:38-40`) while `agent-handoff` targets it as a semantic integration (`bundles/agent-handoff/adopt.toml:135`).
- §3.1 "the specialized aggregate path drops non-handoff fragments" — confirmed in code: `execute_plan` accumulates fragment snippets into a `Report` (`src/project_standards/adopt/engine.py:314-321`), but the agent-handoff aggregate path discards that return value (`src/project_standards/agent_handoff/planning.py:594`), so non-handoff fragment guidance is never surfaced.
- Agent Handoff's package-specific provenance lock exists (`runtime/provenance-lock.json` seed, `standards/agent-handoff/standard.toml:59,193`), supporting §3.1 and FR-020.
- §8.2 migration-matrix row facts match ground truth: adoption modes (`validator`/`copy-adopt`/`cli`/`reference-only`/`none`), provider counts (adr 2, project-spec 6, cli-documentation 1, markdown-tooling 3), python-coding `status = "draft"` with no namespaces, and the exact current namespaces `markdown.adr`, `markdown.frontmatter`, `agent_handoff`, `python_tooling`, `spec`, `cli_documentation`, `markdown_tooling`.
- §3.1 "one current `adopt.toml` payload even when its manifest lists several supported contract versions" — every `standard.toml` lists 2–3 `supported` versions while each bundle has a single unversioned `adopt.toml`.
- The `adr` "hidden Frontmatter adoption dependency" is credible: `adr` declares `markdown-frontmatter` only as a companion, yet its validation provider entrypoint is `project_standards.validate_frontmatter:main` (`standards/adr/standard.toml:22,63`).
- FR-017's premise holds: `project-standards adopt` exists today (`--help` confirms). NG-004's `.agents/skills/` example matches actual skill destinations in `adopt.toml` files.
- SPEC-BA01 exists (`spec_id: SPEC-BA01`, implemented + approved per `docs/handoff/specs-plans.md:16`), so FR-031's supersession framing is accurate. SPEC-CP01 is indexed at `docs/handoff/specs-plans.md:9` with no ID collision.
- R-003's "existing root-artifact decision" is a real tracked prerequisite (`docs/TODO.md:111-113`, explicitly named a SPEC-CP01 prerequisite there).
- All reference-section links resolve (`meta/versioning.md`, `standards/catalog.md`, `.project-standards.yml`, `src/project_standards/README.md#adopt-engine` anchor at line 310, both standard READMEs, SPEC-MT01).
- Internal consistency spot-checks passed: FR-001–FR-031 contiguous and unique; §8.3 D-00x ADR dispositions agree with the reconciliation matrix in every overlapping row; §17.3 traceability covers every FR, NFR, IR, DR, and ERR ID; goal→FR mappings in §4 resolve; §9 lock example is consistent with EC-004 semantics; §18.2 defaults match the §9 examples.

### Findings

#### F1 🟡 No defined behavior or recovery path for a partially present control plane

- **Defect:** §10.4 states run from Uninitialized (no control plane) to Reconciled, and ERR-001 covers _invalid_ files, but nothing covers a control plane with `config.toml` present and `catalog.toml` or `lock.toml` missing (deleted, lost in a merge, or partially committed). Since all three are committed tool-owned files (A-001), this state will occur in practice. FR-001 scopes `init` to "when no legacy or unified control-plane authority exists", so the repo cannot re-init, and no regeneration command is specified.
- **Evidence:** Read §10.4, §12.1, §7.1 FR-001/FR-009, and EC-001–EC-011; no state, error mode, or edge case addresses missing (as opposed to invalid) tool-owned files.
- **Fix:** Add an edge case (and matching ERR row) defining the missing-catalog and missing-lock states and the sanctioned recovery — e.g., a read-only finding that names a regeneration path (`reconcile` regenerates catalog from the installed distribution; missing lock is treated as never-applied live drift), or an explicit `init --repair`-class operation.

#### F2 🟡 Migration does not specify disposal of the legacy `.project-standards.yml`

- **Defect:** FR-022 makes legacy YAML plus unified TOML together a hard split-authority failure, and AW-005 says "Unified files replace legacy authority", but no requirement states that migration apply removes (or instructs removal of) `.project-standards.yml`. If migration leaves it in place, every migrated repo immediately fails validation under FR-022's dual-file rule.
- **Evidence:** Read FR-021, FR-022, AW-005, EC-001, ERR-007, and DR-006; none assigns responsibility for the legacy file's removal or defines the post-migration state of that path.
- **Fix:** State explicitly in FR-021 (or a new acceptance criterion) that a successful migration apply deletes or archives `.project-standards.yml` as part of the same plan, and that the migration preview shows that removal action.

#### F3 🟡 Intentional exit from an accepted breaking-candidate major is undefined

- **Defect:** FR-014, C-006, and §12.3 prohibit _silent_ downgrade, and the §9 lock narrative says resolution stays on the accepted major "until the config pins another supported version or a separately authorized transition occurs" — but that separately authorized transition is never defined. There is no flag, edge case, or requirement covering the user who authorized major 2, wants to return to the 1.x default track, and needs to know whether pinning `version = '1.2'` suffices, whether it requires authorization, and how `track_major`/`major_authorized` in the lock are cleared.
- **Evidence:** Read FR-011–FR-015, EC-003/EC-004, AW-003, §9 lock narrative, and §12.3; only the retention direction is specified.
- **Fix:** Add a requirement or edge case defining the de-authorization path: what config change expresses it, whether it needs explicit authorization (recommended, since it is major-crossing), what migration/rollback support the package must declare, and how the lock's accepted-track record is updated.

#### F4 🟡 The apply concurrency lock exists only in the capacity table

- **Defect:** §14 asserts "Apply uses a repository-local lock and hash preconditions" for concurrent-writer safety, but no FR/NFR/DR defines that lock, no data entity covers it, nothing says whether it is committed or ignored, and §17.3 has no test row for concurrent-apply behavior. A capacity-table "design consequence" is not an implementable contract.
- **Evidence:** Searched §7, §9, §12, and §17 for the repository-local apply lock; it appears only in the §14 concurrent-writers row.
- **Fix:** Either promote it to a requirement (name the lock mechanism/path, its lifecycle, and its Git-ignore status, with a traceability row) or delete the claim from §14 and rely solely on hash preconditions, stating that concurrent applies are unsupported.

#### F5 🟡 Commit policy for `.standards/packages/STANDARD_ID/` is unspecified

- **Defect:** A-001 covers only `config.toml`, `catalog.toml`, and `lock.toml`. DR-005 constrains what package runtime state may contain but never says whether it is committed, whether it participates in lock hashing/drift detection, or how removal treats it. The §3.2 tree presents it as part of the "committed, reviewable control plane", while the ADR 0015 amendment excludes `.standards/packages/**` from ordinary managed-document rules — the reviewability, drift, migration, and removal semantics all change depending on the answer.
- **Evidence:** Read A-001, DR-005, §3.2, FR-019/FR-020, FR-010, and the ADR 0015 matrix row; no statement of commit/ignore status or drift participation exists.
- **Fix:** State in DR-005 (and reflect in FR-010 removal semantics) whether package-directory state is committed, whether the central lock inventories it, and what disable/removal does with it.

#### F6 🟢 Frontmatter `related.adrs` omits ADR 0009

- **Defect:** The frontmatter lists 21 of the 22 existing ADRs, omitting `adr-0009-agent-summary-and-canonical-standard-split.md`, yet the §8.3 reconciliation matrix explicitly dispositions ADR 0009 ("Retain"). Other retain-only ADRs (e.g., 0005) are listed, so the omission is inconsistent rather than a policy.
- **Evidence:** Compared the frontmatter list against `ls docs/adr/` and the reconciliation matrix rows.
- **Fix:** Add `docs/adr/adr-0009-agent-summary-and-canonical-standard-split.md` to `related.adrs`.

#### F7 🟢 §9 catalog and lock examples are built on a package that will not exist

- **Defect:** The catalog-snapshot and applied-lock examples (and the desired-config example's first entry) use `project-toolbox`, which NG-006 excludes from this spec and which will not be in the v5 catalog when this contract is implemented. FR-005 requires the catalog to list packages "available in the installed distribution", so the examples model a state the implementation cannot reproduce, and golden fixtures cannot mirror them.
- **Evidence:** §9 examples versus NG-006, §1, and OQ-012.
- **Fix:** Rebase the catalog/lock examples on an existing package (e.g., `markdown-frontmatter`, already used in the desired-config example) or add one sentence marking `project-toolbox` as a hypothetical future package used for illustration only.

## Round 2

**Review target state:** commit `69918a3` (`docs(v5): resolve control-plane spec review`, spec rev 0.2)

### Verdict

**APPROVE AFTER REVISION** — all seven round-1 findings are resolved and verified against the rev 0.2 text, not on assertion. The revision also passes both repo validators. One new 🟡 emerged in the newly added version-transition machinery (disable/re-enable versus the accepted-major track), plus one new 🟢. Not yet converged because a new 🟡 appeared; a round 3 confirming the F8 fix should converge.

### Method

Reviewed the full `69918a3` spec diff (141 insertions, 89 deletions), verified each round-1 fix in the current spec text, re-ran `project-standards spec validate` (OK) and `validate-frontmatter` (31 files pass), and re-checked the new content's ground-truth claims: FR-035's inventory of current direct-write operations matches the CLI (`fix`, `spec new`, `spec upgrade`, `agent-handoff upgrade`, `format-frontmatter`), and the rebased §9 examples use `markdown-frontmatter` with `1.2` as current stable, matching `standards/markdown-frontmatter/standard.toml` (`supported = ["1.0", "1.1", "1.2"]`).

### Prior-finding verification

| Finding | Status | Evidence in rev 0.2 |
| --- | --- | --- |
| F1 🟡 partial control plane | **Resolved** | New FR-032 (read-only recovery plan; catalog regeneration; evidence-backed lock reconstruction; refuse config inference), EC-012, ERR-009, new `Incomplete` state in §10.4, `--repair-state` in IR-003, DoD item, FR-032 traceability row, MS-1 bullet. |
| F2 🟡 legacy YAML disposal | **Resolved** | FR-021 now requires retiring `.project-standards.yml` as a previewed, visible removal action only after complete conversion and validation; AW-005 and ERR-007 updated to match; dedicated DoD item added. |
| F3 🟡 candidate-major exit | **Resolved** | New FR-033 (`--allow-major ID@MAJOR`, exact-target exit, `track_major`/`major_authorized` lock updates, catalog-promotion exemption), AW-007, EC-013, OQ-015, D-013; FR-011/013/014/015, C-004, EC-003, IR-003, and the §9 lock narrative all reconciled to the same semantics — internally consistent on spot-check. |
| F4 🟡 apply concurrency lock | **Resolved** | New NFR-009 (shared/exclusive non-blocking advisory lock on `.standards/`, no lock artifact, init ordering), ERR-010, §14 row rewritten, DoD item, NFR-009+ERR-010 traceability row, MS-1 bullet. |
| F5 🟡 `packages/` commit policy | **Resolved** | New FR-034 (declared, committed, centrally inventoried and hashed; no transient/ignored state), A-001 expanded to the durable `.standards/` tree, DR-005 rewritten, FR-010 removal/pruning semantics, AW-008, EC-014, ERR-011, §18.6 updated. |
| F6 🟢 ADR 0009 omission | **Resolved** | `docs/adr/adr-0009-agent-summary-and-canonical-standard-split.md` added to frontmatter `related.adrs`. |
| F7 🟢 `project-toolbox` examples | **Resolved** | §9 catalog/lock examples rebased on `markdown-frontmatter` with an explicit note that the breaking candidate is illustrative and fixtures must substitute embedded versions; desired-config example trimmed to real packages. |

Beyond the round-1 scope, rev 0.2 also added a provider phase/effect contract (FR-035, D-011, OQ-013, ERR-012, EC-016) and consumer-owned referenced extensions (FR-036, DR-007, D-012, OQ-014, EC-015, AW-009). Both were checked for internal consistency: goals, DoD, traceability, milestone summaries (now D-001–D-013), authorization table, threat model, and Appendix B were all updated coherently; ERR-010–ERR-012 are each covered by a traceability row.

### New findings

#### F8 🟡 Disable/re-enable is undefined against the accepted-major track

- **Defect:** FR-014 makes candidate-major authorization "durable", and FR-033 defines the only sanctioned exits — but nothing says what happens to the lock's `track_major`/`major_authorized` record when the package is disabled (FR-010/AW-006) and later re-enabled. If the disabled package's `[standards.STANDARD_ID]` lock record is dropped, re-enabling with `version = 'latest'` silently lands on the default major — an unauthorized-feeling downgrade that bypasses FR-033's exact-target exit rule — while any preserved modified major-2 artifacts surface only as generic conflicts. If the record is retained, the lock schema must represent applied state for a package that is no longer enabled. Either answer changes the lock schema contract frozen at MS-0.
- **Evidence:** Searched rev 0.2 for the interaction: FR-010, AW-006, and EC-014 cover artifact removal; FR-014, FR-033, AW-007, EC-004, and the §9 lock narrative all presume a continuously enabled package. No requirement, edge case, or lock-narrative sentence covers the disable→re-enable cycle.
- **Fix:** Add an edge case (and a sentence in the §9 lock narrative) stating whether accepted-track records survive disablement — recommended: retain the track record on disable so re-enable with `latest` resumes the accepted major, and require an FR-033 exact-target exit to leave it even across a disable/re-enable cycle.

#### F9 🟢 Whether plain init creates the `packages/` directory is ambiguous

- **Defect:** The §3.2 tree annotates `extensions/` as "optional … absent after plain init" but leaves `packages/` unannotated, implying it exists after init — yet an empty directory cannot be committed to Git, and FR-001/FR-002's "minimum scaffold" never enumerates directories. Fixture authors (FR-002's filesystem assertions) need the exact scaffold contents.
- **Evidence:** §3.2 tree, FR-001/FR-002, and FR-034; no statement defines the initial directory set.
- **Fix:** Annotate `packages/` the same way as `extensions/` (created on first package-local materialization), or state the minimum scaffold explicitly as exactly the three TOML files.

## Round 3

**Review target state:** commit `0093a87` (`docs(v5): resolve control-plane round-two review`, spec rev 0.3)

### Verdict

**APPROVE** — converged. Both round-2 findings are resolved and verified in the rev 0.3 text, the full `0093a87` diff (79 insertions, 66 deletions) was reviewed for fix-induced regressions, both repo validators pass, and this round produced no 🔴 and no new 🟡 findings. One optional 🟢 remains; it does not block approval.

### Method

Reviewed the complete rev 0.3 diff, verified each round-2 fix against the current text and the workflow's evidence standard, adversarially checked the new lock-partition machinery for the same class of second-order gap that round 2 found in round 1's fixes (state interactions: enabled/disabled × track present/absent × track available/unavailable × catalog promotion), and re-ran `project-standards spec validate` (OK) and `validate-frontmatter` (31 files pass).

### Prior-finding verification

| Finding | Status | Evidence in rev 0.3 |
| --- | --- | --- |
| F8 🟡 disable/re-enable vs accepted-major track | **Resolved** | The lock is restructured into separate enabled-package applied and persistent `accepted_tracks` partitions (FR-006, DR-003, §9 example now shows `[accepted_tracks.markdown-frontmatter]` with `major`/`authorized_catalog` and drops `track_major`/`major_authorized` from the applied record). FR-010 retains the track on disable; FR-014 makes it survive disablement; FR-033 defines record replacement/removal and exit-after-disable; FR-032 forbids reconstructing authorization history in lock repair; new AW-011 (re-enable resumes the track), EC-004 extended to re-enable, and glossary/C-006/D-005/D-007/D-013/OQ-007/OQ-009/OQ-015/§12.3/§18.2/§18.4/DoD/traceability/milestones/Appendix B.2 all updated coherently. The fix even covers the case I did not ask about: EC-017 fails closed (never falls back to the default) when a retained track's major has no compatible version in the current catalog, with ERR-002 extended to match. |
| F9 🟢 `packages/` scaffold ambiguity | **Resolved** | FR-001 now requires exactly three regular files; FR-002 forbids any other path and requires failed-init cleanup of the transient directory (mirrored in NFR-009); the §3.2 tree annotates both optional directories as created only when needed, and the narrative states plain init creates only the directory and three TOML files; OQ-003, the DoD, success evaluation, and MS-1 all match. |

### Consistency checks on the new machinery (held)

- The two-partition lock example matches DR-003's field constraints exactly (standard ID as key, non-default major, authorizing catalog lineage).
- FR-033's "changing that exact selector back to `latest` on the already recorded major shall require no further authorization" is consistent in both exit directions: after a non-default transition the replaced record scopes `latest`; after exit-to-default the record is gone and `latest` resolves the default naturally.
- The redefined `Initialized` state (fresh three-file plane, no records) does not orphan any repository condition: a fully disabled repo with retained tracks lands in `Reconciled`, whose definition now includes authorization state.
- Traceability remains complete after the row reshuffle: IR-002 moved from the FR-017 row into the FR-007–FR-010 row; every FR/NFR/IR/DR/ERR ID still has a verification row.
- Abandoning a track without reinstalling is expressible: FR-033 permits exact-target exit "even after disablement", with matching acceptance coverage ("exact exit before/after disable").

### New findings

#### F10 🟢 `authorized_catalog` has no consuming requirement

- **Defect:** DR-003 and the §9 example require the accepted-track record to carry "authorizing catalog lineage" (`authorized_catalog = '5'`), but no requirement, edge case, or workflow reads that field — FR-015 normalization compares the track's major against the new catalog's default and never consults it. An implementer cannot tell whether it is audit-only metadata or an input to some check.
- **Evidence:** Searched rev 0.3 for uses of the field; it appears only in DR-003 and the §9 example/narrative.
- **Fix:** Add one sentence to the §9 lock narrative (or DR-003) stating its role — e.g., audit evidence for diagnostics and migration reports, not a resolver input.

### Round-to-round tracking

| Round | 🔴 | New 🟡 | New 🟢 | Verdict |
| --- | --- | --- | --- | --- |
| 1 | 0 | 5 | 2 | APPROVE AFTER REVISION |
| 2 | 0 | 1 | 1 | APPROVE AFTER REVISION — all round-1 findings resolved; not converged (one new 🟡) |
| 3 | 0 | 0 | 1 | **APPROVE — converged** (no 🔴, no new 🟡; F10 is optional polish) |
