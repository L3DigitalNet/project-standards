"""Pin the Python Tooling 1.11 import-resolution contract (issue #89).

Every payload access happens inside a test behind an existence assertion: while
1.11 is unauthored these tests must FAIL on the missing contract, never error
during collection, so the red signal stays readable.
"""

import json
import os
import subprocess
import tomllib
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V110 = _FAMILY / "versions/1.10"
_V111 = _FAMILY / "versions/1.11"
_EXTRA_PATHS_SCOPE = "key:/tool/basedpyright/extraPaths"
_TOOLING_ROOT = "tooling"


def _require_payload(root: Path) -> None:
    assert root.is_dir(), f"python-tooling payload {root.name} is not authored yet"
    assert (root / "payload.toml").is_file(), f"payload {root.name} declares no manifest"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, **overrides: object) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(cast("JsonObject", overrides))


def _render(root: Path, scope: str, config: JsonObject) -> str:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={
                "planned_contribution": {
                    "id": "import-roots",
                    "target": "pyproject.toml",
                    "adapter": AdapterKind.TOML.value,
                    "scope": scope,
                }
            },
        )
    )
    assert result.effect is ProviderEffect.CONTENT
    assert result.content is not None
    return result.content.decode()


def _checker_table(rendered: str, table: str) -> JsonObject:
    parsed = tomllib.loads(rendered)
    tools = cast("JsonObject", parsed["tool"])
    return cast("JsonObject", tools[table])


def _checker_source(root: Path, config: JsonObject, table: str = "basedpyright") -> str:
    """Compose the checker table from every key scope the payload declares.

    Reading the key set from the manifest rather than a literal list is what lets
    the same helper render 1.10 and 1.11: the successor's added import-root key
    joins the rendered table without the test naming it twice.
    """
    prefix = f"key:/tool/{table}/"
    lines = [f"[tool.{table}]"]
    for contribution in _payload(root).manifest.contributions:
        if contribution.target.original != "pyproject.toml":
            continue
        if not contribution.scope.startswith(prefix):
            continue
        rendered = _render(root, contribution.scope, config)
        lines.extend(line for line in rendered.splitlines() if not line.startswith("[tool."))
    return "\n".join(lines) + "\n"


# Issue #89: `include` selects the files to check; it never sets import-resolution
# precedence. Without a declared import root the editable installation of the
# consumer's own package answers first, and with no py.typed marker strict mode
# calls every local import an untyped third-party import.
def test_python_tooling_1_11__import_roots__are_declared_for_both_checkers() -> None:
    _require_payload(_V111)
    manifest = _payload(_V111).manifest
    declarations = {
        contribution.scope: contribution
        for contribution in manifest.contributions
        if contribution.target.original == "pyproject.toml"
    }

    assert _EXTRA_PATHS_SCOPE in declarations
    assert "key:/tool/pyright/extraPaths" in declarations
    declaration = declarations[_EXTRA_PATHS_SCOPE]
    assert declaration.policy is ArtifactPolicy.MANAGED
    assert declaration.adapter is AdapterKind.TOML
    assert set(declaration.governing_options or ()) >= {
        "source_layout",
        "additional_source_roots",
    }


@pytest.mark.parametrize(
    ("layout", "expected_root"),
    [("src", "src"), ("flat", ".")],
)
def test_python_tooling_1_11__layout_root__resolves_before_every_other_root(
    layout: str,
    expected_root: str,
) -> None:
    _require_payload(_V111)
    config = _options(
        _V111,
        source_layout=layout,
        additional_source_roots=[{"path": _TOOLING_ROOT, "coverage": False}],
    )

    rendered = _render(_V111, _EXTRA_PATHS_SCOPE, config)

    values = cast("list[str]", _checker_table(rendered, "basedpyright")["extraPaths"])
    assert values[0] == expected_root
    assert _TOOLING_ROOT in values
    assert len(values) == len(set(values))


