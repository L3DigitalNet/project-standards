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


def test_current_authority_docs_match_catalog_versions() -> None:
    catalog = tomllib.loads((_REPO / ".standards/catalog.toml").read_text(encoding="utf-8"))
    standards = catalog["standards"]
    markdown_version = standards["markdown-tooling"]["default"]
    handoff_version = standards["agent-handoff"]["default"]
    authoring_versions = standards["standard-bundle-authoring"]["available"]
    authoring_version = max(
        authoring_versions,
        key=lambda value: tuple(int(part) for part in value.split(".")),
    )
    versioning = (_REPO / "meta/versioning.md").read_text(encoding="utf-8")
    conventions = (_REPO / "docs/handoff/conventions.md").read_text(encoding="utf-8")
    markdown_line = next(
        line for line in versioning.splitlines() if "Markdown Tooling contract version" in line
    )
    handoff_line = next(
        line for line in versioning.splitlines() if "Agent Handoff contract version" in line
    )

    assert f"package release `{markdown_version}`" in markdown_line
    assert f"package release `{handoff_version}`" in handoff_line
    assert f"Standard Bundle Authoring {authoring_version} workflow" in conventions
