---
schema_version: '1.1'
id: 'reference-jr5c82-release-runbook'
title: 'Release Runbook'
description: 'Durable procedure for cutting a project-standards release: every step, its command, its exit evidence, its rollback, and which gate layer owns each proof.'
doc_type: 'reference'
status: 'active'
created: '2026-09-01'
updated: '2026-09-01'
reviewed: '2026-09-01'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'release'
  - 'reference'
  - 'ci'
aliases: []
related:
  - 'docs/research/2026-09-01-release-train-wall-clock.md'
  - 'meta/versioning.md'
  - 'CHANGELOG.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Release Runbook

This is the durable procedure for cutting a `project-standards` release from this checkout. It generalizes the per-train session log to the repeatable steps: what each layer proves, the exact command, the observable that proves it worked, and the rollback if it didn't. [`meta/versioning.md` §"Release requirements"](../../meta/versioning.md) is the normative checklist this runbook operationalizes; where they conflict, `meta/versioning.md` wins and this document is stale.

Throughout, `$RELEASE` is the target version (`X.Y.Z`), `$TAG` is `v$RELEASE`, and `$PREV` is the previous full-version tag (the `packages check-release` baseline). Heavy commands route through `rexec -- …` per `CLAUDE.md` "Heavy Workloads"; anything that mutates authoritative Git state — the release commit, tags, pushes — runs locally, never through `rexec`.

## Install path (context for this runbook)

The Git tag is the only supported install path for a release; GitHub release assets published at R10 below are convenience copies for browsing, not a supported install source. That is why R10's byte-verification and R11's reproducibility rebuild are **periodic** checks rather than a per-release gate — see the Layer ownership table.

## Layer ownership

Every proof this runbook relies on belongs to exactly one layer. A leg never re-runs what an integrated gate will re-run over the final tree, and the integrated gate never re-runs what only publication or a periodic check can prove.

| Layer | Scope | Owns |
| --- | --- | --- |
| L0 — leg | A single in-flight change, before it lands | Only the checks its own diff can affect; never a full battery |
| L1 — integrated gate | The final tree, before the release commit | The five standards validators (`validate`, `validate-packages`, `validate-graph`, `render-catalog --check`, `sync-payload-projection --check`), `ruff format --check` / `ruff check` / `basedpyright`, markdownlint / prettier, `make go-check` (including `go-verify-binary`), the `package_contract` pytest suite, the ordinary pytest lane, the compatibility lane, the performance lane, coverage, and the `issue_regressions` ledger tests |
| L2 — release prep delta re-check | `scripts/release_prep.py`, before and after the version bump | `packages check-release --staged` (run before the bump, classifying the pre-bump findings as expected) and the unstaged `check-release` re-run after; the golden fixture re-render (`make release-golden RELEASE=$RELEASE`) |
| L3 — hosted Check | GitHub Actions on `main`, after push | The hosted `Check` workflow run |
| L4 — publication | Tag creation and push | Tag signature verification (`git tag -v`) and the `--verify-tag`/`isLatest`/`isDraft` assertions at release creation |
| periodic (not per-release) | Scheduled or opportunistic, decoupled from the train | Downloaded-asset byte-verification against the local build; the artifact reproducibility rebuild (`git worktree add` at the tag, rebuild, compare digests) |

A proof that reappears in two layers is a defect in this table, not thoroughness — fix the table instead of adding the extra run.

## Step index

