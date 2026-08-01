---
schema_version: '1.1'
id: 'reference-q4vt7m-open-issue-resolution-program-plan-audit'
title: 'Open-Issue Resolution Program Plan — Adversarial Plan Audit'
description: 'Read-only adversarial audit of the open-issue resolution program implementation plan against live repository, catalog, consumer, and GitHub evidence.'
doc_type: 'reference'
status: 'active'
created: '2026-08-01'
updated: '2026-08-01'
reviewed: '2026-08-01'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'review'
  - 'plan-audit'
  - 'validation'
aliases: []
related:
  - 'docs/plans/2026-08-01-open-issue-resolution-program-plan.md'
  - 'meta/versioning.md'
  - 'docs/research/2026-07-09-agent-handoff-retirement-inventory.md'
---

# Open-Issue Resolution Program Plan — Adversarial Plan Audit

## Executive summary

The plan is structurally sound and its file-level claims survive falsification: every source path, test path, package directory, and script it names exists, its 32 tasks form an acyclic dependency graph with no dangling references, every requirement ID is covered by a task, and Agent Handoff 1.8 is already the catalog default with its payload present — so T1 really is release qualification rather than new development. The failures are not in the task decomposition; they are in the four load-bearing factual premises the program rests on.

Four blocking findings: the frozen 23-issue inventory is already stale against live GitHub state (24 open, #109 unaccounted for); the proposed release-classification rule in REQ-902 contradicts `meta/versioning.md`'s previously-passing rule, which the plan's own corrective tasks repeatedly trip; T32 scopes consumer retirement to two repositories when live branch evidence shows three still owe protected merges; and the plan's documented entry point (T1) is unreachable because T1 depends on T30, contradicting both `docs/TODO.md` and `docs/STATUS.md`.

No internet research was required — every material claim resolved against local repository, git, and GitHub-CLI evidence. The plan carries no external version, API, or upgrade-procedure assumption that could be stale.

## Verdict

Needs major correction before execution.

## Audit loop status

- Audit type: First audit
- Plan path: `docs/plans/2026-08-01-open-issue-resolution-program-plan.md`
- Significant findings remaining: Yes
- Blocking issue count: 4
- Non-blocking issue count: 6

## What the plan gets right

- Every file path it names exists: all seven `src/project_standards/` modules, `meta/versioning.md`, both named test files, `scripts/verify.sh`, `scripts/plan.py`, `docs/mcp-server.md`, `UPGRADING.md`, and all four `standards/` package directories.
- T1's premise is verified: `standards/agent-handoff/versions/1.8/` and `src/project_standards/payloads/agent-handoff/1.8/` both exist, and `standards/catalog.md:21` already lists `agent-handoff` 1.8 with role `default`. The TDD exception for T1 is justified, not an excuse.
- The plan satisfies every invariant `scripts/plan.py validate` enforces: 32 task IDs, all 32 `depends_on` references resolve to defined tasks, all 28 requirement IDs in §4 appear in some task's `requirements:` field, filled `created`/`updated` dates, no unfilled `<...>` placeholders, and no bare `pytest`/`ruff`/`pyright` invocations in fences.
- Release-train batching genuinely reduces qualification cost, and the issue partition is arithmetically complete against the frozen set: §8's trains sum to exactly the 23 issues listed in §3.1, and T8/T15/T21's "six/seven/five closures" match their trains.
- The immutability constraints are real and correctly stated: `release.py` marks payload deletion, payload mutation, and catalog digest replacement as `FORBIDDEN`, matching §3.3's byte-preservation requirement.
- T32 correctly refuses to build generalized migration machinery for a two-repository closeout, and correctly requires publication authorization on protected branches.

## Adversarial review performed

- **Claim inventory** — extracted every file path, package version, command, issue number, dependency edge, count assertion, and owner-decision citation in the plan.
- **Falsification** — tested all 23 named paths on disk; enumerated `standards/*/versions/` and `src/project_standards/payloads/*/` to check successor premises; read `standards/catalog.md` to verify 1.8's role; read `classify_catalog_diff` and `_release_boundary_error` in `release.py` against T30's characterization of the current contract; queried live GitHub issue state; inspected four consumer repositories' branch topology and tree contents directly.
- **Blast radius** — traced what each correction train changes for consumers: the moving `v5` tag means every `@v5` consumer inherits a train immediately, and `meta/versioning.md:160` makes full-version tags immutable, so a defective train cannot be withdrawn by tag deletion.
- **Failure modes** — attacked the dependency graph for ordering inversions, checked whether the ready set matches the documented entry point, and examined whether the #84 investigation is sequenced before the trains whose qualification it could destabilize.
- **Validation attack** — verified the per-task gate is a real signal rather than a pre-red gate: ran full-repo markdownlint (0 issues in 1204 files), confirming the 463-error `docs/future-standards/**` backlog recorded in the retirement inventory's acceptance baseline has been cleared, so `scripts/verify.sh`'s Prettier and markdownlint statics are meaningful. Also checked Appendix A for tasks whose verification has no traceability row.
- **Minimality** — checked T30's scope against the narrower question `docs/TODO.md` actually poses, and checked T32's scope against the canonical retirement ledger.
- **Not checked** — `scripts/verify.sh`, `scripts/verify.sh --full`, `uv run python3 scripts/plan.py validate`, and `project-standards check-release` were not executed: they write coverage data, build artifacts, venv state, or checklist state, which read-only mode forbids. Plan-structure invariants were therefore verified by manual inspection against the validator's source rather than by running it. Prettier was not run because `--cache` writes a cache file; only markdownlint (which writes nothing) was executed. The spec-traceability pass was not performed — the plan declares `spec_ref: ''` and no specification was supplied.

## Blocking issues

### CR-001: The frozen 23-issue inventory is already stale, and #109 has no disposition path

- Severity: High
- Status: Confirmed
- Adversarial angle: The plan asserts a live refresh result as fact; a live refresh performed during this audit should reproduce it exactly.
- Plan reference: §2 ("Live refresh on 2026-08-01 found the same 23 open issues and no closures"), §3.1, §3.2, REQ-901, T29 acceptance ("all 23 issues"), §11, Appendix B.
- Finding: There are 24 open issues, not 23. Issue #109, "[upgrade] Python Tooling fresh adoption emits no PEP 621 project metadata for required uv lock", was created 2026-08-01T07:35:59Z and is open. It appears in no scope list, no requirement, no train, and no task. Appendix B's boundary — "An issue opened after 2026-08-01 is not automatically part of this program" — does not cleanly exclude it, because #109 was opened *on* 2026-08-01, not after it; the freeze is expressed as a date while the collision is at the hour level. Separately, #109 is a Python Tooling adoption defect in the exact surface train D rewrites (T17 `source_layout`/import roots, T18 Ruff roots, T20 root modelling). Train D will publish a Python Tooling successor that still carries #109, forcing a fifth release train for a defect that was open before the successor was cut.
- Repository evidence: `gh issue list --state open` returns 24 issues; `gh issue view 109` gives `createdAt=2026-08-01T07:35:59Z`, `state=OPEN`. Its body reports `uv lock` failing with `No project table found` after `project-standards reconcile --apply` generates a `pyproject.toml` with `[dependency-groups]`, `[build-system]`, and `[tool.*]` but no `[project]` table, against Python Tooling 1.10 with `source_layout = "src"` — the same package and option surface T17/T18/T20 modify. §8's own effort estimates total roughly 58–112 active days, so the inventory will drift much further before T29 runs.
- External research evidence: Not applicable.
- Why it matters: REQ-901 ("Leave no frozen issue open without an accepted disposition") and §11 ("GitHub has no frozen issue open without an accepted monitoring disposition") are both satisfiable while #109 sits open, because #109 is not in the frozen set. The program can therefore report completion against a tracker that still has an open, in-scope-shaped defect — the precise outcome REQ-901 exists to prevent.
- Recommended action for the authoring agent: Re-run the inventory and restate §2 with the true count and the exact freeze timestamp (not just the date). Then make an explicit, recorded decision on #109: either admit it into train D as a new task under Appendix B's owner-approval clause — which is the cheaper option, since T17/T18/T20 already open that package — or record it in §3.2 as a named, deliberate exclusion with a successor release that will carry it. Tighten Appendix B's boundary to a timestamp so same-day issues are unambiguous.
- Suggested validation: `gh issue list --state open --limit 100 --json number,createdAt` immediately before execution begins, diffed against §3.1's list.

### CR-002: REQ-902's release-classification rule contradicts the previously-passing rule, which the plan's own corrections trip

- Severity: High
- Status: Confirmed
- Adversarial angle: A proposed classification rule must be checked against both the documented contract it replaces and the specific releases this plan intends to ship under it.
- Plan reference: REQ-902, T30 acceptance, T30.3, §8, §10 R-007, §11.
- Finding: REQ-902 says releases with a standard-package version advance are MINOR and releases without one are PATCH, with only "package removal/downgrade and immutable-byte violations" carved out as forbidden. `meta/versioning.md:127` states the opposite as an absolute: "If any change can turn a **previously-passing** consumer document or workflow run into a **failure**, the release is **MAJOR** — without exception", and the line immediately after it says this holds *even when the change is a genuine bug fix*. Several of this plan's corrections are exactly that case. T6's acceptance is that "matcher-less and differently matched legacy groups cannot yield a green double injection" — consumers whose `reconcile`/`validate`/`drift-check` are green today go red. T12's acceptance is that "invalid IDs block before lock publication" — migrations that succeed today are blocked. T19 changes ownership of `[tool.ruff]` sub-tables, T7 changes which secret references are flagged, and T5 changes pre-apply refusal behavior; each can flip a consumer outcome. The plan never classifies any of the 20 corrective tasks against the previously-passing rule, and R-007's mitigation covers only forbidden-transition detection, not this rule.
- Repository evidence: `meta/versioning.md:111` ("Classify each release by the highest-severity change it contains"), `:116` (Validator CLI MAJOR column: "Any change that makes a previously-passing document fail"), `:127` (the previously-passing rule), `:53` ("a change that newly fails a consumer or changes an ordinary default incompatibly requires a new MAJOR and catalog-major transition"). In `src/project_standards/package_contract/release.py:137-255`, `classify_catalog_diff` inspects only catalog and payload composition — it never sees engine behavior changes — so it cannot detect the previously-passing violations these tasks introduce; today that gap is closed by the documented rule and human classification, which REQ-902 would remove.
- External research evidence: Not applicable.
- Why it matters: Under REQ-902 as written, trains B, C, and D each carry a package advance and therefore classify as exactly MINOR, shipping consumer-breaking behavior on the moving `v5` tag that every `@v5` consumer inherits without opting in. That inverts the repository's headline compatibility guarantee, and it does so silently, because `check-release` would return green.
- Recommended action for the authoring agent: Add an explicit previously-passing analysis to each corrective task's acceptance criteria, naming whether it can flip a consumer outcome. Then either state in REQ-902 that the previously-passing rule remains an unconditional MAJOR override above the package-composition rule — and make that the first assertion in T30's acceptance and in T30.1's matrix — or, if the owner intends trains B/C/D to ship these behavior changes, restructure §8 so they land as a catalog-major transition rather than as MINOR releases. This decision belongs in §9 Owner Gates; it is currently absent from that table.
- Suggested validation: `project-standards check-release` against each train's candidate catalog (run only after implementation), plus a T30.1 matrix case asserting that a previously-passing-to-failing engine change is rejected at MINOR.

### CR-003: T32 scopes retirement to two consumers, but three still owe protected merges

- Severity: High
- Status: Confirmed
- Adversarial angle: A count assertion about external repositories is verifiable directly against those repositories.
- Plan reference: REQ-904, T32 (goal, files, acceptance), §8 "Owner TODOs", §11, T29 `depends_on`.
- Finding: T32 names only `website-aboutme` and `website-l3digital.net`. Live branch evidence shows `hw-radar` also still owes its protected merge, and its `main` has no v5 control plane at all: `.standards/lock.toml` is absent and there are zero `docs/handoff/` files on `main`, while `dev` is 130 commits ahead. `docmend` has since been merged (`main...dev` is 0/0, `.standards/lock.toml` present on `main`), which is presumably why the plan reduced the ledger's four to two — but the reduction dropped `hw-radar` as well, without evidence. The canonical ledger also records two further residuals in neither the plan nor T32: `~/scripts` needs `reconcile --apply`, and `llm-wiki` has two consumer-side shape overflows.
- Repository evidence: `git -C /home/chris/projects/hw-radar rev-list --left-right --count main...dev` returns `0 130`; `git cat-file -e main:.standards/lock.toml` fails (absent) and `git ls-tree -r --name-only main | grep -c docs/handoff/` returns 0. For `docmend`, the same commands return `0 0`, lock present, 13 handoff files. `website-aboutme` and `website-l3digital.net` each return `0 2` with lock absent on `main` — the plan is correct about those two. `docs/research/2026-07-09-agent-handoff-retirement-inventory.md:75,80,107` names all four consumers plus the `~/scripts` and `llm-wiki` residuals; `docs/TODO.md` still carries the unmodified four-consumer note.
- External research evidence: Not applicable.
- Why it matters: T29 depends on T32, and §11 asserts "the two remaining Agent Handoff consumers are verified retired" as a Definition-of-Done clause. Both gates pass while `hw-radar`'s default branch remains entirely unmigrated, so the program declares consumer retirement complete when it is not. §8's "1–3 days plus protected-branch review latency" is also understated: `hw-radar` needs a 130-commit protected merge, not a two-commit one.
- Recommended action for the authoring agent: Correct T32 to name three consumers, and state `docmend`'s completion as verified with its evidence so the reduction from the ledger's four is auditable. Add an explicit disposition for `~/scripts` (`reconcile --apply`) and `llm-wiki` (consumer-side shape overflows) — either fold them into T32 or record them in §3.2 as deliberate exclusions. Update §11 and §8 to match, and re-scope the effort estimate for the `hw-radar` merge.
- Suggested validation: For each named consumer, `git rev-list --left-right --count main...<authoritative-branch>` and `git ls-tree -r --name-only main -- .standards/lock.toml`, then `project-standards agent-handoff validate --repo .` and `drift-check --repo .` on the merged branch (run only after implementation).

### CR-004: The documented entry point T1 is unreachable — T1 depends on T30

- Severity: High
- Status: Confirmed
- Adversarial angle: The plan's own dependency graph should agree with the entry point the repository's work queue advertises.
- Plan reference: T1 `depends_on: [T30]`, §6 row T1, §2 strategy steps 1–2, Phase P1 versus Phase P9.
- Finding: T1 declares `depends_on: [T30]`, and T30 sits in Phase P9, the last phase. The ready set at program start is therefore `{T30, T32}`, not `{T1}`. Meanwhile `docs/TODO.md` — modified in the working tree as part of this same change — instructs the implementer to "Execute the open-issue resolution program; begin with T1, the Agent Handoff 1.8 release", and `docs/STATUS.md`, also modified in the working tree, says "T1 is ready". Both are false against the plan as written. The same inversion recurs at T21, which depends on T31 (also P9). §2's strategy is internally consistent — step 1 does say to align the release-level contract first — but the P1…P9 phase numbering communicates the opposite ordering, and the two documents an implementing agent actually reads at session start communicate the opposite again.
- Repository evidence: The plan's own `depends_on` fields (T1 `[T30]`, T21 `[T16, T17, T18, T19, T20, T31]`, T30 `[]`, T32 `[]`). `git diff docs/TODO.md` shows the "begin with T1" line added in this working tree; `git diff docs/STATUS.md` shows "T1 is ready" added in the same tree. `scripts/plan.py:492` implements a `next` command that prints the ready set from `depends_on`, so a tool-driven session and a document-driven session will disagree on the first task.
- External research evidence: Not applicable.
- Why it matters: An implementing agent following `docs/TODO.md` starts T1 and publishes Agent Handoff 1.8 before the release-classification contract is aligned — which is precisely the ordering §2 step 1 exists to prevent, and which would classify that release under the contract T30 is meant to replace. This is the single most likely execution error in the whole program, because it is what the entry-point documents actively instruct.
- Recommended action for the authoring agent: Renumber the phases so prerequisites precede dependants — move T30 and T32 into P1 (or a new P0) and renumber the rest — so phase order and dependency order agree. Then correct the "begin with T1" line in `docs/TODO.md` and the "T1 is ready" line in `docs/STATUS.md` to name the true ready set. If T1's dependency on T30 is not actually intended and 1.8 may ship under the current contract, delete the edge and say so explicitly in §2.
- Suggested validation: `uv run python3 scripts/plan.py next docs/plans/2026-08-01-open-issue-resolution-program-plan.md`, and confirm its output matches the entry point named in `docs/TODO.md` and `docs/STATUS.md`.

## Non-blocking issues

### CR-005: REQ-902 converts a classification floor into an equality and exceeds the question its cited source asks

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Compare the proposed rule both to the implementation it replaces and to the owner question the plan cites as its source.
- Plan reference: REQ-902 ("Source: `docs/TODO.md`; owner decision 2026-08-01"), T30 acceptance, T30.2, T30.5.
- Finding: Three distinct mismatches. First, `docs/TODO.md` asks a narrower question than REQ-902 answers: "Define whether owner-designated release levels may **exceed** `check-release` and `meta/versioning.md` classification" — that is about permitting a *higher* level than computed, whereas REQ-902 redefines the computation itself. Second, the working-tree `docs/TODO.md` still carries that line unchanged, so the cited source does not record the decision REQ-902 attributes to it (the same applies more weakly to REQ-903, whose TODO line is still phrased as pending authorization). Third, today's implementation treats `required` as a floor — `_release_boundary_error` only rejects a release *below* the computed level, and returns `None` unconditionally when `required` is PATCH — whereas T30's acceptance demands "exactly MINOR" and "exactly PATCH". Converting a floor to an equality newly forbids a legitimate case: `meta/versioning.md:116` classifies "a new opt-in flag or command" on the Validator CLI as MINOR, and the Reusable workflow row does the same for a new optional input, but neither advances a standard package, so REQ-902 would force them to PATCH.
- Repository evidence: `docs/TODO.md` "Maintenance" section, first bullet (unchanged in `git diff`); `src/project_standards/package_contract/release.py:145` (`required` initialized to PATCH), `:267-290` (`_release_boundary_error`, with no PATCH branch), `:286-289` (the MINOR branch, which also rejects a major bump when only MINOR is required); `meta/versioning.md:116` (Validator CLI MINOR column).
- External research evidence: Not applicable.
- Why it matters: T30.2 asks the implementer to confirm RED failures "expose the current highest-severity/minimum-floor contract". "Minimum floor" is accurate; "highest-severity" describes `meta/versioning.md`'s documented rule, not `classify_catalog_diff`, which never sees engine changes. An implementer working from that characterization will look for a highest-severity mechanism in `release.py` that is not there, and may widen the change while searching for it — the outcome T30.5 explicitly tries to avoid.
- Recommended action for the authoring agent: Restate T30's acceptance in floor-versus-equality terms and say which one is intended; if equality is intended, add explicit carve-outs for engine-only MINOR cases from `meta/versioning.md:116`. Correct T30.2's description of the current contract to distinguish the documented rule from the implemented catalog-diff classifier. Record the actual 2026-08-01 owner decisions in `docs/TODO.md` (or cite the real record) so REQ-902 and REQ-903's `Source` columns resolve.
- Suggested validation: Read `_release_boundary_error` alongside T30.1's proposed matrix and confirm each row asserts the intended relation; `project-standards check-release` on an engine-only candidate (run only after implementation).

### CR-006: No rollback or withdrawal path for a defective published train

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Ask what happens after a train ships and turns out to be wrong — the plan's risk table should answer it.
- Plan reference: §10 (R-001 through R-008), §11, T8.6, T15.6, T21.6, T28.6.
- Finding: The plan defines four publication gates and no recovery path from any of them. §10 has no rollback risk at all — R-005 covers premature issue closure, not a defective release. This matters more than usual here because `meta/versioning.md:160` makes full-version tags immutable ("never deleted, moved, or repointed once pushed"), and `:161` describes the moving `vMAJOR` tag as tracking the newest release, so every `@v5` consumer inherits a train on publication with no opt-in step.
- Repository evidence: `meta/versioning.md:160-161` (tag immutability and the moving-major delete-and-re-push procedure); `meta/versioning.md:194` (`@vMAJOR` described as the recommended consumer pin); plan §10, which contains no rollback entry.
- External research evidence: Not applicable.
- Why it matters: The recovery mechanism does exist — repoint the moving `v5` tag to the prior release via the documented delete-and-re-push — but it is not named anywhere in the plan, so an operator discovering a bad train mid-program has to rediscover it under pressure. Combined with CR-002, the probability that a train needs withdrawal is not negligible.
- Recommended action for the authoring agent: Add a rollback risk to §10 with the moving-tag repoint as its mitigation, and add a rollback-rehearsal step to the `.6 Verify Task` sub-task of T8, T15, T21, and T28 — at minimum, confirm before publication that the prior release's tag and assets are intact and that the repoint procedure has been read.
- Suggested validation: `git tag --list 'v5*'` and `gh release list` before each publication gate to confirm the fallback target exists.

### CR-007: The #84 transient investigation is sequenced after three trains that depend on installed-wheel probes

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Check whether a known-flaky mechanism is relied upon by tasks scheduled before the task that investigates it.
- Plan reference: T23 (`depends_on: [T15]`, phase P5), T1.4, T8.4, T15.4, T21.4, §8 ("Investigation | #84 | 1–2 days before fix estimate").
- Finding: Issue #84 is a transient crash importing `yaml.scanner` during `reconcile --json`, which the plan itself frames as possibly caused by missing or partial installed bytes (T23.2: "prove missing/partial installed bytes if reproduced"). T23 is scheduled after T15, but T1, T8, and T15 all qualify their releases through fresh-wheel extraction and installed reproductions — exactly the install-integrity surface #84 implicates. If the transient is real and install-related, it can produce spurious failures or, worse, spurious passes in three qualification gates before anyone investigates it.
- Repository evidence: Plan T1.4 ("run source and installed-wheel harness probes"), T8.4 ("run package and installed-wheel checks"), T15.4 ("run fresh candidate migration/adapter/planner probes"), §3.3 ("Build and extract a fresh candidate wheel for installed-authority checks"); T23's own `depends_on: [T15]`.
- External research evidence: Not applicable.
- Why it matters: A qualification gate that can fail for reasons unrelated to the train under test erodes the evidence value of every closure decision made through it, and §11 requires "fresh installed probes" as a Definition-of-Done clause.
- Recommended action for the authoring agent: Either move T23's bounded reproduction matrix ahead of T1 — it is estimated at 1–2 days and has no dependency on any correction — or state explicitly in T1, T8, and T15 how a probe failure is distinguished from the #84 transient, so an intermittent failure is not silently retried into a green result.
- Suggested validation: Run T23's isolated install matrix before the first qualification gate (run only after implementation).

### CR-008: Appendix A omits every qualification, specification, and closeout task

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Cross-check the traceability appendix against the task list and the requirements table.
- Plan reference: Appendix A, REQ-900, REQ-901, §11.
- Finding: Appendix A has no row for T8, T15, T21, T24, T26, T28, or T29, and neither REQ-900 nor REQ-901 appears in the Requirement(s) column anywhere in the appendix. Both are `must` requirements in §4. The omission is systematic — every corrective task has a row and every non-corrective task does not — which suggests the appendix was built from the corrective tasks only.
- Repository evidence: Plan Appendix A (25 rows: TC-T1, T2, T3, T4, T5, T6, T7, T9–T14, T16–T20, T22, T23, T25, T27, T30, T31, T32) versus §4 (REQ-900 mapped to T1, T8, T15, T21, T28; REQ-901 mapped to T29).
- External research evidence: Not applicable.
- Why it matters: `scripts/plan.py validate` enforces that requirements-table IDs are covered by some task's `requirements:` field, which they are — so this gap passes the validator silently. The two requirements with no test traceability are precisely the ones governing release integrity and program closure, the hardest ones to prove informally.
- Recommended action for the authoring agent: Add rows for the qualification tasks (release-battery and artifact-parity proofs), the two specification tasks (spec and child-plan validation), and T29 (the live issue-set reconciliation query), each mapped to REQ-900 or REQ-901.
- Suggested validation: Confirm every `must` requirement in §4 appears at least once in Appendix A's Requirement(s) column.

### CR-009: The working-tree preservation constraint names one file but four are dirty

- Severity: Medium
- Status: Confirmed
- Adversarial angle: A preservation constraint is only as good as its enumeration of what must be preserved.
- Plan reference: §3.3 first constraint ("Preserve the existing `docs/adoption-prompt.md` working-tree change and later unrelated work").
- Finding: `docs/adoption-prompt.md` is one of four modified tracked files. `docs/STATUS.md`, `docs/TODO.md`, and `docs/handoff/specs-plans.md` are also modified, and `docs/handoff/sessions/2026-08.md` is untracked. Three of those four carry changes this plan itself depends on or must correct (see CR-004), so an implementing agent that reverts or overwrites them loses the plan's own entry-point wiring.
- Repository evidence: `git status --short` returns ` M docs/STATUS.md`, ` M docs/TODO.md`, ` M docs/adoption-prompt.md`, ` M docs/handoff/specs-plans.md`, `?? docs/handoff/sessions/2026-08.md`, `?? docs/plans/2026-08-01-open-issue-resolution-program-plan.md`.
- External research evidence: Not applicable.
- Why it matters: The repository's non-negotiables forbid `git add .`, so staging is by explicit name; a constraint that enumerates one of five in-flight changes invites an incomplete or destructive first commit.
- Recommended action for the authoring agent: Enumerate all in-flight paths in §3.3, noting which are this plan's own wiring (`docs/STATUS.md`, `docs/TODO.md`, `docs/handoff/specs-plans.md`, `docs/handoff/sessions/2026-08.md`) and which are genuinely unrelated (`docs/adoption-prompt.md`).
- Suggested validation: `git status --short` at the start of the first implementation session, compared against §3.3's list.

### CR-010: `docs/STATUS.md` describes a 29-task plan; the plan defines 32

- Severity: Low
- Status: Confirmed
- Adversarial angle: Check the plan's count assertions against the documents that cite it.
- Plan reference: §7 (T1–T32), Phase P9; `docs/STATUS.md` working-tree change.
- Finding: The added `docs/STATUS.md` line reads "A 29-task master plan groups the 23 open issues into bounded correction, tooling, investigation, and feature trains". The plan defines 32 tasks — the three owner-approved TODO tasks in Phase P9 (T30, T31, T32) appear to have been added after that line was written.
- Repository evidence: `git diff docs/STATUS.md` (the added "29-task" line); plan §7 headings T1 through T32.
- External research evidence: Not applicable.
- Why it matters: §11 requires that "Status, TODO, handoff, roadmap, changelog, release notes, and GitHub agree", so this is a Definition-of-Done violation present at authoring time, and it is the same working-tree file implicated in CR-004.
- Recommended action for the authoring agent: Correct the count to 32 in the same edit that fixes the entry-point line from CR-004.
- Suggested validation: `rg -c '^#### T[0-9]+:' docs/plans/2026-08-01-open-issue-resolution-program-plan.md` compared against the count in `docs/STATUS.md`.

## Missing considerations

- **Previously-passing classification per corrective task** — blocking (CR-002). No task states whether its fix flips a consumer outcome, yet at least T5, T6, T7, T12, and T19 plausibly do.
- **Disposition for #109** — blocking (CR-001). Also missing: a stated policy for issues opened *during* the program's 58–112 day span, beyond Appendix B's owner-approval clause.
- **Third consumer and the two residuals** — blocking (CR-003). `hw-radar` has no task; `~/scripts` and `llm-wiki` have neither a task nor an exclusion.
- **Rollback and release withdrawal** — non-blocking (CR-006).
- **Traceability for release-integrity and closeout requirements** — non-blocking (CR-008).
- **Owner-decision records** — non-blocking (CR-005). REQ-902/903/904 cite `docs/TODO.md` as source, but the TODO still poses them as open questions; the actual 2026-08-01 decision text is not recorded anywhere in the repository.
- **Owner gate for the release-classification change** — non-blocking. §9 lists five owner gates (T7, T5, T19, T24, T26) but not T30, despite REQ-902 being an owner-policy decision with the widest blast radius in the program.
- **Scope inheritance for T25 and T27** — non-blocking. Both declare files "frozen by the approved specification and child plan", so §8's 5–10 and 10–20 day estimates are unbounded by anything in this document; that is inherent to a program plan, but the estimates should be marked provisional.
- **Real-tool oracle version pinning** — non-blocking. T16, T17, T18, and T19 assert behavior of Prettier, Ruff, and BasedPyright. The repository pins `prettier@3.8.3` and `markdownlint-cli2@0.23.1` exactly, but `pyproject.toml` pins Ruff only as `ruff>=0.14.11` and BasedPyright with no floor at all, so a "real-tool parity" oracle can drift under the plan without any task noticing.

## Internet research performed

No internet research was required. Every material claim in the plan is internal: repository file paths, package versions inside `standards/` and `src/project_standards/payloads/`, this repository's own release contract in `meta/versioning.md`, GitHub issues in this repository, and consumer repositories on the local filesystem. All resolved against local evidence or the GitHub CLI. The plan makes no assertion about external library behavior, API contracts, upgrade procedures, or version compatibility that could be stale.

One external-behavior dependency exists but is not a plan claim: issue #109 reports `uv lock` rejecting a generated `pyproject.toml` with `No project table found` under uv 0.11.6. If #109 is admitted into scope per CR-001, verifying current uv behavior for tool-only `pyproject.toml` files would warrant research at that point.

## Items the authoring agent should verify before correcting the plan

- Re-query the open issue set and record the exact freeze timestamp, then decide #109's disposition.
- Confirm `hw-radar`'s `main` state and whether its 130-commit `dev` delta is entirely Agent Handoff work or mostly unrelated application work — the answer changes T32's effort estimate materially.
- Confirm `docmend`'s retirement is genuinely complete (lock present, `main...dev` 0/0) and record that evidence, so the reduction from the ledger's four consumers is auditable.
- Confirm current `~/scripts` and `llm-wiki` state before writing their disposition.
- Locate or create the durable record of the 2026-08-01 owner decisions behind REQ-902, REQ-903, and REQ-904; `docs/TODO.md` does not currently contain them.
- Read `_release_boundary_error` in `release.py` and settle floor-versus-equality before writing T30.1's matrix.
- Decide whether T1's dependency on T30 is intended, then reconcile the plan, `docs/TODO.md`, and `docs/STATUS.md` to one entry point.

## Suggested corrections for the authoring agent's plan

1. Restate §2's inventory claim with the true open-issue count and an exact freeze timestamp; give #109 an explicit admission or exclusion; tighten Appendix B's boundary from a date to a timestamp.
2. Add a previously-passing classification line to each corrective task's acceptance, and make the previously-passing rule an unconditional override in REQ-902 and T30's acceptance — or move the affected trains to a catalog-major transition in §8.
3. Add T30 to §9 Owner Gates with its working assumption stated.
4. Correct T32 to three consumers; add explicit dispositions for `~/scripts` and `llm-wiki`; update §8's effort and §11's Definition-of-Done wording; record `docmend`'s completion evidence.
5. Renumber the phases so T30 and T32 precede P1, and fix the entry-point lines in `docs/TODO.md` and `docs/STATUS.md` (including the 29-task count).
6. Restate T30's acceptance in floor-versus-equality terms with carve-outs for engine-only MINOR cases; correct T30.2's characterization of the current contract.
7. Add a rollback risk to §10 and a fallback-verification step to the `.6` sub-task of T8, T15, T21, and T28.
8. Move T23 ahead of T1, or state how a probe failure is distinguished from the #84 transient at each qualification gate.
9. Add Appendix A rows for T8, T15, T21, T24, T26, T28, and T29, mapped to REQ-900 and REQ-901.
10. Enumerate all five in-flight working-tree paths in §3.3.
11. Pin or assert the Ruff and BasedPyright versions the T16–T19 real-tool oracles are written against.

## Read-only validation performed

- `pwd`, `git branch --show-current`, `git status --short` — established the working directory, the `testing` branch, and the five in-flight paths behind CR-009.
- Existence test over 23 plan-named paths — confirmed every source module, test file, script, standard directory, and document the plan references exists; no path claim was falsified.
- `ls` over `standards/*/versions/` and `src/project_standards/payloads/*/` — confirmed Agent Handoff 1.8 exists as both standard and payload, Python Tooling's latest is 1.10 (so T31's "planned successor" is created by P4, not pre-existing), and Markdown Tooling's latest is 1.11.
- `rg` over `standards/catalog.md` — confirmed `agent-handoff@1.8` carries role `default`, validating T1's release-qualification framing.
- `gh issue list --state open` and `gh issue view 109` — established 24 open issues and #109's creation timestamp and content (CR-001).
- `gh issue list --state closed` — confirmed the six most recent closures all predate 2026-08-01, so §2's "no closures" claim holds for the refresh window even though the count does not.
- `git diff docs/TODO.md docs/STATUS.md` — established that the "begin with T1" and "29-task"/"T1 is ready" lines were added in this working tree (CR-004, CR-010) and that the release-level TODO question is unchanged (CR-005).
- `rg` over `docs/research/2026-07-09-agent-handoff-retirement-inventory.md` — established the canonical four-consumer ledger plus the `~/scripts` and `llm-wiki` residuals (CR-003).
- `git rev-list --left-right --count`, `git cat-file -e`, and `git ls-tree` across `hw-radar`, `docmend`, `website-aboutme`, `website-l3digital.net`, `~/scripts`, and `llm-wiki` — established which consumers still owe merges and which `main` branches lack a control plane (CR-003).
- `rg` and `sed -n` over `meta/versioning.md` — established the highest-severity rule, the Validator CLI classification row, and the previously-passing rule (CR-002, CR-005).
- Read `src/project_standards/package_contract/release.py:137-296` — established that `classify_catalog_diff` is composition-only and that `_release_boundary_error` enforces a floor, not an equality (CR-002, CR-005).
- Read `scripts/plan.py:1-63` and `:378-490` — established the validator's invariants so they could be checked manually without running it.
- `rg` over the plan for placeholders, requirement IDs, task IDs, and `depends_on` values — confirmed 32 tasks, 28 requirement IDs all covered, all dependency references resolvable, no unfilled placeholders.
- `rg` over `scripts/verify.sh` — established that the gate runs Prettier, markdownlint-cli2, Ruff, BasedPyright, coverage, and pip-audit, and that `--full` is the serial release-prep cross-check.
- `node_modules/.bin/markdownlint-cli2` over the repository — returned 0 issues across 1204 files, establishing that the previously recorded 463-error backlog is cleared and the per-task gate is a real signal.
- Read `.prettierrc`, `.prettierignore`, `.markdownlint-cli2.jsonc`, `.markdownlint.json`, and `.standards/config.toml` — established the formatting and frontmatter contracts this report itself must satisfy.

