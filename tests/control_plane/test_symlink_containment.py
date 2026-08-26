"""Reconcile must work in repositories that track symlinks (issue #179).

Every case here pins one half of the same rule: a symlink is judged by where it
lands, not by its existence. Links that stay inside the repository are ordinary
content the control plane traverses; links that leave it are still refused on
both the read (snapshot) and the write (apply) path.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

import project_standards.control_plane.executor as executor
from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.containment import CONTAINMENT_DESTINATION_CODE
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.snapshot import (
    EntryKind,
    RepositorySnapshot,
    resolved_target_paths,
)
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


def _removal_fixture(tmp_path: Path) -> tuple[Path, PlannerRequest, ReconciliationPlan]:
    """Reconcile the symlinked skill, then plan its removal by disabling the package."""
    repo = _skill_repo(tmp_path)
    payload = _skill_payload(tmp_path)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert apply_reconciliation(ApplyRequest(request, plan)).success

    resolution = resolution_request((payload,), previous_lock=plan.next_lock)
    disabled = resolution.desired.model_copy(
        update={
            "standards": {
                "symlinked-skill": resolution.desired.standards["symlinked-skill"].model_copy(
                    update={"enabled": False}
                )
            }
        }
    )
    removal_request = PlannerRequest(repo, replace(resolution, desired=disabled), (payload,))
    removal_plan = plan_reconciliation(removal_request)
    assert removal_plan.applicable, removal_plan.findings
    return repo, removal_request, removal_plan


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


def test_two_targets_aliased_by_a_symlink_converge_in_one_apply(tmp_path: Path) -> None:
    """One apply must converge when a consumer symlink collapses declared twins.

    Agent Handoff and GitHub Workflow declare byte-identical `.agents` and
    `.claude` copies of a skill; linking one at the other makes them a single
    inode. Publishing the first once invalidated the second's precondition and
    stopped the apply, so convergence needed a second run (issue #179 follow-up).
    """
    repo = _skill_repo(tmp_path)
    payload = _skill_payload(tmp_path, aliased=True)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    result = apply_reconciliation(ApplyRequest(request, plan))

    assert result.success
    assert result.error_code is None
    # Both declared names are reported applied and locked, from the one publish.
    assert set(result.applied_action_ids) == {
        ".agents/skills/demo/SKILL.md",
        ".claude/skills/demo/SKILL.md",
    }
    assert {artifact.path.original for artifact in plan.next_lock.artifacts} == {
        ".agents/skills/demo/SKILL.md",
        ".claude/skills/demo/SKILL.md",
    }
    assert (repo / ".agents/skills/demo/SKILL.md").read_bytes() == b"# Skill\n"
    assert (repo / ".claude/skills/demo").is_symlink()

    # `--check` after the single apply: nothing left to reconcile.
    checked_request = PlannerRequest(
        repo,
        resolution_request((payload,), previous_lock=plan.next_lock),
        (payload,),
    )
    checked = plan_reconciliation(checked_request)

    assert checked.applicable, checked.findings
    assert not [action for action in checked.actions if action.kind is not ActionKind.NOOP]
    assert apply_reconciliation(ApplyRequest(checked_request, checked)).applied_action_ids == ()


def test_aliased_targets_declaring_different_bytes_fail_closed(tmp_path: Path) -> None:
    """One file cannot hold two contents, so the plan refuses instead of racing.

    Nothing in the payload contract stops two declarations that a consumer's
    symlink has collapsed from disagreeing. Last-writer-wins would publish a
    lock the repository contradicts, so the conflict is surfaced at plan time.
    """
    repo = _skill_repo(tmp_path)
    payload = write_payload(
        tmp_path / "payload",
        "divergent-skill",
        artifacts=[
            {"id": "skill", "target": ".agents/skills/demo/SKILL.md", "content": b"# Agents\n"},
            {"id": "claude", "target": ".claude/skills/demo/SKILL.md", "content": b"# Claude\n"},
        ],
    )
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)

    plan = plan_reconciliation(request)

    assert not plan.applicable
    conflicts = [finding for finding in plan.findings if finding.code == "CP-ALIAS-CONFLICT"]
    assert len(conflicts) == 1
    assert ".agents/skills/demo/SKILL.md" in conflicts[0].message
    assert ".claude/skills/demo/SKILL.md" in conflicts[0].message
    assert (repo / ".agents/skills/demo/SKILL.md").exists() is False


def test_alias_detection_leaves_an_unaliased_repository_plan_unchanged(tmp_path: Path) -> None:
    """Pin the no-regression half: without a collapsing link nothing changes.

    The two harness copies are ordinary distinct files here, so both are staged,
    published, and precondition-checked exactly as before alias handling existed.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _skill_payload(tmp_path, aliased=True)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)

    plan = plan_reconciliation(request)

    assert plan.applicable, plan.findings
    assert plan.alias_followers == ()
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success
    assert (repo / ".agents/skills/demo/SKILL.md").read_bytes() == b"# Skill\n"
    assert (repo / ".claude/skills/demo/SKILL.md").read_bytes() == b"# Skill\n"
    assert not (repo / ".claude/skills/demo").is_symlink()


