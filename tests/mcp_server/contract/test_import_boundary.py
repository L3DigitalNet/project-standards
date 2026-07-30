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

**T10 completes the graph** (TC-T10-006, NFR-006 and NFR-013). Everything above
reads *module-level, absolute* imports and proves the service layer runs without
the SDK. Three things stay invisible to that pair, and all three are ways the
one-way graph could quietly become two-way once the whole adapter exists:

* a relative import (``from . import transport``) and a dynamic one
  (``importlib.import_module("mcp")``) are both absent from the level-0 scan;
* the adapter's *internal* graph could grow a cycle, or a second module could
  come to depend on ``transport``, without any SDK name appearing outside it;
* NFR-013 has a second half — "**protocol-version conditionals** shall not cross
  into package/control-plane services" — which no import-direction rule can see,
  because a revision string is data rather than a dependency.

``test_complete_adapter_import_graph_is_one_way_and_sdk_isolated`` asserts all
three, and adds the mirror of the T5 probe: a fresh interpreter that blocks the
SDK and then *exercises* every protocol-neutral adapter module. T5 proved the
services survive without the SDK; this proves the adapter's own registration
core does, which is the property that makes ``transport`` replaceable.
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

# T10 (TC-T10-006). The adapter module that is allowed to depend on the one SDK
# importer: `entrypoint` is the launch surface, and ADR 0025 makes launching the
# transport its job. Every other adapter module must stay usable without it,
# which is what keeps `transport` a replaceable file rather than a hub.
TRANSPORT_MODULE = "transport"
TRANSPORT_DEPENDENT_ALLOWLIST = ("entrypoint",)

# The protocol-neutral core: every adapter module that must import, and run,
# with the SDK refused by the import machinery. `transport` imports the SDK by
# design and `entrypoint` imports `transport`, so both are excluded by rule
# rather than by omission.
SDK_FREE_ADAPTER_MODULES = ("__init__", "models", "prompts", "repo_access", "resources", "tools")

# NFR-013's second half: "protocol-version conditionals shall not cross into
# package/control-plane services". Revision strings are *data*, so no
# import-direction rule can see them.
#
# The names below are matched as identifiers, attributes, parameters, and
# keywords — `protocol_version` foremost, because a module that branches on
# `context.protocol_version` carries a protocol conditional while naming no
# revision at all, which is what an exact-literal match missed (review F9).
PROTOCOL_VERSION_NAMES = frozenset(
    {
        "protocol_version",
        "protocolVersion",
        "MODERN_PROTOCOL_VERSIONS",
        "HANDSHAKE_PROTOCOL_VERSIONS",
        "PROTOCOL_VERSION_META_KEY",
    }
)

#: The SDK's own revision register. Importing anything from it outside the
#: transport is a protocol dependency whatever the name is used for.
SDK_VERSION_MODULE = "mcp_types.version"

#: A protocol revision, by shape rather than by enumeration, so a revision this
#: repository has never seen is caught as surely as a current one. Every MCP
#: revision to date is a calendar date, and no other string constant in these two
#: packages is.
REVISION_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


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


# -- T10: the complete graph ---------------------------------------------------


