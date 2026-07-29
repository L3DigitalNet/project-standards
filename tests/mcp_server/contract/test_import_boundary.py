"""Contract: the SDK stops at the adapter and never reaches the services (T5).

Covers TC-T5-003 together with NFR-006, NFR-013, and ADR 0025's confirmation
clause: "no module under ``mcp_services`` imports ``mcp`` or ``mcp_server`` and
no ``mcp_services`` public signature exposes an SDK type."

T2 already proved the service layer was SDK-free when no adapter existed. T5 is
the task that introduces the adapter, so the property has to be re-proved from
the other side: the boundary is only interesting once there is something on the
far side of it to leak. Every test here therefore requires the adapter package
to exist first, and then asserts what its existence must not have changed.

Two mechanisms are used deliberately rather than one. Source analysis names the
offending module and line class, which a runtime probe cannot; the runtime probe
runs the services in a fresh interpreter whose import machinery *refuses* the
SDK, which source analysis cannot — a lazy import inside a function body, an
``importlib.import_module`` call, or a re-export through a third module all
survive an AST scan and die in the probe. This is the T2 blocked-import
precedent extended to the adapter direction, and the probe now imports **every**
``mcp_services`` module rather than only the ones the facade happens to touch,
because a dynamic import in an unexercised method would otherwise evade both
mechanisms (T5.2 Codex review F7).

The plan adds two further constraints T2 could not express. ``transport.py`` is
"the only module that imports SDK server/protocol types", so the adapter's own
internal layering is asserted too — without it, ``repo_access`` or ``models``
could take an SDK dependency and the one-way graph would still hold while the
protocol-neutral core quietly stopped being protocol-neutral. And NFR-006
requires "protocol modules contain registration/mapping only; package and
provider semantics remain outside the MCP layer", which is asserted as a bounded
dependency-direction rule in
``test_protocol_modules_reach_repository_facts_only_through_the_services``
(review F14).
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast, get_type_hints

ADAPTER_PACKAGE = "project_standards.mcp_server"
SERVICE_PACKAGE = "project_standards.mcp_services"

# Everything the selected SDK ships under. `mcp_types` is a separate
# distribution pinned by `mcp==2.0.0`, so a service module could import the
# protocol vocabulary without ever naming `mcp`.
SDK_ROOTS = ("mcp", "mcp_types")

# The modules T5 declares. The set is a floor, not a ceiling: a later task may
# add adapter modules, but none of these five may go missing.
PLANNED_ADAPTER_MODULES = ("__init__", "entrypoint", "transport", "repo_access", "models")

# Plan T5: `transport.py` is the only module that imports SDK server/protocol types.
SDK_IMPORTING_MODULE = "transport.py"

# NFR-006's bounded allowlist (review F14 disposition). `entrypoint` assembles
# the installed distribution the facade is constructed from, and `repo_access`
# owns filesystem containment; everything else in the adapter is registration
# and mapping and must reach repository facts through `mcp_services`.
REPOSITORY_AUTHORITY_PACKAGES = (
    "project_standards.control_plane",
    "project_standards.package_contract",
    "project_standards.standards_graph",
    "project_standards.adopt",
)
DEPENDENCY_ALLOWLIST = ("entrypoint.py", "repo_access.py")


def _blocked_sdk_probe(modules: tuple[str, ...]) -> str:
    """Build the fresh-interpreter probe body for the given service modules."""
    return f"""
import importlib
import sys


class _BlockAdapterAndSdk:
    def find_spec(self, name, path=None, target=None):
        root = name.split(".")[0]
        if root in {set(SDK_ROOTS)!r} or name == {ADAPTER_PACKAGE!r} or name.startswith(
            {ADAPTER_PACKAGE!r} + "."
        ):
            raise ImportError(f"import of {{name!r}} is blocked by the T5 boundary contract")
        return None


sys.meta_path.insert(0, _BlockAdapterAndSdk())

# Every service module, not only the ones the facade happens to exercise: a
# module-level SDK import in an unused module would otherwise pass silently.
for dotted in {list(modules)!r}:
    importlib.import_module(dotted)

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_services import McpServiceFacade

