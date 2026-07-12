"""Shared immutable source and wheel distributions for compatibility rows."""

from __future__ import annotations

import os
import socket
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest

from project_standards.control_plane.distribution import InstalledDistribution
from tests.package_compatibility.matrix import source_distribution
from tests.wheel_helpers import extract_pure_python_wheel

_ROOT = Path(__file__).resolve().parents[2]
_PREBUILT_WHEEL = "PROJECT_STANDARDS_COMPATIBILITY_WHEEL"


def _deny_network(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("package compatibility attempted network access")


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deny network access in every source and installed-payload row."""
    monkeypatch.setattr(socket, "socket", _deny_network)
    monkeypatch.setattr(socket, "create_connection", _deny_network)


@pytest.fixture(scope="session")
def source_payload_distribution(
    tmp_path_factory: pytest.TempPathFactory,
) -> InstalledDistribution:
    return source_distribution(tmp_path_factory.mktemp("compatibility-source"))


@pytest.fixture(scope="session")
def wheel_payload_distribution(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[InstalledDistribution]:
    root = tmp_path_factory.mktemp("compatibility-wheel")
    configured = os.environ.get(_PREBUILT_WHEEL)
    if configured is None:
        output = root / "dist"
        subprocess.run(
            ["uv", "build", "--offline", "--wheel", "--out-dir", str(output)],
            cwd=_ROOT,
            check=True,
            capture_output=True,
        )
        (wheel,) = output.glob("*.whl")
    else:
        wheel = Path(configured).resolve(strict=True)
        if not wheel.is_file() or wheel.suffix != ".whl":
            raise ValueError(f"{_PREBUILT_WHEEL} must name one wheel file")
    installed = root / "installed"
    extract_pure_python_wheel(wheel, installed)
    yield InstalledDistribution(installed / "project_standards", tool_release="5.0.0")