def complete_imports(module_path: Path, package: str) -> set[str]:
    """Every module this file can import, by any mechanism an AST can see.

    The level-0 scan above answers "what does this file depend on at module scope,
    spelled absolutely". This answers the wider question TC-T10-006 asks.

    **Relative imports resolve against the containing package**, which is the bug
    the T10.2 review found (F9): resolving them against the *module's own* dotted
    name put ``from . import transport`` inside ``entrypoint``, where it could be
    normalized back to the source module and escape the graph entirely. One leading
    dot means the package the module lives in; each extra dot strips one more
    component.

    The string-literal argument of ``importlib.import_module``/``__import__`` is
    treated as an import, because it is one, and because a lazy dynamic import
    inside a function body is precisely how a boundary rule stops holding without
    any ``import`` statement changing. A dynamic import built from a *computed*
    expression is deliberately not guessed at; that case is covered by the
    blocked-import probe, which fails on the attempt rather than on the source text.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module is not None:
                    found.add(node.module)
                    found.update(f"{node.module}.{alias.name}" for alias in node.names)
            else:
                parts = package.split(".")
                keep = len(parts) - (node.level - 1)
                assert keep > 0, f"{module_path} escapes its own package with {node.level} dots"
                base = ".".join(parts[:keep])
                prefix = f"{base}.{node.module}" if node.module else base
                found.add(prefix)
                found.update(f"{prefix}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            target = node.func
            name = (
                target.attr
                if isinstance(target, ast.Attribute)
                else target.id
                if isinstance(target, ast.Name)
                else ""
            )
            if name not in ("import_module", "__import__"):
                continue
            found.update(
                argument.value
                for argument in node.args
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            )
    return found


def protocol_conditional_sites(module_path: Path) -> set[str]:
    """Every place one file could branch on a protocol revision.

    NFR-013's second half — "protocol-version conditionals shall not cross into
    package/control-plane services" — is a rule about *data*, invisible to any
    import-direction check. Matching the exact revision strings the SDK currently
    advertises was too narrow (review F9): a module that reads
    ``context.protocol_version`` and compares it to a value it computed carries a
    protocol conditional while naming no revision at all.

    Three signals, none of them an allowlist of dates:

    * any identifier, attribute, keyword, or parameter named for the protocol
      version, in any spelling the codebase could use;
    * any name imported from the SDK's version register;
    * any string constant shaped like a protocol revision (``YYYY-MM-DD``), which
      catches a future revision this repository has never seen.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    sites: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in PROTOCOL_VERSION_NAMES:
            sites.add(f"attribute {node.attr}")
        elif isinstance(node, ast.Name) and node.id in PROTOCOL_VERSION_NAMES:
            sites.add(f"name {node.id}")
        elif isinstance(node, ast.arg) and node.arg in PROTOCOL_VERSION_NAMES:
            sites.add(f"parameter {node.arg}")
        elif isinstance(node, ast.keyword) and node.arg in PROTOCOL_VERSION_NAMES:
            sites.add(f"keyword {node.arg}")
        elif isinstance(node, ast.ImportFrom) and node.module == SDK_VERSION_MODULE:
            sites.update(f"import {alias.name}" for alias in node.names)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and REVISION_PATTERN.fullmatch(node.value)
        ):
            sites.add(f"revision literal {node.value}")
    return sites


def containing_package(module_path: Path, root_directory: Path, root_package: str) -> str:
    """The dotted package one source file actually lives in.

    ``complete_imports``'s relative-import formula is only correct when it is given
    the *file's own* package: passing the package root made a nested module's
    ``from . import x`` resolve as if the module sat at the top level, which is
    the defect that survived the first repair (T10.4 Codex GREEN review, F3).

    Derived from the path rather than from an import, so it is right for every file
    a recursive walk reaches, including one in a subpackage the walk has never
    imported. ``__init__.py`` names its own package; every other module names the
    package of its parent directory.
    """
    relative = module_path.relative_to(root_directory)
    # The file name never contributes a component: a module lives *in* its parent
    # package, and `inner/__init__.py` names `inner` for the same reason.
    parts = list(relative.parts[:-1])
    return ".".join([root_package, *parts]) if parts else root_package


def adapter_module_name(module_path: Path) -> str:
    return module_path.stem


