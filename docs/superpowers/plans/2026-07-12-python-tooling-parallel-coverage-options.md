# Python Tooling Parallel Coverage and Workflow Ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add closed Python Tooling parallel/subprocess coverage options and a generic, fail-closed whole-file ownership-relinquishment path so the optimized repository gate survives the atomic v5 migration.

**Architecture:** The generic control plane owns authorization: an immutable payload signature statically binds one raw owner-intent pointer to one whole-file target, the provider echoes that binding, and the engine clears only the matching held unknown-digest finding after every proof passes. Python Tooling then uses that primitive for a consumer-owned check workflow while independently rendering coverage options, dependency floors, and parallel-aware local/CI commands. Default package output and existing known-history claims remain byte-compatible.

**Tech Stack:** Python 3.14, Pydantic v2, JSON Schema 2020-12, TOML/YAML, pytest, coverage.py 7.10+, uv, Ruff, BasedPyright, package source/wheel reconstruction tests.

---

## Execution prerequisites and boundaries

- Execute only after the converged ADR/spec/design/report and this plan are captured in a named prerequisite commit. Record `git status --short` and `git rev-parse HEAD`, create the isolated implementation worktree from that exact commit with `superpowers:using-git-worktrees`, then verify the new worktree's HEAD and clean status before Task 1. If the owner chooses a reviewed patch transfer instead, record its path list and compare `git diff --stat` before and after application; never assume an ordinary worktree created from HEAD contains uncommitted contract inputs.
- Preserve all unrelated release changes. Each commit command below is path-scoped and assumes a clean isolated implementation worktree; do not run it in a mixed user worktree.
- Keep repository-root `.standards/` absent until the atomic v5 release commit.
- Keep `src/project_standards/bundles/python-tooling/check.py`, the frozen V1 bundle, and the live root `scripts/check.py` byte-identical until the final atomic-migration task.
- Treat [the convergence audit](../../reviews/2026-07-12-1824-ownership-relinquishment-contract-convergence-audit.md) and [the approved design](../specs/2026-07-12-python-tooling-parallel-coverage-options-design.md) as controlling inputs.

## File map

| Unit | Files | Responsibility |
| --- | --- | --- |
| JSON-pointer and payload declaration | `src/project_standards/package_contract/paths.py`, `payload.py`, generated `schemas/standard-payload.schema.json` | Canonical pointer validation and static single-target owner-intent binding |
| Claim and migration engine | `src/project_standards/control_plane/migration.py`, generated `schemas/migration-report.schema.json` | Optional claim pointer, held unknown findings, proof validation, preview/apply safety |
| Generic contract tests | `tests/package_contract/test_paths.py`, `test_payload.py`, `test_schemas.py`, `test_cli_documentation_reconstruction.py`, `tests/control_plane/test_migration.py`, `test_schemas.py` | Declaration/claim shapes, fail-closed cases, known-claim compatibility, no-action/no-lock, stale plan |
| Python Tooling package | `standards/python-tooling/versions/1.1/config.schema.json`, `payload.toml`, `providers/python_tooling.py`, `schemas/migration-report.schema.json`, `README.md` | Coverage options, dependency/rendering behavior, conditional workflow ownership, migration claim |
| Python Tooling tests | `tests/package_contract/test_python_tooling_reconstruction.py` | Defaults, schema rejection, rendering, workflow lifecycle, migration, source/wheel parity |
| Authoring contract synchronization | `standards/standard-bundle-authoring/versions/2.0/README.md`, `templates/legacy-signature.toml`, self-hosting/reconstruction tests | Distinguish exact package history from the narrow owner-resolution exception |
| Release proof | `tests/package_compatibility/release_candidate.py`, `test_release_candidate.py`, retained release evidence | Repository-specific options and disposable atomic migration proof |
| Atomic root migration | `scripts/check.py`, `tests/test_adopt_dogfood.py` | Release-commit-only transition from frozen V1 twin to current V2 rendering |

### Task 1: Add the static payload pointer-to-target declaration

**Files:**

- Modify: `src/project_standards/package_contract/paths.py`
- Modify: `src/project_standards/package_contract/payload.py`
- Modify: `tests/package_contract/test_paths.py`
- Modify: `tests/package_contract/test_payload.py`
- Modify: `tests/package_contract/test_schemas.py`
- Regenerate: `src/project_standards/schemas/standard-payload.schema.json`

- [ ] **Step 1: Add failing canonical-pointer and declaration-shape tests**

Add tests covering a canonical pointer, missing leading slash, noncanonical `~` escape, bounded-block declaration, multi-target whole-file declaration, duplicate pointers across signatures, and one valid single-target declaration.

```python
def test_owner_resolution_pointer_is_canonical_and_target_specific() -> None:
    signature = LegacySignatureDeclaration.model_validate(
        {
            "id": "legacy-workflow",
            "kind": "whole-file",
            "targets": [".github/workflows/check.yml"],
            "known_content_digests": [_digest("a")],
            "consumer_owned_intent_pointer": "/python_tooling/workflow_ownership",
        }
    )
    assert signature.consumer_owned_intent_pointer == (
        "/python_tooling/workflow_ownership"
    )


@pytest.mark.parametrize(
    "update",
    [
        {"kind": "bounded-block", "format": "yaml", "begin": "# begin", "end": "# end"},
        {"targets": ["one.yml", "two.yml"]},
        {"consumer_owned_intent_pointer": "python_tooling/workflow_ownership"},
        {"consumer_owned_intent_pointer": "/python_tooling/~2workflow"},
    ],
)
def test_owner_resolution_declaration_rejects_ambiguous_shapes(update: dict[str, object]) -> None:
    values = _whole_file_signature()
    values.update(update)
    with pytest.raises(ValidationError):
        LegacySignatureDeclaration.model_validate(values)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
uv run pytest tests/package_contract/test_paths.py tests/package_contract/test_payload.py -q
```

Expected: failures because canonical pointer validation is migration-local and `consumer_owned_intent_pointer` is forbidden as an extra field.

- [ ] **Step 3: Extract canonical pointer validation and add the payload field**

Move the existing validation logic from `control_plane/migration.py` into the package-contract boundary without changing its accepted language.

```python
def validate_json_pointer(value: str) -> str:
    """Return one canonical absolute JSON pointer or raise ValueError."""
    if not value.startswith("/"):
        raise ValueError("setting must be an absolute JSON pointer")
    index = 0
    while index < len(value):
        if value[index] != "~":
            index += 1
            continue
        if index + 1 >= len(value) or value[index + 1] not in {"0", "1"}:
            raise ValueError("setting contains a noncanonical JSON pointer escape")
        index += 2
    return value
```

