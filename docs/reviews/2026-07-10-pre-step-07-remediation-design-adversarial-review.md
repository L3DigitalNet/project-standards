# Adversarial Review — Pre-Step-07 Readiness Remediation Design

**Reviewer:** Claude Code (Opus 4.8) **Date:** 2026-07-10 (round 1 at `e5eccea`; round 2 at `e9e4aba`) **Target:** `docs/superpowers/specs/2026-07-10-pre-step-07-readiness-remediation-design.md` **Method:** Every factual claim in the design cross-checked against ground truth — the source inventory (`docs/codex-reviews/2026-07-10-1004-codex-review-plan.md`), SPEC-MT01 and SPEC-RD01 as committed, the live policy (`standards/agent-handoff/resources/policy.toml`), the validator source (`src/project_standards/agent_handoff/validation.py`), the live CLI help, the workflow files, byte-comparison of the dogfooded Python Tooling copies, and fresh runs of the test suite, `agent-handoff validate`, `validate-graph`, `render-catalog --check`, Prettier, and markdownlint. Every 🔴/🟡 finding below is reproduced or traced empirically, not inferred.

## Verdict

**Round 2: APPROVE.** The `e9e4aba` revision resolves all six round-1 findings — F1 substantively (not just re-worded), F2–F4 with the exact mechanisms recommended, F5/F6 verbatim. Three residual 🟢 nits remain (see Round 2 below); none blocks implementation planning.

**Round 1 (at `e5eccea`): APPROVE AFTER ONE REVISION.** The design is factually solid: its diagnosis of the `bugs/INDEX.md` false positive is correct down to the line of code, its counts (nine bundles, seven artifact manifests, ADRs 0017–0022), spec identifiers, FR priorities, and gating claims all check out, and its "green local gate" premise holds (318 tests pass; the session-context CI panel showing 5 pytest failures is stale). But the design silently drops one moderate finding from its own source inventory — HK-006, the absence of hosted CI evidence for the `testing` branch — and its sole CI addition reproduces the exact trigger gap HK-006 describes. Since the readiness gate is the point of the whole exercise, that omission is a blocking revision, and it is a one-line fix. The remaining findings are wording and future-proofing.

## What is correct and verified (so the approver can trust it)

| Design claim | Ground truth | Status |
| --- | --- | --- |
| SPEC-RD01 requires complete SPEC-MT01 traceability before Step 07 | Roadmap Step 07 row: entry criteria "`SPEC-MT01` traceability complete"; §"Treat Step 07 as a hard gate" | ✅ |
| SPEC-MT01 presents implemented requirements as `Not Started` | 22 `Not Started` occurrences in the readiness spec; FR range is exactly FR-001–FR-022 | ✅ |
| FR-013 is a non-blocking `Should` (agent summaries) | FR-013 priority `Should`; only 1 of 9 bundles ships `agent-summary.md` (agent-handoff) — the gap is real | ✅ |
| FR-019 is Step-07 readiness-report work | FR-019 priority `Must`, acceptance is the documented readiness checklist | ✅ |
| `bugs/INDEX.md` false positive exists | `agent-handoff validate` emits `INDEX.md: missing required section: Cause/Fix/Lesson` (3 warnings) today | ✅ |
| Discovery "splits only at `*`" | `validation.py:363` — `parent = pattern.split("*", maxsplit=1)[0].rstrip("/")`; the proposed bracket glob would derive parent `docs/handoff/bugs/[0-9][0-9][0-9]-` without the paired discovery fix, so bundling both changes is correct | ✅ |
| `[0-9][0-9][0-9]-*.md` matches the record convention | Standard's skill mandates three-digit IDs; both live records (`001-`, `002-`) match; bugs shape is `required = false`, so narrowing the glob introduces no missing-document false positive | ✅ |
| check.py/check.yml byte-identical contract | `cmp` confirms `scripts/check.py` ≡ bundle copy and `.github/workflows/check.yml` ≡ bundle copy — decision 2's rationale for a separate workflow is sound | ✅ |
| CLI commands and flags in the workflow and Verification block | `standards validate-graph --root/--json/--require-all-manifests`, `render-catalog --check`, `spec validate/lint`, `validate`, `agent-handoff validate/drift-check` all exist in the live CLI | ✅ |
| Tested-contract items match repo policy | check.yml uses `checkout@v6`, `setup-python@v6`, SHA-pinned `setup-uv` (v8.2.0, uv 0.11.6), `uv sync --locked --all-groups` — every asserted item is real (but see 🟡 F3) | ✅ |
| v5 changelog gap for Steps 02–06 | `CHANGELOG.md` has no entry for `validate-graph`, `render-catalog`, or the standards-graph/manifest introduction | ✅ |
| Stale "future Step 04" comments | `standard_manifest.py:37,149,285` still describe Step 04 as future work | ✅ |
| Nine bundles, seven artifact manifests, ADRs 0017–0022 | 9 standard directories; exactly 7 `standard.toml` files carry `[artifacts]` (python-coding and standard-bundle-authoring do not); ADRs 0001–0022 all present | ✅ |
| New workflow would start green | `validate-graph --require-all-manifests` → `OK standards graph`; `render-catalog --check` → `OK generated catalog` on the current tree | ✅ |
| Deferred Markdown debt still reproduces | markdownlint errors confined to `docs/future-standards/**`; the design doc itself passes Prettier and the frontmatter gate (design-doc genre is intentionally outside spec-frontmatter scope per `.project-standards.yml`) | ✅ |
| "Full local Python gate is green" | 318 tests pass, including the 5 the session CI panel lists as failing (stale data) | ✅ |
| `tests/test_standards_graph_workflow.py` is net-new | File does not exist; named companion tests (`test_standards_graph_cli.py`, `test_standards_graph_catalog.py`, `tests/agent_handoff/test_policy.py`, `test_validation.py`) all exist | ✅ |

