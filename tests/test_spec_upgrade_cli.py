from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.specs.cli import run

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _run(argv: list[str]) -> int:
    return run(["upgrade", *argv])


def test_missing_to_flag_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    rc = _run([str(_FIX / "upgrade_light.md"), "--json"])
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["code"] == "usage"


def test_downgrade_target_light_is_usage_error(tmp_path: Path) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_standard.md").read_text(), encoding="utf-8")
    assert _run([str(src), "--to", "light", "--json"]) == 2  # argparse rejects --to light


def test_same_tier_is_not_upgradeable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_standard.md").read_text(), encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "not_upgradeable"


def test_invalid_source_is_refused_with_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "s.md"
    src.write_text("---\nprofile: light\n---\n\nnot a real spec\n", encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_invalid" and obj["findings"]


def test_gap_prose_source_is_not_upgradeable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Validate-clean (gap prose does not trip validate) but non-canonical → precheck refuses.
    src = tmp_path / "s.md"
    tampered = (
        (_FIX / "upgrade_light.md")
        .read_text()
        .replace("## 7. Requirements", "Author prose in a gap.\n\n## 7. Requirements", 1)
    )
    src.write_text(tampered, encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_not_upgradeable"


def test_preview_prints_upgraded_doc_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "s.md"
    original = (_FIX / "upgrade_light.md").read_text()
    src.write_text(original, encoding="utf-8")
    rc = _run([str(src), "--to", "standard"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "profile: standard" in out
    assert src.read_text(encoding="utf-8") == original  # U4: source untouched


def test_missing_source_file(capsys: pytest.CaptureFixture[str]) -> None:
    rc = _run(["nope.md", "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_not_found"
