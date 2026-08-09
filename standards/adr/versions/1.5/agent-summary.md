# ADR 1.5 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.5`; ADR contract option: `1.0`.
- Managed output: create-only `docs/adr/adr.template.md`; existing consumer scaffolds are never overwritten.
- Optional `require_sections` validates only the three MADR-required level-2 headings.
- Before drafting, identify the governed concern, governed population, applicability condition, exclusions, and reserved authority.
- Keep the title, problem question, options, and outcome at the same breadth; restate the operative boundary in Decision Outcome.
- Out of scope is not an exception. Do not require a waiver or superseding ADR for a case the ADR never governed.
- Consequences, Confirmation, examples, and More Information must not introduce additional governance.
- Use universal terms such as “all,” “default,” or “the repository” only with an explicit population and applicability condition.
- Split independently reversible concerns into separate ADRs.
- Supersession replaces a whole governed decision; amendment narrows, restates, or replaces part of one and leaves the rest in force.
- An amended ADR keeps its `status`. Never set `superseded_by` or `status: superseded` for an amendment.
- Record an external amendment reciprocally: `project.amends` on the amending record, `project.amended_by` on the amended one, both changed together. Both lists are optional and default to empty.
- A self-amendment—a post-acceptance change from a review finding, with no later ADR—leaves both lists empty; its note carries the relationship.
- Put the amendment note on the amended record between the title and `## Context and Problem Statement`. Several notes share one blockquote, oldest first, separated by a bare `>` line, never by a blank line.
- Long amendments keep a lead sentence in the note ending `See [Amendments](#amendments).` and move the rest to an optional `### Amendments` subsection under `## Decision Outcome`.
- Never rewrite accepted Decision Outcome prose in place; state the change as an amendment instead.
- An amendment that widens the concern, population, or applicability is a new ADR. One that leaves nothing in force is a supersession.
- Re-run the decision-boundary review on the amended record before publishing; four checks apply in full and two apply conditionally.
- Markdown Frontmatter is a companion only; enable it separately for metadata validation.
- Legacy `markdown.adr.version` maps to `contract_version`; no Catalog 5 output contains a `.project-standards.yml` fragment.
