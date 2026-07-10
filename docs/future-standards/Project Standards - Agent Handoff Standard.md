---
title: 'Project Standards - Agent Handoff Standard'
source: 'https://chatgpt.com/g/g-p-6a24ec06cda08191be0c41f4bfaefada/c/6a4d9ebd-cb48-83ea-bb7f-e4e32d7dc318'
---

**You:**

GitHub see my agent handoff system, V3 repository. I want to formalize this into a published standard.

---

**ChatGPT:**

I’ll inspect the repository first, then map the existing handoff mechanics into a publishable standard structure: scope, normative rules, repo artifacts, validation/checks, adoption model, and agent-facing summary.

The repository is `chrisdpurcell/agent-handoff-v3`; its README already has the bones of a standard: lifetime-partitioned state, one tiny eager context file, lazy long-lived files, cross-harness hook behavior, and factory/consumer separation.

Yes. The right move is to publish it as a **new `Agent Handoff Standard` in `L3DigitalNet/project-standards`**, while keeping `chrisdpurcell/agent-handoff-v3` as the **reference implementation / engine repo**.

Do **not** publish the V3 repo verbatim as the standard. It currently mixes four things:

1. The actual portable standard.
2. The reference implementation: hook, installer, validators, skill.
3. Engine-repo operational rules.
4. V3/V3.4 changelog and migration history.

That mix is useful in the engine repo, but a published standard should separate the **contract** from the **implementation**.

## Recommended standard shape

Create:

```text
standards/agent-handoff/
├── README.md
├── adopt.md
├── templates/
│   ├── STATUS.md
│   ├── TODO.md
│   ├── state.md
│   ├── deployed.md
│   ├── architecture.md
│   ├── credentials.md
│   ├── conventions.md
│   ├── specs-plans.md
│   └── sessions-YYYY-MM.md
├── examples/
│   └── minimal-repo-layout.md
└── resources/
    ├── implementation-profile-agent-handoff-v3.md
    └── rationale.md
```

Then update:

```text
standards/README.md
README.md
.project-standards.yml
meta/versioning.md
CHANGELOG.md
```

The existing standards repo already expects every published standard to be a self-contained bundle with `README.md`, `adopt.md`, optional `templates/`, optional `examples/`, and optional `resources/` directories.

## Standard name and contract

Use:

```text
Agent Handoff Standard
```

Not:

```text
Agent Handoff System v3
```

Reason: `v3.4` is the implementation/schema lineage of the current engine repo, not the first public contract version of the standard. The project-standards repo already distinguishes repository release tags from per-standard contract versions.

I would start the published standard as:

```YAML
agent_handoff:
  version: '1.0'
```

For now, make it **copy-adopted / externally validated**, not validator-enforced by `project-standards` itself. Consumers adopt the standard by installing the reference engine and running its validators. Later, if you want `project-standards` to own validation directly, move the validator logic into the `project-standards` package as a separate `agent-handoff validate` command.

## Core standard to extract

The standard’s central rule is strong and publishable:

> Agent-managed repository state MUST be partitioned by fact lifetime, not by topic.

That comes directly from the V3 design: active state goes in `state.md`, deployed facts in `deployed.md`, structural facts in `architecture.md`, durable conventions in `conventions.md`, permanent gotchas in `bugs/`, and session history in `sessions/`.

The published standard should define these normative pieces:

### 1. Purpose

Agent sessions are stateless; repository-local handoff files preserve working state across sessions, agents, workstations, and time. The V3 README states the problem well: without deliberate handoff structure, every new session starts blind, and large eager files waste context on stale facts.

### 2. Required layout

The standard should require this shape for active agent-managed repos:

```text
<repo>/
├── STATUS.md
├── TODO.md
├── CLAUDE.md
├── AGENTS.md
├── .claude/
│   ├── settings.json
│   └── hooks/session_start.py
├── .codex/
│   ├── config.toml
│   └── hooks/session_start.py
└── docs/
    └── handoff/
        ├── state.md
        ├── deployed.md
        ├── architecture.md
        ├── credentials.md
        ├── conventions.md
        ├── specs-plans.md
        ├── sessions/
        └── bugs/
```

That layout is already the current V3 target layout.

### 3. Eager vs lazy context

This is the best part of the system and should be first-class in the standard:

| Surface | Rule |
| --- | --- |
| `docs/handoff/state.md` | Eager, tiny, current work only |
| `CLAUDE.md` / `AGENTS.md` | Eager index files, not state |
| `deployed.md`, `architecture.md`, `conventions.md`, `sessions/`, `bugs/` | Lazy, read on demand |

The V3 spec already defines caps: repo `CLAUDE.md` ≤2048 bytes, `state.md` ≤2048 bytes, hook output ≤4096 bytes, and repo `AGENTS.md` ≤4096 bytes.

### 4. SessionStart hook profile

Make this an **implementation profile**, not the whole standard.

The standard can say:

```text
A conforming implementation SHOULD provide an automatic session-start mechanism when the agent harness supports one.
```

