### Executive summary

The specification should not be used as the basis for planning yet. It is directionally aligned with the repo’s v5/MCP-readiness work, but it leaves core authoring-contract decisions unresolved or under-specified: config namespace ownership does not fit the repo’s current nested namespace shape, the required `standard.toml` worked example cannot be objectively judged while central choices remain open, and safety/artifact-linkage rules are too thin for a manifest contract that future tooling will trust.

Internet research was not required for this audit because the material claims are repository-internal: current standard inventory, existing `adopt.toml` behavior, config namespaces, ADR decisions, and project-spec validation surfaces.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 3

### What the specification gets right

* Correctly identifies the seven current standard directories and the `project-spec` / `python-coding` outliers.
* Correctly scopes schema/model/graph validation to later SPEC-MT01 steps.
* Correctly keeps `adopt.toml` as the artifact plane rather than replacing it in this step.
* Correctly anchors the meta-standard to the accepted ADR set for manifests, authorities, resources, providers, namespaces, and relationships.

### Adversarial review performed

I inventoried the spec’s requirements, non-goals, acceptance criteria, open questions, and referenced ADRs; checked them against the live standards index, `.project-standards.yml`, SPEC-MT01 baseline inventory, existing adopt manifests, schema registry, project-spec validator/linter code, and git state. I attacked the strongest claims around “one worked example,” “no adoption machinery,” “config namespace ownership,” “authority/resource/provider declarations,” and acceptance checks that could pass without proving the intended contract.

I did not run `uv` validation commands because this audit is read-only and those commands may create or touch local environment/cache artifacts depending on the machine state.

### Blocking issues

#### SA-001: Config namespace ownership does not fit the existing nested namespace model

* Severity: High
* Status: Confirmed
* Adversarial angle: The spec says each standard owns a top-level config namespace, but the current repo already has shared/nested ownership under `markdown`.
* Spec reference: FR-006; §2.1 config-namespace rules; §17.1 README contract DoD.
* Finding: The spec requires “each standard to declare its owning top-level config namespace” and says duplicate or undeclared namespaces are invalid. That is not sufficient for ADR, which currently owns `markdown.adr` under the `markdown` top-level namespace used by Markdown Frontmatter. It also does not account for non-standard/meta keys like `standards_version`.
* Repository evidence: `.project-standards.yml` uses `markdown.frontmatter` and `markdown.adr` under one top-level `markdown` key, plus `standards_version`, `python_tooling`, `markdown_tooling`, `cli_documentation`, and `spec`. The baseline inventory explicitly lists `markdown.adr` as a sub-namespace and says namespace ownership is currently implicit.
* External research evidence: Not applicable.
* Why it matters: A later implementer could incorrectly force ADR to claim the whole `markdown` top-level key, reject the existing config as duplicate ownership, or fail to model parent/child namespace delegation. That would make graph validation misrepresent the current repo.
* Recommended action for Claude Code: Revise the spec to define namespace ownership at both top-level and nested paths, including parent namespace delegation, reserved/meta keys, and whether a standard can own a nested namespace under another standard’s parent.
* Suggested validation: After correction, verify the proposed namespace model can represent `markdown.frontmatter`, `markdown.adr`, `spec`, and `standards_version` without duplicate-owner ambiguity.

#### SA-002: Required `standard.toml` example is not objectively decidable while core choices remain open

* Severity: High
* Status: Confirmed
* Adversarial angle: The acceptance criteria require a conforming worked example, but the spec leaves key manifest-shape decisions open and defers the schema/model.
* Spec reference: FR-002, FR-003, FR-010, OQ-001, OQ-002, §17.1.
* Finding: The spec requires `standards/standard-bundle-authoring/standard.toml` to “conform to the contract,” but no schema exists yet and OQ-002 leaves open whether the example is full or minimal. OQ-001 also leaves the `project-spec` adoption-mode name open while FR-003 requires the vocabulary to classify every current standard.
* Repository evidence: `find standards src/project_standards/bundles -name standard.toml` found no existing `standard.toml`; the baseline inventory states there is no `standard.toml` schema or authority-map schema yet. The project-spec linter only checks generic spec hygiene, not semantic manifest conformance.
* External research evidence: Not applicable.
* Why it matters: Claude Code could produce a plausible example that satisfies prose locally but becomes incompatible with Step 03’s schema/model, or could leave an “accepted” worked example whose central enum/name choices are still undecided.
* Recommended action for Claude Code: Resolve OQ-001 and OQ-002 before planning, or explicitly define a manual conformance checklist for Step 02 that Step 03 must preserve or deliberately supersede.
* Suggested validation: Add a checklist in the spec mapping each required `standard.toml` field to the worked example and requiring owner acceptance before Step 03 schema work begins.

