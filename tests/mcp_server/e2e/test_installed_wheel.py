"""The candidate wheel a client actually installs, and the docs that describe it (T11).

Covers TC-T11-001 (source and extracted-wheel outputs are equivalent, NFR-009 /
NFR-010) and TC-T11-003 (documented commands match the installed entrypoint,
FR-016 / FR-020).

**Why an end-to-end suite exists after T10 proved the server.** Every earlier
suite runs against whatever ``project_standards`` the test process imported. That
is never what a client installs: ``src/project_standards/{catalogs,families,
payloads}`` are *symlinks* into this repository's authoring tree, and the wheel
dereferences them. So "the server is correct" and "the artifact a client
installs serves the same standards" are two different claims, and only the second
one is what FR-030's client work is exercised against. This file builds the
candidate, extracts it, and compares the two provenances fact by fact.

**Why the source oracle is ``from_source`` over the repository root, not the
``src`` tree.** The facade refuses symlinked resource bytes (bytes must come from
inside the payload), so ``src`` cannot stand in as an installed distribution at
all — pointing a second ``from_installed`` at it would fail for a reason that has
nothing to do with packaging. ``McpServiceFacade.from_source`` over the
repository root reads the real files under ``standards/``, which is the
provenance the projection copies from, and is the same equivalence
``tests/mcp_services/test_resources.py`` proves over fixtures (NFR-010).

**Both sides run out of process, deliberately.** An in-process oracle would be
served by whichever ``project_standards`` happens to be first on ``PYTHONPATH`` —
under the repository's own gate that is a previously built wheel runtime, which
would make the wheel side compare against a wheel. Each side runs under its own
runtime root with ``PYTHONPATH`` *replaced*, and every probe reports the
``__file__`` it resolved so the test can prove the two roots really differed
before believing a match.

**Two layers are compared, not one** (T11.2 Codex RED review, F1). The inner
layer is the registry/facade projection: catalog DTOs, per-resource descriptors
with byte digests, resource listings, templates, and the tool registry with both
schemas. The outer layer is the *reachable protocol surface* of a live stdio
server on **both** eras — declared capabilities, ``tools/list`` with schemas,
``resources/list``, ``resources/templates/list``, and the truthful refusal of
``prompts/list``. Builder output alone cannot see a server built with
``on_list_tools=None``, which would advertise nothing while every registry fact
stayed identical. The era machinery is the T5/T10 harness
(``tests.mcp_server.test_transport``), reused rather than forked.

**The documented-command test drives the declared entry point** (review F2).
``entry_points.txt`` in the extracted distribution names the console script's
target, and that target is what gets imported and invoked — never a hard-coded
``project_standards.cli:main``. A wheel declaring a console script that points at
a module it does not ship must fail here, because that is exactly the failure a
user hits after installation.

**This file does not assert TC-T11-002.** Appendix B makes the Codex and Claude
Code smoke evidence a record appended to the client matrix document, not a pytest
node (freeze F-E, upheld by the review).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, MODERN_PROTOCOL_VERSIONS

from project_standards.mcp_server.models import CATALOG_MAJOR as ADAPTER_CATALOG_MAJOR
from tests.mcp_server.test_standard_read import (
    CLAUDE_CLIENT_TOKEN,
    CODEX_CLIENT_TOKEN,
    FROZEN_CLIENT_MATRIX,
)
from tests.mcp_server.test_transport import (
    ServerProcess,
    declared_capabilities,
    modern_meta,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "src"
REFERENCE_DOC = REPO_ROOT / "docs" / "mcp-server.md"
README = REPO_ROOT / "README.md"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

# ADR 0026 scopes v1 to one catalog generation. The literal is owned *here*
# rather than imported from the adapter (review F7): an oracle read out of the
# implementation moves whenever the implementation moves, so coordinated drift
# away from the binding record would pass. The adapter's own constant is asserted
# equal to it instead, which fails locally and loudly if they ever separate.
CATALOG_MAJOR = "5"

# Build and probe deadlines. Every child is bounded and every bound is enforced
# over the whole process *group* (review F8): `uv build` spawns a build backend,
# and killing only the direct child can leave a grandchild holding the captured
# pipes open past the deadline.
BUILD_DEADLINE = 300.0
PROBE_DEADLINE = 300.0
REAP_GRACE = 5.0

# The probe emits its own import origin so a "match" can never be the accident of
# both sides resolving the same runtime. Compared for *difference*, then excluded.
ORIGIN_KEY = "origin"

CONSOLE_SCRIPT = "project-standards"
MCP_SUBCOMMAND = "mcp"

# One script, two provenances. Keeping it a single script is the point: a
# separate installed probe and source probe could drift into asking two different
# questions, and the comparison would stop meaning anything.
FACADE_PROBE_SCRIPT = """
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import project_standards
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server.resources import build_resource_registry
from project_standards.mcp_server.tools import build_tool_registry
from project_standards.mcp_services import McpServiceFacade
from project_standards.package_contract.repository import build_package_repository

mode, repo_root, catalog_major = sys.argv[1], sys.argv[2], sys.argv[3]
if mode == "installed":
    facade = McpServiceFacade.from_installed(
        InstalledDistribution.current(), CatalogMajor(catalog_major)
    )
else:
    facade = McpServiceFacade.from_source(
        build_package_repository(Path(repo_root), catalog_major=int(catalog_major)),
        CatalogMajor(catalog_major),
    )

catalog = facade.catalog()
resources = {}
for standard in catalog.standards:
    for descriptor in standard.resources:
        content = facade.resource(
            standard.standard_id, standard.package_version, descriptor.resource_id
        )
        resources[descriptor.uri] = {
            "descriptor": content.descriptor.model_dump(mode="json"),
            "sha256": hashlib.sha256(content.data).hexdigest(),
            "length": len(content.data),
        }

registry = build_resource_registry(facade)

