"""Pin the Python Tooling 1.12 Ruff ownership contract (issue #99 / TC-T19-001).

Every 1.12 access happens inside a test behind `_require_payload`: while 1.12 is
unauthored these rows must FAIL on the missing contract, never error during
collection, so the red signal stays readable.

Three rows name 1.11 alone and PASS today. They are the negative controls: they
pin the reported reproduction, prove the released options cannot express the
consumer's intent, and freeze the predecessor bytes the successor must not
disturb. A hollow fix that widened 1.11 instead of authoring 1.12 breaks them.
"""

import os
import subprocess
import tomllib
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.codec import render_lock, semantic_digest
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.models import AppliedPackage, CentralLock
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    plan_reconciliation,
)
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.control_plane.resolution import DeclaredTransition
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    ContributionDeclaration,
    JsonObject,
    JsonValue,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.control_plane.planner_helpers import previous_lock, resolution_request

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-tooling"
_V111 = _FAMILY / "versions/1.11"
_V112 = _FAMILY / "versions/1.12"

_RUFF_TABLE_SCOPE = "table:/tool/ruff"
# The released aggregate digest published for 1.11 in catalogs/5.toml. Pinned as
# a literal rather than recomputed: recomputation would agree with whatever the
# payload happens to contain, which is exactly what this control must refuse.
_V111_AGGREGATE = "sha256:8d288645905cbf8954f246e3631d8636353ac590d62eacc70e68ae75e1057fb2"

# Issue #99's exact consumer value: Typer's Option/Argument return immutable
# sentinels its decorator consumes, so the allow-list suppresses the false B008
# at those call sites while B008 stays selected everywhere else.
_PLUGIN_TABLE = (
    '[tool.ruff.lint.flake8-bugbear]\nextend-immutable-calls = ["typer.Option", "typer.Argument"]\n'
)
_PLUGIN_CALLS = ["typer.Option", "typer.Argument"]

# The nine options the reported CP-CONSUMER-CONFLICT lists as governing the one
# owned unit, none of which reaches a lint plugin sub-table.
_ISSUE_99_GOVERNING = frozenset(
    {
        "python_version",
        "/ruff/line_length",
        "/ruff/extend_exclude",
        "/ruff/extend_include",
        "/ruff/extend_select",
        "/ruff/extend_ignore",
        "source_layout",
        "additional_source_roots",
        "/pytest/test_paths",
    }
)

# T19 GREEN contract: one leaf-addressable unit per rendered Ruff key, so every
# undeclared `[tool.ruff.lint.*]` plugin table is outside package ownership by
# construction. `per-file-ignores` and `format` stay whole tables: both are
# complete package-authored leaves with no plugin-extension surface beneath them.
# An empty frozenset means the payload must declare `governing_options = []` —
# the explicit "no option governs this unit" spelling, which is not the same as
# omitting the field.
_RUFF_UNIT_GOVERNANCE: dict[str, frozenset[str]] = {
    "key:/tool/ruff/target-version": frozenset({"python_version"}),
    "key:/tool/ruff/line-length": frozenset({"/ruff/line_length"}),
    "key:/tool/ruff/src": frozenset(
        {"source_layout", "additional_source_roots", "/pytest/test_paths"}
    ),
    "key:/tool/ruff/extend-exclude": frozenset({"/ruff/extend_exclude"}),
    "key:/tool/ruff/extend-include": frozenset({"/ruff/extend_include"}),
    "key:/tool/ruff/lint/select": frozenset(),
    "key:/tool/ruff/lint/ignore": frozenset(),
    "key:/tool/ruff/lint/extend-select": frozenset({"/ruff/extend_select"}),
    "key:/tool/ruff/lint/extend-ignore": frozenset({"/ruff/extend_ignore"}),
    "table:/tool/ruff/lint/per-file-ignores": frozenset(),
    "table:/tool/ruff/format": frozenset(),
}

# `when_any` has no "non-empty" operator and a contribution cannot render "no
# unit", so 1.12 renders the additive keys unconditionally where 1.11 emitted
# them only when non-empty. That is the whole approved rendered-surface delta.
_ADDITIVE_ROOT_KEYS = frozenset({"extend-include"})
_ADDITIVE_LINT_KEYS = frozenset({"extend-select", "extend-ignore"})

_SATURATED_OVERRIDES: JsonObject = {
    "python_version": "3.13",
    "source_layout": "flat",
    "ruff": {
        "line_length": 88,
        "extend_exclude": ["vendor"],
        "extend_include": ["*.pyi"],
        "extend_select": ["ANN"],
        "extend_ignore": ["ANN401"],
    },
    "pytest": {"test_paths": ["qa/unit"]},
}


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
                    "id": "ruff-unit",
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