def _protected_repo(tmp_path: Path, destination: str) -> Path:
    """Point the declared skill directory at a protected root inside the checkout."""
    repo = tmp_path / "repo"
    (repo / destination).mkdir(parents=True)
    (repo / ".claude/skills").mkdir(parents=True)
    (repo / ".claude/skills/demo").symlink_to(
        Path("../..") / destination,
        target_is_directory=True,
    )
    return repo


@pytest.mark.parametrize("destination", [".git/hooks", ".standards/packages"])
def test_snapshot_refuses_a_link_that_redirects_into_a_protected_root(
    tmp_path: Path,
    destination: str,
) -> None:
    """The read half of #187: containment inside the checkout is not enough.

    A committed link on a declared target's parent path would otherwise make the
    control plane read — and then plan a write — against Git's own state or the
    control plane's authority under the declared spelling.
    """
    repo = _protected_repo(tmp_path, destination)

    with pytest.raises(ControlPlaneError) as failure:
        RepositorySnapshot.capture(repo, (_path(".claude/skills/demo/SKILL.md"),))

    assert failure.value.code == CONTAINMENT_DESTINATION_CODE
    # Both spellings are named, so the operator can find the offending link.
    assert ".claude/skills/demo" in str(failure.value)
    assert destination in str(failure.value)


@pytest.mark.parametrize("destination", [".git/hooks", ".standards/packages"])
def test_snapshot_resolution_refuses_a_protected_destination(
    tmp_path: Path,
    destination: str,
) -> None:
    """Alias resolution shares the walk, so it must refuse the same destination."""
    repo = _protected_repo(tmp_path, destination)

    with pytest.raises(ControlPlaneError) as failure:
        resolved_target_paths(repo, (_path(".claude/skills/demo/SKILL.md"),))

    assert failure.value.code == CONTAINMENT_DESTINATION_CODE


@pytest.mark.parametrize("destination", [".git/hooks", ".standards/packages"])
def test_apply_refuses_a_link_flipped_into_a_protected_root_before_staging(
    tmp_path: Path,
    destination: str,
) -> None:
    """The write half of #187, flipped inside the apply's own staging window.

    Planning happens before the flip and re-planning happens under the lock, so
    this is the narrowest path that reaches the executor's own destination
    refusal rather than the read path's.
    """
    repo = _skill_repo(tmp_path)
    (repo / destination).mkdir(parents=True)
    payload = _skill_payload(tmp_path)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    def redirect(phase: str, identity: str) -> None:
        if (phase, identity) != ("stage", ".claude/skills/demo/SKILL.md"):
            return
        (repo / ".claude/skills/demo").unlink()
        (repo / ".claude/skills/demo").symlink_to(
            Path("../..") / destination,
            target_is_directory=True,
        )

    result = apply_reconciliation(ApplyRequest(request, plan, fault_hook=redirect))

    assert not result.success
    assert result.error_code == CONTAINMENT_DESTINATION_CODE
    assert list((repo / destination).iterdir()) == []


def test_apply_refuses_a_plan_replanned_onto_a_protected_destination(tmp_path: Path) -> None:
    """A flip that lands before apply re-plans keeps the destination code too."""
    repo = _skill_repo(tmp_path)
    (repo / ".git/hooks").mkdir(parents=True)
    payload = _skill_payload(tmp_path)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    (repo / ".claude/skills/demo").unlink()
    (repo / ".claude/skills/demo").symlink_to(Path("../../.git/hooks"), target_is_directory=True)
    result = apply_reconciliation(ApplyRequest(request, plan))

    assert not result.success
    assert result.error_code == CONTAINMENT_DESTINATION_CODE
    assert list((repo / ".git/hooks").iterdir()) == []


