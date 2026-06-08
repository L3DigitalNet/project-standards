### Executive summary

The specification is not ready for Claude Code to use as the basis for planning. The main blockers are repository-fit and packaging defects: the proposed multi-standard adoption flow can hard-fail on overlapping scaffolds that are currently not byte-identical, and the proposed `uv_build`/`importlib.resources` packaging approach conflicts with current official `uv_build` wheel-inclusion behavior.

Internet research was required for the `uv_build`/package-resource assumption. Current official docs indicate the spec’s root-level `standards/**` package-data strategy needs correction before planning.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Significant findings remaining: Yes
* Blocking issue count: 3
* Non-blocking issue count: 2

### What the specification gets right

* Keeps the existing `validate-frontmatter` entry point as a backward-compatible alias.
* Rejects in-place TOML merging, which fits the repo’s “avoid corrupting hand-tuned files” concern.
* Includes dry-run, skip-by-default, force-overwrite, idempotency, packaging, and dogfood-test concepts.
* Correctly recognizes that templates/manifests must be verified inside the built wheel, not only in the source checkout.

### Adversarial review performed

I inventoried the CLI surface, artifact kinds, manifest flow, template extraction scope, test expectations, versioning claim, and safety claims. I falsified those against the current repo layout, standards docs, workflows, root scaffolds, validator code, registry, release/versioning docs, and official `uv_build`/`importlib.resources` docs.

Strongest assumptions tested: “adopt multiple standards at once,” “overlapping artifacts are byte-identical,” “root-level `standards/**` templates can be force-included as package resources,” “deterministic exit codes are fully specified,” and “the tooling inventory accurately describes current ADR enforcement.”

Could not check an implementation because none exists. I did not run build/test commands because they may write `dist/`, coverage data, caches, or virtualenv/tool state.

### Blocking issues

#### SA-001: Multi-standard adoption can conflict on current overlapping scaffolds

* Severity: High
* Status: Confirmed
* Adversarial angle: Test whether the promised `project-standards adopt <standard>...` flow can handle the natural case of adopting both Python Tooling and Markdown Tooling.
* Spec reference: Lines 22, 45, 50, 100, 115-116.
* Finding: The spec allows one or more standards and treats same-destination differing sources as a hard manifest bug, but the currently documented/source scaffolds for overlapping files are not byte-identical. `.editorconfig` and `.vscode/extensions.json` are especially likely to conflict if extracted as written.
* Repository evidence: The spec lists `.editorconfig` for both `markdown-tooling` and `python-tooling` and explicitly cites `.editorconfig` as a dedupe example. Python Tooling’s inline `.editorconfig` uses spaces for `*.{toml,yml,yaml,json,md}` in [standards/python-tooling/README.md](/home/chris/projects/project-standards/standards/python-tooling/README.md:848). The repo/root Markdown Tooling floor uses tab defaults in [.editorconfig](/home/chris/projects/project-standards/.editorconfig:11), while Markdown Tooling adoption tells consumers to copy the repo `.editorconfig` in [standards/markdown-tooling/adopt.md](/home/chris/projects/project-standards/standards/markdown-tooling/adopt.md:33). Python Tooling’s VS Code extensions are Python-focused in [standards/python-tooling/README.md](/home/chris/projects/project-standards/standards/python-tooling/README.md:690); Markdown Tooling recommends Prettier + markdownlint in [standards/markdown-tooling/README.md](/home/chris/projects/project-standards/standards/markdown-tooling/README.md:244).
* External research evidence: Not applicable.
* Why it matters: A likely command such as `project-standards adopt markdown-tooling python-tooling` can fail even though both standards are released and selectable. That makes the manifest conflict rule surface current repo drift as a user-facing failure instead of a maintained standard.
* Recommended action for Claude Code: Decide a canonical strategy for overlapping artifacts before planning: shared superset templates, fragments/report-only for merge-prone files, or explicit incompatibility/order rules. Then require tests for combined adoption.
* Suggested validation: Add tests that adopt `markdown-tooling python-tooling` together and assert the intended behavior for `.editorconfig`, `.vscode/extensions.json`, `.vscode/settings.json`, and `.vscode/tasks.json`.

#### SA-002: Root-level template packaging strategy conflicts with current `uv_build` resource behavior

