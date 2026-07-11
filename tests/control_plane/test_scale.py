from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pytest

from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from tests.control_plane.planner_helpers import resolution_request, write_payload


@pytest.mark.performance
def test_plans_one_hundred_packages_and_one_thousand_artifacts_under_five_seconds(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payloads = tuple(
        write_payload(
            tmp_path / standard_id,
            standard_id,
            artifacts=[
                {
                    "id": f"artifact-{artifact:02d}",
                    "target": f"generated/{standard_id}/{artifact:02d}.txt",
                    "content": f"{standard_id}:{artifact}\n".encode(),
                }
                for artifact in range(10)
            ],
        )
        for standard_id in (f"scale-{index:03d}" for index in range(100))
    )
    request = PlannerRequest(repo, resolution_request(payloads), payloads)

    started = perf_counter()
    plan = plan_reconciliation(request)
    elapsed = perf_counter() - started

    assert plan.applicable
    assert len(plan.targets) == 1_000
    assert elapsed < 5.0, f"planning took {elapsed:.3f}s"
