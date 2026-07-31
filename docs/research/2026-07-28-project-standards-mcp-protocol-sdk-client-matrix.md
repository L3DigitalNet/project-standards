---
schema_version: '1.1'
id: 'research-mcp728-project-standards-mcp-protocol-sdk-client-matrix'
title: 'Project Standards MCP Protocol, SDK, and Client Evidence Matrix'
description: 'Final Step 09 official-source, license, conformance, and client evidence register for the Project Standards MCP protocol, SDK, and client selection.'
doc_type: 'research'
status: 'active'
created: '2026-07-28'
updated: '2026-07-31'
reviewed: '2026-07-31'
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

## T11 candidate-wheel client smoke (2026-07-30)

`TC-T11-002`. Everything below was produced against one candidate wheel and nothing else. The first candidate raised the finding recorded at the end of this section; once that defect was corrected in its owning task the whole smoke was re-run, and every result here is the corrected candidate's. The client matrix above is the T1 register and is **not** amended here: `codex-cli` moved 0.145.0 → 0.146.0, but 0.146.0 registers `mcp_2026_07_28` disabled by default, so every recorded value — protocol revision `2025-06-18`, no roots, no prompts, model-initiated resource access not established — still holds and the owner-authorized refresh condition (a default-on flag) did not occur.

### Candidate identity

| Fact | Value |
| --- | --- |
| Wheel | `project_standards-5.11.0-py3-none-any.whl` |
| SHA-256 | `8ed0b2e8838fcc67a13bc62a82b52791e5b6b37104b7494c8dad16d04b17e07f` |
| Reported version | `project-standards 5.11.0` |
| Invocation | `project-standards mcp` (console script `project-standards = project_standards.cli:main`) |
| Runtime | the extracted wheel only, on `PYTHONPATH`; no other distribution was importable |
| Final commit | `4d2ece9` |

The superseded first candidate — `ed01ce3939b3312247303bde51fc6ad7685f51537d2f87bbba3ac61efd0bd4ff`, built before the provider-dispatch correction — is retained only as the identity of the run that raised the finding below. Every result on this page is the current candidate's.

### Smoke set (`SPEC-MS01 OQ-005`, owner decision 2026-07-30)

| Target | Identity | Role |
| --- | --- | --- |
| Fixture | `tests/fixtures/package_contract/valid/full` | Mandatory fixture leg; uninitialized control plane |
| This repository | `/home/chris/projects/project-standards` | Initialized V5 consumer |
| Real consumer | `/home/chris/scripts` | Low-risk L3Digital consumer, read-only |

Nothing was written to any target. Every repository-scoped call passed an explicit absolute `repo_root`; no target was inferred, and a relative path is refused with `-32602 the repository root must be an absolute path`.

### Server-side observations (all three eras, one process each)

| Observation | `2025-06-18` (Codex era) | `2025-11-25` | `2026-07-28` |
| --- | --- | --- | --- |
| Negotiated | `2025-06-18` | `2025-11-25` | `2026-07-28` (`server/discover`) |
| serverInfo | `project-standards` 5.11.0 | same | same, in `_meta` |
| Capabilities | resources (`subscribe` false, `listChanged` false), tools (`listChanged` false) | same | same |
| Instructions | 727 characters | 727 | present |
| Tools | 6: `drift_check`, `reconcile_preview`, `repo_inspect`, `standard_read`, `standards_list`, `validate_repo` | same 6 | same 6 |
| Resources | 53 registered | 53 | 53 |
| Resource templates | both parameterized forms | same | same |
| Prompts | `prompts/list` → `-32601 Method not found` | same | same |
| Roots | probe advertised none; every repository-scoped call still resolved its target from the explicit `repo_root` | same | same |
| stdout | JSON-RPC frames only | same | same |
| stderr | 0 bytes | 0 | 0 |

