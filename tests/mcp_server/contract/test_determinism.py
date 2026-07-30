"""Determinism and the exact normalization contract (T10, NFR-005 and DR-009).

Covers TC-T10-002 (semantically unordered inputs produce identical stable output)
and TC-T10-004 (only the declared normalization is allowed).

**What "semantically unordered" means here, and why it is not the catalog order.**
The catalog *declares* an order, so permuting it would be changing a declared fact
rather than permuting an unordered input; NFR-005 requires that declared order to
be reproduced. (This freeze was upheld on review.) The genuinely unordered inputs
a server result must not depend on are the ones no document assigns a meaning to:

* the filesystem's directory-entry order for the installed tree, which is creation
  order on most Linux filesystems and is why the mirror runtime materializes the
  same bytes in reverse;
* the absolute path the distribution happens to sit at;
* ``PYTHONHASHSEED``, which reorders every set and every dict built by iterating
  one — including inside a *provider worker*, a separate interpreter with its own
  seed;
* the order the client happens to call the tools in within one session.

Cross-process hash-seed determinism is here by name: T3's review deferred its
finding F9 to "T10, which owns TC-T10-002". The seed is fixed rather than left to
chance, and the fixture tree carries ``unordered-alpha``, a declared ``validate``
provider whose output dict is built by iterating a set literal specifically so its
key order is seed-dependent unless something canonicalizes it.

**Two comparisons, deliberately different, because they answer different
questions** (T10.2 Codex RED review, F1 and F2).

*Determinism* is a claim about **order**: two runs of the same producer must emit
the same key sequence, so it is compared with :func:`~tests.mcp_server.contract.test_protocol_conformance.wire`,
which preserves the order the wire carried. The T10.1 revision used the T8
``rendered()`` helper, whose ``sort_keys=True`` erased precisely the seed-dependent
variance the canary exists to expose — and whose ``default=str`` was itself an
undeclared normalization.

*Closure* is a claim about **values**: every stable field of every surface must
equal an independently constructed expectation, with only DR-008's one exclusion
masked. That is asserted as structural equality of the decoded documents, which is
stronger than any string comparison for this purpose and is unaffected by key
order — a JSON object has no declared member order on the wire, and T8's
``test_standards_list_matches_catalog_resource`` already records that reasoning.
No surface is skipped: ``standards_list``, ``standard_read``, ``repo_inspect``,
``reconcile_preview``, ``validate_repo``, ``drift_check``, and the catalog read all
carry an independent oracle.

Harness reuse follows the T9 statement, with the oracles taken from the suites that
own them: ``test_resources.catalog_projection`` is the FR-001 discovery oracle
written from the spec sentence, ``tests/mcp_services.test_consumer.dumped`` is the
facade projection, and ``test_protocol_conformance`` owns the hazard runtime
builder and the order-preserving renderer.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest

from tests.mcp_server.contract.test_protocol_conformance import (
    as_array,
    build_hazard_runtime,
    call_arguments,
    json_leaves,
    planned_consumer_repo,
    wire,
)
from tests.mcp_server.test_consumer_tools import (
    CONTROL_PLANE_SLOT,
    DRIFT_CHECK,
    PREVIEW_SLOT,
    RECONCILE_PREVIEW,
    VALIDATE_REPO,
    without_diagnostics,
)
from tests.mcp_server.test_discovery_tools import (
    REPO_INSPECT,
    STANDARDS_LIST,
    structured,
)
from tests.mcp_server.test_resources import (
    CATALOG_URI,
    ERA_IDS,
    ERAS,
    MODERN_ERA,
    Era,
    catalog_projection,
    declared_resources,
    metadata_document,
    oracle_facade,
    read_one,
    resource_session,
)
from tests.mcp_server.test_standard_read import TOOL_NAME as STANDARD_READ
from tests.mcp_server.test_standard_read import call_tool, list_tools, tool_names
from tests.mcp_server.test_transport import (
    CLI_LAUNCH,
    ServerProcess,
    as_object,
    assert_stdout_is_protocol_only,
    require_mcp_subcommand,
)
from tests.mcp_services.test_consumer import dumped

# The hazard provider whose output dict is built by iterating a set literal, so
# its key order is `PYTHONHASHSEED`-dependent inside the worker process unless the
# service canonicalizes it. It declares an approved `validate` operation, so
# `validate_repo` reaches it without any new dispatch surface.
DETERMINISM_HAZARD = "unordered"

# Two fixed seeds rather than the interpreter's random default: a probabilistic
# probe that happened to draw the same ordering twice would report determinism it
# never observed.
HASH_SEEDS = ("0", "524287")

# DR-008's single exclusion, named by the DTO field it lives on. Everything else in
# every document below compares verbatim.
DECLARED_EXCLUSIONS = ("ProviderOperationResult.diagnostics",)

# The surface key under which the catalog resource read is captured. Not a tool
# name, so it cannot collide with one.
CATALOG_READ = "resources/read standards://catalog/5"
PAYLOAD_READ = "resources/read payload"

# DR-009: "timestamps and durations shall be excluded from the stable result
# rather than rewritten". Matched on field *name*, because a stable result has no
# legitimate use for either, and separately on value shape, because a timestamp
# smuggled into a differently named field is the same defect.
TIME_FIELD_TOKENS = (
    "timestamp",
    "time",
    "date",
    "duration",
    "elapsed",
    "started",
    "finished",
    "created",
    "modified",
    "updated",
    "mtime",
    "ctime",
    "epoch",
    "seconds",
    "millis",
    "nanos",
)

# Field-name tokens the list above would otherwise catch for the wrong reason.
# `schema_version`/`package_version` are identity, not time; `runtime` names a
# provider execution model.
TIME_TOKEN_EXEMPT = ("runtime", "lifetime", "datetime_format")

# ISO-8601 instants and RFC-3339 dates, matched anywhere in a string value.
ISO_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")


def stable_documents(
    server: ServerProcess, era: Era, repo: Path, payload_uri: str, *, order: list[str] | None = None
) -> dict[str, Any]:
    """Every stable document one session can produce, keyed by its surface.

    One helper rather than a per-test walk, because the whole point of both
    acceptance tests is that *the same* set of documents is compared: a determinism
    proof covering fewer surfaces than the closure proof would leave the difference
    unexplained.

    ``order`` is the call order within the session, itself a semantically unordered
    input: no tool's answer may depend on which tool was asked first. The returned
    mapping is keyed rather than ordered, so a varied call order changes what
    happened without changing what is compared.
    """
    documents: dict[str, Any] = {}
    advertised = order if order is not None else tool_names(list_tools(server, era))
    # A *payload* resource rather than the catalog, so `standard_read`'s
    # declaration slot is non-null and the golden below has something to be exact
    # about.
    arguments = call_arguments(repo, read_uri=payload_uri)
    for name in advertised:
        frame = call_tool(server, era, name=name, arguments=arguments[name])
        documents[name] = structured(server, frame, label=name)
    documents[CATALOG_READ] = metadata_document(server, era, CATALOG_URI)
    documents[PAYLOAD_READ] = read_one(server, era, payload_uri)
    return documents


def masked(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Every document with DR-008's one excluded field masked, and nothing else.

    ``without_diagnostics`` is T9's positional mask — the top-level ``diagnostics``
    of each entry in a ``results`` array — and it passes any document without that
    array through untouched, so applying it everywhere masks exactly the provider
    results and nothing else.
    """
    return {
        name: without_diagnostics(as_object(document, name)) for name, document in documents.items()
    }


