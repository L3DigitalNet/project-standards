"""Launch surface for ``project-standards mcp`` (IR-001, plan T5).

Order of operations is the contract, not an implementation preference:

1. parse the launch arguments and normalize the optional configured root
   boundary — a boundary that would be refused on every later call is a launch
   error, so it fails here rather than after a client has connected;
2. construct ``McpServiceFacade.from_installed``, which eagerly validates the
   *whole* installed distribution — every selected family, payload declaration,
   payload byte, and aggregate digest — so a corrupt distribution can never
   reach the protocol wire as a partially valid server;
3. only then start stdio.

Every failure on that path is a structured
:class:`~project_standards.mcp_services.ServiceError` rendered to **stderr**,
and the process exits non-zero having written nothing to stdout. stdout belongs
to the protocol from the moment the process starts (NFR-003, IR-006), which is
why the diagnostics below are written to ``sys.stderr`` explicitly and why
logging is pointed there before anything else runs.

``transport`` is reached as a module attribute rather than by importing its
functions directly: that keeps the SDK out of this module's import list (only
``transport`` may import SDK types) and leaves a single seam a test can observe
the constructed configuration through.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server import repo_access, transport
from project_standards.mcp_server.models import CATALOG_MAJOR, AdapterConfiguration
from project_standards.mcp_services import McpServiceFacade, ServiceError
from project_standards.package_contract.diagnostics import PackageContractError

# ADR 0026 allows exactly one launch-time knob. The spelling is this module's to
# choose; the *shape* — one optional option, default none — is the frozen part.
BOUNDARY_OPTION = "--root-boundary"

EXIT_OK = 0
EXIT_LAUNCH_REFUSED = 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-standards mcp",
        description=(
            "Serve the installed Catalog 5 standards over the Model Context Protocol "
            "on stdio (read-only, local)."
        ),
    )
    parser.add_argument(
        BOUNDARY_OPTION,
        dest="root_boundary",
        default=None,
        metavar="DIR",
        help=(
            "optional launch-time boundary; repository roots outside it are refused. "
            "Boundaries only narrow: one never supplies or widens a repository root."
        ),
    )
    return parser


def _report(error: ServiceError) -> int:
    """Render one structured launch failure on stderr and refuse to start.

    Every published field is written, not just the message: a client operator
    reading a failed launch needs the stable code to act on and the remediation
    to act with, and neither is recoverable from prose.
    """
    print(f"error: {error.message}", file=sys.stderr)
    print(f"  code: {error.code}", file=sys.stderr)
    print(f"  remediation: {error.remediation}", file=sys.stderr)
    return EXIT_LAUNCH_REFUSED


def _configured_boundary(value: str | None) -> Path | None:
    """Normalize the optional launch-time boundary, or refuse the launch.

    Raises only :class:`ServiceError`, so the caller's handler needs one clause
    for this step rather than a shared one that could mislabel it.
    """
    return None if value is None else repo_access.resolve_boundary(value)


def _installed_facade() -> McpServiceFacade:
    """Build the facade over the installed distribution, or refuse the launch.

    This is the adapter's only error-mapping seam: the distribution boundary
    raises unstructured ``PackageContractError`` messages, and everything past
    this function speaks ``ServiceError``. Keeping the translation here rather
    than in ``run`` means a launch failure is one contract with one shape, and
    that the ``except`` clause covering it cannot silently widen to catch a
    different step's failure.
    """
    try:
        return McpServiceFacade.from_installed(
            InstalledDistribution.current(), CatalogMajor(CATALOG_MAJOR)
        )
    except PackageContractError as error:
        raise ServiceError(
            code="installed-distribution-invalid",
            message=str(error),
            remediation="reinstall project-standards from an intact distribution",
        ) from error


def run(argv: Sequence[str] | None = None) -> int:
    """Validate the launch inputs and the installed distribution, then serve stdio."""
    # stderr before anything else can log: the SDK, anyio, and any warning that
    # fires during construction must never land on the protocol channel.
    logging.basicConfig(stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")

    arguments = _parser().parse_args(list(argv) if argv is not None else None)

    # Server construction joins the refusal path at T6: building the resource
    # registration set can fail (a declared identifier that does not round-trip
    # through the frozen URI grammar), and the plan requires that to be a
    # server-start failure rather than a server with a partial resource list. A
    # traceback would satisfy "non-zero exit" but not "structured error".
    try:
        boundary = _configured_boundary(arguments.root_boundary)
        facade = _installed_facade()
        server = transport.create_server(facade, AdapterConfiguration(configured_boundary=boundary))
    except ServiceError as error:
        return _report(error)

    transport.run_stdio(server)
    return EXIT_OK
