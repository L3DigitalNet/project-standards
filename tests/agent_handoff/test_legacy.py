from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.agent_handoff.legacy import legacy_report
from project_standards.agent_handoff.model import Harness, StartupMode
from project_standards.agent_handoff.paths import RepositoryRoot
from project_standards.agent_handoff.planning import apply_adoption, plan_adoption
from project_standards.cli import main


def _snapshot(root: Path) -> dict[str, tuple[str, bytes | str]]:
    snapshot: dict[str, tuple[str, bytes | str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = ("symlink", str(path.readlink()))
        elif path.is_file():
            snapshot[relative] = ("file", path.read_bytes())
    return snapshot


def _report_read_only(root: Path):
    before = _snapshot(root)
    findings = legacy_report(RepositoryRoot(root))
    assert _snapshot(root) == before
    return findings


@pytest.mark.parametrize(
    ("relative", "code"),
    [
        ("STATUS.md", "AH-LEGACY-ROOT-STATUS"),
        ("TODO.md", "AH-LEGACY-ROOT-TODO"),
        ("docs/state.md", "AH-LEGACY-DOCS-STATE"),
        ("docs/handoff.md", "AH-LEGACY-MONOLITH"),
        (".claude/hooks/session_start.py", "AH-LEGACY-CLAUDE-HOOK"),
        (".codex/hooks/session_start.py", "AH-LEGACY-CODEX-HOOK"),
        (".agents/skills/handoff-system-v3/SKILL.md", "AH-LEGACY-SKILL"),
        (".agents/skills/agent-handoff-v3/SKILL.md", "AH-LEGACY-SKILL"),
    ],
)
def test_known_legacy_paths_are_reported_read_only(
    tmp_path: Path, relative: str, code: str
) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("legacy\n", encoding="utf-8")

    findings = _report_read_only(tmp_path)

    assert any(finding.code == code and finding.path == relative for finding in findings)


def test_mixed_layout_is_reported(tmp_path: Path) -> None:
    old = tmp_path / "docs/state.md"
    current = tmp_path / "docs/handoff/state.md"
    old.parent.mkdir(parents=True)
    current.parent.mkdir(parents=True)
    old.write_text("old", encoding="utf-8")
    current.write_text("current", encoding="utf-8")

    findings = _report_read_only(tmp_path)

    assert any(finding.code == "AH-LEGACY-MIXED-LAYOUT" for finding in findings)


@pytest.mark.parametrize(
    ("relative", "text", "code"),
    [
        (
            ".claude/settings.json",
            'python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/session_start.py"',
            "AH-LEGACY-CLAUDE-REGISTRATION",
        ),
        (
            ".codex/config.toml",
            'command = "python3 .codex/hooks/session_start.py"',
            "AH-LEGACY-CODEX-REGISTRATION",
        ),
        ("AGENTS.md", "Use the handoff-system-v3 skill.", "AH-LEGACY-ENGINE-REFERENCE"),
        ("CLAUDE.md", "Clone agent-handoff-v3 first.", "AH-LEGACY-ENGINE-REFERENCE"),
    ],
)
def test_stale_registrations_and_names_are_reported(
    tmp_path: Path, relative: str, text: str, code: str
) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    findings = _report_read_only(tmp_path)

    assert any(finding.code == code and finding.path == relative for finding in findings)


def test_old_and_new_hooks_report_duplicate_injection_blocker(tmp_path: Path) -> None:
    old = tmp_path / ".claude/hooks/session_start.py"
    new = tmp_path / ".agents/hooks/agent-handoff/session_start.py"
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_text("old", encoding="utf-8")
    new.write_text("new", encoding="utf-8")

    findings = _report_read_only(tmp_path)

    duplicate = next(finding for finding in findings if finding.code == "AH-LEGACY-DUPLICATE-HOOK")
    assert duplicate.severity == "error"


def test_current_clean_v1_has_no_legacy_findings(tmp_path: Path) -> None:
    plan = plan_adoption(
        repository=tmp_path,
        standard_ids=("agent-handoff",),
        startup=StartupMode.AUTOMATIC,
        harnesses=(Harness.CLAUDE_CODE, Harness.CODEX),
    )
    assert not apply_adoption(plan, dry_run=False).blocked

    assert _report_read_only(tmp_path) == ()


def test_unknown_handoff_like_evidence_is_not_guessed(tmp_path: Path) -> None:
    path = tmp_path / "docs/old-handoff-notes.md"
    path.parent.mkdir()
    path.write_text("unknown family", encoding="utf-8")

    findings = _report_read_only(tmp_path)

    finding = next(item for item in findings if item.code == "AH-LEGACY-UNCLASSIFIED")
    assert finding.path == "docs/old-handoff-notes.md"
    assert "inspect" in finding.guidance.lower()


def test_symlinked_evidence_is_reported_without_following(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-secret"
    outside.write_text("SUPER-SECRET-VALUE", encoding="utf-8")
    (tmp_path / "STATUS.md").symlink_to(outside)

    findings = _report_read_only(tmp_path)

    assert any(finding.code == "AH-LEGACY-SYMLINK" for finding in findings)
    assert not any("SUPER-SECRET-VALUE" in finding.message for finding in findings)


def test_secret_looking_legacy_content_is_never_emitted(tmp_path: Path) -> None:
    settings = tmp_path / ".claude/settings.json"
    settings.parent.mkdir()
    secret = "AKIA1234567890ABCDEF"
    settings.write_text(
        json.dumps(
            {
                "token": secret,
                "hook": "python3 .claude/hooks/session_start.py",
            }
        ),
        encoding="utf-8",
    )

    findings = _report_read_only(tmp_path)

    assert findings
    assert all(secret not in finding.message for finding in findings)
    assert all(secret not in finding.guidance for finding in findings)


def test_packaged_legacy_provider_emits_structured_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "STATUS.md").write_text("legacy\n", encoding="utf-8")

    assert main(["agent-handoff", "legacy-report", "--repo", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"][0]["code"] == "AH-LEGACY-ROOT-STATUS"
    assert payload["summary"]["warnings"] == 1
