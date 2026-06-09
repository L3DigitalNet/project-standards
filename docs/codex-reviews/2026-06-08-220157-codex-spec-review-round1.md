### Executive summary

The specification is not ready for Claude Code to use as the basis for planning or implementation. The largest blockers are repository-fit contradictions in the formatter rules: unconditional `doc_type` path inference would rewrite currently valid managed `README.md` standards documents into `doc_type: index`, and the proposed `fix` order can exit clean while leaving `id` invalid after `type`→`doc_type` or `doc_type` inference. The spec also omits the reusable workflow path that consumers actually use for validator enforcement.

Internet research was required for the external `.pre-commit-hooks.yaml` assumptions. Official pre-commit docs confirm the spec needs stronger hook-manifest validation than “entry resolves to a console script.”

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`
* Significant findings remaining: Yes
* Blocking issue count: 4
* Non-blocking issue count: 4

### What the specification gets right

The spec correctly preserves existing `validate-frontmatter`, `validate-id`, and `project-standards` surfaces as invariants; keeps new semantic validation opt-in; treats mutating formatting separately from read-only validation; adds a hardcoded refusal set for agent-instruction files; and requires focused tests for idempotence, line-ending preservation, denylist behavior, and exit codes.

### Adversarial review performed

I inventoried the A/B/C requirements, CLI/config contracts, formatter transforms, reference-validator checks, acceptance criteria, and release/versioning claims. I falsified them against `pyproject.toml`, `.project-standards.yml`, the current schema, `validate_frontmatter.py`, `validate_id.py`, `cli.py`, the reusable workflow, standards docs, shipped examples, test conventions, and official pre-commit documentation.

I did not run mutating validators, tests, package-manager commands, or pre-commit commands because this audit is read-only and those can create caches or artifacts.

### Blocking issues

#### SA-001: Unconditional `doc_type` path inference contradicts current managed docs and can break IDs

* Severity: High
* Status: Confirmed
* Adversarial angle: A formatter rule that sounds deterministic can silently make valid documents invalid.
* Spec reference: Lines 50, 87-94, 181.
* Finding: The spec requires `README.md`/`index.md` to become `doc_type: index`, overriding even valid explicit values, while also saying `format-frontmatter` does not touch `id`. Current managed standards `README.md` files are valid `doc_type: reference` documents with `reference-...` IDs. Rewriting only `doc_type` would create an `id`/`doc_type` mismatch that `validate-id` rejects.
* Repository evidence: `.project-standards.yml` includes `standards/**/*.md` and excludes only `standards/README.md`, templates, and python-coding; `standards/markdown-frontmatter/README.md`, `standards/adr/README.md`, `standards/markdown-tooling/README.md`, and `standards/python-tooling/README.md` all have top-frontmatter `doc_type: 'reference'`. `validate_id.py` validates that ID prefix matches `doc_type`.
* External research evidence: Not applicable.
* Why it matters: The dogfood criterion “`format-frontmatter --check` on the repo is clean” cannot hold unless the spec either changes valid repo docs, excludes them, or narrows the inference rule. It also makes the “A does not touch `id`” invariant unsafe.
* Recommended action for Claude Code: Replace unconditional existing-document override with a narrower rule, such as path inference only for scaffolding or only when `doc_type` is missing/invalid. If any formatter transform can change `doc_type`, specify how `id` validity is preserved.
* Suggested validation: Add tests using current `standards/*/README.md`-style fixtures where `doc_type: reference` remains unchanged and `validate-id` still passes after formatting.

#### SA-002: `project-standards fix` order can exit clean while leaving invalid IDs

* Severity: High
* Status: Confirmed
* Adversarial angle: Acceptance can pass while the user’s intended “fix” outcome remains unmet.
* Spec reference: Lines 87, 167-168, 179.
* Finding: The spec runs `validate-id --fix` before `format-frontmatter --write`. Existing `validate-id` skips files without a valid `doc_type`. A file with `type: note` and an old invalid ID would be skipped by `validate-id`, then formatter would rename `type` to `doc_type`, leaving the invalid ID behind. The same risk applies when formatting changes `doc_type` through path inference.
* Repository evidence: `validate_id.py` skips missing/invalid `doc_type` during check and fix. The formatter is specified to perform `type:`→`doc_type:` and `doc_type` inference after `validate-id --fix` has already run.
* External research evidence: Not applicable.
* Why it matters: `project-standards fix` could return success and still leave a document that `project-standards validate` fails. That is a direct false-positive acceptance path.
* Recommended action for Claude Code: Specify an order that proves the postcondition, such as format structural fields first, then run `validate-id --fix`, then run formatter/check again if needed; or explicitly run final validation and fail if `id` remains invalid.
* Suggested validation: Add fixture tests for `type:` plus invalid ID, missing required arrays plus invalid ID, and path-inferred `doc_type`, asserting `project-standards fix` leaves final `project-standards validate` clean.

#### SA-003: Consumer reusable workflow is missing from the `validate-references` rollout

* Severity: High
* Status: Confirmed
* Adversarial angle: A new validator can be implemented but never run in the downstream enforcement path.
* Spec reference: Lines 36-40, 56, 168, 181-182.
* Finding: The repo’s consumer contract is enforced through `.github/workflows/validate-markdown-frontmatter.yml`, but the spec only extends `project-standards validate`. It does not require the reusable workflow to run `validate-references` or the unified `project-standards validate`.
* Repository evidence: The reusable workflow currently runs `validate-frontmatter` and `validate-id` separately for this repo and consumers. README and `meta/versioning.md` state that consuming repos use the reusable workflow for Frontmatter/ADR enforcement.
* External research evidence: Not applicable.
* Why it matters: A consumer can set `references.enabled: true` and still get no CI coverage if they follow the documented workflow adoption path.
* Recommended action for Claude Code: Add an explicit workflow requirement, tests/documentation for it, and clarify whether the workflow should call `project-standards validate` or add a third standalone `validate-references` step.
* Suggested validation: Add tests or static assertions that the reusable workflow invokes the reference validator, and run the workflow-equivalent local commands after implementation.

#### SA-004: Unsupported-YAML rule excludes schema-valid extension objects

* Severity: High
* Status: Confirmed
* Adversarial angle: The formatter claims to cover the standard surface while skipping valid standard fields.
* Spec reference: Lines 93, 118-124, 181.
* Finding: The spec says supported value shapes cover the entire standard surface, then says nested mappings are unsupported. The schema explicitly allows `publish`, `project`, and `x_project` objects, and shipped examples use `project:` mappings in top frontmatter.
* Repository evidence: Schema lines for `publish`, `project`, and `x_project` allow objects. `standards/adr/examples/adr.example.md` and `standards/markdown-frontmatter/examples/runbook.example.md` include top-level `project:` mappings, and examples are included by this repo’s config.
* External research evidence: Not applicable.
* Why it matters: `format-frontmatter --check` on the repo cannot be clean if valid examples are skipped with warnings or failures. More broadly, valid consumer docs using sanctioned extension namespaces become second-class.
* Recommended action for Claude Code: Specify extension-object handling as opaque top-level entries that can be reordered without editing nested content, or explicitly narrow formatter scope and revise dogfood/acceptance criteria accordingly.
* Suggested validation: Add tests for `project:`, `publish:`, and `x_project:` blocks with nested mappings/lists, proving formatting preserves nested bytes and still reorders the top-level entry safely.

### Non-blocking issues

#### SA-005: `applies_to` is incorrectly treated as a document reference

* Severity: Medium
* Status: Confirmed
* Adversarial angle: A semantic validator can create noisy false positives against valid docs.
* Spec reference: Lines 147, 154.
* Finding: `validate-references` includes `applies_to` in referential integrity, but the standard says `applies_to` is free-form scope identifiers and is exempt from link/reference rules.
* Repository evidence: `standards/markdown-frontmatter/README.md` states `applies_to` is not a document link and holds free-form scopes.
* External research evidence: Not applicable.
* Why it matters: Valid values like service names, environments, or components would warn as dangling references.
* Recommended action for Claude Code: Remove `applies_to` from referential-integrity checks or define a separate optional scope validation with different rules.
* Suggested validation: Add a test where `applies_to: ['netbox', 'production']` produces no dangling-reference warning.

#### SA-006: Scaffold placeholder can pass all stated acceptance while remaining incomplete

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Acceptance criteria can pass without satisfying the authoring goal.
* Spec reference: Lines 106-116, 177, 181.
* Finding: The spec says scaffolded blocks pass the schema and that `validate-frontmatter` “closes the gap,” but the placeholder description is schema-valid and no validator detects `TODO:`.
* Repository evidence: The schema only requires `description` to be a non-empty string; the standard’s stricter description rules are documented conventions, not machine-enforced.
* External research evidence: Not applicable.
* Why it matters: A scaffolded repo can validate clean while containing placeholder metadata.
* Recommended action for Claude Code: Clarify whether placeholders are acceptable post-fix output. If not, add a warning/check for placeholder descriptions or require `format-frontmatter --write` to report scaffolded files distinctly.
* Suggested validation: Add tests asserting scaffold output either fails a semantic placeholder check or emits a warning that authors must resolve manually.

#### SA-007: Pre-commit hook acceptance is too weak

* Severity: Medium
* Status: Needs Claude verification
* Adversarial angle: A manifest can look internally consistent but fail as a real pre-commit hook repository.
* Spec reference: Lines 170-172, 198.
* Finding: The spec only requires parsing `.pre-commit-hooks.yaml` and checking entries against `[project.scripts]`. It does not require official manifest validation, language selection, hook file matching, `pass_filenames`, mutating/check-only behavior, or a real `try-repo` smoke test.
* Repository evidence: No `.pre-commit-hooks.yaml` exists today. `pyproject.toml` uses `[project.scripts]`, so Python hook entries can plausibly work, but the manifest shape is still unspecified.
* External research evidence: Official pre-commit docs say Python hook repositories must be installable with `pip install .` and the installed package should provide an executable matching the hook entry. The docs also provide `pre-commit validate-manifest` for `.pre-commit-hooks.yaml` files and recommend pinned `rev` values. Source: https://pre-commit.com/ accessed 2026-06-09.
* Why it matters: Acceptance could pass while consumers cannot install or run the hooks.
* Recommended action for Claude Code: Specify hook language, file types, args, `pass_filenames`, stages if needed, and validation with `pre-commit validate-manifest` plus at least one `try-repo` smoke.
* Suggested validation: After implementation, run `pre-commit validate-manifest .pre-commit-hooks.yaml` and `pre-commit try-repo . format-frontmatter-check --all-files`.

#### SA-008: Custom-schema behavior is unspecified for new formatter/fix commands

* Severity: Medium
* Status: Unclear
* Adversarial angle: Existing custom-schema consumers may manually run a new command that assumes bundled semantics.
* Spec reference: Lines 63-67, 89, 167-168, 192.
* Finding: Existing `validate-id` skips custom schemas because custom schemas may define different ID conventions. The spec does not say what `format-frontmatter` or `project-standards fix` should do when `markdown.frontmatter.schema` is a custom path.
* Repository evidence: `validate_frontmatter.py` supports custom schema paths; `validate_id.py` skips when `--schema` or config schema is custom.
* External research evidence: Not applicable.
* Why it matters: The formatter would inject bundled `schema_version`, canonical keys, `doc_type` rules, and ID-adjacent transforms into a consumer-owned schema context.
* Recommended action for Claude Code: Define whether formatter/fix refuse, warn, skip bundled-only transforms, or explicitly only support bundled schemas.
* Suggested validation: Add tests for config-level custom schema and `--schema`, matching the existing `validate-id` custom-schema skip contract.

### Missing specification considerations

* Blocking: Final postcondition for `project-standards fix`: the spec should require a final read-only validation or prove that the two mutating passes cannot leave invalid IDs.
* Blocking: Consumer CI enforcement: the reusable workflow must be included in scope if `validate-references` is part of the validator-enforced standard.
* Blocking: Formatter support for `publish`/`project`/`x_project` extension objects.
* Non-blocking: Symlink, atomic-write, partial-write, and rollback behavior for `format-frontmatter --write`.
* Non-blocking: Exact warning semantics: whether warnings make `--check` dirty, whether skipped unsupported YAML exits 0 or 1, and what “repo passes” means when warnings are allowed.
* Non-blocking: Custom-schema behavior for formatter/fix.
* Non-blocking: Pre-commit manifest validation and real install/run smoke tests.
* Non-blocking: `--stdin` incompatibilities with `FILE`, `--glob`, `--write`, and `--check`.

### Ambiguities and decisions needed

* Ambiguity: Does `doc_type` path inference apply to existing valid frontmatter or only to scaffolding/missing values?
* Why it matters: Existing managed standards READMEs are `reference`, not `index`.
* Recommended clarification: Restrict inference or define an ID-safe migration rule.
* Blocking or non-blocking: Blocking.

* Ambiguity: Does a warning-only `validate-references` result count as “passes” for dogfood and CI?
* Why it matters: Warnings exit 0, but noisy gates can still be treated as failures by maintainers.
* Recommended clarification: Define expected stderr cleanliness separately from exit code.
* Blocking or non-blocking: Non-blocking.

* Ambiguity: Should `format-frontmatter --check` fail on unsupported YAML skips?
* Why it matters: Current valid examples contain extension mappings the spec currently calls unsupported.
* Recommended clarification: Define skip exit code and whether extension objects are supported.
* Blocking or non-blocking: Blocking.

### Internet research performed

* Source name: pre-commit official documentation
* URL: https://pre-commit.com/
* Access date: 2026-06-09
* What it was used to verify: `.pre-commit-hooks.yaml` manifest validation, Python hook repository requirements, pinned `rev` expectations, and real hook-run validation options.
* Relevant conclusion: The spec should require `pre-commit validate-manifest` and a real hook smoke test; checking only that `entry` names exist in `[project.scripts]` is insufficient.

### Items Claude Code should verify before correcting the specification

* Re-check the current managed file set from `.project-standards.yml`, especially `standards/*/README.md` and shipped examples.
* Verify whether the formatter should support extension-object fields as opaque entries.
* Verify whether the reusable workflow should call `project-standards validate` or standalone validators.
* Verify intended behavior for custom schemas.
* Verify pre-commit hook language, args, file matching, and check/fix hook behavior against official docs.

### Suggested corrections for Claude Code’s specification

* Narrow `doc_type` path inference and make it ID-safe.
* Change `project-standards fix` ordering or require a final validation postcondition.
* Add explicit reusable workflow changes and tests for `validate-references`.
* Support `publish`/`project`/`x_project` mappings or revise scope and dogfood criteria.
* Remove `applies_to` from document-reference validation.
* Define placeholder-scaffold warnings or checks.
* Add custom-schema behavior for formatter/fix.
* Strengthen `.pre-commit-hooks.yaml` acceptance with `validate-manifest` and `try-repo`.

### Read-only validation performed

* `git status --short` and `git log --oneline -n 10`: confirmed branch state is dirty and recent spec commit exists; no changes were made.
* Read the spec with `sed` and `nl -ba`: inventoried requirements and line references.
* `rg --files`: mapped repository structure and relevant source/test/docs surfaces.
* Inspected `pyproject.toml`, `.project-standards.yml`, schema, `validate_frontmatter.py`, `validate_id.py`, `cli.py`, reusable workflows, README, versioning docs, standards docs, and test strategy.
* Used `rg` to check current console scripts, workflow validation commands, managed `doc_type` values, extension-object usage, and absence of `.pre-commit-hooks.yaml`.
* Inspected `git diff --stat` and current diffs to understand unrelated dirty work without modifying it.
* Opened official pre-commit documentation via web research.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run project-standards validate --config .project-standards.yml`
* Run only after implementation: `uv run format-frontmatter --check --config .project-standards.yml`
* Run only after implementation: `uv run validate-references --config .project-standards.yml` with a temporary config enabling references.
* Run only after implementation: `pre-commit validate-manifest .pre-commit-hooks.yaml`
* Run only after implementation: `pre-commit try-repo . format-frontmatter-check --all-files`

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007, SA-008
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: ID/doc_type safety after formatting, reusable workflow coverage, extension-object support, `applies_to` semantics, pre-commit manifest validation, custom-schema behavior, and acceptance criteria false positives.

