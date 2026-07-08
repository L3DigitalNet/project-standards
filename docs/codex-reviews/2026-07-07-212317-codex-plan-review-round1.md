### Executive summary

The implementation plan needs correction before Claude Code executes it. The largest problems are internal, not external: the plan’s proposed `standard.toml` shape drops the `capabilities` section required by SPEC-MT01/SPEC-BA01, and its minimal meta-standard manifest contradicts SPEC-BA01’s resolved OQ-002 decision that the worked example be complete.

Internet research was required for the Prettier/TOML validation assumptions. Official Prettier documentation confirms Prettier does not include a TOML parser in its listed parser set, and a local read-only probe confirmed `prettier --check pyproject.toml` exits with “No parser could be inferred.”

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md`
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 2

### What the plan gets right

* Correctly keeps schema/model/validator/registry work out of scope for SPEC-MT01 Steps 03–04.
* Correctly treats the new standard as internal/reference with `adoption = "none"` and no `adopt.md`.
* Correctly identifies the main authored bundle files under `standards/standard-bundle-authoring/`.
* Correctly includes frontmatter/id validation for the new managed Markdown README.
* Correctly calls out field-name consistency between README, real manifest, and template as a top risk.

### Adversarial review performed

I inventoried the plan’s claims about files, manifest shape, adoption mode, validation commands, handoff updates, excluded code paths, standards index updates, and release-freeze behavior. I checked those claims against the SPEC-BA01 source document, SPEC-MT01 §9, ADRs 0001/0002/0003/0004/0008/0013, `.project-standards.yml`, `standards/README.md`, root `README.md`, `AGENTS.md`, `CLAUDE.md`, `meta/versioning.md`, registry/config files, package pins, and git state.

The strongest assumptions tested were: “field shapes follow SPEC-MT01 §9,” “the minimal `standard.toml` can serve as the FR-010 worked example,” “Prettier can participate in TOML validation,” “only `standards/README.md`/`AGENTS.md` need index/anatomy updates,” and “validation can prove the plan’s intended behavior.”

Areas not executed: write-producing validation (`prettier --write`, commits, generated files, full tests through `uv run`) was not run due read-only audit constraints.

### Blocking issues

#### CR-001: Plan omits the required `capabilities` manifest section

* Severity: High
* Status: Confirmed
* Adversarial angle: Challenged the plan’s claim that its `standard.toml` field shape follows SPEC-MT01 §9 and satisfies SPEC-BA01 FR-002.
* Plan reference: Lines 81, 125-150, 184-218.
* Finding: The plan’s README outline, real `standard.toml`, and blank template omit `[capabilities]` / `provides`, while SPEC-MT01’s proposed `standard.toml` includes `[capabilities] provides = [...]`, and SPEC-BA01 FR-002 requires the README to document “capabilities” as part of the manifest contract.
* Repository evidence: SPEC-MT01 lines 469-471 define `[capabilities]`. SPEC-BA01 FR-002 requires capabilities in the manifest contract. The plan’s manifest/template sections have `[standard]`, `[versions]`, `[config]`, `[relations]`, `[resources]`, `[[authority]]`, and `[[providers]]`, but no capabilities section.
* External research evidence: Not applicable.
* Why it matters: Step 03 schema/model work will inherit this contract. If the plan is executed as written, the new meta-standard will under-specify a required graph field and create immediate drift between the source spec and the authored standard.
* Recommended action for Claude Code: Revise the plan to include a `[capabilities]` section in the README example, the real manifest, and the template, or explicitly revise SPEC-BA01 with owner-approved deviation before implementation.
* Suggested validation: After implementation, manually map every SPEC-BA01 FR-002 field to the README example, `standard.toml`, and template; run TOML parse checks on both TOML files.

#### CR-002: Minimal `standard.toml` contradicts resolved OQ-002 worked-example decision

* Severity: High
* Status: Confirmed
* Adversarial angle: Tested whether the plan’s “worked example” actually matches the accepted source-of-truth decision.
* Plan reference: Lines 116-153, 281.
* Finding: SPEC-BA01 OQ-002 is resolved as “a complete annotated example” with identity, config namespace, at least one authority, and `adoption = "none"`. The plan instead instructs a minimal manifest with no namespace, no authorities, and no providers, then treats a `DEV-001` row as optional mitigation.
* Repository evidence: SPEC-BA01 lines 148-149 resolve OQ-002 to a complete annotated example. FR-010 and FR-014 require the standard’s own `standard.toml` to conform and serve the manual checklist. The plan’s Task 2 manifest explicitly has `namespaces = []` and no `[[authority]]`.
* External research evidence: Not applicable.
* Why it matters: A pending deviation row is not the same as an accepted spec change. Executing this plan would knowingly diverge from a Must-level acceptance path before owner approval.
* Recommended action for Claude Code: Either make the real `standard.toml` match OQ-002, or revise SPEC-BA01 first and obtain owner acceptance of the deviation before authoring the bundle.
* Suggested validation: Confirm the final Deviations Log is either unchanged or contains an owner-accepted deviation; map FR-010/FR-014 to the actual `standard.toml`.

### Non-blocking issues

#### CR-003: Full-gate Prettier command can pass while TOML validation fails

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Attacked validation for false positives and stale tool assumptions.
* Plan reference: Lines 157, 275, 279.
* Finding: The plan acknowledges Prettier does not format `.toml`, but the full-gate command still includes `"standards/**/*.toml"` and uses `;` before markdownlint. That means a Prettier failure can be hidden by the final markdownlint exit status.
* Repository evidence: `package.json` pins Prettier `3.8.3`. Local read-only probe `./node_modules/.bin/prettier --check pyproject.toml` exited 2 with “No parser could be inferred.”
* External research evidence: Official Prettier CLI docs state `--write` rewrites files and `--check` exits 1 for formatting issues / 2 for Prettier errors; official Prettier options docs list parser values and do not include TOML.
* Why it matters: The final validation could report “markdownlint 0” while TOML formatting/checking failed or was unsupported, undermining the claimed full gate.
* Recommended action for Claude Code: Remove TOML from Prettier checks and validate TOML with `tomllib`; separate validation commands with `&&` or list them one per line without status-masking.
* Suggested validation: Run `tomllib` parse checks for both TOML files and run Prettier only on supported Markdown/JSON/YAML targets.

#### CR-004: Plan misses repository-facing documentation that will become stale

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Checked blast radius beyond the named standards index.
* Plan reference: Lines 30-32, 236-246.
* Finding: The plan updates `standards/README.md` and maybe `AGENTS.md`, but root `README.md`, `CLAUDE.md`, and `meta/versioning.md` also describe the repository’s standards surface and counts. Adding a new governed standard under `standards/` without updating these surfaces leaves conflicting documentation.
* Repository evidence: Root `README.md` lines 32-44 lists the standards directory layout without `standard-bundle-authoring/`; lines 55-111 list all standards. `CLAUDE.md` line 5 says the repo defines six standards plus Python Coding. `meta/versioning.md` lines 54-56 says six standards ship under one version and Python Coding is the seventh document.
* External research evidence: Not applicable.
* Why it matters: The repo’s human-facing and harness-facing maps will disagree with the standards index immediately after implementation.
* Recommended action for Claude Code: Expand the plan’s doc-update scope to include root `README.md`, `CLAUDE.md`, and `meta/versioning.md` if the owner wants the meta-standard represented there now; otherwise explicitly justify why the internal/reference standard is only listed in `standards/README.md`.
* Suggested validation: `rg -n "six standards|seven|Python Coding|standard-bundle-authoring|standards/" README.md CLAUDE.md AGENTS.md meta/versioning.md standards/README.md`.

### Missing considerations

* Blocking: Resolve the manifest capability model before authoring, especially whether `consumes_platform` belongs under `[capabilities]`, `[relations]`, or both.
* Blocking: Decide whether OQ-002 is being followed or formally superseded with owner acceptance.
* Non-blocking: Add a validation step that proves `src/project_standards/schemas/registry.json`, `src/project_standards/bundles/`, and `spec.include` remain unchanged.
* Non-blocking: Decide whether the new internal/reference standard should appear in root README and release-contract docs.
* Non-blocking: Replace masked shell validation with commands whose exit statuses cannot be hidden.

### Internet research performed

* Source name: Prettier CLI documentation
* URL: https://raw.githubusercontent.com/prettier/prettier/main/website/versioned_docs/version-stable/cli.md
* Access date: 2026-07-08
* What it was used to verify: `--write`, `--check`, exit codes, file-pattern behavior.
* Relevant conclusion: `--write` mutates files; `--check` has meaningful non-zero exits that the plan’s semicolon command can mask.

* Source name: Prettier Options documentation
* URL: https://raw.githubusercontent.com/prettier/prettier/main/website/versioned_docs/version-stable/options.md
* Access date: 2026-07-08
* What it was used to verify: Built-in parser list / TOML support.
* Relevant conclusion: The documented parser list includes JSON/JSONC/Markdown/YAML and others, but not TOML.

* Source name: markdownlint-cli2 README
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2/main/README.md
* Access date: 2026-07-08
* What it was used to verify: CLI usage, `--fix`, glob behavior, exit codes.
* Relevant conclusion: The plan’s markdownlint usage is broadly consistent; no blocking issue found there.

### Items Claude Code should verify before correcting the plan

* Whether the owner accepts replacing SPEC-BA01 OQ-002’s complete worked example with a minimal real manifest plus README example.
* The final manifest contract for `[capabilities]`, including `provides` and `consumes_platform`.
* Whether `standard-bundle-authoring` belongs in root `README.md`, `CLAUDE.md`, and `meta/versioning.md` during this Step 02 change.
* Whether `adoption = "none"` alone is the explicit non-adoptability marker required by FR-013.
* The exact validation command set after removing unsupported TOML Prettier checks.

### Suggested corrections for Claude Code's plan

* Add `[capabilities]` to Task 1’s annotated example, Task 2’s real manifest, and Task 3’s template.
* Align Task 2 with SPEC-BA01 OQ-002, or revise SPEC-BA01 first and require owner approval before implementation.
* Remove `standards/**/*.toml` from Prettier checks; validate TOML with `tomllib`.
* Replace `;` in the full-gate command with separate commands or `&&` so failures cannot be masked.
* Add root README / CLAUDE / meta versioning update decisions to the file-scope section.
* Add an explicit “no machine-layer drift” verification step for registry, bundled adopt artifacts, and `spec.include`.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, clean working tree, and recent SPEC-BA01 plan commits.
* `sed -n` on the plan file: inspected the full implementation plan.
* `rg --files`: inventoried repository paths and confirmed `standards/standard-bundle-authoring/` does not yet exist.
* `sed -n` / `rg -n` on SPEC-BA01, SPEC-MT01, ADRs, `standards/README.md`, root `README.md`, `AGENTS.md`, `CLAUDE.md`, `meta/versioning.md`, `.project-standards.yml`, `package.json`, `pyproject.toml`, and `registry.json`: checked plan claims against repository evidence.
* `nl -ba ...`: captured line-referenced evidence for plan/spec/doc mismatches.
* `./node_modules/.bin/prettier --check pyproject.toml`: confirmed local Prettier cannot infer a TOML parser and exits non-zero.

### Recommended implementation validation

Run only after correcting and implementing the plan:

* `uv run validate-frontmatter --config .project-standards.yml`
* `uv run validate-id --config .project-standards.yml`
* `uv run project-standards spec validate --config .project-standards.yml`
* `uv run project-standards spec lint --config .project-standards.yml`
* `uv run python -c "import tomllib,pathlib; [tomllib.loads(p.read_text()) for p in map(pathlib.Path, ['standards/standard-bundle-authoring/standard.toml', 'standards/standard-bundle-authoring/templates/standard.toml'])]; print('toml ok')"`
* Run only after implementation: `./node_modules/.bin/prettier --write standards/standard-bundle-authoring/README.md standards/README.md README.md AGENTS.md CLAUDE.md meta/versioning.md`
* `./node_modules/.bin/markdownlint-cli2`
* `git diff --stat`
* `git diff -- src/project_standards/schemas/registry.json src/project_standards/bundles .project-standards.yml`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md`
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: manifest shape consistency (`capabilities` and OQ-002), validation command correctness, and documentation-scope updates.