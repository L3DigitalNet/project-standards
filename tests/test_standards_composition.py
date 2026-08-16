"""Dogfood the artifact plane across every declared standard combination."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

from project_standards.adopt.engine import build_plan, execute_plan
from project_standards.adopt.manifest import available_standards
from project_standards.package_contract.catalog import CatalogRole
from project_standards.package_contract.repository import build_package_repository

_REPO = Path(__file__).resolve().parent.parent

# Advertised catalog-5 defaults the legacy adopt engine deliberately does not serve: they
# ship no `src/project_standards/bundles/<id>/` tree and are adopted through the control
# plane instead (spec WH-003 defers any legacy migration; a duplicate legacy bundle would
# be a hand-maintained drift surface inside a retiring mechanism). The classification is an
# asserted set rather than a silent filter, so a newly advertised family that has neither a
# bundle nor an entry here fails this module until it is consciously classified.
_CATALOG_NATIVE_FAMILIES = {"github-workflow", "project-toolbox"}


def _catalog_default_ids() -> list[str]:
    repository = build_package_repository(_REPO, catalog_major=5)
    assert repository.findings == ()
    assert repository.catalog is not None
    return [entry.id for entry in repository.catalog.packages if entry.role is CatalogRole.DEFAULT]


def _adoptable_standard_ids() -> list[str]:
    """Catalog-5 defaults the legacy adopt engine can plan, in catalog order."""
    catalog_defaults = _catalog_default_ids()
    legacy_served = set(available_standards())

    assert set(catalog_defaults) - legacy_served == _CATALOG_NATIVE_FAMILIES
    return [standard_id for standard_id in catalog_defaults if standard_id in legacy_served]


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
    # Declared conflicts live in the payload manifests, not the legacy bundles, so this stays
    # over every advertised default — catalog-native families ship payloads and must be checked.
    repository = build_package_repository(_REPO, catalog_major=5)
    artifact_ids = set(_catalog_default_ids())

    assert not {
        (payload.manifest.payload.standard, target)
        for payload in repository.payloads
        if payload.manifest.payload.standard in artifact_ids
        for target in payload.manifest.relations.conflicts
        if target in artifact_ids
    }
