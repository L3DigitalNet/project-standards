---
title: "Project Standards - Template Repo Autopopulate"
source: "https://chatgpt.com/g/g-p-6a24ec06cda08191be0c41f4bfaefada/c/6a4da2ee-b768-83ea-98bf-d72e4689e6b5"
---

**You:**

I want to create a template repository that is a fully populated repository with all of the project standards. That way any new project can just start off with the template and there will be minimal effort for adoption. The problem I have to solve is how to remove the exposure of drift between the standard versions and the actual temple implementation.  I need a mechanism to automate updating the template repo every time a version of a standard is published or released.  This needs to be automatic.  Please help me brainstorm options and strategies.

* * *

**ChatGPT:**

I’ll frame this as an architecture problem: separate the canonical standards, generated template artifacts, release trigger, and drift detection. I’ll verify current GitHub mechanics and tie the options back to your existing standards’ versioning/adoption model.

One important constraint is already visible: a GitHub template repository is only a snapshot mechanism, not an inheritance mechanism. So the core design should not rely on GitHub’s template feature to “stay connected”; it needs a separate sync/generation pipeline.

## Bottom line

Use the **standards repo as the only source of truth** and treat the template repo as a **generated release artifact**, not a hand-maintained repository. GitHub template repositories are useful for starting new repos, but they do not maintain an upstream relationship after creation; GitHub’s own docs describe template-created branches as having unrelated histories, so you cannot rely on normal PR/merge mechanics between the template and generated descendants. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)

The best architecture is:

```
project-standards repo
  ├─ canonical standards
  ├─ scaffold fragments
  ├─ render/update tool
  └─ release workflow
        ↓ on published release
generated template working tree
        ↓ verify
project-template repo
        ↓ GitHub "Use this template"
new project repos
```

Your existing standards already point in this direction: the Python coding standard says canonical standards should live in the standards repo and be referenced from project templates, while compact agent summaries must not weaken the canonical standard.

* * *

## Recommended strategy: generated template repo with a release sync workflow

The template repo should have almost no manually edited content. It should be rebuilt from a manifest every time a standards release is published.

The standards repo owns:

```
standards/
  python/
  markdown/
  adr/
scaffolds/
  python-package/
  cli-app/
  docs-only/
  fastapi-app/
tools/
  render_template/
template-manifest.yml
```

The template repo receives:

```
.project-standards.lock.yml
.project-standards.yml
pyproject.toml
uv.lock
.python-version
.editorconfig
.prettierrc.json
.markdownlint.json
AGENTS.md
CLAUDE.md
.github/workflows/check.yml
.github/workflows/lint-markdown.yml or workflow caller
.vscode/
docs/
src/
tests/
scripts/
```

The lockfile is critical. It should say exactly what generated the template:

```YAML
generated_by: 'project-standards'
source_repo: 'L3DigitalNet/project-standards'
source_ref: 'v2.1.0'
source_sha: '<commit-sha>'
generated_at: '2026-07-07T00:00:00Z'
template_profile: 'python-cli'
standards:
  python_tooling: '2.0.0'
  python_coding: '0.4'
  markdown_frontmatter: '1.1'
  markdown_tooling: '1.0'
managed_paths:
  - 'pyproject.toml'
  - '.github/workflows/check.yml'
  - '.vscode/settings.json'
  - 'AGENTS.md'
  - 'CLAUDE.md'
artifact_hash: '<hash-of-managed-tree>'
```

Then add a **drift check** in the template repo:

```
regenerate from .project-standards.lock.yml
compare generated output to repository contents
fail CI if there is any diff in managed paths
```

That makes drift mechanically visible. If someone edits the template repo by hand, the next check fails.

* * *

## Automation flow

Use one of these two trigger patterns.

### Pattern A — standards repo pushes a PR to the template repo

This is the most direct.

On `release.published` in `project-standards`:

1. Check out the released tag.
2. Run `tools/render_template`.
3. Run all checks against the rendered template.
4. Authenticate as a GitHub App installation.
5. Clone or update the template repo.
6. Replace only manifest-owned paths.
7. Commit to a branch like `standards-sync/v2.1.0`.
8. Open a PR.
9. Auto-merge after required checks pass, or direct-push only if you decide the template repo is purely generated.

