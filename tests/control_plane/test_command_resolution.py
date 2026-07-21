from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from project_standards.control_plane import command_resolution
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import run as reconcile
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    SelectedCommandPackage,
    reenter_selected_command,
    resolve_enabled_companion,
    resolve_selected_package,
    selected_command,
)
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockMode,
    control_plane_lock,
)
from project_standards.control_plane.state import detect_control_plane_state
from tests.control_plane.helpers import installed_distribution


def _selected_alpha(tmp_path: Path) -> SelectedCommandPackage:
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
    return selected


def test_reenter_selected_command__callback_raises__returns_two_inside_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    selected = _selected_alpha(tmp_path)
    active = False

    @contextmanager
    def fake_selected_command(
        *_args: object,
        **_kwargs: object,
    ) -> Generator[SelectedCommandPackage]:
        nonlocal active
        active = True
        try:
            yield selected
        finally:
            active = False

    def fail_reentry(
        arguments: list[str],
        selected_package: SelectedCommandPackage,
    ) -> int:
        assert active
        assert arguments == ["--fix"]
        assert selected_package is selected
        raise RuntimeError("nested command failed")

    monkeypatch.setattr(command_resolution, "selected_command", fake_selected_command)

    outcome = reenter_selected_command(
        ["--fix"],
        standard_id="alpha",
        mode=LockMode.WRITE,
        reenter=fail_reentry,
    )

    assert outcome == 2
    assert not active
    assert capsys.readouterr().err == "error: nested command failed\n"


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
    ("setup", "message", "typed_absence"),
    [
        ("disabled", "disabled", True),
        ("missing", "not present", True),
        ("dual", "legacy and unified", False),
        ("override", "explicit legacy override", False),
    ],
)
def test_initialized_resolution_fails_closed_for_command_matrix_states(
    tmp_path: Path,
    setup: str,
    message: str,
    typed_absence: bool,
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

    with pytest.raises(CommandResolutionError, match=message) as exc_info:
        resolve_selected_package(
            repo,
            standard_id,
            distribution,
            explicit_legacy=explicit_legacy,
        )

    if typed_absence:
        assert type(exc_info.value) is not CommandResolutionError
    else:
        assert type(exc_info.value) is CommandResolutionError


@pytest.mark.parametrize(
    ("standard_id", "disabled"),
    [
        pytest.param("alpha", True, id="disabled"),
        pytest.param("missing-package", False, id="not-present"),
    ],
)
def test_enabled_companion__absent_or_disabled__returns_none(
    tmp_path: Path,
    standard_id: str,
    disabled: bool,
) -> None:
    selected = _selected_alpha(tmp_path)
    if disabled:
        set_standard_enabled(selected.repo, standard_id, False)
        state = detect_control_plane_state(
            selected.repo,
            tool_release=selected.distribution.tool_release.value,
        )
        selected = replace(selected, state=state)

    assert resolve_enabled_companion(selected, standard_id) is None


@pytest.mark.parametrize(
    ("setup", "standard_id"),
    [
        pytest.param("disabled", "alpha", id="disabled"),
        pytest.param("missing", "missing-package", id="not-present"),
    ],
)
def test_companion_absence__missing_or_disabled__uses_typed_resolution_error(
    tmp_path: Path,
    setup: str,
    standard_id: str,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    if setup == "disabled":
        set_standard_enabled(repo, standard_id, True)
        set_standard_enabled(repo, standard_id, False)

    with pytest.raises(CommandResolutionError) as exc_info:
        resolve_selected_package(repo, standard_id, distribution)

    assert type(exc_info.value) is not CommandResolutionError


@pytest.mark.parametrize(
    "message",
    [
        pytest.param("companion provider is disabled unexpectedly", id="disabled"),
        pytest.param("companion output is not present", id="not-present"),
    ],
)
def test_enabled_companion__unrelated_same_word_error__propagates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    selected = _selected_alpha(tmp_path)

    def fail_resolution(*_args: object, **_kwargs: object) -> None:
        raise CommandResolutionError(message)

    monkeypatch.setattr(command_resolution, "_resolve_state_for_command", fail_resolution)

    with pytest.raises(CommandResolutionError, match=message):
        resolve_enabled_companion(selected, "beta")