Add the optional declaration and validate its local shape.

```python
class LegacySignatureDeclaration(StrictModel):
    """Declare exact package history and optional target-bound owner resolution."""

    # existing fields stay in canonical order
    known_content_digests: list[Sha256Digest] = Field(min_length=1)
    consumer_owned_intent_pointer: str | None = None

    @field_validator("consumer_owned_intent_pointer")
    @classmethod
    def _canonical_owner_intent_pointer(cls, value: str | None) -> str | None:
        return None if value is None else validate_json_pointer(value)

    @model_validator(mode="after")
    def _signature_shape(self) -> LegacySignatureDeclaration:
        # retain existing path, digest, and block validation first
        if self.consumer_owned_intent_pointer is not None and (
            self.kind is not LegacySignatureKind.WHOLE_FILE or len(self.targets) != 1
        ):
            raise ValueError(
                "consumer-owned intent requires one whole-file legacy target"
            )
        return self
```

In `PayloadManifest._resource_identity_and_config_schema`, reject reuse:

```python
intent_pointers = [
    signature.consumer_owned_intent_pointer
    for signature in self.legacy_signatures
    if signature.consumer_owned_intent_pointer is not None
]
if len(intent_pointers) != len(set(intent_pointers)):
    raise ValueError("payload reuses a consumer-owned intent pointer")
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
uv run pytest tests/package_contract/test_paths.py tests/package_contract/test_payload.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Regenerate and verify the strict payload schema**

Run:

```bash
uv run project-standards standards generate-package-schemas --root .
uv run pytest tests/package_contract/test_schemas.py -q
```

Expected: `standard-payload.schema.json` contains optional `consumer_owned_intent_pointer`, remains closed, and all schema tests pass.

- [ ] **Step 6: Commit the payload declaration unit**

```bash
git add src/project_standards/package_contract/paths.py src/project_standards/package_contract/payload.py src/project_standards/schemas/standard-payload.schema.json tests/package_contract/test_paths.py tests/package_contract/test_payload.py tests/package_contract/test_schemas.py
git commit -m "feat(control-plane): declare target-bound owner intent"
```

### Task 2: Add the optional claim intent pointer without changing known claims

**Files:**

- Modify: `src/project_standards/control_plane/migration.py`
- Modify: `tests/control_plane/test_migration.py`
- Modify: `tests/control_plane/test_schemas.py`
- Regenerate: `src/project_standards/schemas/migration-report.schema.json`

- [ ] **Step 1: Add failing claim normalization and public-output tests**

```python
def test_legacy_claim_accepts_optional_canonical_intent_pointer() -> None:
    claim = _claim(
        ownership="consumer-owned",
        disposition="preserve",
        intent_pointer="/python_tooling/workflow_ownership",
    )
    assert claim.intent_pointer == "/python_tooling/workflow_ownership"
    assert migration_report_to_jsonable(
        MigrationReport(schema_version="1.0", package=_package(), claims=(claim,))
    )["claims"][0]["intent_pointer"] == claim.intent_pointer


def test_known_claim_json_shape_omits_absent_intent_pointer() -> None:
    report = MigrationReport(schema_version="1.0", package=_package(), claims=(_claim(),))
    assert "intent_pointer" not in migration_report_to_jsonable(report)["claims"][0]
```

Also parametrize invalid noncanonical pointers and assert schema `additionalProperties: false` remains intact.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
uv run pytest tests/control_plane/test_migration.py::test_legacy_claim_accepts_optional_canonical_intent_pointer tests/control_plane/test_migration.py::test_known_claim_json_shape_omits_absent_intent_pointer -q
```

Expected: the first test fails because the field is forbidden.

- [ ] **Step 3: Add the field and preserve field-free serialization**

```python
class LegacyClaim(StrictModel):
    """Identify known package history or one target-bound owner-resolution claim."""

    signature_id: KebabId
    target: SafeRelativePath
    observed_digest: Sha256Digest
    ownership: LegacyOwnership
    disposition: LegacyDisposition
    intent_pointer: str | None = None

    @field_validator("intent_pointer")
    @classmethod
    def _canonical_intent_pointer(cls, value: str | None) -> str | None:
        return None if value is None else validate_json_pointer(value)
```

Include the pointer in `_claim_sort_key`, but add it to public JSON and human rendering only when present:

```python
claim_json = {
    "signature_id": claim.signature_id,
    "target": claim.target.original,
    "observed_digest": claim.observed_digest.value,
    "ownership": claim.ownership,
    "disposition": claim.disposition.value,
}
if claim.intent_pointer is not None:
    claim_json["intent_pointer"] = claim.intent_pointer
```

- [ ] **Step 4: Regenerate the control-plane schema and run focused tests**

Run:

```bash
uv run project-standards standards generate-package-schemas --root .
uv run pytest tests/control_plane/test_migration.py tests/control_plane/test_schemas.py -q
```

Expected: claim/schema tests pass; ordinary claim JSON remains unchanged.

- [ ] **Step 5: Commit the claim contract**

```bash
git add src/project_standards/control_plane/migration.py src/project_standards/schemas/migration-report.schema.json tests/control_plane/test_migration.py tests/control_plane/test_schemas.py
git commit -m "feat(control-plane): carry owner intent in legacy claims"
```

### Task 3: Implement fail-closed owner-resolution validation

**Files:**

- Modify: `src/project_standards/control_plane/migration.py`
- Modify: `tests/control_plane/test_migration.py`
- Modify: `tests/package_contract/test_cli_documentation_reconstruction.py`

- [ ] **Step 1: Add failing adversarial engine tests**

Create one helper that mutates the synthetic alpha payload to use an unknown single-target whole-file signature with a static pointer. Add separate tests for:

- valid explicit relinquishment;
- pointer absent from raw YAML;
- raw value defaulted, false, or not literal `consumer-owned`;
- provider does not report the pointer as recognized;
- claim pointer differs from the declaration;
- claim target differs from the signature target;
- claim digest differs from the observation;
- provider omits the claim entirely;
- known claim includes an extraneous intent pointer;
- resolved payload still materializes the target;
- bounded-block, managed, destructive, shared, and import-lock attempts.
- accepted preview has no action, planned target, planned unit, adopted unit, or lock entry;
- apply/fixed-point/disable/re-enable preservation and path/type/byte stale-plan refusal;
- option-only return to managed conflicts, while explicit owner backup followed by reviewed create-and-lock replacement converges.

