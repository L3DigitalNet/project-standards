# Python Tooling Checker Table Materialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make exactly one checker table (`[tool.basedpyright]` or `[tool.pyright]`) materialize per resolved Python Tooling configuration by extending conditional materialization to canonical nested option pointers.

**Architecture:** Widen `MaterializationPredicate.option` to accept a disjoint absolute option-pointer spelling with matching traversal; add fail-closed cross-contract validation of every `when_any` path at `load_option_schema`; condition the two checker-table contributions on `/type_checker/name`; guard the provider against rendering the non-selected table; prove lifecycle, lock, and migration safety; and replace the executability gap with a reconciliation-driven complete-gate oracle backed by a locked Pyright test dependency.

**Tech Stack:** Python 3.14, Pydantic strict models, pytest, uv, the project-standards control plane and package contract.

**Design:** [2026-07-12-python-tooling-checker-table-materialization-design.md](../specs/2026-07-12-python-tooling-checker-table-materialization-design.md) — owner-approved; contract audit converged after rounds 1–5.

## Global Constraints

- Work on branch `feature/python-tooling-parallel-coverage` in this worktree; never run `git add .` or `git add -A`.
- `.standards/` must never exist at the repository root — the atomic-release boundary holds; oracles use `tmp_path` repositories only.
- The consumer-facing `standards/python-tooling/versions/1.1/config.schema.json` stays byte-identical.
- Top-level predicate spellings and behavior are unchanged; every shipped payload must still load and evaluate identically.
- Selected-checker-table rendering stays byte-identical to current output.
- The two VS Code mode keys (`basedpyright.analysis.typeCheckingMode`, `python.analysis.typeCheckingMode`) remain unconditional.
- Payload byte changes require the digest ritual: resource digests in `payload.toml`, the aggregate in `standards/python-tooling/standard.toml` and `catalogs/5.toml`, then `uv run project-standards standards sync-payload-projection --root . --check`.
- Generated schema bytes are checked in: after model changes run `uv run project-standards standards generate-package-schemas --root .` and commit the result.
- Coverage-plan Tasks 9 and 11 (Pyright carry-through, guarded dev-group pre-alignment, predecessor overlay) are owned by the parallel-coverage plan amendment, NOT this plan. Do not modify `tests/package_compatibility/*` here.
- Run `uv run project-standards validate --config .project-standards.yml` before claiming completion.

## File map

- `src/project_standards/package_contract/payload.py` — predicate grammar, nested matching, cross-contract validation
- `src/project_standards/schemas/standard-payload.schema.json` — regenerated
- `standards/python-tooling/versions/1.1/payload.toml` — conditional checker contributions + digest refresh
- `standards/python-tooling/versions/1.1/providers/python_tooling.py` — `_checker_table` guard
- `standards/python-tooling/standard.toml`, `catalogs/5.toml` — aggregate digests
- `pyproject.toml`, `uv.lock` — pinned, locked `pyright` wrapper test dependency
- `.github/workflows/check.yml` — Pyright runtime provisioning step beside dependency sync
- `tests/package_contract/test_payload.py` — predicate + cross-contract tests
- `tests/control_plane/planner_helpers.py` — `when_any` + `option_properties` fixture support
- `tests/control_plane/test_lifecycle.py` — conditional-unit transition proofs
- `tests/package_contract/test_python_tooling_reconstruction.py` — payload/provider/planner/oracle proofs

---

### Task 1: Widen the materialization predicate to canonical option pointers

**Files:**

- Modify: `src/project_standards/package_contract/payload.py` (`MaterializationPredicate`, ~line 163; `OptionName`, ~line 69)
- Modify: `src/project_standards/schemas/standard-payload.schema.json` (regenerated)
- Test: `tests/package_contract/test_payload.py`

**Interfaces:**

- Produces: `OptionPointer` type alias; `MaterializationPredicate.option: OptionName | OptionPointer`; unchanged `matches(config) -> bool` signature with nested traversal.

- [ ] **Step 1: Write the failing predicate tests**

Add to `tests/package_contract/test_payload.py` (extend the existing imports with `MaterializationPredicate` from `project_standards.package_contract.payload`):

