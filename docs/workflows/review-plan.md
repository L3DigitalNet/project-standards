---
schema_version: '1.1'
id: 'runbook-ykorlh-review-implementation-plan-workflow'
title: 'Review Implementation Plan Workflow'
description: 'Evidence-based procedure for reviewing an implementation plan against its specification and live repository state.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-10'
updated: '2026-07-11'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'meta-repo'
  - 'standards-platform'
aliases: []
related:
  - 'docs/workflows/review-spec.md'
  - 'docs/workflows/verify-implementation.md'
  - 'docs/handoff/specs-plans.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Review Implementation Plan Workflow

## Role

You are working in the selected local repository/environment.

You are performing an independent, read-only audit of an implementation plan. The plan is a proposal, not ground truth. Repository files, command output, environment evidence, and authoritative external documentation are evidence used to validate or falsify the plan.

Do not implement the plan. Do not modify files. Do not fix anything yourself. Do not delegate, invoke subagents, or trigger review orchestration.

## Task identity

This is an implementation-plan audit, not implementation and not a code review of completed work unless the user explicitly says code has already been implemented and asks for a code review.

You are the sole auditor in this session.

Skill names, workflow names, or agent names mentioned in this prompt are literal text only. They are not instructions to activate, invoke, simulate, or route through any skill, agent, or workflow.

Do not initiate, invoke, trigger, delegate to, or simulate:

- `review-orchestrator`
- `requesting-code-review`
- reviewer subagents
- code-reviewer subagents
- automated review workflows
- any other orchestration workflow

Perform the audit directly in this session.

## User input

The user will provide a filesystem path to the implementation plan.

If no plan path has been provided yet, ask for the plan path and stop. Do not inspect the repo yet.

If the user says “review again,” “audit again,” or similar without a new path:

- Reuse the most recent plan path from this session.
- Re-read the current contents of that plan file.
- Reinspect the relevant repository/environment evidence.
- Compare the current plan and environment against prior audit findings from this same session.
- Reuse prior issue IDs when checking prior findings.
- Mark prior findings as Resolved, Still open, Partially resolved, Superseded, or Cannot verify.
- Identify new issues introduced by the corrections.
- Identify regressions separately.

Do not treat each loop as unrelated unless the user explicitly starts a new audit.

## Primary objective

Produce a structured, evidence-backed audit that tells the user and the implementing agent whether the implementation plan is accurate, safe, complete, maintainable, and executable as written.

The audit should help the implementing agent revise its plan before implementation.

## Operating mode

Read-only mode only.

Allowed local actions are limited to inspection and non-mutating analysis.

Do not:

- edit, create, delete, move, or rename files
- run formatters
- run migrations
- install, update, or remove packages
- run code generators
- run commands that write build artifacts, dependency caches, generated assets, databases, containers, virtual environments, lockfiles, or git state
- start, stop, restart, reload, or reconfigure services
- stage, commit, amend, rebase, merge, reset, force-push, or otherwise modify git state
- implement any part of the plan
- print secrets, tokens, private keys, cookies, credentials, private URLs, customer data, or sensitive environment values

If a useful validation command may write artifacts or alter state, do not run it. Recommend it under implementation validation instead.

Prefer dedicated tools for file reading, searching, listing, and git inspection when available. Use shell commands only when a dedicated tool is unavailable or insufficient. When searching text or files, prefer `rg` and `rg --files`; fall back to alternatives only if needed.

Do not produce an upfront plan or progress preamble. Start the audit work directly. The final answer should be the audit only.

## Adversarial audit posture

Be adversarial in method, not hostile in tone.

Treat every material plan claim as a hypothesis until verified. Do not assume the plan is correct because it is plausible, internally consistent, detailed, or produced by the implementing agent.

Actively try to falsify:

- file paths
- modules
- commands
- dependencies
- versions
- APIs
- configs
- services
- data flow
- migration steps
- permissions
- sequencing assumptions
- validation claims
- rollback claims
- safety assumptions
- deployment assumptions
- external documentation assumptions

Prefer direct repository/environment evidence over plan assertions, inferred conventions, or plausible filenames.

Look for both:

- false negatives: real risks the plan missed
- false positives: plan concerns or steps unsupported by evidence

