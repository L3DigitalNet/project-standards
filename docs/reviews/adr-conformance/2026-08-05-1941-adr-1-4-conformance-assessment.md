---
schema_version: '1.1'
id: 'reference-k7p2xf-adr-1-4-conformance-assessment'
title: 'Active ADR Conformance Assessment against ADR Standard 1.4'
description: 'Read-only assessment of all 23 active project-standards ADRs against ADR Standard package 1.4, plus a second pass on inter-ADR conflicts, overlapping ownership, and consistency.'
doc_type: 'reference'
status: 'active'
created: '2026-08-05'
updated: '2026-08-05'
reviewed: '2026-08-05'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'adr'
  - 'review'
  - 'validation'
  - 'standards-platform'
aliases:
  - 'ADR 1.4 conformance'
  - 'ADR boundary audit'
related:
  - 'docs/adr/README.md'
  - 'standards/adr/versions/1.4/README.md'
  - 'src/project_standards/payloads/adr/1.4/README.md'
  - 'src/project_standards/payloads/adr/1.4/templates/adr.md'
  - '.standards/config.toml'
  - '.standards/lock.toml'
  - 'meta/versioning.md'
source:
  - 'src/project_standards/control_plane/providers.py'
  - 'src/project_standards/standards_graph/validators.py'
  - 'src/project_standards/package_contract/payload.py'
  - 'meta/versioning.md'
  - 'src/project_standards/payloads/adr/1.4/README.md'
  - 'src/project_standards/payloads/adr/1.4/agent-summary.md'
  - 'src/project_standards/payloads/adr/1.4/payload.toml'
  - 'src/project_standards/payloads/adr/1.4/providers/adr.py'
  - 'src/project_standards/catalogs/5.toml'
  - '.standards/lock.toml'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# Active ADR Conformance Assessment against ADR Standard 1.4

Read-only assessment. No ADR, configuration, or payload file was modified.

This report covers two passes. **Pass 1** (§1–§8) grades each active ADR individually against the 1.4 decision-boundary rubric. **Pass 2** (§9) treats the corpus as a graph and examines inter-ADR conflicts, overlapping ownership, and internal consistency. The consolidated backlog in §10 covers both.

## 1. Scope and method

**Corpus.** All 27 records under `docs/adr/`. Four carry `status: superseded` (0003, 0008, 0017, 0020) and are excluded from grading; the remaining **23 active ADRs** are assessed individually.

**Authority.** ADR package `1.4`, which is the Catalog 5 `default` (`src/project_standards/catalogs/5.toml:22-26`) and the version this repository actually resolves (`.standards/config.toml` selects `version = "latest"`; `.standards/lock.toml:8-13` records `resolved = "1.4"`). The graded text is `src/project_standards/payloads/adr/1.4/README.md`, with `agent-summary.md` as a cross-check.

**What 1.4 added.** The 1.3 → 1.4 delta is almost entirely one new governance concept. Everything else is copy-editing and the removal of stale cross-package links.

| Added in 1.4 | Effect |
| --- | --- |
| `## Bound the decision` section | Five boundary elements must be defined before options are evaluated |
| `### Decision-boundary review` subsection | Six acceptance checks applied before an ADR is accepted |
| Split rule in `When to write an ADR` | Independently reversible concerns must not be combined |
| Breadth rule | Title, problem question, options, and outcome must sit at the same breadth |
| Outcome-restatement rule | Four facts must be derivable from Decision Outcome alone |
| Optional-section rule | Consequences, Confirmation, examples, and More Information must not create policy |
| Universal-term rule | "all", "every", "the repository", "default" require an explicit population and applicability condition |
| Supersession scoping rule | A new ADR supersedes an old one only for a decision the old one actually governed |
| Template rewrite | `templates/adr.md` now prompts for boundary, exclusions, and reserved authority |

Critically, 1.4 states that these are **authoring requirements**, not schema requirements: "this release does not infer semantic scope from prose." The `require_sections` provider check is unchanged from 1.3 and still validates only the three MADR level-2 headings.

**Rubric.** Ten checks derived directly from the 1.4 text:

| ID | Check | 1.4 source |
| --- | --- | --- |
| B1 | Governed concern, population, applicability condition, exclusions, and reserved authority are defined | `Bound the decision`, list |
| B2 | Decision Outcome alone answers: what is selected, which population, when, what is outside | `Bound the decision`, numbered list |
| B3 | At least one realistic out-of-scope case is stated | `Decision-boundary review`, item 1 |
| B4 | Title, problem question, options, and outcome share one breadth | `Bound the decision`, paragraph 4 |
| B5 | Every considered option answers the same bounded question | `Decision-boundary review`, item 3 |
| B6 | No optional section introduces a normative requirement | `Bound the decision`, paragraph 6 |
| B7 | Universal terms carry an explicit population and applicability condition | `Bound the decision`, final paragraph |
| B8 | Out-of-scope cases require no exception or waiver | `Bound the decision`, paragraph 3 |
| B9 | Combined concerns genuinely require joint reconsideration | `Decision-boundary review`, item 6 |
| B10 | Supersession only replaces decisions the predecessor governed | `Supersession workflow` |

Packaging and convention checks (`id`/filename, required sections, index, frontmatter, link integrity) were run mechanically. Reproduction commands are in §8.

## 2. Verdict

The corpus is **structurally clean and semantically non-conformant**. Every mechanical gate 1.4 can enforce passes; the boundary discipline 1.4 actually introduced is absent from roughly half the corpus and inconsistently applied in the rest.

| Grade | Count | ADRs |
| --- | --- | --- |
| Exemplary — meets the full rubric | 2 | 0027, 0022 |
| Substantially conformant — boundary stated, minor gaps | 4 | 0015, 0018, 0019, 0021 |
| Partially conformant — exclusions present, breadth or split defects | 6 | 0014, 0016, 0023, 0024, 0025, 0026 |
| Non-conformant — no decision boundary of any kind | 11 | 0001, 0002, 0004, 0005, 0006, 0007, 0009, 0010, 0011, 0012, 0013 |

The single sharpest signal: a scan for exclusion language across the active corpus returns **zero matches for every ADR numbered 0001–0013** and at least one match for every ADR numbered 0014 and above. The split is not gradual — it is exactly the boundary between the SPEC-MT01 authoring pass of 2026-07-07 and everything written afterwards.

