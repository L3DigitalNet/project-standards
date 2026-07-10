from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from project_standards.agent_handoff.model import ChangeKind, Harness, StartupMode
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot
from project_standards.agent_handoff.planning import (
    apply_adoption,
    plan_adoption,
    plan_upgrade,
)


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def _plan(
    repository: Path,
    startup: StartupMode = StartupMode.MANUAL,
    harnesses: tuple[Harness, ...] = (),
):
    return plan_adoption(
        repository=repository,
        standard_ids=("agent-handoff",),
        startup=startup,
        harnesses=harnesses,
    )


def test_manual_plan_has_no_hook_or_harness_config(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    destinations = {change.path for change in plan.changes}

    assert ".agents/hooks/agent-handoff/session_start.py" not in destinations
    assert ".claude/settings.json" not in destinations
    assert ".codex/config.toml" not in destinations
    assert ".agents/skills/agent-handoff/SKILL.md" in destinations
    assert "docs/STATUS.md" in destinations
    assert "AGENTS.md" in destinations


@pytest.mark.parametrize(
    ("harnesses", "expected", "absent"),
    [
        (
            (Harness.CLAUDE_CODE,),
            {".claude/settings.json", "CLAUDE.md"},
            {".codex/config.toml", "AGENTS.md"},
        ),
        (
            (Harness.CODEX,),
            {".codex/config.toml", "AGENTS.md"},
            {".claude/settings.json", "CLAUDE.md"},
        ),
        (
            (Harness.CLAUDE_CODE, Harness.CODEX),
            {".claude/settings.json", ".codex/config.toml", "CLAUDE.md", "AGENTS.md"},
            set[str](),
        ),
    ],
)
def test_automatic_profiles_plan_only_selected_integrations(
    tmp_path: Path,
    harnesses: tuple[Harness, ...],
    expected: set[str],
    absent: set[str],
) -> None:
    plan = _plan(tmp_path, StartupMode.AUTOMATIC, harnesses)
    destinations = {change.path for change in plan.changes}

    assert expected <= destinations
    assert not absent & destinations
    assert ".agents/hooks/agent-handoff/session_start.py" in destinations


def test_blocked_plan_writes_nothing(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "<!-- BEGIN agent-handoff managed instructions -->\nbroken\n", encoding="utf-8"
    )
    before = _snapshot_tree(tmp_path)

    plan = _plan(tmp_path)
    report = apply_adoption(plan, dry_run=False)

    assert report.blocked
    assert _snapshot_tree(tmp_path) == before


def test_apply_creates_lock_and_second_run_is_idempotent(tmp_path: Path) -> None:
    first = _plan(tmp_path)
    applied = apply_adoption(first, dry_run=False)

    assert not applied.blocked
    lock_path = tmp_path / ".agents/agent-handoff/manifest.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock["standard"] == "agent-handoff"
    assert lock["version"] == "1.0"
    assert "docs/STATUS.md" not in lock["managed"]
    assert ".agents/skills/agent-handoff/SKILL.md" in lock["managed"]

    second = _plan(tmp_path)

    assert not second.blocked
    assert all(change.kind is ChangeKind.SKIP for change in second.changes)
    assert apply_adoption(second, dry_run=False).changes == second.changes


def test_existing_knowledge_is_never_overwritten(tmp_path: Path) -> None:
    status = tmp_path / "docs/STATUS.md"
    status.parent.mkdir(parents=True)
    status.write_text("consumer knowledge\n", encoding="utf-8")

    report = apply_adoption(_plan(tmp_path), dry_run=False)

    assert not report.blocked
    assert status.read_text(encoding="utf-8") == "consumer knowledge\n"
    status_change = next(change for change in report.changes if change.path == "docs/STATUS.md")
    assert status_change.kind is ChangeKind.SKIP


def test_dry_run_and_apply_report_the_same_plan(tmp_path: Path) -> None:
    plan = _plan(tmp_path)

    dry_run = apply_adoption(plan, dry_run=True)
    assert _snapshot_tree(tmp_path) == {}
    applied = apply_adoption(plan, dry_run=False)

    assert dry_run.changes == plan.changes == applied.changes


def test_symlink_escape_is_a_blocker_and_nothing_is_written(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "docs").symlink_to(outside, target_is_directory=True)
    before = _snapshot_tree(tmp_path)

    plan = _plan(tmp_path)
    report = apply_adoption(plan, dry_run=False)

    assert report.blocked
    assert _snapshot_tree(tmp_path) == before
    assert _snapshot_tree(outside) == {}


def test_static_and_dynamic_blockers_accumulate(tmp_path: Path) -> None:
    (tmp_path / ".agents").symlink_to(tmp_path.parent, target_is_directory=True)
    (tmp_path / "AGENTS.md").write_text(
        "<!-- BEGIN agent-handoff managed instructions -->\n", encoding="utf-8"
    )

    plan = _plan(tmp_path)

    assert plan.blocked
    codes = {finding.code for finding in plan.findings}
    assert "AH-PATH-BOUNDARY" in codes
    assert "AH-INTEGRATION-CONFLICT" in codes


def test_apply_rechecks_dynamic_precondition_before_write(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text("before\n", encoding="utf-8")
    plan = _plan(tmp_path)
    agents.write_text("raced\n", encoding="utf-8")

    report = apply_adoption(plan, dry_run=False)

    assert report.blocked
    assert agents.read_text(encoding="utf-8") == "raced\n"
    assert not (tmp_path / ".agents/agent-handoff/manifest.json").exists()


def test_partial_io_failure_reports_completed_writes_and_withholds_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path)
    real_write = RepositoryRoot.write_bytes

    def fail_project_config(self: RepositoryRoot, relative: str, data: bytes) -> None:
        if relative == ".project-standards.yml":
            raise RepositoryBoundaryError("simulated write failure")
        real_write(self, relative, data)

    monkeypatch.setattr(RepositoryRoot, "write_bytes", fail_project_config)

    report = apply_adoption(plan, dry_run=False)

    assert report.blocked
    assert any(change.kind is ChangeKind.CREATE for change in report.changes)
    assert any(
        change.kind is ChangeKind.BLOCKED and change.path == ".project-standards.yml"
        for change in report.changes
    )
    assert not (tmp_path / ".agents/agent-handoff/manifest.json").exists()


def test_lock_drift_blocks_re_adoption(tmp_path: Path) -> None:
    apply_adoption(_plan(tmp_path), dry_run=False)
    skill = tmp_path / ".agents/skills/agent-handoff/SKILL.md"
    skill.write_text("locally modified\n", encoding="utf-8")

    plan = _plan(tmp_path)

    assert plan.blocked
    assert any(finding.code == "AH-LOCK-DRIFT" for finding in plan.findings)


def test_upgrade_refreshes_clean_old_managed_artifact(tmp_path: Path) -> None:
    apply_adoption(_plan(tmp_path), dry_run=False)
    skill_rel = ".agents/skills/agent-handoff/SKILL.md"
    skill = tmp_path / skill_rel
    old = b"clean content from an older package\n"
    skill.write_bytes(old)
    lock_path = tmp_path / ".agents/agent-handoff/manifest.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["managed"][skill_rel] = hashlib.sha256(old).hexdigest()
    lock_path.write_text(json.dumps(lock), encoding="utf-8")

    plan = plan_upgrade(repository=tmp_path, standard_ids=("agent-handoff",))

    assert not plan.blocked
    change = next(change for change in plan.changes if change.path == skill_rel)
    assert change.kind is ChangeKind.UPDATE
    report = apply_adoption(plan, dry_run=False)
    assert not report.blocked
    assert skill.read_bytes() != old


def test_upgrade_refuses_locally_modified_managed_artifact(tmp_path: Path) -> None:
    apply_adoption(_plan(tmp_path), dry_run=False)
    skill = tmp_path / ".agents/skills/agent-handoff/SKILL.md"
    skill.write_text("unlocked local edit\n", encoding="utf-8")
    before = _snapshot_tree(tmp_path)

    plan = plan_upgrade(repository=tmp_path, standard_ids=("agent-handoff",))
    report = apply_adoption(plan, dry_run=False)

    assert report.blocked
    assert _snapshot_tree(tmp_path) == before
