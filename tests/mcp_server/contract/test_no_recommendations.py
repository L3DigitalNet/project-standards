"""FR-010's omission, proved structurally rather than lexically (T10, TC-T10-005).

FR-010 is a *Could* requirement with a conditional permission: "The server may
expose deterministic package recommendations **only when an existing typed service
can justify them**", and its acceptance is negative — "No v1 tool returns invented
confidence; any recommendation includes declared capability/relation evidence and
exact resource URIs." v1 satisfies it by explicit omission.

**A vocabulary scan cannot prove this, and the first revision of this file was
one** (T10.2 Codex RED review, F8). A method named ``select_standard``, a DTO field
named ``priority`` or ``certainty``, or a helper that ranked by any word not on the
list would all have passed. So the primary proof is a **structural freeze**: the
public service surface is compared, member by member, against the surface plan §5.5
declares. Nothing may be there that the plan does not name — which forecloses a
recommendation service whatever it is called — and nothing the plan names may be
missing, so the freeze cannot be satisfied by an empty facade.

Four independent properties, in the order FR-010's own sentence needs them:

1. **No typed service exists to justify a recommendation.** ``McpServiceFacade``'s
   public callables are exactly the ten §5.5 rows, and every exported DTO's field
   set is exactly the one §5.5 freezes. This is the condition the permission hangs
   on: with no such service, any recommendation surface would be unbacked by
   construction.
2. **The declared schemas stay closed.** Every tool input and output schema is
   ``additionalProperties: false`` at every object level, so no confidence value
   has a slot to travel in even if something produced one.
3. **No served document carries one.** Registration is not enough — a generic
   ``object`` output could carry a score at runtime — so every document a live
   session produces is scanned. The lexical scan survives here, as a *secondary*
   net over runtime values, with its denial exemptions scoped to the exact
   metadata location that carries them rather than applied to the whole document.
4. **What FR-010 would have needed is present and unranked.** Declared
   capabilities, declared relationships, and exact resource URIs are published in
   the catalog's declared order. Proving the evidence exists separates "no
   recommendation logic" from "no useful discovery", which a purely negative test
   would have allowed.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from tests.mcp_server.contract.test_import_boundary import (
    SERVICE_PACKAGE,
    package_directory,
    require_package,
)
from tests.mcp_server.contract.test_protocol_conformance import (
    as_array,
    build_hazard_runtime,
    call_arguments,
    json_leaves,
    planned_consumer_repo,
    wire,
)
from tests.mcp_server.test_discovery_tools import (
    STANDARDS_LIST,
    structured,
)
from tests.mcp_server.test_resources import (
    CATALOG_URI,
    MODERN_ERA,
    oracle_facade,
    read_one,
    resource_session,
)
from tests.mcp_server.test_standard_read import call_tool, list_tools, tool_names
from tests.mcp_server.test_transport import (
    CLI_LAUNCH,
    as_object,
    assert_stdout_is_protocol_only,
    expect_result,
    require_mcp_subcommand,
)

ADAPTER_PACKAGE = "project_standards.mcp_server"

# -- the §5.5 structural freeze ------------------------------------------------
#
# Transcribed from the plan's "Required Internal Interfaces" table (plan:186-195)
# and its DTO table (plan:200-215), never imported. Importing the surface it
# claims to freeze is how the T10.1 declaration golden failed; the same mistake in
# reverse would let a `recommend_standards` method join the facade and be adopted
# by its own oracle.

#: Every public callable plan §5.5 gives ``McpServiceFacade``. Exactly these: a
#: member that is not here has no row in the plan, and a plan row that is not here
#: has been deleted from the facade.
FACADE_METHODS = frozenset(
    {
        "from_installed",
        "from_source",
        "catalog",
        "standard",
        "resource",
        "inspect_repo",
        "reconcile",
        "invoke_read_provider",
        "validate_repo",
        "drift_check",
    }
)

#: Every exported DTO's frozen field set, from plan:200-215. The values are the
#: plan's own words turned into field names; the T3/T4 RED legs froze each one.
DTO_FIELDS: dict[str, frozenset[str]] = {
    "CatalogDescriptor": frozenset({"catalog_major", "standards"}),
    "StandardDescriptor": frozenset(
        {
            "standard_id",
            "title",
            "status",
            "package_version",
            "exposure",
            "capabilities",
            "relationships",
            "resources",
            "providers",
        }
    ),
    "RelationshipSet": frozenset({"companions", "extends", "conflicts"}),
    "ProviderDescriptor": frozenset(
        {
            "provider_id",
            "operation",
            "kind",
            "phase",
            "effect",
            "entrypoint",
            "input_schema",
            "output_schema",
            "resources",
        }
    ),
    "ResourceDescriptor": frozenset(
        {
            "uri",
            "resource_id",
            "role",
            "media_type",
            "digest",
            "standard_id",
            "package_version",
        }
    ),
    "ResourceContent": frozenset({"descriptor", "data"}),
    "RepoInspectionSnapshot": frozenset(
        {"repo_root", "state", "desired_config", "consumer_catalog", "central_lock", "findings"}
    ),
    "Finding": frozenset(
        {
            "rule_id",
            "severity",
            "standard_id",
            "version",
            "path",
            "identity",
            "message",
            "remediation",
            "line",
            "column",
            "locus",
            "observed",
            "limit",
            "expected",
            "actual",
            "expected_digest",
            "actual_digest",
            "governing_options",
            "null_values",
            "first_difference_line",
            "first_difference_expected",
        }
    ),
    "ReconciliationPreview": frozenset(
        {
            "schema_version",
            "applicable",
            "actions",
            "configuration_transforms",
            "units",
            "findings",
            "preconditions",
            "resolution",
            "verification_requests",
            "provider_notices",
            "namespace_prunes",
            "catalog_refresh",
            "next_lock",
            "proposed_lock",
            "reconciliation_fingerprint",
        }
    ),
    "ProviderOperationResult": frozenset(
        {
            "standard_id",
            "version",
            "provider_id",
            "operation",
            "phase",
            "effect",
            "status",
            "findings",
            "diagnostics",
            "output",
        }
    ),
    "ValidationReport": frozenset({"repo_root", "results", "findings"}),
    "DriftReport": frozenset(
        {"repo_root", "reconciliation_fingerprint", "actions", "findings", "results"}
    ),
}

#: The two exported names that are not pydantic DTOs: the facade itself and the
#: structured failure. Named so the walk below can require every other export to
#: be a frozen DTO rather than silently ignoring an unrecognized kind.
NON_DTO_EXPORTS = frozenset({"McpServiceFacade", "ServiceError"})

#: plan §5.5's `ServiceError` row: "stable code, message, affected standard/path
#: when applicable, severity when applicable, and remediation".
SERVICE_ERROR_FIELDS = frozenset(
    {"code", "message", "standard_id", "version", "path", "severity", "remediation"}
)

#: The exact constructor `ServiceError` must keep, rendered by `inspect.signature`.
#:
#: Frozen as a *string* because that is the only form that pins order,
#: keyword-only-ness, annotations, and defaults at once — and because the previous
#: check read class-level `__annotations__`, which is **empty** for a plain
#: exception class, so its subset comparison was vacuous and a renamed or dropped
#: field passed silently (review F2). `ServiceError` is a structured failure a
#: client parses, so its shape is contract rather than implementation detail.
SERVICE_ERROR_SIGNATURE = (
    "(self, *, code: 'str', message: 'str', remediation: 'str', "
    "standard_id: 'str | None' = None, version: 'str | None' = None, "
    "path: 'str | None' = None, severity: 'str' = 'error') -> 'None'"
)

# -- the secondary lexical net -------------------------------------------------

# The vocabulary a recommendation surface speaks. Retained as a runtime-value scan
# only: it is a net under the structural freeze above, never the proof.
ADVISORY_TOKENS = (
    "recommend",
    "recommendation",
    "suggest",
    "suggestion",
    "advise",
    "advice",
    "best_fit",
    "best-fit",
    "should_use",
    "prefer",
)
SCORE_TOKENS = (
    "confidence",
    "relevance",
    "score",
    "ranking",
    "ranked",
    "rank",
    "similarity",
    "affinity",
    "weight",
    "probability",
    "likelihood",
    "certainty",
    "priority",
)
RECOMMENDATION_TOKENS = (*ADVISORY_TOKENS, *SCORE_TOKENS)

# Substring accidents of `rank`.
TOKEN_EXEMPT_SUBSTRINGS = ("frank", "rankine")

#: Denials, not claims — and the reason this scan cannot be a plain token search.
#: FR-023 puts the "nothing is invented" promise in the tool description itself, so
#: the served text necessarily *names* what it refuses to invent. Each entry is
#: ``(tool name, exact metadata field, exact phrase)``: the exemption applies at
#: that one location and nowhere else, so a score leaking into a *result* is still
#: caught, and a separate assertion requires the phrase to still be served (review
#: F8 — the T10.1 revision stripped denials globally).
DECLARED_DENIALS: tuple[tuple[str, str, str], ...] = (
    ("drift_check", "description", "no summary verdict, confidence, or clean-state flag invented"),
)

#: FR-010's own acceptance names what a justified recommendation would have had to
#: carry. Their presence makes the omission a design choice rather than an absence
#: of discovery.
FR010_EVIDENCE_FIELDS = ("capabilities", "relationships", "uri")

# A runtime with no hazard provider: this suite reads the surface rather than
# stressing it.
NO_HAZARDS: tuple[str, ...] = ()


def offending_tokens(text: str, *, denials: tuple[str, ...] = ()) -> list[str]:
    """Every recommendation token one string carries, after the *scoped* exemptions.

    ``denials`` is supplied by the caller only for the exact metadata location that
    declares them. Everywhere else the list is empty, so a description's approved
    denial can never excuse the same word appearing in a served result.
    """
    lowered = text.lower()
    for denial in denials:
        lowered = lowered.replace(denial.lower(), "")
    for exemption in TOKEN_EXEMPT_SUBSTRINGS:
        lowered = lowered.replace(exemption, "")
    return [token for token in RECOMMENDATION_TOKENS if token in lowered]


def offending_leaves(document: object, surface: str) -> list[tuple[str, str, list[str]]]:
    """Every leaf of a decoded document whose location or value speaks the vocabulary.

    No denial exemption applies here at all: this walks *values*, and no requirement
    permits a served value to speak the vocabulary.
    """
    offenders: list[tuple[str, str, list[str]]] = []
    for location, value in json_leaves(document):
        found = offending_tokens(location)
        if isinstance(value, str):
            found += offending_tokens(value)
        if found:
            offenders.append((surface, location, sorted(set(found))))
    return offenders


def metadata_offences(entries: list[dict[str, Any]]) -> list[tuple[str, str, list[str]]]:
    """Recommendation vocabulary in advertised tool metadata, with denials scoped.

    Each entry is checked field by field, and a declared denial is removed only from
    the exact ``(tool, field)`` pair that declares it.
    """
    offenders: list[tuple[str, str, list[str]]] = []
    for entry in entries:
        name = str(entry.get("name"))
        for field, value in sorted(entry.items()):
            if not isinstance(value, str):
                continue
            denials = tuple(
                phrase
                for tool, declared_field, phrase in DECLARED_DENIALS
                if tool == name and declared_field == field
            )
            found = offending_tokens(value, denials=denials)
            if found:
                offenders.append((f"{name}.{field}", value, sorted(set(found))))
    return offenders


def closed_object_schemas(schema: object, path: str = "$") -> list[str]:
    """Every object subschema that does not close itself to extra properties."""
    open_schemas: list[str] = []
    if isinstance(schema, dict):
        mapping = cast("dict[str, object]", schema)
        if mapping.get("type") == "object" and mapping.get("additionalProperties") is not False:
            open_schemas.append(path)
        for key, value in mapping.items():
            open_schemas += closed_object_schemas(value, f"{path}.{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(cast("list[object]", schema)):
            open_schemas += closed_object_schemas(value, f"{path}[{index}]")
    return open_schemas


def public_members(owner: type) -> set[str]:
    """Every public callable the class exposes, **across its whole MRO**.

    ``vars(owner)`` sees only the class's own ``__dict__``, so a public method
    inherited from a base class — a mixin, a future shared façade — was invisible
    to the freeze that claimed to be exact (T10.4 Codex GREEN review, F2). What a
    caller can reach is what the MRO resolves, so that is what is frozen.

    ``object``'s own members are excluded because every class has them and they
    are not part of any declared surface.
    """
    members: set[str] = set()
    for klass in owner.__mro__:
        if klass is object:
            continue
        for attribute, value in vars(klass).items():
            if attribute.startswith("_"):
                continue
            if isinstance(value, classmethod | staticmethod | property) or callable(value):
                members.add(attribute)
    return members


def source_identifiers(module: ModuleType) -> Iterator[tuple[str, str]]:
    """Every identifier a package's source defines, with its file.

    Retained from the first revision as a *third* net, under the structural freeze:
    a private helper that computed a score would never appear in ``__all__``, and
    the structural freeze only constrains the public surface.
    """
    for module_path in sorted(package_directory(module).rglob("*.py")):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                yield module_path.name, node.name
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                yield module_path.name, node.id


@pytest.fixture(scope="module")
def surface_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_hazard_runtime(tmp_path_factory.mktemp("no-recommendations"), NO_HAZARDS)


@pytest.fixture(scope="module")
def surface_repo(surface_runtime: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One planned consumer repository over the recommendation-scan runtime."""
    return planned_consumer_repo(
        surface_runtime, tmp_path_factory.mktemp("no-recommendations-repo")
    )