Nothing here is a validation failure. `uv run project-standards validate` will continue to exit `0`, because the ADR provider checks section presence and nothing else. That is by design, and it is why this assessment exists.

The second pass (§9) reaches a complementary verdict: **no two active ADRs mandate incompatible outcomes, but five authorities are contested and five boundaries are unowned.** The recurring shape is a later ADR replacing an earlier one's mechanism or duplicating its guarantee while both records stay silent about the other. That is the same root cause the per-record grading found — an ADR that never bounded itself keeps apparent authority over ground a later decision took.

## 3. Mechanical findings

These are objective, reproducible, and fixable without judgement.

### F1 — The repository's own ADR scaffold is the 1.3 template, mislabelled as 1.4 (highest impact)

`docs/adr/adr.template.md` is byte-identical to the **1.3** template and contains none of the 1.4 boundary prompts.

```text
f6ac2567...3135d7  docs/adr/adr.template.md
f6ac2567...3135d7  src/project_standards/payloads/adr/1.3/templates/adr.md
e8129bc6...259742  src/project_standards/payloads/adr/1.4/templates/adr.md
```

The 1.4 payload declares this artifact with the **1.4** source digest (`payload.toml:105-109`, `digest = "sha256:e8129bc6…"`), but `policy = "create-only"`. The central lock records the installed file under `versions = { adr = "1.4" }` with `content_digest = "sha256:f6ac2567…"` — the 1.3 bytes (`.standards/lock.toml:1018-1028`).

Consequences:

- Reconcile will never update the file. Create-only means exactly that; this is not drift the platform can detect or repair.
- Drift-check cannot flag it. The lock recorded whatever existed at creation, so installed and recorded state agree.
- The lock asserts a provenance that is false: 1.4 ownership over 1.3 content.
- Every ADR authored in this repository from the scaffold starts from a template whose `Context and Problem Statement` prompt reads "Make the scope of the decision explicit" instead of the five-element boundary checklist, and whose `Decision Outcome` prompt has no `This decision governs … It does not govern …` skeleton.

This is the mechanical root cause of the boundary gap, and it will keep reproducing it. It is also a dogfooding defect in the create-only policy itself: a package whose _only_ managed output is a create-only template has no supported path to deliver a template revision to an existing consumer.

### F2 — ADR 0025 and 0026 filenames violate the id/filename convention

1.4 is explicit: the `id` embeds the repository name, the **filename omits it**.

| File | Current | Convention-conformant |
| --- | --- | --- |
| 0025 | `adr-0025-project-standards-mcp-service-and-sdk-boundary.md` | `adr-0025-mcp-service-and-sdk-boundary.md` |
| 0026 | `adr-0026-project-standards-mcp-local-read-only-transport.md` | `adr-0026-mcp-local-read-only-transport.md` |

Both filenames were derived from the `id` rather than from the short title. The `id` values themselves are correct. All 21 other ADR filenames conform. Renaming touches the index table, five inbound `related`/`source` frontmatter references, and several inline links — it is not free, and it is cosmetic, so it belongs low in the backlog.

### F3 — The ADR index points at the superseded 1.3 standard

`docs/adr/README.md:35` reads "See the [ADR 1.3 standard](../../standards/adr/versions/1.3/README.md)", and `related` line 20 pins `standards/adr/versions/1.3/README.md`. The repository resolves 1.4. The index carries `reviewed: '2026-08-01'`, three days after 1.4 was published (`Last updated: 2026-08-03` in the 1.4 README) — so the review predates the package, but the pointer is now wrong. An author following the index reads the standard that lacks the boundary section entirely.

The same file's `related` list also pins `standards/markdown-frontmatter/versions/1.2/field-values.md` and `standards/standard-bundle-authoring/versions/2.0/README.md` while current defaults are 1.9 and 2.6. Those are historical-evidence pins and defensible; the ADR-standard pointer in body prose is not, because it is presented as the format to follow.

### F4 — ADR 0014 governs a path population that no longer exists

ADR 0014's `### Governed scope` and `### Document type mapping` sections name `docs/adr-library/README.md` and `docs/adr-library/**/*.md` entries. That directory does not exist in the working tree. `.standards/config.toml` still carries the matching `docs/adr-library/**/*.md` include — the known dead-include item on the owner queue.

Under 1.4 this is a boundary-accuracy defect, not just stale config: an active ADR declares a governed population that cannot be instantiated, so the applicability condition is unsatisfiable. The corresponding content now lives at `standards/adr/library/`, which ADR 0027 references correctly and ADR 0014 does not.

### F5 — Mechanical checks that pass

Recorded so future reviews need not repeat them.

- **Required sections:** all 27 records contain exactly one each of `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`. With `require_sections = true` in `.standards/config.toml`, the provider check is green.
- **Relative links:** 167 relative link targets across `docs/adr/`, zero broken.
- **Frontmatter paths:** every repo-relative path in `related` and `source` across all 27 records resolves.
- **Status vocabulary:** all values are drawn from the canonical enum, and every `superseded` record sets `superseded_by`. The MADR-native word is stated in body prose as 1.4 permits.
- **`id` grammar:** all 27 ids match `adr-NNNN-project-standards-<short-title>`.
- **Supersession scope (B10):** 0023 supersedes 0003/0008/0017 and 0024 supersedes 0020. In each case the successor replaces a decision the predecessor actually governed — manifest split, config namespace ownership, adoption methodology, and package versioning respectively. No out-of-scope supersession found.

## 4. Boundary findings by cohort

### Cohort A — ADRs 0001–0013 (11 active): no decision boundary

These record decisions D-001 to D-013 of SPEC-MT01, all accepted 2026-07-07 and last touched 2026-07-09. They share one authoring shape and one systemic defect: **no member states a governed population, an applicability condition, an exclusion, or reserved authority.** B1, B2, and B3 fail for all eleven.

The Decision Outcome sections are single paragraphs of the form _chosen option, because rationale, alternative rejected because reason_. They are good rationale records. They are not bounded decisions: a reader cannot determine from the outcome which systems are governed, when the rule applies, or what falls outside it.

Five members additionally violate **B6** — a normative requirement appears only inside `### Consequences`, where 1.4 says policy must not live:

