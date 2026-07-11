from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.package_contract import PackageContractError
from project_standards.package_contract.projection import sync_payload_projection
from tests.wheel_helpers import extract_pure_python_wheel

_FULL = Path("tests/fixtures/package_contract/valid/full")


def _installed_fixture(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    shutil.copytree(_FULL / "standards", repository / "standards")
    shutil.copytree(_FULL / "catalogs", repository / "catalogs")
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()

    installed = tmp_path / "installed/project_standards"
    shutil.copytree(package, installed)
    return installed


def test_loads_one_installed_catalog_and_verifies_every_payload(tmp_path: Path) -> None:
    installed = _installed_fixture(tmp_path)
    distribution = InstalledDistribution(installed, tool_release="5.1.0")

    catalog = distribution.load_catalog("5")

    assert catalog.source.catalog_major == 5
    assert list(catalog.payload_map) == [
        ("alpha", "1.0"),
        ("alpha", "2.0"),
        ("alpha", "3.0"),
        ("beta", "1.0"),
        ("gamma", "1.0"),
    ]
    assert all(
        payload.integrity.aggregate_digest == entry.digest
        for entry in catalog.source.packages
        for payload in [catalog.payload_map[(entry.id, entry.version.value)]]
    )


def test_installed_distribution_accepts_only_compatible_release_lineage(
    tmp_path: Path,
) -> None:
    installed = _installed_fixture(tmp_path)

    with pytest.raises(PackageContractError, match="tool major"):
        InstalledDistribution(installed, tool_release="4.3.0").load_catalog("5")
    with pytest.raises(PackageContractError, match="newer"):
        InstalledDistribution(installed, tool_release="5.1.0").load_catalog(
            "5", recorded_release="5.2.0"
        )

    loaded = InstalledDistribution(installed, tool_release="5.2.0").load_catalog(
        "5", recorded_release="5.1.0"
    )
    assert loaded.source.catalog_major == 5


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing-catalog", "catalog projection"),
        ("stale-payload", "digest"),
        ("unavailable-payload", "unavailable"),
    ],
)
def test_installed_distribution_fails_closed_on_missing_or_stale_content(
    tmp_path: Path,
    mutation: str,
    expected: str,
) -> None:
    installed = _installed_fixture(tmp_path)
    if mutation == "missing-catalog":
        (installed / "catalogs/5.toml").unlink()
    elif mutation == "stale-payload":
        target = installed / "payloads/alpha/2.0/README.md"
        target.write_bytes(target.read_bytes() + b"stale\n")
    else:
        shutil.rmtree(installed / "payloads/alpha/2.0")

    with pytest.raises(PackageContractError, match=expected):
        InstalledDistribution(installed, tool_release="5.0.0").load_catalog("5")


def test_extracted_wheel_loads_catalog_offline_through_importlib_resources(
    tmp_path: Path,
) -> None:
    project = tmp_path / "build"
    shutil.copytree(_FULL / "standards", project / "standards")
    shutil.copytree(_FULL / "catalogs", project / "catalogs")
    shutil.copytree(Path("src/project_standards"), project / "src/project_standards")
    (project / "pyproject.toml").write_text(
        """[project]
name = "project-standards"
version = "5.0.0"
requires-python = ">=3.14"
dependencies = ["pydantic>=2.13.4", "jsonschema>=4.23.0", "pyyaml>=6.0.2"]

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**", "catalogs/**"]
""",
        encoding="utf-8",
    )
    assert sync_payload_projection(project, check=False) == ()
    dist = project / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (wheel,) = dist.glob("*.whl")
    installed = tmp_path / "wheel-root"
    extract_pure_python_wheel(wheel, installed)

    script = """
import json
import socket

def deny(*args, **kwargs):
    raise AssertionError("network construction is forbidden")

socket.socket = deny
socket.create_connection = deny

from project_standards.control_plane.distribution import InstalledDistribution

catalog = InstalledDistribution.current().load_catalog("5")
print(json.dumps({
    "major": catalog.source.catalog_major,
    "payloads": sorted(f"{key[0]}@{key[1]}" for key in catalog.payload_map),
}))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(installed)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "major": 5,
        "payloads": ["alpha@1.0", "alpha@2.0", "alpha@3.0", "beta@1.0", "gamma@1.0"],
    }
