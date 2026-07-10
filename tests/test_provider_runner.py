from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

import project_standards.provider_runner as provider_runner
from project_standards.adopt.errors import ManifestError, UsageError
from project_standards.provider_runner import (
    load_packaged_standard_manifest,
    run_packaged_providers,
)
from project_standards.standard_manifest import ProviderOperation, StandardManifestError


def _write_bundle(root: Path, providers: str, *, standard_id: str = "demo") -> Path:
    bundle = root / standard_id
    bundle.mkdir(parents=True)
    (bundle / "standard.toml").write_text(
        f'[standard]\nid = "{standard_id}"\nname = "Demo"\nstatus = "active"\n'
        'summary = "Demo."\nadoption = "cli"\n\n[versions]\nsupported = ["1.0"]\n'
        'latest = "1.0"\n\n[config]\nnamespaces = []\n\n[capabilities]\n'
        "provides = []\nconsumes_platform = []\n\n[relations]\ncompanions = []\n"
        'extends = []\nconflicts = []\n\n[resources]\nreadme = "README.md"\n'
        f'adopt = "adopt.md"\n\n{providers}',
        encoding="utf-8",
    )
    (bundle / "README.md").write_text("# Demo\n", encoding="utf-8")
    (bundle / "adopt.md").write_text("# Adopt\n", encoding="utf-8")
    return bundle


def _python_provider(operation: str, entrypoint: str) -> str:
    return (
        "[[providers]]\n"
        f'operation = "{operation}"\n'
        'kind = "python"\n'
        f'entrypoint = "{entrypoint}"\n'
        "optional = false\n"
    )


def _install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    provider: Callable[[list[str]], object] | object,
) -> None:
    module = ModuleType(name)
    module.__dict__["main"] = provider
    monkeypatch.setitem(sys.modules, name, module)


def test_run_packaged_providers_calls_declared_entrypoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))
    called: list[list[str]] = []

    def main(argv: list[str]) -> int:
        called.append(list(argv))
        argv.append("provider-mutation")
        return 0

    _install_module(monkeypatch, "demo_provider", main)
    argv = ["--json"]

    rc = run_packaged_providers("demo", ProviderOperation.VALIDATE, argv, bundles_dir=tmp_path)

    assert rc == 0
    assert called == [["--json"]]
    assert argv == ["--json"]


def test_load_packaged_standard_manifest_rejects_missing_manifest(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="packaged standard manifest missing") as exc_info:
        load_packaged_standard_manifest("demo", bundles_dir=tmp_path)

    assert exc_info.value.exit_code == 3


def test_load_packaged_standard_manifest_accepts_canonical_hyphenated_id(
    tmp_path: Path,
) -> None:
    _write_bundle(
        tmp_path,
        _python_provider("validate", "demo_provider:main"),
        standard_id="demo-standard",
    )

    manifest = load_packaged_standard_manifest("demo-standard", bundles_dir=tmp_path)

    assert manifest.standard.id == "demo-standard"


def test_load_packaged_standard_manifest_wraps_invalid_manifest(tmp_path: Path) -> None:
    bundle = tmp_path / "demo"
    bundle.mkdir()
    (bundle / "standard.toml").write_text("not valid = [", encoding="utf-8")

    with pytest.raises(ManifestError, match="packaged standard manifest is invalid") as exc_info:
        load_packaged_standard_manifest("demo", bundles_dir=tmp_path)

    assert exc_info.value.exit_code == 3
    assert isinstance(exc_info.value.__cause__, StandardManifestError)


@pytest.mark.parametrize(
    "standard_id",
    [
        "",
        ".",
        "..",
        "../demo",
        "nested/demo",
        "nested\\demo",
        "C:demo",
        "Demo",
        "demo_name",
        "-demo",
        "demo-",
        "demo..name",
    ],
)
def test_load_packaged_standard_manifest_rejects_noncanonical_id(
    tmp_path: Path, standard_id: str
) -> None:
    with pytest.raises(ManifestError) as exc_info:
        load_packaged_standard_manifest(standard_id, bundles_dir=tmp_path)

    assert str(exc_info.value) == "invalid packaged standard id"
    assert exc_info.value.exit_code == 3


def test_load_packaged_standard_manifest_rejects_absolute_id_before_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside_bundle = _write_bundle(
        tmp_path / "outside", _python_provider("validate", "demo_provider:main")
    )
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()
    loaded: list[Path] = []

    def record_load(path: Path) -> object:
        loaded.append(path)
        raise AssertionError("outside manifest was read")

    monkeypatch.setattr(provider_runner, "load_standard_manifest", record_load)

    with pytest.raises(ManifestError) as exc_info:
        load_packaged_standard_manifest(str(outside_bundle), bundles_dir=bundles_dir)

    assert str(exc_info.value) == "invalid packaged standard id"
    assert exc_info.value.exit_code == 3
    assert loaded == []


