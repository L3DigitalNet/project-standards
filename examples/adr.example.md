---
schema_version: "1.0"
id: "adr-0001-use-postgresql-for-persistent-storage"
title: "ADR 0001: Use PostgreSQL for persistent storage"
description: "Records the decision to standardise on PostgreSQL 16 as the primary relational datastore."
doc_type: "adr"
status: "active"
created: "2026-01-15"
updated: "2026-05-30"
reviewed: "2026-05-30"
owner: "platform-team"
tags:
  - database
  - storage
aliases:
  - postgres-decision
related:
  - "immutable-infrastructure"
source:
  - "https://www.postgresql.org/docs/16/"
confidence: "high"
visibility: "internal"
license: null
supersedes: []
superseded_by: null
---

# ADR 0001: Use PostgreSQL for persistent storage

## Status

Active.

## Context

The application requires a relational data store with support for ACID transactions, JSON
columns, and full-text search. Three options were evaluated: PostgreSQL, MySQL 8, and SQLite.

SQLite was ruled out early: the single-writer limitation is a non-starter for concurrent
services. MySQL 8 is a viable choice, but the team has significantly more operational experience
with PostgreSQL, its extension ecosystem (`pgvector`, `TimescaleDB`) is stronger, and its JSON
support is more mature.

## Decision

Use PostgreSQL 16 as the primary relational datastore for all services that require persistent
structured data.

## Consequences

- Team expertise reduces operational overhead.
- `pgvector` and `TimescaleDB` extensions are available if needed.
- Strong JSON/JSONB support avoids a separate document store for hybrid workloads.
- One more managed service to operate (backup, PITR, failover).
- Services that only need key-value storage carry the overhead of a full relational engine.

## Alternatives Considered

- **MySQL 8** — viable, but less team experience and a weaker extension ecosystem.
- **SQLite** — rejected; single-writer limitation unsuitable for concurrent services.

## References

- [PostgreSQL 16 documentation](https://www.postgresql.org/docs/16/)
