"""Tests for sync-vscode-colors.

sync-vscode-colors is the .project-standards.yml → settings.json direction of the
two-way sync pair; sync-standards-include is the inverse.  These tests cover the
three public functions (read_include_patterns, patterns_to_path_colors, rewrite_settings)
plus CLI-level error paths via main().
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.sync_vscode_colors import (
    patterns_to_path_colors,
    read_include_patterns,
    rewrite_settings,
)

_COLOR = "foldercolorizer.color_d7af00"


# ---------------------------------------------------------------------------
# patterns_to_path_colors
# ---------------------------------------------------------------------------


def test_file_pattern_produces_file_path() -> None:
    result = patterns_to_path_colors(["CHANGELOG.md"], "myrepo")
    assert result == [{"filePath": "myrepo/CHANGELOG.md", "color": _COLOR}]


def test_glob_pattern_produces_folder_path() -> None:
    result = patterns_to_path_colors(["standards/**/*.md"], "myrepo")
    assert result == [{"folderPath": "myrepo/standards/", "color": _COLOR}]


def test_mixed_patterns() -> None:
    patterns = ["CHANGELOG.md", "docs/**/*.md", "meta/**/*.md"]
    result = patterns_to_path_colors(patterns, "proj")
    assert result == [
        {"filePath": "proj/CHANGELOG.md", "color": _COLOR},
        {"folderPath": "proj/docs/", "color": _COLOR},
        {"folderPath": "proj/meta/", "color": _COLOR},
    ]


# ---------------------------------------------------------------------------
# read_include_patterns
# ---------------------------------------------------------------------------


def test_reads_include_list(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        "markdown:\n  frontmatter:\n    include:\n      - CHANGELOG.md\n      - docs/**/*.md\n"
    )
    assert read_include_patterns(cfg) == ["CHANGELOG.md", "docs/**/*.md"]


def test_missing_include_key_exits(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    required: true\n")
    with pytest.raises(SystemExit):
        read_include_patterns(cfg)


def test_empty_include_list_exits(tmp_path: Path) -> None:
    # An empty list is treated as a config error: syncing nothing would silently clear all
    # folder-color entries, which is almost certainly unintentional.
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include: []\n")
    with pytest.raises(SystemExit):
        read_include_patterns(cfg)


def test_missing_frontmatter_key_exits(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("other_key: value\n")
    with pytest.raises(SystemExit):
        read_include_patterns(cfg)


# ---------------------------------------------------------------------------
# rewrite_settings
# ---------------------------------------------------------------------------


def _make_settings(tmp_path: Path, content: str) -> Path:
    """Write *content* verbatim as settings.json, allowing JSONC (comments) in the fixture."""
    p = tmp_path / "settings.json"
    p.write_text(content)
    return p


def test_writes_path_colors(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path, '{\n\t"python.linting.enabled": true\n}\n')
    entries = [{"filePath": "repo/CHANGELOG.md", "color": _COLOR}]
    rewrite_settings(settings, entries)
    data = json.loads(settings.read_text())
    assert data["folder-color.pathColors"] == entries


def test_replaces_existing_path_colors(tmp_path: Path) -> None:
    old_entry = [{"filePath": "repo/old.md", "color": _COLOR}]
    settings = _make_settings(
        tmp_path,
        json.dumps({"folder-color.pathColors": old_entry, "other": 1}, indent="\t") + "\n",
    )
    new_entries = [{"folderPath": "repo/docs/", "color": _COLOR}]
    rewrite_settings(settings, new_entries)
    data = json.loads(settings.read_text())
    assert data["folder-color.pathColors"] == new_entries
    assert data["other"] == 1


def test_preserves_jsonc_header_comments(tmp_path: Path) -> None:
    # VS Code writes settings.json as JSONC (JSON with comments); json.dumps strips them,
    # so rewrite_settings must capture and re-inject leading // lines before serializing.
    content = '{\n\t// This is a header comment\n\t"key": "value"\n}\n'
    settings = _make_settings(tmp_path, content)
    rewrite_settings(settings, [])
    result = settings.read_text()
    assert "// This is a header comment" in result


def test_output_ends_with_newline(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path, '{\n\t"x": 1\n}\n')
    rewrite_settings(settings, [])
    assert settings.read_text().endswith("\n")


# ---------------------------------------------------------------------------
# Integration: main() CLI errors
# ---------------------------------------------------------------------------


def test_main_missing_standards_file_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # monkeypatch owns sys.argv; mock.patch replaces _repo_root because tmp_path is not a
    # git repo and the real implementation calls `git rev-parse --show-toplevel`.
    from unittest.mock import patch

    settings = tmp_path / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{}\n")

    monkeypatch.setattr(
        "sys.argv", ["sync-vscode-colors", str(tmp_path / "missing.yml"), str(settings)]
    )
    with patch("project_standards.sync_vscode_colors._repo_root", return_value=tmp_path):
        from project_standards.sync_vscode_colors import main

        with pytest.raises(SystemExit):
            main()


def test_main_missing_settings_file_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Same two-layer patching as above.
    from unittest.mock import patch

    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    include:\n      - CHANGELOG.md\n")

    monkeypatch.setattr(
        "sys.argv",
        ["sync-vscode-colors", str(cfg), str(tmp_path / ".vscode" / "missing.json")],
    )
    with patch("project_standards.sync_vscode_colors._repo_root", return_value=tmp_path):
        from project_standards.sync_vscode_colors import main

        with pytest.raises(SystemExit):
            main()
