### Executive summary

The specification is close in intent, but it is not ready for Claude Code to use as the basis for planning or implementation. The main blockers are contract ambiguity around the new CLI surface and a repo-contract mismatch: `project-spec` says every tooling command offers machine-readable `--json`, but this spec omits any JSON mode for `new`.

Internet research was required for current Python CLI/filesystem behavior. Official Python 3.14 docs confirm the external assumptions are mostly feasible, but they also make the write-safety gaps more important: common `pathlib` write primitives overwrite existing files directly, and parent directory creation has permission/symlink implications the spec does not yet constrain.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 3

### What the specification gets right

* Correctly scopes Spec #2 to `new` only and keeps `upgrade` out of this lower-risk authoring command.
* Correctly preserves the existing read-only `validate|lint|extract|next` command surface and proposes a narrow new module.
* Correctly recognizes that the current templates intentionally fail consumer validation only because of the `SPEC-____` sentinel.
* Correctly requires self-validation before writing and refuses to clobber existing paths without `--force`.
* Correctly separates pure scaffold logic from the impure CLI/file I/O shell.

### Adversarial review performed

I inventoried the proposed CLI, scaffold behavior, ID minting, write model, error codes, tests, acceptance criteria, and versioning claims. I falsified those against the current `specs/` implementation, bundled templates, README tooling contract, config discovery behavior, tests, workflow, TODO/handoff state, and Python 3.14 docs for `argparse`, `random`, and `pathlib`.

The strongest assumptions tested were: `new` can reuse `collect_spec_paths` while tolerating an empty corpus; `new` can satisfy the repository’s JSON-output tooling contract without a `--json` surface; the write model is safe enough for a file-writing command; and all CLI conflict cases are specified enough for planning. I did not execute mutating validation or tests because this audit is read-only and several useful checks would write cache/coverage artifacts.

### Blocking issues

#### SA-001: CLI conflict and parent-directory behavior are both specified and unresolved