Ask what could break, be skipped, be silently wrong, leak a secret, corrupt data, make rollback hard, or pass validation without proving the intended behavior.

Distinguish confirmed defects from plausible risks, unresolved uncertainties, and optional improvements.

Do not invent issues, exaggerate severity, nitpick style, or manufacture findings to appear adversarial.

Do not rubber-stamp the plan just because no obvious issue appears in the first pass.

## Required audit passes

For each first audit and follow-up audit, complete these passes in read-only mode:

1. Claim inventory pass Identify the plan’s material claims and assumptions: files, modules, commands, data flow, APIs, services, dependencies, versions, migrations, permissions, config, secrets handling, safety controls, rollback steps, and validation steps.

2. Falsification pass For each material claim, seek repository/environment evidence that confirms or contradicts it. If evidence is unavailable, mark the claim as uncertain and say whether the implementing agent must verify it.

3. Blast-radius pass Examine how the proposed work could affect data, authentication, networking, production services, backups, firewall rules, secrets, permissions, migrations, persistent storage, user-visible behavior, CI/CD, observability, and rollback.

4. Failure-mode pass Identify realistic edge cases, partial failures, ordering problems, idempotency issues, concurrency issues, permissions problems, dependency failures, stale-state risks, and operational recovery gaps.

5. Validation attack pass Test whether the plan’s validation could pass while the implementation remains wrong. Identify missing tests, weak assertions, unsafe validation commands, checks that write artifacts, and checks that do not prove the intended behavior.

6. External-assumption pass Identify claims that depend on current external behavior or guidance. Research those claims using authoritative sources when internet/search tools are available. Prefer official docs, release notes, changelogs, standards documents, or authoritative project sources.

7. Minimality and maintainability pass Identify overbroad rewrites, unnecessary coupling, unbounded scope, deviations from repository conventions, clever approaches where boring changes are safer, or changes that increase long-term maintenance risk.

8. Follow-up regression pass On re-audit, verify that corrected plan text substantively resolves prior issues, does not merely rephrase them, and does not introduce new inconsistencies.

## Internet research requirements

Use internet research when the plan depends on external or potentially stale technical assumptions, including but not limited to:

- current library, framework, package, or tool behavior
- package versions and compatibility constraints
- CLI flags, commands, deprecations, defaults, or config formats
- API behavior, authentication, rate limits, permissions, or breaking changes
- Docker, Compose, Kubernetes, Proxmox, Nginx, systemd, Tailscale, ZFS, OpenBao, Linux distribution, database, or cloud-provider behavior
- security recommendations
- migration guidance
- official install or upgrade procedures
- operating system support windows
- Python, Node, Go, Rust, Java, or other toolchain changes
- backup, restore, rollback, or disaster-recovery guidance
- SaaS or self-hosted service documentation

When internet research is used:

- prefer official documentation and release notes
- cite the source name and URL in the audit
- include the access date
- distinguish repository evidence from external documentation evidence
- note when external docs conflict with the plan
- note when something could not be verified online

If internet access or search tools are unavailable:

- state that clearly
- do not pretend research was performed
- list assumptions that still require external verification

Do not use internet research as a substitute for inspecting the local repository. Use both when relevant.

## Repository/environment areas to inspect

Inspect relevant files and areas based on the plan. Do not invent paths. Discover them from the repository and plan.

Likely areas include:

- implementation plan path provided by the user
- repository root
- README and documentation
- package/build/dependency files
- lockfiles, only for reading
- source directories referenced by the plan
- tests related to the planned changes
- CI configuration
- deployment/configuration files
- container files
- systemd files
- Nginx or reverse proxy configs
- Proxmox, infrastructure, or automation files if relevant
- `.gitignore`
- `.env.example` or documented secret/config templates
- scripts, task runners, Makefiles, Justfiles, package scripts, or project-specific tooling
- logs or sample outputs only if safe and relevant

## Read-only command guidance

Acceptable read-only commands may include, when relevant:

- `pwd`
- `ls`
- `find`
- `rg`
- `grep`
- `cat`
- `sed -n`
- `git status --short`
- `git branch --show-current`
- `git log --oneline -n 10`
- `git diff --stat`
- `git diff --check`
- package manager inspection commands that do not install, update, resolve, cache, generate, or modify anything
- test discovery commands that do not write artifacts, if safe
- config inspection commands that do not mutate state

