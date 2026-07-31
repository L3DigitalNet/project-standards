---
schema_version: '1.1'
id: 'reference-k4n2pw-self-hosted-runner-security-review'
title: 'Self-Hosted Runner Security Review'
description: 'Adversarial security review of migrating this public repository onto the homelab self-hosted runner pool: refuted designs, required hardening program, and the deferral decision recorded for the v5.13.0 train.'
doc_type: 'reference'
status: 'active'
created: '2026-07-31'
updated: '2026-07-31'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - ci
  - self-hosted-runner
  - security
  - migration
  - deferral
aliases: []
related:
  - 'docs/TODO.md'
---

# Self-Hosted Runner Security Review

Recorded 2026-07-31 from the adversarial security review run during the v5.13.0 train. All live-state claims were verified against the GitHub API, the homelab Ansible tree, and docs.github.com on that date. **Outcome: the migration was deferred from v5.13.0 by owner decision.** This record exists so a future migration starts from the review, not from scratch.

## Decision

- The owner's requirement was: untrusted fork code can never execute on the self-hosted runner without admin approval.
- The simple design (flip `allows_public_repositories` on runner group 3, set fork-PR approval to `all_external_contributors`, move `runs-on`) was **refuted** against that requirement.
- A dedicated-group architecture with a ten-item hardening program was approved by the reviewer as the viable shape, but several items are VM 200 / Ansible work in the homelab repository.
- Given that GitHub-hosted runners are free for public repositories (the minute-savings motivation is void; speed was the only remaining payoff), the owner deferred the migration. It returns under the `agent-managed-repo` / repository-governance program.

## Why the simple design fails

1. **Group exposure.** Group 3 (`homelab-private`) has `visibility: all`, made safe by `allows_public_repositories: false` — a documented pairing in the gh-runner machine notes (visibility widened 2026-05-28 _because_ the public flag stayed off). Flipping the flag while keeping `visibility: all` grants every public org repo access to the pool under each repo's own fork-PR policy, which the org policy cannot floor: the org-level approval policy is a default, not an enforcement (repo settings override it; the API schema has no enforcement field).
2. **A per-repo allowlist is not viable either.** The runner-usage census is larger than assumed (`hw-radar` is public and uses the pool; `PinkBox-Portfolio` uses it and was missed; the census sweep was rate-limit-truncated). The org previously abandoned a hand-maintained 16-repo list for exactly this maintenance reason.
3. **Docker group equals root on the VM.** Runner users are in the `docker` group of a rootful daemon (spec D14: container escape is root-on-VM). Verified escalation chain: approved fork-PR job → `docker run --privileged` → root → read the mTLS client cert → mint a JIT runner config (the mint proxy accepts caller-chosen name and labels) → register a rogue runner inside group 3 → receive jobs from every private repo, including deploys carrying 13 secrets across 4 repos and three `production` environments with no protection rules.
4. **Tailnet reach.** UFW allows all traffic on `tailscale0` in both directions and the tailnet still runs a single broad grant (spec D25), so any job reaches the whole homelab without needing the escape.
5. **Undocumented GitHub behaviors are load-bearing.** No documentation states that a job awaiting fork-PR approval is never dispatched to a self-hosted runner, nor whether Dependabot PRs are subject to the approval policy. Both must be verified empirically before any go-live.
6. **`pull_request_target` / `workflow_run` bypass approval entirely** ("always run, regardless of approval settings"). None exist in this repository today; adding one later would void the gate silently.

## Approved architecture (for the future migration)

Dedicated runner group `homelab-public`: `visibility: selected` containing only this repository, `allows_public_repositories: true`, one slot moved from the pool with a distinct label (e.g. `l3digital-public`). Group 3 stays exactly as it is. This closes the other-public-repos leg completely, keeps private repos immune to allowlist mistakes, and gives the isolation slot that the per-slot hardenings below attach to.

## Required hardening program (execution order)

1. Create `homelab-public` group as above; never flip `allows_public_repositories` on group 3.
2. Remove the public slot's user from the `docker` group (the three candidate workflows use no Docker; free).
3. Per-slot systemd `IPAddressDeny` for RFC1918 + CGNAT ranges (resolver re-allowed; the JIT mint uses the public endpoint and is unaffected).
4. A CI gate that fails if `pull_request_target` or `workflow_run` appears anywhere under `.github/workflows/`.
5. Repo fork-PR approval policy → `all_external_contributors`.
6. Route Dependabot PRs to `ubuntu-latest` via a `runs-on` expression on `github.actor`.
7. Per-slot `RUNNER_TOOL_CACHE` under the slot's `_work` (auto-wiped); the shared `/opt/hostedtoolcache` is group-writable and never wiped.
8. Empirically verify approval-before-dispatch and Dependabot gating with throwaway PRs before the first real fork PR.
9. Enable `systemd-journal-upload` on VM 200 (the one unmet item from GitHub's ephemeral-runner guidance; today all forensics are root-wipeable on the box that would be compromised).
10. Resolve the inert pre-job label hook (backlog #27): its log-only rationale is "the public-repo vector is closed org-side", which the migration voids; its documented revive trigger fires on this change.

## Recommended (not gating)

- Org fork-PR approval → `all_external_contributors` as a default for future repos only; it constrains nothing existing.
- `sha_pinning_required` after converting all action pins to full SHAs (it hard-fails tag pins, including GitHub-authored actions).
- Branch protection on `main` (none exists); required reviewers on the three empty `production` environments.
- Tailnet wildcard removal (D25) — the plan file the spec cites does not exist; write it or amend the spec.
- Constrain the JIT mint proxy: reject labels outside the expected set and names outside `gh-runner-[1-3]`, so a leaked cert cannot register an off-box runner.
- Re-run the runner-usage census to completion before trusting any allowlist.

## Homelab findings independent of this migration

These affect the seven-plus repos already using the pool today and belong to the homelab repository's queue, not this train: the docker-group root-on-VM posture for all slots, unrestricted tailnet reach from jobs, journal upload disabled, unprotected `production` environments, the permissive JIT mint surface, and the inert pre-job label hook (546/546 mismatches logged, zero enforced).

## Unresolved questions (blockers for a future go-live)

Approval-before-dispatch semantics; Dependabot gating; Copilot coding-agent PR gating; outside-collaborator exemption wording conflict; per-repo policy override provenance; VM 200 resolver address; live Tailscale ACL state; no-matching-runner queue timeout; the completed usage census.
