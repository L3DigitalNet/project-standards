"""Sync markdown.frontmatter.include in .project-standards.yml from .vscode/settings.json.

Reads ``folder-color.pathColors`` from the VS Code workspace settings and rewrites the
``markdown.frontmatter.include`` list so that it exactly matches the entries colored
``foldercolorizer.color_d7af00``:

- ``filePath`` entries → exact path patterns (prefix stripped).
- ``folderPath`` entries → ``<dir>/**/*.md`` glob patterns (prefix + trailing slash stripped).
- Entries with any other color are excluded from the list.

Note: folder patterns are always reconstructed with the ``/**/*.md`` suffix.  If the
original pattern used a different glob (e.g. ``/**`` or ``/**/*.yaml``), the round-trip
will not reproduce it exactly.

Usage:
    sync-standards-include [standards-file] [settings-file]

Defaults (resolved relative to the git repo root):
    standards-file  .project-standards.yml
    settings-file   .vscode/settings.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, cast

from project_standards._sync_cli import SYNC_COLOR as _COLOR
from project_standards._sync_cli import resolve_tool_paths
from project_standards.jsonc import sanitize_jsonc


def read_path_colors(settings_path: Path) -> list[dict[str, str]]:
    """Return all folder-color.pathColors entries from *settings_path*."""
    original = settings_path.read_text(encoding="utf-8")
    try:
        data = cast(dict[str, Any], json.loads(sanitize_jsonc(original)))
    except json.JSONDecodeError as exc:
        sys.exit(f"error: cannot parse {settings_path}: {exc}")
    raw = data.get("folder-color.pathColors", [])
    return cast(list[dict[str, str]], raw if isinstance(raw, list) else [])


def path_colors_to_patterns(entries: list[dict[str, str]], prefix: str) -> list[str]:
    """Derive include patterns from *entries* that have the project color.

    ``filePath`` entries become exact path patterns; ``folderPath`` entries become
    ``<dir>/**/*.md`` globs.  Entries without the expected color are silently skipped.
    """
    patterns: list[str] = []
    for entry in entries:
        if entry.get("color") != _COLOR:
            continue
        if "filePath" in entry:
            stripped = entry["filePath"].removeprefix(f"{prefix}/")
            patterns.append(stripped)
        elif "folderPath" in entry:
            stripped = entry["folderPath"].removeprefix(f"{prefix}/").rstrip("/")
            patterns.append(f"{stripped}/**/*.md")
    return patterns


def update_include_list(standards_path: Path, new_patterns: list[str]) -> None:
    """Replace the markdown.frontmatter.include block in-place, preserving all other content.

    Only the list items under ``    include:`` (4-space indent) are replaced; surrounding
    keys, comments, and the rest of the file are untouched.  Raises SystemExit if the
    include block cannot be located.
    """
    content = standards_path.read_text(encoding="utf-8")
    new_items = "".join(f'      - "{p}"\n' for p in new_patterns)
    updated, replacements = re.subn(
        (
            r"(?m)(^markdown:\n"
            r"(?:^[ \t]*(?:#[^\n]*)?\n|"
            r"^  (?!frontmatter:|[ \t]*(?:#|$))[^\n]*\n)*"
            r"^  frontmatter:\n"
            r"(?:^[ \t]*(?:#[^\n]*)?\n|"
            r"^    (?!include:|[ \t]*(?:#|$))[^\n]*\n)*"
            r"^    include:\n)"
            r"(?:^      [^\n]*\n)*"
        ),
        lambda match: match.group(1) + new_items,
        content,
        count=1,
    )
    if replacements == 0:
        sys.exit(
            f"error: could not locate 'include:' block in {standards_path}"
            " — only block-style YAML is supported"
        )
    standards_path.write_text(updated, encoding="utf-8")


def main() -> None:
    root, standards_path, settings_path = resolve_tool_paths(
        help_text=(
            f"{Path(sys.argv[0]).name} — sync markdown.frontmatter.include in "
            ".project-standards.yml from the folder-color.pathColors entries in "
            ".vscode/settings.json.\n"
            "Usage: sync-standards-include [standards-file] [settings-file]"
        )
    )

    prefix = root.name
    entries = read_path_colors(settings_path)
    patterns = path_colors_to_patterns(entries, prefix)

    if not patterns:
        print(
            "warning: no color_d7af00 entries found — include list will be emptied",
            file=sys.stderr,
        )

    update_include_list(standards_path, patterns)
    print(f"synced: {len(patterns)} include patterns written to {standards_path}")


if __name__ == "__main__":
    main()