Fallback exercise: `standard_read` returned `standards://adr/1.1/resources/adopt` with its declared digest, media type, and bytes — the required fallback for a client without model-initiated resource access. `resources/read` on `standards://catalog/5` returned the same catalog projection, confirming the two paths agree.

### Repository-scoped tool results (`2025-06-18` process, explicit absolute roots)

| Tool | `tests/fixtures/package_contract/valid/full` | `/home/chris/projects/project-standards` | `/home/chris/scripts` |
| --- | --- | --- | --- |
| `repo_inspect` | state `uninitialized`, 1 finding | state `initialized`, 0 findings | state `initialized`, 0 findings |
| `reconcile_preview` | no preview: control plane uninitialized, 1 finding | 38 planned actions, nothing applied | 30 planned actions, nothing applied |
| `validate_repo` | `-32602 control-plane state is uninitialized` | 10 provider results, all `completed`, 240 findings | 5 provider results, all `completed`, 44 findings |
| `drift_check` | `-32602 control-plane state is uninitialized` | fingerprint `72f1d3a8…`, 1 provider result `completed` | fingerprint `7044b1a3…`, 1 provider result `completed` |

Every composite provider is dispatched with the same authoritative typed input the CLI builds for it, so these are answers and not artifacts of an empty payload. On this repository the ten selected providers are `adr@1.3/validate-adr`, `agent-handoff@1.6/validate` (the 240-finding corpus) and `agent-handoff@1.6/verify`, `cli-documentation@1.5/verify-workflow`, `markdown-frontmatter@1.6/validate-frontmatter`, `markdown-tooling@1.10/verify-format` and `verify-lint`, `project-spec@1.5/validate` and `lint`, and `python-tooling@1.10/verify-toolchain`; on `/home/chris/scripts` the five are `agent-handoff@1.6/validate` (42 findings) and `verify`, `markdown-frontmatter@1.6/validate-frontmatter`, and `markdown-tooling@1.10/verify-format` and `verify-lint` (1 finding each). The uninitialized-fixture refusals are the declared containment path, not a provider failure.

### Client-side probes (scoped configuration only)

Neither client's persistent configuration was written, and neither supplied the `project-standards` server definition: Codex read a throwaway `CODEX_HOME`, and Claude Code read a throwaway project directory carrying only `.mcp.json`, which is the scope it reports back. Claude Code additionally lists the user's own globally configured servers, which are unrelated to this evidence. Both throwaway trees were deleted afterwards; `~/.codex/config.toml` was md5-identical before and after, `~/.claude.json` gained no project entry for the throwaway path, and its root `mcpServers` set was unchanged.

```text
  $ project-standards --version                        -> project-standards 5.11.0 (candidate bytes only)
  $ codex --version                                    -> codex-cli 0.146.0
  $ CODEX_HOME=<temp> codex mcp list                   -> exit 0; project-standards | project-standards | mcp | enabled
  $ CODEX_HOME=<temp> codex mcp get project-standards  -> exit 0; enabled: true, transport: stdio,
                                                          command: project-standards, args: mcp
  $ claude --version                                   -> 2.1.220 (Claude Code)
  $ claude mcp list        (cwd = <temp project>)      -> exit 0; project-standards: project-standards mcp - ✔ Connected
  $ claude mcp get project-standards                   -> Scope: Project config (shared via .mcp.json); Status: ✔ Connected
```

Claude Code's health check performs a real stdio handshake, so `✔ Connected` is a live connection to the candidate wheel's server, not a configuration echo. Under a `CODEX_HOME` below `/home/chris/tmp`, `codex mcp` prints one warning to stderr — it refuses to create PATH helper binaries under a directory it treats as temporary — and then completes normally with exit 0.

### Finding raised by this smoke

**Historical, 2026-07-30 — raised by the first candidate, corrected before the results above were recorded.** The record is kept because it is what this client gate was for; it does **not** describe the current server.

