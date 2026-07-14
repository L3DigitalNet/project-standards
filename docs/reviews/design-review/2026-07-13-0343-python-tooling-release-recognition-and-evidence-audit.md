# Python Tooling Release Recognition and Evidence Audit

## Executive summary

The first executable Task 9 migration preview was recovered from the exact pre-task history, run against the frozen v5 predecessor, and used to audit the remaining release contracts in the [checker-table materialization design](../../superpowers/specs/2026-07-12-python-tooling-checker-table-materialization-design.md) and [parallel coverage implementation plan](../../superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md).

**Final review verdict: Ready after CTM-NEW-009 through CTM-NEW-016 reconciliation; the six-contract implementation recheck is approved.** The frozen predecessor remains commit `26fb984835fdaf66f33174c7138a3250bda689aa`; no baseline was moved to hide a migration failure. CTM-NEW-009 through CTM-NEW-013 close exact-signature, classifier, preserved-container, task-alignment, and comparator-schema gaps exposed by the preview. CTM-NEW-014 separates Task 9's migration patch from Task 11's canonical complete atomic release-content patch. CTM-NEW-015 corrects the pre/post-atomic root-gate boundary, and CTM-NEW-016 hardens self-contained Git authority, canonical diffing, framed input hashing, independent residual proof, and retained-record binding.

This is a contract and scoped implementation-review verdict, not a Task 9 proof-completion claim. Task 9 completion is governed by the retained slow-proof record; Tasks 10 and 11, tagging, publication, and deployed-truth reconciliation remain separate gates.

## Recovery baseline

- `d5c8031fc17df8b5217608f6f9ad8af08cb8fbe1` is the literal commit immediately before Task 9 began.
- `26fb984835fdaf66f33174c7138a3250bda689aa` is the named post-checker, pre-atomic fixture authority.
- The complete 31-path overlay derives from all catalog-5 legacy targets, every non-`.standards/` non-create-only materialization target, and the three pinned authority inputs. Its 25 files and 6 absences were verified against the named Git tree, including file modes.
- The current branch already contains the four reviewed pre-Task-9 commits through `9a04329`; the uncommitted tree is the continuing Task 9 scope, not work that must be replayed.

## Reconciled findings

| ID | Severity | Resolution |
| --- | --- | --- |
| CTM-NEW-009 | Critical | Added the release-current `AGENTS.md` digest to Python Tooling history and preservation requirements and added the already-known release-current `CLAUDE.md` digest to preservation. The proof forbids Python Tooling whole-file retirement while explicitly allowing Agent Handoff's exact legacy bounded-block retirement. |
| CTM-NEW-010 | High | Appended the frozen package-owned workflow and instruction digests without replacing older known history. Consumer-owned `check.yml` remains intentionally unknown and is preserved through its raw intent binding without an action or lock. |
| CTM-NEW-011 | High | Defined historical and current self-host classifier cohorts. Markdown Tooling accepts either complete generation and rejects partial or cross-generation pairs; Project Spec accepts both historical and current self-host digests. |
| CTM-NEW-012 | High | Added a second installed-provider-derived, fail-closed guard for `.vscode/tasks.json` `keyed-set:/tasks#label=check`, including exact source/task/post-alignment facts, sibling preservation, mutation-required behavior, and no-write negatives. |
| CTM-NEW-013 | Medium | Corrected only the unpublished Python Tooling `additional_dev_dependencies` item grammar needed for comparator-bearing requirements and required all four affected package integrity chains to refresh together. |
| CTM-NEW-014 | Critical | Bound Task 11 to a clean recorded pre-atomic Git object tree and a canonical complete release-content patch. Only the self-referential retained evidence file is excluded; binary replay and the committed parent-to-release diff must reproduce the recorded paths and digest before tag or publication. |
| CTM-NEW-015 | High | A literal migrated-root gate passed Ruff/BasedPyright and 2,586 tests, then failed 96 root expectations that intentionally remain pre-atomic until Task 11. Task 9 now proves the exact script through installed rendering, both complete scratch gates, and locked sync; Task 11 executes the real root gate only after its atomic expectation changes. |
| CTM-NEW-016 | Critical | Sanitized every release Git subprocess and verified self-contained object stores; pinned canonical diff formatting; replaced ambiguous NUL input framing with domain-separated length prefixes; added an independent frozen-byte residual oracle; and bound one parsed machine record exactly to the slow proof's ledger, patch, guards, and control-plane digests. |

