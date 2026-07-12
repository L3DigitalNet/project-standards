### Executive summary

Claude Code’s revisions resolved the four prior findings: the manifest now includes `[capabilities]`, OQ-002 now aligns with SPEC-BA01 rev 0.4, TOML validation is no longer routed through Prettier in the full gate, and the repo-facing documentation scope was expanded.

One new blocking issue remains. The plan now says CLI-enforced standards should carry a non-adoptable marker instead of `adopt.md`, but the repository’s current CLI-enforced standard, `project-spec`, has an `adopt.md` and is documented as independently adoptable through its CLI workflow. New internet research was only needed to retest the Prettier/TOML validation assumption.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md`
* Prior audit issue count: 4
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested CR-001 through CR-004 against the revised plan, SPEC-BA01 rev 0.4, SPEC-MT01 §9, repository docs, bundle layout, registry/bundle state, and local Prettier behavior. I attacked the revised manifest shape, OQ-002 split, validation commands, documentation blast radius, release-count assumptions, no-machine-layer-drift claim, and adoption/anatomy wording.

Could not execute write-producing validation, formatter writes, test runs, or implementation commits due the read-only audit constraint.

### Prior findings status

#### CR-001: Plan omits the required `capabilities` manifest section

* Previous severity: High
* Current status: Resolved
* Evidence: The revised plan adds `[capabilities] provides/consumes_platform` to the README contract outline, the real `standard.toml`, and the blank template at plan lines 82, 140-142, and 202-204.
* Remaining action for Claude Code: Keep the README example, real manifest, and template field names synchronized during implementation.

#### CR-002: Minimal `standard.toml` contradicts resolved OQ-002 worked-example decision

* Previous severity: High
* Current status: Resolved
* Evidence: SPEC-BA01 rev 0.4 now explicitly decides that the README carries the complete annotated example while the meta-standard’s own `standard.toml` is minimal-but-conformant; see spec lines 41 and 149-150. The plan now references that split at line 157.
* Remaining action for Claude Code: None for the prior issue, but do not treat the real manifest as a substitute for the README’s full annotated example.

#### CR-003: Full-gate Prettier command can pass while TOML validation fails

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised full gate validates TOML with `tomllib` and runs Prettier only on Markdown globs at plan lines 276-285. Local probe `./node_modules/.bin/prettier --check pyproject.toml` still exits 2 with “No parser could be inferred,” confirming TOML should stay out of Prettier.
* Remaining action for Claude Code: Keep TOML validation as a parser check and avoid adding TOML to Prettier globs.

#### CR-004: Plan misses repository-facing documentation that will become stale

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised file scope now includes root `README.md`, `AGENTS.md`, `CLAUDE.md`, and `meta/versioning.md` at plan lines 31 and 243-255.
* Remaining action for Claude Code: Preserve the stated distinction that this meta-standard is internal/reference and not one of the six released standards.

### New blocking issues

#### CR-NEW-001: Plan falsely treats CLI-enforced standards as non-adoptable

* Severity: High
* Status: Confirmed
* Adversarial angle: Challenged the revised adoption/anatomy rule against the actual current CLI standard rather than accepting the plan’s category labels.
* Plan reference: Lines 17, 81, 245, and 253.
* Finding: The plan says `adopt.md` is present only for “adoptable standards” and that internal/reference and CLI-enforced standards carry an explicit non-adoptable marker instead. But the plan also classifies `project-spec` as `cli`, and the repository currently ships `standards/project-spec/adopt.md` as the Project Specification adoption procedure.
* Repository evidence: `standards/project-spec/adopt.md` exists and defines adoption DoD, config, CLI, and CI wiring. `standards/README.md` line 11 links Project Specification to `project-spec/adopt.md`; root `README.md` lines 97-98 and 145 also point consumers to that adoption runbook. `standards/project-spec/README.md` line 31 says Project Specification is active and registered for adoption.
* External research evidence: Not applicable.
* Why it matters: If implemented as written, the new meta-standard would codify an anatomy rule that contradicts an existing released standard. It confuses “no copy-adopt artifact bundle” with “not adoptable,” and would give Step 03/04 schema and graph work a bad contract for CLI-enforced standards.
* Recommended action for Claude Code: Revise the plan, and SPEC-BA01 if needed, to separate adoption mode from `adopt.md` presence. CLI standards may have an `adopt.md` runbook even when they have no copy-adopt artifact bundle. Reserve explicit non-adoptable markers for standards with no downstream adoption path, such as `adoption = "none"` and possibly draft/reference-only documents not released for adoption.
* Suggested validation: Re-run `rg -n "project-spec|adopt.md|required only|non-adoptable marker|cli" README.md standards/README.md standards/project-spec/adopt.md docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md` and confirm the corrected wording does not imply Project Specification lacks or should not have `adopt.md`.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: Prettier Options documentation
* URL: https://raw.githubusercontent.com/prettier/prettier/main/website/versioned_docs/version-stable/options.md
* Access date: 2026-07-08
* What it was used to verify: Whether built-in Prettier parsers include TOML.
* Relevant conclusion: The documented parser list includes Markdown, JSON/JSONC, YAML, and others, but not TOML.

* Source name: Prettier CLI documentation
* URL: https://raw.githubusercontent.com/prettier/prettier/main/website/versioned_docs/version-stable/cli.md
* Access date: 2026-07-08
* What it was used to verify: `--write`, `--check`, file-pattern behavior, and supported-file discovery.
* Relevant conclusion: Prettier only processes supported files and `--write` mutates files, so TOML should be validated separately with `tomllib`.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, one untracked prior review artifact, and recent plan/spec revision commits.
* `nl -ba docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md`: inspected the revised plan with line references.
* `nl -ba docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md`: verified SPEC-BA01 rev 0.4 and OQ-002 resolution.
* `nl -ba` / `rg -n` on SPEC-MT01, `standards/README.md`, root `README.md`, `AGENTS.md`, `CLAUDE.md`, `meta/versioning.md`, `.project-standards.yml`, `registry.json`, and Project Specification docs: checked manifest, adoption, doc-scope, and no-machine-layer claims.
* `find standards -maxdepth 2 -name adopt.md -print`: confirmed current standards with adoption runbooks, including `project-spec`.
* `find src/project_standards/bundles -maxdepth 2 -type f`: confirmed machine bundle state and absence of a standard-bundle-authoring bundle.
* `test -e standards/standard-bundle-authoring; echo $?`: confirmed the new bundle does not yet exist.
* `./node_modules/.bin/prettier --check pyproject.toml`: confirmed local Prettier 3.8.3 cannot infer a TOML parser and exits non-zero.
* `node -p "require('./package.json').devDependencies.prettier"`: confirmed the pinned Prettier version is 3.8.3.
* `git diff --stat`: confirmed no tracked working-tree diff from the audit.

### Recommended implementation validation

Run only after correcting and implementing the remaining issue:

* `uv run validate-frontmatter --config .project-standards.yml`
* `uv run validate-id --config .project-standards.yml`
* `uv run project-standards spec validate --config .project-standards.yml`
* `uv run project-standards spec lint --config .project-standards.yml`
* `uv run python -c "import tomllib,pathlib; [tomllib.loads(p.read_text()) for p in pathlib.Path('standards/standard-bundle-authoring').rglob('*.toml')]; print('toml ok')"`
* Run only after implementation: `./node_modules/.bin/prettier --write standards/standard-bundle-authoring/README.md standards/README.md README.md AGENTS.md CLAUDE.md meta/versioning.md docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md`
* `./node_modules/.bin/prettier --check "standards/**/*.md" "docs/superpowers/**/*.md"`
* `./node_modules/.bin/markdownlint-cli2`
* `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run pytest -q`
* `git diff -- src/project_standards/schemas/registry.json src/project_standards/bundles .project-standards.yml`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md`
* Audit round: 2
* Open issue IDs: CR-NEW-001
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: correcting the adoption/anatomy rule so CLI-enforced standards with adoption runbooks, especially Project Specification, are not mislabeled as non-adoptable.