json.dump(
    {
        "origin": project_standards.__file__,
        "catalog": catalog.model_dump(mode="json"),
        "resources": resources,
        "listings": [asdict(entry) for entry in registry.listings()],
        "templates": [asdict(entry) for entry in registry.templates()],
        "tools": [asdict(entry) for entry in build_tool_registry()],
    },
    sys.stdout,
    sort_keys=True,
)
"""

# The live stdio server, built from whichever provenance the mode selects. Both
# sides reach `transport.create_server` by the same path, so the only variable is
# the facade construction — which is the thing under test.
STDIO_LAUNCH_TEMPLATE = """
from pathlib import Path

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server import transport
from project_standards.mcp_server.models import AdapterConfiguration
from project_standards.mcp_services import McpServiceFacade
from project_standards.package_contract.repository import build_package_repository

if "__MODE__" == "installed":
    facade = McpServiceFacade.from_installed(
        InstalledDistribution.current(), CatalogMajor("__CATALOG__")
    )
else:
    facade = McpServiceFacade.from_source(
        build_package_repository(Path("__REPO__"), catalog_major=int("__CATALOG__")),
        CatalogMajor("__CATALOG__"),
    )

transport.run_stdio(transport.create_server(facade, AdapterConfiguration()))
"""

# Invoke the *declared* console-script target, whatever it is. `entry_points.txt`
# is the only authority for what a user's `project-standards` command runs, so a
# declaration pointing at an unshipped module has to fail here (review F2).
ENTRY_POINT_SCRIPT = """
import importlib
import sys

module_name, _, attribute = sys.argv[1].partition(":")
entry = importlib.import_module(module_name)
for part in attribute.split("."):
    entry = getattr(entry, part)

raise SystemExit(entry(sys.argv[2:]))
"""

# FR-020's acceptance list plus plan:474's document contract. Each row must map to
# a *distinct* heading with a non-empty body (review F3a): permissive patterns
# alone let one empty heading discharge nine obligations.
REQUIRED_TOPICS: tuple[tuple[str, str], ...] = (
    ("prerequisites", r"prerequisit"),
    ("install and version check", r"install|version"),
    ("per-client stdio configuration", r"config|setup|client"),
    ("capability matrix", r"capabilit|matrix"),
    ("resource URI and tool reference", r"resource|uri|tool|schema"),
    ("explicit-root, read-only, and security rules", r"read-only|security|root|safety"),
    ("equivalent CLI and CI commands", r"cli|\bci\b|equivalent|command"),
    ("troubleshooting", r"troubleshoot"),
    ("uninstall or disable", r"uninstall|disable|remove|turn off"),
)

# FR-020 names stderr logging explicitly; it is a technical term the document
# cannot paraphrase away without losing the fact.
REQUIRED_LITERALS = ("stderr",)

# Which top-level subcommands belong to which family, for FR-016's normative
# acceptance sentence (spec:272): "Setup/reference docs identify equivalent
# package and consumer-control-plane commands". The split follows `cli.py`'s own
# dispatch — `init`/`reconcile`/`render` route into
# `project_standards.control_plane.cli` and `agent-handoff` into the installed
# agent-handoff control plane, while the rest operate on the package/catalog. No
# tool -> command *mapping* is frozen here; the T11.2 arbitration of review F4
# leaves that to an owner amendment. Both sets are asserted to be subsets of the
# extracted CLI's advertised subcommands, so a rename fails loudly.
PACKAGE_LEVEL_SUBCOMMANDS = frozenset({"validate", "fix", "spec", "standards", "packages", "adopt"})
CONTROL_PLANE_SUBCOMMANDS = frozenset({"init", "reconcile", "render", "agent-handoff"})

# Words that turn a capability row into a denial. Used to check the document's
# capability claims against the *installed* declarations rather than against a
# spelling this test prefers (review F3c).
NEGATION = re.compile(r"\b(no|none|not|never|absent|unsupported|false|off)\b", re.IGNORECASE)

HEADING = re.compile(r"^(#{2,})\s+(.*)$")
FENCE = re.compile(r"^```(\S*)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
TABLE_DIVIDER = re.compile(r"^\|[\s:|-]+\|\s*$")
SNAKE_TOKEN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
WORKFLOW_PATH = re.compile(r"\.github/workflows/[A-Za-z0-9._-]+\.ya?ml")
LONG_OPTION = re.compile(r"^--[a-z][a-z0-9-]*")
# The shape every subcommand this CLI advertises has. Used to tell a documented
# *invocation* from transcribed output (`project-standards 5.11.0`).
SUBCOMMAND_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
CHOICE_SET = re.compile(r"\{([a-z0-9,\-]+)\}")

# Fence info strings whose bodies carry shell commands. An unlabelled fence
# counts: this repository's own README uses bare fences for shell.
SHELL_FENCES = frozenset({"", "sh", "bash", "shell", "console", "text"})

# Command prefixes that are not part of the invocation being validated.
COMMAND_PREFIXES = frozenset({"uv", "run", "sudo", "$"})


@dataclass(frozen=True, slots=True)
class InstalledCandidate:
    """One built, extracted candidate wheel and the facts identifying it.

    ``digest`` is carried because plan:474 identifies the temporary candidate by
    its SHA-256, and because review F9 requires *every* post-build failure to name
    it — a diagnostic that does not say which artifact failed is not evidence.
    """

    wheel: Path
    digest: str
    runtime_root: Path
    dist_info: Path

    @property
    def label(self) -> str:
        return f"{self.wheel.name} ({self.digest})"


@dataclass(frozen=True, slots=True)
class Section:
    """One Markdown section: its heading, depth, and body (fences included)."""

    heading: str
    level: int
    body: str


@dataclass(frozen=True, slots=True)
class Table:
    """One Markdown table reduced to its header cells and body-row cells."""

    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def column(self, index: int) -> tuple[str, ...]:
        return tuple(row[index] for row in self.rows if len(row) > index)


def _bounded(
    argv: Sequence[str],
    *,
    env: Mapping[str, str] | None,
    label: str,
    deadline: float = PROBE_DEADLINE,
) -> subprocess.CompletedProcess[str]:
    """Run one child in its own process group, bounded, and reap the whole group.

    ``subprocess.run(timeout=...)`` kills only the direct child; a build backend
    or interpreter grandchild survives it and can keep the captured pipes open
    past the deadline (review F8). Creating a session here means the timeout path
    can signal every descendant, escalating SIGTERM to SIGKILL, before the
    assertion fires.
    """
    process = subprocess.Popen(
        list(argv),
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(env) if env is not None else None,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=deadline)
    except subprocess.TimeoutExpired:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            try:
                process.communicate(timeout=REAP_GRACE)
                break
            except subprocess.TimeoutExpired:
                continue
        process.wait()
        raise AssertionError(
            f"{label} exceeded {deadline}s; its process group was signalled and reaped"
        ) from None
    return subprocess.CompletedProcess(list(argv), process.returncode, stdout, stderr)


def _require(result: subprocess.CompletedProcess[str], label: str) -> str:
    assert result.returncode == 0, (
        f"{label} failed with exit {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result.stdout


@pytest.fixture(scope="module")
def candidate(tmp_path_factory: pytest.TempPathFactory) -> Iterator[InstalledCandidate]:
    """Build and extract exactly one candidate wheel for this module.

    Module-scoped because both tests need the same artifact and building it twice
    would prove nothing except that ``uv build`` is deterministic — a claim
    ``tests/package_contract`` already owns. The build and the extraction use the
    exact commands plan:481 pins for T11.4, so the artifact this suite judges is
    the artifact the verification leg records a digest for.
    """
    root = tmp_path_factory.mktemp("mcp-candidate")
    out_dir = root / "dist"
    runtime_root = root / "runtime"
    _require(
        _bounded(
            ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
            env=None,
            label="uv build --wheel",
            deadline=BUILD_DEADLINE,
        ),
        "uv build --wheel",
    )
    wheels = sorted(out_dir.glob("project_standards-*.whl"))
    assert len(wheels) == 1, f"expected exactly one candidate wheel in {out_dir}; got {wheels}"
    wheel = wheels[0]
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    label = f"{wheel.name} ({digest})"
    _require(
        _bounded(
            [sys.executable, "-m", "zipfile", "-e", str(wheel), str(runtime_root)],
            env=None,
            label=f"extracting candidate {label}",
        ),
        f"extracting candidate {label}",
    )
    dist_infos = sorted(runtime_root.glob("project_standards-*.dist-info"))
    assert len(dist_infos) == 1, (
        f"the extracted candidate {label} must carry exactly one dist-info; got {dist_infos}"
    )
    yield InstalledCandidate(
        wheel=wheel, digest=digest, runtime_root=runtime_root, dist_info=dist_infos[0]
    )


def _runtime_env(runtime_root: Path, **extra: str) -> dict[str, str]:
    """A fresh environment serving exactly one runtime root.

    Replaced, never inherited: no ``HOME``, ``XDG_*``, ``CODEX_HOME`` or
    ``CLAUDE_*`` reaches a probe, so no user or machine configuration can
    influence a result.
    """
    return {"PYTHONPATH": str(runtime_root), "PYTHONUNBUFFERED": "1", "NO_COLOR": "1", **extra}


def _facade_probe(candidate: InstalledCandidate, runtime_root: Path, mode: str) -> dict[str, Any]:
    """Registry-layer facts from one runtime root."""
    label = f"the {mode} facade probe under {runtime_root} for candidate {candidate.label}"
    stdout = _require(
        _bounded(
            [sys.executable, "-c", FACADE_PROBE_SCRIPT, mode, str(REPO_ROOT), CATALOG_MAJOR],
            env=_runtime_env(runtime_root),
            label=label,
        ),
        label,
    )
    return cast("dict[str, Any]", json.loads(stdout))


def _launch_script(mode: str) -> str:
    return (
        STDIO_LAUNCH_TEMPLATE.replace("__MODE__", mode)
        .replace("__CATALOG__", CATALOG_MAJOR)
        .replace("__REPO__", str(REPO_ROOT))
    )


def _frame_facts(frame: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce one JSON-RPC frame to the facts a comparison may depend on.

    A frame is either a result or a structured error, and both are recorded:
    "prompts/list is refused" is as much of a wire contract as "tools/list
    answers", and a wheel that started answering it would be a divergence.
    """
    if "error" in frame:
        error = cast("Mapping[str, Any]", frame["error"])
        return {"error_code": error.get("code"), "error_message": error.get("message")}
    return {"result": frame.get("result")}


