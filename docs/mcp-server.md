---
schema_version: '1.1'
id: 'reference-q4m1zt-project-standards-mcp-server'
title: 'Project Standards MCP Server'
description: 'Setup, capability, resource and tool reference, security rules, equivalent CLI/CI commands, and troubleshooting for the local read-only Project Standards MCP server.'
doc_type: 'reference'
status: 'active'
created: '2026-07-30'
updated: '2026-07-31'
reviewed: '2026-07-30'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'mcp'
  - 'reference'
  - 'standards-platform'
aliases: []
related:
  - 'docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md'
  - 'docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md'
  - 'docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md'
  - 'docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Standards MCP Server

`project-standards mcp` serves the installed Catalog 5 standards to a local MCP client over stdio. It is **read-only and local**; the [capability matrix](#capability-matrix) states what it declares on the wire and the [root, read-only, and security rules](#root-read-only-and-security-rules) state what it refuses.

The server is optional and replaces nothing: the CLI and the CI gates remain the enforcement backstop, [related commands](#equivalent-cli-and-ci-commands) reach the same facts without it, and a repository that never starts it is validated exactly the same way.

## Prerequisites

- **Python 3.14 or newer.** The distribution declares `requires-python >=3.14`.
- **The `project-standards` distribution installed into an environment your client can execute.** The MCP SDK (`mcp==2.0.0`) ships as a standard dependency, so no extra is required.
- **One supported primary client.** The evidence register covers Codex 0.146.0 and Claude Code 2.1.220; other MCP clients may work but are not exercised.
- **A consumer repository you want inspected**, if you intend to use the repository-scoped tools. Every one of them takes an explicit absolute path.

## Install and version check

**The MCP server ships in every published release from v5.12.0 onward.** Install the current release from its immutable tag:

```bash
uv tool install "git+https://github.com/L3DigitalNet/project-standards@v5.17.0"
```

Releases before v5.12.0 do not contain the server; on those, `project-standards mcp --help` fails as an unknown command.

### Build and install a candidate (development route)

Working from a checkout, the candidate-wheel procedure is the repository's own, documented under [Developing this repository](../README.md#developing-this-repository):

```bash
uv sync --all-groups
uv run project-standards standards sync-payload-projection --root .
uv build --wheel --out-dir dist
sha256sum dist/project_standards-5.17.0-py3-none-any.whl
uv tool install ./dist/project_standards-5.17.0-py3-none-any.whl
```

Keep that SHA-256. A candidate carries no release identity, so the digest is the only thing that says which bytes your client is talking to; quote it in any bug report about server behaviour.

### Version check

Whichever route you used, confirm that the console script and the server both answer:

```bash
project-standards --version
project-standards mcp --help
```

The version command reports `project-standards 5.17.0`. A candidate built from a checkout reports the same number as the release it is being prepared for, so two candidates built from different commits are told apart only by the wheel digest above. The `mcp` subcommand accepts exactly one launch-time option:

```bash
project-standards mcp --root-boundary /home/chris/projects
```

`--root-boundary` only ever **narrows** which repository roots a tool call may reach. It never supplies a root and never widens one.

A bare `project-standards mcp` is a valid smoke test: the process starts, writes nothing to stdout until a client speaks to it, and exits when stdin closes. Every diagnostic — launch refusals, warnings, SDK logging — goes to `stderr`, because stdout belongs to the protocol from the moment the process starts.

## Client setup

Both supported clients launch the server as a local stdio subprocess. The command is the installed console script and the first argument is the `mcp` subcommand; nothing else is required.

### Codex 0.146.0

Codex keeps MCP servers in `~/.codex/config.toml` under `[mcp_servers.<id>]`, and `codex mcp {list,get,add,remove}` manages the same file:

```toml
[mcp_servers.project-standards]
command = "project-standards"
args = ["mcp"]
```

The file is user-scoped: one entry serves every Codex session. Set `CODEX_HOME` to point the same commands at a different configuration directory.

Verify from any working directory — the entry is not project-scoped:

```bash
codex mcp list
codex mcp get project-standards
```

`get` must report `enabled: true`, `transport: stdio`, `command: project-standards`, and `args: mcp`. It reads the configuration file only; it does not start the server.

Codex negotiates protocol revision `2025-06-18` only — the `mcp_2026_07_28` feature is registered disabled by default at 0.146.0 — and the server serves that revision from the same process. Codex advertises no roots and no prompts, and model-initiated resource access is not established, so use the `standard_read` tool where a resource read would otherwise be natural.

### Claude Code 2.1.220

Claude Code reads a JSON `mcpServers` object. Put it in **`.mcp.json` at the root of the project you want the server available in** — that is project scope, the scope the evidence register's probe used, and the file is shareable with the repository. `claude mcp add --scope project` writes the same file; `--scope user` writes the equivalent entry into `~/.claude.json` instead, which then applies to every project.

```json
{
	"mcpServers": {
		"project-standards": { "command": "project-standards", "args": ["mcp"] }
	}
}
```

Verify **from that project directory**, because a project-scoped server is only visible there:

```bash
claude mcp list
claude mcp get project-standards
```

`list` health-checks each server over a real stdio handshake, so `project-standards: project-standards mcp - ✔ Connected` means the client actually spoke to your build; `get` reports the scope the entry came from. Servers you configured elsewhere are listed alongside it.

Claude Code gives the model direct resource access, surfaces resources as `@server:uri` mentions, and answers `roots/list`. Advertised roots are read as _narrowing_ context only; they never supply the `repo_root` a repository-scoped tool requires.

## Capability matrix

Everything below is what the running server declares on the wire, not an aspiration.

| Surface | Declared | Notes |
| --- | --- | --- |
| Resources | Yes | `subscribe` is false and `listChanged` is false; the registration set is fixed at launch |
| Resource templates | Yes | Two parameterized forms, listed under the resource reference |
| Tools | Yes | Six read-only tools; `listChanged` is false |
| Prompts | No prompt capability is declared | ADR 0026 approves no prompt role, so no prompt handler is registered |
| Roots | Client-advertised only | Read for repository-scoped tools; never a substitute for `repo_root` |
| Sampling and elicitation | Not declared | The server never calls back into the model |
| Remote transport | Not implemented | stdio only; there is no HTTP or SSE entry point |
| Write or apply surface | Not implemented | No tool mutates, and no apply callable is reachable |

## Resource URIs and tool schemas

| Tool | Purpose | Arguments |
| --- | --- | --- |
| `standards_list` | List every installed standard package in Catalog 5 | none |
| `standard_read` | Return the exact bytes of one declared resource | `uri` |
| `repo_inspect` | Report one consumer repository's control-plane state | `repo_root` |
| `reconcile_preview` | Return the dry-run reconciliation plan for one repository | `repo_root` |
| `validate_repo` | Run every applicable read-only validation provider | `repo_root` |
| `drift_check` | Report reconciliation and provider drift facts | `repo_root` |

### Resource URIs

Three URI forms exist and no others. Identifiers appear exactly as the installed catalog declares them: no trailing slash, no uppercase, no nearest-version or case-insensitive recovery.

| Form | Example | Body |
| --- | --- | --- |
| Catalog | `standards://catalog/5` | Compact generation metadata |
| Package | `standards://{standard_id}/{version}` | One exact standard descriptor |
| Payload | `standards://{standard_id}/{version}/resources/{resource_id}` | Declared bytes plus media type |

The two parameterized forms `standards://{standard_id}/{version}` and `standards://{standard_id}/{version}/resources/{resource_id}` are the templates the server advertises. A URI naming a role such as `latest` in the version slot is refused: only exact versions resolve.

### `standards_list`

Takes no arguments; the installed distribution is the only authority.

| Field           | Where  | Meaning                                                  |
| --------------- | ------ | -------------------------------------------------------- |
| `catalog_major` | output | The generation this server serves                        |
| `standards`     | output | Every installed package with its resources and providers |

### `standard_read`

Returns the same descriptor and bytes a resource read returns, for clients that cannot read MCP resources. It accepts declared resource URIs only, never filesystem paths.

| Field | Where | Meaning |
| --- | --- | --- |
| `uri` | input, output | The canonical `standards://` resource URI |
| `media_type` | output | The declared media type of the returned bytes |
| `declaration` | output | The declared resource id, role, digest, standard, and version |

### `repo_inspect`

| Field | Where | Meaning |
| --- | --- | --- |
| `repo_root` | input, output | Absolute path to the consumer repository |
| `state` | output | The repository's authoritative control-plane classification |
| `desired_config` | output | Parsed `.standards/` desired configuration |
| `consumer_catalog` | output | The consumer catalog the repository resolves |
| `central_lock` | output | The recorded lock state |
| `findings` | output | Bounded, typed findings |

### `reconcile_preview`

Plans but never applies.

| Field | Where | Meaning |
| --- | --- | --- |
| `repo_root` | input | Absolute path to the consumer repository |
| `preview` | output | Actions, findings, preconditions, notices, and the next lock |
| `control_plane` | output | Control-plane state returned when the repository cannot be planned |

### `validate_repo`

Providers are selected by the repository's own resolution and cannot be named by the caller, and each is run with the same authoritative input the equivalent CLI command builds for it. A provider that cannot run is reported as its own typed failed result; it never aborts the call or hides the other providers' answers.

| Field       | Where         | Meaning                                           |
| ----------- | ------------- | ------------------------------------------------- |
| `repo_root` | input, output | Absolute path to the consumer repository          |
| `results`   | output        | Typed per-provider status and bounded diagnostics |
| `findings`  | output        | Bounded, typed findings                           |

### `drift_check`

Facts only: no summary verdict, confidence score, or clean-state flag is invented.

| Field | Where | Meaning |
| --- | --- | --- |
| `repo_root` | input, output | Absolute path to the consumer repository |
| `reconciliation_fingerprint` | output | The control plane's own fingerprint |
| `actions` | output | Reconciliation actions the control plane would plan |
| `results` | output | Per-provider drift-check results |
| `findings` | output | Bounded, typed findings |

## Root, read-only, and security rules

- **Every repository-scoped tool takes an explicit absolute `repo_root`.** The server never uses its working directory, never guesses, and never accepts a relative path.
- **`--root-boundary` only narrows.** A repository outside the configured boundary is refused with a structured error; a boundary can never grant access to a root a call did not name.
- **No write surface exists.** No tool applies a plan, and no mutating provider operation is dispatched. `reconcile_preview` is a dry run by construction.
- **Resource bytes are verified on every read** against the digest declared inside the payload, and must come from a regular file inside that payload — a symlinked or swapped file is refused.
- **stdout is the protocol channel.** Diagnostics, warnings, and provider worker output never reach it; everything human-readable goes to `stderr`.
- **The transport is local stdio.** No remote listener, no network capability, and no credential is read.

## Equivalent CLI and CI commands

The server is a convenience, and CI never depends on it. These are the related commands, not a tool-by-tool mapping: no CLI command returns the exact declared resource bytes that `standard_read` and a resource read return, and none is claimed to.

Related package-level commands — inventory and package validation:

```bash
project-standards standards list
project-standards validate
```

Related consumer-control-plane commands — repository state:

```bash
project-standards reconcile --check --repo /path/to/consumer
```

In CI, the repository gate is `.github/workflows/check.yml`, which runs the same validators and package contract checks the tools report. No workflow starts an MCP server.

## Troubleshooting

Every refusal is a structured JSON-RPC error carrying a stable code, a message, and a remediation. The codes below are the ones a client operator meets most often.

| Code | Means | Do |
| --- | --- | --- |
| `installed-distribution-invalid` | The installed distribution failed its eager integrity check at launch | Reinstall from an intact distribution |
| `catalog-invalid` | The requested catalog generation failed validation | Reinstall; a partial catalog is never served |
| `resource-uri-invalid` | The URI is not one of the three canonical forms | Use an exact declared id and version |
| `resource-not-found` | The URI is well formed but names nothing installed | List the catalog first |
| `resource-integrity` | Payload bytes no longer match their declared digest | Reinstall the distribution |
| `repo-root-invalid` | `repo_root` was missing, relative, or unreadable | Pass an absolute path to an existing directory |
| `repo-root-out-of-bounds` | The root lies outside the configured `--root-boundary` | Widen the launch boundary or pass a contained root |
| `tool-arguments-invalid` | An argument was absent or of the wrong type | Check the tool's declared input schema |
| `consumer-services-unavailable` | The facade has no installed distribution to plan against | Run the server from an installed distribution |

If the server appears to start and then die immediately, read `stderr`: a launch refusal prints the message, the code, and the remediation there and exits non-zero without writing to stdout. If a client reports a protocol mismatch, confirm the client's negotiated revision — Codex speaks `2025-06-18` and the server serves it alongside `2026-07-28` from the same process.

## Uninstall or disable

To stop exposing the server without uninstalling anything, delete the `[mcp_servers.project-standards]` table from `~/.codex/config.toml`, or remove the `project-standards` entry from the client's `mcpServers` object, and restart the client. `codex mcp remove` and `claude mcp remove` do the same edit.

To remove the distribution entirely, uninstall it the way you installed it. Nothing in a consumer repository depends on the server: `.standards/` state, the CLI, and the CI workflows are unaffected.
