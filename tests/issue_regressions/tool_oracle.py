"""Pinned subprocess oracles for formatter, linter, and file-selection outcomes."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

_TOOLS = ("markdownlint-cli2", "prettier")


@dataclass(frozen=True, slots=True)
class ToolOutcome:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def _json_object(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    untyped = cast("dict[object, object]", value)
    if not all(isinstance(key, str) for key in untyped):
        raise AssertionError(f"{path} must contain a JSON object")
    return cast("dict[str, object]", untyped)


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{label} must be an object")
    untyped = cast("dict[object, object]", value)
    if not all(isinstance(key, str) for key in untyped):
        raise AssertionError(f"{label} must be an object")
    return cast("dict[str, object]", untyped)


def _mapping(value: object, *, label: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{label} must be a mapping")
    return cast("dict[object, object]", value)


def locked_tool_versions(repo: Path) -> dict[str, str]:
    """Derive tool pins from both lockfile intent and installed-package records."""
    lock = _json_object(repo / "package-lock.json")
    packages = _object(lock.get("packages"), label="package-lock packages")
    root = _object(packages.get(""), label="package-lock root")
    dependencies = _object(root.get("devDependencies"), label="package-lock devDependencies")
    versions: dict[str, str] = {}
    for tool in _TOOLS:
        declared = dependencies.get(tool)
        installed = _object(
            packages.get(f"node_modules/{tool}"),
            label=f"package-lock node_modules/{tool}",
        ).get("version")
        if not isinstance(declared, str) or not isinstance(installed, str):
            raise AssertionError(f"package-lock must pin and install {tool}")
        if declared != installed:
            raise AssertionError(
                f"package-lock {tool} intent/install mismatch: {declared} != {installed}"
            )
        versions[tool] = declared
    return versions


def _binary(repo: Path, name: str) -> Path:
    binary = repo / "node_modules/.bin" / name
    if not binary.is_file():
        raise AssertionError(f"run npm ci before the tool oracle: missing {binary}")
    return binary


def _run(args: list[str], *, cwd: Path) -> ToolOutcome:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    return ToolOutcome(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def installed_tool_versions(repo: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for tool in _TOOLS:
        argument = "--help" if tool == "markdownlint-cli2" else "--version"
        outcome = _run([str(_binary(repo, tool)), argument], cwd=repo)
        accepted_codes = {0, 2} if tool == "markdownlint-cli2" else {0}
        if outcome.returncode not in accepted_codes:
            raise AssertionError(f"{tool} version probe failed: {outcome.output}")
        match = re.search(r"(?<![0-9])[0-9]+\.[0-9]+\.[0-9]+\b", outcome.output)
        if match is None:
            raise AssertionError(f"{tool} emitted no semantic version: {outcome.output!r}")
        versions[tool] = match.group()
    return versions


def prettier_differences(
    repo: Path,
    cwd: Path,
    patterns: tuple[str, ...],
    *,
    config_path: Path | None = None,
    ignore_path: Path | None = None,
) -> tuple[str, ...]:
    args = [
        str(_binary(repo, "prettier")),
        "--config",
        str(config_path or repo / ".prettierrc.json"),
        "--list-different",
    ]
    if ignore_path is not None:
        args.extend(("--ignore-path", str(ignore_path)))
    args.extend(patterns)
    outcome = _run(args, cwd=cwd)
    if outcome.returncode not in {0, 1}:
        raise AssertionError(f"Prettier selection probe failed: {outcome.output}")
    return tuple(line.strip() for line in outcome.stdout.splitlines() if line.strip())


def format_with_prettier(
    repo: Path,
    cwd: Path,
    patterns: tuple[str, ...],
    *,
    config_path: Path | None = None,
) -> None:
    outcome = _run(
        [
            str(_binary(repo, "prettier")),
            "--config",
            str(config_path or repo / ".prettierrc.json"),
            "--write",
            *patterns,
        ],
        cwd=cwd,
    )
    if outcome.returncode != 0:
        raise AssertionError(f"Prettier write failed: {outcome.output}")


def prettier_string_widths(repo: Path, values: tuple[str, ...]) -> tuple[int, ...]:
    """Measure strings through the exact pinned Prettier utility."""
    script = """
