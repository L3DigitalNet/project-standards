from __future__ import annotations

import json
from pathlib import Path

from project_standards.standard_manifest import StandardManifest
from project_standards.standards_graph.model import (
    GraphFinding,
    StandardNode,
    StandardsGraph,
    findings_to_jsonable,
    format_findings,
    sort_findings,
)


def _manifest(standard_id: str) -> StandardManifest:
    return StandardManifest.model_validate(
        {
            "standard": {
                "id": standard_id,
                "name": standard_id.title(),
                "status": "active",
                "summary": "Example standard.",
                "adoption": "none",
            },
            "versions": {"supported": [], "latest": ""},
            "config": {"namespaces": []},
            "capabilities": {"provides": [], "consumes_platform": []},
            "relations": {"companions": [], "extends": [], "conflicts": []},
            "resources": {"readme": "README.md"},
        }
    )


def test_finding_json_shape_is_stable() -> None:
    finding = GraphFinding(
        code="SG-CONFIG-DUPLICATE-NAMESPACE",
        severity="error",
        standard_id="alpha",
        path="standards/alpha/standard.toml",
        message="namespace 'spec' is claimed by alpha and beta",
        hint="choose one owning standard for namespace 'spec'",
    )

    payload = findings_to_jsonable([finding])

    assert payload == [
        {
            "code": "SG-CONFIG-DUPLICATE-NAMESPACE",
            "severity": "error",
            "standard_id": "alpha",
            "path": "standards/alpha/standard.toml",
            "message": "namespace 'spec' is claimed by alpha and beta",
            "hint": "choose one owning standard for namespace 'spec'",
        }
    ]
    assert json.loads(json.dumps(payload)) == payload


def test_human_format_includes_rule_standard_path_and_hint() -> None:
    finding = GraphFinding(
        code="SG-REL-MISSING-STANDARD",
        severity="error",
        standard_id="alpha",
        path="standards/alpha/standard.toml",
        message="alpha companion 'missing' is not a known standard",
        hint="declare only existing standard ids in relations",
    )

    text = format_findings([finding])

    assert "[SG-REL-MISSING-STANDARD]" in text
    assert "alpha" in text
    assert "standards/alpha/standard.toml" in text
    assert "declare only existing standard ids" in text


def test_graph_indexes_nodes_by_standard_id() -> None:
    alpha = StandardNode(
        standard_id="alpha",
        bundle_dir=Path("standards/alpha"),
        manifest_path=Path("standards/alpha/standard.toml"),
        manifest=_manifest("alpha"),
    )
    graph = StandardsGraph(root=Path(), standards=(alpha,), missing_manifest_dirs=())

    assert graph.ids == frozenset({"alpha"})
    assert graph.by_id["alpha"] is alpha


def test_ownerless_findings_sort_without_type_error() -> None:
    findings = [
        GraphFinding(
            code="SG-Z",
            severity="error",
            standard_id="alpha",
            path="standards/alpha/standard.toml",
            message="z",
            hint="fix z",
        ),
        GraphFinding(
            code="SG-A",
            severity="error",
            standard_id="",
            path=".",
            message="a",
            hint="fix a",
        ),
    ]

    assert [finding.code for finding in sort_findings(findings)] == ["SG-A", "SG-Z"]
    assert [entry["code"] for entry in findings_to_jsonable(findings)] == ["SG-A", "SG-Z"]
