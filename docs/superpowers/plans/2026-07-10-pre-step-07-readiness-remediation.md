# Pre-Step-07 Readiness Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile all implemented SPEC-MT01 Steps 00-06 with repository evidence, fix verified housekeeping defects, and add visible hosted graph/catalog enforcement before Step 07 begins.

**Architecture:** Keep repository-only enforcement separate from the byte-identical reusable Python Tooling gate. Correct Agent Handoff shape discovery at the generic pattern boundary, then reconcile authored standards, traceability, release guidance, and current handoff pointers from existing evidence. Leave Step-07 readiness reporting and owner-choice debt visibly open.

**Tech Stack:** Python 3.14, Pydantic, pytest, PyYAML, GitHub Actions YAML, TOML policy bundles, Markdown, Ruff, BasedPyright, coverage, pip-audit, Prettier, and markdownlint.

---

## Worktree and commit discipline

The worktree already contains an owner-authored rename under `docs/future-standards/`. Do not stage, format, lint, restore, or otherwise modify either of these paths during this plan:

- `docs/future-standards/Project Standards - GitHub Usage Standard.md`
- `docs/future-standards/github-repository-governance-standard.md`

Before every commit, run `git status --short`, stage only the files named by that task, and inspect `git diff --cached --name-status`. Keep `.github/workflows/check.yml` and `scripts/check.py` byte-identical to their Python Tooling bundle copies; this plan never edits them.

## Tasks

### Task 1: Correct Agent Handoff bug-record shape discovery

**Files:**

- Modify: `tests/agent_handoff/test_policy.py`
- Modify: `tests/agent_handoff/test_validation.py`
- Modify: `src/project_standards/agent_handoff/policy.py`
- Modify: `src/project_standards/agent_handoff/validation.py`
- Modify: `standards/agent-handoff/resources/policy.toml`
- Modify: `src/project_standards/bundles/agent-handoff/resources/policy.toml`

- [ ] **Step 1: Add the policy regression assertion**

Extend `tests/agent_handoff/test_policy.py` with:

```python
def test_bug_profile_targets_numbered_records_only(policy: HandoffPolicy) -> None:
    documents = policy.shape.documents

    assert "docs/handoff/bugs/[0-9][0-9][0-9]-*.md" in documents
    assert "docs/handoff/bugs/*.md" not in documents
```

- [ ] **Step 2: Add failing repository-shape tests**

Import the validation module, `load_policy`, and define a policy path plus a helper in `tests/agent_handoff/test_validation.py`:

```python
import project_standards.agent_handoff.validation as validation
from project_standards.agent_handoff.policy import HandoffPolicy, load_policy

POLICY_PATH = (
    Path(__file__).parents[2]
    / "src/project_standards/bundles/agent-handoff/resources/policy.toml"
)


def _replace_shape_pattern(pattern: str) -> HandoffPolicy:
    policy = load_policy(POLICY_PATH)
    bug_policy = next(
        document
        for document in policy.shape.documents.values()
        if document.profile == "bug-record"
    )
    shape = policy.shape.model_copy(update={"documents": {pattern: bug_policy}})
    return policy.model_copy(update={"shape": shape})
```

Add these tests:

```python
def test_shape_check_excludes_index_but_checks_numbered_bug(tmp_path: Path) -> None:
    _adopt(tmp_path)
    bugs = tmp_path / "docs/handoff/bugs"
    (bugs / "INDEX.md").write_text("# Bug Index\n", encoding="utf-8")
    (bugs / "001-test.md").write_text(
        "# Bug\n\n## Cause\n\nCause.\n\n## Fix\n\nFix.\n",
        encoding="utf-8",
    )

    findings = shape_check(RepositoryRoot(tmp_path))

    assert any(finding.path == "docs/handoff/bugs/001-test.md" for finding in findings)
    assert not any(finding.path == "docs/handoff/bugs/INDEX.md" for finding in findings)


def test_shape_check_treats_bracket_only_filename_as_glob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _adopt(tmp_path)
    bug = tmp_path / "docs/handoff/bugs/1.md"
    bug.write_text("# Bug\n", encoding="utf-8")
    policy = _replace_shape_pattern("docs/handoff/bugs/[0-9].md")
    monkeypatch.setattr(validation, "_load_policy", lambda findings: policy)

    findings = shape_check(RepositoryRoot(tmp_path))

    assert any(
        finding.code == "AH-SHAPE" and finding.path.endswith("/1.md")
        for finding in findings
    )


def test_shape_check_rejects_glob_in_directory_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _adopt(tmp_path)
    policy = _replace_shape_pattern("docs/handoff/*/[0-9].md")
    monkeypatch.setattr(validation, "_load_policy", lambda findings: policy)

    findings = shape_check(RepositoryRoot(tmp_path))

    assert any(
        finding.code == "AH-PATH-BOUNDARY"
        and finding.path == "docs/handoff/*/[0-9].md"
        for finding in findings
    )
```

