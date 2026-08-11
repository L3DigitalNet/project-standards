"""Execute trusted Python provider bytes inside the shared bounded child.

Direct control-plane calls send an immutable payload description, while MCP
calls send an installed-distribution selection directive so large authoritative
inputs can still be built on this side of the bounded request pipe. Both modes
end at the same in-child provider implementation and write their only result to
the inherited descriptor; stdout and stderr remain untrusted diagnostics.
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast

from project_standards.control_plane.provider_subprocess import (
    RESULT_LIMIT_BYTES,
    safe_failure_detail,
)

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

if TYPE_CHECKING:  # pragma: no cover - annotations only; see the import note below
    from project_standards.control_plane.command_resolution import SelectedCommandPackage
    from project_standards.package_contract.payload import ProviderOperation

# The request field that names who builds the provider's typed input. Absent or
# `caller` keeps the T4 contract exactly: `invoke_read_provider` passes the
# caller's own input through untouched. `seam` is what the composite operations
# send, and it means "build the authoritative input here" — see
# `authoritative_provider_input` for why construction happens on this side of the
# pipe rather than in the parent.
INPUT_AUTHORITY_FIELD = "input_authority"
SEAM_AUTHORITY = "seam"


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
    from project_standards.control_plane.providers import invoke_provider_in_child

    request = build_planner_request(selected.repo, selected.distribution, frozenset())
    plan = plan_reconciliation(replace(request, provider_runner=invoke_provider_in_child))
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


class _OutputSink(io.TextIOBase):
    """Discard Python-level output while retaining only whether it was used."""

    def __init__(self) -> None:
        super().__init__()
        self.used = False

    def write(self, value: str) -> int:
        self.used = self.used or bool(value)
        return len(value)


def _deep_freeze(value: JsonValue) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _deep_freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(child) for child in value)
    return value


def _capsule_bytes(value: object, *, field: str) -> bytes:
    if not isinstance(value, str):
        raise ValueError(f"provider capsule has a malformed {field}")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"provider capsule has a malformed {field}") from exc


def _run_python_capsule(request: dict[str, Any]) -> dict[str, Any]:
    """Execute one parent-qualified Python capsule without payload rediscovery."""
    raw_capsule = request.get("capsule")
    if not isinstance(raw_capsule, dict):
        raise ValueError("provider capsule is missing")
    capsule = cast(dict[str, object], raw_capsule)
    metadata_fields = (
        "standard_id",
        "version",
        "provider_id",
        "operation",
        "effect",
        "symbol",
        "source_path",
    )
    if any(not isinstance(capsule.get(field), str) for field in metadata_fields):
        raise ValueError("provider capsule has malformed declaration metadata")
    raw_input = capsule.get("input")
    if not isinstance(raw_input, dict):
        raise ValueError("provider capsule input is not a JSON object")
    raw_resources = capsule.get("resources")
    if not isinstance(raw_resources, dict):
        raise ValueError("provider capsule resources are not a JSON object")
    resource_values = cast(dict[object, object], raw_resources)
    if any(not isinstance(resource_id, str) for resource_id in resource_values):
        raise ValueError("provider capsule has a malformed resource id")
    resources = {
        cast(str, resource_id): _capsule_bytes(content, field="resource")
        for resource_id, content in resource_values.items()
    }
    code = _capsule_bytes(capsule.get("code_base64"), field="provider code")
    provider_input = _deep_freeze(cast(JsonObject, raw_input))
    frozen_resources = MappingProxyType(resources)
    stdout = _OutputSink()
    stderr = _OutputSink()
    result: object | None = None
    failure: BaseException | None = None
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            compiled = compile(code, cast(str, capsule["source_path"]), "exec")
            namespace: dict[str, object] = {
                "__file__": cast(str, capsule["source_path"]),
                "__name__": "__project_standards_provider__",
            }
            exec(compiled, namespace)
            callable_provider = namespace.get(cast(str, capsule["symbol"]))
            if not callable(callable_provider):
                raise TypeError("entrypoint symbol is not callable")
            result = callable_provider(provider_input, frozen_resources)
    except BaseException as exc:
        failure = exc
    if failure is not None:
        raise failure
    try:
        output = cast(object, json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False)))
    except (TypeError, ValueError) as exc:
        raise ValueError("provider returned a non-JSON result") from exc
    if not isinstance(output, dict):
        raise ValueError("provider result must be a JSON object")
    streams = [name for name, sink in (("stdout", stdout), ("stderr", stderr)) if sink.used]
    return {
        "status": "ok",
        "effect": cast(str, capsule["effect"]),
        "output": cast(JsonObject, output),
        "output_notice": f"provider output suppressed ({', '.join(streams)})" if streams else None,
        "findings": [],
    }


def run_request(request: dict[str, Any]) -> dict[str, Any]:
    """Execute one provider invocation and return its JSON-safe response.

    Imports are function-local so a parent that spawns this module pays for the
    control-plane import graph only inside the child.
    """
    if request.get("dispatch_mode") == "direct":
        return _run_python_capsule(request)

    from project_standards.control_plane.command_resolution import selected_command
    from project_standards.control_plane.distribution import InstalledDistribution
    from project_standards.control_plane.locking import LockMode
    from project_standards.control_plane.providers import (
        ProviderInvocation,
        invoke_provider_in_child,
    )
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
        providers = [
            item
            for item in selected.payload.manifest.providers
            if item.operation is operation and item.id == provider_id
        ]
        if len(providers) != 1:
            raise ValueError("selected package must declare exactly one requested provider")
        result = invoke_provider_in_child(
            ProviderInvocation(
                repo=selected.repo,
                payload=selected.payload,
                standard_id=selected.payload.manifest.payload.standard,
                version=selected.resolved,
                provider_id=provider_id,
                operation=operation,
                effective_config=selected.effective_config,
                snapshots=cast(JsonObject, snapshots),
            )
        )

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
        request = cast(dict[str, Any], json.loads(raw))
        secrets = (
            str(request.get("repo_root", "")),
            str(request.get("package_root", "")),
            str(request.get("payload_root", "")),
        )
        response = run_request(request)
    except BaseException as exc:
        response = {
            "status": "error",
            "code": "provider-invocation-failed",
            "kind": type(exc).__name__,
            "detail": safe_failure_detail(str(exc), secrets),
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
