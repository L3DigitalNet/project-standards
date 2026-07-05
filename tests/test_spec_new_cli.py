"""CLI/integration tests for `project-standards spec new`."""

from __future__ import annotations

import json
import os
import stat
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


def test_writes_new_file_that_validates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "docs" / "specs" / "checkout.md"  # parents auto-created
    assert run(["new", "--profile", "standard", "--id", "SPEC-7F3Q", str(target)]) == 0
    assert target.is_file()
    assert run(["validate", str(target)]) == 0  # I1 end-to-end


def test_refuse_existing_then_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    target.write_text("PRIOR WORK\n", encoding="utf-8")
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(target)]) == 2  # I2
    assert target.read_text(encoding="utf-8") == "PRIOR WORK\n"  # untouched
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(target)]) == 0
    assert "spec_id: SPEC-7F3Q" in target.read_text(encoding="utf-8")


def test_directory_and_symlink_targets_refused_even_with_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "adir"
    d.mkdir()
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(d)]) == 2
    link = tmp_path / "link.md"
    link.symlink_to(tmp_path / "real.md")
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(link)]) == 2
    assert not (tmp_path / "real.md").exists()  # symlink not followed


def test_symlinked_parent_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    rc = run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(tmp_path / "link" / "s.md")])
    assert rc == 2
    assert not (outside / "s.md").exists()


def test_parent_that_is_a_file_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "afile").write_text("x", encoding="utf-8")
    assert (
        run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(tmp_path / "afile" / "s.md")])
        == 2
    )


def test_write_leaves_no_temp_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    assert run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(target)]) == 0
    assert [p.name for p in tmp_path.iterdir()] == ["s.md"]  # no leftover .spec-new-*.tmp


def test_new_file_mode_is_umask_respecting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    run(["new", "--profile", "light", "--id", "SPEC-7F3Q", str(target)])
    mask = os.umask(0)
    os.umask(mask)
    assert stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(0o666 & ~mask)  # not 0600


def test_force_overwrite_preserves_target_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    target.write_text("old\n", encoding="utf-8")
    target.chmod(0o640)
    run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", str(target)])
    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_write_json_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "s.md"
    run(["new", "--profile", "light", "--id", "SPEC-7F3Q", "--json", str(target)])
    payload = _one_json(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "spec_id": "SPEC-7F3Q",
        "profile": "light",
        "path": str(target),
        "written": True,
        "overwritten": False,
    }
