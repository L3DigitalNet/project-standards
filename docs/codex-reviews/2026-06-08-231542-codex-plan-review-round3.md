### Executive summary

Claude Code’s revisions resolved the prior `fix --schema`, duplicate-key, boolean-like scalar/list coercion, and strict basedpyright optional-match findings. Significant findings still remain: the pre-commit smoke is still ordered in a way that can miss the newly created untracked hook manifest, and the revised formatter can still corrupt valid plain scalar values containing `#`.

New internet research was required for YAML plain-scalar/comment rules and pre-commit `try-repo` behavior.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-frontmatter-suite.md
* Prior audit issue count: 8
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested prior findings against the revised plan, approved spec, current repo source, schema, CI workflow, and toolchain configuration. Re-attacked custom-schema skip semantics, duplicate-key failure coverage, boolean-like scalar/list preservation, strict basedpyright risk, `--stdin` conflicts, pre-commit smoke reproducibility, and formatter false positives around source-preservation claims.

Could not execute implementation tests because this is still a proposal and the audit is read-only. Did not run `uvx pre-commit` because it can create tool/cache state.

### Prior findings status

#### CR-001: `project-standards fix` can skip the new reference gate

* Previous severity: High
* Current status: Resolved
* Evidence: C2 now tests reference-error failure, config custom-schema skip, and forwarded `--schema` skip at plan lines 2198-2225. The implementation snippet detects forwarded `--schema` at lines 2263-2265, skips before writes at lines 2282-2284, and runs all three validators in the final postcondition at lines 2289-2293.
* Remaining action for Claude Code: None for CR-001.

#### CR-002: Duplicate top-level YAML keys can pass silently

* Previous severity: High
* Current status: Resolved
* Evidence: Task 0.5 adds a unique-key loader for `parse_frontmatter` at lines 247-304, with direct parser tests at lines 262-269. C2 adds a combined-CLI duplicate-key failure test at lines 2228-2237. A9 also makes duplicate-key formatter skips fail the check/write gate at lines 1467-1472.
* Remaining action for Claude Code: None for CR-002.

#### CR-003: Planned private helper imports are likely to fail strict basedpyright

* Previous severity: High
* Current status: Resolved
* Evidence: Task 0.4 promotes `schema_value_is_path` to a public helper at lines 222-245. Later snippets import the public helper in `format_frontmatter` and `validate_references` at lines 1389-1391 and 1610-1613.
* Remaining action for Claude Code: None for CR-003; still run `uv run basedpyright` after implementation.

#### CR-004: Supersession reciprocity only checks one direction

* Previous severity: Medium
* Current status: Resolved
* Evidence: B4 includes tests for both superseded-by and reverse supersedes reciprocity at lines 1903-1919, and the implementation checks both maps at lines 1952-1975.
* Remaining action for Claude Code: None.

#### CR-005: `--stdin` mutual exclusions are specified but not enforced

* Previous severity: Medium
* Current status: Resolved
* Evidence: A9 adds `--stdin` conflict tests at lines 1369-1373 and parser enforcement at lines 1429-1432.
* Remaining action for Claude Code: None.

#### CR-006: Pre-commit smoke is not reproducible in the planned toolchain

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The toolchain part is resolved: the plan uses `uvx pre-commit validate-manifest` and `uvx pre-commit try-repo` at lines 2456-2459, and official uv docs say `uvx` is an alias for `uv tool run`. However, C4 creates a new `.pre-commit-hooks.yaml` at lines 2409-2449, runs `try-repo` at lines 2456-2459, and only stages the new file at lines 2463-2467. Official pre-commit docs say `try-repo` clones tracked uncommitted changes; a newly created untracked manifest may not be present in the clone.
* Remaining action for Claude Code: Move staging/tracking of `.pre-commit-hooks.yaml` before `try-repo`, or run `try-repo` after the file is committed/tracked. Keep `validate-manifest` before commit if desired, since it reads the explicit local path.

