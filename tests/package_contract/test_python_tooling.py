"""Pin the Python Tooling layout contract against whichever payload Catalog 5 selects.

Version-agnostic on purpose: these rows describe the contract a consumer on
`version = "latest"` actually resolves, so the family carries them forward
instead of freezing them to one payload directory.
"""

import tomllib
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    JsonValue,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"

# Issue #86: a mixed monorepo keeps Python only under selected subproject roots.
# `src` invents a root that does not exist and `flat` sweeps every unrelated
# nested project, and `additional_source_roots` can only append to either.
_EXPLICIT_LAYOUT = "explicit"
_EXPLICIT_SOURCE_ROOTS = ["components/a", "components/b/tool"]
_EXPLICIT_TEST_ROOTS = ["components/a/tests"]
_EXPLICIT_GATE_ROOTS = [*_EXPLICIT_TEST_ROOTS, *_EXPLICIT_SOURCE_ROOTS]


def _selected_version() -> str:
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    packages = cast("list[JsonObject]", catalog["packages"])
    selected = [
        package
        for package in packages
        if package["id"] == "python-tooling" and package["role"] == "default"
    ]
    assert len(selected) == 1, "Catalog 5 must select exactly one default python-tooling payload"
    return cast(str, selected[0]["version"])


def _payload_root() -> Path:
    root = _FAMILY / f"versions/{_selected_version()}"
    assert (root / "payload.toml").is_file(), f"selected payload {root.name} declares no manifest"
    return root


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, **overrides: object) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(cast("JsonObject", overrides))


def _render(
    root: Path,
    scope: str,
    config: JsonObject,
    *,
    adapter: AdapterKind = AdapterKind.TOML,
    target: str = "pyproject.toml",
) -> str:
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
                    "id": "layout-scope",
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


def _table(root: Path, scope: str, config: JsonObject, *path: str) -> JsonValue:
    document = cast("JsonObject", tomllib.loads(_render(root, scope, config)))
    current: JsonValue = cast("JsonValue", document)
    for key in path:
        current = cast("JsonObject", current)[key]
    return current


def _ruff_gate_targets(root: Path, config: JsonObject) -> list[str]:
    """Read the managed gate's own Ruff argv rather than re-deriving it here."""
    script = _render(
        root,
        "$file",
        config,
        adapter=AdapterKind.WHOLE_FILE,
        target="scripts/check.py",
    )
    namespace: dict[str, object] = {}
    exec(compile(script, "check.py", "exec"), namespace)
    commands = cast("tuple[tuple[str, ...], ...]", namespace["COMMANDS"])
    formatting = next(command for command in commands if "ruff" in command and "format" in command)
    argv = list(formatting[formatting.index("ruff") :])
    # argv[0:2] is `ruff format`; everything else that is not a flag is a root.
    return [part for part in argv[2:] if not part.startswith("-")]


def _declared_layout_modes(root: Path) -> list[str]:
    schema = load_option_schema(root, _payload(root).manifest)
    properties = cast("JsonObject", schema.document["properties"])
    declaration = cast("JsonObject", properties["source_layout"])
    return cast("list[str]", declaration["enum"])


def _require_explicit_mode(root: Path) -> None:
    assert _EXPLICIT_LAYOUT in _declared_layout_modes(root), (
        f"{root.name} declares no {_EXPLICIT_LAYOUT!r} source layout"
    )


def _gate_surfaces(root: Path, config: JsonObject) -> dict[str, object]:
    return {
        "include": _table(root, "key:/tool/basedpyright/include", config, "tool", "basedpyright"),
        "extraPaths": _table(
            root, "key:/tool/basedpyright/extraPaths", config, "tool", "basedpyright"
        ),
        "coverage": _table(root, "table:/tool/coverage/run", config, "tool", "coverage", "run"),
        "ruff": _table(root, "table:/tool/ruff", config, "tool", "ruff"),
        "targets": _ruff_gate_targets(root, config),
    }


