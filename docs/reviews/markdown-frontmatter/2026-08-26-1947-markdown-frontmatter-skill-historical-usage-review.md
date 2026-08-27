---
schema_version: '1.1'
id: 'reference-m8s29w-markdown-frontmatter-skill-historical-usage-review'
title: 'markdown-frontmatter Skill Historical Usage Review'
description: 'Read-only review of Claude Code and Codex sessions that loaded, followed, or worked around the packaged markdown-frontmatter skill, separating already-fixed defects from live friction.'
doc_type: 'reference'
status: 'active'
created: '2026-08-26'
updated: '2026-08-26'
reviewed: '2026-08-26'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'frontmatter'
  - 'metadata'
  - 'review'
  - 'validation'
  - 'standards-platform'
aliases:
  - 'markdown-frontmatter skill review'
  - 'MF skill usage review'
related:
  - 'standards/markdown-frontmatter/versions/1.13/README.md'
  - 'standards/markdown-frontmatter/versions/1.13/skills/markdown-frontmatter/SKILL.md'
  - 'docs/reviews/github-workflow/2026-08-26-0847-github-workflow-session-corpus-efficiency-review.md'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# `markdown-frontmatter` Historical Usage Review

**Date:** 2026-08-26 **Skill:** `standards/markdown-frontmatter/versions/1.13/skills/markdown-frontmatter` **Scope:** Claude Code and Codex historical usage across development repositories **Review mode:** Read-only except for this report

## Executive Summary

The archive holds substantial evidence. Across roughly 3 GB of Claude Code transcripts and 2.2 GB of Codex rollouts, 178 Claude sessions wrote managed frontmatter and ~1,845 Codex rollouts mention `schema_version` (the two predicates differ, and both are stated below), while the skill's own text reached context in 25 Claude sessions and 297 Codex sessions. Twenty-six sessions were extracted into timelines and reviewed in detail; three analysis passes ran over them, including one adversarial pass whose job was to break the findings.

The skill is **correct and largely well-built**. Its prose has been byte-stable since package version 1.2 — only version-pinned URLs changed through 1.13 — so nothing in the corpus is invalidated by version drift, and no session showed the skill giving wrong guidance. Where it was loaded, it worked: it routed a lost agent back to the right command, its controlled-value tables settled `doc_type`/`status` questions without exploration, and the forbidden-path rule was respected in every observed case.

