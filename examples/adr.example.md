---
schema_version: '1.1'
id: 'adr-0001-use-postgresql-for-persistent-storage'
title: 'ADR 0001: Use PostgreSQL for persistent storage'
description: 'Records the decision to standardise on PostgreSQL 16 as the primary relational datastore.'
doc_type: 'adr'
status: 'active'
created: '2026-01-15'
updated: '2026-05-30'
reviewed: '2026-05-30'
owner: 'platform-team'
consumer: 'user'
tags:
  - database
  - storage
aliases:
  - postgres-decision
related:
  - 'immutable-infrastructure'
source:
  - 'https://www.postgresql.org/docs/16/'
confidence: 'high'
visibility: 'internal'
license: null
supersedes: []
superseded_by: null
project:
  decision_makers:
    - chris
  consulted:
    - platform-team
  informed:
    - all-engineering
---

# ADR 0001: Use PostgreSQL for persistent storage

MADR status: **accepted**.

## Context and Problem Statement

Services need a relational data store with ACID transactions, JSON columns, and full-text search. Which engine should be the default for all services that require persistent structured data?

## Decision Drivers

- Operational experience already on the team.
- Strength of the extension ecosystem (vector search, time-series).
- Maturity of JSON/JSONB support for hybrid relational/document workloads.
- Support for concurrent writers.

## Considered Options

- PostgreSQL 16
- MySQL 8
- SQLite

## Decision Outcome

Chosen option: **PostgreSQL 16**, because it meets every decision driver — the team has the most operational experience with it, its extension ecosystem (`pgvector`, `TimescaleDB`) is the strongest, and its JSON/JSONB support is the most mature of the options.

### Consequences

- Good, because team expertise reduces operational overhead.
- Good, because `pgvector`/`TimescaleDB` are available without adding another datastore.
- Good, because JSONB avoids a separate document store for hybrid workloads.
- Bad, because it is one more managed service to operate (backup, PITR, failover).
- Neutral, because services that only need key-value storage carry a full relational engine.

### Confirmation

New service specs are reviewed against this ADR; a service introducing a different relational engine must supersede this ADR or document a scoped exception.

## Pros and Cons of the Options

### PostgreSQL 16

- Good, because of deep team experience and a strong extension ecosystem.
- Good, because JSONB covers hybrid workloads.
- Bad, because operating it (HA, backups) is non-trivial.

### MySQL 8

- Good, because it is a capable, widely-deployed relational engine.
- Bad, because the team has less operational experience with it.
- Bad, because its extension ecosystem is weaker for the anticipated workloads.

### SQLite

- Good, because it is zero-ops and file-based.
- Bad, because the single-writer limitation is a non-starter for concurrent services.

## More Information

Revisit if a service emerges whose scale or workload PostgreSQL cannot serve economically. See the [PostgreSQL 16 documentation](https://www.postgresql.org/docs/16/).
