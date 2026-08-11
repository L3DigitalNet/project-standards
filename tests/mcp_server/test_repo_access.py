"""Explicit-root resolution and boundary narrowing in the adapter (T5).

Covers TC-T5-007 (client roots constrain eligibility but never replace, widen,
or redirect the explicit effective root) together with FR-024, IR-005, and
IR-007.

The contract is fixed in three places and this suite may not soften any of them:

*§5.5* (amended 2026-07-29) — ``resolve_effective_root`` takes an explicit
``repo_root`` plus the optional keyword-only boundary inputs
``configured_boundary`` (the ADR 0026 launch-time boundary) and ``client_roots``
(client-advertised roots), both defaulting to none, and returns "the normalized,
symlink-resolved explicit root after containment validation". Its last sentence
is the whole security property: "client roots may reject an input but never
replace a missing ``repo_root``, select a different repository, or widen the
boundary."

*ADR 0026* (``adr-0026-mcp-local-read-only-transport.md``),
root rules — the explicit argument is "the authoritative repository identity for
that call"; advertised roots "may only validate or narrow containment". The
optional configured launch-time boundary "narrows containment exactly as
client-advertised roots do", which is why every narrowing assertion below is
applied to both inputs rather than to the client one alone.

*T3's already-frozen root class* — a relative root, a nonexistent root, a
non-directory root, a root carrying parent-directory segments, and an
unresolvable root are all refused, while a symlinked root that resolves inside
the boundary is accepted and yields the resolved path. T5 inherits that class
unchanged and adds containment on top of it; the adapter's resolver may be
stricter than the T3 service resolver, never looser.

Error-code *spellings* are deliberately not frozen. What is asserted is what the
contract requires: the repo_root-rejection class shares one stable non-empty
code, exactly as T3 ratified for the same class, so the two services cannot fork
a taxonomy for one concept; each boundary rejection is independently structured
and stable, with no invented cross-source equality or inequality (T5.2 Codex
review F4). Every rejection must be a ``ServiceError`` — a raw ``TypeError`` or
``ValueError`` is a failure here, because plan:373 maps every root error onto
the structured type and an unstructured one gives a client nothing to render
(review F5).
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import os
import stat
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ADAPTER_PACKAGE = "project_standards.mcp_server"

# Frozen by §5.5 as amended 2026-07-29 (T5 RED review F3): the explicit input
# and the two optional keyword-only boundary inputs are documented behavior.
FROZEN_ROOT_PARAMETER = "repo_root"
FROZEN_CONFIGURED_PARAMETER = "configured_boundary"
FROZEN_CLIENT_PARAMETER = "client_roots"
BOUNDARY_PARAMETERS = (FROZEN_CONFIGURED_PARAMETER, FROZEN_CLIENT_PARAMETER)

# Every root-input class T3 already froze, reused here unchanged.
MALFORMED_ROOT_CASES = (
    "nonexistent",
    "file-as-root",
    "traversal",
    "dangling-symlink",
    "symlink-to-file",
    "relative",
    "embedded-nul",
)

# Boundary *values* that are themselves unusable. A boundary that cannot be
# resolved must never be silently ignored: ignoring it would turn a narrowing
# input into a no-op, which is the quietest possible way to widen authority.
MALFORMED_BOUNDARY_CASES = (
    "relative",
    "traversal",
    "dangling-symlink",
    "file-as-boundary",
    "embedded-nul",
)

# A NUL byte is a legal JSON string character, so a protocol client can send one
# on any path argument. `Path.resolve(strict=True)` answers it with `ValueError`,
# not `OSError` — the one input class that escaped the first implementation's
# translation (T5.4 Codex GREEN review, F2). Kept as a module constant so the
# root, the configured boundary, and the client roots all use the same value.
NUL_PATH = "/tmp/embedded\x00null"


def require_adapter_module(name: str) -> ModuleType:
    """Import one planned adapter module, or fail as an explicit RED assertion."""
    dotted = f"{ADAPTER_PACKAGE}.{name}"
    try:
        spec = importlib.util.find_spec(dotted)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        f"planned module {dotted} is absent; the T5 root boundary does not exist yet"
    )
    return importlib.import_module(dotted)


def require_resolver() -> Any:
    module = require_adapter_module("repo_access")
    assert hasattr(module, "resolve_effective_root"), (
        "planned §5.5 function resolve_effective_root is absent; "
        "the T5 root boundary does not exist yet"
    )
    return module.resolve_effective_root


def service_error() -> type[Exception]:
    """The structured failure type the adapter must reuse, never re-invent.

    Plan T5 requires every startup and root error to map to ``ServiceError``.
    The adapter is allowed to import the service layer; the reverse direction is
    what the import-boundary contract forbids.
    """
    from project_standards.mcp_services import ServiceError

    return ServiceError


def build_repo(root: Path) -> Path:
    """Create a plausible consumer repository directory."""
    root.mkdir(parents=True)
    (root / ".standards").mkdir()
    (root / ".standards/config.toml").write_text('schema_version = "1.0"\n', encoding="utf-8")
    return root


def malformed_roots(tmp_path: Path, repo: Path) -> dict[str, Path]:
    """Build every root input class the resolver must refuse before containment."""
    file_root = tmp_path / "file-root.txt"
    file_root.write_text("not a repository\n", encoding="utf-8")
    dangling = tmp_path / "dangling-root"
    if not dangling.is_symlink():
        dangling.symlink_to(tmp_path / "does-not-exist", target_is_directory=True)
    file_link = tmp_path / "file-link-root"
    if not file_link.is_symlink():
        file_link.symlink_to(file_root)
    return {
        "nonexistent": tmp_path / "no-such-repository",
        "file-as-root": file_root,
        "traversal": repo / ".." / repo.name,
        "dangling-symlink": dangling,
        "symlink-to-file": file_link,
        "relative": Path(repo.name),
        "embedded-nul": Path(NUL_PATH),
    }


def malformed_boundaries(tmp_path: Path, workspace: Path) -> dict[str, Path]:
    """Boundary values that are themselves unusable (review F9)."""
    boundary_file = tmp_path / "boundary-file.txt"
    boundary_file.write_text("not a directory\n", encoding="utf-8")
    dangling = tmp_path / "dangling-boundary"
    if not dangling.is_symlink():
        dangling.symlink_to(tmp_path / "does-not-exist", target_is_directory=True)
    return {
        "relative": Path(workspace.name),
        "traversal": workspace / ".." / workspace.name,
        "dangling-symlink": dangling,
        "file-as-boundary": boundary_file,
        "embedded-nul": Path(NUL_PATH),
    }


def error_fields(error: Any) -> dict[str, str]:
    """Return every public string field of one structured service error."""
    return {
        name: str(getattr(error, name, None) or "")
        for name in ("code", "message", "remediation", "path", "standard_id", "version", "severity")
    }


def assert_structured_rejection(error: Any, rejected: object, tmp_path: Path) -> str:
    """Assert the §5.5 error shape and content safety; return the stable code."""
    fields = error_fields(error)
    assert fields["code"], "a rejection must carry a stable non-empty code"
    assert fields["code"].strip() == fields["code"]
    assert fields["message"], "a rejection must carry a message"
    assert fields["remediation"], "a rejection must carry remediation"
    assert fields["severity"] == "error"
    path = getattr(error, "path", None)
    assert path is None or not Path(path).is_absolute(), (
        f"a rejection must not publish an absolute path, got {path!r}"
    )
    # An empty or bare-"." input carries no information to leak, and "." would
    # match every sentence that ends in a full stop, so the echo check applies
    # only to inputs that actually name something.
    echoed = str(rejected) if rejected not in (None, "", Path()) else ""
    for name, value in fields.items():
        assert str(tmp_path) not in value, f"{name} echoed the temporary tree: {value!r}"
        if echoed:
            assert echoed not in value, f"{name} echoed the rejected input: {value!r}"
    return fields["code"]


def rejection_code(resolver: Any, errors: type[Exception], tmp_path: Path, **call: Any) -> str:
    """Refuse one call, assert its structure, and prove the code is stable.

    Stability is checked by repeating the identical call: a code that varied
    between two identical inputs would not be something a client could branch
    on, and that is the property the unfrozen spellings still have to have.
    """
    with pytest.raises(errors) as first:
        resolver(**call)
    code = assert_structured_rejection(first.value, call.get("repo_root"), tmp_path)
    with pytest.raises(errors) as second:
        resolver(**call)
    assert error_fields(second.value)["code"] == code, "the rejection code is not stable"
    return code


def tree_state(root: Path) -> dict[str, tuple[int, int, str, str, int, int]]:
    """Snapshot type, mode, link target, content digest, inode, and change time.

    Content and inode/change-time evidence are both required (review F12, and
    the same oracle T4's F17 disposition settled on): mode and link target alone
    would let a rewritten ``config.toml`` pass, and a digest alone would let a
    rewrite-then-restore pass. Unprivileged code cannot forge ``st_ctime_ns``.
    """
    state: dict[str, tuple[int, int, str, str, int, int]] = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        is_link = stat.S_ISLNK(info.st_mode)
        target = str(path.readlink()) if is_link else ""
        digest = ""
        if not is_link and stat.S_ISREG(info.st_mode):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        state[str(path.relative_to(root))] = (
            stat.S_IFMT(info.st_mode),
            stat.S_IMODE(info.st_mode),
            target,
            digest,
            info.st_ino,
            info.st_ctime_ns,
        )
    return state


def narrowed(resolver: Any, repo_root: Any, *, parameter: str, boundary: Path | None) -> Path:
    """Call the resolver with one boundary supplied through the named parameter.

    The configured boundary is a single path and the client-advertised set is a
    sequence, which is the only shape difference between the two inputs; ADR
    0026 makes their *effect* identical, so every narrowing oracle in this file
    runs against both.
    """
    if boundary is None:
        return resolver(repo_root)
    if parameter == FROZEN_CLIENT_PARAMETER:
        return resolver(repo_root, **{parameter: (boundary,)})
    return resolver(repo_root, **{parameter: boundary})


def test_resolve_effective_root_signature_is_the_frozen_boundary_shape() -> None:
    """§5.5 (amended 2026-07-29): one mandatory explicit root, two optional boundaries.

    The shape is the security-relevant part: a boundary that were mandatory
    would make the server unusable against Codex CLI 0.145.0, which advertises
    no roots, and a boundary that could be passed positionally in the root's
    place would make "never replace a missing ``repo_root``" unenforceable.
    """
    resolver = require_resolver()
    parameters = list(inspect.signature(resolver).parameters.values())
    assert parameters, "resolve_effective_root must accept the explicit repository root"
    assert parameters[0].name == FROZEN_ROOT_PARAMETER
    assert parameters[0].default is inspect.Parameter.empty, (
        "the explicit repo_root is mandatory (FR-024); it may not default to anything"
    )
    optional = {parameter.name: parameter for parameter in parameters[1:]}
    assert set(optional) == set(BOUNDARY_PARAMETERS), (
        f"expected the two §5.5 boundary inputs, got {sorted(optional)}"
    )
    for name, parameter in optional.items():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (
            f"{name} must be keyword-only so it can never be mistaken for the explicit root"
        )
        assert parameter.default is None, f"{name} must default to no boundary at all"


def test_client_roots_only_narrow_explicit_root(tmp_path: Path) -> None:
    """TC-T5-007 (FR-024, IR-007): advertised roots reject, they never redirect.

    Four separable claims, each of which a plausible wrong implementation would
    break: a contained root resolves to exactly the value it resolves to with no
    boundary at all (never to the boundary); a root outside every advertised
    boundary is refused; a root contained in *any one* advertised boundary is
    accepted; and an advertised boundary that names a different repository never
    changes which repository is returned.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    inside = build_repo(workspace / "consumer")
    nested = build_repo(workspace / "consumer/nested")
    outside = build_repo(tmp_path / "elsewhere/other-consumer")
    other_workspace = tmp_path / "other-workspace"
    other_workspace.mkdir()

    unbounded = resolver(inside)
    assert unbounded == inside.resolve(strict=True)

    # Narrowing that accepts must not alter identity.
    assert resolver(inside, client_roots=(workspace,)) == unbounded
    assert resolver(nested, client_roots=(workspace,)) == nested.resolve(strict=True)
    # The boundary itself may be the root.
    assert resolver(inside, client_roots=(inside,)) == unbounded
    # Contained in any one of several advertised roots is enough.
    assert resolver(inside, client_roots=(other_workspace, workspace)) == unbounded

    # Narrowing that rejects must reject, not substitute.
    rejection_code(resolver, errors, tmp_path, repo_root=outside, client_roots=(workspace,))
    rejection_code(resolver, errors, tmp_path, repo_root=inside, client_roots=(other_workspace,))
    rejection_code(resolver, errors, tmp_path, repo_root=inside, client_roots=())

    # An advertised root that *is* a different repository never redirects.
    rejection_code(resolver, errors, tmp_path, repo_root=outside, client_roots=(inside,))


def test_configured_boundary_narrows_exactly_like_client_roots(tmp_path: Path) -> None:
    """ADR 0026: the launch-time boundary and advertised roots have one semantics.

    Asserted as an equivalence over the same inputs rather than as two separate
    behaviours, so a future implementation cannot let one of the two inputs
    drift into a different containment rule. Only the accept/reject *outcome* is
    compared — the review's F4 disposition forbids requiring the two sources to
    share (or to avoid sharing) an error code.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    inside = build_repo(workspace / "consumer")
    outside = build_repo(tmp_path / "elsewhere/other-consumer")

    for boundary, candidate, accepted in (
        (workspace, inside, True),
        (inside, inside, True),
        (workspace, outside, False),
        (outside, inside, False),
    ):
        outcomes: list[Any] = []
        for parameter in BOUNDARY_PARAMETERS:
            try:
                outcomes.append(
                    narrowed(resolver, candidate, parameter=parameter, boundary=boundary)
                )
            except errors:
                outcomes.append("refused")
        assert outcomes[0] == outcomes[1], (
            f"{FROZEN_CONFIGURED_PARAMETER} and {FROZEN_CLIENT_PARAMETER} disagreed for "
            f"boundary={boundary} candidate={candidate}: {outcomes}"
        )
        if accepted:
            assert outcomes[0] == candidate.resolve(strict=True)
        else:
            assert outcomes[0] == "refused"


def test_boundaries_never_replace_a_missing_repo_root(tmp_path: Path) -> None:
    """§5.5: a boundary is not a default. No explicit root, no result.

    The dangerous failure this forbids is silent: a server that fell back to the
    advertised root, the configured boundary, or the process working directory
    would inspect a repository the caller never named, and every later
    containment check would still pass.

    The refusal must be a structured ``ServiceError`` with populated fields. A
    raw ``TypeError`` or ``ValueError`` fails here (review F5).
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    inside = build_repo(workspace / "consumer")

    for empty in (None, "", Path()):
        for parameter in BOUNDARY_PARAMETERS:
            with pytest.raises(errors) as refused:
                narrowed(resolver, empty, parameter=parameter, boundary=workspace)
            assert_structured_rejection(refused.value, empty, tmp_path)
        with pytest.raises(errors) as bare:
            resolver(empty)
        assert_structured_rejection(bare.value, empty, tmp_path)

    # The boundary must never surface as a result under either spelling.
    assert resolver(inside, configured_boundary=workspace) != workspace.resolve(strict=True)
    assert resolver(inside, client_roots=(workspace,)) != workspace.resolve(strict=True)


def test_boundaries_never_widen_an_otherwise_rejected_root(tmp_path: Path) -> None:
    """§5.5/IR-007: adding a boundary is monotonically restrictive.

    Stated as a property over a matrix rather than as a list of cases: for every
    candidate root, supplying any boundary may turn an acceptance into a
    rejection but may never turn a rejection into an acceptance, and may never
    change the value of an acceptance. That single property covers "never
    widen", "never select a different repository", and the T3 malformed-root
    class at once, including boundaries that contain a path the resolver refuses
    for reasons that have nothing to do with containment.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    repo = build_repo(workspace / "consumer")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    candidates: dict[str, Any] = {"valid": repo, **malformed_roots(tmp_path, repo)}
    boundaries = (workspace, tmp_path, repo, elsewhere)

    for label, candidate in candidates.items():
        try:
            baseline: Path | None = resolver(candidate)
        except errors:
            baseline = None
        for boundary in boundaries:
            for parameter in BOUNDARY_PARAMETERS:
                try:
                    bounded = narrowed(resolver, candidate, parameter=parameter, boundary=boundary)
                except errors:
                    continue
                assert baseline is not None, (
                    f"{label} is refused without a boundary but accepted with "
                    f"{parameter}={boundary}: a boundary widened authority"
                )
                assert bounded == baseline, (
                    f"{label} resolved to {bounded} with {parameter}={boundary} but to "
                    f"{baseline} without it: a boundary changed the selected repository"
                )


@pytest.mark.parametrize("case", MALFORMED_ROOT_CASES)
def test_malformed_explicit_roots_are_refused_structurally(tmp_path: Path, case: str) -> None:
    """FR-024/IR-005: the T3 root class is inherited unchanged by the adapter.

    Each class is exercised on its own so a resolver that happens to reject the
    whole set through one over-broad check still has to reject each one, and so
    a regression names the class it broke.
    """
    resolver = require_resolver()
    errors = service_error()
    repo = build_repo(tmp_path / "consumer")
    hostile = malformed_roots(tmp_path, repo)[case]

    rejection_code(resolver, errors, tmp_path, repo_root=hostile)


@pytest.mark.parametrize("case", MALFORMED_BOUNDARY_CASES)
@pytest.mark.parametrize("parameter", BOUNDARY_PARAMETERS)
def test_malformed_boundary_values_are_refused_structurally(
    tmp_path: Path, case: str, parameter: str
) -> None:
    """IR-007 (review F9): an unusable boundary is refused, never ignored.

    A relative, traversing, dangling, or non-directory boundary cannot decide
    containment. Silently dropping it would turn the one narrowing input the
    launch surface exposes into a no-op — the quietest possible way to widen
    authority — so the whole call must fail even though the *root* is perfectly
    valid, which the first assertion establishes. Each rejection is asserted
    independently: nothing requires the boundary classes to share a code with
    each other or with the root class (review F4).
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    repo = build_repo(workspace / "consumer")
    assert resolver(repo) == repo.resolve(strict=True), "the root itself must be valid"
    boundary = malformed_boundaries(tmp_path, workspace)[case]

    with pytest.raises(errors) as refused:
        narrowed(resolver, repo, parameter=parameter, boundary=boundary)
    code = assert_structured_rejection(refused.value, boundary, tmp_path)
    with pytest.raises(errors) as again:
        narrowed(resolver, repo, parameter=parameter, boundary=boundary)
    assert error_fields(again.value)["code"] == code, "the rejection code is not stable"


def test_nul_bearing_path_inputs_are_structured_refusals(tmp_path: Path) -> None:
    """NFR-004/plan:373 (review F2): a NUL byte never escapes as a raw exception.

    An embedded NUL is a legal JSON string character, so it can reach any path
    argument straight off the protocol wire. ``Path.resolve(strict=True)``
    answers it with ``ValueError`` rather than ``OSError``, which is exactly the
    class an ``OSError``-only translation lets through — and a raw ``ValueError``
    carries no stable code and no remediation, so a client sees an unhandled
    crash instead of a refusal it can act on.

    All three inputs are exercised, including a client-root *set* whose poisoned
    element is not the first: a resolver that validated only the head of the
    sequence would pass every other case in this file.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    repo = build_repo(workspace / "consumer")
    poisoned = Path(NUL_PATH)

    for call in (
        {"repo_root": poisoned},
        {"repo_root": repo, "configured_boundary": poisoned},
        {"repo_root": repo, "client_roots": (poisoned,)},
        {"repo_root": repo, "client_roots": (workspace, poisoned)},
        {"repo_root": poisoned, "configured_boundary": workspace},
    ):
        with pytest.raises(errors) as refused:
            resolver(**call)
        assert_structured_rejection(refused.value, poisoned, tmp_path)


def test_repo_root_rejection_class_shares_one_stable_code(tmp_path: Path) -> None:
    """NFR-004 + T3 parity: one repository-root rejection class, one stable code.

    T3 ratified exactly this for exactly this class (nonexistent, non-directory,
    traversal, unresolvable, relative), so forking the taxonomy between the
    service resolver and the adapter resolver for one concept would itself be
    drift. The literal spelling stays unfrozen — no binding document defines it
    — and no constraint is placed on how boundary rejection codes relate to this
    one or to each other (review F4).
    """
    resolver = require_resolver()
    errors = service_error()
    repo = build_repo(tmp_path / "consumer")

    codes = {
        rejection_code(resolver, errors, tmp_path, repo_root=hostile)
        for hostile in malformed_roots(tmp_path, repo).values()
    }
    assert len(codes) == 1, f"the repo_root-rejection class must share one code: {codes}"
    assert codes != {""}


def test_boundary_containment_rejections_are_independently_structured(tmp_path: Path) -> None:
    """IR-007/NFR-004: each containment refusal is structured and stable on its own.

    Deliberately asserts nothing about how the two boundary sources' codes
    relate: no document defines a taxonomy, so requiring them to match — or to
    differ — would freeze an invention (review F4). What a client can rely on is
    that one input always produces one code, with populated fields and no leaked
    path.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    build_repo(workspace / "consumer")
    outside = build_repo(tmp_path / "elsewhere/other")

    for parameter in BOUNDARY_PARAMETERS:
        for boundary in (workspace, workspace / "consumer"):
            with pytest.raises(errors) as refused:
                narrowed(resolver, outside, parameter=parameter, boundary=boundary)
            code = assert_structured_rejection(refused.value, outside, tmp_path)
            with pytest.raises(errors) as again:
                narrowed(resolver, outside, parameter=parameter, boundary=boundary)
            assert error_fields(again.value)["code"] == code


def test_safe_in_bound_symlinked_root_is_accepted_and_resolved(tmp_path: Path) -> None:
    """T3 precedent: symlink resolution is normalization, not a categorical refusal.

    The stop/backtrack rule forbids rejecting a safe symlinked root outright, so
    a link that resolves inside the boundary must be accepted and must return
    the resolved path — which is also what makes the escape cases below
    decidable on resolved paths rather than on spelling. A symlinked *boundary*
    that resolves to a real containing directory is equally safe.
    """
    resolver = require_resolver()
    workspace = tmp_path / "workspace"
    repo = build_repo(workspace / "consumer")
    link = workspace / "consumer-link"
    link.symlink_to(repo, target_is_directory=True)

    resolved = repo.resolve(strict=True)
    assert resolver(link) == resolved
    assert resolver(link, configured_boundary=workspace) == resolved
    assert resolver(link, client_roots=(workspace,)) == resolved

    workspace_link = tmp_path / "workspace-link"
    workspace_link.symlink_to(workspace, target_is_directory=True)
    assert resolver(repo, configured_boundary=workspace_link) == resolved
    assert resolver(repo, client_roots=(workspace_link,)) == resolved

    # Trailing separators and redundant current-directory segments normalize away.
    assert resolver(Path(f"{repo}{os.sep}")) == resolved
    assert resolver(Path(f"{repo}{os.sep}.")) == resolved


def test_symlinked_root_that_escapes_the_boundary_is_refused(tmp_path: Path) -> None:
    """IR-007: containment is decided after symlink resolution, never before.

    A link that lives inside the advertised boundary but points outside it is
    the escape the rule exists for. A resolver that compared the *given* path
    would accept it, inspect a repository the client never advertised, and still
    report a contained root.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = build_repo(tmp_path / "elsewhere/secret-consumer")
    escape = workspace / "looks-contained"
    escape.symlink_to(outside, target_is_directory=True)

    for parameter in BOUNDARY_PARAMETERS:
        with pytest.raises(errors) as refused:
            narrowed(resolver, escape, parameter=parameter, boundary=workspace)
        error = refused.value
        assert_structured_rejection(error, escape, tmp_path)
        for value in error_fields(error).values():
            assert str(outside) not in value, "the escape target leaked into the rejection"
            assert "secret-consumer" not in value


def test_symlinked_client_boundary_cannot_escape_the_configured_boundary(tmp_path: Path) -> None:
    """IR-007 (review F9): an advertised root cannot tunnel out of the launch boundary.

    The configured boundary is set by whoever launched the server; the
    advertised roots come from the client. If an advertised root that *appears*
    to sit inside the launch boundary can resolve outside it and still grant
    access, the client has widened a boundary it may only narrow — the exact
    inversion §5.5 forbids. Both cumulative directions are asserted, because a
    resolver that applied only the last boundary it was handed would pass one of
    them by luck.
    """
    resolver = require_resolver()
    errors = service_error()
    launch = tmp_path / "launch"
    launch.mkdir()
    contained = build_repo(launch / "consumer")
    outside = build_repo(tmp_path / "outside/other-consumer")
    tunnel = launch / "advertised-root"
    tunnel.symlink_to(outside.parent, target_is_directory=True)

    # Each boundary alone behaves as expected.
    assert resolver(contained, configured_boundary=launch) == contained.resolve(strict=True)
    assert resolver(outside, client_roots=(tunnel,)) == outside.resolve(strict=True)

    # Cumulative: the advertised root resolves outside the launch boundary, so a
    # repository it would otherwise admit stays refused.
    with pytest.raises(errors) as refused:
        resolver(outside, configured_boundary=launch, client_roots=(tunnel,))
    assert_structured_rejection(refused.value, outside, tmp_path)

    # And the reverse direction: a repository inside the launch boundary that no
    # advertised root admits is still refused.
    with pytest.raises(errors):
        resolver(contained, configured_boundary=launch, client_roots=(tunnel,))


def test_nested_boundary_in_the_wrong_direction_is_refused(tmp_path: Path) -> None:
    """IR-007 (review F9): containment is directional; the root descends, not the boundary.

    A boundary nested *inside* the candidate root is the wrong-direction case: a
    resolver that tested relatedness rather than descent would accept it and
    hand back a root strictly larger than the boundary it was given, which is
    widening dressed up as narrowing.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    repo = build_repo(workspace / "consumer")
    nested = build_repo(repo / "nested")

    assert resolver(nested, configured_boundary=repo) == nested.resolve(strict=True)
    for parameter in BOUNDARY_PARAMETERS:
        with pytest.raises(errors) as refused:
            narrowed(resolver, repo, parameter=parameter, boundary=nested)
        assert_structured_rejection(refused.value, repo, tmp_path)


def test_boundary_prefix_collisions_do_not_grant_containment(tmp_path: Path) -> None:
    """IR-007: containment is a path-component relation, not a string prefix.

    ``/w/consumer-evil`` shares the string prefix of ``/w/consumer`` and is a
    different repository. A resolver that used ``startswith`` would accept it,
    which is the classic way a narrowing boundary silently widens.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    boundary = build_repo(workspace / "consumer")
    sibling = build_repo(workspace / "consumer-evil")

    assert resolver(boundary, configured_boundary=boundary) == boundary.resolve(strict=True)
    for parameter in BOUNDARY_PARAMETERS:
        with pytest.raises(errors) as refused:
            narrowed(resolver, sibling, parameter=parameter, boundary=boundary)
        assert_structured_rejection(refused.value, sibling, tmp_path)


def test_resolved_root_is_absolute_and_stable_across_working_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-005/FR-024: the result is a process-state-independent absolute path.

    A relative root is refused rather than joined to the working directory
    (T3.1 rev 2, Codex finding 13), and an accepted root resolves to the same
    absolute path no matter where the process happens to be — otherwise two
    identical tool calls could inspect two different repositories.
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    repo = build_repo(workspace / "consumer")
    other = build_repo(tmp_path / "elsewhere/other")
    expected = repo.resolve(strict=True)

    monkeypatch.chdir(other)
    assert resolver(repo) == expected
    with pytest.raises(errors):
        resolver(Path())
    with pytest.raises(errors):
        resolver(Path(repo.name))

    monkeypatch.chdir(workspace)
    assert resolver(repo) == expected
    assert resolver(repo).is_absolute()
    with pytest.raises(errors):
        resolver(Path(repo.name))


def test_root_resolution_never_modifies_the_candidate_repository(tmp_path: Path) -> None:
    """A read-only server's root check must be read-only too.

    Covers the accepted, malformed, and out-of-boundary paths together, because
    a resolver that created a marker, a lock, or a parent directory would do it
    on exactly one of them. The oracle records regular-file digests and
    inode/change-time evidence, so a rewritten file — or a rewrite followed by a
    restore — is caught, not just a changed mode or link target (review F12).
    """
    resolver = require_resolver()
    errors = service_error()
    workspace = tmp_path / "workspace"
    repo = build_repo(workspace / "consumer")
    outside = build_repo(tmp_path / "elsewhere/other")
    before = tree_state(tmp_path)

    resolver(repo)
    resolver(repo, configured_boundary=workspace)
    resolver(repo, client_roots=(workspace,))
    with pytest.raises(errors):
        resolver(outside, configured_boundary=workspace)
    with pytest.raises(errors):
        resolver(tmp_path / "no-such-repository")

    assert tree_state(tmp_path) == before


def test_boundary_inputs_accept_the_declared_sequence_shape(tmp_path: Path) -> None:
    """The advertised-root input is a set of boundaries, not a single path.

    Claude Code 2.1.220 answers ``roots/list`` with the launch directory *plus*
    additional directories, so the plural shape is a client fact rather than a
    stylistic choice, and a resolver that accepted only one advertised root
    would refuse legitimate repositories. The cumulative cases prove both inputs
    are applied, not just whichever one arrives last.
    """
    resolver = require_resolver()
    errors = service_error()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    repo = build_repo(second / "consumer")
    expected = repo.resolve(strict=True)

    for advertised in ((first, second), [first, second], (second,)):
        assert resolver(repo, client_roots=advertised) == expected
    assert isinstance(resolver(repo, client_roots=(second,)), Path)

    with pytest.raises(errors):
        resolver(repo, client_roots=(first,))

    # Both inputs together narrow cumulatively: satisfying one is not enough.
    assert resolver(repo, configured_boundary=second, client_roots=(second,)) == expected
    with pytest.raises(errors):
        resolver(repo, configured_boundary=first, client_roots=(second,))
    with pytest.raises(errors):
        resolver(repo, configured_boundary=second, client_roots=(first,))
