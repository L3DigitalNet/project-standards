"""The bounded child process that actually executes provider code (T4, ADR 0025).

The authoritative dispatcher ``invoke_provider``
(``control_plane/providers.py:732``) compiles and runs provider bytes *in the
calling process*, with no timeout, no cancellation point, no fault isolation, and
output capture that only rebinds ``sys.stdout``/``sys.stderr``. Underneath a
protocol server that is unacceptable, so ADR 0025 moves the call here: a spawned
process on the server's own interpreter and virtual environment, whose real file
descriptors the parent owns and can terminate.

This module deliberately adds *no* provider semantics. It re-derives the
authoritative selection for the requested root — ``selected_command`` for the
payload and effective config, ``invoke_selected_provider`` for the call — so the
result is the same object the CLI would have produced, then projects it to JSON.
Every qualification the parent already performed is performed again here, because
the worker must be correct on its own inputs rather than trusting a caller.

Three transport rules shape the code below.

*The result never travels on ``stdout``.* The parent captures ``stdout`` and
``stderr`` as diagnostics, so both are assumed to be contaminated by provider
output; the response goes out on a third inherited descriptor passed as
``argv[1]``.

*Nothing unbounded crosses the boundary.* An oversized response is replaced here
by a bounded structured failure rather than being streamed to a parent that would
have to buffer it.

*No exception text is republished unfiltered.* A package-contract failure or a
provider traceback can name absolute installed paths, so ``safe_detail`` drops
any text carrying a known root or an absolute-looking path.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - annotations only; see the import note below
    from project_standards.control_plane.command_resolution import SelectedCommandPackage
    from project_standards.package_contract.payload import ProviderOperation

# Responses above this many bytes are refused rather than transported. The
# parent applies the same limit when reading, so neither side can be made to
# buffer an unbounded provider result (ADR 0025: "bounded JSON with an explicit
# size cap").
RESULT_LIMIT_BYTES = 262_144

# The request field that names who builds the provider's typed input. Absent or
# `caller` keeps the T4 contract exactly: `invoke_read_provider` passes the
# caller's own input through untouched. `seam` is what the composite operations
# send, and it means "build the authoritative input here" — see
# `authoritative_provider_input` for why construction happens on this side of the
# pipe rather than in the parent.
INPUT_AUTHORITY_FIELD = "input_authority"
SEAM_AUTHORITY = "seam"

_ABSOLUTE_PATH_PATTERN = re.compile(r"(?:^|[\s'\"(])/[\w.\-/]{4,}")
_REDACTED_DETAIL = "the failure detail was withheld because it named a filesystem path"


def safe_detail(text: str, secrets: tuple[str, ...]) -> str:
    """Return exception text only when it names no root and no absolute path."""
    if any(secret and secret in text for secret in secrets):
        return _REDACTED_DETAIL
    if _ABSOLUTE_PATH_PATTERN.search(text):
        return _REDACTED_DETAIL
    return text


def _jsonable(value: object) -> Any:
    """Project one authoritative dataclass field onto JSON-safe values."""
    if isinstance(value, dict):
        mapping: dict[str, object] = value  # pyright: ignore[reportUnknownVariableType]
        return {str(key): _jsonable(item) for key, item in mapping.items()}
    if isinstance(value, list | tuple):
        sequence: list[object] = list(value)  # pyright: ignore[reportUnknownArgumentType]
        return [_jsonable(item) for item in sequence]
    return value


def authoritative_provider_input(
    selected: SelectedCommandPackage,
    operation: ProviderOperation,
    *,
    provider_id: str,
) -> dict[str, Any] | None:
    """Build one provider's authoritative typed input, or ``None`` if none exists.

    The single authority is ``control_plane.provider_inputs.provider_dispatch_input``
    (FR-015); nothing here reconstructs a shape. What this function owns is the
    *routing* — which of the seam's two authorities a given provider belongs to —
    and it derives that from the seam's own contract rather than from any package
    identity:

    * ask the family branch first, because a provider that has a public command is
      authoritatively dispatched by that command (every frontmatter, project-spec
      and agent-handoff provider, ``agent-handoff/verify`` included);
    * on refusal, retry plan-bound *only* for a ``verify`` operation, because the
      only other authority that dispatches a provider is the executor's post-apply
      verification. The seam then fails closed on membership in
      ``plan.verification_requests`` itself (T15 review F2), so the membership rule
      is never restated here.

    ``None`` means the seam declares no authority for this provider at all, which
    it says with a distinct `NoDeclaredProviderInput` and nothing else (T14 review
    F1). Every other seam failure — a corpus that cannot be captured, a custom
    schema with no locked input, a package that does not own the standard —
    propagates, becomes the worker's typed failure response, and lands in the
    composite as a per-result failure. Catching the base class here would convert
    an unconstructible authoritative input into an empty one, which is the defect
    T14 exists to close rather than a tolerance it may grant.

    Only genuinely family-less standards therefore keep the generic dispatch they
    have always had; that a *shipping* provider never lands there is pinned by
    TC-T14-004 rather than assumed.

    This runs worker-side because it cannot run anywhere else: the authoritative
    inputs measured on a real consumer are 290 KB to 4.8 MB (2026-07-30), against
    a 256 KiB IPC request bound that ADR 0025 makes a property rather than a
    tuning knob. Building here means only the small directive crosses the pipe.
    """
    from project_standards.control_plane.provider_inputs import (
        NoDeclaredProviderInput,
        provider_dispatch_input,
    )
    from project_standards.package_contract.payload import ProviderOperation

    try:
        return dict(provider_dispatch_input(selected, operation, provider_id=provider_id))
    except NoDeclaredProviderInput:
        if operation is not ProviderOperation.VERIFY:
            return None
    # Built here, not shipped: a `ReconciliationPlan` is an object graph that does
    # not survive JSON, so the parent could not hand one over even if the request
    # had room for it.
    from project_standards.control_plane.cli import build_planner_request
    from project_standards.control_plane.planner import plan_reconciliation

    plan = plan_reconciliation(
        build_planner_request(selected.repo, selected.distribution, frozenset())
    )
    try:
        return dict(
            provider_dispatch_input(
                None,
                operation,
                repo=selected.repo,
                standard_id=selected.payload.manifest.payload.standard,
                plan=plan,
                provider_id=provider_id,
            )
        )
    except NoDeclaredProviderInput:
        return None


def run_request(request: dict[str, Any]) -> dict[str, Any]:
    """Execute one provider invocation and return its JSON-safe response.

    Imports are function-local so a parent that spawns this module pays for the
    control-plane import graph only inside the child.
    """
    from project_standards.control_plane.command_resolution import (
        invoke_selected_provider,
        selected_command,
    )
    from project_standards.control_plane.distribution import InstalledDistribution
    from project_standards.control_plane.locking import LockMode
    from project_standards.package_contract.payload import ProviderOperation

    distribution = InstalledDistribution(
        Path(str(request["package_root"])), tool_release=str(request["tool_release"])
    )
    repo = Path(str(request["repo_root"]))
    standard_id = str(request["standard_id"])
    version = str(request["version"])
    provider_id = str(request["provider_id"])
    operation = ProviderOperation(str(request["operation"]))
    snapshots: dict[str, Any] = dict(request["provider_input"])

    with selected_command(
        repo,
        standard_id,
        distribution,
        mode=LockMode.READ,
        require_reconciled=False,
    ) as selected:
        if selected is None:
            raise ValueError("repository has no unified package authority")
        if selected.resolved.value != version:
            # The parent qualified this already; re-checking closes the window
            # between its resolution and the worker's own.
            raise ValueError("selected payload version does not match the request")
        if request.get(INPUT_AUTHORITY_FIELD) == SEAM_AUTHORITY:
            # The composite operations send a directive rather than an input. The
            # selection this worker just resolved for its own dispatch is the same
            # one the seam needs, so the authoritative corpus is read once, here,
            # against the root the request named.
            built = authoritative_provider_input(selected, operation, provider_id=provider_id)
            if built is not None:
                snapshots = built
        result = invoke_selected_provider(selected, operation, snapshots, provider_id=provider_id)

    return {
        "status": "ok",
        "effect": result.effect.value,
        "output": result.structured_output,
        "output_notice": result.output_notice,
        "findings": [_jsonable(asdict(finding)) for finding in result.findings],
    }


def main(argv: list[str] | None = None) -> int:
    """Read one JSON request from stdin and write one bounded JSON response."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    descriptor = int(arguments[0])
    raw = sys.stdin.buffer.read()
    secrets: tuple[str, ...] = ()
    try:
        request: dict[str, Any] = json.loads(raw)
        secrets = (str(request.get("repo_root", "")), str(request.get("package_root", "")))
        response = run_request(request)
    except BaseException as exc:
        response = {
            "status": "error",
            "code": "provider-invocation-failed",
            "kind": type(exc).__name__,
            "detail": safe_detail(str(exc), secrets),
        }

    payload = json.dumps(response, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(payload) > RESULT_LIMIT_BYTES:
        payload = json.dumps(
            {
                "status": "error",
                "code": "provider-result-too-large",
                "kind": "ResultTooLarge",
                "detail": (
                    f"the provider result serialized to {len(payload)} bytes, above the "
                    f"{RESULT_LIMIT_BYTES}-byte transport limit; no part of it was transported"
                ),
            },
            ensure_ascii=False,
        ).encode("utf-8")
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the spawned worker
    raise SystemExit(main())
