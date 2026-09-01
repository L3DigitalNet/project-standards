# Adopt Markdown Tooling 1.16

This package manages the Markdown Tooling configuration, caller workflows, and bounded shared-container contributions. Use the generic lifecycle commands documented in the project-standards CLI usage reference at `docs/usage.md` to initialize a repository, enable this package, preview or apply reconciliation, update its selected version, and disable it.

## Package options

Configure these fields under the `markdown-tooling` package selection:

- `contract_version`: the independent Markdown Tooling contract selector; package 1.16 supports `1.1`.
- `workflow_mode`: `caller` uses reusable workflows pinned to `v5`; `self-hosted` installs immutable in-repository jobs without a remote standards dependency. The default is `caller`.
- `lint` and `format`: enable markdownlint structure checks and Prettier physical-format checks independently.
- `lint_generated_exclusions`: `true` (the default) appends `!.pytest_cache/**`, `!.ruff_cache/**`, `!.venv/**`, and `!node_modules/**` to the rendered lint scope, matching the Git-ignored trees the format workflow already skips through `--ignore-path .gitignore`. Set it to `false` to render the exact 1.9 lint scope when the repository must lint one of those directories.
- `ci.lint_caller` and `ci.format_caller`: add automatic push and pull-request triggers to the corresponding managed caller. A disabled caller remains installed with only `workflow_dispatch`, so toggling enforcement does not churn ownership.
- `lint_workflow_ownership` and `format_workflow_ownership`: `managed` (the default) lets the package render, verify, and lock the corresponding caller workflow; `consumer-owned` leaves that path outside reconciliation, verification, and lock state so a customized caller stays with the consumer.
- `markdownlint_config_ownership`: `managed` (the default) lets the package own `.markdownlint.json`; `consumer-owned` preserves a customized legacy config and keeps that path outside reconciliation, verification, and lock state.
- `markdown_globs`: Markdown included by the lint caller and described in the bounded agent guidance.
- `config_globs`: JSON, JSONC, and YAML scope passed with `markdown_globs` to the managed formatter caller and described in bounded agent guidance.
- `exclusions`: typed `{glob, applies_to, reason}` records. `applies_to` is `lint`, `format`, or `both`; every exception is reviewable instead of being an untyped ignore string.
- `runner_labels`: the runner labels both managed callers pass to the reusable workflows, for example `["self-hosted", "linux", "x64"]`. The default is empty, which omits the input entirely and leaves the GitHub-hosted runner in use. Labels are limited to letters, digits, `.`, `_`, and `-`. This option applies to `caller` mode; in `self-hosted` mode the installed workflows expose `runner-labels` as their own `workflow_call` input instead.

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

Package 1.12 updated both managed self-hosted workflow resources to the exact root workflow bytes. Their external GitHub Actions references use full commit SHAs; the trailing major-version comments aid review but do not affect the immutable pin.

Package 1.13 bounds both documented local checks to the declared corpus and renders them into the two managed instruction blocks, so updating to it rewrites the `markdown-tooling` block in `AGENTS.md` and `CLAUDE.md`. No option or managed config changes, and the corpus is still exactly `markdown_globs` plus `config_globs` for Prettier and `markdown_globs` plus the lint exclusions for markdownlint.

Package 1.13 also updates both self-hosted workflow resources. Each gains an optional `runner-labels` input — a JSON array selecting a caller-owned runner, empty by default so the GitHub-hosted runner stays in use — the formatter job moves to `actions/setup-node` v7.0.0, and its pinned Prettier advances to `3.9.6`. A repository in `caller` mode is unaffected; a `self-hosted` repository reconciles the two workflow files.

Package 1.14 adds the `runner_labels` option to `caller` mode. Both managed callers gain a `runner-labels` entry in their `with:` block whenever the option is non-empty, and omit it entirely otherwise, so a repository that sets nothing renders byte-for-byte the 1.13 callers and reconciliation reports no change. Opting in rewrites `.github/workflows/lint-markdown.yml` and `.github/workflows/format.yml`. No managed config, contribution target, or self-hosted resource changes.

