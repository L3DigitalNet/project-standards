from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.control_plane.planner_helpers import resolution_request

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/cli-documentation"
_PAYLOAD_1_3 = _FAMILY / "versions/1.3"
_PAYLOAD_1_4 = _FAMILY / "versions/1.4"
_TOML_FENCE = re.compile(r"^```toml[ \t]*\n(?P<body>.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
_RELEASED_DIGESTS = {
    "1.1": "sha256:a6aa0b4a9e0f2247a0795dac3073a55e72d9047581493e1326eeb42d43442445",
    "1.2": "sha256:edde1a4011314a9b05f372731a8d50e3b5a0663d39369089256d442430e4943c",
    "1.3": "sha256:2c15f700fd343327b675295579220572fea9f2735386da5aa266d38839a7f9c4",
}
_PLANNED_SUCCESSOR_GUIDES = (
    _ROOT / "standards/python-tooling/versions/1.9/adopt.md",
    _ROOT / "standards/markdown-tooling/versions/1.9/adopt.md",
    _ROOT / "standards/agent-handoff/versions/1.5/adopt.md",
    _PAYLOAD_1_4 / "adopt.md",
)


def _payload_at(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _write_lock(repo: Path, payload: InstalledPayload) -> None:
    control = repo / ".standards"
    control.mkdir(parents=True)
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))


def _fences(path: Path) -> tuple[str, ...]:
    return tuple(match.group("body") for match in _TOML_FENCE.finditer(path.read_text()))


def test_toml_corpus__successor_copyable_fences__all_parse() -> None:
    documents = sorted(_PAYLOAD_1_4.rglob("*.md"))
    documents.extend(path for path in _PLANNED_SUCCESSOR_GUIDES if path.exists())

    assert documents
    for document in documents:
        for body in _fences(document):
            assert "= null" not in body, document
            tomllib.loads(body)


def test_toml_corpus__released_cli_docs__keeps_known_null_limitations_and_digests() -> None:
    for version, expected_digest in _RELEASED_DIGESTS.items():
        root = _FAMILY / f"versions/{version}"
        payload = _payload_at(root)
        invalid: list[str] = []
        for document in sorted(root.rglob("*.md")):
            for body in _fences(document):
                try:
                    tomllib.loads(body)
                except tomllib.TOMLDecodeError:
                    invalid.append(body)

        assert payload.integrity.aggregate_digest.value == expected_digest
        assert len(invalid) == 1
        assert "command_name = null" in invalid[0]


def test_usage_index_schema__defaults_and_cardinality__remain_single_path() -> None:
    payload = _payload_at(_PAYLOAD_1_4)
    schema = load_option_schema(_PAYLOAD_1_4, payload.manifest)

    assert schema.resolve_options({})["usage_index_path"] is None
    assert (
        schema.resolve_options({"usage_index_path": "docs/script-docs/README.md"})[
            "usage_index_path"
        ]
        == "docs/script-docs/README.md"
    )
    with pytest.raises(PackageContractError, match="package options violate schema"):
        schema.resolve_options(
            {"usage_index_path": ["docs/one.md", "docs/two.md"]}  # type: ignore[dict-item]
        )

    assert [
        (extension.id, extension.option, extension.media_type)
        for extension in payload.manifest.extensions
        if extension.id == "usage-index"
    ] == [("usage-index", "usage_index_path", "text/markdown")]
    usage_outputs = [
        item.target.original
        for item in (*payload.manifest.artifacts, *payload.manifest.contributions)
        if item.target.original == "docs/usage.md"
    ]
    assert usage_outputs == ["docs/usage.md"]


def test_usage_renderer__absent_index__matches_1_3_bytes() -> None:
    payload = _payload_at(_PAYLOAD_1_4)
    config = load_option_schema(_PAYLOAD_1_4, payload.manifest).resolve_options({})
    result = invoke_provider(
        ProviderInvocation(
            repo=_ROOT,
            payload=payload,
            standard_id="cli-documentation",
            version=payload.manifest.payload.version,
            provider_id="render-usage",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={},
        )
    )

    assert result.effect is ProviderEffect.CONTENT
    assert result.content == (_PAYLOAD_1_3 / "templates/usage-doc.md").read_bytes()


def test_usage_index__fresh_custom_input__is_locked_and_linked(tmp_path: Path) -> None:
    payload = _payload_at(_PAYLOAD_1_4)
    repo = tmp_path / "consumer"
    index = repo / "docs/script-docs/README.md"
    index.parent.mkdir(parents=True)
    index.write_text("# CLI index\n", encoding="utf-8")
    _write_lock(repo, payload)
    resolution = resolution_request(
        (payload,),
        configs={"cli-documentation": {"usage_index_path": "docs/script-docs/README.md"}},
    )
    request = PlannerRequest(repo, resolution, (payload,))

    plan = plan_reconciliation(request)

    assert plan.applicable, plan.findings
    assert plan.next_lock.referenced_inputs[0].extension_id == "usage-index"
    assert plan.next_lock.referenced_inputs[0].path.original == "docs/script-docs/README.md"
    content = plan.proposed_content("docs/usage.md")
    assert content is not None
    assert b"[Multi-CLI usage index](script-docs/README.md)" in content
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    assert index.read_text(encoding="utf-8") == "# CLI index\n"