The valid test must assert the ordinary finding is cleared; every invalid unknown case must retain it.

Extend the CLI Documentation migration reconstruction test to assert its known `.github/workflows/cli-docs-check.yml` claim has no `intent_pointer` and remains applicable.

```python
assert plan.applicable, plan.findings
assert not any(
    finding.code == "CP-MIGRATION-LEGACY-DIGEST"
    and finding.path == ".github/workflows/check.yml"
    for finding in plan.findings
)

blocked = plan_legacy_migration(invalid_repo, invalid_distribution, "5")
assert not blocked.applicable
assert any(
    finding.code == "CP-MIGRATION-LEGACY-DIGEST"
    and finding.path == ".github/workflows/check.yml"
    for finding in blocked.findings
)
```

- [ ] **Step 2: Run the adversarial tests and verify RED**

Run:

```bash
uv run pytest tests/control_plane/test_migration.py -k 'owner_resolution or unknown_whole_file' -q
```

Expected: the valid exception still fails at both current unknown-digest gates.

- [ ] **Step 3: Add raw-pointer lookup without applying defaults**

```python
_MISSING = object()


def _pointer_value(document: JsonObject, pointer: str) -> object:
    current: object = document
    for part in _pointer_parts(pointer):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isascii() and part.isdigit():
            index = int(part)
            if index >= len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


```

- [ ] **Step 4: Convert unknown findings to hold-and-emit-unless-cleared after reconciliation**

Keep malformed bounded-block findings in `_inspect_signatures`, but stop emitting the whole-file unknown-digest finding there. Move final claim validation until after `plan_reconciliation(planner)` so it can inspect resolved materialization and lock/action state, while still running before applicability and all writes. Pass `legacy`, `payloads`, and the `ReconciliationPlan` into `_claim_findings`. For each unknown observation, clear it only after this complete predicate succeeds:

```python
resolved_package = next(
    package
    for package in reconciliation.resolution.packages
    if package.standard_id == report.package.standard_id
)
payload = payloads[(report.package.standard_id, report.package.version.value)]
valid_relinquishment = (
    signature.kind is LegacySignatureKind.WHOLE_FILE
    and len(signature.targets) == 1
    and signature.targets[0] == claim.target
    and signature.consumer_owned_intent_pointer is not None
    and claim.intent_pointer == signature.consumer_owned_intent_pointer
    and claim.intent_pointer in report.package.recognized_settings
    and _pointer_value(legacy, claim.intent_pointer) == "consumer-owned"
    and claim.ownership == "consumer-owned"
    and claim.disposition is LegacyDisposition.PRESERVE
    and item is not None
    and item.digest == claim.observed_digest
    and not any(
        declaration.target == claim.target
        and declaration.materializes(resolved_package.effective_config)
        for declaration in (
            *payload.manifest.artifacts,
            *payload.manifest.contributions,
        )
    )
    and not any(target.target == claim.target.original for target in reconciliation.targets)
    and not any(action.target == claim.target.original for action in reconciliation.actions)
    and not any(unit.target == claim.target.original for unit in reconciliation.units)
    and not any(
        unit.path == claim.target
        for unit in reconciliation.next_lock.artifacts
    )
)
```

Track cleared observation keys. After all claims, emit `CP-MIGRATION-LEGACY-DIGEST` for every unknown observation not in that set. Emit a stable `CP-MIGRATION-OWNER-RESOLUTION` finding for malformed exception claims, including an intent pointer on known history, while retaining the ordinary digest finding for the unknown observation. Leave `_adopted_legacy_units` and `_removal_actions` behavior unchanged; `preserve` already falls out of both paths.

Extend `render_migration_report` so an accepted exception is labeled as consumer-owned, preserved, and not semantically validated by the package. Add a human-output assertion beside the JSON preview test; do not expose file content.

- [ ] **Step 5: Run the full migration test module and verify GREEN**

Run:

```bash
uv run pytest tests/control_plane/test_migration.py -q
```

Expected: all migration tests pass, including unknown-and-unclaimed and known-claim compatibility.

- [ ] **Step 6: Commit the engine proof**

```bash
git add src/project_standards/control_plane/migration.py tests/control_plane/test_migration.py tests/package_contract/test_cli_documentation_reconstruction.py
git commit -m "feat(control-plane): validate ownership relinquishment"
```

### Task 4: Complete owner-resolution lifecycle verification

**Files:**

- Modify: `tests/control_plane/test_migration.py`

- [ ] **Step 1: Complete the applicable-plan assertions introduced before Task 3 implementation**

For the valid consumer-owned unknown whole file, assert:

```python
assert plan.applicable
assert preserved.read_bytes() == original
assert all(action.target != preserved_relative for action in plan.actions)
assert all(unit.target != preserved_relative for unit in plan.reconciliation.units)
assert all(unit.path.original != preserved_relative for unit in plan.reconciliation.next_lock.artifacts)
adopted = _adopted_legacy_units(plan.reports, observed, payloads)
assert all(unit.path.original != preserved_relative for unit in adopted)
assert preserved_relative not in {target.target for target in plan.reconciliation.targets}
public_claim = plan.to_jsonable()["reports"][0]["claims"][0]
assert public_claim["target"] == preserved_relative
assert public_claim["observed_digest"] == expected_digest.value
assert public_claim["intent_pointer"] == "/alpha/workflow_ownership"
```

- [ ] **Step 2: Complete apply, fixed-point, return-to-managed, and stale-plan coverage**

Apply the relinquishment plan and prove the file remains byte-identical and outside the lock. Reconcile, disable, and re-enable the package and prove the file remains untouched. Then change only the ownership option back to managed while the unowned file still exists and require `CP-CONSUMER-CONFLICT` with no write, removal, adoption, or lock change.

Prove the separate reviewed replacement path by explicitly moving the consumer file to a backup path before replanning. The next preview must preserve that backup, propose a create for the now-vacant managed target, and include that target in the next lock; apply must converge without altering the backup:

