from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.adopt.errors import UsageError
from project_standards.cli import main
from project_standards.standard_manifest import ProviderOperation


def test_top_level_help_advertises_agent_handoff(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert "agent-handoff" in capsys.readouterr().out


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
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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

    assert main(["agent-handoff", command, "--repo", "."]) == 0
    assert seen == [(operation, [*prefix, "--repo", "."])]


def test_agent_handoff_provider_error_preserves_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(_sid: str, _op: ProviderOperation, _argv: list[str]) -> int:
        raise UsageError("bad provider arguments")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        fail,
    )

    assert main(["agent-handoff", "validate", "--repo", "."]) == 2
    assert "bad provider arguments" in capsys.readouterr().err