def test_a_declared_control_plane_target_is_not_treated_as_a_redirect(tmp_path: Path) -> None:
    """The deny-list must not refuse a path the package itself declares.

    `.standards/` is where the control plane's own package state lives, so a
    destination that no link moved — physical equals declared — stays writable.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "payload",
        "control-state",
        artifacts=[
            {
                "id": "state",
                "target": ".standards/packages/control-state/state.txt",
                "content": b"ok\n",
            }
        ],
    )
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    assert apply_reconciliation(ApplyRequest(request, plan)).success
    assert (repo / ".standards/packages/control-state/state.txt").read_bytes() == b"ok\n"


def test_apply_refuses_an_in_root_link_flip_between_staging_and_publish(tmp_path: Path) -> None:
    """A parent that stops naming the staged directory aborts before publication.

    The flip stays inside the repository, so containment alone accepts it; only
    the staged parent's dev/ino pin can tell that the bytes would land somewhere
    the plan never authorized.
    """
    repo = _skill_repo(tmp_path)
    (repo / "elsewhere").mkdir()
    payload = _skill_payload(tmp_path)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    def flip(phase: str, identity: str) -> None:
        if (phase, identity) != ("precondition", ".claude/skills/demo/SKILL.md"):
            return
        (repo / ".claude/skills/demo").unlink()
        (repo / ".claude/skills/demo").symlink_to(Path("../../elsewhere"), target_is_directory=True)

    result = apply_reconciliation(ApplyRequest(request, plan, fault_hook=flip))

    assert not result.success
    assert result.error_code == "CP-PRECONDITION"
    assert list((repo / "elsewhere").iterdir()) == []
    assert not (repo / ".agents/skills/demo/SKILL.md").exists()


def test_snapshot_follows_a_finite_chain_of_links_to_a_real_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "real").mkdir(parents=True)
    (repo / "real/tool.py").write_bytes(b"pass\n")
    (repo / "b").symlink_to(Path("real"), target_is_directory=True)
    (repo / "a").symlink_to(Path("b"), target_is_directory=True)

    entry = RepositorySnapshot.capture(repo, (_path("a/tool.py"),)).entry(_path("a/tool.py"))

    assert entry.content == b"pass\n"


def _link_chain(repo: Path, length: int) -> None:
    """Build `link0 -> link1 -> … -> real`, one followed link per hop."""
    (repo / "real").mkdir(parents=True)
    (repo / "real/tool.py").write_bytes(b"pass\n")
    for index in range(length):
        successor = f"link{index + 1}" if index + 1 < length else "real"
        (repo / f"link{index}").symlink_to(Path(successor), target_is_directory=True)


def test_snapshot_accepts_exactly_the_link_follow_limit(tmp_path: Path) -> None:
    """40 hops is the accepted boundary; 41 is the rejected one below.

    The pair pins the cap as a boundary rather than an approximation, so a
    later edit cannot quietly turn `>` into `>=` or change the constant.
    """
    repo = tmp_path / "repo"
    _link_chain(repo, 40)

    entry = RepositorySnapshot.capture(repo, (_path("link0/tool.py"),)).entry(
        _path("link0/tool.py")
    )

    assert entry.content == b"pass\n"


def test_snapshot_refuses_one_link_past_the_follow_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _link_chain(repo, 41)

    with pytest.raises(ControlPlaneError, match="cyclic"):
        RepositorySnapshot.capture(repo, (_path("link0/tool.py"),))


def test_snapshot_refuses_a_link_to_a_regular_file_used_as_an_ancestor(tmp_path: Path) -> None:
    """A link resolving to a file is a non-directory, not an escape or a cycle.

    The kernel reports ENOTDIR for both a file and an O_NOFOLLOW'd link, so this
    case is only distinguishable by the lstat inside `_link_text`.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "file").write_bytes(b"not a directory\n")
    (repo / "link").symlink_to(Path("file"))

    with pytest.raises(ControlPlaneError, match="non-directory ancestor"):
        RepositorySnapshot.capture(repo, (_path("link/tool.py"),))