def test_load_packaged_standard_manifest_rejects_symlink_escape_before_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside_bundle = _write_bundle(
        tmp_path / "outside", _python_provider("validate", "demo_provider:main")
    )
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()
    (bundles_dir / "demo").symlink_to(outside_bundle, target_is_directory=True)
    loaded: list[Path] = []

    def record_load(path: Path) -> object:
        loaded.append(path)
        raise AssertionError("outside manifest was read")

    monkeypatch.setattr(provider_runner, "load_standard_manifest", record_load)

    with pytest.raises(ManifestError) as exc_info:
        load_packaged_standard_manifest("demo", bundles_dir=bundles_dir)

    assert str(exc_info.value) == "packaged standard manifest escapes bundles directory"
    assert exc_info.value.exit_code == 3
    assert loaded == []


def test_load_packaged_standard_manifest_does_not_echo_invalid_manifest_content(
    tmp_path: Path,
) -> None:
    secret = "provider-secret-material"
    bundle = _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))
    manifest_path = bundle / "standard.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8") + f'\n[unknown]\nsecret = "{secret}"\n',
        encoding="utf-8",
    )

    with pytest.raises(ManifestError) as exc_info:
        load_packaged_standard_manifest("demo", bundles_dir=tmp_path)

    assert str(exc_info.value) == f"packaged standard manifest is invalid: {manifest_path}"
    assert secret not in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, StandardManifestError)


def test_run_packaged_providers_rejects_unavailable_operation(tmp_path: Path) -> None:
    _write_bundle(tmp_path, _python_provider("lint", "demo_provider:main"))

    with pytest.raises(
        UsageError, match="does not declare provider operation validate"
    ) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert exc_info.value.exit_code == 2


def test_run_packaged_providers_does_not_invoke_documentation_only_provider(
    tmp_path: Path,
) -> None:
    _write_bundle(
        tmp_path,
        '[[providers]]\noperation = "validate"\nkind = "documentation-only"\noptional = false\n',
    )

    with pytest.raises(UsageError, match="does not declare executable provider operation validate"):
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)


def test_run_packaged_providers_skips_documentation_only_alongside_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    providers = (
        '[[providers]]\noperation = "validate"\nkind = "documentation-only"\n'
        "optional = false\n\n" + _python_provider("validate", "demo_provider:main")
    )
    _write_bundle(tmp_path, providers)
    called: list[list[str]] = []

    def main(argv: list[str]) -> int:
        called.append(argv)
        return 0

    _install_module(monkeypatch, "demo_provider", main)

    assert (
        run_packaged_providers("demo", ProviderOperation.VALIDATE, ["--json"], bundles_dir=tmp_path)
        == 0
    )
    assert called == [["--json"]]


@pytest.mark.parametrize(
    "entrypoint",
    ["demo_provider", "demo_provider:main:extra", ":main", "demo_provider:"],
)
def test_run_packaged_providers_wraps_manifest_with_malformed_entrypoint(
    tmp_path: Path, entrypoint: str
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", entrypoint))

    with pytest.raises(ManifestError) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert isinstance(exc_info.value.__cause__, StandardManifestError)


def test_run_packaged_providers_wraps_import_failure(tmp_path: Path) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "module_does_not_exist:main"))

    with pytest.raises(ManifestError, match="cannot import Python provider") as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert isinstance(exc_info.value.__cause__, ImportError)


def test_run_packaged_providers_wraps_import_system_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    def abort_import(_module_name: str) -> ModuleType:
        raise SystemExit("provider-secret-material")

    monkeypatch.setattr(provider_runner, "import_module", abort_import)

    with pytest.raises(ManifestError) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert str(exc_info.value) == "cannot import Python provider demo_provider:main (SystemExit)"
    assert exc_info.value.exit_code == 3
    assert isinstance(exc_info.value.__cause__, SystemExit)


def test_run_packaged_providers_wraps_dynamic_attribute_system_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))
    module = ModuleType("demo_provider")

    def abort_attribute(_name: str) -> object:
        raise SystemExit("provider-secret-material")

    module.__dict__["__getattr__"] = abort_attribute
    monkeypatch.setitem(sys.modules, "demo_provider", module)

    with pytest.raises(ManifestError) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert str(exc_info.value) == "cannot resolve Python provider demo_provider:main (SystemExit)"
    assert exc_info.value.exit_code == 3
    assert isinstance(exc_info.value.__cause__, SystemExit)


def test_run_packaged_providers_wraps_missing_attribute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))
    monkeypatch.setitem(sys.modules, "demo_provider", ModuleType("demo_provider"))

    with pytest.raises(ManifestError, match="has no attribute 'main'") as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert isinstance(exc_info.value.__cause__, AttributeError)


