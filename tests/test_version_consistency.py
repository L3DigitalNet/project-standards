from __future__ import annotations

import re
import tomllib
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    data = tomllib.loads((_REPO / "pyproject.toml").read_text(encoding="utf-8"))
    version: str = data["project"]["version"]
    return version


def _latest_changelog_version() -> str:
    # Keep-a-Changelog orders newest first, so the first `## [X.Y.Z]` heading is
    # the release this tree represents.
    text = (_REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    assert match is not None, "no versioned CHANGELOG heading found"
    return match.group(1)


def test_pyproject_version_is_not_older_than_latest_changelog_release() -> None:
    package_version = tuple(int(part) for part in _pyproject_version().split("."))
    changelog_version = tuple(int(part) for part in _latest_changelog_version().split("."))

    assert package_version >= changelog_version