On the first candidate (`ed01ce39…`), `validate_repo` failed against every **real** consumer repository. The composite service dispatched each applicable validate/verify/lint provider with an empty snapshot object, while the packaged providers require the document snapshots the CLI builds for them:

```text
  validate_repo  /home/chris/projects/project-standards -> -32602 provider failed with ValueError
                                                           (adr@1.3/validate-adr)
  validate_repo  /home/chris/scripts                    -> -32602 provider failed with ValueError
                                                           (markdown-frontmatter@1.6/validate-frontmatter)
```

Root cause, reproduced directly at the time: `payloads/adr/1.3/providers/adr.py` raised `ValueError: snapshots.documents must be an array` because the composite dispatch passed `{}` where `frontmatter_commands.py` builds `{"documents": …}` for the same provider. The existing provider tests used a synthetic echo provider that tolerates any snapshot object, which is why no suite caught it. The follow-up analysis widened the finding beyond the two crashes this smoke saw: of eleven providers reachable on this repository, four crashed and at least one more — `agent-handoff@1.6/validate` — returned a _different, wrong_ answer from empty input, so every composite answer was untrustworthy rather than merely incomplete.

It was a service-layer defect, not a packaging or documentation defect: source and extracted-wheel behaviour were identical, so the wheel-equivalence contract was never affected. It was routed out of the documentation task to its owning work and fixed there — `75c9653` published the provider-dispatch-input authority seam and `1abf8d9` made composite dispatch use that authoritative typed input, with per-provider failure isolation so one incompatible provider can no longer abort a whole call. The refreshed run above is against the post-fix candidate.

---

## T12 final-gate re-probe (2026-07-31)

`TC-T12-002`. The final gate built one fresh candidate wheel and ran §13 against only those bytes. **The final candidate is byte-identical to the T11 candidate** — SHA-256 `8ed0b2e8838fcc67a13bc62a82b52791e5b6b37104b7494c8dad16d04b17e07f`, the same digest recorded in the Candidate identity table above. Every commit between T11 and this gate touched `docs/` only, and `docs/` is not packaged, so no product byte changed. This section therefore records a re-probe of the frozen commands rather than any new behavioural claim, and the T1 register above is **not** amended.

### Frozen probes re-executed verbatim

Copied verbatim from the "Executable probes and results" table. All four are read-only.

| # | Command | Exit | Result on 2026-07-31 |
| --- | --- | --- | --- |
| 1 | `claude --version` | 0 | `2.1.220 (Claude Code)` — unchanged from the T1 register |
| 2 | `codex --version` | 0 | `codex-cli 0.146.0` — 0.145.0 in the T1 register; the 0.146.0 assessment is already dispositioned (the `mcp_2026_07_28` flag still ships disabled by default, so the authorized refresh condition did not occur) |
| 3 | `claude mcp list` | 0 | health check passes; every configured server reports `✔ Connected` (2 stdio, 3 HTTP). Server URLs are **not** reproduced here — one carries an API key in its query string, and this page is a tracked, publicly mirrored document |
| 4 | `codex mcp list` | 0 | exit 0; 4 stdio servers `enabled`, 1 `disabled`, 2 HTTP servers `enabled` |

The client inventories differ from the 2026-07-28 register because the workstation's own unrelated MCP servers changed in the interim. That is environment drift, not a protocol or client-capability change: no recorded protocol revision, roots behaviour, prompts behaviour, or resource-access fact moved, so no frozen row is amended.

### Candidate server observed under the final wheel

One process, launched from the extracted candidate runtime only.

