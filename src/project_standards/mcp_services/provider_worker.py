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
from typing import Any

# Responses above this many bytes are refused rather than transported. The
# parent applies the same limit when reading, so neither side can be made to
# buffer an unbounded provider result (ADR 0025: "bounded JSON with an explicit
# size cap").
RESULT_LIMIT_BYTES = 262_144

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
