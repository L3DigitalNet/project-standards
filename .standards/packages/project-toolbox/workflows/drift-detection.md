# Drift detection sweep

## Purpose

Verify that the repository's actual state matches what its adopted standards, configuration, and documentation claim about it. Drift is the gap between the claim and the reality, and it is dangerous precisely because every individual gate is green: the checks that would catch it either do not run, do not cover the file, or report success in a shape that is easy to misread.

This sweep targets the drift classes that survive normal gating. It is instructional, not fail-closed — its output is a list of confirmed differences and the fix that belongs to each.

## When to run

- Before a release, and before adopting or upgrading a standards package.
- After hand-editing anything under a package-managed path, or after a CI or editor toolchain change.
- When a gate passes but the repository's behavior does not match its documentation.

## Preconditions

- A clean working tree; drift findings are ambiguous when uncommitted edits are in flight.
- The default branch checked out, so trunk-only defects are visible.
- The repository's own toolchain installed and usable, so the gates you invoke are the pinned ones rather than an ambient copy.

## Checklist

### 1. Learn what this repository has adopted (do this first)

- [ ] Read `.standards/config.toml`: which packages are enabled, at which versions, and with which options.
- [ ] Read `.standards/lock.toml` (if present) and confirm the resolved versions match what the configuration selects.
- [ ] For each enabled package, note the paths it manages and the gates it owns. Those gates are the authority for their surface; run them rather than re-deriving their checks here.
- [ ] If no standards packages are installed, skip to the generic fallback at the end. Nothing in this document requires a package to be present.

### 2. Reconciliation drift (activated by project-standards)

- [ ] Run the machine-readable form and read the fields, not the exit status:

  ```bash
  project-standards reconcile --check --json
  ```

  Clean means `ok: true`, `drift: false`, and an empty findings list. **`project-standards reconcile --check` exits `1` when drift exists** — that non-zero exit is the preview succeeding at its job, not the command failing. Reading it as a tool error is the standard way this check gets misreported as broken.

- [ ] Treat any `CP-MODIFIED-MANAGED` finding as a hand edit to a package-managed file. Fix it through the owning package's configuration options and re-reconcile; never re-edit the rendered file, and never "fix" it by copying your edit back over the managed output. If the change you want has no option, that missing option is the finding.
- [ ] Confirm the applied state converges: reconcile, apply, then reconcile again and expect no findings. A check that reports drift immediately after a successful apply means the package's render is not idempotent.

### 3. Surfaces reconciliation cannot see (activated by configuration)

These are the silent classes. No finding will ever be raised for them, so they must be checked by hand.

- [ ] **`consumer-owned` ownership.** Where a package option hands a file back to the consumer — a workflow, a config, an instruction file — reconciliation stops covering it entirely. Open each such file and compare it against the configuration that is supposed to describe it: globs, exclusions, path scopes, and job names diverge here and nothing reports it.
- [ ] **Editor versus CI tool version skew.** An editor extension that bundles its own formatter or linter will disagree with the repository's pinned one, and the disagreement is invisible to reconcile-style checks — the file looks formatted to whoever last saved it. Confirm the editor settings point at the workspace-local tool (the one in `node_modules/` or the project virtual environment) rather than the bundled copy, and confirm the pinned version matches CI.
- [ ] **Config-versus-hand-authored divergence generally.** Wherever a value is declared in two places — a version in both a manifest and a workflow, a path in both configuration and a script — assert they still agree.

### 4. CI portability drift (activated by CI)

Each item below is a defect class that lets CI stay green while the thing it claims to check goes unchecked.

- [ ] **`pull_request`-only triggers.** A workflow that never runs on `push` to the default branch cannot catch a defect that lands directly on trunk. Confirm the triggers cover the ways changes actually reach the default branch.
- [ ] **Jobs that do not run what they are named for.** A job called `validate` that runs a formatter, or a `test` job whose command silently skips the suite, is worse than no job. Read each job's actual commands and confirm they invoke the validator or suite the name promises.
- [ ] **Shallow clones.** `actions/checkout` defaults to depth 1. Any test that reads history, tags, or a merge base fails or, worse, degrades into a trivially passing no-op. Set the fetch depth wherever history is read.
- [ ] **Undeclared runner prerequisites.** A job that assumes a tool present on one runner image breaks on another. Confirm every non-trivial tool the job invokes is either installed by a step or declared as a runner requirement — a self-hosted runner is not equivalent to a hosted image.
- [ ] **Path filters that exclude their own trigger.** A workflow filtered to paths that no longer exist, or that exclude the file that would break it, never runs.

### 5. Docs-versus-reality drift (generic)

- [ ] Spot-check commands quoted in `README.md`, adoption guides, and the top-level docs: each command exists, its flags are current, and its described behavior matches what it does.
- [ ] Spot-check paths quoted in documentation: each file or directory still exists at the stated location.
- [ ] Check that documented defaults match the actual defaults in the schema or code, not an earlier release's.
- [ ] Check that any inventory or count stated in prose is derived from its source of truth and still correct.

### 6. Generic fallback (no standards packages installed)

- [ ] Formatter and linter report clean over the repository's declared scope.
- [ ] CI is green on the default branch, not merely on the last pull request.
- [ ] Documentation spot-check from step 5 passes.
- [ ] Lockfiles are consistent with their manifests.

## Record the outcome

- [ ] For each confirmed difference, record what the repository claimed, what it actually does, and which side is wrong.
- [ ] Fix drift at its owner: a package option for managed content, the source file for consumer-owned content, the documentation when the code is right.
- [ ] Open an issue for every difference you did not fix, including the ones you decided to accept — an accepted difference that is not written down becomes an unexplained one.
- [ ] Re-run the reconcile check and the repository's gates, and record the exact commands and their outcomes.