def _selects_ruff(scope: str) -> bool:
    pointer = scope.split(":", 1)[1]
    return pointer == "/tool/ruff" or pointer.startswith("/tool/ruff/")


def _ruff_declarations(root: Path, config: JsonObject) -> list[ContributionDeclaration]:
    return [
        declaration
        for declaration in _payload(root).manifest.contributions
        if declaration.target.original == "pyproject.toml"
        and declaration.adapter is AdapterKind.TOML
        and _selects_ruff(declaration.scope)
        and declaration.materializes(config)
    ]


def _compose_toml(fragments: Sequence[str]) -> str:
    """Fold rendered fragments into one document, merging repeated table headers.

    Each key-scope fragment carries its own `[tool.ruff]` header, so plain
    concatenation would redefine the table and fail the parser. Grouping by
    header is also what makes the two payloads comparable at all: the 1.11
    monolith and the 1.12 unit set reduce to the same document shape.
    """
    grouped: dict[str, list[str]] = {}
    for fragment in fragments:
        header = ""
        for line in fragment.splitlines():
            if not line.strip():
                continue
            if line.startswith("["):
                header = line
                grouped.setdefault(header, [])
                continue
            grouped.setdefault(header, []).append(line)
    sections: list[str] = []
    for header, lines in grouped.items():
        body = "".join(f"{line}\n" for line in lines)
        sections.append(f"{header}\n{body}\n" if header else body)
    return "".join(sections)


def _ruff_source(root: Path, config: JsonObject) -> str:
    return _compose_toml(
        [
            _render(root, declaration.scope, config)
            for declaration in _ruff_declarations(root, config)
        ]
    )


def _ruff_value(root: Path, config: JsonObject) -> JsonObject:
    document = tomllib.loads(_ruff_source(root, config))
    return cast("JsonObject", cast("JsonObject", document["tool"])["ruff"])


def _without_empty_additive(value: JsonObject) -> JsonObject:
    """Drop the additive keys 1.12 renders unconditionally and 1.11 omits when empty."""
    result: JsonObject = {
        key: item for key, item in value.items() if not (key in _ADDITIVE_ROOT_KEYS and item == [])
    }
    lint = result.get("lint")
    if isinstance(lint, dict):
        result["lint"] = {
            key: item
            for key, item in cast("JsonObject", lint).items()
            if not (key in _ADDITIVE_LINT_KEYS and item == [])
        }
    return result


def _write_consumer(repo: Path, *, ruff_table: str = "", plugin: bool = True) -> None:
    """Materialize issue #99's shape: consumer metadata plus a Ruff plugin table.

    The `[project]` table is not decoration: without it the package's own
    consumer-state validation (issue #109) refuses the adoption before ownership
    is ever classified, and the conflict under test would never be reached.
    """
    repo.mkdir(parents=True, exist_ok=True)
    sections = [
        '[project]\nname = "example-package"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n'
    ]
    if ruff_table:
        sections.append(ruff_table.rstrip("\n") + "\n")
    if plugin:
        sections.append(_PLUGIN_TABLE)
    (repo / "pyproject.toml").write_text("\n".join(sections), encoding="utf-8")


def _plan(repo: Path, payload: InstalledPayload) -> ReconciliationPlan:
    return plan_reconciliation(PlannerRequest(repo, resolution_request((payload,)), (payload,)))


def _immutable_calls(repo: Path) -> JsonValue:
    document = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tool = cast("JsonObject", document["tool"])
    ruff = cast("JsonObject", tool["ruff"])
    lint = cast("JsonObject", ruff["lint"])
    bugbear = cast("JsonObject", lint["flake8-bugbear"])
    return bugbear["extend-immutable-calls"]


# ---------------------------------------------------------------------------
# Negative controls: these PASS today and must keep passing.
# ---------------------------------------------------------------------------


def test_python_tooling_1_12__issue_99__predecessor_conflicts_on_the_whole_table(
    tmp_path: Path,
) -> None:
    """CONTROL: 1.11 owns `[tool.ruff]` wholesale, so the plugin table blocks adoption.

    This is the reported reproduction. It must keep failing on 1.11 forever: the
    successor earns its version by changing ownership, not by relaxing a released
    payload.
    """
    _require_payload(_V111)
    repo = tmp_path / "consumer"
    _write_consumer(repo)
    payload = _payload(_V111)

    plan = _plan(repo, payload)

    conflicts = [finding for finding in plan.findings if finding.code == "CP-CONSUMER-CONFLICT"]
    assert not plan.applicable
    assert [finding.identity for finding in conflicts] == [_RUFF_TABLE_SCOPE]
    assert conflicts[0].governing_options is not None
    assert set(conflicts[0].governing_options) == _ISSUE_99_GOVERNING