def test_python_tooling__explicit_layout__bounds_every_gate_to_declared_roots() -> None:
    """The declared roots are the whole gate: no invented `src`, no repository sweep."""
    root = _payload_root()
    config = _options(
        root,
        source_layout=_EXPLICIT_LAYOUT,
        additional_source_roots=_EXPLICIT_SOURCE_ROOTS,
        pytest={"test_paths": _EXPLICIT_TEST_ROOTS},
    )

    surfaces = _gate_surfaces(root, config)

    include = cast("JsonObject", surfaces["include"])["include"]
    extra_paths = cast("JsonObject", surfaces["extraPaths"])["extraPaths"]
    coverage = cast("JsonObject", surfaces["coverage"])["source"]
    ruff = cast("JsonObject", surfaces["ruff"])["src"]
    assert include == _EXPLICIT_GATE_ROOTS
    assert extra_paths == _EXPLICIT_SOURCE_ROOTS
    assert coverage == _EXPLICIT_SOURCE_ROOTS
    assert ruff == _EXPLICIT_GATE_ROOTS
    assert surfaces["targets"] == _EXPLICIT_GATE_ROOTS
    assert _table(root, "key:/tool/pytest/ini_options/testpaths", config, "tool", "pytest") == {
        "ini_options": {"testpaths": _EXPLICIT_TEST_ROOTS}
    }
    # Compare root VALUES, never the rendered text: `[tool.ruff].src` is a key
    # name, so a substring check would read it as an implicit "src" root.
    rendered_roots = [
        *cast("list[str]", include),
        *cast("list[str]", extra_paths),
        *cast("list[str]", coverage),
        *cast("list[str]", ruff),
        *cast("list[str]", surfaces["targets"]),
    ]
    assert "src" not in rendered_roots
    assert "." not in rendered_roots


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param({}, id="no-declaration"),
        pytest.param({"additional_source_roots": []}, id="empty-declaration"),
    ],
)
def test_python_tooling__explicit_layout_without_roots__fails_closed(
    declared: JsonObject,
) -> None:
    """A layout with no implicit root and no declared root is a hollow gate."""
    root = _payload_root()
    # Without this guard the rejection below would also pass while the mode is
    # simply unknown to the enum, which proves nothing about the empty case.
    _require_explicit_mode(root)

    with pytest.raises(PackageContractError, match="package options violate schema"):
        _options(root, source_layout=_EXPLICIT_LAYOUT, **declared)


@pytest.mark.parametrize(
    ("layout", "expected"),
    [
        pytest.param(
            "src",
            {
                "include": ["src", "tests"],
                "extraPaths": ["src"],
                "coverage": ["src"],
                "ruff": ["src", "tests"],
                "targets": ["src", "tests"],
            },
            id="src",
        ),
        pytest.param(
            "flat",
            {
                "include": [".", "tests"],
                "extraPaths": ["."],
                "coverage": ["."],
                "ruff": [".", "tests"],
                "targets": [".", "tests"],
            },
            id="flat",
        ),
    ],
)
def test_python_tooling__released_layouts__are_unchanged_by_the_explicit_mode(
    layout: str,
    expected: JsonObject,
) -> None:
    """Adding a third mode may not move one byte of the two published ones."""
    root = _payload_root()
    config = _options(root, source_layout=layout)

    surfaces = _gate_surfaces(root, config)

    assert cast("JsonObject", surfaces["include"])["include"] == expected["include"]
    assert cast("JsonObject", surfaces["extraPaths"])["extraPaths"] == expected["extraPaths"]
    assert cast("JsonObject", surfaces["coverage"])["source"] == expected["coverage"]
    assert cast("JsonObject", surfaces["ruff"])["src"] == expected["ruff"]
    assert surfaces["targets"] == expected["targets"]


def test_python_tooling__declared_layout_modes__are_exactly_the_supported_set() -> None:
    """The schema enum is the contract a consumer reads before choosing a mode."""
    root = _payload_root()
    schema = load_option_schema(root, _payload(root).manifest)
    properties = cast("JsonObject", schema.document["properties"])
    declaration = cast("JsonObject", properties["source_layout"])

    assert _declared_layout_modes(root) == ["src", "flat", _EXPLICIT_LAYOUT]
    assert declaration["default"] == "src"