import fs from "node:fs";
import prettier from "./node_modules/prettier/index.mjs";
const values = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(values.map(prettier.util.getStringWidth)));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=repo,
        check=False,
        capture_output=True,
        input=json.dumps(values),
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Prettier string-width probe failed: {completed.stdout}{completed.stderr}"
        )
    raw_widths: object = json.loads(completed.stdout)
    if not isinstance(raw_widths, list):
        raise AssertionError("Prettier string-width probe returned invalid JSON")
    untyped_widths = cast("list[object]", raw_widths)
    if not all(isinstance(width, int) for width in untyped_widths):
        raise AssertionError("Prettier string-width probe returned invalid JSON")
    return tuple(cast("list[int]", untyped_widths))


def markdownlint(repo: Path, path: Path) -> ToolOutcome:
    return _run(
        [
            str(_binary(repo, "markdownlint-cli2")),
            "--config",
            str(repo / ".markdownlint-cli2.jsonc"),
            "--no-globs",
            str(path),
        ],
        cwd=repo,
    )


def markdownlint_patterns(
    repo: Path,
    cwd: Path,
    patterns: tuple[str, ...],
    *,
    config_path: Path,
) -> ToolOutcome:
    return _run(
        [
            str(_binary(repo, "markdownlint-cli2")),
            "--config",
            str(config_path),
            "--no-globs",
            *patterns,
        ],
        cwd=cwd,
    )


def prettier_workflow(
    repo: Path,
    cwd: Path,
    caller_path: Path,
) -> ToolOutcome:
    caller = _mapping(yaml.safe_load(caller_path.read_text(encoding="utf-8")), label="caller")
    jobs = _object(caller.get("jobs"), label="caller jobs")
    job = _object(jobs.get("format"), label="caller format job")
    raw_inputs = job.get("with")
    inputs = {} if raw_inputs is None else _object(raw_inputs, label="caller format inputs")
    globs = inputs.get("globs", ".")
    exclusions = inputs.get("exclusions", "")
    if not isinstance(globs, str) or not isinstance(exclusions, str):
        raise AssertionError("caller format inputs must be strings")

    workflow_path = repo / ".github/workflows/format.yml"
    workflow = _mapping(
        yaml.safe_load(workflow_path.read_text(encoding="utf-8")),
        label="format workflow",
    )
    workflow_jobs = _object(workflow.get("jobs"), label="format workflow jobs")
    prettier_job = _object(workflow_jobs.get("prettier"), label="prettier job")
    raw_steps = prettier_job.get("steps")
    if not isinstance(raw_steps, list):
        raise AssertionError("prettier job steps must be a list")
    steps = cast("list[object]", raw_steps)
    check: dict[str, object] | None = None
    for raw_step in steps:
        step = _object(raw_step, label="prettier step")
        if step.get("name") == "Check formatting (Prettier)":
            check = step
            break
    if check is None or not isinstance(check.get("run"), str):
        raise AssertionError("format workflow must define its Prettier check script")

    node_modules = cwd / "node_modules"
    expected_tools = (repo / "node_modules").resolve()
    created_node_modules = False
    if node_modules.exists() or node_modules.is_symlink():
        if node_modules.resolve() != expected_tools:
            raise AssertionError(f"{node_modules} does not expose the pinned tool install")
    else:
        node_modules.symlink_to(expected_tools, target_is_directory=True)
        created_node_modules = True

    environment = os.environ.copy()
    environment.update(
        {
            "FORMAT_GLOBS": globs,
            "FORMAT_EXCLUSIONS": exclusions,
            "npm_config_offline": "true",
        }
    )
    try:
        completed = subprocess.run(
            ["bash", "-c", cast("str", check["run"])],
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        if created_node_modules:
            node_modules.unlink()
    return ToolOutcome(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def markdownlint_findings(
    repo: Path,
    cwd: Path,
    patterns: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the files selected by markdownlint that contain findings."""
    outcome = _run(
        [
            str(_binary(repo, "markdownlint-cli2")),
            "--config",
            str(repo / ".markdownlint-cli2.jsonc"),
            "--no-globs",
            *patterns,
        ],
        cwd=cwd,
    )
    if outcome.returncode not in {0, 1}:
        raise AssertionError(f"markdownlint selection probe failed: {outcome.output}")

    findings: set[str] = set()
    for line in outcome.output.splitlines():
        match = re.match(r"^(?P<path>.+?\.md):[0-9]+(?::[0-9]+)?(?:\s|$)", line)
        if match is None:
            continue
        path = Path(match.group("path"))
        if path.is_absolute():
            path = path.relative_to(cwd)
        findings.add(path.as_posix())
    return tuple(sorted(findings))
