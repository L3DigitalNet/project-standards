# Plan Review — Pre-Step-07 Readiness Remediation Implementation Plan

**Reviewer:** Claude Code (Fable 5) **Date:** 2026-07-10 **Target:** `docs/superpowers/plans/2026-07-10-pre-step-07-readiness-remediation.md` (at working-tree state after `c156d1f`) **Method:** Every code snippet, command, file path, count, commit hash, test name, and premise in the plan cross-checked against ground truth — the live validator source (`src/project_standards/agent_handoff/validation.py`, `policy.py`), both policy TOML copies, the existing test modules and their fixtures/helpers, `.github/workflows/*`, the Prettier and Ruff configuration, the spec's actual section structure and requirement/OQ/DoD text, the handoff pointer documents, and fresh runs of the test suite, `shape-check`, `validate-graph`, `render-catalog --check`, and Prettier against the plan's exact workflow YAML. The companion design (`docs/superpowers/specs/2026-07-10-pre-step-07-readiness-remediation-design.md`) was read for coherence; its own adversarial review already exists and is not re-litigated here.

## Verdict

**APPROVE AFTER ONE REVISION.** The plan is technically sound at an unusual level of detail: the TDD red states in Task 1 Step 3 are individually correct under current code, the monkeypatch signature matches the real `_load_policy(findings)` call, `glob.has_magic` exists at runtime and in BasedPyright's bundled typeshed, adoption really does create `docs/handoff/bugs/` (so the new test's writes succeed), no existing policy key contains `[` or `?` (so widening `_document_config` to `has_magic` is backward-safe), and every cited test, ADR, commit, and count checks out. One finding is blocking because it plants a CI failure that **none of the plan's own gates ever runs against the file**: the workflow YAML's quote style fails the repo-wide Prettier check (F1). Three smaller findings cause avoidable fix-up commits or implementer confusion. All are one-to-three-line plan edits.

## What is correct and verified

