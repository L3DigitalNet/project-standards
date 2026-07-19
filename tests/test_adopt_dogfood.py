"""Dogfood tests: current bundle files must match their adopted counterparts.

The _DOGFOOD dict maps each bundle artifact that this repo self-adopts to the working-copy
file it must match exactly. Frozen legacy bundle bytes are validated separately because
the repo root and current V2 packages legitimately advance beyond those old artifacts.

Also covers: every manifest artifact resolves to an actual file; workflow-caller stubs
render to valid YAML with the correct @vN ref; the starter config and AGENTS.md stub
are scoped for a generic consumer (no project-standards-specific paths or handoff content).
"""

from __future__ import annotations

import json
import re
import shutil
import stat
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from project_standards._version import package_version
from project_standards.adopt.engine import major_ref, resolve_source
from project_standards.adopt.manifest import available_standards, load_manifest
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.planner import plan_reconciliation

_REPO = Path(__file__).resolve().parent.parent
_BUNDLES = _REPO / "src" / "project_standards" / "bundles"
FROZEN_V1_CHECK_DIGEST = "2dd6b7c11db910458add9696ade9b37c9f5ae4e23004da5333b52e3669bd15e5"


@pytest.fixture(autouse=True)
def use_legacy_adopt_route(monkeypatch: pytest.MonkeyPatch) -> None:
    def legacy_route(
        _standards: list[str],
        _dest: Path,
        *,
        force: bool,
        dry_run: bool,
        unsupported_options: bool = False,
    ) -> None:
        del force, dry_run, unsupported_options

    monkeypatch.setattr("project_standards.cli._try_v5_adopt", legacy_route)


# Bundle source file -> repo root working file it must stay byte-identical to.
_DOGFOOD = {
    "_shared/editorconfig": ".editorconfig",
    "_shared/vscode-extensions.json": ".vscode/extensions.json",
    "markdown-tooling/markdownlint.json": ".markdownlint.json",
    "markdown-tooling/prettierrc.json": ".prettierrc.json",
    # ADR bundle template ↔ its canonical copy under standards/ (guards silent drift —
    # the project-spec templates have the analogous guard in test_spec_packaging.py).
    "adr/adr.template.md": "standards/adr/templates/adr.md",
    "cli-documentation/usage-doc.md": "standards/cli-documentation/templates/usage-doc.md",
    "cli-documentation/cli-docs-check.yml": "standards/cli-documentation/templates/cli-docs-check.yml",
    "markdown-frontmatter/skills/markdown-frontmatter/SKILL.md": (
        "standards/markdown-frontmatter/skills/markdown-frontmatter/SKILL.md"
    ),
    "markdown-frontmatter/skills/markdown-frontmatter/agents/openai.yaml": (
        "standards/markdown-frontmatter/skills/markdown-frontmatter/agents/openai.yaml"
    ),
    "markdown-frontmatter/skills/markdown-frontmatter/scripts/new-doc-id": (
        "standards/markdown-frontmatter/skills/markdown-frontmatter/scripts/new-doc-id"
    ),
    "agent-handoff/hooks/session-start/session_start.py": (
        "standards/agent-handoff/hooks/session-start/session_start.py"
    ),
    "agent-handoff/skills/agent-handoff/SKILL.md": (
        "standards/agent-handoff/skills/agent-handoff/SKILL.md"
    ),
    "agent-handoff/skills/agent-handoff/agents/openai.yaml": (
        "standards/agent-handoff/skills/agent-handoff/agents/openai.yaml"
    ),
}


def test_dogfoodable_templates_match_repo_root_byte_for_byte() -> None:
    for bundle_rel, root_rel in _DOGFOOD.items():
        assert (_BUNDLES / bundle_rel).read_bytes() == (_REPO / root_rel).read_bytes(), bundle_rel


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_frozen_v1_python_check_bundle_digest() -> None:
    assert _sha256(_BUNDLES / "python-tooling/check.py") == FROZEN_V1_CHECK_DIGEST


