# Root-Artifact Ownership and Semantic Composition Design

**Date:** 2026-07-10 **Status:** approved; adopted by ADR 0023 after adversarial review converged in round 2 **Author:** session 2026-07-10

## Problem and goal

Several standards must contribute to files that tools discover only at conventional repository paths. The current copy-adopt model can deduplicate byte-identical shared files and report fragments, but it cannot safely compose independently selected standards into an existing consumer repository.

The concrete conflicts already exist:

- Python Tooling installs whole `AGENTS.md` and `CLAUDE.md` files while Agent Handoff owns bounded instruction blocks in those containers.
- Python Tooling reports a `pyproject.toml` fragment instead of applying it.
- Python Tooling and Markdown Tooling both install the same `.editorconfig` and VS Code extension recommendations.
- Agent Handoff semantically updates Claude and Codex settings while preserving unrelated harness configuration.
- Existing consumer repositories may already contain any of these files with valuable local content.

The goal is to define a conflict-free ownership and composition contract for `SPEC-CP01`. Any independently selected standard must be able to contribute its declared semantics without owning unrelated container content, depending on another standard, relying on package order, or overwriting consumer work.

## Approved approach

Use **consumer-owned containers with typed package contributions**.

The consumer owns the surrounding file and every undeclared semantic unit. A standard owns only the keys, sections, set entries, tasks, hooks, or bounded blocks declared by its selected immutable payload. The control plane owns the merge and mutation mechanism, but it does not acquire content ownership merely because its executor writes the final file.

Whole-file package ownership remains available only for exclusive destinations that do not need semantic composition. There is no precedence rule between standards.

## Alternatives rejected

### One standard owns each shared file

Designating Python Tooling, Markdown Tooling, or `project-toolbox` as the owner of a shared root file would simplify rendering, but it would create a hidden dependency. A consumer would need the designated owner even when selecting only another standard that contributes to the file. This conflicts with ADR 0013 and the independent-package contract.

### Per-standard sidecars with generated aggregators

Sidecars isolate ownership cleanly only when the external tool supports includes. `AGENTS.md`, `CLAUDE.md`, VS Code recommendations, common harness settings, and many repository-level configuration files have fixed discovery paths or no portable include mechanism. An aggregator would still need the composition rules defined here.

## Ownership model

### Container

A container is a conventional-path file that may hold consumer content and contributions from one or more packages. The consumer owns:

- the existence and general purpose of a pre-existing container;
- all comments, formatting, ordering, and semantic units outside declared contribution scopes; and
- any content explicitly classified as consumer-owned during migration.

The control plane may create a missing container while applying a reviewed plan. Creation does not make the entire file platform-owned.

### Semantic unit

A semantic unit is the smallest independently ownable element supported by an adapter. Its identity is the normalized tuple:

```text
(target path, adapter type, semantic scope)
```

Examples include a TOML key path, JSON object key, VS Code task label, extension ID, EditorConfig section/property pair, harness hook identity, or Markdown block ID.

An ownership declaration that is broader than the content a package actually controls is invalid. Parent and child scopes may not overlap across packages. Redundant overlapping scopes within one payload are rejected unless the adapter defines them as one normalized unit.

### Package contribution

A package contribution declares:

- the repository-relative target;
- the adapter and normalized semantic scope;
- a static payload source or deterministic read-only render provider;
- an install policy;
- the owning standard and package version; and
- the required conflict behavior.

The exact manifest field names belong to `SPEC-BA02`. The schema must be expressive enough to validate ownership before provider execution and to inventory every applied unit in the central lock.

### Shared contribution

A shared contribution is one semantic value intentionally referenced by multiple independent packages. It has a stable shared identity and payload digest. All references must normalize to the same adapter, scope, and value.

The lock records every current package reference. Disabling one package removes only its reference. The semantic unit is removed only after the last reference disappears and the live unit still matches the recorded value.

Different values at the same scope are never resolved through package order, majority, or precedence. They are a blocking authority conflict.

### Whole-file artifact

A package may own an entire file when all of the following hold:

- the destination is exclusive to that package version;
- no current or planned package contributes a nested semantic unit;
- the payload declares managed, create-only, or other supported lifecycle policy;
- a pre-existing different file produces a reviewed adoption or conflict path; and
- removal preserves modified or ambiguous content under `SPEC-CP01` FR-010.

