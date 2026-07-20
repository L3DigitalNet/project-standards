---
schema_version: '1.1'
id: 'reference-crrlk2-project-standards-drift'
title: 'Project Standards Consumer Documentation Drift Audit'
description: 'Claim-level audit of consumer-facing documentation against Project Standards 5.1.0 implementation behavior.'
doc_type: 'reference'
status: 'active'
created: '2026-07-20'
updated: '2026-07-20'
reviewed: '2026-07-20'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'documentation'
  - 'review'
  - 'validation'
aliases: []
related:
  - 'README.md'
  - 'UPGRADING.md'
  - 'docs/usage.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Standards Consumer Documentation Drift Audit

## Header

| Field           | Value                                                    |
| --------------- | -------------------------------------------------------- |
| Project         | Project Standards 5.1.0                                  |
| Repository      | `/home/chris/projects/project-standards`                 |
| Reviewed commit | `122ebec2515f342e5d55b73fd4b36c25156ee406`               |
| Reviewer        | Codex (GPT-5), high effort                               |
| Review date     | 2026-07-20                                               |
| Verification    | 14 findings after verifier pass; 4 pruned, 2 downgraded. |

## Executive Summary

The main installation and migration path is substantially aligned with the 5.1.0 implementation, but the release candidate still contains several adoption-affecting gaps. The highest-impact items are a false aggregate `validate --version` example, a removed `reconcile --recover` flag in the CLI package example, installed Markdown Frontmatter 1.3 guidance that identifies itself as 1.2, and an undocumented reusable-workflow interface. No Critical or High documentation drift was found; the remaining findings are narrow stale statements, option/default omissions, and reference defects. Two discrepancies are implementation bugs and are separated from the documentation remediation queue.

| Severity | Contradiction | Stale | Omission | Underspecified | Aspirational | Total |
| -------- | ------------: | ----: | -------: | -------------: | -----------: | ----: |
| Critical |             0 |     0 |        0 |              0 |            0 |     0 |
| High     |             0 |     0 |        0 |              0 |            0 |     0 |
| Medium   |             1 |     2 |        1 |              0 |            0 |     4 |
| Low      |             4 |     3 |        3 |              0 |            0 |    10 |

## Coverage Ledger

Every path in the declared consumer-document inventory was opened directly or matched byte-for-byte to an opened representative. `Deep` means the claims and relevant examples were checked individually; `Scanned` means the file was opened and its claims were checked through a byte-identical group, projection parity, or a focused surface scan. Internal maintainer references are included because they are maintained alongside consumer packages and could reasonably be followed by downstream package authors.