* Severity: High
* Status: Confirmed
* Adversarial angle: Verify the external packaging assumption that root `standards/**/templates/**` can be force-included as importable package resources.
* Spec reference: Lines 118-122.
* Finding: The spec mandates keeping templates under root `standards/<id>/templates/` while making them reachable at runtime through `importlib.resources`. Current `uv_build` docs say wheel contents include the module root and optional data directories copied into `.data`; there are no specific wheel includes, and data files must be under the module root or an appropriate data directory. That does not support the spec’s implied “force-include root tree as package resources” shape.
* Repository evidence: Current package code lives under `src/project_standards/`; schema/registry are bundled there in [pyproject.toml](/home/chris/projects/project-standards/pyproject.toml:24) and [src/project_standards/registry.py](/home/chris/projects/project-standards/src/project_standards/registry.py:23). Current `standards/**/templates/**` are outside `src/`, as shown by repository file listing.
* External research evidence: Official uv build backend docs, accessed 2026-06-08: https://docs.astral.sh/uv/concepts/build-backend/ . Official Python `importlib.resources` docs, accessed 2026-06-08: https://docs.python.org/3/library/importlib.resources.html .
* Why it matters: The core CLI may work from a source checkout but fail after `uv tool install`, which is the actual distribution path. A packaging test that merely sees files in the wheel `.data` directory would still not prove they are reachable via `importlib.resources`.
* Recommended action for Claude Code: Revise the spec to choose a supported runtime resource layout: copy/generate templates under `src/project_standards/...`, or use `uv_build.data` plus an explicit non-`importlib.resources` lookup strategy. The spec should name the chosen layout and verification.
* Suggested validation: Build the wheel after implementation, inspect wheel contents, install from the wheel, and run `project-standards list` plus `project-standards adopt ... --dry-run` from the installed tool.

#### SA-003: File-write safety boundaries are underspecified

* Severity: High
* Status: Confirmed
* Adversarial angle: Attack the safety claim that the command is agent/CI-safe and never destroys hand-tuned files.
* Spec reference: Lines 18, 51, 73-86, 101-105.
* Finding: The spec does not require artifact `dest` paths to be relative, normalized, and contained under `--dest`; does not specify rejection of `..` or absolute paths; does not define source path containment inside the bundle; and does not define symlink behavior for existing destinations. `--force` plus an unsafe manifest path could overwrite outside the intended repo.
* Repository evidence: No implementation exists yet. The manifest format accepts arbitrary `source`, `dest`, and `target` strings in the spec example, and the engine flow says to create parent directories and write actions.
* External research evidence: Not applicable.
* Why it matters: The spec treats manifest conflicts as bugs worth surfacing, so manifest safety bugs are in scope. Without path-boundary rules, a later implementation could be deterministic and tested while still unsafe.
* Recommended action for Claude Code: Add a safety contract: reject absolute paths and parent traversal; resolve every write target under `--dest`; keep sources inside the package bundle; define symlink handling; map permission/path errors to deterministic exit codes.
* Suggested validation: Add unit tests for absolute `dest`, `../` traversal, symlink destinations, missing source templates, non-directory `--dest`, and permission-denied writes.

### Non-blocking issues

#### SA-004: Tooling inventory understates current ADR enforcement

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Falsify the problem statement’s “distributed tooling today” table.
* Spec reference: Lines 7-14.
* Finding: The spec says ADR is “frontmatter-validated only,” but current repo docs and validator code include an opt-in ADR body-section check and ADR/Frontmatter compatibility gate.
* Repository evidence: Versioning docs mark ADR as enforced by “body-rule + FM-compatibility check” in [meta/versioning.md](/home/chris/projects/project-standards/meta/versioning.md:57). ADR adoption documents the optional section check and compatibility rule in [standards/adr/adopt.md](/home/chris/projects/project-standards/standards/adr/adopt.md:38). Validator code enforces ADR compatibility and optional section checks in [src/project_standards/validate_frontmatter.py](/home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:336) and [src/project_standards/validate_frontmatter.py](/home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:547).
* External research evidence: Not applicable.
* Why it matters: The problem statement can lead planning to treat ADR as more “doc-only” than it is, potentially duplicating or bypassing existing validator behavior.
* Recommended action for Claude Code: Revise the table to say ADR has frontmatter validation, optional MADR body-section validation, and FM compatibility, but lacks generator/index/relationship tooling.
* Suggested validation: Ensure `adopt adr` scaffolds the existing ADR config knobs instead of inventing a separate ADR enforcement path.

#### SA-005: Template extraction scope does not cover all current inline scaffolds clearly

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Check whether the drift loop is actually closed or just moved.
* Spec reference: Lines 26, 107-116.
* Finding: The spec says every scaffold inline in a README becomes a template, but important current scaffolds live in `adopt.md` files, and the spec does not clearly say whether those inline blocks are removed, retained as examples, or generated from templates.
* Repository evidence: The frontmatter adoption config and workflow caller are inline in [standards/markdown-frontmatter/adopt.md](/home/chris/projects/project-standards/standards/markdown-frontmatter/adopt.md:58) and [standards/markdown-frontmatter/adopt.md](/home/chris/projects/project-standards/standards/markdown-frontmatter/adopt.md:102). Python Tooling adoption still says scaffolds live inline in the standard in [standards/python-tooling/adopt.md](/home/chris/projects/project-standards/standards/python-tooling/adopt.md:28).
* External research evidence: Not applicable.
* Why it matters: If adoption guides keep independent inline copies, the CLI templates and docs can drift immediately after implementation.
* Recommended action for Claude Code: Define the extraction rule as “all scaffold blocks in standard READMEs and adopt guides,” then specify which remaining snippets are illustrative and how they stay synchronized.
* Suggested validation: Add a test or documentation check that every manifest source referenced by `adopt.toml` has exactly one canonical template file and that docs link to it.

