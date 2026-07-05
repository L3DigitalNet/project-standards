### Executive summary

The specification is not ready for Claude Code to use as the basis for planning or implementation. Its high-level goal and command surface fit the repository, but several safety and correctness guarantees are stronger than the validator and current code can support. The most important problems are that a `validate`-clean spec can still contain author prose in places the proposed splice treats as filler or template-owned, and a valid source with an already-present non-prefix subsection can make the proposed insertion algorithm self-fail.

Internet research was required for the Python filesystem assumptions. Official Python 3.14 docs support the `os.replace` atomic-rename premise, but the local specification issues are repository-contract issues, not stale external-doc issues.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md
* Significant findings remaining: Yes
* Blocking issue count: 3
* Non-blocking issue count: 3

### What the specification gets right

* It correctly identifies `upgrade` as the remaining v1-core project-spec authoring command; `TODO.md:25` confirms `upgrade` is the only deferred project-spec tooling command.
* The proposed CLI shape is conservative: preview by default, explicit `--in-place` / `--output`, `--json`, and exit-2 refusal paths align with the existing `spec new` style.
* The spec correctly recognizes that `validate` only gap-checks top-level numbered sections, not dotted subsection gaps.
* The versioning claim that adding an opt-in command is MINOR is consistent with `meta/versioning.md:101-117`.

### Adversarial review performed

I inventoried the spec’s command contract, tier rules, splice algorithm, write-safety claims, JSON contract, acceptance criteria, and version/docs claims. I then checked them against the repository’s current spec CLI, parser, validator, registry, bundled templates, fixtures, test coverage, README/TODO/versioning docs, and Python filesystem documentation.

The strongest challenged assumptions were:

* that full `validate` proves author content cannot exist in inter-section gaps;
* that replacing Appendix A / Appendix D is safe despite “preserve author bytes” and in-place mutation guarantees;
* that already-present subsections can be handled by “insert after the last present subsection”;
* that `new`’s write helper can be reused “verbatim” while producing different overwrite and JSON semantics;
* that `config_error` belongs in `upgrade` despite no `--config` surface.

I did not run mutating validation gates such as pytest, coverage, ruff, basedpyright, pip-audit, or `uv run` commands.

### Blocking issues

#### SA-001: `validate` does not prove the load-bearing “no author gap content” invariant

* Severity: High
* Status: Confirmed
* Adversarial angle: Can a validate-clean source contain author prose exactly where the splice assumes only filler exists?
* Spec reference: Lines 62-70, especially “decision 3 (fail-closed input) guarantees” and “Author content lives only inside canonical sections.”
* Finding: The spec’s central splice invariant is false. The current validator checks canonical section numbers, numeric order, annotated top-level gaps, appendices, references, IDs, and tables, but it does not reject arbitrary prose between canonical sections or around omission notes.
* Repository evidence: `src/project_standards/specs/commands/validate.py:72-104` only scans blockquote omission notes and missing top-level numbers; it does not enforce “only divider/blank/omission-note filler” between sections. An in-memory mutation of `tests/fixtures/specs/valid_light.md` inserting `Author prose in a top-level gap.` before the §3-§6 omission note still returned `[]` findings from `validate_document`.
* External research evidence: Not applicable.
* Why it matters: The splice is specified to edit or replace filler at heading boundaries. If author text can exist in those gaps while still passing the input gate, `upgrade` can silently preserve stale text in the wrong tier context, place inserted sections around it incorrectly, or fail self-validation after doing non-obvious transformations. The spec’s safety proof does not hold.
* Recommended action for Claude Code: Revise the spec to either add an explicit pre-splice structural guard that rejects non-filler gap content with a dedicated error, or define a safe preservation strategy for gap content. Do not claim full `validate` alone proves this invariant.
* Suggested validation: Add tests that construct validate-clean specs with prose before/after omission notes and verify `upgrade` either preserves it at a defined location or refuses before writing.

#### SA-002: Already-present subsections can be valid but break the proposed insertion order