- [ ] **Step 3: Run the tests and verify the red state**

Run:

```bash
uv run pytest \
  tests/agent_handoff/test_policy.py::test_bug_profile_targets_numbered_records_only \
  tests/agent_handoff/test_validation.py::test_shape_check_excludes_index_but_checks_numbered_bug \
  tests/agent_handoff/test_validation.py::test_shape_check_treats_bracket_only_filename_as_glob \
  tests/agent_handoff/test_validation.py::test_shape_check_rejects_glob_in_directory_component -v
```

Expected: failures for the broad policy glob, `INDEX.md` warning, bracket-only literal routing, and unsafe directory glob.

- [ ] **Step 4: Implement generic glob detection and boundary validation**

In `policy.py`, import `has_magic` from `glob` and change `_document_config` so any standard glob metacharacter is recognized:

```python
def _document_config(path: str, policy: HandoffPolicy) -> DocumentPolicy | None:
    exact = policy.shape.documents.get(path)
    if exact is not None:
        return exact
    return next(
        (
            config
            for pattern, config in policy.shape.documents.items()
            if has_magic(pattern) and fnmatch.fnmatchcase(path, pattern)
        ),
        None,
    )
```

In `validation.py`, import `has_magic` and `PurePosixPath`, then replace `_shape_targets` with:

```python
def _shape_targets(repository: RepositoryRoot, pattern: str) -> tuple[tuple[str, bytes], ...]:
    relative_pattern = PurePosixPath(pattern)
    directory = relative_pattern.parent.as_posix()
    filename = relative_pattern.name
    if has_magic(directory):
        raise RepositoryBoundaryError("shape glob directory must be literal")
    if not has_magic(filename):
        data = _read_optional(repository, pattern)
        return () if data is None else ((pattern, data),)
    parent = repository.consumer_path(directory)
    targets: list[tuple[str, bytes]] = []
    for candidate in sorted(parent.glob(filename)):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(repository.path).as_posix()
        data = repository.read_bytes(relative)
        targets.append((relative, data))
    return tuple(targets)
```

- [ ] **Step 5: Narrow both canonical and packaged policy copies**

Change the bug profile key in both TOML files to:

```toml
[shape.documents."docs/handoff/bugs/[0-9][0-9][0-9]-*.md"]
profile = "bug-record"
required_sections = ["Cause", "Fix", "Lesson"]
required = false
severity = "advisory"
```

- [ ] **Step 6: Run focused verification**

Run:

```bash
uv run pytest tests/agent_handoff/test_policy.py tests/agent_handoff/test_validation.py -q
uv run ruff format --check src/project_standards/agent_handoff tests/agent_handoff
uv run ruff check src/project_standards/agent_handoff tests/agent_handoff
cmp standards/agent-handoff/resources/policy.toml \
  src/project_standards/bundles/agent-handoff/resources/policy.toml
uv run project-standards agent-handoff shape-check --repo .
```

Expected: tests pass, policy copies are byte-identical, and no `bugs/INDEX.md` `Cause`/`Fix`/`Lesson` warnings remain.

- [ ] **Step 7: Commit the shape fix**

```bash
git add \
  src/project_standards/agent_handoff/policy.py \
  src/project_standards/agent_handoff/validation.py \
  standards/agent-handoff/resources/policy.toml \
  src/project_standards/bundles/agent-handoff/resources/policy.toml \
  tests/agent_handoff/test_policy.py \
  tests/agent_handoff/test_validation.py
git diff --cached --check
git commit -m "fix(v5): target numbered handoff bug records"
```

### Task 2: Add the repository-only graph and catalog workflow

**Files:**

- Create: `.github/workflows/validate-standards-graph.yml`
- Create: `tests/test_standards_graph_workflow.py`

