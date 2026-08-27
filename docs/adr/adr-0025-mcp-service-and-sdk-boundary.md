---
schema_version: '1.1'
id: 'adr-0025-project-standards-mcp-service-and-sdk-boundary'
title: 'ADR 0025: MCP Service and SDK Boundary'
description: 'Freezes the exact official MCP SDK dependency, the one-way adapter/service boundary, the internal service facade, and the bounded worker-process provider execution boundary.'
doc_type: 'adr'
status: 'active'
created: '2026-07-28'
updated: '2026-08-09'
reviewed: '2026-08-09'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'standards-platform'
  - 'mcp'
  - 'sdk'
  - 'boundary'
aliases:
  - 'ADR 0025'
  - 'MCP service and SDK boundary'
related:
  - 'docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md'
  - 'docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md'
  - 'docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0012-mcp-readiness-before-server-implementation.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0026-mcp-local-read-only-transport.md'
  - 'docs/adr/adr-0030-command-provider-execution-boundary.md'
supersedes: []
superseded_by: null
source:
  - 'docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md'
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

# ADR 0025: MCP Service and SDK Boundary

MADR status: **accepted** (2026-07-28; owner approval recorded in the T1 session for the owner-owned decisions). This decision record was prepared at the `SPEC-RD01` Step 09 gate. The owner recorded approval of `SPEC-RD01 OQ-001` and `SPEC-MS01 OQ-001` on 2026-07-28, and this record is in force.

## Context and Problem Statement

The Project Standards MCP server must expose the installed Catalog 5 distribution and the unified consumer control plane over the Model Context Protocol. Two questions must be answered before any MCP code exists: which protocol implementation the repository depends on and where that dependency is allowed to appear, and how provider invocations are executed when a protocol loop is waiting on them.

The evidence register records revision `2026-07-28` as final and records `mcp` 2.0.0 as serving that revision and every earlier revision from one server, which the installed Codex CLI 0.145.0 requires because it speaks `2025-06-18` only. See the [protocol, SDK, and client evidence matrix](../research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md).

The existing dispatcher is the second problem. `invoke_provider` at `src/project_standards/control_plane/providers.py:1064` compiles and executes provider code in-process with no timeout, signal handling, or subprocess boundary anywhere in its body. That is acceptable for a synchronous CLI run and unacceptable underneath a protocol server, where an unbounded provider stalls the transport for every client.

## Decision Drivers

- The protocol implementation must be an official, licence-reviewed, exactly pinned stable release, never a hand-rolled or prerelease one.
- Protocol churn must not reach domain services; the SDK has already renamed its server API once between major lines.
- Provider results served over MCP must be identical to results from authoritative direct dispatch, not a re-implementation.
- A provider must never be able to block the protocol loop indefinitely, leak output onto the protocol channel, or leave the repository modified.
- Result and diagnostic payloads must be bounded so a large provider output cannot exhaust the server or the client budget.

## Considered Options

- Depend on the official `mcp` Python SDK at an exact stable pin, isolate it behind a one-way adapter boundary, and execute providers in a bounded worker process.
- Hand-roll a JSON-RPC implementation instead of taking an SDK dependency.
- Depend on the official SDK v1 line at `mcp` 1.29.0.
- Declare the SDK as an optional extra, `project-standards[mcp]`, instead of a main runtime dependency.
- Keep provider execution in-process inside the server process.

## Decision Outcome

Chosen option: **depend on the official `mcp` Python SDK at an exact stable pin, isolate it behind a one-way adapter boundary, and execute providers in a bounded worker process**.

### Dependency

The repository depends on the official `mcp` Python SDK with the exact pin `mcp==2.0.0`, declared in the main runtime dependency group of `pyproject.toml`: the PEP 621 `[project].dependencies` array, **not** the PEP 735 `[dependency-groups]` table and not an optional extra. The licence is MIT and has been reviewed. Prereleases of the SDK are prohibited, and no alternative or vendored protocol implementation is permitted.

The owner recorded approval on 2026-07-28, so the pin is declared in `pyproject.toml` as well as in this record and the evidence matrix.

The frozen facade below keeps the property [ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md) protected: every facade method is generic over standard identity and version, so the service surface does not grow when the catalog gains a standard. ADR 0005 constrains growth **per standard**; it does not require one entry point per provider operation, so naming specific methods here is not a departure from it and needs no exception to it.

### Adapter direction and import boundary

There is exactly one direction of dependency:

