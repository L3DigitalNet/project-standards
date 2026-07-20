# Handoff State

## Current focus

- Project Standards 5.2.0 is published from `4d2cc41`; signed `v5.2.0`, moving `v5`, and byte-verified GitHub wheel/sdist assets are live after all nine `main` workflow runs passed. Issues #9, #10, #11 (and an unfiled check-workflow digest gap) are corrected and closed with resolution comments.
- The 5.2.0 correction accepts the `"v3"` platform wire tag, carries the released digest lineage in Python Tooling 1.3 and Markdown Tooling 1.4, and adds the bounded-takeover contract (`unknown_content_disposition = "preserve"`, warning `CP-MIGRATION-BOUNDED-TAKEOVER`); Standard Bundle Authoring 2.3 documents it. Migration tests pin the released v3/v4 artifact bytes under `tests/fixtures/legacy_releases/` because the current-tree v1 bundles were revised after those releases.
- Keep the direct retained gates green. Future work requires explicit selection from `docs/TODO.md`.

## Active incidents

- Engine deletion is blocked until all consumers validate, the final dependency search is clean, and the owner approves.
