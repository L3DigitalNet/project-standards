"""The server as a whole process, over the *real* installed Catalog 5 (T10).

Every other suite in ``tests/mcp_server`` serves a bounded fixture catalog, and for
good reason: the real Catalog 5 grows with every released standard, so a suite that
pinned its contents would fail on the next release. That choice has a cost the T6
close-out recorded twice, in two defects a fixture-scale test could not have caught
— an enumerated resource listing that measured 587,143 bytes and a catalog resource
that measured 373,619 — both found only by smoking the real distribution, and both
queued here: "add a real-catalog byte budget for discovery compactness, since
fixture-scale tests provably cannot regress it".

**The budget is absolute *and* per standard.** Density alone is not a context bound:
at 52 standards a per-standard ceiling of 4 KiB permits roughly 213 KB per document
and grows without limit, and the listing-to-catalog ratio actually *improves* when
the catalog bloats (T10.2 Codex RED review, F12). So each scaling quantity carries
two ceilings — one on the total a client actually pays, one on the density that
would reveal a shape change before the total is reached — and the fixed quantities
carry one.

**Where the numbers come from.** NFR-002 and NFR-012 authorize a bound; no contract
document names a number, so these are reviewed *test* constants, seeded from the
measurements recorded in the pipeline notes and flagged for owner visibility at
closeout. The absolute ceilings are set below the 373,619-byte pre-mask baseline the
T6 review measured and above the current 83,764 bytes with headroom, so the defect
that motivated the FR-001 field mask would fail them while ordinary catalog growth
does not.

This file is also the only place the launch path is exercised end to end against the
distribution a user installs, which is what makes it *integration* rather than
*contract*: same CLI, same eager integrity validation, same catalog, no fixture
projection anywhere. It carries the FR-029/NFR-011 dependency-record check for the
same reason — the pinned SDK is a property of the artifact, not of a fixture.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

from project_standards._version import package_version
from tests.mcp_server.contract.test_protocol_conformance import (
    as_array,
    assert_adr_0026_capability_clause,
    assert_protocol_only_stdout,
    server_identity,
    wire,
)
from tests.mcp_server.test_discovery_tools import STANDARDS_LIST, structured
from tests.mcp_server.test_resources import (
    ERA_IDS,
    ERAS,
    MODERN_ERA,
    Era,
    list_resources,
    list_templates,
    metadata_document,
    read_one,
    resource_session,
)
from tests.mcp_server.test_standard_read import call_tool, list_tools, tool_names
from tests.mcp_server.test_transport import (
    CLI_LAUNCH,
    RUNTIME_ROOT,
    ServerProcess,
    as_object,
    expect_result,
    require_mcp_subcommand,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# The real installed catalog this server exposes. ADR 0026 scopes v1 to Catalog 5
# and the URI is a client-visible fact, so it is spelled as a client would.
CATALOG_URI = "standards://catalog/5"

# -- FR-029 / NFR-011: the pinned SDK contract ---------------------------------
#
# The T1 evidence register (`docs/research/...client-matrix.md`) is the authority
# for every version-sensitive external fact, and FR-029 requires the decision to
# record "stable versions, official sources, license result, transport/capability
# contracts, and conformance evidence" before dependency lock-in. Only the facts
# FR-029 names are pinned here — the exact constraint, the license, and the served
# revisions. The document is not turned into a golden (review F11 amendment).

#: The exact dependency constraint FR-029 froze. `==` rather than a range: the
#: whole point of the T1 lock-in is that the served protocol behaviour belongs to
#: one audited release.
SDK_REQUIREMENT = "mcp==2.0.0"
SDK_DISTRIBUTION = "mcp"
SDK_VERSION = "2.0.0"

#: The license result T1 recorded, which FR-029 names explicitly.
SDK_LICENSE = "MIT"

#: The T1 evidence register that must carry those facts.
EVIDENCE_RECORD = (
    REPO_ROOT / "docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md"
)

# -- NFR-002 / NFR-012 budget --------------------------------------------------
#
# Measured 2026-07-30 against the installed Catalog 5 (52 standards, 53 listed
# resources), modern era, full JSON-RPC frame bytes. Absolute ceilings are ~2.3x
# the measurement and ~0.5x the 373,619-byte pre-mask baseline, so the shape defect
# fails and ordinary growth does not.

#: `resources/list` frame bytes. Measured 12,055.
MAX_LIST_BYTES = 65_536
#: ...and its density. Measured 227 bytes per listed entry.
MAX_LIST_BYTES_PER_ENTRY = 512

#: Catalog-resource body bytes. Measured 83,764; the pre-mask projection measured
#: 373,619, so this ceiling is what an unmasked `CatalogDescriptor` fails.
MAX_CATALOG_BYTES = 196_608
#: ...and its density. Measured 1,611 bytes per declared standard (pre-mask 7,185).
MAX_CATALOG_BYTES_PER_STANDARD = 4_096

#: `standards_list` structured bytes, held to the same pair as the catalog resource
#: it projects: the two publish the same FR-001 field mask, so a divergence is a
#: second producer rather than growth. Measured ~80,876.
MAX_TOOL_CATALOG_BYTES = 196_608
MAX_TOOL_CATALOG_BYTES_PER_STANDARD = 4_096

#: `tools/list` frame bytes. Fixed, because ADR 0026 closes the registry at six and
#: TC-T10-003 proves the catalog cannot add a seventh. Measured 21,143.
MAX_TOOLS_LIST_BYTES = 49_152

#: The opening frame: identity, capabilities, one instructions string. Measured 1,066.
MAX_DISCOVERY_BYTES = 8_192

#: `resources/templates/list`. Fixed: ADR 0026 freezes exactly two forms. Measured 857.
MAX_TEMPLATES_BYTES = 4_096

#: The discovery listing must stay a small fraction of the document it points into.
#: Kept alongside the absolute ceilings rather than instead of them, because the
#: ratio improves when the catalog bloats. Measured 0.14.
MAX_LIST_TO_CATALOG_RATIO = 0.5


def frame_bytes(server: ServerProcess, method: str, params: dict[str, Any] | None) -> int:
    """The exact wire size of one response frame, measured on the transcript.

    Measured from the server's own stdout rather than by re-encoding the decoded
    result, because what a client pays for is the bytes that crossed the pipe: key
    order, separators, and escaping all count, and a re-encoding would quietly
    normalize them away.
    """
    before = len(server.stdout_bytes)
    frame = server.call(method, params or {})
    expect_result(server, frame)
    return len(server.stdout_bytes) - before


def test_pinned_sdk_contract_matches_the_t1_evidence_record() -> None:
    """FR-029/NFR-011: the locked SDK is the one T1 audited, in project and lock alike.

    FR-029 requires the decision record to fix "stable versions, official sources,
    license result, transport/capability contracts, and conformance evidence"
    *before dependency lock-in*, and NFR-011 requires the pin to be verified before
    lock-in as well. Nothing in T5-T9 checks the pin itself: the suites exercise
    whatever SDK happens to be installed, so an unnoticed bump would silently
    change the protocol behaviour every other test measures (review F11).

    Four facts, and only the four FR-029 names — the register is deliberately not
    turned into a broad golden:

    * ``pyproject.toml`` declares the exact constraint ``mcp==2.0.0``;
    * ``uv.lock`` resolves that distribution to that exact version, so the
      environment CI builds is the audited one;
    * the installed distribution reports the same version at runtime;
    * the T1 evidence register carries that version and the MIT license result.
    """
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project.get("project", {}).get("dependencies", [])
    assert SDK_REQUIREMENT in dependencies, (
        f"pyproject.toml must pin the audited SDK exactly as {SDK_REQUIREMENT!r}; it declares "
        f"{[item for item in dependencies if SDK_DISTRIBUTION in item]}"
    )

    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = [
        package for package in lock.get("package", []) if package.get("name") == SDK_DISTRIBUTION
    ]
    assert len(locked) == 1, f"uv.lock resolves {SDK_DISTRIBUTION} {len(locked)} times: {locked}"
    assert locked[0].get("version") == SDK_VERSION, (
        f"uv.lock resolves {SDK_DISTRIBUTION} to {locked[0].get('version')!r}, not the audited "
        f"{SDK_VERSION!r}; refresh T1 before changing the pin"
    )

    from importlib.metadata import version as installed_version

    assert installed_version(SDK_DISTRIBUTION) == SDK_VERSION, (
        f"the installed {SDK_DISTRIBUTION} is {installed_version(SDK_DISTRIBUTION)}, not the "
        f"audited {SDK_VERSION}; every protocol assertion in this tree measures the wrong release"
    )

    assert EVIDENCE_RECORD.is_file(), f"the T1 evidence register {EVIDENCE_RECORD} is absent"
    register = EVIDENCE_RECORD.read_text(encoding="utf-8")
    assert re.search(
        rf"\b{re.escape(SDK_DISTRIBUTION)}\b[^\n]*\b{re.escape(SDK_VERSION)}\b", register
    ), f"the T1 register does not record {SDK_DISTRIBUTION} {SDK_VERSION} as the selected release"
    assert SDK_LICENSE in register, (
        f"the T1 register does not record the {SDK_LICENSE} license result FR-029 requires"
    )


def test_real_catalog_discovery_stays_within_its_context_budget() -> None:
    """NFR-002/NFR-012: discovery over the real catalog stays small *and* dense.

    The queued T6 harvest item, made testable. Each scaling quantity carries an
    absolute ceiling and a density ceiling, because either alone can be satisfied by
    a document a client cannot afford: density alone permits unbounded totals, and a
    total alone would not reveal a shape change until the total was reached (review
    F12). The fixed quantities — discovery, the template listing, and the closed
    six-tool registry — carry an absolute ceiling only, because none of them scales
    with the catalog.

    The measurement is also asserted to be non-trivial, so a distribution that
    shipped an empty catalog could not pass the budget by having nothing to measure.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    with resource_session(era, runtime_root=RUNTIME_ROOT, label="budget", script=CLI_LAUNCH) as (
        server,
        opened,
    ):
        discovery_bytes = len(server.stdout_bytes)
        assert discovery_bytes <= MAX_DISCOVERY_BYTES, server.diagnosis(
            f"the opening frame is {discovery_bytes} bytes against a {MAX_DISCOVERY_BYTES} "
            "ceiling; identity, capabilities, and one instructions string do not scale"
        )
        assert opened.get("instructions"), server.diagnosis("no instructions were served")

        listing_bytes = frame_bytes(server, "resources/list", era.params())
        entries = list_resources(server, era)
        assert len(entries) >= 8, server.diagnosis(
            f"the installed catalog listed only {len(entries)} resources, so this budget measures "
            "nothing"
        )
        assert listing_bytes <= MAX_LIST_BYTES, server.diagnosis(
            f"resources/list is {listing_bytes} bytes against a {MAX_LIST_BYTES} ceiling; an "
            "enumerated payload listing is what this refuses"
        )
        per_entry = listing_bytes / len(entries)
        assert per_entry <= MAX_LIST_BYTES_PER_ENTRY, server.diagnosis(
            f"resources/list costs {per_entry:.0f} bytes per entry against "
            f"{MAX_LIST_BYTES_PER_ENTRY} ({listing_bytes} bytes, {len(entries)} entries)"
        )

        templates_bytes = frame_bytes(server, "resources/templates/list", era.params())
        assert templates_bytes <= MAX_TEMPLATES_BYTES, server.diagnosis(
            f"resources/templates/list is {templates_bytes} bytes against {MAX_TEMPLATES_BYTES} "
            "for two frozen forms"
        )
        assert len(list_templates(server, era)) == 2, server.diagnosis(
            "ADR 0026 freezes exactly two parameterized resource forms"
        )

        tools_bytes = frame_bytes(server, "tools/list", era.params())
        assert tools_bytes <= MAX_TOOLS_LIST_BYTES, server.diagnosis(
            f"tools/list is {tools_bytes} bytes against {MAX_TOOLS_LIST_BYTES} for a registry ADR "
            "0026 closes at six"
        )

        catalog_document = metadata_document(server, era, CATALOG_URI)
        standards = as_array(catalog_document.get("standards"), "the catalog standards array")
        assert len(standards) >= 8, server.diagnosis(
            f"the real catalog declares {len(standards)} standards, so the per-standard ceilings "
            "measure nothing"
        )
        count = len(standards)
        catalog_entry = read_one(server, era, CATALOG_URI)
        catalog_bytes = len(str(catalog_entry.get("text", "")).encode("utf-8"))
        assert catalog_bytes <= MAX_CATALOG_BYTES, server.diagnosis(
            f"the catalog resource is {catalog_bytes} bytes against a {MAX_CATALOG_BYTES} ceiling; "
            "the unmasked CatalogDescriptor projection measured 373,619 and is what this refuses"
        )
        per_standard = catalog_bytes / count
        assert per_standard <= MAX_CATALOG_BYTES_PER_STANDARD, server.diagnosis(
            f"the catalog resource costs {per_standard:.0f} bytes per standard against "
            f"{MAX_CATALOG_BYTES_PER_STANDARD} ({catalog_bytes} bytes, {count} standards)"
        )

        frame = call_tool(server, era, name=STANDARDS_LIST, arguments={})
        document = structured(server, frame, label=STANDARDS_LIST)
        tool_bytes = len(wire(document).encode("utf-8"))
        assert tool_bytes <= MAX_TOOL_CATALOG_BYTES, server.diagnosis(
            f"{STANDARDS_LIST} returns {tool_bytes} bytes against a {MAX_TOOL_CATALOG_BYTES} "
            "ceiling"
        )
        assert tool_bytes / count <= MAX_TOOL_CATALOG_BYTES_PER_STANDARD, server.diagnosis(
            f"{STANDARDS_LIST} costs {tool_bytes / count:.0f} bytes per standard against "
            f"{MAX_TOOL_CATALOG_BYTES_PER_STANDARD}"
        )

        ratio = listing_bytes / catalog_bytes
        assert ratio <= MAX_LIST_TO_CATALOG_RATIO, server.diagnosis(
            f"the discovery listing is {ratio:.2f} of the catalog document it points into, over "
            f"the {MAX_LIST_TO_CATALOG_RATIO} ceiling; NFR-002 wants the index readable before "
            "the documents are"
        )

        assert server.finish() == 0
        assert_protocol_only_stdout(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_real_distribution_serves_the_whole_surface_with_protocol_only_stdout(era: Era) -> None:
    """NFR-003/NFR-009/NFR-010: the installed artifact serves, cleanly, in both eras.

    The same walk the conformance transcript performs, against the distribution a
    user installs rather than a fixture projection — the only way to catch a defect
    that lives in the *packaging*: a payload the projection ships but the catalog
    does not declare, a resource whose declared digest does not match the installed
    bytes, a URI a real standard id cannot round-trip through the frozen grammar.
    Every one of those aborts the launch by design, so a server that reaches the
    wire here has already proved the whole installed distribution validates.

    Repository-scoped tools are deliberately not called: this repository is the
    server's own source tree, not a consumer fixture, and pointing a tool at it
    would make the assertions depend on the working copy's state.
    """
    require_mcp_subcommand()
    with resource_session(era, runtime_root=RUNTIME_ROOT, label="real", script=CLI_LAUNCH) as (
        server,
        opened,
    ):
        assert_adr_0026_capability_clause(server, opened, era, runtime=RUNTIME_ROOT)

        entries = list_resources(server, era)
        assert entries, server.diagnosis("the installed catalog registered no resource")
        uris = [str(entry.get("uri")) for entry in entries]
        assert CATALOG_URI in uris, server.diagnosis(
            f"the catalog resource is not registered: {uris[:5]}"
        )
        for uri in uris:
            assert uri.startswith("standards://"), server.diagnosis(
                f"a registered resource uses a scheme outside the frozen grammar: {uri!r}"
            )

        contents = read_one(server, era, CATALOG_URI)
        assert contents.get("text"), server.diagnosis("the catalog resource served no body")

        advertised = tool_names(list_tools(server, era))
        assert STANDARDS_LIST in advertised, server.diagnosis(
            f"the installed distribution registers no {STANDARDS_LIST}: {advertised}"
        )
        document = structured(
            server,
            call_tool(server, era, name=STANDARDS_LIST, arguments={}),
            label=STANDARDS_LIST,
        )
        standards = as_array(document.get("standards"), "the standards array")
        assert standards, server.diagnosis(
            f"{STANDARDS_LIST} published no standard over the real catalog: {document!r}"
        )
        first = as_object(standards[0], "a standards_list entry")
        assert first.get("package_version"), server.diagnosis(
            f"a published standard carries no exact version: {first!r}"
        )

        assert server.finish() == 0, server.diagnosis("the installed server did not exit cleanly")
        frames = assert_protocol_only_stdout(server)
        assert len(frames) == len(server.sent_ids), server.diagnosis(
            f"the session answered {len(frames)} of {len(server.sent_ids)} requests"
        )


def test_installed_server_reports_the_distribution_version_it_was_built_from() -> None:
    """NFR-010/FR-029: the protocol identity and the installed artifact agree.

    A one-line property with a real failure mode: the server reads its version at
    call time from the installed distribution, so a runtime assembled from mixed
    builds — the hazard the T6 notes recorded, where a ``src/``-only edit was
    invisible to a suite serving ``build/wheel-runtime`` — would report a version
    that does not match the bytes it is serving.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    with resource_session(era, runtime_root=RUNTIME_ROOT, label="identity", script=CLI_LAUNCH) as (
        server,
        opened,
    ):
        identity = server_identity(opened)
        assert identity.get("version") == package_version(), server.diagnosis(
            f"the server reports version {identity.get('version')!r} while this process resolved "
            f"{package_version()!r} from the same runtime root"
        )
        assert server.finish() == 0
        assert_protocol_only_stdout(server)