def _sdk_free_adapter_probe(modules: tuple[str, ...]) -> str:
    """Fresh-interpreter probe body: import and *exercise* the adapter without the SDK.

    Every protocol-neutral handler is driven, not one (review F9): all six tool
    handlers through ``invoke_tool``, both refusal classes ``invoke_tool`` owns,
    every registry surface (listings, templates, and a read of each of the three
    URI forms), the instructions renderer at both registry sizes, the prompt-role
    decision, and the root resolver. A computed lazy import on any of those paths
    dies here rather than on the wire.
    """
    return f"""
import importlib
import sys


class _BlockSdk:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in {set(SDK_ROOTS)!r}:
            raise ImportError(f"import of {{name!r}} is blocked by the T10 boundary contract")
        return None


sys.meta_path.insert(0, _BlockSdk())

for dotted in {list(modules)!r}:
    importlib.import_module(dotted)

from pathlib import Path

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server import models, prompts, repo_access, resources, tools
from project_standards.mcp_services import McpServiceFacade, ServiceError

distribution = InstalledDistribution.current()
facade = McpServiceFacade.from_installed(distribution, CatalogMajor("5"))
catalog = facade.catalog()

# A real control plane, so the four repository-scoped handlers return an answer
# instead of stopping at an uninitialized-state refusal: a handler that refused
# early would leave its projection path — and any lazy import on it — unexecuted.
initialize_control_plane(Path("__REPO_ROOT__"), "5", distribution=distribution)

registry = resources.build_resource_registry(facade)
entries = tools.build_tool_registry()
assert entries, "the tool registry is empty"
names = [entry.name for entry in entries]

# Registration-time decisions.
assert models.SERVER_NAME == "project-standards", models.SERVER_NAME
assert models.instructions_for(names).strip(), "no instructions rendering was produced"
assert models.instructions_for(models.INSTRUCTIONS_TOOL_ORDER).strip()
assert models.server_version(), "no server version was resolved"
assert prompts.prompt_role_resources(catalog) == ()
assert models.AdapterConfiguration().configured_boundary is None

# Every registry surface.
assert list(registry.listings()), "the resource registry listed nothing"
assert list(registry.templates()), "the resource registry declared no template"
catalog_payload = registry.read(f"standards://catalog/{{models.CATALOG_MAJOR}}")
assert catalog_payload.data, "the catalog resource produced no bytes"
first = catalog.standards[0]
package_payload = registry.read(f"standards://{{first.standard_id}}/{{first.package_version}}")
assert package_payload.data, "the package resource produced no bytes"
declared = [
    resource
    for standard in catalog.standards
    for resource in standard.resources
]
assert declared, "the installed catalog declares no payload resource"
payload = registry.read(declared[0].uri)
assert payload.data, "the payload resource produced no bytes"

# Every tool handler, and both refusal classes `invoke_tool` owns.
context = tools.ToolContext(registry=registry, facade=facade, tools=entries)
answers = {{}}
for name in names:
    if name == tools.STANDARDS_LIST:
        arguments = None
    elif name == tools.STANDARD_READ:
        arguments = {{tools.STANDARD_READ_ARGUMENT: declared[0].uri}}
    else:
        arguments = {{tools.REPO_ROOT_ARGUMENT: "__REPO_ROOT__"}}
    answers[name] = tools.invoke_tool(context, name, arguments, None)
    assert answers[name].structured, f"{{name}} produced no structured answer"
assert set(answers) == set(names), "a registered tool was never invoked"

for bad_name, bad_arguments in (("no_such_tool", None), (tools.STANDARDS_LIST, {{"x": 1}})):
    try:
        tools.invoke_tool(context, bad_name, bad_arguments, None)
    except ServiceError:
        pass
    else:
        raise AssertionError(f"{{bad_name}} accepted an invalid call")

# The containment resolver, both directions.
resolved = repo_access.resolve_effective_root("__REPO_ROOT__")
assert resolved.is_absolute(), resolved
try:
    repo_access.resolve_effective_root("relative/path")
except ServiceError:
    pass
else:
    raise AssertionError("a relative repository root was accepted")

leaked = [name for name in sys.modules if name.split(".")[0] in {set(SDK_ROOTS)!r}]
assert not leaked, f"SDK modules were loaded: {{leaked}}"
print("ok")
"""


