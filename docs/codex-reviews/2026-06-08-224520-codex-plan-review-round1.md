### Executive summary

The implementation plan needs correction before Claude Code executes it. The broad decomposition matches the approved spec and current repository shape, but several plan snippets would either let `project-standards fix` report success while reference validation still fails, silently tolerate duplicate YAML keys, or risk failing the strict `basedpyright` gate.

Internet research was required for the pre-commit and basedpyright assumptions, and to sanity-check PyYAML duplicate-key behavior.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-frontmatter-suite.md
* Significant findings remaining: Yes
* Blocking issue count: 3
* Non-blocking issue count: 3

### What the plan gets right

* The referenced plan/spec files exist and target the current `testing` branch state.
* The plan correctly identifies the existing `collect_paths`, `load_config`, `parse_frontmatter`, `validate_id`, workflow, and CLI integration points.
* The additive `references.enabled` config shape preserves the current consumer contract by defaulting off.
* The denylist, custom-schema skip concept, opt-in `updated` bump, and final toolchain gate are directionally aligned with repo conventions.

### Adversarial review performed

Performed claim inventory, falsification, blast-radius, failure-mode, validation-attack, external-assumption, and maintainability passes against the plan, approved spec, current source, schema, config, workflow, tests, and current git state. I specifically attacked CLI sequencing, custom-schema behavior, reference-validation coverage, duplicate YAML semantics, strict type-checking assumptions, pre-commit hook validation, and false-positive validation paths.

Could not execute the proposed implementation because this audit is read-only and the plan is not implemented yet.

### Blocking issues

#### CR-001: `project-standards fix` can skip the new reference gate

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation false positive / postcondition gap.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:1992`, `:2001`, `:2004`; spec intent at `docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:59`, `:176-178`.
* Finding: C2 hardcodes the final postcondition as `validate_frontmatter.main(fix_args)` plus `validate_id.main(fix_args)`, even though C1 extends `project-standards validate` to include `validate_references`. It also does not implement the spec’s “fix skips entirely under a custom schema” contract.
* Repository evidence: Current `src/project_standards/cli.py:136-185` early-dispatches `validate` and returns the max of the validators it calls. The plan’s C1 would add references there, but C2 bypasses that combined path.
* External research evidence: Not applicable.
* Why it matters: With `references.enabled: true`, `fix` could return 0 while duplicate IDs, bad date ordering, or other reference errors remain. Custom-schema consumers could also get a no-op-ish `fix` that still runs validation instead of cleanly skipping.
* Recommended action for Claude Code: Change C2 to run the same final validation contract as `project-standards validate`, including `validate_references`, or explicitly call all three validators. Add a custom-schema preflight for `fix` itself.
* Suggested validation: Add tests where `fix` leaves a valid-schema/valid-id but invalid-reference document and must return 1 when references are enabled. Add a custom-schema `fix` test proving no writes and the documented skip result.

#### CR-002: Duplicate top-level YAML keys can pass silently

* Severity: High
* Status: Confirmed
* Adversarial angle: Ambiguous data / validation false positive.
* Plan reference: `_doc()` includes `tags`, `aliases`, and `related` at `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:593-596`; A4 then appends another `tags` key at `:686-689`. Tokenization/reorder code at `:338-380` and `:498-511` has no duplicate-key rejection.
* Finding: The plan’s tests accidentally create duplicate top-level keys and the planned formatter has no duplicate-key policy. PyYAML parsing keeps only the later value, so schema/reference validation can see one mapping while the source file contains conflicting entries.
* Repository evidence: Current `parse_frontmatter` uses `yaml.safe_load` in `src/project_standards/validate_frontmatter.py:123-134`. A read-only local check confirmed `yaml.safe_load('tags: []\ntags: [a, b]\n')` returns only the later `tags` value.
* External research evidence: PyYAML docs describe `safe_load` as constructing Python objects; PyYAML issue #165 documents duplicate-key overwrites. ruamel.yaml docs note YAML mapping keys must be unique and PyYAML historically did not enforce that.
* Why it matters: A formatter/validator suite can report clean while a human-visible frontmatter block contains duplicate `id`, `doc_type`, `tags`, or relationship keys. That undermines the suite’s safety claims.
* Recommended action for Claude Code: Add an explicit duplicate top-level key policy before transforms. At minimum, `format-frontmatter` should refuse to rewrite duplicate-key blocks; ideally validation should also surface duplicates, with versioning/back-compat implications documented.
* Suggested validation: Add tests for duplicate `id`, `doc_type`, and list keys proving they cannot be silently formatted or validated as clean.

#### CR-003: Planned private helper imports are likely to fail strict basedpyright

* Severity: High
* Status: Needs Claude verification
* Adversarial angle: Toolchain-gate compatibility.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:1227-1229`, `:1436-1439`.
* Finding: The plan imports `_schema_value_is_path` from `validate_frontmatter` into new runtime modules. This repo runs `basedpyright` in strict mode, and current tests already suppress private-use diagnostics with explicit `# pyright: ignore[reportPrivateUsage]` comments.
* Repository evidence: `pyproject.toml:55-60` sets strict basedpyright with warnings failing. Current tests import private helpers only with ignores, e.g. `tests/test_validate_id.py:20-22` and `tests/test_adopt_cli.py:64-66`.
* External research evidence: basedpyright docs describe `reportPrivateLocalImportUsage` for private imports from local modules and strict mode enabling most type-checking rules.
* Why it matters: The full gate can fail late after implementation, even if runtime behavior works.
* Recommended action for Claude Code: Make the custom-schema predicate public, for example `schema_value_is_path` or `is_custom_schema`, and update current internal uses plus planned modules to call the public helper. Avoid adding ignores in production code.
* Suggested validation: Run `uv run basedpyright` after the public-helper refactor and after adding `format_frontmatter.py` / `validate_references.py`.

