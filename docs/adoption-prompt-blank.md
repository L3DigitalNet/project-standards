# Adopt Latest Project Standards

Complete the selection form below, then give this prompt to the agent. Adopt or update this repository to the most recent official Project Standards release. Work end to end, but preserve the repository's existing intent and stop for user input only when a consequential choice cannot be derived safely.

## Requested installation selection

**Requester:** mark every package or optional tool to install with `[x]` before handing this prompt to an agent. Leave every unwanted entry unchecked. The checked package IDs are the complete requested package set: the agent must enable exactly those packages in `.standards/config.toml` and must not add another package merely because repository evidence suggests it could be useful. Repository evidence still determines each selected package's required options and whether its prerequisites are met.

The agent resolves the package versions from the immutable release selected below; do not write package versions in this checklist unless you deliberately need an exact selector.

### Consumer packages (select zero or more)

- [ ] No consumer packages — create or refresh the Catalog 5 control plane only. Do not combine with another consumer-package selection.
- [ ] `markdown-frontmatter` — validates a portable YAML metadata schema for managed Markdown documents and provides a repository-local frontmatter skill.
- [ ] `adr` — supplies a structured Architecture Decision Record format, templates, and validation for durable technical decisions.
- [ ] `python-tooling` — configures the Python toolchain: uv, Ruff, strict BasedPyright, pytest with coverage, pip-audit, and CI support.
- [ ] `markdown-tooling` — configures Prettier, markdownlint, EditorConfig, and Markdown/structured-text format and lint workflows.
- [ ] `project-spec` — provides Light, Standard, and Full project-specification formats, tooling, and validation workflows.
- [ ] `cli-documentation` — provides CLI usage-reference/man-page scaffolding and checks for drift from the executable interface.
- [ ] `agent-handoff` — establishes repository-local status, task, and handoff knowledge; it can also install a shared SessionStart hook for supported agent harnesses.
- [ ] `github-workflow` — installs the GitHub work-discipline skill and the static `linux/amd64` `gh-workflow` binary for a repository owned by a GitHub organization whose Issue Fields schema it audits against.
- [ ] `project-toolbox` — installs two managed workflow checklists (a repository-housekeeping sweep and a drift-detection sweep) plus a routing skill; it has no options, ships no executable code, and requires no other package.

### Existing V5 repositories (select only when changing its package set)

- [ ] Replace the existing V5 package set with the checked consumer packages above. Without this selection, preserve every existing package and use checked packages only to request additions.

### Optional local integration (not a standards package)

- [ ] `project-standards` MCP server — installs/configures the local, read-only stdio server for the selected active clients. It is not recorded in `.standards/config.toml` and does not replace the CLI, reconciliation, package validation, or CI.
  - [ ] Codex — user-scoped `~/.codex/config.toml` registration.
  - [ ] Claude Code — project-scoped `.mcp.json` registration.

### Reference-only packages (listed for clarity; never select or enable)

- `python-coding` — draft reference guidance for Python code shape, boundaries, typing, tests, and agent behavior; it is not consumer-selectable.
- `standard-bundle-authoring` — internal contract for authoring standards packages; it is not consumer-selectable.

