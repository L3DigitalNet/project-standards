"""Pin the Python Tooling 1.17 `setup-uv` action reference and its cache semantics.

Issue #201: the rendered CI workflow pinned `astral-sh/setup-uv` at the v9.0.0
commit. setup-uv publishes no moving major or minor tag from v8.0.0 on, so the
pin is a full SHA and advancing it is a payload cut rather than a tag that
follows on its own. 1.17 advances it to v10.0.1 and changes nothing else.

v10's one breaking change is that `enable-cache: auto` now *disables* the cache
for `release`, tag pushes, `pull_request_target`, and `workflow_run`. That flip
is inert here for two independent reasons, and both are asserted below rather
than asserted in prose: this workflow names `enable-cache: true` explicitly
instead of inheriting `auto`, and it triggers only on `pull_request`, `push`,
and (with CI disabled) `workflow_dispatch`, none of which the flip touches. If
a future cut moved either fact, the pin bump stops being safe, so both are
contract.

Everything else in the payload is a copy of 1.16, so the second contract here is
that exactly one rendered line and no option moved.

1.17 retired to `retained` when 1.18 was cut. The family-root navigation assertion
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

import yaml

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
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V116 = _FAMILY / "versions/1.16"
_V117 = _FAMILY / "versions/1.17"
_PROJECTION_117 = _ROOT / "src/project_standards/payloads/python-tooling/1.17"

_BUILD_SYSTEM_SCOPE = "table:/build-system"
_WORKFLOW = ".github/workflows/check.yml"
_IGNORE_SCOPE = "key:/tool/ruff/lint/ignore"

# The two `uses:` values in full, comment included: the version comment is the
# only human-readable part of a SHA pin, so a SHA advanced without it (or the
# reverse) is exactly the mistake worth catching.
_V9_PIN = "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0"
_V10_PIN = "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d # v10.0.1"

# The events v10 removed from `enable-cache: auto`. This workflow must trigger on
# none of them for the "inert here" argument to hold independently of the
# explicit `true` below.
#
# v10 actually disables the cache for four classes: these three plus tag
# pushes. Tag pushes are deliberately not a member here: this set is compared
# against `_trigger_events()`, which returns the workflow's literal `on:`
# trigger keys (e.g. "push", "pull_request"), and "tag push" is not such a
# key — it is the `push` trigger filtered by a `tags:` pattern, indistinguishable
# from any other `push` trigger at this level. Adding a string that can never
# match a real trigger key would make the isdisjoint check below silently stop
# covering that fourth class. The tag-push class is instead pinned separately, by
# `_push_branch_filter()` and its assertion in the cache test.
_AUTO_DISABLED_EVENTS = frozenset({"pull_request_target", "workflow_run", "release"})

_V116_AGGREGATE = "sha256:60d3a68c9973942b7a92f7affcd3fbac553b3c79c31bcd63b723e1186bd3c734"

# The predecessor is advertised and therefore immutable: a byte change anywhere in
# it is a released-payload mutation, not a diff to review. Pinning the whole tree
# rather than only the file 1.17 happened to touch is what makes that detectable.
_V116_FILES = {
    "README.md": "ffef0d2db9b079a4ee131d15e17e52fc3d4777cf16cd5515046fbddf50fdda74",
    "adopt.md": "f7cc17600c692709df644972a2818d7cbc16d5c77e6d23dc40b7c37d0d671e06",
    "agent-summary.md": "b3e04fad135bc20f6517efc23a908fd9af508d2ed7e48f6307e0fb88074a842a",
    "build-backend.md": "d0d2120f49df6ad6475d807a087933ad0d66b2b796c31ddb690e36874d53d089",
    "config.schema.json": ("aea8a435c489fa0c1297032c2cbbd481d236002a9a6a94e5e14d06aeaa78470e"),
    "payload.toml": "e9062be588b1093dfed5d8d506689e144bfee65e38a9250bb0b8b27364451975",
    "providers/python_tooling.py": (
        "2c140ecadc8d1823117dec1e76559dbb9deecb0817f5493f22b14d45f520ef0e"
    ),
    "resources/check.py": "04930fcc2fc4f9f82af40591a1ea68e8a791c9bc0c8732749439b34afe04091a",
    "resources/check.yml": "2fad10f0328e2c475fce19e4a4db59f8f8e94ab075bb327890e27256284bafcb",
    "resources/python-version": (
        "a876e0b10411037a012498b9fe18d9bc1df32ed8b722a13564dc944ddcfd9135"
    ),
    "schemas/config-transform-input.schema.json": (
        "00340b7754e409d242e97159a25d45f845041b5ffc93559bf3849cdcf26cd7c8"
    ),
    "schemas/config-transform-report.schema.json": (
        "6bbc035ec6b1185ed1cb42a7393fe3005d8181edf8c45b59866436830785f1e2"
    ),
    "schemas/content.schema.json": (
        "760d819048c1f2a153e72227c940f36eed96deb5e2336e802f34caa37ccf14b3"
    ),
    "schemas/findings.schema.json": (
        "c838f02865d72e8d2aa4d6640e1fb50d03187122571752d1c75970f93ffb1066"
    ),
    "schemas/migration-report.schema.json": (
        "a95bc7aef54eca242c1b8285b23e49ec6accbc21aeee71a23fe153974e5eaa24"
    ),
    "schemas/provider-input.schema.json": (
        "2118cb634ef3b6bd0b68e4cb7e29e27a921387e0058e38a210bd5ca3b116cfa2"
    ),
}

# Configurations spelled in 1.16's own option vocabulary. Each moves a knob some
# rendered unit actually reads, so resolving the same source text under both
# payloads compares real renders rather than a repeated default. `ci.enabled =
# false` is here for this cut specifically: it is the one shape that renders a
# different trigger block, and the trigger block is load-bearing for the v10
# cache argument.
_PREDECESSOR_SHAPES: tuple[JsonObject, ...] = (
    {},
    {"ci": {"enabled": False}},
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


def _workflow_document(root: Path, config: JsonObject) -> dict[object, object]:
    return cast(
        "dict[object, object]", yaml.safe_load(_render_workflow(root, config).decode("utf-8"))
    )


def _trigger_events(document: dict[object, object]) -> set[str]:
    """Return the workflow's top-level trigger names.

    YAML 1.1 resolves the bare key `on` to the boolean `True`, so the trigger
    block cannot be looked up under the string a reader of the file sees.
    """
    triggers = document[True] if True in document else document["on"]
    if isinstance(triggers, str):
        return {triggers}
    return set(cast("dict[str, object]", triggers))


def _push_branch_filter(document: dict[object, object]) -> object:
    """Return the `push` trigger's `branches` value, or None when it carries none.

    Callers must confirm `push` is among `_trigger_events()` first. The
    None return deliberately conflates "bare `push:`" with "`push:` filtered by
    something other than branches" — both mean the tag-push class is no longer
    excluded, which is the only distinction the assertion needs.
    """
    triggers = document[True] if True in document else document["on"]
    push = cast("dict[str, object]", triggers)["push"]
    if not isinstance(push, dict):
        return None
    return cast("dict[str, object]", push).get("branches")


def _setup_uv_step(document: dict[object, object]) -> dict[str, object]:
    jobs = cast("dict[str, dict[str, object]]", document["jobs"])
    steps = cast("list[dict[str, object]]", jobs["check"]["steps"])
    return next(
        step
        for step in steps
        if isinstance(step.get("uses"), str)
        and cast("str", step["uses"]).startswith("astral-sh/setup-uv@")
    )


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


def test_python_tooling_1_17__setup_uv_pin__advances_to_v10_everywhere_it_is_written() -> None:
    """The defect itself, across both copies of the same line.

    The pin is written twice — once in the static resource the provider serves
    for a default adoption, once in the provider's rendered line list — and only
    one of the two is exercised by any given consumer. Asserting both is what
    keeps a half-applied bump from shipping.
    """
    resource = (_V117 / "resources/check.yml").read_text(encoding="utf-8")
    assert f"uses: {_V10_PIN}" in resource
    assert _V9_PIN not in resource

    for shape in _PREDECESSOR_SHAPES:
        rendered = _render_workflow(_V117, _options(_V117, shape)).decode("utf-8")
        assert f"uses: {_V10_PIN}" in rendered, shape
        assert _V9_PIN not in rendered, shape


def test_python_tooling_1_17__predecessor_pin__is_the_superseded_reference() -> None:
    """Guard the fix against a silent revert: 1.16 must still show the v9 pin."""
    resource = (_V116 / "resources/check.yml").read_text(encoding="utf-8")

    assert f"uses: {_V9_PIN}" in resource
    assert _V10_PIN not in resource


def test_python_tooling_1_17__cache_configuration__is_immune_to_the_v10_auto_flip() -> None:
    """The substantive reason the bump is safe, asserted rather than claimed.

    v10 redefines `enable-cache: auto` to disable the cache for `release`, tag
    pushes, `pull_request_target`, and `workflow_run`. This workflow is immune
    twice over: it never selects `auto`, and it never triggers on any of those
    four events. Either fact alone makes the flip a non-event, so both are
    pinned — a future cut that gives up one still has to notice it is now relying
    entirely on the other.

    Three of the four classes are absent `on:` keys, so `_AUTO_DISABLED_EVENTS`
    covers them. Tag pushes are not: this workflow does trigger on `push`, and
    only the `branches: ["main"]` qualifier keeps a tag from matching. That
    qualifier therefore carries a load it does not look like it carries, and is
    asserted here so deleting it fails this test rather than silently widening
    the trigger.
    """
    for shape in _PREDECESSOR_SHAPES:
        document = _workflow_document(_V117, _options(_V117, shape))
        cache = _setup_uv_step(document)["with"]

        enable_cache = cast("dict[str, object]", cache)["enable-cache"]
        assert enable_cache != "auto", shape
        assert enable_cache is True, shape

        triggers = _trigger_events(document)
        assert triggers.isdisjoint(_AUTO_DISABLED_EVENTS), shape
        if "push" in triggers:
            assert _push_branch_filter(document) == ["main"], shape


def test_python_tooling_1_17__workflow_render__differs_only_in_the_pin_line() -> None:
    """The whole-file workflow is the one unit allowed to move, by exactly one line."""
    for shape in _PREDECESSOR_SHAPES:
        predecessor = _render_workflow(_V116, _options(_V116, shape)).decode("utf-8").splitlines()
        successor = _render_workflow(_V117, _options(_V117, shape)).decode("utf-8").splitlines()

        assert len(successor) == len(predecessor), shape
        differing = [
            (before, after)
            for before, after in zip(predecessor, successor, strict=True)
            if before != after
        ]
        assert differing == [(f"      - uses: {_V9_PIN}", f"      - uses: {_V10_PIN}")], shape


def test_python_tooling_1_17__other_units__render_byte_identical_outputs() -> None:
    """A copied payload must change exactly one render and nothing else."""
    for shape in _PREDECESSOR_SHAPES:
        predecessor_config = _options(_V116, shape)
        successor_config = _options(_V117, shape)

        assert _render_build_system(_V117, successor_config) == _render_build_system(
            _V116, predecessor_config
        )
        assert _render_lint_ignore(_V117, successor_config) == _render_lint_ignore(
            _V116, predecessor_config
        )

    for backend in ("hatchling", "setuptools", "none"):
        shape: JsonObject = {"build_backend": backend}
        assert _render_build_system(_V117, _options(_V117, shape)) == _render_build_system(
            _V116, _options(_V116, shape)
        )


def test_python_tooling_1_17__option_surface__is_unchanged() -> None:
    """This cut fixes a rendered constant, so the consumer's option vocabulary is frozen."""
    assert _options(_V117) == _options(_V116)
    # The provider decides whether to serve the immutable static resource by
    # comparing the resolved config against its own default mapping, so the two
    # must agree key for key; a schema default missing there silently routes every
    # default adoption down the rendered branch instead.
    assert _provider_default_config(_V117) == _options(_V117)