| Plan claim / premise | Ground truth | Status |
| --- | --- | --- |
| `bugs/INDEX.md` false positive exists today | `shape-check` emits `INDEX.md: missing required section: Cause/Fix/Lesson` (3 warnings) on the live repo | ✅ |
| Current policy glob is `docs/handoff/bugs/*.md`; both copies byte-identical | `policy.toml:118` in both; `cmp` clean | ✅ |
| No existing policy key contains `[` or `?` | All 8 `[shape.documents...]` keys are literal or `*`-globs — the `has_magic` widening changes no existing match | ✅ |
| Task 1 Step 3 red states (all four tests) | Traced individually: broad glob hits INDEX (test 1 red); bracket-only pattern takes the literal branch and finds nothing (test 2 red); `docs/handoff/*/[0-9].md` globs nothing (test 3 red); policy key assertion red until Step 5 | ✅ |
| `monkeypatch.setattr(validation, "_load_policy", lambda findings: policy)` | Real signature is `_load_policy(findings)` called from `shape_check`; module-level, patchable | ✅ |
| `AH-PATH-BOUNDARY` finding with `path == pattern` on boundary error | `shape_check` catches `RepositoryBoundaryError` and emits exactly that (`validation.py:384`) | ✅ |
| `from glob import has_magic` survives the strict gate | Present at runtime (`has_magic('[0-9].md') → True`) and declared in basedpyright's bundled typeshed `glob.pyi` | ✅ |
| New test writes into `docs/handoff/bugs/` without mkdir | `_adopt` creates the full layout — `test_fresh_manual_adoption_passes_its_own_contract` asserts zero findings, and layout requires the bugs dir | ✅ |
| Test helpers/fixtures exist | `_adopt` in `test_validation.py`; module-scoped `policy` fixture and `HandoffPolicy` import in `test_policy.py`; `shape_check`, `RepositoryRoot`, `pytest` already imported where needed | ✅ |
| `fnmatch` matches the narrowed key | `fnmatchcase("docs/handoff/bugs/001-test.md", "docs/handoff/bugs/[0-9][0-9][0-9]-*.md")` holds; `INDEX.md` does not match | ✅ |
| Workflow test mechanics | `yaml.safe_load` parses `on:` as boolean `True` key (the `workflow[True]` trick works); `pull_request:` → `None` is guarded by `isinstance(trigger, dict)`; PyYAML + `types-PyYAML` are declared dependencies | ✅ |
| Pin parity with `check.yml` | `actions/checkout@v6`, `actions/setup-python@v6`, SHA-pinned `astral-sh/setup-uv` (v8.2.0) with `version: "0.11.6"`, `uv sync --locked --all-groups` — all match; branch list order `['main', 'testing']` matches the test's `== ["main", "testing"]` | ✅ |
| No existing hosted graph/catalog gate | No workflow in `.github/workflows/` runs `validate-graph` or `render-catalog`; the new workflow fills a real gap | ✅ |
| Coherence suite unaffected | `tests/coherence/` pins npm tool versions and behavior; it does not enumerate workflow files, so a new workflow cannot break it | ✅ |
| Counts: nine bundles, nine `standard.toml`, seven packaged `adopt.toml` | `standards/` has 9 bundle dirs, 9 manifests; `src/project_standards/bundles/*/adopt.toml` count is 7 | ✅ |
| Stale "eight current bundles (six ship…)" phrase | Present verbatim at `standards/standard-bundle-authoring/README.md:7` | ✅ |
| Stale Step-04 future tense | Present in `standards/standard-bundle-authoring/standard.toml:4-5` and `standard_manifest.py:7,37,149,285` | ✅ |
| Spec structure matches the edit instructions | §17.1 (both quoted Step-07 DoD bullets verbatim), §17.3 (22 FR rows, all `Not Started`), §18.7, §21 (OQ-001–008, all `Open`), Deviations Log with matching columns | ✅ |
| ADRs 0017–0022 exist; FR-016's "ADRs 0001-0013" claim | All six methodology ADRs on disk; §8.3 maps D-001… to `adr-0001`… (the spec's own ADR set), consistent with the matrix row | ✅ |
| All 20 cited test names/files exist | Every `tests/test_*` and `::test_*` reference in the §17.3 matrix located | ✅ |
| Commit `39b9f76` | Exists: `feat(v5): complete standards composition catalog` (the Step 06 closeout) | ✅ |
| Handoff pointer premises | `specs-plans.md` prune note, Storage bullet, "all eight bundles", "Step 06 remains…", and "(this closeout)" all present; Step 06 plan has 26 unchecked boxes; retirement-inventory `project-standards` row matches the described rewrite | ✅ |
| "Gate is green" premise | The session-context panel showing 5 pytest failures is stale — the three named test files pass 318/318; `validate-graph` and `render-catalog --check` pass live | ✅ |
| PEP 758 style context | `validation.py` already uses Python 3.14 unparenthesized multi-exception syntax; the plan's snippets are stylistically compatible | ✅ |

## Findings

### 🔴 F1 — The workflow YAML fails the repo-wide Prettier gate, and no step in the plan ever checks it

Task 2 Step 3's YAML uses single-quoted strings (`'main'`, `'testing'`, `'.python-version'`, `'0.11.6'`). The repo's `.prettierrc` sets `singleQuote: false` (the `**/*.md` override does not apply to YAML), and `format.yml` runs repo-wide `prettier --check .` — whose scope explicitly includes YAML — on every pull request and push to `main`. Empirically, Prettier 3.8.3 with the repo config rewrites all three quoted lines to double quotes, so `--check` fails on the file exactly as written.

The plan never catches this: Task 2 Step 4 runs pytest and the two CLI commands; Task 7 Step 5 runs Prettier **only on changed Markdown**. The failure is latent — it lands cleanly on `testing` (format.yml has no `testing` push trigger) and detonates on the next PR or `npm run format:check`.

