"""Version-selected workflow rendering, verification, and legacy migration."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from typing import cast


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _sequence(value: object, *, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"{name} must be an array")
    return cast("Sequence[object]", value)


def _workflow(config: Mapping[str, object]) -> str:
    ci = _table(config.get("ci"), name="config.ci")
    if ci.get("enabled") is not True:
        return ""
    runner = ci.get("runner")
    language = ci.get("language")
    setup = ci.get("setup")
    if not isinstance(runner, str) or not runner:
        raise ValueError("enabled CI requires a runner")
    if (language, setup) not in {("python", "uv"), ("generic", "none")}:
        raise ValueError("enabled CI has invalid language or setup assumptions")
    lines = [
        "name: cli-docs-check",
        "",
        "on:",
        "  push:",
        "  pull_request:",
        "",
        "env:",
        "  CLI_DOCS_COMMAND: ${{ vars.CLI_DOCS_COMMAND }}",
        "",
        "jobs:",
        "  cli-docs-check:",
        f"    runs-on: {json.dumps(runner)}",
        "    steps:",
        "      - uses: actions/checkout@v7",
        "      - name: Validate command selection",
        "        shell: bash",
        "        run: |",
        '          if [[ ! "$CLI_DOCS_COMMAND" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then',
        "            printf '%s\\n' 'CLI_DOCS_COMMAND must be a command basename' >&2",
        "            exit 2",
        "          fi",
    ]
    if language == "python" and setup == "uv":
        lines.extend(
            [
                "      - uses: astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990 # v8.3.2",
                "      - name: Build and install wheel",
                "        run: |",
                "          uv build --wheel --out-dir dist/",
                "          uv venv .cli-docs-venv",
                "          uv pip install --python .cli-docs-venv dist/*.whl",
                "      - name: Verify installed wrapper",
                "        run: |",
                '          ".cli-docs-venv/bin/$CLI_DOCS_COMMAND" --help',
                '          ".cli-docs-venv/bin/$CLI_DOCS_COMMAND" --version',
            ]
        )
    else:
        lines.extend(
            [
                "      - name: Verify installed wrapper",
                "        shell: bash",
                "        run: |",
                '          command_path="$(command -v -- "$CLI_DOCS_COMMAND")"',
                '          "$command_path" --help',
                '          "$command_path" --version',
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def run_render(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Return workflow bytes derived only from resolved package options."""
    config = _table(request.get("config"), name="config")
    return {"content": _workflow(config)}


def _is_migrated_legacy_config(config: Mapping[str, object]) -> bool:
    expected: dict[str, object] = {
        "contract_version": "1.0",
        "profile": "packaged",
        "command_name": "toolname",
        "workflow_path": ".github/workflows/cli-docs-check.yml",
        "workflow_ownership": "referenced",
        "ci": {
            "enabled": True,
            "runner": "ubuntu-latest",
            "language": "python",
            "setup": "uv",
        },
    }
    return all(config.get(key) == value for key, value in expected.items())