| Step | What | Layer | Irreversible? |
| --- | --- | --- | --- |
| R0 | Read-only pre-flight; record the rollback anchor | — | no |
| R1 | Push `testing`; fast-forward `main` from `testing` | — | no (local `main` re-pointable) |
| R2 | `release_prep.py $RELEASE` (bump/relock/changelog), then `--apply-pins` (dry run, then applied) | L2 | no |
| R3 | Hand pin bumps the allow-list deliberately excludes (judgment sites only) | — | no |
| R4 | `make release-reconcile` (dogfooded control-plane reconcile + validate) | L1 (validators) | no |
| R5 | `make release-golden RELEASE=$RELEASE` | L2 | no |
| R6a | Rebuild the candidate wheel/sdist locally; record artifact digests | — | no |
| R6b | Worker environment parity (`rexec --shell 'uv sync --all-groups --locked'`) | — | no |
| R6c | Fast gate set: `check-release --staged`, validators, markdown, `make go-check`, targeted pytest | L2 / L1 | no |
| R7 | The release commit, on `main` | — | no (reset available) |
| R6d | `scripts/verify.sh --full` on the release commit, detached | L1 | no |
| R8 | Sign `$TAG`; repoint `v$MAJOR`; verify both signatures | L4 | no (local tags deletable) |
| R9 | Push `main` + tags — **point of no return** | — | **YES** |
| R10 | `gh release create --verify-tag --latest` | L4 | partially |
| R11 | Periodic: Go binary reproducibility decision | periodic | no |
| R12 | `testing` fast-forward from `main`; hosted Check; issue closeout; handoff closeout | L3 (R12b only) | no |

Deliberate ordering: **R7 (commit) precedes R6d (the full battery).** The hygiene lane inside `scripts/verify.sh --full` reads `git ls-files` — the Git index — so a battery run before the commit validates a different input than CI will see. Working-tree-only lanes (R6c) are honest earlier, which is why the cheap set still runs before the commit.

## Pin-site discovery

Rerun this before R0 and again after R3 to confirm nothing was missed or over-matched:

```bash
git grep -n '<PREV-without-v>' -- .
```

Classify every hit as one of: **bump** (an R3 edit), **generated-by-reconcile** (never hand-edited; R4 fixes it), or **leave** (deliberate released history — a permalink, a changelog heading, a fixture that pins the release that first shipped something). A hit that is none of these is a new pin site; add it to the classification before continuing.

## R0 — pre-flight snapshot (read-only)

```bash
git status --short                                  # must be empty
git rev-parse origin/main testing origin/testing
git tag --list 'v$MAJOR*'
ls -l .git/hooks/pre-commit .git/hooks/commit-msg
uv run project-standards --version
```

OBSERVABLE: working tree clean; `testing` is a descendant of `origin/main` (`git merge-base --is-ancestor origin/main testing` exits 0); `$TAG` absent from `git tag --list`; both githooks present. Record `PRE_RELEASE_MAIN` (`git rev-parse origin/main`) as the rollback anchor before anything else runs.

ROLLBACK: none needed; nothing mutated.

## R1 — land `testing`, fast-forward `main`

```bash
git push origin testing
git checkout main
git merge --ff-only testing
```

OBSERVABLE: `main` and `testing` at the same OID; the merge printed "Fast-forward" (a merge commit here means `main` had commits `testing` lacked — stop and investigate).

ROLLBACK: `git checkout testing && git branch -f main <PRE_RELEASE_MAIN>` (nothing was pushed to `main`).

## R2 — `release_prep.py`

`--apply-pins` is a separate mode, not an extra step of the default run (`scripts/release_prep.py`'s own module docstring): it rewrites only the allow-listed pin sites and exits. The default run — the version bump, relock, and CHANGELOG conversion — must land and be reviewed first; only then do the pin rewrites make sense against the bumped tree.

```bash
uv run python scripts/release_prep.py $RELEASE --dry-run           # read it; nothing is written
uv run python scripts/release_prep.py $RELEASE
uv run python scripts/release_prep.py $RELEASE --apply-pins --dry-run   # read it; nothing is written
uv run python scripts/release_prep.py $RELEASE --apply-pins
```

OBSERVABLE: after the default run, `pyproject.toml` is at `$RELEASE`; `uv.lock` is relocked; `CHANGELOG.md` carries a new `## [$RELEASE] — <date>` section moved from `## [Unreleased]`. The script's own summary states the `check-release` baseline it used. A FAILED step naming anything other than the catalog projection or release classification (both fixed downstream, by R4 and R3 respectively) is real; stop. After `--apply-pins`, `git diff --stat` touches only the allow-listed pin sites (`scripts/release_prep.py`'s `_RELEASE_PIN_SITES` plus `meta/versioning.md`).