def test_python_tooling_1_12__released_options__cannot_express_the_allow_list() -> None:
    """CONTROL: no 1.11 option renders a plugin sub-table; only global suppression is reachable.

    This is the T19.2 evidence. The conflict hint tells the consumer to "set a
    governing option so the package reproduces the repository value"; these
    assertions are the proof that no such option exists, which is what makes the
    documented remedy unreachable rather than merely inconvenient.
    """
    _require_payload(_V111)
    schema = load_option_schema(_V111, _payload(_V111).manifest)
    properties = cast("JsonObject", schema.document["properties"])
    ruff_properties = cast("JsonObject", cast("JsonObject", properties["ruff"])["properties"])

    assert set(ruff_properties) == {
        "line_length",
        "extend_exclude",
        "extend_include",
        "extend_select",
        "extend_ignore",
    }

    saturated = _render(_V111, _RUFF_TABLE_SCOPE, _options(_V111, **_SATURATED_OVERRIDES))
    assert "flake8-bugbear" not in saturated
    assert "extend-immutable-calls" not in saturated

    # The only response the released options can express is strictly weaker than
    # the targeted allow-list: B008 goes off for the whole repository.
    suppressed = tomllib.loads(
        _render(_V111, _RUFF_TABLE_SCOPE, _options(_V111, ruff={"extend_ignore": ["B008"]}))
    )
    tool = cast("JsonObject", suppressed["tool"])
    ruff = cast("JsonObject", tool["ruff"])
    lint = cast("JsonObject", ruff["lint"])
    assert lint["extend-ignore"] == ["B008"]


def test_python_tooling_1_12__released_predecessor__keeps_its_exact_bytes() -> None:
    """CONTROL: 1.11 stays byte-immutable and keeps declaring the table it owned."""
    _require_payload(_V111)
    manifest = load_payload_manifest(_V111 / "payload.toml")
    scopes = {declaration.scope for declaration in manifest.contributions}

    assert _RUFF_TABLE_SCOPE in scopes
    assert validate_payload_integrity(_V111, manifest).aggregate_digest.value == _V111_AGGREGATE


# ---------------------------------------------------------------------------
# The 1.12 contract: every row below fails on the unauthored payload.
# ---------------------------------------------------------------------------


def test_python_tooling_1_12__ruff_ownership__declares_one_unit_per_rendered_key() -> None:
    """1.12 owns Ruff at leaf granularity, matching BasedPyright and pytest."""
    _require_payload(_V112)
    config = _options(_V112)
    declarations = {
        declaration.scope: declaration for declaration in _ruff_declarations(_V112, config)
    }

    assert _RUFF_TABLE_SCOPE not in declarations
    assert set(declarations) == set(_RUFF_UNIT_GOVERNANCE)
    for scope, governing in _RUFF_UNIT_GOVERNANCE.items():
        declaration = declarations[scope]
        assert declaration.policy is ArtifactPolicy.MANAGED, scope
        assert declaration.adapter is AdapterKind.TOML, scope
        assert declaration.governing_options is not None, scope
        if governing:
            assert set(declaration.governing_options) >= governing, scope
        else:
            assert declaration.governing_options == [], scope


@pytest.mark.parametrize(
    ("label", "overrides"),
    [("defaults", cast("JsonObject", {})), ("saturated", _SATURATED_OVERRIDES)],
)
def test_python_tooling_1_12__unit_set__reproduces_the_predecessor_table(
    label: str,
    overrides: JsonObject,
) -> None:
    """Ownership granularity changes; the effective Ruff configuration does not.

    The only sanctioned difference is the additive keys 1.12 must now render
    unconditionally, because a contribution cannot conditionally render nothing.
    """
    _require_payload(_V111)
    _require_payload(_V112)

    successor = _ruff_value(_V112, _options(_V112, **overrides))
    predecessor = _ruff_value(_V111, _options(_V111, **overrides))

    assert _without_empty_additive(successor) == predecessor, label


