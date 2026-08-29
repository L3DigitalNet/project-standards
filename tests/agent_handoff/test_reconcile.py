"""TC-T6-001: a reconciled repository cannot report a green double injection.

Issue #102: the managed SessionStart unit is one matcher-keyed group among
however many the consumer file already holds. A legacy group carrying no
matcher, or one whose matcher merely intersects the managed matcher, is a
different keyed-set key, so reconciliation appends the managed unit beside it
and every managed-unit check stays green while the harness fires both handlers.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import cast

import pytest

from project_standards.agent_handoff import cli as agent_handoff_cli
from project_standards.agent_handoff.legacy import legacy_report
from project_standards.agent_handoff.model import Finding
from project_standards.agent_handoff.paths import RepositoryRoot
from project_standards.control_plane.command_resolution import SelectedCommandPackage
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.providers import ProviderResult
from project_standards.package_contract.payload import ProviderEffect
from project_standards.package_contract.payload import ProviderOperation as V2ProviderOperation
from tests.installed_package import copy_installed_package

_DUPLICATE = "AH-LEGACY-DUPLICATE-HOOK"

_LEGACY_CODEX_GROUP = """
[[hooks.SessionStart]]

[[hooks.SessionStart.hooks]]
type = "command"
command = "bash -c 'python3 \\"$(git rev-parse --show-toplevel)/.codex/hooks/session_start.py\\"'"
timeout = 30
"""


@pytest.fixture(scope="module")
def distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    installed = tmp_path_factory.mktemp("reconcile-dist") / "project_standards"
    copy_installed_package(installed)
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


def _add_claude_group(repo: Path, group: dict[str, object]) -> None:
    settings = repo / ".claude/settings.json"
    parsed = cast(dict[str, object], json.loads(settings.read_text(encoding="utf-8")))
    hooks = cast(dict[str, object], parsed["hooks"])
    cast(list[object], hooks["SessionStart"]).append(group)
    settings.write_text(f"{json.dumps(parsed, indent=2)}\n", encoding="utf-8")


def test_matcherless_codex_group_beside_the_managed_unit_is_reported(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    # The reproduction from issue #102 step 4: the legacy group has no matcher,
    # so it never collides with the managed keyed-set key and reconciliation
    # appends beside it. Both handlers are live afterwards.
    repo = _reconciled_consumer(tmp_path, distribution)
    config = repo / ".codex/config.toml"
    config.write_text(config.read_text(encoding="utf-8") + _LEGACY_CODEX_GROUP, encoding="utf-8")

    findings = legacy_report(RepositoryRoot(repo))

    duplicate = next(
        finding
        for finding in findings
        if finding.code == _DUPLICATE and finding.path == ".codex/config.toml"
    )
    assert duplicate.severity == "error"


def test_differently_matched_claude_group_beside_the_managed_unit_is_reported(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    # The matcher intersects rather than equals the managed matcher, so the
    # keyed set holds two keys and the Claude conflict check never fires.
    repo = _reconciled_consumer(tmp_path, distribution)
    _add_claude_group(
        repo,
        {
            "matcher": "startup",
            "hooks": [
                {
                    "type": "command",
                    "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/session_start.py",
                    "timeout": 10,
                }
            ],
        },
    )

    findings = legacy_report(RepositoryRoot(repo))

    duplicate = next(
        finding
        for finding in findings
        if finding.code == _DUPLICATE and finding.path == ".claude/settings.json"
    )
    assert duplicate.severity == "error"


def test_unrelated_session_start_handler_stays_consumer_owned(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    # Negative control: overlap is about handoff startup injection, not about
    # SessionStart membership. A consumer handler that injects nothing this
    # standard owns must not be reported or blocked.
    repo = _reconciled_consumer(tmp_path, distribution)
    _add_claude_group(
        repo,
        {
            "hooks": [
                {"type": "command", "command": "echo 'welcome'", "timeout": 5},
            ],
        },
    )

    findings = legacy_report(RepositoryRoot(repo))

    assert not any(finding.code == _DUPLICATE for finding in findings)


def test_reconciled_repository_without_legacy_groups_stays_clean(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    repo = _reconciled_consumer(tmp_path, distribution)

    findings = legacy_report(RepositoryRoot(repo))

    assert not any(finding.code == _DUPLICATE for finding in findings)


def _snapshot(**files: str) -> dict[str, object]:
    return {
        path: {"content_base64": base64.b64encode(text.encode("utf-8")).decode("ascii")}
        for path, text in files.items()
    }


def _findings_for(
    monkeypatch: pytest.MonkeyPatch, snapshots: dict[str, object]
) -> tuple[Finding, ...]:
    def dispatch_stub(*_args: object) -> dict[str, object]:
        return snapshots

    def invoke_stub(*_args: object) -> ProviderResult:
        return ProviderResult(effect=ProviderEffect.FINDINGS, findings=())

    monkeypatch.setattr(agent_handoff_cli, "provider_dispatch_input", dispatch_stub)
    monkeypatch.setattr(agent_handoff_cli, "invoke_selected_provider", invoke_stub)
    return agent_handoff_cli._provider_findings(  # pyright: ignore[reportPrivateUsage]
        cast(SelectedCommandPackage, object()), V2ProviderOperation.DRIFT_CHECK
    )


_MANAGED_CLAUDE_GROUP: dict[str, object] = {
    "matcher": "startup|resume|clear|compact",
    "hooks": [
        {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.agents/hooks/agent-handoff/session_start.py",
            "timeout": 10,
        }
    ],
}


def test_drift_check_reports_the_duplicate_the_payload_call_green(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Issue #102 step 5: the payload sees one well-formed managed unit and
    # answers green, so the engine must be what refuses the double injection.
    legacy_group: dict[str, object] = {
        "hooks": [
            {
                "type": "command",
                "command": "python3 .claude/hooks/session_start.py",
                "timeout": 10,
            }
        ],
    }
    settings = json.dumps({"hooks": {"SessionStart": [_MANAGED_CLAUDE_GROUP, legacy_group]}})
    codex = (
        '[[hooks.SessionStart]]\nmatcher = "startup|resume|clear|compact"\n'
        '[[hooks.SessionStart.hooks]]\ntype = "command"\n'
        'command = "$(git rev-parse --show-toplevel)'
        '/.agents/hooks/agent-handoff/session_start.py"\ntimeout = 10\n' + _LEGACY_CODEX_GROUP
    )

    findings = _findings_for(
        monkeypatch,
        _snapshot(**{".claude/settings.json": settings, ".codex/config.toml": codex}),
    )

    reported = {finding.path for finding in findings if finding.code == _DUPLICATE}
    assert reported == {".claude/settings.json", ".codex/config.toml"}
    assert all(finding.severity == "error" for finding in findings if finding.code == _DUPLICATE)


def test_drift_check_leaves_a_single_managed_group_green(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = json.dumps({"hooks": {"SessionStart": [_MANAGED_CLAUDE_GROUP]}})

    findings = _findings_for(monkeypatch, _snapshot(**{".claude/settings.json": settings}))

    assert not any(finding.code == _DUPLICATE for finding in findings)
