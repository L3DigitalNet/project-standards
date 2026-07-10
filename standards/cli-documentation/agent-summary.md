# CLI Documentation Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

Lifecycle: active. Adoption: `copy-adopt`.

## Use this summary when

Document or review a user-facing command-line interface and its drift checks.

## Core rules

- Coordinate four possible artifacts: parser-generated `--help`, a canonical Markdown usage reference, a generated man page, and an onboarding-focused README. The selected Script, Packaged, or Packaged-deep profile determines which are required.
- Keep `--help` concise. Put exhaustive behavior, options, exit codes, environment variables, files, caveats, and task-first examples in the usage reference. Keep the README focused on installation, quick start, common tasks, and the reference link.
- For packaged CLIs, document the installed `[project.scripts]` command name and every leaf command. Use the required man-style section order and one consistent synopsis notation.
- Each option entry records exact spelling, value syntax, meaning, applicable default or allowed values, interactions, scope, safety impact, and version status.
- Examples are copy-pasteable, task-first, safe by default, and use obviously fake credentials and infrastructure identifiers.
- Treat command names, option spellings, semantic defaults, exit codes, environment variables, file locations, and output formats as versioned interface surface.

## Commands and artifacts

```bash
project-standards adopt cli-documentation
```

The copy-adopt bundle provides a `docs/usage.md` scaffold and `cli-docs-check` workflow. The copied workflow exercises a freshly installed command and normalizes color and terminal width; add the required inventory, option, exit-code, generated-man-page, and safe-example checks as the surface grows. Generate deep-profile per-command pages and committed man pages; do not maintain them separately by hand.

## Boundaries and companions

This standard owns user-facing CLI documentation, not implementation internals or APIs. Markdown Tooling owns formatting, Python Tooling and Python Coding own the executable and its gate, Project Specification owns pre-implementation requirements, and Markdown Frontmatter owns managed-document metadata.

## Canonical resources

Use the [standard](README.md), [adoption guide](adopt.md), [templates](templates/), [example](examples/usage.example.md), and [research notes](resources/research-notes.md).
