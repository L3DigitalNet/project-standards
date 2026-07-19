"""Integration tests for the project-standards CLI: adopt, list, and validate subcommands.

Covers the full CLI surface via main():
- list (plain and --json); registry/bundle parity guard
- adopt: dest validation, file materialization, shared-artifact dedup, idempotency,
  fragment reporting, and the ADR template-exclusion guidance
- validate: early-dispatch architecture (cannot use argparse REMAINDER for flags like
  --config), --help interception before forwarding, flag pass-through to all validators,
  worst-exit-code selection, --schema, and config custom-schema bypass
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards import validate_frontmatter
from project_standards.cli import (
    _try_v5_adopt,  # pyright: ignore[reportPrivateUsage]
    main,
    v5_catalog_has_all_adoptable_defaults,
)
from project_standards.control_plane.codec import parse_catalog
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.package_contract.catalog import render_consumer_catalog
from project_standards.package_contract.repository import build_package_repository


@pytest.fixture(autouse=True)
def use_legacy_adopt_route(monkeypatch: pytest.MonkeyPatch) -> None:
    def legacy_route(
        _standards: list[str],
        _dest: Path,
        *,
        force: bool,
        dry_run: bool,
        unsupported_options: bool = False,
    ) -> None:
        del force, dry_run, unsupported_options

    monkeypatch.setattr("project_standards.cli._try_v5_adopt", legacy_route)


def test_list_plain_lists_packaged_adopt_standards(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    for sid in (
        "markdown-frontmatter",
        "adr",
        "markdown-tooling",
        "python-tooling",
        "cli-documentation",
        "project-spec",
    ):
        assert sid in out


def test_adopt_force_help_explains_create_only_exception(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["adopt", "--help"])

    assert exc_info.value.code == 0
    normalized = " ".join(capsys.readouterr().out.split())
    assert "overwrite existing managed artifacts" in normalized
    assert "create-only artifacts remain skipped" in normalized


def test_v5_adopt_activates_only_for_the_complete_default_set() -> None:
    root = Path(__file__).resolve().parent.parent
    repository = build_package_repository(root, catalog_major=5)
    assert repository.catalog is not None
    catalog = parse_catalog(
        render_consumer_catalog(
            repository.catalog,
            repository.family_map,
            repository.payload_map,
            tool_release="5.0.0",
        )
    )

    assert v5_catalog_has_all_adoptable_defaults(catalog)
    complete_with_extra = catalog.model_copy(
        update={
            "standards": {
                **catalog.standards,
                "future-standard": catalog.standards["agent-handoff"],
            }
        }
    )
    assert v5_catalog_has_all_adoptable_defaults(complete_with_extra)
    incomplete = catalog.model_copy(
        update={
            "standards": {
                **catalog.standards,
                "agent-handoff": catalog.standards["agent-handoff"].model_copy(
                    update={"default": None}
                ),
            }
        }
    )
    assert not v5_catalog_has_all_adoptable_defaults(incomplete)


def test_v5_adopt_distribution_oserror_warns_and_preserves_legacy_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_current() -> InstalledDistribution:
        raise OSError("distribution unavailable")

    monkeypatch.setattr(InstalledDistribution, "current", fail_current)

    result = _try_v5_adopt(
        ["markdown-tooling"],
        tmp_path,
        force=False,
        dry_run=False,
    )

    assert result is None
    assert capsys.readouterr().err == (
        "warning: installed V2 distribution could not be read: distribution unavailable\n"
    )


def test_list_json_schema(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    ids = {s["id"] for s in data}
    assert "python-tooling" in ids
    assert "project-spec" in ids
    for s in data:  # stable schema: every standard carries a contract_version key
        assert "contract_version" in s
    py = next(s for s in data if s["id"] == "python-tooling")
    assert any(a["kind"] == "fragment" and a["target"] == "pyproject.toml" for a in py["artifacts"])
    mf = next(s for s in data if s["id"] == "markdown-frontmatter")
    script = next(
        a
        for a in mf["artifacts"]
        if a["dest"] == ".agents/skills/markdown-frontmatter/scripts/new-doc-id"
    )
    assert script["mode"] == "0755"
    assert script["provenance"] == "source-owned"
    assert script["install_policy"] == "managed"
    assert script["canonical"].endswith("scripts/new-doc-id")
    ps = next(s for s in data if s["id"] == "project-spec")
    assert ps["contract_version"] == "1.0"
    assert any(
        a["kind"] == "workflow-caller" and a["dest"] == ".github/workflows/validate-specs.yml"
        for a in ps["artifacts"]
    )


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
    # Drift guard (both directions): every adoptable bundle is known to the CLI, while
    # version-tracked standards still map to a non-None registry contract version.
    from project_standards.adopt.manifest import available_standards
    from project_standards.cli import (
        _ADOPTABLE_STANDARD_IDS,  # pyright: ignore[reportPrivateUsage]
        _VERSION_TRACKED_STANDARD_IDS,  # pyright: ignore[reportPrivateUsage]
        _contract_version,  # pyright: ignore[reportPrivateUsage]
    )
    from project_standards.registry import load_registry

    reg = load_registry()
    bundle_ids = set(available_standards())
    version_tracked_registry_ids = {
        "markdown-frontmatter": reg.frontmatter_default,
        "adr": reg.adr_default,
        "python-tooling": reg.python_tooling_default,
        "markdown-tooling": reg.markdown_tooling_default,
        "cli-documentation": reg.cli_documentation_default,
        "project-spec": reg.project_spec_default,
        "agent-handoff": reg.agent_handoff_default,
    }
    assert bundle_ids == set(_ADOPTABLE_STANDARD_IDS)
    assert set(_VERSION_TRACKED_STANDARD_IDS) == set(version_tracked_registry_ids)
    for sid in _VERSION_TRACKED_STANDARD_IDS:
        assert _contract_version(reg, sid) is not None, sid


def test_adopt_unknown_standard_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["adopt", "nope"])
    assert rc == 2
    assert "unknown standard" in capsys.readouterr().err


def test_validate_help_shows_all_validators(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["validate", "--help"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "validate-id" in out
    assert "validate-frontmatter" in out
    assert "validate-references" in out


def test_validate_subcommand_delegates_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # All validators must receive the same argv — regression guard for the argparse
    # REMAINDER trap that previously caused exit 2 before delegating.
    import project_standards.cli as cli

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".project-standards.yml").write_text(
        "standards_version: v4\n",
        encoding="utf-8",
    )
    captured_fm: list[list[str]] = []
    captured_id: list[list[str]] = []
    captured_refs: list[list[str]] = []

    def fake_fm(argv: list[str]) -> int:
        captured_fm.append(list(argv))
        return 0

    def fake_id(argv: list[str]) -> int:
        captured_id.append(list(argv))
        return 0

    def fake_refs(argv: list[str]) -> int:
        captured_refs.append(list(argv))
        return 0

    monkeypatch.setattr(cli.validate_frontmatter, "main", fake_fm)
    monkeypatch.setattr(cli.validate_id, "main", fake_id)
    monkeypatch.setattr(cli.validate_references, "main", fake_refs)
    rc = main(["validate", "--config", ".project-standards.yml", "--quiet"])
    assert rc == 0
    assert captured_fm == [["--config", ".project-standards.yml", "--quiet"]]
    assert captured_id == [["--config", ".project-standards.yml", "--quiet"]]
    assert captured_refs == [["--config", ".project-standards.yml", "--quiet"]]


def test_validate_exit_code_is_maximum_of_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Combined command returns the worst validator exit code, so no failure is masked.
    import project_standards.cli as cli

    monkeypatch.chdir(tmp_path)
    cases = [
        (0, 0, 0, 0),
        (1, 0, 0, 1),
        (0, 1, 0, 1),
        (0, 0, 1, 1),
        (2, 0, 0, 2),
        (0, 2, 0, 2),
        (0, 0, 2, 2),
        (1, 2, 1, 2),
    ]
    for rc_fm, rc_id, rc_refs, expected in cases:

        def fake_fm(_argv: list[str], _r: int = rc_fm) -> int:
            return _r

        def fake_id(_argv: list[str], _r: int = rc_id) -> int:
            return _r

        def fake_refs(_argv: list[str], _r: int = rc_refs) -> int:
            return _r

        monkeypatch.setattr(cli.validate_frontmatter, "main", fake_fm)
        monkeypatch.setattr(cli.validate_id, "main", fake_id)
        monkeypatch.setattr(cli.validate_references, "main", fake_refs)
        assert main(["validate"]) == expected


def test_validate_schema_flag_skips_id_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # --schema signals non-standard id conventions; validate-id must exit 0 so the
    # combined command doesn't produce false positives for custom-schema consumers.
    import project_standards.cli as cli

    schema_file = tmp_path / "custom.json"
    schema_file.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def fake_fm(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(cli.validate_frontmatter, "main", fake_fm)
    # validate_id.main runs for real — verifies it returns 0 when --schema is provided
    rc = main(["validate", "--schema", str(schema_file), "--quiet"])
    assert rc == 0


def test_validate_config_custom_schema_skips_id_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A config-level custom schema (markdown.frontmatter.schema: ./path) must also cause
    # validate-id to skip — the reusable workflow invokes `validate-id --config ...`,
    # so consumers with a config-based custom schema must not get false positives.
    import project_standards.cli as cli

    custom_schema = tmp_path / "custom.json"
    custom_schema.write_text("{}", encoding="utf-8")
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        f"markdown:\n  frontmatter:\n    schema: '{custom_schema}'\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    def fake_fm(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(cli.validate_frontmatter, "main", fake_fm)
    # validate_id.main runs for real — verifies it returns 0 for config-based custom schema
    rc = main(["validate", "--config", str(cfg), "--quiet"])
    assert rc == 0


def test_validate_glob_forwarded_to_all_validators(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.cli as cli

    monkeypatch.chdir(tmp_path)
    captured_fm: list[list[str]] = []
    captured_id: list[list[str]] = []
    captured_refs: list[list[str]] = []

    def fake_fm(argv: list[str]) -> int:
        captured_fm.append(list(argv))
        return 0

    def fake_id(argv: list[str]) -> int:
        captured_id.append(list(argv))
        return 0

    def fake_refs(argv: list[str]) -> int:
        captured_refs.append(list(argv))
        return 0

    monkeypatch.setattr(cli.validate_frontmatter, "main", fake_fm)
    monkeypatch.setattr(cli.validate_id, "main", fake_id)
    monkeypatch.setattr(cli.validate_references, "main", fake_refs)
    main(["validate", "--glob", "standards/**/*.md"])
    assert "--glob" in captured_fm[0] and "standards/**/*.md" in captured_fm[0]
    assert "--glob" in captured_id[0] and "standards/**/*.md" in captured_id[0]
    assert "--glob" in captured_refs[0] and "standards/**/*.md" in captured_refs[0]


def test_validate_no_require_frontmatter_forwarded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.cli as cli

    monkeypatch.chdir(tmp_path)
    captured_fm: list[list[str]] = []
    captured_id: list[list[str]] = []
    captured_refs: list[list[str]] = []

    def fake_fm(argv: list[str]) -> int:
        captured_fm.append(list(argv))
        return 0

    def fake_id(argv: list[str]) -> int:
        captured_id.append(list(argv))
        return 0

    def fake_refs(argv: list[str]) -> int:
        captured_refs.append(list(argv))
        return 0

    monkeypatch.setattr(cli.validate_frontmatter, "main", fake_fm)
    monkeypatch.setattr(cli.validate_id, "main", fake_id)
    monkeypatch.setattr(cli.validate_references, "main", fake_refs)
    main(["validate", "--no-require-frontmatter"])
    assert "--no-require-frontmatter" in captured_fm[0]
    assert "--no-require-frontmatter" in captured_id[0]
    assert "--no-require-frontmatter" in captured_refs[0]


def test_adopt_dest_not_a_directory_exits_2(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    rc = main(["adopt", "markdown-tooling", "--dest", str(missing)])
    assert rc == 2


def test_adopt_dry_run_nonexistent_dest_returns_0(tmp_path: Path) -> None:
    """--dry-run skips the dest-exists check; no files are written."""
    nonexistent = tmp_path / "does-not-exist"
    rc = main(["adopt", "markdown-tooling", "--dest", str(nonexistent), "--dry-run"])
    assert rc == 0
    assert not nonexistent.exists()  # nothing was created


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
    # and the ADR template lands at docs/adr/adr.template.md. We also drop a REAL managed
    # doc with valid frontmatter (a shipped, dogfooded example) so validation actually processes
    # a file rather than passing vacuously. Validating IN-PROCESS (chdir; the validator runs from
    # this repo's installed env) must return 0 — proving (a) the managed doc passes and (b) the
    # placeholder template's intentional YYYY-MM-DD frontmatter is excluded, not validated.
    main(["adopt", "markdown-frontmatter", "adr", "--dest", str(tmp_path)])
    assert (tmp_path / "docs/adr/adr.template.md").is_file()
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
    assert (tmp_path / "docs/adr/adr.template.md").is_file()
    monkeypatch.chdir(tmp_path)
    assert validate_frontmatter.main(["--config", ".project-standards.yml"]) == 0


# ---------------------------------------------------------------------------
# CLI plumbing: registry/bundle parity and empty dry-run
# ---------------------------------------------------------------------------


def test_main_list_registry_bundle_drift_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A bundle on disk with no registry contract entry (or vice versa) must be a
    # clean exit 2 before any listing output, not a half-emitted list.
    import project_standards.cli as cli_mod

    def fake_available() -> list[str]:
        return ["markdown-frontmatter"]

    monkeypatch.setattr(cli_mod, "available_standards", fake_available)
    rc = cli_mod.main(["list"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "registry/bundle drift" in captured.err
    assert captured.out == ""


def test_cmd_adopt_dry_run_empty_plan_prints_only_banner(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # No standards -> empty report -> format_report() is empty; only the dry-run
    # banner is printed (an empty report must not add a stray blank line).
    from project_standards.cli import _cmd_adopt  # pyright: ignore[reportPrivateUsage]

    rc = _cmd_adopt([], tmp_path, False, True)
    out = capsys.readouterr().out
    assert rc == 0
    assert out == "\n(dry run — no files written)\n"
