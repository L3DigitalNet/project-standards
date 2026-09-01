from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pytest

from project_standards.cli import main
from project_standards.package_contract import PackageContractError, PackageFinding
from project_standards.package_contract import cli as package_cli
from project_standards.package_contract.cli import run_packages, run_standards
from project_standards.package_contract.release import (
    CatalogDiff,
    ReleaseClassification,
    ReleaseSnapshot,
    ToolVersions,
)
from project_standards.package_contract.repository import (
    PackageRepository,
)
from tests.package_contract.helpers import (
    copy_minimal_repository,
    refresh_declared_file_digest,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"


def test_validate_packages_human_and_json_success(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_standards(["validate-packages", "--root", str(_FIXTURE)]) == 0
    assert "OK package repository" in capsys.readouterr().out

    assert run_standards(["validate-packages", "--root", str(_FIXTURE), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"ok": True, "findings": []}


def test_validate_packages__noncanonical_05_catalog__is_ignored(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = copy_minimal_repository(tmp_path)
    (root / "catalogs/5.toml").rename(root / "catalogs/05.toml")

    assert run_standards(["validate-packages", "--root", str(root), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "findings": []}


def test_validate_packages__dangling_catalogs_symlink__is_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = copy_minimal_repository(tmp_path)
    shutil.rmtree(root / "catalogs")
    (root / "catalogs").symlink_to(root / "missing-catalogs", target_is_directory=True)

    assert run_standards(["validate-packages", "--root", str(root), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "package_load_error"
    assert "catalog source path must be a regular directory" in payload["error"]


def test_validated_repositories__two_canonical_majors__load_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = copy_minimal_repository(tmp_path)
    catalog = (root / "catalogs/5.toml").read_text(encoding="utf-8")
    (root / "catalogs/6.toml").write_text(
        catalog.replace("catalog_major = 5", "catalog_major = 6", 1),
        encoding="utf-8",
    )
    original_build = package_cli.build_package_repository
    loaded: list[PackageRepository] = []

    def counted_build(
        repository_root: Path,
        *,
        catalog_major: int | None = None,
        family_allowlist: Iterable[str] | None = None,
    ) -> PackageRepository:
        repository = original_build(
            repository_root,
            catalog_major=catalog_major,
            family_allowlist=family_allowlist,
        )
        loaded.append(repository)
        return repository

    monkeypatch.setattr(package_cli, "build_package_repository", counted_build)

    repositories, findings = package_cli._validated_repositories(  # pyright: ignore[reportPrivateUsage]
        root
    )

    assert len(loaded) == 1
    base = loaded[0]
    assert base.catalog is None
    assert findings == ()
    assert [
        repository.catalog.catalog_major if repository.catalog is not None else None
        for repository in repositories
    ] == [5, 6]
    assert all(repository is not base for repository in repositories)
    assert all(repository.families is base.families for repository in repositories)


def test_validate_packages_returns_sorted_findings_and_exit1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    (root / "standards/demo/versions/1.2/README.md").unlink()

    assert run_standards(["validate-packages", "--root", str(root), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert [finding["code"] for finding in payload["findings"]] == [
        "PC-INTEGRITY",
        "PC-CATALOG-INVALID",
    ]


def test_validate_packages_load_boundary_and_bad_args_exit2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_standards(["validate-packages", "--root", str(tmp_path / "missing"), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["code"] == "package_load_error"
    assert "Traceback" not in capsys.readouterr().err

    assert run_standards(["validate-packages", "--unknown"]) == 2


def test_generate_package_schemas_write_check_and_stale_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_standards(["generate-package-schemas", "--root", str(tmp_path)]) == 0
    schema = tmp_path / "src/project_standards/schemas/standard-payload.schema.json"
    assert schema.is_file()
    assert run_standards(["generate-package-schemas", "--root", str(tmp_path), "--check"]) == 0
    schema.write_bytes(schema.read_bytes() + b" ")

    assert run_standards(["generate-package-schemas", "--root", str(tmp_path), "--check"]) == 1
    assert schema.read_bytes().endswith(b" ")
    assert "stale" in capsys.readouterr().err


def test_render_consumer_catalog_requires_output_and_is_read_only_in_check_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    output = root / "generated/catalog.toml"
    base = [
        "render-consumer-catalog",
        "--root",
        str(root),
        "--catalog-major",
        "5",
    ]

    assert run_standards(base) == 2
    assert run_standards([*base[:-1], "0", "--output", str(output)]) == 2
    assert run_standards([*base, "--output", str(output)]) == 0
    rendered = output.read_bytes()
    assert run_standards([*base, "--output", str(output), "--check"]) == 0
    output.write_bytes(rendered + b"# stale\n")
    stale = output.read_bytes()
    assert run_standards([*base, "--output", str(output), "--check"]) == 1
    assert output.read_bytes() == stale
    assert "stale" in capsys.readouterr().err


def test_render_consumer_catalog_rejects_output_escape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    outside = tmp_path / "outside.toml"

    assert (
        run_standards(
            [
                "render-consumer-catalog",
                "--root",
                str(root),
                "--catalog-major",
                "5",
                "--output",
                str(outside),
                "--json",
            ]
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "bad_output"
    assert not outside.exists()


def test_render_consumer_catalog__output_path_oserror__reports_bad_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = copy_minimal_repository(tmp_path)
    output = root / "generated/catalog.toml"
    original_is_symlink = Path.is_symlink

    def failing_output_probe(path: Path) -> bool:
        if path == output:
            raise OSError("path probe denied")
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", failing_output_probe)

    assert (
        run_standards(
            [
                "render-consumer-catalog",
                "--root",
                str(root),
                "--catalog-major",
                "5",
                "--output",
                str(output),
                "--json",
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out) == {
        "ok": False,
        "code": "bad_output",
        "error": "path probe denied",
    }


def test_render_consumer_catalog__output_write_oserror__reports_bad_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = copy_minimal_repository(tmp_path)
    output = root / "generated/catalog.toml"

    def failing_write(_output: Path, _content: bytes, *, check: bool) -> bool:
        assert not check
        raise OSError("disk full")

    monkeypatch.setattr(package_cli, "write_consumer_catalog", failing_write)

    assert (
        run_standards(
            [
                "render-consumer-catalog",
                "--root",
                str(root),
                "--catalog-major",
                "5",
                "--output",
                str(output),
                "--json",
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out) == {
        "ok": False,
        "code": "bad_output",
        "error": "disk full",
    }


def test_render_consumer_catalog__unrelated_error_mentions_output__reports_catalog_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = copy_minimal_repository(tmp_path)
    output = root / "generated/catalog.toml"

    def failing_load(
        _root: Path,
        *,
        catalog_major: int | None = None,
        family_allowlist: Iterable[str] | None = None,
    ) -> PackageRepository:
        del catalog_major, family_allowlist
        raise PackageContractError("provider output is invalid")

    monkeypatch.setattr(package_cli, "build_package_repository", failing_load)

    assert (
        run_standards(
            [
                "render-consumer-catalog",
                "--root",
                str(root),
                "--catalog-major",
                "5",
                "--output",
                str(output),
                "--json",
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out) == {
        "ok": False,
        "code": "catalog_error",
        "error": "provider output is invalid",
    }


def test_sync_payload_projection_write_check_and_stale_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_minimal_repository(tmp_path)
    (root / "src/project_standards").mkdir(parents=True)
    command = ["sync-payload-projection", "--root", str(root)]

    assert run_standards([*command, "--check"]) == 1
    assert not (root / "src/project_standards/payloads").exists()
    assert run_standards(command) == 0
    assert run_standards([*command, "--check"]) == 0
    assert "projection" in capsys.readouterr().out


def _create_released_fixture(repository: Path) -> None:
    git_environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    subprocess.run(["git", "init", "-q", repository], check=True, env=git_environment)
    subprocess.run(["git", "-C", repository, "add", "."], check=True, env=git_environment)
    subprocess.run(
        [
            "git",
            "-C",
            repository,
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=168346341+chrisdpurcell@users.noreply.github.com",
            "commit",
            "-qm",
            "baseline",
        ],
        check=True,
        env=git_environment,
    )
    subprocess.run(
        ["git", "-C", repository, "-c", "tag.gpgSign=false", "tag", "v5.2.0"],
        check=True,
        env=git_environment,
    )


def test_packages_check_release_uses_tagged_baseline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.2.1")

    def no_consistency_findings(
        _root: Path,
        _repository: PackageRepository,
        *,
        distribution_version: str,
    ) -> tuple[PackageFinding, ...]:
        del distribution_version
        return ()

    monkeypatch.setattr(
        package_cli,
        "validate_release_consistency",
        no_consistency_findings,
    )

    assert run_packages(["check-release", "--root", str(repository), "--baseline", "v5.2.0"]) == 0
    assert "patch" in capsys.readouterr().out

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["classification"] == "patch"


def test_packages_check_release__unchanged_catalog_with_proposed_minor__exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.3.0")

    def no_consistency_findings(
        _root: Path,
        _repository: PackageRepository,
        *,
        distribution_version: str,
    ) -> tuple[PackageFinding, ...]:
        del distribution_version
        return ()

    monkeypatch.setattr(
        package_cli,
        "validate_release_consistency",
        no_consistency_findings,
    )

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["classification"] == "forbidden"
    assert [finding["code"] for finding in payload["findings"]] == ["PC-RELEASE-LEVEL"]


def test_packages_check_release_stops_on_candidate_consistency_findings(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.2.1")
    finding = PackageFinding(
        code="PC-RELEASE-PROJECT-VERSION",
        severity="error",
        standard_id="project-standards",
        version="5.2.0",
        path="README.md",
        identity="line:1:project-release",
        message="release-current project version is stale",
        hint="refresh release-current prose",
    )

    def stale_consistency_finding(
        _root: Path,
        _repository: PackageRepository,
        *,
        distribution_version: str,
    ) -> tuple[PackageFinding, ...]:
        del distribution_version
        return (finding,)

    monkeypatch.setattr(
        package_cli,
        "validate_release_consistency",
        stale_consistency_finding,
    )

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["findings"] == [
        {
            "code": finding.code,
            "severity": finding.severity,
            "standard_id": finding.standard_id,
            "version": finding.version,
            "path": finding.path,
            "identity": finding.identity,
            "message": finding.message,
            "hint": finding.hint,
        }
    ]


def test_top_level_dispatch_and_help_preserve_existing_groups(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["standards", "validate-packages", "--root", str(_FIXTURE)]) == 0
    assert main(["standards", "--help"]) == 0
    standards_help = capsys.readouterr().out
    for command in (
        "validate-graph",
        "render-catalog",
        "validate-packages",
        "render-consumer-catalog",
        "generate-package-schemas",
        "sync-payload-projection",
    ):
        assert command in standards_help

    assert main(["packages", "--help"]) == 0
    assert "check-release" in capsys.readouterr().out


def _staged_consistency_findings() -> tuple[PackageFinding, ...]:
    """Return the two consistency findings a correct mid-train tree still reports.

    `.standards/` and the catalog projection are refreshed by release prep, not by
    the payload cut, so a staged tree legitimately carries exactly these codes.
    """
    return (
        PackageFinding(
            code="PC-RELEASE-PROJECTION",
            severity="error",
            standard_id="project-standards",
            version="",
            path="src/project_standards/payloads",
            identity="projection",
            message="a generated catalog projection is stale",
            hint="regenerate the catalog projection from the candidate catalog",
        ),
        PackageFinding(
            code="PC-RELEASE-PROJECT-VERSION",
            severity="error",
            standard_id="project-standards",
            version="5.2.0",
            path="README.md",
            identity="line:1:project-release",
            message="release-current project version is stale",
            hint="refresh release-current prose",
        ),
    )


def _staged_consistency_stub(
    _root: Path,
    _repository: PackageRepository,
    *,
    distribution_version: str,
) -> tuple[PackageFinding, ...]:
    del distribution_version
    return _staged_consistency_findings()


def _mutate_released_payload(repository: Path) -> None:
    """Change a released payload file and re-declare it everywhere it is pinned.

    Digests are refreshed through payload.toml, standard.toml and the catalog so the
    working tree is internally valid; only the comparison with the tagged baseline
    can object, which is what makes PC-RELEASE-PAYLOAD-MUTATED the finding under test
    rather than a repository-integrity or graph finding raised earlier.
    """
    payload_root = repository / "standards/demo/versions/1.2"
    (payload_root / "README.md").write_text("# Demo (mutated)\n", encoding="utf-8")
    refresh_declared_file_digest(repository / "standards/demo", "README.md")
    aggregate = re.findall(
        r'digest = "(sha256:[0-9a-f]{64})"',
        (repository / "standards/demo/standard.toml").read_text(encoding="utf-8"),
    )[-1]
    catalog_path = repository / "catalogs/5.toml"
    catalog_path.write_text(
        re.sub(
            r'digest = "sha256:[0-9a-f]{64}"',
            f'digest = "{aggregate}"',
            catalog_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )


def test_packages_check_release_staged__only_expected_pre_bump_codes__exits_zero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    # A tool version still equal to the baseline is the mid-train shape: release
    # prep has not bumped pyproject yet, so the classifier refuses the transition
    # with the lag producer of PC-RELEASE-LEVEL — the exact red `--staged` exists
    # to reclassify. A bumped-but-wrong-level version (5.3.0 here) would reach the
    # other producer of the same code and must keep failing, which is why this
    # value is load-bearing rather than arbitrary.
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.2.0")
    monkeypatch.setattr(package_cli, "validate_release_consistency", _staged_consistency_stub)

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--staged",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["staged"] is True
    assert payload["classification"] == "forbidden"
    assert payload["expected_pre_bump"] == [
        "PC-RELEASE-LEVEL",
        "PC-RELEASE-PROJECT-VERSION",
        "PC-RELEASE-PROJECTION",
    ]
    assert sorted(finding["code"] for finding in payload["findings"]) == [
        "PC-RELEASE-LEVEL",
        "PC-RELEASE-PROJECT-VERSION",
        "PC-RELEASE-PROJECTION",
    ]

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--staged",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "3 expected pre-bump finding(s)" in captured.out
    assert captured.err.count("EXPECTED-PRE-BUMP ") == 3
    assert "ERROR " not in captured.err


def test_packages_check_release_staged__payload_mutation__still_exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    _mutate_released_payload(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.3.0")
    monkeypatch.setattr(package_cli, "validate_release_consistency", _staged_consistency_stub)

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--staged",
                "--json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "PC-RELEASE-PAYLOAD-MUTATED" in {finding["code"] for finding in payload["findings"]}
    assert "PC-RELEASE-PAYLOAD-MUTATED" not in payload["expected_pre_bump"]


def test_packages_check_release_staged__non_expected_consistency_finding__exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.2.1")
    stale = PackageFinding(
        code="PC-RELEASE-PACKAGE-CURRENT",
        severity="error",
        standard_id="demo",
        version="1.2",
        path="README.md",
        identity="line:1:package-current",
        message="package-current prose names a superseded version",
        hint="refresh package-current prose",
    )

    def package_current_finding(
        _root: Path,
        _repository: PackageRepository,
        *,
        distribution_version: str,
    ) -> tuple[PackageFinding, ...]:
        del distribution_version
        return (stale,)

    monkeypatch.setattr(package_cli, "validate_release_consistency", package_current_finding)

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--staged",
                "--json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert [finding["code"] for finding in payload["findings"]] == ["PC-RELEASE-PACKAGE-CURRENT"]


def test_packages_check_release__without_staged__output_is_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin that `--staged` is inert when absent: same JSON keys, same exit code."""
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.3.0")
    monkeypatch.setattr(package_cli, "validate_release_consistency", _staged_consistency_stub)

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"ok", "findings"}
    assert payload["ok"] is False
    assert [finding["code"] for finding in payload["findings"]] == [
        "PC-RELEASE-PROJECTION",
        "PC-RELEASE-PROJECT-VERSION",
    ]


def test_packages_check_release_staged__breaking_default_promotion__still_exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--staged` must not excuse the other producer of PC-RELEASE-LEVEL.

    The classifier reports a breaking default promotion under the same code as the
    pre-bump lag, so a code-keyed expectation would silently pass a genuinely
    forbidden transition. The stubbed diff leaves `pre_bump_lag` empty, which is
    exactly what `classify_catalog_diff` does for that producer.
    """
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    _create_released_fixture(repository)
    monkeypatch.setattr(package_cli, "package_version", lambda: "5.2.0")
    monkeypatch.setattr(package_cli, "validate_release_consistency", _staged_consistency_stub)
    promotion = PackageFinding(
        code="PC-RELEASE-LEVEL",
        severity="error",
        standard_id="demo",
        version="2.0",
        path="catalogs",
        identity="catalog-entry",
        message="breaking default promotion requires an owner-designated tool and catalog major",
        hint="preserve released payloads and follow ADR 0024 release boundaries",
    )

    def breaking_promotion(
        _previous: ReleaseSnapshot,
        _current: ReleaseSnapshot,
        _tool_versions: ToolVersions,
    ) -> CatalogDiff:
        return CatalogDiff(ReleaseClassification.FORBIDDEN, (promotion,))

    monkeypatch.setattr(package_cli, "classify_catalog_diff", breaking_promotion)

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--staged",
                "--json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["expected_pre_bump"] == [
        "PC-RELEASE-PROJECT-VERSION",
        "PC-RELEASE-PROJECTION",
    ]

    assert (
        run_packages(
            [
                "check-release",
                "--root",
                str(repository),
                "--baseline",
                "v5.2.0",
                "--staged",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "ERROR PC-RELEASE-LEVEL demo@2.0 catalog-entry:" in captured.err
    assert "expected pre-bump finding(s)" not in captured.out