* Severity: High
* Status: Confirmed
* Adversarial angle: Can Claude Code produce a reliable parser and test matrix without inventing behavior?
* Spec reference: Component 1 says `PATH` + `--stdout` is deferred; Component 5 says missing parent directories are created; Open implementation questions re-open both `PATH` + `--stdout` and parent-dir creation.
* Finding: The spec treats material CLI/write behavior as frozen in one section and undecided in another. `PATH` + `--stdout` is explicitly contradictory but deferred to the plan, while acceptance criteria require all exit codes and flag behavior to hold. Parent-dir creation is specified as “create parent dirs as needed” but later listed as an open implementation question.
* Repository evidence: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md:74-79`, `:131-138`, `:164-169`, and `:186-189` conflict. Current `src/project_standards/specs/cli.py:45-55` uses argparse for command-specific parsing and tests exit-code behavior explicitly in `tests/test_spec_cli.py:16-71`, so unspecified parser cases will become implementation/test guesses.
* External research evidence: Python 3.14 `argparse` supports clean usage errors and mutually exclusive option handling, but the spec must choose the intended behavior. Source: https://docs.python.org/3.14/library/argparse.html, accessed 2026-07-05.
* Why it matters: This blocks a deterministic implementation plan. Different reasonable implementations could reject `PATH` + `--stdout`, ignore `PATH`, or treat `--force` differently under `--stdout`; all could plausibly claim to follow parts of the spec.
* Recommended action for Claude Code: Make these decisions in the spec, not the plan. Specify exact behavior and exit code for `PATH` + `--stdout`, `--force` + `--stdout`, `--force` without `PATH`, and missing parent directories.
* Suggested validation: Add CLI tests for every conflicting flag combination and for parent-dir creation or refusal, whichever behavior the spec chooses.

#### SA-002: `new` omits the project-spec JSON output contract

* Severity: High
* Status: Confirmed
* Adversarial angle: Does the new command preserve the standard’s published tooling contract?
* Spec reference: CLI surface lists `--profile`, `PATH`, `--id`, `--title`, `--owner`, `--implementer`, `--stdout`, and `--force`, but no `--json`.
* Finding: The Project Specification Standard says every command offers machine-readable `--json` output, and the spec says no standard-text change is required. If implemented as written, `new` would be the first project-spec command without the promised JSON mode.
* Repository evidence: `standards/project-spec/README.md:101-103` says every command offers machine-readable `--json`; `README.md:116-118` also requires outputs consumable by other tools. The spec’s CLI surface at `docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md:67-79` omits `--json`; current implemented commands already support JSON where output payloads exist in `src/project_standards/specs/cli.py:47-50`, `:81-96`, and `:105-119`.
* External research evidence: Not applicable.
* Why it matters: `new` is explicitly agent/CI-safe tooling. Without a specified JSON payload, downstream automation cannot reliably capture the minted `spec_id`, output path, profile, overwrite status, or self-validation failure details.
* Recommended action for Claude Code: Add a `--json` contract for `new`, or explicitly amend the README/tooling contract to exempt generative commands. Prefer specifying JSON for success and error/finding cases.
* Suggested validation: Add tests for `new --json PATH`, `new --json --stdout`, collision errors, validation-failure errors, and overwrite refusal payload shape.

### Non-blocking issues

#### SA-003: Empty-corpus discovery conflicts with the current discovery helper contract

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Can the implementation reuse the named helper without accidentally preserving `validate` semantics?
* Spec reference: Component 2 says `load_spec_config` + discovery enumerate existing specs with empty result tolerated; Component 4 says `new` must not raise `DiscoveryError`; acceptance says `new` works with no specs and no `spec:` config.
* Finding: The spec names `collect_spec_paths` as reusable discovery, but the current helper intentionally raises `DiscoveryError` when no `spec:` block exists, include globs are empty, or discovery matches no files. The spec needs to state whether to add a tolerant helper, catch only `DiscoveryError`, or bypass `collect_spec_paths` for ID discovery.
* Repository evidence: `src/project_standards/specs/config.py:59-75` raises `DiscoveryError` for the empty cases. `tests/test_spec_config.py:16-39` locks that behavior for existing commands. The spec requires the opposite behavior for `new` at `docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md:92`, `:124-125`, and `:168`.
* External research evidence: Not applicable.
* Why it matters: If Claude Code “reuses discovery” naively, the empty-repo acceptance criterion fails. If it catches too broadly, it could hide unreadable config or invalid config errors that the spec says must fail closed.
* Recommended action for Claude Code: Specify a distinct tolerant ID-discovery path and exactly which exceptions become empty `existing_ids` versus exit 2.
* Suggested validation: Add tests for no config, `spec:` with empty include, zero-match include, malformed config, unreadable config, and one malformed discovered spec.

#### SA-004: Write safety does not address partial writes, symlinks, or non-regular targets

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Could the safety model pass tests while still damaging an existing or outside-repo file?
* Spec reference: Write model and safety.
* Finding: The spec says writing is last and refuses existing paths unless `--force`, but it does not define atomic write behavior, partial-write recovery, symlink handling, directory/FIFO/device targets, or whether `--force` may follow symlinks. A direct `Path.write_text` implementation would overwrite an existing file and follow normal OS path semantics.
* Repository evidence: The current repo has no `new` implementation yet; the spec’s write model at `docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md:129-138` is the only safety contract. Existing CLI error handling catches config/parse errors but not a new write boundary in `src/project_standards/specs/cli.py:151-158`.
* External research evidence: Python 3.14 `pathlib.Path.write_text` opens and writes the target file and overwrites existing files; `Path.mkdir(parents=True)` creates missing parents with default permissions; `Path.is_symlink` exists to distinguish symlink targets. Source: https://docs.python.org/3.14/library/pathlib.html, accessed 2026-07-05.
* Why it matters: A file-writing command’s tests could prove “no pre-write failure writes bytes” while still allowing partial output on disk-full/interruption or unintended writes through symlinks under `--force`.
* Recommended action for Claude Code: Specify whether writes must be atomic for new files and forced overwrites, whether symlinks are refused or followed, and how non-regular targets are handled.
* Suggested validation: Add tests for existing regular file, existing directory, symlink target, broken symlink, parent path that is a file, write permission failure, and simulated write failure if practical.

#### SA-005: Flag value escaping is underspecified beyond quotes and colons

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Can arbitrary CLI values corrupt frontmatter or fail with unclear errors?
* Spec reference: Fill operation and testing.
* Finding: The spec requires YAML-safe single-quoted emission and tests a title containing `'` and `:`, but it does not define behavior for newlines, carriage returns, leading/trailing whitespace, non-printing control characters, or empty strings. Those inputs can alter the generated frontmatter shape or produce self-validation errors after scaffold generation rather than a clear argument error.
* Repository evidence: The spec names only quote/colon escaping at `docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md:113` and tests only that case at `:156-157`. Current parsing uses PyYAML scalar parsing in `src/project_standards/specs/document.py`, so malformed emitted YAML becomes a parse/self-validation failure, but the user-facing contract is not defined.
* External research evidence: Not applicable.
* Why it matters: Agent/CI-safe CLIs need predictable handling for values supplied non-interactively. A newline in `--title` should either be rejected clearly or encoded by a specified rule.
* Recommended action for Claude Code: Define accepted value grammar for `--title`, `--owner`, and `--implementer`, including empty string and newline/control-character behavior.
* Suggested validation: Add unit and CLI tests for apostrophes, colons, empty strings, leading/trailing spaces, newline/carriage return, and Unicode/non-ASCII if supported.