The most important recurring problem is not the skill's content but its **reach**. In the eleven days after Claude Code's discovery defect was repaired (#170, commit `e2d25f21`, 2026-08-15), 22 Claude sessions wrote managed frontmatter and exactly **one** had the skill in context. The repair did not move the load rate — it was 7.7% before and 4.5% after. Codex, which reads `SKILL.md` explicitly with `sed`/`rg`, sits near 15% in the same window. Correctness held anyway, because `project-standards validate` is doing the enforcement work.

The clearest content defect is narrow and fixable: the skill names `format-frontmatter`, `validate-id`, and `validate-frontmatter` without ever saying what they are or where they come from, while its only provenance sentence says `scripts/` is the skill's own directory. Codex agents invented a non-existent `scripts/validate-frontmatter` and a non-existent `project-standards validate-id` subcommand, costing roughly six recovery calls across two sessions.

Several apparent problems are **already fixed** and must not be re-solved: the retired repo-name id convention, the `python3`-shim break in `new-doc-id` (#97), Claude Code's inability to see `.agents/skills/` (#170), and the Codex-only `openai.yaml` copy (#175).

Confidence is **medium-high** on the content findings (F2, F4, F5, F11), **medium** on the reach finding (F1 — the counting predicate is sensitive and the post-fix window is only 22 sessions), and the review explicitly records two findings the verifier **refuted** so a follow-up session does not act on them.

## Bottom Line

1. **The skill is rarely in context when frontmatter is written, and fixing discovery did not change that.** Reconsider whether this package should reach agents the way its three sibling packages do — through an `AGENTS.md`/`CLAUDE.md` marker block — or whether it should accept that the validators carry enforcement and shrink accordingly. Do not do both.
2. **The skill names four commands and explains the provenance of none of them.** This is the one place where its wording demonstrably caused wasted work, twice, on Codex. It is a small edit with a measured payoff.
3. **`--scaffold` — the affordance that emits all eleven fields correctly quoted and ordered — is used in 6 of 240 real invocations (2.5%).** The skill shows the bare form first and buries `--scaffold` third. The corpus does not show this causing failures, but it means the eleven-field block is almost always hand-authored, which is precisely what the skill's longest section exists to police.
4. **One shipped sentence is factually wrong** and contradicts the same package's own agent-summary. Low harm, near-zero cost to correct.
5. **Resist adding instructions.** The verifier flagged four improvement directions that relocate complexity rather than remove it. Two candidate findings were refuted outright.

## Current Skill Model

`SKILL.md` is a 9.6 KB operating layer over the Markdown Frontmatter Standard. It is explicit that it is _not_ authoritative: "the schema is authoritative, not this file," and on conflict the schema and standard pages win.

**Trigger.** Creating or editing a managed Markdown file; recovering from a failed validation run; choosing a controlled value. It carries an equally prominent negative trigger: agent-instruction and agent-skill files (`CLAUDE.md`, `AGENTS.md`, `.claude/`, `.agents/`, `.codex/`) must never carry frontmatter and are excluded through the package's `exclude` option.

**Content.** Eleven required fields in canonical order; the formatting rules that machine-fail (quote every string including dates, block-style non-empty lists, `[]` for empty, no unknown top-level keys, canonical key order); controlled-value tables for `doc_type`/`status`/`confidence`/`visibility`/`consumer`; the id contract; a worked example; four referenced validation commands; a "Common mistakes" table; links to the authoritative pages.

**The id rule is the skill's centre of gravity.** Ids are `{doc_type}-{base36-6}-{document-name}`, and `validate_id.py` requires segment 1 to **equal** the document's own `doc_type` field, not merely be a valid one. The skill forbids inventing the token by hand — "An LLM asked for a 'random' base36 token produces low-entropy, collision-prone strings and reuses tokens already in context" — and ships `scripts/new-doc-id` as the sanctioned source. ADRs are carved out (`adr-{NNNN}-{repo-name}-{title}`) and the script must not be used for them.

**Install surface.** `payload.toml` installs `SKILL.md` and `new-doc-id` as byte-identical digest-locked managed copies to both `.agents/skills/markdown-frontmatter/` (Codex) and `.claude/skills/markdown-frontmatter/` (Claude Code), plus a Codex-only `agents/openai.yaml` gated on the `harnesses` option. A separate 37-line `agent-summary.md` installs to `.standards/packages/markdown-frontmatter/`. The package contributes **only** to `.github/workflows/validate-standards.yml` — no agent-instruction contribution.

## Corpus and Methodology

**Archive.** `/mnt/nas/files/agent-session-data/data/raw`, split into `claude/projects/<slugified-cwd>/<uuid>.jsonl` (plus per-session `subagents/` and `tool-results/`) and `codex/sessions/2026/<MM>/<DD>/rollout-*.jsonl` with `session_index.jsonl` and `archived_sessions/`. 3,667 Claude transcripts, 2,569 Codex rollouts, ~3 GB total.

**Repositories represented.** Claude-side hits appeared in 19 project directories. Substantive: `project-standards` (338 hit files), `agent-configs` (147), `repolens` (21), `doc-proc-scripts` (14), `homelab` (7), `projects` (6), `scripts` (5), `project-feldspar` (5), plus 1–2 each in `remote-execution`, `dotfiles`, `llm-wiki`, `docmend`, `agent-pseudocode`, `social-ventures`, `agent-handoff-v3`, `hw-radar`, `ai-spy`. Codex sessions carrying the skill body resolved to `project-standards` (112), `agent-configs` (91), `llm-wiki` (35), `star-trek-retro-remake` (14), `scripts` (8), `agent-pseudocode` (7), `homelab` (6), `doc-proc-scripts` (6), and a long tail.

**Discovery method.** Anchor greps (`skills/markdown-frontmatter`, `new-doc-id`, `validate-id`, `format-frontmatter`, `doc_type`, `schema_version`, `project-standards validate`), then three purpose-built extractors: a Claude timeline extractor, a Codex rollout extractor, and an id-provenance analyzer that pairs `Write`/`Edit` ids against ids that appeared in earlier tool results. Extracted timelines live under `/tmp/mfreview/ev/` (17 Claude) and `/tmp/mfreview/codex/` (9 Codex).

**Counting predicates — stated because they are sensitive.** "Wrote frontmatter" = a session with at least one `Write`/`Edit`/`MultiEdit` whose input contains both `schema_version` and `1.1`. "Skill in context" = a session containing either `Core principle: the schema is authoritative` (current form, 17 Claude files) or `the schema is authoritative, not this file` (pre-1.2 form, 25 Claude files); the union is what the load counts use. The verifier reproduced 17 for the current-form grep alone and could not reproduce a looser 1,699-file `schema_version` denominator against the narrower 178 — the discrepancy is a predicate difference, not a data error, and both predicates are recorded here so a follow-up can re-derive either.

**Scale reviewed.** ~800 candidate hit files; 26 sessions extracted to timelines and materially reviewed; 240 real `new-doc-id` shell invocations parsed (100 Claude, 140 Codex); corpus-wide tallies for id-prefix rejections, placeholder leakage, and id-type distribution.

**Historical versions.** `SKILL.md` is byte-identical from 1.2 through 1.13 except three version-pinned URLs and one inline version string — verified by direct diff. Two era boundaries matter and are applied throughout: **2026-07-09**, when the packaged repo-local skill replaced a near-identical global skill that documented the retired repo-name id format and the old `validate-frontmatter` CLI / `.project-standards.yml` config; and **2026-08-15**, when the `.claude/skills/` twin landed (`e2d25f21`) and Claude Code could see the skill for the first time. Sessions showing `.project-standards.yml` or `/home/chris/.claude/skills/markdown-frontmatter/` are pre-packaging and are labelled historical.

**Coverage limitations.** Codex rollouts are date-partitioned, not repo-partitioned, so repo attribution required parsing `session_meta` per file; the two largest 2026-07-09 rollouts (515 KB / 374 KB) were sampled, not read end to end. No token counts, context sizes, or latency figures are recorded in either archive, so all cost statements here are tool-call counts or qualitative.

| Sample | Harness | Repo | Date | Why included |
| --- | --- | --- | --- | --- |
| `019fed17` | Codex | project-standards | 2026-08-10 | Two invented-CLI incidents in one session |
| `01a00fb8` | Codex | llm-wiki | 2026-08-17 | Invented skill-local validator; gate caught a real defect |
| `019f569d` | Codex | agent-configs | 2026-08-12 | `SKILL.md` read four times in one session |
| `019f7f43` | Codex | project-standards | 2026-07-20 | Clean end-to-end id generation |
| `6d55f52d` | Claude | scripts | post-1.2 | 46-document backfill; date-derived ids |
| `a8032963` | Claude | project-standards | 2026-08-16 | Post-#170 `Skill` invocation, absolute path, zero discovery cost |
| `db633d23` | Claude | project-standards | pre-07-09 | Placeholder-then-`--fix` workflow |
| `9977270f` | Claude | agent-configs | 2026-07-07/08 | Hand-formed mnemonic ids (historical era) |
| `adb9cde5` | Claude | doc-proc-scripts | 2026-07-07 | Ten-id shell loop (historical era) |
| `b9150781` | Claude | doc-proc-scripts | 2026-07-07 | Discovered the stale global skill; six-doc_type conformance sweep |

## What Works Well

**The skill is correct, and it has been stable long enough to trust.** Byte-identical prose from 1.2 to 1.13 means no session in this corpus was misled by drift, and no reviewed session showed the skill stating something false about the schema. _Why it matters:_ a follow-up session can edit this file without reconciling a decade of variants, and any change is a genuine change rather than a catch-up.

**It functions as a recovery reference when an agent is lost.** In the 2026-08-17 `llm-wiki` session, after guessing a validator that does not exist, the agent listed the skill directory, re-grepped `SKILL.md`, and recovered the correct `project-standards validate` invocation from it (`/tmp/mfreview/codex/rollout-2026-08-17T08-36-13-01a00fb8-*.txt`, L611→L617→L634). The "schema is authoritative" framing pointed it at the right tool. _Why it matters:_ the Validate section earns its place even though its wording caused the original wrong turn — a recommendation that deletes it would regress the recovery path.

**The deterministic gate catches real defects and agents credit it.** The same session's `project-standards validate` run rejected a date-shaped id on a freshly authored companion document, and the agent explicitly attributed the catch to "the authoritative frontmatter gate" (L696). _Why it matters:_ enforcement is already deterministic. That is the strongest argument for keeping the skill small.

**The forbidden-path rule held everywhere it was tested.** No reviewed session added frontmatter to `CLAUDE.md`, `AGENTS.md`, or anything under `.claude/`, `.agents/`, `.codex/`. One 2026-08-16 session explicitly weighed whether a packaged `SKILL.md`'s own Agent-Skills manifest header conflicted with the prohibition and resolved it correctly (manifest header ≠ managed-document profile) — but only after several turns of reasoning. _Why it matters:_ the prohibition works; the manifest-vs-profile distinction is the one place agents have had to derive it themselves.

**Controlled-value tables removed exploration.** Across the reviewed sessions no agent searched the schema to decide a `doc_type` or `status` value once the skill was in context, and the README/index and `docs/research/` mappings were applied directly. _Why it matters:_ these tables are cheap and load-bearing; do not trade them away in a simplification pass.

**The `new-doc-id` script header is a second, working documentation surface.** Its first 48 lines carry the ADR carve-out, the entropy rationale, and the `#97` `uv run --no-project` dispatch rationale. An agent that `head`s the script gets correct guidance without `SKILL.md` at all — observed in the `scripts` backfill session. _Why it matters:_ shipping an executable with a substantive header is doing real work, and a consolidation pass should route toward it rather than duplicate it.

**When the `Skill` tool does fire, path discovery costs nothing.** Claude Code's launch output begins "Base directory for this skill: `<absolute path>`", so post-#170 sessions invoked `…/.claude/skills/markdown-frontmatter/scripts/new-doc-id` immediately with no `find` or `ls` (`/tmp/mfreview/ev/…project-standards_a8032963-*.txt`, L34→L248). _Why it matters:_ the discovery problem is about the skill firing at all, not about what happens afterwards.

## Findings

Findings are numbered as they were carried into verification, and refuted ones are retained under their original numbers so a follow-up session does not rediscover and re-act on them.

### F1 — The skill is almost never in context when frontmatter is written, and repairing discovery did not change that

**Severity/Impact:** High **Confidence:** Medium **Evidence breadth:** corpus-wide counts, both harnesses, 19 Claude project directories

#### Observation

Claude Code, whole archive: 178 sessions wrote managed frontmatter; 25 sessions anywhere contained the skill body. Split at the #170 repair date (2026-08-15): **before**, 156 sessions wrote frontmatter and 12 of them also had the skill body (7.7%); **after**, 22 sessions wrote frontmatter and **1** had it (4.5%). Only two sessions in the entire archive loaded the skill more than once.

Codex reads the file explicitly and loads it more often, but still in a minority of relevant sessions: in the 2026-08-15 → 08-26 window, 117 rollouts mention `schema_version` and 17 contain the skill body (~15%). Of the 297 Codex sessions carrying the skill body across the archive, 203 (68%) are in `project-standards` or `agent-configs`, where `SKILL.md` is a source file being edited rather than guidance being consumed — genuine consumer-repo loads are ~94.

Structural cause candidate, verified: `markdown-frontmatter@1.13`'s `payload.toml` declares contributions **only** to `.github/workflows/validate-standards.yml`. Every sibling skill-shipping package contributes a marker block to both `AGENTS.md` and `CLAUDE.md` — `agent-handoff@1.15` (`payload.toml:345,357`), `markdown-tooling@1.15` (`:341,349`), `github-workflow@1.5` (`:227,236`), `python-tooling@1.15` (`:848,856`). A consumer repo therefore gives agents no ambient statement that frontmatter rules exist.

#### Evidence

Corpus-wide predicate counts (predicates stated in Corpus and Methodology, reproducible). Per-repo load distribution from `session_meta` parsing. Payload comparison across five packages.

#### Analysis

_Observation:_ the load rate is low on both harnesses and did not rise after the discovery fix. _Inference:_ attributable to the **skill's reach**, not its content — the content was fine in every session that had it. The verifier correctly noted that #170 made the skill structurally undiscoverable to Claude Code for most of the measured window, and that attributing the whole gap to the contributions asymmetry would blame the current version for a fixed defect. The post-2026-08-15 recomputation was run specifically to answer that: **the repair did not raise the rate.** The verifier also noted that `SKILL.md`'s `description:` field is itself Claude Code's discovery surface — true, and it means the skill is _listed_; the data says being listed is not sufficient to get it _invoked_.

Codex's higher rate is a harness difference: Codex agents open `SKILL.md` with `sed`/`rg` as an explicit act, which is more reliable than model-judged auto-invocation but costs a tool call each time.

#### Cost/Consequence

The skill's operating layer is absent from ~95% of the work it governs on Claude Code. That is not currently producing defects — `project-standards validate` catches what matters — but it means the file's ~180 lines are being maintained for a small fraction of the sessions they target, and any future rule added to it inherits the same reach.

#### Improvement Direction

Change the trigger, or accept the reach and shrink the file. Two coherent options, and they are alternatives, not a package: (a) add an agent-instruction contribution matching the three sibling packages, giving both harnesses an ambient pointer; (b) accept that the validators enforce, and reduce `SKILL.md` to the rules that are _not_ machine-checkable. Measuring first is cheap: the post-fix window is only 22 Claude sessions and eleven days.

#### Tradeoff / Regression Risk

Option (a) adds a permanently-rendered managed block to two files in every consumer repo — the verifier flagged this as relocating the pointer problem rather than removing it, and it partially duplicates what Claude Code's skill listing already provides. Option (b) risks removing guidance whose absence would only show up as validation failures later; the skill's "Formatting rules that actually fail validation" section is load-bearing precisely because `--scaffold` is barely used (F11). The post-fix window is small enough that the measured rate could shift.

### F2 — The skill names four commands and explains the provenance of none of them, and agents invent CLI that does not exist

**Severity/Impact:** High **Confidence:** High **Evidence breadth:** 2 Codex sessions, 3 distinct incidents, ~6 wasted calls

#### Observation

`SKILL.md` references `project-standards validate`, `format-frontmatter --check`, `validate-id <file>`, and `validate-frontmatter` (line 24) without stating that the latter three are **separate console scripts** installed by the `project-standards` distribution (`pyproject.toml` `[project.scripts]`), not subcommands and not skill-local files. Its only provenance statement is line 94: "`scripts/` is this skill's own directory."

Three incidents follow directly from that gap:

1. `uv run project-standards validate-id <file>` → `error: argument command: invalid choice: 'validate-id' (choose from validate, fix, spec, standards, packages, agent-handoff, init, reconcile, render, mcp, adopt, list)`, EXIT=2. One recovery call.
2. `.agents/skills/markdown-frontmatter/scripts/validate-frontmatter <file>` — a script that has never shipped. Recovery took an `rg --files` of the skill directory, a re-grep of `SKILL.md`, and three further attempts before landing on `project-standards validate`: roughly five calls.
3. `new-doc-id --doc-type research --title '…' --created 2026-08-11` — invented flags. The script accepts only `--scaffold`, `--doc-type`, `--status`, and a positional name. Corrected on the next call.

#### Evidence

`/tmp/mfreview/codex/rollout-2026-08-10T15-12-27-019fed17-*.txt` L4700 (invented flags), L4706 (correction), L4826→L4828 (invalid subcommand with exit code). `/tmp/mfreview/codex/rollout-2026-08-17T08-36-13-01a00fb8-*.txt` L605 (invented script), L611, L617, L634, L657, L681 (recovery chain). CLI surface confirmed against `pyproject.toml` and `src/project_standards/cli.py`.

#### Analysis

_Observation:_ three invented invocations across two sessions. _Inference:_ attributable to **the skill itself**, not ordinary model error. The skill presents `project-standards validate` as the aggregate that "runs schema validation, ID-format validation, and reference validation" and then names `validate-id` bare in the next paragraph — reading it as a sibling subcommand is the natural inference. Symmetrically, having declared `scripts/` to be the skill's own directory and shipped one executable there, looking for a second executable in the same place is the natural inference. `validate-frontmatter` _is_ a real console script, which makes the conflation more, not less, likely.

The verifier independently confirmed both incidents verbatim, judged the traceability "direct, not ordinary model error," and found the 08-17 cost higher than first estimated. Both harnesses are exposed; the observed incidents are Codex-side, plausibly because Codex reads the file more often (F1).

#### Cost/Consequence

~6 wasted tool calls across two sessions, plus the reasoning turns around them. Small per incident, but it recurs whenever an agent tries to validate a single file rather than run the aggregate — a common shape.

#### Improvement Direction

Clarify provenance in one line: state that `validate-id`, `format-frontmatter`, and `validate-frontmatter` are console scripts installed with the `project-standards` package, that `scripts/` holds `new-doc-id` and nothing else, and show the invocation form the repository actually uses. Alternatively, drop the single-file commands and name only `project-standards validate`, pushing the rest to the standard pages.

#### Tradeoff / Regression Risk

Naming the invocation form risks staleness if the repository's runner convention changes — the observed sessions used `uv run` and `PYTHONPATH=…/build/wheel-runtime`, which are repository-local, not package-general. Dropping the single-file commands removes a genuinely useful narrow gate and would regress the recovery path documented in _What Works Well_.

### F3 — REFUTED: the relative `scripts/new-doc-id` path in the usage block

**Severity/Impact:** — **Confidence:** High (in the refutation) **Evidence breadth:** 26 extracted timelines

#### Observation and refutation

The candidate finding held that the skill's usage block shows an un-runnable relative path and that this caused an observed failure. It does not. The cited failure (`/tmp/mfreview/ev/-home-chris-scripts_6d55f52d-*.txt` L551–L563) invoked `.agents/skills/markdown-frontmatter/scripts/new-doc-id` — a repo-root-relative path, not the skill's form — and failed because the file did not exist yet; the agent's own reasoning names the cause ("the reconcile plan indicated that a new doc ID script _should be created_ … this might be a planned action that didn't go through"). A search across all 26 extracted timelines found **zero** invocations of a bare relative `scripts/new-doc-id`. The parenthetical mitigation — "invoke by absolute path if your cwd is elsewhere" — appears to be working.

#### Improvement Direction

None. Recorded so a follow-up session does not edit line 94 on this basis.

### F4 — The install-path statement is stale and contradicts the package's own agent-summary

**Severity/Impact:** Low **Confidence:** High **Evidence breadth:** static, verified in both directions

#### Observation

`SKILL.md:17` states the skill "is installed repo-local at `.agents/skills/markdown-frontmatter` … That path is deliberate: both Claude Code and Codex CLI can discover it without a global skill owner." `payload.toml:269–271`, citing #170, states the opposite: "Claude Code discovers project skills only under `.claude/skills/`; it has **never** read `.agents/skills/`" — and installs byte-identical copies to both trees. `artifacts/agent-summary.md:28` describes the dual install correctly. All three ship inside version 1.13.

#### Evidence

Direct reads of the three files; `e2d25f21` (2026-08-15) as the commit that introduced the twin.

#### Analysis

_Observation:_ an intra-version factual contradiction. _Inference:_ attributable to the **historical fix having landed in the payload without a corresponding prose edit** — the skill body was not touched by `e2d25f21` because it is byte-locked and shared by both install targets. No behavioral incident was found. The verifier confirmed the contradiction and correctly narrowed the sub-claim: the forbidden-paths rule at `SKILL.md:27` already covers "anything under `.claude/`, `.agents/`, `.codex/`" generically, so the `.claude/` twin is protected; only the illustrative "That includes this installed skill at `.agents/…`" is stale.

#### Cost/Consequence

No measured cost. The latent risk — an agent "deduplicating" what looks like an accidental copy — is guarded by digest-locked managed artifacts and by the agent-summary's explicit "neither copy may be edited or deleted to deduplicate them."

#### Improvement Direction

Correct one sentence to match the agent-summary. Near-zero cost, removes a shipped contradiction.

#### Tradeoff / Regression Risk

None material. Any edit re-cuts the payload digest for both install targets.

### F5 — The placeholder token `xxxxxx` is schema-valid, and the package itself seeds it

**Severity/Impact:** Low–Medium **Confidence:** High on mechanism, Medium on impact **Evidence breadth:** 3 sessions, plus static analysis of shipped artifacts

#### Observation

`providers/frontmatter.py:31` defines `_TOKEN = re.compile(r"^[0-9a-z]{6}$", re.ASCII)`. `x` is a base36 digit, so `xxxxxx` passes id validation. Document-specific ids retaining the placeholder appear in three sessions (`reference-xxxxxx-project-specification-standard`, `runbook-xxxxxx-project-specification-standard-adoption-procedure`, `reference-xxxxxx-tool-name-command-reference`, `reference-xxxxxx-spec-template-tooling-notes`).

The verifier reframed the source, correctly and more sharply than the original finding: `xxxxxx` is **the package's own shipped placeholder**, not an agent invention. It appears at `SKILL.md:36`, in `structure.md:14,34`, `field-values.md:12`, and in every shipped template (`templates/note.md:3`, `concept.md:3`, `spec.md:3`, `runbook.md:3`, `research.md:3`, `frontmatter-minimal.yml:3`, `frontmatter-standard.yml:3`, `repo-pages/README.directory.template.md:3`). An agent copying the skill's own required-fields block gets a schema-valid placeholder.

#### Evidence

Static reads of the provider, skill, standard pages, and templates. Session hits in `claude/projects/-home-chris-projects-project-standards/db633d23-*.jsonl`, `codex/sessions/2026/07/13/rollout-…019f5b91-*.jsonl`, `codex/sessions/2026/08/10/rollout-…019fec51-*.jsonl`.

#### Analysis

_Observation:_ the placeholder is valid, shipped, and reaches real document slugs. _Inference:_ the mechanism is real but the impact is bounded. In the Claude case the agent wrote the placeholder deliberately and cleared all three with a single `uv run validate-id --fix` before a clean validate run — a sanctioned use of the tooling, and that session predates packaging (it runs against `.project-standards.yml`). No placeholder id was observed surviving into a commit; every repository occurrence is inside a fenced example, a template, or a transcript. The original finding's framing — "agents invent it, nothing catches it" — is overstated.

#### Cost/Consequence

No observed escape. The residual is that the one class of id error the validator structurally cannot see is the one the package's own exemplars propagate.

#### Improvement Direction

A deterministic option exists: make the shipped placeholder token _invalid_ by construction (a form outside `[0-9a-z]{6}`) so any copy fails loudly, instead of teaching the validator a blocklist. This is a package-artifact change, not a skill change.

#### Tradeoff / Regression Risk

The verifier's warning is decisive here: tightening `_TOKEN` to reject `xxxxxx` would invalidate the package's own templates and documentation examples — breaking the artifacts before catching any agent. Any change must move the exemplars first. Changing the placeholder also churns eight shipped files for a defect with no observed escape; the priority should reflect that.

### F6 — REFUTED: hand-invented low-entropy ids under the current skill

**Severity/Impact:** — **Confidence:** High (in the refutation) **Evidence breadth:** 3 cited examples, all falsified

#### Observation and refutation

The candidate finding held that agents still hand-invent low-entropy tokens despite the skill's strongest prohibition, citing `index-abc123-research-index`, `index-ad0001-adr`, and `index-de0001-decisions`. All three fall:

- `index-abc123-research-index` is not a document id. It is golden-test fixture data, labelled "mutated golden" in the transcript, for a Go binary-parity test.
- `index-ad0001-adr` and `index-de0001-decisions` were written into a real file, but that session (`agent-configs/9977270f`) reads and edits `.project-standards.yml` — it is pre-2026-07-09, before the packaged skill existed — and the agent's own reasoning shows deliberate conformance to a pre-existing repo-local mnemonic convention ("a 2-letter mnemonic followed by a 4-digit sequence … the repo's convention uses patterns like `index-dr0001-docs`"), not a failed attempt at randomness.

The broader id-provenance sweep that produced these candidates used a regex that also matches ordinary kebab slugs whose second segment happens to be six characters (`plan-format-legacy`, `spec-review-r1`), so its "handmade" bucket is not reliable evidence.

#### Improvement Direction

None. The entropy prohibition at `SKILL.md:94` is not implicated by the evidence. Recorded to prevent a follow-up session from strengthening a rule that is not failing.

### F7 — WEAKENED: one id per invocation and batching workarounds

**Severity/Impact:** Low **Confidence:** Medium **Evidence breadth:** 2 sessions, both pre-packaging

#### Observation

`new-doc-id` emits one id per call. Agents batch with shell loops — one call minting ten ids (`S=…/new-doc-id; for n in <ten names>; do printf '%s → ' "$n"; $S "$n"; done`) and a chained five-call form elsewhere. A second batching route also appears: write `xxxxxx` placeholders, then one `validate-id --fix`.

#### Evidence

`/tmp/mfreview/ev/…doc-proc-scripts_adb9cde5-*.txt` L180, L253, L274; `…homelab_ba335183-*.txt` L290; `…project-standards_db633d23-*.txt` L163–L167, L926.

#### Analysis

_Observation:_ batching happens. _Inference:_ it is a cheap adaptation, not a defect. The verifier established that both batching sessions invoke `/home/chris/.claude/skills/markdown-frontmatter/scripts/new-doc-id` and quote the retired usage text ("bare id, repo name from git root") — pre-2026-07-09 evidence — and that the loop was a single successful Bash call with no error, retry, or diagnostic turn. The only durable observation is documentary: `validate-id --fix` as a bulk id-minting route is used but not mentioned in the skill.

#### Cost/Consequence

One tool call. No measured harm.

#### Improvement Direction

At most, one sentence naming `validate-id --fix` as the bulk path. Do not add batch flags.

#### Tradeoff / Regression Risk

The verifier flagged batch-mode as a net complexity increase — argument parsing, output formatting, and a second usage contract on a script whose current cost is one shell loop. Agreed.

### F8 — CANNOT-DETERMINE: duplication between `SKILL.md` and the installed `agent-summary.md`

**Severity/Impact:** Unknown **Confidence:** Low **Evidence breadth:** static overlap confirmed; no usage evidence either way

#### Observation

The two documents overlap substantially: both restate the eleven required fields, the quoting and list rules, the id format, the ADR exception, the forbidden paths, and the command set (`SKILL.md:27,31–49,55–57,84–104,140–156` vs `agent-summary.md:13–17,21–26`). A consumer repo carries both, on top of the upstream `README.md` + `structure.md` + `field-values.md` (~850 lines).

#### Evidence

Direct reads. No session in the extracted set reads both; the only evidence-file hits for the installed `agent-summary.md` path are reconcile install-plan output, not reads.

#### Analysis

_Observation:_ real textual overlap. _Inference — and it is only inference:_ the two may serve different trigger points (package-level orientation vs invocation-time operating layer), which the verifier judged a plausible non-defect explanation it could not rule out. Notably, only `agent-summary.md` states the dual-install rule correctly (F4).

#### Cost/Consequence

Unmeasured. Maintenance burden is real — a rule change must be reflected in two managed artifacts plus two standard pages.

#### Improvement Direction

Measure before acting: count sessions whose context contains both bodies. Do not deduplicate on structural grounds alone.

#### Tradeoff / Regression Risk

The verifier's objection stands: deduplicating would either strip the operating layer that F2 shows agents recover from, or push ~180 lines into an ~850-line corpus — relocating rather than removing, and requiring a new cross-artifact single-source mechanism plus a digest-sync rule between two differently-targeted managed artifacts.

### F9 — WEAKENED: subagents write frontmatter without the skill in context

**Severity/Impact:** Low **Confidence:** Low **Evidence breadth:** many subagent transcripts; no defect linkage

#### Observation

A large share of `Write`/`Edit`s carrying `schema_version` occur in `<uuid>/subagents/*.jsonl` transcripts with no skill body present.

#### Analysis

_Observation:_ true. _Inference:_ not attributable to the skill. For nearly the whole archive window Claude Code could not load the skill from `.agents/skills/` at all (#170), and subagents inherit briefing from an orchestrator — skill preloading is an orchestrator property, not something `SKILL.md` can assert about itself. Neither the primary analysis nor the verifier found a linkage from any skill-absent subagent write to an actual validation defect.

#### Improvement Direction

None for the skill. If pursued, this belongs to the orchestrator-dispatch discipline, not this package.

#### Tradeoff / Regression Risk

n/a. Settling it would require, per subagent write, whether a later parent-session validate flagged that file.

### F10 — WEAKENED: `validate-id` prefix rejections, and what actually causes them

**Severity/Impact:** Low **Confidence:** Medium **Evidence breadth:** corpus tally, 7 instances traced

#### Observation

Corpus-wide tally of rejections, excluding the skill's own `'<x>'` example text: `'doc'` ×38, `'2026'` ×30, `'agent'` ×9, `'network'` ×8, `'madr'` ×6, `'greenfield'` ×6, `'frontmatter'` ×6, then singles (`'my'`, `'python'`, `'restore'`, `'synthetic'`, `'batch'`, `'architecture'`, `'append'`).

#### Analysis

_Observation:_ the tally is real. _Inference:_ it does not support "the skill fails to warn about date-shaped ids." Every instance the verifier could reach contradicts the new-authoring premise. All three reachable `'2026'` rejections are a one-shot **bulk backfill of pre-existing legacy documents** in `/home/chris/scripts`, where a migration helper derived ids from `YYYY-MM-DD-*.md` filenames — a script bug in a migration, not per-document authoring the skill could intercept. All four reachable `'agent'` rejections are **deliberate control tests** proving the retired repo-name format fails ("Confirmed: old format fails (exit 1, 'prefix agent is not a valid doc_type'), new format passes"); `'agent'` is itself the `agent-configs` repo-name prefix, the same retired-convention class as `'doc'` ×38. The tally excludes the skill's example text but not migration noise or intentional negative tests, so "genuine rejections" is not established. The remaining 27 `'2026'` and 5 `'agent'` instances live only in the raw archive and were not classified.

The positive counterpart survives intact and is evidence _for_ the current tooling: the 2026-08-17 `llm-wiki` gate catch of a date-shaped id on a fresh document.

#### Cost/Consequence

None attributable to the skill.

#### Improvement Direction

None on this evidence. If a warning is ever added, it belongs to bulk-migration tooling, not the authoring skill.

### F11 — `--scaffold`, the strongest defect-prevention affordance, is used in 2.5% of invocations

**Severity/Impact:** Medium **Confidence:** High on the measurement, Medium on the consequence **Evidence breadth:** 240 real invocations, both harnesses

#### Observation

Parsing every real shell invocation of `new-doc-id` in the archive — 100 Claude Bash calls, 140 Codex shell calls:

| Form              | Claude | Codex | Combined |
| ----------------- | ------ | ----- | -------- |
| Total invocations | 100    | 140   | 240      |
| with `--scaffold` | 4      | 2     | 6 (2.5%) |
| with `--doc-type` | 21     | 15    | 36 (15%) |
| with `--status`   | 5      | —     | 5        |

`--scaffold` emits all eleven required fields in canonical order with today's date correctly quoted and `[]` empties — exactly the class `SKILL.md:51–57` calls "the machine-checked rules an agent skips by habit." It is used in 6 of 240 calls. The other 234 produce a bare id, and the eleven-field block is hand-authored.

A related measurement, reported here because it looked like a defect and is not: `validate_id.py` requires the id prefix to **equal** the document's own `doc_type` field, and 85% of invocations omit `--doc-type` (defaulting to `note`), while `note` accounts for only ~21% of id occurrences in the corpus. A grep for the mismatch message — `prefix '<x>' does not match the document's doc_type '<y>'` — returns **zero** occurrences corpus-wide. Agents evidently pass `--doc-type` when it matters or correct the id before validating. The risk is latent, not realized, and should not be reported as a live defect.

#### Evidence

`/tmp/mfreview/inv-claude.jsonl` and `/tmp/mfreview/inv-codex.jsonl` (extracted invocation corpora). `src/project_standards/validate_id.py:163–210` for the prefix-equality rule and its exact message. Corpus id-prefix distribution: `note` 2,449, `index` 2,317, `reference` 2,187, `runbook` 1,678, `spec` 990, `research` 787, `log` 516, `plan` 452, `decision` 198, `prompt` 72, `concept` 67, `template` 56 (occurrences, not unique documents).

#### Analysis

_Observation:_ `--scaffold` adoption is ~2.5%. _Inference:_ attributable to the skill's **presentation order** — the usage block shows the bare form first, `--doc-type` second, `--scaffold` third, and the surrounding prose treats id generation as the problem rather than block generation. The verifier independently flagged `--scaffold` adoption as "the single most decision-relevant missing measurement"; this closes that gap.

The consequence is a reframing rather than a defect: the skill's longest section exists to police hand-authored frontmatter, and hand-authored frontmatter is what agents produce, because the affordance that would make that section unnecessary is buried.

#### Cost/Consequence

Every non-scaffolded document is an opportunity for the quoting, ordering, and empty-list errors the skill enumerates. No count of such errors surviving to a commit was established — the validators catch them — so the realized cost is validate→fix cycles, not defects.

#### Improvement Direction

Lead with `--scaffold` in the usage block and demote the bare-id form, or state plainly that `--scaffold` is the default path for a new document and the bare form is for repairing an existing one. This is a reordering, not an addition.

#### Tradeoff / Regression Risk

Low. The risk is that `--scaffold`'s output still needs the `REPLACE:` description placeholder filled in, so promoting it without keeping that warning adjacent could trade one placeholder problem for another — note the family resemblance to F5.

## Cross-Session Patterns

**Claude and Codex consume the skill differently, and the difference is structural.** Codex opens `SKILL.md` explicitly with `sed`/`rg` — deliberate, reliable, and it costs a tool call each time, including four separate reads in one 2026-07-12 `agent-configs` session. Claude Code relies on model-judged `Skill` auto-invocation, which fires rarely (F1) but, when it does, supplies the absolute base directory for free. Neither mode is clearly better: Codex pays predictably, Claude pays nothing but usually does not load at all. Any change to the skill should be checked against both consumption modes, because a fix that helps one (an `AGENTS.md` pointer for Codex) does little for the other.

**Era matters more than any single finding.** Three candidate findings (F5, F6, F7) rested on sessions that turned out to predate the packaged skill — identifiable by `.project-standards.yml` or a `/home/chris/.claude/skills/markdown-frontmatter/` path. The archive's centre of mass is July 2026, which is precisely the transition window. Any future analysis of this corpus should partition on the 2026-07-09 and 2026-08-15 boundaries _before_ tallying anything.

**Correctness is not the problem; reach and provenance are.** Across 26 reviewed sessions, not one produced a wrong frontmatter block that survived. The failures were all navigational — which command, which path, which flag — and the aggregate validator resolved the substantive errors. This mirrors the sibling `github-workflow` review's F9 ("Correctness is not the problem") and suggests the same conclusion: the marginal value of more rules in the skill is low, and the marginal value of clearer wayfinding is high.

**Authoring repositories dominate the hit counts and must be excluded from consumption metrics.** 68% of Codex skill-body loads and the largest Claude hit counts come from `project-standards` and `agent-configs`, where `SKILL.md` is a file being edited. Raw grep counts over this archive overstate consumption by roughly 3×.

## Token and Workflow Efficiency

**Measurable cost.**

- ~6 wasted tool calls across two Codex sessions from invented CLI (F2): one for the invalid subcommand, one for invented flags, ~4–5 for the non-existent validator recovery chain.
- Four separate `SKILL.md` reads in one Codex session (2026-07-12, `agent-configs`), each bundled with other skills' `SKILL.md` in one combined `sed` — the ~9.6 KB body entering context four times. Whether this was re-verification after edits or pure waste could not be established.
- Repeated loads are otherwise rare: only 2 Claude sessions in the whole archive loaded the skill twice or more.

**Inferred cost.**

- The dominant inefficiency is inverted from what a skill review usually finds: the file is not loaded _too much_, it is loaded almost never (F1). There is no measurable token waste from over-loading to remove.
- 234 of 240 `new-doc-id` invocations produce a bare id and leave the eleven-field block to be hand-authored (F11). Each hand-authored block is a candidate for a validate→fix cycle that `--scaffold` would have prevented. No count of realized cycles was established.
- No evidence of the skill driving excessive exploration, unnecessary subagents, or forced serialization. No session read the ~850-line standard pages when the skill would have sufficed.

**Actions better handled deterministically.** Enforcement already is: `project-standards validate` is the load-bearing gate, agents credit it by name, and it caught the one substantive authoring defect in the reviewed set. The one gap where determinism is absent is the placeholder token (F5), and the deterministic fix there is to change the shipped exemplar, not to add a validator rule.

## Missed or Inappropriate Invocations

**Probably should have been used but was not.** This is the archive's dominant pattern (F1): 21 of 22 post-#170 Claude sessions that wrote managed frontmatter did so without the skill. The strongest single instance is the `/home/chris/scripts` backfill, where a migration helper derived ids from `YYYY-MM-DD-*.md` filenames and produced the `'2026'` prefix rejections — the skill's id section addresses exactly that, and it was not in context when the helper was written.

**Used but added little.** The 2026-07-13 `project-standards` Codex session touched `markdown-frontmatter` only through comparative `rg` searches across standard versions — an audit, not authoring. Loading the skill there would have added nothing, and the agent correctly did not.

**Trigger rules.** The negative trigger is precise and worked in every observed case. The positive trigger ("Creating or editing a managed Markdown file") is accurate but does not fire in practice on Claude Code, which is F1. One boundary the trigger does not address: whether a packaged `SKILL.md`'s own Agent-Skills manifest header falls under the "never carry frontmatter" prohibition. One 2026-08-16 session had to reason that out (manifest header ≠ managed-document profile) rather than read it.

## Historical Issues Already Resolved

Do not re-solve these.

| Issue | Problem | Resolved |
| --- | --- | --- |
| Retired id convention | The global skill documented `{repo-name}-{base36}-{slug}`; v4's `validate-id` rejected it (`prefix 'doc' is not a valid doc_type` ×38, `'agent'` ×9). A 2026-07-07 `doc-proc-scripts` session hit it on its first generated id, rewrote 15 ids with `validate-id --fix`, and escalated the stale skill. | Skill and script rewritten 2026-07-07/08; packaged into the standard 2026-07-09 (`6634b9f4`, ADR 0016). The `agent-configs` source copy was retired. |
| #97 | The `uv-strict-python` shim this project's own guidance prescribes rejects a bare `python3` and exits 1, so `new-doc-id` — the _only_ sanctioned id source — could not run in a correctly configured environment. Editing the installed copy was no escape: it is lock-owned. | Both embedded Python steps dispatch through `uv run --no-project python3` when `uv` is present, plain `python3` otherwise. Landed in 1.10. |
| #170 | Claude Code discovers project skills only under `.claude/skills/` and has never read `.agents/skills/`, so the packaged skill was invisible to Claude Code. | Byte-identical digest-locked twins installed to both trees (`e2d25f21`, 2026-08-15). Copies, not symlinks — a symlink checks out as a plain text file on a Windows clone without Developer Mode. **Note:** the prose fix did not follow; see F4. |
| #175 | `agents/openai.yaml` is a Codex-only descriptor, but an unconditional `.claude/skills/…/agents/openai.yaml` copy shipped to a harness that cannot read it. | Typed `harnesses` option gates the sidecar; cut in 1.13 (`66056c29`, 2026-08-26). |
| Legacy config surface | Pre-packaging sessions used `.project-standards.yml` and standalone `validate-frontmatter` as the primary entry point. | Superseded by `.standards/config.toml` and the aggregate `project-standards validate`. The skill's current text is correct on both. |

## Improvement Opportunities

| Priority | Related finding(s) | Opportunity | Expected benefit | Risk | Evidence strength |
| --- | --- | --- | --- | --- | --- |
| 1 | F2 | State the provenance of `validate-id`, `format-frontmatter`, and `validate-frontmatter` (console scripts of the `project-standards` distribution), and that `scripts/` holds `new-doc-id` alone | Removes the only wording demonstrably shown to waste calls; ~6 calls across 2 sessions | Naming a repository-local invocation form could go stale | High — 3 incidents, exit codes captured, verifier-confirmed |
| 2 | F11 | Reorder the `new-doc-id` usage block to lead with `--scaffold`; frame the bare form as the repair path | Raises use of the affordance that pre-satisfies the skill's longest section; reordering, not addition | Must keep the `REPLACE:` description warning adjacent, or it trades one placeholder problem for another (cf. F5) | High on the 2.5% measurement; medium on the consequence |
| 3 | F1 | Decide the reach question deliberately: either add an agent-instruction contribution like the three sibling packages, **or** accept validator-carried enforcement and shrink `SKILL.md` to non-machine-checkable rules. Not both | Either closes a 95% reach gap or stops maintaining prose for sessions that never see it | (a) adds a managed block to two files per consumer repo and partly duplicates Claude's skill listing; (b) risks removing guidance whose absence surfaces later | Medium — counts are predicate-sensitive; post-fix window is 22 sessions over 11 days |
| 4 | F4 | Correct the install-path sentence to match `agent-summary.md` | Removes a shipped intra-version contradiction | None material; re-cuts the payload digest for both targets | High — static, verified both ways |
| 5 | F11, trigger | Add one line distinguishing a `SKILL.md` Agent-Skills manifest header from the managed-document profile the prohibition targets | Removes a boundary agents have had to derive mid-task | Adds a line to a file that should be shrinking | Low–medium — 1 session, resolved correctly but slowly |
| 6 | F5 | Make the shipped placeholder token invalid by construction so a copied exemplar fails loudly | Closes the one id error the validator structurally cannot see | Must move all shipped exemplars first; tightening `_TOKEN` alone breaks the package's own templates. Eight files churn for a defect with no observed escape | Medium on mechanism; low on realized impact |
| 7 | F7 | Mention `validate-id --fix` as the bulk id-minting route | Documents a route agents already use | One more sentence | Low — 2 sessions, both pre-packaging |
| — | F8 | Measure sessions carrying both `SKILL.md` and `agent-summary.md` bodies before considering deduplication | Would settle a real maintenance-burden question | Deduplicating on structural grounds relocates ~180 lines into an ~850-line corpus | Insufficient — no usage evidence either way |
| — | F3, F6 | **Take no action.** Both refuted | Avoids spending change budget with no defect behind it | Acting would edit text the evidence does not implicate | Refuted with high confidence |

## Independent Verification

**Scope.** A separate read-only `verifier` (opus/medium, roster pin, no model override) received the skill, the payload, the agent-summary, both extracted evidence corpora, raw-archive access, and all ten candidate findings with instructions to refute rather than confirm. Its `Bash` is default-deny under the repository command guard, so all its counts were single `grep` invocations; one `for`-loop grep was denied and reformulated.

**Confirmed.** F2 — both invented-CLI incidents verified verbatim with exit codes, and judged _stronger_ than stated (the 08-17 recovery cost ~5 calls, not the ~3 first estimated), with traceability to wording called "direct, not ordinary model error." F4 — the contradiction verified literally in all three files. F5 — the `_TOKEN` regex and placeholder mechanism confirmed.

**Challenged, and the challenges were upheld.** F5's session framing (the placeholder was deliberate and cleared by `--fix`; no commit escape; the session is pre-packaging). F7's evidence era and cost (global-skill era; one successful call, no harm). F10's tally (contaminated by bulk-migration noise and deliberate control tests). F9's attribution (orchestrator briefing, not skill). F4's forbidden-paths sub-claim (the generic `.claude/` prohibition already covers the twin).

**Removed.** F3 and F6 were refuted with specific counter-evidence — a misread invocation path with the agent's own stated cause, zero corpus instances of the form the finding blamed, a golden-test fixture mistaken for a document id, and a pre-packaging session following a documented repo-local convention. Both are retained above as refutations so the work is not repeated.

**Added by the verifier and incorporated.** The `--scaffold` adoption gap was flagged as "the single most decision-relevant missing measurement" — measured afterwards and promoted to F11. The `new-doc-id` script header was identified as a load-bearing documentation surface the primary analysis had ignored. The 08-17 recovery loop was reframed as _positive_ evidence (the skill worked as the recovery reference). Era contamination was identified as systemic rather than per-finding, and drove the F1 recomputation.

**Disagreement, resolved by measurement.** The verifier argued F1's causal inference was confounded: #170 made the skill undiscoverable to Claude Code for most of the window, so a low load rate could not be attributed to the contributions asymmetry. That objection was correct in principle and prompted a split at 2026-08-15. The data does not support it as a full explanation — the rate was 7.7% before and 4.5% after, so repairing discovery did not raise consumption. F1 stands, at Medium confidence rather than High, with the small post-fix window recorded as its main weakness.

**Unresolved.** The verifier reproduced 17 files for the current-form skill-sentence grep but not the 25 used in the load counts (a union with the pre-1.2 form), and could not reproduce the 178-session denominator within budget against its own looser 1,699-file `schema_version` count. Both predicates are stated verbatim in Corpus and Methodology so either can be re-derived; the reproduction gap itself remains open. F8 is unresolved in both directions. 27 of 30 `'2026'` and 5 of 9 `'agent'` rejections remain unclassified in the raw archive.

## Recommendations for Follow-Up

1. **Fix the tooling provenance (F2).** _Target:_ agents inventing `project-standards validate-id` and `scripts/validate-frontmatter`. _Outcome:_ an agent that needs a single-file check reaches a working command on the first try. _Change surface:_ the Validate section of `SKILL.md`, roughly two sentences; re-cut the payload digest for both install targets. _Evidence:_ 3 incidents, 2 Codex sessions, exit codes captured, verifier-confirmed. _Validation after:_ confirm the named commands exist in `pyproject.toml` `[project.scripts]` and that no repository-local runner detail is baked in.

2. **Lead with `--scaffold` (F11).** _Target:_ 234 of 240 invocations producing a bare id and leaving eleven fields hand-authored. _Outcome:_ the default path emits a correct block. _Change surface:_ reorder the usage block; adjust one paragraph of surrounding prose. Keep the `REPLACE:` warning adjacent. _Evidence:_ 240 parsed invocations, both harnesses. _Validation after:_ re-measure `--scaffold` share on the next corpus window.

3. **Decide the reach question, once (F1).** _Target:_ ~95% of Claude Code frontmatter work happening without the skill. _Outcome:_ either the package reaches agents like its three siblings, or it stops carrying prose for sessions that never load it. _Change surface:_ either a new `AGENTS.md`/`CLAUDE.md` contribution in `payload.toml` (mirroring `agent-handoff@1.15`), or a reduction of `SKILL.md` to non-machine-checkable content. _Evidence:_ load-rate split at 2026-08-15; payload comparison across five packages. _Regression risk:_ option (a) relocates rather than removes the pointer problem and adds managed surface to every consumer repo; option (b) can only be validated over a later corpus window. _Recommended sequencing:_ re-measure the post-2026-08-15 window once it holds more than 22 sessions before committing to either branch.

4. **Correct the install-path sentence (F4).** _Target:_ a shipped intra-version contradiction. _Outcome:_ `SKILL.md` matches `agent-summary.md` and `payload.toml`. _Change surface:_ one sentence. _Evidence:_ static, verified. _Validation after:_ the standards-graph destination test (`SG-ARTIFACT-SKILL-DEST`, #174) already accepts both destinations; no test change expected.

5. **Consider the manifest-vs-profile line (trigger clarity).** _Target:_ agents deriving mid-task whether a `SKILL.md` manifest header violates the prohibition. _Outcome:_ one sentence resolves it. _Change surface:_ the "When NOT to use" section. _Evidence:_ 1 session, resolved correctly but slowly. _Caution:_ this **adds** an instruction to a file that recommendation 3 may be shrinking — sequence it after that decision.

6. **Do not act on F3, F6, F7's batch-mode, or F8's deduplication.** All four were refuted, weakened to non-defect, or judged to relocate complexity. F5's placeholder change, if pursued, must move the shipped exemplars before touching `_TOKEN`.

## Uncertainties and Coverage Gaps

- **The load-rate counting predicate is not fully reproduced.** The current-form grep yields 17 Claude files; the union with the pre-1.2 form yields 25. The verifier could not reproduce the 178-session denominator within budget against a looser `schema_version` mention count of 1,699. Both predicates are stated exactly; the discrepancy is definitional, but the numbers should be re-derived before F1 drives a package change.
- **The post-#170 window is 22 Claude sessions over 11 days.** The 4.5% post-fix load rate is directionally clear but statistically thin.
- **Cross-harness load rates use different denominators.** Claude's is "sessions that wrote frontmatter"; Codex's is "sessions mentioning `schema_version`". The comparison is directional only.
- **No token, context-size, or latency data exists in either archive.** Every cost figure here is a tool-call count or qualitative.
- **F8 has no usage evidence in either direction.** Whether `SKILL.md` and the installed `agent-summary.md` are ever both in context is unknown.
- **27 of 30 `'2026'` and 5 of 9 `'agent'` prefix rejections were not classified** as authoring vs backfill vs control test.
- **The two largest 2026-07-09 Codex rollouts were sampled, not read end to end**, and both are pre-packaging.
- **Whether a placeholder id ever reached a commit** cannot be settled from transcripts alone; it would need git history across the consumer repositories.
- **`--scaffold`'s effect on defect rates is not established** — only its adoption rate. The corpus does not support a claim that non-scaffolded documents produce more validation failures, only that they could.
- **Codex `agents/openai.yaml`'s practical effect could not be observed** in any reviewed session.

## Evidence Index

| Ref | Harness | Repository | Date | Session/source | Why relevant |
| --- | --- | --- | --- | --- | --- |
| E1 | Codex | project-standards | 2026-08-10 | `codex/sessions/2026/08/10/rollout-2026-08-10T15-12-27-019fed17-2da5-73a1-ba33-e2e39a8966a3.jsonl` → `/tmp/mfreview/codex/rollout-2026-08-10T15-12-27-*.txt` L4700, L4706, L4826, L4828 | F2 — invented `--title`/`--created` flags; `project-standards validate-id` invalid subcommand with EXIT=2 |
| E2 | Codex | llm-wiki | 2026-08-17 | `codex/sessions/2026/08/17/rollout-2026-08-17T08-36-13-01a00fb8-ee77-7d23-8710-2b3a49cb7a2b.jsonl` → `/tmp/mfreview/codex/rollout-2026-08-17T08-36-13-*.txt` L605–L696 | F2 — invented `scripts/validate-frontmatter`, ~5-call recovery; **and** the positive gate catch of a date-shaped id |
| E3 | Codex | agent-configs | 2026-07-12 | `codex/sessions/2026/07/12/rollout-2026-07-12T09-56-47-019f569d-*.jsonl` L7383, L7526, L7820, L10354 | Repeated `SKILL.md` loads (4×) in one session; correct `--doc-type spec`/`plan` usage |
| E4 | Codex | project-standards | 2026-07-20 | `codex/sessions/2026/07/20/rollout-2026-07-20T07-23-07-019f7f43-*.jsonl` L1209 | Clean end-to-end id generation → committed document |
| E5 | Claude | scripts | post-1.2 | `claude/projects/-home-chris-scripts/6d55f52d-0e8b-4d4d-b334-6aabc9a49287.jsonl` → `/tmp/mfreview/ev/-home-chris-scripts_6d55f52d-*.txt` L537, L551–L573, L611 | F3 refutation (missing-file cause, not path form); F10 — `'2026'` rejections from a bulk backfill helper |
| E6 | Claude | project-standards | 2026-08-16 | `claude/projects/-home-chris-projects-project-standards/a8032963-9a22-4871-8550-dc80e197e332.jsonl` L34, L248, L674–L679 | Post-#170 `Skill` invocation; absolute path at zero discovery cost; manifest-vs-profile reasoning |
| E7 | Claude | project-standards | pre-2026-07-09 | `claude/projects/-home-chris-projects-project-standards/db633d23-7367-4f9a-9402-45304ba18a4e.jsonl` L884, L888, L926 | F5 — deliberate `xxxxxx` placeholder cleared by one `validate-id --fix` |
| E8 | Claude | agent-configs | 2026-07-07/08 | `claude/projects/-home-chris-projects-agent-configs/9977270f-8a6a-457f-aa02-b5cb6a7db59c.jsonl` L48, L98, L124, L225, L473 | F6 refutation — mnemonic ids follow a pre-existing repo convention; pre-packaging era |
| E9 | Claude | doc-proc-scripts | 2026-07-07 | `claude/projects/-home-chris-projects-doc-proc-scripts/adb9cde5-b68e-4fc7-a587-4db67c120d09.jsonl` L171, L180, L253, L274 | F7 — ten-id shell loop; quotes the retired "repo name from git root" usage text |
| E10 | Claude | doc-proc-scripts | 2026-07-07 | `claude/projects/-home-chris-projects-doc-proc-scripts/b9150781-f307-4110-8668-f7150efa76fd.jsonl` and `…/subagents/agent-askill-fix-76efe872d833596d.jsonl` L77, L79, L106, L468 | Discovery of the stale global skill; six-doc_type conformance sweep proving the generator correct; F10's `'agent'` control tests |
| E11 | Claude | homelab | 2026-07-04/10 | `claude/projects/-home-chris-projects-homelab/ba335183-838d-4676-b90c-8180243dcd69.jsonl` L290 | Chained five-call id generation |
| E12 | — | project-standards | — | `standards/markdown-frontmatter/versions/1.13/payload.toml:269–290`; `artifacts/agent-summary.md:28`; `skills/markdown-frontmatter/SKILL.md:17` | F4 — the intra-version contradiction, verified in all three files |
| E13 | — | project-standards | — | `src/project_standards/validate_id.py:163–210`; `providers/frontmatter.py:31` | F11 prefix-equality rule and its exact message; F5 `_TOKEN` regex |
| E14 | — | project-standards | — | `standards/{agent-handoff/versions/1.15,markdown-tooling/versions/1.15,github-workflow/versions/1.5,python-tooling/versions/1.15}/payload.toml` | F1 — sibling packages all contribute to `AGENTS.md` and `CLAUDE.md`; `markdown-frontmatter` does not |
| E15 | both | — | — | `/tmp/mfreview/inv-claude.jsonl` (100 calls), `/tmp/mfreview/inv-codex.jsonl` (140 calls) | F11 — the `--scaffold` / `--doc-type` adoption measurement |

Extraction tooling used to build the timeline bundles is under `/tmp/mfreview/` (`timeline.py`, `codex_tl.py`, `idsource2.py`, `invocations.py`, `loadcount.py`, `window.py`). These are session scratch and are not retained in the repository; the greps and predicates above are sufficient to rebuild them.
