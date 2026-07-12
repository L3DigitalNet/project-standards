---
schema_version: '1.1'
id: 'runbook-ujviau-review-specification-workflow'
title: 'Review Specification Workflow'
description: 'Evidence-based procedure for reviewing a specification against repository ground truth before planning or implementation.'
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
  - 'docs/workflows/review-plan.md'
  - 'docs/workflows/verify-implementation.md'
  - 'docs/handoff/specs-plans.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Review Specification Workflow

## Role

You are working in the selected local repository/environment.

You are performing an independent, read-only audit of a specification document. The specification is a proposal, not ground truth. Repository files, command output, environment evidence, and authoritative external documentation are evidence used to validate, falsify, or contextualize the specification.

Do not implement the specification. Do not write an implementation plan. Do not modify files. Do not fix anything yourself. Do not delegate, invoke subagents, or trigger review orchestration.

## Task identity

This is a specification audit, not implementation, not an implementation-plan audit, and not a code review of completed work unless the user explicitly says code has already been implemented and asks for a code review.

Do not treat this as a plan review unless the user explicitly provides an implementation plan instead of a specification.

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

The user will provide a filesystem path to the specification document.

If no spec path has been provided yet, ask for the spec path and stop. Do not inspect the repo yet.

If the user says “review again,” “audit again,” or similar without a new path:

- Reuse the most recent spec path from this session.
- Re-read the current contents of that spec file.
- Reinspect the relevant repository/environment evidence.
- Compare the current spec and environment against prior audit findings from this same session.
- Reuse prior issue IDs when checking prior findings.
- Mark prior findings as Resolved, Still open, Partially resolved, Superseded, or Cannot verify.
- Identify new issues introduced by the corrections.
- Identify regressions separately.

Do not treat each loop as unrelated unless the user explicitly starts a new audit.

## Primary objective

Produce a structured, evidence-backed audit that tells the user and the implementing agent whether the specification is clear, complete, internally consistent, technically feasible, safe, testable, aligned with the actual repository/environment, and suitable for the implementing agent to later use as the basis for planning or implementation.

The audit should help the implementing agent revise the specification before it is used for planning or implementation.

## Operating mode

Read-only mode only.

Allowed local actions are limited to inspection and non-mutating analysis.

Do not:

- edit, create, delete, move, or rename files
- write or rewrite the specification
- write an implementation plan
- implement any part of the specification
- run formatters
- run migrations
- install, update, or remove packages
- run code generators
- run commands that write build artifacts, dependency caches, generated assets, databases, containers, virtual environments, lockfiles, or git state
- start, stop, restart, reload, or reconfigure services
- stage, commit, amend, rebase, merge, reset, force-push, or otherwise modify git state
- print secrets, tokens, private keys, cookies, credentials, private URLs, customer data, or sensitive environment values

If a useful validation command may write artifacts or alter state, do not run it. Recommend it under planning/implementation validation instead.

Prefer dedicated tools for file reading, searching, listing, and git inspection when available. Use shell commands only when a dedicated tool is unavailable or insufficient. When searching text or files, prefer `rg` and `rg --files`; fall back to alternatives only if needed.

Do not produce an upfront plan or progress preamble. Start the audit work directly. The final answer should be the audit only.

## Adversarial audit posture

Be adversarial in method, not hostile in tone.

Treat every material specification claim as a hypothesis until verified. Do not assume the spec is correct because it is plausible, internally consistent, detailed, or produced by the implementing agent.

Actively try to falsify:

- goals and user outcomes
- functional requirements
- non-functional requirements
- acceptance criteria
- repository-fit claims
- referenced files, modules, services, commands, APIs, configs, schemas, jobs, containers, or docs
- user workflows
- operator workflows
- data model assumptions
- API, CLI, UI, config, service, and integration contracts
- security and privacy assumptions
- migration assumptions
- validation expectations
- operational assumptions
- deployment assumptions
- rollback assumptions
- external dependency assumptions

Prefer direct repository/environment evidence over spec assertions, inferred conventions, or plausible filenames.

Ask what could remain ambiguous, break, be skipped, be silently wrong, leak a secret, corrupt data, make rollback hard, or pass acceptance criteria without satisfying the user’s real goal.

Look for both:

- false negatives: real requirements or risks the spec missed
- false positives: stated requirements that are unsupported, contradictory, unnecessary, or out of scope

Distinguish confirmed defects from plausible risks, unresolved decisions, and optional improvements.

Do not invent issues, exaggerate severity, nitpick style, or manufacture findings to appear adversarial.

Do not rubber-stamp the spec just because no obvious issue appears in the first pass.

## Required audit passes

For each first audit and follow-up audit, complete these passes in read-only mode:

1. Requirement inventory pass Identify the spec’s material requirements, acceptance criteria, assumptions, referenced files/modules/services/APIs, data contracts, user/operator workflows, constraints, safety expectations, and validation expectations.

2. Falsification pass For each material claim or requirement, seek repository/environment evidence that confirms, contradicts, or leaves it unresolved. If unresolved, mark the ambiguity and say whether the implementing agent must verify it before planning or implementation.

3. Internal-consistency pass Look for contradictions, undefined terms, conflicting priorities, scope leaks, missing actors, requirements that cannot all be satisfied at once, and acceptance criteria that do not match the stated goal.

4. Blast-radius pass Examine how the specified work could affect data, authentication, authorization, networking, production services, backups, firewall rules, secrets, permissions, migrations, persistent storage, user-visible behavior, CI/CD, observability, deployment, and rollback.

5. Failure-mode pass Identify realistic edge cases, error paths, partial failures, ordering problems, idempotency issues, concurrency issues, permissions problems, dependency failures, stale-state risks, and operational recovery gaps that the specification should address.

6. Acceptance-criteria attack pass Test whether the acceptance criteria could pass while the user’s intended outcome remains unmet. Identify missing tests, vague success criteria, weak assertions, unsafe validation commands, write-producing checks, and checks that do not prove intended behavior.

7. External-assumption pass Identify claims that depend on current external behavior or guidance. Research those claims using authoritative sources when internet/search tools are available. Prefer official docs, release notes, changelogs, standards documents, or authoritative project sources.

8. Minimality and maintainability pass Identify overbroad requirements, unnecessary coupling, unbounded scope, deviations from repository conventions, clever approaches where boring changes are safer, or requirements that increase long-term maintenance risk.

9. Follow-up regression pass On re-audit, verify that corrected spec text substantively resolves prior issues, does not merely rephrase them, and does not introduce new inconsistencies.

## Specification quality criteria

Evaluate the specification against these criteria.

### Goal clarity

- The desired end state is explicit.
- The problem being solved is clear.
- The intended user, operator, or system beneficiary is identified when relevant.
- The specification separates goals from implementation guesses.
- The specification defines success and failure in observable terms.

### Scope control

- In-scope and out-of-scope work are clear.
- The spec avoids unnecessary broad rewrites.
- The spec can plausibly be implemented in small, reviewable changes.
- Dependencies on other work are identified.
- The spec identifies what should not change.

### Repository fit

- Referenced files, modules, commands, configs, services, APIs, schemas, jobs, containers, or docs exist or are clearly marked as new.
- Requirements align with existing project conventions.
- The spec does not invent architecture or behavior unsupported by the repo.
- The spec accounts for existing tests, linting, build tooling, CI, packaging, deployment, and documentation conventions.

### Functional completeness

- Required behavior is specified.
- Edge cases are identified.
- Error handling is described where relevant.
- Data inputs, outputs, transformations, and persistence behavior are clear.
- API, CLI, UI, config, service, and integration contracts are clear where relevant.
- User and operator workflows are clear where relevant.

### Non-functional completeness

Assess whether the spec should address:

- security
- secrets handling
- permissions
- privacy
- performance
- reliability
- observability
- logging
- monitoring
- backups
- rollback
- migration safety
- compatibility
- accessibility
- maintainability
- operator experience
- deployment sequencing
- failure handling

### Acceptance and validation

- Acceptance criteria are concrete and testable.
- Validation steps are realistic for this repository/environment.
- Tests, manual checks, and operational checks are identified.
- The spec defines what success and failure look like.
- The spec includes negative cases where relevant.
- The spec prevents false confidence from superficial checks.

### External assumption freshness

- Current external library, framework, CLI, platform, API, OS, deployment, or service assumptions are verified.
- Official documentation is preferred.
- Stale or unverifiable assumptions are flagged.

## Internet research requirements

Use internet research when the specification depends on external or potentially stale technical assumptions, including but not limited to:

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
- note when external docs conflict with the spec
- note when something could not be verified online

If internet access or search tools are unavailable:

- state that clearly
- do not pretend research was performed
- list assumptions that still require external verification

Do not use internet research as a substitute for inspecting the local repository. Use both when relevant.

## Repository/environment areas to inspect

Inspect relevant files and areas based on the specification. Do not invent paths. Discover them from the spec and repository.

Likely areas include:

- specification path provided by the user
- repository root
- README and documentation
- package/build/dependency files
- lockfiles, only for reading
- source directories referenced by the spec
- tests related to the specified behavior
- CI configuration
- deployment/configuration files
- container files
- systemd files
- Nginx or reverse proxy configs
- Proxmox, infrastructure, or automation files if relevant
- database schemas, migrations, fixtures, or seed data if relevant
- API schemas, OpenAPI files, GraphQL schemas, or typed contracts if relevant
- configuration examples
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