| Observation | Value |
| --- | --- |
| `serverInfo` | `{"name": "project-standards", "version": "5.11.0"}` |
| Negotiated revision | `2025-06-18` (the Codex-era opening contract) |
| Advertised capabilities | `experimental {}`, `resources {listChanged: false, subscribe: false}`, `tools {listChanged: false}` |
| `tools/list` | exactly six, all read-only: `drift_check`, `reconcile_preview`, `repo_inspect`, `standard_read`, `standards_list`, `validate_repo` |
| `resources/list` | 53 entries |
| `prompts/list` | `-32601 Method not found` — the prompts capability is truthfully absent because no prompt-role resource is approved |
| `tools/call standards_list` | `isError: false`; structured content carries `catalog_major` and `standards` |
| stdout | pure JSON-RPC on every line |
| stderr | empty for the whole session |

This satisfies the §13 discovery inspection: capabilities equal registrations, and no mutating, apply, recommendation, logging, or remote surface is reachable.

### Persistent client configuration

Neither persistent configuration was written. Before the probes, the Claude global `mcpServers` mapping held `brave-search`, `serper-search`, and `tavily`, and the Codex `mcp_servers` table held `basedpyright-lsp`, `brave-search`, `context7`, `lsp-typescript`, `openaiDeveloperDocs`, `serper-search`, and `tavily-mcp`. **Neither contained a `project-standards` entry before the gate and neither gained one.** The candidate server was exercised from an isolated throwaway directory with its own `CODEX_HOME`, never through a registered client entry.

One honest limitation on the wording: `~/.claude.json` is continuously rewritten by the running Claude Code harness for unrelated session state, so a whole-file checksum cannot prove "untouched" and none is claimed. The precise provable claim is the one made above — the `mcpServers` mapping is unchanged and gained no `project-standards` entry.

---

## v5.12.0 release-gate re-probe (2026-07-31)

The v5.12.0 release train (version bump plus the owner-approved thirteen-issue roll-in, including three new default payload versions) rebuilt the candidate, so the release-gate re-ran the §13 regression set against the new wheel. The MCP service layer and the provider-dispatch-input seam are byte-identical to the `4d2ece9` baseline (`git diff 4d2ece9..23daf49 -- src/project_standards/mcp_services/ src/project_standards/control_plane/provider_inputs.py` is empty); what changed underneath the server is the payload set it serves.

### Candidate identity

| Fact          | Value                                                               |
| ------------- | ------------------------------------------------------------------- |
| Wheel         | `dist/project_standards-5.12.0-py3-none-any.whl`                    |
| SHA-256       | `766a155434a68d86dd43c6c0060abe64f838e6979a8ab02721d5b1f75d2a3986`  |
| Source commit | `23daf49` (`testing`, release-prep tip)                             |
| Verdict       | **NO-REGRESSIONS** versus the T12 baseline `8ed0b2e8…` at `4d2ece9` |

### Candidate server observed under the release wheel

| Observation | 2025-06-18 / 2025-11-25 eras | 2026-07-28 era |
| --- | --- | --- |
| `serverInfo` | `{"name": "project-standards", "version": "5.12.0"}` | same, carried in `_meta["io.modelcontextprotocol/serverInfo"]` per the frozen contract |
| Capabilities | `experimental {}`, `resources {listChanged: false, subscribe: false}`, `tools {listChanged: false}` | identical |
| `tools/list` | the same six read-only tools as T12 | identical |
| `resources/list` | 56 entries — exactly +3 over T12's 53, the three new payload versions | identical |
| `prompts/list` | `-32601 Method not found` | identical |
| stdout / stderr | pure JSON-RPC, empty stderr, exit 0 | identical |

### New default payloads through composite dispatch

