# GitHub Workflow Standard 1.9

- **Status:** Active; immutable package version 1.9.
- **Owner:** Project standards / repository template.
- **Last updated:** 2026-09-01.
- **Scope:** GitHub work discipline for organization-owned repositories — issues as authorized work contracts, organization-level typed issue metadata, pull requests as execution evidence, and the repo-local agent skill that binds sessions to that discipline.

---

## 1. Purpose

GitHub is the durable control plane for work in an organization-owned repository. An issue is the authorized contract for a unit of work, its organization-level fields carry the typed operational metadata that drives lifecycle decisions, and a pull request is the evidence that the contract was executed. This standard packages that operating model so a consuming repository receives one versioned, upgradeable copy of it instead of restating it as local advice.

The package delivers the model to agent sessions. The managed instruction block routes ordinary work state in every session, including delegated workers that load no skill; the packaged skill carries the judgment behind it and is loaded for triage, an organization-schema audit, a T0 or governing-relationship judgment, or uncommon recovery. The same discipline applies across harnesses, repositories, and sessions.

## 2. Applicability

This standard applies to repositories owned by a GitHub organization.

Personal-account repositories are out of scope. Organization-level issue fields do not exist outside an organization, and this package defines no degraded fallback that operates without them.

## 3. Configuration

The package accepts exactly two options, both required.

| Option | Type | Meaning |
| --- | --- | --- |
| `organization` | string | Login of the GitHub organization that owns the consuming repository. Must be nonempty. |
| `harnesses` | array | Agent harnesses that receive the managed instruction block. Each entry is `claude-code` or `codex`. Must be nonempty. |

Unknown options and empty values are rejected by [`config.schema.json`](config.schema.json).

```toml
[standards.github-workflow]
enabled = true
version = "1.9"

[standards.github-workflow.config]
organization = "example-org"
harnesses = ["claude-code", "codex"]
```

The package itself is organization-agnostic: no organization login appears in any packaged artifact. The `organization` option is the single place a consumer names its own organization.

## 4. What the package delivers

Reconcile places the following in the consuming repository. Everything is `policy = "managed"`: the control plane owns the bytes, reports hand edits as drift, and replaces them on the next reconcile.

| Delivered | Path | Delivered when |
| --- | --- | --- |
| Agent skill | `.agents/skills/github-workflow/SKILL.md` and `.claude/skills/github-workflow/SKILL.md` | always |
| Six references | `.agents/skills/github-workflow/references/` and `.claude/skills/github-workflow/references/` — `field-vocabulary.md`, `issue-structure.md`, `org-schema.yaml`, `pr-standard.md`, `review-checklist.md`, `summary-format.md` | always |
| `gh-workflow` binary | `.agents/skills/github-workflow/bin/gh-workflow` and `.claude/skills/github-workflow/bin/gh-workflow`, mode `0755` | always |
| Rendered policy | `.standards/packages/github-workflow/policy.toml` | always |
| Codex skill companion | `.agents/skills/github-workflow/agents/openai.yaml` | `harnesses` contains `codex` |
| Managed instruction block | `CLAUDE.md`, scope `block:github-workflow` | `harnesses` contains `claude-code` |
| Managed instruction block | `AGENTS.md`, scope `block:github-workflow` | `harnesses` contains `codex` |

The managed block routes ordinary work on its own; the skill carries the judgment the block deliberately omits and loads a reference only when a decision needs it. The binary carries the mechanical half: eleven non-interactive subcommands — `audit`, `new`, `set`, `close`, `reopen`, `summary`, `receipt`, `check`, `ready`, `merge`, `admission` — that apply, validate, and render what the agent decides. It is a static linux/amd64 build with no consumer toolchain requirement, and it runs under the operator's existing `gh` authentication; the package embeds no credentials. Version 1.9 ships that platform only; a binary that is missing or will not run is a stop-and-report condition, never a reason to hand-build the `gh` call it would have made.