| Consumer-facing document or group | Depth | Notable gaps |
| --- | --- | --- |
| `README.md` | Deep | D-004 |
| `UPGRADING.md`, `CHANGELOG.md`, `meta/versioning.md` | Deep | No confirmed drift; 5.1.0 release-ready wording was treated as pre-tag staging. |
| `docs/usage.md` | Deep | D-001, D-013, D-014; two implementation bugs recorded separately. |
| `src/project_standards/README.md` | Deep | D-007; included as the public developer/extension reference. |
| `scripts/README.md`, `standards/README.md`, `standards/catalog.md` | Deep | No confirmed drift. |
| Installed CLI help for 7 console entry points and 41 root/leaf command paths | Deep | Observed against the exact-commit candidate wheel; D-001 and both Bugs Found entries were reproduced. |
| `standards/adr/**` (16 Markdown files) | Deep/Scanned | D-011. Five versioned example/template replicas were byte-identical to opened representatives. |
| `standards/agent-handoff/**` (60 Markdown files) | Deep/Scanned | Documentation matches intended behavior; current alias/help implementation defects are in Bugs Found. Forty template replicas were checked through byte-identical groups. |
| `standards/cli-documentation/**` (21 Markdown files) | Deep/Scanned | D-002, D-010. Versioned examples, research notes, and templates were checked through byte-identical groups where applicable. The 1.2 prerelease cadence wording is accurate at the reviewed pre-tag commit. |
| `standards/markdown-frontmatter/**` (52 Markdown files) | Deep/Scanned | D-003. Twenty-six example/resource/template replicas were byte-identical to opened representatives. |
| `standards/markdown-tooling/**` (6 Markdown files) | Deep | D-008. |
| `standards/project-spec/**` (24 Markdown files) | Deep/Scanned | D-009. Versioned tooling notes, examples, and templates were checked through byte-identical groups where applicable. Prerelease wording is accurate at the reviewed commit; the illustrative `#slug` is correctly code-formatted, not a rendered link. |
| `standards/python-coding/**` (4 Markdown files) | Deep | D-012; reference-only but externally readable. |
| `standards/python-tooling/**` (8 Markdown files) | Deep | D-005, D-006. |
| `standards/standard-bundle-authoring/**` (8 Markdown files) | Scanned | No new finding; the mutable family page already records the 2.0 SPEC-BA02 pointer correction. Internal maintainer surface, included conservatively. |
| `src/project_standards/bundles/**` (19 legacy-bundle Markdown files) | Scanned | Frozen V1 compatibility evidence; no projection/content mismatch. |
| `src/project_standards/families/**` (9 installed family Markdown indexes) | Scanned | All are relative symlinks resolving to canonical `standards/**` files. |
| `src/project_standards/payloads/**` (135 installed payload Markdown files) | Scanned | All are relative symlinks resolving to canonical `standards/**` files; D-003 remains a canonical-source defect. |
| `.standards/packages/markdown-frontmatter/agent-summary.md`, `.agents/skills/markdown-frontmatter/SKILL.md` | Deep | Installed managed outputs reproduce D-003. |

The reverse code-to-documentation pass ran across all CLI parser/dispatch definitions, user-visible errors and warnings, selected-package schemas and provider defaults, 4 reusable workflow `workflow_call` interfaces, 6 pre-commit hooks, Catalog 5 roles/defaults, and all 350 tracked family/payload projection entries. Projection mismatches: 0.

## Severity and Drift-type Rubric

Severity follows the requested consumer-impact bar:

- **Critical:** documentation actively leads a consumer into a broken or destructive action, such as data loss or an incorrect security step.
- **High:** documented behavior contradicts actual behavior on a common path, such as a wrong flag, default, or exit code.
- **Medium:** stale or omitted behavior has a workaround or a narrow trigger.
- **Low:** a minor wording problem, example defect, or cosmetic omission that still creates real drift.

Confidence is **High**, **Medium**, or **Low** according to whether the discrepancy is real and correctly attributed to documentation rather than implementation.

Drift types are:

- **Contradiction:** documentation says one thing and implementation does another.
- **Stale:** documentation describes removed or changed behavior.
- **Omission:** real consumer behavior is undocumented.
- **Underspecified:** documentation implies behavior but leaves it ambiguous.
- **Aspirational:** documentation describes behavior that is not implemented.

## Findings

### D-001 — Correct the aggregate `validate --version` exit behavior

- **Drift type:** Contradiction · **Severity:** Medium · **Confidence:** High
- **Doc location** (`docs/usage.md:824`): "For example, `validate --version` forwards the flag to the validators and exits 0, while `render --version`, generic `adopt --version`, `spec --version`, and `standards --version` are usage errors and exit 2."
- **Code location** (`src/project_standards/frontmatter_commands.py:51-59`, `_parser`): `validate` registers `files`, `--config`, `--schema`, `--glob`, `--quiet`, and `--no-require-frontmatter`; it does not register `--version`. The exact-commit installed command printed `error: unrecognized arguments: --version` and exited `2`.
- **Discrepancy:** the usage reference promises a successful compatibility path that the aggregate parser rejects. A script using the documented placement receives an operator-error exit instead of version output.
- **Fix:** in `docs/usage.md:824`, replace the quoted example sentence with: "For example, `validate --version` and `fix --version` are usage errors and exit 2; the standalone validator and formatter scripts accept their own `--version` flags. `render --version`, generic `adopt --version`, `spec --version`, and `standards --version` are also usage errors and exit 2." Keep the final "Put `--version` first" instruction.
- **Verification:** with the candidate wheel first on `PYTHONPATH`, run `project-standards validate --version` and `project-standards fix --version`; both must exit `2`, and `project-standards --version` must exit `0`.
- **Effort:** S

