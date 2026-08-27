# Project Standards Roadmap

This file tracks work planned for upcoming Project Standards releases. It is forward-looking planning, not a release commitment or a substitute for the release record in [CHANGELOG.md](CHANGELOG.md).

- [Project Standards Roadmap](#project-standards-roadmap)
  - [Planned releases](#planned-releases)
    - [5.18.0](#5180)
      - [ADR v1.5 and corpus remediation](#adr-v15-and-corpus-remediation)
      - [Python Tooling configuration](#python-tooling-configuration)
      - [Agent Handoff follow-ups](#agent-handoff-follow-ups)
      - [GitHub Workflow follow-ups](#github-workflow-follow-ups)
      - [Executable payload adoption guidance](#executable-payload-adoption-guidance)
      - [Test reliability and contract cleanup](#test-reliability-and-contract-cleanup)
    - [5.19.0](#5190)
      - [ADR corpus completion](#adr-corpus-completion)
      - [Control plane and payload contract](#control-plane-and-payload-contract)
      - [Package follow-ups](#package-follow-ups)
      - [Project Specification conformance](#project-specification-conformance)
      - [Test reliability](#test-reliability)
      - [Release and execution tooling](#release-and-execution-tooling)
      - [Deferred with reasoning](#deferred-with-reasoning)
    - [5.20.0](#5200)
      - [Claude Code skill discovery](#claude-code-skill-discovery)
    - [5.21.0](#5210)
      - [Project Toolbox standards](#project-toolbox-standards)
    - [5.22.0](#5220)
  - [Beyond](#beyond)

## Planned releases

### 5.18.0

**Shipped as v5.18.0.** Kept for the planning record; [CHANGELOG.md](CHANGELOG.md) is what actually landed. Every item below shipped: `adr` 1.5, `python-tooling` 1.13, `agent-handoff` 1.11, and `github-workflow` 1.1 are the release's four Catalog 5 defaults.

#### ADR v1.5 and corpus remediation

- Publish `adr` 1.5 with the amendment vocabulary from [#127](https://github.com/L3DigitalNet/project-standards/issues/127) as the Catalog 5 default, then work the corpus backlog in [#128](https://github.com/L3DigitalNet/project-standards/issues/128) using the 1.5 amendment form. Moved here from 5.17.0 by owner direction on 2026-08-08.

#### Python Tooling configuration

- Publish a Python Tooling successor that supports scoped Ruff per-file ignore extensions without replacing package defaults or disabling rules globally, as tracked in [#116](https://github.com/L3DigitalNet/project-standards/issues/116).

#### Agent Handoff follow-ups

- Make the pre-enable legacy inventory workflow reachable or align its runbook ordering, as tracked in [#130](https://github.com/L3DigitalNet/project-standards/issues/130).
- Align exclusion guidance with Markdown Tooling's typed exclusions option in [#139](https://github.com/L3DigitalNet/project-standards/issues/139).
- Add the actionable exact-selection upgrade finding in [#141](https://github.com/L3DigitalNet/project-standards/issues/141) and correct the 1.10 adoption-guide version mismatch in [#148](https://github.com/L3DigitalNet/project-standards/issues/148).

#### GitHub Workflow follow-ups

- Derive Issue Type guidance from the schema in [#144](https://github.com/L3DigitalNet/project-standards/issues/144) and settle the family-root adoption-document decision in [#145](https://github.com/L3DigitalNet/project-standards/issues/145).
- Correct the ledger mutation guidance in [#149](https://github.com/L3DigitalNet/project-standards/issues/149) and eliminate or explicitly resolve timestamp-only ledger churn in [#154](https://github.com/L3DigitalNet/project-standards/issues/154).

#### Executable payload adoption guidance

- Document narrow pre-commit exemptions for the immutable Agent Handoff and GitHub Workflow executables without weakening repository-wide added-file protection, as tracked in [#151](https://github.com/L3DigitalNet/project-standards/issues/151).

#### Test reliability and contract cleanup

- Collapse the duplicated retained-version digest assertions tracked in [#146](https://github.com/L3DigitalNet/project-standards/issues/146), preserving the promotion-contract documentation without changing payload or catalog bytes.
- Resolve the gate-parallelism failures tracked in [#147](https://github.com/L3DigitalNet/project-standards/issues/147) so the MCP timing and determinism tests pass reliably under the ordinary verification lane.

### 5.19.0

**Shipped as v5.19.0.** Kept for the planning record; [CHANGELOG.md](CHANGELOG.md) is the release truth. The train combines the completed backlog corrections, Project Specification 1.9, and the final Catalog 5 defaults. `project-toolbox` moved to [5.21.0](#5210) when the skill-discovery repair train took [5.20.0](#5200); #129 remains deferred pending a new decision derived from amended ADR 0028.

Fourteen of the twenty triaged issues carried a materially wrong or stale premise, so several landed in a smaller or differently shaped form than filed. The issue decision comments retain the rejected alternatives and release classification.

#### ADR corpus completion

Ordered. [#162](https://github.com/L3DigitalNet/project-standards/issues/162) rewrites every active ADR body plus 46 references across 17 tracked files, so it conflicts with everything before it and goes last.

- [#161](https://github.com/L3DigitalNet/project-standards/issues/161) — ADR 0026 owns resource-URI grammar; ADR 0010 adopts it by reference. Both records still claim an open producer divergence that closed at `e400f83f` on 2026-07-29.
- [#160](https://github.com/L3DigitalNet/project-standards/issues/160) — record ADR 0024's coupling as load-bearing with a reader's map. No split: its rejected alternatives are jointly determined.
- [#159](https://github.com/L3DigitalNet/project-standards/issues/159) — a new ADR owning the `.agents/` root, allocating per artifact class. Landing it before #162 keeps the sweep to one pass over 24 records.
- [#162](https://github.com/L3DigitalNet/project-standards/issues/162) — the evidence-vs-authority link convention and the ADR 0025/0026 renames. Sweep with `git grep`; a recursive grep reaches excluded agent worktrees.
- [#163](https://github.com/L3DigitalNet/project-standards/issues/163) — validate `amends`/`amended_by` reciprocity. The corpus already passes with zero findings, so this ships the guard, not a repair.

#### Control plane and payload contract

- [#156](https://github.com/L3DigitalNet/project-standards/issues/156) — report stale predecessor version references embedded in successor payload schemas. **Lands before every payload cut below**, so the guard exists when those cuts are authored.
- [#157](https://github.com/L3DigitalNet/project-standards/issues/157) — create-only stays permanent; add a content-match advisory against every advertised payload digest in `validate` and `drift-check`. Engine-only. Amends ADR 0028 and closes bug 006.
- [#142](https://github.com/L3DigitalNet/project-standards/issues/142) — implement the `command` provider kind. Extract the bounded runner from `mcp_services` so the control-plane CLI path shares it; that path dispatches in-process with no timeout today.
- [#140](https://github.com/L3DigitalNet/project-standards/issues/140) — managed-artifact retirement. The original defect is obsolete for V5-native installs; the live defect is the `agent-handoff` 1.11 `adopt.md` guidance.

#### Package follow-ups

- [#153](https://github.com/L3DigitalNet/project-standards/issues/153) — a closed `vscode.task_prefix` enum in `python-tooling`, reserved-label documentation, and a governing-option name on the `CP-MODIFIED-MANAGED` missing-unit diagnostic.
- [#165](https://github.com/L3DigitalNet/project-standards/issues/165) — correct the `agent-handoff` legacy-migration runbook, which still names the retired `session_start.py` launcher.
- [#169](https://github.com/L3DigitalNet/project-standards/issues/169) — close the `github-workflow` gaps recorded at `agent-configs#13`.

#### Project Specification conformance

- [#143](https://github.com/L3DigitalNet/project-standards/issues/143) — advise when `runner_labels` is set but a consumer-owned caller cannot receive it. Needs no diagnostic model change; `severity` already carries `warning`.
- [#62](https://github.com/L3DigitalNet/project-standards/issues/62) then [#55](https://github.com/L3DigitalNet/project-standards/issues/55) — the approved T24 feature phase, dependency-ready since the v5.16.0 checkpoints.

#### Test reliability

- [#158](https://github.com/L3DigitalNet/project-standards/issues/158) — inject `PROVIDER_TIMEOUT_SECONDS` in the two real-provider proofs, as nine other tests already do. Measure unloaded timing first: a result near 30 s is a production defect, not a test-isolation problem.
- [#166](https://github.com/L3DigitalNet/project-standards/issues/166) — the scale gate's ceiling. Its performance-lane remedy already shipped, so confirm what remains before planning work.

#### Release and execution tooling

- [#164](https://github.com/L3DigitalNet/project-standards/issues/164) — `release_prep.py` version sweep. Its acceptance criteria are unsatisfiable as written: `sweep_version_references` reports and never rewrites, and its hint is MAJOR-only. Restate the outcome before implementing.
- [#167](https://github.com/L3DigitalNet/project-standards/issues/167) — `rexec` pytest offload. Not worktree-specific: `.git` is never mirrored from any checkout.

#### Deferred with reasoning

- [#129](https://github.com/L3DigitalNet/project-standards/issues/129) — the `adr-conformance` guardrail foundation stays deferred. Both prerequisites are closed, but its decision 10 must be re-derived from ADR 0028 as amended, which [#157](https://github.com/L3DigitalNet/project-standards/issues/157) settles.

### 5.20.0

**Shipped as v5.20.0.** Kept for the planning record; CHANGELOG.md is the release truth.

#### Claude Code skill discovery

- Verified 2026-08-15: Claude Code has never read `.agents/skills/` (Codex's convention), so every packaged skill was silently invisible to it in every consumer. [#170](https://github.com/L3DigitalNet/project-standards/issues/170) ships the fix: `agent-handoff` 1.13, `github-workflow` 1.3, and `markdown-frontmatter` 1.12 install byte-identical, digest-locked skill copies to both `.agents/skills/<id>/` and `.claude/skills/<id>/`, carried by the same-path-same-digest declaration allowance in the package contract (ADRs 0016 and 0021 amended 2026-08-15).
- [#171](https://github.com/L3DigitalNet/project-standards/issues/171) — provider-level drift checks cover both skill trees symmetrically.
- [#172](https://github.com/L3DigitalNet/project-standards/issues/172) — the two umask-fragile control-plane tests become umask-independent.

### 5.21.0

**Shipped as v5.21.0.** Kept for the planning record; [CHANGELOG.md](CHANGELOG.md) is the release truth. The train is a single feature: the ninth consumer family, `project-toolbox@1.0`, adopted by this repository in the same release.

#### Project Toolbox standards

- Develop and release the `project-toolbox` standards, tracked in [#168](https://github.com/L3DigitalNet/project-standards/issues/168). Owner direction 2026-08-09 originally placed this at 5.19.0; moved to 5.20.0 on 2026-08-10 so the triaged backlog consolidates first, then to 5.21.0 on 2026-08-15 when the skill-discovery repair train took 5.20.0.

### 5.22.0

**Shipped as v5.22.0.** Kept for the planning record; CHANGELOG.md is the release truth.

- Agent Handoff 1.14 session-scoped closeout, tracked in [#184](https://github.com/L3DigitalNet/project-standards/issues/184).
- Control-plane symlink containment/alias/hardening, tracked in [#179](https://github.com/L3DigitalNet/project-standards/issues/179) and [#186](https://github.com/L3DigitalNet/project-standards/issues/186)/[#187](https://github.com/L3DigitalNet/project-standards/issues/187).
- GitHub Workflow 1.4 Prettier-stable ledger, tracked in [#177](https://github.com/L3DigitalNet/project-standards/issues/177) and [#185](https://github.com/L3DigitalNet/project-standards/issues/185).
- Python Tooling 1.15 `runner_labels`/`enforce_line_length`, tracked in [#180](https://github.com/L3DigitalNet/project-standards/issues/180) and [#181](https://github.com/L3DigitalNet/project-standards/issues/181).
- Standard Bundle Authoring 2.7, tracked in [#173](https://github.com/L3DigitalNet/project-standards/issues/173).

## Beyond