Inventory-coverage audit: PS-001/002/003/005, HK-001, HK-002 (core), HK-005 → **Included**. PS-004, HK-003, HK-004 → **Deferred for owner input**. That leaves HK-006 — see F1.

---

## Findings

### 🔴 F1 — HK-006 is dropped without disposition, and the new workflow reproduces the exact gap it describes

**Claim under attack:** "Add explicit hosted CI for graph validation and catalog freshness … runs on every pull request and every push to `main`" (§Scope, §Design decision 2), plus the acceptance criterion "A dedicated repository-only workflow visibly enforces graph validity and catalog freshness."

**Evidence.** The source inventory's HK-006 (severity: moderate): `testing` is 111 commits ahead of `main`, push workflows run on `main` only, there is no open PR, so "recent hosted runs validate released `main`, not the current v5 branch"; its action is "obtain a hosted pull-request or equivalent workflow run **before the readiness gate is declared complete**." The design cites this inventory as its source, gives every other PS/HK finding a disposition (see coverage audit above), and gives HK-006 none — it appears in neither Included, nor Deferred, nor Excluded.

Worse, the design's only CI change copies check.yml's trigger shape (`pull_request` + `push: [main]`). In this repository's actual flow — single developer, direct commits on `testing`, no PRs — that trigger produces **zero hosted runs for the branch where all v5 and remediation work lands**. The new "hosted evidence" gate therefore cannot generate hosted evidence for the very work it is meant to gate, and the acceptance criterion "visibly enforces" is unfalsifiable until a merge or PR that the design neither schedules nor defers.

