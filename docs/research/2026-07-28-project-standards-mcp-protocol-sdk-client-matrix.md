---
schema_version: '1.1'
id: 'research-mcp728-project-standards-mcp-protocol-sdk-client-matrix'
title: 'Project Standards MCP Protocol, SDK, and Client Evidence Matrix'
description: 'Final Step 09 official-source, license, conformance, and client evidence register for the Project Standards MCP protocol, SDK, and client selection.'
doc_type: 'research'
status: 'active'
created: '2026-07-28'
updated: '2026-07-28'
reviewed: '2026-07-28'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'project-standards'
  - 'mcp'
  - 'protocol'
  - 'sdk'
  - 'clients'
  - 'evidence'
aliases:
  - 'MCP Evidence Matrix'
  - 'MCP Protocol SDK Client Matrix'
related:
  - 'docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md'
  - 'docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md'
  - 'docs/plans/2026-07-24-project-standards-mcp-server-plan.md'
  - 'docs/research/2026-07-07-project-standards-mcp-specification-reference-pack.md'
  - 'docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md'
  - 'docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md'
source:
  - 'https://blog.modelcontextprotocol.io/posts/2026-07-28/'
  - 'https://modelcontextprotocol.io/specification/2026-07-28/changelog'
  - 'https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio'
  - 'https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization'
  - 'https://modelcontextprotocol.io/specification/2026-07-28/basic/lifecycle'
  - 'https://modelcontextprotocol.io/specification/2026-07-28/server/resources'
  - 'https://pypi.org/pypi/mcp/json'
  - 'https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0'
  - 'https://py.sdk.modelcontextprotocol.io/v1/'
  - 'https://code.claude.com/docs/en/mcp.md'
  - 'https://learn.chatgpt.com/docs/extend/mcp?surface=cli'
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Standards MCP Protocol, SDK, and Client Evidence Matrix

## Purpose

This document is the final Step 09 official-source, license, conformance, and client evidence register for `SPEC-RD01` and `SPEC-MS01` task T1. It supersedes the pre-publication baseline recorded in the [MCP specification reference pack](2026-07-07-project-standards-mcp-specification-reference-pack.md), which deliberately did not preselect a not-yet-final protocol or SDK release.

Every external fact below was verified on 2026-07-28 against the cited primary source, twice: once by an independent researcher and once by a fresh-context adversarial verifier re-fetching the same sources. One qualification: the attributions to the lifecycle and resources pages were corrected after that review as a citation reassignment of facts already verified twice, not as a fresh fetch of those two pages (see the Revision History). Version-sensitive claims about the protocol, the SDK, and the two installed clients belong here; the ADRs and specifications cite this register rather than restating it.

Decisions frozen against this evidence are recorded in [ADR 0025](../adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md) and [ADR 0026](../adr/adr-0026-project-standards-mcp-local-read-only-transport.md).

---

## Protocol register

### Final publication

MCP revision `2026-07-28` is final, not a release candidate. The release announcement at <https://blog.modelcontextprotocol.io/posts/2026-07-28/> states: "Today, we're officially pushing the release button on the next version of the MCP specification, 2026-07-28" and "All four Tier 1 SDKs speak 2026-07-28 as of today."

The normative change summary against the prior stable revision `2025-11-25` is published at <https://modelcontextprotocol.io/specification/2026-07-28/changelog>.

### Changes material to a local read-only stdio server

