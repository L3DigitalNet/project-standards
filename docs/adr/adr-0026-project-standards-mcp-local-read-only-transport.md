---
schema_version: '1.1'
id: 'adr-0026-project-standards-mcp-local-read-only-transport'
title: 'ADR 0026: MCP Local Read-Only Transport'
description: 'Freezes the v1 local stdio read-only scope, CLI form, resource URI grammar, explicit-root rules, capability semantics, and tool/prompt registry for the Project Standards MCP server.'
doc_type: 'adr'
status: 'active'
created: '2026-07-28'
updated: '2026-08-10'
reviewed: '2026-08-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'standards-platform'
  - 'mcp'
  - 'transport'
  - 'resources'
aliases:
  - 'ADR 0026'
  - 'MCP local read-only transport'
related:
  - 'docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md'
  - 'docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md'
  - 'docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0012-mcp-readiness-before-server-implementation.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
  - 'docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md'
supersedes: []
superseded_by: null
source:
  - 'docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md'
  - 'docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
  amends: []
  amended_by: []
---

# ADR 0026: MCP Local Read-Only Transport

MADR status: **accepted** (2026-07-28; owner approval recorded in the T1 session for the owner-owned decisions). This decision record was prepared at the `SPEC-RD01` Step 09 gate. The owner recorded approval on 2026-07-28, so the whole record is in force and binding on an implementer — not merely the CLI form and the generic-dispatch disposition, but equally the resource URI grammar, the root rules, the capability semantics, the adapter configuration, and the tool and prompt registry. The named owner questions inside it are `SPEC-MS01 OQ-002` (CLI form) and `SPEC-MS01 OQ-007` (generic dispatch tool).

