"""Pin the Python Tooling 1.15 runner-selection and line-length contracts.

Two consumer defects motivate this cut, and both share one acceptance property:
an existing consumer who configures neither option must reconcile to bytes that
are identical, not merely equivalent, to 1.14's. Reconciliation compares bytes,
so any drift would rewrite managed files on upgrade for features nobody selected
and would report a hand-edited file as CP-MODIFIED-MANAGED afterwards.

- Issue #180: the generated `check.yml` hardcoded `runs-on: ubuntu-latest`, so an
  organization that blocks GitHub-hosted runners for private repositories could
  not use the managed workflow at all — the job died with no runner assigned. The
  only conforming workaround was `workflow_ownership = "consumer-owned"`, which
  gives up every future managed update.
- Issue #181: `[tool.ruff.lint] ignore = ["E501"]` was unconditional, and Ruff
  resolves `ignore` after `extend-select`, so no consumer configuration could
  re-enable the rule. The declared `line-length` was therefore unenforceable on
  comment, docstring, and string prose, which `ruff format` never reflows.

1.15 is a released, advertised payload: its bytes are immutable and its catalog
role only ever moves forward to `retained`. The activation assertions below
therefore track the family's current default rather than claiming 1.15 is still
the selection.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import stat
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract import PackageContractError
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
from project_standards.package_contract.repository import build_package_repository
from tests.control_plane.planner_helpers import resolution_request
from tests.package_contract.helpers import assert_schema_payload_references

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V114 = _FAMILY / "versions/1.14"
_V115 = _FAMILY / "versions/1.15"
_PROJECTION_115 = _ROOT / "src/project_standards/payloads/python-tooling/1.15"

_WORKFLOW = ".github/workflows/check.yml"
_IGNORE_SCOPE = "key:/tool/ruff/lint/ignore"
_LABELS: list[JsonValue] = ["self-hosted", "linux", "x64", "l3digital-private"]

_V114_AGGREGATE = "sha256:50f96c72d73253d7bd2016a374a3e46e31b6da51bba8a2dd79a56041fe2937db"

# The predecessor is advertised and therefore immutable: a byte change anywhere in
# it is a released-payload mutation, not a diff to review. Pinning the whole tree
# rather than only the files 1.15 happened to touch is what makes that detectable.
_V114_FILES = {
    "README.md": "c35a75fcdc913235252a40192a7db9fe1463baa7129ef685d2da8533f91bc879",
    "adopt.md": "85ca4e328714e54382337e18d417ac81b50b900d1f4944e2b8eb7b710a9fabd5",
    "agent-summary.md": "54d425f3e20be24f7eb56c47b97f080814a75f65bbfd4d34ee56eb33e4275112",
    "build-backend.md": "3e83b6ed2763d369537d59e9f0baad47ddeb6c9cbe77537478c9b1069c937083",
    "config.schema.json": ("a19b9da71a9bf4d5c8ae2d3a6b71b239d5a4b4fc3ba8c3c045e982adec518ba5"),
    "payload.toml": "7ccc3547253bd0fad5dd00d67249f6fa4a800dc3dbea1660be4e344518ec69ba",
    "providers/python_tooling.py": (
        "f8e73720a90ea3567291dfdba28e85ba9a59180ddcd48a17c51d320f46962942"
    ),
    "resources/check.py": ("04930fcc2fc4f9f82af40591a1ea68e8a791c9bc0c8732749439b34afe04091a"),
    "resources/check.yml": ("2fad10f0328e2c475fce19e4a4db59f8f8e94ab075bb327890e27256284bafcb"),
    "resources/python-version": (
        "a876e0b10411037a012498b9fe18d9bc1df32ed8b722a13564dc944ddcfd9135"
    ),
    "schemas/config-transform-input.schema.json": (
        "bf6f61da95017c30ea8b26b2d67dd399753c0598b4f70da688417bf33e0bde9d"
    ),
    "schemas/config-transform-report.schema.json": (
        "83b524a68a4eb074959ca07e02e3d687bbdfeaa1b200f760231aa21fbf0ba508"
    ),
    "schemas/content.schema.json": (
        "760d819048c1f2a153e72227c940f36eed96deb5e2336e802f34caa37ccf14b3"
    ),
    "schemas/findings.schema.json": (
        "c838f02865d72e8d2aa4d6640e1fb50d03187122571752d1c75970f93ffb1066"
    ),
    "schemas/migration-report.schema.json": (
        "07799eb56bc8d55463e1227cf9e0c8592ccd57a7e40b38c522307d6bee6250cb"
    ),
    "schemas/provider-input.schema.json": (
        "b0d5971dbf3d87b06d2f698d946a7a0da0b334f46cd7c32ddf4cbecafcf200a3"
    ),
}

# Configurations spelled in 1.14's own option vocabulary — no key below exists in
# 1.15 only. Each one moves a knob the workflow render or the Ruff lint units
# actually read, so resolving the same source text under both payloads is a real
# comparison rather than a repeated default.
_PREDECESSOR_SHAPES: tuple[JsonObject, ...] = (
    {},
    {"ci": {"enabled": False, "performance": False}},
    {"ci": {"enabled": True, "performance": True}},
    {"type_checker": {"name": "pyright", "mode": "basic"}},
    {"source_layout": "flat"},
    {
        "source_layout": "explicit",
        "additional_source_roots": ["packages/core", {"path": "scripts", "coverage": False}],
        "pytest": {"test_paths": ["qa/unit", "qa/integration"]},
    },
    {"coverage": {"parallel": True, "patch": ["subprocess"], "omit": ["src/generated/*"]}},
    {"pip_audit": {"ignore_vulnerabilities": ["GHSA-aaaa-bbbb-cccc"]}},
    {"ruff": {"line_length": 79, "extend_select": ["ANN"], "extend_ignore": ["D"]}},
    {"ruff": {"extend_per_file_ignores": {"scripts/*.py": ["T201"]}}},
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


def _write_consumer(repo: Path) -> None:
    repo.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "example-package"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n',
        encoding="utf-8",
    )


def _request(
    repo: Path,
    payload: InstalledPayload,
    config: JsonObject,
) -> PlannerRequest:
    return PlannerRequest(
        repo,
        resolution_request((payload,), configs={"python-tooling": config}),
        (payload,),
    )


def _apply(repo: Path, payload: InstalledPayload, config: JsonObject) -> ReconciliationPlan:
    request = _request(repo, payload, config)
    control = repo / ".standards"
    control.mkdir(exist_ok=True)
    (control / "lock.toml").write_bytes(render_lock(request.resolution.previous_lock))
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    return plan


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


def test_python_tooling_1_15__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        path.relative_to(_V114).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in _V114.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert actual == {path: (0o644, digest) for path, digest in _V114_FILES.items()}
    assert (
        validate_payload_integrity(
            _V114, load_payload_manifest(_V114 / "payload.toml")
        ).aggregate_digest.value
        == _V114_AGGREGATE
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "python-tooling"
    }
    # Withdrawing an advertised package is a catalog-major transition (ADR 0024),
    # so every predecessor stays advertised and only its role moves to `retained`.
    assert roles == {
        # 1.15 retired to `retained` when the 1.16 successor was activated (issue
        # #182); a released role never moves backwards, and the predecessor rows
        # are what this test actually guards.
        **{f"1.{minor}": "retained" for minor in range(1, 16)},
        "1.16": "default",
    }


def test_python_tooling_1_15__option_surface__adds_only_the_two_opt_in_options() -> None:
    predecessor_defaults = _options(_V114)
    successor_defaults = _options(_V115)
    ruff = cast("JsonObject", predecessor_defaults["ruff"])

    assert successor_defaults == {
        **predecessor_defaults,
        "runner_labels": [],
        "ruff": {**ruff, "enforce_line_length": False},
    }
    # The provider decides whether to serve the immutable static resource by
    # comparing the resolved config against its own default mapping, so the two
    # must agree key for key; a schema default missing there silently routes every
    # default adoption down the rendered branch instead.
    assert _provider_default_config(_V115) == successor_defaults


def test_python_tooling_1_15__predecessor_configs__render_byte_identical_outputs() -> None:
    """The acceptance property both issues share, over 1.14's own option vocabulary."""
    for shape in _PREDECESSOR_SHAPES:
        predecessor_config = _options(_V114, shape)
        successor_config = _options(_V115, shape)

        assert _render_workflow(_V115, successor_config) == _render_workflow(
            _V114, predecessor_config
        )
        assert _render_lint_ignore(_V115, successor_config) == _render_lint_ignore(
            _V114, predecessor_config
        )

        # Writing the defaults out explicitly must mean exactly what omitting them
        # means; otherwise a consumer who documents the default in their config
        # would silently take a different render than one who leaves it out.
        ruff = cast("JsonObject", shape.get("ruff", {}))
        explicit = _options(
            _V115,
            {
                **shape,
                "runner_labels": [],
                "ruff": {**ruff, "enforce_line_length": False},
            },
        )
        assert _render_workflow(_V115, explicit) == _render_workflow(_V114, predecessor_config)
        assert _render_lint_ignore(_V115, explicit) == _render_lint_ignore(
            _V114, predecessor_config
        )


