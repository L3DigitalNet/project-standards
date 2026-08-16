# Project Toolbox Standard

**Package version:** `1.0`.

## Purpose

Project Toolbox is the durable home for proven cross-cutting workflows and tools — assets that fit no existing standard, or that span two or more of them. Packaging them as a standard makes them versioned, distributable, reconciled, and drift-checked instead of living as personal practice.

Version 1.0 ships a deliberately minimal inventory that proves the family shape: two workflow documents and the routing skill that points at them.

## Applicability

Adopt Project Toolbox in any repository whose maintenance work is performed or assisted by agents and where those sweeps should follow one written, versioned procedure. The package makes no assumption about language, toolchain, or forge, and it requires no other standards package.

It does not apply where the packaged workflows would be dead weight — a repository with no CI, no dependencies, and no history worth sweeping gains nothing from it.

## What the package installs

| Installed path | Contents |
| --- | --- |
| `.standards/packages/project-toolbox/workflows/repo-housekeeping.md` | Periodic repository hygiene sweep |
| `.standards/packages/project-toolbox/workflows/drift-detection.md` | Claim-versus-reality verification sweep |
| `.agents/skills/project-toolbox/SKILL.md` | Routing skill, Codex CLI discovery path |
| `.agents/skills/project-toolbox/agents/openai.yaml` | Harness interface declaration |
| `.claude/skills/project-toolbox/SKILL.md` | Routing skill, Claude Code discovery path |
| `.claude/skills/project-toolbox/agents/openai.yaml` | Harness interface declaration |

Every installed file is a managed, digest-locked whole-file artifact: the package owns its complete bytes and reconciliation reports any hand edit as drift.

The two skill destinations are byte-identical copies of one payload source. Claude Code discovers project skills only under `.claude/skills/`; Codex uses `.agents/skills/`. Installing both is the only shape that serves both harnesses, and the pair must never diverge.

## Configuration

The package has no options. Its configuration schema is a closed object with no properties, so adoption is all-or-nothing: enabling the family installs the complete inventory.

```toml
[standards.project-toolbox]
enabled = true
version = "1.0"
```

## Dependency posture

Project Toolbox requires no other standards package, declares no companions, extends nothing, and conflicts with nothing.

It is nonetheless standards-aware by design. Both workflow documents open by reading `.standards/config.toml` to learn which packages the repository has installed, then fold each installed package's own gates and conventions into the sweep. That composition is instructional, not mechanical: the workflows tell the operator to run the existing machinery rather than duplicating its checks. When no packages are installed, both documents degrade to their generic checks and remain usable.

## Ownership boundary

The package ships **no executable providers** — no Python provider code, no scripts, no binaries. This is a deliberate declaration rather than an omission: version 1.0 delivers guidance documents, and every action a sweep prompts is performed and reviewed by the operator or agent as an ordinary change. Nothing in this package writes to the repository outside reconciliation's delivery of its own managed files.

The package likewise contributes no bounded block to any agent-instruction file, declares no migrations, and registers no legacy states or signatures — 1.0 is a new family with no predecessor to migrate from.

## Extending the toolbox

New proven workflows land as additive minor versions of this family rather than as new families, so a checklist document never pays a new family's integration cost. Per-tool configuration options and a mechanical drift-detection provider are deliberate deferrals, addable later without breaking consumers.

## Versioning

The `versions/1.0/` payload is immutable once released. Corrections to its normative content require a new package version; the family root is mutable navigation only.
