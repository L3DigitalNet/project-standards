# Adopt Markdown Tooling 1.12

This package manages the Markdown Tooling configuration, caller workflows, and bounded shared-container contributions. Use the generic lifecycle commands documented in the project-standards CLI usage reference at `docs/usage.md` to initialize a repository, enable this package, preview or apply reconciliation, update its selected version, and disable it.

## Package options

Configure these fields under the `markdown-tooling` package selection:

- `contract_version`: the independent Markdown Tooling contract selector; package 1.12 supports `1.1`.
- `workflow_mode`: `caller` uses reusable workflows pinned to `v5`; `self-hosted` installs immutable in-repository jobs without a remote standards dependency. The default is `caller`.
- `lint` and `format`: enable markdownlint structure checks and Prettier physical-format checks independently.
- `lint_generated_exclusions`: `true` (the default) appends `!.pytest_cache/**`, `!.ruff_cache/**`, `!.venv/**`, and `!node_modules/**` to the rendered lint scope, matching the Git-ignored trees the format workflow already skips through `--ignore-path .gitignore`. Set it to `false` to render the exact 1.9 lint scope when the repository must lint one of those directories.
- `ci.lint_caller` and `ci.format_caller`: add automatic push and pull-request triggers to the corresponding managed caller. A disabled caller remains installed with only `workflow_dispatch`, so toggling enforcement does not churn ownership.
- `lint_workflow_ownership` and `format_workflow_ownership`: `managed` (the default) lets the package render, verify, and lock the corresponding caller workflow; `consumer-owned` leaves that path outside reconciliation, verification, and lock state so a customized caller stays with the consumer.
- `markdownlint_config_ownership`: `managed` (the default) lets the package own `.markdownlint.json`; `consumer-owned` preserves a customized legacy config and keeps that path outside reconciliation, verification, and lock state.
- `markdown_globs`: Markdown included by the lint caller and described in the bounded agent guidance.
- `config_globs`: JSON, JSONC, and YAML scope passed with `markdown_globs` to the managed formatter caller and described in bounded agent guidance.
- `exclusions`: typed `{glob, applies_to, reason}` records. `applies_to` is `lint`, `format`, or `both`; every exception is reviewable instead of being an untyped ignore string.

When `lint` or `format` is false, its matching CI caller option must also be false. Disabling both caller options produces manual-only workflows; it does not remove the managed caller files.

The managed instruction blocks display selected globs as inline code. Because the schema excludes backticks from glob values, this preserves wildcard characters literally without creating ambiguous Markdown emphasis.

## Managed outputs

The package exclusively manages these whole files:

- `.markdownlint.json`
- `.prettierrc.json`
- `.github/workflows/lint-markdown.yml`
- `.github/workflows/format.yml`

It composes only declared semantic units in these consumer containers:

- EditorConfig global, Markdown, and YAML properties in `.editorconfig`
- the Prettier and markdownlint recommendation entries in `.vscode/extensions.json`
- each declared formatter setting under the Markdown, JSON, JSONC, and YAML objects in `.vscode/settings.json`
- one `markdown-tooling` managed block in each of `AGENTS.md` and `CLAUDE.md`

Unrelated properties, recommendations, settings, and instruction text remain consumer-owned. A later package may share an identical contribution through the same normalized shared identity without depending on this package.

## Boundaries and companions

Prettier is the sole physical-formatting authority for supported structured text. markdownlint owns Markdown structure and diagnostics; it does not fix on save. This package does not own Python formatting, frontmatter schemas, document IDs, arbitrary VS Code settings, or whole instruction files.

Markdown Frontmatter is a companion only. Either package can be enabled independently, and this package has no hidden dependency on it.

## Migration

The automatic V4 migration maps only `markdown_tooling.version` into `contract_version` and recognizes exact released bytes for the two configs, two callers, legacy shared EditorConfig, and legacy VS Code recommendations. Exact exclusive files transfer to managed ownership; exact shared containers are preserved while their declared units are adopted semantically.

Modified legacy root configuration is reported as a migration conflict and preserved. Resolve the local intent before retrying migration; the provider never writes the repository, accesses the network, or emits an active `.project-standards.yml` fragment.

A `.markdownlint.json` that is byte-for-byte the shipped config re-serialized with literal (non-escaped) UTF-8 punctuation is accepted as known legacy content and migrates to managed ownership of the escaped bytes; it is not treated as a modified config.

A `.markdownlint.json` that already equals the rule set this package currently ships is likewise accepted as known legacy content. Package 1.11 added the shipped bytes' own digest to the `legacy-markdownlint-config` signature, so a consumer whose local deviation upstream has since adopted as the default no longer has to regress the file to a superseded rule value to get past migration.

Package 1.12 updates both managed self-hosted workflow resources to the exact root workflow bytes. Their external GitHub Actions references use full commit SHAs; the trailing major-version comments aid review but do not affect the immutable pin.

