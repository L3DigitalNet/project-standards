"""Render, verify, and migrate Python Tooling from immutable inputs."""

from __future__ import annotations

import hashlib
import json
import shlex
from collections.abc import Mapping, Sequence
from typing import cast


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _json_value(value: object) -> object:
    """Copy frozen legacy snapshots into provider-returnable JSON containers."""
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _json_value(item) for key, item in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        sequence = cast("Sequence[object]", value)
        return [_json_value(item) for item in sequence]
    return value


def _config(request: Mapping[str, object]) -> Mapping[str, object]:
    return _table(request.get("config"), name="config")


def _section(config: Mapping[str, object], name: str) -> Mapping[str, object]:
    return _table(config.get(name), name=f"config.{name}")


def _checker(config: Mapping[str, object]) -> tuple[str, str]:
    selected = _section(config, "type_checker")
    name = selected.get("name")
    mode = selected.get("mode")
    if name not in {"basedpyright", "pyright"}:
        raise ValueError("config.type_checker.name is unsupported")
    if mode not in {"basic", "standard", "strict"}:
        raise ValueError("config.type_checker.mode is unsupported")
    return cast(str, name), cast(str, mode)


def _python_version(config: Mapping[str, object]) -> str:
    value = config.get("python_version")
    if not isinstance(value, str):
        raise ValueError("config.python_version must be a string")
    return value


def _source_roots(config: Mapping[str, object]) -> tuple[list[str], list[str]]:
    layout = config.get("source_layout")
    if layout == "src":
        return ["src", "tests"], ["src"]
    if layout == "flat":
        return [".", "tests"], ["."]
    raise ValueError("config.source_layout is unsupported")


def _toml_array(values: Sequence[str]) -> str:
    if not values:
        return "[]"
    lines = ["["]
    lines.extend(f"    {json.dumps(value)}," for value in values)
    lines.append("]")
    return "\n".join(lines) + "\n"


def _build_system(config: Mapping[str, object]) -> str:
    backend = config.get("build_backend")
    choices = {
        "uv_build": (["uv_build>=0.11,<0.12"], "uv_build"),
        "hatchling": (["hatchling>=1.27"], "hatchling.build"),
        "setuptools": (["setuptools>=75"], "setuptools.build_meta"),
    }
    try:
        requirements, entrypoint = choices[cast(str, backend)]
    except KeyError as exc:
        raise ValueError("config.build_backend is unsupported") from exc
    return (
        "[build-system]\n"
        f"requires = {json.dumps(requirements)}\n"
        f"build-backend = {json.dumps(entrypoint)}\n"
    )


def _dependencies(config: Mapping[str, object]) -> str:
    checker, _mode = _checker(config)
    coverage = _section(config, "coverage")
    coverage_dependency = "coverage[toml]>=7.10.0" if coverage.get("patch") else "coverage[toml]"
    values = [checker, coverage_dependency, "pip-audit", "pytest>=9.0", "ruff>=0.14.11"]
    additional = config.get("additional_dev_dependencies")
    if not isinstance(additional, Sequence) or isinstance(additional, str | bytes):
        raise ValueError("config.additional_dev_dependencies must be an array")
    values.extend(cast("Sequence[str]", additional))
    return "[dependency-groups]\ndev = " + _toml_array(values)


def _ruff_table(config: Mapping[str, object]) -> str:
    ruff = _section(config, "ruff")
    include, _coverage = _source_roots(config)
    target = f"py{_python_version(config).replace('.', '')}"
    return (
        "[tool.ruff]\n"
        f"target-version = {json.dumps(target)}\n"
        f"line-length = {ruff.get('line_length')}\n"
        f"src = {json.dumps(include)}\n"
        f"extend-exclude = {json.dumps(ruff.get('extend_exclude'))}\n\n"
        "[tool.ruff.lint]\n"
        'select = ["E", "F", "I", "B", "UP", "SIM", "C4", "PIE", "PTH", "RET", "RUF"]\n'
        'ignore = ["E501"]\n\n'
        "[tool.ruff.lint.per-file-ignores]\n"
        '"tests/**/*.py" = ["S101"]\n\n'
        "[tool.ruff.format]\n"
        'quote-style = "double"\n'
        'indent-style = "space"\n'
        "docstring-code-format = true\n"
    )