def test_python_tooling_1_15__default_workflow__is_the_immutable_static_resource() -> None:
    rendered = _render_workflow(_V115, _options(_V115))

    assert rendered == (_V115 / "resources/check.yml").read_bytes()
    assert b"runs-on: ubuntu-latest" in rendered


def test_python_tooling_1_15__default_adoption__is_a_fixed_point(tmp_path: Path) -> None:
    predecessor_repo = tmp_path / "predecessor"
    successor_repo = tmp_path / "successor"
    _write_consumer(predecessor_repo)
    _write_consumer(successor_repo)
    _apply(predecessor_repo, _payload(_V114), {})
    first = _apply(successor_repo, _payload(_V115), {})

    assert (successor_repo / _WORKFLOW).read_bytes() == (predecessor_repo / _WORKFLOW).read_bytes()
    assert (successor_repo / "pyproject.toml").read_bytes() == (
        predecessor_repo / "pyproject.toml"
    ).read_bytes()

    successor = _payload(_V115)
    request = PlannerRequest(
        successor_repo,
        resolution_request(
            (successor,),
            configs={"python-tooling": {}},
            previous_lock=first.next_lock,
        ),
        (successor,),
    )
    second = plan_reconciliation(request)
    assert second.applicable, second.findings
    repeat = apply_reconciliation(ApplyRequest(request, second))
    assert repeat.success
    assert repeat.applied_action_ids == ()


