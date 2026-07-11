from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from project_standards.package_contract import PackageContractError
from project_standards.package_contract.discovery import discover_v2_families
from tests.package_contract.helpers import copy_minimal_repository


def test_discovery_uses_the_v2_preamble_and_ignores_v1_manifests(tmp_path: Path) -> None:
    repository = copy_minimal_repository(tmp_path)
    legacy = repository / "standards/legacy"
    legacy.mkdir()
    (legacy / "standard.toml").write_text(
        'schema_version = "1.0"\n[standard]\nid = "legacy"\n', encoding="utf-8"
    )

    result = discover_v2_families(repository)

    assert [path.parent.name for path in result.paths] == ["demo"]
    assert result.findings == ()


def test_discovery_allowlist_is_explicit_and_deterministic(tmp_path: Path) -> None:
    repository = copy_minimal_repository(tmp_path)
    shutil.copytree(repository / "standards/demo", repository / "standards/other")

    first = discover_v2_families(repository, family_allowlist=["other", "demo"])
    second = discover_v2_families(repository, family_allowlist=["demo", "other"])

    assert first.paths == second.paths
    assert [path.parent.name for path in first.paths] == ["demo", "other"]


def test_discovery_reports_missing_allowlisted_manifest_and_case_collisions(
    tmp_path: Path,
) -> None:
    repository = copy_minimal_repository(tmp_path)
    shutil.copytree(repository / "standards/demo", repository / "standards/DEMO")

    result = discover_v2_families(repository, family_allowlist=["demo", "DEMO", "missing"])

    assert {finding.code for finding in result.findings} == {
        "PC-DUPLICATE-ID",
        "PC-FAMILY-MANIFEST-MISSING",
    }


def test_discovery_rejects_symlinked_or_non_directory_roots(tmp_path: Path) -> None:
    repository = copy_minimal_repository(tmp_path)
    linked = tmp_path / "linked"
    linked.symlink_to(repository, target_is_directory=True)

    with pytest.raises(PackageContractError, match="root"):
        discover_v2_families(linked)
    with pytest.raises(PackageContractError, match="root"):
        discover_v2_families(tmp_path / "missing")

    family_link = repository / "standards/linked"
    family_link.symlink_to(repository / "standards/demo", target_is_directory=True)
    with pytest.raises(PackageContractError, match="symbolic links"):
        discover_v2_families(repository)
