from __future__ import annotations

from pathlib import Path

from project_standards.standards_graph.catalog import load_contract_defaults, render_catalog
from project_standards.standards_graph.discovery import build_graph
from tests.standards_graph_helpers import write_standard

_REPO = Path(__file__).resolve().parent.parent


def test_catalog_renders_all_manifest_and_relationship_facts() -> None:
    graph = build_graph(_REPO)

    rendered = render_catalog(graph, contract_defaults=load_contract_defaults(graph))

    for standard_id in graph.ids:
        assert f"`{standard_id}`" in rendered
    assert "Package" in rendered
    assert "Role" in rendered
    assert "Managed outputs" in rendered
    assert "standards://markdown-frontmatter/1.2/readme" in rendered
    assert "markdown-frontmatter" in rendered
    assert "markdown-tooling" in rendered
    assert "companion" in rendered
    assert "[`agent-handoff`](agent-handoff/README.md)" in rendered
    assert "standards://agent-handoff/1.1/skill" in rendered
    assert "startup\\|resume\\|clear\\|compact" in rendered


def test_catalog_is_deterministic() -> None:
    graph = build_graph(_REPO)

    assert render_catalog(graph) == render_catalog(graph)
    assert "Generated at" not in render_catalog(graph)


def test_catalog_matches_checked_in_generated_file() -> None:
    graph = build_graph(_REPO)
    rendered = render_catalog(graph, contract_defaults=load_contract_defaults(graph))

    assert (_REPO / "standards/catalog.md").read_text(encoding="utf-8") == rendered


def test_catalog_renders_exact_synthetic_contract_matrix(tmp_path: Path) -> None:
    artifact_path = "src/project_standards/bundles/alpha/adopt.toml"
    write_standard(
        tmp_path,
        "alpha",
        status="review",
        adoption="copy-adopt",
        supported_versions=["1.0", "2.0"],
        latest_version="2.0",
        namespaces=["alpha.config"],
        provides=["alpha.render"],
        consumes_platform=["project-standards.render"],
        companions=["beta"],
        extends=["beta"],
        conflicts=["gamma"],
        resources={"adopt": "adopt.md", "extension_adr": "resources/extension.md"},
        providers=[
            {
                "operation": "render",
                "kind": "python",
                "entrypoint": "pkg.alpha:render",
                "optional": False,
            }
        ],
        artifact_manifest=artifact_path,
    )
    write_standard(tmp_path, "beta")
    write_standard(tmp_path, "gamma")
    packaged = tmp_path / artifact_path
    packaged.parent.mkdir(parents=True)
    packaged.write_text(
        """[standard]
id = "alpha"

[[artifact]]
kind = "file"
source = "source.txt"
dest = "source.txt"
provenance = "source-owned"
canonical = "standards/alpha/source.txt"

[[artifact]]
kind = "file"
source = "generated.txt"
dest = "generated.txt"
provenance = "generated"
canonical = "standards/alpha/source.txt"
transform = "render"

[[artifact]]
kind = "file"
source = "skills/alpha/SKILL.md"
dest = ".agents/skills/alpha/SKILL.md"
provenance = "package-owned"

[[artifact]]
kind = "file"
shared = "_shared/editorconfig"
dest = ".editorconfig"
provenance = "external-owned"
""",
        encoding="utf-8",
    )

    rendered = render_catalog(build_graph(tmp_path), contract_defaults={"alpha": "2.0"})

    assert (
        "| [`alpha`](alpha/README.md) | review | copy-adopt | "
        "2.0 (supported: 1.0, 2.0) | 2.0 | `alpha.config` | 4 | ready |"
    ) in rendered
    assert "| `alpha` | `alpha.render` | `project-standards.render` |" in rendered
    assert "| `alpha` | companion | `beta` |" in rendered
    assert "| `alpha` | extends | `beta` |" in rendered
    assert "| `alpha` | conflicts | `gamma` |" in rendered
    assert "| `alpha` | `render` | python | `pkg.alpha:render` | no |" in rendered
    assert "external-owned: 1, generated: 1, package-owned: 1, source-owned: 1" in rendered
    assert "`.agents/skills/alpha/SKILL.md`" in rendered
    assert "`standards://alpha/extension_adr`" in rendered
