"""Render, verify, and migrate Markdown Tooling from immutable snapshots."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import cast


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _optional_table(value: object) -> Mapping[str, object]:
    return (
        cast("Mapping[str, object]", value)
        if isinstance(value, Mapping)
        else cast("Mapping[str, object]", {})
    )


def _sequence(value: object, *, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"{name} must be an array")
    return cast("Sequence[object]", value)


def _config(request: Mapping[str, object]) -> Mapping[str, object]:
    return _table(request.get("config"), name="config")


def _ci(config: Mapping[str, object]) -> Mapping[str, object]:
    return _table(config.get("ci"), name="config.ci")


def _automatic(config: Mapping[str, object], tool: str) -> bool:
    caller = f"{tool}_caller"
    return config.get(tool) is True and _ci(config).get(caller) is True


def _triggers(automatic: bool) -> list[str]:
    if automatic:
        return [
            "on:",
            "  pull_request:",
            "  push:",
            "    branches:",
            "      - main",
            "  workflow_dispatch:",
        ]
    return ["on:", "  workflow_dispatch:"]


def _glob(value: object, *, name: str, role: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("!")
        or value[0].isspace()
        or value[-1].isspace()
        or "`" in value
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise ValueError(f"{name} must contain a safe {role} glob")
    return value


def _globs(config: Mapping[str, object], key: str) -> list[str]:
    raw = _sequence(config.get(key), name=f"config.{key}")
    return [_glob(value, name=f"config.{key}", role="include") for value in raw]


def _exclusion_globs(config: Mapping[str, object], tool: str) -> list[str]:
    exclusions = _sequence(config.get("exclusions"), name="config.exclusions")
    result: list[str] = []
    for raw in exclusions:
        exclusion = _table(raw, name="config.exclusions item")
        applies_to = exclusion.get("applies_to")
        glob = exclusion.get("glob")
        if applies_to in {tool, "both"}:
            result.append(
                _glob(
                    glob,
                    name="config.exclusions item",
                    role="exclusion",
                )
            )
    return sorted(result, key=str.encode)


def _yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _lint_caller(config: Mapping[str, object]) -> str:
    globs = _globs(config, "markdown_globs")
    globs.extend(f"!{value}" for value in _exclusion_globs(config, "lint"))
    lines = ["name: Lint Markdown", "", *_triggers(_automatic(config, "lint")), "", "jobs:"]
    lines.extend(
        [
            "  lint-markdown:",
            "    uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v5",
            "    with:",
            f"      markdownlint: {'true' if config.get('lint') is True else 'false'}",
            f"      globs: {_yaml_scalar(chr(10).join(globs))}",
        ]
    )
    return "\n".join(lines) + "\n"


def _format_caller(config: Mapping[str, object]) -> str:
    markdown = _globs(config, "markdown_globs")
    structured = _globs(config, "config_globs")
    globs = [*markdown, *structured]
    exclusions = _exclusion_globs(config, "format")
    lines = ["name: Format", "", *_triggers(_automatic(config, "format")), "", "jobs:"]
    lines.extend(
        [
            "  format:",
            "    uses: L3DigitalNet/project-standards/.github/workflows/format.yml@v5",
            "    with:",
            f"      prettier: {'true' if config.get('format') is True else 'false'}",
            f"      globs: {_yaml_scalar(chr(10).join(globs))}",
            f"      exclusions: {_yaml_scalar(chr(10).join(exclusions))}",
        ]
    )
    return "\n".join(lines) + "\n"


def run_render_lint(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, str]:
    """Render the managed lint caller for its selected enforcement state."""
    return {"content": _lint_caller(_config(request))}


def run_render_format(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, str]:
    """Render the managed formatter caller for its selected enforcement state."""
    return {"content": _format_caller(_config(request))}


_EDITORCONFIG_VALUES = {
    "property:$global#root": "true",
    "property:*#charset": "utf-8",
    "property:*#end_of_line": "lf",
    "property:*#indent_size": "2",
    "property:*#indent_style": "tab",
    "property:*#insert_final_newline": "true",
    "property:*#trim_trailing_whitespace": "true",
    "property:*.md#indent_size": "2",
    "property:*.md#indent_style": "space",
    "property:*.md#trim_trailing_whitespace": "false",
    "property:*.{yml,yaml}#indent_size": "2",
    "property:*.{yml,yaml}#indent_style": "space",
}

_JSON_VALUES: dict[str, object] = {
    "key:/[json]/editor.defaultFormatter": "esbenp.prettier-vscode",
    "key:/[jsonc]/editor.defaultFormatter": "esbenp.prettier-vscode",
    "key:/[markdown]/editor.defaultFormatter": "esbenp.prettier-vscode",
    "key:/[markdown]/editor.formatOnSave": True,
    "key:/[yaml]/editor.defaultFormatter": "esbenp.prettier-vscode",
    "set:/recommendations#value=DavidAnson.vscode-markdownlint": ("DavidAnson.vscode-markdownlint"),
    "set:/recommendations#value=esbenp.prettier-vscode": "esbenp.prettier-vscode",
}


def _instructions(config: Mapping[str, object]) -> str:
    enabled = [tool for tool in ("format", "lint") if config.get(tool) is True]
    markdown_globs = _globs(config, "markdown_globs")
    config_globs = _globs(config, "config_globs")
    lines = [
        "# Markdown and structured-text tooling",
        "",
        "Prettier owns physical formatting and markdownlint owns Markdown structure. Do not add overlapping tools.",
        "",
        f"Enabled checks: {', '.join(enabled) if enabled else 'none'}.",
        f"Markdown scope: {', '.join(str(item) for item in markdown_globs)}.",
        f"Structured-config scope: {', '.join(str(item) for item in config_globs)}.",
    ]
    exclusions = _sequence(config.get("exclusions"), name="config.exclusions")
    if exclusions:
        lines.extend(["", "Declared exclusions:"])
        for raw in exclusions:
            exclusion = _table(raw, name="config.exclusions item")
            lines.append(
                f"- `{exclusion.get('glob')}` ({exclusion.get('applies_to')}): "
                f"{exclusion.get('reason')}"
            )
    lines.extend(["", "Run the enabled checks before claiming completion."])
    return "\n".join(lines) + "\n"


def run_render_semantic(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, str]:
    """Render one declared shared-container unit without reading live files."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    planned = _table(
        snapshots.get("planned_contribution"),
        name="snapshots.planned_contribution",
    )
    adapter = planned.get("adapter")
    scope = planned.get("scope")
    if adapter == "editorconfig" and isinstance(scope, str):
        try:
            value = _EDITORCONFIG_VALUES[scope]
        except KeyError as exc:
            raise ValueError("undeclared EditorConfig contribution scope") from exc
        section, key = scope.removeprefix("property:").rsplit("#", 1)
        if section == "$global":
            return {"content": f"{key} = {value}\n"}
        return {"content": f"[{section}]\n{key} = {value}\n"}
    if adapter == "jsonc" and isinstance(scope, str):
        try:
            value = _JSON_VALUES[scope]
        except KeyError as exc:
            raise ValueError("undeclared JSONC contribution scope") from exc
        if scope.startswith("key:/"):
            content: object = value
            for key in reversed(scope.removeprefix("key:/").split("/")):
                content = {key: content}
        else:
            content = {"recommendations": [value]}
        return {"content": json.dumps(content, separators=(",", ":"))}
    if adapter == "markdown-block" and scope == "block:markdown-tooling":
        body = _instructions(_config(request))
        return {
            "content": (
                "<!-- prettier-ignore-start -->\n\n"
                "<!-- BEGIN project-standards:markdown-tooling -->\n"
                f"{body}"
                "<!-- END project-standards:markdown-tooling -->\n\n"
                "<!-- prettier-ignore-end -->\n"
            )
        }
    raise ValueError("unsupported Markdown Tooling semantic contribution")


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _finding(code: str, path: str, identity: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "error",
        "path": path,
        "identity": identity,
        "message": message,
        "hint": "reconcile the selected Markdown Tooling payload",
    }