facade = McpServiceFacade.from_installed(InstalledDistribution.current(), CatalogMajor("5"))
catalog = facade.catalog()
assert catalog.standards, "the installed catalog produced no standards"
first = catalog.standards[0]
descriptor = facade.standard(first.standard_id, first.package_version)
assert descriptor.standard_id == first.standard_id
if descriptor.resources:
    content = facade.resource(
        first.standard_id, first.package_version, descriptor.resources[0].resource_id
    )
    assert content.data is not None

leaked = [
    name
    for name in sys.modules
    if name.split(".")[0] in {set(SDK_ROOTS)!r} or name.startswith({ADAPTER_PACKAGE!r})
]
assert not leaked, f"SDK or adapter modules were loaded: {{leaked}}"
print("ok")
"""


def require_package(dotted: str, label: str) -> ModuleType:
    """Import one planned package, or fail as an explicit RED assertion."""
    try:
        spec = importlib.util.find_spec(dotted)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        f"planned {label} {dotted} is absent; the T5 adapter does not exist yet"
    )
    return importlib.import_module(dotted)


def package_directory(module: ModuleType) -> Path:
    package_file = module.__file__
    assert package_file is not None, f"{module.__name__} must live in a real directory"
    return Path(package_file).parent


def service_module_names() -> tuple[str, ...]:
    """Every importable module under ``mcp_services``, discovered from the tree."""
    services = require_package(SERVICE_PACKAGE, "service package")
    directory = package_directory(services)
    names = [SERVICE_PACKAGE]
    names += [
        f"{SERVICE_PACKAGE}.{path.stem}"
        for path in sorted(directory.rglob("*.py"))
        if path.stem != "__init__"
    ]
    assert len(names) > 1, "the service package has no modules to probe"
    return tuple(names)


def imported_roots(module_path: Path) -> set[str]:
    """Return every dotted module name a source file imports at any level."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            roots.add(node.module)
    return roots


def matches(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes)


def runtime_root() -> Path:
    import project_standards

    package_file = project_standards.__file__
    assert package_file is not None
    return Path(package_file).resolve().parent.parent


def test_service_package_imports_without_mcp_sdk() -> None:
    """TC-T5-003 (NFR-006, NFR-013, IR-004): the adapter exists and services ignore it.

    The adapter package is required first on purpose. "Services import without
    the SDK" is trivially true while no SDK-importing module exists at all, and
    the claim T5 actually has to make is that *adding* the adapter left the
    service layer independently importable and fully usable.

    The probe imports every service module by dotted name before exercising the
    facade, so a module-level or lazy SDK import in a method the facade never
    calls is caught too (review F7).
    """
    require_package(ADAPTER_PACKAGE, "adapter package")
    modules = service_module_names()

    result = subprocess.run(
        [sys.executable, "-c", _blocked_sdk_probe(modules)],
        env={**os.environ, "PYTHONPATH": str(runtime_root()), "NO_COLOR": "1"},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"the service layer failed with the SDK and adapter blocked:\n{result.stderr}"
    )
    assert result.stdout.strip().endswith("ok")


def test_adapter_package_carries_the_planned_module_set() -> None:
    """Plan T5 file list: the five adapter modules exist and are importable."""
    package = require_package(ADAPTER_PACKAGE, "adapter package")
    directory = package_directory(package)
    missing = [name for name in PLANNED_ADAPTER_MODULES if not (directory / f"{name}.py").is_file()]
    assert not missing, f"planned adapter modules are absent: {missing}"
    for name in PLANNED_ADAPTER_MODULES:
        if name != "__init__":
            require_package(f"{ADAPTER_PACKAGE}.{name}", "adapter module")


def test_service_modules_never_import_the_sdk_or_the_adapter() -> None:
    """ADR 0025 confirmation: the import graph is one-way, checked at the source.

    Complements the runtime probe rather than duplicating it: the probe proves
    the services *run* without the SDK, this names the file that would have
    broken the rule, which is the difference between a diagnosable failure and
    a stack trace from a subprocess.
    """
    require_package(ADAPTER_PACKAGE, "adapter package")
    services = require_package(SERVICE_PACKAGE, "service package")
    forbidden = (*SDK_ROOTS, ADAPTER_PACKAGE)
    offenders: dict[str, set[str]] = {}
    for module_path in sorted(package_directory(services).rglob("*.py")):
        found = {root for root in imported_roots(module_path) if matches(root, forbidden)}
        if found:
            offenders[module_path.name] = found
    assert not offenders, f"service modules import the SDK or the adapter: {offenders}"


