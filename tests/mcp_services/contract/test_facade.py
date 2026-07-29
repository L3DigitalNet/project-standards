"""Contract: the facade package is SDK-free and exports protocol-neutral types.

TC-T2-004 (IR-004): the service layer must be importable and fully usable with
no MCP SDK importable at all, export exactly the facade and DTO/error names,
and keep every SDK type out of its public surface (ADR 0025 adapter direction).
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from tests.mcp_services.helpers import FULL_FIXTURE, import_mcp_services

_FROZEN_EXPORTS = {
    "McpServiceFacade",
    "CatalogDescriptor",
    "StandardDescriptor",
    "ResourceDescriptor",
    "ResourceContent",
    "ProviderDescriptor",
    "RelationshipSet",
    "ServiceError",
}
_FROZEN_T2_METHODS = {"from_installed", "from_source", "catalog", "standard", "resource"}
_FORBIDDEN_IMPORT_ROOTS = ("mcp", "project_standards.mcp_server")

# Runs the facade end to end in a fresh interpreter whose import machinery
# refuses the SDK and the adapter package outright: construction, catalog,
# descriptor, and digest-verified resource reads must all work without them.
_BLOCKED_SDK_PROBE = """
import sys


class _BlockSdk:
    def find_spec(self, name, path=None, target=None):
        if (
            name == "mcp"
            or name.startswith("mcp.")
            or name.startswith("project_standards.mcp_server")
        ):
            raise ImportError(f"import of {{name!r}} is blocked by the T2 contract test")
        return None


sys.meta_path.insert(0, _BlockSdk())

from pathlib import Path

from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_services import McpServiceFacade
from project_standards.package_contract.repository import build_package_repository

facade = McpServiceFacade.from_source(
    build_package_repository(Path({fixture!r}), catalog_major=5), CatalogMajor("5")
)
catalog = facade.catalog()
assert catalog.catalog_major == 5
assert len(catalog.standards) == 5
descriptor = facade.standard("alpha", "2.0")
assert descriptor.title == "Alpha"
content = facade.resource("alpha", "2.0", "readme")
assert content.data
bad = [
    name
    for name in sys.modules
    if name == "mcp" or name.startswith("mcp.") or name.startswith("project_standards.mcp_server")
]
assert not bad, f"SDK modules were loaded: {{bad}}"
"""


def _imported_roots(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            roots.add(node.module)
    return roots


def test_facade_exports_protocol_neutral_types_without_mcp_sdk() -> None:
    services = import_mcp_services()

    # "Export only the facade and DTO/error types": the public surface is an
    # exact set, so an undeclared extra export fails just like a missing one.
    exported = set(getattr(services, "__all__", ()))
    assert exported == _FROZEN_EXPORTS
    for name in exported:
        assert hasattr(services, name), f"__all__ names an unbound export: {name}"

    facade = services.McpServiceFacade
    missing = {name for name in _FROZEN_T2_METHODS if not hasattr(facade, name)}
    assert not missing, f"facade is missing frozen T2 methods: {missing}"
    assert issubclass(services.ServiceError, Exception)

    package_file = services.__file__
    assert package_file is not None
    package_dir = Path(package_file).parent
    for module_path in sorted(package_dir.rglob("*.py")):
        forbidden = {
            root
            for root in _imported_roots(module_path)
            if any(root == bad or root.startswith(f"{bad}.") for bad in _FORBIDDEN_IMPORT_ROOTS)
        }
        assert not forbidden, f"{module_path.name} imports SDK/adapter modules: {forbidden}"

    result = subprocess.run(
        [sys.executable, "-c", _BLOCKED_SDK_PROBE.format(fixture=str(FULL_FIXTURE))],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"facade operations failed with SDK imports blocked:\n{result.stderr}"
    )