```python
def test_materialization_predicate_accepts_canonical_option_pointer() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/type_checker/name", "equals": "basedpyright"}
    )

    assert predicate.matches({"type_checker": {"name": "basedpyright", "mode": "strict"}})
    assert not predicate.matches({"type_checker": {"name": "pyright", "mode": "strict"}})


def test_materialization_predicate_pointer_misses_fail_closed() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/type_checker/name", "equals": "basedpyright"}
    )

    assert not predicate.matches({})
    assert not predicate.matches({"type_checker": "basedpyright"})
    assert not predicate.matches({"type_checker": {"mode": "strict"}})


def test_materialization_predicate_contains_matches_nested_arrays() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/coverage/patch", "contains": "subprocess"}
    )

    assert predicate.matches({"coverage": {"patch": ["subprocess"]}})
    assert not predicate.matches({"coverage": {"patch": []}})
    assert not predicate.matches({"coverage": {}})


def test_materialization_predicate_equals_stays_type_exact_at_nested_leaves() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "/coverage/parallel", "equals": True}
    )

    assert predicate.matches({"coverage": {"parallel": True}})
    assert not predicate.matches({"coverage": {"parallel": 1}})


@pytest.mark.parametrize(
    "option",
    [
        "/type_checker",
        "/type_checker/",
        "//name",
        "/type_checker/~1name",
        "/type_checker/0",
        "/Type_Checker/name",
        "/type_checker/naïve",
        "type_checker/name",
    ],
)
def test_materialization_predicate_rejects_noncanonical_pointers(option: str) -> None:
    with pytest.raises(ValidationError):
        MaterializationPredicate.model_validate({"option": option, "equals": "x"})


def test_materialization_predicate_top_level_spelling_is_unchanged() -> None:
    predicate = MaterializationPredicate.model_validate(
        {"option": "workflow_ownership", "equals": "managed"}
    )

    assert predicate.matches({"workflow_ownership": "managed"})
    assert not predicate.matches({"workflow_ownership": "consumer-owned"})
```

- [ ] **Step 2: Run and verify RED**

```bash
uv run pytest tests/package_contract/test_payload.py -k materialization_predicate -q
```

Expected: pointer acceptance, nested-array, type-exact, and fail-closed tests fail with `ValidationError` (pattern mismatch on the current top-level-only `OptionName`); the rejection and top-level tests pass.

- [ ] **Step 3: Implement the widened predicate**

In `src/project_standards/package_contract/payload.py`, next to `OptionName` (~line 69):

```python
OptionPointer = Annotated[
    str,
    StringConstraints(pattern=r"^(?:/[a-z][a-z0-9]*(?:_[a-z0-9]+)*){2,}$"),
]
```

Update `MaterializationPredicate` (~line 163): change the field to `option: OptionName | OptionPointer`, update the class docstring to distinguish the two spellings (bare top-level option name versus absolute multi-segment option pointer; single-segment pointers are noncanonical), and replace the lookup:

```python
    def _observed(self, config: Mapping[str, JsonValue]) -> JsonValue | None:
        if not self.option.startswith("/"):
            return config.get(self.option)
        node: object = config
        for segment in self.option.split("/")[1:]:
            if not isinstance(node, Mapping):
                return None
            node = cast("Mapping[str, JsonValue]", node).get(segment)
        return cast("JsonValue | None", node)

    def matches(self, config: Mapping[str, JsonValue]) -> bool:
        """Return whether the resolved option satisfies this closed predicate."""
        observed = self._observed(config)
        if self.equals is not None:
            return type(observed) is type(self.equals) and observed == self.equals
        return isinstance(observed, list) and any(
            type(item) is type(self.contains) and item == self.contains for item in observed
        )
```

- [ ] **Step 4: Run and verify GREEN, then regenerate the payload schema**

```bash
uv run pytest tests/package_contract/test_payload.py -k materialization_predicate -q
uv run project-standards standards generate-package-schemas --root .
uv run pytest tests/package_contract/test_schemas.py -q
```

Expected: predicate tests pass; the regenerated `src/project_standards/schemas/standard-payload.schema.json` gains the pointer spelling in the `option` contract; schema-canonicality tests pass. If a locked invalid-TOML fixture expectation legitimately changes because the pointer spelling is now valid, update only that fixture's locked expectation.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/package_contract/payload.py src/project_standards/schemas/standard-payload.schema.json tests/package_contract/test_payload.py
git commit -m "feat(package-contract): accept canonical option pointers in materialization predicates"
```

---

### Task 2: Cross-contract predicate validation at option-schema load

**Files:**

- Modify: `src/project_standards/package_contract/payload.py` (`load_option_schema`, ~line 1084)
- Modify: `tests/control_plane/planner_helpers.py` (`ContributionFixture`, `write_payload`)
- Modify: `tests/control_plane/test_migration.py` (fixture schema only if RED surfaces it)
- Test: `tests/package_contract/test_payload.py`

**Interfaces:**

- Consumes: `OptionPointer` spelling from Task 1.
- Produces: `load_option_schema` raising `PackageContractError` with `"undeclared option path"` / `"non-object option"`; `write_payload(..., option_properties: Mapping[str, object] | None = None)` and `ContributionFixture.when_any: NotRequired[list[dict[str, object]]]` for Tasks 4–5.

- [ ] **Step 1: Extend the fixture harness**

In `tests/control_plane/planner_helpers.py`:

Add to `ContributionFixture`:

```python
    when_any: NotRequired[list[dict[str, object]]]