- [ ] **Step 1: Write the workflow contract test**

Create `tests/test_standards_graph_workflow.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parent.parent


def _load(name: str) -> dict[str, Any]:
    payload = yaml.safe_load((_REPO / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _uses_steps(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    job = next(iter(workflow["jobs"].values()))
    return {step["uses"].split("@", 1)[0]: step for step in job["steps"] if "uses" in step}


def test_repository_graph_workflow_contract() -> None:
    workflow = _load(".github/workflows/validate-standards-graph.yml")
    reusable_gate = _load(".github/workflows/check.yml")
    triggers = workflow[True]

    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main", "testing"]
    assert all(
        "paths" not in trigger
        for trigger in triggers.values()
        if isinstance(trigger, dict)
    )

    job = workflow["jobs"]["standards-graph"]
    assert job["name"] == "Standards graph and catalog"
    commands = [step.get("run") for step in job["steps"]]
    assert "uv sync --locked --all-groups" in commands
    assert (
        "uv run project-standards standards validate-graph --root . "
        "--require-all-manifests"
    ) in commands
    assert "uv run project-standards standards render-catalog --root . --check" in commands

    actual = _uses_steps(workflow)
    expected = _uses_steps(reusable_gate)
    for action in ("actions/checkout", "actions/setup-python", "astral-sh/setup-uv"):
        assert actual[action]["uses"] == expected[action]["uses"]
    assert actual["astral-sh/setup-uv"]["with"]["version"] == expected[
        "astral-sh/setup-uv"
    ]["with"]["version"]
```

- [ ] **Step 2: Run the test and verify it fails because the workflow is absent**

Run `uv run pytest tests/test_standards_graph_workflow.py -v`.

Expected: failure while reading `.github/workflows/validate-standards-graph.yml`.

- [ ] **Step 3: Create the dedicated workflow**

Create `.github/workflows/validate-standards-graph.yml`:

<!-- prettier-ignore -->
```yaml
name: Validate standards graph

on:
  pull_request:
  push:
    branches: ["main", "testing"]

permissions:
  contents: read

jobs:
  standards-graph:
    name: Standards graph and catalog
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - uses: actions/setup-python@v6
        with:
          python-version-file: ".python-version"

      - uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
        with:
          version: "0.11.6"
          enable-cache: true

      - name: Sync dependencies
        run: uv sync --locked --all-groups

      - name: Validate standards graph
        run: uv run project-standards standards validate-graph --root . --require-all-manifests

      - name: Check standards catalog freshness
        run: uv run project-standards standards render-catalog --root . --check
```

- [ ] **Step 4: Verify the workflow contract and live commands**

Run:

```bash
uv run pytest \
  tests/test_standards_graph_workflow.py \
  tests/test_standards_graph_cli.py \
  tests/test_standards_graph_catalog.py -q
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run project-standards standards render-catalog --root . --check
npx prettier --check .github/workflows/validate-standards-graph.yml
```

Expected: all tests pass, graph output is `OK standards graph`, and catalog output is `OK generated catalog`.

- [ ] **Step 5: Commit the repository-only gate**

```bash
git add .github/workflows/validate-standards-graph.yml tests/test_standards_graph_workflow.py
git diff --cached --check
git commit -m "ci(v5): validate standards graph on testing"
```

### Task 3: Reconcile Standard Bundle Authoring and manifest descriptions

**Files:**

- Modify: `standards/standard-bundle-authoring/README.md`
- Modify: `standards/standard-bundle-authoring/standard.toml`
- Modify: `standards/standard-bundle-authoring/templates/standard.toml`
- Modify: `src/project_standards/standard_manifest.py`
- Modify: `src/project_standards/schemas/standard.schema.json`

- [ ] **Step 1: Correct the current repository counts**

Replace “eight current bundles” and “six ship packaged adopt-artifact manifests” with “nine current bundles” and “seven ship packaged adopt-artifact manifests.” Preserve the distinction between seven released/staged standards and the two reference/unreleased bundles.

- [ ] **Step 2: Make ADRs 0017-0022 explicit contract owners**

Add concise links at the relevant rules:

- ADR 0017 for unified adoption modes and commands;
- ADR 0018 for package lifecycle;
- ADR 0019 for artifact parity and provenance;
- ADR 0020 for package versioning;
- ADR 0021 for project-local skill installation;
- ADR 0022 for project-local hook installation.