ROLLBACK: `git checkout -- pyproject.toml uv.lock CHANGELOG.md README.md UPGRADING.md docs/mcp-server.md tests/package_contract/test_current_catalog_activation.py meta/versioning.md`.

## R3 — hand pin bumps

R2's `--apply-pins` already rewrote every allow-listed site (`scripts/release_prep.py`'s `_RELEASE_PIN_SITES`: README.md's install-tag/wheel-artifact/version-report/product-prose/precommit-rev, UPGRADING.md's install-tag/version-report/upgrade-target, docs/mcp-server.md's install-tag/wheel-artifact/version-report, and tests/package_contract/test_current_catalog_activation.py's release-constant — plus `_PACKAGE_PIN_PATH`, `meta/versioning.md`'s package-contract-prose pin). This step is only the judgment sites the allow-list deliberately excludes: run the pin-site discovery grep and classify each remaining hit against R2's diff. **bump** sites still needing a hand edit are typically `ROADMAP.md`, UPGRADING.md's history section headings (never its allow-listed pin, which R2 already moved), and `_BASELINE_REF`; **leave** sites are deliberate released history (a permalink, a changelog heading, a fixture pinning the release that first shipped something) and stay untouched, including the activation-constant baseline reference (it moves in the payload-cut commit that stages a new activation, not in the release commit).

OBSERVABLE: `git grep -n '<PREV-without-v>' -- .` returns only sites classified **leave**, plus the sites R2's `--apply-pins` already rewrote (now at `$RELEASE`). `git diff --stat` (this step only) touches only the files the classification named as **bump**.

ROLLBACK: `git checkout -- <each file this step touched>`.

## R4 — reconcile the dogfooded control plane

```bash
make release-reconcile
```

`make release-reconcile` wraps the two-pass `project-standards reconcile --apply` (pass 1 refreshes a stale catalog; pass 2 must be a no-op) and a subsequent `validate`, all first on the wheel-runtime `PYTHONPATH`.

OBSERVABLE: pass 2 reports no mutations; `validate` reports OK over the managed file set; both `.standards/catalog.toml` and `.standards/lock.toml` read `release = "$RELEASE"`.

**The `.standards/catalog.toml` trap.** If reconcile refuses with `PC-RELEASE-PAYLOAD-MUTATED`, `PC-CATALOG-DIGEST-REPLACED`, `CP-CONTROL-STATE`, or `CP-MODIFIED-MANAGED`, diagnose before treating it as a payload defect: run `packages check-release --root . --baseline $PREV --json`. If it reports only `PC-RELEASE-PROJECTION`, the payloads are clean and some earlier commit rendered `.standards/catalog.toml` mid-train (never do that — the catalog and lock are release-time-only outputs). Recovery is restore-then-reconcile: `git show $PREV:.standards/catalog.toml > .standards/catalog.toml`, then the lock if `CP-CONTROL-STATE` persists, then every other managed file the offending commit touched together, then rerun `make release-reconcile`. Afterward, re-check consumer-owned workflows the restore may have reverted (any family declaring `workflow_ownership = "consumer-owned"` is never re-rendered by reconcile) — a stale pin there is a self-inflicted regression, not part of the recovery.

ROLLBACK: `git checkout -- .standards .agents .claude .github/workflows AGENTS.md CLAUDE.md && git clean -fd`, then re-run R4 from the top (R2/R3 edits are in other files and survive).

## R5 — re-render the synthetic golden catalog fixture

```bash
make release-golden RELEASE=$RELEASE
git diff -- tests/fixtures/package_contract/valid/full/expected/catalog.toml
```

OBSERVABLE: the diff is exactly two lines — the `release` string and the derived `digest` — proving the render came from the synthetic fixture root, not the real repository. No payload digest and no `[standards.*]` block may move; if any package stanza changes, the target root was wrong.