def run_verify(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Report drift when an immutable consumer workflow snapshot is supplied."""
    config = _table(request.get("config"), name="config")
    expected = _workflow(config)
    if not expected:
        return {"findings": []}
    workflow_path = config.get("workflow_path")
    if not isinstance(workflow_path, str) or not workflow_path:
        raise ValueError("enabled CI requires a workflow path")
    snapshots = _table(request.get("snapshots"), name="snapshots")
    referenced = _sequence(
        snapshots.get("referenced_input_content"),
        name="snapshots.referenced_input_content",
    )
    matches: list[Mapping[str, object]] = []
    for raw in referenced:
        entry = _table(raw, name="referenced workflow")
        if (
            entry.get("standard_id") == "cli-documentation"
            and entry.get("extension_id") == "workflow"
            and entry.get("path") == workflow_path
        ):
            matches.append(entry)
    content: bytes | None = None
    if len(matches) == 1 and isinstance(matches[0].get("content_base64"), str):
        content = base64.b64decode(cast(str, matches[0]["content_base64"]), validate=True)
    legacy = _resources.get("legacy-workflow")
    exact_render = content is not None and content == expected.encode()
    legacy_compatible = (
        content is not None
        and legacy is not None
        and content == legacy
        and _is_migrated_legacy_config(config)
    )
    if exact_render or legacy_compatible:
        return {"findings": []}
    return {
        "findings": [
            {
                "code": "CLI-DOCS-DRIFT",
                "severity": "error",
                "path": workflow_path,
                "identity": "$file",
                "message": "consumer workflow differs from the selected package rendering",
                "hint": "review and regenerate the workflow from the selected payload",
            }
        ]
    }


def _known_claim(
    snapshots: Mapping[str, object],
    signature_id: str,
    target: str,
    *,
    ownership: str,
) -> dict[str, object] | None:
    raw_signature = snapshots.get(signature_id)
    if not isinstance(raw_signature, Mapping):
        return None
    signature = cast("Mapping[str, object]", raw_signature)
    raw_observed = signature.get(target)
    if not isinstance(raw_observed, Mapping):
        return None
    observed = cast("Mapping[str, object]", raw_observed)
    digest = observed.get("digest")
    if observed.get("known") is not True or not isinstance(digest, str):
        return None
    return {
        "signature_id": signature_id,
        "target": target,
        "observed_digest": digest,
        "ownership": ownership,
        "disposition": "preserve",
    }


def _unknown_workflow_claim(snapshots: Mapping[str, object]) -> dict[str, object] | None:
    """Build the relinquishment claim for an unrecognized consumer workflow."""
    target = ".github/workflows/cli-docs-check.yml"
    raw_signature = snapshots.get("legacy-workflow")
    if not isinstance(raw_signature, Mapping):
        return None
    raw_observed = cast("Mapping[str, object]", raw_signature).get(target)
    if not isinstance(raw_observed, Mapping):
        return None
    observed = cast("Mapping[str, object]", raw_observed)
    digest = observed.get("digest")
    if observed.get("known") is True or not isinstance(digest, str):
        return None
    return {
        "signature_id": "legacy-workflow",
        "target": target,
        "observed_digest": digest,
        "ownership": "consumer-owned",
        "disposition": "preserve",
        "intent_pointer": "/cli_documentation/workflow_ownership",
    }


def _unknown_usage_claim(snapshots: Mapping[str, object]) -> dict[str, object] | None:
    target = "docs/usage.md"
    raw_signature = snapshots.get("legacy-usage")
    if not isinstance(raw_signature, Mapping):
        return None
    raw_observed = cast("Mapping[str, object]", raw_signature).get(target)
    if not isinstance(raw_observed, Mapping):
        return None
    observed = cast("Mapping[str, object]", raw_observed)
    digest = observed.get("digest")
    if observed.get("known") is True or not isinstance(digest, str):
        return None
    return {
        "signature_id": "legacy-usage",
        "target": target,
        "observed_digest": digest,
        "ownership": "consumer-owned",
        "disposition": "preserve",
        "intent_pointer": "/cli_documentation/usage_ownership",
    }


def run_migrate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Map the bounded legacy namespace and preserve recognized consumer files."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    legacy = _table(snapshots.get("legacy_config"), name="snapshots.legacy_config")
    cli_documentation = _table(
        legacy.get("cli_documentation"),
        name="legacy_config.cli_documentation",
    )
    config: dict[str, object] = {}
    recognized: list[str] = []
    if "version" in cli_documentation:
        config["contract_version"] = cli_documentation["version"]
        recognized.append("/cli_documentation/version")
    consumer_owned_workflow = cli_documentation.get("workflow_ownership") == "consumer-owned"
    consumer_owned_usage = cli_documentation.get("usage_ownership") == "consumer-owned"
    if "workflow_ownership" in cli_documentation:
        config["workflow_ownership"] = cli_documentation["workflow_ownership"]
        recognized.append("/cli_documentation/workflow_ownership")
    if "usage_ownership" in cli_documentation:
        config["usage_ownership"] = cli_documentation["usage_ownership"]
        recognized.append("/cli_documentation/usage_ownership")

    raw_signatures = _table(
        snapshots.get("legacy_signatures"),
        name="snapshots.legacy_signatures",
    )
    claims = [
        claim
        for claim in (
            _known_claim(
                raw_signatures,
                "legacy-usage",
                "docs/usage.md",
                ownership="consumer-owned" if consumer_owned_usage else "create-only",
            ),
            _known_claim(
                raw_signatures,
                "legacy-workflow",
                ".github/workflows/cli-docs-check.yml",
                ownership="consumer-owned",
            ),
        )
        if claim is not None
    ]
    workflow_recognized = any(claim["signature_id"] == "legacy-workflow" for claim in claims)
    usage_recognized = any(claim["signature_id"] == "legacy-usage" for claim in claims)
    if consumer_owned_usage and not usage_recognized:
        unknown_usage = _unknown_usage_claim(raw_signatures)
        if unknown_usage is not None:
            claims.append(unknown_usage)
    if consumer_owned_workflow:
        # Relinquished: the consumer keeps the workflow, so migration must not
        # enable CI or lock the file as a referenced input. An unrecognized
        # digest is preserved through the target-bound intent pointer.
        if not workflow_recognized:
            unknown_claim = _unknown_workflow_claim(raw_signatures)
            if unknown_claim is not None:
                claims.append(unknown_claim)
    elif workflow_recognized:
        config.update(
            {
                "profile": "packaged",
                "command_name": "toolname",
                "workflow_path": ".github/workflows/cli-docs-check.yml",
                "ci": {
                    "enabled": True,
                    "runner": "ubuntu-latest",
                    "language": "python",
                    "setup": "uv",
                },
            }
        )
    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "cli-documentation",
            "version": str(request.get("version")),
            "selector": "latest",
            "config": config,
            "recognized_settings": recognized,
        },
        "claims": claims,
        "findings": [],
    }
