# CLI Documentation 1.6 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.6`; documentation contract option: `1.0`.
- Default profile: `script`; default CI state: disabled.
- With `usage_ownership = "managed"`, owned output is create-only `docs/usage.md`; `consumer-owned` preserves a customized legacy usage reference and leaves the path outside reconciliation and lock state.
- Optional `usage_index_path` references one existing, contained consumer-owned Markdown index; a fresh usage scaffold links to it, while later path changes preserve the create-only scaffold.
- Multiple generated usage artifacts and per-command CI matrices remain unsupported.
- Packaged profiles require a nonempty inert `command_name`; it never affects executable or workflow run bytes.
- Enabled CI requires runner, language (`python`, `go`, or `generic`), matching setup (`uv`, `go`, or `none`), and a consumer-owned `workflow_path`.
- Rendered workflows obtain the installed command name from the reviewed `CLI_DOCS_COMMAND` repository variable.
- The Go workflow also validates `CLI_DOCS_GO_PACKAGE`, reads the toolchain from `go.mod`, builds one explicit `main` package to a temporary executable, and smokes that binary.
- Packaged documentation is language-neutral: public command names come from the distribution authority; Python maps that to `[project.scripts]`, while Go maps it to explicit build or release targets.
- Parser-derived man pages, deep command references, and shell completions are generated surfaces; committed or shipped artifacts require regeneration drift checks.
- Workflow verification uses the resolved payload and immutable referenced-input bytes; the package owns no GitHub workflow path.
- Companions are empty, so package selection remains independent.
- Legacy exact usage/workflow bytes are preserved. An edited usage reference requires explicit `usage_ownership: "consumer-owned"` migration intent.
- A customized legacy workflow migrates by declaring `workflow_ownership: "consumer-owned"` before previewing; migration preserves the file, leaves CI disabled, and records no referenced input.
- V2 adoption delegates generic lifecycle mechanics and installs no legacy configuration fragment.

Use [adopt.md](adopt.md) for package-specific configuration.
