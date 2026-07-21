# Adopt CLI Documentation 1.3

Use this package to create a consumer-owned CLI usage reference and optionally generate and verify a CI drift workflow.

The common V5 control-plane lifecycle—initialization, preview, apply, disable, removal, and catalog updates—is documented by `project-standards`. This guide covers CLI-documentation-specific choices only.

## Select a profile

The neutral default supports a script without selecting a language or CI host:

```toml
[standards.cli-documentation]
enabled = true
version = "1.3"

[standards.cli-documentation.config]
contract_version = "1.0"
profile = "script"
usage_ownership = "managed"
command_name = null
workflow_path = null
ci = { enabled = false }
```

For an installed Python command with CI generation, use:

```toml
[standards.cli-documentation.config]
contract_version = "1.0"
profile = "packaged"
usage_ownership = "managed"
command_name = "toolname"
workflow_path = ".github/workflows/cli-docs-check.yml"
ci = { enabled = true, runner = "ubuntu-latest", language = "python", setup = "uv" }
```

Use `language = "generic"` and `setup = "none"` for a command that the runner already provides. Runner, language, setup, and `workflow_path` are invalid while CI is disabled. `command_name` is inert documentation text. It cannot select provider code, an executable, a shell command, a path, or workflow run bytes.

The rendered workflow takes its executable name from the reviewed, consumer-owned GitHub repository variable `CLI_DOCS_COMMAND`. It validates that value as a command basename before use. The Python profile builds a wheel, creates a throwaway virtual environment, installs the wheel, and invokes the installed wrapper from that environment. The generic profile resolves an already-installed wrapper from the same repository variable.

## Preserve consumer documentation

With `usage_ownership = "managed"`, reconciliation creates `docs/usage.md` from the package template only when the path is absent. Edit it to match the executable CLI. Subsequent reconciliation preserves those bytes. During V4 migration, select `usage_ownership = "consumer-owned"` to preserve a customized legacy usage reference and leave the path outside reconciliation and lock state.

The workflow renderer returns content but does not claim a GitHub workflow path. After saving the enabled package configuration above, bootstrap the consumer-owned workflow before reconciliation resolves referenced inputs:

```bash
set -euo pipefail
workflow_path=.github/workflows/cli-docs-check.yml
scratch=$(mktemp "${TMPDIR:-/tmp}/cli-docs-check.XXXXXX")
trap 'rm -f -- "$scratch"' EXIT
project-standards render cli-documentation render-workflow --repo . >"$scratch"
less "$scratch"
actionlint "$scratch"
mkdir -p "$(dirname "$workflow_path")"
(set -o noclobber; cat -- "$scratch" >"$workflow_path")
project-standards reconcile --check
project-standards reconcile --apply
```

`render` has no destination or output-path write path; the no-clobber shell redirection is the explicit consumer-owned publication step. `set -e` stops before publication when rendering or validation fails, and the trap removes the scratch file. If `workflow_path` already exists, `noclobber` fails without truncating or overwriting it. Retain ownership of future edits.

Installed provider resources are integrity-verified and providers are forbidden to write repository files. A detected provider mutation is an integrity incident and refusal, not automatic rollback; inspect and restore affected paths before continuing. Reconciliation locks the published file only as a typed consumer-owned referenced input, then verification compares its immutable bytes with the selected rendering. It also accepts the exact legacy workflow only at `.github/workflows/cli-docs-check.yml` with the exact migrated V4 package configuration. Disabling or removing this package drops the reference and never removes the consumer workflow.

A customized legacy workflow migrates by declaring `workflow_ownership: "consumer-owned"` under `cli_documentation:` in `.project-standards.yml` before previewing. Migration then preserves the file exactly, leaves CI disabled, and records no referenced input, so the consumer keeps full ownership of the workflow; re-enabling managed CI later is an explicit configuration decision. The default `workflow_ownership = "referenced"` keeps the recognized workflow locked as a verified referenced input.

This package declares no companions. CLI Documentation, Python Tooling, Markdown Tooling, and every other package remain independently selectable; enabling this package never enables another standard.

Verify the selected state through the generic lifecycle:

```bash
project-standards reconcile --check
project-standards validate
```

Legacy `cli_documentation.version` maps to `contract_version`. Exact legacy usage and workflow files are recognized and preserved. An edited usage document blocks automatic transfer unless the legacy configuration explicitly selects `usage_ownership: "consumer-owned"`; that choice preserves the file without claiming it. No V2 output prints or installs a `.project-standards.yml` fragment.

## Author and review

Replace every placeholder in the create-only usage scaffold and cover every public leaf command. Review the result against the canonical contract:

- `NAME` and `SYNOPSIS` use the installed command name, not a module path.
- Synopsis notation is consistent, and parser-owned `--help` stays concise.
- Every option records applicable defaults, constraints, interactions, and configuration or environment precedence.
- Exit status, environment, files, safety effects, and user tasks are complete.
- Examples are copyable and favor dry-run or explicit-output forms for stateful operations.
- CI smoke tests invoke the installed wrapper and normalize color and terminal width when the selected runtime supports those controls.
- README and help surfaces point to the canonical usage reference instead of duplicating its complete option catalog.

The [single-file README template](templates/readme-single-file.md) is a manual reference for the Script profile. The [worked example](examples/usage.example.md) shows the full section and option-entry shape.

## Troubleshooting

| Finding | Resolution |
| --- | --- |
| Referenced workflow is missing | Render to scratch, review it, and publish with the documented no-clobber step before reconciliation. |
| Rendered workflow differs | Reconcile the consumer-owned edit with the selected package options; the provider never overwrites it. |
| Command name is unsafe or unavailable | Use a command basename and configure the reviewed `CLI_DOCS_COMMAND` repository variable. |
| Provider mutation is detected | Treat it as an integrity incident, restore the repository, and do not retry until the package is verified. |
