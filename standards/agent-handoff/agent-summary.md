# Agent Handoff family: Agent Summary

Current authority is the Catalog 5 consumer payload [`agent-handoff@1.3`](versions/1.3/agent-summary.md). Its [versioned standard](versions/1.3/README.md) and installed repo-local skill win over this mutable navigation summary.

- Keep all project handoff knowledge inside the adopting repository.
- Preserve consumer-owned `docs/STATUS.md`, `docs/TODO.md`, and `docs/handoff/**`; package operations create them only when absent.
- Route facts by lifetime: current snapshot to `STATUS.md`, work queues to `TODO.md`, immediate focus to `state.md`, and durable deployment, architecture, conventions, spec/plan, session, or bug facts to their named owners.
- Do not reread `state.md` when SessionStart already injected it. In manual mode, read it and inspect Git state.
- Store credential references only, never values.
- The standard owns only its repo-local skill, optional shared hook, package policy, and declared bounded integration units.

Validate with `project-standards agent-handoff validate --repo .` and check managed drift with `project-standards agent-handoff drift-check --repo .`. See the [current adoption guide](adopt.md) for configuration and migration.