# -- RED controls --------------------------------------------------------------


def test_recommendation_scanner_detects_an_invented_confidence_surface() -> None:
    """RED control: every net in this file catches a planted defect.

    Deliberately green, and deliberately negative. The T10.1 control tested only
    the same vocabulary the scan already knew, which is why it could not see that
    a vocabulary scan was the wrong instrument (review F8). This control now covers
    all four nets, including the two mixed cases the reviewer named:

    * a scored value and an advisory value at runtime;
    * a **denial plus an offender in the same string** — the approved phrase must
      not launder the second occurrence;
    * a **denial in the wrong field** — the exemption is scoped to one
      ``(tool, field)`` pair, so the same phrase elsewhere is still an offence;
    * an open object schema, which is how an invented confidence would find a slot.
    """
    scored = {"standards": [{"standard_id": "alpha", "confidence": 0.92}]}
    caught = offending_leaves(scored, "probe")
    assert [location for _surface, location, _tokens in caught] == ["$.standards[0].confidence"], (
        f"the scanner missed an invented confidence field: {caught}"
    )
    assert offending_leaves({"results": [{"rank": 1}]}, "probe"), "a ranking field passed"
    assert offending_leaves(
        {"tools": [{"description": "Recommend the best standard."}]}, "probe"
    ), "advisory value text passed"

    denial = DECLARED_DENIALS[0][2]
    clean = metadata_offences(
        [{"name": "drift_check", "description": f"Facts only, with {denial}."}]
    )
    assert not clean, f"the scoped denial exemption does not apply where it was declared: {clean}"

    mixed = metadata_offences(
        [
            {
                "name": "drift_check",
                "description": f"Facts only, with {denial}. Also returns a relevance score.",
            }
        ]
    )
    assert mixed, "a denial laundered a genuine offender in the same string"
    assert "relevance" in mixed[0][2] and "score" in mixed[0][2], mixed

    misplaced = metadata_offences([{"name": "drift_check", "title": f"Facts only, with {denial}."}])
    assert misplaced, "the denial exemption leaked outside the field that declares it"
    other_tool = metadata_offences(
        [{"name": "validate_repo", "description": f"Facts only, with {denial}."}]
    )
    assert other_tool, "the denial exemption leaked outside the tool that declares it"

    assert closed_object_schemas({"type": "object", "properties": {}}) == ["$"], (
        "an open object schema was accepted"
    )
    assert not closed_object_schemas(
        {"type": "object", "properties": {}, "additionalProperties": False}
    ), "a closed object schema was rejected"
    assert closed_object_schemas(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {"a": {"type": "object", "properties": {}}},
        }
    ) == ["$.properties.a"], "a nested open object schema was missed"

    assert not offending_tokens("Frankfurt rankine"), (
        "the substring exemptions are not applied before the token match"
    )


