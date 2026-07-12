# Standards Graph Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SPEC-MT01 Step 04: a standards graph loader, graph validator, and `project-standards standards validate-graph` CLI that validate authority, capability, resource, provider, namespace, and relationship rules, including hidden-dependency rejection.

**Architecture:** Add a focused `project_standards.standards_graph` package that converts existing `standard.toml` manifests into typed graph nodes, runs deterministic validators that return structured findings, and exposes both Python API and CLI entry points. The graph layer consumes the Step 03 `standard_manifest.py` loader; it does not retrofit real standards, generate indexes, or implement MCP.

**Tech Stack:** Python 3.14, stdlib dataclasses/pathlib/json/fnmatch, existing Pydantic `StandardManifest` model, argparse CLI, pytest + coverage, BasedPyright strict, Ruff.

---

## Source of Truth

- `TODO.md` Step 04: graph validator plus CLI.
- `docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md`:
  - FR-004 authority tuples.
  - FR-005 config namespace ownership.
  - FR-006 capabilities and relationships without hidden dependencies.
  - FR-007 resources.
  - FR-009 providers.
  - FR-010 graph validator.
  - FR-017 safe arbitrary co-adoption.
  - FR-021 hidden-dependency rejection.
  - IR-003 CLI shape and exit codes.
- `docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` Step 04 row.
- `standards/standard-bundle-authoring/README.md` authority, relationship, config namespace, resource, provider, and conformance rules.
- ADRs:
  - `docs/adr/adr-0002-manifest-first-standard-discovery.md`.
  - `docs/adr/adr-0004-authority-map-and-conflict-free-composition.md`.
  - `docs/adr/adr-0006-standard-provider-plugin-model.md`.
  - `docs/adr/adr-0007-standard-graph-validation-gate.md`.
  - `docs/adr/adr-0008-consumer-config-namespace-registry.md`.
  - `docs/adr/adr-0010-standard-resource-uris-and-index.md`.
  - `docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md`.

## Global Constraints

- **Step 04 only.** Do not retrofit existing standards with manifests; that is Step 05.
- **No MCP code.** This layer is future MCP input, not an MCP server.
- **No new runtime dependency.** Use stdlib `fnmatch` plus conservative glob overlap detection.
- **Current real repo must stay usable before Step 05.** The CLI supports `--require-all-manifests`; Step 04 tests exercise that rule with fixtures, but the default real-repo smoke test loads manifest-backed standards only so this plan can pass before retrofit.
- **Structured findings are stable.** Each finding includes `code`, `severity`, `standard_id`, `path`, `message`, and `hint`.
- **Exit codes:** valid graph = 0; graph findings = 1; invocation/config/load boundary errors = 2.
- **Hidden dependencies:** reject ambiguous dependency fields through Step 03 model errors; reject extension relationships that are undeclared, point to missing standards, form cycles, or lack an ADR resource.
- **Authority conflicts:** two mutating authorities conflict when they share `domain` and `concern`, have overlapping targets, and use different owners, unless an explicit `extends` relationship connects the involved standards.
- **Extension ADR scope:** Step 04 treats a bundle-local `extension_adr` resource on the extending standard as the machine-checkable proof that an `extends` edge is ADR-backed. Per-edge ADR attribution is deferred unless the manifest schema grows a dedicated relation object later.
- **Commit style:** use `feat(v5):`, `test(v5):`, and `docs(v5):`; branch remains `testing`.
- **Full gate at close:** `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run coverage run -m pytest`, `uv run coverage report`, `uv run pip-audit`, `uv run pytest tests/coherence`, `npx --no-install prettier --check .`, `npx --no-install markdownlint-cli2 "**/*.md"`, `uv run validate-frontmatter --config .project-standards.yml`, `uv run project-standards spec validate --config .project-standards.yml`, and `uv run project-standards spec lint --config .project-standards.yml --strict`.

## File Structure

- **Create** `src/project_standards/standards_graph/__init__.py` — public exports for graph loading, validation, and findings.
- **Create** `src/project_standards/standards_graph/model.py` — immutable graph dataclasses, finding shape, JSON/human rendering helpers.
- **Create** `src/project_standards/standards_graph/discovery.py` — standards directory discovery and manifest loading.
- **Create** `src/project_standards/standards_graph/validators.py` — pure validation functions for namespace, resource, provider, authority, capability, and relationship rules.
- **Create** `src/project_standards/standards_graph/cli.py` — nested `standards validate-graph` command group.
- **Modify** `src/project_standards/cli.py` — dispatch `project-standards standards ...` and advertise it in help.
- **Create** `tests/standards_graph_helpers.py` — fixture-writing helpers used only by graph tests.
- **Create** `tests/test_standards_graph_model.py` — finding and graph model tests.
- **Create** `tests/test_standards_graph_discovery.py` — manifest discovery/load tests.
- **Create** `tests/test_standards_graph_validators.py` — graph rule tests.
- **Create** `tests/test_standards_graph_cli.py` — CLI behavior and exit-code tests.
- **Modify** `docs/handoff/specs-plans.md` — add this Step 04 plan row.

## Public Interfaces

```python
from pathlib import Path

from project_standards.standards_graph import (
    GraphFinding,
    StandardsGraph,
    build_graph,
    validate_graph,
)

graph = build_graph(Path.cwd())
findings = validate_graph(graph)
```

```bash
project-standards standards validate-graph
project-standards standards validate-graph --json
project-standards standards validate-graph --root /path/to/repo
project-standards standards validate-graph --require-all-manifests
```

---

### Task 1: Graph Model and Finding Shape

**Files:**

- Create: `src/project_standards/standards_graph/__init__.py`
- Create: `src/project_standards/standards_graph/model.py`
- Test: `tests/test_standards_graph_model.py`

**Interfaces:**

- Produces `GraphFinding`, `StandardNode`, `StandardsGraph`, `finding_sort_key`, `sort_findings`, `findings_to_jsonable`, and `format_findings`.
- No filesystem access in this task.

- [ ] **Step 1: Write failing model tests.**