LISTING_METHODS = ("tools/list", "resources/list", "resources/templates/list", "prompts/list")


def _protocol_probe(candidate: InstalledCandidate, runtime_root: Path, mode: str) -> dict[str, Any]:
    """The reachable protocol surface of a live server, on both eras.

    This is the layer registry comparison cannot see (review F1): capabilities are
    derived by the SDK from which handlers were passed, so a build that registered
    no tool handler advertises nothing while every builder fact stays identical.
    One process per era, because the SDK locks a connection's era at its opening
    request (T5.2 review F1).
    """
    script = _launch_script(mode)
    document: dict[str, Any] = {}

    classic_version = sorted(HANDSHAKE_PROTOCOL_VERSIONS)[-1]
    with ServerProcess(script, runtime_root=runtime_root, label=f"{mode}-classic") as server:
        initialize = server.handshake(classic_version)
        document["classic"] = {
            "protocolVersion": initialize.get("protocolVersion"),
            "serverInfo": initialize.get("serverInfo"),
            "instructions": initialize.get("instructions"),
            "capabilities": declared_capabilities(initialize),
            **{method: _frame_facts(server.call(method, {})) for method in LISTING_METHODS},
        }
        server.close()

    modern_version = sorted(MODERN_PROTOCOL_VERSIONS)[-1]
    with ServerProcess(script, runtime_root=runtime_root, label=f"{mode}-modern") as server:
        envelope = {"_meta": modern_meta(modern_version)}
        document["modern"] = {
            "discover": _frame_facts(server.call("server/discover", dict(envelope))),
            **{
                method: _frame_facts(server.call(method, dict(envelope)))
                for method in LISTING_METHODS
            },
        }
        server.close()

    assert document["classic"] and document["modern"], (
        f"the {mode} protocol probe produced no transcript for candidate {candidate.label}"
    )
    return document


