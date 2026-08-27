---
spec_id: SPEC-GSF3
title: 'Durable Document References Optional Tooling'
status: draft
profile: standard
owner: 'Chris Purcell / L3DigitalNet'
implementer: 'Coding agent under human review'
created: '2026-07-31'
last_reviewed: '2026-08-27'
supersedes: null
superseded_by: null
related:
  adrs: []
  tickets: []
  repositories:
    - 'L3DigitalNet/project-standards'
  prior_specs:
    - 'SPEC-CP01'
    - 'SPEC-MS01'
---

# Durable Document References Optional Tooling — Specification (Standard)

## Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 0.1 | 2026-07-31 | Codex with owner-directed design decisions | Initial draft defining optional meta-repository tooling for canonical specification and ADR references, validation, graph generation, and guarded reconciliation. |
| 0.2 | 2026-08-27 | Claude, owner-directed currency audit (#178) | Currency audit against the repository at HEAD; no scope change. `project-toolbox` now exists as an active Catalog 5 package, so WH-004 and §2.4 record the real remaining gate instead of a planned family. §3.1 marks the 2026-07-31 corpus counts as a dated measurement that was not re-taken. IR-005 and new OQ-001 surface the previously unstated consumer-config `schema_version` obligation for a new top-level `[tools]` table. §References repins the Standards entries to the versions this repository currently resolves. |

**Spec lifecycle:** This draft formalizes the owner-approved design discussion but remains under review until the owner accepts this written specification. After approval, scope-affecting changes require a new revision and renewed approval. Implementation deviations belong in the [Deviations Log](#deviations-log), not silent requirement edits.

---

## 1. Purpose & Background

Project Standards documents use stable identifiers such as `SPEC-MT01` and `ADR 0025`, repository-relative Markdown links, and schema-specific relationship metadata. Those forms serve different purposes but are not composed by one repository-level authority. A stable identifier is searchable but not navigable; a Markdown link is navigable but its path can drift; and a `related:` entry records a deliberate editorial relationship rather than every mention or backlink.

The repository already validates Project Specification structure, ADR structure, and selected Markdown Frontmatter relationships independently. It also maintains human indexes such as `docs/specs/README.md`. No current tool proves that a formal identifier uniquely maps to its canonical document, that a linked identifier targets the document declaring that identity, that required prose and navigation references are linked consistently, or that repository-wide document relationships form a coherent graph.

This project adds optional tooling owned directly by the `project-standards` meta-repository and distributed in the main wheel. It composes existing public document contracts without becoming a standards package or making adoption of any standard depend on the tool. Version one optimizes for reliable human navigation and deterministic drift detection over specifications and ADRs. Its contracts leave room for later namespace adapters, caching, MCP exposure, or relocation to `project-toolbox`, but none is part of this release.

---

## 2. Scope

### 2.1 In Scope

- An optional `project-standards references` command group distributed in the main wheel.
- Tool-specific configuration independent of `[standards.*]` selections.
- Configured authored-corpus discovery with explicit index, historical, include, and exclude scopes.
- Canonical identity discovery for Project Specification and ADR documents.
- Deterministic validation of canonical IDs, first prose references, navigation references, local links, external-ID declarations, and supported relationship metadata.
- Typed error and advisory findings with equivalent human and versioned JSON reports.
- On-demand deterministic JSON and DOT document graphs.
- Preview-first reconciliation limited to mechanically certain link corrections.
- Source-tree, candidate-wheel, and installed-wheel verification against controlled fixtures and this repository's real corpus.

### 2.2 Out of Scope (Non-Goals — never)

| ID | Non-Goal | Reason |
| --- | --- | --- |
| NG-001 | Make the subsystem a standards package or a dependency of standards adoption. | Repository-level composition spans multiple document contracts and is optional meta-repository tooling. |
| NG-002 | Replace the Project Specification, ADR, Markdown Frontmatter, Markdown Tooling, or standards-graph validators. | Each existing owner continues enforcing its own schema and package contract. |
| NG-003 | Treat every body mention as a `related:` relationship or automatically curate relationship metadata. | Body references and deliberate editorial relationships have different semantics. |
| NG-004 | Commit a generated document graph or treat derived output as repository authority. | Authored Markdown and its declared identifiers remain the source of truth. |
| NG-005 | Operate a graph database, watcher, daemon, web interface, or interactive UI. | The local corpus does not justify an additional runtime or operational system. |
| NG-006 | Check the availability or health of external URLs over the network. | Network-dependent link health is nondeterministic and belongs to complementary tooling such as Lychee. |
| NG-007 | Rewrite prose or infer ambiguous document intent. | Reconciliation is restricted to edits with one provably correct canonical target. |

### 2.3 Won't Have in v1 (deferred — not never)

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | Namespace adapters beyond Project Specifications and ADRs. | The first release must prove the policy against formal identifiers before generalizing to every frontmatter ID. | A concrete repository requires another stable identifier family and supplies its canonical declaration and reference grammar. |
| WH-002 | Persistent or incremental scan caching. | On-demand scanning is simpler and avoids a second artifact lifecycle before performance evidence exists. | A recorded cold-run benchmark demonstrates a material performance need in a supported corpus. |
| WH-003 | MCP resources or tools for reference reports and graphs. | CLI-only delivery avoids adding protocol, response-size, security, and compatibility obligations to version one. | The CLI contracts are stable and an approved MCP use case requires remote exposure. |
| WH-004 | Relocation into the `project-toolbox` standard. | Direct meta-repository ownership is the approved initial boundary; relocation would be a separate compatibility decision. `project-toolbox` now exists as an active Catalog 5 package (1.1, enabled in this repository), but its delivered inventory is managed workflow checklists plus a routing skill, not wheel-distributed Python subsystems, so it does not yet own a surface of this shape. | The owner approves a migration preserving public contracts and `project-toolbox` gains a delivery form for wheel-distributed tooling. |
| WH-005 | Full cross-file transactional rollback for reconciliation. | Version one can preflight all edits and replace each file atomically without claiming a transaction the executor does not provide. | The mutation platform gains and proves an all-or-nothing multi-file transaction contract. |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| System owns | Tool configuration, corpus scanning, namespace composition, canonical registry, policy findings, graph schemas, reconciliation plans, CLI behavior, and wheel distribution. |
| System depends on | Authored Markdown, the Project Specification and ADR identity contracts shipped in the wheel, Markdown parsing helpers, repository configuration, and the existing guarded mutation executor. |
| System does not own | The content or lifecycle of consumer documents, package selection, standards adoption, external URL availability, editorial `related:` decisions, CI enablement in unconfigured repositories, or a `project-toolbox` relocation. |

---

## 3. Context

### 3.1 Current State

Project Specifications declare `spec_id` and use a dedicated nested `related` schema whose prior-spec relationships are bare specification IDs. Markdown Frontmatter documents use a different schema that prefers repository-root-relative paths for `related`, `depends_on`, `supersedes`, and `superseded_by`. The scopes are intentionally disjoint.

The current `validate-references` implementation is an opt-in Markdown Frontmatter pass. It checks ID uniqueness, date ordering, relationship resolution, supersession reciprocity, and ADR sequence uniqueness over its configured managed corpus. Unresolved references are advisory, body references are outside its scope, and well-formed nonlocal ADR IDs are assumed external. The standards graph separately models standard-package contracts, not document navigation.

The maintained specification index links canonical documents, but it is authored navigation rather than the identity authority. A 2026-07-31 audit found 355 Markdown lines containing `SPEC-` tokens and 22 containing linked `SPEC-` tokens; `SPEC-MT01` appeared on 140 lines and was linked on 14. These counts include contexts that the target policy will exempt, so they demonstrate inconsistent convention rather than a defect total. They are a dated one-off measurement and were deliberately not re-taken at revision 0.2; NFR-005 and MS-2 forbid deriving behavior from corpus counts, so their current values are not a requirement input.

### 3.2 Target State

An installed `project-standards` wheel always offers `project-standards references`, independently of selected standards packages. A repository may invoke the commands explicitly with configuration or equivalent scope arguments. It receives automatic aggregate-validation findings only after opting in under a distinct tooling namespace.

The subsystem derives a unique canonical ID-to-document registry from authored declarations, validates required body and navigation links, preserves schema-specific metadata forms, produces a typed document graph on demand, and previews only deterministic repairs. Authored Markdown remains authoritative; validation and graph commands never mutate it.

### 3.3 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | Repository-scale authored Markdown can be scanned on demand without a persistent cache or hard resource cap. | Pathological repository-owned Markdown may consume excessive CPU or memory or stall CI; v1 accepts that risk, records a cold-run benchmark, and may reconsider WH-002 or evidence-based limits in a later revision. |
| A-002 | The existing Markdown and frontmatter parsing surfaces can expose code ranges, links, headings, and supported relationship fields without changing their owners' semantics. | A shared parsing boundary must be added without duplicating grammars or weakening existing validators. |

### 3.4 Constraints

| ID | Constraint | Source |
| --- | --- | --- |
| C-001 | The feature is optional meta-repository tooling, not a standards package, and no standard selection enables it implicitly. | Owner-approved design. |
| C-002 | The command ships in the main wheel and is available independently of MCP. | Owner-approved ownership and v1 interface decisions. |
| C-003 | Project Specification and Markdown Frontmatter metadata retain their own schemas and reference forms. | Existing versioned package contracts. |
| C-004 | Authored Markdown and declared identifiers remain authoritative; generated graphs and reports are derived. | Owner-approved graph policy. |
| C-005 | Validation never mutates files; reconciliation is preview-first and apply requires explicit authorization. | Owner-approved reconciliation policy. |
| C-006 | Repository paths must be contained, symlink-safe, and handled through existing guarded mutation patterns. | Project Standards filesystem-safety contract. |
| C-007 | Version one recognizes only Project Specification and ADR formal identifier namespaces. | Owner-approved release scope. |
| C-008 | The schema and serialized report, graph, and plan envelopes are versioned public contracts. | Repository convention that schemas are versioned. |

---

## 4. Goals

| ID | Goal | Success Signal | Achieved By |
| --- | --- | --- | --- |
| G-001 | Make formal document references reliably navigable without linking every repeated mention. | Required first prose and navigation references resolve to the document declaring the referenced identity. | FR-004–FR-009 |
| G-002 | Detect objective document-reference drift through one optional repository-level gate. | Duplicate IDs, missing local identities, wrong targets, broken links, configured index drift, and unresolved supported relationships produce blocking findings. | FR-003, FR-004, FR-006, FR-008, FR-009, FR-011, FR-013 |
| G-003 | Expose document relationships without creating another source of truth. | Repeated graph runs over unchanged input produce identical unstamped JSON or DOT while writing no repository state by default. | FR-014, DR-004–DR-006, NFR-001 |
| G-004 | Repair only drift whose intended target is mechanically certain. | Reconciliation previews preconditioned edits, applies only unique canonical corrections, and refuses editorial or ambiguous changes. | FR-015–FR-019 |
| G-005 | Preserve optional, package-neutral ownership and future portability. | The wheel exposes the CLI without a selected standard or MCP server, and aggregate validation runs only when configured. | FR-001, FR-002, IR-001–IR-004 |

---

> **§5 (Stakeholders and Users) is Full-tier** and is intentionally omitted at the Standard profile.

## 6. Glossary

| Term | Definition | Notes / Not to be confused with |
| --- | --- | --- |
| Canonical document | The one local authored document that validly declares a formal identifier. | An index entry points to it but does not establish its identity. |
| Canonical registry | The derived, in-memory mapping from canonical identifiers and accepted aliases to canonical documents. | Not a committed registry file. |
| Formal identifier | A recognized specification or ADR reference token governed by an enabled namespace adapter. | Version one does not include every generic Markdown Frontmatter `id`. |
| First prose reference | The first non-exempt visible-prose occurrence of another local document's formal identifier. | Frontmatter, code, self-references, link destinations, autolink targets, raw URLs, path-like tokens, and configured historical content are excluded. |
| Linked reference | A formal-ID token contained in the visible label of an inline or reference-style Markdown link whose resolved target satisfies the applicable local or external identity rule. | A title-only link, destination-embedded token, autolink, or separate same-line link does not link or itself mention the formal ID. |
| Navigation surface | A configured index, or a Markdown section whose plain-text heading after trimming surrounding whitespace is exactly the case-sensitive word `References`, where listed formal document references must be linked. | The section ends at the next heading of equal or higher level. Configured indexes additionally own completeness for their declared namespace and roots; ordinary References sections do not. |
| Path-like token | A non-code token containing a path separator or ending in a filename extension whose span embeds a formal-ID-shaped substring. | It is not visible formal-ID prose and is never a reconciliation target; explicit Markdown links remain subject to broken-link checking. |
| Relationship metadata | Schema-governed fields such as `related`, `depends_on`, `supersedes`, `superseded_by`, and Project Specification `prior_specs`. | Their schema-specific forms and meanings remain distinct. |
| Current document | A local canonical document whose lifecycle status is not `superseded` and whose path is outside configured historical scope. | Superseded and historical documents do not produce orphan or missing-relationship advisories. |
| Strong relationship evidence | Reciprocal resolved `body-link` edges between two current local canonical documents when no stronger relationship already connects them. | It permits an advisory `related:` suggestion, never metadata mutation. |
| Orphan document | A current local canonical document with no inbound resolved edge from another authored document or configured navigation surface. | Self-edges and historical sources do not prevent orphan status. |
| Reference drift | A mismatch between a formal identifier, its declared canonical document, an explicit link target, a configured index, or supported relationship metadata. | External URL reachability is not reference drift in this subsystem. |
| Historical scope | Configured authored content checked for resolvable explicit links but exempt from first-reference and reconciliation requirements. | Historical files are not silently rewritten. |
| Derived graph | A deterministic, disposable node-and-edge projection built from the current identity and policy scopes. | It is not repository authority or a graph database. |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The system shall expose the reference subsystem from the main `project-standards` wheel without requiring any standards-package selection. | The meta-repository owns the optional cross-package composition. | Source-tree and installed-wheel probes invoke the command in a repository with no selected standard package. | Must |
| FR-002 | The system shall run aggregate reference validation only when `[tools.references].enabled` is true, while allowing explicit commands to run with configuration or equivalent CLI scope arguments. | Installation alone must not impose policy on consumers. | An unconfigured aggregate validation run emits no reference findings; explicit configured and CLI-scoped runs execute the same checks. | Must |
| FR-003 | The system shall separate identity discovery from policy enforcement. Enabled namespace adapters shall discover declarations at their recognized canonical document locations beneath the selected repository root, independently of `include`; `include`, configured indexes, and historical scope shall select documents for policy enforcement. `exclude` or equivalent CLI exclusion shall remove paths from both scopes, so generated files and fixtures receive no reference processing or identity authority. | Phased adoption must resolve legitimate canonical targets outside the enforced subset without allowing excluded copies to create identities. | Fixtures prove an in-scope document resolves an out-of-include canonical target, excluded declarations remain unknown, nested enforcement inclusion, historical classification, configured index coverage, and rejection of traversal or symlink escapes. | Must |
| FR-004 | The system shall build one canonical registry from the identity-discovery scope through enabled Project Specification and ADR declaration adapters before applying reference policy. The specification adapter shall recognize uppercase `SPEC-` plus four uppercase ASCII letters or digits. The ADR adapter shall recognize the declared lowercase canonical `adr-NNNN-repo-name-short-title` ID and the case-sensitive human aliases `ADR NNNN` and `ADR-NNNN`, with ASCII token boundaries; a numeric alias must resolve uniquely in the local identity scope. | Later checks must rely on unambiguous, bounded identity grammar without coupling identity to phased enforcement scope. | Valid fixtures map `spec_id`, ADR canonical IDs, and each accepted ADR alias to one document inside or outside `include`; case, boundary, near-miss, malformed, duplicate, excluded-declaration, and alias-collision cases fail or remain nonmentions as specified. | Must |
| FR-005 | The system shall require the first prose reference to another local document's formal identifier in each nonhistorical authored document to link to its canonical document. | Readers need one predictable navigation point without repeated-link noise. | Tests cover linked and unlinked first references, later plain mentions, self-references, title-only links, and multiple identifiers in one document. | Must |
| FR-006 | The system shall require every formal identifier in a list item or table row beneath a Markdown heading whose normalized text is exactly `References` to link to its canonical document until the next heading of equal or higher level. It shall also require each configured index to contain a correctly linked formal-ID entry for every canonical document within that index's declared namespaces and roots. | Ordinary References sections need link quality, while configured indexes own explicit, testable completeness boundaries. | Fixtures cover ordinary References lists/tables without completeness enforcement; configured indexes fail on bare, missing, duplicate, and wrong-target entries and pass complete correctly linked coverage. | Must |
| FR-007 | Within the authored corpus, the system shall exclude frontmatter, inline code, fenced code, self-identity declarations, link destinations, autolink targets, raw URLs, path-like tokens, configured historical content, and occurrences after a valid first link from first-reference enforcement. A title-only link is an ordinary link but neither mentions nor links a destination-embedded formal ID. Generated and fixture paths are outside both discovery scopes under FR-003 rather than a scanner-inferred class. | Nonprose and immutable contexts must not create noise, unsafe rewrite spans, or churn. | One fixture per structural exemption proves the token is not reported; title-only, destination/path, and later-visible-ID fixtures pin the visible-prose rule; FR-003 fixtures prove generated and fixture paths are not scanned. | Must |
| FR-008 | The system shall report every broken local Markdown link in the authored corpus as blocking and shall verify that a link whose label contains a formal identifier resolves to the canonical document declaring that identifier. | A local link must resolve, and a resolving link can still point to the wrong document. | Fixtures cover broken ordinary local links, ID-bearing missing and wrong targets, correct relative paths, and anchored links. | Must |
| FR-009 | The system shall treat enabled formal namespaces as local by default and resolve external formal identifiers only through explicit stable external links or configured `external_ids` mappings. | Shape alone cannot distinguish local from external ownership. | Unknown bare identifiers fail; mapped external IDs resolve for policy without document-graph nodes; external documents never enter the local canonical corpus. | Must |
| FR-010 | The system shall validate supported relationship metadata using its governing schema's reference form without rewriting it into another package's form. | Project Specification IDs and Markdown Frontmatter paths are intentionally different contracts. | Fixtures cover Project Specification `prior_specs` IDs and Markdown Frontmatter relationship paths without cross-schema normalization. | Must |
| FR-011 | The system shall fail unresolved relationship identifiers or paths and noncanonical local relationship paths as blocking drift at the exact source field. A `prior_specs` formal ID may resolve to one unique local specification or an explicit `external_ids` mapping; only a local resolution creates a `prior-spec` graph edge, while external, unresolved, and ambiguous values create no edge. | Existing relationship metadata must resolve deterministically without inventing remote graph nodes. | Fixtures cover local, externally mapped, unresolved, and ambiguous `prior_specs` values plus each supported path defect; blocking findings use relationship-specific codes and valid local relationships produce edges. | Must |
| FR-012 | The system shall report only advisories for strong-evidence missing `related:` suggestions between current documents, one-sided nonrequired relationships, orphan current documents, and a target duplicated in `related` plus a stronger supported relationship. | These bounded findings require editorial judgment or are deterministic cleanup opportunities outside the approved blocking list. | Exact-threshold and below-threshold fixtures bound strong-evidence suggestions; superseded and historical documents are excluded; every advisory class has a stable code, does not change exit `0`, and produces no reconciliation edit. | Must |
| FR-013 | The `check` command shall report all independent findings it can safely determine without modifying source or derived artifacts. | CI and maintainers need complete read-only evidence. | Before/after repository hashes are identical; human and JSON outputs contain equivalent findings and locations. | Must |
| FR-014 | The `graph` command shall emit deterministic JSON or DOT containing validated local nodes and typed edges for resolved local body links and supported relationship kinds. | Agents and humans need a disposable local relationship view without inventing remote document nodes. | Repeated unstamped output is byte-identical; edge fixtures cover `body-link`, `related`, `depends-on`, `supersedes`, `superseded-by`, and `prior-spec`, while external mappings produce no nodes or edges. | Must |
| FR-015 | The `reconcile` command shall produce a read-only typed preview by default and shall mutate files only with explicit `--apply`. Apply shall recompute the current plan in that invocation and shall not consume or persist a prior preview. | Repair must be intentional without introducing hidden reconciliation state or implying that separate invocations share one plan. | Default invocation changes no bytes; `--apply` is required to recompute, report, preflight, and execute a nonempty current plan. | Must |
| FR-016 | Reconciliation shall propose only a uniquely mapped bare visible-prose first-reference link, a formal-ID link whose target disagrees with its unique canonical mapping, or a configured index correction established by the entry's formal-ID label. It shall never rewrite a link destination, autolink target, raw URL, or path-like token. | Only provably correct visible-label edits are safe to automate. | Positive fixtures produce the exact bounded edits; destination/path spans, ambiguous labels, unknown IDs, and prose restructuring produce no plan entry. | Must |
| FR-017 | Reconciliation shall never add, remove, or infer `related:` entries or other editorial relationship metadata. | Editorial relationships are not equivalent to backlinks. | Relationship-advisory fixtures yield findings and an empty reconciliation plan. | Must |
| FR-018 | An apply operation shall verify repository containment and every content-hash precondition as a group before replacing any file. | Stale previews and unsafe paths must fail before mutation. | A stale or unsafe plan exits nonzero with all targeted source files unchanged. | Must |
| FR-019 | Apply shall replace each changed file atomically and shall not claim cross-file transactional rollback in version one. | The interface must match the executor's actual guarantee. | Interruption tests show no truncated individual target; documentation states the bounded multi-file guarantee. | Must |
| FR-020 | The subsystem shall preserve existing standards-package validator behavior and keep the standards package graph distinct from the document graph. In aggregate output, existing and new findings shall retain distinct stable code namespaces and their own severities; overlapping findings may both appear with source attribution rather than silently changing an existing validator's result. | Optional composition must not create hidden package coupling or conceal intentional policy differences. | Existing validator and standards-graph suites remain green; an overlapping-defect fixture proves source attribution and unchanged standalone severity; reference graph schemas use distinct names and entry points. | Must |

### 7.2 Non-Functional Requirements

| ID | Category | Requirement | Measurement / Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| NFR-001 | Determinism | Unstamped findings, graphs, and reconciliation plans shall use stable ordering and serialization. | Two runs over identical bytes produce byte-identical JSON, DOT, and plan output. | Must |
| NFR-002 | Safety | Read operations shall perform no network calls and shall not modify authored source. `check`, reconciliation preview, and `graph` without an output path write no repository bytes; an explicit graph output may create or replace only its guarded target outside both identity and policy scopes. | Network-denied and scoped repository-hash tests pass for each read path; output tests reject identity-scope, policy-scope, symlinked, and non-regular targets and prove explicit publication changes only the named guarded target. | Must |
| NFR-003 | Compatibility | Human and JSON modes shall expose the same semantic findings, locations, severities, and limits through versioned envelopes. | Contract tests compare normalized human and JSON records and reject unknown envelope versions. | Must |
| NFR-004 | Portability | The subsystem shall behave equivalently from the source tree, candidate wheel, and installed wheel on supported Python platforms. | Distribution probes compare command availability, exit status, and normalized JSON output. | Must |
| NFR-005 | Performance | Implementation shall record a reproducible cold-run benchmark over this repository. | Benchmark method, environment, corpus shape, and measured result are recorded without hardcoded corpus counts. | Must |
| NFR-006 | Maintainability | Namespace-specific declaration and alias rules shall be isolated behind adapters while policy consumes a common typed document model. | Unit tests replace each adapter independently and policy tests use adapter-neutral records. | Must |
| NFR-007 | Diagnostics | Findings shall use stable codes and one-based physical source locations without echoing unrelated document content. | Golden tests cover codes, coordinates, bounded messages, and redaction of nonessential content. | Must |

### 7.3 Interface Requirements

| ID | Interface | Requirement | Contract / Format | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| IR-001 | CLI group | The wheel shall expose `project-standards references {check,graph,reconcile}`. | Existing top-level CLI dispatch; common `--root`, configuration, and output options. | Source and wheel `--help` snapshots expose exactly the approved v1 commands. |
| IR-002 | Command status and check output | Every subcommand shall use exit `0` only when the operation succeeds with no blocking findings, including advisory-only output; exit `1` for policy, drift, identity, publication, precondition, apply, or unexpected internal failure; and exit `2` for invocation or configuration error. Reconciliation preview and successful apply still exit `1` when blocking findings remain. `check` shall support human output and `--json`. | Versioned finding-report envelope and one stable group-wide exit contract. Unsafe corpus scope or an invalid output target, including a symlink, non-regular object, or path in either reference scope, is error `2`; an otherwise valid guarded output target that cannot be published is error `1`. | A status-matrix test covers every subcommand and ERR-001–ERR-008, including preview/apply with remaining findings; check modes have equivalent normalized content. |
| IR-003 | Graph output | `graph` shall emit JSON by default and DOT with `--format dot`; output is stdout unless an explicit guarded path outside both identity and policy scopes is supplied. | Versioned graph envelope or deterministic DOT; existing regular-file target requires explicit overwrite; symlinked, non-regular, and reference-scope targets are invalid. | Output-path tests cover stdout, new file, overwrite refusal, symlink/directory/identity-scope/policy-scope refusal, and no truncation. |
| IR-004 | Reconciliation output | `reconcile` shall emit a versioned typed plan by default. `reconcile --apply` shall rescan and recompute a new current plan, emit that plan in the selected output mode, and preflight its hashes immediately before writes; it shall not accept a prior plan as input in v1. | Plan carries repository identity, source paths, edits, and content-hash preconditions; a preview from another invocation is informative, not an apply token. | Preview/apply and intra-invocation stale-precondition tests pass in human and JSON modes. |
| IR-005 | Tool configuration | `.standards/config.toml` shall accept an optional `[tools.references]` namespace separate from `[standards.*]`, and every existing config that omits it shall keep its current parse, resolution, rendering, and digest behavior unchanged. | Closed schema with `enabled`, `include`, `exclude`, `historical`, `indexes`, `namespaces`, and `external_ids`. At least one effective authored or index path must resolve; an explicit or enabled aggregate run with no effective corpus is configuration error `2`. The consumer-config document is a versioned contract whose top level is closed (`additionalProperties: false` over `project_standards` and `standards`), so introducing a sibling `[tools]` table is a config-schema change governed by OQ-001. | Schema tests accept the documented configuration, reject unknown keys, preserve configs without the namespace, and reject absent or empty effective scope without a vacuous green result. A compatibility test proves a config that omits `[tools]` produces byte-identical rendering and an unchanged `config_digest`. |
| IR-006 | Aggregate validation | `project-standards validate` shall include reference findings only when `[tools.references].enabled = true`. | Existing aggregate report conventions; no selected package implied. | Enabled and disabled integration fixtures produce the expected aggregate result. |

### 7.4 Data Requirements

| ID | Data Entity | Requirement | Validation Rules | Ownership |
| --- | --- | --- | --- | --- |
| DR-001 | Parsed document record | The scanner shall retain repository-relative path, declared identity, title, document kind, lifecycle status, structural ranges, links, mentions, and supported relationship values needed by policy. | Path contained; ranges physical and nonoverlapping; values preserve governing-schema semantics. | Derived in memory by reference tooling. |
| DR-002 | Canonical registry entry | Each local canonical identifier shall map to exactly one parsed document and zero or more unambiguous accepted aliases. | Duplicate canonical IDs or alias collisions are blocking; external mappings are separate. | Derived in memory from authored declarations. |
| DR-003 | Finding report | Each finding shall carry schema version, stable code, severity, path, physical location when available, message, and guidance. | Closed envelope; deterministic order; unrelated source content omitted. | Derived output owned by reference tooling. |
| DR-004 | Graph node and edge | Each local canonical document and referencing authored source shall have a deterministic node identity; each valid relationship between local graph nodes shall have a typed directed edge. | Nodes unique; edges sorted and deduplicated; unresolved and externally mapped identities are not graph nodes or edges. | Disposable output owned by reference tooling. |
| DR-005 | Reconciliation plan | Each planned file shall carry its source digest and each edit shall identify a bounded source span and replacement. | Closed schema; nonoverlapping edits; all targets contained; preconditions mandatory. | Ephemeral operator-reviewed output. |
| DR-006 | Persistent state | The subsystem shall persist no cache, graph, registry, or reconciliation state by default. | A complete read-only run leaves the repository and user configuration unchanged. | Authored Markdown remains consumer-owned authority. |

---

## 8. Architecture and Design

### 8.1 Architecture Summary

The subsystem is a main-wheel Python module behind a thin top-level CLI group. Discovery resolves two related scopes: adapter-recognized canonical locations for identity, and configured authored, index, and historical paths for policy enforcement. Configured exclusions apply to both. One Markdown scanner parses every selected file at most once and exposes frontmatter, structural ranges, explicit links, and visible formal-ID mentions through a common typed record. Namespace adapters interpret only their own declaration, canonical-location, and alias contracts: Project Specification maps `spec_id`, while ADR maps its canonical frontmatter ID and supported human reference forms.

The canonical registry rejects ambiguous identity before policy, graph, or reconciliation relies on it. The policy checker consumes registry and parsed records to produce typed findings. The graph builder consumes only validated identities and relationships; unresolved references stay findings rather than becoming invented nodes. The reconciliation planner converts an allowlisted subset of findings into preconditioned span edits. Application delegates containment and atomic file replacement to the guarded mutation boundary after verifying every plan precondition.

No command requires the MCP server or a selected standards package. Existing package validators remain authoritative for their own schemas; this subsystem composes their public meanings at repository scope.

### 8.2 Architecture Views

```text
adapter identity scope --> Markdown scanner --> namespace adapters --> canonical registry
                               ^                                        |
                               |                                        v
configured policy scope ------+-------------------------------> typed policy records
                                                                        |
                                              +-------------------------+------------------+
                                              |                         |                  |
                                              v                         v                  v
                                        policy checker            graph builder   reconciliation planner
                                              |                         |                  |
                                              v                         v                  v
                                        finding report              JSON / DOT    preview / guarded apply
```

| Component | Responsibility | Interfaces | Failure Boundary |
| --- | --- | --- | --- |
| Corpus discovery | Resolve adapter-owned identity locations plus configured authored, index, historical, and shared exclusion scopes. | Repository root, namespace adapters, and `[tools.references]`. | Invalid or escaping paths fail configuration; excluded paths enter neither scope. |
| Markdown scanner | Parse each file once and expose structure, links, mentions, and metadata. | Typed parsed-document records. | An unreadable or malformed governed document blocks identity-dependent output. |
| Namespace adapters | Interpret declaration, canonical ID, and alias grammar for specs and ADRs. | Adapter-neutral identity candidates. | Malformed declarations produce source-located findings. |
| Canonical registry | Enforce unique local identity and explicit external separation. | Lookup by canonical ID or accepted alias. | Duplicate or ambiguous identity blocks graph and reconciliation. |
| Policy checker | Apply link, navigation, exemption, relationship, and severity rules. | Versioned findings. | Reports all safely independent findings. |
| Graph builder | Build deterministic path/canonical nodes and typed edges. | JSON and DOT renderers. | Refuses identity-invalid or partial graphs. |
| Reconciliation planner | Produce only allowlisted deterministic edits. | Versioned change plan. | Ambiguous intent remains a finding with no edit. |
| Guarded executor | Verify the complete plan and publish atomic per-file replacements. | Existing mutation safety boundary. | Stale or unsafe plans fail before any write. |

### 8.3 Design Decisions

| ID | Decision | Rationale | Alternatives Considered | ADR |
| --- | --- | --- | --- | --- |
| D-001 | Own and distribute the subsystem directly from the meta-repository as optional main-wheel tooling. | No one standards package owns cross-document composition, and adoption must remain independent. | Project Specification ownership; ADR ownership; a new standards package; initial `project-toolbox` ownership. | None; this specification records the feature boundary. |
| D-002 | Use declared document ID as identity and repository-relative path as current location. | IDs survive moves while links remain human-navigable and checkable. | Treat index or filename as identity. | None. |
| D-003 | Require the first prose reference and every navigation entry to link, while permitting later plain mentions. | This provides predictable navigation without repetitive-link clutter. | Link every occurrence; link only indexes. | None. |
| D-004 | Classify objective violations as blocking and editorial interpretations as advisory. | CI must fail on deterministic drift without blocking on guesses. | All warnings; all findings fatal. | None. |
| D-005 | Keep `related:` curated and never derive it from body mentions. | A deliberate nearby-document recommendation is not an exhaustive backlink. | Mirror every body link into metadata. | None. |
| D-006 | Generate graphs on demand and persist no authoritative graph or database. | Markdown remains reviewable authority and v1 avoids another lifecycle. | Committed graph; graph database; persistent cache. | None. |
| D-007 | Make reconciliation preview-first and restrict apply to uniquely determined link edits. | Automatic editorial changes would be unsafe and hard to review. | Report-only forever; broad self-healing. | None. |
| D-008 | Treat configured namespaces as local by default and require explicit external mappings or links. | Identifier shape cannot prove repository ownership. | Assume every unresolved well-formed ADR is external. | None. |
| D-009 | Ship CLI-only in v1 while versioning machine contracts for later MCP consumption. | MCP exposure adds no v1 capability and expands protocol and security scope. | Ship CLI and MCP together. | None. |

> **§8.4 (Solution Alternatives Considered) is Full-tier** and is intentionally omitted at the Standard profile.

### 8.5 Design Constraints

- Package-specific schemas and validators remain the sole authorities for their document shapes.
- Namespace adapters may interpret declared public contracts but may not silently widen their accepted grammar.
- The document graph and standards package graph use distinct models, schemas, commands, and terminology.
- One scanner owns Markdown occurrence classification; policy, graph, and reconciliation may not implement competing regular expressions.
- Unresolved or ambiguous references remain findings and never become guessed graph nodes or edits.
- `check` never writes, and `graph` writes no repository state except an explicitly requested guarded output target outside both identity and policy scopes; neither command modifies authored source.
- Reconciliation validates the entire plan before its first write and publishes each target with atomic replacement.
- Version-one reports, graphs, and plans are unstamped.

> **§8.6 (Dependency Policy) is Full-tier** and is intentionally omitted at the Standard profile.

---

## 9. Data Model

The subsystem owns no durable datastore. Its public data model consists of versioned serialized views over current authored Markdown.

| Entity | Identity | Required Content | Integrity Rules |
| --- | --- | --- | --- |
| Document | Repository-relative path | Kind, declared ID when present, title/status when available, structural ranges, links, mentions, relationships. | One record per selected regular file; contained canonical path. |
| Canonical identity | Namespace plus canonical ID | Canonical document path and accepted aliases. | One local target; aliases cannot collide across local identities. |
| External identity | Formal ID | Stable external target URL. | Explicit configuration; cannot shadow a local canonical identity. |
| Finding | Code plus source locus and deterministic ordinal | Severity, path, line/column when available, message, guidance. | Closed schema and stable ordering. |
| Graph node | Canonical ID for local identity-bearing documents; path for other local referencing documents | Display path, title, kind, and status. | Local canonical nodes unique; configured external identities do not become graph nodes. |
| Graph edge | Source, target, and relationship type | Typed directed relationship and source locus. | Resolved only, sorted, deduplicated; unlinked mentions are diagnostics rather than valid edges. |
| Reconciliation plan | Repository identity plus plan schema version | Target files, source digests, ordered nonoverlapping span edits. | Every target contained; every precondition required; no editorial relationship edits. |

JSON envelopes use distinct initial schema identifiers for finding reports, graphs, and reconciliation plans. Schema names and exact field sets are frozen by contract tests before release. DOT is a deterministic rendering of the graph envelope, not an independent data authority.

---

## 10. Behavior and Workflows

### 10.1 Primary Workflow

1. The operator runs `project-standards references check --root .`, or aggregate validation dispatches the check for an enabled repository.
2. Configuration resolves from `.standards/config.toml` or explicit equivalent CLI scope arguments.
3. Discovery resolves adapter-owned identity candidates independently of `include`, selects the configured policy corpus, and removes shared exclusions from both.
4. The scanner parses every selected file at most once into typed records while excluding destinations, paths, code, and other nonprose contexts from first-reference analysis.
5. Namespace adapters build identity candidates across canonical locations; the canonical registry validates uniqueness and local/external separation before policy evaluates the configured subset.
6. The policy checker validates references and relationships and emits deterministically ordered findings.
7. Human output summarizes findings, or `--json` returns the versioned envelope.
8. The process exits `0` for clean or advisory-only output, `1` for blocking findings, or `2` for invocation/configuration failure.

Expected result: maintainers and CI receive one repository-level account of objective reference drift without any source mutation.

### 10.2 Alternate Workflows

| ID | Trigger | Behavior | Expected Result |
| --- | --- | --- | --- |
| AW-001 | Operator requests `references graph`. | The system performs the same discovery and identity validation, then renders validated nodes and edges as JSON or DOT. | Deterministic graph on stdout or at an explicitly guarded non-authored output path. |
| AW-002 | Operator requests `references reconcile`. | The system performs checking and converts only allowlisted uniquely determined findings into a typed preview. | Reviewable plan; no source changes. |
| AW-003 | Operator invokes `references reconcile --apply`. | The system rescans, recomputes and emits the current plan, verifies every path and digest, then atomically replaces each planned target. | Safe deterministic links updated; remaining findings reported; a prior preview is not consumed as apply input. |
| AW-004 | Repository lacks tool configuration but the operator supplies equivalent scope arguments. | The system runs explicitly without enabling aggregate validation or selecting a standard. | Same semantic check under ephemeral CLI scope. |

### 10.3 Edge Cases

| ID | Edge Case | Expected Behavior |
| --- | --- | --- |
| EC-001 | Two local documents declare the same canonical ID. | Both declarations are reported; graph and reconciliation refuse to run. |
| EC-002 | An ADR alias collides with another canonical identity or alias. | Registry construction fails with source-located ambiguity findings. |
| EC-003 | A link resolves to a file whose declared identity differs from its formal-ID label. | A blocking wrong-target finding is emitted even though the file exists. |
| EC-004 | The first reference appears inside code and a later prose reference is bare. | Code is ignored; the later prose reference is treated as the first and must link. |
| EC-005 | A document contains only self-references to its declared ID. | No first-reference finding is emitted for its own identity. |
| EC-006 | A historical document contains bare first references and a broken explicit local link. | First-reference policy is exempt; the broken explicit link is still reported; reconciliation proposes no historical edit. |
| EC-007 | A well-formed formal ID has neither a local canonical document nor an external mapping/link. | The unknown bare ID is a blocking finding; it is not assumed external. |
| EC-008 | An external mapping shadows a local canonical ID. | Configuration is rejected as ambiguous. |
| EC-009 | `related:` duplicates a target already expressed by `depends_on` or supersession. | An advisory redundancy finding identifies both fields; no repair is proposed and exit status remains `0` if no blocking findings exist. |
| EC-010 | A graph target is unresolved. | The unresolved occurrence remains a finding and no placeholder node or edge is emitted. |
| EC-011 | A source file changes after the apply invocation scans and plans it but before group preflight. | Content-hash group preflight fails before any planned target is written. A change between a separate preview invocation and apply is incorporated into the newly computed apply plan. |
| EC-012 | An output target traverses a symlink, escapes the root, is a directory or other non-regular object, or falls within either identity or policy scope. | The command rejects the target as invocation/configuration error `2` and leaves it unchanged. A valid regular target outside both scopes that cannot be published or lacks overwrite authorization remains operational error `1`. |
| EC-013 | No authored or index document remains after effective scope resolution. | The explicit command or enabled aggregate integration fails as configuration error `2` rather than reporting vacuous success. |
| EC-014 | An enforced document references a valid canonical document outside `include` but at an adapter-recognized identity location. | Identity resolution succeeds; only the referencing document receives policy enforcement. |
| EC-015 | A formal-ID-shaped token appears only in a link destination, autolink target, raw URL, or path-like token before a later visible prose occurrence. | The nonvisible/path occurrence is ignored; the later visible occurrence is the first prose reference and must link. |
| EC-016 | A `prior_specs` ID resolves through `external_ids`. | The relationship is valid and produces no local graph node or `prior-spec` edge. An unresolved or ambiguous value is blocking at the field. |
| EC-017 | A canonical document within a configured index's namespaces and roots has no index entry. | A blocking missing-index-entry finding is emitted. An ordinary `References` section has no completeness obligation. |
| EC-018 | A superseded or historical canonical document otherwise meets an orphan or strong-evidence advisory predicate. | No orphan or missing-relationship advisory is emitted for that document. |

### 10.4 State Transitions

Reconciliation plans have a small observable lifecycle:

| State | Meaning | Entry Condition | Exit Condition |
| --- | --- | --- | --- |
| Previewed | A read-only invocation emitted an informative plan describing its source bytes. | Deterministic findings produced one or more safe edits. | Terminal; a later apply invocation always computes a new plan. |
| Applicable | The apply invocation's newly computed plan passed every path and digest precondition. | Apply was explicitly requested and group preflight succeeded. | Per-file publication begins. |
| Stale | At least one digest or path changed between planning and group preflight within the apply invocation. | Group preflight detects drift. | The invocation fails; a later invocation rescans and computes a new plan. |
| Applied | Every planned file was atomically replaced. | Publication completes successfully. | Terminal; a new check verifies outcome. |
| Failed | Publication encountered an error after preflight. | A per-file replacement fails. | Operator inspects the report and reruns check; no global rollback is implied. |

---

## 11. UI Pages / API Endpoints

The version-one user and machine interface is CLI-only; there is no UI, HTTP API, or MCP surface.

| Command | Purpose | State Effect | Principal Output |
| --- | --- | --- | --- |
| `project-standards references check` | Validate canonical identity and reference policy. | Read-only. | Human findings or versioned JSON. |
| `project-standards references graph` | Render the current validated document relationship graph. | Read-only except an explicit guarded output file outside both reference scopes. | JSON by default; DOT on request. |
| `project-standards references reconcile` | Preview mechanically certain link repairs. | Read-only by default. | Human plan or versioned JSON. |
| `project-standards references reconcile --apply` | Apply the current valid plan. | Guarded authored-file updates. | Applied/skipped/failed change report. |

The optional configuration surface is conceptually:

```toml
[tools.references]
enabled = true
include = ["docs/**/*.md"]
exclude = ["docs/reviews/**"]
historical = ["docs/handoff/sessions/**", "docs/specs/archive/**"]
namespaces = ["spec", "adr"]

[[tools.references.indexes]]
path = "docs/specs/README.md"
namespaces = ["spec"]
roots = ["docs/specs"]

[tools.references.external_ids]
"SPEC-AB12" = "https://example.org/example-repository/blob/v1/docs/spec.md"
```

The authoritative configuration schema shall define exact index coverage and defaults. The example establishes the approved namespace separation and data categories; it does not authorize undocumented keys.

---

## 12. Error Handling and Recovery

### 12.1 Expected Failures

| ID | Failure Mode | User/System Behavior | Logging / Observability | Recovery |
| --- | --- | --- | --- | --- |
| ERR-001 | Invalid configuration, empty effective corpus, or unsafe corpus-scope path. | Exit `2`; no scan, graph, plan, or write occurs. | Bounded path and field diagnostic. | Correct configuration or corpus scope and rerun. |
| ERR-002 | Unreadable or malformed governed document. | Exit `1`; `check` reports the source failure and identity-dependent graph/reconciliation fails closed. | Source-located finding without unrelated content. | Repair the document or adjust legitimate scope. |
| ERR-003 | Duplicate or ambiguous canonical identity. | Exit `1`; report every involved declaration; refuse graph/reconciliation. | Stable identity-conflict codes and loci. | Resolve the declarations or aliases and rerun. |
| ERR-004 | Blocking reference-policy drift. | Exit `1`; continue reporting independent safe findings. | Human/JSON finding report. | Edit manually or preview deterministic reconciliation. |
| ERR-005 | A graph output target is invalid or a valid guarded target cannot be published. | Exit `2` for an escaping path, symlink, directory or other non-regular object, or target inside either identity or policy scope. Exit `1` when a valid regular target outside both scopes cannot be published or lacks required overwrite authorization. Refuse publication and leave the target unchanged. | Output-path diagnostic. | Choose a valid non-authored target, authorize overwrite where supported, and rerun. |
| ERR-006 | An apply invocation's reconciliation precondition becomes stale or unsafe after planning. | Exit `1` before any write. | Current plan target and precondition class, not source contents. | Rerun preview if desired, then invoke apply to compute and preflight a fresh current plan. |
| ERR-007 | Per-file replacement fails after group preflight. | Exit `1`; stop publication, report applied and unapplied targets, and make no global rollback claim. | Typed apply report. | Run `check`, inspect exact state, then generate a new plan. |
| ERR-008 | Unexpected internal failure. | Exit `1`; emit a controlled diagnostic and publish no graph, plan, or partial output file. | Exception class and bounded operational context. | Treat as a tool defect; preserve source bytes and report reproduction. |

### 12.2 Retry and Idempotency

`check`, `graph`, and reconciliation preview are read-only and idempotent for identical input bytes. They perform no automatic retry because all dependencies are local. An operator may rerun after correcting configuration, source, or an output target.

Apply is safe to retry because every invocation rescans and computes a fresh plan. No previously emitted plan is replayed. The invocation verifies the newly computed source digests immediately before its first write, so a concurrent change after planning fails precondition validation instead of being overwritten.

### 12.3 Rollback / Recovery

Read-only commands require no rollback. Reconciliation checks every target and digest before its first write and atomically replaces each individual file. If a later replacement fails, earlier files may already contain their planned edits. The apply report identifies applied and unapplied targets. Recovery is forward: run `check` against current bytes, review the remaining drift, and create a new plan. Version one does not promise multi-file rollback.

---

## 13. Security and Privacy

The security model is local and filesystem-bound: read operations must remain within the selected repository scope, while reconciliation adds explicit authorization, freshness, and guarded-write requirements. The absence of a network service removes protocol authentication concerns but does not remove path-containment, concurrent-edit, or diagnostic-disclosure risks.

### 13.1 Authentication

Not applicable: the subsystem is a local CLI operating with the invoking user's existing filesystem identity and exposes no network service.

### 13.2 Authorization

| Actor / Role | Allowed Actions | Denied Actions |
| --- | --- | --- |
| Local operator | Run read commands; request preview; explicitly apply a valid plan to repository-owned files. | Bypass containment, symlink, overwrite, or digest preconditions. |
| Aggregate validator / CI | Run configured read-only checking and consume findings. | Apply reconciliation or mutate authored documents. |

### 13.3 Secrets

Not applicable: the subsystem requires no credentials and performs no network access. Repository configuration must not contain credential values.

### 13.4 Sensitive Data

| Data | Classification | Storage | Transmission | Retention |
| --- | --- | --- | --- | --- |
| Parsed authored Markdown | Same classification as source repository | Memory only unless the operator explicitly writes derived output | Local process only | Process lifetime |
| Finding, graph, and plan output | Potentially internal repository metadata | Stdout or explicit guarded output file | Local process only | Operator controlled |

### 13.5 Threats and Mitigations

| Threat | Impact | Mitigation |
| --- | --- | --- |
| Malicious or malformed Markdown causes path escape or unintended reads. | Data outside repository scope could be exposed. | Resolve configured and referenced paths against the selected root; reject traversal and escaping symlinks. |
| Pathological repository-owned Markdown exhausts CPU or memory or stalls CI. | A local or hosted validation run may fail to complete. | Accept the bounded v1 risk, exercise malformed-input cases, record a reproducible cold-run benchmark, and add resource limits only when operational evidence supports them. |
| Stale reconciliation overwrites concurrent work. | User-authored changes could be lost. | Preview source digests, group preflight, and atomic per-file replacement. |
| Diagnostics echo unrelated source content. | Internal or sensitive prose could leak to logs. | Stable codes, bounded messages, and only the minimum identifier/path context. |
| A partial or identity-invalid graph is consumed as truth. | Downstream decisions use misleading relationships. | Fail closed on parse or canonical-registry errors and version every graph envelope. |
| Optional tooling becomes implicit policy through installation. | Consumers receive unexpected failures. | Separate `[tools.references]` opt-in and no standards-selection coupling. |

### 13.6 Hardening Checklist

- [x] Cookie/session settings — not applicable; no session or browser surface.
- [x] CSRF/CORS policy — not applicable; no HTTP surface.
- [x] Webhook/API signature validation — not applicable; no external API input.
- [ ] Sensitive-data redaction in diagnostics — required by NFR-007 and distribution tests.
- [x] CI/CD secret handling — no secrets required; tests run network-denied.
- [x] Network exposure — no listening socket or network request in v1.
- [x] Identity-header trust rules — not applicable; no proxy or header input.
- [x] Least-privilege filesystem access — commands use invoking-user permissions plus repository containment and guarded writes.

---

> **Sections §14 (Capacity and Scale Assumptions), §15 (Risks), and §16 (Compliance, Licensing, and Data Rights) are Full-tier** and are intentionally omitted at the Standard profile.

## 17. Testing and Acceptance

### 17.1 Definition of Done

- [ ] Every Must requirement has passing executable evidence in §17.3.
- [ ] Source-tree, candidate-wheel, and installed-wheel command probes pass without a selected standards package.
- [ ] Scanner, namespace, policy, graph, reconciliation, security, and CLI failure fixtures pass.
- [ ] Repeated unstamped reports, graphs, and plans are byte-identical for identical inputs.
- [ ] `check`, reconciliation preview, and stdout-only `graph` leave the repository byte-identical and make no network calls; explicit graph publication changes only its guarded target outside both reference scopes.
- [ ] Reconciliation preview and apply prove containment, preconditions, ambiguity refusal, and atomic per-file publication.
- [ ] Existing package validators, standards graph, control-plane gates, and compatibility matrix remain green.
- [ ] The real repository corpus passes the approved policy or records explicit accepted advisory baselines.
- [ ] A reproducible cold-run benchmark records the environment, corpus shape, method, and result without hardcoded corpus counts.
- [ ] User and configuration documentation accurately distinguishes optional reference tooling from standards adoption and MCP.
- [ ] Security-sensitive diagnostics and path handling are reviewed; §13.6 is complete.
- [ ] Deviations Log is empty or every entry has owner disposition.
- [ ] No blocking open questions remain.

### 17.2 Test Strategy

| Layer | Scope | Required Coverage | Required? |
| --- | --- | --- | --- |
| Scanner unit | Frontmatter, Markdown structure, ranges, links, mentions, and exemptions. | Inline/fenced code, anchors, malformed input, duplicate keys, Unicode, CRLF, physical coordinates. | Yes |
| Namespace unit | Project Specification and ADR adapters. | Canonical declarations, aliases, malformed IDs, duplicate IDs, alias collisions, local/external separation. | Yes |
| Policy unit | First-reference, navigation, target, relationship, and severity rules. | Every FR-005–FR-012 success and failure class. | Yes |
| Graph contract | Node/edge model and JSON/DOT renderers. | All edge types, ordering, deduplication, unresolved exclusion, schema compatibility, byte determinism. | Yes |
| Reconciliation unit | Finding-to-edit planning and guarded application. | Safe allowlist, ambiguity refusal, nonoverlapping spans, stale digests, symlinks, traversal, interruption. | Yes |
| CLI integration | Commands, configuration, exits, human/JSON parity, and aggregate opt-in. | Exit `0`/`1`/`2`, absent config, explicit scope, output guards, disabled aggregate gate. | Yes |
| Distribution | Source, candidate wheel, and installed wheel. | Package contents, `--help`, normalized results, no selected-package dependency. | Yes |
| Real corpus | Current project-standards authored Markdown. | Unique canonical identities, configured index coverage, link policy, advisory inventory, no hardcoded counts. | Yes |
| Performance | Cold full-corpus check. | Reproducible environment, corpus shape, method, and recorded result without hardcoded corpus counts. | Yes before release |
| Security | Filesystem and output boundaries. | Network denial, symlink escape, traversal, stale writes, bounded diagnostics, no partial output. | Yes |

### 17.3 Requirement-to-Test Traceability

| Requirement IDs | Test / Verification Method | Status |
| --- | --- | --- |
| FR-001, NFR-004, IR-001 | Source/candidate/installed-wheel command-availability and parity probes. | Planned |
| FR-002, IR-005, IR-006 | Closed configuration-schema and aggregate enabled/disabled integration fixtures. | Planned |
| FR-003, NFR-002 | Corpus-scope, containment, network-denial, and repository-hash tests. | Planned |
| FR-004, FR-009, NFR-006 | Namespace-adapter and canonical-registry fixtures. | Planned |
| FR-005–FR-008 | Markdown occurrence, exemption, navigation, and canonical-target policy fixtures. | Planned |
| FR-010–FR-012 | Schema-specific relationship and severity fixtures. | Planned |
| FR-013, NFR-003, NFR-007, IR-002 | Check command, report envelope, coordinate, and human/JSON parity tests. | Planned |
| FR-014, NFR-001, IR-003, DR-004 | Graph schema, edge, determinism, DOT, and guarded-output tests. | Planned |
| FR-015–FR-019, IR-004, DR-005 | Reconciliation preview/apply, allowlist, precondition, path, atomicity, and recovery tests. | Planned |
| FR-020 | Existing validator, package graph, and compatibility suites. | Planned |
| NFR-005 | Reproducible cold-run benchmark with recorded environment, corpus shape, method, and result. | Planned |
| DR-001–DR-003, DR-006 | Typed model validation, closed serialization, uniqueness, and no-persistent-state tests. | Planned |

---

## 18. Deployment and Operations

### 18.1 Runtime Environment

| Item | Value |
| --- | --- |
| Runtime | The Python versions supported by the released `project-standards` wheel. |
| Platform | Local repository checkout on supported operating systems. |
| Datastore | None. |
| External services | None. |
| Scheduling | None. |
| Hosting | Main `project-standards` wheel; invoked by a local operator or CI. |

There is no long-running service. Command exit status plus the selected human or JSON report is the health signal.

### 18.2 Configuration

| Setting | Required? | Default | Description |
| --- | --- | --- | --- |
| `tools.references.enabled` | No | `false` | Include reference checking in aggregate validation. |
| `tools.references.include` | No | `[]` | Authored Markdown globs selected for policy enforcement; together with configured indexes, they must resolve at least one effective document when the tool runs. They do not limit adapter-owned identity discovery. |
| `tools.references.exclude` | No | `[]` | Paths excluded from identity discovery and policy enforcement, including generated copies and fixtures. |
| `tools.references.historical` | No | `[]` | Paths checked for explicit link resolution but exempt from first-reference and reconciliation rules. |
| `tools.references.namespaces` | No | `["spec", "adr"]` | Enabled formal identifier adapters; v1 rejects other values. |
| `tools.references.indexes` | No | `[]` | Navigation surfaces and the namespaces/path roots whose entries they cover. |
| `tools.references.external_ids` | No | `{}` | Formal IDs intentionally resolved to stable external URLs. |

Equivalent explicit CLI scope arguments permit one-off use without durable configuration; they never enable aggregate validation.

Version one has no finding waiver or suppression mechanism. A repository may adopt the tool in phases by selecting an honest policy-enforcement subset with `include`, `historical`, and `indexes`, but every selected path receives the complete applicable policy and enabled adapters still discover nonexcluded canonical documents at their recognized locations. `exclude` removes generated, fixture, or intentionally out-of-system paths from both identity and enforcement rather than hiding policy drift. This meta-repository records its full-corpus blocking baseline during MS-2, remediates objective blocking drift before MS-5, and enables aggregate validation only when its declared scope has no blocking findings; scope shall not be narrowed merely to hide known drift.

### 18.3 Deployment Flow

1. Complete the milestone and test gates in §17 and qualify the candidate wheel.
2. Document the optional commands, configuration, finding semantics, graph formats, and reconciliation safety boundary.
3. Classify the public feature and configuration-contract change under `meta/versioning.md`.
4. Build and byte-verify the release wheel through the repository release process.
5. Publish only with separate owner authorization.
6. Verify the installed wheel exposes the command without a selected standard or MCP configuration.
7. Roll back by installing the prior release; authored repositories require no migration because the feature owns no persistent state and is disabled by default.

> **§18.4 (Rollout Controls) is Full-tier** and is intentionally omitted at the Standard profile.

### 18.5 Observability

The subsystem has no runtime service, metrics pipeline, or alerts. Its observable contract is the stable command exit status and versioned report envelope. Human diagnostics and JSON reports identify the operation, selected repository, schema version, findings or changes, and aggregate counts without echoing unrelated source content.

### 18.6 Backup and Disaster Recovery

Not applicable: the subsystem owns no durable data; authored Markdown remains protected by the repository's existing Git workflow.

### 18.7 Documentation Deliverables

- [ ] Add user-facing command and optional-configuration documentation.
- [ ] Document formal namespace, first-reference, navigation, historical, external-ID, and relationship policies.
- [ ] Document finding severities, exit codes, graph schemas, output guards, and reconciliation guarantees.
- [ ] Explain that standards adoption and MCP do not enable or own the feature.
- [ ] Update repository specification navigation and applicable CLI reference surfaces.
- [ ] Record the cold-run benchmark environment, corpus shape, method, and result.

---

## 19. Implementation Plan

### MS-0 — Contract and Corpus Fixtures

Freeze versioned configuration, finding, graph, and reconciliation-plan schemas; define spec and ADR namespace fixtures; and capture representative repository corpus cases. Exit when schemas validate, approved rules have RED tests, and no implementation behavior is inferred from mutable corpus counts.

### MS-1 — Discovery, Scanning, and Canonical Identity

Implement contained corpus discovery, shared Markdown scanning, namespace adapters, and canonical-registry validation. Exit when Project Specification and ADR identities, aliases, external mappings, structural exclusions, duplicates, and path failures pass their unit and integration tests.

### MS-2 — Policy Check, Baseline, and Optional Aggregate Gate

Implement first-reference, navigation, target, relationship, severity, report, and configuration behavior plus `references check`. Exit when explicit and aggregate enabled/disabled workflows pass, read-only behavior is proven, and the current repository produces a documented full-corpus baseline of blocking and advisory findings.

### MS-3 — Derived Graph

Implement versioned graph records plus deterministic JSON and DOT rendering. Exit when every approved edge type, identity failure, unresolved exclusion, output guard, and repeated-run determinism check passes.

### MS-4 — Guarded Reconciliation

Implement preview planning for the safe allowlist and explicit guarded application. Exit when ambiguous/editorial cases produce no edits, complete-plan preflight prevents stale writes, per-file atomicity is proven, and recovery reporting matches §12.3.

### MS-5 — Distribution and Release Readiness

Complete source/candidate/installed-wheel parity, full repository gates, objective full-corpus blocking-drift remediation, real-corpus validation, documentation, security review, and cold-run measurement. Enable this repository's aggregate gate only after its declared scope has no blocking findings. Exit when the feature is classified, the candidate is proven, the benchmark is recorded, and publication remains the only separately authorized step.

### Milestone Summary

| Milestone | Deliverable | Exit Criteria |
| --- | --- | --- |
| MS-0 | Frozen contracts and RED corpus | Versioned schemas plus failing acceptance fixtures cover every approved rule. |
| MS-1 | Identity foundation | Contained scanner and unique spec/ADR registry pass. |
| MS-2 | Read-only policy gate and corpus baseline | Optional check and aggregate integration produce correct findings without writes, and the full-corpus baseline is recorded. |
| MS-3 | Document graph | JSON/DOT graph is valid, complete for resolved edges, and deterministic. |
| MS-4 | Reconciliation | Preview/apply safety and bounded repair policy pass. |
| MS-5 | Qualified optional tooling | Blocking baseline drift is remediated; distribution, docs, security, performance, and repository gates pass. |

---

> **§20 (Success Evaluation) is Full-tier** and is intentionally omitted at the Standard profile.

## 21. Open Questions and Decisions

No blocking product or architecture decisions remain. One non-blocking compatibility question is recorded.

| ID | Question | Blocking? | Current Assumption | Owner | Decide By |
| --- | --- | --- | --- | --- | --- |
| OQ-001 | Does introducing the sibling top-level `[tools]` table require the consumer-config header to advance to `schema_version = "1.2"`, or is `[tools.references]` version-neutral for `1.0` and `1.1` headers? | No | Follow the repository's own precedent for `role`, which was introduced at header `schema_version = "1.1"` and is rejected under `1.0` while leaving unmodified `1.0` configs valid and digest-stable: gate writing `[tools.references]` behind a new header version, keep every prior header valid, and exclude the absent namespace from the digest basis. The alternative — treating a sibling table as outside the header's version contract — is cheaper but leaves no declared signal that a consumer config uses a key an older tool would reject. | Owner | Before MS-0 freezes the configuration contract. |

---

## Deviations Log

No implementation deviations have been recorded.

---

## References

### Standards

Repinned at revision 0.2 to the versions this repository currently resolves in `.standards/lock.toml`. The identity grammars this subsystem composes are unchanged from the 0.1 pins: the Project Specification `spec_id` pattern is byte-identical between 1.5 and 1.9, and the ADR canonical `adr-NNNN-repo-name-short-title` form is unchanged through 1.6.

- [Project Specification Standard 1.9](../../standards/project-spec/versions/1.9/README.md)
- [ADR Standard 1.6](../../standards/adr/versions/1.6/README.md)
- [Markdown Frontmatter Standard 1.13](../../standards/markdown-frontmatter/versions/1.13/README.md)
- [Markdown Frontmatter relationship policy](../../standards/markdown-frontmatter/versions/1.13/field-values.md#relationships-and-sources)
- [Repository versioning policy](../../meta/versioning.md)

### Project References

- [Consumer Standards Control Plane — SPEC-CP01](2026-07-10-consumer-standards-control-plane-spec.md)
- [MCP Server Implementation — SPEC-MS01](2026-07-07-project-standards-mcp-server-implementation-spec.md)
- [Current specification index](README.md)
- [Current frontmatter reference validator](../../src/project_standards/validate_references.py)
- [Current Agent Handoff conventions](../handoff/conventions.md)

---

## Appendix A: ID Conventions

Stable IDs allow requirements to be referenced from commits, tests, issues, ADRs, and review comments. Section numbers match the canonical Full profile, so IDs retain their meaning across profile upgrades.

| Prefix | Meaning                     | Defined In     |
| ------ | --------------------------- | -------------- |
| `G-`   | Goal                        | §4             |
| `NG-`  | Non-goal (never)            | §2.2           |
| `WH-`  | Won't have in v1 (deferred) | §2.3           |
| `A-`   | Assumption                  | §3.3           |
| `C-`   | Constraint                  | §3.4           |
| `FR-`  | Functional requirement      | §7.1           |
| `NFR-` | Non-functional requirement  | §7.2           |
| `IR-`  | Interface requirement       | §7.3           |
| `DR-`  | Data requirement            | §7.4           |
| `D-`   | Design decision             | §8.3           |
| `AW-`  | Alternate workflow          | §10.2          |
| `EC-`  | Edge case                   | §10.3          |
| `ERR-` | Error-handling requirement  | §12.1          |
| `MS-`  | Milestone                   | §19            |
| `OQ-`  | Open question               | §21            |
| `DEV-` | Deviation                   | Deviations Log |

The `R-` prefix is Full-tier and is not used in this Standard profile. Priority values never change IDs.

---

## Appendix B: Agent Implementation Contract

Binding when this specification is implemented by a coding agent.

### B.1 Implementation Rules

The implementer shall:

- Read this entire specification before making changes; in later sessions, reread at minimum §7, §21, and the Deviations Log.
- Preserve all non-goals, deferred items, constraints, and design constraints.
- Treat Must requirements and blocking open questions as hard gates.
- Use RED-GREEN-REFACTOR for each behavioral increment and keep §17.3 current with executable evidence.
- Preserve existing package-validator and standards-graph behavior while adding repository-level composition.
- Keep `check` and stdout-only `graph` byte-read-only, constrain explicit graph publication to a guarded target outside both identity and policy scopes, and make reconciliation preview the default.
- Record an underspecified consequential behavior as an `OQ-` row rather than guessing.
- Record every divergence as a `DEV-` row rather than silently adapting the contract.
- Stop at authorization boundaries for release, MCP exposure, new namespaces, caching, or relocation.

### B.2 Prohibited Behaviors

The implementer shall not:

- Invent requirements absent from this specification.
- Couple command availability to any selected standards package.
- Make a standards package own or implicitly enable the subsystem.
- Implement MCP exposure, additional namespace adapters, persistent caching, or `project-toolbox` relocation as incidental work.
- Create a second Markdown parser, identifier grammar, or document-graph authority.
- Infer or mutate `related:` or other editorial relationships.
- Emit partial or identity-invalid graphs as successful output.
- Weaken containment, symlink, overwrite, or precondition checks.
- Claim multi-file transactionality not provided by the executor.
- Publish a release without explicit owner authorization.

### B.3 Required Completion Report (verification gate)

At completion, provide:

- Summary of changes and exact files changed.
- Every implemented requirement mapped to its passing test or command through completed §17.3 entries.
- Source-tree, candidate-wheel, and installed-wheel evidence.
- Tests added or changed, including real-corpus and performance evidence.
- Configuration, finding, graph, and reconciliation schema versions.
- Security and read-only verification results.
- Deviations and owner dispositions.
- Known limitations, deferred items, and remaining open questions.
- Documentation deliverables completed.

### B.4 Session Handoff

For multi-session implementation, record the current milestone, in-progress requirement IDs, and unresolved `OQ-`/`DEV-` items in the repository's Agent Handoff documents. The specification records the contract; handoff records live state.

---

> **Appendix C (Optional Modules) is Full-tier** and is intentionally omitted at the Standard profile.

## Appendix D: Tailoring

The Standard profile is the smallest appropriate profile because this project adds a local Python CLI subsystem with versioned machine contracts and guarded file mutation, but no runtime service, datastore, scheduler, external integration, or multi-stakeholder operational deployment.

| Profile | Template File | Use For |
| --- | --- | --- |
| Light | `spec-light-template.md` | Scripts and single-session tasks |
| Standard | `spec-standard-template.md` | Typical features and services |
| Full | `spec-full-template.md` | Multi-service systems, durable data, external integrations, or multiple stakeholders |

Upgrade to Full only if approved scope adds a runtime service, durable datastore, consequential external integration, multi-stakeholder rollout, or another Full-tier concern. A profile upgrade is additive and preserves existing section and ID references.
