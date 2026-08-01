"""Shared prologue for the two folder-color sync tools.

SYNC_COLOR is a cross-tool contract: both tools read/write entries tagged with
this exact color, so a single definition makes drift impossible.
"""

from __future__ import annotations

import argparse
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


def _argument_parser(description: str) -> argparse.ArgumentParser:
    prog = Path(sys.argv[0]).name
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument("standards_file", nargs="?", metavar="standards-file")
    parser.add_argument("settings_file", nargs="?", metavar="settings-file")
    parser.add_argument("--version", action="version", version=f"{prog} {package_version()}")
    return parser


def resolve_tool_paths(description: str) -> tuple[Path, Path, Path]:
    """Render parser-owned help/version, then resolve the raw positional contract."""
    if "--help" in sys.argv[1:] or "-h" in sys.argv[1:]:
        _argument_parser(description).parse_args(sys.argv[1:])
    if "--version" in sys.argv[1:]:
        _argument_parser(description).parse_args(sys.argv[1:])

    root = repo_root()
    standards_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / ".project-standards.yml"
    settings_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / ".vscode" / "settings.json"

    if not standards_path.is_file():
        sys.exit(f"error: {standards_path} not found")
    if not settings_path.is_file():
        sys.exit(f"error: {settings_path} not found")
    return root, standards_path, settings_path