```python
# tests/test_standards_graph_model.py
from __future__ import annotations

import json
from pathlib import Path

from project_standards.standard_manifest import StandardManifest
from project_standards.standards_graph.model import (
    GraphFinding,
    StandardNode,
    StandardsGraph,
    findings_to_jsonable,
    format_findings,
    sort_findings,
)


def _manifest(standard_id: str) -> StandardManifest:
    return StandardManifest.model_validate(
        {
            "standard": {
                "id": standard_id,
                "name": standard_id.title(),
                "status": "active",
                "summary": "Example standard.",
                "adoption": "none",
            },
            "versions": {"supported": [], "latest": ""},
            "config": {"namespaces": []},
            "capabilities": {"provides": [], "consumes_platform": []},
            "relations": {"companions": [], "extends": [], "conflicts": []},
            "resources": {"readme": "README.md"},
        }
    )


def test_finding_json_shape_is_stable() -> None:
    finding = GraphFinding(
        code="SG-CONFIG-DUPLICATE-NAMESPACE",
        severity="error",
        standard_id="alpha",
        path="standards/alpha/standard.toml",
        message="namespace 'spec' is claimed by alpha and beta",
        hint="choose one owning standard for namespace 'spec'",
    )

    payload = findings_to_jsonable([finding])

    assert payload == [
        {
            "code": "SG-CONFIG-DUPLICATE-NAMESPACE",
            "severity": "error",
            "standard_id": "alpha",
            "path": "standards/alpha/standard.toml",
            "message": "namespace 'spec' is claimed by alpha and beta",
            "hint": "choose one owning standard for namespace 'spec'",
        }
    ]
    assert json.loads(json.dumps(payload)) == payload


def test_human_format_includes_rule_standard_path_and_hint() -> None:
    finding = GraphFinding(
        code="SG-REL-MISSING-STANDARD",
        severity="error",
        standard_id="alpha",
        path="standards/alpha/standard.toml",
        message="alpha companion 'missing' is not a known standard",
        hint="declare only existing standard ids in relations",
    )

    text = format_findings([finding])

    assert "[SG-REL-MISSING-STANDARD]" in text
    assert "alpha" in text
    assert "standards/alpha/standard.toml" in text
    assert "declare only existing standard ids" in text


def test_graph_indexes_nodes_by_standard_id() -> None:
    alpha = StandardNode(
        standard_id="alpha",
        bundle_dir=Path("standards/alpha"),
        manifest_path=Path("standards/alpha/standard.toml"),
        manifest=_manifest("alpha"),
    )
    graph = StandardsGraph(root=Path("."), standards=(alpha,), missing_manifest_dirs=())

    assert graph.ids == frozenset({"alpha"})
    assert graph.by_id["alpha"] is alpha


def test_ownerless_findings_sort_without_type_error() -> None:
    findings = [
        GraphFinding(
            code="SG-Z",
            severity="error",
            standard_id="alpha",
            path="standards/alpha/standard.toml",
            message="z",
            hint="fix z",
        ),
        GraphFinding(
            code="SG-A",
            severity="error",
            standard_id="",
            path=".",
            message="a",
            hint="fix a",
        ),
    ]

    assert [finding.code for finding in sort_findings(findings)] == ["SG-A", "SG-Z"]
    assert [entry["code"] for entry in findings_to_jsonable(findings)] == ["SG-A", "SG-Z"]
```

- [ ] **Step 2: Run the tests and verify they fail.**

Run: `uv run pytest tests/test_standards_graph_model.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'project_standards.standards_graph'`.

- [ ] **Step 3: Create the package and model implementation.**

```python
# src/project_standards/standards_graph/model.py
"""Typed standards graph data structures and finding renderers."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from project_standards.standard_manifest import StandardManifest

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class GraphFinding:
    """A deterministic standards-graph validation finding."""

    code: str
    severity: Severity
    standard_id: str
    path: str
    message: str
    hint: str


@dataclass(frozen=True)
class StandardNode:
    """One loaded standard bundle in the graph."""

    standard_id: str
    bundle_dir: Path
    manifest_path: Path
    manifest: StandardManifest


@dataclass(frozen=True)
class StandardsGraph:
    """Loaded standards plus discovery metadata for graph-wide checks."""

    root: Path
    standards: tuple[StandardNode, ...]
    missing_manifest_dirs: tuple[Path, ...]

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(node.standard_id for node in self.standards)

    @property
    def by_id(self) -> dict[str, StandardNode]:
        return {node.standard_id: node for node in self.standards}


def finding_sort_key(finding: GraphFinding) -> tuple[str, str, str, str]:
    return (finding.code, finding.standard_id, finding.path, finding.message)


def sort_findings(findings: list[GraphFinding]) -> list[GraphFinding]:
    """Return findings in deterministic report order."""
    return sorted(findings, key=finding_sort_key)


def findings_to_jsonable(findings: list[GraphFinding]) -> list[dict[str, object]]:
    """Return findings in the stable CLI JSON shape."""
    return [dataclasses.asdict(finding) for finding in sort_findings(findings)]


def format_findings(findings: list[GraphFinding]) -> str:
    """Render findings for humans."""
    if not findings:
        return "OK standards graph"
    lines: list[str] = []
    for finding in sort_findings(findings):
        owner = f"{finding.standard_id}: " if finding.standard_id else ""
        lines.append(f"{finding.severity.upper()} [{finding.code}] {owner}{finding.message}")
        lines.append(f"  path: {finding.path}")
        lines.append(f"  hint: {finding.hint}")
    return "\n".join(lines)
```

```python
# src/project_standards/standards_graph/__init__.py
"""Standards graph loading and validation APIs."""

from project_standards.standards_graph.model import (
    GraphFinding,
    StandardNode,
    StandardsGraph,
    finding_sort_key,
    findings_to_jsonable,
    format_findings,
    sort_findings,
)

__all__ = [
    "GraphFinding",
    "StandardNode",
    "StandardsGraph",
    "finding_sort_key",
    "findings_to_jsonable",
    "format_findings",
    "sort_findings",
]
```

- [ ] **Step 4: Run tests and verify they pass.**

Run: `uv run pytest tests/test_standards_graph_model.py -q`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standards_graph tests/test_standards_graph_model.py
git commit -m "feat(v5): add standards graph model and findings"
```

---

### Task 2: Test Fixture Writer

**Files:**

- Create: `tests/standards_graph_helpers.py`
- Test: `tests/test_standards_graph_discovery.py`

**Interfaces:**

- Produces `write_standard(root, standard_id, ...) -> Path`.
- Used by later graph tests to create realistic `standards/{id}/standard.toml` bundles.

- [ ] **Step 1: Write the helper and its failing discovery-side smoke test.**

```python
# tests/standards_graph_helpers.py
from __future__ import annotations

from pathlib import Path


def write_standard(
    root: Path,
    standard_id: str,
    *,
    namespaces: list[str] | None = None,
    provides: list[str] | None = None,
    consumes_platform: list[str] | None = None,
    companions: list[str] | None = None,
    extends: list[str] | None = None,
    conflicts: list[str] | None = None,
    resources: dict[str, str] | None = None,
    relation_extras: dict[str, list[str]] | None = None,
    authorities: list[dict[str, object]] | None = None,
    providers: list[dict[str, object]] | None = None,
    adoption: str = "none",
    extra_toml: str = "",
) -> Path:
    bundle = root / "standards" / standard_id
    bundle.mkdir(parents=True)
    (bundle / "README.md").write_text(f"# {standard_id}\n", encoding="utf-8")
    resource_map = {"readme": "README.md", **(resources or {})}
    for rel_path in resource_map.values():
        target = bundle / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(f"# {rel_path}\n", encoding="utf-8")

    def _array(values: list[str] | None) -> str:
        return "[" + ", ".join(f'"{value}"' for value in (values or [])) + "]"

    text = f"""[standard]
id = "{standard_id}"
name = "{standard_id.title()}"
status = "active"
summary = "Example standard."
adoption = "{adoption}"

[versions]
supported = []
latest = ""

[config]
namespaces = {_array(namespaces)}

[capabilities]
provides = {_array(provides)}
consumes_platform = {_array(consumes_platform)}

[relations]
companions = {_array(companions)}
extends = {_array(extends)}
conflicts = {_array(conflicts)}
"""
    for key, value in (relation_extras or {}).items():
        text += f"{key} = {_array(value)}\n"
    text += """
[resources]
"""
    for key, value in resource_map.items():
        text += f'{key} = "{value}"\n'
    for authority in authorities or []:
        text += "\n[[authority]]\n"
        text += f'domain = "{authority["domain"]}"\n'
        text += f'target = "{authority["target"]}"\n'
        text += f'concern = "{authority["concern"]}"\n'
        text += f'owner = "{authority["owner"]}"\n'
        text += f"mutates = {str(authority['mutates']).lower()}\n"
    for provider in providers or []:
        text += "\n[[providers]]\n"
        text += f'operation = "{provider["operation"]}"\n'
        text += f'kind = "{provider["kind"]}"\n'
        if provider.get("entrypoint") is not None:
            text += f'entrypoint = "{provider["entrypoint"]}"\n'
        if provider.get("input_schema") is not None:
            text += f'input_schema = "{provider["input_schema"]}"\n'
        if provider.get("output_schema") is not None:
            text += f'output_schema = "{provider["output_schema"]}"\n'
        text += f"optional = {str(provider['optional']).lower()}\n"
    text += extra_toml

    manifest = bundle / "standard.toml"
    manifest.write_text(text, encoding="utf-8")
    return bundle
