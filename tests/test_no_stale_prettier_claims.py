from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def test_root_readme_names_format_workflow() -> None:
    text = (_REPO / "README.md").read_text(encoding="utf-8")
    assert "Prettier is copy-adopt (no workflow)" not in text
    assert "format.yml" in text  # the Markdown Tooling surface names the new workflow


def test_agent_files_do_not_call_prettier_workflowless() -> None:
    for name in ("CLAUDE.md", "AGENTS.md"):
        text = (_REPO / name).read_text(encoding="utf-8")
        # The Markdown Tooling description must not imply only lint-markdown.yml.
        assert "format.yml" in text
