"""Reconcile must work in repositories that track symlinks (issue #179).

Every case here pins one half of the same rule: a symlink is judged by where it
lands, not by its existence. Links that stay inside the repository are ordinary
content the control plane traverses; links that leave it are still refused on
both the read (snapshot) and the write (apply) path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.control_plane.snapshot import EntryKind, RepositorySnapshot
from project_standards.package_contract.paths import SafeRelativePath
from tests.control_plane.planner_helpers import resolution_request, write_payload


def _path(value: str) -> SafeRelativePath:
    return SafeRelativePath.parse(value)


def _skill_repo(tmp_path: Path) -> Path:
    """Build agent-configs' shape: `.claude/skills/demo` links to `.agents/skills/demo`."""
    repo = tmp_path / "repo"
    (repo / ".agents/skills/demo").mkdir(parents=True)
    (repo / ".claude/skills").mkdir(parents=True)
    (repo / ".claude/skills/demo").symlink_to(
        Path("../../.agents/skills/demo"),
        target_is_directory=True,
    )
    return repo


def _skill_payload(tmp_path: Path, *, aliased: bool = False) -> InstalledPayload:
    """Declare the `.claude` skill target, optionally alongside its `.agents` twin.

    `aliased` reproduces the agent-handoff payload shape, where both harness
    paths are declared and the consumer's symlink collapses them onto one inode.
    """
    artifacts: list[dict[str, object]] = [
        {"id": "claude", "target": ".claude/skills/demo/SKILL.md", "content": b"# Skill\n"},
    ]
    if aliased:
        artifacts.insert(
            0,
            {"id": "skill", "target": ".agents/skills/demo/SKILL.md", "content": b"# Skill\n"},
        )
    return write_payload(tmp_path / "payload", "symlinked-skill", artifacts=artifacts)  # pyright: ignore[reportArgumentType]


def _seed_control(repo: Path, request: PlannerRequest) -> None:
    control = repo / ".standards"
    control.mkdir(parents=True, exist_ok=True)
    (control / "lock.toml").write_bytes(render_lock(request.resolution.previous_lock))


def test_snapshot_reads_a_target_beneath_an_inside_repository_symlink(tmp_path: Path) -> None:
    repo = _skill_repo(tmp_path)
    (repo / ".agents/skills/demo/SKILL.md").write_bytes(b"# Skill\n")

    snapshot = RepositorySnapshot.capture(repo, (_path(".claude/skills/demo/SKILL.md"),))
    entry = snapshot.entry(_path(".claude/skills/demo/SKILL.md"))

    assert entry.kind is EntryKind.REGULAR
    assert entry.content == b"# Skill\n"


def test_snapshot_ignores_a_tracked_symlink_that_no_target_traverses(tmp_path: Path) -> None:
    repo = _skill_repo(tmp_path)
    (repo / "tool.py").write_bytes(b"pass\n")

    entry = RepositorySnapshot.capture(repo, (_path("tool.py"),)).entry(_path("tool.py"))

    assert entry.content == b"pass\n"


def test_snapshot_reports_a_missing_target_below_a_dangling_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".claude/skills").mkdir(parents=True)
    (repo / ".claude/skills/demo").symlink_to(Path("../../.agents/skills/demo"))

    entry = RepositorySnapshot.capture(
        repo,
        (_path(".claude/skills/demo/SKILL.md"),),
    ).entry(_path(".claude/skills/demo/SKILL.md"))

    assert entry.kind is EntryKind.MISSING


def test_snapshot_accepts_an_absolute_link_that_stays_inside_the_repository(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "real").mkdir(parents=True)
    (repo / "real/tool.py").write_bytes(b"pass\n")
    (repo / "link").symlink_to(repo.resolve() / "real", target_is_directory=True)

    entry = RepositorySnapshot.capture(repo, (_path("link/tool.py"),)).entry(_path("link/tool.py"))

    assert entry.content == b"pass\n"


def test_snapshot_refuses_an_absolute_link_that_leaves_the_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_bytes(b"secret\n")
    (repo / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ControlPlaneError, match="symlink ancestor escaping the repository"):
        RepositorySnapshot.capture(repo, (_path("link/secret.txt"),))


def test_snapshot_refuses_a_relative_link_that_climbs_out_of_the_repository(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "nested").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_bytes(b"secret\n")
    # Two levels of `..` from `repo/nested` lands in tmp_path, outside the root.
    (repo / "nested/link").symlink_to(Path("../../outside"), target_is_directory=True)

    with pytest.raises(ControlPlaneError, match="symlink ancestor escaping the repository"):
        RepositorySnapshot.capture(repo, (_path("nested/link/secret.txt"),))


