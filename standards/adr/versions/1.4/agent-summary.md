# ADR 1.4 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.4`; ADR contract option: `1.0`.
- Managed output: create-only `docs/adr/adr.template.md`; existing consumer scaffolds are never overwritten.
- Optional `require_sections` validates only the three MADR-required level-2 headings.
- Before drafting, identify the governed concern, governed population, applicability condition, exclusions, and reserved authority.
- Keep the title, problem question, options, and outcome at the same breadth; restate the operative boundary in Decision Outcome.
- Out of scope is not an exception. Do not require a waiver or superseding ADR for a case the ADR never governed.
- Consequences, Confirmation, examples, and More Information must not introduce additional governance.
- Use universal terms such as “all,” “default,” or “the repository” only with an explicit population and applicability condition.
- Split independently reversible concerns into separate ADRs.
- Markdown Frontmatter is a companion only; enable it separately for metadata validation.
- Legacy `markdown.adr.version` maps to `contract_version`; no Catalog 5 output contains a `.project-standards.yml` fragment.
