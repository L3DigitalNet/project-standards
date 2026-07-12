### Executive summary

Claude Code’s corrections resolved four of the five prior findings. One safety finding remains partially resolved: the spec now requires safe manifest paths, but it defines resource/template/provider paths as “repository-relative,” which is broader than the bundle-contained resource model required by the existing ADR/SPEC evidence and could allow future tooling to expose files outside the declaring standard’s bundle.

No new internet research was required; the remaining issue is governed by local ADRs, SPEC-MT01, and current adopt-engine behavior.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md
* Prior audit issue count: 5
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 0
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the prior namespace, worked-example, manifest safety, `adopt.toml` linkage, and standards-index findings against the revised spec. Rechecked the current standards inventory, `.project-standards.yml`, SPEC-MT01 baseline inventory, accepted ADRs, adopt-engine path handling, and validation/tooling surfaces. Acceptance criteria were attacked for false positives, especially whether documenting “safe paths” would still allow overbroad manifest resource exposure.

I did not run `uv`, pytest, npm, or validation commands because this is read-only audit mode and those commands may write caches or artifacts.

### Prior findings status

#### SA-001: Config namespace ownership does not fit the existing nested namespace model

* Previous severity: High
* Current status: Resolved
* Evidence: The revised FR-006 defines dotted namespace paths, parent delegation, reserved meta keys, and duplicate ownership of the same path as invalid. It explicitly requires representing `markdown.frontmatter`, `markdown.adr`, `spec`, and `standards_version`, matching `.project-standards.yml` and the baseline inventory.
* Remaining action for Claude Code: None for this finding.

#### SA-002: Required `standard.toml` example is not objectively decidable while core choices remain open

* Previous severity: High
* Current status: Resolved
* Evidence: OQ-001 is answered as `cli`; OQ-002 is answered as a complete annotated example. FR-014 now requires a manual conformance checklist mapping required fields to the worked example until Step 03 introduces a schema.
* Remaining action for Claude Code: None for this finding.

#### SA-003: Manifest path and provider safety rules are missing from the authoring contract

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: FR-012 now adds safety rules for paths and providers, including no `..`, no absolute paths, no symlink escape, first-party/local providers, and no network by default. However, it requires paths to be “repository-relative,” while ADR-0010 says standard resources are bundle resources, SPEC-MT01 EC-001 says a manifest path outside the bundle must fail, and the current adopt engine models owned artifacts as paths relative to the bundle directory with containment checks.
* Remaining action for Claude Code: Revise FR-012 so resources/templates are bundle-relative and must remain inside the declaring standard bundle, with only explicitly modeled shared artifact paths allowed through the artifact plane. Also distinguish filesystem paths from provider import paths or command entrypoints.

#### SA-004: `adopt.toml` linkage and artifact ownership are under-specified

* Previous severity: Medium
* Current status: Resolved
* Evidence: FR-013 now requires each `standard.toml` to reference `adopt.toml` or explicitly declare non-adoptability, and it preserves artifact ownership, `_shared`, and destination-collision semantics in the artifact plane.
* Remaining action for Claude Code: None for this finding.

#### SA-005: No-`adopt.md` scope conflicts with the current standards index contract

* Previous severity: Medium
* Current status: Resolved
* Evidence: Definition of Done now requires updating `standards/README.md` bundle-anatomy text so `adopt.md` is required only for adoptable standards, not merely adding a table row.
* Remaining action for Claude Code: None for this finding.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Are manifest resource/template paths bundle-relative or repository-relative?
* Why it matters: Repository-relative paths can point outside the declaring standard bundle while still satisfying “no `..`, no absolute paths, no symlink escape.”
* Recommended clarification: Require bundle-relative containment for standard resources/templates; allow shared artifacts only through the explicit artifact/shared mechanism.
* Blocking or non-blocking: Non-blocking, but significant because it affects future resource/provider safety.

### Internet research performed

No new internet research was necessary. The remaining material claim is repository-internal and is covered by local ADR/SPEC/adopt-engine evidence rather than current external API or library behavior.

### Read-only validation performed

* `pwd`, `git branch --show-current`, `git status --short`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, modified spec file, and prior v5/SPEC-BA01 history.
* Read the revised spec with line numbers: confirmed FR-006, FR-012, FR-013, FR-014, DoD, and OQ corrections.
* `git diff -- docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md`: confirmed the exact round-2 edits.
* Inspected `standards/README.md`, `.project-standards.yml`, `registry.json`, and the Step 00 baseline inventory: confirmed current standard inventory, config namespaces, and registry gaps.
* Inspected ADRs 0001, 0003, 0004, 0006, 0008, 0010, and 0013: confirmed manifest, authority, namespace, provider, resource, and relationship decisions.
* Inspected SPEC-MT01 sections on manifest edge cases, security threats, and validation strategy: confirmed paths outside a bundle are expected to fail.
* Inspected `src/project_standards/adopt/manifest.py`, `src/project_standards/adopt/engine.py`, and adopt safety tests: confirmed current artifact source paths are bundle-relative/shared-plane-relative with containment checks.
* `git diff --stat` and `git diff --check`: confirmed only the spec file is modified in tracked diff and no diff-check output was reported.

### Recommended planning/implementation validation

* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml`.
* Run only after implementation: `uv run project-standards spec lint --config .project-standards.yml`.
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`.
* Run only after implementation: `npm run format:check`.
* Run only after implementation: `uv run pytest tests/coherence` after `npm ci` if Node dependencies are not installed.
* Run only after implementation: targeted manual check that FR-012 rejects resource/template paths outside the declaring standard bundle and distinguishes provider import/command entrypoints from filesystem resource paths.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md
* Audit round: 2
* Open issue IDs: SA-003
* Resolved issue IDs: SA-001, SA-002, SA-004, SA-005
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: FR-012 path-base semantics, bundle containment for resources/templates, explicit shared-artifact exceptions, and provider entrypoint wording.