---
schema_version: '1.1'
id: 'reference-6mnv03-github-workflow-session-corpus-efficiency-review'
title: 'github-workflow Session-Corpus Efficiency Review'
description: 'Measured review of every recorded Claude Code and Codex session in the six repositories that install github-workflow, separating defects resolved by v5.20.0 from the live context-cost and coverage problems.'
doc_type: 'reference'
status: 'active'
created: '2026-08-26'
updated: '2026-08-26'
reviewed: '2026-08-26'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'github-workflow'
  - 'review'
  - 'validation'
  - 'standards-platform'
aliases:
  - 'github-workflow efficiency review'
  - 'GW session corpus review'
related:
  - 'standards/github-workflow/README.md'
  - 'standards/github-workflow/agent-summary.md'
  - 'docs/research/2026-08-06-github-workflow-live-run-evidence.md'
  - 'docs/specs/2026-08-06-github-workflow-package-spec.md'
  - 'docs/specs/2026-08-06-github-workflow-package-design.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# github-workflow Session-Corpus Efficiency Review

This is a measured review of how the **github-workflow** package behaves in production agent sessions, undertaken to find where it costs tokens, imposes friction, or fails to reach the agent. It is descriptive: it reports what the corpus shows and does not propose package changes.

Three conclusions frame everything below.

**The package is not failing on correctness.** Its command error rate is 3.1%, its field validation catches what agents guess wrong, and no session in the corpus violated the readiness-inference refusal.

**The corpus spans a repair, and the repair worked.** Release v5.20.0 (2026-08-15) fixed Claude Code skill discovery with a dual-tree install. Splitting at that date separates two defects that are now **resolved** from six that remain **live**. Any figure quoted without an era attached averages across a step change and is the wrong number to reason from.

**Guidance loading is now the dominant live cost, and the repair increased it.** Post-repair sessions load more guidance than pre-repair ones (108 loads against 77), because they comply more. Fixing distribution converted a compliance problem into a context-cost problem.

| Finding | Status |
| --- | --- |
| F1 Load compliance (parent sessions) | Resolved by v5.20.0 |
| F2 Skill discovery failure | Resolved by v5.20.0; two repositories still undeployed |
| F3 Whole-file guidance loads | Live, growing |
| F4 `field-vocabulary.md` size | Live |
| F5 Routing violations vs coverage gaps | Violations resolved; gaps live |
| F6 CI waiting is unowned | Live |
| F7 Work-state payload width | Live, improving |
| F8 Helper usage rediscovery | Live, growing |
| F9 Correctness | Not a problem |
| F10 Delegated workers bypass the load path | Live |

## Method

The corpus is every recorded Claude Code and Codex session for the six repositories that have the package installed, identified by the deployed skill directory rather than by catalog pin: `agent-configs`, `agent-ventures`, `llm-wiki`, `project-feldspar`, `project-standards`, `social-ventures`.

Claude Code stores one JSONL per session under `~/.claude/projects/<path-slug>/`, keyed by `tool_use` / `tool_result` pairs. Codex stores `rollout-*.jsonl` under `~/.codex/sessions/YYYY/MM/DD/`, where each shell call is a `custom_tool_call` whose `input` is JavaScript wrapping the command. Both were normalized into one event stream covering skill invocations, reference reads, `gh` and `gh-workflow` invocations, and each call's result payload and error flag.

Byte-cost, not token-cost, is the unit throughout. Claude records real `usage` figures and Codex does not, but both record exact commands and payload sizes, so bytes-in-context is the only measure comparing across harnesses.

Fourteen high-signal sessions — seven per harness — were read in depth to check the aggregates against verbatim transcript evidence. A separate reviewer then re-derived the numbers from the raw corpus with an independently written extractor.

### Counting rules, and a correction they forced

**One invocation is one tool call**, counted once per distinct operation key it contains. A shell line chaining `gh issue view 1 && gh issue view 2` is one invocation; a line mixing `gh run list` with `gh issue view` contributes to both keys.