Individual workflow callers, package-specific lint configuration, installed skills, and executable helper scripts normally use this model.

## Composition algorithm

The reconciler composes all enabled packages against one virtual tree before any write:

1. Resolve package versions and validate their contribution declarations.
2. Load each live target once and record its whole-file precondition digest.
3. Parse the target with the declared syntax-preserving adapter.
4. Invoke declared read-only render or migration-planning providers and validate their output bounds.
5. Normalize every current, rendered desired, and previously applied semantic unit.
6. Detect overlapping package scopes, incompatible shared identities, malformed containers, and consumer conflicts.
7. Classify every relevant current and desired unit as create, adopt-equal, update, preserve, remove, no-op, or conflict.
8. Apply every non-conflicting contribution to an in-memory virtual target in the canonical contribution order defined below.
9. Display one final action per target plus its unit-level provenance and conflict details.
10. On explicit apply, recheck the whole-file precondition, atomically write the reviewed virtual target, verify it, and write the central lock last.

No provider writes a partial file, and the executor never writes one package's whole file before asking another package to patch it.

### Deterministic ordering and placement

Canonical contribution order is bytewise lexicographic standard ID followed by the adapter's normalized semantic scope. A shared unit uses its stable shared identity in place of a standard ID. This order controls deterministic physical placement only; it never chooses a value, suppresses a conflict, or grants precedence.

Adapters preserve the relative order and physical representation of existing consumer-owned units. Existing managed units remain in place unless their selected payload updates or removes them. When one reconciliation inserts several units at the same placement point, it orders those new units canonically:

- TOML, JSON/JSONC, and YAML mapping entries are appended to the end of their existing parent mapping.
- Set-like entries are appended after existing entries and sorted by normalized entry identity.
- Markdown blocks are inserted after the last existing managed block, or at end of file when none exists, with one surrounding blank line.
- EditorConfig properties are appended to an existing section; missing sections are appended at end of file.
- Whole-file artifacts have no nested placement order.

Package argument order therefore cannot change a plan's final bytes. The adapter does not reorder existing consumer content merely to canonicalize a file.

## Preservation and conflict rules

### Pre-existing content

- A missing semantic unit may be inserted.
- An unowned unit already equal to the desired value may be adopted without rewriting after the plan identifies the new ownership.
- An unowned unit with a different value blocks apply until a declared migration or explicit user resolution exists.
- Unknown keys, blocks, entries, comments, and formatting are preserved.
- A malformed container blocks every contribution targeting it; the tool does not guess a repair.

### Applied content

- `preserve` applies only when the current transition intentionally lacks mutation authority, such as unrelated consumer content, create-only content after creation, or a shared unit retained for another owner.
- An unchanged owned unit may be updated or removed according to its selected payload.
- Any owned unit whose normalized live value differs from its recorded value classifies as `conflict`, remains untouched, and blocks the complete plan. This rule applies whether the selected payload would keep, update, or remove the unit.
- An edit outside owned scopes does not create package drift, but the executor still rechecks the whole-file digest to prevent a concurrent overwrite.
- A package-version migration may change scope only through a declared migration that proves how old ownership maps to new ownership.

### Container removal

Removing the final contribution does not normally delete the container. The executor deletes it only when the lock proves the platform created it, no consumer or other package content remains, and the empty result has no durable comments or formatting intent. Otherwise it preserves a valid container with the package unit removed.

## Syntax-preserving adapter contract

Semantic equality and physical preservation are separate concerns. Every shared-container adapter must:

- parse and validate the supported real-world syntax;
- identify stable semantic scopes;
- preserve unowned comments, ordering, whitespace, quoting, and trailing separators;
- render deterministic changes only within owned scopes;
- expose normalized values for conflict and drift comparison;
- make Markdown-block normalization stable under every declared physical formatter, without erasing semantic distinctions such as code fences, links, or heading levels; otherwise require and validate formatter exclusion for the block;
- reject duplicate or ambiguous identities; and
- support unit removal without reformatting the rest of the file.

