"""Tests for the adopt engine's pure functions: major_ref, resolve_source, and build_plan.

Scope: unit-level — exercises the engine against the real bundles directory. Companion
files cover the path-safety / symlink surface (test_adopt_safety.py), full CLI integration
(test_adopt_cli.py), manifest parsing (test_adopt_manifest.py), dogfood byte-identity
(test_adopt_dogfood.py), and wheel packaging (test_adopt_packaging.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.adopt.engine import (
    Action,
    build_plan,
    execute_plan,
    major_ref,
    resolve_source,
)
from project_standards.adopt.errors import ManifestError, UsageError, WriteError
from project_standards.adopt.manifest import Artifact, InstallPolicy


def test_major_ref_is_vN() -> None:
    ref = major_ref()
    assert ref.startswith("v") and ref[1:].isdigit()


def test_resolve_source_rejects_absolute() -> None:
    art = Artifact(
        kind="file", owner=True, source="/etc/passwd", shared=None, dest="x", target=None
    )
    with pytest.raises(ManifestError):
        resolve_source(art, "python-tooling")


def test_resolve_source_rejects_traversal() -> None:
    art = Artifact(
        kind="file", owner=True, source="../../escape", shared=None, dest="x", target=None
    )
    with pytest.raises(ManifestError):
        resolve_source(art, "python-tooling")


def test_build_plan_dedupes_shared_editorconfig() -> None:
    plan = build_plan(["markdown-tooling", "python-tooling"])
    editorconfig_actions = [a for a in plan if a.dest == ".editorconfig"]
    assert len(editorconfig_actions) == 1


def test_build_plan_unknown_standard_raises_usageerror() -> None:
    with pytest.raises(UsageError):
        build_plan(["nope"])


def test_build_plan_collision_across_kinds(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two artifacts of DIFFERENT kinds targeting one dest from different sources -> UsageError
    # (regression guard: must not KeyError).
    import project_standards.adopt.engine as eng
    from project_standards.adopt.manifest import Artifact, Manifest

    fake = Manifest(
        id="markdown-tooling",
        artifacts=(
            Artifact(
                kind="file",
                owner=True,
                source="markdownlint.json",
                shared=None,
                dest="collide",
                target=None,
            ),
            Artifact(
                kind="workflow-caller",
                owner=True,
                source="lint-markdown.caller.yml",
                shared=None,
                dest="collide",
                target=None,
            ),
        ),
    )

    def fake_available(*_a: object, **_k: object) -> list[str]:
        return ["markdown-tooling"]

    def fake_load(*_a: object, **_k: object) -> Manifest:
        return fake

    monkeypatch.setattr(eng, "available_standards", fake_available)
    monkeypatch.setattr(eng, "load_manifest", fake_load)
    with pytest.raises(UsageError):
        build_plan(["markdown-tooling"])


def test_build_plan_rejects_different_install_policies(monkeypatch: pytest.MonkeyPatch) -> None:
    import project_standards.adopt.engine as eng
    from project_standards.adopt.manifest import Manifest

    source = "markdownlint.json"
    fake = Manifest(
        id="markdown-tooling",
        artifacts=(
            Artifact(
                kind="file",
                owner=True,
                source=source,
                shared=None,
                dest="same-dest",
                target=None,
                install_policy=InstallPolicy.MANAGED,
            ),
            Artifact(
                kind="file",
                owner=True,
                source=source,
                shared=None,
                dest="same-dest",
                target=None,
                install_policy=InstallPolicy.CREATE_ONLY,
            ),
        ),
    )

    def fake_available(*_a: object, **_k: object) -> list[str]:
        return ["markdown-tooling"]

    def fake_load(*_a: object, **_k: object) -> Manifest:
        return fake

    monkeypatch.setattr(eng, "available_standards", fake_available)
    monkeypatch.setattr(eng, "load_manifest", fake_load)

    with pytest.raises(UsageError, match="different install policies"):
        build_plan(["markdown-tooling"])


# ---------------------------------------------------------------------------
# resolve_source containment + execute_plan / _atomic_write failure paths
# ---------------------------------------------------------------------------


def test_resolve_source_symlink_escape_raises(tmp_path: Path) -> None:
    # A relative source with no ".." can still escape via a symlink inside the
    # bundle tree; the resolve()-based containment check must catch it.
    bundles = tmp_path / "bundles"
    bundle = bundles / "x"
    bundle.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    (bundle / "link.txt").symlink_to(outside)
    art = Artifact(kind="file", owner=True, source="link.txt", shared=None, dest="d", target=None)
    with pytest.raises(ManifestError, match="escapes bundle tree"):
        resolve_source(art, "x", bundles_dir=bundles)


def test_resolve_source_missing_template_raises(tmp_path: Path) -> None:
    bundles = tmp_path / "bundles"
    (bundles / "x").mkdir(parents=True)
    art = Artifact(kind="file", owner=True, source="nope.txt", shared=None, dest="d", target=None)
    with pytest.raises(ManifestError, match="source template missing"):
        resolve_source(art, "x", bundles_dir=bundles)


def test_has_symlinked_ancestor_dest_outside_root_returns_false(tmp_path: Path) -> None:
    # A leaf that is not under root at all walks every parent without hitting
    # root; the loop must terminate and report no symlinked ancestor.
    from project_standards.adopt.engine import (
        _has_symlinked_ancestor,  # pyright: ignore[reportPrivateUsage]
    )

    assert _has_symlinked_ancestor(Path("/elsewhere/leaf"), tmp_path.resolve()) is False


def test_atomic_write_cleans_tmp_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # KeyboardInterrupt mid-write must not leave a .adopt-*.tmp file behind, and
    # must re-raise rather than be converted to WriteError, so Ctrl-C still aborts.
    from project_standards.adopt.engine import _atomic_write  # pyright: ignore[reportPrivateUsage]

    def boom(*_a: object, **_k: object) -> object:
        raise KeyboardInterrupt

    monkeypatch.setattr("os.fdopen", boom)
    target = tmp_path / "out.txt"
    with pytest.raises(KeyboardInterrupt):
        _atomic_write(target, b"data")
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_execute_plan_unreadable_fragment_raises_writeerror(tmp_path: Path) -> None:
    action = Action(
        kind="fragment",
        source_path=tmp_path / "missing-snippet.md",
        dest=None,
        target="README.md",
        standards=("x",),
    )
    with pytest.raises(WriteError, match="cannot read fragment"):
        execute_plan([action], tmp_path, force=False, dry_run=True)


def test_force_never_overwrites_create_only(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("template\n", encoding="utf-8")
    target = tmp_path / "consumer" / "docs" / "STATUS.md"
    target.parent.mkdir(parents=True)
    target.write_text("consumer knowledge\n", encoding="utf-8")
    action = Action(
        kind="file",
        source_path=source,
        dest="docs/STATUS.md",
        target=None,
        standards=("agent-handoff",),
        mode=None,
        install_policy=InstallPolicy.CREATE_ONLY,
    )

    report = execute_plan([action], target.parents[1], force=True, dry_run=False)

    assert target.read_text(encoding="utf-8") == "consumer knowledge\n"
    assert report.skipped == ["docs/STATUS.md"]


def test_validate_dest_lexical_escape_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # On POSIX every escape vector is already rejected by _require_safe_relative,
    # so the normpath containment check is exercised by injection (it guards
    # Windows-style vectors like drive-letter rels that POSIX treats as plain names).
    import os

    from project_standards.adopt.engine import validate_dest

    def fake_normpath(_p: object) -> str:
        return "/elsewhere"

    monkeypatch.setattr(os.path, "normpath", fake_normpath)
    with pytest.raises(UsageError, match="destination escapes --dest"):
        validate_dest("inner.txt", Path("/srv/dest"))


def test_atomic_write_interrupt_before_tmp_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An interrupt before mkstemp succeeds means there is no temp file to clean
    # up; the handler must re-raise without touching anything.
    import tempfile

    from project_standards.adopt.engine import _atomic_write  # pyright: ignore[reportPrivateUsage]

    def boom(*_a: object, **_k: object) -> tuple[int, str]:
        raise KeyboardInterrupt

    monkeypatch.setattr(tempfile, "mkstemp", boom)
    with pytest.raises(KeyboardInterrupt):
        _atomic_write(tmp_path / "out.txt", b"data")
    assert list(tmp_path.iterdir()) == []