def test_only_the_transport_module_imports_the_sdk() -> None:
    """Plan T5: ``transport.py`` is the only module that imports SDK types.

    The adapter is allowed to depend on the SDK; that is what it is for. What it
    may not do is spread that dependency, because every other adapter module is
    then pinned to the SDK's own release cadence — the exact churn ADR 0025's
    decision drivers call out, the SDK having already renamed its server API
    once in this major line.
    """
    package = require_package(ADAPTER_PACKAGE, "adapter package")
    offenders: dict[str, set[str]] = {}
    for module_path in sorted(package_directory(package).rglob("*.py")):
        if module_path.name == SDK_IMPORTING_MODULE:
            continue
        found = {root for root in imported_roots(module_path) if matches(root, SDK_ROOTS)}
        if found:
            offenders[module_path.name] = found
    assert not offenders, (
        f"only {SDK_IMPORTING_MODULE} may import the SDK; these modules also do: {offenders}"
    )


def test_protocol_modules_reach_repository_facts_only_through_the_services() -> None:
    """NFR-006: "Protocol modules contain registration/mapping only".

    The spec's verification criterion is explicit — "package and provider
    semantics remain outside the MCP layer" — so this is a documented rule, not
    an invented one (review F14 required checking that first). Import direction
    alone does not enforce it: an adapter module can import the control plane or
    the package contract directly and re-derive semantics the facade already
    owns, while every other boundary test still passes.

    The allowlist is deliberately narrow and matches the disposition:
    ``entrypoint`` assembles the installed distribution the facade is
    constructed from, and ``repo_access`` owns filesystem containment. Every
    other adapter module is registration and mapping, and must reach repository
    facts through ``mcp_services``.
    """
    package = require_package(ADAPTER_PACKAGE, "adapter package")
    offenders: dict[str, set[str]] = {}
    for module_path in sorted(package_directory(package).rglob("*.py")):
        if module_path.name in DEPENDENCY_ALLOWLIST:
            continue
        found = {
            root
            for root in imported_roots(module_path)
            if matches(root, REPOSITORY_AUTHORITY_PACKAGES)
        }
        if found:
            offenders[module_path.name] = found
    assert not offenders, (
        "protocol registration/mapping modules must reach repository facts through "
        f"{SERVICE_PACKAGE}, not directly: {offenders}"
    )


def _type_arguments(annotation: object) -> tuple[Any, ...]:
    """Every parameter of a generic annotation, or an empty tuple."""
    arguments = getattr(annotation, "__args__", ())
    return tuple(cast("tuple[Any, ...]", arguments))


def _resolved_signature(member: Any) -> inspect.Signature | None:
    """Signature with annotations resolved where the module makes that possible."""
    for eval_str in (True, False):
        try:
            return inspect.signature(member, eval_str=eval_str)
        except TypeError, ValueError, NameError, AttributeError:
            continue
    return None


def _resolved_class_annotations(owner: type) -> dict[str, Any]:
    """Class field annotations, resolved to objects where possible.

    The except clause is broad on purpose: ``get_type_hints`` raises `NameError`,
    `TypeError`, and pydantic's own errors depending on why a name failed to
    resolve, and every one of them must degrade to the raw strings rather than
    lose the class from the leak check.
    """
    try:
        return dict(get_type_hints(owner))
    except Exception:
        return dict(getattr(owner, "__annotations__", {}))


def _public_callables(owner: type, prefix: str) -> list[tuple[str, Any]]:
    """Every public callable a class exposes, unwrapped to the underlying function.

    Classmethods, staticmethods, properties, and the constructor are all part of
    the public surface an SDK type could leak through, and all four are invisible
    to a plain ``vars()`` walk that only keeps ``callable`` values (review F7):
    a ``classmethod`` object is not callable before binding, and a ``property``
    never is.
    """
    members: list[tuple[str, Any]] = [(f"{prefix}.__init__", owner.__init__)]
    for attribute, value in vars(owner).items():
        if attribute.startswith("_"):
            continue
        label = f"{prefix}.{attribute}"
        if isinstance(value, classmethod | staticmethod):
            members.append((label, cast("Any", value).__func__))
        elif isinstance(value, property):
            members += [
                (f"{label}.{role}", accessor)
                for role, accessor in (
                    ("fget", value.fget),
                    ("fset", value.fset),
                    ("fdel", value.fdel),
                )
                if accessor is not None
            ]
        elif callable(value):
            members.append((label, value))
    return members


