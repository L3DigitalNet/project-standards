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


# TC-T8-004
def test_python_tooling_1_9__package_registration__preserves_1_8_and_root_default() -> None:
    predecessor = _payload(_V18)
    successor = _payload(_V19)

    assert predecessor.integrity.aggregate_digest.value == _V18_RELEASED_DIGEST
    assert successor.manifest.payload.version.value == "1.9"
    migrations = {migration.id for migration in successor.manifest.migrations}
    assert migrations == {"legacy-v4-to-1-9"}
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
