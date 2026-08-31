"""Pin the Python Tooling 1.16 `uv_build` requirement contract.

Issue #182: the rendered `[build-system]` table pinned `uv_build>=0.11,<0.12`, a
single-minor window. uv checks whether its own version satisfies that requirement
before taking the in-process fast path for its own backend, and warns
``build_system.requires = [...] does not contain the current uv version 0.12.3``
when it does not. Because uv_build ships in lockstep with uv and uv releases a new
minor regularly, any single-minor window turns every managed adoption into
compatibility noise the day uv's next minor lands — and a released payload's bytes
are immutable, so the package cannot chase it.

1.16 widens the window to the whole pre-1.0 uv_build series. The bound is verified
by containment, not by string shape: the property that matters is that a supported
uv is inside it. An unbounded requirement is not an option — uv warns about that
too (``is missing an upper bound on the `uv_build` version``), because an
unbounded sdist breaks when a future breaking uv_build ships.

Everything else in the payload is a copy of 1.15, so the second contract here is
that no other rendered unit and no option moved.

1.16 retired to `retained` when 1.17 was cut. The family-root navigation assertion
this module used to carry was dropped there, because it re-pinned which sibling
currently holds `default` and so went red on that cut rather than on a regression
of its own; `test_catalog_roles.py` owns that invariant catalog-derived.
"""

from __future__ import annotations

import ast
import hashlib
import re
import stat
import tomllib
from pathlib import Path
from typing import cast

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

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
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V115 = _FAMILY / "versions/1.15"
_V116 = _FAMILY / "versions/1.16"
_PROJECTION_116 = _ROOT / "src/project_standards/payloads/python-tooling/1.16"

_BUILD_SYSTEM_SCOPE = "table:/build-system"
_WORKFLOW = ".github/workflows/check.yml"
_IGNORE_SCOPE = "key:/tool/ruff/lint/ignore"

# The uv release the issue reporter ran (0.12.3) and the uv that this repository's
# own toolchain pins; both must sit inside the rendered bound, or the adoption the
# issue describes warns again.
_SUPPORTED_UV = ("0.11.0", "0.11.6", "0.12.3", "0.99.0")

_V115_AGGREGATE = "sha256:61631defaf36143fa4862fafae82f404a41187cb72b649aae61fc8f6fb8bc985"

# The predecessor is advertised and therefore immutable: a byte change anywhere in
# it is a released-payload mutation, not a diff to review. Pinning the whole tree
# rather than only the file 1.16 happened to touch is what makes that detectable.
_V115_FILES = {
    "README.md": "baadf0b61d6b35229671833b6d62e2253cc3d5d7cc403329b58f8ade76e7cc1c",
    "adopt.md": "ac4ea62a4eb9bdbcc08cc88c66a709cded970769faf434fe88044ba9f26177a5",
    "agent-summary.md": "bbf88fb56ea1fd8bc7df85c3ffbe4362be2bc2755182a09dd097427b21d8db71",
    "build-backend.md": "3e83b6ed2763d369537d59e9f0baad47ddeb6c9cbe77537478c9b1069c937083",
    "config.schema.json": ("aea8a435c489fa0c1297032c2cbbd481d236002a9a6a94e5e14d06aeaa78470e"),
    "payload.toml": "036b870a7e8edebfd19a100e196e7198441e5004a0a2ce792728a0324e9e15a8",
    "providers/python_tooling.py": (
        "d339a8ad6dd03d3a76d7d746e191035535e9c7e74beeadf19a8e753f4ea13657"
    ),
    "resources/check.py": "04930fcc2fc4f9f82af40591a1ea68e8a791c9bc0c8732749439b34afe04091a",
    "resources/check.yml": "2fad10f0328e2c475fce19e4a4db59f8f8e94ab075bb327890e27256284bafcb",
    "resources/python-version": (
        "a876e0b10411037a012498b9fe18d9bc1df32ed8b722a13564dc944ddcfd9135"
    ),
    "schemas/config-transform-input.schema.json": (
        "aff1d30766fb55da3c8e5d173b4ba4e1e4889cca0248bc68eaad105b75cf626f"
    ),
    "schemas/config-transform-report.schema.json": (
        "eb4b6f04d12540b6cac44edc0ae762c98b660467e4696550e096f99c48f3b5f8"
    ),
    "schemas/content.schema.json": (
        "760d819048c1f2a153e72227c940f36eed96deb5e2336e802f34caa37ccf14b3"
    ),
    "schemas/findings.schema.json": (
        "c838f02865d72e8d2aa4d6640e1fb50d03187122571752d1c75970f93ffb1066"
    ),
    "schemas/migration-report.schema.json": (
        "66df59b9d9c940524804529905e0332fbf074d335ad523215098bd3dc2c25d45"
    ),
    "schemas/provider-input.schema.json": (
        "9ec7beee0ce6bd3364c8f7743b6c31bb8581201d5159413494fd24d1eb9242fa"
    ),
}

