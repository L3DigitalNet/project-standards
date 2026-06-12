"""Tests for sync-standards-include.

sync-standards-include is the settings.json → .project-standards.yml direction of
the two-way sync pair; sync-vscode-colors is the inverse.  These tests cover the
three public functions (read_path_colors, path_colors_to_patterns, update_include_list)
plus CLI-level error paths via main().
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.sync_standards_include import (
    path_colors_to_patterns,
    read_path_colors,
    update_include_list,
)

_COLOR = "foldercolorizer.color_d7af00"
_OTHER = "foldercolorizer.color_ff0000"


# ---------------------------------------------------------------------------
# path_colors_to_patterns
# ---------------------------------------------------------------------------


def test_file_entry_strips_prefix() -> None:
    entries = [{"filePath": "myrepo/CHANGELOG.md", "color": _COLOR}]
    assert path_colors_to_patterns(entries, "myrepo") == ["CHANGELOG.md"]


def test_folder_entry_appends_glob() -> None:
    entries = [{"folderPath": "myrepo/standards/", "color": _COLOR}]
    assert path_colors_to_patterns(entries, "myrepo") == ["standards/**/*.md"]


def test_non_project_color_skipped() -> None:
    entries = [
        {"filePath": "myrepo/CHANGELOG.md", "color": _COLOR},
        {"folderPath": "myrepo/docs/", "color": _OTHER},
    ]
    assert path_colors_to_patterns(entries, "myrepo") == ["CHANGELOG.md"]


def test_empty_entries_returns_empty() -> None:
    assert path_colors_to_patterns([], "myrepo") == []


def test_mixed_entries_order_preserved() -> None:
    entries = [
        {"filePath": "proj/CHANGELOG.md", "color": _COLOR},
        {"folderPath": "proj/standards/", "color": _COLOR},
        {"folderPath": "proj/meta/", "color": _COLOR},
    ]
    result = path_colors_to_patterns(entries, "proj")
    assert result == ["CHANGELOG.md", "standards/**/*.md", "meta/**/*.md"]


# ---------------------------------------------------------------------------
# read_path_colors
# ---------------------------------------------------------------------------


def _settings(tmp_path: Path, data: object) -> Path:
    """Write *data* as tab-indented settings.json, matching VS Code's own serialization format."""
    p = tmp_path / "settings.json"
    p.write_text(json.dumps(data, indent="\t") + "\n")
    return p


def test_reads_path_colors(tmp_path: Path) -> None:
    entries = [{"filePath": "repo/x.md", "color": _COLOR}]
    p = _settings(tmp_path, {"folder-color.pathColors": entries})
    assert read_path_colors(p) == entries


def test_missing_key_returns_empty(tmp_path: Path) -> None:
    p = _settings(tmp_path, {"other": 1})
    assert read_path_colors(p) == []


