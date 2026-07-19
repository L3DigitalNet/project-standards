from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import project_standards.agent_handoff.cli as agent_handoff_cli
from project_standards.agent_handoff.cli import run
from project_standards.agent_handoff.model import Finding
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import (
    ApplyRequest,
    AuthoringApplyResult,
    apply_reconciliation,
)
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockMode,
    control_plane_lock,
)
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.control_plane.schemas import MutationPlanSchema


@pytest.fixture(scope="module")
def distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    installed = tmp_path_factory.mktemp("agent-handoff-v2") / "project_standards"
    shutil.copytree(Path("src/project_standards"), installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _consumer(tmp_path: Path, distribution: InstalledDistribution) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "agent-handoff", True)
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    return repo


def test_unified_validate_uses_selected_provider(
    tmp_path: Path,
    distribution: InstalledDistribution,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)

    def fail_legacy(*_args: object, **_kwargs: object) -> int:
        pytest.fail("legacy provider runner used under unified authority")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        fail_legacy,
    )

    assert run(["validate", "--repo", str(repo), "--json"], distribution=distribution) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["standard_version"] == "1.2"
    assert report["findings"] == []


def test_unified_validate_reports_selected_payload_drift_without_writing(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    skill = repo / ".agents/skills/agent-handoff/SKILL.md"
    skill.write_text("consumer drift\n", encoding="utf-8")
    before = skill.read_bytes()

    assert run(["drift-check", "--repo", str(repo), "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)
    assert any(item["code"] == "AH-DRIFT" for item in report["findings"])
    assert skill.read_bytes() == before


def test_unified_upgrade_refuses_local_managed_drift(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    skill = repo / ".agents/skills/agent-handoff/SKILL.md"
    skill.write_text("consumer drift\n", encoding="utf-8")

    assert run(["upgrade", "--repo", str(repo), "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["changes"] == []
    assert any(item["code"] == "AH-ARTIFACT-DRIFT" for item in report["findings"])
    assert skill.read_text(encoding="utf-8") == "consumer drift\n"


def test_unified_upgrade_is_a_noop_when_managed_bytes_are_current(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)

    assert run(["upgrade", "--repo", str(repo), "--json"], distribution=distribution) == 0
    assert json.loads(capsys.readouterr().out)["changes"] == []


def test_unified_upgrade__missing_resource__exits_three_without_traceback(
    tmp_path: Path,
    distribution: InstalledDistribution,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    monkeypatch.setitem(
        agent_handoff_cli._UPGRADE_RESOURCES,  # pyright: ignore[reportPrivateUsage]
        ".agents/skills/agent-handoff/SKILL.md",
        "missing-resource",
    )

    assert run(["upgrade", "--repo", str(repo)], distribution=distribution) == 3
    captured = capsys.readouterr()
    assert "selected Agent Handoff payload is missing resource 'missing-resource'" in captured.err
    assert "Traceback" not in captured.err


def test_unified_upgrade_reports_recoverable_apply_failure_as_a_finding(
    tmp_path: Path,
    distribution: InstalledDistribution,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)

    def fail_apply(_repo: Path, _plan: MutationPlanSchema) -> AuthoringApplyResult:
        return AuthoringApplyResult(False, (), "CP-PRECONDITION")

    monkeypatch.setattr(
        agent_handoff_cli,
        "apply_authoring_plan",
        fail_apply,
    )

    assert run(["upgrade", "--repo", str(repo), "--json"], distribution=distribution) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["findings"][0]["code"] == "AH-APPLY-FAILED"
    assert report["findings"][0]["path"] == "."
    assert "CP-PRECONDITION" in report["findings"][0]["message"]
    assert "Traceback" not in captured.err


def test_unified_upgrade_dry_run_holds_a_read_lock(
    tmp_path: Path,
    distribution: InstalledDistribution,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _consumer(tmp_path, distribution)
    original = agent_handoff_cli._upgrade_plan  # pyright: ignore[reportPrivateUsage]

    def assert_read_locked(selected: object) -> object:
        with (
            pytest.raises(ControlPlaneBusyError, match="CP-BUSY"),
            control_plane_lock(repo, LockMode.WRITE),
        ):
            pytest.fail("dry-run allowed a concurrent writer")
        return original(selected)  # pyright: ignore[reportArgumentType]

    monkeypatch.setattr(agent_handoff_cli, "_upgrade_plan", assert_read_locked)

    assert run(["upgrade", "--repo", str(repo), "--dry-run"], distribution=distribution) == 0


def test_unified_size_report_preserves_numeric_budget_message(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / "docs/handoff/state.md").write_bytes(b"x" * 3000)

    assert run(["size-report", "--repo", str(repo), "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)
    finding = next(item for item in report["findings"] if item["code"] == "AH-SIZE-CAP")
    assert finding["message"] == "document exceeds 2048 byte hard cap by 952 bytes"
    assert finding["locus"] == "byte budget"


@pytest.mark.parametrize(
    ("view_arguments", "expected_code_prefix"),
    [
        pytest.param(("--repo", "{repo}", "--view", "size"), "AH-SIZE", id="after-repo"),
        pytest.param(("--repo", "{repo}", "--view=size"), "AH-SIZE", id="equals-form"),
        pytest.param(
            ("--view", "size", "--repo", "{repo}", "--view", "shape"),
            "AH-SHAPE",
            id="repeated-last-wins",
        ),
    ],
)
def test_unified_validate__parser_compatible_view_forms__select_expected_findings(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
    view_arguments: tuple[str, ...],
    expected_code_prefix: str,
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / "docs/handoff/state.md").write_bytes(b"x" * 3000)
    arguments = [str(repo) if item == "{repo}" else item for item in view_arguments]

    assert run(["validate", *arguments, "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)
    codes = [item["code"] for item in report["findings"]]

    assert codes
    assert all(code.startswith(expected_code_prefix) for code in codes)


def test_unified_validate_uses_the_last_repeated_repo_option(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first = _consumer(first_root, distribution)
    second = _consumer(second_root, distribution)
    (first / ".agents/skills/agent-handoff/SKILL.md").write_text(
        "consumer drift\n", encoding="utf-8"
    )

    assert (
        run(
            ["validate", "--repo", str(first), "--repo", str(second), "--json"],
            distribution=distribution,
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["repository"] == str(second)


def test_unified_command_rejects_empty_repo_without_legacy_fallback(
    tmp_path: Path,
    distribution: InstalledDistribution,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    monkeypatch.chdir(repo)

    def fail_legacy(*_args: object, **_kwargs: object) -> int:
        pytest.fail("legacy provider runner used for malformed unified invocation")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        fail_legacy,
    )

    assert run(["validate", "--repo="], distribution=distribution) == 2
    assert "--repo requires a non-empty path" in capsys.readouterr().err


def test_unified_command_reports_invalid_pending_options_without_traceback(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    config = repo / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + "\n[standards.agent-handoff.config]\nstartup = 'invalid'\n",
        encoding="utf-8",
    )

    assert run(["validate", "--repo", str(repo)], distribution=distribution) == 2
    captured = capsys.readouterr()
    assert "configured package options are invalid" in captured.err
    assert "Traceback" not in captured.err


def test_unified_command_reports_malformed_config_as_operator_error(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / ".standards/config.toml").write_text("not = [valid", encoding="utf-8")

    assert run(["validate", "--repo", str(repo)], distribution=distribution) == 2
    captured = capsys.readouterr()
    assert "config" in captured.err
    assert "Traceback" not in captured.err


def test_unified_command_reports_missing_config_as_operator_error(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / ".standards/config.toml").unlink()

    assert run(["validate", "--repo", str(repo)], distribution=distribution) == 2
    captured = capsys.readouterr()
    assert "config" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("filename", ["catalog.toml", "lock.toml"])
def test_unified_command_reports_malformed_control_state_as_prerequisite_failure(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
    filename: str,
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / ".standards" / filename).write_text("not = [valid", encoding="utf-8")

    assert run(["validate", "--repo", str(repo)], distribution=distribution) == 3
    captured = capsys.readouterr()
    assert "invalid" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("filename", ["catalog.toml", "lock.toml"])
def test_unified_command_reports_missing_control_state_as_prerequisite_failure(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
    filename: str,
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / ".standards" / filename).unlink()

    assert run(["validate", "--repo", str(repo)], distribution=distribution) == 3
    captured = capsys.readouterr()
    assert "missing" in captured.err
    assert "Traceback" not in captured.err


def test_unified_command_reports_nonexistent_repo_as_operator_error(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "missing"

    assert run(["validate", "--repo", str(repo)], distribution=distribution) == 2
    captured = capsys.readouterr()
    assert "repository root" in captured.err
    assert "Traceback" not in captured.err


def test_unified_validate_restores_missing_link_findings(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    state = repo / "docs/handoff/state.md"
    state.write_text(
        state.read_text(encoding="utf-8") + "\n[Missing](missing.md)\n",
        encoding="utf-8",
    )

    assert run(["validate", "--repo", str(repo), "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)
    assert any(item["code"] == "AH-REFERENCE-MISSING" for item in report["findings"])


def test_agent_handoff_1_2_selected_provider_normalizes_link_targets(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    target = repo / "docs/handoff/reference with spaces.md"
    target.write_text("# Reference\n", encoding="utf-8")
    architecture = repo / "docs/handoff/architecture.md"
    architecture.write_text(
        architecture.read_text(encoding="utf-8")
        + '\n[Angle path](<reference with spaces.md> "Reference")\n'
        + "[Empty target]()\n"
        + "[Whitespace target]( )\n"
        + "[Angle empty target](<>)\n",
        encoding="utf-8",
    )

    assert run(["validate", "--repo", str(repo), "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)
    references = [item for item in report["findings"] if item["code"] == "AH-REFERENCE-MISSING"]

    assert report["standard_version"] == "1.2"
    assert [(item["path"], item["locus"]) for item in references] == [
        ("docs/handoff/architecture.md", "Markdown link: "),
        ("docs/handoff/architecture.md", "Markdown link: "),
        ("docs/handoff/architecture.md", "Markdown link: "),
    ]


def test_unified_validate_does_not_follow_a_symlinked_link_target(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    target = repo / "docs/handoff/target.md"
    target.write_text("# Target\n", encoding="utf-8")
    (repo / "docs/handoff/linked.md").symlink_to(target)
    state = repo / "docs/handoff/state.md"
    state.write_text(
        state.read_text(encoding="utf-8") + "\n[Linked](linked.md)\n",
        encoding="utf-8",
    )

    assert run(["validate", "--repo", str(repo), "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)
    assert any(item["code"] == "AH-REFERENCE-MISSING" for item in report["findings"])


def test_unified_legacy_report_serializes_platform_evidence_through_provider(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / "STATUS.md").write_text("legacy\n", encoding="utf-8")

    assert run(["legacy-report", "--repo", str(repo), "--json"], distribution=distribution) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["findings"][0]["code"] == "AH-LEGACY-ROOT-STATUS"
    assert report["standard_version"] == "1.2"


@pytest.mark.parametrize(
    ("selected_authority", "as_json"),
    [
        pytest.param(True, False, id="selected-human"),
        pytest.param(True, True, id="selected-json"),
        pytest.param(False, False, id="fallback-human"),
        pytest.param(False, True, id="fallback-json"),
    ],
)
def test_legacy_report__emitted_inventory_with_errors__returns_success_and_retains_findings(
    tmp_path: Path,
    distribution: InstalledDistribution,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    selected_authority: bool,
    as_json: bool,
) -> None:
    finding = Finding(
        code="AH-LEGACY-TEST",
        severity="error",
        path="legacy.txt",
        locus="legacy inventory",
        message="legacy evidence requires review",
        guidance="review it",
    )

    def find_legacy(_root: object) -> tuple[Finding, ...]:
        return (finding,)

    if selected_authority:
        repo = _consumer(tmp_path, distribution)
        monkeypatch.setattr(agent_handoff_cli, "legacy_report", find_legacy)
    else:
        repo = tmp_path / "consumer"
        repo.mkdir()

        def load_finder(_module_name: str, _attribute: str) -> object:
            return find_legacy

        monkeypatch.setattr(
            "project_standards.agent_handoff.providers._load_finder",
            load_finder,
        )

    args = ["legacy-report", "--repo", str(repo)]
    if as_json:
        args.append("--json")

    assert run(args, distribution=distribution) == 0
    captured = capsys.readouterr()
    if as_json:
        assert captured.err == ""
        report = json.loads(captured.out)
        assert report["findings"] == [
            {
                "code": "AH-LEGACY-TEST",
                "severity": "error",
                "path": "legacy.txt",
                "locus": "legacy inventory",
                "message": "legacy evidence requires review",
                "guidance": "review it",
            }
        ]
        assert report["summary"]["errors"] == 1
    else:
        assert captured.out == ""
        assert captured.err == "error: legacy.txt: legacy evidence requires review\n"
