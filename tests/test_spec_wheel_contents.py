"""The built wheel must ship the bundled project-spec templates."""

from __future__ import annotations

import zipfile
from pathlib import Path


def test_built_wheel_contains_spec_templates(built_wheel: Path) -> None:
    names = set(zipfile.ZipFile(built_wheel).namelist())
    for tier in ("light", "standard", "full"):
        assert f"project_standards/specs/templates/spec-{tier}-template.md" in names
