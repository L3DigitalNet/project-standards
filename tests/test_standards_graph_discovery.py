from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.standard_manifest import StandardManifestError
from project_standards.standards_graph.discovery import (
    build_graph,
    discover_manifest_paths,
    discover_standard_dirs,
)
from tests.standards_graph_helpers import write_standard


def test_write_standard_helper_creates_loadable_shape(tmp_path: Path) -> None:
    bundle = write_standard(tmp_path, "alpha", namespaces=["alpha"])

    assert (bundle / "README.md").is_file()
    assert (bundle / "standard.toml").read_text(encoding="utf-8").startswith("[standard]")


def test_discover_standard_dirs_ignores_non_directories(tmp_path: Path) -> None:
    write_standard(tmp_path, "beta")
    (tmp_path / "standards" / "README.md").write_text("# index\n", encoding="utf-8")

    assert discover_standard_dirs(tmp_path) == [tmp_path / "standards" / "beta"]


def test_discover_manifest_paths_are_sorted(tmp_path: Path) -> None:
    write_standard(tmp_path, "zeta")
    write_standard(tmp_path, "alpha")

    assert [path.parent.name for path in discover_manifest_paths(tmp_path)] == ["alpha", "zeta"]


def test_build_graph_loads_manifest_nodes_and_missing_dirs(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha")
    missing = tmp_path / "standards" / "beta"
    missing.mkdir(parents=True)
    (missing / "README.md").write_text("# beta\n", encoding="utf-8")

    graph = build_graph(tmp_path)

    assert [node.standard_id for node in graph.standards] == ["alpha"]
    assert graph.missing_manifest_dirs == (missing,)


def test_requires_field_is_rejected_as_hidden_dependency(tmp_path: Path) -> None:
    bundle = write_standard(tmp_path, "alpha", relation_extras={"requires": ["beta"]})

    with pytest.raises(StandardManifestError) as exc_info:
        build_graph(tmp_path)

    message = str(exc_info.value)
    assert "requires" in message
    assert "Extra inputs are not permitted" in message
    assert bundle.name == "alpha"


def test_real_repo_graph_loads_manifest_backed_standards() -> None:
    root = Path(__file__).resolve().parent.parent

    graph = build_graph(root)

    assert graph.ids == frozenset({"standard-bundle-authoring"})
    assert any(path.name == "markdown-frontmatter" for path in graph.missing_manifest_dirs)


def test_build_graph_requires_existing_standards_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="standards"):
        build_graph(tmp_path)
