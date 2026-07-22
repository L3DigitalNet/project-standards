# Standard Bundle Authoring family: Agent Summary

Current authority is the active Catalog 5 internal payload [`standard-bundle-authoring@2.4`](versions/2.4/agent-summary.md). Its [versioned standard](versions/2.4/README.md) wins over this mutable navigation summary.

- Keep mutable family identity and indexed version digests in `standards/<id>/standard.toml`.
- Put each complete immutable payload under `standards/<id>/versions/<major.minor>/`.
- Assign channel and availability roles only in catalog sources.
- Declare and digest every payload file; released payload corrections require a new package version.
- Give contributions the smallest normalized adapter scope; providers run offline against immutable snapshots and never write the live repository.
- Prove source, graph, projection, direct-wheel, sdist-derived-wheel, migration, and compatibility parity before release.

Version 2.4 is active and internal, not staged or consumer-selectable; versions 2.0, 2.1, 2.2, and 2.3 stay advertised as released history. Use the [author workflow](versions/2.4/README.md#author-workflow) and [templates](versions/2.4/templates/).