| ADR | Requirement stated only in Consequences |
| --- | --- |
| 0001 | "draft or reference-only standards must now explicitly declare their non-adoptable status" |
| 0002 | "every standard bundle must now maintain an additional manifest file in sync with its documentation" |
| 0004 | "every standard must now explicitly declare its authority tuples" |
| 0006 | "standards without a provider for a given capability must explicitly opt out rather than silently no-op" |
| 0007 | "contributors must fix graph violations before merging rather than deferring them to a later cleanup pass" |

Each is a real, load-bearing rule that the platform enforces today. Under 1.4 each must be moved into the bounded Decision Outcome or removed. This is the highest-value remediation in the cohort, because these are the requirements most likely to be missed by a reader who reads outcomes and skips consequences.

**B7** fails across the cohort through unqualified universals — "every standard bundle", "every standard", "arbitrary combinations of standards", "every change" — none paired with an explicit population and applicability condition.

Two members carry additional issues:

- **ADR 0010** is one half of an unreconciled conflict with ADR 0026; see §5.
- **ADR 0012** decided a sequencing gate ("defer MCP server implementation until the meta-repo readiness gate passes"). The gate has since passed and `src/project_standards/mcp_server/` exists. The applicability condition is discharged, yet the record remains `status: active` and is cited by ADR 0025 as "sequencing precedent". Under 1.4 the boundary should have carried its own expiry; as written, an active ADR appears to prohibit work that has already shipped. This is a lifecycle-accuracy question for the owner, not a defect the standard names directly.

### Cohort B — ADRs 0014–0022 (7 active): boundary discipline emerging

Every member states at least one exclusion, and four use a formula that anticipates 1.4 almost exactly: _"This decision governs X as a class. It does not decide Y."_

- **0022 (hooks)** is the strongest pre-1.4 record in the corpus. It declares the class, names three exclusions in one sentence ("does not require every standard to ship a hook, define every harness registration format, or authorize hooks to execute without the consumer's normal harness trust and approval controls"), restates the operative boundary inside Decision Outcome, and its `### Confirmation` describes verification without adding policy. It satisfies B1–B9 as written.
- **0018 (lifecycle)** and **0019 (provenance)** both declare the class and reserve adjacent authority to other decisions. Both use exceptions correctly in the 1.4 sense — an exception applies to an in-population item that departs from the rule, not to an ungoverned case, so **B8 holds**.
- **0021 (skills)** states its class, its exclusions, and a genuine out-of-scope case ("Global or home-level skill installation may still exist as a separate workstation convenience"). One soft spot: it requires consumers to exclude installed skill paths from "managed Markdown frontmatter validation, formatting, linting, type checking, or other standards" — the open-ended tail extends the governed population to standards this ADR does not name.
- **0015** is short and well bounded: population is `standards/**` in this repository, and it explicitly disclaims changing the Markdown Frontmatter Standard or constraining consuming repositories.
- **0014** predates 1.4 but invented a `### Governed scope` heading, which is the right instinct. Its defect is factual, not structural — see F4.
- **0016** has the clearest **B4** breadth failure in the corpus. The problem question is about who owns and packages the frontmatter skill; the Decision Outcome then imposes a validation-scope requirement on every consuming repository ("must keep `.agents/**` excluded from managed-document frontmatter validation") and rules on the state of a **different repository** ("`agent-configs` no longer owns, tests, inventories, or deploys this skill"). Neither population is declared, and neither is the same breadth as the question evaluated. The later, broader 0021 covers the consumer-exclusion rule properly.

### Cohort C — ADRs 0023–0027 (5 active): strong exclusions, weak split discipline

This cohort states exclusions well — several state them better than 1.4 requires — but four of five bundle independently reversible concerns, failing **B5** and **B9**.

- **ADR 0023 (control plane).** The bounded question is "How should a consumer repository declare, reconcile, and audit its installed standards and their repository artifacts?" The four considered options all answer that question. The Decision Outcome then also fixes the semantic-ownership model, the adapter formatting contract, the provider execution rules, the central lock schema, and a 400-word whole-file consumer-ownership migration exception with its own static pointer-binding protocol. No considered option evaluates any of those. The migration exception in particular is independently reversible from the control-plane placement decision and would have to be reconsidered on its own — the 1.4 split test says it belongs in its own record. B3 is also weak: the ADR states what other authorities own but names no realistic out-of-scope case for itself.
- **ADR 0024 (version channels).** The problem question openly enumerates six concerns. More significantly, it governs **two different populations without distinguishing them**: the selector, candidate, and accepted-major rules govern consuming repositories, while the entire `### Tool release classification` section governs this repository's own release process ("a package-version advance requires exactly MINOR and a release without one requires exactly PATCH"). Neither population is declared, and no applicability condition separates them. A reader cannot tell from the outcome which rules apply to them.
- **ADR 0025 (MCP service and SDK boundary).** Opens by declaring that "two questions must be answered" — commendably explicit, and precisely the case 1.4 says to split. The considered-options list then mixes them: "Hand-roll a JSON-RPC implementation" answers the dependency question, "Keep provider execution in-process" answers the execution question, and they are not alternatives to each other. B5 fails structurally. Set against that, its exclusions are the best in the corpus: the approved effect set names exactly what is excluded and why, and "**No aggregate per-tool-call budget is frozen by this record**" is a model statement of non-governance — precisely what 1.4 asks for.
- **ADR 0026 (transport).** Freezes six commitments — transport, CLI form, URI grammar, root rules, capability semantics, tool registry. Same mixed-options defect. Its deferrals are exemplary: each is bound to a named owning question (`SPEC-RD01 OQ-004`, `OQ-007`), which is exactly 1.4's "reserved authority". It also states an explicit non-reconciliation ("The forms differ, and this record does not reconcile them"), which is textbook B3. Its three post-acceptance `Amendment (…)` paragraphs sit inside Decision Outcome — the correct location — but were added after acceptance and therefore after any boundary review; the 2026-07-30 F3 amendment mints a 32-code error taxonomy, which is a substantial policy addition made outside the acceptance path.
- **ADR 0027 (Go).** The reference exemplar. It declares the governed concern and population, states exclusions as a positive list ("does not authorize a Python-to-Go migration, production cutover, Python freeze, dependency removal, test retirement, or standards-package change"), reserves authority explicitly ("Language selection … requires case-specific requirements or later approved guidance"), sets its own amendment threshold ("Exact Go and tool versions are ordinary reviewed configuration … Changing the module boundary, canonical command owner, verification categories, coexistence policy, or language-neutral posture does"), and its `### Confirmation` determines applicability before verifying conformance — the exact two-step 1.4 specifies. It satisfies all ten checks. Written 2026-08-01, two days before 1.4 was published, which suggests 1.4 was drafted from this record's shape.

