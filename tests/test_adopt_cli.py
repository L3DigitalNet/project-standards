from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards import validate_frontmatter
from project_standards.cli import main


def test_list_plain_lists_four_standards(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    for sid in ("markdown-frontmatter", "adr", "markdown-tooling", "python-tooling"):
        assert sid in out


def test_list_json_schema(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    ids = {s["id"] for s in data}
    assert "python-tooling" in ids
    for s in data:  # stable schema: every standard carries a contract_version key
        assert "contract_version" in s
    py = next(s for s in data if s["id"] == "python-tooling")
    assert any(a["kind"] == "fragment" and a["target"] == "pyproject.toml" for a in py["artifacts"])


def test_list_on_broken_manifest_exits_clean(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A malformed/absent bundle manifest must yield a documented exit code, not a traceback.
    import project_standards.cli as cli
    from project_standards.adopt.errors import ManifestError

    def boom(_sid: str) -> object:
        raise ManifestError("manifest missing")

    monkeypatch.setattr(cli, "load_manifest", boom)
    rc = main(["list"])
    assert rc == 3
    assert "manifest missing" in capsys.readouterr().err


def test_bundle_ids_align_with_registry_contract_versions() -> None:
    # Drift guard (both directions): every adoptable bundle maps to a non-None registry
    # contract version, and the registry's version-tracked standards are exactly the bundles.
    from project_standards.adopt.manifest import available_standards
    from project_standards.cli import (
        _contract_version,  # pyright: ignore[reportPrivateUsage]
    )
    from project_standards.registry import load_registry

    reg = load_registry()
    bundle_ids = set(available_standards())
    registry_ids = {
        "markdown-frontmatter": reg.frontmatter_default,
        "adr": reg.adr_default,
        "python-tooling": reg.python_tooling_default,
        "markdown-tooling": reg.markdown_tooling_default,
    }
    assert bundle_ids == set(registry_ids)
    for sid in bundle_ids:
        assert _contract_version(reg, sid) is not None, sid


def test_adopt_unknown_standard_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["adopt", "nope"])
    assert rc == 2
    assert "unknown standard" in capsys.readouterr().err


def test_validate_subcommand_delegates_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    # `project-standards validate --config X --quiet` must forward ALL flags to the validator
    # (regression guard for the argparse REMAINDER trap — must not exit 2 before delegating).
    import project_standards.cli as cli

    captured: list[list[str]] = []

    def fake_validate(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    monkeypatch.setattr(cli.validate_frontmatter, "main", fake_validate)
    rc = main(["validate", "--config", ".project-standards.yml", "--quiet"])
    assert rc == 0
    assert captured == [["--config", ".project-standards.yml", "--quiet"]]


def test_adopt_dest_not_a_directory_exits_2(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    rc = main(["adopt", "markdown-tooling", "--dest", str(missing)])
    assert rc == 2


def test_adopt_markdown_tooling_creates_files(tmp_path: Path) -> None:
    rc = main(["adopt", "markdown-tooling", "--dest", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / ".markdownlint.json").is_file()
    assert (tmp_path / ".editorconfig").is_file()
    caller = (tmp_path / ".github/workflows/lint-markdown.yml").read_text()
    assert "{{ref}}" not in caller and "@v" in caller


def test_combined_adoption_emits_shared_editorconfig_once(tmp_path: Path) -> None:
    rc = main(["adopt", "markdown-tooling", "python-tooling", "--dest", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / ".editorconfig").is_file()
    assert (tmp_path / ".markdownlint.json").is_file()
    assert (tmp_path / ".python-version").read_text().strip() == "3.14"


def test_python_only_and_markdown_only_share_same_editorconfig(tmp_path: Path) -> None:
    a, b = tmp_path / "py", tmp_path / "md"
    a.mkdir()
    b.mkdir()
    main(["adopt", "python-tooling", "--dest", str(a)])
    main(["adopt", "markdown-tooling", "--dest", str(b)])
    assert (a / ".editorconfig").read_bytes() == (b / ".editorconfig").read_bytes()


def test_pyproject_fragment_reported_not_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["adopt", "python-tooling", "--dest", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Add these sections to `pyproject.toml`" in out
    assert not (tmp_path / "pyproject.toml").exists()


def test_adr_reports_project_standards_fragment_no_inplace_edit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".project-standards.yml").write_text("standards_version: 'v2'\n")
    before = (tmp_path / ".project-standards.yml").read_text()
    main(["adopt", "adr", "--dest", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Add these sections to `.project-standards.yml`" in out
    assert (tmp_path / ".project-standards.yml").read_text() == before  # untouched


def test_idempotent_rerun_skips(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["adopt", "markdown-tooling", "--dest", str(tmp_path)])
    capsys.readouterr()
    main(["adopt", "markdown-tooling", "--dest", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Skipped (already present)" in out


def test_adopt_frontmatter_adr_validates_real_managed_file_and_excludes_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Clean config-less repo: the starter (with its **/*.template.md exclusion) is written,
    # and the ADR template lands at docs/decisions/adr.template.md. We also drop a REAL managed
    # doc with valid frontmatter (a shipped, dogfooded example) so validation actually processes
    # a file rather than passing vacuously. Validating IN-PROCESS (chdir; the validator runs from
    # this repo's installed env) must return 0 — proving (a) the managed doc passes and (b) the
    # placeholder template's intentional YYYY-MM-DD frontmatter is excluded, not validated.
    main(["adopt", "markdown-frontmatter", "adr", "--dest", str(tmp_path)])
    assert (tmp_path / "docs/decisions/adr.template.md").is_file()
    example = (
        Path(__file__).resolve().parent.parent
        / "standards/markdown-frontmatter/examples/note.example.md"
    )
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs/guide.md").write_bytes(example.read_bytes())
    monkeypatch.chdir(tmp_path)
    rc = validate_frontmatter.main(["--config", ".project-standards.yml"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "validated" in out  # at least one managed file was actually validated


def test_adopt_adr_into_existing_config_reports_exclusion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Pre-existing config lacking the template exclusion: the ADR fragment report must
    # carry the **/*.template.md exclusion guidance (CLI never edits the file in place).
    (tmp_path / ".project-standards.yml").write_text(
        "markdown:\n  frontmatter:\n    include:\n      - 'docs/**/*.md'\n"
    )
    main(["adopt", "adr", "--dest", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Add these sections to `.project-standards.yml`" in out
    assert "**/*.template.md" in out


def test_adopt_adr_existing_config_with_exclusion_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proves the reported guidance is *correct*: an existing config that includes docs/**/*.md
    # AND applies the reported **/*.template.md exclusion validates cleanly after adopting ADR,
    # despite the template's intentional placeholder frontmatter.
    (tmp_path / ".project-standards.yml").write_text(
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '1.1'\n"
        "    schema: 'markdown-frontmatter'\n"
        "    required: true\n"
        "    include:\n"
        "      - 'docs/**/*.md'\n"
        "    exclude:\n"
        "      - '**/*.template.md'\n"  # the operator-applied exclusion from the ADR report
    )
    main(["adopt", "adr", "--dest", str(tmp_path)])
    assert (tmp_path / "docs/decisions/adr.template.md").is_file()
    monkeypatch.chdir(tmp_path)
    assert validate_frontmatter.main(["--config", ".project-standards.yml"]) == 0