### Missing specification considerations

* Machine-readable output for `new`: blocking. The README-level tooling contract requires JSON-capable output, but this spec omits payload shape and error/finding serialization.
* CLI conflict matrix: blocking. `PATH`/`--stdout`/`--force` combinations need exact behavior before planning.
* Parent directory policy: blocking because the spec currently both specifies and reopens it.
* Tolerant ID discovery API: non-blocking but required before implementation because current `collect_spec_paths` has validate-oriented empty-corpus behavior.
* Write atomicity and target type policy: non-blocking but safety-relevant for a file-writing CLI.
* Input validation for human fields: non-blocking but correctness-relevant.
* Exhausted ID space / retry limit: non-blocking. `mint_spec_id` should specify a bounded failure mode if all candidates are exhausted or a deterministic RNG keeps colliding.
* Parse-failed neighbor policy: non-blocking. Skipping malformed neighbors conflicts slightly with “explicit id can never introduce a duplicate” when the malformed file’s ID cannot be read.

### Ambiguities and decisions needed

* Ambiguity: What happens when both `PATH` and `--stdout` are supplied?
* Why it matters: It affects parser design, safety expectations, tests, and exit codes.
* Recommended clarification: Choose reject with exit 2, or define `--stdout` precedence explicitly.
* Blocking or non-blocking: Blocking.

* Ambiguity: Does `--force` have any effect with `--stdout` or without `PATH`?
* Why it matters: Otherwise a no-write preview mode can still accept a write-safety flag with unclear meaning.
* Recommended clarification: Specify whether it is ignored, rejected, or accepted only with `PATH`.
* Blocking or non-blocking: Blocking.

* Ambiguity: Are missing parent directories created or refused?
* Why it matters: Component 5 and the open questions disagree.
* Recommended clarification: Pick one behavior and remove the contradictory text.
* Blocking or non-blocking: Blocking.

* Ambiguity: What is the JSON output contract for `new`?
* Why it matters: The standard promises machine-readable command output.
* Recommended clarification: Define success and error JSON payloads, including minted ID, path/stdout mode, profile, overwritten flag, and findings.
* Blocking or non-blocking: Blocking.

* Ambiguity: What write primitive/safety guarantees are required?
* Why it matters: Direct writes can partially overwrite files and symlinks can redirect writes.
* Recommended clarification: Define atomic write expectations, symlink behavior, and non-regular target errors.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: Python 3.14 argparse documentation
* URL: https://docs.python.org/3.14/library/argparse.html
* Access date: 2026-07-05
* What it was used to verify: Current argparse behavior for clean parser errors, invalid arguments, and mutually exclusive option support.
* Relevant conclusion: The proposed exit-2 usage-error model is feasible, but the spec must choose the unresolved CLI conflict behavior.

* Source name: Python 3.14 random documentation
* URL: https://docs.python.org/3.14/library/random.html
* Access date: 2026-07-05
* What it was used to verify: `random.Random` determinism and suitability for injected testable RNG.
* Relevant conclusion: Injected `Random` instances are suitable for deterministic non-security IDs; Python docs warn the module is not for cryptographic purposes, which is acceptable because `spec_id` is not a secret.

