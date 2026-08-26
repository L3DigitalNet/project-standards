# Repository housekeeping sweep

## Purpose

Remove accumulated repository debris and surface the entropy that no single gate owns: dead branches and worktrees, stale caches, drifting dependencies, orphaned files, documentation describing removed behavior, abandoned issues and pull requests, and broken or disabled CI.

This is a sweep, not a gate. It finds work; it does not decide it. Record findings, fix the cheap ones in place, and turn everything else into tracked work rather than leaving it in a session transcript.

## When to run

- On a periodic cadence — monthly is a reasonable default for an active repository.
- After a large merge, a release, or a burst of parallel agent worktrees.
- Before onboarding a new contributor or agent to the repository.

## Preconditions

- A clean working tree, or a deliberate decision to preserve specific in-progress work. Every reaping step below destroys something.
- The default branch is checked out and up to date with its remote.
- You may read `.git`, run the repository's own gates, and query the forge (`gh`, or the equivalent) if issue and pull-request checks are in scope.

## Checklist

### 1. Learn what this repository has adopted (do this first)

- [ ] Read `.standards/config.toml` and list every enabled standards package.
- [ ] For each enabled package, read its adoption guide and agent summary, and note the gates and conventions it already owns.
- [ ] Fold those gates into the sweep by **running them**, not by re-implementing their checks here. A package that already validates formatting, frontmatter, or workflow ownership is the authority for that surface.
- [ ] If `.standards/config.toml` is absent or enables nothing, run the generic checks below and skip the package-activated ones. Nothing in this document requires a standards package to be installed.

### 2. Branches, worktrees, and their caches (generic)

- [ ] List local branches merged into the default branch and delete the ones whose work has landed.
- [ ] List local branches whose upstream is gone (`git fetch --prune`, then `git branch -vv`) and reap them deliberately.
- [ ] List remote branches with no open pull request and no recent commits; delete after confirming with the owner.
- [ ] `git worktree list` — remove worktrees whose branch is merged or abandoned, then `git worktree prune`.
- [ ] **Clean the tool caches keyed to any worktree you just reaped.** Several linters cache results under a user-level directory keyed by absolute path, and a path that is deleted and later reused resurrects the previous run's findings. `golangci-lint cache clean` is the known instance; treat any tool with a user-scoped cache the same way. A "phantom" finding on a file that no longer contains the reported code is this bug, not a real defect.
- [ ] Check for stale `git stash` entries and either apply, branch, or drop them.

### 3. Generated artifacts and caches (generic)

- [ ] Remove build outputs, coverage data, and test scratch that are not gitignored deliberately: `build/`, `dist/`, `*.egg-info/`, `.coverage*`, `htmlcov/`.
- [ ] Remove tool caches inside the repository: `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `node_modules/.cache/`.
- [ ] Confirm every one of those paths is covered by `.gitignore`; a cache directory that is not ignored will eventually be committed.
- [ ] `git status --ignored --short` and skim for anything large or surprising that has quietly accumulated.

### 4. Dependency freshness (activated by toolchain)

Run only the lanes whose lockfile actually exists. A lockfile is the source of truth; never hand-edit a resolved version.

- [ ] Python with uv: `uv lock --check` to prove the lock matches the manifest, then `uv lock --upgrade --dry-run` to see what has moved.
- [ ] Node: `npm outdated`, and confirm `package-lock.json` is in sync with `package.json` (`npm ci` succeeds on a clean checkout).
- [ ] Go: `go list -m -u all` for available upgrades; `go mod tidy` and confirm it produces no diff.
- [ ] Security advisories, where the toolchain offers them: `uv run pip-audit`, `npm audit`, `govulncheck`.
- [ ] Pinned external actions and container images: confirm each pin is still the intended version rather than an abandoned one.

### 5. Orphaned and unreferenced files (generic)

- [ ] Look for documents and scripts that nothing references: grep the tree for each candidate's file name and confirm at least one live pointer exists.
- [ ] Look for the residue of completed work: finished plans, superseded specs, one-off migration scripts, `*.bak`, `*.orig`, `*.rej`, timestamped scratch files.
- [ ] Look for fixtures and test data no test loads any more.
- [ ] Move genuinely historical material to its archive location rather than deleting it, if the repository has one; delete the rest.

### 6. Documentation staleness (generic)

- [ ] Spot-check that commands quoted in `README.md` and the top-level docs still exist and still take the flags shown.
- [ ] Spot-check that paths quoted in documentation still resolve.
- [ ] Search the docs for behavior that has since been removed or renamed — the most common stale claim is a command, option, or file that was replaced but left described.
- [ ] Confirm counts and inventories stated in prose ("eight packages", "three subcommands") still match their source of truth; derive them, do not trust the sentence.
- [ ] Check that per-directory `README` files still describe their directory's current contents.

### 7. Issue and pull-request tidiness (activated by a forge)

- [ ] List open pull requests older than the repository's tolerance. For each: merge, rebase and revive, or close with a reason.
- [ ] List draft pull requests with no activity; a permanent draft is a branch, not a proposal.
- [ ] Review open issues whose premise no longer holds — the bug was fixed incidentally, the file was deleted, the design was superseded. Close them with the evidence, not silently.
- [ ] Confirm issues in a terminal workflow state are actually closed, and that reopened issues are back in a non-terminal state.
- [ ] Where a standards package owns the issue workflow, follow that package's rules for state transitions instead of improvising them here.

### 8. CI health (activated by CI)

- [ ] List the workflows that exist and the ones that actually ran in the last 30 days. A workflow that never runs is either dead or silently broken.
- [ ] Identify disabled workflows and confirm each disablement is still intentional.
- [ ] Identify workflows that have been red for more than a few runs; a permanently red job trains everyone to ignore CI.
- [ ] Confirm required checks named by branch protection still correspond to jobs that exist.
- [ ] Check runner selection is still correct for the repository's ownership and visibility, and that no job depends on tooling the runner image no longer provides.

## Record the outcome

- [ ] Write down what you reaped, what you deferred, and why — in the repository's own handoff or session record if it has one, otherwise in the commit message.
- [ ] Open an issue for every finding you did not fix in this sweep. An unrecorded finding is a finding you will rediscover at full cost.
- [ ] Commit the deletions as their own cohesive change, separate from any fix the sweep prompted.
- [ ] Re-run the repository's gates before finishing: a housekeeping sweep that leaves the build red has made things worse.
