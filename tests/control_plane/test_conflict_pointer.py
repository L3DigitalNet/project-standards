"""Whole-file conflict first-difference pointer (5.8.0 FR-012 / SPEC-CP01).

Guards the confidentiality contract: a whole-file ``CP-CONSUMER-CONFLICT`` on a
text target must point at the first differing line and quote the EXPECTED
(package-side, public) line only. Consumer bytes may hold secrets and must never
reach any rendered or serialized output.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from project_standards.control_plane.cli import (
    _format_human_finding,  # pyright: ignore[reportPrivateUsage]  # focused rendering boundary
)
from project_standards.control_plane.diagnostics import (
    ControlFinding,
    findings_to_jsonable,
)
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from tests.control_plane.planner_helpers import resolution_request, write_payload

_CANARY = "SUPER-SECRET-CONSUMER-TOKEN-9f3ab7"


def _request(repo: Path, payloads: Sequence[InstalledPayload]) -> PlannerRequest:
    resolution = resolution_request(payloads)
    return PlannerRequest(
        repo=repo,
        resolution=replace(resolution),
        payloads=tuple(payloads),
    )


def _consumer_conflict(plan: ReconciliationPlan) -> ControlFinding:
    return next(finding for finding in plan.findings if finding.code == "CP-CONSUMER-CONFLICT")


def _whole_file_conflict_plan(
    tmp_path: Path,
    *,
    package: bytes,
    consumer: bytes,
) -> ReconciliationPlan:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tool.txt").write_bytes(consumer)
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[{"id": "tool", "target": "tool.txt", "content": package}],
    )
    return plan_reconciliation(_request(repo, (payload,)))


def test_tc_t6_001_whole_file_text_conflict_points_at_first_differing_line(
    tmp_path: Path,
) -> None:
    plan = _whole_file_conflict_plan(
        tmp_path,
        package=b"alpha\nBEETLE\ngamma\n",
        consumer=b"alpha\ndelta\ngamma\n",
    )
    finding = _consumer_conflict(plan)

    assert finding.first_difference_line == 2
    assert finding.first_difference_expected == "BEETLE"

    rendered = _format_human_finding(finding)
    lines = rendered.splitlines()
    assert "  first difference: line 2" in lines
    assert "  expected: BEETLE" in lines

    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )
    assert jsonable["first_difference_line"] == 2
    assert jsonable["first_difference_expected"] == "BEETLE"


def test_tc_t6_002_consumer_secret_never_appears_in_rendered_or_serialized_output(
    tmp_path: Path,
) -> None:
    plan = _whole_file_conflict_plan(
        tmp_path,
        package=b"alpha\nBEETLE\ngamma\n",
        consumer=f"alpha\n{_CANARY}\ngamma\n".encode(),
    )
    finding = _consumer_conflict(plan)

    rendered = _format_human_finding(finding)
    assert _CANARY not in rendered

    serialized = repr(findings_to_jsonable(plan.findings))
    assert _CANARY not in serialized
    # The actual/consumer digest is allowed (it is a hash, not the bytes); the
    # plaintext canary must be absent everywhere the finding surfaces.
    assert finding.first_difference_expected is not None
    assert _CANARY not in finding.first_difference_expected


def test_tc_t6_003_binary_or_undecodable_target_keeps_digest_only_rendering(
    tmp_path: Path,
) -> None:
    # An invalid UTF-8 byte on either side must suppress the pointer entirely so
    # rendering falls back to the digest-only shape.
    plan = _whole_file_conflict_plan(
        tmp_path,
        package=b"\xff\xfe\x00\x01package-blob",
        consumer=b"\xff\xfe\x00\x02consumer-blob",
    )
    finding = _consumer_conflict(plan)

    assert finding.first_difference_line is None
    assert finding.first_difference_expected is None

    lines = _format_human_finding(finding).splitlines()
    assert any(line.startswith("  expected digest: ") for line in lines)
    assert any(line.startswith("  actual digest: ") for line in lines)
    assert not any(line.startswith("  first difference: ") for line in lines)

    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )
    assert "first_difference_line" not in jsonable
    assert "first_difference_expected" not in jsonable


def test_tc_t6_004_overlong_expected_line_truncates_with_marker_everywhere(
    tmp_path: Path,
) -> None:
    long_expected = "X" * 200
    plan = _whole_file_conflict_plan(
        tmp_path,
        package=f"{long_expected}\n".encode(),
        consumer=b"short\n",
    )
    finding = _consumer_conflict(plan)

    expected_excerpt = "X" * 120 + "…"
    assert finding.first_difference_line == 1
    assert finding.first_difference_expected == expected_excerpt
    assert finding.first_difference_expected is not None
    # 120 code points plus the single-char truncation marker.
    assert len(finding.first_difference_expected) == 121

    rendered = _format_human_finding(finding)
    assert f"  expected: {expected_excerpt}" in rendered.splitlines()
    assert long_expected not in rendered

    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )
    assert jsonable["first_difference_expected"] == expected_excerpt
