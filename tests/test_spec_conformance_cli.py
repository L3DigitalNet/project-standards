from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from project_standards.control_plane.diagnostics import ControlFinding
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, ProviderResult
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    ProviderEffect,
    load_payload_manifest,
)
from project_standards.specs import cli as spec_cli

_ROOT = Path(__file__).resolve().parents[1]
_PAYLOAD_ROOT = _ROOT / "standards/project-spec/versions/1.8"
_CHECKS: list[JsonValue] = ["shared-boilerplate", "mandatory-phrasing"]
_SpecRuntime = spec_cli._SpecRuntime  # pyright: ignore[reportPrivateUsage]
_run_setwide = spec_cli._run_setwide  # pyright: ignore[reportPrivateUsage]


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD_ROOT / "payload.toml")
    integrity = validate_payload_integrity(_PAYLOAD_ROOT, manifest)
    return InstalledPayload(_PAYLOAD_ROOT, manifest, integrity)


def _selected_runtime(repo: Path, *, version: str = "1.8") -> _SpecRuntime:
    payload = _payload()
    if version != "1.8":
        payload = InstalledPayload(
            payload.root,
            payload.manifest.model_copy(
                update={
                    "payload": payload.manifest.payload.model_copy(
                        update={"version": PackageVersion(version)}
                    )
                }
            ),
            payload.integrity,
        )
    return _SpecRuntime(
        repo,
        payload,
        {"reference_prefixes": []},
    )


@pytest.fixture
def clean_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    (tmp_path / "spec.md").write_bytes((_ROOT / "tests/fixtures/specs/valid_light.md").read_bytes())
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.mark.parametrize(
    "runtime_kind",
    [pytest.param("legacy", id="legacy"), pytest.param("selected-1.8", id="selected-1.8")],
)
@pytest.mark.parametrize("json_mode", [False, True], ids=["human", "json"])
def test_lint__coverage_metadata_absent__preserves_clean_output_exactly(
    clean_repo: Path,
    capsys: pytest.CaptureFixture[str],
    runtime_kind: str,
    json_mode: bool,
) -> None:
    runtime = (
        _SpecRuntime(clean_repo) if runtime_kind == "legacy" else _selected_runtime(clean_repo)
    )
    argv = ["--strict", "spec.md"]
    if json_mode:
        argv.insert(1, "--json")

    assert _run_setwide(argv, lint=True, runtime=runtime) == 0

    captured = capsys.readouterr()
    expected = (
        '[\n  {\n    "file": "spec.md",\n    "ok": true,\n    "findings": []\n  }\n]\n'
        if json_mode
        else "OK   spec.md\n"
    )
    assert captured.out == expected
    assert captured.err == ""


@pytest.mark.parametrize("lint", [False, True], ids=["validate", "lint"])
def test_selected_18__strict_clean__preserves_three_key_json_and_exit(
    clean_repo: Path,
    capsys: pytest.CaptureFixture[str],
    lint: bool,
) -> None:
    assert (
        _run_setwide(
            ["--strict", "--json", "spec.md"],
            lint=lint,
            runtime=_selected_runtime(clean_repo),
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out) == [{"file": "spec.md", "ok": True, "findings": []}]


@pytest.mark.parametrize("json_mode", [False, True], ids=["human", "json"])
def test_lint__provider_declares_coverage__projects_checks(
    clean_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    json_mode: bool,
) -> None:
    def declared_result(_invocation: ProviderInvocation) -> ProviderResult:
        return ProviderResult(
            ProviderEffect.FINDINGS,
            structured_output={"findings": [], "checks": _CHECKS},
        )

    monkeypatch.setattr(spec_cli, "invoke_provider", declared_result)
    argv = ["spec.md"]
    if json_mode:
        argv.insert(0, "--json")

    assert (
        _run_setwide(
            argv,
            lint=True,
            runtime=_selected_runtime(clean_repo, version="1.9"),
        )
        == 0
    )

    captured = capsys.readouterr()
    if json_mode:
        assert json.loads(captured.out) == [
            {
                "file": "spec.md",
                "ok": True,
                "findings": [],
                "checks": _CHECKS,
            }
        ]
    else:
        assert captured.out == "OK   spec.md (checks: shared-boilerplate, mandatory-phrasing)\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    "structured_output",
    [
        pytest.param({"findings": []}, id="absent"),
        pytest.param({"findings": [], "checks": []}, id="empty"),
        pytest.param({"findings": [], "checks": ["unknown"]}, id="unapproved"),
    ],
)
def test_lint__provider_does_not_declare_approved_coverage__does_not_infer_checks(
    clean_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    structured_output: JsonObject,
) -> None:
    def undeclared_result(_invocation: ProviderInvocation) -> ProviderResult:
        return ProviderResult(
            ProviderEffect.FINDINGS,
            structured_output=structured_output,
        )

    monkeypatch.setattr(spec_cli, "invoke_provider", undeclared_result)

    assert (
        _run_setwide(
            ["--strict", "--json", "spec.md"],
            lint=True,
            runtime=_selected_runtime(clean_repo, version="1.9"),
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out) == [{"file": "spec.md", "ok": True, "findings": []}]


def test_lint__findings_without_coverage__preserves_payload_and_strict_exit(
    clean_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    finding = ControlFinding(
        code="SL-EXAMPLE",
        severity="warning",
        standard_id="project-spec",
        version="1.9",
        path="spec.md",
        identity="example",
        message="example warning",
        hint="repair the example",
        line=7,
        locus="example",
    )

    def finding_result(_invocation: ProviderInvocation) -> ProviderResult:
        return ProviderResult(
            ProviderEffect.FINDINGS,
            findings=(finding,),
            structured_output={"findings": []},
        )

    monkeypatch.setattr(spec_cli, "invoke_provider", finding_result)

    assert (
        _run_setwide(
            ["--strict", "--json", "spec.md"],
            lint=True,
            runtime=_selected_runtime(clean_repo, version="1.9"),
        )
        == 1
    )

    assert json.loads(capsys.readouterr().out) == [
        {
            "file": "spec.md",
            "ok": False,
            "findings": [
                {
                    "code": "SL-EXAMPLE",
                    "severity": "warning",
                    "message": "example warning",
                    "line": 7,
                    "locus": "example",
                }
            ],
        }
    ]
