from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def test_wheel_contains_bundles_and_manifests(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    names = zipfile.ZipFile(wheels[0]).namelist()
    must = [
        "project_standards/bundles/_shared/editorconfig",
        "project_standards/bundles/markdown-tooling/adopt.toml",
        "project_standards/bundles/python-tooling/check.yml",
        "project_standards/bundles/markdown-frontmatter/project-standards.starter.yml",
        "project_standards/bundles/adr/adr.template.md",
    ]
    for entry in must:
        assert any(n.endswith(entry) for n in names), entry