## 5. Cross-ADR finding: two active ADRs answer one question differently

ADR 0010 established manifest-declared resource URIs and the generated index. ADR 0026 froze the MCP v1 URI grammar. They disagree, and ADR 0026 says so:

| Producer | Form | Authority |
| --- | --- | --- |
| `standards/catalog.md`, via `catalog.py:172` | `standards://{standard_id}/{version}/{resource_id}` | ADR 0010 |
| `render_catalog`, `catalog.py:330` (exported, CLI-reachable) | `standards://{standard_id}/{resource_id}` | ADR 0010 lineage |
| MCP v1 | `standards://{standard_id}/{version}/resources/{resource_id}` | ADR 0026 |

ADR 0026 discloses the divergence, explains the failure mode, and declares reconciliation "out of scope for T1 … flagged for owner decision as one index-and-producer alignment item". That disclosure is good practice and is why this reads as an open item rather than a latent defect.

The 1.4 gap is on the other side: **ADR 0010 never states that it does not govern the MCP server's URI grammar.** Its authority is unbounded as written, so a reader consulting only ADR 0010 would conclude that the three-segment form is repository policy and that ADR 0026 departs from it without an exception. Under 1.4's rule that an item outside the boundary is out of scope rather than an exception, ADR 0010 needs an exclusion, or the two need one reconciling record.

## 6. Gaps on the standard's side

Two observations that are properly findings against ADR 1.4 itself, not against the corpus.

**Amendment has no vocabulary.** Five active ADRs carry `> **Amended by ADR NNNN.**` banners (0014, 0015, 0016, 0018, 0019), and ADR 0026 carries three inline `Amendment (date, finding)` paragraphs. This repository has clearly needed partial amendment — a later decision narrowing or restating part of an earlier one without replacing it. ADR 1.4 defines only supersession, which is all-or-nothing. The banner convention is a sound local invention that the standard neither sanctions nor forbids. Since 1.4 tightened the supersession rule ("a new ADR supersedes an old ADR only when it replaces a decision the old ADR actually governed"), the need for a partial-amendment concept is now _stronger_, not weaker: the tightened rule pushes more changes out of supersession and into amendment, where no guidance exists.