#### CR-NEW-001: Formatter can corrupt YAML boolean-like plain scalars

* Previous severity: High
* Current status: Resolved
* Evidence: A3 now quotes raw plain scalar text without PyYAML type resolution at lines 747-775 and adds scalar tests for `on`/`off`/`Yes`/`No` at lines 694-699. A4 uses `yaml.BaseLoader` for list items at lines 874-884 and adds list-item tests at lines 832-837.
* Remaining action for Claude Code: None for the boolean-like coercion case.

#### CR-NEW-002: A4 snippet likely fails strict basedpyright on optional regex match

* Previous severity: High
* Current status: Resolved
* Evidence: A4 now derives indentation by string slicing at lines 892-895 rather than `re.match(...).group(0)`.
* Remaining action for Claude Code: None for this specific optional-match issue.

### New blocking issues

#### CR-NEW-003: Scalar quote normalization treats valid `#` characters as comments

* Severity: High
* Status: Confirmed
* Adversarial angle: Data corruption / source-preserving formatter false positive.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:747-778`
* Finding: `_requote_scalar_line` splits plain scalar values at any `#`, not only at a YAML comment boundary. Valid values such as `title: C# guide` or `title: http://example.com/foo#bar` are parsed by PyYAML as full strings, but the planned regex would emit values like `title: 'C'# guide` or truncate the URL before the fragment.
* Repository evidence: Local read-only Python checks showed `yaml.safe_load("title: C# guide\n")` and `yaml.safe_load("title: http://x/#frag\n")` preserve the `#` as part of the string. A local simulation of the planned regex split those same lines into value-before-`#` plus a fake trailing comment.
* External research evidence: YAML 1.2.2 says comments must be separated from other tokens by whitespace, and its plain-scalar section forbids the ` #` combination, not every `#`: https://yaml.org/spec/1.2.2/
* Why it matters: `format-frontmatter --write` can silently corrupt valid metadata while still passing the existing planned tests and likely the repo dogfood check.
* Recommended action for Claude Code: Split inline comments only at a valid YAML comment boundary, e.g. whitespace followed by `#`, while preserving bare `#` inside plain scalars. Add tests for `title: C# guide`, URL fragments, and a real inline comment like `title: X # comment`.
* Suggested validation: Run only after correction/implementation: `uv run pytest tests/test_format_frontmatter.py -k "hash or comment or quoted" -v`

### New non-blocking issues

#### CR-NEW-004: List normalization still drops inline comments on flow/empty list values

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Source preservation / validation false positive.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:875-909`, `:2509`
* Finding: `normalize_lists` preserves `tags: # comment`, but loses comments on common forms like `tags: [] # keep` and `tags: [a] # keep` because `after_colon.strip().startswith("#")` is false when the value starts with `[`. The plan later claims list-key inline comments are preserved.
* Repository evidence: A local simulation of the planned `after_colon` logic returned an empty `inline` value for `tags: [] # keep`. The spec and plan both emphasize preserving inline comments attached to key lines.
* External research evidence: YAML 1.2.2 treats whitespace-separated trailing `#` text as a comment: https://yaml.org/spec/1.2.2/
* Why it matters: The formatter can delete maintainer comments while still reporting a successful write. This is not schema-breaking, but it violates the source-preservation contract.
* Recommended action for Claude Code: Preserve trailing comments when normalizing flow-list and empty-list forms, or skip rewriting list entries when the comment boundary cannot be safely retained. Add tests for `tags: [] # keep`, `tags: [a, b] # keep`, and `tags: # keep`.
* Suggested validation: Run only after correction/implementation: `uv run pytest tests/test_format_frontmatter.py -k "list and comment" -v`

### Regressions

None found.

### Internet research performed