# -- acceptance ----------------------------------------------------------------


def test_v1_has_no_unbacked_recommendation_surface(
    surface_runtime: Path, surface_repo: Path
) -> None:
    """TC-T10-005 (FR-010): the omission, proved structurally and then lexically.

    The first and load-bearing assertion is the **structural freeze**:
    ``McpServiceFacade``'s public callables equal plan §5.5's ten rows exactly, and
    every exported DTO's field set equals the frozen one. A recommendation service
    cannot hide behind a name the vocabulary list never anticipated, because there
    is no room in the surface for a member the plan does not declare — and the
    equality runs in both directions, so the freeze cannot be satisfied by deleting
    the facade.

    The declared schemas are then required to stay closed at every object level, so
    an invented confidence has no slot even if something produced one; the adapter
    and service sources are scanned for scoring identifiers, which reaches private
    helpers the public freeze does not constrain; and every document a live session
    produces is scanned for the vocabulary at runtime, where denial exemptions do
    not apply at all.

    Finally, FR-010's own acceptance evidence — declared capabilities, declared
    relationships, exact version-qualified resource URIs — must be present and in
    the catalog's declared order, so the omission has not removed the facts a
    client needs to choose for itself.
    """
    require_mcp_subcommand()
    services = require_package(SERVICE_PACKAGE, "service package")
    exports = set(getattr(services, "__all__", ()))
    assert exports == set(DTO_FIELDS) | NON_DTO_EXPORTS, (
        "the service layer's public exports are no longer plan §5.5's set; a new export is a "
        f"contract change, not a test edit: {sorted(exports ^ (set(DTO_FIELDS) | NON_DTO_EXPORTS))}"
    )

    facade = cast("type", services.McpServiceFacade)
    members = public_members(facade)
    assert members == FACADE_METHODS, (
        "McpServiceFacade's public surface is not plan §5.5's ten rows. Extra members have no "
        f"plan row and are how a recommendation service would arrive: {sorted(members ^ FACADE_METHODS)}"
    )

    for name, expected in sorted(DTO_FIELDS.items()):
        dto = getattr(services, name)
        fields = set(getattr(dto, "model_fields", {}))
        assert fields == set(expected), (
            f"{name}'s field set is not the one plan §5.5 freezes; a new field is a contract "
            f"change: {sorted(fields ^ set(expected))}"
        )
        config = cast("Mapping[str, Any]", getattr(dto, "model_config", {}))
        assert config.get("extra") == "forbid", (
            f"{name} accepts extra fields, so an invented value could ride along: {config!r}"
        )

    error_signature = str(inspect.signature(services.ServiceError.__init__))
    assert error_signature == SERVICE_ERROR_SIGNATURE, (
        "ServiceError's constructor is no longer the §5.5 shape. Its fields are what a client "
        "parses out of `error.data`, so adding, renaming, or defaulting one differently is a "
        f"contract change.\nserved: {error_signature}\nfrozen: {SERVICE_ERROR_SIGNATURE}"
    )
    declared_error_fields = {
        name
        for name in inspect.signature(services.ServiceError.__init__).parameters
        if name != "self"
    }
    assert declared_error_fields == set(SERVICE_ERROR_FIELDS), (
        "ServiceError's parameters are not plan §5.5's field set: "
        f"{sorted(declared_error_fields ^ set(SERVICE_ERROR_FIELDS))}"
    )

    adapter = require_package(ADAPTER_PACKAGE, "adapter package")
    identifier_offenders: dict[str, list[str]] = {}
    for module in (services, adapter):
        for file_name, identifier in source_identifiers(module):
            found = offending_tokens(identifier)
            if found:
                identifier_offenders.setdefault(file_name, []).extend(found)
    assert not identifier_offenders, (
        f"a scoring or recommendation identifier is defined in the service or adapter layer: "
        f"{identifier_offenders}"
    )

    era = MODERN_ERA
    with resource_session(
        era, runtime_root=surface_runtime, label="no-recommendations", script=CLI_LAUNCH
    ) as (server, opened):
        instructions = str(opened.get("instructions"))
        assert not offending_tokens(instructions), server.diagnosis(
            f"the server describes itself in recommendation vocabulary: "
            f"{offending_tokens(instructions)}"
        )

        entries = list_tools(server, era)
        offences = metadata_offences(entries)
        assert not offences, server.diagnosis(
            f"advertised tool metadata speaks the recommendation vocabulary: {offences}"
        )
        served_metadata = wire(entries).lower()
        stale = [
            f"{tool}.{field}"
            for tool, field, phrase in DECLARED_DENIALS
            if phrase.lower() not in served_metadata
        ]
        assert not stale, server.diagnosis(
            f"these denial exemptions no longer match any served description, so the scan above "
            f"is weaker than it reads: {stale}"
        )

        for entry in entries:
            for slot in ("inputSchema", "outputSchema"):
                open_at = closed_object_schemas(entry.get(slot), f"{entry.get('name')}.{slot}")
                assert not open_at, server.diagnosis(
                    f"these object schemas accept extra properties, so an invented confidence "
                    f"would have a slot to travel in: {open_at}"
                )

        listing = expect_result(server, server.call("resources/list", era.params()))
        registration = offending_leaves(
            as_array(listing.get("resources"), "the resource listing"), "resources/list"
        )
        templates = expect_result(server, server.call("resources/templates/list", era.params()))
        registration += offending_leaves(
            as_array(templates.get("resourceTemplates"), "the template listing"), "templates/list"
        )
        assert not registration, server.diagnosis(
            f"the registered resource surface advertises a recommendation: {registration}"
        )

        advertised = tool_names(entries)
        arguments = call_arguments(surface_repo)
        documents: dict[str, Any] = {}
        for name in advertised:
            frame = call_tool(server, era, name=name, arguments=arguments[name])
            documents[name] = structured(server, frame, label=name)
        documents["resources/read catalog"] = read_one(server, era, CATALOG_URI)

        runtime_offenders: list[tuple[str, str, list[str]]] = []
        for surface, document in sorted(documents.items()):
            runtime_offenders += offending_leaves(document, surface)
        assert not runtime_offenders, server.diagnosis(
            f"a served document carries an invented confidence or ranking: {runtime_offenders}"
        )

        catalog_document = as_object(documents[STANDARDS_LIST], STANDARDS_LIST)
        standards = as_array(catalog_document.get("standards"), "the standards array")
        assert standards, server.diagnosis(
            f"{STANDARDS_LIST} published no standard, so the evidence check below is vacuous"
        )
        first = as_object(standards[0], "a standards_list entry")
        missing = [field for field in FR010_EVIDENCE_FIELDS if not _carries(first, field)]
        assert not missing, server.diagnosis(
            f"FR-010's acceptance evidence {missing} is absent, so the omission has removed the "
            f"facts a client needs to choose for itself: {wire(first)}"
        )

        oracle = oracle_facade(surface_runtime).catalog()
        declared_order = [descriptor.standard_id for descriptor in oracle.standards]
        served_order = [
            str(as_object(entry, "a standards_list entry").get("standard_id"))
            for entry in standards
        ]
        assert served_order == declared_order, server.diagnosis(
            "the served order is not the catalog's declared order, so the listing imposes an "
            f"ordering FR-010 would read as a ranking.\nserved:   {served_order}\n"
            f"declared: {declared_order}"
        )

        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def _carries(entry: Mapping[str, Any], field: str) -> bool:
    """Whether one catalog entry carries the named evidence, at its own level or nested."""
    if field in entry:
        return True
    resources = entry.get("resources")
    if isinstance(resources, list):
        return any(
            field in cast("dict[str, object]", item)
            for item in cast("list[object]", resources)
            if isinstance(item, dict)
        )
    return False