def test_snapshot_accepts_an_absolute_link_to_the_repository_root_itself(tmp_path: Path) -> None:
    """The root is the one destination whose root-relative path has no parts."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tool.py").write_bytes(b"pass\n")
    (repo / "self").symlink_to(repo.resolve(), target_is_directory=True)

    entry = RepositorySnapshot.capture(repo, (_path("self/tool.py"),)).entry(_path("self/tool.py"))

    assert entry.content == b"pass\n"


def _dangling_link_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".claude/skills").mkdir(parents=True)
    (repo / ".claude/skills/demo").symlink_to(
        Path("../../.agents/skills/demo"),
        target_is_directory=True,
    )
    return repo


def test_apply_creates_the_physical_destination_behind_a_dangling_link(tmp_path: Path) -> None:
    repo = _dangling_link_repo(tmp_path)
    payload = _skill_payload(tmp_path)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    assert apply_reconciliation(ApplyRequest(request, plan)).success

    # The missing ancestry is created where the link points, never as a
    # directory that would shadow the link itself.
    assert (repo / ".agents/skills/demo/SKILL.md").read_bytes() == b"# Skill\n"
    assert (repo / ".claude/skills/demo").is_symlink()


def test_failed_apply_rolls_back_directories_created_behind_a_dangling_link(
    tmp_path: Path,
) -> None:
    """Rollback must remove the PHYSICAL directories, not the declared spelling.

    `Path.rmdir()` on `.claude/skills/demo` would have re-resolved through the
    link and tried to remove the destination under a name the walk never
    verified; the descriptor-relative rollback removes exactly what was made.
    """
    repo = _dangling_link_repo(tmp_path)
    payload = write_payload(
        tmp_path / "payload",
        "symlinked-skill",
        artifacts=[
            {"id": "claude", "target": ".claude/skills/demo/SKILL.md", "content": b"# Skill\n"},
            {"id": "zeta", "target": "zeta.txt", "content": b"zeta\n"},
        ],
    )
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    def interrupt(phase: str, identity: str) -> None:
        # `zeta.txt` stages after the skill, so the ancestry behind the dangling
        # link already exists — and must not survive the aborted apply.
        if (phase, identity) == ("stage", "zeta.txt"):
            raise KeyboardInterrupt

    result = apply_reconciliation(ApplyRequest(request, plan, fault_hook=interrupt))

    assert not result.success
    assert not (repo / ".agents").exists()
    assert (repo / ".claude/skills/demo").is_symlink()
    assert list(repo.rglob(".project-standards-*.tmp")) == []


def test_apply_removes_a_target_through_a_symlinked_parent(tmp_path: Path) -> None:
    repo, request, plan = _removal_fixture(tmp_path)

    result = apply_reconciliation(ApplyRequest(request, plan))

    assert result.success
    assert not (repo / ".agents/skills/demo/SKILL.md").exists()
    assert (repo / ".claude/skills/demo").is_symlink()


def test_removal_refuses_an_in_root_link_flip_after_the_precondition(tmp_path: Path) -> None:
    """A removal is pinned to the parent it was authorized against.

    The decoy holds byte-identical content, so the precondition read alone
    cannot tell the flip happened: only the dev/ino pin taken before the read
    stops the unlink from deleting a file in a directory the plan never named.
    """
    repo, request, plan = _removal_fixture(tmp_path)
    decoy = repo / "elsewhere/SKILL.md"
    decoy.parent.mkdir()
    decoy.write_bytes(b"# Skill\n")

    def flip(phase: str, identity: str) -> None:
        if (phase, identity) != ("precondition", ".claude/skills/demo/SKILL.md"):
            return
        (repo / ".claude/skills/demo").unlink()
        (repo / ".claude/skills/demo").symlink_to(Path("../../elsewhere"), target_is_directory=True)

    result = apply_reconciliation(ApplyRequest(request, plan, fault_hook=flip))

    assert not result.success
    assert result.error_code == "CP-PRECONDITION"
    assert decoy.read_bytes() == b"# Skill\n"
    assert (repo / ".agents/skills/demo/SKILL.md").read_bytes() == b"# Skill\n"


def test_open_existing_parent_refuses_a_protected_destination(tmp_path: Path) -> None:
    """Managed restore's non-creating opener enforces the same destination policy.

    Reached directly because `plan_managed_restore` refuses a symlinked
    immediate parent lexically before the executor is asked, so the public
    restore route cannot express this case.
    """
    repo = _protected_repo(tmp_path, ".git/hooks")
    root = repo.resolve()
    root_descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        with pytest.raises(executor._ApplyFailure) as failure:  # pyright: ignore[reportPrivateUsage]
            executor._open_existing_parent(  # pyright: ignore[reportPrivateUsage]
                root,
                root_descriptor,
                PurePosixPath(".claude/skills/demo"),
            )
    finally:
        os.close(root_descriptor)

    assert failure.value.code == CONTAINMENT_DESTINATION_CODE


def test_aliased_twin_of_a_managed_target_is_not_classified_pre_adoption(
    tmp_path: Path,
) -> None:
    """An alias group is one file, so one lock record governs every member (issue #188).

    Reproduces agent-configs: the consumer adopted a version that declared only
    the `.agents` copy, so only that name reached the lock. When a later version
    adds the `.claude` twin, the twin has no lock entry of its own even though
    the bytes it names are the managed ones — classifying it pre-adoption made
    `--check` report a `CP-CONSUMER-CONFLICT` against a file the plan is already
    updating, and the conflict's remediation named an `rm` that would delete the
    managed copy with it.
    """
    repo = _skill_repo(tmp_path)
    adopted = write_payload(
        tmp_path / "v1",
        "symlinked-skill",
        artifacts=[
            {"id": "skill", "target": ".agents/skills/demo/SKILL.md", "content": b"# Skill\n"}
        ],
    )
    request = PlannerRequest(repo, resolution_request((adopted,)), (adopted,))
    _seed_control(repo, request)
    adoption = plan_reconciliation(request)
    assert apply_reconciliation(ApplyRequest(request, adoption)).success
    assert {artifact.path.original for artifact in adoption.next_lock.artifacts} == {
        ".agents/skills/demo/SKILL.md"
    }

    successor = write_payload(
        tmp_path / "v2",
        "symlinked-skill",
        version="1.1",
        artifacts=[
            {"id": "skill", "target": ".agents/skills/demo/SKILL.md", "content": b"# Skill 2\n"},
            {"id": "claude", "target": ".claude/skills/demo/SKILL.md", "content": b"# Skill 2\n"},
        ],
    )
    upgrade = PlannerRequest(
        repo,
        resolution_request(
            (adopted, successor),
            previous_lock=adoption.next_lock,
            selected_versions={"symlinked-skill": "1.1"},
        ),
        (adopted, successor),
    )

    plan = plan_reconciliation(upgrade)

    assert plan.applicable, plan.findings
    assert not [finding for finding in plan.findings if finding.code == "CP-CONSUMER-CONFLICT"]
    kinds = {
        action.target: action.kind
        for action in plan.actions
        if action.target.endswith("skills/demo/SKILL.md")
    }
    assert kinds == {
        ".agents/skills/demo/SKILL.md": ActionKind.UPDATE,
        ".claude/skills/demo/SKILL.md": ActionKind.UPDATE,
    }
    assert apply_reconciliation(ApplyRequest(upgrade, plan)).success
    assert (repo / ".agents/skills/demo/SKILL.md").read_bytes() == b"# Skill 2\n"


def test_aliased_pre_adoption_conflict_never_advises_deleting_the_shared_file(
    tmp_path: Path,
) -> None:
    """Both names are one inode, so `rm` on either destroys the other's file too.

    Neither twin is lock-recorded here, so both are genuinely pre-adoption and
    both conflict — the classification is symmetric, which is half of #188. The
    other half is the remediation: the generic pre-adoption hint offers `rm --
    <path> && reconcile --apply`, which on an alias group deletes the file the
    other declaration also names.
    """
    repo = _skill_repo(tmp_path)
    (repo / ".agents/skills/demo/SKILL.md").write_bytes(b"# Local\n")
    payload = _skill_payload(tmp_path, aliased=True)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    _seed_control(repo, request)

    plan = plan_reconciliation(request)

    conflicts = [finding for finding in plan.findings if finding.code == "CP-CONSUMER-CONFLICT"]
    assert {finding.path for finding in conflicts} == {
        ".agents/skills/demo/SKILL.md",
        ".claude/skills/demo/SKILL.md",
    }
    for finding in conflicts:
        assert finding.hint is not None
        assert "rm --" not in finding.hint
        assert "one repository file" in finding.hint