def _verify(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
    *,
    tool: str,
) -> dict[str, object]:
    config = _config(request)
    if config.get(tool) is not True:
        return {"findings": []}
    snapshots = _table(request.get("snapshots"), name="snapshots")
    if tool == "lint":
        expected = {
            ".markdownlint.json": _digest(resources["markdownlint-source"]),
            ".github/workflows/lint-markdown.yml": _digest(_lint_caller(config).encode()),
        }
    else:
        expected = {
            ".prettierrc.json": _digest(resources["prettier-source"]),
            ".github/workflows/format.yml": _digest(_format_caller(config).encode()),
        }
    findings: list[dict[str, str]] = []
    for path, digest in expected.items():
        observed = snapshots.get(path)
        table = _optional_table(observed)
        if table.get("kind") != "regular" or table.get("content_digest") != digest:
            findings.append(
                _finding(
                    f"MT-{tool.upper()}-DRIFT",
                    path,
                    "$file",
                    f"managed {tool} bytes do not match the selected payload",
                )
            )
    return {"findings": findings}


def run_verify_lint(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Verify selected lint configuration and caller digests."""
    return _verify(request, resources, tool="lint")


def run_verify_format(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Verify selected formatter configuration and caller digests."""
    return _verify(request, resources, tool="format")


_SIGNATURES = {
    "legacy-editorconfig": (".editorconfig", "shared", "preserve"),
    "legacy-format-caller": (".github/workflows/format.yml", "managed", "adopt"),
    "legacy-lint-caller": (".github/workflows/lint-markdown.yml", "managed", "adopt"),
    "legacy-markdownlint-config": (".markdownlint.json", "managed", "adopt"),
    "legacy-prettier-config": (".prettierrc.json", "managed", "adopt"),
    "legacy-vscode-extensions": (".vscode/extensions.json", "shared", "preserve"),
}


def run_migrate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Map V4 package metadata and exact artifacts without emitting YAML."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    legacy = _table(snapshots.get("legacy_config"), name="snapshots.legacy_config")
    namespace = _table(legacy.get("markdown_tooling"), name="legacy_config.markdown_tooling")
    config: dict[str, object] = {}
    recognized: list[str] = []
    if "version" in namespace:
        config["contract_version"] = namespace["version"]
        recognized.append("/markdown_tooling/version")

    signatures = _table(
        snapshots.get("legacy_signatures"),
        name="snapshots.legacy_signatures",
    )
    claims: list[dict[str, object]] = []
    findings: list[dict[str, str]] = []
    for signature_id, (target, ownership, disposition) in _SIGNATURES.items():
        raw_signature = signatures.get(signature_id)
        if not isinstance(raw_signature, Mapping):
            continue
        observed = cast("Mapping[str, object]", raw_signature).get(target)
        if not isinstance(observed, Mapping):
            continue
        state = cast("Mapping[str, object]", observed)
        digest = state.get("digest")
        if state.get("known") is True and isinstance(digest, str):
            claims.append(
                {
                    "signature_id": signature_id,
                    "target": target,
                    "observed_digest": digest,
                    "ownership": ownership,
                    "disposition": disposition,
                }
            )
        elif isinstance(digest, str):
            findings.append(
                {
                    "code": "MT-LEGACY-MODIFIED",
                    "severity": "error",
                    "path": target,
                    "identity": signature_id,
                }
            )
    claims.sort(key=lambda item: str(item["signature_id"]).encode())
    findings.sort(key=lambda item: (item["path"].encode(), item["identity"].encode()))
    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "markdown-tooling",
            "version": str(request.get("version")),
            "selector": "latest",
            "config": config,
            "recognized_settings": recognized,
        },
        "claims": claims,
        "findings": findings,
    }