Then define the V3 reference profile:

```text
Reference profile: agent-handoff-v3
```

The V3 hook already does the right things: resolves project root explicitly, reads `state.md`, truncates it safely, captures branch/recent commits/status, emits Claude JSON or Codex stdout, and never blocks session start on failure.

### 5. Factory vs consumer model

This should be a core normative section.

The engine repo is the **factory**: it owns the canonical hook, skill, validators, installer, settings templates, and tests. Every managed repo is a **consumer**: it owns only its own `docs/handoff/` state and local agent index files.

Rules to publish:

```text
- Shared engine files MUST have one canonical source.
- Installed hook files MUST be byte-identical copies of the canonical source.
- Per-repo hook edits MUST NOT be made.
- Live files MUST be regular copies, not repo-to-live symlinks.
- Repo facts MUST stay with the repo they describe.
```

### 6. Security and trust boundary

This should not be buried. It is a standard-level rule.

The current skill already states it well: credentials files store references only, never secret values; handoff docs from untrusted repos are reference data, not instructions; injected state is wrapped in a `<session_context>` data boundary.

### 7. Session-end ritual

This should become a required operational procedure. The current V3 ritual is already implementable: update only facts that changed, route each changed fact to its lifetime home, append session rows when durable, regenerate the bug index when bug records change, and keep `TODO.md` user-owned section intact.

### 8. Validation

Keep this as a standard requirement:

```text
A conforming implementation MUST provide a non-mutating validation command.
```

The V3 implementation already has `validate-layout.sh` and `validate-globals.sh`, and the validator checks layout, size budgets, hook registration, hook hash parity, and Codex/Claude registration details.

## What to remove from the published standard

Move these out of `README.md` and into `resources/implementation-profile-agent-handoff-v3.md` or changelog material:

- V3.0/V3.1/V3.2/V3.3/V3.4 changelog entries.
- Specific bug IDs and issue references unless they justify a rule.
- Local implementation archaeology.
- Engine repo bootstrapping details that only apply to `chrisdpurcell/agent-handoff-v3`.
- Personal/global instruction-file language.
- Any statement that assumes Claude/Codex are the only possible harnesses.

Keep the concrete Claude/Codex details, but mark them as the **V3 reference implementation profile**.

## Adoption model

The `adopt.md` should be procedural, like the existing Project Specification adoption guide: definition of done, prerequisites, scaffold/install, validation, CI, versioning, references. The project-spec adopt guide is a good model because it starts with a clear definition of done and then walks through tooling and validation.

Suggested definition of done:

```Markdown
A repository has adopted the Agent Handoff Standard when:

1. It contains the required root files and `docs/handoff/` layout.
2. `state.md`, `CLAUDE.md`, and `AGENTS.md` stay within the configured eager-context budgets.
3. Credential files contain references only, never secret values.
4. Session-start hook files, when used, are installed from a canonical source and validate by hash.
5. The non-mutating layout validator passes locally and in CI.
6. Agent instructions point to the handoff files without duplicating volatile state.
```

## Implementation spec for an agent

Use this as the actual work order:

