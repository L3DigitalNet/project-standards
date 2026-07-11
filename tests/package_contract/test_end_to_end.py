from __future__ import annotations

import random
import shutil
import socket
import subprocess
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest

from project_standards._version import package_version
from project_standards.package_contract import (
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.catalog import render_consumer_catalog
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import PayloadManifest
from project_standards.package_contract.projection import sync_payload_projection
from project_standards.package_contract.schemas import package_schema_bytes
from tests.wheel_helpers import extract_pure_python_wheel

_FULL = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/full"


def test_full_synthetic_repository_validates_and_matches_catalog_golden() -> None:
    repository = build_package_repository(_FULL, catalog_major=5)

    assert validate_package_repository(repository) == ()
    assert repository.catalog is not None
    rendered = render_consumer_catalog(
        repository.catalog,
        repository.family_map,
        repository.payload_map,
        tool_release=package_version(),
    )
    assert rendered == (_FULL / "expected/catalog.toml").read_bytes()


def test_full_fixture_covers_foundation_contract_shapes() -> None:
    repository = build_package_repository(_FULL, catalog_major=5)
    payloads = repository.payload_map

    assert len(repository.families) == 3
    assert len(payloads) == 5
    assert {payload.payload.availability.value for payload in payloads.values()} == {
        "consumer",
        "reference-only",
        "internal",
    }
    assert repository.catalog is not None
    assert {entry.role.value for entry in repository.catalog.packages} == {
        "default",
        "retained",
        "candidate",
        "reference-only",
        "internal",
    }

    alpha = payloads[("alpha", "2.0")]
    assert alpha.artifacts
    assert {item.provider is None for item in alpha.contributions} == {False, True}
    assert any(item.shared_identity for item in alpha.contributions)
    assert alpha.providers
    assert alpha.extensions
    assert alpha.relations.extends == ["beta"]
    assert {migration.mode.value for migration in alpha.migrations} == {
        "automatic",
        "manual",
    }


def _repository_facts(root: Path) -> dict[tuple[str, str], tuple[str, str, tuple[str, ...]]]:
    repository = build_package_repository(root, catalog_major=5)
    assert validate_package_repository(repository) == ()
    return {
        (payload.manifest.payload.standard, payload.manifest.payload.version.value): (
            payload.manifest.model_dump_json(by_alias=True),
            payload.integrity.aggregate_digest.value,
            tuple(item.path.original for item in payload.integrity.inventory),
        )
        for payload in repository.payloads
    }


def _installed_facts(root: Path) -> dict[tuple[str, str], tuple[str, str, tuple[str, ...]]]:
    facts: dict[tuple[str, str], tuple[str, str, tuple[str, ...]]] = {}
    for path in sorted(root.glob("*/*/payload.toml")):
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        manifest = PayloadManifest.model_validate(raw)
        integrity = validate_payload_integrity(path.parent, manifest)
        key = (manifest.payload.standard, manifest.payload.version.value)
        facts[key] = (
            manifest.model_dump_json(by_alias=True),
            integrity.aggregate_digest.value,
            tuple(item.path.original for item in integrity.inventory),
        )
    return facts


def _deny_network(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("installed payload discovery attempted network access")


def test_wheel_rediscovery_is_offline_and_matches_source_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "build"
    shutil.copytree(_FULL / "standards", project / "standards")
    shutil.copytree(_FULL / "catalogs", project / "catalogs")
    package = project / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """[project]
name = "project-standards"
version = "1.0.0"
requires-python = ">=3.14"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**", "catalogs/**"]
""",
        encoding="utf-8",
    )
    assert sync_payload_projection(project, check=False) == ()
    distribution = project / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(distribution)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (wheel,) = distribution.glob("*.whl")
    installed = tmp_path / "installed"
    extract_pure_python_wheel(wheel, installed)

    monkeypatch.setattr(socket, "socket", _deny_network)
    monkeypatch.setattr(socket, "create_connection", _deny_network)
    assert _installed_facts(installed / "project_standards/payloads") == _repository_facts(_FULL)


def test_randomized_discovery_is_byte_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_iterdir = Path.iterdir
    original_rglob = Path.rglob
    generator = random.Random(731)

    def shuffled_iterdir(path: Path) -> Iterator[Path]:
        entries = list(original_iterdir(path))
        generator.shuffle(entries)
        return iter(entries)

    def shuffled_rglob(path: Path, pattern: str) -> Iterator[Path]:
        entries = list(original_rglob(path, pattern))
        generator.shuffle(entries)
        return iter(entries)

    monkeypatch.setattr(Path, "iterdir", shuffled_iterdir)
    monkeypatch.setattr(Path, "rglob", shuffled_rglob)
    fingerprints: set[tuple[object, ...]] = set()
    for _ in range(100):
        repository = build_package_repository(_FULL, catalog_major=5)
        assert repository.catalog is not None
        fingerprints.add(
            (
                tuple(
                    (
                        finding.code,
                        finding.standard_id,
                        finding.version,
                        finding.identity,
                        finding.message,
                    )
                    for finding in validate_package_repository(repository)
                ),
                tuple(payload.integrity.aggregate_digest.value for payload in repository.payloads),
                tuple(package_schema_bytes().items()),
                render_consumer_catalog(
                    repository.catalog,
                    repository.family_map,
                    repository.payload_map,
                    tool_release="5.0.0",
                ),
            )
        )
    assert len(fingerprints) == 1
