# Adopt the CLI Documentation Standard

The current consumer package is [`cli-documentation@1.3`](versions/1.3/adopt.md). Use it for a create-only CLI usage reference and, when selected, a consumer-owned CI workflow verified against provider-rendered bytes.

## Configure and reconcile

Enable the package, then choose `profile`, `command_name`, `workflow_ownership`, and the closed `ci` options under `[standards.cli-documentation.config]`. Package version `1.3` and `contract_version = "1.0"` are independent selectors. `workflow_ownership = "referenced"` verifies and locks the reviewed workflow; `"consumer-owned"` preserves a customized legacy workflow without a reference or CI enablement.

```bash
project-standards standards enable cli-documentation --version 1.3
project-standards reconcile
project-standards reconcile --apply
```

The bare `reconcile` is the required preview; review every action before `--apply`. When CI is enabled and `workflow_ownership = "referenced"`, render the workflow to a scratch file, review and validate it, publish it with a no-clobber redirection, then rerun preview and apply. The provider writes only to standard output; the published workflow remains consumer-owned and is locked as a referenced input. Reconciliation creates `docs/usage.md` only when absent.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Migration maps `cli_documentation.version`, recognizes exact legacy workflow bytes, and preserves existing usage prose. A customized legacy workflow migrates only when `workflow_ownership: "consumer-owned"` is declared under `cli_documentation:` in `.project-standards.yml` before preview: migration preserves the file exactly, leaves CI disabled, and records no referenced input. Other edited or ambiguous files remain unclaimed until the owner resolves them.

## Verify and troubleshoot

```bash
project-standards render cli-documentation render-workflow --repo . >/tmp/cli-docs-check.yml
project-standards reconcile --check
project-standards validate
```

A missing referenced workflow, unsafe command basename, output mismatch, or provider mutation is a refusal. Restore the reviewed consumer file and retry; never grant the provider a destination path. See the [version-specific guide](versions/1.3/adopt.md) for exact profiles, options, output publication, verification, and authoring review.
