# Go Migration Assessment

**Assessment date:** 2026-08-01 **Repository state assessed:** `testing` at `06274608`, including the existing uncommitted CLI-contract work **Decision scope:** migrating the Project Standards CLI, runtime, and possibly repository tooling from Python to Go

## Recommendation

Do **not** authorize a repo-wide Go rewrite as a performance, CI, reliability, or file-clutter project. The current evidence does not show that Python is the dominant cause of the repository's expensive work, and a transitional Go host that retains Python providers would add a second runtime and release model without delivering the main operational benefit of a self-contained binary.

Go remains a credible strategic option for a deliberately incompatible v6 if the primary goal is eventually to distribute one fast-starting executable without requiring Python. Before making that commitment, run a bounded, read-only Go pilot against frozen black-box contracts and profile the hosted compatibility lane. The pilot should be abandoned unless it proves both exact behavioral parity and material benefit on representative repository work.

The best immediate performance change is independent of language: split the hosted ordinary and compatibility suites into parallel jobs, while retaining the timing-sensitive performance lane in isolation. The latest inspected green hosted Check took 40:14; its compatibility step took 25:32 and its covered ordinary suite took 13:17. Running those legs concurrently could remove roughly the smaller leg from the critical path, subject to an actual GitHub-hosted benchmark. It would consume more CI minutes and duplicate setup, so it is a separate optimization decision rather than part of a migration.

## Bottom line by objective

| Objective | Expected effect of a complete Go migration | Assessment |
| --- | --- | --- |
| Interactive CLI startup | Strong improvement likely | The current command takes about 0.40 seconds and 45 MiB RSS even for `--version`; this is real user-facing headroom. |
| Hosted CI wall time | Uncertain to modest | Compatibility fixtures, subprocess behavior, wheel installation, repository trees, and filesystem work dominate the observed job. |
| Local gate wall time | Uncertain | Python-side concurrency already reduced the covered gate from 55:31 to 10:23 under load. |
| Lint and format time | Little direct benefit | Ruff is already a fast Rust binary; Prettier and markdownlint remain required for governed Markdown and structured text. |
| Distribution simplicity | Strong only after a clean break | A native binary avoids interpreter and virtual-environment setup, but requires an OS/architecture artifact matrix. |
| File clutter | Worse during transition; limited improvement after completion | A dual-runtime tree adds Go files and release machinery. Standards, schemas, fixtures, and versioned payload data remain regardless of implementation language. |
| Robustness | Mixed | Go removes interpreter-resolution failures and adds useful fuzz/race tooling, but a rewrite risks regressions in byte preservation, parsing, path safety, locking, and diagnostics. |
| Cross-platform support | Mixed | Building binaries is straightforward; reproducing the current POSIX descriptor, symlink, and lock guarantees on every target is not. |
| Long-term maintainability | Potentially better only after Python is retired | A permanent Go host plus Python provider worker is more complex than the current system. |

If the principal motivation is CI speed, stay with Python and optimize the workflow. If the principal motivation is a small, fast, self-contained end-user artifact, investigate Go as a new major-version architecture.

## Current repository surface

The migration is substantially larger than the seven console scripts declared in [`pyproject.toml`](../../pyproject.toml). The unified command exposes 12 top-level command families, several with their own nested command trees. The same domain implementation also serves the MCP process and executable standard providers.

| Area | Python files | Approximate LOC | Migration significance |
| --- | --: | --: | --- |
| Versioned packaged providers | 73 | 36,634 | Historical executable behavior selected by immutable payload versions |
| Control plane | 31 | 18,542 | Planning, migration, recovery, structured-file adapters, locks, and provider execution |
| Root modules and CLI tools | 19 | 6,870 | Unified dispatcher, standalone commands, frontmatter operations, registry, and filesystem helpers |
| Package contract | 16 | 5,543 | Catalog, payload, graph, schema, digest, and release integrity |
| MCP server and services | 14 | 5,216 | stdio transport, service façade, repository access, and provider worker |
| Agent Handoff | 17 | 4,117 | Validation, inspection, upgrade, integration, and legacy fallback |
| Project Specification | 13 | 2,857 | Validate, lint, extract, scaffold, and upgrade operations |
| Standards graph | 6 | 1,426 | Catalog views, selection changes, graph validation, and package command routing |
| Legacy adoption and bundled hooks | 6 | 893 | Compatibility materialization and shipped executable helpers |