def test_python_tooling_1_15__configured_labels__template_the_job_runs_on() -> None:
    rendered = _render_workflow(_V115, _options(_V115, {"runner_labels": _LABELS})).decode()
    default = _render_workflow(_V115, _options(_V115)).decode()

    # A block sequence, deliberately not the flow sequence the sibling packages'
    # JSON-string input decodes to: Prettier owns `*.yml` wherever Markdown Tooling
    # is also adopted, and it explodes a flow sequence across lines once the line
    # passes `printWidth`. That would make the managed bytes a fixed point only
    # until a consumer declared one label too many (issue #115's defect).
    assert "\n    runs-on:\n      - self-hosted\n      - linux\n      - x64\n" in rendered
    assert "ubuntu-latest" not in rendered
    assert "runs-on: [" not in rendered

    # Nothing but the runner selection may move: the option must not be able to
    # reorder, drop, or rename a gate step.
    def without_runner(text: str) -> list[str]:
        return [
            line
            for line in text.splitlines()
            if not line.startswith("    runs-on") and line.strip().lstrip("- ") not in _LABELS
        ]

    assert without_runner(rendered) == without_runner(default)


def test_python_tooling_1_15__labels__reach_the_applied_workflow(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_consumer(repo)

    _apply(repo, _payload(_V115), {"runner_labels": _LABELS})

    workflow = (repo / _WORKFLOW).read_text(encoding="utf-8")
    assert "    runs-on:\n      - self-hosted\n" in workflow
    # Regression pin for the defect that motivated the option: this workflow is
    # self-contained, so both of its triggers must reach the selected pool. A
    # caller-only route would leave push and pull_request on the hosted runner.
    assert "pull_request:" in workflow
    assert "push:" in workflow


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param("self hosted", id="space"),
        pytest.param("-self-hosted", id="leading-dash"),
        pytest.param(".self-hosted", id="leading-dot"),
        pytest.param("self/hosted", id="slash"),
        pytest.param('self"hosted', id="quote"),
        pytest.param("self\\hosted", id="backslash"),
        pytest.param("self\nhosted", id="newline"),
        pytest.param("", id="empty"),
    ],
)
def test_python_tooling_1_15__label_alphabet__is_closed(invalid: str) -> None:
    """No admitted label can need YAML escaping, which is what keeps the render exact."""
    with pytest.raises(PackageContractError, match="package options violate schema"):
        _options(_V115, {"runner_labels": [invalid]})


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param("self-hosted", id="bare-string"),
        pytest.param(["self-hosted", "self-hosted"], id="duplicate"),
        pytest.param([1], id="integer-item"),
        pytest.param({"labels": ["self-hosted"]}, id="table"),
    ],
)
def test_python_tooling_1_15__runner_labels_shape__is_closed(invalid: JsonValue) -> None:
    with pytest.raises(PackageContractError, match="package options violate schema"):
        _options(_V115, {"runner_labels": invalid})


