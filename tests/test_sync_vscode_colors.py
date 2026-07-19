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

from project_standards.jsonc import (
    _sanitize_jsonc,  # pyright: ignore[reportPrivateUsage]
)
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


def test_rewrite_settings_splices_only_existing_path_colors_value(tmp_path: Path) -> None:
    old_value = (
        f'[\n\t\t{{\n\t\t\t"filePath": "repo/old].md",\n\t\t\t"color": "{_COLOR}"\n\t\t}}\n\t]'
    )
    content = (
        "{\n"
        "\t// preserve this comment with [brackets]\n"
        '\t"nested": {"values": [1, {"text": "] not the end"}]},\n'
        '\t"escaped": "quote: \\" and bracket [",\n'
        f'\t"folder-color.pathColors": {old_value}, // keep inline comment\n'
        '    "tail": "/* not a comment */",\n'
        "}\n"
    )
    settings = _make_settings(tmp_path, content)
    entries = [{"folderPath": "repo/docs/", "color": _COLOR}]
    value_start = content.index(old_value)
    expected_value = json.dumps(entries, indent="\t").replace("\n", "\n\t")

    rewrite_settings(settings, entries)

    assert settings.read_text() == (
        content[:value_start] + expected_value + content[value_start + len(old_value) :]
    )


def test_rewrite_settings_inserts_missing_path_colors_without_reserializing(
    tmp_path: Path,
) -> None:
    nested_value = '{"text": "} in string", "values": [1, {"item": "]"}]}'
    content = f'{{\n\t"nested": {nested_value}\n\t// preserve trailing comment\n}}\n'
    settings = _make_settings(tmp_path, content)
    entries = [{"filePath": "repo/CHANGELOG.md", "color": _COLOR}]
    last_value_end = content.index(nested_value) + len(nested_value)
    close_line_start = content.rindex("\n", 0, content.rindex("}")) + 1
    serialized = json.dumps(entries, indent="\t").replace("\n", "\n\t")
    inserted = f'\t"folder-color.pathColors": {serialized}\n'

    rewrite_settings(settings, entries)

    assert settings.read_text() == (
        content[:last_value_end]
        + ","
        + content[last_value_end:close_line_start]
        + inserted
        + content[close_line_start:]
    )


def test_rewrite_settings_preserves_crlf_when_replacing_last_path_colors(
    tmp_path: Path,
) -> None:
    old_value = (
        "[\r\n"
        "\t\t{\r\n"
        f'\t\t\t"filePath": "repo/old.md",\r\n'
        f'\t\t\t"color": "{_COLOR}"\r\n'
        "\t\t}\r\n"
        "\t]"
    )
    content = (
        f'{{\r\n\t"other": ["] in string"],\r\n\t"folder-color.pathColors": {old_value}\r\n}}\r\n'
    )
    settings = _make_settings(tmp_path, content)
    entries = [{"folderPath": "repo/docs/", "color": _COLOR}]
    value_start = content.index(old_value)
    expected_value = json.dumps(entries, indent="\t").replace("\n", "\r\n\t")

    rewrite_settings(settings, entries)

    assert settings.read_bytes().decode() == (
        content[:value_start] + expected_value + content[value_start + len(old_value) :]
    )


def test_rewrite_settings_preserves_crlf_when_inserting_after_trailing_comma(
    tmp_path: Path,
) -> None:
    content = (
        "{\r\n"
        '\t"nested": {"text": "} in string", "values": ["]"]},\r\n'
        "\t// preserve trailing comment\r\n"
        "}\r\n"
    )
    settings = _make_settings(tmp_path, content)
    entries = [{"filePath": "repo/CHANGELOG.md", "color": _COLOR}]
    close_line_start = content.rindex("\n", 0, content.rindex("}")) + 1
    serialized = json.dumps(entries, indent="\t").replace("\n", "\r\n\t")
    inserted = f'\t"folder-color.pathColors": {serialized}\r\n'

    rewrite_settings(settings, entries)

    assert settings.read_bytes().decode() == (
        content[:close_line_start] + inserted + content[close_line_start:]
    )


def test_preserves_jsonc_header_comments(tmp_path: Path) -> None:
    # The bounded splice must leave comments outside the managed value untouched.
    content = '{\n\t// This is a header comment\n\t"key": "value"\n}\n'
    settings = _make_settings(tmp_path, content)
    rewrite_settings(settings, [])
    result = settings.read_text()
    assert "// This is a header comment" in result


def test_rewrite_settings__jsonc_extensions__accepts_inline_comments_and_trailing_commas(
    tmp_path: Path,
) -> None:
    settings = _make_settings(
        tmp_path,
        """{
\t// preserved header
\t"literal": "https://example.test/* literal */,}", // inline comment
\t"nested": {
\t\t"enabled": true, /* block comment */
\t},
}
""",
    )
    entries = [{"filePath": "repo/CHANGELOG.md", "color": _COLOR}]

    rewrite_settings(settings, entries)

    rewritten = settings.read_text()
    data = json.loads(_sanitize_jsonc(rewritten))
    assert data["literal"] == "https://example.test/* literal */,}"
    assert data["nested"] == {"enabled": True}
    assert data["folder-color.pathColors"] == entries
    assert "// preserved header" in rewritten
    assert "// inline comment" in rewritten
    assert "/* block comment */" in rewritten


def test_rewrite_settings__malformed_jsonc__exits_with_controlled_error(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path, '{"nested": [} /* malformed */')

    with pytest.raises(SystemExit, match=r"^error: cannot parse .*settings\.json:"):
        rewrite_settings(settings, [])


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


# ---------------------------------------------------------------------------
# _repo_root + rewrite_settings edge cases + main() success path
# ---------------------------------------------------------------------------


def test_repo_root_outside_git_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from project_standards.sync_vscode_colors import (
        _repo_root,  # pyright: ignore[reportPrivateUsage]
    )

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="not inside a git repository"):
        _repo_root()


def test_repo_root_returns_git_toplevel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    from project_standards.sync_vscode_colors import (
        _repo_root,  # pyright: ignore[reportPrivateUsage]
    )

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    assert _repo_root().resolve() == tmp_path.resolve()


def test_rewrite_settings_single_line_file(tmp_path: Path) -> None:
    # Root insertion must create a valid member boundary when both braces share a line.
    p = tmp_path / "settings.json"
    p.write_text("{}")
    rewrite_settings(p, [{"filePath": "x/y.md", "color": _COLOR}])
    data = json.loads(p.read_text())
    assert data["folder-color.pathColors"][0]["filePath"] == "x/y.md"


def test_main_writes_colors_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Full default-path flow: repo root from git, both files at their default
    # locations, pathColors written from the include patterns.
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(
        'markdown:\n  frontmatter:\n    include:\n      - "CHANGELOG.md"\n      - "docs/**/*.md"\n'
    )
    settings = tmp_path / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sync-vscode-colors"])
    from project_standards.sync_vscode_colors import main

    main()
    out = capsys.readouterr().out
    assert "synced: 2 path color entries" in out
    data = json.loads(settings.read_text())
    entries = data["folder-color.pathColors"]
    prefix = tmp_path.name
    assert {"filePath": f"{prefix}/CHANGELOG.md", "color": _COLOR} in entries
    assert {"folderPath": f"{prefix}/docs/", "color": _COLOR} in entries
