# Adversarial Review — Agent Handoff Standard Package Implementation Plan

**Reviewer:** Claude Code (Fable 5) **Date:** 2026-07-09 **Target:** `docs/superpowers/plans/2026-07-09-agent-handoff-standard-package.md` (committed at `909bd05`) **Basis:** `SPEC-DPEY` rev 0.3 (approved), accepted ADR 0022, ADRs 0017–0021, the round-2 spec review (`docs/reviews/2026-07-09-agent-handoff-spec-review.md`) **Method:** every platform claim in the plan checked against the live code on `testing` (manifest/engine/CLI/registry/validators/tests), every legacy-source claim checked against the pinned commit `56b24df` in `/home/chris/projects/agent-handoff-v3`, and the Claude Code hooks contract re-fetched live today from the plan's own cited URL.

## Verdict

**READY TO EXECUTE AFTER FIXES.** The plan is unusually well-grounded: its platform-delta claims match the code exactly, its task ordering respects the spec's milestone dependencies, every task follows the TDD RED→GREEN→commit discipline, and its hardest external claims — the Claude Code hook-entry shape — check out against the live documentation fetched today. But two items must be fixed before an executor starts: Task 13's verification command contradicts the hook behavior Task 13 itself specifies (it will either fail or silently verify a mis-rooted degraded path), and the plan's installed-path root-derivation design deviates from the approved spec's §10.1 workflow without a Deviations Log entry — in a change-controlled spec process, that deviation must be recorded or reconciled _before_ Task 13's tests bake it in. Five 🟡 items close smaller soundness and completeness gaps; none challenge the architecture.

What is **correct and verified** (so the executor can trust it):

- **Provider-operation strategy.** The plan's Global Constraints ("the manifest operation enum stays unchanged") and Task 11's command→operation mapping (`size-report`/`shape-check` → `validate`, `legacy-report` → `extract`, `upgrade` → `upgrade`) exactly implement spec D-009/IR-002. All five declared operations exist in the frozen `ProviderOperation` StrEnum (`standard_manifest.py:66-76`, including `DRIFT_CHECK = "drift-check"`). No enum expansion is claimed anywhere.
- **Platform-delta honesty.** Everything the round-1 spec review forced into §8.5 as named new work is a named plan task: `InstallPolicy` does not exist today (grep-confirmed) → Task 1 creates it; no executable provider dispatch exists → Task 3; no hook validation exists in `standards_graph/validators.py` (no "hook" match in the file) → Task 2; the adopt parser lacks `--harness`/`--manual`/`--json` → Task 11. Nothing is presented as already existing that isn't.
- **Exit-code plumbing.** Task 3's plan to wrap boundary failures as `ManifestError` (exit 3) and reject missing operations as `UsageError` (exit 2) matches the existing exception model exactly (`adopt/errors.py`: `UsageError.exit_code = 2`, `ManifestError.exit_code = 3`; CLI catches `AdoptError` and returns `exc.exit_code` at `cli.py:337-339`).
- **CLI integration points.** `_contract_version()` (`cli.py:34`), `_ADOPTABLE_STANDARD_IDS` (`cli.py:48`), `_VERSION_TRACKED_STANDARD_IDS` (`cli.py:59`), and the early-dispatch precedent (`spec` at `cli.py:273`, `standards` at `cli.py:278`) all exist where Task 4/11 expect them. The registry pattern Task 4 extends (`is_known_agent_handoff()`) matches the four existing `is_known_*` functions (`registry.py:86-95`), and `registry.json` uses snake_case keys with `{default, versions}` shapes as the plan assumes.
- **Claude Code hook contract — verified live today.** The plan's Task 8 details that looked most speculative are all real in the current official reference (`code.claude.com/docs/en/hooks`): command handlers support an `args` array; "a command hook runs as exec form when `args` is set, and shell form when `args` is omitted"; exec form substitutes `${CLAUDE_PROJECT_DIR}` as a plain string with no shell tokenization (so "without shell quoting" is accurate); `statusMessage` and `timeout` fields exist; and SessionStart matchers are exactly `startup|resume|clear|compact`. One caveat: the plan relies on an _empty_ `args` array triggering exec form — the docs say exec form applies "when `args` is set", which an empty array plausibly satisfies, but Task 8's RED tests should include a fixture proving that reading before committing to it.
- **Codex contract.** The plan's Codex references (`learn.chatgpt.com/docs/hooks`, config-basic, the raw SessionStart input schema) are the corrected URLs the round-2 spec review verified live the same day, including the four `source` values and stdout/`additionalContext` transports.
- **Legacy evidence.** The pinned commit `56b24df7…` exists in `/home/chris/projects/agent-handoff-v3` and all nine artifact classes the ingestion-inventory table cites are present in that tree (see L2 for a path-prefix nit). The plan's read-only/no-copy constraints on the checkout match spec §18.4 and B.2.
- **Test landscape.** All twelve existing test files the plan modifies exist; `tests/test_provider_runner.py` and `tests/agent_handoff/` correctly do not. The dogfood targets of Task 17 all exist today exactly as the plan assumes: root `STATUS.md`/`TODO.md`, `.claude/hooks/session_start.py`, `.codex/hooks/session_start.py`, `.codex/config.toml`, `.agents/skills/handoff-system-v3/`.
- **Baseline is green.** The five pytest failures shown in stale session-start data do not reproduce — the three implicated files run 315 passed / 0 failed on the current tree, and the only dirty files are `.gitignore` and `TODO.md`. Task 1's RED step starts from a clean baseline.
- **Dogfood side-effects checked.** Moving `STATUS.md`/`TODO.md` to `docs/` cannot trip the frontmatter gate: `.project-standards.yml` uses an explicit opt-in `include` list (`CHANGELOG.md`, `UPGRADING.md`, `docs/usage.md`, `meta/**`, `docs/adr/**`) that does not cover `docs/*.md`, and `.agents/**` is already excluded.
- **Coverage table content.** All FR-001–024, NFR-001–009, AW, EC, and ERR rows are present and the task assignments spot-check correctly (e.g. FR-016/017 → Task 15, FR-019 → wheel tests in 3/4/16/18, FR-022 → 17–18). Gaps are enumerated below (M1, M2), not scattered.

