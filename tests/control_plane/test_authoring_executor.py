from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from project_standards.control_plane.executor import apply_authoring_plan
from project_standards.control_plane.schemas import MutationPlanSchema
from project_standards.control_plane.snapshot import RepositorySnapshot
from project_standards.package_contract.paths import SafeRelativePath


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _action(
    repo: Path,
    target: str,
    content: bytes,
    *,
    kind: str,
    mode: str | None = None,
) -> dict[str, object]:
    relative = SafeRelativePath.parse(target)
    snapshot = RepositorySnapshot.capture(repo, (relative,)).entry(relative)
    action: dict[str, object] = {
        "kind": kind,
        "target": target,
        "adapter": "whole-file",
        "scope": "$file",
        "summary": f"{kind} managed document",
        "precondition_digest": snapshot.precondition_digest.value,
        "content_digest": _digest(content),
        "content_base64": base64.b64encode(content).decode("ascii"),
    }
    if mode is not None:
        action["mode"] = mode
    return action


def _plan(
    actions: list[dict[str, object]],
    *,
    diagnostics: list[dict[str, object]] | None = None,
) -> MutationPlanSchema:
    return MutationPlanSchema.model_validate(
        {
            "schema_version": "1.0",
            "standard_id": "markdown-frontmatter",
            "version": "1.2",
            "actions": actions,
            "diagnostics": diagnostics or [],
        }
    )


def test_authoring_executor_rejects_a_plan_with_package_refusal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "existing.md"
    target.write_bytes(b"old\n")
    plan = _plan(
        [_action(repo, "existing.md", b"new\n", kind="update")],
        diagnostics=[
            {
                "code": "FM-AUTHORING-REFUSED",
                "severity": "error",
                "path": "existing.md",
                "message": "package refused the target",
                "refusal": True,
            }
        ],
    )

    result = apply_authoring_plan(repo, plan)

    assert result.success is False
    assert result.error_code == "CP-AUTHORING-PLAN"
    assert target.read_bytes() == b"old\n"


def test_authoring_executor_stages_and_applies_complete_whole_file_plan(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    existing = repo / "existing.md"
    existing.write_bytes(b"old\n")
    existing.chmod(0o640)
    remove = repo / "remove.md"
    remove.write_bytes(b"remove\n")
    remove_snapshot = RepositorySnapshot.capture(
        repo,
        (SafeRelativePath.parse("remove.md"),),
    ).entries[0]
    removal: dict[str, object] = {
        "kind": "remove",
        "target": "remove.md",
        "adapter": "whole-file",
        "scope": "$file",
        "summary": "remove obsolete document",
        "precondition_digest": remove_snapshot.precondition_digest.value,
    }
    actions: list[dict[str, object]] = [
        _action(repo, "existing.md", b"new\n", kind="update"),
        _action(repo, "nested/new.md", b"created\n", kind="create", mode="0600"),
        removal,
    ]

    result = apply_authoring_plan(repo, _plan(actions))

    assert result.success
    assert result.applied_targets == ("existing.md", "nested/new.md", "remove.md")
    assert existing.read_bytes() == b"new\n"
    assert existing.stat().st_mode & 0o777 == 0o640
    created = repo / "nested/new.md"
    assert created.read_bytes() == b"created\n"
    assert created.stat().st_mode & 0o777 == 0o600
    assert not remove.exists()


def test_authoring_executor_rejects_stale_plan_before_any_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    first = repo / "first.md"
    first.write_bytes(b"first\n")
    stale = repo / "stale.md"
    stale.write_bytes(b"before\n")
    plan = _plan(
        [
            _action(repo, "first.md", b"changed\n", kind="update"),
            _action(repo, "stale.md", b"after\n", kind="update"),
        ]
    )
    stale.write_bytes(b"concurrent edit\n")

    result = apply_authoring_plan(repo, plan)

    assert not result.success
    assert result.error_code == "CP-PRECONDITION"
    assert result.applied_targets == ()
    assert first.read_bytes() == b"first\n"
    assert stale.read_bytes() == b"concurrent edit\n"
