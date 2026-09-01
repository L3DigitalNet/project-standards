# GitHub Workflow 1.10 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.10`; applies only to repositories owned by a GitHub organization.
- Configuration is exactly two required options: `organization` (nonempty string) and `harnesses` (nonempty array of `claude-code` or `codex`). 1.9 adds four optional, defaulted admission options — `integration_branch`, `release_subject_prefix`, `admission_floor`, and `handoff_admission` — so a consumer that sets none upgrades from 1.8 by a version bump. Unknown options and empty values are rejected.
- The package is organization-agnostic; `organization` is the only place a consumer names its own organization.
- Adoption: set both options in `.standards/config.toml`, then `project-standards reconcile` and `project-standards validate`.
- Reconcile delivers the skill, six references, and the `gh-workflow` binary under both `.agents/skills/github-workflow/` and `.claude/skills/github-workflow/`, renders `.standards/packages/github-workflow/policy.toml`, and adds one managed instruction block per selected harness.
- The two skill trees are byte-identical managed copies from one source: Claude Code discovers project skills only under `.claude/skills/`, Codex only under `.agents/skills/`. Never edit or delete one to deduplicate them.
- Every subcommand is read-only against the consumer's repository: 1.5 removed `ledger`, so nothing in this package writes a file into the checkout.
- `gh-workflow` is a static linux/amd64 binary with eleven subcommands — `audit`, `new`, `set`, `close`, `reopen`, `summary`, `receipt`, `check`, `ready`, `merge`, `admission`. The skill's routing table is the complete flag surface; actions it routes to raw `gh` are documented decisions, not gaps.
- The managed block routes ordinary mutations and summaries by itself. Load the skill for triage, an organization-schema audit, a T0 or governing-relationship judgment, and uncommon recovery.
- An issue is the authorized work contract, its organization-level fields carry the typed operational metadata, and a pull request is the execution evidence.
- From 1.9 a commit on a **governed** branch — the repository default, or the `integration_branch` when the consumer declares one — is admitted by exactly one of four classes, each carrying one `Workflow-Admission` trailer: `T0` (an unambiguous prose repair, no protected surface, at most three files and thirty changed lines), `PR #N` (written by `merge --pr N` itself), `handoff`, or `release`. A topic branch is ungoverned while open. Agents apply the T0 predicate; no subcommand classifies it.
- The handoff class admits a commit whose every path is `docs/handoff/**`, `docs/STATUS.md`, or `docs/TODO.md`. The set is fixed by the standard and cannot be widened by configuration; `handoff_admission = "none"` removes the class. A commit mixing handoff and other paths is **not** a handoff commit and takes the pull-request route.
- `admission --branch B [--since REF] [--offline]` classifies a range and exits 1 listing the commits no class admits. Nothing runs it for you — the package ships no CI workflow, so an unwired check covers nothing.
- Every PR declares exactly one relationship under `## Governing work`: `Final: #N`, `Supporting: #N`, or `Standalone`. At most one open Final per Issue. A ready PR has exactly four sections: Summary, Governing work, Acceptance coverage, Verification.
- Agent-created PRs start as drafts and cross Ready through `ready --pr N`; `merge --pr N` admits them and converges a merged Final's Issue to `Done`; `close --pr N --as OUTCOME --reason S` is the only route for abandoning an open Final. All three are idempotent — rerun the same command after a partial failure.
- Open state never implies `Ready`, for an issue or a PR. The governing Issue's `Workflow` remains the sole lifecycle authority; Supporting and Standalone merges never authorize `Done`.
- `check`, `receipt`, and `summary` project one shared finding model over six categories, filtered by observed state. A receipt is a projection, not a creation ceremony: the paired commands emit one each and raw creation needs none.
- All eleven subcommands accept `--output human|json`; JSON is one envelope carrying the result class, the gate, every finding, and each mutation step.
- An explicit operator instruction is sufficient authority for the action it names and creates no standing exception.
- From 1.6, not every finding needs an issue: a related finding the session can address is fixed in place when this repository owns it, filed against the owning repository when an upstream dependency in the organization owns it, and put to the operator only when it warrants a full separate session.
- Organization schema — issue types and issue fields — is human-applied. Report differences against the versioned baseline; never mutate organization schema.
- Never manipulate rulesets, branch protection, or merge gating: the package must not control the mechanisms judging work performed under it.
- GitHub access uses the operator's existing `gh` authentication. The package embeds no credentials.
- Only the package's bounded managed block in an agent-instruction file is package-owned; the surrounding content stays consumer-owned.
- Reconciliation is offline, deterministic, and convergent on rerun. Hand-edited managed artifacts are reported as drift.
