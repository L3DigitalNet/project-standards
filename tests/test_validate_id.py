"""Tests for validate_id — frontmatter id format validation.

Two id formats are tested:
- Standard: {doc_type}-{6-char base36}-{title-slug} for all doc_types except adr.
- ADR:      adr-{NNNN}-{repo-name}-{short-title} (sequential number, not base36).

Coverage spans the pure validation functions (slugify, _validate_adr_id, validate_id),
the file-level check_file, and the main() CLI entry point.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.validate_id import (
    check_file,
    main,
    slugify,
    validate_id,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc(frontmatter: str) -> str:
    """Wrap *frontmatter* in YAML delimiters with a stub body."""
    return f"---\n{frontmatter}\n---\n# Body\n"


def _write(tmp_path: Path, frontmatter: str, name: str = "doc.md") -> Path:
    path = tmp_path / name
    path.write_text(_doc(frontmatter), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_lowercases_and_replaces_spaces() -> None:
    assert slugify("Tailscale ACL Tag") == "tailscale-acl-tag"


def test_slugify_collapses_punctuation_to_single_hyphen() -> None:
    # & and spaces together must not produce double hyphens.
    assert (
        slugify("Standards Adoption & Compliance Procedure")
        == "standards-adoption-compliance-procedure"
    )


def test_slugify_strips_parentheses() -> None:
    assert (
        slugify("Architecture Decision Record (ADR) Standard")
        == "architecture-decision-record-adr-standard"
    )


def test_slugify_preserves_digits() -> None:
    assert slugify("ADR 0001: Use PostgreSQL") == "adr-0001-use-postgresql"


def test_slugify_strips_accents() -> None:
    # NFKD normalisation removes combining accent marks before encoding to ASCII.
    assert slugify("Café Notes") == "cafe-notes"


def test_slugify_strips_leading_and_trailing_hyphens() -> None:
    # Titles starting or ending with punctuation should not produce border hyphens.
    assert slugify("(Leading punctuation)") == "leading-punctuation"


def test_slugify_already_kebab_case() -> None:
    assert slugify("already-kebab") == "already-kebab"


# ---------------------------------------------------------------------------
# ADR id validation (exercised via validate_id with doc_type="adr")
# ---------------------------------------------------------------------------

# A dummy title is passed for ADR tests — validate_id ignores the title for ADRs
# (the short-title portion of the id is set-once, not tracked against the live title).
_ADR_TITLE = "ADR 0001: Some Decision"


def test_adr_id_valid_minimal() -> None:
    assert validate_id("adr-0001-repo-title", "adr", _ADR_TITLE) == []


def test_adr_id_valid_real_example() -> None:
    assert (
        validate_id("adr-0001-homelab-use-postgresql-for-persistent-storage", "adr", _ADR_TITLE)
        == []
    )


def test_adr_id_valid_five_digit_sequence() -> None:
    # Sequence numbers beyond 9999 must still pass.
    assert validate_id("adr-10000-repo-decision", "adr", _ADR_TITLE) == []


def test_adr_id_sequence_too_short_fails() -> None:
    # 3-digit sequence number must be rejected.
    errors = validate_id("adr-001-repo-title", "adr", _ADR_TITLE)
    assert len(errors) == 1
    assert "adr-{NNNN}" in errors[0]


def test_adr_id_missing_adr_prefix_fails() -> None:
    # Even with doc_type="adr", a non-`adr-` prefix must fail.
    errors = validate_id("note-0001-repo-title", "adr", _ADR_TITLE)
    assert errors


def test_adr_id_empty_suffix_after_number_fails() -> None:
    # No repo-name/short-title after the sequence number.
    errors = validate_id("adr-0001", "adr", _ADR_TITLE)
    assert errors


def test_adr_id_uppercase_in_suffix_fails() -> None:
    errors = validate_id("adr-0001-Repo-Title", "adr", _ADR_TITLE)
    assert errors


def test_adr_id_trailing_hyphen_fails() -> None:
    errors = validate_id("adr-0001-repo-", "adr", _ADR_TITLE)
    assert errors


def test_adr_id_non_digit_sequence_fails() -> None:
    errors = validate_id("adr-abcd-repo-title", "adr", _ADR_TITLE)
    assert errors


# ---------------------------------------------------------------------------
# validate_id — ADR dispatch
# ---------------------------------------------------------------------------


def test_validate_id_dispatches_adr_to_adr_validator() -> None:
    # A valid ADR id must pass through validate_id unchanged.
    assert validate_id("adr-0001-myrepo-use-postgres", "adr", "ADR 0001: Use Postgres") == []


def test_validate_id_adr_with_bad_format_fails() -> None:
    errors = validate_id("adr-001-repo-title", "adr", "ADR 001: Decision")
    assert errors
    assert "adr-{NNNN}" in errors[0]


# ---------------------------------------------------------------------------
# validate_id — standard format: segment count
# ---------------------------------------------------------------------------


def test_validate_id_no_hyphens_fails() -> None:
    # An id with no hyphens at all has only one segment.
    errors = validate_id("changelog", "log", "Changelog")
    assert len(errors) == 1
    assert "too few" in errors[0]


def test_validate_id_one_hyphen_fails() -> None:
    # Two segments — missing the title-slug segment.
    errors = validate_id("log-abc123", "log", "Changelog")
    assert len(errors) == 1
    assert "too few" in errors[0]


# ---------------------------------------------------------------------------
# validate_id — standard format: doc_type prefix
# ---------------------------------------------------------------------------


def test_validate_id_valid_passes() -> None:
    assert validate_id("note-a3f9zk-tailscale-acl-gotcha", "note", "Tailscale ACL gotcha") == []


def test_validate_id_prefix_not_a_doc_type_fails() -> None:
    # "markdown" is not in the valid doc_type enum.
    errors = validate_id("markdown-a3f9zk-some-title", "reference", "Some Title")
    assert any("not a valid doc_type" in e for e in errors)


def test_validate_id_prefix_mismatch_fails() -> None:
    # Prefix is a valid doc_type but doesn't match the document's own doc_type.
    errors = validate_id("note-a3f9zk-some-title", "concept", "Some Title")
    assert len(errors) == 1
    assert "does not match" in errors[0]
    assert "concept" in errors[0]


def test_validate_id_prefix_matches_doc_type() -> None:
    # No prefix error when they agree.
    errors = validate_id("reference-a3f9zk-versioning-standard", "reference", "Versioning Standard")
    assert not any("doc_type" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_id — standard format: base-36 segment
# ---------------------------------------------------------------------------


def test_validate_id_base36_too_short_fails() -> None:
    errors = validate_id("note-abc-some-title", "note", "Some Title")
    assert any("base-36" in e for e in errors)


def test_validate_id_base36_too_long_fails() -> None:
    errors = validate_id("note-abcdefg-some-title", "note", "Some Title")
    assert any("base-36" in e for e in errors)


def test_validate_id_base36_uppercase_fails() -> None:
    errors = validate_id("note-A3F9ZK-some-title", "note", "Some Title")
    assert any("base-36" in e for e in errors)


def test_validate_id_base36_all_digits_passes() -> None:
    # Pure-digit 6-char token is valid base-36.
    errors = validate_id("note-012345-some-title", "note", "Some Title")
    assert not any("base-36" in e for e in errors)


def test_validate_id_base36_all_letters_passes() -> None:
    # Pure-alpha 6-char token is valid base-36.
    errors = validate_id("note-abcdef-some-title", "note", "Some Title")
    assert not any("base-36" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_id — standard format: title slug
# ---------------------------------------------------------------------------


def test_validate_id_title_slug_uppercase_fails() -> None:
    errors = validate_id("note-a3f9zk-Some-Title", "note", "Some Title")
    assert any("kebab-case" in e for e in errors)


def test_validate_id_title_slug_mismatch_fails() -> None:
    # Slug doesn't match slugify("Some Title") → "some-title".
    errors = validate_id("note-a3f9zk-wrong-slug", "note", "Some Title")
    assert any("does not match" in e and "some-title" in e for e in errors)


def test_validate_id_title_slug_matches_title() -> None:
    errors = validate_id("note-a3f9zk-some-title", "note", "Some Title")
    assert not any("does not match" in e for e in errors)


def test_validate_id_title_slug_with_punctuation_in_title() -> None:
    # Punctuation in title collapses to hyphens in slug.
    errors = validate_id(
        "runbook-a3f9zk-standards-adoption-compliance-procedure",
        "runbook",
        "Standards Adoption & Compliance Procedure",
    )
    assert errors == []


# ---------------------------------------------------------------------------
# validate_id — multiple simultaneous violations
# ---------------------------------------------------------------------------


def test_validate_id_multiple_errors_reported() -> None:
    # Wrong prefix AND invalid base36 — both should appear.
    errors = validate_id("markdown-abc-wrong", "reference", "Some Title")
    assert any("doc_type" in e for e in errors)
    assert any("base-36" in e for e in errors)


# ---------------------------------------------------------------------------
# check_file
# ---------------------------------------------------------------------------


def test_check_file_no_frontmatter_skipped(tmp_path: Path) -> None:
    # Files without frontmatter are silently skipped (schema validator's responsibility).
    path = tmp_path / "plain.md"
    path.write_text("# No Frontmatter\n\nJust prose.\n", encoding="utf-8")
    assert check_file(path) == []


def test_check_file_invalid_yaml_returns_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_text("---\n: invalid: yaml: [\n---\n# Body\n", encoding="utf-8")
    errors = check_file(path)
    assert len(errors) == 1
    assert "invalid YAML" in errors[0]


def test_check_file_missing_id_skipped(tmp_path: Path) -> None:
    path = _write(tmp_path, "doc_type: note\ntitle: Test\n")
    assert check_file(path) == []


def test_check_file_missing_doc_type_skipped(tmp_path: Path) -> None:
    path = _write(tmp_path, "id: note-a3f9zk-test\ntitle: Test\n")
    assert check_file(path) == []


def test_check_file_invalid_doc_type_skipped(tmp_path: Path) -> None:
    # Unknown doc_type → skip (schema validator catches it, not this one).
    path = _write(tmp_path, "id: foo-a3f9zk-test\ndoc_type: notavalidtype\ntitle: Test\n")
    assert check_file(path) == []


def test_check_file_missing_title_skipped(tmp_path: Path) -> None:
    path = _write(tmp_path, "id: note-a3f9zk-test\ndoc_type: note\n")
    assert check_file(path) == []


def test_check_file_valid_id_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, "id: note-a3f9zk-test-note\ndoc_type: note\ntitle: Test Note\n")
    assert check_file(path) == []


def test_check_file_invalid_id_returns_error(tmp_path: Path) -> None:
    # Old-style id with no base36 segment.
    path = _write(tmp_path, "id: note-standard\ndoc_type: note\ntitle: Standard\n")
    errors = check_file(path)
    assert len(errors) >= 1
    assert "[id]" in errors[0]


def test_check_file_valid_adr_id_passes(tmp_path: Path) -> None:
    # Title must be single-quoted in YAML: an unquoted "ADR 0001: Use Postgres" has ": "
    # mid-value, which PyYAML treats as a nested mapping indicator → ScannerError.
    path = _write(
        tmp_path,
        "id: adr-0001-myrepo-use-postgres\ndoc_type: adr\ntitle: 'ADR 0001: Use Postgres'\n",
    )
    assert check_file(path) == []


def test_check_file_invalid_adr_id_returns_error(tmp_path: Path) -> None:
    # 3-digit sequence number fails ADR pattern. Title also needs quoting (see above).
    path = _write(
        tmp_path,
        "id: adr-001-myrepo-use-postgres\ndoc_type: adr\ntitle: 'ADR 001: Use Postgres'\n",
    )
    errors = check_file(path)
    assert len(errors) == 1
    assert "[id]" in errors[0]


def test_check_file_error_includes_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "id: changelog\ndoc_type: log\ntitle: Changelog\n")
    errors = check_file(path)
    assert any(str(path) in e for e in errors)


# ---------------------------------------------------------------------------
# main() — CLI entry point
# ---------------------------------------------------------------------------


def _cfg(tmp_path: Path, include: list[str]) -> Path:
    """Write a minimal .project-standards.yml with the given include patterns."""
    lines = "markdown:\n  frontmatter:\n    include:\n"
    for pat in include:
        lines += f'      - "{pat}"\n'
    path = tmp_path / ".project-standards.yml"
    path.write_text(lines, encoding="utf-8")
    return path


def test_main_valid_file_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    doc = _write(tmp_path, "id: note-a3f9zk-my-note\ndoc_type: note\ntitle: My Note\n")
    monkeypatch.setattr("sys.argv", ["validate-id", str(doc)])
    assert main() == 0


def test_main_invalid_file_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    doc = _write(tmp_path, "id: old-style\ndoc_type: note\ntitle: Old Style\n")
    monkeypatch.setattr("sys.argv", ["validate-id", str(doc)])
    assert main() == 1


def test_main_quiet_suppresses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = _write(tmp_path, "id: old-style\ndoc_type: note\ntitle: Old Style\n")
    monkeypatch.setattr("sys.argv", ["validate-id", "--quiet", str(doc)])
    rc = main()
    assert rc == 1
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_bad_config_exits_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad_cfg = tmp_path / "bad.yml"
    bad_cfg.write_text(": invalid: yaml: [\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate-id", "--config", str(bad_cfg)])
    assert main() == 2


def test_main_config_include_picks_up_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "id: note-a3f9zk-my-note\ndoc_type: note\ntitle: My Note\n", "doc.md")
    cfg = _cfg(tmp_path, ["doc.md"])
    monkeypatch.setattr("sys.argv", ["validate-id", "--config", str(cfg)])
    # chdir so the glob resolves relative to tmp_path
    monkeypatch.chdir(tmp_path)
    assert main() == 0


def test_main_no_files_and_empty_config_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An empty config with no include patterns → 0 files checked → exit 0.
    # collect_paths falls back to **/*.md when include is empty; chdir to tmp_path
    # so that fallback glob finds nothing instead of scanning the project root.
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate-id", "--config", str(cfg)])
    monkeypatch.chdir(tmp_path)
    assert main() == 0
