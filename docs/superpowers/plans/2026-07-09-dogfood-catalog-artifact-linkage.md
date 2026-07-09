# Dogfood Catalog and Artifact Linkage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete SPEC-MT01 Step 06 by linking standard and artifact manifests, proving standard composition, and generating a fresh standards catalog.

**Architecture:** Keep `standard.toml` as the standard metadata plane and packaged `adopt.toml` as the artifact plane. Add an explicit optional `[artifacts]` link to the standard manifest, typed provenance to every packaged artifact, graph-level cross-plane validation, a pure catalog renderer, and a CLI freshness check. Exercise the existing multi-standard adopt planner over individual, pairwise, and all-standard combinations.

**Tech Stack:** Python 3.14, Pydantic, `tomllib`, pytest, the existing adopt engine and standards graph CLI.

---

## Tasks

### Task 1: Model explicit artifact-manifest linkage

**Files:**

- Modify: `src/project_standards/standard_manifest.py`
- Modify: `src/project_standards/schemas/standard.schema.json`
- Modify: `tests/standards_graph_helpers.py`
- Modify: `tests/test_standard_manifest.py`

- [ ] Add a failing model test proving `[artifacts].manifest` accepts a safe repository-relative path and rejects absolute/traversing paths.
- [ ] Add an `ArtifactsTable` with `manifest: str`, validate it as a safe relative path, and expose `artifacts: ArtifactsTable | None` on `StandardManifest`.
- [ ] Regenerate the bundled JSON schema and run `uv run pytest tests/test_standard_manifest.py -q`.

### Task 2: Add typed artifact provenance

**Files:**

- Modify: `src/project_standards/adopt/manifest.py`
- Modify: `tests/test_adopt_manifest.py`
- Modify: `src/project_standards/bundles/*/adopt.toml`

- [ ] Add failing tests for the four provenance classes: `source-owned`, `generated`, `package-owned`, and `external-owned`.
- [ ] Require `provenance` on every `[[artifact]]`; require `canonical` for source-owned/generated artifacts, require `transform` for generated artifacts, and reject canonical/transform metadata on package-owned/external-owned artifacts.
- [ ] Require `external-owned` artifacts to use `shared`, and reject `shared` for the other provenance classes.
- [ ] Annotate every current packaged artifact with its provenance and canonical source when applicable.
- [ ] Run `uv run pytest tests/test_adopt_manifest.py tests/test_adopt_dogfood.py -q`.

### Task 3: Validate the two manifest planes together

**Files:**

- Modify: `src/project_standards/standards_graph/model.py`
- Modify: `src/project_standards/standards_graph/discovery.py`
- Modify: `src/project_standards/standards_graph/validators.py`
- Modify: `tests/standards_graph_helpers.py`
- Modify: `tests/test_standards_graph_discovery.py`
- Modify: `tests/test_standards_graph_validators.py`

- [ ] Add failing tests for missing/mismatched artifact links, orphan packaged manifests, non-adoptable standards with artifact links, source-owned parity drift, missing canonical sources, and global skill destinations.
- [ ] Load a linked adopt manifest into each `StandardNode` and retain its path; discover orphan packaged manifests under `src/project_standards/bundles/*/adopt.toml`.
- [ ] Add deterministic graph findings for cross-plane linkage, adoption posture, canonical provenance/parity, and project-local skill installation.
- [ ] Run `uv run pytest tests/test_standards_graph_discovery.py tests/test_standards_graph_validators.py -q`.

### Task 4: Retrofit real standard manifests and authoring docs

**Files:**

- Modify: `standards/{adr,cli-documentation,markdown-frontmatter,markdown-tooling,project-spec,python-tooling}/standard.toml`
- Modify: `standards/standard-bundle-authoring/README.md`
- Modify: `standards/standard-bundle-authoring/templates/standard.toml`

- [ ] Add `[artifacts]` links to all six standards that ship packaged adoption manifests.
- [ ] Document the link and provenance contract in the Standard Bundle Authoring Standard and its template.
- [ ] Run `uv run project-standards standards validate-graph --root . --require-all-manifests`.

### Task 5: Prove individual and combined adoption

**Files:**

- Create: `tests/test_standards_composition.py`

- [ ] Add a failing fixture test that derives adoptable standard IDs from graph metadata rather than a handwritten list.
- [ ] Prove every adoptable standard builds a plan alone, every pair builds a collision-free plan, and the all-standard combination builds and executes into `tmp_path`.
- [ ] Assert declared conflicts are absent from successful combinations, shared artifacts deduplicate, fragments remain report-only, and the repo-local skill lands under `.agents/skills/`.
- [ ] Run `uv run pytest tests/test_standards_composition.py -q`.

### Task 6: Generate and check the standards catalog

**Files:**

- Create: `src/project_standards/standards_graph/catalog.py`
- Modify: `src/project_standards/standards_graph/cli.py`
- Modify: `src/project_standards/standards_graph/__init__.py`
- Create: `tests/test_standards_graph_catalog.py`
- Modify: `tests/test_standards_graph_cli.py`
- Create: `standards/catalog.md`
- Modify: `standards/README.md`

- [ ] Add failing renderer tests covering all standard IDs, lifecycle/adoption/version/config facts, capabilities, resources, provider operations, artifact counts/provenance, repo-local skills, and companion/extension/conflict edges.
- [ ] Implement a deterministic pure Markdown renderer and `standards render-catalog --root . [--check] [--output PATH]`.
- [ ] Generate `standards/catalog.md`, link it from the human standards index, and prove `--check` exits 1 on stale output and 0 when fresh.
- [ ] Run `uv run pytest tests/test_standards_graph_catalog.py tests/test_standards_graph_cli.py -q`.

### Task 7: Verify Step 06 and update handoff

**Files:**

- Modify: `TODO.md`
- Modify: `STATUS.md`
- Modify: `docs/handoff/state.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/handoff/sessions/2026-07.md`

- [ ] Run the complete Python gate, coherence gate, graph validation, catalog freshness check, managed Markdown/spec gates, and handoff validators.
- [ ] Mark Step 06 complete and advance the active next item to Step 07 without starting MCP server work.
- [ ] Run `git diff --check` and review the complete diff.
