---
schema_version: '1.1'
id: 'immutable-infrastructure'
title: 'Immutable Infrastructure'
description: 'Servers and containers are replaced wholesale on every change rather than modified in place.'
doc_type: 'concept'
status: 'active'
created: '2026-06-02'
updated: '2026-06-02'
reviewed: null
owner: 'platform-team'
consumer: 'mix'
tags:
  - infrastructure
  - deployment
aliases:
  - immutable-infra
related:
  - 'docs/decisions/adr-0001-homelab-use-postgresql-for-persistent-storage.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Immutable Infrastructure

## Summary

Servers and containers are never modified after deployment — they are replaced entirely.

## Context

Traditional "mutable" infrastructure accumulates configuration drift over time: manual fixes, one-off package installs, and undocumented changes that are impossible to reproduce. Immutable infrastructure eliminates this class of problem by treating every change as a fresh deployment.

## Core Idea

Every artifact — container image, VM snapshot, or disk image — is built once from a declarative source (Dockerfile, Packer template, NixOS config). Deployments swap the artifact; they never `ssh` in and patch the running instance.

## Implications

- Rollback is trivially safe: re-deploy the previous artifact.
- The build pipeline becomes the audit log.
- Secrets must be injected at runtime (env vars, vault agent) rather than baked into the image.
- Stateful data must be separated from the compute layer (external volumes, managed databases).

## Open Questions

- How do we handle services that need local state (e.g. write-ahead logs)?
- Applies to LXC containers on Proxmox: use snapshot + restore instead of in-place upgrades.
