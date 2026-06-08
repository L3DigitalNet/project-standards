from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.adopt.engine import Action, execute_plan, validate_dest
from project_standards.adopt.errors import UsageError


def _file_action(tmp_path: Path, dest: str) -> Action:
    src = tmp_path / "src.txt"
    src.write_text("canonical\n")
    return Action(kind="file", source_path=src, dest=dest, target=None, standards=("x",))


def test_validate_dest_rejects_absolute(tmp_path: Path) -> None:
    with pytest.raises(UsageError):
        validate_dest("/etc/cron.d/evil", tmp_path)


def test_validate_dest_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(UsageError):
        validate_dest("../escape", tmp_path)


def test_execute_creates_then_skips(tmp_path: Path) -> None:
    plan = [_file_action(tmp_path, "a/b.txt")]
    r1 = execute_plan(plan, tmp_path, force=False, dry_run=False)
    assert r1.created == ["a/b.txt"]
    assert (tmp_path / "a/b.txt").read_text() == "canonical\n"
    r2 = execute_plan(plan, tmp_path, force=False, dry_run=False)
    assert r2.skipped == ["a/b.txt"] and r2.created == []


def test_force_overwrites_regular_file(tmp_path: Path) -> None:
    plan = [_file_action(tmp_path, "c.txt")]
    (tmp_path / "c.txt").write_text("old\n")
    r = execute_plan(plan, tmp_path, force=True, dry_run=False)
    assert r.overwritten == ["c.txt"] and (tmp_path / "c.txt").read_text() == "canonical\n"


def test_symlink_dest_skipped_even_with_force(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("precious\n")
    link = tmp_path / "d.txt"
    link.symlink_to(outside)
    plan = [_file_action(tmp_path, "d.txt")]
    r = execute_plan(plan, tmp_path, force=True, dry_run=False)
    assert r.symlink_skipped == ["d.txt"]
    assert outside.read_text() == "precious\n"  # never written through the symlink


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    plan = [_file_action(tmp_path, "e.txt")]
    r = execute_plan(plan, tmp_path, force=False, dry_run=True)
    assert r.created == ["e.txt"] and not (tmp_path / "e.txt").exists()
