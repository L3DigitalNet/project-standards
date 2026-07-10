# Review: Root-Artifact Ownership and Semantic Composition Design

**Spec:** `docs/superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md` **Review target state:** commit `3a79bff` (`docs(v5): design semantic artifact composition`; working tree clean) **Workflow:** `docs/workflows/review-spec.md` **Reviewer:** session 2026-07-10

## Round 1

### Verdict

**APPROVE AFTER REVISION** — no blocking findings. Every factual claim about current package manifests, integrations, shared payloads, ADRs, and SPEC-CP01 requirement IDs verified against ground truth. Four 🟡 findings: an internal ambiguity between the `preserve` and `conflict` classifications for locally modified owned units, an undefined migration disposition for previously installed v4 whole-file payloads, a missing formatting-stability requirement for Markdown-block normalization, and an undefined "canonical package and scope order." Two 🟢 polish items.

### Method

The design (all 324 lines) was read end to end before recording findings. Every factual claim was then verified live against the repository, not from memory or the design's own citations: all seven bundle `adopt.toml` manifests, the `_shared` payloads, the Agent Handoff integration modules (`instructions.py`, `claude.py`, `codex.py`), the CLI Documentation authority declarations, ADR 0004/0013 texts, SPEC-CP01 FR-010/FR-021/FR-031/EC-005 rows, and the repo validation gate (`uv run validate-frontmatter --config .project-standards.yml` → 31 files pass). The design carries no frontmatter, matching the two sibling owner-approved design documents (`2026-07-10-fr-013-...-design.md`, `2026-07-10-pre-step-07-...-design.md`), so no convention violation.

### Verified and held (do not re-check in later rounds)

- **Problem-statement conflicts are all real.** Python Tooling installs whole `AGENTS.md`, `CLAUDE.md`, `.vscode/settings.json`, and `.vscode/tasks.json` files (`src/project_standards/bundles/python-tooling/adopt.toml`, `kind = "file"`, `provenance = "package-owned"`); its `pyproject.toml` artifact is `kind = "fragment"` (reported, not applied — the report-only fragment path was verified in code during the SPEC-CP01 review: `adopt/engine.py:314-321`). Agent Handoff contributes a bounded `AGENTS.md` fragment (`bundles/agent-handoff/adopt.toml`) and adds `CLAUDE.md` as an instruction target for the Claude harness (`agent_handoff/integrations/instructions.py:25`), maintaining one marked block via `replace_marked_block`.
- Both Python Tooling and Markdown Tooling reference the identical shared payloads `_shared/editorconfig` and `_shared/vscode-extensions.json` (`shared =` entries in both `adopt.toml` files); both payload files exist under `src/project_standards/bundles/_shared/`.
- Agent Handoff's Claude and Codex integrations are semantic: `claude.py` merges only its managed `SessionStart` hook group into `.claude/settings.json` (raising `IntegrationConflictError` on malformed structure rather than rewriting), and `codex.py` maintains a bounded marker block in `.codex/config.toml` — consistent with "semantically updates … while preserving unrelated harness configuration."
- Exclusive whole-file examples all match manifests: `.python-version`, `scripts/check.py`, and `check.yml` are `owner = true` Python Tooling artifacts; `.markdownlint.json` and `.prettierrc.json` are Markdown Tooling's; every current workflow caller has a distinct filename (`check.yml`, `lint-markdown.yml`, `format.yml`, `cli-docs-check.yml`, `validate-specs.yml`, `validate-standards.yml`).
- CLI Documentation's README claim holds exactly: `standards/cli-documentation/standard.toml` declares `target = "README.md"` with `mutates = false` (read-only command-reference authority) and `docs/usage.md` with `mutates = true` — matching both the surface-table README row and "validation authority does not grant write access."
- Agent Handoff's package-specific provenance lock exists (`runtime/provenance-lock.json` → `.agents/agent-handoff/manifest.json`, last artifact in its `adopt.toml`), supporting the "retire the package-specific provenance lock" migration bullet.
- SPEC-CP01 citations are accurate: FR-010 (line 251) governs removal preserving modified/ambiguous content; FR-021 (line 262) retires `.project-standards.yml` after migration; SPEC-BA02 is the planned successor contract per FR-031 (line 272). ADR 0004 and ADR 0013 exist and say what the design attributes to them; ADR 0023 does not exist yet, consistent with the design being its prerequisite input.
- The `.project-standards.yml` fragment inventory behind "Other current packages" holds: `adr`, `cli-documentation`, `agent-handoff`, and `project-spec` carry fragments targeting it; `markdown-frontmatter` owns it whole-file.
- Every current artifact destination is covered: named surface-table rows plus the generic whole-file categories (installed skills under `.agents/skills/**`, hooks, `docs/adr/adr.template.md` as a unique template, the provenance lock via the migration section).
- "Standard-library `tomllib` alone is insufficient because it cannot write TOML" — correct; `tomllib` is read-only.
- External consistency spot-checks passed: the shared-unit last-reference removal rule matches FR-010's "reference counting" verification; the whole-plan conflict-blocking stance matches SPEC-CP01's Conflicted state and EC-005; the no-force-flag rule matches SPEC-CP01 §safety ("Do not overwrite or delete modified, shared, create-only, consumer-owned, or ambiguously owned content").
- Repo gate: `uv run validate-frontmatter --config .project-standards.yml` → 31 files validated.

