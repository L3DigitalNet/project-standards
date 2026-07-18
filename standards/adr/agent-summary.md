# Architecture Decision Record family: Agent Summary

Current authority is the Catalog 5 consumer payload [`adr@1.1`](versions/1.1/agent-summary.md). Its [versioned standard](versions/1.1/README.md) wins over this mutable navigation summary.

- Store ADRs in `docs/adr/` and index them in that directory's `README.md`.
- Use `adr-NNNN-short-title.md` for filenames and `adr-NNNN-repo-name-short-title` for globally unique document IDs.
- Package 1.1 creates only `docs/adr/adr.template.md`; it never replaces consumer ADRs.
- Optional `require_sections` validates the three MADR-required level-2 headings.
- Markdown Frontmatter is a companion, not a dependency.
- Legacy `markdown.adr.version` maps to `contract_version`; no V2 output contains a `.project-standards.yml` fragment.

Enable `adr@1.1`, preview with `project-standards reconcile`, and apply only after reviewing the plan. See the [current adoption guide](adopt.md) for the complete procedure.
