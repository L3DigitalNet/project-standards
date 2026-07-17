from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from project_standards.specs import cli as spec_cli
from project_standards.specs.cli import run

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


@pytest.fixture(autouse=True)
def use_legacy_spec_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)


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


def test_dogfood_upgrade_then_validate_is_clean(tmp_path: Path) -> None:
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(), encoding="utf-8")
    out = tmp_path / "up.md"
    assert _run([str(src), "--to", "full", "-o", str(out)]) == 0
    from project_standards.specs.cli import run as _run_group

    assert _run_group(["validate", str(out)]) == 0  # end-to-end U1


def _new_scaffold(tmp_path: Path, tier: str) -> Path:
    """Write an UNMODIFIED real `spec new` scaffold of `tier` to disk and return its path.

    Unlike the hand-maintained upgrade_*.md fixtures, real `spec new` output carries the
    intro-blockquote `[Appendix D](#appendix-d-…)` cross-reference — the exact element the
    tier-crossing anchor-rewrite regression (dead SV-ANCHOR after Appendix D's heading is
    swapped to the target tier) depends on. Generating it here keeps the guard drift-proof.
    """
    src = tmp_path / f"scaffold_{tier}.md"
    rc = run(
        [
            "new",
            "--profile",
            tier,
            "--id",
            "SPEC-9999",
            "--title",
            "Anchor Regression",
            "--owner",
            "me",
            "--implementer",
            "agent",
            str(src),
        ]
    )
    assert rc == 0
    return src


@pytest.mark.parametrize("source_tier", ["light", "standard"])
def test_real_scaffold_carries_preamble_appendix_d_link(tmp_path: Path, source_tier: str) -> None:
    # Precondition guard for the regression tests below: if `spec new` ever stops emitting the
    # intro-blockquote Appendix D anchor, the round-trip tests would pass vacuously. Fail loudly
    # here instead. (This is exactly the coverage the upgrade_*.md fixtures silently lacked.)
    body = _new_scaffold(tmp_path, source_tier).read_text(encoding="utf-8")
    assert re.search(r"\[Appendix D\]\(#appendix-d-[-\w]+\)", body)


@pytest.mark.parametrize(
    ("source_tier", "target_tier", "target_anchor"),
    [
        ("light", "standard", "#appendix-d-tailoring"),
        ("light", "full", "#appendix-d-tailoring-guide"),
        ("standard", "full", "#appendix-d-tailoring-guide"),
    ],
)
def test_tier_increasing_upgrade_of_real_scaffold_self_validates(
    tmp_path: Path, source_tier: str, target_tier: str, target_anchor: str
) -> None:
    # Regression for the release-blocker: `spec upgrade` on an unmodified `spec new` scaffold
    # failed SV-ANCHOR self-validation for EVERY tier-increasing pair, because the kept source
    # preamble's `[Appendix D](#appendix-d-<source-slug>)` pointed at the vanished source-tier
    # heading after Appendix D was swapped to the target tier. upgrade_text now re-points every
    # Appendix D anchor at the target tier's real slug. Assert the upgrade both succeeds (its
    # own self-validation gate) and independently re-validates, and that the anchor is retargeted.
    src = _new_scaffold(tmp_path, source_tier)
    out = tmp_path / "up.md"
    assert run(["upgrade", str(src), "--to", target_tier, "-o", str(out)]) == 0
    upgraded = out.read_text(encoding="utf-8")
    assert f"profile: {target_tier}" in upgraded
    assert target_anchor in upgraded  # retargeted to the target tier's Appendix D slug
    assert "#appendix-d-upgrading-this-spec" not in upgraded  # source (Light) slug is gone
    assert run(["validate", str(out)]) == 0  # independent end-to-end SV-ANCHOR check


def test_mkdir_failed_when_output_parent_is_a_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A regular file sitting where an intermediate directory component is expected makes
    # Path.mkdir(parents=True) raise NotADirectoryError/FileExistsError -> mkdir_failed,
    # not a traceback (mirrors test_spec_new_cli.test_json_codes_for_write_paths).
    src = _valid_light_src(tmp_path)
    blocker = tmp_path / "afile"
    blocker.write_text("x", encoding="utf-8")
    out = blocker / "nested" / "out.md"
    rc = _run([str(src), "--to", "standard", "-o", str(out), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "mkdir_failed"


def test_write_failed_when_atomic_replace_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Best-effort per the plan: forcing the OSError via monkeypatch of os.replace (used by
    # _safe_atomic_write) is deterministic across environments (root ignores read-only-dir
    # mode bits, so chmod(0o500) is not reliable here) — mirrors
    # test_spec_new_cli.test_json_code_write_failed.
    src = _valid_light_src(tmp_path)
    out = tmp_path / "out.md"

    def _boom(_src: object, _dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(spec_cli.os, "replace", _boom)
    rc = _run([str(src), "--to", "standard", "-o", str(out), "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "write_failed"


def _inject_ref(base: str) -> str:
    # Insert RQ-123 as prose at a point that keeps the doc upgradeable (does NOT add a
    # heading/table/section, so upgrade's Gate-2 check_upgradeable is unaffected). Insert
    # right after the frontmatter's closing fence, before the first "# " title line.
    marker = "\n---\n"  # end of frontmatter
    head, _, tail = base.partition(marker)
    return head + marker + "\nExternal backlog: RQ-123.\n" + tail


def test_upgrade_honors_reference_prefixes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Negative proves RQ-123 is the ONLY blocker (source_invalid via SV-ID-UNDECLARED),
    # not a structural/upgradeability problem; positive proves the config clears it.
    src = tmp_path / "s.md"
    src.write_text(
        _inject_ref((_FIX / "upgrade_standard.md").read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    rc = _run([str(src), "--to", "full", "--stdout", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert rc == 2 and obj["code"] == "source_invalid"
    assert any(f["code"] == "SV-ID-UNDECLARED" for f in obj["findings"])

    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("spec:\n  reference_prefixes: ['RQ']\n", encoding="utf-8")
    assert _run([str(src), "--to", "full", "--stdout", "--config", str(cfg)]) == 0


def test_upgrade_without_config_ignores_malformed_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Guards SA-NEW-001: no --config means config is never read, even a broken one present.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".project-standards.yml").write_text("spec: [not, a, mapping\n", encoding="utf-8")
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(encoding="utf-8"), encoding="utf-8")
    assert _run([str(src), "--to", "standard", "--stdout"]) == 0  # unchanged v4.0.0 behavior


def test_upgrade_explicit_malformed_config_is_json_safe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # CR-004: an explicit --config pointing at broken YAML returns the JSON config_error
    # envelope (not a bare crash), preserving the machine contract for --json operators.
    bad = tmp_path / "bad.yml"
    bad.write_text("spec: [not, a, mapping\n", encoding="utf-8")
    src = tmp_path / "s.md"
    src.write_text((_FIX / "upgrade_light.md").read_text(encoding="utf-8"), encoding="utf-8")
    rc = _run([str(src), "--to", "standard", "--stdout", "--config", str(bad), "--json"])
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["code"] == "config_error"


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
