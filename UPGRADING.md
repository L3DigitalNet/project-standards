---
schema_version: '1.1'
id: 'runbook-p5m7nf-upgrading-from-v4-to-v5'
title: 'Upgrading from v4 to v5'
description: 'Step-by-step runbook for migrating a consuming repository from project-standards v4 authority to the v5 control plane.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-05'
updated: '2026-07-31'
tags:
  - 'migration'
  - 'upgrade'
  - 'versioning'
aliases: []
related:
  - 'CHANGELOG.md'
  - 'docs/usage.md'
  - 'meta/versioning.md'
  - 'standards/README.md'
  - 'standards/agent-handoff/adopt.md'
---

# Upgrading from v4 to v5

`project-standards` 5.0.0 replaces the legacy `.project-standards.yml` and package-specific provenance model with one committed `.standards/` catalog, desired config, and central lock. This is an explicit repository migration, not a pin-only upgrade.

The v5 tool keeps a warned fallback for a repository that still has only `.project-standards.yml`. The YAML is a read-only authority input: v5 never rewrites it or merges YAML and TOML authority, but explicitly mutating compatibility commands such as `fix` retain their documented repository writes. V6 removes that fallback, so every V4 consumer must complete this migration before moving beyond v5.

## Before you start

- Upgrade on a branch with a clean, reviewed working tree.
- Use Python 3.14 or newer.
- Install or invoke the exact v5 release you intend to pin. For 5.26.0:

  ```bash
  uv tool install --force "git+https://github.com/L3DigitalNet/project-standards@v5.26.0"
  project-standards --version || project-standards --version
  ```

  Confirm that the command reports `project-standards 5.26.0` before continuing. The first `--version` probe immediately after a forced install can fail transiently while the freshly installed environment finishes import wiring; retry once before treating a failure as real.

- Preserve `.project-standards.yml`, recognized package locks, and managed artifacts until migration apply succeeds.
- Review the current package-specific [adoption guide](standards/README.md) for option and output changes.
- Inventory the standards the repository actually uses. A copy-adopted package with no legacy configuration namespace cannot be inferred from file presence alone; plan to enable it explicitly after the authority migration.
- Search consumer-owned automation for legacy dependencies before apply:

  ```bash
  rg -n '\.project-standards\.yml|project-standards/.+@v[1-4]' .github scripts
  ```

  Package-known callers are retired by migration. Unrelated consumer-owned workflows are preserved, so update any matches they contain deliberately.

Do not run plain `init` in a legacy repository; it correctly refuses split authority.

## 1. Preview the complete migration

Run both human and JSON previews against the same repository bytes. Keep the machine-readable report outside the repository so it cannot be mistaken for a migration output or committed accidentally:

```bash
report=$(mktemp "${TMPDIR:-/tmp}/project-standards-migration.XXXXXX")
trap 'rm -f -- "$report"' EXIT
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --json >"$report"
```

Preview is read-only. Review every selected package, migrated option, recognized artifact, ownership transfer, planned output, finding, and legacy retirement action. Resolve before apply:

- unknown or unsupported legacy versions;
- modified managed files that no preservation path covers;
- duplicate or overlapping ownership claims;
- unsafe paths, symlinks, or unclassified legacy artifacts;
- missing repository intent that a closed package option must preserve.

Rerun preview after each correction. Do not edit the repository between the accepted preview and apply.

Preview exit codes carry the readiness signal: `0` means the plan is applicable with no error findings and is ready to apply; `1` means the plan is blocked and the findings above list what to resolve. The JSON `ok` and `applicable` fields agree with the exit code, so a wrapper may gate on either.

### Resolve common preview findings