- `src/project_standards/mcp_server/` is the SDK-dependent adapter. It is the only place in the repository that imports `mcp`.
- `src/project_standards/mcp_services/` is SDK-free. It holds the protocol-neutral services and DTOs.
- `mcp_server` imports `mcp_services`. `mcp_services` never imports `mcp_server` and never imports `mcp`.
- SDK types never appear in the public signatures, return values, or exceptions of `mcp_services`.

### Frozen service facade

This ADR freezes the service-facade and protocol-neutral DTO boundary directly: these names, inputs, and required results are the implementation contract, and an implementer must not invent parallel models. The frozen names are:

- `McpServiceFacade.from_installed` and `McpServiceFacade.from_source` for construction.
- `McpServiceFacade.catalog`, `McpServiceFacade.standard`, and `McpServiceFacade.resource` for exact package facts and verified resource bytes.
- `McpServiceFacade.inspect_repo` and `McpServiceFacade.reconcile` for consumer inspection and non-applying reconciliation preview.
- `McpServiceFacade.invoke_read_provider`, `McpServiceFacade.validate_repo`, and `McpServiceFacade.drift_check` for bounded non-mutating provider work.
- `resolve_effective_root` for root normalization and containment.
- `create_server` and `run_stdio` in the adapter.

Changing any of these names or shapes requires an approved amendment to this record and corresponding specification, implementation, and test updates.

### Provider execution boundary

Every provider invocation reached through `invoke_read_provider` runs in a spawned worker process using the same interpreter and virtual environment as the server.

- The worker calls the existing `invoke_provider` dispatcher at `src/project_standards/control_plane/providers.py:1064` with exact installed payload identity and typed, JSON-safe input, against the resolved effective consumer root. The MCP path therefore produces results equivalent to authoritative direct dispatch; it does not re-implement provider semantics.
- The provider timeout is **30 seconds per provider invocation**. It exists to bound a single hung or runaway provider and to make termination decidable, nothing more.
- **No aggregate per-tool-call budget is frozen by this record.** The composite tools `validate_repo` and `drift_check` perform N invocations, so their worst case is 30·N seconds. Client-side tool timeouts are client-owned configuration; the evidence matrix documents Codex CLI 0.145.0's `tool_timeout_sec` default of 60 seconds and notes that consumers running composite tools against large consumer sets may need to raise it.
- On timeout the worker is terminated with `SIGTERM`, then `SIGKILL` if it has not exited, and is reaped in both cases. The service returns a structured timeout `ServiceError` and the repository is left unchanged.
- On every completion path — success, timeout, kill, and crash — the parent closes and drains all worker pipes and queues, releases any temporary files or sockets used for IPC, and reaps the process. No IPC resource, file descriptor, or child process survives the invocation.
- Results and diagnostics cross the process boundary as bounded JSON with an explicit size cap. Output beyond the cap is truncated and carries an explicit truncation marker; truncation is never silent.
- The worker's `stdout` and `stderr` are captured into buffers. Neither inherits the server's protocol `stdout`. This is defence in depth rather than the sole protection: the SDK already diverts stray prints to stderr while serving stdio, as recorded in the evidence matrix.

#### T1-approved non-mutating effect set

`invoke_read_provider` may dispatch only provider operations whose declared effect is `findings` (`ProviderEffect.FINDINGS`, `src/project_standards/package_contract/payload.py:420`), restricted to the operations `validate`, `verify`, `lint`, and `drift-check` as declared in the operation contract at `src/project_standards/package_contract/payload.py:426`.

- `semantic-review` also declares the `findings` effect but is excluded from the approved set: its exposure is governed by `SPEC-RD01 OQ-006`, which omits it from v1 unless the selected client surface preserves its user-controlled semantics.
- The `content` effect (`payload.py:421`; operations `id-next`, `extract`, `render`) is non-mutating in itself but is not in the approved set, because no v1 tool exposes those operations. Adding one requires an approved amendment.
- The `mutation-plan` effect (`payload.py:422`; operations `fix`, `scaffold`, `upgrade`) and the `migration-report` effect (`payload.py:423`; operation `migrate`) are excluded outright: they belong to the apply and authoring path this server does not serve.

### Consequences

- Good, because protocol conformance, dual-era serving, and error-code correctness are owned by a maintained official SDK rather than by this repository.
- Good, because an SDK major transition changes one adapter package and no domain service.
- Good, because provider results served over MCP remain equivalent to CLI results by construction: the same dispatcher is called.
- Good, because a hung, noisy, or oversized provider degrades one tool call instead of the whole server.
- Neutral, because the pin is exact, so SDK updates are deliberate repository changes rather than resolver drift.
- Bad, because every `project-standards` consumer installs the SDK and its unconditionally installed HTTP-stack dependencies even if it never runs the MCP server, enlarging the audited dependency surface for all consumers.
- Bad, because worker-process dispatch adds spawn latency and IPC serialization cost to every provider invocation.
- Bad, because a composite tool has no frozen aggregate budget, so a consumer with a large standard set may have to raise its client tool timeout.