# Configurations spelled in 1.15's own option vocabulary. Each moves a knob some
# rendered unit actually reads, so resolving the same source text under both
# payloads compares real renders rather than a repeated default.
_PREDECESSOR_SHAPES: tuple[JsonObject, ...] = (
    {},
    {"ci": {"enabled": True, "performance": True}},
    {"type_checker": {"name": "pyright", "mode": "basic"}},
    {"source_layout": "flat"},
    {"coverage": {"parallel": True, "patch": ["subprocess"], "omit": ["src/generated/*"]}},
    {"ruff": {"line_length": 79, "enforce_line_length": True, "extend_select": ["ANN"]}},
    {"runner_labels": ["self-hosted", "linux", "x64"]},
    {"vscode": {"task_prefix": "python: "}},
)


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, configured: JsonObject | None = None) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(configured or {})


def _render(root: Path, planned: JsonObject, config: JsonObject) -> bytes:
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
            snapshots={"planned_contribution": planned},
        )
    )
    assert result.effect is ProviderEffect.CONTENT
    assert result.content is not None
    return result.content


def _render_build_system(root: Path, config: JsonObject) -> bytes:
    return _render(
        root,
        {
            "id": "build-system",
            "target": "pyproject.toml",
            "adapter": AdapterKind.TOML.value,
            "scope": _BUILD_SYSTEM_SCOPE,
        },
        config,
    )


def _render_workflow(root: Path, config: JsonObject) -> bytes:
    return _render(
        root,
        {
            "id": "check-workflow",
            "target": _WORKFLOW,
            "adapter": AdapterKind.WHOLE_FILE.value,
            "scope": "$file",
        },
        config,
    )


def _render_lint_ignore(root: Path, config: JsonObject) -> bytes:
    return _render(
        root,
        {
            "id": "ruff-lint-ignore",
            "target": "pyproject.toml",
            "adapter": AdapterKind.TOML.value,
            "scope": _IGNORE_SCOPE,
        },
        config,
    )


def _uv_build_requirement(root: Path, config: JsonObject) -> str:
    table = tomllib.loads(_render_build_system(root, config).decode("utf-8"))
    requires = cast("list[str]", cast("dict[str, object]", table["build-system"])["requires"])
    assert len(requires) == 1, requires
    return requires[0]


