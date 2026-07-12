### Executive summary

The implementation plan needs major correction before Claude Code executes it. The overall scope matches the repo direction, but the proposed `[resources]` model and generated-schema validation strategy can accept invalid manifests while still passing the plan’s tests. Internet research was required for current Pydantic v2 behavior; the main stale-assumption finding is that `extra="allow"` extras are not validated unless explicitly typed, and a generated JSON Schema can be structurally valid without proving the Python-only validators are represented.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-manifest-schema-model.md
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 3

### What the plan gets right

* It keeps Step 03 scoped to single-manifest modeling and defers graph-wide checks to Step 04.
* It correctly identifies `standards/standard-bundle-authoring/standard.toml` as the real manifest that must keep validating.
* It adds focused loader tests for parse errors, missing files, id/directory mismatch, and symlink escape.
* It avoids planned changes to `registry.json`, bundled standards, `.project-standards.yml`, and CLI wiring.

### Adversarial review performed

Performed claim inventory, falsification, blast-radius, failure-mode, validation attack, external-assumption, and maintainability passes. Strongest assumptions tested: Pydantic `extra="allow"` behavior for open resources, whether generated JSON Schema validates the same contract as the Pydantic model, basedpyright strict compatibility, resource-path safety/existence, and artifact-producing validation commands. I did not run `uv` commands or tests because dependency resolution, build, and test commands may write caches/artifacts in this read-only audit.

### Blocking issues

#### CR-001: `[resources]` extras are accepted without type validation

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation false positive at the manifest boundary.
* Plan reference: Task 5, lines 439 and 496-516.
* Finding: The plan claims `[resources]` is an open URI-safe-ID to safe path mapping, but the proposed `ResourcesTable` uses `extra="allow"` and then coerces non-string extra values with `str(value)`. A TOML array, boolean, integer, or table under an extra resource key can be converted into a string and pass path checks accidentally.
* Repository evidence: SPEC-BA01 says `[resources]` maps IDs to paths and every path is bundle-relative and contained (`standards/standard-bundle-authoring/README.md` lines 190-205). The design says `[resources]` should be a constrained dict whose values are safe bundle-relative paths (`docs/superpowers/specs/2026-07-07-standard-manifest-schema-model-design.md` lines 67-78). The plan’s implementation instead stringifies untyped extras (`docs/superpowers/plans/2026-07-07-standard-manifest-schema-model.md` lines 512-516).
* External research evidence: Pydantic v2 docs state that `extra="allow"` stores extra data and that, by default, no validation is applied to those extra items unless `__pydantic_extra__` is typed: https://docs.pydantic.dev/latest/api/config/ (accessed 2026-07-08).
* Why it matters: Invalid manifests can pass the model, loader, and schema drift tests, creating an unreliable foundation for Step 04 and future MCP/resource consumers.
* Recommended action for Claude Code: Model resources as a typed open mapping, for example by typing `__pydantic_extra__: dict[ResourceId, SafeBundlePath]` or using a `RootModel`/custom model that validates both keys and values without string coercion.
* Suggested validation: Add invalid tests for non-string extra resource values, nested resource tables, arrays, booleans, and integers. Ensure both model validation and generated schema reject them where schema can express the rule.

#### CR-002: Schema tests can pass while the committed schema omits important contract rules

* Severity: High
* Status: Needs Claude verification
* Adversarial angle: Generated artifact false positive.
* Plan reference: Task 9 lines 884-909 and Task 10 lines 1096-1099.
* Finding: The plan only checks that `standard.schema.json` is byte-equal to `standard_schema_json()` and is a valid JSON Schema. It does not validate the invalid fixture corpus against the generated schema. Several planned rules are Python validators, such as `latest in supported`, duplicate/reserved namespaces, `adoption = "none"` forbidding `adopt`, provider entrypoint conditionals, and resource path safety. These can be enforced by Pydantic while absent or weaker in the generated JSON Schema.
* Repository evidence: The design’s acceptance criteria require the committed schema to be produced and parse as JSON Schema, but the implementation plan does not attack semantic equivalence between schema and model (`docs/superpowers/specs/2026-07-07-standard-manifest-schema-model-design.md` lines 119-135; plan lines 904-909, 1096-1099).
* External research evidence: Pydantic documents `model_json_schema()` as generating JSON Schema from the model/adapted type and provides separate customization mechanisms for JSON Schema output: https://docs.pydantic.dev/latest/concepts/json_schema/ (accessed 2026-07-08).
* Why it matters: Step 03’s deliverable is a trustworthy schema plus model. If future consumers use the JSON Schema directly, they may accept manifests that the model rejects.
* Recommended action for Claude Code: Add schema-vs-fixture tests using `Draft202012Validator` against representative invalid fixtures, document any rules intentionally model-only, and customize schema output for expressible rules.
* Suggested validation: After generation, run JSON Schema validation over all valid/invalid fixtures and explicitly record which invalid cases are model-only because JSON Schema cannot express them.

### Non-blocking issues

#### CR-003: The planned schema validity test likely fails basedpyright strict without an ignore

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Strict-type gate failure hidden until late validation.
* Plan reference: Task 9 lines 888-909; Task 11 lines 1141-1148.
* Finding: The plan adds `Draft202012Validator.check_schema(...)` without the `pyright` ignore already required elsewhere in this repo.
* Repository evidence: Existing `tests/test_validate_frontmatter.py` uses `Draft202012Validator.check_schema(schema)  # pyright: ignore[reportUnknownMemberType]` at line 1026. `pyproject.toml` sets basedpyright strict mode and `failOnWarnings = true` at lines 56-61.
* External research evidence: Not applicable.
* Why it matters: The plan’s local `pytest` pass can be green while the full gate fails at basedpyright.
* Recommended action for Claude Code: Mirror the existing inline ignore and comment for `check_schema`, or wrap the call in a typed helper consistent with repo conventions.
* Suggested validation: Run `uv run basedpyright` after adding Task 9 tests.