def _differences(source: object, installed: object, *, path: str = "") -> list[str]:
    """Report bounded, addressed differences between two probe documents.

    Recursion stops at the first *level* that disagrees rather than walking to the
    leaves of every branch, so a projection that dropped a whole family reports
    one line naming the family instead of thousands naming its fields.
    """
    if source == installed:
        return []
    reports: list[str] = []
    if isinstance(source, Mapping) and isinstance(installed, Mapping):
        left = cast("Mapping[str, object]", source)
        right = cast("Mapping[str, object]", installed)
        missing = sorted(set(left) - set(right))
        extra = sorted(set(right) - set(left))
        if missing:
            reports.append(f"{path}: absent from the wheel: {missing}")
        if extra:
            reports.append(f"{path}: present only in the wheel: {extra}")
        for key in sorted(set(left) & set(right)):
            reports.extend(_differences(left[key], right[key], path=f"{path}.{key}"))
        return reports
    if isinstance(source, list) and isinstance(installed, list):
        left_items = cast("list[object]", source)
        right_items = cast("list[object]", installed)
        if len(left_items) != len(right_items):
            return [f"{path}: length {len(left_items)} from source, {len(right_items)} from wheel"]
        for index, (one, other) in enumerate(zip(left_items, right_items, strict=True)):
            reports.extend(_differences(one, other, path=f"{path}[{index}]"))
        return reports
    return [f"{path}: source {source!r} != wheel {installed!r}"]


def test_extracted_wheel_matches_source_contract(candidate: InstalledCandidate) -> None:
    """Extracted-wheel bytes and repository source expose identical stable facts.

    TC-T11-001 (NFR-009, NFR-010). This contract was already satisfied when T11
    opened, and it is written to hold rather than to fail: the plan's T11.1
    instruction is to record that characterization honestly instead of
    manufacturing a failure. It is also this module's harness control — a passing
    result proves the build, the extraction, the two-runtime isolation, and both
    comparison layers are sound, so the documentation failure below cannot be
    blamed on them.
    """
    # Review F7: the binding catalog generation is owned by this test and the
    # adapter is checked against it, not consulted for it.
    assert ADAPTER_CATALOG_MAJOR == CATALOG_MAJOR, (
        f"ADR 0026 freezes v1 to catalog {CATALOG_MAJOR}; the adapter declares "
        f"{ADAPTER_CATALOG_MAJOR}"
    )

    installed = _facade_probe(candidate, candidate.runtime_root, "installed")
    source = _facade_probe(candidate, SOURCE_ROOT, "source")

    installed_origin = str(installed.pop(ORIGIN_KEY))
    source_origin = str(source.pop(ORIGIN_KEY))
    assert installed_origin.startswith(str(candidate.runtime_root)), (
        f"the installed probe must be served by the extracted candidate {candidate.label} at "
        f"{candidate.runtime_root}; it resolved {installed_origin}"
    )
    assert source_origin.startswith(str(SOURCE_ROOT)), (
        f"the source probe must be served by {SOURCE_ROOT}; it resolved {source_origin}"
    )

    # Sanity before equivalence: an empty catalog would compare equal to an empty
    # catalog and prove nothing.
    installed_catalog = cast("Mapping[str, Any]", installed["catalog"])
    assert cast("list[object]", installed_catalog["standards"]), (
        f"the extracted candidate {candidate.label} serves an empty catalog; run "
        "`project-standards standards sync-payload-projection --root .` before the build"
    )
    assert cast("list[object]", installed["tools"]), (
        f"the extracted candidate {candidate.label} registers no tools"
    )

    differences = _differences(source, installed)

    # The outer layer: what a client can actually reach, on both eras.
    installed_wire = _protocol_probe(candidate, candidate.runtime_root, "installed")
    source_wire = _protocol_probe(candidate, SOURCE_ROOT, "source")
    for era in ("classic", "modern"):
        transcript = cast("Mapping[str, Any]", installed_wire[era])
        listing = cast("Mapping[str, Any]", transcript["tools/list"])
        result = cast("Mapping[str, Any] | None", listing.get("result"))
        assert result is not None, (
            f"the extracted candidate {candidate.label} answers no tools/list on the {era} era: "
            f"{listing}"
        )
        assert cast("list[object]", result.get("tools", [])), (
            f"the extracted candidate {candidate.label} advertises no tools on the {era} era; the "
            "registry builders agree but no tool handler is reachable"
        )
    assert cast("Mapping[str, Any]", installed_wire["classic"])["capabilities"], (
        f"the extracted candidate {candidate.label} declares no capabilities"
    )
    differences.extend(_differences(source_wire, installed_wire, path="wire"))

    assert not differences, (
        f"the extracted candidate {candidate.label} does not expose the same stable facts as the "
        "repository source; per plan:475 this is a packaging/projection defect owned by an "
        "earlier task, not something T11 may correct:\n"
        + "\n".join(f"  - {line}" for line in differences[:40])
    )


# -- documented-command contract -----------------------------------------------


def _console_scripts(candidate: InstalledCandidate) -> dict[str, str]:
    """Return the console scripts the built distribution actually declares."""
    entry_points = candidate.dist_info / "entry_points.txt"
    assert entry_points.is_file(), (
        f"the extracted candidate {candidate.label} has no {entry_points.name}"
    )
    scripts: dict[str, str] = {}
    section = ""
    for raw in entry_points.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif section == "console_scripts" and "=" in line:
            name, _, target = line.partition("=")
            scripts[name.strip()] = target.strip()
    return scripts


