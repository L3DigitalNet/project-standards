from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from typing import cast

import pytest

import project_standards.agent_handoff.cli as agent_handoff_cli
import project_standards.control_plane.command_resolution as command_resolution
from project_standards.agent_handoff.cli import run
from project_standards.agent_handoff.model import Finding
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import parse_lock
from project_standards.control_plane.config_edit import (
    set_standard_enabled,
    set_standard_selection,
)
from project_standards.control_plane.diagnostics import ControlFinding
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
from project_standards.control_plane.providers import ProviderResult
from project_standards.control_plane.schemas import MutationPlanSchema
from project_standards.package_contract.payload import JsonObject, ProviderEffect

_ROOT = Path(__file__).resolve().parents[2]


def test_managed_markdown_snapshot_spans_all_packages_while_local_units_stay_local() -> None:
    lock = parse_lock((_ROOT / ".standards/lock.toml").read_bytes())
    markdown_units = cast(
        "list[JsonObject]", command_resolution.managed_markdown_unit_snapshot(lock)
    )
    assert {(item["target"], item["scope"]) for item in markdown_units} == {
        (target, f"block:{owner}")
        for target in ("AGENTS.md", "CLAUDE.md")
        for owner in ("agent-handoff", "markdown-tooling", "python-tooling")
    }
    local_units = cast(
        "list[JsonObject]",
        command_resolution.managed_unit_snapshot(lock, "agent-handoff"),
    )
    assert not any(item["scope"] == "block:markdown-tooling" for item in local_units)
    assert not any(item["scope"] == "block:python-tooling" for item in local_units)


@pytest.fixture(scope="module")
def distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    installed = tmp_path_factory.mktemp("agent-handoff-v2") / "project_standards"
    shutil.copytree(_ROOT / "src/project_standards", installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _consumer(
    tmp_path: Path,
    distribution: InstalledDistribution,
    *,
    version: str | None = None,
) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "agent-handoff", True)
    if version is not None:
        set_standard_selection(repo, "agent-handoff", version=version)
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    return repo


def _selected_agent_handoff_version(repo: Path) -> str:
    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    return lock.standards["agent-handoff"].resolved.value


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def _predecessor_catalog(text: str, standard_id: str, ceiling: str) -> str:
    """Re-render one installed catalog projection as an older release published it.

    Issue #91 is only reachable when the installed catalog advertises a newer
    selection than the consumer's lock records, so the fixture needs two genuine
    catalog generations rather than one catalog read twice.
    """
    document = tomllib.loads(text)
    limit = _version_key(ceiling)
    rendered = [
        f'schema_version = "{document["schema_version"]}"',
        f"catalog_major = {document['catalog_major']}",
    ]
    for entry in document["packages"]:
        version = cast("str", entry["version"])
        role = cast("str", entry["role"])
        if entry["id"] == standard_id:
            if _version_key(version) > limit:
                continue
            role = "default" if _version_key(version) == limit else "retained"
        rendered.extend(
            [
                "",
                "[[packages]]",
                f'id = "{entry["id"]}"',
                f'version = "{version}"',
                f'digest = "{entry["digest"]}"',
                f'role = "{role}"',
            ]
        )
    return "\n".join(rendered) + "\n"


@pytest.fixture(scope="module")
def predecessor_distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    """Install the tool as it stood while Agent Handoff 1.4 was the default."""
    installed = tmp_path_factory.mktemp("agent-handoff-predecessor") / "project_standards"
    shutil.copytree(_ROOT / "src/project_standards", installed, symlinks=False)
    catalog = installed / "catalogs/5.toml"
    catalog.write_text(
        _predecessor_catalog(catalog.read_text(encoding="utf-8"), "agent-handoff", "1.4"),
        encoding="utf-8",
    )
    return InstalledDistribution(installed, tool_release="5.0.0")


@pytest.fixture(scope="module")
def refreshed_distribution(distribution: InstalledDistribution) -> InstalledDistribution:
    """Present the full installed catalog as the newer release a consumer installs."""
    return InstalledDistribution(distribution.package_root, tool_release="5.1.0")


def _control_bytes(repo: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted((repo / ".standards").iterdir())
        if path.is_file()
    }


