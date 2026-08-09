"""Pin the Python Tooling 1.13 scoped per-file-ignore contract (issue #116).

Every 1.13 access happens inside a test behind `_require_payload`: while 1.13 is
unauthored these rows must FAIL on the missing contract, never error during
collection, so the red signal stays readable.

Two rows name 1.12 alone and PASS today. They are the negative controls: they
prove the released options cannot express a scoped exemption at all — only a
repository-wide `extend_ignore` — and freeze the predecessor bytes the successor
must not disturb. A hollow fix that widened 1.12 instead of authoring 1.13
breaks them.
"""

import json
import os
import subprocess
import tomllib
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
from tests.control_plane.planner_helpers import resolution_request
from tests.package_contract.helpers import ruff_declarations, ruff_source, selects_ruff

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V112 = _FAMILY / "versions/1.12"
_V113 = _FAMILY / "versions/1.13"

_PER_FILE_SCOPE = "table:/tool/ruff/lint/per-file-ignores"
_OPTION = "extend_per_file_ignores"
_OPTION_POINTER = "/ruff/extend_per_file_ignores"

# The released aggregate digest published for 1.12 in catalogs/5.toml. Pinned as
# a literal rather than recomputed: recomputation would agree with whatever the
# payload happens to contain, which is exactly what this control must refuse.
_V112_AGGREGATE = "sha256:7595019e39b209fb700817b0563aa2e5db50d368c3c5042eeb714e234076de5f"

# The package's own per-file ignores, which every composed result must retain.
_PACKAGE_GLOB = "tests/**/*.py"
_PACKAGE_RULES = ["S101"]

# Issue #116's reported intent: `Any` is permitted at dynamic test boundaries
# while ANN401 keeps governing shipped code.
_TESTS_EXTENSION: JsonObject = {_PACKAGE_GLOB: ["ANN401"]}

# Ruff's own extension table, which 1.12 declared consumer-owned by construction
# and 1.13 must leave that way — it is the documented pre-1.13 workaround, so a
# repository upgrading into the typed option may still be carrying it.
_CONSUMER_TABLE = '[tool.ruff.lint.extend-per-file-ignores]\n"docs/**/*.py" = ["INP001"]\n'


def _require_payload(root: Path) -> None:
    assert root.is_dir(), f"python-tooling payload {root.name} is not authored yet"
    assert (root / "payload.toml").is_file(), f"payload {root.name} declares no manifest"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, **overrides: JsonValue) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(overrides)


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
                    "id": "unit-under-test",
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


def _per_file_ignores(root: Path, **ruff: JsonValue) -> JsonObject:
    """Return the resolved per-file-ignore table the payload renders under `ruff`."""
    rendered = _render(root, _PER_FILE_SCOPE, _options(root, ruff=ruff))
    document = tomllib.loads(rendered)
    tool = cast("JsonObject", document["tool"])
    lint = cast("JsonObject", cast("JsonObject", tool["ruff"])["lint"])
    return cast("JsonObject", lint["per-file-ignores"])


def _ruff_properties(root: Path) -> JsonObject:
    schema = load_option_schema(root, _payload(root).manifest)
    properties = cast("JsonObject", schema.document["properties"])
    return cast("JsonObject", cast("JsonObject", properties["ruff"])["properties"])


def _write_consumer(repo: Path, *, ruff_table: str = "", extension_table: bool = True) -> None:
    """Materialize the reporting consumer: metadata plus Ruff's own extension table.

    The `[project]` table is not decoration: without it the package's own
    consumer-state validation (issue #109) refuses the adoption before ownership
    is ever classified, and the behavior under test would never be reached.
    """
    repo.mkdir(parents=True, exist_ok=True)
    sections = [
        '[project]\nname = "example-package"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n'
    ]
    if ruff_table:
        sections.append(ruff_table.rstrip("\n") + "\n")
    if extension_table:
        sections.append(_CONSUMER_TABLE)
    (repo / "pyproject.toml").write_text("\n".join(sections), encoding="utf-8")


def _request(repo: Path, payload: InstalledPayload, config: JsonObject) -> PlannerRequest:
    return PlannerRequest(
        repo,
        resolution_request((payload,), configs={"python-tooling": config}),
        (payload,),
    )


def _plan(request: PlannerRequest) -> ReconciliationPlan:
    return plan_reconciliation(request)


