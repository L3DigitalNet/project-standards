"""Protocol resource registration, URI grammar, and read integrity (T6).

Covers TC-T6-001 (list/read return exact metadata and bytes), TC-T6-002 (fixture
package growth changes the resource surface, never the tool surface), TC-T6-003
(an invalid distribution fails startup and post-startup byte drift fails the
read), TC-T6-004 (the URI contract is generation/version qualified and
deterministic), and TC-T6-005 (every declared resource-descriptor field survives
the protocol projection).

Four authorities constrain every expectation here and none of them may be
re-derived by the module under test:

*ADR 0026, resource URI grammar* — three URI forms exist and no others:
``standards://catalog/{catalog_major}``, ``standards://{standard_id}/{version}``,
and ``standards://{standard_id}/{version}/resources/{resource_id}``. Identifiers
appear exactly as the installed catalog declares them; there is no trailing
slash, no uppercase, and no percent-encoding beyond RFC 3986 necessity. A
non-canonical URI, or one naming an undeclared identifier, is a structured
not-found or invalid-URI error — never a fuzzy match, nearest version, or
case-insensitive recovery. The record also disposes of two live producers that
disagree with the frozen grammar: the three-segment index form
``standards://{id}/{version}/{resource_id}`` is rejected outright, and a
two-segment ``standards://{id}/{resource_id}`` parses *positionally* as form 2,
so the resource id lands in the version slot and fails as an unknown version.

*The plan's T6 block* — the catalog resource is compact metadata, the package
resource is one exact ``StandardDescriptor``, and the payload resource returns
bytes plus the declared media type only after T2 rechecks the selected
declaration, contained path, and current byte digest. Registration is backed
*only* by ``McpServiceFacade.catalog``/``.standard``/``.resource``: T6 adds
protocol mapping and nothing else. "Lazy" means payload bytes enter protocol
context only on a selected read; it never defers the eager full-distribution
startup integrity check.

*The SDK* — ``mcp==2.0.0`` serves both protocol eras from one server object but
locks a connection's era at its opening request, so every probe uses one process
per era (T5.2 review F1). ``ReadResourceRequestParams.uri`` is a plain ``str``:
the SDK performs no URI parsing, normalization, or scheme validation whatsoever,
so every canonicalization rule above is the adapter's to enforce and none of it
can be inherited from the protocol layer.

*The fixture catalog* — the assertions are driven by
``McpServiceFacade.from_installed`` over the same bytes the server serves, never
by literals restating the fixture. That is what makes the suite a projection
test: a mapper that dropped, reordered, or re-derived a declared fact fails
against the service layer that already owns it.

**The harness is reused, not re-implemented.** ``tests/mcp_server/
test_transport.py`` owns the deadline-bound subprocess, transcript, and
capability machinery, and this module imports it rather than forking a second
copy that could drift from the T5 contract. ``build_installed_tree`` from
``tests/mcp_services/helpers.py`` owns the fixture projection.

``test_fixture_runtime_harness_serves_the_fixture_catalog`` is the RED control
required by T6.2: it drives this module's runtime builder, oracle facade, and
session machinery against surfaces that already exist (T5's server, T2's
facade), so a failure anywhere else is provably the absent resource registration
rather than a broken fixture. It is a test oracle, not a sketch of the GREEN
design.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib
import importlib.util
import json
import shutil
import time
import tomllib
import uuid
from collections.abc import Generator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from mcp_types import INTERNAL_ERROR, INVALID_PARAMS, METHOD_NOT_FOUND
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

from project_standards._version import package_version
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_services import (
    CatalogDescriptor,
    McpServiceFacade,
    RelationshipSet,
    ResourceDescriptor,
    ServiceError,
    StandardDescriptor,
)
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import PayloadManifest
from tests.mcp_server.test_transport import (
    CLI_LAUNCH,
    CODEX_CLIENT_REVISION,
    QUIET_WINDOW,
    RUNTIME_ROOT,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_modern_result_contract,
    assert_no_list_change_promises,
    assert_no_write_surface,
    assert_stdout_is_protocol_only,
    declared_capabilities,
    expect_error,
    expect_result,
    modern_meta,
    require_mcp_subcommand,
)
from tests.mcp_services.helpers import build_installed_tree

ADAPTER_PACKAGE = "project_standards.mcp_server"

# ADR 0026 scopes v1 to one catalog generation, and `models.CATALOG_MAJOR` makes
# it a constant rather than a launch option. The fixture catalog is major 5 for
# the same reason the installed one is: `InstalledDistribution.load_catalog`
# refuses a generation that disagrees with the installed tool's major version.
FIXTURE_CATALOG_MAJOR = "5"
SCHEME_PREFIX = "standards://"
CATALOG_URI = f"{SCHEME_PREFIX}catalog/{FIXTURE_CATALOG_MAJOR}"

# The two parameterized forms, spelled exactly as ADR 0026 spells them. Frozen
# literally because the record's stop/backtrack condition is explicit: if the
# SDK cannot express these templates *without changing their identity*, T6
# returns to T1 rather than registering alternate URIs.
PACKAGE_TEMPLATE = "standards://{standard_id}/{version}"
RESOURCE_TEMPLATE = "standards://{standard_id}/{version}/resources/{resource_id}"
FROZEN_TEMPLATES = frozenset({PACKAGE_TEMPLATE, RESOURCE_TEMPLATE})

# The literal segment that separates form 3 from the rejected three-segment
# index form ADR 0026 discloses as a divergence from `standards/catalog.md`.
RESOURCES_SEGMENT = "resources"

# Catalog *roles*, not versions. A URI naming one of these in the version slot
# is the mutable-alias class FR-027 exists to refuse: it would resolve to a
# different payload the moment the catalog moved.
MUTABLE_ALIASES = ("latest", "default", "stable", "candidate", "retained", "current")

# Growth fixture (T6.2 Codex review F5). The added family's identity is generated
# per session and is absent from the baseline fixture in every component —
# standard id, version, and two resource ids — because a predictable growth target
# lets an adapter with per-package branches pass a test that exists to prove
# data-driven template expansion (FR-004, and T6's stop against per-package
# handlers). Nothing in the suite may hard-code the generated identity.
GENERATED_ID_PREFIX = "epsilon"
GENERATED_VERSION = "7.3"
GENERATED_NOTE_RESOURCE = "generated-note"
GENERATED_NOTE_ROLE = "generated-note"
GENERATED_BINARY_RESOURCE = "binary-payload"
GENERATED_BINARY_ROLE = "binary-reference"

# Deliberately not valid UTF-8 anywhere (F6): every byte value appears, so a
# mapper that decodes payloads as text cannot serve it, and the protocol must
# take the base64 `blob` path to satisfy FR-003's exact-byte promise.
GENERATED_BINARY_BYTES = bytes(range(256)) * 3
GENERATED_BINARY_MEDIA_TYPE = "application/octet-stream"

# The three installed subtrees `InstalledDistribution.load_catalog` reads. They
# are replaced wholesale rather than merged so no real Catalog 5 fact can leak
# into a fixture assertion.
FIXTURE_SUBTREES = ("catalogs", "families", "payloads")

# FR-001's own field list for the catalog discovery resource, in DTO spelling:
# "every installed family with ID, title, status, package version, exposure,
# capabilities, relations, and version-qualified resource URIs". The resource URIs
# are handled separately because they are nested. Written from the spec sentence
# rather than read from the implementation's mask, so the two can disagree.
FR001_CATALOG_FIELDS = (
    "standard_id",
    "title",
    "status",
    "package_version",
    "exposure",
    "capabilities",
    "relationships",
)

# The resource-not-found code pre-2026 revisions define. The evidence matrix
# records the change to INVALID_PARAMS at 2026-07-28; `mcp_types` cannot export it
# because that revision lists it as reserved-never-reused, so a legacy connection
# is the only place it may legally appear (T6.4 review F2).
LEGACY_RESOURCE_NOT_FOUND = -32002

# Bounded pagination follow. The registration set is static and small, so a
# server that keeps handing out cursors is looping, not paginating.
MAX_LIST_PAGES = 32

# How long a launch on a corrupt distribution may take to *die*. The startup
# check must complete before stdio, so the process must exit on its own without
# ever being sent a frame and without its stdin being closed (F4): a server that
# reached stdio would still be running when this window expires.
STARTUP_DEADLINE = 30.0

# The exact resource whose bytes are drifted after a successful startup, and the
# file behind it. The path is named because a byte-level tamper needs one, and
# the test cross-checks it against the facade's digest-verified bytes so a
# fixture layout change fails as a fixture problem rather than as an adapter bug.
INTEGRITY_STANDARD = "alpha"
INTEGRITY_VERSION = "2.0"
INTEGRITY_RESOURCE = "readme"
INTEGRITY_PAYLOAD_FILE = "payloads/alpha/2.0/README.md"

# A payload byte the suite never reads through the protocol. Corrupting it
# proves the startup integrity check covers the *whole* distribution rather than
# only what a session happens to select (plan T6: "never defers the eager full
# distribution startup integrity check"). It is a declared artifact source, not
# a declared resource, so no URI addresses it.
UNREAD_PAYLOAD_BYTE_TARGET = "payloads/gamma/1.0/workflow.yml"

# The stable codes `mcp_services.ServiceError` already assigns to the failure
# classes reachable through a resource read. Used to give a refusal a
# URI-independent *class* identity: two refusals of the same class must compare
# equal even though they name different URIs. Their presence on the wire is
# required only for the one class that provably originates in the service layer
# (see TC-T6-003); for the rest they simply sharpen the comparison when present.
SERVICE_ERROR_CODES = (
    "catalog-invalid",
    "standard-not-found",
    "resource-not-found",
    "resource-integrity",
)

# Marker for the recording-facade launch script below. Prefixed so the records
# are separable from anything else the SDK, anyio, or a warning writes to stderr.
SPY_PREFIX = "T6-SPY "

# Serves through the real `create_server`/`run_stdio` pair with the facade
# wrapped in a call recorder. This is the only launch in the suite that bypasses
# the CLI entry point, and it exists for one reason: "URI parsing must reject
# ... before service lookup" is a claim about ordering across the adapter's
# internal boundary, and the wire cannot see that boundary. The proxy delegates
# everything, so the server under observation is otherwise the real one.
SPY_LAUNCH_TEMPLATE = '''
import json
import sys
from pathlib import Path

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server import transport
from project_standards.mcp_server.models import AdapterConfiguration
from project_standards.mcp_services import McpServiceFacade


class RecordingFacade:
    """The real facade, with every call reported on stderr before it runs."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        attribute = getattr(self._inner, name)
        if not callable(attribute):
            return attribute

        def recorded(*args, **kwargs):
            record = {
                "call": name,
                "args": [repr(value) for value in args],
                "kwargs": {key: repr(value) for key, value in sorted(kwargs.items())},
            }
            print("__SPY_PREFIX__" + json.dumps(record), file=sys.stderr, flush=True)
            return attribute(*args, **kwargs)

        return recorded