The superseded MCP-first proposal is retired. `gh-workflow` uses the operator's existing `gh` authentication and the GitHub REST API only. This package provides no MCP read or mutation path and no `issue_read` body-escaping procedure.

### What 1.9 changed

1.9 gives the admission rule a vocabulary that fits a repository whose work lands on a long-lived integration branch, an exemption for Agent Handoff bookkeeping, and — for the first time — an executable check (ADR 0031; issues #203, #218). It adds four configuration options, all optional and all defaulted, so an upgrade from 1.8 that changes nothing behaves exactly as 1.8 did.

**Branch classes.** The default branch and, when the consumer declares one through `integration_branch`, a single long-lived integration branch are *governed*. Everything else is a topic branch, ungoverned while it is open; its commits are admitted when they land on a governed branch. Through 1.8 the rule attached to "the default branch" alone, which in this topology is reached only by fast-forward — so the obligation attached at no moment at all, and the orphaned `construction branch` phrase 1.8's `pr-standard.md` named once and defined nowhere is deleted rather than defined.

**Four admission classes, one trailer each.** `T0`, `PR #N`, `handoff`, and `release`. The load-bearing addition is `PR #N`: `merge --pr N` writes it into the merge or squash commit it creates, so pull-request provenance becomes an offline-checkable fact instead of something an author must remember. Subject heuristics were measured and rejected — over one 362-commit corpus, 29 subjects ended in `(#N)` against 4 merged pull requests.

**The handoff exemption.** A commit whose every path lies in `docs/handoff/**`, `docs/STATUS.md`, or `docs/TODO.md` is admitted directly, carrying `Workflow-Admission: handoff`. The set is fixed by the standard and `policy.toml` cannot widen it: an extensible exempt set is a bypass surface an agent could use on its own change. A **mixed** commit — any handoff path plus any other path — is not a handoff commit and takes the pull-request route.

**`gh-workflow admission --branch B [--since REF] [--offline]`.** The eleventh subcommand classifies every commit in a range, exits 1 listing the commits no class admits with the trailer or route each needs, and exits 0 only when every commit is admitted. It verifies a `PR #N` trailer against the merged pull request when authenticated and falls back to the trailer alone under `--offline`. `admission_floor` records where enforcement begins, because adoption cannot rewrite history and a permanently red control is an ignored one. **Nothing runs it for you:** this package contributes no workflow to `.github/`, so a repository that has not wired it into its own CI has the rule and no coverage.

Two ceilings were paid for by displacement rather than raised. `SKILL.md` stays within NFR-006's 70 lines and 12,000 bytes: the lifecycle preconditions it restated now live only in `pr-standard.md`'s coherence table, which `ready` and `merge` enforce anyway. The managed block stays within NFR-003's 2,400 bytes: the `Wait for CI` routing row — the one row that mutates nothing and costs at most one extra call when forgotten — moved out of the block, and `SKILL.md`'s routing table still carries it.

### What 1.8 changed

1.8 is a correction release. It changes no option, no subcommand, and no gate outcome; an upgrade from 1.7 is a version bump. The rendered `policy.toml` moves by exactly one line — `package_version`, which every cut stamps with its own version — and its policy values are 1.7's.

**The risk vocabulary is stated once, and the refusal repeats it.** 1.7's `pr-standard.md` showed `Change risk: R2` while the Ready gate accepted only the four full spellings `org-schema.yaml` declares, so a PR body copied from the shipped example was refused (issue #202). The example and the surrounding prose in `pr-standard.md`, and the risk ladder in `review-checklist.md`, now carry `R1 Low`, `R2 Moderate`, `R3 High`, `R4 Critical` — the spellings `org-schema.yaml` has declared all along, and which it therefore did not need to change. `GHW-PR-READY-RISK-INVALID` and `GHW-PR-READY-RISK-MISSING` now name those four values in the finding's own message rather than only in its remediation, because the human envelope prints the message and drops the remediation — an operator who never asks for JSON previously saw the constraint without the vocabulary that satisfies it.

### What 1.7 changed

1.7 makes pull-request admission part of the package instead of leaving it to repository convention, and it costs no configuration change: the two options, their meanings, and every rendered `policy.toml` value outside the `package_version` stamp are exactly 1.6's, so an upgrade is a version bump.

**Two admission classes.** A change is either a T0 direct commit — an unambiguous prose repair that touches no protected surface, stays outside active governed work, fits three files and thirty changed lines, and carries exactly one `Workflow-Admission: T0` trailer — or it goes through a pull request. The predicate is conjunctive and semantic; the file and line ceiling is only a blast-radius backstop. No subcommand classifies a change as T0, because the deciding conditions are judgments about meaning. `git log --grep 'Workflow-Admission: T0'` is the on-demand retrospective audit, and there is no routine report and no ledger.

**Every PR declares one relationship.** Under an exact `## Governing work` heading a PR states `Final: #N`, `Supporting: #N`, or `Standalone`. A Final claims to satisfy every remaining acceptance criterion of its Issue; a Supporting contributes without claiming completion; a Standalone owns its own outcome and declares its own `Change risk`. One Issue may have any number of Supporting PRs and at most one open Final.

**Draft first, then two paired commands.** Agent-created PRs are drafts, so Ready is a real boundary rather than a state anything infers from openness. `ready --pr N` revalidates, synchronizes a Final's Issue from `In progress` to `In review`, marks the PR ready, and emits one receipt. `merge --pr N` revalidates, admits by the repository's permitted method, observes the outcome, and converges a merged Final's Issue to `Done` — Supporting and Standalone merges stay lifecycle-neutral. `close --pr N --as OUTCOME --reason S` is the only route for abandoning an open Final: it writes an immutable disposition comment before closing. Each is idempotent and resumable, so a partial failure is recovered by rerunning the same command.

**One finding model, three surfaces.** `check`, `receipt`, and `summary` project the same typed findings from one validation engine across six categories — Blocked, Needs definition, PR admission blocked, Synchronization required, Disposition required, Target date passed — filtered by observed state, so a draft is judged structurally and a terminal PR is judged on disposition. Findings are never persisted as a phase. `--output json` returns one envelope for every subcommand, with a stable finding code, the gate that ran, and the status of each mutation step.

**Receipts stop being ceremony.** Through 1.6 the guidance required a receipt immediately after every creation. From 1.7 a receipt is a projection of observed state: the paired commands emit one each, raw PR creation needs none, and an agent asks for one when the current picture is worth having. That removes a mandatory round trip from every creation without losing the visibility it existed for.

A PR opened under the older conventions is repaired when it is next touched by a summary, check, ready, or merge run. Nothing scans for incompatible PRs, and no terminal PR's evidence is rewritten.

### What 1.6 changed

One rule changes, in the skill and in the managed instruction block: discovered work no longer has to become an issue before the session ends. A related finding the session can address is fixed in place when the consuming repository owns it; a finding owned by an upstream dependency inside the organization is filed against that dependency's repository; and only a finding large enough to warrant a full separate session goes to the operator as a question — file it, or take it now. The rule it replaces produced issues nobody needed for defects the session had already fixed. It is stated in both the skill and the block because the block binds sessions that never load the skill, and the two references that restated the old rule follow it: `pr-standard.md` now describes disposition rather than issue creation, and `summary-format.md` adds “fixed in place” to the dispositions a discovered follow-up may report.

Nothing else changed at 1.6: the delivered tree, 1.5's eight subcommands, the configuration contract, and every other invariant were carried forward unchanged.

### What 1.5 changed

Two cuts, both aimed at what a session actually pays for.

`ledger` is gone, and with it the generated `docs/GH-WORKFLOWS.md`. The subcommand was the package's only writer into a consumer checkout; the file it produced was a timestamped snapshot of state GitHub already holds, outside the payload digests and outside drift-check, so nothing could keep it honest. Every remaining subcommand reads. A consumer upgrading from 1.4 or earlier keeps whatever copy of that file it committed — the package will not delete consumer content — and [`adopt.md`](adopt.md) states the one manual step. `gh-workflow ledger` now exits 2 as an unknown subcommand.

The skill's guidance was restructured against measured session behavior: `SKILL.md` is one ~70-line read carrying a single complete routing-and-flag table, `field-vocabulary.md` keeps only the two things the tool cannot tell you in a refusal (the `Workflow` value meanings and the field-pinning matrix), and the managed instruction block now carries the routing table itself, because delegated workers routinely mutate work state without ever loading a skill. The per-session binary preflight and the instruction to confirm flags with `gh-workflow help` are both removed: they cost calls and prevented nothing. Guidance also now states that admitting work to `Ready` and setting `Execution mode` (short of `Unattended agent`) are the agent's own decisions, which is what `check` always implemented. And `check` no longer refuses `Ready` over an empty `Target date`: the field is pinned to three Issue Types, but the package has always documented empty as a valid, expected state, so the gate now agrees with the reference instead of sending agents around itself (project-standards issue #192).

### Two skill trees, one set of bytes

Every skill file is delivered twice: once under `.agents/skills/github-workflow/` and once under `.claude/skills/github-workflow/`. Claude Code discovers project skills only under `.claude/skills/`, while `.agents/skills/` is Codex's convention, so a single tree leaves the skill invisible to one harness or the other. Both copies come from the same packaged source and carry the same declared digest, so they are byte-identical by construction and drift-check reports either one that is edited.

They are copies rather than symlinks deliberately. A symlink checks out as a plain text file containing the link path on a Windows clone without Developer Mode, which would install unusable content as the skill body. The redundancy costs disk and buys a delivery that does not depend on the consumer's filesystem or clone settings.

The `summary` and `receipt` output is printed, never written, but it is written _into_ Markdown by whoever relays it, so it still satisfies the markdown-tooling standard's default Prettier and markdownlint configuration unmodified. An underscore in a title is escaped only where Markdown could read it as an emphasis marker — at a word edge, next to punctuation, or in a run of two or more — because Prettier strips a redundant escape and an unconditional one made a relayed table fail the consumer's own `prettier --check`. A `|`, which would silently add a column, always keeps its escape.

`gh-workflow new` also derives the Issue Type vocabulary it asks for from the loaded `org-schema.yaml` rather than from a count written into the tool, so guidance text stays correct when a later payload version changes the baseline.

Three invariants hold across all of it:

- **Managed.** No delivered unit is create-only, so every one stays upgradeable and every hand edit stays visible.
- **Offline and deterministic.** Reconciliation, validation, drift-check, and upgrade touch no network. Repeated runs converge instead of accumulating changes. Only the `gh-workflow` binary talks to GitHub, and only when an agent runs it.
- **Organization-agnostic.** No organization login, repository name, or other environment-specific value appears in a packaged source. Those values enter only through rendered consumer outputs.

## 5. Ownership boundary

The package owns its delivered artifacts and the discipline they describe. It does not own live GitHub state.

- Organization schema — issue types and organization-level issue fields — is applied by a human. The package compares live schema against its versioned baseline and reports differences; it never mutates them.
- Admission is the package's from 1.7: a change is either a T0 direct commit or a pull request, and both the T0 predicate and the PR content standard are packaged. What a repository requires on top of that — required checks, protected branches, review rules — stays repository policy, and nothing in the package routes around it.
- Repository rulesets, branch protection, and merge gating stay outside the package. It never manipulates the mechanisms that judge work performed under it.
- Unmarked content in a consumer's agent-instruction files stays consumer-owned; only the package's bounded managed block is package-owned.

## 6. Adoption

[`adopt.md`](adopt.md) covers the package-specific choices. The shared control-plane lifecycle — initialization, preview, apply, disable, removal, and catalog updates — is documented by `project-standards`.
