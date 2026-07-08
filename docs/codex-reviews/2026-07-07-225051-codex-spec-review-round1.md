### Executive summary

The specification needs major correction before Claude Code uses it for planning or implementation. Its overall Step 03 boundary is sound, but several material schema/model requirements contradict or under-cover the approved Standard Bundle Authoring contract: resource IDs are too closed for an intentionally extensible `[resources]` table, provider declarations omit optional schema fields and an explicit operation vocabulary, and identity/config single-manifest rules are missing from validation and fixtures.

Internet research was required for current `tomllib` and Pydantic API assumptions. The main stale-assumption finding is that `tomllib.loads(bytes)` is not a valid Python 3.14 flow; `loads` takes `str`, while file parsing uses `tomllib.load()` on a binary file object.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-standard-manifest-schema-model-design.md
* Significant findings remaining: Yes
* Blocking issue count: 3
* Non-blocking issue count: 3

### What the specification gets right

* Correctly scopes Step 03 to a single `standard.toml` and leaves graph validation, CLI wiring, retrofit, generated indexes, and MCP readiness to later steps.
* Correctly identifies `standards/standard-bundle-authoring/standard.toml` as the one existing real manifest that must validate.
* Correctly separates syntactic path checks from loader-level symlink containment.
* Correctly aligns the new module/test shape with the repo’s `src/project_standards/` and `tests/test_*.py` conventions.
* Correctly treats Pydantic as plausible for this external-input boundary under the repo’s Python standards.

### Adversarial review performed

I inventoried the spec’s claimed model fields, validation rules, dependency changes, acceptance criteria, fixture plan, and non-goals. I then falsified those claims against `standards/standard-bundle-authoring/README.md`, the real `standard.toml`, `templates/standard.toml`, SPEC-MT01, SPEC-BA01, accepted ADRs, `pyproject.toml`, existing schema/registry patterns, test guidance, CI workflows, and git state.

The strongest assumptions tested were: “extra forbid on every model can preserve the resource contract,” “the provider model mirrors SPEC-BA01,” “all single-manifest rules are listed,” “the fixture corpus can prove conformance,” “the loader flow is technically correct,” and “the schema drift check is testable as written.”

I did not run tests or package/dependency commands because this is read-only and those commands may write caches, environments, lockfiles, coverage data, or package artifacts.

### Blocking issues

#### SA-001: Resource model contradicts extensible resource IDs

* Severity: High
* Status: Confirmed
* Adversarial angle: Challenged whether `extra = "forbid"` on every model preserves the SPEC-BA01 resource contract.
* Spec reference: `Validation rules encoded in the model`, especially `extra = "forbid"` and resource path rules.
* Finding: The spec requires unknown keys to fail on every model, but `[resources]` is explicitly a mapping from URI-safe resource IDs to paths and may include `agent_summary`, `template`, and bundle-specific IDs under `resources/`. If implemented literally as a closed Pydantic submodel, valid future manifests with additional resource IDs would fail.
* Repository evidence: The spec says every model forbids extra keys and unknown keys fail. `standards/standard-bundle-authoring/README.md` defines `[resources]` as ID-to-path mappings and explicitly allows `agent_summary`, `template`, and any bundle-specific IDs. SPEC-MT01 FR-007 requires resource descriptors for docs, adoption docs, templates, examples, schemas, agent summaries, and rationale/source docs. The real manifest already uses `template = "templates/standard.toml"`.
* External research evidence: Not applicable.
* Why it matters: Step 04 and future MCP/resource consumers depend on extensible manifest-declared resources. A closed resources model would bake a false contract into the generated schema and block valid standards unless every resource ID is pre-hardcoded.
* Recommended action for Claude Code: Revise the spec to model `[resources]` as a constrained mapping: required/reserved IDs such as `readme` and conditional `adopt`, known optional IDs such as `agent_summary` and `template`, plus arbitrary URI-safe resource IDs whose values are safe bundle-relative paths.
* Suggested validation: Add valid fixtures with `agent_summary`, `template`, and one bundle-specific resource ID under `resources/`; add invalid fixtures for malformed resource IDs and unsafe paths on arbitrary resource keys.

#### SA-002: Provider schema omits contract fields and leaves operations undefined