```

Add the parameter `option_properties: Mapping[str, object] | None = None` to `write_payload`, and merge it into the schema construction (replacing the current `option_properties` local seeded from extensions):

```python
    schema_properties: dict[str, object] = dict(option_properties or {})
    for extension in extensions:
        schema_properties[str(extension["option"])] = {"type": "string"}
    config_schema = json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": schema_properties,
            "required": sorted(schema_properties),
        },
        sort_keys=True,
    ).encode()
```

In the contribution-row loop, pass predicates through:

```python
        if "when_any" in item:
            row["when_any"] = item["when_any"]
```

- [ ] **Step 2: Write the failing cross-contract tests**

Add to `tests/package_contract/test_payload.py` (import `load_option_schema`, `load_payload_manifest`, `PackageContractError`, and `write_payload` from `tests.control_plane.planner_helpers`):

```python
_ENGINE_SCHEMA: dict[str, object] = {
    "engine": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"name": {"enum": ["alpha", "beta"]}},
        "required": ["name"],
    }
}


def _predicate_payload(tmp_path: Path, option: str) -> InstalledPayload:
    return write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "conditional",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/alpha",
                "content": b'[tool.alpha]\nmode = "on"\n',
                "when_any": [{"option": option, "equals": "alpha"}],
            }
        ],
        option_properties=_ENGINE_SCHEMA,
    )


def test_option_schema_accepts_predicates_naming_declared_paths(tmp_path: Path) -> None:
    payload = _predicate_payload(tmp_path, "/engine/name")

    load_option_schema(payload.root, payload.manifest)


def test_option_schema_rejects_predicate_naming_undeclared_path(tmp_path: Path) -> None:
    payload = _predicate_payload(tmp_path, "/engine/nmae")

    with pytest.raises(PackageContractError, match="undeclared option path"):
        load_option_schema(payload.root, payload.manifest)


@pytest.mark.parametrize(
    "engine_schema",
    [
        {"type": ["object", "null"], "properties": {"name": {"type": "string"}}},
        {"anyOf": [{"type": "object"}, {"type": "null"}]},
        {"oneOf": [{"type": "object"}]},
        {"allOf": [{"type": "object"}]},
        {"$ref": "#/$defs/engine"},
        {"properties": {"name": {"type": "string"}}},
    ],
)
def test_option_schema_rejects_predicate_through_non_object_intermediate(
    tmp_path: Path,
    engine_schema: dict[str, object],
) -> None:
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "conditional",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/alpha",
                "content": b'[tool.alpha]\nmode = "on"\n',
                "when_any": [{"option": "/engine/name", "equals": "alpha"}],
            }
        ],
        option_properties={"engine": engine_schema},
    )

    with pytest.raises(PackageContractError, match="non-object option"):
        load_option_schema(payload.root, payload.manifest)


def test_every_shipped_payload_satisfies_the_predicate_option_contract() -> None:
    for manifest_path in sorted(
        Path(__file__).resolve().parents[2].glob("standards/*/versions/*/payload.toml")
    ):
        manifest = load_payload_manifest(manifest_path)
        load_option_schema(manifest_path.parent, manifest)
```

- [ ] **Step 3: Run and verify RED**

```bash
uv run pytest tests/package_contract/test_payload.py -k option_schema -q
```

Expected: the two rejection tests fail (no error raised yet); the acceptance and shipped-payload tests pass.

- [ ] **Step 4: Implement the cross-contract validator**

In `src/project_standards/package_contract/payload.py`, add near `_validate_default_contract`:

```python
def _validate_predicate_options(
    document: Mapping[str, JsonValue],
    manifest: PayloadManifest,
) -> None:
    for declaration in (*manifest.artifacts, *manifest.contributions):
        for predicate in declaration.when_any:
            option = predicate.option
            segments = option.split("/")[1:] if option.startswith("/") else [option]
            node: object = document
            for index, segment in enumerate(segments):
                properties = _object_properties(cast("Mapping[str, JsonValue]", node))
                child = properties.get(segment)
                if not isinstance(child, dict):
                    raise PackageContractError(
                        f"materialization predicate names an undeclared option path: {option}"
                    )
                if index + 1 < len(segments) and child.get("type") != "object":
                    raise PackageContractError(
                        f"materialization predicate traverses a non-object option: {option}"
                    )
                node = child