```

```python
# tests/test_standards_graph_discovery.py
from __future__ import annotations

from pathlib import Path

from tests.standards_graph_helpers import write_standard


def test_write_standard_helper_creates_loadable_shape(tmp_path: Path) -> None:
    bundle = write_standard(tmp_path, "alpha", namespaces=["alpha"])

    assert (bundle / "README.md").is_file()
    assert (bundle / "standard.toml").read_text(encoding="utf-8").startswith("[standard]")
```

- [ ] **Step 2: Run the helper smoke test.**

Run: `uv run pytest tests/test_standards_graph_discovery.py::test_write_standard_helper_creates_loadable_shape -q`

Expected: PASS.

- [ ] **Step 3: Commit.**

```bash
git add tests/standards_graph_helpers.py tests/test_standards_graph_discovery.py
git commit -m "test(v5): add standards graph fixture writer"
```

---

### Task 3: Discovery and Graph Loading

**Files:**

- Create: `src/project_standards/standards_graph/discovery.py`
- Modify: `src/project_standards/standards_graph/__init__.py`
- Modify: `tests/test_standards_graph_discovery.py`

**Interfaces:**

- Produces `discover_standard_dirs(root)`, `discover_manifest_paths(root)`, and `build_graph(root)`.
- Loader wraps `StandardManifestError` into findings later; this task lets invalid manifests raise so tests can prove the boundary in Task 8.

- [ ] **Step 1: Add failing discovery tests.**

First add these names to the import block at the **top** of `tests/test_standards_graph_discovery.py` (keep every import at the top — the repo enforces Ruff `E402`, which is not autofixable, so an import placed after a `def` fails the close gate):

```python
from project_standards.standards_graph.discovery import (
    build_graph,
    discover_manifest_paths,
    discover_standard_dirs,
)
```

Then append the tests:

```python
# append to tests/test_standards_graph_discovery.py


def test_discover_standard_dirs_ignores_non_directories(tmp_path: Path) -> None:
    write_standard(tmp_path, "beta")
    (tmp_path / "standards" / "README.md").write_text("# index\n", encoding="utf-8")

    assert discover_standard_dirs(tmp_path) == [tmp_path / "standards" / "beta"]


def test_discover_manifest_paths_are_sorted(tmp_path: Path) -> None:
    write_standard(tmp_path, "zeta")
    write_standard(tmp_path, "alpha")

    assert [path.parent.name for path in discover_manifest_paths(tmp_path)] == ["alpha", "zeta"]


