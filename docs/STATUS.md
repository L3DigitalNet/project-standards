# Project Status

## Current snapshot

- Project Standards 5.23.0 is published from release commit `740caf4c`; signed `v5.23.0` and moving `v5` tags are live.
- The release assets are byte-verified: wheel `371eb89b…` and source distribution `cc32f377…`. Full evidence is in
  `docs/handoff/deployed.md`.
- Package cuts this release: github-workflow 1.5 (ledger subcommand + `docs/GH-WORKFLOWS.md` removed, leaner
  `SKILL.md`/field-vocabulary, agents self-define acceptance criteria/Ready/Execution mode except `Unattended agent`),
  agent-handoff 1.15, markdown-frontmatter 1.13 (new `harnesses` option), python-tooling 1.16 (`uv_build` `<1.0`
  pin), project-toolbox 1.1.
- Issues closed Done/completed with release references: #174 #175 #182 #183 #188 #189 #190 #192 #193.
- Filed this session: #191 (Inbox, re-measure the corpus after 1.5 deploys), #194 (Ready, generic
  provider-registry==payload contract check), #195 (Ready, `CP-VERIFY` should name its target).
- Still owner-held: #178 (plan disposition) and #129.
- Owner deviation to resolve: spec keeps `Unattended agent` owner-only, narrower than "all three by judgment"; no
  mechanism honors the wider rule yet.
- `rexec` is the full gate path; the pre-tag battery ran green remotely (statics/compatibility/performance/coverage
  90%), plus a detached rerun after the harness killed the first background `--full` run.
- Consumer-pin rollout is deferred to owner scheduling; `@v5` trackers inherit 5.23.0 automatically. Consumers of
  `github-workflow` must delete `docs/GH-WORKFLOWS.md` manually per `UPGRADING.md`'s 5.23.0 subsection.
- Consumer repos still on `.agents`-only skill trees (`agent-ventures`, `llm-wiki`) per the session-corpus review's F2.
