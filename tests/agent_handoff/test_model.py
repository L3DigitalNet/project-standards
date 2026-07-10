import json

import pytest
from pydantic import ValidationError

from project_standards.agent_handoff.model import (
    AgentHandoffConfig,
    ChangeKind,
    Finding,
    Harness,
    OperationReport,
    PlannedChange,
    ProvenanceLock,
    StartupMode,
)


def test_agent_handoff_config_profile_invariants() -> None:
    automatic = AgentHandoffConfig(
        version="1.0",
        startup=StartupMode.AUTOMATIC,
        harnesses=(Harness.CLAUDE_CODE,),
    )
    manual = AgentHandoffConfig(version="1.0", startup=StartupMode.MANUAL, harnesses=())

    assert automatic.harnesses == (Harness.CLAUDE_CODE,)
    assert manual.harnesses == ()


def test_finding_and_change_sort_order_is_stable() -> None:
    findings = (
        Finding("Z-CODE", "warning", "z/path", "line 2", "z", "fix z"),
        Finding("B-CODE", "error", "a/path", "line 3", "b", "fix b"),
        Finding("A-CODE", "error", "a/path", "line 4", "a", "fix a"),
    )
    changes = (
        PlannedChange(ChangeKind.UPDATE, "z/path"),
        PlannedChange(ChangeKind.CREATE, "a/path"),
    )
    report = OperationReport(
        repository="/repo",
        standard_version="1.0",
        changes=changes,
        findings=findings,
    )

    payload = json.loads(report.to_json())

    assert [item["code"] for item in payload["findings"]] == [
        "A-CODE",
        "B-CODE",
        "Z-CODE",
    ]
    assert [item["path"] for item in payload["changes"]] == ["a/path", "z/path"]
    assert list(payload) == [
        "repository",
        "standard_version",
        "changes",
        "findings",
        "summary",
    ]
    assert payload["summary"] == {
        "blocked": 0,
        "created": 1,
        "errors": 2,
        "skipped": 0,
        "updated": 1,
        "warnings": 1,
    }


def test_planned_change_accepts_sha256_precondition() -> None:
    change = PlannedChange(
        ChangeKind.UPDATE,
        "AGENTS.md",
        precondition_sha256="a" * 64,
    )

    assert change.precondition_sha256 == "a" * 64


@pytest.mark.parametrize("digest", ["", "abc", "g" * 64, "A" * 64, "a" * 65])
def test_planned_change_rejects_malformed_sha256_precondition(digest: str) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        PlannedChange(ChangeKind.UPDATE, "AGENTS.md", precondition_sha256=digest)


def test_provenance_lock_json_is_deterministic() -> None:
    lock = ProvenanceLock(
        standard_version="1.0",
        startup=StartupMode.MANUAL,
        harnesses=(),
        managed={"z": "b" * 64, "AGENTS.md#agent-handoff": "a" * 64},
    )

    first = lock.to_json()
    second = lock.to_json()
    payload = json.loads(first)

    assert first == second
    assert first.endswith("\n")
    assert payload["standard"] == "agent-handoff"
    assert payload["version"] == "1.0"
    assert list(payload["managed"]) == ["AGENTS.md#agent-handoff", "z"]
    assert ProvenanceLock.model_validate_json(first) == lock


@pytest.mark.parametrize("digest", ["abc", "A" * 64, "g" * 64])
def test_provenance_lock_rejects_malformed_sha256(digest: str) -> None:
    with pytest.raises(ValidationError, match="SHA-256"):
        ProvenanceLock(
            standard_version="1.0",
            startup=StartupMode.MANUAL,
            harnesses=(),
            managed={"AGENTS.md": digest},
        )


def test_provenance_lock_rejects_duplicate_or_inconsistent_harnesses() -> None:
    with pytest.raises(ValidationError, match="unique"):
        ProvenanceLock(
            standard_version="1.0",
            startup=StartupMode.AUTOMATIC,
            harnesses=(Harness.CODEX, Harness.CODEX),
            managed={},
        )
    with pytest.raises(ValidationError, match="manual"):
        ProvenanceLock(
            standard_version="1.0",
            startup=StartupMode.MANUAL,
            harnesses=(Harness.CODEX,),
            managed={},
        )
