# Retrofit Standard Manifests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete SPEC-MT01 Step 05 by adding validated `standard.toml` manifests to every existing standard bundle.

**Architecture:** This is a data-first retrofit over the Step 03 manifest model and Step 04 standards graph validator. Canonical manifests live in `standards/<id>/standard.toml`; packaged `src/project_standards/bundles/<id>/adopt.toml` files remain the artifact plane and are not moved in this step. The current-repo graph smoke test becomes the enforcement gate: `--require-all-manifests` must pass once the retrofit lands. The only code change allowed in this plan is the narrow graph-rule correction that lets `reference-only` standards omit an `adopt` resource, matching the Standard Bundle Authoring Standard's non-adoptable draft rule.

**Tech Stack:** TOML, Pydantic `StandardManifest`, `project-standards standards validate-graph`, pytest, markdown/frontmatter/spec validators.

---

## Manifest Matrix

Use these exact classifications while writing the manifests:

| Standard | Adoption | Status | Versions | Config namespaces | Relations |
| --- | --- | --- | --- | --- | --- |
| `markdown-frontmatter` | `validator` | `active` | supported `["1.1"]`, latest `"1.1"` | `["markdown.frontmatter"]` | companions `["adr", "markdown-tooling"]` |
| `adr` | `validator` | `active` | supported `["1.0"]`, latest `"1.0"` | `["markdown.adr"]` | companions `["markdown-frontmatter"]` |
| `markdown-tooling` | `copy-adopt` | `active` | supported `["1.0", "1.1"]`, latest `"1.1"` | `["markdown_tooling"]` | companions `["markdown-frontmatter"]` |
| `python-tooling` | `copy-adopt` | `active` | supported `["1.0"]`, latest `"1.0"` | `["python_tooling"]` | companions `["python-coding"]` |
| `project-spec` | `cli` | `active` | supported `[]`, latest `""` | `["spec"]` | companions `[]` |
| `cli-documentation` | `copy-adopt` | `active` | supported `["1.0"]`, latest `"1.0"` | `["cli_documentation"]` | companions `[]` |
| `python-coding` | `reference-only` | `draft` | supported `[]`, latest `"0.4"` | `[]` | companions `["python-tooling"]` |
| `standard-bundle-authoring` | `none` | `active` | supported `[]`, latest `""` | `[]` | existing manifest remains valid |

Provider rules:

- Use `kind = "python"` only for importable, existing entry points such as `project_standards.validate_frontmatter:main`, `project_standards.validate_id:main`, `project_standards.validate_references:main`, `project_standards.format_frontmatter:main`, and `project_standards.specs.cli:run`.
- Use `kind = "workflow"` only for shipped workflow names such as `validate-markdown-frontmatter`, `lint-markdown`, `format`, `check`, `validate-specs`, and `cli-docs-check`.
- Use `kind = "documentation-only"` when the standard has no executable provider today.
- Do not create cross-bundle resource paths; every `[resources]` path must be bundle-local and already exist.

Authority rules:

- Mutating authorities may overlap only when they share the same owner or govern different concerns.
- `markdown-tooling` owns physical formatting for Markdown/JSON/YAML/EditorConfig and structure linting for Markdown.
- `markdown-frontmatter` owns frontmatter schema/id/reference validation and frontmatter formatting.
- `adr` owns ADR schema/section validation and ADR templates.
- `python-tooling` owns Python project tooling configuration, Ruff formatting/linting, BasedPyright typing, pytest/coverage, and pip-audit checks.
- `project-spec` owns project spec structure, ID allocation/extraction, scaffolding, and upgrade operations.
- `cli-documentation` owns CLI usage documentation structure and drift checks.
- `python-coding` is draft/reference guidance, so declare non-mutating review authority only.

### Task 1: Flip the Step 05 graph smoke test and reference-only rule

**Files:**

- Modify: `tests/test_standards_graph_cli.py`
- Modify: `tests/test_standards_graph_validators.py`
- Modify: `src/project_standards/standards_graph/validators.py`

- [ ] **Step 1: Replace the pre-retrofit expected-failure assertion.**

Change `test_current_repo_validate_graph_require_all_manifests_reports_step05_gap` so it is named `test_current_repo_validate_graph_require_all_manifests_passes_after_retrofit` and asserts:

```python
    rc = main(
        ["standards", "validate-graph", "--root", str(root), "--require-all-manifests", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["findings"] == []
```

- [ ] **Step 2: Run the focused test and confirm it fails for the Step 05 reason.**

Run:

```bash
uv run pytest tests/test_standards_graph_cli.py::test_current_repo_validate_graph_require_all_manifests_passes_after_retrofit -q
```

Expected: FAIL with `assert 1 == 0` because the seven existing standards still have no manifest.