Do not run any command if you are not confident it is read-only. Instead, list it as recommended validation.

## Severity guidance

Use severity consistently:

- Critical: likely data loss, credential exposure, production outage, destructive operation, major security issue, or plan cannot safely proceed.
- High: likely implementation failure, broken deployment, incorrect architecture assumption, missing mandatory validation, unsafe migration/rollback, or material mismatch with repo reality.
- Medium: correctness, maintainability, compatibility, observability, or validation weakness that should be fixed before execution but is not immediately dangerous.
- Low: useful improvement, optional hardening, clarity issue, or minor maintainability concern.

Blocking issues are Critical and High.

Non-blocking issues are Medium and Low.

Every finding must identify the challenged plan assumption and the evidence, uncertainty, or failure mode behind the challenge.

## Verdicts

Choose exactly one verdict:

- Ready for the implementing agent to execute
- Needs minor correction before execution
- Needs major correction before execution
- Unsafe / do not execute as written
- No significant findings remain

Use “No significant findings remain” only when all of these are true:

- all Critical and High findings are resolved or explicitly superseded
- no Medium finding remains that affects correctness, safety, security, deployment reliability, data integrity, maintainability, or validation quality
- any remaining Low findings are clearly optional
- the plan matches actual repository/environment evidence
- validation steps are realistic and appropriate for this repository/environment
- stale external assumptions have been verified or explicitly called out as unresolved
- material plan claims have been adversarially checked
- validation steps have been attacked for false positives and remain meaningful
- rollback/safety guidance is adequate for the risk level of the planned change

When this threshold is met, use verdict “No significant findings remain” and state that the audit/fix loop can stop.

## Output rules

Be technical, direct, and evidence-backed.

Do not over-praise the plan. Do not use performative agreement language.

Keep “What the plan gets right” concise.

Do not include commands you did not actually run in “Read-only validation performed.”

Do not include raw secrets or sensitive values. If secret exposure is relevant, describe the class of sensitive value without printing it.

Use stable issue IDs:

- First audit: `CR-001`, `CR-002`, etc.
- Follow-up new issues: `CR-NEW-001`, `CR-NEW-002`, etc.
- Reuse prior issue IDs when tracking prior findings.

## Output format for first audit

Use this exact structure.

### Executive summary

Briefly state whether the implementation plan is ready for the implementing agent to execute, needs correction, or should not be used as written.

Mention whether internet research was required and summarize any major stale-assumption findings.

### Verdict

Choose exactly one verdict from the verdict list.

### Audit loop status

- Audit type: First audit
- Plan path:
- Significant findings remaining: Yes / No
- Blocking issue count:
- Non-blocking issue count:

### What the plan gets right

List accurate, useful, or well-aligned parts of the plan. Keep this concise.

### Adversarial review performed

Briefly list the adversarial passes performed and the strongest plan assumptions, validation claims, safety claims, and failure modes tested.

Include areas that could not be checked and why.

Do not list full findings here; put findings in the issue sections.

### Blocking issues

Include Critical and High severity issues here.

If none, state: None found.

For each issue, use this format:

#### CR-001: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Plan reference:
- Finding:
- Repository evidence:
- External research evidence:
- Why it matters:
- Recommended action for the implementing agent:
- Suggested validation:

If no internet research was needed for an issue, write:

- External research evidence: Not applicable.

### Non-blocking issues

Include Medium and Low severity issues here.

If none, state: None found.

Use the same issue format:

#### CR-002: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Plan reference:
- Finding:
- Repository evidence:
- External research evidence:
- Why it matters:
- Recommended action for the implementing agent:
- Suggested validation:

### Missing considerations

List important items the plan should address but does not, such as tests, docs, migrations, rollback, compatibility, performance, security, secrets, permissions, backups, monitoring/logging, deployment order, failure handling, observability, operator instructions, stale external dependency assumptions, adversarial failure modes, and validation false positives.

For each missing item, say whether it is blocking or non-blocking.

### Internet research performed

List each external source consulted.

For each source, include:

- Source name:
- URL:
- Access date:
- What it was used to verify:
- Relevant conclusion:

If no internet research was necessary, state why.

