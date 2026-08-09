"""Actionable upgrade diagnostic for a pre-1.8 launcher that cannot start (#141).

1.10 removed the interpreter-resolution failure class for new adopters by shipping
the launcher as a compiled executable, but it did nothing for a consumer holding an
exact pre-1.8 selection: those payloads are immutable, their registration is a bare
path to `session_start.py`, and its `#!/usr/bin/env python3` shebang resolves the
first `python3` on `PATH`. Where that is a policy rejection shim the hook exits 1
before it runs, while `validate` and `drift-check` report the composition clean —
every managed byte really does match the selected payload.

The fixture below is the reported environment: an exact pre-1.8 selection, automatic
startup, and a rejecting `python3` first on `PATH`. It is held fixed across the
version matrix so the finding's trigger is the launcher shape and not the shim: 1.8
and 1.9 register the interpreter probe and 1.10 registers the compiled launcher, and
all three stay finding-free under exactly the same shim.
"""

from __future__ import annotations

import json
import shutil
import stat
import sys
from pathlib import Path

import pytest

from project_standards.agent_handoff.cli import run
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation

_ROOT = Path(__file__).resolve().parents[2]
_FINDING = "AH-LAUNCHER-INTERPRETER"

# Both harness selections share one launcher boundary, so each must reach the finding
# on its own — a repository that selects only Codex is exposed exactly as much as one
# that selects only Claude Code.
_HARNESS_SELECTIONS = (["claude-code"], ["codex"], ["claude-code", "codex"])

_REJECTING_SHIM = """#!/bin/sh
echo 'ERROR: Use `uv run python3 ...` instead of `python3 ...`' >&2
exit 1
"""


@pytest.fixture(scope="module")
def distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    installed = tmp_path_factory.mktemp("launcher-interpreter") / "project_standards"
    shutil.copytree(_ROOT / "src/project_standards", installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


@pytest.fixture
def rejecting_python3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put a `python3` that refuses every invocation first — and only — on PATH."""
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    shim = shim_dir / "python3"
    shim.write_text(_REJECTING_SHIM, encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", str(shim_dir))
    return shim_dir


@pytest.fixture
def working_python3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put the interpreter running this suite first — and only — on PATH."""
    interpreter_dir = tmp_path / "interpreter"
    interpreter_dir.mkdir()
    (interpreter_dir / "python3").symlink_to(sys.executable)
    monkeypatch.setenv("PATH", str(interpreter_dir))
    return interpreter_dir


def _consumer(
    tmp_path: Path,
    distribution: InstalledDistribution,
    *,
    version: str,
    harnesses: list[str],
) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    config = repo / ".standards/config.toml"
    startup = "automatic" if harnesses else "manual"
    config.write_text(
        config.read_text(encoding="utf-8")
        + f'\n[standards.agent-handoff]\nenabled = true\nversion = "{version}"\n\n'
        + '[standards.agent-handoff.config]\ncontract_version = "1.1"\n'
        + f'startup = "{startup}"\nharnesses = {json.dumps(harnesses)}\n',
        encoding="utf-8",
    )
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    return repo


def _findings(
    repo: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
    *,
    command: str = "validate",
) -> tuple[int, list[dict[str, object]]]:
    exit_code = run([command, "--repo", str(repo), "--json"], distribution=distribution)
    report = json.loads(capsys.readouterr().out)
    return exit_code, report["findings"]


@pytest.mark.parametrize("harnesses", _HARNESS_SELECTIONS)
@pytest.mark.parametrize("command", ["validate", "drift-check"])
@pytest.mark.usefixtures("rejecting_python3")
def test_pre_1_8_selection_under_a_rejecting_shim_is_reported_as_actionable(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
    harnesses: list[str],
    command: str,
) -> None:
    repo = _consumer(tmp_path, distribution, version="1.6", harnesses=harnesses)

    exit_code, findings = _findings(repo, distribution, capsys, command=command)

    assert exit_code == 1
    finding = next(item for item in findings if item["code"] == _FINDING)
    assert finding["severity"] == "error"
    assert finding["path"] == ".agents/hooks/agent-handoff/session_start.py"
    assert "1.10 or newer" in str(finding["guidance"])
    # The managed hook and both registrations are centrally locked, so an edit is
    # the one repair the guidance must never suggest.
    assert "Do not edit the managed hook" in str(finding["guidance"])


@pytest.mark.parametrize("version", ["1.8", "1.9", "1.10"])
@pytest.mark.parametrize("harnesses", _HARNESS_SELECTIONS)
@pytest.mark.usefixtures("rejecting_python3")
def test_launcher_versions_that_do_not_consult_path_stay_finding_free(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
    version: str,
    harnesses: list[str],
) -> None:
    repo = _consumer(tmp_path, distribution, version=version, harnesses=harnesses)

    exit_code, findings = _findings(repo, distribution, capsys)

    assert exit_code == 0
    assert findings == []


@pytest.mark.usefixtures("working_python3")
def test_pre_1_8_selection_with_a_usable_interpreter_stays_finding_free(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The trigger is the runtime, not the version: same payload, usable `python3`."""
    repo = _consumer(tmp_path, distribution, version="1.6", harnesses=["claude-code", "codex"])

    exit_code, findings = _findings(repo, distribution, capsys)

    assert exit_code == 0
    assert findings == []


@pytest.mark.usefixtures("rejecting_python3")
def test_manual_startup_registers_no_launcher_and_stays_finding_free(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Manual mode installs no hook, so no interpreter is ever selected."""
    repo = _consumer(tmp_path, distribution, version="1.6", harnesses=[])

    exit_code, findings = _findings(repo, distribution, capsys)

    assert exit_code == 0
    assert findings == []
