from __future__ import annotations

import shutil
import subprocess
from itertools import combinations
from pathlib import Path
from typing import NoReturn

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import parse_lock
from project_standards.control_plane.config_edit import (
    set_standard_enabled,
    set_standard_version,
)
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import plan_legacy_migration
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.payload import (
    PayloadAvailability,
    load_payload_manifest,
)
from tests.package_compatibility.matrix import (
    LifecycleResult,
    catalog_default_ids,
    exercise_fresh_lifecycle,
    exercise_migrated_lifecycle,
    exercise_partial_migrated_lifecycle,
    partial_legacy_config,
)

pytestmark = pytest.mark.compatibility

_DEFAULTS = catalog_default_ids()
_PAIRS = tuple(combinations(_DEFAULTS, 2))
_PARTIAL_MIGRATION_ROWS = tuple((standard_id,) for standard_id in _DEFAULTS) + tuple(
    tuple(candidate for candidate in _DEFAULTS if candidate != omitted) for omitted in _DEFAULTS
)
_MANDATORY_GROUPS = (
    ("python-tooling", "agent-handoff", "markdown-tooling"),
    ("adr", "markdown-frontmatter"),
    ("project-spec", "markdown-frontmatter"),
)
_ROOT = Path(__file__).resolve().parents[2]
_ARTIFACT_STATES = _ROOT / "tests/fixtures/package_compatibility/legacy/artifact-states"
_ALL_NAMESPACES = (
    _ROOT / "tests/fixtures/package_compatibility/legacy/all-namespaces/.project-standards.yml"
)
_CORRECTION_TRANSITIONS = (
    ("agent-handoff", "1.3", "1.4"),
    ("markdown-tooling", "1.6", "1.7"),
    ("project-spec", "1.3", "1.4"),
    ("python-tooling", "1.6", "1.7"),
)


def _deny_child_process(*_args: object, **_kwargs: object) -> NoReturn:
    pytest.fail("package compatibility provider attempted a child process")


