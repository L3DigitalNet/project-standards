"""Explicit-root normalization and boundary containment (§5.5, ADR 0026).

``resolve_effective_root`` is the single place the server decides which
directory a repository-scoped call may touch. Its contract, from §5.5 and ADR
0026's root rules:

- the explicit ``repo_root`` is the authoritative repository identity and is
  mandatory — no boundary and no process state may ever supply it;
- ``configured_boundary`` (the launch-time option) and ``client_roots`` (roots a
  client advertises) may only *narrow*: they can reject an input, never select a
  different repository and never widen the boundary;
- the returned path is normalized and symlink-resolved, so containment is
  decided on real paths rather than on spelling.

Three rejection rules carry the security weight and each exists because the
obvious implementation gets it wrong:

1. Containment compares *resolved* paths. A symlink that sits inside a boundary
   but points outside it would otherwise be accepted, and the server would
   report a contained root while reading a repository nobody advertised.
2. Containment is a path-component relation, not a string prefix. ``/w/repo-evil``
   shares ``/w/repo``'s prefix and is a different repository.
3. An unusable boundary value fails the whole call. Ignoring a boundary the
   caller supplied would turn the one narrowing input the launch surface exposes
   into a silent no-op — the quietest possible way to widen authority.

Every refusal is a :class:`~project_standards.mcp_services.ServiceError`, per
plan T5's "map every startup/root error to ``ServiceError``/protocol error".
Messages never echo the rejected path: a client that supplied a path already has
it, and a client that did not must not learn it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from project_standards.mcp_services import ServiceError

# The repository-root rejection class shares one stable code with the T3 service
# resolver (`mcp_services.consumer`). Two services deciding the same question
# must not publish two taxonomies for it; the spelling itself is not frozen by
# any binding document, only its stability and the class it covers.
ROOT_ERROR_CODE = "repo-root-invalid"
ROOT_REMEDIATION = (
    "pass an explicit absolute path to an existing repository directory, "
    "without parent-directory segments"
)

BOUNDARY_ERROR_CODE = "root-boundary-invalid"
BOUNDARY_REMEDIATION = (
    "supply an absolute path to an existing directory as the root boundary, "
    "without parent-directory segments"
)

CONTAINMENT_ERROR_CODE = "repo-root-out-of-bounds"
CONTAINMENT_REMEDIATION = (
    "pass a repository root inside every configured and client-advertised boundary, "
    "or launch the server with a boundary that contains it"
)


def _root_error(message: str) -> ServiceError:
    return ServiceError(code=ROOT_ERROR_CODE, message=message, remediation=ROOT_REMEDIATION)


def _boundary_error(message: str) -> ServiceError:
    return ServiceError(code=BOUNDARY_ERROR_CODE, message=message, remediation=BOUNDARY_REMEDIATION)


def _containment_error(message: str) -> ServiceError:
    return ServiceError(
        code=CONTAINMENT_ERROR_CODE, message=message, remediation=CONTAINMENT_REMEDIATION
    )


def _normalized(value: object, *, label: str, fail: Callable[[str], ServiceError]) -> Path:
    """Normalize one explicit path input, or raise a structured refusal.

    Shared by the root and the boundaries so a boundary can never be held to a
    weaker standard than the root it is supposed to constrain. The two callers
    publish different codes, so the failure factory is passed in rather than
    branched on inside.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise fail(f"an explicit {label} is required")
    try:
        candidate = Path(value)  # pyright: ignore[reportArgumentType]
    except TypeError as exc:
        raise fail(f"the {label} must be a filesystem path") from exc
    if not candidate.is_absolute():
        raise fail(f"the {label} must be an absolute path")
    if ".." in candidate.parts:
        raise fail(f"the {label} must not contain parent-directory segments")
    try:
        resolved = candidate.resolve(strict=True)
        usable = resolved.is_dir()
    except (OSError, ValueError) as exc:
        # ValueError is not defensive padding: an embedded NUL is a perfectly
        # representable JSON string, and `Path.resolve(strict=True)` raises
        # `ValueError: embedded null character` rather than `OSError` for it.
        # Catching only OSError would let that one input escape as a raw
        # exception with no code and no remediation — the exact leak plan:373
        # forbids. `is_dir()` shares the clause because it performs the same
        # stat and can raise the same way on a path built after resolution.
        raise fail(f"the {label} could not be resolved") from exc
    if not usable:
        raise fail(f"the {label} must be an existing directory")
    return resolved


def resolve_boundary(value: object) -> Path:
    """Normalize one boundary value, or refuse it structurally.

    Exposed because the launch surface has to validate its boundary argument
    *before* the server starts: a boundary that would be refused on every later
    call is a launch error, not a per-call one.
    """
    return _normalized(value, label="root boundary", fail=_boundary_error)


def _contains(boundary: Path, root: Path) -> bool:
    """Whether ``root`` is ``boundary`` or descends from it, by path components."""
    return root == boundary or root.is_relative_to(boundary)


def resolve_effective_root(
    repo_root: object,
    *,
    configured_boundary: object | None = None,
    client_roots: Iterable[object] | None = None,
) -> Path:
    """Return the normalized, symlink-resolved explicit root after containment.

    ``configured_boundary`` and ``client_roots`` are applied cumulatively: the
    root must satisfy the launch-time boundary *and* at least one advertised
    root whenever each is supplied. Passing ``client_roots=()`` therefore
    rejects everything — an empty advertised set is a client that has admitted
    no repository at all, which is different from advertising none.
    """
    root = _normalized(repo_root, label="repository root", fail=_root_error)

    if configured_boundary is not None:
        boundary = resolve_boundary(configured_boundary)
        if not _contains(boundary, root):
            raise _containment_error("repository root lies outside the configured root boundary")

    if client_roots is not None:
        advertised = [resolve_boundary(candidate) for candidate in client_roots]
        if not any(_contains(boundary, root) for boundary in advertised):
            raise _containment_error("repository root lies outside every client-advertised root")

    return root
