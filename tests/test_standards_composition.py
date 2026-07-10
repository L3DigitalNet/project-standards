"""Dogfood the artifact plane across every declared standard combination."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

from project_standards.adopt.engine import build_plan, execute_plan
from project_standards.standard_manifest import AdoptionMode
from project_standards.standards_graph.discovery import build_graph

_REPO = Path(__file__).resolve().parent.parent


def _adoptable_standard_ids() -> list[str]:
    graph = build_graph(_REPO)
    adoptable_modes = {AdoptionMode.VALIDATOR, AdoptionMode.COPY_ADOPT, AdoptionMode.CLI}
    nodes = [node for node in graph.standards if node.manifest.standard.adoption in adoptable_modes]
    assert all(node.artifact_manifest is not None for node in nodes)
    return [node.standard_id for node in nodes]


def test_each_artifact_standard_builds_an_independent_plan() -> None:
    standard_ids = _adoptable_standard_ids()

    assert standard_ids
    assert "agent-handoff" in standard_ids
    for standard_id in standard_ids:
        assert build_plan([standard_id]), standard_id


def test_every_artifact_standard_pair_builds_without_destination_conflict() -> None:
    standard_ids = _adoptable_standard_ids()

    agent_handoff_pairs = [
        pair for pair in combinations(standard_ids, 2) if "agent-handoff" in pair
    ]
    assert agent_handoff_pairs
    for pair in combinations(standard_ids, 2):
        assert build_plan(list(pair)), pair


def test_all_artifact_standards_build_and_execute_together(tmp_path: Path) -> None:
    standard_ids = _adoptable_standard_ids()
    plan = build_plan(standard_ids)

    report = execute_plan(plan, tmp_path, force=False, dry_run=False)

    assert report.created
    assert ".editorconfig" in report.created
    assert report.fragments[".project-standards.yml"]
    assert report.fragments["pyproject.toml"]
    assert not (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / ".agents/skills/markdown-frontmatter/SKILL.md").is_file()


def test_all_standard_plan_deduplicates_shared_artifacts() -> None:
    plan = build_plan(_adoptable_standard_ids())

    editorconfig = [action for action in plan if action.dest == ".editorconfig"]
    extensions = [action for action in plan if action.dest == ".vscode/extensions.json"]
    assert len(editorconfig) == 1
    assert len(extensions) == 1
    assert set(editorconfig[0].standards) == {"markdown-tooling", "python-tooling"}
    assert set(extensions[0].standards) == {"markdown-tooling", "python-tooling"}


def test_successful_dogfood_profile_has_no_declared_conflicts() -> None:
    graph = build_graph(_REPO)
    artifact_ids = set(_adoptable_standard_ids())

    assert not {
        (node.standard_id, target)
        for node in graph.standards
        if node.standard_id in artifact_ids
        for target in node.manifest.relations.conflicts
        if target in artifact_ids
    }
