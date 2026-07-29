"""Fixture builders shared by the mcp_services facade tests.

Projects the package-contract ``valid/full`` fixture into both construction
shapes the facade accepts — an installed distribution tree and a source
``PackageRepository`` — so tests can prove byte-equivalent inputs produce
equivalent stable facts through either path (NFR-010).
"""

from __future__ import annotations

import importlib
import importlib.util
import shutil
import tomllib
from pathlib import Path
from types import ModuleType

from project_standards.package_contract.projection import sync_payload_projection

FULL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/full"

# The alternate generation drops packages so a facade that merely restamps the
# requested major onto Catalog 5 — or merges the generations — fails the exact
# membership assertions (TC-T2-001).
ALTERNATE_MAJOR_EXCLUDES = {("alpha", "1.0"), ("beta", "1.0")}


def import_mcp_services() -> ModuleType:
    """Import the planned facade package through an in-test existence assertion.

    The plan's RED contract requires a missing planned symbol to fail as a test
    assertion, never as a module collection/import error, so no test module may
    import ``project_standards.mcp_services`` at module scope.
    """
    spec = importlib.util.find_spec("project_standards.mcp_services")
    assert spec is not None, (
        "planned module project_standards.mcp_services is absent; "
        "the T2 facade behavior does not exist yet"
    )
    return importlib.import_module("project_standards.mcp_services")


def build_source_tree(tmp_path: Path) -> Path:
    """Copy the full fixture into a mutable source repository tree."""
    repository = tmp_path / "repository"
    shutil.copytree(FULL_FIXTURE / "standards", repository / "standards")
    shutil.copytree(FULL_FIXTURE / "catalogs", repository / "catalogs")
    return repository


def _render_catalog_source(major: int, packages: list[dict[str, str]]) -> str:
    lines = ['schema_version = "1.0"', f"catalog_major = {major}", ""]
    for entry in packages:
        lines.append("[[packages]]")
        lines.extend(f'{key} = "{entry[key]}"' for key in ("id", "version", "digest", "role"))
        lines.append("")
    return "\n".join(lines)


def build_installed_tree(tmp_path: Path, *, alternate_major: int | None = None) -> Path:
    """Project the fixture into an installed ``project_standards`` package tree.

    The source staging tree is removed before returning so a facade that scans
    sibling source files instead of the installed projection cannot pass.
    ``alternate_major`` adds a second catalog generation with deliberately
    reduced package membership (``ALTERNATE_MAJOR_EXCLUDES``) to the installed
    tree, so generation-distinctness tests can load catalog ``5`` and the
    alternate major from the same installed bytes.
    """
    repository = build_source_tree(tmp_path)
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = tmp_path / "installed/project_standards"
    shutil.copytree(package, installed)
    shutil.rmtree(repository)
    if alternate_major is not None:
        data = tomllib.loads((installed / "catalogs/5.toml").read_text(encoding="utf-8"))
        kept = [
            entry
            for entry in data["packages"]
            if (entry["id"], entry["version"]) not in ALTERNATE_MAJOR_EXCLUDES
        ]
        (installed / f"catalogs/{alternate_major}.toml").write_text(
            _render_catalog_source(alternate_major, kept), encoding="utf-8"
        )
    return installed