The three payload successors that v5.12.0 activates (`markdown-frontmatter 1.7`, `markdown-tooling 1.11`, `agent-handoff 1.7`) are demonstrably the versions dispatched, and they reproduce the T11 baseline corpora exactly: this repository yields 10 provider results, all `completed`, with the identical 240-finding agent-handoff validate corpus; `~/scripts` yields its baseline 42. The `TC-T14-004` canary passes with the new defaults, and the MCP↔CLI parity check matches action-kind histograms exactly on both real roots (`38 {no-op: 25, preserve: 13}` here; `30 {no-op: 11, preserve: 11, update: 8}` for `~/scripts`, whose `update` set is that consumer's own not-yet-upgraded drift, reported identically by both surfaces). Reconciliation fingerprints moved on both roots, as they must when the resolved payload set changes; both surfaces agree on the new values' consequences.

### Frozen probes re-executed verbatim

All four probes exit 0: `claude --version` → `2.1.220 (Claude Code)`; `codex --version` → `codex-cli 0.146.0`; both `mcp list` commands enumerate only the user's own servers. No frozen T1 matrix row moves. The Claude inventory shifted to three stdio and two HTTP entries — the same unrelated-workstation-drift class the T12 re-probe already dispositioned. **Neither persistent client configuration contained a `project-standards` entry before the gate and neither gained one**; the candidate was exercised from an isolated throwaway directory with its own `CODEX_HOME`, with the same `~/.claude.json` provability caveat recorded by the T12 entry.

---

## Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 0.6 | 2026-07-31 | Claude (v5.12.0 release gate) | Append the v5.12.0 release-gate re-probe: new candidate wheel `766a1554…` at release-prep tip `23daf49`, NO-REGRESSIONS verdict, byte-identical MCP service layer since `4d2ece9`, the 5.12.0 version surface on all three eras, resources 53→56 for the three new default payloads, composite-dispatch corpus parity (240/42) with the moved reconciliation fingerprints dispositioned, and the four frozen probes at exit 0 with no persistent-configuration changes. |
| 0.5 | 2026-07-31 | Claude (T12 final gate) | Append the `TC-T12-002` final-gate re-probe: the freshly built final candidate is byte-identical to the T11 candidate (`8ed0b2e8…`), the four frozen probes re-executed verbatim at exit 0, the candidate server's observed capabilities and six read-only tools under the final wheel, and the persistent-client-configuration disposition. Client inventories moved with unrelated workstation changes, so no frozen T1 row is amended. Server URLs are deliberately not reproduced because one carries an API key and this page is tracked and publicly mirrored. |
| 0.4 | 2026-07-30 | Claude (T11 client gate, refresh) | Re-run the whole `TC-T11-002` smoke against the post-fix candidate `8ed0b2e8…`: new wheel digest, the fixture leg exercised with an absolute root, repository-scoped results for all six tools on both real roots (10 and 5 provider results, all `completed`), and precise client-scope wording. The `validate_repo` empty-input finding is retained as a dated historical record of the discovery and its routing to `75c9653`/`1abf8d9`, not as current behaviour. |
| 0.3 | 2026-07-30 | Claude (T11 client gate) | Append the `TC-T11-002` candidate-wheel client smoke: wheel digest and invocation, the owner-approved `OQ-005` smoke set, three-era server observations, scoped Codex 0.146.0 and Claude Code 2.1.220 probes, and the `validate_repo` empty-snapshot finding. The T1 client matrix is unchanged; 0.146.0 keeps `mcp_2026_07_28` disabled by default, so the authorized refresh condition did not occur. |
| 0.2 | 2026-07-28 | Claude | Post-review corrections: reattributed the dual-era compatibility facts to the lifecycle page and the custom-URI-scheme quote to the resources page and added both sources; restated the SDK v1 line as maintenance-mode with no documented 2026-07-28 support instead of asserting non-support; labelled the HTTP-stack grouping an author assessment distinct from the register's unconditional-installation fact; labelled the Codex client-timeout guidance an author assessment; and changed the Claude Code resource-templates and Codex output-limits cells to 'not recorded in the evidence register'. |
| 0.1 | 2026-07-28 | Claude | Initial Step 09 evidence register: final 2026-07-28 protocol, `mcp==2.0.0` SDK, Claude Code 2.1.220 and Codex CLI 0.145.0 client matrix, executable probes, required fallbacks, and the pending-approval selection statement. |