**Agent instruction:** copy the checked consumer-package IDs into the initial `.standards/config.toml` during fresh adoption. For an existing V5 repository, preserve every existing selection unless the requester marks “Replace the existing V5 package set”; otherwise, use checked packages only to request additions. Explain every resulting addition or removal in the preview before applying it. Treat every unchecked consumer package as intentionally out of scope. Configure the MCP server only when its parent checkbox is marked; configure only marked clients. If “No consumer packages” is selected, initialize or inspect the Catalog 5 control plane without enabling a package. If neither a consumer package nor “No consumer packages” is selected, stop and ask the requester to complete the checklist.

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
- Release history for 5.x minor upgrades: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/CHANGELOG.md`
- Versioning and selector policy: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/meta/versioning.md`
- Package catalog and adoption guides: `https://github.com/L3DigitalNet/project-standards/tree/<release-tag>/standards`
- CLI reference: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/docs/usage.md`
- MCP server setup and reference: `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/docs/mcp-server.md`

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
   - a fresh adoption with no Project Standards authority; or
   - an existing V5 repository using `.standards/`, either already on `<release-version>` or behind it on an older 5.x release.

   For an existing V5 repository, record the release it currently sits on before changing anything:

   ```bash
   grep -E '^release = ' .standards/catalog.toml .standards/lock.toml
   ```

   Both files must report the same value; call it `<current-version>` and use it for the rest of the task. If they disagree or either value is missing, treat the control plane as inconsistent and resolve that before upgrading. If `<current-version>` is newer than `<release-version>`, stop and ask the user: a tool older than the repository's recorded release refuses catalog refresh.

5. Inventory the repository's languages, tooling, workflows, current standards configuration, and consumer-owned files. Use the checked consumer-package list as the requested package set; do not add another package from repository evidence alone, and do not enable reference-only or internal packages. Use repository evidence to determine required options and prerequisites for each selected package. Separately detect any pre-package Agent Handoff implementation; if present, complete "Legacy Agent Handoff migration" below in addition to the mode-specific workflow only when `agent-handoff` is selected or already enabled.
6. Use Python 3.14 or newer. Install the exact release and verify it before changing the repository:

   ```bash
   release_tag="<release-tag>"
   release_version="<release-version>"
   uv tool install --force "git+https://github.com/L3DigitalNet/project-standards@${release_tag}"
   project-standards --version >/dev/null 2>&1 || true
   probed="$(project-standards --version)"
   test "$probed" = "project-standards ${release_version}"
   ```

   The first `--version` probe immediately after a forced install can fail transiently while the freshly installed environment finishes import wiring, with no reinstall needed. The first line absorbs that transient failure without capturing anything, so the authoritative probe on the second line compares a single clean value — capturing `cmd || cmd` instead would concatenate a failed first probe's partial output with the second probe's output and fail the comparison for the wrong reason. Replace both placeholders with the values recorded above before running the block. Continue only if the version check succeeds.

7. Work on a branch with a clean baseline whenever possible. Do not discard, overwrite, normalize, commit, push, or open a pull request for unrelated work. Do not use `--force` to bypass ownership or provenance protections.

## Perform the correct workflow

### Fresh adoption

1. Initialize Catalog 5 without enabling packages:

   ```bash
   project-standards init --catalog 5
   ```

2. Enable every checked consumer package at the version specified by its exact-release adoption guide. Configure its closed options from repository intent; do not invent values.
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

### Legacy Agent Handoff migration

A repository may carry a pre-package Agent Handoff implementation — the v3 system — independently of its Project Standards mode, so check for it in both fresh adoptions and 5.x minor upgrades alike. Legacy evidence includes root `STATUS.md` or `TODO.md`, `docs/state.md` or `docs/handoff.md`, `.claude/hooks/session_start.py` or `.codex/hooks/session_start.py`, a repo-local `.agents/skills/handoff-system-v3/` or similarly named retired skill, and SessionStart registrations in harness settings that point at those paths. The package layout instead keeps the status snapshot and work queues at `docs/STATUS.md` and `docs/TODO.md` beside `docs/handoff/**`, injected by the shared managed hook.

When any such evidence exists, migrating it onto the release's Agent Handoff package is part of this task, not a follow-up. Read the packaged runbook for the Agent Handoff version being adopted at `https://github.com/L3DigitalNet/project-standards/blob/<release-tag>/standards/agent-handoff/versions/<major.minor>/resources/legacy-migration.md` and work through it:

1. Inventory before changing files, and treat the output as evidence rather than a migration plan:

   ```bash
   project-standards agent-handoff legacy-report --repo . --json
   ```

   This report is the one Agent Handoff subcommand that answers before the package is selected: it resolves the installed catalog's default payload, discloses that basis on stderr, and writes and locks nothing, so the evidence that adopting is safe arrives before the selection is committed. Review every recognized and unclassified finding, and inspect repository history when two files appear to own the same fact.

2. Route each durable fact to its canonical destination: the current project snapshot to `docs/STATUS.md`, user and agent work queues to `docs/TODO.md`, next-session focus and active incidents to `docs/handoff/state.md`, and the remaining lifetimes to the deployment, architecture, credential, convention, spec-pointer, session, and bug documents the runbook names. Split monolithic legacy documents by fact lifetime instead of copying them wholesale, preserve user-authored tasks and knowledge, keep credential references only and never values, and reconcile conflicting facts before deleting any source.
3. Enable `agent-handoff` in `.standards/config.toml` with one deliberate startup profile and harness list, then preview with `project-standards reconcile --check`. Reconciliation creates the canonical knowledge files only when they are absent and never overwrites consumer content, so route facts first. A blocked preview is expected while duplicate hooks, stale registrations, or unmanaged skill files remain; resolve each conflict locally instead of forcing an unsafe overwrite.
4. Retire the legacy layer only after its useful content exists in the canonical files and the preview is clean. Remove the old SessionStart registrations so exactly one injection path remains, remove the per-harness hook copies once both selected harnesses reference the package's single managed launcher at `.agents/hooks/agent-handoff/session-start`, remove the retired repo-local skill directory after preserving intentional local guidance, and remove the superseded root or direct-`docs/` knowledge files. A migrated repository has no root `STATUS.md` or `TODO.md`; never leave both layouts in one repository. Rerun the legacy report and investigate every remaining blocker or unclassified item.
5. Apply and verify:

   ```bash
   project-standards reconcile --apply
   project-standards agent-handoff validate --repo .
   project-standards agent-handoff drift-check --repo .
   ```

   Document shapes and size budgets are machine-enforced, so a hand-migrated document that reads well may still fail validation; correct the document to the contract rather than relaxing the check. Confirm that startup context is injected exactly once, stays within its byte ceiling, and points only at repository-local knowledge.

6. Do not delete a legacy file whose facts you could not confidently route, and do not guess a transformation for an unclassified item. Preserve it and present the ambiguity to the user.

### Optional Project Standards MCP server adoption

Perform this section only when the `project-standards` MCP server is selected in the installation checklist. It provides a local, read-only stdio convenience layer over the installed Catalog 5 distribution; it does not replace the CLI, reconciliation, package validation, or CI gates. Configure only the client registrations selected in that checklist; do not infer another client from repository files or local availability.

1. Read the exact-release MCP server reference before configuring a client. Confirm that the installed release exposes the subcommand:

   ```bash
   project-standards mcp --help
   ```

   If the resolved release does not provide that command, do not invent a candidate-wheel or development-checkout installation path. Record that the requested release cannot supply the server, report the discrepancy upstream, and stop for user direction only if the user must choose a different release or installation source.

2. Configure every client selected in the checklist. Preserve existing client configuration and unrelated MCP servers. Do not add credentials, remote URLs, HTTP/SSE transport, or a write/apply capability. Use the release-pinned reference for the exact client configuration shape and scope:
   - For Codex, add or preserve the user-scoped `project-standards` stdio entry in `~/.codex/config.toml` (or the task's explicit `CODEX_HOME`):

     ```toml
     [mcp_servers.project-standards]
     command = "project-standards"
     args = ["mcp"]
     ```

   - For Claude Code, add or preserve the project-scoped `project-standards` entry in the consumer repository's `.mcp.json`; merge it with an existing `mcpServers` object rather than replacing that file:

     <!-- prettier-ignore -->
     ```json
     {
       "mcpServers": {
         "project-standards": { "command": "project-standards", "args": ["mcp"] }
       }
     }
     ```

   Add `--root-boundary <absolute-parent-directory>` only when the intended repository roots can be derived safely and a narrower boundary is useful. It can only narrow access; every repository-scoped MCP tool must still receive an explicit absolute `repo_root`.

3. Verify each configured client using the release-pinned commands. For Codex, run `codex mcp list` and `codex mcp get project-standards`; confirm it is enabled and uses stdio with `project-standards` and `mcp`. For Claude Code, run `claude mcp list` and `claude mcp get project-standards` from the consumer repository; confirm the project-scoped server completes a real stdio handshake. Also record the successful `project-standards mcp --help` check. Treat client registration as separate from repository reconciliation and from a full repository gate.

4. Use only the server's declared read-only capabilities. Its repository tools require an explicit absolute root, and `reconcile_preview` is a dry run; do not treat it as authorization to apply a plan. Continue to run the required CLI and CI verification commands independently.

## Report adoption and upgrade irregularities upstream

Open or update an upstream issue for every concrete observation whose resolution could make adoption or updating faster, clearer, safer, or less error-prone. Issue eligibility does not depend on blocking progress, causing a command failure, or lacking a workaround. Examples include contradictory, incomplete, or hard-to-discover documentation; an undocumented prerequisite; unclear package selection, option semantics, command output, or help; unnecessary manual or repeated steps; avoidable retries; surprising diffs; unsafe-looking ownership or removal plans; preservation conflicts; non-idempotent reconciliation; weak diagnostics; validation failures; traceback or internal errors; and steps that require an undocumented workaround.

Use consumer impact and reproducibility to prioritize the report, not to decide whether to report it. A safe workaround or the ability to complete the adoption or update does not waive issue reporting.

Report upstream at <https://github.com/L3DigitalNet/project-standards/issues>. The repository has GitHub Issues enabled.

Do not silently work around, normalize, or hide an irregularity. For each distinct irregularity:

1. Preserve the failing state and capture sanitized evidence before attempting a workaround:
   - adoption mode: fresh or V5 update;
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

- whether this was fresh adoption or a V5 update, and whether a legacy Agent Handoff migration was included;
- for a V5 update, the release the repository moved from and to, or that it was already current, and every resolved package version that advanced;
- for a legacy Agent Handoff migration, the legacy files retired, where their facts now live, and anything preserved for user judgment;
- installed Project Standards version and selected package versions;
- MCP server availability, every client scope configured or preserved, and the MCP launch/client-registration checks run;
- files created, changed, preserved, or intentionally removed;
- preview and apply commands run;
- known upstream issues that shaped the plan, and any workaround adopted because the observed behavior matched one;
- verification commands and exact outcomes;
- every upstream issue URL opened or updated, including reports for friction that did not block progress;
- any workaround, remaining uncertainty, or blocked step; and
- whether the working tree is ready for human review.

Do not commit, push, or open a pull request unless the invoking user separately authorizes those actions.
