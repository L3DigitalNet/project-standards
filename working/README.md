# Working Folder

Scratch space for in-progress release work on the standards. **Nothing here is a
governing artifact** — the authoritative standard, schema, templates, examples,
validator, and changelog all live in the repo proper. These files are excluded
from frontmatter validation (not in `.project-standards.yml` include globs).

## Layout

- [`HANDOFF.md`](HANDOFF.md) — **the living session handoff.** Read it first at
  the start of any session; update it at the end. It is the permanent process
  doc; see its header for how it works.
- `archive/<version>/` — frozen planning docs (plans + proposals) for a shipped
  release, moved here once the work lands. One subfolder per release
  (e.g. `archive/v1.1.0/`), each with its own `README.md` index.

## Ritual

While a release is in flight, its planning docs live under
`archive/<next-version>/` (or a temporary `plans/` folder) and `HANDOFF.md`
points at them. When the release ships, the planning docs stay archived under
their version and `HANDOFF.md` is reset to point at the next piece of work.
