"""Pin the Python Tooling 1.10 gate-script argument, annotation, and exclusion contract."""

import importlib.util
import sys
import tomllib
import types
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V19 = _FAMILY / "versions/1.9"
_V110 = _FAMILY / "versions/1.10"
_V19_RELEASED_DIGEST = "sha256:299356c05185ce85d015abc04ad34c1c476d77b41e400377aa2aa942dbe7ad23"
_SCRIPT_TARGET = "scripts/check.py"
_SETTINGS_TARGET = ".vscode/settings.json"
_FUTURE_IMPORT = "from __future__ import annotations"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(**overrides: object) -> JsonObject:
    payload = _payload(_V110)
    schema = load_option_schema(_V110, payload.manifest)
    return schema.resolve_options(cast("JsonObject", overrides))


def _selectable_python_versions() -> tuple[str, ...]:
    """Read the declared targets so the annotation rule is never pinned to a literal set."""
    payload = _payload(_V110)
    schema = load_option_schema(_V110, payload.manifest)
    properties = schema.document.get("properties")
    if not isinstance(properties, dict):
        raise AssertionError("option schema declares no properties")
    declaration = cast("JsonObject", properties).get("python_version")
    if not isinstance(declaration, dict):
        raise AssertionError("option schema declares no python_version")
    values = cast("JsonObject", declaration).get("enum")
    if not isinstance(values, list) or not values:
        raise AssertionError("python_version declares no enum")
    return tuple(cast(str, value) for value in cast("list[object]", values))