def test_root_check_script_matches_current_v2_rendering(tmp_path: Path) -> None:
    installed = tmp_path / "project_standards"
    shutil.copytree(
        _REPO / "src/project_standards",
        installed,
        symlinks=False,
    )
    distribution = InstalledDistribution(
        installed,
        tool_release=package_version(),
    )
    request = build_planner_request(_REPO, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert (_REPO / "scripts/check.py").read_bytes() == plan.proposed_content("scripts/check.py")


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
        "markdown-tooling/format.caller.yml": "format.yml",
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


@pytest.mark.parametrize(
    "standard_id,version",
    [("markdown-frontmatter", "1.3"), ("adr", "1.1"), ("project-spec", "1.2")],
)
def test_current_adoption_guides_use_v5_packages_not_v1_fragments(
    standard_id: str,
    version: str,
) -> None:
    doc = (_REPO / "standards" / standard_id / "adopt.md").read_text()
    assert f"versions/{version}/adopt.md" in doc
    assert "project-standards init --catalog 5 --migrate" in doc
    assert "```yaml" not in doc


def test_no_yaml_fence_in_standards_docs_contains_tabs() -> None:
    # YAML forbids tab indentation; a tab-indented scaffold fence ships a broken
    # artifact to manual copy-adopters (python-tooling §15 did exactly that until
    # 2026-07-01). Keep the check even though EditorConfig now gives Markdown a
    # space override: copied or generated fences can still carry literal tabs.
    for md in (_REPO / "standards").rglob("*.md"):
        for block in re.findall(r"```ya?ml\n(.*?)```", md.read_text(), re.DOTALL):
            assert "\t" not in block, md


def test_doc_workflow_snippets_reference_current_major() -> None:
    # Partial `jobs:` snippets stay Prettier-managed (they are examples, not
    # byte-locked artifacts); guard the load-bearing parts — every `uses:` of this
    # repo's reusable workflows must name a workflow that exists, at the current major.
    ref = major_ref()
    workflows = {p.name for p in (_REPO / ".github" / "workflows").glob("*.yml")}
    pat = re.compile(
        r"uses: L3DigitalNet/project-standards/\.github/workflows/([\w.-]+\.yml)@(\S+)"
    )
    for md in (_REPO / "standards").rglob("*.md"):
        for workflow, used_ref in pat.findall(md.read_text()):
            assert workflow in workflows, f"{md}: {workflow}"
            assert used_ref == ref, f"{md}: {workflow}@{used_ref}"


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


def test_adopt_markdown_frontmatter_delivers_repo_local_skill(tmp_path: Path) -> None:
    from project_standards.cli import main

    main(["adopt", "markdown-frontmatter", "--dest", str(tmp_path)])
    skill_root = tmp_path / ".agents" / "skills" / "markdown-frontmatter"
    assert (skill_root / "SKILL.md").is_file()
    assert (skill_root / "agents" / "openai.yaml").is_file()
    script = skill_root / "scripts" / "new-doc-id"
    assert script.is_file()
    assert stat.S_IMODE(script.stat().st_mode) & stat.S_IXUSR
    result = subprocess.run(
        [
            str(script),
            "--doc-type",
            "runbook",
            "--status",
            "draft",
            "Router Upgrade",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert re.fullmatch(r"runbook-[0-9a-z]{6}-router-upgrade", result.stdout.strip())


def test_adopt_project_spec_reports_config_fragment_and_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from project_standards.cli import main

    assert main(["adopt", "project-spec", "--dest", str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert "Add these sections to `.project-standards.yml`:" in captured.out
    assert "spec:" in captured.out
    assert 'version: "1.0"' in captured.out
    assert "docs/specs/**/*.md" in captured.out
    workflow = tmp_path / ".github" / "workflows" / "validate-specs.yml"
    assert workflow.is_file()
    doc = yaml.safe_load(workflow.read_text())
    job = doc["jobs"]["validate-specs"]
    assert job["uses"].endswith(f"validate-specs.yml@{major_ref()}")
    assert job["with"]["standards-ref"] == major_ref()
    assert not (tmp_path / "docs" / "specs").exists()


def test_markdown_frontmatter_skill_script_mode_is_manifest_explicit() -> None:
    manifest = load_manifest("markdown-frontmatter")
    script = next(
        a
        for a in manifest.artifacts
        if a.dest == ".agents/skills/markdown-frontmatter/scripts/new-doc-id"
    )
    assert script.mode == 0o755


def test_agent_stub_is_generic_no_handoff_content(tmp_path: Path) -> None:
    from project_standards.cli import main

    main(["adopt", "python-tooling", "--dest", str(tmp_path)])
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "Python Tooling SSOT" in agents
    assert "docs/handoff" not in agents and "project-standards" not in agents.lower()
