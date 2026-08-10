"""Render, verify, and migrate Python Tooling from immutable inputs."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
import tomllib
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


def _string_list(
    section: Mapping[str, object],
    key: str,
    *,
    option: str,
    selector: bool = False,
) -> list[str]:
    value = section.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"{option} must be an array")
    items = list(cast("Sequence[object]", value))
    if any(not isinstance(item, str) or not item for item in items):
        raise ValueError(f"{option} entries must be nonempty strings")
    resolved = cast("list[str]", items)
    if len(resolved) != len(set(resolved)):
        raise ValueError(f"{option} entries must be unique")
    if selector and any(re.fullmatch(r"[A-Z][A-Z0-9]*", item) is None for item in resolved):
        raise ValueError(f"{option} entries must be Ruff rule selectors")
    if not selector and any(re.search(r"[\r\n<>`]", item) for item in resolved):
        raise ValueError(f"{option} entries contain an unsupported character")
    return resolved


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


def _declared_source_roots(config: Mapping[str, object]) -> list[tuple[str, bool]]:
    additional = config.get("additional_source_roots")
    if not isinstance(additional, Sequence) or isinstance(additional, str | bytes):
        raise ValueError("config.additional_source_roots must be an array")
    declared: list[tuple[str, bool]] = []
    for entry in cast("Sequence[object]", additional):
        if isinstance(entry, str):
            declared.append((entry, True))
            continue
        if isinstance(entry, Mapping):
            table = cast("Mapping[str, object]", entry)
            path = table.get("path")
            coverage = table.get("coverage", True)
            if not isinstance(path, str) or not isinstance(coverage, bool):
                raise ValueError("config.additional_source_roots entry is malformed")
            declared.append((path, coverage))
            continue
        raise ValueError("config.additional_source_roots entry is malformed")
    # A path declared twice with different scopes would silently resolve the
    # conflict; fail closed instead so the declaration stays unambiguous.
    paths = [path for path, _coverage in declared]
    if len(paths) != len(set(paths)):
        raise ValueError("config.additional_source_roots declares a duplicate path")
    return declared


def _test_paths(config: Mapping[str, object]) -> list[str]:
    """Return the declared pytest collection roots (5.8.0 FR-001..004 / issue #31).

    1.7 hardcoded a single ``tests`` root; 1.8 renders whatever the closed schema
    resolved into ``pytest.test_paths`` (default ``["tests"]``), preserving order.
    """
    paths = _section(config, "pytest").get("test_paths")
    if not isinstance(paths, Sequence) or isinstance(paths, str | bytes):
        raise ValueError("config.pytest.test_paths must be an array")
    resolved = list(cast("Sequence[object]", paths))
    if not resolved:
        raise ValueError("config.pytest.test_paths must declare at least one root")
    if any(not isinstance(item, str) for item in resolved):
        raise ValueError("config.pytest.test_paths entries must be strings")
    return cast("list[str]", resolved)


def _layout_root(config: Mapping[str, object]) -> str | None:
    """Return the one repository-relative root the declared layout owns, if any.

    Issue #86: a mixed monorepo keeps Python only under selected subproject
    roots, so both published layouts misdescribe it — "src" invents a root that
    does not exist and "." sweeps every unrelated nested project, and
    additional_source_roots can only append to either. The "explicit" layout
    owns no root at all and returns None: it is the one place the three modes
    differ, so every downstream root list drops the implicit entry and keeps
    its existing composition rule unchanged.
    """
    layout = config.get("source_layout")
    if layout == "src":
        return "src"
    if layout == "flat":
        return "."
    if layout == "explicit":
        return None
    raise ValueError("config.source_layout is unsupported")


def _declared_roots_or_fail(roots: list[str]) -> list[str]:
    """Refuse a hollow gate: the explicit layout must declare where the code is.

    The option schema already rejects `explicit` without additional_source_roots,
    so this only guards a caller that reached the provider with unresolved
    options — a gate over no roots would otherwise render as a clean pass.
    """
    if not roots:
        raise ValueError("config.source_layout explicit requires a declared source root")
    return roots


def _import_roots(config: Mapping[str, object]) -> list[str]:
    """Return the checker's import-resolution roots, layout root first.

    Issue #89: `include` selects which files are checked and establishes no
    resolution order at all. On a src layout whose distribution is installed
    editably without a py.typed marker, the checker answered every local import
    from site-packages first and strict mode called the repository's own code
    untyped third-party code. Declaring the layout root ahead of everything else
    makes that source the first-party answer; declared additional roots keep
    their declared order behind it, first-wins deduplicated.

    Collection roots are deliberately absent: pytest collects and the checker
    includes them, but tests are not importable package roots, and adding them
    would let a test package shadow a real distribution.
    """
    layout_root = _layout_root(config)
    roots = [] if layout_root is None else [layout_root]
    for root, _coverage in _declared_source_roots(config):
        if root not in roots:
            roots.append(root)
    return _declared_roots_or_fail(roots)


def _source_roots(config: Mapping[str, object]) -> tuple[list[str], list[str]]:
    root = _layout_root(config)
    include: list[str] = [] if root is None else [root]
    sources: list[str] = list(include)
    # 5.8.0 FR-001..004 / issue #31: pytest collection roots join the checker
    # include (and Ruff src) right after the layout-derived source root, before
    # additional_source_roots, with first-wins dedupe. They never enter
    # coverage.run.source on their own — only an additional_source_roots
    # declaration grants coverage, so a path appearing in BOTH keeps its
    # additional_source_roots coverage semantics.
    for path in _test_paths(config):
        if path not in include:
            include.append(path)
    # Declared roots keep their declared order after the collection roots. Every
    # declared root joins the checker include (and Ruff src); only coverage-scoped
    # roots join coverage.run.source, so a strictly-typed but unmeasured tooling
    # root cannot drag down the coverage gate.
    for root, coverage in _declared_source_roots(config):
        if root not in include:
            include.append(root)
        if coverage and root not in sources:
            sources.append(root)
    return _declared_roots_or_fail(include), sources


def _toml_array(values: Sequence[str]) -> str:
    if not values:
        return "[]"
    lines = ["["]
    lines.extend(f"    {json.dumps(value)}," for value in values)
    lines.append("]")
    return "\n".join(lines) + "\n"


def _build_system(config: Mapping[str, object]) -> str:
    backend = config.get("build_backend")
    if backend == "none":
        return ""
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
    seen = {_dependency_name(value) for value in values}
    for value in cast("Sequence[str]", additional):
        name = _dependency_name(value)
        if name not in seen:
            values.append(value)
            seen.add(name)
    return "[dependency-groups]\ndev = " + _toml_array(values)


def _dependency_name(requirement: str) -> str:
    name = re.split(r"[\[<>=!~;@]", requirement, maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


# KEY OWNERSHIP INVARIANT (issues #99 and #117), declared once for every value
# table below, the unit renderers, and the payload scopes that mirror them: this
# package owns exactly the leaf keys it names and nothing else inside the tables
# it contributes to. Every undeclared key or sub-table is therefore consumer-owned
# by construction, not by an allow-list this package would have to keep growing —
# `[tool.ruff.lint.flake8-bugbear]`, `isort`, `extend-per-file-ignores` and any
# future Ruff plugin (#99); `exclude` and any other checker setting in
# `[tool.basedpyright]`/`[tool.pyright]` (#117); `pythonpath` in
# `[tool.pytest.ini_options]`. Through 1.11 `[tool.ruff]` alone broke that rule by
# owning a whole table, so the compared value was the entire subtree and one
# consumer sub-table blocked adoption outright, with none of the nine governing
# options able to express it.
#
# The invariant is also why `ruff.extend_exclude` does not feed the checker
# (#117): a rendered `exclude` key would have to exist unconditionally — a
# contribution cannot render nothing, and materialization predicates cannot test
# emptiness — so an empty option would replace the checker's own default excludes
# for every consumer. Leaving the key undeclared hands that decision back.
#
# Rejected alternative: a bounded typed option per plugin (`ruff.flake8_bugbear.*`
# or a generic sub-table passthrough). It re-runs this defect for the next plugin
# a consumer adopts, imports Ruff's own schema into this package's option surface
# where it cannot be validated, and still overwrites bytes a consumer wrote
# directly. Adding a key here — not an option there — is how this package grows.
#
# Issue #116 is why `ruff.extend_per_file_ignores` (1.13) composes into the owned
# `per-file-ignores` table instead of rendering Ruff's separate
# `extend-per-file-ignores` table. The invariant above names that second table as
# consumer-owned, and the documented 1.12 answer to #116 was to write it by hand;
# declaring it here would take ownership of bytes existing consumers already wrote
# and reintroduce the CP-MODIFIED-MANAGED failure the option exists to remove. It
# also cannot be scoped per glob — globs are consumer values, not payload
# identities — so the unit would have to be the whole table, and the empty default
# would emit a bare table header into every consumer's pyproject.toml. Composing
# into the already-owned table changes no ownership boundary at all: both routes
# stay open and Ruff unions them.
_LINT_SELECT = ["E", "F", "I", "B", "UP", "SIM", "C4", "PIE", "PTH", "RET", "RUF"]
_LINT_IGNORE = ["E501"]
_PER_FILE_IGNORES = {"tests/**/*.py": ["S101"]}
_FORMAT = {
    "quote-style": "double",
    "indent-style": "space",
    "docstring-code-format": True,
}


def _per_file_ignores(ruff: Mapping[str, object]) -> dict[str, list[str]]:
    """Compose this package's per-file ignores with `ruff.extend_per_file_ignores`.

    Extension, never replacement (issue #116): a glob the package already ships
    keeps every package rule and gains the consumer's, and a glob the package does
    not ship is added. Dropping the option therefore drops exactly the consumer's
    additions and restores the package default. That is what makes the scoped
    exemption a real alternative to `ruff.extend_ignore`, which can only silence a
    rule for the whole repository.

    Consumer globs and their rules are emitted in sorted order after the package's
    own, so the rendered unit — and every digest over it — depends on the option's
    value and not on the key order the consumer happened to write in TOML.
    """
    value = ruff.get("extend_per_file_ignores")
    extension = _table(value, name="config.ruff.extend_per_file_ignores")
    composed = {glob: list(rules) for glob, rules in _PER_FILE_IGNORES.items()}
    for glob in sorted(extension):
        if not glob or re.search(r"[\r\n<>`]", glob):
            raise ValueError("config.ruff.extend_per_file_ignores globs are unsupported")
        rules = _string_list(
            extension,
            glob,
            option=f"config.ruff.extend_per_file_ignores[{glob!r}]",
            selector=True,
        )
        if not rules:
            raise ValueError(
                f"config.ruff.extend_per_file_ignores[{glob!r}] must list at least one rule"
            )
        owned = composed.setdefault(glob, [])
        owned.extend(rule for rule in sorted(rules) if rule not in owned)
    return composed


def _ruff_values(config: Mapping[str, object]) -> dict[tuple[str, ...], object]:
    """Return every Ruff value this package owns, addressed by its own key path.

    `per-file-ignores` and `format` are whole tables rather than leaf keys. Both
    are complete package-authored leaves with no plugin-extension surface beneath
    them, and keeping `per-file-ignores` a table is what lets 1.13 compose the
    consumer's `extend_per_file_ignores` entries into it without a payload scope
    naming a consumer-chosen glob.

    The three additive keys are rendered UNCONDITIONALLY, where 1.11 emitted them
    only when non-empty. A contribution cannot conditionally render nothing, and
    materialization predicates match a literal value rather than emptiness, so a
    key-level unit has to exist for every key the option can fill. An empty array
    is inert in Ruff, and this is the whole rendered-surface delta of that cut.
    """
    ruff = _section(config, "ruff")
    include, _coverage = _source_roots(config)
    return {
        ("target-version",): f"py{_python_version(config).replace('.', '')}",
        ("line-length",): ruff.get("line_length"),
        ("src",): include,
        ("extend-exclude",): ruff.get("extend_exclude"),
        ("extend-include",): _string_list(
            ruff,
            "extend_include",
            option="config.ruff.extend_include",
        ),
        ("lint", "select"): _LINT_SELECT,
        ("lint", "ignore"): _LINT_IGNORE,
        ("lint", "extend-select"): _string_list(
            ruff,
            "extend_select",
            option="config.ruff.extend_select",
            selector=True,
        ),
        ("lint", "extend-ignore"): _string_list(
            ruff,
            "extend_ignore",
            option="config.ruff.extend_ignore",
            selector=True,
        ),
        ("lint", "per-file-ignores"): _per_file_ignores(ruff),
        ("format",): _FORMAT,
    }


def _toml_key_name(key: str) -> str:
    """Quote a key only when TOML requires it, so bare keys keep their 1.11 spelling."""
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else json.dumps(key)


def _toml_assignment(key: str, value: object) -> str:
    """Spell one owned assignment; every rendered TOML value passes through here."""
    return f"{_toml_key_name(key)} = {json.dumps(value)}\n"


def _toml_key(table: Sequence[str], key: str, value: object) -> str:
    """Render one addressable assignment under its own table header."""
    return f"[{'.'.join(table)}]\n{_toml_assignment(key, value)}"


def _toml_table(table: Sequence[str], value: Mapping[str, object]) -> str:
    body = "".join(_toml_assignment(key, item) for key, item in value.items())
    return f"[{'.'.join(table)}]\n{body}"


def _ruff_unit(config: Mapping[str, object], kind: str, path: str) -> str:
    """Render exactly the one declared Ruff unit the planner asked for."""
    components = tuple(part for part in path.split("/") if part)
    try:
        value = _ruff_values(config)[components]
    except KeyError as exc:
        raise ValueError("undeclared Ruff contribution scope") from exc
    table = ("tool", "ruff", *components[:-1])
    if kind == "table":
        if not isinstance(value, Mapping):
            raise ValueError("Ruff table scope does not name a table")
        return _toml_table(
            (*table, components[-1]),
            cast("Mapping[str, object]", value),
        )
    if isinstance(value, Mapping):
        raise ValueError("Ruff key scope names a table")
    return _toml_key(table, components[-1], value)


def _checker_key(config: Mapping[str, object], table: str, key: str) -> str:
    checker, mode = _checker(config)
    if checker != table:
        raise ValueError("non-selected checker key must not be rendered")
    include, _coverage = _source_roots(config)
    values: dict[str, object] = {
        "extraPaths": _import_roots(config),
        "include": include,
        "typeCheckingMode": mode,
        "pythonVersion": _python_version(config),
        "pythonPlatform": "All",
        "failOnWarnings": True,
    }
    try:
        value = values[key]
    except KeyError as exc:
        raise ValueError("undeclared checker key scope") from exc
    return _toml_key(("tool", table), key, value)


def _pytest_key(config: Mapping[str, object], key: str) -> str:
    values: dict[str, object] = {
        "minversion": "9.0",
        # 5.8.0 FR-001..004 / issue #31: render the declared collection roots.
        "testpaths": _test_paths(config),
        "addopts": ["-ra", "--strict-markers", "--strict-config"],
        "markers": _section(config, "pytest").get("markers"),
    }
    try:
        value = values[key]
    except KeyError as exc:
        raise ValueError("undeclared pytest key scope") from exc
    return _toml_key(("tool", "pytest", "ini_options"), key, value)


def _coverage_run(config: Mapping[str, object]) -> str:
    coverage = _section(config, "coverage")
    _include, sources = _source_roots(config)
    omit = _string_list(coverage, "omit", option="config.coverage.omit")
    lines = ["[tool.coverage.run]", "branch = true"]
    if coverage.get("parallel") is True:
        lines.append("parallel = true")
    if coverage.get("patch"):
        lines.append('patch = ["subprocess"]')
    lines.append(f"source = {json.dumps(sources)}")
    if omit:
        lines.append(f"omit = {json.dumps(omit)}")
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


def _ruff_targets(config: Mapping[str, object]) -> tuple[str, ...]:
    """Return the roots every rendered Ruff command is bounded to.

    Issue #95: Ruff was the one gate handed ".", so it swept every discoverable
    Python file — an independent nested project, a machine-local scratch script,
    an undeclared directory — while the checker and coverage stayed inside the
    declared roots. The file-selection scope coincides exactly with the checker
    `include` set: the layout root, the declared collection roots, then the
    declared additional roots, first-wins deduplicated. Unlike the import roots
    of issue #89, collection roots belong here: tests are formatted and linted
    even though they are never imported as a package root.

    A flat layout still renders "." because there the repository root IS the
    declared source root; bounding it further would need exclusions this
    package does not own.
    """
    include, _coverage = _source_roots(config)
    return tuple(include)


def _ruff_commands(config: Mapping[str, object]) -> list[tuple[str, ...]]:
    targets = _ruff_targets(config)
    return [
        ("uv", "run", "ruff", "format", "--check", *targets),
        ("uv", "run", "ruff", "check", *targets),
    ]


def _ruff_fix_commands(config: Mapping[str, object]) -> list[tuple[str, ...]]:
    targets = _ruff_targets(config)
    return [
        ("uv", "run", "ruff", "format", *targets),
        ("uv", "run", "ruff", "check", *targets, "--fix"),
    ]


def _commands(config: Mapping[str, object]) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = [*_ruff_commands(config)]
    checker, _mode = _checker(config)
    commands.append(("uv", "run", checker))
    commands.extend(_coverage_commands("-m", "not performance", config=config))
    if _section(config, "ci").get("performance") is True:
        commands.append(("uv", "run", "pytest", "-m", "performance"))
    commands.append(_audit_command(config))
    return commands


def _local_commands(config: Mapping[str, object]) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = [*_ruff_commands(config)]
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
        # SHA-pinned because setup-uv publishes no moving major or minor tag from
        # v8.0.0 on, so `@v9` does not resolve. `prune-cache: true` is explicit
        # rather than inherited: v9 stopped pruning before saving the cache, so
        # the v8 cache behavior this workflow was measured under has to be asked
        # for by name.
        "      - uses: astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0",
        "        with:",
        '          version: "0.11.6"',
        "          enable-cache: true",
        "          prune-cache: true",
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


def _annotation_future_import(config: Mapping[str, object]) -> str:
    """Render the future import only for targets below Python 3.14.

    Python Coding 0.6 forbids `from __future__ import annotations` by default,
    and PEP 649 deferred evaluation makes it redundant from 3.14 on. The option
    schema still admits older targets, so those keep the predecessor bytes
    rather than silently changing annotation semantics under an old runtime.
    """
    version = _python_version(config)
    try:
        components = tuple(int(part) for part in version.split("."))
    except ValueError as exc:
        raise ValueError("config.python_version must be numeric MAJOR.MINOR") from exc
    if components >= (3, 14):
        return ""
    return "from __future__ import annotations\n\n"


def _command_literal(command: Sequence[str]) -> str:
    """Render one gate command as an argv literal Ruff's formatter cannot rewrite.

    Issue #115: the predecessor emitted each command on a single line, so line
    length grew with the declared root count (#95 renders every root as its own
    argv element). Past `ruff.line_length` the formatter would split the line,
    and the package's own generated script failed the `ruff format --check` stage
    that the same script invokes first — with no consumer fix, because editing
    the managed bytes trips CP-MODIFIED-MANAGED.

    One element per line with a magic trailing comma is the formatter's own
    output for an exploded collection, and Ruff never rejoins a collection that
    carries one. That makes the rendering a fixed point at ANY root count and any
    `line_length`, rather than one that holds until a consumer declares a root
    too many. Hoisting the roots into a shared module constant (the report's
    other suggestion) would shorten these lines but not bound them: the
    non-Ruff commands can exceed a low `line_length` on their own.
    """
    return "    (\n" + "".join(f"        {json.dumps(part)},\n" for part in command) + "    ),"


def _script(config: Mapping[str, object]) -> str:
    command_lines = "\n".join(_command_literal(command) for command in _local_commands(config))
    return f'''"""Run the selected Python verification gate and stop at the first failure."""

{_annotation_future_import(config)}import subprocess
import sys
from collections.abc import Sequence

USAGE = """usage: scripts/check.py [-h]

Run the verification gate commands in order and stop at the first failure.

options:
  -h, --help  show this message and exit
"""

COMMANDS: tuple[tuple[str, ...], ...] = (
{command_lines}
)


def run_command(command: Sequence[str]) -> int:
    """Run one gate command and preserve its exit code."""
    print(f"\\n$ {{' '.join(command)}}", flush=True)
    return subprocess.run(command, check=False).returncode


def main(argv: Sequence[str]) -> int:
    """Resolve arguments before any gate command, then stop at the first failure.

    Only `-h`/`--help` are accepted, and an unrecognized argument outranks them:
    `check.py --typo --help` must fail rather than print usage and exit 0, or a
    mistyped CI invocation silently skips the whole gate. A `--` ends option
    parsing, so it and everything after it are positionals this script never
    accepts. No gate command runs on any of these paths.
    """
    arguments = list(argv)
    separator = arguments.index("--") if "--" in arguments else len(arguments)
    unrecognized = next(
        (
            argument
            for index, argument in enumerate(arguments)
            if index >= separator or argument not in {{"-h", "--help"}}
        ),
        None,
    )
    if unrecognized is not None:
        # Pre-split with a magic trailing comma: `ruff.line_length` accepts values
        # down to 79, and this call is 97 columns joined. Issue #115's original
        # 1.10 report had no per-root argv at all, so a low line_length was the
        # only way its managed script could fail its own formatter stage.
        print(
            f"scripts/check.py: error: unrecognized argument: {{unrecognized}}",
            file=sys.stderr,
        )
        print(USAGE, end="", file=sys.stderr)
        return 2
    if arguments:
        print(USAGE, end="")
        return 0
    for command in COMMANDS:
        if return_code := run_command(command):
            return return_code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
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
    "additional_source_roots": [],
    "additional_dev_dependencies": [],
    "ruff": {
        "line_length": 100,
        "extend_exclude": [".claude", ".agents", ".codex", ".continue"],
        "extend_include": [],
        "extend_select": [],
        "extend_ignore": [],
        "extend_per_file_ignores": {},
    },
    "type_checker": {"name": "basedpyright", "mode": "strict"},
    "pytest": {
        "fail_under": 85,
        "markers": [],
        "coverage_exclude_also": [],
        "test_paths": ["tests"],
    },
    "coverage": {"parallel": False, "patch": [], "omit": []},
    "pip_audit": {"ignore_vulnerabilities": []},
    "ci": {"enabled": True, "performance": False},
    "workflow_ownership": "managed",
    "script_ownership": "managed",
    "vscode": {"format_on_save": True, "task_prefix": ""},
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
        # 5.8.0 FR-001..004 / issue #31: same declared roots drive VS Code discovery.
        "key:/python.testing.pytestArgs": _test_paths(config),
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
        "key:/files.exclude/**~1.coverage": True,
    }
    try:
        return settings[scope]
    except KeyError as exc:
        raise ValueError("undeclared VS Code setting scope") from exc


def _task(scope: str, config: Mapping[str, object]) -> dict[str, object]:
    checker, _mode = _checker(config)
    check_command = (
        "uv run python scripts/check.py"
        if config.get("script_ownership") == "consumer-owned"
        else " && ".join(_command_text(command) for command in _local_commands(config))
    )
    command_by_label = {
        "check": check_command,
        "fix": " && ".join(_command_text(command) for command in _ruff_fix_commands(config)),
        "test": "uv run pytest",
        "typecheck": f"uv run {checker}",
        "audit": _command_text(_audit_command(config)),
    }
    task_prefix = _section(config, "vscode").get("task_prefix")
    if not isinstance(task_prefix, str) or task_prefix not in {"", "python: "}:
        raise ValueError("undeclared VS Code task scope")
    scope_prefix = "keyed-set:/tasks#label="
    if not scope.startswith(scope_prefix):
        raise ValueError("undeclared VS Code task scope")
    label = scope.removeprefix(scope_prefix)
    base_label = label.removeprefix(task_prefix)
    if label != f"{task_prefix}{base_label}" or base_label not in command_by_label:
        raise ValueError("undeclared VS Code task scope")
    task: dict[str, object] = {
        "label": label,
        "type": "shell",
        "command": command_by_label[base_label],
        "problemMatcher": [],
    }
    if base_label in {"check", "test"}:
        task["group"] = "test"
    return {"tasks": [task]}


def _fix_command_text(config: Mapping[str, object]) -> str:
    """Spell the remediation commands over the same bounded roots as the gate."""
    return "\n".join(_command_text(command) for command in _ruff_fix_commands(config))


def _instructions(config: Mapping[str, object]) -> str:
    checker, mode = _checker(config)
    commands = "\n".join(_command_text(command) for command in _local_commands(config))
    fix_commands = (
        "\n\nWhen the gate reports formatting or lint findings, run:\n\n"
        f"```bash\n{_fix_command_text(config)}\n```"
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
        "<!-- markdownlint-disable MD025 -->\n"
        "# Python tooling\n\n"
        f"{body}\n"
        "<!-- markdownlint-enable MD025 -->\n"
        "<!-- END project-standards:python-tooling -->\n\n"
        "<!-- prettier-ignore-end -->\n"
    )


def _render_toml(scope: str, config: Mapping[str, object]) -> str:
    if scope == "table:/build-system":
        return _build_system(config)
    if scope == "key:/dependency-groups/dev":
        return _dependencies(config)
    for kind in ("key", "table"):
        prefix = f"{kind}:/tool/ruff/"
        if scope.startswith(prefix):
            return _ruff_unit(config, kind, scope.removeprefix(prefix))
    for table in ("basedpyright", "pyright"):
        prefix = f"key:/tool/{table}/"
        if scope.startswith(prefix):
            return _checker_key(config, table, scope.removeprefix(prefix))
    pytest_prefix = "key:/tool/pytest/ini_options/"
    if scope.startswith(pytest_prefix):
        return _pytest_key(config, scope.removeprefix(pytest_prefix))
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


_PROJECT_METADATA_HINT = (
    "declare consumer-owned PEP 621 metadata in pyproject.toml "
    "(at minimum [project] with name, version, and requires-python), "
    'or declare the repository deliberately non-installable with build_backend = "none"'
)


def run_validate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Refuse an installable adoption the consumer has not authorized.

    Issue #109: enabling this package in a repository with no pyproject.toml
    rendered a tool-only file - dependency groups, build system, tool tables and
    no [project] table - and the adoption guide's required `uv lock` then exited
    2 with "No `project` table found". Project identity is consumer authority:
    a package may not invent a distribution name, version, or Python floor, and
    it must not leave the repository holding a file its own guide cannot use.

    Both halves are the same defect: the file may be absent, or present without
    the table. Neither is reported when the repository is deliberately
    non-installable, because then no build system is rendered and `uv lock` is
    not part of the documented flow.
    """
    config = _config(request)
    snapshots = _table(request.get("snapshots"), name="snapshots")
    observed_state = snapshots.get("consumer_state")
    if not isinstance(observed_state, Mapping):
        # No consumer-state input: nothing about the repository's own metadata was
        # offered, so there is nothing to fault. The engine supplies this input
        # only where the decision matters — fresh adoption during reconcile
        # planning — and every other caller (post-apply verification sweeps,
        # generic validator harnesses) legitimately dispatches a different input
        # class. Inferring absence from an input that was never provided would
        # fail an already-adopted consumer for a condition it did not create.
        return {"findings": []}
    state = cast("Mapping[str, object]", observed_state)
    return {
        "findings": [*_metadata_findings(config, state), *_declared_root_findings(config, state)]
    }


def _declared_root_findings(
    config: Mapping[str, object],
    state: Mapping[str, object],
) -> list[dict[str, object]]:
    """Report each declared root the repository does not actually have.

    Issue #118: every adoption declares at least one collection root, because
    `pytest.test_paths` has a minimum of one entry, and the declared roots are
    rendered straight into the checker `include` and the bounded Ruff commands.
    Nothing creates them. A fresh adoption that has not written its first test
    therefore reconciled clean and then failed its own one-command gate on
    `File or directory "/repo/tests" does not exist.` — a message that names
    neither this package nor the option that produced the path.

    Reported, never repaired, and never blocking: creating a directory is not
    this package's authority, the declaration may legitimately precede the code
    it describes, and turning a normal early-adoption state into a refused
    reconcile would be a worse defect than the one being fixed. Absence of a
    captured fact is silence, not a fault — a caller that offered no state for a
    path is not evidence the path is missing.
    """
    findings: list[dict[str, object]] = []
    roots, _coverage = _source_roots(config)
    for root in roots:
        if root == ".":
            # The flat layout root IS the repository, which necessarily exists.
            continue
        observed = state.get(root)
        if not isinstance(observed, Mapping):
            continue
        kind = cast("Mapping[str, object]", observed).get("kind")
        if kind == "directory":
            continue
        findings.append(
            {
                "code": "PT-DECLARED-ROOT-MISSING",
                "severity": "warning",
                "path": root,
                "identity": "$directory",
                "message": (
                    f"declared source or test root {root!r} does not exist, "
                    "so the managed gate will fail on it before any check runs"
                ),
                "hint": (
                    "create the directory (an empty placeholder is enough) or drop it from "
                    "pytest.test_paths, additional_source_roots, or source_layout"
                ),
                "line": None,
                "locus": None,
            }
        )
    return findings


def _metadata_findings(
    config: Mapping[str, object],
    state: Mapping[str, object],
) -> list[dict[str, object]]:
    """Refuse an installable adoption with no consumer-owned project identity."""
    if config.get("build_backend") == "none":
        return []
    observed = state.get("pyproject.toml")
    metadata: Mapping[str, object] = (
        cast("Mapping[str, object]", observed) if isinstance(observed, Mapping) else {}
    )
    if metadata.get("kind") != "regular":
        return [_metadata_finding("this repository has no pyproject.toml")]
    content = metadata.get("content_base64")
    if not isinstance(content, str):
        raise ValueError("consumer_state pyproject.toml carries no content")
    try:
        document: Mapping[str, object] = tomllib.loads(base64.b64decode(content).decode("utf-8"))
    except UnicodeDecodeError, ValueError:
        raise ValueError("consumer pyproject.toml is not valid UTF-8 TOML") from None
    if isinstance(document.get("project"), Mapping):
        return []
    return [_metadata_finding("this pyproject.toml declares none")]


def _metadata_finding(observation: str) -> dict[str, object]:
    return {
        "code": "PT-PROJECT-METADATA",
        "severity": "error",
        "path": "pyproject.toml",
        "identity": "table:/project",
        "message": (
            f"installable adoption requires a consumer-owned [project] table and {observation}"
        ),
        "hint": _PROJECT_METADATA_HINT,
        "line": None,
        "locus": None,
    }


def run_verify(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Verify the selected exclusive rendered files from captured snapshot facts."""
    config = _config(request)
    snapshots = _table(request.get("snapshots"), name="snapshots")
    findings: list[dict[str, object]] = []
    targets = [".python-version"]
    if config.get("workflow_ownership") == "managed":
        targets.append(".github/workflows/check.yml")
    if config.get("script_ownership") == "managed":
        targets.append("scripts/check.py")
    for target in targets:
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
    "sha256:b7b00e3bf4a74e47a19418979925260f73098734c805148ee31384f3e6571b2b",
    "sha256:8c9ba6563c70ea051ad36f2054d41f36aa048ce61d813d100d4e7b25d5e05de0",
    "sha256:22f598ebf1f24e29041289891b3c56131f0acc4dddfed802d92a6a3802eab55f",
    "sha256:cf4aa30c3e2bfb1d69d0cfb7953d1e351db0e6ab06c5812f48cf9eface79a9f7",
}

# Signatures whose targets stay managed only through bounded units in this
# payload; the declarations carry unknown_content_disposition = "preserve", so
# unrecognized bytes become a preserve claim (bounded takeover) instead of a
# blocking PT-LEGACY-MODIFIED finding.
_BOUNDED_TAKEOVER_SIGNATURES = {
    "legacy-agents",
    "legacy-claude",
    "legacy-editorconfig",
    "legacy-vscode-extensions",
    "legacy-vscode-settings",
    "legacy-vscode-tasks",
}


def run_migrate_config(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Preserve the effective performance lane across the 1.9 default change."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    transform = _table(
        snapshots.get("configuration_transform"),
        name="snapshots.configuration_transform",
    )
    raw_config = _table(
        transform.get("raw_config"),
        name="snapshots.configuration_transform.raw_config",
    )
    copied = _json_value(raw_config)
    if not isinstance(copied, dict):
        raise ValueError("configuration transform raw config must be an object")
    config = cast("dict[str, object]", copied)

    effective_ci = _section(_config(request), "ci")
    enabled = effective_ci.get("enabled")
    performance = effective_ci.get("performance")
    if not isinstance(enabled, bool) or not isinstance(performance, bool):
        raise ValueError("config.ci values must be booleans")

    recognized: list[str] = []
    raw_ci = config.get("ci")
    if raw_ci is not None and not isinstance(raw_ci, dict):
        raise ValueError("raw config.ci must be an object")
    if enabled and performance and (raw_ci is None or "performance" not in raw_ci):
        ci: dict[str, object] = {} if raw_ci is None else cast("dict[str, object]", raw_ci)
        ci["performance"] = True
        config["ci"] = ci
        recognized.append("/ci/performance")

    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "python-tooling",
            "version": "1.14",
            "selector": transform.get("selector"),
            "config": config,
            "recognized_settings": recognized,
        },
        "claims": [],
        "findings": [],
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
    for key in (
        "additional_source_roots",
        "additional_dev_dependencies",
        "ruff",
        "pytest",
        "coverage",
        "ci",
        "workflow_ownership",
        "script_ownership",
    ):
        if key in namespace:
            config[key] = _json_value(namespace[key])
            recognized.append(f"/python_tooling/{key}")

    raw_ci = namespace.get("ci")
    if raw_ci is None:
        config["ci"] = {"enabled": True, "performance": True}
    else:
        ci = _table(raw_ci, name="config.ci")
        enabled = ci.get("enabled", True)
        performance = ci.get("performance", True)
        if not isinstance(enabled, bool) or not isinstance(performance, bool):
            raise ValueError("config.ci values must be booleans")
        config["ci"] = {
            "enabled": enabled,
            # Disabled CI had no effective performance lane in 1.8. Record that
            # effective state explicitly so the new fresh default cannot revive it.
            "performance": performance if enabled else False,
        }

    signatures = _table(snapshots.get("legacy_signatures"), name="legacy signatures")
    claims: list[dict[str, object]] = []
    findings: list[dict[str, str]] = []
    # Relinquishable CI signatures: the pointed-at ownership setting lets migration
    # preserve an unrecognized consumer customization instead of blocking on it.
    relinquished = {
        "legacy-check-workflow": (
            namespace.get("workflow_ownership") == "consumer-owned",
            "/python_tooling/workflow_ownership",
        ),
        "legacy-check-script": (
            namespace.get("script_ownership") == "consumer-owned",
            "/python_tooling/script_ownership",
        ),
    }
    for signature_id, (target, ownership, disposition) in _SIGNATURES.items():
        raw = signatures.get(signature_id)
        if not isinstance(raw, Mapping):
            continue
        observed = cast("Mapping[str, object]", raw).get(target)
        if not isinstance(observed, Mapping):
            continue
        state = cast("Mapping[str, object]", observed)
        digest = state.get("digest")
        relinquish, intent_pointer = relinquished.get(signature_id, (False, ""))
        if state.get("known") is True and isinstance(digest, str):
            resolved_disposition = (
                "preserve" if digest in _PRESERVED_CONTAINER_DIGESTS else disposition
            )
            if relinquish:
                ownership = "consumer-owned"
                resolved_disposition = "preserve"
            claims.append(
                {
                    "signature_id": signature_id,
                    "target": target,
                    "observed_digest": digest,
                    "ownership": ownership,
                    "disposition": resolved_disposition,
                }
            )
        elif relinquish and isinstance(digest, str):
            claims.append(
                {
                    "signature_id": signature_id,
                    "target": target,
                    "observed_digest": digest,
                    "ownership": "consumer-owned",
                    "disposition": "preserve",
                    "intent_pointer": intent_pointer,
                }
            )
        elif signature_id in _BOUNDED_TAKEOVER_SIGNATURES and isinstance(digest, str):
            claims.append(
                {
                    "signature_id": signature_id,
                    "target": target,
                    "observed_digest": digest,
                    "ownership": ownership,
                    "disposition": "preserve",
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
