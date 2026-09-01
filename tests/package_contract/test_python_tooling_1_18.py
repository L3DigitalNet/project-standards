"""Pin the Python Tooling 1.18 project-metadata tightening and its three doc fixes.

Issue #204 is the behavioral half. Through 1.17 `_metadata_findings` returned an
empty list the moment `build_backend = "none"` was selected, so a repository that
declared itself non-installable could reconcile clean with no `[project]` table
and then fail at the very next documented step: `uv lock` refuses any
`pyproject.toml` without that table, whatever backend is chosen, and every `uv
run` command in the rendered gate refuses it too. 1.18 drops the short-circuit,
so the guard is evaluated for every adoption. The rows below assert both
directions on 1.18 and keep 1.17 as the negative control, because a "fix" that
mutated the released payload instead of cutting 1.18 has to break something.

Issues #205 and #206 are documentation-only, and their assertions are
deliberately narrow: each names the one fact the adopter could not get from the
payload before — that declared source roots scope the checkers without making a
subproject importable, and that an undeclared `[tool.pytest.ini_options]` key is
consumer-owned but must not be written before its plugin is installed, because
the package-owned `addopts` carries `--strict-config`.

Nothing else in the payload moves, so the remaining contract is that 1.18 renders
byte-identical output to 1.17 for every unit and offers the identical option
surface.
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

from project_standards.control_plane.diagnostics import ControlFinding, ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
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
from tests.control_plane.planner_helpers import resolution_request
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V117 = _FAMILY / "versions/1.17"
_V118 = _FAMILY / "versions/1.18"
_PROJECTION_118 = _ROOT / "src/project_standards/payloads/python-tooling/1.18"

_METADATA_FINDING = "PT-PROJECT-METADATA"
_WORKFLOW = ".github/workflows/check.yml"

# A repository that declared itself non-installable and never wrote `[project]`:
# the exact shape 1.17's adoption guide told adopters was complete, and the one
# `uv lock` rejects with "No 'project' table found" (issue #204).
_NO_PROJECT_PYPROJECT = '[tool.example]\nkey = "value"\n'

# The shape uv classifies as `source = { virtual = "." }`: consumer identity
# present, no build backend. This is what a `build_backend = "none"` adoption is
# supposed to look like, and it must stay finding-free or the tightening would be
# refusing the very configuration the guide now prescribes.
_VIRTUAL_PYPROJECT = (
    '[project]\nname = "example-package"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n'
)

_NONE_BACKEND: JsonObject = {"build_backend": "none"}

_V117_AGGREGATE = "sha256:4c5ec078fd033cf3bf14c16f6fbc5b48e58d24ffe03b026b30b1e76b9b0a0950"

# The predecessor is advertised and therefore immutable: a byte change anywhere in
# it is a released-payload mutation, not a diff to review. Pinning the whole tree
# rather than only the files 1.18 happened to touch is what makes that detectable.
_V117_FILES = {
    "README.md": "87e8342e04339002a1aa70cd433b3517caebfa597eff87b31f5a78ffa8e2cff2",
    "adopt.md": "fcaff268d6993e07fdf40f3e0f7b2137b22070aacc24b22f7837943a7c53e12e",
    "agent-summary.md": "66db775044037d7eb69480bb72e1da4563db66e464d1ce8c4a0d3e38e06ebcaa",
    "build-backend.md": "d0d2120f49df6ad6475d807a087933ad0d66b2b796c31ddb690e36874d53d089",
    "config.schema.json": ("aea8a435c489fa0c1297032c2cbbd481d236002a9a6a94e5e14d06aeaa78470e"),
    "payload.toml": "c201d12d64cb70ccce7a83de6f76f097623dd41e12b732d26114759c85f112c4",
    "providers/python_tooling.py": (
        "a921286de414fedde2e8bf7ccf79403b5b210b99f80e91bc0ad4095287d6c4d6"
    ),
    "resources/check.py": "04930fcc2fc4f9f82af40591a1ea68e8a791c9bc0c8732749439b34afe04091a",
    "resources/check.yml": "63c4c3ca416c09767f2bbe5638ed87fbdd59c784856056562daf9425d161d916",
    "resources/python-version": (
        "a876e0b10411037a012498b9fe18d9bc1df32ed8b722a13564dc944ddcfd9135"
    ),
    "schemas/config-transform-input.schema.json": (
        "534c8739324804ecfe1b473b3affaa313eaa56026118daecdb307317cf66300f"
    ),
    "schemas/config-transform-report.schema.json": (
        "17f5c69de00ddec8b884559e82b3f52b532c67cf723924940c1eb84875037461"
    ),
    "schemas/content.schema.json": (
        "760d819048c1f2a153e72227c940f36eed96deb5e2336e802f34caa37ccf14b3"
    ),
    "schemas/findings.schema.json": (
        "c838f02865d72e8d2aa4d6640e1fb50d03187122571752d1c75970f93ffb1066"
    ),
    "schemas/migration-report.schema.json": (
        "c20927b47e91a49a5f97ef0e85c23240e803f68d57f2caf55602fd83330b91b1"
    ),
    "schemas/provider-input.schema.json": (
        "ad6970722987619f4583658f1c78af068f5b58938460c18b28590202dff83488"
    ),
}

# Option shapes spelled in 1.17's own vocabulary, each moving a knob some rendered
# unit actually reads. Resolving the same source text under both payloads compares
# real renders rather than a repeated default.
_PREDECESSOR_SHAPES: tuple[JsonObject, ...] = (
    {},
    {"build_backend": "none"},
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


def _plan(repo: Path, root: Path, config: JsonObject) -> ReconciliationPlan:
    payload = _payload(root)
    return plan_reconciliation(
        PlannerRequest(
            repo,
            resolution_request((payload,), configs={"python-tooling": config}),
            (payload,),
        )
    )


def _metadata_findings(plan: ReconciliationPlan) -> list[ControlFinding]:
    return [finding for finding in plan.findings if finding.code == _METADATA_FINDING]


def _consumer(tmp_path: Path, pyproject: str) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return repo


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


def _render_dev_dependencies(root: Path, config: JsonObject) -> bytes:
    return _render(
        root,
        {
            "id": "dev-dependencies",
            "target": "pyproject.toml",
            "adapter": AdapterKind.TOML.value,
            "scope": "key:/dependency-groups/dev",
        },
        config,
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


def test_python_tooling_1_18__none_backend_without_project__now_blocks(tmp_path: Path) -> None:
    """The defect: 1.17 let this adoption through, and `uv lock` then refused it."""
    repo = _consumer(tmp_path, _NO_PROJECT_PYPROJECT)

    plan = _plan(repo, _V118, _NONE_BACKEND)

    findings = _metadata_findings(plan)
    assert len(findings) == 1, plan.findings
    finding = findings[0]
    assert finding.severity == "error"
    assert finding.path == "pyproject.toml"
    assert not plan.applicable
    # The hint may no longer offer `build_backend = "none"` as a way out of this
    # finding: from 1.18 that option is already selected here and changes nothing.
    assert "[project]" in finding.hint
    assert "or declare the repository deliberately non-installable" not in finding.hint


def test_python_tooling_1_18__predecessor_short_circuits_on_the_same_input(
    tmp_path: Path,
) -> None:
    """CONTROL: 1.17's bytes are frozen, so the same adoption must still pass there.

    This row is what distinguishes an authored 1.18 from a released payload edited
    in place. It must keep passing forever.
    """
    repo = _consumer(tmp_path, _NO_PROJECT_PYPROJECT)

    plan = _plan(repo, _V117, _NONE_BACKEND)

    assert _metadata_findings(plan) == []


def test_python_tooling_1_18__project_without_build_system__is_accepted(tmp_path: Path) -> None:
    """`[project]` with no `[build-system]` is uv's virtual source; it must not fault.

    Tightening the guard is only correct if the configuration the corrected
    adoption guide prescribes is the one that passes.
    """
    repo = _consumer(tmp_path, _VIRTUAL_PYPROJECT)

    plan = _plan(repo, _V118, _NONE_BACKEND)

    assert _metadata_findings(plan) == []
    document = tomllib.loads(_VIRTUAL_PYPROJECT)
    assert "build-system" not in document


def test_python_tooling_1_18__installable_backends__keep_the_1_17_behavior(
    tmp_path: Path,
) -> None:
    """The guard's original case is untouched: a missing `[project]` still blocks."""
    repo = _consumer(tmp_path, _NO_PROJECT_PYPROJECT)

    for root in (_V117, _V118):
        plan = _plan(repo, root, {"build_backend": "uv_build"})
        assert len(_metadata_findings(plan)) == 1, (root.name, plan.findings)