def test_no_service_signature_exposes_an_sdk_type() -> None:
    """NFR-013/ADR 0025: SDK types stay out of the service layer's public surface.

    Every service module uses postponed annotations, so a naive
    ``inspect.signature`` would hand back *strings* and quietly find nothing.
    Annotations are therefore resolved with ``eval_str``/``get_type_hints``
    first, and any annotation that cannot be resolved (a ``TYPE_CHECKING``-only
    name, for instance) falls back to a word-boundary match on its source text
    rather than being skipped.

    The walk covers constructors, classmethods, staticmethods, and property
    accessors, and recurses through nested type arguments to arbitrary depth, so
    ``tuple[dict[str, mcp_types.Tool], ...]`` is caught as surely as a bare
    annotation (review F7).
    """
    require_package(ADAPTER_PACKAGE, "adapter package")
    services = require_package(SERVICE_PACKAGE, "service package")

    def offending(annotation: Any, depth: int = 0) -> set[str]:
        if annotation is inspect.Parameter.empty or annotation is inspect.Signature.empty:
            return set()
        if isinstance(annotation, str):
            # Unresolvable annotation: fall back to its text.
            return {root for root in SDK_ROOTS if re.search(rf"\b{re.escape(root)}\b", annotation)}
        found: set[str] = set()
        module = getattr(annotation, "__module__", None)
        if isinstance(module, str) and matches(module, SDK_ROOTS):
            found.add(f"{module}.{getattr(annotation, '__qualname__', annotation)!s}")
        if depth < 8:
            for argument in _type_arguments(annotation):
                found |= offending(argument, depth + 1)
        return found

    offenders: dict[str, set[str]] = {}

    def record(label: str, annotation: Any) -> None:
        if leaked := offending(annotation):
            offenders[label] = leaked

    for name in getattr(services, "__all__", ()):
        exported = getattr(services, name)
        members: list[tuple[str, Any]] = []
        if inspect.isclass(exported):
            members = _public_callables(exported, name)
            for field, annotation in _resolved_class_annotations(exported).items():
                if not field.startswith("_"):
                    record(f"{name}.{field}", annotation)
        elif callable(exported):
            members = [(name, exported)]
        for label, member in members:
            signature = _resolved_signature(member)
            if signature is None:
                continue
            for parameter in signature.parameters.values():
                record(f"{label}({parameter.name})", parameter.annotation)
            record(f"{label}->", signature.return_annotation)

    assert not offenders, f"service signatures expose SDK types: {offenders}"


def test_service_annotations_actually_resolve() -> None:
    """Guard the guard: the leak check above must not be silently inert.

    Every service module uses ``from __future__ import annotations``, so the
    check is only meaningful if annotations resolve to real objects. If a future
    refactor makes them all unresolvable, the SDK-type check degrades to a text
    match without saying so — this test makes that degradation visible.
    """
    services = require_package(SERVICE_PACKAGE, "service package")
    resolved = 0
    unresolved = 0
    for name in getattr(services, "__all__", ()):
        exported = getattr(services, name)
        if not inspect.isclass(exported):
            continue
        for annotation in _resolved_class_annotations(exported).values():
            if isinstance(annotation, str):
                unresolved += 1
            else:
                resolved += 1
        for _, member in _public_callables(exported, name):
            signature = _resolved_signature(member)
            if signature is None:
                continue
            for parameter in signature.parameters.values():
                if parameter.annotation is inspect.Parameter.empty:
                    continue
                if isinstance(parameter.annotation, str):
                    unresolved += 1
                else:
                    resolved += 1
    assert resolved > 0, "no service annotation resolved; the SDK-type check would be inert"
    assert resolved > unresolved, (
        f"{unresolved} of {resolved + unresolved} service annotations are unresolvable; "
        "the SDK-type check has degraded to a text match"
    )
