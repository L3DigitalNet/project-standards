from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

import project_standards.agent_handoff.validation as validation
from project_standards.agent_handoff.integrations.links import (
    _normalized_link_targets,  # pyright: ignore[reportPrivateUsage]  # focused internal contract
)
from project_standards.agent_handoff.model import Finding, Harness, StartupMode
from project_standards.agent_handoff.paths import RepositoryRoot
from project_standards.agent_handoff.planning import apply_adoption, plan_adoption
from project_standards.agent_handoff.policy import HandoffPolicy, load_policy
from project_standards.agent_handoff.validation import (
    drift_check,
    shape_check,
    size_report,
    validate_repository,
)
from project_standards.cli import main

POLICY_PATH = (
    Path(__file__).parents[2] / "src/project_standards/bundles/agent-handoff/resources/policy.toml"
)


def _replace_shape_pattern(pattern: str) -> HandoffPolicy:
    policy = load_policy(POLICY_PATH)
    bug_policy = next(
        document for document in policy.shape.documents.values() if document.profile == "bug-record"
    )
    shape = policy.shape.model_copy(update={"documents": {pattern: bug_policy}})
    return policy.model_copy(update={"shape": shape})


def _fixed_policy_loader(
    policy: HandoffPolicy,
) -> Callable[[list[Finding]], HandoffPolicy]:
    def load(_findings: list[Finding]) -> HandoffPolicy:
        return policy

    return load


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


def test_missing_local_markdown_link_is_reported(tmp_path: Path) -> None:
    _adopt(tmp_path)
    state = tmp_path / "docs/handoff/state.md"
    state.write_text(
        state.read_text(encoding="utf-8") + "\n- [Missing](docs/missing.md)\n",
        encoding="utf-8",
    )

    assert any(
        finding.code == "AH-REFERENCE-MISSING" and finding.locus == "Markdown link: docs/missing.md"
        for finding in validate_repository(RepositoryRoot(tmp_path))
    )


def test_reference_validation__empty_targets__reports_missing_findings(tmp_path: Path) -> None:
    _adopt(tmp_path)
    state = tmp_path / "docs/handoff/state.md"
    state.write_text(
        state.read_text(encoding="utf-8")
        + "\n[Literal empty]()\n"
        + "[Whitespace]( )\n"
        + "[Angle brackets](<>)\n",
        encoding="utf-8",
    )

    missing = [
        finding
        for finding in validate_repository(RepositoryRoot(tmp_path))
        if finding.code == "AH-REFERENCE-MISSING"
    ]

    assert len(missing) == 3
    assert all(finding.locus == "Markdown link: " for finding in missing)


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        pytest.param("[Literal empty]()", ("",), id="literal-empty"),
        pytest.param("[Whitespace]( )", ("",), id="whitespace-empty"),
        pytest.param("[Angle brackets](<>)", ("",), id="angle-empty"),
        pytest.param(
            "[Angle path](<docs/handoff/path with spaces.md>)",
            ("docs/handoff/path with spaces.md",),
            id="angle-path-with-spaces",
        ),
        pytest.param(
            '[Angle path](<docs/handoff/path with spaces.md> "Reference")',
            ("docs/handoff/path with spaces.md",),
            id="angle-path-with-title",
        ),
        pytest.param(
            "[Local](docs/handoff/local.md)",
            ("docs/handoff/local.md",),
            id="ordinary-local",
        ),
        pytest.param(
            "[URL](https://example.invalid/reference)",
            ("https://example.invalid/reference",),
            id="url",
        ),
        pytest.param(
            "[Mail](mailto:owner@example.invalid)",
            ("mailto:owner@example.invalid",),
            id="mail",
        ),
        pytest.param("[Fragment](#current)", ("#current",), id="fragment"),
    ],
)
def test_link_target_normalizer__supported_forms__preserves_caller_decisions(
    markdown: str, expected: tuple[str, ...]
) -> None:
    assert tuple(_normalized_link_targets(markdown)) == expected


def test_reference_validation_decodes_urls_and_ignores_code_examples(tmp_path: Path) -> None:
    _adopt(tmp_path)
    target = tmp_path / "docs with spaces/reference.md"
    target.parent.mkdir()
    target.write_text("# Reference\n", encoding="utf-8")
    local = tmp_path / "docs/handoff/local-reference.md"
    local.write_text("# Local reference\n", encoding="utf-8")
    architecture = tmp_path / "docs/handoff/architecture.md"
    architecture.write_text(
        architecture.read_text(encoding="utf-8")
        + "\n[Encoded path](docs%20with%20spaces/reference.md)\n"
        + "\n[Angle path](<docs with spaces/reference.md>)\n"
        + '\n[Angle path with title](<docs with spaces/reference.md> "Reference")\n'
        + "\n[Local path](local-reference.md)\n"
        + "\n[URL](https://example.invalid/reference)\n"
        + "\n[Mail](mailto:owner@example.invalid)\n"
        + "\n[Fragment](#current)\n"
        + "\n`[inline example](url)`\n"
        + "\n```markdown\n[fenced example](missing.md)\n```\n"
        + "\n    [indented example](also-missing.md)\n",
        encoding="utf-8",
    )

    findings = validate_repository(RepositoryRoot(tmp_path))

    assert not any(finding.code == "AH-REFERENCE-MISSING" for finding in findings)


def test_size_and_shape_views_project_policy_findings(tmp_path: Path) -> None:
    _adopt(tmp_path)
    state = tmp_path / "docs/handoff/state.md"
    state.write_text("x" * 2050, encoding="utf-8")

    assert any(finding.code == "AH-SIZE-CAP" for finding in size_report(RepositoryRoot(tmp_path)))
    assert any(finding.code == "AH-SHAPE" for finding in shape_check(RepositoryRoot(tmp_path)))


def test_shape_check_excludes_index_but_checks_numbered_bug(tmp_path: Path) -> None:
    _adopt(tmp_path)
    bugs = tmp_path / "docs/handoff/bugs"
    (bugs / "INDEX.md").write_text("# Bug Index\n", encoding="utf-8")
    (bugs / "001-test.md").write_text(
        "# Bug\n\n## Cause\n\nCause.\n\n## Fix\n\nFix.\n",
        encoding="utf-8",
    )

    findings = shape_check(RepositoryRoot(tmp_path))

    assert any(finding.path == "docs/handoff/bugs/001-test.md" for finding in findings)
    assert not any(finding.path == "docs/handoff/bugs/INDEX.md" for finding in findings)


def test_shape_check_treats_bracket_only_filename_as_glob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _adopt(tmp_path)
    bug = tmp_path / "docs/handoff/bugs/1.md"
    bug.write_text("# Bug\n", encoding="utf-8")
    policy = _replace_shape_pattern("docs/handoff/bugs/[0-9].md")
    monkeypatch.setattr(validation, "_load_policy", _fixed_policy_loader(policy))

    findings = shape_check(RepositoryRoot(tmp_path))

    assert any(
        finding.code == "AH-SHAPE" and finding.path.endswith("/1.md") for finding in findings
    )


def test_shape_check_rejects_glob_in_directory_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _adopt(tmp_path)
    policy = _replace_shape_pattern("docs/handoff/*/[0-9].md")
    monkeypatch.setattr(validation, "_load_policy", _fixed_policy_loader(policy))

    findings = shape_check(RepositoryRoot(tmp_path))

    assert any(
        finding.code == "AH-PATH-BOUNDARY" and finding.path == "docs/handoff/*/[0-9].md"
        for finding in findings
    )


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