```

Call it in `load_option_schema` immediately after `_validate_extension_options(document, manifest.extensions)`:

```python
    _validate_predicate_options(document, manifest)
```

- [ ] **Step 5: Run and verify GREEN, including migration-fixture fallout**

```bash
uv run pytest tests/package_contract/test_payload.py -k option_schema -q
uv run pytest tests/control_plane/test_migration.py -q
uv run pytest tests/control_plane -q
```

Expected: cross-contract tests pass. If migration tests fail with `undeclared option path: workflow_ownership`, locate the synthetic fixture schema (`grep -n "workflow_ownership" tests/control_plane/test_migration.py`) and declare the option in that fixture payload's config schema — via the new `option_properties` parameter where the payload is written, or by adding `"workflow_ownership": {"type": "string"}` to the fixture's schema properties. Do not weaken the validator.

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/package_contract/payload.py tests/package_contract/test_payload.py tests/control_plane/planner_helpers.py tests/control_plane/test_migration.py
git commit -m "feat(package-contract): statically validate when_any paths against option schemas"
```

---

### Task 3: Conditional checker tables and the provider guard

**Files:**

- Modify: `standards/python-tooling/versions/1.1/payload.toml` (~lines 159–173)
- Modify: `standards/python-tooling/versions/1.1/providers/python_tooling.py` (`_checker_table`, ~line 125)
- Modify: `standards/python-tooling/standard.toml`, `catalogs/5.toml` (aggregate digest)
- Test: `tests/package_contract/test_python_tooling_reconstruction.py`

**Interfaces:**

- Consumes: pointer predicates (Task 1), cross-contract loading (Task 2).
- Produces: `basedpyright-config`/`pyright-config` contributions with `when_any`; `_checker_table` raising `ValueError("non-selected checker table must not be rendered")`.

- [ ] **Step 1: Write the failing payload and provider tests**

Add to `tests/package_contract/test_python_tooling_reconstruction.py`, using its existing `_payload`, `_options`, and `_render` helpers:

```python
def test_python_tooling_declares_conditional_checker_tables() -> None:
    declarations = {item.id: item for item in _payload().manifest.contributions}

    for contribution_id, selected in (
        ("basedpyright-config", "basedpyright"),
        ("pyright-config", "pyright"),
    ):
        predicates = declarations[contribution_id].when_any
        assert [item.option for item in predicates] == ["/type_checker/name"]
        assert [item.equals for item in predicates] == [selected]

    for name in ("basedpyright", "pyright"):
        config = _options(type_checker={"name": name, "mode": "strict"})
        materialized = [
            contribution_id
            for contribution_id in ("basedpyright-config", "pyright-config")
            if declarations[contribution_id].materializes(config)
        ]
        assert materialized == [f"{name}-config"]


def test_python_tooling_provider_refuses_non_selected_checker_table() -> None:
    with pytest.raises(ControlPlaneError):
        _render("table:/tool/pyright", AdapterKind.TOML, _options())


def test_python_tooling_selected_checker_table_rendering_is_unchanged() -> None:
    assert _render("table:/tool/basedpyright", AdapterKind.TOML, _options()) == (
        "[tool.basedpyright]\n"
        'include = ["src", "tests"]\n'
        'typeCheckingMode = "strict"\n'
        'pythonVersion = "3.14"\n'
        'pythonPlatform = "All"\n'
        "failOnWarnings = true\n"
    )
```

If `_render` surfaces provider failures as something other than `ControlPlaneError`, match the file's existing provider-rejection idiom instead (find it with `grep -n "pytest.raises" tests/package_contract/test_python_tooling_reconstruction.py`).

- [ ] **Step 2: Run and verify RED**

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -k checker_table -q
```

Expected: the conditional-declaration test fails (`when_any` is empty); the refusal test fails (the off-mode table renders today); the unchanged-rendering test passes.

- [ ] **Step 3: Add the payload predicates and provider guard**

In `standards/python-tooling/versions/1.1/payload.toml`, extend the two contributions:

```toml
[[contributions]]
id = "basedpyright-config"
target = "pyproject.toml"
adapter = "toml"
scope = "table:/tool/basedpyright"
policy = "managed"
provider = "render-semantic"
when_any = [{ option = "/type_checker/name", equals = "basedpyright" }]

