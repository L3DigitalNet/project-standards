# Standard Bundle Authoring Standard

The "standard for standards": the contract every standard bundle under `standards/{id}/` must declare so the repository can be discovered and composed mechanically by the standards graph, and eventually by an MCP server, without hardcoding each standard.

## Purpose & status

This standard closes a gap: the repository defines standards as bundles under `standards/{id}/`, but nothing said what a bundle must declare, and the nine current bundles diverge (seven ship packaged adopt-artifact manifests, `python-coding` is an unregistered draft, and this meta-standard is internal/reference-only). This document is the single, machine-checkable authoring contract that closes it. It realizes [adr-0001](../../docs/adr/adr-0001-standard-bundle-authoring-contract.md) and is the `SPEC-MT01` Step 02 deliverable.

It is an **internal / reference** standard: it governs how this repository authors its own standards. Its adoption mode is `none` — there is **no `adopt.md`**, no copy-adopt bundle, and no `registry.json` contract version, because no downstream repository authors its own standards today. It still ships its own [`standard.toml`](standard.toml) so the repository dogfoods the contract it defines.

The contract is enforced by the bundled `standard.toml` schema, typed model, fixture corpus, and `project-standards standards validate-graph` gate implemented in `SPEC-MT01` Steps 03–04. This document remains the author-facing source of truth; the machine layer rejects drift from the contract.

## Bundle anatomy

A standard bundle is the directory `standards/{id}/`. The `{id}` is kebab-case and is the standard's identity everywhere (directory name, `standard.toml` `id`, cross-references).

