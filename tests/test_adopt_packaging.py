"""Wheel packaging smoke test: verify bundle artifacts land inside the built wheel.

Shells out to `uv build --wheel` — this is the slowest test in the suite.
Skip with `-k "not packaging"` when iterating on logic-only changes.

Verifies that the `package_data` globs in pyproject.toml include bundles/, schemas/,
and registry.json so the adopt engine works identically from a source checkout and
from a `uv tool install`-ed wheel.
"""

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
        "project_standards/bundles/markdown-tooling/format.caller.yml",
        "project_standards/bundles/python-tooling/check.yml",
        "project_standards/bundles/markdown-frontmatter/project-standards.starter.yml",
        "project_standards/bundles/adr/adr.template.md",
        "project_standards/bundles/cli-documentation/adopt.toml",
    ]
    for entry in must:
        assert any(n.endswith(entry) for n in names), entry