| Finding | Meaning | Resolution |
| --- | --- | --- |
| `CP-MIGRATION-STATE` | The repository authority cannot be interpreted as one complete legacy migration input. | Read the accompanying detail before changing files. Remove neither authority. Repair the reported missing, partial, or conflicting control state, then rerun preview. If an earlier migration was interrupted, use the recovery procedure below. |
| `CP-MIGRATION-CONFIG` | A migration provider mapped legacy settings to options the selected package does not accept. | Correct the legacy values or the migration provider mapping. This finding blocks apply but does not suppress other migration findings. |
| `CP-MIGRATION-LEGACY-BLOCK` | A bounded legacy block has partial, duplicated, or reversed markers. | Restore a known managed block or remove the partial markers, then rerun preview. |
| `CP-MIGRATION-SETTING-MISSING` | A migration provider claimed a legacy setting that is not present. | Update the provider declaration or the legacy configuration. |
| `CP-MIGRATION-SETTING-OVERLAP` | Migration providers claimed overlapping legacy settings. | Use the reported package identities to make their setting claims disjoint. |
| `CP-MIGRATION-CLAIM-OVERLAP` | Several packages claimed the same legacy object. | Use the reported package identities to make their package claims disjoint. |
| `CP-MIGRATION-UNCLAIMED-ARTIFACT` | Recognized legacy content has no ownership disposition. | Make the selected migration provider claim or preserve the artifact. |
| `CP-MIGRATION-BOUNDED-ORPHAN` | A bounded legacy block has no safe replacement target. | Add a replacement that preserves content outside the managed block. |
| `CP-MIGRATION-PLATFORM-VERSION` | `standards_version` is absent or is not the recognized platform tag `"v3"` or `"v4"`. | Released repositories may contain a full tool release such as `"v4.3.0"`, or omit the key. Normalize either form to `standards_version: "v4"` before preview. The two accepted tags name the same legacy wire format. |
| `CP-MIGRATION-UNCLAIMED-SETTING` | A legacy setting is not represented by any selected package. | Remove the unknown key from `.project-standards.yml`, or select the package that migrates it. |
| `CP-MIGRATION-LEGACY-DIGEST`, `PT-LEGACY-MODIFIED`, `MT-LEGACY-MODIFIED` | A recognized file's bytes match no shipped package history. | Instruction blocks and bounded JSON/JSONC/YAML units resolve automatically: consumer content outside the package-owned unit is preserved and the preview reports `CP-MIGRATION-BOUNDED-TAKEOVER`. Property-level conflicts inside `.editorconfig` and other semantic targets still block; use the reported identity to restore or remove only the conflicting property. For a customized whole-file target, declare its documented ownership option as `"consumer-owned"` in `.project-standards.yml` before previewing. Migration then preserves the bytes and leaves the file consumer-owned. Otherwise restore the released bytes (adopt again with the old CLI, or check the file out from history) and rerun preview. |
| `CP-MIGRATION-BOUNDED-TAKEOVER` (warning) | Consumer-modified content at a bounded-managed target is preserved; the package takes over only its managed block or properties inside the file. | No action required to apply. After apply, review the preserved file and delete any superseded copy-adopt boilerplate the old release left behind. |
| `CP-MIGRATION-OWNER-RESOLUTION` | A consumer-owned preservation claim is incomplete. | Ensure the legacy configuration supplies the literal `consumer-owned` value through the documented option (for example `python_tooling.workflow_ownership`) and rerun preview. |
| `CP-CONSUMER-CONFLICT` | A pre-existing file value conflicts with a package-owned unit and no lock history explains it. | The finding reports the expected package value, the observed repository value, and — when the package declares them — the governing options that can reproduce the repository intent. Set a listed governing option (in `.project-standards.yml` during migration) so the package renders the intended value, align the value with the reported expected value, or remove the consumer value so the package can create it, then rerun preview. A finding that states no declared option governs the unit means only alignment or ownership resolution can clear it. Unrelated sibling values remain consumer-owned. |

Python Tooling owns the selected `[build-system]`, but it does not claim `[tool.uv].package`. A repository that uses the tooling baseline without publishing an installable package can retain the managed backend while declaring:

```toml
[tool.uv]
package = false
```

That consumer-owned setting survives reconciliation and tells uv not to build or install the project during ordinary environment synchronization.

Python Tooling 1.5 also narrows checker and pytest ownership to the canonical keys it renders. Additional settings in the same tables remain consumer-owned: for example, `[tool.basedpyright].extraPaths` and `[tool.pytest.ini_options].pythonpath` survive V4 migration and later reconciliation. A conflict on a canonical key still blocks before write.

The current package successors also correct three migration and validation edge cases. Markdown Tooling 1.7 safely adopts an exact released caller whose automatic trigger is disabled. Project Specification 1.4 treats a configured corpus with no matching files as an informational success. Agent Handoff 1.4 excludes only exact central-lock-authenticated managed Markdown envelopes from instruction-file size budgets; malformed, unlocked, or drifted lookalikes still count.

The 5.8.0 release advanced three more successors that widen what migrates cleanly. Python Tooling 1.8 adds `pytest.test_paths`, an array of collection roots (unique safe relative paths, default `["tests"]`) that governs the pytest `testpaths`, the checker `include`, the Ruff `src` value, and the VS Code `python.testing.pytestArgs`, but never `coverage.run.source`. A repository whose suite does not live in `tests/` sets it under the `python_tooling` namespace in `.project-standards.yml` to resolve the include/`testpaths` `CP-CONSUMER-CONFLICT` before apply; the conflict now names the governing option instead of `none declared`. Undeclared, every unit renders byte-identically to 1.7. Markdown Tooling 1.8 accepts a `.markdownlint.json` that is byte-for-byte the shipped config re-serialized with literal (non-escaped) UTF-8 punctuation: the proven legacy byte form is parsed-JSON-equal to the shipped resource, so a consumer holding it migrates to managed ownership of the current escaped bytes with no findings on that file instead of blocking as a modified config (`CP-MIGRATION-LEGACY-DIGEST` / `MT-LEGACY-MODIFIED`). Markdown Frontmatter 1.5 adds the `workflow_ownership` escape for `.github/workflows/validate-standards.yml` documented in §3.

The 5.9.0 release advances the current defaults to Python Tooling 1.9, Markdown Tooling 1.9, Agent Handoff 1.5, and CLI Documentation 1.4.