Generic plan, apply, update, and disable behavior is delegated to the unified control plane. The central `.standards/lock.toml` records ownership; this package creates no package-local lock.

## Verify and troubleshoot

```bash
project-standards reconcile --check
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Run a local tool only when its matching `lint` or `format` option is `true`:

- For markdownlint, pass every selected `markdown_globs` value, then the generated-directory exclusions unless `lint_generated_exclusions` is `false`, then each exclusion whose `applies_to` value is `lint` or `both`, every one prefixed with `!`. With the defaults that is `npx markdownlint-cli2 "**/*.md" "!.pytest_cache/**" "!.ruff_cache/**" "!.venv/**" "!node_modules/**"`. Order matters: `markdownlint-cli2` resolves globs in sequence, so the negations have to trail the positive globs.
- For Prettier, pass every selected `markdown_globs` and `config_globs` value and supply each exclusion whose `applies_to` value is `format` or `both` through an additional `--ignore-path` file.

These local commands require the corresponding packages to be installed; the managed reusable lint caller supplies its own action runtime. With `npx --no-install`, install the repository's lockfile-defined Node dependencies first, normally with `npm ci`. The reconciled workflow is the canonical option-aware CI verification.

Neither local invocation honors `.git/info/exclude`, and the markdownlint invocation does not honor `.gitignore` either. `markdownlint-cli2` reads Git ignore files only when a `.markdownlint-cli2.*` runner config sets `gitignore: true`; this package ships the rule set `.markdownlint.json`, not a runner config, and the option has no CLI or action equivalent, so the bare globs above select ignored trees. The Prettier invocation differs only because the managed format caller passes `--ignore-path .gitignore`, which covers tracked patterns and nothing else. Cover anything excluded only in `.git/info/exclude` by adding it as an explicit negative glob to the local invocation, or as a typed `exclusions` record when it belongs in the reconciled scope — neither `lint_generated_exclusions` nor any Git ignore file reaches it.

Normal verification never asks either tool to rewrite files; the autofix hazards below are why. When a bounded exceptional region needs a structural-rule suppression, place paired block `markdownlint-disable` and `markdownlint-enable` directives immediately outside the region and name only the necessary rules. Do not use a one-line suppression that Prettier can detach from its target.

The standard reference's optional recovery recipe is the only documented markdownlint autofix path. It requires a clean starting diff, review of the resulting diff, and mandatory follow-up Prettier and markdownlint checks.

| Finding | Resolution |
| --- | --- |
| A disabled tool still has its CI caller enabled | Disable the matching caller option or enable the tool. |
| Lint reports findings in a generated directory | Confirm `lint_generated_exclusions` is `true` and reconcile; the directory is covered only when it is one of the four listed above. Add any other generated tree as a typed `exclusions` entry with `applies_to = "lint"` or `"both"`. |
| A generated directory must be linted | Set `lint_generated_exclusions = false` and reconcile. In `self-hosted` mode the negations are baked into the installed workflow, so take `lint_workflow_ownership = "consumer-owned"` instead. |
| Shared container contribution conflicts | Preserve unrelated content and reconcile only the declared property, recommendation, or managed block. |
| Managed config or workflow drift | Restore the locked bytes or change package options and reconcile deliberately. |
| V4 artifact is modified | A modified `.editorconfig` or `.vscode/extensions.json` is preserved automatically with a `CP-MIGRATION-BOUNDED-TAKEOVER` warning; a modified caller workflow is preserved by declaring `lint_workflow_ownership` or `format_workflow_ownership` as `"consumer-owned"` in the legacy configuration before migrating; a modified `.markdownlint.json` is preserved with `markdownlint_config_ownership = "consumer-owned"`; other modified exclusive configs block until their known content is restored. |

### Autofix hazards: markdownlint `--fix` and Prettier `--write`

Treat both autofix paths as manual, reviewed operations, not part of the routine check. `markdownlint --fix` can corrupt content outside its declared scope, which is why the recovery recipe above is the only documented path to it. The same corruption class is independently reachable through `prettier --write`: an upstream Prettier Markdown-printer bug can rewrite an intraword literal underscore (for example `America/New_York`) into a literal asterisk, and can edit content **inside a code span**, where bytes must be inviolable. This is most likely to surprise a consumer on the first `prettier --write` run after newly enabling the format caller (`format = true`, `ci.format_caller = true`), because `prettier --check` failures do not explain themselves and the natural next step is to run `--write` and commit the result.

Before accepting any `prettier --write` or `markdownlint --fix` output, diff it and confirm no literal character inside prose or a code span changed meaning. That diff review is the control. When a diff shows an unpaired underscore rewritten as an asterisk, or a change inside backticks, back the run out and escape the underscore in the prose occurrence (`America/New\_York`). Do not rely on backticking the identifier: upstream [prettier#7695](https://github.com/prettier/prettier/issues/7695) is a prose underscore pairing with an underscore _inside_ a code span, so a code span is not out of reach of the bug.