def _apply(repo: Path, payload: InstalledPayload, config: JsonObject) -> ReconciliationPlan:
    """Reconcile `repo` once from a clean lock and assert the apply succeeded."""
    request = _request(repo, payload, config)
    control = repo / ".standards"
    control.mkdir(exist_ok=True)
    (control / "lock.toml").write_bytes(render_lock(request.resolution.previous_lock))
    plan = _plan(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    return plan


def _managed_per_file_ignores(repo: Path) -> JsonObject:
    document = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tool = cast("JsonObject", document["tool"])
    lint = cast("JsonObject", cast("JsonObject", tool["ruff"])["lint"])
    return cast("JsonObject", lint["per-file-ignores"])


# ---------------------------------------------------------------------------
# Negative controls: these PASS today and must keep passing.
# ---------------------------------------------------------------------------


def test_python_tooling_1_13__issue_116__predecessor_can_only_disable_globally() -> None:
    """CONTROL: 1.12 exposes no scoped option, so ANN401 can only be dropped repository-wide.

    This is the reported reproduction. It must keep failing on 1.12 forever: the
    successor earns its version by adding an option, not by relaxing a released
    payload.
    """
    _require_payload(_V112)

    assert _OPTION not in _ruff_properties(_V112)
    assert _per_file_ignores(_V112) == {_PACKAGE_GLOB: _PACKAGE_RULES}

    # The only response the released options can express is strictly weaker than
    # the reported intent: ANN401 goes off for the whole repository, shipped
    # scripts included.
    rendered = _render(
        _V112,
        "key:/tool/ruff/lint/extend-ignore",
        _options(_V112, ruff={"extend_ignore": ["ANN401"]}),
    )
    assert 'extend-ignore = ["ANN401"]' in rendered


def test_python_tooling_1_13__released_predecessor__keeps_its_exact_bytes() -> None:
    """CONTROL: 1.12 stays byte-immutable and keeps its ungoverned per-file-ignore unit."""
    _require_payload(_V112)
    manifest = load_payload_manifest(_V112 / "payload.toml")
    governance = {
        declaration.scope: declaration.governing_options
        for declaration in manifest.contributions
        if declaration.scope == _PER_FILE_SCOPE
    }

    assert governance == {_PER_FILE_SCOPE: []}
    assert validate_payload_integrity(_V112, manifest).aggregate_digest.value == _V112_AGGREGATE


# ---------------------------------------------------------------------------
# The 1.13 contract: every row below fails on the unauthored payload.
# ---------------------------------------------------------------------------


def test_python_tooling_1_13__provider_input_schema__pins_its_own_payload_identity() -> None:
    """The render envelope's consts must name the payload that ships them.

    A successor copies the predecessor's schemas forward, and a copy that keeps the
    predecessor's `version` const fails closed in `_validate_json_schema` on the first
    render after the version becomes selectable — the payload is unreachable, not
    merely mislabelled. Both sides are derived from the manifest so a stale copy is
    visible at cut time rather than at release prep.
    """
    _require_payload(_V113)
    manifest = load_payload_manifest(_V113 / "payload.toml")
    schema = cast(
        "JsonObject",
        json.loads((_V113 / "schemas/provider-input.schema.json").read_text(encoding="utf-8")),
    )
    properties = cast("JsonObject", schema["properties"])

    assert cast("JsonObject", properties["version"])["const"] == manifest.payload.version.value
    assert cast("JsonObject", properties["standard_id"])["const"] == manifest.payload.standard


def test_python_tooling_1_13__option_schema__declares_a_closed_glob_to_rule_map() -> None:
    """The option is a typed map of Ruff glob to a nonempty list of rule selectors."""
    _require_payload(_V113)
    option = cast("JsonObject", _ruff_properties(_V113)[_OPTION])

    assert option["type"] == "object"
    assert option["default"] == {}
    values = cast("JsonObject", option["additionalProperties"])
    assert values["type"] == "array"
    assert values["uniqueItems"] is True
    assert values["minItems"] == 1
    assert cast("JsonObject", values["items"])["pattern"] == "^[A-Z][A-Z0-9]*$"


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param({_PACKAGE_GLOB: []}, id="empty-rule-list"),
        pytest.param({_PACKAGE_GLOB: ["ann401"]}, id="lowercase-selector"),
        pytest.param({_PACKAGE_GLOB: ["ANN401", "ANN401"]}, id="duplicate-selector"),
        pytest.param({"": ["ANN401"]}, id="empty-glob"),
        pytest.param({_PACKAGE_GLOB: "ANN401"}, id="scalar-instead-of-list"),
    ],
)
def test_python_tooling_1_13__option_schema__rejects_malformed_entries(invalid: JsonValue) -> None:
    """Rule codes and glob shapes are validated at option resolution, not at Ruff runtime."""
    _require_payload(_V113)

    with pytest.raises(Exception):  # noqa: B017 - schema layer raises its own error type
        _options(_V113, ruff={_OPTION: invalid})


