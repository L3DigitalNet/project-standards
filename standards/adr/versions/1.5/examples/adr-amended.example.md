---
schema_version: '1.1'
id: 'adr-0004-homelab-store-platform-backups-on-the-shared-object-store'
title: 'ADR 0004: Store platform database backups on the shared object store'
description: 'Selects the shared object store as the backup destination for platform-operated relational databases, as amended twice since acceptance.'
doc_type: 'adr'
status: 'active'
created: '2026-03-02'
updated: '2026-08-09'
reviewed: '2026-08-09'
owner: 'platform-team'
consumer: 'user'
tags:
  - 'backup'
  - 'storage'
aliases: []
related: []
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted:
    - 'platform-team'
  informed:
    - 'all-engineering'
  amends:
    - 'adr-0003-homelab-operate-one-backup-target-per-service'
  amended_by:
    - 'adr-0009-homelab-replicate-tier-1-backups-offsite'
---

# ADR 0004: Store platform database backups on the shared object store

MADR status: **accepted**.

> **Amended by ADR 0009 (2026-06-18).** Tier-1 platform databases must additionally replicate each completed backup object to the offsite bucket. The destination selected here is unchanged, and it remains the only backup destination for every other governed database.
>
> **Amended 2026-08-09 (2026-Q3 recovery drill, finding R2).** Retention is now stated as an explicit per-tier schedule rather than as "at least thirty days", because the drill found two readings of the original wording. Nothing else in the outcome changes. See [Amendments](#amendments).

## Context and Problem Statement

ADR 0003 decided that each first-party service on the shared homelab application platform operates exactly one backup target. It deliberately left the destination for that target open, reserving it for a later decision.

This decision applies only to backups of platform-operated relational databases—the databases governed by ADR 0001—when the platform itself performs the backup. It does not govern backups taken by a third-party application on its own schedule, filesystem-level snapshots of the hypervisor, workstation backups, or the offsite replication of any of those.

Where should the platform write the backups it takes for governed relational databases?

## Decision Drivers

- One restore procedure for every governed database.
- Storage cost proportional to retained data rather than to provisioned volumes.
- Object immutability windows that survive a compromised platform credential.

## Considered Options

- The shared object store
- Per-host local volumes
- A dedicated backup appliance

## Decision Outcome

Chosen option: **the shared object store**, because it gives one restore procedure across every governed database and supports immutability windows that local volumes cannot.

The platform writes backups of platform-operated relational databases to the shared object store when the platform performs the backup, and retains each backup for at least thirty days.

This decision does not govern application-managed backups, hypervisor snapshots, workstation backups, or offsite replication. Those concerns remain undecided or are governed by a more specific ADR. An out-of-scope backup does not require an exception to this ADR.

### Consequences

- Good, because one restore runbook covers every governed database.
- Good, because immutability windows survive a compromised platform credential.
- Bad, because a shared destination concentrates the blast radius of a store-wide outage.

### Confirmation

Platform deployment review first determines whether the proposed backup is taken by the platform for a governed relational database. In-scope backups are then checked for an object-store destination and for a retention setting matching the schedule below. Out-of-scope backups receive no finding under this ADR.

### Amendments

**Amended 2026-08-09 (2026-Q3 recovery drill, finding R2).** The retention clause in the outcome above is restated as the following per-tier schedule, which is what the platform has enforced since acceptance:

| Tier   | Daily backups retained | Monthly backups retained |
| ------ | ---------------------- | ------------------------ |
| Tier 1 | 35                     | 12                       |
| Tier 2 | 35                     | 3                        |
| Tier 3 | 14                     | 0                        |

The drill found that "at least thirty days" was read by one team as thirty daily objects and by another as a thirty-day floor on the oldest monthly object. The schedule replaces that clause only; the destination, the governed population, and the exclusions are unchanged, and no database moves tier as a result. Lengthening a tier's retention is a reviewed additive change to this table; shortening one or removing a tier is a new decision.

## More Information

Revisit this decision if the shared object store's immutability guarantees change or if a governed database outgrows the retention schedule. ADR 0003 records the one-target-per-service decision this record amends; ADR 0009 records the offsite-replication decision that amends it.
