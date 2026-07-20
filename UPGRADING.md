---
schema_version: '1.1'
id: 'runbook-p5m7nf-upgrading-from-v4-to-v5'
title: 'Upgrading from v4 to v5'
description: 'Step-by-step runbook for migrating a consuming repository from project-standards v4 authority to the v5 control plane.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-05'
updated: '2026-07-20'
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

The v5 tool keeps a warned read-only fallback for a repository that still has only `.project-standards.yml`. It never merges YAML and TOML authority. V6 removes that fallback, so every V4 consumer must complete this migration before moving beyond v5.

## Before you start

- Upgrade on a branch with a clean, reviewed working tree.
- Use Python 3.14 or newer.
- Install or invoke the exact v5 release you intend to pin. For 5.2.0:

  ```bash
  uv tool install --force "git+https://github.com/L3DigitalNet/project-standards@v5.2.0"
  project-standards --version
  ```

  Confirm that the command reports `project-standards 5.2.0` before continuing.

- Preserve `.project-standards.yml`, recognized package locks, and managed artifacts until migration apply succeeds.
- Review the current package-specific [adoption guide](standards/README.md) for option and output changes.

Do not run plain `init` in a legacy repository; it correctly refuses split authority.

## 1. Preview the complete migration

Run both human and JSON previews against the same repository bytes:

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --json >migration-plan.json
```

Preview is read-only. Review every selected package, migrated option, recognized artifact, ownership transfer, planned output, finding, and legacy retirement action. Resolve before apply:

- unknown or unsupported legacy versions;
- modified managed files that no preservation path covers;
- duplicate or overlapping ownership claims;
- unsafe paths, symlinks, or unclassified legacy artifacts;
- missing repository intent that a closed package option must preserve.

Rerun preview after each correction. Do not edit the repository between the accepted preview and apply.

### Resolve common preview findings

| Finding | Meaning | Resolution |
| --- | --- | --- |
| `CP-MIGRATION-PLATFORM-VERSION` | `standards_version` is not a recognized platform tag. | Supported values are `"v3"` and `"v4"`; they name the same legacy wire format, and every released v3/v4 CLI wrote `"v3"`. Any other value must be corrected to one of the two before preview. |
| `CP-MIGRATION-UNCLAIMED-SETTING` | A legacy setting is not represented by any selected package. | Remove the unknown key from `.project-standards.yml`, or select the package that migrates it. |
| `CP-MIGRATION-LEGACY-DIGEST`, `PT-LEGACY-MODIFIED`, `MT-LEGACY-MODIFIED` | A recognized file's bytes match no shipped package history. | For instruction and shared configuration targets (`CLAUDE.md`, `AGENTS.md`, `.editorconfig`, `.vscode/*`) this resolves automatically: the file is preserved and the preview reports `CP-MIGRATION-BOUNDED-TAKEOVER` instead. For `.github/workflows/check.yml`, either restore the released bytes or declare `workflow_ownership: "consumer-owned"` under `python_tooling:` in `.project-standards.yml`. For any other recognized file, restore the released bytes (adopt again with the old CLI, or check the file out from history) and rerun preview. |
| `CP-MIGRATION-BOUNDED-TAKEOVER` (warning) | Consumer-modified content at a bounded-managed target is preserved; the package takes over only its managed block or properties inside the file. | No action required to apply. After apply, review the preserved file and delete any superseded copy-adopt boilerplate the old release left behind. |
| `CP-MIGRATION-OWNER-RESOLUTION` | A consumer-owned preservation claim is incomplete. | Ensure the legacy configuration supplies the literal `consumer-owned` value through the documented option (for example `python_tooling.workflow_ownership`) and rerun preview. |
| `CP-CONSUMER-CONFLICT` | A pre-existing file value conflicts with a package-owned unit and no lock history explains it. | Align the conflicting value with the package value (or remove it) so the unit can be adopted, then rerun preview. |

## 2. Apply the reviewed migration

```bash
project-standards init --catalog 5 --migrate --apply
```

Apply rechecks the inspected bytes, materializes package outputs, runs unified verification, publishes `.standards/lock.toml`, and only then removes `.project-standards.yml` and recognized package-specific locks. A stale plan, ambiguity, provider refusal, or verification failure preserves recoverable legacy authority and exits non-zero.

Review the result:

```bash
git status --short
git diff --check
project-standards standards list
project-standards reconcile --check
```

Commit `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, and every reconciled output together.

## 3. Review selectors and package options

Each enabled package has two separate version planes:

- `standards.<id>.version` selects an immutable package payload (`latest` or exact `major.minor`);
- package options such as `contract_version` select supported document/schema behavior inside that payload.

Changing one does not silently change the other. Use `project-standards standards version` for the payload selector, edit only declared package options in `.standards/config.toml`, and preview with `reconcile` before apply.

An exact selector remains pinned. `latest` follows only the compatible default or an explicitly accepted package-major track. Entering or leaving a non-default major requires the matching `--allow-major STANDARD_ID@MAJOR` and a declared migration path.

## 4. Verify provider-backed commands

Under unified authority, validators and authoring commands resolve the selected payload. Read-only providers receive immutable snapshots; authoring providers return typed plans whose writes are performed by the platform executor.

Run the commands for the selected packages, including as applicable:

```bash
project-standards validate
project-standards fix
project-standards spec validate
project-standards spec lint --strict
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
```

An explicit `--config .project-standards.yml` is now a legacy/debug-only path and is rejected under unified authority.

## 5. Re-pin workflows and the tool

Pin reusable workflows and the installed CLI to the same v5 release line. Use `@v5` for compatible updates or `@v5.2.0`/a commit SHA for an immutable pin. Never mix a v5 workflow with a v4 `standards-ref`.

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