def test_python_tooling_1_12__plugin_subtable__survives_fresh_adoption(tmp_path: Path) -> None:
    """TC-T19-001: the reported adoption plans cleanly instead of conflicting."""
    _require_payload(_V112)
    repo = tmp_path / "consumer"
    _write_consumer(repo)
    payload = _payload(_V112)

    plan = _plan(repo, payload)

    assert plan.applicable, plan.findings
    assert not [
        finding
        for finding in plan.findings
        if finding.code == "CP-CONSUMER-CONFLICT" and _selects_ruff(finding.identity)
    ]


def test_python_tooling_1_12__reconcile__preserves_the_plugin_table_and_converges(
    tmp_path: Path,
) -> None:
    """TC-T19-001: apply keeps the consumer's allow-list byte-for-byte and is a fixed point."""
    _require_payload(_V112)
    repo = tmp_path / "consumer"
    _write_consumer(repo)
    payload = _payload(_V112)
    request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    control = repo / ".standards"
    control.mkdir()
    (control / "lock.toml").write_bytes(render_lock(request.resolution.previous_lock))
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings

    assert apply_reconciliation(ApplyRequest(request, plan)).success

    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert _PLUGIN_TABLE in text
    assert _immutable_calls(repo) == _PLUGIN_CALLS
    # No split-file workaround: the whole Ruff configuration stays in the one file
    # the package manages, so the two-authority hazard the report documented never
    # arises. Ruff reads exactly one configuration file and `ruff.toml` wins.
    assert not (repo / "ruff.toml").exists()
    second_request = PlannerRequest(
        repo,
        resolution_request((payload,), previous_lock=plan.next_lock),
        (payload,),
    )
    second = plan_reconciliation(second_request)
    result = apply_reconciliation(ApplyRequest(second_request, second))
    assert second.applicable, second.findings
    assert result.success
    assert result.applied_action_ids == ()
    assert (repo / "pyproject.toml").read_text(encoding="utf-8") == text


