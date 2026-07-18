---
schema_version: '1.1'
id: research-byzynj-consumer-owned-workflow-migration-safety
title: Consumer-Owned Whole-File Preservation During Legacy Migration
description: Research on safely preserving an unrecognized consumer-owned workflow while migrating Python Tooling into the v5 control plane.
doc_type: research
status: active
created: 2026-07-12
updated: 2026-07-12
reviewed: 2026-07-12
owner: project-standards
consumer: agent
tags:
  - v5
  - migration
  - ownership
  - python-tooling
  - workflow
aliases:
  - consumer-owned workflow migration
  - unknown legacy whole-file preservation
related:
  - docs/specs/2026-07-10-consumer-standards-control-plane-spec.md
  - docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md
  - docs/adr/adr-0023-unified-consumer-standards-control-plane.md
source:
  - https://developer.hashicorp.com/terraform/language/block/removed
  - https://docs.hashicorp.com/terraform/language/meta-arguments/lifecycle
  - https://developer.hashicorp.com/terraform/language/import/single-resource
  - https://kubernetes.io/docs/reference/using-api/server-side-apply/
  - https://helm.sh/docs/howto/charts_tips_and_tricks/
  - https://helm.sh/docs/helm/helm_install/
  - https://helm.sh/docs/helm/helm_upgrade/
  - https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-baseline-on-migrate-setting
confidence: high
visibility: public
license: Apache-2.0
---

# Consumer-Owned Whole-File Preservation During Legacy Migration

## Summary

The migration failure is not a coverage.py problem or a Python Tooling provider bug. It is an ownership-transition gap in the generic migration engine. The optimized root `.github/workflows/check.yml` has digest `sha256:9f4f90364b85af187ce7430a18d5e189389e5884157d74e8defc4d468cb13bdc`, while Python Tooling declares only the frozen V1 workflow digest as known. The engine reports `CP-MIGRATION-LEGACY-DIGEST` before provider classification and later rejects any claim whose observed signature is not known. A `consumer-owned`/`preserve` provider claim therefore cannot make the migration applicable under the current contract.

The strongest external precedent is an explicit **relinquish ownership without destroying or changing the object** operation:

- Terraform's configuration-driven `removed` block with `destroy = false` removes an object from state while leaving it intact so management can pass to another tool or team. [Terraform removed block](https://developer.hashicorp.com/terraform/language/block/removed)
- Kubernetes Server-Side Apply lets a manager give up a field by omitting it from the manager's applied model; the live value remains unchanged and the manager's ownership entry is removed. Conflicting takeover remains an explicit force operation. [Kubernetes Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/)
- Helm's `helm.sh/resource-policy: keep` prevents deletion but deliberately orphans the resource, with documented consequences for later replacement. [Helm chart guidance](https://helm.sh/docs/howto/charts_tips_and_tricks/)

For a clean general solution, add a narrow engine rule for an **explicit consumer-owned whole-file preserve claim**. It should accept the exact observed digest without requiring that digest to be package-shipped, but only when the selected payload omits every managed contribution for that target. Managed adoption, replacement, removal, bounded-block migration, and package-lock import must continue requiring declared known digests.

This is not implementable as a design-only clarification. It changes the v5 migration contract and requires amendments to ADR 0023, SPEC-CP01, and SPEC-BA02 before implementation planning resumes.

## Repository diagnosis

The current sequence is:

1. The engine reads every target named by the migration's declared legacy signatures.
2. It computes the observed digest and marks the signature `known` only when the digest appears in `known_content_digests`.
3. It immediately emits `CP-MIGRATION-LEGACY-DIGEST` for an unknown digest.
4. The provider receives the signature snapshot and can return a claim.
5. Claim validation independently requires the observed signature to be known.

The relevant implementation is [`migration.py`](../../src/project_standards/control_plane/migration.py). Python Tooling's current signature declaration is [`payload.toml`](../../standards/python-tooling/versions/1.1/payload.toml), and the ownership contract is recorded in [SPEC-CP01](../specs/2026-07-10-consumer-standards-control-plane-spec.md) and [ADR 0023](../adr/adr-0023-unified-consumer-standards-control-plane.md).

This ordering protects managed adoption: modified bytes cannot be silently treated as package-owned and replaced. It also means ownership intent cannot currently resolve an unknown whole file even when the selected package explicitly promises not to render, lock, update, disable, or remove it.

### Governing local contracts

The existing durable contracts are stricter than the round-4 design audit assumed:

- [ADR 0023](../adr/adr-0023-unified-consumer-standards-control-plane.md) says exact known whole-file matches receive replacement actions, while modified or ambiguous matches block.
- [SPEC-BA02](../specs/2026-07-10-standard-bundle-authoring-v2-spec.md) defines `known_content_digests` as bytes previously shipped by the package and requires unknown legacy content to remain ambiguous until owner resolution.
- [SPEC-CP01](../specs/2026-07-10-consumer-standards-control-plane-spec.md) requires preservation of consumer-owned content, explicit preview/apply, a stale-plan boundary, and no writes when migration remains ambiguous.