The 5.10.0 release advances the current defaults again, to Python Tooling 1.10, Markdown Tooling 1.10, Agent Handoff 1.6, and Markdown Frontmatter 1.6; CLI Documentation stays at 1.4. Markdown Tooling 1.10 adds `lint_generated_exclusions` (default `true`), which appends `.pytest_cache/**`, `.ruff_cache/**`, `.venv/**`, and `node_modules/**` as negative lint globs after any consumer-declared positive glob; set it to `false` under the `markdown_tooling` namespace to keep the 1.9 lint scope byte-for-byte. Python Tooling 1.10's `scripts/check.py` rejects an unrecognized argument even alongside `--help`, so a CI step that passed a typo and exited `0` will now fail. Removing the retired `.mypy_cache` exclusion during the Python Tooling 1.9 to 1.10 upgrade can leave one whitespace-only line in `.vscode/settings.json`; if a Prettier gate flags the file, run Prettier on it once — reconciliation stays drift-free either way. Review their [current adoption guides](standards/README.md) before migration or same-major refresh; retained predecessor behavior above remains historical release guidance.

The 5.11.0 release advances the current defaults to ADR 1.3, CLI Documentation 1.5, and Project Spec 1.5; Python Tooling stays at 1.10, Markdown Tooling at 1.10, Agent Handoff at 1.6, and Markdown Frontmatter at 1.6. All three successors change documentation links only, with no option, contribution, or output change, so a consumer already reconciled at ADR 1.2, CLI Documentation 1.4, or Project Spec 1.4 needs no migration work for them. One engine change does affect this stage: the Agent Handoff shape checks now fall back to `shape.defaults.max_paragraph_chars` (360 characters in the shipped policy) for a document that declares no limit of its own. The pre-apply `agent-handoff shape-check` run below has no payload provider to defer to, so a long paragraph that passed silently under 5.10.0 can report a finding, and in a document configured at fatal severity — `docs/TODO.md` in the shipped policy — it blocks. Shorten the paragraph, or declare that document's own `max_paragraph_chars`.

The 5.12.0 release advances the current defaults to Markdown Frontmatter 1.7, Markdown Tooling 1.11, and Agent Handoff 1.7; Python Tooling stays at 1.10, ADR at 1.3, CLI Documentation at 1.5, and Project Spec at 1.5. All three successors only widen or correct behavior. Markdown Frontmatter 1.7's `new-doc-id` helper probes for `uv` and runs `uv run --no-project python3 -` when it is present, so a workstation that shims `python3` into a uv-strict wrapper keeps a working identifier source; a consumer without uv keeps the original invocation. Markdown Tooling 1.11 recognizes one more released `.markdownlint.json` byte form as known legacy content, so a consumer holding it migrates to managed ownership instead of blocking as a modified config; no rendered artifact changes. Agent Handoff 1.7's credential checker reports one finding per offending line, naming that line, and exempts genuine runtime acquisition — `$( … )`, and a command-shaped backtick span one of whose tokens names a credential reference — so an assignment that retrieves a credential at runtime stops being reported as one that stores it. That exemption also reaches the shared engine, so it applies on an older Agent Handoff pin too; it only withdraws findings. No option, contribution, or ownership surface changes in any of the three, so a consumer already reconciled at Markdown Frontmatter 1.6, Markdown Tooling 1.10, or Agent Handoff 1.6 needs no migration work beyond the same-major refresh.

## 2. Apply the reviewed migration

```bash
project-standards init --catalog 5 --migrate --apply
```

Apply rechecks the inspected bytes, materializes package outputs, runs unified verification, publishes `.standards/lock.toml`, and only then removes `.project-standards.yml` and recognized package-specific locks. A stale plan, ambiguity, provider refusal, or verification failure preserves recoverable legacy authority and exits non-zero.

When Agent Handoff is selected, run its size and shape reports before apply. Consumer-owned knowledge is preserved, but a pre-existing hard-cap violation in `docs/handoff/state.md` remains a validation error and must be routed to its durable owner rather than copied into the new eager state:

```bash
project-standards agent-handoff size-report --repo .
project-standards agent-handoff shape-check --repo .
```

Running these reports under legacy authority before apply is expected. The tool emits only a factual note — `note: reading legacy .project-standards.yml authority; the V5 control plane takes over after migration` — and does not instruct you to stop; the pre-migration reports this runbook prescribes and the emitted message no longer contradict each other.

The same checkpoint holds when you enable Agent Handoff on a control plane that has already migrated. Between `standards enable` and `reconcile --apply` the package is enabled but absent from `.standards/lock.toml` — the normal state of that window, not an inconsistency — and the read-only reports run there against the desired selection, naming their basis: `note: reading the not-yet-applied selection: agent-handoff@1.8; it is enabled but absent from .standards/lock.toml until project-standards reconcile --apply locks it`. They write nothing, so a hard-cap violation still surfaces before any eager state exists.

A read-only command also resolves the applied lock when the installed release is newer than the one your repository has reconciled, which is what makes the pre-change inventory (`project-standards agent-handoff legacy-report --repo .`) runnable before a same-major refresh. That note names the locked package version — `note: reading the applied lock: agent-handoff@1.6; installed release 5.15.0 is not reconciled into this repository yet` — and reconciliation, not the report, advances the selection.