> **Amended 2026-07-29 (T5 RED review, finding F6).** The frozen instructions text becomes binding at the plan task that completes the six-tool registry it describes; until then the server serves a static, era-stable string that must stay truthful for its phase. See [Amendments](#amendments).
>
> **Amended 2026-07-30 (T9 RED review, finding F2).** The frozen instructions text binds per session registry, so the string never names a tool the session does not register. See [Amendments](#amendments).
>
> **Amended 2026-07-30 (T10 RED review, finding F3; record queued at the T3, T5, and T6 close-out harvests).** The v1 error taxonomy and its per-revision JSON-RPC wire mapping are frozen as enumerated below. See [Amendments](#amendments).
>
> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §4 and C4).** The three amendments above were previously inline paragraphs inside `### Frozen adapter configuration`; their text is unchanged and now lives under [Amendments](#amendments), so a reader meets them before the decision text as the amendment form requires. The outcome also records why the omitted generic provider-dispatch tool is consistent with [ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md) rather than a departure from it. No frozen commitment changes.
>
> **Amended 2026-08-10 (#161 grammar-authority reconciliation).** This ADR remains the sole owner of the unchanged four-segment MCP resource URI grammar. [ADR 0010](adr-0010-standard-resource-uris-and-index.md) adopts it by reference for its catalog and index population without widening either record. Commit `e400f83f` already aligned both catalog producers; the earlier divergence disclosure remains below as historical accepted text. See [Amendments](#amendments).

## Context and Problem Statement

With the protocol implementation and service boundary settled by [ADR 0025](adr-0025-project-standards-mcp-service-and-sdk-boundary.md), the externally visible surface of the server still has to be fixed before any code is written: which transport and effect class v1 ships, how the server is launched, how a client names a standard resource, how the repository under inspection is identified, which protocol capabilities are declared, and which tools and prompts exist.

Each of these is a compatibility commitment. A resource URI that is not canonical becomes a permanent alias; a declared capability that is not implemented becomes a client-visible failure; a tool added in v1 cannot be withdrawn without breaking consumers. The client evidence also constrains the answers: Codex CLI 0.145.0 advertises no roots and has no established model-initiated resource access, and revision `2026-07-28` deprecates Roots. See the [protocol, SDK, and client evidence matrix](../research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md).

## Decision Drivers

- v1 must be small enough to prove and safe enough to run unattended in an editor session.
- The surface must work identically on both installed clients, not only on the more capable one.
- Resource identity must be exact and version-qualified, because catalog packages advertise multiple versions concurrently.
- Declared capabilities must equal implemented behaviour under `2026-07-28` and under every earlier revision the SDK serves.
- Deferred scope must be recorded against an existing owning question, not left implicit.

## Considered Options

- Ship v1 as a local stdio, read-only server with an explicit-root argument, a frozen version-qualified URI grammar, and a fixed six-tool registry.
- Include the remote Streamable HTTP transport in v1.
- Include apply, mutation, or write tools in v1.
- Identify the repository from client-advertised roots instead of an explicit `repo_root` argument.
- Ship a generic provider-dispatch tool in v1 alongside the specialized tools.
- Ship the server as a separate entrypoint executable rather than a subcommand.

## Decision Outcome

Chosen option: **ship v1 as a local stdio, read-only server with an explicit-root argument, a frozen version-qualified URI grammar, and a fixed six-tool registry**.

### Scope

v1 serves the local stdio transport only and is read-only: it exposes no apply, mutation, or write tool, and no tool that modifies the consumer repository, the installed distribution, or any lock file.

- The remote Streamable HTTP transport is deferred. It is governed by `SPEC-RD01 OQ-007` ("When is remote MCP justified?", Step 18).
- Controlled writes are deferred. They are governed by `SPEC-RD01 OQ-004` ("Should controlled writes ever call GitHub directly?", Step 15).

Neither deferral is a placeholder in the code: v1 declares no write capability and registers no write tool.

### CLI form

The server is launched through a `project-standards mcp` subcommand on the existing unified CLI, not through a separate executable. This resolves `SPEC-MS01 OQ-002`; owner approval was recorded on 2026-07-28.

### Resource URI grammar

This section resolves `SPEC-RD01 OQ-002`. Three URI forms exist and no others:

| Form | Meaning |
| --- | --- |
| `standards://catalog/{catalog_major}` | The installed catalog projection for one catalog major |
| `standards://{standard_id}/{version}` | One exact standard package version |
| `standards://{standard_id}/{version}/resources/{resource_id}` | One declared resource inside that exact package version |

Canonicalization rules:

- `standard_id`, `version`, and `resource_id` appear exactly as declared by the installed catalog. The server does not normalize, alias, or re-case declared identifiers.
- No trailing slash.
- No uppercase.
- No percent-encoding beyond what RFC 3986 makes necessary.
- A non-canonical URI, or a URI naming an identifier the installed catalog does not declare, produces a structured not-found or invalid-URI error. The server never performs fuzzy matching, nearest-version resolution, or case-insensitive recovery.

#### Disclosed divergence from the shipped catalog index

The shipped catalog index `standards/catalog.md`, generated by `src/project_standards/standards_graph/catalog.py:172` under [ADR 0010](adr-0010-standard-resource-uris-and-index.md), publishes three-segment resource URIs of the form `standards://{standard_id}/{version}/{resource_id}`, without the `/resources/` segment. The grammar frozen above is `SPEC-MS01`'s four-segment form.

A second live producer exists. `render_catalog` at `src/project_standards/standards_graph/catalog.py:330` is exported and CLI-reachable and emits a two-segment unversioned form, `standards://{standard_id}/{resource_id}`. No tracked or shipped artifact carries that form today. Under the frozen grammar a two-segment URI is parsed positionally as form 2, `standards://{standard_id}/{version}`, so the resource id lands in the version slot and the read fails with a structured unknown-version not-found error: the form is rejected, never silently served as something else.

The forms differ, and this record does not reconcile them. v1 serves **only** the canonical four-segment form and registers **no** alias, redirect, or compatibility mapping for either the three-segment index form or the two-segment unversioned form. Aligning both producers, `SPEC-MS01`, and ADR 0010 on one form is out of scope for T1 and is flagged for owner decision as one index-and-producer alignment item.

### Root rules

- An explicit `repo_root` argument is mandatory on every repository-scoped tool and is the authoritative repository identity for that call.
- Client-advertised roots, where a client supplies them, may only validate or narrow containment: they may cause the server to reject an explicit root that lies outside the advertised boundary.
- Client-advertised roots never substitute a missing `repo_root`, never select a different repository, and never widen the boundary.
- Claude Code 2.1.220 advertises roots; Codex CLI 0.145.0 advertises none; revision `2026-07-28` deprecates Roots. The explicit-argument design is therefore deliberately roots-independent and does not become less correct when Roots is removed.

### Capability semantics

The server declares only what it implements.

- **Resources:** declared, without `subscribe`, and with `listChanged` false.
- **Tools:** declared, with `listChanged` false.
- **Prompts:** declared only when prompt-role resources are registered, and when declared, with `listChanged` false; otherwise the capability is absent.
- `listChanged` is false for all three capabilities without exception. The resource, tool, and prompt registration sets are all fixed at process start and static for the lifetime of the server process, so there is never anything to notify.
- No capability is declared for sampling, roots, or logging.

These declarations are accurate under `2026-07-28` and under every earlier revision the SDK serves. The server keeps a stateless posture and relies on no initialize-time session state, which matches the removal of sessions and of the initialize handshake in `2026-07-28`; `server/discover` is answered by the SDK.

### v1 tool, prompt, and fallback registry

| Tool | Purpose |
| --- | --- |
| `standards_list` | List the installed catalog's standards and exact versions |
| `standard_read` | Return the bytes of one declared package resource |
| `repo_inspect` | Report normalized consumer state and bounded findings for an explicit root |
| `reconcile_preview` | Return the non-applying reconciliation plan and its fingerprint |
| `validate_repo` | Run applicable validate, verify, and lint provider operations |
| `drift_check` | Return reconciliation facts plus applicable drift-check provider results |

`standard_read` is a required fallback, not a convenience: Codex CLI 0.145.0 has no established model-initiated resource access, so without it Codex users have no path to standard content. See the required-fallbacks section of the [evidence matrix](../research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md).

A generic provider-dispatch tool is **omitted** from v1. `McpServiceFacade.invoke_read_provider` remains facade-internal and is reached only through `validate_repo` and `drift_check`. This is the recorded disposition of `SPEC-MS01 OQ-007`; owner approval was recorded on 2026-07-28.

That omission is consistent with [ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md) rather than a departure from it, and needs no exception to it. ADR 0005 rejected **a tool per standard**, because that surface grows linearly with the catalog. The registry frozen above is six tools regardless of how many standards the catalog carries: `standards_list` and `standard_read` take the standard and version as parameters, which is exactly the property ADR 0005 protected. Declining a generic dispatch tool constrains a different axis — one entry point per provider **operation** — which ADR 0005 never governed.

Prompts are registered only from declared prompt-role resources. The server invents no prompts of its own.

### Frozen adapter configuration

`create_server` is constructed with exactly this configuration; it is not implementer-tunable in v1 beyond the items listed here.

- **Server name:** `project-standards`.
- **Configured root boundary:** one **optional** launch-time boundary, exposed as a CLI option on the `project-standards mcp` form, default none. When supplied it is passed to `resolve_effective_root` as the configured boundary input, and it narrows containment exactly as client-advertised roots do. When absent, containment rests on the mandatory explicit `repo_root` argument together with any client-advertised roots. It never supplies a missing `repo_root` and never widens the boundary.
- **Capabilities:** exactly the set frozen in the capability-semantics section above — resources without `subscribe`, tools, and prompts only when prompt-role resources are registered, all three with `listChanged` false.
- **Logging:** every log record, warning, and traceback goes to `stderr`. Nothing but protocol messages is written to `stdout`, and the server declares no logging capability.
- **Instructions:** one static string, unchanged for the process lifetime. Codex CLI 0.145.0 documents server instructions as a supported feature (see the evidence matrix), so this string is a real client-visible surface rather than decoration. The frozen draft text is:

> Project Standards is a read-only, local standards server. It exposes the installed Catalog 5 standard packages and reports on a consumer repository; it never writes to any repository. Standard content is addressed under the `standards://` URI scheme as `standards://catalog/{catalog_major}`, `standards://{standard_id}/{version}`, and `standards://{standard_id}/{version}/resources/{resource_id}`, using ids and versions exactly as the installed catalog declares them. Six tools are available: `standards_list`, `standard_read`, `repo_inspect`, `reconcile_preview`, `validate_repo`, and `drift_check`. Every repository-scoped tool requires an explicit `repo_root` argument; the server does not infer the repository from the working directory or from client roots.

### Consequences

- Good, because the v1 surface is provable end to end on both installed clients with no client-specific code path.
- Good, because an exact, version-qualified URI grammar keeps resource identity stable while a catalog advertises several versions of a standard concurrently.
- Good, because the explicit `repo_root` argument makes repository selection auditable and survives the deprecation and eventual removal of Roots.
- Good, because a read-only server cannot damage a consumer repository, so it needs no approval workflow in v1.
- Neutral, because deferred remote and write scope stays visible through named owning questions rather than through code stubs.
- Bad, because omitting a generic provider-dispatch tool means each new exposed provider operation needs a deliberate tool decision.
- Bad, because strict URI canonicalization rejects near-miss URIs that a lenient server would have resolved, which will surface as client-visible errors.

### Confirmation

Contract tests assert the declared capability set equals the registration set, that `subscribe` is absent, that `listChanged` is false on all three of the resources, tools, and prompts capabilities, and that prompts are declared only when prompt-role resources exist. Further contract tests pin the server name, the instructions string, and the absence of any non-protocol output on `stdout`. Parametrized tests cover URI canonicalization, rejection of non-canonical and undeclared URIs, rejection of the three-segment index form, and root containment including symlinked and out-of-bounds inputs. Security tests assert that no registered tool writes to the repository. The client smoke matrix exercises the registry against Claude Code and Codex CLI from an installed wheel.

### Amendments

**Amended 2026-08-10 (#161 grammar-authority reconciliation).** The producer divergence disclosed in the accepted outcome was resolved by `e400f83f`: `_render_package_catalog` changed from the three-segment index form and `render_catalog` changed from the two-segment unversioned form to this ADR's frozen four-segment form. This ADR remains the sole owner of that grammar. ADR 0010 adopts it by reference for its existing catalog and index population and retains its protocol-boundary exclusion; neither record's governed population changes. The three permitted forms, canonicalization rules, structured-error behavior, and positional rejection of the former two-segment form remain unchanged. A v2 protocol successor must carry the grammar forward or deliberately replace it in its own decision.

**Amended 2026-07-29 (T5 RED review, finding F6).** The frozen draft text above becomes binding at the implementation-plan task that completes the six-tool registry it describes (T9) and is pinned verbatim by the T10 contract suite. Until that registry exists, the server serves a static, era-stable instructions string that must stay truthful for its phase: it must not name tools, prompts, or URIs that are not registered. This phase rule resolves the conflict between the frozen text and the plan's T5 empty-registry boundary without weakening either.

**Amended 2026-07-30 (T9 RED review, finding F2).** The frozen text binds per session registry. A server process whose recorded client matrix registers all six tools serves the six-tool text; a process whose matrix omits the `standard_read` fallback serves the same text with the tool enumeration reduced to its actual registry — the count word and the enumeration shrink, nothing else changes — so the instructions never name a tool the session does not register. The string remains static and non-tunable: it is fixed at process construction from the T1 evidence matrix, which is recorded evidence rather than configuration. The T10 contract suite pins each rendering the matrix can produce. This keeps the truthfulness rule — name nothing unregistered, deny nothing registered, promise nothing unimplemented — true in every configuration.

**Amended 2026-07-30 (T10 RED review, finding F3; record queued at the T3, T5, and T6 close-out harvests).** The v1 error taxonomy and its per-revision JSON-RPC mapping are frozen. The stable `ServiceError` code strings in service and adapter use are exactly `catalog-invalid`, `catalog-not-found`, `consumer-services-unavailable`, `control-plane-busy`, `control-plane-unavailable`, `installed-distribution-invalid`, `internal-error`, `prompt-derivation-unavailable`, `provider-cancelled`, `provider-effect-refused`, `provider-frame-invalid`, `provider-input-invalid`, `provider-invocation-failed`, `provider-not-found`, `provider-not-selected`, `provider-operation-refused`, `provider-result-invalid`, `provider-result-too-large`, `provider-timeout`, `provider-worker-failed`, `provider-worker-unavailable`, `reconciliation-unavailable`, `repo-root-invalid`, `repo-root-out-of-bounds`, `resource-integrity`, `resource-not-found`, `resource-registration-invalid`, `resource-uri-invalid`, `root-boundary-invalid`, `standard-not-found`, `tool-arguments-invalid`, and `tool-not-found` (inventory corrected 2026-07-30 at T10 GREEN, finding F1: the initial enumeration missed nine pre-existing provider and repository codes; `internal-error` was minted at T10 GREEN for the unexpected-handler class under the additive clause below and is ratified here); adding a code is a reviewed additive change, while renaming or removing one breaks this record. The wire mapping has three classes and only one revision-dependent member: the transport's declared server-fault set (`resource-integrity`, `catalog-invalid`) answers `-32603` under every revision; the not-found set (`catalog-not-found`, `standard-not-found`, `resource-not-found`) answers `-32002` under the pre-2026 revisions that define that code and `-32602` under `2026-07-28`; every other refusal answers `-32602` under every revision. A refusal carries the service's own message with the published `code`, `severity`, `remediation`, and optional identity fields in `error.data` — nothing invented, nothing dropped — and is delivered as a JSON-RPC error, never as a successful `isError` result. An unexpected handler exception is mapped by the adapter to a structured `-32603` refusal in both eras; the SDK's generic path (classic `code: 0` carrying raw exception text, modern `-32603` with no `data`) is never served, and raw exception text never reaches the wire.

## Pros and Cons of the Options

### Local stdio, read-only v1

- Good, because stdio needs no network exposure, no authorization flow, and no credential handling: `2026-07-28` authorization is HTTP-only and directs stdio implementations to take credentials from the environment.
- Good, because read-only scope removes the entire class of destructive failure from the first release.
- Bad, because useful write workflows must wait for a later, separately approved step.

### Remote Streamable HTTP in v1

- Rejected: deferred to `SPEC-RD01 OQ-007`, which admits remote MCP only after the local server has recurring use and a concrete remote use case.
- Bad, because it would add authorization, identity, and multi-user concerns before the local surface is proven.

### Apply, mutation, or write tools in v1

- Rejected: deferred to `SPEC-RD01 OQ-004`, which answers no for v1 and requires local repository writes first.
- Bad, because model-initiated writes need an approval story that the client surfaces do not yet standardize.

### Client-advertised roots as the repository identity

- Rejected: Codex CLI 0.145.0 advertises no roots, and `2026-07-28` deprecates Roots with removal no earlier than 2027-07-28.
- Bad, because repository selection would then be implicit, client-dependent, and unauditable from the tool call itself.

### Generic provider-dispatch tool in v1

- Rejected for v1 under the recorded resolution of `SPEC-MS01 OQ-007`: the specialized `validate_repo` and `drift_check` tools cover the current read-only provider operations, and a generic tool does not materially reduce the exposed surface.
- Bad, because a generic dispatch tool widens the model-controlled surface to every declared provider operation at once.

### Separate entrypoint executable

- Rejected under the recorded resolution of `SPEC-MS01 OQ-002`: a second executable duplicates CLI wiring, packaging entry points, and documentation for no gain.
- Bad, because it splits the discoverable command surface of one distribution.

## More Information

- Evidence register: [`2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md`](../research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md)
- Service and SDK boundary: [`adr-0025-project-standards-mcp-service-and-sdk-boundary.md`](adr-0025-project-standards-mcp-service-and-sdk-boundary.md)
- Existing standard resource URI and index decision: [`adr-0010-standard-resource-uris-and-index.md`](adr-0010-standard-resource-uris-and-index.md)
- Catalog version channels that make version-qualified URIs necessary: [`adr-0024-catalog-scoped-package-version-channels.md`](adr-0024-catalog-scoped-package-version-channels.md)
- Owning specifications: [`SPEC-RD01`](../specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md) and [`SPEC-MS01`](../specs/2026-07-07-project-standards-mcp-server-implementation-spec.md)
