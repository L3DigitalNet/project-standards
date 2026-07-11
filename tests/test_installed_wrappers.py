"""Installed-wrapper smoke (spec §8, codex SA-005 + SA-NEW-001): build the wheel,
install into a throwaway venv via the venv's own seeded pip, run every console
script via the installed wrapper. Slowest test in the suite alongside
test_adopt_packaging.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

import pytest

_SCRIPTS = tuple(
    tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
)


@pytest.fixture(scope="module")
def installed_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("wheel-smoke")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp)], check=True, capture_output=True
    )
    (wheel,) = tmp.glob("*.whl")
    venv = tmp / "venv"
    subprocess.run(["uv", "venv", "--seed", str(venv)], check=True, capture_output=True)
    subprocess.run(
        [str(venv / "bin" / "python"), "-m", "pip", "install", "--quiet", str(wheel)],
        check=True,
        capture_output=True,
    )
    return venv


def _run(venv: Path, cmd: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NO_COLOR": "1", "COLUMNS": "100"}
    return subprocess.run([str(venv / "bin" / cmd), *args], capture_output=True, text=True, env=env)


@pytest.mark.parametrize("script", _SCRIPTS)
def test_wrapper_help_exits_zero(installed_venv: Path, script: str) -> None:
    proc = _run(installed_venv, script, "--help")
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("script", _SCRIPTS)
def test_wrapper_version_prints_exact_contract(installed_venv: Path, script: str) -> None:
    # The standard's contract is EXACT "<script-name> <version>" (codex CR-004): the
    # installed wrapper name is sys.argv[0], so argparse %(prog)s, the sync mains'
    # Path(sys.argv[0]).name, and cli.py's literal all resolve to the script name here.
    from project_standards._version import package_version

    proc = _run(installed_venv, script, "--version")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == f"{script} {package_version()}"


def test_nested_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "spec", "validate", "--help")
    assert proc.returncode == 0, proc.stderr


def test_standards_nested_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "standards", "validate-graph", "--help")
    assert proc.returncode == 0, proc.stderr


def test_package_authoring_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "standards", "validate-packages", "--help")
    assert proc.returncode == 0, proc.stderr


def test_package_release_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "packages", "check-release", "--help")
    assert proc.returncode == 0, proc.stderr


def test_agent_handoff_nested_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "agent-handoff", "--help")
    assert proc.returncode == 0, proc.stderr
