from pathlib import Path

from project_standards.validate_references import build_index, check_dates, check_id_uniqueness


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
