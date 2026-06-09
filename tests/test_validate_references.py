from pathlib import Path

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
