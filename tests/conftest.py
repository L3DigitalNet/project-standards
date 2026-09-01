"""Coverage bootstrap for pytest-xdist worker interpreters.

``coverage run -m pytest -n N`` traces only the controller process. xdist runs
the tests in separate interpreters started through execnet, so without this hook
the parallel gate reports near-zero coverage.

Rejected alternative: ``COVERAGE_PROCESS_START`` (or ``patch = ["subprocess"]``,
which sets the equivalent). coverage 7.10+ installs ``a1_coverage.pth``, which
auto-starts coverage in *every* child interpreter whenever that variable is
present in the environment. The suite spawns ``project-standards`` CLI
subprocesses that the serial gate does not measure, so that route would inflate
the totals against the serial baseline instead of reproducing them. Handing the
controller's own serialized coverage config down xdist's ``workerinput`` channel
reaches exactly the worker interpreters and nothing else.

The workers inherit the controller's effective configuration verbatim --
including ``--source`` given on the command line -- so the parallel gate cannot
drift from the serial one through a second copy of the settings.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Protocol, cast

import pytest
from coverage import Coverage
from coverage.control import CONFIG_DATA_PREFIX

# Travels controller -> worker inside xdist's workerinput mapping.
_CONFIG_KEY = "project_standards_coverage_config"

_COVERAGE_STASH: pytest.StashKey[Coverage] = pytest.StashKey()


class _WorkerNode(Protocol):
    """The part of xdist's WorkerController this module touches.

    xdist ships no type information, so importing its classes would fail the
    strict type gate; this structural stand-in keeps the annotation honest.
    """

    workerinput: dict[str, object]


def pytest_configure_node(node: _WorkerNode) -> None:
    """Controller-side xdist hook: publish the live coverage config to a worker."""
    controller_coverage = Coverage.current()
    if controller_coverage is None:
        # Uninstrumented run (the compatibility matrix): leave the workers alone.
        return
    node.workerinput[_CONFIG_KEY] = controller_coverage.config.serialize()


def pytest_configure(config: pytest.Config) -> None:
    """Worker-side: start measurement before any test module is imported."""
    workerinput = cast("dict[str, object] | None", getattr(config, "workerinput", None))
    if workerinput is None:
        # Controller or serial run: `coverage run` already traces this process.
        return
    serialized = workerinput.get(_CONFIG_KEY)
    if not isinstance(serialized, str):
        return
    # data_suffix=True regardless of the inherited `parallel` setting: every
    # worker needs its own data file for `coverage combine` to merge.
    worker_coverage = Coverage(config_file=CONFIG_DATA_PREFIX + serialized, data_suffix=True)
    worker_coverage.start()
    config.stash[_COVERAGE_STASH] = worker_coverage


def pytest_unconfigure(config: pytest.Config) -> None:
    """Worker-side: flush the worker's own ``.coverage.*`` file."""
    worker_coverage = config.stash.get(_COVERAGE_STASH, None)
    if worker_coverage is None:
        return
    del config.stash[_COVERAGE_STASH]
    worker_coverage.stop()
    worker_coverage.save()


_PREBUILT_WHEEL = "PROJECT_STANDARDS_COMPATIBILITY_WHEEL"

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return one wheel built from the pristine repository root, per session.

    Only for tests that judge what the *released* artifact contains. A test that
    builds a deliberately modified tree — a synthesized minimal project, a bumped
    version, a rewritten `[tool.uv.build-backend]` — must keep its own build; this
    fixture would silently substitute the real repository and prove nothing.

    `PROJECT_STANDARDS_COMPATIBILITY_WHEEL` short-circuits the build, matching the
    override `tests/package_compatibility/conftest.py` already honors. `scripts/verify.sh`
    exports it (line 144) after building the candidate wheel once, so every xdist worker
    reuses that single 71 MB artifact instead of rebuilding it. Without the export each
    worker builds once, which is the floor: session scope cannot cross process boundaries.
    """
    configured = os.environ.get(_PREBUILT_WHEEL)
    if configured is not None:
        wheel = Path(configured).resolve(strict=True)
        if not wheel.is_file() or wheel.suffix != ".whl":
            raise ValueError(f"{_PREBUILT_WHEEL} must name one wheel file")
        return wheel
    output = tmp_path_factory.mktemp("built-wheel")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(output)],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
    )
    (wheel,) = output.glob("*.whl")
    return wheel