facade = McpServiceFacade.from_installed(
    InstalledDistribution(Path("__PACKAGE_ROOT__"), tool_release="__TOOL_RELEASE__"),
    CatalogMajor("__CATALOG_MAJOR__"),
)
transport.run_stdio(transport.create_server(RecordingFacade(facade), AdapterConfiguration()))
'''


def require_resources_module() -> ModuleType:
    """Import the planned T6 registration module, or fail as a RED assertion.

    The plan's RED contract requires a missing planned module to surface as a
    test assertion rather than a collection error, so nothing in this file
    imports ``project_standards.mcp_server.resources`` at module scope.
    """
    dotted = f"{ADAPTER_PACKAGE}.resources"
    try:
        spec = importlib.util.find_spec(dotted)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        f"planned module {dotted} is absent; the T6 resource registration does not exist yet"
    )
    return importlib.import_module(dotted)


# -- fixture distribution ------------------------------------------------------


def _append_catalog_entry(path: Path, entry: Mapping[str, str]) -> None:
    """Add one package to an installed catalog projection, preserving its shape.

    Rewritten from parsed TOML rather than patched textually because the
    projection is the authority `load_catalog` validates against: every existing
    entry keeps all of its declared keys, so the result is a *valid* larger
    catalog rather than a corrupted one (which is a different fixture's job).
    ``CatalogSource`` re-sorts packages by (id, version) on load, so the appended
    entry's file position is irrelevant to the served order.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    packages = cast("list[dict[str, object]]", data["packages"])
    assert (entry["id"], entry["version"]) not in {
        (existing["id"], existing["version"]) for existing in packages
    }, f"the generated identity {entry['id']}@{entry['version']} already exists in {path}"
    lines = [
        f'schema_version = "{data["schema_version"]}"',
        f"catalog_major = {data['catalog_major']}",
        "",
    ]
    for existing in (*packages, dict(entry)):
        lines.append("[[packages]]")
        lines.extend(f'{key} = "{value}"' for key, value in existing.items())
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


@dataclass(frozen=True, slots=True)
class GeneratedFamily:
    """One valid standard family synthesized into an installed fixture runtime.

    Its identity is generated per session (F5), so no assertion and no adapter
    can hard-code it. ``binary_uri`` addresses a declared resource whose bytes
    are not valid UTF-8 anywhere, which is what forces the protocol's base64
    representation (F6).
    """

    runtime: Path
    standard_id: str
    version: str
    resource_bytes: Mapping[str, bytes]

    @property
    def package_uri(self) -> str:
        return f"standards://{self.standard_id}/{self.version}"

    def resource_uri(self, resource_id: str) -> str:
        return f"{self.package_uri}/resources/{resource_id}"

    @property
    def binary_uri(self) -> str:
        return self.resource_uri(GENERATED_BINARY_RESOURCE)


def _render_generated_payload(
    standard_id: str, version: str, resources: Sequence[tuple[str, str, str, str, str]]
) -> str:
    """Render a valid V2 payload manifest for the generated family.

    Written out rather than templated from an existing fixture file because the
    generated family must carry *novel* resource ids and a media type no baseline
    payload declares. The required-role rules the manifest model enforces are the
    reason the first three entries are fixed: exactly one each of
    ``canonical-standard``, ``agent-summary``, and ``config-schema``, and — since
    this payload is ``reference-only`` — no ``adoption-guide``.
    """
    lines = [
        'schema_version = "1.0"',
        "",
        "[payload]",
        f'standard = "{standard_id}"',
        f'version = "{version}"',
        'availability = "reference-only"',
        "",
        "[config]",
        'schema_resource = "config-schema"',
        "",
        "[capabilities]",
        f'provides = ["{standard_id}.reference"]',
        "consumes_platform = []",
        "",
    ]
    for resource_id, role, relative_path, media_type, digest in resources:
        lines.extend(
            [
                "[[resources]]",
                f'id = "{resource_id}"',
                f'role = "{role}"',
                f'path = "{relative_path}"',
                f'media_type = "{media_type}"',
                f'digest = "{digest}"',
                "",
            ]
        )
    return "\n".join(lines)


def add_generated_family(package_root: Path, *, standard_id: str, version: str) -> GeneratedFamily:
    """Synthesize one valid, digest-sealed family into an installed fixture tree.

    Written directly into the installed projection rather than into a source tree
    and re-projected, because `InstalledDistribution.load_catalog` reads exactly
    three locations — ``catalogs/{major}.toml``, ``families/{id}/standard.toml``,
    and ``payloads/{id}/{version}/`` — and nothing else. Every digest is computed
    from the bytes just written and the payload aggregate comes from the
    authoritative `validate_payload_integrity`, so the result is genuine rather
    than merely well-shaped: if any of it were wrong, `oracle_facade` would
    refuse to construct and the test would fail on its fixture rather than on the
    adapter (the reseal pattern `tests/test_installed_wrappers.py` established).
    """
    payload_directory = package_root / "payloads" / standard_id / version
    payload_directory.mkdir(parents=True)
    files: dict[str, bytes] = {
        "README.md": f"# {standard_id} {version}\n\nGenerated growth fixture.\n".encode(),
        "agent-summary.md": f"Generated agent summary for {standard_id}.\n".encode(),
        "config.schema.json": (
            b'{"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",\n'
            b' "additionalProperties": false, "properties": {}}\n'
        ),
        "note.md": f"Generated note resource for {standard_id} {version}.\n".encode(),
        "payload.bin": GENERATED_BINARY_BYTES,
    }
    for name, data in files.items():
        (payload_directory / name).write_bytes(data)

    declarations = (
        ("readme", "canonical-standard", "README.md", "text/markdown"),
        ("agent-summary", "agent-summary", "agent-summary.md", "text/markdown"),
        ("config-schema", "config-schema", "config.schema.json", "application/schema+json"),
        (GENERATED_NOTE_RESOURCE, GENERATED_NOTE_ROLE, "note.md", "text/markdown"),
        (
            GENERATED_BINARY_RESOURCE,
            GENERATED_BINARY_ROLE,
            "payload.bin",
            GENERATED_BINARY_MEDIA_TYPE,
        ),
    )
    manifest_path = payload_directory / "payload.toml"
    manifest_path.write_text(
        _render_generated_payload(
            standard_id,
            version,
            [
                (
                    resource_id,
                    role,
                    relative_path,
                    media_type,
                    f"sha256:{hashlib.sha256(files[relative_path]).hexdigest()}",
                )
                for resource_id, role, relative_path, media_type in declarations
            ],
        ),
        encoding="utf-8",
    )

    # `load_payload_manifest` additionally requires the source layout
    # (`.../versions/{version}/payload.toml`); the installed projection is
    # `payloads/{id}/{version}/`, so the model is validated directly — the same
    # split `_load_installed_payload` makes on the production side.
    manifest = PayloadManifest.model_validate(tomllib.loads(manifest_path.read_text("utf-8")))
    aggregate = validate_payload_integrity(payload_directory, manifest).aggregate_digest.value

    family_path = package_root / "families" / standard_id / "standard.toml"
    family_path.parent.mkdir(parents=True)
    # `load_family_manifest` requires a regular README.md beside the index.
    (family_path.parent / "README.md").write_text(f"# Generated {standard_id}\n", encoding="utf-8")
    family_path.write_text(
        "\n".join(
            [
                'schema_version = "2.0"',
                "",
                "[standard]",
                f'id = "{standard_id}"',
                f'name = "Generated {standard_id}"',
                'summary = "Synthetic family generated by the T6 growth fixture."',
                'status = "active"',
                "",
                "[[versions]]",
                f'version = "{version}"',
                f'payload = "versions/{version}/payload.toml"',
                f'digest = "{aggregate}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    _append_catalog_entry(
        package_root / f"catalogs/{FIXTURE_CATALOG_MAJOR}.toml",
        {
            "id": standard_id,
            "version": version,
            "digest": aggregate,
            "role": "reference-only",
        },
    )
    return GeneratedFamily(
        runtime=package_root.parent,
        standard_id=standard_id,
        version=version,
        resource_bytes={
            resource_id: files[relative_path] for resource_id, _, relative_path, _ in declarations
        },
    )


def build_fixture_runtime(destination: Path) -> Path:
    """Return an importable runtime root whose Catalog 5 is the package fixture.

    The real adapter code is linked in and only the three catalog subtrees are
    replaced, so the server under test is the installed distribution's own code
    serving a *bounded, mutable* catalog. That is what makes the fixture
    assertions exact — the real Catalog 5 grows with every released standard, so
    a suite that pinned its contents would fail on the next release — and what
    lets a test corrupt one payload byte without touching the repository.

    The staging tree is deleted before returning, so a runtime that reached
    sibling source files instead of its own projection cannot pass.
    """
    staging = destination / "staging"
    installed = build_installed_tree(staging)
    runtime = destination / "runtime"
    package = runtime / "project_standards"
    package.mkdir(parents=True)
    for entry in sorted((RUNTIME_ROOT / "project_standards").iterdir()):
        if entry.name in FIXTURE_SUBTREES or entry.name == "__pycache__":
            continue
        (package / entry.name).symlink_to(entry)
    for name in FIXTURE_SUBTREES:
        shutil.copytree(installed / name, package / name)
    shutil.rmtree(installed.parent)
    return runtime


def oracle_facade(runtime: Path) -> McpServiceFacade:
    """Build the §5.5 facade over the same bytes the server will serve.

    Every expected descriptor, ordering, media type, and byte string in this
    module comes from here. T6 is a protocol *mapping* task, so its oracle is
    the service layer that already owns those facts — not a second copy of them
    written into the tests, which would let a mapper and its test drift
    together.
    """
    return McpServiceFacade.from_installed(
        InstalledDistribution(runtime / "project_standards", tool_release=package_version()),
        CatalogMajor(FIXTURE_CATALOG_MAJOR),
    )


def package_uri(descriptor: StandardDescriptor) -> str:
    return f"standards://{descriptor.standard_id}/{descriptor.package_version}"


def expected_package_uris(catalog: CatalogDescriptor) -> tuple[str, ...]:
    return tuple(package_uri(descriptor) for descriptor in catalog.standards)


def expected_resource_uris(catalog: CatalogDescriptor) -> tuple[str, ...]:
    return tuple(
        resource.uri for descriptor in catalog.standards for resource in descriptor.resources
    )


def declared_resources(catalog: CatalogDescriptor) -> dict[str, ResourceDescriptor]:
    """Every declared payload resource of the catalog, keyed by its canonical URI."""
    return {
        resource.uri: resource
        for descriptor in catalog.standards
        for resource in descriptor.resources
    }


@pytest.fixture(scope="module")
def full_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The complete fixture catalog, shared read-only across tests."""
    return build_fixture_runtime(tmp_path_factory.mktemp("full"))


@pytest.fixture(scope="module")
def duplicate_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A second, byte-equivalent fixture catalog at a different filesystem path.

    Determinism (NFR-005) means the served order is a function of the catalog,
    not of directory iteration order or of where the distribution happens to
    live. Two independently built trees are the only way to observe that.
    """
    return build_fixture_runtime(tmp_path_factory.mktemp("duplicate"))


@pytest.fixture(scope="module")
def grown_family(tmp_path_factory: pytest.TempPathFactory) -> GeneratedFamily:
    """The baseline fixture catalog plus one family with a generated identity.

    Built as a separate distribution rather than by mutating ``full_runtime``
    because growth is observed as two server instances: v1 does not watch a
    running process for installation changes (FR-004). The identity is a fresh
    UUID fragment per session, which is what makes the growth test unsatisfiable
    by per-package branches.
    """
    runtime = build_fixture_runtime(tmp_path_factory.mktemp("grown"))
    return add_generated_family(
        runtime / "project_standards",
        standard_id=f"{GENERATED_ID_PREFIX}-{uuid.uuid4().hex[:10]}",
        version=GENERATED_VERSION,
    )


@pytest.fixture
def mutable_runtime(tmp_path: Path) -> Path:
    """A private fixture catalog a test may corrupt after the server starts."""
    return build_fixture_runtime(tmp_path / "mutable")


# -- protocol sessions ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Era:
    """One protocol era, with the opening contract and per-request envelope it needs.

    A connection's era is fixed by the SDK at its opening request, so this is
    per-*process* state rather than per-request state; switching mid-connection
    was the T5 RED oracle bug (review F1). Both eras are exercised because the
    installed Codex CLI speaks 2025-06-18 only while 2026-07-28 is the final
    published revision, and a resource surface that works in one era and not the
    other is a broken surface for half the client matrix.
    """

    name: str
    revision: str
    modern: bool

    @property
    def envelope(self) -> dict[str, Any] | None:
        return {"_meta": modern_meta(self.revision)} if self.modern else None

    def open(self, server: ServerProcess) -> dict[str, Any]:
        return server.discover(self.revision) if self.modern else server.handshake(self.revision)

    def params(self, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        params = dict(self.envelope or {})
        if extra is not None:
            params.update(extra)
        return params


ERAS = (
    Era("classic", CODEX_CLIENT_REVISION, modern=False),
    *(Era(f"modern-{version}", version, modern=True) for version in MODERN_PROTOCOL_VERSIONS),
)
ERA_IDS = [era.name for era in ERAS]
MODERN_ERA = ERAS[-1]


@contextlib.contextmanager
def resource_session(
    era: Era, *, runtime_root: Path, label: str, script: str = CLI_LAUNCH
) -> Generator[tuple[ServerProcess, dict[str, Any]]]:
    """Start one server over a fixture runtime and complete its opening contract."""
    with ServerProcess(script, runtime_root=runtime_root, label=f"{label}-{era.name}") as server:
        yield server, era.open(server)


def list_resources(server: ServerProcess, era: Era) -> list[dict[str, Any]]:
    """Every registered resource, following pagination cursors if the server pages."""
    entries: list[dict[str, Any]] = []
    cursor: object = None
    for _ in range(MAX_LIST_PAGES):
        extra = {"cursor": cursor} if isinstance(cursor, str) else None
        result = expect_result(server, server.call("resources/list", era.params(extra)))
        if era.modern:
            assert_modern_result_contract(server, result)
        raw = result.get("resources")
        assert isinstance(raw, list), server.diagnosis(
            f"resources/list returned no resources array: {result!r}"
        )
        entries.extend(
            as_object(item, "a resources/list entry") for item in cast("list[object]", raw)
        )
        cursor = result.get("nextCursor")
        if not isinstance(cursor, str) or not cursor:
            return entries
    raise AssertionError(server.diagnosis("resources/list never stopped paginating"))


def list_templates(server: ServerProcess, era: Era) -> list[dict[str, Any]]:
    """Every registered resource template, following pagination cursors."""
    entries: list[dict[str, Any]] = []
    cursor: object = None
    for _ in range(MAX_LIST_PAGES):
        extra = {"cursor": cursor} if isinstance(cursor, str) else None
        result = expect_result(server, server.call("resources/templates/list", era.params(extra)))
        if era.modern:
            assert_modern_result_contract(server, result)
        raw = result.get("resourceTemplates")
        assert isinstance(raw, list), server.diagnosis(
            f"resources/templates/list returned no resourceTemplates array: {result!r}"
        )
        entries.extend(
            as_object(item, "a resources/templates/list entry")
            for item in cast("list[object]", raw)
        )
        cursor = result.get("nextCursor")
        if not isinstance(cursor, str) or not cursor:
            return entries
    raise AssertionError(server.diagnosis("resources/templates/list never stopped paginating"))


def read_frame(server: ServerProcess, era: Era, uri: str) -> dict[str, Any]:
    return server.call("resources/read", era.params({"uri": uri}))


def read_contents(server: ServerProcess, era: Era, uri: str) -> list[dict[str, Any]]:
    """The contents array of one successful read."""
    result = expect_result(server, read_frame(server, era, uri))
    if era.modern:
        assert_modern_result_contract(server, result)
    raw = result.get("contents")
    assert isinstance(raw, list) and raw, server.diagnosis(
        f"resources/read returned no contents for {uri}: {result!r}"
    )
    return [
        as_object(item, "a resources/read contents entry") for item in cast("list[object]", raw)
    ]


def read_one(server: ServerProcess, era: Era, uri: str) -> dict[str, Any]:
    """The single contents entry of one exact resource read.

    Exactness is the point: a declared resource is one identity with one byte
    string and one declared media type (FR-003, DR-002), so a read that answered
    with several contents entries would have invented an aggregation the
    declaration does not describe.
    """
    contents = read_contents(server, era, uri)
    assert len(contents) == 1, server.diagnosis(
        f"reading the exact resource {uri} returned {len(contents)} contents entries"
    )
    entry = contents[0]
    assert entry.get("uri") == uri, server.diagnosis(
        f"a read of {uri} answered for {entry.get('uri')!r} instead"
    )
    return entry


def content_bytes(server: ServerProcess, entry: Mapping[str, Any]) -> bytes:
    """The exact bytes a contents entry carries, in either wire representation.

    The protocol carries text resources as ``text`` and binary ones as base64
    ``blob``. Which representation a declared media type takes is the
    implementation's choice, so this recovers bytes from either rather than
    freezing that choice; what the callers then assert is byte equality with the
    service layer's digest-verified bytes.
    """
    blob = entry.get("blob")
    if isinstance(blob, str):
        return base64.b64decode(blob, validate=True)
    text = entry.get("text")
    assert isinstance(text, str), server.diagnosis(
        f"a contents entry carries neither text nor blob: {entry!r}"
    )
    return text.encode("utf-8")


def frame_json(frame: Mapping[str, Any]) -> str:
    """One searchable rendering of a decoded frame, nested documents included.

    Used for *negative* searches — no payload bytes, no absolute path — and for
    the descriptor-field recovery check, where placement is deliberately not
    frozen. It is never the oracle for metadata *correctness*: substring presence
    over a whole frame is an evasion oracle, which is why the metadata resources
    are compared structurally instead (see ``metadata_document``).
    """
    return json.dumps(frame, sort_keys=True)


def metadata_document(server: ServerProcess, era: Era, uri: str) -> dict[str, Any]:
    """The decoded metadata document one metadata resource serves.

    T6.2 Codex review F2: the catalog and package resources are compared
    *structurally* against the §5.5 DTO projection, so the body must be one
    coherent JSON document rather than prose that happens to contain the right
    tokens. Its media type must say so — a client cannot be expected to guess
    that a ``text/markdown`` body is parseable JSON.
    """
    entry = read_one(server, era, uri)
    media_type = entry.get("mimeType")
    assert isinstance(media_type, str) and media_type.endswith("json"), server.diagnosis(
        f"{uri} serves a structured metadata document, so its media type must be a JSON "
        f"type; got {media_type!r}"
    )
    raw = content_bytes(server, entry)
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            server.diagnosis(f"{uri} did not serve a decodable JSON document: {raw[:400]!r}")
        ) from exc
    return as_object(decoded, f"the metadata document served by {uri}")


def dto_projection(model: CatalogDescriptor | StandardDescriptor) -> dict[str, Any]:
    """The DTO's own jsonable projection, which is the package-metadata oracle.

    Derived from the model, never hand-written: §5.5 fixes the DTO field sets, so
    a hand-copied expected structure in this file would be a second schema free
    to drift from the one the service layer publishes. A field added to
    ``StandardDescriptor`` therefore widens this oracle automatically instead of
    silently escaping it.
    """
    return model.model_dump(mode="json")


def catalog_projection(catalog: CatalogDescriptor) -> dict[str, Any]:
    """The FR-001 masked projection the catalog resource owes (T6.4 review F1).

    The catalog resource is the *discovery* point, so it carries FR-001's field
    list — "every installed family with ID, title, status, package version,
    exposure, capabilities, relations, and version-qualified resource URIs" — and
    not the whole ``CatalogDescriptor``: the full DTO also carries every resource
    digest, role, and media type plus every provider declaration, which measures
    373,619 bytes against the real installed Catalog 5 and cannot be the "compact
    metadata" the plan requires or satisfy NFR-002.

    The field *names* are written out here because they are FR-001's own sentence
    — the spec is the authority on what discovery owes, and asserting the
    implementation's mask against the implementation's mask would prove nothing.
    Every *value* still comes from the DTO's ``model_dump``, so this stays a
    projection of the service layer's facts rather than a second schema: a changed
    status, exposure, capability, or relation value fails here.
    """
    dumped = catalog.model_dump(mode="json")
    return {
        "catalog_major": dumped["catalog_major"],
        "standards": [
            {
                **{field: standard[field] for field in FR001_CATALOG_FIELDS},
                "resources": [{"uri": resource["uri"]} for resource in standard["resources"]],
            }
            for standard in cast("list[dict[str, Any]]", dumped["standards"])
        ],
    }


def listed_uris(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    uris: list[str] = []
    for entry in entries:
        uri = entry.get("uri")
        assert isinstance(uri, str), f"a resources/list entry carries no string uri: {entry!r}"
        uris.append(uri)
    return uris


def template_strings(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    templates: list[str] = []
    for entry in entries:
        template = entry.get("uriTemplate")
        assert isinstance(template, str), (
            f"a resource template carries no string uriTemplate: {entry!r}"
        )
        templates.append(template)
    return templates


def tool_surface(server: ServerProcess, era: Era, capabilities: Mapping[str, Any]) -> str:
    """A comparable rendering of everything the server says about tools.

    Compared as a whole — declared capability plus the listing outcome — so
    TC-T6-002's "no tool-name change" claim survives T8/T9 registering the real
    six-tool registry: at that point both runtimes advertise the same six, and
    the equality still holds. Request ids are excluded because they differ by
    construction between two sessions.
    """
    frame = server.call("tools/list", era.params())
    if "error" in frame:
        listing: dict[str, Any] = {"error": expect_error(server, frame)["code"]}
    else:
        result = expect_result(server, frame)
        raw = result.get("tools")
        assert isinstance(raw, list), server.diagnosis(f"tools/list returned no array: {result!r}")
        listing = {
            "names": sorted(
                str(as_object(tool, "a tools/list entry").get("name"))
                for tool in cast("list[object]", raw)
            )
        }
    return json.dumps({"capability": capabilities.get("tools"), "listing": listing}, sort_keys=True)


def assert_structured_refusal(
    server: ServerProcess, frame: Mapping[str, Any], *, uri: str
) -> dict[str, Any]:
    """One structured rejection: an error, not a crash, and not a missing method.

    ``METHOD_NOT_FOUND`` would mean the resource surface is not registered at
    all, and the SDK's generic ``INTERNAL_ERROR``/"Internal server error" is
    what an *unhandled* handler exception becomes on the wire — the runner
    deliberately replaces such a body so handler internals never leak. Either
    outcome means the refusal was not designed, which is what NFR-004 ("all
    tool/resource failures shall be structured") forbids.
    """
    error = expect_error(server, frame)
    assert error["code"] != METHOD_NOT_FOUND, server.diagnosis(
        f"resources/read is not served, so {uri!r} was never actually refused: {error!r}"
    )
    assert not (error["code"] == INTERNAL_ERROR and error["message"] == "Internal server error"), (
        server.diagnosis(f"{uri!r} was refused by an unhandled exception, not a mapping: {error!r}")
    )
    return error


def assert_no_declared_bytes(
    server: ServerProcess,
    frame: Mapping[str, Any],
    canaries: Mapping[str, tuple[str, ...]],
) -> None:
    """FR-006/NFR-002: a frame that is not a selected read carries no payload bytes."""
    rendered = frame_json(frame)
    leaked = sorted(
        uri
        for uri, variants in canaries.items()
        if any(variant in rendered for variant in variants)
    )
    assert not leaked, server.diagnosis(f"payload bytes for {leaked} appear in a metadata frame")


def byte_canary(data: bytes) -> tuple[str, ...]:
    """One resource's bytes in every representation a JSON frame could carry them.

    Both wire forms are covered because a payload may legitimately travel either
    way: the JSON-escaped text (for a ``text`` field or an embedded document) and
    the base64 encoding (for a ``blob``). A binary resource has no text form at
    all, so it contributes only the base64 variant — which is exactly why the
    canary cannot simply UTF-8 decode (T6.2 review F6).

    Whole bodies rather than tokens: a metadata frame legitimately carries every
    identifier, digest, and version, so only the complete byte string is evidence
    of a leak.
    """
    variants = [base64.b64encode(data).decode("ascii")]
    with contextlib.suppress(UnicodeDecodeError):
        variants.append(json.dumps(data.decode("utf-8"))[1:-1])
    return tuple(variants)


def byte_canaries(
    facade: McpServiceFacade, catalog: CatalogDescriptor
) -> dict[str, tuple[str, ...]]:
    """A leak canary per declared resource, keyed by canonical URI."""
    return {
        resource.uri: byte_canary(
            facade.resource(
                descriptor.standard_id, descriptor.package_version, resource.resource_id
            ).data
        )
        for descriptor in catalog.standards
        for resource in descriptor.resources
    }


def assert_canonical_uri(uri: str, catalog: CatalogDescriptor) -> None:
    """ADR 0026: one of three forms, canonical, and declared by this catalog.

    Applied to the server's *own* advertised URIs. The grammar is checked
    positionally, exactly as the record describes it — the token after the
    scheme is the standard id, the next is the exact version, and a four-segment
    URI carries the literal ``resources`` separator — because that positional
    reading is what makes the record's disclosed two-segment case resolve to an
    unknown version rather than to a resource.
    """
    assert uri.startswith(SCHEME_PREFIX), f"{uri!r} is not a standards:// URI"
    assert uri == uri.lower(), f"{uri!r} carries uppercase, which ADR 0026 forbids"
    assert "%" not in uri, f"{uri!r} carries percent-encoding beyond RFC 3986 necessity"
    assert not uri.endswith("/"), f"{uri!r} carries a trailing slash"
    assert "?" not in uri and "#" not in uri, f"{uri!r} carries a query or fragment"
    assert ".." not in uri, f"{uri!r} carries a dot segment"
    assert uri == uri.strip() and " " not in uri, f"{uri!r} carries whitespace"

    segments = uri.removeprefix(SCHEME_PREFIX).split("/")
    assert all(segments), f"{uri!r} carries an empty segment"
    if segments[0] == "catalog":
        assert segments == ["catalog", FIXTURE_CATALOG_MAJOR], (
            f"{uri!r} is not the generation-qualified catalog form {CATALOG_URI}"
        )
        return

    assert len(segments) in (2, 4), (
        f"{uri!r} has {len(segments)} segments; ADR 0026 registers only the two-segment "
        "package form and the four-segment resource form"
    )
    if len(segments) == 4:
        assert segments[2] == RESOURCES_SEGMENT, (
            f"{uri!r} is not the four-segment resource form; segment 3 must be "
            f"{RESOURCES_SEGMENT!r}, which is what separates it from the rejected "
            "three-segment index form"
        )
    standard_id, version = segments[0], segments[1]
    declared = {
        (descriptor.standard_id, descriptor.package_version): descriptor
        for descriptor in catalog.standards
    }
    assert version not in MUTABLE_ALIASES, (
        f"{uri!r} names the mutable alias {version!r} in the version slot"
    )
    assert (standard_id, version) in declared, (
        f"{uri!r} names an identity the installed catalog does not declare"
    )
    if len(segments) == 4:
        ids = {resource.resource_id for resource in declared[(standard_id, version)].resources}
        assert segments[3] in ids, (
            f"{uri!r} names a resource {standard_id} {version} never declares"
        )


def refusal_class(error: Mapping[str, Any]) -> tuple[int, frozenset[str]]:
    """The request-independent identity of one refusal.

    The JSON-RPC code plus whichever stable service codes the envelope carries —
    deliberately not the message, and not any identifier echoed from the request,
    because two refusals of the same *class* name different URIs and would never
    compare equal if the URI were part of the identity.
    """
    return int(error["code"]), frozenset(
        code for code in SERVICE_ERROR_CODES if code in frame_json(error)
    )


def spy_calls(server: ServerProcess) -> list[dict[str, Any]]:
    """Every service call the recording facade has reported so far."""
    records: list[dict[str, Any]] = []
    for line in bytes(server.stderr_bytes).decode("utf-8", "replace").splitlines():
        if line.startswith(SPY_PREFIX):
            decoded = json.loads(line.removeprefix(SPY_PREFIX))
            records.append(as_object(decoded, "a recorded service call"))
    return records


def payload_reads(records: Sequence[Mapping[str, Any]]) -> list[tuple[str, ...]]:
    """The argument tuples of every recorded ``resource`` call, in order.

    ``resource`` is the only facade method that touches payload bytes, so this is
    the observable that separates "the adapter served metadata" from "the adapter
    read every payload and threw the bytes away" (NFR-007). Arguments are compared
    as the proxy's ``repr`` strings, which is enough to identify *which* resource
    a call selected without binding the assertion to positional or keyword form.
    """
    selections: list[tuple[str, ...]] = []
    for record in records:
        if record.get("call") != "resource":
            continue
        positional = [str(value) for value in cast("list[object]", record.get("args", []))]
        keyword = cast("dict[str, object]", record.get("kwargs", {}))
        selections.append((*positional, *(str(keyword[key]) for key in sorted(keyword))))
    return selections


def spy_launch(package_root: Path) -> str:
    """A launch script that serves through a facade whose calls are observable."""
    return (
        SPY_LAUNCH_TEMPLATE.replace("__SPY_PREFIX__", SPY_PREFIX)
        .replace("__PACKAGE_ROOT__", str(package_root))
        .replace("__TOOL_RELEASE__", package_version())
        .replace("__CATALOG_MAJOR__", FIXTURE_CATALOG_MAJOR)
    )


# -- RED control ---------------------------------------------------------------


def test_fixture_runtime_harness_serves_the_fixture_catalog(
    full_runtime: Path, grown_family: GeneratedFamily
) -> None:
    """RED control (T6.2): the fixture, oracle, and session machinery are valid.

    Every other test in this file drives the same machinery against a resource
    surface that does not exist yet. This one drives it against surfaces that
    already do — T5's server and T2's facade — so a failure elsewhere is
    provably the absent registration and not a broken fixture distribution.

    It also pins the three properties the rest of the suite depends on: the
    fixture runtime is a *self-contained* installed distribution the eager
    integrity check accepts; the grown distribution differs from the baseline by
    exactly the generated family, which the authoritative loader accepted as
    genuine (so the synthesized digests and manifest are real, not merely
    well-shaped); and that family's binary resource is not valid UTF-8, which is
    what makes the blob-path test meaningful.
    """
    require_mcp_subcommand()

    baseline = oracle_facade(full_runtime).catalog()
    grown = oracle_facade(grown_family.runtime).catalog()
    assert baseline.catalog_major == int(FIXTURE_CATALOG_MAJOR)
    assert expected_package_uris(baseline), "the fixture catalog declares no packages"
    assert set(expected_package_uris(grown)) - set(expected_package_uris(baseline)) == {
        grown_family.package_uri
    }
    assert set(expected_resource_uris(baseline)) < set(expected_resource_uris(grown))
    assert grown_family.standard_id not in {
        descriptor.standard_id for descriptor in baseline.standards
    }, "the generated identity is not novel"

    # The fixture catalog must be the *only* catalog the server can see: a
    # runtime that still resolved the repository's real Catalog 5 would make
    # every exact-membership assertion below meaningless.
    assert {descriptor.standard_id for descriptor in baseline.standards} == {
        "alpha",
        "beta",
        "gamma",
    }

    # The blob fixture must actually be undecodable, or the F6 assertion is vacuous.
    binary = grown_family.resource_bytes[GENERATED_BINARY_RESOURCE]
    with pytest.raises(UnicodeDecodeError):
        binary.decode("utf-8")
    assert (
        oracle_facade(grown_family.runtime)
        .resource(grown_family.standard_id, grown_family.version, GENERATED_BINARY_RESOURCE)
        .data
        == binary
    )

    for era in ERAS:
        with resource_session(era, runtime_root=full_runtime, label="harness-control") as (
            server,
            result,
        ):
            assert result, "the opening contract returned an empty result"
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)


# -- frozen acceptance tests ---------------------------------------------------


def test_resources_module_is_the_planned_registration_surface() -> None:
    """Plan T6 file list: ``mcp_server/resources.py`` is where registration lives.

    Named because the plan names it, and no further internal shape is asserted:
    T6.5 keeps URI parsing in one adapter helper whose spelling no binding
    document freezes, and T5's import-boundary contract already constrains what
    the module may import (no SDK outside ``transport``, no repository authority
    outside ``entrypoint``/``repo_access``).
    """
    require_resources_module()


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_list_and_read_return_exact_metadata_and_bytes(full_runtime: Path, era: Era) -> None:
    """TC-T6-001 (FR-001, FR-002, FR-003, NFR-002): every registered URI is exact.

    All three forms are exercised on one connection: the concrete catalog
    resource, one exact package descriptor per installed version, and every
    declared payload resource. The oracle for each is the facade over the same
    bytes, so "exact" means byte- and field-equal to the service layer rather
    than merely well-formed.

    The listing is checked for *canonicality, uniqueness, and readability* rather
    than for a frozen membership: whether a mapper enumerates every payload
    resource concretely or exposes them through the templates is a design choice
    FR-004 leaves open, but everything it does advertise must be a canonical URI
    of one of the three forms, must appear once (F8), and must read.

    The two metadata forms are compared *structurally* against the §5.5 DTO
    projection, not by substring presence (T6.2 review F2). Substring-over-frame
    is an evasion oracle: concatenated garbage containing every expected token
    passes it, ids and versions can match merely because they appear in the
    response URI, and whole DTO fields — capabilities, relationships, providers —
    can be missing while it still passes. Recursive equality against
    ``model_dump(mode="json")`` is the only oracle that means "one exact
    ``StandardDescriptor``" (plan:389).
    """
    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    resources = declared_resources(catalog)

    with resource_session(era, runtime_root=full_runtime, label="list-read") as (server, _):
        listing = list_resources(server, era)
        advertised = listed_uris(listing)
        assert CATALOG_URI in advertised, (
            f"the concrete catalog resource {CATALOG_URI} is not listed: {advertised}"
        )
        assert len(advertised) == len(set(advertised)), (
            f"resources/list advertises a duplicate registration: {sorted(advertised)}"
        )
        for uri in advertised:
            assert (
                uri == CATALOG_URI or uri in resources or uri in expected_package_uris(catalog)
            ), f"resources/list advertises {uri!r}, which is not a declared catalog identity"

        # Form 1: the compact, generation-qualified catalog projection, exactly.
        served_catalog = metadata_document(server, era, CATALOG_URI)
        assert served_catalog == catalog_projection(catalog), (
            f"{CATALOG_URI} does not serve the exact FR-001 catalog projection"
        )
        # Compactness is the other half of FR-001's contract, and it is a *negative*
        # claim the structural equality above cannot make on its own: the discovery
        # resource must not carry the payload digests or provider declarations that
        # belong to the package resource one read away.
        rendered_catalog = json.dumps(served_catalog)
        for descriptor in catalog.standards:
            for resource in descriptor.resources:
                assert resource.digest not in rendered_catalog, (
                    f"the catalog resource carries the digest of {resource.uri}; digests "
                    "belong to the package resource, not the discovery point"
                )
            for provider in descriptor.providers:
                assert provider.provider_id not in rendered_catalog, (
                    f"the catalog resource carries provider {provider.provider_id!r} of "
                    f"{package_uri(descriptor)}; providers belong to the package resource"
                )

        # Form 2: one exact StandardDescriptor per installed version.
        for descriptor in catalog.standards:
            assert metadata_document(server, era, package_uri(descriptor)) == dto_projection(
                descriptor
            ), f"{package_uri(descriptor)} does not serve the exact StandardDescriptor projection"

        # Form 3: declared bytes and declared media type, and nothing invented.
        for uri, resource in resources.items():
            entry = read_one(server, era, uri)
            expected = facade.resource(
                resource.standard_id, resource.package_version, resource.resource_id
            )
            assert content_bytes(server, entry) == expected.data, (
                f"{uri} returned bytes that differ from the digest-verified payload"
            )
            assert entry.get("mimeType") == resource.media_type, (
                f"{uri} returned media type {entry.get('mimeType')!r}, "
                f"declared {resource.media_type!r}"
            )

        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_resource_templates_expose_the_two_parameterized_forms(
    full_runtime: Path, era: Era
) -> None:
    """FR-004/IR-002: the two parameterized forms are registered, verbatim.

    Frozen literally because ADR 0026's stop/backtrack condition is explicit:
    if the SDK cannot express these templates without changing their identity,
    T6 returns to T1 rather than registering an alternate URI shape. The catalog
    resource is deliberately absent from this set — with the catalog generation
    fixed by ``models.CATALOG_MAJOR`` it is a concrete resource, not a
    parameterized one.

    Template expansion is then proven the only way it can be proven from a
    client: every declared identity of the fixture distribution resolves through
    the expanded form, with no per-package registration anywhere in the surface.
    """
    catalog = oracle_facade(full_runtime).catalog()

    with resource_session(era, runtime_root=full_runtime, label="templates") as (server, _):
        templates = template_strings(list_templates(server, era))
        assert set(templates) == FROZEN_TEMPLATES, (
            f"the registered templates must be exactly {sorted(FROZEN_TEMPLATES)}, got {templates}"
        )
        assert len(templates) == len(set(templates)), f"a template is registered twice: {templates}"

        for descriptor in catalog.standards:
            expanded = PACKAGE_TEMPLATE.format(
                standard_id=descriptor.standard_id, version=descriptor.package_version
            )
            read_one(server, era, expanded)
            for resource in descriptor.resources:
                assert resource.uri == RESOURCE_TEMPLATE.format(
                    standard_id=descriptor.standard_id,
                    version=descriptor.package_version,
                    resource_id=resource.resource_id,
                ), f"{resource.uri} is not an expansion of the frozen template"
                read_one(server, era, resource.uri)

        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_fixture_package_growth_changes_resources_not_tools(
    full_runtime: Path, grown_family: GeneratedFamily
) -> None:
    """TC-T6-002 (FR-004, FR-021, NFR-001, NFR-007): data grows, the surface does not.

    Two servers over two distributions that differ by exactly one family, whose
    identity — standard id, version, and two resource ids — is generated per
    session and appears nowhere in the baseline fixture (T6.2 review F5). That is
    the whole point: a predictable growth target (removing and restoring a known
    family) is satisfiable by an adapter carrying explicit per-package branches,
    which is exactly what FR-004's data-driven expansion rule and T6's stop
    against per-package handlers forbid. Nothing here may name the identity.

    What must change is the *served resource surface* — the listing and the
    catalog resource's own projection. What must not change is the tool surface or
    the template set: NFR-001 states that adding a standard shall not require
    adding a top-level MCP tool, and FR-004 states that a new payload appears
    "through the same templates, without server code or tool-list changes".

    The resource-surface comparison deliberately spans both the listing and the
    catalog resource rather than the listing alone, because whether concrete
    payload URIs are enumerated or reached through templates is a design choice
    FR-004 leaves open — and under either choice a grown distribution must become
    visible to a client that only lists and reads.

    Both distributions are also held to the F2 structural-metadata contract, so
    the catalog projection is exact on each side rather than merely different
    between them.

    v1 does not watch a running process for installation changes (FR-004), so
    growth is observed as two server instances, never as a live reload.
    """
    era = MODERN_ERA
    baseline = oracle_facade(full_runtime).catalog()
    grown = oracle_facade(grown_family.runtime).catalog()
    novel_resources = sorted(
        set(expected_resource_uris(grown)) - set(expected_resource_uris(baseline))
    )
    assert len(novel_resources) == len(grown_family.resource_bytes), (
        "the generated family's resources are not all novel"
    )

    surfaces: dict[str, tuple[str, str, str]] = {}
    for label, runtime, catalog in (
        ("baseline", full_runtime, baseline),
        ("grown", grown_family.runtime, grown),
    ):
        with resource_session(era, runtime_root=runtime, label=f"growth-{label}") as (
            server,
            result,
        ):
            capabilities = declared_capabilities(result)
            listing = json.dumps(sorted(listed_uris(list_resources(server, era))))
            templates = json.dumps(sorted(template_strings(list_templates(server, era))))
            projection = metadata_document(server, era, CATALOG_URI)
            assert projection == catalog_projection(catalog), (
                f"the {label} distribution does not serve its exact catalog projection"
            )
            surfaces[label] = (
                json.dumps([listing, projection], sort_keys=True),
                templates,
                tool_surface(server, era, capabilities),
            )

            if label == "baseline":
                # The generated family must be absent, not merely unlisted: a
                # server that served an unadvertised package would make the
                # catalog projection non-authoritative (FR-027).
                for uri in (grown_family.package_uri, *novel_resources):
                    assert_structured_refusal(server, read_frame(server, era, uri), uri=uri)
            else:
                # ... and present through the *unchanged* templates, with exact
                # metadata and exact bytes, without any per-package registration.
                assert metadata_document(server, era, grown_family.package_uri) == dto_projection(
                    next(
                        descriptor
                        for descriptor in grown.standards
                        if descriptor.standard_id == grown_family.standard_id
                    )
                )
                for resource_id, data in grown_family.resource_bytes.items():
                    expanded = RESOURCE_TEMPLATE.format(
                        standard_id=grown_family.standard_id,
                        version=grown_family.version,
                        resource_id=resource_id,
                    )
                    assert expanded in novel_resources, (
                        f"{expanded} is not one of the catalog's newly declared resources"
                    )
                    assert content_bytes(server, read_one(server, era, expanded)) == data

            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)

    assert surfaces["baseline"][0] != surfaces["grown"][0], (
        "growing the installed distribution left the served resource surface unchanged"
    )
    assert surfaces["baseline"][1] == surfaces["grown"][1], (
        "growing the installed distribution changed the registered template set"
    )
    assert surfaces["baseline"][2] == surfaces["grown"][2], (
        "growing the installed distribution changed the tool surface"
    )


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_binary_resource_reads_as_base64_with_its_declared_media_type(
    grown_family: GeneratedFamily, era: Era
) -> None:
    """FR-003 (T6.2 review F6): exact declared bytes, including bytes that are not text.

    Every baseline fixture resource is UTF-8, so an implementation that decodes
    payloads as text passes the rest of the suite and then fails on a legitimate
    binary declared resource. The generated family carries one whose bytes cover
    every value 0-255, so it has no text representation at all: the protocol must
    use base64 ``blob``, that blob must decode to the facade's digest-verified
    bytes exactly, and the declared media type must survive.

    ``text`` is asserted absent because a contents entry carrying both would be
    ambiguous about which is authoritative, and any text form of these bytes is
    lossy by construction.
    """
    facade = oracle_facade(grown_family.runtime)
    expected = facade.resource(
        grown_family.standard_id, grown_family.version, GENERATED_BINARY_RESOURCE
    )

    with resource_session(era, runtime_root=grown_family.runtime, label="blob") as (server, _):
        entry = read_one(server, era, grown_family.binary_uri)
        blob = entry.get("blob")
        assert isinstance(blob, str), server.diagnosis(
            f"a non-UTF-8 resource must travel as a base64 blob, got {sorted(entry)}"
        )
        assert entry.get("text") is None, server.diagnosis(
            f"a contents entry carries both text and blob for {grown_family.binary_uri}"
        )
        assert base64.b64decode(blob, validate=True) == expected.data
        assert expected.data == GENERATED_BINARY_BYTES
        assert (
            entry.get("mimeType") == expected.descriptor.media_type == (GENERATED_BINARY_MEDIA_TYPE)
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_invalid_distribution_fails_startup_and_changed_bytes_fail_read(
    mutable_runtime: Path,
) -> None:
    """TC-T6-003 (FR-006, FR-027): fail closed at startup, and again on every read.

    Both halves of the plan's stop/backtrack condition, in one test because they
    are one claim about *when* integrity is established:

    First, "any invalid family or payload at construction is a server-start
    failure, never a partial resource list". The corrupted byte is deliberately
    one no URI in this suite ever reads — a declared artifact source rather than
    a declared resource — so a server that verified only what a session selects
    would still start and serve a partial catalog. It must instead answer
    nothing at all.

    Second, "each read rechecks the selected declaration, contained path, and
    current byte digest after startup validation". A payload changed *after* a
    successful start must fail its own read while every other resource keeps
    reading and the registration set stays static, because ADR 0026 fixes the
    registration sets for the process lifetime: the failure is a refusal, not a
    server that degrades or re-lists.

    Post-startup drift is also the one refusal class that *provably* originates in
    the service layer — only ``McpServiceFacade.resource`` rechecks the digest,
    and no registration-time index can predict it — so it is the one place this
    suite requires a stable service code to survive onto the wire (NFR-004:
    "error includes code, message, affected path/standard, severity when
    applicable, and remediation"). Every other refusal class may legitimately be
    answered by the adapter from its own registration index, because the plan
    requires undeclared identifiers to be rejected *before* service lookup; those
    codes are the adapter's own and no binding document spells them.
    """
    era = MODERN_ERA
    facade = oracle_facade(mutable_runtime)
    package = mutable_runtime / "project_standards"
    payload_file = package / INTEGRITY_PAYLOAD_FILE
    expected = facade.resource(INTEGRITY_STANDARD, INTEGRITY_VERSION, INTEGRITY_RESOURCE)
    original = payload_file.read_bytes()
    assert original == expected.data, (
        f"{INTEGRITY_PAYLOAD_FILE} is not the payload behind {expected.descriptor.uri}; "
        "the fixture layout this test names has changed"
    )
    untouched = next(
        resource
        for resource in facade.standard(INTEGRITY_STANDARD, INTEGRITY_VERSION).resources
        if resource.resource_id != INTEGRITY_RESOURCE
    )

    with resource_session(era, runtime_root=mutable_runtime, label="integrity") as (server, _):
        assert content_bytes(server, read_one(server, era, expected.descriptor.uri)) == original
        before = json.dumps(sorted(listed_uris(list_resources(server, era))))

        payload_file.write_bytes(original + b"\ndrifted after startup\n")
        refusal = assert_structured_refusal(
            server, read_frame(server, era, expected.descriptor.uri), uri=expected.descriptor.uri
        )
        assert_no_declared_bytes(server, refusal, {expected.descriptor.uri: byte_canary(original)})
        assert "resource-integrity" in frame_json(refusal), server.diagnosis(
            f"a post-startup digest mismatch dropped its stable service code: {refusal!r}"
        )
        # A server fault, not a bad request: the client asked for a resource this
        # server advertises and the distribution failed underneath it. The class is
        # revision-stable, unlike not-found (see
        # test_refusal_codes_follow_the_negotiated_revision).
        assert refusal["code"] == INTERNAL_ERROR, server.diagnosis(
            f"a digest mismatch answered {refusal['code']}, not an internal fault"
        )

        # The refusal is scoped to the drifted resource: the rest of the exact
        # catalog is still authoritative and still served.
        assert (
            content_bytes(server, read_one(server, era, untouched.uri))
            == facade.resource(INTEGRITY_STANDARD, INTEGRITY_VERSION, untouched.resource_id).data
        )
        assert json.dumps(sorted(listed_uris(list_resources(server, era)))) == before, (
            "a failed read changed the registered resource set, which ADR 0026 fixes at start"
        )

        payload_file.write_bytes(original)
        assert content_bytes(server, read_one(server, era, expected.descriptor.uri)) == original
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    # Startup half: corrupt a payload byte nothing addresses, then prove the
    # process dies on its own before serving anything.
    unread = package / UNREAD_PAYLOAD_BYTE_TARGET
    unread.write_bytes(unread.read_bytes() + b"\ntampered\n")
    with pytest.raises(ServiceError):
        oracle_facade(mutable_runtime)

    with ServerProcess(CLI_LAUNCH, runtime_root=mutable_runtime, label="integrity-startup") as bad:
        # No protocol frame is sent and stdin is not closed (T6.2 review F4).
        # Sending a request first would make this indistinguishable from a server
        # that entered stdio, validated lazily on the first request, and exited:
        # both end with a non-zero code and an empty stdout. The discriminating
        # observation is that the process terminates *unprompted*, which is what
        # "the check completes before stdio starts" means.
        started = time.monotonic()
        bad.drain(STARTUP_DEADLINE)
        elapsed = time.monotonic() - started
        assert elapsed < STARTUP_DEADLINE, bad.diagnosis(
            f"a corrupted distribution was still serving after {STARTUP_DEADLINE:.0f}s with no "
            "request sent, so its integrity check did not precede stdio"
        )
        exit_code = bad.finish()
        assert exit_code != 0, bad.diagnosis("a corrupted distribution still started stdio")
        assert bytes(bad.stdout_bytes) == b"", bad.diagnosis(
            "a corrupted distribution wrote to the protocol channel, so the list was partial"
        )
        assert bytes(bad.stderr_bytes), bad.diagnosis(
            "a refused startup produced no diagnostic on stderr"
        )


def test_uri_contract_is_generation_version_qualified_and_deterministic(
    full_runtime: Path, duplicate_runtime: Path
) -> None:
    """TC-T6-004 (NFR-005, IR-002): one grammar, one order, no hidden inputs.

    Three independent claims:

    *Qualified* — every advertised URI is one of ADR 0026's three forms, the
    catalog form names the generation explicitly, and every package form names
    an exact declared version rather than a catalog role. A role in the version
    slot is the mutable alias FR-027 exists to refuse.

    *Canonical* — lower case, no trailing slash, no percent-encoding, no query
    or fragment, no dot segments. Asserted on the server's own output, because a
    server that advertises a URI it would itself reject is unusable regardless
    of how well it validates input.

    *Deterministic* — the served order and content are a function of the
    installed catalog and of nothing else. Two independently built,
    byte-equivalent distributions at different filesystem paths must produce
    identical listings, identical templates, and identical catalog bytes, in
    both eras and across repeated processes. That also catches the DR-009
    violation this surface is most prone to: an absolute payload path leaking
    into a served frame.
    """
    catalog = oracle_facade(full_runtime).catalog()
    assert oracle_facade(duplicate_runtime).catalog() == catalog, (
        "the duplicate fixture runtime is not byte-equivalent, so it cannot test determinism"
    )

    observed: dict[str, tuple[str, str, str]] = {}
    for label, runtime in (
        ("full-a", full_runtime),
        ("full-b", full_runtime),
        ("duplicate", duplicate_runtime),
    ):
        for era in ERAS:
            with resource_session(era, runtime_root=runtime, label=f"determinism-{label}") as (
                server,
                _,
            ):
                listing = list_resources(server, era)
                uris = listed_uris(listing)
                for uri in uris:
                    assert_canonical_uri(uri, catalog)
                templates = template_strings(list_templates(server, era))
                catalog_entry = read_one(server, era, CATALOG_URI)

                # DR-009: paths in stable results are root-relative, so no frame
                # may carry the distribution's own location.
                for frame in (
                    json.dumps(listing),
                    json.dumps(templates),
                    frame_json(catalog_entry),
                ):
                    assert str(runtime) not in frame, server.diagnosis(
                        "an absolute distribution path leaked into a served frame"
                    )

                observed[f"{label}-{era.name}"] = (
                    json.dumps(uris),
                    json.dumps(templates),
                    frame_json(catalog_entry),
                )
                assert server.finish() == 0
                assert_stdout_is_protocol_only(server)

    first = observed["full-a-classic"]
    varied = sorted(key for key, value in observed.items() if value != first)
    assert not varied, (
        "the resource listing, template set, or catalog bytes varied by process, era, or "
        f"distribution path: {varied}"
    )


def test_resource_descriptor_preserves_declared_fields(full_runtime: Path) -> None:
    """TC-T6-005 (DR-002): every declared descriptor field survives the projection.

    DR-002 enumerates the exposed fields — URI, declared resource ID, role,
    media type, digest, standard ID, and exact package version — and the §5.5
    ``ResourceDescriptor`` is where they already live. So the oracle is the
    facade's descriptor, field by field, and the protocol surface must preserve
    every one of them.

    *Where* each field lands is deliberately not asserted. No binding document
    freezes the placement, and the SDK's ``Resource``/``ResourceContents`` types
    have named slots for only two of the seven (``uri``, ``mimeType``); the rest
    must ride in ``_meta`` or in a serialized metadata document, which is the
    mapper's choice. The two the protocol does name are pinned exactly; the
    others must be recoverable from the resource's own protocol surface — its
    listing entry, if it is listed, together with its read result.
    """
    era = MODERN_ERA
    catalog = oracle_facade(full_runtime).catalog()
    resources = declared_resources(catalog)

    with resource_session(era, runtime_root=full_runtime, label="descriptor") as (server, _):
        entries = list_resources(server, era)
        listing = dict(zip(listed_uris(entries), entries, strict=True))
        for uri, descriptor in resources.items():
            entry = read_one(server, era, uri)
            assert entry.get("uri") == descriptor.uri
            assert entry.get("mimeType") == descriptor.media_type, (
                f"{uri} projects media type {entry.get('mimeType')!r}, "
                f"declared {descriptor.media_type!r}"
            )
            surface = frame_json(entry) + frame_json(listing.get(uri, {}))
            missing = [
                f"{field}={value!r}"
                for field, value in (
                    ("uri", descriptor.uri),
                    ("resource_id", descriptor.resource_id),
                    ("role", descriptor.role),
                    ("media_type", descriptor.media_type),
                    ("digest", descriptor.digest),
                    ("standard_id", descriptor.standard_id),
                    ("package_version", descriptor.package_version),
                )
                if value not in surface
            ]
            assert not missing, server.diagnosis(
                f"the protocol surface for {uri} drops declared descriptor fields: {missing}"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


# -- URI grammar refusals ------------------------------------------------------

# Every refusal class ADR 0026 and FR-006 name, against the fixture catalog.
# `alpha` `2.0` `readme` is declared, so each entry differs from a *serveable*
# URI only by the property under test: that is what makes a passing read a
# provable fuzzy match rather than an unrelated success.
REFUSED_URIS: tuple[tuple[str, str], ...] = (
    ("empty", ""),
    ("scheme-only", "standards://"),
    ("scheme-without-authority", "standards:/alpha/2.0"),
    ("uppercase-scheme", "STANDARDS://alpha/2.0"),
    ("foreign-scheme", "file:///etc/passwd"),
    ("not-a-uri", "alpha/2.0/resources/readme"),
    ("leading-whitespace", " standards://catalog/5"),
    ("catalog-generation-omitted", "standards://catalog"),
    ("catalog-generation-empty", "standards://catalog/"),
    ("catalog-trailing-slash", "standards://catalog/5/"),
    ("catalog-uppercase", "standards://CATALOG/5"),
    ("catalog-undeclared-generation", "standards://catalog/6"),
    ("catalog-non-canonical-generation", "standards://catalog/05"),
    ("catalog-as-package", "standards://catalog/5/resources/readme"),
    ("version-omitted", "standards://alpha"),
    ("version-empty", "standards://alpha/"),
    ("package-trailing-slash", "standards://alpha/2.0/"),
    ("uppercase-standard-id", "standards://ALPHA/2.0"),
    ("uppercase-resource-id", "standards://alpha/2.0/resources/README"),
    ("uppercase-separator", "standards://alpha/2.0/RESOURCES/readme"),
    ("resource-trailing-slash", "standards://alpha/2.0/resources/readme/"),
    ("three-segment-index-form", "standards://alpha/2.0/readme"),
    ("two-segment-unversioned-form", "standards://alpha/readme"),
    ("mutable-alias-version", "standards://alpha/latest/resources/readme"),
    ("mutable-alias-package", "standards://alpha/default"),
    ("percent-encoded-resource-id", "standards://alpha/2.0/resources/read%6de"),
    ("percent-encoded-version", "standards://alpha/2%2E0/resources/readme"),
    ("percent-encoded-separator", "standards://alpha/2.0%2Fresources%2Freadme"),
    ("traversal-in-version", "standards://alpha/../beta/1.0"),
    ("traversal-in-resource-id", "standards://alpha/2.0/resources/../../../etc/passwd"),
    ("traversal-back-to-declared", "standards://alpha/2.0/resources/../../2.0/resources/readme"),
    ("encoded-traversal", "standards://alpha/2.0/resources/%2e%2e%2fREADME.md"),
    ("absolute-path-resource-id", "standards://alpha/2.0/resources//etc/passwd"),
    ("declared-path-as-resource-id", "standards://alpha/2.0/resources/README.md"),
    ("query-appended", "standards://alpha/2.0/resources/readme?raw=1"),
    ("fragment-appended", "standards://alpha/2.0/resources/readme#top"),
    ("separator-missing-resource-id", "standards://alpha/2.0/resources"),
    ("separator-empty-resource-id", "standards://alpha/2.0/resources/"),
    ("undeclared-standard", "standards://delta/1.0"),
    ("undeclared-version", "standards://alpha/9.9/resources/readme"),
    ("undeclared-resource", "standards://alpha/2.0/resources/nope"),
    ("undeclared-resource-of-other-version", "standards://alpha/1.0/resources/provider-code"),
)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_non_canonical_and_undeclared_uris_are_refused_without_bytes(
    full_runtime: Path, era: Era
) -> None:
    """FR-006/FR-027 + ADR 0026: strict canonicalization, and no fuzzy recovery.

    Every entry in ``REFUSED_URIS`` differs from a URI this server *does* serve
    only by the property under test, so a success is proof of the recovery
    behaviour the record forbids: fuzzy matching, nearest-version resolution, or
    case-insensitive lookup. Two entries are the record's disclosed producer
    divergences — the three-segment index form and the two-segment unversioned
    form — and they are refused here for the same reason as the rest.

    Every refusal must also be *empty of resource bytes* (FR-006), including the
    entries a lenient server would have resolved to a real declared payload. The
    canaries cover every declared resource in the catalog rather than just the
    one each URI aims at, so an error body that echoed some other file fails too.

    One connection serves the whole table: refusals must not poison the wire, so
    the session ends with a successful read and a protocol-clean transcript.
    """
    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    canaries = byte_canaries(facade, catalog)
    control = f"standards://{INTEGRITY_STANDARD}/{INTEGRITY_VERSION}/resources/{INTEGRITY_RESOURCE}"
    assert control in canaries, "the control URI is not a declared fixture resource"

    with resource_session(era, runtime_root=full_runtime, label="refusals") as (server, _):
        for label, uri in REFUSED_URIS:
            frame = read_frame(server, era, uri)
            assert "result" not in frame, server.diagnosis(
                f"{label}: {uri!r} was served instead of refused; ADR 0026 forbids fuzzy "
                f"matching, nearest-version resolution, and case-insensitive recovery: {frame!r}"
            )
            refusal = assert_structured_refusal(server, frame, uri=uri)
            assert_no_declared_bytes(server, refusal, canaries)

        # The connection survived every refusal and still serves exact bytes.
        assert (
            content_bytes(server, read_one(server, era, control))
            == facade.resource(INTEGRITY_STANDARD, INTEGRITY_VERSION, INTEGRITY_RESOURCE).data
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_two_segment_form_fails_as_an_unknown_version(full_runtime: Path) -> None:
    """ADR 0026 disclosed divergence: the two-segment form is parsed positionally.

    ``render_catalog`` is exported and CLI-reachable and emits
    ``standards://{standard_id}/{resource_id}``. The record disposes of it
    exactly: under the frozen grammar that URI parses positionally as form 2, so
    the resource id lands in the version slot and the read "fails with a
    structured unknown-version not-found error: the form is rejected, never
    silently served as something else".

    Both halves of that sentence are asserted. Rejection is covered by the
    refusal table; what this adds is the *class*: the two-segment form must fail
    like an unknown version, not like a syntax error and not like a resource
    lookup. Compared by refusal class rather than by message, because the class
    is the contract and the wording is not.
    """
    era = MODERN_ERA
    with resource_session(era, runtime_root=full_runtime, label="two-segment") as (server, _):
        positional = assert_structured_refusal(
            server,
            read_frame(server, era, f"standards://{INTEGRITY_STANDARD}/{INTEGRITY_RESOURCE}"),
            uri="two-segment form",
        )
        unknown_version = assert_structured_refusal(
            server,
            read_frame(server, era, f"standards://{INTEGRITY_STANDARD}/9.9"),
            uri="unknown version",
        )
        assert refusal_class(positional) == refusal_class(unknown_version), (
            "the two-segment form must fail as an unknown version, not as its own class: "
            f"{positional!r} vs {unknown_version!r}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_refusal_codes_follow_the_negotiated_revision(full_runtime: Path, era: Era) -> None:
    """NFR-004 + the client matrix: the not-found code is revision-dependent.

    Resource-not-found was ``-32002`` through revision 2025-11-25 and became
    ``INVALID_PARAMS`` at 2026-07-28. The SDK serves both eras from one server and
    never rewrites a code the adapter chose, so emitting the modern value to a
    2025-06-18 client would report a failure that revision does not define — and
    the installed Codex CLI speaks 2025-06-18 only (T6.4 Codex GREEN review, F2).

    The two revision-*stable* classes are asserted in the same breath, because
    "this one varies" is only meaningful beside "these do not": a URI that is not
    canonical is a bad parameter in every revision, since no revision defines a
    resource whose name it could be; and a digest mismatch is a server fault in
    every revision, because nothing the client sent was wrong.
    """
    expected_not_found = INVALID_PARAMS if era.modern else LEGACY_RESOURCE_NOT_FOUND

    with resource_session(era, runtime_root=full_runtime, label="refusal-codes") as (server, _):
        # Canonical URIs naming things the installed catalog does not declare.
        for uri in (
            f"{SCHEME_PREFIX}catalog/6",
            f"{SCHEME_PREFIX}delta/1.0",
            f"{SCHEME_PREFIX}{INTEGRITY_STANDARD}/9.9",
            f"{SCHEME_PREFIX}{INTEGRITY_STANDARD}/{INTEGRITY_VERSION}/resources/nope",
        ):
            error = assert_structured_refusal(server, read_frame(server, era, uri), uri=uri)
            assert error["code"] == expected_not_found, server.diagnosis(
                f"{uri} answered {error['code']} on a {era.revision} connection; a canonical "
                f"undeclared identity must answer {expected_not_found}"
            )

        # Non-canonical URIs: a bad parameter in every revision.
        for uri in (
            f"{CATALOG_URI}/",
            f"{SCHEME_PREFIX}{INTEGRITY_STANDARD.upper()}/{INTEGRITY_VERSION}",
            f"{SCHEME_PREFIX}{INTEGRITY_STANDARD}/{INTEGRITY_VERSION}/{INTEGRITY_RESOURCE}",
            "not-a-standards-uri",
        ):
            error = assert_structured_refusal(server, read_frame(server, era, uri), uri=uri)
            assert error["code"] == INVALID_PARAMS, server.diagnosis(
                f"{uri} answered {error['code']} on a {era.revision} connection; a "
                f"non-canonical URI must answer {INVALID_PARAMS} in every revision"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_uri_rejection_precedes_any_service_lookup(full_runtime: Path, era: Era) -> None:
    """Plan T6: "URI parsing must reject ... before service lookup".

    Ordering is not observable from the wire — a refusal looks the same whether
    the adapter parsed first or asked the facade first — so the facade itself is
    the instrument. The launch script wraps the real facade in a proxy that
    reports every call on stderr, then serves through the same
    ``transport.create_server``/``run_stdio`` pair the CLI uses. A rejected URI
    must add no service call at all; a canonical one must add some.

    This is the only test that bypasses the CLI entry point, and it bypasses it
    for exactly one reason: to make the service boundary observable. Everything
    it asserts about the protocol still travels the real adapter.
    """
    package_root = full_runtime / "project_standards"
    with resource_session(
        era,
        runtime_root=full_runtime,
        label="lookup-order",
        script=spy_launch(package_root),
    ) as (server, _):
        # Let any registration-time facade calls happen and settle first, so the
        # comparison below is about the read path only.
        list_resources(server, era)
        list_templates(server, era)
        server.drain(QUIET_WINDOW)
        before = spy_calls(server)

        for label, uri in REFUSED_URIS:
            frame = read_frame(server, era, uri)
            assert "error" in frame, server.diagnosis(f"{label}: {uri!r} was served, not refused")
        server.drain(QUIET_WINDOW)
        assert spy_calls(server) == before, server.diagnosis(
            "a non-canonical or undeclared URI reached the service layer; parsing must "
            f"reject it first. New calls: {spy_calls(server)[len(before) :]}"
        )

        control = (
            f"standards://{INTEGRITY_STANDARD}/{INTEGRITY_VERSION}/resources/{INTEGRITY_RESOURCE}"
        )
        read_one(server, era, control)
        server.drain(QUIET_WINDOW)
        assert len(spy_calls(server)) > len(before), server.diagnosis(
            "a canonical read reached no service call, so the spy proves nothing about ordering"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


# -- lazy reads, relations, and the T5 capability contract ---------------------


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_payload_bytes_enter_context_only_on_a_selected_read(full_runtime: Path, era: Era) -> None:
    """FR-003/NFR-002: metadata is compact; bytes arrive only when selected.

    "Lazy" in the plan means precisely this: payload bytes enter MCP and model
    context only on a selected read. So no listing, no template set, no catalog
    resource, and no package descriptor may carry a payload body — an agent must
    be able to resolve which standard it needs without any README text entering
    context (NFR-002's own verification criterion).

    The eager half of the same sentence — that laziness never defers the
    full-distribution startup integrity check — is
    ``test_invalid_distribution_fails_startup_and_changed_bytes_fail_read``,
    which corrupts a payload byte no URI in this suite ever reads.
    """
    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    canaries = byte_canaries(facade, catalog)

    with resource_session(era, runtime_root=full_runtime, label="lazy") as (server, _):
        assert_no_declared_bytes(server, {"resources": list_resources(server, era)}, canaries)
        assert_no_declared_bytes(
            server, {"resourceTemplates": list_templates(server, era)}, canaries
        )
        assert_no_declared_bytes(server, read_one(server, era, CATALOG_URI), canaries)
        for descriptor in catalog.standards:
            assert_no_declared_bytes(
                server, read_one(server, era, package_uri(descriptor)), canaries
            )

        # ... and a selected read delivers exactly the bytes the metadata withheld.
        for descriptor in catalog.standards:
            for resource in descriptor.resources:
                entry = read_one(server, era, resource.uri)
                assert (
                    content_bytes(server, entry)
                    == facade.resource(
                        descriptor.standard_id, descriptor.package_version, resource.resource_id
                    ).data
                ), f"the selected read of {resource.uri} did not deliver the declared bytes"
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_metadata_requests_never_read_payload_bytes_through_the_facade(
    full_runtime: Path, era: Era
) -> None:
    """NFR-007 (T6.2 review F7): laziness is internal, not just a clean response.

    Checking the response boundary alone is insufficient: an implementation may
    call ``facade.resource`` for every declared payload while answering
    ``resources/list`` or the catalog resource, verify and discard the bytes, and
    still emit a byte-free frame. That is a full-distribution read on every
    metadata request, which is precisely what NFR-007 rules out ("index/manifest
    reads are cached within process; repo scans are explicit and bounded").

    Scope, per the arbitrated amendment: the eager *startup* integrity check is
    legitimate and out of scope — it runs inside ``from_installed``, before the
    proxy exists, and TC-T6-003 requires it. What is asserted is that once the
    session is open, list/templates/catalog/package requests select no payload at
    all, and a selected payload read selects exactly its own one.
    """
    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    selected = next(
        resource for descriptor in catalog.standards for resource in descriptor.resources
    )

    with resource_session(
        era,
        runtime_root=full_runtime,
        label="lazy-service-calls",
        script=spy_launch(full_runtime / "project_standards"),
    ) as (server, _):
        server.drain(QUIET_WINDOW)
        baseline = payload_reads(spy_calls(server))

        list_resources(server, era)
        list_templates(server, era)
        read_one(server, era, CATALOG_URI)
        for descriptor in catalog.standards:
            read_one(server, era, package_uri(descriptor))
        server.drain(QUIET_WINDOW)
        assert payload_reads(spy_calls(server)) == baseline, server.diagnosis(
            "a metadata request read payload bytes through the facade; new selections: "
            f"{payload_reads(spy_calls(server))[len(baseline) :]}"
        )

        read_one(server, era, selected.uri)
        server.drain(QUIET_WINDOW)
        added = payload_reads(spy_calls(server))[len(baseline) :]
        assert len(added) == 1, server.diagnosis(
            f"one selected read produced {len(added)} payload selections: {added}"
        )
        for identifier in (
            selected.standard_id,
            selected.package_version,
            selected.resource_id,
        ):
            assert any(identifier in value for value in added[0]), server.diagnosis(
                f"the selected read did not select {identifier!r}: {added[0]}"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_declared_relationships_survive_the_protocol_projection(full_runtime: Path) -> None:
    """FR-021/DR-006: each relation kind is projected exactly, and never invented.

    "Results distinguish companions, extensions, and conflicts exactly as V2
    declarations encode them; empty relations remain independent." Distinguishing
    is asserted **per bucket** (T6.2 review F3): comparing only the union lets a
    mapper swap ``companions`` with ``extends``, or dump the whole union into one
    bucket and emit empty placeholders for the others, while still passing.

    Empty buckets are asserted too, and for every package rather than only the
    related ones — an independent package that acquired a companion through the
    projection is the hidden dependency FR-021 exists to prevent, and §5.5 makes
    the empty tuple the declared default rather than an absent field.

    The bucket names are the ``RelationshipSet`` field names because §5.5 freezes
    them; the values come from the DTO, so nothing here is hand-written.
    """
    era = MODERN_ERA
    catalog = oracle_facade(full_runtime).catalog()
    related = [
        descriptor
        for descriptor in catalog.standards
        if descriptor.relationships != RelationshipSet()
    ]
    assert related, "the fixture catalog declares no relations, so this test proves nothing"
    assert len(related) < len(catalog.standards), (
        "every fixture package declares relations, so the independent-package half is untested"
    )

    with resource_session(era, runtime_root=full_runtime, label="relations") as (server, _):
        for descriptor in catalog.standards:
            document = metadata_document(server, era, package_uri(descriptor))
            projected = as_object(
                document.get("relationships"),
                f"the relationships object of {package_uri(descriptor)}",
            )
            for bucket in ("companions", "extends", "conflicts"):
                expected = list(cast("tuple[str, ...]", getattr(descriptor.relationships, bucket)))
                assert projected.get(bucket) == expected, server.diagnosis(
                    f"{package_uri(descriptor)} projects {bucket}={projected.get(bucket)!r}, "
                    f"declared {expected!r}"
                )
            assert set(projected) == {"companions", "extends", "conflicts"}, server.diagnosis(
                f"{package_uri(descriptor)} projects unexpected relation buckets: {sorted(projected)}"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_resource_registrations_satisfy_the_transport_capability_contract(
    full_runtime: Path, era: Era
) -> None:
    """FR-025/IR-008/DR-007: T6 flips the resources capability and nothing else.

    T5 asserts an *equivalence* between declared capabilities and reachable
    registrations rather than an emptiness, precisely so that T6 can register
    resources without weakening it. This test drives T5's own helpers against the
    T6 server to prove that forward compatibility actually held: resources
    become declared and reachable, prompts and tools keep whatever T7/T8 give
    them, ``listChanged`` stays false, ``subscribe`` stays absent, and no write
    or non-frozen tool appears.

    Registering resources also makes the subscription question live again, so the
    two methods that would deliver change notifications are re-checked here: ADR
    0026 fixes the registration set for the process lifetime, so a registered
    resource set must still not come with a notification promise.
    """
    with resource_session(era, runtime_root=full_runtime, label="capabilities") as (
        server,
        result,
    ):
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=era.envelope
        )
        assert_no_write_surface(server, reachable)
        assert_no_list_change_promises(capabilities)
        assert reachable.get("resources") is not None, server.diagnosis(
            "T6 registers resources, so the resources capability must be declared and reachable"
        )
        # Both probes carry *well-formed* params for their own era, because the
        # SDK surface-validates spec methods before handler lookup: malformed
        # params answer INVALID_PARAMS whether or not the method is served, which
        # would mask the only thing being asked here (T6.2 review F1; the same
        # oracle bug T5 fixed at test_transport.py:1171). ``resources/subscribe``
        # is the legacy subscription entry point and needs only its uri;
        # ``subscriptions/listen`` is the 2026-07-28 replacement and requires the
        # opt-in notifications filter.
        for method, params in (
            ("resources/subscribe", {"uri": CATALOG_URI}),
            (
                "subscriptions/listen",
                {"notifications": {"resourcesListChanged": True}} if era.modern else {},
            ),
        ):
            error = expect_error(server, server.call(method, era.params(params)))
            assert error["code"] == METHOD_NOT_FOUND, server.diagnosis(
                f"{method} answered {error!r} instead of not-found, for a registration set "
                "ADR 0026 fixes at process start"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_instructions_stay_truthful_once_resources_are_registered(full_runtime: Path) -> None:
    """ADR 0026 phase amendment (2026-07-29): the instructions describe *this* build.

    The record's frozen six-tool text becomes binding at T9; until then the
    served string must be "static, era-stable, and truthful for its phase". The
    T5 build satisfied that by stating that no resources, prompts, or tools are
    registered — a sentence that becomes false the moment T6 registers the
    ``standards://`` resource surface.

    So this asserts the phase rule in both the directions T6 makes live, without
    pinning any wording.

    *No denial of what is registered.* The T5 text said no resources are
    registered; that becomes false the moment T6 registers the ``standards://``
    surface.

    *No promise of what is not.* The record's frozen text also says the server
    "reports on a consumer repository" and explains the explicit-root rule for
    repository-scoped operations — both true of the finished v1 surface, both
    premature while no repository-scoped tool exists (T6.4 Codex GREEN review,
    F3). T5's own helper only looks for *tool names*, so a present-tense claim
    about repository reporting slips past it; this closes that half. The forbidden
    phrases are claim-shaped rather than word-shaped, so the truthful sentence
    "never writes to any repository" is unaffected.
    """
    era = MODERN_ERA
    with resource_session(era, runtime_root=full_runtime, label="instructions") as (
        server,
        result,
    ):
        reachable = assert_capabilities_match_reachable_registrations(
            server, declared_capabilities(result), envelope=era.envelope
        )
        assert reachable.get("resources"), server.diagnosis(
            "no resource is registered, so the phase rule this test asserts is not yet live"
        )
        assert not reachable.get("tools"), server.diagnosis(
            "a tool is registered, so the premature-claim half of this test no longer applies; "
            "fold the repository claims back into the instructions with the tools that keep them"
        )
        instructions = result.get("instructions")
        assert isinstance(instructions, str) and instructions.strip(), server.diagnosis(
            f"the server must serve a non-empty instructions string, got {instructions!r}"
        )
        lowered = instructions.lower()
        denials = [
            phrase
            for phrase in (
                "no resources",
                "protocol discovery only",
                "resources, prompts, or tools are registered",
            )
            if phrase in lowered
        ]
        assert not denials, server.diagnosis(
            f"the instructions deny a resource surface this build registers: {denials}"
        )
        promises = [
            phrase
            for phrase in (
                "reports on",
                "consumer repository",
                "repository-scoped",
                "repository root",
                "inspect",
                "reconcil",
                "drift",
                "working directory",
                "client roots",
            )
            if phrase in lowered
        ]
        assert not promises, server.diagnosis(
            "the instructions claim repository inspection or reporting this build cannot "
            f"perform, with no tool registered: {promises}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)