Package 1.15 emits a non-fatal reconciliation warning when non-empty `runner_labels` cannot reach an enabled caller. For a consumer-owned caller, pass `runner-labels` from that caller or restore its ownership option to `managed`. In direct `self-hosted` mode, move to a managed caller path or keep the workflow consumer-owned and pin `runs-on` directly. Empty labels, managed callers, and disabled tools produce no reachability warning; existing managed-byte drift remains an error.

Package 1.16 changes two managed surfaces. The documented local Prettier check now lists the corpus with `git ls-files -s` and drops index mode `120000`, so tracked symlinks no longer make the check exit non-zero on a clean tree (issue #209); updating rewrites the `markdown-tooling` block in `AGENTS.md` and `CLAUDE.md`. The self-hosted lint workflow advances `DavidAnson/markdownlint-cli2-action` to `v24.2.0` (`21c1be1b93ad9ed58fa840aacc3f279cde2a72ff`), so a `self-hosted` repository reconciles `.github/workflows/lint-markdown.yml`. No option, managed config, or contribution target changes, and the set of files Prettier reads is unchanged — a refused symlink was never checked.

A `runner-labels` value only reaches the job through `workflow_call`. Both self-hosted workflows also trigger directly on `push` and `pull_request`, and on those events `inputs` is empty, so the expression falls through to `ubuntu-latest` and the job runs on the GitHub-hosted runner. A repository that must keep every run off hosted minutes therefore cannot rely on the input alone; take `lint_workflow_ownership = "consumer-owned"` or `format_workflow_ownership = "consumer-owned"` and pin `runs-on` directly. Runner groups are allocated from the caller's context, so a public repository — which the private runner group rejects — keeps the hosted runner whatever labels a caller passes.

Generic plan, apply, update, and disable behavior is delegated to the unified control plane. The central `.standards/lock.toml` records ownership; this package creates no package-local lock.

## Verify and troubleshoot

```bash
project-standards reconcile --check
git ls-files -s -z -- ':(glob)**/*.md' ':(glob)**/*.json' ':(glob)**/*.jsonc' ':(glob)**/*.yml' ':(glob)**/*.yaml' | sed -zn '/^120000 /!s/^[^\t]*\t//p' | xargs -0 -r npx prettier --check --
git ls-files -z -- ':(glob)**/*.md' ':(glob,exclude).pytest_cache/**' ':(glob,exclude).ruff_cache/**' ':(glob,exclude).venv/**' ':(glob,exclude)node_modules/**' | sed -z 's|^|:|' | xargs -0 -r npx markdownlint-cli2 --no-globs
```

Run a local tool only when its matching `lint` or `format` option is `true`. Both commands select Git-tracked files rather than expanding globs themselves, and the managed instruction blocks render both from the repository's own selected globs, so that block is the authority for a specific repository:

- For markdownlint, pass every selected `markdown_globs` value as a `:(glob)` pathspec, then the generated-directory exclusions unless `lint_generated_exclusions` is `false`, then each exclusion whose `applies_to` value is `lint` or `both`, every one as a `:(glob,exclude)` pathspec. Git applies its `exclude` magic after the positive pathspecs regardless of argument order, so the ordering the caller workflow depends on is preserved rather than relied upon. Three parts of the invocation are load-bearing against `markdownlint-cli2` 0.23.2: `--no-globs` is mandatory, because a consumer's `.markdownlint-cli2.*` runner config would otherwise contribute its own `globs` and re-widen the run; the `sed` step prefixes each path with `:`, which marks it a literal file path, without which a name beginning with `#` or `!` is parsed as a negation and silently dropped; and a negation supplied as a trailing CLI glob does **not** filter a literal path, which is why the exclusions travel through Git instead.
- For Prettier, select the Git-tracked files matching every selected `markdown_globs` and `config_globs` value, then subtract each exclusion whose `applies_to` value is `format` or `both` as a `:(glob,exclude)` pathspec, exactly as the command above does. The corpus is listed with `git ls-files -s` so index mode `120000` can be dropped: a path handed to Prettier on the command line is an explicitly specified pattern, and Prettier refuses a symbolic link with a non-zero status while still reporting every real file correctly formatted, so a repository that tracks symlinked Markdown or config would fail this check on a clean tree. Removing them narrows nothing, because a refused path was never checked. The Git-routed form is the only one that can apply those exclusions, because Prettier's CLI has no negative pattern. Without Git, use `npx prettier --check --no-error-on-unmatched-pattern -- '**/*.md' '**/*.json' '**/*.jsonc' '**/*.yml' '**/*.yaml'` and supply the same exclusions through an additional `--ignore-path` file; the file must live inside the repository, because Prettier anchors its patterns to the file's own directory. A repository with no declared format exclusions can use either form interchangeably.

`:(glob)` pathspec magic is required in both commands. Under Git's default pathspec magic, `**/*.md` skips root-level files and `nested/**/*.md` matches nothing at all; `:(glob)` selects wildmatch, giving `**/` the "zero or more leading directories" reading both tools give the configured glob.

Never run either tool over a bare `.` or a bare recursive glob. Prettier over `.` reaches every language it supports rather than the declared corpus, and it reaches Git-excluded scratch, where an intentionally invalid test artifact turns a formatting check into a hard error. `markdownlint-cli2 "**/*.md"` descends into every independent Git repository checked out beneath the working directory, so a workspace parent lints thousands of child-owned documents that are not part of its adoption.

If you hand-narrow the Prettier globs rather than using a rendered command, keep `--no-error-on-unmatched-pattern`. Prettier exits `2` — a hard error, printed alongside its success line — when _any_ supplied pattern matches no file, and the shipped `config_globs` default includes `**/*.jsonc`, which most repositories have no file for. The default is deliberately unchanged: the rendered commands already tolerate an empty match, the Git-routed one because an unmatched pathspec is not an error and `xargs -r` skips an empty set, the fallback because of that flag.

`xargs` maps any child exit status between `1` and `125` onto `123`, so both Git-routed forms report clean as `0` and everything else as `123` rather than reproducing the tool's own status. Read the output to tell findings from errors, or use the Prettier fallback form, which preserves Prettier's status.

`sed -z` and `xargs -0 -r` are GNU forms. On a system without them, use the fallback Prettier command and give `markdownlint-cli2` the tracked file list another way; do not fall back to a bare recursive glob.

These local commands require the corresponding packages to be installed; the managed reusable lint caller supplies its own action runtime. With `npx --no-install`, install the repository's lockfile-defined Node dependencies first, normally with `npm ci`. The reconciled workflow is the canonical option-aware CI verification.

Neither tool reads `.git/info/exclude` on its own, and a bare markdownlint invocation does not read `.gitignore` either. `markdownlint-cli2` 0.23.2 reads Git ignore files only when a `.markdownlint-cli2.*` runner config sets `gitignore: true`; this package ships the rule set `.markdownlint.json`, not a runner config, and the option has no CLI or action equivalent. Prettier reads `.gitignore` and `.prettierignore`, but only the copies in the working directory: a nested `.gitignore` is never consulted. Routing both checks through `git ls-files` closes every one of those gaps at once, because Git honors each ignore file at each level plus `.git/info/exclude`, and lists nothing belonging to an independent nested repository — a child repository appears in the parent index as a single gitlink, never as its files. Do not try to reach `.git/info/exclude` with `--ignore-path`; Prettier anchors an ignore file's patterns to that file's own directory, so every pattern would resolve against `.git/info/`.

The managed CI callers keep passing globs, because the reusable workflows and the `markdownlint-cli2` action expand them in a fresh single-repository checkout where none of these hazards exist. The generated-directory negations therefore remain required there and are carried into the local command as `:(glob,exclude)` pathspecs, so both scopes stay equal even for a repository that deliberately tracks one of those directories.

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
