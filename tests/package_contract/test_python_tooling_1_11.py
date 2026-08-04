"""Pin the Python Tooling 1.11 import-resolution contract (issue #89).

Every payload access happens inside a test behind an existence assertion: while
1.11 is unauthored these tests must FAIL on the missing contract, never error
during collection, so the red signal stays readable.
"""

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
