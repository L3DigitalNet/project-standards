### Executive summary

Claude Code’s round-2 corrections resolve the six prior findings by adding an explicit upgradeability precheck, switching to canonical subsection insertion, clarifying Appendix A/D replacement safety, separating the atomic write helper from `new`’s write policy, removing config coupling, and adding package CLI docs to scope.

Significant findings still remain. The revised spec newly makes Appendix B part of the canonical precheck, but the transformation model does not classify or replace Appendix B even though the Light, Standard, and Full templates differ there. That leaves the “template-faithful” guarantee under-specified and likely false as written. New internet research was limited to rechecking the Python filesystem assumptions used by the write model; no stale external-doc conflict was found.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md
* Prior audit issue count: 6
* Resolved issue count: 6
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 3
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised spec and retested the prior issue areas against repository evidence: validator guarantees, template structure, CLI/write helper behavior, config coupling, docs scope, bundled-template parity, and release/versioning claims. I specifically attacked the revised upgradeability precheck, the source-as-spine splice, ownership classification, Appendix replacement rules, fixture-fidelity acceptance criteria, JSON/error contracts, and write-model external assumptions.

I did not run mutating gates such as pytest, coverage, ruff, basedpyright, pip-audit, or any command that would create implementation artifacts.

### Prior findings status

#### SA-001: `validate` does not prove the load-bearing “no author gap content” invariant

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec now states that `validate` does not guarantee the invariant and adds an explicit upgradeability precheck that refuses gap prose before splicing.
* Remaining action for Claude Code: None for the prior gap-content issue; account for SA-NEW-001 before planning.

#### SA-002: Already-present subsections can be valid but break the proposed insertion order

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec now refuses non-canonical subsection membership before splicing and specifies canonical numeric insertion rather than “after the last present subsection.”
* Remaining action for Claude Code: None for the prior subsection-order issue.

#### SA-003: Template-owned Appendix A/D replacement can silently delete validate-clean author content

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec requires Appendix A/D to byte-match the source-tier template before replacement, and says edited Appendix A/D sources are refused as `source_not_upgradeable`.
* Remaining action for Claude Code: None for Appendix A/D; Appendix B is a separate new issue.

#### SA-004: “Reuse `_write_new_file` verbatim” conflicts with upgrade’s own write and JSON contract

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec now calls for extracting a `_safe_atomic_write` primitive while keeping upgrade-specific overwrite policy and JSON payloads in `_run_upgrade`.
* Remaining action for Claude Code: None.

#### SA-005: `config_error` is specified without a config surface or clear need

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec explicitly says `upgrade` has no `--config`, reads no repo config, and removes `config_error` from the upgrade slug set.
* Remaining action for Claude Code: None.

#### SA-006: Documentation impact omits the package CLI reference

* Previous severity: Low
* Current status: Resolved
* Evidence: The revised docs-impact section adds `src/project_standards/README.md` and top-level CLI help text to the implementation scope.
* Remaining action for Claude Code: None.

### New blocking issues

#### SA-NEW-001: Appendix B is checked as canonical but not transformed to the target tier

* Severity: High
* Status: Confirmed
* Adversarial angle: Can the source-as-spine splice produce a target-template-faithful output if Appendix B differs by tier but is neither classified as template-owned nor replaced?
* Spec reference: Lines 61, 71, 166-171, 175-177, 264, and 275-276.
* Finding: The revised precheck says Appendices A/B/D must byte-match the source-tier template, but the ownership and transformation rules only make Appendix A and Appendix D template-owned and replaced from the target tier. Appendix B is always present in all tiers, so it is not “missing”; if it remains source-owned, a Light→Standard or Standard→Full upgrade preserves stale lower-tier Appendix B prose and cannot satisfy U3/template-fidelity. If it is intended to be target-owned, the spec does not say so and does not test edited Appendix B refusal.
* Repository evidence: `standards/project-spec/templates/spec-light-template.md` Appendix B differs from Standard: Standard adds background/reference reading scope, constraints/design constraints preservation, §17.3 traceability, milestone ordering, and different completion-report wording. Standard Appendix B also differs from Full in prohibited dependency/example wording. Bundled templates match standards templates (`cmp -s` returned 0 for light, standard, full), so this is the actual shipped template contract.
* External research evidence: Not applicable.
* Why it matters: Claude Code could implement the spec literally and preserve Light Appendix B in a Standard output, leaving stale agent instructions while still possibly passing `validate`. Conversely, replacing Appendix B would be reasonable but is not specified in the ownership table, error examples, tests, or non-goals. This blocks reliable planning because the central U3 byte-for-byte fidelity criterion depends on Appendix B behavior.
* Recommended action for Claude Code: Decide and state Appendix B ownership. The repository evidence points toward treating Appendix B as template-owned like Appendix A/D: precheck source Appendix B byte-matches the source-tier template, replace it wholesale from the target-tier template, refuse edited Appendix B with `source_not_upgradeable`, and add Appendix B to the error/test/non-goal examples.
* Suggested validation: Add tests that Light→Standard and Standard→Full outputs contain the target-tier Appendix B exactly, that edited Appendix B is refused before splicing, and that aligned-fixture U3 equality covers Appendix B.

### New non-blocking issues

#### SA-NEW-002: `source_not_upgradeable` is omitted from the JSON-specific test list