### D-002 — Replace the removed `reconcile --recover` option in CLI examples

- **Drift type:** Stale · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/cli-documentation/examples/usage.example.md:42`, `standards/cli-documentation/versions/1.1/examples/usage.example.md:42`, `standards/cli-documentation/versions/1.2/examples/usage.example.md:42`): `project-standards reconcile [--check | --apply | --recover]`
- **Code location** (`src/project_standards/control_plane/cli.py:82-97`, `_parser`): `parser.add_argument("--repair-state", action="store_true", help="plan or explicitly apply sanctioned incomplete-state recovery")`; no `--recover` option is registered.
- **Discrepancy:** the worked example teaches an option removed from the V5 control plane. Consumers copying it receive an argparse exit `2` instead of a recovery plan.
- **Fix:** change line 42 in the mutable `standards/cli-documentation/examples/usage.example.md` and unpublished 1.2 copy to `project-standards reconcile [--check | --apply] [--allow-major <standard>@<major>]... [--repair-state] [--repo <dir>] [--json]`. Do not modify released 1.1 bytes; add this exact sentence under a new `## Released-version errata` section in `standards/cli-documentation/README.md`: "The immutable 1.1 usage example names the removed `reconcile --recover` option; use `reconcile --repair-state` with an explicit `--apply` when applying sanctioned incomplete-state recovery." Refresh 1.2 payload/resource digests, its family digest, catalog digest, and generated projections after changing the release candidate.
- **Verification:** compare the corrected synopsis with installed `project-standards reconcile --help`, then run package, graph, catalog-render, and projection checks.
- **Effort:** M

### D-003 — Make installed Markdown Frontmatter 1.3 guidance identify version 1.3