* Severity: High
* Status: Confirmed
* Adversarial angle: Does the “insert missing subsections after the last present subsection” rule work for any validate-clean source, or only for prefix-shaped subsection sets?
* Spec reference: Lines 70 and 168-170; test claim at line 257.
* Finding: A Light source can validate while already containing `### 7.3` but not `### 7.2`. The spec says missing subsections are inserted after the last present subsection, which would place `7.2` after `7.3` and produce an out-of-order document, contradicting U1 and the “already-present subsection” test goal.
* Repository evidence: `validate.py:86-89` checks numeric order but not dotted gaps; an in-memory mutation adding `### 7.3 Interface Requirements` after Light §7.1 produced no validation findings. `validate.py:84-89` would reject a later output ordered `7.1, 7.3, 7.2, 7.4` as `SV-ORDER`.
* External research evidence: Not applicable.
* Why it matters: The tool can refuse a valid source that meets the spec’s own input contract, simply because the algorithm assumes already-present subsections are a contiguous prefix. That breaks “for every additive tier pair” and makes the acceptance criteria too broad for the described algorithm.
* Recommended action for Claude Code: Specify positional insertion by canonical subsection order, not “after the last present subsection.” Define behavior for non-prefix subsection sets, including preservation of already-present author subsections and insertion of missing predecessors/successors around them.
* Suggested validation: Add fixtures where Light has only `7.3`, only `17.3`, or Standard has `8.6` without `8.4`, and assert the output is ordered, non-duplicated, and validates.

#### SA-003: Template-owned Appendix A/D replacement can silently delete validate-clean author content

* Severity: High
* Status: Confirmed
* Adversarial angle: Can an in-place upgrade lose author-written content while still satisfying the source `validate` precondition?
* Spec reference: Lines 46, 76-84, 157-164, and 168-170.
* Finding: The spec treats Appendix A and Appendix D as template-owned and replaced wholesale, but `validate` does not prevent author edits inside those appendices. This contradicts the stated mutation-risk premise and “author bytes preserved” safety posture for an in-place command.
* Repository evidence: `validate_document` accepts arbitrary prose in Appendix A and Appendix D if it does not break the checked tables/IDs. In-memory mutations adding author prose inside Appendix A and inside Appendix D of `valid_light.md` returned `[]` findings. Current templates include Appendix A and D in all tiers, so this is not a missing-unit insertion; it is replacement of existing source content.
* External research evidence: Not applicable.
* Why it matters: A user can run `upgrade -i` on a valid spec and lose notes or local conventions stored in Appendix A/D. Even if those appendices are intended to be canonical boilerplate, the current standard/validator does not make that contract enforceable.
* Recommended action for Claude Code: Clarify Appendix A/D ownership. Either refuse if template-owned appendices differ from the expected canonical source, preserve non-canonical author additions in a defined way, or explicitly document that those appendices are overwritten and add a preview/validation warning before any in-place write.
* Suggested validation: Add tests where Appendix A/D contain extra validate-clean author prose and assert the command refuses or preserves it according to the revised contract.

### Non-blocking issues

#### SA-004: “Reuse `_write_new_file` verbatim” conflicts with upgrade’s own write and JSON contract

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Can the existing `new` write helper be reused exactly while satisfying `upgrade` semantics?
* Spec reference: Lines 183 and 190-194.
* Finding: The existing `_write_new_file` is coupled to `spec new`: it refuses overwrites unless `args.force`, expects `args.path`, emits `profile` and `overwritten` JSON fields, and uses `NewOptions`. `upgrade -i` must overwrite normally, preserve source mode, and emit `from_profile`, `to_profile`, `mode`, and no `overwritten` field in the documented payload.
* Repository evidence: `src/project_standards/specs/cli.py:229-286` implements `_write_new_file`; its JSON payload at lines 263-274 does not match the upgrade contract at spec lines 222-241, and overwrite refusal at lines 238-239 conflicts with normal in-place rewrite.
* External research evidence: Python docs support `os.replace` as an atomic successful rename; see Python 3.14 `os.replace` docs, accessed 2026-07-05: https://docs.python.org/3.14/library/os.html#os.replace.
* Why it matters: The implementation plan could either reuse too much and get wrong behavior, or ignore the “verbatim” instruction. The spec should identify the reusable safety primitive separately from the `new` command’s command-specific policy and JSON layer.
* Recommended action for Claude Code: Change the spec to require extracting or sharing an atomic-write helper, while keeping upgrade-specific overwrite policy and JSON emission in `_run_upgrade`.
* Suggested validation: Tests should assert `-i` overwrites without `--force`, preserves mode, and emits the documented upgrade JSON shape.