def test_python_tooling_1_17__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        path.relative_to(_V116).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in payload_tree(_V116)
        if path.is_file()
    }
    assert actual == {path: (0o644, digest) for path, digest in _V116_FILES.items()}
    assert (
        validate_payload_integrity(
            _V116, load_payload_manifest(_V116 / "payload.toml")
        ).aggregate_digest.value
        == _V116_AGGREGATE
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "python-tooling"
    }
    # Withdrawing an advertised package is a catalog-major transition (ADR 0024),
    # so every predecessor stays advertised and only its role moves to `retained`.
    # 1.17 itself retired to `retained` when 1.18 was activated (issue #204); a
    # released role never moves backwards, which is the whole of what this module
    # can still prove. Which version currently holds `default`, and the full
    # membership of this family's catalog rows, both move on every later cut and
    # are asserted catalog-derived in test_catalog_roles.py instead.
    assert roles["1.16"] == "retained"
    assert roles["1.17"] == "retained"


def test_python_tooling_1_17__versioned_guidance__explains_the_pin_and_its_safety() -> None:
    """An adopter reading only the exact-release README must learn why v10 is safe.

    The pin is invisible to option resolution, so the README is the only place a
    consumer can find out that the action moved a major and that the cache
    semantics it inherited did not.
    """
    readme = (_V117 / "README.md").read_text(encoding="utf-8")

    assert "v10.0.1" in readme
    assert "enable-cache: auto" in readme
    assert "issue #201" in readme