The current source tree contains about 195 Python files and 82,098 lines. The test tree contains 225 Python files and 97,303 lines, with 4,412 tests collected in the assessed worktree. Excluding versioned providers and bundled helpers still leaves about 45,000 implementation lines.

Python files are not the repository's main source of file count. The tracked tree contains approximately 498 `.py`, 1,246 `.md`, 762 `.json`, 369 `.toml`, and 309 `.yml` files. Much of the repository is immutable standards content, schemas, examples, fixtures, and retained versions. A language change cannot remove that content.

There is also no narrow public Python library layer that can be swapped out behind the CLI. [`src/project_standards/cli.py`](../../src/project_standards/cli.py) imports validators, adoption, registry, and control-plane models directly. The control plane is the dependency hub for the CLI, package contract, Agent Handoff, specifications, and MCP services. Tests import implementation modules directly, so the effective internal contract is broad.

The in-flight [`src/project_standards/cli_contract.py`](../../src/project_standards/cli_contract.py) is useful groundwork: it begins to centralize allowed public exit statuses. It is not yet a complete cross-runtime contract and was treated as uncommitted user-owned work for this assessment.

## Performance assessment

### Measured current costs

Local warm probes on the assessed workstation produced these results:

| Probe | Result | Interpretation |
| --- | --: | --- |
| `project-standards --version`, 50 invocations | 19.98 seconds total | About 400 ms per invocation; eager imports make even the cheapest command expensive. |
| `validate-frontmatter --help`, 20 invocations | 7.90 seconds total | About 395 ms per invocation. |
| `uv run project-standards --version`, 20 invocations | 8.58 seconds total | `uv run` adds little after the environment is warm; Python imports dominate this probe. |
| Ruff lint, warm | 0.01 seconds | No meaningful Go opportunity. |
| Ruff format check, warm | 0.01 seconds | No meaningful Go opportunity. |
| BasedPyright, warm | 17.50 seconds and about 1.22 GiB RSS | A notable local static-analysis cost, but it is concurrent and hidden under slower test lanes in the fast gate. |

These are local observations, not Go comparisons. No Go prototype exists, so the report does not claim a specific replacement time. The startup result is nevertheless a legitimate reason to improve the current Python import graph or to value a future native executable.

The repository's own [`release-gate wall-clock study`](2026-07-31-release-gate-wall-clock-spike.md) is more important than microbenchmarks. It records:

- a 55:31 covered serial baseline;
- a 10:23 fully green fast gate under real-usage load;
- a projected quiet-machine floor of 7:30–8:30;
- 4,191 ordinary tests, 133 compatibility tests, and five performance tests in that study; and
- byte-equivalent coverage across the old and new gate configurations.

That 5.3-fold improvement came from xdist, `sys.monitoring` coverage, concurrent lanes, cache isolation, and a sufficiently large temporary filesystem—not from changing the product language. It consumes much of the easy local speedup that might otherwise be attributed to Go.

The latest inspected green hosted Check remained 40:14 because [`check.yml`](../../.github/workflows/check.yml) runs the ordinary, compatibility, and performance legs serially. The observed step times were:

- ordinary tests under coverage: 13:17;
- compatibility matrix: 25:32;
- performance gates: 0:40;
- type checking: 0:22; and
- checkout through dependency sync: about 0:12.

The compatibility matrix alone accounted for about 63.5% of job wall time. It installs candidate distributions, creates consumer repositories, runs CLI subprocesses, and checks source-versus-wheel behavior. Go can accelerate parsing and in-process planning, but it cannot eliminate the filesystem, Git, process, fixture, external-tool, and compatibility work the suite is designed to prove.

