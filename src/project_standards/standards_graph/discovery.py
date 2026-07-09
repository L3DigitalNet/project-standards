"""Discover standard bundles and load them into a standards graph."""

from __future__ import annotations

from pathlib import Path

from project_standards.adopt.manifest import load_manifest as load_artifact_manifest
from project_standards.standard_manifest import load_standard_manifest
from project_standards.standards_graph.model import StandardNode, StandardsGraph


def discover_standard_dirs(root: Path) -> list[Path]:
    """Return sorted `standards/{id}` directories under root."""
    standards_dir = root / "standards"
    if not standards_dir.is_dir():
        return []
    return sorted(path for path in standards_dir.iterdir() if path.is_dir())


def discover_manifest_paths(root: Path) -> list[Path]:
    """Return sorted manifest paths under `standards/*/standard.toml`."""
    return [
        path / "standard.toml"
        for path in discover_standard_dirs(root)
        if (path / "standard.toml").is_file()
    ]


def discover_artifact_manifest_paths(root: Path) -> list[Path]:
    """Return sorted packaged artifact manifests under the repository bundle tree."""
    bundles = root / "src" / "project_standards" / "bundles"
    if not bundles.is_dir():
        return []
    return sorted(
        (child / "adopt.toml").resolve()
        for child in bundles.iterdir()
        if child.is_dir() and child.name != "_shared" and (child / "adopt.toml").is_file()
    )


def build_graph(root: Path) -> StandardsGraph:
    """Load manifest-backed standards from root."""
    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        msg = f"root is not a directory: {root}"
        raise ValueError(msg)
    standards_dir = resolved_root / "standards"
    if not standards_dir.is_dir():
        msg = f"root has no standards directory: {resolved_root}"
        raise ValueError(msg)

    nodes: list[StandardNode] = []
    missing_manifest_dirs: list[Path] = []
    linked_artifact_paths: set[Path] = set()
    for bundle_dir in discover_standard_dirs(resolved_root):
        manifest_path = bundle_dir / "standard.toml"
        if not manifest_path.is_file():
            missing_manifest_dirs.append(bundle_dir)
            continue
        manifest = load_standard_manifest(manifest_path)
        standard_id = manifest.standard.id
        artifact_manifest_path: Path | None = None
        artifact_manifest = None
        if manifest.artifacts is not None:
            artifact_manifest_path = (resolved_root / manifest.artifacts.manifest).resolve()
            linked_artifact_paths.add(artifact_manifest_path)
            expected_parent = resolved_root / "src" / "project_standards" / "bundles" / standard_id
            if (
                artifact_manifest_path.is_relative_to(resolved_root)
                and artifact_manifest_path.parent == expected_parent
                and artifact_manifest_path.is_file()
            ):
                artifact_manifest = load_artifact_manifest(
                    standard_id, bundles_dir=artifact_manifest_path.parent.parent
                )
        nodes.append(
            StandardNode(
                standard_id=standard_id,
                bundle_dir=bundle_dir,
                manifest_path=manifest_path,
                manifest=manifest,
                artifact_manifest_path=artifact_manifest_path,
                artifact_manifest=artifact_manifest,
            )
        )
    discovered_artifacts = set(discover_artifact_manifest_paths(resolved_root))
    return StandardsGraph(
        root=resolved_root,
        standards=tuple(sorted(nodes, key=lambda node: node.standard_id)),
        missing_manifest_dirs=tuple(sorted(missing_manifest_dirs)),
        orphan_artifact_manifests=tuple(sorted(discovered_artifacts - linked_artifact_paths)),
    )
