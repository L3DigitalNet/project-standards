# Design: Per-standard versioning for `project-standards`

**Date:** 2026-06-06 **Status:** approved (brainstorming complete; awaiting implementation plan) **Author:** session 2026-06-06

## Problem / Goal

This repo governs **three standards** — Markdown Frontmatter, ADR, and Python Tooling SSOT — but ships them under a **single version plane**: one git tag, one Python package (`project-standards`), one reusable workflow. A consumer pins `@v1` and atomically receives all three at one commit.

Two problems follow:

1. **No independent adoption.** A consumer cannot move to a newer Frontmatter contract while holding ADR steady — there is only one number to pin, and it moves all standards together.
2. **Cross-axis contamination.** Runtime/tooling churn inflates a number consumers read as "the standards changed." The pending `2.0.0` is a MAJOR **only** because `requires-python` jumped `3.11`→`3.13`; no standard's _content_ changed, yet every standard appears to have had a breaking release.

The pre-existing per-component markers are ad hoc and non-uniform: Frontmatter has `schema_version` (`1.1`), ADR rides it with no number of its own, and Python Tooling carries a prose `internal revision 1.6` banner that is explicitly "not a release version."

**Goal:** give each standard its own SemVer, reconciled with the repo's monolithic distribution, so that:

1. each standard has its own **contract version**;
2. a consumer selects **each standard's version independently** in config (adopt Frontmatter 2.0 while ADR stays 1.0);
3. tooling/runtime breaks version the **tool**, not the standards;
4. the **ADR→Frontmatter dependency** (ADR is a profile _over_ the frontmatter schema) is explicit and machine-checked.

## Decisions (locked during brainstorming)

1. **Goal = independent adoption.** A consumer can adopt one standard's version independently of the others — not merely clearer change-comms.
2. **Approach A — config-selected contract versions; one tool, one distribution pin.** The validator becomes multi-version-aware and the consumer selects each standard's contract version in `.project-standards.yml`. Rejected: **B** (per-standard git-tag tracks + per-standard CI jobs — fights the single-package reality, forces a package split or validator duplication) and **C** (split into three repos — abandons single-source-of-truth simplicity; ADR→FM becomes a cross-repo dependency).
3. **Python Tooling = versioned label, no new enforcement.** It is copy-adopted; "adopt v1.0" means "copy scaffolds from the matching ref." No checker is built.
4. **Starting numbers:** Frontmatter **keeps its existing line** (currently `1.1`; not reset); ADR **starts at `1.0`**; Python Tooling **starts at `1.0`** (replacing the `internal revision 1.6` banner). Resetting Frontmatter to `1.0` was rejected — it would rewrite every doc's `schema_version`, collide with the real `1.0`→`1.1` history, and break the enum's meaning.
5. **Frontmatter version selection = config pin + doc-declared.** A doc declares `schema_version` (as today); an **optional** `markdown.frontmatter.version` in config sets the repo's target so stray-version docs fail. **Unset = accept any bundled version** (back-compat).
6. **ADR contract version is consumer-wide (config), not per-doc.** ADR docs keep their frontmatter `schema_version` for the metadata profile; the ADR body-rule version comes from `markdown.adr.version`.
7. **Two version planes** (below). `requires-python`-style breakage lives on the **tool** plane and touches no standard's contract version.

## The model: two version planes