def _write_editable_fixture(repo: Path, checker_table: str) -> None:
    """Materialize issue #89's shape: src layout, editable install, no py.typed."""
    (repo / "src/example_package").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / f"{_TOOLING_ROOT}/helper").mkdir(parents=True)
    (repo / f"{_TOOLING_ROOT}/helper/__init__.py").write_text(
        'def helper() -> str:\n    return "helper"\n',
        encoding="utf-8",
    )
    (repo / "src/example_package/__init__.py").write_text(
        'from example_package.module import greet\n\n__all__ = ["greet"]\n',
        encoding="utf-8",
    )
    (repo / "src/example_package/module.py").write_text(
        'def greet(name: str) -> str:\n    return f"hello {name}"\n',
        encoding="utf-8",
    )
    (repo / "tests/test_example.py").write_text(
        "from example_package.module import greet\n\n\n"
        'def test_greet() -> None:\n    assert greet("world") == "hello world"\n',
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "[project]\n"
        'name = "example-package"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.14"\n'
        "dependencies = []\n\n"
        "[build-system]\n"
        'requires = ["uv_build>=0.11,<0.12"]\n'
        'build-backend = "uv_build"\n\n'
        "[dependency-groups]\n"
        'dev = ["basedpyright"]\n\n'
        f"{checker_table}",
        encoding="utf-8",
    )


def _run(repo: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    # The fixture must resolve imports from its own editable environment alone:
    # this suite runs with the extracted wheel runtime on PYTHONPATH and inside
    # the repository's virtualenv, and either would enter the checker's search
    # paths and mask the very ordering under test.
    environment = {
        key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "VIRTUAL_ENV"}
    }
    environment["UV_OFFLINE"] = "1"
    return subprocess.run(
        command,
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _basedpyright_output(repo: Path) -> str:
    synced = _run(repo, ["uv", "sync", "--quiet"])
    if synced.returncode != 0:
        output = synced.stdout + synced.stderr
        if "cache" in output.lower() or "offline" in output.lower():
            pytest.fail(f"offline oracle is missing a locked cache entry:\n{output}")
        pytest.fail(f"editable fixture could not be synced:\n{output}")
    result = _run(repo, ["uv", "run", "basedpyright", "--verbose", "tests/test_example.py"])
    return result.stdout + result.stderr


# TC-T17-001: the acceptance is behavioral, so the oracle is the real checker over
# a real editable install. The 1.10 rendering is the negative control — it must
# still reproduce the reported failure on the same bytes.
def test_python_tooling_1_11__editable_install__never_resolves_before_local_source(
    tmp_path: Path,
) -> None:
    _require_payload(_V110)
    _require_payload(_V111)
    baseline_config = _options(_V110, source_layout="src")
    # The reported consumer already owned one unrelated extraPaths root, which is
    # what displaced the editor-derived src entry; 1.11 must own that list instead.
    baseline_table = _checker_source(_V110, baseline_config).replace(
        "[tool.basedpyright]\n",
        f'[tool.basedpyright]\nextraPaths = ["{_TOOLING_ROOT}"]\n',
    )
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    _write_editable_fixture(baseline, baseline_table)

    assert "reportMissingTypeStubs" in _basedpyright_output(baseline)

    managed_config = _options(
        _V111,
        source_layout="src",
        additional_source_roots=[{"path": _TOOLING_ROOT, "coverage": False}],
    )
    managed = tmp_path / "managed"
    managed.mkdir()
    _write_editable_fixture(managed, _checker_source(_V111, managed_config))

    output = _basedpyright_output(managed)

    assert "reportMissingTypeStubs" not in output
    assert "0 errors" in output
    assert not (managed / "src/example_package/py.typed").exists()


def test_python_tooling_1_11__released_predecessor__keeps_its_exact_bytes() -> None:
    _require_payload(_V110)
    manifest = load_payload_manifest(_V110 / "payload.toml")
    scopes = {contribution.scope for contribution in manifest.contributions}

    assert _EXTRA_PATHS_SCOPE not in scopes
    assert validate_payload_integrity(_V110, manifest).aggregate_digest.value.startswith("sha256:")


def test_python_tooling_1_11__package_registration__succeeds_1_10_without_touching_it() -> None:
    """The payload can be valid while nothing selects it; these rows do the selecting."""
    _require_payload(_V111)
    successor = _payload(_V111)
    migrations = {migration.id for migration in successor.manifest.migrations}
    expected = {"legacy-v4-to-1-11"} | {
        f"python-tooling-1-{minor}-to-1-11" for minor in range(1, 11)
    }
    family = (_FAMILY / "standard.toml").read_text(encoding="utf-8")
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[JsonObject]", catalog["packages"])
        if package["id"] == "python-tooling"
    }

    assert successor.manifest.payload.version.value == "1.11"
    assert migrations == expected
    assert 'version = "1.11"' in family
    assert successor.integrity.aggregate_digest.value in family
    assert roles["1.11"] == "default"
    assert roles["1.10"] == "retained"


