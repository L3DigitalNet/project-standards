---
schema_version: '1.1'
id: 'adr-0001-homelab-use-postgresql-for-platform-relational-databases'
title: 'ADR 0001: Use PostgreSQL for platform relational databases'
description: 'Selects PostgreSQL 16 for bounded first-party platform workloads that need a networked relational database.'
doc_type: 'adr'
status: 'active'
created: '2026-01-15'
updated: '2026-08-03'
reviewed: '2026-08-03'
owner: 'platform-team'
consumer: 'user'
tags:
  - 'database'
  - 'storage'
aliases:
  - 'postgres-decision'
related: []
supersedes: []
superseded_by: null
source:
  - 'https://www.postgresql.org/docs/16/'
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
---

# ADR 0001: Use PostgreSQL for platform relational databases

MADR status: **accepted**.

## Context and Problem Statement

First-party services deployed on the shared homelab application platform sometimes require a networked, multi-user relational datastore. Operating a different relational engine for each such service would multiply backup, monitoring, upgrade, and recovery procedures.

This decision applies only to first-party, centrally operated services on that platform when they need a primary networked relational database. It does not govern embedded or local-only state, caches, queues, search indexes, analytical stores, third-party applications whose datastore is prescribed upstream, or workloads governed by a more specific ADR.

Which relational database should be the default within that boundary?

## Decision Drivers

- Operational experience already on the team.
- JSON and full-text capabilities for anticipated platform workloads.
- Support for concurrent writers and reliable backup and recovery.
- A mature extension ecosystem.

## Considered Options

- PostgreSQL 16
- MySQL 8
- Operate no platform default and decide separately for every in-scope service

## Decision Outcome

Chosen option: **PostgreSQL 16**, because it satisfies the identified transactional and operational requirements while matching existing team experience.

PostgreSQL 16 is the default primary relational database for first-party, centrally operated services deployed on the shared homelab application platform when they require a networked, multi-user relational datastore and no more specific ADR governs the workload.

This decision does not govern embedded or local-only state, non-relational stores such as caches, queues, search indexes, and analytical stores, third-party applications whose datastore is prescribed upstream, or workloads governed by a more specific ADR. An out-of-scope workload does not require an exception to this ADR. An in-scope service proposing another relational engine requires a separate service-scoped decision record.

### Consequences

- Good, because team expertise reduces operational overhead for the governed workloads.
- Good, because one default concentrates backup, monitoring, and recovery practice.
- Bad, because operating PostgreSQL remains non-trivial.
- Neutral, because out-of-scope persistence choices remain unaffected.

### Confirmation

Service design review first determines whether the proposed datastore falls within the governed population. In-scope services are then checked for use of PostgreSQL 16 or for a related service-scoped ADR documenting a different decision. Out-of-scope persistence mechanisms receive no finding under this ADR.

## Pros and Cons of the Options

### PostgreSQL 16

- Good, because of deep team experience and a strong extension ecosystem.
- Good, because JSONB and full-text search cover anticipated platform workloads.
- Bad, because high availability and recovery require deliberate operations.

### MySQL 8

- Good, because it is capable and widely deployed.
- Bad, because the team has less operational experience with it.

### Operate no platform default

- Good, because every service could optimize independently.
- Bad, because each decision would duplicate evaluation and operational practice.

## More Information

Revisit this decision if the shared platform changes materially or an in-scope workload cannot be served economically by PostgreSQL. See the [PostgreSQL 16 documentation](https://www.postgresql.org/docs/16/).