def test_python_tooling_1_17__machine_readable_payload__carries_no_1_16_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.16.

    Every prior cut in this repository inherited at least one stale embedded
    version string — a schema const, a migration id, a transform endpoint — that no
    per-cut assertion caught.

    The sweep covers the declarative files, where every `1.16` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown and the provider's own prose
    are excluded for the same reason and are pinned by the narrower assertion below,
    which names the one machine-readable version literal the provider emits.
    """

    stale = {
        path.relative_to(_V117).as_posix()
        for path in payload_tree(_V117)
        if path.is_file()
        and path.suffix in {".json", ".toml", ".yml"}
        and re.search(
            r"(?<![\d.])1[.-]16(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()

    provider = (_V117 / "providers/python_tooling.py").read_text(encoding="utf-8")
    assert '"version": "1.17"' in provider
    assert '"version": "1.16"' not in provider


def test_python_tooling_1_17__migration_edges__retarget_without_a_new_edge() -> None:
    """1.12 through 1.16 owe no edge: the changed unit keeps its identity and policy."""
    manifest = load_payload_manifest(_V117 / "payload.toml")

    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        *(f"package:1.{minor}" for minor in range(1, 12)),
        "legacy:v4-python-tooling",
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.17"


def test_python_tooling_1_17__projection_and_index__are_complete() -> None:
    source_files = {
        path.relative_to(_V117).as_posix() for path in payload_tree(_V117) if path.is_file()
    }
    projected_files = {
        path.relative_to(_PROJECTION_117).as_posix()
        for path in payload_tree(_PROJECTION_117)
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_117 / relative).resolve() == (_V117 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in payload_tree(_PROJECTION_117) if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.17"]["payload"] == "versions/1.17/payload.toml"
    assert versions["1.17"]["digest"] == _payload(_V117).integrity.aggregate_digest.value
    assert "python-tooling@1.17" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