If apply is interrupted after unified files appear beside the legacy configuration, keep both authorities. Rerun the migration entry point: it recognizes only a sanctioned migration prefix, previews the recovery, and completes it on apply.

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

`reconcile --repair-state` is reserved for interrupted same-major catalog refreshes after legacy authority has already been retired.

Review the result:

```bash
git status --short
git diff --check
project-standards standards list
project-standards reconcile --check
```

If migration changed `pyproject.toml`, refresh the consumer dependency lock before the final reconcile check:

```bash
uv lock
project-standards reconcile --check
```

Commit `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, and every reconciled output together.

Enable any package identified in the pre-migration inventory that had no legacy configuration namespace, then preview and apply that package separately. Do not infer ownership by deleting or adopting copy-pasted files manually.

## 3. Review selectors and package options

Each enabled package has two separate version planes:

- `standards.<id>.version` selects an immutable package payload (`latest` or exact `major.minor`);
- package options such as `contract_version` select supported document/schema behavior inside that payload.

Changing one does not silently change the other. Use `project-standards standards version` for the payload selector, edit only declared package options in `.standards/config.toml`, and preview with `reconcile` before apply.

During legacy migration, `.standards/config.toml` does not exist yet. Every setting a selected package's migration provider recognizes may be set under that package's namespace in `.project-standards.yml`, and the next preview picks it up. That includes ordinary package options — frequently required to resolve a `CP-CONSUMER-CONFLICT` before apply — spelled as nested YAML under the namespace:

```yaml
python_tooling:
  ruff:
    extend_exclude: ['.claude', '.vscode', '*.md']
```

The whole-file ownership escapes are the subset of those options that transfers file ownership instead of shaping rendered values:

```yaml
python_tooling:
  workflow_ownership: consumer-owned # .github/workflows/check.yml
  script_ownership: consumer-owned # scripts/check.py
markdown_tooling:
  markdownlint_config_ownership: consumer-owned # .markdownlint.json
  lint_workflow_ownership: consumer-owned # lint-markdown.yml
  format_workflow_ownership: consumer-owned # format.yml
cli_documentation:
  workflow_ownership: consumer-owned # cli-docs-check.yml
  usage_ownership: consumer-owned # docs/usage.md
spec:
  workflow_ownership: consumer-owned # validate-specs.yml
markdown:
  frontmatter:
    workflow_ownership: consumer-owned # validate-standards.yml