def _cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Every dependency cycle in one module graph, reported by its member names."""
    found: list[list[str]] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def walk(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for target in sorted(graph.get(node, set())):
            if state.get(target, 0) == 0:
                walk(target)
            elif state.get(target) == 1:
                found.append([*stack[stack.index(target) :], target])
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            walk(node)
    return found


def test_complete_import_extraction_sees_relative_and_dynamic_forms(tmp_path: Path) -> None:
    """RED control: the resolver and the conditional scan catch what they claim to.

    Deliberately green. ``complete_imports`` and ``protocol_conditional_sites`` are
    the two mechanisms TC-T10-006 rests on, and both were wrong or too narrow in
    the T10.1 revision (review F9). Every form is planted here against a synthetic
    module whose containing package is known, so a resolver that maps
    ``from . import transport`` to the wrong package — the exact defect found —
    fails immediately rather than silently widening the graph.
    """
    source = tmp_path / "probe.py"
    source.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import importlib",
                "from . import transport",
                "from .models import SERVER_NAME",
                "from .. import mcp_services",
                "from project_standards.mcp_services import McpServiceFacade",
                "import mcp_types",
                "",
                "",
                "def late(version: str) -> object:",
                '    module = importlib.import_module("mcp.server.lowlevel")',
                '    other = __import__("mcp_types.version")',
                '    if version == "2026-07-28":',
                "        return module",
                "    return other",
                "",
                "",
                "def branch(protocol_version: str) -> bool:",
                "    return protocol_version in MODERN_PROTOCOL_VERSIONS",
                "",
            ]
        ),
        encoding="utf-8",
    )
    found = complete_imports(source, "project_standards.mcp_server")
    assert "project_standards.mcp_server.transport" in found, (
        f"`from . import transport` did not resolve to the containing package: {sorted(found)}"
    )
    assert "project_standards.mcp_server.models" in found, sorted(found)
    assert "project_standards.mcp_services" in found, (
        f"a two-dot relative import did not resolve one level up: {sorted(found)}"
    )
    assert "mcp_types" in found and "mcp.server.lowlevel" in found, sorted(found)
    assert "mcp_types.version" in found, (
        f"the `__import__` string literal was not treated as an import: {sorted(found)}"
    )
    assert all(name != "probe" for name in found), (
        f"a relative import was normalized back to its own module: {sorted(found)}"
    )

    sites = protocol_conditional_sites(source)
    assert any(site.startswith("parameter protocol_version") for site in sites), sites
    assert any(site.startswith("name MODERN_PROTOCOL_VERSIONS") for site in sites), sites
    assert "revision literal 2026-07-28" in sites, (
        f"a revision-shaped literal escaped the conditional scan: {sites}"
    )

    clean = tmp_path / "clean.py"
    clean.write_text("VALUE = 'not-a-date'\nOTHER = '2026-07'\n", encoding="utf-8")
    assert not protocol_conditional_sites(clean), (
        f"the conditional scan flags an ordinary constant: {protocol_conditional_sites(clean)}"
    )

    # A module one level down, whose `from . import x` names the *subpackage*.
    # Resolving it against the package root instead — the defect this control
    # exists for — would silently move the import out of the graph the boundary
    # rules police.
    root = tmp_path / "pkg"
    nested_directory = root / "inner"
    nested_directory.mkdir(parents=True)
    nested = nested_directory / "deep.py"
    nested.write_text(
        "from . import sibling\nfrom .. import outer\nfrom ...far import thing\n",
        encoding="utf-8",
    )
    package_name = containing_package(nested, root, "project_standards.mcp_server")
    assert package_name == "project_standards.mcp_server.inner", package_name
    nested_found = complete_imports(nested, package_name)
    assert "project_standards.mcp_server.inner.sibling" in nested_found, (
        f"a one-dot import inside a subpackage did not resolve to that subpackage: "
        f"{sorted(nested_found)}"
    )
    assert "project_standards.mcp_server.outer" in nested_found, sorted(nested_found)
    assert "project_standards.far.thing" in nested_found, sorted(nested_found)
    assert containing_package(root / "top.py", root, "project_standards.mcp_server") == (
        "project_standards.mcp_server"
    ), "a top-level module must name the package root"
    assert (
        containing_package(nested_directory / "__init__.py", root, "project_standards.mcp_server")
        == "project_standards.mcp_server.inner"
    ), "a subpackage __init__ must name its own package"


def test_complete_adapter_import_graph_is_one_way_and_sdk_isolated(tmp_path: Path) -> None:
    """TC-T10-006 (NFR-006, NFR-013): the whole graph, not only its level-0 slice.

    Four properties, each closing a hole the T5 pair leaves open.

    *Completeness.* Imports are extracted including relative forms — resolved
    against the containing package — and the string literal of a dynamic
    ``import_module``/``__import__`` call, so a lazy import inside a function body
    is as visible as a module-level one.

    *Internal layering.* The adapter's own dependency graph must be acyclic, and
    ``transport`` must be depended on only by the launch surface. Without this,
    ``tools`` could import ``transport`` for one SDK type and every other assertion
    in this file would still pass while the protocol-neutral core stopped being
    protocol-neutral.

    *Runtime isolation, from the adapter side.* T5 proves the *services* run with
    the SDK blocked. This proves the adapter's registration core does: a fresh
    interpreter refuses ``mcp`` and ``mcp_types``, imports every protocol-neutral
    adapter module, and then drives **every** handler — all six tools, both refusal
    classes, every registry surface and URI form, the instructions renderer, the
    prompt-role decision, and the root resolver in both directions. Importing
    alone, or invoking one tool, would miss a lazy SDK import on any other path.

    *NFR-013's second half.* No protocol-version conditional may appear anywhere
    outside ``transport`` — not a named constant, not a ``protocol_version``
    parameter or attribute, not an import from the SDK's version register, and not
    a revision-shaped string literal. Matching only the revisions this SDK
    currently advertises would have missed a comparison against a computed value.
    """
    package = require_package(ADAPTER_PACKAGE, "adapter package")
    services = require_package(SERVICE_PACKAGE, "service package")
    directory = package_directory(package)
    service_directory = package_directory(services)

    forbidden = (*SDK_ROOTS, ADAPTER_PACKAGE)
    service_offenders: dict[str, set[str]] = {}
    for module_path in sorted(service_directory.rglob("*.py")):
        package_name = containing_package(module_path, service_directory, SERVICE_PACKAGE)
        found = {
            name for name in complete_imports(module_path, package_name) if matches(name, forbidden)
        }
        if found:
            service_offenders[module_path.name] = found
    assert not service_offenders, (
        "the complete import graph shows service modules reaching the SDK or the adapter through "
        f"a relative or dynamic import: {service_offenders}"
    )

    sdk_offenders: dict[str, set[str]] = {}
    internal: dict[str, set[str]] = {}
    for module_path in sorted(directory.rglob("*.py")):
        name = adapter_module_name(module_path)
        imports = complete_imports(
            module_path, containing_package(module_path, directory, ADAPTER_PACKAGE)
        )
        if name != TRANSPORT_MODULE:
            found = {item for item in imports if matches(item, SDK_ROOTS)}
            if found:
                sdk_offenders[module_path.name] = found
        internal[name] = {
            item.removeprefix(f"{ADAPTER_PACKAGE}.").split(".")[0]
            for item in imports
            if matches(item, (ADAPTER_PACKAGE,)) and item != ADAPTER_PACKAGE
        } - {name}
    assert not sdk_offenders, (
        f"only {TRANSPORT_MODULE}.py may reach the SDK by any mechanism: {sdk_offenders}"
    )

    dependents = sorted(name for name, targets in internal.items() if TRANSPORT_MODULE in targets)
    assert dependents == sorted(TRANSPORT_DEPENDENT_ALLOWLIST), (
        f"only {list(TRANSPORT_DEPENDENT_ALLOWLIST)} may depend on the SDK-importing module; "
        f"these do: {dependents}"
    )
    cycles = _cycles(internal)
    assert not cycles, f"the adapter's internal import graph is not acyclic: {cycles}"

    conditional_offenders: dict[str, set[str]] = {}
    for module_path in sorted([*directory.rglob("*.py"), *service_directory.rglob("*.py")]):
        if module_path.name == f"{TRANSPORT_MODULE}.py" and module_path.parent == directory:
            continue
        sites = protocol_conditional_sites(module_path)
        if sites:
            conditional_offenders[str(module_path)] = sites
    assert not conditional_offenders, (
        "NFR-013 keeps protocol-version conditionals inside the adapter's SDK-facing module; "
        f"these carry one: {conditional_offenders}"
    )

    missing = [
        name for name in SDK_FREE_ADAPTER_MODULES if not (directory / f"{name}.py").is_file()
    ]
    assert not missing, f"the protocol-neutral adapter modules are absent: {missing}"
    dotted_modules = tuple(
        ADAPTER_PACKAGE if name == "__init__" else f"{ADAPTER_PACKAGE}.{name}"
        for name in SDK_FREE_ADAPTER_MODULES
    )
    repo_root = tmp_path / "consumer"
    repo_root.mkdir()
    probe = _sdk_free_adapter_probe(dotted_modules).replace("__REPO_ROOT__", str(repo_root))
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env={**os.environ, "PYTHONPATH": str(runtime_root()), "NO_COLOR": "1"},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, (
        "the adapter's protocol-neutral core could not import or run every handler with the SDK "
        f"blocked:\n{result.stderr}"
    )
    assert result.stdout.strip().endswith("ok")