def test_snapshot_accepts_a_relative_link_that_climbs_and_returns_inside(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "nested").mkdir(parents=True)
    (repo / "real").mkdir()
    (repo / "real/tool.py").write_bytes(b"pass\n")
    (repo / "nested/link").symlink_to(Path("../real"), target_is_directory=True)

    entry = RepositorySnapshot.capture(
        repo,
        (_path("nested/link/tool.py"),),
    ).entry(_path("nested/link/tool.py"))

    assert entry.content == b"pass\n"


def test_snapshot_refuses_a_cyclic_symlink_ancestor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a").symlink_to(Path("b"))
    (repo / "b").symlink_to(Path("a"))

    with pytest.raises(ControlPlaneError, match="cyclic"):
        RepositorySnapshot.capture(repo, (_path("a/tool.py"),))


def test_snapshot_still_refuses_a_regular_file_used_as_an_ancestor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "file").write_bytes(b"not a directory\n")

    with pytest.raises(ControlPlaneError, match="non-directory ancestor"):
        RepositorySnapshot.capture(repo, (_path("file/tool.py"),))


def test_reconcile_applies_through_a_tracked_skill_symlink_and_reconverges(
    tmp_path: Path,
) -> None:
    repo = _skill_repo(tmp_path)
    payload = _skill_payload(tmp_path)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)

    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success

    # The write follows the link instead of replacing it, so the bytes land in
    # the link's destination and the tracked link survives reconcile untouched.
    assert (repo / ".agents/skills/demo/SKILL.md").read_bytes() == b"# Skill\n"
    assert (repo / ".claude/skills/demo").is_symlink()

    second_request = PlannerRequest(
        repo,
        resolution_request((payload,), previous_lock=plan.next_lock),
        (payload,),
    )
    second = plan_reconciliation(second_request)
    result = apply_reconciliation(ApplyRequest(second_request, second))

    assert second.applicable
    assert result.success
    assert result.applied_action_ids == ()


def test_reconcile_succeeds_when_an_unrelated_tracked_symlink_exists(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs/note.md").write_bytes(b"# Note\n")
    (repo / "mirror").symlink_to(Path("docs"), target_is_directory=True)
    payload = write_payload(
        tmp_path / "payload",
        "unrelated-symlink",
        artifacts=[{"id": "tool", "target": "tools/check.py", "content": b"pass\n"}],
    )
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)

    plan = plan_reconciliation(request)

    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    assert (repo / "tools/check.py").read_bytes() == b"pass\n"
    assert (repo / "mirror").is_symlink()


def test_apply_refuses_an_escaping_ancestor_introduced_after_planning(tmp_path: Path) -> None:
    """Pin the write half of containment: a plan cannot be redirected out of the repo."""
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    payload = write_payload(
        tmp_path / "payload",
        "escaping-parent",
        artifacts=[{"id": "tool", "target": "tools/check.py", "content": b"pass\n"}],
    )
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    # The swap happens between planning and applying, which is exactly the
    # window the descriptor walk exists to close.
    (repo / "tools").rmdir()
    (repo / "tools").symlink_to(outside, target_is_directory=True)
    result = apply_reconciliation(ApplyRequest(request, plan))

    assert not result.success
    assert list(outside.iterdir()) == []


def test_two_targets_aliased_by_a_symlink_converge_on_the_next_reconcile(
    tmp_path: Path,
) -> None:
    """Characterize the residual limit of following an ancestor link.

    When a payload declares both harness copies of one file and the consumer has
    collapsed them onto a single inode, publishing the first target invalidates
    the second's plan-time precondition, so the first apply stops partway by
    design rather than writing against a stale precondition. The important
    property is that the state is repairable: a fresh plan sees the alias
    already carrying the desired bytes and converges without further writes.
    """
    repo = _skill_repo(tmp_path)
    payload = _skill_payload(tmp_path, aliased=True)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)

    first = apply_reconciliation(ApplyRequest(request, plan))

    assert not first.success
    assert first.error_code == "CP-PRECONDITION"

    repaired_request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    repaired = plan_reconciliation(repaired_request)
    result = apply_reconciliation(ApplyRequest(repaired_request, repaired))

    assert repaired.applicable, repaired.findings
    assert result.success
    assert (repo / ".agents/skills/demo/SKILL.md").read_bytes() == b"# Skill\n"
