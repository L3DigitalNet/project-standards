"""CLI/integration tests for `project-standards spec new`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.specs.cli import run


def _one_json(captured: str) -> dict[str, object]:
    lines = [ln for ln in captured.splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected exactly one JSON line, got: {captured!r}"
    obj: dict[str, object] = json.loads(lines[0])
    return obj


def test_stdout_prints_valid_spec_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    rc = run(["new", "--profile", "light", "--stdout", "--id", "SPEC-7F3Q"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "spec_id: SPEC-7F3Q" in out
    assert set(tmp_path.iterdir()) == before  # I3: nothing created


def test_stdout_json_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = run(["new", "--profile", "full", "--stdout", "--json", "--id", "SPEC-AB12"])
    payload = _one_json(capsys.readouterr().out)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["spec_id"] == "SPEC-AB12"
    assert payload["profile"] == "full"
    assert payload["path"] is None and payload["written"] is False
    assert isinstance(payload["content"], str) and payload["content"].startswith("---\n")


@pytest.mark.parametrize(
    "argv",
    [
        ["new", "--profile", "light", "--stdout", "out.md"],  # PATH + --stdout
        ["new", "--profile", "light"],  # neither PATH nor --stdout
        ["new", "--profile", "light", "--stdout", "--force"],  # --force with --stdout
    ],
)
def test_flag_conflicts_exit_2(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(argv) == 2


@pytest.mark.parametrize(
    "argv",
    [
        ["new", "--stdout", "--json"],  # missing required --profile
        ["new", "--profile", "medium", "--stdout", "--json"],  # invalid --profile choice
        ["new", "--profile", "light", "--stdout", "--json", "--bogus"],  # unknown flag
    ],
)
def test_argparse_failures_are_json_and_never_systemexit(
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = run(argv)  # must NOT raise SystemExit
    payload = _one_json(capsys.readouterr().out)
    assert rc == 2
    assert payload["ok"] is False and payload["code"] == "usage"


def test_bad_id_and_bad_field_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(["new", "--profile", "light", "--stdout", "--id", "SPEC-lower"]) == 2
    assert run(["new", "--profile", "light", "--stdout", "--title", "has\nnewline"]) == 2
    capsys.readouterr()  # drain stderr from the two non-json runs above
    rc = run(["new", "--profile", "light", "--stdout", "--json", "--id", "nope"])
    payload = _one_json(capsys.readouterr().out)
    assert rc == 2 and payload["code"] == "bad_id"