@pytest.fixture(autouse=True)
def deny_provider_child_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail correctness rows if packaged provider code tries to spawn a child."""
    monkeypatch.setattr(subprocess, "Popen", _deny_child_process)


def _assert_distribution_parity(source: LifecycleResult, wheel: LifecycleResult) -> None:
    assert wheel.actions == source.actions
    assert wheel.snapshot == source.snapshot


def _exercise_both(
    tmp_path: Path,
    source: InstalledDistribution,
    wheel: InstalledDistribution,
    standard_ids: tuple[str, ...],
    *,
    migrated: bool,
) -> None:
    exercise = exercise_migrated_lifecycle if migrated else exercise_fresh_lifecycle
    source_result = exercise(tmp_path / "source", source, standard_ids)
    wheel_result = exercise(tmp_path / "wheel", wheel, standard_ids)
    _assert_distribution_parity(source_result, wheel_result)


def _shared_surface_contributors(
    distribution: InstalledDistribution,
) -> tuple[str, ...]:
    catalog = distribution.load_catalog("5")
    return tuple(
        sorted(
            {
                payload.manifest.payload.standard
                for payload in catalog.payloads
                for contribution in payload.manifest.contributions
                if contribution.target.original == ".editorconfig"
                or contribution.target.original in {"AGENTS.md", "CLAUDE.md"}
                or contribution.target.original.startswith((".vscode/", ".github/workflows/"))
            }
        )
    )


def _consumer_family_ids() -> set[str]:
    result: set[str] = set()
    for family_path in sorted((_ROOT / "standards").glob("*/standard.toml")):
        family = load_family_manifest(family_path)
        latest = max(family.versions, key=lambda item: item.version.sort_key)
        payload = load_payload_manifest(family_path.parent / latest.payload.normalized)
        if payload.payload.availability is PayloadAvailability.CONSUMER:
            result.add(family.standard.id)
    return result


def test_consumer_default_matrix_is_derived_from_catalog_5() -> None:
    assert _DEFAULTS
    assert tuple(sorted(_DEFAULTS)) == _DEFAULTS
    assert {item for pair in _PAIRS for item in pair} == set(_DEFAULTS)
    assert set(_DEFAULTS) == _consumer_family_ids()


def _apply_exact_selection(
    repo: Path,
    distribution: InstalledDistribution,
) -> tuple[str, tuple[tuple[str, str, str], ...]]:
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success, result
    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    (standard_id,) = lock.standards
    mutations = tuple(
        (action.target, action.scope, action.kind.value)
        for action in plan.actions
        if action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
    )
    return lock.standards[standard_id].resolved.value, mutations


@pytest.mark.parametrize(
    ("standard_id", "predecessor", "successor"),
    _CORRECTION_TRANSITIONS,
)
def test_correction_predecessors_resolve_exactly_and_latest_transitions_converge(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
    standard_id: str,
    predecessor: str,
    successor: str,
) -> None:
    results: list[tuple[str, str, tuple[tuple[str, str, str], ...]]] = []
    for label, distribution in (
        ("source", source_payload_distribution),
        ("wheel", wheel_payload_distribution),
    ):
        repo = tmp_path / label
        repo.mkdir()
        initialize_control_plane(repo, "5", distribution=distribution)
        set_standard_enabled(repo, standard_id, True)
        set_standard_version(repo, standard_id, predecessor)
        exact, _initial_mutations = _apply_exact_selection(repo, distribution)

        set_standard_version(repo, standard_id, "latest")
        promoted, mutations = _apply_exact_selection(repo, distribution)
        request = build_planner_request(repo, distribution, frozenset())
        fixed = plan_reconciliation(request)

        assert exact == predecessor
        assert promoted == successor
        assert fixed.applicable, fixed.findings
        assert not any(
            action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
            for action in fixed.actions
        )
        results.append((exact, promoted, mutations))
    assert results[0] == results[1]


@pytest.mark.parametrize(
    "standard_ids",
    _PARTIAL_MIGRATION_ROWS,
    ids=lambda row: "+".join(row),
)
def test_legacy_migration__partial_namespaces__enables_only_selected_packages(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
    standard_ids: tuple[str, ...],
) -> None:
    source = exercise_partial_migrated_lifecycle(
        tmp_path / "source",
        source_payload_distribution,
        standard_ids,
    )
    wheel = exercise_partial_migrated_lifecycle(
        tmp_path / "wheel",
        wheel_payload_distribution,
        standard_ids,
    )

    _assert_distribution_parity(source, wheel)


def test_legacy_migration__present_non_mapping_namespace__fails_closed(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
) -> None:
    repo = tmp_path / "malformed-legacy"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        "standards_version: v4\nmarkdown:\n  adr: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ControlPlaneError, match="provider failed with ValueError"):
        plan_legacy_migration(repo, source_payload_distribution, "5")


def test_legacy_migration__unadopted_known_artifact__does_not_enroll_package(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
) -> None:
    repo = tmp_path / "unadopted-artifact"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        partial_legacy_config(("python-tooling",)),
        encoding="utf-8",
    )
    template = repo / "docs/adr/adr.template.md"
    template.parent.mkdir(parents=True)
    shutil.copyfile(_ROOT / "standards/adr/versions/1.2/templates/adr.md", template)

    plan = plan_legacy_migration(repo, source_payload_distribution, "5")

    assert tuple(report.package.standard_id for report in plan.reports) == ("python-tooling",)
    assert "adr" not in plan.desired_config.standards


@pytest.mark.parametrize("standard_id", _DEFAULTS)
def test_partial_legacy_migration__present_empty_namespace__adopts_defaults(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
    standard_id: str,
) -> None:
    source = exercise_partial_migrated_lifecycle(
        tmp_path / f"source-empty-{standard_id}",
        source_payload_distribution,
        (standard_id,),
        empty_namespaces=True,
    )
    wheel = exercise_partial_migrated_lifecycle(
        tmp_path / f"wheel-empty-{standard_id}",
        wheel_payload_distribution,
        (standard_id,),
        empty_namespaces=True,
    )

    _assert_distribution_parity(source, wheel)


def test_partial_legacy_migration__unknown_only_namespace__remains_unclaimed(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
) -> None:
    repo = tmp_path / "unknown-only-legacy"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        "standards_version: v4\npython_tooling:\n  typo: true\n",
        encoding="utf-8",
    )

    plan = plan_legacy_migration(repo, source_payload_distribution, "5")

    assert not plan.applicable
    assert any(
        finding.code == "CP-MIGRATION-UNCLAIMED-SETTING"
        and finding.identity == "/python_tooling/typo"
        for finding in plan.findings
    )


@pytest.mark.parametrize("standard_id", _DEFAULTS)
def test_each_package_converges_alone_from_source_and_wheel(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
    standard_id: str,
) -> None:
    _exercise_both(
        tmp_path,
        source_payload_distribution,
        wheel_payload_distribution,
        (standard_id,),
        migrated=False,
    )


@pytest.mark.parametrize("standard_ids", _PAIRS)
@pytest.mark.parametrize("migrated", [False, True], ids=["fresh", "migrated"])
def test_every_unordered_pair_preserves_ownership_and_converges(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
    standard_ids: tuple[str, str],
    *,
    migrated: bool,
) -> None:
    _exercise_both(
        tmp_path,
        source_payload_distribution,
        wheel_payload_distribution,
        standard_ids,
        migrated=migrated,
    )


@pytest.mark.parametrize("migrated", [False, True], ids=["fresh", "all-namespace-legacy"])
def test_full_supported_set_converges_from_source_and_wheel(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
    *,
    migrated: bool,
) -> None:
    _exercise_both(
        tmp_path,
        source_payload_distribution,
        wheel_payload_distribution,
        _DEFAULTS,
        migrated=migrated,
    )


def test_mandatory_interaction_groups_are_explicitly_covered(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
) -> None:
    for index, standard_ids in enumerate(_MANDATORY_GROUPS):
        assert set(standard_ids) <= set(_DEFAULTS)
        _exercise_both(
            tmp_path / str(index),
            source_payload_distribution,
            wheel_payload_distribution,
            standard_ids,
            migrated=False,
        )
    contributors = _shared_surface_contributors(source_payload_distribution)
    assert contributors
    _exercise_both(
        tmp_path / "catalog-shared-surfaces",
        source_payload_distribution,
        wheel_payload_distribution,
        contributors,
        migrated=False,
    )


def test_every_shared_surface_contributor_is_in_the_full_matrix(
    source_payload_distribution: InstalledDistribution,
) -> None:
    contributors = set(_shared_surface_contributors(source_payload_distribution))

    assert contributors
    assert contributors <= set(_DEFAULTS)


def test_real_catalog_remains_inside_planning_scale_boundary(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
) -> None:
    repo = tmp_path / "real-catalog"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=source_payload_distribution)
    for standard_id in _DEFAULTS:
        set_standard_enabled(repo, standard_id, True)
    plan = plan_reconciliation(
        build_planner_request(repo, source_payload_distribution, frozenset())
    )

    assert plan.applicable, plan.findings
    assert len(plan.resolution.packages) == len(_DEFAULTS) <= 100
    assert len(plan.units) <= 1_000


def test_modified_artifact_state_fixture_is_fail_closed_without_writes(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
) -> None:
    repo = tmp_path / "artifact-states"
    shutil.copytree(_ARTIFACT_STATES, repo)
    shutil.copyfile(_ALL_NAMESPACES, repo / ".project-standards.yml")
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }

    plan = plan_legacy_migration(repo, source_payload_distribution, "5")

    assert not plan.applicable
    assert {finding.code for finding in plan.findings} >= {
        "AH-LEGACY-MODIFIED",
        "CP-MIGRATION-LEGACY-DIGEST",
    }
    assert not (repo / ".standards").exists()
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before
