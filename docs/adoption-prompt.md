---
schema_version: '1.1'
id: 'prompt-3nw7vm-project-standards-adoption-update'
title: 'Adopt or update Project Standards with an agent'
description: 'Copy/paste agent prompt for a safe, verified Project Standards adoption or update.'
doc_type: 'prompt'
status: 'active'
created: '2026-07-20'
updated: '2026-07-21'
reviewed: '2026-07-21'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'standard'
aliases: []
related:
  - 'README.md'
  - 'UPGRADING.md'
  - 'docs/usage.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Adopt or update Project Standards with an agent

Copy the prompt below into a coding agent session rooted in the repository to adopt Project Standards or update an existing consumer. The prompt requires a preview before every apply, preservation of consumer intent, latest-release discovery with immutable-release verification, and sanitized upstream issue reports for defects, blockers, and friction-reducing improvements.

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
- Package catalog and adoption guides: `https://github.com/L3DigitalNet/project-standards/tree/<release-tag>/standards`
- CLI reference: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/docs/usage.md`

Treat the documentation at `<release-tag>` and the installed `project-standards <release-version>` behavior as authoritative. Do not follow `main`, mutable family pages from another ref, older release instructions, or remembered commands when they conflict with these sources.

## Safety and orientation

1. Confirm the repository root, active branch, recent commits, remotes, and `git status`. Preserve all unrelated and pre-existing changes.
2. Read the repository's agent instructions and relevant maintainer documentation before editing.
3. Determine whether this is:
   - a fresh adoption with no Project Standards authority;
   - an existing V5 repository using `.standards/`; or
   - a V4 repository using `.project-standards.yml` and package-specific locks.
4. Inventory the repository's languages, tooling, workflows, current standards configuration, and consumer-owned files. Select only packages supported by repository evidence or explicit user intent. Do not enable reference-only or internal packages.
5. Use Python 3.14 or newer. Install the exact release and verify it before changing the repository:

   ```bash
   release_tag="<release-tag>"
   release_version="<release-version>"
   uv tool install --force "git+https://github.com/L3DigitalNet/project-standards@${release_tag}"
   test "$(project-standards --version)" = "project-standards ${release_version}"
   ```

   Replace both placeholders with the values recorded above before running the block. Continue only if the version check succeeds.

6. Work on a branch with a clean baseline whenever possible. Do not discard, overwrite, normalize, commit, push, or open a pull request for unrelated work. Do not use `--force` to bypass ownership or provenance protections.

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

### Existing V5 update

1. Preserve `.standards/config.toml`, exact selectors, accepted major tracks, package options, extensions, consumer-owned content, and unrelated files.
2. Run `project-standards standards list` and inspect each enabled package with `project-standards standards show <standard>`.
3. Compare each selection with the Catalog 5 packages and exact-release adoption guide. `latest` may follow its compatible release channel; an exact selector remains pinned unless this task explicitly requires changing it. Use `project-standards standards version <standard> <latest|major.minor>` only when the intended selector change is clear.
4. Run `project-standards reconcile` and review the complete catalog/package refresh before applying it with `project-standards reconcile --apply`.
5. Never silently cross a package-major boundary or rewrite a closed package option to make reconciliation pass.

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

Run a second reconciliation and confirm it contains no findings or pending managed mutations. Customized consumer-owned or create-only files may produce intentional `preserve` actions and make `--check` report drift; verify that JSON still reports `ok: true` and that every non-`no-op` action is an understood preservation. Run package-specific checks such as `project-standards validate` when Markdown Frontmatter is enabled, strict specification lint, Markdown formatting/linting, Python verification, and Agent Handoff validation/drift checks when those packages are enabled. If any check cannot run, state exactly why and do not describe the adoption or update as fully verified.

Review the complete diff. Confirm that `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, and reconciled outputs agree; consumer-owned knowledge and unrelated files remain preserved; workflow and tool pins use the intended release line; and no temporary migration evidence is accidentally included.

## Final report

Report:

- whether this was fresh adoption, a V5 update, or a V4 migration;
- installed Project Standards version and selected package versions;
- files created, changed, preserved, or intentionally removed;
- preview and apply commands run;
- verification commands and exact outcomes;
- every upstream issue URL opened or updated, including reports for friction that did not block progress;
- any workaround, remaining uncertainty, or blocked step; and
- whether the working tree is ready for human review.

Do not commit, push, or open a pull request unless the invoking user separately authorizes those actions.
````