def test_python_tooling_1_13__empty_default__renders_the_predecessor_bytes() -> None:
    """The default contributes nothing, so an existing 1.12 consumer sees no change.

    Byte parity against the released 1.12 unit, not merely equivalent TOML: this
    is what makes the cut a no-op for every repository that does not opt in, and
    it is why no 1.12-to-1.13 migration edge is declared.
    """
    _require_payload(_V113)
    _require_payload(_V112)

    assert _render(_V113, _PER_FILE_SCOPE, _options(_V113)) == _render(
        _V112, _PER_FILE_SCOPE, _options(_V112)
    )


def test_python_tooling_1_13__two_rules_on_one_glob__compose_with_the_package_default() -> None:
    """Acceptance (a): several rules on one glob extend the package entry, never replace it."""
    _require_payload(_V113)

    composed = _per_file_ignores(_V113, extend_per_file_ignores={_PACKAGE_GLOB: ["ANN401", "D103"]})

    assert composed == {_PACKAGE_GLOB: ["S101", "ANN401", "D103"]}


def test_python_tooling_1_13__distinct_globs__render_side_by_side() -> None:
    """Acceptance (b): distinct rules on distinct globs each get their own entry."""
    _require_payload(_V113)

    composed = _per_file_ignores(
        _V113,
        extend_per_file_ignores={"scripts/*.py": ["T201"], "docs/**/*.py": ["INP001"]},
    )

    assert composed == {
        _PACKAGE_GLOB: _PACKAGE_RULES,
        "docs/**/*.py": ["INP001"],
        "scripts/*.py": ["T201"],
    }


def test_python_tooling_1_13__render__is_independent_of_option_key_order() -> None:
    """Sorted emission keeps the unit — and every digest over it — a function of the value."""
    _require_payload(_V113)

    forward = _render(
        _V113,
        _PER_FILE_SCOPE,
        _options(
            _V113,
            ruff={_OPTION: {"a/*.py": ["B008", "ANN401"], "z/*.py": ["T201"]}},
        ),
    )
    reversed_order = _render(
        _V113,
        _PER_FILE_SCOPE,
        _options(
            _V113,
            ruff={_OPTION: {"z/*.py": ["T201"], "a/*.py": ["ANN401", "B008"]}},
        ),
    )

    assert forward == reversed_order


def test_python_tooling_1_13__unit_governance__names_the_new_option() -> None:
    """The unit declares the one option that can change its value, as the contract requires."""
    _require_payload(_V113)
    manifest = load_payload_manifest(_V113 / "payload.toml")
    declaration = next(item for item in manifest.contributions if item.scope == _PER_FILE_SCOPE)

    assert declaration.governing_options == [_OPTION_POINTER]


def test_python_tooling_1_13__ruff_extension_table__stays_consumer_owned() -> None:
    """1.12's ownership rule survives: the package still declares no `extend-per-file-ignores`.

    Taking that table over would make the documented pre-1.13 workaround into
    managed drift for the very repositories issue #116 was filed from, which is
    why the typed option composes into the already-owned table instead.
    """
    _require_payload(_V113)
    manifest = load_payload_manifest(_V113 / "payload.toml")
    scopes = {declaration.scope for declaration in ruff_declarations(manifest, _options(_V113))}

    assert _PER_FILE_SCOPE in scopes
    assert not [scope for scope in scopes if "extend-per-file-ignores" in scope]