## Exact release-recognition facts

| Target | Frozen or derived SHA-256 | Required treatment |
| --- | --- | --- |
| `AGENTS.md` | `b7b00e3bf4a74e47a19418979925260f73098734c805148ee31384f3e6571b2b` | Append to `legacy-agents` and the release-current preserved set. |
| `CLAUDE.md` | `8c9ba6563c70ea051ad36f2054d41f36aa048ce61d813d100d4e7b25d5e05de0` | Retain in `legacy-claude`; add to the release-current preserved set. |
| `.vscode/settings.json` | `22f598ebf1f24e29041289891b3c56131f0acc4dddfed802d92a6a3802eab55f` | Already known and preserved. |
| Frozen `.vscode/tasks.json` | `8dcb4880139bb708bf20819479bcb7898bb5d1dabd8d79e43b7d64bb3e4b3b08` | Guard source; already known and preserved. |
| Guarded `check` task | `119597ceaea2647bae17e3261ad820bf1a7ffec997a33b431c9396797e03ff6d` | Provider-derived after-semantic digest and next-lock identity. |
| Post-alignment `.vscode/tasks.json` | `cf4aa30c3e2bfb1d69d0cfb7953d1e351db0e6ab06c5812f48cf9eface79a9f7` | Append to `legacy-vscode-tasks` and the release-current preserved set. |
| `.github/workflows/check.yml` | `9f4f90364b85af187ce7430a18d5e189389e5884157d74e8defc4d468cb13bdc` | Intentionally unknown; consumer-owned preserve claim; no action or lock. |

Older known Python Tooling whole-file signatures are deliberately not all preserved. Existing standard-owned V4/V1 histories must retain their removal-and-recomposition behavior; preservation is an exact release-current subset, not a synonym for known history.

## Workflow transition matrix

| Owner | Predecessor path | Required transition |
| --- | --- | --- |
| Python Tooling | `.github/workflows/check.yml` | Preserve unknown bytes through consumer-owned intent; never create a unit or lock entry. |
| Markdown Frontmatter | `.github/workflows/validate-markdown-frontmatter.yml` | Recognize and adopt the path as the immutable V5 self-host endpoint, then compose a same-commit local call at `.github/workflows/validate-standards.yml`. |
| Markdown Tooling | `.github/workflows/format.yml`, `.github/workflows/lint-markdown.yml` | Select self-hosted mode from one complete historical/current cohort and preserve the current frozen files byte-for-byte. |
| Project Spec | `.github/workflows/validate-specs.yml` | Select self-hosted mode from historical/current classifiers and replace the transitional root workflow in place with the immutable v5 self-host resource. |

This matrix replaces every earlier universal workflow-identity statement.

## Instruction-container proof

The root instruction files already contain the legacy Agent Handoff bounded block. A valid proof therefore cannot strip only the new Python Tooling block and compare the whole file with the predecessor.

For both `AGENTS.md` and `CLAUDE.md`, the executable proof must:

1. require the path to be absent from Python Tooling whole-file removal claims, `retired_targets`, and `legacy_removals`;
2. independently slice the sole frozen begin line through the end-line terminator, require the exact frozen prefix-plus-suffix residual, and then require each `retired_content` entry to equal it;
3. require that residual to omit both legacy markers and be smaller than the frozen predecessor;
4. require the applied file to begin with the exact `retired_content` residual;
5. require its suffix to consist only of adapter newline separators and one correctly bounded current envelope from each provider; and
6. require every current block body to be byte-identical to its installed-provider rendering.

## Complete atomic evidence boundary

Task 9 continues to prove the migration engine from pre-atomic and reconstructed post-atomic shapes. Its binary patch and changed-path ledger are retained as **migration patch** evidence.