Use a GitHub App instead of a personal token. GitHub App installation access tokens can make API requests for resources owned by the installation, are attributed to the app, and expire after one hour. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation) GitHub also recommends selecting the minimum permissions required for the app. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)

### Pattern B — standards repo dispatches an update event to the template repo

This is cleaner if you want the template repo to own its own update logic.

On `release.published` in `project-standards`, call the template repo’s `repository_dispatch` endpoint with payload:

```JSON
{
  "event_type": "standards-release",
  "client_payload": {
    "standards_ref": "v2.1.0",
    "standards_sha": "<sha>"
  }
}
```

GitHub Actions supports `repository_dispatch` for activity outside GitHub Actions, and the payload is available through `github.event.client_payload`. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/actions/using-workflows/events-that-trigger-workflows) The REST endpoint for creating a repository dispatch event accepts `event_type` and `client_payload`; fine-grained tokens need repository `Contents: write`. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/rest/repos/repos)

I would prefer **Pattern A** for your setup because the standards repo is the authority. The update logic belongs beside the release logic.

* * *

## Option comparison

| Option | How it works | Drift exposure | Automation quality | Recommendation |
| --- | --- | --- | --- | --- |
| **Generated template repo from standards release** | Standards release renders and updates template repo | Very low | High | **Best default** |
| **Copier-backed template** | Template is a Copier template; updates use `copier update` | Low | Medium-high | Good if you need variable rendering and later consumer-repo updates |
| **Cruft/Cookiecutter-backed template** | Cookiecutter template plus `.cruft.json` tracking | Medium-low | Medium | Viable, but less attractive than Copier for your standards model |
| **Reusable workflows/actions only** | Repos call central workflows by tag/SHA | Low for CI, high for copied files | High | Use for CI where possible, but not sufficient alone |
| **Git submodule/subtree** | Template vendors standards as Git object | Medium | Medium | Useful for docs, awkward for repo-root config |
| **GitHub template repo only** | Manually maintain template repo | High | Low | Not enough |
| **Direct edits by agents** | Agent updates template when standards change | Very high | Low | Do not use as the control mechanism |

* * *

## Copier/Cruft angle

Copier is worth considering if you want the **same mechanism** to update both:

1. the official template repo, and
2. existing project repos created from that template.