def test_python_tooling_1_15__runner_labels__matches_the_sibling_declarations() -> None:
    """A fourth divergent spelling of one organization-wide option is the real risk.

    Issue #132 shipped `runner_labels` in three families and #180 completes the
    rollout here. Consumers copy the block between repositories, so the option must
    validate identically in all four. The released payloads are compared rather
    than restated, so an edit to any of them fails here instead of drifting.
    """
    siblings = {
        "markdown-tooling": "1.14",
        "markdown-frontmatter": "1.10",
        "project-spec": "1.8",
    }
    declarations = {
        standard_id: cast(
            "JsonObject",
            cast(
                "JsonObject",
                json.loads(
                    (
                        _FAMILY.parent / standard_id / "versions" / version / "config.schema.json"
                    ).read_text(encoding="utf-8")
                )["properties"],
            )["runner_labels"],
        )
        for standard_id, version in siblings.items()
    }
    schema = load_option_schema(_V115, _payload(_V115).manifest)
    option = cast("JsonObject", cast("JsonObject", schema.document["properties"])["runner_labels"])

    assert option == {
        "type": "array",
        "items": {
            "type": "string",
            "minLength": 1,
            "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*$",
        },
        "uniqueItems": True,
        "default": [],
    }
    assert all(declaration == option for declaration in declarations.values())


def test_python_tooling_1_15__enforce_line_length__drops_only_the_e501_exclusion() -> None:
    default = tomllib.loads(_render_lint_ignore(_V115, _options(_V115)).decode())
    enforced = tomllib.loads(
        _render_lint_ignore(
            _V115, _options(_V115, {"ruff": {"enforce_line_length": True}})
        ).decode()
    )

    def ignore(document: Mapping[str, object]) -> object:
        tool = cast("Mapping[str, object]", document["tool"])
        ruff = cast("Mapping[str, object]", tool["ruff"])
        return cast("Mapping[str, object]", ruff["lint"])["ignore"]

    assert ignore(default) == ["E501"]
    assert ignore(enforced) == []


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param("true", id="string"),
        pytest.param(1, id="integer"),
        pytest.param([True], id="array"),
    ],
)
def test_python_tooling_1_15__enforce_line_length_shape__is_closed(invalid: JsonValue) -> None:
    with pytest.raises(PackageContractError, match="package options violate schema"):
        _options(_V115, {"ruff": {"enforce_line_length": invalid}})


def test_python_tooling_1_15__lint_ignore_unit__declares_its_governing_option() -> None:
    """A drift report on this key has to name the lever that decides it (issue #181)."""
    manifest = load_payload_manifest(_V115 / "payload.toml")
    [declaration] = [item for item in manifest.contributions if item.scope == _IGNORE_SCOPE]

    assert declaration.governing_options == ["/ruff/enforce_line_length"]


