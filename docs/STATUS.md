# Project Status

## Current snapshot

- `main` remains the released v4.3.0 line; `testing` carries the unreleased v5.0.0 standards-platform work.
- Seven standards are released or staged: the six v4 standards plus Agent Handoff v1 for the v5 release.
- Agent Handoff v1 Tasks 1-17 are complete on `feature/agent-handoff-v1`; final acceptance and release readiness remain.
- The package is repository-local: shared hook, skill, provenance lock, state, status, and tasks all remain inside the adopting repo.
- ADRs 0017-0022 define standard-package adoption, lifecycle, provenance, versioning, skills, and hook installation.
- SPEC-MT01 Steps 00-06 are complete; Step 07 remains the MCP-readiness gate before SPEC-MS01 server work.
- The release freeze remains active until v5.0.0; versioned changes accumulate under CHANGELOG `[Unreleased]`.
- Durable implementation history is in `docs/handoff/sessions/2026-07.md`; active work is in `docs/TODO.md`.