def test_service_source_scan_reaches_every_module(
    surface_runtime: Path,
) -> None:
    """Guard the guard: the identifier scan above must actually see the source.

    A scan that walked no file would report no offender, which is indistinguishable
    from a clean layer. Both packages must yield identifiers, and the count must be
    substantial rather than incidental.
    """
    del surface_runtime
    services = require_package(SERVICE_PACKAGE, "service package")
    adapter = require_package(ADAPTER_PACKAGE, "adapter package")
    for module in (services, adapter):
        seen = list(source_identifiers(module))
        files = {file_name for file_name, _ in seen}
        assert len(files) >= 4, f"{module.__name__}: the scan reached only {sorted(files)}"
        assert len(seen) > 50, f"{module.__name__}: the scan found only {len(seen)} identifiers"


def test_facade_freeze_matches_the_live_signature_arity() -> None:
    """Guard the guard: the frozen method names must name real callables.

    ``FACADE_METHODS`` is a set of strings, so a typo would silently relax the
    equality it participates in. Every name is resolved and required to be callable
    with a signature, which is what makes the freeze a statement about the surface
    rather than about a spelling.
    """
    services = require_package(SERVICE_PACKAGE, "service package")
    facade = cast("type", services.McpServiceFacade)
    for name in sorted(FACADE_METHODS):
        member = getattr(facade, name, None)
        assert member is not None, f"the frozen §5.5 method {name!r} is absent from the facade"
        assert inspect.signature(member) is not None, f"{name!r} is not callable"


