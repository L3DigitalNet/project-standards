### Executive summary

Claude Code’s round-3 revisions resolved the prior CLI/adoption-mode blocker: `project-spec` is no longer treated as non-adoptable, and the plan now correctly says CLI-enforced standards released for adoption keep `adopt.md`.

One prior documentation-scope issue is only partially resolved. The plan includes `AGENTS.md`, but its concrete search/update step can still miss the existing stale “five standards” text in `AGENTS.md`, and it omits `docs/handoff/architecture.md`, whose component graph will become stale when `standard-bundle-authoring/` is added. New internet research only rechecked the Prettier/TOML assumption against current official Prettier docs.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md`
* Prior audit issue count: 5
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested CR-001 through CR-004 and CR-NEW-001 against the current plan, SPEC-BA01 rev 0.5, current bundle/index state, root README, `AGENTS.md`, `CLAUDE.md`, `meta/versioning.md`, handoff docs, `.project-standards.yml`, registry/bundle state, local Prettier 3.8.3 behavior, and current official Prettier docs.

I attacked the corrected adoption/anatomy wording, manifest field consistency, TOML validation route, repo-facing documentation scope, handoff blast radius, validation false positives, and dirty-tree assumptions. I did not run write-producing validators, formatters, tests, commits, or handoff updates due to read-only audit constraints.

### Prior findings status

#### CR-001: Plan omits the required `capabilities` manifest section

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still includes `[capabilities]` in the README manifest contract, the real manifest, and the blank template at lines 82, 140-142, and 202-204.
* Remaining action for Claude Code: Keep README, `standard.toml`, and template field names synchronized during implementation.

#### CR-002: Minimal `standard.toml` contradicts resolved OQ-002 worked-example decision

* Previous severity: High
* Current status: Resolved
* Evidence: SPEC-BA01 now carries rev 0.5 and preserves the rev 0.4 OQ-002 decision at spec lines 41 and 151. The plan repeats that split at line 157: README has the complete annotated example; the meta-standard’s own manifest is real and minimal.
* Remaining action for Claude Code: None for this issue.

#### CR-003: Full-gate Prettier command can pass while TOML validation fails

* Previous severity: Medium
* Current status: Resolved
* Evidence: The full gate validates TOML with `tomllib` and limits Prettier to Markdown globs at plan lines 276-285. Local `./node_modules/.bin/prettier --check pyproject.toml` still exits 2 with “No parser could be inferred,” and official Prettier parser docs still do not list TOML.
* Remaining action for Claude Code: Keep TOML parsing separate from Prettier.

#### CR-004: Plan misses repository-facing documentation that will become stale

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The plan includes root `README.md`, `AGENTS.md`, `CLAUDE.md`, and `meta/versioning.md` in file scope at lines 31 and 243-255. However, the actual Task 4 search at line 255 omits `AGENTS.md`, even though current `AGENTS.md` line 11 still says the repo defines “five standards” and omits CLI Documentation. The plan also omits `docs/handoff/architecture.md`, whose component graph at line 9 enumerates standards and will become stale once `standards/standard-bundle-authoring/` exists.
* Remaining action for Claude Code: Expand the plan’s repo-facing/handoff map update to explicitly include `AGENTS.md` in the “six standards” search and update `docs/handoff/architecture.md` if the new bundle changes the component graph.

#### CR-NEW-001: Plan falsely treats CLI-enforced standards as non-adoptable

* Previous severity: High
* Current status: Resolved
* Evidence: SPEC-BA01 rev 0.5 explicitly says `adopt.md` presence is independent of adoption mode and that CLI-enforced standards like `project-spec` keep `adopt.md` at spec lines 42, 106, and 134. The plan now states the same at lines 81, 245, and 253.
* Remaining action for Claude Code: None for the prior blocker.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-002: Plan still cites stale SPEC-BA01 revision numbers

* Severity: Low
* Status: Confirmed
* Adversarial angle: Checked whether the plan’s stated source of truth matches the current spec revision after round-3 corrections.
* Plan reference: Lines 11, 157, 291, and 306.
* Finding: The plan still names SPEC-BA01 as rev 0.3 in its source-of-truth and notes, and references rev 0.4 for OQ-002, while the current spec is rev 0.5. `docs/handoff/specs-plans.md` also still says rev 0.3 at line 15.
* Repository evidence: SPEC-BA01 revision history line 42 shows rev 0.5 as the current correction for the adoption/anatomy rule. Plan lines 11 and 306 still say rev 0.3.
* External research evidence: Not applicable.
* Why it matters: This is unlikely to break implementation because the plan body now contains the rev 0.5 substance, but stale revision labels make the audit trail ambiguous and can send the implementer to the wrong acceptance baseline.
* Recommended action for Claude Code: Update the plan and handoff pointer to cite SPEC-BA01 rev 0.5 consistently.
* Suggested validation: Re-run `rg -n "rev 0\\.3|rev 0\\.4|rev 0\\.5" docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md docs/handoff/specs-plans.md docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md`.

### Regressions

None found.

### Internet research performed

* Source name: Prettier Options documentation
* URL: https://prettier.io/docs/options
* Access date: 2026-07-08
* What it was used to verify: Current built-in parser list and whether TOML is supported.
* Relevant conclusion: The parser list includes Markdown, JSON/JSONC, YAML, and others, but not TOML.

* Source name: Prettier CLI documentation
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-08
* What it was used to verify: `--write`, `--check`, supported-file discovery, and unknown-file behavior.
* Relevant conclusion: `--write` mutates processed files, and supported-file discovery is extension/parser based; TOML should remain validated with `tomllib`.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, recent round-3 correction commit, and two untracked prior review artifacts.
* `nl -ba` on the plan and SPEC-BA01: inspected current plan and confirmed SPEC-BA01 is rev 0.5.
* `nl -ba` / `rg -n` on `README.md`, `standards/README.md`, `AGENTS.md`, `CLAUDE.md`, `meta/versioning.md`, `docs/handoff/architecture.md`, `docs/handoff/specs-plans.md`, `STATUS.md`, and `TODO.md`: checked stale documentation surfaces and standards-count claims.
* `find standards ...`: confirmed current standards have `adopt.md` where expected and `standard-bundle-authoring/` does not yet exist.
* `find src/project_standards/bundles ...` and `nl -ba src/project_standards/schemas/registry.json`: confirmed no machine bundle or registry entry exists for the new meta-standard.
* `nl -ba .project-standards.yml`, `.markdownlint-cli2.jsonc`, and `.prettierignore`: checked validation inclusion/exclusion behavior.
* `node -p "require('./package.json').devDependencies.prettier"`: confirmed local Prettier is pinned at 3.8.3.
* `./node_modules/.bin/prettier --check pyproject.toml`: confirmed TOML is not Prettier-gated locally.
* `git diff --stat` and `git diff --check`: confirmed no tracked diff and no whitespace errors from existing tracked changes.

### Recommended implementation validation

After correcting and implementing the remaining documentation-scope issues:

* `rg -n "defines five|six standards|CLI Documentation|standard-bundle-authoring|python-coding" AGENTS.md README.md CLAUDE.md meta/versioning.md docs/handoff/architecture.md docs/handoff/specs-plans.md STATUS.md TODO.md`
* `uv run validate-frontmatter --config .project-standards.yml`
* `uv run validate-id --config .project-standards.yml`
* `uv run project-standards spec validate --config .project-standards.yml`
* `uv run project-standards spec lint --config .project-standards.yml`
* `uv run python -c "import tomllib,pathlib; [tomllib.loads(p.read_text()) for p in pathlib.Path('standards/standard-bundle-authoring').rglob('*.toml')]; print('toml ok')"`
* Run only after implementation: `./node_modules/.bin/prettier --write standards/standard-bundle-authoring/README.md standards/README.md README.md AGENTS.md CLAUDE.md meta/versioning.md docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md`
* `./node_modules/.bin/prettier --check "standards/**/*.md" "docs/superpowers/**/*.md"`
* `./node_modules/.bin/markdownlint-cli2`
* `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run pytest -q`
* `git diff -- src/project_standards/schemas/registry.json src/project_standards/bundles .project-standards.yml`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md`
* Audit round: 3
* Open issue IDs: CR-004, CR-NEW-002
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-NEW-001
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: confirming the plan explicitly updates stale repo-facing and handoff standards maps, especially `AGENTS.md` and `docs/handoff/architecture.md`, and that all SPEC-BA01 revision references now point to rev 0.5.

