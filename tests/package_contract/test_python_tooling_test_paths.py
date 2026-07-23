"""Pin python-tooling 1.8 declared pytest collection roots (5.8.0 FR-001..004 / issue #31).

python-tooling 1.7 hardcodes ``tests`` as the sole pytest collection root across
the pytest ``testpaths`` key, both checker ``include`` tables, the Ruff ``src``
value, and the VS Code ``pytestArgs`` setting. Issue #31 adds a ``pytest.test_paths``
option that drives all four surfaces while leaving coverage sources governed only
by ``additional_source_roots``. These tests compare the 1.7 predecessor against the
1.8 successor to prove the new behavior, byte-identical defaults, closed schema
validation, governance, and verbatim migration carriage.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.control_plane.planner_helpers import resolution_request

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V17_PAYLOAD = _FAMILY / "versions/1.7"
_V18_PAYLOAD = _FAMILY / "versions/1.8"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, **overrides: object) -> JsonObject:
    manifest = load_payload_manifest(root / "payload.toml")
    schema = load_option_schema(root, manifest)
    return schema.resolve_options(cast("JsonObject", overrides))


def _render(
    root: Path,
    scope: str,
    adapter: AdapterKind,
    config: JsonObject,
    *,
    target: str = "pyproject.toml",
) -> str:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={
                "planned_contribution": {
                    "id": "test-unit",
                    "target": target,
                    "adapter": adapter.value,
                    "scope": scope,
                }
            },
        )
    )
    assert result.effect is ProviderEffect.CONTENT
    assert result.content is not None
    return result.content.decode()


# TC-T7-001
def test_1_7_cannot_express_alternate_collection_root() -> None:
    """1.7 has no pytest.test_paths option, so the closed schema rejects it."""
    with pytest.raises(PackageContractError, match="package options violate schema"):
        _options(_V17_PAYLOAD, pytest={"test_paths": ["qa/tests"]})


# TC-T7-002
def test_test_paths_renders_across_all_four_units() -> None:
    """A declared pytest.test_paths drives the four collection surfaces while
    leaving coverage sources unchanged."""
    config = _options(_V18_PAYLOAD, pytest={"test_paths": ["qa/tests"]})

    testpaths = _render(
        _V18_PAYLOAD, "key:/tool/pytest/ini_options/testpaths", AdapterKind.TOML, config
    )
    assert testpaths == '[tool.pytest.ini_options]\ntestpaths = ["qa/tests"]\n'

    include = _render(_V18_PAYLOAD, "key:/tool/basedpyright/include", AdapterKind.TOML, config)
    assert include == '[tool.basedpyright]\ninclude = ["src", "qa/tests"]\n'

    ruff = _render(_V18_PAYLOAD, "table:/tool/ruff", AdapterKind.TOML, config)
    assert 'src = ["src", "qa/tests"]' in ruff

    pytest_args = _render(
        _V18_PAYLOAD,
        "key:/python.testing.pytestArgs",
        AdapterKind.JSONC,
        config,
        target=".vscode/settings.json",
    )
    assert pytest_args == '{"python.testing.pytestArgs":["qa/tests"]}'

    coverage = _render(_V18_PAYLOAD, "table:/tool/coverage/run", AdapterKind.TOML, config)
    assert coverage == '[tool.coverage.run]\nbranch = true\nsource = ["src"]\n'


def _materialized_units(root: Path, config: JsonObject) -> dict[str, str]:
    """Render every materializing contribution for one config into id->bytes."""
    manifest = _payload(root).manifest
    rendered: dict[str, str] = {}
    for contribution in manifest.contributions:
        if not contribution.materializes(config):
            continue
        rendered[contribution.id] = _render(
            root,
            contribution.scope,
            contribution.adapter,
            config,
            target=contribution.target.original,
        )
    return rendered


# TC-T7-003
@pytest.mark.parametrize(
    "overrides",
    [
        {},
        # Overlap: declaring the default collection root in additional_source_roots
        # must not shift any byte relative to 1.7's hardcoded tests handling.
        {"additional_source_roots": ["tests"]},
        {"additional_source_roots": [{"path": "tests", "coverage": True}]},
    ],
)
def test_default_and_overlap_configs_render_byte_identical_to_1_7(
    overrides: JsonObject,
) -> None:
    """Undeclared (default tests) and overlap configs render identically to 1.7."""
    v17_units = _materialized_units(_V17_PAYLOAD, _options(_V17_PAYLOAD, **overrides))
    v18_units = _materialized_units(_V18_PAYLOAD, _options(_V18_PAYLOAD, **overrides))

    assert set(v17_units) == set(v18_units)
    for unit_id, rendered in v17_units.items():
        assert v18_units[unit_id] == rendered, unit_id


# TC-T7-004
@pytest.mark.parametrize(
    "test_paths",
    [
        [],  # minItems: at least one root
        ["tests", "tests"],  # uniqueItems
        ["/absolute"],  # unsafe leading slash
        ["../escape"],  # unsafe parent traversal
        [".."],  # dot-only segment
        ["back\\slash"],  # non-portable separator
        "tests",  # not an array
        [1],  # non-string entry
    ],
)
def test_test_paths_schema_rejections(test_paths: object) -> None:
    """Empty, duplicate, unsafe, and mistyped collection roots fail closed."""
    with pytest.raises(PackageContractError, match="package options violate schema"):
        _options(_V18_PAYLOAD, pytest={"test_paths": test_paths})


def test_test_paths_unknown_pytest_key_is_rejected() -> None:
    """The pytest object stays closed; an unknown sibling key fails resolution."""
    with pytest.raises(PackageContractError, match="package options violate schema"):
        _options(_V18_PAYLOAD, pytest={"test_paths": ["tests"], "unknown_key": True})


_GOVERNED_CONTRIBUTIONS = (
    "pytest-testpaths",
    "vscode-pytest-args",
    "basedpyright-include",
    "pyright-include",
    "ruff-config",
)


# TC-T7-005
def test_governing_options_name_test_paths_on_conflict(tmp_path: Path) -> None:
    """All four affected surfaces govern with /pytest/test_paths and conflicts name it."""
    payload = _payload(_V18_PAYLOAD)
    by_id = {item.id: item for item in payload.manifest.contributions}
    for contribution_id in _GOVERNED_CONTRIBUTIONS:
        governing = by_id[contribution_id].governing_options
        assert governing is not None, contribution_id
        assert "/pytest/test_paths" in governing, contribution_id

    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / "pyproject.toml").write_bytes(b'[tool.basedpyright]\ninclude = ["src"]\n')
    request = PlannerRequest(
        repo,
        resolution_request(
            (payload,),
            configs={"python-tooling": {"pytest": {"test_paths": ["qa/tests"]}}},
        ),
        (payload,),
    )

    plan = plan_reconciliation(request)

    assert not plan.applicable
    conflict = next(
        finding
        for finding in plan.findings
        if finding.code == "CP-CONSUMER-CONFLICT"
        and finding.identity == "key:/tool/basedpyright/include"
    )
    assert conflict.governing_options is not None
    assert "/pytest/test_paths" in conflict.governing_options


def _migrate(namespace: JsonObject) -> JsonObject:
    payload = _payload(_V18_PAYLOAD)
    result = invoke_provider(
        ProviderInvocation(
            repo=_V18_PAYLOAD,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="migrate-legacy",
            operation=ProviderOperation.MIGRATE,
            effective_config={},
            snapshots={
                "legacy_config": {
                    "standards_version": "v4",
                    "python_tooling": namespace,
                },
                "legacy_signatures": {},
            },
        )
    )
    assert result.migration_report is not None
    return result.migration_report.package.config


# TC-T7-006
def test_migrations_carry_values_and_affected_list_covers_delta() -> None:
    """Migrations carry declared test_paths verbatim, never invent them, and the
    affected list covers the real 1.7->1.8 rendered delta."""
    carried = _migrate({"version": "1.0", "pytest": {"test_paths": ["qa/unit", "qa/integration"]}})
    assert cast("JsonObject", carried["pytest"])["test_paths"] == ["qa/unit", "qa/integration"]

    # No invention: an undeclared collection root must not appear in either the
    # package-to-package or the legacy migration output.
    without_pytest = _migrate({"version": "1.0"})
    assert "pytest" not in without_pytest
    pytest_without_paths = _migrate({"version": "1.0", "pytest": {"fail_under": 90}})
    assert "test_paths" not in cast("JsonObject", pytest_without_paths["pytest"])

    config = _options(_V18_PAYLOAD, pytest={"test_paths": ["qa/tests"]})
    predecessor_config = _options(_V17_PAYLOAD, additional_source_roots=[])
    v18_units = _materialized_units(_V18_PAYLOAD, config)
    v17_units = _materialized_units(_V17_PAYLOAD, predecessor_config)
    delta = {
        unit_id for unit_id, rendered in v18_units.items() if v17_units.get(unit_id) != rendered
    }
    assert delta == {
        "pytest-testpaths",
        "vscode-pytest-args",
        "basedpyright-include",
        "ruff-config",
    }

    migration = next(
        item
        for item in _payload(_V18_PAYLOAD).manifest.migrations
        if item.id == "python-tooling-1-7-to-1-8"
    )
    affected = set(migration.affected)
    assert {f"contribution:{unit_id}" for unit_id in delta} <= affected


def _multi_root_config(root: Path, additional: list[object]) -> JsonObject:
    return _options(
        root,
        pytest={"test_paths": ["qa/unit", "qa/integration"]},
        additional_source_roots=additional,
    )


# TC-T7-007
@pytest.mark.parametrize(
    "overlap",
    [
        ["qa/integration", {"path": "scripts", "coverage": False}],
        [{"path": "qa/integration", "coverage": True}, {"path": "scripts", "coverage": False}],
    ],
)
def test_multi_root_ordering_and_cross_option_overlap_semantics(
    overlap: list[object],
) -> None:
    """Declared order holds after the layout root; a path in both test_paths and
    additional_source_roots dedupes first-wins in include while keeping its
    additional_source_roots coverage semantics."""
    config = _multi_root_config(_V18_PAYLOAD, overlap)

    include = _render(_V18_PAYLOAD, "key:/tool/basedpyright/include", AdapterKind.TOML, config)
    assert include == (
        '[tool.basedpyright]\ninclude = ["src", "qa/unit", "qa/integration", "scripts"]\n'
    )
    coverage = _render(_V18_PAYLOAD, "table:/tool/coverage/run", AdapterKind.TOML, config)
    assert coverage == '[tool.coverage.run]\nbranch = true\nsource = ["src", "qa/integration"]\n'
    testpaths = _render(
        _V18_PAYLOAD, "key:/tool/pytest/ini_options/testpaths", AdapterKind.TOML, config
    )
    assert testpaths == '[tool.pytest.ini_options]\ntestpaths = ["qa/unit", "qa/integration"]\n'
    ruff = _render(_V18_PAYLOAD, "table:/tool/ruff", AdapterKind.TOML, config)
    assert 'src = ["src", "qa/unit", "qa/integration", "scripts"]' in ruff
