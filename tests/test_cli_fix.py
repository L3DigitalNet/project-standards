from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from project_standards.cli import main as cli_main


def _ps(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "project_standards.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _doc(p: Path, **fm: str) -> None:
    p.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# B\n")


def test_validate_runs_references_when_enabled(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    # duplicate id -> references error -> validate must fail
    _doc(
        tmp_path / "a.md",
        schema_version="'1.1'",
        id="'note-aaaaaa-x'",
        title="'A'",
        description="'d'",
        doc_type="'note'",
        status="'draft'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        tags="[]",
        aliases="[]",
        related="[]",
    )
    _doc(
        tmp_path / "b.md",
        schema_version="'1.1'",
        id="'note-aaaaaa-x'",
        title="'B'",
        description="'d'",
        doc_type="'note'",
        status="'draft'",
        created="'2026-01-01'",
        updated="'2026-01-02'",
        tags="[]",
        aliases="[]",
        related="[]",
    )
    r = _ps(["validate", "--config", str(cfg)], tmp_path)
    assert r.returncode == 1
    assert "duplicate id" in (r.stdout + r.stderr)


def test_fix_leaves_validate_clean_for_type_and_bad_id(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    # `type` instead of doc_type AND an invalid id: format fixes doc_type, then id-fix fixes id.
    (tmp_path / "a.md").write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'wrong'\n"
        "title: 'Hello World'\n"
        "description: 'd'\n"
        "type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-02'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# B\n"
    )
    r = _ps(["fix", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0
    text = (tmp_path / "a.md").read_text()
    assert "doc_type: 'note'" in text
    assert "id: 'note-" in text  # id regenerated from doc_type+title
    # postcondition: a follow-up validate is clean
    assert _ps(["validate", "--config", str(cfg)], tmp_path).returncode == 0


def _full(did: str = "a", doc_id: str = "note-aaaaaa-x") -> str:
    return (
        "---\n"
        "schema_version: '1.1'\n"
        f"id: '{doc_id}'\n"
        f"title: '{did}'\n"
        "description: 'd'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-02'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# B\n"
    )


def test_fix_fails_on_reference_error_when_enabled(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    # Both docs are schema-valid and id-valid, but share an id -> ONLY a reference error.
    (tmp_path / "a.md").write_text(_full("a"))
    (tmp_path / "b.md").write_text(_full("b"))  # same id -> duplicate
    r = _ps(["fix", "--config", str(cfg)], tmp_path)
    assert r.returncode == 1  # CR-001: final validate (incl. references) catches the dup id


def test_fix_skips_under_custom_schema(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    schema: 'custom/my.json'\n    include: ['*.md']\n"
    )
    before = "---\ntitle: X\n---\n# B\n"
    (tmp_path / "a.md").write_text(before)
    r = _ps(["fix", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "a.md").read_text() == before  # CR-001: no writes under custom schema


def test_fix_skips_with_schema_flag(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    before = "---\ntitle: X\n---\n# B\n"
    (tmp_path / "a.md").write_text(before)
    r = _ps(["fix", "--schema", "custom.json", "--config", str(cfg)], tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "a.md").read_text() == before  # CR-001: forwarded --schema -> skip


def test_validate_fails_on_duplicate_keys(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    (tmp_path / "a.md").write_text(
        "---\nschema_version: '1.1'\nid: 'note-aaaaaa-x'\ntitle: 'A'\n"
        "description: 'd'\ndoc_type: 'note'\nstatus: 'draft'\ncreated: '2026-01-01'\n"
        "updated: '2026-01-02'\ntags: []\ntags: ['dup']\naliases: []\nrelated: []\n---\n# B\n"
    )
    r = _ps(["validate", "--config", str(cfg)], tmp_path)
    assert r.returncode == 1  # CR-002: duplicate key -> parse error -> validate fails


# ---------------------------------------------------------------------------
# In-process tests for the `fix` subcommand (cli.py lines 202-229)
# These exercise the fix block in-process so coverage registers the branches.
# ---------------------------------------------------------------------------


def test_fix_help_in_process(capsys: pytest.CaptureFixture[str]) -> None:
    """fix --help prints usage and returns 0."""
    rc = cli_main(["fix", "--help"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "usage" in (captured.out + captured.err).lower()


def test_validate_help_glob_text_matches_real_replace_semantics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--glob replaces the config include list; it is not merely "additional"."""
    rc = cli_main(["validate", "--help"])
    assert rc == 0
    captured = capsys.readouterr()
    text = " ".join((captured.out + captured.err).lower().split())
    assert "additional glob pattern" not in text
    assert "instead of the config include list" in text


def test_fix_bad_config_in_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """fix with a malformed --config (bad YAML) → returns 2."""
    monkeypatch.chdir(tmp_path)
    bad_cfg = tmp_path / "bad.yml"
    bad_cfg.write_text("{\nnot: valid: yaml: [\n")
    rc = cli_main(["fix", "--config", str(bad_cfg)])
    assert rc == 2


def test_fix_schema_flag_skips_in_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """fix with a forwarded --schema flag → skips, returns 0, no writes."""
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    before = "---\ntitle: X\n---\n# B\n"
    doc = tmp_path / "a.md"
    doc.write_text(before)
    rc = cli_main(["fix", "--schema", "custom.json", "--config", str(cfg)])
    assert rc == 0
    assert doc.read_text() == before  # no writes


def test_fix_config_schema_path_skips_in_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """fix when config has a custom schema path → skips, returns 0, no writes."""
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    schema: 'custom/x.json'\n    include: ['*.md']\n"
    )
    before = "---\ntitle: X\n---\n# B\n"
    doc = tmp_path / "a.md"
    doc.write_text(before)
    rc = cli_main(["fix", "--config", str(cfg)])
    assert rc == 0
    assert doc.read_text() == before  # no writes


def test_fix_type_and_bad_id_in_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """fix on a doc with type: + bad id → formats + fixes id, returns 0.

    A follow-up in-process validate also returns 0 (postcondition clean).
    """
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: ['*.md']\n")
    (tmp_path / "a.md").write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'wrong'\n"
        "title: 'Hello World'\n"
        "description: 'd'\n"
        "type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-02'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# B\n"
    )
    rc = cli_main(["fix", "--config", str(cfg)])
    assert rc == 0
    text = (tmp_path / "a.md").read_text()
    assert "doc_type: 'note'" in text
    assert "id: 'note-" in text  # id regenerated from doc_type+title
    # postcondition: in-process validate is also clean
    rc_val = cli_main(["validate", "--config", str(cfg)])
    assert rc_val == 0


def test_fix_fails_on_reference_error_in_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """fix where final validate fails (references enabled + duplicate id) → returns 1."""
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n"
    )
    (tmp_path / "a.md").write_text(_full("a"))
    (tmp_path / "b.md").write_text(_full("b"))  # same id as a -> duplicate
    rc = cli_main(["fix", "--config", str(cfg)])
    assert rc == 1  # CR-001: final validate (incl. references) catches the dup id