### What would become faster

A compiled executable should materially reduce command startup and can reduce CPU time in parsers, catalog traversal, hashing, and validation. A completed Go port would also replace BasedPyright, pytest collection, coverage.py, and much of the Python dependency setup with Go's build, test, vet, coverage, and format tools.

Go includes coverage-guided fuzzing in the standard toolchain and a runtime race detector, both useful for the repository's parsers and concurrent/recovery paths. Fuzzing is supported directly by `go test`, while the race detector only finds races on executed paths and has substantial runtime cost. These are complementary verification tools, not evidence that rewritten code is automatically safer. See the official [Go fuzzing documentation](https://go.dev/doc/security/fuzz/) and [race detector documentation](https://go.dev/doc/articles/race_detector).

### What would not become faster automatically

- Prettier and markdownlint operate on repository content and remain the formatting and structure authorities. Replacing them would be a standards compatibility change, not a Python-to-Go migration.
- Git operations, temporary-tree construction, filesystem synchronization, subprocess launch, and consumer installation still occur.
- The historical compatibility matrix remains necessary unless support policy changes.
- Candidate-artifact validation still has to prove that packaged standards, schemas, and payload bytes match the source authorities.
- CI checkout, Node setup, and Markdown dependencies remain.
- While either runtime or Python providers remain, the Python test and audit lanes cannot be removed.

Go's build cache can make repeated builds inexpensive, but it adds a distinct cache and module supply chain. It does not make the repository's external tools or integration fixtures disappear.

## Distribution and release effects

### The wheel is part of the product contract

The current pure-Python wheel is not just a launcher. It packages the `standards/` and `catalogs/` trees, exposes seven console entry points, and is tested as the candidate runtime. [`meta/versioning.md`](../../meta/versioning.md) requires an isolated wheel build, extraction, wheel-first `PYTHONPATH`, the full serial gate, and package-contract validation before release.

Consumers install an immutable Git tag with `uv tool install`; reusable workflows do the same. [`.pre-commit-hooks.yaml`](../../.pre-commit-hooks.yaml) declares six Python 3.14 hooks by their current console-script names. A Go release must replace or bridge all of these interfaces:

- installation documentation and upgrade behavior;
- reusable validation workflows;
- pre-commit hook language and entry points;
- the primary and six legacy executable names;
- GitHub release asset production and verification;
- candidate-artifact dogfooding; and
- rollback to the previous major line.

A `py3-none-any` wheel is one portable artifact for every supported Python host. A Go release normally becomes an explicit OS/architecture matrix with checksums, signatures, artifact naming, selection/install logic, and smoke tests for every supported target. The current Check workflow is Ubuntu-only, so the repository does not yet have evidence for a broader binary support promise.

The release process also needs fuller artifact automation regardless of language. The current repository prints a `gh release create` handoff, while the published release carries wheel and source-distribution assets. A Go migration should not proceed until the reproducible build, upload, checksum, signing, and verification owner is explicit.

### Executable payloads are the blocking architecture constraint

Every current consumer package default declares Python providers. The control plane validates `kind = "python"`, verifies the provider bytes, compiles them, and executes their declared symbols. Retained provider versions are part of the immutable catalog contract, not generated implementation debris.

Consequently, a Go host has only three honest choices:

1. **Retain a Python worker.** This gives an incremental path and preserves old payloads, but consumers still need Python and the repository permanently owns two runtimes.
2. **Port every retained provider version.** This is a roughly 36,600-line historical behavior rewrite with byte/output parity obligations. It also changes how immutable payloads identify and execute code.
3. **Create a new provider ABI and keep v5 separate.** A Go v6 supports only the new ABI while the Python v5 line remains available for old catalogs and consumers. This is the cleanest long-term option if Go is selected, but it is an explicit major compatibility break rather than an internal rewrite.

