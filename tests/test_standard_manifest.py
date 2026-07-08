from __future__ import annotations

import pytest
from pydantic import ValidationError

from project_standards.standard_manifest import (
    AdoptionMode,
    LifecycleStatus,
    ProviderKind,
    StandardManifestError,
    StandardTable,
    VersionsTable,
)


def test_enums_have_contract_values() -> None:
    assert {m.value for m in AdoptionMode} == {
        "validator",
        "copy-adopt",
        "cli",
        "reference-only",
        "none",
    }
    assert {m.value for m in LifecycleStatus} == {
        "draft",
        "review",
        "active",
        "deprecated",
        "archived",
        "superseded",
    }
    assert {m.value for m in ProviderKind} == {
        "python",
        "command",
        "workflow",
        "documentation-only",
    }


def test_error_is_valueerror() -> None:
    assert issubclass(StandardManifestError, ValueError)


def test_standard_table_valid() -> None:
    t = StandardTable.model_validate(
        {
            "id": "markdown-tooling",
            "name": "Markdown Tooling",
            "status": "active",
            "summary": "Formatting and structural linting.",
            "adoption": "copy-adopt",
        }
    )
    assert t.id == "markdown-tooling"
    assert t.adoption is AdoptionMode.COPY_ADOPT


@pytest.mark.parametrize(
    "override",
    [
        {"id": "Not_Kebab"},  # bad id syntax
        {"adoption": "package-tooling"},  # not in enum
        {"status": "retired"},  # not in enum
        {"requires": "adr"},  # stray reserved key
    ],
)
def test_standard_table_rejects(override: dict[str, str]) -> None:
    base = {
        "id": "markdown-tooling",
        "name": "Markdown Tooling",
        "status": "active",
        "summary": "x",
        "adoption": "copy-adopt",
    }
    with pytest.raises(ValidationError):
        StandardTable.model_validate({**base, **override})


def test_versions_latest_must_be_in_supported() -> None:
    VersionsTable.model_validate({"supported": ["1.0", "1.1"], "latest": "1.1"})
    VersionsTable.model_validate({"supported": [], "latest": ""})
    with pytest.raises(ValidationError):
        VersionsTable.model_validate({"supported": ["1.0"], "latest": "2.0"})
