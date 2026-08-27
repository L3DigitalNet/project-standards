---
schema_version: '1.1'
id: 'reference-k7p2vc-control-plane-diagnostic-codes'
title: 'Control-Plane Diagnostic Codes'
description: 'Reference for every CP- diagnostic code the reconcile, init, render, and recovery control plane emits, with its meaning, the condition that raises it, and the remediation.'
doc_type: 'reference'
status: 'active'
created: '2026-08-26'
updated: '2026-08-27'
reviewed: '2026-08-26'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'reference'
  - 'control-plane'
  - 'diagnostics'
aliases: []
related:
  - 'docs/usage.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Control-Plane Diagnostic Codes

Every control-plane finding, refusal, and apply failure carries a stable `CP-` code. The code is the part of the output that does not change between releases: messages are content-safe prose and may be reworded, but the code identifies the condition and is what a runbook, a CI grep, or an issue report should quote. In `--json` mode the code is the `code` field of a finding or of the top-level error object.

The tables below cover the codes emitted by `src/project_standards/control_plane/**` — the vocabulary of `project-standards reconcile`, `init`, `render`, and `standards`, including managed restore and sanctioned recovery. [`tests/test_control_plane_diagnostic_docs.py`](../../tests/test_control_plane_diagnostic_docs.py) derives the code set from that source and fails if this reference and the code disagree in either direction, so a code added upstream cannot ship undocumented.

Severity is not part of the code. Most codes are emitted as errors; `CP-DRIFT` and `CP-MIGRATION-BOUNDED-TAKEOVER` are the warnings an otherwise clean run can carry. Exit status follows the command's own convention documented in [`docs/usage.md`](../usage.md): `1` for drift, findings, an authorization refusal, or a recoverable apply failure, and `2` for an invalid invocation or invalid control authority.

Legacy-migration codes also appear in [`UPGRADING.md`](../../UPGRADING.md) with migration-specific guidance; that section stays the deeper treatment for a V4 preview, and this page is the complete vocabulary.

## Invocation, authority, and state

| Code | Meaning | When it fires | Remediation |
| --- | --- | --- | --- |
| `CP-ARGUMENT` | The invocation is not a valid command line. | Mutually exclusive flags, a flag without its required companion (`--apply` without `--migrate`), or a malformed `--allow-major` value. | Correct the invocation against the command's synopsis and rerun. |
| `CP-CONTROL-STATE` | Unified `.standards/` authority cannot be read or interpreted for this command. | A control file is missing, unparsable, or internally inconsistent when a read-only inspection needs it. | Read the reported detail, restore the named authority from version control, then rerun. Nothing was written. |
| `CP-MISSING-CONFIG` | The user-owned desired configuration is absent. | `.standards/config.toml` does not exist, and no other sanctioned missing-file case applies. | Restore `config.toml`, or run an explicit legacy migration. Desired configuration is never inferred. |
| `CP-INIT-STATE` | `init` cannot interpret the existing control-plane state. | A non-migrating `init` meets state it did not create and cannot safely extend. | Resolve the reported state — usually a partial or foreign `.standards/` — before initializing again. |
| `CP-CATALOG-MAJOR-MISMATCH` | The installed tool's catalog major does not match the configured one. | An apply is requested while `.standards/config.toml` names a catalog major the installed release does not carry. | Install the release matching the configured catalog major, or migrate the repository to the newer major deliberately. |
| `CP-RESOLUTION` | Package selection could not be resolved from the configuration and catalog. | A read-only check hits an unresolvable selector, an absent package version, or an invalid extension reference. | Fix the reported selection in `.standards/config.toml`, or install a release whose catalog carries it. |
| `CP-RESOLVE-MAJOR-AUTH` | A resolved selection would cross a package-major boundary without authorization. | `latest` or an accepted-major track resolves into a new package major that this invocation did not authorize. | Read the target major's adoption guide, then rerun with `--allow-major <standard>@<major>`. |
| `CP-BUSY` | Another process holds the control-plane lock. | A concurrent `reconcile`, `init`, or recovery run owns `.standards/` for the duration of its work. | Wait for the other invocation to finish and retry. Nothing was changed. |
| `CP-RENDER` | The `render` command could not produce content. | The selected package or provider is unavailable, or the provider refused its inputs. | Check the standard id, provider id, and effective configuration; `render` never writes, so no rollback is needed. |
| `CP-DRIFT` | Lock metadata must be refreshed even though no target changes. | A warning on `reconcile --check` when only the central lock is behind — commonly after `fix` edited files whose digests the lock records. | Run `reconcile --apply` to publish the refreshed lock metadata. |
| `CP-REPAIR-REQUIRED` | The control plane is incomplete and recovery was not requested. | `reconcile` finds an incomplete or interrupted-refresh state without `--repair-state`. | Preview the sanctioned recovery with `reconcile --repair-state`, review it, then apply it. |
| `CP-REPAIR-NOT-NEEDED` | Recovery was requested for a healthy control plane. | `--repair-state` is passed while the state is complete. | Drop `--repair-state` and run the ordinary reconciliation. |
| `CP-REPAIR-AUTH` | A recovery write lacks its explicit authorizations. | A recovery apply is attempted without both `--repair-state` and `--apply`. | Rerun with both flags once the previewed recovery is reviewed. |
| `CP-MIGRATION-STATE` | The repository authority is not one complete legacy-migration input. | `init --migrate` meets missing, partial, duplicated, or conflicting legacy and unified state, including a dual authority that is not an exact interrupted-migration prefix. | Read the detail, repair the reported control state without removing either authority, and rerun the preview. Use the documented recovery procedure for an interrupted migration. |