### Non-blocking issues

#### CR-004: Supersession reciprocity only checks one direction

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Missed semantic check.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:1729-1735`, `:1768-1780`; spec at `docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:162`.
* Finding: The planned `check_reciprocity` checks `A.superseded_by = B` requires `B.supersedes` A, but not the reverse: `B.supersedes` A requiring `A.superseded_by = B`.
* Repository evidence: The ADR standard says replacement changes should update both documents: `standards/adr/README.md:174-177`.
* External research evidence: Not applicable.
* Why it matters: Half of the documented reciprocity invariant can remain broken while `validate-references` passes.
* Recommended action for Claude Code: Add the reverse-direction check and tests for both missing sides.
* Suggested validation: Add one fixture where the new document lists `supersedes` but the old document lacks `superseded_by`.

#### CR-005: `--stdin` mutual exclusions are specified but not enforced

* Severity: Medium
* Status: Confirmed
* Adversarial angle: CLI contract mismatch.
* Plan reference: Spec says `--stdin` is mutually exclusive with `FILE` / `--glob` / `--write` at `docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:83`; planned parser is at `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:1245-1276`.
* Finding: The parser accepts `--stdin` alongside files, `--glob`, or `--write`, then ignores those incompatible inputs.
* Repository evidence: Existing CLI code is careful about argparse edge cases in `src/project_standards/cli.py:121-185`; this plan should preserve that precision for new surfaces.
* External research evidence: Not applicable.
* Why it matters: Ambiguous editor/automation invocations can appear to succeed while not validating or writing the named file set.
* Recommended action for Claude Code: Add explicit argparse validation for `--stdin` conflicts and tests for `--stdin FILE`, `--stdin --glob`, and `--stdin --write`.
* Suggested validation: Each incompatible invocation should return exit 2 with a clear usage error.

#### CR-006: Pre-commit smoke is not reproducible in the planned toolchain

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation command can be skipped by environment accident.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:2162-2172`; acceptance at spec `:182`, `:189`.
* Finding: The plan requires `pre-commit validate-manifest` and `try-repo` as acceptance, but only runs them “if available” and does not add `pre-commit` to the dev dependency group or give an equivalent `uvx` command.
* Repository evidence: `pyproject.toml:21-30` has no `pre-commit`; `uv.lock` has no pre-commit entry; `command -v pre-commit` returned not found.
* External research evidence: Official pre-commit docs state pre-commit must be installed before hooks can run, and document `validate-manifest` and `try-repo` as the commands for this validation.
* Why it matters: The plan’s hook manifest can pass unit tests but never be exercised in the implementation environment.
* Recommended action for Claude Code: Either add `pre-commit` to the dev dependency group or specify `uvx pre-commit ...` / another reproducible invocation in the plan and final gate.
* Suggested validation: Run `pre-commit validate-manifest .pre-commit-hooks.yaml` and `pre-commit try-repo . format-frontmatter-check --all-files` after implementation in a Python 3.14-capable environment.