### Non-blocking issues

#### SA-003: Manifest path and provider safety rules are missing from the authoring contract

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Future tooling will trust manifest-declared resources and providers, but this spec does not define safety constraints for paths or executable hooks.
* Spec reference: FR-007, FR-008, §2.1, omitted §§13–16.
* Finding: The spec says resource IDs map to bundle file paths and provider declarations include operation/kind/entrypoint/optional, but it does not require safe relative paths, no `..`, no absolute paths, no symlink escapes, first-party-only provider targets, network defaults, or explicit opt-out behavior.
* Repository evidence: The existing adopt engine validates source paths and destination paths against traversal/symlink hazards. SPEC-MT01 also names path traversal, provider execution, and prompt/tool poisoning as threats.
* External research evidence: Not applicable.
* Why it matters: A manifest contract without safety rules can be implemented inconsistently in Step 03/04, especially around resource exposure and provider execution.
* Recommended action for Claude Code: Add manifest safety requirements for resource paths, template paths, provider entrypoints, and optional/missing provider behavior.
* Suggested validation: Later schema/graph tests should include invalid absolute paths, `..` traversal, missing resource files, unsupported provider operations, and unsafe provider declarations.

#### SA-004: `adopt.toml` linkage and artifact ownership are under-specified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The spec says `adopt.toml` remains the artifact plane but does not define how `standard.toml` references or delegates artifact ownership to it.
* Spec reference: §2.1, NG-002, FR-001, FR-002, §2.4.
* Finding: The spec lists `adopt.toml` linkage in scope but the manifest contract acceptance criteria omit artifact manifest references, artifact ownership, shared artifacts, and collision semantics. This leaves a gap between the meta-standard and the existing adopt engine.
* Repository evidence: Existing `adopt.toml` files define `file`, `workflow-caller`, and `fragment` artifacts; shared artifacts exist under `_shared`; the adopt engine deduplicates identical shared sources and rejects conflicting destinations.
* External research evidence: Not applicable.
* Why it matters: Step 04 graph validation needs to reason about artifact ownership and collisions. If Step 02 does not define the linkage, Step 03/04 must invent it.
* Recommended action for Claude Code: Add a requirement that `standard.toml` either references `adopt.toml` or explicitly declares non-adoptability, and define how artifact ownership/collisions remain delegated to the artifact plane.
* Suggested validation: Later tests should prove the graph can represent standards with no `adopt.toml`, with owned artifacts, and with shared artifacts used by multiple standards.

#### SA-005: No-`adopt.md` scope conflicts with the current standards index contract

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The spec says this internal standard ships no `adopt.md`, but the repo’s current standards index still says `adopt.md` is required for every standard except the current draft-only case.
* Spec reference: NG-001, FR-001, §17.1.
* Finding: The spec requires the new standard to be listed in `standards/README.md` but does not explicitly require updating the bundle anatomy text to allow an internal/reference standard with no `adopt.md`.
* Repository evidence: `standards/README.md` says every standard has `README.md` required and `adopt.md` required; it only names `python-coding` as the current README-only in-development draft exception.
* External research evidence: Not applicable.
* Why it matters: Acceptance could pass with a new row in the index while leaving the repo’s own bundle anatomy documentation internally inconsistent.
* Recommended action for Claude Code: Require the standards index anatomy to be updated to include explicit non-adoptable/internal-reference markers and the no-`adopt.md` rule for this meta-standard.
* Suggested validation: Review `standards/README.md` after implementation to ensure the anatomy section and table both describe the new bundle honestly.

### Missing specification considerations

* Blocking: Namespace model for nested config paths, delegated ownership, and reserved/meta keys.
* Blocking: Manual conformance criteria for `standard.toml` while schema/model validation is deferred.
* Non-blocking: Safe relative-path rules for manifest resources, templates, examples, and provider entrypoints.
* Non-blocking: Explicit `adopt.toml` linkage, no-adoptability markers, shared artifact semantics, and artifact collision expectations.
* Non-blocking: Lifecycle mapping between spec status values, standard README frontmatter status, and `standard.toml` lifecycle states.
* Non-blocking: Acceptance criteria that prove `standards/README.md` anatomy is updated, not merely that the new standard is listed.
* Non-blocking: Negative examples for invalid bundle anatomy, invalid adoption mode, duplicate namespace, unsafe resource path, missing provider, and hidden dependency language.