def test_python_tooling_1_13__reconcile__accepts_the_scoped_extension_and_converges(
    tmp_path: Path,
) -> None:
    """`reconcile --check` reports no managed drift, and a second pass is a fixed point."""
    _require_payload(_V113)
    repo = tmp_path / "consumer"
    _write_consumer(repo)
    payload = _payload(_V113)
    config: JsonObject = {"ruff": {_OPTION: _TESTS_EXTENSION}}

    plan = _apply(repo, payload, config)

    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert _managed_per_file_ignores(repo) == {_PACKAGE_GLOB: ["S101", "ANN401"]}
    # Both routes coexist: the consumer's own extension table is untouched.
    assert _CONSUMER_TABLE.splitlines()[1] in text

    second_request = PlannerRequest(
        repo,
        resolution_request(
            (payload,),
            configs={"python-tooling": config},
            previous_lock=plan.next_lock,
        ),
        (payload,),
    )
    second = plan_reconciliation(second_request)
    result = apply_reconciliation(ApplyRequest(second_request, second))

    assert second.applicable, second.findings
    assert not [
        finding
        for finding in second.findings
        if finding.code == "CP-CONSUMER-CONFLICT" and selects_ruff(finding.identity)
    ]
    assert result.success
    assert result.applied_action_ids == ()
    assert (repo / "pyproject.toml").read_text(encoding="utf-8") == text


def test_python_tooling_1_13__removing_the_input__removes_only_the_extension(
    tmp_path: Path,
) -> None:
    """Dropping the option restores the package default and nothing else moves."""
    _require_payload(_V113)
    repo = tmp_path / "consumer"
    _write_consumer(repo)
    payload = _payload(_V113)

    plan = _apply(repo, payload, {"ruff": {_OPTION: _TESTS_EXTENSION}})
    assert _managed_per_file_ignores(repo) == {_PACKAGE_GLOB: ["S101", "ANN401"]}

    removed_request = PlannerRequest(
        repo,
        resolution_request(
            (payload,),
            configs={"python-tooling": {}},
            previous_lock=plan.next_lock,
        ),
        (payload,),
    )
    removed = plan_reconciliation(removed_request)
    assert removed.applicable, removed.findings
    assert apply_reconciliation(ApplyRequest(removed_request, removed)).success

    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert _managed_per_file_ignores(repo) == {_PACKAGE_GLOB: _PACKAGE_RULES}
    assert _CONSUMER_TABLE.splitlines()[1] in text


def _ruff(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the real linter as the oracle, from this repository's locked toolchain.

    PYTHONPATH and VIRTUAL_ENV are stripped for the same reason the 1.12 suite
    strips them: this suite runs under the extracted wheel runtime inside the
    repository venv, and either would leak into the child's resolution. UV_PROJECT
    keeps the offline environment while the CWD stays the fixture, so Ruff
    discovers the fixture's own pyproject.toml — the managed file under test.
    """
    environment = {
        key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "VIRTUAL_ENV"}
    }
    environment.update({"UV_OFFLINE": "1", "UV_PROJECT": str(_ROOT)})
    return subprocess.run(
        ["uv", "run", "ruff", "check", *arguments],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


# Both modules use the same dynamic boundary the report describes, so the only
# thing separating their findings is the path they sit at.
_ANY_MODULE = '''"""Load a value through a dynamic boundary that cannot be typed precisely."""

from typing import Any


def unwrap(payload: Any) -> str:
    """Return the payload as text."""
    assert payload is not None
    return str(payload)
'''


def test_python_tooling_1_13__ruff_oracle__scopes_the_exemption_without_a_global_disable(
    tmp_path: Path,
) -> None:
    """The acceptance is behavioral, so the oracle is the real linter on the managed file.

    ANN401 must be live for shipped code and silent under the tests glob, and
    S101 must stay silent there too — proving the package default composed rather
    than being replaced by the consumer entry.
    """
    _require_payload(_V113)
    repo = tmp_path / "consumer"
    options = _options(
        _V113,
        ruff={"extend_select": ["ANN", "S"], _OPTION: _TESTS_EXTENSION},
    )
    _write_consumer(
        repo,
        ruff_table=ruff_source(
            lambda scope: _render(_V113, scope, options), _payload(_V113).manifest, options
        ),
    )
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "src/example.py").write_text(_ANY_MODULE, encoding="utf-8")
    (repo / "tests/test_example.py").write_text(_ANY_MODULE, encoding="utf-8")

    shipped = _ruff(repo, "--output-format", "concise", "src")
    tested = _ruff(repo, "--output-format", "concise", "tests")

    shipped_output = shipped.stdout + shipped.stderr
    tested_output = tested.stdout + tested.stderr
    # No global disable: the rule the consumer scoped is still enforced elsewhere.
    assert "ANN401" in shipped_output, shipped_output
    assert "S101" in shipped_output, shipped_output
    # Scoped exemption plus surviving package default.
    assert "ANN401" not in tested_output, tested_output
    assert "S101" not in tested_output, tested_output
