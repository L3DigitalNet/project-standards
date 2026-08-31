"""Contract for the Project Specification 1.8 caller-runner-selection successor.

1.7 added `runner-labels` to the SELF-HOSTED workflow resource. 1.8 makes the same
selection reachable from `caller` mode (issue #132) through the additive
`runner_labels` option, which the managed caller emits as a `runner-labels`
JSON-array string for the reusable workflow to re-read with `fromJSON`.

The load-bearing property is that an empty selection — the default — is
*byte-identical* to the 1.7 render rather than merely equivalent: reconciliation
compares bytes, so anything else would rewrite every consumer's managed caller on
upgrade for a feature it did not select.

The catalog-role row below was deferred to release prep and landed with the 5.17.0
activation, which is the first commit permitted to advance catalogs/5.toml. Root-
workflow parity was never 1.8's: `runner_labels` reaches caller mode only, so 1.8
supersedes none of the self-hosted bytes this repository renders.

1.8 retired to `retained` long ago. The family-navigation assertion this module
used to carry was dropped at the 1.11 cut, because it re-pinned which sibling
currently holds `default` and so went red on each later cut rather than on a
regression of its own; `test_catalog_roles.py` owns that invariant catalog-derived.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import yaml

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-spec"
_PREDECESSOR = _FAMILY / "versions/1.7"
_SUCCESSOR = _FAMILY / "versions/1.8"
_PROJECTION = _ROOT / "src/project_standards/payloads/project-spec/1.8"
_PREDECESSOR_DIGEST = "sha256:2d012e3de7699dc44bdf4ee8605cf350caca3ba05b0c490b8ff795ce5014df8f"
_WORKFLOW_RESOURCE = "resources/self-host-validate-specs.yml"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "config.schema.json",
        "payload.toml",
        "providers/project_spec.py",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_LABELS = ["self-hosted", "linux", "x64", "l3digital-private"]


def _render(root: Path, config: JsonObject) -> bytes:
    manifest = load_payload_manifest(root / "payload.toml")
    payload = InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="project-spec",
            version=manifest.payload.version,
            provider_id="render-workflow",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={},
        )
    )
    assert result.content is not None
    return result.content


def _options(root: Path, selected: Mapping[str, object] | None = None) -> JsonObject:
    manifest = load_payload_manifest(root / "payload.toml")
    schema = load_option_schema(root, manifest)
    return schema.resolve_options(selected or {})  # type: ignore[arg-type]


def test_project_spec_1_8__successor__preserves_1_7_and_indexes_complete_payload() -> None:
    """Only the option surface, provider, identity prose, and schema bytes change."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in payload_tree(_PREDECESSOR)
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.8"
    assert indexed["1.8"].digest == integrity.aggregate_digest
    # An additive option with an empty default moves nothing between artifact
    # targets, so 1.8 declares no package-to-package edge — only the legacy route.
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-8"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.8"]


def test_project_spec_1_8__self_hosted_resource__is_unchanged_from_1_7() -> None:
    """1.8 touches only the caller path; the 1.7 workflow bytes carry forward."""
    successor = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()
    assert successor == (_PREDECESSOR / _WORKFLOW_RESOURCE).read_bytes()

    text = successor.decode("utf-8")
    assert "runner-labels:" in text
    assert "runs-on: ${{ inputs.runner-labels && fromJSON(inputs.runner-labels) ||" in text


def test_project_spec_1_8__option_surface__adds_only_a_closed_runner_selection() -> None:
    """`runner_labels` is typed, closed, and defaults to the empty selection."""
    predecessor_defaults = _options(_PREDECESSOR)
    successor_defaults = _options(_SUCCESSOR)

    assert successor_defaults == {**predecessor_defaults, "runner_labels": []}
    assert _options(_SUCCESSOR, {"runner_labels": _LABELS})["runner_labels"] == _LABELS


def test_project_spec_1_8__empty_selection__renders_the_1_7_caller_bytes() -> None:
    """The default render must be byte-identical, not merely equivalent."""
    predecessor = _render(_PREDECESSOR, _options(_PREDECESSOR))
    assert _render(_SUCCESSOR, _options(_SUCCESSOR)) == predecessor
    assert _render(_SUCCESSOR, _options(_SUCCESSOR, {"runner_labels": []})) == predecessor
    assert b"runner-labels" not in predecessor

    # The `ci = false` caller shape is equally protected.
    disabled = _options(_PREDECESSOR, {"ci": False})
    assert _render(_SUCCESSOR, _options(_SUCCESSOR, {"ci": False})) == _render(
        _PREDECESSOR, disabled
    )


def test_project_spec_1_8__selected_labels__reach_the_caller_as_json() -> None:
    """The caller passes the labels as a JSON string the callee can `fromJSON`."""
    rendered = _render(_SUCCESSOR, _options(_SUCCESSOR, {"runner_labels": _LABELS}))
    with_block = yaml.safe_load(rendered)["jobs"]["validate-specs"]["with"]

    assert isinstance(with_block["runner-labels"], str)
    assert json.loads(with_block["runner-labels"]) == _LABELS
    assert with_block["standards-ref"] == "v5"
    assert with_block["strict-lint"] is True


def test_project_spec_1_8__self_hosted_mode__ignores_the_caller_option() -> None:
    """A self-hosted repository receives the static resource, labels or not."""
    expected = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()
    assert _render(_SUCCESSOR, _options(_SUCCESSOR, {"workflow_mode": "self-hosted"})) == expected
    assert (
        _render(
            _SUCCESSOR,
            _options(_SUCCESSOR, {"workflow_mode": "self-hosted", "runner_labels": _LABELS}),
        )
        == expected
    )


def test_project_spec_1_8__identity_documents_and_schemas__name_the_successor() -> None:
    """Every self-identifying string names 1.8.

    Unlike the 1.7 cut, a blanket "predecessor absent" assertion would be wrong
    here: `adopt.md` deliberately narrates what 1.7 did, because that is what a
    reader upgrading from it needs. Only the identity positions are pinned.
    """
    identities = {
        "README.md": ("- **Package version:** `1.8`",),
        "adopt.md": (
            "# Adopt Project Specification 1.8",
            "project-standards standards enable project-spec --version 1.8",
            'version = "1.8"',
            "independently of package version `1.8`",
        ),
        "agent-summary.md": (
            "# Project Specification 1.8 summary",
            "Package version `1.8`",
            "`project-standards standards enable project-spec --version 1.8`",
        ),
    }
    for relative, expected in identities.items():
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        for fragment in expected:
            assert fragment in document, (relative, fragment)
        assert "project-spec --version 1.7" not in document
        assert "Package version:** `1.7`" not in document

    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )
    assert provider_input["properties"]["version"]["const"] == "1.8"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.8"


def test_project_spec_1_8__payload_projection__matches_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def test_project_spec_1_8__catalog_role__stays_advertised_and_retained() -> None:
    """1.8 and the predecessors it shipped behind stay selectable by exact pin.

    Its `default` row landed with the 5.17.0 activation and moved on at the next
    cut; a released role only ever advances to `retained`, never back, and never
    to withdrawn (ADR 0024). Which version currently holds `default` is asserted
    catalog-derived in test_catalog_roles.py, not re-pinned here.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "project-spec"
    }

    assert roles["1.8"] == "retained"
    assert roles["1.7"] == "retained"
    assert roles["1.6"] == "retained"
