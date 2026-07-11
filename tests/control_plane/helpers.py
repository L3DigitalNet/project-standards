from __future__ import annotations

import shutil
from pathlib import Path

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.package_contract.projection import sync_payload_projection

_FULL = Path("tests/fixtures/package_contract/valid/full")


def installed_distribution(tmp_path: Path) -> InstalledDistribution:
    """Project the full synthetic V2 repository into an installed package root."""
    repository = tmp_path / "repository"
    shutil.copytree(_FULL / "standards", repository / "standards")
    shutil.copytree(_FULL / "catalogs", repository / "catalogs")
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = tmp_path / "installed/project_standards"
    shutil.copytree(package, installed)
    return InstalledDistribution(installed, tool_release="5.0.0")