```

Package options remain closed sets: a key that no selected package's migration provider recognizes produces `CP-MIGRATION-UNCLAIMED-SETTING`, while every recognized key — ownership escape or ordinary option — is carried into the migrated configuration. The selected package adoption guides define the same keys for unified `.standards/config.toml` configuration after migration.

A stock workflow from an older package major can differ from the currently recognized migration signature even when nobody customized it. Treat that state explicitly: choose `consumer-owned` if the repository intends to retain the older workflow, or restore the current legacy package bytes before migrating to managed ownership. Do not label or discard the file as accidental drift.

A consumer-owned workflow keeps its job names outside reconciliation, and so does the hosted configuration that depends on them. GitHub branch-protection and ruleset required status checks match the workflow job's display name, which lives in repository settings rather than in Git, so renaming a job to match a new toolchain can orphan a required context and leave later pull requests unmergeable while migration, reconciliation, and every local check still pass. Inspect the hosted required contexts before renaming a check job, and coordinate the rename with the branch-protection or ruleset update.

A relinquished target is intentionally absent from the action list because the resulting package has no ownership claim on it. The migrated option and unchanged target bytes are the confirmation: inspect both in the preview/post-apply review and keep the consumer-owned file in the repository's own verification scope.

`markdown.frontmatter.workflow_ownership: consumer-owned` relinquishes `.github/workflows/validate-standards.yml`, and it carries an obligation the other escapes do not. Markdown Frontmatter composes that caller from four bounded contributions — the workflow `name`, `on` triggers, `permissions`, and the `frontmatter` job — so relinquishing it transfers the whole file, including the job wiring that dispatches the reusable Frontmatter workflow. The package then keeps none of the job reference, permissions, or triggers current; track upstream workflow changes yourself and keep the caller in the repository's own verification scope. This is the declared preservation path for a caller that was hand-edited (added `paths:` filters, comments, or extra jobs) and therefore holds a byte form migration does not recognize — declare the option in the legacy configuration before migration to preserve those exact bytes instead of blocking. The documented path back to managed ownership: restore the shipped caller bytes for your `workflow_mode`, then set `workflow_ownership` back to `managed`; the next reconcile recomposes the four contributions and resumes managing the file.

An exact selector remains pinned. `latest` follows only the compatible default or an explicitly accepted package-major track. Entering or leaving a non-default major requires the matching `--allow-major STANDARD_ID@MAJOR` and a declared migration path.

## 4. Verify provider-backed commands

Under unified authority, validators and authoring commands resolve the selected payload. Read-only providers receive immutable snapshots; authoring providers return typed plans whose writes are performed by the platform executor.

Run the commands for the selected packages, including as applicable:

```bash
project-standards fix
project-standards reconcile --apply
project-standards validate
project-standards spec validate
project-standards spec lint --strict
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
```

Markdown Tooling's local `npx --no-install` checks require Node plus repository-local `prettier` and `markdownlint-cli2` installations. Install the consumer's declared Node dependencies first (`npm ci` when it has a lockfile); the managed GitHub callers provision their own tooling.

`fix` can change files whose current digests participate in the central lock. Reconcile those reviewed changes before `validate`; otherwise validation correctly reports `CP-DRIFT` against the pre-fix lock.

An explicit `--config .project-standards.yml` is now a legacy/debug-only path and is rejected under unified authority.

### Frontmatter serialization convergence

The 5.8.0 release converged `format-frontmatter` (the format stage of `fix`) with the Markdown Tooling Prettier configuration on one frontmatter serialization. The formatter now emits each scalar in the minimal-escape quote style — the style that needs no escapes, which is Prettier's resting state under `singleQuote: true` — instead of unconditionally single-quoting and doubling apostrophes (`'Apple''s'`). Both quote forms are accepted: a value already spelled single-quoted, or double-quoted when double is the minimal style for that value, is kept verbatim; only a value in neither form is re-spelled. Legacy single-quoted spellings therefore stay valid forever, and no scalar the 5.7.0 checker accepted is now reported as needing reformatting — an additive, previously-passing-safe widening that exact `markdown-frontmatter@1.4` pins inherit through the shared engine. The one-time effect a consumer sees is that `format-frontmatter` keeps a legacy escaped spelling such as `'Apple''s'` byte-identical, while Prettier performs the one-time normalization to the minimal `"Apple's"` form the next time it rewrites the file — a form `format-frontmatter` now also accepts — so the two companion tools no longer each flag the other's output. A latent corruption where control-character values were re-emitted as literal control bytes is fixed at the same time.

## 5. Re-pin workflows and the tool

Pin reusable workflows and the installed CLI to the same v5 release line. Use `@v5` for compatible updates or `@v5.12.0`/a commit SHA for an immutable pin. Never mix a v5 workflow with a v4 `standards-ref`.

Self-hosted package workflow mode removes the remote reusable-workflow dependency for Markdown Tooling or Project Specification, but the repository must then commit the package-managed self-hosted workflow bytes.

V5's live and self-hosted workflows use Node 24-generation actions. GitHub-hosted runners already satisfy the runtime requirement; self-hosted runners must run GitHub Actions Runner v2.327.1 or newer before adopting the v5 workflow bytes. The lockfile-free Markdown formatter keeps setup-node package-manager caching disabled, while workflows that run `npm ci` retain explicit npm caching.

## 6. Understand same-major refresh

A newer v5 tool may carry a compatible updated catalog-5 snapshot. `reconcile` previews that catalog refresh together with affected `latest` package updates; `--apply` publishes the catalog and central lock transactionally.

Refresh preserves exact pins, package options, accepted-major tracks, referenced extensions, and unrelated files. It refuses an unavailable pin/track, incompatible default change, older-tool downgrade, or catalog-major mismatch.

### Producing repositories

A repository that builds the catalog it publishes is the one exception to the equal-release rule. Between two release trains its installed catalog legitimately carries payloads its committed `.standards/catalog.toml` does not, at an unchanged tool release, and a publishing command would otherwise refuse that state. Declare the repository's side of the contract once in `.standards/config.toml`:

```toml
[project_standards]
schema_version = "1.1"
catalog = "5"
role = "producer"
```

`role` is optional and defaults to `consumer`, whose behavior is exactly what this section describes; a consuming repository changes nothing and keeps its `schema_version = "1.0"` header. The key requires `schema_version = "1.1"`, and a `1.0` header that carries it is rejected.

The declaration widens one rule, in one window: a catalog-publishing command — `init`, `upgrade`, and `reconcile --apply` — accepts an installed catalog that differs from the committed one while the tool release is unchanged, and reports the release classification instead of refusing over it. Everything else is unchanged. An older installed release, a catalog-major mismatch, a central lock that disagrees with the committed catalog lineage, and the package release policy once the release has advanced all still refuse. The role is a local declaration rather than desired state, so writing it does not itself change `.standards/lock.toml`.

### What the 5.16.0 defaults rewrite on refresh

Refreshing onto the 5.16.0 catalog changes bytes in two managed surfaces. Both are expected diffs, not drift; review them once and commit them with the refresh.

**Ruff ownership moves to leaf keys (Python Tooling 1.11 → 1.12).** Through 1.11 the package owned `[tool.ruff]` as one whole table, so any plugin sub-table you added — `[tool.ruff.lint.flake8-bugbear]`, `[tool.ruff.lint.extend-per-file-ignores]`, and the rest — conflicted with the package and no option could express keeping it. From 1.12 the package owns only the eleven Ruff keys it renders; every undeclared `[tool.ruff.*]` sub-table is consumer-owned by construction and survives reconciliation unchanged. Two consequences are visible in the first apply. The three additive Ruff lists (`extend_include`, `extend_select`, `extend_ignore`) now render their keys unconditionally, as empty arrays when the option is empty, because each is a separately owned key and an empty array is inert in Ruff; through 1.11 an empty list emitted no key at all. Coverage `omit` is unchanged and still emits nothing when empty. The 1.11→1.12 migration also relocks the whole-table predecessor, so the transition does not raise `CP-LOCK-INCONSISTENT`.

**The documented Markdown verification commands become corpus-bounded (Markdown Tooling 1.12 → 1.13).** The managed instruction block and the versioned prose now render the local Prettier and markdownlint recipes from the same `markdown_globs` + `config_globs` selection the CI caller uses, rather than a broad glob. The normative form selects tracked files through `git ls-files` with `:(glob)` pathspec magic — the only form that excludes `.git/info/exclude` scratch files — with a bounded-glob fallback for contexts without Git. The selection narrows; nothing that was previously checked in CI stops being checked. If you own the block through `instructions_ownership = "consumer-owned"`, copy the new recipe across by hand.

### What the 5.17.0 defaults rewrite on refresh

Refreshing onto the 5.17.0 catalog is byte-neutral for the three package advances and consumer-acted for the fourth. Markdown Tooling 1.14, Project Specification 1.8, and Markdown Frontmatter 1.10 only add the optional top-level `runner_labels` config option; leave it unset and every managed output renders exactly as its predecessor did, so a refresh that touches nothing but these three is expected to produce no diff beyond the lock. Set it to the labels of a self-hosted runner pool and the caller-mode managed workflows pass them through to the reusable workflows' `runner-labels` input as managed content, which is the supported alternative to hand-editing a generated caller and tripping `CP-MODIFIED-MANAGED`.

**The Agent Handoff SessionStart launcher becomes a committed binary (Agent Handoff 1.9 → 1.10).** The Claude Code and Codex registrations now invoke a statically linked `linux/amd64` executable directly instead of resolving an interpreter for `session_start.py`, and the emitted context is byte-identical on both transports. Two consequences need a decision at refresh time. The payload contract has no policy for retiring a file an earlier version installed, so reconciliation preserves the superseded `session_start.py` — delete it yourself once the binary is registered. And 1.10 ships that one platform, so a consumer who is not `linux/amd64` selects manual startup where 1.9 ran anywhere a supported interpreter did.

### What the 5.18.0 defaults rewrite on refresh

Refreshing onto the 5.18.0 catalog rewrites nothing by default. All four package advances — ADR 1.4 → 1.5, Python Tooling 1.12 → 1.13, Agent Handoff 1.10 → 1.11, and GitHub Workflow 1.0 → 1.1 — are additive or documentation-only, so a refresh that touches nothing but these four is expected to produce no diff beyond the lock.

**ADR 1.5** adds an optional amendment vocabulary: reciprocal `project.amends` / `project.amended_by` frontmatter lists, a blockquote amendment note between the title and Context and Problem Statement, and an optional `### Amendments` subsection under Decision Outcome. Both fields default to empty, no section becomes required, `schema_version` stays `1.1`, and the option surface and validator bytes are 1.4's, so every existing ADR validates untouched. The revised `docs/adr/adr.template.md` reaches new consumers automatically: the scaffold is `policy = "create-only"`, so reconcile writes it when it is absent and never touches it again. A repository that already has one and wants the 1.5 prompts refreshes it by **copying `standards/adr/versions/1.5/templates/adr.md` over its scaffold** and reviewing the result like any other change to a file it owns — the sanctioned mechanism as amended in [ADR 0028](docs/adr/adr-0028-create-only-artifact-refresh.md) on 2026-08-09. Do not delete the scaffold expecting reconcile to recreate it: an applied reconcile records the deletion as a permanent `[[create_only_absences]]` entry in `.standards/lock.toml` and no later reconcile recreates the file. After a copy, `.standards/lock.toml` keeps the digest it recorded when the scaffold was created — a create-only unit is not re-digested on later reconciles — so lock and file disagree by design. That is the documented steady state, not drift: reconcile plans the unit as `preserve` and `reconcile --check` stays clean.

