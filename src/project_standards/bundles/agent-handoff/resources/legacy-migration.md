# Legacy Handoff Migration

Migration is repository-local, read-only until the owner reviews a plan, and guided by an agent rather than a deterministic converter.

## Procedure

1. Run the package's `legacy-report` against the target repository only.
2. Inventory recognized and unclassified evidence without reading home-directory or sibling-repository state.
3. Reconcile useful facts into `docs/STATUS.md`, `docs/TODO.md`, and the lifetime-specific files under `docs/handoff/`.
4. Preserve ambiguous or conflicting facts for owner review. Do not invent migration state, a quarantine tree, or a conflict ledger.
5. Adopt the explicit manual or automatic v1 profile and review every proposed managed integration.
6. Validate the complete v1 layout and inspect the repository diff.
7. Delete obsolete repo-local legacy artifacts only after useful content is preserved and validation passes.

## Known legacy families

Older repositories may contain root `STATUS.md` or `TODO.md`, a monolithic handoff document, duplicated Claude/Codex hook copies, old repo-local skill identities, or references to a global installer. These are detection evidence only; none implies a safe mechanical transform.

The pinned evidence repository is MIT-licensed, `Copyright (c) 2026 Chris Purcell`. This v1 resource is a fresh rewrite. Any future copied or substantially derived legacy content must retain the legacy MIT copyright and permission notice; the `agent-handoff` package itself inherits the project-standards repository license and ships no nested license.
