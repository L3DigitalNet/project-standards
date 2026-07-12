# Consumer Standards Control Plane Release-Cut Evidence

**Evidence date:** 2026-07-12

**Source branch:** `testing`

**Release candidate:** `project-standards 5.0.0` built from a disposable tracked-tree checkout

## Result

The disposable release cut migrates the repository from the bounded V4 YAML authority to the catalog-5 control plane without changing the source checkout. Human and JSON previews report the same applicable migration, apply retires the legacy authority and Agent Handoff package lock only after verification, and a second reconciliation changes no bytes.

The migrated checkout passes unified Frontmatter validation, Project Specification validation and strict lint, Agent Handoff validation and drift checking, installed catalog drift checking, and patch replay. Consumer-authored `docs/handoff/**` bytes are unchanged.

The installed checkout also exercises Frontmatter fix, Project Specification extract/next plus scaffold/upgrade stdout previews, Agent Handoff size/shape/legacy reports and upgrade, and CLI Documentation render. The command matrix removes its temporary spec and proves the complete repository file identity is unchanged afterward.

## Reviewed procedure

The test copies only `git ls-files` entries, changes `pyproject.toml` and the root `uv.lock` package entry to `5.0.0`, and records repository-specific Python Tooling intent in the disposable legacy input. That intent retains `types-PyYAML`, the performance marker, the coverage `__main__` exclusion, and the three narrow vendored/handoff Ruff exclusions; the release patch also tightens the package-owned Ruff lower bound from `0.14` to `0.14.11`.

The reviewed commands are:

```bash
project-standards init --catalog 5 --migrate --repo .
project-standards init --catalog 5 --migrate --repo . --json
project-standards init --catalog 5 --migrate --apply --repo .
project-standards reconcile --apply --repo .
project-standards standards render-consumer-catalog --root . --catalog-major 5 \
  --output .standards/catalog.toml --tool-release 5.0.0 --check
```

The automated proof uses a source-side read-only plan for detailed expected-state assertions, proves that its action targets equal both installed CLI preview formats, and performs the mutation only through the extracted wheel's `init --migrate --apply`. Every mutating and validation command runs with `PYTHONPATH` bound to that installed tree.

## Patch identity

The binary-safe patch is `git diff --binary --no-ext-diff HEAD -- .` from a local commit of the tracked baseline after mirroring the completed disposable release tree. Its SHA-256 is:

```text
c0cb28608c9450ea22f10bb3e54df50b97734ba76261c306a8930b88a536f656
```

Changed paths:

```text
D .agents/agent-handoff/manifest.json
M .agents/skills/agent-handoff/SKILL.md
A .agents/skills/markdown-frontmatter/SKILL.md
A .agents/skills/markdown-frontmatter/agents/openai.yaml
A .agents/skills/markdown-frontmatter/scripts/new-doc-id
M .codex/config.toml
M .github/workflows/check.yml
D .github/workflows/validate-markdown-frontmatter.yml
M .github/workflows/validate-specs.yml
A .github/workflows/validate-standards.yml
D .project-standards.yml
A .standards/catalog.toml
A .standards/config.toml
A .standards/lock.toml
A .standards/packages/agent-handoff/policy.toml
A .standards/packages/markdown-frontmatter/agent-summary.md
M .vscode/settings.json
M AGENTS.md
M CLAUDE.md
A docs/adr/adr.template.md
M pyproject.toml
M scripts/check.py
M uv.lock
```

Control-plane file SHA-256 digests:

```text
config.toml  2bce514453bb7d08fbd16136325d1d8c55c42cd9aa63d043f7fc9f89c7a2a098
catalog.toml 840051ba2a5a4cf02a6105169e24d1adb953cca046d911c7eb04778899c75dd8
lock.toml    9955e73104c415b1b6fffc130db87b72c5dd3c1578f96d84d3935228b222f556
```

Replaying the recorded patch with `git apply --binary -` against a fresh tracked-tree copy produces an identical complete file tree and the same three control-plane digests.

## Dependency classification

- `src/project_standards/control_plane/**` references to `.project-standards.yml` are the explicit V5 legacy-only detection, preview, and retirement adapter.
- `src/project_standards/bundles/**`, the legacy adopt engine, V1 graph tooling, and their tests remain the plan-pinned V5 fallback surface for removal at the V6 gate.
- legacy paths in migration fixtures, payload legacy signatures, historical specifications, and migration documentation are inert evidence.
- the migrated root workflows contain no active `.project-standards.yml` or package-specific Agent Handoff lock dependency. `.standards/config.toml` is their only root authority.

The release-candidate test performs the active-workflow scan and rejects either legacy authority path. Retained runtime references are covered by the V5 fallback tests in `tests/test_adopt_*.py`, `tests/test_frontmatter_unified_config.py`, `tests/test_spec_selected_routing.py`, and the package migration fixtures; the extracted-wheel compatibility matrix reruns the same catalog-derived package inventory offline.

## Same-major refresh

`tests/control_plane/test_catalog_refresh.py` builds a second catalog-5 snapshot containing `alpha@2.1`. The CLI preview/apply proof advances a compatible `latest` selection from `2.0` to `2.1`, preserves exact pins, options, accepted-track boundaries, extensions, and unrelated files, writes the catalog and central lock transactionally, and converges under `--check`.

## Automated evidence

- `tests/package_compatibility/test_release_candidate.py`
- `tests/control_plane/test_catalog_refresh.py`
- `tests/package_compatibility/test_catalog_matrix.py`
- `tests/package_compatibility/test_performance.py`
- `tests/test_spec_selected_routing.py` and the selected Frontmatter/Agent Handoff routing suites, which exercise inspect, validate, render, fix, scaffold, upgrade, verify, drift-check, and migration provider paths through unified selection

The source checkout deliberately retains package version `4.3.0`, `.project-standards.yml`, and no `.standards/` directory. The complete tracked `.standards/` tree first materializes in this disposable proof and is reserved for the atomic v5 release commit.
