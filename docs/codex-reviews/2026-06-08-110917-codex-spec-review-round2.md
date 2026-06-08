### Executive summary

Claude Code’s revisions resolved the packaging, path-safety, ADR-inventory, and extraction-scope findings, but one prior blocker remains partially resolved: the shared `.editorconfig` strategy avoids byte-level conflicts while still failing to reconcile the current Python Tooling indentation contract with the proposed shared root/template policy. New internet research was required for YAML syntax and package-resource assumptions; it exposed a new blocker where “byte-unchanged” extraction can turn the current Python Tooling inline workflow scaffold into invalid YAML.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Prior audit issue count: 5
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the revised spec, prior audit ledger, current repo state, validator/registry code, package metadata, standard READMEs/adopt guides, root scaffolds, workflows, tests, and versioning docs. Retested the prior blockers against the new shared-bundle, packaging, path-safety, exit-code, ADR-inventory, and extraction-scope text. Attacked acceptance criteria for false positives around combined adoption, installed-wheel behavior, generated workflow validity, YAML fragments, and “byte-identical” dogfooding.

Could not check an implementation because none exists. I did not run build, test, install, or validation commands that can write caches/artifacts.

### Prior findings status

#### SA-001: Multi-standard adoption can conflict on current overlapping scaffolds

* Previous severity: High
* Current status: Partially resolved
* Evidence: The spec now requires any combination including all four, introduces `_shared` artifacts, and adds a combined `markdown-tooling python-tooling` test. That resolves the hard same-destination failure mode. But the chosen “root `.editorconfig` already is this superset” claim is still not reconciled with the Python Tooling standard: Python’s current inline `.editorconfig` specifies spaces for `*.{toml,yml,yaml,json,md}` in [standards/python-tooling/README.md](/home/chris/projects/project-standards/standards/python-tooling/README.md:848), while the root `.editorconfig` uses global tabs and only overrides Python/TOML/YAML in [.editorconfig](/home/chris/projects/project-standards/.editorconfig:16). The spec also claims “relocated-but-byte-unchanged template content” at line 192, which cannot be true for this shared file if Python’s current scaffold is replaced by the root superset.
* Remaining action for Claude Code: Decide whether the shared `.editorconfig` is a deliberate Python Tooling standard change, a Markdown Tooling override, or a new synthesized template. Update the affected standard prose and versioning impact explicitly, then require tests for Python-only, Markdown-only, and combined adoption.

#### SA-002: Root-level template packaging strategy conflicts with current `uv_build` resource behavior

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now moves canonical templates/manifests under `src/project_standards/bundles/<id>/` and uses the existing `Path(__file__).parent` pattern. Local precedent exists in [src/project_standards/registry.py](/home/chris/projects/project-standards/src/project_standards/registry.py:25) and [src/project_standards/validate_frontmatter.py](/home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:72). Official `uv_build` docs confirm wheel inclusion includes the module under the module root and that small data commonly lives under the module root.
* Remaining action for Claude Code: Keep the wheel-inspection/install-run validation in the later plan.

#### SA-003: File-write safety boundaries are underspecified

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now rejects absolute/`..` destinations, enforces containment under `--dest`, enforces source containment in the package bundle tree, skips symlink destinations even under `--force`, maps I/O failures to exit 1, and adds safety unit tests.
* Remaining action for Claude Code: None beyond implementing those tests.

#### SA-004: Tooling inventory understates current ADR enforcement

* Previous severity: Medium
* Current status: Resolved
* Evidence: The inventory now says ADR has frontmatter validation, opt-in MADR body-section checks, and FM-to-ADR compatibility. This matches [meta/versioning.md](/home/chris/projects/project-standards/meta/versioning.md:57) and the validator’s compatibility gate in [src/project_standards/validate_frontmatter.py](/home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:336).
* Remaining action for Claude Code: None.

#### SA-005: Template extraction scope does not cover all current inline scaffolds clearly

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now covers scaffolds inline in a standard README or its `adopt.md`, names the frontmatter adoption-guide scaffolds, and adds a single-canonical-copy rule.
* Remaining action for Claude Code: Ensure the implementation actually removes or marks remaining inline snippets as illustrative.

### New blocking issues

#### SA-NEW-001: Byte-unchanged extraction can produce invalid workflow YAML

* Severity: High
* Status: Confirmed
* Adversarial angle: Test whether “extract inline scaffolds byte-unchanged” can produce valid target files.
* Spec reference: Lines 139, 146, 169, 192.
* Finding: The Python Tooling inline `check.yml` scaffold currently contains tab indentation inside a YAML code fence. The spec says inline scaffolds become canonical files and later calls the relocation byte-unchanged, but YAML forbids tabs in indentation. The real root `.github/workflows/check.yml` uses spaces.
* Repository evidence: `cat -vet` on [standards/python-tooling/README.md](/home/chris/projects/project-standards/standards/python-tooling/README.md:883) showed `^I` indentation throughout the workflow scaffold. The root workflow at [.github/workflows/check.yml](/home/chris/projects/project-standards/.github/workflows/check.yml:1) uses space indentation.
* External research evidence: YAML 1.2.2, accessed 2026-06-08, states indentation is spaces and tabs must not be used in indentation: https://yaml.org/spec/1.2.2/
* Why it matters: `adopt python-tooling` could generate an invalid GitHub Actions workflow while passing superficial “file exists” or byte-copy tests.
* Recommended action for Claude Code: Change the spec from “byte-unchanged” extraction to “semantic extraction into syntactically valid target files.” Require YAML templates to be space-indented and parsed/validated after generation.
* Suggested validation: Add tests that generated `.yml`/`.yaml` artifacts contain no tab indentation and parse as YAML; compare `check.caller.yml` against a valid canonical workflow, not the Markdown fence bytes.