* Severity: High
* Status: Confirmed
* Adversarial angle: Tested whether the provider model really mirrors SPEC-BA01/SPEC-MT01 instead of narrowing it.
* Spec reference: Provider enum/rule bullets and fixture corpus.
* Finding: The spec says unknown keys fail and provider fields are operation/kind/optional plus entrypoint for executable kinds. The approved contract allows `input_schema` and `output_schema`, and SPEC-MT01 names `semantic-review` as a provider operation example. The spec also uses an ellipsis for “known generic operations,” which is not implementable as a stable enum.
* Repository evidence: `standards/standard-bundle-authoring/README.md` says providers may declare `input_schema` / `output_schema`. SPEC-MT01 Provider Declaration lists `input_schema` and `output_schema` as Should fields and includes `semantic-review` in operation examples. The audited spec lists only `validate`, `fix`, `drift-check`, `id-next`, `extract`, and an ellipsis.
* External research evidence: Not applicable.
* Why it matters: A generated schema that rejects `input_schema` / `output_schema` would reject contract-compliant provider declarations. An undefined operation enum forces the implementer to invent the vocabulary, making later graph/MCP behavior unstable.
* Recommended action for Claude Code: Define the complete provider field schema, including optional `input_schema` and `output_schema`, and replace the ellipsis with an explicit operation vocabulary or a clearly versioned extension mechanism.
* Suggested validation: Add valid provider fixtures with `input_schema`, `output_schema`, and each accepted operation; add invalid fixtures for out-of-vocabulary operations and unknown provider keys outside the approved field set.

#### SA-003: Required single-manifest identity and reserved-config rules are missing

* Severity: High
* Status: Confirmed
* Adversarial angle: Attacked the claim that the model encodes every single-manifest rule from SPEC-BA01 FR-002 through FR-014.
* Spec reference: Required fields, dotted namespaces, acceptance criteria, fixture corpus.
* Finding: The spec does not require tests or implementation behavior for `[standard].id` being kebab-case and matching the bundle directory, and it omits the single-manifest reserved meta-key rule for config namespaces. Both are in the approved conformance checklist.
* Repository evidence: `standards/standard-bundle-authoring/README.md` requires `id` to be kebab-case and match the directory. The same checklist requires `[config].namespaces` to claim no reserved meta key, and the namespace table marks `standards_version` as repo-owned/reserved. The audited spec only lists id as a required field and only rejects duplicate namespaces within the one manifest.
* External research evidence: Not applicable.
* Why it matters: A manifest with `id = "wrong-standard"` in `standards/standard-bundle-authoring/standard.toml`, or `namespaces = ["standards_version"]`, could pass Step 03 despite violating the source contract. Step 04 would then build graph validation on corrupted identity/config data.
* Recommended action for Claude Code: Add explicit loader-level validation that `standard.id` is kebab-case and equals the parent bundle directory name, and model-level validation that reserved meta namespaces cannot be claimed.
* Suggested validation: Add invalid fixtures or loader tests for bad id syntax, id/directory mismatch, and `standards_version` in `[config].namespaces`.

### Non-blocking issues

#### SA-004: Loader/error acceptance criteria under-test the untrusted TOML boundary

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Tested whether acceptance criteria can pass while parser and I/O failure paths remain unproven.
* Spec reference: Data flow, acceptance criteria, testing.
* Finding: The spec calls `standard.toml` untrusted external input, but the fixture list focuses on semantically invalid TOML documents. It does not require validation for malformed TOML, a missing file, unreadable file, root value/type surprises, or loader error message consistency.
* Repository evidence: Existing repo test guidance requires parsing/config error branches and path-safety invariants. Existing loader-style code such as `adopt/manifest.py` translates TOML decode and OSError failures into structured domain errors.
* External research evidence: Not applicable.
* Why it matters: The public loader contract could be green on model fixtures while still leaking raw `TOMLDecodeError`/`OSError`, returning inconsistent errors, or failing Step 04 CLI exit-code mapping.
* Recommended action for Claude Code: Add acceptance criteria and tests for malformed TOML, missing file, unreadable file where practical, non-table/root-shape handling, and consistent `StandardManifestError` wrapping.
* Suggested validation: Unit tests should assert `StandardManifestError` for TOML syntax errors and missing manifests without exposing raw tracebacks.

