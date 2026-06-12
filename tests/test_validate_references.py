import subprocess
import sys
from pathlib import Path

import pytest

from project_standards.validate_references import (
    build_index,
    check_adr_sequence,
    check_dates,
    check_id_uniqueness,
    check_reciprocity,
    check_references,
)


def _write(p: Path, **fm: str) -> None:
    body = "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# B\n"
    p.write_text(body)


def test_duplicate_id_is_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    _write(
        tmp_path / "b.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    index = build_index([tmp_path / "a.md", tmp_path / "b.md"])
    errors = check_id_uniqueness(index)
    assert len(errors) == 1
    assert "note-aaaaaa-x" in errors[0]


def test_build_index_skips_unreadable_unparseable_and_non_dict(tmp_path: Path) -> None:
    # build_index must tolerate (skip) three classes of bad input rather than raising:
    #   - FrontmatterParseError (duplicate top-level key, rejected since Phase 0 Task 0.5)
    #   - a non-existent path (read_text -> FileNotFoundError, an OSError)
    #   - frontmatter that parses to a non-mapping (a YAML list, not a dict)
    # This pins the two except branches and the `not isinstance(meta, dict)` guard.
    dup = tmp_path / "dup.md"
    dup.write_text("---\ntags: []\ntags: ['x']\n---\n# B\n")
    list_fm = tmp_path / "list.md"
    list_fm.write_text("---\n- a\n- b\n---\n# B\n")
    missing = tmp_path / "missing.md"  # never created -> OSError on read
    index = build_index([dup, list_fm, missing])
    assert index.docs == []
    assert index.by_id == {}


def test_unique_ids_no_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    _write(
        tmp_path / "b.md",
        id="'note-bbbbbb-y'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    index = build_index([tmp_path / "a.md", tmp_path / "b.md"])
    assert check_id_uniqueness(index) == []


def test_created_after_updated_is_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-02-01'",
        updated="'2026-01-01'",
    )
    errors = check_dates(build_index([tmp_path / "a.md"]))
    assert any("created" in e and "updated" in e for e in errors)


def test_reviewed_before_created_is_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-02-01'",
        updated="'2026-02-02'",
        reviewed="'2026-01-01'",
    )
    errors = check_dates(build_index([tmp_path / "a.md"]))
    assert any("reviewed" in e for e in errors)


def test_valid_dates_no_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-02-01'",
        reviewed="'2026-02-02'",
    )
    assert check_dates(build_index([tmp_path / "a.md"])) == []


def test_dangling_reference_is_warning(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        related="['note-zzzzzz-missing']",
    )
    warnings = check_references(build_index([tmp_path / "a.md"]), tmp_path)
    assert len(warnings) == 1
    assert "[warning]" in warnings[0]


def test_reference_to_existing_path_resolves(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "arch.md").write_text("# A\n")
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        related="['docs/arch.md']",
    )
    assert check_references(build_index([tmp_path / "a.md"]), tmp_path) == []