- **Drift type:** Stale · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/markdown-frontmatter/versions/1.3/artifacts/agent-summary.md:3-5,34-36`): "The canonical [Markdown Frontmatter 1.2 standard](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/markdown-frontmatter/versions/1.2/README.md) is authoritative"; "Lifecycle: active. Package: `markdown-frontmatter@1.2`."; and the canonical-resource link targets `versions/1.2`. `standards/markdown-frontmatter/versions/1.3/skills/markdown-frontmatter/SKILL.md:84-86,170-176` likewise says "`markdown-frontmatter@1.2`" and links the 1.2 adoption guide and schema. The mutable `standards/markdown-frontmatter/skills/markdown-frontmatter/SKILL.md:84-86,170-176` repeats the same claims.
- **Code location** (`standards/markdown-frontmatter/versions/1.3/payload.toml:3-6,228-240`): the payload declares `version = "1.3"` and installs those two files as managed artifacts at `.standards/packages/markdown-frontmatter/agent-summary.md` and `.agents/skills/markdown-frontmatter/SKILL.md`. `standards/markdown-frontmatter/versions/1.3/agent-summary.md:3-5` correctly states `Package: markdown-frontmatter@1.3`.
- **Discrepancy:** the default 1.3 package installs agent-facing documentation that claims 1.2 authority and routes consumers to retained 1.2 resources. This obscures the selected payload and its 1.3 behavior changes.
- **Fix:** because 1.3 first appeared after tag `v5.0.2` and remains part of the unpublished 5.1.0 release candidate, correct it in place before publication. In both 1.3 managed sources and the mutable current skill, replace `Markdown Frontmatter 1.2` with `Markdown Frontmatter 1.3`, `markdown-frontmatter@1.2` with `markdown-frontmatter@1.3`, and every `/versions/1.2/` target with `/versions/1.3/`. Preserve released 1.2 files. Regenerate the dogfood outputs and update the affected payload/resource/family/catalog/lock digests through reconciliation.
- **Verification:** run `rg -n 'markdown-frontmatter@1\.2|versions/1\.2|Frontmatter 1\.2' standards/markdown-frontmatter/versions/1.3/{artifacts,skills} standards/markdown-frontmatter/skills`; it must return no stale identity/link. Reconcile into a temporary consumer and assert both installed artifacts identify 1.3, then run package, graph, catalog-render, schema, and projection checks.
- **Effort:** M

### D-004 — Publish the complete reusable-workflow input contract

- **Drift type:** Omission · **Severity:** Medium · **Confidence:** High
- **Doc location** (`README.md:174-178`): "Reference reusable workflows by **major tag** (`@v5`), never `@main`. For an immutable pin, use a full version (`@v5.1.0`) or a commit SHA." No complete table in `README.md`, `docs/usage.md`, or the active package docs enumerates the callable inputs and defaults.
- **Code location** (`.github/workflows/lint-markdown.yml:33-49`): `markdownlint=true`, `globs="**/*.md"`, `config=""`; (`.github/workflows/validate-markdown-frontmatter.yml:4-10`): `standards-ref="v5"`; (`.github/workflows/validate-specs.yml:17-28`): `standards-ref="v5"`, `strict-lint=true`; (`.github/workflows/format.yml:14-30`): `prettier=true`, `globs="."`, `exclusions=""`.
- **Discrepancy:** direct workflow callers are told how to pin a workflow but not how to discover all inputs, defaults, or the requirement that `standards-ref` match the `uses` ref. A caller can unknowingly install code from a different ref, enable strict spec lint, or miss the caller-config override.
- **Fix:** directly after `README.md:178`, add `#### Reusable workflow inputs` and a table with one row per workflow/input: `lint-markdown.yml` (`markdownlint`, boolean, `true`; `globs`, string, `**/*.md`; `config`, string, empty, auto-discovers caller `.markdownlint.json`), `format.yml` (`prettier`, boolean, `true`; `globs`, string, `.`; `exclusions`, string, empty), `validate-markdown-frontmatter.yml` (`standards-ref`, string, `v5`), and `validate-specs.yml` (`standards-ref`, string, `v5`; `strict-lint`, boolean, `true`). Immediately below, state: "For either validation workflow, set `standards-ref` to the same ref used after `@` in `jobs.<job>.uses`; a full-version or SHA pin must be repeated exactly." Add one minimal YAML caller example for each of the four workflows showing `uses` and any non-obvious `with` value.
- **Verification:** parse `on.workflow_call.inputs` from all four YAML files and compare every documented input, type, and default; run Markdown link/format/lint checks.
- **Effort:** M

### D-005 — Document Python Tooling coverage and workflow-ownership controls

- **Drift type:** Omission · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/python-tooling/README.md:7-9`, `standards/python-tooling/versions/1.1/adopt.md:13-50`): the family page calls the adoption guide "complete options," but its explicit TOML has no `workflow_ownership` key or `[standards.python-tooling.config.coverage]` table.
- **Code location** (`standards/python-tooling/versions/1.1/config.schema.json:79-91,115-118,132-150`): the closed schema exposes `coverage.parallel` (default `false`), `coverage.patch` (default `[]`, only `"subprocess"`), and `workflow_ownership` (default `"managed"`), and requires `parallel = true` when `patch` is non-empty. `standards/python-tooling/versions/1.1/providers/python_tooling.py:91-95,152-159,194-215,350-367` shows the Coverage 7.10 dependency floor for patching, rendered coverage settings, changed erase/run/combine/report sequence, and defaults. The canonical `standards/python-tooling/versions/1.1/README.md:36-38` already documents both `workflow_ownership` values.
- **Discrepancy:** the guide advertised as the complete option reference omits advanced coverage controls and leaves workflow ownership out of its copyable example, even though the canonical README explains ownership. Consumers can still discover ownership elsewhere, which limits the impact, but the adoption path is incomplete.
- **Fix:** immediately expand `standards/python-tooling/adopt.md:15` to name `coverage.parallel`, `coverage.patch`, and `workflow_ownership`. Because 1.1 was included in `v5.0.2`, publish the durable correction in a successor `python-tooling@1.2` copied from 1.1. In its explicit TOML, add `workflow_ownership = "managed"` after `additional_dev_dependencies = []` and add after the pytest block: `[standards.python-tooling.config.coverage]`, `parallel = false`, `patch = []`. Add this prose: "Set `coverage.parallel = true` to collect parallel data and combine it before reporting. `coverage.patch` accepts only `\"subprocess\"`; a non-empty list requires `parallel = true`, enables coverage.py subprocess startup patching, and selects `coverage[toml]>=7.10.0`. `workflow_ownership = \"managed\"` lets the package own `.github/workflows/check.yml`; `\"consumer-owned\"` leaves that path outside reconciliation, verification, and lock state." Route the family page to 1.2 and refresh package/catalog integrity metadata.
- **Verification:** compare every top-level and nested selected-schema property with the successor adoption guide, validate its TOML example against the schema, render default, parallel, subprocess, and consumer-owned variants, and run package/graph/schema/catalog/projection checks.
- **Effort:** M

