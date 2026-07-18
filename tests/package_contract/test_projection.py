from __future__ import annotations

import os
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

from project_standards.package_contract import PackageContractError
from project_standards.package_contract.projection import (
    plan_payload_projection,
    projection_findings,
    sync_payload_projection,
)
from tests.package_contract.helpers import copy_minimal_repository


def _prepare_repository(tmp_path: Path) -> Path:
    root = copy_minimal_repository(tmp_path)
    package = root / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    return root


def _snapshot(root: Path) -> dict[str, tuple[str, bytes | str]]:
    result: dict[str, tuple[str, bytes | str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("symlink", path.readlink().as_posix())
        elif path.is_file():
            result[relative] = ("file", path.read_bytes())
    return result


def test_projection_plan_and_apply_create_only_relative_file_symlinks(
    tmp_path: Path,
) -> None:
    root = _prepare_repository(tmp_path)
    canonical = _snapshot(root / "standards")

    plan = plan_payload_projection(root)
    assert [link.relative_path for link in plan.links] == [
        "catalogs/5.toml",
        "demo/1.2/README.md",
        "demo/1.2/adopt.md",
        "demo/1.2/agent-summary.md",
        "demo/1.2/config.schema.json",
        "demo/1.2/payload.toml",
        "families/demo/README.md",
        "families/demo/standard.toml",
    ]
    assert sync_payload_projection(root, check=False) == ()
    assert projection_findings(root) == ()
    assert sync_payload_projection(root, check=True) == ()
    assert _snapshot(root / "standards") == canonical

    catalog_link = root / "src/project_standards/catalogs/5.toml"
    assert catalog_link.is_symlink()
    assert not catalog_link.readlink().is_absolute()
    assert catalog_link.resolve(strict=True).read_bytes() == (root / "catalogs/5.toml").read_bytes()

    family_link = root / "src/project_standards/families/demo/standard.toml"
    assert family_link.is_symlink()
    assert (
        family_link.resolve(strict=True).read_bytes()
        == (root / "standards/demo/standard.toml").read_bytes()
    )
    assert (root / "src/project_standards/families/demo/README.md").is_symlink()

    projection = root / "src/project_standards/payloads"
    links = sorted(path for path in projection.rglob("*") if path.is_symlink())
    assert len(links) == 5
    for link in links:
        assert not link.readlink().is_absolute()
        assert (
            link.resolve(strict=True).read_bytes()
            == (
                root / "standards/demo/versions/1.2" / link.relative_to(projection / "demo/1.2")
            ).read_bytes()
        )


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", "PC-PROJECTION-MISSING"),
        ("extra", "PC-PROJECTION-EXTRA"),
        ("regular", "PC-PROJECTION-NONLINK"),
        ("absolute", "PC-PROJECTION-ABSOLUTE"),
        ("broken", "PC-PROJECTION-BROKEN"),
        ("outside", "PC-PROJECTION-OUTSIDE"),
        ("directory-link", "PC-PROJECTION-DIRECTORY-LINK"),
    ],
)
def test_projection_check_rejects_every_noncanonical_shape(
    tmp_path: Path, mutation: str, expected_code: str
) -> None:
    root = _prepare_repository(tmp_path)
    sync_payload_projection(root, check=False)
    projection = root / "src/project_standards/payloads"
    target = projection / "demo/1.2/README.md"
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")

    if mutation == "missing":
        target.unlink()
    elif mutation == "extra":
        (projection / "extra").symlink_to("demo/1.2/README.md")
    elif mutation == "regular":
        target.unlink()
        target.write_text("transformed\n", encoding="utf-8")
    elif mutation == "absolute":
        target.unlink()
        target.symlink_to(root / "standards/demo/versions/1.2/README.md")
    elif mutation == "broken":
        target.unlink()
        target.symlink_to("missing.md")
    elif mutation == "outside":
        target.unlink()
        target.symlink_to(os.path.relpath(outside, start=target.parent))
    else:
        linked_directory = projection / "linked-directory"
        linked_directory.symlink_to(root / "standards/demo/versions/1.2", target_is_directory=True)

    before = _snapshot(projection)
    findings = projection_findings(root)

    assert expected_code in {finding.code for finding in findings}
    assert sync_payload_projection(root, check=True) == findings
    assert _snapshot(projection) == before