[[contributions]]
id = "pyright-config"
target = "pyproject.toml"
adapter = "toml"
scope = "table:/tool/pyright"
policy = "managed"
provider = "render-semantic"
when_any = [{ option = "/type_checker/name", equals = "pyright" }]
```

In `standards/python-tooling/versions/1.1/providers/python_tooling.py`, replace `_checker_table`:

```python
def _checker_table(config: Mapping[str, object], table: str) -> str:
    checker, mode = _checker(config)
    if checker != table:
        raise ValueError("non-selected checker table must not be rendered")
    include, _coverage = _source_roots(config)
    return (
        f"[tool.{table}]\n"
        f"include = {json.dumps(include)}\n"
        f"typeCheckingMode = {json.dumps(mode)}\n"
        f"pythonVersion = {json.dumps(_python_version(config))}\n"
        'pythonPlatform = "All"\n'
        "failOnWarnings = true\n"
    )
```

Remove or update any existing test asserting the retired off-mode rendering (`grep -n '"off"' tests/package_contract/test_python_tooling_reconstruction.py`) — the VS Code settings `"off"` values at `python_tooling.py:399-400` stay untouched.

- [ ] **Step 4: Refresh Python Tooling integrity**

```bash
sha256sum standards/python-tooling/versions/1.1/providers/python_tooling.py
```

Replace the `provider-code` resource digest in `payload.toml`, then print and propagate the aggregate:

```bash
uv run python - <<'PY'
from pathlib import Path
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

root = Path("standards/python-tooling/versions/1.1")
manifest = load_payload_manifest(root / "payload.toml")
print(validate_payload_integrity(root, manifest).aggregate_digest.value)
PY
```

Write that aggregate to `standards/python-tooling/standard.toml` and the `python-tooling@1.1` entry in `catalogs/5.toml`, then:

```bash
uv run project-standards standards sync-payload-projection --root . --check
```

- [ ] **Step 5: Run and verify GREEN**

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -q
uv run pytest tests/package_contract/test_integrity.py tests/package_contract/test_catalog.py -q
```

Expected: checker tests pass; integrity, catalog, and reconstruction suites pass with the refreshed digests.

- [ ] **Step 6: Commit**

```bash
git add standards/python-tooling/versions/1.1/payload.toml standards/python-tooling/versions/1.1/providers/python_tooling.py standards/python-tooling/standard.toml catalogs/5.toml tests/package_contract/test_python_tooling_reconstruction.py
git commit -m "feat(python-tooling): materialize exactly one checker table"
```

---

### Task 4: Planner and lifecycle transition proofs

**Files:**

- Test: `tests/control_plane/test_lifecycle.py`
- Test: `tests/package_contract/test_python_tooling_reconstruction.py`

**Interfaces:**

- Consumes: `write_payload(..., option_properties=..., contributions=[{..., "when_any": [...]}])` from Task 2; the conditional real payload from Task 3.

- [ ] **Step 1: Write the failing generic transition test**

Add to `tests/control_plane/test_lifecycle.py`, following the file's `write_payload` → `plan_reconciliation` → `_materialize` idiom:

```python
def test_conditional_units_transition_across_pointer_predicate_flips(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        contributions=[
            {
                "id": "alpha-table",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/alpha",
                "content": b'[tool.alpha]\nmode = "on"\n',
                "when_any": [{"option": "/engine/name", "equals": "alpha"}],
            },
            {
                "id": "beta-table",
                "target": "config.toml",
                "adapter": "toml",
                "scope": "table:/tool/beta",
                "content": b'[tool.beta]\nmode = "on"\n',
                "when_any": [{"option": "/engine/name", "equals": "beta"}],
            },
        ],
        option_properties={
            "engine": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"name": {"enum": ["alpha", "beta"]}},
                "required": ["name"],
            }
        },
    )

    def _request(name: str, previous: CentralLock | None = None) -> ResolutionRequest:
        return resolution_request(
            (payload,),
            configs={"demo": {"engine": {"name": name}}},
            previous_lock=previous,
        )

    def _scopes(plan: ReconciliationPlan) -> set[str]:
        return {unit.scope for unit in plan.next_lock.artifacts}

    first = plan_reconciliation(PlannerRequest(repo, _request("alpha"), (payload,)))
    assert _scopes(first) == {"table:/tool/alpha"}
    _materialize(repo, first)

    converged = plan_reconciliation(
        PlannerRequest(repo, _request("alpha", first.next_lock), (payload,))
    )
    assert not converged.actions

    to_beta = plan_reconciliation(
        PlannerRequest(repo, _request("beta", first.next_lock), (payload,))
    )
    assert _scopes(to_beta) == {"table:/tool/beta"}
    assert {unit.kind for unit in to_beta.units} >= {ActionKind.REMOVE, ActionKind.CREATE}
    _materialize(repo, to_beta)
    assert "[tool.alpha]" not in (repo / "config.toml").read_text(encoding="utf-8")

    back = plan_reconciliation(
        PlannerRequest(repo, _request("alpha", to_beta.next_lock), (payload,))
    )
    assert _scopes(back) == {"table:/tool/alpha"}
    _materialize(repo, back)

    settled = plan_reconciliation(
        PlannerRequest(repo, _request("alpha", back.next_lock), (payload,))
    )
    assert not settled.actions
```