#### CR-004: Resource existence is not explicitly validated

* Severity: Medium
* Status: Unclear
* Adversarial angle: Missing-path false positive.
* Plan reference: Task 8 lines 736-859.
* Finding: The loader resolves resource paths and checks containment, but it does not check that declared files exist. A manifest with `readme = "missing.md"` appears able to pass if the path stays inside the bundle.
* Repository evidence: SPEC-MT01 says validation fails when resource paths are missing (`docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` lines 278 and 608). SPEC-BA01 describes resources as lazy-loadable bundle content and `README.md` as required (`standards/standard-bundle-authoring/README.md` lines 45-52, 190-205).
* External research evidence: Not applicable.
* Why it matters: Future resource consumers can get a manifest that validates but points to absent content.
* Recommended action for Claude Code: Decide whether existence checks belong in Step 03 loader or Step 04 graph validation. If Step 03, add an existence test. If Step 04, state that explicitly in the plan.
* Suggested validation: Add a missing resource-path fixture/test at the layer chosen by the corrected plan.

#### CR-005: Wheel validation writes repo-local `dist/` artifacts

* Severity: Low
* Status: Confirmed
* Adversarial angle: Validation command dirties the worktree.
* Plan reference: Task 11 lines 1150-1152.
* Finding: `uv build` without `--out-dir` writes to `dist/`. The repo already has a wheel-content test using a temporary output directory.
* Repository evidence: `tests/test_spec_wheel_contents.py` builds with `uv build --wheel --out-dir <tmp_path>` and inspects the resulting wheel. The plan’s command writes to default `dist/`.
* External research evidence: Not applicable.
* Why it matters: The implementation can finish with untracked build artifacts, confusing closeout and handoff.
* Recommended action for Claude Code: Use a temporary output directory for the manual wheel check or add/extend a pytest packaging test that builds into `tmp_path`.
* Suggested validation: Run the wheel check with `uv build --wheel --out-dir "$tmpdir"` after implementation.

### Missing considerations

* Blocking: Add semantic JSON Schema validation against valid and invalid fixtures, or document schema/model rule gaps.
* Blocking: Ensure open `[resources]` validates both extra keys and values without coercing arbitrary TOML values to strings.
* Non-blocking: Decide and document whether declared resource paths must exist in Step 03 or Step 04.
* Non-blocking: Add the known basedpyright ignore for `Draft202012Validator.check_schema`.
* Non-blocking: Avoid repo-local build artifacts during wheel validation.

### Internet research performed

* Source name: Pydantic ConfigDict / extra behavior
* URL: https://docs.pydantic.dev/latest/api/config/
* Access date: 2026-07-08
* What it was used to verify: Behavior of `extra="allow"` and validation of extra fields.
* Relevant conclusion: Extra items are stored and not validated by default unless extra storage is typed.

* Source name: Pydantic JSON Schema docs
* URL: https://docs.pydantic.dev/latest/concepts/json_schema/
* Access date: 2026-07-08
* What it was used to verify: Current `model_json_schema()` behavior and schema customization guidance.
* Relevant conclusion: Pydantic can generate JSON Schema from models, but semantic equivalence for custom validators must be tested/customized, not assumed from `check_schema`.

### Items Claude Code should verify before correcting the plan

* Whether Step 03 must reject missing resource files, or whether that is explicitly deferred to Step 04.
* The exact generated JSON Schema for `ResourcesTable` with open extras.
* Which invalid fixture cases are rejected by `Draft202012Validator` versus only by Pydantic.
* Whether basedpyright still requires `reportUnknownMemberType` suppression on `Draft202012Validator.check_schema`.

### Suggested corrections for Claude Code's plan

* Replace `ResourcesTable` with a typed open mapping that validates extra values as strings/path tokens and never stringifies non-string TOML values.
* Add invalid tests for non-string resource values and nested resource payloads.
* Add schema semantic tests that validate valid and invalid fixtures with `Draft202012Validator`.
* Mark any model-only constraints explicitly if JSON Schema cannot express them.
* Add or defer a missing-resource-path existence test with an explicit rationale.
* Mirror the existing basedpyright ignore for `Draft202012Validator.check_schema`.
* Change the wheel check to build into a temporary directory.

### Read-only validation performed

* `sed -n` on the plan file: read the full implementation plan.
* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed clean visible status output, branch `testing`, and recent Step 03 plan/design commits.
* `rg --files`: inventoried repository layout and confirmed relevant source/test/schema paths.
* `sed -n` on the design doc, SPEC-BA01 README, real `standard.toml`, template, `pyproject.toml`, and existing wheel/schema tests: compared plan claims against repo evidence.
* `rg -n` searches for schema, Pydantic, resource, and packaging references: checked local conventions and prior related constraints.
* `nl -ba` on key files: captured stable line evidence for findings.
* Web research against official Pydantic docs: verified current external behavior for `extra="allow"` and JSON Schema generation.

### Recommended implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: JSON Schema semantic validation over the valid/invalid manifest fixture corpus.
* Run only after implementation: wheel-content check using a temporary build output directory.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-standard-manifest-schema-model.md
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: typed `[resources]` extras, schema-vs-model fixture validation, resource existence decision, basedpyright schema test typing, and artifact-free wheel validation