**Fix (3 lines):** use double quotes in the workflow snippet, matching `check.yml`'s existing style: `branches: ["main", "testing"]`, `python-version-file: ".python-version"`, `version: "0.11.6"`. Optionally add `npx prettier --check .github/workflows/validate-standards-graph.yml` to Task 2 Step 4.

### 🟡 F2 — Task 1 Step 2 snippet exceeds the Ruff line length by one character

The line `assert any(finding.code == "AH-SHAPE" and finding.path.endswith("/1.md") for finding in findings)` is 101 characters; `pyproject.toml` sets `line-length = 100`. `ruff format --check` (via `scripts/check.py`) rejects it — but the first formatter run in the plan is Task 7 Step 3, five commits after Task 1 Step 7 committed the file. The result is an out-of-plan fix-up commit or a rewritten Task 1 commit.

**Fix:** wrap the assertion across two lines in the plan snippet (e.g., bind `matches = [f for f in findings if ...]` or split inside `any(...)`), or add `uv run ruff format --check tests/agent_handoff/` to Task 1 Step 6.

### 🟡 F3 — Task 4 marks FR-015 `Passing` citing evidence that Task 5 creates

The §17.3 matrix row for FR-015 cites "`UPGRADING.md` v5 manifest/graph migration posture" — but that section is added by Task 5 Step 2, one task **after** Task 4 commits the matrix. At the `docs(v5): reconcile spec mt01 traceability` commit, the tree contains a `Passing` claim whose evidence does not exist, contradicting the design's own first principle ("traceability records reality"). The end-of-tranche state is consistent, but commit-granular history is not.

**Fix:** swap Tasks 4 and 5 (Task 5 has no dependency on Task 4), or defer only the FR-015 row edit into Task 5.

### 🟡 F4 — Task 3 lists and stages `templates/standard.toml` but no step edits it

`standards/standard-bundle-authoring/templates/standard.toml` appears in Task 3's **Files** list and its Step 6 `git add`, yet Steps 1–4 name only the README, the bundle's own `standard.toml`, `standard_manifest.py`, and the schema. The template contains no stale Step-04 text or bundle-count phrase (verified by grep). Either an intended template change went unstated (most plausibly mirroring the manifest-comment rewrite or a count fix in commentary) or the entry is leftover from drafting. Under the plan's own commit discipline — "stage only the files named by that task" — naming a file that never changes invites the implementer to invent an edit.

**Fix:** state the intended template change, or delete the file from the Files list and the `git add`.

### 🟢 F5 — `_POLICY_PATH` duplicates an existing constant

Task 1 Step 2 defines `_POLICY_PATH` in `test_validation.py`; `test_policy.py` already defines the identical `POLICY_PATH`. Duplication across test modules is acceptable (cross-importing test modules would be worse), but the implementer should know the sibling exists and keep the two spellings consistent.

### 🟢 F6 — Session-context CI panel is stale, not a plan defect

The harness session context reports 5 pytest failures in `test_adopt_manifest.py`, `test_format_frontmatter.py`, and `test_validate_frontmatter.py`. All 318 tests in those files pass on the current tree. Recorded here so the implementing session does not burn time reconciling a phantom regression.

## Design–plan coherence

The plan faithfully implements every design decision: the workflow trigger set (PR + push to `testing`/`main`, no path filters) matches design decision 2 including the round-1 HK-006 remediation; the eight-point tested-contract list in design decision 3 maps one-to-one onto `test_repository_graph_workflow_contract`'s assertions; the shape-discovery mechanics in design decision 4 (glob-metachar filename ⇒ glob, metachar directory ⇒ `AH-PATH-BOUNDARY`, no hard-coded `INDEX.md` exception) match the Task 1 snippets; and the deferred owner-choice list (7 items) matches the design's verbatim. No scope drift found in either direction.