def test_build_graph_loads_manifest_nodes_and_missing_dirs(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha")
    missing = tmp_path / "standards" / "beta"
    missing.mkdir(parents=True)
    (missing / "README.md").write_text("# beta\n", encoding="utf-8")

    graph = build_graph(tmp_path)

    assert [node.standard_id for node in graph.standards] == ["alpha"]
    assert graph.missing_manifest_dirs == (missing,)


```

- [ ] **Step 2: Run the discovery tests and verify they fail.**

Run: `uv run pytest tests/test_standards_graph_discovery.py -q`

Expected: FAIL with `ModuleNotFoundError: project_standards.standards_graph.discovery`.

- [ ] **Step 3: Implement discovery.**

```python
# src/project_standards/standards_graph/discovery.py
"""Discover standard bundles and load them into a standards graph."""

from __future__ import annotations

from pathlib import Path

from project_standards.standard_manifest import load_standard_manifest
from project_standards.standards_graph.model import StandardNode, StandardsGraph


def discover_standard_dirs(root: Path) -> list[Path]:
    """Return sorted `standards/{id}` directories under root."""
    standards_dir = root / "standards"
    if not standards_dir.is_dir():
        return []
    return sorted(path for path in standards_dir.iterdir() if path.is_dir())


def discover_manifest_paths(root: Path) -> list[Path]:
    """Return sorted manifest paths under `standards/*/standard.toml`."""
    return [path / "standard.toml" for path in discover_standard_dirs(root) if (path / "standard.toml").is_file()]


def build_graph(root: Path) -> StandardsGraph:
    """Load manifest-backed standards from root."""
    resolved_root = root.resolve()
    nodes: list[StandardNode] = []
    missing_manifest_dirs: list[Path] = []
    for bundle_dir in discover_standard_dirs(resolved_root):
        manifest_path = bundle_dir / "standard.toml"
        if not manifest_path.is_file():
            missing_manifest_dirs.append(bundle_dir)
            continue
        manifest = load_standard_manifest(manifest_path)
        standard_id = manifest.standard.id
        nodes.append(
            StandardNode(
                standard_id=standard_id,
                bundle_dir=bundle_dir,
                manifest_path=manifest_path,
                manifest=manifest,
            )
        )
    return StandardsGraph(
        root=resolved_root,
        standards=tuple(sorted(nodes, key=lambda node: node.standard_id)),
        missing_manifest_dirs=tuple(sorted(missing_manifest_dirs)),
    )
```

```python
# append exports in src/project_standards/standards_graph/__init__.py
from project_standards.standards_graph.discovery import (
    build_graph,
    discover_manifest_paths,
    discover_standard_dirs,
)

__all__ += [
    "build_graph",
    "discover_manifest_paths",
    "discover_standard_dirs",
]
```

- [ ] **Step 4: Run discovery tests.**

Run: `uv run pytest tests/test_standards_graph_discovery.py -q`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standards_graph tests/test_standards_graph_discovery.py
git commit -m "feat(v5): load standard manifests into a graph"
```

---

### Task 4: Namespace, Resource, Provider, and Missing-Manifest Validators

**Files:**

- Create: `src/project_standards/standards_graph/validators.py`
- Modify: `src/project_standards/standards_graph/__init__.py`
- Test: `tests/test_standards_graph_validators.py`

**Interfaces:**

- Produces `validate_graph(graph, require_all_manifests=False) -> list[GraphFinding]`.
- Rule codes:
  - `SG-MANIFEST-MISSING`
  - `SG-CONFIG-DUPLICATE-NAMESPACE`
  - `SG-RESOURCE-ADOPT-MISSING`
  - `SG-PROVIDER-SCHEMA-MISSING`

- [ ] **Step 1: Write failing validator tests.**

```python
# tests/test_standards_graph_validators.py
from __future__ import annotations

from pathlib import Path

from tests.standards_graph_helpers import write_standard

from project_standards.standards_graph.discovery import build_graph
from project_standards.standards_graph.validators import validate_graph


def _codes(root: Path, *, require_all_manifests: bool = False) -> set[str]:
    return {finding.code for finding in validate_graph(build_graph(root), require_all_manifests=require_all_manifests)}


def test_duplicate_config_namespace_is_error(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", namespaces=["markdown.frontmatter"])
    write_standard(tmp_path, "beta", namespaces=["markdown.frontmatter"])

    findings = validate_graph(build_graph(tmp_path))

    assert [(f.code, f.standard_id) for f in findings] == [
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "alpha"),
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "beta"),
    ]


def test_validate_graph_returns_multiple_findings_in_stable_order(tmp_path: Path) -> None:
    write_standard(tmp_path, "beta", namespaces=["duplicate"], adoption="copy-adopt")
    write_standard(tmp_path, "alpha", namespaces=["duplicate"], adoption="copy-adopt")

    findings = validate_graph(build_graph(tmp_path))

    assert [(finding.code, finding.standard_id) for finding in findings] == [
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "alpha"),
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "beta"),
        ("SG-RESOURCE-ADOPT-MISSING", "alpha"),
        ("SG-RESOURCE-ADOPT-MISSING", "beta"),
    ]


def test_missing_manifest_is_optional_until_retrofit_gate(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha")
    missing = tmp_path / "standards" / "beta"
    missing.mkdir(parents=True)
    (missing / "README.md").write_text("# beta\n", encoding="utf-8")

    assert "SG-MANIFEST-MISSING" not in _codes(tmp_path)
    assert "SG-MANIFEST-MISSING" in _codes(tmp_path, require_all_manifests=True)


def test_adoptable_standard_requires_adopt_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "copyable", adoption="copy-adopt")

    assert "SG-RESOURCE-ADOPT-MISSING" in _codes(tmp_path)


def test_provider_schema_resources_must_exist_when_declared(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "alpha",
        resources={"schema": "schemas/out.json"},
        providers=[
            {
                "operation": "validate",
                "kind": "python",
                "entrypoint": "pkg.mod:validate",
                "optional": False,
                "output_schema": "missing_schema",
            }
        ],
    )

    assert "SG-PROVIDER-SCHEMA-MISSING" in _codes(tmp_path)
```

- [ ] **Step 2: Run validator tests and verify they fail.**

Run: `uv run pytest tests/test_standards_graph_validators.py -q`

Expected: FAIL with `ModuleNotFoundError: project_standards.standards_graph.validators`.

- [ ] **Step 3: Implement the first validator layer.**

```python
# src/project_standards/standards_graph/validators.py
"""Validate graph-wide standard metadata rules."""

from __future__ import annotations

from collections import defaultdict

from project_standards.standard_manifest import AdoptionMode
from project_standards.standards_graph.model import GraphFinding, StandardNode, StandardsGraph, sort_findings


def _rel(path: object) -> str:
    return str(path)


def _finding(
    code: str,
    node: StandardNode,
    path: str,
    message: str,
    hint: str,
) -> GraphFinding:
    return GraphFinding(
        code=code,
        severity="error",
        standard_id=node.standard_id,
        path=path,
        message=message,
        hint=hint,
    )


def _validate_missing_manifests(graph: StandardsGraph, require_all_manifests: bool) -> list[GraphFinding]:
    if not require_all_manifests:
        return []
    return [
        GraphFinding(
            code="SG-MANIFEST-MISSING",
            severity="error",
            standard_id=path.name,
            path=_rel(path),
            message=f"standard directory {path.name!r} has no standard.toml",
            hint="add a standard.toml manifest or remove the standard directory",
        )
        for path in graph.missing_manifest_dirs
    ]


def _validate_namespaces(graph: StandardsGraph) -> list[GraphFinding]:
    owners: dict[str, list[StandardNode]] = defaultdict(list)
    for node in graph.standards:
        for namespace in node.manifest.config.namespaces:
            owners[namespace].append(node)

    findings: list[GraphFinding] = []
    for namespace, nodes in sorted(owners.items()):
        if len(nodes) < 2:
            continue
        ids = ", ".join(node.standard_id for node in nodes)
        for node in nodes:
            findings.append(
                _finding(
                    "SG-CONFIG-DUPLICATE-NAMESPACE",
                    node,
                    _rel(node.manifest_path),
                    f"namespace {namespace!r} is claimed by multiple standards: {ids}",
                    f"choose one owning standard for namespace {namespace!r}",
                )
            )
    return findings


def _validate_resources_and_providers(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    for node in graph.standards:
        resources = node.manifest.resources.as_dict()
        if node.manifest.standard.adoption is not AdoptionMode.NONE and "adopt" not in resources:
            findings.append(
                _finding(
                    "SG-RESOURCE-ADOPT-MISSING",
                    node,
                    _rel(node.manifest_path),
                    f"{node.standard_id} is adoptable but has no 'adopt' resource",
                    "add adopt = \"adopt.md\" to [resources] or change adoption to none",
                )
            )
        for provider in node.manifest.providers:
            for field_name, resource_id in (
                ("input_schema", provider.input_schema),
                ("output_schema", provider.output_schema),
            ):
                if resource_id is not None and resource_id not in resources:
                    findings.append(
                        _finding(
                            "SG-PROVIDER-SCHEMA-MISSING",
                            node,
                            _rel(node.manifest_path),
                            f"provider {provider.operation!r} references {field_name} resource {resource_id!r} that is not declared",
                            "declare the schema in [resources] or remove the provider schema reference",
                        )
                    )
    return findings


def validate_graph(graph: StandardsGraph, *, require_all_manifests: bool = False) -> list[GraphFinding]:
    """Return deterministic graph validation findings."""
    findings: list[GraphFinding] = []
    findings.extend(_validate_missing_manifests(graph, require_all_manifests))
    findings.extend(_validate_namespaces(graph))
    findings.extend(_validate_resources_and_providers(graph))
    return sort_findings(findings)
```

```python
# append exports in src/project_standards/standards_graph/__init__.py
from project_standards.standards_graph.validators import validate_graph

__all__ += ["validate_graph"]
```

- [ ] **Step 4: Run validator tests.**

Run: `uv run pytest tests/test_standards_graph_validators.py -q`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standards_graph tests/standards_graph_helpers.py tests/test_standards_graph_validators.py
git commit -m "feat(v5): validate graph namespaces resources and providers"
```

---

### Task 5: Authority Conflict Validator

**Files:**

- Modify: `src/project_standards/standards_graph/validators.py`
- Modify: `tests/test_standards_graph_validators.py`

**Interfaces:**

- Adds `SG-AUTHORITY-CONFLICT`.
- Uses `targets_may_overlap(left, right)` helper:
  - identical targets overlap;
  - `**/*` overlaps every target;
  - exact file names are checked with `fnmatch`;
  - recursive extension globs with the same suffix overlap;
  - literal files with the same suffix as a recursive extension glob overlap.

- [ ] **Step 1: Add failing authority tests.**

Extend the `validators` import at the **top** of `tests/test_standards_graph_validators.py` so it reads (keep imports at the top for Ruff `E402`):

```python
from project_standards.standards_graph.validators import targets_may_overlap, validate_graph
```

Then append the tests:

```python
# append to tests/test_standards_graph_validators.py


def test_mutating_authority_conflict_is_error(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "alpha",
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "prettier",
                "mutates": True,
            }
        ],
    )
    write_standard(
        tmp_path,
        "beta",
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "otherfmt",
                "mutates": True,
            }
        ],
    )

    assert "SG-AUTHORITY-CONFLICT" in _codes(tmp_path)


def test_non_mutating_authorities_do_not_conflict(tmp_path: Path) -> None:
    authority = {
        "domain": "markdown",
        "target": "**/*.md",
        "concern": "structure-lint",
        "owner": "markdownlint",
        "mutates": False,
    }
    write_standard(tmp_path, "alpha", authorities=[authority])
    write_standard(tmp_path, "beta", authorities=[{**authority, "owner": "custom-lint"}])

    assert "SG-AUTHORITY-CONFLICT" not in _codes(tmp_path)