ROLLBACK: `git checkout -- tests/fixtures/package_contract/valid/full/expected/catalog.toml`.

## R6a — candidate wheel + sdist (local — do not route through rexec)

```bash
uv sync --all-groups --locked
npm ci
uv run project-standards standards sync-payload-projection --root . --check --json
uv build --clear --wheel --out-dir build/release-wheel
uv build --sdist --out-dir build/release-wheel
rm -rf -- build/wheel-runtime
uv run python -m zipfile -e build/release-wheel/project_standards-$RELEASE-py3-none-any.whl build/wheel-runtime
scripts/wheel-runtime-stamp.sh write
export PYTHONPATH="$PWD/build/wheel-runtime"
uv run project-standards --version
sha256sum build/release-wheel/project_standards-$RELEASE-py3-none-any.whl \
          build/release-wheel/project_standards-$RELEASE.tar.gz
```

OBSERVABLE: `project-standards $RELEASE` — a stale runtime silently tests the old bytes; `sync-payload-projection --check` exits 0 before the build. Record both digests: they are the baseline the periodic byte-verify and reproducibility checks (R11, periodic) compare against later.

ROLLBACK: `rm -rf build/release-wheel build/wheel-runtime` and rerun; nothing tracked is touched.

## R6b — worker environment parity

```bash
rexec --shell 'uv sync --all-groups --locked'
rexec --shell 'uv run project-standards --version'
```

OBSERVABLE: the worker reports `$RELEASE`. Skipping this produces phantom control-plane reds, because `.venv` is an rsync exclude and its editable dist metadata lags the bump. If the worker was `rexec clean`-ed, also run `rexec --shell 'npm ci'`.

ROLLBACK: none — worker state is disposable; `rexec setup` reconverges it.

## R6c — fast gate set (working-tree lanes; honest before the commit)

```bash
uv run project-standards packages check-release --root . --baseline $PREV --staged --json
uv run project-standards validate
uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards generate-package-schemas --root . --check --json
uv run project-standards standards render-catalog --root . --check
rexec -- make go-check
rexec -- env PYTHONPATH="$PWD/build/wheel-runtime" uv run pytest tests/package_contract -q
```

`--staged` classifies the still-expected pre-bump findings instead of requiring them cleared first; run the unstaged `check-release --baseline $PREV --json` again once R2–R4 have landed, and expect `"classification"` matching the pin-site survey with `"findings": []`. Add the markdownlint and prettier commands from `AGENTS.md`.

OBSERVABLE: all exit 0; `make go-check` includes `go-verify-binary` reporting a match on all committed artifacts — the proof any R4 restore did not corrupt them.

ROLLBACK: none (read-only); a red here rolls back to the owning step (R3/R4/R5).

## R7 — the release commit, on `main`

```bash
git diff --check
git status --short          # review every path; nothing unexpected staged
PROJECT_STANDARDS_RELEASE_COMMIT=1 git commit -am "release: prepare v$RELEASE"
```

`PROJECT_STANDARDS_RELEASE_COMMIT=1` is what `scripts/githooks/main-branch-guard` accepts for exactly this commit; the general escape hatch `PROJECT_STANDARDS_MAIN_COMMIT_OVERRIDE=1` is not for this and must not be used here. This commit is exempt from the draft-PR admission rule by construction — `scripts/release_prep.py` pins `RELEASE_BRANCH = "main"`.

OBSERVABLE: the commit exists on `main`; `git status --short` is empty; the commit contains `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, the R3 pins, the R4 managed surface, and the R5 golden. Record the release commit OID.

ROLLBACK: `git reset --hard <PRE_RELEASE_MAIN>` — valid until R9.

## R6d — the full battery, on the release commit (detached)

Run after R7: the hygiene lane reads the Git index, which cannot see uncommitted work. Launch it detached yourself (`setsid nohup … &`) — never through a backgrounded tool call or a worker leg that the harness can kill mid-run — and keep the tree absolutely quiet for the whole run.

```bash
setsid nohup rexec --env VERIFY_FULL_COMPAT_WORKERS=16 -- scripts/verify.sh --full \
  > verify-full.log 2>&1; echo "VERIFY_FULL_EXIT=$?" >> verify-full.log &
