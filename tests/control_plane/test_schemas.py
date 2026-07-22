from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from project_standards.control_plane.schemas import (
    MutationPlanSchema,
    control_plane_schema_bytes,
    control_plane_schema_documents,
    generate_control_plane_schemas,
)
from project_standards.package_contract.cli import run_standards

_SCHEMA_NAMES = {
    "consumer-catalog.schema.json",
    "consumer-config.schema.json",
    "consumer-lock.schema.json",
    "migration-report.schema.json",
    "mutation-plan.schema.json",
    "provider-input.schema.json",
    "reconciliation-plan.schema.json",
}


def _assert_closed_objects(value: object) -> None:
    if isinstance(value, dict):
        table = cast(dict[str, object], value)
        if table.get("type") == "object" and "properties" in table:
            assert table.get("additionalProperties") is False
        for nested in table.values():
            _assert_closed_objects(nested)
    elif isinstance(value, list):
        for nested in cast(list[object], value):
            _assert_closed_objects(nested)


def test_control_plane_schema_set_is_deterministic_and_structurally_closed() -> None:
    documents = control_plane_schema_documents()

    assert set(documents) == _SCHEMA_NAMES
    assert control_plane_schema_bytes() == control_plane_schema_bytes()
    for name, document in documents.items():
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert cast(str, document["$id"]).endswith(f"/{name}")
        _assert_closed_objects(document)
        assert json.loads(control_plane_schema_bytes()[name]) == document


@pytest.mark.parametrize(
    ("schema_name", "central_lock_definition"),
    [
        ("consumer-lock.schema.json", None),
        ("reconciliation-plan.schema.json", "CentralLock"),
    ],
)
def test_lock_bearing_schemas_define_closed_create_only_absences(
    schema_name: str,
    central_lock_definition: str | None,
) -> None:
    schema = control_plane_schema_documents()[schema_name]
    definitions = cast("dict[str, object]", schema["$defs"])
    absence = cast("dict[str, object]", definitions["CreateOnlyAbsence"])
    properties = cast("dict[str, object]", absence["properties"])
    central_lock = (
        schema
        if central_lock_definition is None
        else cast("dict[str, object]", definitions[central_lock_definition])
    )
    lock_properties = cast("dict[str, object]", central_lock["properties"])

    assert absence["additionalProperties"] is False
    assert set(properties) == {
        "path",
        "adapter",
        "scope",
        "owners",
        "shared_identity",
        "versions",
        "provenance",
    }
    assert set(cast("list[str]", absence["required"])) == {
        "path",
        "adapter",
        "scope",
        "owners",
        "versions",
        "provenance",
    }
    assert lock_properties["create_only_absences"] == {
        "items": {"$ref": "#/$defs/CreateOnlyAbsence"},
        "title": "Create Only Absences",
        "type": "array",
    }


def test_migration_claim_schema_exposes_optional_intent_pointer() -> None:
    schema = control_plane_schema_documents()["migration-report.schema.json"]
    definitions = cast("dict[str, object]", schema["$defs"])
    claim = cast("dict[str, object]", definitions["LegacyClaim"])
    properties = cast("dict[str, object]", claim["properties"])

    assert "intent_pointer" in properties
    assert "intent_pointer" not in cast("list[str]", claim["required"])
    assert claim["description"] == (
        "Identify recognized package history or one target-bound consumer-owned "
        "preservation claim without retaining source bytes."
    )
    disposition = cast("dict[str, object]", definitions["LegacyDisposition"])
    assert disposition["description"] == (
        "Propose treatment for recognized package history or an authorized "
        "consumer-owned preservation."
    )


def test_control_plane_schema_generator_writes_checks_and_detects_drift(
    tmp_path: Path,
) -> None:
    assert generate_control_plane_schemas(tmp_path, check=False)
    output = tmp_path / "src/project_standards/schemas"
    assert {path.name for path in output.iterdir()} == _SCHEMA_NAMES
    assert generate_control_plane_schemas(tmp_path, check=True)

    changed = output / "consumer-config.schema.json"
    changed.write_text("{}\n", encoding="utf-8")

    assert not generate_control_plane_schemas(tmp_path, check=True)