def test_python_tooling_1_18__adoption_guide__stops_contradicting_itself() -> None:
    """Issue #204: 1.17's guide said `none` needs no `[project]` two lines above the block."""
    adopt = (_V118 / "adopt.md").read_text(encoding="utf-8")

    assert "needs no `[project]` table" not in adopt
    assert "it does not remove the `[project]` requirement" in adopt
    assert 'source = { virtual = "." }' in adopt
    assert "issues/204" in adopt


def test_python_tooling_1_18__adoption_guide__wires_subproject_imports() -> None:
    """Issue #205: declared roots are scopes, not import paths, and the guide now says so."""
    adopt = (_V118 / "adopt.md").read_text(encoding="utf-8")

    assert "ModuleNotFoundError" in adopt
    assert 'pythonpath = ["subproj/src"]' in adopt
    # Both routes and the difference between them: pytest alone versus every
    # `uv run` command. A guide naming only one of the two repeats the defect for
    # the next adopter who needs the other.
    assert "uv workspace member" in adopt
    assert "additional_dev_dependencies" in adopt


def test_python_tooling_1_18__adoption_guide__states_the_pytest_ini_ownership_rule() -> None:
    """Issue #206: undeclared ini keys are consumer-owned, but `--strict-config` orders them."""
    adopt = (_V118 / "adopt.md").read_text(encoding="utf-8")

    assert "asyncio_mode" in adopt
    assert "--strict-config" in adopt
    # pytest's own message names neither the flag nor the missing plugin, so the
    # row has to quote it verbatim or an adopter cannot match what they saw.
    assert "ERROR: Unknown config option: asyncio_mode" in adopt
    # The owned set is exactly what `_pytest_key` enumerates; a guide that named a
    # wider set would invite a consumer to hand-edit a managed key.
    provider = (_V118 / "providers/python_tooling.py").read_text(encoding="utf-8")
    for key in ("minversion", "testpaths", "addopts", "markers"):
        assert f'"{key}"' in provider
        assert f"`{key}`" in adopt