Mirror the disable/re-enable shape of `test_enable_update_disable_and_reenable_package_local_artifact` (same file, ~line 204) with a beta-selected config: disable via `_enable_only`, assert the beta unit is removed from file and lock, re-enable with the same config, and assert only `table:/tool/beta` returns and the follow-up plan is empty. Adjust imports (`CentralLock`, `ReconciliationPlan`, `ResolutionRequest`, `ActionKind`) to match the file's existing import block.

- [ ] **Step 2: Write the failing real-payload planner test**

Add to `tests/package_contract/test_python_tooling_reconstruction.py`:

```python
@pytest.mark.parametrize("checker", ["basedpyright", "pyright"])
def test_python_tooling_plan_materializes_exactly_one_checker_scope(
    tmp_path: Path,
    checker: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _payload()
    request = resolution_request(
        (payload,),
        configs={"python-tooling": {"type_checker": {"name": checker, "mode": "strict"}}},
    )
    plan = plan_reconciliation(PlannerRequest(repo, request, (payload,)))

    scopes = {
        unit.scope for unit in plan.next_lock.artifacts if unit.path.original == "pyproject.toml"
    }
    other = "pyright" if checker == "basedpyright" else "basedpyright"
    assert f"table:/tool/{checker}" in scopes
    assert f"table:/tool/{other}" not in scopes
```

If `LockedUnit.path` is a plain string in this model, drop `.original`. Also extend the existing legacy-migration reconstruction test in this file (locate with `grep -n "plan_legacy_migration" tests/package_contract/test_python_tooling_reconstruction.py`) so the composed post-migration `pyproject.toml` proves the default:

```python
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tables = [name for name in ("basedpyright", "pyright") if name in data.get("tool", {})]
    assert tables == ["basedpyright"]
```

- [ ] **Step 3: Write the failing real-payload transition and disable/re-enable tests**

Add to `tests/package_contract/test_python_tooling_reconstruction.py`, reusing the initialize/enable/plan/apply sequence from `test_python_tooling_real_apply_uses_selected_pyright_everywhere` (~line 753) and the disable flow from `test_python_tooling_fresh_apply_second_apply_drift_and_disable` (~line 703). Shared assertion helper:

```python
def _assert_checker_state(repo: Path, plan: ReconciliationPlan, selected: str) -> None:
    other = "pyright" if selected == "basedpyright" else "basedpyright"
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tool = cast("dict[str, object]", data["tool"])
    assert selected in tool
    assert other not in tool
    scopes = {
        unit.scope
        for unit in plan.next_lock.artifacts
        if unit.path.original == "pyproject.toml" and unit.scope.startswith("table:/tool/")
    }
    assert f"table:/tool/{selected}" in scopes
    assert f"table:/tool/{other}" not in scopes
```

Transition cycles from both starting selections:

```python
@pytest.mark.parametrize("first", ["basedpyright", "pyright"])
def test_python_tooling_real_checker_transitions_preserve_locks(
    tmp_path: Path,
    first: str,
) -> None:
    second = "pyright" if first == "basedpyright" else "basedpyright"
    # Initialize and enable python-tooling with type_checker={"name": first,
    # "mode": "strict"} using the established sequence, then for each state:
    #   apply -> _assert_checker_state(repo, plan, selected)
    #   re-plan same config -> assert not plan.actions   (convergence)
    # States, in order: first -> second -> first. On each flip, assert the
    # planned pyproject units include both a REMOVE (stale table) and a
    # CREATE (new table) before applying.
```

Disable/re-enable with a retained non-default selection: extend the existing drift-and-disable test (or add a sibling) so that after disable removes the selected checker table and its lock unit, re-enabling with the retained `pyright` selection restores only `table:/tool/pyright`, `_assert_checker_state` passes, and the follow-up plan is empty.

- [ ] **Step 4: Run and verify RED, then GREEN**

```bash
uv run pytest tests/control_plane/test_lifecycle.py -k conditional_units -q
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -k "exactly_one_checker_scope or real_checker_transitions or drift_and_disable or migration" -q
```

Expected: RED only if Tasks 1–3 left a defect — these tests prove existing machinery; on failure fix the engine or payload work from the earlier tasks, never the assertions. Both commands end GREEN.

- [ ] **Step 5: Commit**