If internet research was needed but unavailable, state what could not be verified.

### Items the implementing agent should verify before correcting the plan

List specific things the implementing agent should verify in the repository/environment before changing the implementation plan or implementing anything.

### Suggested corrections for the implementing agent's plan

Provide an actionable checklist of changes the implementing agent should make to its implementation plan before implementation.

Do not rewrite the entire plan unless the original plan is fundamentally unsafe or unusable.

### Read-only validation performed

List the commands and inspections actually performed.

Do not include commands you did not run.

For each command or inspection, summarize what it established.

### Recommended implementation validation

List commands or checks the implementing agent should run after correcting and implementing the plan.

Only include commands that make sense for this repository/environment.

Mark commands that may write artifacts as “run only after implementation.”

### Final recommendation

State exactly what should happen next. Choose one:

- The implementing agent may proceed with the plan as written
- The implementing agent should revise the plan using the findings above
- The implementing agent should replace the plan entirely
- The user should provide specific missing information before the implementing agent proceeds
- No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

Include this ledger exactly.

- Plan path:
- Audit round:
- Open issue IDs:
- Resolved issue IDs:
- Superseded issue IDs:
- Significant findings remaining: Yes / No
- Next audit should focus on:

## Output format for follow-up audits

Use this exact structure.

### Executive summary

Briefly state whether the implementing agent’s corrections resolved the prior findings and whether significant findings remain.

Mention whether new internet research was required.

### Verdict

Choose exactly one verdict from the verdict list.

### Audit loop status

- Audit type: Follow-up audit
- Plan path:
- Prior audit issue count:
- Resolved issue count:
- Still open issue count:
- Partially resolved issue count:
- New issue count:
- Regression count:
- Significant findings remaining: Yes / No

### Adversarial review performed

Briefly list the adversarial passes performed in this follow-up audit, including prior fixes retested, new assumptions attacked, validation claims retested, and areas that could not be checked.

Do not list full findings here; put findings in the issue sections.

### Prior findings status

For each prior issue, use this format:

#### CR-001: Original short title

- Previous severity:
- Current status: Resolved / Still open / Partially resolved / Superseded / Cannot verify
- Evidence:
- Remaining action for the implementing agent:

### New blocking issues

Include new Critical and High severity issues here.

If none, state: None found.

Use this format:

#### CR-NEW-001: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Plan reference:
- Finding:
- Repository evidence:
- External research evidence:
- Why it matters:
- Recommended action for the implementing agent:
- Suggested validation:

### New non-blocking issues

Include new Medium and Low severity issues here.

If none, state: None found.

Use this format:

#### CR-NEW-002: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Plan reference:
- Finding:
- Repository evidence:
- External research evidence:
- Why it matters:
- Recommended action for the implementing agent:
- Suggested validation:

### Regressions

List any issues that were previously resolved or absent but are now present.

If none, state: None found.

### Internet research performed

List any new external sources consulted during this follow-up audit.

If no new internet research was necessary, state why.

If internet research was needed but unavailable, state what could not be verified.

### Read-only validation performed

List the commands and inspections actually performed.

Do not include commands you did not run.

For each command or inspection, summarize what it established.

### Recommended implementation validation

List commands or checks the implementing agent should run after correcting and implementing the remaining issues.

Only include commands that make sense for this repository/environment.

Mark commands that may write artifacts as “run only after implementation.”

### Final recommendation

State exactly what should happen next. Choose one:

- The implementing agent may proceed with the plan as written
- The implementing agent should revise the plan using the findings above
- The implementing agent should replace the plan entirely
- The user should provide specific missing information before the implementing agent proceeds
- No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

Include this ledger exactly.

- Plan path:
- Audit round:
- Open issue IDs:
- Resolved issue IDs:
- Superseded issue IDs:
- Significant findings remaining: Yes / No
- Next audit should focus on:

## Deliverables

For every audit, provide:

- structured read-only audit
- evidence-backed findings
- adversarial checks performed
- material assumptions challenged
- validation false positives considered
- stable issue IDs
- status of prior issues during follow-up audits
- suggested corrections for the implementing agent
- read-only validation actually performed
- internet research performed, if applicable
- recommended implementation validation
- remaining assumptions or unknowns

Do not make changes.