---

## 🔴 Critical — fix before execution starts

### C1 · Task 13 Step 4's smoke command contradicts the hook Task 13 builds

```bash
python3 standards/agent-handoff/hooks/session-start/session_start.py </dev/null >/tmp/agent-handoff-hook.out
test "$(wc -c </tmp/agent-handoff-hook.out)" -le 4096
```

Two independent problems:

1. **Wrong root, by construction.** Step 3 mandates the hook "derives the repository root from its installed `.agents/hooks/agent-handoff/` path", and Step 1's test pins that to `parents[3]` of the hook file. But the _canonical source_ path this command runs has a different depth: `standards/agent-handoff/hooks/session-start/session_start.py` is four directories below the repo root, so `parents[3]` resolves to `<repo>/standards`. The smoke run would look for `<repo>/standards/docs/handoff/state.md` (absent) and run Git from `<repo>/standards` — at best it byte-counts a mis-rooted degraded payload, which is not evidence the hook works.
2. **Undefined empty-stdin semantics.** Step 3 requires malformed hook input to "emit a concise stderr diagnostic and exit `2`" (spec EC-009). `</dev/null` supplies zero bytes — which is not valid JSON. If the hook treats it as malformed, this command exits 2 and the GREEN step fails; if it doesn't, the plan never says what empty stdin means. Either way the executor hits an ambiguity in a gating command.

**Fix:** replace the smoke with a fixture that mirrors reality: copy the hook into a disposable repo at `.agents/hooks/agent-handoff/session_start.py`, pipe a valid SessionStart JSON fixture in, then assert exit 0 and ≤ 4096 bytes. And add one sentence to Step 3 defining empty stdin (recommended: treat as malformed → exit 2, consistent with EC-009, and give the byte-cap check a real fixture instead).

### C2 · Installed-path root derivation is an unrecorded deviation from the approved spec

Spec §10.1 "Session start" step 2 states: "The hook resolves the Git root **from the event working directory** without escaping it." The plan replaces that with a different authority model — Task 13 Step 3: the hook "derives the repository root **from its installed `.agents/hooks/agent-handoff/` path**, treats stdin/env paths as event metadata rather than authority" — and Step 1's `test_hook_uses_installed_path_as_repository_authority` encodes it permanently.

