# CLI Documentation family: Agent Summary

Current authority is the Catalog 5 consumer payload [`cli-documentation@1.2`](versions/1.2/agent-summary.md). Its [versioned standard](versions/1.2/README.md) wins over this mutable navigation summary.

- Select the Script, Packaged, or Packaged-deep profile independently of package version 1.2.
- Keep parser-generated help concise and put the complete command, option, exit-code, environment, file, caveat, and example contract in the usage reference.
- Package 1.2 owns only a create-only `docs/usage.md`; existing usage prose remains consumer-owned.
- When CI is enabled, the provider renders workflow bytes to standard output. Review and publish those bytes to the configured consumer-owned path, then reconcile the referenced input.
- Document installed entry-point names and every leaf command. Treat command names, options, semantic defaults, exit codes, environment variables, file locations, and output formats as versioned interface surface.
- Legacy exact usage/workflow bytes support migration only; no V2 adoption writes a legacy configuration fragment.

See the [current adoption guide](adopt.md) for configuration, workflow publication, migration, and verification.