def _checker_table(config: Mapping[str, object], table: str) -> str:
    checker, mode = _checker(config)
    include, _coverage = _source_roots(config)
    effective_mode = mode if checker == table else "off"
    return (
        f"[tool.{table}]\n"
        f"include = {json.dumps(include)}\n"
        f"typeCheckingMode = {json.dumps(effective_mode)}\n"
        f"pythonVersion = {json.dumps(_python_version(config))}\n"
        'pythonPlatform = "All"\n'
        f"failOnWarnings = {'true' if checker == table else 'false'}\n"
    )


def _pytest_table(config: Mapping[str, object]) -> str:
    testpaths = ["tests"]
    rendered = (
        "[tool.pytest.ini_options]\n"
        'minversion = "9.0"\n'
        f"testpaths = {json.dumps(testpaths)}\n"
        'addopts = ["-ra", "--strict-markers", "--strict-config"]\n'
    )
    markers = _section(config, "pytest").get("markers")
    return rendered + (f"markers = {json.dumps(markers)}\n" if markers else "")


def _coverage_run(config: Mapping[str, object]) -> str:
    coverage = _section(config, "coverage")
    _include, sources = _source_roots(config)
    lines = ["[tool.coverage.run]", "branch = true"]
    if coverage.get("parallel") is True:
        lines.append("parallel = true")
    if coverage.get("patch"):
        lines.append('patch = ["subprocess"]')
    lines.append(f"source = {json.dumps(sources)}")
    return "\n".join(lines) + "\n"


def _coverage_report(config: Mapping[str, object]) -> str:
    pytest = _section(config, "pytest")
    threshold = pytest.get("fail_under")
    rendered = (
        "[tool.coverage.report]\n"
        "show_missing = true\n"
        "skip_covered = true\n"
        f"fail_under = {threshold}\n"
    )
    exclusions = pytest.get("coverage_exclude_also")
    return rendered + (f"exclude_also = {json.dumps(exclusions)}\n" if exclusions else "")


def _audit_command(config: Mapping[str, object]) -> tuple[str, ...]:
    ignored = _section(config, "pip_audit").get("ignore_vulnerabilities")
    if (
        not isinstance(ignored, Sequence)
        or isinstance(ignored, str)
        or not all(isinstance(item, str) for item in cast("Sequence[object]", ignored))
    ):
        raise ValueError("config.pip_audit.ignore_vulnerabilities must be a string array")
    vulnerabilities = cast("Sequence[str]", ignored)
    return (
        "uv",
        "run",
        "pip-audit",
        *(part for vulnerability in vulnerabilities for part in ("--ignore-vuln", vulnerability)),
    )


def _coverage_commands(
    *pytest_args: str,
    config: Mapping[str, object],
) -> list[tuple[str, ...]]:
    parallel = _section(config, "coverage").get("parallel") is True
    run = (
        "uv",
        "run",
        "coverage",
        "run",
        *(("--parallel-mode",) if parallel else ()),
        "-m",
        "pytest",
        *pytest_args,
    )
    if not parallel:
        return [run, ("uv", "run", "coverage", "report")]
    return [
        ("uv", "run", "coverage", "erase"),
        run,
        ("uv", "run", "coverage", "combine"),
        ("uv", "run", "coverage", "report"),
    ]


def _commands(config: Mapping[str, object]) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = [
        ("uv", "run", "ruff", "format", "--check", "."),
        ("uv", "run", "ruff", "check", "."),
    ]
    checker, _mode = _checker(config)
    commands.append(("uv", "run", checker))
    commands.extend(_coverage_commands("-m", "not performance", config=config))
    if _section(config, "ci").get("performance") is True:
        commands.append(("uv", "run", "pytest", "-m", "performance"))
    commands.append(_audit_command(config))
    return commands


