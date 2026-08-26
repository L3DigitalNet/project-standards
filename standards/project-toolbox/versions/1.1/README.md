# Project Toolbox Standard

**Package version:** `1.1`.

## Purpose

Project Toolbox is the durable home for proven cross-cutting workflows and tools — assets that fit no existing standard, or that span two or more of them. Packaging them as a standard makes them versioned, distributable, reconciled, and drift-checked instead of living as personal practice.

Version 1.0 shipped a deliberately minimal inventory that proves the family shape: two workflow documents and the routing skill that points at them. Version 1.1 adds a `harnesses` option and gates the Codex-only `openai.yaml` skill sidecar on it; every other document and artifact is unchanged.

## Applicability

Adopt Project Toolbox in any repository whose maintenance work is performed or assisted by agents and where those sweeps should follow one written, versioned procedure. The package makes no assumption about language, toolchain, or forge, and it requires no other standards package.

It does not apply where the packaged workflows would be dead weight — a repository with no CI, no dependencies, and no history worth sweeping gains nothing from it.

## What the package installs

| Installed path | Contents |
| --- | --- |
| `.standards/packages/project-toolbox/workflows/repo-housekeeping.md` | Periodic repository hygiene sweep |
| `.standards/packages/project-toolbox/workflows/drift-detection.md` | Claim-versus-reality verification sweep |
| `.agents/skills/project-toolbox/SKILL.md` | Routing skill, Codex CLI discovery path |
| `.agents/skills/project-toolbox/agents/openai.yaml` | Harness interface declaration (Codex only, gated by `harnesses`) |
| `.claude/skills/project-toolbox/SKILL.md` | Routing skill, Claude Code discovery path |

Every installed file is a managed, digest-locked whole-file artifact: the package owns its complete bytes and reconciliation reports any hand edit as drift.

The two `SKILL.md` destinations are byte-identical copies of one payload source. Claude Code discovers project skills only under `.claude/skills/`; Codex uses `.agents/skills/`. Installing both is the only shape that serves both harnesses, and the pair must never diverge.

`agents/openai.yaml` is a Codex-only descriptor that Claude Code never reads, so it installs solely at `.agents/skills/project-toolbox/agents/openai.yaml`, gated on the `harnesses` option containing `codex`. No `.claude/skills/project-toolbox/agents/openai.yaml` copy is declared (issue #175).

## Configuration

| Option | Default | Purpose |
| --- | --- | --- |
| `harnesses` | `["claude-code", "codex"]` | Selected coding-agent harnesses. Controls only which skill artifacts install where a target is harness-specific — currently just the Codex-only `agents/openai.yaml` sidecar. |

```toml
[standards.project-toolbox]
enabled = true
version = "1.1"
```

## Dependency posture

Project Toolbox requires no other standards package, declares no companions, extends nothing, and conflicts with nothing.

It is nonetheless standards-aware by design. Both workflow documents open by reading `.standards/config.toml` to learn which packages the repository has installed, then fold each installed package's own gates and conventions into the sweep. That composition is instructional, not mechanical: the workflows tell the operator to run the existing machinery rather than duplicating its checks. When no packages are installed, both documents degrade to their generic checks and remain usable.

## Ownership boundary

The package ships **no executable providers** — no Python provider code, no scripts, no binaries. This is a deliberate declaration rather than an omission: the package delivers guidance documents, and every action a sweep prompts is performed and reviewed by the operator or agent as an ordinary change. Nothing in this package writes to the repository outside reconciliation's delivery of its own managed files.

The package likewise contributes no bounded block to any agent-instruction file and registers no legacy states or signatures. It declares no migrations either: this family has no legacy pre-catalog state to migrate from, so that stays empty even now that 1.1 has an in-repo predecessor.

## Extending the toolbox

New proven workflows land as additive minor versions of this family rather than as new families, so a checklist document never pays a new family's integration cost. Per-tool configuration options and a mechanical drift-detection provider are deliberate deferrals, addable later without breaking consumers.

## Versioning

The `versions/1.1/` payload is immutable once released. Corrections to its normative content require a new package version; the family root is mutable navigation only.