def _ruff(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the real linter as the oracle, from this repository's locked toolchain.

    PYTHONPATH and VIRTUAL_ENV are stripped for the same reason the 1.11 suite
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


def _resolved_immutable_calls(output: str) -> list[str]:
    """Read Ruff's own resolved allow-list out of `--show-settings`.

    Ruff's resolved settings are the only witness that a preserved consumer table
    is *effective* rather than merely present in the file; it is also the evidence
    the reporter used to validate their `ruff.toml` workaround.
    """
    lines = output.splitlines()
    for index, line in enumerate(lines):
        prefix = "linter.flake8_bugbear.extend_immutable_calls = "
        if not line.startswith(prefix):
            continue
        remainder = line.removeprefix(prefix)
        if remainder != "[":
            return []
        entries: list[str] = []
        for entry in lines[index + 1 :]:
            if entry.strip() == "]":
                break
            entries.append(entry.strip().rstrip(","))
        return entries
    raise AssertionError("ruff reported no flake8-bugbear allow-list setting")


# The B008 probe is deliberately NOT a Typer call. Ruff 0.15 exempts
# `typer.Option`/`typer.Argument` from B008 by default, so the report's own
# 13-finding reproduction no longer fires on the toolchain this package pins
# (`ruff>=0.14.11`, resolved 0.15.15 here). What the acceptance actually needs is
# preserved: the consumer's reported allow-list must reach Ruff's resolved
# settings, and B008 must stay globally active rather than being suppressed to
# make the reconcile pass. `datetime.datetime.now` is a call Ruff still flags, so
# it witnesses the second half without inventing consumer configuration.
_TYPER_MODULE = '''"""Typer CLI using the documented Option/Argument default idiom."""

import datetime

import typer

app = typer.Typer()


@app.command()
def greet(
    name: str = typer.Option("world"),
    count: int = typer.Argument(1),
    when: datetime.datetime = datetime.datetime.now(),
) -> None:
    """Greet NAME COUNT times."""
    for _ in range(count):
        print(name, when)
'''


@pytest.mark.parametrize("keep_allow_list", [True, False])
def test_python_tooling_1_12__b008_gate__stays_active_while_the_allow_list_is_preserved(
    tmp_path: Path,
    keep_allow_list: bool,
) -> None:
    """TC-T19-001: the preserved allow-list reaches Ruff and B008 is never suppressed.

    The acceptance is behavioral, so the oracle is the real linter reading the
    real managed file. Both arms prove "without global suppression": B008 stays
    selected and reports the probe. The arms differ only in whether the reported
    consumer table survived reconciliation into Ruff's resolved settings.
    """
    _require_payload(_V112)
    repo = tmp_path / "consumer"
    _write_consumer(
        repo,
        ruff_table=_ruff_source(_V112, _options(_V112)),
        plugin=keep_allow_list,
    )
    (repo / "src").mkdir()
    (repo / "src/example_cli.py").write_text(_TYPER_MODULE, encoding="utf-8")

    settings = _ruff(repo, "--show-settings", "src/example_cli.py")
    findings = _ruff(repo, "--output-format", "concise", "src")

    output = findings.stdout + findings.stderr
    if settings.returncode != 0:
        pytest.fail(f"ruff could not resolve the managed settings:\n{settings.stderr}")
    assert _resolved_immutable_calls(settings.stdout) == (_PLUGIN_CALLS if keep_allow_list else [])
    # No global suppression and no source churn: B008 is live, the module carries
    # no per-line escape, and the Typer defaults are never what fails the gate.
    assert "B008" in output, output
    assert "datetime.datetime.now" in output, output
    assert "typer.Option" not in output, output
    assert "noqa" not in _TYPER_MODULE


def _locked_ruff_table() -> CentralLock:
    """Seed the lock exactly as a reconciled 1.11 consumer holds it.

    The applied-package record is not optional bookkeeping: a lock that owns
    units for a package but records no exact applied version is inferred-only
    evidence, and the planner fails that closed (SPEC-VAIC FR-021) before it ever
    classifies ownership. Recording 1.11 is also what makes this the real upgrade
    path rather than a fresh adoption wearing a lock.
    """
    predecessor = _payload(_V111)
    base = previous_lock(
        {
            "path": "pyproject.toml",
            "adapter": "toml",
            "scope": _RUFF_TABLE_SCOPE,
            "owners": ["python-tooling"],
            "versions": {"python-tooling": "1.11"},
            "provenance": "provider",
            "policy": "managed",
            "semantic_digest": f"sha256:{'1' * 64}",
            "content_digest": f"sha256:{'2' * 64}",
            "mode": None,
            "created_container": False,
        }
    )
    applied = AppliedPackage.model_validate(
        {
            "requested": "latest",
            "resolved": "1.11",
            "selection": "stable",
            "payload_digest": predecessor.integrity.aggregate_digest.value,
            "effective_config_digest": semantic_digest(_options(_V111)).value,
        }
    )
    return base.model_copy(update={"standards": {"python-tooling": applied}})


def test_python_tooling_1_12__upgrade_from_1_11__relocks_without_lock_inconsistency(
    tmp_path: Path,
) -> None:
    """The declared 1.11->1.12 edge is what lets the owned table split into keys.

    Without it the locked `table:/tool/ruff` overlaps every new key scope and the
    planner refuses the upgrade with CP-LOCK-INCONSISTENT, so the migration edge
    is part of the contract rather than bookkeeping.
    """
    _require_payload(_V111)
    _require_payload(_V112)
    repo = tmp_path / "consumer"
    _write_consumer(
        repo,
        ruff_table=_render(_V111, _RUFF_TABLE_SCOPE, _options(_V111)),
        plugin=False,
    )
    control = repo / ".standards"
    control.mkdir()
    # The package-configuration transform rewrites the persisted desired config,
    # so an upgrade plan requires the real file rather than a synthesized one.
    (control / "config.toml").write_text(
        '[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n\n'
        '[standards.python-tooling]\nenabled = true\nversion = "latest"\n',
        encoding="utf-8",
    )
    # Both payloads are installed, as they are in a real distribution: the
    # configuration transform authenticates the applied version against the
    # predecessor's own aggregate digest and refuses to run on inference alone.
    predecessor = _payload(_V111)
    payload = _payload(_V112)
    resolution = replace(
        resolution_request((predecessor, payload), previous_lock=_locked_ruff_table()),
        transition_paths=frozenset(
            {
                DeclaredTransition(
                    "python-tooling",
                    PackageVersion("1.11"),
                    PackageVersion("1.12"),
                )
            }
        ),
    )

    plan = plan_reconciliation(PlannerRequest(repo, resolution, (predecessor, payload)))

    assert plan.applicable, plan.findings
    locked = {
        artifact.scope
        for artifact in plan.next_lock.artifacts
        if artifact.path.original == "pyproject.toml"
    }
    assert _RUFF_TABLE_SCOPE not in locked
    assert set(_RUFF_UNIT_GOVERNANCE) <= locked
    edge = next(
        migration
        for migration in payload.manifest.migrations
        if migration.id == "python-tooling-1-11-to-1-12"
    )
    config = _options(_V112)
    assert edge.from_endpoint.value == "package:1.11"
    assert {
        f"contribution:{declaration.id}" for declaration in _ruff_declarations(_V112, config)
    } <= set(edge.affected)