def test_usage_index__upgrade_and_path_switch__preserve_create_only_usage(
    tmp_path: Path,
) -> None:
    previous = _payload_at(_PAYLOAD_1_3)
    successor = _payload_at(_PAYLOAD_1_4)
    repo = tmp_path / "consumer"
    _write_lock(repo, previous)
    initial_resolution = resolution_request((previous,))
    initial_request = PlannerRequest(repo, initial_resolution, (previous,))
    initial = plan_reconciliation(initial_request)
    assert apply_reconciliation(ApplyRequest(initial_request, initial)).success
    usage = repo / "docs/usage.md"
    old_usage = usage.read_bytes()

    first_index = repo / "docs/script-docs/README.md"
    first_index.parent.mkdir(parents=True)
    first_index.write_text("# First index\n", encoding="utf-8")
    upgraded_resolution = resolution_request(
        (successor,),
        configs={"cli-documentation": {"usage_index_path": "docs/script-docs/README.md"}},
        previous_lock=initial.next_lock,
    )
    upgraded_request = PlannerRequest(repo, upgraded_resolution, (successor,))
    upgraded = plan_reconciliation(upgraded_request)
    assert upgraded.applicable, upgraded.findings
    assert any(
        action.kind is ActionKind.PRESERVE and action.target == "docs/usage.md"
        for action in upgraded.actions
    )
    assert apply_reconciliation(ApplyRequest(upgraded_request, upgraded)).success
    assert usage.read_bytes() == old_usage

    second_index = repo / "docs/other-index.md"
    second_index.write_text("# Second index\n", encoding="utf-8")
    switched_resolution = resolution_request(
        (successor,),
        configs={"cli-documentation": {"usage_index_path": "docs/other-index.md"}},
        previous_lock=upgraded.next_lock,
    )
    switched_request = PlannerRequest(repo, switched_resolution, (successor,))
    switched = plan_reconciliation(switched_request)

    assert switched.applicable, switched.findings
    assert [item.path.original for item in switched.next_lock.referenced_inputs] == [
        "docs/other-index.md"
    ]
    assert not any(action.kind is ActionKind.REMOVE for action in switched.actions)
    assert apply_reconciliation(ApplyRequest(switched_request, switched)).success
    assert usage.read_bytes() == old_usage

    removed_resolution = resolution_request(
        (successor,),
        previous_lock=switched.next_lock,
    )
    removed_request = PlannerRequest(repo, removed_resolution, (successor,))
    removed = plan_reconciliation(removed_request)

    assert removed.applicable, removed.findings
    assert removed.next_lock.referenced_inputs == []
    assert not any(action.kind is ActionKind.REMOVE for action in removed.actions)
    assert apply_reconciliation(ApplyRequest(removed_request, removed)).success
    assert usage.read_bytes() == old_usage


@pytest.mark.parametrize(
    ("case", "configured_path", "message"),
    [
        pytest.param("absolute", "/tmp/index.md", "repository-relative", id="absolute"),
        pytest.param("escaping", "../index.md", "repository-relative", id="escaping"),
        pytest.param("missing", "docs/missing.md", "does not exist", id="missing"),
        pytest.param("directory", "docs/index", "not a regular file", id="directory"),
        pytest.param("symlink", "docs/index.md", "cannot contain a symlink", id="symlink"),
        pytest.param(
            "owned-output",
            "docs/usage.md",
            "aliases a managed output",
            id="owned-output",
        ),
    ],
)
def test_usage_index_path__unsafe_shape__fails_closed(
    tmp_path: Path,
    case: str,
    configured_path: str,
    message: str,
) -> None:
    payload = _payload_at(_PAYLOAD_1_4)
    repo = tmp_path / "consumer"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    if case == "directory":
        (docs / "index").mkdir()
    elif case == "symlink":
        (docs / "real.md").write_text("# Real\n", encoding="utf-8")
        (docs / "index.md").symlink_to("real.md")
    elif case == "owned-output":
        (docs / "usage.md").write_text("# Existing usage\n", encoding="utf-8")
    _write_lock(repo, payload)
    resolution = resolution_request(
        (payload,),
        configs={"cli-documentation": {"usage_index_path": configured_path}},
    )
    request = PlannerRequest(repo, resolution, (payload,))

    with pytest.raises(ControlPlaneError, match=message):
        plan_reconciliation(request)


def test_cli_docs_1_4__family_registration__stays_retained_beside_1_3() -> None:
    family = tomllib.loads((_FAMILY / "standard.toml").read_text())
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text())

    assert "1.4" in {entry["version"] for entry in family["versions"]}
    entries = [entry for entry in catalog["packages"] if entry["id"] == "cli-documentation"]
    roles = {entry["version"]: entry["role"] for entry in entries}
    # Issue #72 advanced the default to the corrective 1.5 payload, so 1.4 joins
    # 1.3 as retained. A superseded payload is never withdrawn from the catalog.
    assert roles["1.4"] == "retained"
    assert roles["1.3"] == "retained"