def _local_commands(config: Mapping[str, object]) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = [
        ("uv", "run", "ruff", "format", "--check", "."),
        ("uv", "run", "ruff", "check", "."),
    ]
    checker, _mode = _checker(config)
    commands.append(("uv", "run", checker))
    commands.extend(_coverage_commands(config=config))
    commands.append(_audit_command(config))
    return commands


def _command_text(command: Sequence[str]) -> str:
    return shlex.join(command)


def _workflow(config: Mapping[str, object]) -> str:
    ci_enabled = _section(config, "ci").get("enabled") is True
    trigger = (
        ["on:", "  pull_request:", "  push:", '    branches: ["main"]']
        if ci_enabled
        else ["on:", "  workflow_dispatch:"]
    )
    lines = [
        "name: Check",
        "",
        *trigger,
        "",
        "permissions:",
        "  contents: read",
        "",
        "jobs:",
        "  check:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v7",
        "      - uses: actions/setup-python@v6",
        "        with:",
        '          python-version-file: ".python-version"',
        "      - uses: astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990 # v8.3.2",
        "        with:",
        '          version: "0.11.6"',
        "          enable-cache: true",
        "      - name: Sync dependencies",
        "        run: uv sync --locked --all-groups",
    ]
    for index, command in enumerate(_commands(config), start=1):
        lines.extend(
            [
                f"      - name: Gate {index}",
                f"        run: {_command_text(command)}",
            ]
        )
    return "\n".join(lines) + "\n"