- [ ] **Step 3: Add the reference-only no-adopt regression test.**

Add this test to `tests/test_standards_graph_validators.py`:

```python
def test_reference_only_standard_does_not_require_adopt_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "python-coding", adoption="reference-only")

    assert "SG-RESOURCE-ADOPT-MISSING" not in _codes(tmp_path)
```

Run:

```bash
uv run pytest tests/test_standards_graph_validators.py::test_reference_only_standard_does_not_require_adopt_resource -q
```

Expected before the code fix: FAIL with `SG-RESOURCE-ADOPT-MISSING`.

- [ ] **Step 4: Restrict adopt-resource enforcement to adoptable modes.**

In `src/project_standards/standards_graph/validators.py`, add:

```python
_ADOPT_RESOURCE_REQUIRED_MODES = frozenset(
    {AdoptionMode.VALIDATOR, AdoptionMode.COPY_ADOPT, AdoptionMode.CLI}
)
```

Then change the `SG-RESOURCE-ADOPT-MISSING` condition to check membership in that set instead of `adoption is not AdoptionMode.NONE`.

Run:

```bash
uv run pytest tests/test_standards_graph_validators.py::test_reference_only_standard_does_not_require_adopt_resource -q
```

Expected after the code fix: PASS.

### Task 2: Add validator and CLI standard manifests

**Files:**

- Create: `standards/markdown-frontmatter/standard.toml`
- Create: `standards/adr/standard.toml`
- Create: `standards/project-spec/standard.toml`

- [ ] **Step 1: Add the three manifests using the matrix above.**

Each file must include `[standard]`, `[versions]`, `[config]`, `[capabilities]`, `[relations]`, `[resources]`, `[[authority]]`, and `[[providers]]` sections. Required adoptable resources are `readme = "README.md"` and `adopt = "adopt.md"`.

- [ ] **Step 2: Run focused validation.**

Run:

```bash
uv run pytest tests/test_standard_manifest.py::test_real_manifest_validates -q
uv run project-standards standards validate-graph --root . --require-all-manifests --json
```

Expected after this task: manifest test passes for the manifests that exist; graph still exits `1` with missing-manifest findings for the remaining standards.

### Task 3: Add copy-adopt and reference standard manifests

**Files:**

- Create: `standards/markdown-tooling/standard.toml`
- Create: `standards/python-tooling/standard.toml`
- Create: `standards/cli-documentation/standard.toml`
- Create: `standards/python-coding/standard.toml`

- [ ] **Step 1: Add the four manifests using the matrix above.**

For `python-coding`, omit `adopt` because `adoption = "reference-only"` is not backed by an adoption guide today; declare `readme = "README.md"` only.

- [ ] **Step 2: Run the focused graph smoke test.**

Run:

```bash
uv run pytest tests/test_standards_graph_cli.py::test_current_repo_validate_graph_require_all_manifests_passes_after_retrofit -q
```

Expected: PASS.

### Task 4: Broaden real-manifest coverage

**Files:**

- Modify: `tests/test_standard_manifest.py`

- [ ] **Step 1: Parametrize real manifest validation.**

Replace the single hard-coded real manifest test with:

```python
_REAL_MANIFESTS = sorted(
    (Path(__file__).resolve().parent.parent / "standards").glob("*/standard.toml")
)


@pytest.mark.parametrize("real", _REAL_MANIFESTS, ids=lambda p: p.parent.name)
def test_real_manifests_validate(real: Path) -> None:
    load_standard_manifest(real)
```

- [ ] **Step 2: Run the focused manifest tests.**

Run:

```bash
uv run pytest tests/test_standard_manifest.py::test_real_manifests_validate -q
```

Expected: PASS for all eight standard manifests.

### Task 5: Verify Step 05

**Files:**

- No edits unless verification exposes a narrow bug.

- [ ] **Step 1: Run the Step 05 focused gate.**

Run:

```bash
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run pytest tests/test_standards_graph_cli.py tests/test_standard_manifest.py -q
```

Expected: graph exits 0 and focused tests pass.

- [ ] **Step 2: Run standards/docs gates touched by the change.**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
```

Expected: all exit 0.

### Task 6: Update handoff and release tracker

**Files:**

- Modify: `TODO.md`
- Modify: `docs/handoff/state.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/handoff/sessions/2026-07.md`
- Modify: `STATUS.md`

- [ ] **Step 1: Record Step 05 as complete.**

In `TODO.md`, mark Step 05 complete with the date and final commit ref. In `docs/handoff/state.md`, advance the next item to Step 06. In `docs/handoff/specs-plans.md`, add this plan row and mark Step 05 implemented. Add one concise `STATUS.md` recent-change line and one session-log row.

- [ ] **Step 2: Run handoff/doc validation.**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
git diff --check
```

Expected: both exit 0.
