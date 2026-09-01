---
schema_version: '1.1'
id: 'adr-0031-project-standards-integration-branch-admission-model'
title: 'ADR 0031: Integration-Branch Admission Model and Its Enforcement'
description: 'Defines branch classes, the four admission classes including the Agent Handoff exemption, their commit trailers, and the shipped classifier that enforces them.'
doc_type: 'adr'
status: 'review'
created: '2026-09-01'
updated: '2026-09-01'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'admission'
  - 'github-workflow'
  - 'enforcement'
  - 'branching'
aliases:
  - 'ADR 0031'
  - 'Integration-branch admission model'
related:
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
  - 'docs/adr/adr-0027-adopt-go-alongside-python-with-neutral-tooling.md'
  - 'docs/adr/adr-0030-command-provider-execution-boundary.md'
supersedes: []
superseded_by: null
source:
  - 'https://github.com/L3DigitalNet/project-standards/issues/203'
  - 'https://github.com/L3DigitalNet/project-standards/issues/218'
  - 'standards/github-workflow/versions/1.8/skills/github-workflow/references/pr-standard.md'
  - 'standards/github-workflow/versions/1.8/skills/github-workflow/SKILL.md'
confidence: 'medium'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted:
    - 'Claude'
  informed: []
  amends: []
  amended_by: []
---

# ADR 0031: Integration-Branch Admission Model and Its Enforcement

MADR status: **proposed** (2026-09-01; awaiting owner ratification — issues 203 and 218).

## Context and Problem Statement

`github-workflow` 1.8 admits exactly two classes: "There are exactly two admission classes. A change is either a **T0** direct commit or it goes through a pull request. There is no third tier and no repository-configurable middle ground" (`references/pr-standard.md`), and `SKILL.md` attaches that rule to "the default branch". Two independent failures follow from the same hole.

