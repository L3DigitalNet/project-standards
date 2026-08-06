# Project Status

## Current snapshot

- Project Standards 5.16.0 is the published release at `8a2d1b9a`; signed `v5.16.0` and `v5` tags are live and `uvx` from the tag reports 5.16.0.
- The release closed all ten open bug issues (#88–#126 defect set) and superseded the six dependency PRs.
- The tracker holds exactly the three feature deferrals #55, #62, and #116.
- Catalog 5 defaults: markdown-tooling 1.13, markdown-frontmatter 1.9, python-tooling 1.12, project-spec 1.7; every predecessor remains byte-immutable and selectable.
- The full local battery and the complete hosted fleet including `Check` ran green on the tagged commit.
- Release assets are byte-verified: wheel `02f51b12…`, sdist `bf3875f9…`.
- The open-issue program has T16, T19, and T36 terminal (checkpoints `50d0c364`, `229a4bc1`, `e13e1a66`; EV-008); the feature phase T24–T29 remains, with T24 ready.
- All four reusable workflows accept an optional `runner-labels` input for private same-organization callers.
- Reviewed action pins: setup-uv 9.0.0 (`prune-cache: true`), setup-node 7.0.0, setup-python 7.0.0.
- Dependabot stays disabled by decision; dependency currency moves through the payload cycle under the pin and width-table guards.
- The `js-yaml` override remains until `markdownlint-cli2-action` ships >= 0.23.2 (v24 still bundles 0.23.1).
- The ADR corpus was assessed against ADR 1.4: 11 of 23 active records state no boundary, five authorities contested, five boundaries unowned. See `docs/reviews/adr-conformance/`.
- v5.17.0 is scoped as the ADR train: #127 ships as `adr` 1.5, then the 21-item corpus backlog in #128. MINOR; 1.5 must stay non-breaking to become the Catalog 5 default.
- The repository's `docs/adr/adr.template.md` is still the 1.3 template because create-only artifacts are invisible to drift-check (bug 006).
- Program tail otherwise unchanged: T24–T29, SPEC-GSF3 T1, and the Usage Documentation Site V2 specs stay queued for later sessions.