def time_shaped_leaves(documents: Mapping[str, Any]) -> list[tuple[str, str, object]]:
    """Every leaf whose *name* or *value* looks like a timestamp or a duration."""
    offenders: list[tuple[str, str, object]] = []
    for surface, document in documents.items():
        for location, value in json_leaves(document):
            field = location.rsplit(".", 1)[-1].split("[", 1)[0].lower()
            if any(token in field for token in TIME_TOKEN_EXEMPT):
                continue
            named = any(
                token == field or field.endswith(f"_{token}") for token in TIME_FIELD_TOKENS
            )
            if named or (isinstance(value, str) and ISO_INSTANT.search(value)):
                offenders.append((surface, location, value))
    return offenders


def absolute_path_leaves(
    documents: Mapping[str, Any], *, roots: tuple[Path, ...]
) -> list[tuple[str, str, object]]:
    """Every leaf carrying an absolute path or a fixture root DR-009 forbids on the wire."""
    needles = tuple(str(root) for root in roots)
    offenders: list[tuple[str, str, object]] = []
    for surface, document in documents.items():
        for location, value in json_leaves(document):
            if not isinstance(value, str):
                continue
            if value.startswith("/") or any(needle in value for needle in needles):
                offenders.append((surface, location, value))
    return offenders


def reverse_materialized(source: Path, destination: Path) -> Path:
    """The same tree, byte for byte, with its entries created in reverse order.

    Directory-entry order is creation order on the filesystems this suite runs on,
    so a server whose output followed ``os.scandir`` anywhere would answer
    differently here while every declared fact stayed identical. Symlinks are
    recreated rather than followed, because the fixture runtime links the real
    adapter code in and copying it would serve a different distribution.
    """
    destination.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir(), reverse=True):
        target = destination / entry.name
        if entry.is_symlink():
            target.symlink_to(entry.readlink())
        elif entry.is_dir():
            reverse_materialized(entry, target)
        else:
            shutil.copy2(entry, target)
    return destination


