# Architecture Decision Record family: Agent Summary

Current authority is the Catalog 5 consumer payload [`adr@1.6`](versions/1.6/agent-summary.md). Its [versioned standard](versions/1.6/README.md) wins over this mutable navigation summary.

- Store ADRs in `docs/adr/` and index them in that directory's `README.md`.
- Use `adr-NNNN-short-title.md` for filenames and `adr-NNNN-repo-name-short-title` for globally unique document IDs.
- Package 1.6 creates only `docs/adr/adr.template.md`; it never replaces consumer ADRs or an existing scaffold.
- Optional `require_sections` validates the three MADR-required level-2 headings.
- Optional `validate_amendments` independently checks reciprocal external amendment relationships and rejects an `amends` target whose status is `superseded`; it never infers relationships from prose.
- Bound every decision by concern, population, applicability condition, exclusions, and reserved authority.
- Keep the title, question, options, and outcome at the same breadth; restate the boundary in the outcome.
- Out of scope is not an exception, and optional sections must not create additional governance.
- Record a partial change with the amendment vocabulary, not supersession: reciprocal `project.amends` / `project.amended_by` lists plus a blockquote note after the title. An amended ADR keeps its `status`; accepted Decision Outcome prose is never rewritten in place.
- Markdown Frontmatter is a companion, not a dependency.

Enable `adr@1.6`, preview with `project-standards reconcile`, and apply only after reviewing the plan. See the [current adoption guide](adopt.md) for the complete procedure.
