from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.cli import main as project_standards_main
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import run, validate_repository
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, ApplyResult
from project_standards.control_plane.providers import ProviderInvocation, ProviderResult
from project_standards.package_contract.payload import ProviderEffect
from tests.control_plane.helpers import installed_distribution


def _use_distribution(
    monkeypatch: pytest.MonkeyPatch,
    distribution: InstalledDistribution,
) -> None:
    def current() -> InstalledDistribution:
        return distribution

    monkeypatch.setattr(InstalledDistribution, "current", staticmethod(current))


def test_reconcile_help_documents_mutation_and_recovery_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["--help"]) == 0

    output = capsys.readouterr().out
    assert "--check" in output
    assert "--apply" in output
    assert "--allow-major STANDARD_ID@MAJOR" in output
    assert "--repair-state" in output
    assert "--json" in output


def test_top_level_dispatches_reconcile_and_advertises_it(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    _use_distribution(monkeypatch, distribution)

    assert project_standards_main(["reconcile", "--repo", str(repo), "--json"]) == 0
    assert '"mode": "plan"' in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        project_standards_main(["--help"])
    assert exc_info.value.code == 0
    assert "reconcile" in capsys.readouterr().out


def test_init_json_reports_created_and_idempotent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = installed_distribution(tmp_path)
    _use_distribution(monkeypatch, distribution)

    assert (
        project_standards_main(["init", "--catalog", "5", "--repo", str(tmp_path), "--json"]) == 0
    )
    assert '"created": true' in capsys.readouterr().out

    assert (
        project_standards_main(["init", "--catalog", "5", "--repo", str(tmp_path), "--json"]) == 0
    )
    assert '"created": false' in capsys.readouterr().out

    assert project_standards_main(["init", "--catalog", "05", "--json"]) == 2
    invalid = capsys.readouterr()
    assert invalid.err == ""
    assert '"code": "CP-ARGUMENT"' in invalid.out


def test_legacy_list_and_adopt_emit_v5_deprecation_notices(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert project_standards_main(["list"]) == 0
    listed = capsys.readouterr()
    assert "deprecated" in listed.err
    assert "project-standards standards list" in listed.err

    assert (
        project_standards_main(
            ["adopt", "markdown-frontmatter", "--dest", str(tmp_path), "--dry-run"]
        )
        == 0
    )
    adopted = capsys.readouterr()
    assert "deprecated" in adopted.err
    assert "control plane" in adopted.err
    assert not (tmp_path / ".standards").exists()


def test_v5_adopt_wrapper_matches_explicit_init_enable_and_apply(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = installed_distribution(tmp_path)
    catalog_path = distribution.package_root / "catalogs/5.toml"
    catalog_text = catalog_path.read_text(encoding="utf-8")
    catalog_path.write_text(
        catalog_text.replace('role = "retained"', 'role = "__first__"', 1)
        .replace('role = "default"', 'role = "retained"', 1)
        .replace('role = "__first__"', 'role = "default"', 1),
        encoding="utf-8",
    )
    _use_distribution(monkeypatch, distribution)
    explicit = tmp_path / "explicit"
    wrapped = tmp_path / "wrapped"
    explicit.mkdir()
    wrapped.mkdir()

    initialize_control_plane(explicit, "5", distribution=distribution)
    set_standard_enabled(explicit, "alpha", True)
    assert run(["--repo", str(explicit), "--apply"], distribution=distribution) == 0
    capsys.readouterr()

    assert project_standards_main(["adopt", "alpha", "--dest", str(wrapped)]) == 0
    capsys.readouterr()

    expected_paths = [
        ".standards/config.toml",
        ".standards/catalog.toml",
        ".standards/lock.toml",
    ]
    for relative in expected_paths:
        assert (wrapped / relative).read_bytes() == (explicit / relative).read_bytes()


def test_v5_adopt_wrapper_reports_control_plane_refusal_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = installed_distribution(tmp_path)
    _use_distribution(monkeypatch, distribution)
    (tmp_path / ".project-standards.yml").write_text("legacy: true\n", encoding="utf-8")

    assert project_standards_main(["adopt", "alpha", "--dest", str(tmp_path)]) == 2
    assert "legacy standards authority" in capsys.readouterr().err


def test_v5_adopt_never_falls_back_from_present_invalid_or_nonselectable_catalog(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = installed_distribution(tmp_path)
    _use_distribution(monkeypatch, distribution)

    assert project_standards_main(["adopt", "gamma", "--dest", str(tmp_path)]) == 2
    assert "not consumer-selectable" in capsys.readouterr().err

    catalog = distribution.package_root / "catalogs/5.toml"
    catalog.write_text("not valid toml = [\n", encoding="utf-8")

    assert project_standards_main(["adopt", "alpha", "--dest", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "installed V2 catalog" in error
    assert "unknown standard" not in error


def test_validate_repository_reports_unified_drift_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)

    assert validate_repository(repo, distribution=distribution) == 0
    before = (repo / ".standards/lock.toml").read_bytes()
    (repo / ".standards/config.toml").write_text(
        '[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n\n'
        '[standards.alpha]\nenabled = true\nversion = "3.0"\n',
        encoding="utf-8",
    )

    assert validate_repository(repo, distribution=distribution) == 1
    assert "authorization" in capsys.readouterr().err
    assert (repo / ".standards/lock.toml").read_bytes() == before


def test_top_level_validate_warns_for_legacy_and_rejects_dual_authority(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = installed_distribution(tmp_path)
    _use_distribution(monkeypatch, distribution)

    def clean_validator(_args: list[str] | None = None) -> int:
        return 0

    monkeypatch.setattr("project_standards.cli.validate_frontmatter.main", clean_validator)
    monkeypatch.setattr("project_standards.cli.validate_id.main", clean_validator)
    monkeypatch.setattr("project_standards.cli.validate_references.main", clean_validator)
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / ".project-standards.yml"
    legacy.write_text("legacy: true\n", encoding="utf-8")

    assert project_standards_main(["validate"]) == 0
    assert "legacy" in capsys.readouterr().err

    legacy.unlink()
    initialize_control_plane(tmp_path, "5", distribution=distribution)
    legacy.write_text("legacy: true\n", encoding="utf-8")

    assert project_standards_main(["validate"]) == 1
    assert "both exist" in capsys.readouterr().err


def test_reconcile_json_clean_plan_dirty_apply_and_fixed_point(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)

    assert run(["--repo", str(repo), "--json"], distribution=distribution) == 0
    clean = capsys.readouterr().out
    assert '"mode": "plan"' in clean
    assert '"drift": false' in clean

    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("enabled = true\n", encoding="utf-8")

    def render(_invocation: ProviderInvocation) -> ProviderResult:
        return ProviderResult(
            ProviderEffect.CONTENT,
            content=b"[alpha]\ngenerated = true\n",
        )

    monkeypatch.setattr("project_standards.control_plane.planner.invoke_provider", render)
    set_standard_enabled(repo, "alpha", True)
    assert run(["--repo", str(repo), "--check", "--json"], distribution=distribution) == 1
    dirty = capsys.readouterr().out
    assert '"mode": "check"' in dirty
    assert '"drift": true' in dirty
    assert '"target": ".editorconfig"' in dirty

    assert run(["--repo", str(repo), "--apply", "--json"], distribution=distribution) == 0
    applied = capsys.readouterr().out
    assert '"mode": "apply"' in applied
    assert '"success": true' in applied

    assert run(["--repo", str(repo), "--check", "--json"], distribution=distribution) == 0
    fixed = capsys.readouterr().out
    assert '"drift": false' in fixed


def test_reconcile_candidate_requires_matching_allow_major(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    from project_standards.control_plane.config_edit import set_standard_selection

    set_standard_selection(repo, "alpha", enabled=True, version="3.0")

    assert run(["--repo", str(repo), "--json"], distribution=distribution) == 1
    denied = capsys.readouterr().out
    assert "CP-RESOLVE-MAJOR-AUTH" in denied

    assert (
        run(
            ["--repo", str(repo), "--allow-major", "alpha@3", "--json"],
            distribution=distribution,
        )
        == 1
    )
    allowed = capsys.readouterr().out
    assert '"applicable": true' in allowed


def test_reconcile_missing_lock_requires_repair_and_apply(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    (repo / ".standards/lock.toml").unlink()

    assert run(["--repo", str(repo), "--json"], distribution=distribution) == 1
    refused = capsys.readouterr().out
    assert "CP-REPAIR-REQUIRED" in refused

    assert run(["--repo", str(repo), "--repair-state", "--json"], distribution=distribution) == 1
    preview = capsys.readouterr().out
    assert '"recovery_kind": "missing-lock"' in preview
    assert not (repo / ".standards/lock.toml").exists()

    assert (
        run(
            ["--repo", str(repo), "--repair-state", "--apply", "--json"],
            distribution=distribution,
        )
        == 0
    )
    applied = capsys.readouterr().out
    assert '"success": true' in applied
    assert (repo / ".standards/lock.toml").is_file()


def test_reconcile_human_plan_apply_and_authorization_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)

    assert run(["--repo", str(repo)], distribution=distribution) == 0
    assert "reconciled" in capsys.readouterr().out
    assert run(["--repo", str(repo), "--repair-state"], distribution=distribution) == 2
    assert "not in a sanctioned" in capsys.readouterr().err

    def fail_apply(_request: ApplyRequest) -> ApplyResult:
        return ApplyResult(False, (), False, "CP-INJECTED")

    monkeypatch.setattr(
        "project_standards.control_plane.cli.apply_reconciliation",
        fail_apply,
    )
    assert run(["--repo", str(repo), "--apply"], distribution=distribution) == 1
    assert "CP-INJECTED" in capsys.readouterr().err

    (repo / ".standards/config.toml").write_text(
        '[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n\n'
        '[standards.alpha]\nenabled = true\nversion = "3.0"\n',
        encoding="utf-8",
    )
    assert run(["--repo", str(repo)], distribution=distribution) == 1
    assert "CP-RESOLVE-MAJOR-AUTH" in capsys.readouterr().err


def test_reconcile_human_recovery_preview_success_and_refusal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    (repo / ".standards/lock.toml").unlink()

    assert run(["--repo", str(repo), "--repair-state"], distribution=distribution) == 1
    assert "would restore" in capsys.readouterr().out
    assert (
        run(
            ["--repo", str(repo), "--repair-state", "--apply"],
            distribution=distribution,
        )
        == 0
    )
    assert "Recovered" in capsys.readouterr().out

    (repo / ".standards/config.toml").unlink()
    assert run(["--repo", str(repo), "--repair-state"], distribution=distribution) == 1
    assert "CP-MISSING-CONFIG" in capsys.readouterr().err
    assert (
        run(
            ["--repo", str(repo), "--repair-state", "--apply"],
            distribution=distribution,
        )
        == 1
    )
    assert "recovery failed" in capsys.readouterr().err


def test_validate_repository_reports_compatible_config_digest_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    (repo / ".standards/config.toml").write_text(
        '[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n\n'
        '[standards.alpha]\nenabled = false\nversion = "latest"\n',
        encoding="utf-8",
    )

    assert validate_repository(repo, distribution=distribution) == 1
    assert "CP-DRIFT" in capsys.readouterr().err


@pytest.mark.parametrize(
    "arguments",
    [
        ["--check", "--apply"],
        ["--allow-major", "alpha"],
        ["--allow-major", "alpha@0"],
        ["--repair-state", "--apply", "--check"],
    ],
)
def test_reconcile_bad_arguments_exit_two(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(arguments) == 2
    assert "error:" in capsys.readouterr().err
