### Executive summary

Claude Code’s round-2 corrections substantively resolve the multi-entry-point dogfood scope and `src/project_standards/README.md` alignment findings. One part of SA-NEW-001 remains partially unresolved: the revised spec repeatedly says `project-standards` has 11 leaf commands, but repository evidence shows 10 leaf commands plus the non-leaf `spec` group. I also found one new non-blocking acceptance-criteria gap: the dogfood validation can prove command-entry inventory without proving option/exit-code documentation matches parser behavior.

No new internet research was required in this round; the remaining issues are repository-fit and acceptance-strength issues against local source evidence.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md`
* Prior audit issue count: 8
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested SA-001..SA-006 and SA-NEW-001..SA-NEW-002 against the revised spec, current `[project.scripts]`, `project-standards` parser dispatch, nested `spec` verb table, package CLI README, registry/bundle/adopt tests, frontmatter config, and release/versioning docs.

Attacked the corrected acceptance criteria for false positives around full installed-command coverage, leaf-command counting, source-package README drift, installed-wrapper smoke coverage, `docs/usage.md` inclusion, stale `cli-framework` references, and whether command inventory checks also prove option/exit-code documentation correctness.

Could not run implementation gates, wheel builds, `uv run`, pytest, or frontmatter validation because this audit is read-only and those commands may write caches, build artifacts, coverage data, dependency state, or generated outputs.

### Prior findings status

#### SA-001: Dogfood profile contradicts the standard’s own deep-profile rule

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec keeps Packaged as a recorded adopter judgment and says nesting is only a signal, not an automatic Packaged-deep trigger.
* Remaining action for Claude Code: None.

#### SA-002: Mandatory `--version` requirement is not carried into implementation scope or acceptance

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now requires `--version` on every installed command and requires installed-wrapper tests for all seven wrappers.
* Remaining action for Claude Code: None.

#### SA-003: `docs/usage.md` can escape frontmatter validation

* Previous severity: High
* Current status: Resolved
* Evidence: The spec requires adding `docs/usage.md` to `.project-standards.yml` include globs and proving it appears in the validated-file set.
* Remaining action for Claude Code: None.

#### SA-004: Existing manifest tests do not automatically enforce new bundle byte identity

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec requires explicit byte-identity mappings for the `cli-documentation` bundle artifacts.
* Remaining action for Claude Code: None.

#### SA-005: Installed-entry-point smoke test is underspecified

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec defines a wheel-build plus throwaway-venv installed-wrapper smoke test for all seven wrappers and a nested `project-standards spec` subcommand.
* Remaining action for Claude Code: None for smoke mechanics. Address SA-NEW-003 separately for documentation parity strength.

#### SA-006: “No `cli-framework/` path remains anywhere” is overbroad

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now limits failure to active stale references and explicitly exempts historical provenance.
* Remaining action for Claude Code: None.

#### SA-NEW-001: Dogfood scope omits installed console scripts and top-level commands

* Previous severity: High
* Current status: Partially resolved
* Evidence: The spec now covers all seven `[project.scripts]` keys, treats all standalone wrappers as public, adds `--version` to every wrapper, requires all-wrapper smoke tests, and requires an inventory-parity guard. However, it now states the `project-standards` CLI has “11 leaf commands” in lines 62, 152, 153, and 208. Repository evidence shows four top-level leaf commands (`validate`, `fix`, `adopt`, `list`) plus six nested `spec` verbs (`validate`, `lint`, `extract`, `next`, `new`, `upgrade`) for 10 leaf commands. `spec` itself is a group, not a leaf.
* Remaining action for Claude Code: Correct the command count to 10 leaf commands, or explicitly define that top-level `project-standards spec --help` is a separately documented group entry and do not call it a leaf command.

#### SA-NEW-002: Active package CLI README is omitted from touchpoints

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now adds `src/project_standards/README.md` to repo touchpoints and acceptance criteria, requiring it to be repositioned as an implementation-internals reference that links to `docs/usage.md` as authoritative.
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-003: Dogfood acceptance proves command inventory but not option/exit-code parity

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Can `docs/usage.md` pass the new dogfood checks while omitting or misdocumenting flags, defaults, exit codes, or parser behavior?
* Spec reference: Lines 88-93, 158-169, 208-211, 229.
* Finding: The standard’s own rules require every documented option to include spelling, value syntax, defaults, allowed values, safety impact, and interactions, and say the usage doc is the exhaustive contract. The dogfood tests and acceptance criteria require installed-wrapper smoke tests and command-inventory parity, but they do not require parser/help-output parity for options or exit-status sections. A `docs/usage.md` containing all command headings could satisfy the inventory guard while still being materially stale or incomplete.
* Repository evidence: `src/project_standards/cli.py` defines early-dispatched top-level commands with hand-built help for `validate` and `fix`, while `src/project_standards/specs/cli.py` defines six nested verbs with distinct parsers and flags. `src/project_standards/README.md` currently carries detailed option tables, showing that option-level drift is a real existing documentation surface.
* External research evidence: Not applicable.
* Why it matters: The proposed standard is specifically meant to prevent user-facing CLI docs drift. Inventory-only validation could provide false confidence: all commands are present, but flags, defaults, exit codes, or safety behavior are wrong.
* Recommended action for Claude Code: Add a dogfood acceptance requirement that option and exit-code documentation is checked against parser/help behavior, either by normalized help snapshots for every installed wrapper/leaf command, a parser-derived option inventory, or an explicit manual parity review checklist recorded in the implementation evidence.
* Suggested validation: After implementation, compare each documented command’s `OPTIONS` and `EXIT STATUS` sections against normalized `--help` output and source-defined exit-code behavior. At minimum, require the implementation notes to enumerate any intentionally manual assertions.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Does “11 leaf commands” include the top-level `project-standards spec` group help as a documented entry?
* Why it matters: Repository parser evidence shows 10 true leaves. Leaving the count wrong can make acceptance either impossible or encourage documenting a non-leaf command under the wrong category.
* Recommended clarification: State “10 leaf commands plus the `spec` group overview” if group help must be documented, or change all references to “10 leaf commands.”
* Blocking or non-blocking: Non-blocking.

* Ambiguity: What level of doc-to-parser parity is required for this repo’s own dogfood usage doc?
* Why it matters: Command inventory parity alone does not prove options, defaults, exclusions, environment interactions, or exit codes are correct.
* Recommended clarification: Require normalized help snapshots, parser-derived option inventory, or a documented manual parity pass for every command entry.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

No new internet research was necessary. The round-3 changes and remaining findings concern local repository command inventory, local parser structure, and acceptance-criteria strength. External entry-point and argparse assumptions were not materially changed from the prior audit.

### Read-only validation performed

* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git diff --stat`: confirmed branch `testing`, latest relevant commits addressing round 2, and no local diff output.
* `nl -ba docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md | sed -n '1,280p'`: re-read the current revised spec and verified round-2 corrections.
* `nl -ba pyproject.toml | sed -n '1,80p'`: confirmed seven installed console scripts.
* `nl -ba src/project_standards/cli.py | sed -n '120,330p'`: confirmed top-level `project-standards` command structure and the four top-level leaf commands.
* `nl -ba src/project_standards/specs/cli.py | sed -n '560,620p'`: confirmed the six nested `spec` verbs.
* `sed` / `nl` inspections of `src/project_standards/README.md`: confirmed the active package README’s current CLI-reference role and command surface.
* Inspected `.project-standards.yml`, registry files, adopt manifest tests, adopt CLI tests, dogfood tests, packaging tests, root README, standards index, and `meta/versioning.md`: checked repo-fit claims, current standard/bundle counts, and validation surfaces.
* Ran targeted `rg` searches for `cli-framework`, `cli-documentation`, `cli_documentation`, `docs/usage.md`, `--version`, console-script terms, and standards-count references: verified active stale-reference surfaces and revised spec claims.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run pytest tests/coherence`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`, with proof that `docs/usage.md` is included.
* Run only after implementation: build/install an isolated wheel and smoke all seven installed command wrappers for `--help` and `--version`.
* Run only after implementation: compare `[project.scripts]` keys plus actual `project-standards` parser leaves against `docs/usage.md`; expect 10 leaves unless the spec explicitly defines a separate group-overview entry.
* Run only after implementation: compare documented options and exit statuses against normalized help/parser/source behavior for every documented command.
* Run only after implementation: `project-standards adopt cli-documentation --dry-run` or equivalent isolated CLI test proving the expected artifacts and config fragment.
* Run only after implementation: `rg -n "cli-framework"` and classify remaining hits as active stale references or historical provenance.
* Run only after implementation: package-content check that the `cli-documentation` bundle files and manifest are included in the wheel.
* Run only after implementation: inspect `src/project_standards/README.md` for stale CLI, registry, config, and bundle references.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md`
* Audit round: 3
* Open issue IDs: SA-NEW-001, SA-NEW-003
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-NEW-002
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: correcting the `project-standards` leaf-command count, deciding whether `spec` group help is separately documented, and strengthening dogfood acceptance so option and exit-code documentation cannot drift behind parser behavior.