**Python Tooling 1.13** adds `ruff.extend_per_file_ignores`, a typed glob-to-rules table that exempts named rules for one path without disabling them repository-wide. Entries compose into the package-owned `[tool.ruff.lint.per-file-ignores]` table rather than replacing it, and the empty default renders the 1.12 bytes. Ruff's own `[tool.ruff.lint.extend-per-file-ignores]` table stays consumer-owned, so the documented pre-1.13 workaround keeps working and does not become `CP-MODIFIED-MANAGED` drift.

**Agent Handoff 1.11** and **GitHub Workflow 1.1** change no option, artifact, contribution, or provider byte; the Agent Handoff launcher is 1.10's exact executable. GitHub Workflow 1.1 rebuilds `gh-workflow`, whose `ledger` subcommand no longer stamps a read timestamp into `docs/GH-WORKFLOWS.md` — the first regeneration after the refresh therefore drops that line, and every later one against unchanged work state produces no diff at all.

### What the 5.23.0 defaults rewrite on refresh: GitHub Workflow 1.5 removes the ledger

**GitHub Workflow 1.4 → 1.5 removes the `ledger` subcommand**, and with it the generated `docs/GH-WORKFLOWS.md`. This is the one advance in this train that a consumer must act on by hand.

`gh-workflow ledger` now exits `2` as an unknown subcommand; the remaining eight — `audit`, `new`, `set`, `close`, `reopen`, `summary`, `receipt`, `check` — are unchanged, and `summary` and `receipt` render byte-identically to 1.4 for the same work state. Any script, alias, or session habit that invoked `ledger` needs a different answer: `gh-workflow summary` prints the same view to stdout without writing a file.

