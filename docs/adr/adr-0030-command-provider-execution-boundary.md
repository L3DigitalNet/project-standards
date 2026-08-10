---
schema_version: '1.1'
id: 'adr-0030-project-standards-command-provider-execution-boundary'
title: 'ADR 0030: Command Provider Execution Boundary'
description: 'Defines the shared bounded provider runner, command wire ABI, Linux amd64 target, and integrity-preserving executable materialization contract.'
doc_type: 'adr'
status: 'active'
created: '2026-08-10'
updated: '2026-08-10'
reviewed: '2026-08-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'architecture'
  - 'boundary'
  - 'go'
  - 'security'
  - 'standards-platform'
aliases:
  - 'ADR 0030'
  - 'Command provider execution boundary'
related:
  - 'docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md'
  - 'docs/adr/adr-0027-adopt-go-alongside-python-with-neutral-tooling.md'
supersedes: []
superseded_by: null
source:
  - 'https://github.com/L3DigitalNet/project-standards/issues/142'
  - 'docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md'
  - 'docs/adr/adr-0027-adopt-go-alongside-python-with-neutral-tooling.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted:
    - 'Codex'
  informed: []
  amends: []
  amended_by: []
---

# ADR 0030: Command Provider Execution Boundary

MADR status: **accepted** (2026-08-10; owner approval recorded on issue 142).

## Context and Problem Statement

The V2 payload contract already recognizes `command` as a provider kind, but its executable-provider grammar and runtime support only Python. Direct control-plane dispatch compiles and executes trusted Python payload bytes in the caller, while the MCP path adds the bounded worker process required by [ADR 0025](adr-0025-project-standards-mcp-service-and-sdk-boundary.md). Adding a native executable without a common boundary would leave direct calls unbounded or create a second process implementation whose timeout, teardown, caps, and diagnostics could drift.

A command provider also cannot execute bytes in memory. Executing its installed payload path would depend on wheel installers preserving an executable mode and would separate the digest check from the file actually used. The executable needs a defined platform, wire ABI, environment, materialization sequence, and cleanup contract.

This decision governs execution of trusted executable providers from selected V2 payloads through direct control-plane and MCP routes. It applies when the control plane invokes a V2 Python or command provider. It does not govern the MCP SDK or service surface retained by ADR 0025, the repository's language-neutral tooling policy in [ADR 0027](adr-0027-adopt-go-alongside-python-with-neutral-tooling.md), V1 installed-bundle provider dispatch, migration of any production package, additional command platforms, or operating-system sandboxing and privilege restriction.

The child boundary provides bounded execution and transport, not a security sandbox. Selected payload code remains trusted to run with the invoking user's operating-system permissions.

How should the control plane execute providers through one bounded process boundary, and what declaration, platform, wire, environment, and materialization contract should a V2 command provider use?

## Decision Drivers

- Give direct control-plane and MCP calls one owner for timeout, process-group cleanup, result transport, and diagnostics.
- Preserve every accepted ADR 0025 process-boundary guarantee without nesting workers.
- Execute the exact integrity-checked payload bytes rather than an installer-dependent path.
- Make an unsupported host a deterministic pre-spawn refusal rather than an opaque executable-format failure.
- Give command providers the same validated input and declared resource bytes as Python providers without exposing undeclared resources.
- Keep results separate from untrusted `stdout` and `stderr` diagnostics.
- Prevent command providers from inheriting ambient credentials, executable search paths, or other caller environment state.
- Preserve Python provider behavior while moving it into the bounded child.

## Considered Options

- **Use one control-plane-owned bounded runner with a native command ABI** - extract the existing MCP process machinery, route direct and MCP calls through it once, and materialize verified command bytes privately.
- **Keep the status quo and continue refusing command providers** - retain in-process direct Python execution and defer the accepted Go provider direction.
- **Wrap Go provider logic in a Python shim** - keep the Python entrypoint contract and have a shim locate or launch the native executable.
- **Add a separate command-only runner** - retain the MCP-owned Python worker and introduce another subprocess implementation for command providers.

## Decision Outcome

Chosen option: **use one control-plane-owned bounded runner with a native command ABI**.