def _provider_default_config(root: Path) -> JsonObject:
    """Return the provider's `_DEFAULT_CONFIG` literal without importing the module.

    Executing a payload provider from the source checkout byte-compiles a
    `__pycache__` directory inside it, which the projection and activation suites
    then compare against the wheel and fail on. Reading the literal with `ast`
    keeps this assertion free of that side effect.
    """
    module = ast.parse((root / "providers/python_tooling.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.AnnAssign | ast.Assign):
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            names = {target.id for target in targets if isinstance(target, ast.Name)}
            if "_DEFAULT_CONFIG" in names and node.value is not None:
                return cast("JsonObject", ast.literal_eval(node.value))
    raise AssertionError("the provider declares no _DEFAULT_CONFIG mapping")


@pytest.mark.parametrize("uv_version", _SUPPORTED_UV)
def test_python_tooling_1_16__uv_build_bound__contains_every_supported_uv(uv_version: str) -> None:
    """The defect itself: uv warns unless its own version satisfies `requires`."""
    requirement = Requirement(_uv_build_requirement(_V116, _options(_V116)))

    assert requirement.name == "uv_build"
    assert Version(uv_version) in requirement.specifier


def test_python_tooling_1_16__uv_build_bound__stays_bounded_below_the_1_0_series() -> None:
    """uv warns about a missing upper bound too, so widening cannot mean dropping it.

    1.0 is the boundary because uv_build is pre-1.0: every 0.x release is inside the
    same unstable series this bound accepts, while a 1.0 backend is a deliberate
    re-evaluation that belongs to a future payload rather than to this window.
    """
    rendered = _uv_build_requirement(_V116, _options(_V116))
    specifier = Requirement(rendered).specifier

    assert Version("1.0") not in specifier
    assert Version("0.10.0") not in specifier
    assert "<" in rendered


def test_python_tooling_1_16__predecessor_bound__is_the_reported_defect() -> None:
    """Guard the fix against a silent revert: 1.15's window excludes the reported uv."""
    requirement = _uv_build_requirement(_V115, _options(_V115))

    assert requirement == "uv_build>=0.11,<0.12"
    assert Version("0.12.3") not in Requirement(requirement).specifier


def test_python_tooling_1_16__other_backends__render_the_predecessor_bytes() -> None:
    """Only the `uv_build` requirement moves; the other backends are untouched."""
    for backend in ("hatchling", "setuptools", "none"):
        shape: JsonObject = {"build_backend": backend}
        assert _render_build_system(_V116, _options(_V116, shape)) == _render_build_system(
            _V115, _options(_V115, shape)
        )


def test_python_tooling_1_16__other_units__render_byte_identical_outputs() -> None:
    """A copied payload must change exactly one render and nothing else."""
    for shape in _PREDECESSOR_SHAPES:
        predecessor_config = _options(_V115, shape)
        successor_config = _options(_V116, shape)

        assert _render_workflow(_V116, successor_config) == _render_workflow(
            _V115, predecessor_config
        )
        assert _render_lint_ignore(_V116, successor_config) == _render_lint_ignore(
            _V115, predecessor_config
        )


def test_python_tooling_1_16__option_surface__is_unchanged() -> None:
    """This cut fixes a rendered constant, so the consumer's option vocabulary is frozen."""
    assert _options(_V116) == _options(_V115)
    # The provider decides whether to serve the immutable static resource by
    # comparing the resolved config against its own default mapping, so the two
    # must agree key for key; a schema default missing there silently routes every
    # default adoption down the rendered branch instead.
    assert _provider_default_config(_V116) == _options(_V116)


def test_python_tooling_1_16__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        path.relative_to(_V115).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in payload_tree(_V115)
        if path.is_file()
    }
    assert actual == {path: (0o644, digest) for path, digest in _V115_FILES.items()}
    assert (
        validate_payload_integrity(
            _V115, load_payload_manifest(_V115 / "payload.toml")
        ).aggregate_digest.value
        == _V115_AGGREGATE
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "python-tooling"
    }
    # Withdrawing an advertised package is a catalog-major transition (ADR 0024),
    # so every predecessor stays advertised and only its role moves to `retained`.
    # 1.16 itself retired to `retained` when 1.17 was activated (issue #201); a
    # released role never moves backwards, which is the whole of what this module
    # can still prove. Which version currently holds `default`, and the full
    # membership of this family's catalog rows, both move on every later cut and
    # are asserted catalog-derived in test_catalog_roles.py instead.
    assert roles["1.15"] == "retained"
    assert roles["1.16"] == "retained"


def test_python_tooling_1_16__versioned_guidance__states_the_uv_prerequisite() -> None:
    """Acceptance criterion two: the exact-release guide names the uv range it needs.

    The lower bound is a real prerequisite — uv 0.10 emits the same warning against
    this payload's requirement — so an adopter has to be able to read it without
    running a reconciliation first.
    """
    readme = (_V116 / "README.md").read_text(encoding="utf-8")
    adopt = (_V116 / "adopt.md").read_text(encoding="utf-8")
    guidance = (_V116 / "build-backend.md").read_text(encoding="utf-8")

    for text in (readme, adopt, guidance):
        assert "uv_build>=0.11,<1.0" in text
    assert "uv 0.11" in adopt


def test_python_tooling_1_16__machine_readable_payload__carries_no_1_15_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.15.

    Every prior cut in this repository inherited at least one stale embedded
    version string — a schema const, a migration id, a transform endpoint — that no
    per-cut assertion caught.

    The sweep covers the declarative files, where every `1.15` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown and the provider's own prose
    are excluded for the same reason and are pinned by the narrower assertion below,
    which names the one machine-readable version literal the provider emits.
    """

    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        path.relative_to(_V116).as_posix()
        for path in payload_tree(_V116)
        if path.is_file()
        and path.suffix in {".json", ".toml", ".yml"}
        and re.search(
            r"(?<![\d.])1[.-]15(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()

    provider = (_V116 / "providers/python_tooling.py").read_text(encoding="utf-8")
    assert '"version": "1.16"' in provider
    assert '"version": "1.15"' not in provider


def test_python_tooling_1_16__migration_edges__retarget_without_a_new_edge() -> None:
    """1.12 through 1.15 owe no edge: the changed unit keeps its identity and policy."""
    manifest = load_payload_manifest(_V116 / "payload.toml")

    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        *(f"package:1.{minor}" for minor in range(1, 12)),
        "legacy:v4-python-tooling",
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.16"


def test_python_tooling_1_16__projection_and_index__are_complete() -> None:
    source_files = {
        path.relative_to(_V116).as_posix() for path in payload_tree(_V116) if path.is_file()
    }
    projected_files = {
        path.relative_to(_PROJECTION_116).as_posix()
        for path in payload_tree(_PROJECTION_116)
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_116 / relative).resolve() == (_V116 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in payload_tree(_PROJECTION_116) if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.16"]["payload"] == "versions/1.16/payload.toml"
    assert versions["1.16"]["digest"] == _payload(_V116).integrity.aggregate_digest.value
    assert "python-tooling@1.16" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
