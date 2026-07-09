# Adopt the CLI Documentation Standard

This procedure walks an adopter from profile selection to a passing CI drift check. It assumes the standard itself ([`README.md`](README.md)) has already been read for the rules; this document is the runbook for applying them.

## 1. Choose a profile

Profile selection is a recorded judgment, not a validator-checked number ([README §3 Profiles](README.md#3-profiles)). Use the signals below, then write the chosen profile and its rationale into `docs/usage.md` (or repo docs, for the Script profile, which has no usage doc by default).

| Signal | Profile |
| --- | --- |
| Single-file script, run in place, no packaging | Script |
| Installed via `[project.scripts]`; a single-page usage reference stays maintainable | Packaged |
| More than roughly 5–7 top-level subcommands, or a second nesting level combined with a leaf-command count large enough that a single page demonstrably drifts or becomes unnavigable | Packaged, deep |

Nesting alone is never the trigger for the deep profile — it is one input alongside leaf-command count ([README §3](README.md#3-profiles)). If unsure, start at Packaged; moving to Packaged-deep later is additive, not a rewrite, because the ladder is a strict superset ([README §3](README.md#3-profiles)).

## 2. What `adopt` materializes vs. what you copy manually

| Artifact | Source | Materialized by |
| --- | --- | --- |
| `docs/usage.md` scaffold | [`templates/usage-doc.md`](templates/usage-doc.md) | `adopt` (file) |
| `.github/workflows/cli-docs-check.yml` | [`templates/cli-docs-check.yml`](templates/cli-docs-check.yml) | `adopt` (file) |
| `cli_documentation: version: "1.0"` fragment for `.project-standards.yml` | this standard's contract version | `adopt` (reported/printed only — the engine never writes `.project-standards.yml` itself; merge the fragment in by hand) |
| `templates/readme-single-file.md` | [`templates/readme-single-file.md`](templates/readme-single-file.md) | manual copy — Script-profile repos only; script repos rarely run `adopt` at all ([README §12 Adoption](README.md#12-adoption)) |

`adopt` skips a target file that already exists unless you pass `--force`; rerunning it is safe and idempotent.

## 3. Fill the usage scaffold

Work through the copied `docs/usage.md` top to bottom:

- **`NAME`/`SYNOPSIS`**: replace `toolname` with your installed entry-point name — the `[project.scripts]` key, never the module path or filename ([README §8 Packaged CLIs](README.md#8-packaged-clis), the `prog` discipline rule).
- **Every leaf command**: the Packaged tier requires the reference to cover every leaf command the tool exposes, not just top-level subcommands ([README §3 Profiles](README.md#3-profiles)).
- **Option entries**: for every flag, option-argument, positional, and subcommand, fill the required fields from [README §6 Option entries](README.md#6-option-entries) in order — spelling and meaning are always required; value syntax, default, allowed values, mutually-exclusive/depends-on, applies-to, safety impact, environment/config interaction, and since/deprecated apply only when relevant. Delete the template's placeholder options (`--format`, `--jobs`, and so on) that don't exist in your tool, and add real ones using the same field order.
- **Multi-entry-point packages**: give each installed command its own usage-reference page, or use the grouped-page provision, provided each command still gets a complete `NAME`/`SYNOPSIS`/`OPTIONS`/`EXIT STATUS` entry ([README §3 Profiles](README.md#3-profiles)).

## 4. Wire the CI workflow

- Edit the copied `.github/workflows/cli-docs-check.yml`'s `env.TOOL` to your installed command name (the `[project.scripts]` key, matching step 3).
- Keep `NO_COLOR: "1"`. Snapshot tests of help output MUST normalize `NO_COLOR` and a fixed terminal width before comparing, because Python 3.14's `argparse` colors help by default and Click rewraps by width ([README §9 CI drift prevention](README.md#9-ci-drift-prevention)).
- The shipped workflow only proves the installed `--help`/`--version` run. As the tool's surface grows, add the remaining Packaged-tier-and-above checks from [README §9](README.md#9-ci-drift-prevention): subcommand help smoke, inventory parity (every `[project.scripts]` key and parser leaf appears in the docs), option/exit-code parity, a generated man-page diff (if a man page is committed), and example execution.

## 5. Authoring and review checklist

| Area | Review question |
| --- | --- |
| Name line | Does `NAME` fit the `toolname — short description` pattern? |
| Synopsis | Does `SYNOPSIS` describe real parser behavior, not an aspirational interface? |
| Notation | Does the document use one notation system consistently? |
| Help boundary | Is `--help` concise while the usage doc stays exhaustive? |
| Options | Does every documented option state defaults, values, conflicts, and scope when relevant? |
| Examples | Are examples task-first, copy-pasteable, and safety-biased? |
| Exit codes | Are all user-visible exit codes documented with conditions? |
| Environment | Are all effective env vars listed, with precedence rules if needed? |
| Files | Are config/state/log/cache paths listed with defaults? |
| Versioning | Are newly introduced or deprecated flags marked by version when relevant? |
| Accessibility | Can the docs be understood without color or terminal-specific rendering? |
| Localization | Are localizable prose and non-localizable command literals clearly separated? |
| Drift | Do docs, `--help`, parser definitions, and man page agree? |
| Links and references | Do README and help point to the authoritative usage doc? |
| Scripts inventory | Every `[project.scripts]` key documented or classified internal? |
| Installed-wrapper smoke | Installed-wrapper smoke test present? |
| Normalized help | Option/exit-code sections checked against normalized `--help`? |

## 6. Conformance summary per profile

| Profile | Must show |
| --- | --- |
| Script | `--help` and `--version`; a compact README per [`templates/readme-single-file.md`](templates/readme-single-file.md); documented exit codes. A usage doc and man page are optional. |
| Packaged | Everything the Script tier requires, plus `docs/usage.md` covering every leaf command with `NAME`/`SYNOPSIS` keyed to the entry-point name, and a CI smoke test of the installed entry point. A man page is recommended where practical, best-effort by nature. |
| Packaged, deep | Everything the Packaged tier requires, except the usage reference is generated per-command (`docs/cli/<command>.md`) from parser metadata — hand-maintained per-command pages are prohibited — plus one shared-concepts page for common environment variables, exit codes, and config. |