## Recommended implementation validation

- `uv run python3 scripts/plan.py validate docs/plans/2026-08-01-open-issue-resolution-program-plan.md` — confirms master and checklist invariants after the corrections. Run only after implementation; it touches the venv.
- `uv run python3 scripts/plan.py sync docs/plans/2026-08-01-open-issue-resolution-program-plan.md` — re-projects the existing `.project-pipeline/2026-08-01-open-issue-resolution-program/` checklists after renumbering. Run only after implementation; it writes checklist files.
- `uv run python3 scripts/plan.py next docs/plans/2026-08-01-open-issue-resolution-program-plan.md` — confirms the ready set matches the entry point named in `docs/TODO.md` and `docs/STATUS.md` (CR-004).
- `scripts/verify.sh` — the per-task gate. Run only after implementation; it writes coverage and temporary artifacts.
- `scripts/verify.sh --full` — the release-prep cross-check at each qualification gate. Run only after implementation.
- `project-standards check-release` against each candidate catalog — confirms classification under the corrected REQ-902 rule. Run only after implementation.
- `project-standards agent-handoff validate --repo .` and `drift-check --repo .` inside each consumer named by the corrected T32. Run only after implementation.
- `gh issue list --state open --limit 100 --json number,createdAt` immediately before execution and again at T29 — bounds inventory drift (CR-001).

## Final recommendation

The authoring agent should revise the plan using the findings above. The task decomposition, dependency structure, and file-level accuracy are sound and worth keeping — the corrections are to four factual premises (issue inventory, release classification, consumer scope, entry point) plus six smaller consistency and coverage gaps. Do not replace the plan.

## Review ledger for next loop

- Plan path: `docs/plans/2026-08-01-open-issue-resolution-program-plan.md`
- Audit round: 1
- Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-006, CR-007, CR-008, CR-009, CR-010
- Resolved issue IDs: none
- Superseded issue IDs: none
- Significant findings remaining: Yes
- Next audit should focus on: whether the previously-passing rule is now reconciled with REQ-902 and applied per corrective task (CR-002); whether the corrected consumer scope matches live branch state at re-audit time (CR-003); whether the phase renumbering, `docs/TODO.md`, and `docs/STATUS.md` now agree on one entry point (CR-004); whether #109 received an explicit disposition and the open-issue count still matches (CR-001); and whether the corrections introduced new dependency-graph or traceability inconsistencies.
