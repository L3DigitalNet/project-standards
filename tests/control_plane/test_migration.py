from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from project_standards.control_plane.migration import (
    LegacyClaim,
    LegacyDisposition,
    MigratedPackage,
    MigrationFinding,
    MigrationReport,
    migration_report_to_jsonable,
    render_migration_report,
)


def _digest(character: str = "a") -> str:
    return f"sha256:{character * 64}"


def _package(**overrides: object) -> MigratedPackage:
    values: dict[str, object] = {
        "standard_id": "demo",
        "version": "1.2",
        "selector": "latest",
        "config": {"credential_env": "DEMO_TOKEN", "mode": "strict"},
        "recognized_settings": ["/markdown/frontmatter", "/spec"],
    }
    values.update(overrides)
    return MigratedPackage.model_validate(values)


def _claim(**overrides: object) -> LegacyClaim:
    values: dict[str, object] = {
        "signature_id": "legacy-demo-config",
        "target": ".project-standards.yml",
        "observed_digest": _digest(),
        "ownership": "managed",
        "disposition": "adopt",
    }
    values.update(overrides)
    return LegacyClaim.model_validate(values)


def _finding(**overrides: object) -> MigrationFinding:
    values: dict[str, object] = {
        "code": "CP-MIGRATION-REVIEW",
        "severity": "warning",
        "path": ".project-standards.yml",
        "identity": "legacy-demo-config",
    }
    values.update(overrides)
    return MigrationFinding.model_validate(values)


def test_migration_report_normalizes_package_claim_and_finding_order() -> None:
    first = MigrationReport(
        schema_version="1.0",
        package=_package(recognized_settings=["/spec", "/markdown/frontmatter"]),
        claims=(
            _claim(
                signature_id="legacy-workflow",
                target=".github/workflows/standards.yml",
                observed_digest=_digest("b"),
                ownership="create-only",
                disposition="preserve",
            ),
            _claim(),
        ),
        findings=(_finding(identity="zeta"), _finding(identity="alpha")),
    )
    second = MigrationReport(
        schema_version="1.0",
        package=_package(),
        claims=tuple(reversed(first.claims)),
        findings=tuple(reversed(first.findings)),
    )

    assert first == second
    assert first.package.recognized_settings == ("/markdown/frontmatter", "/spec")
    assert isinstance(first.claims, tuple)
    assert isinstance(first.findings, tuple)
    assert json.dumps(first.model_dump(mode="json"), sort_keys=True) == json.dumps(
        second.model_dump(mode="json"), sort_keys=True
    )


@pytest.mark.parametrize(
    "settings",
    [
        ["markdown.frontmatter"],
        ["/markdown/~2frontmatter"],
        ["/spec", "/spec"],
    ],
)
def test_migrated_package_rejects_noncanonical_or_duplicate_json_pointers(
    settings: list[str],
) -> None:
    with pytest.raises(ValidationError, match="recognized setting"):
        _package(recognized_settings=settings)


@pytest.mark.parametrize("target", ["../outside", "/absolute", "config\\legacy.yml"])
def test_legacy_claim_rejects_unsafe_targets(target: str) -> None:
    with pytest.raises(ValidationError, match="safe canonical relative POSIX path"):
        _claim(target=target)


def test_migration_report_rejects_duplicate_signature_target_claims() -> None:
    with pytest.raises(ValidationError, match="duplicate legacy claim"):
        MigrationReport(
            schema_version="1.0",
            package=_package(),
            claims=(_claim(), _claim(disposition="remove")),
        )


@pytest.mark.parametrize(
    ("ownership", "disposition"),
    [
        ("managed", LegacyDisposition.ADOPT),
        ("create-only", LegacyDisposition.PRESERVE),
        ("shared", LegacyDisposition.PRESERVE),
        ("consumer-owned", LegacyDisposition.PRESERVE),
        ("package-lock", LegacyDisposition.IMPORT_LOCK),
    ],
)
def test_legacy_claim_accepts_every_ownership_disposition_class(
    ownership: str,
    disposition: LegacyDisposition,
) -> None:
    claim = _claim(ownership=ownership, disposition=disposition.value)

    assert claim.ownership == ownership
    assert claim.disposition is disposition


@pytest.mark.parametrize(
    ("ownership", "disposition"),
    [
        ("create-only", "remove"),
        ("consumer-owned", "adopt"),
        ("package-lock", "preserve"),
    ],
)
def test_legacy_claim_rejects_destructive_or_unimported_ownership_dispositions(
    ownership: str,
    disposition: str,
) -> None:
    with pytest.raises(ValidationError, match="disposition is not valid"):
        _claim(ownership=ownership, disposition=disposition)


def test_migrated_package_rejects_secret_shaped_config_without_echoing_value() -> None:
    secret = "do-not-echo-this-value"

    with pytest.raises(ValidationError) as caught:
        _package(config={"api_token": secret})

    assert secret not in str(caught.value)


def test_public_serializers_omit_configured_values_and_source_content() -> None:
    report = MigrationReport(
        schema_version="1.0",
        package=_package(),
        claims=(_claim(),),
        findings=(_finding(),),
    )

    jsonable = migration_report_to_jsonable(report)
    serialized = json.dumps(jsonable, sort_keys=True)
    human = render_migration_report(report)

    for hidden in ("DEMO_TOKEN", "strict", "source content"):
        assert hidden not in serialized
        assert hidden not in human
    for visible in (
        "demo",
        "legacy-demo-config",
        ".project-standards.yml",
        _digest(),
        "adopt",
    ):
        assert visible in serialized
        assert visible in human
