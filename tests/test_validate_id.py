"""Tests for validate_id — frontmatter id format validation.

Two id formats are tested:
- Standard: {doc_type}-{6-char base36}-{readable-slug} for all doc_types except adr.
- ADR:      adr-{NNNN}-{repo-name}-{short-title} (sequential number, not base36).

The readable-slug is validated as well-formed lowercase kebab-case but is NOT checked
against the current title — it is frozen at creation time to keep ids stable.

Coverage spans the pure validation functions (slugify, validate_id), the file-level
check_file, and the main() CLI entry point.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.validate_id import (
    _replace_frontmatter_id,  # pyright: ignore[reportPrivateUsage]
    check_file,
    fix_file,
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


def test_adr_id_valid_minimal() -> None:
    assert validate_id("adr-0001-repo-title", "adr") == []


def test_adr_id_valid_real_example() -> None:
    assert validate_id("adr-0001-homelab-use-postgresql-for-persistent-storage", "adr") == []


def test_adr_id_valid_five_digit_sequence() -> None:
    # Sequence numbers beyond 9999 must still pass.
    assert validate_id("adr-10000-repo-decision", "adr") == []


def test_adr_id_sequence_too_short_fails() -> None:
    # 3-digit sequence number must be rejected.
    errors = validate_id("adr-001-repo-title", "adr")
    assert len(errors) == 1
    assert "adr-{NNNN}" in errors[0]


def test_adr_id_missing_adr_prefix_fails() -> None:
    # Even with doc_type="adr", a non-`adr-` prefix must fail.
    errors = validate_id("note-0001-repo-title", "adr")
    assert errors


def test_adr_id_empty_suffix_after_number_fails() -> None:
    # No repo-name/short-title after the sequence number.
    errors = validate_id("adr-0001", "adr")
    assert errors


def test_adr_id_only_repo_name_no_short_title_fails() -> None:
    # Three segments total (adr, NNNN, repo) but missing the required short-title segment.
    # "adr-0001-repo" looks plausible but is incomplete — the contract is
    # adr-{NNNN}-{repo-name}-{short-title} so at least 4 segments are required.
    errors = validate_id("adr-0001-repo", "adr")
    assert errors


def test_adr_id_uppercase_in_suffix_fails() -> None:
    errors = validate_id("adr-0001-Repo-Title", "adr")
    assert errors


def test_adr_id_trailing_hyphen_fails() -> None:
    errors = validate_id("adr-0001-repo-", "adr")
    assert errors


def test_adr_id_non_digit_sequence_fails() -> None:
    errors = validate_id("adr-abcd-repo-title", "adr")
    assert errors


# ---------------------------------------------------------------------------
# validate_id — ADR dispatch
# ---------------------------------------------------------------------------


def test_validate_id_dispatches_adr_to_adr_validator() -> None:
    # A valid ADR id must pass through validate_id unchanged.
    assert validate_id("adr-0001-myrepo-use-postgres", "adr") == []


def test_validate_id_adr_with_bad_format_fails() -> None:
    errors = validate_id("adr-001-repo-title", "adr")
    assert errors
    assert "adr-{NNNN}" in errors[0]


# ---------------------------------------------------------------------------
# validate_id — standard format: segment count
# ---------------------------------------------------------------------------


def test_validate_id_no_hyphens_fails() -> None:
    # An id with no hyphens at all has only one segment.
    errors = validate_id("changelog", "log")
    assert len(errors) == 1
    assert "too few" in errors[0]


def test_validate_id_one_hyphen_fails() -> None:
    # Two segments — missing the readable-slug segment.
    errors = validate_id("log-abc123", "log")
    assert len(errors) == 1
    assert "too few" in errors[0]


# ---------------------------------------------------------------------------
# validate_id — standard format: doc_type prefix
# ---------------------------------------------------------------------------


def test_validate_id_valid_passes() -> None:
    assert validate_id("note-a3f9zk-tailscale-acl-gotcha", "note") == []


def test_validate_id_prefix_not_a_doc_type_fails() -> None:
    # "markdown" is not in the valid doc_type enum.
    errors = validate_id("markdown-a3f9zk-some-title", "reference")
    assert any("not a valid doc_type" in e for e in errors)


def test_validate_id_prefix_mismatch_fails() -> None:
    # Prefix is a valid doc_type but doesn't match the document's own doc_type.
    errors = validate_id("note-a3f9zk-some-title", "concept")
    assert len(errors) == 1
    assert "does not match" in errors[0]
    assert "concept" in errors[0]


def test_validate_id_prefix_matches_doc_type() -> None:
    # No prefix error when they agree.
    errors = validate_id("reference-a3f9zk-versioning-standard", "reference")
    assert not any("doc_type" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_id — standard format: base-36 segment
# ---------------------------------------------------------------------------


def test_validate_id_base36_too_short_fails() -> None:
    errors = validate_id("note-abc-some-title", "note")
    assert any("base-36" in e for e in errors)


def test_validate_id_base36_too_long_fails() -> None:
    errors = validate_id("note-abcdefg-some-title", "note")
    assert any("base-36" in e for e in errors)


def test_validate_id_base36_uppercase_fails() -> None:
    errors = validate_id("note-A3F9ZK-some-title", "note")
    assert any("base-36" in e for e in errors)


def test_validate_id_base36_all_digits_passes() -> None:
    # Pure-digit 6-char token is valid base-36.
    errors = validate_id("note-012345-some-title", "note")
    assert not any("base-36" in e for e in errors)


def test_validate_id_base36_all_letters_passes() -> None:
    # Pure-alpha 6-char token is valid base-36.
    errors = validate_id("note-abcdef-some-title", "note")
    assert not any("base-36" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_id — standard format: readable slug
# ---------------------------------------------------------------------------


def test_validate_id_readable_slug_uppercase_fails() -> None:
    # Uppercase in the slug violates the kebab-case constraint.
    errors = validate_id("note-a3f9zk-Some-Title", "note")
    assert any("kebab-case" in e for e in errors)


def test_validate_id_readable_slug_with_internal_hyphens_passes() -> None:
    # Multi-word slugs with hyphens are valid (this is the expected normal form).
    errors = validate_id("runbook-a3f9zk-standards-adoption-compliance-procedure", "runbook")
    assert errors == []


def test_validate_id_readable_slug_double_hyphen_fails() -> None:
    # Consecutive hyphens in the readable-slug are not valid kebab-case.
    # slugify() never produces them, but hand-crafted ids can.
    errors = validate_id("note-a3f9zk-bad--slug", "note")
    assert any("kebab-case" in e for e in errors)


def test_adr_id_double_hyphen_in_suffix_fails() -> None:
    # Consecutive hyphens in the repo-name/short-title suffix violate the kebab contract.
    errors = validate_id("adr-0001-repo--title", "adr")
    assert errors


# ---------------------------------------------------------------------------
# validate_id — multiple simultaneous violations
# ---------------------------------------------------------------------------


def test_validate_id_multiple_errors_reported() -> None:
    # Wrong prefix AND invalid base36 — both should appear.
    errors = validate_id("markdown-abc-wrong", "reference")
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


def test_check_file_valid_id_without_title_passes(tmp_path: Path) -> None:
    # title is no longer required by this validator — schema validator owns that check.
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


def test_main_schema_flag_skips_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # When --schema is provided, validate-id must exit 0 regardless of id format.
    # A custom schema signals non-standard id conventions; the bundled base36 rules
    # must not produce false positives against those files.
    monkeypatch.chdir(tmp_path)
    bad_id_file = tmp_path / "doc.md"
    bad_id_file.write_text(
        "---\nschema_version: '1.1'\nid: 'old-style-id'\ndoc_type: 'note'\n---\n# Doc\n",
        encoding="utf-8",
    )
    schema_override = tmp_path / "custom.json"
    schema_override.write_text("{}", encoding="utf-8")
    rc = main(["--schema", str(schema_override), str(bad_id_file)])
    assert rc == 0


def test_main_schema_flag_quiet_suppresses_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    schema_override = tmp_path / "custom.json"
    schema_override.write_text("{}", encoding="utf-8")
    rc = main(["--schema", str(schema_override), "--quiet"])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_main_config_custom_schema_skips_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A custom schema configured via .project-standards.yml must also skip id validation —
    # the reusable workflow runs `validate-id --config ...`, so consumers with a config-level
    # custom schema must not get false positives from the bundled base36 rules.
    monkeypatch.chdir(tmp_path)
    custom_schema = tmp_path / "custom.json"
    custom_schema.write_text("{}", encoding="utf-8")
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        f"markdown:\n  frontmatter:\n    schema: '{custom_schema}'\n",
        encoding="utf-8",
    )
    bad_id_file = tmp_path / "doc.md"
    bad_id_file.write_text(
        "---\nschema_version: '1.1'\nid: 'old-style-id'\ndoc_type: 'note'\n---\n# Doc\n",
        encoding="utf-8",
    )
    rc = main(["--config", str(cfg), str(bad_id_file)])
    assert rc == 0


# ---------------------------------------------------------------------------
# _replace_frontmatter_id
# ---------------------------------------------------------------------------


def test_replace_frontmatter_id_single_quoted(tmp_path: Path) -> None:
    text = "---\nid: 'old-id'\ndoc_type: 'note'\n---\n# Body\n"
    result = _replace_frontmatter_id(text, "note-a3f9zk-new-slug")
    assert "id: 'note-a3f9zk-new-slug'" in result
    assert "old-id" not in result
    assert "# Body" in result  # body untouched


def test_replace_frontmatter_id_double_quoted(tmp_path: Path) -> None:
    text = '---\nid: "old-id"\ndoc_type: "note"\n---\n# Body\n'
    result = _replace_frontmatter_id(text, "note-a3f9zk-new-slug")
    assert "id: 'note-a3f9zk-new-slug'" in result


def test_replace_frontmatter_id_unquoted(tmp_path: Path) -> None:
    text = "---\nid: old-id\ndoc_type: note\n---\n# Body\n"
    result = _replace_frontmatter_id(text, "note-a3f9zk-new-slug")
    assert "id: 'note-a3f9zk-new-slug'" in result


def test_replace_frontmatter_id_no_frontmatter_unchanged(tmp_path: Path) -> None:
    text = "# No frontmatter\njust body text\n"
    assert _replace_frontmatter_id(text, "note-a3f9zk-new-slug") == text


def test_replace_frontmatter_id_preserves_inline_comment(tmp_path: Path) -> None:
    # An inline comment on the id: line must survive the replacement unchanged.
    text = "---\nid: 'old-id'  # frozen at creation\ntitle: Test\n---\n# Body\n"
    result = _replace_frontmatter_id(text, "note-abc123-test")
    assert "id: 'note-abc123-test'  # frozen at creation" in result
    assert "old-id" not in result


def test_replace_frontmatter_id_body_id_not_replaced(tmp_path: Path) -> None:
    # An `id:` line in the body (after the closing ---) must not be replaced.
    text = "---\nid: 'old-id'\n---\n# Body\nid: 'body-field'\n"
    result = _replace_frontmatter_id(text, "note-a3f9zk-new-slug")
    assert "id: 'body-field'" in result  # body id untouched


# ---------------------------------------------------------------------------
# fix_file
# ---------------------------------------------------------------------------

_FULL_FM = (
    "---\n"
    "schema_version: '1.1'\n"
    "id: 'old-kebab-id'\n"
    "title: 'Tailscale ACL gotcha'\n"
    "description: 'Test.'\n"
    "doc_type: 'note'\n"
    "status: 'active'\n"
    "created: '2026-06-01'\n"
    "updated: '2026-06-08'\n"
    "tags: []\naliases: []\nrelated: []\n"
    "---\n# Body\n"
)


def test_fix_file_rewrites_invalid_id(tmp_path: Path) -> None:
    f = tmp_path / "doc.md"
    f.write_text(_FULL_FM, encoding="utf-8")
    new_id = fix_file(f)
    assert new_id is not None
    # Format: note-{6-char base36}-tailscale-acl-gotcha
    assert new_id.startswith("note-")
    parts = new_id.split("-", 2)
    assert len(parts) == 3
    assert len(parts[1]) == 6 and parts[1].isalnum()
    assert parts[2] == "tailscale-acl-gotcha"
    # File was updated
    assert f"id: '{new_id}'" in f.read_text()


def test_fix_file_already_valid_returns_none(tmp_path: Path) -> None:
    text = _FULL_FM.replace("id: 'old-kebab-id'", "id: 'note-a3f9zk-tailscale-acl-gotcha'")
    f = tmp_path / "doc.md"
    f.write_text(text, encoding="utf-8")
    assert fix_file(f) is None
    assert "note-a3f9zk-tailscale-acl-gotcha" in f.read_text()  # unchanged


def test_fix_file_adr_returns_none(tmp_path: Path) -> None:
    text = (
        "---\nschema_version: '1.1'\nid: 'bad-adr-id'\ntitle: 'Use Postgres'\n"
        "description: 'Test.'\ndoc_type: 'adr'\nstatus: 'active'\n"
        "created: '2026-06-01'\nupdated: '2026-06-08'\ntags: []\naliases: []\nrelated: []\n---\n"
    )
    f = tmp_path / "adr.md"
    f.write_text(text, encoding="utf-8")
    assert fix_file(f) is None  # ADR — needs repo-name


def test_fix_file_no_title_returns_none(tmp_path: Path) -> None:
    text = (
        "---\nschema_version: '1.1'\nid: 'old-id'\ndoc_type: 'note'\n"
        "description: 'Test.'\nstatus: 'active'\ncreated: '2026-06-01'\n"
        "updated: '2026-06-08'\ntags: []\naliases: []\nrelated: []\n---\n"
    )
    f = tmp_path / "doc.md"
    f.write_text(text, encoding="utf-8")
    assert fix_file(f) is None


def test_fix_file_preserves_mixed_line_endings(tmp_path: Path) -> None:
    # In a file with mixed endings, bare-LF lines must NOT be converted to CRLF.
    # Each line's original ending is kept byte-exact; only the id: value changes.
    mixed = (
        "---\r\n"
        "schema_version: '1.1'\r\n"
        "id: 'old-kebab-id'\n"  # bare LF — must stay LF after fix
        "title: 'Tailscale ACL gotcha'\r\n"
        "description: 'Test.'\r\n"
        "doc_type: 'note'\r\n"
        "status: 'active'\r\n"
        "created: '2026-06-01'\r\n"
        "updated: '2026-06-08'\r\n"
        "tags: []\r\naliases: []\r\nrelated: []\r\n"
        "---\r\n# Body\r\n"
    )
    path = tmp_path / "mixed.md"
    path.write_bytes(mixed.encode("utf-8"))
    new_id = fix_file(path)
    assert new_id is not None
    written = path.read_bytes()
    # id: line originally had bare LF — must still have bare LF after fix.
    assert (f"id: '{new_id}'\n").encode() in written
    assert (f"id: '{new_id}'\r\n").encode() not in written
    # Unrelated CRLF lines must remain CRLF (no normalisation side-effects).
    assert b"schema_version: '1.1'\r\n" in written


def test_fix_file_preserves_crlf_line_endings(tmp_path: Path) -> None:
    # fix_file must not normalise CRLF → LF when writing back.  On all platforms,
    # read_text() translates \r\n to \n; the function must detect the original style
    # and restore it in the output.
    crlf = (
        "---\r\n"
        "schema_version: '1.1'\r\n"
        "id: 'old-kebab-id'\r\n"
        "title: 'Tailscale ACL gotcha'\r\n"
        "description: 'Test.'\r\n"
        "doc_type: 'note'\r\n"
        "status: 'active'\r\n"
        "created: '2026-06-01'\r\n"
        "updated: '2026-06-08'\r\n"
        "tags: []\r\naliases: []\r\nrelated: []\r\n"
        "---\r\n# Body\r\n"
    )
    path = tmp_path / "crlf.md"
    path.write_bytes(crlf.encode("utf-8"))
    new_id = fix_file(path)
    assert new_id is not None
    written = path.read_bytes()
    assert b"\r\n" in written, "CRLF line endings must be preserved after fix"
    assert b"\r\n---\r\n" in written, "frontmatter delimiters must retain CRLF"
    assert b"id: '" + new_id.encode() + b"'" in written


# ---------------------------------------------------------------------------
# main --fix
# ---------------------------------------------------------------------------


def test_main_fix_rewrites_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "doc.md"
    f.write_text(_FULL_FM, encoding="utf-8")
    rc = main(["--fix", str(f)])
    assert rc == 0
    content = f.read_text()
    # id must now pass validation
    import re as _re

    new_id_match = _re.search(r"^id: '([^']+)'", content, _re.MULTILINE)
    assert new_id_match is not None
    new_id = new_id_match.group(1)
    assert new_id.startswith("note-")
    from project_standards.validate_id import validate_id as _validate_id

    assert _validate_id(new_id, "note") == []


def test_main_fix_adr_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ADR files can't be auto-fixed — exit 1 so the user knows manual work is needed.
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "adr.md"
    f.write_text(
        "---\nschema_version: '1.1'\nid: 'bad-adr'\ntitle: 'Use Postgres'\n"
        "description: 'Test.'\ndoc_type: 'adr'\nstatus: 'active'\n"
        "created: '2026-06-01'\nupdated: '2026-06-08'\ntags: []\naliases: []\nrelated: []\n---\n",
        encoding="utf-8",
    )
    rc = main(["--fix", str(f)])
    assert rc == 1


def test_main_fix_already_valid_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    text = _FULL_FM.replace("id: 'old-kebab-id'", "id: 'note-a3f9zk-tailscale-acl-gotcha'")
    f = tmp_path / "doc.md"
    f.write_text(text, encoding="utf-8")
    rc = main(["--fix", str(f)])
    assert rc == 0


def test_check_file_non_utf8_reports_error_not_traceback(tmp_path: Path) -> None:
    # UnicodeDecodeError must be handled like an unreadable file (F1).
    bad = tmp_path / "latin1.md"
    bad.write_bytes(b"---\nid: caf\xe9\n---\n")
    errors = check_file(bad)
    assert len(errors) == 1
    assert "cannot read" in errors[0]
