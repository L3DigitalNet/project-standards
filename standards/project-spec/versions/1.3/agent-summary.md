# Project Specification 1.3 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version `1.3`; independent document `contract_version` `1.1`; consumer availability.
- Enable with `project-standards standards enable project-spec --version 1.3`, review with `project-standards reconcile`, and apply with `project-standards reconcile --apply`.
- Closed options in `.standards/config.toml`: `contract_version`, `workflow_mode`, `workflow_ownership`, `include_patterns`, `reference_prefixes`, `default_profile`, and `ci`.
- Light, Standard, and Full share canonical section numbers and typed IDs. Upgrades add missing structure without renumbering existing sections or rewriting authored prose.
- Keep requirements atomic and testable. Declare spec-local IDs in Appendix A; list cited external namespaces in `reference_prefixes`.
- Selected-mode CLI paths must be consumer-root-relative and cannot contain traversal or symlinked parents or leaves.
- `validate`, `lint`, `extract`, and `next` are read-only. `new --stdout` and `upgrade --stdout` are read-only previews. File-producing authoring operations return typed plans for the platform executor.
- With `workflow_ownership = "managed"`, the package manages `.github/workflows/validate-specs.yml`; its jobs use bare spec commands and defer authority resolution to the CLI. Consumer-authored specification documents remain consumer-owned.
- Automatic migration maps specification settings semantically and adopts only the exact released caller. A customized legacy caller requires explicit `workflow_ownership: "consumer-owned"` intent; other modified or unclaimed state blocks apply.
- Disable plus reconcile removes managed workflow ownership without deleting authored specifications.

Use [adopt.md](adopt.md) for package-specific configuration, authoring, CI, migration, verification, and disable behavior.
