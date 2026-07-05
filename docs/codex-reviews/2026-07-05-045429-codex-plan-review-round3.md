### Executive summary

Claude Code’s latest revisions resolve the prior CI/workflow blocker and substantially improve the fenced-code segmentation tests. One correctness issue remains: the proposed fence tracker still claims to mirror CommonMark, but its regex treats four-space-indented code fences and closing-fence lines with trailing info text as real fence delimiters. That can make `upgrade` skip real headings or split authored sections incorrectly in edge-case but valid Markdown.

New internet research was performed only for the CommonMark fence rules.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-05-project-spec-tooling-spec3.md
* Prior audit issue count: 3
* Resolved issue count: 2
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 0
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the two open prior findings against the revised plan and current repository state. I re-read the revised plan, inspected the `Validate Specs` workflow/config/parser paths, checked current git history for the out-of-band workflow fix, compared the proposed fence tracker with the repo’s existing CommonMark-aware fence logic and tests, and verified the relevant CommonMark rules against the official spec.

I did not run tests or `uv` commands because this is a read-only audit and those commands may write caches/artifacts.

### Prior findings status

#### CR-001: H1 tier suffix rewrite can silently fail while validation still passes

* Previous severity: High
* Current status: Resolved
* Evidence: Still resolved from the prior pass. The plan keeps the explicit H1 tier precheck in `check_upgradeable` at lines 775-804 and the CLI path runs that precheck before `upgrade_text` at lines 967-974.
* Remaining action for Claude Code: None.

#### CR-002: Final gate omits the repo’s triggered `Validate Specs` CI workflow

* Previous severity: High
* Current status: Resolved
* Evidence: The repository now contains the out-of-band workflow fix the revised plan references. `.github/workflows/validate-specs.yml` lines 60-79 detect whether the this-repo config has a top-level `spec:` block and gate the self-repo validate/lint steps on `steps.cfg.outputs.has_spec == 'true'`. `.project-standards.yml` still has no top-level `spec:` block at lines 1-62, so the workflow no longer runs the repo-local `spec validate --config` command on this branch until project-spec is registered. The recent git log also shows `b76c96d fix(ci): gate this-repo Validate Specs on a spec: block existing`.
* Remaining action for Claude Code: Keep the workflow file unchanged in this task and preserve Step 5b’s note that local `spec validate --config .project-standards.yml` remains expected to exit 2 until registration.

#### CR-003: Heading segmentation lacks an explicit fenced-code adversarial test

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The plan now adds nested/mixed fence tests at lines 229-242 and updates `_heading_starts()` to require same-character and at-least-equal-length closing fences at lines 257-290. That resolves the specific nested-backtick and mixed-tilde gap from the prior audit. However, the proposed `_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")` at line 257 still diverges from the repo’s existing CommonMark-aware model in `src/project_standards/validate_frontmatter.py:223-231`: it allows arbitrary whitespace indentation, and it uses the same permissive regex for opening and closing. The repo already tests that four-space-indented backticks are not fences in `tests/test_validate_frontmatter.py:1469-1478`. The official CommonMark spec says fenced blocks begin with a code fence preceded by up to three spaces, and closing fences may be preceded by up to three spaces and followed only by spaces/tabs.
* Remaining action for Claude Code: Update Task 3 to reuse or mirror the existing `_CODE_FENCE_RE` / `_CODE_FENCE_CLOSE_RE` split: opening fences allow up to three spaces and optional info text; closing fences require same marker, sufficient length, up to three spaces indent, and only trailing spaces/tabs. Add tests for a four-space-indented ``` line not opening a fence, and a closing-looking ``` aaa line inside a backtick fence not closing it.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: CommonMark Spec 0.31.2, Fenced code blocks
* URL: https://spec.commonmark.org/0.31.2/#fenced-code-blocks
* Access date: 2026-07-05
* What it was used to verify: Whether the revised `_heading_starts()` fence tracking matches CommonMark indentation and close-fence rules.
* Relevant conclusion: Fences are valid only with up to three leading spaces; closing fences must use the same character, be at least as long as the opener, and be followed only by spaces/tabs. The plan’s regex still over-accepts fence delimiters.

### Read-only validation performed

* `pwd`: Confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: Confirmed branch `testing`, recent workflow/plan commits, and only untracked codex review docs.
* `rg` and `nl -ba` on the revised plan: Re-read the current CR-002/CR-003 revisions, including fence tests and `_heading_starts()` implementation.
* `nl -ba .github/workflows/validate-specs.yml` and `.project-standards.yml`: Confirmed the workflow is now gated for this repo and the config still lacks a top-level `spec:` block.
* `nl -ba src/project_standards/specs/config.py`: Confirmed `collect_spec_paths()` still raises when no explicit files and no `spec.include` exist.
* `nl -ba src/project_standards/validate_frontmatter.py` and `tests/test_validate_frontmatter.py`: Confirmed the repo’s existing fence tracker handles same-character/equal-length rules and rejects four-space-indented fences.
* `nl -ba pyproject.toml`, `.python-version`, and `.github/workflows/check.yml`: Confirmed the plan’s Python/tooling gate matches repo configuration.
* Official CommonMark documentation lookup: Verified current fence indentation and closing rules.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_upgrade.py -k "top_blocks or present_top or check_upgradeable" -v`
* Run only after implementation: targeted tests for four-space-indented fence markers and closing-fence lines with trailing info text inside authored spec sections.
* Run only after implementation: `uv run pytest tests/test_spec_upgrade_fixtures.py tests/test_spec_upgrade.py tests/test_spec_upgrade_cli.py -v`
* Run only after implementation: `uv run pytest tests/test_spec_new_cli.py tests/test_spec_new.py -v`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run validate-frontmatter --config .project-standards.yml`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-05-project-spec-tooling-spec3.md
* Audit round: 3
* Open issue IDs: CR-003
* Resolved issue IDs: CR-001, CR-002
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: whether Task 3’s fence tracker now fully mirrors the repo’s CommonMark-aware open/close delimiter rules, especially four-space-indented fence markers and closing-looking lines with trailing info text.