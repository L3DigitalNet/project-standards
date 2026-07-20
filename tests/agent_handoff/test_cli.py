from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.adopt.errors import UsageError
from project_standards.cli import main
from project_standards.control_plane.command_resolution import (
    CommandConfigurationError,
    CommandResolutionError,
)
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.standard_manifest import ProviderOperation


def test_top_level_help_advertises_agent_handoff(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert "agent-handoff" in capsys.readouterr().out


def test_agent_handoff_adopt_help_uses_specialized_nonmutating_parser(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["adopt", "agent-handoff", "--dest", str(tmp_path), "--help"]) == 0

    output = capsys.readouterr().out
    assert "--manual" in output
    assert "--harness {claude-code,codex}" in output
    assert "--json" in output
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize(
    "args",
    [
        ["adopt", "agent-handoff", "--dry-run"],
        [
            "adopt",
            "agent-handoff",
            "--manual",
            "--harness",
            "codex",
            "--dry-run",
        ],
    ],
)
def test_agent_handoff_adopt_requires_exactly_one_startup_selection(
    args: list[str],
) -> None:
    assert main(args) == 2


def test_agent_handoff_adopt_json_dry_run_is_aggregate_and_non_mutating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unavailable() -> InstalledDistribution:
        raise PackageContractError("V2 distribution unavailable")

    monkeypatch.setattr(InstalledDistribution, "current", staticmethod(unavailable))
    rc = main(
        [
            "adopt",
            "agent-handoff",
            "markdown-tooling",
            "--dest",
            str(tmp_path),
            "--manual",
            "--dry-run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert list(payload) == [
        "repository",
        "standard_version",
        "changes",
        "findings",
        "summary",
    ]
    paths = {change["path"] for change in payload["changes"]}
    assert "docs/STATUS.md" in paths
    assert ".markdownlint.json" in paths
    assert not any(tmp_path.iterdir())


def test_agent_handoff_adopt_attempts_v5_before_legacy_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[list[str], Path, bool, bool, bool]] = []

    def capture(
        standards: list[str],
        destination: Path,
        *,
        force: bool,
        dry_run: bool,
        unsupported_options: bool = False,
    ) -> int:
        seen.append((standards, destination, force, dry_run, unsupported_options))
        return 7

    monkeypatch.setattr("project_standards.cli._try_v5_adopt", capture)

    def fail_legacy(_args: list[str]) -> int:
        pytest.fail("legacy dispatch ran after V5 activation")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_adopt",
        fail_legacy,
    )

    assert main(["adopt", "agent-handoff", "--dest", str(tmp_path)]) == 7
    assert seen == [(["agent-handoff"], tmp_path, False, False, False)]


@pytest.mark.parametrize(
    "args",
    [
        ["adopt", "agent-handoff", "--dest", "--force"],
        ["adopt", "agent-handoff", "--bogus"],
        ["adopt", "agent-handoff", "--force=false"],
    ],
)
def test_agent_handoff_adopt_rejects_malformed_route_before_v5_dispatch(
    args: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> int:
        pytest.fail("V5 dispatch ran after malformed adopt syntax")

    monkeypatch.setattr("project_standards.cli._try_v5_adopt", fail)

    assert main(args) == 2


@pytest.mark.parametrize(
    ("command", "operation", "prefix"),
    [
        ("validate", ProviderOperation.VALIDATE, []),
        ("size-report", ProviderOperation.VALIDATE, ["--view", "size"]),
        ("shape-check", ProviderOperation.VALIDATE, ["--view", "shape"]),
        ("drift-check", ProviderOperation.DRIFT_CHECK, []),
        ("legacy-report", ProviderOperation.EXTRACT, []),
        ("upgrade", ProviderOperation.UPGRADE, []),
    ],
)
def test_agent_handoff_command_maps_to_generic_operation(
    command: str,
    operation: ProviderOperation,
    prefix: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[ProviderOperation, list[str]]] = []

    def capture(_sid: str, op: ProviderOperation, argv: list[str]) -> int:
        seen.append((op, argv))
        return 0

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        capture,
    )

    assert main(["agent-handoff", command, "--repo", str(tmp_path)]) == 0
    assert seen == [(operation, [*prefix, "--repo", str(tmp_path)])]


@pytest.mark.parametrize("command", ["size-report", "shape-check"])
def test_agent_handoff_policy_view_alias_help_omits_view_override(
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent-handoff", command, "--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert f"usage: project-standards agent-handoff {command}" in output
    assert "--view" not in output


@pytest.mark.parametrize(
    ("command", "view_argument"),
    [("size-report", "shape"), ("shape-check", "size")],
)
def test_agent_handoff_policy_view_alias_rejects_view_override_before_fallback(
    command: str,
    view_argument: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_legacy(*_args: object, **_kwargs: object) -> int:
        pytest.fail("legacy provider ran after an invalid alias invocation")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        fail_legacy,
    )

    assert (
        main(
            [
                "agent-handoff",
                command,
                "--repo",
                str(tmp_path),
                "--view",
                view_argument,
            ]
        )
        == 2
    )
    assert "unrecognized arguments: --view" in capsys.readouterr().err


def test_agent_handoff_provider_error_preserves_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(_sid: str, _op: ProviderOperation, _argv: list[str]) -> int:
        raise UsageError("bad provider arguments")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        fail,
    )

    assert main(["agent-handoff", "validate", "--repo", str(tmp_path)]) == 2
    assert "bad provider arguments" in capsys.readouterr().err


def test_agent_handoff_configuration_failure_exits_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_selection(*_args: object, **_kwargs: object) -> object:
        raise CommandConfigurationError("selected package configuration is invalid")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.selected_command",
        fail_selection,
    )

    assert main(["agent-handoff", "validate", "--repo", str(tmp_path)]) == 2


@pytest.mark.parametrize(
    "failure",
    [
        CommandResolutionError("selected package is unavailable"),
        OSError("provider prerequisite is unavailable"),
        RuntimeError("provider runtime failed"),
    ],
)
def test_agent_handoff_prerequisite_and_internal_failures_exit_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    def fail_selection(*_args: object, **_kwargs: object) -> object:
        raise failure

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.selected_command",
        fail_selection,
    )

    assert main(["agent-handoff", "validate", "--repo", str(tmp_path)]) == 3
