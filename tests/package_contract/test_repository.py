from __future__ import annotations

import shutil
from pathlib import Path

from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import (
    clone_demo_family,
    copy_minimal_repository,
    refresh_declared_file_digest,
)


def test_builds_a_version_qualified_repository_with_selected_catalog(tmp_path: Path) -> None:
    root = copy_minimal_repository(tmp_path)

    repository = build_package_repository(root, catalog_major=5)

    assert repository.findings == ()
    assert [family.manifest.standard.id for family in repository.families] == ["demo"]
    assert repository.payloads[0].manifest.payload.version.value == "1.2"
    assert repository.catalog is not None
    assert repository.catalog.catalog_major == 5


def test_empty_v2_discovery_is_a_non_vacuous_finding(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "standards").mkdir(parents=True)

    repository = build_package_repository(root)

    assert [finding.code for finding in repository.findings] == ["PC-NO-FAMILIES"]


def test_missing_family_readme_and_indexed_payload_are_aggregated(tmp_path: Path) -> None:
    root = copy_minimal_repository(tmp_path)
    other = clone_demo_family(root, "other")
    (root / "standards/demo/README.md").unlink()
    shutil.rmtree(other / "versions/1.2")

    repository = build_package_repository(root)

    assert {finding.code for finding in repository.findings} == {
        "PC-FAMILY-LOAD",
        "PC-PAYLOAD-LOAD",
    }


def test_malformed_payload_toml_and_option_json_do_not_mask_each_other(
    tmp_path: Path,
) -> None:
    root = copy_minimal_repository(tmp_path)
    alpha = clone_demo_family(root, "alpha")
    beta = clone_demo_family(root, "beta")
    (root / "standards/demo").rename(root / "legacy-demo")
    (alpha / "versions/1.2/payload.toml").write_bytes(b"\xff")
    (beta / "versions/1.2/config.schema.json").write_text("{", encoding="utf-8")
    refresh_declared_file_digest(beta, "config.schema.json")

    repository = build_package_repository(root)

    assert [(finding.standard_id, finding.code) for finding in repository.findings] == [
        ("alpha", "PC-PAYLOAD-LOAD"),
        ("beta", "PC-OPTIONS"),
    ]


def test_family_payload_identity_mismatch_is_reported_without_trusting_it(
    tmp_path: Path,
) -> None:
    root = copy_minimal_repository(tmp_path)
    payload = root / "standards/demo/versions/1.2/payload.toml"
    payload.write_text(
        payload.read_text(encoding="utf-8").replace('standard = "demo"', 'standard = "other"'),
        encoding="utf-8",
    )

    repository = build_package_repository(root)

    assert [finding.code for finding in repository.findings] == ["PC-PAYLOAD-LOAD"]


def test_unindexed_version_directories_are_not_loaded(tmp_path: Path) -> None:
    root = copy_minimal_repository(tmp_path)
    unindexed = root / "standards/demo/versions/9.9"
    unindexed.mkdir()
    (unindexed / "payload.toml").write_bytes(b"\xff")

    repository = build_package_repository(root)

    assert repository.findings == ()
    assert [payload.manifest.payload.version.value for payload in repository.payloads] == ["1.2"]


def test_selected_catalog_errors_join_package_load_findings(tmp_path: Path) -> None:
    root = copy_minimal_repository(tmp_path)
    (root / "standards/demo/versions/1.2/README.md").unlink()
    catalog = root / "catalogs/5.toml"
    catalog.write_text(
        catalog.read_text(encoding="utf-8").replace('id = "demo"', 'id = "unknown"'),
        encoding="utf-8",
    )

    repository = build_package_repository(root, catalog_major=5)

    assert {finding.code for finding in repository.findings} == {
        "PC-INTEGRITY",
        "PC-CATALOG-INVALID",
    }
