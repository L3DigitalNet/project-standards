from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.agent_handoff.legacy import legacy_report
from project_standards.agent_handoff.model import Harness, StartupMode
from project_standards.agent_handoff.paths import RepositoryRoot
from project_standards.agent_handoff.planning import apply_adoption, plan_adoption
from project_standards.cli import main
from project_standards.control_plane.distribution import InstalledDistribution
from tests.payload_tree import payload_tree


def _snapshot(root: Path) -> dict[str, tuple[str, bytes | str]]:
    snapshot: dict[str, tuple[str, bytes | str]] = {}
    for path in payload_tree(root):
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


@pytest.fixture(scope="module")
def distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    import shutil

    root = Path(__file__).resolve().parents[2]
    installed = tmp_path_factory.mktemp("legacy-lock-dist") / "project_standards"
    shutil.copytree(root / "src/project_standards", installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _reconciled_consumer(tmp_path: Path, distribution: InstalledDistribution) -> Path:
    from project_standards.control_plane.bootstrap import initialize_control_plane
    from project_standards.control_plane.cli import build_planner_request
    from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
    from project_standards.control_plane.planner import plan_reconciliation

    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    config = repo / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[standards.agent-handoff]\nenabled = true\nversion = "latest"\n\n'
        + '[standards.agent-handoff.config]\ncontract_version = "1.1"\n'
        + 'startup = "automatic"\nharnesses = ["claude-code", "codex"]\n',
        encoding="utf-8",
    )
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    return repo


def test_locked_registration_container_is_not_legacy_evidence(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    # Issue #90: the applied lock owns the SessionStart keyed set inside
    # .codex/config.toml. A stale hook-path string in the consumer-owned
    # remainder of that managed container must not become registration
    # evidence, and must not cascade into a duplicate-hook error against
    # the current shared hook.
    repo = _reconciled_consumer(tmp_path, distribution)
    config = repo / ".codex/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + "\n# retired wrapper reference: .codex/hooks/session_start.py\n",
        encoding="utf-8",
    )

    findings = _report_read_only(repo)

    assert not any(finding.code == "AH-LEGACY-CODEX-REGISTRATION" for finding in findings)
    assert not any(finding.code == "AH-LEGACY-DUPLICATE-HOOK" for finding in findings)


def test_unowned_duplicate_hook_stays_visible_beside_locked_units(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    # Negative control for TC-T3-001: lock provenance suppresses only managed
    # evidence. A real unowned per-harness hook file still reports, and still
    # raises the duplicate-injection error against the managed shared hook.
    repo = _reconciled_consumer(tmp_path, distribution)
    stray = repo / ".claude/hooks/session_start.py"
    stray.parent.mkdir(parents=True)
    stray.write_text("legacy\n", encoding="utf-8")

    findings = _report_read_only(repo)

    assert any(finding.code == "AH-LEGACY-CLAUDE-HOOK" for finding in findings)
    duplicate = next(finding for finding in findings if finding.code == "AH-LEGACY-DUPLICATE-HOOK")
    assert duplicate.severity == "error"
