# Working Folder

Scratch space for in-progress release work on the standards. **Nothing here is a governing artifact** — the authoritative standard, schema, templates, examples, validator, and changelog all live in the repo proper. These files are excluded from frontmatter validation (not in `.project-standards.yml` include globs).

## Layout

- [`HANDOFF.md`](HANDOFF.md) — **the living session handoff.** Read it first at the start of any session; update it at the end. It is the permanent process doc; see its header for how it works.
- `linting-formatting/` — active planning docs for the in-flight release (currently the DEC-1…9 decision trail in `linting-formatting-stack.md`). Moves to `archive/<version>/` when the release ships.
- `archive/<version>/` — frozen planning docs (plans + proposals) for a shipped release, moved here once the work lands. One subfolder per release (e.g. `archive/v1.1.0/`), each with its own `README.md` index.

## Ritual

While a release is in flight, its planning docs live under `archive/<next-version>/` (or a temporary `plans/` folder) and `HANDOFF.md` points at them. When the release ships, the planning docs stay archived under their version and `HANDOFF.md` is reset to point at the next piece of work.

## Next release — `1.3.0` (implemented on `testing`, unreleased)

Feature-complete and green; awaiting the release ritual (see [`HANDOFF.md`](HANDOFF.md)):

- The required linting/formatting stack is specified and wired — markdownlint (full explicit config + opt-in CI workflow), Prettier (repo-local formatter + CI gate), and `.editorconfig`, all trailed as DEC-1…9.
- First ADR conventions on **MADR 4.0**, plus an opt-in ADR section-structure validator check.

Further out: pre-commit hooks (deferred); `2.0.0` repo-root-relative link enforcement (breaking).
