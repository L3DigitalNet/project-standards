"""Ownership-sensitive guidance for pre-adoption reconciliation conflicts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

import pytest

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
from project_standards.package_contract.payload import JsonValue
from tests.control_plane.planner_helpers import (
    ContributionFixture,
    resolution_request,
    write_payload,
)

_CANARY = "SUPER-SECRET-CONSUMER-GUIDANCE-TOKEN"


def _request(
    repo: Path,
    payloads: Sequence[InstalledPayload],
    *,
    configs: Mapping[str, Mapping[str, JsonValue]] | None = None,
) -> PlannerRequest:
    return PlannerRequest(
        repo=repo,
        resolution=replace(resolution_request(payloads, configs=configs)),
        payloads=tuple(payloads),
    )


def _consumer_conflict(plan: ReconciliationPlan) -> ControlFinding:
    return next(finding for finding in plan.findings if finding.code == "CP-CONSUMER-CONFLICT")


def _ownership_payload(root: Path) -> InstalledPayload:
    return write_payload(
        root,
        "demo",
        contributions=[
            {
                "id": "script",
                "target": "scripts/check.py",
                "adapter": "whole-file",
                "scope": "$file",
                "content": b"package\n",
                "when_any": [{"option": "script_ownership", "equals": "managed"}],
            }
        ],
        option_properties={
            "script_ownership": {
                "enum": ["managed", "consumer-owned"],
                "default": "managed",
            }
        },
    )


def test_pre_adoption_whole_file__managed_selector__permits_delete_and_reconcile(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts/check.py").write_text("consumer\n", encoding="utf-8")
    payload = _ownership_payload(tmp_path / "payload")

    finding = _consumer_conflict(
        plan_reconciliation(
            _request(
                repo,
                (payload,),
                configs={"demo": {"script_ownership": "managed"}},
            )
        )
    )

    assert "ownership class: pre-adoption exclusive whole-file target" in finding.hint
    assert "deleting scripts/check.py is permitted" in finding.hint
    assert "rm -- scripts/check.py && project-standards reconcile --apply" in finding.hint
    assert 'script_ownership = "managed"' in finding.hint


def test_pre_adoption_whole_artifact__without_selector__does_not_invent_option(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tool.txt").write_text("consumer\n", encoding="utf-8")
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[{"id": "tool", "target": "tool.txt", "content": b"package\n"}],
    )

    finding = _consumer_conflict(plan_reconciliation(_request(repo, (payload,))))

    assert "ownership class: pre-adoption exclusive whole-file target" in finding.hint
    assert "deleting tool.txt is permitted" in finding.hint
    assert "rm -- tool.txt && project-standards reconcile --apply" in finding.hint
    assert "ownership option" not in finding.hint


@pytest.mark.parametrize(
    "shared",
    [
        pytest.param(False, id="partial"),
        pytest.param(True, id="shared"),
    ],
)
def test_nonexclusive_semantic_conflict__delete_container__is_not_authorized(
    tmp_path: Path,
    *,
    shared: bool,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "settings.toml").write_text("[tool.demo]\nvalue = 2\n", encoding="utf-8")
    contribution: ContributionFixture = {
        "id": "value",
        "target": "settings.toml",
        "adapter": "toml",
        "scope": "key:/tool/demo/value",
        "content": b"[tool.demo]\nvalue = 1\n",
    }
    if shared:
        contribution["shared_identity"] = "tool-demo-value"
    alpha = write_payload(tmp_path / "alpha", "alpha", contributions=[contribution])
    payloads = (alpha,)
    if shared:
        beta = write_payload(tmp_path / "beta", "beta", contributions=[contribution])
        payloads = (alpha, beta)

    finding = _consumer_conflict(plan_reconciliation(_request(repo, payloads)))

    ownership_class = "shared semantic unit" if shared else "partial semantic unit"
    assert f"ownership class: {ownership_class}" in finding.hint
    assert "deleting settings.toml is not authorized" in finding.hint
    assert "consumer-owned or separately managed content" in finding.hint


def test_consumer_owned_whole_file__not_materialized__preserves_consumer_bytes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    target = repo / "scripts/check.py"
    target.write_text("consumer\n", encoding="utf-8")
    payload = _ownership_payload(tmp_path / "payload")

    plan = plan_reconciliation(
        _request(
            repo,
            (payload,),
            configs={"demo": {"script_ownership": "consumer-owned"}},
        )
    )

    assert plan.applicable
    assert plan.actions == ()
    assert plan.findings == ()
    assert plan.next_lock.artifacts == []
    assert target.read_text(encoding="utf-8") == "consumer\n"


def test_conflict_guidance__text_and_json__agree_without_consumer_content(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tool.txt").write_text(_CANARY, encoding="utf-8")
    payload = write_payload(
        tmp_path / "payload",
        "demo",
        artifacts=[{"id": "tool", "target": "tool.txt", "content": b"package\n"}],
    )

    plan = plan_reconciliation(_request(repo, (payload,)))
    finding = _consumer_conflict(plan)
    rendered = _format_human_finding(finding)
    jsonable = next(
        item
        for item in findings_to_jsonable(plan.findings)
        if item["code"] == "CP-CONSUMER-CONFLICT"
    )

    assert jsonable["hint"] == finding.hint
    assert f"  hint: {finding.hint}" in rendered.splitlines()
    assert _CANARY not in rendered
    assert _CANARY not in repr(jsonable)