def _render(
    scope: str,
    adapter: AdapterKind,
    config: JsonObject,
    *,
    target: str,
) -> str:
    payload = _payload(_V110)
    result = invoke_provider(
        ProviderInvocation(
            repo=_V110,
            payload=payload,
            standard_id="python-tooling",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={
                "planned_contribution": {
                    "id": "test-unit",
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


def _script_source(config: JsonObject) -> str:
    return _render("$file", AdapterKind.WHOLE_FILE, config, target=_SCRIPT_TARGET)


class _FakeCompletedProcess:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


class _RecordingSubprocess:
    """Stand in for the `subprocess` module inside the rendered script's globals.

    Substituting the module reference keeps the rendered bytes unmodified while
    proving which gate commands the script would have launched, including none.
    """

    def __init__(self, return_codes: Sequence[int] = ()) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._return_codes = list(return_codes)

    def run(self, command: Sequence[str], *, check: bool = False) -> _FakeCompletedProcess:
        assert check is False
        self.calls.append(tuple(command))
        if not self._return_codes:
            return _FakeCompletedProcess(0)
        return _FakeCompletedProcess(self._return_codes.pop(0))


def _load_script(
    tmp_path: Path,
    config: JsonObject,
    return_codes: Sequence[int] = (),
) -> tuple[types.ModuleType, _RecordingSubprocess]:
    path = tmp_path / "check.py"
    path.write_text(_script_source(config), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("rendered_python_tooling_check", path)
    if spec is None or spec.loader is None:
        raise AssertionError("rendered gate script is not importable")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop("rendered_python_tooling_check", None)
    recorder = _RecordingSubprocess(return_codes)
    module.subprocess = recorder  # pyright: ignore[reportAttributeAccessIssue]
    return module, recorder


def _main(module: types.ModuleType, argv: Sequence[str]) -> int:
    entrypoint = cast("object", module.main)
    assert callable(entrypoint)
    return cast(int, entrypoint(list(argv)))


# Issue #51: a help probe must never start the toolchain.
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_python_tooling_1_10__help_flag__prints_usage_and_runs_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flag: str,
) -> None:
    module, recorder = _load_script(tmp_path, _options())

    exit_code = _main(module, [flag])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert recorder.calls == []
    assert captured.out.startswith(f"usage: {_SCRIPT_TARGET}")
    assert captured.err == ""


# Issue #51: an unknown argument is a usage error, not a silent full gate run.
@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["--halp"], id="misspelled-option"),
        pytest.param(["--fix"], id="unsupported-option"),
        pytest.param(["lint"], id="positional"),
        pytest.param(["--", "extra"], id="separator"),
        # A typo must not be excused by a help flag beside it, and `--` ends
        # option parsing, so a help flag after it is a positional.
        pytest.param(["--unknown", "--help"], id="unknown-before-help"),
        pytest.param(["--", "--help"], id="help-after-separator"),
    ],
)
def test_python_tooling_1_10__unknown_argument__fails_without_running_the_gate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    module, recorder = _load_script(tmp_path, _options())

    exit_code = _main(module, argv)

    captured = capsys.readouterr()
    assert exit_code != 0
    assert recorder.calls == []
    assert captured.out == ""
    assert f"unrecognized argument: {argv[0]}" in captured.err


def test_python_tooling_1_10__no_arguments__runs_every_command_in_order(
    tmp_path: Path,
) -> None:
    module, recorder = _load_script(tmp_path, _options())
    commands = cast("tuple[tuple[str, ...], ...]", module.COMMANDS)

    exit_code = _main(module, [])

    assert exit_code == 0
    assert recorder.calls == list(commands)


def test_python_tooling_1_10__failing_command__stops_and_propagates_exit_code(
    tmp_path: Path,
) -> None:
    module, _ = _load_script(tmp_path, _options())
    commands = cast("tuple[tuple[str, ...], ...]", module.COMMANDS)
    assert len(commands) > 2
    module, recorder = _load_script(tmp_path, _options(), return_codes=[0, 3])

    exit_code = _main(module, [])

    assert exit_code == 3
    assert recorder.calls == list(commands[:2])


# Issue #54: the Python Coding 0.6 annotation rule applies from 3.14 on.
def test_python_tooling_1_10__default_target__renders_no_future_import(tmp_path: Path) -> None:
    source = _script_source(_options())

    assert _FUTURE_IMPORT not in source
    assert (_V110 / "resources/check.py").read_text(encoding="utf-8") == source
    module, _ = _load_script(tmp_path, _options())
    assert module.__doc__ is not None


@pytest.mark.parametrize("python_version", _selectable_python_versions())
def test_python_tooling_1_10__selectable_target__gates_future_import_on_314(
    python_version: str,
) -> None:
    source = _script_source(_options(python_version=python_version))

    expected = tuple(int(part) for part in python_version.split(".")) < (3, 14)
    assert (_FUTURE_IMPORT in source) is expected


# Issue #56: MyPy is not a selectable checker, so no MyPy cache key is managed.
@pytest.mark.parametrize("checker", ["basedpyright", "pyright"])
def test_python_tooling_1_10__vscode_settings__declare_no_mypy_cache(checker: str) -> None:
    payload = _payload(_V110)
    config = _options(type_checker={"name": checker, "mode": "strict"})
    settings = [
        contribution
        for contribution in payload.manifest.contributions
        if contribution.target.original == _SETTINGS_TARGET and contribution.materializes(config)
    ]

    assert settings
    for contribution in settings:
        assert "mypy" not in contribution.id
        assert "mypy" not in contribution.scope
        rendered = _render(
            contribution.scope,
            contribution.adapter,
            config,
            target=contribution.target.original,
        )
        assert "mypy" not in rendered


def test_python_tooling_1_10__retired_mypy_scope__is_undeclared() -> None:
    with pytest.raises(ControlPlaneError) as raised:
        _render(
            "key:/files.exclude/**~1.mypy_cache",
            AdapterKind.JSONC,
            _options(),
            target=_SETTINGS_TARGET,
        )

    assert isinstance(raised.value.__cause__, ValueError)
    assert "undeclared VS Code setting scope" in str(raised.value.__cause__)


def test_python_tooling_1_10__package_registration__succeeds_1_9_without_touching_it() -> None:
    predecessor = _payload(_V19)
    successor = _payload(_V110)

    assert predecessor.integrity.aggregate_digest.value == _V19_RELEASED_DIGEST
    assert successor.manifest.payload.version.value == "1.10"
    migrations = {migration.id for migration in successor.manifest.migrations}
    expected = {"legacy-v4-to-1-10"} | {
        f"python-tooling-1-{minor}-to-1-10" for minor in range(1, 10)
    }
    assert migrations == expected
    family = (_FAMILY / "standard.toml").read_text(encoding="utf-8")
    assert 'version = "1.10"' in family
    assert successor.integrity.aggregate_digest.value in family


def test_python_tooling_1_10__catalog_role__selects_the_successor_as_default() -> None:
    """Catalog 5 must actually select the successor these tests pin.

    The payload can be complete and valid while the catalog still selects its
    predecessor; only this row makes the successor the default a consumer on
    `version = "latest"` resolves to.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "python-tooling"
    }

    assert roles["1.10"] == "default"
    assert roles["1.9"] == "retained"
