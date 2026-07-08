### Executive summary

Claude Code’s revisions substantively resolved the six prior findings: the spec now models `[resources]` as extensible, accepts provider schema fields, defines identity/reserved-namespace checks, fixes the `tomllib` flow, strengthens loader-boundary tests, and defines deterministic schema serialization.

One new non-blocking specification gap remains: executable provider `entrypoint` validation is still underspecified for `command` and `workflow` providers. New internet research was performed for current `tomllib` and Pydantic behavior; no stale external assumption conflict remains.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-standard-manifest-schema-model-design.md
* Prior audit issue count: 6
* Resolved issue count: 6
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested prior issues against the revised spec, the approved Standard Bundle Authoring contract, SPEC-MT01, the real `standards/standard-bundle-authoring/standard.toml`, the blank template, current package/test layout, existing loader/error patterns, schema-validation conventions, and packaging/dogfood tests.

Acceptance criteria were attacked for false positives around resource extensibility, provider optional fields, operation vocabulary, id/directory matching, reserved config namespaces, raw parser/I/O errors, deterministic schema drift, and schema validity checks. External API assumptions for `tomllib.loads()` and `model_json_schema()` were rechecked against official documentation.

I did not run tests, package builds, dependency commands, formatters, or validators because this is a read-only audit and those checks may write caches, build artifacts, coverage data, or lock/package state.

### Prior findings status

#### SA-001: Resource model contradicts extensible resource IDs

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec exempts `[resources]` from closed fixed-shape models, defines it as an open URI-safe-ID-to-path mapping, requires `readme`, conditionally handles `adopt`, accepts `agent_summary` and `template`, and requires arbitrary bundle-specific resource IDs to remain valid. Testing now includes `agent_summary`, `template`, a bundle-specific resource ID, malformed IDs, and unsafe paths on arbitrary keys.
* Remaining action for Claude Code: None for this issue.

#### SA-002: Provider schema omits contract fields and leaves operations undefined

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec accepts optional `input_schema` and `output_schema`, makes provider `operation` an open lowercase kebab token rather than an undefined ellipsis/closed enum, names `semantic-review` as an example, and defers registry membership checks to Step 04.
* Remaining action for Claude Code: None for this issue; see SA-NEW-001 for a narrower remaining entrypoint grammar gap.

#### SA-003: Required single-manifest identity and reserved-config rules are missing

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec requires kebab-case `[standard].id`, loader-level id/parent-directory equality, rejection of `standards_version` in `[config].namespaces`, duplicate namespace rejection within one manifest, and acceptance criteria/fixtures for these cases.
* Remaining action for Claude Code: None for this issue.

#### SA-004: Loader/error acceptance criteria under-test the untrusted TOML boundary

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec requires `StandardManifestError` as the single loader error type, wrapping Pydantic `ValidationError`, `tomllib.TOMLDecodeError`, and `OSError`; tests now include malformed TOML, missing file, non-table root via defensive branch coverage, id/directory mismatch, field-named errors, and symlink escape.
* Remaining action for Claude Code: None for this issue.

#### SA-005: `tomllib.loads(bytes)` is technically wrong

* Previous severity: Medium
* Current status: Resolved
* Evidence: The data flow now says `path.read_text(encoding="utf-8") -> tomllib.loads(str) -> dict`, and explicitly notes that `tomllib.load(fp)` on a binary handle is the equivalent alternative. This matches the existing `adopt/manifest.py` pattern.
* Remaining action for Claude Code: None for this issue.

