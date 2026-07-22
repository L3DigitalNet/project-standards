---
schema_version: '1.1'
id: 'runbook-p5m7nf-upgrading-from-v4-to-v5'
title: 'Upgrading from v4 to v5'
description: 'Step-by-step runbook for migrating a consuming repository from project-standards v4 authority to the v5 control plane.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-05'
updated: '2026-07-22'
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
- Install or invoke the exact v5 release you intend to pin. For 5.6.0:

  ```bash
  uv tool install --force "git+https://github.com/L3DigitalNet/project-standards@v5.6.0"
  project-standards --version
  ```

  Confirm that the command reports `project-standards 5.6.0` before continuing.

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
project_spec:
  workflow_ownership: consumer-owned # validate-specs.yml
```

Package options remain closed sets: a key that no selected package's migration provider recognizes produces `CP-MIGRATION-UNCLAIMED-SETTING`, while every recognized key — ownership escape or ordinary option — is carried into the migrated configuration. The selected package adoption guides define the same keys for unified `.standards/config.toml` configuration after migration.

A stock workflow from an older package major can differ from the currently recognized migration signature even when nobody customized it. Treat that state explicitly: choose `consumer-owned` if the repository intends to retain the older workflow, or restore the current legacy package bytes before migrating to managed ownership. Do not label or discard the file as accidental drift.

A relinquished target is intentionally absent from the action list because the resulting package has no ownership claim on it. The migrated option and unchanged target bytes are the confirmation: inspect both in the preview/post-apply review and keep the consumer-owned file in the repository's own verification scope.

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

## 5. Re-pin workflows and the tool

Pin reusable workflows and the installed CLI to the same v5 release line. Use `@v5` for compatible updates or `@v5.6.0`/a commit SHA for an immutable pin. Never mix a v5 workflow with a v4 `standards-ref`.

Self-hosted package workflow mode removes the remote reusable-workflow dependency for Markdown Tooling or Project Specification, but the repository must then commit the package-managed self-hosted workflow bytes.

V5's live and self-hosted workflows use Node 24-generation actions. GitHub-hosted runners already satisfy the runtime requirement; self-hosted runners must run GitHub Actions Runner v2.327.1 or newer before adopting the v5 workflow bytes. The lockfile-free Markdown formatter keeps setup-node package-manager caching disabled, while workflows that run `npm ci` retain explicit npm caching.

## 6. Understand same-major refresh

A newer v5 tool may carry a compatible updated catalog-5 snapshot. `reconcile` previews that catalog refresh together with affected `latest` package updates; `--apply` publishes the catalog and central lock transactionally.

Refresh preserves exact pins, package options, accepted-major tracks, referenced extensions, and unrelated files. It refuses an unavailable pin/track, incompatible default change, older-tool downgrade, or catalog-major mismatch.

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
