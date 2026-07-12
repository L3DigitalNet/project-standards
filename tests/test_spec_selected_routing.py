from __future__ import annotations

import json
import os
import shutil
import socket
import stat
from pathlib import Path

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, ProviderResult
from project_standards.control_plane.snapshot import RepositorySnapshot
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.projection import sync_payload_projection
from project_standards.specs.cli import run
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[1]
_FAMILY = _ROOT / "standards/project-spec"
_PAYLOAD = _FAMILY / "versions/1.1"


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    integrity = validate_payload_integrity(_PAYLOAD, manifest)
    return InstalledPayload(_PAYLOAD, manifest, integrity)


def _installed_distribution(tmp_path: Path) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    repository = copy_minimal_repository(fixture)
    family = repository / "standards/project-spec"
    shutil.copytree(_FAMILY, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "project-spec"
name = "Project Specification Standard"
summary = "Tiered version-selected project specifications."
status = "active"

[[versions]]
version = "1.1"
payload = "versions/1.1/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "project-spec"
version = "1.1"
digest = "{payload.integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def test_validate_routes_through_enabled_selected_payload(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    spec = repo / "docs/specs/example.md"
    spec.parent.mkdir(parents=True)
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    assert run(["validate", "--json"], repo=repo, distribution=distribution) == 0

    result = json.loads(capsys.readouterr().out)
    assert result == [{"file": "docs/specs/example.md", "ok": True, "findings": []}]


def test_selected_validate_and_lint_do_not_call_legacy_validators(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    spec = repo / "spec.md"
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    def fail_legacy(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy validate/lint path executed")

    monkeypatch.setattr("project_standards.specs.cli.validate_document", fail_legacy)
    monkeypatch.setattr("project_standards.specs.cli.lint_document", fail_legacy)

    assert run(["validate", "spec.md"], repo=repo, distribution=distribution) == 0
    assert run(["lint", "spec.md"], repo=repo, distribution=distribution) == 0


def test_selected_command_refuses_a_disabled_project_spec_package(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    spec = repo / "spec.md"
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    assert run(["validate", str(spec)], repo=repo, distribution=distribution) == 2

    assert "project-spec package is disabled or not selected" in capsys.readouterr().err


def test_v5_legacy_only_state_explicitly_uses_the_legacy_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    spec = repo / "spec.md"
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())
    (repo / ".project-standards.yml").write_text(
        "spec:\n  include: ['spec.md']\n",
        encoding="utf-8",
    )

    def fail_provider(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("selected provider path executed")

    monkeypatch.setattr("project_standards.specs.cli.invoke_provider", fail_provider)

    assert (
        run(
            ["validate", str(spec), "--config", str(repo / ".project-standards.yml")],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )


def test_extract_uses_the_selected_provider_and_preserves_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    spec = repo / "spec.md"
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    def fail_legacy(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy extract path executed")

    monkeypatch.setattr("project_standards.specs.cli.extract_slice", fail_legacy)

    assert run(["extract", "spec.md", "§7", "--json"], repo=repo, distribution=distribution) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["file"] == "spec.md"
    assert result["selector"] == "§7"
    assert result["found"] is True
    assert result["kind"] == "section"
    assert result["markdown"].startswith("## 7. Requirements")


def test_next_uses_the_selected_provider_and_preserves_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    spec = repo / "spec.md"
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    def fail_legacy(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy next path executed")

    monkeypatch.setattr("project_standards.specs.cli.next_free_id", fail_legacy)

    assert run(["next", "spec.md", "FR", "--json"], repo=repo, distribution=distribution) == 0

    assert json.loads(capsys.readouterr().out) == {
        "file": "spec.md",
        "prefix": "FR",
        "next_id": "FR-003",
    }


def test_selected_next_preserves_invalid_prefix_refusal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    spec = repo / "spec.md"
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    assert run(["next", "spec.md", "NOPE"], repo=repo, distribution=distribution) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown prefix 'NOPE'" in captured.err
    assert "Traceback" not in captured.err


def test_selected_validate_reports_provider_config_refusal_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    config = repo / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[standards.project-spec.config]\nreference_prefixes = ["FR"]\n',
        encoding="utf-8",
    )
    spec = repo / "spec.md"
    spec.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    assert run(["validate", "spec.md"], repo=repo, distribution=distribution) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "spec.reference_prefixes entry 'FR' is a canonical spec-local prefix" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("json_mode", [False, True])
def test_selected_upgrade_reports_provider_config_refusal_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    json_mode: bool,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    config = repo / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[standards.project-spec.config]\nreference_prefixes = ["FR"]\n',
        encoding="utf-8",
    )
    (repo / "spec.md").write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())
    argv = ["upgrade", "spec.md", "--to", "standard"]
    if json_mode:
        argv.append("--json")

    assert run(argv, repo=repo, distribution=distribution) == 2
    captured = capsys.readouterr()
    if json_mode:
        assert json.loads(captured.out)["code"] == "config_error"
    else:
        assert captured.out == ""
        assert "canonical spec-local prefix" in captured.err
    assert "Traceback" not in captured.err


def test_selected_validate_json_preserves_line_and_locus(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    spec = repo / "bad.md"
    spec.write_bytes((_ROOT / "tests/fixtures/specs/bad_dup_id.md").read_bytes())

    assert run(["validate", "--json", "bad.md"], repo=repo, distribution=distribution) == 1

    findings = json.loads(capsys.readouterr().out)[0]["findings"]
    duplicate = next(finding for finding in findings if finding["code"] == "SV-ID-DUP")
    assert duplicate["line"] is not None
    assert duplicate["locus"] == "FR-001"


def test_new_stdout_uses_render_preview_and_writes_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }

    def fail_legacy(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy scaffold path executed")

    def deny_network(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("selected preview attempted network access")

    monkeypatch.setattr("project_standards.specs.cli.scaffold", fail_legacy)
    monkeypatch.setattr(socket, "socket", deny_network)

    assert (
        run(
            [
                "new",
                "--profile",
                "light",
                "--stdout",
                "--id",
                "SPEC-7F3Q",
                "--title",
                "Preview",
            ],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )

    assert "spec_id: SPEC-7F3Q" in capsys.readouterr().out
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before


def test_new_write_applies_the_selected_scaffold_plan_through_the_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    target = repo / "docs/specs/new.md"

    def fail_direct_write(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy direct writer executed")

    monkeypatch.setattr("project_standards.specs.cli._safe_atomic_write", fail_direct_write)

    assert (
        run(
            ["new", "--profile", "light", "--id", "SPEC-7F3Q", "docs/specs/new.md"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )

    assert "spec_id: SPEC-7F3Q" in target.read_text(encoding="utf-8")


def test_selected_new_write_does_not_invoke_the_preview_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    calls: list[str] = []
    from project_standards.specs import cli as spec_cli

    real_invoke = spec_cli.invoke_provider

    def record(invocation: ProviderInvocation) -> ProviderResult:
        calls.append(invocation.provider_id)
        return real_invoke(invocation)

    monkeypatch.setattr(spec_cli, "invoke_provider", record)

    assert (
        run(
            ["new", "--profile", "light", "--id", "SPEC-7F3Q", "new.md"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )
    assert calls == ["scaffold"]


def test_selected_new_force_on_missing_target_remains_a_create(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)

    assert (
        run(
            ["new", "--profile", "light", "--id", "SPEC-7F3Q", "--force", "new.md"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )
    assert capsys.readouterr().out == "wrote new.md\n"
    assert (repo / "new.md").is_file()


def test_selected_new_refuses_explicit_absolute_target_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    outside = tmp_path / "outside/new.md"
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)

    def fail_direct_write(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy direct writer executed")

    monkeypatch.setattr("project_standards.specs.cli._safe_atomic_write", fail_direct_write)

    assert (
        run(
            ["new", "--profile", "light", "--id", "SPEC-7F3Q", str(outside)],
            repo=repo,
            distribution=distribution,
        )
        == 2
    )
    assert not outside.exists()


def test_selected_new_refuses_relative_escape_and_in_tree_symlink_parent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "link").symlink_to(outside, target_is_directory=True)
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)

    assert (
        run(
            ["new", "--profile", "light", "--id", "SPEC-7F3Q", "../escaped.md"],
            repo=repo,
            distribution=distribution,
        )
        == 2
    )
    assert not (tmp_path / "escaped.md").exists()
    assert (
        run(
            ["new", "--profile", "light", "--id", "SPEC-7F3Q", "link/spec.md"],
            repo=repo,
            distribution=distribution,
        )
        == 2
    )
    assert not (outside / "spec.md").exists()
    assert "symlink" in capsys.readouterr().err


def test_selected_new_file_mode_respects_umask(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    target = repo / "new.md"

    previous = os.umask(0o027)
    try:
        assert (
            run(
                ["new", "--profile", "light", "--id", "SPEC-7F3Q", "new.md"],
                repo=repo,
                distribution=distribution,
            )
            == 0
        )
    finally:
        os.umask(previous)
    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_upgrade_preview_uses_render_provider_and_writes_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    original = (_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes()
    source.write_bytes(original)

    def fail_legacy(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy upgrade path executed")

    monkeypatch.setattr("project_standards.specs.cli.upgrade_text", fail_legacy)

    assert (
        run(
            ["upgrade", "spec.md", "--to", "standard"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )

    assert "profile: standard" in capsys.readouterr().out
    assert source.read_bytes() == original


def test_upgrade_in_place_applies_selected_plan_through_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    source.write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())
    source.chmod(0o640)

    def fail_direct_write(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy direct writer executed")

    monkeypatch.setattr("project_standards.specs.cli._safe_atomic_write", fail_direct_write)

    assert (
        run(
            ["upgrade", "spec.md", "--to", "standard", "--in-place"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )

    assert "profile: standard" in source.read_text(encoding="utf-8")
    assert source.stat().st_mode & 0o777 == 0o640


def test_upgrade_in_place_refuses_to_replace_a_concurrent_edit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    source.write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())
    concurrent = source.read_text(encoding="utf-8") + "\n<!-- concurrent edit -->\n"
    from project_standards.specs import cli as spec_cli

    real_invoke = spec_cli.invoke_provider

    def race(invocation: ProviderInvocation) -> ProviderResult:
        result = real_invoke(invocation)
        if invocation.provider_id == "upgrade":
            source.write_text(concurrent, encoding="utf-8")
        return result

    monkeypatch.setattr(spec_cli, "invoke_provider", race)

    assert (
        run(
            ["upgrade", "spec.md", "--to", "standard", "--in-place", "--json"],
            repo=repo,
            distribution=distribution,
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["code"] == "write_failed"
    assert source.read_text(encoding="utf-8") == concurrent


def test_selected_upgrade_write_does_not_invoke_the_preview_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    source.write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())
    calls: list[str] = []
    from project_standards.specs import cli as spec_cli

    real_invoke = spec_cli.invoke_provider

    def record(invocation: ProviderInvocation) -> ProviderResult:
        calls.append(invocation.provider_id)
        return real_invoke(invocation)

    monkeypatch.setattr(spec_cli, "invoke_provider", record)

    assert (
        run(
            ["upgrade", "spec.md", "--to", "standard", "--in-place"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )
    assert calls == ["validate", "upgrade"]


def test_upgrade_output_applies_selected_plan_through_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    source.write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())
    output = repo / "upgraded.md"

    def fail_direct_write(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy direct writer executed")

    monkeypatch.setattr("project_standards.specs.cli._safe_atomic_write", fail_direct_write)

    assert (
        run(
            ["upgrade", "spec.md", "--to", "standard", "-o", "upgraded.md"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )
    assert "profile: standard" in output.read_text(encoding="utf-8")


def test_selected_upgrade_force_on_missing_output_remains_a_create(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    source.write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())

    assert (
        run(
            ["upgrade", "spec.md", "--to", "standard", "-o", "out.md", "--force"],
            repo=repo,
            distribution=distribution,
        )
        == 0
    )
    assert capsys.readouterr().out == "wrote out.md\n"
    assert "profile: standard" in (repo / "out.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "argv",
    [
        ["validate", "{path}"],
        ["lint", "{path}"],
        ["extract", "{path}", "§7"],
        ["next", "{path}", "FR"],
        ["upgrade", "{path}", "--to", "standard"],
    ],
)
def test_selected_read_commands_refuse_absolute_paths_outside_consumer_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    outside = tmp_path / "outside.md"
    outside.write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())

    resolved = [part.format(path=str(outside)) for part in argv]
    assert run(resolved, repo=repo, distribution=distribution) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "consumer root" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "path",
    ["../outside.md", "nested/../../outside.md"],
)
def test_selected_validate_refuses_traversal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    path: str,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    (tmp_path / "outside.md").write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())

    assert run(["validate", path], repo=repo, distribution=distribution) == 2
    captured = capsys.readouterr()
    assert "consumer root" in captured.err
    assert "Traceback" not in captured.err


def test_selected_validate_refuses_discovered_and_explicit_symlink_escape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    outside = tmp_path / "outside.md"
    outside.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())
    discovered = repo / "docs/specs/linked.md"
    discovered.parent.mkdir(parents=True)
    discovered.symlink_to(outside)

    assert run(["validate"], repo=repo, distribution=distribution) == 2
    assert run(["validate", "docs/specs/linked.md"], repo=repo, distribution=distribution) == 2
    captured = capsys.readouterr()
    assert "symlink" in captured.err
    assert "Traceback" not in captured.err


def test_selected_validate_uses_captured_bytes_if_path_changes_after_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    victim = repo / "victim.md"
    victim.write_text("not a valid specification\n", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_bytes((_PAYLOAD / "examples/spec.example.md").read_bytes())
    real_capture = RepositorySnapshot.capture

    def capture_then_swap(
        repo_root: Path,
        targets: tuple[SafeRelativePath, ...],
    ) -> RepositorySnapshot:
        result = real_capture(repo_root, targets)
        if any(target.original == "victim.md" for target in targets):
            victim.unlink()
            victim.symlink_to(outside)
        return result

    monkeypatch.setattr(RepositorySnapshot, "capture", staticmethod(capture_then_swap))

    assert run(["validate", "victim.md"], repo=repo, distribution=distribution) == 1


@pytest.mark.parametrize(
    "argv",
    [
        ["validate", "link/spec.md"],
        ["lint", "link/spec.md"],
        ["extract", "link/spec.md", "§7"],
        ["next", "link/spec.md", "FR"],
        ["upgrade", "link/spec.md", "--to", "standard"],
    ],
)
def test_selected_read_commands_refuse_symlinked_parent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "spec.md").write_bytes(
        (_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes()
    )
    (repo / "link").symlink_to(outside, target_is_directory=True)
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)

    assert run(argv, repo=repo, distribution=distribution) == 2
    captured = capsys.readouterr()
    assert "symlink" in captured.err
    assert "Traceback" not in captured.err


def test_selected_upgrade_output_equal_to_source_is_flag_conflict_even_with_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    original = (_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes()
    source.write_bytes(original)

    assert (
        run(
            [
                "upgrade",
                "spec.md",
                "--to",
                "standard",
                "-o",
                "spec.md",
                "--force",
                "--json",
            ],
            repo=repo,
            distribution=distribution,
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["code"] == "flag_conflict"
    assert source.read_bytes() == original


def test_selected_upgrade_output_hard_linked_to_source_is_flag_conflict(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    source = repo / "spec.md"
    original = (_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes()
    source.write_bytes(original)
    alias = repo / "alias.md"
    alias.hardlink_to(source)

    assert (
        run(
            [
                "upgrade",
                "spec.md",
                "--to",
                "standard",
                "-o",
                "alias.md",
                "--force",
                "--json",
            ],
            repo=repo,
            distribution=distribution,
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["code"] == "flag_conflict"
    assert source.read_bytes() == original
    assert alias.read_bytes() == original


def test_selected_upgrade_refuses_absolute_output_outside_consumer_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    (repo / "spec.md").write_bytes((_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes())
    outside = tmp_path / "outside.md"

    assert (
        run(
            ["upgrade", "spec.md", "--to", "standard", "-o", str(outside), "--json"],
            repo=repo,
            distribution=distribution,
        )
        == 2
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["code"] == "not_regular_file"
    assert "Traceback" not in captured.err
    assert not outside.exists()


@pytest.mark.parametrize("json_mode", [False, True])
def test_selected_extract_translates_malformed_document_refusal_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    json_mode: bool,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = _installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)
    (repo / "bad.md").write_text("---\nspec_id: [broken\n---\n", encoding="utf-8")
    argv = ["extract", "bad.md", "§7"]
    if json_mode:
        argv.append("--json")

    assert run(argv, repo=repo, distribution=distribution) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert "Traceback" not in captured.err