def test_run_packaged_providers_rejects_non_callable_attribute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))
    _install_module(monkeypatch, "demo_provider", object())

    with pytest.raises(ManifestError, match="is not callable") as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert exc_info.value.__cause__ is None


def test_run_packaged_providers_wraps_provider_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    def main(_argv: list[str]) -> int:
        raise RuntimeError("provider failed")

    _install_module(monkeypatch, "demo_provider", main)

    with pytest.raises(
        ManifestError, match="Python provider demo_provider:main failed"
    ) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_run_packaged_providers_wraps_call_system_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    def main(_argv: list[str]) -> int:
        raise SystemExit("provider-secret-material")

    _install_module(monkeypatch, "demo_provider", main)

    with pytest.raises(ManifestError) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert str(exc_info.value) == "Python provider demo_provider:main failed (SystemExit)"
    assert exc_info.value.exit_code == 3
    assert isinstance(exc_info.value.__cause__, SystemExit)


def test_run_packaged_providers_allows_keyboard_interrupt_to_propagate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    def main(_argv: list[str]) -> int:
        raise KeyboardInterrupt

    _install_module(monkeypatch, "demo_provider", main)

    with pytest.raises(KeyboardInterrupt):
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)


def test_run_packaged_providers_formats_broken_exception_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    class BrokenStringError(RuntimeError):
        def __str__(self) -> str:
            raise RuntimeError("secondary formatting failure")

    def main(_argv: list[str]) -> int:
        raise BrokenStringError("provider-secret-material")

    _install_module(monkeypatch, "demo_provider", main)

    with pytest.raises(ManifestError) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert str(exc_info.value) == ("Python provider demo_provider:main failed (BrokenStringError)")
    assert exc_info.value.exit_code == 3
    assert isinstance(exc_info.value.__cause__, BrokenStringError)


def test_run_packaged_providers_does_not_echo_provider_exception_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "provider-secret-material"
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    def main(_argv: list[str]) -> int:
        raise TypeError(secret)

    _install_module(monkeypatch, "demo_provider", main)

    with pytest.raises(ManifestError) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert str(exc_info.value) == "Python provider demo_provider:main failed (TypeError)"
    assert secret not in str(exc_info.value)
    assert exc_info.value.exit_code == 3
    assert isinstance(exc_info.value.__cause__, TypeError)


@pytest.mark.parametrize("result", [True, None, "0", -1, 256])
def test_run_packaged_providers_rejects_invalid_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: object
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    def main(_argv: list[str]) -> object:
        return result

    _install_module(monkeypatch, "demo_provider", main)

    with pytest.raises(ManifestError, match="returned invalid exit code"):
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)


def test_run_packaged_providers_formats_invalid_result_with_broken_repr_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, _python_provider("validate", "demo_provider:main"))

    class BrokenResult:
        def __repr__(self) -> str:
            raise RuntimeError("secondary formatting failure")

    def main(_argv: list[str]) -> object:
        return BrokenResult()

    _install_module(monkeypatch, "demo_provider", main)

    with pytest.raises(ManifestError) as exc_info:
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)

    assert str(exc_info.value) == (
        "Python provider demo_provider:main returned invalid exit code type BrokenResult"
    )
    assert exc_info.value.exit_code == 3


def test_run_packaged_providers_runs_python_providers_in_declared_order_and_returns_maximum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    providers = "\n".join(
        _python_provider("validate", f"provider_{name}:main")
        for name in ("first", "second", "third")
    )
    _write_bundle(tmp_path, providers)
    called: list[tuple[str, list[str]]] = []

    for name, exit_code in (("first", 1), ("second", 3), ("third", 2)):

        def main(argv: list[str], *, _name: str = name, _exit_code: int = exit_code) -> int:
            called.append((_name, list(argv)))
            argv.append(_name)
            return _exit_code

        _install_module(monkeypatch, f"provider_{name}", main)

    argv = ["--json"]
    rc = run_packaged_providers("demo", ProviderOperation.VALIDATE, argv, bundles_dir=tmp_path)

    assert rc == 3
    assert called == [
        ("first", ["--json"]),
        ("second", ["--json"]),
        ("third", ["--json"]),
    ]
    assert argv == ["--json"]


@pytest.mark.parametrize("kind", ["command", "workflow"])
def test_run_packaged_providers_rejects_non_python_executable_kind(
    tmp_path: Path, kind: str
) -> None:
    _write_bundle(
        tmp_path,
        f'[[providers]]\noperation = "validate"\nkind = "{kind}"\n'
        'entrypoint = "external-tool"\noptional = false\n',
    )

    with pytest.raises(ManifestError, match=f"unsupported executable provider kind {kind}"):
        run_packaged_providers("demo", ProviderOperation.VALIDATE, [], bundles_dir=tmp_path)