def test_python_tooling_1_15__enforced_limit__is_observable_to_ruff(tmp_path: Path) -> None:
    """Run Ruff against the rendered configuration, because that is the whole claim.

    Issue #181's defect survived every unit-level gate: the option surface looked
    right while the shipped `ignore` silently outranked it. Only Ruff's own verdict
    on an overlong docstring line — prose `ruff format` never reflows — shows the
    declared limit actually became enforceable.

    The fixture prose is deliberately made of separate words: Ruff's E501 skips an
    overlong line that carries no whitespace past the limit, on the grounds that no
    formatter could have split it. A single long run of characters would make this
    test pass in both branches and prove nothing.
    """
    limit = 100
    overlong = f'"""{"word " * 30}"""\n'
    assert len(overlong.rstrip("\n")) > limit
    for name, configured, expected in (
        ("default", {}, False),
        ("enforced", {"ruff": {"enforce_line_length": True}}, True),
    ):
        project = tmp_path / name
        project.mkdir()
        (project / "sample.py").write_text(overlong, encoding="utf-8")
        rendered = _render_lint_ignore(_V115, _options(_V115, cast("JsonObject", configured)))
        (project / "pyproject.toml").write_text(
            f'[tool.ruff]\nline-length = {limit}\n\n[tool.ruff.lint]\nselect = ["E"]\n'
            + rendered.decode().split("\n", 1)[1],
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--no-cache",
                "--output-format",
                "concise",
                ".",
            ],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        assert ("E501" in completed.stdout) is expected, completed.stdout


def test_python_tooling_1_15__versioned_guidance__documents_both_options() -> None:
    readme = (_V115 / "README.md").read_text(encoding="utf-8")
    adopt = (_V115 / "adopt.md").read_text(encoding="utf-8")
    summary = (_V115 / "agent-summary.md").read_text(encoding="utf-8")

    for text in (readme, adopt, summary):
        assert "runner_labels" in text
        assert "enforce_line_length" in text
    assert "runner_labels = []" in adopt
    assert "enforce_line_length = false" in adopt


def test_python_tooling_1_15__machine_readable_payload__carries_no_1_14_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.14.

    Every prior cut in this repository inherited at least one stale embedded
    version string — a schema const, a migration id, a transform endpoint — that
    no per-cut assertion caught.

    The sweep covers the declarative files, where every `1.14` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown and the provider's own prose
    are excluded for the same reason and are pinned by the narrower assertion below,
    which names the one machine-readable version literal the provider emits.
    """
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        path.relative_to(_V115).as_posix()
        for path in _V115.rglob("*")
        if path.is_file()
        and path.suffix in {".json", ".toml", ".yml"}
        and re.search(
            r"(?<![\d.])1[.-]14(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()

    provider = (_V115 / "providers/python_tooling.py").read_text(encoding="utf-8")
    assert '"version": "1.15"' in provider
    assert '"version": "1.14"' not in provider


def test_python_tooling_1_15__migration_edges__retarget_without_a_new_edge() -> None:
    """1.12, 1.13, and 1.14 owe no edge: their default units and bytes are unchanged."""
    manifest = load_payload_manifest(_V115 / "payload.toml")

    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        *(f"package:1.{minor}" for minor in range(1, 12)),
        "legacy:v4-python-tooling",
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.15"


def test_python_tooling_1_15__projection_and_index__are_complete() -> None:
    source_files = {
        path.relative_to(_V115).as_posix()
        for path in _V115.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    projected_files = {
        path.relative_to(_PROJECTION_115).as_posix()
        for path in _PROJECTION_115.rglob("*")
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_115 / relative).resolve() == (_V115 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in _PROJECTION_115.rglob("*") if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.15"]["payload"] == "versions/1.15/payload.toml"
    assert versions["1.15"]["digest"] == _payload(_V115).integrity.aggregate_digest.value
    assert "python-tooling@1.15" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_python_tooling_1_15__mutable_navigation__names_the_new_authority() -> None:
    """The family pages track the current default, which moved to 1.16 (issue #182)."""
    for name in ("README.md", "adopt.md", "agent-summary.md"):
        content = (_FAMILY / name).read_text(encoding="utf-8")
        assert f"versions/1.16/{name}" in content
        assert "versions/1.15/" not in content