### Ambiguities and decisions needed

* Ambiguity: Is namespace ownership top-level only, nested-path capable, or both?
* Why it matters: Current ADR config is nested under `markdown.adr`.
* Recommended clarification: Define namespace IDs as dotted paths and specify parent/child ownership rules.
* Blocking or non-blocking: Blocking.

* Ambiguity: Is the meta-standard’s `standard.toml` example full, minimal, or annotated-but-non-normative?
* Why it matters: FR-010 depends on it, and Step 03 schema work will likely copy its shape.
* Recommended clarification: Resolve OQ-002 or define an explicit manual conformance checklist.
* Blocking or non-blocking: Blocking.

* Ambiguity: Is the adoption mode `cli` final or provisional?
* Why it matters: FR-003 requires the vocabulary to classify all current standards, including `project-spec`.
* Recommended clarification: Decide the v1 enum name now, or mark it explicitly provisional and non-schema-binding.
* Blocking or non-blocking: Non-blocking if the provisional status is explicit.

### Internet research performed

No internet research was necessary. The audited assumptions are governed by local repository evidence and accepted local ADRs rather than current external API/library behavior.

### Items Claude Code should verify before correcting the specification

* Reconfirm the current seven standards and their adoption surfaces from `standards/README.md`, `src/project_standards/bundles/`, and `src/project_standards/schemas/registry.json`.
* Reconfirm `.project-standards.yml` namespace ownership, especially `markdown.frontmatter` vs `markdown.adr`.
* Decide whether `standard.toml` should use dotted namespace IDs, nested tables, or another representation for config ownership.
* Decide whether the worked example is normative for Step 03 schema design.
* Verify whether provider/resource/path safety rules should live in this Light spec or require upgrading to Standard profile sections.

### Suggested corrections for Claude Code’s specification

* Define config namespace ownership as dotted paths with explicit parent/delegation rules.
* Resolve OQ-001 and OQ-002, or make their provisional nature explicit and non-blocking for Step 03.
* Add a manual `standard.toml` conformance checklist for Step 02.
* Add safety rules for manifest paths, resource IDs, provider declarations, and missing optional providers.
* Add explicit `adopt.toml` linkage/non-adoptability requirements.
* Require `standards/README.md` anatomy updates for internal/reference standards with no `adopt.md`.
* Add acceptance criteria that attack false positives: example exists but omits a required field, index row exists but anatomy still says `adopt.md` required, namespace list cannot represent `markdown.adr`.

### Read-only validation performed

* `pwd`, `git branch --show-current`, `git status --short`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, and recent v5/SPEC-BA01 history.
* Read the full spec under audit with `sed` and line-numbered `nl`.
* Searched repo evidence with `rg` for standard-bundle, manifest, registry, namespace, provider, and project-spec references.
* Listed repository files with `rg --files` and targeted `find`.
* Inspected `standards/README.md`, `.project-standards.yml`, current standard READMEs, SPEC-MT01, SPEC-RD01, the Step 00 baseline inventory, and referenced ADRs.
* Inspected `src/project_standards/adopt/manifest.py` and `engine.py` for current artifact and path-safety behavior.
* Inspected `src/project_standards/specs/commands/validate.py`, `lint.py`, and `config.py` for what spec validation/linting actually proves.
* Ran `git diff --stat` and `git diff --check`; no output, establishing no visible working-tree diff/check findings at that moment.

### Recommended planning/implementation validation

* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml`.
* Run only after implementation: `uv run project-standards spec lint --config .project-standards.yml`.
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`.
* Run only after implementation: `npm run format:check`.
* Run only after implementation: markdownlint/Prettier coherence gate used by this repo, including `uv run pytest tests/coherence` after `npm ci` if dependencies are not already installed.
* Run only after implementation: targeted review that every Must requirement maps to a concrete check or owner-accepted manual review item.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: namespace ownership semantics, resolved `standard.toml` example decisions, manifest safety rules, `adopt.toml` linkage, and standards index consistency.