Option 1 is the safest experiment and the weakest final architecture. Option 3 is the recommended destination if the strategic decision is truly “remove the Python runtime.”

### MCP is viable in Go, but should move last

The official MCP Go SDK is now a real option rather than an ecosystem blocker. Its current release supports the 2026-07-28 protocol while preserving older protocol negotiation, according to the official [Go SDK releases](https://github.com/modelcontextprotocol/go-sdk/releases). Project Standards, however, pins the Python SDK and has specific dual-era, launch-failure, stdout-purity, distribution-integrity, and bounded-provider contracts. SDK availability does not prove parity with those contracts.

The MCP server should therefore move after the domain services and provider strategy stabilize. Porting transport first would couple two migrations and make protocol differences harder to distinguish from domain differences.

## File clutter and toolchain effects

A side-by-side migration initially adds:

- `go.mod` and `go.sum`;
- `cmd/` and `internal/` Go trees;
- golden corpora shared by Python and Go;
- Go formatting, vet, test, coverage, fuzz, and vulnerability gates;
- multi-platform build and release configuration;
- binary installation and checksum logic; and
- differential test orchestration.

Python files, `pyproject.toml`, `uv.lock`, the wheel build, and much of pytest must remain while historical providers or the Python oracle remain. Node and npm also remain because Markdown tooling is independent of the implementation language. This is materially more clutter than the current repository.

After a clean v6 break, Go could remove the main Python package, Python static analysis, and the wheel runtime. It would not remove the Python Tooling and Python Coding standards that this repository publishes, the immutable standards history, schemas, JSON fixtures, Markdown documentation, or Node-based content tooling. The eventual reduction is therefore meaningful in runtime machinery, but modest relative to the whole repository.

Do not create a second committed copy of standard payload bytes for Go embedding. Keep one canonical `standards/` and `catalogs/` tree, generate or embed from that authority, and prove byte identity in source and released artifacts.

## Robustness and reliability

### Failures Go would remove

A self-contained executable eliminates Python interpreter discovery, virtual environment wiring, and console-script generation. Those are known operational failure classes in this ecosystem: the Agent Handoff startup hook previously resolved a rejecting Python shim, and installation guidance already permits a retry when the first post-install version probe fails transiently.

Go also supplies a stricter compile-time type boundary for many model and error paths. Explicit structs, sum-like tagged representations, fuzz corpora, and race testing could improve assurance if the port preserves the current closed input models and diagnostic contracts.

### Regressions a rewrite is likely to introduce

The hard parts of this repository are not argument parsing. They include:

- a custom JSON/JSONC lexer and source-span editor that rejects duplicate keys and non-finite numbers while preserving comments, trailing commas, Unicode width behavior, and Prettier-compatible presentation;
- YAML node inspection that rejects duplicates, aliases, anchors, and merges at mutable boundaries before splicing bounded source regions;
- canonical TOML encoding, self-digests, and in-memory lock upgrades;
- strict models that distinguish absent, null, zero, and invalid unknown fields;
- Unicode normalization, case-folding, and repository-relative path rules;
- descriptor-relative `openat` operations, `O_NOFOLLOW`, staging, `fsync`, and atomic publication;
- non-blocking `fcntl.flock` semantics;
- Git environment isolation, fixed subprocess argument vectors, and timeouts;
- interrupted migration and recovery state; and
- stable exit status, stdout, stderr, diagnostic code, and no-mutation behavior.

Generic Go JSON, YAML, or TOML unmarshalling will not preserve these contracts. Go structs also require deliberate pointer/optional representations to retain absent-versus-zero semantics. A portable Go executable can still contain Unix-only safety behavior; supporting Windows requires either equivalent APIs and tests or an explicit platform limitation.

The current test corpus is a migration asset. It already exercises malformed structured text, byte idempotence, digest vectors, symlink races, lock contention, process exit, installed-wheel behavior, offline migration fixed points, help, version, and nested commands. The right migration technique is to turn those behaviors into language-neutral executable contracts, not translate test functions mechanically.

## Migration shapes considered

| Shape | Benefit | Cost and risk | Disposition |
| --- | --- | --- | --- |
| Go launcher calling Python | Faster top-level dispatch only | Still pays Python startup for real work; two runtimes and more failure boundaries | Reject as an end state |
| Selected standalone validators in Go | Tests parser and distribution assumptions on bounded commands | Exact YAML/schema/diagnostic parity is harder than the commands appear | Suitable only as an experimental pilot |
| Go read-only package/catalog core | Exercises canonical models, digests, discovery, and release artifact design without mutations | Still needs shared fixtures and differential testing | Best pilot boundary |
| Go control plane with Python provider worker | Can move performance-sensitive planning while preserving payloads | Permanent dual runtime unless followed by a major break | Acceptable transition, poor destination |
| Full in-place Go rewrite retaining v5 behavior | One final runtime | Largest parity burden; rewrites immutable historical execution and release contracts | Do not pursue |
| Separate Go v6 with a new provider ABI | Clean native architecture and release model | Major migration, new consumers/workflows/hooks, v5 support policy required | Best long-term Go shape if strategic gates pass |

## Recommended decision gates

Do not begin a production port until the following discovery work is complete:

1. **Freeze a black-box contract.** Record argv, working tree, stdin, exit code, exact stdout/stderr bytes, resulting tree digest, and expected diagnostic codes for public commands. Include malformed flags, help/version short-circuits, empty and non-Git repositories, contention, symlink attacks, and interrupted recovery.
2. **Profile the hosted compatibility lane.** Separate Python CPU time from process, installation, Git, and filesystem time. Proceed beyond a pilot only if replaceable CPU work is a material fraction of the critical path.
3. **Build a read-only Go shadow executable.** Limit it to version/help, canonical model decoding, catalog/package discovery, hashing, and read-only validation. Do not write repository state.
4. **Run differential and fuzz tests.** Seed Go fuzz targets with all existing JSONC, YAML, TOML, path, catalog, lock, and diagnostic fixtures. Every minimized failure becomes a shared permanent corpus entry.
5. **Prototype the released artifact.** Define supported targets, reproducible asset build, checksums/signing, installation, pre-commit behavior, candidate dogfooding, and rollback before claiming distribution simplicity.
6. **Make the provider decision explicitly.** Choose a temporary Python bridge or a clean v6 ABI. Do not let an experimental bridge become an accidental permanent architecture.

Recommended go/no-go criteria for the pilot:

- exact parity on the frozen read-only corpus, including output bytes and rejection behavior;
- no regression in path, symlink, digest, or malformed-input safety;
- a material end-to-end improvement on representative validation, not only a parser microbenchmark;
- an artifact installation path demonstrably simpler than `uv tool install` for the supported consumers; and
- an owner-approved v5 compatibility and retirement policy.

If the pilot fails any semantic criterion, stop. If it passes semantics but profiling shows little end-to-end improvement, retain Python and apply the measured workflow and import-graph optimizations instead.

## Near-term actions that do not require migration

1. Parallelize the hosted ordinary and compatibility jobs experimentally and compare wall time, queueing, reliability, and CI minutes.
2. Profile one representative compatibility row and the complete lane before attributing its cost to Python.
3. Reduce eager imports for `--version`, `--help`, and dispatch-only paths; the observed 0.40-second startup is large enough to address directly.
4. Complete and validate the in-flight public exit-code contract, then extend it to black-box fixtures useful to either language.
5. Keep the existing controlled fast-gate benchmark work; do not use old serial baselines to justify a rewrite after the repository already eliminated most of that wall time.

## Final decision

The repository should remain Python for v5. Go should be treated as a possible v6 product and distribution decision, not as a refactor or generalized speed fix. Authorize only a read-only, contract-first pilot after current CLI-contract work is stable. The evidence threshold for continuing should be high because the intermediate dual-runtime state is objectively more complex, while the existing Python implementation already has unusually strong semantic and reliability coverage.
