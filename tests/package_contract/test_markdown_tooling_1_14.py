"""Contract for the Markdown Tooling 1.14 caller-runner-selection successor.

1.14 adds the optional `runner_labels` config key (issue #132) and emits it into
both managed callers as a `runner-labels` JSON-array string, which the reusable
workflows re-read with `fromJSON`. The load-bearing property is that an empty
selection — the default — is not merely equivalent but *byte-identical* to the
1.13 render: a consumer that sets nothing must see no reconciliation change, and
a hand-edited managed caller would otherwise be reported as CP-MODIFIED-MANAGED
drift. `test_markdown_tooling_1_14__empty_selection__renders_the_1_13_bytes`
holds that line by rendering both payloads and comparing raw bytes.

The catalog-role and family-navigation rows below were deferred to release prep
and landed with the 5.17.0 activation: the catalogs/5.toml advance batches with
the other cuts of the release, so asserting it at cut time would have pinned work
that commit was not allowed to do. Root-workflow parity stays with 1.13, which
still owns the bytes this repository's self-hosted workflows are rendered from —
`runner_labels` reaches caller mode only, so 1.14 supersedes nothing there.
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
_FAMILY = _ROOT / "standards/markdown-tooling"
_PREDECESSOR = _FAMILY / "versions/1.13"
_SUCCESSOR = _FAMILY / "versions/1.14"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-tooling/1.14"
_PREDECESSOR_DIGEST = "sha256:271cfbb5e5abde80439cb1f90b9d2eb55720fd52bff3d78f51057efa72aabfba"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "config.schema.json",
        "payload.toml",
        "providers/markdown_tooling.py",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_LABELS = ["self-hosted", "linux", "x64", "l3digital-private"]


def _render(root: Path, provider_id: str, config: JsonObject) -> bytes:
    manifest = load_payload_manifest(root / "payload.toml")
    payload = InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="markdown-tooling",
            version=manifest.payload.version,
            provider_id=provider_id,
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


def test_markdown_tooling_1_14__successor__preserves_1_13_and_indexes_complete_payload() -> None:
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
            successor_files[relative].stat().st_mode & 0o777 == predecessor.stat().st_mode & 0o777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.14"
    assert indexed["1.14"].digest == integrity.aggregate_digest
    # The 1.13 inbound edge set is retargeted, not extended: 1.14 re-renders nothing
    # for a 1.13 consumer that sets no labels, so there is no 1.13-to-1.14 edge.
    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        "package:1.7",
        "package:1.8",
        "package:1.9",
        "package:1.10",
        "package:1.11",
        "package:1.12",
        "legacy:v4-markdown-tooling",
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.14"


def test_markdown_tooling_1_14__option_surface__adds_only_a_closed_runner_selection() -> None:
    """`runner_labels` is typed, closed, and defaults to the empty selection."""
    predecessor_defaults = _options(_PREDECESSOR)
    successor_defaults = _options(_SUCCESSOR)

    assert successor_defaults == {**predecessor_defaults, "runner_labels": []}

    configured = _options(_SUCCESSOR, {"runner_labels": _LABELS})
    assert configured["runner_labels"] == _LABELS


def test_markdown_tooling_1_14__empty_selection__renders_the_1_13_bytes() -> None:
    """The default render must be byte-identical, not merely equivalent.

    Reconciliation compares bytes. Any drift here would rewrite every consumer's
    managed callers on upgrade for a feature they did not select. The matrix
    covers each caller shape the trigger and glob options can produce, because
    the new emission is appended to the same `with:` block those options build.
    """
    shapes: tuple[Mapping[str, object], ...] = (
        {},
        {"format": False, "ci": {"lint_caller": True, "format_caller": False}},
        {"lint": False, "ci": {"lint_caller": False, "format_caller": True}},
        {"lint": False, "format": False, "ci": {"lint_caller": False, "format_caller": False}},
        {"lint_generated_exclusions": False},
        {
            "markdown_globs": ["docs/**/*.md"],
            "config_globs": ["config/**/*.yaml"],
            "exclusions": [
                {
                    "glob": "docs/generated/**",
                    "applies_to": "both",
                    "reason": "Generated documentation is not formatter-owned.",
                }
            ],
        },
    )
    for provider_id in ("render-lint-caller", "render-format-caller"):
        for shape in shapes:
            predecessor = _render(_PREDECESSOR, provider_id, _options(_PREDECESSOR, shape))
            assert _render(_SUCCESSOR, provider_id, _options(_SUCCESSOR, shape)) == predecessor
            # An explicitly empty selection is the same omission as an absent key.
            explicit = _options(_SUCCESSOR, {**shape, "runner_labels": []})
            assert _render(_SUCCESSOR, provider_id, explicit) == predecessor
            assert b"runner-labels" not in predecessor


def test_markdown_tooling_1_14__selected_labels__reach_both_callers_as_json() -> None:
    """Both callers pass the labels as a JSON string the callee can `fromJSON`."""
    configured = _options(_SUCCESSOR, {"runner_labels": _LABELS})
    jobs = {"render-lint-caller": "lint-markdown", "render-format-caller": "format"}

    for provider_id, job in jobs.items():
        rendered = _render(_SUCCESSOR, provider_id, configured)
        with_block = yaml.safe_load(rendered)["jobs"][job]["with"]
        assert json.loads(with_block["runner-labels"]) == _LABELS
        # A YAML sequence would not survive the string-typed workflow_call input.
        assert isinstance(with_block["runner-labels"], str)
        # The pre-existing inputs keep their own serialization untouched.
        assert "globs" in with_block


def test_markdown_tooling_1_14__self_hosted_mode__ignores_the_caller_option() -> None:
    """Self-hosted repositories receive the static resource, labels or not."""
    self_hosted = _options(_SUCCESSOR, {"workflow_mode": "self-hosted"})
    with_labels = _options(_SUCCESSOR, {"workflow_mode": "self-hosted", "runner_labels": _LABELS})

    for provider_id, resource in (
        ("render-lint-caller", "resources/self-host-lint-markdown.yml"),
        ("render-format-caller", "resources/self-host-format.yml"),
    ):
        expected = (_SUCCESSOR / resource).read_bytes()
        assert _render(_SUCCESSOR, provider_id, self_hosted) == expected
        assert _render(_SUCCESSOR, provider_id, with_labels) == expected


def test_markdown_tooling_1_14__payload_projection__matches_successor() -> None:
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


def test_markdown_tooling_1_14__catalog_role__selects_the_successor_as_default() -> None:
    """Catalog 5 must actually select the successor these tests pin.

    The payload can be complete and valid while the catalog still selects its
    predecessor; only this row makes the successor the default a consumer on
    `version = "latest"` resolves to. Landed by the 5.17.0 activation, which is
    the first commit permitted to advance the catalog role.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-tooling"
    }

    assert roles["1.14"] == "retained"
    assert roles["1.13"] == "retained"
    assert roles["1.12"] == "retained"


def test_markdown_tooling_1_14__mutable_navigation__names_the_new_authority() -> None:
    """Family-level readers must resolve the same current payload as the index."""
    expected_links = {
        _FAMILY / "README.md": "versions/1.16/README.md",
        _FAMILY / "adopt.md": "versions/1.16/adopt.md",
        _FAMILY / "agent-summary.md": "versions/1.16/agent-summary.md",
    }
    for path, expected_link in expected_links.items():
        content = path.read_text(encoding="utf-8")
        assert expected_link in content
        assert "versions/1.14/" not in content
