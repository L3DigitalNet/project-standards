"""Sync folder-color.pathColors in .vscode/settings.json from .project-standards.yml.

Reads the ``markdown.frontmatter.include`` list from a project-standards config
file and writes a matching ``folder-color.pathColors`` block into the VS Code
workspace settings.  Patterns containing ``**`` become ``folderPath`` entries;
everything else becomes ``filePath`` entries.

Usage:
    sync-vscode-colors [standards-file] [settings-file]

Defaults (resolved relative to the git repo root):
    standards-file  .project-standards.yml
    settings-file   .vscode/settings.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from project_standards._version import package_version
from project_standards.jsonc import (
    _sanitize_jsonc,  # pyright: ignore[reportPrivateUsage]  # package-internal parser
)

# The folder-colorizer color that marks managed-docs paths in the user's VS Code
# setup. Cross-file contract: must equal _COLOR in sync_standards_include.py — the
# two tools are inverse round-trips of the same convention, and a mismatch makes
# one direction silently drop every entry the other wrote.
_COLOR = "foldercolorizer.color_d7af00"
_PATH_COLORS_KEY = "folder-color.pathColors"


@dataclass(frozen=True, slots=True)
class _SettingsScan:
    value_span: tuple[int, int] | None
    root_close: int
    last_value_end: int | None
    trailing_comma: bool
    property_indent: str


def _skip_jsonc_trivia(text: str, index: int) -> int:
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index + 2)
            index = len(text) if newline == -1 else newline + 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end == -1 else end + 2
            continue
        break
    return index


def _json_string_end(text: str, start: int) -> int:
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == '"':
            return index + 1
        index += 1
    raise ValueError("unterminated JSON string")


def _jsonc_value_end(text: str, start: int) -> int:
    start = _skip_jsonc_trivia(text, start)
    if start >= len(text):
        raise ValueError("missing JSON value")
    if text[start] == '"':
        return _json_string_end(text, start)
    if text[start] not in "[{":
        index = start
        while index < len(text):
            if text[index] in ",} \t\r\n" or text.startswith(("//", "/*"), index):
                break
            index += 1
        return index

    stack = [text[start]]
    index = start + 1
    while index < len(text):
        next_index = _skip_jsonc_trivia(text, index)
        if next_index != index:
            index = next_index
            continue
        character = text[index]
        if character == '"':
            index = _json_string_end(text, index)
            continue
        if character in "[{":
            stack.append(character)
        elif character in "]}":
            expected = "[" if character == "]" else "{"
            if stack[-1] != expected:
                raise ValueError("mismatched JSON container")
            stack.pop()
            if not stack:
                return index + 1
        index += 1
    raise ValueError("unterminated JSON container")


def _scan_settings(text: str) -> _SettingsScan:
    index = _skip_jsonc_trivia(text, 0)
    if index >= len(text) or text[index] != "{":
        raise ValueError("settings root must be an object")
    index += 1
    value_span: tuple[int, int] | None = None
    last_value_end: int | None = None
    trailing_comma = False
    property_indent = "\t"
    value_indent: str | None = None

    while True:
        index = _skip_jsonc_trivia(text, index)
        if index >= len(text):
            raise ValueError("unterminated settings object")
        if text[index] == "}":
            return _SettingsScan(
                value_span=value_span,
                root_close=index,
                last_value_end=last_value_end,
                trailing_comma=trailing_comma,
                property_indent=(value_indent if value_indent is not None else property_indent),
            )
        if text[index] != '"':
            raise ValueError("settings property name must be a string")

        key_start = index
        key_end = _json_string_end(text, key_start)
        key = json.loads(text[key_start:key_end])
        line_start = text.rfind("\n", 0, key_start) + 1
        candidate_indent = text[line_start:key_start]
        if candidate_indent.strip() == "":
            property_indent = candidate_indent
        index = _skip_jsonc_trivia(text, key_end)
        if index >= len(text) or text[index] != ":":
            raise ValueError("settings property is missing a colon")
        value_start = _skip_jsonc_trivia(text, index + 1)
        value_end = _jsonc_value_end(text, value_start)
        if key == _PATH_COLORS_KEY:
            value_span = (value_start, value_end)
            value_indent = property_indent
        last_value_end = value_end

        index = _skip_jsonc_trivia(text, value_end)
        trailing_comma = index < len(text) and text[index] == ","
        if trailing_comma:
            index += 1
        elif index >= len(text) or text[index] != "}":
            raise ValueError("settings properties must be comma-separated")


def _render_path_colors(path_colors: list[dict[str, str]], indent: str, newline: str) -> str:
    serialized = json.dumps(path_colors, indent="\t")
    return serialized.replace("\n", f"{newline}{indent}")


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit("error: not inside a git repository")
    return Path(result.stdout.strip())


def read_include_patterns(standards_path: Path) -> list[str]:
    """Return the markdown.frontmatter.include list from *standards_path*."""
    raw = yaml.safe_load(standards_path.read_text(encoding="utf-8"))
    data = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
    try:
        patterns = data["markdown"]["frontmatter"]["include"]
    except KeyError, TypeError:
        patterns = None
    if not patterns:
        sys.exit(
            f"error: no include patterns found under markdown.frontmatter.include"
            f" in {standards_path}"
        )
    return [str(p) for p in patterns]


def patterns_to_path_colors(patterns: list[str], prefix: str) -> list[dict[str, str]]:
    """Translate glob patterns to folder-color entry dicts.

    Patterns with ``**`` become ``folderPath`` entries (the directory up to the
    first ``/**``); plain paths become ``filePath`` entries.
    """
    entries: list[dict[str, str]] = []
    for pattern in patterns:
        if "**" in pattern:
            dir_part = pattern.split("/**")[0]
            entries.append({"folderPath": f"{prefix}/{dir_part}/", "color": _COLOR})
        else:
            entries.append({"filePath": f"{prefix}/{pattern}", "color": _COLOR})
    return entries


def rewrite_settings(settings_path: Path, path_colors: list[dict[str, str]]) -> None:
    """Replace folder-color.pathColors in *settings_path*, preserving JSONC comments."""
    original = settings_path.read_text(encoding="utf-8", newline="")
    try:
        json.loads(_sanitize_jsonc(original))
        scanned = _scan_settings(original)
    except (json.JSONDecodeError, ValueError) as exc:
        sys.exit(f"error: cannot parse {settings_path}: {exc}")
    newline = "\r\n" if "\r\n" in original else "\n"
    serialized = _render_path_colors(path_colors, scanned.property_indent, newline)

    if scanned.value_span is not None:
        start, end = scanned.value_span
        rewritten = original[:start] + serialized + original[end:]
    else:
        close_line_start = original.rfind("\n", 0, scanned.root_close) + 1
        if original[close_line_start : scanned.root_close].strip() != "":
            close_line_start = scanned.root_close
        line_prefix = "" if original[:close_line_start].endswith(("\n", "\r")) else newline
        inserted = (
            f'{line_prefix}{scanned.property_indent}"{_PATH_COLORS_KEY}": {serialized}{newline}'
        )
        if scanned.last_value_end is None or scanned.trailing_comma:
            rewritten = original[:close_line_start] + inserted + original[close_line_start:]
        else:
            rewritten = (
                original[: scanned.last_value_end]
                + ","
                + original[scanned.last_value_end : close_line_start]
                + inserted
                + original[close_line_start:]
            )

    settings_path.write_text(rewritten, encoding="utf-8", newline="")


def main() -> None:
    if "--version" in sys.argv[1:]:
        print(f"{Path(sys.argv[0]).name} {package_version()}")
        raise SystemExit(0)
    if "--help" in sys.argv[1:] or "-h" in sys.argv[1:]:
        print(
            f"{Path(sys.argv[0]).name} — sync folder-color.pathColors in .vscode/settings.json "
            "from the markdown.frontmatter.include list in .project-standards.yml.\n"
            "Usage: sync-vscode-colors [standards-file] [settings-file]"
        )
        raise SystemExit(0)

    root = _repo_root()
    standards_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / ".project-standards.yml"
    settings_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / ".vscode" / "settings.json"

    if not standards_path.is_file():
        sys.exit(f"error: {standards_path} not found")
    if not settings_path.is_file():
        sys.exit(f"error: {settings_path} not found")

    prefix = root.name
    patterns = read_include_patterns(standards_path)
    path_colors = patterns_to_path_colors(patterns, prefix)
    rewrite_settings(settings_path, path_colors)

    print(f"synced: {len(path_colors)} path color entries written to {settings_path}")


if __name__ == "__main__":
    main()