```bash
git add tests/control_plane/test_lifecycle.py tests/package_contract/test_python_tooling_reconstruction.py
git commit -m "test(control-plane): prove conditional checker-table transitions"
```

---

### Task 5: Locked Pyright dependency and the reconciliation-driven complete-gate oracle

**Files:**

- Modify: `pyproject.toml` (dev dependency group), `uv.lock`
- Modify: `.github/workflows/check.yml` (Pyright runtime provisioning step)
- Test: `tests/package_contract/test_python_tooling_reconstruction.py`

**Interfaces:**

- Consumes: `_installed_distribution`, `initialize_control_plane`, `build_planner_request`, `plan_reconciliation`, `apply_reconciliation` — all already imported at the top of the test file.

- [ ] **Step 1: Add the pinned Pyright wrapper and its provisioning contract**

The PyPI `pyright` package is a wrapper: it installs the matching Pyright npm payload at runtime into a user cache (outside `uv.lock`), and `UV_OFFLINE` does not govern that download. Provisioning is therefore a declared setup-phase step — the same class as `uv sync` and `npm ci` — per the design's amended oracle contract (plan-audit CR-001).

Resolve the current wrapper release, pin it exactly, and lock (network required; do not set `UV_OFFLINE` for this step):

```bash
uv add --group dev "pyright==<resolved latest>"
uv sync --locked --all-groups
uv run pyright --version
```

The wrapper's npm payload version tracks the wrapper release, so the exact pin makes the provisioned content deterministic; only its transport is a setup-phase network step. Record the pinned version in the commit message.

Add the provisioning step to `.github/workflows/check.yml` immediately after the "Sync dependencies" step:

```yaml
- name: Provision Pyright runtime
  run: uv run pyright --version
```

Verify the contract once in a fresh-home model: with an empty `PYRIGHT_PYTHON_CACHE_DIR` (or empty user cache), provisioning succeeds online; afterwards `uv run pyright --version` succeeds with outbound network disabled. A one-time cache warm is provisioning, never offline evidence.

- [ ] **Step 2: Write the failing reconciliation-driven oracle**

Add to `tests/package_contract/test_python_tooling_reconstruction.py`. Drive the scratch consumer through the real control plane — mirror the existing initialize/apply call shape already used in this file (locate with `grep -n "initialize_control_plane\|apply_reconciliation" tests/package_contract/test_python_tooling_reconstruction.py`):

```python
@pytest.mark.parametrize("checker", ["basedpyright", "pyright"])
def test_python_tooling_reconciled_complete_gate_oracle(
    tmp_path: Path,
    checker: str,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / "src/consumer_pkg").mkdir(parents=True)
    (repo / "src/consumer_pkg/__init__.py").write_text(
        'GREETING: str = "materialized"\n', encoding="utf-8"
    )
    (repo / "tests").mkdir()
    (repo / "tests/test_consumer_pkg.py").write_text(
        """from consumer_pkg import GREETING


def test_greeting() -> None:
    assert GREETING == "materialized"
""",
        encoding="utf-8",
    )

    # Initialize the control plane, enable python-tooling with the selected
    # checker plus {"pytest": {"fail_under": 0}, "ci": {"enabled": True,
    # "performance": False}}, then plan and apply reconciliation using the
    # file's established initialize/build/plan/apply sequence.

    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tool = cast("dict[str, object]", data["tool"])
    other = "pyright" if checker == "basedpyright" else "basedpyright"
    assert checker in tool
    assert other not in tool

    # Boundary: the oracle proves generated command/config execution against
    # the root locked tool environment (UV_PROJECT); the scratch package is
    # made importable through the asserted PYTHONPATH seam below. Consumer
    # dependency installation is explicitly out of scope.
    environment = {
        **os.environ,
        "COVERAGE_FILE": str(repo / ".coverage"),
        "UV_OFFLINE": "1",
        "UV_PROJECT": str(_ROOT),
        "PYTHONPATH": str(repo / "src"),
    }
    provision = subprocess.run(
        ["uv", "run", checker, "--version"],
        cwd=_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if provision.returncode != 0:
        pytest.fail(
            "checker runtime is not provisioned for the network-isolated oracle; "
            f"run 'uv run {checker} --version' once during environment setup:\n"
            + provision.stdout
            + provision.stderr
        )
    probe = subprocess.run(
        [sys.executable, "-c", "import consumer_pkg"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
    result = subprocess.run(
        [sys.executable, "scripts/check.py"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0 and "cache" in output.lower():
        pytest.fail(f"offline complete-gate oracle is missing a locked cache entry:\n{output}")
    assert result.returncode == 0, output
    subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
        cwd=repo,
        env=environment,
        check=True,
    )
    report = json.loads((repo / "coverage.json").read_text(encoding="utf-8"))
    assert any(
        path.endswith("src/consumer_pkg/__init__.py") for path in report["files"]
    )
```

