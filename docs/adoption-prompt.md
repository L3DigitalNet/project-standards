---
schema_version: '1.1'
id: 'prompt-3nw7vm-project-standards-adoption-update'
title: 'Adopt or update Project Standards with an agent'
description: 'Copy/paste agent prompt for a safe, verified Project Standards adoption, minor-version upgrade, or major migration.'
doc_type: 'prompt'
status: 'active'
created: '2026-07-20'
updated: '2026-07-28'
reviewed: '2026-07-28'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'standard'
aliases: []
related:
  - 'README.md'
  - 'UPGRADING.md'
  - 'CHANGELOG.md'
  - 'docs/usage.md'
  - 'meta/versioning.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Adopt or update Project Standards with an agent

Copy the prompt below into a coding agent session rooted in the repository to adopt Project Standards or update an existing consumer. It covers all three entry points — a fresh adoption, a V5 consumer moving from an older 5.x release to the latest 5.x release, and a V4-to-V5 migration — plus migrating a repository off the pre-package Agent Handoff v3 system. The prompt requires a preview before every apply, preservation of consumer intent, latest-release discovery with immutable-release verification, a review of open upstream issues before planning, and sanitized upstream issue reports for defects, blockers, and friction-reducing improvements.

## Copy/paste prompt

````markdown
Adopt or update this repository to the most recent official Project Standards release. Work end to end, but preserve the repository's existing intent and stop for user input only when a consequential choice cannot be derived safely.

Resolve GitHub's latest published, non-prerelease Project Standards release once, before reading release documentation or changing the repository:

```bash
release_tag="$(gh api repos/L3DigitalNet/project-standards/releases/latest --jq .tag_name)"
release_version="${release_tag#v}"
test -n "$release_tag"
test "$release_version" != "$release_tag"
printf 'Project Standards release: %s (%s)\n' "$release_tag" "$release_version"
```

Record both values and use them unchanged for the rest of the task, even if a newer release appears while work is in progress. In every command and URL below, replace `<release-tag>` and `<release-version>` with those recorded literal values.

Use these resolved, immutable-release sources as authority:

- Consumer setup: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/README.md#consuming-the-standards`
- V4-to-V5 migration: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/UPGRADING.md`
- Release history for 5.x minor upgrades: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/CHANGELOG.md`
- Versioning and selector policy: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/meta/versioning.md`
- Package catalog and adoption guides: `https://github.com/L3DigitalNet/project-standards/tree/<release-tag>/standards`
- CLI reference: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/docs/usage.md`

Treat the documentation at `<release-tag>` and the installed `project-standards <release-version>` behavior as authoritative. Do not follow `main`, mutable family pages from another ref, older release instructions, or remembered commands when they conflict with these sources.

## Safety and orientation

1. Confirm the repository root, active branch, recent commits, remotes, and `git status`. Preserve all unrelated and pre-existing changes.
2. Read the repository's agent instructions and relevant maintainer documentation before editing.
3. Review the upstream tracker before planning the work, so known friction is anticipated instead of rediscovered mid-apply:

   ```bash
   gh issue list --repo L3DigitalNet/project-standards --state open --limit 100
   ```

   Read the open issues that touch adoption, upgrading, migration, reconciliation, the CLI commands this task will run, and the packages this repository will enable; open the relevant ones with `gh issue view <issue-number> --repo L3DigitalNet/project-standards` to capture the reproduction and any documented workaround. Also check recently closed issues, because a fix merged after `<release-tag>` is not present in the release being installed. Plan around each confirmed limitation and note it in the final report; apply a workaround from an issue thread only when the behavior you observe actually matches it, never preemptively. If the tracker is unreachable, report that gap and continue.

4. Determine whether this is:
   - a fresh adoption with no Project Standards authority;
   - an existing V5 repository using `.standards/`, either already on `<release-version>` or behind it on an older 5.x release; or
   - a V4 repository using `.project-standards.yml` and package-specific locks.

   For an existing V5 repository, record the release it currently sits on before changing anything:

   ```bash
   grep -E '^release = ' .standards/catalog.toml .standards/lock.toml
   ```

   Both files must report the same value; call it `<current-version>` and use it for the rest of the task. If they disagree or either value is missing, treat the control plane as inconsistent and resolve that before upgrading. If `<current-version>` is newer than `<release-version>`, stop and ask the user: a tool older than the repository's recorded release refuses catalog refresh.

5. Inventory the repository's languages, tooling, workflows, current standards configuration, and consumer-owned files. Select only packages supported by repository evidence or explicit user intent. Do not enable reference-only or internal packages. Separately detect any pre-package Agent Handoff implementation; if present, complete "Legacy Agent Handoff migration" below in addition to the mode-specific workflow.
6. Use Python 3.14 or newer. Install the exact release and verify it before changing the repository:

   ```bash
   release_tag="<release-tag>"
   release_version="<release-version>"
   uv tool install --force "git+https://github.com/L3DigitalNet/project-standards@${release_tag}"
   test "$(project-standards --version)" = "project-standards ${release_version}"
   ```

   Replace both placeholders with the values recorded above before running the block. Continue only if the version check succeeds.

7. Work on a branch with a clean baseline whenever possible. Do not discard, overwrite, normalize, commit, push, or open a pull request for unrelated work. Do not use `--force` to bypass ownership or provenance protections.

## Perform the correct workflow

### Fresh adoption

1. Initialize Catalog 5 without enabling packages:

   ```bash
   project-standards init --catalog 5
   ```

2. Enable each evidence-backed consumer package at the version specified by its exact-release adoption guide. Configure its closed options from repository intent; do not invent values.
3. Read every selected package's `versions/<major.minor>/adopt.md` from `<release-tag>`.
4. Run `project-standards reconcile` first as a read-only preview. Review every planned write, removal, ownership claim, finding, and verification action.
5. Resolve all unexpected or ambiguous preview findings before running `project-standards reconcile --apply`.

### Existing V5 update, including a 5.x minor upgrade

Moving from an older 5.x release to `<release-version>` is an in-place, non-breaking upgrade within the same Catalog 5: the newly installed tool carries a newer snapshot of that catalog, and `reconcile` refreshes the control plane to it. It is not a re-adoption, and nothing about it licenses rewriting the repository's existing intent.

1. Preserve `.standards/config.toml`, exact selectors, accepted major tracks, package options, extensions, consumer-owned content, and unrelated files.
2. Read every changelog section released after `<current-version>` up to and including `<release-version>`. Note added, changed, fixed, and deprecated behavior for the enabled packages, plus any entry that calls for consumer action. Carry that list into the preview review so an expected diff is recognizable and an unexpected one is not waved through.
3. If `<current-version>` already equals `<release-version>`, there is no release delta. Still run the steps below to confirm the control plane reconciles cleanly, and report the repository as already current instead of manufacturing changes.
4. Run `project-standards standards list` and inspect each enabled package with `project-standards standards show <standard>`.
5. Compare each selection with the Catalog 5 packages and exact-release adoption guide. `latest` advances only within its compatible default or accepted-major track, so a minor upgrade may legitimately move those resolved package versions; an exact selector remains pinned unless this task explicitly requires changing it. Use `project-standards standards version <standard> <latest|major.minor>` only when the intended selector change is clear, and read the target version's `versions/<major.minor>/adopt.md` at `<release-tag>` before changing a selector.
6. Run `project-standards reconcile` and review the complete catalog/package refresh, including the recorded release moving from `<current-version>` to `<release-version>` and every resolved package version that advances, before applying it with `project-standards reconcile --apply`.
7. Never silently cross a package-major boundary or rewrite a closed package option to make reconciliation pass. A refreshed catalog may advertise opt-in breaking package candidates; entering one requires reading its migration path and an explicit `project-standards reconcile --allow-major <standard>@<major>` authorization, which is outside a routine minor upgrade unless the user asks for it.
8. Review consumer-owned references to the standards release that reconciliation does not own: reusable workflow `uses:` refs, `standards-ref` inputs, `uv tool install` and `uvx` invocations, and documentation examples. A `@v5` major pin already tracks this release and must not be narrowed on its own; update an exact `@v<release-version>`-style pin only where the repository deliberately freezes the release, and update every such reference in the same change.

### V4-to-V5 migration

1. Follow `UPGRADING.md` exactly. Do not run plain `init` and do not create `.standards/` beside legacy authority manually.
2. Preserve `.project-standards.yml`, recognized package locks, and managed artifacts until migration apply succeeds.
3. Produce both previews against identical repository bytes:

   ```bash
   project-standards init --catalog 5 --migrate
   project-standards init --catalog 5 --migrate --json >migration-plan.json
   ```

4. Review and resolve every ambiguity, unknown artifact, modified managed file, ownership conflict, unsafe path, and missing intent. Rerun both previews after any correction.
5. Apply only the accepted plan:

   ```bash
   project-standards init --catalog 5 --migrate --apply
   ```

### Legacy Agent Handoff migration

A repository may carry a pre-package Agent Handoff implementation — the v3 system — independently of its Project Standards mode, so check for it in a fresh adoption, a 5.x minor upgrade, and a V4 migration alike. Legacy evidence includes root `STATUS.md` or `TODO.md`, `docs/state.md` or `docs/handoff.md`, `.claude/hooks/session_start.py` or `.codex/hooks/session_start.py`, a repo-local `.agents/skills/handoff-system-v3/` or similarly named retired skill, and SessionStart registrations in harness settings that point at those paths. The package layout instead keeps the status snapshot and work queues at `docs/STATUS.md` and `docs/TODO.md` beside `docs/handoff/**`, injected by the shared managed hook.

When any such evidence exists, migrating it onto the release's Agent Handoff package is part of this task, not a follow-up. Read the packaged runbook for the Agent Handoff version being adopted at `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/standards/agent-handoff/versions/<major.minor>/resources/legacy-migration.md` and work through it:

1. Inventory before changing files, and treat the output as evidence rather than a migration plan:

   ```bash
   project-standards agent-handoff legacy-report --repo . --json
   ```

   Review every recognized and unclassified finding, and inspect repository history when two files appear to own the same fact.

2. Route each durable fact to its canonical destination: the current project snapshot to `docs/STATUS.md`, user and agent work queues to `docs/TODO.md`, next-session focus and active incidents to `docs/handoff/state.md`, and the remaining lifetimes to the deployment, architecture, credential, convention, spec-pointer, session, and bug documents the runbook names. Split monolithic legacy documents by fact lifetime instead of copying them wholesale, preserve user-authored tasks and knowledge, keep credential references only and never values, and reconcile conflicting facts before deleting any source.
3. Enable `agent-handoff` in `.standards/config.toml` with one deliberate startup profile and harness list, then preview with `project-standards reconcile --check`. Reconciliation creates the canonical knowledge files only when they are absent and never overwrites consumer content, so route facts first. A blocked preview is expected while duplicate hooks, stale registrations, or unmanaged skill files remain; resolve each conflict locally instead of forcing an unsafe overwrite.
4. Retire the legacy layer only after its useful content exists in the canonical files and the preview is clean. Remove the old SessionStart registrations so exactly one injection path remains, remove the per-harness hook copies once both selected harnesses reference `.agents/hooks/agent-handoff/session_start.py`, remove the retired repo-local skill directory after preserving intentional local guidance, and remove the superseded root or direct-`docs/` knowledge files. A migrated repository has no root `STATUS.md` or `TODO.md`; never leave both layouts in one repository. Rerun the legacy report and investigate every remaining blocker or unclassified item.
5. Apply and verify:

   ```bash
   project-standards reconcile --apply
   project-standards agent-handoff validate --repo .
   project-standards agent-handoff drift-check --repo .
   ```

   Document shapes and size budgets are machine-enforced, so a hand-migrated document that reads well may still fail validation; correct the document to the contract rather than relaxing the check. Confirm that startup context is injected exactly once, stays within its byte ceiling, and points only at repository-local knowledge.

6. Do not delete a legacy file whose facts you could not confidently route, and do not guess a transformation for an unclassified item. Preserve it and present the ambiguity to the user.

## Report adoption and upgrade irregularities upstream

Open or update an upstream issue for every concrete observation whose resolution could make adoption or updating faster, clearer, safer, or less error-prone. Issue eligibility does not depend on blocking progress, causing a command failure, or lacking a workaround. Examples include contradictory, incomplete, or hard-to-discover documentation; an undocumented prerequisite; unclear package selection, option semantics, command output, or help; unnecessary manual or repeated steps; avoidable retries; surprising diffs; unsafe-looking ownership or removal plans; preservation conflicts; non-idempotent reconciliation; weak diagnostics; validation failures; traceback or internal errors; and steps that require an undocumented workaround.

Use consumer impact and reproducibility to prioritize the report, not to decide whether to report it. A safe workaround or the ability to complete the adoption or update does not waive issue reporting.

Report upstream at https://github.com/L3DigitalNet/project-standards/issues. The repository has GitHub Issues enabled.

Do not silently work around, normalize, or hide an irregularity. For each distinct irregularity:

1. Preserve the failing state and capture sanitized evidence before attempting a workaround:
   - adoption mode: fresh, V5 update, or V4 migration;
   - Project Standards version and exact source ref;
   - selected package ids, selectors, and relevant non-secret options;
   - operating system, Python version, agent/harness, and installation method;
   - exact command and exit code;
   - expected behavior and actual behavior;
   - complete relevant output or traceback;
   - minimal reproduction steps;
   - relevant `git status`, focused diff, and documentation links;
   - consumer consequence, including extra time, steps, confusion, or risk; and
   - whether the irregularity blocks progress or has a safe temporary workaround.
2. Remove secrets, credentials, private repository names or URLs, proprietary source, personal data, and unrelated consumer content from all evidence.
3. Search the upstream issue tracker before filing:

   ```bash
   gh issue list --repo L3DigitalNet/project-standards --state all --search "<concise symptoms or command>"
   ```

4. If an exact issue already exists, add the new reproducible evidence there instead of creating a duplicate:

   ```bash
   gh issue comment <issue-number> --repo L3DigitalNet/project-standards \
     --body-file <sanitized-issue-body.md>
   ```

   Otherwise, open one issue per distinct irregularity:

   ```bash
   gh issue create --repo L3DigitalNet/project-standards \
     --title "[adoption] <concise irregularity>" \
     --body-file <sanitized-issue-body.md>
   ```

   Use `[upgrade]` instead of `[adoption]` for an existing-consumer update or migration. Include the captured evidence, consumer consequence, and any safe workaround. Cross-link related issues rather than combining unrelated failures.

5. Opening or updating these upstream issues, including reports for non-blocking friction, is explicitly part of this task. If GitHub authentication, network access, or issue permissions prevent it, prepare the complete sanitized issue title and body, report the single missing prerequisite, and do not claim the reporting step complete unless the user explicitly waives it.
6. After reporting, continue only if the next action is safe, documented, preserves consumer intent, and will not destroy useful failure evidence. Otherwise stop and present the issue URL and blocker to the user.

## Verify the result

Run the repository's own checks and every verification command required by the selected package adoption guides. At minimum, inspect the generic control-plane plan and run the diff checks:

```bash
project-standards standards list
project-standards reconcile --check --json
git status --short
git diff --check
```

For an existing V5 update, confirm the release actually moved:

```bash
grep -E '^release = ' .standards/catalog.toml .standards/lock.toml
```

Both files must now report `<release-version>`. If either still reports `<current-version>` after an applied reconciliation, the upgrade did not take effect; investigate the cause instead of editing the control-plane files by hand.

Run a second reconciliation and confirm it contains no findings or pending managed mutations. Customized consumer-owned or create-only files may produce intentional `preserve` actions and make `--check` report drift; verify that JSON still reports `ok: true` and that every non-`no-op` action is an understood preservation. Run package-specific checks such as `project-standards validate` when Markdown Frontmatter is enabled, strict specification lint, Markdown formatting/linting, Python verification, and Agent Handoff validation/drift checks when those packages are enabled. If any check cannot run, state exactly why and do not describe the adoption or update as fully verified.

Review the complete diff. Confirm that `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, and reconciled outputs agree; consumer-owned knowledge and unrelated files remain preserved; workflow and tool pins use the intended release line; and no temporary migration evidence is accidentally included.

## Final report

Report:

- whether this was fresh adoption, a V5 update, or a V4 migration, and whether a legacy Agent Handoff migration was included;
- for a V5 update, the release the repository moved from and to, or that it was already current, and every resolved package version that advanced;
- for a legacy Agent Handoff migration, the legacy files retired, where their facts now live, and anything preserved for user judgment;
- installed Project Standards version and selected package versions;
- files created, changed, preserved, or intentionally removed;
- preview and apply commands run;
- known upstream issues that shaped the plan, and any workaround adopted because the observed behavior matched one;
- verification commands and exact outcomes;
- every upstream issue URL opened or updated, including reports for friction that did not block progress;
- any workaround, remaining uncertainty, or blocked step; and
- whether the working tree is ready for human review.

Do not commit, push, or open a pull request unless the invoking user separately authorizes those actions.
````