```python
blocked = plan_reconciliation(_request(repo, workflow_ownership="managed"))
assert any(item.code == "CP-CONSUMER-CONFLICT" for item in blocked.findings)
assert not blocked.applicable
assert workflow.read_bytes() == original

backup = workflow.with_name("check.consumer-owned.yml")
workflow.rename(backup)
replacement_request = _request(repo, workflow_ownership="managed")
replacement = plan_reconciliation(replacement_request)
assert replacement.applicable, replacement.findings
assert any(
    action.kind is ActionKind.CREATE and action.target == preserved_relative
    for action in replacement.actions
)
assert any(
    unit.path.original == preserved_relative
    for unit in replacement.next_lock.artifacts
)
result = apply_reconciliation(ApplyRequest(replacement_request, replacement))
assert result.success, result
assert backup.read_bytes() == original
assert workflow.read_bytes() == expected_managed_workflow
fixed = plan_reconciliation(_request(repo, workflow_ownership="managed"))
assert fixed.applicable, fixed.findings
assert all(
    action.kind in {ActionKind.NOOP, ActionKind.PRESERVE}
    for action in fixed.actions
)
```

Finally, modify each of path type, symlink state, and bytes between relinquishment preview/apply and require `CP-STALE-PLAN` with no `.standards/` publication.

- [ ] **Step 3: Run the lifecycle tests**

Run:

```bash
uv run pytest tests/control_plane/test_migration.py -k 'owner_resolution or relinquishment' -q
```

Expected: all selected lifecycle tests pass.

- [ ] **Step 4: Commit lifecycle evidence**

```bash
git add tests/control_plane/test_migration.py
git commit -m "test(control-plane): prove relinquishment lifecycle safety"
```

### Task 5: Add Python Tooling coverage and workflow-ownership options

**Files:**

- Modify: `standards/python-tooling/versions/1.1/config.schema.json`
- Modify: `standards/python-tooling/versions/1.1/providers/python_tooling.py`
- Modify: `standards/python-tooling/versions/1.1/payload.toml`
- Modify: `standards/python-tooling/standard.toml`
- Modify: `catalogs/5.toml`
- Modify: `tests/package_contract/test_python_tooling_reconstruction.py`

- [ ] **Step 1: Add failing option/default/cross-field tests**

Extend `test_python_tooling_options_are_closed_and_fully_defaulted` with:

```python
"coverage": {"parallel": False, "patch": []},
"workflow_ownership": "managed",
```

Add valid opted-in values and invalid cases for unknown patch names, duplicate patches, false parallel with subprocess, and omitted parallel with subprocess.

Before provider implementation, add named failing tests for each rendering seam:

- `test_python_tooling_subprocess_patch_selects_coverage_7_10_floor`;
- `test_python_tooling_coverage_run_renders_canonical_parallel_patch_order`;
- `test_python_tooling_parallel_commands_render_erase_run_combine_report`;
- `test_python_tooling_parallel_local_commands_match_ci_coverage_lifecycle`;
- parameterized `test_python_tooling_generated_gate_subprocess_capture_oracle`, covering patch-enabled capture and the no-patch negative control in the offline scratch checkout described in Task 6.

- [ ] **Step 2: Run the option test and verify RED**

Run:

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -k 'options_are_closed or coverage_run or parallel_commands or parallel_local_commands or subprocess_capture_oracle' -q
```

Expected: option tests fail because both options are unknown; rendering and scratch-oracle tests fail because the dependency floor, TOML keys, and parallel command lifecycle are absent.

- [ ] **Step 3: Add the closed schema with the raw-input conditional**

Add top-level properties:

```json
"coverage": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "parallel": { "type": "boolean", "default": false },
    "patch": {
      "type": "array",
      "items": { "const": "subprocess" },
      "uniqueItems": true,
      "default": []
    }
  },
  "default": { "parallel": false, "patch": [] }
},
"workflow_ownership": {
  "enum": ["managed", "consumer-owned"],
  "default": "managed"
}
```

Add an `allOf` condition whose `then` branch includes both `required: ["parallel"]` and `parallel: {"const": true}` when a non-empty patch is present. This must reject raw `{patch:["subprocess"]}` before default application.

- [ ] **Step 4: Update `_DEFAULT_CONFIG`, dependency rendering, and coverage TOML rendering**

```python
_DEFAULT_CONFIG.update(
    {
        "coverage": {"parallel": False, "patch": []},
        "workflow_ownership": "managed",
    }
)


def _coverage_run(config: Mapping[str, object]) -> str:
    coverage = _section(config, "coverage")
    _include, sources = _source_roots(config)
    lines = ["[tool.coverage.run]", "branch = true"]
    if coverage.get("parallel") is True:
        lines.append("parallel = true")
    if coverage.get("patch"):
        lines.append('patch = ["subprocess"]')
    lines.append(f"source = {json.dumps(sources)}")
    return "\n".join(lines) + "\n"
```

In `_dependencies`, render `coverage[toml]>=7.10.0` only when `patch` is non-empty; keep `coverage[toml]` for defaults.

- [ ] **Step 5: Add conditional coverage command construction**

```python
def _coverage_commands(*pytest_args: str, config: Mapping[str, object]) -> list[tuple[str, ...]]:
    run = ("uv", "run", "coverage", "run", *(('--parallel-mode',) if _section(config, "coverage").get("parallel") is True else ()), "-m", "pytest", *pytest_args)
    if _section(config, "coverage").get("parallel") is not True:
        return [run, ("uv", "run", "coverage", "report")]
    return [
        ("uv", "run", "coverage", "erase"),
        run,
        ("uv", "run", "coverage", "combine"),
        ("uv", "run", "coverage", "report"),
    ]
```

Use the helper from both `_commands` and `_local_commands`; preserve the default command sequence byte for byte.

- [ ] **Step 6: Refresh Python Tooling integrity before loader-backed tests**

Run `sha256sum` for `config.schema.json` and `providers/python_tooling.py`, then replace only their matching resource digests in `payload.toml`. After those resource digests validate, print the new aggregate:

```bash
sha256sum standards/python-tooling/versions/1.1/config.schema.json standards/python-tooling/versions/1.1/providers/python_tooling.py
uv run python - <<'PY'
from pathlib import Path
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

root = Path("standards/python-tooling/versions/1.1")
manifest = load_payload_manifest(root / "payload.toml")
print(validate_payload_integrity(root, manifest).aggregate_digest.value)
PY
```

Write that aggregate to `standards/python-tooling/standard.toml` and the `python-tooling@1.1` entry in `catalogs/5.toml`. Run `uv run project-standards standards sync-payload-projection --root . --check`; because this task adds no payload path, any projection drift is unexpected and must be investigated.

- [ ] **Step 7: Run rendering tests and verify GREEN**

Run:

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -k 'options or coverage or workflow' -q
```

