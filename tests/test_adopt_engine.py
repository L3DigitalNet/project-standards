"""Tests for the adopt engine's pure functions: major_ref, resolve_source, and build_plan.

Scope: unit-level — exercises the engine against the real bundles directory. Companion
files cover the path-safety / symlink surface (test_adopt_safety.py), full CLI integration
(test_adopt_cli.py), manifest parsing (test_adopt_manifest.py), dogfood byte-identity
(test_adopt_dogfood.py), and wheel packaging (test_adopt_packaging.py).
"""

from __future__ import annotations

import pytest

from project_standards.adopt.engine import build_plan, major_ref, resolve_source
from project_standards.adopt.errors import ManifestError, UsageError
from project_standards.adopt.manifest import Artifact


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
