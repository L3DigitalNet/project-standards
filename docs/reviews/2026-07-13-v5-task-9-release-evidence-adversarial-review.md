# V5 Task 9 Release Evidence Adversarial Review

## Verdict

**Ready.** A read-only Claude Opus review found no Critical, High, or Medium defect in the refreshed Task 9 evidence, release plan, checker-materialization design, Frontmatter bootstrap contract, Project Spec unified workflow, or executable two-path proof.

The review treated CTM-NEW-017 as the active Frontmatter release-bootstrap authority. Earlier remove-and-compose wording in CTM-NEW-010/011 is historical and superseded only for explicit local mode.

## Scope

- `docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md`
- Task 9 and Task 11 in `docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md`
- CTM-NEW-017 and current integration/acceptance text in `docs/superpowers/specs/2026-07-12-python-tooling-checker-table-materialization-design.md`
- `tests/package_compatibility/release_candidate.py` and `test_release_candidate.py`
- Markdown Frontmatter 1.2 and Project Spec 1.1 package authority

The reviewer had `Read`, `Grep`, and `Glob` tools only. Repository writes and external research were disabled.

## Confirmed release-critical facts

- Explicit Frontmatter local mode preserves the recognized reusable endpoint byte-for-byte during preliminary migration and composes `validate-standards.yml` as a same-commit local caller.
- Project Spec selects the installed self-host workflow and invokes unified `spec validate` / `spec lint --strict` commands without a legacy config override.
- The retained prose ledger and machine-readable ledger are identical, and the quoted migration, release-input, guard, and control-plane digests agree with the record.
- The release proof fails closed on unclassified legacy authority, whole-file shared-container retirement, mismatched guard inputs, partial workflow cohorts, and evidence-record mismatch.
- The fast evidence check validates currency and record structure; the serial two-path `release_replay` proof binds every recorded value to executed migration output.

## Finding dispositions

| ID | Severity | Disposition |
| --- | --- | --- |
| OR-001 | Low | Fixed. The implementation-plan prerequisites now name CTM-NEW-017 and its bootstrap-safe local-endpoint contract. |
| OR-002 | Low | Fixed. CTM-NEW-010/011 now carry inline supersession notes for their historical Frontmatter removal clauses. |
| OR-003 | Low | Fixed in the Task 11 contract. The plan now requires a concrete oracle for the rewritten unified v5 Frontmatter endpoint, its public inputs/defaults, absence of legacy authority, and local root caller. |
| OR-004 | Low | Fixed operationally. Task 10 and `meta/versioning.md` explicitly require the complete serial `release_replay` proof before tag or publication. |

No finding was rejected, deferred, or risk-accepted.

## Required final check

After these non-evidence dispositions are included in the release-input digest, rerun:

```bash
uv run pytest tests/package_compatibility/test_release_candidate.py -q
```

The retained record is current only when the fast currency check and the executable two-path proof pass together against the final pre-atomic checkpoint.
