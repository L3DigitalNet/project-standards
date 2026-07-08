from __future__ import annotations

from project_standards.standard_manifest import (
    AdoptionMode,
    LifecycleStatus,
    ProviderKind,
    StandardManifestError,
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