The control plane owns one provider-neutral subprocess implementation. Direct CLI/control-plane dispatch and MCP services use it exactly once; MCP delegates to the control-plane boundary and must not add a nested worker. ADR 0025 remains authoritative for the MCP SDK, service facade, read-only operation set, and MCP failure isolation. This record carries its accepted process properties into the shared runner.

### Shared bounded runner

Every V2 Python or command invocation runs in a new process group. One invocation is bounded to 30 seconds. On completion, timeout, cancellation, crash, spawn failure, malformed result, or parent-side failure, the parent drains and closes the transport, signals the whole group with `SIGTERM`, escalates surviving processes to `SIGKILL`, reaps the leader, and releases every descriptor and temporary resource. Teardown is unconditional after a successful result as well as after failure, so a descendant cannot survive by retaining an inherited descriptor.

The parent retains at most 8,192 bytes from each of `stdout` and `stderr`, accepts at most 262,144 result bytes, and composes at most 16,384 diagnostic characters. Truncation is explicit and quantified; it is never silent. Fixed failure categories plus bounded, content-safe diagnostics are the public error surface. Raw installed paths, temporary paths, arbitrary exception text, and secret environment values are not republished.

Existing V2 Python providers use a fixed interpreter/bootstrap invocation and write their result through the same result descriptor. To preserve their current semantics, the Python child receives the caller environment plus the runner's exact Python import path. This is a kind-specific compatibility rule for trusted Python payloads and does not permit a command provider to inherit the caller environment. Existing input and output schema checks, resource immutability, typed effects, output notices, declared-live-path integrity checks, and public results remain unchanged.

### V2 command declaration and platform

A V2 command provider declares all of these exact properties:

- `kind = "command"`;
- `entrypoint = "payload:{resource-id}"`, naming exactly one declared payload resource and carrying no `#symbol` fragment;
- `platforms = ["linux/amd64"]`; and
- `mode = "0755"`.

Missing, duplicate, or additional platform entries, any other mode, a symbol fragment, or an undeclared entrypoint resource is invalid. A host outside `linux/amd64` is refused with a stable path-free diagnostic before materialization or spawn.

This portability narrowing is accepted knowingly. The deployed internal consumer population is Linux x86-64, while a package that adopts a command provider no longer has Python's host portability. Python providers remain portable anywhere the supported CLI runs. Adding another command platform requires a separate accepted decision and corresponding reproducible bytes; it is not an exception to this record.

### Command wire ABI

The command process receives no provider data in arguments or environment. The materialized executable is invoked directly, without a shell and without `PATH` lookup. `argv[1]` is the decimal number of one inherited result descriptor.

Standard input is one canonical UTF-8 JSON object with exactly these fields:

- `schema_version`, the string `"1.0"`;
- `input`, the already schema-validated provider input object; and
- `resources`, an object keyed by the IDs in the provider's `resources` list whose values are standard padded Base64 encodings of the exact integrity-checked bytes.

Canonical encoding sorts object keys, uses compact separators, preserves Unicode as UTF-8, and rejects non-finite numbers. Resource IDs are therefore serialized in lexical order. Only IDs in the provider's `resources` list are present; the provider input's resource-digest map continues to identify the same bytes. Malformed JSON, duplicate or unknown fields, malformed Base64, or non-object input is rejected before use.

The command writes exactly one UTF-8 JSON result object to the inherited result descriptor. The result never travels on `stdout` or `stderr`; both streams are untrusted diagnostics. The parent rejects malformed, non-object, duplicate-field, trailing-data, oversized, or otherwise invalid results, then applies the provider's declared output schema and typed-effect validation before publishing anything to the caller.

### Command environment and materialization

The command environment is a closed map constructed by the runner. It contains only explicitly declared locale or runtime values required for deterministic process startup. It never copies the parent environment, includes no `PATH`, and exposes no ambient credential, user configuration, or unrelated runtime variable. Future environment capabilities require an explicit revision of this ABI.

The control plane loads the entrypoint bytes through the selected payload's integrity-checked resource inventory, then performs this order for every invocation:

1. Refuse an unsupported platform before creating executable state.
2. Create a private per-invocation directory.
3. Write the already verified entrypoint bytes to a new file in that directory.
4. Set its mode to exactly `0755`.
5. Rehash the on-disk file and compare it with the manifest digest.
6. Execute that exact temporary path directly.
7. Tear down and reap the complete process group.
8. Remove the file and directory.