**`gh` must appear in command position** — at the start of a line or after `;`, `&`, `|`, `` ` ``, `$(`, `&&`, `||`, `do`, `then`, or `else`. The first pass of this review matched `gh` anywhere in a command string. Independent re-derivation showed that inflated the totals badly, because these transcripts are full of heredocs, commit messages, `grep` patterns, and prose that contain the literal text `gh issue create`. Only 88% of the original Claude matches and **47% of the original Codex matches** survive the command-position test; the corpus total falls from 2,203 to 1,431. Every figure in this document is the corrected one.

That correction changed magnitudes, not conclusions: every finding's direction, era split, and ratio survived it. Absolute counts here should still be read as carrying a band of roughly 10–15%, since a reasonable alternative unit — per shell segment rather than per tool call — moves them again. **Ratios and era splits, computed under one definition throughout, are firmer than absolute totals.**

**Error counting is restricted to genuine tool results** — `tool_result` blocks carrying `is_error`. A text search for a string such as `Unknown skill: github-workflow` also matches agent prose discussing the failure; restricting to real errors reduces that string's match count from 23 to 7 and moves its entire date range.

**Self-contamination was checked and is negligible.** Transcripts include this review's own analysis scripts pasted as heredocs. Excluding every event whose command references the analysis harness removes **1 event**, and moves no figure.

### Corpus scale

|                                  | Claude Code | Codex | Total             |
| -------------------------------- | ----------- | ----- | ----------------- |
| Sessions touching GitHub         | 69          | 117   | 186               |
| Sessions mutating GitHub state   | 41          | 19    | 60                |
| `gh` / `gh-workflow` invocations | 835         | 596   | 1,431             |
| Command error rate               |             |       | 3.1% (44 / 1,431) |

By era: 1,042 invocations before 2026-08-15, 389 on or after.

## Resolved by v5.20.0

### F1 — Load compliance went from 35% to 100%

Sessions that created, edited, closed, or commented on GitHub work state, by whether they loaded the standard at all:

| Era               | Claude Code   | Codex          | Combined           |
| ----------------- | ------------- | -------------- | ------------------ |
| Before 2026-08-15 | 10 / 32 (31%) | 4 / 8 (50%)    | **14 / 40 (35%)**  |
| On or after       | 9 / 9 (100%)  | 11 / 11 (100%) | **20 / 20 (100%)** |

Every mutating **parent** session since the repair loaded the standard first. That scoping matters: F10 shows delegated subagents, invisible to this measure, perform roughly half the mutation volume and almost never load the standard.

### F2 — Skill discovery no longer fails, but is not fully deployed

Genuine `Unknown skill: github-workflow` tool errors number **7**, dated 2026-08-07, 08-08, 08-09 (×2) and 08-10 (×3). **None occurred on or after 2026-08-15.** An independent extractor reproduced this exactly, including zero occurrences anywhere in the Codex corpus.

The cause was a path mismatch: the package installed its skill only to `.agents/skills/`, which Codex discovers natively, while Claude Code registers skills only from `.claude/skills/`, `~/.claude/skills/`, and plugins. v5.20.0's dual-tree byte-identical install closed it.

The recovery cost is what the repair bought back. After the sibling `Unknown skill: agent-handoff`, one agent wrote _"The agent-handoff skill isn't registered under that exact name in this session — let me find the repo-local skill"_, then dispatched two subagents purely to establish where Claude Code discovers skills from, none of which advanced the task.

Two residues persist.

Even post-repair, Claude Code sessions reach the guidance by shell more often than by tool — **10 `Skill` invocations against 25 manual document reads**. The tool path works; it is not consistently the one taken.

And the repair is not universally deployed. Checking installed trees directly, `agent-ventures` and `llm-wiki` still carry only `.agents/skills/github-workflow/` with no `.claude/` counterpart. Neither shows the failure here because both are Codex-dominated — one Claude Code session each against 44 Codex sessions — but a Claude Code session opened in either repository today would reproduce the original failure exactly.

## Live findings

### F3 — Guidance loads are whole-file, repeat within a session, and are growing

Counted from invocation events only, deduplicated so that a command echoed back inside its own output is not recounted:

| Document                         | Loads before | Loads on/after |
| -------------------------------- | ------------ | -------------- |
| `SKILL.md`                       | 49           | 47             |
| `references/field-vocabulary.md` | 16           | 26             |
| `references/issue-structure.md`  | 9            | 21             |
| `references/pr-standard.md`      | 1            | 8              |
| `references/org-schema.yaml`     | 1            | 5              |
| `references/summary-format.md`   | 0            | 1              |
| `references/review-checklist.md` | 1            | 0              |
| **Total**                        | **77**       | **108**        |

Multiplying by actual file sizes: **941,871 bytes before the repair, 1,101,532 after** — about **19,000 bytes of guidance per post-repair session**. Loading rose because compliance rose, which makes this the dominant live cost rather than a shrinking legacy one.

**Every load is a whole-file load.** `SKILL.md` is **157 lines**. Post-repair read shapes are `sed -n '1,240p'` (20), `'1,260p'` (13), `'1,220p'` (12), plus 8 bare `cat` reads and 5 at `'1,9999p'` — agents read blindly past end-of-file because nothing tells them the length. Codex batches: one session issued `sed -n '1,9999p'` across six different `SKILL.md` paths in a single `Promise.all`. Narrower ranges such as `sed -n '1,80p'` (6) do begin to appear post-repair.

**Loads repeat inside one session.** Across the 61 sessions that read any document: `SKILL.md` re-read 43 times, `field-vocabulary.md` 15, `issue-structure.md` 7, `pr-standard.md` 4. One Codex session loaded `SKILL.md` four times. A Claude session read it in full through the `Read` tool, then re-read the command-surface section with `sed -n '55,80p'`.

Reach is very uneven: `SKILL.md` reached 57 sessions and `field-vocabulary.md` 30, while `summary-format.md` and `review-checklist.md` reached **one session each**.

### F4 — field-vocabulary.md is oversized relative to its use

At 12,344 bytes and 240 lines it is nearly as large as `SKILL.md`, is read by 30 sessions, is essentially always read in full, and is typically consulted to confirm one or two field values before a single `new` or `set` call. One Codex session read the whole file immediately before a `new` invocation that used only `Size`, `Change risk`, and `Execution mode`. Its load count **rose** across the repair, from 16 to 26.

Reading it in full does not reliably prevent the error it exists to prevent, because the binary already validates and reports the valid set on refusal:

```text
gh-workflow set: "Low" is not a valid Severity value;
  valid values are: S0 Critical, S1 High, S2 Moderate, S3 Low

gh-workflow set: "High" is not a valid Priority value;
  valid values are: P0 Immediate, P1 Next, P2 Planned, P3 Opportunistic, P4 Someday
gh-workflow set: "P1 High" is not a valid Priority value; valid values are: P0 Im...

gh-workflow new: "S2 Medium" is not a valid Severity value;
  valid values are: S0 Critical, S1 High, S2 Moderate, S3 Low
```

The second block is the informative one: the agent guessed `High`, was told the valid set, then guessed `P1 High` — a blend of its own guess and the answer it had just been given. These vocabularies are memory-hostile in a way a document read minutes earlier does not fix, and the refusal path already handles them at zero standing context cost.

### F5 — Routing violations are resolved; the coverage gaps are not

| Covered by the surface — routing violations | Before | On/after |
| ------------------------------------------- | ------ | -------- |
| create issue → `new`                        | 26     | **0**    |
| close issue → `close`                       | 13     | **0**    |

| Not covered by the surface — coverage gaps | Before | On/after |
| ------------------------------------------ | ------ | -------- |
| wait on CI (`gh run` / `gh pr checks`)     | 389    | 64       |
| post a comment                             | 35     | 5        |
| merge a pull request                       | 8      | 8        |
| create a pull request                      | 3      | 2        |

Routing violations fall to **zero** after the repair, while helper invocations **rise** from 94 to 138 in an era carrying roughly one third the total command volume. Where the surface covers an operation and the tool is reachable, agents route through it.

Where agents did reach for raw `gh` on an arguably-covered action, both qualitative readers found explicit reasoning citing a real surface gap rather than unawareness:

> `gh-workflow set` covers Issue Fields but has no subcommand for retyping an existing issue... I used a raw `gh` call for one mutation.

and, in a second session:

> gh-workflow tool doesn't support title edits.

One reader noted a genuine ambiguity this creates. `SKILL.md`'s refusal text scopes the ban on improvised raw `gh` mutations to _"an unavailable tool"_, and says nothing about a **working** tool with a documented capability gap. The agent reasoned the question out from first principles each time it hit one — _"The real question is whether this is a genuine gap in the tool's design or a workaround that bypasses validation"_ — and hit it twice in one session for two different missing capabilities.

Uncovered operations, verbatim:

```bash
gh issue comment 115 --repo L3DigitalNet/project-standards \
  --body-file /tmp/.../scratchpad/issue115-comment.md

CHILD_ID=$(gh api repos/L3DigitalNet/project-feldspar/issues/71 --jq '.id')
gh api -X POST repos/L3DigitalNet/project-feldspar/issues/69/sub_issues \
  -F sub_issue_id="$CHILD_ID" --jq '.number'

gh pr merge 7 --merge
```

### F6 — CI waiting is unowned, and is the largest adjacent surface

**461 of 1,431 commands (32%)** are `gh run list`, `gh run view`, `gh run watch`, or `gh pr checks`, returning 1.09 MB — 19% of all tool output attributable to GitHub work. `gh run list` alone is the most frequent single command at 252 invocations.

| Era               | Polling | Hand-rolled wait loops |
| ----------------- | ------- | ---------------------- |
| Before 2026-08-15 | 391     | 147                    |
| On or after       | 70      | 23                     |

The share fell, but the behaviour did not change: each loop is independently reinvented.

```bash
until [ "$(gh pr checks 10 2>/dev/null | grep -cE '\bpending\b')" = "0" ]; do
  sleep 20
done; echo "SETTLED"; gh pr checks 10 2>&1 | head -12

for attempt in $(seq 1 10); do
  active="$(gh run list ... --jq '[.[]|select(.status!="completed")]|length')"
  if [[ "$active" == '0' ]]; then break; fi
  sleep 5
done
```

One Codex session escalated its own loop bound from `seq 1 10` to `seq 1 12`, then to twelve explicit attempts, within a single task. Several loops were rejected outright by the harness before running:

```text
<tool_use_error>Blocked: sleep 90 followed by: gh pr checks 10 head -10.
To wait for a condition, use Monitor with an until-loop...

<tool_use_error>Blocked: sleep 30 followed by: gh run list --repo ... --branch=dev
```

This is not a violation of the package's contract — the routing map has no CI-wait subcommand, so there is nothing to route to.

### F7 — Work-state payloads are wide, and improving

`gh issue view` runs 158 times at a mean of 6,721 bytes, 1.06 MB in total. Discipline is not the problem — 178 of 215 issue and pull-request views (83%) pass `--json`. Projection width is.

| Projection      | Mean payload        |
| --------------- | ------------------- |
| Includes `body` | 11,209 B (66 calls) |
| Excludes `body` | 3,502 B (92 calls)  |

Across 355 observed projections, `body` appears in 131 and `comments` in 71, at a mean of 4.2 fields per call. The widest observed:

```bash
gh pr view N --json number,title,body,state,isDraft,mergeable,mergeStateStatus,\
reviewDecision,headRefName,headRefOid,baseRefName,baseRefOid,commits,files,reviews,\
comments,closingIssuesReferences,statusCheckRollup,url          # 19 fields → 40,134 B
```

A reader traced that call's downstream use: only `headRefOid`, `mergeable`, `mergeStateStatus`, and `statusCheckRollup` were ever referenced.

Two compounding effects:

- **28% of issue views re-fetch an issue the same session already fetched** — 53 re-views of 189. One session queried issue #134 as `--json number,state,title` then again as `--json state,stateReason`; another queried #168 as `--json body` and later as `--json title,body,createdAt,updatedAt`.
- One session requested `projectItems` across 20 issues against a token lacking `read:project`, so the field could not resolve for any of them — _"ProjectV2 fields unavailable for all 14 issues — the token lacks `read:project` scope"_.

### F8 — Helper usage is rediscovered by design, and the cost is growing

Twenty-five of the 59 helper-using sessions invoked `gh-workflow help` or `<subcommand> -h` — 30 calls returning 129 KB. This traces directly to `SKILL.md`, which instructs the agent to _"consult the tool's own help ... rather than reciting it from memory"_ even though the same file carries a complete flag table for all nine subcommands.

The cost is deliberate, and it is **rising** as helper adoption rises: 9 such calls before the repair, **21 after**, in an era with one third the command volume.

```bash
.agents/skills/github-workflow/bin/gh-workflow new -h 2>&1 | head -30
.agents/skills/github-workflow/bin/gh-workflow help 2>&1 | head -20
```

One session hit four consecutive `gh-workflow: command not found` errors from invoking the bare name before switching to the checked relative path.

The binary preflight mandate — "check the binary once per session, before the first invocation" — ran in 48 of 64 helper-using sessions under the original matcher. It succeeded trivially every time, and its omissions produced no failure anywhere in the corpus.

### F9 — Correctness is not the problem

The error rate is **3.1%** (44 of 1,431), and only 4 errors were followed by a reference re-read, so the documents are rarely the repair path. Rates are concentrated in read-side commands — `gh release download` 22% (4/18), `gh pr checks` 14% (4/28), `gh release view` 11% (5/45) — rather than in the package's own mutation surface. `gh-workflow set` at 10% (3/31) is the field-vocabulary refusal path of F4 working as designed.

Rule adherence, where the corpus can speak to it:

- **Readiness inference** — no violation observed. `gh-workflow check --issue N` recurs as the actual gate.
- **Execution mode self-promotion** — correctly refused, explicitly: _"No `Execution mode` was set anywhere — that one stays yours."_
- **Terminal-state synchronization** — the failure mode is churn, not error. One session cycled issue #31 through `close --as done` → `reopen --workflow 'In progress'` four times, each gated on push/fetch parity, converging as designed. Another self-caught a near-miss: it noticed its own commit message `Closes #131` would silently auto-close on merge to `main` and wrote _"That's exactly the terminal-state desynchronization the package exists to prevent"_ — the standard's stated rationale, not its tooling, doing the work.
- **PR-links-issue** — measured against live pull requests rather than transcripts, because the rule's evidence lives on GitHub. Across 52 non-dependabot pull requests in the six repositories:

  | Era               | PRs | Any issue reference | Closing keyword + issue |
  | ----------------- | --- | ------------------- | ----------------------- |
  | Before 2026-08-15 | 13  | 4 (31%)             | 1 (8%)                  |
  | On or after       | 39  | 31 (79%)            | 26 (67%)                |

  The same step change appears, but compliance is not complete: 8 of 39 post-repair pull requests carry no issue reference at all, and this repository's own three agent-authored pull requests (`#4`, `#120`, `#125`) link nothing.

### F10 — Delegated workers are half the mutation volume and bypass the load path

Claude Code subagent transcripts are not written into the parent session file — an `isSidechain` count across all 107,408 parent-transcript lines returns **zero**. They are persisted separately under `/tmp/claude-1000/<project>/<session>/tasks/*.output`, which `/tmp` retention limits to a three-day window (2026-08-24 to 2026-08-26 at the time of writing). That window is entirely post-repair, and 224 such transcripts survive in it.

Excluding transcripts belonging to this review's own analysis agents, and counting only `Bash` invocations that run a mutation rather than search for one:

|                      | Parent sessions       | Subagents  |
| -------------------- | --------------------- | ---------- |
| Mutations performed  | 54                    | 50         |
| Distinct transcripts | 10                    | 15         |
| Loaded the standard  | 9 / 9 mutating (100%) | **1 / 15** |

**48% of observed GitHub mutations in that window happened inside delegated workers**, and 14 of the 15 workers that performed them never read `SKILL.md` or any reference.

The behaviour that survives delegation is routing, not guidance: these workers reach for `gh-workflow new`, `set`, and `close` directly, evidently from rules embedded in their briefs or role definitions rather than from a live load. One sampled parent session shows that construction explicitly, dispatching a `triager` with the package's binding rules pre-embedded in its system prompt.

They also pay F8's cost again, in isolation:

```bash
.agents/skills/github-workflow/bin/gh-workflow new -h 2>&1; echo ---
./.agents/skills/github-workflow/bin/gh-workflow help close 2>&1
```

This does not overturn F1 — parent-session compliance genuinely went to 100% — but it bounds it. The population F1 measures is roughly half the population that mutates.

## Limits of this review

- **Absolute counts carry a 10–15% band; ratios do not.** The counting-unit correction described in Method changed the corpus total from 2,203 to 1,431 without changing any finding's direction. Treat era splits, ratios, and step changes as the durable results, and single totals as indicative.
- **Independent re-derivation reproduced the Claude side and diverged on Codex.** A reviewer writing a separate extractor matched the Claude figures closely — invocations within 2%, tool-output bytes exactly, F1 rates confirmed, `gh run list` within 6%, CI-wait counts within 3% — but reached roughly 40–60% of the Codex counts. The gap was not resolved. Because that reviewer's rates and proportions agreed with these even where absolute counts did not, the shape of the findings is corroborated while the Codex absolute totals remain the least certain numbers here.
- **Codex error detection is weaker than Claude's.** Claude `tool_result` blocks carry a structured `is_error` field; the newer Codex `custom_tool_call_output` shape carries no exit-code field, so Codex-side errors are detected heuristically from output text. The 3.1% rate is therefore a floor, and understates the true rate by an unknown margin concentrated in the post-repair era.
- **Selection bias in the qualitative sample.** Sessions were ranked for depth reading by a score weighting reference reads, so the 14 sampled sessions load documents far above the corpus base rate. Every rate here comes from the full corpus, never the sample. One reader initially refuted F1 on its seven sessions; that refutation reflects the ranking, not the population.
- **The post-repair era is small and recent** — 58 sessions and 389 invocations over eleven days. Zero routing violations in that window is a real signal but a short one.
- **The era boundary was checked, not assumed.** Four of six repositories carry the dual-tree install today, and the two that do not hold one Claude Code session each against 44 Codex sessions. Since Codex discovers `.agents/skills/` natively, the undeployed repositories do not distort the post-repair figures: splitting that era by actual repair status gives Claude in repaired repositories 9/9, Codex in repaired 3/3, Codex in unrepaired 13/13.
- **Subagent transcripts are invisible to the parent and only recently recoverable.** F1 through F9 are measured on parent sessions alone. F10 quantifies the undercount, but only inside the three-day `/tmp` retention window; the same measurement cannot be made for the pre-repair era, so F10's ratio must not be projected backwards.
- **The extraction filter cannot prove absences.** Events were matched on a `gh` / `gh-workflow` / skill-path regex, so the corpus cannot establish that agents never asked the operator a question `SKILL.md` should have answered, only that no such question appeared adjacent to matched activity. A hand-built `gh api` PATCH against project field values also evades the routing classification in F5.

## Reproduction

The normalized event stream and the analysis scripts behind every figure were written to scratch directories outside this repository and are not tracked. Regenerating them requires the local session stores under `~/.claude/projects/` and `~/.codex/sessions/`, which are workstation state, not repository state.
