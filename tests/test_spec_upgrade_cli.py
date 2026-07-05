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


def _valid_light_src(tmp_path: Path) -> Path:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(encoding="utf-8"), encoding="utf-8")
    return src


@pytest.mark.parametrize(
    "extra",
    [
        ["--in-place", "--output", "OUT"],
        ["--in-place", "--stdout"],
        ["--stdout", "--output", "OUT"],
        ["--force"],  # --force without --output
    ],
)
def test_flag_conflicts_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extra: list[str]
) -> None:
    # Every conflicting flag combination the matrix rejects must exit 2 with flag_conflict,
    # not fall through to a partial/ambiguous delivery. --output's OUT (when present) points
    # under tmp_path so the check is purely on flag combination, not a filesystem side effect.
    argv = [str(_valid_light_src(tmp_path)), "--to", "standard", *extra, "--json"]
    argv = [str(tmp_path / a) if a == "OUT" else a for a in argv]
    rc = _run(argv)
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["code"] == "flag_conflict"


def test_self_validation_failed_when_splice_does_not_parse(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Gate 3, parse-failure sub-branch: a spliced output that cannot be parsed at all is
    # refused as self_validation_failed (fail-closed U6), never emitted or exit-1'd. The
    # splice must genuinely raise SpecParseError to hit this branch (not merely lack a spec
    # body — parse_document is lenient about that and would fall to the findings branch), so
    # return malformed frontmatter (unclosed YAML flow sequence).
    def _unparseable(*_a: object, **_k: object) -> str:
        return "---\nprofile: [unclosed\n---\nbody\n"

    monkeypatch.setattr("project_standards.specs.cli.upgrade_text", _unparseable)
    rc = _run([str(_valid_light_src(tmp_path)), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "self_validation_failed"


def test_self_validation_failed_when_splice_parses_but_is_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Gate 3, findings sub-branch: a spliced output that PARSES but fails validate is also
    # refused. bad_gap.md has valid frontmatter (parses) yet yields a validation finding,
    # proving the gate rejects a parseable-but-invalid splice, not only an unparseable one.
    bad = (_FIX / "bad_gap.md").read_text(encoding="utf-8")

    def _parseable_but_invalid(*_a: object, **_k: object) -> str:
        return bad

    monkeypatch.setattr("project_standards.specs.cli.upgrade_text", _parseable_but_invalid)
    rc = _run([str(_valid_light_src(tmp_path)), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "self_validation_failed"


def test_undecodable_source_is_source_read_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # _read wraps a UnicodeDecodeError as SpecParseError → source_read_error (not a traceback).
    src = tmp_path / "s.md"
    src.write_bytes(b"\xff\xfe\x00 not utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_read_error"


def test_unparseable_but_decodable_source_is_source_read_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Distinct from the undecodable case: the bytes decode as UTF-8 (so _read succeeds) but
    # parse_document raises on malformed frontmatter → source_read_error, not a traceback.
    src = tmp_path / "s.md"
    src.write_text("---\nprofile: [unclosed\n---\nbody\n", encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_read_error"


def test_success_json_preview_envelope_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = _run([str(_valid_light_src(tmp_path)), "--to", "full", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert obj["ok"] is True
    assert obj["from_profile"] == "light"
    assert obj["to_profile"] == "full"
    assert obj["mode"] == "stdout"
    assert isinstance(obj["content"], str) and "profile: full" in obj["content"]


def test_in_place_rewrites_source_and_preserves_mode(tmp_path: Path) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    src.chmod(0o640)
    rc = _run([str(src), "--to", "standard", "-i"])
    assert rc == 0
    assert "profile: standard" in src.read_text(encoding="utf-8")
    assert (src.stat().st_mode & 0o777) == 0o640  # mode preserved


def test_output_refuses_existing_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    out = tmp_path / "out.md"
    out.write_text("existing\n", encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "-o", str(out), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "exists"
    rc2 = _run([str(src), "--to", "standard", "-o", str(out), "--force"])
    assert rc2 == 0 and "profile: standard" in out.read_text(encoding="utf-8")


def test_output_equal_to_source_is_conflict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "-o", str(src), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "flag_conflict"


def test_json_success_payload_for_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    out = tmp_path / "out.md"
    rc = _run([str(src), "--to", "full", "-o", str(out), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 0 and obj["ok"] and obj["mode"] == "output"
    assert obj["from_profile"] == "light" and obj["to_profile"] == "full" and obj["written"] is True


def test_output_symlink_target_refused_even_with_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Mirrors test_spec_new_cli.test_directory_and_symlink_targets_refused_even_with_force:
    # a symlinked -o target must be refused (not_regular_file) via _safe_atomic_write, and
    # --force (which only governs the overwrite gate) must not bypass this refusal.
    src = _valid_light_src(tmp_path)
    link = tmp_path / "link.md"
    link.symlink_to(tmp_path / "real.md")
    rc = _run([str(src), "--to", "standard", "-o", str(link), "--force", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "not_regular_file"
    assert not (tmp_path / "real.md").exists()  # symlink not followed


def test_output_symlinked_parent_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Mirrors test_spec_new_cli.test_symlinked_parent_refused: an in-tree symlinked parent
    # directory in the -o path must be refused (symlinked_parent) via _safe_atomic_write.
    # The guard is bounded to cwd (see _parent_chain_has_symlink), so chdir into tmp_path
    # like the mirrored test does — otherwise the walk never reaches the symlinked segment.
    monkeypatch.chdir(tmp_path)
    src = _valid_light_src(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    out = tmp_path / "link" / "out.md"
    rc = _run([str(src), "--to", "standard", "-o", str(out), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "symlinked_parent"
    assert not (outside / "out.md").exists()
