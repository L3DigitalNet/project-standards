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
#: must be static, era-stable, and truthful for its phase. Truthful cuts three
#: ways, and each has cost a review finding:
#:
#: * it must not name a tool, prompt, or URI scheme this build does not register
#:   (advertising the six tools here is the untruthful surface TC-T5-002 polices);
#: * it must not *deny* a surface this build does register (continuing to say "no
#:   resources are registered" after T6 registered them is the same fault in
#:   reverse);
#: * it must not *promise* behaviour this build cannot perform. The ADR's frozen
#:   text says the server "reports on a consumer repository" and describes the
#:   explicit-root rule for repository-scoped operations — both true of the
#:   finished v1 surface, both premature while no repository-scoped tool is
#:   registered (T6.4 Codex GREEN review, F3). Those two claims return with the
#:   tools that implement them, at T8/T9, along with the removal of the
#:   no-prompt/no-tool sentence below.
PHASE_INSTRUCTIONS = (
    "Project Standards is a read-only, local standards server. It exposes the installed "
    f"Catalog {CATALOG_MAJOR} standard packages and never writes to any repository. "
    "Standard content is addressed under the standards:// URI scheme as "
    f"standards://catalog/{CATALOG_MAJOR}, standards://{{standard_id}}/{{version}}, and "
    "standards://{standard_id}/{version}/resources/{resource_id}, using ids and versions "
    "exactly as the installed catalog declares them. This build registers those resources "
    "and nothing else; no prompt or tool is available yet."
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