Filed as [issue #127](https://github.com/L3DigitalNet/project-standards/issues/127). The second pass strengthened the case considerably: C2, C3, and C5 are three substantive changes to active decisions made through neither amendment nor supersession, because no sanctioned form existed for what they actually were.

**Nothing mechanical enforces the new rules.** 1.4 is explicit that "this release does not infer semantic scope from prose", and the provider is unchanged from 1.3. That is a defensible design choice, but it means 1.4 has no enforcement surface at all — and the one artifact that _would_ have carried the guidance to authors, the template, cannot reach existing consumers because it is create-only (F1). As shipped, 1.4's boundary discipline reaches new consumers only, and reaches this repository not at all.

A modest, prose-free check is available: the four-part outcome test could be approximated by requiring that Decision Outcome contain a sentence matching a declared governs/does-not-govern pattern. That would be a 1.5 conversation, not a fix to this corpus.

## 7. Per-ADR results

`Y` = satisfied, `~` = partial, `N` = failed, `–` = not applicable.

| ADR | Title | B1 boundary | B2 outcome | B3 exclusion | B4 breadth | B5 options | B6 no policy in optional | B9 split | Grade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0001 | Standard Bundle Authoring Contract | N | N | N | Y | Y | **N** | Y | Non-conformant |
| 0002 | Manifest-First Standard Discovery | N | N | N | Y | Y | **N** | Y | Non-conformant |
| 0004 | Authority Map and Conflict-Free Composition | N | N | N | Y | Y | **N** | Y | Non-conformant |
| 0005 | Stable Generic Agent and Tooling Interface | ~ | N | N | Y | Y | ~ | Y | Non-conformant |
| 0006 | Standard Provider and Plugin Model | N | N | N | Y | Y | **N** | Y | Non-conformant |
| 0007 | Standard Graph Validation Gate | ~ | N | N | Y | Y | **N** | Y | Non-conformant |
| 0009 | Agent Summary and Canonical Standard Split | N | N | N | Y | Y | Y | Y | Non-conformant |
| 0010 | Standard Resource URIs and Index | N | N | N | Y | Y | Y | Y | Non-conformant (see §5) |
| 0011 | Dogfood Consumer Fixtures | N | N | N | Y | Y | Y | Y | Non-conformant |
| 0012 | MCP Readiness Before Server Implementation | ~ | ~ | N | Y | Y | Y | Y | Non-conformant + discharged |
| 0013 | Independent Packages and Relationship Taxonomy | N | N | N | Y | Y | Y | Y | Non-conformant |
| 0014 | Markdown Frontmatter Field Value Policy | ~ | Y | ~ | Y | Y | Y | Y | Partial (stale population) |
| 0015 | Exclude Standards from Local Frontmatter Scope | Y | Y | Y | Y | Y | Y | Y | Substantial |
| 0016 | Package Markdown Frontmatter Skill with Standard | ~ | ~ | ~ | **N** | Y | Y | Y | Partial |
| 0018 | Standard Package Lifecycle Methodology | Y | Y | Y | Y | Y | Y | Y | Substantial |
| 0019 | Packaged Artifact Parity and Provenance | Y | Y | Y | Y | Y | Y | Y | Substantial |
| 0021 | Standard-Packaged Skill Installation | Y | Y | Y | ~ | Y | Y | Y | Substantial |
| 0022 | Standard-Packaged Hook Installation | Y | Y | Y | Y | Y | Y | Y | **Exemplary** |
| 0023 | Unified Consumer Standards Control Plane | ~ | ~ | ~ | **N** | **N** | Y | **N** | Partial |
| 0024 | Catalog-Scoped Package Version Channels | ~ | ~ | ~ | **N** | **N** | Y | **N** | Partial |
| 0025 | MCP Service and SDK Boundary | Y | Y | Y | Y | **N** | Y | **N** | Partial |
| 0026 | MCP Local Read-Only Transport | Y | Y | Y | ~ | **N** | Y | **N** | Partial |
| 0027 | Adopt Go Alongside Python | Y | Y | Y | Y | Y | Y | Y | **Exemplary** |

B7 (universal terms) fails for all eleven Cohort A records and is satisfied or non-applicable elsewhere. B8 (out-of-scope is not an exception) is satisfied wherever tested — no ADR demands a waiver for a case it never governed. B10 is satisfied for both supersession chains.

## 8. Reproduction

Every mechanical claim above is reproducible from a clean checkout at `b7206941`.

```bash
# F5 — required MADR sections in every record
for f in docs/adr/adr-0*.md; do
  printf '%s ctx=%s opt=%s out=%s\n' "$(basename "$f")" \
    "$(grep -c '^## Context and Problem Statement$' "$f")" \
    "$(grep -c '^## Considered Options$' "$f")" \
    "$(grep -c '^## Decision Outcome$' "$f")"
done

# F1 — scaffold is the 1.3 template while the lock claims 1.4
sha256sum docs/adr/adr.template.md \
  src/project_standards/payloads/adr/1.3/templates/adr.md \
  src/project_standards/payloads/adr/1.4/templates/adr.md
grep -n -A10 'docs/adr/adr.template.md' .standards/lock.toml

# §2 — the 0013/0014 exclusion-language cliff
for f in docs/adr/adr-0*.md; do
  st=$(grep -m1 '^status:' "$f" | tr -d " '")
  [ "$st" = 'status:active' ] || continue
  printf '%-68s %s\n' "$(basename "$f")" \
    "$(grep -c -iE 'does not (govern|decide|require|define|authorize|change|reconcile|apply)|out of scope|remains? (undecided|historical)|is deferred|excluded (outright|from)|as a class' "$f")"
done

# F4 — the governed population ADR 0014 names
ls docs/adr-library 2>&1; grep -n 'adr-library' .standards/config.toml
```

Link and frontmatter-path integrity were checked with a short script over `docs/adr/**`: 167 relative links resolved, zero dangling `related`/`source` paths.

Second-pass evidence:

```bash
# C2 — no provider registry; providers resolve from the payload manifest
grep -n 'def invoke_provider' -A25 src/project_standards/control_plane/providers.py
grep -rniE 'provider_registry|register_provider|PROVIDER_REGISTRY' \
  src/project_standards/control_plane/ src/project_standards/package_contract/

# C3 — both ownership models are live
grep -n '_validate_authorities' src/project_standards/standards_graph/validators.py
grep -n 'class AdapterRegistry' src/project_standards/control_plane/adapters/registry.py

# C4 — which ADRs cite ADR 0005
grep -ln 'adr-0005' docs/adr/*.md

# O1, O2 — frontmatter-scope and exception-escalation claims
grep -n -iE 'exclude[d]? .*(frontmatter|managed[- ]document)' docs/adr/adr-0*.md
grep -n -iE 'exception[s]? to|requires? an ADR|narrow exception|another ADR' docs/adr/adr-0*.md

# O5 — what the ADR payload actually declares about markdown-frontmatter
sed -n '/\[relations\]/,/^$/p' src/project_standards/payloads/adr/1.4/payload.toml
grep -n -A4 'FM→ADR compatibility' meta/versioning.md
```

The one-way `related` edge count (S1) came from a script that parses each record's frontmatter, keeps only `related` entries pointing at `docs/adr/adr-*.md`, and reports edges whose reverse is absent: 37 of them.

## 9. Second pass — inter-ADR conflicts, overlapping ownership, and consistency

Pass 1 graded each record in isolation. This pass treats the 23 active ADRs as a decision graph and asks a different question: where do two records claim the same ground, contradict each other, or leave a boundary unowned?

The headline result is that **the corpus has no conflicting decisions but several contested authorities**. Nothing here is a case of two ADRs mandating incompatible outcomes. What recurs instead is one ADR's mechanism being quietly replaced by a later one, or two ADRs claiming the same guarantee through different models, with neither record acknowledging the other. Under 1.4 that is exactly the failure the boundary rules exist to prevent: an unbounded ADR keeps apparent authority over ground a later decision took.

Findings are grouped as **C** (contested authority), **O** (overlapping ownership), and **S** (consistency).

### C1 — Resource URI grammar: three producers, two active ADRs, no reconciliation

Detailed in §5. Added here for graph completeness, with one point §5 did not make: **ADR 0010 has no pointer to ADR 0026.** ADR 0026 lists 0010 in both `related` and More Information and openly discloses the divergence; the reverse edge does not exist. A reader arriving at ADR 0010 — the record that still reads as repository policy on resource addressing — has no way to learn that a later active ADR froze a different grammar and declined to reconcile it.

### C2 — ADR 0006's chosen mechanism is no longer the mechanism

ADR 0006 evaluated exactly two options and chose "**provider registries** — a registry per capability (validators, fixers, drift checks, ID generation, extraction) that standards register implementations into, **looked up by standard identity at call time**".

That is not how providers work today:

- `invoke_provider` (`src/project_standards/control_plane/providers.py:732`) resolves a provider from `payload.manifest.providers`, matching on provider id and operation against the selected immutable payload. There is no capability registry and no registration step.
- ADR 0023 states the current rule directly: "Only immutable, catalog-trusted package payloads may declare providers", and the control plane "consumes that contract generically and contains no package-ID branches for ordinary behavior."
- The only registry in the control plane is `AdapterRegistry` (`control_plane/adapters/registry.py`), which serves ADR 0023's semantic-composition model — a different concept that happens to share the word.
- ADR 0006's five capabilities have become twelve declared operations (`package_contract/payload.py`, `_OPERATION_CONTRACT`).

ADR 0006's **principle** survives intact and is still correct: standard-specific behavior must be pluggable, and adding a standard must not touch shared dispatch code. Its **stated mechanism** was replaced. ADR 0006 remains `status: active`, unamended, with the registry wording unqualified; ADR 0023 lists it in `related` without reciprocation and never says it is replacing it. This is the clearest instance in the corpus of substance changing without amendment or supersession — and the direct motivation for issue #127.

### C3 — Two live ownership models claim the same guarantee

|  | ADR 0004 | ADR 0023 |
| --- | --- | --- |
| Model | `(domain, target, concern, owner, mutability)` authority tuples | Semantic units: TOML key path, JSON/JSONC key, YAML mapping, EditorConfig property, task/hook identity, delimiter-bounded Markdown block |
| Conflict rule | Overlapping mutating claims are a validation error | No precedence; overlapping or ambiguous claims block before writes; identical units are reference-counted |
| Still implemented? | Yes — `_validate_authorities`, `standards_graph/validators.py:344` | Yes — planner and adapter registry |
| Claimed guarantee | "arbitrary co-adoption can be **proven conflict-free**" | "package composition and removal become deterministic, reviewable, and **safe**" |

Both are active, both are implemented, and they are in fact complementary: ADR 0004 governs authoring-time conflicts between standard manifests in the standards graph, while ADR 0023 governs write-time ownership of bytes inside a consumer's files. **Neither ADR states that boundary.** ADR 0004's population is never limited to the graph plane, so its conflict-free guarantee reads as covering consumer composition too. ADR 0023 lists 0004 in `related` and does not say what it leaves to it.

This is the paradigm 1.4 case: two records claiming one guarantee through different mechanisms, each recoverable with a single exclusion sentence, neither having one.

### C4 — The ADR that decided tool shape is invisible to the ADRs that fixed the tool registry

ADR 0005 chose "keep future agent/MCP tools generic over `standard_id` and operation" and rejected "a new tool for every standard" because "the tool surface would grow linearly with the number of standards".

ADR 0026 registers six fixed tools (`standards_list`, `standard_read`, `repo_inspect`, `reconcile_preview`, `validate_repo`, `drift_check`) and **explicitly omits** a generic provider-dispatch tool, recording that omission as the resolution of `SPEC-MS01 OQ-007`.

These reconcile cleanly: ADR 0026's tools are generic over standard and version — `standards_list` and `standard_read` take the standard as a parameter — so the surface is fixed at six regardless of how many standards the catalog carries, which is the property ADR 0005 actually protected. ADR 0005 constrains growth _per standard_; ADR 0026 declines a generic dispatch tool _per provider operation_. Different axes.

**That reasoning appears nowhere.** ADR 0026 does not cite ADR 0005 in prose, `related`, `source`, or More Information; neither does ADR 0025. Six other ADRs cite 0005; the two records that implemented its subject do not. A reader who consults ADR 0005 before reviewing the MCP surface will see an apparent departure with no recorded justification, and — because 1.4 says an out-of-scope case needs no exception — may wrongly conclude that an exception was required and skipped.

### C5 — ADR 0002's "primary manifest" claim was narrowed twice without amendment

ADR 0002 decided `standard.toml` is "the primary, machine-readable source of a standard's metadata", explicitly rejecting "expand `registry.json` only" on the grounds that "a single registry would grow too broad and distant from each bundle".

Catalog 5 has three manifest planes:

| Plane | Owns | Established by |
| --- | --- | --- |
| Family `standard.toml` | Lifecycle state and relationships | ADR 0002, narrowed by ADR 0018 |
| Per-version `payload.toml` | Artifacts, resources, providers, digests, destinations | ADRs 0019, 0023 |
| `src/project_standards/catalogs/5.toml` | Every advertised version, digest, and channel role | ADR 0024 |

The third is a central registry of advertised package metadata — structurally the thing ADR 0002 rejected, reintroduced for a different and good reason (offline resolution and permanent version advertisement). ADR 0018 partially patches the drift by asserting "The family `standard.toml` is the canonical machine-readable **lifecycle** source", silently narrowing 0002's claim from all metadata to lifecycle. ADR 0002 still carries the original unqualified wording and no amendment banner.

### O1 — Markdown frontmatter scope is written by five ADRs at three normative strengths

| ADR | Claim | Modality |
| --- | --- | --- |
| 0014 | The `standards.markdown-frontmatter.config` table "is the source of truth for this repository's managed Markdown scope" | declares itself the authority |
| 0015 | Excludes `standards/**` from local frontmatter validation | decides |
| 0016 | "The consuming repo **must keep** `.agents/**` excluded from managed-document frontmatter validation" | must |
| 0021 | "A consumer repository **must exclude** installed skill paths from managed Markdown frontmatter validation, formatting, linting, type checking, **or other standards**" | must, open-ended population |
| 0022 | "Consumer tooling **should exclude** [installed hook paths] from unrelated content-management rules **where appropriate**" | should, discretionary |

One class of rule, three normative strengths, and two records reaching outside their declared class — ADR 0021's trailing "or other standards" binds packages it does not name, and ADR 0016 imposes a rule on every consuming repository from inside a decision about who owns one skill. ADR 0014 declares itself the scope authority, and three later ADRs write scope rules without amending it.

Under 1.4 the fix is mechanical: each of 0016, 0021, and 0022 should state the population it binds and defer scope authority to 0014, or 0014 should absorb the rules.

### O2 — Exception escalation has four incompatible formulations, and all four predate 1.4's distinction

| ADR | Escalation clause |
| --- | --- |
| 0018 | "Exceptions to this lifecycle methodology require an ADR." |
| 0019 | "require an ADR **or an explicit manifest-backed exception that graph validation can surface**" |
| 0021 | "invalid **unless a later ADR creates a narrow exception**" |
| 0022 | "requires **another ADR or a superseding decision**" |
| 0027 | Defines an amendment threshold instead: routine config changes need nothing; boundary changes need an amendment |

ADR 0027's form is the one 1.4 endorses. The other four share a defect the standard now names explicitly: none distinguishes an **exception** (an in-population item permitted to depart from the rule) from an **out-of-scope case** (an item the ADR never governed). 1.4 is direct about this — "Do not require an exception, waiver, or superseding ADR for a case the ADR never governed." As written, four active ADRs instruct a reader to open an ADR for cases that may simply lie outside them.

ADR 0019's manifest-backed variant is additionally the only one that is machine-surfaceable, and is worth propagating rather than harmonizing away.

### O3 — The `.agents/` root has three claimants and no owner

| ADR  | Claimed destination                         |
| ---- | ------------------------------------------- |
| 0016 | `.agents/skills/markdown-frontmatter/`      |
| 0021 | `.agents/skills/<skill-id>/` (class rule)   |
| 0022 | `.agents/hooks/<standard-id>/` (class rule) |

The destinations do not collide, and each record justifies its own subtree well. Nothing governs the **root**: who creates `.agents/`, what else may live directly under it, whether a future standard may claim `.agents/<something-new>/`, and who adjudicates if two packages want the same subtree. ADR 0021 comes closest — a new project-local path "may be added only when it remains inside the consumer repository or project and is declared explicitly in the selected payload manifest" — but that governs skills, and a hook or a future artifact class is not bound by it. In 1.4 terms this is unassigned reserved authority: three ADRs each reserve a slice and none reserves the container.

### O4 — ADR 0016 is a special case of ADR 0021, unmarked in both directions

ADR 0016 (2026-07-09) decided ownership and installation for the Markdown Frontmatter skill. ADR 0021 (same day, higher number) generalized the identical reasoning to "skills shipped by standard packages **as a class**", and its rules cover everything 0016 decided about installation destination and global-install prohibition.

ADR 0016 carries an "Amended by ADR 0023" banner and no relationship to 0021. ADR 0021 lists 0016 in `source` — evidence it was written from — but nothing marks it as the record 0021 generalizes. Two active ADRs govern one skill's installation destination, and a future change to the class rule in 0021 would leave 0016 stating the old rule for its one skill.

### O5 — A cross-package compatibility constraint is asserted outside the ADR corpus

`meta/versioning.md` §FM→ADR compatibility states: "The resolved ADR payload declares the Frontmatter contract versions it supports. Selection remains independent **subject to declared compatibility** … the resolver and validator **fail closed** on an incompatible pair."

Nothing in the ADR corpus governs this, and the surrounding evidence points the other way:

- ADR 0013's taxonomy classifies the relationship as `companion`, defined there as a non-binding recommendation, not a hard dependency. A fail-closed version constraint is, in 0013's own vocabulary, `extends` or `conflicts`.
- The 1.4 standard text says Markdown Frontmatter is "a compatible companion for metadata, **not an installation dependency**."
- `src/project_standards/payloads/adr/1.4/payload.toml` declares `companions = ["markdown-frontmatter"]` with `extends = []`, `conflicts = []`, and no version constraint of any kind.
- I did not locate an implementing fail-closed check in `control_plane/` or `package_contract/`. Recorded as **not located**, not as absent — a targeted search would settle it.

Either `meta/versioning.md` overstates a binding constraint, or a real binding cross-package constraint exists with no ADR and no manifest declaration behind it. ADR 0013 is the natural owner and says nothing about version-level compatibility between companions.

### S1 — The decision graph cannot be traversed backwards

Of the ADR→ADR edges in `related`, **37 are one-way**. The pattern is systematic rather than random: later ADRs cite the earlier decisions they build on, and the earlier records are never updated to point forward.

| Cited record           | Cites it               | Points back |
| ---------------------- | ---------------------- | ----------- |
| 0004, 0006, 0013       | 0023                   | none        |
| 0010, 0012, 0023, 0024 | 0025, 0026             | none        |
| 0002                   | 0010, 0012, 0019       | none        |
| 0007                   | 0006, 0011, 0012, 0013 | none        |

ADR 0014's own field-value policy defines `related` as "Nearby standard, ADR, spec, or meta doc a reader would naturally consult" and does not require reciprocity, so this violates no rule. It is still the mechanism behind C1–C5: in every one of those findings, the reader who most needs the pointer is standing on the record that lacks it. Reciprocating the ~12 edges that carry a substantive relationship — as distinct from the incidental ones — would close most of the navigational gap without a policy change.

### S2 — Frozen evidence is presented as current authority

| ADR | Cited as authority | Current default |
| --- | --- | --- |
| 0014, 0016 | `markdown-frontmatter/versions/1.2/**` | 1.9 |
| 0018, 0019, 0021, 0022 | `standard-bundle-authoring/versions/2.0/README.md` | 2.6 |
| 0022 | `agent-handoff/versions/1.1/hooks/session-start/session_start.py` | 1.9 (per `.standards/lock.toml`) |

Every link resolves — advertised payloads are permanent under ADR 0024 — so nothing is broken. The defect is framing: a More Information entry reading "Standard bundle authoring contract: `…/versions/2.0/README.md`" presents itself as the document to consult now, not as the evidence the decision was made against. ADR 0018 shows the correct handling in prose ("`active` consumer-facing standards must satisfy ADR 0023 and SPEC-BA02") while its own link list still points at 2.0.

The corpus has no convention distinguishing _the evidence I decided on_ from _the current authority you should read_. ADR 0014's `source` versus `related` split is exactly that distinction and is already available; the body link lists do not use it.

### S3 — Terminology drift across the V1→V2 rename

| Term               | Used normatively by          |
| ------------------ | ---------------------------- |
| "standard bundle"  | 0001, 0002, 0004, 0007, 0010 |
| "standard package" | 0018, 0019, 0021, 0022       |
| "package family"   | 0018                         |
| "payload"          | 0019, 0023, 0024             |

ADR 0019 states that V1 layout paths "remain historical migration and compatibility evidence only", which handles the paths. It does not handle the vocabulary: ADRs 0001–0010 still use "bundle" inside active normative sentences — "every standard bundle must now maintain an additional manifest file" — with nothing indicating the term was renamed or that the rule now binds `standards/<id>/versions/<version>/`. A reader cannot tell whether those rules survived the rename or were scoped to a layout that no longer exists.

### S4 — The index asserts a supersession discipline the corpus does not have

`docs/adr/README.md:37` states that ADRs 0001–0013 "were accepted on 2026-07-07; later decisions **preserve that history through explicit amendment or supersession**."

C2, C3, and C5 are counterexamples. ADR 0006's mechanism was replaced, ADR 0004's guarantee was duplicated by a different model, and ADR 0002's claim was narrowed — none through amendment, none through supersession, and none reflected in either record. The index states the intended discipline as though it were the achieved one.

### S5 — Cross-references to superseded ADRs

ADRs 0018, 0019, 0021, and 0022 cite superseded records (0003, 0017, 0020) in `source` and More Information. This is **correct** and worth recording as a pass: each is cited as historical evidence, and ADR 0018 labels it explicitly ("ADR 0017 remains historical context for the superseded V1 adoption model"). No active ADR presents a superseded decision as current authority. Both supersession chains — 0023 over 0003/0008/0017, and 0024 over 0020 — are reciprocal and correctly scoped under B10.

## 10. Remediation backlog

Ordered by value per unit of effort, covering both passes. None of this was applied.

### Tier 1 — small, independent, high leverage

| # | Item | Finding | Scope | Why it ranks here |
| --- | --- | --- | --- | --- |
| 1 | Replace `docs/adr/adr.template.md` with the 1.4 template and correct the lock record | F1 | 1 file + lock | Stops the defect reproducing; every future ADR inherits boundary prompts. Requires deciding how a create-only artifact is legitimately refreshed — that decision is itself worth an ADR |
| 2 | Reciprocate the ~12 substantive `related` edges | S1 | ~12 ADRs, frontmatter only | Cheapest item with the widest effect: it is the mechanism behind C1–C5, and in each of those the reader who needs the pointer is standing on the record that lacks it |
| 3 | Retarget `docs/adr/README.md` to the 1.4 standard and correct its supersession-discipline claim | F3, S4 | 2 lines + 1 frontmatter entry | Authors following the index read the pre-boundary standard, and the index asserts a discipline C2/C3/C5 contradict |
| 4 | Note in ADR 0006 that manifest-declared providers replaced capability registries | C2 | 0006 (+0023 back-edge) | An active ADR names a mechanism that does not exist. Sanctioned form depends on #127; an interim banner matches existing practice |
| 5 | Correct ADR 0014's governed population and drop the dead `docs/adr-library/**` include | F4 | 0014 + `.standards/config.toml` | Already on the owner queue; 1.4 makes it a boundary defect, not just stale config |
| 6 | Add reciprocal exclusions to ADRs 0004 and 0023 naming the graph plane and the consumer-file plane | C3 | 2 sentences | Two records claim one guarantee; one sentence each recovers both |
| 7 | Cite ADR 0005 from ADRs 0025/0026 with the per-standard-versus-per-operation reasoning | C4 | 2 ADRs | The reconciliation is sound and entirely unrecorded |
| 8 | Add an exclusion to ADR 0010 for the MCP URI grammar, or reconcile 0010 and 0026 | §5, C1 | 0010 (+0026) | The one live contested grammar; ADR 0026 already flagged it for owner decision |
| 9 | Settle the FM→ADR compatibility claim in `meta/versioning.md` | O5 | 1 doc, possibly 1 ADR | Either the meta doc overstates a binding constraint, or a fail-closed cross-package rule has no ADR and no manifest declaration |

### Tier 2 — substantive, best done as deliberate passes

| # | Item | Finding | Scope | Why it ranks here |
| --- | --- | --- | --- | --- |
| 10 | Move the five Cohort A requirements out of `### Consequences` into Decision Outcome | §4, B6 | 0001, 0002, 0004, 0006, 0007 | Load-bearing rules sit where 1.4 says policy must not live and where readers skip |
| 11 | Add a boundary paragraph to each Cohort A Decision Outcome | §4, B1–B3 | 11 ADRs | Highest total value, highest cost. Mechanical per record: population, applicability, one exclusion. Do as one pass — the eleven share a shape and will be more consistent rewritten together |
| 12 | Harmonize the frontmatter-scope claims and defer scope authority to ADR 0014 | O1 | 0014, 0016, 0021, 0022 | One class of rule at three normative strengths, two of them binding unnamed populations |
| 13 | Assign ownership of the `.agents/` root | O3 | new ADR, or extend 0021/0022 | Three ADRs each reserve a subtree; none reserves the container |
| 14 | Harmonize exception clauses on ADR 0027's amendment-threshold form, keeping 0019's manifest-backed variant | O2 | 0018, 0019, 0021, 0022 | Four formulations, none distinguishing an in-population exception from an out-of-scope case — the distinction 1.4 introduced. Depends on #127 |
| 15 | Mark ADR 0016 as the special case ADR 0021 generalizes | O4 | 0016, 0021 | A later class-rule change would leave 0016 stating the old rule for its one skill |
| 16 | Record that ADR 0002's claim is now lifecycle-scoped | C5 | 0002 (+0018, 0024) | Narrowed twice without amendment; the central catalog is the registry 0002 rejected |
| 17 | Decide ADR 0012's lifecycle now that its gate has passed | §4 | 0012 | An active ADR appears to prohibit shipped work |
| 18 | Split ADR 0024's release-classification rules from its consumer selector rules | §4, B9 | 0024 + new ADR | Two populations in one record; the clearest split case in Cohort C |

### Tier 3 — conventions and cosmetics

| # | Item | Finding | Scope | Why it ranks here |
| --- | --- | --- | --- | --- |
| 19 | Adopt a convention separating frozen evidence from current authority in body link lists | S2 | corpus-wide | The `source`-versus-`related` split already encodes this; body links do not use it |
| 20 | Reconcile bundle/package/family/payload terminology in ADRs 0001–0010 | S3 | 5 ADRs | Active normative sentences use a vocabulary the V1→V2 rename retired |
| 21 | Rename ADR 0025 and 0026 files to omit the repository name | F2 | 2 files + inbound references | Cosmetic; touches the index, five frontmatter references, and inline links |

**Filed:** the amendment-vocabulary gap (§6) is now [issue #127](https://github.com/L3DigitalNet/project-standards/issues/127). Items 4, 14, and 16 all want the sanctioned form it requests, so #127 is a soft prerequisite for the cleanest version of each; interim banner notes match existing practice and need not wait.

## 11. Not assessed

- The four superseded ADRs (0003, 0008, 0017, 0020), graded only for supersession correctness under B10 and for cross-reference handling under S5.
- Whether each decision is _correct_ — this assesses conformance to the recording standard and internal consistency, not the engineering merit of the decisions.
- ADRs in other repositories that adopt this package.
- `standards/adr/library/**`, which holds reusable candidate ADR material rather than this repository's decisions.
- Prettier and markdownlint conformance of the ADR corpus, which the repository gate already owns.
- Whether a fail-closed FM→ADR compatibility check exists in the control plane (O5) — searched and not located, not proven absent.
- Conflicts between the ADR corpus and the specifications under `docs/specs/`. Pass 2 checked ADR-to-ADR and ADR-to-implementation consistency only; the specs are a third authority plane and were out of scope.
