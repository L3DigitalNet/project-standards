"""Tests for adopt manifest loading and available-standards discovery.

Scope: available_standards() and load_manifest() — the TOML parsing and validation
layer that sits between raw adopt.toml files and the engine's build_plan step.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.adopt.errors import ManifestError
from project_standards.adopt.manifest import available_standards, load_manifest


def test_available_standards_lists_four_released_excludes_shared() -> None:
    ids = available_standards()
    assert set(ids) == {"markdown-frontmatter", "adr", "markdown-tooling", "python-tooling"}
    assert "_shared" not in ids


def test_load_manifest_parses_artifacts() -> None:
    m = load_manifest("markdown-tooling")
    assert m.id == "markdown-tooling"
    kinds = {a.kind for a in m.artifacts}
    assert kinds == {"file", "workflow-caller"}
    shared = [a for a in m.artifacts if a.shared is not None]
    assert any(a.shared == "_shared/editorconfig" for a in shared)


def test_load_manifest_unknown_raises_manifesterror() -> None:
    with pytest.raises(ManifestError):
        load_manifest("does-not-exist")


def test_load_manifest_rejects_non_string_field(tmp_path: Path) -> None:
    bundle = tmp_path / "x"
    bundle.mkdir()
    (bundle / "adopt.toml").write_text(
        '[standard]\nid = "x"\n\n[[artifact]]\nkind = "file"\nowner = true\nsource = 1\ndest = "y"\n'
    )
    with pytest.raises(ManifestError):
        load_manifest("x", bundles_dir=tmp_path)