_RUFF_TEST_ROOT = "qa/unit"
_DECLARED_RUFF_TARGETS = ("src", _RUFF_TEST_ROOT, _TOOLING_ROOT)
_UNBOUNDED = ("nested/src/nested_module.py", "local_scratch.py", "scripts/undeclared.py")


def _bounded_config(root: Path) -> JsonObject:
    return _options(
        root,
        source_layout="src",
        additional_source_roots=[_TOOLING_ROOT],
        pytest={"test_paths": [_RUFF_TEST_ROOT]},
    )


def _rendered(root: Path, scope: str, adapter: AdapterKind, config: JsonObject, target: str) -> str:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={
                "planned_contribution": {
                    "id": "ruff-scope",
                    "target": target,
                    "adapter": adapter.value,
                    "scope": scope,
                }
            },
        )
    )
    assert result.effect is ProviderEffect.CONTENT
    assert result.content is not None
    return result.content.decode()


_ARGV_PUNCTUATION = str.maketrans(dict.fromkeys("(){}[]\",'", " "))


def _ruff_invocations(text: str) -> list[list[str]]:
    """Return every rendered ruff argv, however its surface spells the command.

    The same command is spelled four ways across this payload — a Python tuple
    literal, a shell line, a Markdown code block, and a `&&`-joined VS Code task
    — so the shared reading is "split shell conjunctions, drop the punctuation
    each spelling adds, then take everything from `ruff` onward".
    """
    invocations: list[list[str]] = []
    for line in text.splitlines():
        for segment in line.replace("&&", "\n").splitlines():
            words = segment.translate(_ARGV_PUNCTUATION).split()
            if "ruff" not in words:
                continue
            invocations.append(words[words.index("ruff") :])
    return invocations


def _ruff_targets(argv: list[str]) -> list[str]:
    return [word for word in argv[2:] if not word.startswith("-")]


def _command_text_of(target: str, rendered: str) -> str:
    """Reduce one rendered surface to just the shell text it declares.

    A VS Code task renders its command as a JSON string beside sibling keys, so
    scanning the raw document would read `problemMatcher` as a command argument.
    Every other surface is already shell text or a literal argv.
    """
    if not target.endswith(".json"):
        return rendered
    document = cast("JsonObject", json.loads(rendered))
    tasks = cast("list[JsonObject]", document["tasks"])
    return "\n".join(str(task["command"]) for task in tasks)


