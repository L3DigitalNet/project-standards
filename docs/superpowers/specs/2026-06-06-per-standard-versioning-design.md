# Design: Per-standard versioning for `project-standards`

**Date:** 2026-06-06 **Status:** approved (brainstorming complete; awaiting implementation plan) **Author:** session 2026-06-06

## Problem / Goal

This repo governs **three standards** — Markdown Frontmatter, ADR, and Python Tooling SSOT — but ships them under a **single version plane**: one git tag, one Python package (`project-standards`), one reusable workflow. A consumer pins `@v1` and atomically receives all three at one commit.

Two problems follow:

1. **No independent adoption.** A consumer cannot move to a newer Frontmatter contract while holding ADR steady — there is only one number to pin, and it moves all standards together.
2. **Cross-axis contamination.** Runtime/tooling churn inflates a number consumers read as "the standards changed." The pending `2.0.0` is a MAJOR **only** because `requires-python` jumped `3.11`→`3.13`; no standard's _content_ changed, yet every standard appears to have had a breaking release.

The pre-existing per-component markers are ad hoc and non-uniform: Frontmatter has `schema_version` (`1.1`), ADR rides it with no number of its own, and Python Tooling carries a prose `internal revision 1.6` banner that is explicitly "not a release version."

**Goal:** give each standard its own **two-part (`major.minor`) contract version** (see [Version grammar](#version-grammar)), reconciled with the repo's monolithic distribution, so that:

1. each standard has its own **contract version**;
2. a consumer selects **each standard's version independently, subject to declared cross-standard compatibility** — e.g. advance ADR to a new body-rule version without touching Frontmatter, or move to Frontmatter `2.0` together with an ADR version that declares support for it;
3. tooling/runtime breaks version the **tool**, not the standards;
4. the **ADR→Frontmatter dependency** (ADR is a profile _over_ the frontmatter schema) is explicit and machine-checked.

## Decisions (locked during brainstorming)

1. **Goal = independent adoption.** A consumer can adopt one standard's version independently of the others — not merely clearer change-comms.
2. **Approach A — config-selected contract versions; one tool, one distribution pin.** The validator becomes multi-version-aware and the consumer selects each standard's contract version in `.project-standards.yml`. Rejected: **B** (per-standard git-tag tracks + per-standard CI jobs — fights the single-package reality, forces a package split or validator duplication) and **C** (split into three repos — abandons single-source-of-truth simplicity; ADR→FM becomes a cross-repo dependency).
3. **Python Tooling = versioned label, no new enforcement.** It is copy-adopted; "adopt v1.0" means "copy scaffolds from the matching ref." No checker is built.
4. **Starting numbers:** Frontmatter **keeps its existing line** (currently `1.1`; not reset); ADR **starts at `1.0`**; Python Tooling **starts at `1.0`** (replacing the `internal revision 1.6` banner). Resetting Frontmatter to `1.0` was rejected — it would rewrite every doc's `schema_version`, collide with the real `1.0`→`1.1` history, and break the enum's meaning.
5. **Frontmatter version selection = config pin + doc-declared, layered over existing schema resolution.** A doc declares `schema_version` (as today); an **optional** `markdown.frontmatter.version` resolves (via the registry) to a bundled schema. **Unset = the current default bundled schema (the `1.1` contract), exactly as today** — which accepts docs declaring `schema_version` `1.0` _or_ `1.1`. A custom schema (`--schema <path>` or a config `schema:` path) **bypasses** version selection; setting both a custom `schema:` path and `frontmatter.version` is a config error. See [Legacy & custom-schema compatibility](#legacy--custom-schema-compatibility).
6. **ADR contract version is consumer-wide (config), not per-doc.** ADR docs keep their frontmatter `schema_version` for the metadata profile; the ADR body-rule version comes from `markdown.adr.version`. **Unset = a frozen default (today `1.0`), never "latest bundled"** — so adding a future ADR `2.0` cannot silently change a no-version config's outcome.
7. **Two version planes** (below). `requires-python`-style breakage lives on the **tool** plane and touches no standard's contract version.
8. **Version grammar.** Contract versions are **`major.minor`** (no patch — matching `schema_version`, which the repo states carries no patch component); the **tool release** uses full SemVer `MAJOR.MINOR.PATCH`. "SemVer" in this spec refers only to the tool plane.
9. **`python_tooling.version` is config metadata only.** If present it is validated as a known registry value, but it is **not emitted in default output** — success/error streams are unchanged, preserving the byte-identical guarantee.
10. **`standards_version` is unchanged** — it remains the consumer's **tool-release pin** (tool plane) and coexists with the new contract-version keys; this change neither removes nor redefines it.

## The model: two version planes

| Plane | What it versions | Who bumps it | How a consumer sees it |
| --- | --- | --- | --- |
| **Tool release** | the validator CLI + reusable workflow + the _bundle_ of contract versions it ships | the release ritual | the git tag they pin (`@v1` → the tool's v-line) |
| **Contract version** (×3) | each standard's _content_ — fields/vocab (Frontmatter), body rules + FM-compatibility (ADR), scaffold set (Python Tooling) | whoever edits that standard | a `version:` selected in config (FM/ADR) or a ref they copy from (Python Tooling) |

**The reconciliation move:** contract versions are **delivered by tool releases**. The tool at version `T` bundles a known set of contract versions, e.g. `{frontmatter: ["1.1"], adr: ["1.0"]}`. "Adopt Frontmatter 2.0" therefore requires a tool new enough to _bundle_ 2.0. This maps onto the existing consumer-outcome rule:

- **Adding** a contract version to the bundle → **MINOR** tool release (safe to inherit on `@vN`; nothing a passing consumer relied on changed).
- **Removing** a bundled contract version → **MAJOR** tool release (a consumer pinned to that version would newly fail).

The pending `requires-python 3.11→3.13` break is a **tool-plane** MAJOR (the tool's `2.0.0`) and changes **zero** standard contract versions.

## Version grammar

- **Contract plane (per standard):** `major.minor` — no patch component, matching `schema_version` (the repo states `schema_version` carries no patch). Registry keys and config values use this two-part form (`'1.0'`, `'1.1'`, `'2.0'`).
- **Tool release plane:** full SemVer `MAJOR.MINOR.PATCH` (the git tag / `pyproject.toml` version). "SemVer" in this spec refers only to this plane.

## Per-standard contract versions

- **Frontmatter** — its contract version **is the existing `schema_version`** field. No new concept; it simply stops being capped at `1.1` and gains a `2.x` line when the field set or controlled vocabularies change. Stays `1.1` today.
- **ADR** — gets its own number, **`1.0`**. It declares which Frontmatter version(s) it supports (it is a profile over FM). Body-rule version is consumer-wide via config.
- **Python Tooling** — first real contract version (`major.minor`), **`1.0`**, replacing the `internal revision N.M` banner. Pure label; no enforcement.

**Starting compatibility matrix** (bundled in the tool):

```text
Frontmatter    1.1   (current bundled schema; ACCEPTS docs declaring schema_version 1.0 or 1.1)
ADR            1.0   → supports Frontmatter contract 1.1 (ADR docs declaring schema_version 1.0 or 1.1 are valid)
Python Tooling 1.0   (copy-adopted label; no compatibility edges)
```

There is no separate bundled "Frontmatter 1.0" contract: `1.0` is the legacy-compatible subset that the `1.1` schema's enum already accepts. Legacy `schema_version: '1.0'` documents therefore stay valid without any dedicated contract entry.

### FM→ADR compatibility (machine-checked)

Each bundled ADR contract version declares its supported Frontmatter contract set. "Independent" therefore means **independently selected, subject to declared compatibility** — not "any combination." The validator enforces the configured pair.

**Valid** — advance ADR while Frontmatter holds (once an ADR `1.1` ships that still targets FM `1.1`):

```yaml
markdown:
  frontmatter: { version: '1.1' }
  adr: { version: '1.1' } # ADR 1.1 supports FM 1.1 → OK
```

**Caught by the guard** — selecting a Frontmatter contract the chosen ADR version does not support:

```yaml
markdown:
  frontmatter: { version: '2.0' }
  adr: { version: '1.0' } # ADR 1.0 supports FM [1.1] only
```

→ validator hard-errors: `ADR 1.0 supports Frontmatter [1.1]; configured frontmatter.version is 2.0`. To run on Frontmatter `2.0`, the consumer also selects an ADR version that declares support for `2.0`. This turns the latent ADR→FM coupling into an explicit, enforced contract.

> At the **starting** point only `frontmatter 1.1` and `adr 1.0` exist, so there is no cross-version combination to select yet; independence becomes observable once a second version of either ships. The machinery is built now so the first such bump is a config edit, not a code change.

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
    version: '1.1' # OPTIONAL; resolves to a bundled schema. Unset = current default (1.1)
    schema: 'markdown-frontmatter' # bundled NAME or a custom PATH; a custom path bypasses `version`
    required: true
    include: [...]
    exclude: [...]
  adr:
    version: '1.0' # OPTIONAL; unset = frozen default 1.0 (never "latest")
    require_sections: true
python_tooling:
  version: '1.0' # OPTIONAL; config metadata only — validated if present, never emitted in default output
```

### Resolution algorithm

**Schema/version precedence** (first match wins), extending the validator's existing order:

1. `--schema <path>` (CLI) — explicit schema; bypasses version selection.
2. config `markdown.frontmatter.schema` when it is a **custom path** — bypasses version selection. Setting this _together_ with `markdown.frontmatter.version` is a config error (exit 2), not a silent ignore.
3. config `markdown.frontmatter.version` — resolved via the registry to a bundled versioned schema.
4. config `markdown.frontmatter.schema` as a bundled **name** — as today.
5. default bundled `markdown-frontmatter` (the `1.1` contract) — today's behaviour.

**Per document:**

1. The resolved Frontmatter schema validates the doc. The `1.1` schema accepts `schema_version` `1.0` or `1.1`, so choosing `version: '1.1'` (or leaving it unset) keeps every legacy `1.0` document valid.
2. For `doc_type: adr` docs, apply the ADR contract for `markdown.adr.version` (unset = frozen `1.0`) and check the **resolved Frontmatter contract** against that ADR version's supported-FM set. A custom (non-bundled) Frontmatter schema with `require_sections` is treated as compatible (the consumer owns it).
3. `python_tooling.version`, if present, is validated as a known registry value and otherwise ignored — **no output**, no pass/fail effect.

### Legacy & custom-schema compatibility

- **Legacy `schema_version: '1.0'`** stays valid under a no-version config: the default/`1.1` schema's enum includes `1.0`. This is the back-compat invariant, covered by tests (incl. `doc_type: adr` docs declaring `1.0`).
- **Custom schemas** (`--schema <path>` or a config `schema:` path) are unaffected by version selection — the consumer supplies their own contract. The registry and `frontmatter.version` apply only to **bundled** schemas.
- **Ambiguity guard:** a config setting both a custom `schema:` path and `frontmatter.version` is rejected (exit 2) rather than silently dropping one.

## Release & classification changes

`meta/versioning.md` is rewritten around the two planes:

- **Tool-plane classification table** — the existing CLI/workflow rows, plus explicit rows for _bundle_ changes (add contract version = MINOR; remove = MAJOR).
- **Contract-plane rule, per standard** — within a single standard's line the previously-passing rule applies: an additive field/value = MINOR; a stricter rule, removed enum value, or removed/renamed field = MAJOR. Each standard's line advances on its own cadence.
- **FM→ADR compatibility** documented as a first-class contract with the supported-set table.
- **Python Tooling** keeps the copy-adopted classification (impact-on-re-sync), now expressed as a `major.minor` contract-version line rather than an internal counter.

Each standard's README gains a small **version banner** (Frontmatter: its `schema_version` line; ADR: `ADR contract v1.0`; Python Tooling: `v1.0`, replacing `internal revision 1.6`).

## Invariants — consumer contract (must NOT change)

- The bundled schema's `$id`/path `src/project_standards/schemas/markdown-frontmatter.schema.json` (the `1.1` schema stays at this filename).
- Reusable workflow filenames; the `validate-frontmatter` console-script entry point; the package name `project_standards`.
- All published git tags (`v1.x`, the moving `v1`).
- **A config with no `version:` keys validates byte-identically to today** — same schema, same streams, same exit codes. Existing docs declaring `schema_version` `1.0` **or** `1.1` keep passing, including `doc_type: adr` docs.
- **`--schema` and custom config `schema:` paths behave exactly as today** — version selection applies only to bundled schemas.
- **Default stdout/stderr is unchanged** — `python_tooling.version` adds no output.

## Versioning classification of _this_ change

Introducing the scheme is **additive on the tool plane**: new _optional_ config keys, multi-version bundling, and a compatibility check that fires only on `adr.version`/`frontmatter.version` combinations no existing consumer configures today → no previously-passing repo newly fails → **MINOR** tool change. It nonetheless **ships inside the already-locked tool `2.0.0`** (whose MAJOR is the `requires-python` bump); it is not itself the reason for the major.

## Scope / non-goals

**In scope:** the two-plane model; validator multi-version registry + the documented schema/version precedence (incl. custom-schema bypass) + config selectors + FM→ADR compatibility check + `python_tooling.version` metadata (no default-output change); rewritten `meta/versioning.md`; per-standard README version banners; CHANGELOG entry; tests for the resolution algorithm, the compatibility check, and back-compat (no-`version` config).

**Non-goals (YAGNI):** per-standard git tags (Approach B); repo split (Approach C); Python Tooling enforcement; _authoring_ a Frontmatter 2.0 (build the machinery only — 2.0 content is a separate, later change); running the release ritual; any change to the schema `$id`/path or workflow filenames.

## Deliverables checklist

- [ ] `registry.json` + multi-version schema/contract bundle (1.1 schema unmoved).
- [ ] Validator: schema/version precedence + custom-schema bypass + both-set config error; FM→ADR compatibility enforcement; `python_tooling.version` validated as metadata (no default-output change).
- [ ] `.project-standards.yml` (this repo) + the adopt examples gain the optional `version:` keys; config docs updated.
- [ ] `meta/versioning.md` rewritten (two planes, version grammar, per-standard contract rules, compatibility table).
- [ ] README version banners on all three standards.
- [ ] Tests: schema/version precedence; `--schema` + custom `schema:` path; no-version config with `schema_version: '1.0'` (incl. `doc_type: adr`); explicit `frontmatter.version: '1.1'` on a `1.0` doc; valid vs incompatible ADR/FM combos; both-custom-and-version error; default-output unchanged.
- [ ] Build/install validation: the wheel / `uv tool install` includes `registry.json`, ADR contract JSON, and all bundled schema files.
- [ ] CHANGELOG entry (rides the tool `2.0.0`).

## Open questions

None blocking. One decision recorded for visibility: contract-version **grammar is `major.minor`** (Decision 8), for consistency with `schema_version`. If full `MAJOR.MINOR.PATCH` contract versions are later preferred for ADR / Python Tooling, that is a one-line change to the grammar and registry-key format.

## Audit history

- **Round 1 (2026-06-06)** — adversarial spec audit raised SA-001 (custom-schema / `--schema` precedence), SA-002 (legacy `schema_version: '1.0'` back-compat), SA-003 (headline example contradicted the compatibility matrix), SA-004 ("SemVer" vs two-part contract grammar), SA-005 (`python_tooling.version` output contract), plus ADR default-version and `standards_version` gaps. All resolved in this revision: schema/version precedence + custom bypass (Decision 5, Resolution algorithm); legacy `1.0` accepted by the `1.1` contract (matrix + Legacy & custom-schema compatibility); valid/guard examples (FM→ADR compatibility); `major.minor` grammar (Version grammar, Decision 8); metadata-only `python_tooling.version` (Decision 9); frozen ADR default (Decision 6); `standards_version` retained (Decision 10).
