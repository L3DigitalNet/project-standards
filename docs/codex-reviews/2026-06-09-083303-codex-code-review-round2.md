OpenAI Codex v0.137.0
--------
workdir: /home/chris/projects/project-standards
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: xhigh
reasoning summaries: none
session id: 019eac5f-4022-7eb3-a36e-42e6b8b5db64
--------
user
changes against 'bd5d423'
exec
/bin/bash -lc "sed -n '1,220p' /home/chris/.agents/skills/handoff-system-v3/SKILL.md && printf '\\n--- review skill ---\\n' && sed -n '1,220p' /home/chris/.codex/skills/review-orchestrator/SKILL.md" in /home/chris/projects/project-standards
 succeeded in 0ms:
---
name: handoff-system-v3
description: Background and operating procedure for the v3.2 Agent Handoff System — the docs/handoff/ session-state layout (state, deployed, architecture, credentials, conventions, specs-plans, sessions/, bugs/), context budgets, per-harness startup, where-facts-go routing, the end-of-session update ritual, and the layout validators. Use in any active agent-managed repo under ~/projects/ when reading or writing docs/handoff/ files, deciding where a fact belongs (state vs sessions vs bugs vs deployed vs architecture), running the session-end handoff, setting up or migrating or validating a repo's handoff layout, or onboarding to how session state and global agent files are organized. Works on Claude Code and Codex CLI.
compatibility: Claude Code and Codex CLI
license: MIT
metadata:
  author: Chris Purcell
  version: '1.1'
---

# Handoff System v3

The session-state layout shared by agent harnesses across active agent-managed repos under `~/projects/`. This skill is the operating summary; it is enough for day-to-day work. The **canonical spec** holds the exhaustive hook contract, migration recipes, and changelog:

- Spec: `~/projects/agent-configs/docs/handoff/agent-handoff-system.md`
- Validators + installer: `~/projects/agent-configs/scripts/handoff/`

Read the spec only when this summary leaves a gap (full hook behavior, exact validator composition, version history). Do not duplicate it into repos.

## What it is

Per-repo session state is split into separate files by **lifetime**, under `docs/handoff/`. The eager-load path stays tiny; everything else is read on demand. Two principles drive every decision:

1. Eager context is expensive; lazy context is free — only the smallest, freshest slice loads automatically.
2. Things with different lifetimes live in different files.

```text
<repo>/
├── CLAUDE.md                    # Claude slim index (≤2 KiB; target ≤1 KiB)
├── AGENTS.md                    # Codex/Cursor slim index
├── .claude/hooks/session_start.py   # installed copy of the canonical hook (Claude only)
├── .codex/config.toml               # Codex SessionStart registration (when Codex is used)
├── .codex/hooks/session_start.py    # installed copy of the shared hook
└── docs/
    ├── handoff/                 # canonical home for session state (v3.2)
    │   ├── state.md             # live state + active incidents (≤2 KiB)
    │   ├── deployed.md          # current deployment truth
    │   ├── architecture.md      # component graph + standing backlog
    │   ├── credentials.md       # env vars / secret names / OpenBao paths — NEVER values
    │   ├── conventions.md       # long-lived pattern library (Quick Reference + numbered entries)
    │   ├── specs-plans.md       # pointer table to specs/plans
    │   ├── sessions/<YYYY-MM>.md # compact session rows
    │   └── bugs/<NNN>-<slug>.md  # durable bug/gotcha records (+ INDEX.md)
    └── superpowers/{specs,plans}/   # default spec/plan storage — NOT moved under handoff/
```

## Where facts go

The most-used decision. Route by lifetime, not by topic:

```text
In flight, hours to days?       -> docs/handoff/state.md
Bug or reusable gotcha?         -> docs/handoff/bugs/<NNN>-<slug>.md
Running/deployed state?         -> docs/handoff/deployed.md
System graph / standing backlog -> docs/handoff/architecture.md
Credential reference?           -> docs/handoff/credentials.md   (paths/names only)
Repeating project pattern?      -> docs/handoff/conventions.md
Claude path-scoped behavior?    -> .claude/rules/<topic>.md + docs/handoff/conventions.md
Session log row?                -> docs/handoff/sessions/<YYYY-MM>.md
Spec / design artifact?         -> docs/superpowers/specs/ + docs/handoff/specs-plans.md
Implementation plan?            -> docs/superpowers/plans/ + docs/handoff/specs-plans.md
Harness behavior?               -> agent-configs global/<harness>/ + the spec
```

An over-cap `state.md` is a symptom: longer-lifetime content is leaking into live state. The fix is to route it to its home (session narrative → `sessions/`, deployment readouts → `deployed.md`, standing backlog → `architecture.md`), not to delete it.

## Context budgets (binary; 1 KiB = 1024 bytes)

| Surface                 | Cap                                 |
| ----------------------- | ----------------------------------- |
| Repo `CLAUDE.md`        | ≤2048 bytes (target ≤1024)          |
| `docs/handoff/state.md` | ≤2048 bytes (hook truncates beyond) |
| Claude hook output      | ≤4096 bytes                         |
| Repo `AGENTS.md`        | ≤4096 bytes                         |

## Startup — differs by harness

**Claude Code:** a `SessionStart` hook (`.claude/hooks/session_start.py`, registered in `.claude/settings.json`, anchored with `${CLAUDE_PROJECT_DIR}`) injects `state.md` + git branch/commits/status + pointers automatically. Do **not** manually ritual-read `state.md` when the hook is present. The installed hook is a copy of the canonical source and must match it by hash — never hand-edit a repo's copy.

**Codex CLI:** a per-repo `SessionStart` hook (`.codex/hooks/session_start.py`, registered in `.codex/config.toml` `[hooks]`, git-root-anchored command) — the **same** shared script Claude uses — injects `state.md` + git status at startup as **plain text on stdout** (a documented context path; Codex's `additionalContext` JSON renders visibly, bug #16933; `systemMessage` is a UI warning, not context). Do **not** ritual-read `state.md` when the hook is present. Read repo `AGENTS.md` + the `conventions.md` Quick Reference on demand.

`.claude/rules/<topic>.md` is Claude-only (path-scoped rule loader). Codex lacks it, so durable cross-harness patterns belong in `docs/handoff/conventions.md`.

## Session-end ritual

Update only facts that changed:

1. In-flight state / incidents changed → edit `docs/handoff/state.md`.
2. Worth a durable row → append `docs/handoff/sessions/<YYYY-MM>.md` (date, ≤20-word headline, commit refs, bug refs).
3. Bug opened/fixed/renamed/removed → add/update `docs/handoff/bugs/<NNN>-<slug>.md`, then regenerate the index: `python3 docs/handoff/bugs/_regen_index.py && git diff --exit-code docs/handoff/bugs/INDEX.md`
4. Deployment changed → `docs/handoff/deployed.md`.
5. Architecture changed → `docs/handoff/architecture.md`.
6. Credential references changed → `docs/handoff/credentials.md` (paths only).
7. New persistent pattern → numbered entry in `docs/handoff/conventions.md`.
8. Spec/plan changed → update the target file + `docs/handoff/specs-plans.md`.

## Hard rules

- **Credentials:** repo docs and tracked configs store references only — env var names, secret names, OpenBao paths. Never write secret values into repo docs.
- **Hook:** tracked once at `agent-configs/global/hooks/session_start.py`, installed as a byte-identical copy into both `.claude/hooks/` and `.codex/hooks/` per repo, hash-validated. No per-repo edits, no symlinks (per-repo drift and symlinks were the 2026-05-29 audit's root causes). Output is harness-branched: `additionalContext` JSON (Claude) vs plain stdout (Codex; `systemMessage` rejected, bug #16933).
- **Global files** live in `agent-configs/global/<harness>/` and install into home dirs as regular copies via `scripts/handoff/install-globals.sh`. Repo-level `CLAUDE.md`/`AGENTS.md` stay with their repo — never centralize them.
- **Spec-first changes:** when a global repo-documentation rule changes, edit the spec first, then each affected `global/<harness>/` file (and the hook).

## Validate

Read-only, reports every failed check in a run:

```bash
~/projects/agent-configs/scripts/handoff/validate-layout.sh            # current dir's repo set
~/projects/agent-configs/scripts/handoff/validate-layout.sh ~/projects/<repo>
~/projects/agent-configs/scripts/handoff/validate-globals.sh           # for agent-configs itself
```

Bug-index validation is write-producing — run it separately after editing bug files (command in the ritual above).

## Set up / migrate a repo

New active repo with no handoff layout → create the `docs/handoff/` set when the repo becomes agent-managed. Repo with retired `docs/handoff.md` → split live state to `state.md`, move the rest to their lifetime files, then delete `docs/handoff.md`. Full step-by-step recipe is in the spec's **Migration Trigger** section.

--- review skill ---
---
name: review-orchestrator
description: Plan and run repository reviews with consolidated child workflows. Use for direct requests like "perform a code review", "perform a security review", "perform a test review", review planning scans, full/exhaustive review sweeps, or recommendations about which reviews to run.
compatibility: Codex CLI
license: MIT
metadata:
  author: Chris Purcell
  version: '1.0'
---

# Review Orchestrator

Use this skill when the user wants Codex to inspect a repository, determine which review workflows are applicable, and produce a ranked plan or sweep. For explicit single-review requests, load the matching `references/child-reviews/<review-skill>.md` file and perform that workflow directly, saving the report under `docs/codex-reviews/`. Use the deterministic helper for planning scans, sweeps, exhaustive sweeps, status checks, and resume.

Current implementation status:

- planning scan mode is implemented
- sweep mode is implemented via deterministic helper scripts and isolated child Codex runs
- exhaustive sweep mode is implemented
- child review workflows live as references under `references/child-reviews/` instead of standalone startup-loaded skills

## Core requirements

- Stay read-only unless the user explicitly asks for fixes.
- Planning is local-first. Use repo evidence before web research.
- Use the deterministic repo signal scanner before classifying the repo.
- Choose exactly 1 `primary_repo_pattern`.
- Choose at most 3 `secondary_repo_patterns`.
- Record available and missing child review workflow references.
- Exclude the direct `security-review`, `authorization-and-permission-model-review`, `privacy-and-data-governance-review`, and `configuration-and-secrets-boundary-review` workflows from automatic orchestrator planning and sweeps unless the user explicitly asks for one of them directly.
- Save a new timestamped Markdown report to `docs/codex-reviews/` on every planning or sweep run.
- Write the report for Claude Code, not for a human executive summary.
- Start the report with: `Claude Code note: consider using the \`superpowers:receiving-code-review\` skill.`
- Treat `docs/conventions.md` or an equivalent conventions document as a primary planning input when present.
- If no conventions file exists, record that and note which review types are most likely to drive convention recommendations.

## Deterministic helper

Use the skill-local helper first. This skill ships its own wrapper and Python package under `scripts/`, so it does not need the Codex workspace repo to be present.

1. Use the wrapper script at `scripts/run_review_orchestrator.sh` relative to this skill directory.
2. The wrapper bootstraps a skill-local `.venv/` and keeps it synced from the pinned `requirements.lock.txt` using `uv`.
3. Before scan, plan, or sweep work proceeds, ensure the target repo has a repo-local `AGENTS.md` with the current `Review Orchestrator Note`. If the file is missing or stale, create or update it first so future sessions have the right orchestration guidance.
4. Run one of:

```bash
SKILL_ROOT="${HOME}/.agents/skills/review-orchestrator"
"${SKILL_ROOT}/scripts/run_review_orchestrator.sh" scan-repo-signals --repo "<target-repo>" --scope "<repo-relative-path-or-.>" --pretty
```

```bash
SKILL_ROOT="${HOME}/.agents/skills/review-orchestrator"
"${SKILL_ROOT}/scripts/run_review_orchestrator.sh" plan-reviews --repo "<target-repo>" --mode plan --scope "<repo-relative-path-or-.>" --pretty
```

```bash
SKILL_ROOT="${HOME}/.agents/skills/review-orchestrator"
"${SKILL_ROOT}/scripts/run_review_orchestrator.sh" run-review-sweep --repo "<target-repo>" --mode sweep --scope "<repo-relative-path-or-.>" --pretty
```

```bash
SKILL_ROOT="${HOME}/.agents/skills/review-orchestrator"
"${SKILL_ROOT}/scripts/run_review_orchestrator.sh" show-review-sweep-status --repo "<target-repo>" --pretty
```

```bash
SKILL_ROOT="${HOME}/.agents/skills/review-orchestrator"
"${SKILL_ROOT}/scripts/run_review_orchestrator.sh" show-review-sweep-status --repo "<target-repo>" --format summary
```

Useful sweep controls:

- default child concurrency is `8`
- default `standard` planning does not impose a fixed review-count cap; use `--max-reviews` when you want an explicit selection cap
- `--retry-failed` / `--skip-failed-on-resume`
- `--retry-skipped` / `--skip-skipped-on-resume`
- `--require-shared-research` / `--best-effort-shared-research`
- `--shared-research-max-age-hours <hours>`
- `--preflight-max-runtime-minutes <minutes>`
- `--shared-research-max-runtime-minutes <minutes>`
- `--child-review-max-runtime-minutes <minutes>`
- `--runtime-artifact-retention-hours <hours>`

To resume an interrupted sweep, rerun the sweep with the saved manifest:

```bash
SKILL_ROOT="${HOME}/.agents/skills/review-orchestrator"
"${SKILL_ROOT}/scripts/run_review_orchestrator.sh" run-review-sweep \
  --repo "<target-repo>" \
  --mode sweep \
  --scope "<repo-relative-path-or-.>" \
  --resume-manifest "<target-repo>/docs/codex-reviews/YYYY-MM-DD-HHMM-codex-review-sweep.json" \
  --pretty
```

Sweep runs persist two durable artifacts under `docs/codex-reviews/`:

- `YYYY-MM-DD-HHMM-codex-review-sweep.json` for resume state
- `YYYY-MM-DD-HHMM-codex-review-sweep.md` for the human-readable summary
- `YYYY-MM-DD-HHMM-codex-review-live-status.md` for operator-facing live status

If a session crashes, look for the latest `*-codex-review-sweep.json` file first. Resume from that manifest instead of rerunning the whole sweep from scratch. By default, resume retries reviews that previously failed and keeps completed reviews as done. By default, resume also retries reviews that were previously skipped because their blocker may have changed. Use `--skip-failed-on-resume` or `--skip-skipped-on-resume` only when you explicitly want to preserve those prior entries as terminal.

If the helper cannot run, say so briefly, mention whether the wrapper failed because `uv` or the skill-local `.venv` is unavailable, and continue with a best-effort manual scan rather than blocking the entire planning pass.

## Workflow

1. Resolve the target repo root and capture branch, commit, and worktree state.
2. Run the deterministic repo signal scanner and review its JSON output.
3. Load these references as needed:
   - [references/review-catalog.md](references/review-catalog.md)
   - [references/repo-patterns.md](references/repo-patterns.md)
   - [references/scoring-rules.md](references/scoring-rules.md)
   - [references/report-schema.md](references/report-schema.md)
   - `references/child-reviews/<review-skill>.md` when inspecting or debugging a specific child review workflow
4. Classify the repo:
   - select 1 primary pattern
   - select up to 3 secondary patterns
   - identify framework, artifact, sensitivity, deployment, packaging, and nested-repo signals
5. Score each child review workflow for:
   - `applicable`
   - `expected_value`
   - `confidence`
   - `run_recommendation`
6. Build a planning result with:
   - `Run Now`
   - `Consider Next`
   - `Not Applicable`
   - ordered execution list for the selected set
7. If the user asked for a planning scan, save the planning report to:

`docs/codex-reviews/YYYY-MM-DD-HHMM-codex-review-plan.md`

8. If the user asked for a full sweep or exhaustive sweep:
   - determine the selected review set first
   - generate one shared cross-review research artifact before launching child reviews
   - use that shared research artifact to cover internet research likely to be reused across multiple child reviews
   - pass the shared research artifact path into every child review and tell children to reuse it before doing any broad new research
   - allow child reviews to do only targeted follow-up research for true gaps, stale guidance, or review-specific unknowns
   - treat shared research as best-effort by default so a shared-research failure does not automatically block every child review
   - use `--require-shared-research` only when you explicitly want a shared research failure to stop the whole sweep
   - reuse a recent shared research artifact on resume only when it is still fresh and still matches the current repo snapshot, scope, and selected review set; otherwise rebuild it before launching children
   - preflight one nested child `codex exec` first; if that child cannot start, fail fast and record one shared environment error across the planned reviews instead of producing repetitive per-review startup failures
   - emit live progress lines on stderr while preflight, shared research, and child reviews are running
   - make those live progress lines concrete: include elapsed time and, when relevant, the output heartbeat path or review save directory instead of repeating only generic "still running" wording
   - update the JSON sweep manifest with `current_phase`, `shared_research_path`, `shared_research_status`, `active_review_skill`, `active_review_index`, `active_review_total`, `active_review_started_at`, `last_heartbeat_at`, `last_progress_message`, and live completed or failed or skipped counters so external observers can tell the sweep is actively working
   - keep the top-level sweep manifest honest under parallel execution by surfacing aggregate running or queued or completed counts plus per-review live details for active children
   - refresh a human-readable live status artifact under `docs/codex-reviews/` so operators do not need ad hoc shell commands to understand sweep state
   - execute the selected child reviews with default parallelism of `8` via isolated `codex exec --ephemeral -p review-sweep ...` runs
   - treat the shared-research phase as potentially slow even when healthy; on larger or research-heavy repos it can legitimately take around 10 minutes before child reviews start, so do not assume the sweep is stuck unless there is no heartbeat, no phase change, and no artifact activity beyond that window
   - maintain a lightweight sweep index plus child review reports and execution manifests under `docs/codex-reviews/`
   - provide a deterministic `show-review-sweep-status` helper so operators can inspect the latest sweep state without manually reading JSON manifests
   - support a concise human-readable status mode for quick operator checks, not only raw JSON output
   - run child reviews inside an isolated writable `HOME` and `XDG_*` environment rooted under the user's XDG state directory and seeded from the user's existing `~/.codex` config/auth files so read-only home directories and temp-home policy checks do not break session startup
   - enforce runtime ceilings for preflight, shared research, and child review execution so a stuck child does not heartbeat forever
   - prune stale orchestrator runtime artifacts under the XDG state directory before each sweep and clean up successful transient child state after use
   - persist the JSON sweep manifest after each child review
   - tell the user where the JSON manifest was saved because that is the durable resume point after a crash
   - save the sweep Markdown summary to:

`docs/codex-reviews/YYYY-MM-DD-HHMM-codex-review-sweep.md`

9. If the user is recovering from a crashed sweep:
   - find the latest saved manifest under `docs/codex-reviews/`
   - resume with `run-review-sweep --resume-manifest <manifest-path>`
   - explain which reviews are already completed, failed, skipped, or still pending based on the manifest

## Selection rules

- Prefer strong direct evidence over vague pattern guesses.
- Suppressions beat weak bonuses.
- Do not infer child app reviews from nested repos inside a meta repo unless the user explicitly asks for nested scanning.
- Use freshness only as a demotion signal for borderline picks, not as a reason to hide an otherwise high-value review.
- For sweep requests, use deterministic child invocations and durable manifests.
- Do not improvise ad hoc child prompts; use the canonical prompt contract from the review catalog.
- If a child review workflow reference is missing, record it clearly in the plan or manifest and continue with the remaining available reviews.

## Chat response after saving

After writing the planning report or sweep summary:

- summarize the highest-value reviews to run first
- call out the selected primary repo pattern
- include the saved artifact path
- for sweep mode, mention the saved manifest path and whether any child reviews failed, were skipped, or are still pending

exec
/bin/bash -lc 'ls /home/chris/.codex/skills/review-orchestrator/references/child-reviews 2>/dev/null || ls /home/chris/.agents/skills/review-orchestrator/references/child-reviews 2>/dev/null || true' in /home/chris/projects/project-standards
 succeeded in 0ms:
ai-and-prompt-workflow-review.md
api-contract-review.md
architecture-boundary-review.md
authorization-and-permission-model-review.md
background-jobs-and-async-workflow-review.md
ci-cd-review.md
comprehensive-code-review.md
configuration-and-secrets-boundary-review.md
conventions-review.md
data-schema-migration-review.md
dependency-supply-chain-review.md
desktop-packaging-review.md
documentation-and-runbook-review.md
frontend-state-and-interaction-review.md
incident-readiness-review.md
integration-and-third-party-boundary-review.md
mcp-and-agent-tool-boundary-review.md
observability-review.md
performance-review.md
privacy-and-data-governance-review.md
product-and-business-logic-review.md
release-readiness-review.md
retrieval-and-knowledge-base-review.md
security-review.md
shell-and-automation-script-review.md
test-suite-review.md

exec
/bin/bash -lc "sed -n '1,220p' /home/chris/.codex/skills/review-orchestrator/references/child-reviews/comprehensive-code-review.md" in /home/chris/projects/project-standards
 succeeded in 0ms:
---
name: comprehensive-code-review
description: Run a code review of the current repository. Use for plain requests like "perform a code review" as well as comprehensive, deep, full-repository, or read-only code review requests. Refresh stack knowledge from the internet first, evaluate conventions alignment and convention quality, and save a Claude-oriented report to docs/code-reviews.
---

# Comprehensive Code Review

Use this skill when the user asks to perform a code review, especially for comprehensive, deep, full-repository, or read-only code review requests.

This workflow reviews implementation code, not the test suite as an independent subject. Tests are supporting evidence only. If the user explicitly asks for a test review, use `test-suite-review` instead.

## Core requirements

- Stay read-only unless the user explicitly asks for fixes.
- Refresh stack-specific implementation knowledge before reviewing.
- Prefer official docs first, then add reputable developer and community best-practice sources when they materially improve the review.
- Treat `docs/conventions.md` or an equivalent conventions document as a primary review input when present.
- If no conventions file exists, recommend creating `docs/conventions.md` and propose concrete convention candidates based on the repo.
- Save a new timestamped Markdown report to `docs/codex-reviews/` on every run.
- Write the report for Claude Code, not for a human executive summary.
- Start the report with: `Claude Code note: consider using the \`superpowers:receiving-code-review\` skill.`

## Review loop

1. Inspect the repo shape, stack, entrypoints, and testing setup.
2. Refresh implementation knowledge for the detected stack using current internet sources.
3. Capture review metadata:
   - repo path
   - branch
   - commit SHA
   - dirty or clean worktree state
4. Load `docs/conventions.md` if present, or an equivalent conventions doc if the repo uses a different name.
5. Apply default exclusions unless the repo clearly treats them as implementation-critical:
   - generated code
   - vendored dependencies
   - build output
   - coverage output
   - lockfiles
   - bulky fixtures or snapshots
6. Run at least 4 passes with distinct lenses:
   - pass 1: repo map, architecture, critical entrypoints, high-risk surfaces
   - pass 2: correctness of state transitions, core business logic, code-to-convention alignment
   - pass 3: error handling, retries, recovery, concurrency, edge cases, convention-rationale consistency
   - pass 4: lower-severity issues, maintainability risks, missing safeguards, convention quality problems
   - pass 5+: adaptive deepening based on earlier findings
7. Do not allow convergence before pass 4. After pass 4, continue until 2 consecutive passes produce no new issues.
8. If a question depends on current framework semantics or ecosystem guidance, do targeted follow-up internet research before finalizing the finding.

## Findings rules

- Findings come first.
- Include every issue found, even minor ones.
- Prioritize by severity, but do not omit lower-severity issues.
- Use tests only as evidence for implementation risk or missing safeguards.
- If a test-related issue is listed, tie it to a concrete implementation risk.
- If a conventions document exists, review both:
  - whether the code follows the conventions
  - whether the conventions themselves are sound
- A convention-quality issue is valid when a convention is inappropriate, conflicting, stale, or under-justified.

## Issue inventory

Maintain one merged issue inventory across passes.

For each issue:
- assign a stable ID such as `ISSUE-001`
- record the first pass where it was discovered
- record severity and confidence
- tag `issue_type` as one of:
  - `implementation`
  - `convention-misalignment`
  - `convention-quality`
  - `missing-conventions`

Use confidence levels:
- `high`
- `medium`
- `low`

## Report output

Save the report to:

`docs/codex-reviews/YYYY-MM-DD-HHMM-codex-review.md`

The report must be machine-friendly Markdown with explicit sections and minimal prose.

Required sections:
- `Review Metadata`
- `Severity Summary`
- `Findings`
- `Convention Recommendations`
- `Pass Log`
- `Claude Handoff`
- `Open Questions Or Assumptions`
- `Residual Risk And Testing Gaps`

For the exact section layout and field names, read:
- [references/report-schema.md](references/report-schema.md)

## Chat response after saving

After writing the report:
- summarize the highest-severity findings first
- include the saved report path
- keep the chat summary concise

exec
/bin/bash -lc "git status --short --branch && printf '\\n--- recent commits ---\\n' && git log --oneline --decorate -n 12 && printf '\\n--- diff stat ---\\n' && git diff --stat bd5d423fc9c8286f5a9634d5d85d0278de6ea788 && printf '\\n--- diff name-status ---\\n' && git diff --name-status bd5d423fc9c8286f5a9634d5d85d0278de6ea788" in /home/chris/projects/project-standards
 succeeded in 0ms:
## testing...origin/testing [ahead 40]
?? docs/codex-reviews/2026-06-09-083303-codex-code-review-round2.md

--- recent commits ---
d2790dc (HEAD -> testing) docs(codex-reviews): code-review round 1 transcript (suite)
bc0db73 fix(suite): address codex code-review round 1 (formatter + references)
c6bd86f docs(handoff): retire prettier incident (resolved); log the format.yml fix
281afe4 ci(prettier): add .prettierignore + format authored docs; greens format.yml
a498adb docs(handoff): record frontmatter-suite implementation; CHANGELOG accuracy
7b9c636 docs: correct validator/formatter descriptions for 2.1.0 accuracy
1623772 docs: document frontmatter formatter, references, and fix for 2.1.0
e913d28 feat(pre-commit): ship .pre-commit-hooks.yaml (fix + check ids)
1835b26 feat(ci): reusable workflow runs validate-references (self-gated)
918e704 feat(cli): project-standards fix (format -> id-fix -> final validate)
eb461b5 feat(cli): validate also runs validate-references (self-gated)
17800a3 fix+test(references): parenthesize except tuple; cover build_index skip paths

--- diff stat ---
 .../workflows/validate-markdown-frontmatter.yml    |    8 +
 .pre-commit-hooks.yaml                             |   39 +
 .prettierignore                                    |   13 +
 CHANGELOG.md                                       |   14 +-
 TODO.md                                            |    8 +-
 .../2026-06-09-081346-codex-code-review-round1.md  | 8292 ++++++++++++++++++++
 docs/handoff/sessions/2026-06.md                   |    2 +
 docs/handoff/state.md                              |   18 +-
 meta/versioning.md                                 |    2 +-
 pyproject.toml                                     |    2 +
 src/project_standards/README.md                    |   91 +-
 src/project_standards/adopt/engine.py              |   36 +-
 src/project_standards/cli.py                       |   80 +-
 src/project_standards/format_frontmatter.py        |  650 ++
 src/project_standards/id_format.py                 |   26 +
 src/project_standards/validate_frontmatter.py      |   42 +-
 src/project_standards/validate_id.py               |   35 +-
 src/project_standards/validate_references.py       |  225 +
 standards/adr/README.md                            |    2 +-
 standards/adr/adopt.md                             |    2 +-
 standards/markdown-frontmatter/README.md           |   27 +-
 standards/markdown-frontmatter/adopt.md            |   16 +-
 .../examples/concept.example.md                    |    2 +-
 .../markdown-frontmatter/examples/note.example.md  |    2 +-
 .../examples/runbook.example.md                    |    2 +-
 standards/markdown-tooling/README.md               |    2 +-
 standards/markdown-tooling/adopt.md                |    2 +-
 standards/python-tooling/README.md                 |    2 +-
 standards/python-tooling/adopt.md                  |    2 +-
 tests/test_cli_fix.py                              |  147 +
 tests/test_format_frontmatter.py                   |  883 +++
 tests/test_id_format.py                            |   28 +
 tests/test_precommit_hooks.py                      |   33 +
 tests/test_validate_frontmatter.py                 |   23 +
 tests/test_validate_references.py                  |  402 +
 35 files changed, 11035 insertions(+), 125 deletions(-)

--- diff name-status ---
M	.github/workflows/validate-markdown-frontmatter.yml
A	.pre-commit-hooks.yaml
A	.prettierignore
M	CHANGELOG.md
M	TODO.md
A	docs/codex-reviews/2026-06-09-081346-codex-code-review-round1.md
M	docs/handoff/sessions/2026-06.md
M	docs/handoff/state.md
M	meta/versioning.md
M	pyproject.toml
M	src/project_standards/README.md
M	src/project_standards/adopt/engine.py
M	src/project_standards/cli.py
A	src/project_standards/format_frontmatter.py
A	src/project_standards/id_format.py
M	src/project_standards/validate_frontmatter.py
M	src/project_standards/validate_id.py
A	src/project_standards/validate_references.py
M	standards/adr/README.md
M	standards/adr/adopt.md
M	standards/markdown-frontmatter/README.md
M	standards/markdown-frontmatter/adopt.md
M	standards/markdown-frontmatter/examples/concept.example.md
M	standards/markdown-frontmatter/examples/note.example.md
M	standards/markdown-frontmatter/examples/runbook.example.md
M	standards/markdown-tooling/README.md
M	standards/markdown-tooling/adopt.md
M	standards/python-tooling/README.md
M	standards/python-tooling/adopt.md
A	tests/test_cli_fix.py
A	tests/test_format_frontmatter.py
A	tests/test_id_format.py
A	tests/test_precommit_hooks.py
M	tests/test_validate_frontmatter.py
A	tests/test_validate_references.py

exec
/bin/bash -lc 'git diff --find-renames --minimal bd5d423fc9c8286f5a9634d5d85d0278de6ea788 -- src/project_standards pyproject.toml .github/workflows/validate-markdown-frontmatter.yml .pre-commit-hooks.yaml tests/test_cli_fix.py tests/test_format_frontmatter.py tests/test_id_format.py tests/test_precommit_hooks.py tests/test_validate_frontmatter.py tests/test_validate_references.py' in /home/chris/projects/project-standards
 succeeded in 0ms:
diff --git a/.github/workflows/validate-markdown-frontmatter.yml b/.github/workflows/validate-markdown-frontmatter.yml
index ba21dd4..d36381e 100644
--- a/.github/workflows/validate-markdown-frontmatter.yml
+++ b/.github/workflows/validate-markdown-frontmatter.yml
@@ -78,6 +78,10 @@ jobs:
         if: github.repository == 'L3DigitalNet/project-standards'
         run: uv run validate-id --config "${{ inputs.config-path || '.project-standards.yml' }}"
 
+      - name: Validate references (this repo)
+        if: github.repository == 'L3DigitalNet/project-standards'
+        run: uv run validate-references --config "${{ inputs.config-path || '.project-standards.yml' }}"
+
       # Running in a consuming repo: install the validator (and its bundled schema)
       # from the standards repo as a tool, then validate the caller's files.
       - name: Install validator (consuming repo)
@@ -93,3 +97,7 @@ jobs:
       - name: Validate id format (consuming repo)
         if: github.repository != 'L3DigitalNet/project-standards'
         run: validate-id --config "${{ inputs.config-path || '.project-standards.yml' }}"
+
+      - name: Validate references (consuming repo)
+        if: github.repository != 'L3DigitalNet/project-standards'
+        run: validate-references --config "${{ inputs.config-path || '.project-standards.yml' }}"
diff --git a/.pre-commit-hooks.yaml b/.pre-commit-hooks.yaml
new file mode 100644
index 0000000..d254a69
--- /dev/null
+++ b/.pre-commit-hooks.yaml
@@ -0,0 +1,39 @@
+# .pre-commit-hooks.yaml — consumers reference this repo + a pinned rev.
+# Per-file hooks take staged markdown; validate-references needs the whole repo.
+- id: format-frontmatter-fix
+  name: format frontmatter (write)
+  entry: format-frontmatter --write
+  language: python
+  language_version: python3.14
+  types: [markdown]
+- id: format-frontmatter-check
+  name: format frontmatter (check)
+  entry: format-frontmatter --check
+  language: python
+  language_version: python3.14
+  types: [markdown]
+- id: validate-id-fix
+  name: validate id (fix)
+  entry: validate-id --fix
+  language: python
+  language_version: python3.14
+  types: [markdown]
+- id: validate-id-check
+  name: validate id (check)
+  entry: validate-id
+  language: python
+  language_version: python3.14
+  types: [markdown]
+- id: validate-frontmatter
+  name: validate frontmatter schema
+  entry: validate-frontmatter
+  language: python
+  language_version: python3.14
+  types: [markdown]
+- id: validate-references
+  name: validate cross-file references
+  entry: validate-references
+  language: python
+  language_version: python3.14
+  types: [markdown]
+  pass_filenames: false
diff --git a/pyproject.toml b/pyproject.toml
index 041c721..4c2d8cf 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -17,6 +17,8 @@ validate-frontmatter = "project_standards.validate_frontmatter:main"
 validate-id = "project_standards.validate_id:main"
 sync-vscode-colors = "project_standards.sync_vscode_colors:main"
 sync-standards-include = "project_standards.sync_standards_include:main"
+format-frontmatter = "project_standards.format_frontmatter:main"
+validate-references = "project_standards.validate_references:main"
 
 [dependency-groups]
 dev = [
diff --git a/src/project_standards/README.md b/src/project_standards/README.md
index dc3bead..4832313 100644
--- a/src/project_standards/README.md
+++ b/src/project_standards/README.md
@@ -9,12 +9,15 @@ This is the Python package that ships the validator, adopt engine, bundled schem
 - [`project_standards` — source layout](#project_standards--source-layout)
   - [Table of Contents](#table-of-contents)
   - [CLI surface](#cli-surface)
-  - [Validators](#validators)
+  - [Validators and formatters](#validators-and-formatters)
     - [validate-frontmatter](#validate-frontmatter)
     - [validate-id](#validate-id)
       - [Standard format — all `doc_type` values except `adr`](#standard-format--all-doc_type-values-except-adr)
       - [ADR format — `doc_type: adr`](#adr-format--doc_type-adr)
+    - [validate-references](#validate-references)
+    - [format-frontmatter](#format-frontmatter)
     - [project-standards validate (combined command)](#project-standards-validate-combined-command)
+    - [project-standards fix (combined fix command)](#project-standards-fix-combined-fix-command)
   - [Module map](#module-map)
   - [Adopt engine](#adopt-engine)
     - [Artifact kinds](#artifact-kinds)
@@ -26,23 +29,28 @@ This is the Python package that ships the validator, adopt engine, bundled schem
 
 ## CLI surface
 
-Three console scripts are registered by `pyproject.toml`:
+Console scripts registered by `pyproject.toml`:
 
 | Command | Module | Purpose |
 | --- | --- | --- |
 | `project-standards adopt STANDARD …` | `cli.py` | Materialize a standard's files into a target repo |
 | `project-standards list [--json]` | `cli.py` | List adoptable standards and their artifacts |
-| `project-standards validate [FLAGS] [FILE …]` | `cli.py` | Run both validators (schema + id) in one pass |
+| `project-standards validate [FLAGS] [FILE …]` | `cli.py` | Run all three validators (schema + id + references) in one pass |
+| `project-standards fix [FLAGS] [FILE …]` | `cli.py` | Format frontmatter, fix ids, then re-validate (bundled schema only) |
 | `validate-frontmatter [FLAGS] [FILE …]` | `validate_frontmatter.py` | Validate YAML frontmatter against the JSON Schema |
 | `validate-id [FLAGS] [FILE …]` | `validate_id.py` | Validate `id` field format per `doc_type` |
+| `validate-references [FLAGS]` | `validate_references.py` | Cross-file checks (id uniqueness, referential integrity, etc.) |
+| `format-frontmatter [FLAGS] [FILE …]` | `format_frontmatter.py` | Reformat frontmatter (canonical key order, quoting, transforms) |
 
-`project-standards validate` is an early-dispatch alias that forwards its full argv to both `validate_frontmatter.main()` and `validate_id.main()` and returns the worst exit code so neither validator's errors can be masked by the other's success.
+`project-standards validate` is an early-dispatch command that forwards its full argv to `validate_frontmatter.main()`, `validate_id.main()`, and `validate_references.main()` and returns the worst exit code so no validator's errors are masked by another's success. `validate-references` self-gates on `references_enabled` — it exits 0 immediately unless the repo has opted in via `.project-standards.yml`.
+
+`project-standards fix` is an early-dispatch command that runs `format_frontmatter.main(["--write", …])`, then `validate_id.main(["--fix", …])`, and finally the full `validate` contract (schema + id + references). It skips entirely when a custom schema is in use (flag `--schema` or `markdown.frontmatter.schema:` pointing to a file path).
 
 ---
 
-## Validators
+## Validators and formatters
 
-Two validators enforce the managed-document contract. They share the same config file and the same `collect_paths()` logic, and are both invoked by `project-standards validate`.
+Three validators and one formatter enforce and repair the managed-document contract. They share the same config file and the same `collect_paths()` logic, and are all invoked by `project-standards validate` / `project-standards fix`.
 
 ### validate-frontmatter
 
@@ -54,7 +62,7 @@ Validates YAML frontmatter blocks against a JSON Schema (Draft 2020-12 via `json
 - The YAML block is valid and parses without error.
 - Every field matches the JSON Schema (required fields present, types correct, enum values valid, date formats correct, etc.).
 - The `schema_version` matches the configured contract version if `version:` is pinned.
-- For ADR docs (`doc_type: adr`), when `require_sections: true`, enforces the three required `##` headings: `## Context`, `## Decision`, `## Consequences`.
+- For ADR docs (`doc_type: adr`), when `require_sections: true`, enforces the three required `##` headings: `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome` (MADR 4.0).
 
 **Key flags:**
 
@@ -67,7 +75,7 @@ Validates YAML frontmatter blocks against a JSON Schema (Draft 2020-12 via `json
 | `--no-require-frontmatter` | — | Do not fail files with no frontmatter block |
 | `--quiet` / `-q` | — | Suppress per-file output; exit code only |
 
-**Custom schema and bundled schema names:** `--schema` accepts a path OR a bundled name (e.g. `markdown-frontmatter`). `_schema_value_is_path()` in `validate_frontmatter.py` detects paths by looking for `/`, `\`, or `.json` suffix. A bare token is treated as a bundled name. The same logic governs `markdown.frontmatter.schema:` in the config file.
+**Custom schema and bundled schema names:** `--schema` accepts a path OR a bundled name (e.g. `markdown-frontmatter`). `schema_value_is_path()` in `validate_frontmatter.py` detects paths by looking for `/`, `\`, or `.json` suffix. A bare token is treated as a bundled name. The same logic governs `markdown.frontmatter.schema:` in the config file.
 
 ---
 
@@ -140,21 +148,60 @@ Rewrites each non-compliant file's `id:` value in place:
 
 ---
 
+### validate-references
+
+Cross-file checks that JSON Schema cannot express. Entry point: `validate_references.main(argv)`. **Disabled by default** — opt in via `markdown.frontmatter.references.enabled: true` in `.project-standards.yml`.
+
+**What it checks:**
+
+- `id` uniqueness — no two documents share the same `id`.
+- Referential integrity (warning) — every value in `related`, `depends_on`, `supersedes`, and `superseded_by` resolves, either as a known document `id` or as a file at that repo-root-relative path.
+- Supersede reciprocity (warning) — `supersedes` ↔ `superseded_by` links are symmetric (both directions checked).
+- Date ordering (error) — `created` ≤ `updated`, and `reviewed` ≥ `created` when present.
+- ADR sequence (error) — no two ADRs share the same `adr-NNNN` number.
+
+It is a repo-wide pass (no per-file mode). When `references_enabled` is false, `main()` returns 0 immediately — invoking it is always safe.
+
+---
+
+### format-frontmatter
+
+Reformats frontmatter to canonical style. Entry point: `format_frontmatter.main(argv)`. Two modes:
+
+| Flag      | Effect                                      |
+| --------- | ------------------------------------------- |
+| `--write` | Rewrite files in place                      |
+| `--check` | Check only; exit 1 if any file would change |
+
+**Transforms applied:**
+
+- Reorder keys to canonical order.
+- Quote all string values with single quotes.
+- Rename `type` → `doc_type` (deny-listed alias).
+- Render empty arrays as `[]`; non-empty arrays in block style.
+- Preserve explicit `null` values (never stripped).
+- Preserve the document body unchanged.
+
+Works only with the bundled schema. Skips files under a custom schema.
+
+---
+
 ### project-standards validate (combined command)
 
-`project-standards validate [FLAGS] [FILE …]` runs both validators in a single pass:
+`project-standards validate [FLAGS] [FILE …]` runs all three validators in a single pass:
 
 ```python
 rc_frontmatter = validate_frontmatter.main(validator_args)
 rc_id = validate_id.main(validator_args)
-return max(rc_frontmatter, rc_id)
+rc_refs = validate_references.main(validator_args)
+return max(rc_frontmatter, rc_id, rc_refs)
 ```
 
-All flags (`--config`, `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`) are forwarded unchanged to both validators. The worst exit code is returned so neither validator's errors can be masked by the other's success.
+All flags (`--config`, `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`) are forwarded unchanged to all validators. The worst exit code is returned so no validator's errors can be masked by another's success.
 
-`--schema` causes `validate-id` to skip automatically: a custom schema signals non-standard id conventions, so the bundled base-36 rules would produce false positives for consumers who define their own id format. The same skip applies when `markdown.frontmatter.schema:` in the config file is a path.
+`--schema` causes `validate-id` to skip automatically (custom schemas may use different id conventions). `validate-references` self-gates on `references_enabled`.
 
-`--help` is intercepted before forwarding and prints combined documentation rather than delegating to `validate-frontmatter --help` (which would hide that `validate-id` also runs).
+`--help` is intercepted before forwarding and prints combined documentation.
 
 **Dogfood command:**
 
@@ -164,13 +211,29 @@ uv run project-standards validate --config .project-standards.yml
 
 ---
 
+### project-standards fix (combined fix command)
+
+`project-standards fix [FLAGS] [FILE …]` is a three-phase pipeline:
+
+1. `format_frontmatter.main(["--write", …])` — reformat frontmatter in place.
+2. `validate_id.main(["--fix", …])` — regenerate non-compliant ids in place.
+3. Full `validate` contract — schema + id + references — as a postcondition.
+
+Returns the worst exit code across all three phases. If the final validate fails (e.g. a duplicate-id reference error), the exit code is non-zero even though the write phases succeeded.
+
+**Custom-schema skip (CR-001):** when `--schema` is passed, or `markdown.frontmatter.schema:` in the config is a path, `fix` prints a note and exits 0 without touching any files — bundled transforms are semantically undefined for non-standard schemas.
+
+---
+
 ## Module map
 
 ```text
 src/project_standards/
-├── cli.py                        # Unified CLI: adopt | list | validate dispatch
+├── cli.py                        # Unified CLI: adopt | list | validate | fix dispatch
 ├── validate_frontmatter.py       # Schema validator (Draft 2020-12 via jsonschema)
 ├── validate_id.py                # id-format validator (base-36 and ADR formats)
+├── validate_references.py        # Cross-file reference checker (opt-in)
+├── format_frontmatter.py         # Frontmatter formatter (--write / --check)
 ├── registry.py                   # Contract-version registry (reads registry.json)
 ├── sync_standards_include.py     # Internal maintenance: sync include lists
 ├── sync_vscode_colors.py         # Internal maintenance: VS Code colour tokens
diff --git a/src/project_standards/adopt/engine.py b/src/project_standards/adopt/engine.py
index 0f4bcaf..4b65754 100644
--- a/src/project_standards/adopt/engine.py
+++ b/src/project_standards/adopt/engine.py
@@ -22,15 +22,11 @@ def major_ref() -> str:
     try:
         full = version("project-standards")
     except PackageNotFoundError as exc:  # pragma: no cover - exercised via monkeypatch
-        raise ManifestError(
-            "cannot resolve project-standards version for @vN ref"
-        ) from exc
+        raise ManifestError("cannot resolve project-standards version for @vN ref") from exc
     return "v" + full.split(".")[0]
 
 
-def resolve_source(
-    artifact: Artifact, standard_id: str, bundles_dir: Path = BUNDLES_DIR
-) -> Path:
+def resolve_source(artifact: Artifact, standard_id: str, bundles_dir: Path = BUNDLES_DIR) -> Path:
     """Absolute path to an artifact's source, validated to live inside `bundles/`.
 
     Absolute or `..`-traversing source/shared, or a path that escapes the bundle tree,
@@ -61,9 +57,7 @@ class Action:
     standards: tuple[str, ...]  # contributing standard ids (for reporting)
 
 
-def build_plan(
-    standard_ids: list[str], *, bundles_dir: Path = BUNDLES_DIR
-) -> list[Action]:
+def build_plan(standard_ids: list[str], *, bundles_dir: Path = BUNDLES_DIR) -> list[Action]:
     """Flatten requested standards into one deduplicated, source-resolved action list.
 
     Unknown id or two *owned* artifacts targeting one dest -> UsageError (exit 2).
@@ -78,9 +72,7 @@ def build_plan(
     # would write the same dest from DIFFERENT sources is an authoring bug. The same
     # source (a shared file referenced by two standards) dedupes to one action.
     write_actions: dict[str, Action] = {}  # dest -> Action (file / workflow-caller)
-    fragment_actions: list[
-        Action
-    ] = []  # fragments are reported; multiple per target allowed
+    fragment_actions: list[Action] = []  # fragments are reported; multiple per target allowed
     for sid in standard_ids:
         manifest = load_manifest(sid, bundles_dir)
         for art in manifest.artifacts:
@@ -207,9 +199,7 @@ def _atomic_write(target: Path, data: bytes) -> None:
     tmp: Path | None = None
     try:
         target.parent.mkdir(parents=True, exist_ok=True)
-        fd, tmp_name = tempfile.mkstemp(
-            dir=target.parent, prefix=".adopt-", suffix=".tmp"
-        )
+        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".adopt-", suffix=".tmp")
         tmp = Path(tmp_name)
         with os.fdopen(fd, "wb") as fh:
             fh.write(data)
@@ -222,31 +212,23 @@ def _atomic_write(target: Path, data: bytes) -> None:
         raise WriteError(f"failed writing {target}: {exc}") from exc
 
 
-def execute_plan(
-    plan: list[Action], dest_root: Path, *, force: bool, dry_run: bool
-) -> Report:
+def execute_plan(plan: list[Action], dest_root: Path, *, force: bool, dry_run: bool) -> Report:
     """Classify and execute each action; accumulate fragments (multiple per target)."""
     ref = major_ref()
     report = Report()
     for action in plan:
         if action.kind == "fragment":
             assert action.target is not None
-            _require_safe_relative(
-                action.target
-            )  # target safety even though never written
+            _require_safe_relative(action.target)  # target safety even though never written
             try:
                 snippet = action.source_path.read_text(encoding="utf-8")
             except OSError as exc:
-                raise WriteError(
-                    f"cannot read fragment {action.source_path}: {exc}"
-                ) from exc
+                raise WriteError(f"cannot read fragment {action.source_path}: {exc}") from exc
             report.fragments.setdefault(action.target, []).append(snippet)
             continue
         assert action.dest is not None
         abs_dest = validate_dest(action.dest, dest_root)
-        if abs_dest.is_symlink() or _has_symlinked_ancestor(
-            abs_dest, dest_root.resolve()
-        ):
+        if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, dest_root.resolve()):
             report.symlink_skipped.append(
                 action.dest
             )  # never write through a symlinked leaf OR parent
diff --git a/src/project_standards/cli.py b/src/project_standards/cli.py
index d09537e..127ee0b 100644
--- a/src/project_standards/cli.py
+++ b/src/project_standards/cli.py
@@ -1,7 +1,8 @@
 """Unified `project-standards` CLI: adopt | list | validate.
 
-`validate` runs both `validate-frontmatter` (schema) and `validate-id` (id format) so
-consumers get the full contract check from a single command.  The standalone
+`validate` runs `validate-frontmatter` (schema), `validate-id` (id format), and
+`validate-references` (cross-file, opt-in) so consumers get the full contract check
+from a single command.  The standalone
 `validate-frontmatter` console script is kept as a back-compat alias.
 """
 
@@ -12,7 +13,12 @@ import json
 import sys
 from pathlib import Path
 
-from project_standards import validate_frontmatter, validate_id
+from project_standards import (
+    format_frontmatter,
+    validate_frontmatter,
+    validate_id,
+    validate_references,
+)
 from project_standards.adopt.engine import build_plan, execute_plan, format_report
 from project_standards.adopt.errors import AdoptError
 from project_standards.adopt.manifest import (
@@ -43,6 +49,21 @@ _REGISTRY_STANDARD_IDS = (
 )
 
 
+def _extract_config_path(args: list[str]) -> Path:
+    """Pull the --config value out of a forwarded argv (default .project-standards.yml)."""
+    for i, a in enumerate(args):
+        if a == "--config" and i + 1 < len(args):
+            return Path(args[i + 1])
+        if a.startswith("--config="):
+            return Path(a.split("=", 1)[1])
+    return Path(".project-standards.yml")
+
+
+def _has_schema_flag(args: list[str]) -> bool:
+    """True if a forwarded argv passes --schema (custom-schema mode) — CR-001."""
+    return any(a == "--schema" or a.startswith("--schema=") for a in args)
+
+
 def _assert_registry_bundle_parity(registry: Registry) -> None:
     """Bundles and the registry's version-tracked standards must agree in BOTH directions.
 
@@ -122,12 +143,12 @@ def main(argv: list[str] | None = None) -> int:
     """
     args_list = list(sys.argv[1:] if argv is None else argv)
 
-    # EARLY DISPATCH for `validate`: delegate every trailing arg to both validators BEFORE the
+    # EARLY DISPATCH for `validate`: delegate every trailing arg to all three validators BEFORE the
     # adopt/list parser runs. `parse_args()` + `REMAINDER` does NOT work here — argparse rejects
     # `validate --config x` as an unrecognized top-level option before REMAINDER can capture it.
-    # Both validators accept the same --config / --quiet / FILE flags, so we pass args through
-    # unchanged. We return the worst exit code (2 > 1 > 0) so a schema error or id violation
-    # is never masked by the other tool's success.
+    # All three validators accept the same --config / --quiet / FILE flags, so we pass args through
+    # unchanged. We return the worst exit code (2 > 1 > 0) so a schema error, id violation, or
+    # reference error is never masked by another tool's success.
     if args_list and args_list[0] == "validate":
         validator_args = args_list[1:]
         # Intercept --help before forwarding — otherwise validate_frontmatter.main(["--help"])
@@ -136,14 +157,16 @@ def main(argv: list[str] | None = None) -> int:
             _p = argparse.ArgumentParser(
                 prog="project-standards validate",
                 description=(
-                    "Run validate-frontmatter (schema) and validate-id (id format).\n"
-                    "Both validators run; the worst exit code is returned.\n\n"
-                    "All flags are forwarded to both validators. --schema and\n"
+                    "Run validate-frontmatter (schema), validate-id (id format), and\n"
+                    "validate-references (cross-file, opt-in). All run; the worst exit\n"
+                    "code is returned.\n\n"
+                    "All flags are forwarded to every validator. --schema and\n"
                     "--no-require-frontmatter are frontmatter-only; --schema also causes\n"
                     "validate-id to skip (custom schemas may use different id conventions).\n\n"
                     "For the full flag set of each validator:\n"
                     "  validate-frontmatter --help\n"
-                    "  validate-id --help"
+                    "  validate-id --help\n"
+                    "  validate-references --help"
                 ),
                 formatter_class=argparse.RawDescriptionHelpFormatter,
             )
@@ -173,15 +196,46 @@ def main(argv: list[str] | None = None) -> int:
             return 0
         rc_frontmatter = validate_frontmatter.main(validator_args)
         rc_id = validate_id.main(validator_args)
-        return max(rc_frontmatter, rc_id)
+        rc_refs = validate_references.main(validator_args)
+        return max(rc_frontmatter, rc_id, rc_refs)
+
+    if args_list and args_list[0] == "fix":
+        fix_args = args_list[1:]
+        if "--help" in fix_args or "-h" in fix_args:
+            print(
+                "usage: project-standards fix [FILE ...] [--config PATH] [--glob PATTERN] [--quiet]\n"
+                "Format frontmatter (--write), fix ids, then re-validate (incl. references).\n"
+                "Skips entirely under a custom schema."
+            )
+            return 0
+        # Custom-schema preflight (CR-001): fix is bundled-only, like format/validate-id.
+        try:
+            fix_cfg = validate_frontmatter.load_config(_extract_config_path(fix_args))
+        except validate_frontmatter.ConfigError as exc:
+            print(f"error: {exc}", file=sys.stderr)
+            return 2
+        if _has_schema_flag(fix_args) or validate_frontmatter.schema_value_is_path(fix_cfg.schema):
+            print("note: custom schema in use; skipping fix", file=sys.stderr)
+            return 0
+        rc_format = format_frontmatter.main(["--write", *fix_args])
+        rc_idfix = validate_id.main(["--fix", *fix_args])
+        # Final postcondition = the SAME contract as `project-standards validate`,
+        # references included, so a "successful" fix cannot hide a reference error (CR-001).
+        rc_check = max(
+            validate_frontmatter.main(fix_args),
+            validate_id.main(fix_args),
+            validate_references.main(fix_args),
+        )
+        return max(rc_format, rc_idfix, rc_check)
 
     parser = argparse.ArgumentParser(prog="project-standards")
     sub = parser.add_subparsers(dest="command", required=True)
     # Registered only so top-level `--help` advertises it; real handling is the early dispatch above.
     sub.add_parser(
         "validate",
-        help="validate frontmatter schema + id format (runs validate-frontmatter and validate-id)",
+        help="validate schema + id + references (validate-frontmatter, validate-id, validate-references)",
     )
+    sub.add_parser("fix", help="format frontmatter + fix ids, then re-validate")
 
     p_adopt = sub.add_parser("adopt", help="materialize a standard's artifacts")
     p_adopt.add_argument("standards", nargs="+", metavar="STANDARD")
diff --git a/src/project_standards/format_frontmatter.py b/src/project_standards/format_frontmatter.py
new file mode 100644
index 0000000..b508ffe
--- /dev/null
+++ b/src/project_standards/format_frontmatter.py
@@ -0,0 +1,650 @@
+"""Autoformatter for managed Markdown frontmatter (the write-side companion to
+validate-frontmatter). Tokenizes the leading YAML block into per-key entries,
+applies deterministic transforms, and re-emits the block preserving comments and
+per-line endings (same technique as validate_id --fix). Never changes the `id`
+value (it may re-quote it like any scalar, but the value is validate_id's domain)
+and never edits the document body."""
+
+from __future__ import annotations
+
+import argparse
+import contextlib
+import datetime
+import json
+import os
+import re
+import sys
+import tempfile
+from dataclasses import dataclass, field
+from pathlib import Path
+from typing import Any, cast
+
+import yaml
+
+from project_standards.id_format import random_token, slugify
+
+# Leading frontmatter block; groups: open fence, body (between fences), close fence.
+_FM_RE = re.compile(r"\A(---[ \t]*\r?\n)(.*?)(\r?\n---[ \t]*(?:\r?\n|$))", re.DOTALL)
+# A top-level (column 0) mapping key line: `key:` optionally followed by a value.
+_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")
+
+_SCHEMA_PATH = Path(__file__).parent / "schemas" / "markdown-frontmatter.schema.json"
+VALID_DOC_TYPES: frozenset[str] = frozenset(
+    json.loads(_SCHEMA_PATH.read_text())["properties"]["doc_type"]["enum"]
+)
+
+CANONICAL_ORDER: tuple[str, ...] = (
+    "schema_version",
+    "id",
+    "title",
+    "description",
+    "doc_type",
+    "status",
+    "created",
+    "updated",
+    "reviewed",
+    "owner",
+    "consumer",
+    "tags",
+    "aliases",
+    "related",
+    "supersedes",
+    "superseded_by",
+    "depends_on",
+    "applies_to",
+    "source",
+    "confidence",
+    "visibility",
+    "license",
+    "publish",
+    "project",
+    "x_project",
+)
+
+
+@dataclass
+class Entry:
+    """One top-level frontmatter key and the exact source lines it owns.
+
+    `lines` holds every physical source line for this entry WITH its original
+    line ending: any leading comment/blank run, the `key:` line (incl. an inline
+    `# comment`), and indented continuation lines (block list or nested mapping).
+    `key` is None only for a trailing comment/blank run after the last key."""
+
+    key: str | None
+    lines: list[str] = field(default_factory=list)
+
+
+def _split_keepends(text: str) -> list[str]:
+    return text.splitlines(keepends=True)
+
+
+def tokenize(body: str) -> tuple[list[Entry], str | None]:
+    """Split the between-fences `body` into Entry objects.
+
+    Returns (entries, None) on success, or ([], reason) if the block contains a
+    construct unsafe to reorder/reserialize (anchors, merge keys, a non-key line
+    at column 0). Nested mappings and block lists are supported (carried opaquely
+    as continuation lines)."""
+    lines = _split_keepends(body)
+    entries: list[Entry] = []
+    pending: list[str] = []  # leading comment/blank lines for the next key
+    seen: set[str] = set()  # duplicate top-level keys are unsafe to reorder (CR-002)
+    i = 0
+    while i < len(lines):
+        line = lines[i]
+        content = line.rstrip("\r\n")
+        stripped = content.lstrip(" \t")
+        if stripped == "" or stripped.startswith("#"):
+            pending.append(line)
+            i += 1
+            continue
+        m = _TOP_KEY_RE.match(content)
+        if not m:
+            return [], f"unrecognized top-level line: {content!r}"
+        key = m.group(1)
+        value = m.group(2).lstrip()
+        if value[:1] in ("&", "*") or value.startswith("<<") or value[:1] in ("|", ">"):
+            return [], f"unsupported YAML construct on key {key!r}"
+        if key in seen:
+            return [], f"duplicate top-level key {key!r} (refusing to rewrite)"
+        seen.add(key)
+        entry = Entry(key=key, lines=[*pending, line])
+        pending = []
+        i += 1
+        # Gather indented continuation lines (block list items / nested mapping).
+        while i < len(lines):
+            nxt = lines[i]
+            ncontent = nxt.rstrip("\r\n")
+            if ncontent.lstrip(" \t") == "":
+                break  # blank line ends the entry; becomes leading run of next
+            if nxt[:1] in (" ", "\t"):
+                entry.lines.append(nxt)
+                i += 1
+                continue
+            break
+        entries.append(entry)
+    if pending:
+        entries.append(Entry(key=None, lines=pending))
+    return entries, None
+
+
+def _emit_single_quoted(value: str) -> str:
+    """YAML single-quoted scalar: wrap in quotes, double internal single-quotes."""
+    return "'" + value.replace("'", "''") + "'"
+
+
+_NULL_TOKENS = frozenset({"null", "Null", "NULL", "~"})
+
+
+def _split_value_comment(rest: str) -> tuple[str, str]:
+    """Split the text after `key:` into (raw_value, comment). A YAML inline comment
+    begins only at whitespace + '#' (CR-NEW-003); a bare '#' (e.g. `C# guide`,
+    `http://x/#frag`), a '#' inside a quoted scalar, or a '#' inside a quoted flow-list
+    item (e.g. `['Issue #123']` — CR-NEW-005) is literal. `comment` keeps its leading
+    whitespace (e.g. '  # note') so it round-trips, or is ''."""
+    stripped = rest.lstrip(" \t")
+    lead = rest[: len(rest) - len(stripped)]
+    if stripped[:1] in ("'", '"'):
+        quote = stripped[0]
+        i = 1
+        while i < len(stripped):
+            ch = stripped[i]
+            if quote == "'" and ch == "'":
+                if stripped[i : i + 2] == "''":  # escaped single quote
+                    i += 2
+                    continue
+                return lead + stripped[: i + 1], stripped[i + 1 :]
+            if quote == '"' and ch == "\\":
+                i += 2
+                continue
+            if quote == '"' and ch == '"':
+                return lead + stripped[: i + 1], stripped[i + 1 :]
+            i += 1
+        return rest, ""  # unterminated quote -> treat whole as value (left as-is upstream)
+    if stripped[:1] == "[":  # flow list: scan to the matching ], honoring quotes
+        depth = 0
+        in_quote = ""
+        i = 0
+        while i < len(stripped):
+            ch = stripped[i]
+            if in_quote:
+                if in_quote == "'" and ch == "'":
+                    if stripped[i : i + 2] == "''":
+                        i += 2
+                        continue
+                    in_quote = ""
+                elif in_quote == '"' and ch == "\\":
+                    i += 2
+                    continue
+                elif in_quote == '"' and ch == '"':
+                    in_quote = ""
+            elif ch in ("'", '"'):
+                in_quote = ch
+            elif ch == "[":
+                depth += 1
+            elif ch == "]":
+                depth -= 1
+                if depth == 0:
+                    tail = stripped[i + 1 :]
+                    return lead + stripped[: i + 1], (tail if re.match(r"\s+#", tail) else "")
+            i += 1
+        return rest, ""  # unbalanced brackets -> no comment
+    m = re.search(r"(\s+#.*)$", rest)  # plain scalar: comment = whitespace then '#' to end
+    if m:
+        return rest[: m.start()], rest[m.start() :]
+    return rest, ""
+
+
+def _requote_scalar_line(line: str, key: str) -> str:
+    """Re-quote the scalar value on a `key: value` line WITHOUT resolving its YAML type
+    (CR-NEW-001): the author's literal text is single-quoted, so `on`/`off`/`1.1`/a date
+    keep their exact characters. Indentation, an inline `# comment` (split at a real
+    whitespace-`#` boundary — CR-NEW-003), and the line ending are preserved; explicit
+    `null`/`~`, empty values, and flow lists are left untouched."""
+    m = re.match(
+        r"^(?P<indent>[ \t]*)(?P<key>" + re.escape(key) + r":)(?P<sep>[ \t]*)"
+        r"(?P<rest>[^\r\n]*)(?P<eol>\r?\n?)$",
+        line,
+    )
+    if m is None:
+        return line
+    value_raw, comment = _split_value_comment(m.group("rest"))
+    raw = value_raw.strip()
+    if raw == "" or raw.startswith("["):
+        return line  # empty or flow list -> handled by normalize_lists
+    if raw in _NULL_TOKENS:
+        return line  # explicit null stays null
+    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
+        return line  # already single-quoted -> idempotent
+    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
+        try:
+            decoded = yaml.safe_load(raw)  # explicit quotes -> intended string, no type guess
+        except yaml.YAMLError:
+            return line  # malformed double-quoted scalar -> leave for the validator, never crash
+        text_value = decoded if isinstance(decoded, str) else raw
+    else:
+        text_value = raw  # unquoted plain scalar: quote the RAW text, never resolve it
+    sep = m.group("sep") or " "
+    return (
+        m.group("indent")
+        + m.group("key")
+        + sep
+        + _emit_single_quoted(text_value)
+        + comment
+        + m.group("eol")
+    )
+
+
+def _line_ending(line: str) -> str:
+    """Return the line ending of `line`, or '' if the line has no trailing newline.
+
+    The regex design absorbs the final newline of the frontmatter body into the
+    close-fence group, so the very last physical line of `body` arrives without a
+    trailing newline.  Returning '' here lets callers preserve that absent newline
+    on the key line; item lines in a block list always use '\n'."""
+    if line.endswith("\r\n"):
+        return "\r\n"
+    if line.endswith("\n"):
+        return "\n"
+    return ""
+
+
+# The array-typed fields in the schema; only these are list-normalized.
+_LIST_FIELDS = ("tags", "aliases", "related", "supersedes", "depends_on", "applies_to", "source")
+
+
+def _leading_run(entry: Entry) -> int:
+    """Count of leading comment/blank lines before the entry's `key:` line."""
+    n = 0
+    for ln in entry.lines:
+        stripped = ln.rstrip("\r\n").lstrip(" \t")
+        if stripped == "" or stripped.startswith("#"):
+            n += 1
+        else:
+            break
+    return n
+
+
+def _block_list_has_item_comment(item_lines: list[str]) -> bool:
+    """True if any block-list item line carries a real inline comment (e.g. `- 'a'  # why`).
+    Re-rendering the list from parsed values would silently drop such a comment (codex P2),
+    so the formatter leaves a comment-bearing list untouched rather than destroy the note."""
+    for ln in item_lines:
+        stripped = ln.lstrip(" \t").rstrip("\r\n")
+        if not stripped.startswith("-"):
+            continue
+        after_dash = stripped[1:].lstrip(" \t")
+        if _split_value_comment(after_dash)[1].lstrip(" \t").startswith("#"):
+            return True
+    return False
+
+
+def normalize_lists(entries: list[Entry]) -> None:
+    """In place: render each list-typed field as canonical block style (single-quoted
+    items, duplicates removed first-wins); an empty/absent value becomes `key: []`.
+    Values are read with yaml.BaseLoader so list items are NEVER type-coerced — e.g.
+    `[on, off]` stays the strings 'on'/'off', not booleans (CR-NEW-001)."""
+    for entry in entries:
+        if entry.key not in _LIST_FIELDS:
+            continue
+        lead = _leading_run(entry)
+        try:
+            loaded = yaml.load("".join(entry.lines[lead:]), Loader=yaml.BaseLoader)  # pyright: ignore[reportUnknownMemberType]
+        except yaml.YAMLError:
+            continue
+        if not isinstance(loaded, dict) or entry.key not in loaded:
+            continue
+        value: Any = cast(Any, loaded)[entry.key]  # BaseLoader dict values are untyped
+        if not (value is None or value == "" or isinstance(value, list)):
+            continue  # a scalar where a list belongs -> leave for the validator
+        if _block_list_has_item_comment(entry.lines[lead + 1 :]):
+            continue  # preserve authored per-item comments; do not re-render (codex P2)
+        key_line = entry.lines[lead]
+        eol = _line_ending(entry.lines[-1])
+        # Indent by slice (NOT re.match(...).group(0), which basedpyright-strict flags — CR-NEW-002).
+        indent = key_line[: len(key_line) - len(key_line.lstrip(" \t"))]
+        after_colon = key_line.rstrip("\r\n").split(":", 1)[1] if ":" in key_line else ""
+        inline = _split_value_comment(after_colon)[
+            1
+        ]  # comment after [], [a], or bare key (CR-NEW-004)
+        leading = entry.lines[:lead]
+        raw_items: list[Any] = cast(list[Any], value) if isinstance(value, list) else []
+        items: list[str] = [str(x) for x in raw_items]
+        seen: list[str] = []
+        for item in items:
+            if item not in seen:
+                seen.append(item)
+        # item_eol: block-list items always need a real newline; fall back to '\n'
+        # when the key line has no trailing newline (last entry in body — the regex
+        # design absorbs that newline into close_fence).
+        item_eol = eol or "\n"
+        if not seen:
+            entry.lines = [*leading, f"{indent}{entry.key}: []{inline}{eol}"]
+        else:
+            rendered = [f"{indent}{entry.key}:{inline}{item_eol}"]
+            rendered += [f"{indent}  - {_emit_single_quoted(s)}{item_eol}" for s in seen]
+            entry.lines = [*leading, *rendered]
+
+
+def requote(entries: list[Entry]) -> None:
+    """In place: single-quote the scalar value on each scalar entry — including one
+    preceded by leading comment/blank lines, which bundle into the same entry (a bare
+    `len(entry.lines) != 1` guard would wrongly skip such a commented key — codex P2).
+    Multi-line VALUES (block lists, nested mappings) are left for their own transforms."""
+    for entry in entries:
+        if entry.key is None:
+            continue
+        lead = _leading_run(entry)
+        if len(entry.lines) != lead + 1:
+            continue  # the value spans multiple lines (block list / nested mapping)
+        entry.lines[lead] = _requote_scalar_line(entry.lines[lead], entry.key)
+
+
+_ORDER_INDEX = {key: i for i, key in enumerate(CANONICAL_ORDER)}
+
+
+def reorder(entries: list[Entry], warnings: list[str]) -> list[Entry]:
+    """Stable sort entries into CANONICAL_ORDER. Unknown keys keep their relative
+    order after all known keys; a trailing comment-only entry (key=None) stays last.
+    Unknown keys also emit a warn-only message (never deleted)."""
+
+    def sort_key(item: tuple[int, Entry]) -> tuple[int, int]:
+        idx, entry = item
+        if entry.key is None:
+            return (len(CANONICAL_ORDER) + 1, idx)  # trailing comments last
+        if entry.key in _ORDER_INDEX:
+            return (_ORDER_INDEX[entry.key], 0)
+        warnings.append(f"unknown frontmatter key '{entry.key}' (kept; not in schema)")
+        return (len(CANONICAL_ORDER), idx)
+
+    return [e for _, e in sorted(enumerate(entries), key=sort_key)]
+
+
+def serialize(entries: list[Entry]) -> str:
+    """Concatenate entries' source lines verbatim.
+
+    The regex design absorbs the final `\\n` of the body into `close_fence`, so
+    the very last physical line of `body` arrives without a trailing newline.  When
+    reordering moves that entry to a non-tail position, we must ensure it still
+    ends with a newline so the following entry starts on a new line.  If the entry
+    stays last, we leave it unchanged to preserve byte-identity on round-trips."""
+    parts: list[str] = []
+    for i, entry in enumerate(entries):
+        is_last = i == len(entries) - 1
+        for j, line in enumerate(entry.lines):
+            is_last_line = j == len(entry.lines) - 1
+            if is_last_line and not is_last and line and not line.endswith(("\n", "\r\n")):
+                parts.append(line + "\n")
+            else:
+                parts.append(line)
+    return "".join(parts)
+
+
+BUNDLED_SCHEMA_VERSION = "1.1"  # matches registry frontmatter_default; see Task A9 note
+REQUIRED_ARRAYS = ("tags", "aliases", "related")
+
+
+def _keys(entries: list[Entry]) -> set[str]:
+    return {e.key for e in entries if e.key is not None}
+
+
+def rename_type(entries: list[Entry], warnings: list[str]) -> None:
+    present = _keys(entries)
+    if "doc_type" in present:
+        if "type" in present:
+            warnings.append("both 'type' and 'doc_type' present; kept 'doc_type', left 'type'")
+        return
+    for entry in entries:
+        if entry.key == "type":
+            entry.key = "doc_type"
+            entry.lines = [re.sub(r"\btype:", "doc_type:", ln, count=1) for ln in entry.lines]
+            return
+
+
+def _new_scalar_entry(key: str, value: str, eol: str) -> Entry:
+    return Entry(key=key, lines=[f"{key}: {_emit_single_quoted(value)}{eol}"])
+
+
+def _new_empty_list_entry(key: str, eol: str) -> Entry:
+    return Entry(key=key, lines=[f"{key}: []{eol}"])
+
+
+def inject_defaults(entries: list[Entry]) -> None:
+    """Add schema_version and any missing required arrays. Reorder (A2) places them."""
+    eol = _line_ending(entries[0].lines[-1]) if entries and entries[0].lines else "\n"
+    present = _keys(entries)
+    if "schema_version" not in present:
+        entries.append(_new_scalar_entry("schema_version", BUNDLED_SCHEMA_VERSION, eol))
+    for key in REQUIRED_ARRAYS:
+        if key not in present:
+            entries.append(_new_empty_list_entry(key, eol))
+
+
+_NEVER_NAMES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
+_NEVER_DIRS = {".claude", ".agents", ".codex"}
+
+
+def is_denylisted(path: Path) -> bool:
+    """Files that must NEVER carry frontmatter (harness config). Overrides include
+    and scaffold, independent of config — defense-in-depth over consumer exclude."""
+    if path.name in _NEVER_NAMES:
+        return True
+    return any(part in _NEVER_DIRS for part in path.parts)
+
+
+def _infer_doc_type(path: Path) -> str | None:
+    """The standard's path rules. None = no rule applies."""
+    posix = path.as_posix()
+    if "docs/research/" in posix or posix.startswith("docs/research/"):
+        return "research"
+    if path.name in ("README.md", "index.md"):
+        return "index"
+    return None
+
+
+def infer_doc_type(entries: list[Entry], path: Path | None) -> None:
+    """Fill/correct-only (SA-001): set doc_type from the path rule ONLY when the
+    current value is missing or not a valid enum value. A valid value is kept."""
+    if path is None:
+        return
+    inferred = _infer_doc_type(path)
+    if inferred is None:
+        return
+    eol = _line_ending(entries[0].lines[-1]) if entries and entries[0].lines else "\n"
+    for entry in entries:
+        if entry.key == "doc_type":
+            current = entry.lines[-1].split(":", 1)[1].strip().strip("'\"")
+            if current in VALID_DOC_TYPES:
+                return  # valid -> never override
+            entry.lines = [f"doc_type: {_emit_single_quoted(inferred)}{eol}"]
+            return
+    entries.append(_new_scalar_entry("doc_type", inferred, eol))
+
+
+_H1_RE = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)
+
+
+def _today_iso() -> str:
+    return datetime.date.today().isoformat()
+
+
+def _build_scaffold(body_text: str, path: Path, today: str) -> str:
+    h1 = _H1_RE.search(body_text)
+    title = h1.group(1) if h1 else path.stem.replace("-", " ").replace("_", " ").title()
+    doc_type = _infer_doc_type(path) or "note"
+    slug = slugify(title) or slugify(path.stem) or "untitled"
+    new_id = f"{doc_type}-{random_token()}-{slug}"
+    return (
+        "---\n"
+        f"schema_version: {_emit_single_quoted(BUNDLED_SCHEMA_VERSION)}\n"
+        f"id: {_emit_single_quoted(new_id)}\n"
+        f"title: {_emit_single_quoted(title)}\n"
+        "description: 'TODO: one-sentence description.'\n"
+        f"doc_type: {_emit_single_quoted(doc_type)}\n"
+        "status: 'draft'\n"
+        f"created: {_emit_single_quoted(today)}\n"
+        f"updated: {_emit_single_quoted(today)}\n"
+        "tags: []\n"
+        "aliases: []\n"
+        "related: []\n"
+        "---\n"
+    )
+
+
+def format_text(
+    text: str,
+    *,
+    path: Path | None,
+    scaffold: bool = False,
+    today: str | None = None,
+    bump_updated: bool = False,
+) -> tuple[str, bool, list[str]]:
+    """Format the frontmatter block of `text`. Returns (new_text, changed, warnings).
+
+    `path` informs path-based transforms; None disables them (stdin mode). The
+    `scaffold` flag inserts a schema-valid block into files with no frontmatter.
+    `bump_updated` rewrites the `updated` field when the block changes."""
+    warnings: list[str] = []
+    if path is not None and is_denylisted(path):
+        return text, False, ["refused (denylisted): never add frontmatter to this file"]
+    match = _FM_RE.match(text)
+    if match is None:
+        if scaffold and path is not None and not is_denylisted(path):
+            stamp = today or _today_iso()
+            return (
+                _build_scaffold(text, path, stamp) + text,
+                True,
+                [f"scaffolded: {path} — fill in title/description"],
+            )
+        return text, False, warnings
+    open_fence, body, close_fence = match.group(1), match.group(2), match.group(3)
+    rest = text[match.end() :]
+    entries, reason = tokenize(body)
+    if reason is not None:
+        warnings.append(f"skipped (unsupported frontmatter): {reason}")
+        return text, False, warnings
+    rename_type(entries, warnings)
+    infer_doc_type(entries, path)
+    inject_defaults(entries)
+    normalize_lists(entries)
+    requote(entries)
+    entries = reorder(entries, warnings)
+    new_body = serialize(entries)
+    new_text = open_fence + new_body + close_fence + rest
+    changed = new_text != text
+    if bump_updated and changed:
+        stamp = today or _today_iso()
+        for entry in entries:
+            if entry.key == "updated" and len(entry.lines) == 1:
+                eol = _line_ending(entry.lines[0])
+                entry.lines = [f"updated: {_emit_single_quoted(stamp)}{eol}"]
+        new_body = serialize(entries)
+        new_text = open_fence + new_body + close_fence + rest
+        changed = new_text != text
+    return new_text, changed, warnings
+
+
+from project_standards.validate_frontmatter import (  # noqa: E402
+    ConfigError,
+    collect_paths,
+    load_config,
+    schema_value_is_path,
+)
+
+_DEFAULT_CONFIG = Path(".project-standards.yml")
+
+
+def _atomic_write(path: Path, data: str) -> None:
+    """Write atomically AND preserve the original file's permission bits (codex
+    missing-consideration): mkstemp creates 0600, so copy the source mode first."""
+    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
+    tmp_path = Path(tmp)
+    try:
+        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
+            fh.write(data)
+        with contextlib.suppress(OSError):
+            tmp_path.chmod(path.stat().st_mode & 0o777)
+        tmp_path.replace(path)
+    except BaseException:
+        tmp_path.unlink()
+        raise
+
+
+def main(argv: list[str] | None = None) -> int:
+    parser = argparse.ArgumentParser(
+        prog="format-frontmatter",
+        description=__doc__,
+        formatter_class=argparse.RawDescriptionHelpFormatter,
+    )
+    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
+    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
+    parser.add_argument("--schema", type=Path, default=None)
+    parser.add_argument("--glob", metavar="PATTERN")
+    mode = parser.add_mutually_exclusive_group()
+    mode.add_argument("--check", action="store_true")
+    mode.add_argument("--write", action="store_true")
+    parser.add_argument("--bump-updated", action="store_true")
+    parser.add_argument("--stdin", action="store_true")
+    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
+    parser.add_argument("--quiet", "-q", action="store_true")
+    args = parser.parse_args(argv)
+
+    # SA-spec: --stdin reads one document and writes stdout; it is incompatible with a
+    # file set or in-place write. Enforce it (parser.error exits 2) — CR-005.
+    if args.stdin and (args.files or args.glob or args.write):
+        parser.error("--stdin cannot be combined with FILE, --glob, or --write")
+
+    try:
+        config = load_config(args.config)
+    except ConfigError as exc:
+        print(f"error: {exc}", file=sys.stderr)
+        return 2
+
+    if args.schema is not None or schema_value_is_path(config.schema):
+        if not args.quiet:
+            print("note: custom schema in use; skipping frontmatter formatting")
+        return 0
+
+    if args.stdin:
+        text = sys.stdin.read()
+        new, _changed, _warn = format_text(text, path=None, bump_updated=args.bump_updated)
+        sys.stdout.write(new)
+        return 0
+
+    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
+    write = args.write  # default is check-mode
+    any_change = False
+    unparseable = False
+    for path in paths:
+        if is_denylisted(path):
+            continue
+        try:
+            text = path.read_text(encoding="utf-8")
+        except OSError as exc:
+            print(f"{path}: cannot read: {exc}", file=sys.stderr)
+            unparseable = True
+            continue
+        new, changed, warnings = format_text(
+            text, path=path, scaffold=write, bump_updated=args.bump_updated
+        )
+        for w in warnings:
+            print(f"{path}: {w}", file=sys.stderr)
+            # A duplicate-key block is refused (not rewritten) AND must fail the gate (CR-002).
+            if "duplicate top-level key" in w:
+                unparseable = True
+        if changed:
+            any_change = True
+            if write:
+                _atomic_write(path, new)
+                if not args.quiet:
+                    print(f"formatted: {path}")
+            elif not args.quiet:
+                print(f"would reformat: {path}")
+    if write:
+        return 1 if unparseable else 0
+    return 1 if (any_change or unparseable) else 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/src/project_standards/id_format.py b/src/project_standards/id_format.py
new file mode 100644
index 0000000..e57fe18
--- /dev/null
+++ b/src/project_standards/id_format.py
@@ -0,0 +1,26 @@
+"""Shared id-token helpers used by validate_id (id validation/fix) and
+format_frontmatter (scaffold). One copy so the two tools cannot drift."""
+
+from __future__ import annotations
+
+import re
+import secrets
+import string
+import unicodedata
+
+# Base-36 alphabet (digits + lowercase letters) for the 6-char id token.
+_BASE36_CHARS = string.digits + string.ascii_lowercase
+
+
+def slugify(text: str) -> str:
+    """Lowercase kebab-case slug: strip accents to ASCII, lowercase, collapse
+    every run of non-alphanumerics to a single hyphen, trim leading/trailing."""
+    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
+    text = text.lower()
+    text = re.sub(r"[^a-z0-9]+", "-", text)
+    return text.strip("-")
+
+
+def random_token(length: int = 6) -> str:
+    """A cryptographically-random base-36 token (default 6 chars)."""
+    return "".join(secrets.choice(_BASE36_CHARS) for _ in range(length))
diff --git a/src/project_standards/validate_frontmatter.py b/src/project_standards/validate_frontmatter.py
index 3dea528..b3f8e73 100755
--- a/src/project_standards/validate_frontmatter.py
+++ b/src/project_standards/validate_frontmatter.py
@@ -74,7 +74,7 @@ def find_bundled_schema(name: str) -> Path:
     return Path(__file__).parent / "schemas" / f"{name}.schema.json"
 
 
-def _schema_value_is_path(value: str | None) -> bool:
+def schema_value_is_path(value: str | None) -> bool:
     """True when a config `schema` value names a filesystem path, not a bundled name.
 
     A bare token (e.g. "markdown-frontmatter") is a bundled schema name; anything
@@ -89,7 +89,7 @@ def resolve_schema_path(schema_value: str | None) -> Path:
     A bare token is treated as a bundled schema name; anything containing a path
     separator or ending in `.json` is treated as a filesystem path.
     """
-    if _schema_value_is_path(schema_value):
+    if schema_value_is_path(schema_value):
         return Path(cast("str", schema_value))
     return find_bundled_schema(schema_value or _DEFAULT_SCHEMA_NAME)
 
@@ -99,6 +99,28 @@ def resolve_schema_path(schema_value: str | None) -> Path:
 # ---------------------------------------------------------------------------
 
 
+class _UniqueKeyLoader(yaml.SafeLoader):
+    """SafeLoader that rejects duplicate mapping keys (PyYAML otherwise keeps the
+    last silently). Frontmatter with a duplicate key is a bug, not a valid doc."""
+
+
+def _construct_no_duplicates(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[str, Any]:
+    mapping: dict[Any, Any] = {}
+    for key_node, value_node in node.value:
+        key = cast(Any, loader.construct_object(key_node, deep=True))  # pyright: ignore[reportUnknownMemberType]
+        if key in mapping:
+            raise yaml.constructor.ConstructorError(
+                None, None, f"duplicate key {key!r}", key_node.start_mark
+            )
+        mapping[key] = loader.construct_object(value_node, deep=True)  # pyright: ignore[reportUnknownMemberType]
+    return mapping
+
+
+_UniqueKeyLoader.add_constructor(
+    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_no_duplicates
+)
+
+
 def _coerce_dates(obj: Any) -> Any:
     """Recursively convert datetime.date/datetime to ISO strings.
 
@@ -124,7 +146,7 @@ def parse_frontmatter(text: str) -> dict[str, Any] | None:
     if not match:
         return None
     try:
-        loaded = yaml.safe_load(match.group(1))
+        loaded = yaml.load(match.group(1), Loader=_UniqueKeyLoader)
     except yaml.YAMLError as exc:
         raise FrontmatterParseError(str(exc)) from exc
     if not isinstance(loaded, dict):
@@ -292,6 +314,7 @@ class ProjectConfig:
         adr_version: str | None = None,
         python_tooling_version: str | None = None,
         markdown_tooling_version: str | None = None,
+        references_enabled: bool = False,
     ) -> None:
         self.schema = schema
         self.include = include
@@ -302,6 +325,7 @@ class ProjectConfig:
         self.adr_version = adr_version
         self.python_tooling_version = python_tooling_version
         self.markdown_tooling_version = markdown_tooling_version
+        self.references_enabled = references_enabled
 
 
 def resolve_effective_schema(
@@ -320,7 +344,7 @@ def resolve_effective_schema(
     if args_schema is not None:
         return args_schema
     schema_value = config.schema
-    custom_path = _schema_value_is_path(schema_value)
+    custom_path = schema_value_is_path(schema_value)
     if custom_path and config.frontmatter_version is not None:
         raise ConfigError(
             "set markdown.frontmatter.schema (a custom path) or "
@@ -343,7 +367,7 @@ def frontmatter_adr_incompatibility(config: ProjectConfig, registry: Registry) -
     version as an incompatibility). Returns None when compatible or not applicable;
     raises RegistryError if the configured ADR version is unknown.
     """
-    if _schema_value_is_path(config.schema):
+    if schema_value_is_path(config.schema):
         return None
     if not (config.require_adr_sections or config.adr_version is not None):
         return None
@@ -376,6 +400,7 @@ def load_config(path: Path) -> ProjectConfig:
     adr_version: str | None = None
     python_tooling_version: str | None = None
     markdown_tooling_version: str | None = None
+    references_enabled = False
 
     if path.exists():
         try:
@@ -397,6 +422,12 @@ def load_config(path: Path) -> ProjectConfig:
                     required = bool(fm.get("required", True))
                     version_val = fm.get("version")
                     frontmatter_version = str(version_val) if version_val is not None else None
+                    references = fm.get("references")
+                    if isinstance(references, dict):
+                        references_dict = cast("dict[str, Any]", references)
+                        references_enabled = bool(references_dict.get("enabled", False))
+                    else:
+                        references_enabled = False
                 adr = markdown_dict.get("adr")
                 if isinstance(adr, dict):
                     adr_dict = cast("dict[str, Any]", adr)
@@ -426,6 +457,7 @@ def load_config(path: Path) -> ProjectConfig:
         adr_version=adr_version,
         python_tooling_version=python_tooling_version,
         markdown_tooling_version=markdown_tooling_version,
+        references_enabled=references_enabled,
     )
 
 
diff --git a/src/project_standards/validate_id.py b/src/project_standards/validate_id.py
index 6bc5f5d..5edb54c 100644
--- a/src/project_standards/validate_id.py
+++ b/src/project_standards/validate_id.py
@@ -51,13 +51,11 @@ from __future__ import annotations
 import argparse
 import json
 import re
-import secrets
-import string
 import sys
-import unicodedata
 from pathlib import Path
 from typing import Any
 
+from project_standards.id_format import random_token, slugify
 from project_standards.validate_frontmatter import (
     ConfigError,
     FrontmatterParseError,
@@ -68,9 +66,6 @@ from project_standards.validate_frontmatter import (
 
 _DEFAULT_CONFIG = Path(".project-standards.yml")
 
-# Characters used to generate the 6-character base-36 token (digits + lowercase letters).
-_BASE36_CHARS = string.digits + string.ascii_lowercase
-
 # Load the doc_type enum directly from the bundled schema so this list never drifts.
 # No valid doc_type contains a hyphen, which makes split('-', 2) safe: the first segment
 # is always the doc_type prefix with no ambiguity.
@@ -96,30 +91,6 @@ _KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
 _ADR_ID_RE = re.compile(r"^adr-[0-9]{4,}-[a-z0-9]+(-[a-z0-9]+)+$")
 
 
-def slugify(text: str) -> str:
-    """Convert *text* to a lowercase kebab-case slug.
-
-    Normalises Unicode to ASCII, lowercases, then collapses any run of
-    non-alphanumeric characters to a single hyphen. This is the canonical transform
-    for deriving the title-slug portion of a document ``id``.
-
-    Examples::
-
-        slugify("Tailscale ACL tag ordering gotcha")
-        # → "tailscale-acl-tag-ordering-gotcha"
-
-        slugify("Standards Adoption & Compliance Procedure")
-        # → "standards-adoption-compliance-procedure"
-    """
-    # Strip accent marks (e.g. é → e) before lowercasing.
-    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
-    text = text.lower()
-    # Collapse any run of non-alphanumeric characters (spaces, punctuation, symbols)
-    # to a single hyphen, then strip leading/trailing hyphens.
-    text = re.sub(r"[^a-z0-9]+", "-", text)
-    return text.strip("-")
-
-
 def _validate_adr_id(doc_id: str) -> list[str]:
     """Return violation messages for an ADR id; empty list means valid.
 
@@ -317,7 +288,7 @@ def fix_file(path: Path) -> str | None:
         return None
     if not isinstance(title, str) or not title.strip():
         return None
-    token = "".join(secrets.choice(_BASE36_CHARS) for _ in range(6))
+    token = random_token()
     slug = slugify(title)
     if not slug:
         return None
@@ -417,7 +388,7 @@ def main(argv: list[str] | None = None) -> int:
     # via the --schema CLI flag or via a config-level path.  A bare token like
     # "markdown-frontmatter" is a bundled schema name; anything containing a path
     # separator or ending in ".json" is consumer-owned and may define different id
-    # conventions.  Mirrors the _schema_value_is_path check in validate_frontmatter.
+    # conventions.  Mirrors the schema_value_is_path check in validate_frontmatter.
     config_schema = config.schema
     config_has_custom_schema = config_schema is not None and (
         "/" in config_schema or "\\" in config_schema or config_schema.endswith(".json")
diff --git a/src/project_standards/validate_references.py b/src/project_standards/validate_references.py
new file mode 100644
index 0000000..c4838e7
--- /dev/null
+++ b/src/project_standards/validate_references.py
@@ -0,0 +1,225 @@
+"""Opt-in cross-file frontmatter checks the JSON Schema cannot express: id
+uniqueness, referential integrity, supersede reciprocity, date ordering, ADR
+sequence. Repo-wide pass; warnings never fail the build, errors do."""
+
+from __future__ import annotations
+
+import argparse
+import re as _re
+import sys
+from dataclasses import dataclass, field
+from pathlib import Path
+from typing import Any, cast
+
+from project_standards.validate_frontmatter import (
+    ConfigError,
+    FrontmatterParseError,
+    collect_paths,
+    load_config,
+    parse_frontmatter,
+    schema_value_is_path,
+)
+
+_DEFAULT_CONFIG = Path(".project-standards.yml")
+_REF_FIELDS = ("related", "depends_on", "supersedes", "superseded_by")  # NOT applies_to
+
+_ADR_NUM_RE = _re.compile(r"^adr-([0-9]{4,})-")
+
+
+@dataclass
+class Doc:
+    path: Path
+    meta: dict[str, Any]
+
+
+@dataclass
+class Index:
+    docs: list[Doc] = field(default_factory=list)
+    by_id: dict[str, list[Path]] = field(default_factory=dict)
+    ids: set[str] = field(default_factory=set)
+
+
+def build_index(paths: list[Path]) -> Index:
+    index = Index()
+    for path in paths:
+        try:
+            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
+        except OSError, FrontmatterParseError:
+            continue
+        if not isinstance(meta, dict):
+            continue
+        doc = Doc(path=path, meta=meta)
+        index.docs.append(doc)
+        doc_id = meta.get("id")
+        if isinstance(doc_id, str) and doc_id:
+            index.by_id.setdefault(doc_id, []).append(path)
+            index.ids.add(doc_id)
+    return index
+
+
+def check_id_uniqueness(index: Index) -> list[str]:
+    errors: list[str] = []
+    for doc_id, paths in sorted(index.by_id.items()):
+        if len(paths) > 1:
+            joined = ", ".join(str(p) for p in sorted(paths))
+            errors.append(f"[error] duplicate id '{doc_id}' in: {joined}")
+    return errors
+
+
+def check_dates(index: Index) -> list[str]:
+    errors: list[str] = []
+    for doc in index.docs:
+        created = doc.meta.get("created")
+        updated = doc.meta.get("updated")
+        reviewed = doc.meta.get("reviewed")
+        if isinstance(created, str) and isinstance(updated, str) and created > updated:
+            errors.append(f"[error] {doc.path}: created '{created}' is after updated '{updated}'")
+        if isinstance(reviewed, str) and isinstance(created, str) and reviewed < created:
+            errors.append(
+                f"[error] {doc.path}: reviewed '{reviewed}' is before created '{created}'"
+            )
+    return errors
+
+
+def _ref_values(meta: dict[str, Any]) -> list[str]:
+    values: list[str] = []
+    for field_name in _REF_FIELDS:
+        val = meta.get(field_name)
+        if val is None:
+            continue
+        if isinstance(val, str):
+            values.append(val)
+        elif isinstance(val, list):
+            val_list = cast("list[Any]", val)
+            values.extend(v for v in val_list if isinstance(v, str) and v)
+    return values
+
+
+def _resolves(ref: str, index: Index, repo_root: Path) -> bool:
+    if ref in index.ids:  # exact id match
+        return True
+    if "#" in ref:  # section anchors are not document references (standard)
+        return False
+    if ref.startswith(("/", "../")) or "/../" in ref:
+        return False
+    return (repo_root / ref).is_file()
+
+
+def check_references(index: Index, repo_root: Path) -> list[str]:
+    warnings: list[str] = []
+    for doc in index.docs:
+        for ref in _ref_values(doc.meta):
+            if not _resolves(ref, index, repo_root):
+                warnings.append(f"[warning] {doc.path}: unresolved reference '{ref}'")
+    return warnings
+
+
+def _as_list(val: Any) -> list[str]:
+    if isinstance(val, str):
+        return [val]
+    if isinstance(val, list):
+        val_list = cast("list[Any]", val)
+        return [v for v in val_list if isinstance(v, str)]
+    return []
+
+
+def check_reciprocity(index: Index) -> list[str]:
+    """Both directions of the supersede invariant (CR-004): A.superseded_by=B requires
+    B.supersedes=A, AND A.supersedes=B requires B.superseded_by=A. Only checked when
+    the counterpart doc is local (cross-repo ids can't be inspected)."""
+    warnings: list[str] = []
+    supersedes_map = {
+        d.meta.get("id"): set(_as_list(d.meta.get("supersedes")))
+        for d in index.docs
+        if isinstance(d.meta.get("id"), str)
+    }
+    superseded_by_map = {
+        d.meta.get("id"): set(_as_list(d.meta.get("superseded_by")))
+        for d in index.docs
+        if isinstance(d.meta.get("id"), str)
+    }
+    for doc in index.docs:
+        a_id = doc.meta.get("id")
+        for b_id in _as_list(doc.meta.get("superseded_by")):
+            if b_id in supersedes_map and a_id not in supersedes_map[b_id]:
+                warnings.append(
+                    f"[warning] {doc.path}: '{a_id}' is superseded_by '{b_id}', "
+                    f"but '{b_id}' does not list it in supersedes"
+                )
+        for b_id in _as_list(doc.meta.get("supersedes")):
+            if b_id in superseded_by_map and a_id not in superseded_by_map[b_id]:
+                warnings.append(
+                    f"[warning] {doc.path}: '{a_id}' supersedes '{b_id}', "
+                    f"but '{b_id}' does not list it in superseded_by"
+                )
+    return warnings
+
+
+def check_adr_sequence(index: Index) -> list[str]:
+    by_num: dict[str, list[str]] = {}
+    for doc in index.docs:
+        if doc.meta.get("doc_type") != "adr":
+            continue
+        doc_id = doc.meta.get("id")
+        if not isinstance(doc_id, str):
+            continue
+        m = _ADR_NUM_RE.match(doc_id)
+        if m:
+            by_num.setdefault(m.group(1), []).append(doc_id)
+    return [
+        f"[error] duplicate ADR number {num}: {', '.join(sorted(ids))}"
+        for num, ids in sorted(by_num.items())
+        if len(ids) > 1
+    ]
+
+
+def main(argv: list[str] | None = None) -> int:
+    parser = argparse.ArgumentParser(prog="validate-references", description=__doc__)
+    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
+    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
+    parser.add_argument("--schema", type=Path, default=None)
+    parser.add_argument("--glob", metavar="PATTERN")
+    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
+    parser.add_argument("--quiet", "-q", action="store_true")
+    args = parser.parse_args(argv)
+
+    try:
+        config = load_config(args.config)
+    except ConfigError as exc:
+        print(f"error: {exc}", file=sys.stderr)
+        return 2
+    if not config.references_enabled:
+        return 0  # opt-in: disabled -> no checks
+    if args.schema is not None or schema_value_is_path(config.schema):
+        if not args.quiet:
+            print("note: custom schema in use; skipping reference validation")
+        return 0
+
+    # validate-references is a REPO-WIDE invariant pass (duplicate ids / ADR numbers,
+    # cross-file references), so the index MUST cover the full configured set even when
+    # the caller scopes to specific FILE / --glob (project-standards validate forwards
+    # them) — otherwise a duplicate in an unselected doc is silently missed (codex P2).
+    paths = collect_paths([], None, config.include, config.exclude)
+    index = build_index(paths)
+    errors: list[str] = []
+    warnings: list[str] = []
+    errors += check_id_uniqueness(index)
+    errors += check_dates(index)
+    warnings += check_references(index, Path.cwd())
+    warnings += check_reciprocity(index)
+    errors += check_adr_sequence(index)
+
+    for w in warnings:
+        print(w, file=sys.stderr)
+    for e in errors:
+        print(e, file=sys.stderr)
+    if errors:
+        print(f"\n✗  {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
+        return 1
+    if not args.quiet:
+        print(f"✓  references valid ({len(index.docs)} docs, {len(warnings)} warning(s))")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tests/test_cli_fix.py b/tests/test_cli_fix.py
new file mode 100644
index 0000000..7a2200a
--- /dev/null
+++ b/tests/test_cli_fix.py
@@ -0,0 +1,147 @@
+import subprocess
+import sys
+from pathlib import Path
+
+
+def _ps(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
+    return subprocess.run(
+        [sys.executable, "-m", "project_standards.cli", *args],
+        capture_output=True,
+        text=True,
+        cwd=cwd,
+    )
+
+
+def _doc(p: Path, **fm: str) -> None:
+    p.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# B\n")
+
+
+def test_validate_runs_references_when_enabled(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    # duplicate id -> references error -> validate must fail
+    _doc(
+        tmp_path / "a.md",
+        schema_version="'1.1'",
+        id="'note-aaaaaa-x'",
+        title="'A'",
+        description="'d'",
+        doc_type="'note'",
+        status="'draft'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        tags="[]",
+        aliases="[]",
+        related="[]",
+    )
+    _doc(
+        tmp_path / "b.md",
+        schema_version="'1.1'",
+        id="'note-aaaaaa-x'",
+        title="'B'",
+        description="'d'",
+        doc_type="'note'",
+        status="'draft'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        tags="[]",
+        aliases="[]",
+        related="[]",
+    )
+    r = _ps(["validate", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 1
+    assert "duplicate id" in (r.stdout + r.stderr)
+
+
+def test_fix_leaves_validate_clean_for_type_and_bad_id(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    # `type` instead of doc_type AND an invalid id: format fixes doc_type, then id-fix fixes id.
+    (tmp_path / "a.md").write_text(
+        "---\n"
+        "schema_version: '1.1'\n"
+        "id: 'wrong'\n"
+        "title: 'Hello World'\n"
+        "description: 'd'\n"
+        "type: 'note'\n"
+        "status: 'draft'\n"
+        "created: '2026-01-01'\n"
+        "updated: '2026-01-02'\n"
+        "tags: []\n"
+        "aliases: []\n"
+        "related: []\n"
+        "---\n# B\n"
+    )
+    r = _ps(["fix", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 0
+    text = (tmp_path / "a.md").read_text()
+    assert "doc_type: 'note'" in text
+    assert "id: 'note-" in text  # id regenerated from doc_type+title
+    # postcondition: a follow-up validate is clean
+    assert _ps(["validate", "--config", str(cfg)], tmp_path).returncode == 0
+
+
+def _full(did: str = "a", doc_id: str = "note-aaaaaa-x") -> str:
+    return (
+        "---\n"
+        "schema_version: '1.1'\n"
+        f"id: '{doc_id}'\n"
+        f"title: '{did}'\n"
+        "description: 'd'\n"
+        "doc_type: 'note'\n"
+        "status: 'draft'\n"
+        "created: '2026-01-01'\n"
+        "updated: '2026-01-02'\n"
+        "tags: []\n"
+        "aliases: []\n"
+        "related: []\n"
+        "---\n# B\n"
+    )
+
+
+def test_fix_fails_on_reference_error_when_enabled(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    # Both docs are schema-valid and id-valid, but share an id -> ONLY a reference error.
+    (tmp_path / "a.md").write_text(_full("a"))
+    (tmp_path / "b.md").write_text(_full("b"))  # same id -> duplicate
+    r = _ps(["fix", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 1  # CR-001: final validate (incl. references) catches the dup id
+
+
+def test_fix_skips_under_custom_schema(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['*.md']\n"
+    )
+    before = "---\ntitle: X\n---\n# B\n"
+    (tmp_path / "a.md").write_text(before)
+    r = _ps(["fix", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 0
+    assert (tmp_path / "a.md").read_text() == before  # CR-001: no writes under custom schema
+
+
+def test_fix_skips_with_schema_flag(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    before = "---\ntitle: X\n---\n# B\n"
+    (tmp_path / "a.md").write_text(before)
+    r = _ps(["fix", "--schema", "custom.json", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 0
+    assert (tmp_path / "a.md").read_text() == before  # CR-001: forwarded --schema -> skip
+
+
+def test_validate_fails_on_duplicate_keys(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    (tmp_path / "a.md").write_text(
+        "---\nschema_version: '1.1'\nid: 'note-aaaaaa-x'\ntitle: 'A'\n"
+        "description: 'd'\ndoc_type: 'note'\nstatus: 'draft'\ncreated: '2026-01-01'\n"
+        "updated: '2026-01-02'\ntags: []\ntags: ['dup']\naliases: []\nrelated: []\n---\n# B\n"
+    )
+    r = _ps(["validate", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 1  # CR-002: duplicate key -> parse error -> validate fails
diff --git a/tests/test_format_frontmatter.py b/tests/test_format_frontmatter.py
new file mode 100644
index 0000000..2d0e870
--- /dev/null
+++ b/tests/test_format_frontmatter.py
@@ -0,0 +1,883 @@
+import io
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+from project_standards.format_frontmatter import (
+    Entry,
+    _leading_run,  # pyright: ignore[reportPrivateUsage]
+    _split_value_comment,  # pyright: ignore[reportPrivateUsage]
+    _today_iso,  # pyright: ignore[reportPrivateUsage]
+    format_text,
+    main,
+    tokenize,
+)
+
+CLEAN = (
+    "---\n"
+    "schema_version: '1.1'\n"
+    "id: 'note-a3f9zk-x'\n"
+    "title: 'X'\n"
+    "description: 'A doc.'\n"
+    "doc_type: 'note'\n"
+    "status: 'draft'\n"
+    "created: '2026-06-08'\n"
+    "updated: '2026-06-08'\n"
+    "tags: []\n"
+    "aliases: []\n"
+    "related: []\n"
+    "---\n"
+    "# Body\n"
+)
+
+
+def test_clean_input_is_byte_identical():
+    # format_text returns (new_text, changed, warnings). Already-canonical -> no change.
+    new, changed, _warnings = format_text(CLEAN, path=None)
+    assert new == CLEAN
+    assert changed is False
+
+
+def test_no_frontmatter_is_noop():
+    body = "# Just a body\n\nNo frontmatter here.\n"
+    new, changed, _warnings = format_text(body, path=None)
+    assert new == body
+    assert changed is False
+
+
+def test_comment_block_preserved_on_roundtrip():
+    src = CLEAN.replace("id: 'note-a3f9zk-x'\n", "id: 'note-a3f9zk-x'  # frozen at creation\n")
+    new, changed, _warnings = format_text(src, path=None)
+    assert "# frozen at creation" in new
+    assert changed is False
+
+
+def test_duplicate_top_level_key_is_refused():
+    # PyYAML silently keeps the last duplicate; the formatter must NOT rewrite such a
+    # block (it would erase the human-visible conflict). It skips with a warning. (CR-002)
+    src = CLEAN.replace("tags: []\n", "tags: []\ntags: ['x']\n")
+    new, changed, warnings = format_text(src, path=None)
+    assert new == src
+    assert changed is False
+    assert any("duplicate" in w for w in warnings)
+
+
+def test_reorder_to_canonical_order():
+    src = (
+        "---\n"
+        "title: 'X'\n"
+        "schema_version: '1.1'\n"
+        "doc_type: 'note'\n"
+        "id: 'note-a3f9zk-x'\n"
+        "description: 'A doc.'\n"
+        "status: 'draft'\n"
+        "created: '2026-06-08'\n"
+        "updated: '2026-06-08'\n"
+        "tags: []\n"
+        "aliases: []\n"
+        "related: []\n"
+        "---\n"
+    )
+    new, changed, _ = format_text(src, path=None)
+    keys = [ln.split(":")[0] for ln in new.splitlines() if ln and not ln.startswith("-")]
+    assert keys[:4] == ["schema_version", "id", "title", "description"]
+    assert changed is True
+
+
+def test_unknown_key_sorts_after_known_keys():
+    src = (
+        "---\n"
+        "schema_version: '1.1'\n"
+        "custom_thing: 'x'\n"
+        "id: 'note-a3f9zk-x'\n"
+        "title: 'X'\n"
+        "description: 'A doc.'\n"
+        "doc_type: 'note'\n"
+        "status: 'draft'\n"
+        "created: '2026-06-08'\n"
+        "updated: '2026-06-08'\n"
+        "tags: []\n"
+        "aliases: []\n"
+        "related: []\n"
+        "---\n"
+    )
+    new, _, warnings = format_text(src, path=None)
+    lines = [ln for ln in new.splitlines() if ":" in ln]
+    assert lines.index("custom_thing: 'x'") > lines.index("related: []")
+    assert any("custom_thing" in w for w in warnings)
+
+
+def _doc(*, title: str = "X", extra: str = "", tags_line: str = "tags: []") -> str:
+    # tags_line lets a test vary the tags entry WITHOUT appending a second `tags:`
+    # (which would create a duplicate key the formatter now refuses — CR-002).
+    return (
+        "---\n"
+        "schema_version: '1.1'\n"
+        "id: 'note-a3f9zk-x'\n"
+        f"title: {title}\n"
+        "description: 'A doc.'\n"
+        "doc_type: 'note'\n"
+        "status: 'draft'\n"
+        "created: '2026-06-08'\n"
+        "updated: '2026-06-08'\n"
+        f"{tags_line}\n"
+        "aliases: []\n"
+        "related: []\n"
+        f"{extra}"
+        "---\n"
+    )
+
+
+def test_unquoted_scalars_get_single_quoted():
+    src = (
+        "---\n"
+        "schema_version: 1.1\n"  # identifier-like number -> '1.1'
+        "id: 'note-a3f9zk-x'\n"
+        "title: X\n"  # bare string -> 'X'
+        "description: A doc.\n"
+        "doc_type: note\n"
+        "status: draft\n"
+        "created: 2026-06-08\n"  # unquoted date -> '2026-06-08'
+        "updated: '2026-06-08'\n"
+        "tags: []\n"
+        "aliases: []\n"
+        "related: []\n"
+        "---\n"
+    )
+    new, changed, _ = format_text(src, path=None)
+    assert "schema_version: '1.1'" in new
+    assert "title: 'X'" in new
+    assert "created: '2026-06-08'" in new
+    assert "doc_type: 'note'" in new
+    assert changed is True
+
+
+def test_null_license_stays_null():
+    src = _doc(extra="license: null\n")  # helper defined below
+    new, _, _ = format_text(src, path=None)
+    assert "license: null" in new
+    assert "license: 'null'" not in new
+
+
+def test_double_quoted_becomes_single_quoted():
+    src = _doc(title='"Hello"')
+    new, _, _ = format_text(src, path=None)
+    assert "title: 'Hello'" in new
+
+
+@pytest.mark.parametrize("token", ["on", "off", "Yes", "No"])
+def test_boolean_like_scalar_kept_as_string(token: str) -> None:
+    # `title: on` must become `title: 'on'`, NOT 'true' (CR-NEW-001).
+    src = _doc(title=token)
+    new, _, _ = format_text(src, path=None)
+    assert f"title: '{token}'" in new
+
+
+def test_hash_in_plain_scalar_is_not_a_comment():
+    # `C#` has no whitespace before '#', so it is scalar content, not a comment (CR-NEW-003).
+    src = _doc(title="C# guide")
+    new, _, _ = format_text(src, path=None)
+    assert "title: 'C# guide'" in new
+
+
+def test_url_fragment_preserved():
+    src = _doc(title="http://example.com/p#frag")
+    new, _, _ = format_text(src, path=None)
+    assert "title: 'http://example.com/p#frag'" in new
+
+
+def test_real_inline_comment_preserved_on_scalar():
+    src = _doc(title="X  # keep me")  # whitespace + '#' IS a real comment
+    new, _, _ = format_text(src, path=None)
+    assert "title: 'X'  # keep me" in new
+
+
+def test_flow_list_becomes_block_and_dedupes():
+    src = _doc(tags_line="tags: ['a', 'b', 'a']")
+    new, changed, _ = format_text(src, path=None)
+    assert "tags:\n  - 'a'\n  - 'b'\n" in new
+    assert new.count("- 'a'") == 1
+    assert changed is True
+
+
+def test_empty_block_list_becomes_flow_empty():
+    src = _doc(tags_line="tags:")  # key with no value and no items -> tags: []
+    new, _, _ = format_text(src, path=None)
+    assert "tags: []" in new
+
+
+def test_boolean_like_list_items_kept_as_strings():
+    # list items must not be coerced (BaseLoader); [on, off, yes, no] stay strings (CR-NEW-001).
+    src = _doc(tags_line="tags: [on, off, yes, no]")
+    new, _, _ = format_text(src, path=None)
+    assert "- 'on'" in new and "- 'off'" in new and "- 'yes'" in new and "- 'no'" in new
+    assert "True" not in new and "False" not in new
+
+
+def test_inline_comment_preserved_on_flow_list():
+    src = _doc(tags_line="tags: [a, b]  # keep")  # CR-NEW-004
+    new, _, _ = format_text(src, path=None)
+    assert "tags:  # keep" in new  # comment moves to the block key line
+    assert "- 'a'" in new and "- 'b'" in new
+
+
+def test_inline_comment_preserved_on_empty_list():
+    src = _doc(tags_line="tags: []  # keep")  # CR-NEW-004
+    new, _, _ = format_text(src, path=None)
+    assert "tags: []  # keep" in new
+
+
+def test_hash_inside_quoted_list_item_not_a_comment():
+    src = _doc(extra="source: ['Issue #123']\n")  # CR-NEW-005: '#' inside quote is literal
+    new, _, _ = format_text(src, path=Path("docs/x.md"))
+    assert "- 'Issue #123'" in new  # whole item preserved, '#' kept
+    assert "source: []" not in new  # not emptied / mis-split
+
+
+def test_real_comment_after_quoted_list_item_preserved():
+    src = _doc(extra="source: ['Issue #123']  # keep\n")  # CR-NEW-005
+    new, _, _ = format_text(src, path=Path("docs/x.md"))
+    assert "- 'Issue #123'" in new
+    assert "source:  # keep" in new
+
+
+def test_type_renamed_to_doc_type_when_absent():
+    src = _doc().replace("doc_type: 'note'\n", "type: 'note'\n")
+    new, changed, _ = format_text(src, path=None)
+    assert "doc_type: 'note'" in new
+    assert "\ntype:" not in new
+    assert changed is True
+
+
+def test_both_type_and_doc_type_present_warns_keeps_both():
+    src = _doc(extra="type: 'x'\n")
+    new, _, warnings = format_text(src, path=None)
+    assert "doc_type: 'note'" in new
+    assert any("type" in w.lower() for w in warnings)
+
+
+def test_missing_required_arrays_injected():
+    src = (
+        "---\n"
+        "schema_version: '1.1'\n"
+        "id: 'note-a3f9zk-x'\n"
+        "title: 'X'\n"
+        "description: 'A doc.'\n"
+        "doc_type: 'note'\n"
+        "status: 'draft'\n"
+        "created: '2026-06-08'\n"
+        "updated: '2026-06-08'\n"
+        "---\n"
+    )
+    new, changed, _ = format_text(src, path=None)
+    assert "tags: []" in new and "aliases: []" in new and "related: []" in new
+    assert changed is True
+
+
+def test_schema_version_injected_when_missing():
+    src = _doc().replace("schema_version: '1.1'\n", "")
+    new, _, _ = format_text(src, path=None)
+    assert "schema_version: '1.1'" in new
+
+
+def test_doc_type_filled_from_readme_path_when_missing():
+    src = _doc().replace("doc_type: 'note'\n", "")  # no doc_type
+    new, _, _ = format_text(src, path=Path("README.md"))
+    assert "doc_type: 'index'" in new
+
+
+def test_doc_type_research_under_docs_research_when_invalid():
+    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'bogus'\n")
+    new, _, _ = format_text(src, path=Path("docs/research/x.md"))
+    assert "doc_type: 'research'" in new
+
+
+def test_valid_doc_type_never_overridden_by_path():
+    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'reference'\n")
+    new, _, _ = format_text(src, path=Path("README.md"))
+    assert "doc_type: 'reference'" in new  # SA-001: valid value preserved
+    assert "doc_type: 'index'" not in new
+
+
+def test_denylisted_paths_are_refused():
+    from project_standards.format_frontmatter import is_denylisted
+
+    assert is_denylisted(Path("CLAUDE.md"))
+    assert is_denylisted(Path("sub/AGENTS.md"))
+    assert is_denylisted(Path(".claude/settings.md"))
+    assert is_denylisted(Path("x/.codex/y.md"))
+    assert not is_denylisted(Path("docs/note.md"))
+
+
+def test_extension_object_nested_bytes_preserved():
+    src = (
+        "---\n"
+        "schema_version: '1.1'\n"
+        "id: 'note-a3f9zk-x'\n"
+        "title: 'X'\n"
+        "description: 'A doc.'\n"
+        "doc_type: 'note'\n"
+        "status: 'draft'\n"
+        "created: '2026-06-08'\n"
+        "updated: '2026-06-08'\n"
+        "tags: []\n"
+        "aliases: []\n"
+        "related: []\n"
+        "project:\n"
+        "  team: 'platform'\n"
+        "  nested:\n"
+        "    deep: 1\n"
+        "---\n"
+    )
+    new, changed, warnings = format_text(src, path=None)
+    assert "project:\n  team: 'platform'\n  nested:\n    deep: 1\n" in new
+    assert changed is False
+    assert warnings == []
+
+
+def test_crlf_line_endings_preserved():
+    src = _doc().replace("\n", "\r\n")
+    src = src.replace("title: X\r\n", "title: X\r\n") if "title: X" in src else src
+    # Force one change (unquoted) and assert CRLF survives on unchanged lines.
+    src = src.replace("title: 'X'\r\n", "title: X\r\n")
+    new, _changed, _ = format_text(src, path=None)
+    assert "\r\n" in new
+    assert "\n\n" not in new.replace("\r\n", "")  # no stray bare LFs introduced
+    assert "title: 'X'\r\n" in new
+
+
+def test_scaffold_injects_schema_valid_block():
+    body = "# Real Title\n\nSome content.\n"
+    new, changed, _ = format_text(
+        body, path=Path("docs/guide.md"), scaffold=True, today="2026-06-08"
+    )
+    assert new.startswith("---\n")
+    assert "title: 'Real Title'" in new
+    assert "doc_type: 'note'" in new  # no path rule -> note
+    assert "created: '2026-06-08'" in new and "updated: '2026-06-08'" in new
+    assert "description: 'TODO:" in new  # placeholder, schema-valid
+    assert "# Real Title" in new  # body preserved
+    assert changed is True
+
+
+def test_scaffold_disabled_leaves_body_untouched():
+    body = "# Title\n\nContent.\n"
+    new, changed, _ = format_text(body, path=Path("docs/guide.md"), scaffold=False)
+    assert new == body and changed is False
+
+
+def test_scaffold_uses_path_doc_type_rule():
+    new, _, _ = format_text("# R\n", path=Path("README.md"), scaffold=True, today="2026-06-08")
+    assert "doc_type: 'index'" in new
+
+
+def _run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
+    return subprocess.run(
+        [sys.executable, "-m", "project_standards.format_frontmatter", *args],
+        capture_output=True,
+        text=True,
+        **kw,  # type: ignore[call-overload]
+    )
+
+
+def test_check_exits_1_when_would_change(tmp_path: Path) -> None:
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
+    assert r.returncode == 1
+
+
+def test_write_formats_in_place_atomically(tmp_path: Path) -> None:
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    r = _run(["--write", "--config", str(cfg), str(f)], cwd=tmp_path)
+    assert r.returncode == 0
+    assert "title: 'X'" in f.read_text()
+
+
+def test_stdin_mode_round_trips() -> None:
+    r = _run(["--stdin"], input=_doc(title="X").replace("title: 'X'", "title: X"))
+    assert r.returncode == 0
+    assert "title: 'X'" in r.stdout
+
+
+def test_custom_schema_skips(tmp_path: Path) -> None:
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['*.md']\n"
+    )
+    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
+    assert r.returncode == 0
+    assert "custom schema" in (r.stdout + r.stderr).lower()
+
+
+@pytest.mark.parametrize("conflict", [["x.md"], ["--glob", "*.md"], ["--write"]])
+def test_stdin_conflicts_exit_2(conflict: list[str]) -> None:
+    r = _run(["--stdin", *conflict], input="---\ntitle: 'X'\n---\n")
+    assert r.returncode == 2
+    assert "stdin" in (r.stdout + r.stderr).lower()
+
+
+CASES = [
+    _doc(title="X").replace("title: 'X'", "title: X"),
+    _doc(tags_line="tags: ['b','a','b']"),
+    _doc().replace("schema_version: '1.1'\n", ""),
+    _doc().replace("doc_type: 'note'\n", "type: 'note'\n"),
+]
+
+
+@pytest.mark.parametrize("src", CASES)
+def test_format_is_idempotent(src: str) -> None:
+    once, _, _ = format_text(src, path=Path("docs/x.md"))
+    twice, changed2, _ = format_text(once, path=Path("docs/x.md"))
+    assert twice == once
+    assert changed2 is False
+
+
+# ---------------------------------------------------------------------------
+# In-process unit tests for tokenize() / _split_value_comment / _leading_run
+# ---------------------------------------------------------------------------
+
+
+def test_tokenize_blank_and_comment_lines_become_pending() -> None:
+    # Covers lines 97-100 (blank/comment append to pending) and 126-127
+    # (pending flushed as a trailing key=None Entry at end).
+    body = "# top comment\n\ntitle: 'X'\n# tail\n"
+    entries, reason = tokenize(body)
+    assert reason is None
+    # first entry should carry the leading comment and blank
+    assert entries[0].key == "title"
+    assert any("# top comment" in ln for ln in entries[0].lines)
+    # trailing comment entry
+    last = entries[-1]
+    assert last.key is None
+    assert any("# tail" in ln for ln in last.lines)
+
+
+def test_tokenize_unrecognized_line_returns_reason() -> None:
+    # Covers line 103 — a line at column 0 that doesn't match key: syntax
+    # (e.g. a bare list item `- x` or a number-prefixed key)
+    body = "- orphan-list-item\n"
+    entries, reason = tokenize(body)
+    assert entries == []
+    assert reason is not None and "unrecognized" in reason
+
+
+def test_tokenize_unsupported_yaml_constructs() -> None:
+    # Covers line 107 — anchor, alias, block scalar
+    for bad_val in ("&anchor value", "*alias", "<< merge", "| block"):
+        body = f"title: {bad_val}\n"
+        entries, reason = tokenize(body)
+        assert entries == [], f"expected empty for {bad_val!r}"
+        assert reason is not None and "unsupported" in reason, f"bad reason for {bad_val!r}"
+
+
+def test_tokenize_blank_line_breaks_continuation() -> None:
+    # Covers line 119 — blank line inside a nested entry ends continuation
+    body = "tags:\n  - 'a'\n\ntitle: 'X'\n"
+    entries, reason = tokenize(body)
+    assert reason is None
+    tag_entry = next(e for e in entries if e.key == "tags")
+    # blank line is NOT included in the tag entry's lines (it ends it)
+    assert not any(ln.strip() == "" for ln in tag_entry.lines)
+
+
+def test_split_value_comment_single_quoted_with_escaped_quote() -> None:
+    # Covers lines 154-155 — escaped '' inside single-quoted scalar
+    val, comment = _split_value_comment(" 'it''s here'  # note")
+    assert val.strip() == "'it''s here'"
+    assert "# note" in comment
+
+
+def test_split_value_comment_double_quoted_with_escape() -> None:
+    # Covers lines 158-159 — backslash escape inside double-quoted scalar
+    val, comment = _split_value_comment(' "foo\\"bar"  # cmt')
+    assert val.strip().startswith('"')
+    assert "# cmt" in comment
+
+
+def test_split_value_comment_unterminated_single_quote() -> None:
+    # Covers line 163 — unterminated quote: whole rest returned as value
+    val, comment = _split_value_comment(" 'unterminated")
+    assert comment == ""
+    assert "unterminated" in val
+
+
+def test_split_value_comment_flow_list_with_inner_double_quote() -> None:
+    # Covers lines 173-174 and 177-178 — quote tracking inside flow list
+    val, comment = _split_value_comment(' ["foo\\"bar", \'baz\']  # keep')
+    assert val.strip().startswith("[")
+    assert "]" in val
+    assert "# keep" in comment
+
+
+def test_split_value_comment_flow_list_inner_single_quote_double_escape() -> None:
+    # Covers line 175-176 — '' escape inside single-quoted flow list item
+    val, comment = _split_value_comment(" ['it''s']")
+    assert val.strip() == "['it''s']"
+    assert comment == ""
+
+
+def test_split_value_comment_unbalanced_brackets() -> None:
+    # Covers line 191 — unbalanced brackets: no comment extracted
+    _val, comment = _split_value_comment(" [open but no close")
+    assert comment == ""
+
+
+def test_leading_run_counts_only_prefix_blanks_and_comments() -> None:
+    # Covers lines 256-262 — _leading_run returns count of leading blank/comment lines
+    entry = Entry(key="tags", lines=["# comment\n", "\n", "tags:\n", "  - 'a'\n"])
+    assert _leading_run(entry) == 2
+
+
+def test_normalize_lists_yaml_error_is_skipped() -> None:
+    # Covers lines 276-277 — yaml.YAMLError during load → continue (no crash)
+    # Build an entry whose lines produce invalid YAML when joined
+    entry = Entry(key="tags", lines=["tags: [\n", "  broken yaml\n"])
+    from project_standards.format_frontmatter import normalize_lists
+
+    normalize_lists([entry])  # must not raise
+    # lines unchanged (skipped)
+    assert entry.lines[0] == "tags: [\n"
+
+
+def test_normalize_lists_non_dict_load_skipped() -> None:
+    # The joined entry lines parse as a YAML list, not a mapping -> `not isinstance(
+    # loaded, dict)` is True and the entry is left untouched. Defensive guard: tokenize
+    # only ever builds `key:` entries, so this cannot arise in production; assert it via
+    # a direct Entry construction so the guard's contract is locked.
+    entry = Entry(key="tags", lines=["- list-item\n"])
+    from project_standards.format_frontmatter import normalize_lists
+
+    normalize_lists([entry])
+    assert entry.lines == ["- list-item\n"]  # unchanged (non-dict load skipped)
+
+
+def test_normalize_lists_scalar_where_list_expected_is_left() -> None:
+    # Covers line 282 — value is a scalar (not list/None/empty) -> left for validator
+    entry = Entry(key="tags", lines=["tags: not-a-list\n"])
+    from project_standards.format_frontmatter import normalize_lists
+
+    normalize_lists([entry])
+    assert "not-a-list" in entry.lines[0]
+
+
+def test_reorder_trailing_comment_entry_stays_last() -> None:
+    # Covers line 330 — trailing comment-only Entry (key=None) sort key
+    from project_standards.format_frontmatter import reorder
+
+    e_title = Entry(key="title", lines=["title: 'X'\n"])
+    e_tail = Entry(key=None, lines=["# trailing\n"])
+    warnings: list[str] = []
+    result = reorder([e_tail, e_title], warnings)
+    assert result[-1].key is None
+
+
+def test_today_iso_returns_valid_date() -> None:
+    # Covers line 444 — _today_iso() returns today's ISO date string
+    import datetime as _dt
+
+    result = _today_iso()
+    parsed = _dt.date.fromisoformat(result)
+    assert parsed == _dt.date.today()
+
+
+def test_scaffold_no_path_is_noop() -> None:
+    # Covers line 485 — scaffold=True but path=None -> returns text unchanged
+    body = "# Title\n\nContent.\n"
+    new, changed, _ = format_text(body, path=None, scaffold=True)
+    assert new == body
+    assert changed is False
+
+
+def test_bump_updated_sets_new_date() -> None:
+    # Covers lines 512-519 — bump_updated rewrites updated: when block changes
+    src = _doc(title="X").replace("title: 'X'", "title: X")  # unquoted -> will change
+    new, changed, _ = format_text(src, path=None, bump_updated=True, today="2099-01-01")
+    assert changed is True
+    assert "updated: '2099-01-01'" in new
+
+
+def test_bump_updated_noop_when_already_formatted() -> None:
+    # bump_updated only fires when the block actually changes; clean input -> no change
+    new, changed, _ = format_text(CLEAN, path=None, bump_updated=True, today="2099-01-01")
+    assert changed is False
+    assert "updated: '2099-01-01'" not in new
+
+
+# ---------------------------------------------------------------------------
+# In-process main() tests — CLI coverage
+# ---------------------------------------------------------------------------
+
+
+def _cfg(tmp_path: Path, *, include: str = "['**/*.md']", extra: str = "") -> Path:
+    """Write a minimal .project-standards.yml and return its path."""
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(f"markdown:\n  frontmatter:\n    include: {include}\n{extra}")
+    return cfg
+
+
+def test_main_check_exits_1_when_file_would_change(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = _cfg(tmp_path)
+    rc = main(["--check", "--config", str(cfg), str(f)])
+    assert rc == 1
+
+
+def test_main_check_exits_0_when_already_clean(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "clean.md"
+    f.write_text(CLEAN)
+    cfg = _cfg(tmp_path)
+    rc = main(["--check", "--config", str(cfg), str(f)])
+    assert rc == 0
+
+
+def test_main_write_rewrites_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = _cfg(tmp_path)
+    rc = main(["--write", "--config", str(cfg), str(f)])
+    assert rc == 0
+    assert "title: 'X'" in f.read_text()
+
+
+def test_main_write_preserves_file_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    # Exercises _atomic_write: set a non-default mode, assert it survives the rewrite
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    f.chmod(0o644)
+    cfg = _cfg(tmp_path)
+    rc = main(["--write", "--config", str(cfg), str(f)])
+    assert rc == 0
+    mode = f.stat().st_mode & 0o777
+    assert mode == 0o644
+
+
+def test_main_write_preserves_executable_mode(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    # A non-default mode (0o755) must survive the atomic rewrite
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    f.chmod(0o755)
+    cfg = _cfg(tmp_path)
+    rc = main(["--write", "--config", str(cfg), str(f)])
+    assert rc == 0
+    assert (f.stat().st_mode & 0o777) == 0o755
+
+
+def test_main_stdin_round_trips(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    src = _doc(title="X").replace("title: 'X'", "title: X")
+    monkeypatch.setattr("sys.stdin", io.StringIO(src))
+    cfg = _cfg(tmp_path)
+    rc = main(["--stdin", "--config", str(cfg)])
+    assert rc == 0
+    out, _ = capsys.readouterr()
+    assert "title: 'X'" in out
+
+
+def test_main_stdin_with_file_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.chdir(tmp_path)
+    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
+    with pytest.raises(SystemExit) as exc:
+        main(["--stdin", "x.md"])
+    assert exc.value.code == 2
+
+
+def test_main_stdin_with_glob_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.chdir(tmp_path)
+    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
+    with pytest.raises(SystemExit) as exc:
+        main(["--stdin", "--glob", "*.md"])
+    assert exc.value.code == 2
+
+
+def test_main_stdin_with_write_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.chdir(tmp_path)
+    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
+    with pytest.raises(SystemExit) as exc:
+        main(["--stdin", "--write"])
+    assert exc.value.code == 2
+
+
+def test_main_custom_schema_via_config_skips(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = _cfg(
+        tmp_path,
+        extra="",
+    )
+    # Write config with a custom schema path
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['**/*.md']\n"
+    )
+    rc = main(["--check", "--config", str(cfg), str(f)])
+    assert rc == 0
+    out, err = capsys.readouterr()
+    assert "custom schema" in (out + err).lower()
+
+
+def test_main_custom_schema_via_flag_skips(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = _cfg(tmp_path)
+    # Pass a --schema flag pointing to a non-existent custom path
+    rc = main(["--check", "--config", str(cfg), "--schema", "custom/x.json", str(f)])
+    assert rc == 0
+    out, err = capsys.readouterr()
+    assert "custom schema" in (out + err).lower()
+
+
+def test_main_malformed_config_exits_2(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    cfg = tmp_path / ".project-standards.yml"
+    # Invalid YAML: tab character at start of line where not allowed
+    cfg.write_text("markdown:\n\t frontmatter: bad\n")
+    rc = main(["--check", "--config", str(cfg)])
+    assert rc == 2
+    _out, err = capsys.readouterr()
+    assert "error" in err.lower()
+
+
+def test_main_denylisted_file_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.chdir(tmp_path)
+    # CLAUDE.md with a frontmatter block that would be changed if processed
+    f = tmp_path / "CLAUDE.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = _cfg(tmp_path)
+    # Pass the denylist file explicitly as a positional arg
+    rc = main(["--check", "--config", str(cfg), str(f)])
+    # denylisted -> skipped -> no change detected -> 0
+    assert rc == 0
+
+
+def test_main_duplicate_key_warning_sets_exit_1(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    # Frontmatter with a duplicate key: tokenize returns reason "duplicate top-level key"
+    src = CLEAN.replace("tags: []\n", "tags: []\ntags: ['x']\n")
+    f = tmp_path / "dup.md"
+    f.write_text(src)
+    cfg = _cfg(tmp_path)
+    rc = main(["--check", "--config", str(cfg), str(f)])
+    _out, err = capsys.readouterr()
+    assert "duplicate" in err.lower()
+    # unparseable flag set -> returns 1 regardless of any_change
+    assert rc == 1
+
+
+def test_main_bump_updated_with_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.chdir(tmp_path)
+    # File with unquoted title so it will change; existing updated date in the past
+    f = tmp_path / "d.md"
+    old_content = _doc(title="X").replace("title: 'X'", "title: X")
+    # Replace the updated date with an obviously old value
+    old_content = old_content.replace("updated: '2026-06-08'", "updated: '2020-01-01'")
+    f.write_text(old_content)
+    cfg = _cfg(tmp_path)
+    rc = main(["--write", "--bump-updated", "--config", str(cfg), str(f)])
+    assert rc == 0
+    new_content = f.read_text()
+    # updated: must have changed from the old placeholder
+    assert "updated: '2020-01-01'" not in new_content
+    assert "updated:" in new_content
+
+
+def test_main_write_scaffold_on_no_frontmatter_docs_file(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    # A .md file under docs/ with no frontmatter: --write triggers scaffold
+    docs = tmp_path / "docs"
+    docs.mkdir()
+    f = docs / "guide.md"
+    f.write_text("# Guide Title\n\nSome content.\n")
+    cfg = _cfg(tmp_path, include="['docs/**/*.md']")
+    rc = main(["--write", "--config", str(cfg), str(f)])
+    assert rc == 0
+    content = f.read_text()
+    assert content.startswith("---\n")
+    assert "title: 'Guide Title'" in content
+    assert "doc_type: 'note'" in content
+
+
+def test_main_write_quiet_suppresses_output(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = _cfg(tmp_path)
+    rc = main(["--write", "--quiet", "--config", str(cfg), str(f)])
+    assert rc == 0
+    out, _ = capsys.readouterr()
+    assert out == ""
+
+
+def test_main_check_quiet_suppresses_output(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    f = tmp_path / "d.md"
+    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
+    cfg = _cfg(tmp_path)
+    rc = main(["--check", "--quiet", "--config", str(cfg), str(f)])
+    assert rc == 1
+    out, _ = capsys.readouterr()
+    assert out == ""
+
+
+def test_malformed_double_quoted_scalar_does_not_crash() -> None:
+    # An invalid double-quoted YAML escape must NOT crash the formatter (codex P3) —
+    # it can't safely re-quote, so it leaves the line for the validator to reject.
+    src = _doc(title='"bad \\q"')
+    new, _changed, _warnings = format_text(src, path=None)
+    assert 'title: "bad \\q"' in new  # line preserved, no traceback
+
+
+def test_scalar_with_leading_comment_is_requoted() -> None:
+    # A leading comment bundles into the key's entry; requote must still quote the
+    # scalar (codex P2) rather than skip the whole entry as a multi-line value.
+    src = _doc(title="X").replace("title: X", "# keep this note\ntitle: X")
+    new, _changed, _warnings = format_text(src, path=None)
+    assert "# keep this note" in new
+    assert "title: 'X'" in new
+
+
+def test_block_list_item_comment_is_preserved() -> None:
+    # Re-rendering a block list would drop per-item comments (codex P2); a comment-
+    # bearing list is left untouched so the authored note survives.
+    src = _doc(tags_line="tags:\n  - 'a'  # why a\n  - 'b'")
+    new, _changed, _warnings = format_text(src, path=None)
+    assert "# why a" in new
+    assert "- 'a'" in new and "- 'b'" in new
diff --git a/tests/test_id_format.py b/tests/test_id_format.py
new file mode 100644
index 0000000..becfa4b
--- /dev/null
+++ b/tests/test_id_format.py
@@ -0,0 +1,28 @@
+import re
+
+from project_standards.id_format import random_token, slugify
+
+
+def test_slugify_basic():
+    assert slugify("Tailscale ACL tag ordering gotcha") == "tailscale-acl-tag-ordering-gotcha"
+
+
+def test_slugify_strips_accents_and_punctuation():
+    assert (
+        slugify("Standards Adoption & Compliance Procedure")
+        == "standards-adoption-compliance-procedure"
+    )
+    assert slugify("café déjà") == "cafe-deja"
+
+
+def test_slugify_empty_for_symbol_only():
+    assert slugify("!!!") == ""
+
+
+def test_random_token_is_six_base36_chars():
+    tok = random_token()
+    assert re.fullmatch(r"[0-9a-z]{6}", tok)
+
+
+def test_random_token_varies():
+    assert len({random_token() for _ in range(50)}) > 1
diff --git a/tests/test_precommit_hooks.py b/tests/test_precommit_hooks.py
new file mode 100644
index 0000000..9bf542b
--- /dev/null
+++ b/tests/test_precommit_hooks.py
@@ -0,0 +1,33 @@
+# tests/test_precommit_hooks.py
+import tomllib
+from pathlib import Path
+
+import yaml
+
+REPO = Path(__file__).resolve().parents[1]
+
+
+def test_workflow_invokes_validate_references():
+    wf = (REPO / ".github/workflows/validate-markdown-frontmatter.yml").read_text()
+    assert "validate-references" in wf
+
+
+def test_hook_entries_map_to_console_scripts():
+    hooks = yaml.safe_load((REPO / ".pre-commit-hooks.yaml").read_text())
+    scripts = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["scripts"]
+    ids = {h["id"] for h in hooks}
+    assert {
+        "format-frontmatter-fix",
+        "format-frontmatter-check",
+        "validate-frontmatter",
+        "validate-references",
+    } <= ids
+    for h in hooks:
+        # entry's first token is the console-script name
+        assert h["entry"].split()[0] in scripts
+        assert h["language"] == "python"
+
+
+def test_references_hook_runs_whole_repo():
+    hooks = {h["id"]: h for h in yaml.safe_load((REPO / ".pre-commit-hooks.yaml").read_text())}
+    assert hooks["validate-references"]["pass_filenames"] is False
diff --git a/tests/test_validate_frontmatter.py b/tests/test_validate_frontmatter.py
index 22eb8a7..97b2fca 100644
--- a/tests/test_validate_frontmatter.py
+++ b/tests/test_validate_frontmatter.py
@@ -36,6 +36,7 @@ from jsonschema import Draft202012Validator
 
 import project_standards.validate_frontmatter as _vf
 from project_standards.validate_frontmatter import (
+    FrontmatterParseError,
     collect_paths,
     find_bundled_schema,
     load_config,
@@ -1297,3 +1298,25 @@ def test_unknown_markdown_tooling_version_exits_2(
     rc = main(["--config", ".project-standards.yml"])
     assert rc == 2
     assert "unknown markdown_tooling.version" in capsys.readouterr().err
+
+
+def test_references_enabled_defaults_false(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    assert load_config(cfg).references_enabled is False
+
+
+def test_references_enabled_true(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    references:\n      enabled: true\n")
+    assert load_config(cfg).references_enabled is True
+
+
+def test_duplicate_top_level_key_rejected() -> None:
+    with pytest.raises(FrontmatterParseError):
+        parse_frontmatter("---\ntags: []\ntags: ['x']\n---\n# body\n")
+
+
+def test_unique_keys_still_parse() -> None:
+    meta = parse_frontmatter("---\nid: 'x'\ntags: []\n---\n# body\n")
+    assert meta == {"id": "x", "tags": []}
diff --git a/tests/test_validate_references.py b/tests/test_validate_references.py
new file mode 100644
index 0000000..b70423e
--- /dev/null
+++ b/tests/test_validate_references.py
@@ -0,0 +1,402 @@
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+from project_standards.validate_references import (
+    build_index,
+    check_adr_sequence,
+    check_dates,
+    check_id_uniqueness,
+    check_reciprocity,
+    check_references,
+)
+
+
+def _write(p: Path, **fm: str) -> None:
+    body = "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# B\n"
+    p.write_text(body)
+
+
+def test_duplicate_id_is_error(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    _write(
+        tmp_path / "b.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    index = build_index([tmp_path / "a.md", tmp_path / "b.md"])
+    errors = check_id_uniqueness(index)
+    assert len(errors) == 1
+    assert "note-aaaaaa-x" in errors[0]
+
+
+def test_build_index_skips_unreadable_unparseable_and_non_dict(tmp_path: Path) -> None:
+    # build_index must tolerate (skip) three classes of bad input rather than raising:
+    #   - FrontmatterParseError (duplicate top-level key, rejected since Phase 0 Task 0.5)
+    #   - a non-existent path (read_text -> FileNotFoundError, an OSError)
+    #   - frontmatter that parses to a non-mapping (a YAML list, not a dict)
+    # This pins the two except branches and the `not isinstance(meta, dict)` guard.
+    dup = tmp_path / "dup.md"
+    dup.write_text("---\ntags: []\ntags: ['x']\n---\n# B\n")
+    list_fm = tmp_path / "list.md"
+    list_fm.write_text("---\n- a\n- b\n---\n# B\n")
+    missing = tmp_path / "missing.md"  # never created -> OSError on read
+    index = build_index([dup, list_fm, missing])
+    assert index.docs == []
+    assert index.ids == set()
+
+
+def test_unique_ids_no_error(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    _write(
+        tmp_path / "b.md",
+        id="'note-bbbbbb-y'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    index = build_index([tmp_path / "a.md", tmp_path / "b.md"])
+    assert check_id_uniqueness(index) == []
+
+
+def test_created_after_updated_is_error(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-02-01'",
+        updated="'2026-01-01'",
+    )
+    errors = check_dates(build_index([tmp_path / "a.md"]))
+    assert any("created" in e and "updated" in e for e in errors)
+
+
+def test_reviewed_before_created_is_error(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-02-01'",
+        updated="'2026-02-02'",
+        reviewed="'2026-01-01'",
+    )
+    errors = check_dates(build_index([tmp_path / "a.md"]))
+    assert any("reviewed" in e for e in errors)
+
+
+def test_valid_dates_no_error(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-02-01'",
+        reviewed="'2026-02-02'",
+    )
+    assert check_dates(build_index([tmp_path / "a.md"])) == []
+
+
+def test_dangling_reference_is_warning(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        related="['note-zzzzzz-missing']",
+    )
+    warnings = check_references(build_index([tmp_path / "a.md"]), tmp_path)
+    assert len(warnings) == 1
+    assert "[warning]" in warnings[0]
+
+
+def test_reference_to_existing_path_resolves(tmp_path: Path) -> None:
+    (tmp_path / "docs").mkdir()
+    (tmp_path / "docs" / "arch.md").write_text("# A\n")
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        related="['docs/arch.md']",
+    )
+    assert check_references(build_index([tmp_path / "a.md"]), tmp_path) == []
+
+
+def test_reference_to_known_id_resolves(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        related="['note-bbbbbb-y']",
+    )
+    _write(
+        tmp_path / "b.md",
+        id="'note-bbbbbb-y'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    assert check_references(build_index([tmp_path / "a.md", tmp_path / "b.md"]), tmp_path) == []
+
+
+def test_null_superseded_by_not_flagged(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        superseded_by="null",
+    )
+    assert check_references(build_index([tmp_path / "a.md"]), tmp_path) == []
+
+
+def test_anchor_and_absolute_paths_do_not_resolve(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        related="['docs/arch.md#section', '/abs/x.md']",
+    )
+    warnings = check_references(build_index([tmp_path / "a.md"]), tmp_path)
+    assert len(warnings) == 2
+
+
+def test_missing_supersede_reciprocity_warns(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        superseded_by="'note-bbbbbb-y'",
+    )
+    _write(
+        tmp_path / "b.md",
+        id="'note-bbbbbb-y'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )  # no supersedes back
+    warnings = check_reciprocity(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
+    assert any("reciprocal" in w or "supersedes" in w for w in warnings)
+
+
+def test_reverse_supersede_reciprocity_warns(tmp_path: Path) -> None:
+    # B.supersedes A but A lacks superseded_by -> the OTHER direction (CR-004).
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )  # no superseded_by back
+    _write(
+        tmp_path / "b.md",
+        id="'note-bbbbbb-y'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+        supersedes="['note-aaaaaa-x']",
+    )
+    warnings = check_reciprocity(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
+    assert any("superseded_by" in w for w in warnings)
+
+
+def test_duplicate_adr_number_is_error(tmp_path: Path) -> None:
+    _write(
+        tmp_path / "a.md",
+        id="'adr-0001-repo-one'",
+        doc_type="'adr'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    _write(
+        tmp_path / "b.md",
+        id="'adr-0001-repo-two'",
+        doc_type="'adr'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    errors = check_adr_sequence(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
+    assert any("0001" in e for e in errors)
+
+
+def _run_refs(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
+    return subprocess.run(
+        [sys.executable, "-m", "project_standards.validate_references", *args],
+        capture_output=True,
+        text=True,
+        cwd=cwd,
+    )
+
+
+def test_references_index_is_repo_wide_under_scoped_invocation(tmp_path: Path) -> None:
+    # validate-references is a REPO-WIDE invariant pass: invoking it scoped to one file
+    # (as `project-standards validate FILE` forwards) must STILL catch a duplicate id in
+    # another managed doc (codex P2 — a scoped index silently misses it).
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    _write(
+        tmp_path / "b.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    r = _run_refs(["a.md", "--config", str(cfg)], tmp_path)  # scoped to a.md only
+    assert r.returncode == 1  # repo-wide index still sees b.md's duplicate id
+    assert "note-aaaaaa-x" in r.stderr
+
+
+def test_disabled_by_default_exits_0(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-02-01'",
+        updated="'2026-01-01'",
+    )  # bad dates, but disabled
+    r = _run_refs(["--config", str(cfg)], tmp_path)
+    assert r.returncode == 0
+
+
+def test_forwarded_schema_flag_skips_not_errors(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    r = _run_refs(["--schema", "custom.json", "--quiet", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 0
+
+
+def test_no_require_frontmatter_is_accepted(tmp_path: Path) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    r = _run_refs(["--no-require-frontmatter", "--quiet", "--config", str(cfg)], tmp_path)
+    assert r.returncode == 0
+
+
+# In-process main() tests for coverage of the CLI paths not reached by subprocess.
+
+
+def test_main_disabled_returns_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
+    monkeypatch.chdir(tmp_path)
+    from project_standards.validate_references import main
+
+    assert main(["--config", str(cfg)]) == 0
+
+
+def test_main_enabled_duplicate_id_returns_1(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    _write(
+        tmp_path / "b.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    monkeypatch.chdir(tmp_path)
+    from project_standards.validate_references import main
+
+    rc = main(["--config", str(cfg)])
+    assert rc == 1
+    captured = capsys.readouterr()
+    assert "note-aaaaaa-x" in captured.err
+
+
+def test_main_custom_schema_skips(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    monkeypatch.chdir(tmp_path)
+    from project_standards.validate_references import main
+
+    rc = main(["--schema", "custom.json", "--config", str(cfg)])
+    assert rc == 0
+    captured = capsys.readouterr()
+    assert "custom schema" in captured.out
+
+
+def test_main_config_error_returns_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(": invalid: yaml: [\n")
+    monkeypatch.chdir(tmp_path)
+    from project_standards.validate_references import main
+
+    assert main(["--config", str(cfg)]) == 2
+
+
+def test_main_success_prints_summary(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    cfg = tmp_path / ".project-standards.yml"
+    cfg.write_text(
+        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
+    )
+    _write(
+        tmp_path / "a.md",
+        id="'note-aaaaaa-x'",
+        doc_type="'note'",
+        created="'2026-01-01'",
+        updated="'2026-01-02'",
+    )
+    monkeypatch.chdir(tmp_path)
+    from project_standards.validate_references import main
+
+    rc = main(["--config", str(cfg)])
+    assert rc == 0
+    captured = capsys.readouterr()
+    assert "references valid" in captured.out

exec
/bin/bash -lc "sed -n '1,260p' src/project_standards/cli.py && printf '\\n--- format_frontmatter 1 ---\\n' && sed -n '1,260p' src/project_standards/format_frontmatter.py && printf '\\n--- format_frontmatter 2 ---\\n' && sed -n '261,620p' src/project_standards/format_frontmatter.py && printf '\\n--- format_frontmatter 3 ---\\n' && sed -n '621,980p' src/project_standards/format_frontmatter.py" in /home/chris/projects/project-standards
 succeeded in 0ms:
"""Unified `project-standards` CLI: adopt | list | validate.

`validate` runs `validate-frontmatter` (schema), `validate-id` (id format), and
`validate-references` (cross-file, opt-in) so consumers get the full contract check
from a single command.  The standalone
`validate-frontmatter` console script is kept as a back-compat alias.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from project_standards import (
    format_frontmatter,
    validate_frontmatter,
    validate_id,
    validate_references,
)
from project_standards.adopt.engine import build_plan, execute_plan, format_report
from project_standards.adopt.errors import AdoptError
from project_standards.adopt.manifest import (
    Artifact,
    Manifest,
    available_standards,
    load_manifest,
)
from project_standards.registry import Registry, RegistryError, load_registry


def _contract_version(registry: Registry, standard_id: str) -> str | None:
    """The bundled default contract version for a standard (None if not version-tracked)."""
    return {
        "markdown-frontmatter": registry.frontmatter_default,
        "adr": registry.adr_default,
        "python-tooling": registry.python_tooling_default,
        "markdown-tooling": registry.markdown_tooling_default,
    }.get(standard_id)


# The registry's version-tracked standards (hyphenated ids), the single source for drift checks.
_REGISTRY_STANDARD_IDS = (
    "markdown-frontmatter",
    "adr",
    "python-tooling",
    "markdown-tooling",
)


def _extract_config_path(args: list[str]) -> Path:
    """Pull the --config value out of a forwarded argv (default .project-standards.yml)."""
    for i, a in enumerate(args):
        if a == "--config" and i + 1 < len(args):
            return Path(args[i + 1])
        if a.startswith("--config="):
            return Path(a.split("=", 1)[1])
    return Path(".project-standards.yml")


def _has_schema_flag(args: list[str]) -> bool:
    """True if a forwarded argv passes --schema (custom-schema mode) — CR-001."""
    return any(a == "--schema" or a.startswith("--schema=") for a in args)


def _assert_registry_bundle_parity(registry: Registry) -> None:
    """Bundles and the registry's version-tracked standards must agree in BOTH directions.

    Catches a bundle with no registry contract (would emit `contract_version: null`) AND a
    registry-known standard with no bundle (silently un-adoptable). Either way -> clean exit 2.
    """
    bundles = set(available_standards())
    registry_ids = {s for s in _REGISTRY_STANDARD_IDS if _contract_version(registry, s) is not None}
    if bundles != registry_ids:
        raise RegistryError(
            f"registry/bundle drift — registry-only: {sorted(registry_ids - bundles)}, "
            f"bundle-only: {sorted(bundles - registry_ids)}"
        )


def _artifact_entry(a: Artifact) -> dict[str, object]:
    entry: dict[str, object] = {"kind": a.kind, "owner": a.owner}
    if a.kind == "fragment":
        entry["target"] = a.target
    else:
        entry["dest"] = a.dest
    if a.source is not None:
        entry["source"] = a.source
    else:
        entry["shared"] = a.shared
    return entry


def _cmd_list(as_json: bool) -> int:
    """List adoptable standards; fail cleanly on registry/bundle drift before emitting output."""
    registry = load_registry()
    _assert_registry_bundle_parity(registry)  # fail cleanly on drift before emitting anything
    entries: list[tuple[str, str | None, Manifest]] = [
        (sid, _contract_version(registry, sid), load_manifest(sid)) for sid in available_standards()
    ]
    if as_json:
        payload = [
            {
                "id": sid,
                "contract_version": contract,
                "artifacts": [_artifact_entry(a) for a in manifest.artifacts],
            }
            for sid, contract, manifest in entries
        ]
        print(json.dumps(payload, indent=2))
        return 0
    for sid, contract, manifest in entries:
        print(f"{sid} (contract {contract})")
        for a in manifest.artifacts:
            where = a.target if a.kind == "fragment" else a.dest
            print(f"  {a.kind:<16} {where}")
    return 0


def _cmd_adopt(standards: list[str], dest: Path, force: bool, dry_run: bool) -> int:
    """Materialize *standards* into *dest*; apply registry/bundle parity guard before planning."""
    if not dest.is_dir():
        print(f"error: --dest is not a directory: {dest}", file=sys.stderr)
        return 2
    _assert_registry_bundle_parity(load_registry())  # same drift guard as `list`
    plan = build_plan(standards)
    report = execute_plan(plan, dest, force=force, dry_run=dry_run)
    out = format_report(report)
    if out:
        print(out)
    if dry_run:
        print("\n(dry run — no files written)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for project-standards.

    `validate` is early-dispatched before argparse runs — argparse's REMAINDER cannot
    capture flags like `--config` that look like top-level options. All other subcommands
    go through the normal argparse path inside the error boundary below.
    """
    args_list = list(sys.argv[1:] if argv is None else argv)

    # EARLY DISPATCH for `validate`: delegate every trailing arg to all three validators BEFORE the
    # adopt/list parser runs. `parse_args()` + `REMAINDER` does NOT work here — argparse rejects
    # `validate --config x` as an unrecognized top-level option before REMAINDER can capture it.
    # All three validators accept the same --config / --quiet / FILE flags, so we pass args through
    # unchanged. We return the worst exit code (2 > 1 > 0) so a schema error, id violation, or
    # reference error is never masked by another tool's success.
    if args_list and args_list[0] == "validate":
        validator_args = args_list[1:]
        # Intercept --help before forwarding — otherwise validate_frontmatter.main(["--help"])
        # calls sys.exit(0), which hides that validate-id also runs.
        if "--help" in validator_args or "-h" in validator_args:
            _p = argparse.ArgumentParser(
                prog="project-standards validate",
                description=(
                    "Run validate-frontmatter (schema), validate-id (id format), and\n"
                    "validate-references (cross-file, opt-in). All run; the worst exit\n"
                    "code is returned.\n\n"
                    "All flags are forwarded to every validator. --schema and\n"
                    "--no-require-frontmatter are frontmatter-only; --schema also causes\n"
                    "validate-id to skip (custom schemas may use different id conventions).\n\n"
                    "For the full flag set of each validator:\n"
                    "  validate-frontmatter --help\n"
                    "  validate-id --help\n"
                    "  validate-references --help"
                ),
                formatter_class=argparse.RawDescriptionHelpFormatter,
            )
            _p.add_argument("files", nargs="*", metavar="FILE", help="Markdown files to validate.")
            _p.add_argument(
                "--config",
                metavar="PATH",
                help="Project config file (default: .project-standards.yml).",
            )
            _p.add_argument(
                "--schema",
                metavar="PATH",
                help="Custom schema; also skips id-format validation.",
            )
            _p.add_argument(
                "--glob",
                metavar="PATTERN",
                help="Additional glob pattern relative to cwd.",
            )
            _p.add_argument(
                "--no-require-frontmatter",
                action="store_true",
                help="Do not fail files that have no frontmatter block.",
            )
            _p.add_argument("--quiet", "-q", action="store_true", help="Suppress per-file output.")
            _p.print_help()
            return 0
        rc_frontmatter = validate_frontmatter.main(validator_args)
        rc_id = validate_id.main(validator_args)
        rc_refs = validate_references.main(validator_args)
        return max(rc_frontmatter, rc_id, rc_refs)

    if args_list and args_list[0] == "fix":
        fix_args = args_list[1:]
        if "--help" in fix_args or "-h" in fix_args:
            print(
                "usage: project-standards fix [FILE ...] [--config PATH] [--glob PATTERN] [--quiet]\n"
                "Format frontmatter (--write), fix ids, then re-validate (incl. references).\n"
                "Skips entirely under a custom schema."
            )
            return 0
        # Custom-schema preflight (CR-001): fix is bundled-only, like format/validate-id.
        try:
            fix_cfg = validate_frontmatter.load_config(_extract_config_path(fix_args))
        except validate_frontmatter.ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if _has_schema_flag(fix_args) or validate_frontmatter.schema_value_is_path(fix_cfg.schema):
            print("note: custom schema in use; skipping fix", file=sys.stderr)
            return 0
        rc_format = format_frontmatter.main(["--write", *fix_args])
        rc_idfix = validate_id.main(["--fix", *fix_args])
        # Final postcondition = the SAME contract as `project-standards validate`,
        # references included, so a "successful" fix cannot hide a reference error (CR-001).
        rc_check = max(
            validate_frontmatter.main(fix_args),
            validate_id.main(fix_args),
            validate_references.main(fix_args),
        )
        return max(rc_format, rc_idfix, rc_check)

    parser = argparse.ArgumentParser(prog="project-standards")
    sub = parser.add_subparsers(dest="command", required=True)
    # Registered only so top-level `--help` advertises it; real handling is the early dispatch above.
    sub.add_parser(
        "validate",
        help="validate schema + id + references (validate-frontmatter, validate-id, validate-references)",
    )
    sub.add_parser("fix", help="format frontmatter + fix ids, then re-validate")

    p_adopt = sub.add_parser("adopt", help="materialize a standard's artifacts")
    p_adopt.add_argument("standards", nargs="+", metavar="STANDARD")
    p_adopt.add_argument("--dest", type=Path, default=Path.cwd())
    p_adopt.add_argument("--force", action="store_true")
    p_adopt.add_argument("--dry-run", action="store_true")

    p_list = sub.add_parser("list", help="list adoptable standards and their artifacts")
    p_list.add_argument("--json", action="store_true")

    args = parser.parse_args(args_list)

    # `list` and `adopt` both touch bundle/registry data, so both sit inside the error
    # boundary — broken or drifted metadata must produce a clean exit code, never a traceback.
    try:
        if args.command == "list":
            return _cmd_list(args.json)
        return _cmd_adopt(args.standards, args.dest, args.force, args.dry_run)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except AdoptError as exc:

--- format_frontmatter 1 ---
"""Autoformatter for managed Markdown frontmatter (the write-side companion to
validate-frontmatter). Tokenizes the leading YAML block into per-key entries,
applies deterministic transforms, and re-emits the block preserving comments and
per-line endings (same technique as validate_id --fix). Never changes the `id`
value (it may re-quote it like any scalar, but the value is validate_id's domain)
and never edits the document body."""

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from project_standards.id_format import random_token, slugify

# Leading frontmatter block; groups: open fence, body (between fences), close fence.
_FM_RE = re.compile(r"\A(---[ \t]*\r?\n)(.*?)(\r?\n---[ \t]*(?:\r?\n|$))", re.DOTALL)
# A top-level (column 0) mapping key line: `key:` optionally followed by a value.
_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "markdown-frontmatter.schema.json"
VALID_DOC_TYPES: frozenset[str] = frozenset(
    json.loads(_SCHEMA_PATH.read_text())["properties"]["doc_type"]["enum"]
)

CANONICAL_ORDER: tuple[str, ...] = (
    "schema_version",
    "id",
    "title",
    "description",
    "doc_type",
    "status",
    "created",
    "updated",
    "reviewed",
    "owner",
    "consumer",
    "tags",
    "aliases",
    "related",
    "supersedes",
    "superseded_by",
    "depends_on",
    "applies_to",
    "source",
    "confidence",
    "visibility",
    "license",
    "publish",
    "project",
    "x_project",
)


@dataclass
class Entry:
    """One top-level frontmatter key and the exact source lines it owns.

    `lines` holds every physical source line for this entry WITH its original
    line ending: any leading comment/blank run, the `key:` line (incl. an inline
    `# comment`), and indented continuation lines (block list or nested mapping).
    `key` is None only for a trailing comment/blank run after the last key."""

    key: str | None
    lines: list[str] = field(default_factory=list)


def _split_keepends(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def tokenize(body: str) -> tuple[list[Entry], str | None]:
    """Split the between-fences `body` into Entry objects.

    Returns (entries, None) on success, or ([], reason) if the block contains a
    construct unsafe to reorder/reserialize (anchors, merge keys, a non-key line
    at column 0). Nested mappings and block lists are supported (carried opaquely
    as continuation lines)."""
    lines = _split_keepends(body)
    entries: list[Entry] = []
    pending: list[str] = []  # leading comment/blank lines for the next key
    seen: set[str] = set()  # duplicate top-level keys are unsafe to reorder (CR-002)
    i = 0
    while i < len(lines):
        line = lines[i]
        content = line.rstrip("\r\n")
        stripped = content.lstrip(" \t")
        if stripped == "" or stripped.startswith("#"):
            pending.append(line)
            i += 1
            continue
        m = _TOP_KEY_RE.match(content)
        if not m:
            return [], f"unrecognized top-level line: {content!r}"
        key = m.group(1)
        value = m.group(2).lstrip()
        if value[:1] in ("&", "*") or value.startswith("<<") or value[:1] in ("|", ">"):
            return [], f"unsupported YAML construct on key {key!r}"
        if key in seen:
            return [], f"duplicate top-level key {key!r} (refusing to rewrite)"
        seen.add(key)
        entry = Entry(key=key, lines=[*pending, line])
        pending = []
        i += 1
        # Gather indented continuation lines (block list items / nested mapping).
        while i < len(lines):
            nxt = lines[i]
            ncontent = nxt.rstrip("\r\n")
            if ncontent.lstrip(" \t") == "":
                break  # blank line ends the entry; becomes leading run of next
            if nxt[:1] in (" ", "\t"):
                entry.lines.append(nxt)
                i += 1
                continue
            break
        entries.append(entry)
    if pending:
        entries.append(Entry(key=None, lines=pending))
    return entries, None


def _emit_single_quoted(value: str) -> str:
    """YAML single-quoted scalar: wrap in quotes, double internal single-quotes."""
    return "'" + value.replace("'", "''") + "'"


_NULL_TOKENS = frozenset({"null", "Null", "NULL", "~"})


def _split_value_comment(rest: str) -> tuple[str, str]:
    """Split the text after `key:` into (raw_value, comment). A YAML inline comment
    begins only at whitespace + '#' (CR-NEW-003); a bare '#' (e.g. `C# guide`,
    `http://x/#frag`), a '#' inside a quoted scalar, or a '#' inside a quoted flow-list
    item (e.g. `['Issue #123']` — CR-NEW-005) is literal. `comment` keeps its leading
    whitespace (e.g. '  # note') so it round-trips, or is ''."""
    stripped = rest.lstrip(" \t")
    lead = rest[: len(rest) - len(stripped)]
    if stripped[:1] in ("'", '"'):
        quote = stripped[0]
        i = 1
        while i < len(stripped):
            ch = stripped[i]
            if quote == "'" and ch == "'":
                if stripped[i : i + 2] == "''":  # escaped single quote
                    i += 2
                    continue
                return lead + stripped[: i + 1], stripped[i + 1 :]
            if quote == '"' and ch == "\\":
                i += 2
                continue
            if quote == '"' and ch == '"':
                return lead + stripped[: i + 1], stripped[i + 1 :]
            i += 1
        return rest, ""  # unterminated quote -> treat whole as value (left as-is upstream)
    if stripped[:1] == "[":  # flow list: scan to the matching ], honoring quotes
        depth = 0
        in_quote = ""
        i = 0
        while i < len(stripped):
            ch = stripped[i]
            if in_quote:
                if in_quote == "'" and ch == "'":
                    if stripped[i : i + 2] == "''":
                        i += 2
                        continue
                    in_quote = ""
                elif in_quote == '"' and ch == "\\":
                    i += 2
                    continue
                elif in_quote == '"' and ch == '"':
                    in_quote = ""
            elif ch in ("'", '"'):
                in_quote = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    tail = stripped[i + 1 :]
                    return lead + stripped[: i + 1], (tail if re.match(r"\s+#", tail) else "")
            i += 1
        return rest, ""  # unbalanced brackets -> no comment
    m = re.search(r"(\s+#.*)$", rest)  # plain scalar: comment = whitespace then '#' to end
    if m:
        return rest[: m.start()], rest[m.start() :]
    return rest, ""


def _requote_scalar_line(line: str, key: str) -> str:
    """Re-quote the scalar value on a `key: value` line WITHOUT resolving its YAML type
    (CR-NEW-001): the author's literal text is single-quoted, so `on`/`off`/`1.1`/a date
    keep their exact characters. Indentation, an inline `# comment` (split at a real
    whitespace-`#` boundary — CR-NEW-003), and the line ending are preserved; explicit
    `null`/`~`, empty values, and flow lists are left untouched."""
    m = re.match(
        r"^(?P<indent>[ \t]*)(?P<key>" + re.escape(key) + r":)(?P<sep>[ \t]*)"
        r"(?P<rest>[^\r\n]*)(?P<eol>\r?\n?)$",
        line,
    )
    if m is None:
        return line
    value_raw, comment = _split_value_comment(m.group("rest"))
    raw = value_raw.strip()
    if raw == "" or raw.startswith("["):
        return line  # empty or flow list -> handled by normalize_lists
    if raw in _NULL_TOKENS:
        return line  # explicit null stays null
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return line  # already single-quoted -> idempotent
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        try:
            decoded = yaml.safe_load(raw)  # explicit quotes -> intended string, no type guess
        except yaml.YAMLError:
            return line  # malformed double-quoted scalar -> leave for the validator, never crash
        text_value = decoded if isinstance(decoded, str) else raw
    else:
        text_value = raw  # unquoted plain scalar: quote the RAW text, never resolve it
    sep = m.group("sep") or " "
    return (
        m.group("indent")
        + m.group("key")
        + sep
        + _emit_single_quoted(text_value)
        + comment
        + m.group("eol")
    )


def _line_ending(line: str) -> str:
    """Return the line ending of `line`, or '' if the line has no trailing newline.

    The regex design absorbs the final newline of the frontmatter body into the
    close-fence group, so the very last physical line of `body` arrives without a
    trailing newline.  Returning '' here lets callers preserve that absent newline
    on the key line; item lines in a block list always use '\n'."""
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


# The array-typed fields in the schema; only these are list-normalized.
_LIST_FIELDS = ("tags", "aliases", "related", "supersedes", "depends_on", "applies_to", "source")


def _leading_run(entry: Entry) -> int:
    """Count of leading comment/blank lines before the entry's `key:` line."""
    n = 0
    for ln in entry.lines:

--- format_frontmatter 2 ---
        stripped = ln.rstrip("\r\n").lstrip(" \t")
        if stripped == "" or stripped.startswith("#"):
            n += 1
        else:
            break
    return n


def _block_list_has_item_comment(item_lines: list[str]) -> bool:
    """True if any block-list item line carries a real inline comment (e.g. `- 'a'  # why`).
    Re-rendering the list from parsed values would silently drop such a comment (codex P2),
    so the formatter leaves a comment-bearing list untouched rather than destroy the note."""
    for ln in item_lines:
        stripped = ln.lstrip(" \t").rstrip("\r\n")
        if not stripped.startswith("-"):
            continue
        after_dash = stripped[1:].lstrip(" \t")
        if _split_value_comment(after_dash)[1].lstrip(" \t").startswith("#"):
            return True
    return False


def normalize_lists(entries: list[Entry]) -> None:
    """In place: render each list-typed field as canonical block style (single-quoted
    items, duplicates removed first-wins); an empty/absent value becomes `key: []`.
    Values are read with yaml.BaseLoader so list items are NEVER type-coerced — e.g.
    `[on, off]` stays the strings 'on'/'off', not booleans (CR-NEW-001)."""
    for entry in entries:
        if entry.key not in _LIST_FIELDS:
            continue
        lead = _leading_run(entry)
        try:
            loaded = yaml.load("".join(entry.lines[lead:]), Loader=yaml.BaseLoader)  # pyright: ignore[reportUnknownMemberType]
        except yaml.YAMLError:
            continue
        if not isinstance(loaded, dict) or entry.key not in loaded:
            continue
        value: Any = cast(Any, loaded)[entry.key]  # BaseLoader dict values are untyped
        if not (value is None or value == "" or isinstance(value, list)):
            continue  # a scalar where a list belongs -> leave for the validator
        if _block_list_has_item_comment(entry.lines[lead + 1 :]):
            continue  # preserve authored per-item comments; do not re-render (codex P2)
        key_line = entry.lines[lead]
        eol = _line_ending(entry.lines[-1])
        # Indent by slice (NOT re.match(...).group(0), which basedpyright-strict flags — CR-NEW-002).
        indent = key_line[: len(key_line) - len(key_line.lstrip(" \t"))]
        after_colon = key_line.rstrip("\r\n").split(":", 1)[1] if ":" in key_line else ""
        inline = _split_value_comment(after_colon)[
            1
        ]  # comment after [], [a], or bare key (CR-NEW-004)
        leading = entry.lines[:lead]
        raw_items: list[Any] = cast(list[Any], value) if isinstance(value, list) else []
        items: list[str] = [str(x) for x in raw_items]
        seen: list[str] = []
        for item in items:
            if item not in seen:
                seen.append(item)
        # item_eol: block-list items always need a real newline; fall back to '\n'
        # when the key line has no trailing newline (last entry in body — the regex
        # design absorbs that newline into close_fence).
        item_eol = eol or "\n"
        if not seen:
            entry.lines = [*leading, f"{indent}{entry.key}: []{inline}{eol}"]
        else:
            rendered = [f"{indent}{entry.key}:{inline}{item_eol}"]
            rendered += [f"{indent}  - {_emit_single_quoted(s)}{item_eol}" for s in seen]
            entry.lines = [*leading, *rendered]


def requote(entries: list[Entry]) -> None:
    """In place: single-quote the scalar value on each scalar entry — including one
    preceded by leading comment/blank lines, which bundle into the same entry (a bare
    `len(entry.lines) != 1` guard would wrongly skip such a commented key — codex P2).
    Multi-line VALUES (block lists, nested mappings) are left for their own transforms."""
    for entry in entries:
        if entry.key is None:
            continue
        lead = _leading_run(entry)
        if len(entry.lines) != lead + 1:
            continue  # the value spans multiple lines (block list / nested mapping)
        entry.lines[lead] = _requote_scalar_line(entry.lines[lead], entry.key)


_ORDER_INDEX = {key: i for i, key in enumerate(CANONICAL_ORDER)}


def reorder(entries: list[Entry], warnings: list[str]) -> list[Entry]:
    """Stable sort entries into CANONICAL_ORDER. Unknown keys keep their relative
    order after all known keys; a trailing comment-only entry (key=None) stays last.
    Unknown keys also emit a warn-only message (never deleted)."""

    def sort_key(item: tuple[int, Entry]) -> tuple[int, int]:
        idx, entry = item
        if entry.key is None:
            return (len(CANONICAL_ORDER) + 1, idx)  # trailing comments last
        if entry.key in _ORDER_INDEX:
            return (_ORDER_INDEX[entry.key], 0)
        warnings.append(f"unknown frontmatter key '{entry.key}' (kept; not in schema)")
        return (len(CANONICAL_ORDER), idx)

    return [e for _, e in sorted(enumerate(entries), key=sort_key)]


def serialize(entries: list[Entry]) -> str:
    """Concatenate entries' source lines verbatim.

    The regex design absorbs the final `\\n` of the body into `close_fence`, so
    the very last physical line of `body` arrives without a trailing newline.  When
    reordering moves that entry to a non-tail position, we must ensure it still
    ends with a newline so the following entry starts on a new line.  If the entry
    stays last, we leave it unchanged to preserve byte-identity on round-trips."""
    parts: list[str] = []
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        for j, line in enumerate(entry.lines):
            is_last_line = j == len(entry.lines) - 1
            if is_last_line and not is_last and line and not line.endswith(("\n", "\r\n")):
                parts.append(line + "\n")
            else:
                parts.append(line)
    return "".join(parts)


BUNDLED_SCHEMA_VERSION = "1.1"  # matches registry frontmatter_default; see Task A9 note
REQUIRED_ARRAYS = ("tags", "aliases", "related")


def _keys(entries: list[Entry]) -> set[str]:
    return {e.key for e in entries if e.key is not None}


def rename_type(entries: list[Entry], warnings: list[str]) -> None:
    present = _keys(entries)
    if "doc_type" in present:
        if "type" in present:
            warnings.append("both 'type' and 'doc_type' present; kept 'doc_type', left 'type'")
        return
    for entry in entries:
        if entry.key == "type":
            entry.key = "doc_type"
            entry.lines = [re.sub(r"\btype:", "doc_type:", ln, count=1) for ln in entry.lines]
            return


def _new_scalar_entry(key: str, value: str, eol: str) -> Entry:
    return Entry(key=key, lines=[f"{key}: {_emit_single_quoted(value)}{eol}"])


def _new_empty_list_entry(key: str, eol: str) -> Entry:
    return Entry(key=key, lines=[f"{key}: []{eol}"])


def inject_defaults(entries: list[Entry]) -> None:
    """Add schema_version and any missing required arrays. Reorder (A2) places them."""
    eol = _line_ending(entries[0].lines[-1]) if entries and entries[0].lines else "\n"
    present = _keys(entries)
    if "schema_version" not in present:
        entries.append(_new_scalar_entry("schema_version", BUNDLED_SCHEMA_VERSION, eol))
    for key in REQUIRED_ARRAYS:
        if key not in present:
            entries.append(_new_empty_list_entry(key, eol))


_NEVER_NAMES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
_NEVER_DIRS = {".claude", ".agents", ".codex"}


def is_denylisted(path: Path) -> bool:
    """Files that must NEVER carry frontmatter (harness config). Overrides include
    and scaffold, independent of config — defense-in-depth over consumer exclude."""
    if path.name in _NEVER_NAMES:
        return True
    return any(part in _NEVER_DIRS for part in path.parts)


def _infer_doc_type(path: Path) -> str | None:
    """The standard's path rules. None = no rule applies."""
    posix = path.as_posix()
    if "docs/research/" in posix or posix.startswith("docs/research/"):
        return "research"
    if path.name in ("README.md", "index.md"):
        return "index"
    return None


def infer_doc_type(entries: list[Entry], path: Path | None) -> None:
    """Fill/correct-only (SA-001): set doc_type from the path rule ONLY when the
    current value is missing or not a valid enum value. A valid value is kept."""
    if path is None:
        return
    inferred = _infer_doc_type(path)
    if inferred is None:
        return
    eol = _line_ending(entries[0].lines[-1]) if entries and entries[0].lines else "\n"
    for entry in entries:
        if entry.key == "doc_type":
            current = entry.lines[-1].split(":", 1)[1].strip().strip("'\"")
            if current in VALID_DOC_TYPES:
                return  # valid -> never override
            entry.lines = [f"doc_type: {_emit_single_quoted(inferred)}{eol}"]
            return
    entries.append(_new_scalar_entry("doc_type", inferred, eol))


_H1_RE = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)


def _today_iso() -> str:
    return datetime.date.today().isoformat()


def _build_scaffold(body_text: str, path: Path, today: str) -> str:
    h1 = _H1_RE.search(body_text)
    title = h1.group(1) if h1 else path.stem.replace("-", " ").replace("_", " ").title()
    doc_type = _infer_doc_type(path) or "note"
    slug = slugify(title) or slugify(path.stem) or "untitled"
    new_id = f"{doc_type}-{random_token()}-{slug}"
    return (
        "---\n"
        f"schema_version: {_emit_single_quoted(BUNDLED_SCHEMA_VERSION)}\n"
        f"id: {_emit_single_quoted(new_id)}\n"
        f"title: {_emit_single_quoted(title)}\n"
        "description: 'TODO: one-sentence description.'\n"
        f"doc_type: {_emit_single_quoted(doc_type)}\n"
        "status: 'draft'\n"
        f"created: {_emit_single_quoted(today)}\n"
        f"updated: {_emit_single_quoted(today)}\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )


def format_text(
    text: str,
    *,
    path: Path | None,
    scaffold: bool = False,
    today: str | None = None,
    bump_updated: bool = False,
) -> tuple[str, bool, list[str]]:
    """Format the frontmatter block of `text`. Returns (new_text, changed, warnings).

    `path` informs path-based transforms; None disables them (stdin mode). The
    `scaffold` flag inserts a schema-valid block into files with no frontmatter.
    `bump_updated` rewrites the `updated` field when the block changes."""
    warnings: list[str] = []
    if path is not None and is_denylisted(path):
        return text, False, ["refused (denylisted): never add frontmatter to this file"]
    match = _FM_RE.match(text)
    if match is None:
        if scaffold and path is not None and not is_denylisted(path):
            stamp = today or _today_iso()
            return (
                _build_scaffold(text, path, stamp) + text,
                True,
                [f"scaffolded: {path} — fill in title/description"],
            )
        return text, False, warnings
    open_fence, body, close_fence = match.group(1), match.group(2), match.group(3)
    rest = text[match.end() :]
    entries, reason = tokenize(body)
    if reason is not None:
        warnings.append(f"skipped (unsupported frontmatter): {reason}")
        return text, False, warnings
    rename_type(entries, warnings)
    infer_doc_type(entries, path)
    inject_defaults(entries)
    normalize_lists(entries)
    requote(entries)
    entries = reorder(entries, warnings)
    new_body = serialize(entries)
    new_text = open_fence + new_body + close_fence + rest
    changed = new_text != text
    if bump_updated and changed:
        stamp = today or _today_iso()
        for entry in entries:
            if entry.key == "updated" and len(entry.lines) == 1:
                eol = _line_ending(entry.lines[0])
                entry.lines = [f"updated: {_emit_single_quoted(stamp)}{eol}"]
        new_body = serialize(entries)
        new_text = open_fence + new_body + close_fence + rest
        changed = new_text != text
    return new_text, changed, warnings


from project_standards.validate_frontmatter import (  # noqa: E402
    ConfigError,
    collect_paths,
    load_config,
    schema_value_is_path,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")


def _atomic_write(path: Path, data: str) -> None:
    """Write atomically AND preserve the original file's permission bits (codex
    missing-consideration): mkstemp creates 0600, so copy the source mode first."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(data)
        with contextlib.suppress(OSError):
            tmp_path.chmod(path.stat().st_mode & 0o777)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="format-frontmatter",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--glob", metavar="PATTERN")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--bump-updated", action="store_true")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args(argv)

    # SA-spec: --stdin reads one document and writes stdout; it is incompatible with a
    # file set or in-place write. Enforce it (parser.error exits 2) — CR-005.
    if args.stdin and (args.files or args.glob or args.write):
        parser.error("--stdin cannot be combined with FILE, --glob, or --write")

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.schema is not None or schema_value_is_path(config.schema):
        if not args.quiet:
            print("note: custom schema in use; skipping frontmatter formatting")
        return 0

    if args.stdin:
        text = sys.stdin.read()
        new, _changed, _warn = format_text(text, path=None, bump_updated=args.bump_updated)
        sys.stdout.write(new)
        return 0

    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
    write = args.write  # default is check-mode
    any_change = False
    unparseable = False
    for path in paths:
        if is_denylisted(path):

--- format_frontmatter 3 ---
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"{path}: cannot read: {exc}", file=sys.stderr)
            unparseable = True
            continue
        new, changed, warnings = format_text(
            text, path=path, scaffold=write, bump_updated=args.bump_updated
        )
        for w in warnings:
            print(f"{path}: {w}", file=sys.stderr)
            # A duplicate-key block is refused (not rewritten) AND must fail the gate (CR-002).
            if "duplicate top-level key" in w:
                unparseable = True
        if changed:
            any_change = True
            if write:
                _atomic_write(path, new)
                if not args.quiet:
                    print(f"formatted: {path}")
            elif not args.quiet:
                print(f"would reformat: {path}")
    if write:
        return 1 if unparseable else 0
    return 1 if (any_change or unparseable) else 0


if __name__ == "__main__":
    sys.exit(main())

exec
/bin/bash -lc "sed -n '260,560p' src/project_standards/cli.py && printf '\\n--- id_format ---\\n' && sed -n '1,220p' src/project_standards/id_format.py && printf '\\n--- validate_frontmatter diff context ---\\n' && git diff --minimal bd5d423fc9c8286f5a9634d5d85d0278de6ea788 -- src/project_standards/validate_frontmatter.py && printf '\\n--- validate_id diff context ---\\n' && git diff --minimal bd5d423fc9c8286f5a9634d5d85d0278de6ea788 -- src/project_standards/validate_id.py" in /home/chris/projects/project-standards
 succeeded in 0ms:
    except AdoptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())

--- id_format ---
"""Shared id-token helpers used by validate_id (id validation/fix) and
format_frontmatter (scaffold). One copy so the two tools cannot drift."""

from __future__ import annotations

import re
import secrets
import string
import unicodedata

# Base-36 alphabet (digits + lowercase letters) for the 6-char id token.
_BASE36_CHARS = string.digits + string.ascii_lowercase


def slugify(text: str) -> str:
    """Lowercase kebab-case slug: strip accents to ASCII, lowercase, collapse
    every run of non-alphanumerics to a single hyphen, trim leading/trailing."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def random_token(length: int = 6) -> str:
    """A cryptographically-random base-36 token (default 6 chars)."""
    return "".join(secrets.choice(_BASE36_CHARS) for _ in range(length))

--- validate_frontmatter diff context ---
diff --git a/src/project_standards/validate_frontmatter.py b/src/project_standards/validate_frontmatter.py
index 3dea528..b3f8e73 100755
--- a/src/project_standards/validate_frontmatter.py
+++ b/src/project_standards/validate_frontmatter.py
@@ -74,7 +74,7 @@ def find_bundled_schema(name: str) -> Path:
     return Path(__file__).parent / "schemas" / f"{name}.schema.json"
 
 
-def _schema_value_is_path(value: str | None) -> bool:
+def schema_value_is_path(value: str | None) -> bool:
     """True when a config `schema` value names a filesystem path, not a bundled name.
 
     A bare token (e.g. "markdown-frontmatter") is a bundled schema name; anything
@@ -89,7 +89,7 @@ def resolve_schema_path(schema_value: str | None) -> Path:
     A bare token is treated as a bundled schema name; anything containing a path
     separator or ending in `.json` is treated as a filesystem path.
     """
-    if _schema_value_is_path(schema_value):
+    if schema_value_is_path(schema_value):
         return Path(cast("str", schema_value))
     return find_bundled_schema(schema_value or _DEFAULT_SCHEMA_NAME)
 
@@ -99,6 +99,28 @@ def resolve_schema_path(schema_value: str | None) -> Path:
 # ---------------------------------------------------------------------------
 
 
+class _UniqueKeyLoader(yaml.SafeLoader):
+    """SafeLoader that rejects duplicate mapping keys (PyYAML otherwise keeps the
+    last silently). Frontmatter with a duplicate key is a bug, not a valid doc."""
+
+
+def _construct_no_duplicates(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[str, Any]:
+    mapping: dict[Any, Any] = {}
+    for key_node, value_node in node.value:
+        key = cast(Any, loader.construct_object(key_node, deep=True))  # pyright: ignore[reportUnknownMemberType]
+        if key in mapping:
+            raise yaml.constructor.ConstructorError(
+                None, None, f"duplicate key {key!r}", key_node.start_mark
+            )
+        mapping[key] = loader.construct_object(value_node, deep=True)  # pyright: ignore[reportUnknownMemberType]
+    return mapping
+
+
+_UniqueKeyLoader.add_constructor(
+    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_no_duplicates
+)
+
+
 def _coerce_dates(obj: Any) -> Any:
     """Recursively convert datetime.date/datetime to ISO strings.
 
@@ -124,7 +146,7 @@ def parse_frontmatter(text: str) -> dict[str, Any] | None:
     if not match:
         return None
     try:
-        loaded = yaml.safe_load(match.group(1))
+        loaded = yaml.load(match.group(1), Loader=_UniqueKeyLoader)
     except yaml.YAMLError as exc:
         raise FrontmatterParseError(str(exc)) from exc
     if not isinstance(loaded, dict):
@@ -292,6 +314,7 @@ class ProjectConfig:
         adr_version: str | None = None,
         python_tooling_version: str | None = None,
         markdown_tooling_version: str | None = None,
+        references_enabled: bool = False,
     ) -> None:
         self.schema = schema
         self.include = include
@@ -302,6 +325,7 @@ class ProjectConfig:
         self.adr_version = adr_version
         self.python_tooling_version = python_tooling_version
         self.markdown_tooling_version = markdown_tooling_version
+        self.references_enabled = references_enabled
 
 
 def resolve_effective_schema(
@@ -320,7 +344,7 @@ def resolve_effective_schema(
     if args_schema is not None:
         return args_schema
     schema_value = config.schema
-    custom_path = _schema_value_is_path(schema_value)
+    custom_path = schema_value_is_path(schema_value)
     if custom_path and config.frontmatter_version is not None:
         raise ConfigError(
             "set markdown.frontmatter.schema (a custom path) or "
@@ -343,7 +367,7 @@ def frontmatter_adr_incompatibility(config: ProjectConfig, registry: Registry) -
     version as an incompatibility). Returns None when compatible or not applicable;
     raises RegistryError if the configured ADR version is unknown.
     """
-    if _schema_value_is_path(config.schema):
+    if schema_value_is_path(config.schema):
         return None
     if not (config.require_adr_sections or config.adr_version is not None):
         return None
@@ -376,6 +400,7 @@ def load_config(path: Path) -> ProjectConfig:
     adr_version: str | None = None
     python_tooling_version: str | None = None
     markdown_tooling_version: str | None = None
+    references_enabled = False
 
     if path.exists():
         try:
@@ -397,6 +422,12 @@ def load_config(path: Path) -> ProjectConfig:
                     required = bool(fm.get("required", True))
                     version_val = fm.get("version")
                     frontmatter_version = str(version_val) if version_val is not None else None
+                    references = fm.get("references")
+                    if isinstance(references, dict):
+                        references_dict = cast("dict[str, Any]", references)
+                        references_enabled = bool(references_dict.get("enabled", False))
+                    else:
+                        references_enabled = False
                 adr = markdown_dict.get("adr")
                 if isinstance(adr, dict):
                     adr_dict = cast("dict[str, Any]", adr)
@@ -426,6 +457,7 @@ def load_config(path: Path) -> ProjectConfig:
         adr_version=adr_version,
         python_tooling_version=python_tooling_version,
         markdown_tooling_version=markdown_tooling_version,
+        references_enabled=references_enabled,
     )
 
 

--- validate_id diff context ---
diff --git a/src/project_standards/validate_id.py b/src/project_standards/validate_id.py
index 6bc5f5d..5edb54c 100644
--- a/src/project_standards/validate_id.py
+++ b/src/project_standards/validate_id.py
@@ -51,13 +51,11 @@ from __future__ import annotations
 import argparse
 import json
 import re
-import secrets
-import string
 import sys
-import unicodedata
 from pathlib import Path
 from typing import Any
 
+from project_standards.id_format import random_token, slugify
 from project_standards.validate_frontmatter import (
     ConfigError,
     FrontmatterParseError,
@@ -68,9 +66,6 @@ from project_standards.validate_frontmatter import (
 
 _DEFAULT_CONFIG = Path(".project-standards.yml")
 
-# Characters used to generate the 6-character base-36 token (digits + lowercase letters).
-_BASE36_CHARS = string.digits + string.ascii_lowercase
-
 # Load the doc_type enum directly from the bundled schema so this list never drifts.
 # No valid doc_type contains a hyphen, which makes split('-', 2) safe: the first segment
 # is always the doc_type prefix with no ambiguity.
@@ -96,30 +91,6 @@ _KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
 _ADR_ID_RE = re.compile(r"^adr-[0-9]{4,}-[a-z0-9]+(-[a-z0-9]+)+$")
 
 
-def slugify(text: str) -> str:
-    """Convert *text* to a lowercase kebab-case slug.
-
-    Normalises Unicode to ASCII, lowercases, then collapses any run of
-    non-alphanumeric characters to a single hyphen. This is the canonical transform
-    for deriving the title-slug portion of a document ``id``.
-
-    Examples::
-
-        slugify("Tailscale ACL tag ordering gotcha")
-        # → "tailscale-acl-tag-ordering-gotcha"
-
-        slugify("Standards Adoption & Compliance Procedure")
-        # → "standards-adoption-compliance-procedure"
-    """
-    # Strip accent marks (e.g. é → e) before lowercasing.
-    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
-    text = text.lower()
-    # Collapse any run of non-alphanumeric characters (spaces, punctuation, symbols)
-    # to a single hyphen, then strip leading/trailing hyphens.
-    text = re.sub(r"[^a-z0-9]+", "-", text)
-    return text.strip("-")
-
-
 def _validate_adr_id(doc_id: str) -> list[str]:
     """Return violation messages for an ADR id; empty list means valid.
 
@@ -317,7 +288,7 @@ def fix_file(path: Path) -> str | None:
         return None
     if not isinstance(title, str) or not title.strip():
         return None
-    token = "".join(secrets.choice(_BASE36_CHARS) for _ in range(6))
+    token = random_token()
     slug = slugify(title)
     if not slug:
         return None
@@ -417,7 +388,7 @@ def main(argv: list[str] | None = None) -> int:
     # via the --schema CLI flag or via a config-level path.  A bare token like
     # "markdown-frontmatter" is a bundled schema name; anything containing a path
     # separator or ending in ".json" is consumer-owned and may define different id
-    # conventions.  Mirrors the _schema_value_is_path check in validate_frontmatter.
+    # conventions.  Mirrors the schema_value_is_path check in validate_frontmatter.
     config_schema = config.schema
     config_has_custom_schema = config_schema is not None and (
         "/" in config_schema or "\\" in config_schema or config_schema.endswith(".json")

exec
/bin/bash -lc "sed -n '1,360p' src/project_standards/validate_references.py && printf '\\n--- rest ---\\n' && sed -n '361,760p' src/project_standards/validate_references.py" in /home/chris/projects/project-standards
 succeeded in 0ms:
"""Opt-in cross-file frontmatter checks the JSON Schema cannot express: id
uniqueness, referential integrity, supersede reciprocity, date ordering, ADR
sequence. Repo-wide pass; warnings never fail the build, errors do."""

from __future__ import annotations

import argparse
import re as _re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from project_standards.validate_frontmatter import (
    ConfigError,
    FrontmatterParseError,
    collect_paths,
    load_config,
    parse_frontmatter,
    schema_value_is_path,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")
_REF_FIELDS = ("related", "depends_on", "supersedes", "superseded_by")  # NOT applies_to

_ADR_NUM_RE = _re.compile(r"^adr-([0-9]{4,})-")


@dataclass
class Doc:
    path: Path
    meta: dict[str, Any]


@dataclass
class Index:
    docs: list[Doc] = field(default_factory=list)
    by_id: dict[str, list[Path]] = field(default_factory=dict)
    ids: set[str] = field(default_factory=set)


def build_index(paths: list[Path]) -> Index:
    index = Index()
    for path in paths:
        try:
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        except OSError, FrontmatterParseError:
            continue
        if not isinstance(meta, dict):
            continue
        doc = Doc(path=path, meta=meta)
        index.docs.append(doc)
        doc_id = meta.get("id")
        if isinstance(doc_id, str) and doc_id:
            index.by_id.setdefault(doc_id, []).append(path)
            index.ids.add(doc_id)
    return index


def check_id_uniqueness(index: Index) -> list[str]:
    errors: list[str] = []
    for doc_id, paths in sorted(index.by_id.items()):
        if len(paths) > 1:
            joined = ", ".join(str(p) for p in sorted(paths))
            errors.append(f"[error] duplicate id '{doc_id}' in: {joined}")
    return errors


def check_dates(index: Index) -> list[str]:
    errors: list[str] = []
    for doc in index.docs:
        created = doc.meta.get("created")
        updated = doc.meta.get("updated")
        reviewed = doc.meta.get("reviewed")
        if isinstance(created, str) and isinstance(updated, str) and created > updated:
            errors.append(f"[error] {doc.path}: created '{created}' is after updated '{updated}'")
        if isinstance(reviewed, str) and isinstance(created, str) and reviewed < created:
            errors.append(
                f"[error] {doc.path}: reviewed '{reviewed}' is before created '{created}'"
            )
    return errors


def _ref_values(meta: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field_name in _REF_FIELDS:
        val = meta.get(field_name)
        if val is None:
            continue
        if isinstance(val, str):
            values.append(val)
        elif isinstance(val, list):
            val_list = cast("list[Any]", val)
            values.extend(v for v in val_list if isinstance(v, str) and v)
    return values


def _resolves(ref: str, index: Index, repo_root: Path) -> bool:
    if ref in index.ids:  # exact id match
        return True
    if "#" in ref:  # section anchors are not document references (standard)
        return False
    if ref.startswith(("/", "../")) or "/../" in ref:
        return False
    return (repo_root / ref).is_file()


def check_references(index: Index, repo_root: Path) -> list[str]:
    warnings: list[str] = []
    for doc in index.docs:
        for ref in _ref_values(doc.meta):
            if not _resolves(ref, index, repo_root):
                warnings.append(f"[warning] {doc.path}: unresolved reference '{ref}'")
    return warnings


def _as_list(val: Any) -> list[str]:
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        val_list = cast("list[Any]", val)
        return [v for v in val_list if isinstance(v, str)]
    return []


def check_reciprocity(index: Index) -> list[str]:
    """Both directions of the supersede invariant (CR-004): A.superseded_by=B requires
    B.supersedes=A, AND A.supersedes=B requires B.superseded_by=A. Only checked when
    the counterpart doc is local (cross-repo ids can't be inspected)."""
    warnings: list[str] = []
    supersedes_map = {
        d.meta.get("id"): set(_as_list(d.meta.get("supersedes")))
        for d in index.docs
        if isinstance(d.meta.get("id"), str)
    }
    superseded_by_map = {
        d.meta.get("id"): set(_as_list(d.meta.get("superseded_by")))
        for d in index.docs
        if isinstance(d.meta.get("id"), str)
    }
    for doc in index.docs:
        a_id = doc.meta.get("id")
        for b_id in _as_list(doc.meta.get("superseded_by")):
            if b_id in supersedes_map and a_id not in supersedes_map[b_id]:
                warnings.append(
                    f"[warning] {doc.path}: '{a_id}' is superseded_by '{b_id}', "
                    f"but '{b_id}' does not list it in supersedes"
                )
        for b_id in _as_list(doc.meta.get("supersedes")):
            if b_id in superseded_by_map and a_id not in superseded_by_map[b_id]:
                warnings.append(
                    f"[warning] {doc.path}: '{a_id}' supersedes '{b_id}', "
                    f"but '{b_id}' does not list it in superseded_by"
                )
    return warnings


def check_adr_sequence(index: Index) -> list[str]:
    by_num: dict[str, list[str]] = {}
    for doc in index.docs:
        if doc.meta.get("doc_type") != "adr":
            continue
        doc_id = doc.meta.get("id")
        if not isinstance(doc_id, str):
            continue
        m = _ADR_NUM_RE.match(doc_id)
        if m:
            by_num.setdefault(m.group(1), []).append(doc_id)
    return [
        f"[error] duplicate ADR number {num}: {', '.join(sorted(ids))}"
        for num, ids in sorted(by_num.items())
        if len(ids) > 1
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-references", description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--glob", metavar="PATTERN")
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not config.references_enabled:
        return 0  # opt-in: disabled -> no checks
    if args.schema is not None or schema_value_is_path(config.schema):
        if not args.quiet:
            print("note: custom schema in use; skipping reference validation")
        return 0

    # validate-references is a REPO-WIDE invariant pass (duplicate ids / ADR numbers,
    # cross-file references), so the index MUST cover the full configured set even when
    # the caller scopes to specific FILE / --glob (project-standards validate forwards
    # them) — otherwise a duplicate in an unselected doc is silently missed (codex P2).
    paths = collect_paths([], None, config.include, config.exclude)
    index = build_index(paths)
    errors: list[str] = []
    warnings: list[str] = []
    errors += check_id_uniqueness(index)
    errors += check_dates(index)
    warnings += check_references(index, Path.cwd())
    warnings += check_reciprocity(index)
    errors += check_adr_sequence(index)

    for w in warnings:
        print(w, file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        print(f"\n✗  {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"✓  references valid ({len(index.docs)} docs, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

--- rest ---

exec
/bin/bash -lc "python -m py_compile src/project_standards/validate_references.py 2>&1 || true && nl -ba src/project_standards/validate_references.py | sed -n '30,50p'" in /home/chris/projects/project-standards
 succeeded in 0ms:
ERROR: Use `uv run python -m py_compile` instead of `python -m py_compile`
    30	class Doc:
    31	    path: Path
    32	    meta: dict[str, Any]
    33	
    34	
    35	@dataclass
    36	class Index:
    37	    docs: list[Doc] = field(default_factory=list)
    38	    by_id: dict[str, list[Path]] = field(default_factory=dict)
    39	    ids: set[str] = field(default_factory=set)
    40	
    41	
    42	def build_index(paths: list[Path]) -> Index:
    43	    index = Index()
    44	    for path in paths:
    45	        try:
    46	            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    47	        except OSError, FrontmatterParseError:
    48	            continue
    49	        if not isinstance(meta, dict):
    50	            continue

exec
/bin/bash -lc 'uv run python -m py_compile src/project_standards/validate_references.py 2>&1 || true' in /home/chris/projects/project-standards
 succeeded in 0ms:
error: Could not acquire lock
  Caused by: Could not create temporary file
  Caused by: Read-only file system (os error 30) at path "/home/chris/.cache/uv/.tmpuMu1xt"

exec
/bin/bash -lc 'UV_CACHE_DIR=/tmp/uv-cache uv run python -m py_compile src/project_standards/validate_references.py 2>&1 || true' in /home/chris/projects/project-standards
 succeeded in 0ms:
exec
/bin/bash -lc "UV_CACHE_DIR=/tmp/uv-cache uv run python --version && UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY'
try:
    raise FileNotFoundError('x')
except OSError, FrontmatterParseError:
    print('caught')
PY
printf 'rc=%s\\n' "'$?' in /home/chris/projects/project-standards
 succeeded in 0ms:
Python 3.14.5
Traceback (most recent call last):
  File "<stdin>", line 2, in <module>
FileNotFoundError: x

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
NameError: name 'FrontmatterParseError' is not defined
rc=1

exec
/bin/bash -lc "UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY'
class FrontmatterParseError(Exception): pass
try:
    raise FrontmatterParseError('fm')
except OSError, FrontmatterParseError:
    print('caught')
PY
printf 'rc=%s\\n' "'$?' in /home/chris/projects/project-standards
 succeeded in 0ms:
caught
rc=0

exec
/bin/bash -lc "sed -n '1,80p' pyproject.toml && sed -n '80,180p' pyproject.toml" in /home/chris/projects/project-standards
 succeeded in 0ms:
[project]
name = "project-standards"
version = "2.0.0"
description = "Reusable project standards, templates, schemas, and validation tools."
license = "Apache-2.0"
license-files = ["LICENSE"]
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "jsonschema>=4.23.0",
    "pyyaml>=6.0.2",
]

[project.scripts]
project-standards = "project_standards.cli:main"
validate-frontmatter = "project_standards.validate_frontmatter:main"
validate-id = "project_standards.validate_id:main"
sync-vscode-colors = "project_standards.sync_vscode_colors:main"
sync-standards-include = "project_standards.sync_standards_include:main"
format-frontmatter = "project_standards.format_frontmatter:main"
validate-references = "project_standards.validate_references:main"

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "ruff>=0.9.0",
    "basedpyright",
    "types-PyYAML",
    "coverage[toml]",
    "pip-audit",
    "pytest-cov",
]

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.ruff]
target-version = "py314"
line-length = 100
src = ["src", "tests"]
# Vendored harness/agent-state Python must not be reformatted (byte-identical contract).
extend-exclude = [".claude/hooks", ".codex/hooks", "docs/handoff"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "C4", "PIE", "PTH", "RET", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true

[tool.basedpyright]
include = ["src", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.14"
pythonPlatform = "All"
failOnWarnings = true

[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 85

exec
/bin/bash -lc 'UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q' in /home/chris/projects/project-standards
 succeeded in 2472ms:
........................................................................ [ 16%]
........................................................................ [ 33%]
........................................................................ [ 50%]
........................................................................ [ 67%]
........................................................................ [ 84%]
...................................................................      [100%]
427 passed in 2.26s

exec
/bin/bash -lc "jq '.properties | keys, .properties.superseded_by, .properties.source' src/project_standards/schemas/markdown-frontmatter.schema.json" in /home/chris/projects/project-standards
 succeeded in 0ms:
[
  "aliases",
  "applies_to",
  "confidence",
  "consumer",
  "created",
  "depends_on",
  "description",
  "doc_type",
  "id",
  "license",
  "owner",
  "project",
  "publish",
  "related",
  "reviewed",
  "schema_version",
  "source",
  "status",
  "superseded_by",
  "supersedes",
  "tags",
  "title",
  "updated",
  "visibility",
  "x_project"
]
null
null

exec
/bin/bash -lc "sed -n '1,260p' src/project_standards/schemas/markdown-frontmatter.schema.json" in /home/chris/projects/project-standards
 succeeded in 0ms:
{
	"$schema": "https://json-schema.org/draft/2020-12/schema",
	"$id": "https://raw.githubusercontent.com/L3DigitalNet/project-standards/main/src/project_standards/schemas/markdown-frontmatter.schema.json",
	"title": "Markdown Frontmatter Standard",
	"description": "Canonical metadata profile for project documentation. See standards/markdown-frontmatter/README.md for the governing standard.",
	"type": "object",
	"additionalProperties": false,
	"required": [
		"schema_version",
		"id",
		"title",
		"description",
		"doc_type",
		"status",
		"created",
		"updated",
		"tags",
		"aliases",
		"related"
	],
	"properties": {
		"schema_version": {
			"type": "string",
			"enum": ["1.0", "1.1"],
			"description": "Version of this metadata schema."
		},
		"id": {
			"type": "string",
			"minLength": 1,
			"pattern": "^[a-z0-9][a-z0-9._-]*$",
			"description": "Stable document identifier independent of file path."
		},
		"title": {
			"type": "string",
			"minLength": 1,
			"description": "Human-readable document title."
		},
		"description": {
			"type": "string",
			"minLength": 1,
			"description": "One-sentence description of document purpose/content."
		},
		"doc_type": {
			"type": "string",
			"enum": [
				"index",
				"note",
				"concept",
				"reference",
				"runbook",
				"spec",
				"plan",
				"adr",
				"decision",
				"research",
				"template",
				"log",
				"prompt",
				"schema"
			],
			"description": "Document type. Avoid `type` to reduce future publishing-tool collisions."
		},
		"status": {
			"type": "string",
			"enum": [
				"draft",
				"active",
				"review",
				"deprecated",
				"archived",
				"superseded",
				"stub"
			],
			"description": "Lifecycle state of the document."
		},
		"created": { "$ref": "#/$defs/date" },
		"updated": { "$ref": "#/$defs/date" },
		"reviewed": {
			"anyOf": [{ "$ref": "#/$defs/date" }, { "type": "null" }],
			"description": "Last correctness review date. Distinct from `updated`."
		},
		"owner": {
			"type": "string",
			"description": "Person, team, repo, or role responsible for maintenance."
		},
		"consumer": {
			"type": "string",
			"enum": ["user", "agent", "mix", "unknown"],
			"description": "Intended reader/consumer of the document."
		},
		"tags": {
			"type": "array",
			"items": { "type": "string", "pattern": "^[a-z0-9][a-z0-9-]*$" },
			"uniqueItems": true,
			"description": "Discovery labels. Prefer lowercase kebab-case."
		},
		"aliases": {
			"type": "array",
			"items": { "type": "string" },
			"uniqueItems": true,
			"description": "Alternate names, abbreviations, or likely search terms."
		},
		"related": {
			"type": "array",
			"items": { "type": "string" },
			"uniqueItems": true,
			"description": "Related document IDs or relative paths."
		},
		"supersedes": {
			"type": "array",
			"items": { "type": "string" },
			"uniqueItems": true,
			"description": "Document IDs this document replaces."
		},
		"superseded_by": {
			"anyOf": [{ "type": "string" }, { "type": "null" }],
			"description": "ID of the document that replaces this one."
		},
		"depends_on": {
			"type": "array",
			"items": { "type": "string" },
			"uniqueItems": true,
			"description": "Document IDs this document depends on."
		},
		"applies_to": {
			"type": "array",
			"items": { "type": "string" },
			"uniqueItems": true,
			"description": "Scopes, services, or components this document applies to."
		},
		"source": {
			"type": "array",
			"items": { "type": "string" },
			"uniqueItems": true,
			"description": "Sources used to create or support the document."
		},
		"confidence": {
			"type": "string",
			"enum": ["high", "medium", "low", "unknown"],
			"description": "Reliability signal for LLM and human use."
		},
		"visibility": {
			"type": "string",
			"enum": ["private", "internal", "public"],
			"description": "Exposure level."
		},
		"license": {
			"anyOf": [{ "type": "string" }, { "type": "null" }],
			"description": "License or reuse terms, if applicable."
		},
		"publish": {
			"type": "object",
			"additionalProperties": true,
			"description": "Optional namespace for future publishing-tool metadata."
		},
		"project": {
			"type": "object",
			"additionalProperties": true,
			"description": "Optional namespace for project-specific extensions."
		},
		"x_project": {
			"type": "object",
			"additionalProperties": true,
			"description": "Alternate namespace for project-specific extensions."
		}
	},
	"$defs": { "date": { "type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$" } }
}

exec
/bin/bash -lc "grep -n \"def collect_paths\\|def main\" -A80 -B20 src/project_standards/validate_frontmatter.py" in /home/chris/projects/project-standards
 succeeded in 0ms:
232-        if require_frontmatter:
233-            return [f"{path}: no frontmatter found at top of file"]
234-        return []
235-
236-    errors: list[str] = []
237-    for error in sorted(validator.iter_errors(meta), key=lambda e: list(e.path)):  # pyright: ignore[reportUnknownMemberType]
238-        field = ".".join(str(p) for p in error.path) or "(root)"
239-        errors.append(f"{path}: [{field}] {error.message}")
240-
241-    if require_adr_sections and meta.get("doc_type") == "adr":
242-        for section in missing_adr_sections(text):
243-            errors.append(f"{path}: missing required ADR section '## {section}'")
244-    return errors
245-
246-
247-# ---------------------------------------------------------------------------
248-# Path collection
249-# ---------------------------------------------------------------------------
250-
251-
252:def collect_paths(
253-    explicit: list[Path],
254-    glob_pattern: str | None,
255-    include_patterns: list[str],
256-    exclude_patterns: list[str],
257-) -> list[Path]:
258-    """Resolve the final set of files to check.
259-
260-    Explicit file arguments and/or a --glob take precedence: when either is given,
261-    the config `include` patterns are NOT added (naming files means "just these").
262-    Only when nothing is named do we fall back to config `include`, and failing
263-    that to every Markdown file under cwd. `exclude` is applied in all cases.
264-    """
265-    paths: set[Path] = set()
266-
267-    if explicit or glob_pattern:
268-        paths.update(p for p in explicit if p.is_file())
269-        if glob_pattern:
270-            paths.update(p for p in Path().glob(glob_pattern) if p.is_file())
271-    elif include_patterns:
272-        for pattern in include_patterns:
273-            paths.update(p for p in Path().glob(pattern) if p.is_file())
274-    else:
275-        paths.update(p for p in Path().glob("**/*.md") if p.is_file())
276-
277-    # Exclusion matches each candidate's posix path against the patterns with fnmatch
278-    # rather than Path.glob. Path.glob's `**` semantics are version-dependent (on Python
279-    # 3.13+ a trailing `**` also matches files; on <=3.12 it matches directories only),
280-    # so a directory pattern like "docs/decisions/**" would silently fail to exclude the
281-    # files beneath it on older interpreters. fnmatch's `*` spans path
282-    # separators, giving consistent prefix-style exclusion on every supported
283-    # Python version.
284-    def is_excluded(path: Path) -> bool:
285-        posix = path.as_posix()
286-        return any(fnmatchcase(posix, pattern) for pattern in exclude_patterns)
287-
288-    return sorted(p for p in paths if not is_excluded(p))
289-
290-
291-# ---------------------------------------------------------------------------
292-# Config (nested markdown.{frontmatter,adr} shape)
293-# ---------------------------------------------------------------------------
294-
295-
296-class ProjectConfig:
297-    """Resolved view of `.project-standards.yml`.
298-
299-    Holds the `markdown.frontmatter` settings (schema/include/exclude/required)
300-    plus the separate, opt-in `markdown.adr` flags. The two namespaces stay
301-    conceptually distinct in the file; this is the validator's merged in-memory
302-    view of them.
303-    """
304-
305-    def __init__(
306-        self,
307-        *,
308-        schema: str | None,
309-        include: list[str],
310-        exclude: list[str],
311-        required: bool,
312-        require_adr_sections: bool,
313-        frontmatter_version: str | None = None,
314-        adr_version: str | None = None,
315-        python_tooling_version: str | None = None,
316-        markdown_tooling_version: str | None = None,
317-        references_enabled: bool = False,
318-    ) -> None:
319-        self.schema = schema
320-        self.include = include
321-        self.exclude = exclude
322-        self.required = required
323-        self.require_adr_sections = require_adr_sections
324-        self.frontmatter_version = frontmatter_version
325-        self.adr_version = adr_version
326-        self.python_tooling_version = python_tooling_version
327-        self.markdown_tooling_version = markdown_tooling_version
328-        self.references_enabled = references_enabled
329-
330-
331-def resolve_effective_schema(
332-    args_schema: Path | None, config: ProjectConfig, registry: Registry
--
449-
450-    return ProjectConfig(
451-        schema=schema,
452-        include=include,
453-        exclude=exclude,
454-        required=required,
455-        require_adr_sections=require_adr_sections,
456-        frontmatter_version=frontmatter_version,
457-        adr_version=adr_version,
458-        python_tooling_version=python_tooling_version,
459-        markdown_tooling_version=markdown_tooling_version,
460-        references_enabled=references_enabled,
461-    )
462-
463-
464-# ---------------------------------------------------------------------------
465-# Entry point
466-# ---------------------------------------------------------------------------
467-
468-
469:def main(argv: list[str] | None = None) -> int:
470-    parser = argparse.ArgumentParser(
471-        description=__doc__,
472-        formatter_class=argparse.RawDescriptionHelpFormatter,
473-    )
474-    parser.add_argument(
475-        "files",
476-        nargs="*",
477-        type=Path,
478-        metavar="FILE",
479-        help="Markdown files to validate. With no files/globs/config includes, "
480-        "defaults to all **/*.md under cwd.",
481-    )
482-    parser.add_argument(
483-        "--schema",
484-        type=Path,
485-        default=None,
486-        metavar="PATH",
487-        help="JSON Schema file to validate against (overrides the config).",
488-    )
489-    parser.add_argument(
490-        "--glob",
491-        metavar="PATTERN",
492-        help="Additional glob pattern relative to cwd.",
493-    )
494-    parser.add_argument(
495-        "--config",
496-        type=Path,
497-        default=_DEFAULT_CONFIG,
498-        metavar="PATH",
499-        help=f"Project config file (default: {_DEFAULT_CONFIG}).",
500-    )
501-    parser.add_argument(
502-        "--no-require-frontmatter",
503-        action="store_true",
504-        help="Do not fail files that have no frontmatter block.",
505-    )
506-    parser.add_argument(
507-        "--quiet",
508-        "-q",
509-        action="store_true",
510-        help="Suppress success output.",
511-    )
512-    args = parser.parse_args(argv)
513-
514-    try:
515-        config = load_config(args.config)
516-    except ConfigError as exc:
517-        print(f"error: {exc}", file=sys.stderr)
518-        return 2
519-
520-    try:
521-        registry = load_registry()
522-    except RegistryError as exc:
523-        print(f"error: {exc}", file=sys.stderr)
524-        return 2
525-
526-    # python_tooling.version is metadata only: validated if present, never emitted.
527-    if config.python_tooling_version is not None and not registry.is_known_python_tooling(
528-        config.python_tooling_version
529-    ):
530-        print(
531-            f"error: unknown python_tooling.version {config.python_tooling_version!r}",
532-            file=sys.stderr,
533-        )
534-        return 2
535-
536-    # markdown_tooling.version is metadata only: validated if present, never emitted.
537-    if config.markdown_tooling_version is not None and not registry.is_known_markdown_tooling(
538-        config.markdown_tooling_version
539-    ):
540-        print(
541-            f"error: unknown markdown_tooling.version {config.markdown_tooling_version!r}",
542-            file=sys.stderr,
543-        )
544-        return 2
545-
546-    # Resolve first: this validates that a configured frontmatter.version is a known
547-    # bundled contract (unknown/typo versions report "unknown frontmatter version"
548-    # here, before the compatibility gate, so they are never masked as a combo error).
549-    try:

exec
/bin/bash -lc "sed -n '546,650p' src/project_standards/validate_frontmatter.py" in /home/chris/projects/project-standards
 succeeded in 0ms:
    # Resolve first: this validates that a configured frontmatter.version is a known
    # bundled contract (unknown/typo versions report "unknown frontmatter version"
    # here, before the compatibility gate, so they are never masked as a combo error).
    try:
        schema_path = resolve_effective_schema(args.schema, config, registry)
    except (ConfigError, RegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # FM->ADR compatibility (bundled Frontmatter only; --schema bypasses it).
    if args.schema is None:
        try:
            incompatibility = frontmatter_adr_incompatibility(config, registry)
        except RegistryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if incompatibility is not None:
            print(f"error: {incompatibility}", file=sys.stderr)
            return 2

    try:
        schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot load schema {schema_path}: {exc}", file=sys.stderr)
        return 2

    try:
        Draft202012Validator.check_schema(schema)  # pyright: ignore[reportUnknownMemberType]
    except SchemaError as exc:
        print(f"error: invalid schema {schema_path}: {exc.message}", file=sys.stderr)
        return 2
    validator = Draft202012Validator(schema)

    require_frontmatter = config.required and not args.no_require_frontmatter
    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)

    if not paths:
        if not args.quiet:
            print("no files matched", file=sys.stderr)
        return 0

    all_errors: list[str] = []
    for path in paths:
        all_errors.extend(
            validate_file(
                path,
                validator,
                require_frontmatter=require_frontmatter,
                require_adr_sections=config.require_adr_sections,
            )
        )

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        print(
            f"\n✗  {len(all_errors)} error(s) across {len(paths)} file(s)",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(f"✓  {len(paths)} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

exec
/bin/bash -lc "sed -n '1,240p' src/project_standards/validate_id.py && sed -n '240,480p' src/project_standards/validate_id.py" in /home/chris/projects/project-standards
 succeeded in 0ms:
"""Validate that frontmatter ``id`` fields follow the correct format for their doc_type.

Two formats are in use; which applies depends on ``doc_type``:

**Standard format** — all doc_types except ``adr``:
``{doc_type}-{6-char base36 token}-{readable-slug}``

- ``{doc_type}``        matches the document's own ``doc_type`` field value.
- ``{base36 token}``    is exactly 6 characters from [0-9a-z] (the base-36 alphabet).
- ``{readable-slug}``   is a lowercase kebab-case hint frozen at creation time.
                        It is NOT validated against the current ``title`` — ids must be stable
                        even when documents are renamed.

Example: ``note-a3f9zk-tailscale-acl-tag-ordering-gotcha``.

**ADR format** — ``doc_type: adr``:
``adr-{NNNN}-{repo-name}-{short-title}``

- ``{NNNN}``            is a zero-padded, repo-scoped sequence number (at least 4 digits).
- ``{repo-name}``       is the repository name in kebab-case; it makes the id globally
                        unique so ADRs can be cited by id from other repositories' ``related:``
                        fields without ambiguity.
- ``{short-title}``     is a kebab-case short form of the decision title, set once at creation.

Example: ``adr-0001-homelab-use-postgresql-for-persistent-storage``.

Usage:
    validate-id FILE [FILE ...]
    validate-id --config .project-standards.yml
    validate-id --quiet --config .project-standards.yml
    validate-id --glob 'docs/**/*.md'
    validate-id --fix --config .project-standards.yml

When ``--schema PATH`` is provided, id-format validation is **skipped** (exit 0).
A custom schema signals non-standard id conventions; running the bundled base36 rules
against those files would produce false positives.

``--no-require-frontmatter`` is accepted for compatibility (forwarded by
``project-standards validate``) but has no effect here — id validation already
silently skips files with no frontmatter.

Exit codes: 0 = all ids valid (or skipped due to --schema); 1 = violations found;
2 = config/invocation error.

Files missing frontmatter or missing ``id`` / ``doc_type`` fields are silently
skipped — those structural gaps are the frontmatter schema validator's job.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from project_standards.id_format import random_token, slugify
from project_standards.validate_frontmatter import (
    ConfigError,
    FrontmatterParseError,
    collect_paths,
    load_config,
    parse_frontmatter,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")

# Load the doc_type enum directly from the bundled schema so this list never drifts.
# No valid doc_type contains a hyphen, which makes split('-', 2) safe: the first segment
# is always the doc_type prefix with no ambiguity.
_SCHEMA_PATH = Path(__file__).parent / "schemas" / "markdown-frontmatter.schema.json"
_VALID_DOC_TYPES: frozenset[str] = frozenset(
    json.loads(_SCHEMA_PATH.read_text())["properties"]["doc_type"]["enum"]
)

# Exactly 6 characters from the base-36 alphabet (digits 0-9 + lowercase letters a-z).
_BASE36_RE = re.compile(r"^[0-9a-z]{6}$")

# Non-empty lowercase kebab-case with no consecutive hyphens: each hyphen must be surrounded
# by at least one alphanumeric on each side (i.e. every segment between hyphens is non-empty).
# slugify() already guarantees this for derived slugs; this guard catches hand-crafted ids
# that would produce double hyphens (e.g. "bad--slug").
_KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# ADR id: adr-{NNNN}-{repo-name}-{short-title}
# NNNN is at least 4 zero-padded digits.  The suffix after the sequence number requires at
# least two hyphen-separated segments (repo-name and short-title); a single-segment suffix
# like "adr-0001-repo" is rejected.  Consecutive hyphens are impossible because each segment
# is [a-z0-9]+.
_ADR_ID_RE = re.compile(r"^adr-[0-9]{4,}-[a-z0-9]+(-[a-z0-9]+)+$")


def _validate_adr_id(doc_id: str) -> list[str]:
    """Return violation messages for an ADR id; empty list means valid.

    ADRs use ``adr-{NNNN}-{repo-name}-{short-title}`` rather than the base-36 format
    because the repo-name segment provides global uniqueness: an ADR id remains
    unambiguous when cited from another repository's ``related:`` list. A random token
    cannot provide that property.

    Title-slug consistency is not checked here — the short-title is set once at ADR
    creation and is not expected to track the mutable ``title`` field.
    """
    if not _ADR_ID_RE.match(doc_id):
        return [
            f"ADR id must match adr-{{NNNN}}-{{repo-name}}-{{short-title}} "
            f"(e.g. adr-0001-homelab-use-postgresql); got '{doc_id}'"
        ]
    return []


def validate_id(doc_id: str, doc_type: str) -> list[str]:
    """Return violation messages for *doc_id*; empty list means the id is valid.

    Dispatches to ``_validate_adr_id`` for ``doc_type == 'adr'`` (sequential-number
    format) and validates the base-36 three-segment format for all other doc_types.

    Standard-format checks in order:
    1. Three segments present: ``{doc_type}-{base36}-{readable-slug}``.
    2. Segment 1 is a valid doc_type and matches the document's ``doc_type`` field.
    3. Segment 2 is exactly 6 base-36 characters ([0-9a-z]{6}).
    4. Segment 3 is non-empty lowercase kebab-case.

    The readable-slug (segment 3) is validated as well-formed kebab-case but NOT matched
    against the current ``title`` — the slug is frozen at creation time and must remain
    stable even if the title is later edited.

    Each returned string is a plain message (no path prefix); callers annotate with path.
    """
    if doc_type == "adr":
        return _validate_adr_id(doc_id)

    # maxsplit=2 so the readable-slug segment may itself contain hyphens.
    # e.g. "note-a3f9zk-tailscale-acl-gotcha" → ["note", "a3f9zk", "tailscale-acl-gotcha"]
    parts = doc_id.split("-", 2)

    if len(parts) < 3:
        return [
            f"must be '{doc_type}-<6-char base36>-<readable-slug>'; got '{doc_id}' (too few hyphen-separated segments)"
        ]

    id_type, id_base36, id_readable_slug = parts
    errors: list[str] = []

    # --- Segment 1: doc_type prefix ---
    if id_type not in _VALID_DOC_TYPES:
        errors.append(
            f"prefix '{id_type}' is not a valid doc_type "
            f"(valid: {', '.join(sorted(_VALID_DOC_TYPES))})"
        )
    elif id_type != doc_type:
        # The prefix must exactly match the document's own doc_type — catching cases
        # where a document's type was changed after the id was authored.
        errors.append(f"prefix '{id_type}' does not match the document's doc_type '{doc_type}'")

    # --- Segment 2: base-36 token ---
    if not _BASE36_RE.match(id_base36):
        errors.append(
            f"base-36 segment '{id_base36}' must be exactly 6 characters "
            f"from [0-9a-z] (got {len(id_base36)} chars)"
        )

    # --- Segment 3: readable slug ---
    if not id_readable_slug:
        errors.append("readable-slug segment (after the base-36 token) is empty")
    elif not _KEBAB_RE.match(id_readable_slug):
        errors.append(
            f"readable-slug '{id_readable_slug}' must be lowercase kebab-case ([a-z0-9][a-z0-9-]*)"
        )

    return errors


def check_file(path: Path) -> list[str]:
    """Return formatted violation lines for *path*; empty list means the file is clean.

    Files without frontmatter, or whose ``id`` / ``doc_type`` / ``title`` fields are
    absent or have the wrong type, are silently skipped — those gaps are caught by the
    frontmatter schema validator rather than duplicated here.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read: {exc}"]

    try:
        meta: dict[str, Any] | None = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        return [f"{path}: invalid YAML frontmatter: {exc}"]

    if meta is None:
        return []

    doc_id = meta.get("id")
    doc_type = meta.get("doc_type")

    # Skip files where the required fields are missing or have wrong types; those
    # structural violations belong to the schema validator's output, not this one's.
    if not isinstance(doc_id, str) or not doc_id:
        return []
    if not isinstance(doc_type, str) or doc_type not in _VALID_DOC_TYPES:
        return []

    violations = validate_id(doc_id, doc_type)
    return [f"{path}: [id] {msg}" for msg in violations]


def _replace_frontmatter_id(text: str, new_id: str) -> str:
    """Replace the ``id:`` value inside the leading frontmatter block.

    Only modifies the id value; all other content — including inline comments on the
    same line (e.g. ``id: 'old'  # frozen at creation``) — is preserved.
    Returns *text* unchanged if there is no frontmatter block or no ``id:`` line.

    *text* must use LF-only line endings (callers normalise before calling).
    """
    match = re.match(r"^(---[ \t]*\n)(.*?)(\n---[ \t]*(?:\n|$))", text, re.DOTALL)
    if not match:
        return text
    prefix, fm_body, suffix = match.group(1), match.group(2), match.group(3)
    rest = text[match.end() :]

    # Three capture groups:
    #   1. key prefix  (id:[ \t]*)                     — not used in replacement
    #   2. value       single-/double-quoted or lazy unquoted
    #   3. trailing    optional whitespace + inline comment
    # The lazy unquoted form [^\n]*? yields the shortest match, leaving any "  # comment"
    # suffix to group 3 rather than including it in the value.
    def _repl(m: re.Match[str]) -> str:
        return f"id: '{new_id}'" + (m.group(3) or "")

    new_fm_body = re.sub(
        r"^(id:[ \t]*)('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|[^\n]*?)"
        r"([ \t]*(?:#[^\n]*)?)$",
        _repl,
        fm_body,
        flags=re.MULTILINE,
        count=1,
    )
    )
    if new_fm_body == fm_body:
        return text
    return prefix + new_fm_body + suffix + rest


def fix_file(path: Path) -> str | None:
    """Rewrite the ``id`` field in *path* to a valid standard-format id.

    Derives the new id from the document's ``doc_type`` and ``title`` fields:
    ``{doc_type}-{6-char base36 token}-{slugify(title)}``.

    Returns the new id string if the file was modified. Returns ``None`` when:
    - the id is already valid (nothing to do),
    - the ``doc_type`` is ``adr`` (repo-name cannot be auto-derived),
    - required fields (``doc_type``, ``title``) are absent or have wrong types,
    - or ``title`` slugifies to an empty string.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Normalise to LF-only for YAML parsing and _replace_frontmatter_id (which requires LF).
    # Keep the original decoded string so we can reconstruct the output line-by-line,
    # preserving each line's individual ending — including files with mixed \r\n / \n.
    text_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        meta: dict[str, Any] | None = parse_frontmatter(text_lf)
    except FrontmatterParseError:
        return None
    if meta is None:
        return None
    doc_id = meta.get("id")
    doc_type = meta.get("doc_type")
    title = meta.get("title")
    if not isinstance(doc_id, str) or not doc_id:
        return None
    if not isinstance(doc_type, str) or doc_type not in _VALID_DOC_TYPES:
        return None
    # ADR ids include a repo-name segment that cannot be derived from document fields.
    if doc_type == "adr":
        return None
    # Already valid — nothing to fix.
    if not validate_id(doc_id, doc_type):
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    token = random_token()
    slug = slugify(title)
    if not slug:
        return None
    new_id = f"{doc_type}-{token}-{slug}"
    new_text_lf = _replace_frontmatter_id(text_lf, new_id)
    if new_text_lf == text_lf:
        return None
    # Reconstruct output preserving per-line endings.  Only the id: line differs between
    # text_lf and new_text_lf; all other lines — whether \r\n, \n, or \r — are kept
    # byte-exact.  This avoids converting bare-LF lines to CRLF in mixed-ending files.
    orig_lines = text.splitlines(keepends=True)
    new_lines_lf = new_text_lf.splitlines(keepends=True)
    if len(orig_lines) != len(new_lines_lf):
        # Unexpected line-count mismatch; fall back to writing the LF-normalised content.
        path.write_bytes(new_text_lf.encode("utf-8"))
        return new_id
    output: list[str] = []
    for orig_line, new_line_lf in zip(orig_lines, new_lines_lf, strict=False):
        orig_stripped = orig_line.rstrip("\r\n")
        new_stripped = new_line_lf.rstrip("\r\n")
        if orig_stripped == new_stripped:
            output.append(orig_line)  # unchanged — keep original bytes exactly
        else:
            # Content changed: apply new content with the original line ending.
            orig_ending = orig_line[len(orig_stripped) :]
            output.append(new_stripped + orig_ending)
    path.write_bytes("".join(output).encode("utf-8"))
    return new_id


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns an exit code."""
    parser = argparse.ArgumentParser(
        prog="validate-id",
        description=(
            "Validate that frontmatter id fields follow [doc_type]-[base36-6]-[readable-slug]."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        type=Path,
        help="Markdown files to validate. Omit to use the project config include list.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        type=Path,
        default=_DEFAULT_CONFIG,
        help=f"Project config file (default: {_DEFAULT_CONFIG}).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file output; exit code only.",
    )
    parser.add_argument(
        "--glob",
        metavar="PATTERN",
        help="Additional glob pattern relative to cwd (same semantics as validate-frontmatter).",
    )
    parser.add_argument(
        "--schema",
        metavar="PATH",
        type=Path,
        default=None,
        help=(
            "Custom JSON Schema override (see validate-frontmatter). "
            "When provided, id-format validation is skipped entirely — "
            "custom schemas may define different id conventions."
        ),
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Fix non-compliant ids in place, deriving the new id from doc_type and title: "
            "{doc_type}-{base36-token}-{slugify(title)}. "
            "ADR ids (which require a repo-name segment) are skipped with a warning."
        ),
    )
    # Accepted for compatibility when project-standards validate forwards its full argv.
    # Has no effect here: id validation already silently skips files without frontmatter.
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Skip id-format validation when a custom (non-bundled) schema is in use — either
    # via the --schema CLI flag or via a config-level path.  A bare token like
    # "markdown-frontmatter" is a bundled schema name; anything containing a path
    # separator or ending in ".json" is consumer-owned and may define different id
    # conventions.  Mirrors the schema_value_is_path check in validate_frontmatter.
    config_schema = config.schema
    config_has_custom_schema = config_schema is not None and (
        "/" in config_schema or "\\" in config_schema or config_schema.endswith(".json")
    )
    if args.schema is not None or config_has_custom_schema:
        if not args.quiet:
            print("note: custom schema in use; skipping id-format validation")
        return 0

    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)

    if args.fix:
        fixed: list[tuple[Path, str]] = []
        adr_skipped: list[Path] = []
        remaining_errors: list[str] = []

        for path in paths:
            violations = check_file(path)
            if not violations:
                continue
            new_id = fix_file(path)
            if new_id is not None:
                fixed.append((path, new_id))
            else:
                # fix_file returns None for ADR files; distinguish for a clearer message.
                try:
                    meta = parse_frontmatter(path.read_text(encoding="utf-8"))
                    if isinstance(meta, dict) and meta.get("doc_type") == "adr":
                        adr_skipped.append(path)
                        continue
                except OSError, FrontmatterParseError:
                    pass
                remaining_errors.extend(violations)

        if not args.quiet:
            for path, new_id in fixed:
                print(f"fixed: {path}: id → '{new_id}'")
            for path in adr_skipped:
                print(
                    f"skipped (ADR): {path}: ADR ids require a repo-name segment "
                    f"(e.g. adr-0001-myrepo-short-title) — fix manually",
                    file=sys.stderr,
                )
            for error in remaining_errors:
                print(error)
            if remaining_errors:
                file_count = len({e.split(":")[0] for e in remaining_errors})
                print(
                    f"\n✗  {len(remaining_errors)} violation(s) remain across {file_count} file(s)"
                )
            elif fixed:
                print(f"\n✓  {len(fixed)} id(s) fixed")
            elif not adr_skipped:
                print(f"✓  {len(paths)} file(s) already valid")

        return 1 if (remaining_errors or adr_skipped) else 0

    all_errors: list[str] = []
    for path in paths:
        all_errors.extend(check_file(path))

    if not args.quiet:
        for error in all_errors:
            print(error)

    if all_errors:
        if not args.quiet:
            file_count = len({e.split(":")[0] for e in all_errors})
            print(f"\n✗  {len(all_errors)} violation(s) across {file_count} file(s)")
        return 1

    if not args.quiet:
        print(f"✓  {len(paths)} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

exec
/bin/bash -lc 'git show bd5d423fc9c8286f5a9634d5d85d0278de6ea788:src/project_standards/validate_id.py | grep -n "if args.schema" -A8 -B8' in /home/chris/projects/project-standards
 succeeded in 0ms:
417-    # via the --schema CLI flag or via a config-level path.  A bare token like
418-    # "markdown-frontmatter" is a bundled schema name; anything containing a path
419-    # separator or ending in ".json" is consumer-owned and may define different id
420-    # conventions.  Mirrors the _schema_value_is_path check in validate_frontmatter.
421-    config_schema = config.schema
422-    config_has_custom_schema = config_schema is not None and (
423-        "/" in config_schema or "\\" in config_schema or config_schema.endswith(".json")
424-    )
425:    if args.schema is not None or config_has_custom_schema:
426-        if not args.quiet:
427-            print("note: custom schema in use; skipping id-format validation")
428-        return 0
429-
430-    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
431-
432-    if args.fix:
433-        fixed: list[tuple[Path, str]] = []

exec
/bin/bash -lc "grep -R \"bump-updated\\|project-standards fix\\|format-frontmatter\" -n README.md standards src/project_standards/README.md .pre-commit-hooks.yaml tests | head -80" in /home/chris/projects/project-standards
 succeeded in 0ms:
grep: tests/__pycache__/test_precommit_hooks.cpython-314-pytest-9.0.3.pyc: binary file matches
grep: tests/__pycache__/test_format_frontmatter.cpython-314-pytest-9.0.3.pyc: binary file matches
standards/markdown-frontmatter/adopt.md:278:**Auto-fix mode:** run `project-standards fix` (same flags) to format frontmatter, regenerate non-compliant ids, and then re-validate. This reduces the manual fixup burden when adopting the standard on an existing codebase. Skips entirely under a custom schema.
standards/markdown-frontmatter/README.md:460:- **Auto-fix and re-validate:** `uv run project-standards fix --config .project-standards.yml` — formats frontmatter (applies transforms, re-quotes, reorders keys), regenerates non-compliant ids, then re-runs the full `validate` contract. Skips entirely under a custom schema. Run this when adopting the standard on an existing codebase to reduce manual fixups.
src/project_standards/README.md:18:    - [format-frontmatter](#format-frontmatter)
src/project_standards/README.md:20:    - [project-standards fix (combined fix command)](#project-standards-fix-combined-fix-command)
src/project_standards/README.md:39:| `project-standards fix [FLAGS] [FILE …]` | `cli.py` | Format frontmatter, fix ids, then re-validate (bundled schema only) |
src/project_standards/README.md:43:| `format-frontmatter [FLAGS] [FILE …]` | `format_frontmatter.py` | Reformat frontmatter (canonical key order, quoting, transforms) |
src/project_standards/README.md:47:`project-standards fix` is an early-dispatch command that runs `format_frontmatter.main(["--write", …])`, then `validate_id.main(["--fix", …])`, and finally the full `validate` contract (schema + id + references). It skips entirely when a custom schema is in use (flag `--schema` or `markdown.frontmatter.schema:` pointing to a file path).
src/project_standards/README.md:53:Three validators and one formatter enforce and repair the managed-document contract. They share the same config file and the same `collect_paths()` logic, and are all invoked by `project-standards validate` / `project-standards fix`.
src/project_standards/README.md:167:### format-frontmatter
src/project_standards/README.md:214:### project-standards fix (combined fix command)
src/project_standards/README.md:216:`project-standards fix [FLAGS] [FILE …]` is a three-phase pipeline:
.pre-commit-hooks.yaml:3:- id: format-frontmatter-fix
.pre-commit-hooks.yaml:5:  entry: format-frontmatter --write
.pre-commit-hooks.yaml:9:- id: format-frontmatter-check
.pre-commit-hooks.yaml:11:  entry: format-frontmatter --check
tests/test_precommit_hooks.py:20:        "format-frontmatter-fix",
tests/test_precommit_hooks.py:21:        "format-frontmatter-check",
tests/test_format_frontmatter.py:808:    rc = main(["--write", "--bump-updated", "--config", str(cfg), str(f)])

exec
/bin/bash -lc "sed -n '1,150p' .github/workflows/validate-markdown-frontmatter.yml" in /home/chris/projects/project-standards
 succeeded in 0ms:
name: Validate Markdown Frontmatter

on:
  push:
    branches: ["main"]
    paths:
      - "**/*.md"
      - "src/**"
      - ".project-standards.yml"
      - "pyproject.toml"
  pull_request:
    paths:
      - "**/*.md"
      - "src/**"
      - ".project-standards.yml"
      - "pyproject.toml"

  # Reusable: call this workflow from any consuming repo. Because the validator
  # bundles the schema in its wheel, consuming repos do not need to check out this
  # repo or vendor the schema — `uv tool install` brings both.
  #
  #   jobs:
  #     validate:
  #       uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v1
  #       with:
  #         config-path: .project-standards.yml
  #         standards-ref: v1
  workflow_call:
    inputs:
      config-path:
        description: "Path to the project standards config file in the calling repo."
        required: false
        type: string
        default: ".project-standards.yml"
      standards-ref:
        # The git ref the validator + bundled schema install from. Defaults to the
        # major tag `v2` (NOT `main`) so a caller that pins `uses: ...@v2` but omits
        # this input still gets pinned, reproducible validation instead of floating
        # on unreleased changes. Set it to match your `uses:` pin (e.g. `v2`, or a
        # full version like `v2.0.0` for an immutable pin).
        description: "project-standards git ref to install the validator from (match your uses: @vN pin)."
        required: false
        type: string
        default: "v2"

jobs:
  validate:
    name: Frontmatter
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v6

      - name: Set up uv
        # SHA-pinned: setup-uv publishes no moving major/minor tag as of v8.0.0
        # (no @v8), so a tag pin no longer resolves and would break every caller.
        # Dependabot bumps the SHA via the trailing version comment.
        uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
        with:
          # Only this repo ships a uv.lock for the cache to key on. Consuming
          # repos install the validator via `uv tool install` from git and have
          # no lockfile, so enabling the cache there only produces the
          # "cache will never get invalidated" warning. Gate it on the same
          # caller-identity check the install/validate steps below use.
          enable-cache: ${{ github.repository == 'L3DigitalNet/project-standards' }}

      # Running inside this repo (push/PR or self-call): use the local source.
      - name: Install validator (this repo)
        if: github.repository == 'L3DigitalNet/project-standards'
        run: uv sync --dev

      - name: Validate frontmatter (this repo)
        if: github.repository == 'L3DigitalNet/project-standards'
        run: uv run validate-frontmatter --config "${{ inputs.config-path || '.project-standards.yml' }}"

      - name: Validate id format (this repo)
        if: github.repository == 'L3DigitalNet/project-standards'
        run: uv run validate-id --config "${{ inputs.config-path || '.project-standards.yml' }}"

      - name: Validate references (this repo)
        if: github.repository == 'L3DigitalNet/project-standards'
        run: uv run validate-references --config "${{ inputs.config-path || '.project-standards.yml' }}"

      # Running in a consuming repo: install the validator (and its bundled schema)
      # from the standards repo as a tool, then validate the caller's files.
      - name: Install validator (consuming repo)
        if: github.repository != 'L3DigitalNet/project-standards'
        run: |
          uv tool install \
            "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v1' }}"

      - name: Validate frontmatter (consuming repo)
        if: github.repository != 'L3DigitalNet/project-standards'
        run: validate-frontmatter --config "${{ inputs.config-path || '.project-standards.yml' }}"

      - name: Validate id format (consuming repo)
        if: github.repository != 'L3DigitalNet/project-standards'
        run: validate-id --config "${{ inputs.config-path || '.project-standards.yml' }}"

      - name: Validate references (consuming repo)
        if: github.repository != 'L3DigitalNet/project-standards'
        run: validate-references --config "${{ inputs.config-path || '.project-standards.yml' }}"

exec
/bin/bash -lc "sed -n '1,260p' tests/test_format_frontmatter.py && sed -n '260,560p' tests/test_format_frontmatter.py && sed -n '560,940p' tests/test_format_frontmatter.py" in /home/chris/projects/project-standards
 succeeded in 0ms:
import io
import subprocess
import sys
from pathlib import Path

import pytest

from project_standards.format_frontmatter import (
    Entry,
    _leading_run,  # pyright: ignore[reportPrivateUsage]
    _split_value_comment,  # pyright: ignore[reportPrivateUsage]
    _today_iso,  # pyright: ignore[reportPrivateUsage]
    format_text,
    main,
    tokenize,
)

CLEAN = (
    "---\n"
    "schema_version: '1.1'\n"
    "id: 'note-a3f9zk-x'\n"
    "title: 'X'\n"
    "description: 'A doc.'\n"
    "doc_type: 'note'\n"
    "status: 'draft'\n"
    "created: '2026-06-08'\n"
    "updated: '2026-06-08'\n"
    "tags: []\n"
    "aliases: []\n"
    "related: []\n"
    "---\n"
    "# Body\n"
)


def test_clean_input_is_byte_identical():
    # format_text returns (new_text, changed, warnings). Already-canonical -> no change.
    new, changed, _warnings = format_text(CLEAN, path=None)
    assert new == CLEAN
    assert changed is False


def test_no_frontmatter_is_noop():
    body = "# Just a body\n\nNo frontmatter here.\n"
    new, changed, _warnings = format_text(body, path=None)
    assert new == body
    assert changed is False


def test_comment_block_preserved_on_roundtrip():
    src = CLEAN.replace("id: 'note-a3f9zk-x'\n", "id: 'note-a3f9zk-x'  # frozen at creation\n")
    new, changed, _warnings = format_text(src, path=None)
    assert "# frozen at creation" in new
    assert changed is False


def test_duplicate_top_level_key_is_refused():
    # PyYAML silently keeps the last duplicate; the formatter must NOT rewrite such a
    # block (it would erase the human-visible conflict). It skips with a warning. (CR-002)
    src = CLEAN.replace("tags: []\n", "tags: []\ntags: ['x']\n")
    new, changed, warnings = format_text(src, path=None)
    assert new == src
    assert changed is False
    assert any("duplicate" in w for w in warnings)


def test_reorder_to_canonical_order():
    src = (
        "---\n"
        "title: 'X'\n"
        "schema_version: '1.1'\n"
        "doc_type: 'note'\n"
        "id: 'note-a3f9zk-x'\n"
        "description: 'A doc.'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
    new, changed, _ = format_text(src, path=None)
    keys = [ln.split(":")[0] for ln in new.splitlines() if ln and not ln.startswith("-")]
    assert keys[:4] == ["schema_version", "id", "title", "description"]
    assert changed is True


def test_unknown_key_sorts_after_known_keys():
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "custom_thing: 'x'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
    new, _, warnings = format_text(src, path=None)
    lines = [ln for ln in new.splitlines() if ":" in ln]
    assert lines.index("custom_thing: 'x'") > lines.index("related: []")
    assert any("custom_thing" in w for w in warnings)


def _doc(*, title: str = "X", extra: str = "", tags_line: str = "tags: []") -> str:
    # tags_line lets a test vary the tags entry WITHOUT appending a second `tags:`
    # (which would create a duplicate key the formatter now refuses — CR-002).
    return (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        f"title: {title}\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        f"{tags_line}\n"
        "aliases: []\n"
        "related: []\n"
        f"{extra}"
        "---\n"
    )


def test_unquoted_scalars_get_single_quoted():
    src = (
        "---\n"
        "schema_version: 1.1\n"  # identifier-like number -> '1.1'
        "id: 'note-a3f9zk-x'\n"
        "title: X\n"  # bare string -> 'X'
        "description: A doc.\n"
        "doc_type: note\n"
        "status: draft\n"
        "created: 2026-06-08\n"  # unquoted date -> '2026-06-08'
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
    )
    new, changed, _ = format_text(src, path=None)
    assert "schema_version: '1.1'" in new
    assert "title: 'X'" in new
    assert "created: '2026-06-08'" in new
    assert "doc_type: 'note'" in new
    assert changed is True


def test_null_license_stays_null():
    src = _doc(extra="license: null\n")  # helper defined below
    new, _, _ = format_text(src, path=None)
    assert "license: null" in new
    assert "license: 'null'" not in new


def test_double_quoted_becomes_single_quoted():
    src = _doc(title='"Hello"')
    new, _, _ = format_text(src, path=None)
    assert "title: 'Hello'" in new


@pytest.mark.parametrize("token", ["on", "off", "Yes", "No"])
def test_boolean_like_scalar_kept_as_string(token: str) -> None:
    # `title: on` must become `title: 'on'`, NOT 'true' (CR-NEW-001).
    src = _doc(title=token)
    new, _, _ = format_text(src, path=None)
    assert f"title: '{token}'" in new


def test_hash_in_plain_scalar_is_not_a_comment():
    # `C#` has no whitespace before '#', so it is scalar content, not a comment (CR-NEW-003).
    src = _doc(title="C# guide")
    new, _, _ = format_text(src, path=None)
    assert "title: 'C# guide'" in new


def test_url_fragment_preserved():
    src = _doc(title="http://example.com/p#frag")
    new, _, _ = format_text(src, path=None)
    assert "title: 'http://example.com/p#frag'" in new


def test_real_inline_comment_preserved_on_scalar():
    src = _doc(title="X  # keep me")  # whitespace + '#' IS a real comment
    new, _, _ = format_text(src, path=None)
    assert "title: 'X'  # keep me" in new


def test_flow_list_becomes_block_and_dedupes():
    src = _doc(tags_line="tags: ['a', 'b', 'a']")
    new, changed, _ = format_text(src, path=None)
    assert "tags:\n  - 'a'\n  - 'b'\n" in new
    assert new.count("- 'a'") == 1
    assert changed is True


def test_empty_block_list_becomes_flow_empty():
    src = _doc(tags_line="tags:")  # key with no value and no items -> tags: []
    new, _, _ = format_text(src, path=None)
    assert "tags: []" in new


def test_boolean_like_list_items_kept_as_strings():
    # list items must not be coerced (BaseLoader); [on, off, yes, no] stay strings (CR-NEW-001).
    src = _doc(tags_line="tags: [on, off, yes, no]")
    new, _, _ = format_text(src, path=None)
    assert "- 'on'" in new and "- 'off'" in new and "- 'yes'" in new and "- 'no'" in new
    assert "True" not in new and "False" not in new


def test_inline_comment_preserved_on_flow_list():
    src = _doc(tags_line="tags: [a, b]  # keep")  # CR-NEW-004
    new, _, _ = format_text(src, path=None)
    assert "tags:  # keep" in new  # comment moves to the block key line
    assert "- 'a'" in new and "- 'b'" in new


def test_inline_comment_preserved_on_empty_list():
    src = _doc(tags_line="tags: []  # keep")  # CR-NEW-004
    new, _, _ = format_text(src, path=None)
    assert "tags: []  # keep" in new


def test_hash_inside_quoted_list_item_not_a_comment():
    src = _doc(extra="source: ['Issue #123']\n")  # CR-NEW-005: '#' inside quote is literal
    new, _, _ = format_text(src, path=Path("docs/x.md"))
    assert "- 'Issue #123'" in new  # whole item preserved, '#' kept
    assert "source: []" not in new  # not emptied / mis-split


def test_real_comment_after_quoted_list_item_preserved():
    src = _doc(extra="source: ['Issue #123']  # keep\n")  # CR-NEW-005
    new, _, _ = format_text(src, path=Path("docs/x.md"))
    assert "- 'Issue #123'" in new
    assert "source:  # keep" in new


def test_type_renamed_to_doc_type_when_absent():
    src = _doc().replace("doc_type: 'note'\n", "type: 'note'\n")
    new, changed, _ = format_text(src, path=None)
    assert "doc_type: 'note'" in new
    assert "\ntype:" not in new
    assert changed is True


def test_both_type_and_doc_type_present_warns_keeps_both():
    src = _doc(extra="type: 'x'\n")
    new, _, warnings = format_text(src, path=None)
    assert "doc_type: 'note'" in new
    assert any("type" in w.lower() for w in warnings)



def test_missing_required_arrays_injected():
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "---\n"
    )
    new, changed, _ = format_text(src, path=None)
    assert "tags: []" in new and "aliases: []" in new and "related: []" in new
    assert changed is True


def test_schema_version_injected_when_missing():
    src = _doc().replace("schema_version: '1.1'\n", "")
    new, _, _ = format_text(src, path=None)
    assert "schema_version: '1.1'" in new


def test_doc_type_filled_from_readme_path_when_missing():
    src = _doc().replace("doc_type: 'note'\n", "")  # no doc_type
    new, _, _ = format_text(src, path=Path("README.md"))
    assert "doc_type: 'index'" in new


def test_doc_type_research_under_docs_research_when_invalid():
    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'bogus'\n")
    new, _, _ = format_text(src, path=Path("docs/research/x.md"))
    assert "doc_type: 'research'" in new


def test_valid_doc_type_never_overridden_by_path():
    src = _doc().replace("doc_type: 'note'\n", "doc_type: 'reference'\n")
    new, _, _ = format_text(src, path=Path("README.md"))
    assert "doc_type: 'reference'" in new  # SA-001: valid value preserved
    assert "doc_type: 'index'" not in new


def test_denylisted_paths_are_refused():
    from project_standards.format_frontmatter import is_denylisted

    assert is_denylisted(Path("CLAUDE.md"))
    assert is_denylisted(Path("sub/AGENTS.md"))
    assert is_denylisted(Path(".claude/settings.md"))
    assert is_denylisted(Path("x/.codex/y.md"))
    assert not is_denylisted(Path("docs/note.md"))


def test_extension_object_nested_bytes_preserved():
    src = (
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-a3f9zk-x'\n"
        "title: 'X'\n"
        "description: 'A doc.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-06-08'\n"
        "updated: '2026-06-08'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "project:\n"
        "  team: 'platform'\n"
        "  nested:\n"
        "    deep: 1\n"
        "---\n"
    )
    new, changed, warnings = format_text(src, path=None)
    assert "project:\n  team: 'platform'\n  nested:\n    deep: 1\n" in new
    assert changed is False
    assert warnings == []


def test_crlf_line_endings_preserved():
    src = _doc().replace("\n", "\r\n")
    src = src.replace("title: X\r\n", "title: X\r\n") if "title: X" in src else src
    # Force one change (unquoted) and assert CRLF survives on unchanged lines.
    src = src.replace("title: 'X'\r\n", "title: X\r\n")
    new, _changed, _ = format_text(src, path=None)
    assert "\r\n" in new
    assert "\n\n" not in new.replace("\r\n", "")  # no stray bare LFs introduced
    assert "title: 'X'\r\n" in new


def test_scaffold_injects_schema_valid_block():
    body = "# Real Title\n\nSome content.\n"
    new, changed, _ = format_text(
        body, path=Path("docs/guide.md"), scaffold=True, today="2026-06-08"
    )
    assert new.startswith("---\n")
    assert "title: 'Real Title'" in new
    assert "doc_type: 'note'" in new  # no path rule -> note
    assert "created: '2026-06-08'" in new and "updated: '2026-06-08'" in new
    assert "description: 'TODO:" in new  # placeholder, schema-valid
    assert "# Real Title" in new  # body preserved
    assert changed is True


def test_scaffold_disabled_leaves_body_untouched():
    body = "# Title\n\nContent.\n"
    new, changed, _ = format_text(body, path=Path("docs/guide.md"), scaffold=False)
    assert new == body and changed is False


def test_scaffold_uses_path_doc_type_rule():
    new, _, _ = format_text("# R\n", path=Path("README.md"), scaffold=True, today="2026-06-08")
    assert "doc_type: 'index'" in new


def _run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "project_standards.format_frontmatter", *args],
        capture_output=True,
        text=True,
        **kw,  # type: ignore[call-overload]
    )


def test_check_exits_1_when_would_change(tmp_path: Path) -> None:
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 1


def test_write_formats_in_place_atomically(tmp_path: Path) -> None:
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    r = _run(["--write", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 0
    assert "title: 'X'" in f.read_text()


def test_stdin_mode_round_trips() -> None:
    r = _run(["--stdin"], input=_doc(title="X").replace("title: 'X'", "title: X"))
    assert r.returncode == 0
    assert "title: 'X'" in r.stdout


def test_custom_schema_skips(tmp_path: Path) -> None:
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['*.md']\n"
    )
    r = _run(["--check", "--config", str(cfg), str(f)], cwd=tmp_path)
    assert r.returncode == 0
    assert "custom schema" in (r.stdout + r.stderr).lower()


@pytest.mark.parametrize("conflict", [["x.md"], ["--glob", "*.md"], ["--write"]])
def test_stdin_conflicts_exit_2(conflict: list[str]) -> None:
    r = _run(["--stdin", *conflict], input="---\ntitle: 'X'\n---\n")
    assert r.returncode == 2
    assert "stdin" in (r.stdout + r.stderr).lower()


CASES = [
    _doc(title="X").replace("title: 'X'", "title: X"),
    _doc(tags_line="tags: ['b','a','b']"),
    _doc().replace("schema_version: '1.1'\n", ""),
    _doc().replace("doc_type: 'note'\n", "type: 'note'\n"),
]


@pytest.mark.parametrize("src", CASES)
def test_format_is_idempotent(src: str) -> None:
    once, _, _ = format_text(src, path=Path("docs/x.md"))
    twice, changed2, _ = format_text(once, path=Path("docs/x.md"))
    assert twice == once
    assert changed2 is False


# ---------------------------------------------------------------------------
# In-process unit tests for tokenize() / _split_value_comment / _leading_run
# ---------------------------------------------------------------------------


def test_tokenize_blank_and_comment_lines_become_pending() -> None:
    # Covers lines 97-100 (blank/comment append to pending) and 126-127
    # (pending flushed as a trailing key=None Entry at end).
    body = "# top comment\n\ntitle: 'X'\n# tail\n"
    entries, reason = tokenize(body)
    assert reason is None
    # first entry should carry the leading comment and blank
    assert entries[0].key == "title"
    assert any("# top comment" in ln for ln in entries[0].lines)
    # trailing comment entry
    last = entries[-1]
    assert last.key is None
    assert any("# tail" in ln for ln in last.lines)


def test_tokenize_unrecognized_line_returns_reason() -> None:
    # Covers line 103 — a line at column 0 that doesn't match key: syntax
    # (e.g. a bare list item `- x` or a number-prefixed key)
    body = "- orphan-list-item\n"
    entries, reason = tokenize(body)
    assert entries == []
    assert reason is not None and "unrecognized" in reason


def test_tokenize_unsupported_yaml_constructs() -> None:
    # Covers line 107 — anchor, alias, block scalar
    for bad_val in ("&anchor value", "*alias", "<< merge", "| block"):
        body = f"title: {bad_val}\n"
        entries, reason = tokenize(body)
        assert entries == [], f"expected empty for {bad_val!r}"
        assert reason is not None and "unsupported" in reason, f"bad reason for {bad_val!r}"


def test_tokenize_blank_line_breaks_continuation() -> None:
    # Covers line 119 — blank line inside a nested entry ends continuation
    body = "tags:\n  - 'a'\n\ntitle: 'X'\n"
    entries, reason = tokenize(body)
    assert reason is None
    tag_entry = next(e for e in entries if e.key == "tags")
    # blank line is NOT included in the tag entry's lines (it ends it)
    assert not any(ln.strip() == "" for ln in tag_entry.lines)


def test_split_value_comment_single_quoted_with_escaped_quote() -> None:
    # Covers lines 154-155 — escaped '' inside single-quoted scalar
    val, comment = _split_value_comment(" 'it''s here'  # note")
    assert val.strip() == "'it''s here'"
    assert "# note" in comment


def test_split_value_comment_double_quoted_with_escape() -> None:
    # Covers lines 158-159 — backslash escape inside double-quoted scalar
    val, comment = _split_value_comment(' "foo\\"bar"  # cmt')
    assert val.strip().startswith('"')
    assert "# cmt" in comment


def test_split_value_comment_unterminated_single_quote() -> None:
    # Covers line 163 — unterminated quote: whole rest returned as value
    val, comment = _split_value_comment(" 'unterminated")
    assert comment == ""
    assert "unterminated" in val


def test_split_value_comment_flow_list_with_inner_double_quote() -> None:
    # Covers lines 173-174 and 177-178 — quote tracking inside flow list
    val, comment = _split_value_comment(' ["foo\\"bar", \'baz\']  # keep')
    assert val.strip().startswith("[")
    assert "]" in val
    assert "# keep" in comment


def test_split_value_comment_flow_list_inner_single_quote_double_escape() -> None:
    # Covers line 175-176 — '' escape inside single-quoted flow list item
    val, comment = _split_value_comment(" ['it''s']")
    assert val.strip() == "['it''s']"
    assert comment == ""


def test_split_value_comment_unbalanced_brackets() -> None:
    # Covers line 191 — unbalanced brackets: no comment extracted
    _val, comment = _split_value_comment(" [open but no close")
    assert comment == ""


def test_leading_run_counts_only_prefix_blanks_and_comments() -> None:
    # Covers lines 256-262 — _leading_run returns count of leading blank/comment lines
    entry = Entry(key="tags", lines=["# comment\n", "\n", "tags:\n", "  - 'a'\n"])
    assert _leading_run(entry) == 2


def test_normalize_lists_yaml_error_is_skipped() -> None:
    # Covers lines 276-277 — yaml.YAMLError during load → continue (no crash)
    # Build an entry whose lines produce invalid YAML when joined
    entry = Entry(key="tags", lines=["tags: [\n", "  broken yaml\n"])
    from project_standards.format_frontmatter import normalize_lists

    normalize_lists([entry])  # must not raise
    # lines unchanged (skipped)
    assert entry.lines[0] == "tags: [\n"


def test_normalize_lists_non_dict_load_skipped() -> None:
    # The joined entry lines parse as a YAML list, not a mapping -> `not isinstance(
    # loaded, dict)` is True and the entry is left untouched. Defensive guard: tokenize
    # only ever builds `key:` entries, so this cannot arise in production; assert it via
    # a direct Entry construction so the guard's contract is locked.
    entry = Entry(key="tags", lines=["- list-item\n"])
    from project_standards.format_frontmatter import normalize_lists

    normalize_lists([entry])
    normalize_lists([entry])
    assert entry.lines == ["- list-item\n"]  # unchanged (non-dict load skipped)


def test_normalize_lists_scalar_where_list_expected_is_left() -> None:
    # Covers line 282 — value is a scalar (not list/None/empty) -> left for validator
    entry = Entry(key="tags", lines=["tags: not-a-list\n"])
    from project_standards.format_frontmatter import normalize_lists

    normalize_lists([entry])
    assert "not-a-list" in entry.lines[0]


def test_reorder_trailing_comment_entry_stays_last() -> None:
    # Covers line 330 — trailing comment-only Entry (key=None) sort key
    from project_standards.format_frontmatter import reorder

    e_title = Entry(key="title", lines=["title: 'X'\n"])
    e_tail = Entry(key=None, lines=["# trailing\n"])
    warnings: list[str] = []
    result = reorder([e_tail, e_title], warnings)
    assert result[-1].key is None


def test_today_iso_returns_valid_date() -> None:
    # Covers line 444 — _today_iso() returns today's ISO date string
    import datetime as _dt

    result = _today_iso()
    parsed = _dt.date.fromisoformat(result)
    assert parsed == _dt.date.today()


def test_scaffold_no_path_is_noop() -> None:
    # Covers line 485 — scaffold=True but path=None -> returns text unchanged
    body = "# Title\n\nContent.\n"
    new, changed, _ = format_text(body, path=None, scaffold=True)
    assert new == body
    assert changed is False


def test_bump_updated_sets_new_date() -> None:
    # Covers lines 512-519 — bump_updated rewrites updated: when block changes
    src = _doc(title="X").replace("title: 'X'", "title: X")  # unquoted -> will change
    new, changed, _ = format_text(src, path=None, bump_updated=True, today="2099-01-01")
    assert changed is True
    assert "updated: '2099-01-01'" in new


def test_bump_updated_noop_when_already_formatted() -> None:
    # bump_updated only fires when the block actually changes; clean input -> no change
    new, changed, _ = format_text(CLEAN, path=None, bump_updated=True, today="2099-01-01")
    assert changed is False
    assert "updated: '2099-01-01'" not in new


# ---------------------------------------------------------------------------
# In-process main() tests — CLI coverage
# ---------------------------------------------------------------------------


def _cfg(tmp_path: Path, *, include: str = "['**/*.md']", extra: str = "") -> Path:
    """Write a minimal .project-standards.yml and return its path."""
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(f"markdown:\n  frontmatter:\n    include: {include}\n{extra}")
    return cfg


def test_main_check_exits_1_when_file_would_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--config", str(cfg), str(f)])
    assert rc == 1


def test_main_check_exits_0_when_already_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "clean.md"
    f.write_text(CLEAN)
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--config", str(cfg), str(f)])
    assert rc == 0


def test_main_write_rewrites_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    assert "title: 'X'" in f.read_text()


def test_main_write_preserves_file_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Exercises _atomic_write: set a non-default mode, assert it survives the rewrite
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    f.chmod(0o644)
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    mode = f.stat().st_mode & 0o777
    assert mode == 0o644


def test_main_write_preserves_executable_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A non-default mode (0o755) must survive the atomic rewrite
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    f.chmod(0o755)
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    assert (f.stat().st_mode & 0o777) == 0o755


def test_main_stdin_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    src = _doc(title="X").replace("title: 'X'", "title: X")
    monkeypatch.setattr("sys.stdin", io.StringIO(src))
    cfg = _cfg(tmp_path)
    rc = main(["--stdin", "--config", str(cfg)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "title: 'X'" in out


def test_main_stdin_with_file_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
    with pytest.raises(SystemExit) as exc:
        main(["--stdin", "x.md"])
    assert exc.value.code == 2


def test_main_stdin_with_glob_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
    with pytest.raises(SystemExit) as exc:
        main(["--stdin", "--glob", "*.md"])
    assert exc.value.code == 2


def test_main_stdin_with_write_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("---\ntitle: 'X'\n---\n"))
    with pytest.raises(SystemExit) as exc:
        main(["--stdin", "--write"])
    assert exc.value.code == 2


def test_main_custom_schema_via_config_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(
        tmp_path,
        extra="",
    )
    # Write config with a custom schema path
    cfg.write_text(
        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['**/*.md']\n"
    )
    rc = main(["--check", "--config", str(cfg), str(f)])
    assert rc == 0
    out, err = capsys.readouterr()
    assert "custom schema" in (out + err).lower()


def test_main_custom_schema_via_flag_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    # Pass a --schema flag pointing to a non-existent custom path
    rc = main(["--check", "--config", str(cfg), "--schema", "custom/x.json", str(f)])
    assert rc == 0
    out, err = capsys.readouterr()
    assert "custom schema" in (out + err).lower()


def test_main_malformed_config_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".project-standards.yml"
    # Invalid YAML: tab character at start of line where not allowed
    cfg.write_text("markdown:\n\t frontmatter: bad\n")
    rc = main(["--check", "--config", str(cfg)])
    assert rc == 2
    _out, err = capsys.readouterr()
    assert "error" in err.lower()


def test_main_denylisted_file_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # CLAUDE.md with a frontmatter block that would be changed if processed
    f = tmp_path / "CLAUDE.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    # Pass the denylist file explicitly as a positional arg
    rc = main(["--check", "--config", str(cfg), str(f)])
    # denylisted -> skipped -> no change detected -> 0
    assert rc == 0


def test_main_duplicate_key_warning_sets_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    # Frontmatter with a duplicate key: tokenize returns reason "duplicate top-level key"
    src = CLEAN.replace("tags: []\n", "tags: []\ntags: ['x']\n")
    f = tmp_path / "dup.md"
    f.write_text(src)
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--config", str(cfg), str(f)])
    _out, err = capsys.readouterr()
    assert "duplicate" in err.lower()
    # unparseable flag set -> returns 1 regardless of any_change
    assert rc == 1


def test_main_bump_updated_with_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # File with unquoted title so it will change; existing updated date in the past
    f = tmp_path / "d.md"
    old_content = _doc(title="X").replace("title: 'X'", "title: X")
    # Replace the updated date with an obviously old value
    old_content = old_content.replace("updated: '2026-06-08'", "updated: '2020-01-01'")
    f.write_text(old_content)
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--bump-updated", "--config", str(cfg), str(f)])
    assert rc == 0
    new_content = f.read_text()
    # updated: must have changed from the old placeholder
    assert "updated: '2020-01-01'" not in new_content
    assert "updated:" in new_content


def test_main_write_scaffold_on_no_frontmatter_docs_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # A .md file under docs/ with no frontmatter: --write triggers scaffold
    docs = tmp_path / "docs"
    docs.mkdir()
    f = docs / "guide.md"
    f.write_text("# Guide Title\n\nSome content.\n")
    cfg = _cfg(tmp_path, include="['docs/**/*.md']")
    rc = main(["--write", "--config", str(cfg), str(f)])
    assert rc == 0
    content = f.read_text()
    assert content.startswith("---\n")
    assert "title: 'Guide Title'" in content
    assert "doc_type: 'note'" in content


def test_main_write_quiet_suppresses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--write", "--quiet", "--config", str(cfg), str(f)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert out == ""


def test_main_check_quiet_suppresses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.md"
    f.write_text(_doc(title="X").replace("title: 'X'", "title: X"))
    cfg = _cfg(tmp_path)
    rc = main(["--check", "--quiet", "--config", str(cfg), str(f)])
    assert rc == 1
    out, _ = capsys.readouterr()
    assert out == ""


def test_malformed_double_quoted_scalar_does_not_crash() -> None:
    # An invalid double-quoted YAML escape must NOT crash the formatter (codex P3) —
    # it can't safely re-quote, so it leaves the line for the validator to reject.
    src = _doc(title='"bad \\q"')
    new, _changed, _warnings = format_text(src, path=None)
    assert 'title: "bad \\q"' in new  # line preserved, no traceback


def test_scalar_with_leading_comment_is_requoted() -> None:
    # A leading comment bundles into the key's entry; requote must still quote the
    # scalar (codex P2) rather than skip the whole entry as a multi-line value.
    src = _doc(title="X").replace("title: X", "# keep this note\ntitle: X")
    new, _changed, _warnings = format_text(src, path=None)
    assert "# keep this note" in new
    assert "title: 'X'" in new


def test_block_list_item_comment_is_preserved() -> None:
    # Re-rendering a block list would drop per-item comments (codex P2); a comment-
    # bearing list is left untouched so the authored note survives.
    src = _doc(tags_line="tags:\n  - 'a'  # why a\n  - 'b'")
    new, _changed, _warnings = format_text(src, path=None)
    assert "# why a" in new
    assert "- 'a'" in new and "- 'b'" in new

exec
/bin/bash -lc "git diff --minimal bd5d423fc9c8286f5a9634d5d85d0278de6ea788 -- CHANGELOG.md meta/versioning.md standards/markdown-frontmatter/README.md standards/markdown-frontmatter/adopt.md TODO.md | sed -n '1,260p'" in /home/chris/projects/project-standards
 succeeded in 0ms:
diff --git a/CHANGELOG.md b/CHANGELOG.md
index cd3e7a5..6b869c1 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,12 +1,12 @@
 ---
 schema_version: '1.1'
-id: log-atsd8b-changelog
+id: 'log-atsd8b-changelog'
 title: 'Changelog'
 description: 'Notable changes to the project-standards repository.'
 doc_type: 'log'
 status: 'active'
 created: '2026-06-02'
-updated: '2026-06-08'
+updated: '2026-06-09'
 reviewed: null
 owner: ''
 consumer: 'mix'
@@ -29,18 +29,24 @@ Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version
 
 ## [Unreleased]
 
+## [2.1.0] — 2026-06-09
+
 > **Note for release planning:** The reusable-workflow change below (`validate-id` now runs in CI) can fail consumers that passed under `@v2`, which classifies as **MAJOR** per `meta/versioning.md §3`. Decide the version number before cutting the release tag.
 
 ### Added
 
+- **`format-frontmatter` command** — reformats YAML frontmatter to canonical style (`--write` to rewrite in place, `--check` to report-only). Applies canonical key ordering, single-quote-wraps all string values, renames the deny-listed `type` alias to `doc_type`, renders empty arrays as `[]` and non-empty arrays in block style, and preserves the document body unchanged. Skips files under a custom schema.
+- **`validate-references` command** — opt-in cross-file checker (`markdown.frontmatter.references.enabled: true`). Enforces id uniqueness (error), referential integrity (warning — each value in `related`/`depends_on`/`supersedes`/`superseded_by` must resolve as a known document `id` or a repo-root-relative path), supersede reciprocity (warning, both directions), date ordering (error — `created` ≤ `updated`, and `reviewed` ≥ `created` when present), and ADR-number uniqueness (error — no two ADRs share the same `adr-NNNN`). Self-gates: exits 0 immediately when not enabled, so adding it to CI is a no-op until the repo opts in.
+- **`project-standards fix` subcommand** — three-phase pipeline: format frontmatter (`--write`), regenerate non-compliant ids (`--fix`), then re-run the full `validate` contract (schema + id + references) as a postcondition. Skips entirely under a custom schema (CR-001). Postcondition failure (e.g. duplicate-id reference error) surfaces as a non-zero exit even after successful write phases.
+- **`project-standards validate` also runs `validate-references`.** The combined `validate` command now invokes all three validators — `validate-frontmatter`, `validate-id`, and `validate-references` — returning the worst exit code. `validate-references` is a no-op when `references.enabled` is false, so existing repos without the opt-in are unaffected.
 - **`validate-id` command** — validates that `id` fields conform to the project-standards format. Two formats are enforced: `{doc_type}-{6-char base36 token}-{readable-slug}` for all standard doc types (e.g. `note-a3f9zk-tailscale-acl-gotcha`); `adr-{NNNN}-{repo-name}-{short-title}` for ADRs. The readable-slug is validated as well-formed kebab-case but is **not** matched against the current `title` — ids are frozen at creation time and must remain stable after a document is renamed. Files with no frontmatter, or missing/invalid `id`/`doc_type`, are silently skipped (those gaps are caught by `validate-frontmatter`). When a custom schema is in use — either via the `--schema` CLI flag or `markdown.frontmatter.schema` pointing to a file path in the config — id validation is skipped entirely (custom schemas may define different id conventions).
-- **`project-standards validate` runs both validators.** The `validate` subcommand now invokes `validate-frontmatter` and `validate-id` in sequence, returning the worst exit code. All `validate-frontmatter` flags (`--schema`, `--glob`, `--no-require-frontmatter`) are forwarded correctly; `--glob` also restricts which files `validate-id` checks so both validators always operate on the same file set.
 - **`project-standards` CLI with an `adopt <standard>...` subcommand** that materializes a chosen standard's canonical artifacts into a consumer repo (plus `list` and a back-compat `validate` subcommand). Adopting any subset — including all four standards together — is supported; runs are idempotent (skip-if-exists, `--force` to overwrite regular files only), path-safe (never writes through a symlink or outside `--dest`), and use atomic writes (a failed `--force` never truncates the original). `fragment` artifacts (the `pyproject.toml` and `.project-standards.yml` sections) are **reported for manual merge, never written**. The existing `validate-frontmatter` console script is retained as a back-compat alias.
 - **Per-standard `adopt.toml` manifests and bundled templates** under `src/project_standards/bundles/`, resolved at runtime by the same `Path(__file__)`-relative, wheel-safe lookup the bundled schema/registry already use. A generic engine reads each manifest, so adding a standard is data, not code.
+- **`.pre-commit-hooks.yaml`** — consumers can use this repo as a pre-commit source (`repo: https://github.com/L3DigitalNet/project-standards`). Six hooks: `format-frontmatter-fix`, `format-frontmatter-check`, `validate-id-fix`, `validate-id-check`, `validate-frontmatter`, and `validate-references` (whole-repo, `pass_filenames: false`).
 
 ### Changed
 
-- **BREAKING (reusable workflow): `validate-markdown-frontmatter.yml` now also runs `validate-id`.** Consumers whose managed documents carry old-style kebab ids (e.g. `restart-netbox-after-config-change`) will begin failing once they re-pin to the new release tag. Per `meta/versioning.md §3`, any stricter validator or workflow behavior that can fail a previously-passing consumer requires a **major** version bump. Consumers on a custom (non-bundled) `markdown.frontmatter.schema` are unaffected — `validate-id` skips automatically.
+- **`validate-markdown-frontmatter.yml` now also runs `validate-id` and `validate-references`.** `validate-references` is a self-gated no-op unless the calling repo enables it, so there is no breakage for repos that have not opted in. Consumers whose managed documents carry old-style kebab ids (e.g. `restart-netbox-after-config-change`) will begin failing the `validate-id` step once they re-pin to the new release tag. Per `meta/versioning.md §3`, any stricter validator or workflow behavior that can fail a previously-passing consumer requires a **major** version bump. Consumers on a custom (non-bundled) `markdown.frontmatter.schema` are unaffected — `validate-id` skips automatically.
 - **Copy-adopt scaffolds relocated** out of README/`adopt.md` prose into packaged bundles (documentation reorganization; non-breaking — consumers pin git tags and reusable-workflow filenames, not template paths). Each standard's `adopt.md` now references `project-standards adopt <id>`.
 - **Python Tooling `.editorconfig` JSON/Markdown indentation reconciled** to the shared superset floor (global `indent_style = tab`; `[*.py]`/`[*.toml]` 4 spaces; YAML 2 spaces). A clarifying change to a copy-adopt standard — copy-adopt standards are never inherited automatically, so it cannot newly-fail an existing consumer.
 
diff --git a/TODO.md b/TODO.md
index 0d8eea0..fb7597c 100644
--- a/TODO.md
+++ b/TODO.md
@@ -18,7 +18,7 @@ This document is the user's visible task list alongside the v3 handoff system. U
 
 ## Repo & Agent Tracked Tasks
 
-- [ ] **Implement the frontmatter suite** — plan `docs/superpowers/plans/2026-06-08-frontmatter-suite.md` (codex spec ×3 + plan ×4, converged; ~26 TDD tasks, Phase 0→A→B→C). Builds `format-frontmatter` (autoformatter), `validate-references` (opt-in semantics), `project-standards fix`, and `.pre-commit-hooks.yaml`. Execute subagent-driven; toolchain gate after each phase.
-- [ ] **Decide the Task 0.5 invariant question** (before/at implementation). The plan rejects duplicate top-level keys in `parse_frontmatter` — a documented narrow exception to "no consumer newly-fails". Confirm that exception, or scope duplicate-key detection to the formatter only (the tokenizer already refuses them).
-- [ ] **Cut the `2.1.0` release — HELD (E3).** `2.1.0` bundles the adopt CLI + `validate-id` (both implemented + green on `testing`, 299 tests / 91% / gate green) **and** the frontmatter suite (above, not yet built). Run E3 only after the suite is implemented and the full gate is green: version bump + `uv.lock` + dated changelog in one commit, signed tag `v2.1.0`, move `v2`, update `deployed.md`. Resume only on explicit user go.
-- [ ] **Green the prettier/`format.yml` CI gate.** `npx prettier --check .` is latently red on `docs/codex-reviews/**` (13 regenerated transcripts) + `src/project_standards/bundles/*` (5 shipped scaffolds with intentional placeholders); there is no `.prettierignore`. Recommended fix: add a `.prettierignore` mirroring the `.markdownlint-cli2.jsonc` `ignores` (`codex-reviews`, `handoff`), then decide whether to prettier-format the bundle scaffolds or ignore them too. (markdownlint's counterpart was scoped + greened 2026-06-09, commit `ec2b517`.)
+- [x] **Implement the frontmatter suite** — DONE 2026-06-09 on `testing` (Phases 0→A→B→C, subagent-driven, two-stage review + gate per phase). Ships `format-frontmatter`, `validate-references` (opt-in), `project-standards fix`, `validate` also runs references, `.pre-commit-hooks.yaml`. 423 tests, 92% cov, basedpyright 0/0/0, ruff clean, pip-audit clean; dogfood `format-frontmatter --check` + `project-standards validate`/`fix` clean on the repo.
+- [x] **Decide the Task 0.5 invariant question** — RESOLVED 2026-06-09 (user-confirmed): `parse_frontmatter` rejects duplicate top-level keys (`validate`/`fix` + consumer CI now error on them). Documented as a contract-strictness bump in CHANGELOG 2.1.0.
+- [ ] **Cut the `2.1.0` release — HELD (E3).** The full 2.1.0 payload (adopt CLI + validate-id + frontmatter suite) is now **implemented and green on `testing`**. Run E3 only on explicit user go: decide the version number first (`validate-id`-in-CI may be MAJOR per `meta/versioning.md §3`), then version bump + `uv.lock` + dated changelog in one commit, signed tag `v2.1.0`, move `v2`, update `deployed.md`.
+- [x] **Green the prettier/`format.yml` CI gate** — DONE 2026-06-09 (`281afe4`). Real failures were 13 `docs/codex-reviews/**` transcripts + 2 authored docs (`src/project_standards/README.md`, `standards/markdown-frontmatter/adopt.md`) — NOT the bundle scaffolds the earlier note guessed. Added `.prettierignore` (codex-reviews, handoff) + prettier-formatted the 2 authored docs; `prettier --check .` clean; format-frontmatter + markdownlint stay green.
diff --git a/meta/versioning.md b/meta/versioning.md
index 574ae10..47319b0 100644
--- a/meta/versioning.md
+++ b/meta/versioning.md
@@ -1,6 +1,6 @@
 ---
 schema_version: '1.1'
-id: reference-cirycm-versioning-standard
+id: 'reference-cirycm-versioning-standard'
 title: 'Versioning Standard'
 description: 'How releases of this repository are numbered, tagged, and consumed — a consumer-outcome contract over the standard, schema, validator, and workflow.'
 doc_type: 'reference'
diff --git a/standards/markdown-frontmatter/README.md b/standards/markdown-frontmatter/README.md
index 11d11b4..499472f 100644
--- a/standards/markdown-frontmatter/README.md
+++ b/standards/markdown-frontmatter/README.md
@@ -1,6 +1,6 @@
 ---
 schema_version: '1.1'
-id: reference-ove1rr-markdown-frontmatter-standard
+id: 'reference-ove1rr-markdown-frontmatter-standard'
 title: 'Markdown Frontmatter Standard'
 description: 'Canonical, tool-neutral metadata profile for project Markdown documents.'
 doc_type: 'reference'
@@ -58,6 +58,7 @@ license: null
   - [Extensions](#extensions)
   - [Versioning and compatibility](#versioning-and-compatibility)
   - [Validation](#validation)
+    - [Cross-file reference validation (opt-in)](#cross-file-reference-validation-opt-in)
   - [Valid frontmatter template](#valid-frontmatter-template)
 
 ## Purpose
@@ -455,9 +456,31 @@ How a schema change maps to a release level (additive → minor; a field or cont
 
 Frontmatter is validated by [`src/project_standards/validate_frontmatter.py`](../../src/project_standards/validate_frontmatter.py) — installed as the `validate-frontmatter` command — against [`src/project_standards/schemas/markdown-frontmatter.schema.json`](../../src/project_standards/schemas/markdown-frontmatter.schema.json), in CI and locally.
 
-- **Run locally (full check):** `uv run project-standards validate --config .project-standards.yml` — runs both the schema validator (`validate-frontmatter`) and the id-format validator (`validate-id`) in one command. To run either standalone: `uv run validate-frontmatter …` or `uv run validate-id …`. Run `validate-frontmatter --help` / `validate-id --help` for the full flag lists.
+- **Run locally (full check):** `uv run project-standards validate --config .project-standards.yml` — runs the schema validator (`validate-frontmatter`), the id-format validator (`validate-id`), and the cross-file reference validator (`validate-references`) in one command. To run any standalone: `uv run validate-frontmatter …`, `uv run validate-id …`, or `uv run validate-references …`. Run `validate-frontmatter --help` / `validate-id --help` / `validate-references --help` for the full flag lists.
+- **Auto-fix and re-validate:** `uv run project-standards fix --config .project-standards.yml` — formats frontmatter (applies transforms, re-quotes, reorders keys), regenerates non-compliant ids, then re-runs the full `validate` contract. Skips entirely under a custom schema. Run this when adopting the standard on an existing codebase to reduce manual fixups.
 - **Exit codes:** `0` — all matched files valid (or none matched); `1` — one or more documents failed validation (each error, then a summary count, prints to stderr); `2` — configuration or schema error: a missing or invalid config or schema, an unknown standard version label (`markdown.frontmatter.version`, `markdown.adr.version`, `python_tooling.version`, or `markdown_tooling.version`), or an incompatible configured `frontmatter`↔`adr` version pair.
 
+### Cross-file reference validation (opt-in)
+
+`validate-references` is **disabled by default** and must be opted in per-repo via `.project-standards.yml`:
+
+```yaml
+markdown:
+  frontmatter:
+    references:
+      enabled: true
+```
+
+When enabled, it checks:
+
+- **`id` uniqueness** — no two managed documents share the same `id` value.
+- **Referential integrity** — every value in `related`, `depends_on`, `supersedes`, and `superseded_by` resolves, either as a known document `id` or as a file at that repo-root-relative path.
+- **Supersede reciprocity** — when document A lists B in `supersedes`, B must list A in `superseded_by`, and vice versa.
+- **Date ordering** — `created` ≤ `updated`.
+- **ADR sequence** — no two ADRs share the same `adr-NNNN` number.
+
+`validate-references` is a repo-wide pass. It self-gates on `references_enabled`, so adding it to CI is a no-op until the repo opts in: `project-standards validate` always invokes it, but it exits 0 immediately when not enabled.
+
 Configuration (`.project-standards.yml`), the reusable CI workflow, and how consuming repositories pin a release tag are documented in [the adoption guide](adopt.md); they are not repeated here.
 
 ## Valid frontmatter template
diff --git a/standards/markdown-frontmatter/adopt.md b/standards/markdown-frontmatter/adopt.md
index 1abd483..81eaf4a 100644
--- a/standards/markdown-frontmatter/adopt.md
+++ b/standards/markdown-frontmatter/adopt.md
@@ -1,6 +1,6 @@
 ---
 schema_version: '1.1'
-id: runbook-s87fvu-standards-adoption-compliance-procedure
+id: 'runbook-s87fvu-standards-adoption-compliance-procedure'
 title: 'Standards Adoption & Compliance Procedure'
 description: 'Step-by-step procedure for an agent to adopt the project-standards Markdown Frontmatter Standard in a consuming repository and bring it into compliance.'
 doc_type: 'runbook'
@@ -85,6 +85,8 @@ markdown:
       # Tooling / generated content you do not want validated:
       - '.obsidian/**'
       - 'node_modules/**'
+    references:
+      enabled: false # Set to true to enable cross-file checks (id uniqueness, referential integrity, etc.)
 ```
 
 **Selecting a contract version (optional).** `markdown.frontmatter.version` pins which bundled Frontmatter contract validates your documents; omit it to use the tool's current default (today `1.1`, which also accepts legacy `schema_version: '1.0'` documents). A custom `schema:` path owns its own versioning — setting both a custom `schema:` path and `version` is a config error.
@@ -267,11 +269,15 @@ project:
 Run the released validator directly — no checkout required:
 
 ```bash
-uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v1' \
-  validate-frontmatter --config .project-standards.yml
+uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v2' \
+  project-standards validate --config .project-standards.yml
 ```
 
-**Exit codes:** `0` = all matched files valid (or none matched); `1` = one or more documents failed (each error then a summary prints to stderr); `2` = configuration or schema error (config/schema missing or invalid). Useful flags: `--glob PATTERN` to add files, positional `FILE` args to check specific files, `--quiet` to suppress success output, `--no-require-frontmatter` to not fail files lacking a block. Run `validate-frontmatter --help` for the full list.
+This runs all three validators — schema (`validate-frontmatter`), id format (`validate-id`), and cross-file references (`validate-references`, no-op unless `references.enabled: true`) — in a single pass.
+
+**Auto-fix mode:** run `project-standards fix` (same flags) to format frontmatter, regenerate non-compliant ids, and then re-validate. This reduces the manual fixup burden when adopting the standard on an existing codebase. Skips entirely under a custom schema.
+
+**Exit codes:** `0` = all matched files valid (or none matched); `1` = one or more documents failed (each error then a summary prints to stderr); `2` = configuration or schema error (config/schema missing or invalid). Useful flags: `--glob PATTERN` to add files, positional `FILE` args to check specific files, `--quiet` to suppress success output, `--no-require-frontmatter` to not fail files lacking a block.
 
 Compliance is reached when this exits `0`.
 
@@ -282,7 +288,7 @@ Compliance is reached when this exits `0`.
 - [ ] Every managed Markdown file has a conformant frontmatter block (required fields present, controlled values valid, strings/dates quoted, no unknown top-level keys, canonical key order).
 - [ ] No agent-instruction file (`CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`) carries frontmatter, and all are excluded.
 - [ ] Links in frontmatter use repo-root-relative paths (convention).
-- [ ] `validate-frontmatter --config .project-standards.yml` exits `0` locally.
+- [ ] `project-standards validate --config .project-standards.yml` exits `0` locally.
 - [ ] CI runs the workflow on PRs and `main`.
 
 ## 7. Versioning & staying in compliance

exec
/bin/bash -lc 'UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright' in /home/chris/projects/project-standards
 exited 1 in 1496ms:
/home/chris/projects/project-standards/src/project_standards/format_frontmatter.py
  /home/chris/projects/project-standards/src/project_standards/format_frontmatter.py:22:8 - warning: Import "yaml" could not be resolved from source (reportMissingModuleSource)
/home/chris/projects/project-standards/src/project_standards/sync_vscode_colors.py
  /home/chris/projects/project-standards/src/project_standards/sync_vscode_colors.py:25:8 - warning: Import "yaml" could not be resolved from source (reportMissingModuleSource)
/home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py
  /home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:33:8 - warning: Import "yaml" could not be resolved from source (reportMissingModuleSource)
  /home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:34:6 - warning: Import "jsonschema" could not be resolved from source (reportMissingModuleSource)
  /home/chris/projects/project-standards/src/project_standards/validate_frontmatter.py:35:6 - warning: Import "jsonschema.exceptions" could not be resolved from source (reportMissingModuleSource)
/home/chris/projects/project-standards/tests/test_adopt_cli.py
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:17:8 - error: Import "pytest" could not be resolved (reportMissingImports)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:23:42 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:23:50 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:25:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:25:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:25:11 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:31:27 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:31:35 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:33:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:33:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:33:11 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:35:23 - error: Argument type is unknown
    Argument corresponds to parameter "s" in function "loads" (reportUnknownArgumentType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:45:5 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:45:18 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:45:38 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:45:46 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:54:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:57:34 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:57:34 - error: Type of "err" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:82:41 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:82:49 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:85:34 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:85:34 - error: Type of "err" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:88:46 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:88:54 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:90:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:90:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:90:11 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:96:46 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:96:59 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:112:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:113:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:120:48 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:120:61 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:134:9 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:135:9 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:140:5 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:140:18 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:152:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:159:5 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:159:18 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:177:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:183:53 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:183:66 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:197:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:198:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:204:52 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:204:65 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:218:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:219:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:258:21 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:258:29 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:261:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:261:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:261:11 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:267:21 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:267:29 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:272:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:272:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:272:11 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:277:49 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:277:57 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:279:5 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:281:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:281:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:281:11 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:286:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:286:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:286:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:286:62 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:302:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:304:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:304:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_adopt_cli.py:304:11 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:660:57 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:662:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:674:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:677:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:688:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:688:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:690:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:696:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:700:68 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:701:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:702:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:703:10 - error: Type of "raises" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:703:39 - error: Type of "exc" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:705:12 - error: Type of "code" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:709:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:710:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:711:39 - error: Type of "exc" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_format_frontmatter.py:713:12 - error: Type of "code" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1286:5 - error: Type of "out" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1286:11 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1288:12 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1290:38 - error: Type of "err" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1294:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1294:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1294:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1294:62 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1296:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1300:50 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1300:50 - error: Type of "err" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_frontmatter.py:1316:10 - error: Type of "raises" is unknown (reportUnknownMemberType)
/home/chris/projects/project-standards/tests/test_validate_id.py
  /home/chris/projects/project-standards/tests/test_validate_id.py:18:8 - error: Import "pytest" could not be resolved (reportMissingImports)
  /home/chris/projects/project-standards/tests/test_validate_id.py:382:53 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:382:66 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:384:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:388:54 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:388:67 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:390:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:395:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:395:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:395:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:395:62 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:398:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:401:5 - error: Type of "captured" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:401:16 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:402:12 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:405:52 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:405:65 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:408:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:413:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:413:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:417:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:419:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:424:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:424:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:431:5 - error: Type of "setattr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:432:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:436:60 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:436:73 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:440:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:453:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:453:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:453:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:453:62 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:455:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:460:12 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:460:12 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:464:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:464:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:469:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:655:49 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:655:62 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:656:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:674:49 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:674:62 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:676:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:688:60 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:688:73 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_id.py:689:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
/home/chris/projects/project-standards/tests/test_validate_references.py
  /home/chris/projects/project-standards/tests/test_validate_references.py:5:8 - error: Import "pytest" could not be resolved (reportMissingImports)
  /home/chris/projects/project-standards/tests/test_validate_references.py:318:50 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:318:63 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:321:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:328:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:328:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:328:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:328:62 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:348:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:353:5 - error: Type of "captured" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:353:16 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:354:31 - error: Type of "err" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:358:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:358:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:358:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:358:62 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:364:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:369:5 - error: Type of "captured" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:369:16 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:370:31 - error: Type of "out" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:373:54 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:373:67 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:376:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:383:21 - error: Type of parameter "monkeypatch" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:383:34 - error: Type of "MonkeyPatch" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:383:54 - error: Type of parameter "capsys" is unknown (reportUnknownParameterType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:383:62 - error: Type of "CaptureFixture" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:396:5 - error: Type of "chdir" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:401:5 - error: Type of "captured" is unknown (reportUnknownVariableType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:401:16 - error: Type of "readouterr" is unknown (reportUnknownMemberType)
  /home/chris/projects/project-standards/tests/test_validate_references.py:402:34 - error: Type of "out" is unknown (reportUnknownMemberType)
476 errors, 9 warnings, 0 notes

exec
/bin/bash -lc 'UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .' in /home/chris/projects/project-standards
 succeeded in 0ms:
All checks passed!

exec
/bin/bash -lc 'UV_CACHE_DIR=/tmp/uv-cache uv run project-standards validate --config .project-standards.yml' in /home/chris/projects/project-standards
 succeeded in 140ms:
✓  15 file(s) validated
✓  15 file(s) validated

exec
/bin/bash -lc "UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY'
from pathlib import Path
from project_standards.format_frontmatter import format_text
src='''---\\nschema_version: '1.1'\\nid: 'reference-a3f9zk-x'\\ntitle: 'X'\\ndescription: 'A doc.'\\ndoc_type: 'reference'  # keep as reference\\nstatus: 'draft'\\ncreated: '2026-06-08'\\nupdated: '2026-06-08'\\ntags: []\\naliases: []\\nrelated: []\\n---\\n'''
new,changed,w=format_text(src,path=Path('README.md'))
print(new)
print(changed,w)
PY" in /home/chris/projects/project-standards
 succeeded in 0ms:
---
schema_version: '1.1'
id: 'reference-a3f9zk-x'
title: 'X'
description: 'A doc.'
doc_type: 'index'
status: 'draft'
created: '2026-06-08'
updated: '2026-06-08'
tags: []
aliases: []
related: []
---

True []

exec
/bin/bash -lc "nl -ba src/project_standards/format_frontmatter.py | sed -n '370,410p'" in /home/chris/projects/project-standards
 succeeded in 0ms:
   370	    ends with a newline so the following entry starts on a new line.  If the entry
   371	    stays last, we leave it unchanged to preserve byte-identity on round-trips."""
   372	    parts: list[str] = []
   373	    for i, entry in enumerate(entries):
   374	        is_last = i == len(entries) - 1
   375	        for j, line in enumerate(entry.lines):
   376	            is_last_line = j == len(entry.lines) - 1
   377	            if is_last_line and not is_last and line and not line.endswith(("\n", "\r\n")):
   378	                parts.append(line + "\n")
   379	            else:
   380	                parts.append(line)
   381	    return "".join(parts)
   382	
   383	
   384	BUNDLED_SCHEMA_VERSION = "1.1"  # matches registry frontmatter_default; see Task A9 note
   385	REQUIRED_ARRAYS = ("tags", "aliases", "related")
   386	
   387	
   388	def _keys(entries: list[Entry]) -> set[str]:
   389	    return {e.key for e in entries if e.key is not None}
   390	
   391	
   392	def rename_type(entries: list[Entry], warnings: list[str]) -> None:
   393	    present = _keys(entries)
   394	    if "doc_type" in present:
   395	        if "type" in present:
   396	            warnings.append("both 'type' and 'doc_type' present; kept 'doc_type', left 'type'")
   397	        return
   398	    for entry in entries:
   399	        if entry.key == "type":
   400	            entry.key = "doc_type"
   401	            entry.lines = [re.sub(r"\btype:", "doc_type:", ln, count=1) for ln in entry.lines]
   402	            return
   403	
   404	
   405	def _new_scalar_entry(key: str, value: str, eol: str) -> Entry:
   406	    return Entry(key=key, lines=[f"{key}: {_emit_single_quoted(value)}{eol}"])
   407	
   408	
   409	def _new_empty_list_entry(key: str, eol: str) -> Entry:
   410	    return Entry(key=key, lines=[f"{key}: []{eol}"])

exec
/bin/bash -lc "nl -ba src/project_standards/format_frontmatter.py | sed -n '430,465p'" in /home/chris/projects/project-standards
 succeeded in 0ms:
   430	    and scaffold, independent of config — defense-in-depth over consumer exclude."""
   431	    if path.name in _NEVER_NAMES:
   432	        return True
   433	    return any(part in _NEVER_DIRS for part in path.parts)
   434	
   435	
   436	def _infer_doc_type(path: Path) -> str | None:
   437	    """The standard's path rules. None = no rule applies."""
   438	    posix = path.as_posix()
   439	    if "docs/research/" in posix or posix.startswith("docs/research/"):
   440	        return "research"
   441	    if path.name in ("README.md", "index.md"):
   442	        return "index"
   443	    return None
   444	
   445	
   446	def infer_doc_type(entries: list[Entry], path: Path | None) -> None:
   447	    """Fill/correct-only (SA-001): set doc_type from the path rule ONLY when the
   448	    current value is missing or not a valid enum value. A valid value is kept."""
   449	    if path is None:
   450	        return
   451	    inferred = _infer_doc_type(path)
   452	    if inferred is None:
   453	        return
   454	    eol = _line_ending(entries[0].lines[-1]) if entries and entries[0].lines else "\n"
   455	    for entry in entries:
   456	        if entry.key == "doc_type":
   457	            current = entry.lines[-1].split(":", 1)[1].strip().strip("'\"")
   458	            if current in VALID_DOC_TYPES:
   459	                return  # valid -> never override
   460	            entry.lines = [f"doc_type: {_emit_single_quoted(inferred)}{eol}"]
   461	            return
   462	    entries.append(_new_scalar_entry("doc_type", inferred, eol))
   463	
   464	
   465	_H1_RE = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)

exec
/bin/bash -lc 'cat .prettierignore' in /home/chris/projects/project-standards
 succeeded in 0ms:
# Prettier ignore — mirrors the `ignores` in .markdownlint-cli2.jsonc.
#
# These paths are machine-generated transcripts or v3 handoff session state, not
# authored prose held to the formatter's bar — the same boundary
# .project-standards.yml draws for frontmatter validation (it excludes
# docs/handoff/**). Formatting them is churn, not quality, and would keep the
# Format CI gate permanently red on content no human wrote to a style.
#
# Authored design docs under docs/superpowers/{specs,plans} are deliberately NOT
# ignored — they stay gated, same as markdownlint. Prettier already honors
# .gitignore, so .venv/ and caches need no entry here.
docs/codex-reviews/
docs/handoff/

exec
/bin/bash -lc 'rg "infer_doc_type|doc_type|inline comment|schema" docs/superpowers -n | head -100' in /home/chris/projects/project-standards
 succeeded in 0ms:
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:19:    - [What the schema actually enforces (the "must pass" rules)](#what-the-schema-actually-enforces-the-must-pass-rules)
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:99:| **A. Frontmatter validation** | The YAML metadata block: required keys, enums, date/id patterns, `additionalProperties:false` | Python (`jsonschema` + `pyyaml`) | ✅ Yes — CI + local |
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:115:| `jsonschema` | `>=4.23.0` | `Draft202012Validator` — validates the parsed mapping |
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:125:| `schemas/markdown-frontmatter.schema.json` | The contract (JSON Schema Draft 2020-12) |
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:126:| `.project-standards.yml` | Declares `schema`, `required`, `include`, `exclude` globs |
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:135:- **Schema resolution order:** `--schema` path > config `markdown.frontmatter.schema` (bundled name or path) > bundled `markdown-frontmatter`.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:137:- **Exit codes:** `0` ok / none matched · `1` validation failure · `2` config/schema error.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:138:- **Date coercion:** unquoted YAML dates parse to `datetime.date`; `_coerce_dates` converts to ISO strings before schema check, so authors can write quoted or unquoted dates.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:140:### What the schema actually enforces (the "must pass" rules)
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:142:- **11 required keys:** `schema_version, id, title, description, doc_type, status, created, updated, tags, aliases, related`.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:144:- Enums: `schema_version ∈ {1.0, 1.1}`, `doc_type` (14 values incl. `adr`), `status` (7 values), `consumer`, `confidence`, `visibility`.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:158:> **Decision seed:** several "rules" in the standard (key order, quoting, list style) are exactly what a YAML/Markdown _formatter_ would normalize. If we want them enforced rather than merely documented, that's a Stack-B (or new) tool, not the schema.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:215:- `examples/adr.example.md` — a fully-worked, schema-valid ADR.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:246:| C2 **Metadata model** | canonical YAML frontmatter (`doc_type`, mapped `status` enum, `project.*` roles) | MADR-native inline/`2.1.2` metadata (`status:`, `date:`, `deciders`) | Extension's webview round-trip won't understand our frontmatter; may flag/garble on edit. |
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:316:- 🟡 **Owned code + edge cases.** "All strings quoted" via node styles must special-case values YAML parses as non-strings (unquoted dates → `date` objects; `schema_version: 1.1` unquoted → float). The validator already coerces dates; a style pass needs to flag _unquoted_ identifier- like scalars specifically. More tests we own vs. delegating to a maintained linter.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:317:- 🟢 **"Do nothing" is legitimate.** The standard already labels these "authoring rules," not machine-enforced. Keeping them as convention is a valid choice (less churn, the schema stays the sole gate).
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:323:- **Chosen (you, 2026-06-04):** key order, quoting, list style stay **authoring conventions** in `standards/markdown-frontmatter.md`. The **schema remains the sole CI gate.** No new lint pass, no new dependency.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:324:- **Rejected:** (a) opt-in validator lint pass and (b) yamllint-for-quoting — to avoid added owned-code/test surface, sidestep the major-bump/opt-in-flag complexity, and keep the validator's remit strictly _schema validity_, not style.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:341:- **(a) Editor + review (status quo, recommended).** Stack A stays a _frontmatter_ validator; markdownlint-cli2 (DEC-3) handles style; ADR section presence is caught by the editor extension's diagnostics + PR review. Consistent with DEC-4's lightweight lean (schema is the sole semantic gate; don't grow the validator's remit).
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:342:- **(b) Minimal opt-in validator check.** Default-off flag; for `doc_type: adr` only, assert the **3 truly-required** MADR sections exist (`## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`). Respects MADR's optional-sections philosophy; default-off keeps it a minor bump. More owned code + tests.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:345:**Counter-case to (a):** without a CI gate, a malformed ADR (e.g., missing Decision Outcome) can merge. Mitigations: the schema already pins `doc_type: adr`; the standard documents the required sections; the editor extension + reviewers catch structure. If structural drift becomes real, (b) is the ready escalation — same default-off pattern as DEC-4.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:351:- **Chosen (you, 2026-06-04):** extend the validator with a **default-off** check that — for `doc_type: adr` only — asserts the **3 MADR-required `##` sections** are present: `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:356:- **Implementation notes (future — not built this session):** new config namespace (body-level, not frontmatter), e.g. `markdown.adr.require_sections: true` (default `false`); scan headings when `doc_type == adr` and flag on; emit per-missing-section errors; add tests + CHANGELOG + `standards/adr.md` note. Keep it under a _separate_ config key from `markdown.frontmatter.*` so the validator's frontmatter remit stays conceptually distinct.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:367:> - Still no schema/validator change (id pattern already admits the longer form; filename never machine-checked). Still additive → MINOR.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:394:- **Versioning:** new reusable workflow = additive → minor; it joins the versioned shipped surface (standard + schema + validator + workflow**s**).
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:407:- **Rejected — Prettier as a frontmatter-semantics enforcer (already settled in DEC-4/D2):** Prettier reorders nothing and cannot enforce key order / quoting / list style, so it is **not** the frontmatter gate. Its remit here is body + whitespace formatting only; the schema remains the sole frontmatter gate.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:409:- **Quote tiebreaker:** `*.md singleQuote: true` makes single quotes the canonical frontmatter quote style; the standard allows either and the validator is quote-agnostic, so this is a formatting convention, not a schema rule.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:410:- **Versioning:** Prettier is dev tooling, not part of the versioned consumer contract — `.prettierrc.json` changes cannot fail a previously-passing consumer (consumers don't run our Prettier). Out of the standard/schema/validator/workflows versioning surface.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:421:- Schema `id` pattern `^[a-z0-9][a-z0-9._-]*$` accepts **both** `0001-…` and `adr-0001-…`. No schema change needed for either choice.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:450:- Python ≥3.11; `uv` (runner); `jsonschema>=4.23.0`; `pyyaml>=6.0.2`.
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:467:- Project sources of truth: `standards/adr.md`, `standards/markdown-frontmatter.md`, `schemas/markdown-frontmatter.schema.json`, `.project-standards.yml`, `.markdownlint.json`
docs/superpowers/specs/2026-06-04-linting-formatting-stack.md:495:- ✅ **DONE (2026-06-05) — DEC-5:** validator gained the default-off `markdown.adr.require_sections` check (pure helper `missing_adr_sections` + `doc_type: adr` gate in `validate_file` + `ProjectConfig.require_adr_sections`), built TDD with 17 new tests (87 total green). Reconciled `standards/adr.md` (Consequences required→optional, matching MADR 4.0 + templates) + added the opt-in note; enabled it in this repo's `.project-standards.yml` to dogfood (verified it fires on a broken example). CHANGELOG updated.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:34:1. **No general autoformatter.** Everything the schema checks but cannot fix — key order (JSON Schema structurally cannot enforce object key order), quoting, list style, missing required arrays, `type`→`doc_type` — is left for a human to fix by hand. Hand-fixing is exactly what drifts.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:40:- **B — `validate-references`**: the semantic checks the schema cannot express.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:51:5. **`doc_type` inference is fill/correct-only and ID-safe** — apply the standard's path rules (`README.md`/`index.md` → `index`; under `docs/research/` → `research`) **only when `doc_type` is missing or not a valid enum value**, and when scaffolding a new block. A valid explicit `doc_type` is **never** overridden. (Reversed from the round-0 "override even valid" rule: overriding a valid `doc_type` while the formatter leaves `id` untouched would create an `id`/`doc_type` mismatch that `validate-id` rejects — this repo's `standards/*/README.md` are validly `doc_type: 'reference'` with `reference-…` ids. See codex SA-001.)
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:55:9. **`schema_version` is injected only when missing** (= the bundled contract version); an existing value is never changed (a version change is a contract migration, not formatting).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:56:10. **Unknown top-level keys are warn-only**, never auto-deleted (the formatter cannot know the author's intent; the schema's `additionalProperties:false` already errors on them).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:60:14. **C:** `project-standards fix` = `format-frontmatter --write` **first** (normalizes `type`→`doc_type` and fills missing `doc_type`), **then** `validate-id --fix` (id now derivable from a valid `doc_type`), **then a final `project-standards validate`** that fails if any id/schema check still fails — proving the fix postcondition (codex SA-002). `project-standards validate` is extended to also run `validate-references` (self-gates on config), **and the reusable consumer workflow runs it too** (codex SA-003). `format-frontmatter` gains `--stdin`. A root `.pre-commit-hooks.yaml` ships **both** a mutating and a check-only hook id per tool. `format-frontmatter`/`fix` **skip when a custom schema is configured**, mirroring `validate-id` (codex SA-008).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:66:- The bundled schema path (`src/project_standards/schemas/markdown-frontmatter.schema.json`, its own `$id`) and the bundled `registry.json` + `Registry` reader.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:75:format-frontmatter [FILE ...] [--config PATH] [--schema PATH] [--glob PATTERN]
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:81:- **Flag compatibility:** accepts the same flag set as `validate-frontmatter`/`validate-id` — `--config`, `--schema`, `--glob`, `--no-require-frontmatter` (compat no-op; the formatter already skips no-frontmatter files unless scaffolding), `--quiet` — so `project-standards fix`/`validate` can forward their full argv unchanged without argparse errors (codex SA-008, SA-NEW-001).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:84:- **`--stdin`**: read one document from stdin, emit the formatted document to stdout, exit 0 (1 if unparseable). Mutually exclusive with `FILE`/`--glob`/`--write`. Path-dependent transforms are **disabled** in stdin mode: no path means no `doc_type` path-inference, no scaffolding, and the denylist cannot apply — stdin formats an **existing** block only and emits no-frontmatter input unchanged.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:85:- **Custom schema:** when `markdown.frontmatter.schema` is a custom path (or `--schema` is passed), `format-frontmatter` **skips with a note and exits 0** — the canonical-order, `schema_version`, and `doc_type` transforms assume the bundled contract, and a consumer-owned schema may define different conventions. Mirrors `validate-id`'s existing custom-schema skip (codex SA-008).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:92:1. **Key rename** `type:` → `doc_type:` — only when `doc_type` is absent; if both are present, warn and leave both (don't clobber).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:93:2. **`doc_type` path inference** (Decision 5) — **fill/correct only**: apply `README.md`/`index.md` → `index` and `docs/research/**` → `research` **only when `doc_type` is missing or not a valid enum value**. A valid value is left untouched, so the formatter never creates an `id`/`doc_type` mismatch without touching `id`.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:94:3. **Inject `schema_version`** if missing (= bundled contract version from config/registry); never change an existing value.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:96:5. **Quote normalization** — single-quote every scalar string, including dates and identifier-like numbers (`schema_version: '1.1'`).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:98:7. **Canonical key reorder** to the 25-key order (`schema_version, id, title, description, doc_type, status, created, updated, reviewed, owner, consumer, tags, aliases, related, supersedes, superseded_by, depends_on, applies_to, source, confidence, visibility, license, publish, project, x_project`); unknown keys (warn-only) are preserved after the known keys in original relative order.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:103:The block is tokenized into **entries**, one per top-level key, each owning its source line(s): the key line (with any inline comment), plus **all following more-indented continuation lines** — whether a block list **or a nested mapping** (`publish`/`project`/`x_project` extension objects). A run of leading comment/blank lines attaches to the **following** key entry, so reordering moves a key's comment banner with it. Entries are re-emitted in canonical order, each contributing its source line(s) with **original per-line endings preserved**, exactly as `validate_id.py:333-349` does. For an extension object the top-level key is repositioned but its **nested content is preserved byte-for-byte** (no re-quoting inside the block), so the sanctioned `project:`/`publish:`/`x_project:` mappings in shipped examples format cleanly (codex SA-004); only top-level scalar values are re-quoted. The document body after the closing `---` is copied byte-for-byte. `--write` is **atomic** — the formatter writes a temp file and `os.replace`s it over the original, so an interrupted run never truncates a document.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:111:For an included, non-denylisted file with **no** frontmatter block, fabricate a block that **passes the schema** yet is visibly incomplete:
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:113:- `schema_version` = bundled contract version.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:114:- `id` = `{doc_type}-{base36(6)}-{slug}`, reusing `validate_id`'s token generator and `slugify` (extracted to a shared helper to avoid coupling). `doc_type` from the path rule else `note`; `slug` from the first `# H1` title if present, else the filename stem.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:116:- `description` = a non-empty placeholder (`'TODO: one-sentence description.'`) — schema-valid but flagged for the author to replace.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:117:- `doc_type` = path rule else `note`; `status` = `draft`.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:121:Scaffold gets the file ~90% of the way. Because the `TODO:` placeholder is schema-valid (the schema only requires a non-empty `description`; the standard's stricter description rules are documented conventions, not machine-enforced — codex SA-006), `--write` **reports every scaffolded file distinctly** (`scaffolded: <path> — fill in title/description`) rather than implying completeness. Scaffolded blocks are deliberate _starting points_, not finished documents; the distinct report is the author's signal to fill them in.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:136:validate-references [FILE ...] [--config PATH] [--schema PATH] [--glob PATTERN]
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:140:**Flag compatibility (codex SA-NEW-001):** `validate-references` accepts the _full_ flag set that `project-standards validate` forwards to its validators — `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`, and `FILE` — so extending `validate` to call it never argparse-errors a previously-valid invocation like `project-standards validate --schema custom.json --quiet`. Under a custom schema (`--schema` or a config custom-schema path) it **skips with a note and exits 0**, mirroring `validate-id` (the reference/id/ADR checks assume the bundled id conventions). `--no-require-frontmatter` is a compat no-op — references already skip files lacking frontmatter.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:155:Collect the included set (via `collect_paths`), parse each file's frontmatter, and build: `id → [paths]`, the set of all known ids, and per-doc `{created, updated, reviewed, related, depends_on, supersedes, superseded_by, doc_type, id, path}`. (`applies_to` is deliberately absent — it is free-form scope, not references; see B.3.)
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:165:| ADR sequence | **error** | duplicate `NNNN` among `doc_type: adr` docs in this repo |
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:177:- **`project-standards fix`** (new subcommand, early-dispatched like `validate` so `--config` is forwarded): runs `format_frontmatter.main(['--write', …])` **first** (normalizes `type`→`doc_type`, fills missing `doc_type`), **then** `validate_id.main(['--fix', …])` (id now derivable from a valid `doc_type`), **then a final read-only `validate`** (`validate-frontmatter` + `validate-id`); returns the worst exit code and **fails if the final pass is non-clean**. Format-first + final-validate proves no invalid id can survive a "successful" fix (codex SA-002). Skips entirely under a custom schema (SA-008).
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:183:Testing: `fix` dispatch (format→id-fix→final-validate, worst exit, final pass clean on `type:`+invalid-id / missing-arrays+invalid-id / path-inferred-`doc_type` fixtures); `validate` runs references when enabled; a reusable-workflow test asserts the `validate-references` invocation; `.pre-commit-hooks.yaml` passes `pre-commit validate-manifest`, every `entry` resolves to a real `[project.scripts]` console script, and `pre-commit try-repo . format-frontmatter-check --all-files` runs the hook successfully.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:188:- `format-frontmatter` is idempotent; preserves comments + per-line endings; **preserves `publish`/`project`/`x_project` nested bytes while reordering** (examples with `project:` format clean); enforces the denylist; scaffolds schema-valid blocks and **reports them distinctly**; skips genuinely-unsupported YAML (anchors/merge/block-scalars) safely; `--stdin` round-trips; **skips when a custom schema is configured**.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:189:- `validate-references` is opt-in; implements all checks with the specified levels and exit codes; dangling = warning; `applies_to` raises no dangling warning; `superseded_by: null` is not flagged; repo-root-relative paths and exact ids resolve, absolute paths/anchors do not. It accepts the forwarded `--schema`/`--no-require-frontmatter`/`--glob` flags (skip-with-note under a custom schema), so `project-standards validate --schema custom.json --quiet` and `--no-require-frontmatter --quiet` still succeed with `references.enabled: true`.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:190:- `project-standards fix` runs format→id-fix→final-validate and **leaves `project-standards validate` clean** for `type:`+invalid-id, missing-arrays+invalid-id, and path-inferred-`doc_type` fixtures. The extended `validate` runs `validate-references` when enabled; the **reusable workflow runs it too** (asserted by test). `.pre-commit-hooks.yaml` passes `pre-commit validate-manifest`, every `entry` maps to a real console script, and a `try-repo` smoke runs.
docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md:200:- No overriding a **valid** `doc_type` (inference is fill/correct-only — see Decision 5).
docs/superpowers/specs/2026-06-08-check-drift-design.md:29:`check` closes the lifecycle. The repo now covers **adopt** (materialize) and **enforce** (`validate-frontmatter`, `validate-id` fail CI on schema violations); `check` adds **drift detection** — telling a consumer when an adopted artifact has fallen behind the bundle, diverged from it locally, gone missing, or fallen out of sync with the standard's current artifact set.
docs/superpowers/specs/2026-06-08-check-drift-design.md:124:- **Writing TOML without a new dependency.** `tomllib` is read-only. `lock.py` hand-rolls a small serializer for this constrained schema (top-level scalars + `[standard]` tables with `contract_version` and the `artifacts`/`local_edits` string→string sub-tables); destinations are quoted TOML keys.
docs/superpowers/specs/2026-06-08-check-drift-design.md:141:- `--json` — machine-readable report (schema below); valid with the default and `--update` modes.
docs/superpowers/specs/2026-06-08-check-drift-design.md:153:**JSON schema** (`--json`), stable contract mirroring `list --json`'s discipline:
docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md:58:| `working/archive/v1.1.0/` (plans + schema proposals) | `docs/superpowers/plans/v1.1.0/` | `git mv` verbatim; row in `specs-plans.md` |
docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md:61:| `AGENTS.md` _General_ rules (dogfood, no-frontmatter-on-agent-files, toolchain-green, schema-is-a-contract) | `docs/handoff/conventions.md` | 4 numbered entries (durable patterns, not live state) |
docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md:74:- **`architecture.md`** — component graph (`standards/`, `schemas/`, `templates/`, `examples/`, `tools/`+`tests/`, `.github/workflows/`) and standing backlog (pre-commit hooks deferred; 2.0.0 repo-root-relative link enforcement, breaking).
docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md:76:- **`conventions.md`** — Quick Reference + 4 numbered entries ported from `AGENTS.md`: (1) Dogfood the standards, (2) Never add frontmatter to agent-instruction files, (3) Keep the toolchain green, (4) The schema is a versioned contract.
docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md:94:- Any change to the standards product, schema, validator code, or tests.
docs/superpowers/specs/2026-06-08-adopt-cli-design.md:29:This repo ships two enforcement modalities — a packaged Python validator (`validate-frontmatter`, schema bundled in the wheel) and reusable `workflow_call` workflows — but only **two of the four released standards** ship a _programmatic adoption path_. The other two are prose a human copies by hand:
docs/superpowers/specs/2026-06-08-adopt-cli-design.md:48:5. **Canonical content + manifests live under the package** at `src/project_standards/bundles/<id>/`, resolved at runtime by a `Path(__file__).parent`-relative lookup — the **same proven, wheel-safe pattern the bundled schema and `registry.json` already use** (`src/project_standards/schemas/`). This supersedes the round-0 idea of keeping canonical templates at repo-root `standards/<id>/templates/`; see "Supersedes" below. The repo-root `standards/<id>/` READMEs _reference_ the packaged files.
docs/superpowers/specs/2026-06-08-adopt-cli-design.md:63:- The Python package `project_standards`, the **existing `validate-frontmatter` console-script entry point** (kept as an alias), the bundled schema at `src/project_standards/schemas/markdown-frontmatter.schema.json` (the path is the schema's own `$id`), and the bundled `registry.json` + its `Registry` reader.
docs/superpowers/specs/2026-06-08-adopt-cli-design.md:192:The shipped ADR template carries intentional placeholder frontmatter (`YYYY-MM-DD` dates, `replace-with-stable-id`) that **deliberately fails the schema** — exactly why this repo excludes `standards/**/templates/**` from validation. So `adopt adr` writes it to a **template path that the consumer's validation excludes**: `docs/decisions/adr.template.md`, and the markdown-frontmatter `.project-standards.yml` **starter's `exclude` list covers `**/\*.template.md`** (mirroring this repo's own template exclusion). A consumer authors a real ADR by copying the template to `docs/decisions/NNNN-title.md` and filling it in.
docs/superpowers/specs/2026-06-08-adopt-cli-design.md:228:- `list` prints every released standard and its artifact destinations (plain text); `--json` emits the same data with a stable schema: an array of standards, each `{id, contract_version, artifacts: [{kind, dest|target, source|shared, owner}]}`.
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:46:6. **Doc-type scaffolds belong to the frontmatter bundle.** `concept/note/runbook/research/spec` templates and examples demonstrate the `doc_type` + frontmatter profile, which the Frontmatter Standard owns. ADR's scaffolds live in the ADR bundle even though ADR builds on frontmatter.
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:54:- The **Python package** `project_standards`, its `validate-frontmatter` console-script entry point, and the **bundled schema** at `src/project_standards/schemas/markdown-frontmatter.schema.json` (the path is the schema's own `$id`).
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:148:| `src/project_standards/validate_frontmatter.py` (docstrings), `…/schemas/*.json` (`description`) | Repoint `standards/adr.md` → `standards/adr/README.md`, etc. **The schema `$id` line stays.** |
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:151:| `CHANGELOG.md` | 2.0.0 entry: docs reorg (BREAKING for doc deep-links; consumer workflow + validator + schema contract unchanged). |
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:153:**Verify during implementation:** `.markdownlint-cli2.jsonc` for any `templates/`/`examples/` path ignores that must follow the move. **Confirmed unchanged:** `.github/workflows/**`, `pyproject.toml` (no standards-path coupling; schema ships from `src/`), `scripts/check.py`, git tags.
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:181:Under this repo's own versioning contract ("the contract is the consumer's _validation outcome_"), moving docs changes nothing a consumer depends on — config schema, workflow names, validator entry point, and bundled schema are untouched. A repo pinned `@v1` is wholly unaffected (old tags immutable); a repo moving to `@v2` sees identical validation behavior. The restructure therefore **does not force a major on its own** — it rides inside the already-locked `2.0.0` (whose break is the `requires-python` 3.13 bump). One major absorbs both; there is no second migration for consumers.
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:188:- Renaming or restructuring the validator package, the reusable workflows, or the bundled schema location.
docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md:189:- Changing the validator's behavior, the schema contract, or the config schema shape.
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:34:This repo defines a deliberately **tool-neutral** Markdown Frontmatter Standard (`standards/markdown-frontmatter/README.md`, line 35: "not an Obsidian/Hugo/Jekyll/Quarto schema"). It governs the YAML metadata block and says nothing about how the Markdown _body_ — or the JSON/YAML config files that live alongside docs — should be linted or formatted. Yet the repo already runs a complete toolchain for exactly that: Prettier (formatter, repo-wide over `md`/`json`/`jsonc`/`yaml`) + markdownlint-cli2 (Markdown linter) + EditorConfig (floor). That toolchain's design is recorded only as a scratch decision trail (`docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`, DEC-1…9) and as comments inside the config files. There is no **governing reference** a reader or downstream consumer can adopt.
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:42:1. **Form = a new governed standard bundle** — sibling to `markdown-frontmatter/`, `adr/`, `python-tooling/`. The bundle folder is doc-only (`README.md` + `adopt.md`); the contract-version support lives in `src/` (like the frontmatter schema/validator), so "doc-only bundle" refers to the folder, not the standard's full footprint.
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:76:└── adopt.md       # adoption runbook (doc_type: runbook)
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:79:Both files carry conformant frontmatter (`doc_type: reference` for README, `runbook` for adopt) because they fall under the validator's `standards/**/*.md` include. The contract-version support (decision 4) lives in `src/`, not the bundle.
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:98:2. **Purpose & scope** — governs Markdown linting + Prettier formatting of all Prettier-supported files (`md`/`json`/`jsonc`/`yaml` in this repo) + the EditorConfig floor; the complement to the tool-neutral Frontmatter standard and the Python Tooling standard. Out of scope: `.py` (ruff) and YAML frontmatter _semantics_ (the Frontmatter schema/validator).
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:137:- **`src/project_standards/schemas/registry.json`** — add `"markdown_tooling": { "default": "1.0", "versions": ["1.0"] }`.
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:149:- markdownlint (DavidAnson) — `Rules.md` (MD001/003/004/009/010/013/024/025/029/030/032/041/043/048/049/050), `.markdownlint.json` schema, `default` behavior.
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:163:| `src/project_standards/schemas/registry.json` | add `markdown_tooling` (SA-001) |
docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md:229:- **No new validator over document bodies / no schema.** Markdown body linting is enforced (downstream) only by the existing reusable markdownlint workflow; the contract version is a validated _label_, not a body gate.
docs/superpowers/specs/2026-06-06-python-tooling-ssot-adoption-design.md:18:    - [G. Reference sweep (path/schema moves + new gate)](#g-reference-sweep-pathschema-moves--new-gate)
docs/superpowers/specs/2026-06-06-python-tooling-ssot-adoption-design.md:30:The complication: this repo's Python is not incidental. The `tools/` validator is a **shipped product** — downstream repos install `validate-frontmatter` via `uv tool install git+...@<tag>` and call reusable workflows. So the migration must preserve the wheel's ability to resolve the bundled schema by name, and must not damage the orthogonal **Markdown-standard product** (Prettier + markdownlint + the reusable `validate-markdown-frontmatter.yml` / `lint-markdown.yml` workflows) that this repo also ships.
docs/superpowers/specs/2026-06-06-python-tooling-ssot-adoption-design.md:38:3. **Schema moves into the package** — `src/project_standards/schemas/markdown-frontmatter.schema.json`. Forced by `uv_build`: per current uv docs, _"all data files must be under the module root or a data directory"_, and `[tool.uv.build-backend].data` dirs land in the wheel's `.data/` (not the importable package). The repo-root `schemas/` directory is **retired**; the package copy is canonical.
docs/superpowers/specs/2026-06-06-python-tooling-ssot-adoption-design.md:67:| `schemas/markdown-frontmatter.schema.json` | `src/project_standards/schemas/markdown-frontmatter.schema.json` | `git mv` |

exec
/bin/bash -lc "UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY'
from project_standards.format_frontmatter import format_text
src='''---\\nschema_version: '1.1'\\nid: 'note-a3f9zk-x'\\ntitle: 'X'\\ndescription: 'A doc.'\\n# type: legacy alias\\ntype: 'note'\\nstatus: 'draft'\\ncreated: '2026-06-08'\\nupdated: '2026-06-08'\\ntags: []\\naliases: []\\nrelated: []\\n---\\n'''
new,_,_=format_text(src,path=None)
print(new)
PY" in /home/chris/projects/project-standards
 succeeded in 0ms:
---
schema_version: '1.1'
id: 'note-a3f9zk-x'
title: 'X'
description: 'A doc.'
# doc_type: legacy alias
doc_type: 'note'
status: 'draft'
created: '2026-06-08'
updated: '2026-06-08'
tags: []
aliases: []
related: []
---


exec
/bin/bash -lc "nl -ba src/project_standards/format_frontmatter.py | sed -n '540,585p'" in /home/chris/projects/project-standards
 succeeded in 0ms:
   540	                eol = _line_ending(entry.lines[0])
   541	                entry.lines = [f"updated: {_emit_single_quoted(stamp)}{eol}"]
   542	        new_body = serialize(entries)
   543	        new_text = open_fence + new_body + close_fence + rest
   544	        changed = new_text != text
   545	    return new_text, changed, warnings
   546	
   547	
   548	from project_standards.validate_frontmatter import (  # noqa: E402
   549	    ConfigError,
   550	    collect_paths,
   551	    load_config,
   552	    schema_value_is_path,
   553	)
   554	
   555	_DEFAULT_CONFIG = Path(".project-standards.yml")
   556	
   557	
   558	def _atomic_write(path: Path, data: str) -> None:
   559	    """Write atomically AND preserve the original file's permission bits (codex
   560	    missing-consideration): mkstemp creates 0600, so copy the source mode first."""
   561	    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
   562	    tmp_path = Path(tmp)
   563	    try:
   564	        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
   565	            fh.write(data)
   566	        with contextlib.suppress(OSError):
   567	            tmp_path.chmod(path.stat().st_mode & 0o777)
   568	        tmp_path.replace(path)
   569	    except BaseException:
   570	        tmp_path.unlink()
   571	        raise
   572	
   573	
   574	def main(argv: list[str] | None = None) -> int:
   575	    parser = argparse.ArgumentParser(
   576	        prog="format-frontmatter",
   577	        description=__doc__,
   578	        formatter_class=argparse.RawDescriptionHelpFormatter,
   579	    )
   580	    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
   581	    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
   582	    parser.add_argument("--schema", type=Path, default=None)
   583	    parser.add_argument("--glob", metavar="PATTERN")
   584	    mode = parser.add_mutually_exclusive_group()
   585	    mode.add_argument("--check", action="store_true")

exec
/bin/bash -lc "nl -ba src/project_standards/format_frontmatter.py | sed -n '600,635p'" in /home/chris/projects/project-standards
 succeeded in 0ms:
   600	    except ConfigError as exc:
   601	        print(f"error: {exc}", file=sys.stderr)
   602	        return 2
   603	
   604	    if args.schema is not None or schema_value_is_path(config.schema):
   605	        if not args.quiet:
   606	            print("note: custom schema in use; skipping frontmatter formatting")
   607	        return 0
   608	
   609	    if args.stdin:
   610	        text = sys.stdin.read()
   611	        new, _changed, _warn = format_text(text, path=None, bump_updated=args.bump_updated)
   612	        sys.stdout.write(new)
   613	        return 0
   614	
   615	    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
   616	    write = args.write  # default is check-mode
   617	    any_change = False
   618	    unparseable = False
   619	    for path in paths:
   620	        if is_denylisted(path):
   621	            continue
   622	        try:
   623	            text = path.read_text(encoding="utf-8")
   624	        except OSError as exc:
   625	            print(f"{path}: cannot read: {exc}", file=sys.stderr)
   626	            unparseable = True
   627	            continue
   628	        new, changed, warnings = format_text(
   629	            text, path=path, scaffold=write, bump_updated=args.bump_updated
   630	        )
   631	        for w in warnings:
   632	            print(f"{path}: {w}", file=sys.stderr)
   633	            # A duplicate-key block is refused (not rewritten) AND must fail the gate (CR-002).
   634	            if "duplicate top-level key" in w:
   635	                unparseable = True

exec
/bin/bash -lc "printf '%s' \"---
tags: []
tags: ['x']
---
# B
\" | UV_CACHE_DIR=/tmp/uv-cache uv run format-frontmatter --stdin >/tmp/fmout 2>/tmp/fmerr; rc="'$?; printf '"'rc=%s\\nstdout=%s\\nstderr=%s\\n' \""'$rc" "$(cat /tmp/fmout)" "$(cat /tmp/fmerr)"' in /home/chris/projects/project-standards
 succeeded in 106ms:
rc=0
stdout=---
tags: []
tags: ['x']
---
# B
stderr=

codex
The new formatter can silently change valid document metadata in path-inference cases and lets stdin mode report success for frontmatter it could not safely process. These behavioral issues should be fixed before treating the patch as correct.

Full review comments:

- [P2] Preserve commented valid doc_type values — /home/chris/projects/project-standards/src/project_standards/format_frontmatter.py:457-457
  When formatting `README.md`, `index.md`, or `docs/research/**`, a valid `doc_type` with an inline comment (for example `doc_type: 'reference'  # intentional`) is parsed as `reference'  # intentional`, treated as invalid, and overwritten with the path-inferred value. In `project-standards fix` this can then cascade into `validate-id --fix` rewriting the document id to match the wrong type, even though the explicit value was valid and should be kept.

- [P2] Fail stdin mode on unparseable frontmatter — /home/chris/projects/project-standards/src/project_standards/format_frontmatter.py:611-613
  For `format-frontmatter --stdin`, duplicate keys or unsupported frontmatter only appear in the `warnings` returned by `format_text`, but this branch discards them and always exits 0. That makes stdin-based editor/CI integrations silently accept invalid frontmatter that file mode correctly treats as a failing condition, such as duplicate top-level keys.

- [P3] Rename only the type key line — /home/chris/projects/project-standards/src/project_standards/format_frontmatter.py:401-401
  When a legacy `type:` entry has leading comments, this substitution runs across every line owned by the entry, so a comment like `# type: legacy alias` is rewritten to `# doc_type: legacy alias`. The formatter otherwise promises to preserve authored comments, so this should target only the actual key line rather than all `entry.lines`.
The new formatter can silently change valid document metadata in path-inference cases and lets stdin mode report success for frontmatter it could not safely process. These behavioral issues should be fixed before treating the patch as correct.

Full review comments:

- [P2] Preserve commented valid doc_type values — /home/chris/projects/project-standards/src/project_standards/format_frontmatter.py:457-457
  When formatting `README.md`, `index.md`, or `docs/research/**`, a valid `doc_type` with an inline comment (for example `doc_type: 'reference'  # intentional`) is parsed as `reference'  # intentional`, treated as invalid, and overwritten with the path-inferred value. In `project-standards fix` this can then cascade into `validate-id --fix` rewriting the document id to match the wrong type, even though the explicit value was valid and should be kept.

- [P2] Fail stdin mode on unparseable frontmatter — /home/chris/projects/project-standards/src/project_standards/format_frontmatter.py:611-613
  For `format-frontmatter --stdin`, duplicate keys or unsupported frontmatter only appear in the `warnings` returned by `format_text`, but this branch discards them and always exits 0. That makes stdin-based editor/CI integrations silently accept invalid frontmatter that file mode correctly treats as a failing condition, such as duplicate top-level keys.

- [P3] Rename only the type key line — /home/chris/projects/project-standards/src/project_standards/format_frontmatter.py:401-401
  When a legacy `type:` entry has leading comments, this substitution runs across every line owned by the entry, so a comment like `# type: legacy alias` is rewritten to `# doc_type: legacy alias`. The formatter otherwise promises to preserve authored comments, so this should target only the actual key line rather than all `entry.lines`.
