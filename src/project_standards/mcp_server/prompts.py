"""The prompt-registration decision, and why v1's answer is "none" (plan T7).

Deliberately SDK-free and repository-free, like every adapter module except
``transport``: prompt sources are *declared package facts*, so they are reached
through ``mcp_services`` and never re-derived here. Both boundaries are enforced
by ``tests/mcp_server/contract/test_import_boundary.py``.

**This module exists to make an absence deliberate.** ADR 0026 states the rule
twice — "Prompts: declared only when prompt-role resources are registered ...
otherwise the capability is absent", and "Prompts are registered only from
declared prompt-role resources. The server invents no prompts of its own" — and
FR-005 adds that prompts are exposed "only where selected clients support them
usefully". The T1 evidence matrix records prompts as "an additive Claude Code
affordance, never a required access path", since Codex CLI 0.145.0 has no
prompts capability at all.

**No record approves a prompt role, so nothing is derived.** The installed
Catalog 5 declares 22 distinct resource roles and ADR 0026 enumerates none of
them as prompt-eligible, so :data:`APPROVED_PROMPT_ROLES` is empty, no prompt is
registered, and ``transport`` registers no prompt handler — which is what makes
the SDK omit the capability. ``agent-summary``, the template roles, and the
prose roles are *not* prompts and must never be reinterpreted as prompts
(plan:405); that is a statement about approval, not about their content, so the
rule is expressed as an approved-role set rather than as a denylist.

**What is deliberately not here.** No prompt name, title, description, or
message builder. plan:405's derivation clause ("If prompts are approved, derive
names/content only from exact declared resources") is conditional on an approval
that does not exist, and building the machinery for it now would make a future
approval look implementation-ready without the approval and specification pass
it requires (T7.2 Codex RED review, F2/F3). What this module does own is the
decision itself: :func:`prompt_role_resources` is evaluated on every launch, so
adding a role to the set without also adding a derivation fails loudly at
``create_server`` instead of silently registering nothing.
"""

from __future__ import annotations

from project_standards.mcp_services import CatalogDescriptor, ResourceDescriptor

#: Resource roles an approved record has designated as prompt sources.
#:
#: Empty in v1, and empty for a *record* reason rather than an implementation
#: one: ADR 0026's v1 registry enumerates no prompt-eligible role. Adding an
#: entry here is therefore not a code change but the visible consequence of a new
#: approval, and it is inert until a derivation exists to consume it — see the
#: guard in ``transport.create_server``.
APPROVED_PROMPT_ROLES: frozenset[str] = frozenset()

#: The stable code for the launch refusal that keeps the set above honest: a role
#: is approved, but no derivation exists to turn it into a prompt. It lives here
#: rather than at the ``transport`` call site because every other stable code in
#: the adapter is a module constant beside the rule it names (``resources`` and
#: ``tools`` both do this), and a client that ever sees it needs the taxonomy to
#: be one taxonomy.
PROMPT_DERIVATION_UNAVAILABLE = "prompt-derivation-unavailable"


def prompt_role_resources(catalog: CatalogDescriptor) -> tuple[ResourceDescriptor, ...]:
    """Every declared resource whose role an approved record designates as a prompt.

    The one derivation input ADR 0026 permits. Returns an empty tuple for every
    installed distribution while :data:`APPROVED_PROMPT_ROLES` is empty, which is
    what the absence of the prompts capability rests on.
    """
    return tuple(
        resource
        for descriptor in catalog.standards
        for resource in descriptor.resources
        if resource.role in APPROVED_PROMPT_ROLES
    )