### D-006 — Mark the unversioned Python build-backend guide as historical

- **Drift type:** Stale · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/python-tooling/build-backend.md:1-5,51-55,96-104`): the current-looking guide says it uses "this repository as the worked example," shows `project_standards-3.0.0` artifacts, says "This repo is configured exactly as above," and runs `project-standards@v4 validate-frontmatter --config .project-standards.yml`.
- **Code location** (`pyproject.toml:1-8`; `standards/python-tooling/README.md:3-8,33-35`; `standards/python-tooling/versions/1.1/build-backend.md:1-12`): the project is version 5.1.0 on Python 3.14+, the versioned 1.1 guidance is current, and the family page classifies unversioned copy-adopt material as migration evidence.
- **Discrepancy:** a reader entering the unversioned guide directly is given V3 artifact names, a V4 install, and legacy YAML authority without a historical warning.
- **Fix:** immediately after the title in `standards/python-tooling/build-backend.md`, add this exact banner:

  ```markdown
  > **Historical V4 mechanism reference.** This unversioned file is migration evidence only. For the current package contract, use [Build Backend Guidance for `python-tooling@1.1`](versions/1.1/build-backend.md). Commands and artifact versions below describe the former V3/V4 delivery path and are not current adoption instructions.
  ```

  Replace "This repo is configured exactly as above" at line 98 with "This repository formerly used the following V4 invocation; it is retained only to illustrate the build-backend mechanism." Leave the historical command and artifact names intact under that banner.

- **Verification:** `rg -n '3\.0\.0|@v4|\.project-standards\.yml' standards/python-tooling/build-backend.md` must show every match within explicitly historical context; run Markdown format/lint/link checks.
- **Effort:** S

### D-007 — Point the developer guide to Standard Bundle Authoring 2.2

- **Drift type:** Stale · **Severity:** Low · **Confidence:** High
- **Doc location** (`src/project_standards/README.md:345-347`): "Follow the active internal [Standard Bundle Authoring 2.0 workflow](../../standards/standard-bundle-authoring/versions/2.0/README.md#author-workflow)."
- **Code location** (`standards/standard-bundle-authoring/standard.toml:19-22`; `standards/standard-bundle-authoring/README.md:1-8`): version 2.2 is indexed and the family page states, "Version 2.2 is the current authority for this repository."
- **Discrepancy:** maintainers extending the public package catalog are routed to a superseded internal authoring contract and can miss 2.2's consumer-runtime and artifact-mode requirements.
- **Fix:** in `src/project_standards/README.md:347`, change the link text to `Standard Bundle Authoring 2.2 workflow` and its target to `../../standards/standard-bundle-authoring/versions/2.2/README.md#author-workflow`.
- **Verification:** open the corrected link and confirm it resolves to the 2.2 `Author workflow` heading; run Markdown link checks.
- **Effort:** S

### D-008 — Add `workflow_mode` and its default to Markdown Tooling options