def test_extends_relation_allows_compatible_authority_overlap(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "base",
        resources={"extension_adr": "resources/extension-adr.md"},
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "prettier",
                "mutates": True,
            }
        ],
    )
    write_standard(
        tmp_path,
        "child",
        resources={"extension_adr": "resources/extension-adr.md"},
        extends=["base"],
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "otherfmt",
                "mutates": True,
            }
        ],
    )

    assert "SG-AUTHORITY-CONFLICT" not in _codes(tmp_path)


def test_target_overlap_catches_literal_file_inside_recursive_extension_glob() -> None:
    assert targets_may_overlap("pyproject.toml", "**/*.toml") is True
    assert targets_may_overlap("README.md", "**/*.toml") is False


def test_mutating_authority_conflict_detects_literal_file_against_recursive_glob(
    tmp_path: Path,
) -> None:
    write_standard(
        tmp_path,
        "alpha",
        authorities=[
            {
                "domain": "python",
                "target": "pyproject.toml",
                "concern": "tool-config",
                "owner": "uv",
                "mutates": True,
            }
        ],
    )
    write_standard(
        tmp_path,
        "beta",
        authorities=[
            {
                "domain": "python",
                "target": "**/*.toml",
                "concern": "tool-config",
                "owner": "other-tool",
                "mutates": True,
            }
        ],
    )

    assert "SG-AUTHORITY-CONFLICT" in _codes(tmp_path)
```

- [ ] **Step 2: Run the authority tests and verify they fail.**

Run: `uv run pytest tests/test_standards_graph_validators.py -q`

Expected: FAIL because `SG-AUTHORITY-CONFLICT` is not produced yet.

- [ ] **Step 3: Implement authority conflict detection.**

```python
# add imports in validators.py
import fnmatch
from itertools import combinations


def _extension_connects(left: StandardNode, right: StandardNode) -> bool:
    return (
        right.standard_id in left.manifest.relations.extends
        or left.standard_id in right.manifest.relations.extends
    )


def _target_suffix(pattern: str) -> str | None:
    prefix = "**/*"
    if pattern.startswith(prefix) and len(pattern) > len(prefix):
        return pattern[len(prefix) :]
    return None


def _literal_has_suffix(pattern: str, suffix: str) -> bool:
    return not any(ch in pattern for ch in "*?[]") and pattern.endswith(suffix)


def targets_may_overlap(left: str, right: str) -> bool:
    """Return True when two consumer-file glob targets have an obvious intersection."""
    if left == right or left in {"**/*", "**/*.*"} or right in {"**/*", "**/*.*"}:
        return True
    if fnmatch.fnmatch(left, right) or fnmatch.fnmatch(right, left):
        return True
    left_suffix = _target_suffix(left)
    right_suffix = _target_suffix(right)
    if left_suffix is not None and right_suffix is not None:
        return left_suffix == right_suffix
    if left_suffix is not None:
        return _literal_has_suffix(right, left_suffix)
    if right_suffix is not None:
        return _literal_has_suffix(left, right_suffix)
    return False


