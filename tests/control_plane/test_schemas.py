from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from project_standards.control_plane.schemas import (
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