## Planning findings

These are reported by `reconcile` (and by `reconcile --check`) before anything is written. A plan carrying any of them is not applicable, so the apply is refused rather than partially performed.

| Code | Meaning | When it fires | Remediation |
| --- | --- | --- | --- |
| `CP-CONSUMER-CONFLICT` | Pre-existing consumer content differs from the value the selected package owns. | A package would claim a file or a unit inside one that already exists with different content, and no lock history explains the difference. | Set a governing option so the package renders the intended value, align the value with the reported expected value, or remove the consumer value so the package can create it. The finding names the governing options when the package declares any. |
| `CP-MODIFIED-MANAGED` | Managed content diverged from the central lock. | A managed file's bytes or mode, or a managed semantic unit, changed outside reconciliation — or a previously managed unit is missing from its container. | Revert the hand edit, or express the intent through the package option the finding names, then reconcile. Editing generated managed content directly is always drift. |
| `CP-PACKAGE-OVERLAP` | Two selected packages claim the same target or unit. | Overlapping whole-file ownership, overlapping semantic contribution scopes, or a selection that contradicts exclusive lock ownership. | Deselect one of the reported packages, or reconfigure them so their claims are disjoint. |
| `CP-DUPLICATE-IDENTITY` | One whole-file target carries duplicate package ownership identities. | A target's declared owner list repeats an identity. | Correct the duplicated selection; a whole file has exactly one owning package. |
| `CP-SHARED-CONFLICT` | A shared identity resolves inconsistently across its contributors. | Contributors to one shared identity declare incompatible semantic addresses, values, or lifecycle metadata. | Align the contributing packages' options so the shared identity resolves to one address, value, and lifecycle. |
| `CP-ADAPTER-CONFLICT` | One target is claimed through incompatible semantic adapters. | Two declarations disagree on a target's adapter, or the desired adapter disagrees with the locked one. | Correct the package selection or configuration so one adapter governs the target. |
| `CP-ALIAS-CONFLICT` | Two declared targets are the same repository file through a symlink. | A symlink makes distinct declared paths resolve to one file, and the declarations require different content. | Replace the symlink with a real file, or stop declaring both aliases; the finding names the first divergent pair. |
| `CP-LOCK-INCONSISTENT` | The central lock does not describe one exclusive, matching target. | Overlapping locked scopes, a lock record that does not describe one exclusive target, or a locked identity that does not match the current declaration without a migration. | Reconcile from a clean lock: restore `.standards/lock.toml` from version control, or run the documented recovery, then reconcile again. |
| `CP-MALFORMED-CONTAINER` | A target cannot be parsed as the container its adapter declares. | Managed TOML, JSON, or YAML at the target is syntactically invalid. | Repair the file's syntax and rerun the preview. Reconciliation never rewrites an unparsable container. |
| `CP-CREATE-ONLY-ABSENT` | A create-only unit recorded in the lock is gone from the repository. | A scaffold the package creates once was deleted after adoption. | None required: reconciliation records the removal in the lock and never recreates it. Restore the file yourself if it was deleted by mistake. |
| `CP-CREATE-ONLY-STALE` | A create-only unit matches a version other than the selected one. | The scaffold on disk matches a package version that is not the selected one. | Adopt the selected version's scaffold by hand if you want its content; the package will not overwrite consumer state. |
| `CP-UNDECLARED-PACKAGE-CONTENT` | Content exists in a package namespace that no declaration owns. | A file or a non-regular entry appears under `.standards/packages/**` outside the declared set. | Remove the undeclared content, or select the package that declares it. The namespace root must be a regular directory. |
| `CP-DUPLICATE-PACKAGE-LOCK` | A competing lock file sits inside a package namespace. | A `lock.json`, `lock.toml`, or `provenance.lock` is found under a package namespace that does not declare it. | Delete the stray lock artifact; the central lock is the only lock authority. |
| `CP-PAYLOAD-CONTENT` | An installed package payload is invalid. | Payload normalization fails while planning — a defect in the installed distribution, not in the repository. | Reinstall the exact release, and report the failure upstream with the detail message. |
| `CP-PROVIDER-INTEGRITY` | A provider mutated a declared live path during planning. | A provider is observed changing or making unsafe a path it declared, which planning must treat as read-only. | Do not retry blindly: capture the message and report it upstream. The invocation is refused to keep the plan trustworthy. |
| `CP-CATALOG-PRECONDITION` | The committed catalog changed before refresh planning finished. | `.standards/catalog.toml` no longer matches the committed content the refresh was planned against. | Restore or re-review the catalog and rerun the preview. |
| `CP-CONTAINMENT-DESTINATION` | A declared target resolves outside the repository or into protected state. | Traversal cannot be proven to stay inside the repository root, or a link redirects a target into `.git/` or `.standards/` — reported as an escape, a non-directory component, or a link loop. | Replace the offending symlink or path component with a real in-repository path. No write is attempted at an unproven destination. |