def test_reference_to_known_id_resolves(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        related="['note-bbbbbb-y']",
    )
    _write(
        tmp_path / "b.md",
        id="'note-bbbbbb-y'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    assert check_references(build_index([tmp_path / "a.md", tmp_path / "b.md"]), tmp_path) == []


def test_null_superseded_by_not_flagged(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        superseded_by="null",
    )
    assert check_references(build_index([tmp_path / "a.md"]), tmp_path) == []


def test_anchor_and_absolute_paths_do_not_resolve(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        related="['docs/arch.md#section', '/abs/x.md']",
    )
    warnings = check_references(build_index([tmp_path / "a.md"]), tmp_path)
    assert len(warnings) == 2


def test_missing_supersede_reciprocity_warns(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        superseded_by="'note-bbbbbb-y'",
    )
    _write(
        tmp_path / "b.md",
        id="'note-bbbbbb-y'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )  # no supersedes back
    warnings = check_reciprocity(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert any("reciprocal" in w or "supersedes" in w for w in warnings)


def test_reverse_supersede_reciprocity_warns(tmp_path: Path) -> None:
    # B.supersedes A but A lacks superseded_by -> the OTHER direction (CR-004).
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )  # no superseded_by back
    _write(
        tmp_path / "b.md",
        id="'note-bbbbbb-y'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        supersedes="['note-aaaaaa-x']",
    )
    warnings = check_reciprocity(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert any("superseded_by" in w for w in warnings)


def test_duplicate_adr_number_is_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        id="'adr-0001-repo-one'",
        doc_type="'adr'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    _write(
        tmp_path / "b.md",
        id="'adr-0001-repo-two'",
        doc_type="'adr'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    errors = check_adr_sequence(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert any("0001" in e for e in errors)


def _run_refs(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "project_standards.validate_references", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_references_index_is_repo_wide_under_scoped_invocation(tmp_path: Path) -> None:
    # validate-references is a REPO-WIDE invariant pass: invoking it scoped to one file
    # (as `project-standards validate FILE` forwards) must STILL catch a duplicate id in
    # another managed doc (codex P2 — a scoped index silently misses it).
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    _write(
        tmp_path / "b.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    r = _run_refs(["a.md", "--config", str(cfg)], tmp_path)  # scoped to a.md only
    assert r.returncode == 1  # repo-wide index still sees b.md's duplicate id
    assert "note-aaaaaa-x" in r.stderr


def test_disabled_by_default_exits_0(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-02-01'",
        updated="'2026-01-01'",
    )  # bad dates, but disabled
    r = _run_refs(["--config", str(cfg)], tmp_path)
    assert r.returncode == 0


def test_forwarded_schema_flag_skips_not_errors(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    r = _run_refs(["--schema", "custom.json", "--quiet", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0


def test_no_require_frontmatter_is_accepted(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    r = _run_refs(["--no-require-frontmatter", "--quiet", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0


# In-process main() tests for coverage of the CLI paths not reached by subprocess.


def test_main_disabled_returns_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    monkeypatch.chdir(tmp_path)
    from project_standards.validate_references import main

    assert main(["--config", str(cfg)]) == 0


def test_main_enabled_duplicate_id_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    _write(
        tmp_path / "b.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    monkeypatch.chdir(tmp_path)
    from project_standards.validate_references import main

    rc = main(["--config", str(cfg)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "note-aaaaaa-x" in captured.err


def test_main_custom_schema_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    monkeypatch.chdir(tmp_path)
    from project_standards.validate_references import main

    rc = main(["--schema", "custom.json", "--config", str(cfg)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "custom schema" in captured.out


def test_main_config_error_returns_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(": invalid: yaml: [\n")
    monkeypatch.chdir(tmp_path)
    from project_standards.validate_references import main

    assert main(["--config", str(cfg)]) == 2


def test_main_success_prints_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    monkeypatch.chdir(tmp_path)
    from project_standards.validate_references import main

    rc = main(["--config", str(cfg)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "references valid" in captured.out


def test_build_index_tolerates_utf8_bom(tmp_path: Path) -> None:
    # Regression: build_index previously used encoding="utf-8", which misreads a BOM as
    # content. The BOM prefix (\xef\xbb\xbf) prepends to the first bytes, so the
    # frontmatter fence starts at byte 3 rather than byte 0 — the regex never matches and
    # the file is treated as having no frontmatter, silently dropping it from the index.
    # With fix E (encoding="utf-8-sig") the BOM is stripped and the file is indexed normally.
    bom_file = tmp_path / "bom.md"
    body = (
        "---\n"
        "id: 'note-bomtest-x'\n"
        "doc_type: 'note'\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-02'\n"
        "---\n# Title\n"
    )
    bom_file.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    index = build_index([bom_file])
    assert len(index.docs) == 1, "BOM-prefixed doc must be indexed, not silently dropped"
    assert "note-bomtest-x" in index.by_id


def test_build_index_skips_non_utf8_file(tmp_path: Path) -> None:
    # A non-UTF-8 file must be skipped like an unreadable one, not crash the pass (F1).
    bad = tmp_path / "latin1.md"
    bad.write_bytes(b"---\nid: caf\xe9\n---\n")
    index = build_index([bad])
    assert index.docs == []


def test_main_explicit_missing_config_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The worst silent failure for this validator: a typo'd --config left
    # references disabled and the pass exited 0 with no output (F4).
    monkeypatch.chdir(tmp_path)
    from project_standards.validate_references import main

    rc = main(["--config", "typo.yml"])
    assert rc == 2
    assert "config file not found" in capsys.readouterr().err


def test_empty_string_superseded_by_not_flagged(tmp_path: Path) -> None:
    # Schema-valid but reference-free: '' must be ignored in the scalar form just
    # as it is in the list form, not warned as "unresolved reference ''" (F47).
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        superseded_by="''",
    )
    assert check_references(build_index([tmp_path / "a.md"]), tmp_path) == []


def test_reciprocity_skips_doc_without_id(tmp_path: Path) -> None:
    # A doc lacking its own id used to produce "'None' is superseded_by ..." —
    # a nonsense warning; the missing id is the schema validator's job (F48).
    _write(
        tmp_path / "a.md",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        superseded_by="'note-bbbbbb-y'",
    )
    _write(
        tmp_path / "b.md",
        id="'note-bbbbbb-y'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    warnings = check_reciprocity(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert not any("None" in w for w in warnings)


def test_reciprocity_merges_sets_across_duplicate_ids(tmp_path: Path) -> None:
    # When two docs share an id (itself an error elsewhere), reciprocity must
    # consider the union of their supersede sets, not whichever doc indexed
    # last (F49). Here the second duplicate carries the reciprocal link.
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        superseded_by="'note-dddddd-dup'",
    )
    _write(
        tmp_path / "dup1.md",
        id="'note-dddddd-dup'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    _write(
        tmp_path / "dup2.md",
        id="'note-dddddd-dup'",
        doc_type="'note'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        supersedes="['note-aaaaaa-x']",
    )
    index = build_index([tmp_path / "a.md", tmp_path / "dup1.md", tmp_path / "dup2.md"])
    warnings = check_reciprocity(index)
    assert not any("note-aaaaaa-x" in w and "superseded_by" in w for w in warnings)


def test_duplicate_adr_number_detected_across_zero_padding(tmp_path: Path) -> None:
    # adr-0001-... and adr-00001-... are both ADR number 1; the comparison must
    # be numeric so padding variants cannot dodge the duplicate check (F50).
    _write(
        tmp_path / "a.md",
        id="'adr-0001-repo-one'",
        doc_type="'adr'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    _write(
        tmp_path / "b.md",
        id="'adr-00001-repo-two'",
        doc_type="'adr'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
    )
    errors = check_adr_sequence(build_index([tmp_path / "a.md", tmp_path / "b.md"]))
    assert len(errors) == 1
    assert "adr-0001-repo-one" in errors[0] and "adr-00001-repo-two" in errors[0]


def test_dates_compared_as_dates_not_strings(tmp_path: Path) -> None:
    # Lexicographic comparison orders non-padded dates wrongly; values are now
    # parsed and unparseable ones skipped — shape errors belong to the schema
    # validator (F51).
    _write(
        tmp_path / "a.md",
        id="'note-aaaaaa-x'",
        doc_type="'note'",
        created="'2026-9-1'",  # not ISO-padded: skipped, not mis-ordered
        updated="'2026-10-01'",
    )
    assert check_dates(build_index([tmp_path / "a.md"])) == []
