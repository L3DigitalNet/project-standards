"""Pin the bounded Python Tooling 1.8 to 1.9 successor contract."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.migration import MigratedPackage
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    MigrationMode,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
    validate_configuration_transform_eligibility,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V18 = _FAMILY / "versions/1.8"
_V19 = _FAMILY / "versions/1.9"
_V18_RELEASED_DIGEST = "sha256:7397498723a1f683b09037c233e1872df825cd70a27c514a45bb2bacf24cb312"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(**overrides: object) -> JsonObject:
    payload = _payload(_V19)
    schema = load_option_schema(_V19, payload.manifest)
    return schema.resolve_options(cast("JsonObject", overrides))


def _family_version_roots() -> dict[str, Path]:
    family = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = cast("list[dict[str, object]]", family["versions"])
    return {
        cast(str, version["version"]): _FAMILY / Path(cast(str, version["payload"])).parent
        for version in versions
    }


def _direct_performance_declaration(document: JsonObject) -> JsonObject | None:
    properties = document.get("properties")
    if not isinstance(properties, dict):
        raise AssertionError("performance declaration is underivable")
    ci = properties.get("ci")
    if ci is None:
        return None
    if not isinstance(ci, dict):
        raise AssertionError("performance declaration is underivable")
    ci_properties = ci.get("properties")
    if not isinstance(ci_properties, dict):
        raise AssertionError("performance declaration is underivable")
    performance = ci_properties.get("performance")
    if performance is None:
        return None
    if not isinstance(performance, dict):
        raise AssertionError("performance declaration is underivable")
    return performance


def _qualifies_for_performance_transform(
    document: JsonObject,
    resolved_empty: JsonObject | None,
) -> bool:
    if _direct_performance_declaration(document) is None:
        return False
    if resolved_empty is None:
        raise AssertionError("resolved empty performance value is underivable")
    ci = resolved_empty.get("ci")
    if not isinstance(ci, dict) or "performance" not in ci:
        raise AssertionError("resolved empty performance value is absent")
    performance = ci["performance"]
    if not isinstance(performance, bool):
        raise AssertionError("resolved empty performance value is not boolean")
    return performance


def _qualifying_predecessors() -> set[str]:
    qualifiers: set[str] = set()
    for version, root in _family_version_roots().items():
        if version == "1.9":
            continue
        payload = _payload(root)
        schema = load_option_schema(root, payload.manifest)
        if _qualifies_for_performance_transform(
            schema.document,
            schema.resolve_options({}),
        ):
            qualifiers.add(version)
    return qualifiers


def _source_options(version: str, config: JsonObject) -> JsonObject:
    root = _family_version_roots()[version]
    payload = _payload(root)
    schema = load_option_schema(root, payload.manifest)
    return schema.resolve_options(config)


def _migrate_config(
    source_version: str,
    config: JsonObject,
    source_effective: JsonObject,
) -> MigratedPackage:
    payload = _payload(_V19)
    result = invoke_provider(
        ProviderInvocation(
            repo=_V19,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="migrate-config",
            operation=ProviderOperation.MIGRATE,
            effective_config=source_effective,
            snapshots={
                "configuration_transform": {
                    "migration_id": (f"python-tooling-{source_version.replace('.', '-')}-to-1-9"),
                    "source": f"package:{source_version}",
                    "target": "package:1.9",
                    "provider_id": "migrate-config",
                    "selector": "latest",
                    "raw_config": config,
                    "declared_pointers": ["/ci/performance"],
                }
            },
        )
    )
    assert result.migration_report is not None
    return result.migration_report.package


def _render(
    scope: str,
    adapter: AdapterKind,
    config: JsonObject,
    *,
    target: str = "pyproject.toml",
) -> str:
    payload = _payload(_V19)
    result = invoke_provider(
        ProviderInvocation(
            repo=_V19,
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


def _materialized_units(config: JsonObject) -> dict[str, str]:
    payload = _payload(_V19)
    return {
        contribution.id: _render(
            contribution.scope,
            contribution.adapter,
            config,
            target=contribution.target.original,
        )
        for contribution in payload.manifest.contributions
        if contribution.materializes(config)
    }


def _migrate(namespace: JsonObject) -> JsonObject:
    payload = _payload(_V19)
    result = invoke_provider(
        ProviderInvocation(
            repo=_V19,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="migrate-legacy",
            operation=ProviderOperation.MIGRATE,
            effective_config={},
            snapshots={
                "legacy_config": {
                    "standards_version": "v5",
                    "python_tooling": namespace,
                },
                "legacy_signatures": {},
            },
        )
    )
    assert result.migration_report is not None
    return result.migration_report.package.config


# TC-T8-001
def test_python_tooling_1_9__nonempty_additive_lists__render_canonical_native_keys() -> None:
    config = _options(
        ruff={
            "extend_include": ["tools/**/*.py", "bin/check"],
            "extend_select": ["D", "S"],
            # B is baseline-selected; explicit suppression remains reviewed intent.
            "extend_ignore": ["B"],
        },
        coverage={"omit": ["src/generated/*", "tests/fixtures/*"]},
    )

    ruff = _render("table:/tool/ruff", AdapterKind.TOML, config)
    coverage = _render("table:/tool/coverage/run", AdapterKind.TOML, config)

    assert 'extend-include = ["tools/**/*.py", "bin/check"]' in ruff
    assert 'extend-select = ["D", "S"]' in ruff
    assert 'extend-ignore = ["B"]' in ruff
    assert 'omit = ["src/generated/*", "tests/fixtures/*"]' in coverage


def test_python_tooling_1_9__empty_additive_lists__render_no_keys() -> None:
    config = _options()

    ruff = _render("table:/tool/ruff", AdapterKind.TOML, config)
    coverage = _render("table:/tool/coverage/run", AdapterKind.TOML, config)

    assert "extend-include =" not in ruff
    assert "extend-select =" not in ruff
    assert "extend-ignore =" not in ruff
    assert "omit =" not in coverage


@pytest.mark.parametrize(
    ("overrides", "option"),
    [
        pytest.param(
            {"ruff": {"extend_include": [""]}},
            "ruff.extend_include",
            id="empty-ruff-path",
        ),
        pytest.param(
            {"ruff": {"extend_select": ["lowercase"]}},
            "ruff.extend_select",
            id="invalid-select",
        ),
        pytest.param(
            {"ruff": {"extend_ignore": ["B", "B"]}},
            "ruff.extend_ignore",
            id="duplicate-ignore",
        ),
        pytest.param(
            {"coverage": {"omit": [""]}},
            "coverage.omit",
            id="empty-coverage-path",
        ),
    ],
)
def test_python_tooling_1_9__invalid_additive_lists__name_option(
    overrides: JsonObject,
    option: str,
) -> None:
    with pytest.raises(PackageContractError, match=option.replace(".", r"\.")):
        _options(**overrides)


@pytest.mark.parametrize(
    ("section", "value", "option"),
    [
        pytest.param("ruff", {"extend_include": [1]}, "config.ruff.extend_include", id="include"),
        pytest.param("ruff", {"extend_select": [""]}, "config.ruff.extend_select", id="select"),
        pytest.param("ruff", {"extend_ignore": "B"}, "config.ruff.extend_ignore", id="ignore"),
        pytest.param("coverage", {"omit": [1]}, "config.coverage.omit", id="omit"),
    ],
)
def test_python_tooling_1_9__provider_bypass__fails_with_governing_option(
    section: str,
    value: JsonObject,
    option: str,
) -> None:
    config = _options()
    cast("JsonObject", config[section]).update(value)
    scope = "table:/tool/coverage/run" if section == "coverage" else "table:/tool/ruff"

    with pytest.raises(ControlPlaneError) as raised:
        _render(scope, AdapterKind.TOML, config)
    assert isinstance(raised.value.__cause__, ValueError)
    assert option in str(raised.value.__cause__)


# TC-T8-002
def test_python_tooling_1_9__backend_none__omits_only_build_system() -> None:
    baseline = _materialized_units(_options())
    non_installable = _materialized_units(_options(build_backend="none"))

    assert set(baseline) - set(non_installable) == {"build-system"}
    assert set(non_installable) - set(baseline) == set()
    for contribution_id, content in non_installable.items():
        assert content == baseline[contribution_id], contribution_id


# TC-T8-003
def test_python_tooling_1_9__fresh_default__omits_performance_ci() -> None:
    config = _options()

    assert cast("JsonObject", config["ci"])["performance"] is False
    workflow = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        config,
        target=".github/workflows/check.yml",
    )
    assert "pytest -m performance" not in workflow


def test_python_tooling_1_9__explicit_performance_without_tests__retains_exit_5(
    tmp_path: Path,
) -> None:
    config = _options(ci={"enabled": True, "performance": True})
    workflow = _render(
        "$file",
        AdapterKind.WHOLE_FILE,
        config,
        target=".github/workflows/check.yml",
    )
    assert "pytest -m performance" in workflow

    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\nmarkers = ["performance: serial performance tests"]\n',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "performance"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 5


@pytest.mark.parametrize(
    ("namespace", "expected"),
    [
        pytest.param({}, {"enabled": True, "performance": True}, id="ci-absent"),
        pytest.param(
            {"ci": {"enabled": True}},
            {"enabled": True, "performance": True},
            id="performance-absent",
        ),
        pytest.param(
            {"ci": {"enabled": True, "performance": True}},
            {"enabled": True, "performance": True},
            id="performance-true",
        ),
        pytest.param(
            {"ci": {"enabled": True, "performance": False}},
            {"enabled": True, "performance": False},
            id="performance-false",
        ),
        pytest.param(
            {"ci": {"enabled": False}},
            {"enabled": False, "performance": False},
            id="ci-disabled",
        ),
    ],
)
def test_python_tooling_1_9__legacy_v4_migration__preserves_effective_performance(
    namespace: JsonObject,
    expected: JsonObject,
) -> None:
    migrated = _migrate(namespace)

    assert migrated["ci"] == expected
    assert cast("JsonObject", _options(**migrated)["ci"]) == expected


def test_python_tooling_1_9__family_predecessors__directly_declare_qualifying_default() -> None:
    predecessors = {
        version: root for version, root in _family_version_roots().items() if version != "1.9"
    }

    for root in predecessors.values():
        payload = _payload(root)
        schema = load_option_schema(root, payload.manifest)
        declaration = _direct_performance_declaration(schema.document)
        assert declaration is not None
        assert declaration.get("type") == "boolean"
        assert declaration.get("default") is True

    assert _qualifying_predecessors() == set(predecessors)


def test_performance_transform_classifier__undeclared_option__does_not_qualify() -> None:
    document: JsonObject = {
        "properties": {
            "ci": {
                "type": "object",
                "properties": {},
            }
        }
    }

    assert not _qualifies_for_performance_transform(document, {})


def test_performance_transform_classifier__resolved_false__does_not_qualify() -> None:
    document: JsonObject = {
        "properties": {
            "ci": {
                "type": "object",
                "properties": {
                    "performance": {
                        "type": "boolean",
                        "default": False,
                    }
                },
            }
        }
    }

    assert not _qualifies_for_performance_transform(
        document,
        {"ci": {"performance": False}},
    )


@pytest.mark.parametrize(
    ("resolved_empty", "message"),
    [
        pytest.param({}, "absent", id="absent"),
        pytest.param(
            {"ci": {"performance": "true"}},
            "not boolean",
            id="nonboolean",
        ),
        pytest.param(None, "underivable", id="underivable"),
    ],
)
def test_performance_transform_classifier__invalid_resolved_value__stops_characterization(
    resolved_empty: JsonObject | None,
    message: str,
) -> None:
    document: JsonObject = {
        "properties": {
            "ci": {
                "type": "object",
                "properties": {
                    "performance": {
                        "type": "boolean",
                        "default": True,
                    }
                },
            }
        }
    }

    with pytest.raises(AssertionError, match=message):
        _qualifies_for_performance_transform(document, resolved_empty)


def test_python_tooling_1_9__qualifying_predecessors__declare_exact_transform_edges() -> None:
    successor = _payload(_V19)
    qualifiers = _qualifying_predecessors()
    target_schema = load_option_schema(_V19, successor.manifest)
    transforms = [
        migration
        for migration in successor.manifest.migrations
        if migration.to_endpoint.package_version == successor.manifest.payload.version
        and migration.configuration_transform is not None
    ]

    actual_sources: set[str] = set()
    for migration in transforms:
        source_version = migration.from_endpoint.package_version
        assert source_version is not None
        actual_sources.add(source_version.value)
    assert actual_sources == qualifiers
    assert len(transforms) == len(qualifiers)
    for source in qualifiers:
        source_root = _family_version_roots()[source]
        source_payload = _payload(source_root)
        validate_configuration_transform_eligibility(
            load_option_schema(source_root, source_payload.manifest),
            target_schema,
            ("/ci/performance",),
        )
        matching = [
            migration
            for migration in transforms
            if migration.from_endpoint.package_version is not None
            and migration.from_endpoint.package_version.value == source
        ]
        assert len(matching) == 1, source
        migration = matching[0]
        assert migration.mode is MigrationMode.AUTOMATIC
        assert migration.provider == "migrate-config"
        assert migration.configuration_transform == ["/ci/performance"]


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param({}, {"ci": {"performance": True}}, id="ci-absent"),
        pytest.param(
            {"ci": {"enabled": True}},
            {"ci": {"enabled": True, "performance": True}},
            id="performance-absent",
        ),
        pytest.param(
            {"ci": {"enabled": True, "performance": True}},
            {"ci": {"enabled": True, "performance": True}},
            id="performance-true",
        ),
        pytest.param(
            {"ci": {"enabled": True, "performance": False}},
            {"ci": {"enabled": True, "performance": False}},
            id="performance-false",
        ),
        pytest.param(
            {"ci": {"enabled": False}},
            {"ci": {"enabled": False}},
            id="ci-disabled",
        ),
    ],
)
def test_python_tooling_1_9__package_config_transform__preserves_effective_performance(
    config: JsonObject,
    expected: JsonObject,
) -> None:
    for source in sorted(_qualifying_predecessors()):
        migrated = _migrate_config(source, config, _source_options(source, config))
        assert migrated.config == expected, source
        assert migrated.recognized_settings == (
            ("/ci/performance",) if config in ({}, {"ci": {"enabled": True}}) else ()
        )


def test_python_tooling_1_9__source_invalid_newer_atomic_value__is_preserved() -> None:
    raw: JsonObject = {
        "additional_source_roots": [{"path": "src"}],
        "ci": {"enabled": True},
    }
    source_effective = _source_options("1.6", {"ci": {"enabled": True}})

    migrated = _migrate_config("1.6", raw, source_effective)

    assert migrated.config == {
        "additional_source_roots": [{"path": "src"}],
        "ci": {"enabled": True, "performance": True},
    }
    assert source_effective["additional_source_roots"] == []
    assert migrated.recognized_settings == ("/ci/performance",)


def test_python_tooling_1_9__same_change_successor_options__remain_sparse() -> None:
    raw: JsonObject = {
        "build_backend": "none",
        "ruff": {
            "extend_include": ["tools/**/*.py"],
            "extend_select": ["D"],
            "extend_ignore": ["B"],
        },
        "coverage": {"omit": ["src/generated/*"]},
        "ci": {"enabled": True},
    }
    source_effective = _source_options("1.8", {"ci": {"enabled": True}})

    migrated = _migrate_config("1.8", raw, source_effective)

    assert migrated.config == {
        **raw,
        "ci": {"enabled": True, "performance": True},
    }
    assert migrated.recognized_settings == ("/ci/performance",)


# TC-T8-004
def test_python_tooling_1_9__package_registration__preserves_1_8_and_root_default() -> None:
    predecessor = _payload(_V18)
    successor = _payload(_V19)

    assert predecessor.integrity.aggregate_digest.value == _V18_RELEASED_DIGEST
    assert successor.manifest.payload.version.value == "1.9"
    migrations = {migration.id for migration in successor.manifest.migrations}
    expected_transforms = {
        f"python-tooling-{version.replace('.', '-')}-to-1-9"
        for version in _qualifying_predecessors()
    }
    assert migrations == {"legacy-v4-to-1-9", *expected_transforms}
    family = (_FAMILY / "standard.toml").read_text(encoding="utf-8")
    assert 'version = "1.9"' in family
    assert successor.integrity.aggregate_digest.value in family
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    entries = [entry for entry in catalog["packages"] if entry["id"] == "python-tooling"]
    assert [entry["version"] for entry in entries if entry["role"] == "default"] == ["1.8"]
    assert "1.9" not in {entry["version"] for entry in entries}
    generated_catalog = (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
    assert (
        generated_catalog.count(
            "| [`python-tooling`](python-tooling/README.md) | active | 1.9 | "
            "unadvertised | consumer |"
        )
        == 1
    )