Expected: default bytes remain unchanged; opted-in TOML uses `branch`, `parallel`, `patch`, `source`; dependency and command assertions pass.

- [ ] **Step 8: Commit the option/rendering unit**

```bash
git add standards/python-tooling/versions/1.1/config.schema.json standards/python-tooling/versions/1.1/providers/python_tooling.py standards/python-tooling/versions/1.1/payload.toml standards/python-tooling/standard.toml catalogs/5.toml tests/package_contract/test_python_tooling_reconstruction.py
git commit -m "feat(python-tooling): configure parallel coverage"
```

### Task 6: Prove generated subprocess coverage end to end

**Files:**

- Modify: `tests/package_contract/test_python_tooling_reconstruction.py`

- [ ] **Step 1: Complete the pre-implementation scratch-consumer oracle**

Complete the parameterized test introduced before Task 5 implementation: it launches `python -m child_only`, while no parent imports `child_only`. Use the existing minimal-repository/installed-wheel helpers and the locked local environment so the test remains offline; do not add a network-dependent dependency installation path. Render the complete local script in both supported configurations, execute its gate in the scratch repository, then inspect coverage JSON. The `patch=["subprocess"]` case must capture `child_only.py`; the `patch=[]` negative control must prove it is absent.

```python
config = _options(coverage={"parallel": True, "patch": ["subprocess"]})
script = _render("$file", AdapterKind.WHOLE_FILE, config, target="scripts/check.py")
(repo / "scripts/check.py").write_text(script, encoding="utf-8")

result = subprocess.run(
    [sys.executable, "scripts/check.py"],
    cwd=repo,
    env={**os.environ, "COVERAGE_FILE": str(repo / ".coverage")},
    check=False,
    capture_output=True,
    text=True,
)
assert result.returncode == 0, result.stdout + result.stderr
subprocess.run(
    [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
    cwd=repo,
    check=True,
)
report = json.loads((repo / "coverage.json").read_text(encoding="utf-8"))
captured = any(path.endswith("child_only.py") for path in report["files"])
assert captured is expect_child_capture
assert not list(repo.glob(".coverage.*"))
```

Give the scratch project the minimal Ruff, pytest, type-checker, coverage, and pip-audit configuration needed for the complete generated gate; do not skip non-coverage commands. Run subprocesses with `UV_OFFLINE=1` and fail with an explicit missing-cache diagnostic rather than accessing the network.

- [ ] **Step 2: Run both oracle cases and verify GREEN**

Run:

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -k subprocess_only -q
```

Expected: the child-only module appears in the report and input shards are removed.

- [ ] **Step 3: Run the durable paired oracle**

Run the parameterized test without source edits and require both the positive subprocess-patch case and negative no-patch case to pass. This committed comparison is the evidence that the oracle detects the behavior being preserved.

- [ ] **Step 4: Commit the executable coverage proof**

```bash
git add tests/package_contract/test_python_tooling_reconstruction.py
git commit -m "test(python-tooling): prove subprocess coverage capture"
```

### Task 7: Implement consumer-owned Python workflow migration

**Files:**

- Modify: `standards/python-tooling/versions/1.1/payload.toml`
- Modify: `standards/python-tooling/versions/1.1/providers/python_tooling.py`
- Modify: `standards/python-tooling/versions/1.1/schemas/migration-report.schema.json`
- Modify: `standards/python-tooling/versions/1.1/README.md`
- Modify: `standards/python-tooling/standard.toml`
- Modify: `catalogs/5.toml`
- Modify: `tests/package_contract/test_python_tooling_reconstruction.py`

- [ ] **Step 1: Add failing materialization, verification, and migration tests**

Cover:

- managed default materializes and verifies the workflow;
- consumer-owned mode omits only `.github/workflows/check.yml` while retaining `.python-version` and `scripts/check.py`;
- `ci.*` remains schema-valid but inert in consumer-owned mode;
- known consumer-owned workflow produces a field-free preserve claim;
- unknown consumer-owned workflow produces the exact pointer/target/digest claim;
- unknown managed workflow remains blocked;
- migrate/reconcile/disable/re-enable preserves consumer bytes and creates no lock/action state;
- source and extracted-wheel providers return identical results.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -k 'workflow_ownership or consumer_owned' -q
```

Expected: the option and predicate/claim behavior are absent.

- [ ] **Step 3: Add conditional workflow materialization and signature binding**

In `payload.toml`:

```toml
[[contributions.when_any]]
option = "workflow_ownership"
equals = "managed"

[[legacy_signatures]]
id = "legacy-check-workflow"
kind = "whole-file"
targets = [".github/workflows/check.yml"]
known_content_digests = ["sha256:16a65f2bdc06adfc814786201ec32937bad4b5930cbf2bf722489007150c933e"]
consumer_owned_intent_pointer = "/python_tooling/workflow_ownership"
```

Place the `when_any` table under the `check-workflow` contribution only.

- [ ] **Step 4: Make verification ownership-aware**

```python
targets = [".python-version", "scripts/check.py"]
if config.get("workflow_ownership") == "managed":
    targets.insert(1, ".github/workflows/check.yml")
for target in targets:
    # retain the existing regular-file and digest checks
```

- [ ] **Step 5: Emit the correct known or unknown migration claim**

Copy raw `coverage` and `workflow_ownership` through normal JSON-safe option handling and add both recognized pointers. For `legacy-check-workflow`:

```python
consumer_owned = namespace.get("workflow_ownership") == "consumer-owned"
if state.get("known") is True and isinstance(digest, str):
    claim = _claim(
        ownership="consumer-owned" if consumer_owned else "managed",
        disposition="preserve" if consumer_owned else "adopt",
        intent_pointer=None,
    )
elif consumer_owned and isinstance(digest, str):
    claim = _claim(
        ownership="consumer-owned",
        disposition="preserve",
        intent_pointer="/python_tooling/workflow_ownership",
    )
else:
    findings.append(_modified_finding(signature_id, target))
```

The provider must not add its package-specific modified finding for the valid unknown consumer-owned case.

- [ ] **Step 6: Extend the installed provider-output schema and package docs**

Add optional `intent_pointer` to `$defs.claim.properties` without adding it to `required`. Document `workflow_ownership`, managed-only `ci.*`, unmanaged/unvalidated consumer responsibility, and the separate return-to-managed boundary.

- [ ] **Step 7: Refresh Python Tooling resource and aggregate digests**

Run `sha256sum` for the three changed resources and replace their exact entries in `payload.toml`. Then print the new aggregate:

