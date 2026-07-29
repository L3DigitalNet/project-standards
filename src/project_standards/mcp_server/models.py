"""Protocol-neutral adapter configuration frozen by ADR 0026.

Deliberately SDK-free and free of any repository-authority import.

ADR 0026 states that ``create_server`` "is not implementer-tunable in v1 beyond
the items listed here", and of those items exactly one is a launch-time input:
the optional configured root boundary. The server's identity, its version, and
its phase instructions are *frozen facts*, so they live here as module-level
constants that no caller can override — a public field accepting an arbitrary
``server_name`` or ``instructions`` would let a caller rename the server or
advertise features it does not register, which is the tunability the record
forbids (T5.4 Codex GREEN review, F1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from project_standards._version import package_version

#: ADR 0026, frozen adapter configuration: the server's protocol identity.
SERVER_NAME = "project-standards"

#: The catalog generation this server exposes. ADR 0026 scopes v1 to Catalog 5;
#: it is a constant rather than an option because a launch-time catalog switch
#: would make the served resource identities depend on invocation.
CATALOG_MAJOR = "5"

#: Instructions served before the six-tool registry exists.
#:
#: ADR 0026's frozen draft text becomes binding at the task that completes the
#: registry it describes (record amendment 2026-07-29); until then the string
#: must be static, era-stable, and truthful for its phase — naming no tool,
#: prompt, or URI scheme this build does not register. Advertising the six tools
#: here would be exactly the untruthful surface TC-T5-002 exists to police.
PHASE_INSTRUCTIONS = (
    "Project Standards is a read-only, local standards server. It exposes the installed "
    "Catalog 5 standard packages and reports on a consumer repository; it never writes to "
    "any repository. This build serves protocol discovery only: no resources, prompts, or "
    "tools are registered, and no capability is advertised for them. Repository-scoped "
    "operations require an explicit repository root argument; the server never infers the "
    "repository from the working directory or from client roots."
)


def server_version() -> str:
    """The installed distribution's version, reported as the server's version.

    Read at call time rather than frozen at import so the protocol identity can
    never disagree with the distribution the facade was actually built from.
    """
    return package_version()


@dataclass(frozen=True, slots=True)
class AdapterConfiguration:
    """The one launch-time input ADR 0026 leaves open.

    ``configured_boundary`` is the record's optional launch-time boundary,
    already normalized and validated by
    :mod:`~project_standards.mcp_server.repo_access` before it reaches here — an
    adapter that accepted an unchecked path would let a bad launch argument
    silently degrade into no boundary at all.

    Nothing else belongs on this object. Identity, version, and instructions are
    module constants precisely so they cannot arrive from a caller.
    """

    configured_boundary: Path | None = None
