### Executive summary

Claude Code’s corrections resolved the major contract issues around consumer validation vs. template-maintainer validation, non-vacuous discovery, hard/advisory rule placement, Light traceability, JSON shape, and documented template guarantees. Significant findings remain, but they are now narrow: two stale/contradictory wording remnants from the prior findings and one new validation-contract gap around real `spec_id` format.

New internet research was limited to rechecking the uv build-backend packaging assumption. Official uv docs still support placing Markdown templates under the Python module tree and verifying wheel inclusion after implementation.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md
* Prior audit issue count: 7
* Resolved issue count: 5
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised spec and retested all prior findings against current repository evidence: `project-spec` README/tooling notes/templates, `check_specs.py`, current CLI dispatch, config loading, workflow patterns, pyproject packaging, and current git state. I attacked the corrected acceptance criteria for false positives around template sentinels, zero-file CI success, ID registry integrity, Light traceability, JSON output, config shape, wheel packaging, and maintainer-script retirement.

I could not run the preferred `uv run` validation path in read-only mode because it may create or update environments/caches. A direct `python3` attempt was refused by the local wrapper and told me to use `uv run`.

### Prior findings status

#### SA-001: Consumer `validate` conflicts with template sentinel semantics

* Previous severity: High
* Current status: Partially resolved
* Evidence: The revised spec now clearly separates consumer `validate` from maintainer-mode template validation at lines 107, 112, 123, 128, 132, 207, 212, and 218. Consumer `validate` rejects `SPEC-____`; maintainer tests expect it. However line 48 still says `check_specs.py` per-file checks are subsumed by “running the real `validate` over the templates,” which contradicts the corrected maintainer-mode contract.
* Remaining action for Claude Code: Replace line 48’s “real `validate` over the templates” wording with “maintainer-mode tests over the shared parser/core.”

#### SA-002: Missing or empty `spec:` discovery behavior is undefined

* Previous severity: High
* Current status: Resolved
* Evidence: Lines 179-188 now define no-arg behavior for missing `spec:`, zero-match include sets, explicit paths, and exit `2` for configuration/invocation errors. Testing and acceptance cover these at lines 210 and 220.
* Remaining action for Claude Code: None.

#### SA-003: ID registry and uniqueness rules are split between hard and advisory checks

* Previous severity: High
* Current status: Resolved
* Evidence: Lines 123 and 128 move duplicate IDs, undeclared prefixes, tier-invalid prefixes, and Appendix-A compatibility into hard `validate`; lines 207-218 require invalid fixtures and acceptance coverage.
* Remaining action for Claude Code: None.

#### SA-004: Approved Light traceability is underspecified

* Previous severity: Medium
* Current status: Resolved
* Evidence: Line 130 defines Light-profile traceability behavior: no §17.3 matrix failure; approved Light specs are checked against §17.1 items. Lines 208 and 219 add test/acceptance coverage.
* Remaining action for Claude Code: None.

#### SA-005: `--json` is required but its schema is not specified

* Previous severity: Medium
* Current status: Resolved
* Evidence: Lines 136-164 now freeze the JSON shapes for `validate`, `lint`, `extract`, and `next`, including file, finding, severity, line, locus, selector, kind, found, markdown, and next-id fields. Exact per-check code spellings are left to the plan, but the shape and namespace are now specified enough for planning.
* Remaining action for Claude Code: None.

#### SA-006: Documented template interchangeability guarantees are not preserved or retired

* Previous severity: Medium
* Current status: Resolved
* Evidence: Lines 114, 223, and 241 explicitly require demoting the two previously unenforced `tooling-notes.md` guarantees instead of silently deleting `check_specs.py`.
* Remaining action for Claude Code: None.

#### SA-007: Config-surface wording references a non-existent `files:` config

