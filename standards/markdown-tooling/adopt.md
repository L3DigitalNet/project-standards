# Adopt the Markdown Tooling Standard

The current consumer package is [`markdown-tooling@1.13`](versions/1.13/adopt.md). Use it for markdownlint and Prettier configuration, managed lint/format workflows, and bounded EditorConfig, VS Code, and agent-instruction contributions.

## Configure and reconcile

```bash
project-standards standards enable markdown-tooling --version 1.13
project-standards reconcile
project-standards reconcile --apply
```

Options under `[standards.markdown-tooling.config]` select the independent contract, lint/format behavior, CI triggers, Markdown/config globs, typed exclusions, `workflow_mode`, and the `lint_workflow_ownership` and `format_workflow_ownership` decisions. Use `caller` for reusable `@v5` workflows or `self-hosted` for immutable in-repository jobs. The default is `caller`. Each caller is managed by default; set its matching ownership option to `"consumer-owned"` to leave that caller outside reconciliation, verification, and lock state. The package owns its two configs and only the workflow files that remain managed, plus its declared semantic units in shared containers.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Migration maps `markdown_tooling.version`, transfers only exact exclusive files, and adopts exact shared units semantically. Modified root configuration is preserved and reported as a conflict; resolve local intent before retrying.

## Verify and troubleshoot

```bash
project-standards reconcile --check
```

Run a local tool only when its matching `lint` or `format` option is `true`. For markdownlint, pass every selected `markdown_globs` value followed by each `lint` or `both` exclusion as a negative glob. For Prettier, pass every selected Markdown and config glob and supply each `format` or `both` exclusion through an additional ignore file. These local commands require the corresponding packages to be installed; the managed reusable lint caller supplies its own action runtime. The reconciled workflow is the canonical option-aware CI verification.

Local verification does not honor `.git/info/exclude`, and a bare markdownlint invocation does not honor `.gitignore` either. `markdownlint-cli2` reads Git ignore files only when a `.markdownlint-cli2.*` runner config sets `gitignore: true`, which this package does not ship and which has no CLI or action equivalent, so bare CLI globs select ignored trees. Prettier differs: the managed format caller passes `--ignore-path .gitignore`, so tracked ignore patterns do apply there. Neither tool sees `.git/info/exclude` at all. Add anything that must stay out of a local run as an explicit negative glob to the invocation itself — no Git ignore file reliably covers it.

Conflicting shared properties, invalid exclusion records, disabled-tool/enabled-CI combinations, or modified managed files block apply. Do not replace consumer-owned container content to resolve a package unit. See the [version-specific guide](versions/1.13/adopt.md) for exact options, managed outputs, companions, migration, and failure handling.

### Autofix hazards: markdownlint `--fix` and Prettier `--write`

Normal verification never asks either tool to rewrite files; treat both autofix paths as manual, reviewed operations, not part of the routine check. `markdownlint --fix` can corrupt content outside its declared scope. The same corruption class is independently reachable through `prettier --write`: an upstream Prettier Markdown-printer bug can rewrite an intraword literal underscore (for example `America/New_York`) into a literal asterisk, and can edit content **inside a code span**, where bytes must be inviolable. This is most likely to surprise a consumer on the first `prettier --write` run after newly enabling the format caller (`format = true`, `ci.format_caller = true`), because `prettier --check` failures do not explain themselves and the natural next step is to run `--write` and commit the result.

Before accepting any `prettier --write` or `markdownlint --fix` output, diff it and confirm no literal character inside prose or a code span changed meaning. That diff review is the control. When a diff shows an unpaired underscore rewritten as an asterisk, or a change inside backticks, back the run out and escape the underscore in the prose occurrence (`America/New\_York`). Do not rely on backticking the identifier: upstream [prettier#7695](https://github.com/prettier/prettier/issues/7695) is a prose underscore pairing with an underscore _inside_ a code span, so a code span is not out of reach of the bug.
