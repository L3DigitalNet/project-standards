from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pytest

from project_standards.cli import main
from project_standards.package_contract import cli as package_cli
from project_standards.package_contract.cli import run_packages, run_standards
from project_standards.package_contract.repository import (
    PackageRepository,
)
from tests.package_contract.helpers import copy_minimal_repository

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"


def test_validate_packages_human_and_json_success(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_standards(["validate-packages", "--root", str(_FIXTURE)]) == 0
    assert "OK package repository" in capsys.readouterr().out

    assert run_standards(["validate-packages", "--root", str(_FIXTURE), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"ok": True, "findings": []}


def test_validate_packages__noncanonical_05_catalog__is_ignored(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = copy_minimal_repository(tmp_path)
    (root / "catalogs/5.toml").rename(root / "catalogs/05.toml")

    assert run_standards(["validate-packages", "--root", str(root), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "findings": []}


def test_validate_packages__dangling_catalogs_symlink__is_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = copy_minimal_repository(tmp_path)
    shutil.rmtree(root / "catalogs")
    (root / "catalogs").symlink_to(root / "missing-catalogs", target_is_directory=True)

    assert run_standards(["validate-packages", "--root", str(root), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "package_load_error"
    assert "catalog source path must be a regular directory" in payload["error"]


def test_validated_repositories__two_canonical_majors__load_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = copy_minimal_repository(tmp_path)
    catalog = (root / "catalogs/5.toml").read_text(encoding="utf-8")
    (root / "catalogs/6.toml").write_text(
        catalog.replace("catalog_major = 5", "catalog_major = 6", 1),
        encoding="utf-8",
    )
    original_build = package_cli.build_package_repository
    loaded: list[PackageRepository] = []

    def counted_build(
        repository_root: Path,
        *,
        catalog_major: int | None = None,
        family_allowlist: Iterable[str] | None = None,
    ) -> PackageRepository:
        repository = original_build(
            repository_root,
            catalog_major=catalog_major,
            family_allowlist=family_allowlist,
        )
        loaded.append(repository)
        return repository

    monkeypatch.setattr(package_cli, "build_package_repository", counted_build)

    repositories, findings = package_cli._validated_repositories(  # pyright: ignore[reportPrivateUsage]
        root
    )

    assert len(loaded) == 1
    base = loaded[0]
    assert base.catalog is None
    assert findings == ()
    assert [
        repository.catalog.catalog_major if repository.catalog is not None else None
        for repository in repositories
    ] == [5, 6]
    assert all(repository is not base for repository in repositories)
    assert all(repository.families is base.families for repository in repositories)


def test_validate_packages_returns_sorted_findings_and_exit1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    (root / "standards/demo/versions/1.2/README.md").unlink()

    assert run_standards(["validate-packages", "--root", str(root), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert [finding["code"] for finding in payload["findings"]] == [
        "PC-INTEGRITY",
        "PC-CATALOG-INVALID",
    ]


def test_validate_packages_load_boundary_and_bad_args_exit2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_standards(["validate-packages", "--root", str(tmp_path / "missing"), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["code"] == "package_load_error"
    assert "Traceback" not in capsys.readouterr().err

    assert run_standards(["validate-packages", "--unknown"]) == 2


def test_generate_package_schemas_write_check_and_stale_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_standards(["generate-package-schemas", "--root", str(tmp_path)]) == 0
    schema = tmp_path / "src/project_standards/schemas/standard-payload.schema.json"
    assert schema.is_file()
    assert run_standards(["generate-package-schemas", "--root", str(tmp_path), "--check"]) == 0
    schema.write_bytes(schema.read_bytes() + b" ")

    assert run_standards(["generate-package-schemas", "--root", str(tmp_path), "--check"]) == 1
    assert schema.read_bytes().endswith(b" ")
    assert "stale" in capsys.readouterr().err


def test_render_consumer_catalog_requires_output_and_is_read_only_in_check_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    output = root / "generated/catalog.toml"
    base = [
        "render-consumer-catalog",
        "--root",
        str(root),
        "--catalog-major",
        "5",
    ]

    assert run_standards(base) == 2
    assert run_standards([*base[:-1], "0", "--output", str(output)]) == 2
    assert run_standards([*base, "--output", str(output)]) == 0
    rendered = output.read_bytes()
    assert run_standards([*base, "--output", str(output), "--check"]) == 0
    output.write_bytes(rendered + b"# stale\n")
    stale = output.read_bytes()
    assert run_standards([*base, "--output", str(output), "--check"]) == 1
    assert output.read_bytes() == stale
    assert "stale" in capsys.readouterr().err


def test_render_consumer_catalog_rejects_output_escape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    outside = tmp_path / "outside.toml"

    assert (
        run_standards(
            [
                "render-consumer-catalog",
                "--root",
                str(root),
                "--catalog-major",
                "5",
                "--output",
                str(outside),
                "--json",
            ]
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "bad_output"
    assert not outside.exists()


def test_sync_payload_projection_write_check_and_stale_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    (root / "src/project_standards").mkdir(parents=True)
    command = ["sync-payload-projection", "--root", str(root)]

    assert run_standards([*command, "--check"]) == 1
    assert not (root / "src/project_standards/payloads").exists()
    assert run_standards(command) == 0
    assert run_standards([*command, "--check"]) == 0
    assert "projection" in capsys.readouterr().out


def _create_released_fixture(repository: Path) -> None:
    subprocess.run(["git", "init", "-q", repository], check=True)
    subprocess.run(["git", "-C", repository, "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            repository,
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=168346341+chrisdpurcell@users.noreply.github.com",
            "commit",
            "-qm",
            "baseline",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", repository, "-c", "tag.gpgSign=false", "tag", "v5.2.0"],
        check=True,
    )


def test_packages_check_release_uses_tagged_baseline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.2.1")

    assert run_packages(["check-release", "--root", str(repository), "--baseline", "v5.2.0"]) == 0
    assert "patch" in capsys.readouterr().out

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["classification"] == "patch"


def test_top_level_dispatch_and_help_preserve_existing_groups(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["standards", "validate-packages", "--root", str(_FIXTURE)]) == 0
    assert main(["standards", "--help"]) == 0
    standards_help = capsys.readouterr().out
    for command in (
        "validate-graph",
        "render-catalog",
        "validate-packages",
        "render-consumer-catalog",
        "generate-package-schemas",
        "sync-payload-projection",
    ):
        assert command in standards_help

    assert main(["packages", "--help"]) == 0
    assert "check-release" in capsys.readouterr().out