* Severity: Low
* Status: Confirmed
* Adversarial angle: Can the implementation satisfy the enumerated JSON tests while leaving the new central precheck failure unverified under `--json`?
* Spec reference: Lines 257, 264, 269, and 278-279.
* Finding: The spec adds `source_not_upgradeable` as a frozen JSON code and tests precheck refusal generally, but the JSON-specific bullet enumerates success, `source_invalid`, `not_upgradeable`, `exists`, and `self_validation_failed` without naming `source_not_upgradeable`.
* Repository evidence: Existing `spec new` tests freeze individual JSON slugs, and the revised upgrade spec treats JSON as a universal tooling contract.
* External research evidence: Not applicable.
* Why it matters: This is the new safety gate introduced to resolve the prior high-severity findings. Its machine-readable failure shape should be pinned directly so CI/agents do not get a human-only or malformed refusal.
* Recommended action for Claude Code: Add `source_not_upgradeable` to the JSON test matrix explicitly.
* Suggested validation: Assert `--json` on gap prose, edited Appendix A/D/B, and non-canonical subsection sources emits exactly one JSON object with `ok: false`, `code: "source_not_upgradeable"`, and a useful deviation description.

#### SA-NEW-003: Stale internal anchor remains after renaming the load-bearing section

* Severity: Low
* Status: Confirmed
* Adversarial angle: Does the revised spec’s own cross-reference still resolve after the section rename?
* Spec reference: Line 53.
* Finding: The text still links to `#the-load-bearing-invariant`, but the section was renamed to “The load-bearing property — enforced, not assumed,” whose current table-of-contents anchor is `#the-load-bearing-property--enforced-not-assumed`.
* Repository evidence: The spec’s TOC points to the new anchor at lines 12 and 63; line 53 retains the old anchor.
* External research evidence: Not applicable.
* Why it matters: This does not block implementation, but it is a broken self-reference in the spec’s key rationale section.
* Recommended action for Claude Code: Update the stale link target and visible text.
* Suggested validation: Run the repository’s normal Markdown/link checks after implementation if available.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Is Appendix B template-owned during upgrade, author-owned, or preserved only if canonical?
* Why it matters: The tier templates differ materially in Appendix B, and U3 target-fidelity cannot be evaluated without this rule.
* Recommended clarification: Treat Appendix B consistently in the precheck, ownership table, transformation pass, error examples, tests, and non-goals.
* Blocking or non-blocking: Blocking

### Internet research performed

* Source name: Python documentation, `os.replace`
* URL: https://docs.python.org/3/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: Atomic replacement assumption in the write model.
* Relevant conclusion: Official docs state successful same-filesystem replacement is atomic and existing file destinations are replaced when permissions allow.

* Source name: Python documentation, `pathlib.Path.mkdir`
* URL: https://docs.python.org/3/library/pathlib.html#pathlib.Path.mkdir
* Access date: 2026-07-05
* What it was used to verify: Parent auto-creation behavior.
* Relevant conclusion: Official docs confirm `parents=True` creates missing parents and `exist_ok=True` still fails if an existing component is not a directory.

* Source name: Python documentation, `pathlib.Path.samefile`
* URL: https://docs.python.org/3/library/pathlib.html#pathlib.Path.samefile
* Access date: 2026-07-05
* What it was used to verify: Availability of same-file checks for `-o OUT == SRC`.
* Relevant conclusion: `Path.samefile` remains available; the spec’s fallback for missing `OUT` is still appropriately left to implementation planning.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`: found one untracked prior review artifact under `docs/codex-reviews/`; no tracked working-tree edits were reported.
* `git branch --show-current`: confirmed branch `testing`.
* `git log --oneline -n 10`: confirmed the latest commit is the round-2 spec revision.
* Inspected the revised spec with `nl -ba` and `sed`: re-inventoried decisions, precheck, splice ownership, write model, error/JSON contract, testing, acceptance criteria, and docs impact.
* `git show --unified=80`: compared the round-2 spec commit against the prior version and confirmed intended SA-001..006 corrections.
* `rg --files`: identified relevant source, templates, fixtures, tests, docs, workflows, and metadata.
* Inspected `specs/cli.py`, `commands/new.py`, `document.py`, `validate.py`, and `registry.py`: checked current command surface, reusable write helper behavior, parser/validator guarantees, and registry-derived tier structure.
* Inspected project-spec templates and fixtures: confirmed actual section/appendix layout and Appendix B tier differences.
* Ran `diff -u` on Appendix B across Light/Standard and Standard/Full templates: confirmed Appendix B is tier-variant.
* Ran `cmp -s` for bundled vs standards templates: confirmed bundled light, standard, and full templates match the standards templates.
* Inspected `standards/project-spec/README.md`, `TODO.md`, `meta/versioning.md`, `src/project_standards/README.md`, and `src/project_standards/cli.py`: checked v1-core status, versioning classification, and package docs/help claims.
* Consulted official Python docs for `os.replace`, `Path.mkdir`, and `Path.samefile`.

### Recommended planning/implementation validation

* Run only after implementation: targeted `tests/test_spec_upgrade.py` covering Appendix B target replacement, edited Appendix B refusal, gap-content refusal, modified Appendix A/D refusal, non-canonical subsection refusal, canonical subsection insertion, aligned-fixture fidelity, and output validation.
* Run only after implementation: targeted `tests/test_spec_upgrade_cli.py` covering flag conflicts, all JSON slugs including `source_not_upgradeable`, in-place mode preservation, output overwrite behavior, symlink/non-regular refusals, parent auto-creation, output-equals-source checks, and no-write preview.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: dogfood `project-standards spec upgrade` preview output piped into spec validation without writing repository files.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md
* Audit round: 2
* Open issue IDs: SA-NEW-001, SA-NEW-002, SA-NEW-003
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: whether Appendix B ownership and transformation are specified consistently across the precheck, splice ownership table, replacement pass, tests, and acceptance criteria; then verify the new `source_not_upgradeable` JSON coverage and stale anchor correction.