from __future__ import annotations

from pathlib import Path

import yaml

from project_standards.adopt.engine import major_ref, resolve_source
from project_standards.adopt.manifest import available_standards, load_manifest

_REPO = Path(__file__).resolve().parent.parent
_BUNDLES = _REPO / "src" / "project_standards" / "bundles"

# Bundle source file -> repo root working file it must stay byte-identical to.
_DOGFOOD = {
    "_shared/editorconfig": ".editorconfig",
    "_shared/vscode-extensions.json": ".vscode/extensions.json",
    "markdown-tooling/markdownlint.json": ".markdownlint.json",
    "markdown-tooling/prettierrc.json": ".prettierrc.json",
    "python-tooling/check.yml": ".github/workflows/check.yml",
    "python-tooling/check.py": "scripts/check.py",
}


def test_dogfoodable_templates_match_repo_root_byte_for_byte() -> None:
    for bundle_rel, root_rel in _DOGFOOD.items():
        assert (_BUNDLES / bundle_rel).read_bytes() == (_REPO / root_rel).read_bytes(), bundle_rel


def test_every_manifest_source_resolves_to_one_file() -> None:
    for sid in available_standards():
        for art in load_manifest(sid).artifacts:
            assert resolve_source(art, sid).is_file()


def test_caller_stubs_valid_and_reference_correct_workflow() -> None:
    ref = major_ref()
    cases = {
        "markdown-frontmatter/validate-markdown-frontmatter.caller.yml": (
            "validate-markdown-frontmatter.yml"
        ),
        "markdown-tooling/lint-markdown.caller.yml": "lint-markdown.yml",
    }
    for rel, workflow in cases.items():
        raw = (_BUNDLES / rel).read_text()
        rendered = raw.replace("{{ref}}", ref)
        assert "\t" not in rendered  # no tab indentation
        doc = yaml.safe_load(rendered)
        uses = doc["jobs"][next(iter(doc["jobs"]))]["uses"]
        assert workflow in uses and uses.endswith(f"@{ref}")


def test_generated_workflow_yaml_has_no_tabs() -> None:
    # check.yml (kind=file) ships verbatim; assert it is space-indented.
    assert "\t" not in (_BUNDLES / "python-tooling" / "check.yml").read_text()


def test_starter_config_is_generic_consumer_scope(tmp_path: Path) -> None:
    from project_standards.cli import main

    main(["adopt", "markdown-frontmatter", "--dest", str(tmp_path)])
    cfg = yaml.safe_load((tmp_path / ".project-standards.yml").read_text())
    include = cfg["markdown"]["frontmatter"]["include"]
    exclude = cfg["markdown"]["frontmatter"]["exclude"]
    assert "README.md" in include and "docs/**/*.md" in include
    assert not any("standards/**" in p or "meta/**" in p for p in include)
    assert "**/*.template.md" in exclude  # ADR-template safety


def test_agent_stub_is_generic_no_handoff_content(tmp_path: Path) -> None:
    from project_standards.cli import main

    main(["adopt", "python-tooling", "--dest", str(tmp_path)])
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "Python Tooling SSOT" in agents
    assert "docs/handoff" not in agents and "project-standards" not in agents.lower()
