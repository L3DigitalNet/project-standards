# GitHub Workflow Standard 1.1

- **Status:** Active; immutable package version 1.1.
- **Owner:** Project standards / repository template.
- **Last updated:** 2026-08-09.
- **Scope:** GitHub work discipline for organization-owned repositories — issues as authorized work contracts, organization-level typed issue metadata, pull requests as execution evidence, and the repo-local agent skill that binds sessions to that discipline.

---

## 1. Purpose

GitHub is the durable control plane for work in an organization-owned repository. An issue is the authorized contract for a unit of work, its organization-level fields carry the typed operational metadata that drives lifecycle decisions, and a pull request is the evidence that the contract was executed. This standard packages that operating model so a consuming repository receives one versioned, upgradeable copy of it instead of restating it as local advice.

The package delivers the model to agent sessions. An agent that is about to create or mutate GitHub work state loads the packaged skill first and follows its decision procedures, so the same discipline applies across harnesses, repositories, and sessions.

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
version = "1.1"

[standards.github-workflow.config]
organization = "example-org"
harnesses = ["claude-code", "codex"]
```

The package itself is organization-agnostic: no organization login appears in any packaged artifact. The `organization` option is the single place a consumer names its own organization.

## 4. What the package delivers

Reconcile places the following in the consuming repository. Everything is `policy = "managed"`: the control plane owns the bytes, reports hand edits as drift, and replaces them on the next reconcile.

| Delivered | Path | Delivered when |
| --- | --- | --- |
| Agent skill | `.agents/skills/github-workflow/SKILL.md` | always |
| Six references | `.agents/skills/github-workflow/references/` — `field-vocabulary.md`, `issue-structure.md`, `org-schema.yaml`, `pr-standard.md`, `review-checklist.md`, `summary-format.md` | always |
| `gh-workflow` binary | `.agents/skills/github-workflow/bin/gh-workflow`, mode `0755` | always |
| Rendered policy | `.standards/packages/github-workflow/policy.toml` | always |
| Codex skill companion | `.agents/skills/github-workflow/agents/openai.yaml` | `harnesses` contains `codex` |
| Managed instruction block | `CLAUDE.md`, scope `block:github-workflow` | `harnesses` contains `claude-code` |
| Managed instruction block | `AGENTS.md`, scope `block:github-workflow` | `harnesses` contains `codex` |

The skill carries the discipline and loads a reference only when a decision needs it. The binary carries the mechanical half: nine non-interactive subcommands — `audit`, `ledger`, `new`, `set`, `close`, `reopen`, `summary`, `receipt`, `check` — that apply, validate, and render what the agent decides. It is a static linux/amd64 build with no consumer toolchain requirement, and it runs under the operator's existing `gh` authentication; the package embeds no credentials. Version 1.1 ships that platform only, and the skill checks for a usable binary before its first invocation.

`docs/GH-WORKFLOWS.md` — the work-state ledger `gh-workflow ledger` regenerates — is tool-generated consumer content, not a payload artifact. It carries no digest, is excluded from drift-check, and is rewritten whole rather than merged.

Its body is a function of work state alone. From 1.1 the generated header carries the tool version and the counts but no read timestamp, so regenerating against unchanged GitHub state rewrites the same bytes and produces no diff; `ledger` reports the read time on its own stdout instead. A consumer that commits the ledger therefore sees it in a diff when work moved, and not when a session merely looked. Version 1.0 stamped the read time into the file and churned on every run.

`gh-workflow new` also derives the Issue Type vocabulary it asks for from the loaded `org-schema.yaml` rather than from a count written into the tool, so guidance text stays correct when a later payload version changes the baseline.

Three invariants hold across all of it:

- **Managed.** No delivered unit is create-only, so every one stays upgradeable and every hand edit stays visible.
- **Offline and deterministic.** Reconciliation, validation, drift-check, and upgrade touch no network. Repeated runs converge instead of accumulating changes. Only the `gh-workflow` binary talks to GitHub, and only when an agent runs it.
- **Organization-agnostic.** No organization login, repository name, or other environment-specific value appears in a packaged source. Those values enter only through rendered consumer outputs.

## 5. Ownership boundary

The package owns its delivered artifacts and the discipline they describe. It does not own live GitHub state.

- Organization schema — issue types and organization-level issue fields — is applied by a human. The package compares live schema against its versioned baseline and reports differences; it never mutates them.
- Whether a change requires a pull request is repository-local branch policy that varies by repository. This standard does not set that threshold. Once a pull request exists, its content standard applies.
- Repository rulesets, branch protection, and merge gating stay outside the package. It never manipulates the mechanisms that judge work performed under it.
- Unmarked content in a consumer's agent-instruction files stays consumer-owned; only the package's bounded managed block is package-owned.

## 6. Adoption

[`adopt.md`](adopt.md) covers the package-specific choices. The shared control-plane lifecycle — initialization, preview, apply, disable, removal, and catalog updates — is documented by `project-standards`.