### New non-blocking issues

#### SA-NEW-002: ADR config-fragment behavior is promised but not specified or tested

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Attack whether `adopt adr` can satisfy its own promised adoption behavior without inventing YAML merge semantics.
* Spec reference: Lines 101, 115, 143-144, 161, 167, 175.
* Finding: The spec says `adopt adr` scaffolds the existing `.project-standards.yml` `markdown.adr` knobs, but the artifact/report/testing text only concretely defines fragments around `pyproject.toml`. It does not say whether the ADR knobs are a YAML fragment, a full file when adopting ADR alone, or a report-only section when adopting with `markdown-frontmatter`.
* Repository evidence: ADR adoption requires adding the `markdown.adr` block in [standards/adr/adopt.md](/home/chris/projects/project-standards/standards/adr/adopt.md:38), and the validator consumes that block in [src/project_standards/validate_frontmatter.py](/home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:336).
* External research evidence: Not applicable.
* Why it matters: Acceptance could pass while `adopt adr` drops an ADR template but omits the config needed to enable ADR body-section enforcement.
* Recommended action for Claude Code: Define fragment behavior generically for `.project-standards.yml`, or add an ADR-specific report artifact. Cover `adopt adr`, `adopt markdown-frontmatter adr`, and all-four adoption.
* Suggested validation: Assert the report includes the `markdown.adr` block when ADR is selected and that no YAML file is edited in place.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Is the shared `.editorconfig` a deliberate change to Python Tooling’s current JSON/Markdown indentation policy?
* Why it matters: Without that decision, shared adoption may succeed while violating one standard.
* Recommended clarification: State the canonical policy and update Python/Markdown Tooling docs plus versioning impact.
* Blocking or non-blocking: Blocking.

* Ambiguity: Is `python-tooling`’s `check.caller.yml` a standalone workflow template or a `workflow-caller` artifact with `{{ref}}` substitution?
* Why it matters: Python Tooling has no reusable workflow, so “caller” terminology can mislead planning.
* Recommended clarification: Name it `check.yml` or explicitly mark it `kind = "file"`.
* Blocking or non-blocking: Non-blocking.

* Ambiguity: What is the stable JSON schema for `project-standards list --json`?
* Why it matters: “Machine-readable” is underspecified.
* Recommended clarification: Define keys for standard id, version, artifact kind, destination, shared owner, and fragment target.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: uv Build backend docs
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Whether package data under `src/project_standards/` is a supported wheel layout.
* Relevant conclusion: Wheel contents include the module under the module root; small data under the module root is the supported boring path.

* Source name: Python `importlib.metadata` docs
* URL: https://docs.python.org/3/library/importlib.metadata.html
* Access date: 2026-06-08
* What it was used to verify: `importlib.metadata.version()` behavior and failure class for unresolved package metadata.
* Relevant conclusion: The API exposes installed distribution versions and raises `PackageNotFoundError` when the distribution is unavailable.

* Source name: YAML 1.2.2 specification
* URL: https://yaml.org/spec/1.2.2/
* Access date: 2026-06-08
* What it was used to verify: Whether tab-indented YAML workflow templates are valid.
* Relevant conclusion: YAML indentation is spaces; tabs must not be used in indentation.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, and `git log --oneline -n 10`: confirmed repo root, branch `testing`, modified spec, and recent history.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed repo rules and v3 layout.
* `nl -ba docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: inventoried the revised spec with line references.
* `git diff -- docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: compared the revision to the prior committed spec.
* Inspected `pyproject.toml`, `src/project_standards/registry.py`, `validate_frontmatter.py`, schema registry, `.project-standards.yml`, workflows, root configs, standard README/adopt files, `meta/versioning.md`, `README.md`, and `CHANGELOG.md`.
* `find`/`rg` inspections mapped current standards, templates, workflows, tests, registry references, and adoption snippets.
* `sed ... | cat -vet` checked inline workflow indentation and verified the Python Tooling workflow fence contains tabs while root workflows use spaces.
* `git tag --list 'v*' --sort=version:refname`: confirmed local release tags through `v2.0.0` and moving `v2`.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build the wheel, inspect wheel contents, install from the wheel, then run installed `project-standards list` and `project-standards adopt ... --dry-run`.
* Run only after implementation: parse every generated YAML workflow/config artifact and assert no tab indentation.
* Run only after implementation: adoption matrix for each standard alone, `markdown-frontmatter adr`, `markdown-tooling python-tooling`, and all four together.
* Run only after implementation: verify generated workflow refs use the derived `@v<major>` and, for frontmatter validation, matching `standards-ref`.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Audit round: 2
* Open issue IDs: SA-001, SA-NEW-001, SA-NEW-002
* Resolved issue IDs: SA-002, SA-003, SA-004, SA-005
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: shared `.editorconfig` semantics/versioning, syntax-valid template extraction for workflow YAML, ADR `.project-standards.yml` fragment behavior, and generated-template validation coverage.