### Missing considerations

* Blocking: Duplicate top-level key behavior needs an explicit safety policy.
* Blocking: `fix` must prove the same postcondition as the extended `validate`, including reference checks.
* Non-blocking: `--stdin` conflict handling should be tested.
* Non-blocking: Atomic write should preserve file mode bits, or the plan should explicitly accept replacing Markdown files with temp-file default permissions.
* Non-blocking: List normalization should preserve inline comments on list key lines if the plan keeps claiming inline comment preservation.
* Non-blocking: Pre-commit validation needs a reproducible installation path.

### Internet research performed

* Source name: basedpyright documentation
* URL: https://docs.basedpyright.com/latest/benefits-over-pyright/new-diagnostic-rules/
* Access date: 2026-06-09
* What it was used to verify: Private local import diagnostics.
* Relevant conclusion: basedpyright has diagnostics for private imports from local modules; strict gate risk is real for planned `_schema_value_is_path` imports.

* Source name: pre-commit documentation
* URL: https://pre-commit.com/
* Access date: 2026-06-09
* What it was used to verify: Hook authoring and validation commands.
* Relevant conclusion: `pre-commit` must be installed to run hooks; `validate-manifest` and `try-repo` are official validation commands.

* Source name: PyYAML documentation and PyYAML issue tracker
* URL: https://pyyaml.org/wiki/PyYAMLDocumentation and https://github.com/yaml/pyyaml/issues/165
* Access date: 2026-06-09
* What it was used to verify: `safe_load` behavior and duplicate-key risk.
* Relevant conclusion: `safe_load` constructs Python objects, and duplicate keys have historically been overwritten rather than rejected.

### Items Claude Code should verify before correcting the plan

* Verify the current dirty working tree before staging anything; there are unrelated changes already present.
* Verify basedpyright’s exact diagnostic for private helper imports after choosing the public-helper fix.
* Decide whether duplicate frontmatter keys are formatter-only refusals or validator errors, and document the compatibility impact.
* Confirm custom-schema behavior for `project-standards fix`: the spec currently says skip entirely.
* Confirm a reproducible pre-commit invocation path in this repo’s Python 3.14 environment.

### Suggested corrections for Claude Code's plan

* Change C2 final validation to include `validate-references` or call the unified `validate` path.
* Add explicit custom-schema skip handling for `project-standards fix`.
* Add duplicate top-level key detection tests and implementation before any formatter rewrite.
* Replace private `_schema_value_is_path` imports with a public helper.
* Add reverse supersession reciprocity tests and implementation.
* Enforce `--stdin` mutual exclusions.
* Make pre-commit smoke validation reproducible via dev dependency or `uvx`.

### Read-only validation performed

* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed branch `testing`, current commits, and dirty/untracked working tree state.
* `nl -ba` / `sed -n` on the plan and spec: inventoried material claims and exact implementation snippets.
* `rg --files` and targeted `rg -n`: discovered relevant repository files and current references.
* `nl -ba` on `validate_id.py`, `validate_frontmatter.py`, `cli.py`, `pyproject.toml`, workflow, schema, config, and standards docs: checked current implementation points.
* `git diff --stat` and `git diff --check`: confirmed unrelated local changes and no whitespace errors in the dirty diff.
* `PYTHONDONTWRITEBYTECODE=1 python3 ... yaml.safe_load(...)`: confirmed local PyYAML duplicate-key overwrite and boolean coercion behavior without writing bytecode.
* `command -v pre-commit`, `command -v uv`, `python3 --version`, and `rg pre-commit uv.lock pyproject.toml`: confirmed `pre-commit` is not installed or declared, while Python 3.14 and uv are present.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_format_frontmatter.py tests/test_validate_references.py tests/test_cli_fix.py tests/test_precommit_hooks.py -q`
* Run only after implementation: `uv run format-frontmatter --check --config .project-standards.yml`
* Run only after implementation: `uv run project-standards validate --config .project-standards.yml`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`
* Run only after implementation: `pre-commit validate-manifest .pre-commit-hooks.yaml`
* Run only after implementation: `pre-commit try-repo . format-frontmatter-check --all-files`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-frontmatter-suite.md
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-006
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: C2 final validation/custom-schema behavior, duplicate-key handling, private helper import strategy, supersession reverse checks, `--stdin` conflicts, and reproducible pre-commit validation.

