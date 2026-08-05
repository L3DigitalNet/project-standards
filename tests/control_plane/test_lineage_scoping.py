"""Scope the catalog release-lineage assertion to catalog-advancing invocations.

Issue #123 (TC-T39-001): a producing repository normally spends a whole release
train with an installed catalog that carries payloads its committed
``.standards/catalog.toml`` does not, at an unchanged tool release. That state is
a refusal only for an invocation that would publish the installed catalog into
the repository; every other command decides nothing about lineage and must answer
from the installed catalog instead.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.catalog_refresh import (
    CatalogAdvance,
    plan_catalog_refresh,
)
from project_standards.control_plane.cli import build_planner_request, run, validate_repository
from project_standards.control_plane.command_resolution import selected_command
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.locking import LockMode
from project_standards.control_plane.state import detect_control_plane_state
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.helpers import installed_distribution

_LINEAGE_REFUSAL = "catalog changed but its tool release did not advance"


def _mid_cycle_distribution(tmp_path: Path, base: InstalledDistribution) -> InstalledDistribution:
    """Stage the authoring state issue #123 describes: a new payload, same release.

    Mirrors the released-catalog fixture used by ``test_catalog_refresh`` except
    that the tool release deliberately does *not* advance, which is exactly the
    window between two release trains.
    """
    repository = tmp_path / "repository"
    source = repository / "standards/alpha/versions/2.0"
    target = repository / "standards/alpha/versions/2.1"
    shutil.copytree(source, target)
    payload_path = target / "payload.toml"
    payload_text = payload_path.read_text(encoding="utf-8").replace(
        'version = "2.0"',
        'version = "2.1"',
        1,
    )
    zeta = b"alpha 2.1 staged artifact\n"
    (target / "zeta.txt").write_bytes(zeta)
    zeta_digest = f"sha256:{hashlib.sha256(zeta).hexdigest()}"
    payload_path.write_text(
        payload_text.replace('to = "package:2.0"', 'to = "package:2.1"')
        + (
            '\n[[artifacts]]\nid = "zeta"\ntarget = "zeta.txt"\n'
            f'source = "zeta.txt"\ndigest = "{zeta_digest}"\n'
            'policy = "managed"\nmode = "0644"\n'
        ),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    digest = validate_payload_integrity(target, manifest).aggregate_digest.value
    family_path = repository / "standards/alpha/standard.toml"
    family_path.write_text(
        family_path.read_text(encoding="utf-8")
        + (
            '\n[[versions]]\nversion = "2.1"\n'
            'payload = "versions/2.1/payload.toml"\n'
            f'digest = "{digest}"\n'
        ),
        encoding="utf-8",
    )
    catalog_path = repository / "catalogs/5.toml"
    catalog_text = catalog_path.read_text(encoding="utf-8").replace(
        'version = "2.0"\n'
        'digest = "sha256:c1666aee5b8d0bbf35bf771c4539012a1c5c7fbd3f5aeb5d99bc7f0ba18b69e9"\n'
        'role = "default"',
        'version = "2.0"\n'
        'digest = "sha256:c1666aee5b8d0bbf35bf771c4539012a1c5c7fbd3f5aeb5d99bc7f0ba18b69e9"\n'
        'role = "retained"',
        1,
    )
    catalog_path.write_text(
        catalog_text
        + (
            '\n[[packages]]\nid = "alpha"\nversion = "2.1"\n'
            f'digest = "{digest}"\nrole = "default"\n'
        ),
        encoding="utf-8",
    )
    assert sync_payload_projection(repository, check=False) == ()
    installed = tmp_path / "installed-mid-cycle/project_standards"
    shutil.copytree(repository / "src/project_standards", installed)
    return InstalledDistribution(installed, tool_release=base.tool_release.value)


def _reconciled_consumer(tmp_path: Path) -> tuple[Path, InstalledDistribution]:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    set_standard_enabled(repo, "alpha", True)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    assert run(["--repo", str(repo), "--apply"], distribution=base) == 0
    return repo, base


def test_mid_cycle_fixture_holds_an_equal_release_catalog_delta(tmp_path: Path) -> None:
    """Lock the fixture's premise so a later failure cannot be misread as staleness."""
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)
    state = detect_control_plane_state(repo, tool_release=mid_cycle.tool_release.value)

    assert state.catalog is not None
    installed = mid_cycle.consumer_catalog("5")
    assert installed.project_standards.release == state.catalog.project_standards.release
    assert installed != state.catalog


def test_read_only_planner_request_answers_from_the_installed_catalog(tmp_path: Path) -> None:
    """The shared boundary behind every read-only command must not assert lineage."""
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)

    planner = build_planner_request(repo, mid_cycle, frozenset())

    assert planner.catalog_refresh is not None
    assert planner.catalog_refresh.changed


def test_selected_command_resolves_a_package_mid_cycle(tmp_path: Path) -> None:
    """Cover the route `agent-handoff`, `validate-frontmatter`, and `validate-id` take."""
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)

    with selected_command(
        repo,
        "alpha",
        mid_cycle,
        mode=LockMode.READ,
        require_reconciled=False,
    ) as selected:
        assert selected is not None


def test_repository_validation_reports_drift_instead_of_refusing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)

    status = validate_repository(repo, distribution=mid_cycle)

    assert status == 1
    assert _LINEAGE_REFUSAL not in capsys.readouterr().err


def test_reconcile_preview_modes_report_findings(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)

    for arguments in (["--repo", str(repo)], ["--repo", str(repo), "--check"]):
        assert run(arguments, distribution=mid_cycle) == 1
        assert _LINEAGE_REFUSAL not in capsys.readouterr().err


def test_apply_still_refuses_with_the_unchanged_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)
    catalog = (repo / ".standards/catalog.toml").read_bytes()
    lock = (repo / ".standards/lock.toml").read_bytes()

    assert run(["--repo", str(repo), "--apply"], distribution=mid_cycle) == 2

    assert _LINEAGE_REFUSAL in capsys.readouterr().err
    assert (repo / ".standards/catalog.toml").read_bytes() == catalog
    assert (repo / ".standards/lock.toml").read_bytes() == lock


def test_refusal_and_clean_result_stay_distinguishable_by_exit_status(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)

    assert run(["--repo", str(repo), "--check"], distribution=base) == 0
    capsys.readouterr()
    assert run(["--repo", str(repo), "--check"], distribution=mid_cycle) == 1
    capsys.readouterr()
    assert run(["--repo", str(repo), "--apply"], distribution=mid_cycle) == 2
    capsys.readouterr()


def test_lineage_assertion_is_selected_by_the_advance_classification(tmp_path: Path) -> None:
    """The rule itself is unchanged; only the invocations that consult it are."""
    repo, base = _reconciled_consumer(tmp_path)
    mid_cycle = _mid_cycle_distribution(tmp_path, base)
    state = detect_control_plane_state(repo, tool_release=mid_cycle.tool_release.value)
    assert state.catalog is not None
    assert state.config is not None
    assert state.lock is not None
    installed = mid_cycle.consumer_catalog("5")

    with pytest.raises(ControlPlaneError, match=_LINEAGE_REFUSAL):
        plan_catalog_refresh(
            state.catalog,
            installed,
            state.config,
            state.lock,
            advance=CatalogAdvance.ADVANCING,
        )

    plan = plan_catalog_refresh(
        state.catalog,
        installed,
        state.config,
        state.lock,
        advance=CatalogAdvance.NON_ADVANCING,
    )

    assert plan.changed