## Apply failures

An apply failure names the stage that refused. The executor rechecks every precondition, does not retry automatically, and leaves the central lock replaced last.

| Code | Meaning | When it fires | Remediation |
| --- | --- | --- | --- |
| `CP-STALE-PLAN` | The reviewed plan no longer matches the repository. | A target, the catalog, the central lock, or migration state changed between the preview and the apply. | Rerun the preview, review the new plan, and retry the apply. |
| `CP-PRECONDITION` | A specific precondition failed during publication. | A target, its parent directory, the central lock, or migration authority changed after planning or after staging. | Same as a stale plan: rerun the preview and retry. Concurrent editors and format-on-save are the usual causes. |
| `CP-APPLY-PATH` | A path could not be used safely. | The repository root is unsafe or unopenable, or a target parent escapes the repository, is not a safe directory, or could not be created. | Repair the reported path — usually a symlinked or non-directory parent — and retry. |
| `CP-APPLY-STAGE` | Content could not be staged before publication. | The staged temporary write failed, produced zero bytes, or a catalog refresh target does not share the control-plane filesystem. | Check free space, permissions, and that `.standards/` is not on a separate filesystem, then retry. |
| `CP-APPLY-PUBLISH` | The staged replacement could not be published. | The atomic removal, replacement, namespace prune, control-file write, or lock write failed at the last step. | Inspect the reported path for permissions or filesystem errors, then rerun the preview and apply again. |
| `CP-APPLY-FAILED` | An apply failed with no more specific code. | The generic classification for an apply refusal the executor could not attribute to one stage. | Read the detail, resolve the reported state, rerun the preview, and retry. |
| `CP-VERIFY` | Post-apply verification refused the result. | A published target changed before verification, a verification provider failed or reported the wrong effect, or verification returned an error. | Read the emitted finding: a published-target refusal names the offending target in `path` and its mismatch kind in `locus` (see below). Re-run the read-only preview to see the current state before making further changes; the published bytes are on disk but unverified. |
| `CP-CATALOG-ROLLBACK` | The committed catalog could not be restored after an apply failure. | A catalog refresh failed and rolling `.standards/catalog.toml` back also failed. | Restore `.standards/catalog.toml` from version control before running any further control-plane command. |
| `CP-AUTHORING-PLAN` | An authoring plan is not a complete, unambiguous set of actions. | The plan repeats a target, carries a package refusal, is not whole-file, or a replacement was never staged. | Rebuild the authoring plan; this is an internal-consistency refusal, not a repository condition. |
| `CP-AUTHORING-PUBLISH` | An authoring replacement could not be published. | The authoring removal or replacement failed at the filesystem. | Check the target's permissions and parent directory, then retry. |
| `CP-MIGRATION-REMOVE` | Legacy state could not be retired after a migration. | Removing `.project-standards.yml` or a recognized empty legacy directory failed. | Remove the reported legacy path by hand once the migration is verified. |