```bash
sha256sum standards/python-tooling/versions/1.1/README.md standards/python-tooling/versions/1.1/providers/python_tooling.py standards/python-tooling/versions/1.1/schemas/migration-report.schema.json
uv run python - <<'PY'
from pathlib import Path
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

root = Path("standards/python-tooling/versions/1.1")
manifest = load_payload_manifest(root / "payload.toml")
print(validate_payload_integrity(root, manifest).aggregate_digest.value)
PY
```

Write the aggregate to `standards/python-tooling/standard.toml` and the `python-tooling@1.1` catalog-5 entry, then run:

```bash
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards standards validate-packages --root . --json
```

Expected: projection and package validation pass before any source/wheel test runs.

- [ ] **Step 8: Run Python Tooling reconstruction and installed-wheel tests**

Run:

```bash
uv run pytest tests/package_contract/test_python_tooling_reconstruction.py -q
```

Expected: all source and wheel reconstruction tests pass.

- [ ] **Step 9: Commit the Python workflow unit**

```bash
git add standards/python-tooling/versions/1.1 standards/python-tooling/standard.toml catalogs/5.toml tests/package_contract/test_python_tooling_reconstruction.py
git commit -m "feat(python-tooling): preserve consumer-owned workflow"
```

### Task 8: Synchronize Standard Bundle Authoring guidance and generated descriptions

**Files:**

- Modify: `standards/standard-bundle-authoring/versions/2.0/README.md`
- Modify: `standards/standard-bundle-authoring/versions/2.0/templates/legacy-signature.toml`
- Modify: `standards/standard-bundle-authoring/versions/2.0/payload.toml`
- Modify: `standards/standard-bundle-authoring/standard.toml`
- Modify: `catalogs/5.toml`
- Modify: `src/project_standards/package_contract/payload.py`
- Modify: `src/project_standards/control_plane/migration.py`
- Regenerate: `src/project_standards/schemas/standard-payload.schema.json`
- Regenerate: `src/project_standards/schemas/migration-report.schema.json`
- Modify: `tests/package_contract/test_self_hosting.py`
- Modify: `tests/package_contract/test_payload.py`
- Modify: `tests/control_plane/test_schemas.py`

- [ ] **Step 1: Add failing canonical-guide and schema-description assertions**

Assert the README and template mention `consumer_owned_intent_pointer`, whole-file/single-target restriction, literal raw intent, and the fact that the field is not package-history evidence. Assert generated descriptions no longer say every claim/disposition is exactly recognized history.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/package_contract/test_self_hosting.py tests/package_contract/test_payload.py tests/control_plane/test_schemas.py -q
```

Expected: documentation/template assertions fail against the old absolute wording.

- [ ] **Step 3: Revise the canonical authoring surfaces**

Replace the absolute rule with this bounded distinction:

```markdown
Legacy signatures recognize exact package-history bytes through `known_content_digests`. Unknown bounded blocks and every ownership-acquiring or destructive transition block automatic migration. A single-target whole-file signature may additionally declare `consumer_owned_intent_pointer`; this authorizes only the FR-037 consumer-owned preserve path and never adds observed bytes to package history.
```

Add a commented whole-file example to `legacy-signature.toml`. Update `LegacySignatureDeclaration`, `LegacyDisposition`, and `LegacyClaim` docstrings so both generated schemas express the same distinction.

- [ ] **Step 4: Refresh Standard Bundle Authoring integrity**

Run `sha256sum` for `README.md` and `templates/legacy-signature.toml`, replace their exact resource entries in `payload.toml`, then print the new aggregate:

```bash
sha256sum standards/standard-bundle-authoring/versions/2.0/README.md standards/standard-bundle-authoring/versions/2.0/templates/legacy-signature.toml
uv run python - <<'PY'
from pathlib import Path
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