| Change | Source expectation | Consequence for this server |
| --- | --- | --- |
| Sessions removed (SEP-2567); the `initialize` / `notifications/initialized` handshake removed and the per-request protocol version and capabilities moved into `_meta`, with `UnsupportedProtocolVersionError` (SEP-2575) | <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | The server must be stateless per request and must not rely on initialize-time session state. |
| `server/discover` RPC is mandatory (SEP-2575) | <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | Discovery must be answered for every 2026-07-28 client; the selected SDK serves it. |
| `resultType` is required on all results (SEP-2322) | <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | Result envelopes are protocol-owned and must be produced by the SDK, not hand-assembled. |
| `ttlMs` and `cacheScope` are required on `tools/list`, `prompts/list`, `resources/list`, `resources/read`, and `resources/templates/list` (SEP-2549) | <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | Every listing and read response carries revision-specific cache metadata; the adapter must not emit listings outside the SDK. |
| `resources/subscribe` and `resources/unsubscribe` replaced by `subscriptions/listen` (SEP-2575) | <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | Subscription surface differs per revision; a server that declares no subscription support is unaffected in both eras. |
| Resource-not-found error code changed from `-32002` to `-32602`, with clients that SHOULD still accept `-32002`; `-32001` renumbered to `-32020`, `-32003` to `-32021`, and `-32004` to `-32022` | <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | Not-found and other structured errors must be raised through the SDK so the correct per-revision code is emitted. |
| Roots, Sampling, and Logging deprecated (SEP-2577) with a window of at least 12 months and removal no earlier than 2027-07-28; `ping`, `logging/setLevel`, and `notifications/roots/list_changed` removed; MRTR replaces server-initiated requests (`roots/list`, `sampling/createMessage`, `elicitation/create`) (SEP-2322) | <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | A design that depends on client roots, sampling, or protocol logging is on a removal path; the server must not require any of them. |
| Authorization is HTTP-only: "Implementations using an STDIO transport SHOULD NOT follow this specification, and instead retrieve credentials from the environment" | <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization> | A local stdio server implements no MCP authorization flow and takes any credentials it needs from the environment. |

The stdio transport framing is unchanged: newline-delimited JSON-RPC on stdout with logs on stderr, with per-request version and capabilities carried inline in `_meta`. The revision states that "The server MUST NOT write JSON-RPC requests to stdout"; under MRTR a server replies with `InputRequiredResult` instead of calling the client. Source: <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio>.

Additive changes recorded for completeness: an `extensions` field on `ClientCapabilities` and `ServerCapabilities`; OpenTelemetry `_meta` trace-context conventions (SEP-414); a SHOULD for deterministic `tools/list` ordering; `inputSchema` and `outputSchema` loosened to full JSON Schema 2020-12 (SEP-2106); HTTP-only authorization changes (RFC 9207 `iss`, `application_type`, CIMD replacing DCR); and tasks moved to the `io.modelcontextprotocol/tasks` extension (SEP-2663). Deprecated alongside Roots, Sampling, and Logging: the HTTP+SSE transport and `includeContext` values `thisServer` and `allServers`. SSE resumability and `Last-Event-ID` were removed (SEP-2575).

### Dual-era serving is required

The versioning compatibility matrix on the lifecycle page records that a legacy client against a modern-only server fails, while dual-era servers may implement both eras. Source: <https://modelcontextprotocol.io/specification/2026-07-28/basic/lifecycle>.

Custom URI schemes remain legal. The resources page states: "This list is not exhaustive—implementations are always free to use additional, custom URI schemes." Source: <https://modelcontextprotocol.io/specification/2026-07-28/server/resources>.

This is not theoretical for this project. Codex CLI 0.145.0 speaks `2025-06-18` only (see the client matrix below), so a server that offers `2026-07-28` alone fails against the released Codex build. Dual-era serving through the official SDK is therefore mandatory rather than optional.

---

## SDK register

### Distribution facts

| Fact | Value | Source |
| --- | --- | --- |
| Latest stable distribution | `mcp` 2.0.0 | <https://pypi.org/pypi/mcp/json> |
| PyPI upload timestamp | 2026-07-28T13:45:28Z (wheel `mcp-2.0.0-py3-none-any.whl`) | <https://pypi.org/pypi/mcp/json> |
| GitHub tag publication | v2.0.0 published 2026-07-28T13:41:36Z | <https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0> |
| License | MIT — PyPI classifier `OSI Approved :: MIT License`; repository `LICENSE` reads "MIT License / Copyright (c) 2024 Anthropic, PBC" | <https://pypi.org/pypi/mcp/json>, <https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0> |
| `requires-python` | `>=3.10`; this repository targets 3.14, so the constraint is satisfied | <https://pypi.org/pypi/mcp/json> |

### Direct dependencies

