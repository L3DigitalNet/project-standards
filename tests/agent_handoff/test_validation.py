from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.agent_handoff.model import Harness, StartupMode
from project_standards.agent_handoff.paths import RepositoryRoot
from project_standards.agent_handoff.planning import apply_adoption, plan_adoption
from project_standards.agent_handoff.validation import (
    drift_check,
    shape_check,
    size_report,
    validate_repository,
)
from project_standards.cli import main


def _adopt(
    root: Path,
    startup: StartupMode = StartupMode.MANUAL,
    harnesses: tuple[Harness, ...] = (),
) -> None:
    plan = plan_adoption(
        repository=root,
        standard_ids=("agent-handoff",),
        startup=startup,
        harnesses=harnesses,
    )
    report = apply_adoption(plan, dry_run=False)
    assert not report.blocked


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def test_validate_accumulates_sorted_findings(tmp_path: Path) -> None:
    (tmp_path / ".project-standards.yml").write_text(
        "agent_handoff:\n  version: '1.0'\n  startup: automatic\n  harnesses: [codex]\n",
        encoding="utf-8",
    )

    findings = validate_repository(RepositoryRoot(tmp_path))
    codes = [finding.code for finding in findings]

    assert "AH-LAYOUT-STATUS-MISSING" in codes
    assert "AH-HOOK-MISSING" in codes
    assert "AH-CODEX-CONFIG-MISSING" in codes
    assert codes == sorted(codes)


def test_fresh_manual_adoption_passes_its_own_contract(tmp_path: Path) -> None:
    _adopt(tmp_path)

    assert validate_repository(RepositoryRoot(tmp_path)) == ()


def test_packaged_validate_provider_returns_clean_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _adopt(tmp_path)

    assert main(["agent-handoff", "validate", "--repo", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["summary"]["errors"] == 0


def test_validation_is_read_only(tmp_path: Path) -> None:
    _adopt(tmp_path)
    before = _snapshot(tmp_path)

    validate_repository(RepositoryRoot(tmp_path))
    drift_check(RepositoryRoot(tmp_path))
    size_report(RepositoryRoot(tmp_path))
    shape_check(RepositoryRoot(tmp_path))

    assert _snapshot(tmp_path) == before


def test_strict_config_and_instruction_conflicts_accumulate(tmp_path: Path) -> None:
    _adopt(tmp_path)
    config = tmp_path / ".project-standards.yml"
    config.write_text(config.read_text(encoding="utf-8") + "  unknown: true\n", encoding="utf-8")
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8")
        + "\n<!-- BEGIN agent-handoff managed instructions -->\nduplicate\n"
        + "<!-- END agent-handoff managed instructions -->\n",
        encoding="utf-8",
    )

    codes = {finding.code for finding in validate_repository(RepositoryRoot(tmp_path))}

    assert "AH-CONFIG-INVALID" in codes
    assert "AH-INSTRUCTIONS-INVALID" in codes


def test_duplicate_claude_injection_is_reported(tmp_path: Path) -> None:
    _adopt(tmp_path, StartupMode.AUTOMATIC, (Harness.CLAUDE_CODE,))
    settings = tmp_path / ".claude/settings.json"
    payload = json.loads(settings.read_text(encoding="utf-8"))
    payload["hooks"]["SessionStart"].append(payload["hooks"]["SessionStart"][0])
    settings.write_text(json.dumps(payload), encoding="utf-8")

    codes = {finding.code for finding in validate_repository(RepositoryRoot(tmp_path))}

    assert "AH-CLAUDE-CONFIG-INVALID" in codes


def test_hook_mode_artifact_and_lock_drift_are_reported(tmp_path: Path) -> None:
    _adopt(tmp_path, StartupMode.AUTOMATIC, (Harness.CODEX,))
    hook = tmp_path / ".agents/hooks/agent-handoff/session_start.py"
    hook.chmod(0o644)
    hook.write_text("locally changed\n", encoding="utf-8")

    codes = {finding.code for finding in validate_repository(RepositoryRoot(tmp_path))}

    assert "AH-HOOK-MODE" in codes
    assert "AH-ARTIFACT-DRIFT" in codes
    assert "AH-LOCK-DRIFT" in codes


def test_symlinked_required_path_is_reported_without_following(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-status"
    outside.write_text("outside", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").symlink_to(outside)

    findings = validate_repository(RepositoryRoot(tmp_path))

    assert any(
        finding.code == "AH-PATH-BOUNDARY" and finding.path == "docs/STATUS.md"
        for finding in findings
    )
    assert outside.read_text(encoding="utf-8") == "outside"


def test_missing_local_markdown_pointer_is_reported(tmp_path: Path) -> None:
    _adopt(tmp_path)
    state = tmp_path / "docs/handoff/state.md"
    state.write_text(
        state.read_text(encoding="utf-8") + "\n- [Missing](docs/missing.md)\n",
        encoding="utf-8",
    )

    assert any(
        finding.code == "AH-REFERENCE-MISSING"
        for finding in validate_repository(RepositoryRoot(tmp_path))
    )


def test_size_and_shape_views_project_policy_findings(tmp_path: Path) -> None:
    _adopt(tmp_path)
    state = tmp_path / "docs/handoff/state.md"
    state.write_text("x" * 2050, encoding="utf-8")

    assert any(finding.code == "AH-SIZE-CAP" for finding in size_report(RepositoryRoot(tmp_path)))
    assert any(finding.code == "AH-SHAPE" for finding in shape_check(RepositoryRoot(tmp_path)))


def test_literal_credentials_fail_but_references_pass(tmp_path: Path) -> None:
    _adopt(tmp_path)
    credentials = tmp_path / "docs/handoff/credentials.md"
    credentials.write_text(
        "# Credentials\n\n- token = literal-value\n- vault: bao://kv/project/path\n",
        encoding="utf-8",
    )

    findings = validate_repository(RepositoryRoot(tmp_path))

    assert sum(finding.code == "AH-SECRET-LITERAL" for finding in findings) == 1


def test_drift_view_excludes_consumer_layout_and_shape(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / "docs/STATUS.md").unlink()
    skill = tmp_path / ".agents/skills/agent-handoff/SKILL.md"
    skill.write_text("drift\n", encoding="utf-8")

    codes = {finding.code for finding in drift_check(RepositoryRoot(tmp_path))}

    assert "AH-ARTIFACT-DRIFT" in codes
    assert "AH-LOCK-DRIFT" in codes
    assert not any(code.startswith("AH-LAYOUT") for code in codes)
    assert "AH-SHAPE" not in codes
