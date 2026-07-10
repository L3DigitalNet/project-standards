# Review: FR-013 Agent Summary Coverage Design

**Spec:** `docs/superpowers/specs/2026-07-10-fr-013-agent-summary-coverage-design.md` **Review target state:** commit `65d6394` (spec as committed; working tree clean for spec content) **Workflow:** `docs/workflows/review-spec.md` **Reviewer:** session 2026-07-10

## Round 1

### Verdict

**APPROVE AFTER REVISION** — no blocking findings; two 🟡 completeness gaps in the "Generated and traceability updates" list would cause avoidable fix-up commits, and one 🟢 verification-list omission.

### Method

Every factual claim was verified live against the repository, not from memory or the spec's own citations: manifest inventory and fields, byte counts, ADR texts, SPEC-MT01 requirement/traceability rows, CLI flags (`--help` output), test and script paths, byte-identity of the runtime mirror, and current test-suite state.

### Verified and held (do not re-check in later rounds)

- Nine `standards/*/standard.toml` manifests exist; eight `status = "active"`, Python Coding `status = "draft"` / `adoption = "reference-only"` — matches "Current state".
- Only `agent-handoff` declares `agent_summary = "agent-summary.md"` (`standards/agent-handoff/standard.toml:39`); the summary is exactly 2,367 UTF-8 bytes.
- Python Coding's rationale exists as claimed — `standards/python-coding/README.md:1265` ("No compact agent summary or separate rationale file exists today … agents … read this document directly").
- SPEC-MT01 FR-013 row (line 292) and acceptance wording ("provide `agent-summary.md` or explain why not", priority `Should`); traceability row (line 825) reports "Failing — non-blocking `Should` gap"; NFR-005 (line 311) requires a documented size target or recorded exception. All match the spec's characterization.
- ADR 0009 (accepted): summaries are reviewed companions, never replacements — the spec's authority model conforms.
- ADR 0020 (accepted): additive package-surface change → advance `latest`, retain prior values in `supported`; consumer contract versions are a separate plane. The spec's versioning table matches every manifest's current `latest` exactly (adr 1.0, agent-handoff 1.0, cli-documentation 1.0, markdown-frontmatter 1.1, markdown-tooling 1.1, project-spec 1.0, python-coding 0.4, python-tooling 1.0, standard-bundle-authoring 1.0), and the "registry defaults unchanged" claim is consistent with the plane split (`src/project_standards/registry.py` defaults are contract versions retained in `supported`).
- Runtime mirror `src/project_standards/bundles/agent-handoff/standard.toml` is byte-identical to the canonical manifest (verified with `cmp`).
- Catalog already exposes `standards://agent-handoff/agent_summary` (`standards/catalog.md:60`); the manifest schema accepts the `agent_summary` resource key (`tests/test_standard_manifest.py:182`).
- All referenced verification paths and commands exist: both pytest files, `scripts/check.py`, `tests/coherence/`, `standards validate-graph --root/--require-all-manifests`, `standards render-catalog --root/--check`, `spec validate`, `spec lint`. CHANGELOG has an `[Unreleased]` section.
- Adopt manifests live only under `src/project_standards/bundles/*/adopt.toml` — "summaries not added to `adopt.toml`" is coherent with the packaging model.
- The five test failures reported in stale session state do not reproduce: 318 tests in the affected files pass on the current tree.
- Internal consistency: Decisions, Enforcement, and Acceptance criteria agree (nine-of-nine, 3,000-byte target, README link, authority notice, no MCP/consumer changes). Scope is clean — every section traces to closing FR-013.

### Findings

#### 🟡 F1 — Agent Handoff bundle re-sync is missing from the updates list

**Defect.** The spec changes both canonical Agent Handoff files: `standard.toml` (`[versions]` 1.0 → 1.1) and `agent-summary.md` (gains the common authority notice and section structure). The runtime bundle `src/project_standards/bundles/agent-handoff/` carries copies of both, and `tests/test_adopt_dogfood.py::test_dogfoodable_templates_match_repo_root_byte_for_byte` (mapping at line 54) asserts byte-for-byte parity for `agent-summary.md`; the spec itself requires the manifest mirror to remain byte-identical. Yet the "Generated and traceability updates" list never instructs re-syncing the bundle copies — the spec mentions the mirror only as a present-tense current-state fact.

**Evidence.** `ls src/project_standards/bundles/agent-handoff/` shows `standard.toml` and `agent-summary.md`; the dogfood parity test reads both byte-for-byte; `cmp` confirms the manifests are identical today, which the planned edits will break until re-synced.

**Fix.** Add an explicit step to "Generated and traceability updates": re-sync `src/project_standards/bundles/agent-handoff/standard.toml` and `.../agent-summary.md` byte-for-byte after the canonical edits.

#### 🟡 F2 — Python Coding canonical README update is not enumerated

**Defect.** The Decisions section says the Python Coding rationale "will be replaced by an actual summary," but the rationale lives inside the canonical README (`standards/python-coding/README.md:1265`: "No compact agent summary or separate rationale file exists today…"). The "Generated and traceability updates" list does not include editing that passage. If missed, the canonical README asserts no summary exists while `standard.toml` declares one — precisely the canonical/summary contradiction the spec's own manual semantic review is defined to reject.

**Evidence.** `grep` of `standards/python-coding/README.md` lines 1265–1270; the updates list (spec lines 103–110) covers catalog, Standard Bundle Authoring docs, CHANGELOG, traceability, status, and session record — but not this README.

**Fix.** Add "revise the Python Coding README agent-summary passage (§ around line 1265) to reference the new summary" to the updates list.

#### 🟢 F3 — Verification list omits the repo frontmatter gate

**Defect.** The repository non-negotiable `uv run validate-frontmatter --config .project-standards.yml` is absent from the Verification command list, and `scripts/check.py` does not run it (its `COMMANDS` are ruff format/check, basedpyright, coverage pytest, coverage report, pip-audit). New summaries under `standards/` are outside frontmatter scope (ADR 0015), so the gate will almost certainly pass — but the spec's verification list presents itself as the complete pass gate.

**Fix.** Append `uv run validate-frontmatter --config .project-standards.yml` to the Verification block.