**Delete `docs/GH-WORKFLOWS.md` yourself if you committed it.** The file was never a payload artifact — no digest, outside drift-check — so reconcile does not know the path and will neither refresh nor remove it, and the package will not delete consumer content on your behalf. `project-standards upgrade` reports it as a warning instead. Left in place it is a frozen snapshot of work state that nothing regenerates and no tool owns. If you ignored the path rather than committing it, drop the `.gitignore` entry; if you excluded it from a tooling scope — a `markdown-frontmatter` `exclude` entry, for example — drop that too, in the same change.

The rest of 1.5 is guidance: `SKILL.md` is now one bounded read carrying a single complete routing-and-flag table, `field-vocabulary.md` keeps only the vocabulary the binary cannot state in a refusal, and the managed `AGENTS.md` / `CLAUDE.md` block carries the routing table, so its bytes change on the first reconcile after the refresh. The Codex companion `agents/openai.yaml` is now delivered under `.agents/` only; the `.claude/` copy is removed on reconcile, because Claude Code never read it. No configuration option changed, so a repository that sets nothing keeps its `.standards/config.toml` as it is.

### What the 5.24.0 defaults rewrite on refresh: Markdown Frontmatter 1.14 adds agent-instruction blocks

**Markdown Frontmatter 1.13 → 1.14** adds a managed `markdown-frontmatter` block to `AGENTS.md` (when `harnesses` contains `codex`) and to `CLAUDE.md` (when `harnesses` contains `claude-code`); a `reconcile --apply` onto this catalog writes the block where it is missing and nothing is removed.

Installed skill and template copies also switch their placeholder token from `xxxxxx` to `XXXXXX`. A copy carried over from before the switch keeps the old token and now fails `validate-id`; run `validate-id --fix` to bring it current.

### What the 5.25.0 defaults rewrite on refresh: GitHub Workflow 1.6 changes the follow-up rule

**GitHub Workflow 1.5 → 1.6 replaces one standing invariant** and nothing else. The rule that discovered durable follow-up work becomes an issue before the session ends is withdrawn. In its place: a related finding a session can address gets no issue — it is fixed in place when the repository being worked in owns it, and filed against the owning repository when an upstream dependency inside the organization owns it. Only a finding large enough to warrant a full separate session goes to the operator as a question, to file or to take on now.

The rule is stated in the packaged `SKILL.md` and in the managed `AGENTS.md` / `CLAUDE.md` block, and `references/pr-standard.md` and `references/summary-format.md` are aligned with it, so those bytes change on the first reconcile after the refresh. Nothing else moves: the delivered tree, the `gh-workflow` binary's eight subcommands, the configuration contract, and every other invariant are 1.5's. No configuration option changed, so a repository that sets nothing keeps its `.standards/config.toml` as it is.

**Agent Handoff 1.15 → 1.16 re-cites one internal comment.** The provider's cross-file contract comment above `_SKILL_TARGETS` named a per-family registry test as the place that pins the skill-target/`payload.toml` agreement; it now names the catalog-wide `tests/package_contract/test_provider_registry.py` (#196). No option, policy value, template, hook, provider behavior, contribution, or artifact target changes, so `reconcile --apply` onto this catalog rewrites nothing for an already-conforming repository.

### What the 5.25.0 defaults rewrite on refresh: Project Specification 1.10 resyncs the templates