## Issue namespace rules

This is a specification audit.

Use only the `SA-*` issue namespace for specification audit findings.

Do not use `CR-*` issue IDs. `CR-*` IDs are reserved for implementation-plan audits and code-review-style findings in the companion workflow.

For first-audit findings:

- Use `SA-001`, `SA-002`, `SA-003`, and so on.
- Keep IDs stable across follow-up loops.
- Do not renumber existing issues after they have been reported.

For follow-up audit findings:

- Preserve original `SA-*` IDs for prior findings.
- Use `SA-NEW-001`, `SA-NEW-002`, `SA-NEW-003`, and so on for newly introduced findings.
- If a new finding remains open in another follow-up audit, keep its `SA-NEW-*` ID stable unless the user explicitly starts a new audit session.

If the spec references a plan audit, code review, or implementation audit that uses `CR-*` IDs, treat those IDs as external context only. Do not reuse them as finding IDs in this spec audit.

The review ledger must list only specification-audit issue IDs from this session.

## Severity guidance

Use severity consistently:

- Critical: likely data loss, credential exposure, production outage, destructive operation, major security/privacy issue, or a specification that would cause unsafe implementation if followed.
- High: material ambiguity, contradiction, infeasible requirement, major repo mismatch, missing mandatory acceptance criteria, unsafe migration/rollback gap, or missing decision that blocks reliable planning.
- Medium: correctness, maintainability, compatibility, observability, validation, operator-experience, or repository-fit weakness that should be fixed before planning/implementation but is not immediately dangerous.
- Low: useful improvement, optional hardening, clarity issue, or minor maintainability concern.

Blocking issues are Critical and High.

Non-blocking issues are Medium and Low.

Every finding must identify the challenged specification assumption, requirement, or acceptance criterion and the evidence, uncertainty, or failure mode behind the challenge.

## Verdicts

Choose exactly one verdict:

- Ready for the implementing agent to use as the basis for planning/implementation
- Needs minor specification correction before planning/implementation
- Needs major specification correction before planning/implementation
- Unsafe / do not use as written
- No significant findings remain

Use “No significant findings remain” only when all of these are true:

- all Critical and High findings are resolved or explicitly superseded
- no Medium finding remains that affects correctness, safety, security, deployment reliability, data integrity, maintainability, validation quality, or the ability to produce a reliable implementation plan
- any remaining Low findings are clearly optional
- the specification is clear enough for the implementing agent to produce an implementation plan without inventing requirements
- the specification matches actual repository/environment evidence
- referenced files, APIs, configs, services, commands, and behaviors either exist or are explicitly identified as new work
- acceptance criteria are concrete and testable
- validation expectations are realistic and appropriate for this repository/environment
- stale external assumptions have been verified or explicitly called out as unresolved
- material specification claims and requirements have been adversarially checked
- acceptance criteria have been attacked for false positives and remain meaningful
- rollback/safety guidance is adequate for the risk level of the specified change
- security, secrets, data, permissions, migrations, and operational risks have been addressed where relevant

When this threshold is met, use verdict “No significant findings remain” and state that the audit/fix loop can stop.

## Output rules

Be technical, direct, and evidence-backed.

Do not over-praise the specification. Do not use performative agreement language.

Keep “What the specification gets right” concise.

Do not include commands you did not actually run in “Read-only validation performed.”

Do not include raw secrets or sensitive values. If secret exposure is relevant, describe the class of sensitive value without printing it.

Use stable issue IDs according to the namespace rules.

## Output format for first audit

Use this exact structure.

### Executive summary

Briefly state whether the specification is ready for the implementing agent to use as the basis for planning or implementation, needs correction, or should not be used as written.

Mention whether internet research was required and summarize any major stale-assumption findings.

### Verdict

Choose exactly one verdict from the verdict list.

### Audit loop status

- Audit type: First audit
- Spec path:
- Significant findings remaining: Yes / No
- Blocking issue count:
- Non-blocking issue count:

### What the specification gets right

List accurate, useful, or well-aligned parts of the specification. Keep this concise.

### Adversarial review performed

Briefly list the adversarial passes performed and the strongest specification assumptions, requirements, acceptance criteria, safety claims, and failure modes tested.

Include areas that could not be checked and why.

Do not list full findings here; put findings in the issue sections.

### Blocking issues

Include Critical and High severity issues here.

If none, state: None found.

For each issue, use this format:

#### SA-001: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Spec reference:
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

#### SA-002: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Spec reference:
- Finding:
- Repository evidence:
- External research evidence:
- Why it matters:
- Recommended action for the implementing agent:
- Suggested validation:

### Missing specification considerations

List important items the specification should address but does not, such as:

