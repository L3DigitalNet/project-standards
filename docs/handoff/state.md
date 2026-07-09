# State

**Last updated:** 2026-07-09

## Active

- `testing` carries unreleased v5.0.0 work; `main` remains released v4.3.0 (`v4.3.0@74db623`).
- Release freeze holds until v5.0.0; Steps 00-06 and package ADRs 0017-0021 are complete.
- `SPEC-DPEY` defines the new `agent-handoff` v1 standards package and awaits owner review.
- Handoff v3.5 migration is applied; fatal checks pass, with advisories only in historical session rows and the generated bug index.

## Next

- Review `SPEC-DPEY`; after approval, write its implementation plan.
- SPEC-MT01 Step 07 remains queued: produce the MCP-readiness report and close blocking traceability gaps.

## Blockers

- No active incidents.
- Do not start SPEC-MS01 MCP server work until SPEC-MT01 readiness gate passes.

## Pointers

- `TODO.md` has the v5.0.0 tracker and release-cut queue.
- `STATUS.md` summarizes current released and unreleased state.
- `docs/handoff/specs-plans.md` indexes active specs and plans.
- `meta/versioning.md` is the release policy source.