**Project Specification 1.9 → 1.10 replaces the three shipped templates** with byte-identical copies of this repository's canonical template source and changes nothing else — no option, provider, schema, artifact, or lint rule moves. `spec new` and `spec upgrade` therefore scaffold the same text the selected package's conformance check measures against, which they had stopped doing after two source edits landed without a payload cut (project-standards issue #199).

Existing specifications are not rewritten by reconciliation, and one surface did move: Appendix D of the Full template closes on a reworded paragraph, because the wording it replaces contained a code span `spec lint` reads as a field to fill — unwinnable inside a checked surface. A **Full** specification carrying the 1.9 text reports `SL-BOILERPLATE` on Appendix D once 1.10 is selected; replace that closing paragraph with the one in `templates/spec-full-template.md`. Light and Standard specifications are unaffected. `project-standards spec lint` names the surface, and `--strict` is what turns it into a CI failure.

### What the 5.26.0 defaults rewrite on refresh: GitHub Workflow 1.7 adds PR admission

**GitHub Workflow 1.6 → 1.7 makes pull-request admission part of the package.** Refreshing onto this catalog rewrites the skill, its six references, and the managed `AGENTS.md` / `CLAUDE.md` block to the 1.7 content on the first reconcile after the refresh; the delivered tree and the two skill trees are otherwise 1.6's, and 1.6 stays retained in the catalog for a repository that pins it explicitly. No configuration option changed (FR-035): the two options, their meanings, and the rendered `policy.toml` are exactly 1.6's, so the upgrade is a version bump.

An admitted change is now either a T0 direct commit — an unambiguous prose repair that touches no protected surface, stays outside active governed work, fits three files and thirty changed lines, and carries exactly one `Workflow-Admission: T0` trailer — or a pull request that declares `Final: #N`, `Supporting: #N`, or `Standalone` under an exact `## Governing work` heading. Agent-created PRs start as drafts; `gh-workflow ready --pr N` and `gh-workflow merge --pr N` are the two paired commands that cross each boundary, and `gh-workflow close --pr N --as OUTCOME --reason S` is the only route for abandoning an open Final.

**A pull request already open before the refresh is repaired only when it is next touched**, by a summary, check, ready, or merge run. Nothing scans for an older PR, and no terminal PR's evidence is rewritten, so there is no migration step and no ledger to keep.

**A script that parsed `gh-workflow`'s exit `1` as "API failure" needs the new exit `3`.** From 1.7 the binary distinguishes a domain finding (exit `1`, validation completed but found something to fix) from an authentication, API, transport, or other operational failure that prevented completion (exit `3`, a new code). Update any caller that treated the two as the same condition.

### What the 5.27.0 defaults rewrite on refresh: one action pin and one corrected reference

**Python Tooling 1.16 → 1.17, Markdown Frontmatter 1.14 → 1.15, and Project Specification 1.10 → 1.11 each advance one pinned action** and nothing else. The `astral-sh/setup-uv` step in each package's rendered CI workflow moves from `v9.0.0` to `v10.0.1` (project-standards issue #201), so the first reconcile after the refresh rewrites `.github/workflows/check.yml`, `validate-markdown-frontmatter.yml`, and `validate-specs.yml` respectively. `setup-uv` publishes no moving major or minor tag from v8.0.0 on, so a repository mirroring a payload byte-exactly could not refresh the pin itself without tripping `CP-MODIFIED-MANAGED`; the refresh has to arrive with the package.

**setup-uv v10 flips one default, and none of the three payloads is exposed to it.** Under `enable-cache: auto`, v10 now disables the cache for `pull_request_target`, `workflow_run`, and `release` events. All three rendered workflows set `enable-cache` explicitly — `true` for Python Tooling, a repository-scoped expression for the other two — so the caching behavior each gate was measured under is unchanged. If you own your workflow (`workflow_ownership = "consumer-owned"`) and wrote `enable-cache: auto` yourself, check whether any of those three events triggers it before you advance your own pin. No configuration option changed in any of the three packages.

**GitHub Workflow 1.7 → 1.8 corrects the risk vocabulary in the delivered reference.** 1.7's `references/pr-standard.md` showed a Standalone PR declaring `Change risk: R2`, but the Ready gate has only ever accepted the four full labels `references/org-schema.yaml` declares. A pull request copying the shipped example verbatim was refused with `GHW-PR-READY-RISK-INVALID` (project-standards issue #202). 1.8 corrects the example to `Change risk: R2 Moderate`, carries the full labels through that reference and `references/review-checklist.md`'s risk ladder, and makes both risk refusals name the four accepted values in the finding's own message rather than only in its remediation — the human output prints the message and drops the remediation, so the refusal is now self-sufficient without `--output json`.

Refreshing rewrites those two references, `SKILL.md`, the `gh-workflow` binary, and the `package_version` stamp inside the rendered `policy.toml` on the first reconcile. **No behavior changes:** the two configuration options, every `policy.toml` value outside that stamp, the ten subcommands, every exit code, and every gate outcome are 1.7's, so a PR body that passed the Ready gate under 1.7 still passes under 1.8. If you keep a PR template or house style that spells the value `R2`, correct it to `R2 Moderate` — that was always what the gate required.

### Comments inside managed TOML regions

Consumer comments attached to a managed `pyproject.toml` unit survive a rewrite. When an apply re-renders a managed table, keyed-set entry, or key, comments found in the rewritten region — inside a multi-line array, trailing an owned line, or on their own line between owned lines — are re-emitted directly above the statement with the same key or table in the new rendering; a comment whose key no longer exists moves above the rewritten unit. Rewrites consume the old region completely, so they leave no stray blank lines, and a follow-up `reconcile --check` stays a no-op. The rendered layout of the managed unit itself (line breaks, indentation, entry order) belongs to the package, so annotate managed regions with comment lines rather than relying on a specific array layout.

## Verify

Run the repository's own checks plus the generic control-plane gates:

```bash
project-standards reconcile --check
project-standards validate
project-standards standards list
git diff --check
```

A second reconciliation must be a no-op. Package-specific adoption guides list their additional verification and troubleshooting commands.

## Rollback

Before successful apply, rollback is simply no action: preview writes nothing, and a failed apply preserves a recoverable authority state.

After successful apply, do not recreate `.project-standards.yml` beside `.standards/`; that is rejected dual authority. Revert the complete migration commit or replay a reviewed reverse patch that restores the legacy config, package locks, and artifacts together, then re-pin the v4 tool/workflows. Validate the restored V4 state before deleting the migration branch.
