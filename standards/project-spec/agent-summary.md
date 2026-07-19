# Project Specification family: Agent Summary

Current authority is the Catalog 5 consumer payload [`project-spec@1.2`](versions/1.2/agent-summary.md). Its [versioned standard](versions/1.2/README.md) wins over this mutable navigation summary.

- Choose the smallest adequate Light, Standard, or Full profile. Upgrades add missing canonical structure without renumbering sections or rewriting authored prose.
- Keep requirements atomic and testable. Declare spec-local IDs in Appendix A and list cited external namespaces in `reference_prefixes`.
- Maintain goal-to-requirement-to-test traceability and satisfy the status-aware Definition-of-Done contract before approval.
- `validate`, `lint`, `extract`, and `next` are read-only. `new --stdout` and `upgrade --stdout` are previews; file-producing operations return typed plans for the platform executor.
- The package manages `.github/workflows/validate-specs.yml`; consumer-authored specification documents remain consumer-owned.
- Under unified authority, bare commands resolve the selected package through `.standards/`; an explicit `--config` is legacy/debug input and cannot override it.

See the [current adoption guide](adopt.md) for package options, authoring, CI, migration, and verification.
