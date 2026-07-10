# Architecture Decision Record Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

## Use this summary when

Create, review, index, or validate a durable record for a significant, costly-to-reverse architecture decision.

## Core rules

- Store ADRs in `docs/adr/` and list them in that directory's `README.md` index.
- Use `adr-NNNN-short-title.md` for the filename and `adr-NNNN-repo-name-short-title` for the globally unique frontmatter `id`. Sequence numbers are zero-padded, repository-scoped, and never reused.
- Set `doc_type: 'adr'` and map MADR lifecycle states to canonical frontmatter: proposed to `review`, accepted to `active`, rejected to `archived`, and replaced decisions to `superseded`.
- Include the three exact level-2 MADR sections: `Context and Problem Statement`, `Considered Options`, and `Decision Outcome`. Section enforcement is opt-in through `markdown.adr.require_sections: true`.
- When one ADR replaces another, update both in the same change: the new record names the old ID in `supersedes`; the old record sets `superseded_by` and `status: 'superseded'`.

## Commands and artifacts

Adopt the standard after Markdown Frontmatter:

```bash
project-standards adopt adr
project-standards validate --config .project-standards.yml
```

The adoption command writes `docs/adr/adr.template.md` and reports configuration to merge manually. Choose a full, minimal, bare, or bare-minimal scaffold from [`templates/`](templates/); see the [worked example](examples/adr.example.md).

## Boundaries and companions

ADR is independently adoptable. Markdown Frontmatter is its companion metadata standard and must be adopted when ADR documents are managed; this relation does not make an undeclared graph dependency. Routine, easily reversed decisions belong in a smaller decision note, not an ADR.

## Canonical resources

Read the [standard](README.md) for rationale and exact mappings, and [adoption guide](adopt.md) for setup and compatibility rules.