def _script(config: Mapping[str, object]) -> str:
    command_lines = "\n".join(
        "    (" + ", ".join(json.dumps(part) for part in command) + "),"
        for command in _local_commands(config)
    )
    return f'''"""Run the selected Python verification gate and stop at the first failure."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

COMMANDS: tuple[tuple[str, ...], ...] = (
{command_lines}
)


def run_command(command: Sequence[str]) -> int:
    """Run one gate command and preserve its exit code."""
    print(f"\\n$ {{' '.join(command)}}", flush=True)
    return subprocess.run(command, check=False).returncode


def main() -> int:
    """Run the gate in order and stop at the first failure."""
    for command in COMMANDS:
        if return_code := run_command(command):
            return return_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


_EDITORCONFIG_VALUES = {
    "property:$global#root": "true",
    "property:*#charset": "utf-8",
    "property:*#end_of_line": "lf",
    "property:*#indent_size": "2",
    "property:*#indent_style": "tab",
    "property:*#insert_final_newline": "true",
    "property:*#trim_trailing_whitespace": "true",
    "property:*.py#indent_size": "4",
    "property:*.py#indent_style": "space",
    "property:*.toml#indent_size": "4",
    "property:*.toml#indent_style": "space",
}

_EXTENSIONS = {
    "set:/recommendations#value=charliermarsh.ruff": "charliermarsh.ruff",
    "set:/recommendations#value=detachhead.basedpyright": "detachhead.basedpyright",
    "set:/recommendations#value=editorconfig.editorconfig": "editorconfig.editorconfig",
    "set:/recommendations#value=github.vscode-github-actions": "github.vscode-github-actions",
    "set:/recommendations#value=ms-python.python": "ms-python.python",
    "set:/recommendations#value=redhat.vscode-yaml": "redhat.vscode-yaml",
    "set:/recommendations#value=tamasfe.even-better-toml": "tamasfe.even-better-toml",
}

_DEFAULT_CONFIG: dict[str, object] = {
    "contract_version": "1.1",
    "python_version": "3.14",
    "build_backend": "uv_build",
    "source_layout": "src",
    "additional_dev_dependencies": [],
    "ruff": {
        "line_length": 100,
        "extend_exclude": [".claude", ".agents", ".codex", ".continue"],
    },
    "type_checker": {"name": "basedpyright", "mode": "strict"},
    "pytest": {"fail_under": 85, "markers": [], "coverage_exclude_also": []},
    "coverage": {"parallel": False, "patch": []},
    "pip_audit": {"ignore_vulnerabilities": []},
    "ci": {"enabled": True, "performance": True},
    "workflow_ownership": "managed",
    "vscode": {"format_on_save": True},
    "agent_instructions": {"include_fix_commands": True},
}

_STATIC_TARGETS = {
    ".python-version": "python-version-source",
    ".github/workflows/check.yml": "check-workflow-source",
    "scripts/check.py": "check-script-source",
}


def _nested(pointer: str, value: object) -> dict[str, object]:
    components = [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]
    result: object = value
    for component in reversed(components):
        result = {component: result}
    return cast("dict[str, object]", result)


def _setting(scope: str, config: Mapping[str, object]) -> object:
    checker, mode = _checker(config)
    settings: dict[str, object] = {
        "key:/python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
        "key:/python.testing.pytestEnabled": True,
        "key:/python.testing.unittestEnabled": False,
        "key:/python.testing.pytestArgs": ["tests"],
        "key:/[python]/editor.defaultFormatter": "charliermarsh.ruff",
        "key:/[python]/editor.formatOnSave": _section(config, "vscode").get("format_on_save"),
        "key:/version": "2.0.0",
        "key:/[python]/editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit",
        },
        "key:/ruff.nativeServer": "on",
        "key:/basedpyright.analysis.typeCheckingMode": mode if checker == "basedpyright" else "off",
        "key:/python.analysis.typeCheckingMode": mode if checker == "pyright" else "off",
        "key:/files.exclude/**~1__pycache__": True,
        "key:/files.exclude/**~1.pytest_cache": True,
        "key:/files.exclude/**~1.ruff_cache": True,
        "key:/files.exclude/**~1.mypy_cache": True,
        "key:/files.exclude/**~1.coverage": True,
    }
    try:
        return settings[scope]
    except KeyError as exc:
        raise ValueError("undeclared VS Code setting scope") from exc


def _task(scope: str, config: Mapping[str, object]) -> dict[str, object]:
    checker, _mode = _checker(config)
    command_by_label = {
        "check": " && ".join(_command_text(command) for command in _local_commands(config)),
        "fix": "uv run ruff format . && uv run ruff check . --fix",
        "test": "uv run pytest",
        "typecheck": f"uv run {checker}",
        "audit": _command_text(_audit_command(config)),
    }
    binding = scope.rsplit("#label=", 1)
    if len(binding) != 2 or binding[1] not in command_by_label:
        raise ValueError("undeclared VS Code task scope")
    label = binding[1]
    task: dict[str, object] = {
        "label": label,
        "type": "shell",
        "command": command_by_label[label],
        "problemMatcher": [],
    }
    if label in {"check", "test"}:
        task["group"] = "test"
    return {"tasks": [task]}


def _instructions(config: Mapping[str, object]) -> str:
    checker, mode = _checker(config)
    commands = "\n".join(_command_text(command) for command in _local_commands(config))
    fix_commands = (
        "\n\nWhen the gate reports formatting or lint findings, run:\n\n"
        "```bash\nuv run ruff format .\nuv run ruff check . --fix\n```"
        if _section(config, "agent_instructions").get("include_fix_commands") is True
        else ""
    )
    body = (
        "Use uv for environments and dependency changes. Ruff owns formatting, linting, and imports.\n"
        f"Use {checker} in {mode} mode for type checking. Do not add a competing Python gate.\n\n"
        "Run before claiming completion:\n\n"
        "```bash\n"
        f"{commands}\n"
        "```"
        f"{fix_commands}"
    )
    return (
        "<!-- prettier-ignore-start -->\n\n"
        "<!-- BEGIN project-standards:python-tooling -->\n"
        "# Python tooling\n\n"
        f"{body}\n"
        "<!-- END project-standards:python-tooling -->\n\n"
        "<!-- prettier-ignore-end -->\n"
    )


def _render_toml(scope: str, config: Mapping[str, object]) -> str:
    if scope == "table:/build-system":
        return _build_system(config)
    if scope == "key:/dependency-groups/dev":
        return _dependencies(config)
    if scope == "table:/tool/ruff":
        return _ruff_table(config)
    if scope == "table:/tool/basedpyright":
        return _checker_table(config, "basedpyright")
    if scope == "table:/tool/pyright":
        return _checker_table(config, "pyright")
    if scope == "table:/tool/pytest/ini_options":
        return _pytest_table(config)
    if scope == "table:/tool/coverage/run":
        return _coverage_run(config)
    if scope == "table:/tool/coverage/report":
        return _coverage_report(config)
    raise ValueError("undeclared pyproject.toml contribution scope")


def run_render_semantic(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, str]:
    """Render exactly one declared contribution from resolved options."""
    config = _config(request)
    snapshots = _table(request.get("snapshots"), name="snapshots")
    planned = _table(snapshots.get("planned_contribution"), name="planned contribution")
    target = planned.get("target")
    adapter = planned.get("adapter")
    scope = planned.get("scope")
    if not isinstance(target, str) or not isinstance(scope, str):
        raise ValueError("planned contribution is incomplete")

    if adapter == "whole-file" and scope == "$file":
        if target == ".python-version":
            rendered = f"{_python_version(config)}\n"
        elif target == ".github/workflows/check.yml":
            rendered = _workflow(config)
        elif target == "scripts/check.py":
            rendered = _script(config)
        else:
            rendered = ""
        resource_id = _STATIC_TARGETS.get(target)
        if resource_id is not None and config == _DEFAULT_CONFIG:
            source = resources.get(resource_id)
            if source is None or source != rendered.encode():
                raise ValueError("default rendered bytes differ from immutable static source")
            return {"content": source.decode()}
        if resource_id is not None:
            return {"content": rendered}
    if adapter == "toml":
        return {"content": _render_toml(scope, config)}
    if adapter == "editorconfig":
        try:
            value = _EDITORCONFIG_VALUES[scope]
        except KeyError as exc:
            raise ValueError("undeclared EditorConfig contribution scope") from exc
        section, key = scope.removeprefix("property:").rsplit("#", 1)
        content = (
            f"{key} = {value}\n" if section == "$global" else f"[{section}]\n{key} = {value}\n"
        )
        return {"content": content}
    if adapter == "jsonc":
        if scope in _EXTENSIONS:
            return {
                "content": json.dumps(
                    {"recommendations": [_EXTENSIONS[scope]]}, separators=(",", ":")
                )
            }
        if scope.startswith("keyed-set:/tasks#label="):
            return {"content": json.dumps(_task(scope, config), separators=(",", ":"))}
        if scope.startswith("key:/"):
            pointer = scope.removeprefix("key:")
            return {
                "content": json.dumps(
                    _nested(pointer, _setting(scope, config)), separators=(",", ":")
                )
            }
    if adapter == "markdown-block" and scope == "block:python-tooling":
        return {"content": _instructions(config)}
    raise ValueError("unsupported Python Tooling semantic contribution")


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _whole_content(
    target: str,
    config: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> bytes:
    if target == ".python-version":
        rendered = f"{_python_version(config)}\n".encode()
    elif target == ".github/workflows/check.yml":
        rendered = _workflow(config).encode()
    elif target == "scripts/check.py":
        rendered = _script(config).encode()
    else:
        raise ValueError("undeclared managed whole-file target")
    if config == _DEFAULT_CONFIG:
        source = resources.get(_STATIC_TARGETS[target])
        if source is None or source != rendered:
            raise ValueError("default rendered bytes differ from immutable static source")
        return source
    return rendered


def run_verify(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Verify the three exclusive rendered files from captured snapshot facts."""
    config = _config(request)
    snapshots = _table(request.get("snapshots"), name="snapshots")
    findings: list[dict[str, object]] = []
    for target in (".python-version", ".github/workflows/check.yml", "scripts/check.py"):
        observed = snapshots.get(target)
        state: Mapping[str, object] = (
            cast("Mapping[str, object]", observed) if isinstance(observed, Mapping) else {}
        )
        if state.get("kind") != "regular" or state.get("content_digest") != _digest(
            _whole_content(target, config, resources)
        ):
            findings.append(
                {
                    "code": "PT-DRIFT",
                    "severity": "error",
                    "path": target,
                    "identity": "$file",
                    "message": "managed Python Tooling bytes do not match the selected payload",
                    "hint": "reconcile the selected Python Tooling payload",
                    "line": None,
                    "locus": None,
                }
            )
    return {"findings": findings}


_SIGNATURES = {
    "legacy-agents": ("AGENTS.md", "managed", "remove"),
    "legacy-check-script": ("scripts/check.py", "managed", "adopt"),
    "legacy-check-workflow": (".github/workflows/check.yml", "managed", "adopt"),
    "legacy-claude": ("CLAUDE.md", "managed", "remove"),
    "legacy-editorconfig": (".editorconfig", "shared", "preserve"),
    "legacy-python-version": (".python-version", "managed", "adopt"),
    "legacy-vscode-extensions": (".vscode/extensions.json", "shared", "preserve"),
    "legacy-vscode-settings": (".vscode/settings.json", "managed", "remove"),
    "legacy-vscode-tasks": (".vscode/tasks.json", "managed", "remove"),
}

_PRESERVED_CONTAINER_DIGESTS = {
    "sha256:960e17f7c7f0980a979b48e4457de958697afeb3d6e1953c379e20a443669b92",
    "sha256:f345f6167f040071b925a0c3b507cbe7e62a41b05ffc662055b25fb1f595405a",
    "sha256:68eba3cdc1101d739ae5aafb2407f5237e3d8fdce74ff6a3cc4ba1ff37491aa2",
    "sha256:21cd73316ba5128b5a0bc66a34de4563dcf8af6b049f22ff4409f40c496850c0",
    "sha256:22f598ebf1f24e29041289891b3c56131f0acc4dddfed802d92a6a3802eab55f",
    "sha256:8dcb4880139bb708bf20819479bcb7898bb5d1dabd8d79e43b7d64bb3e4b3b08",
}


def run_migrate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Map V4 metadata and exact files without retaining YAML authority."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    legacy = _table(snapshots.get("legacy_config"), name="snapshots.legacy_config")
    namespace = _table(legacy.get("python_tooling"), name="legacy_config.python_tooling")
    config: dict[str, object] = {}
    recognized: list[str] = []
    if "version" in namespace:
        config["contract_version"] = namespace["version"]
        recognized.append("/python_tooling/version")
    for key in ("additional_dev_dependencies", "ruff", "pytest"):
        if key in namespace:
            config[key] = _json_value(namespace[key])
            recognized.append(f"/python_tooling/{key}")

    signatures = _table(snapshots.get("legacy_signatures"), name="legacy signatures")
    claims: list[dict[str, object]] = []
    findings: list[dict[str, str]] = []
    for signature_id, (target, ownership, disposition) in _SIGNATURES.items():
        raw = signatures.get(signature_id)
        if not isinstance(raw, Mapping):
            continue
        observed = cast("Mapping[str, object]", raw).get(target)
        if not isinstance(observed, Mapping):
            continue
        state = cast("Mapping[str, object]", observed)
        digest = state.get("digest")
        if state.get("known") is True and isinstance(digest, str):
            resolved_disposition = (
                "preserve" if digest in _PRESERVED_CONTAINER_DIGESTS else disposition
            )
            claims.append(
                {
                    "signature_id": signature_id,
                    "target": target,
                    "observed_digest": digest,
                    "ownership": ownership,
                    "disposition": resolved_disposition,
                }
            )
        elif isinstance(digest, str):
            findings.append(
                {
                    "code": "PT-LEGACY-MODIFIED",
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
            "standard_id": "python-tooling",
            "version": str(request.get("version")),
            "selector": "latest",
            "config": config,
            "recognized_settings": recognized,
        },
        "claims": claims,
        "findings": findings,
    }
