from __future__ import annotations

import base64
import hashlib
import json
import tomllib
from pathlib import Path
from typing import cast

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

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.5"
_SUCCESSOR = _FAMILY / "versions/1.6"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.6"
_PREDECESSOR_DIGEST = "sha256:4acf48a8dbb987088700c558128d9b180718e1001a8bc7d4364950b0f05dc3da"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "payload.toml",
        "providers/agent_handoff.py",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)


def _successor() -> InstalledPayload:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    return InstalledPayload(_SUCCESSOR, manifest, validate_payload_integrity(_SUCCESSOR, manifest))


def _shape_messages(path: str, text: str, repo: Path) -> list[str]:
    """Return one payload's AH-SHAPE prose for a single document snapshot.

    Only the named document is snapshotted, so unrelated required-path findings
    stay out of the assertion without needing a full adopted repository.
    """
    payload = _successor()
    schema = load_option_schema(payload.root, payload.manifest)
    content = text.encode()
    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="agent-handoff",
            version=payload.manifest.payload.version,
            provider_id="validate",
            operation=ProviderOperation.VALIDATE,
            effective_config=schema.resolve_options(cast("JsonObject", {})),
            snapshots={
                path: {
                    "kind": "regular",
                    "content_digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
                    "content_base64": base64.b64encode(content).decode("ascii"),
                    "mode": None,
                }
            },
        )
    )
    return [
        finding.message
        for finding in result.findings
        if finding.code == "AH-SHAPE" and finding.path == path
    ]


def test_agent_handoff_1_6__provider_schemas__bind_the_successor_identity() -> None:
    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )

    assert provider_input["properties"]["version"]["const"] == "1.6"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.6"


def test_agent_handoff_1_6__activated_successor__is_complete_default_and_immutable() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()

    successor_manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    successor_integrity = validate_payload_integrity(_SUCCESSOR, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert successor_manifest.payload.version.value == "1.6"
    assert successor_manifest.payload.availability.value == "consumer"
    assert indexed["1.6"].digest == successor_integrity.aggregate_digest
    assert any(
        migration.to_endpoint.value == "package:1.6" for migration in successor_manifest.migrations
    )

    # Catalog 5 selects 1.6 and keeps 1.5 advertised as retained. The dogfood lock
    # tracks this default only after the release-prep reconcile, so that assertion
    # stays in tests/agent_handoff/test_packaging.py rather than here.
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "agent-handoff"
    }
    successor_version = successor_manifest.payload.version.value
    assert roles[successor_version] == "default"
    assert roles[predecessor_manifest.payload.version.value] == "retained"


def test_agent_handoff_1_6__payload_projection__matches_complete_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def test_agent_handoff_1_6__session_caps__scan_table_rows_only(tmp_path: Path) -> None:
    prose = " ".join(f"word{index}" for index in range(80))
    text = (
        "# Sessions\n\n"
        "| Date | Summary | Evidence |\n| --- | --- | --- |\n"
        "| 2026-07-09 | Short row. | commit |\n\n"
        f"{prose}\n\n"
        f"- {prose}\n\n"
        "```text\n"
        f"| 2026-07-09 | {prose} | commit |\n"
        "```\n"
    )

    assert len(prose) > 220
    messages = _shape_messages("docs/handoff/sessions/2026-07.md", text, tmp_path)

    assert "row is too long" not in messages
    assert "headline is too long" not in messages
    # Prose length outside a table belongs to the paragraph rule, which still owns it.
    assert "document contains an overlong paragraph" in messages


def test_agent_handoff_1_6__session_caps__still_report_oversized_rows(tmp_path: Path) -> None:
    headline = " ".join(f"word{index}" for index in range(21))
    text = f"| 2026-07-09 | {headline} | {'x' * 221} |\n"

    messages = _shape_messages("docs/handoff/sessions/2026-07.md", text, tmp_path)

    assert messages == ["row is too long", "headline is too long"]


def test_agent_handoff_1_6__entry_findings__name_each_oversized_section(tmp_path: Path) -> None:
    text = (
        "## Quick Reference\n\n- Short.\n\n"
        "## 1. First\n\n" + ("x" * 1300) + "\n\n"
        "## 2. Second\n\n- Short enough.\n\n"
        "## 3. Third\n\n" + ("y" * 1400) + "\n"
    )

    messages = _shape_messages("docs/handoff/conventions.md", text, tmp_path)

    assert [message for message in messages if "entry has" in message] == [
        "section 1. First entry has 1300 chars; max 1200",
        "section 3. Third entry has 1400 chars; max 1200",
    ]


def test_agent_handoff_1_6__entry_size__excludes_fenced_examples(tmp_path: Path) -> None:
    fence = "```bash\n" + ("uv run project-standards validate\n" * 60) + "```\n"
    text = (
        "## Quick Reference\n\n- Short.\n\n"
        "## 1. Worked example\n\n- Run the gate before closeout.\n\n"
        f"{fence}\n- Review the diff.\n"
    )

    assert len(fence) > 1200
    assert _shape_messages("docs/handoff/conventions.md", text, tmp_path) == []
