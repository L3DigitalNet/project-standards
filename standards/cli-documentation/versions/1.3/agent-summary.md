# CLI Documentation 1.3 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.3`; documentation contract option: `1.0`.
- Default profile: `script`; default CI state: disabled.
- With `usage_ownership = "managed"`, owned output is create-only `docs/usage.md`; `consumer-owned` preserves a customized legacy usage reference and leaves the path outside reconciliation and lock state.
- Packaged profiles require a nonempty inert `command_name`; it never affects executable or workflow run bytes.
- Enabled CI requires runner, language, setup, and a consumer-owned `workflow_path`.
- Rendered workflows obtain the installed wrapper from the reviewed `CLI_DOCS_COMMAND` repository variable.
- Workflow verification uses the resolved payload and immutable referenced-input bytes; the package owns no GitHub workflow path.
- Companions are empty, so package selection remains independent.
- Legacy exact usage/workflow bytes are preserved. An edited usage reference requires explicit `usage_ownership: "consumer-owned"` migration intent.
- A customized legacy workflow migrates by declaring `workflow_ownership: "consumer-owned"` before previewing; migration preserves the file, leaves CI disabled, and records no referenced input.
- V2 adoption delegates generic lifecycle mechanics and installs no legacy configuration fragment.

Use [adopt.md](adopt.md) for package-specific configuration.