def test_python_tooling_1_18__additional_dev_dependencies__is_explained() -> None:
    """Issue #205 secondary finding: 1.17 shipped a bare `= []` example and no prose."""
    adopt = (_V118 / "adopt.md").read_text(encoding="utf-8")

    explanatory = [
        line
        for line in adopt.splitlines()
        if "additional_dev_dependencies" in line and not line.startswith(("|", "additional_dev"))
    ]
    assert explanatory, "additional_dev_dependencies still appears only as a config example"
    assert "dependency-groups" in adopt


def test_python_tooling_1_18__additional_dev_dependencies__fault_stays_bounded() -> None:
    """A non-string entry must raise the provider's bounded ValueError, not a TypeError.

    Every sibling list option gets that contract from `_string_list`. This one
    cannot use the helper, because the helper rejects `<` and `>` and those are
    ordinary characters in a PEP 508 requirement — so the second half of this row
    pins that a version-bounded requirement still renders.
    """
    config = dict(_options(_V118))
    config["additional_dev_dependencies"] = [7]
    # The control plane wraps a provider fault in a ControlPlaneError whose own
    # message carries only the coordinate, so the bounded contract is observable
    # on the chained cause: a ValueError naming the option, never a bare TypeError
    # out of `_dependency_name`'s `re.split`.
    with pytest.raises(ControlPlaneError) as raised:
        _render_dev_dependencies(_V118, config)
    cause = raised.value.__cause__
    assert isinstance(cause, ValueError)
    assert "config.additional_dev_dependencies" in str(cause)

    config["additional_dev_dependencies"] = ["pytest-asyncio>=1.0,<2"]
    rendered = _render_dev_dependencies(_V118, config).decode("utf-8")
    assert "pytest-asyncio>=1.0,<2" in rendered