#### SA-005: `tomllib.loads(bytes)` is technically wrong

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Checked whether the specified loader data flow matches Python 3.14 `tomllib`.
* Spec reference: Data flow and errors.
* Finding: The data-flow diagram says `Path -> tomllib.loads(bytes) -> dict`. Python’s docs say `tomllib.loads()` loads from a `str`; file parsing uses `tomllib.load()` with a readable binary file object.
* Repository evidence: `pyproject.toml` requires Python `>=3.14`, so current Python 3.14 `tomllib` behavior is the relevant baseline. Existing `src/project_standards/adopt/manifest.py` uses `tomllib.loads(path.read_text(...))`, not bytes.
* External research evidence: Python 3.14 `tomllib` docs, https://docs.python.org/3/library/tomllib.html, accessed 2026-07-08. The docs define `tomllib.load(fp)` for a readable binary file object and `tomllib.loads(s)` for a `str`.
* Why it matters: This is easy to fix in implementation, but leaving it in the spec can cause a needless parser bug or inconsistent loader pattern.
* Recommended action for Claude Code: Change the spec to either `path.read_text(encoding="utf-8") -> tomllib.loads(str)` or `path.open("rb") -> tomllib.load(file)`.
* Suggested validation: Add a loader test that exercises the actual file-reading path, not only `model_validate()` on prebuilt dictionaries.

#### SA-006: Schema drift byte-equality is underspecified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Attacked whether the drift test can be implemented deterministically from the acceptance text alone.
* Spec reference: Generated schema decision, acceptance criteria, schema drift test.
* Finding: The spec says the committed JSON file “equals `StandardManifest.model_json_schema()`” and the drift test asserts byte-equality, but `model_json_schema()` returns a Python `dict`. The spec does not define JSON serialization parameters, key ordering, trailing newline, or whether `$schema` / `$id` metadata are injected outside Pydantic output.
* Repository evidence: The existing `markdown-frontmatter.schema.json` is a hand-authored JSON file with stable formatting, `$schema`, and `$id`. The audited spec adds a generated schema but does not define the canonical writer.
* External research evidence: Pydantic BaseModel docs, https://docs.pydantic.dev/latest/api/base_model/, accessed 2026-07-08. `model_json_schema()` returns `dict[str, Any]`, not bytes or a JSON string.
* Why it matters: The drift test can fail or pass for formatting reasons unrelated to schema semantics, and two implementers could choose incompatible canonicalization.
* Recommended action for Claude Code: Specify the canonical generation function and serialization format, including `json.dumps` options, newline policy, and whether `$schema`/`$id` are model config metadata or post-processing.
* Suggested validation: Add a test that regenerates the exact file text through the same helper used to write the schema, and a separate test that the JSON parses as a schema object.

### Missing specification considerations

* Blocking: Extensible resource IDs and optional provider schema fields must be included before implementation planning; otherwise the generated schema will contradict the approved contract.
* Blocking: Identity validation must include both model-level syntax and loader-level directory matching.
* Blocking: Reserved config meta keys such as `standards_version` must be rejected in a single manifest.
* Non-blocking: The spec should state whether `relations.extends` ADR-backed validation is entirely Step 04 or whether Step 03 only checks array shape.
* Non-blocking: The spec should define how `documentation-only` providers behave when `entrypoint` is absent or present.
* Non-blocking: The spec should say whether `latest` must be a member of `supported` when both are non-empty, or explicitly defer that to graph/version validation.
* Non-blocking: The fixture corpus should include fully populated happy paths, not only a representative copy-adopt fixture and the minimal real manifest.
* Non-blocking: The spec should state that provider “first-party” and “no network by default” are not mechanically provable by this schema unless a manifest field or later validation rule is added.
* Non-blocking: Acceptance criteria should prevent false positives where `model_validate()` passes but `load_standard_manifest()` fails to wrap parse/I/O/path-resolution errors correctly.

### Ambiguities and decisions needed

* Ambiguity: What exact provider operation vocabulary is accepted?
* Why it matters: A Pydantic enum and JSON Schema need a closed list or a deliberate extension model.
* Recommended clarification: List all accepted operations now, including whether `semantic-review` is in Step 03, or define operations as constrained strings with Step 04 registry validation.
* Blocking or non-blocking: Blocking

* Ambiguity: What counts as an “adoptable mode” for `adopt` presence, especially `reference-only` when released versus draft?
* Why it matters: The contract says released adoptable standards have `adopt.md`, while unreleased drafts and `adoption = "none"` do not.
* Recommended clarification: Define the conditional in terms of `adoption` and `status`, or explicitly defer draft/release nuance.
* Blocking or non-blocking: Non-blocking

* Ambiguity: How should arbitrary `[resources]` keys be represented in the typed object?
* Why it matters: Step 04/MCP consumers need stable iteration over declared resource IDs.
* Recommended clarification: Define a `dict[ResourceId, ResourcePath]` shape plus typed helpers for reserved keys.
* Blocking or non-blocking: Blocking