| File / directory | Required? | Purpose |
| --- | --- | --- |
| `README.md` | **Required** | The canonical standard: the human- and agent-readable contract. |
| `standard.toml` | **Required** | The machine manifest (identity, adoption, config, capabilities, authorities, relations, resources, providers). |
| `adopt.md` | Required _if adoptable_ | The adoption guide. Present for every standard **released for adoption** — `validator`, `copy-adopt`, and `cli` alike. |
| _non-adoptable marker_ | Required _if not_ | A standard with `adoption = "reference-only"` or `adoption = "none"`, or an unreleased draft, carries an explicit non-adoptable note **instead of** `adopt.md`. |
| `templates/` | Optional | Blank, annotated files an author or the adopt engine materializes. |
| `examples/` | Optional | Worked, validated examples that dogfood the standard. |
| `skills/` | Optional | Standard-owned agent skills installed into consuming repositories by the adoption path. |
| `hooks/{hook-id}/` | Optional | Canonical source for a standard-owned executable hook. Adoption installs it under the shared project-local hook root. |
| `resources/` | Optional | Additional lazy-loadable bundle content addressed by resource ID (see [Resources](#resources)). |
| `agent-summary.md` | Expected | A condensed, token-cheap view for agents; never the source of truth. If omitted, the canonical `README.md` records why a summary would not be useful. |

**`adopt.md` presence is independent of adoption _mode_.** Any standard released for adoption keeps its `adopt.md`, including CLI-enforced ones like `project-spec` (`adoption = "cli"`). Only `adoption = "none"` (internal) standards and unreleased-draft documents replace it with the explicit non-adoptable marker. This standard is the first `adoption = "none"` case.

## The `standard.toml` manifest

Every bundle carries a `standard.toml` — stable, validated metadata that machine consumers read without parsing prose ([adr-0002](../../docs/adr/adr-0002-manifest-first-standard-discovery.md)). The manifest below is a complete annotated example for a representative _adoptable_ standard (`markdown-tooling`) so every table is realistic; each comment marks a field **required** or **optional**. The field _names_ shown here are the contract — this standard's own manifest and the [template](templates/standard.toml) use exactly these keys.

Package and contract versions follow [ADR 0020](../../docs/adr/adr-0020-standard-package-versioning-methodology.md): each package declares its current version and every version it still supports.

```toml
[standard]
id = "markdown-tooling"       # required — kebab-case, matches the directory name
name = "Markdown Tooling"     # required — human-readable display name
status = "active"             # required — draft | review | active | deprecated | archived (| superseded)
summary = "Formatting and structural linting for Markdown and adjacent structured text." # required
adoption = "copy-adopt"       # required — validator | copy-adopt | cli | reference-only | none

[versions]
supported = ["1.0", "1.1"]    # required — every package/contract version still accepted; never empty
latest = "1.1"                # required — the current default package/contract version; must be in supported

[config]
namespaces = ["markdown_tooling"] # required — dotted paths this standard owns in .project-standards.yml (may be [])

[capabilities]
provides = ["markdown.format", "markdown.lint.structure", "yaml.format", "json.format"] # required (may be [])
consumes_platform = []        # required — generic platform capabilities consumed, never other standards (may be [])

[relations]
companions = ["markdown-frontmatter"] # optional — advisory only, never auto-required
extends = []                  # optional — explicit, ADR-backed extension only
conflicts = []                # optional — exceptional; prefer redesign

[resources]
readme = "README.md"          # required — bundle-relative, contained
adopt = "adopt.md"            # required for validator/copy-adopt/cli; omit for reference-only/none
agent_summary = "agent-summary.md" # expected compact view; target <= 3,000 UTF-8 bytes

[artifacts]
manifest = "src/project_standards/bundles/markdown-tooling/adopt.toml" # optional — required when packaged artifacts exist

[[authority]]                 # optional — one block per owned concern
domain = "markdown"
target = "**/*.md"
concern = "physical-formatting"
owner = "prettier"
mutates = true

[[authority]]
domain = "markdown"
target = "**/*.md"
concern = "structure-lint"
owner = "markdownlint"
mutates = false

[[providers]]                 # optional — one block per generic operation
operation = "drift-check"
kind = "python"               # python | command | workflow | documentation-only
entrypoint = "project_standards.markdown_tooling:check_drift" # import path or command — NOT a filesystem path
optional = true
```

## Adoption modes

`adoption` classifies **how** a standard reaches a consumer repository, so today's outliers are first-class rather than special cases ([adr-0001](../../docs/adr/adr-0001-standard-bundle-authoring-contract.md), [ADR 0017](../../docs/adr/adr-0017-unified-standard-adoption-methodology.md)). The vocabulary is exactly:

| Mode | Meaning | Current standards |
| --- | --- | --- |
| `validator` | Enforced by a Python validator downstream repos run via a reusable CI workflow. | `markdown-frontmatter`, `adr` |
| `copy-adopt` | Materialized config / scaffold files copied into the consumer repo by the adopt engine. | `python-tooling`, `markdown-tooling`, `cli-documentation` |
| `cli` | Enforced through a CLI command the consumer runs; may also seed repo-local support scaffolding through the artifact plane. | `project-spec` |
| `reference-only` | Guidance only — no validator, no materialized files, no CLI enforcement. | `python-coding` (draft) |
| `none` | Internal: governs how this repository authors standards; not consumer-adopted. | `standard-bundle-authoring` (this standard) |

The mode is schema-bound manifest metadata. `cli` names how `project-spec` compliance is enforced; static config and workflow support files still belong in `adopt.toml` when they are seeded into a consumer repository. Broaden the mode name (e.g. to `package-tooling`) only via a spec revision if a second CLI-enforced standard appears ([SPEC-BA01 OQ-001](../../docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md)).

## Authorities

An **authority** is a declared claim that a standard governs some concern over some files, so conflict-free composition is provable from data rather than prose ([adr-0004](../../docs/adr/adr-0004-authority-map-and-conflict-free-composition.md)). Each `[[authority]]` block is the tuple:

```text
(domain, target, concern, owner, mutates)
```

- `domain` — the subject area, e.g. `markdown`.
- `target` — a glob over consumer-repo files the authority applies to, e.g. `**/*.md`.
- `concern` — the specific aspect governed, e.g. `physical-formatting` or `structure-lint`.
- `owner` — the tool or component that exercises the authority, e.g. `prettier`.
- `mutates` — whether exercising it rewrites files (`true`) or only inspects them (`false`).

**Conflict rule.** Two **mutating** authorities conflict when they share a `domain` and `concern` and have **overlapping** `target` globs but **different** owners — _unless_ an explicit, ADR-backed [`extends`](#relationships) relation reconciles them. Non-mutating authorities (validators) may overlap freely when their concerns are distinct or one is advisory. This is what lets an arbitrary set of standards be adopted together and still be proven not to fight over the same bytes.

## Relationships

Relationships between standards are **explicit graph data, not prose implications** ([adr-0013](../../docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md)). The default relationship between any two standards is `independent`.

| Relationship | Meaning | Effect |
| --- | --- | --- |
| `independent` | No relationship declared (the default). | Either standard may be adopted alone. |
| `companion` | Often useful together. | A planner may _recommend_ the companion but must never require it. |
| `extends` | One standard intentionally builds on another's authority/schema. | Surfaced explicitly; requires an ADR, an acyclic graph, and compatible authorities. |
| `conflicts` | Standards cannot safely co-exist as designed. | A planner refuses the combination; must be exceptional and ADR-backed. |
| `consumes_platform` | The standard needs a generic platform capability (validation, package tooling). | Satisfied by platform/provider infrastructure, never by another standard. |

A manifest field named `requires` is **reserved and invalid** for standard-to-standard dependencies: there are no hidden hard dependencies. Use `relations.extends` for rare extension relationships and `relations.companions` for recommendations.

## Config-namespace ownership

A standard's consumer configuration lives under **dotted namespace paths** in `.project-standards.yml`. Ownership is per-path, so a shared parent can host children owned by different standards ([adr-0008](../../docs/adr/adr-0008-consumer-config-namespace-registry.md)).

- A namespace is a **dotted path** (`markdown.frontmatter`), not only a top-level key.
- A **parent** namespace (e.g. `markdown`) may be a shared _container_ whose child paths are owned by **different** standards; the parent itself is owned by no standard.
- **Meta keys** that are not part of any standard (e.g. `standards_version`) are **repo-owned** and reserved — no standard may claim them.
- Duplicate ownership of the **same** path by two standards is invalid.

The current repository maps without ambiguity:

| Namespace path | Owner | Note |
| --- | --- | --- |
| `markdown` | _(container — unowned)_ | Shared parent; not owned by any standard. |
| `markdown.frontmatter` | `markdown-frontmatter` | Child of the shared `markdown` container. |
| `markdown.adr` | `adr` | Sibling child, different owner — no conflict. |
| `markdown_tooling` | `markdown-tooling` | A single-segment dotted path (top-level). |
| `python_tooling` | `python-tooling` | Top-level. |
| `cli_documentation` | `cli-documentation` | Top-level. |
| `spec` | `project-spec` | Top-level. |
| `standards_version` | _(repo meta — reserved)_ | Not standard-owned. |

## Providers

A **provider** declares how a generic operation is fulfilled for this standard, so standard-specific behavior is pluggable rather than hardcoded into the tooling ([adr-0006](../../docs/adr/adr-0006-standard-provider-plugin-model.md)). Each `[[providers]]` block declares:

| Field | Meaning | Required? |
| --- | --- | --- |
| `operation` | The generic operation: `validate`, `fix`, `lint`, `drift-check`, `id-next`, `extract`, `render`, `scaffold`, `upgrade`, or `semantic-review`. | Yes |
| `kind` | `python`, `command`, `workflow`, or `documentation-only`. | Yes |
| `entrypoint` | An import path (`pkg.mod:func`) or command reference — **never a filesystem path**. | Required for executable kinds |
| `optional` | Whether the provider's absence blocks adoption. | Yes |

Providers cover the operations a graph or MCP server invokes generically across standards. A provider may also declare `input_schema` / `output_schema` (a structured or named built-in schema) — recommended for executable providers. A **missing optional provider is declared explicitly** (`optional = true`), never silently inferred.

When an executable provider runner loads a standard's declarations from the installed wheel, the standard also ships `src/project_standards/bundles/{id}/standard.toml`. This runtime mirror must be byte-identical to `standards/{id}/standard.toml`. Package and installed-wheel tests enforce parity because the manifest schema does not identify which provider runners need a runtime mirror; graph validation must not infer that requirement.

## Resources

A **resource** is a lazy-loadable piece of bundle content addressed by a stable, URI-safe ID that maps to a bundle-relative file path, so future resource / MCP consumers reference identifiers rather than paths ([adr-0010](../../docs/adr/adr-0010-standard-resource-uris-and-index.md)). The `[resources]` table maps IDs to paths:

- `readme` → `README.md` (required),
- `adopt` → `adopt.md` (adoptable standards),
- `agent_summary` → `agent-summary.md` (expected; omission requires a rationale in the canonical README),
- `template` → `templates/standard.toml`,
- `skill` / `skill_<name>` → files under `skills/`, when the standard owns an agent skill,
- and any bundle-specific IDs under `resources/`.

Resource IDs are lowercase, URI-safe tokens. Every path is **bundle-relative and contained** (see [Manifest safety](#manifest-safety)).

An `agent-summary.md` is a reviewed companion for routine context loading, not a second normative contract. It targets at most **3,000 UTF-8 bytes**, links to the canonical `README.md`, and includes this exact authority notice:

```markdown
The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.
```

If a useful summary cannot meet the target, record the exception and its rationale in the canonical README. If a bundle omits the summary entirely, the README must instead explain why a compact agent view would not be useful. Summary content must preserve lifecycle, adoption mode, core rules, commands or artifacts, boundaries, and companion relationships without weakening the canonical standard.

## Manifest safety

Future tooling trusts manifest-declared paths and providers, so the contract constrains them ([adr-0010](../../docs/adr/adr-0010-standard-resource-uris-and-index.md)):

- **Paths are bundle-relative and contained** within the declaring standard's own directory: no `..`, no absolute paths, no symlink escape. A path that resolves outside the bundle is invalid.
- **Cross-bundle sharing** is permitted only through the explicit shared-artifact (`_shared`) mechanism — never by pointing into a sibling bundle directly.
- A provider **`entrypoint` is an import path or command reference, not a filesystem path**.
- Providers are **first-party** and perform **no network access by default**.
- A missing **optional** provider is declared explicitly rather than inferred.

## Adoption resources and artifact linkage

The `standard.toml` manifest describes the standard; the **artifact plane** (`adopt.toml`) describes what an adopting repository receives. They stay separate ([adr-0003](../../docs/adr/adr-0003-separate-standard-and-artifact-manifests.md)). A standard that ships packaged artifacts links the repository-relative manifest through `[artifacts].manifest`; graph validation rejects missing and orphan links. Each `standard.toml` also either:

- **references its `adopt.md` adoption guide** through the `adopt` resource when `adoption` is `validator`, `copy-adopt`, or `cli`, or
- **explicitly declares non-adoptability** (`adoption = "reference-only"` or `adoption = "none"`, no `adopt` resource).

Artifact ownership, shared artifacts (`_shared`), destination-collision semantics, and installed file modes remain delegated to the artifact plane under [ADR 0019](../../docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md). Every `[[artifact]]` declares provenance: `source-owned` with a byte-identical repository-relative `canonical` source; `generated` with `canonical` plus a deterministic `transform`; `package-owned` for installed-tooling-only files; or `external-owned` for explicit `_shared` artifacts. An artifact's optional `install_policy` defaults to `managed`; `create-only` installs the artifact only when its destination is absent and is never overwritten, even when adoption uses `--force`. Written artifacts may declare an explicit POSIX `mode` as an octal string (for example, `mode = "0755"`) when the installed file must be executable; omit it for ordinary documents and configs, which use the adopt engine's normal umask/preserve-mode behavior.

Under [ADR 0021](../../docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md), standard-packaged skills install only under `.agents/skills/<skill-id>/`. Under [ADR 0022](../../docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md), a standard-owned hook's canonical source lives under `standards/{standard-id}/hooks/{hook-id}/`, and its source-owned artifact installs under `.agents/hooks/{standard-id}/` by default. Hook artifacts declare `provenance = "source-owned"`, a byte-identical canonical source, `install_policy = "managed"`, and an executable `mode`. Drift validation identifies changed or stale installed hooks, and only the package's owned upgrade path refreshes them after its normal precondition and ambiguity checks. Graph validation checks linkage, provenance parity, and the project-local skill and hook boundaries without re-inventing the adopt engine.

## Lifecycle & exceptions

A standard moves through the package lifecycle defined by [ADR 0018](../../docs/adr/adr-0018-standard-package-lifecycle-methodology.md), mirrored in `standard.toml` `status` so tooling can tell draft from active from retired:

```text
draft → review → active → deprecated → archived
```

`superseded` is the terminal state for a standard replaced by another (the replacement is named in the successor's frontmatter / manifest). Any **exception** to this contract — an outlier field, a conflict that cannot be redesigned away, a deviation from an authority rule — is recorded as an **ADR** in `docs/adr/`, never as an undocumented special case. The ADR trail is the auditable record of every deliberate divergence.

## Manual conformance checklist

The machine schema and graph validator are authoritative, but this checklist is the manual authoring quick-check. A `standard.toml` conforms when **every required field is present and well-formed**:

- [ ] `[standard]` — `id` (kebab-case, matches directory), `name`, `status` (a valid lifecycle state), `summary`, `adoption` (one of the five modes).
- [ ] `[versions]` — `supported` (non-empty array) and `latest` (non-empty string, present in `supported`) both present.
- [ ] `[config]` — `namespaces` present (array of dotted paths, may be empty); no path duplicates another standard's; no reserved meta key claimed.
- [ ] `[capabilities]` — `provides` and `consumes_platform` both present (arrays, may be empty).
- [ ] `[resources]` — `readme` present; `adopt` present **iff** `adoption` is `validator`, `copy-adopt`, or `cli`.
- [ ] Agent context — provide `agent-summary.md`, declare `resources.agent_summary`, target at most 3,000 UTF-8 bytes, link `README.md`, and include the exact canonical-authority notice; otherwise record the explicit omission or size-exception rationale in the canonical README.
- [ ] `[artifacts]` — present when a packaged `adopt.toml` exists; `manifest` names its safe repository-relative path; every artifact declares valid provenance.
- [ ] `hooks/{hook-id}/` — present when the standard owns a hook; the source-owned artifact installs under `.agents/hooks/{standard-id}/` with managed drift and executable mode declarations.
- [ ] `[relations]` — any of `companions` / `extends` / `conflicts` present are arrays; no `requires` field; every `extends` is ADR-backed.
- [ ] `[[authority]]` — each block (if any) declares `domain`, `target`, `concern`, `owner`, `mutates`; no mutating conflict per the [conflict rule](#authorities).
- [ ] `[[providers]]` — each block (if any) declares `operation`, `kind`, `optional`, and an `entrypoint` for executable kinds; `entrypoint` is an import path or command, not a filesystem path.
- [ ] Runtime `standard.toml` mirror — present and byte-identical in `src/project_standards/bundles/{id}/` when an executable provider runner loads declarations from the installed wheel; package/wheel tests enforce parity.
- [ ] All resource / template paths are bundle-relative and contained (no `..`, absolute, or symlink escape).

Schema/model changes must preserve this checklist's field set or record a deliberate supersession.
