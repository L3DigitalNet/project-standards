### Executive summary

Claude Code’s revisions resolved the private-helper import, reverse reciprocity, `--stdin` conflict, and reproducible pre-commit-smoke findings. Significant findings remain: the duplicate-key fix only prevents formatter rewrites and can still let duplicate keys pass the suite, `fix --schema ...` still does not skip entirely, and the formatter plan can corrupt YAML boolean-like plain scalars such as `on`/`off`.

New internet research was required for PyYAML scalar coercion and to re-check the pre-commit/uv assumptions.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-frontmatter-suite.md
* Prior audit issue count: 6
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the six prior CR findings against the revised plan, the approved spec, and current repo evidence. Re-attacked the `fix` postcondition, custom-schema skip semantics, duplicate-key behavior, strict basedpyright risk, pre-commit reproducibility, reference validation, and formatter false positives/data-corruption paths.

Could not execute implementation tests because the plan is still a proposal and this audit is read-only. Did not run `uvx pre-commit` because it may write tool/cache state.

### Prior findings status

#### CR-001: `project-standards fix` can skip the new reference gate

* Previous severity: High
* Current status: Partially resolved
* Evidence: C2 now calls `validate_frontmatter`, `validate_id`, and `validate_references` in the final postcondition at lines 2154-2158, and config-level custom schema skips at lines 2141-2149. However, the preflight only checks `fix_cfg.schema`; it does not check a forwarded `--schema custom.json`, while the spec treats `--schema` as custom-schema mode for formatting and says `fix` skips under custom schema.
* Remaining action for Claude Code: Add explicit `--schema`/`--schema=...` detection to the `fix` early dispatch and test `project-standards fix --schema custom.json` returns 0 with no writes and no final validation.

#### CR-002: Duplicate top-level YAML keys can pass silently

* Previous severity: High
* Current status: Partially resolved
* Evidence: The tokenizer now refuses duplicate top-level keys at lines 383-401, with a formatter unit test at lines 305-312. But `format_text` returns unchanged text plus warnings at lines 439-442, and the CLI exits 0 when there is no change/unparseable flag at lines 1360-1372. Current `parse_frontmatter` still uses `yaml.safe_load` at `src/project_standards/validate_frontmatter.py:129`; local read-only evidence confirmed duplicate keys keep the later value.
* Remaining action for Claude Code: Make duplicate top-level keys fail a meaningful gate, either as `validate-frontmatter` errors or as `format-frontmatter --check` exit 1, and add CLI tests proving duplicate keys cannot pass the final suite.

#### CR-003: Planned private helper imports are likely to fail strict basedpyright

* Previous severity: High
* Current status: Resolved
* Evidence: Task 0.4 promotes `schema_value_is_path` to a public helper at lines 222-245, and later snippets import the public name.
* Remaining action for Claude Code: None for the private-import issue; still run `uv run basedpyright` after implementation.

#### CR-004: Supersession reciprocity only checks one direction

* Previous severity: Medium
* Current status: Resolved
* Evidence: The plan adds reverse-direction tests at lines 1804-1811 and implements both directions at lines 1844-1867.
* Remaining action for Claude Code: None.

#### CR-005: `--stdin` mutual exclusions are specified but not enforced

* Previous severity: Medium
* Current status: Resolved
* Evidence: The plan adds conflict tests at lines 1262-1266 and parser enforcement at lines 1322-1325.
* Remaining action for Claude Code: None.

#### CR-006: Pre-commit smoke is not reproducible in the planned toolchain

* Previous severity: Medium
* Current status: Resolved
* Evidence: The plan now uses `uvx pre-commit validate-manifest` and `uvx pre-commit try-repo` at lines 2321-2326. `uv` is installed locally; official uv docs describe `uvx` as an alias for `uv tool run`.
* Remaining action for Claude Code: Run the smoke only after implementation.

### New blocking issues

#### CR-NEW-001: Formatter can corrupt YAML boolean-like plain scalars