#### SA-005: `config_error` is specified without a config surface or clear need

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Does `upgrade` need `.project-standards.yml`, and if so where is that CLI contract defined?
* Spec reference: CLI syntax lines 88-100; error table line 213; JSON slug list line 250.
* Finding: The CLI surface has no `--config` flag and the execution flow only needs `SRC`, registry/templates, parse, and `validate_document`. Yet the error contract includes “Config present but unreadable / unparseable” and a reused `config_error` slug.
* Repository evidence: Existing `new` needs config for ID collision checks (`cli.py:163-166`), but `upgrade` preserves `spec_id` and does not collect repo IDs. Existing direct-file validate paths can parse/validate without repo-wide config when files are passed.
* External research evidence: Not applicable.
* Why it matters: This creates unnecessary coupling to repo config and a false failure mode. A direct file upgrade should not fail because an unrelated `.project-standards.yml` is malformed unless the spec deliberately adds a config-dependent feature.
* Recommended action for Claude Code: Remove `config_error` from `upgrade`, or add an explicit `--config` option with a concrete purpose. Prefer no config dependency unless required.
* Suggested validation: Add a test with malformed `.project-standards.yml` and explicit `SRC`; expected behavior should be defined by the revised spec.

#### SA-006: Documentation impact omits the package CLI reference

* Severity: Low
* Status: Confirmed
* Adversarial angle: Could the command ship with implementation and standard README updated but developer-facing CLI docs stale?
* Spec reference: Lines 283-287.
* Finding: The docs impact section only names README §5, TODO/CHANGELOG, and project-spec adoption state. It does not mention `src/project_standards/README.md`, whose CLI surface table currently omits the `project-standards spec` group entirely.
* Repository evidence: `src/project_standards/README.md:30-44` lists console commands but not the nested `project-standards spec` command group. `src/project_standards/cli.py:245` also needs help text expansion.
* External research evidence: Not applicable.
* Why it matters: This is not implementation-blocking, but it can leave the command discoverability and developer docs stale.
* Recommended action for Claude Code: Add a docs-impact bullet for package CLI documentation, or explicitly state that `src/project_standards/README.md` remains out of scope for this spec.
* Suggested validation: After implementation, inspect CLI help and package README for the new subcommand.

### Missing specification considerations

* Blocking: Define a guard or preservation rule for non-filler content in inter-section and inter-appendix gaps. Current `validate` does not enforce the assumed invariant.
* Blocking: Define behavior for non-prefix subsection sets, such as Light containing `7.3` but not `7.2`.
* Blocking: Define how template-owned appendices handle validate-clean author edits before any in-place replacement.
* Non-blocking: Separate the atomic-write primitive from `new`-specific overwrite policy and JSON payload.
* Non-blocking: Decide whether `upgrade` has any config dependency; if not, remove `config_error`.
* Non-blocking: Add package CLI docs to the docs-impact checklist.
* Non-blocking: Add negative tests for output path equality through symlinks and missing-output fallback path comparisons.
* Non-blocking: State whether full-template optional Appendix C modules are inserted wholesale on Standard→Full even when a user may later delete unused modules; the spec implies yes, but acceptance criteria should pin that.

### Ambiguities and decisions needed

* Ambiguity: Are Appendix A and Appendix D strictly standard-owned boilerplate in user specs, or can authors add local content there?
* Why it matters: The current splice would overwrite them, which can lose author work.
* Recommended clarification: State whether modified Appendix A/D causes refusal, preservation, or overwrite-with-warning.
* Blocking or non-blocking: Blocking

* Ambiguity: Are already-present subsections allowed to be any canonical subsection, or only a contiguous prefix of the target subsection set?
* Why it matters: Current validator permits non-prefix sets; the proposed algorithm does not safely handle them.
* Recommended clarification: Define canonical positional insertion for arbitrary existing subsets, or reject non-tier-shaped subsection sets before splicing.
* Blocking or non-blocking: Blocking

* Ambiguity: Does `upgrade` read `.project-standards.yml`?
* Why it matters: The CLI syntax omits config, but the error table includes config failure.
* Recommended clarification: Remove config handling or add a concrete `--config` contract.
* Blocking or non-blocking: Non-blocking

### Internet research performed

* Source name: Python 3.14 documentation, `os.replace`
* URL: https://docs.python.org/3.14/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: Whether `os.replace` supports the spec’s atomic replacement assumption.
* Relevant conclusion: Official docs state that if successful, the rename/replace operation is atomic, and existing file destinations are replaced if permissions allow.

* Source name: Python 3.14 documentation, `pathlib.Path.mkdir`
* URL: https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.mkdir
* Access date: 2026-07-05
* What it was used to verify: Behavior of `mkdir(parents=True, exist_ok=True)` for parent auto-creation.
* Relevant conclusion: Official docs confirm missing parents are created as needed, matching the spec’s note that parent directories may be created before later write failure.