Task 11 has a broader atomic scope. Before its first live mutation it records clean `PRE_ATOMIC_HEAD` and materializes that exact Git object tree as an independently committed predecessor repository. After migration, release-only documentation/metadata edits, cleanup, and the post-atomic gate, it derives the canonical **complete release-content patch** from that predecessor to the Git-known live tree.

The scratch predecessor index must initially equal its committed tree. After mirroring the final Git-known tree, intent-to-add marks every non-ignored addition so the canonical worktree diff includes new `.standards/**` and workflow paths without staging their content. A synthetic addition must appear in both patch and ledger and replay byte-for-byte; the later commit-to-commit verification remains read-only.

The complete patch contract is fail closed:

- binary diff and changed-path derivation use a minimal non-credential Git environment, self-contained object verification, and fully pinned diff formatting;
- retained release evidence is the only excluded path;
- a fresh predecessor copy replays the patch to exact path-, mode-, symlink-, and byte-aware equality with the final live tree under that one exclusion;
- the release-input digest is calculated from domain-separated, length-prefixed path/mode/kind/content records in the final live tree with the same evidence-only self-exclusion;
- the evidence file is then refreshed and its single machine-readable record must exactly equal the executed ledger, patch, two guard records, and control-plane digests without changing either digest;
- its validated SHA-256 must equal both the staged index blob and committed `HEAD` bytes under clean-worktree checks; and
- after the atomic commit, the parent-to-release commit diff under the same exclusion must reproduce the recorded complete ledger and digest before tagging or publishing.

This prevents Task 11's instruction, documentation, changelog, test, adoption, handoff, and metadata edits from being omitted from release evidence or leaked into reconstructed predecessor authority.

## Review provenance

- A completed user-authorized Fable `xhigh` audit produced CTM-NEW-009 through CTM-NEW-013 and returned **Revision Required**.
- Independent read-only repository audits then corrected instruction bounded-block semantics, Markdown Frontmatter's endpoint-adoption-and-composition transition, positional signature-test assumptions, historical/current classifier compatibility, and exact retirement-view assertions.
- A second Fable `xhigh` delta call was stopped at the user's rate-limit warning. It returned no verdict and is not counted as review evidence.
- The fully amended delta received an independent read-only adversarial review, including CTM-NEW-014's Git-object-tree, replay, self-exclusion, and post-commit verification contract.
- A final independent implementation review returned **Revision Required** on six high-severity proof gaps: missing locked/root execution claims, ambient Git authority, diff nondeterminism, ambiguous input framing, self-oracled instruction preservation, and unbound retained digests. Executable remediation produced CTM-NEW-015/016. The same reviewer then returned **Approved**, found no remaining Critical or High defect in those six contracts, and independently passed 12 focused regressions, Ruff, BasedPyright, and hostile `GIT_DIFF_OPTS`/`GIT_INDEX_FILE` canonical-hash probes.
- The first post-approval slow proof reached final migration-patch replay and exposed one narrow wiring defect: the copied replay snapshot lacked the committed Git baseline required by the hardened Git-known equality check. Replay now initializes the same predecessor baseline before applying the patch; a focused regression, Ruff, and BasedPyright pass, and the same reviewer approved the correction with no Critical or High concern.
- Per the user's standing direction, no future Fable call may exceed `xhigh`; the next Fable checkpoint is deferred until capacity is available before Task 11.

## Validation

The reconciled documents are validated with:

```bash
git diff --check
npx prettier --check docs/superpowers/specs/2026-07-12-python-tooling-checker-table-materialization-design.md docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
npx markdownlint-cli2 docs/superpowers/specs/2026-07-12-python-tooling-checker-table-materialization-design.md docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md
```

Implementation gates are credited only after fresh output. Task 9's code and focused gates cover the second guard, signature/classifier/preservation contracts, complete-patch helpers, all four package integrity refreshes, locked sync, two-path migration, and bound retained evidence. Task 10 may begin only after the slow proof and its retained machine record pass exact comparison.