The plan's design is defensible, arguably better (the installed path is repository-anchored by construction; a cwd can be anywhere, and Claude Code's exec-form command already resolves through `${CLAUDE_PROJECT_DIR}`). But SPEC-DPEY is `status: approved` and change-controlled: its own lifecycle note says deviations are "recorded in the Deviations Log, not silently patched into requirements," and Appendix B.1 requires approval before continuing past a divergence. Right now the spec and the plan disagree on observable hook behavior and nothing records the disagreement.

**Fix (either):** (a) record a `DEV-` row in SPEC-DPEY's Deviations Log (or issue rev 0.4 amending §10.1) adopting installed-path authority, with the owner's sign-off — the cleaner outcome; or (b) change Task 13 to cwd-derived Git-root resolution per the spec. Do it before Task 13's tests are written, and note that C1's fix depends on which way this goes.

---

## 🟡 Important — close before or during execution

### M1 · The Requirement Coverage table omits the IR and DR families

Spec §17.3 traces all seven ID families; Appendix B.3 requires the completion report to map "every implemented requirement" to verification. The plan's coverage table stops at FR/NFR/AW/EC/ERR — no IR-001–IR-008 rows and no DR-001–DR-008 rows. The _content_ is covered (Task 11's tests exercise IR-001/IR-002's exact flag and mapping rules; Task 4 authors DR-001/DR-003; Task 5 implements DR-004/DR-007/DR-008), so this is a bookkeeping gap — but it is precisely the bookkeeping the completion gate audits. **Fix:** add two rows (IR-001–008 → tasks 4–5, 8–11; DR-001–008 → tasks 4–5, 10, 12) or per-ID rows if finer audit is wanted.

### M2 · NFR-004's benchmark has no task step anywhere

The coverage table claims "NFR-003–NFR-005 hook limits/runtime → 12–13, 18", but NFR-004's acceptance criterion is specific: a benchmark test recording p95 < 2 s across **100 local fixture runs** with network disabled. Task 13 Step 4 runs the hook once; Task 18 Step 2's harness probes are single-shot smoke tests. Nothing produces a p95. NFR-004 is a Should, so it may be consciously waived — but then the coverage row is wrong and the waiver belongs in the Deviations Log. **Fix:** add a benchmark test to Task 13 Step 1's list (a 100-iteration loop with `time.perf_counter` percentiles is ~10 lines of pytest) or explicitly record the waiver.

### M3 · The §16 license-verification obligation is missing from the ingestion inventory

Spec §16: "Before ingestion, **the implementation plan shall verify** that every retained legacy file is MIT-licensed or authored under compatible ownership." Task 4 Step 2's inventory table has Disposition and New owner columns but no license/ownership column, and no step performs the check. For a single-author MIT repo this is likely a one-line confirmation — which is exactly why it should be in the inventory rather than skipped. **Fix:** add a license/ownership column (or a one-time verification sentence) to the Task 4 Step 2 inventory requirements.

### M4 · The four integration rows' execution path is underspecified