From the PyPI `requires_dist` metadata for `mcp` 2.0.0 (<https://pypi.org/pypi/mcp/json>): `anyio>=4.9` (`>=4.10` on Python 3.14 and later), `httpx2>=2.5.0`, `jsonschema>=4.20.0`, `mcp-types==2.0.0`, `opentelemetry-api>=1.28.0`, `pydantic>=2.12.0`, `pyjwt[crypto]>=2.10.1`, `python-multipart>=0.0.9`, `pywin32>=311` (Windows only), `sse-starlette>=3.0.0`, `starlette>=0.27` (`>=0.48.0` on Python 3.14 and later), `typing-extensions>=4.13.0`, `typing-inspection>=0.4.1`, and `uvicorn>=0.31.1` (non-Emscripten). Extras: `[cli]` adds `python-dotenv` and `typer`; `[rich]` adds `rich`.

The register fact is that every dependency listed above, other than the Windows-only `pywin32` and the non-Emscripten-only `uvicorn` marker, installs unconditionally: the metadata declares no stdio-only subset and no `http` extra. Which of those entries constitute an HTTP stack is an **author assessment**, not a register fact, derived from the documented upstream purpose of each distribution: `httpx2` (HTTP client), `starlette` and `sse-starlette` (ASGI framework and server-sent events), `uvicorn` (ASGI server), `python-multipart` (HTTP form parsing), and `pyjwt[crypto]` (HTTP authorization tokens). Under that assessment a stdio-only deployment installs an HTTP surface it never executes. The full transitive surface is covered by `uv run pip-audit` at T1.4 and T1.6 regardless of how it is classified.

The only Pydantic statement in the release metadata is the `pydantic>=2.12.0` pin; there is no additional prose constraint. This repository already uses Pydantic 2.

### v2.0.0 capabilities

Quotes from the v2.0.0 release notes and README (<https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0>):

- "supports the 2026-07-28 revision of the Model Context Protocol and serves every earlier revision from the same server" — this is the dual-era serving property the client evidence requires.
- "over Streamable HTTP and stdio, with nothing to configure" — stdio is a first-class supported transport in the same server object.
- "stdio servers keep handler subprocesses and stray prints off the wire" — stdout is diverted to stderr while serving, which protects the protocol channel from handler output.
- "FastMCP is now MCPServer" — the server API is `MCPServer`, and the low-level `Server` is rebuilt on a shared dispatcher. A unified `Client` class is provided.
- "At 2026-07-28 the server can no longer call the client, so tools return the question instead" — MRTR replaces server-initiated requests.

### v1 line

`mcp` 1.29.0 was released 2026-07-28T13:41:40Z. The release states that "v1.x is in maintenance mode and will only receive security fixes from now on", with pin guidance `mcp>=1.28,<2` for projects that do not migrate; v1 documentation remains at <https://py.sdk.modelcontextprotocol.io/v1/>. Official `2026-07-28` support is delivered in v2.0.0, whose release notes carry the revision statement quoted above; the register records no documented `2026-07-28` support for the v1 line.

---

## Client matrix

Both clients are the builds installed on this workstation on 2026-07-28. Claude Code facts are from <https://code.claude.com/docs/en/mcp.md>; Codex CLI facts are from <https://learn.chatgpt.com/docs/extend/mcp?surface=cli> and from the released source at tag `rust-v0.145.0`.

| Capability | Claude Code 2.1.220 | Codex CLI 0.145.0 |
| --- | --- | --- |
| Transport configuration | Managed through the `claude mcp` CLI; the probe below shows both stdio and HTTP servers connected | `~/.codex/config.toml` under `[mcp_servers.<id>]`, managed through `codex mcp {list,get,add,remove,login,logout}`; documentation lists stdio, Streamable HTTP, and server instructions as the supported features |
| Tools | Yes; tool results are bounded by the output limits row below | Yes; `list_tools` and `call_tool` implemented in `codex-rs/rmcp-client/src/rmcp_client.rs` at `rust-v0.145.0` |
| Resources | Yes; referenced as `@server:uri` mentions with autocompletion, and built-in tools can list and read MCP resources | `list_resources` and `read_resource` exist in the client source, but model-initiated resource access is not established at 0.145.0 |
| Resource templates | Not recorded in the evidence register | `list_resource_templates` implemented in the client source |
| Prompts | Yes; exposed as `/mcp__<server>__<prompt>` commands | No prompts capability found in the client source at `rust-v0.145.0` |
| Roots | Yes; answers `roots/list` with the launch directory plus additional directories and sends `notifications/roots/list_changed` from v2.1.203, so the installed 2.1.220 qualifies | No roots capability in the client source |
| Sampling | Not implemented and undocumented; open feature request `anthropics/claude-code#1785` | No sampling capability in the client source |
| Elicitation | Yes | Yes; `ClientCapabilities` sets elicitation |
| Negotiated protocol revision | Not documented; behaviour against a 2026-07-28-only server is unstated | Hardcodes `InitializeRequestParams ... with_protocol_version(ProtocolVersion::V_2025_06_18)`, so it speaks `2025-06-18` only. 2026-07-28 support (`mcp_2026_*.rs` tests, `server/discover`, MRTR) exists only on unreleased `main` and is absent at tags `rust-v0.145.0` and `rust-v0.146.0-alpha.14`, verified through full tree listings |
| Startup and tool timeouts | Startup timeout 30s (`MCP_TIMEOUT`); stdio idle timeout 30 minutes; auto-background after 2 minutes from v2.1.212 | `startup_timeout_sec` default 10s; `tool_timeout_sec` default 60s. Author assessment: client-side tool timeouts are client-owned configuration, so a composite tool that performs several provider invocations against a large consumer set can exceed 60 seconds and consumers may need to raise `tool_timeout_sec` accordingly |
| Output limits | Tool-result warning at 10k tokens and a 25k default cap (`MAX_MCP_OUTPUT_TOKENS`) | Not recorded in the evidence register |

### Executable probes and results

Recorded on this workstation on 2026-07-28:

```text
  $ claude --version            -> 2.1.220 (Claude Code)
  $ codex --version             -> codex-cli 0.145.0
  $ claude mcp list             -> health check passes; stdio servers (context7, brave-search) "✔ Connected",
                                   HTTP server (Notion) "✔ Connected"
  $ codex mcp list              -> exit 0; stdio servers (basedpyright-lsp, brave-search, serper-search, tavily-mcp)
                                   enabled; HTTP servers (context7, openaiDeveloperDocs) enabled
```

---

## Required fallbacks

These three fallbacks are frozen by the client evidence above and are not implementer options.

| Fallback | Status | Evidence |
| --- | --- | --- |
| A `standard_read` read tool that returns the same bytes a resource read would return | REQUIRED | Codex CLI 0.145.0 has `read_resource` in its client source, but model-initiated resource access is not established at that release. Without the tool, Codex users have no path to standard content. |
| An explicit `repo_root` argument on every repository-scoped tool | REQUIRED | Codex CLI 0.145.0 advertises no roots, and revision 2026-07-28 deprecates Roots (SEP-2577) with removal no earlier than 2027-07-28. The server cannot depend on a client-supplied root in either client. |
| Prompts exposed only where they are useful | REQUIRED | Claude Code 2.1.220 surfaces prompts as `/mcp__<server>__<prompt>` commands; no prompts capability is present in the Codex CLI 0.145.0 client source. Prompts are therefore an additive Claude Code affordance, never a required access path. |

---

## Conformance and selection statement

The selected pair is protocol revision **2026-07-28**, served dual-era, through the official Python SDK pinned exactly at **`mcp==2.0.0`**.

- Protocol conformance rests on the SDK: v2.0.0 "supports the 2026-07-28 revision of the Model Context Protocol and serves every earlier revision from the same server", which is the recorded way to satisfy both the final revision and Codex CLI 0.145.0's `2025-06-18`-only client in one server process.
- The license is MIT and reviewed; `requires-python >=3.10` is satisfied by this repository's 3.14 target.
- Selection of a prerelease protocol revision or a prerelease SDK build is prohibited. The v1 line is excluded because it is in maintenance mode receiving security fixes only, and official `2026-07-28` support is delivered in v2.0.0.
- This selection is the candidate answer to `SPEC-RD01 OQ-001` and `SPEC-MS01 OQ-001` and is **pending recorded owner approval**. Until that approval is recorded, no MCP dependency is added to `pyproject.toml`.

---

## Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 0.2 | 2026-07-28 | Claude | Post-review corrections: reattributed the dual-era compatibility facts to the lifecycle page and the custom-URI-scheme quote to the resources page and added both sources; restated the SDK v1 line as maintenance-mode with no documented 2026-07-28 support instead of asserting non-support; labelled the HTTP-stack grouping an author assessment distinct from the register's unconditional-installation fact; labelled the Codex client-timeout guidance an author assessment; and changed the Claude Code resource-templates and Codex output-limits cells to 'not recorded in the evidence register'. |
| 0.1 | 2026-07-28 | Claude | Initial Step 09 evidence register: final 2026-07-28 protocol, `mcp==2.0.0` SDK, Claude Code 2.1.220 and Codex CLI 0.145.0 client matrix, executable probes, required fallbacks, and the pending-approval selection statement. |