### `CP-VERIFY` published-target mismatch kinds

When post-apply verification rejects a published target, the reported finding carries the target path in `path` and one of these kinds in `locus`, repeated in the message. `CP-VERIFY` raised by a verification provider carries that provider's own findings instead.

| Kind | Meaning |
| --- | --- |
| `missing` | The plan requires a file at the path and nothing is there — a target deleted between planning and verification, including one the plan only holds unchanged. |
| `entry-kind` | Something other than a regular file occupies the path (a directory, a symlink, or another entry kind). |
| `content` | The bytes on disk differ from the reviewed plan. The finding publishes the planned and observed content digests; consumer bytes are never included. |
| `mode` | The bytes match but the file mode does not match the planned mode. |
| `removal-present` | The plan asserts the path is absent after apply — a removal, or a create-only unit the consumer deleted — but an entry is present. |

## Managed restore

Emitted by `reconcile --restore-managed <path>`, which restores exactly one exclusively managed whole file and refuses everything else.

| Code | Meaning | When it fires | Remediation |
| --- | --- | --- | --- |
| `CP-RESTORE-AUTHORITY` | The persisted authority is incomplete or disagrees with the preview. | Config, catalog, or lock is missing or not a regular file, or the persisted state no longer matches the reviewed planner inputs. | Restore the complete control-plane authority, then rebuild the preview from the current config, catalog, and lock. |
| `CP-RESTORE-LOCK` | The target has no single authoritative lock entry. | The path is not recorded once in the central lock — typically a pre-adoption file. | Resolve ownership and reconcile first; restore is only for content the lock already proves. |
| `CP-RESTORE-OWNERSHIP` | The target is not exclusively managed whole-file content. | The declaration or lock entry shows partial, shared, consumer-owned, or create-only content. | Use ordinary reconciliation instead. No destructive action is authorized for content the package does not exclusively own. |
| `CP-RESTORE-PATH` | The requested path is not one usable canonical target. | The argument is a glob, absolute, or traversing path; or the parent is absent or unsafe; or the target is neither absent nor a regular file. | Supply one declared repository-relative file path, and create or replace the parent through its owning workflow first. |
| `CP-RESTORE-PLAN` | The restore plan lacks its preview or desired content. | The plan reached apply without the reviewed preview and desired bytes. | Rerun the preview and apply from its output. |
| `CP-RESTORE-APPLY` | The restore write failed. | The staged replacement could not be published, or the plan repeated a target. | Check permissions on the target and its parent, then rerun the preview and retry. |
| `CP-RESTORE-VERIFY` | The restored target changed before verification. | Another writer touched the file between publication and verification. | Rerun the preview to see the current state before retrying. |

## Sanctioned recovery

Emitted by `reconcile --repair-state`, which reconstructs a missing catalog or lock from retained evidence and never infers desired configuration.

| Code | Meaning | When it fires | Remediation |
| --- | --- | --- | --- |
| `CP-RECOVERY-INCOMPLETE` | The control plane is not in one sanctioned recovery case. | Several authorities are missing at once, or the incomplete shape is unsupported. | Restore the incomplete authorities from version control; recovery reconstructs one missing file, not an arbitrary state. |
| `CP-RECOVERY-UNSAFE` | Control-plane files are not safe regular files. | `.standards/` or a required entry is a symlink, a directory where a file is expected, or otherwise not inspectable safely — including an unsafe catalog-refresh backup. | Restore a regular `.standards/` directory and regular control files from version control. |
| `CP-RECOVERY-AUTH` | A missing lock cannot be reconstructed from current evidence. | Lock recovery lacks the candidate authorization the evidence requires. | Restore `.standards/lock.toml`, or supply the required candidate authorization. |
| `CP-RECOVERY-DISTRIBUTION` | The installed distribution cannot reproduce the missing catalog. | The installed release does not carry the recorded catalog, or its catalog does not match the retained lineage. | Install the tool release matching the recorded catalog, or restore the catalog snapshot from version control. |
| `CP-RECOVERY-CATALOG-REFRESH` | Catalog-refresh recovery evidence is invalid or contradictory. | The retained refresh evidence is malformed, disagrees on catalog major, or neither the live nor the backed-up catalog matches the lock lineage. | Restore matching catalog and lock authorities from version control, then reconcile. |
| `CP-RECOVERY-APPLY` | The recovery write failed. | Publishing the reconstructed authority failed at the filesystem. | Inspect `.standards/` permissions and retry the previewed recovery. |