Add this checklist item immediately after `[resources]`:

```markdown
- [ ] Agent context — provide `agent-summary.md` and declare `resources.agent_summary` when useful; otherwise record the explicit rationale in the canonical README.
```

This records the FR-013 author decision without claiming the existing bundle gap is closed.

In `standards/standard-bundle-authoring/templates/standard.toml`, add the corresponding optional resource directly below `readme`:

```toml
# agent_summary = "agent-summary.md" # optional: compact view; otherwise explain omission in README
```

- [ ] **Step 3: Remove obsolete Step 04 future tense**

In `standards/standard-bundle-authoring/standard.toml`, replace the opening comment with:

```toml
# The machine manifest for the Standard Bundle Authoring Standard.
# This meta-standard dogfoods the contract it defines. It is internal/reference
# (adoption = "none"): no consumer config namespace, no authorities over consumer
# files, and no providers. The repository graph validator enforces the contract.
```

In `standard_manifest.py`, revise the module and class descriptions so they describe the current graph validator and current loader boundary. Remove all phrases that call Step 04 future work without changing runtime behavior or public names.

- [ ] **Step 4: Regenerate the schema after model-description changes**

Run:

```bash
uv run python -c "from pathlib import Path; from project_standards.standard_manifest import standard_schema_json; Path('src/project_standards/schemas/standard.schema.json').write_text(standard_schema_json(), encoding='utf-8')"
```

- [ ] **Step 5: Verify authoring and manifest coherence**

Run:

```bash
uv run pytest tests/test_standard_manifest.py tests/test_standards_graph_catalog.py -q
uv run project-standards standards validate-graph --root . --require-all-manifests
npx prettier --check standards/standard-bundle-authoring/README.md
npx markdownlint-cli2 --no-globs standards/standard-bundle-authoring/README.md
```

Expected: schema drift test, real-manifest tests, graph validation, and targeted Markdown checks pass.

- [ ] **Step 6: Commit authoring-contract reconciliation**

```bash
git add \
  standards/standard-bundle-authoring/README.md \
  standards/standard-bundle-authoring/standard.toml \
  standards/standard-bundle-authoring/templates/standard.toml \
  src/project_standards/standard_manifest.py \
  src/project_standards/schemas/standard.schema.json
git diff --cached --check
git commit -m "docs(v5): reconcile standard bundle authoring"
```

### Task 4: Reconcile SPEC-MT01 completion evidence

**Files:**

- Modify: `docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md`

- [ ] **Step 1: Update the Definition of Done from current evidence**

Check every §17.1 item except these Step-07 outcomes:

```markdown
- [ ] MCP-readiness report shows no blocking gaps.
- [ ] Documentation deliverables (§18.7) complete.
```

The documentation aggregate stays open because the readiness report/checklist deliverable remains open.

- [ ] **Step 2: Replace the §17.3 traceability matrix**

Use the following evidence and statuses:

```markdown
| Requirement ID | Test / Verification Method | Status |
| --- | --- | --- |
| FR-001 | `standards/standard-bundle-authoring/README.md`; graph validation; catalog includes `standard-bundle-authoring`. | Passing |
| FR-002 | `tests/test_standard_manifest.py::test_real_manifests_validate`; `tests/test_standards_graph_cli.py::test_current_repo_validate_graph_require_all_manifests_passes_after_retrofit`. | Passing |
| FR-003 | `tests/test_standards_graph_discovery.py::test_build_graph_loads_linked_artifact_manifest`; artifact-linkage tests in `tests/test_standards_graph_validators.py`. | Passing |
| FR-004 | `tests/test_standards_graph_validators.py::test_mutating_authority_conflict_is_error` and compatible-extension coverage. | Passing |
| FR-005 | `tests/test_standards_graph_validators.py::test_duplicate_config_namespace_is_error`. | Passing |
| FR-006 | Relationship, companion, capability, and platform-consumption tests in `tests/test_standards_graph_validators.py`. | Passing |
| FR-007 | Resource-path loader tests in `tests/test_standard_manifest.py` and provider-schema resource checks in `tests/test_standards_graph_validators.py`. | Passing |
| FR-008 | Lifecycle enum and version-consistency tests in `tests/test_standard_manifest.py`. | Passing |
| FR-009 | `tests/test_provider_runner.py`; provider declaration and resource checks in manifest/graph tests. | Passing |
| FR-010 | `tests/test_standards_graph_cli.py` human, JSON, load-error, and current-repository cases. | Passing |
| FR-011 | `.github/workflows/validate-standards-graph.yml`; `tests/test_standards_graph_workflow.py`. | Passing |
| FR-012 | Nine real `standards/*/standard.toml` files; `test_real_manifests_validate`; required-manifest graph gate. | Passing |
| FR-013 | Agent Handoff provides `agent-summary.md`; Python Coding records a rationale; the other active standards do not yet provide either. | Failing — non-blocking `Should` gap |
| FR-014 | `standards/catalog.md`; `tests/test_standards_graph_catalog.py`; `render-catalog --check`. | Passing |
| FR-015 | v5 manifest/graph migration posture is added with the release documents. | Blocked — migration note not yet committed |
| FR-016 | ADRs 0001-0013 are active and pass managed frontmatter/ADR validation. | Passing |
| FR-017 | Individual, pairwise, and all-standard coverage in `tests/test_standards_composition.py`. | Passing |
| FR-018 | `tests/test_adopt_dogfood.py` and `tests/test_standards_composition.py`. | Passing |
| FR-019 | Step 07 must produce the MCP-readiness report and no-blocker checklist. | Blocked — Step 07 deliverable |
| FR-020 | Standard Bundle Authoring exception rules; ADR-backed extension tests in `tests/test_standards_graph_validators.py`. | Passing |
| FR-021 | Companion, extension, hidden dependency, unknown target, and cycle tests in graph validation. | Passing |
| FR-022 | Relationship enums/schema; `tests/test_standard_manifest.py::test_relations_rejects_requires_key`. | Passing |
```

- [ ] **Step 3: Check only documentation deliverables with current evidence**

In §18.7, check the first six deliverables through the updated adopt guides. Leave both `UPGRADING.md / migration notes` and `MCP-readiness report template/checklist` unchecked until their evidence exists.

- [ ] **Step 4: Resolve settled open questions without erasing real choices**

Set these outcomes in §21:

- OQ-001 `Resolved`: canonical manifests live in `standards/{id}/`; only executable installed-wheel providers require a byte-identical runtime mirror.
- OQ-002 `Resolved`: keep `standard.toml` and `adopt.toml` separate and link them, per ADR 0003.
- OQ-003 `Resolved`: use validated dot-separated capability identifiers.
- OQ-004 `Resolved`: draft/reference manifests validate structurally without becoming adoptable.
- OQ-005 stays `Open` and non-blocking because FR-013 remains incomplete.
- OQ-006 becomes `Deferred`: explicit versions only; ranges require a demonstrated compatibility need.
- OQ-007 `Resolved`: no blocking graph findings, all manifests present, accepted core ADRs, fresh catalog, and Step-07 report.
- OQ-008 `Resolved`: independent package plus companion by default; `extends` only with explicit ADR metadata.

- [ ] **Step 5: Replace the placeholder deviation row**

Use:

```markdown
| ID | Spec Reference | Deviation | Reason | Approved? |
| --- | --- | --- | --- | --- |
| — | N/A | No implementation deviations recorded through Step 06. | Implemented behavior follows the accepted ADRs and requirements. | N/A |
```

- [ ] **Step 6: Validate the reconciled specification**

Run:

```bash
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
npx prettier --check docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
npx markdownlint-cli2 --no-globs docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
```

Expected: validation and strict lint pass; FR-013, FR-015, and FR-019 remain visible rather than being marked complete.

- [ ] **Step 7: Commit traceability reconciliation**

```bash
git add docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
git diff --cached --check
git commit -m "docs(v5): reconcile spec mt01 traceability"
```

### Task 5: Add v5 release and migration guidance

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `UPGRADING.md`
- Modify: `docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md`

- [ ] **Step 1: Add classified `[Unreleased]` entries**

Under `### Added`, add separate bullets for:

- Standard Bundle Authoring Standard and its nine-bundle authoring contract;
- the typed `standard.toml` model, generated schema, real-manifest retrofit, and provider runner;
- graph validation, individual/pairwise/all-standard composition proof, generated catalog, and the dedicated `testing`/`main` hosted workflow.

Under `### Changed`, state that seven artifact-bearing standards now link their `standard.toml` metadata plane to packaged `adopt.toml` manifests with validated provenance while non-adoptable bundles remain explicit.

- [ ] **Step 2: Add the v5 manifest/graph migration posture**

Set `UPGRADING.md` frontmatter `updated: '2026-07-10'`, add `standards/standard-bundle-authoring/README.md` to `related`, and add a section after the Agent Handoff preparation section with this contract:

````markdown
## Standard manifests and graph validation in v5.0.0

No action is required for ordinary consuming repositories. `standard.toml`, the standards graph, provider declarations, artifact-manifest links, composition fixtures, and `standards/catalog.md` describe and verify this repository's published standard packages; they do not add consumer configuration keys or silently adopt files.

Repositories that author or redistribute their own standard bundles must follow the [Standard Bundle Authoring Standard](standards/standard-bundle-authoring/README.md), provide a validated `standard.toml`, declare any packaged `adopt.toml` link and artifact provenance, and run:

```bash
project-standards standards validate-graph --root . --require-all-manifests
project-standards standards render-catalog --root . --check
```

Existing consumers continue to use their selected standard's `adopt.md`, config fragment, and reusable workflow. Re-pinning to v5 does not enable graph validation against the consumer repository unless that repository deliberately adopts the authoring contract.
````

- [ ] **Step 3: Promote FR-015 only after its evidence exists**

Replace the temporary FR-015 traceability row with:

```markdown
| FR-015 | `UPGRADING.md` v5 manifest/graph migration posture. | Passing |
```

Check the §18.7 `UPGRADING.md / migration notes` deliverable. Keep the MCP-readiness report/checklist deliverable and the aggregate §17.1 documentation item unchecked for Step 07.

- [ ] **Step 4: Verify changed release documents**

Run:

```bash
uv run project-standards validate --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
npx prettier --check \
  CHANGELOG.md \
  UPGRADING.md \
  docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
npx markdownlint-cli2 --no-globs \
  CHANGELOG.md \
  UPGRADING.md \
  docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
```

- [ ] **Step 5: Commit release guidance**

```bash
git add \
  CHANGELOG.md \
  UPGRADING.md \
  docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
git diff --cached --check
git commit -m "docs(v5): document standards graph migration"
```

### Task 6: Reconcile current plans, retirement inventory, and handoff pointers

**Files:**

- Modify: `docs/superpowers/plans/2026-07-09-dogfood-catalog-artifact-linkage.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/superpowers/research/2026-07-09-agent-handoff-retirement-inventory.md`

- [ ] **Step 1: Mark the implemented Step 06 plan accurately**

Change every Task 1-7 checkbox in `2026-07-09-dogfood-catalog-artifact-linkage.md` from `[ ]` to `[x]`. Do not alter task prose.

- [ ] **Step 2: Reconcile plan pointers**

In `docs/handoff/specs-plans.md`:

- correct the prune note and Storage bullet so they acknowledge retained v5 implementation plans;
- change the Step 05 count from eight to nine and remove the claim that Step 06 remains;
- replace Step 06 `this closeout` with `39b9f76`;
- mark this remediation plan as implemented with its commit range at closeout;
- retain Step 07 as the next work item.

- [ ] **Step 3: Reconcile the Agent Handoff retirement inventory**

Set frontmatter `updated: '2026-07-10'`. Change only the `project-standards` ledger row to state that migration and package adoption are integrated on `testing`, validation passes on `testing`, and the remaining repository-specific gate is v5 promotion plus published-artifact recheck. Do not alter other repository rows or claim engine deletion is unblocked.

- [ ] **Step 4: Validate the reconciled pointers**

Run:

```bash
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
uv run project-standards validate --config .project-standards.yml
```

Expected: no fatal findings; historical session-shape and instruction-size advisories may remain.

- [ ] **Step 5: Commit current-pointer reconciliation**

Stage only the three files named by this task and commit:

```bash
git add \
  docs/superpowers/plans/2026-07-09-dogfood-catalog-artifact-linkage.md \
  docs/handoff/specs-plans.md \
  docs/superpowers/research/2026-07-09-agent-handoff-retirement-inventory.md
git diff --cached --check
git commit -m "docs(v5): reconcile pre-step 07 handoff"
```

### Task 7: Run the complete gate and close the remediation tranche

**Files:**

- Modify: `docs/superpowers/plans/2026-07-10-pre-step-07-readiness-remediation.md`
- Modify: `docs/superpowers/specs/2026-07-10-pre-step-07-readiness-remediation-design.md`
- Modify: `docs/handoff/sessions/2026-07.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/STATUS.md`
- Modify: `docs/TODO.md`

- [ ] **Step 1: Install the locked Node dependencies for coherence checks**

Run `npm ci`.

Expected: install succeeds without modifying `package.json` or `package-lock.json`.

- [ ] **Step 2: Run focused feature verification**

```bash
uv run pytest tests/agent_handoff/test_policy.py tests/agent_handoff/test_validation.py -q
uv run pytest \
  tests/test_standards_graph_workflow.py \
  tests/test_standards_graph_cli.py \
  tests/test_standards_graph_catalog.py -q
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards render-catalog --root . --check
```

Expected: focused tests pass, graph JSON has zero findings, and the catalog is fresh.

- [ ] **Step 3: Run the complete Python and coherence gates**

```bash
uv run python scripts/check.py
uv run pytest tests/coherence -v
```

Expected: Ruff format/check, BasedPyright, pytest with coverage, coverage report, pip-audit, and all coherence tests pass.

- [ ] **Step 4: Run specification, managed Markdown, and handoff gates**

```bash
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
uv run project-standards validate --config .project-standards.yml
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
```

Expected: all commands exit zero. Advisory warnings are reported honestly and do not become errors.

- [ ] **Step 5: Run changed-Markdown hygiene without touching deferred drafts**

Build the explicit changed-Markdown file list from `git diff --name-only e5eccea..HEAD`, remove `docs/future-standards/**`, and run targeted Prettier and markdownlint. Do not run either formatter with `--write`.

- [ ] **Step 6: Append one compact correction/session row**

Append a new row to `docs/handoff/sessions/2026-07.md` that records:

- pre-Step-07 traceability and release-document reconciliation;
- the bug-index policy fix;
- the dedicated `testing`/`main` graph/catalog workflow;
- the actual commit range and final test count;
- that Step 07 remains next and owner-choice debt is still open.

Do not rewrite historical `this commit` or `this closeout` rows.

- [ ] **Step 7: Update current status, tasks, and completion markers**

In `docs/STATUS.md`, add the verified pre-Step-07 reconciliation outcome and hosted workflow posture while keeping Step 07 next. In the durable v5 tracker in `docs/TODO.md`:

- replace the Step 06 placeholder with commit `39b9f76`;
- add a checked 2026-07-10 pre-Step-07 remediation entry with the implementation commit range;
- keep Step 07 unchecked;
- preserve every user task, including the blank checkbox.

Mark every completed checkbox in this plan `[x]`. Update the design status line to:

```markdown
**Date:** 2026-07-10 **Status:** owner-approved; implementation complete **Author:** session 2026-07-10
```

Update the remediation row in `docs/handoff/specs-plans.md` from planned to implemented with the implementation commit range.

- [ ] **Step 8: Re-run handoff validation and review the complete diff**

```bash
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
git diff --check
git status --short --branch
```

Confirm that the only unrelated worktree changes are the owner-authored `docs/future-standards/` rename.

- [ ] **Step 9: Commit closeout facts**

```bash
git add \
  docs/superpowers/plans/2026-07-10-pre-step-07-readiness-remediation.md \
  docs/superpowers/specs/2026-07-10-pre-step-07-readiness-remediation-design.md \
  docs/handoff/sessions/2026-07.md \
  docs/handoff/specs-plans.md \
  docs/STATUS.md \
  docs/TODO.md
git diff --cached --check
git commit -m "docs(v5): close pre-step 07 remediation"
```

- [ ] **Step 10: Begin owner-choice questions one at a time**

After the no-input tranche is verified, ask in this order:

1. repair or explicitly exclude `docs/future-standards/**` from broad Markdown workflows;
2. whether FR-013 advisory summary/rationale debt blocks v5;
3. GitHub required-review and required-check ruleset adoption;
4. remote issue and pull-request cleanup;
5. root-artifact consolidation design;
6. instruction-file size warning cleanup;
7. machine-enforced bug-index sorting/completeness.

Do not begin Step 07 until the pre-Step-07 blockers and the owner's blocking decisions are resolved.