- **Drift type:** Omission · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/markdown-tooling/versions/1.2/README.md:61-74`; `standards/markdown-tooling/versions/1.2/adopt.md:7-10`): the README says, "The closed package schema provides these options," but the table omits `workflow_mode`; the adoption guide names `caller` and `self-hosted` without stating the default.
- **Code location** (`standards/markdown-tooling/versions/1.2/config.schema.json:5-9`): `"workflow_mode": { "enum": ["caller", "self-hosted"], "default": "caller" }`.
- **Discrepancy:** consumers treating the canonical table as complete cannot discover the self-hosted delivery selector or determine that omitted configuration uses the reusable-workflow caller.
- **Fix:** because 1.2 was included in `v5.0.2`, publish the correction in successor `markdown-tooling@1.3`. Add after `contract_version` in its README options table: `| workflow_mode | caller | Uses published @v5 reusable workflows; set self-hosted to install immutable in-repository workflow endpoints. |`, with code formatting around the option, values, and tag. In its adoption guide, change the option sentence to end with "The default is `caller`." Route the mutable family page to 1.3 and refresh integrity/catalog/projection metadata. Until 1.3 is published, add the same default sentence to mutable `standards/markdown-tooling/adopt.md`.
- **Verification:** compare every successor schema property/default with the README table and adoption guide, then run package, graph, schema, catalog, projection, and Markdown checks.
- **Effort:** M

### D-009 — Correct the Project Specification option count

- **Drift type:** Contradiction · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/project-spec/versions/1.1/adopt.md:16,74`; `standards/project-spec/versions/1.2/adopt.md:16,74`): both guides say "five closed options."
- **Code location** (`standards/project-spec/versions/1.2/config.schema.json:5-26`): the schema defines six properties: `contract_version`, `workflow_mode`, `include_patterns`, `reference_prefixes`, `default_profile`, and `ci`.
- **Discrepancy:** the guide's count contradicts the six options it then shows, making the configuration inventory and migration description internally inconsistent.
- **Fix:** in unpublished `standards/project-spec/versions/1.2/adopt.md:16,74`, replace `five closed options` with `six closed options`. Preserve released 1.1; under `standards/project-spec/README.md`'s release-status correction, add: "The immutable 1.1 adoption guide counts five closed options; its example and schema define six." Refresh 1.2 resource/payload/family/catalog/projection digests.
- **Verification:** count the schema's six top-level properties and confirm both corrected 1.2 sentences say six; run package, graph, catalog, and projection checks.
- **Effort:** S

### D-010 — Point CLI research notes at the versioned standard

- **Drift type:** Stale · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/cli-documentation/resources/research-notes.md:3,28,32,34,47-50,72,87,96`): the rationale repeatedly links numbered standard sections as `../README.md#...`, including `../README.md#15-source-register` and `../README.md#9-ci-drift-prevention`.
- **Code location** (`standards/cli-documentation/README.md:1-33`; `standards/cli-documentation/versions/1.2/README.md:149-373`): the mutable family page has only Current authority, Use, Adopt, Release-status correction, and Legacy boundary headings; the numbered sections and source register are in the versioned 1.2 README.
- **Discrepancy:** eleven rationale-to-standard links target anchors absent from the family landing page, so readers cannot navigate from the research claim to its governing rule.
- **Fix:** in `standards/cli-documentation/resources/research-notes.md`, change the bare standard target on line 3 to `../versions/1.2/README.md` and every `../README.md#...` target to `../versions/1.2/README.md#...`. Do not change the current-file anchors.
- **Verification:** run a local Markdown link/anchor checker and confirm each changed target resolves in `versions/1.2/README.md`.
- **Effort:** S

### D-011 — Correct the ADR standard's dogfood claim

- **Drift type:** Contradiction · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/adr/versions/1.1/README.md:136-143`): "This standards repository documents the convention but does not itself host a `docs/adr/` tree."
- **Code location** (`docs/adr/README.md:1-20`): the tracked managed ADR index has active frontmatter and relates to `standards/adr/versions/1.1/README.md`; `git ls-files docs/adr` returns the index, template, and ADRs 0001 through 0024.
- **Discrepancy:** the canonical released ADR package misstates the repository's visible dogfood layout.
- **Fix:** do not alter released 1.1. Add under a new `## Released-version errata` section in mutable `standards/adr/README.md`: "The immutable 1.1 README incorrectly says this repository has no `docs/adr/` tree. The repository already dogfooded the convention in `docs/adr/` when 1.1 was published; retain the released payload bytes but treat that sentence as a known factual error." In the next ADR payload, replace the parenthetical with: "The project-standards repository also dogfoods this convention in its own `docs/adr/` tree."
- **Verification:** run `git ls-files docs/adr`, re-read the mutable erratum, and ensure the next payload contains no `does not itself host` claim.
- **Effort:** S

