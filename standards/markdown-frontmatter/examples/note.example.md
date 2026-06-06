---
schema_version: '1.1'
id: 'tailscale-acl-gotcha'
title: 'Tailscale ACL tag ordering gotcha'
description: 'A working note on why a Tailscale ACL rule silently failed until tag order was fixed.'
doc_type: 'note'
status: 'active'
created: '2026-06-02'
updated: '2026-06-02'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - 'tailscale'
  - 'networking'
  - 'gotcha'
aliases: []
related:
  - 'docs/concepts/immutable-infrastructure.md'
source:
  - 'https://tailscale.com/kb/1018/acls'
confidence: 'medium'
visibility: 'internal'
license: null
---

# Tailscale ACL tag ordering gotcha

<!-- General-purpose working note. Captured while debugging an ACL rule. -->

## Notes

- An ACL rule referencing `tag:server` matched nothing until the tag was also declared under `tagOwners`. Tailscale validates `tagOwners` before evaluating `acls`, so an undeclared tag is treated as an empty set rather than an error.
- Fix: declare every tag in `tagOwners` first, then reference it in `acls`.
- Worth promoting to a `concept` or `runbook` if this bites a second time.