def test_existing_schema_cli_checks_all_ten_schemas_for_drift(tmp_path: Path) -> None:
    assert run_standards(["generate-package-schemas", "--root", str(tmp_path)]) == 0
    output = tmp_path / "src/project_standards/schemas"
    assert len(list(output.glob("*.schema.json"))) == 10

    changed = output / "provider-input.schema.json"
    original = changed.read_bytes()
    changed.write_text("{}\n", encoding="utf-8")
    assert run_standards(["generate-package-schemas", "--root", str(tmp_path), "--check"]) == 1

    changed.write_bytes(original)
    assert run_standards(["generate-package-schemas", "--root", str(tmp_path), "--check"]) == 0


def test_mutation_plan_carries_complete_bytes_and_snapshot_preconditions() -> None:
    content = b"---\ntitle: Fixed\n---\n"
    digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    plan = MutationPlanSchema.model_validate(
        {
            "schema_version": "1.0",
            "standard_id": "markdown-frontmatter",
            "version": "1.2",
            "diagnostics": [
                {
                    "code": "FM-AUTHORING-WARNING",
                    "severity": "warning",
                    "path": "docs/example.md",
                    "message": "unknown key was preserved",
                    "refusal": False,
                }
            ],
            "actions": [
                {
                    "kind": "update",
                    "target": "docs/example.md",
                    "adapter": "whole-file",
                    "scope": "$file",
                    "summary": "format frontmatter and repair its document id",
                    "precondition_digest": f"sha256:{'a' * 64}",
                    "content_digest": digest,
                    "content_base64": base64.b64encode(content).decode("ascii"),
                    "mode": "0644",
                }
            ],
        }
    )

    assert plan.actions[0].content_bytes == content
    assert plan.diagnostics[0].path.original == "docs/example.md"

    invalid = plan.model_dump(mode="json")
    del cast("list[dict[str, object]]", invalid["actions"])[0]["precondition_digest"]
    with pytest.raises(ValidationError):
        MutationPlanSchema.model_validate(invalid)


@pytest.mark.parametrize(
    "override",
    [
        {"kind": "preserve"},
        {"scope": "file"},
        {"content_base64": "not base64", "content_digest": f"sha256:{'a' * 64}"},
        {"content_base64": None},
    ],
)
def test_mutation_plan_rejects_incomplete_or_unbounded_actions(
    override: dict[str, object],
) -> None:
    content = b"replacement\n"
    action: dict[str, object] = {
        "kind": "update",
        "target": "README.md",
        "adapter": "whole-file",
        "scope": "$file",
        "summary": "update one document",
        "precondition_digest": f"sha256:{'b' * 64}",
        "content_digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "content_base64": base64.b64encode(content).decode("ascii"),
    }
    action.update(override)

    with pytest.raises(ValidationError):
        MutationPlanSchema.model_validate(
            {
                "schema_version": "1.0",
                "standard_id": "markdown-frontmatter",
                "version": "1.2",
                "actions": [action],
            }
        )


def test_reconciliation_finding_schema_is_additively_enriched_at_1_1() -> None:
    document = control_plane_schema_documents()["reconciliation-plan.schema.json"]
    definitions = cast("dict[str, object]", document["$defs"])
    finding = cast("dict[str, object]", definitions["PublicFindingSchema"])
    properties = cast("dict[str, object]", finding["properties"])

    for field in ("expected", "actual", "expected_digest", "actual_digest", "governing_options"):
        assert field in properties
    assert set(cast("list[str]", finding["required"])) == {
        "code",
        "severity",
        "standard_id",
        "version",
        "path",
        "identity",
        "message",
        "hint",
    }
    top_properties = cast("dict[str, object]", document["properties"])
    schema_version = cast("dict[str, object]", top_properties["schema_version"])
    assert schema_version["const"] == "1.1"