* Previous severity: Low
* Current status: Partially resolved
* Evidence: Line 177 correctly names `markdown.frontmatter.include/exclude`, matching `.project-standards.yml` and `validate_frontmatter.load_config`. But line 49 still says “frontmatter validator’s `files:` config,” and it appears in the locked decisions section.
* Remaining action for Claude Code: Replace line 49’s `files:` wording with `markdown.frontmatter.include/exclude`.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-001: Consumer `spec_id` real-ID validation is not explicitly required

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Acceptance could pass while `validate` rejects only `SPEC-____` but accepts another malformed `spec_id`, weakening G7’s typed frontmatter guarantee.
* Spec reference: Lines 98, 123, 207, and 218.
* Finding: The spec requires frontmatter key-set/order, enum checks, and sentinel rejection, but it does not explicitly require real consumer `spec_id` values to match `^SPEC-[0-9A-Z]{4}$`.
* Repository evidence: `standards/project-spec/resources/tooling-notes.md` lines 175 and 192 define the real `spec_id` pattern and explain why `SPEC-____` is intentionally invalid. `standards/project-spec/README.md` line 74 defines G7 as typed frontmatter/lifecycle with a sentinel that fails until filled in. The templates’ line 2 comments repeat the base36 real-ID contract.
* External research evidence: Not applicable.
* Why it matters: A consumer spec with `spec_id: foo` or `SPEC-123` could satisfy the revised acceptance criteria if the implementation only checks “not the sentinel.” That would create invalid IDs in a field meant to be stable and referenceable.
* Recommended action for Claude Code: Add real `spec_id` pattern validation to the hard `validate` contract and acceptance criteria.
* Suggested validation: Add invalid fixtures for malformed `spec_id` values such as `SPEC-123`, `SPEC-12_4`, and `foo`, plus a valid `SPEC-7F3Q` fixture.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: `extract` selector disambiguation is still deferred to the plan.
  * Why it matters: Duplicate or partial heading matches could produce non-deterministic slices.
  * Recommended clarification: Either define disambiguation in the spec or require the plan to choose deterministic `exit 2` ambiguity behavior before implementation.
  * Blocking or non-blocking: Non-blocking.

* Ambiguity: `validate-specs.yml` input surface is still deferred.
  * Why it matters: Existing reusable workflows expose `config-path` and `standards-ref`; omitting those could create a less reproducible consumer workflow.
  * Recommended clarification: Mirror the existing workflow’s `config-path` and `standards-ref`, and define strict-lint as an explicit opt-in.
  * Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: uv documentation — Build backend
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-07-05
* What it was used to verify: Current `uv_build` wheel file-inclusion behavior for Markdown templates placed under `src/project_standards/specs/templates/`.
* Relevant conclusion: uv includes the module tree in wheels by default and says data files should live under the module root or configured data directories. This supports the spec’s packaging approach, with the planned wheel-inclusion check still required.

### Read-only validation performed

* `pwd`: confirmed repository root `/home/chris/projects/project-standards`.
* `git status --short`: confirmed `docs/superpowers/specs/README.md` is modified and the audited spec plus prior review doc are untracked.
* `git branch --show-current`: confirmed branch `testing`.
* `git log --oneline -n 10`: confirmed recent `project-spec` commits and session context.
* `nl -ba` on the spec: re-inventoried revised requirements, acceptance criteria, non-goals, and open questions.
* `nl -ba` / `rg` on `standards/project-spec/README.md`, `resources/tooling-notes.md`, templates, and `check_specs.py`: checked sentinel, ID, profile, traceability, and maintainer-validation claims.
* `nl -ba` / `rg` on `.project-standards.yml`, `src/project_standards/cli.py`, `validate_frontmatter.py`, `pyproject.toml`, and workflows: checked config shape, dispatch pattern, package layout, and reusable workflow precedent.
* `rg --files` and targeted `rg -n`: discovered relevant repo files and references.
* `git diff --stat`, `git diff --name-status`, and `git diff -- docs/superpowers/specs/README.md`: confirmed tracked local change is only the specs index entry.
* `git ls-files --error-unmatch`: confirmed `check_specs.py` is tracked and the audited spec is not yet tracked.
* `python3 standards/project-spec/resources/check_specs.py standards/project-spec/templates`: attempted read-only direct validation; local wrapper refused and required `uv run`, which I did not run in read-only mode.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: build a wheel and verify `project_standards/specs/templates/*.md` is included.
* Run only after implementation: exercise `project-standards spec validate|lint|extract|next --json` against valid and invalid fixtures.
* Run only after implementation: test malformed `spec_id` fixtures in consumer `validate`.
* Run only after implementation: test reusable `validate-specs.yml` for missing config, empty config, valid config, strict-lint opt-in, and pinned `standards-ref`.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md
* Audit round: 2
* Open issue IDs: SA-001, SA-007, SA-NEW-001
* Resolved issue IDs: SA-002, SA-003, SA-004, SA-005, SA-006
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: removing the stale `real validate over templates` and `files:` wording, and adding explicit real `spec_id` pattern validation to the hard consumer `validate` contract