root = Path("standards/standard-bundle-authoring/versions/2.0")
manifest = load_payload_manifest(root / "payload.toml")
print(validate_payload_integrity(root, manifest).aggregate_digest.value)
PY
```

Write the aggregate to `standards/standard-bundle-authoring/standard.toml` and its catalog-5 entry, then require:

```bash
uv run project-standards standards validate-packages --root . --json
```

Expected: package validation passes before self-hosting or source/wheel tests run.

- [ ] **Step 5: Regenerate schemas and run focused tests**

Run:

```bash
uv run project-standards standards generate-package-schemas --root .
uv run pytest tests/package_contract/test_self_hosting.py tests/package_contract/test_payload.py tests/control_plane/test_schemas.py -q
```

Expected: authoring, model-description, and schema tests pass.

- [ ] **Step 6: Commit the authoring synchronization**

```bash
git add standards/standard-bundle-authoring/versions/2.0 standards/standard-bundle-authoring/standard.toml catalogs/5.toml src/project_standards/package_contract/payload.py src/project_standards/control_plane/migration.py src/project_standards/schemas tests/package_contract/test_self_hosting.py tests/package_contract/test_payload.py tests/control_plane/test_schemas.py
git commit -m "docs(authoring): explain ownership relinquishment"
```

### Task 9: Prove the disposable v5 release migration

**Files:**

- Create: `tests/fixtures/package_compatibility/legacy/release-root/manifest.toml`
- Create: `tests/fixtures/package_compatibility/legacy/release-root/files/**`
- Modify: `tests/package_compatibility/release_candidate.py`
- Modify: `tests/package_compatibility/test_release_candidate.py`
- Modify: `docs/STATUS.md`
- Modify: `docs/TODO.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/handoff/state.md`
- Modify: `docs/handoff/sessions/2026-07.md`
- Refresh: `docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md`

- [ ] **Step 1: Make disposable legacy input independent of live root authority**

Create a complete pre-intent legacy overlay. Derive its required path set from every catalog-5 payload legacy signature plus `.project-standards.yml`; do not hand-maintain a count. `manifest.toml` records each derived path as `file` or `absent`, and `files/**` stores every pre-atomic regular-file byte, including the optimized unknown workflow, V1 check script, instruction files, VS Code inputs, and Agent Handoff legacy manifest. Add a test that recomputes the declared signature-target set and fails on a missing or extra overlay entry.

Add `prepare_legacy_release_checkout(source_root, target)` that copies the Git-known source tree, removes copied `.standards/` only inside the disposable checkout, removes every manifest-listed path, and then restores only entries declared `file`. This ensures a post-atomic root cannot leak unified or absent bytes into the legacy replay.

```python
_LEGACY_RELEASE_FIXTURE = Path(
    "tests/fixtures/package_compatibility/legacy/release-root"
)


def prepare_legacy_release_checkout(source_root: Path, target: Path) -> Path:
    checkout = copy_tracked_checkout(target, source_root=source_root)
    shutil.rmtree(checkout / ".standards", ignore_errors=True)
    overlay = load_legacy_overlay(source_root / _LEGACY_RELEASE_FIXTURE)
    for entry in overlay:
        destination = checkout / entry.path
        if destination.exists() or destination.is_symlink():
            destination.unlink()
        if entry.state == "file":
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                source_root / _LEGACY_RELEASE_FIXTURE / "files" / entry.path,
                destination,
            )
    return checkout
```

The overlay's `.project-standards.yml` is deliberately pre-intent. `declare_release_cut_intent` injects the new Python settings exactly once after preparation. Make `set_release_version` accept either the pre-release `4.3.0` form or an already-versioned `5.0.0` source. Test reconstruction from both a simulated pre-atomic tree and the eventual unified-root shape. Remove direct assertions that the live source root contains `.project-standards.yml`.

```python
content = path.read_text(encoding="utf-8")
if before in content:
    assert content.count(before) == 1, path
    path.write_text(content.replace(before, after), encoding="utf-8")
else:
    assert content.count(after) == 1, path
```

- [ ] **Step 2: Add post-implementation release-intent and preservation assertions**

Update `declare_release_cut_intent` to write:

```yaml
additional_dev_dependencies:
  - 'types-PyYAML'
  - 'pytest-xdist>=3.8'
coverage:
  parallel: true
  patch:
    - 'subprocess'
workflow_ownership: 'consumer-owned'
```

Retain all three repository markers: `compatibility`, `performance`, and `release_replay`. In the disposable release test, snapshot the optimized root workflow before migration and assert byte identity afterward.

- [ ] **Step 3: Separate executable proof from retained-evidence currency**

Remove `assert_release_evidence_current()` from the migration/replay test's preamble. Have the proof helper return the release patch plus config/catalog/lock digests; keep evidence-currency assertions in a separate test so TDD can execute migration before retained prose is refreshed.

- [ ] **Step 4: Run the post-implementation disposable proof**

Run:

```bash
uv run pytest tests/package_compatibility/test_release_candidate.py::test_disposable_release_checkout_migrates_and_reaches_fixed_point -q
```

Expected: migration, apply, and fixed-point reconciliation pass independently of retained-evidence currency.

- [ ] **Step 5: Complete config, preview, workflow, script, and lock assertions**

Assert:

```python
python_config = config.standards["python-tooling"].config
assert python_config["coverage"] == {"parallel": True, "patch": ["subprocess"]}
assert python_config["workflow_ownership"] == "consumer-owned"
assert "pytest-xdist>=3.8" in python_config["additional_dev_dependencies"]
assert "coverage[toml]>=7.10.0" in pyproject["dependency-groups"]["dev"]
assert pyproject["tool"]["coverage"]["run"]["parallel"] is True
assert pyproject["tool"]["coverage"]["run"]["patch"] == ["subprocess"]
assert workflow.read_bytes() == workflow_before
assert ".github/workflows/check.yml" not in locked_paths
assert "coverage erase" in check_script
assert "coverage combine" in check_script
```

Also prove all markers survive; human and JSON previews expose the exact target/digest/intent plus consumer-owned, preserved, not-semantically-validated labeling; no matching target/unit/action/lock state exists; and the second reconciliation has no create/update/remove actions. Execute the migrated parallel-aware `scripts/check.py` successfully in the disposable checkout rather than relying only on substrings. Prevent recursive execution of the release-replay test itself:

```python
gate_environment = {
    **environment,
    "PYTEST_ADDOPTS": '-m "not release_replay"',
}
gate = subprocess.run(
    [sys.executable, "scripts/check.py"],
    cwd=checkout,
    env=gate_environment,
    check=False,
    capture_output=True,
    text=True,
)
assert gate.returncode == 0, gate.stdout + gate.stderr
```

- [ ] **Step 6: Reconcile implementation traceability before evidence hashing**

Mark CP01/BA02 FR-037 and CP01 FR-038 Passing only after their focused, source/wheel, and lifecycle tests pass. Update TODO and handoff to leave refreshed release evidence and atomic migration as the remaining P0 work. Do not edit these release-input files again before the retained-evidence test is green.

- [ ] **Step 7: Refresh retained evidence from the stable pre-atomic tree**

Update the evidence file's release-input digest from `release_input_digest()`. Run the separate evidence-currency test once to obtain the newly executed release-patch/config/catalog/lock digests, update only those values in the evidence file, then run:

```bash
uv run pytest tests/package_compatibility/test_release_candidate.py -q
uv run pytest tests/package_compatibility/test_catalog_matrix.py -q
```

Expected: disposable migration, fixed point, retained-evidence currency, source/wheel matrix, and performance rows pass. The evidence file is excluded from its own input digest, so the final evidence-only correction does not invalidate the proof.

- [ ] **Step 8: Commit the release proof**

```bash
git add tests/fixtures/package_compatibility/legacy/release-root tests/package_compatibility/release_candidate.py tests/package_compatibility/test_release_candidate.py tests/package_compatibility/test_catalog_matrix.py docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md docs/STATUS.md docs/TODO.md docs/handoff
git commit -m "test(v5): preserve optimized Python gate in migration"
```

### Task 10: Verify integrity metadata and run the implementation gate

**Files:**

- Verify generated digests in: `standards/python-tooling/standard.toml`, `standards/python-tooling/versions/1.1/payload.toml`, `standards/standard-bundle-authoring/versions/2.0/payload.toml`, `standards/standard-bundle-authoring/standard.toml`, `catalogs/5.toml`
- Verify projection: `src/project_standards/payloads/**`

- [ ] **Step 1: Check schemas, payload projection, and package integrity**

Run:

```bash
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
catalog_output="$(mktemp -p "$PWD" .catalog-check.XXXXXX.toml)"
trap 'rm -f "$catalog_output"' EXIT
uv run project-standards standards render-consumer-catalog --root . --catalog-major 5 --output "$catalog_output" --tool-release 5.0.0
uv run project-standards standards render-consumer-catalog --root . --catalog-major 5 --output "$catalog_output" --tool-release 5.0.0 --check
rm "$catalog_output"
trap - EXIT
```

Expected: all commands exit 0 and generated checks report no drift. The catalog round trip uses a temporary output so the root `.standards/` directory remains absent until the atomic v5 release commit. Any schema/projection drift returns to the task that owns those bytes and requires another evidence refresh; this final gate does not mutate release inputs.

- [ ] **Step 2: Run focused suites**

```bash
uv run pytest tests/package_contract/test_paths.py tests/package_contract/test_payload.py tests/package_contract/test_schemas.py tests/package_contract/test_self_hosting.py tests/control_plane/test_migration.py tests/control_plane/test_schemas.py tests/package_contract/test_python_tooling_reconstruction.py tests/package_compatibility/test_release_candidate.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run the complete repository gate**

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run python scripts/run_repository_tests.py
uv run pip-audit
npm ci
uv run pytest tests/coherence
npm audit
npx prettier --check .
npx markdownlint-cli2
```

Expected: every command exits 0, combined coverage meets the configured threshold, coverage shards are removed, and both Python and npm dependency audits report no actionable vulnerability.

- [ ] **Step 4: Run package, document, spec, and handoff gates**

```bash
uv run project-standards validate --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --strict --config .project-standards.yml
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
git diff --check
```

Expected: all commands exit 0; only documented pre-existing append-only session warnings may remain.

- [ ] **Step 5: Confirm the final gate introduced no new diff**

Run `git status --short` and compare it with the recorded pre-gate status. Task 10 is verification-only; any new tracked or untracked output is a failure to clean up or a return to the owning implementation task, not a catch-all commit.

### Task 11: Perform the atomic root-script migration in the v5 release commit

**Files:**

- Modify then remove atomically: `.project-standards.yml`
- Modify only at release time: `scripts/check.py`
- Modify only at release time: `tests/test_adopt_dogfood.py`
- Modify only at release time: `AGENTS.md`
- Preserve: `src/project_standards/bundles/python-tooling/check.py`
- Create only in the atomic release commit: `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`
- Refresh: `docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md`

- [ ] **Step 1: Verify the pre-migration twin and frozen V1 digest**

Run:

```bash
uv run pytest tests/test_adopt_dogfood.py::test_dogfoodable_templates_match_repo_root_byte_for_byte -q
sha256sum scripts/check.py src/project_standards/bundles/python-tooling/check.py
```

Expected: the two legacy files are byte-identical before migration.

- [ ] **Step 2: Inject the reviewed live legacy intent and verify preview**

Before preview, apply the same explicit Python Tooling intent used by the disposable fixture to the live `.project-standards.yml`: `types-PyYAML`, `pytest-xdist>=3.8`, all three markers, the retained coverage exclusion, `coverage.parallel = true`, `coverage.patch = ["subprocess"]`, and `workflow_ownership = "consumer-owned"`. This edit is transient: it must be consumed and removed by the same atomic migration, never committed as an intermediate legacy state.

Run both previews:

```bash
uv run project-standards init --catalog 5 --migrate --repo .
uv run project-standards init --catalog 5 --migrate --repo . --json
```

Assert the workflow claim's exact path, observed digest, `intent_pointer`, consumer-owned/preserve disposition, and not-semantically-validated label; assert no workflow action/unit/lock entry and the parallel coverage/script rendering before apply.

- [ ] **Step 3: Apply the reviewed v5 migration atomically**

Run:

```bash
uv run project-standards init --catalog 5 --migrate --apply --repo .
```

The apply must create the three `.standards/` files, replace root `scripts/check.py` with the non-default V2 rendering, preserve the optimized workflow bytes, and remove `.project-standards.yml` in the same reviewed commit.

- [ ] **Step 4: Retire only the obsolete root-script dogfood mapping**

Remove `"python-tooling/check.py": "scripts/check.py"` from `_DOGFOOD`. Add separate assertions:

```python
def test_frozen_v1_python_check_bundle_digest() -> None:
    assert _sha256(_BUNDLES / "python-tooling/check.py") == FROZEN_V1_CHECK_DIGEST


def test_root_check_script_matches_current_v2_rendering(tmp_path: Path) -> None:
    installed = tmp_path / "project_standards"
    shutil.copytree(
        _REPO / "src/project_standards",
        installed,
        symlinks=False,
    )
    distribution = InstalledDistribution(
        installed,
        tool_release="5.0.0",
    )
    request = build_planner_request(_REPO, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert (_REPO / "scripts/check.py").read_bytes() == plan.proposed_content(
        "scripts/check.py"
    )
```

Do not modify the frozen bundle bytes.

- [ ] **Step 5: Switch root validation commands to unified authority**

Update the AGENTS dogfood command and any active release-checklist command that passes `--config .project-standards.yml` so post-migration validation resolves from `.standards/config.toml`. Keep explicit legacy/debug-config examples only where they intentionally test migration.

- [ ] **Step 6: Rerun the post-atomic release checklist**

Rerun the Task 9 disposable proof from the now-stable unified root, refresh its release-input and executed output digests in the retained evidence, and require the separate evidence-currency test to pass. Then rerun Task 10's complete gate with the document commands changed to `project-standards validate`, `project-standards spec validate`, and `project-standards spec lint --strict` without the legacy `--config`. The disposable proof must still pass because it reconstructs its own legacy authority and frozen V1 script. Also run the exact release checklist in `meta/versioning.md`. Confirm the optimized workflow is unchanged, the root script is parallel-aware, `.standards/` is complete, `.project-standards.yml` is absent, and fixed-point reconciliation contains no mutating actions.

- [ ] **Step 7: Commit as part of the atomic v5 release commit**

Stage the complete reviewed release set, including `.standards/`, root-script transition, metadata/version changes, release evidence, and legacy-authority removal. Do not create a standalone partial migration commit.

## Plan self-review checklist

- [x] Every CP01 FR-037/FR-038 and BA02 FR-037 acceptance item maps to a task and executable test.
- [x] Default Python Tooling output and known CLI Documentation claims have explicit regression coverage.
- [x] Unknown-and-unclaimed, wrong-target, wrong-pointer, bounded, managed, destructive, shared, and lock-import cases remain fail closed.
- [x] Provider output, central models, generated schemas, package schemas, payload digests, projections, and source/wheel behavior change together.
- [x] Standard Bundle Authoring guidance and generated descriptions cannot retain the obsolete absolute unknown-byte statement.
- [x] Root `.standards/` creation and root-script/V1-twin retirement remain isolated to the atomic release commit.
- [x] No step begins `project-toolbox` or `agent-managed-repo` work before v5.0.0.
