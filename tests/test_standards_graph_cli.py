from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.cli import main
from project_standards.standards_graph.cli import run
from tests.standards_graph_helpers import write_standard


def test_validate_graph_exit0_human(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_standard(tmp_path, "alpha")

    rc = run(["validate-graph", "--root", str(tmp_path)])

    assert rc == 0
    assert "OK standards graph" in capsys.readouterr().out


def test_validate_graph_exit1_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_standard(tmp_path, "alpha", namespaces=["dup"])
    write_standard(tmp_path, "beta", namespaces=["dup"])

    rc = run(["validate-graph", "--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["findings"][0]["code"] == "SG-CONFIG-DUPLICATE-NAMESPACE"


def test_validate_graph_exit2_on_load_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_standard(tmp_path, "alpha", relation_extras={"requires": ["beta"]})

    rc = run(["validate-graph", "--root", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["code"] == "graph_load_error"
    assert "Traceback" not in captured.err


def test_validate_graph_exit2_when_root_does_not_exist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_root = tmp_path / "missing"

    rc = run(["validate-graph", "--root", str(missing_root), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["code"] == "graph_load_error"
    assert str(missing_root) in payload["error"]
    assert "Traceback" not in captured.err


def test_validate_graph_exit2_when_root_has_no_standards_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = run(["validate-graph", "--root", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["code"] == "graph_load_error"
    assert "standards" in payload["error"]
    assert "Traceback" not in captured.err


def test_validate_graph_exit2_when_root_is_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file_root = tmp_path / "not-a-directory"
    file_root.write_text("nope\n", encoding="utf-8")

    rc = run(["validate-graph", "--root", str(file_root), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["code"] == "graph_load_error"
    assert str(file_root) in payload["error"]
    assert "Traceback" not in captured.err


def test_validate_graph_bad_args_exit2(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["validate-graph", "--nope"]) == 2
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err


def test_bare_standards_cli_and_unknown_subcommand_exit2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run([]) == 2
    assert run(["bogus"]) == 2
    assert run(["--help"]) == 0
    assert "usage:" in capsys.readouterr().out


def test_top_level_standards_validate_graph(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_standard(tmp_path, "alpha")

    assert main(["standards", "validate-graph", "--root", str(tmp_path)]) == 0
    assert "OK standards graph" in capsys.readouterr().out


def test_top_level_help_advertises_standards(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert "standards" in capsys.readouterr().out


def test_current_repo_validate_graph_default_allows_pre_retrofit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parent.parent

    rc = main(["standards", "validate-graph", "--root", str(root)])

    assert rc == 0
    assert "OK standards graph" in capsys.readouterr().out


def test_current_repo_validate_graph_require_all_manifests_reports_step05_gap(
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parent.parent

    rc = main(
        ["standards", "validate-graph", "--root", str(root), "--require-all-manifests", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert any(f["code"] == "SG-MANIFEST-MISSING" for f in payload["findings"])