def _validate_authorities(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    authority_rows = [
        (node, authority)
        for node in graph.standards
        for authority in node.manifest.authority
        if authority.mutates
    ]
    for (left_node, left), (right_node, right) in combinations(authority_rows, 2):
        if left_node.standard_id == right_node.standard_id:
            continue
        if left.domain != right.domain or left.concern != right.concern:
            continue
        if left.owner == right.owner:
            continue
        if not targets_may_overlap(left.target, right.target):
            continue
        if _extension_connects(left_node, right_node):
            continue
        for node, other in ((left_node, right_node), (right_node, left_node)):
            findings.append(
                _finding(
                    "SG-AUTHORITY-CONFLICT",
                    node,
                    _rel(node.manifest_path),
                    f"{node.standard_id} authority conflicts with {other.standard_id} for {left.domain}/{left.concern}",
                    "use one owner, split target globs, or declare an ADR-backed extends relationship",
                )
            )
    return findings
```

Add the call:

```python
    findings.extend(_validate_authorities(graph))
```

- [ ] **Step 4: Run validator tests.**

Run: `uv run pytest tests/test_standards_graph_validators.py -q`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standards_graph/validators.py tests/test_standards_graph_validators.py
git commit -m "feat(v5): detect standards authority conflicts"
```

---

### Task 6: Relationship and Capability Validator

**Files:**

- Modify: `src/project_standards/standards_graph/validators.py`
- Modify: `tests/test_standards_graph_validators.py`

**Interfaces:**

- Adds:
  - `SG-REL-MISSING-STANDARD`
  - `SG-REL-EXTENDS-CYCLE`
  - `SG-REL-EXTENDS-NO-ADR`
  - `SG-CAPABILITY-PLATFORM-UNKNOWN`
  - `SG-CAPABILITY-STANDARD-CONSUMED`

- [ ] **Step 1: Add failing relationship and capability tests.**

```python
# append to tests/test_standards_graph_validators.py

def test_relationships_must_point_to_known_standards(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", companions=["missing"], extends=["also-missing"], conflicts=["gone"])

    assert "SG-REL-MISSING-STANDARD" in _codes(tmp_path)


def test_extends_cycle_is_error(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", extends=["beta"], resources={"extension_adr": "resources/extension-adr.md"})
    write_standard(tmp_path, "beta", extends=["alpha"], resources={"extension_adr": "resources/extension-adr.md"})

    assert "SG-REL-EXTENDS-CYCLE" in _codes(tmp_path)


def test_extends_requires_adr_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "base")
    write_standard(tmp_path, "child", extends=["base"])

    assert "SG-REL-EXTENDS-NO-ADR" in _codes(tmp_path)


def test_extends_accepts_bundle_local_adr_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "base")
    write_standard(tmp_path, "child", extends=["base"], resources={"extension_adr": "resources/extension-adr.md"})

    assert "SG-REL-EXTENDS-NO-ADR" not in _codes(tmp_path)


def test_extends_requires_exact_extension_adr_resource_id(tmp_path: Path) -> None:
    write_standard(tmp_path, "base")
    write_standard(tmp_path, "child", extends=["base"], resources={"adr_notes": "resources/extension-adr.md"})

    assert "SG-REL-EXTENDS-NO-ADR" in _codes(tmp_path)


def test_consumes_platform_must_not_name_standard_capability(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", provides=["markdown.format"])
    write_standard(tmp_path, "beta", consumes_platform=["markdown.format"])

    assert "SG-CAPABILITY-STANDARD-CONSUMED" in _codes(tmp_path)


def test_consumes_platform_allows_known_platform_capability(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", consumes_platform=["project-standards.validate"])

    assert "SG-CAPABILITY-PLATFORM-UNKNOWN" not in _codes(tmp_path)
```

- [ ] **Step 2: Run the tests and verify they fail.**

Run: `uv run pytest tests/test_standards_graph_validators.py -q`

Expected: FAIL because relationship and capability findings are not emitted yet.

- [ ] **Step 3: Implement relationship validation.**

```python
# add near top of validators.py
_PLATFORM_CAPABILITIES = frozenset(
    {
        "project-standards.validate",
        "project-standards.fix",
        "project-standards.drift-check",
        "project-standards.id-next",
        "project-standards.extract",
        "project-standards.render",
    }
)


def _has_extension_adr_resource(node: StandardNode) -> bool:
    resources = node.manifest.resources.as_dict()
    return "extension_adr" in resources


def _validate_relationship_targets(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    ids = graph.ids
    for node in graph.standards:
        relation_map = {
            "companions": node.manifest.relations.companions,
            "extends": node.manifest.relations.extends,
            "conflicts": node.manifest.relations.conflicts,
        }
        for relation_name, targets in relation_map.items():
            for target in targets:
                if target not in ids:
                    findings.append(
                        _finding(
                            "SG-REL-MISSING-STANDARD",
                            node,
                            _rel(node.manifest_path),
                            f"{relation_name} target {target!r} is not a known standard",
                            "declare only existing standard ids in relations",
                        )
                    )
        if node.manifest.relations.extends and not _has_extension_adr_resource(node):
            findings.append(
                _finding(
                    "SG-REL-EXTENDS-NO-ADR",
                    node,
                    _rel(node.manifest_path),
                    f"{node.standard_id} declares extends without an ADR resource",
                    "add a bundle-local extension_adr resource documenting the extension",
                )
            )
    return findings


def _extends_has_cycle(graph: StandardsGraph) -> bool:
    edges = {node.standard_id: tuple(node.manifest.relations.extends) for node in graph.standards}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        for target in edges.get(node_id, ()):
            if target in edges and visit(target):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in edges)


def _validate_extends_cycles(graph: StandardsGraph) -> list[GraphFinding]:
    if not _extends_has_cycle(graph):
        return []
    return [
        _finding(
            "SG-REL-EXTENDS-CYCLE",
            node,
            _rel(node.manifest_path),
            "extends relationships contain a cycle",
            "remove the cycle so extension relationships form a directed acyclic graph",
        )
        for node in graph.standards
        if node.manifest.relations.extends
    ]
```

- [ ] **Step 4: Implement capability validation.**

```python
def _validate_capabilities(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    provided_by_standard = {
        capability
        for node in graph.standards
        for capability in node.manifest.capabilities.provides
    }
    for node in graph.standards:
        for capability in node.manifest.capabilities.consumes_platform:
            if capability in provided_by_standard:
                findings.append(
                    _finding(
                        "SG-CAPABILITY-STANDARD-CONSUMED",
                        node,
                        _rel(node.manifest_path),
                        f"consumes_platform {capability!r} is provided by a standard",
                        "model standard-to-standard relationships with companions or extends, not consumes_platform",
                    )
                )
            elif capability not in _PLATFORM_CAPABILITIES:
                findings.append(
                    _finding(
                        "SG-CAPABILITY-PLATFORM-UNKNOWN",
                        node,
                        _rel(node.manifest_path),
                        f"platform capability {capability!r} is not registered",
                        "add the capability to the platform registry or remove it from consumes_platform",
                    )
                )
    return findings
```

Add calls:

```python
    findings.extend(_validate_relationship_targets(graph))
    findings.extend(_validate_extends_cycles(graph))
    findings.extend(_validate_capabilities(graph))
```

- [ ] **Step 5: Run validator tests.**

Run: `uv run pytest tests/test_standards_graph_validators.py -q`

Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add src/project_standards/standards_graph/validators.py tests/test_standards_graph_validators.py
git commit -m "feat(v5): validate standard relationships and capabilities"
```

---

### Task 7: Hidden-Dependency Regression Fixtures

**Files:**

- Modify: `tests/test_standards_graph_validators.py`
- Modify: `tests/test_standards_graph_discovery.py`

**Interfaces:**

- Proves the graph layer rejects hidden dependency shapes through loader errors and graph findings.

- [ ] **Step 1: Add loader-boundary tests for reserved dependency fields.**

Add these names to the import block at the **top** of `tests/test_standards_graph_discovery.py` (keep imports at the top for Ruff `E402`):

```python
import pytest

from project_standards.standard_manifest import StandardManifestError
```

Then append the test:

```python
# append to tests/test_standards_graph_discovery.py


def test_requires_field_is_rejected_as_hidden_dependency(tmp_path: Path) -> None:
    bundle = write_standard(tmp_path, "alpha", relation_extras={"requires": ["beta"]})

    with pytest.raises(StandardManifestError) as exc_info:
        build_graph(tmp_path)

    message = str(exc_info.value)
    assert "requires" in message
    assert "Extra inputs are not permitted" in message
    assert bundle.name == "alpha"
```

- [ ] **Step 2: Add graph-level hidden dependency tests.**

```python
# append to tests/test_standards_graph_validators.py

def test_companion_is_advisory_not_required(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", companions=["beta"])
    write_standard(tmp_path, "beta")

    findings = validate_graph(build_graph(tmp_path))

    assert "SG-REL-MISSING-STANDARD" not in {finding.code for finding in findings}
    assert "SG-REL-EXTENDS-NO-ADR" not in {finding.code for finding in findings}


def test_missing_companion_is_reported_but_not_as_extension(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", companions=["beta"])

    findings = validate_graph(build_graph(tmp_path))
    codes = {finding.code for finding in findings}

    assert "SG-REL-MISSING-STANDARD" in codes
    assert "SG-REL-EXTENDS-NO-ADR" not in codes
```

- [ ] **Step 3: Run discovery and validator tests.**

Run: `uv run pytest tests/test_standards_graph_discovery.py tests/test_standards_graph_validators.py -q`

Expected: PASS.

- [ ] **Step 4: Commit.**

```bash
git add tests/test_standards_graph_discovery.py tests/test_standards_graph_validators.py
git commit -m "test(v5): pin hidden dependency rejection"
```

---

### Task 8: CLI Boundary and JSON/Human Output

**Files:**

- Create: `src/project_standards/standards_graph/cli.py`
- Modify: `src/project_standards/standards_graph/__init__.py`
- Test: `tests/test_standards_graph_cli.py`

**Interfaces:**

- Produces `project_standards.standards_graph.cli.run(argv) -> int`.
- CLI command handled here: `validate-graph`.

- [ ] **Step 1: Write failing CLI tests.**

```python
# tests/test_standards_graph_cli.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.standards_graph_helpers import write_standard

from project_standards.standards_graph.cli import run


def test_validate_graph_exit0_human(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_standard(tmp_path, "alpha")

    rc = run(["validate-graph", "--root", str(tmp_path)])

    assert rc == 0
    assert "OK standards graph" in capsys.readouterr().out


def test_validate_graph_exit1_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_standard(tmp_path, "alpha", namespaces=["dup"])
    write_standard(tmp_path, "beta", namespaces=["dup"])

    rc = run(["validate-graph", "--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["findings"][0]["code"] == "SG-CONFIG-DUPLICATE-NAMESPACE"


def test_validate_graph_exit2_on_load_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_standard(tmp_path, "alpha", relation_extras={"requires": ["beta"]})

    rc = run(["validate-graph", "--root", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["code"] == "graph_load_error"
    assert "Traceback" not in captured.err


def test_validate_graph_bad_args_exit2(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["validate-graph", "--nope"]) == 2
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err


def test_bare_standards_cli_and_unknown_subcommand_exit2(capsys: pytest.CaptureFixture[str]) -> None:
    assert run([]) == 2
    assert run(["bogus"]) == 2
    assert run(["--help"]) == 0
    assert "usage:" in capsys.readouterr().out
```

- [ ] **Step 2: Run CLI tests and verify they fail.**

Run: `uv run pytest tests/test_standards_graph_cli.py -q`

Expected: FAIL with `ModuleNotFoundError: project_standards.standards_graph.cli`.

- [ ] **Step 3: Implement the graph CLI.**

```python
# src/project_standards/standards_graph/cli.py
"""Nested `project-standards standards` command group."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

from project_standards.standard_manifest import StandardManifestError
from project_standards.standards_graph.discovery import build_graph
from project_standards.standards_graph.model import findings_to_jsonable, format_findings
from project_standards.standards_graph.validators import validate_graph

_USAGE = "usage: project-standards standards {validate-graph} ..."


class _ArgparseError(Exception):
    """Raised when argparse would normally call sys.exit."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)


def _emit_error(json_mode: bool, code: str, message: str) -> int:
    if json_mode:
        print(json.dumps({"ok": False, "code": code, "error": message}))
    else:
        print(f"error: {message}", file=sys.stderr)
    return 2


def _run_validate_graph(argv: list[str]) -> int:
    ap = _Parser(prog="project-standards standards validate-graph")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-all-manifests", action="store_true")
    try:
        args = ap.parse_args(argv)
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))

    try:
        graph = build_graph(args.root)
        findings = validate_graph(graph, require_all_manifests=args.require_all_manifests)
    except (OSError, ValueError, StandardManifestError) as exc:
        return _emit_error(args.json, "graph_load_error", str(exc))

    if args.json:
        print(json.dumps({"ok": not findings, "findings": findings_to_jsonable(findings)}, indent=2))
    else:
        print(format_findings(findings))
    return 1 if findings else 0


def run(argv: list[str] | None = None) -> int:
    """Run the nested standards command group."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(_USAGE, file=sys.stderr)
        return 2
    if args[0] in {"--help", "-h"}:
        print(_USAGE)
        print("  validate-graph   validate standard manifests as one graph")
        return 0
    command, rest = args[0], args[1:]
    if command == "validate-graph":
        return _run_validate_graph(rest)
    print(_USAGE, file=sys.stderr)
    return 2
```

- [ ] **Step 4: Run CLI tests.**

Run: `uv run pytest tests/test_standards_graph_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standards_graph/cli.py tests/test_standards_graph_cli.py
git commit -m "feat(v5): add standards graph validation CLI"
```

---

### Task 9: Wire Top-Level `project-standards standards`

**Files:**

- Modify: `src/project_standards/cli.py`
- Modify: `tests/test_standards_graph_cli.py`

**Interfaces:**

- Makes `project-standards standards validate-graph` available through `project_standards.cli.main`.

- [ ] **Step 1: Add top-level CLI tests.**

Add this to the import block at the **top** of `tests/test_standards_graph_cli.py` (keep imports at the top for Ruff `E402`):

```python
from project_standards.cli import main
```

Then append the tests:

```python
# append to tests/test_standards_graph_cli.py


def test_top_level_standards_validate_graph(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_standard(tmp_path, "alpha")

    assert main(["standards", "validate-graph", "--root", str(tmp_path)]) == 0
    assert "OK standards graph" in capsys.readouterr().out


def test_top_level_help_advertises_standards(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert "standards" in capsys.readouterr().out
```

- [ ] **Step 2: Run the top-level CLI tests and verify they fail.**

Run: `uv run pytest tests/test_standards_graph_cli.py::test_top_level_standards_validate_graph tests/test_standards_graph_cli.py::test_top_level_help_advertises_standards -q`

Expected: FAIL because `standards` is not dispatched.

- [ ] **Step 3: Add early dispatch and help registration.**

```python
# in src/project_standards/cli.py, after the existing spec early dispatch
    if args_list and args_list[0] == "standards":
        from project_standards.standards_graph.cli import run as _standards_run

        return _standards_run(args_list[1:])
```

```python
# near the existing subparser help registrations
    sub.add_parser("standards", help="validate-graph over standard manifests")
```

- [ ] **Step 4: Run all graph CLI tests.**

Run: `uv run pytest tests/test_standards_graph_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/cli.py tests/test_standards_graph_cli.py
git commit -m "feat(v5): wire standards graph command"
```

---

### Task 10: Real-Repo Smoke and Packaging

**Files:**

- Modify: `tests/test_standards_graph_discovery.py`
- Modify: `tests/test_standards_graph_cli.py`
- Modify: `tests/test_installed_wrappers.py` if the wrapper inventory test expects command help content.

**Interfaces:**

- Proves the current repository can run the graph command before Step 05.
- Proves package import and CLI wrapper coverage.

- [ ] **Step 1: Add current-repo smoke tests.**

```python
# append to tests/test_standards_graph_discovery.py

def test_real_repo_graph_loads_manifest_backed_standards() -> None:
    root = Path(__file__).resolve().parent.parent

    graph = build_graph(root)

    assert graph.ids == frozenset({"standard-bundle-authoring"})
    assert any(path.name == "markdown-frontmatter" for path in graph.missing_manifest_dirs)
```

```python
# append to tests/test_standards_graph_cli.py

def test_current_repo_validate_graph_default_allows_pre_retrofit(capsys: pytest.CaptureFixture[str]) -> None:
    root = Path(__file__).resolve().parent.parent

    rc = main(["standards", "validate-graph", "--root", str(root)])

    assert rc == 0
    assert "OK standards graph" in capsys.readouterr().out


def test_current_repo_validate_graph_require_all_manifests_reports_step05_gap(
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parent.parent

    rc = main(["standards", "validate-graph", "--root", str(root), "--require-all-manifests", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert any(f["code"] == "SG-MANIFEST-MISSING" for f in payload["findings"])
```

- [ ] **Step 2: Run current-repo smoke tests.**

Run: `uv run pytest tests/test_standards_graph_discovery.py::test_real_repo_graph_loads_manifest_backed_standards tests/test_standards_graph_cli.py::test_current_repo_validate_graph_default_allows_pre_retrofit tests/test_standards_graph_cli.py::test_current_repo_validate_graph_require_all_manifests_reports_step05_gap -q`

Expected: PASS.

- [ ] **Step 3: Run package-facing tests.**

Run: `uv run pytest tests/test_installed_wrappers.py tests/test_version_flag.py tests/test_standards_graph_cli.py -q`

Expected: PASS. If `tests/test_installed_wrappers.py` enumerates top-level commands, add `standards` to the expected help text in that test.

- [ ] **Step 4: Commit.**

```bash
git add tests/test_standards_graph_discovery.py tests/test_standards_graph_cli.py tests/test_installed_wrappers.py
git commit -m "test(v5): cover graph CLI against current repo"
```

---

### Task 11: Documentation and Handoff Index

**Files:**

- Modify: `docs/handoff/specs-plans.md`
- Modify: `TODO.md` only if the executor wants the pending Step 04 row to link the plan before starting implementation.

**Interfaces:**

- Makes the Step 04 plan discoverable through the handoff plan table.

- [ ] **Step 1: Add a row to `docs/handoff/specs-plans.md`.**

Add this row after the Step 03 plan row:

```markdown
| SPEC-MT01 Step 04 — Standards graph validator (plan) | `docs/superpowers/plans/2026-07-09-standards-graph-validator.md` | **planned 2026-07-09** — implementation plan for the graph loader, authority/capability/resource/provider/config/relationship validators, hidden-dependency rejection fixtures, and `project-standards standards validate-graph` CLI. Step 05 remains the existing-standards retrofit |
```

- [ ] **Step 2: Optionally link the pending Step 04 row in `TODO.md`.**

Only make this tiny edit if it helps the executor:

```markdown
- [ ] **Step 04 — Standards graph validator** (authority / capability / resource / relationship, including hidden-dependency rejection) + CLI. Plan: `docs/superpowers/plans/2026-07-09-standards-graph-validator.md`.
```

- [ ] **Step 3: Validate the plan docs.**

Run: `npx --no-install prettier --check docs/superpowers/plans/2026-07-09-standards-graph-validator.md docs/handoff/specs-plans.md`

Expected: PASS.

Run: `npx --no-install markdownlint-cli2 --no-globs docs/superpowers/plans/2026-07-09-standards-graph-validator.md docs/handoff/specs-plans.md`

Expected: PASS.

- [ ] **Step 4: Commit.**

```bash
git add docs/superpowers/plans/2026-07-09-standards-graph-validator.md docs/handoff/specs-plans.md TODO.md
git commit -m "docs(v5): plan standards graph validator"
```

---

### Task 12: Full Verification and Implementation Closeout

**Files:**

- No new files.
- Modify only files needed to fix failures found by the gate.

- [ ] **Step 1: Run focused graph tests.**

Run: `uv run pytest tests/test_standards_graph_model.py tests/test_standards_graph_discovery.py tests/test_standards_graph_validators.py tests/test_standards_graph_cli.py -q`

Expected: PASS.

- [ ] **Step 2: Run formatter/linter/type gate.**

Run: `uv run ruff format --check .`

Expected: PASS.

Run: `uv run ruff check .`

Expected: PASS.

Run: `uv run basedpyright`

Expected: PASS with 0 errors and 0 warnings.

- [ ] **Step 3: Run Python test and coverage gate.**

Run: `uv run coverage run -m pytest`

Expected: PASS.

Run: `uv run coverage report`

Expected: PASS with coverage at or above the configured 85 percent threshold.

Run: `uv run pip-audit`

Expected: PASS with no known vulnerabilities.

- [ ] **Step 4: Run repo documentation and coherence gates.**

Run: `uv run pytest tests/coherence`

Expected: PASS.

Run: `npx --no-install prettier --check .`

Expected: PASS.

Run: `npx --no-install markdownlint-cli2`

Expected: PASS on a clean repo baseline. If this fails before Step 04 code changes on unrelated `docs/future-standards/**` backlog files, capture the exact baseline output, keep the Step 04 touched-file markdownlint command from Task 11 passing, and ask the owner whether to fix or exclude that backlog before claiming the full markdown gate is green.

Run: `uv run validate-frontmatter --config .project-standards.yml`

Expected: PASS.

Run: `uv run project-standards spec validate --config .project-standards.yml`

Expected: PASS.

Run: `uv run project-standards spec lint --config .project-standards.yml --strict`

Expected: PASS.

- [ ] **Step 5: Run the new CLI manually.**

Run: `uv run project-standards standards validate-graph`

Expected: `OK standards graph` and exit 0.

Run: `uv run project-standards standards validate-graph --require-all-manifests --json`

Expected: exit 1 before Step 05, with `SG-MANIFEST-MISSING` findings for standards not yet retrofitted.

- [ ] **Step 6: Update release tracker state after implementation.**

When implementation is complete, update:

- `TODO.md`: check off Step 04 with date and commit range.
- `docs/handoff/state.md`: Step 04 done, next Step 05.
- `docs/handoff/specs-plans.md`: Step 04 plan status implemented with commit range and test count.
- `docs/handoff/sessions/2026-07.md`: one compact session row.
- `STATUS.md`: one current-state sentence if Step 04 materially changes the builder-facing summary.

- [ ] **Step 7: Commit final handoff update.**

```bash
git add TODO.md STATUS.md docs/handoff/state.md docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md
git commit -m "docs(v5): record standards graph validator completion"
```

---

## Self-Review Checklist

- SPEC-MT01 FR-004: Task 5 covers authority conflict validation.
- SPEC-MT01 FR-005: Task 4 covers config namespace duplicate ownership.
- SPEC-MT01 FR-006: Task 6 covers capabilities and relationships without hidden dependency semantics.
- SPEC-MT01 FR-007: Task 4 covers resource/adoption/provider schema resource consistency; Step 03 loader covers path existence and containment.
- SPEC-MT01 FR-009: Task 4 covers provider schema resource references; Step 03 model covers provider entrypoint shape.
- SPEC-MT01 FR-010 and IR-003: Tasks 8 and 9 add `project-standards standards validate-graph [--json]`.
- SPEC-MT01 FR-017: Tasks 5, 6, 7, and 10 cover co-adoption safety fixtures.
- SPEC-MT01 FR-021: Tasks 6 and 7 cover missing standards, ADR-backed extension requirements, cycles, and reserved hidden dependency fields.
- Step 05 is intentionally excluded except for `--require-all-manifests` support and smoke tests that expose the gap.