Copier’s update flow expects a valid `.copier-answers.yml`, a Git-tagged template, and a Git-versioned destination; `copier update` reads available Git tags and can update to the latest tag. [![](https://www.google.com/s2/favicons?domain=https://copier.readthedocs.io&sz=128)Copier](https://copier.readthedocs.io/en/stable/updating/) Copier also has `copier check-update` with JSON and quiet modes for automation. [![](https://www.google.com/s2/favicons?domain=https://copier.readthedocs.io&sz=128)Copier](https://copier.readthedocs.io/en/stable/updating/)

Cruft is similar for Cookiecutter templates: it stores template commit/context in `.cruft.json`, supports update/check/diff, and documents GitHub Actions automation for detecting changes and opening PRs. [![](https://www.google.com/s2/favicons?domain=https://cruft.github.io&sz=128)Cruft](https://cruft.github.io/cruft/)

My read: **use Copier only if templating variables matter**. For your immediate “standards → official template repo” problem, a purpose-built generator is simpler and more deterministic. Copier becomes more attractive once you want to propagate template changes into dozens of already-created repos.

* * *

## Reduce copied surface area

Not every standard artifact should be copied into the template. Split artifacts into three classes:

| Class | Examples | Best treatment |
| --- | --- | --- |
| **Canonical standards** | full standards, rationale, evidence | Keep in `project-standards`; reference by pinned tag |
| **Generated scaffolds** | `pyproject.toml`, `.vscode/settings.json`, `AGENTS.md`, `CLAUDE.md`, `.editorconfig` | Render/copy into template |
| **Reusable automation** | validation workflows, markdownlint workflow, shared checks | Call centrally by release tag or SHA |

Your Markdown tooling standard already makes this split: `.markdownlint.json` and the reusable markdownlint workflow are shipped, while `.prettierrc.json` is copy-adopt only and Prettier has no reusable workflow. It also shows the intended consumer pattern for reusable workflows pinned by release tag.

For anything reusable, prefer:

```YAML
jobs:
  lint-markdown:
    uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v2
```

GitHub reusable workflows are called with `jobs.<job_id>.uses`, and external reusable workflow refs can be a SHA, release tag, or branch; GitHub says commit SHA is safest for stability/security. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)

* * *

## Drift controls to build in from day one

### 1. Managed-path manifest

Do not let the sync tool freehand the repo. It should only touch paths declared in `template-manifest.yml`.

Example:

```YAML
managed_paths:
  full_replace:
    - '.editorconfig'
    - '.markdownlint.json'
    - '.prettierrc.json'
    - '.github/workflows/check.yml'
    - '.vscode/extensions.json'
    - '.vscode/settings.json'
    - 'AGENTS.md'
    - 'CLAUDE.md'
  generated_from_templates:
    - 'pyproject.toml'
    - 'README.md'
  never_touch:
    - '.github/dependabot.yml'
    - 'docs/decisions/'
```

### 2. Generated headers

For files where comments are legal:

```
# Generated from L3DigitalNet/project-standards@v2.1.0.
# Do not edit directly. Update the source standard/scaffold instead.
```

For JSON files, use adjacent metadata in `.project-standards.lock.yml` because comments are not legal JSON.

### 3. Regeneration diff check

Template CI should run:

```Bash
uv run render-template --profile python-cli --ref "$LOCKED_REF" --output /tmp/rendered
uv run compare-managed-tree --expected /tmp/rendered --actual .
```

If the generated tree differs, CI fails.

### 4. Release artifact hash

Compute a deterministic hash over managed files and store it in `.project-standards.lock.yml`. This is stronger than “looks up to date.”

### 5. Verification gates

The generated template must run the same checks it gives to consumers. Your Python tooling standard already defines a single non-mutating verification gate and states code is not complete until that gate passes. Your frontmatter standard also already has machine validation through `validate-frontmatter`, with distinct exit codes for validation versus config/schema errors.

### 6. No hand edits to generated artifacts

Manual edits should happen in:

```
project-standards/scaffolds/
project-standards/standards/
project-standards/tools/render_template/
```

Not in:

```
project-template/
```

* * *

## Versioning policy

Use this rule:

| Change type | Template action |
| --- | --- |
| Patch standard fix | Auto-update template and auto-merge after checks |
| Minor additive standard change | Auto-update template and auto-merge after checks |
| Major/breaking standard change | Auto-update template branch and PR; auto-merge only if template migration checks pass |
| Security or broken-template fix | Auto-update immediately; allow direct merge after checks |

Your standards already distinguish schema/contract versions from repository release tags: the frontmatter standard says `schema_version` is the metadata schema version, while the repository release tag versions the standard, schema, validator CLI, and reusable workflow together. Keep that distinction in the template lockfile.

For Python tooling specifically, your standard already treats raising the Python baseline as a major-level change for copy-adopting consumers. That is exactly the kind of thing the template sync should label clearly.

* * *

## GitHub permissions note

If you rely on a workflow inside the **template repo** using `GITHUB_TOKEN` to create PRs, GitHub has a repository/org setting controlling whether workflows may create or approve pull requests; new personal repositories default to not allowing it, while org repos inherit the org setting. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)

To avoid that fragility, use a GitHub App installed on both repos and give it only the permissions it needs. For writing workflow files under `.github/workflows`, GitHub’s GitHub App permission docs say the app needs `Workflows` permission in addition to `Contents`. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)

* * *

## What I would build first

Start with the simplest durable system:

```
project-standards
  tools/render_template/
  template-manifest.yml
  .github/workflows/release-sync-template.yml

project-template
  .project-standards.lock.yml
  .github/workflows/check-generated.yml
```

Initial release workflow:

```
on release published:
  checkout project-standards at release tag
  render template to /tmp/rendered-template
  run template checks in /tmp/rendered-template
  clone project-template using GitHub App token
  replace managed paths
  update .project-standards.lock.yml
  commit branch standards-sync/<version>
  open PR
  enable auto-merge after checks
```

That gives you automatic updates, an audit trail, and a hard drift detector without depending on agents to remember the standard. Later, add Copier only if you want this same update machinery to maintain existing downstream repos, not just the official template repo.

* * *

**You:**

i very frequently observe agents using the handoff system requiring multiple attempts to reduce the size of the documents that have explicit caps in size. It seems like they’re randomly guessing that their efforts to reduce size will bring it under the limit and then they test after the fact and realize it’s not and have to go back and try fixing it again. This seems inefficient and a waste of time and a waste of tokens.  What sort of options do I have that I could bake into this standard which would help the agents use it more effectively and efficiently

* * *

**ChatGPT:**

The failure mode is quantitative, so the standard should stop treating it as a writing-quality problem. The strongest fixes are budget-first authoring, machine validation before handoff, and smaller typed artifacts instead of one prose blob.

## Bottom line

Bake in a **budgeted handoff contract** plus a **machine validator**. Agents are failing because they are doing qualitative editing against a quantitative constraint. The standard should require them to measure first, allocate budget, write to budget, then validate. Do not let “make it shorter” be the control mechanism.

This fits your existing standards direction: you already treat agent workflows as something that should have a verification gate and should not be considered complete until checks pass. The same idea should apply to handoff size.

* * *

## 1. Add a handoff size validator

Create a repo tool such as:

```Bash
uv run handoff-check
uv run handoff-check --fix
uv run handoff-check --report
```

It should validate:

| Rule | Example |
| --- | --- |
| File hard cap | `handoff/current.md <= 8_000 chars` |
| Section caps | `Current State <= 1_500 chars` |
| Total handoff set cap | `handoff/*.md <= 20_000 chars` |
| Required sections present | `Objective`, `State`, `Next Action`, `Blockers`, `Commands Run` |
| Forbidden bloat | no pasted logs, no chat transcript, no duplicated command output |
| Links instead of copies | large details moved to `handoff/archive/` or repo docs |

The output needs to be actionable, not just “too long”:

```
handoff/current.md: FAIL
limit: 8000 chars
actual: 10426 chars
over: 2426 chars

largest sections:
- Context: 4210 chars, limit 1800, over 2410
- Completed Work: 2310 chars, limit 1500, over 810

recommended compression profile:
- Replace narrative history with 5 bullets.
- Move completed implementation detail to handoff/archive/2026-07-07-details.md.
- Keep only current blocker and next action in active handoff.
```

This is the single highest-leverage fix.

* * *

## 2. Require budget-first authoring

Add a rule like this to the standard:

```
Agents MUST NOT revise capped handoff documents by guessing whether the result will fit.

Before writing or shrinking a capped handoff document, the agent MUST:
1. Read the configured cap.
2. Measure current size.
3. Calculate required reduction.
4. Allocate a target budget per section with at least 10% safety margin.
5. Rewrite to that budget.
6. Run the handoff validator before reporting completion.
```

Example:

```
Cap: 8,000 chars
Safety target: 7,200 chars
Current size: 11,400 chars
Required reduction: 4,200 chars minimum
Practical reduction target: 4,800 chars

Budget:
- Objective: 500
- Current state: 1,500
- Changed files: 1,200
- Verification: 1,000
- Blockers: 700
- Next action: 1,000
- Metadata: 300
- Reserve: 1,000
```

This changes the agent’s job from “try shorter” to “fit this allocation.”

* * *

## 3. Use hard section budgets, not only document budgets

A single total cap still lets one section consume the whole file. Give each section a quota.

```YAML
handoff:
  current_file: 'handoff/current.md'
  hard_cap_chars: 8000
  target_cap_chars: 7200
  sections:
    objective:
      required: true
      max_chars: 500
    current_state:
      required: true
      max_chars: 1500
    changed_files:
      required: true
      max_chars: 1200
    verification:
      required: true
      max_chars: 1000
    blockers:
      required: true
      max_chars: 700
    next_action:
      required: true
      max_chars: 1000
    details_pointer:
      required: false
      max_chars: 500
```

This prevents the common agent failure mode where it preserves the wrong thing: a rich narrative history, while squeezing out the actual next action.

* * *

## 4. Split handoff into tiers

Do not force one document to serve every use case.

Recommended structure:

```
handoff/
  current.md              # hard-capped, active working state
  index.md                # tiny pointer file
  archive/
    2026-07-07-detail.md  # uncapped or larger cap
    2026-07-07-log.md     # command output / detailed history
```

The active handoff should be a **resume point**, not a memoir.

| File | Cap | Purpose |
| --- | --- | --- |
| `handoff/index.md` | 1–2 KB | where to start |
| `handoff/current.md` | 6–10 KB | current agent resume state |
| `handoff/archive/*.md` | larger | durable history and detail |
| `docs/decisions/*.md` | normal docs cap | decisions worth preserving |
| issue / PR comments | external context | discussion, review, traceability |

Your Python coding standard already recommends compact agent summaries for routine work while keeping full rationale discoverable elsewhere. Apply the same pattern to handoff: compact active context, linked durable detail.

* * *

## 5. Define content priority rules

Agents need to know what to delete first. Add a deterministic retention order.

### Keep, in order

1. Current objective.
2. Current repo state.
3. Exact next action.
4. Blockers / risks / failing checks.
5. Files changed and why.
6. Commands run and results.
7. Decisions made.
8. Pointers to supporting detail.

### Drop or move first

1. Polite narrative.
2. Chronological chat history.
3. Repeated rationale.
4. Full command output.
5. Long logs.
6. Code snippets already present in files.
7. Speculative next steps.
8. Completed micro-steps that no longer affect the next agent.

This is important because LLMs often compress the wrong material. They preserve fluent story and delete operational state.

* * *

## 6. Make compression deterministic

Give agents a required over-cap reduction ladder.

Example:

```
If handoff/current.md exceeds its cap, apply these reductions in order:

1. Delete duplicated information already present in repo files.
2. Replace narrative paragraphs with bullets.
3. Replace completed-work detail with file/path references.
4. Move command output to archive and keep only command + pass/fail result.
5. Collapse changed-file explanations to one line per file.
6. Collapse decisions to "Decision / reason / date" triples.
7. Remove historical sequence unless it affects the next action.
8. If still over cap, create an archive detail file and link it from current.md.
```

This avoids iterative “try again” behavior because the agent has a known sequence of transformations.

* * *

## 7. Add a size report command agents must run before editing

Useful commands:

```Bash
uv run handoff-size
uv run handoff-size --by-section
uv run handoff-size --json
```

Example JSON:

```JSON
{
  "file": "handoff/current.md",
  "limit_chars": 8000,
  "target_chars": 7200,
  "actual_chars": 10426,
  "over_chars": 2426,
  "sections": [
    {
      "name": "Current State",
      "limit_chars": 1500,
      "actual_chars": 4210,
      "over_chars": 2710
    }
  ]
}
```

Agents are much better when they can use numbers. Do not make them estimate.

* * *

## 8. Add “must not start by rewriting” rule

This sounds small, but it matters.

```
When reducing a capped document, agents MUST NOT begin by rewriting the whole document.

They MUST first produce or inspect a size report, identify the over-budget sections, and only edit the sections responsible for the overage.
```

Without this, agents repeatedly rewrite everything, often making some sections longer while shortening others.

* * *

## 9. Use a template that is hard to bloat

Bad template shape:

```Markdown
## Background

## Work Completed

## Detailed Notes

## Current State

## Next Steps
```

Better template shape:

```Markdown
# Current Handoff

## Objective
One sentence.

## Current State
- ...

## Next Action
- ...

## Blockers
- None / ...

## Changed Files
- `path`: reason.

## Verification
- `command`: pass/fail/result.

## Detail Pointers
- `path`: what it contains.
```

Constrain each section in comments or generated metadata:

```Markdown
## Current State
<!-- max_chars: 1500; prefer bullets; no chronology unless needed -->
```

The Markdown frontmatter standard already treats `description` as a retrieval hint for agents and caps it at 280 characters as an authoring convention. That same philosophy should be extended from metadata to handoff sections.

* * *

## 10. Consider machine-enforced frontmatter or sidecar metadata

For capped handoff files, add explicit metadata:

```YAML
---
handoff_schema: '1.0'
role: 'current-handoff'
hard_cap_chars: 8000
target_cap_chars: 7200
overflow_policy: 'archive-and-link'
---
```

Or keep it in a sidecar config to avoid mixing it into agent-facing prose:

```YAML
handoffs:
  - path: 'handoff/current.md'
    hard_cap_chars: 8000
    target_cap_chars: 7200
    required_sections:
      - objective
      - current_state
      - next_action
      - blockers
      - changed_files
      - verification
```

I prefer sidecar config for enforcement because the validator can own it. Frontmatter is fine for human readability, but sidecar config is cleaner if the handoff system is a tool rather than just Markdown.

* * *

## 11. Prefer character or byte caps over token caps

Use character or byte caps for repository validation. Token caps are model-dependent and tokenizer-dependent.

Recommended:

```
Primary cap: UTF-8 bytes or Unicode characters.
Optional advisory cap: approximate tokens.
```

For example:

```YAML
hard_cap_chars: 8000
target_cap_chars: 7200
advisory_token_estimate: 2000
```

The validator should enforce the exact cap and optionally report the estimate. Do not make exact correctness depend on tokenizer availability unless you intentionally pin a tokenizer package and model profile.

* * *

## 12. Add golden tests for agent behavior

Your coding standard already suggests golden-task or fixture suites for repeated agent use. Add fixtures like:

```
tests/fixtures/handoff/over_cap_narrative.md
tests/fixtures/handoff/over_cap_logs.md
tests/fixtures/handoff/missing_next_action.md
tests/fixtures/handoff/valid_current.md
```

Test that the tool:

* identifies over-cap sections,
* reports exact overage,
* rejects missing required sections,
* accepts a compact valid handoff,
* catches pasted logs,
* catches duplicate sections.

This is how you turn “agents should be better” into an enforceable standard.

* * *

## 13. Add a required final report format

Agents should not say “reduced the handoff” unless they include numbers.

```
Handoff update report:
- File: handoff/current.md
- Cap: 8,000 chars
- Final size: 7,142 chars
- Margin: 858 chars
- Validator: pass
- Overflow moved to: handoff/archive/2026-07-07-detail.md
```

This mirrors your existing pattern where agents must not claim completion when checks were not run or failed.

* * *

## Recommended standard language

Add something close to this:

```Markdown
## Capped handoff documents

Capped handoff documents are quantitative artifacts. Agents MUST NOT rely on estimated or guessed reductions.

Before editing a capped handoff document, agents MUST run the configured size-report command or otherwise measure the current exact size. The report MUST identify the document cap, current size, overage, and section-level sizes when section markers are present.

Agents MUST write to the target cap, not the hard cap. The default target cap is 90% of the hard cap unless the repository config sets another value.

Agents MUST preserve information in this priority order:

1. current objective
2. current state
3. next atomic action
4. blockers and failing checks
5. changed files and reasons
6. verification commands and results
7. decisions
8. links to supporting detail

Agents SHOULD move overflow detail to an archive or durable project document and link to it from the active handoff. Agents MUST NOT preserve long narrative history, pasted logs, duplicated repo content, or completed micro-step chronology at the expense of current state and next action.

Before reporting completion, agents MUST run the handoff validator. Final reports MUST include the final size, hard cap, remaining margin, and validator result.
```

* * *

## My recommended design choice

Implement **three things**, not a huge system:

1. `handoff-check`: exact validation and section-size reporting.
2. `handoff/current.md`: small, structured, hard-capped resume file.
3. `handoff/archive/`: overflow detail with links from `current.md`.

That gives you the biggest efficiency gain without overbuilding. The important rule is: **no capped handoff update is complete until the validator passes, and no reduction attempt starts without a size report.**