@pytest.fixture(scope="module")
def unordered_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture catalog whose ``validate`` set includes the hash-seed canary."""
    return build_hazard_runtime(tmp_path_factory.mktemp("determinism"), (DETERMINISM_HAZARD,))


@pytest.fixture(scope="module")
def mirrored_runtime(unordered_runtime: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The same distribution at a different absolute path, materialized in reverse order."""
    destination = tmp_path_factory.mktemp("determinism-mirror") / "runtime"
    return reverse_materialized(unordered_runtime, destination)


@pytest.fixture(scope="module")
def determinism_repo(unordered_runtime: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One planned consumer repository against the canary distribution."""
    return planned_consumer_repo(unordered_runtime, tmp_path_factory.mktemp("determinism-repo"))


@pytest.fixture(scope="module")
def payload_uri(unordered_runtime: Path) -> str:
    """One declared payload resource URI, used by every ``standard_read`` call here."""
    catalog = oracle_facade(unordered_runtime).catalog()
    declared = declared_resources(catalog)
    assert declared, "the fixture catalog declares no payload resource"
    return next(iter(declared))


def _capture(
    runtime: Path, repo: Path, payload: str, *, era: Era, label: str, seed: str, reverse: bool
) -> dict[str, Any]:
    """One complete stable-document set, under a chosen hash seed and call order."""
    previous = os.environ.get("PYTHONHASHSEED")
    os.environ["PYTHONHASHSEED"] = seed
    try:
        with resource_session(era, runtime_root=runtime, label=label, script=CLI_LAUNCH) as (
            server,
            _opened,
        ):
            names = tool_names(list_tools(server, era))
            # The call order within a session is semantically unordered: no tool's
            # answer may depend on which tool was asked first.
            order = list(reversed(names)) if reverse else list(names)
            documents = stable_documents(server, era, repo, payload, order=order)
            assert set(documents) >= set(names), "the capture missed an advertised tool"
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)
            return documents
    finally:
        if previous is None:
            os.environ.pop("PYTHONHASHSEED", None)
        else:
            os.environ["PYTHONHASHSEED"] = previous


def expected_projections(runtime: Path, repo: Path, payload: str) -> dict[str, Any]:
    """An independent expected document for **every** stable surface (review F2).

    Each oracle is built from an authority other than the adapter under test:
    ``catalog_projection`` is written from FR-001's own sentence, ``dumped`` is the
    §5.5 facade's projection, and the ``standard_read`` and payload-read shapes are
    assembled from the declared ``ResourceDescriptor`` the catalog carries. The
    T10.1 revision skipped ``standards_list`` outright and left ``standard_read``,
    ``reconcile_preview``, and the catalog read with no oracle at all, which is
    partial coverage presented as closure.
    """
    facade = oracle_facade(runtime)
    catalog = facade.catalog()
    descriptor = declared_resources(catalog)[payload]
    declaration = descriptor.model_dump(mode="json")
    content = facade.resource(
        descriptor.standard_id, descriptor.package_version, descriptor.resource_id
    )
    projection = catalog_projection(catalog)
    return {
        STANDARDS_LIST: projection,
        CATALOG_READ: projection,
        STANDARD_READ: {
            "uri": descriptor.uri,
            "media_type": descriptor.media_type,
            "declaration": declaration,
        },
        PAYLOAD_READ: {
            "uri": descriptor.uri,
            "mimeType": descriptor.media_type,
            "text": content.data.decode("utf-8"),
            "_meta": {"dev.project-standards/declaration": declaration},
        },
        REPO_INSPECT: dumped(facade.inspect_repo(repo)),
        RECONCILE_PREVIEW: {
            PREVIEW_SLOT: dumped(facade.reconcile(repo)),
            CONTROL_PLANE_SLOT: None,
        },
        VALIDATE_REPO: dumped(facade.validate_repo(repo)),
        DRIFT_CHECK: dumped(facade.drift_check(repo)),
    }


# -- RED control ---------------------------------------------------------------


def test_determinism_probe_detects_an_unstable_document() -> None:
    """RED control: the comparison and the scanners are not vacuous.

    Deliberately green, and deliberately negative: it feeds the machinery the
    acceptance tests rely on a document that *is* unstable — in **key order**, not
    only in list order — one that carries a timestamp, and one that carries an
    absolute path, and requires each to be caught. The key-order case is the one
    the T10.1 revision could not see at all (review F1).
    """
    assert wire({"a": 1, "b": 2}) != wire({"b": 2, "a": 1}), (
        "the comparison cannot see a reversed dictionary, which is exactly the seed-dependent "
        "variance TC-T10-002 exists to catch"
    )
    assert {"a": 1, "b": 2} == {"b": 2, "a": 1}, (
        "structural equality is order-insensitive by definition; the wire comparison above is "
        "what carries the ordering claim"
    )
    assert wire({"tools": ["one", "two"]}) != wire({"tools": ["two", "one"]}), (
        "the comparison ignores sequence order"
    )

    timed = {"report": {"finished_at": "2026-07-30T11:00:00Z", "id": "alpha"}}
    caught = time_shaped_leaves(timed)
    assert [location for _surface, location, _value in caught] == ["$.finished_at"], (
        f"the timestamp scanner missed a named time field: {caught}"
    )
    assert time_shaped_leaves({"report": {"note": "run at 2026-07-30T11:00:00"}}), (
        "the timestamp scanner missed an instant-shaped value"
    )
    exempt = {"report": {"schema_version": "1.0", "package_version": "2.0", "runtime": "worker"}}
    assert not time_shaped_leaves(exempt), (
        f"the timestamp scanner flags identity fields: {time_shaped_leaves(exempt)}"
    )

    assert absolute_path_leaves({"snapshot": {"path": "/tmp/fixture/README.md"}}, roots=()), (
        "the path scanner missed an absolute path"
    )
    rooted = {"snapshot": {"path": "sub/README.md"}}
    assert not absolute_path_leaves(rooted, roots=(Path("/nowhere"),)), (
        "the path scanner flags a root-relative path"
    )
    assert absolute_path_leaves(rooted, roots=(Path("sub"),)), (
        "the path scanner ignores a leaked fixture root"
    )

    masked_pair = masked({VALIDATE_REPO: {"repo_root": ".", "results": [], "findings": []}})
    assert masked_pair[VALIDATE_REPO]["repo_root"] == ".", (
        f"the DR-008 mask altered a field outside its one exclusion: {masked_pair}"
    )


# -- acceptance ----------------------------------------------------------------


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_semantically_unordered_inputs_have_identical_stable_output(
    unordered_runtime: Path,
    mirrored_runtime: Path,
    determinism_repo: Path,
    payload_uri: str,
    era: Era,
) -> None:
    """TC-T10-002 (NFR-005): four unordered inputs, one stable answer, both eras.

    The baseline session and the varied session differ in every input NFR-005 says
    must not matter and in nothing that it says must:

    * a different ``PYTHONHASHSEED``, which reorders every set and every
      set-derived dict in the server process *and* in each provider worker — the
      cross-process half T3's review deferred here by name;
    * a different absolute path for the installed distribution;
    * a different filesystem entry order, because the mirror materializes the same
      bytes in reverse;
    * a different order of tool calls within the session.

    Everything declared is identical: the same catalog, the same payload bytes, the
    same consumer repository. The comparison is the **order-preserving** rendering
    with exactly DR-008's one exclusion masked, so a difference in key sequence
    fails rather than being sorted away (review F1), and so does a difference in
    any value.

    Run in both eras because the two connections serve the same documents through
    different envelopes, and a normalization applied on only one path would
    otherwise be invisible (review F13).
    """
    require_mcp_subcommand()
    baseline = _capture(
        unordered_runtime,
        determinism_repo,
        payload_uri,
        era=era,
        label="determinism-a",
        seed=HASH_SEEDS[0],
        reverse=False,
    )
    varied = _capture(
        mirrored_runtime,
        determinism_repo,
        payload_uri,
        era=era,
        label="determinism-b",
        seed=HASH_SEEDS[1],
        reverse=True,
    )

    assert set(baseline) == set(varied), (
        f"the two sessions served different surfaces: {sorted(set(baseline) ^ set(varied))}"
    )
    left = masked(baseline)
    right = masked(varied)
    for surface in sorted(left):
        assert wire(left[surface]) == wire(right[surface]), (
            f"{surface} is not deterministic across hash seed, install path, filesystem order, "
            f"and call order.\nseed {HASH_SEEDS[0]}: {wire(left[surface])}\n"
            f"seed {HASH_SEEDS[1]}: {wire(right[surface])}"
        )

    canary = as_object(left.get(VALIDATE_REPO), VALIDATE_REPO)
    assert DETERMINISM_HAZARD in wire(canary), (
        "the hash-seed canary provider never ran, so the comparison above proves nothing about "
        f"cross-process ordering: {wire(canary)[:400]}"
    )
    results = as_array(canary.get("results"), "the validate_repo results")
    ran = [
        cast("dict[str, Any]", entry)
        for entry in results
        if isinstance(entry, dict)
        and DETERMINISM_HAZARD in str(cast("dict[str, object]", entry).get("provider_id"))
    ]
    assert ran, f"the canary provider produced no result entry: {wire(results)[:400]}"


def test_only_declared_normalization_is_allowed(
    unordered_runtime: Path, determinism_repo: Path, payload_uri: str
) -> None:
    """TC-T10-004 (DR-009): the normalization contract is closed, on every surface.

    Four properties, in the order DR-009 states them.

    *Stable fields compare verbatim, everywhere.* Every wire document equals an
    independently constructed expectation — the FR-001 discovery projection written
    from the spec sentence, the §5.5 facade projections, and the declared
    ``ResourceDescriptor`` for both read paths — with no sort, round, rename, or
    rewrite applied by the adapter. Nothing is skipped and nothing is checked only
    for non-nullity, which is what makes this closure rather than sampling (review
    F2). It is also what makes the exclusion list *closed*: an implementation that
    normalized a second field to make a golden pass would break equality here.

    *Filesystem paths are root-relative.* No leaf may be an absolute path or carry
    the fixture's own root, which is the form in which a consumer's directory
    layout would otherwise reach a client.

    *Timestamps and durations are excluded rather than rewritten.* No leaf may be
    named like one or shaped like one — a rewritten instant is still an instant, so
    this is a presence check rather than a stability check.

    *The declared exclusion is exactly one field.* DR-008 names
    ``ProviderOperationResult.diagnostics`` and nothing else, and every equality
    above is asserted with only that mask applied.

    Modern-only by the reviewer's own scoping: the documents compared here are
    protocol-neutral state carried inside the larger envelope, and the
    era-divergent halves — refusal codes and ``isError`` behaviour — are
    parameterized in ``test_protocol_conformance``.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    documents = _capture(
        unordered_runtime,
        determinism_repo,
        payload_uri,
        era=era,
        label="normalization",
        seed=HASH_SEEDS[0],
        reverse=False,
    )
    expected = expected_projections(unordered_runtime, determinism_repo, payload_uri)
    assert set(expected) == set(documents), (
        "every captured surface needs an independent oracle and every oracle needs a captured "
        f"surface: {sorted(set(expected) ^ set(documents))}"
    )
    for surface in sorted(expected):
        served = as_object(documents[surface], surface)
        want = as_object(expected[surface], surface)
        if surface in (VALIDATE_REPO, DRIFT_CHECK):
            served = without_diagnostics(served)
            want = without_diagnostics(want)
        assert served == want, (
            f"{surface} does not publish its authoritative projection verbatim, so a "
            f"normalization outside DR-009's list has been applied.\nwire:   {wire(served)}\n"
            f"oracle: {wire(want)}"
        )

    preview = as_object(documents[RECONCILE_PREVIEW], RECONCILE_PREVIEW)
    assert preview.get(PREVIEW_SLOT) is not None, (
        "the fixture repository produced no preview, so the assertions above never reached the "
        "plan document at all"
    )

    stable = masked(documents)
    timed = time_shaped_leaves(stable)
    assert not timed, (
        f"DR-009 excludes timestamps and durations from the stable result; these leaves carry "
        f"one: {timed}"
    )
    absolute = absolute_path_leaves(
        stable, roots=(unordered_runtime, determinism_repo, determinism_repo.parent)
    )
    assert not absolute, (
        f"DR-009 requires root-relative filesystem paths; these leaves are absolute or leak a "
        f"fixture root: {absolute}"
    )
    snapshot = as_object(stable[REPO_INSPECT], REPO_INSPECT)
    assert snapshot.get("repo_root") == ".", (
        f"the normalized root identity must serialize as '.': {snapshot.get('repo_root')!r}"
    )

    assert DECLARED_EXCLUSIONS == ("ProviderOperationResult.diagnostics",), (
        "the declared exclusion list changed; DR-008 names one field, and widening it needs a "
        "record amendment rather than a test edit"
    )