class HelpSurface:
    """The installed CLI's help, reached only through the declared entry point.

    Every answer is produced by importing and calling the exact ``module:attr``
    the extracted ``entry_points.txt`` names (review F2), so a console script that
    points at an unshipped module fails here rather than after installation.
    Results are memoized because validating a document walks the same subcommands
    repeatedly.
    """

    def __init__(self, candidate: InstalledCandidate, target: str) -> None:
        self._candidate = candidate
        self._target = target
        self._cache: dict[tuple[str, ...], str] = {}

    def help(self, path: Sequence[str] = ()) -> str:
        key = tuple(path)
        if key not in self._cache:
            label = (
                f"`{CONSOLE_SCRIPT} {' '.join(key)} --help` through the declared entry point "
                f"{self._target} of candidate {self._candidate.label}"
            )
            self._cache[key] = _require(
                _bounded(
                    [sys.executable, "-c", ENTRY_POINT_SCRIPT, self._target, *key, "--help"],
                    env=_runtime_env(self._candidate.runtime_root, COLUMNS="200"),
                    label=label,
                ),
                label,
            )
        return self._cache[key]

    def subcommands(self, path: Sequence[str] = ()) -> frozenset[str]:
        match = CHOICE_SET.search(self.help(path))
        return frozenset(match.group(1).split(",")) if match is not None else frozenset()

    def options(self, path: Sequence[str] = ()) -> frozenset[str]:
        return frozenset(re.findall(r"--[a-z][a-z0-9-]*", self.help(path)))


def _sections(text: str) -> list[Section]:
    """Split a Markdown document into sections, ignoring headings inside fences."""
    sections: list[Section] = []
    heading, level = "", 0
    body: list[str] = []
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        match = None if fenced else HEADING.match(line)
        if match is None:
            body.append(line)
            continue
        sections.append(Section(heading=heading, level=level, body="\n".join(body)))
        heading, level = match.group(2).strip(), len(match.group(1))
        body = []
    sections.append(Section(heading=heading, level=level, body="\n".join(body)))
    return sections


def _fences(body: str) -> list[tuple[str, str]]:
    """Return (info string, content) for every fenced block in one body."""
    blocks: list[tuple[str, str]] = []
    info: str | None = None
    content: list[str] = []
    for line in body.splitlines():
        match = FENCE.match(line)
        if match is not None and info is None:
            info = match.group(1).strip().lower()
            content = []
        elif match is not None:
            blocks.append((info or "", "\n".join(content)))
            info = None
        elif info is not None:
            content.append(line)
    return blocks


def _shell_commands(body: str) -> list[str]:
    """Every runnable command line in the shell fences of one body.

    Line continuations are joined before anything is validated (review F6): a
    command split across backslash-terminated lines is one invocation, and
    scanning raw lines would let a continued ``project-standards`` / ``mcp
    --invented`` pair past both the subcommand and the option check.
    """
    commands: list[str] = []
    for info, content in _fences(body):
        if info not in SHELL_FENCES:
            continue
        buffer = ""
        for raw in content.splitlines():
            stripped = raw.strip()
            if stripped.startswith("$ "):
                stripped = stripped[2:].strip()
            if stripped.endswith("\\"):
                buffer += stripped[:-1].rstrip() + " "
                continue
            joined = (buffer + stripped).strip()
            buffer = ""
            if joined:
                commands.append(joined)
        if buffer.strip():
            commands.append(buffer.strip())
    return commands


