from __future__ import annotations

import random
import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import render_catalog, render_lock, semantic_digest
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
)
from tests.package_compatibility.matrix import catalog_default_ids
from tests.wheel_helpers import extract_pure_python_wheel

_ROOT = Path(__file__).resolve().parents[2]


def _cached_provider_runner() -> Callable[[ProviderInvocation], ProviderResult]:
    cache: dict[tuple[str, ...], ProviderResult] = {}

    def run(invocation: ProviderInvocation) -> ProviderResult:
        key = (
            invocation.standard_id,
            invocation.version.value,
            invocation.provider_id,
            invocation.operation.value,
            invocation.payload.integrity.aggregate_digest.value,
            semantic_digest(invocation.effective_config).value,
            semantic_digest(invocation.snapshots).value,
        )
        if key not in cache:
            cache[key] = invoke_provider(invocation)
        return cache[key]

    return run


def _permuted_request(
    base: PlannerRequest,
    randomizer: random.Random,
) -> PlannerRequest:
    desired_items = list(base.resolution.desired.standards.items())
    resolution_payloads = list(base.resolution.payloads)
    installed_payloads = list(base.payloads)
    for items in (
        desired_items,
        resolution_payloads,
        installed_payloads,
    ):
        randomizer.shuffle(items)
    resolution = replace(
        base.resolution,
        desired=base.resolution.desired.model_copy(update={"standards": dict(desired_items)}),
        payloads=tuple(resolution_payloads),
    )
    return replace(base, resolution=resolution, payloads=tuple(installed_payloads))


def _plan_evidence(plan: ReconciliationPlan, request: PlannerRequest) -> tuple[object, ...]:
    return (
        plan.applicable,
        plan.findings,
        plan.actions,
        plan.units,
        plan.verification_requests,
        plan.provider_notices,
        tuple(
            (standard_id, package.model_dump_json())
            for standard_id, package in sorted(request.resolution.desired.standards.items())
        ),
        render_catalog(request.resolution.catalog),
        render_lock(plan.next_lock),
        tuple((target.target, target.content, target.mode) for target in plan.targets),
    )


@pytest.mark.performance
def test_real_catalog_plans_inside_scale_and_time_boundary(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
) -> None:
    repo = tmp_path / "real-catalog"
    repo.mkdir()
    defaults = catalog_default_ids()
    initialize_control_plane(repo, "5", distribution=source_payload_distribution)
    for standard_id in defaults:
        set_standard_enabled(repo, standard_id, True)
    request = build_planner_request(repo, source_payload_distribution, frozenset())

    started = perf_counter()
    plan = plan_reconciliation(request)
    elapsed = perf_counter() - started

    assert plan.applicable, plan.findings
    assert len(plan.resolution.packages) == len(defaults) <= 100
    assert len(plan.units) <= 1_000
    assert elapsed < 5.0, f"real catalog planning took {elapsed:.3f}s"


@pytest.mark.performance
def test_one_hundred_requested_and_discovery_orders_are_byte_deterministic(
    tmp_path: Path,
    source_payload_distribution: InstalledDistribution,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=source_payload_distribution)
    for standard_id in reversed(catalog_default_ids()):
        set_standard_enabled(repo, standard_id, True)
    base = replace(
        build_planner_request(repo, source_payload_distribution, frozenset()),
        provider_runner=_cached_provider_runner(),
    )
    config_bytes = (repo / ".standards/config.toml").read_bytes()

    started = perf_counter()
    baseline_plan = plan_reconciliation(base)
    assert baseline_plan.applicable, baseline_plan.findings
    expected = _plan_evidence(baseline_plan, base)
    for seed in range(100):
        request = _permuted_request(base, random.Random(seed))
        plan = plan_reconciliation(request)
        assert _plan_evidence(plan, request) == expected

    result = apply_reconciliation(ApplyRequest(base, baseline_plan))
    assert result.success, result
    assert (repo / ".standards/config.toml").read_bytes() == config_bytes
    for target in baseline_plan.targets:
        assert (repo / target.target).read_bytes() == target.content
    elapsed = perf_counter() - started
    assert elapsed < 30.0, f"100-order compatibility sweep took {elapsed:.3f}s"


@pytest.mark.performance
def test_repeated_wheel_builds_extract_identical_catalogs(tmp_path: Path) -> None:
    catalog_bytes: list[bytes] = []
    started = perf_counter()
    for cycle in range(3):
        output = tmp_path / f"dist-{cycle}"
        subprocess.run(
            ["uv", "build", "--offline", "--wheel", "--out-dir", str(output)],
            cwd=_ROOT,
            check=True,
            capture_output=True,
        )
        (wheel,) = output.glob("*.whl")
        installed = tmp_path / f"installed-{cycle}"
        extract_pure_python_wheel(wheel, installed)
        distribution = InstalledDistribution(
            installed / "project_standards",
            tool_release="5.0.0",
        )
        distribution.load_catalog("5")
        catalog_bytes.append((installed / "project_standards/catalogs/5.toml").read_bytes())

    assert catalog_bytes[1:] == catalog_bytes[:-1]
    elapsed = perf_counter() - started
    assert elapsed < 30.0, f"three wheel build/extract cycles took {elapsed:.3f}s"
