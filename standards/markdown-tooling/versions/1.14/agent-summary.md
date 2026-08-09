# Markdown Tooling 1.14: Agent Summary

The canonical [standard](README.md) is authoritative. Use the [adoption guide](adopt.md) for package-specific options, outputs, migration, and ownership; use `docs/usage.md` from the project-standards distribution for generic lifecycle commands.

Prettier is the sole physical-formatting authority for Markdown and supported JSON, JSONC, and YAML. markdownlint owns Markdown structure and diagnostics. Never add an overlapping formatter or structural linter.

The package manages `.prettierrc.json`, `.markdownlint.json`, and distinct lint/format caller workflows. Each caller can be relinquished with its `lint_workflow_ownership` or `format_workflow_ownership` option; a customized legacy `.markdownlint.json` can be preserved with `markdownlint_config_ownership = "consumer-owned"`, which also removes that path from package verification and lock state. It contributes only bounded EditorConfig properties, VS Code settings and extension entries, and managed Markdown instruction blocks. Preserve all unrelated consumer content. The self-hosted workflow resources use full-SHA GitHub Action references, with major tags retained only as review comments.

`lint` and `format` select checks independently. CI caller options select automatic triggers; a disabled caller remains present as a manual `workflow_dispatch` workflow and passes a false enforcement flag so the reusable job skips. Typed exclusions name their tool scope and rationale. The format caller passes selected Markdown/config globs and exclusions to the reusable workflow, which keeps `.gitignore`, `.prettierignore`, and configured exclusions as separate ignore sources without treating config as shell source.

`runner_labels` selects the runner both managed callers request. It renders a `runner-labels` JSON-array string into the caller's `with:` block and is omitted entirely when empty, which is the default and the byte-identical render. The input is reachable only over `workflow_call`; a direct `push` or `pull_request` run leaves `inputs` empty and falls through to the GitHub-hosted runner.

The lint caller passes bare globs instead, and `markdownlint-cli2` traverses dot directories and `node_modules`. `lint_generated_exclusions` (default `true`) therefore appends `!.pytest_cache/**`, `!.ruff_cache/**`, `!.venv/**`, and `!node_modules/**` after the positive globs, so lint and format select the same repository content in CI. Set the option to `false` only when a generated tree must be linted.

Run the enabled checks before completion, bounded to the selected globs and routed through `git ls-files`. Never use a bare `.` or a bare recursive glob: `prettier --check .` reaches undeclared languages and Git-excluded scratch, where an invalid fixture makes the check exit `2`, and `markdownlint-cli2 "**/*.md"` descends into any independent Git repository checked out below this one. Git is what honors nested `.gitignore` files, `.git/info/exclude`, and the child-repository boundary, none of which either tool reads by itself. `:(glob)` is required for `**/` to mean "zero or more leading directories"; declared exclusions travel as `:(glob,exclude)` pathspecs; `xargs -r` keeps an empty selection from being an error; and the markdownlint form needs `--no-globs` plus the `:` literal-path prefix, or a consumer runner config re-widens the run and a `#`-leading filename is silently dropped.

```bash
git ls-files -z -- ':(glob)**/*.md' ':(glob)**/*.json' ':(glob)**/*.jsonc' ':(glob)**/*.yml' ':(glob)**/*.yaml' | xargs -0 -r npx prettier --check --
git ls-files -z -- ':(glob)**/*.md' ':(glob,exclude).pytest_cache/**' ':(glob,exclude).ruff_cache/**' ':(glob,exclude).venv/**' ':(glob,exclude)node_modules/**' | sed -z 's|^|:|' | xargs -0 -r npx markdownlint-cli2 --no-globs
```

The managed instruction blocks render both that command and a no-Git fallback from the repository's own selected globs.

Markdown Frontmatter is a companion, not a dependency. This package never validates frontmatter semantics or document IDs.