* Ambiguity: What canonical JSON serialization produces `standard.schema.json`?
* Why it matters: The drift test requires byte equality.
* Recommended clarification: Define the generator helper and serialization settings.
* Blocking or non-blocking: Non-blocking

### Internet research performed

* Source name: Python 3.14 `tomllib` documentation
* URL: https://docs.python.org/3/library/tomllib.html
* Access date: 2026-07-08
* What it was used to verify: Whether `tomllib.loads()` accepts bytes and the correct file-loading API.
* Relevant conclusion: `tomllib.loads()` loads TOML from a `str`; `tomllib.load()` reads from a binary file object.

* Source name: Pydantic BaseModel API documentation
* URL: https://docs.pydantic.dev/latest/api/base_model/
* Access date: 2026-07-08
* What it was used to verify: The return type and behavior surface of `model_json_schema()`.
* Relevant conclusion: `model_json_schema()` generates and returns a JSON schema as a `dict[str, Any]`, so byte-stable file output needs a specified serialization step.

### Items Claude Code should verify before correcting the specification

* Confirm the intended provider operation vocabulary against SPEC-MT01, SPEC-BA01, and accepted ADRs before freezing the enum.
* Confirm whether released `reference-only` standards require `adopt.md`, and how unreleased drafts should be represented in Step 03.
* Confirm the reserved config meta-key list beyond `standards_version`, if any.
* Confirm whether `latest in supported` is a single-manifest rule or deferred to graph/version validation.
* Confirm package-data behavior for `src/project_standards/schemas/standard.schema.json` after adding the generated schema.
* Confirm whether `uv add pydantic` chooses a Python 3.14-compatible Pydantic v2 line and updates `uv.lock` as expected during implementation.

### Suggested corrections for Claude Code’s specification

* Replace the closed `[resources]` model language with a constrained mapping model that allows arbitrary URI-safe resource IDs.
* Add `agent_summary`, `template`, and bundle-specific resources to valid fixture requirements.
* Add optional provider `input_schema` and `output_schema`, and define the complete operation vocabulary or extension mechanism.
* Add identity validation: kebab-case `standard.id` and loader-level id/parent-directory match.
* Add reserved meta namespace rejection, at least for `standards_version`.
* Correct the `tomllib` data flow.
* Specify canonical schema JSON generation and byte-drift serialization.
* Add parser/I/O/loader failure tests for malformed TOML, missing files, and error wrapping.
* Clarify whether status/version relationship checks are Step 03 or Step 04.
* Clarify which FR-012 provider safety claims are schema-enforced versus policy-only/deferred.

### Read-only validation performed

* `sed -n` on the audited spec: inventoried scope, model fields, validation rules, dependency claim, acceptance criteria, and fixture plan.
* `git branch --show-current`, `git status --short`, `git log --oneline -n 10`, and `git diff --stat`: confirmed branch `testing`, recent Step 03 design commit, and no working-tree diff/status output.
* `rg --files` over source, schemas, tests, workflows, and standards: identified current module/schema/test layout and confirmed no existing `standard_manifest.py` or `standard.schema.json`.
* `sed -n` on `standards/standard-bundle-authoring/README.md`, `standard.toml`, and `templates/standard.toml`: checked the approved manifest contract, real manifest shape, and template fields.
* `sed -n` / `nl -ba` on SPEC-MT01 and SPEC-BA01: verified resource/provider/config/identity requirements and Step 03/04 boundaries.
* `sed -n` on `src/project_standards/adopt/manifest.py` and `registry.py`: compared existing loader/error patterns and typed-view conventions.
* `sed -n` / `rg` on `pyproject.toml`, `tests/README.md`, and `.github/workflows/*`: verified Python 3.14 baseline, dependencies, test policy, and gate commands.
* Opened official Python and Pydantic documentation: verified external API assumptions for `tomllib` and `model_json_schema()`.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run pytest tests/test_standard_manifest.py -v`
* Run only after implementation: `uv run pytest tests/coherence` after `npm ci` is available.
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml` if managed Markdown is edited.
* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml` and `uv run project-standards spec lint --config .project-standards.yml` if specs are edited.
* Run only after implementation: package/wheel contents check that `project_standards/schemas/standard.schema.json` ships in the installed package.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-standard-manifest-schema-model-design.md
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: resource-map extensibility, provider field/operation vocabulary, identity/config reserved-key validation, loader error coverage, corrected TOML parsing flow, and deterministic schema generation.