def test_structural_freeze_rejects_an_inherited_extra_and_a_changed_error_shape() -> None:
    """RED control: the §5.5 freeze catches the two evasions that survived rev 2.

    Deliberately green, and deliberately negative. The rev-2 freeze read
    ``vars(owner)`` and class-level ``ServiceError.__annotations__``, so a
    recommendation method arriving through a **base class** and an error surface
    that had **lost or renamed** a field both passed it (T10.4 Codex GREEN review,
    F2). Both evasions are planted here against the same helpers the acceptance
    test uses, so a future relaxation of either mechanism fails immediately.
    """

    class _Base:
        def recommend_standards(self) -> None:  # pragma: no cover - never called
            """The surface an inherited recommendation service would arrive on."""

    class _Derived(_Base):
        def catalog(self) -> None:  # pragma: no cover - never called
            """One declared §5.5 row, so the class is not trivially empty."""

    inherited = public_members(_Derived)
    assert "recommend_standards" in inherited, (
        "an inherited public callable is invisible to the freeze, so a recommendation service "
        f"could arrive through a base class: {sorted(inherited)}"
    )
    assert "catalog" in inherited, f"the freeze lost the class's own members: {sorted(inherited)}"
    assert inherited != FACADE_METHODS, (
        "the control class must not accidentally equal the frozen surface"
    )

    class _RenamedError(Exception):
        def __init__(
            self,
            *,
            code: str,
            message: str,
            remediation: str,
            standard_id: str | None = None,
            version: str | None = None,
            location: str | None = None,
            severity: str = "error",
        ) -> None:  # pragma: no cover - never raised
            super().__init__(message)

    class _ShortError(Exception):
        def __init__(self, *, code: str, message: str) -> None:  # pragma: no cover - never raised
            super().__init__(message)

    for label, candidate in (("renamed field", _RenamedError), ("missing fields", _ShortError)):
        signature = str(inspect.signature(candidate.__init__))
        assert signature != SERVICE_ERROR_SIGNATURE, (
            f"the frozen signature accepts a {label} variant, so it pins nothing: {signature}"
        )
        parameters = {
            name for name in inspect.signature(candidate.__init__).parameters if name != "self"
        }
        assert parameters != set(SERVICE_ERROR_FIELDS), (
            f"the field-set comparison accepts a {label} variant: {sorted(parameters)}"
        )

    # An `__annotations__` read — the rev-2 mechanism — sees nothing on any of
    # these classes, which is why it could not have caught either evasion.
    assert not getattr(_ShortError, "__annotations__", {}), (
        "class-level __annotations__ is no longer empty for a plain exception class; the "
        "rationale recorded for freezing the signature instead needs revisiting"
    )
