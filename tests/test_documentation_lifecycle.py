"""Lifecycle authority regression checks for maintained repository documents."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_HANDOFF_INDEX = _ROOT / "docs/handoff/specs-plans.md"
_SPEC_INDEX = _ROOT / "docs/specs/README.md"
_AGENT_HANDOFF_SPEC = _ROOT / "docs/specs/2026-07-09-agent-handoff-standard-package.md"
_MCP_ROADMAP = _ROOT / "docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md"
_VAIC_SPEC = _ROOT / "docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md"
_RETIRED_AGENT_HANDOFF_PLAN = _ROOT / "docs/plans/2026-07-09-agent-handoff-standard-package.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_maintained_lifecycle_documents_have_one_current_authority() -> None:
    """Completed plans cannot remain as a competing retirement authority."""
    handoff_index = _read(_HANDOFF_INDEX)
    spec_index = _read(_SPEC_INDEX)
    agent_handoff_spec = _read(_AGENT_HANDOFF_SPEC)

    assert not _RETIRED_AGENT_HANDOFF_PLAN.exists()
    assert "2026-07-09-agent-handoff-standard-package.md` | **Tasks 1-17" not in handoff_index
    assert "T32" in handoff_index
    assert "Task 18 retirement phase" not in handoff_index
    assert "T32 operational closeout" in spec_index
    assert "Task 18 retirement gates" not in spec_index
    assert "| 1.0 | 2026-08-01" in agent_handoff_spec
    assert "T32 operational closeout" in agent_handoff_spec


def test_completed_specs_point_to_durable_evidence_and_current_delivery_state() -> None:
    """Completion links and roadmap state must not refer to deleted or future work."""
    vaic_spec = _read(_VAIC_SPEC)
    roadmap = _read(_MCP_ROADMAP)

    assert "[Completion record](../handoff/specs-plans.md)" in vaic_spec
    assert "2026-07-25-v5-adoption-integrity-correction-train-plan.md" not in vaic_spec
    assert "| 1.7 | 2026-08-01" in roadmap
    assert "last_reviewed: '2026-08-01'" in roadmap
    assert "server implementation may begin at T2" not in roadmap
    assert "read-only server was delivered in 5.12.0" in roadmap
    assert "controlled-write and remote-transport phases remain deferred" in roadmap
    assert "approved and locked rev 1.8; read-only server delivered in 5.12.0" in _read(_SPEC_INDEX)
    assert "approved and locked rev 1.8; read-only server delivered in 5.12.0" in _read(
        _HANDOFF_INDEX
    )


def test_roadmap_traceability_matches_the_delivered_read_only_server() -> None:
    """Delivered read-only requirements cannot retain pre-delivery statuses."""
    roadmap = _read(_MCP_ROADMAP)

    for requirement in (
        "FR-005",
        "FR-007",
        "FR-008",
        "FR-009",
        "FR-010",
        "FR-011",
        "FR-012",
        "FR-017",
    ):
        assert re.search(rf"^\| {requirement} \| .+ \| Passing \|$", roadmap, flags=re.MULTILINE), (
            f"{requirement} must name passing evidence for the delivered read-only server"
        )

    assert "| FR-014 | Future write safety ADR/spec review. | Gate Defined |" in roadmap
    assert (
        "| FR-015 | Apply tool plan identity tests, when write phase starts. | Gate Defined |"
        in roadmap
    )
    oq_006 = next(line for line in roadmap.splitlines() if line.startswith("| OQ-006 |"))
    assert oq_006.startswith(
        "| OQ-006 | Should semantic review be an MCP prompt or tool? | Resolved for v1:"
    )
    assert oq_006.endswith("| Resolved for v1 |")
    mutated_roadmap = roadmap.replace(
        oq_006, oq_006.removesuffix("| Resolved for v1 |") + "| Open |", 1
    )
    assert not next(
        line for line in mutated_roadmap.splitlines() if line.startswith("| OQ-006 |")
    ).endswith("| Resolved for v1 |")
    assert "omit semantic review from the v1 tool and prompt registries" in roadmap
    assert "A future expansion requires separate approval" in roadmap