| Plane | What it versions | Who bumps it | How a consumer sees it |
| --- | --- | --- | --- |
| **Tool release** | the validator CLI + reusable workflow + the _bundle_ of contract versions it ships | the release ritual | the git tag they pin (`@v1` → the tool's v-line) |
| **Contract version** (×3) | each standard's _content_ — fields/vocab (Frontmatter), body rules + FM-compatibility (ADR), scaffold set (Python Tooling) | whoever edits that standard | a `version:` selected in config (FM/ADR) or a ref they copy from (Python Tooling) |

**The reconciliation move:** contract versions are **delivered by tool releases**. The tool at version `T` bundles a known set of contract versions, e.g. `{frontmatter: ["1.1"], adr: ["1.0"]}`. "Adopt Frontmatter 2.0" therefore requires a tool new enough to _bundle_ 2.0. This maps onto the existing consumer-outcome rule:

- **Adding** a contract version to the bundle → **MINOR** tool release (safe to inherit on `@vN`; nothing a passing consumer relied on changed).
- **Removing** a bundled contract version → **MAJOR** tool release (a consumer pinned to that version would newly fail).

The pending `requires-python 3.11→3.13` break is a **tool-plane** MAJOR (the tool's `2.0.0`) and changes **zero** standard contract versions.

## Per-standard contract versions

- **Frontmatter** — its contract version **is the existing `schema_version`** field. No new concept; it simply stops being capped at `1.1` and gains a `2.x` line when the field set or controlled vocabularies change. Stays `1.1` today.
- **ADR** — gets its own number, **`1.0`**. It declares which Frontmatter version(s) it supports (it is a profile over FM). Body-rule version is consumer-wide via config.
- **Python Tooling** — first real SemVer, **`1.0`**, replacing the `internal revision N.M` banner. Pure label; no enforcement.

**Starting compatibility matrix** (bundled in the tool):

```
Frontmatter    1.1
ADR            1.0  → supports Frontmatter: ["1.1"]
Python Tooling 1.0  (copy-adopted label; no compatibility edges)
```

### FM→ADR compatibility (machine-checked)

Each bundled ADR contract version declares its supported Frontmatter version set. The validator enforces the configured combination:

```yaml
# .project-standards.yml — INVALID combo example
markdown:
  frontmatter: { version: '2.0' }
  adr: { version: '1.0' } # ADR 1.0 supports FM ["1.1"] only
```

→ validator hard-errors: `ADR 1.0 supports Frontmatter [1.1]; configured frontmatter.version is 2.0`. This turns the latent ADR→FM coupling into an explicit, enforced contract.

## Validator mechanics (Approach A)

### Multi-version bundle + registry

The tool bundles multiple contract versions side by side, behind a small registry. **Critical invariant:** the current schema's path _is its `$id`_ and a consumer contract — so the `1.1` schema **keeps its current filename**; only _new_ versions get versioned filenames.

```text
src/project_standards/schemas/
  markdown-frontmatter.schema.json          # = 1.1  (UNCHANGED $id/path — invariant)
  markdown-frontmatter-2.0.schema.json      # future, when FM 2.0 is authored
  adr/
    adr-1.0.contract.json                   # ADR body-rule descriptor + supported FM set
  registry.json                             # version → schema file + compatibility edges
```

`registry.json` maps each standard version to its schema/contract file and (for ADR) its supported-FM set. Adding a row = a MINOR tool release; removing a row = MAJOR.

### Config selectors (`.project-standards.yml`)

```yaml
markdown:
  frontmatter:
    version: '1.1' # OPTIONAL target; unset = accept any bundled version
    schema: 'markdown-frontmatter'
    required: true
    include: [...]
    exclude: [...]
  adr:
    version: '1.0' # OPTIONAL; default = latest bundled
    require_sections: true
python_tooling:
  version: '1.0' # OPTIONAL; RECORDED in the report only, never enforced
```

### Resolution algorithm

1. For each managed doc, read its declared `schema_version`.
2. Resolve the target FM version: `markdown.frontmatter.version` if set, else "any bundled."
3. Validate the doc against the bundled FM schema for the resolved version; error if the doc's `schema_version` is not in the allowed/bundled set.
4. For docs with `doc_type: adr`, additionally apply the ADR contract for `markdown.adr.version` (default = latest bundled) and check the doc's FM `schema_version` against that ADR version's supported-FM set.
5. `python_tooling.version` is surfaced in the validator's report output only; it has no pass/fail effect.

## Release & classification changes

`meta/versioning.md` is rewritten around the two planes:

- **Tool-plane classification table** — the existing CLI/workflow rows, plus explicit rows for _bundle_ changes (add contract version = MINOR; remove = MAJOR).
- **Contract-plane rule, per standard** — within a single standard's line the previously-passing rule applies: an additive field/value = MINOR; a stricter rule, removed enum value, or removed/renamed field = MAJOR. Each standard's line advances on its own cadence.
- **FM→ADR compatibility** documented as a first-class contract with the supported-set table.
- **Python Tooling** keeps the copy-adopted classification (impact-on-re-sync), now expressed as a SemVer line rather than an internal counter.

Each standard's README gains a small **version banner** (Frontmatter: its `schema_version` line; ADR: `ADR contract v1.0`; Python Tooling: `v1.0`, replacing `internal revision 1.6`).

## Invariants — consumer contract (must NOT change)

- The bundled schema's `$id`/path `src/project_standards/schemas/markdown-frontmatter.schema.json` (the `1.1` schema stays at this filename).
- Reusable workflow filenames; the `validate-frontmatter` console-script entry point; the package name `project_standards`.
- All published git tags (`v1.x`, the moving `v1`).
- **A config with no `version:` keys validates byte-identically to today.** Existing docs (`schema_version: '1.1'`) keep passing.

## Versioning classification of _this_ change

Introducing the scheme is **additive on the tool plane**: new _optional_ config keys, multi-version bundling, and a compatibility check that fires only on `adr.version`/`frontmatter.version` combinations no existing consumer configures today → no previously-passing repo newly fails → **MINOR** tool change. It nonetheless **ships inside the already-locked tool `2.0.0`** (whose MAJOR is the `requires-python` bump); it is not itself the reason for the major.

## Scope / non-goals

**In scope:** the two-plane model; validator multi-version registry + config selectors + FM→ADR compatibility check + version reporting; rewritten `meta/versioning.md`; per-standard README version banners; CHANGELOG entry; tests for the resolution algorithm, the compatibility check, and back-compat (no-`version` config).

**Non-goals (YAGNI):** per-standard git tags (Approach B); repo split (Approach C); Python Tooling enforcement; _authoring_ a Frontmatter 2.0 (build the machinery only — 2.0 content is a separate, later change); running the release ritual; any change to the schema `$id`/path or workflow filenames.

## Deliverables checklist

- [ ] `registry.json` + multi-version schema/contract bundle (1.1 schema unmoved).
- [ ] Validator: version resolution, FM→ADR compatibility enforcement, `python_tooling.version` reporting.
- [ ] `.project-standards.yml` (this repo) + the adopt examples gain the optional `version:` keys; config docs updated.
- [ ] `meta/versioning.md` rewritten (two planes, per-standard contract rules, compatibility table).
- [ ] README version banners on all three standards.
- [ ] Tests: resolution, compatibility errors, back-compat (no-`version` config behaves as today).
- [ ] CHANGELOG entry (rides the tool `2.0.0`).

## Open questions

None — resolved during brainstorming (goal, approach, Python Tooling treatment, starting numbers, FM selection mechanism all locked above).
