import subprocess
import sys
from pathlib import Path


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
