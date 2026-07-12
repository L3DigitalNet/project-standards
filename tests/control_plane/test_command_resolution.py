from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import run as reconcile
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    resolve_selected_package,
    selected_command,
)
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockMode,
    control_plane_lock,
)
from tests.control_plane.helpers import installed_distribution


def test_legacy_only_state_returns_the_bounded_fallback_with_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "project_standards.control_plane.command_resolution._legacy_warning_emitted",
        False,
    )
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text("legacy: true\n", encoding="utf-8")

    assert resolve_selected_package(repo, "alpha", installed_distribution(tmp_path)) is None
    assert "migrate before using the V5 control plane" in capsys.readouterr().err


def test_initialized_state_returns_exact_payload_and_effective_config(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "alpha", True)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    assert reconcile(["--repo", str(repo), "--apply"], distribution=distribution) == 0

    selected = resolve_selected_package(repo, "alpha", distribution)

    assert selected is not None
    assert selected.payload.manifest.payload.standard == "alpha"
    assert selected.payload.manifest.payload.version == selected.resolved
    assert selected.effective_config == {
        "extension_path": ".standards/extensions/alpha/options.toml"
    }


@pytest.mark.parametrize("mode", [LockMode.READ, LockMode.WRITE])
def test_selected_command_retains_the_requested_lock_for_its_lifetime(
    tmp_path: Path,
    mode: LockMode,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "alpha", True)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    assert reconcile(["--repo", str(repo), "--apply"], distribution=distribution) == 0

    incompatible = LockMode.WRITE if mode is LockMode.READ else LockMode.READ
    with selected_command(
        repo,
        "alpha",
        distribution,
        mode=mode,
    ) as selected:
        assert selected is not None
        with (
            pytest.raises(ControlPlaneBusyError, match="CP-BUSY"),
            control_plane_lock(repo, incompatible),
        ):
            pytest.fail("incompatible command lock was acquired")


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("disabled", "disabled"),
        ("missing", "not present"),
        ("dual", "legacy and unified"),
        ("override", "explicit legacy override"),
    ],
)
def test_initialized_resolution_fails_closed_for_command_matrix_states(
    tmp_path: Path,
    setup: str,
    message: str,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    standard_id = "alpha"
    explicit_legacy: Path | None = None
    if setup == "disabled":
        set_standard_enabled(repo, "alpha", True)
        set_standard_enabled(repo, "alpha", False)
    elif setup == "missing":
        standard_id = "missing-package"
    elif setup == "dual":
        (repo / ".project-standards.yml").write_text("legacy: true\n", encoding="utf-8")
    elif setup == "override":
        explicit_legacy = repo / "override.yml"

    with pytest.raises(CommandResolutionError, match=message):
        resolve_selected_package(
            repo,
            standard_id,
            distribution,
            explicit_legacy=explicit_legacy,
        )