def test_python_tooling_1_18__option_surface__is_unchanged() -> None:
    """This cut changes a finding and prose, so the consumer's option vocabulary is frozen."""
    assert _options(_V118) == _options(_V117)
    # The provider decides whether to serve the immutable static resource by
    # comparing the resolved config against its own default mapping, so the two
    # must agree key for key; a schema default missing there silently routes every
    # default adoption down the rendered branch instead.
    assert _provider_default_config(_V118) == _options(_V118)


def test_python_tooling_1_18__rendered_units__are_byte_identical_to_1_17() -> None:
    """No rendered byte moves in this cut, so no consumer sees a reconcile diff."""
    for shape in _PREDECESSOR_SHAPES:
        config = _options(_V117, shape)
        assert _options(_V118, shape) == config
        assert _render_workflow(_V118, config) == _render_workflow(_V117, config), shape
        assert _render_dev_dependencies(_V118, config) == _render_dev_dependencies(_V117, config)


def test_python_tooling_1_18__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        path.relative_to(_V117).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in payload_tree(_V117)
        if path.is_file()
    }
    assert actual == {path: (0o644, digest) for path, digest in _V117_FILES.items()}
    assert (
        validate_payload_integrity(
            _V117, load_payload_manifest(_V117 / "payload.toml")
        ).aggregate_digest.value
        == _V117_AGGREGATE
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
        **{f"1.{minor}": "retained" for minor in range(1, 18)},
        "1.18": "default",
    }


def test_python_tooling_1_18__versioned_guidance__records_the_behavior_change() -> None:
    """An adopter must learn from the exact-release README that the guard tightened.

    The change is invisible to option resolution: nothing in the config surface
    moves, so a consumer who reads only the options never discovers that a clean
    1.17 reconcile can become a blocked 1.18 one.
    """
    readme = (_V118 / "README.md").read_text(encoding="utf-8")

    assert "PT-PROJECT-METADATA" in readme
    assert "issues/204" in readme
    # Not a silent tightening: the README has to say the affected repository was
    # already failing, or an adopter reads the block as a regression.
    assert "was already failing at `uv lock`" in readme
    assert "surfaces that existing failure" in readme


def test_python_tooling_1_18__machine_readable_payload__carries_no_1_17_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.17.

    Every prior cut in this repository inherited at least one stale embedded
    version string — a schema const, a migration id, a transform endpoint — that no
    per-cut assertion caught. Note that the migration ids spell the version with a
    hyphen (`-to-1-17`), which a dotted-version sweep alone would miss.

    The sweep covers the declarative files, where every `1.17` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown and the provider's own prose
    are excluded for the same reason and are pinned by the narrower assertion below,
    which names the one machine-readable version literal the provider emits.
    """

    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        path.relative_to(_V118).as_posix()
        for path in payload_tree(_V118)
        if path.is_file()
        and path.suffix in {".json", ".toml", ".yml"}
        and re.search(
            r"(?<![\d.])1[.-]17(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()

    provider = (_V118 / "providers/python_tooling.py").read_text(encoding="utf-8")
    assert '"version": "1.18"' in provider
    assert '"version": "1.17"' not in provider


def test_python_tooling_1_18__migration_edges__retarget_without_a_new_edge() -> None:
    """1.12 through 1.17 owe no edge: this cut moves a finding, and a finding is not lock state."""
    manifest = load_payload_manifest(_V118 / "payload.toml")

    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        *(f"package:1.{minor}" for minor in range(1, 12)),
        "legacy:v4-python-tooling",
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.18"


def test_python_tooling_1_18__projection_and_index__are_complete() -> None:
    source_files = {
        path.relative_to(_V118).as_posix() for path in payload_tree(_V118) if path.is_file()
    }
    projected_files = {
        path.relative_to(_PROJECTION_118).as_posix()
        for path in payload_tree(_PROJECTION_118)
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_118 / relative).resolve() == (_V118 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in payload_tree(_PROJECTION_118) if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.18"]["payload"] == "versions/1.18/payload.toml"
    assert versions["1.18"]["digest"] == _payload(_V118).integrity.aggregate_digest.value
    assert "python-tooling@1.18" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_python_tooling_1_18__mutable_navigation__names_the_new_authority() -> None:
    for name in ("README.md", "adopt.md", "agent-summary.md"):
        content = (_FAMILY / name).read_text(encoding="utf-8")
        assert f"versions/1.18/{name}" in content
        assert "versions/1.17/" not in content