#### SA-006: Schema drift byte-equality is underspecified

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec defines a canonical writer, `$schema`/`$id` injection, `json.dumps(schema, indent=2, ensure_ascii=False)`, preserved key order, no `sort_keys`, trailing newline, byte-equality drift testing through the same helper, and a separate schema parse/validity check.
* Remaining action for Claude Code: None for this issue.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-001: Executable provider entrypoint grammar remains underspecified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Tested whether the spec gives Claude Code enough detail to encode and test provider `entrypoint` validation without inventing rules.
* Spec reference: Validation rules, provider fields; Testing invalid fixture list for filesystem-path `entrypoint`.
* Finding: The spec says executable provider `entrypoint` must look like an import path or command reference and must not look like a filesystem path, but it does not define a concrete grammar for valid command or workflow references. A later implementation could pass acceptance by only rejecting obvious paths while accepting unsafe shell strings, or could reject valid command-style providers by choosing an overly narrow pattern.
* Repository evidence: The approved README also says provider entrypoints are import paths or command references and never filesystem paths, but the one real manifest has no providers. The template only shows a placeholder comment. Existing repo tests emphasize one-field negative fixtures and path-safety invariants, so this boundary should be made testable before implementation.
* External research evidence: Not applicable.
* Why it matters: Provider declarations are part of the future generic operation surface. Ambiguous entrypoint grammar weakens validation quality and can produce a schema that is either too permissive for safety or too restrictive for future command/workflow providers.
* Recommended action for Claude Code: Add a minimal entrypoint grammar to the spec: for example, Python providers use `module.path:object`, command providers use a documented command token/reference format without path separators or shell metacharacters, and workflow providers use a named workflow/provider reference format or are explicitly deferred to Step 04.
* Suggested validation: Add valid fixtures for one Python import entrypoint and one command or workflow entrypoint, plus invalid fixtures for filesystem paths, `..`, absolute paths, shell metacharacters/pipelines, and network-looking command strings if those are out of scope.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: What exact grammar is valid for executable provider `entrypoint` values by provider `kind`.
* Why it matters: The Pydantic model and generated JSON Schema need concrete constraints, and tests need positive and negative examples.
* Recommended clarification: Define provider-kind-specific patterns or explicitly defer command/workflow reference validation to Step 04 while Step 03 only rejects paths and shell-like strings.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: Python 3.14 `tomllib` documentation
* URL: https://docs.python.org/3/library/tomllib.html
* Access date: 2026-07-08
* What it was used to verify: Correct parser API and return shape for the revised loader flow.
* Relevant conclusion: `tomllib.loads()` accepts a `str` and returns a `dict`; `tomllib.load()` reads from a binary file object; invalid TOML raises `TOMLDecodeError`.

* Source name: Pydantic BaseModel API documentation
* URL: https://docs.pydantic.dev/latest/api/base_model/
* Access date: 2026-07-08
* What it was used to verify: `model_json_schema()` return type and schema generation behavior.
* Relevant conclusion: `model_json_schema()` returns `dict[str, Any]`, so the revised canonical JSON writer remains necessary and appropriate.

### Read-only validation performed

* `sed -n` on the revised spec: inventoried current scope, validation rules, loader flow, canonical schema generation, acceptance criteria, and fixture plan.
* `nl -ba` on the revised spec: captured line-level evidence for resolved prior findings and the new provider-entrypoint ambiguity.
* `git branch --show-current`, `git status --short`, `git log --oneline -n 5`, and `git diff --stat`: confirmed branch `testing`, the latest revision commit, and no displayed working-tree status/stat changes.
* `rg --files` over `standards`, `docs/superpowers`, `src/project_standards`, `tests`, and `.github`: confirmed relevant repo layout and no existing `standard_manifest.py` / `standard.schema.json`.
* `nl -ba` on `standards/standard-bundle-authoring/README.md`, `standard.toml`, and `templates/standard.toml`: rechecked the approved contract, real manifest, provider/resource/config/id rules, and template surface.
* `rg` / `nl -ba` on SPEC-MT01 and SPEC-BA01: rechecked Step 03 boundaries, provider/resource requirements, config namespace rules, and package/readiness expectations.
* `nl -ba` on `src/project_standards/adopt/manifest.py`, `pyproject.toml`, and test documentation: compared loader/error patterns, Python 3.14 baseline, dependencies, coverage policy, schema validity tests, and packaging conventions.
* Opened official Python and Pydantic documentation: verified external API assumptions for `tomllib` and `model_json_schema()`.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run pytest tests/test_standard_manifest.py -v`
* Run only after implementation: schema validity check using `jsonschema.Draft202012Validator.check_schema` for `standard.schema.json`.
* Run only after implementation: package/wheel contents check that `project_standards/schemas/standard.schema.json` ships.
* Run only after implementation: `uv run pytest tests/coherence` after `npm ci` is available.
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml` if managed Markdown is edited.
* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml` and `uv run project-standards spec lint --config .project-standards.yml` if specs are edited.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-standard-manifest-schema-model-design.md
* Audit round: 2
* Open issue IDs: SA-NEW-001
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: executable provider entrypoint grammar and fixtures for valid/invalid Python, command, and workflow provider references.