disown
```

`--full` defaults to `--fail-fast`, so a red lane stops the run instead of burning the remaining wall clock; pass `--keep-going` to see every lane's result in one pass when diagnosing more than one red. `rexec` forwards nothing from the local environment, so `VERIFY_FULL_COMPAT_WORKERS` must be set through `rexec --env`, not exported first.

OBSERVABLE: the log ends with `VERIFY_FULL_EXIT=0` and every lane exits 0. Poll liveness with `pgrep -x rexec` (matching the process name, never `-f`, which self-matches the wrapping `bash -c` command line). Exit codes 20–25 are `rexec` infrastructure verdicts, not gate results — retry once before treating one as a finding.

If a lane is red: fix it on `main` (a follow-up commit or `git commit --amend` while nothing is pushed), rebuild the wheel runtime (R6a) if `src/**` or a payload moved, delete the stale log, and re-run the whole battery — a targeted re-run of the failing test is evidence the fix works, not evidence the battery is green.

ROLLBACK: none (read-only); failures roll back to the owning step.

## R8 — tags (local, still reversible)

```bash
git tag -as $TAG -m "project-standards $TAG"
git tag -v $TAG
git tag -fs v$MAJOR -m "project-standards v$MAJOR (-> $TAG)" <release-commit-oid>
git tag -v v$MAJOR
git rev-parse $TAG^{commit} v$MAJOR^{commit} main   # all three identical
```

OBSERVABLE: both `git tag -v` print `GOODSIG`. Both tags resolve to the release commit. Full-version tags are immutable once pushed; only `v$MAJOR` is ever repointed, and only by delete-and-re-push, never `--force`.

**Pre-R9 gate — all must hold:** R6c green · R6d `VERIFY_FULL_EXIT=0` · both tags `GOODSIG` · working tree clean · `check-release` classification matches the pin-site survey with no findings · release notes drafted.

ROLLBACK: `git tag -d $TAG && git tag -fs v$MAJOR -m "project-standards v$MAJOR (-> $PREV)" <the v$MAJOR commit recorded at R0>`, then `git reset --hard <PRE_RELEASE_MAIN>`.

## R9 — push — point of no return

Everything before this line is reversible with `git reset --hard <PRE_RELEASE_MAIN>` and local tag deletion. After the full-version tag is pushed it is permanent: a `vMAJOR.MINOR.PATCH` tag is never deleted or moved once pushed. A mistake past this point is corrected by a new release, never by rewriting this one.

```bash
git push origin main
git push origin $TAG
git push origin :refs/tags/v$MAJOR      # delete the old remote moving tag
git push origin v$MAJOR                 # re-push it at the release commit
git ls-remote --tags origin 'v$MAJOR*'
```

`main` is pushed directly, with no PR: the admission rule is scoped to the default branch, the feature commits already landed on `testing` through it, and a PR is structurally impossible for the release commit because `release_prep.py` pins `RELEASE_BRANCH = "main"`.

OBSERVABLE: `git ls-remote --tags origin` shows both tags at the release commit; `origin/main` equals it.

ROLLBACK: none for `$TAG`. If the push fails between tags, finish the remaining pushes; `v$MAJOR` can still be repointed. If `main` pushed but the tags did not, the branch is recoverable in principle but is now public — treat it as forward-only.

## R10 — publish

```bash
gh release create $TAG \
  --title "project-standards $TAG" \
  --notes-file <notes> \
  --verify-tag --latest \
  build/release-wheel/project_standards-$RELEASE-py3-none-any.whl \
  build/release-wheel/project_standards-$RELEASE.tar.gz
gh release view $TAG --json isLatest,isDraft,isPrerelease,tagName
```

`--verify-tag` and the `isLatest`/`isDraft` assertions stay a per-release gate — they confirm the release object itself, not the asset bytes. OBSERVABLE: `isLatest: true`, `isDraft: false`, `isPrerelease: false`.

Asset byte-verification (downloading the assets back and comparing `sha256sum` against the R6a digests) is **periodic, not per-release**: release assets are convenience copies, not the supported install path, so their fidelity is checked on a schedule rather than gating every train.

ROLLBACK: `gh release delete $TAG --yes` (the release object only — the tag stays, permanently). Re-create it with corrected notes or assets; an asset-only repair is `gh release upload $TAG <file> --clobber`.

## R11 — periodic: Go binary reproducibility

Not a per-release gate (D4). Run this on a periodic cadence, or opportunistically when Go-owned files changed in the release:

```bash
rexec -- make go-verify-binary
git worktree add /tmp/release-repro $TAG
cd /tmp/release-repro && uv build --clear --wheel --out-dir out && uv build --sdist --out-dir out \
  && sha256sum out/*
git worktree remove /tmp/release-repro
```

OBSERVABLE: `go-verify-binary` green with no Go-source diff since `$PREV` means the committed binaries already reproduce from this commit's source. The wheel/sdist rebuild's digests should equal the published assets, proving `uv build` is deterministic here. A red on either is a defect worth its own issue, not a release blocker discovered this late — it should have been caught by the leg that touched the Go source.

ROLLBACK: none (verification only).

## R12 — post-release

**R12a — fast-forward `testing` from `main`.**

```bash
git checkout testing
git merge --ff-only main
git push origin testing
```

OBSERVABLE: "Fast-forward"; `main`, `testing`, and `origin/testing` are identical.

ROLLBACK: `git branch -f testing <PRE_RELEASE_TESTING>` (pre-push only).

**R12b — hosted Check on `main`, watched by run ID (L3).**

```bash
gh run list --branch main --limit 10
gh run watch <RUN_ID> --exit-status
```

Watch by ID: several workflows fire on the same push. The pre-release `PC-RELEASE-LEVEL` finding that is normal on `testing` before the bump must not appear here — the version has advanced.

ROLLBACK: none. A red is a follow-up fix on `testing`, or a patch release.

**R12c — close the issues**, only after R12b is green, through `gh-workflow close --issue <N> --as done` and confirm with `gh-workflow check --issue <N>`.

**R12d — closeout documents** (commit directly to `testing`, never through a PR — Agent Handoff convention): a new `docs/handoff/deployed.md` row (release commit, both tag objects, classification, CI result, issues closed, consumer-pin rollout decision stated either way), plus `docs/STATUS.md`, `docs/TODO.md`, `docs/handoff/state.md`, and a session log row. Validate with `make handoff-validate` and `make handoff-drift-check` — the bare `project-standards agent-handoff …` commands fail in this repository by design; the Make targets wrap the wheel-runtime `PYTHONPATH`.

**R12e — durable lessons.** Write anything a later cut would rediscover to `.workflow/lessons/` and to the shared knowledge base. Archive this train's checkpoint state.

## Wall-clock measurement

Measure the `--full` battery's per-lane cost the same way as [`docs/research/2026-09-01-release-train-wall-clock.md` §1a](../research/2026-09-01-release-train-wall-clock.md#1a-local---full-battery-v5270-worker-ct-117-via-rexec): exit code, elapsed seconds, and share of total wall clock per lane (statics, ordinary, compatibility, performance, coverage-report), read from the detached `verify-full.log` recorded at R6d, without rerunning a lane solely to remeasure it.

| Release | Statics | Ordinary | Compatibility | Performance | Coverage-report | Total |
| --- | --- | --- | --- | --- | --- | --- |
| v5.27.0 | 77s | 3031s | 3178s | 66s | 2s | 6354s (106 min) |
| v5.29.0 | _fill at cut_ | _fill at cut_ | _fill at cut_ | _fill at cut_ | _fill at cut_ | _fill at cut_ |