**Why the design's own logic permits the fix.** Decision 2's constraint (don't contaminate the byte-identical generic gate) applies to `check.yml`; `validate-standards-graph.yml` is explicitly repository-only, so nothing prevents `push: [main, testing]`.

**Required revision (one of):**

1. Trigger the new workflow on `push: [main, testing]` (and update the workflow-contract test in decision 3 accordingly) — recommended, one line; or
2. Add HK-006 to "Deferred for owner input" with an explicit rationale and a note that Step 07's readiness report cannot claim hosted evidence until it is resolved.

### 🟡 F2 — "Distinct index shape" is overstated; the fix leaves `INDEX.md` with zero shape validation

Decision 4 asserts the standard gives `bugs/INDEX.md` "a distinct index shape." Ground truth: the standard's only index contract is one skill sentence ("maintain `docs/handoff/bugs/INDEX.md` sorted by ID" — `standards/agent-handoff/skills/agent-handoff/SKILL.md:62`); `policy.toml` defines **no** index shape, and the design adds none. After the fix, the index is excluded from bug-record checks and gains nothing in exchange — a stale, unsorted, or incomplete index validates silently. The acceptance criterion only demands the absence of the false positive, so this regression-by-omission would pass acceptance. Not blocking (the pre-fix state validated the index against the _wrong_ shape, which is strictly worse), but the design should either state the trade-off explicitly or add a minimal index profile (e.g., required table, ascending three-digit IDs) while it is touching both policy copies anyway.

### 🟡 F3 — The pin-assertion test collides with deferred HK-003 and undefined "current repository policy"

Decision 3's test asserts "action and uv pins match current repository policy," but the repo has no single pin policy to match: `coherence.yml` uses `setup-node@v4` alongside `checkout@v6`, and Dependabot PR #2 (`checkout` v6→v7) — deferred to owner cleanup under HK-003 — already demonstrates the failure mode: a pin bump that misses one of the coordinated surfaces. The new test adds a **third** place (workflow + check.yml + test literals) that must move in lockstep on the next bump. Recommendation: define "current policy" operationally as "equal to `check.yml`'s pins" and have the test parse and compare the two workflows rather than asserting hard-coded literals — then a future coordinated bump is one comparison invariant, not two edit sites. If the owner later accepts checkout v7 via HK-003, nothing in this design's tests should need touching.

### 🟡 F4 — The discovery fix's safety constraint is implicit and untested

Decision 4's fix "derives the static parent directory from the path component before the filename pattern." That is only static if glob metacharacters are confined to the final path component — true for every pattern in today's policy, but nothing rejects a future pattern like `docs/handoff/*/[0-9]*.md`, whose "parent" derivation would silently mis-resolve and whose boundary check (`repository.consumer_path(parent)` at `validation.py:364`) would again receive a non-literal path. The listed regression tests (malformed record warns; index excluded; bracket discovery repo-confined) do not cover a glob character in a directory component. Recommendation: make discovery reject (or explicitly document and test) directory-level glob characters — one extra test alongside the three already planned.

### 🟢 F5 — HK-002's instruction-file size warnings have no disposition

The inventory's third HK-002 action (trim `AGENTS.md`/`CLAUDE.md` over-target advisory warnings if the self-contained contract allows) appears in none of the scope buckets and not in the owner-question list. Advisory-only and harmless, but for a design whose premise is "reconcile the inventory," name it — one bullet under Deferred or owner question 6.

### 🟢 F6 — Verification block omits the coherence gate

`CLAUDE.md` lists the full toolchain gate as including coherence tests (`npm ci` required). The Verification section runs the Python gate, the graph/catalog CLI, handoff validation, and targeted Prettier/markdownlint, but not coherence — and this remediation adds a workflow file and edits packaged policy copies, both surfaces coherence-style parity tests may assert over. Add `npm ci && <coherence run>` (or note why it is exempt) to the Verification list.

---

## Adversarial checks attempted that did NOT produce findings

- **Fresh-repo false positive from the narrowed glob:** dismissed — `[shape.documents."docs/handoff/bugs/*.md"]` has `required = false`, so an empty bugs directory stays silent after the change.
- **Bracket glob unsupported by the matcher:** dismissed — targets are enumerated via `Path.glob(pattern)` (`validation.py:366`), which supports character classes.
- **"Green gate" premise vs. session CI panel showing 5 failing tests:** dismissed — all 318 tests pass on the current tree; the panel data is stale.
- **Decision 2's byte-identity rationale:** confirmed byte-for-byte; adding repo-specific commands to `check.py`/`check.yml` really would break the bundle contract.
- **Command/flag fabrication in the workflow and Verification block:** every command exists with the exact flags cited.
- **Count inflation (bundles, manifests, ADRs):** all counts exact; the 10th `standard.toml` is the authoring template, correctly not counted.
- **Design doc's own hygiene:** passes Prettier, the repo frontmatter gate, and its markdown is clean; the `../../codex-reviews/…` source link resolves.

## Disposition summary

| # | Severity | Finding | Fix cost |
| --- | --- | --- | --- |
| F1 | 🔴 | HK-006 dropped; new workflow can't produce hosted evidence for `testing` | One line (`push: [main, testing]`) + test |
| F2 | 🟡 | Index left with zero shape validation; "distinct shape" overstated | One sentence, or a small index profile |
| F3 | 🟡 | Pin test hard-codes literals; collides with deferred HK-003 | Compare against check.yml instead |
| F4 | 🟡 | Discovery fix assumes filename-only globs, untested | One rejection branch + one test |
| F5 | 🟢 | Instruction-file size warnings undispositioned | One bullet |
| F6 | 🟢 | Coherence gate missing from Verification | One line |

---

## Round 2 — review of revision `e9e4aba` ("docs(v5): address pre-step 07 design review")

**Method:** diffed `e5eccea..e9e4aba`, re-verified every new claim the revision introduces (not just that the old text changed), re-ran hygiene gates on the revised doc, and executed the coherence suite the revision now cites.

### Round-1 finding dispositions

| # | Round-1 finding | Disposition | Evidence |
| --- | --- | --- | --- |
| F1 | 🔴 HK-006 dropped; no hosted evidence for `testing` | ✅ Resolved | Recommended option 1 taken end-to-end: the Included bullet, decision 2 ("push to `testing` or `main`", with the rationale for each trigger), the tested-contract list, and the acceptance criterion all now name `testing`. The acceptance criterion is falsifiable on the next `testing` push. HK-006 is not cited by ID, but its substance is covered — acceptable. |
| F2 | 🟡 "Distinct index shape" overstated | ✅ Resolved | Reworded to the truth ("governed only by the skill's sorting instruction; it has no machine-enforced shape profile"), the trade-off is now explicit ("deliberately leaves `INDEX.md` without structural validation … narrower and safer"), and index validation is a named Deferred item plus owner question 7. |
| F3 | 🟡 Pin test hard-codes literals | ✅ Resolved | Test now compares values "parsed from `.github/workflows/check.yml`" instead of literals. Verified the anchor is sound: `tests/test_adopt_dogfood.py:36` already enforces bundle ↔ `check.yml` byte-parity, so the new comparison is transitively anchored to the bundle contract — a coordinated pin bump is one invariant, as recommended. |
| F4 | 🟡 Discovery fix generality unstated/untested | ✅ Resolved | Decision 4 now specifies the algorithm (separate directory from filename pattern; reject `*`/`?`/`[` in the directory component with `AH-PATH-BOUNDARY`; validate the literal directory through the boundary; `Path.glob` the filename) and adds the fourth regression test for a directory-level metacharacter. |
| F5 | 🟢 Size warnings undispositioned | ✅ Resolved | Named Deferred bullet + owner question 6. |
| F6 | 🟢 Coherence gate missing | ✅ Resolved | Verification adds `npm ci` and `uv run pytest tests/coherence -v` — exactly what `coherence.yml:32-33` and `AGENTS.md:28` prescribe. Verified `tests/coherence/` exists (`test_behavioral.py`, `test_declaration.py`, `test_pins.py`) and the suite passes (8 passed). |

### New claims introduced by the revision — verified

- **`uv run pytest tests/coherence -v` is the correct invocation:** matches `coherence.yml` verbatim and the `AGENTS.md` gate line; suite runs green today.
- **check.yml as pin anchor is not a third pin source:** confirmed — `tests/coherence/test_pins.py` governs the npm-side pins (Prettier/markdownlint) only, so no overlap or conflict with the new workflow test's action/uv comparison; the byte-parity test makes check.yml a _derived_ surface of the bundle, not an independent one.
- **Revised doc hygiene:** Prettier clean, frontmatter gate green (27 files), status line updated honestly to "revised after adversarial review; pending owner approval".

### Residual findings (non-blocking)

- 🟢 **R2-1 — The incorporated review is cited without a link, and the review file is untracked.** "The design also incorporates the 2026-07-10 adversarial design review" names no path, while the codex inventory sentence beside it is a live link. This file (`docs/reviews/2026-07-10-pre-step-07-remediation-design-adversarial-review.md`) is also still untracked in git, so a link added today would dangle for any reader of the committed tree. Commit the review and link it.
- 🟢 **R2-2 — The literal-vs-glob branch selector is still unspecified.** Decision 4 rejects `*`/`?`/`[` in _directory_ components but never states which condition routes a pattern to the literal-path branch (today it is `"*" not in pattern` — `validation.py:360`). A future filename pattern using only `?` or `[` (no `*`) would silently be read as a literal path and match nothing. The chosen pattern contains `*`, so nothing breaks now; one sentence ("a pattern whose filename component contains any of `*`, `?`, `[` is treated as a glob") closes it, and the implementation should test that branch condition, not just directory rejection.
- 🟢 **R2-3 — "uv setup versions" is ambiguous about the `version:` input.** The tested contract compares "checkout, Python setup, and uv setup versions" against check.yml. The uv step has two version-bearing values: the action ref (SHA-pinned `v8.2.0`) and the `with: version: "0.11.6"` uv release. The comparison should explicitly cover both; as worded, an implementer could satisfy it with the action ref alone and let the uv release drift between the two workflows.

### Round 2 disposition summary

| # | Severity | Finding | Fix cost |
| --- | --- | --- | --- |
| R2-1 | 🟢 | Review cited without link; review file untracked | Commit + one link |
| R2-2 | 🟢 | Literal-vs-glob branch selector unspecified for `?`/`[`-only patterns | One sentence + one test |
| R2-3 | 🟢 | uv `version:` input not explicitly in the pin comparison | Two words in the contract list |

**No 🔴 or 🟡 findings remain. Approved for implementation planning; the 🟢 items can be folded into implementation without another design round.**
