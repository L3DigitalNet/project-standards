### Executive summary

Claude Code’s round-4 revisions resolved the prior open findings for `try-repo` ordering, scalar `#` handling, and simple flow/empty-list inline comments. New internet research was used to re-check YAML and pre-commit assumptions.

One new non-blocking formatter issue remains: the revised flow-list comment extraction can still misclassify ` #` inside quoted flow-list items as a comment, corrupting preserved comment text for valid list values.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-frontmatter-suite.md
* Prior audit issue count: 10
* Resolved issue count: 10
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested all prior findings against the current plan, approved spec, repository source, schema, workflow, and current toolchain state. Re-attacked the updated scalar/comment splitter, list normalization, `pre-commit try-repo` ordering, custom-schema skip behavior, duplicate-key protections, and strict basedpyright-sensitive snippets.

Could not execute implementation tests because this is still a proposal and the audit is read-only. Did not run `uvx pre-commit` because it can create tool/cache state.

### Prior findings status

#### CR-001: `project-standards fix` can skip the new reference gate

* Previous severity: High
* Current status: Resolved
* Evidence: C2 still includes reference-error, custom-schema, forwarded-`--schema`, duplicate-key, and final validation coverage at plan lines 2202-2369.
* Remaining action for Claude Code: None.

#### CR-002: Duplicate top-level YAML keys can pass silently

* Previous severity: High
* Current status: Resolved
* Evidence: Task 0.5 still adds duplicate-key rejection in `parse_frontmatter` at lines 247-314, and formatter/CLI duplicate-key checks remain at lines 380-387 and 1526-1530.
* Remaining action for Claude Code: None.

#### CR-003: Planned private helper imports are likely to fail strict basedpyright

* Previous severity: High
* Current status: Resolved
* Evidence: Task 0.4 still promotes `schema_value_is_path` to public API, and later snippets import that public name at lines 1448-1450 and 1669-1672.
* Remaining action for Claude Code: None; still run `uv run basedpyright` after implementation.

#### CR-004: Supersession reciprocity only checks one direction

* Previous severity: Medium
* Current status: Resolved
* Evidence: B4 still tests both directions at lines 1962-1978 and checks both `superseded_by` and `supersedes` maps at lines 2011-2034.
* Remaining action for Claude Code: None.

#### CR-005: `--stdin` mutual exclusions are specified but not enforced

* Previous severity: Medium
* Current status: Resolved
* Evidence: A9 still enforces `--stdin` conflicts at lines 1488-1491 and tests them at lines 1428-1432.
* Remaining action for Claude Code: None.

#### CR-006: Pre-commit smoke is not reproducible in the planned toolchain

* Previous severity: Medium
* Current status: Resolved
* Evidence: C4 now validates the manifest before tracking, commits `.pre-commit-hooks.yaml`, then runs `try-repo` after the commit at lines 2510-2533. Official pre-commit docs say `try-repo` supports local paths and uses the repository revision/tracked changes, so the prior untracked-manifest gap is closed.
* Remaining action for Claude Code: None.

#### CR-NEW-001: Formatter can corrupt YAML boolean-like plain scalars

* Previous severity: High
* Current status: Resolved
* Evidence: A3 still quotes raw plain scalar text without PyYAML type resolution at lines 766-823, and A4 still loads lists with `yaml.BaseLoader` at lines 933-943. Tests for scalar and list boolean-like values remain at lines 694-699 and 878-883.
* Remaining action for Claude Code: None.

#### CR-NEW-002: A4 snippet likely fails strict basedpyright on optional regex match

* Previous severity: High
* Current status: Resolved
* Evidence: A4 still derives indentation with slicing at lines 953-954 rather than dereferencing an optional regex match.
* Remaining action for Claude Code: None.

#### CR-NEW-003: Scalar quote normalization treats valid `#` characters as comments

* Previous severity: High
* Current status: Resolved
* Evidence: A3 now tests `C# guide`, URL fragments, and real inline comments at lines 702-718. `_split_value_comment` now splits plain scalars only at whitespace-`#` boundaries at lines 766-790. Local read-only simulation preserved `C# guide` and `http://example.com/p#frag` while preserving `X  # keep me` as a comment.
* Remaining action for Claude Code: None for scalar values.

#### CR-NEW-004: List normalization still drops inline comments on flow/empty list values

