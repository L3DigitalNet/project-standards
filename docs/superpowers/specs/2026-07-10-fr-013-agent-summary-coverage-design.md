# FR-013 Agent Summary Coverage Design

**Date:** 2026-07-10 **Status:** owner-approved in principle; written review pending **Author:** session 2026-07-10

## Goal

Close SPEC-MT01 FR-013 with compact, discoverable agent summaries for all nine manifested standards. Preserve each canonical `README.md` as the normative source, and make every summary useful to future MCP resource consumers without beginning MCP server implementation.

## Current state

The repository has nine `standards/*/standard.toml` manifests: eight active standards and the draft, reference-only Python Coding standard.

- Agent Handoff already declares `agent_summary = "agent-summary.md"`; its summary is 2,367 UTF-8 bytes.
- Python Coding records a rationale for reading its canonical README directly.
- ADR, CLI Documentation, Markdown Frontmatter, Markdown Tooling, Project Specification, Python Tooling, and Standard Bundle Authoring provide neither a summary nor an omission rationale.

The SPEC-MT01 traceability row therefore reports FR-013 as a failing, non-blocking `Should` gap. The owner has approved treating it as a v5 release blocker and using strict nine-of-nine summary coverage rather than exceptions.

## Decisions

### Coverage

Every current standard, regardless of lifecycle or adoption mode, will provide `standards/<id>/agent-summary.md` and declare it as `resources.agent_summary` in `standard.toml`.

The Python Coding rationale will be replaced by an actual summary even though the package remains draft and reference-only. Standard Bundle Authoring will also provide a summary even though it is internal and non-adoptable. This satisfies the stronger ADR 0009 decision as well as FR-013's minimum acceptance wording.

### Authority and content

Each summary is a reviewed companion, never a normative replacement. It must:

- identify the standard's purpose, lifecycle status, and adoption mode;
- state when an agent should load it;
- capture the standard's core rules and invariants without adding new requirements;
- list relevant commands, artifacts, or validation gates;
- identify boundaries and companion relationships;
- link to the canonical `README.md` and relevant adoption or supporting documents; and
- state that the canonical README wins if the summary conflicts with it.

Summaries will use the same compact section order:

1. scope and authority notice;
2. when to use;
3. core rules;
4. commands or artifacts, when applicable;
5. boundaries and companions; and
6. canonical resources.

### Size contract

The Standard Bundle Authoring Standard will document a 3,000 UTF-8 byte target for `agent-summary.md`. All nine current summaries must meet the target; this implementation will not use exceptions.

The limit is deterministic, keeps the summaries token-cheap, and accommodates the existing 2,367-byte Agent Handoff summary. A future standard that cannot meet the target must record its exception and rationale in the canonical README, as required by SPEC-MT01 NFR-005.

### Resource and packaging model

Each canonical manifest will add:

```toml
[resources]
agent_summary = "agent-summary.md"
```

Graph validation will enforce path existence and bundle containment. The generated catalog will expose each summary as `standards://<id>/agent_summary`.

Summaries will not be added to packaged `adopt.toml` artifact manifests. They are standard-package resources for discovery and context loading, not files installed into consumer repositories. No consumer configuration, adoption behavior, registry default, reusable workflow, or MCP server code changes.

Agent Handoff's runtime `standard.toml` mirror already declares its summary and remains byte-identical to the canonical manifest.

### Package versioning

Adding or materially revising a discoverable package resource is an additive standard-package change under ADR 0020. Every current package will advance its package `latest` minor while retaining the previous value in `supported`:

| Standard                  | Package version change |
| ------------------------- | ---------------------- |
| ADR                       | `1.0` → `1.1`          |
| Agent Handoff             | `1.0` → `1.1`          |
| CLI Documentation         | `1.0` → `1.1`          |
| Markdown Frontmatter      | `1.1` → `1.2`          |
| Markdown Tooling          | `1.1` → `1.2`          |
| Project Specification     | `1.0` → `1.1`          |
| Python Coding             | `0.4` → `0.5`          |
| Python Tooling            | `1.0` → `1.1`          |
| Standard Bundle Authoring | `1.0` → `1.1`          |

Agent Handoff's summary will gain the common canonical-authority notice and structure, so its package version advances with the other eight. Consumer-selectable registry defaults remain unchanged because the summaries do not alter normative contracts or consumer behavior.

## Enforcement

A real-manifest regression test will derive every standard from `standards/*/standard.toml` and assert:

- `resources.agent_summary` exists;
- the declared file exists within the bundle;
- the summary is at most 3,000 UTF-8 bytes;
- the summary links to `README.md`; and
- the summary contains the canonical-authority notice.

Existing manifest and graph tests continue to own resource syntax, safe containment, and missing-path failures. The new test owns this repository's strict nine-of-nine readiness policy without making the generic open resource mapping conditional on lifecycle or adoption mode.

The summaries also receive a manual semantic review against their canonical documents. The review checks that no summary introduces a rule, drops a load-bearing boundary, or weakens `MUST`/`SHOULD` language.

## Generated and traceability updates

After the summaries and manifests exist:

- regenerate `standards/catalog.md`;
- update Standard Bundle Authoring's anatomy, example, checklist, and template guidance;
- record the additive package-resource changes in CHANGELOG `[Unreleased]`;
- update the SPEC-MT01 FR-013 traceability row to `Passing` only after verification;
- update current status and the compact session record; and
- keep Step 07 as the next development step.

## Verification

The implementation must pass:

```bash
uv run pytest tests/test_standard_manifest.py tests/test_standards_graph_catalog.py -q
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run project-standards standards render-catalog --root . --check
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
uv run python scripts/check.py
uv run pytest tests/coherence -v
```

Agent Handoff validation and drift-check remain part of closeout. Concurrent owner-authored `docs/TODO.md` work must be preserved and must not be staged with this implementation.

## Acceptance criteria

- Nine of nine manifested standards declare an existing `agent_summary` resource.
- Nine of nine summaries meet the 3,000-byte target and link to their canonical README.
- Semantic review finds no contradiction or weakened normative rule.
- The catalog exposes nine `standards://<id>/agent_summary` resources.
- FR-013 is `Passing`, with committed test and catalog evidence.
- No future-standard draft is promoted, no consumer artifact is added, and no MCP server code begins.