def test_projection_apply_removes_stale_symlinks_but_refuses_regular_files(
    tmp_path: Path,
) -> None:
    root = _prepare_repository(tmp_path)
    sync_payload_projection(root, check=False)
    projection = root / "src/project_standards/payloads"
    stale = projection / "stale/nested/old.md"
    stale.parent.mkdir(parents=True)
    stale.symlink_to("../../../demo/1.2/README.md")

    assert sync_payload_projection(root, check=False) == ()
    assert not stale.exists() and not stale.is_symlink()
    assert not stale.parent.exists()

    managed = projection / "demo/1.2/README.md"
    managed.unlink()
    managed.write_text("consumer bytes\n", encoding="utf-8")
    before = managed.read_bytes()
    with pytest.raises(PackageContractError, match="regular file"):
        sync_payload_projection(root, check=False)
    assert managed.read_bytes() == before


def test_current_build_configuration_includes_canonical_sources_in_sdist() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert config["tool"]["uv"]["build-backend"]["source-include"] == [
        "standards/**",
        "catalogs/**",
    ]


def test_uv_build_dereferences_relative_payload_links_from_source_and_sdist(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projection-build"
    canonical = project / "standards/demo/versions/1.0/README.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("# Packaged payload\n", encoding="utf-8")
    package = project / "src/demo_projection/payloads/demo/1.0"
    package.mkdir(parents=True)
    (project / "src/demo_projection/__init__.py").write_text("", encoding="utf-8")
    link = package / "README.md"
    link.symlink_to(os.path.relpath(canonical, start=link.parent))
    (project / "pyproject.toml").write_text(
        """[project]
name = "demo-projection"
version = "1.0.0"
requires-python = ">=3.14"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**"]
""",
        encoding="utf-8",
    )
    direct = project / "dist/direct"
    subprocess.run(
        ["uv", "build", "--sdist", "--wheel", "--out-dir", str(direct)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (sdist,) = direct.glob("*.tar.gz")
    from_sdist = project / "dist/from-sdist"
    subprocess.run(
        ["uv", "build", "--wheel", str(sdist), "--out-dir", str(from_sdist)],
        cwd=project,
        check=True,
        capture_output=True,
    )

    member = "demo_projection/payloads/demo/1.0/README.md"
    wheels = [*direct.glob("*.whl"), *from_sdist.glob("*.whl")]
    assert len(wheels) == 2
    member_sets: list[set[str]] = []
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            payload_members = {
                name
                for name in archive.namelist()
                if "/payloads/" in name and not name.endswith("/")
            }
            member_sets.append(payload_members)
            assert archive.read(member) == canonical.read_bytes()
    assert member_sets == [{member}, {member}]

    with tarfile.open(sdist) as archive:
        names = archive.getnames()
    assert any(name.endswith("/standards/demo/versions/1.0/README.md") for name in names)


def test_current_root_build__direct_and_sdist_wheels__match_projected_assets(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    direct = tmp_path / "direct"
    subprocess.run(
        [
            "uv",
            "build",
            "--offline",
            "--sdist",
            "--wheel",
            "--out-dir",
            str(direct),
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    (sdist,) = direct.glob("*.tar.gz")
    (direct_wheel,) = direct.glob("*.whl")

    from_sdist = tmp_path / "from-sdist"
    subprocess.run(
        [
            "uv",
            "build",
            "--offline",
            "--wheel",
            str(sdist),
            "--out-dir",
            str(from_sdist),
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    (sdist_wheel,) = from_sdist.glob("*.whl")

    package = root / "src/project_standards"
    projected_directories = ("catalogs", "families", "payloads")
    expected_assets = {
        path.relative_to(root / "src").as_posix(): path.resolve(strict=True).read_bytes()
        for directory in projected_directories
        for path in sorted((package / directory).rglob("*"))
        if path.is_file()
    }
    prefixes = tuple(f"project_standards/{directory}/" for directory in projected_directories)
    assert all(any(name.startswith(prefix) for name in expected_assets) for prefix in prefixes)

    for wheel in (direct_wheel, sdist_wheel):
        with zipfile.ZipFile(wheel) as archive:
            actual_assets = {
                name: archive.read(name)
                for name in archive.namelist()
                if name.startswith(prefixes) and not name.endswith("/")
            }
        assert actual_assets.keys() == expected_assets.keys()
        for name, expected in expected_assets.items():
            assert actual_assets[name] == expected, name
