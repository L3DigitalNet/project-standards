"""Tests for adopt-engine path-containment and symlink safety.

Scope: validate_dest, execute_plan's symlink detection, and _atomic_write failure modes.
Covers the full attack surface the engine defends against:
  - Absolute and ../-traversal destinations (validate_dest → UsageError)
  - Symlinked-leaf destinations (skipped even with --force)
  - Symlinked parent directories that could redirect writes outside --dest
  - Broken (dangling) symlinks
  - WriteError mapping for staging failure, unreadable source, and os.replace failure
  - Create-only hard-link publication, cleanup failures, and unsupported filesystems
  - Fragment target path-safety (UsageError on traversal even though fragments never write)
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from project_standards.adopt.engine import Action, execute_plan, validate_dest
from project_standards.adopt.errors import UsageError, WriteError


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


def test_atomic_write_failure_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import project_standards.adopt.engine as eng

    target = tmp_path / "keep.txt"
    target.write_text("original\n")
    plan = [_file_action(tmp_path, "keep.txt")]

    def boom(_src: str, _dst: str, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(eng.os, "replace", boom)
    with pytest.raises(WriteError):
        eng.execute_plan(plan, tmp_path, force=True, dry_run=False)
    assert target.read_text() == "original\n"  # untouched
    assert not list(tmp_path.glob(".adopt-*"))  # temp cleaned up


def test_create_only_transient_cleanup_failure_reports_installed_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from project_standards.adopt.engine import _atomic_write  # pyright: ignore[reportPrivateUsage]

    target = tmp_path / "STATUS.md"
    real_unlink = os.unlink
    attempts = 0

    def flaky_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal attempts
        if isinstance(path, str) and path.startswith(".adopt-"):
            attempts += 1
            if attempts == 1:
                raise PermissionError("staging cleanup blocked")
        real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(os, "unlink", flaky_unlink)

    with pytest.raises(
        WriteError, match=r"destination .* was installed but staging cleanup failed"
    ) as exc_info:
        _atomic_write(target, b"template\n", replace=False)

    assert isinstance(exc_info.value.__cause__, PermissionError)
    assert target.read_bytes() == b"template\n"
    assert list(tmp_path.glob(".adopt-*.tmp")) == []
    assert attempts == 2


def test_create_only_persistent_cleanup_failure_never_masks_writeerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from project_standards.adopt.engine import _atomic_write  # pyright: ignore[reportPrivateUsage]

    target = tmp_path / "STATUS.md"
    real_unlink = os.unlink
    attempts = 0

    def blocked_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal attempts
        if isinstance(path, str) and path.startswith(".adopt-"):
            attempts += 1
            raise PermissionError("staging cleanup blocked")
        real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(os, "unlink", blocked_unlink)

    with pytest.raises(
        WriteError, match=r"destination .* was installed but staging cleanup failed"
    ) as exc_info:
        _atomic_write(target, b"template\n", replace=False)

    assert isinstance(exc_info.value.__cause__, PermissionError)
    assert target.read_bytes() == b"template\n"
    staged = list(tmp_path.glob(".adopt-*.tmp"))
    assert len(staged) == 1
    assert staged[0].read_bytes() == b"template\n"
    assert attempts == 2


def test_create_only_unsupported_hard_link_fails_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import project_standards.adopt.engine as engine

    target = tmp_path / "STATUS.md"

    def unsupported_link(_src: str, _dst: str, **_kwargs: object) -> None:
        raise OSError(errno.EOPNOTSUPP, "hard links unsupported")

    monkeypatch.setattr(engine.os, "link", unsupported_link)

    with pytest.raises(WriteError, match="failed writing") as exc_info:
        engine._atomic_write(  # pyright: ignore[reportPrivateUsage]
            target, b"template\n", replace=False
        )

    assert isinstance(exc_info.value.__cause__, OSError)
    assert exc_info.value.__cause__.errno == errno.EOPNOTSUPP
    assert not target.exists()
    assert list(tmp_path.glob(".adopt-*.tmp")) == []


def test_source_side_unsafe_rejected() -> None:
    from project_standards.adopt.engine import resolve_source
    from project_standards.adopt.errors import ManifestError
    from project_standards.adopt.manifest import Artifact

    art = Artifact(kind="file", owner=True, source=None, shared="../x", dest="x", target=None)
    with pytest.raises(ManifestError):
        resolve_source(art, "markdown-tooling")


def test_format_report_groups_fragments_by_target() -> None:
    from project_standards.adopt.engine import Report, format_report

    r = Report()
    r.created.append(".markdownlint.json")
    r.fragments["pyproject.toml"] = ["[tool.ruff]\n"]
    r.fragments[".project-standards.yml"] = ["markdown:\n  adr:\n"]
    out = format_report(r)
    assert "Add these sections to `pyproject.toml`" in out
    assert "Add these sections to `.project-standards.yml`" in out
    assert ".markdownlint.json" in out


def test_format_report_keeps_multiple_fragments_for_one_target() -> None:
    from project_standards.adopt.engine import Report, format_report

    r = Report()
    r.fragments[".project-standards.yml"] = ["# block A\nfoo: 1\n", "# block B\nbar: 2\n"]
    out = format_report(r)
    assert "block A" in out and "block B" in out  # neither snippet dropped


def test_execute_maps_staging_open_failure_to_writeerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import project_standards.adopt.engine as eng

    real_open = os.open

    def boom(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if isinstance(path, str) and path.startswith(".adopt-"):
            raise OSError("no temp")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(eng.os, "open", boom)
    plan = [_file_action(tmp_path, "x.txt")]
    with pytest.raises(WriteError):
        eng.execute_plan(plan, tmp_path, force=False, dry_run=False)
    assert not (tmp_path / "x.txt").exists()


def test_execute_maps_unreadable_source_to_writeerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import project_standards.adopt.engine as eng

    def boom(_self: Path) -> bytes:
        raise OSError("unreadable")

    monkeypatch.setattr(eng.Path, "read_bytes", boom)
    plan = [_file_action(tmp_path, "y.txt")]
    with pytest.raises(WriteError):
        eng.execute_plan(plan, tmp_path, force=False, dry_run=False)


def test_symlink_to_internal_target_skipped(tmp_path: Path) -> None:
    # Link whose target is a regular file *inside* dest: must still be detected as a symlink
    # (regression guard for resolve()-before-is_symlink()).
    from project_standards.adopt.engine import execute_plan

    real = tmp_path / "real.txt"
    real.write_text("inside\n")
    (tmp_path / "f.txt").symlink_to(real)
    r = execute_plan([_file_action(tmp_path, "f.txt")], tmp_path, force=True, dry_run=False)
    assert r.symlink_skipped == ["f.txt"]
    assert real.read_text() == "inside\n"  # not written through the link


def test_broken_symlink_dest_skipped(tmp_path: Path) -> None:
    from project_standards.adopt.engine import execute_plan

    (tmp_path / "g.txt").symlink_to(tmp_path / "missing")  # dangling
    r = execute_plan([_file_action(tmp_path, "g.txt")], tmp_path, force=True, dry_run=False)
    assert r.symlink_skipped == ["g.txt"]


def test_symlinked_parent_dir_not_written_through(tmp_path: Path) -> None:
    # --dest/linkdir is a symlink to a dir OUTSIDE --dest; writing linkdir/file must not escape.
    outside = tmp_path / "outside"
    outside.mkdir()
    dest = tmp_path / "repo"
    dest.mkdir()
    (dest / "linkdir").symlink_to(outside)
    from project_standards.adopt.engine import execute_plan

    r = execute_plan([_file_action(tmp_path, "linkdir/f.txt")], dest, force=True, dry_run=False)
    assert r.symlink_skipped == ["linkdir/f.txt"]
    assert not (outside / "f.txt").exists()  # nothing written outside --dest


def test_parent_symlink_swap_race_does_not_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.adopt.engine as engine

    root = tmp_path / "repo"
    parent = root / "nested"
    parent.mkdir(parents=True)
    detached = root / "detached"
    outside = tmp_path / "outside"
    outside.mkdir()
    original_render = engine.render_action

    def racing_render(action: Action, ref: str | None = None) -> bytes:
        content = original_render(action, ref)
        parent.rename(detached)
        parent.symlink_to(outside, target_is_directory=True)
        return content

    monkeypatch.setattr(engine, "render_action", racing_render)

    with pytest.raises(WriteError):
        execute_plan(
            [_file_action(tmp_path, "nested/managed.txt")],
            root,
            force=False,
            dry_run=False,
        )

    assert not (outside / "managed.txt").exists()
    assert not (detached / "managed.txt").exists()


def test_leaf_symlink_swap_race_does_not_clobber(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.adopt.engine as engine

    root = tmp_path / "repo"
    root.mkdir()
    target = root / "managed.txt"
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    original_render = engine.render_action

    def racing_render(action: Action, ref: str | None = None) -> bytes:
        content = original_render(action, ref)
        target.symlink_to(outside)
        return content

    monkeypatch.setattr(engine, "render_action", racing_render)

    report = execute_plan(
        [_file_action(tmp_path, "managed.txt")],
        root,
        force=False,
        dry_run=False,
    )

    assert target.is_symlink()
    assert outside.read_text(encoding="utf-8") == "outside\n"
    assert report.created == []
    assert report.skipped == ["managed.txt"]


def test_atomic_write_new_file_is_group_other_readable(tmp_path: Path) -> None:
    # Regression: _atomic_write previously used mkstemp's default 0600, leaving new adopted
    # files owner-only. With fix C the mode must be umask-respecting (like a normal file
    # creation), so at minimum the group and other readable bits that the umask permits must
    # be set (fix C from round-3 review).
    plan = [_file_action(tmp_path, "new_file.txt")]
    r = execute_plan(plan, tmp_path, force=False, dry_run=False)
    assert r.created == ["new_file.txt"]
    mode = (tmp_path / "new_file.txt").stat().st_mode & 0o777
    # Under a typical umask (0o022) the result is 0o644. The important invariant is that
    # the file is NOT stuck at 0o600 (owner-only). At minimum, world-read or group-read must
    # be present unless the umask strips all public bits (umask 0o177 or stricter).
    import os

    mask = os.umask(0)
    os.umask(mask)
    expected = 0o666 & ~mask
    assert mode == expected or expected == 0, (
        f"Expected mode {oct(expected)}, got {oct(mode)} — adopted file must not be 0600"
    )


def test_unsafe_fragment_target_rejected(tmp_path: Path) -> None:
    from project_standards.adopt.engine import Action, execute_plan
    from project_standards.adopt.errors import UsageError

    src = tmp_path / "frag.txt"
    src.write_text("frag\n")
    for bad in ("../escape.yml", "/etc/evil.yml"):
        plan = [Action(kind="fragment", source_path=src, dest=None, target=bad, standards=("x",))]
        with pytest.raises(UsageError):
            execute_plan(plan, tmp_path, force=False, dry_run=False)