# Issue #95: BasedPyright and coverage are bounded to declared roots while Ruff
# is handed ".", so the managed gate sweeps every discoverable Python file —
# independent nested projects and machine-specific scripts included.
@pytest.mark.parametrize(
    ("scope", "adapter", "target"),
    [
        pytest.param("$file", AdapterKind.WHOLE_FILE, "scripts/check.py", id="check-script"),
        pytest.param(
            "$file",
            AdapterKind.WHOLE_FILE,
            ".github/workflows/check.yml",
            id="ci-workflow",
        ),
        pytest.param(
            "block:python-tooling",
            AdapterKind.MARKDOWN_BLOCK,
            "AGENTS.md",
            id="agent-instructions",
        ),
        pytest.param(
            "keyed-set:/tasks#label=check",
            AdapterKind.JSONC,
            ".vscode/tasks.json",
            id="vscode-check-task",
        ),
        pytest.param(
            "keyed-set:/tasks#label=fix",
            AdapterKind.JSONC,
            ".vscode/tasks.json",
            id="vscode-fix-task",
        ),
    ],
)
def test_python_tooling_1_11__ruff_scope__names_every_declared_root_and_nothing_else(
    scope: str,
    adapter: AdapterKind,
    target: str,
) -> None:
    _require_payload(_V111)
    rendered = _rendered(_V111, scope, adapter, _bounded_config(_V111), target)

    invocations = _ruff_invocations(_command_text_of(target, rendered))

    assert invocations, f"{target} renders no ruff command"
    for argv in invocations:
        targets = _ruff_targets(argv)
        assert targets == list(_DECLARED_RUFF_TARGETS), argv
        assert "." not in argv, argv


def _write_ruff_corpus(repo: Path, ruff_table: str) -> dict[str, bytes]:
    """Materialize issue #95's shape and return every file's pre-run bytes."""
    unformatted = {
        "src/example_package/module.py": b'def greet( name ):\n    return "hi"\n',
        f"{_RUFF_TEST_ROOT}/test_module.py": b"def test_greet( ):\n    assert True\n",
        f"{_TOOLING_ROOT}/helper.py": b"def helper( ):\n    return 1\n",
        # Out of every declared root: an independent uv project, a machine-local
        # scratch file, and an undeclared script directory.
        "nested/src/nested_module.py": b"def nested_thing( ):\n    return 2\n",
        "local_scratch.py": b"def machine_specific( ):\n    return 3\n",
        "scripts/undeclared.py": b"def undeclared( ):\n    return 4\n",
    }
    for relative, content in unformatted.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (repo / "nested/pyproject.toml").write_text(
        '[project]\nname = "nested"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "[project]\n"
        'name = "example-package"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.14"\n\n'
        f"{ruff_table}",
        encoding="utf-8",
    )
    return unformatted


def _script_commands(source: str) -> list[list[str]]:
    namespace: dict[str, object] = {}
    exec(compile(source, "check.py", "exec"), namespace)
    commands = cast("tuple[tuple[str, ...], ...]", namespace["COMMANDS"])
    return [list(command) for command in commands]


# TC-T18-001: the acceptance is about which files the managed command touches, so
# the oracle is a real `ruff format` run driven by the rendered argv.
def test_python_tooling_1_11__managed_ruff_format__rewrites_only_declared_roots(
    tmp_path: Path,
) -> None:
    _require_payload(_V111)
    config = _bounded_config(_V111)
    repo = tmp_path / "consumer"
    repo.mkdir()
    before = _write_ruff_corpus(
        repo,
        _rendered(_V111, "table:/tool/ruff", AdapterKind.TOML, config, "pyproject.toml"),
    )
    script = _rendered(_V111, "$file", AdapterKind.WHOLE_FILE, config, "scripts/check.py")
    format_command = next(
        command for command in _script_commands(script) if "ruff" in command and "format" in command
    )

    environment = {
        key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "VIRTUAL_ENV"}
    }
    environment.update({"UV_OFFLINE": "1", "UV_PROJECT": str(_ROOT)})
    result = subprocess.run(
        [part for part in format_command if part != "--check"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    if "cache" in output.lower() and result.returncode != 0:
        pytest.fail(f"offline oracle is missing a locked cache entry:\n{output}")
    for relative in _UNBOUNDED:
        assert (repo / relative).read_bytes() == before[relative], relative
    for relative in (
        "src/example_package/module.py",
        f"{_RUFF_TEST_ROOT}/test_module.py",
        f"{_TOOLING_ROOT}/helper.py",
    ):
        assert (repo / relative).read_bytes() != before[relative], relative
