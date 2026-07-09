"""Typed standards graph data structures and finding renderers."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from project_standards.standard_manifest import StandardManifest

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class GraphFinding:
    """A deterministic standards-graph validation finding."""

    code: str
    severity: Severity
    standard_id: str
    path: str
    message: str
    hint: str


@dataclass(frozen=True)
class StandardNode:
    """One loaded standard bundle in the graph."""

    standard_id: str
    bundle_dir: Path
    manifest_path: Path
    manifest: StandardManifest


@dataclass(frozen=True)
class StandardsGraph:
    """Loaded standards plus discovery metadata for graph-wide checks."""

    root: Path
    standards: tuple[StandardNode, ...]
    missing_manifest_dirs: tuple[Path, ...]

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(node.standard_id for node in self.standards)

    @property
    def by_id(self) -> dict[str, StandardNode]:
        return {node.standard_id: node for node in self.standards}


def finding_sort_key(finding: GraphFinding) -> tuple[str, str, str, str]:
    return (finding.code, finding.standard_id, finding.path, finding.message)


def sort_findings(findings: list[GraphFinding]) -> list[GraphFinding]:
    """Return findings in deterministic report order."""
    return sorted(findings, key=finding_sort_key)


def findings_to_jsonable(findings: list[GraphFinding]) -> list[dict[str, object]]:
    """Return findings in the stable CLI JSON shape."""
    return [dataclasses.asdict(finding) for finding in sort_findings(findings)]


def format_findings(findings: list[GraphFinding]) -> str:
    """Render findings for humans."""
    if not findings:
        return "OK standards graph"
    lines: list[str] = []
    for finding in sort_findings(findings):
        owner = f"{finding.standard_id}: " if finding.standard_id else ""
        lines.append(f"{finding.severity.upper()} [{finding.code}] {owner}{finding.message}")
        lines.append(f"  path: {finding.path}")
        lines.append(f"  hint: {finding.hint}")
    return "\n".join(lines)
