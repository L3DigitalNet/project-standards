from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from project_standards.cli import main
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.codec import parse_catalog, parse_config, parse_lock
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.locking import LockedControlDirectory
from project_standards.package_contract.projection import sync_payload_projection
from tests.wheel_helpers import extract_pure_python_wheel

_FULL = Path("tests/fixtures/package_contract/valid/full")


def _installed_fixture(tmp_path: Path, *, tool_release: str = "5.0.0") -> InstalledDistribution:
    repository = tmp_path / "package-repository"
    shutil.copytree(_FULL / "standards", repository / "standards")
    shutil.copytree(_FULL / "catalogs", repository / "catalogs")
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()

    installed = tmp_path / "installed/project_standards"
    shutil.copytree(package, installed)
    return InstalledDistribution(installed, tool_release=tool_release)


def _tree(root: Path) -> dict[str, tuple[str, bytes]]:
    result: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            result[relative] = ("directory", b"")
        elif path.is_file():
            result[relative] = ("file", path.read_bytes())
        else:
            result[relative] = ("other", b"")
    return result


def test_initialization_creates_exactly_three_neutral_regular_files(tmp_path: Path) -> None:
    distribution = _installed_fixture(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()

    result = initialize_control_plane(repo, "5", distribution=distribution)

    assert result.created
    assert list(_tree(repo)) == [
        ".standards",
        ".standards/catalog.toml",
        ".standards/config.toml",
        ".standards/lock.toml",
    ]
    assert all(
        kind == "file" for path, (kind, _content) in _tree(repo).items() if path != ".standards"
    )
    config = parse_config((repo / ".standards/config.toml").read_bytes())
    catalog = parse_catalog((repo / ".standards/catalog.toml").read_bytes())
    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert config.standards == {}
    assert lock.standards == {}
    assert lock.accepted_tracks == {}
    assert lock.artifacts == []
    assert lock.referenced_inputs == []
    assert catalog.project_standards.release == "5.0.0"
    assert catalog.project_standards.digest == lock.project_standards.catalog_digest


def test_second_initialization_is_a_byte_and_metadata_noop(tmp_path: Path) -> None:
    distribution = _installed_fixture(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    before = _tree(repo)
    before_stats = {path.name: path.stat().st_mtime_ns for path in (repo / ".standards").iterdir()}

    result = initialize_control_plane(repo, "5", distribution=distribution)

    assert not result.created
    assert _tree(repo) == before
    assert {
        path.name: path.stat().st_mtime_ns for path in (repo / ".standards").iterdir()
    } == before_stats


def test_initialization_refuses_legacy_partial_and_existing_different_state(
    tmp_path: Path,
) -> None:
    distribution = _installed_fixture(tmp_path)

    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / ".project-standards.yml").write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(ControlPlaneError, match="legacy"):
        initialize_control_plane(legacy, "5", distribution=distribution)
    assert not (legacy / ".standards").exists()

    partial = tmp_path / "partial"
    (partial / ".standards").mkdir(parents=True)
    (partial / ".standards/config.toml").write_text("partial\n", encoding="utf-8")
    with pytest.raises(ControlPlaneError, match="incomplete"):
        initialize_control_plane(partial, "5", distribution=distribution)
    assert (partial / ".standards/config.toml").read_text(encoding="utf-8") == "partial\n"

    different = tmp_path / "different"
    different.mkdir()
    initialize_control_plane(different, "5", distribution=distribution)
    config = different / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace('catalog = "5"', 'catalog = "6"'),
        encoding="utf-8",
    )
    with pytest.raises(ControlPlaneError, match="different"):
        initialize_control_plane(different, "5", distribution=distribution)


def test_initialization_rejects_repository_and_control_plane_symlinks(tmp_path: Path) -> None:
    distribution = _installed_fixture(tmp_path)
    real = tmp_path / "real"
    real.mkdir()
    linked_repo = tmp_path / "linked-repo"
    linked_repo.symlink_to(real, target_is_directory=True)
    with pytest.raises(ControlPlaneError, match="repository"):
        initialize_control_plane(linked_repo, "5", distribution=distribution)

    target = tmp_path / "target"
    target.mkdir()
    (real / ".standards").symlink_to(target, target_is_directory=True)
    with pytest.raises(ControlPlaneError, match="symlink"):
        initialize_control_plane(real, "5", distribution=distribution)
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("failure_call", [1, 2, 3])
def test_staging_failure_removes_only_the_transient_empty_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_call: int,
) -> None:
    import project_standards.control_plane.bootstrap as bootstrap

    distribution = _installed_fixture(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    original = bootstrap._stage_file  # pyright: ignore[reportPrivateUsage]
    calls = 0

    def fail_at_boundary(
        control: LockedControlDirectory,
        name: str,
        content: bytes,
    ) -> str:
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("injected staging failure")
        return original(control, name, content)

    monkeypatch.setattr(bootstrap, "_stage_file", fail_at_boundary)

    with pytest.raises(ControlPlaneError, match="stage"):
        initialize_control_plane(repo, "5", distribution=distribution)

    assert not (repo / ".standards").exists()


@pytest.mark.parametrize("failure_call", [1, 2, 3])
def test_publication_failure_exposes_only_complete_canonical_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_call: int,
) -> None:
    import project_standards.control_plane.bootstrap as bootstrap

    distribution = _installed_fixture(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    original = bootstrap.os.replace
    calls = 0

    def fail_at_publication(
        source: str,
        destination: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("injected publication failure")
        original(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(bootstrap.os, "replace", fail_at_publication)

    with pytest.raises(ControlPlaneError, match="publish"):
        initialize_control_plane(repo, "5", distribution=distribution)

    published = ["config.toml", "catalog.toml", "lock.toml"][: failure_call - 1]
    control = repo / ".standards"
    if not published:
        assert not control.exists()
    else:
        assert sorted(path.name for path in control.iterdir()) == sorted(published)
        assert all((control / name).is_file() for name in published)


def test_cli_initializes_and_reports_usage_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    distribution = _installed_fixture(tmp_path)

    def current(_cls: type[InstalledDistribution]) -> InstalledDistribution:
        return distribution

    monkeypatch.setattr(InstalledDistribution, "current", classmethod(current))
    repo = tmp_path / "consumer"
    repo.mkdir()

    assert main(["init", "--catalog", "5", "--repo", str(repo)]) == 0
    assert "Initialized" in capsys.readouterr().out
    assert main(["init", "--catalog", "05", "--repo", str(repo)]) == 2


def test_extracted_wheel_initializes_offline_with_the_exact_scaffold(tmp_path: Path) -> None:
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
    consumer = tmp_path / "consumer"
    consumer.mkdir()

    script = """
import json
import socket
import sys
from pathlib import Path

def deny(*args, **kwargs):
    raise AssertionError("network construction is forbidden")

socket.socket = deny
socket.create_connection = deny

from project_standards.cli import main

code = main(["init", "--catalog", "5", "--repo", sys.argv[1]])
root = Path(sys.argv[1])
print(json.dumps({
    "code": code,
    "paths": sorted(path.relative_to(root).as_posix() for path in root.rglob("*")),
}))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(installed)
    result = subprocess.run(
        [sys.executable, "-c", script, str(consumer)],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.splitlines()[-1])

    assert payload == {
        "code": 0,
        "paths": [
            ".standards",
            ".standards/catalog.toml",
            ".standards/config.toml",
            ".standards/lock.toml",
        ],
    }
