# Pull Request Standard

The pull request is the execution record for a work contract. This reference owns PR _content_: what a PR says, what it links, when it is a draft, and what happens to work it discovered. It does not own PR _existence_ — see the deference below.

## When a PR is required

Whether a change must go through a pull request at all is repository-local policy. The consuming repository's branch rules, protections, and its own contributor instructions decide the direct-push versus PR threshold, and that threshold legitimately differs per repository with project scope, exposure, and importance. This standard's PR obligations bind only once a PR exists.

Absent repo-local policy, the default is:

- nontrivial or consequential changes go through a pull request;
- minor or inconsequential changes may be pushed directly rather than polluting history with ceremony.

Where a repository states its own threshold, that statement wins over this default. Enforcement of any threshold belongs to the repository's rulesets and protected-branch configuration, never to an agent's discretion: an implementation agent never bypasses or weakens protected-branch policy, and never argues its way past a required check.

## PR content

A nontrivial implementation PR should reference its governing Issue. Recommended body:

```markdown
## Summary

What changed.

## Governing work

Issue or plan being implemented.

## Acceptance coverage

How the implementation satisfies the Issue's acceptance criteria.

## Verification

Commands and checks actually executed.

## Risk / compatibility notes

Material behavioral, migration, security, or compatibility implications.

## Follow-up

Discovered work intentionally excluded from the current PR.
```

Two sections carry most of the evidentiary weight. **Acceptance coverage** ties the change back to the Issue's stated criteria, so a reviewer can judge completeness without reconstructing intent. **Verification** records the commands and checks that actually ran; a command listed there but never executed is a false evidence claim.

## Follow-up work

Follow-up work that will survive the PR should become Issues. Do not leave significant future work only as:

- review comments
- prose TODOs in the PR
- agent-session notes

Durable work discovered during implementation gets a real work contract before the session ends, or it is lost.

## Draft PRs

For substantial work, open a draft PR once a coherent implementation exists and externalized review or CI becomes useful. A draft PR gives GitHub a durable representation of active execution without implying acceptance.

Because a local agent runs under observation, there is no need to require a draft PR immediately when a task begins merely to prove that an agent is working. The boundary is:

> Open the PR when repository-visible implementation state becomes useful.

Marking a PR ready for review asserts that the implementation is complete against its acceptance criteria and that verification has actually run.

## Lifecycle coupling

A PR is evidence, not state. The governing Issue's `Workflow` field carries the lifecycle: `In progress` while implementation continues, `In review` once the deliverable awaits acceptance or verification, and a terminal value only when acceptance criteria are satisfied or the work is abandoned. Merging a PR does not by itself make an Issue `Done`; route the terminal transition through `gh-workflow close` so the `Workflow` value and the GitHub close reason stay paired.

Creation and merge themselves are raw `gh` — `gh pr create --body-file PATH`, `gh pr merge N` — because a PR body has no vocabulary for the tool to validate. What the tool does validate is the part that matters: run `gh-workflow receipt --pr N` immediately after creating a PR, which reports the governing-issue link and the other gaps while they are still cheap to close.
