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

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from project_standards._version import package_version

#: ADR 0026, frozen adapter configuration: the server's protocol identity.
SERVER_NAME = "project-standards"

#: The catalog generation this server exposes. ADR 0026 scopes v1 to Catalog 5;
#: it is a constant rather than an option because a launch-time catalog switch
#: would make the served resource identities depend on invocation.
CATALOG_MAJOR = "5"

#: ADR 0026's own enumeration order for the v1 registry. It is the order the
#: record's instructions sentence uses, so a rendering built from it reproduces
#: the record rather than re-deciding it. Registry *membership* belongs to
#: ``tools.build_tool_registry``; this is the record's prose order, and the T9
#: instructions test holds the two equal.
INSTRUCTIONS_TOOL_ORDER: tuple[str, ...] = (
    "standards_list",
    "standard_read",
    "repo_inspect",
    "reconcile_preview",
    "validate_repo",
    "drift_check",
)

#: The count word the record's sentence uses, indexed by registry size. Spelled
#: out because the frozen text says "Six tools are available": a rendering that
#: said "6" would not be that text with its enumeration reduced.
_COUNT_WORDS: tuple[str, ...] = ("No", "One", "Two", "Three", "Four", "Five", "Six")

_INSTRUCTIONS_PREFIX = (
    "Project Standards is a read-only, local standards server. It exposes the installed "
    f"Catalog {CATALOG_MAJOR} standard packages and reports on a consumer repository; it "
    "never writes to any repository. Standard content is addressed under the standards:// "
    f"URI scheme as standards://catalog/{CATALOG_MAJOR}, "
    "standards://{standard_id}/{version}, and "
    "standards://{standard_id}/{version}/resources/{resource_id}, using ids and versions "
    "exactly as the installed catalog declares them. "
)

_INSTRUCTIONS_SUFFIX = (
    " Every repository-scoped tool requires an explicit repo_root argument; the server does "
    "not infer the repository from the working directory or from client roots."
)


def instructions_for(registered: Iterable[str]) -> str:
    """ADR 0026's frozen instructions, rendered for one session's actual registry.

    The record's 2026-07-30 amendment binds the frozen text *per session*: a
    process registering all six tools serves it verbatim, and a process whose
    client matrix omits the ``standard_read`` fallback serves the same text with
    the count word and the enumeration reduced to its actual registry, nothing
    else changed. That is what keeps the string truthful in every configuration —
    naming a tool the session does not register is the untruthful surface
    TC-T5-002 polices, and it is why one static sentence could not survive
    FR-008's matrix gate.

    The string stays *static and non-tunable*: it is fixed at server construction
    from the T1 evidence matrix, which is recorded evidence rather than a knob,
    and no caller can supply it.

    Ordering is normalized to the record's own enumeration rather than taken from
    the caller, so a registry assembled in another order still renders the
    record's sentence.

    Raises:
        ValueError: if the registry names a tool ADR 0026's v1 set does not
            contain. A tool with no place in the record's enumeration cannot be
            described truthfully, so that is a registration bug and must abort the
            launch rather than produce prose that silently omits a served tool.
    """
    names = set(registered)
    unknown = sorted(names - set(INSTRUCTIONS_TOOL_ORDER))
    if unknown:
        raise ValueError(f"tools outside ADR 0026's v1 registry cannot be described: {unknown}")
    ordered = [name for name in INSTRUCTIONS_TOOL_ORDER if name in names]
    enumeration = f"{', '.join(ordered[:-1])}, and {ordered[-1]}"
    return (
        f"{_INSTRUCTIONS_PREFIX}{_COUNT_WORDS[len(ordered)]} tools are available: "
        f"{enumeration}.{_INSTRUCTIONS_SUFFIX}"
    )


#: The record's text for a session that registers the whole v1 registry.
#:
#: Kept as a module constant because ADR 0026 makes identity, version, and
#: instructions frozen facts no caller may supply (T5.4 Codex GREEN review, F1),
#: and because it is what a default launch serves: the recorded client matrix
#: requires the ``standard_read`` fallback, so all six register and the served
#: string equals this constant.
PHASE_INSTRUCTIONS = instructions_for(INSTRUCTIONS_TOOL_ORDER)


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