### Missing specification considerations

* Blocking: Canonical merge strategy for overlapping files across standards, especially `.editorconfig` and `.vscode/*`.
* Blocking: Supported installed-wheel resource layout and runtime loader.
* Blocking: Path traversal, absolute path, symlink, and source containment rules.
* Blocking: Deterministic exit-code mapping for invalid manifests, missing templates, nonexistent/non-directory `--dest`, permission errors, and package-version lookup failures.
* Non-blocking: Concrete `project-standards list` output contract and tests.
* Non-blocking: Whether `adopt adr` creates an optional `docs/adr/` seed/index by default, behind a flag, or never.
* Non-blocking: Changelog/versioning acceptance for relocating copy-adopt scaffolds out of README sections.

### Ambiguities and decisions needed

* Ambiguity: Should adopting `markdown-tooling` and `python-tooling` together succeed?
* Why it matters: The current artifact overlap likely conflicts.
* Recommended clarification: State the intended combined-standard behavior and canonical shared template ownership.
* Blocking or non-blocking: Blocking.

* Ambiguity: Where do bundled templates physically live in the wheel?
* Why it matters: Source-checkout paths and installed-package paths differ.
* Recommended clarification: Choose `src/project_standards/...` resources or `.data` plus explicit lookup.
* Blocking or non-blocking: Blocking.

* Ambiguity: What is exit code `3` for?
* Why it matters: The spec promises deterministic exit codes but does not assign realistic missing-prerequisite cases.
* Recommended clarification: Define exact cases for `0`, `1`, `2`, and `3`.
* Blocking or non-blocking: Blocking.

### Internet research performed

* Source name: uv Build backend docs
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Wheel inclusion behavior for `uv_build`.
* Relevant conclusion: Wheel includes the module root and optional data directories; there are no specific wheel includes, and data files must be under the module root or appropriate data directory.

* Source name: Python `importlib.resources` docs
* URL: https://docs.python.org/3/library/importlib.resources.html
* Access date: 2026-06-08
* What it was used to verify: Whether arbitrary wheel data is naturally a package resource.
* Relevant conclusion: `importlib.resources` is for resources associated with modules/packages, so the spec must ensure templates are packaged under an importable anchor or use a different lookup mechanism.

### Items Claude Code should verify before correcting the specification

* Confirm whether combined adoption of all released standards is a required supported workflow.
* Compare current source scaffolds for every overlapping destination and decide canonical ownership.
* Re-check current `uv_build` docs before finalizing the packaging text.
* Decide exact behavior for `fragment` artifacts when `pyproject.toml` is absent.
* Decide whether ADR seed/index creation is default, optional, or out of scope.
* Decide whether `list` needs stable machine-readable output now or only plain text.

### Suggested corrections for Claude Code’s specification

* Add an overlapping-artifact strategy and require combined-standard tests.
* Replace the unsupported root-template `importlib.resources` packaging assumption with a supported wheel resource layout.
* Add path safety rules for manifest sources and destination writes.
* Define exit-code mapping for missing prerequisites and I/O failures.
* Correct the ADR tooling inventory.
* Expand template extraction scope to include adoption-guide scaffolds.
* Add acceptance criteria for `project-standards list`, invalid manifests, installed-wheel execution, and safety failures.

### Read-only validation performed

* `pwd` established the repository root as `/home/chris/projects/project-standards`.
* `git status --short && git branch --show-current && git log --oneline -n 10` established a clean working tree on `testing` with the spec commit at HEAD.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and the Quick Reference in `docs/handoff/conventions.md` for repo state and local rules.
* `nl -ba docs/superpowers/specs/2026-06-08-adopt-cli-design.md` inventoried the specification with line references.
* `rg --files` and `find` mapped repo structure, standards bundles, workflows, and existing templates.
* Inspected `pyproject.toml`, `.project-standards.yml`, `src/project_standards/validate_frontmatter.py`, `registry.py`, and `registry.json`.
* Inspected root workflows, root config scaffolds, standard READMEs/adopt guides, `meta/versioning.md`, `CHANGELOG.md`, and deployed state.
* `git tag --list 'v*' --sort=version:refname` confirmed local release tags through `v2.0.0` and moving `v2`.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build the wheel, inspect wheel contents, install from the wheel, then run installed `project-standards list` and `project-standards adopt ... --dry-run`.
* Run only after implementation: integration tests for adopting each standard alone and all released standards together into `tmp_path`.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: combined-standard artifact conflicts, installed-wheel resource strategy, path safety/exit-code contract, and whether the ADR/tooling inventory plus extraction scope were corrected.