* Source name: YAML 1.2.2 specification
* URL: https://yaml.org/spec/1.2.2/
* Access date: 2026-06-09
* What it was used to verify: Comment boundaries and whether `#` can appear inside plain scalars.
* Relevant conclusion: Comments require whitespace separation; bare `#` can be scalar content, so the formatter cannot treat every `#` as a comment.

* Source name: PyYAML documentation
* URL: https://pyyaml.org/wiki/PyYAMLDocumentation
* Access date: 2026-06-09
* What it was used to verify: PyYAML implicit boolean behavior and loader context.
* Relevant conclusion: The revised `BaseLoader`/raw-scalar approach addresses the prior boolean-like scalar issue.

* Source name: pre-commit documentation
* URL: https://pre-commit.com/
* Access date: 2026-06-09
* What it was used to verify: `.pre-commit-hooks.yaml`, `try-repo`, tracked uncommitted changes, `language_version`, and `validate-manifest`.
* Relevant conclusion: `uvx pre-commit` is plausible, but `try-repo` should run after the new hook manifest is tracked or committed.

* Source name: uv CLI reference
* URL: https://docs.astral.sh/uv/reference/cli/#uv-tool-run
* Access date: 2026-06-09
* What it was used to verify: `uvx` behavior.
* Relevant conclusion: `uvx` is an alias for `uv tool run`.

* Source name: basedpyright documentation
* URL: https://docs.basedpyright.com/latest/benefits-over-pyright/new-diagnostic-rules/
* Access date: 2026-06-09
* What it was used to verify: Strict diagnostic risk context.
* Relevant conclusion: The optional regex-match issue is resolved, but final `uv run basedpyright` remains required.

### Read-only validation performed

* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed branch `testing`, recent plan-review commits, and an unrelated dirty tree.
* Targeted `rg`, `nl -ba`, and `sed -n` inspections of the revised plan/spec: retested all prior findings and located new formatter/pre-commit risks.
* Inspected `src/project_standards/validate_frontmatter.py`, `src/project_standards/cli.py`, `src/project_standards/validate_id.py`, the JSON schema, `pyproject.toml`, and the reusable workflow: confirmed current repo integration points and strict gate settings.
* `git diff --stat` and `git diff --check`: confirmed current dirty files and no whitespace errors in the existing diff.
* `rg --files` for planned new files: confirmed `format_frontmatter`, `validate_references`, CLI-fix tests, pre-commit tests, and `.pre-commit-hooks.yaml` are still planned, not implemented.
* `PYTHONDONTWRITEBYTECODE=1 python3` snippets: confirmed PyYAML preserves bare `#` in plain scalar values, the planned regex would split those values incorrectly, and planned list inline-comment extraction drops comments after flow/empty list values.
* `command -v uv`, `command -v pre-commit`, `python3 --version`: confirmed `uv` and Python 3.14.5 are present; direct `pre-commit` is not installed.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_format_frontmatter.py -k "hash or comment or quoted or list" -v`
* Run only after implementation: `uv run pytest tests/test_cli_fix.py -k "custom_schema or reference_error or duplicate_keys or fix_leaves_validate_clean" -v`
* Run only after implementation: `uv run pytest tests/test_validate_references.py tests/test_cli_fix.py tests/test_precommit_hooks.py tests/test_format_frontmatter.py -q`
* Run only after implementation: `uv run format-frontmatter --check --config .project-standards.yml`
* Run only after implementation: `uv run project-standards validate --config .project-standards.yml`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`
* Run only after implementation: `uvx pre-commit validate-manifest .pre-commit-hooks.yaml`
* Run only after `.pre-commit-hooks.yaml` is tracked or committed: `uvx pre-commit try-repo . format-frontmatter-check --all-files`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-frontmatter-suite.md
* Audit round: 3
* Open issue IDs: CR-006, CR-NEW-003, CR-NEW-004
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-NEW-001, CR-NEW-002
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: pre-commit `try-repo` ordering/tracking, plain scalar `#` preservation, and inline comments on normalized list fields.