Adding the optimized root digest to Python Tooling's known package signatures would make the immediate test pass, but it would describe repository-specific consumer bytes as though the package had shipped them. That is inconsistent with the current BA02 meaning and does not fulfill the design's general promise to consumers with project-specific workflows.

## External ownership models

### Relinquish and preserve

Terraform separates state ownership from object existence. A `removed` block with `destroy = false` records the management handoff in configuration, produces a reviewable plan, and leaves the infrastructure object intact. Terraform explicitly describes this as handing management to another tool or team. [Terraform removed block](https://developer.hashicorp.com/terraform/language/block/removed)

Kubernetes Server-Side Apply uses the same conceptual boundary at field granularity. Conflicts prevent accidental overwrite. A manager that no longer cares about a field removes it from its applied model, leaving the live value unchanged and giving up its ownership claim. Overwrite-and-takeover requires an explicit force operation. [Kubernetes Server-Side Apply conflicts](https://kubernetes.io/docs/reference/using-api/server-side-apply/#conflicts)

Helm's `resource-policy: keep` shows the lifecycle consequence of relinquishment: preservation means the resource becomes orphaned and Helm no longer manages it. The documentation warns that later replacement can conflict with the retained object. [Helm keep policy](https://helm.sh/docs/howto/charts_tips_and_tricks/#tell-helm-not-to-uninstall-a-resource)

Applied here, `workflow_ownership = "consumer-owned"` should mean exactly that: Python Tooling does not trust or adopt the workflow's content, does not put it in package state, and does not mutate or remove it. The migration plan records the handoff and the observed digest only to make preview/apply stale-safe.

### Share selected fields

Terraform's `ignore_changes` lets Terraform continue managing a resource while ignoring selected attributes that another process changes. Terraform may still create and destroy the object. [Terraform lifecycle reference](https://docs.hashicorp.com/terraform/language/meta-arguments/lifecycle#ignore_changes)

This is not the right model for the optimized workflow. Python Tooling cannot safely divide a whole YAML workflow into a managed lifecycle shell and consumer-owned command details under its current whole-file adapter. Treating the entire file as ignored while retaining create/delete authority would also contradict the design's consumer-owned lifecycle promise.

### Take ownership or import

Terraform import attaches an existing object to Terraform state and requires matching configuration so subsequent plans do not unexpectedly change it. [Terraform import](https://developer.hashicorp.com/terraform/language/import/single-resource)

Helm exposes the inverse operation explicitly: `--take-ownership` ignores existing Helm-annotation checks and takes ownership of existing resources. [Helm install](https://helm.sh/docs/helm/helm_install/) and [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)

These are appropriate precedents for `workflow_ownership = "managed"`, not `consumer-owned`. Importing or force-taking the optimized workflow would require Python Tooling to reproduce and govern repository-specific commands, which the approved design rejects.

### Automatic baseline acknowledgement

Flyway can automatically baseline a non-empty schema when no history table exists, but the option defaults to false and its documentation warns that enabling it removes a safety net against migrating the wrong database. [Flyway `baselineOnMigrate`](https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-baseline-on-migrate-setting)

The lesson is not to forbid explicit owner resolution. It is to prevent broad or default acknowledgement. A consumer-owned preserve path should require a non-default, target-specific package option, show the preserved path and observed digest in preview, and remain bound to the migration's stale-plan fingerprint.

## Options

| Option | Safety | Generality | Contract impact | Debt assessment |
| --- | --- | --- | --- | --- |
| Register the optimized root digest as known package history | Strong exact-byte gate | Root-only | Small BA02 semantic exception | Tactical but bespoke; mislabels consumer bytes as package-shipped |
| Accept explicit consumer-owned whole-file preserve claims | Strong when constrained as below | General | Amend ADR 0023, CP01, BA02, engine, provider, and tests | Best long-term fit; one reusable ownership primitive |
| Require an owner-supplied expected digest in config | Strong and explicit | General | New option plus the same engine changes | Redundant with preview digest and stale-plan binding; burdens consumers |
| Remove the workflow before migration and restore it afterward | End state can match | Root-only | No engine change | Weak migration evidence and failure boundary; contradicts preserve-through-migration wording |
| Teach Python Tooling to render the optimized workflow | Managed exact output | Not general | Large package-specific workflow surface | Overfits the meta-repo and regresses the optimization boundary |
| Force adoption/takeover | Destructive unless bytes match generated output | General mechanism, wrong intent | Existing managed path | Reject; conflicts with explicit consumer ownership |

## Recommended engine contract

Add a generic owner-resolution rule with all of these constraints:

1. The legacy signature must be `whole-file`. Unknown bounded blocks remain ambiguous because preserving one unknown block inside a shared file is a semantic-composition problem, not whole-file relinquishment.
2. The package option selecting consumer ownership must be explicit in raw migration input. A schema default is insufficient owner authorization.
3. The selected payload must statically bind a canonical `consumer_owned_intent_pointer` to one single-target whole-file legacy signature. The migration provider must return `ownership = "consumer-owned"`, `disposition = "preserve"`, the exact observed target and digest, and an `intent_pointer` that echoes the declaration and that it also reports as a recognized setting. The engine must verify declaration/claim/signature/target equality and that the raw pointed-to value is the literal string `consumer-owned` before defaults.
4. The selected payload must materialize no artifact or contribution for that target under the resolved options. This prevents a preserve claim from coexisting with managed output.
5. The engine must emit no create, update, remove, adopted lock unit, or package-owned digest for the target.
6. Preview must expose the preserved target, observed digest, and reason. Apply must reject any byte, type, path, or symlink change since preview through the existing stale-plan/content-fingerprint boundary.
7. A known digest remains mandatory for `managed/adopt`, `managed/remove`, `shared/adopt`, bounded-block transitions, and package-lock import.
8. Every observed unknown signature retains the ordinary digest finding unless a fully valid owner-resolution claim clears that exact observation. Omitted claims, omitted ownership intent, invalid or duplicate pointer bindings, provider-selected different targets, unsupported ownership values, missing targets, and unknown managed bytes continue to fail closed.
9. Disable, re-enable, refresh, and fixed-point reconciliation must leave the consumer-owned file byte-identical and absent from the central package lock.

This makes exact signature recognition an ownership proof only where the package will claim or mutate content. An explicit consumer-owned preserve claim proves the opposite: the package declines ownership and only binds the reviewed migration plan to the observed bytes.

## Required design and test amendments

Before planning implementation:

- Amend ADR 0023 to distinguish exact-digest managed transitions from explicit consumer-owned whole-file relinquishment.
- Amend CP01 migration evidence, claim validation, edge cases, and acceptance tests for the new owner-resolution path.
- Amend BA02's legacy-signature semantics so an eligible single-target whole-file signature statically binds its owner-intent pointer and unknown bytes may be preserved only by the constrained matching claim; retain the current bounded-block and managed-content rules.
- Revise the Python Tooling design to depend on that generic engine contract instead of registering a repository-specific workflow digest.
- Re-audit the amended durable contracts and design together because this is a platform behavior change, not a Python Tooling-only correction.

Minimum tests should prove:

- unknown whole-file plus explicit consumer-owned preserve succeeds without a write or lock claim;
- a provider cannot use one recognized ownership pointer to relinquish a different target, and malformed or duplicate static bindings fail authoring validation;
- an unknown whole-file observation with no provider claim retains `CP-MIGRATION-LEGACY-DIGEST`;
- the same bytes under managed ownership fail with `CP-MIGRATION-LEGACY-DIGEST`;
- unknown bounded-block content still fails;
- a preserve claim for a target that also materializes a contribution fails;
- preview/apply byte changes fail stale-plan validation;
- the optimized root workflow remains byte-identical through migration, reconcile, disable, and re-enable;
- source and installed-wheel providers produce identical claims and plans.

## Recommendation

Choose the generic explicit consumer-owned whole-file preserve path. It best matches the approved `workflow_ownership` semantics, mature ownership-transfer models, and the user's goal of avoiding release-time debt. Do not add the root workflow digest to package history unless release timing forces a consciously temporary exception with a recorded follow-up; that shortcut solves one checkout while leaving the advertised general option false.

The cost is a focused control-plane contract amendment and additional engine tests before implementation planning. The benefit is one reusable, fail-closed primitive for future consumer-owned whole-file migrations without teaching packages to trust or reproduce consumer content.

The owner accepted this recommendation on 2026-07-12. Combined contract audit round 1 then found that a flat provider-reported `recognized_settings` list could not prove which target a pointer authorized. ADR 0023, SPEC-CP01 rev 0.10, SPEC-BA02 rev 0.11, and the Python Tooling design now add a static single-target signature binding and explicit hold-and-emit-unless-cleared behavior. Convergence audit is the next gate.

## References

- [Terraform removed block](https://developer.hashicorp.com/terraform/language/block/removed) — configuration-driven handoff without destroying the object.
- [Terraform lifecycle rules](https://docs.hashicorp.com/terraform/language/meta-arguments/lifecycle) — shared management through selected ignored attributes.
- [Terraform import](https://developer.hashicorp.com/terraform/language/import/single-resource) — explicit adoption of an existing object into managed state.
- [Kubernetes Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/) — conflict detection, force takeover, shared ownership, and relinquishment.
- [Helm chart tips](https://helm.sh/docs/howto/charts_tips_and_tricks/) — keep policy and orphaned-resource consequences.
- [Helm install](https://helm.sh/docs/helm/helm_install/) and [upgrade](https://helm.sh/docs/helm/helm_upgrade/) — explicit ownership takeover.
- [Flyway baseline-on-migrate](https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-baseline-on-migrate-setting) — convenience versus safety-net tradeoff for automatic acknowledgement.
