# Python Tooling Root-Authority Reconstruction Backtrack Audit

## Executive summary

The release-integration contract in the [checker-table materialization design](../../superpowers/specs/2026-07-12-python-tooling-checker-table-materialization-design.md) and Tasks 9 and 11 of the [parallel coverage implementation plan](../../superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md) were re-audited after initial Task 9 implementation exposed an incomplete predecessor overlay.

**Final verdict: Ready.** The design now defines complete root-authority reconstruction as CTM-NEW-008, superseding CTM-NEW-007's legacy-signature-only union. The implementation plan is executable without another owner-level decision. No CP01 or BA02 contract backtrack is required.

This audit supersedes only the frozen-overlay and post-atomic-reconstruction conclusions in the [2026-07-13 00:09 Task 9/11 audit](2026-07-13-0009-python-tooling-parallel-coverage-task-9-11-plan-audit.md). That audit remains authoritative for its unchanged installed-provider, Pyright, and release-sequencing findings.

## Historical baseline

- `26fb984835fdaf66f33174c7138a3250bda689aa` is the named post-checker, pre-atomic fixture authority in the plan.
- `d5c8031fc17df8b5217608f6f9ad8af08cb8fbe1` is the literal commit immediately before Task 9 began.
- `git diff 26fb984 d5c8031 -- <31 overlay paths>` is empty. The named fixture authority and the exact pre-Task-9 commit therefore provide identical bytes and absences for every reconstructed path.
- Every frozen file or absence is sourced from the `26fb984` Git tree. The executable Agent Handoff hook retains mode `100755`; the other newly frozen files retain mode `100644`.

## Root-cause finding

The earlier exact union covered catalog-5 legacy-signature targets plus `.project-standards.yml`, `pyproject.toml`, and `uv.lock`. Legacy signatures describe prior authority; they do not enumerate every non-signature root output a selected v5 payload can materialize. Reconstructing from a completed migrated tree could therefore leak v5 outputs and produce a different predecessor and release patch.

CTM-NEW-008 closes the authority set over all nine catalog-5 package identities:

1. every legacy-signature target;
2. every non-`.standards/` artifact or contribution target with at least one non-`create-only` declaration; and
3. `.project-standards.yml`, `pyproject.toml`, and `uv.lock`.

The live-preserved set is every non-`.standards/` target whose declarations are all `create-only`, minus that complete overlay union. This subtraction keeps create-only legacy targets in the frozen overlay. All `.standards/**` paths remain outside the overlay because reconstruction removes that directory wholesale.

The live derivation yields 31 overlay paths: 25 frozen files and 6 frozen absences. Its six additions over the former union are:

| Path                                                     | State at `26fb984`  |
| -------------------------------------------------------- | ------------------- |
| `.agents/hooks/agent-handoff/session_start.py`           | file, mode `100755` |
| `.agents/skills/agent-handoff/SKILL.md`                  | file, mode `100644` |
| `.agents/skills/agent-handoff/agents/openai.yaml`        | file, mode `100644` |
| `.agents/skills/markdown-frontmatter/agents/openai.yaml` | absent              |
| `.claude/settings.json`                                  | file, mode `100644` |
| `.github/workflows/validate-standards.yml`               | absent              |

Ten all-`create-only`, nonlegacy targets remain live-preserved: `docs/STATUS.md`, `docs/TODO.md`, and the eight selected Agent Handoff knowledge/state paths. The proof requires each to be a nonsymlink regular file and byte-identical through migration.

## Reconciled execution findings

| ID | Severity | Resolution |
| --- | --- | --- |
| RA-001 | Release blocker | Replaced the legacy-signature-only overlay with CTM-NEW-008's complete root-authority closure. |
| RA-002 | High | The post-atomic source is now the first completed migrated authority tree, not a hand-built approximation; both reconstructed predecessors must be byte-identical before digest comparison. |
| RA-003 | High | Snapshots, mirroring, post-atomic capture, and replay now use Git-known current paths. `.git/**` and ignored `.venv`, cache, bytecode, and coverage artifacts cannot enter release identity or overwrite a replay repository. |
| RA-004 | High | Human ownership-relinquishment evidence is asserted through `render_migration_report`; the ordinary human CLI remains an action/finding view and is not required to expose claim fields. |
| RA-005 | Medium | Task 9 now stages both CP01 and BA02 evidence-only revisions and finalizes all non-evidence documentation before calculating `release_input_digest()`. |
| RA-006 | Medium | Retained evidence regeneration now covers the procedure, changed-path ledger, workflow-preservation facts, and all executed digests instead of updating hashes alone. |
| RA-007 | Medium | Both lock refresh and lock currency checks run offline; `uv lock --check --offline` was verified against the installed uv CLI. |
| RA-008 | Medium | Task 11 explicitly reviews the changelog, reusable-workflow defaults, README, every adoption guide, and the v4-to-v5 upgrade runbook before final evidence currency. |
| RA-009 | Low | Release patch and changed-path derivation disable rename detection; the stale catalog-matrix staging entry is removed. |
| RA-010 | Low | The plan explicitly subtracts the overlay from the all-`create-only` set and repairs the lock-command snippet indentation. |

## Evidence and specification timing

CP01 and BA02 remain unchanged during this plan audit. Their evidence-only revisions occur after the focused FR-037/FR-038 implementation proofs pass, but before the release-input digest is calculated. This ordering is mandatory: both specifications are release inputs, while the retained evidence file is the sole self-excluded input. Revising either specification after evidence refresh would immediately stale the proof.

Task 9 still owns executable implementation, retained evidence, specification traceability, status, TODO, and handoff updates. Task 11 still owns the atomic live-root transition. This report makes no implementation-completion or release-readiness claim.

## Independent delta checks

- A user-authorized Fable review found the incomplete overlay to be a release blocker and confirmed that a design-level reconstruction correction, not a CP01 or BA02 requirement change, was required.
- A user-authorized Fable `xhigh` delta audit independently recomputed the 31-path closure and returned Ready after identifying bounded offline, release-file-enumeration, subtraction, and formatting corrections.
- Separate implementation-focused reviews independently derived the 31 required and 10 live-preserved paths, verified the historical file states and modes, and caught the Git/runtime-artifact and human-report execution gaps.
- A final read-only delta check returned Ready with every finding explicitly closed in the amended design and plan.

## Validation

The amended documents pass:

```bash
git diff --check
npx prettier --check docs/superpowers/specs/2026-07-12-python-tooling-checker-table-materialization-design.md docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
npx markdownlint-cli2 docs/superpowers/specs/2026-07-12-python-tooling-checker-table-materialization-design.md docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
python /home/chris/.agents/skills/technical-writer/scripts/docctl.py validate docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
uv run project-standards validate --config .project-standards.yml
uv lock --check --offline
```

No Task 9 implementation test is credited by this plan-only closeout. The incomplete uncommitted fixture and helper remain implementation work and must be brought forward under CTM-NEW-008 before the executable release proof can pass.