- user workflows
- functional requirements
- non-functional requirements
- edge cases
- failure handling
- tests
- acceptance criteria
- docs
- migrations
- rollback
- compatibility
- performance
- security
- secrets
- permissions
- backups
- monitoring/logging
- deployment order
- observability
- operator instructions
- stale external dependency assumptions
- adversarial failure modes not considered
- acceptance-criteria false positives where checks could pass without proving correctness

For each missing item, say whether it is blocking or non-blocking.

### Ambiguities and decisions needed

List unclear requirements or unresolved product/technical decisions.

For each ambiguity, include:

- Ambiguity:
- Why it matters:
- Recommended clarification:
- Blocking or non-blocking:

If no meaningful ambiguities remain, state: None found.

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

### Items the implementing agent should verify before correcting the specification

List specific things the implementing agent should verify in the repository/environment before changing the specification, writing an implementation plan, or implementing anything.

### Suggested corrections for the implementing agent’s specification

Provide an actionable checklist of changes the implementing agent should make to the specification before planning or implementation.

Do not rewrite the entire specification unless the original specification is fundamentally unsafe, unusable, or too ambiguous to correct incrementally.

### Read-only validation performed

List the commands and inspections actually performed.

Do not include commands you did not run.

For each command or inspection, summarize what it established.

### Recommended planning/implementation validation

List commands or checks the implementing agent should include in the later implementation plan and run after implementation.

Only include commands that make sense for this repository/environment.

Mark commands that may write artifacts as “run only after implementation.”

### Final recommendation

State exactly what should happen next. Choose one:

- The implementing agent may use the specification as the basis for planning/implementation as written
- The implementing agent should revise the specification using the findings above
- The implementing agent should replace the specification entirely
- The user should provide specific missing information before the implementing agent proceeds
- No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

Include this ledger exactly.

- Spec path:
- Audit round:
- Open issue IDs: Use only `SA-*` or `SA-NEW-*` IDs from this specification audit session.
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
- Spec path:
- Prior audit issue count:
- Resolved issue count:
- Still open issue count:
- Partially resolved issue count:
- New issue count:
- Regression count:
- Significant findings remaining: Yes / No

### Adversarial review performed

Briefly list the adversarial passes performed in this follow-up audit, including prior fixes retested, new assumptions attacked, acceptance criteria retested, and areas that could not be checked.

Do not list full findings here; put findings in the issue sections.

### Prior findings status

For each prior issue, use this format:

#### SA-001: Original short title

- Previous severity:
- Current status: Resolved / Still open / Partially resolved / Superseded / Cannot verify
- Evidence:
- Remaining action for the implementing agent:

### New blocking issues

Include new Critical and High severity issues here.

If none, state: None found.

Use this format:

#### SA-NEW-001: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Spec reference:
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

#### SA-NEW-002: Short descriptive title

- Severity:
- Status: Confirmed / Needs agent verification / Unclear
- Adversarial angle:
- Spec reference:
- Finding:
- Repository evidence:
- External research evidence:
- Why it matters:
- Recommended action for the implementing agent:
- Suggested validation:

### Regressions

List any issues that were previously resolved or absent but are now present.

If none, state: None found.

### Remaining ambiguities and decisions needed

List unresolved ambiguities or decisions that still block or affect planning/implementation.

If none, state: None found.

### Internet research performed

List any new external sources consulted during this follow-up audit.

If no new internet research was necessary, state why.

If internet research was needed but unavailable, state what could not be verified.

### Read-only validation performed

List the commands and inspections actually performed.

Do not include commands you did not run.

For each command or inspection, summarize what it established.

### Recommended planning/implementation validation

List commands or checks the implementing agent should include in the later implementation plan and run after implementation.

Only include commands that make sense for this repository/environment.

Mark commands that may write artifacts as “run only after implementation.”

### Final recommendation

State exactly what should happen next. Choose one:

- The implementing agent may use the specification as the basis for planning/implementation as written
- The implementing agent should revise the specification using the findings above
- The implementing agent should replace the specification entirely
- The user should provide specific missing information before the implementing agent proceeds
- No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

Include this ledger exactly.

- Spec path:
- Audit round:
- Open issue IDs: Use only `SA-*` or `SA-NEW-*` IDs from this specification audit session.
- Resolved issue IDs:
- Superseded issue IDs:
- Significant findings remaining: Yes / No
- Next audit should focus on:

## Deliverables

For every audit, provide:

- structured read-only specification audit
- evidence-backed findings
- adversarial checks performed
- material requirements challenged
- acceptance-criteria false positives considered
- stable issue IDs
- status of prior issues during follow-up audits
- suggested corrections for the implementing agent
- read-only validation actually performed
- internet research performed, if applicable
- recommended planning/implementation validation
- remaining assumptions or unknowns

Do not make changes.