* Previous severity: Medium
* Current status: Resolved
* Evidence: A4 now tests `tags: [a, b]  # keep` and `tags: []  # keep` at lines 886-896, and `normalize_lists` reuses `_split_value_comment` for comments after flow/empty list values at line 956. Local read-only simulation confirmed the simple prior examples now preserve comments.
* Remaining action for Claude Code: None for the prior simple flow/empty-list comment cases; see CR-NEW-005 for a new quoted-item edge case.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-005: Flow-list comment splitting can misread `#` inside quoted list items

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Source preservation / validation false positive.
* Plan reference: `docs/superpowers/plans/2026-06-08-frontmatter-suite.md:933-969`
* Finding: `normalize_lists` calls `_split_value_comment(after_colon)` on the whole text after `key:`. Because flow lists begin with `[` rather than a quote, `_split_value_comment` falls back to `re.search(r"(\s+#.*)$", rest)`, which can split inside valid quoted list items such as `aliases: ['RFC #1']` or `source: ['Issue #123']`.
* Repository evidence: The schema and standard allow free string arrays for `aliases` and `source` (`standards/markdown-frontmatter/README.md:144-146`, `:373-381`), and `_LIST_FIELDS` includes those fields at plan line 918. A read-only Python simulation of the planned logic loaded `source: ['Issue #123']` as `{'source': ['Issue #123']}` with PyYAML, but split the key line as value ` "['Issue"` plus fake comment `" #123']"`.
* External research evidence: YAML 1.2.2 permits quoted scalars to contain printable characters, while the ` #` restriction is specifically a plain-scalar ambiguity rule: https://yaml.org/spec/1.2.2/
* Why it matters: `format-frontmatter --write` can preserve the semantic list item but add bogus comment text to the key line, leaving ugly or misleading metadata while tests and validation still pass.
* Recommended action for Claude Code: Make flow-list comment extraction quote/bracket-aware, or skip preserving/moving comments for flow-list entries when the comment boundary cannot be safely identified. Add tests for `aliases: ['RFC #1']`, `source: ['Issue #123']`, and the same forms with a real trailing `# keep` comment.
* Suggested validation: Run only after correction/implementation: `uv run pytest tests/test_format_frontmatter.py -k "flow_list or inline_comment or hash" -v`

### Regressions

None found.

### Internet research performed

* Source name: YAML 1.2.2 specification
* URL: https://yaml.org/spec/1.2.2/
* Access date: 2026-06-09
* What it was used to verify: Comment boundaries, plain-scalar ` #` rules, and quoted scalar behavior.
* Relevant conclusion: The scalar `#` fix is valid, but flow-list comment detection must respect quoted scalars.

* Source name: pre-commit documentation
* URL: https://pre-commit.com/
* Access date: 2026-06-09
* What it was used to verify: `.pre-commit-hooks.yaml`, `try-repo`, local hook repositories, and manifest validation.
* Relevant conclusion: Running `try-repo` after committing/tracking the manifest resolves CR-006.

* Source name: uv CLI reference
* URL: https://docs.astral.sh/uv/reference/cli/#uv-tool-run
* Access date: 2026-06-09
* What it was used to verify: `uvx` behavior.
* Relevant conclusion: `uvx` remains a valid alias for `uv tool run`.

### Read-only validation performed

* `pwd && git branch --show-current && git status --short && git log --oneline -n 10`: confirmed branch `testing`, current dirty tree, and recent plan-review commits.
* Targeted `rg`, `nl -ba`, and `sed -n` inspections of the plan and spec: retested prior findings and found CR-NEW-005.
* Inspected `pyproject.toml`, `.github/workflows/validate-markdown-frontmatter.yml`, `.project-standards.yml`, `validate_frontmatter.py`, `validate_id.py`, `cli.py`, schema, and standards README.
* `rg --files | rg ...`: confirmed planned new formatter/reference/pre-commit files are not implemented yet.
* `git diff --stat && git diff --check`: confirmed unrelated dirty files and no whitespace errors in the existing diff.
* `PYTHONDONTWRITEBYTECODE=1 python3` snippets: simulated the revised scalar splitter, simple list comment preservation, and quoted flow-list `#` failure.
* `command -v uv; command -v pre-commit || true; python3 --version`: confirmed `uv` and Python 3.14.5 are present; direct `pre-commit` is not installed.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_format_frontmatter.py -k "hash or comment or flow_list or inline_comment" -v`
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
* Audit round: 4
* Open issue IDs: CR-NEW-005
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-006, CR-NEW-001, CR-NEW-002, CR-NEW-003, CR-NEW-004
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: flow-list inline-comment extraction for quoted list items containing whitespace-`#`, plus tests proving comments and list values both survive.