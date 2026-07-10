# Adversarial Review — Agent Handoff Standard Package Specification

**Reviewer:** Claude Code (Fable 5) **Date:** 2026-07-09 **Target:** `docs/superpowers/specs/2026-07-09-agent-handoff-standard-package.md` (SPEC-DPEY, draft, Full profile) **Method:** Spec assertions cross-checked against ground truth — ADRs 0017–0021, the Standard Bundle Authoring contract (`standards/standard-bundle-authoring/README.md`), the manifest schema (`src/project_standards/standard_manifest.py`), the adopt engine (`src/project_standards/adopt/`), the live CLI (`src/project_standards/cli.py`), the repo's own `.project-standards.yml`, the project-spec Full template, and the live Codex/Claude Code hook documentation fetched today. Every 🔴 finding is reproduced empirically, not inferred.

## Verdict

**APPROVE AFTER REVISIONS.** The specification is architecturally sound, internally coherent, and unusually well-grounded: its external harness-contract claims check out against the live Codex documentation, its ADR attributions are accurate, its requirement-to-test traceability is complete (verified by script — all 24 FRs and 9 NFRs appear in §17.3, all FRs appear in the milestone summary, no dangling IDs), and its frontmatter passes the repo's own `spec validate`/`spec lint` gates. But it is not approvable as written: the §7.3 interface-requirements table is broken GFM that silently fails to render, IR-002's command set conflicts with the constrained `ProviderOperation` enum the repo froze two commits ago, and several load-bearing platform capabilities the spec treats as existing (per-standard CLI command groups, create-only artifact lifecycle, consumer-config unknown-key rejection) do not exist and are not called out as new work. Fix the two 🔴 items and decide the 🟡 items before MS-0 approval; otherwise the implementer discovers them mid-flight, which this repo's spec process exists to prevent.

What is **correct and verified** (so the approver can trust it):

