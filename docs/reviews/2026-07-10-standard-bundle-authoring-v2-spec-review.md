# Review: Standard Bundle Authoring V2 Specification (SPEC-BA02)

**Spec:** `docs/superpowers/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (rev 0.1, draft, Full profile) **Review target state:** working tree after commit `e56db56` (spec is untracked; no other working-tree changes) **Workflow:** `docs/workflows/review-spec.md` **Reviewer:** session 2026-07-10

## Round 1

### Verdict

**APPROVE AFTER REVISION** — no blocking findings. Every external factual claim checked against the repository held: all 14 related ADRs, all 4 prior specs, and all reference paths exist; the §3.1 current-state inventory (9 bundles, 7 `adopt.toml` manifests, `registry.json` contract tracking) matches the tree; every constraint citation into SPEC-CP01 says what BA02 claims it says. Four 🟡 findings (one internal inconsistency, one traceability gap, one unverifiable count, one unacknowledged legacy incompatibility) and two 🟢 polish items.

### Method

- Read the spec end to end (1,091 lines), then verified claims live against the working tree at `e56db56` — file existence checks, greps into cited documents, enumeration of goal/traceability ID coverage, and the repository's own validation gate.
- Governing documents identified and read where cited: ADRs 0001–0024 (existence), ADR 0009/0013/0018/0023/0024 (content), SPEC-CP01 (cited FRs/NFRs), SPEC-BA01 README, the root-artifact ownership design, `meta/versioning.md`.

### Verified and held (do not re-check in later rounds unless ground truth moves)

- **Frontmatter and references.** All 14 `related.adrs` paths, all `prior_specs` (SPEC-BA01 = `2026-07-07-standard-bundle-authoring-standard.md`, SPEC-MT01 = `2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md`, SPEC-CP01, root-artifact design), and all §References paths exist. Frontmatter shape matches approved SPEC-CP01's. `uv run validate-frontmatter --config .project-standards.yml` passes (33 files).
- **§3.1 current state.** 9 bundle directories under `standards/`; exactly 7 `adopt.toml` files under `src/project_standards/bundles/`; `python-coding` is `adoption = "reference-only"`; `src/project_standards/schemas/registry.json` tracks per-standard consumer contract versions; runtime bundle mirror exists (`src/project_standards/bundles/agent-handoff/standard.toml`).
- **Constraint citations into SPEC-CP01.** C-001→FR-001/FR-002 (plain init enables no package), C-004→FR-035 (executor sole writer; `fix`/`scaffold`/`upgrade` return mutation plans), C-005→FR-016/FR-028 (offline), C-006→FR-036 (consumer-owned referenced extensions, `.standards/extensions/` preferred, no output overlap), C-007→NFR-007 (compatibility) — all verified verbatim.
- **ADR-backed vocabularies.** Family status enum (`draft`/`review`/`active`/`deprecated`/`archived`/`superseded`) matches ADR 0018; relationship taxonomy (independent default, companion/extends/conflicts/consumes_platform, no `requires`) matches ADR 0013; catalog-scoped channels match ADR 0024 and its ADR 0018 amendment note.
- **3,000-byte agent-summary limit** (FR-027) is grounded in the BA01 README ("targets at most 3,000 UTF-8 bytes") and all current `agent-summary.md` files are under it (max today: 2,720 bytes).
- **FR-013 adapter coverage** matches the root-artifact design's V5 surface matrix: whole-file, TOML tables/keys (`pyproject.toml`), JSON/JSONC keys + set entries + keyed sets (`.vscode/*`, `.claude/settings.json`), YAML mappings/keyed sets (workflows, hooks), EditorConfig section/property, delimiter-bounded Markdown blocks. No current destination lacks an adapter.
- **Runtime environment.** `requires-python = ">=3.14"` matches §18.1.
- **Internal ID coverage.** Operation vocabulary (12 ops) and the phase/effect mapping are mutually complete; §17.3 traceability covers FR-001–FR-034, NFR-001–NFR-009, IR-001–IR-007, DR-001–DR-008 with no gaps; catalog/payload/availability role-matching rules are consistent across FR-004, FR-022, §9, and AW-004.

### Findings

#### F1 🟡 — §9 provider example enumerates the wrong phase vocabulary

**Defect.** The `[[providers]]` example comments `phase = "plan" # plan | validate | verify | authoring`, omitting `inspect`. The normative phase table twelve lines later defines five phases (`plan`, `inspect`, `validate`, `verify`, `authoring`), and the closed operation mapping routes `id-next` and `extract` to `inspect/content`.

**Evidence.** Spec §9 "Providers and Migrations": example comment vs. the phase/effect table and the operation-mapping paragraph immediately following it.

**Fix.** Change the comment to `# plan | inspect | validate | verify | authoring`. Since §9 examples are the seed for the FR-031 templates, a wrong inline enum here propagates directly into authored payloads.

#### F2 🟡 — FR-009 is mapped to no goal

**Defect.** The union of §4 "Achieved By" ranges is FR-001–FR-008 and FR-010–FR-034; FR-009 (resource declarations: ID, role, path, media type, digest) is the only functional requirement that traces to no goal.

**Evidence.** Enumerated G-001 (FR-004–FR-008, FR-017–FR-020, FR-034), G-002 (FR-001–FR-003, FR-021–FR-023), G-003 (FR-010–FR-014), G-004 (FR-015–FR-016, FR-024–FR-026), G-005 (FR-027–FR-033).

**Fix.** Add FR-009 to G-001 (content-addressed resources are part of "every advertised package version a real immutable offline payload"). While editing that table, consider whether FR-026 (adoption guides) belongs under G-005's authoring gate rather than G-004's provider/migration bounds — the current placement is thematically wrong but harmless.

#### F3 🟡 — "11 planned for V5 launch" has no ground-truth source

**Defect.** §14 states "Package families: 9 current; 11 planned for V5 launch". The 9 verifies; the 11 appears nowhere else in the repository.

**Evidence.** Searched `docs/STATUS.md`, `docs/handoff/architecture.md`, SPEC-CP01, ADR 0023, ADR 0024 for a planned-family count — no match. The repo's own instructions define seven released/v5-staged plus two unreleased standards (nine total).

**Fix.** Either cite where the two additional families are planned (the root-artifact design mentions a future `project-toolbox` package — that is one, not two) or restate the row as "9 current" with the growth assumption carrying the scaling claim. A specific unverifiable count in a capacity table reads as authoritative and will be copied into the compatibility matrix scope.

#### F4 🟡 — New Markdown-block delimiter grammar silently orphans every deployed managed block

**Defect.** §9 fixes delimiters as derived from the block ID: `BEGIN project-standards:BLOCK_ID`. Every managed block deployed today uses a different marker text — `<!-- BEGIN agent-handoff managed instructions -->` in live consumer `CLAUDE.md` files and `# BEGIN agent-handoff managed codex hook` in `standards/agent-handoff/resources/integration/codex-session-start.toml`. The spec never acknowledges that pre-V2 delimiters exist: FR-030's legacy-input list (legacy `standard.toml`, `adopt.toml`, `registry.json`, YAML fragments, `_shared` files, package-specific locks) omits deployed block markers, and no EC or migration example covers delimiter recognition. The root-artifact design left the exact delimiter text open ("Delimiter-bounded Markdown; stable block ID"), so this spec is the first place the incompatibility becomes real.

**Evidence.** Spec §9 markdown-block paragraph; live `<!-- BEGIN agent-handoff managed instructions -->` block in this repo's own `CLAUDE.md`; `standards/agent-handoff/resources/integration/codex-session-start.toml:1`; FR-030's enumerated legacy inputs; design doc surface-matrix row for `AGENTS.md`.

**Fix.** State explicitly that pre-V2 delimiter formats are legacy signatures recognized by `legacy:STATE` migration declarations (and add them to FR-030's input list), or make the delimiter derivation compatible with the deployed format. Without this, an implementer reconstructing Agent Handoff under FR-029 has no sanctioned way to claim the existing blocks, and AW-005's compatibility matrix would fail on every migrated consumer.

#### F5 🟢 — Placeholder naming drift: `{catalog-major}` vs `{major}`

§2.1 and §8.2.2 write `catalogs/{catalog-major}.toml`; FR-022 and IR-004 write `catalogs/{major}.toml`. Same meaning; pick one token (suggest `{catalog-major}`, matching the glossary term) so template and schema generation don't produce two spellings.

#### F6 🟢 — §3.1 describes Standard Bundle Authoring's current mode with V2 vocabulary

§3.1 says "Standard Bundle Authoring is internal", but the current manifest says `adoption = "none"` (`standards/standard-bundle-authoring/standard.toml:11`). "Internal" is the V2 availability term FR-005 introduces; when describing current state, use the actual legacy value ("adoption `none`") to avoid implying the V2 enum already exists.

### Scope, testability, and consistency checks that passed without findings

- Every Must requirement's acceptance criterion names a concrete verification (fixtures, spies, parity tests, snapshots); DoD items map to §17.2/§17.3.
- No scope creep detected: all FRs trace to §1's stated contract; runtime behavior consistently deferred to SPEC-CP01 (NG-001 honored throughout — checked §12.3, §11, Appendix D).
- Non-goals/deferred items (NG-001–NG-005, WH-001–WH-004) are consistent with ADR 0023/0024 and SPEC-CP01's own non-goals.
- Open questions all answered and dated; Deviations Log present and empty; ID conventions in Appendix A match actual usage.
- The immutability model is coherent end to end: FR-020/FR-021 aggregate-digest algorithm (§9 Integrity) is non-self-referential and deterministic; FR-024/ERR-009/EC-011/§18.6 agree on baseline handling.

## Round 2

### Verdict

**APPROVE** — converged. Rev 0.2 (commit `2fc9df5`, "docs(v5): resolve bundle authoring spec review") resolves all six Round 1 findings; every fix was re-verified against ground truth, not accepted on assertion. No new 🔴 or 🟡 findings. Review target state: commit `2fc9df5`, clean working tree except this review file.

### Prior-finding verification

- **F1 (phase enum comment) — fixed.** Spec line 527 now reads `# plan | inspect | validate | verify | authoring`, matching the five-phase normative table and the `inspect/content` operation mappings.
- **F2 (FR-009 goal mapping) — fixed.** The §4 table was remapped: G-001 (FR-004–FR-009, FR-020–FR-021, FR-024, FR-034), G-002 (FR-001–FR-003, FR-022–FR-025), G-003 (FR-010–FR-014, FR-017), G-004 (FR-015–FR-019), G-005 (FR-026–FR-033). Re-enumerated the union: FR-001–FR-034 fully covered, no orphans. FR-017 and FR-024 now appear under two goals each — intentional multi-goal traceability, not a contradiction.
- **F3 (11-family count) — fixed and sourced.** §14 now cites `docs/TODO.md` for the two additional V5 deliverables. Verified: `project-toolbox` (TODO.md line 127) and `agent-managed-repo` (TODO.md line 131) are both tracked V5 release tasks; 9 current + 2 = 11. The relative link `../../TODO.md` resolves correctly from `docs/superpowers/specs/`.
- **F4 (legacy delimiters) — fixed substantively.** The revision adds a complete `[[legacy_signatures]]` contract (§9), extends FR-018 (migrations declare recognized signatures), FR-030 (deployed managed-block marker formats listed as migration inputs), EC-012 (unknown/modified block bodies block automatic migration and are never claimed from markers alone), AW-005, and the §17.2 migration test row. All three signature examples verified byte-for-byte against deployed reality: `<!-- BEGIN/END agent-handoff managed instructions -->` (live in `CLAUDE.md`, `AGENTS.md`, and the bundle resource `agent-instructions.md`), `# BEGIN/END agent-handoff managed codex hook` (`codex-session-start.toml`, installed to repo-relative `.codex/config.toml` per `adopt.toml:153`), and `# BEGIN/END agent-handoff managed config` (live at `.project-standards.yml:87`, resource `project-config.yml`). The declared targets match the actual install destinations, and the "marker presence alone never proves ownership" rule closes the ambiguous-block case Round 1 flagged.
- **F5 (placeholder drift) — fixed.** FR-022, IR-004, the component view, and OQ-003 all use `catalogs/{catalog-major}.toml`; grep confirms zero remaining `catalogs/{major}` occurrences.
- **F6 (§3.1 terminology) — fixed.** Current state now reads "legacy adoption `reference-only`" / "legacy adoption `none`", matching the actual `standard.toml` values.

### New-material checks (rev 0.2 additions)

- Revision row 0.2 added and status advanced `draft` → `review`; `uv run validate-frontmatter --config .project-standards.yml` passes (33 files).
- The `[[legacy_signatures]]` prose is internally consistent with the adapter section: legacy recognition is signature-data-only, forward state maps to typed V2 contributions, and the V2 delimiter derivation ("valid HTML comments") no longer implies it should match deployed markers.
- The `signatures` field appears as `[]` in one migration example and is absent in the other — read as optional-with-empty-default; the FR-032 generated schema will fix its exact optionality. Noted only for the template author; not a finding.

### Convergence

Round 2 produced no 🔴 findings and no new 🟡 findings. Per `docs/workflows/review-spec.md`, the review has **converged: APPROVE**. SPEC-BA02 rev 0.2 is ready for owner approval (MS-0 step 1).
