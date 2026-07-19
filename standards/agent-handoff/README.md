# Agent Handoff Standard

This is the Catalog 5 family landing page for the active consumer package `agent-handoff@1.2`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Agent Handoff 1.2 standard](versions/1.2/README.md) — normative repository-knowledge and session-continuity contract
- [Agent Handoff 1.2 adoption guide](versions/1.2/adopt.md) — exact profiles, outputs, ownership, migration, and troubleshooting
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Agent Handoff 1.2 agent summary](versions/1.2/agent-summary.md) — session startup, fact routing, and closeout rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Agent Handoff for repository-local project knowledge, bounded session continuity, a shared repo-local skill, and optional Claude Code or Codex SessionStart integration. Consumer-authored `docs/**` knowledge is create-only. The package centrally locks only its skill, optional hook, policy, and bounded integration units; it never owns workstation-global state or credentials.

## Adopt

```bash
project-standards standards enable agent-handoff --version 1.2
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying. Choose manual or automatic startup through the package options in `.standards/config.toml`.

After adoption, use:

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
```

## Legacy boundary

The legacy `project-standards adopt agent-handoff` route, package-specific provenance lock, `.project-standards.yml` integration, and unversioned V1 artifacts are migration evidence only. They do not define current Catalog 5 behavior. Use the exact `versions/1.2/` payload and unified reconciliation.