* Source name: Python 3.14 documentation, `pathlib.Path.samefile`
* URL: https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.samefile
* Access date: 2026-07-05
* What it was used to verify: Availability of `Path.samefile` for output-equals-source checks.
* Relevant conclusion: Official docs list `Path.samefile`; the spec still needs to define missing-output fallback behavior clearly.

### Items Claude Code should verify before correcting the specification

* Verify whether project-spec authors are expected to edit Appendix A/D, and whether the standard should forbid, preserve, or overwrite those edits.
* Verify whether the intended input domain is “any `validate`-clean spec” or “validate-clean plus stricter upgradeable-shape preconditions.”
* Verify whether `upgrade` should ever consult `.project-standards.yml`.
* Verify whether the package CLI README should become part of this spec’s docs scope.
* Verify whether aligned light/standard/full fixture triples should be newly created rather than trying to reuse current independently authored fixtures.

### Suggested corrections for Claude Code’s specification

* Replace the claim that `validate` guarantees no gap author content with a new explicit `upgrade` structural precheck or preservation rule.
* Change subsection insertion from “after the last present subsection” to canonical positional insertion for every missing subsection.
* Add tests for non-prefix already-present subsections.
* Define Appendix A/D overwrite semantics and add tests for modified appendices.
* Replace “reuse `_write_new_file` verbatim” with “reuse/extract the atomic write safety primitive; keep upgrade-specific policy and JSON in upgrade.”
* Remove `config_error` from the upgrade contract unless a real `--config` option is added.
* Expand docs-impact scope to include `src/project_standards/README.md` or explicitly exclude it.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`: confirmed working tree was clean.
* `git branch --show-current`: confirmed branch is `testing`.
* `git log --oneline -n 10`: confirmed recent spec-tooling history, including Spec #3 plan and Spec #2/new implementation commits.
* Inspected the spec file with `sed` and `nl -ba`: inventoried requirements, splice rules, write model, JSON contract, tests, acceptance criteria, docs/versioning claims.
* `rg --files src/project_standards tests standards/project-spec docs/superpowers meta`: identified relevant source, template, fixture, and docs files.
* `rg -n "upgrade|status|semantic-review|v1-core|..." ...`: checked repository references to `upgrade`, current TODOs, templates, and validators.
* Inspected `src/project_standards/specs/cli.py`: confirmed current `spec` verbs are `validate|lint|extract|next|new`, and inspected `new` write/error helpers.
* Inspected `src/project_standards/specs/commands/new.py`: confirmed `_rewrite_frontmatter` and `_rewrite_h1` behavior.
* Inspected `src/project_standards/specs/document.py`, `registry.py`, and `commands/validate.py`: checked parser/validator guarantees and registry-derived tier data.
* Inspected `tests/test_spec_new*.py`, `test_template_conformance.py`, and `test_template_interchangeability.py`: checked existing patterns and current coverage shape.
* Compared bundled and standards templates with `cmp -s`: confirmed `src/project_standards/specs/templates/*` match `standards/project-spec/templates/*`.
* Inspected project-spec README, templates, fixtures, `.project-standards.yml`, `meta/versioning.md`, `TODO.md`, and package README: checked standard claims, docs scope, release classification, and deferred work.
* Ran read-only in-memory validator probes with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /usr/bin/python3 - <<'PY' ...`: confirmed arbitrary gap prose, modified Appendix A/D prose, and a Light spec with `### 7.3` but no `### 7.2` can still validate clean.
* Attempted `PYTHONDONTWRITEBYTECODE=1 python - <<'PY' ...`: command failed because the repo environment requires `uv run python -`; reran with `/usr/bin/python3` and `PYTHONPATH=src` to avoid mutating dependency state.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: targeted `tests/test_spec_upgrade.py` and `tests/test_spec_upgrade_cli.py` covering gap-content refusal/preservation, modified Appendix A/D behavior, non-prefix subsection insertion, JSON payloads, in-place mode preservation, symlink targets, symlinked parents, output-equals-source, and malformed config behavior if retained.
* Run only after implementation: dogfood `project-standards spec upgrade` preview output piped into spec validation without writing repository files.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: whether the revised spec adds enforceable upgradeability preconditions or preservation rules for gap prose and appendices, fixes subsection insertion ordering for arbitrary validate-clean subsection sets, and removes the `_write_new_file` / config-contract inconsistencies.