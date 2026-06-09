import subprocess, sys
from pathlib import Path


def _ps(args, cwd):
    return subprocess.run([sys.executable, "-m", "project_standards.cli", *args],
                          capture_output=True, text=True, cwd=cwd)


def _doc(p: Path, **fm):
    p.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# B\n")


def test_validate_runs_references_when_enabled(tmp_path):
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    references:\n      enabled: true\n    include: ['*.md']\n")
    # duplicate id -> references error -> validate must fail
    _doc(tmp_path / "a.md", schema_version="'1.1'", id="'note-aaaaaa-x'", title="'A'",
         description="'d'", doc_type="'note'", status="'draft'", created="'2026-01-01'",
         updated="'2026-01-02'", tags="[]", aliases="[]", related="[]")
    _doc(tmp_path / "b.md", schema_version="'1.1'", id="'note-aaaaaa-x'", title="'B'",
         description="'d'", doc_type="'note'", status="'draft'", created="'2026-01-01'",
         updated="'2026-01-02'", tags="[]", aliases="[]", related="[]")
    r = _ps(["validate", "--config", str(cfg)], tmp_path)
    assert r.returncode == 1
    assert "duplicate id" in (r.stdout + r.stderr)
