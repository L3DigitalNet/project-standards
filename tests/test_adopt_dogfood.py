"""Dogfood tests: bundle source files must stay byte-identical to their repo-root counterparts.

The _DOGFOOD dict maps each bundle artifact that this repo self-adopts to the working-copy
file it must match exactly. Any drift means the bundle would ship different content from
what the repo itself runs — caught here rather than on a consumer's adoption run.

Also covers: every manifest artifact resolves to an actual file; workflow-caller stubs
render to valid YAML with the correct @vN ref; the starter config and AGENTS.md stub
are scoped for a generic consumer (no project-standards-specific paths or handoff content).
"""

from __future__ import annotations

import json
import re
import tomllib
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
        job = doc["jobs"][next(iter(doc["jobs"]))]
        uses = job["uses"]
        assert workflow in uses and uses.endswith(f"@{ref}")
        # "Pin BOTH refs": a caller that also passes standards-ref must keep it
        # equal to the uses: ref, or the installed validator + bundled schema
        # would come from a different major than the workflow definition. Guards
        # against a future bump that moves uses: but leaves standards-ref behind.
        if "standards-ref" in job.get("with", {}):
            assert job["with"]["standards-ref"] == ref


def test_generated_workflow_yaml_has_no_tabs() -> None:
    # check.yml (kind=file) ships verbatim; assert it is space-indented.
    assert "\t" not in (_BUNDLES / "python-tooling" / "check.yml").read_text()


_PY_TOOLING_DOC = _REPO / "standards" / "python-tooling" / "README.md"


def test_standard_doc_check_yml_block_matches_bundle() -> None:
    # The standard's §15 scaffold and the bundle's check.yml are two representations
    # of one artifact; manual copy-adopters use the doc block, the CLI ships the
    # bundle. They must stay byte-identical or the two adoption paths diverge
    # (2026-07-01: the doc block had drifted into tab-indented, unparseable YAML).
    doc = _PY_TOOLING_DOC.read_text()
    blocks = re.findall(r"```yaml\n(.*?)```", doc, re.DOTALL)
    assert len(blocks) == 1  # §15 is the document's only YAML fence
    block = blocks[0]
    assert block == (_BUNDLES / "python-tooling" / "check.yml").read_text()
    assert "\t" not in block  # YAML forbids tab indentation
    yaml.safe_load(block)
    # Guard the guard: without a bare prettier-ignore directly above the fence,
    # Prettier's embedded formatting rewrites the block's quote style on the next
    # --write and byte-equality with the bundle breaks.
    assert "<!-- prettier-ignore -->\n```yaml\n" in doc


def test_standard_doc_pyproject_block_matches_bundle_fragment() -> None:
    # §6's baseline and the CLI-reported fragment must agree semantically. The doc
    # block additionally carries an illustrative [project] table, so compare only
    # the tables the fragment defines (comments and formatting are free to differ).
    doc = _PY_TOOLING_DOC.read_text()
    blocks = re.findall(r"```toml\n(\[project\].*?)```", doc, re.DOTALL)
    assert len(blocks) == 1
    doc_toml = tomllib.loads(blocks[0])
    fragment = tomllib.loads(
        (_BUNDLES / "python-tooling" / "pyproject.python-tooling.toml").read_text()
    )
    for table, value in fragment.items():
        assert doc_toml[table] == value, table


def test_adopt_python_tooling_delivers_vscode_settings_and_tasks(tmp_path: Path) -> None:
    # §13 mandates all three .vscode files; before 2026-07-01 the CLI silently
    # delivered only extensions.json, leaving settings/tasks to manual copying.
    from project_standards.cli import main

    main(["adopt", "python-tooling", "--dest", str(tmp_path)])
    settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
    tasks = json.loads((tmp_path / ".vscode" / "tasks.json").read_text())
    assert settings["python.testing.pytestEnabled"] is True
    assert {t["label"] for t in tasks["tasks"]} >= {"check", "fix", "test", "typecheck", "audit"}
    assert (tmp_path / ".vscode" / "extensions.json").is_file()


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