### Findings

#### F1 🟡 A locally modified owned unit maps to two different classifications with no assignment rule

- **Defect:** Step 7 of the composition algorithm defines `preserve` and `conflict` as distinct classifications. The preservation rules say "A locally modified owned unit blocks update or removal and remains in place" (line 124) — which reads as preserve-and-continue — while the error-behavior section lists "modified managed unit" as a stable conflict class (line 244) and the composition suite requires "any conflict blocks the complete plan before the first write" (line 266). As written, the same state (modified owned unit whose payload wants an update) is simultaneously a per-unit preservation and a plan-wide blocker, and nothing says which units ever receive the `preserve` classification. SPEC-CP01 leans both ways too (FR-010 "preserve … modified … content" on successful reconciliation vs. the Conflicted state including "modified managed files"), so the design — which owns the ownership/lifecycle semantics — is the right place to state the rule.
- **Evidence:** Design lines 104-106 (classification set), 124, 244, 266; SPEC-CP01 FR-010 (line 251), EC-005 (line 655), Conflicted state (line 677).
- **Fix:** Add one explicit rule, e.g.: a modified owned unit whose selected payload desires no change classifies `preserve` (or `no-op`); a modified owned unit whose payload desires an update or removal classifies `conflict` and blocks the complete plan. State the blocking scope (whole plan, per SPEC-CP01's Conflicted state) in the preservation-rules section, not only in the verification suite.

#### F2 🟡 Migration disposition of previously installed v4 whole-file payloads is undefined, producing silent duplication

- **Defect:** The Python Tooling migration says "Split Python Tooling's whole file into a `python-tooling` block," but no rule states how the reconciler recognizes a v4-installed whole `AGENTS.md`/`CLAUDE.md` (no central lock exists today, and only Agent Handoff has a package provenance lock). Under the stated preservation rules the outcome is silently wrong rather than blocked: the pre-existing v4 file body sits outside any declared scope, so the consumer acquires ownership of the entire legacy payload text; the new bounded block is a "missing semantic unit [that] may be inserted" — no conflict fires, and the consumer permanently keeps a stale full-file copy of the old instructions alongside the new managed block. SPEC-CP01 FR-021 anticipates "recognized installed artifacts," but this design owns "current-package migration decisions" (Included scope) and never defines recognition or cleanup for this case, and the migration suite fixtures (lines 271-278) cover "combined consumer and package blocks" — a state that only exists _after_ this migration — not the v4 whole-file starting state.
- **Evidence:** `bundles/python-tooling/adopt.toml` whole-file `AGENTS.md`/`CLAUDE.md` artifacts; design lines 114-116 (insertion + adopt-equal rules), 41-45 (consumer owns undeclared units), 153-154 (split dispositions), 271-278 (fixture list); SPEC-CP01 FR-021.
- **Fix:** Add a migration decision: recognition of legacy whole-file payloads (e.g., content-addressed comparison against known v4 release payloads) yields a reviewed replace/cleanup action; unrecognized pre-existing content classifies consumer-owned as today. Add a migration fixture: repository with a byte-identical v4 Python Tooling `AGENTS.md` migrates to the bounded block without retaining the legacy body.

#### F3 🟡 No requirement or fixture guarantees Markdown-block normalization survives the sanctioned formatting authority

- **Defect:** The design permits an explicitly requested formatting operation (Markdown Tooling's Prettier authority covers `AGENTS.md` and `CLAUDE.md` — they are Markdown) to change physical bytes "within its declared authority" provided "it must preserve normalized values" (line 146). But Prettier rewraps text, changes emphasis and list markers, and reflows content _inside_ delimiter-bounded blocks; whether normalized values survive depends entirely on the Markdown-block adapter defining a formatting-insensitive normalization, which no adapter requirement states. If normalization is byte- or near-byte-based, every format run manufactures semantic-unit drift on every instruction block, contradicting line 146. Neither the adapter suites (line 254) nor the composition suites (lines 259-267) include a format-then-reconcile fixture.
- **Evidence:** Design lines 134-146 (adapter contract + formatting-authority paragraph), 254, 259-267; Markdown Tooling's formatting authority over `*.md` (its `format.yml` caller, `bundles/markdown-tooling/adopt.toml`).
- **Fix:** Add an adapter-contract bullet: block-content normalization must be stable under the repository's declared formatting authorities (or managed blocks must be excluded from formatting). Add a fixture requirement: run the sanctioned formatter over a container holding managed blocks, then reconcile — every owned unit must classify `no-op`.

#### F4 🟡 "Canonical package and scope order" and physical placement of new units are undefined

- **Defect:** Step 8 applies contributions "in canonical package and scope order," but no section defines that order, and nothing states where a new semantic unit is physically inserted into a consumer-owned container (end of file? after the last managed block? adapter-specific anchor?). The verification contract requires input-order independence of final bytes (line 264), so implementers must invent a deterministic order and placement — divergent inventions mean fixture rework. The phrase also superficially collides with "There is no precedence rule between standards" (line 25) and the acceptance criterion "no package-order or precedence rule exists" (line 321); the design never says the canonical order affects only physical placement, never value resolution.
- **Evidence:** Design lines 105 (step 8), 25, 264, 321; the Deferred list (lines 299-305) does not assign this to SPEC-BA02 or SPEC-CP01.
- **Fix:** Define the canonical order (e.g., lexicographic package ID, then normalized scope), state per-adapter placement expectations for newly inserted units, and add one sentence that canonical ordering governs deterministic physical placement only and never resolves value conflicts.

#### F5 🟢 Composition algorithm normalizes desired units before the providers that render them run

- **Defect:** Step 4 normalizes "every current, desired, and previously applied semantic unit," but desired values may come from "a static payload source or deterministic read-only render provider" (line 65), and providers are invoked in step 5. As numbered, desired units from render providers cannot be normalized in step 4.
- **Evidence:** Design lines 101-102 (steps 4-5), 65.
- **Fix:** Swap steps 4 and 5, or split step 4 into pre-provider (current/previously applied) and post-provider (desired) normalization.

#### F6 🟢 The shared-baseline rule does not decide the general-vs-package split for the current `.editorconfig`, and the split is not listed as deferred

- **Defect:** The policy says "general EditorConfig properties may use shared identities, while Python, Markdown, TOML, or YAML-specific properties belong to the package that requires them," but the current shared payload's `[*]` section sets `indent_style = tab` / `indent_size = 2`, which the payload's own header comment attributes to Prettier output — a Markdown Tooling motivation living in the "general" section. Whether that property is a shared identity or Markdown Tooling's is exactly the kind of assignment the acceptance criterion asks the owner to confirm, yet neither the design nor its Deferred list assigns the per-property enumeration anywhere.
- **Evidence:** `src/project_standards/bundles/_shared/editorconfig` (header comment and `[*]` section); design lines 171-182, 299-305, 324.
- **Fix:** Either enumerate the shared-vs-package assignment for the current payload's properties in the shared-baseline section, or add a Deferred bullet assigning the enumeration to the package-migration payloads under SPEC-BA02.

## Round 2

**Review target state:** commit `b229602` (`docs(v5): resolve semantic composition review`; working tree contains only this untracked review file)

### Verdict

**APPROVE** — converged. The revision resolves all six Round 1 findings; no 🔴 findings and no new 🟡 findings this round. One 🟢 completeness nit against an explicitly non-exhaustive list. The design is ready to feed ADR 0023, `SPEC-BA02`, and the control-plane implementation plan.

### Method

Diffed the design between `3a79bff` and `b229602` (all changes fall inside the six finding areas plus the status header), verified each fix against the revised text rather than accepting the commit message, re-checked the new sections for internal consistency and against SPEC-CP01 (FR-010, EC-005, Conflicted state), and re-ran the repo gate (`uv run validate-frontmatter --config .project-standards.yml` → 31 files pass). Round 1 ground-truth verifications were not re-checked; no manifest, integration, or ADR ground truth moved between the two commits.

### Prior findings verified fixed

- **F1 — fixed.** The Applied-content rules now open with an explicit assignment rule for `preserve` ("applies only when the current transition intentionally lacks mutation authority, such as unrelated consumer content, create-only content after creation, or a shared unit retained for another owner") and replace the ambiguous sentence with a single unambiguous rule: any owned unit whose normalized live value differs from its recorded value classifies `conflict`, remains untouched, and blocks the complete plan, regardless of whether the payload would keep, update, or remove it. The blocking scope is now stated where the rule lives. This strict stance is consistent with SPEC-CP01's Conflicted state ("modified managed files" as blocking findings) and EC-005 ("Report conflict; neither overwrite nor delete"); FR-010's "preserve … modified … content" is satisfied because the unit is left untouched. The adapter suite fixture list also gained a `preserve` fixture, matching the new classification rule.
- **F2 — fixed.** A new "Legacy whole-file recognition" section defines offline, versioned digest/structural signatures for known v4 payloads with four exhaustive dispositions: byte-identical match → reviewed replacement that removes the legacy body and installs the bounded units; structural match with different digest → conflict with **no block inserted** (directly closing the silent-duplication hole); no signature → consumer-owned with normal insertion; legacy signature coexisting with a current managed block → cleanup conflict. Migration fixtures now cover byte-identical v4 `AGENTS.md`/`CLAUDE.md`/VS Code files, byte-identical v4 shared EditorConfig/extension files decomposing without duplication, and structurally recognized but modified v4 files blocking without duplicate blocks.
- **F3 — fixed.** The adapter contract gained: "make Markdown-block normalization stable under every declared physical formatter, without erasing semantic distinctions such as code fences, links, or heading levels; otherwise require and validate formatter exclusion for the block." The adapter suites now require running every sanctioned formatter over a managed container and reconciling to `no-op`, or proving the formatter exclusion effective. The fallback is implementable (Prettier supports ignore ranges), so the requirement is not vacuous.
- **F4 — fixed.** A new "Deterministic ordering and placement" section defines canonical contribution order (bytewise lexicographic standard ID, then normalized semantic scope; shared identity substitutes for standard ID on shared units), states it "controls deterministic physical placement only; it never chooses a value, suppresses a conflict, or grants precedence," and gives per-adapter placement rules for TOML/JSON/YAML mappings, set-like entries, Markdown blocks, and EditorConfig sections. The composition suite gained a matching proof obligation ("canonical ordering changes placement only and never resolves a conflicting value"). The tension with the no-precedence acceptance criterion is resolved explicitly.
- **F5 — fixed.** Steps 4 and 5 are swapped: providers are invoked (with output-bounds validation, a bonus tightening) before normalization, and step 5 now normalizes "current, rendered desired, and previously applied" units.
- **F6 — fixed.** The Deferred list gained: "Exact per-property and per-extension ownership plus shared identities for the current `_shared` payloads, assigned by the package-migration payloads under `SPEC-BA02`."

### New findings

#### F7 🟢 The two new legacy-recognition conflict types are absent from the stable conflict-class enumeration

- **Defect:** The Legacy whole-file recognition section introduces two conflicts — ambiguous local modification of a structurally recognized v4 file, and the legacy-signature-plus-managed-block cleanup conflict — but the Error behavior list of stable conflict classes was not extended. The list is explicitly non-exhaustive ("include"), so this is polish, but the enumeration is the natural seed for stable conflict codes in SPEC-CP01/SPEC-BA02, and omitting the migration classes there invites divergent naming later.
- **Evidence:** Revised design "Legacy whole-file recognition" bullets 2 and 4 versus the unchanged conflict-class list in "Error behavior."
- **Fix:** Append "ambiguous legacy payload modification" and "unresolved legacy cleanup" (or equivalent names) to the stable conflict-class list.

### Convergence

Round 2 produced no 🔴 and no new 🟡 findings. Converged verdict: **APPROVE** (F7 is optional polish and does not gate ADR/spec work).
