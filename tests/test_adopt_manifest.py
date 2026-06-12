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


# ---------------------------------------------------------------------------
# available_standards / load_manifest validation branches
# ---------------------------------------------------------------------------


def _manifest(tmp_path: Path, body: str, standard_id: str = "x") -> None:
    """Write *body* as adopt.toml for a bundle named *standard_id* under tmp_path."""
    bundle = tmp_path / standard_id
    bundle.mkdir(exist_ok=True)
    (bundle / "adopt.toml").write_text(body, encoding="utf-8")


def test_available_standards_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="bundles directory missing"):
        available_standards(tmp_path / "nope")


def test_available_standards_skips_bundle_without_manifest(tmp_path: Path) -> None:
    _manifest(tmp_path, '[standard]\nid = "a"\n', standard_id="a")
    (tmp_path / "b").mkdir()  # bundle dir with no adopt.toml -> not adoptable
    (tmp_path / "_shared").mkdir()
    assert available_standards(tmp_path) == ["a"]


def test_load_manifest_invalid_toml_raises(tmp_path: Path) -> None:
    _manifest(tmp_path, "not = valid = toml")
    with pytest.raises(ManifestError, match="cannot read manifest"):
        load_manifest("x", bundles_dir=tmp_path)


def test_load_manifest_non_table_payload_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # tomllib.loads can only ever return a dict, so the not-a-table guard is
    # reachable solely by failure injection — covered anyway because
    # load_manifest must keep failing closed if the parser is ever swapped out.
    import project_standards.adopt.manifest as manifest_mod

    _manifest(tmp_path, '[standard]\nid = "x"\n')

    def fake_loads(_s: str) -> list[object]:
        return []

    monkeypatch.setattr(manifest_mod.tomllib, "loads", fake_loads)
    with pytest.raises(ManifestError, match="not a TOML table"):
        load_manifest("x", bundles_dir=tmp_path)


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ('id = "x"\n', r"missing/mismatched \[standard\].id"),
        ('[standard]\nid = "other"\n', r"missing/mismatched \[standard\].id"),
        # artifact must precede the [standard] header — written after it, TOML
        # would nest the key inside the standard table and the loader would see
        # no artifacts at all.
        ('artifact = "oops"\n[standard]\nid = "x"\n', r"\[\[artifact\]\] is not a list"),
        ('artifact = ["oops"]\n[standard]\nid = "x"\n', "artifact 0 is not a table"),
        (
            '[standard]\nid = "x"\n\n[[artifact]]\nkind = "weird"\nsource = "s"\ndest = "d"\n',
            "unknown kind",
        ),
        (
            '[standard]\nid = "x"\n\n[[artifact]]\nkind = "file"\nsource = "s"\nshared = "sh"\ndest = "d"\n',
            "exactly one of source/shared",
        ),
        (
            '[standard]\nid = "x"\n\n[[artifact]]\nkind = "file"\ndest = "d"\n',
            "exactly one of source/shared",
        ),
        (
            '[standard]\nid = "x"\n\n[[artifact]]\nkind = "fragment"\nsource = "s"\n',
            "needs a target",
        ),
        (
            '[standard]\nid = "x"\n\n[[artifact]]\nkind = "file"\nsource = "s"\n',
            "needs a dest",
        ),
    ],
)
def test_load_manifest_validation_raises(tmp_path: Path, body: str, match: str) -> None:
    _manifest(tmp_path, body)
    with pytest.raises(ManifestError, match=match):
        load_manifest("x", bundles_dir=tmp_path)
