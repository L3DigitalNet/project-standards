# ADR Library Candidates

- [ADR Library Candidates](#adr-library-candidates)
  - [Purpose](#purpose)
  - [Survey boundary](#survey-boundary)
  - [Candidates](#candidates)
    - [Governance, ownership, and document architecture](#governance-ownership-and-document-architecture)
    - [Safe mutation and batch operations](#safe-mutation-and-batch-operations)
    - [Data, persistence, and recovery](#data-persistence-and-recovery)
    - [Testing, evidence, and quality gates](#testing-evidence-and-quality-gates)
    - [Delivery, runtime, and security](#delivery-runtime-and-security)
    - [Application and agent architecture](#application-and-agent-architecture)
  - [Not advanced](#not-advanced)

## Purpose

This document records reusable ADR-library opportunities found by surveying the Git repositories under `/home/chris/projects/`. It is an intake list, not an acceptance decision: each candidate still needs a generalized draft, evidence review, placement in the library taxonomy, and owner approval before it becomes release content.

Candidate titles describe the reusable decision rather than the source implementation. Product names, repository paths, thresholds, topology, and other local mechanics must be replaced with explicit adoption-time choices unless they are essential to the decision.

## Survey boundary

The survey covered all 28 Git repositories discovered under `/home/chris/projects/` on 2026-08-01. It read 136 formal ADRs and 26 retained, implemented or approved design decisions that serve the same architectural-record function. Templates, fixtures, generated copies, unresolved specifications, and descriptive architecture without a decision were excluded.

Active decisions were preferred. Superseded records were used only when a current decision retained their reusable rationale. Proposed decisions were not promoted. Repeated local `dev`/`main` and hook-policy ADRs were treated as covered by the existing [Branch Integration and Protection Strategy](git/branch-integration-and-protection.md) library entry.

Source references use `repository: record` notation and are relative to the named repository.

## Candidates

### Governance, ownership, and document architecture

| Candidate | Source evidence | Reusable decision | Confidence |
| --- | --- | --- | --- |
| Explicit authority maps and scope boundaries | `project-standards: ADR 0004`; `agent-configs: ADRs 0013-0014`; `Claude-Code-Plugins: ADR 0001` | Assign one owner to each domain, target, concern, and mutable unit; reject overlap instead of resolving it through hidden precedence. | High |
| Manifest-first self-describing bundles | `project-standards: ADRs 0001-0002` | Keep machine-readable identity, lifecycle, capabilities, relationships, and resources beside each bundle so additions do not require central dispatch changes. | High |
| Stable generic operations with pluggable policy seams | `project-standards: ADRs 0005-0006`; `docmend: ADR 0010` | Keep the public operation surface generic and bind specialized behavior through narrow registries or interfaces; add swapping machinery only when a second implementation exists. | High |
| Canonical sources with disposable derived projections | `llm-wiki: ADR 0016`; `agent-configs: ADR 0014`; `project-standards: ADR 0010` | Make indexes, caches, and harness projections regenerable views over authoritative sources, publish related views as one generation, and verify freshness and provenance. | High |
| Canonical documents with compact subordinate summaries | `project-standards: ADR 0009` | Preserve full evidence and rationale in the authoritative document while providing a reviewed, version-matched summary for low-context consumers. | High |
| Independent packages with explicit relationship taxonomy | `project-standards: ADR 0013` | Make components independently selectable by default and declare companion, extension, conflict, and platform relationships instead of hiding dependencies in profiles. | High |
| Repository-owned extensions projected into discovery roots | `project-standards: ADRs 0016 and 0021-0022`; `llm-wiki: ADR 0014`; `agent-configs: ADR 0016` | Version skills, hooks, and other extensions with the repository they govern; project attributable installed views without creating competing canonical copies or mutating global state. | High |
| Unified desired-state and applied-state reconciliation | `project-standards: ADR 0023` | Separate user-owned desired configuration, tool-owned catalog and lock state, read-only planning, and an explicit atomic apply path that preserves unowned content. | High |
| Governed package lifecycle and explicit major channels | `project-standards: ADRs 0018 and 0024` | Treat lifecycle transitions as multi-surface package changes; keep compatible defaults distinct from opt-in breaking tracks and persist exceptional authorization. | Medium |
| Cross-repository product and adapter ownership | `doc-proc-scripts: ADRs 0002 and 0007`; `docmend: ADR 0018` | Define mirrored owns/does-not-own boundaries, consume the product through versioned public interfaces, and prevent adapters from duplicating core semantics. | High |
| Target-repository governance for cross-repository automation | `Claude-Code-Plugins: up-docs migration design` | Read the target repository's contracts at runtime, validate from its root, confine writes to authorized layers, and fail only the affected integration when the target is unavailable. | High |
| Durable specification, reference, and plan lifetimes | `agent-pseudocode: ADR 0001`; `llm-wiki: ADR 0018`; `agent-configs: ADR 0009` | Classify documents by authority and lifetime: implemented contracts remain reference, intended-state specifications persist, and execution plans are removed after evidence-backed completion. | High |
| Document form separate from subject taxonomy | `llm-wiki: ADRs 0003 and 0008` | Use one strict metadata core for how a document functions, namespaced extensions for special fields, and directories or tags for subject classification. | High |
| Stable document identity with validated path references | `llm-wiki: ADRs 0005, 0011, and 0015` | Keep identity stable across moves and retitles while validating canonical repository-relative references and local uniqueness invariants. | High |
| Documentation authority and system-of-record cutover | `llm-wiki: ADR 0009` | Assign strategy, implementation reference, and live truth to explicit owners; name and validate the replacement before migration or decommission. | High |
| Evidence, synthesis, and intake layer separation | `llm-wiki: ADRs 0001 and 0007` | Separate immutable captured evidence, maintained synthesis, and mutable intake; prohibit citing staging content until an explicit promotion path completes. | High |
| Positive-scope validation for competing schemas | `project-standards: ADR 0015`; `agent-pseudocode: ADR 0003`; `docmend: ADR 0023` | Give each schema a narrow positive corpus, exclude templates and ephemeral state, and keep metadata validation distinct from body validation. | High |

### Safe mutation and batch operations

| Candidate | Source evidence | Reusable decision | Confidence |
| --- | --- | --- | --- |
| Consent-gated staging in dirty worktrees | `Claude-Code-Plugins: up-docs and qdev designs` | Capture the baseline, disclose per-path diffs, exclude same-path collisions, recheck late, stage literal paths, review the index, and never infer commit or push authority. | High |
| Safe destructive repository removal | `projects: projects-manager design` | Check eligibility before selection, aggregate confirmation, revalidate immediately before each removal, skip changed targets, and provide no force escape hatch. | High |
| Failure-isolated batch execution | `projects: projects-manager design`; `hw-radar: ADR 0017` | Classify targets independently, preserve safe partial progress, persist per-target lifecycle, and prevent one failed source or repository from halting peers. | High |
| Reviewable plan/apply pipeline with one mutator | `docmend: ADR 0002`; `project-standards: ADR 0023` | Separate discovery, immutable planning, pure transformation, isolated mutation, and verification; reject stale plans and allow only one layer to write. | High |
| Prove-before-mutate preservation contract | `doc-proc-scripts: ADR 0005`; `docmend: ADR 0004` | Default to read-only, require explicit mutation, evaluate independent fail-closed predicates, verify preservation before writing, and prove restoration mechanically. | High |
| Atomic replacement bound to object identity | `docmend: ADRs 0003 and 0020`; `agent-sandbox: atomic-write decision` | Stage on the same filesystem, read through descriptors, capture device and inode identity, recheck containment immediately before replacement, and document residual races. | High |
| Versioned recovery journal and durable artifact contract | `docmend: ADRs 0005 and 0019` | Use strict versioned schemas and an append-only, fsynced, hash-linked journal whose run and root identity are validated before any path is accessed. | High |
| Risk-classed output and destination policy | `doc-proc-scripts: ADR 0009`; `docmend: ADR 0021` | Permit overwrite only for regenerable output; require preservation for valuable content; reject symlinks and input aliases at lexical and resolved boundaries. | High |
| Deterministic automation and probabilistic evidence | `doc-proc-scripts: ADRs 0008 and 0010`; `docmend: ADR 0009` | Automate exact, versioned cases; treat classifier confidence as quarantine or review evidence; use independent gates and fail toward retaining data. | High |
| Stable machine-readable exit-code taxonomy | `docmend: ADR 0012`; `projects: projects-manager design` | Use one cross-command taxonomy for clean results, findings, invalid invocation, and safety refusal; send data to stdout and diagnostics to stderr. | High |
| Safe bulk formatter adoption | `Claude-Code-Plugins: Markdown Tooling adoption design` | Inventory tracked and untracked scope, isolate mechanical formatting from semantic edits, clean the corpus before enforcement, and prove excluded families remain untouched. | High |
| AI-proposed mutations with consent and audit | `HomeBase: tags and autorename design` | Preserve the original, present an editable proposal, support accept/edit/skip, make collisions safe, and leave the original intact on failure. | Medium |

### Data, persistence, and recovery

| Candidate | Source evidence | Reusable decision | Confidence |
| --- | --- | --- | --- |
| Safe schema-validated serialization | `star-trek-retro-remake: ADR 0004` | Use a non-executable, human-inspectable format behind an explicit schema boundary; forbid code-executing deserializers for user-controlled state. | High |
| Event-driven snapshots with periodic fallback | `star-trek-retro-remake: ADR 0010`; `hw-radar: ADR 0015` | Persist at meaningful state transitions, add a bounded interval fallback, avoid redundant full snapshots, and make freshness an explicit service objective. | High |
| Zero-verbatim agent boundary for sensitive corpora | `doc-proc-scripts: ADR 0003` | Let tools handle content bytes while agents receive paths and metadata; keep reports and errors content-free and test with synthetic fixtures. | High |
| Two-corpus testing with re-synthesized anomalies | `doc-proc-scripts: ADR 0006`; `docmend: ADR 0015` | Pair a frozen committed synthetic regression corpus with a seed-generated scale corpus and reproduce causal anomalies without retaining source bytes. | High |
| Relational system of record with a time-series extension | `hw-radar: ADR 0007` | Keep mutable dimensions and append-mostly observations in one relational authority; require a plain-database fallback and extension-aware restore proof. | High |
| Auditable monetary normalization without false precision | `hw-radar: ADR 0008` | Normalize to one reporting currency while storing rate, pair, date, and source; flag unknowable costs instead of inventing constants. | High |
| Explainable composite scoring with vetoes | `hw-radar: ADR 0011` | Combine normalized factors without allowing one strong factor to hide a disqualifying weakness; shrink sparse evidence and retain factor-level explanations. | High |
| Stable credential replacement and secret-free fingerprints | `cc-usage-monitor: ADR 0001` | Separate candidate arrival order from installed-state replacement and fingerprint normalized, intrinsic, non-secret content rather than publisher metadata. | Medium |
| Layered backup around an explicit system of record | `HomeBase: MCP redeploy design`; `hw-radar: ADR 0003` | Distinguish seed, cache, replica, and authority; assign backup ownership and verify logical, data, system, off-site, and restore lanes as applicable. | High |

### Testing, evidence, and quality gates

| Candidate | Source evidence | Reusable decision | Confidence |
| --- | --- | --- | --- |
| Deterministic validation before semantic review | `project-standards: ADR 0007`; `Claude-Code-Plugins: spec-pipeline design` | Mechanize syntax, references, dependency graphs, lifecycle transitions, and evidence capture before paying for human or model judgment. | High |
| Consumer-composition fixtures and real-capability lanes | `project-standards: ADR 0011`; `Markdown-Keeper: integration-test design` | Test combinations on realistic consumers and prove that capability-specific lanes loaded the real implementation rather than a fallback. | High |
| Staged strict quality-gate ratchet | `control-center: ADR 0002`; `llm-wiki: ADRs 0010 and 0012` | Keep the final strict mode visible, baseline legacy debt, reject new violations, set truthful floors, and require monotonic improvement. | High |
| Packaged-artifact parity and release-bound qualification | `project-standards: ADR 0019`; `docmend: ADR 0022` | Prove source, built artifacts, and installed behavior are byte- or semantics-equivalent; bind scale and resource claims to the exact release artifact and environment. | High |
| Epoch-bound resumable evaluation evidence | `agent-configs: ADRs 0007-0008` | Bind plans, runs, retries, budgets, confidence, and resume to immutable input digests; never combine evidence from changed inputs. | High |
| Current external research with durable reuse | `Claude-Code-Plugins: qdev design` | Prefer current authoritative sources, corroborate acted-on hazards, grade evidence, and persist the report so downstream work does not repeat the search. | Medium |
| Dependency selection and reversal contract | `docmend: ADR 0013` | Evaluate licensing, offline behavior, runtime artifacts, native risk, maintenance, and fallbacks; name measurable triggers for replacement or escalation. | High |

### Delivery, runtime, and security

| Candidate | Source evidence | Reusable decision | Confidence |
| --- | --- | --- | --- |
| Runtime secrets via a local agent with credential-free CI | `hw-radar: ADR 0009` | Separate deployment from secret authority; render short-lived credentials to volatile storage, gate service startup on successful rendering, and keep store credentials out of CI. | High |
| Credential-minimized delivery to a private target | `hw-radar: ADR 0006` | Join the private network ephemerally from trusted events, use environment-scoped approval and least privilege, migrate before restart, and prove rollback. | High |
| Authentication when crossing the loopback boundary | `HomeBase: MCP redeploy design`; `Claude-Code-Plugins: Home Assistant design` | Default to loopback; require authentication for non-loopback exposure; resolve secrets outside committed config and prove enforcement with a negative test. | High |
| Dedicated service container on an existing operations substrate | `hw-radar: ADR 0003` | Choose the deployment unit that inherits proven backup, monitoring, and policy coverage; require explicit wiring and restore proof instead of assuming discovery. | High |
| Local read-only service with explicit roots and exact capabilities | `project-standards: ADRs 0025-0026` | Start with local IPC, read-only effects, explicit repository identity, strict resource identifiers, truthful capability declarations, bounded workers, and no protocol noise. | High |
| Artifact-free runtime in immutable extension installs | `Claude-Code-Plugins: spec-pipeline design` | Keep environments, locks, caches, bytecode, and state outside installed extension roots; verify ignored artifacts as well as Git-visible changes. | High |
| Fail-safe budget gate for metered APIs | `hw-radar: ADR 0016` | Order every call through kill switch, persisted reserve-before-call budget, provider breaker, and rate limiter; reconcile estimates without loosening the local bound. | High |
| HTTP-first, browser-last acquisition escalation | `hw-radar: ADR 0014` | Prefer structured data and plain HTTP, escalate only on evidence, reserve browsers and managed unblockers for bounded cases, and define an explicit skip boundary. | High |

### Application and agent architecture

| Candidate | Source evidence | Reusable decision | Confidence |
| --- | --- | --- | --- |
| Mechanically enforced domain and UI boundary | `star-trek-retro-remake: ADR 0003` | Keep the domain layer framework-free, route integration through one bridge, forbid reverse imports, and enforce the boundary in CI. | High |
| One rendering framework and event loop | `star-trek-retro-remake: ADR 0001` | Prefer one UI event loop, rendering pipeline, and input model when bridging frameworks creates more complexity than the workload needs. | Medium |
| Right-sized explicit state machine | `star-trek-retro-remake: ADR 0005` | Use a small explicit state graph while it remains inspectable; record objective triggers for adopting a framework as states and hooks grow. | Medium |
| Explicit supported-platform boundary | `star-trek-retro-remake: ADR 0002` | Limit platform support when testing, packaging, and triage capacity cannot sustain a matrix; state the assumptions and reopening trigger rather than claiming best effort. | Medium |
| Batteries-included server-rendered application stack | `hw-radar: ADR 0004` | For a small authenticated CRUD or dashboard product, prefer integrated auth, ORM, migrations, admin, and modest progressive enhancement over an unnecessary SPA/API split. | High |
| Single supervised scheduler for shared admission state | `hw-radar: ADR 0012` | Use one scheduler when jobs share rapidly changing breaker or token-bucket state; let the OS supervise it and define a scale-out trigger. | High |
| Optional capability with deterministic fallback | `Markdown-Keeper: feature and integration-test designs` | Preserve a deterministic baseline when an optional dependency is absent and maintain a separate lane proving that the real capability loads and meets its contract. | High |
| Generated-asset provenance and policy enforcement | `star-trek-retro-remake: ADR 0012` | Store generation prompts, tool and version, date, references, and selection notes beside generated assets; mechanically reject unprovenanced additions. | High |
| Agent orchestration boundary and workload-based model selection | `Claude-Code-Plugins: qdev and Home Assistant designs` | Keep user interaction and approval in the orchestrator, give workers bounded I/O-heavy work, require structured results, and select capacity by reasoning complexity. | High |
| Default-deny tooling acquisition | `agent-configs: ADR 0003` | Distinguish execution from acquisition; require declared capability, task authorization, repository permission, and reviewable effects before installing tools. | High |
| Isolated subscription-backed headless evaluation | `agent-configs: ADR 0006` | Use installed authenticated clients in isolated homes, keep comparison arms equivalent, bound output and cleanup, and fail closed when authentication is absent. | Medium |

## Not advanced

- The branch-integration ADRs in `agent-configs`, `agent-pseudocode`, `doc-proc-scripts`, `docmend`, and `network-infrastructure` duplicate the existing library entry. The distinct hosted-ruleset choice in `star-trek-retro-remake: ADR 0013` remains a possible future branch-protection variant but is too platform- and maintainer-model-specific for this release list.
- Empty drafts, templates, fixtures, generated copies, and explicitly proposed records were excluded. This includes `network-infrastructure: ADR 0001`, `hw-radar: ADR 0019`, and all ADR authoring templates.
- Superseded records were not proposed independently. Their surviving principles were folded into current candidates only when a later active record or implementation preserved them.
- Domain-specific game rules, marketplace schemas, hardware matching, individual notification-provider choices, and one-off application-layout exceptions did not yield sufficiently general decisions.
- The untracked `agent-sandbox/cave-crawler` decision file supplied corroborating examples for atomic replacement, but its remaining decisions were not advanced until they have durable repository status.