- **Skill contract.** C-005/FR-006 (`.agents/skills/agent-handoff/`) matches ADR 0021 (`adr-0021…md:95,107`) exactly, and matches the live precedent set by commit `6634b9f`: `bundles/markdown-frontmatter/adopt.toml` installs to `.agents/skills/markdown-frontmatter/…` with `mode = "0755"` scripts and `canonical` source-owned provenance. The bundle-source path in §18.7 (`standards/agent-handoff/skills/agent-handoff/SKILL.md`) matches ADR 0021's prescribed layout.
- **Versioning.** Package version `1.0` and quoted `version: '1.0'` conform to ADR 0020's `major.minor` string shape; live precedent `standards/markdown-frontmatter/standard.toml` uses `supported = ["1.0", "1.1"]`.
- **Provenance vocabulary.** FR-018/C-006/DR-003 use ADR 0019's exact four-class model (`source-owned | generated | package-owned | external-owned`, `adopt/manifest.py:25-32`) and its parity-or-declared-transform proof obligations.
- **Exit codes.** IR-007's `0/1/2/3` matches the union of existing conventions: validators return 0/1/2 (`validate_frontmatter.py`, `standards_graph/cli.py:61`), and the adopt engine already uses `3` for the prerequisite class (`adopt/errors.py:24`).
- **Codex harness claims.** Verified against the live docs (the spec's URL 308-redirects; see L2): Codex supports project-local hooks in `.codex/config.toml` loaded only when the project layer is trusted, a `SessionStart` event with `source` values `startup|resume|clear|compact`, and context injection via stdout or `hookSpecificOutput.additionalContext`. The cited raw input schema exists and matches (seven required properties including `source` and `hook_event_name: "SessionStart"`). A-003, IR-005, and §18.1 hold today.
- **Spec hygiene.** `spec validate` OK, `spec lint` OK, `validate-frontmatter` OK, Prettier OK. Frontmatter key set exactly matches the Full template (the validator enforces exact-order key equality — `specs/commands/validate.py:47-51`). `SPEC-DPEY` matches `^SPEC-[0-9A-Z]{4}$` (`specs/registry.py:18`). The spec is indexed in `docs/handoff/specs-plans.md:22` as Appendix B.4 requires. All nine reference links resolve.
- **Net-new confirmation.** No `standards/agent-handoff/` exists; the spec correctly implies the graph gate consequence (adding the directory without a complete `standard.toml` fails `render-catalog`, which forces `require_all_manifests` — `standards_graph/cli.py:73`, `validators.py:57-72`), and MS-0's "add red package/graph/fixture tests" is the right entry move.

---

## 🔴 Critical — must fix before approval

### C1 · §7.3 interface-requirements table is malformed GFM and does not render as a table at all

The header row (line 259) has 5 cells; the delimiter row (line 260) has 6. Under the GFM spec, a delimiter row that does not match the header's cell count means the block is **not recognized as a table** — the whole of §7.3 renders as raw pipe text on GitHub and in any GFM renderer. This is also why the repo's own gates are silent: markdownlint's MD056 (enabled in `.markdownlint.json:63`) and Prettier's table formatter both skip the block because it never parses as a table. Reproduced with a cell-count scan:

```text
HEADER/DELIM MISMATCH at line 260: header=5 cells, delim=6 cells
ROW MISMATCH lines 262-268: 5 cells vs delim 6  (IR-002 … IR-008)
```

The root cause is IR-001 (line 261): its CLI synopsis contains a raw `|` in `(--harness {claude-code,codex}... | --manual)`. Backticks do **not** protect pipes inside GFM table cells, so that row genuinely has 6 cells — and the delimiter row was apparently widened to 6 to match it, breaking the header instead. The author knew the rule elsewhere: IR-003 (line 263) correctly escapes its pipe as `automatic\|manual`.

**Fix:** escape the IR-001 pipe (`… \| --manual`) and restore the delimiter row to 5 cells. Then confirm MD056/Prettier pass — after the fix the block becomes a real table, so the formatters will start seeing it for the first time.

### C2 · IR-002's command set cannot be declared under the just-frozen `ProviderOperation` enum

IR-002 exposes `project-standards agent-handoff {validate,drift-check,size-report,shape-check,legacy-report}`, and DR-001 requires the manifest to declare the standard's providers. But commit `ce11a54` ("constrain manifest provider operations") froze the operation vocabulary to exactly: `validate`, `fix`, `lint`, `drift-check`, `id-next`, `extract`, `render`, `scaffold`, `upgrade`, `semantic-review` (`standard_manifest.py:66-77`, enforced as a `StrEnum` on `ProviderBlock`). **`size-report`, `shape-check`, and `legacy-report` are not in it** — a `standard.toml` declaring them fails manifest validation, which fails the graph gate, which fails FR-001's own acceptance criterion. The mutation-capable adoption flow (IR-001 with `--harness`/`--manual`) likewise has no operation value.

The spec never resolves this. MS-0's "Freeze canonical naming, paths, config schema, provider operations, and CLI contracts" (line 803) gestures at it, but the Standard Bundle Authoring contract explicitly requires a **spec revision** to broaden the mode/operation vocabularies (`standard-bundle-authoring/README.md:100`) — so the decision belongs in _this_ document, not in an implementer's judgment call at MS-0.

**Fix (pick one and write it into §7.3/DR-001):** (a) extend `ProviderOperation` with the new operations as part of MS-0, recorded as a Standard Bundle Authoring revision/ADR; or (b) map the three reports onto existing operations (`size-report`/`shape-check` are arguably `validate` sub-modes; `legacy-report` is arguably `extract`) and keep IR-002 as pure CLI subcommands not declared as providers — in which case DR-001's provider list must say which operations _are_ declared.

---

## 🟡 Important — decide before or at MS-0 (soundness and scope-honesty gaps)

### M1 · Per-standard CLI command groups are new architecture, presented as if routine

The current CLI has no extension mechanism: `spec` and `standards` are hardcoded early-dispatch branches in `main()` (`cli.py:273-281`), `adopt` takes positional standard names with only `--dest/--force/--dry-run` — no `--harness`, `--manual`, or `--json` (`cli.py:295-321`), and providers declared in `standard.toml` are **metadata consumed by graph validation, not an execution dispatch** — nothing runs them. Additionally, `_ADOPTABLE_STANDARD_IDS` / `_VERSION_TRACKED_STANDARD_IDS` are hardcoded tuples with a parity guard that raises `RegistryError` when the bundle set disagrees (`cli.py:48-66,84-102`). So MS-2's "wire the specialized provider through the approved CLI surfaces" quietly includes: a new dispatch branch, new adopt flags, adopt-level `--json` (FR-024 depends on it), registry-tuple edits, and possibly a real provider runner. None of this is _wrong_ — a spec may specify new CLI — but the spec should name the delta so MS-2 is scoped honestly, the same way it already names the TOML/JSON-merge delta (R-002). **Fix:** add the CLI-platform delta to §8.5 Design Constraints or as a new risk row, and mention the registry parity guard in MS-1/MS-2.

### M2 · The create-only vs. standard-owned artifact lifecycle does not exist in the adopt engine

FR-005/FR-020/DR-003 rest on a per-artifact distinction between create-only consumer scaffolds (never overwritten) and standard-owned upgradeable artifacts (refreshed on upgrade). Today's `adopt.toml` model has three kinds (`file`, `workflow-caller`, `fragment` — `adopt/manifest.py:22`), a single `owner: bool`, and overwrite behavior governed by the CLI `--force` flag — no create-only mode, no upgrade lifecycle. This is the platform's biggest gap after C2 and it is nowhere flagged as new work. **Fix:** state explicitly (D-002 consequence or §8.5) that the artifact plane gains a create-only/owned lifecycle attribute, and decide whether that is an `adopt.toml` schema change (which touches ADR 0019's validation rules and every existing bundle's tests) or a provider-level behavior layered on top.

### M3 · §18.2's "Unknown keys fail configuration validation" is claimed, not specified — and contradicts current loader behavior

The consumer-config loader reads only known keys and silently ignores everything else (`validate_frontmatter.py:594-669`); nothing rejects unknown keys, and an `agent_handoff:` block added today would be ignored without error. `extra="forbid"` exists only in the _standard.toml_ manifest schema (`standard_manifest.py:79-82`) — a different file with a different owner. No FR requires consumer-config strictness, so §18.2's sentence has no traceability row and would be unverifiable at §17.3. **Fix:** either add it to FR-010/IR-003's acceptance criteria (making the new `agent_handoff` config parser strict for its own namespace — the realistic scope) or drop the sentence. Note the spec cannot honestly promise whole-file unknown-key rejection: that is the shared config's business, not this standard's.

### M4 · `.agents/hooks/` is an unprecedented location with no ADR backing

ADR 0021 blesses `.agents/skills/` for skills and prohibits global destinations, but says nothing about hooks; no contract anywhere establishes `.agents/hooks/`. The placement is safe under the artifact model (a contained `kind = "file"` dest) and consistent with ADR 0021's project-local rationale, but it is a new convention — and a deliberate departure from this repo's own current layout of per-harness copies (`.claude/hooks/session_start.py` + `.codex/hooks/session_start.py`), which is exactly the duplication D-003 argues against. That departure is the right call; it just needs the same treatment skills got. **Fix:** record a short ADR (or an ADR 0021 amendment) establishing `.agents/hooks/<standard-id>/` as the standard-owned hook location, and cite it from C-005's neighborhood so NG-001's "ADR 0021" attribution stops carrying more weight than the ADR's actual scope.

### M5 · The bundle's `adoption` mode is never pinned

DR-001 lists `adoption` among the manifest fields but no section states its value. The closed set is `validator | copy-adopt | cli | reference-only | none` (`standard_manifest.py:42-47`); `cli` is the obvious fit (same as project-spec: "enforced through a CLI command… may also seed repo-local support scaffolding"). Trivial to fix, but leaving it open invites an MS-1 guess on a field the graph validator gates on. **Fix:** one sentence in §8.3 or DR-001: `adoption = "cli"`.

### M6 · Appendix A promises `AW-`/`EC-`/`ERR-` IDs the body never assigns

Appendix A (lines 944-946) declares prefixes for alternate workflows (§10.2), edge cases (§10.3), and error-handling rows (§12.1), and closes with "Commits, plans, tests, review findings, and completion reports reference these IDs directly." But §10.2 uses unnumbered headings, §10.3 is an unnumbered bullet list, and §12.1's table has no ID column — the prefixes appear nowhere outside the appendix. The Full template _does_ assign them as table rows (`spec-full-template.md:317,323,374`), so this is a template deviation, not a template quirk: twelve edge cases and nine error rows are currently unreferenceable by any test or review finding. `spec lint` passes because it checks structure, not ID usage. **Fix:** either restore ID'd rows per the template (preferred — §10.3's edge cases are exactly what regression tests will cite) or delete the three prefixes from Appendix A.

---

## 🟢 Minor

| # | Location | Issue | Fix |
| --- | --- | --- | --- |
| L1 | FR-001 (line 218), §18.7 | `agent-summary.md` is framed as a bundle requirement; the bundle contract marks it Optional (`standard-bundle-authoring/README.md:27`). Shipping it is fine; requiring it overstates the contract. | Keep it in FR-001 but word it as a chosen deliverable, not a contract obligation. |
| L2 | References (lines 916-920) | Both `developers.openai.com/codex/*` URLs now 308-redirect to `learn.chatgpt.com/docs/*` (verified today). Content is intact; NFR-009's release-time recheck would catch it, but the spec is the pinned evidence trail. | Update the URLs (or note the redirect) so the citation matches what a release checklist will actually fetch. |
| L3 | WH-002 vs. §2.3 header | WH-005's "Revisit When" begins "Never through standard adoption…" inside the table headed "deferred — not never." Half of WH-005 is a non-goal (NG territory), half (a separately authorized operator workflow) is genuinely deferred. | Split it: move the "never through adoption" clause into NG-002's row or a new NG, keep the operator-workflow deferral as WH-005. |
| L4 | Frontmatter (line 2) | `SPEC-DPEY` is valid per `^SPEC-[0-9A-Z]{4}$` and matches the tool-minted base36 style, but every hand-authored sibling uses mnemonic IDs (`SPEC-MT01`, `SPEC-RD01`, `SPEC-MS01`, `SPEC-BA01`). Purely cosmetic; renaming after references exist costs more than it buys. | Leave it unless the owner wants mnemonic consistency now, before commits start citing it. |
| L5 | §18.2 (line 729) | `agent_handoff` is a valid single-segment config namespace (`standard_manifest.py:113-115`) but the spec never says the manifest must declare it in `[config].namespaces`, which the graph validator's namespace-collision rule consumes. | Add the namespace declaration to DR-001's field list. |

---

## Traceability and coherence — verified clean

Scripted cross-check results (no action needed, recorded for the approver):

- Every defined FR-001…FR-024 and NFR-001…NFR-009 appears in §17.3; nothing traced is undefined.
- The §19 milestone summary covers all 24 FRs; §4 goals reference only defined requirements.
- IR-003/FR-010/DR-004/§18.2 agree with each other on the automatic/manual mode rules (harness-list non-empty vs. empty).
- NFR-003's 2 KiB / 4 KiB caps are consistent across §10.1, §14, and §20 (4096 UTF-8 bytes).
- All nine References links resolve from the spec's directory.

## Suggested edit order before MS-0 approval

1. **C1** — fix the §7.3 table (escape IR-001's pipe, 5-cell delimiter row); rerun markdownlint/Prettier, which will now actually see the table.
2. **C2** — decide the provider-operation strategy (extend the enum via a Standard Bundle Authoring revision, or map onto `validate`/`extract` and scope IR-002 as CLI-only) and write it into §7.3/DR-001.
3. **M5** — pin `adoption = "cli"` (one line, unblocks MS-1 manifest authoring).
4. **M2 + M1** — add the artifact-lifecycle and CLI-platform deltas to §8.5/§15 so MS-2's scope is honest.
5. **M4** — draft the `.agents/hooks/` ADR (can land with MS-0's "record any required ADR updates").
6. **M3, M6, L1–L5** — batch with the same editing pass.

None of the findings challenge the spec's architecture: repository confinement, the shared-hook model, create-only knowledge, guide-plus-report migration, and the retirement gate are all well-reasoned and consistent with the platform's direction. The gaps are between the spec's assumed platform and the platform that exists on `testing` today — exactly the class of gap MS-0 exists to close, so close it there with these items named.