The Artifact Matrix declares four integration rows targeting live consumer files (`.project-standards.yml` block, `AGENTS.md`/`CLAUDE.md` block, `.claude/settings.json` entry, `.codex/config.toml` block), but the plan states a generic-plan filter only for the lock seed ("the provider filters **that static seed** from generic execution") and, in manual mode, the hook. If an executor declares those four rows as plain `kind = "file"` artifacts with those `dest` values, `execute_plan()` will copy whole packaged fragments over consumer configs — the exact clobbering FR-012 forbids. The current manifest has `fragment`/`target` vocabulary that presumably carries these rows, but the plan never says which kind each row uses nor that all four are intercepted for provider-side bounded merges (Task 10 Step 3's "build config/instruction actions" implies it without connecting it to the matrix rows). **Fix:** annotate the four integration rows with their artifact kind and add one sentence to Task 4 Step 4 or Task 10 Step 3: integration rows are declared for artifact-plane visibility but are always executed by the provider's merge path, never by generic static file copy.

### M5 · The packaged `standard.toml` runtime mirror is a new convention the bundle contract never learns

No existing bundle ships a `standard.toml` under `src/project_standards/bundles/` — today `adopt.toml` lives in bundles and `standard.toml` lives only in `standards/<id>/` (verified across all six bundles). Task 3's provider runner reads `bundles_dir/<id>/standard.toml`, and Task 4 creates the mirror plus a byte-identity test — good. But the plan's Standard Bundle Authoring updates (Task 1: `install_policy`; Task 2: `hooks/` anatomy) never document this third contract change, even though it is what makes `adoption = "cli"` standards executable from a wheel. The meta-standard would immediately drift from reality — and there is already a standing TODO about keeping `standards/standard-bundle-authoring` current. **Fix:** fold "packaged provider-manifest mirror: a standard declaring executable providers ships a byte-identical `standard.toml` in its bundle" into Task 2 Step 4's or Task 16's documentation scope; consider whether the graph validator should enforce mirror parity the way it does for artifacts.

---

## 🟢 Minor

| # | Location | Issue | Fix |
| --- | --- | --- | --- |
| L1 | Task 1 Step 1 | The illustrative `Action(...)` omits `mode`, but the current frozen dataclass (`engine.py:51-60`: kind, source_path, dest, target, standards, mode) has no default shown for it; the snippet as written may not construct. Harmless if executors treat snippets as sketches, hazardous if copied verbatim into the RED test. | Add `mode=None` to the snippet (and note `execute_plan`'s first parameter is named `plan`, with keyword-only `force`/`dry_run` — the plan's call matches, the naming just differs). |
| L2 | Task 4 Step 2 | Path-prefix inconsistency against the pinned commit (verified): the v3 repo nests most content under an `agent-handoff-v3/` subdirectory, which the first rows correctly include, but the skill row (`skills/.agents/skills/handoff-system-v3/`) omits the prefix, and the legacy Python tests live at the repo root (`tests/unit/…`), not nested. | Pin every inventory row to its exact commit-relative path so the executor doesn't chase wrong paths. |
| L3 | Sources of Truth | The plan cites SPEC-DPEY "rev 0.3" and ADR 0022 as accepted — both true at `909bd05` — but `docs/handoff/state.md` still says rev 0.2 and ADR 0022 "await owner approval." Stale handoff state, not a plan defect. | Update `state.md` at the next session closeout. |
| L4 | Task 13 Step 4 | Output redirect to `/tmp/agent-handoff-hook.out`; workstation convention prefers the session scratchpad for temp artifacts. Moot if C1's fixture rewrite lands. | Fold into the C1 fix. |

---

## Coverage and structure — verified clean

- Every FR/NFR/AW/EC/ERR ID defined in the spec appears in the plan's coverage table; no row references an undefined ID. (IR/DR omission is M1.)
- Task ordering is dependency-sound: platform primitives (1–3) → package + registry (4) → models/paths (5–6) → integrations (7–9) → planner (10) → CLI (11) → policy/hook/validation (12–14) → legacy (15) → docs/parity/wheel (16) → dogfood (17) → acceptance/release (18). Execution checkpoints match spec §19's wave gates.
- Every task carries the RED→GREEN→commit cycle with focused test commands and explicit `git add` by name (no `git add .`), and commit messages follow the repo's `feat(v5)`/`docs(v5)`/`chore(v5)` convention.
- Task 18's acceptance matrix matches the repo's non-negotiable gate list plus the standard-specific gates (`validate-graph --require-all-manifests`, `render-catalog --check`, spec validate/lint), and correctly quarantines the known `docs/future-standards/**` Markdown backlog rather than folding it in.
- The retirement sequence (Task 18 Steps 4–6) preserves the spec's owner-approval deletion checkpoint and keeps forks/topic branches inventory-only, consistent with FR-022 and the workstation's git rules.

## Suggested edit order

1. **C2** — decide the root-derivation authority with the owner and record it (Deviations Log entry or spec rev 0.4); it determines C1's shape.
2. **C1** — rewrite Task 13 Step 4 as an installed-layout fixture probe and define empty-stdin semantics in Step 3.
3. **M1 + M2 + M3** — one editing pass: add IR/DR coverage rows, the NFR-004 benchmark step (or waiver), and the license column.
4. **M4 + M5** — pin the integration rows' artifact kinds/interception and add the bundled-manifest-mirror doc scope.
5. **L1–L2** — batch with the same pass.

None of the findings disturb the plan's architecture: the provider-runner boundary, install-policy lifecycle, bounded-merge adapters, two-phase preflight-then-apply planner, provenance lock, and agent-guided migration are all faithful to SPEC-DPEY rev 0.3 and ADR 0022, and the plan's platform assumptions were verified against the code rather than assumed. Fix the two criticals, batch the importants, and it is safe to hand to an executor.
