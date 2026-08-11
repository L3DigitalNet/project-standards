from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import project_standards.specs.cli as spec_cli
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import AuthoringApplyResult
from project_standards.control_plane.schemas import MutationPlanSchema
from project_standards.specs.cli import run
from tests.test_spec_selected_routing import (
    _enable_selected,  # pyright: ignore[reportPrivateUsage]
    _installed_distribution,  # pyright: ignore[reportPrivateUsage]
)


@pytest.fixture
def selected_repo(tmp_path: Path) -> tuple[Path, InstalledDistribution]:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path, version="1.9")
    initialize_control_plane(repo, "5", distribution=distribution)
    _enable_selected(repo, distribution)
    return repo, distribution


def _source(repo: Path, content: bytes = b"# 2 Scope\nlegacy body\n") -> Path:
    source = repo / "docs/legacy.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    return source


def _invoke(
    repo: Path,
    distribution: InstalledDistribution,
    *extra: str,
) -> int:
    return run(
        [
            "import",
            "docs/legacy.md",
            "--output",
            "docs/imported.md",
            "--id",
            "SPEC-AB12",
            *extra,
        ],
        repo=repo,
        distribution=distribution,
    )


def test_import_preview__repeated_json__is_deterministic_and_read_only(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, distribution = selected_repo
    source = _source(repo, b"intro\n# 2 Scope\nlegacy body\n")
    before = source.read_bytes()

    assert _invoke(repo, distribution, "--json") == 0
    first_text = capsys.readouterr().out
    assert _invoke(repo, distribution, "--json") == 0
    second_text = capsys.readouterr().out
    first = json.loads(first_text)

    assert first_text == second_text
    assert set(first) == {
        "schema_version",
        "ok",
        "written",
        "source",
        "target",
        "provider",
        "spec_id",
        "plan_digest",
        "mappings",
        "review",
        "diagnostics",
        "error",
    }
    assert first["schema_version"] == "project-standards-spec-import-v1"
    assert first["ok"] is True
    assert first["written"] is False
    assert first["source"] == "docs/legacy.md"
    assert first["target"] == "docs/imported.md"
    assert first["provider"] == "project-spec@1.9/fix"
    assert first["spec_id"] == "SPEC-AB12"
    assert first["plan_digest"].startswith("sha256:")
    assert first["mappings"] == [{"ordinal": 1, "destination": "2"}]
    assert first["review"] == [
        {"ordinal": 0, "classification": "preamble", "code": "SPEC-IMPORT-PREAMBLE"}
    ]
    assert first["diagnostics"][0]["code"] == "SPEC-IMPORT-PREAMBLE"
    assert first["error"] is None
    assert source.read_bytes() == before
    assert not (repo / "docs/imported.md").exists()


def test_import_preview__human__reports_stable_review_contract(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, distribution = selected_repo
    _source(repo, b"unmapped preamble\n")

    assert _invoke(repo, distribution) == 0
    output = capsys.readouterr().out

    assert "source: docs/legacy.md" in output
    assert "target: docs/imported.md" in output
    assert "provider: project-spec@1.9/fix" in output
    assert "mapped: 0" in output
    assert "review: 1" in output
    assert "SPEC-IMPORT-PREAMBLE" in output
    assert "plan digest: sha256:" in output
    assert "written: false" in output


def test_import_apply__matching_digest__executes_same_plan_exactly_once(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, distribution = selected_repo
    source = _source(repo)
    assert _invoke(repo, distribution, "--json") == 0
    digest = cast(str, json.loads(capsys.readouterr().out)["plan_digest"])
    real_apply = spec_cli.apply_authoring_plan
    plans: list[MutationPlanSchema] = []

    def tracked_apply(root: Path, plan: MutationPlanSchema) -> AuthoringApplyResult:
        plans.append(plan)
        return real_apply(root, plan)

    monkeypatch.setattr(spec_cli, "apply_authoring_plan", tracked_apply)

    assert (
        _invoke(
            repo,
            distribution,
            "--apply",
            "--expected-plan-digest",
            digest,
            "--json",
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)

    assert result["written"] is True
    assert result["plan_digest"] == digest
    assert len(plans) == 1
    plan = plans[0]
    assert plan.import_report is not None
    assert plan.import_report.plan_digest.value == digest
    assert source.read_bytes() == b"# 2 Scope\nlegacy body\n"
    assert (repo / "docs/imported.md").is_file()


@pytest.mark.parametrize(
    ("extra", "code"),
    [
        pytest.param(["--apply"], "expected_digest_required", id="missing-digest"),
        pytest.param(
            ["--apply", "--expected-plan-digest", f"sha256:{'0' * 64}"],
            "plan_digest_mismatch",
            id="wrong-digest",
        ),
    ],
)
def test_import_apply__invalid_authorization__calls_executor_zero_times(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    extra: list[str],
    code: str,
) -> None:
    repo, distribution = selected_repo
    source = _source(repo)
    calls = 0

    def forbidden(_root: Path, _plan: MutationPlanSchema) -> AuthoringApplyResult:
        nonlocal calls
        calls += 1
        pytest.fail("executor must not run for an unauthorized digest")

    monkeypatch.setattr(spec_cli, "apply_authoring_plan", forbidden)

    assert _invoke(repo, distribution, *extra, "--json") == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert result["written"] is False
    assert result["error"]["code"] == code
    assert calls == 0
    assert source.read_bytes() == b"# 2 Scope\nlegacy body\n"
    assert not (repo / "docs/imported.md").exists()


def test_import_apply__source_changed_after_preview__refuses_without_executor(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, distribution = selected_repo
    source = _source(repo)
    assert _invoke(repo, distribution, "--json") == 0
    digest = cast(str, json.loads(capsys.readouterr().out)["plan_digest"])
    source.write_bytes(b"# 2 Scope\nchanged after preview\n")

    def forbidden(_root: Path, _plan: MutationPlanSchema) -> AuthoringApplyResult:
        pytest.fail("executor must not run for a stale digest")

    monkeypatch.setattr(spec_cli, "apply_authoring_plan", forbidden)

    assert (
        _invoke(
            repo,
            distribution,
            "--apply",
            "--expected-plan-digest",
            digest,
            "--json",
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["code"] == "plan_digest_mismatch"
    assert source.read_bytes() == b"# 2 Scope\nchanged after preview\n"
    assert not (repo / "docs/imported.md").exists()


@pytest.mark.parametrize(
    ("argv", "code"),
    [
        pytest.param(
            ["import", "docs/legacy.md", "--id", "SPEC-AB12", "--json"],
            "usage",
            id="missing-output",
        ),
        pytest.param(
            [
                "import",
                "docs/legacy.md",
                "--output",
                "docs/imported.md",
                "--json",
            ],
            "usage",
            id="missing-id",
        ),
        pytest.param(
            [
                "import",
                "docs/legacy.md",
                "--output",
                "docs/imported.md",
                "--id",
                "invalid",
                "--json",
            ],
            "bad_id",
            id="invalid-id",
        ),
        pytest.param(
            [
                "import",
                "docs/legacy.md",
                "--output",
                "docs/legacy.md",
                "--id",
                "SPEC-AB12",
                "--json",
            ],
            "path_alias",
            id="same-path",
        ),
    ],
)
def test_import_refusal__invalid_request__has_stable_json_and_no_write(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    code: str,
) -> None:
    repo, distribution = selected_repo
    source = _source(repo)

    assert run(argv, repo=repo, distribution=distribution) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert result["written"] is False
    assert result["error"]["code"] == code
    assert source.read_bytes() == b"# 2 Scope\nlegacy body\n"


def test_import_refusal__source_or_target_symlink__does_not_follow_alias(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, distribution = selected_repo
    real_source = _source(repo)
    (repo / "docs/source-link.md").symlink_to(real_source)
    target = repo / "docs/target-link.md"
    target.symlink_to(repo / "outside.md")

    for source, output in (
        ("docs/source-link.md", "docs/imported.md"),
        ("docs/legacy.md", "docs/target-link.md"),
    ):
        assert (
            run(
                [
                    "import",
                    source,
                    "--output",
                    output,
                    "--id",
                    "SPEC-AB12",
                    "--json",
                ],
                repo=repo,
                distribution=distribution,
            )
            == 2
        )
        result = json.loads(capsys.readouterr().out)
        assert result["error"]["code"] == "unsafe_path"
    assert not (repo / "outside.md").exists()


def test_import_apply__executor_fault__preserves_target_and_cleans_staging(
    selected_repo: tuple[Path, InstalledDistribution],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, distribution = selected_repo
    _source(repo)
    target = repo / "docs/imported.md"
    target.write_bytes(b"prior target\n")
    assert _invoke(repo, distribution, "--json") == 0
    digest = cast(str, json.loads(capsys.readouterr().out)["plan_digest"])

    def fault(_root: Path, _plan: MutationPlanSchema) -> AuthoringApplyResult:
        return AuthoringApplyResult(
            success=False,
            applied_targets=(),
            error_code="injected-fault",
        )

    monkeypatch.setattr(spec_cli, "apply_authoring_plan", fault)

    assert (
        _invoke(
            repo,
            distribution,
            "--apply",
            "--expected-plan-digest",
            digest,
            "--json",
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["code"] == "write_failed"
    assert target.read_bytes() == b"prior target\n"
    assert list(target.parent.glob(".project-standards-authoring-*")) == []