* Severity: High
* Status: Confirmed
* Adversarial angle: Data corruption / unsafe autocorrection.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:661-688`, `:760-798`.
* Finding: The formatter snippets parse scalar and list values with `yaml.safe_load`, then re-emit `bool` values as `true`/`false` or `str(item)`. Plain YAML scalars like `on`, `off`, `yes`, and `no` are coerced by PyYAML to booleans, so `title: on` can become `title: 'true'` instead of `title: 'on'`.
* Repository evidence: Local read-only check: `yaml.safe_load('yes')`, `yaml.safe_load('on')`, `yaml.safe_load('No')`, and `yaml.safe_load('Off')` returned booleans. The repo already depends on PyYAML in `pyproject.toml`.
* External research evidence: PyYAML docs show boolean examples where `on`/`off` construct to Python `True`/`False`: https://pyyaml.org/wiki/PyYAMLDocumentation.
* Why it matters: `--write` can silently alter human-authored metadata while making the document schema-valid, which is worse than leaving an invalid unquoted scalar for the validator to catch.
* Recommended action for Claude Code: Quote raw scalar/list text without round-tripping through PyYAML’s implicit boolean resolver, or use a loader/parse path that preserves plain scalars as strings for formatter purposes. Add explicit tests for `title: on`, `description: no`, and list items `[on, off, yes, no]`.
* Suggested validation: `format-frontmatter --write` should convert those values to quoted original text, not canonical booleans.

#### CR-NEW-002: A4 snippet likely fails strict basedpyright on optional regex match

* Severity: High
* Status: Needs Claude verification
* Adversarial angle: Toolchain-gate compatibility.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:783`.
* Finding: `re.match(...).group(0)` dereferences a potentially `None` match in production code. This repo’s basedpyright config is strict with `failOnWarnings = true`.
* Repository evidence: `pyproject.toml:55-60` sets strict basedpyright and fail-on-warning. The planned code has no guard or assertion around the `re.match` result.
* External research evidence: basedpyright docs confirm the stricter diagnostic posture and additional rules: https://docs.basedpyright.com/latest/benefits-over-pyright/new-diagnostic-rules/.
* Why it matters: The full gate can fail late even if runtime tests pass.
* Recommended action for Claude Code: Replace the call with a safe helper, an explicit checked match, or a non-optional expression such as slicing from a known regex result after a guard.
* Suggested validation: Run `uv run basedpyright` after A4 and again at the final gate.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: PyYAML documentation
* URL: https://pyyaml.org/wiki/PyYAMLDocumentation
* Access date: 2026-06-09
* What it was used to verify: PyYAML implicit scalar construction for booleans.
* Relevant conclusion: PyYAML treats tokens such as `on`/`off` as booleans, so formatter use of `safe_load` can change text semantics.

* Source name: pre-commit documentation
* URL: https://pre-commit.com/
* Access date: 2026-06-09
* What it was used to verify: Hook manifest fields, `pass_filenames`, `language_version`, and `try-repo`.
* Relevant conclusion: The revised pre-commit hook shape and `try-repo` smoke are aligned with official docs.

* Source name: uv CLI reference
* URL: https://docs.astral.sh/uv/reference/cli/#uv-tool-run
* Access date: 2026-06-09
* What it was used to verify: `uvx` behavior.
* Relevant conclusion: `uvx` is an alias for `uv tool run`, making the revised smoke reproducible without adding `pre-commit` to dev dependencies.

* Source name: basedpyright documentation
* URL: https://docs.basedpyright.com/latest/benefits-over-pyright/new-diagnostic-rules/
* Access date: 2026-06-09
* What it was used to verify: Strict diagnostic risk context.
* Relevant conclusion: The public-helper fix resolves the prior private-import concern, but new snippets still need strict type-check verification.

### Read-only validation performed

* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed branch `testing` and an unrelated dirty tree.
* Targeted `rg`, `sed`, and `nl -ba` inspections of the revised plan and spec: retested all prior findings against current plan text.
* Inspected `src/project_standards/cli.py`, `validate_frontmatter.py`, `validate_id.py`, `pyproject.toml`, workflow, and `.project-standards.yml`: verified current repo integration points and strict gate config.
* `git diff --stat` and `git diff --check`: confirmed existing dirty files and no whitespace errors in the current diff.
* `PYTHONDONTWRITEBYTECODE=1 python3 -c ... yaml.safe_load(...)`: confirmed duplicate-key overwrite and boolean-like scalar coercion locally.
* `command -v uv`, `command -v pre-commit`, `python3 --version`: confirmed uv and Python 3.14 are present; `pre-commit` is not installed directly.
* `rg --files` and targeted current-repo `rg`: confirmed the new `format-frontmatter`/`validate-references` surfaces are still planned, not implemented.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_format_frontmatter.py -k "duplicate or boolean or scalar or list" -v`
* Run only after implementation: `uv run pytest tests/test_cli_fix.py -k "custom_schema or reference_error or fix_leaves_validate_clean" -v`
* Run only after implementation: `uv run pytest tests/test_validate_references.py tests/test_cli_fix.py tests/test_precommit_hooks.py tests/test_format_frontmatter.py -q`
* Run only after implementation: `uv run format-frontmatter --check --config .project-standards.yml`
* Run only after implementation: `uv run project-standards validate --config .project-standards.yml`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`
* Run only after implementation: `uvx pre-commit validate-manifest .pre-commit-hooks.yaml`
* Run only after implementation: `uvx pre-commit try-repo . format-frontmatter-check --all-files`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-frontmatter-suite.md
* Audit round: 2
* Open issue IDs: CR-001, CR-002, CR-NEW-001, CR-NEW-002
* Resolved issue IDs: CR-003, CR-004, CR-005, CR-006
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: `fix --schema` skip behavior, duplicate-key failure semantics, YAML boolean-like scalar/list preservation, and strict basedpyright safety for the formatter snippets.