Full parse-and-reserialize of a consumer-owned container is prohibited unless byte-level preservation of every unowned region is proven. The implementation plan must select and test a round-trip-capable library or bounded text-edit strategy for each adapter. Standard-library `tomllib` alone is insufficient because it cannot write TOML, and strict JSON parsing is insufficient for VS Code JSON with comments or trailing commas.

Physical-formatting authority is distinct from semantic ownership. Reconciliation does not invoke Prettier or another whole-file formatter as a merge step. An explicitly requested formatting operation may change physical bytes within its declared authority, but it must preserve normalized values; that physical change does not create semantic-unit drift. The next apply still plans from the newly observed whole-file precondition.

## V5 adapter and surface mapping

| Surface | Container owner | Package-owned unit | Adapter and identity | V5 disposition |
| --- | --- | --- | --- | --- |
| `pyproject.toml` | Consumer | Declared tables and key paths | Round-trip TOML; normalized dotted key path | Convert Python Tooling's reported fragment into typed contributions. Existing conflicting build or tool keys require migration or block. |
| `AGENTS.md` | Consumer | Standard-specific instruction blocks | Delimiter-bounded Markdown; stable block ID | Split Python Tooling's whole file into a `python-tooling` block. Retain Agent Handoff's independent block. Future packages, including `project-toolbox`, contribute their own blocks. |
| `CLAUDE.md` | Consumer | Standard-specific instruction blocks | Delimiter-bounded Markdown; stable block ID | Split Python Tooling's whole file into a bounded block and retain Agent Handoff's block. Preserve all other instructions. |
| `.claude/settings.json` | Consumer | Declared hook registrations | Round-trip JSON/JSONC; stable hook identity | Agent Handoff owns only its SessionStart registration. Preserve unrelated hooks and settings. |
| `.codex/config.toml` | Consumer | Declared hook registration or bounded table entries | Round-trip TOML; normalized hook identity/key path | Agent Handoff owns only its installed registration. Preserve unrelated Codex configuration. |
| `.vscode/settings.json` | Consumer | Declared setting keys | Round-trip JSONC; normalized object key | Replace Python Tooling whole-file ownership with per-key contributions. |
| `.vscode/tasks.json` | Consumer | Declared task objects | Round-trip JSONC; task label as stable identity | Python Tooling owns its task labels, not the tasks array or file. Duplicate labels with different definitions block. |
| `.vscode/extensions.json` | Consumer | Recommendation entries | Set-like JSONC list; case-normalized extension ID | Decompose the current whole shared file into per-extension units. Preserve consumer recommendations and remove only unreferenced owned entries. |
| `.editorconfig` | Consumer | Section/property values | Round-trip EditorConfig; normalized glob section plus property | Decompose the current whole shared file into per-property units. Common values may be shared; language-specific values belong to the relevant package. Conflicting consumer values block, and unrelated content remains. |
| `.github/workflows/*.yml` | Consumer container when pre-existing; otherwise package-created | Whole document or explicitly declared mapping scopes | Syntax-preserving YAML; unique path or normalized mapping path | Current callers keep distinct filenames and normally remain managed whole-file artifacts. Same-path composition requires disjoint declared YAML scopes; otherwise it blocks. |
| `.markdownlint.json`, `.prettierrc.json`, `.python-version` | Package when newly created and exclusive | Whole file | Whole-artifact adapter | Retain package ownership with normal pre-existing, drift, update, and removal protections. |
| `scripts/check.py` and package-local installed tools | Package when newly created and exclusive | Whole file | Whole-artifact adapter | Retain managed source-owned behavior and executable mode tracking. |
| `docs/usage.md` | Consumer when pre-existing | Package document only after explicit adoption | Whole document with managed/create-only policy | CLI Documentation may create or adopt the document but never overwrite unrelated existing documentation implicitly. |
| `README.md` | Consumer | None in v5 | Read-only semantic validation | CLI Documentation continues to inspect command-reference coverage without mutating the README. |
| `docs/handoff/**`, `docs/STATUS.md`, `docs/TODO.md` | Consumer after creation | Initial scaffold only | Create-only artifact plus validators | Agent Handoff never treats consumer knowledge as managed package content after scaffolding. |
| `.project-standards.yml` | Legacy consumer authority during migration | None after migration | Read-only legacy parser | Package fragments become `.standards/config.toml` options or typed contributions. Successful migration retires the YAML authority under FR-021. |

## Shared baseline policy

