### Executive summary

Claude Code’s round-1 corrections resolve the six prior findings, but the revised spec still is not ready as a basis for planning. A new blocking repository-fit issue remains: the dogfood scope treats this repo as though the only installed command to document is `project-standards`, while the package actually exposes multiple `console_scripts`, and the spec’s own multi-entry-point rule says installed command names define the user-facing command contract.

New internet research was required for entry-point and packaging assumptions. Official Python Packaging docs confirm that `console_scripts` names are installed shell commands, which supports the new blocking finding.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md`
* Prior audit issue count: 6
* Resolved issue count: 6
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested SA-001..SA-006 against the revised spec, current repo config, CLI entry points, adopt engine, registry/version validation paths, package docs, bundle tests, frontmatter config, versioning contract, and official Python/PyPA/uv documentation. Re-attacked the acceptance criteria for false positives around dogfood completeness, installed-wrapper proof, config validation, stale-path sweeps, and docs drift.

Could not run implementation gates, wheel builds, pytest, `uv run`, or frontmatter validation because this audit is read-only and those commands may write caches, build artifacts, coverage data, or dependency state.

### Prior findings status

#### SA-001: Dogfood profile contradicts the standard’s own deep-profile rule

* Previous severity: High
* Current status: Resolved
* Evidence: The profile rule now states that nesting is a scale signal, not an automatic Packaged-deep trigger, and records `project-standards` as Packaged with a maintainability rationale. The Packaged tier now explicitly requires every leaf command in the single-page reference.
* Remaining action for Claude Code: None for the original profile-ladder contradiction. Address SA-NEW-001 separately because the current dogfood command inventory is incomplete.

#### SA-002: Mandatory `--version` requirement is not carried into implementation scope or acceptance

* Previous severity: High
* Current status: Resolved
* Evidence: The revised dogfood section requires adding top-level `project-standards --version`, sourcing it from package metadata, and the acceptance criteria require it to print the release version and exit 0. The installed-wrapper smoke test also includes `--version`.
* Remaining action for Claude Code: None for the original omission.

#### SA-003: `docs/usage.md` can escape frontmatter validation

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec requires adding `docs/usage.md` to `.project-standards.yml` include globs and says acceptance must prove it appears in the validated-file set.
* Remaining action for Claude Code: None for the original false-positive path.

#### SA-004: Existing manifest tests do not automatically enforce new bundle byte identity

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised tests section requires explicit byte-identity mappings for each shipped `cli-documentation` bundle artifact, acknowledging the current `_DOGFOOD` map is hardcoded and not automatic.
* Remaining action for Claude Code: None for the original test-coverage gap.

#### SA-005: Installed-entry-point smoke test is underspecified

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec now defines the smoke mechanism as wheel build, throwaway venv install, and execution via the installed wrapper for `--help`, `--version`, and one nested subcommand.
* Remaining action for Claude Code: None for the original underspecification. Extend the same reasoning to the multi-entry-point scope under SA-NEW-001.

#### SA-006: “No `cli-framework/` path remains anywhere” is overbroad

* Previous severity: Medium
* Current status: Resolved
* Evidence: The acceptance criterion now limits failures to active stale references and explicitly exempts historical provenance such as specs, research reports, audit logs, TODO phase history, and session logs.
* Remaining action for Claude Code: None for the original overbroad sweep.

### New blocking issues

#### SA-NEW-001: Dogfood scope omits installed console scripts and top-level commands

* Severity: High
* Status: Confirmed
* Adversarial angle: Can the spec’s “full dogfood” acceptance pass while the repo violates the standard’s own multi-entry-point and every-leaf-command requirements?
* Spec reference: Lines 62, 73, 78, 150-154, 200-202.
* Finding: The spec scopes dogfood to a single `docs/usage.md` for the `project-standards` entry point and describes the CLI as `spec` plus `adopt` groups with about 8 leaf commands. The actual package exposes multiple installed `console_scripts`, and even within the `project-standards` command it has top-level `validate`, `fix`, `list`, and `adopt` plus the nested `spec` commands. The spec’s own multi-entry-point rule requires one usage-reference page per installed command name, but dogfood and acceptance only smoke/document `project-standards`.
* Repository evidence: `pyproject.toml` registers `project-standards`, `validate-frontmatter`, `validate-id`, `sync-vscode-colors`, `sync-standards-include`, `format-frontmatter`, and `validate-references` as console scripts. `src/project_standards/cli.py` registers top-level `validate`, `fix`, `spec`, `adopt`, and `list`; `src/project_standards/specs/cli.py` adds `validate`, `lint`, `extract`, `next`, `new`, and `upgrade` under `spec`. `src/project_standards/README.md` documents these as the current CLI surface.
* External research evidence: Python Packaging User Guide, Entry points specification, https://packaging.python.org/en/latest/specifications/entry-points/, accessed 2026-07-07. It states that `console_scripts` entry-point names are commands created by installers, so the user-facing command contract is not limited to the unified `project-standards` command.
* Why it matters: Claude Code could implement and test a polished `docs/usage.md` for only `project-standards --help`, `--version`, and `spec validate --help` while leaving six installed command wrappers and several top-level `project-standards` commands undocumented or unsmoked. That would satisfy the revised acceptance text but violate the proposed standard’s own Packaged/multi-entry-point rules.
* Recommended action for Claude Code: Decide and state the dogfood boundary. Either document and smoke every installed console script according to the multi-entry-point rule, or explicitly classify the standalone scripts as compatibility aliases/internal commands and define what documentation they require. Also correct the `project-standards` leaf-command inventory to include `validate`, `fix`, `list`, and `adopt`.
* Suggested validation: After implementation, compare `[project.scripts]` keys and `project-standards` parser leaves against the generated or authored usage docs. Fail if any public installed command or in-scope leaf command lacks documentation and an installed-wrapper smoke path.

### New non-blocking issues

#### SA-NEW-002: Active package CLI README is omitted from touchpoints

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Can the new standard land while an active repo-local CLI reference remains stale or conflicts with `docs/usage.md`?
* Spec reference: Lines 167-184, 198-202.
* Finding: The multi-file touchpoint list omits `src/project_standards/README.md`, which is an active package/CLI reference documenting command surface, module map, registry keys, bundle list, config examples, and “Adding a new standard” instructions. Adding `cli-documentation`, `cli_documentation.version`, `--version`, new bundle files, and a new dogfood usage doc will make this README stale unless the spec defines whether to update it, reduce it to implementation internals, or point it to `docs/usage.md`.
* Repository evidence: `src/project_standards/README.md` lists current console scripts, documents `project-standards spec`, describes `bundles/`, explains `registry.json`, and includes config examples with only `python_tooling` and `markdown_tooling`. Root `README.md` points users to `src/project_standards/README.md` for the full CLI reference.
* External research evidence: Not applicable.
* Why it matters: The repo could pass the spec’s acceptance criteria while shipping two conflicting active CLI references: the new dogfood `docs/usage.md` and the existing source-package README. That increases maintenance drift exactly where this standard is trying to make CLI documentation reliable.
* Recommended action for Claude Code: Add `src/project_standards/README.md` to the touchpoints with a clear ownership decision: either update it to mirror the new command/config/bundle facts, or make it explicitly implementation-focused and link to `docs/usage.md` as the authoritative CLI usage reference.
* Suggested validation: After implementation, inspect `src/project_standards/README.md` for stale command, registry, config, and bundle references, and verify its CLI-reference role does not conflict with `docs/usage.md`.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Does full dogfood apply to all `[project.scripts]` commands or only the unified `project-standards` command?
* Why it matters: It determines whether the standard requires one usage page per installed command and whether smoke tests must cover standalone wrappers.
* Recommended clarification: State the public installed-command set and any explicit alias/internal-command exceptions.
* Blocking or non-blocking: Blocking.

* Ambiguity: What is the authoritative CLI usage reference after `docs/usage.md` is added?
* Why it matters: `src/project_standards/README.md` currently functions as a CLI/package reference and can drift from the new usage doc.
* Recommended clarification: Define whether `docs/usage.md` supersedes, complements, or is linked from the source-package README.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: Python Packaging User Guide, Entry points specification
* URL: https://packaging.python.org/en/latest/specifications/entry-points/
* Access date: 2026-07-07
* What it was used to verify: Whether `[project.scripts]` / `console_scripts` names are installed user-facing commands.
* Relevant conclusion: Installers create command wrappers for console scripts; the entry-point name is the shell command contract.

* Source name: Python 3.14 argparse documentation
* URL: https://docs.python.org/3.14/library/argparse.html
* Access date: 2026-07-07
* What it was used to verify: `ArgumentParser` color default and `prog` behavior.
* Relevant conclusion: `color=True` is the documented default in Python 3.14, and default `prog` depends on invocation, supporting the spec’s normalization and installed-wrapper checks.

* Source name: uv build backend documentation
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-07-07
* What it was used to verify: Wheel inclusion behavior for module-root data and `.data` directories.
* Relevant conclusion: uv’s wheel build includes the module root and data directories; package-content checks for bundled files remain appropriate.

### Read-only validation performed

* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git diff --stat`: confirmed branch `testing`, latest commit `86f7c04` addresses SA-001..SA-006, and no local diff output.
* Inspected the revised spec with `nl -ba ... | sed -n '1,260p'`: verified the round-1 corrections and inventoried new dogfood, test, release, and acceptance requirements.
* Inspected `.project-standards.yml`: confirmed current include/exclude state and the interim `standards/cli-framework/**` exclude.
* Inspected `pyproject.toml`: confirmed the package exposes multiple `console_scripts`, not only `project-standards`.
* Inspected `src/project_standards/cli.py` and `src/project_standards/specs/cli.py`: confirmed top-level command surface, nested `spec` leaves, and no current top-level `--version`.
* Inspected `src/project_standards/README.md`: confirmed it is an active CLI/package reference omitted from the spec touchpoints.
* Inspected `src/project_standards/registry.py`, `src/project_standards/schemas/registry.json`, and `src/project_standards/validate_frontmatter.py`: confirmed current registry/version validation shape and where `cli_documentation.version` support must be added.
* Inspected adopt engine and tests: confirmed current fragment reporting, skip-on-existing semantics, hardcoded manifest standard count, byte-identity map, and wheel-content test shape.
* Inspected root `README.md`, `standards/README.md`, `meta/versioning.md`, and `.github/workflows/validate-specs.yml`: checked repo-consumer docs, standard count, versioning classification, and current CI surfaces.
* Ran targeted `rg` searches for `cli-framework`, `cli-documentation`, `cli_documentation`, `python_tooling`, `markdown_tooling`, and command-surface terms: confirmed stale-path surfaces and active docs/config touchpoints.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run pytest tests/coherence`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`, with proof that `docs/usage.md` is included.
* Run only after implementation: build/install an isolated wheel and smoke every in-scope installed command wrapper, or every explicitly public wrapper if aliases are scoped out.
* Run only after implementation: compare `[project.scripts]` keys plus `project-standards` parser leaves against the usage documentation inventory.
* Run only after implementation: `project-standards adopt cli-documentation --dry-run` or equivalent isolated CLI test proving two files are created/skipped as expected and the config fragment is reported.
* Run only after implementation: `rg -n "cli-framework"` and classify remaining hits as active stale references or historical provenance.
* Run only after implementation: package-content check that the `cli-documentation` bundle files and manifest are included in the wheel.
* Run only after implementation: inspect `src/project_standards/README.md` for stale CLI, registry, config, and bundle references.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md`
* Audit round: 2
* Open issue IDs: SA-NEW-001, SA-NEW-002
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: multi-entry-point dogfood scope, complete `project-standards` leaf-command inventory, installed-wrapper smoke coverage, and `src/project_standards/README.md` alignment.