Real-payload transition cycles from both selections are proven in Task 4; this oracle stays single-purpose per selection.

The commented block is the only part whose exact call signatures come from the file's existing usage — thread the selected checker into the enabled package config and keep everything else verbatim. The scratch project needs a `[project]` table for uv; if reconciliation composes `pyproject.toml` semantic units only, seed the file first with:

```toml
[project]
name = "consumer-pkg"
version = "0.1.0"
requires-python = ">=3.14"
```

- [ ] **Step 3: Run and verify**

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -k complete_gate_oracle -q
```

Expected: both selections pass — the composed pyproject holds exactly one checker table and the full reconciled gate (ruff, checker, coverage lifecycle, pip-audit) exits 0 offline. This supersedes the narrowed subprocess oracle's executability boundary; leave that oracle unchanged for its subprocess-coverage claim.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .github/workflows/check.yml tests/package_contract/test_python_tooling_reconstruction.py
git commit -m "test(python-tooling): prove the reconciled complete gate for both checkers"
```

---

### Task 6: Full verification and documentation

**Files:**

- Modify: `docs/handoff/specs-plans.md`, `docs/STATUS.md`, `docs/TODO.md`

- [ ] **Step 1: Run the complete repository gate**

```bash
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run pytest tests/package_contract tests/control_plane -q
uv run ruff format --check . && uv run ruff check .
uv run basedpyright
uv run pip-audit
npm ci
uv run pytest tests/coherence -v
uv run project-standards validate --config .project-standards.yml
uv run python scripts/run_repository_tests.py
```

Also run the catalog freshness check exactly as `.github/workflows/validate-standards-graph.yml` runs it (its steps around lines 30–37). `pip-audit` is mandatory here because Task 5 added a dependency; the coherence suite is mandatory because `AGENTS.md` requires it after validator/test changes. Expected: all green; `.standards/` still absent at the repository root (`test -e .standards && echo VIOLATION || echo ok`); `git status --short` shows only the intended implementation and documentation changes.

- [ ] **Step 2: Record the pointers**

Add the design and this plan to `docs/handoff/specs-plans.md`; update `docs/STATUS.md` and `docs/TODO.md`: checker fix implemented, coverage-plan Tasks 9/11 amendment plus fresh audit still pending before Task 9 executes.

- [ ] **Step 3: Commit**

```bash
git add docs/handoff/specs-plans.md docs/STATUS.md docs/TODO.md
git commit -m "docs: record checker-table materialization implementation"
```

---

## Audit round 1 reconciliation

- **CR-001:** Task 5 pins the wrapper version, adds the CI provisioning step, defines runtime provisioning as a declared setup-phase prerequisite, and makes the oracle assert the provisioned runtime before its network-isolated gate. The design's oracle-environment contract carries the matching amendment.
- **CR-002:** the oracle keeps the default `src` layout, adds an asserted `PYTHONPATH` import seam, an explicit import probe, and a coverage-includes-source assertion, and states the root-tool boundary in the test.
- **CR-003:** Task 4 gains real-payload transition cycles from both starting selections plus a real disable/re-enable lock proof anchored to the existing real-apply tests; the generic fixture remains complementary and the superseded Task 5 flip-back epilogue is removed.
- **CR-004:** Task 6 is the complete repository gate: dependency audit, package/graph/catalog validation, and Node/Python coherence after `npm ci`, in addition to the original checks.
- **CR-005:** the intermediate-shape rejection test is parameterized across nullable, `anyOf`, `oneOf`, `allOf`, `$ref`, and missing-type intermediates.

## Plan self-review checklist

- [ ] Every design acceptance criterion owned by this plan maps to a task (predicate grammar → Task 1; static validation → Task 2; payload/provider → Task 3; transitions, migration default, disable/re-enable, both-selection cycles → Task 4; pinned Pyright provisioning + oracle → Task 5; regeneration and full gates → Tasks 1/3/6). Release integration (Pyright carry-through, guarded pre-alignment, predecessor overlay) is explicitly owned by the parallel-coverage plan amendment.
- [ ] No placeholder steps; the convention-following blocks (lifecycle imports, real-apply initialize/apply sequences, oracle setup) carry exact discovery commands, named in-file precedents, and complete surrounding code.
- [ ] Names are consistent across tasks: `OptionPointer`, `_observed`, `_validate_predicate_options`, `option_properties`, `when_any`, `_assert_checker_state`, `"non-selected checker table must not be rendered"`.
- [ ] Commits are per-task and add files by explicit name.