* Source name: Python 3.14 pathlib documentation
* URL: https://docs.python.org/3.14/library/pathlib.html
* Access date: 2026-07-05
* What it was used to verify: File overwrite, parent-directory creation, and symlink/path behavior relevant to the write model.
* Relevant conclusion: Common primitives can overwrite existing files and create parents with default permissions; the spec should define atomicity and symlink/non-regular target behavior instead of leaving it to implementation defaults.

### Items Claude Code should verify before correcting the specification

* Confirm whether `new` should support `--json` for both file-write and `--stdout` modes, and what payload downstream agents need.
* Confirm intended behavior for `PATH` + `--stdout`, `--force` + `--stdout`, and missing parent directories.
* Confirm whether `new` should use a new tolerant discovery helper or catch `DiscoveryError` around `collect_spec_paths`.
* Confirm desired safety policy for symlinks, directories, special files, and atomic writes.
* Confirm accepted character set/value grammar for `--title`, `--owner`, and `--implementer`.
* Confirm whether parse failures in discovered specs should be skipped, warned, or treated as exit 2 when they prevent reliable duplicate-ID detection.

### Suggested corrections for Claude Code’s specification

* Add `--json` to the CLI surface or explicitly revise the README-level tooling contract; define JSON payloads for success and failure.
* Resolve `PATH` + `--stdout`, `--force` + `--stdout`, `--force` without `PATH`, and parent-directory behavior in the spec.
* Replace the vague “reuse discovery” instruction with a precise tolerant ID-discovery contract.
* Add a bounded ID mint retry/exhaustion error.
* Add write-safety requirements for atomicity, symlinks, non-regular paths, permission errors, and partial write failures.
* Add input validation/escaping rules for human-field flags.
* Add tests for every new edge case above, not just happy-path scaffold output.

### Read-only validation performed

* `git status --short && git branch --show-current && git log --oneline -n 10`: confirmed branch `testing`, no short-status output, and recent commits include Spec #1 implementation and Spec #2 design.
* `rg --files`: inventoried repository files and confirmed relevant `project-spec`, `src/project_standards/specs`, tests, workflows, and handoff docs exist.
* Inspected the spec under audit with `sed` and `nl -ba`: inventoried requirements, acceptance criteria, open questions, and internal contradictions.
* Inspected `standards/project-spec/README.md`: confirmed the project-spec tooling contract and `new` capability text.
* Inspected `src/project_standards/specs/cli.py`, `config.py`, `document.py`, `registry.py`, `commands/validate.py`, `commands/lint.py`, and `commands/next_id.py`: checked current command dispatch, validation, discovery, parsing, and registry behavior.
* Inspected bundled templates under `standards/project-spec/templates/` and `src/project_standards/specs/templates/`: confirmed frontmatter keys, sentinel, profile values, and H1 shapes.
* Inspected `tests/test_spec_cli.py`, `tests/test_spec_config.py`, `tests/test_template_conformance.py`, `tests/test_spec_packaging.py`, `tests/test_spec_validate.py`, and `tests/test_spec_lint.py`: confirmed existing test contracts, especially empty discovery raising `DiscoveryError`.
* Inspected `.project-standards.yml`, `.github/workflows/validate-specs.yml`, `pyproject.toml`, `TODO.md`, and `docs/handoff/specs-plans.md`: checked repo configuration, workflow expectations, toolchain gates, and current project-spec status.
* Performed targeted `rg` searches for `spec_id`, `SPEC-____`, `project-spec`, and `spec new`: confirmed sentinel usage and absence of an existing `new` implementation.
* One attempted `rg` command containing a shell backtick pattern failed with a quoting error; no evidence from that failed command was used.
* Opened official Python 3.14 docs for `argparse`, `random`, and `pathlib`: verified current external assumptions relevant to CLI parsing, RNG injection, and write safety.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: targeted tests for `tests/test_spec_new.py` and `tests/test_spec_new_cli.py`.
* Run only after implementation: CLI checks for `new --profile light|standard|full PATH` followed by `project-standards spec validate PATH`.
* Run only after implementation: CLI checks for `--stdout`, `--json`, `--force`, bad `--id`, ID collision, missing/no-match config, malformed config, existing path, missing parents, symlink path, directory path, and invalid human-field values.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: whether the revised spec resolves the CLI conflict matrix, adds or explicitly exempts `--json`, defines tolerant discovery without weakening config errors, and closes write-safety/input-validation gaps.