**No vocabulary for a long-lived integration branch (#203).** Where the default branch is reached only by fast-forward from an integration branch, the obligation has no moment at which it attaches: not at commit time on the integration branch — which reads as the exempt "construction branch" that `pr-standard.md` names once and defines nowhere — and not at fast-forward time, where no commit is authored. Measured in this repository at `3bda3cf4` over `9c47907f..HEAD`: **362 commits, 1 merge commit, 0 `Workflow-Admission` trailers, 4 merged pull requests**. Twenty-five days at effectively zero compliance, and the package ships no executable enforcement of any kind.

**No route for Agent Handoff bookkeeping (#218).** T0 condition 1 requires every hunk to be a spelling, grammar, punctuation, or reflow repair, so a closeout that rewrites `state.md` and appends a session row can never qualify. The observed consequence is a pull request per closeout (#216) and, here, a hand-written carve-out in `CLAUDE.md`/`AGENTS.md` (`d5792907`) that is precisely the repository-configurable middle ground the standard forbids. 66 of the 362 commits touch only handoff surfaces.

Payload bytes are immutable once published, and both defects edit the same admission prose, so one cut must carry both.

**Governed concern:** the branch and admission vocabulary the `github-workflow` standard ships, the commit-borne evidence each admitted change carries, the mechanism that enforces it, and the disposition of this repository's hand-written carve-outs. **Applies to** any repository adopting `github-workflow` 1.9 or later. **Applies when** a commit is authored onto a branch the consumer has declared governed. **Does not apply to** GitHub rulesets, branch protection, or required checks (they still decide what is mechanically permitted); the content of the T0 predicate; which paths the `agent-handoff` standard owns; issue lifecycle and the `Final`/`Supporting`/`Standalone` relationship; or the release procedure itself. **Remains undecided:** whether a preventive local hook ever ships, and which catalog release activates 1.9.

What branch and admission classes should the standard define for a repository whose work lands on a long-lived integration branch, what evidence must each admitted commit carry, and what mechanism enforces the rule?

## Decision Drivers

- A rule with no attach point cannot be enforced; the topology must be declared before a check can exist.
- The control must be non-vacuous against a corpus at zero compliance — a clean report on this repository's history would disprove it.
- `policy.toml` is read by a bounded parser that accepts only comments, table headers, and double-quoted scalar assignments (`internal/ghworkflow/policy`), so new options must be scalars or the parser changes too.
- The exemption #218 needs must not become the configurable middle ground #218 objects to.
- A consumer that adopts `github-workflow` without `agent-handoff` must not inherit a free-commit hole on three paths it owns for other purposes.
- 1.9 must be cuttable inside one release train; the binary's bytes are rebuilt and byte-compared by `make go-check`.

## Considered Options

- **A. Declared branch classes, four admission classes, and a classifier subcommand in the shipped binary.**
- **B. Same vocabulary, enforced by a managed CI workflow contribution.**
- **C. Same vocabulary, enforced by a packaged git hook.**
- **D. Keep two classes; define the integration branch as an exempt construction branch and attach the obligation at promotion.**

## Decision Outcome

Chosen option: **A**, because it is the only option that owns the classification in one testable implementation, runs offline, can be exercised against this repository's own 362-commit history inside the cut's contract tests, and needs no new delivery machinery. B and C are enforcement _carriers_, not classifiers; each would either duplicate A's logic or depend on it. B is therefore deferred to a successor cut rather than rejected, and C is rejected outright.

This decision governs admission vocabulary and its enforcement for repositories adopting `github-workflow` 1.9+. It does not govern the surfaces listed as out of boundary above.

### D1 — Branch classes and what admits a change

Three branch classes, one of them optional and consumer-declared:

| Class | Declaration | Meaning |
| --- | --- | --- |
| Default branch | Repository default | Publication branch. Governed. |
| Integration branch | `integration_branch` option; absent means none | The single long-lived branch where authored work lands. Governed. |
| Topic branch | Everything else | Ungoverned while open; its commits are admitted only when they land on a governed branch. |

A commit authored onto a **governed** branch is admitted by exactly one of four classes, each carrying exactly one `Workflow-Admission` trailer:

| Class | Trailer | Written by |
| --- | --- | --- |
| T0 | `Workflow-Admission: T0` | the author, standing behind the predicate |
| Pull request | `Workflow-Admission: PR #N` | `gh-workflow merge --pr N`, into the merge or squash commit |
| Handoff | `Workflow-Admission: handoff` | the author (D2) |
| Release | `Workflow-Admission: release`, or a subject matching `release_subject_prefix` | the consumer's release tooling |

The PR trailer is the load-bearing addition: it is written by the tool that already owns merging, so it cannot be forgotten, and it turns PR provenance into an offline-checkable fact. **Subject-line heuristics were tested and rejected on evidence.** Over `9c47907f..3bda3cf4`, 29 commit subjects end in `(#N)` but only 4 pull requests merged, and one of those four (`bd0750f2`, PR #217) carries no suffix at all — 25 false admissions and 1 false accusation from the only offline signal available today.

Promotion **from** the integration branch to the default branch authors no commit: it is a fast-forward or a merge whose provenance is that every commit it introduces was already admitted upstream. The classifier therefore asserts on the default branch only that its tip is reachable from the integration branch or is release-class, and does its real work on the integration branch — which satisfies #203's requirement that the check target the branch where work actually lands. The release-prep commit authored directly on the default branch is the release class, not an unstated exception.

Four new `config.schema.json` options, all scalars so the bounded `policy.toml` parser is unchanged:

| Option | Type | Default | Purpose |
| --- | --- | --- | --- |
| `integration_branch` | string | `""` | Names the integration branch; empty means the two-branch topology. |
| `release_subject_prefix` | string | `""` | Subject prefix that admits a release commit without a trailer. |
| `admission_floor` | string | `""` | Commit-ish enforcement epoch; commits at or before it are not classified. |
| `handoff_admission` | `"agent-handoff"` \| `"none"` | `"agent-handoff"` | Whether the handoff class exists in this repository (D2). |

`admission_floor` exists because adoption cannot rewrite history: without it every adopter's first run is a permanent red, and a permanently red control is ignored. It records where enforcement begins rather than pretending the past complied.

**Rejected:** option D — declaring the integration branch an exempt construction branch and attaching the obligation at promotion. It is the status quo with a name: a fast-forward creates no reviewable object, so the obligation attaches to nothing, and it would have admitted all 362 commits. The orphaned `construction branch` occurrence in `pr-standard.md` is deleted rather than defined.

### D2 — The handoff admission class

A commit whose every path lies in the handoff set admits directly, carrying `Workflow-Admission: handoff`. The default set is fixed by the standard as `docs/handoff/**`, `docs/STATUS.md`, and `docs/TODO.md` — exactly the document artifacts `agent-handoff` 1.16 declares as targets. A **mixed** commit — any handoff path plus any non-exempt path — is governed by the pull-request rule, stated explicitly in `pr-standard.md` and in the managed instruction block, so the exemption cannot be used as a wrapper for unrelated work.

**`policy.toml` may not extend the path set.** The only knob is `handoff_admission = "none"`, which removes the class for a consumer that has not adopted `agent-handoff` and whose `docs/TODO.md` is an ordinary document. Rationale: #218's own objection is that a consumer-side override is the middle ground the standard forbids; `agent-handoff`'s config schema exposes no document-root option, so the set is invariant across every consumer that has the standard; and an extensible exempt set is a live bypass surface — an agent could widen it to cover its own change, which the skill already classifies as an escalation, not a convenience. **Reopens if** `agent-handoff` gains a configurable document root, or a consumer presents a handoff surface outside the three paths.

**Rejected:** a subject-prefix convention (for example `docs(handoff):`). It is checkable but not _sound_ — it neither implies nor is implied by the paths touched, so it would admit a prose commit that never touched a handoff file and refuse a correct closeout with a different subject. **Rejected:** deriving the class from paths alone with no trailer. `git log` cannot express "touched only these paths", so #218's audit requirement would be unmet, and a direct commit would carry no declaration its author stands behind. A handoff-only commit missing the trailer is a distinct, self-explaining finding rather than an unadmitted commit.

### D3 — Enforcement mechanism

Ship `gh-workflow admission --branch B [--since REF] [--offline]`: it classifies every commit in the range against D1 and D2, exits `1` with per-commit findings naming the commit, what was violated, and which trailer or route would satisfy it, and exits `0` only when every commit is admitted. PR provenance is verified through the existing `ghapi` client when authenticated — the binary is not blind to PR state, contrary to the framing in #203 — and `--offline` falls back to the `Workflow-Admission: PR #N` trailer alone, which is why D1 makes `merge` write it.

Placement follows the binary's existing seam: a new `internal/ghworkflow/admission` package with one self-registering command file, plus one blank import in `cmd/gh-workflow/main.go`, whose own comment records that "adding a subcommand adds one import line here and one file in its own package; no dispatch table is edited". Commit inspection shells out to `git` with fixed argument vectors; the module takes no new dependency (`go mod tidy -diff` is a gate). Sealing is the standing procedure: `scripts/build-gh-workflow.sh` moves `ARTIFACT_OUTPUT_PATH` to the 1.9 payload directory and `ARTIFACT_LDFLAGS` to `-X main.version=1.9`, `make go-binary` rebuilds the committed bytes, and `make go-check` re-runs `go-verify-binary`, which rebuilds to a temp directory and byte-compares — so the payload binary can never drift from the source in the same commit.

Non-vacuity is provable now. Classifying `9c47907f..3bda3cf4` by the D1/D2 rules with no floor yields 9 release commits, 0 T0, 66 handoff-only, 4 PR-admitted, and **283 unadmitted commits** out of 362. The contract test pins that shape, and the negative case removes the handoff or release clause and asserts the count moves.

**Deferred, not rejected — B, a managed CI workflow contribution.** It is the only option that fires without anyone remembering, and `markdown-frontmatter` shows the mechanism (a job contributed into `.github/workflows/validate-standards.yml` under `shared_identity`, gated by `workflow_ownership`, with `runner_labels`). But `github-workflow` contributes nothing to `.github/` today, so B means new workflow templates, a render provider, two new options, and their contract tests — a second cut's work that would not fit 1.9 this week, and it would carry no classification logic of its own. 1.9 therefore ships the classifier and states plainly in `pr-standard.md` what enforces the rule and what does not, and wires the check into _this_ repository's consumer-owned CI as the dogfood proof. **Reopens** as 1.10 once the classifier's finding set is stable.

**Rejected — C, a packaged git hook.** ADR 0022 makes packaged hook installation available, so it is feasible, but a hook is per-clone, silently bypassed by `--no-verify`, and absent from CI. It adds a second delivery path and a second place to bypass without covering anything CI would not.

### D4 — Disposition of this repository's hand-written carve-outs

| Site | Disposition |
| --- | --- |
| `CLAUDE.md` Non-Negotiables branch bullet (`d5792907`, `996bf924`) | **Rewrite.** Delete the restated admission classes and the handoff carve-out, both of which the managed block will carry; keep only consumer-owned specifics — the branch names, `release_prep.py`'s `RELEASE_BRANCH`, and the `main-branch-guard` override. Hand-owned prose outside the managed block; reconcile will not touch it, so it is a human edit in the same release. |
| `AGENTS.md` pointer bullet (`996bf924`) | **Rewrite to a pointer.** The managed `github-workflow` block now carries the classes; the hand-owned bullet keeps only the branch names, which closes the `AGENTS.md`/`CLAUDE.md` asymmetry #203 measured. |
| `docs/handoff/conventions.md` §24 (`:481`) | **Keep** as consumer-owned operational detail (it documents the local hook), with its "no PR" implication reworded to the promotion class. This is an `agent-handoff`-owned surface: it changes through the closeout path, never through the payload cut. |
| `docs/handoff/conventions.md` §20 (`:422`) | **Keep unchanged.** The `testing` mention there is incidental to an unrelated rule. |
| `scripts/githooks/main-branch-guard:4-6` | **Keep.** It enforces the default-branch half locally and remains correct; add one comment line naming the promotion class so the two vocabularies agree. |
| `meta/versioning.md:131` | **Rewrite** the phrase calling `testing` a "topic branch" to "integration branch". Under D1 a topic branch is precisely the ungoverned class `testing` is not, and this is the vocabulary conflict #203 names. |
| `.standards/config.toml` `[standards.github-workflow]` | **Extend** with the four D1/D2 options at release-time reconcile: `integration_branch = "testing"`, `release_subject_prefix = "release: prepare v"`, `admission_floor` set to the adoption epoch, `handoff_admission` left at its default. |

**Rejected:** deleting all six sites and relying on the managed block alone. Three of them encode consumer-owned facts no managed block can carry — the branch names, `release_prep.py`, and the local hook — and `docs/handoff/conventions.md` is an `agent-handoff`-owned surface the cut may not edit at all, so a delete-everything migration would drop true operational detail and reintroduce the vocabulary conflict from the other side.

### Consequences

- Good, because the obligation finally attaches to the branch where work lands, and the tool that merges writes the evidence the check reads.
- Good, because the handoff exemption is owned by the standard, so the hand-written carve-out can be deleted rather than blessed.
- Bad, because 1.9 ships a check nobody is obliged to run; until B lands, coverage depends on each consumer wiring it into CI, and `pr-standard.md` must say so rather than imply coverage.
- Bad, because `admission_floor` makes the historical corpus permanently invisible to the check by design; the record of what it would have flagged lives here, not in a passing gate.
- Neutral, because `Workflow-Admission` grows from one value to four; existing T0 commits stay valid and no published payload changes.

### Confirmation

A change is in scope when it is a commit on a branch named by `integration_branch` or on the repository default branch, after `admission_floor`. Conformance is confirmed by `gh-workflow admission --branch <branch>` exiting `0`, and by the 1.9 contract test file pinning the classification of this repository's `9c47907f..3bda3cf4` corpus together with a negative case that fails when a clause is removed. Out-of-scope commits — topic branches, and anything at or before the floor — receive no finding.

## Pros and Cons of the Options

### A. Classifier subcommand in the shipped binary

- Good, because one implementation owns classification and is unit-testable and offline-capable.
- Good, because it can be run against any range at any moment, including this repository's own history.
- Bad, because nothing invokes it automatically until a consumer wires it in.

### B. Managed CI workflow contribution

- Good, because it fires without anyone remembering, on the branch where work lands.
- Neutral, because the mechanism is proven by `markdown-frontmatter`.
- Bad, because it detects only after the push, and the delivery surface does not fit this cut.

### C. Packaged git hook

- Good, because it is the only preventive option.
- Bad, because it is per-clone, bypassable with `--no-verify`, and invisible to CI.

### D. Exempt construction branch, obligation at promotion

- Good, because it needs no new vocabulary.
- Bad, because a fast-forward creates no reviewable object, so the obligation attaches to nothing; it would have admitted all 362 non-compliant commits.

## More Information

Evidence was read at `3bda3cf4` in this repository: `standards/github-workflow/versions/1.8/` (payload, `config.schema.json`, `resources/policy.toml`, `skills/github-workflow/`), `internal/ghworkflow/` (`policy`, `ghapi`, `cli`), `cmd/gh-workflow/main.go`, `scripts/build-gh-workflow.sh`, `Makefile`, and `standards/agent-handoff/versions/1.16/payload.toml`. The corpus counts quoted throughout are reproducible with `git rev-list`, `git log --format=%B`, and `git show --name-only` over `9c47907f..3bda3cf4`.

### Appendix: the `github-workflow` 1.9 edit list

- `standards/github-workflow/versions/1.9/` — copy 1.8 forward; 1.8 stays byte-immutable.
- `skills/github-workflow/references/pr-standard.md` — replace the two-class §"Admission" with the branch-class table and the four admission classes; delete the orphaned `construction branch` sentence; add the mixed-commit rule; add a paragraph stating what enforces the rule and what does not.
- `skills/github-workflow/SKILL.md` — rewrite the **Admission** decision procedure away from "the default branch one of exactly two ways"; add the `admission` row to the routing table; bump `metadata.version` and `lines`.
- `providers/gh_workflow.py` — extend `_block_body()` so the managed `AGENTS.md`/`CLAUDE.md` block names all four classes and the handoff exemption (#218 criterion 3), and render the four new options into `policy.toml`.
- `resources/policy.toml` — add the four `@option@` placeholders as double-quoted scalars.
- `config.schema.json` — add `integration_branch`, `release_subject_prefix`, `admission_floor`, `handoff_admission` with the defaults in D1.
- `payload.toml` — bump `version`, re-digest every changed resource and artifact.
- `internal/ghworkflow/admission/command.go` (+ tests) — the classifier; `cmd/gh-workflow/main.go` gains one blank import.
- `internal/ghworkflow/mutate/merge.go` — write `Workflow-Admission: PR #N` into the merge or squash commit body.
- `internal/ghworkflow/cli/cli.go` — `DefaultVersion` (currently `"1.7"`, already lagging).
- `scripts/build-gh-workflow.sh` — `ARTIFACT_OUTPUT_PATH` to the 1.9 directory, `ARTIFACT_LDFLAGS` to `-X main.version=1.9`; then `make go-binary` and `make go-check`.
- `tests/package_contract/test_github_workflow_1_9.py` — new file: the four classes and their trailers; the mixed-commit rule; `handoff_admission = "none"`; the block-text assertions for #218 criterion 3; the corpus classification and its negative case.
- `catalogs/5.toml`, `standards/github-workflow/README.md`, `CHANGELOG.md`, `UPGRADING.md` — channel promotion, family prose, and consumer-visible notes.
- Repository-side, after reconcile: the six D4 sites and the `.standards/config.toml` options.