### D-012 — Point Python Coding's tree diagram at the versioned standard

- **Drift type:** Contradiction · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/python-coding/versions/0.5/README.md:1258-1265`): the diagram labels `standards/python-coding/README.md` as "this document," followed by "The canonical standard remains this document."
- **Code location** (`standards/python-coding/README.md:3-8,21-23`; `standards/python-coding/versions/0.5/payload.toml:24-29`): the family root is mutable navigation, while the versioned payload's own `README.md` is the canonical-standard resource.
- **Discrepancy:** the versioned canonical document points readers to a different mutable file while claiming that path is itself, obscuring which bytes are authoritative.
- **Fix:** preserve released 0.5. Add a `## Released-version errata` section to mutable `standards/python-coding/README.md` stating: "The immutable 0.5 tree diagram labels the mutable family `README.md` as `this document`; the authoritative path is `standards/python-coding/versions/0.5/README.md`." In successor 0.6, make the diagram's second path `standards/python-coding/versions/0.6/README.md` and retain "this document, reference-only."
- **Verification:** compare the corrected displayed path with the successor payload's `canonical-standard` resource path; run package, graph, catalog, and Markdown checks.
- **Effort:** S

### D-013 — Document `PYTHON_COLORS`, `TERM=dumb`, and color precedence

- **Drift type:** Omission · **Severity:** Low · **Confidence:** High
- **Doc location** (`docs/usage.md:619-625`): the Environment section lists only `NO_COLOR`, `FORCE_COLOR`, and `COLUMNS`, then says, "The tool reads no color state of its own beyond this."
- **Code location** (`pyproject.toml:3,8`; `src/project_standards/cli.py:558-559`): Project Standards 5.1.0 requires Python 3.14 and uses the standard Python 3.14 `argparse.ArgumentParser` color behavior. Python 3.14's [controlling-color contract](https://docs.python.org/3/using/cmdline.html#controlling-color) states that `TERM=dumb` disables color and `PYTHON_COLORS` controls Python-only color with precedence over `NO_COLOR`, which precedes `FORCE_COLOR`. Exact-commit probes confirmed `PYTHON_COLORS=0` disables, `PYTHON_COLORS=1` enables, and `TERM=dumb` disables help color.
- **Discrepancy:** consumers cannot predict help output when standard Python color variables are present, and the current list implies it is complete. This can make help snapshots and CI logs vary unexpectedly.
- **Fix:** in `docs/usage.md` Environment, add: "`PYTHON_COLORS` — Python-specific override: `1` enables and `0` disables help color; it takes precedence over `NO_COLOR` and `FORCE_COLOR`." Add: "`TERM=dumb` — Disables help color unless overridden by `FORCE_COLOR` or `PYTHON_COLORS=1`." After the list, add: "Color precedence is `PYTHON_COLORS` > `NO_COLOR` > `FORCE_COLOR` > `TERM`. These variables are interpreted by Python 3.14 `argparse`; Project Standards adds no separate color configuration."
- **Verification:** with the candidate wheel, inspect ANSI escapes from `env -u NO_COLOR PYTHON_COLORS=0 project-standards --help`, `PYTHON_COLORS=1`, `TERM=dumb`, and conflicting variables; compare with the documented precedence.
- **Effort:** S

### D-014 — Correct empty `NO_COLOR` semantics