The current `_shared/editorconfig` and `_shared/vscode-extensions.json` prove that multiple independent standards can intentionally request the same content. V5 retains the useful sharing but changes the ownership granularity:

- the current shared files are decomposed into semantic units rather than preserved as indivisible baselines;
- general EditorConfig properties may use shared identities, while Python, Markdown, TOML, or YAML-specific properties belong to the package that requires them;
- VS Code recommendations are owned per extension ID, and only packages that request the same extension share its reference;
- shared payload resources remain platform-distributed and content-addressed;
- a package references a shared contribution without depending on another package;
- the catalog validates that every reference resolves to identical normalized content;
- the lock records package references at semantic-unit granularity; and
- a later package may add a disjoint unit without inheriting ownership of the existing baseline.

The shared resource is not an automatically enabled standard and does not appear as a consumer-selectable package.

## Package migration requirements

### Legacy whole-file recognition

V5 migration metadata carries offline signatures for known v4 whole-file payloads that become semantic contributions. The migrator handles each pre-existing target as follows:

- A byte-identical digest match to a known released payload produces a reviewed replacement action that removes the legacy whole-file body and installs only the new bounded units.
- A file with a declared legacy structural signature but a different digest is ambiguous local modification. It produces a conflict and no new block is inserted, preventing stale and current instructions from coexisting silently.
- A file with no known payload digest or structural signature remains consumer-owned. The normal missing-unit insertion rules apply.
- A file containing both a legacy signature and a current managed block is a cleanup conflict until the duplicate legacy content is resolved.

Signatures are versioned package migration data, not network lookups or heuristic guesses. The plan names the recognized payload version, the content to be retired, the replacement units, and every preserved consumer region.

### Python Tooling

- Replace `pyproject.toml` fragment reporting with typed TOML contributions.
- Replace whole `AGENTS.md`, `CLAUDE.md`, VS Code settings, and VS Code tasks artifacts with bounded contributions.
- Reference shared EditorConfig properties and extension recommendations by stable identity.
- Retain exclusive ownership of `.python-version`, `scripts/check.py`, and its workflow caller.

### Markdown Tooling

- Reference the same shared EditorConfig properties and extension recommendations.
- Retain exclusive ownership of its lint/format configuration and distinct workflow callers.
- Preserve its physical-formatting authority without claiming unrelated semantic keys in shared containers.

### Agent Handoff

- Retain bounded instruction and harness-registration contributions.
- Move legacy `.project-standards.yml` settings into unified package options.
- Retire the package-specific provenance lock after central-lock migration while preserving consumer-owned handoff documents.

### Other current packages

- Convert `.project-standards.yml` fragments into package option schemas.
- Keep unique templates, skills, workflow callers, and package documents as exclusive or create-only artifacts.
- Declare read-only authorities separately from mutation ownership; validation authority does not grant write access.

## Manifest and lock consequences

`SPEC-BA02` must define versioned contribution declarations and adapter-specific ownership scopes. Catalog validation must reject:

- unsupported adapters or ambiguous selectors;
- path traversal or non-repository destinations;
- overlapping mutable scopes without one identical shared identity;
- shared identities with different values or digests;
- whole-file ownership combined with nested contributions at the same target;
- duplicate Markdown block IDs, task labels, hook identities, extension IDs, or normalized key paths; and
- a provider output broader than its declared contribution scope.

The central lock must record, per semantic unit:

- target, adapter, and normalized scope;
- owner or shared-reference set;
- selected package and payload version;
- source or provider provenance;
- normalized semantic digest;
- install policy; and
- enough creation evidence to decide whether an empty container may be removed.

The lock does not claim unowned container bytes. Whole-file precondition digests protect execution concurrency, while semantic-unit digests own drift and lifecycle decisions.

## Error behavior

Every conflict is reported before writes and identifies the target, normalized scope, current owner or consumer state, requesting package, and safe next action. Stable conflict classes include:

- package/package scope overlap;
- package/consumer value conflict;
- malformed or unsupported container syntax;
- ambiguous duplicate semantic identity;
- modified managed unit;
- incompatible shared contribution;
- ambiguous legacy payload modification;
- unresolved legacy cleanup;
- provider output outside declared scope; and
- unsafe container deletion.

