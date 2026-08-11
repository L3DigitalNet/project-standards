from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.cli import main
from project_standards.control_plane.locking import LockMode
from project_standards.specs import cli as spec_cli
from project_standards.specs.cli import run

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"
_COORDINATE_SOURCE = (
    "---\n"
    "spec_id: SPEC-0001\n"
    "profile: light\n"
    "status: draft\n"
    "---\n"
    "# Demo\n"
    "<replace me>\n"
    "## 999. Unknown\n"
)


@pytest.fixture(autouse=True)
def use_legacy_spec_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)


def test_spec_validate_valid_exit0(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["spec", "validate", str(_FIX / "valid_standard.md")]) == 0
    assert "OK" in capsys.readouterr().out


def test_spec_validate_bad_exit1_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["spec", "validate", "--json", str(_FIX / "bad_dup_id.md")])
    data = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert any(f["code"] == "SV-ID-DUP" for f in data[0]["findings"])


def test_spec_missing_config_exit2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["spec", "validate"]) == 2


def test_spec_next_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["spec", "next", "--json", str(_FIX / "valid_standard.md"), "FR"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["next_id"].startswith("FR-")


def test_spec_malformed_input_no_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text("---\nspec_id: SPEC-7F3Q\n# unterminated frontmatter\n", encoding="utf-8")
    assert main(["spec", "validate", str(bad)]) == 1
    assert main(["spec", "extract", str(bad), "§7"]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_bare_spec_is_exit2_but_help_is_exit0(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["spec"]) == 2
    assert main(["spec", "--help"]) == 0
    assert main(["spec", "bogus"]) == 2
    assert "usage:" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("verb", "argv"),
    [
        pytest.param("new", ["--stdout"], id="new-missing-profile"),
        pytest.param(
            "new",
            ["--profile", "light", "--stdout", "--unknown"],
            id="new-unknown-option",
        ),
        pytest.param("upgrade", ["source.md", "--to"], id="upgrade-missing-value"),
        pytest.param(
            "upgrade",
            ["source.md", "--to", "full", "--unknown"],
            id="upgrade-unknown-option",
        ),
        pytest.param("import", ["source.md", "--apply"], id="import-incomplete-apply"),
    ],
)
def test_operation_lock_mode_fails_safe_on_uncertain_arguments(
    verb: str,
    argv: list[str],
) -> None:
    assert (
        spec_cli._operation_lock_mode(  # pyright: ignore[reportPrivateUsage]
            verb,
            argv,
        )
        is LockMode.WRITE
    )


def test_import_lock_mode_tracks_digest_authorized_apply() -> None:
    assert (
        spec_cli._operation_lock_mode(  # pyright: ignore[reportPrivateUsage]
            "import",
            ["source.md", "--output", "target.md", "--id", "SPEC-AB12"],
        )
        is LockMode.READ
    )
    assert (
        spec_cli._operation_lock_mode(  # pyright: ignore[reportPrivateUsage]
            "import",
            [
                "source.md",
                "--output",
                "target.md",
                "--id",
                "SPEC-AB12",
                "--apply",
                "--expected-plan-digest",
                f"sha256:{'a' * 64}",
            ],
        )
        is LockMode.WRITE
    )


def test_spec_help_lists_import_and_required_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["spec", "--help"]) == 0
    assert "import" in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        main(["spec", "import", "--help"])
    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "--output" in help_text
    assert "--id" in help_text
    assert "--expected-plan-digest" in help_text


def test_non_utf8_spec_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "latin1.md"
    bad.write_bytes(b"---\nspec_id: SPEC-7F3Q\n---\n# t \xff\xfe not utf-8\n")
    assert main(["spec", "validate", str(bad)]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_lint_json_shape(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["spec", "lint", "--json", str(_FIX / "draft_placeholders.md")])
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert set(data[0]) == {"file", "ok", "findings"}
    assert data[0]["findings"] and data[0]["findings"][0]["severity"] == "warning"


def test_strict_lint_refuses_ok_for_a_document_validate_rejects(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Issue #121: `lint --strict` reported OK and exit 0 for a one-line document."""
    spec = tmp_path / "example.md"
    spec.write_text("# Example Spec\n", encoding="utf-8")

    assert main(["spec", "validate", str(spec)]) == 1
    capsys.readouterr()

    assert main(["spec", "lint", "--strict", str(spec)]) == 1
    human = capsys.readouterr().out
    assert human.startswith("WARN")
    assert "[SL-STRUCTURE]" in human
    assert "run spec validate" in human

    assert main(["spec", "lint", str(spec)]) == 0


@pytest.mark.parametrize(
    ("verb", "code", "expected_line"),
    [("lint", "SL-PLACEHOLDER", 7), ("validate", "SV-SECTION", 8)],
)
def test_spec_finding_lines_are_absolute_in_human_and_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    verb: str,
    code: str,
    expected_line: int,
) -> None:
    spec = tmp_path / "coordinates.md"
    spec.write_text(_COORDINATE_SOURCE, encoding="utf-8")

    assert run([verb, "--strict", str(spec)]) == 1
    human = capsys.readouterr().out
    assert f"[{code}]" in human
    assert f"(L{expected_line})" in human

    assert run([verb, "--strict", "--json", str(spec)]) == 1
    result = json.loads(capsys.readouterr().out)
    finding = next(item for item in result[0]["findings"] if item["code"] == code)
    assert finding["line"] == expected_line


def test_extract_json_found_and_no_match(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["spec", "extract", "--json", str(_FIX / "valid_standard.md"), "§7"])
    found = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert found["found"] is True and found["kind"] == "section" and found["markdown"]
    rc2 = main(["spec", "extract", "--json", str(_FIX / "valid_standard.md"), "FR-999"])
    miss = json.loads(capsys.readouterr().out)
    assert rc2 == 1
    assert miss["found"] is False and miss["markdown"] is None


def test_validate_honors_reference_prefixes(tmp_path: Path) -> None:
    # valid_light.md validates clean today; injecting RQ-123 as prose (not a heading
    # or table cell) keeps it structurally valid, so rc turns on the reference behavior.
    base = (_FIX / "valid_light.md").read_text(encoding="utf-8")
    spec = tmp_path / "s.md"
    spec.write_text(
        base.replace("## Revision History", "External backlog: RQ-123.\n\n## Revision History", 1),
        encoding="utf-8",
    )
    # Sanity: without the config the same file fails (RQ-123 trips SV-ID-UNDECLARED).
    assert run(["validate", str(spec)]) == 1
    # With RQ declared as an external reference, the file is clean again.
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("spec:\n  include: ['s.md']\n  reference_prefixes: ['RQ']\n", encoding="utf-8")
    assert run(["validate", str(spec), "--config", str(cfg)]) == 0


def test_validate_malformed_reference_prefixes_exits_2(tmp_path: Path) -> None:
    """ConfigError from malformed reference_prefixes maps to exit 2."""
    spec = tmp_path / "s.md"
    spec.write_text((_FIX / "valid_light.md").read_text(encoding="utf-8"), encoding="utf-8")
    cfg = tmp_path / ".project-standards.yml"
    # FR is a canonical spec-local prefix; listing it raises ConfigError.
    cfg.write_text("spec:\n  include: ['s.md']\n  reference_prefixes: ['FR']\n", encoding="utf-8")
    assert run(["validate", str(spec), "--config", str(cfg)]) == 2