## Legacy migration preview

Emitted by `init --migrate` while previewing a V4 repository. [`UPGRADING.md`](../../UPGRADING.md) carries the extended guidance for these findings.

| Code | Meaning | When it fires | Remediation |
| --- | --- | --- | --- |
| `CP-MIGRATION-PLATFORM-VERSION` | The legacy platform version is not recognized. | `standards_version` in `.project-standards.yml` is absent or is not the recognized `"v3"` or `"v4"` tag. | Normalize the value to `standards_version: "v4"` before previewing; a full release string such as `"v4.3.0"` is the same wire format. |
| `CP-MIGRATION-CONFIG` | Migrated options violate the selected payload schema. | A migration provider mapped legacy settings to options the package does not accept. | Correct the legacy values or the provider mapping. This blocks apply but does not suppress other findings. |
| `CP-MIGRATION-SETTING-MISSING` | A provider claimed a legacy setting that is not present. | The provider declares a setting the legacy configuration does not contain. | Update the provider declaration or the legacy configuration. |
| `CP-MIGRATION-SETTING-OVERLAP` | Providers claimed overlapping legacy settings. | Two selected packages claim the same legacy key. | Use the reported package identities to make their setting claims disjoint. |
| `CP-MIGRATION-UNCLAIMED-SETTING` | A legacy setting is represented by no selected package. | `.project-standards.yml` carries a key no selected migration provider recognizes. | Remove the unknown key, or select the package that migrates it. |
| `CP-MIGRATION-CLAIM-OVERLAP` | Several packages claimed the same legacy object. | Two migration providers claim one legacy file or unit. | Use the reported identities to make the package claims disjoint. |
| `CP-MIGRATION-UNCLAIMED-ARTIFACT` | Recognized legacy content has no ownership disposition. | A known legacy artifact is neither claimed nor preserved by the selected providers. | Make the selected migration provider claim or preserve the artifact. |
| `CP-MIGRATION-LEGACY-DIGEST` | A recognized file's bytes match no shipped package history. | The legacy file was customized, so migration cannot prove what it is taking over. | Restore the released bytes, or declare the documented `"consumer-owned"` ownership option so migration preserves the file. |
| `CP-MIGRATION-LEGACY-FORMAT` | Legacy semantic content is invalid or ambiguous. | The legacy YAML or TOML does not parse as a declared canonical historical shape. | Restore a declared canonical historical shape and rerun the preview. |
| `CP-MIGRATION-LEGACY-BLOCK` | A bounded legacy block is ambiguous. | Markers are partial, duplicated, or reversed. | Restore a known managed block, or remove the partial markers, then rerun the preview. |
| `CP-MIGRATION-BOUNDED-ORPHAN` | Bounded legacy content has no safe replacement target. | A managed block exists with nothing the package can replace it with. | Add a replacement that preserves the content outside the managed block. |
| `CP-MIGRATION-BOUNDED-TAKEOVER` | Consumer content at a bounded target is preserved (warning). | The package takes over only its managed block or properties inside a file that also carries consumer content. | No action needed to apply. After apply, review the preserved file and delete superseded copy-adopt boilerplate. |
| `CP-MIGRATION-HISTORICAL-UNIT` | A declared historical semantic unit cannot be bound. | The unit is absent or malformed, or historical units lack the exact whole-file signature they require. | Correct the adapter and scope the migration provider declares, or bind the units to known whole-file history. |
| `CP-MIGRATION-OWNER-RESOLUTION` | A consumer-owned preservation claim is incomplete. | Owner-resolution evidence is used for recognized package history, or the relinquishment is not fully authorized. | Supply the literal `consumer-owned` value through the documented option, and omit owner intent from claims for recognized history. |
| `CP-MIGRATION-VALIDATE` | Selected-package validation could not run during migration. | A provider input needed for validation is missing or invalid. | Resolve the reported provider input, then rerun the preview. |