### Confirmation

An import-boundary contract test asserts that no module under `mcp_services` imports `mcp` or `mcp_server` and that no `mcp_services` public signature exposes an SDK type. Provider-boundary tests cover the 30-second timeout, `SIGTERM`-then-`SIGKILL` termination with reaping, unchanged repository state after a timeout, bounded IPC with explicit truncation markers, and the absence of worker output on the server's protocol `stdout`.

An IPC-cleanup test asserts that after each of the four completion paths — success, timeout, kill, and crash — the parent holds no open worker pipe, queue, temporary file, or socket, and no child process remains unreaped; file-descriptor and child-process counts return to their pre-invocation values. A dispatch-guard test asserts that `invoke_read_provider` refuses any operation outside the approved `findings` set. Dependency resolution, the exact pin, and `uv run pip-audit` are checked in the T1 verification gate.

## Pros and Cons of the Options

### Depend on the official SDK at an exact stable pin, isolate it, and use a bounded worker

- Good, because `mcp` 2.0.0 "supports the 2026-07-28 revision of the Model Context Protocol and serves every earlier revision from the same server", which is required for Codex CLI 0.145.0.
- Good, because the licence is MIT and `requires-python >=3.10` is satisfied by this repository.
- Neutral, because the SDK renamed `FastMCP` to `MCPServer` in this major line, which the adapter absorbs.
- Bad, because the unconditional HTTP dependencies are audited even though v1 serves stdio only.

### Hand-roll a JSON-RPC implementation

- Rejected: the implementation plan prohibits an implicit hand-rolled JSON-RPC implementation.
- Bad, because revision `2026-07-28` makes `server/discover` mandatory and adds required `resultType`, `ttlMs`, and `cacheScope` fields, and dual-era serving would have to be written and maintained here.

### Depend on the SDK v1 line at `mcp` 1.29.0

- Rejected: v1.x is in maintenance mode receiving security fixes only, and the register records no documented `2026-07-28` support for that line; official `2026-07-28` support is delivered in v2.0.0.
- Bad, because adopting a maintenance-mode line at first release means the server's protocol support is frozen at whatever the line already documents.

### Declare the SDK as an optional extra `project-standards[mcp]`

- Rejected: the `project-standards mcp` subcommand lives on the unified CLI and must work in the standard install. An extra ships a subcommand that is broken by default and splits the tested surface into installed-with-extra and installed-without-extra variants.
- Good, because consumers that never run the server would avoid the SDK's transitive dependencies.
- Bad, because every CLI test, documentation path, and client smoke run would have to state which variant it exercises.

### Keep provider execution in-process

- Rejected: an unbounded in-process provider blocks the protocol event loop with no decidable termination. A Python thread cannot be safely killed, so there is no in-process action that reliably ends a runaway provider; only a separate process gives `SIGTERM`/`SIGKILL` as a real remedy.
- Bad, because there is no fault isolation: a provider that segfaults, exhausts memory, or calls `sys.exit` takes the server down with it, whereas a worker crash degrades one tool call.
- Neutral on stdout hygiene: the SDK already diverts stray prints to stderr while serving stdio (recorded in the evidence matrix), so process isolation of worker output is defence in depth rather than the deciding ground.

## More Information

- Evidence register: [`2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md`](../research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md)
- Transport, scope, and registry decision: [`adr-0026-mcp-local-read-only-transport.md`](adr-0026-mcp-local-read-only-transport.md)
- Sequencing precedent: [`adr-0012-mcp-readiness-before-server-implementation.md`](adr-0012-mcp-readiness-before-server-implementation.md)
- Generic tool-surface constraint this facade satisfies: [`adr-0005-stable-generic-agent-tooling-interface.md`](adr-0005-stable-generic-agent-tooling-interface.md)
- Dispatcher and control-plane authority: [`adr-0023-unified-consumer-standards-control-plane.md`](adr-0023-unified-consumer-standards-control-plane.md)
- Server contract: [`SPEC-MS01`](../specs/2026-07-07-project-standards-mcp-server-implementation-spec.md)
- Operator reference: [`docs/mcp-server.md`](../mcp-server.md)