The installed payload path is data authority only and is never executed. A mode or digest mismatch fails before spawn. Cleanup covers success, timeout, cancellation, crash, nonzero exit, malformed or schema-invalid result, and spawn failure. Neither a result nor a diagnostic publishes the private path.

The V1 installed-bundle runner remains Python-only and continues to fail closed for `command` and `workflow`. Its module-import contract is separate from V2 integrity-addressed payload execution, and widening it would authorize installed-path execution outside this decision.

### Consequences

- Good, because direct and MCP provider calls share one bounded implementation and one set of process invariants.
- Good, because the file that executes is coupled to the selected payload digest even when wheel installation does not preserve mode bits.
- Good, because unsupported platforms, invalid declarations, untrusted diagnostics, and malformed results fail deterministically before unsafe publication.
- Good, because moving Python dispatch into the child closes the direct path's unbounded execution weakness without changing provider semantics.
- Neutral, because the boundary limits execution and transport but intentionally does not sandbox catalog-trusted code from the invoking user's filesystem or network permissions.
- Bad, because every provider invocation pays process startup and serialization cost.
- Bad, because packages adopting command providers support only `linux/amd64` until another platform receives explicit authority and reproducible bytes.
- Bad, because Python compatibility retains its inherited environment while command providers use a stricter kind-specific environment contract.

### Confirmation

Conformance requires one control-plane-owned runner and source/import tests proving that MCP delegates without a second spawn. Process tests cover the exact timeout and size boundaries plus `N + 1`, result-descriptor isolation, explicit truncation, stable content-safe diagnostics, `SIGTERM`/`SIGKILL`, descendant termination, reaping, descriptor cleanup, cancellation, crash, and every success and failure path.

Declaration and wire tests cover the exact Python and command entrypoint grammars, `linux/amd64`, `0755`, unsupported-host refusal before spawn, canonical input/resource equivalence, strict Base64 and JSON parsing, result-schema and typed-effect validation, and the V1 refusal. Filesystem and environment tests independently prove that the installed resource is not executed, the temporary file has mode `0755` and the expected digest at use time, the private directory disappears after teardown, command children receive no parent canary variable or `PATH`, and Python providers retain existing behavior. A command provider's committed binary must also pass the repository's reproducible Go build gate.

## Pros and Cons of the Options

### Shared bounded runner with a native command ABI

- Good, because one control-plane boundary can be proved once for every caller and supported provider kind.
- Good, because the command contract is independent of Python import mechanics and installer-preserved modes.
- Bad, because extracting the existing MCP machinery changes the execution path for all V2 Python providers and requires exact parity tests.

### Keep the status quo

- Good, because it avoids a new executable ABI and retains broad Python portability.
- Rejected, because the owner sanctioned Go provider logic and accepted the internal population's `linux/amd64` narrowing.
- Bad, because direct provider execution would remain in-process without a deadline, cancellation point, or fault isolation.

### Python shim around native logic

- Good, because manifests could retain the current Python entrypoint shape.
- Rejected, because the owner has a standing preference against Python shim layers and sanctioned Go as the provider-logic direction.
- Bad, because a shim adds another launch and failure layer while obscuring the executable platform and integrity contract.

### Separate command-only runner

- Good, because the existing MCP implementation could remain in its current module.
- Rejected, because duplicated or nested runners can drift in limits, teardown, framing, and diagnostic filtering.
- Bad, because direct Python dispatch would remain unbounded unless a third path were added.

## More Information

- Owner decision and implementation findings: [issue 142](https://github.com/L3DigitalNet/project-standards/issues/142)
- Existing MCP service and process requirements: [ADR 0025](adr-0025-project-standards-mcp-service-and-sdk-boundary.md)
- Neutral Go and Python tooling boundary: [ADR 0027](adr-0027-adopt-go-alongside-python-with-neutral-tooling.md)

Migrating Agent Handoff or another production package is a separate successor decision after this platform boundary is implemented and verified. Revisit this record before adding another platform, changing the command wire or environment, weakening a bound or cleanup rule, executing an installed resource path, or introducing sandboxing or additional privileges.
