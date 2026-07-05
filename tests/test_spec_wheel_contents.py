"""The built wheel must ship the bundled project-spec templates."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path


def test_built_wheel_contains_spec_templates(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parent.parent
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    names = set(zipfile.ZipFile(wheels[0]).namelist())
    for tier in ("light", "standard", "full"):
        assert f"project_standards/specs/templates/spec-{tier}-template.md" in names