- **Drift type:** Contradiction · **Severity:** Low · **Confidence:** High
- **Doc location** (`docs/usage.md:621`): "`NO_COLOR` — When set (to any value), disables ANSI color in `--help` output."
- **Code location** (`src/project_standards/cli.py:558-559`): default Python 3.14 `argparse` owns color handling. On the exact-commit installed command, `NO_COLOR=1 FORCE_COLOR=1 project-standards --help` emitted no ANSI escapes, while `NO_COLOR= FORCE_COLOR=1 project-standards --help` emitted ANSI escapes.
- **Discrepancy:** the phrase "to any value" says an explicitly empty variable disables color, but an empty value is treated as unset. Shell users who export an empty placeholder can receive colored output contrary to the reference.
- **Fix:** in `docs/usage.md:621`, replace "When set (to any value)" with "When set to a non-empty value". Keep the precedence wording added by D-013 adjacent to this entry.
- **Verification:** compare ANSI output for `NO_COLOR=1 FORCE_COLOR=1` and `NO_COLOR= FORCE_COLOR=1` against the corrected sentence.
- **Effort:** S

## Remediation Plan

Work top-to-bottom; details and exact edits remain in each finding.

1. **Phase 1 — Medium release/adoption drift:** D-001, D-002, D-003, D-004.
2. **Phase 2 — Low current-reference corrections:** D-005, D-006, D-007, D-009, D-010, D-013, D-014.
3. **Phase 3 — Low successor-package and released-history errata:** D-008, D-011, D-012.

## Bugs Found

### Agent Handoff policy-view aliases can be overridden

- **Documentation intent** (`docs/usage.md:242,273-286`): "`validate` additionally accepts **`--view {full,size,shape}`** (default: `full`); `size-report` and `shape-check` are convenience entry points for its `size` and `shape` views." The two alias synopses expose only `--repo` and `--json`.
- **Implementation** (`src/project_standards/agent_handoff/cli.py:49-55,140-148,398-428`): `_COMMANDS` prefixes the aliases with `("--view", "size")` or `("--view", "shape")`; `_parse_v2` registers public `--view` for every `VALIDATE` operation; caller arguments are appended after the prefix.
- **Observed vs. intended:** installed `size-report --view shape --json` emitted `AH-SHAPE`, and `shape-check --view size --json` emitted `AH-SIZE-CAP`; both help surfaces advertise `--view`. The documented aliases are intended to select their named fixed view. This is an implementation defect, so the documentation should not be changed to bless the override.
- **Implementation fix:** refactor alias dispatch so the fixed `size`/`shape` selection is internal rather than a parseable argument prefix. Register public `--view` only for command `validate`; reject caller-supplied `--view` on both aliases with exit `2`, while still supplying the fixed view to selected-package and legacy-fallback providers.
- **Verification:** add selected-package and fallback tests asserting alias help omits `--view`, cross-view attempts exit `2`, `size-report` emits only `AH-SIZE-CAP` findings, `shape-check` emits only `AH-SHAPE` findings, and `validate --view` retains all three choices.

### Specialized Agent Handoff adoption help is unreachable

- **Documentation intent** (`docs/usage.md:201-214`): `project-standards adopt agent-handoff` supports `--manual`, repeatable `--harness {claude-code | codex}`, and `--json` in addition to shared adoption options.
- **Implementation** (`src/project_standards/cli.py:365-387,578-604`): any `adopt ... --help` bypasses `_parse_early_adopt`, so argparse renders only the generic parser containing `STANDARD`, `--dest`, `--force`, and `--dry-run`.
- **Observed vs. intended:** exact-commit installed `project-standards adopt agent-handoff --help` exited `0` but omitted all three specialized options. The long-form documentation matches the specialized runtime parser; help routing, not documentation, must be corrected separately.
- **Implementation fix:** before generic `adopt --help` handling and V5 mutation routing, recognize `adopt agent-handoff ... --help` and render the specialized Agent Handoff adoption parser without executing adoption. Keep bare/generic `adopt --help` on the generic parser.
- **Verification:** add installed-command help tests asserting `adopt agent-handoff --help` exits `0` and lists `--manual`, `--harness {claude-code,codex}`, and `--json`, while generic `adopt --help` remains unchanged and neither help invocation writes files.

## Open Questions

None. Package publication status was resolved from git history: Markdown Frontmatter 1.3, CLI Documentation 1.2, and Project Specification 1.2 first appeared after `v5.0.2` and remain correctable 5.1.0 release candidates; already-tagged payloads are left immutable and receive mutable errata or successor-package instructions.
