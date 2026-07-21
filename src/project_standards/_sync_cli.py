"""Shared prologue for the two folder-color sync tools.

SYNC_COLOR is a cross-tool contract: both tools read/write entries tagged with
this exact color, so a single definition makes drift impossible.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Final

from project_standards._version import package_version

SYNC_COLOR: Final = "foldercolorizer.color_d7af00"


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit("error: not inside a git repository")
    return Path(result.stdout.strip())


def resolve_tool_paths(help_text: str) -> tuple[Path, Path, Path]:
    """Handle --version/--help, then resolve and require the two tool paths."""
    if "--version" in sys.argv[1:]:
        print(f"{Path(sys.argv[0]).name} {package_version()}")
        raise SystemExit(0)
    if "--help" in sys.argv[1:] or "-h" in sys.argv[1:]:
        print(help_text)
        raise SystemExit(0)

    root = repo_root()
    standards_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / ".project-standards.yml"
    settings_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / ".vscode" / "settings.json"

    if not standards_path.is_file():
        sys.exit(f"error: {standards_path} not found")
    if not settings_path.is_file():
        sys.exit(f"error: {settings_path} not found")
    return root, standards_path, settings_path