def test_legacy_report_before_catalog_refresh_reads_the_applied_lock(
    tmp_path: Path,
    predecessor_distribution: InstalledDistribution,
    refreshed_distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """TC-T4-001 (#91): a read-only command resolves the applied lock pre-refresh.

    The consumer is reconciled and consistent; only the freshly installed catalog
    advertises a newer selection. The documented pre-change inventory must run on
    the locked basis, disclose it, and change nothing.
    """
    command_resolution.reset_legacy_authority_warning()
    repo = _consumer(tmp_path, predecessor_distribution)
    assert _selected_agent_handoff_version(repo) == "1.4"
    (repo / "STATUS.md").write_text("legacy\n", encoding="utf-8")
    control = _control_bytes(repo)
    preview = plan_reconciliation(build_planner_request(repo, refreshed_distribution, frozenset()))
    assert preview.applicable, preview.findings

    assert (
        run(
            ["legacy-report", "--repo", str(repo), "--json"],
            distribution=refreshed_distribution,
        )
        == 0
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["standard_version"] == "1.4"
    assert report["findings"][0]["code"] == "AH-LEGACY-ROOT-STATUS"
    assert "agent-handoff@1.4" in captured.err
    assert _control_bytes(repo) == control


@pytest.mark.parametrize(
    ("command", "expected_code"),
    [("size-report", "AH-SIZE-CAP"), ("shape-check", "AH-SHAPE")],
)
def test_reports_between_enable_and_apply_read_the_desired_selection(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
    command: str,
    expected_code: str,
) -> None:
    """TC-T5-001 (#101): the documented pre-apply checkpoint runs before the write.

    The consumer has enabled Agent Handoff but not reconciled it, so the package
    is absent from the lock — the ordinary window UPGRADING.md sends a consumer
    into. A pre-existing knowledge document violates the byte cap; the runbook
    exists so that violation is routed to its owner before eager state is
    written, which requires the report to run here rather than after apply.
    """
    command_resolution.reset_legacy_authority_warning()
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "agent-handoff", True)
    state = repo / "docs/handoff/state.md"
    state.parent.mkdir(parents=True)
    state.write_text("# State\n\n" + "consumer knowledge " * 200 + "\n", encoding="utf-8")
    control = _control_bytes(repo)
    preview = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert preview.applicable, preview.findings

    assert run([command, "--repo", str(repo), "--json"], distribution=distribution) == 1

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert any(item["code"] == expected_code for item in report["findings"])
    assert f"agent-handoff@{report['standard_version']}" in captured.err
    assert "reconcile --apply" in captured.err
    assert _control_bytes(repo) == control
    assert not (repo / ".agents").exists()


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
    assert report["standard_version"] == _selected_agent_handoff_version(repo)
    assert report["findings"] == []


def test_selected_predecessor_provider_redacts_and_locates_missing_link(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution, version="1.4")
    state = repo / "docs/handoff/state.md"
    secret_target = "docs/sk-live-consumer-secret.md"
    secret_heading = "sk-live-consumer-heading"
    link = f"- [Missing]({secret_target})"
    content = (
        state.read_text(encoding="utf-8").rstrip()
        + f"\n\n## {secret_heading}\n\n{link}\n\n{link}\n"
    )
    state.write_text(content, encoding="utf-8")

    assert run(["validate", "--repo", str(repo), "--json"], distribution=distribution) == 1

    payload = json.loads(capsys.readouterr().out)
    links = [item for item in payload["findings"] if item["code"] == "AH-REFERENCE-MISSING"]
    assert len(links) == 2
    assert {item["path"] for item in links} == {"docs/handoff/state.md"}
    assert {item["locus"] for item in links} == {"Markdown link"}
    assert [item["line"] for item in links] == [
        index + 1 for index, line in enumerate(content.splitlines()) if line == link
    ]
    assert all(item["column"] > 0 for item in links)
    shape = next(item for item in payload["findings"] if item["code"] == "AH-SHAPE")
    assert shape["locus"] == "section heading"
    assert shape["line"] == content.splitlines().index(f"## {secret_heading}") + 1
    assert secret_target not in json.dumps(payload)
    assert secret_heading not in json.dumps(payload)


def test_selected_predecessor_provider_enriches_size_measure_and_limit(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution, version="1.4")
    (repo / "docs/handoff/state.md").write_text("x" * 2050, encoding="utf-8")

    assert run(["size-report", "--repo", str(repo), "--json"], distribution=distribution) == 1

    payload = json.loads(capsys.readouterr().out)
    finding = next(item for item in payload["findings"] if item["code"] == "AH-SIZE-CAP")
    assert finding["path"] == "docs/handoff/state.md"
    assert finding["locus"] == "byte budget"
    assert finding["observed"] == 2050
    assert finding["limit"] == 2048


def test_exact_older_provider_uses_its_raw_size_measure(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution, version="1.3")
    agents = repo / "AGENTS.md"
    content = agents.read_bytes()
    content += b"\n" + (b"x" * (3500 - len(content) - 1))
    assert len(content) == 3500
    agents.write_bytes(content)

    assert run(["size-report", "--repo", str(repo), "--json"], distribution=distribution) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["standard_version"] == "1.3"
    finding = next(item for item in payload["findings"] if item["code"] == "AH-SIZE-TARGET")
    assert finding["path"] == "AGENTS.md"
    assert finding["observed"] == 3500
    assert finding["limit"] == 3480


def test_selected_provider_preserves_structural_fields_in_json_and_text(
    tmp_path: Path,
    distribution: InstalledDistribution,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    finding = ControlFinding(
        code="AH-SHAPE",
        severity="error",
        standard_id="agent-handoff",
        version=_selected_agent_handoff_version(repo),
        path="docs/TODO.md",
        identity="shape",
        message="bullet exceeds its configured character limit",
        hint="condense the bullet",
        line=22,
        column=7,
        locus="document bullet",
        observed=191,
        limit=160,
    )

    def structured_findings(*_args: object, **_kwargs: object) -> ProviderResult:
        return ProviderResult(ProviderEffect.FINDINGS, findings=(finding,))

    monkeypatch.setattr(agent_handoff_cli, "invoke_selected_provider", structured_findings)

    assert run(["validate", "--repo", str(repo), "--json"], distribution=distribution) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert captured.err == ""
    assert payload["schema_version"] == "1.1"
    assert payload["findings"][0] == {
        "code": "AH-SHAPE",
        "severity": "error",
        "path": "docs/TODO.md",
        "locus": "document bullet",
        "message": "bullet exceeds its configured character limit",
        "guidance": "condense the bullet",
        "line": 22,
        "column": 7,
        "observed": 191,
        "limit": 160,
    }

    assert run(["validate", "--repo", str(repo)], distribution=distribution) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "docs/TODO.md:22:7" in captured.err
    assert "document bullet" in captured.err
    assert "observed: 191" in captured.err
    assert "limit: 160" in captured.err


@pytest.mark.parametrize("command", ["size-report", "shape-check"])
def test_unified_policy_view_help__requested_alias__uses_alias_name(
    command: str,
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)

    with pytest.raises(SystemExit) as exc_info:
        run([command, "--repo", str(repo), "--help"], distribution=distribution)

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert f"usage: project-standards agent-handoff {command}" in output
    assert "--view" not in output


@pytest.mark.parametrize(
    ("command", "view_argument"),
    [("size-report", "shape"), ("shape-check", "size")],
)
def test_unified_policy_view_alias_rejects_view_override(
    command: str,
    view_argument: str,
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)

    assert (
        run(
            [command, "--repo", str(repo), "--view", view_argument],
            distribution=distribution,
        )
        == 2
    )
    assert "unrecognized arguments: --view" in capsys.readouterr().err


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
    assert all(item["code"].startswith("AH-SIZE") for item in report["findings"])


def test_unified_shape_check_emits_only_shape_findings(
    tmp_path: Path,
    distribution: InstalledDistribution,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _consumer(tmp_path, distribution)
    (repo / "docs/handoff/state.md").write_bytes(b"x" * 3000)

    assert run(["shape-check", "--repo", str(repo), "--json"], distribution=distribution) == 1
    report = json.loads(capsys.readouterr().out)

    assert report["findings"]
    assert all(item["code"].startswith("AH-SHAPE") for item in report["findings"])


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

    assert report["standard_version"] == _selected_agent_handoff_version(repo)
    assert [(item["path"], item["locus"]) for item in references] == [
        ("docs/handoff/architecture.md", "Markdown link"),
        ("docs/handoff/architecture.md", "Markdown link"),
        ("docs/handoff/architecture.md", "Markdown link"),
    ]
    assert len({item["line"] for item in references}) == 3
    assert all(item["column"] > 0 for item in references)


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
    assert report["standard_version"] == _selected_agent_handoff_version(repo)


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
        assert captured.err == (
            "error: legacy.txt: legacy evidence requires review (locus: legacy inventory)\n"
        )
