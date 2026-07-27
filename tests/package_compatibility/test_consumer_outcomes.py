from __future__ import annotations

import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

import project_standards
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import (
    build_planner_request,
    validate_repository,
)
from project_standards.control_plane.cli import (
    run as run_reconcile,
)
from project_standards.control_plane.codec import parse_lock
from project_standards.control_plane.config_edit import (
    set_standard_enabled,
    set_standard_version,
)
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.package_contract.catalog import CatalogRole
from tests.issue_regressions.ledger import ConsumerOutcome, validate_baseline
from tests.issue_regressions.tool_oracle import (
    format_with_prettier,
    markdownlint_patterns,
    prettier_workflow,
)
from tests.package_compatibility.matrix import catalog_default_ids

pytestmark = pytest.mark.compatibility

_ROOT = Path(__file__).resolve().parents[2]
_BASELINE = validate_baseline(
    _ROOT / "tests/issue_regressions/baseline.toml",
    _ROOT,
)


def _active_distribution(
    source_payload_distribution: InstalledDistribution,
) -> InstalledDistribution:
    package_root = Path(project_standards.__file__).resolve().parent
    catalog_projection = package_root / "catalogs/5.toml"
    if catalog_projection.is_symlink() or not catalog_projection.is_file():
        package_root = source_payload_distribution.package_root
    return InstalledDistribution(
        package_root,
        tool_release=version("project-standards"),
    )


def _write_clean_consumer_seed(repo: Path) -> None:
    files = {
        "pyproject.toml": (
            '[project]\nname = "outcome-consumer"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n'
        ),
        "AGENTS.md": "# Consumer instructions\n\nPreserve this guidance.\n",
        "CLAUDE.md": "# Consumer instructions\n\nPreserve this guidance.\n",
        "docs/STATUS.md": "# Consumer status\n\nNo active incidents.\n",
        "docs/TODO.md": "# Consumer tasks\n\nNo queued work.\n",
    }
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _apply(repo: Path, distribution: InstalledDistribution) -> None:
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success, result


def _materialize_track(
    repo: Path,
    distribution: InstalledDistribution,
    authority: ConsumerOutcome,
    selector: str,
    expected: str,
) -> None:
    repo.mkdir()
    _write_clean_consumer_seed(repo)
    initialize_control_plane(repo, "5", distribution=distribution)
    for standard_id in catalog_default_ids():
        set_standard_enabled(repo, standard_id, True)
    set_standard_version(repo, authority.standard_id, selector)
    _apply(repo, distribution)

    format_with_prettier(
        _ROOT,
        repo,
        (".",),
        config_path=repo / ".prettierrc.json",
    )
    _apply(repo, distribution)

    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert lock.standards[authority.standard_id].resolved.value == expected


def _catalog_default_version(
    distribution: InstalledDistribution,
    standard_id: str,
) -> str:
    defaults = [
        entry.version.value
        for entry in distribution.load_catalog("5").source.packages
        if entry.id == standard_id and entry.role is CatalogRole.DEFAULT
    ]
    assert len(defaults) == 1
    return defaults[0]


def _caller_job(path: Path, name: str) -> dict[str, Any]:
    raw = cast("dict[Any, Any]", yaml.safe_load(path.read_text(encoding="utf-8")))
    return cast("dict[str, Any]", raw["jobs"][name])


def _status(returncode: int) -> str:
    return "passed" if returncode == 0 else "failed"


def _run_consumer_checks(
    repo: Path,
    distribution: InstalledDistribution,
) -> dict[str, str]:
    format_outcome = prettier_workflow(
        _ROOT,
        repo,
        repo / ".github/workflows/format.yml",
    )
    lint_job = _caller_job(
        repo / ".github/workflows/lint-markdown.yml",
        "lint-markdown",
    )
    lint_outcome = markdownlint_patterns(
        _ROOT,
        repo,
        tuple(cast("str", lint_job["with"]["globs"]).splitlines()),
        config_path=repo / ".markdownlint.json",
    )

    validate_code = validate_repository(repo, distribution=distribution)
    reconcile_code = run_reconcile(
        ["--repo", str(repo), "--check"],
        distribution=distribution,
    )

    workflow_job = _caller_job(
        repo / ".github/workflows/validate-standards.yml",
        "frontmatter",
    )
    expected_endpoint = (
        "L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v5"
    )
    environment = os.environ.copy()
    pythonpath = [str(distribution.package_root.parent)]
    if inherited := environment.get("PYTHONPATH"):
        pythonpath.append(inherited)
    environment["PYTHONPATH"] = os.pathsep.join(pythonpath)
    version_probe = subprocess.run(
        [sys.executable, "-m", "project_standards.cli", "--version"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    installed_validate = subprocess.run(
        [sys.executable, "-m", "project_standards.cli", "validate", "--quiet"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    installed_workflow_code = (
        0
        if workflow_job["uses"] == expected_endpoint
        and version_probe.returncode == 0
        and version_probe.stdout.strip() == f"project-standards {distribution.tool_release.value}"
        and installed_validate.returncode == 0
        else 1
    )

    return {
        "format": _status(format_outcome.returncode),
        "installed_workflow": _status(installed_workflow_code),
        "lint": _status(lint_outcome.returncode),
        "reconcile": _status(reconcile_code),
        "validate": _status(validate_code),
    }


@pytest.mark.parametrize(
    "authority",
    _BASELINE.consumer_outcomes,
    ids=lambda outcome: outcome.standard_id,
)
def test_consumer_outcomes__exact_and_default_tracks__match_baseline_authority(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
    authority: ConsumerOutcome,
) -> None:
    distribution = _active_distribution(source_payload_distribution)
    latest = _catalog_default_version(distribution, authority.standard_id)
    tracks = (
        ("exact", authority.predecessor, authority.predecessor, authority.exact_checks),
        ("latest", "latest", latest, authority.latest_checks),
    )

    for name, selector, expected, expected_checks in tracks:
        repo = tmp_path / name
        _materialize_track(
            repo,
            distribution,
            authority,
            selector,
            expected,
        )
        assert _run_consumer_checks(repo, distribution) == expected_checks