The platform provides no force flag that silently chooses a package or overwrites consumer content. Resolution requires a supported package option, declared migration, explicit consumer edit, or revised standard contract.

## Verification contract

### Adapter suites

Each adapter requires fixtures for create, adopt-equal, update, no-op, preserve, remove, malformed input, duplicate identity, consumer conflict, package overlap, local modification, and concurrent precondition failure. Round-trip fixtures must contain comments, unusual ordering, alternate quoting, trailing commas where supported, and unrelated content that remains byte-identical. Markdown-block fixtures must run every sanctioned formatter over a managed container and then reconcile to `no-op`, or prove that the declared formatter exclusion remains effective.

### Composition suites

The installed-wheel compatibility suite must prove:

- every current package reconciles independently;
- every package pair and the full supported set perform a real apply;
- package input order does not change the final bytes or lock;
- canonical ordering changes placement only and never resolves a conflicting value;
- Python Tooling, Markdown Tooling, and Agent Handoff compose on all shared surfaces;
- enable, update, disable, re-enable, and removal preserve consumer content;
- shared units remain until the final reference is removed;
- any conflict blocks the complete plan before the first write; and
- interrupted multi-target apply remains recoverable under the prior lock.

### Migration suites

Fixtures must cover fresh repositories and representative existing consumers with:

- pre-existing compatible and conflicting `pyproject.toml` keys;
- byte-identical known-v4 Python Tooling `AGENTS.md`, `CLAUDE.md`, VS Code settings, and VS Code tasks files that migrate without retaining the legacy whole-file body;
- byte-identical known-v4 shared EditorConfig and extension-recommendation files that decompose into semantic units without duplication or content loss;
- structurally recognized but locally modified v4 instruction files that block without inserting duplicate managed blocks;
- combined consumer and package blocks in agent instructions;
- JSONC comments and consumer-defined VS Code settings, tasks, and recommendations;
- customized EditorConfig sections;
- existing distinct workflow callers; and
- legacy `.project-standards.yml` fragments from every current package.

## Documentation and decision integration

This design is a prerequisite input, not a replacement for the controlling contracts:

- ADR 0023 records consumer-owned containers, typed contributions, executor-only mutation, and the no-precedence rule while extending ADR 0004.
- `SPEC-BA02` defines the exact versioned manifest schema, adapter selectors, shared identities, and provider-output bounds.
- `SPEC-CP01` owns planning, apply, lock, migration, recovery, and package compatibility behavior.
- Package standards document their owned semantic units and supported conflict-resolution options.
- The later `project-toolbox` package follows the same block/key model and never becomes a required root-container owner.

## Scope boundaries

### Included

- Ownership and lifecycle semantics for current shared, root, and externally discovered artifacts.
- Adapter-level preservation and conflict requirements.
- Current-package migration decisions and verification expectations.
- Required inputs to ADR 0023, `SPEC-BA02`, and the control-plane implementation plan.

### Deferred

- Exact TOML/JSONC/YAML/EditorConfig library selection and performance benchmarks.
- Final manifest field names and generated schema layout, owned by `SPEC-BA02`.
- Exact per-property and per-extension ownership plus shared identities for the current `_shared` payloads, assigned by the package-migration payloads under `SPEC-BA02`.
- Package-specific configuration choices such as alternate Python type checkers.
- Workflow-installation methodology for `project-toolbox`, which receives its own ADR.
- Repository-host settings governed by the future `agent-managed-repo` standard.

### Excluded

- Package precedence or implicit conflict resolution.
- Automatic rewriting of ambiguous consumer content.
- Moving conventional artifacts under `.standards/` when external tools require their current paths.
- Making any standard depend on Python Tooling, Markdown Tooling, Agent Handoff, or `project-toolbox` solely to obtain a shared container.

## Acceptance criteria

The design is ready to feed ADR and specification work when:

- every current artifact destination has a declared V5 ownership model;
- the consumer/container, package/unit, platform/executor, and shared-reference boundaries are unambiguous;
- install, update, drift, disable, and removal behavior preserve unrelated content;
- no package-order or precedence rule exists;
- adapter contracts prohibit destructive reserialization;
- `SPEC-BA02` and ADR 0023 inputs are explicit; and
- owner review confirms the per-surface mapping and shared baseline policy.
