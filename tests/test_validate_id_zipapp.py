"""Regression tests for the standalone validate-id zipapp builder."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BUILD_SCRIPT = _ROOT / "scripts/build-validate-id-pyz.sh"
_SOURCE_PACKAGE = _ROOT / "src/project_standards"
_ORIGINAL_UV_CACHE = Path.home() / ".cache/uv"


def _source_package(path: Path, marker: str) -> Path:
    path.mkdir(parents=True)
    (path / "__init__.py").write_text("", encoding="utf-8")
    (path / "source-marker.txt").write_text(marker, encoding="utf-8")
    return path


def _build_environment(home: Path, *, ps_src: Path | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "LC_ALL": "C.UTF-8",
            "UV_CACHE_DIR": str(_ORIGINAL_UV_CACHE),
        }
    )
    if ps_src is None:
        environment.pop("PS_SRC", None)
    else:
        environment["PS_SRC"] = str(ps_src)
    return environment


def _build_zipapp(
    checkout: Path,
    *,
    source_argument: Path | None = None,
    environment: dict[str, str] | None = None,
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    script = checkout / "scripts/build-validate-id-pyz.sh"
    script.parent.mkdir(parents=True)
    shutil.copy2(_BUILD_SCRIPT, script)
    command = ["bash", str(script)]
    if source_argument is not None:
        command.append(str(source_argument))
    completed = subprocess.run(
        command,
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        env=environment,
    )
    return checkout / "dist/validate-id.pyz", completed


def _run_zipapp(zipapp: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(zipapp), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "LC_ALL": "C.UTF-8"},
    )


@pytest.fixture(scope="module")
def validate_id_zipapp(tmp_path_factory: pytest.TempPathFactory) -> Path:
    checkout = tmp_path_factory.mktemp("validate-id-zipapp")
    materialized_source = checkout / "materialized/project_standards"
    shutil.copytree(_SOURCE_PACKAGE, materialized_source)
    environment_source = _source_package(checkout / "environment/project_standards", "environment")
    zipapp, completed = _build_zipapp(
        checkout,
        source_argument=materialized_source,
        environment=_build_environment(checkout / "home", ps_src=environment_source),
    )
    assert f"→ source: {materialized_source}" in completed.stdout
    return zipapp


def test_validate_id_zipapp__help__prints_usage(validate_id_zipapp: Path, tmp_path: Path) -> None:
    completed = _run_zipapp(validate_id_zipapp, "--help", cwd=tmp_path)

    assert completed.returncode == 0
    assert "usage: validate-id" in completed.stdout


def test_validate_id_zipapp__valid_document__reports_success(
    validate_id_zipapp: Path, tmp_path: Path
) -> None:
    document = tmp_path / "valid.md"
    document.write_text(
        "---\nid: note-a3f9zk-valid\ndoc_type: note\ntitle: Valid\n---\n",
        encoding="utf-8",
    )

    completed = _run_zipapp(validate_id_zipapp, str(document), cwd=tmp_path)

    assert completed.returncode == 0
    assert "✓  1 file(s) validated" in completed.stdout


def test_validate_id_zipapp__invalid_document__reports_violation(
    validate_id_zipapp: Path, tmp_path: Path
) -> None:
    document = tmp_path / "invalid.md"
    document.write_text(
        "---\nid: note-invalid\ndoc_type: note\ntitle: Invalid\n---\n",
        encoding="utf-8",
    )

    completed = _run_zipapp(validate_id_zipapp, str(document), cwd=tmp_path)

    assert completed.returncode == 1
    assert "[id]" in completed.stderr


@pytest.mark.parametrize(
    "call",
    [
        pytest.param("Draft202012Validator({}).iter_errors({})", id="iter-errors"),
        pytest.param("Draft202012Validator.check_schema({})", id="check-schema"),
    ],
)
def test_jsonschema_stub__unsupported_call__raises_not_implemented(
    validate_id_zipapp: Path, call: str
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import sys; "
                "sys.path.insert(0, sys.argv[1]); "
                "from jsonschema import Draft202012Validator; "
                f"{call}"
            ),
            str(validate_id_zipapp),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "LC_ALL": "C.UTF-8"},
    )

    assert completed.returncode != 0
    assert "NotImplementedError" in completed.stderr
    assert "schema validation is unavailable" in completed.stderr


def test_build_validate_id_zipapp__ps_src__precedes_checkout_and_fallback(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    _source_package(checkout / "src/project_standards", "checkout")
    environment_source = _source_package(tmp_path / "environment/project_standards", "environment")
    home = tmp_path / "home"
    _source_package(home / "projects/project-standards/src/project_standards", "fallback")

    zipapp, completed = _build_zipapp(
        checkout,
        environment=_build_environment(home, ps_src=environment_source),
    )

    assert f"→ source: {environment_source}" in completed.stdout
    with zipfile.ZipFile(zipapp) as archive:
        assert archive.read("project_standards/source-marker.txt") == b"environment"


def test_build_validate_id_zipapp__alternate_checkout__prefers_sibling_source(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "alternate-checkout"
    _source_package(checkout / "src/project_standards", "checkout")
    home = tmp_path / "home"
    _source_package(home / "projects/project-standards/src/project_standards", "fallback")

    zipapp, completed = _build_zipapp(
        checkout,
        environment=_build_environment(home),
    )

    assert f"→ source: {checkout / 'src/project_standards'}" in completed.stdout
    with zipfile.ZipFile(zipapp) as archive:
        assert archive.read("project_standards/source-marker.txt") == b"checkout"