def test_strips_jsonc_comments_before_parsing(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    p.write_text('{\n\t// header comment\n\t"folder-color.pathColors": []\n}\n')
    assert read_path_colors(p) == []


# ---------------------------------------------------------------------------
# update_include_list
# ---------------------------------------------------------------------------

# update_include_list targets exactly 4-space indent for `include:` and 6-space for items.
# This template must preserve that indentation or the regex substitution tests are vacuous.
_YAML_TEMPLATE = """\
markdown:
  frontmatter:
    include:
      - "CHANGELOG.md"
      - "standards/**/*.md"
    exclude:
      - "README.md"
"""


def test_replaces_include_items(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(_YAML_TEMPLATE)
    update_include_list(cfg, ["CHANGELOG.md", "meta/**/*.md"])
    result = cfg.read_text()
    assert '      - "CHANGELOG.md"\n' in result
    assert '      - "meta/**/*.md"\n' in result
    assert "standards" not in result


def test_preserves_exclude_block(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(_YAML_TEMPLATE)
    update_include_list(cfg, ["CHANGELOG.md"])
    assert '      - "README.md"\n' in cfg.read_text()


def test_empties_include_list(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(_YAML_TEMPLATE)
    update_include_list(cfg, [])
    text = cfg.read_text()
    assert "    include:\n" in text
    assert "CHANGELOG.md" not in text
    assert "standards" not in text


def test_no_op_when_already_matching(tmp_path: Path) -> None:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(_YAML_TEMPLATE)
    # update_include_list always rewrites (no early-exit comparison), so "no-op" means
    # the substitution produces identical content, not that the write is skipped.
    update_include_list(cfg, ["CHANGELOG.md", "standards/**/*.md"])
    assert '      - "CHANGELOG.md"\n' in cfg.read_text()


def test_missing_include_block_exits(tmp_path: Path) -> None:
    # Requires an existing `    include:` key; refusing to silently insert one at an
    # arbitrary indentation level is safer than guessing the correct YAML nesting.
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text("markdown:\n  frontmatter:\n    required: true\n")
    with pytest.raises(SystemExit):
        update_include_list(cfg, ["CHANGELOG.md"])


# ---------------------------------------------------------------------------
# Integration: main() CLI errors
# ---------------------------------------------------------------------------


def test_main_missing_standards_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # monkeypatch owns sys.argv; mock.patch replaces _repo_root because tmp_path is not a
    # git repo and the real implementation calls `git rev-parse --show-toplevel`.
    from unittest.mock import patch

    settings = tmp_path / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{}\n")

    monkeypatch.setattr(
        "sys.argv",
        ["sync-standards-include", str(tmp_path / "missing.yml"), str(settings)],
    )
    with patch("project_standards.sync_standards_include._repo_root", return_value=tmp_path):
        from project_standards.sync_standards_include import main

        with pytest.raises(SystemExit):
            main()


def test_main_missing_settings_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Same two-layer patching as above.
    from unittest.mock import patch

    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(_YAML_TEMPLATE)

    monkeypatch.setattr(
        "sys.argv",
        ["sync-standards-include", str(cfg), str(tmp_path / ".vscode" / "missing.json")],
    )
    with patch("project_standards.sync_standards_include._repo_root", return_value=tmp_path):
        from project_standards.sync_standards_include import main

        with pytest.raises(SystemExit):
            main()


# ---------------------------------------------------------------------------
# _repo_root + main() success paths (real git repo in tmp)
# ---------------------------------------------------------------------------


def test_path_colors_entry_without_path_keys_is_skipped() -> None:
    # A correctly-colored entry that carries neither filePath nor folderPath
    # contributes nothing (defensive against hand-edited settings).
    assert path_colors_to_patterns([{"color": _COLOR}], "proj") == []


def test_repo_root_outside_git_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from project_standards.sync_standards_include import (
        _repo_root,  # pyright: ignore[reportPrivateUsage]
    )

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="not inside a git repository"):
        _repo_root()


def test_repo_root_returns_git_toplevel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    from project_standards.sync_standards_include import (
        _repo_root,  # pyright: ignore[reportPrivateUsage]
    )

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    assert _repo_root().resolve() == tmp_path.resolve()


def test_main_writes_include_patterns_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Full default-path flow: repo root from git, both files at their default
    # locations, include list rewritten from the colored settings entries.
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    prefix = tmp_path.name
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(_YAML_TEMPLATE)
    settings = tmp_path / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(
        json.dumps(
            {
                "folder-color.pathColors": [
                    {"filePath": f"{prefix}/CHANGELOG.md", "color": _COLOR},
                    {"folderPath": f"{prefix}/docs/", "color": _COLOR},
                ]
            },
            indent="\t",
        )
        + "\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sync-standards-include"])
    from project_standards.sync_standards_include import main

    main()
    out = capsys.readouterr().out
    assert "synced: 2 include patterns" in out
    content = cfg.read_text()
    assert '- "CHANGELOG.md"' in content
    assert '- "docs/**/*.md"' in content


def test_main_no_colored_entries_warns_and_empties(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(_YAML_TEMPLATE)
    settings = tmp_path / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text('{\n\t"folder-color.pathColors": []\n}\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sync-standards-include"])
    from project_standards.sync_standards_include import main

    main()
    captured = capsys.readouterr()
    assert "warning: no color_d7af00 entries" in captured.err
    assert "synced: 0 include patterns" in captured.out