def _tables(body: str) -> list[Table]:
    """Every Markdown table in one body, reduced to header and body cells."""
    tables: list[Table] = []
    rows: list[tuple[str, ...]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if TABLE_ROW.match(stripped):
            if TABLE_DIVIDER.match(stripped):
                continue
            rows.append(tuple(cell.strip() for cell in stripped.strip("|").split("|")))
            continue
        if rows:
            tables.append(Table(header=rows[0], rows=tuple(rows[1:])))
            rows = []
    if rows:
        tables.append(Table(header=rows[0], rows=tuple(rows[1:])))
    return tables


def _bare(cell: str) -> str:
    return cell.strip().strip("`").strip()


def _schema_properties(schema: Mapping[str, Any]) -> set[str]:
    """Every property name anywhere in one JSON Schema tree.

    Recursive because review F5 requires a tool's documented fields to be checked
    against *that tool's* schema tree, and nested result objects (findings,
    actions, results) carry the fields a reference table would list.
    """
    names: set[str] = set()
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        for name, child in cast("Mapping[str, Any]", properties).items():
            names.add(str(name))
            if isinstance(child, Mapping):
                names |= _schema_properties(cast("Mapping[str, Any]", child))
    for key in ("items", "additionalProperties", "not"):
        child = schema.get(key)
        if isinstance(child, Mapping):
            names |= _schema_properties(cast("Mapping[str, Any]", child))
    for key in ("anyOf", "oneOf", "allOf", "prefixItems"):
        children = schema.get(key)
        if isinstance(children, list):
            for item in cast("list[Any]", children):
                if isinstance(item, Mapping):
                    names |= _schema_properties(cast("Mapping[str, Any]", item))
    for key in ("$defs", "definitions"):
        defs = schema.get(key)
        if isinstance(defs, Mapping):
            for item in cast("Mapping[str, Any]", defs).values():
                if isinstance(item, Mapping):
                    names |= _schema_properties(cast("Mapping[str, Any]", item))
    return names


def _assign_topics(sections: Sequence[Section]) -> tuple[dict[str, str], list[str]]:
    """Match each required topic to a distinct heading with a non-empty body.

    A system of distinct representatives, computed by backtracking over nine
    topics: without distinctness one heading could discharge every obligation,
    and without the non-empty body an outline of empty headings could (F3a).
    """
    candidates: dict[str, list[int]] = {
        topic: [
            index
            for index, section in enumerate(sections)
            if section.level >= 2
            and re.search(pattern, section.heading, re.IGNORECASE)
            and section.body.strip()
        ]
        for topic, pattern in REQUIRED_TOPICS
    }

    order = sorted(candidates, key=lambda topic: len(candidates[topic]))
    assignment: dict[str, int] = {}
    used: set[int] = set()

    def _place(position: int) -> bool:
        if position == len(order):
            return True
        topic = order[position]
        for index in candidates[topic]:
            if index in used:
                continue
            used.add(index)
            assignment[topic] = index
            if _place(position + 1):
                return True
            used.discard(index)
            del assignment[topic]
        return False

    if _place(0):
        return {topic: sections[index].heading for topic, index in assignment.items()}, []
    unmatched = [topic for topic in candidates if not candidates[topic]]
    if unmatched:
        return {}, [
            f"{REFERENCE_DOC.name} has no non-empty section covering {topic}" for topic in unmatched
        ]
    return {}, [
        f"{REFERENCE_DOC.name} cannot map the nine required topics onto distinct non-empty "
        "sections; at least two topics share their only candidate heading"
    ]


def _strip_prefixes(tokens: list[str]) -> list[str]:
    while tokens and tokens[0] in COMMAND_PREFIXES:
        tokens = tokens[1:]
    return tokens


def _invocation_problems(command: str, surface: HelpSurface, origin: str) -> list[str]:
    """Validate one documented command against the installed help surfaces.

    Walks the subcommand tree the extracted CLI actually advertises, then checks
    every long option against the help of the deepest resolved path (review F4c).
    ``project-standards validate --invented`` therefore fails here, which the
    previous revision's `mcp`-only option check let through.
    """
    try:
        tokens = _strip_prefixes(shlex.split(command))
    except ValueError:
        return []
    if not tokens or tokens[0] != CONSOLE_SCRIPT:
        return []
    tokens = tokens[1:]
    if not tokens:
        return []
    # `project-standards 5.11.0` is what `--version` *prints*, not something a
    # reader can run: a first token that cannot be a subcommand name by grammar
    # means the span is transcribed output, and holding output to the CLI's
    # subcommand set would make the document unable to show what it prints.
    # An invented subcommand still matches this grammar and is still caught.
    if not SUBCOMMAND_NAME.match(tokens[0]) and not tokens[0].startswith("-"):
        return []

    path: list[str] = []
    while tokens and not tokens[0].startswith("-"):
        available = surface.subcommands(path)
        if tokens[0] in available:
            path.append(tokens.pop(0))
            continue
        if not path:
            return [
                f"{origin} documents `{CONSOLE_SCRIPT} {tokens[0]}`, which the installed CLI does "
                f"not advertise; it accepts {sorted(available)}"
            ]
        if available:
            return [
                f"{origin} documents `{CONSOLE_SCRIPT} {' '.join([*path, tokens[0]])}`, which the "
                f"installed `{' '.join(path)}` does not advertise; it accepts {sorted(available)}"
            ]
        break  # a positional argument to a leaf subcommand
    allowed = surface.options(path)
    return [
        f"{origin} documents `{token}` on `{CONSOLE_SCRIPT} {' '.join(path)}`; the installed "
        f"subcommand accepts {sorted(allowed)}"
        for token in tokens
        if LONG_OPTION.match(token) and token.split("=", 1)[0] not in allowed
    ]


def _config_entries(info: str, content: str) -> list[Mapping[str, Any]]:
    """Parse the approved client configuration formats into server entries.

    Codex CLI keys servers under ``[mcp_servers.<id>]`` in TOML; Claude Code uses
    a JSON ``mcpServers`` object. Both are the formats the T1 client matrix
    records, and both are parsed structurally rather than string-matched (review
    F6), so a block with the right words and the wrong ``args`` cannot pass.
    """
    try:
        if info == "toml":
            servers = cast("Mapping[str, Any]", tomllib.loads(content)).get("mcp_servers")
        elif info == "json":
            servers = cast("Mapping[str, Any]", json.loads(content)).get("mcpServers")
        else:
            return []
    except tomllib.TOMLDecodeError, json.JSONDecodeError, TypeError, AttributeError:
        return []
    if not isinstance(servers, Mapping):
        return []
    return [
        cast("Mapping[str, Any]", entry)
        for entry in cast("Mapping[str, Any]", servers).values()
        if isinstance(entry, Mapping)
    ]


def _client_config_problems(
    bodies: Sequence[str], token: str, surface: HelpSurface, mcp_options: frozenset[str]
) -> list[str]:
    """Require one parseable, correct launch configuration per primary client."""
    entries = [
        entry
        for body in bodies
        for info, content in _fences(body)
        for entry in _config_entries(info, content)
    ]
    if not entries:
        return [
            f"the {token} section of {REFERENCE_DOC.name} carries no parseable MCP server "
            "configuration block (codex: TOML `[mcp_servers.<id>]`; claude: JSON `mcpServers`)"
        ]
    problems: list[str] = []
    for entry in entries:
        command = str(entry.get("command", ""))
        if Path(command).name != CONSOLE_SCRIPT:
            problems.append(
                f"the {token} configuration in {REFERENCE_DOC.name} launches {command!r}; the "
                f"installed distribution declares the console script `{CONSOLE_SCRIPT}`"
            )
            continue
        raw = entry.get("args")
        args = [str(item) for item in cast("list[Any]", raw)] if isinstance(raw, list) else []
        if not args or args[0] != MCP_SUBCOMMAND:
            problems.append(
                f"the {token} configuration in {REFERENCE_DOC.name} passes args {args!r}; the "
                f"first argument must be `{MCP_SUBCOMMAND}`"
            )
            continue
        problems.extend(
            _invocation_problems(
                shlex.join([CONSOLE_SCRIPT, *args]),
                surface,
                f"the {token} configuration block in {REFERENCE_DOC.name}",
            )
        )
        for argument in args[1:]:
            if LONG_OPTION.match(argument) and argument.split("=", 1)[0] not in mcp_options:
                problems.append(
                    f"the {token} configuration in {REFERENCE_DOC.name} passes {argument!r} to "
                    f"`{MCP_SUBCOMMAND}`, which accepts {sorted(mcp_options)}"
                )
    return problems


def _capability_problems(section: Section | None, capabilities: Mapping[str, Any]) -> list[str]:
    """Require the documented capability claims to agree with the installed wire.

    The polarity is read from the server's own declarations, never asserted here:
    if a future build declared prompts or ``subscribe``, this check would demand
    the document say so instead (review F3c).
    """
    if section is None:
        return [f"{REFERENCE_DOC.name} has no capability-matrix section to check"]
    resources = cast("Mapping[str, Any]", capabilities.get("resources", {}))
    tools = cast("Mapping[str, Any]", capabilities.get("tools", {}))
    claims = (
        ("prompt", "prompts" in capabilities),
        ("subscribe", bool(resources.get("subscribe"))),
        ("listchanged", bool(resources.get("listChanged")) or bool(tools.get("listChanged"))),
    )
    rows = [" ".join(row) for table in _tables(section.body) for row in table.rows]
    if not rows:
        rows = section.body.splitlines()
    problems: list[str] = []
    for term, declared in claims:
        matching = [row for row in rows if term in row.lower().replace(" ", "").replace("_", "")]
        if not matching:
            problems.append(
                f"the capability matrix in {REFERENCE_DOC.name} states nothing about `{term}`, "
                f"which the installed server declares as {declared}"
            )
            continue
        for row in matching:
            if (NEGATION.search(row) is not None) is declared:
                problems.append(
                    f"the capability matrix in {REFERENCE_DOC.name} claims {row.strip()!r}, which "
                    f"disagrees with the installed declaration ({term} = {declared})"
                )
    for required in ("resource", "tool"):
        if not any(required in row.lower() for row in rows):
            problems.append(f"the capability matrix in {REFERENCE_DOC.name} omits {required}s")
    return problems


def _leading_subcommand(command: str) -> str:
    """The top-level subcommand of one documented invocation, or the empty string."""
    try:
        tokens = _strip_prefixes(shlex.split(command))
    except ValueError:
        return ""
    if len(tokens) < 2 or tokens[0] != CONSOLE_SCRIPT or tokens[1].startswith("-"):
        return ""
    return tokens[1]


def test_documented_commands_match_installed_entrypoint(candidate: InstalledCandidate) -> None:
    """Every command the reference documentation shows is one the installed artifact accepts.

    TC-T11-003 (FR-016, FR-020). Every expectation is derived from the extracted
    candidate — the console script and its declared target, the full subcommand
    and option help surface reached through that target, the tool names and
    schemas, the resource templates, the wire capabilities, and the exact version
    — so the test freezes artifact facts rather than prose it invented.

    Violations are collected rather than short-circuited, and a missing document
    is treated as an empty one, so the RED failure states the complete contract
    T11.3 has to satisfy instead of revealing it one run at a time.
    """
    scripts = _console_scripts(candidate)
    assert CONSOLE_SCRIPT in scripts, (
        f"the extracted candidate {candidate.label} declares no `{CONSOLE_SCRIPT}` console "
        f"script; got {sorted(scripts)}"
    )
    surface = HelpSurface(candidate, scripts[CONSOLE_SCRIPT])
    subcommands = surface.subcommands()
    assert MCP_SUBCOMMAND in subcommands, (
        f"the extracted candidate {candidate.label} advertises no `{MCP_SUBCOMMAND}` subcommand"
    )
    for family, members in (
        ("package-level", PACKAGE_LEVEL_SUBCOMMANDS),
        ("consumer-control-plane", CONTROL_PLANE_SUBCOMMANDS),
    ):
        assert members <= subcommands, (
            f"the {family} subcommand family {sorted(members - subcommands)} is not advertised by "
            f"candidate {candidate.label}; the family split needs updating with the CLI"
        )
    mcp_options = surface.options([MCP_SUBCOMMAND])

    installed = _facade_probe(candidate, candidate.runtime_root, "installed")
    tool_entries = cast("list[Mapping[str, Any]]", installed["tools"])
    tool_names = frozenset(str(entry["name"]) for entry in tool_entries)
    schema_tree = {
        str(entry["name"]): _schema_properties(cast("Mapping[str, Any]", entry["input_schema"]))
        | _schema_properties(cast("Mapping[str, Any]", entry["output_schema"]))
        for entry in tool_entries
    }
    declared_fields = {
        str(entry["name"]): sorted(
            set(cast("Mapping[str, Any]", entry["input_schema"]).get("properties", {}))
            | set(cast("Mapping[str, Any]", entry["output_schema"]).get("properties", {}))
        )
        for entry in tool_entries
    }
    templates = frozenset(
        str(entry["uri_template"])
        for entry in cast("list[Mapping[str, Any]]", installed["templates"])
    )
    classic = cast(
        "Mapping[str, Any]",
        _protocol_probe(candidate, candidate.runtime_root, "installed")["classic"],
    )
    capabilities = cast("Mapping[str, Any]", classic["capabilities"])
    version = str(cast("Mapping[str, Any]", classic["serverInfo"])["version"])

    problems: list[str] = []
    if not REFERENCE_DOC.is_file():
        problems.append(f"{REFERENCE_DOC.relative_to(REPO_ROOT)} does not exist")
    doc = REFERENCE_DOC.read_text(encoding="utf-8") if REFERENCE_DOC.is_file() else ""

    # Repository-compliant frontmatter (plan:474). Only the block's presence and
    # its identity keys are checked here; field values belong to
    # `project-standards validate`, which already owns them (freeze F-L, upheld).
    if not doc.startswith("---\n"):
        problems.append(f"{REFERENCE_DOC.name} must open with a Markdown frontmatter block")
    else:
        closing = doc.find("\n---\n", 4)
        if closing == -1:
            problems.append(f"{REFERENCE_DOC.name} frontmatter block is not closed")
        block = doc[4:closing] if closing != -1 else ""
        for field in ("id", "title", "doc_type", "status"):
            if not re.search(rf"^{field}:", block, re.MULTILINE):
                problems.append(f"{REFERENCE_DOC.name} frontmatter is missing `{field}`")

    sections = _sections(doc)
    topic_headings, topic_problems = _assign_topics(sections)
    problems.extend(topic_problems)
    by_heading = {section.heading: section for section in sections}

    for literal in REQUIRED_LITERALS:
        if literal not in doc:
            problems.append(f"{REFERENCE_DOC.name} never mentions `{literal}` (FR-020)")
    if version not in doc:
        problems.append(
            f"{REFERENCE_DOC.name} does not state the exact installed package version {version} "
            "(FR-020)"
        )

    problems.extend(
        _capability_problems(
            by_heading.get(topic_headings.get("capability matrix", "")), capabilities
        )
    )

    # Per-client setup: a parseable configuration block in that client's approved
    # format, resolving to the installed console script (review F3b). The client
    # set is the T1-frozen matrix, not a spelling chosen here.
    assert set(FROZEN_CLIENT_MATRIX), "the T1 primary-client matrix is empty"
    for token in (CODEX_CLIENT_TOKEN, CLAUDE_CLIENT_TOKEN):
        bodies = [section.body for section in sections if token in section.heading.lower()]
        if not bodies:
            problems.append(f"{REFERENCE_DOC.name} has no setup section for the {token} client")
            continue
        problems.extend(_client_config_problems(bodies, token, surface, mcp_options))

    # Every documented invocation, anywhere, against the full help surface
    # (review F4c). Shell fences are continuation-joined; inline code spans are
    # validated too but never count as the runnable smoke command (review F6).
    for section in sections:
        origin = (
            f"{REFERENCE_DOC.name} section {section.heading!r}"
            if section.heading
            else f"{REFERENCE_DOC.name} preamble"
        )
        for command in _shell_commands(section.body):
            problems.extend(_invocation_problems(command, surface, origin))
        for span in INLINE_CODE.findall(section.body):
            problems.extend(_invocation_problems(str(span), surface, origin))

    # FR-020's smoke command: a fenced, runnable launch invocation.
    if not any(
        re.match(rf"^(uv run )?{CONSOLE_SCRIPT} {MCP_SUBCOMMAND}\b", command)
        for section in sections
        for command in _shell_commands(section.body)
    ):
        problems.append(
            f"{REFERENCE_DOC.name} shows no runnable `{CONSOLE_SCRIPT} {MCP_SUBCOMMAND}` "
            "invocation in a fenced block (FR-020)"
        )

    # FR-016's normative acceptance (spec:272): equivalent package-level and
    # consumer-control-plane commands, plus a CI reference that exists.
    equivalents = by_heading.get(topic_headings.get("equivalent CLI and CI commands", ""))
    if equivalents is None:
        problems.append(f"{REFERENCE_DOC.name} has no equivalent-commands section")
    else:
        shown = {
            _leading_subcommand(command)
            for command in [
                *_shell_commands(equivalents.body),
                *(str(span) for span in INLINE_CODE.findall(equivalents.body)),
            ]
        } - {""}
        for family, members in (
            ("package-level", PACKAGE_LEVEL_SUBCOMMANDS),
            ("consumer-control-plane", CONTROL_PLANE_SUBCOMMANDS),
        ):
            if not shown & members:
                problems.append(
                    f"the equivalent-commands section of {REFERENCE_DOC.name} shows no real "
                    f"{family} command (FR-016, spec:272); it shows {sorted(shown)}"
                )
        if not [
            path for path in WORKFLOW_PATH.findall(equivalents.body) if (REPO_ROOT / path).is_file()
        ]:
            problems.append(
                f"the equivalent-commands section of {REFERENCE_DOC.name} names no CI workflow "
                f"that exists; the repository has "
                f"{sorted(path.name for path in WORKFLOWS.glob('*.yml'))}"
            )

    # Tool reference: an exact-set tool table, then per-tool field validation
    # against that tool's own schema tree (review F5).
    tool_tables = [
        table
        for section in sections
        for table in _tables(section.body)
        if {_bare(cell) for cell in table.column(0)} & tool_names
    ]
    if not tool_tables:
        problems.append(
            f"{REFERENCE_DOC.name} has no tool table listing the installed tools "
            f"{sorted(tool_names)}"
        )
    for table in tool_tables:
        listed = {_bare(cell) for cell in table.column(0)}
        if listed != set(tool_names):
            problems.append(
                f"a tool table in {REFERENCE_DOC.name} lists {sorted(listed)}; the installed "
                f"registry exposes exactly {sorted(tool_names)}"
            )
    for name in sorted(tool_names):
        owned = [section for section in sections if name in section.heading]
        if not owned:
            problems.append(f"{REFERENCE_DOC.name} has no reference section for the tool `{name}`")
            continue
        body = "\n".join(section.body for section in owned)
        problems.extend(
            f"the `{name}` section of {REFERENCE_DOC.name} does not document its declared schema "
            f"field `{field}`"
            for field in declared_fields[name]
            if f"`{field}`" not in body
        )
        for table in _tables(body):
            for cell in table.column(0):
                field = _bare(cell)
                if SNAKE_TOKEN.match(field) and field not in schema_tree[name]:
                    problems.append(
                        f"the `{name}` section of {REFERENCE_DOC.name} documents a field "
                        f"`{field}` that is absent from that tool's input/output schemas"
                    )

    problems.extend(
        f"{REFERENCE_DOC.name} does not document the installed resource template `{template}`"
        for template in sorted(templates)
        if template not in doc
    )

    # README is the entry point a reader arrives through; a reference document
    # nothing links to is not documentation.
    readme = README.read_text(encoding="utf-8")
    if "docs/mcp-server.md" not in readme:
        problems.append("README.md does not link to docs/mcp-server.md")
    for section in _sections(readme):
        for command in _shell_commands(section.body):
            problems.extend(_invocation_problems(command, surface, "README.md"))
        for span in INLINE_CODE.findall(section.body):
            problems.extend(_invocation_problems(str(span), surface, "README.md"))

    assert not problems, (
        f"the documented-command contract for the extracted candidate {candidate.label} is "
        f"absent or incomplete ({len(problems)} findings):\n"
        + "\n".join(f"  {n}. {p}" for n, p in enumerate(problems, 1))
    )
