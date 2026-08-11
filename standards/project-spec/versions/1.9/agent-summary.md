# Project Specification 1.9 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version `1.9`; independent document `contract_version` `1.1`; consumer availability.
- Enable with `project-standards standards enable project-spec --version 1.9`, review with `project-standards reconcile`, and apply with `project-standards reconcile --apply`.
- Closed options in `.standards/config.toml`: `contract_version`, `workflow_mode`, `workflow_ownership`, `include_patterns`, `reference_prefixes`, `default_profile`, and `ci`.
- Light, Standard, and Full share canonical section numbers and typed IDs. Upgrades add missing structure without renumbering existing sections or rewriting authored prose.
- Keep requirements atomic and testable. Declare spec-local IDs in Appendix A; list cited external namespaces in `reference_prefixes`.
- Selected-mode CLI paths must be consumer-root-relative and cannot contain traversal or symlinked parents or leaves.
- `validate`, `lint`, `extract`, and `next` are read-only. `new --stdout` and `upgrade --stdout` are read-only previews. File-producing authoring operations return typed plans for the platform executor.
- Line-bearing `validate` and `lint` findings use absolute, one-based physical file lines in human, JSON, and selected-provider output; line-less findings remain `null`.
- `SL-BOILERPLATE` requires exact selected-profile Lifecycle, Quality, and Appendix A/B/D surfaces. `SL-REQUIREMENT-PHRASING` requires every `FR-`, `NFR-`, `IR-`, and `DR-` Requirement cell to start with `The system shall`.
- Ordinary lint warns and exits `0`; strict lint exits `1`. Clean human output names `shared-boilerplate` and `mandatory-phrasing`, while JSON adds the same names in `checks`.
- Repair exact conformance without changing requirement meaning, rationale, acceptance criteria, or priority. Semantic review remains required after the mechanical checks pass.
- With `workflow_ownership = "managed"`, the package manages `.github/workflows/validate-specs.yml`; its jobs use bare spec commands and defer authority resolution to the CLI. Consumer-authored specification documents remain consumer-owned.
- `runner_labels` selects the runner the managed caller requests. It renders a `runner-labels` JSON-array string into the caller's `with:` block and is omitted entirely when empty, which is the default and the byte-identical render. The input is reachable only over `workflow_call`; a direct `push` or `pull_request` run leaves `inputs` empty and falls through to the GitHub-hosted runner.
- Reconciliation warns with `PS-RUNNER-LABELS-UNREACHABLE` when non-empty labels are inert under consumer-owned caller ownership or direct self-hosted mode. Pass the input from an owned caller, restore managed caller ownership, or own and pin the direct workflow's `runs-on` selection. Empty labels and the managed caller path stay silent.
- Automatic migration maps specification settings semantically and adopts only the exact released caller. A customized legacy caller requires explicit `workflow_ownership: "consumer-owned"` intent; other modified or unclaimed state blocks apply.
- Disable plus reconcile removes managed workflow ownership without deleting authored specifications.

Use [adopt.md](adopt.md) for package-specific configuration, authoring, CI, migration, verification, and disable behavior.