```Markdown
# Implement Agent Handoff Standard in project-standards

## Goal

Promote the existing `agent-handoff-v3` repository design into a published `Agent Handoff Standard` in `L3DigitalNet/project-standards`, while keeping `chrisdpurcell/agent-handoff-v3` as the reference implementation / engine repo.

## Source material

Primary source:
- `chrisdpurcell/agent-handoff-v3`
- `README.md`
- `docs/specs/agent-handoff-v3.md`
- `agent-handoff-v3/skills/.agents/skills/handoff-system-v3/SKILL.md`

Reference standards:
- `standards/README.md`
- `meta/versioning.md`
- `standards/project-spec/adopt.md`

## Required changes

1. Create `standards/agent-handoff/README.md`.
   - Use Markdown frontmatter.
   - `doc_type: 'reference'`
   - `status: 'active'`
   - `consumer: 'mix'`
   - `visibility: 'public'`
   - Contract version: `1.0`.
   - Define the standard, not the V3 implementation.

2. Create `standards/agent-handoff/adopt.md`.
   - Use runbook frontmatter.
   - Define adoption prerequisites.
   - Define adoption definition of done.
   - Explain use of the `agent-handoff-v3` engine as the reference implementation.
   - Include local validation commands.
   - Include optional CI wiring pattern.

3. Create templates under `standards/agent-handoff/templates/`.
   - `STATUS.md`
   - `TODO.md`
   - `state.md`
   - `deployed.md`
   - `architecture.md`
   - `credentials.md`
   - `conventions.md`
   - `specs-plans.md`
   - `sessions-YYYY-MM.md`
   - Keep templates generic and secret-free.

4. Create `standards/agent-handoff/resources/implementation-profile-agent-handoff-v3.md`.
   - Move V3-specific hook, installer, validator, changelog, and factory repo details here.
   - Make clear that this is the current reference implementation profile, not the standard itself.

5. Update `standards/README.md`.
   - Add `Agent Handoff` to the standards table.

6. Update root `README.md`.
   - Add an `Agent Handoff Standard` section under Standards.
   - Add consumption/adoption notes.

7. Update `meta/versioning.md`.
   - Add `Agent Handoff` to the component list.
   - Add its contract marker to the per-standard table.
   - Classify it as copy-adopted / externally validated unless validator code is moved into `project-standards`.

8. Update `.project-standards.yml`.
   - Include `standards/agent-handoff/**/*.md`.
   - Exclude `standards/agent-handoff/templates/**`.
   - Exclude any examples that intentionally use non-frontmatter handoff runtime format.

9. Run the repository checks.
   - Python gate.
   - Frontmatter validation.
   - Spec validation if relevant.
   - Markdown formatting/linting according to repo policy.

## Design constraints

- Do not move the V3 engine code into `project-standards` in this change.
- Do not make `docs/handoff/` a managed frontmatter documentation surface; it remains agent session state.
- Do not add personal instructions, hostnames, private paths, tokens, secret names, or local machine assumptions.
- Do not call the published standard `v3`.
- Do not weaken existing standards or validation behavior.
```

## Bottom line

Publish it as a **standardized contract with a reference implementation**, not as “the V3 repo but moved.” The V3 repo already proves the design; `project-standards` should define the portable rules, adoption contract, templates, and versioning surface.

---

**You:**

i very frequently observe agents using the handoff system requiring multiple attempts to reduce the size of the documents that have explicit caps in size. It seems like they’re randomly guessing that their efforts to reduce size will bring it under the limit and then they test after the fact and realize it’s not and have to go back and try fixing it again. This seems inefficient and a waste of time and a waste of tokens. What sort of options do I have that I could bake into this standard which would help the agents use it more effectively and efficiently

---

**ChatGPT:**

The failure mode is not the cap itself; it is that the standard tells agents the destination but not the measurement procedure. I’d add deterministic “budget workflow” rules plus small tooling so an agent never edits blind.

Bake in a **deterministic byte-budget workflow**. The current standard already has the right caps — `state.md` ≤2048 bytes, repo `CLAUDE.md` ≤2048 bytes, hook output ≤4096 bytes, and repo `AGENTS.md` ≤4096 bytes — but agents need explicit instructions to **measure first, calculate the overage, target a safety margin, then edit**. Right now they are treating the cap like a prose-quality goal instead of an engineering constraint.

## Best standard additions

### 1. Add a “no blind shrinking” rule

Make this normative:

```text
Agents MUST NOT reduce capped handoff files by guessing.

Before editing any capped file, the agent MUST:
1. Measure the exact UTF-8 byte size.
2. Compare it to the cap and target size.
3. Calculate the required reduction.
4. Identify which facts will be moved, compressed, or removed.
5. Edit toward a target at least 10–20% below the hard cap.
6. Re-measure before running the full validator.
```

The safety margin matters. A file at 2044/2048 bytes is technically valid but practically brittle. I would set **hard cap = 2048 bytes, working target = 1700–1800 bytes** for `state.md` and `CLAUDE.md`.

### 2. Add a dedicated size command, not just validation

The validator currently catches layout drift and size failures, but agents need a cheap preflight command before full validation. The V3 validator already checks layout, caps, hook registration, and hash parity ; add a smaller command focused only on budgets.

Example interface:

```Bash
./scripts/handoff/size-report.sh
./scripts/handoff/size-report.sh --json
./scripts/handoff/size-report.sh --file docs/handoff/state.md
```

Human output:

```text
docs/handoff/state.md     2314 / 2048 bytes   OVER by 266   target: 1740   reduce: 574
CLAUDE.md                 1320 / 2048 bytes   OK            target: 1740   spare: 420
AGENTS.md                 3550 / 4096 bytes   OK            target: 3600   spare: 46
```

Machine output:

```JSON
{
  "files": [
    {
      "path": "docs/handoff/state.md",
      "bytes": 2314,
      "cap": 2048,
      "target": 1740,
      "over_by": 266,
      "recommended_reduction": 574,
      "status": "over"
    }
  ]
}
```

That gives agents arithmetic instead of vibes.

### 3. Require draft-to-temp for capped file rewrites

For capped files, agents should not edit the live file and then discover the mistake. They should draft the replacement into a temp file, measure it, then replace only if it fits.

Normative rule:

```text
When replacing a capped file wholesale, agents SHOULD write the candidate content to a temporary file, measure it with the same byte-counting method used by the validator, and only then replace the real file.
```

This is especially useful for `state.md`, `CLAUDE.md`, and `AGENTS.md`.

### 4. Define exact byte-count semantics

Make the measurement canonical:

```text
Capped file size is measured as the length in bytes of the file's UTF-8 encoded contents on disk.
The count includes newlines and frontmatter if present.
Agents MUST NOT use character count, token estimate, word count, or rendered Markdown length as a substitute.
```

Then include the canonical one-liner:

```Bash
python3 - <<'PY'
from pathlib import Path
for path in ["docs/handoff/state.md", "CLAUDE.md", "AGENTS.md"]:
    p = Path(path)
    if p.exists():
        print(f"{path}: {len(p.read_bytes())} bytes")
PY
```

This prevents the common `wc -m`, token estimate, or “looks shorter” failure.

### 5. Add sub-budgets inside `state.md`

A 2048-byte total cap is still too abstract. Give agents a structure and approximate section budgets.

Example:

```Markdown
**Last updated:** YYYY-MM-DD

## Active
<!-- target: <=700 bytes -->

## Next
<!-- target: <=350 bytes -->

## Blockers
<!-- target: <=300 bytes -->

## Pointers
<!-- target: <=300 bytes -->
```

Then the rule:

```text
If `state.md` exceeds its cap, agents MUST reduce by moving facts out by lifetime before shortening prose.
```

This aligns with the existing design: over-full `state.md` means longer-lived content leaked into the live slice, and the fix is to route facts to their correct home rather than delete them.

### 6. Standardize a reduction algorithm

Add a deterministic algorithm agents must follow when a capped file is over budget:

```text
Capped-file reduction order:

1. Move completed work to `STATUS.md` or `sessions/<YYYY-MM>.md`.
2. Move future work to `TODO.md`.
3. Move deployment facts to `deployed.md`.
4. Move architecture/backlog facts to `architecture.md`.
5. Move durable patterns to `conventions.md`.
6. Move bug/gotcha facts to `bugs/<NNN>-<slug>.md`.
7. Replace remaining detail with a one-line pointer.
8. Only then compress wording.
9. Never delete a fact unless it is obsolete or preserved elsewhere.
```

That converts “make it shorter” into “route by lifetime.” The spec already has the lifecycle concept: session rows are the permanent record, and once a row captures what happened, convenience copies in current files are safe to prune.

### 7. Require a size delta in the agent’s final report

This gives you an audit signal and trains agents to think numerically.

Example final report requirement:

```text
When editing capped handoff files, the agent's final response MUST report:
- file path
- before size
- after size
- cap
- whether validation passed
```

Example:

```text
Size results:
- `docs/handoff/state.md`: 2314 → 1628 bytes / 2048 cap
- `AGENTS.md`: unchanged, 3550 bytes / 4096 cap
- `validate-layout.sh`: passed
```

### 8. Add validator advice, not just failure

A failure like this is not enough:

```text
state.md exceeds 2048 bytes
```

Better:

```text
docs/handoff/state.md is 2314 bytes; cap is 2048; over by 266.
Recommended target is 1740, so reduce by about 574 bytes.
Do not delete live facts blindly. Move longer-lived facts to:
- sessions/YYYY-MM.md for completed session narrative
- deployed.md for runtime/deployment facts
- architecture.md for standing backlog or component graph
- conventions.md for durable patterns
```

Agents are much better when the tool output tells them what to do next.

### 9. Add capped-file templates that are intentionally sparse

For `state.md`, the template should make it hard to write paragraphs.

Use this style:

```Markdown
**Last updated:** YYYY-MM-DD

## Active

- `<one-line current work item>`

## Next

- `<one-line next action>`

## Blockers

- None.

## Pointers

- Plan/spec: `<path>`
- Details: `<path>`
```

Do not let the template invite narrative. Narrative belongs in `sessions/`, specs, plans, or bug records.

### 10. Add a “two-attempt rule”

This is a good agent discipline rule:

```text
If a capped-file reduction still fails after one edit-and-measure cycle, the agent MUST stop prose tweaking and produce a size report plus a routing plan before editing again.
```

That prevents the “randomly shorten, validate, fail, shorten again” loop.

## My recommendation

Bake in three layers:

| Layer | Addition | Why |
| --- | --- | --- |
| Standard prose | “No blind shrinking” workflow | Changes agent behavior immediately |
| Tooling | `size-report.sh --json` | Gives exact arithmetic and machine-readable output |
| Templates | Sparse capped-file structure + sub-budgets | Prevents bloat from entering in the first place |

The most important single rule is:

```text
For capped handoff files, agents MUST target a working size below the cap, not merely pass the cap.
```

Use **85% of cap** as the default working target. For a 2048-byte file, that is about **1740 bytes**. This gives enough slack that the next session update can add a line without immediately triggering another reduction cycle.

---

**You:**

That’s the other thing I would like to solve, overly verbose comments. I would like stricter controls, preferably, deterministic, mechanical controls over what the agent writes the format and the length this would vary by document what would be useful in all documents, even though that aren’t strictly limited in size.

---

**ChatGPT:**

This is the same class of problem as byte caps: agents need shape constraints, not advice like “be concise.” I’d solve it with a document-policy manifest plus validators that check countable properties before content quality is reviewed.

Yes — solve this by adding a **document shape contract**, not more prose guidance.

The standard should stop saying only “keep this concise” and instead define **allowed content units, section limits, line limits, bullet limits, and overflow routing** per document. Then a validator enforces the mechanical parts.

The existing handoff design already has the key premise: facts route by lifetime, not topic, and `state.md` is only the live eager slice. The missing layer is: **what shape is each file allowed to take once the fact gets there?**

## Core recommendation

Add a new section to the standard:

```text
Document Shape and Verbosity Control
```

with this rule:

```text
Every handoff document has a shape profile. Agents MUST write to the profile for that document, not to an open-ended prose style.

When a shape profile sets a measurable limit, agents MUST measure it before completion. Agents MUST NOT rely on visual length, estimated token count, or subjective concision.
```

This gives you deterministic control over documents that are byte-capped **and** documents that are uncapped but should still not become agent rambling.

## Add a document-policy manifest

Use a repo-local policy file:

```YAML
# docs/handoff/policy.yml
version: '1.0'

defaults:
  max_paragraph_chars: 360
  max_bullet_chars: 180
  max_heading_depth: 3
  forbid_narrative_history: true
  prefer_bullets: true
  require_overflow_pointer: true

documents:
  docs/handoff/state.md:
    profile: live-state
    hard_byte_cap: 2048
    target_bytes: 1740
    max_sections: 4
    allowed_sections:
      - Active
      - Next
      - Blockers
      - Pointers
    max_bullets_per_section: 4
    max_bullet_chars: 140
    forbid_paragraphs: true

  STATUS.md:
    profile: status-snapshot
    target_lines: 60
    max_bullet_chars: 180
    forbid_narrative_history: true
    required_sections:
      - Current State
      - Completed Recently
      - Notes

  TODO.md:
    profile: work-queue
    max_bullet_chars: 160
    required_order:
      - User Tracked Tasks
      - Agent Tracked Tasks
    forbid_completed_items: true

  docs/handoff/deployed.md:
    profile: current-truth
    target_lines: 120
    require_tables_or_bullets: true
    forbid_changelog: true

  docs/handoff/architecture.md:
    profile: structural-reference
    target_lines: 200
    max_paragraph_chars: 420
    require_pointer_for_details_over_chars: 700

  docs/handoff/conventions.md:
    profile: numbered-rules
    require_quick_reference: true
    max_rule_summary_chars: 180
    max_entry_chars: 1200

  docs/handoff/sessions/*.md:
    profile: session-log
    append_only: true
    row_max_chars: 220
    headline_max_words: 20

  docs/handoff/bugs/*.md:
    profile: bug-record
    required_sections:
      - Cause
      - Fix
      - Lesson
    max_section_chars:
      Cause: 700
      Fix: 700
      Lesson: 360
```

This can live in the published standard as the default profile, with repos allowed to tune thresholds through documented exceptions.

## Make the validator enforce the cheap things

Add a validator command that checks shape separately from semantic quality:

```Bash
./scripts/handoff/validate-shape.sh
./scripts/handoff/validate-shape.sh --json
```

It should report exact failures:

```text
docs/handoff/state.md
  FAIL: 2291 bytes; cap 2048; target 1740
  FAIL: section "Active" has 7 bullets; max 4
  FAIL: bullet 3 is 214 chars; max 140
  ADVICE: Move completed work to STATUS.md or sessions/2026-07.md.
```

This is more useful than “too long.” It tells the agent **what kind of edit is needed**.

## Universal controls useful across all docs

These are broadly useful even where there is no hard byte cap.

| Control | Why it helps |
| --- | --- |
| `max_paragraph_chars` | Prevents agent essays. |
| `max_bullet_chars` | Forces atomic, scannable facts. |
| `max_bullets_per_section` | Prevents backlog dumping. |
| `allowed_sections` | Stops agents inventing new structure. |
| `required_sections` | Keeps docs predictable. |
| `forbid_paragraphs` | Useful for live state and task queues. |
| `target_lines` | Soft limit for lazy docs without hard byte caps. |
| `forbid_narrative_history` | Keeps current-state docs from becoming logs. |
| `require_overflow_pointer` | Forces long detail into the right file. |
| `append_only` | Protects session logs. |
| `required_order` | Protects files like `TODO.md` where user-owned content must stay first. |

The current V3 system already distinguishes current snapshots, queues, deployment truth, conventions, session rows, and bug records. For example, `STATUS.md` is supposed to be current state, not history, and `sessions/` is the permanent log. The shape validator makes that mechanically enforceable.

## Document-specific profiles

### `state.md`: live-state profile

Strictest profile.

Rules:

```text
- Hard cap: 2048 bytes.
- Working target: 1740 bytes.
- Paragraphs forbidden.
- Only approved sections allowed.
- Max 4 bullets per section.
- Max 140 characters per bullet.
- No completed work except as a pointer to STATUS.md or sessions/YYYY-MM.md.
- No deployment details except a pointer to deployed.md.
- No architecture explanation except a pointer to architecture.md.
```

Template:

```Markdown
**Last updated:** YYYY-MM-DD

## Active

- One-line live item.

## Next

- One-line next action.

## Blockers

- None.

## Pointers

- Plan/spec: `path/to/doc.md`
- Details: `docs/handoff/<file>.md`
```

### `STATUS.md`: status-snapshot profile

Rules:

```text
- Snapshot, not history.
- Bullets only by default.
- No session narrative.
- Max 60 lines target.
- Completed items should be one sentence unless a pointer is needed.
- If a detail needs more than 2 bullets, link to the durable document.
```

This directly reinforces the current V3 rule that `STATUS.md` is a current-state snapshot, not a history file.

### `TODO.md`: work-queue profile

Rules:

```text
- Preserve `## User Tracked Tasks` above `## Agent Tracked Tasks`.
- Agent may not rewrite the user-owned section unless asked.
- Each task is one checkbox line.
- Max 160 characters per task.
- Completed agent tasks must be rolled into STATUS.md, then removed unless they are sub-steps of an open parent item.
```

The current spec already requires the user-tracked section to stay above the agent-tracked section.

### `deployed.md`: current-truth profile

Rules:

```text
- Current runtime/deployment truth only.
- No deployment changelog.
- Prefer compact tables.
- Each environment/service row should fit one table row.
- Historical deployment notes go to sessions/YYYY-MM.md.
```

### `architecture.md`: structural-reference profile

Rules:

```text
- Structural map and standing backlog only.
- Explanations allowed, but paragraphs max 420 characters.
- If a topic needs more than 700 characters, create or link a spec/ADR/design note.
- Do not store session narrative.
```

### `conventions.md`: numbered-rules profile

The current skill already defines this file as a pattern library with a Quick Reference table and numbered entries. Make that strict:

```text
- Must start with Quick Reference.
- Every convention has a stable number.
- Every entry uses this structure:
  - Applies when
  - Rule
  - Example
  - Why
  - Sources
  - Related
- Rule summary max 180 characters.
- Entry target max 1200 characters.
- ADR-shaped conventions must be proposed for ADR graduation, not expanded indefinitely.
```

### `sessions/YYYY-MM.md`: session-log profile

Rules:

```text
- Append-only.
- One row per noteworthy session.
- Headline max 20 words.
- Row max 220 characters unless a link/pointer is required.
- Do not bulk-read session logs; grep by date or keyword.
```

The V3 spec already says session rows should be compact with date, ≤20-word headline, commit refs, and bug refs.

### `bugs/NNN-slug.md`: bug-record profile

Rules:

```text
- Required sections: Cause, Fix, Lesson.
- No general debugging diary.
- Cause explains root cause.
- Fix explains the corrected action.
- Lesson explains the reusable gotcha.
- Long reproduction logs go elsewhere and are linked.
```

## Add “allowed writing units”

This is the part that will reduce agent verbosity the most.

Define allowed units:

```text
Allowed units:
- Fact bullet: one durable fact, one sentence preferred.
- Task bullet: one action, starts with a verb.
- Pointer: path plus reason to read it.
- Decision summary: decision + rationale pointer.
- Table row: one entity/state pair.
- Bug lesson: cause/fix/lesson only.

Disallowed units in handoff docs:
- Stream-of-consciousness session summaries.
- “It is important to note…” filler.
- Repeated rationale already captured in a spec/ADR.
- Full transcripts.
- Multi-paragraph explanations in live/current files.
- Agent self-commentary about what it attempted.
```

This gives agents a vocabulary for what they are allowed to write.

## Add an overflow rule

This should be universal:

```text
When content exceeds the profile limit, agents MUST NOT continue compressing the same document indefinitely. They MUST move detail to the correct durable location and leave a pointer.
```

Pointer format:

```Markdown
- Details: `docs/superpowers/specs/2026-07-07-example.md` — design rationale and rejected options.
```

This prevents the agent from trying to cram a spec into `state.md` or a deployment history into `deployed.md`.

## Add a “comment/prose lint” pass

For deterministic controls, a custom validator can catch common bloat phrases. Keep this small and mechanical, not stylistic.

Example blocked phrases:

```YAML
blocked_phrases:
  - "it is important to note"
  - "it should be noted"
  - "as mentioned above"
  - "this section provides"
  - "in order to"
  - "the purpose of this document is to"
  - "going forward"
  - "at this point in time"
```

Use this as **warning by default**, fail only in capped/eager files.

Better rule:

```text
Capped files fail on blocked filler phrases.
Lazy reference files warn on blocked filler phrases.
```

## Add before/after metrics to agent reports

Require this after any handoff-doc edit:

```text
When an agent edits handoff documents, the final response MUST report shape metrics for every capped or shaped file changed:
- path
- bytes before/after, if byte budgeted
- line count before/after, if line target exists
- validator command run
- pass/fail result
```

Example:

```text
Shape results:
- `docs/handoff/state.md`: 1912 → 1488 bytes / 2048 cap; 9 bullets; passed.
- `STATUS.md`: 72 → 54 lines; target 60; passed.
- `TODO.md`: section order preserved; passed.
```

That makes verbosity visible.

## What to add to the standard

Add this implementer-ready section:

```Markdown
## Document shape and verbosity control

Handoff documents are structured state, not freeform prose. Every managed handoff document MUST follow its document shape profile.

Agents MUST NOT write unconstrained narrative into handoff documents. Agents MUST write the smallest durable unit that preserves the fact and route supporting detail to the correct longer-lived document.

### Universal rules

- Prefer bullets or tables over paragraphs.
- One bullet SHOULD contain one fact or one task.
- A bullet in a managed handoff document MUST NOT exceed the configured profile limit.
- A paragraph in a managed handoff document MUST NOT exceed the configured profile limit.
- Agents MUST NOT create new top-level sections unless the profile allows them.
- Agents MUST NOT store historical narrative in current-state files.
- Agents MUST leave a pointer when moving detail out of a constrained file.
- Agents MUST run the shape validator before reporting completion.

### Overflow rule

If content does not fit the profile, route detail by lifetime:
- live work -> `docs/handoff/state.md`
- completed/current summary -> `STATUS.md`
- future work -> `TODO.md`
- deployment truth -> `docs/handoff/deployed.md`
- structure/backlog -> `docs/handoff/architecture.md`
- durable pattern -> `docs/handoff/conventions.md`
- session history -> `docs/handoff/sessions/YYYY-MM.md`
- durable bug/gotcha -> `docs/handoff/bugs/NNN-slug.md`
- design rationale -> spec, plan, or ADR, then pointer from handoff docs

### Validation

A conforming implementation MUST provide a non-mutating shape validator that checks byte caps, section names, required section order, line targets, bullet limits, paragraph limits, and blocked filler phrases according to the repository policy.
```

## Best implementation path

Do this in phases:

| Phase | Add                                  | Enforcement                         |
| ----- | ------------------------------------ | ----------------------------------- |
| 1     | Standard prose + templates           | Agent behavior improves immediately |
| 2     | `size-report.sh` / `shape-report.sh` | Deterministic feedback              |
| 3     | `docs/handoff/policy.yml`            | Per-file customization              |
| 4     | CI shape validation                  | Prevents drift                      |
| 5     | JSON output                          | Lets agents plan edits mechanically |

The key design choice: **hard caps for eager files, shape limits for all handoff files, advisory targets for lazy reference files.**

That gives you deterministic control without making every useful reference doc artificially tiny.

---

**You:**

See the prior conversation in this project regarding creating an MCP server for the project standards Meta repository. Would the agent handoff standard be able to make use of this MCP server for operating within and handling the files in the handoff system? Would it be better to have its own MCP server that completely separate and scoped to this particular standard? Or is an MCP server not offering any benefit please advise.

---

**ChatGPT:**

I found the relevant prior-thread signal: the earlier direction was “manifest-driven meta repo first, MCP later as a thin local read-only layer,” with no hard dependency between standards. I’m going to treat that as the governing constraint for this recommendation.

Recommendation: **do not make MCP required for the Agent Handoff Standard.** Use the Project Standards MCP server, when it exists, as a **read-only standards/reference surface**. Build any repo-local handoff operations first as deterministic CLI/library functions. Only add a handoff-specific MCP layer later as a thin adapter over those functions.

## Bottom line

Use this split:

| Concern | Best home | Why |
| --- | --- | --- |
| Reading the published Agent Handoff Standard, templates, adoption guide, policy docs | **Project Standards MCP server** | It is standards/meta content. Read-only resources and prompts are appropriate. |
| Measuring, validating, shaping, and updating `docs/handoff/` in a target repo | **Agent Handoff CLI/core library first** | Deterministic, CI-friendly, works without MCP, lower attack surface. |
| Exposing handoff operations to Claude/Codex/Cursor through structured tools | **Optional handoff MCP server/profile later** | Useful only if it wraps the same validated operations and stays repo-scoped. |

The Agent Handoff Standard should say MCP is **optional convenience**, not part of conformance.

## Why the Project Standards MCP should not mutate handoff files

The handoff system’s own model is repo-local: each active agent-managed repo owns its `STATUS.md`, `TODO.md`, agent index files, and `docs/handoff/` state set. The V3 factory/consumer model also says the factory owns shared engine artifacts, while each consumer repo owns only its own state and receives engine files through the installer.

That separation is important. A Project Standards MCP server should know the **standard**. It should not become the thing that reaches into every consumer repo and mutates live session state. That would blur the standard/consumer boundary and create exactly the kind of hidden coupling the prior MCP/meta-repo discussion was trying to avoid.

## What MCP would actually help with

MCP is useful when you want an agent-visible, typed, discoverable interface. Official MCP defines server-exposed **tools**, **resources**, and **prompts**: tools are executable functions, resources provide context data, and prompts provide reusable interaction templates. [![Source](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol](https://modelcontextprotocol.io/docs/concepts/architecture)

That maps cleanly to two different layers.

### Project Standards MCP: read-only standard access

Good uses:

```text
standards://agent-handoff/README.md
standards://agent-handoff/adopt.md
standards://agent-handoff/templates/state.md
standards://agent-handoff/resources/implementation-profile-agent-handoff-v3.md
```

Prompts:

```text
adopt_agent_handoff_standard
review_handoff_layout
explain_handoff_fact_routing
draft_agent_handoff_exception_adr
```

Tools should be minimal, mostly read-only:

```text
standards.find_standard
standards.get_adoption_runbook
standards.get_template
standards.compare_version
```

This is valuable because agents can pull the exact standard and templates without searching the repo manually. It also keeps the standard discoverable across Claude, Codex, and other MCP-aware clients.

### Handoff MCP: optional repo-local operations

Good uses, but only after the CLI/core library exists:

```text
handoff.size_report
handoff.shape_report
handoff.validate_layout
handoff.route_fact
handoff.session_closeout_plan
handoff.append_session_row
handoff.update_state
```

But these should be wrappers around deterministic local code, not independent MCP-only logic.

For example:

```text
handoff.size_report
  -> calls the same byte-counting function used by validate-layout

handoff.shape_report
  -> calls the same profile validator used by CI

handoff.route_fact
  -> returns a proposed destination and diff, not an unreviewed mutation

handoff.update_state
  -> dry-run by default, apply only when explicitly requested
```

## MCP does not replace the SessionStart hook

Keep the SessionStart hook. MCP is not the right primitive for guaranteed startup injection.

The current V3 hook automatically injects `state.md`, git branch, recent commits, working-tree status, and pointers at session start; it also branches output for Claude vs Codex. MCP resources, by contrast, are application-driven: the host decides how to incorporate them. [![Source](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/server/resources) Prompts are user-controlled, and tools are model-controlled. [![Source](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol+1](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

So the hook remains the reliable eager-context mechanism. MCP is better for **on-demand structured operations**.

## Security boundary

A handoff MCP server would be more dangerous than a read-only standards server because it touches repo state. Official MCP tooling guidance explicitly treats tools as model-invoked functions and recommends human-visible controls/confirmation for operations. [![Source](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) MCP roots can define filesystem boundaries, and servers are expected to respect those boundaries and validate paths against them. [![Source](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/client/roots)

For this standard, require:

```text
- MCP MUST NOT be required for conformance.
- MCP write tools MUST be dry-run by default.
- MCP write tools MUST be scoped to the active repo root.
- MCP tools MUST reject paths outside the declared repo root.
- MCP tools MUST NOT read or request secret values.
- MCP tools MUST NOT use sampling or elicitation for handoff validation.
- MCP tools MUST call the same core functions as the CLI validators.
- MCP tools MUST NOT be the only enforcement path; CI/CLI validation remains authoritative.
```

The “no secrets” point is especially important because the handoff standard already says `credentials.md` stores references only, never credential values.

## Recommended architecture

Do this in three phases.

### Phase 1 — no MCP dependency

Build the deterministic tooling first:

```text
handoff size-report
handoff shape-report
handoff validate-layout
handoff route-fact --dry-run
handoff closeout --dry-run
```

This directly fixes the problems you identified: blind byte reduction, verbosity drift, and inconsistent document shapes.

### Phase 2 — Project Standards MCP, read-only

Expose standards as resources and prompts:

```text
standards://agent-handoff/README.md
standards://agent-handoff/adopt.md
standards://agent-handoff/templates/*
```

This helps agents consume the standard but does not mutate repo state.

### Phase 3 — optional handoff MCP adapter

Add a separate logical server/profile only if the CLI proves useful and repeated agent workflows benefit from structured tools.

I would implement it as one of these:

```text
project-standards mcp --profile standards
agent-handoff mcp --profile repo
```

or:

```text
project-standards-mcp        # read-only standards server
agent-handoff-mcp            # repo-local handoff adapter
```

I slightly prefer **separate logical servers** even if they share code internally. It keeps tool scope obvious in the agent UI.

## What to put in the Agent Handoff Standard

Add this section:

```Markdown
## MCP integration profile

MCP support is optional. A repository MUST be usable and validatable without MCP.

The Project Standards MCP server MAY expose this standard, its templates, examples, and adoption prompts as read-only resources. It MUST NOT be required to operate a consuming repository's handoff files.

A handoff-specific MCP server MAY expose repo-local handoff operations when it is scoped to a declared repository root and delegates to the same deterministic implementation used by the CLI and CI validators.

MCP write operations MUST be dry-run by default, MUST report the exact files they would change, and MUST require explicit apply semantics. MCP tools MUST NOT read, request, emit, or persist secret values. MCP tooling MUST NOT weaken the file-based standard, the CLI validation contract, or CI enforcement.
```

## Final recommendation

Build the standard around **files + CLI validators + CI**. Let the Project Standards MCP server serve the standard and templates. Add a handoff-specific MCP server only as a later adapter over the same deterministic handoff library.

That gives you the benefit of MCP where it is strongest — discoverable resources, typed commands, reusable prompts — without making the handoff system depend on a tool layer that is less portable, harder to audit, and riskier for repo-local writes.
