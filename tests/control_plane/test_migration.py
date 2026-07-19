from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
import yaml
from pydantic import ValidationError

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_catalog,
    parse_config,
    parse_lock,
)
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import (
    InstalledCatalog,
    InstalledDistribution,
    InstalledPayload,
    ParsedToolRelease,
)
from project_standards.control_plane.executor import (
    ApplyRequest,
    apply_reconciliation,
    reconciliation_fingerprint,
)
from project_standards.control_plane.migration import (
    LegacyClaim,
    LegacyDisposition,
    LegacyMigrationPlan,
    MigratedPackage,
    MigrationFinding,
    MigrationReport,
    apply_legacy_migration,
    legacy_migration_content_fingerprint,
    migration_report_to_jsonable,
    plan_legacy_migration,
    render_migration_report,
)
from project_standards.control_plane.models import ConsumerCatalog, DesiredConfig
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.planner import VerificationRequest, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, ProviderResult
from project_standards.control_plane.state import StateKind, detect_control_plane_state
from project_standards.package_contract.paths import SafeRelativePath, Sha256Digest
from project_standards.package_contract.payload import (
    ContributionDeclaration,
    LegacySignatureDeclaration,
    LegacySignatureFormat,
    LegacySignatureKind,
    ProviderEffect,
    ProviderOperation,
)
from tests.control_plane.helpers import installed_distribution

_FULL_ALPHA = Path("tests/fixtures/package_contract/valid/full/standards/alpha/versions/2.0")
_LEGACY_CORPUS = Path("tests/fixtures/package_compatibility/legacy")


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


def test_legacy_claim_accepts_optional_canonical_intent_pointer() -> None:
    claim = _claim(
        ownership="consumer-owned",
        disposition="preserve",
        intent_pointer="/python_tooling/workflow_ownership",
    )
    report = MigrationReport(
        schema_version="1.0",
        package=_package(),
        claims=(claim,),
    )
    claims = cast(
        "list[dict[str, object]]",
        migration_report_to_jsonable(report)["claims"],
    )

    assert claim.intent_pointer == "/python_tooling/workflow_ownership"
    assert claims[0]["intent_pointer"] == claim.intent_pointer
    assert "/python_tooling/workflow_ownership" in render_migration_report(report)


def test_known_claim_json_shape_omits_absent_intent_pointer() -> None:
    report = MigrationReport(
        schema_version="1.0",
        package=_package(),
        claims=(_claim(),),
    )
    claims = cast(
        "list[dict[str, object]]",
        migration_report_to_jsonable(report)["claims"],
    )

    assert "intent_pointer" not in claims[0]


@pytest.mark.parametrize("pointer", ["relative", "/bad~2escape", "/trailing~"])
def test_legacy_claim_rejects_noncanonical_intent_pointer(pointer: str) -> None:
    with pytest.raises(ValidationError, match="intent_pointer"):
        _claim(intent_pointer=pointer)


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


def _legacy_repo(tmp_path: Path, yaml_text: str | None = None) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir(parents=True)
    (repo / ".project-standards.yml").write_text(
        yaml_text or "standards_version: v4\nalpha:\n  enabled: true\n",
        encoding="utf-8",
    )
    (repo / "legacy-alpha.md").write_bytes((_FULL_ALPHA / "legacy.md").read_bytes())
    extension = repo / "config/alpha-options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    return repo


def _tree(root: Path) -> dict[str, tuple[str, bytes]]:
    result: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("symlink", str(path.readlink()).encode())
        elif path.is_dir():
            result[relative] = ("directory", b"")
        else:
            result[relative] = ("file", path.read_bytes())
    return result


def _replace_alpha_signature_target(
    distribution: InstalledDistribution,
    target: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed = distribution.load_catalog("5")
    alpha = installed.payload_map[("alpha", "2.0")]
    signature = alpha.manifest.legacy_signatures[0].model_copy(
        update={"targets": [SafeRelativePath.parse(target)]}
    )
    manifest = alpha.manifest.model_copy(update={"legacy_signatures": [signature]})
    changed_alpha = InstalledPayload(alpha.root, manifest, alpha.integrity)
    changed = InstalledCatalog(
        installed.source,
        installed.families,
        tuple(changed_alpha if payload is alpha else payload for payload in installed.payloads),
    )
    original = InstalledDistribution.load_catalog

    def changed_catalog(
        self: InstalledDistribution,
        catalog: CatalogMajor | str,
        *,
        recorded_release: str | None = None,
    ) -> InstalledCatalog:
        if self is distribution:
            return changed
        return original(self, catalog, recorded_release=recorded_release)

    monkeypatch.setattr(InstalledDistribution, "load_catalog", changed_catalog)


class _FixtureDistribution:
    def __init__(
        self,
        installed: InstalledCatalog,
        catalog: ConsumerCatalog,
    ) -> None:
        self.tool_release = ParsedToolRelease("5.0.0")
        self._installed = installed
        self._catalog = catalog

    def load_catalog(
        self,
        _catalog: CatalogMajor | str,
        *,
        recorded_release: str | None = None,
    ) -> InstalledCatalog:
        assert recorded_release in {None, "5.0.0"}
        return self._installed

    def consumer_catalog(
        self,
        _catalog: CatalogMajor | str,
        *,
        installed: InstalledCatalog | None = None,
    ) -> ConsumerCatalog:
        assert installed is None or installed is self._installed
        return self._catalog


def _two_package_distribution(
    distribution: InstalledDistribution,
    *,
    reverse: bool,
) -> _FixtureDistribution:
    installed = distribution.load_catalog("5")
    alpha = installed.payload_map[("alpha", "2.0")]
    alpha_family = installed.family_map["alpha"]
    alpha_entry = next(
        entry
        for entry in installed.source.packages
        if entry.id == "alpha" and entry.version.value == "2.0"
    )
    omega_manifest = alpha.manifest.model_copy(
        update={"payload": alpha.manifest.payload.model_copy(update={"standard": "omega"})}
    )
    omega = InstalledPayload(alpha.root, omega_manifest, alpha.integrity)
    omega_family = alpha_family.model_copy(
        update={"standard": alpha_family.standard.model_copy(update={"id": "omega"})}
    )
    omega_entry = alpha_entry.model_copy(update={"id": "omega"})
    entries = (alpha_entry, omega_entry)
    payloads = (alpha, omega)
    families = (alpha_family, omega_family)
    if reverse:
        entries = tuple(reversed(entries))
        payloads = tuple(reversed(payloads))
        families = tuple(reversed(families))
    source = installed.source.model_copy(update={"packages": entries})
    changed = InstalledCatalog(source, families, payloads)
    standards = {
        standard_id: {
            "status": "active",
            "available": ["2.0"],
            "default": "2.0",
            "candidates": [],
            "versions": {
                "2.0": {
                    "channel": "stable",
                    "availability": "consumer",
                    "payload_digest": alpha.integrity.aggregate_digest.value,
                }
            },
        }
        for standard_id in ("alpha", "omega")
    }
    catalog = bind_catalog_digest(
        ConsumerCatalog.model_validate(
            {
                "project_standards": {
                    "schema_version": "1.0",
                    "catalog": "5",
                    "release": "5.0.0",
                    "digest": _digest(),
                },
                "standards": standards,
            }
        )
    )
    return _FixtureDistribution(changed, catalog)


_OWNER_TARGET = ".github/workflows/consumer-check.yml"
_OWNER_POINTER = "/alpha/workflow_ownership"
_OWNER_BYTES = b"name: Consumer check\n"
_OWNER_DIGEST = Sha256Digest(f"sha256:{hashlib.sha256(_OWNER_BYTES).hexdigest()}")


def _owner_resolution_distribution(
    base: InstalledDistribution,
    *,
    known: bool = False,
    materializes_target: bool = False,
    managed_target: bool = False,
) -> InstalledDistribution:
    installed = base.load_catalog("5")
    catalog = base.consumer_catalog("5", installed=installed)
    alpha = installed.payload_map[("alpha", "2.0")]
    schema_path = alpha.root / "config.schema.json"
    schema = cast("dict[str, object]", json.loads(schema_path.read_text(encoding="utf-8")))
    properties = cast("dict[str, object]", schema["properties"])
    properties["workflow_ownership"] = {
        "type": "string",
        "enum": ["managed", "consumer-owned"],
        "default": "managed",
    }
    schema_path.write_text(
        json.dumps(schema, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    signature = LegacySignatureDeclaration.model_validate(
        {
            "id": "legacy-alpha",
            "kind": "whole-file",
            "targets": [_OWNER_TARGET],
            "known_content_digests": [_OWNER_DIGEST.value if known else _digest("f")],
            "consumer_owned_intent_pointer": _OWNER_POINTER,
        }
    )
    contributions = list(alpha.manifest.contributions)
    if materializes_target or managed_target:
        contribution_values: dict[str, object] = {
            "id": "consumer-workflow",
            "target": _OWNER_TARGET,
            "adapter": "whole-file",
            "scope": "$file",
            "policy": "managed",
            "provider": "render-alpha",
        }
        if managed_target:
            contribution_values["when_any"] = [
                {"option": "workflow_ownership", "equals": "managed"}
            ]
        contributions.append(ContributionDeclaration.model_validate(contribution_values))
    manifest = alpha.manifest.model_copy(
        update={
            "contributions": contributions,
            "legacy_signatures": [signature],
        }
    )
    changed_alpha = InstalledPayload(alpha.root, manifest, alpha.integrity)
    changed = InstalledCatalog(
        installed.source,
        installed.families,
        tuple(changed_alpha if payload is alpha else payload for payload in installed.payloads),
    )
    return cast(
        InstalledDistribution,
        _FixtureDistribution(changed, catalog),
    )


def _owner_resolution_repo(tmp_path: Path, owner_value: object = "consumer-owned") -> Path:
    alpha: dict[str, object] = {"enabled": True}
    if owner_value is not _MISSING_OWNER_VALUE:
        alpha["workflow_ownership"] = owner_value
    repo = _legacy_repo(
        tmp_path,
        yaml.safe_dump(
            {"standards_version": "v4", "alpha": alpha},
            sort_keys=False,
        ),
    )
    workflow = repo / _OWNER_TARGET
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_bytes(_OWNER_BYTES)
    return repo


_MISSING_OWNER_VALUE = object()


def _install_owner_resolution_provider(
    monkeypatch: pytest.MonkeyPatch,
    *,
    claim_overrides: dict[str, object] | None = None,
    omit_claim: bool = False,
    recognize_pointer: bool = True,
) -> None:
    import project_standards.control_plane.providers as provider_module

    original = provider_module.invoke_provider

    def owner_resolution(invocation: ProviderInvocation) -> ProviderResult:
        if invocation.operation is not ProviderOperation.MIGRATE:
            return original(invocation)
        claim_values: dict[str, object] = {
            "signature_id": "legacy-alpha",
            "target": _OWNER_TARGET,
            "observed_digest": _OWNER_DIGEST.value,
            "ownership": "consumer-owned",
            "disposition": "preserve",
            "intent_pointer": _OWNER_POINTER,
        }
        if claim_overrides is not None:
            claim_values.update(claim_overrides)
        recognized = ["/alpha/enabled"]
        if recognize_pointer:
            recognized.append(_OWNER_POINTER)
        report = MigrationReport(
            schema_version="1.0",
            package=MigratedPackage.model_validate(
                {
                    "standard_id": "alpha",
                    "version": "2.0",
                    "selector": "latest",
                    "config": {
                        "extension_path": "config/alpha-options.toml",
                        "workflow_ownership": "consumer-owned",
                    },
                    "recognized_settings": recognized,
                }
            ),
            claims=() if omit_claim else (LegacyClaim.model_validate(claim_values),),
        )
        return ProviderResult(
            effect=ProviderEffect.MIGRATION_REPORT,
            migration_report=report,
        )

    monkeypatch.setattr(provider_module, "invoke_provider", owner_resolution)


def _finding_codes(plan: LegacyMigrationPlan) -> set[str]:
    return {finding.code for finding in plan.findings}


def _set_owner_mode(repo: Path, mode: str) -> None:
    config_path = repo / ".standards/config.toml"
    content = config_path.read_bytes()
    before = b'workflow_ownership = "consumer-owned"'
    after = f'workflow_ownership = "{mode}"'.encode()
    assert content.count(before) == 1
    config_path.write_bytes(content.replace(before, after))


def test_unknown_whole_file_relinquishment_requires_target_bound_raw_intent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = installed_distribution(tmp_path)
    distribution = _owner_resolution_distribution(base)
    repo = _owner_resolution_repo(tmp_path)
    _install_owner_resolution_provider(monkeypatch)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    assert "CP-MIGRATION-LEGACY-DIGEST" not in _finding_codes(plan)
    assert all(action.target != _OWNER_TARGET for action in plan.actions)
    assert all(unit.target != _OWNER_TARGET for unit in plan.reconciliation.units)
    assert all(target.target != _OWNER_TARGET for target in plan.reconciliation.targets)
    assert all(
        unit.path.original != _OWNER_TARGET for unit in plan.reconciliation.next_lock.artifacts
    )
    public_report = cast(
        "dict[str, object]",
        cast("list[object]", plan.to_jsonable()["reports"])[0],
    )
    public_claim = cast("list[dict[str, object]]", public_report["claims"])[0]
    assert public_claim["target"] == _OWNER_TARGET
    assert public_claim["observed_digest"] == _OWNER_DIGEST.value
    assert public_claim["intent_pointer"] == _OWNER_POINTER
    assert "not semantically validated" in render_migration_report(plan.reports[0])


@pytest.mark.parametrize(
    ("case", "owner_value", "claim_overrides", "recognize_pointer"),
    [
        ("missing-raw", _MISSING_OWNER_VALUE, None, True),
        ("false-raw", False, None, True),
        ("wrong-raw", "managed", None, True),
        ("unrecognized", "consumer-owned", None, False),
        (
            "wrong-pointer",
            "consumer-owned",
            {"intent_pointer": "/alpha/other_ownership"},
            True,
        ),
        (
            "wrong-target",
            "consumer-owned",
            {"target": ".github/workflows/other.yml"},
            True,
        ),
        (
            "wrong-digest",
            "consumer-owned",
            {"observed_digest": _digest("e")},
            True,
        ),
        (
            "managed",
            "consumer-owned",
            {"ownership": "managed", "disposition": "preserve"},
            True,
        ),
        (
            "destructive",
            "consumer-owned",
            {"ownership": "managed", "disposition": "remove"},
            True,
        ),
        (
            "shared",
            "consumer-owned",
            {"ownership": "shared", "disposition": "preserve"},
            True,
        ),
        (
            "package-lock",
            "consumer-owned",
            {"ownership": "package-lock", "disposition": "import-lock"},
            True,
        ),
    ],
)
def test_unknown_relinquishment_rejects_invalid_intent_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    owner_value: object,
    claim_overrides: dict[str, object] | None,
    recognize_pointer: bool,
) -> None:
    base = installed_distribution(tmp_path)
    distribution = _owner_resolution_distribution(base)
    repo = _owner_resolution_repo(tmp_path, owner_value)
    _install_owner_resolution_provider(
        monkeypatch,
        claim_overrides=claim_overrides,
        recognize_pointer=recognize_pointer,
    )

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable, case
    assert "CP-MIGRATION-LEGACY-DIGEST" in _finding_codes(plan)
    assert "CP-MIGRATION-OWNER-RESOLUTION" in _finding_codes(plan)


def test_unknown_signature_without_claim_retains_digest_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = installed_distribution(tmp_path)
    distribution = _owner_resolution_distribution(base)
    repo = _owner_resolution_repo(tmp_path)
    _install_owner_resolution_provider(monkeypatch, omit_claim=True)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert "CP-MIGRATION-LEGACY-DIGEST" in _finding_codes(plan)


def test_ordinary_claim_without_matching_observation_retains_digest_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.providers as provider_module

    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    (repo / "legacy-alpha.md").unlink()
    original = provider_module.invoke_provider

    def missing_observation(invocation: ProviderInvocation) -> ProviderResult:
        if invocation.operation is not ProviderOperation.MIGRATE:
            return original(invocation)
        return ProviderResult(
            effect=ProviderEffect.MIGRATION_REPORT,
            migration_report=MigrationReport(
                schema_version="1.0",
                package=MigratedPackage.model_validate(
                    {
                        "standard_id": "alpha",
                        "version": "2.0",
                        "selector": "latest",
                        "config": {"extension_path": "config/alpha-options.toml"},
                        "recognized_settings": ["/alpha/enabled"],
                    }
                ),
                claims=(
                    LegacyClaim.model_validate(
                        {
                            "signature_id": "legacy-alpha",
                            "target": "legacy-alpha.md",
                            "observed_digest": _digest("d"),
                            "ownership": "managed",
                            "disposition": "preserve",
                        }
                    ),
                ),
            ),
        )

    monkeypatch.setattr(provider_module, "invoke_provider", missing_observation)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert _finding_codes(plan) == {"CP-MIGRATION-LEGACY-DIGEST"}


def test_known_consumer_owned_claim_forbids_extraneous_intent_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = installed_distribution(tmp_path)
    distribution = _owner_resolution_distribution(base, known=True)
    repo = _owner_resolution_repo(tmp_path)
    _install_owner_resolution_provider(monkeypatch)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert "CP-MIGRATION-OWNER-RESOLUTION" in _finding_codes(plan)
    assert "CP-MIGRATION-LEGACY-DIGEST" not in _finding_codes(plan)


def test_owner_resolution_rejects_selected_payload_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = installed_distribution(tmp_path)
    distribution = _owner_resolution_distribution(base, materializes_target=True)
    repo = _owner_resolution_repo(tmp_path)
    _install_owner_resolution_provider(monkeypatch)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert "CP-MIGRATION-LEGACY-DIGEST" in _finding_codes(plan)
    assert "CP-MIGRATION-OWNER-RESOLUTION" in _finding_codes(plan)


def test_owner_resolution_rejects_adversarial_bounded_block_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = installed_distribution(tmp_path)
    distribution = _owner_resolution_distribution(base)
    installed = distribution.load_catalog("5")
    alpha = installed.payload_map[("alpha", "2.0")]
    signature = alpha.manifest.legacy_signatures[0].model_copy(
        update={
            "kind": LegacySignatureKind.BOUNDED_BLOCK,
            "format": LegacySignatureFormat.MARKDOWN,
            "begin": "<!-- owner begin -->",
            "end": "<!-- owner end -->",
        }
    )
    manifest = alpha.manifest.model_copy(update={"legacy_signatures": [signature]})
    changed_alpha = InstalledPayload(alpha.root, manifest, alpha.integrity)
    changed = InstalledCatalog(
        installed.source,
        installed.families,
        tuple(changed_alpha if payload is alpha else payload for payload in installed.payloads),
    )
    adversarial = cast(
        InstalledDistribution,
        _FixtureDistribution(changed, distribution.consumer_catalog("5")),
    )
    repo = _owner_resolution_repo(tmp_path)
    (repo / _OWNER_TARGET).write_bytes(
        b"before\n<!-- owner begin -->\nconsumer body\n<!-- owner end -->\nafter\n"
    )
    body = b"consumer body\n"
    body_digest = f"sha256:{hashlib.sha256(body).hexdigest()}"
    _install_owner_resolution_provider(
        monkeypatch,
        claim_overrides={"observed_digest": body_digest},
    )

    plan = plan_legacy_migration(repo, adversarial, "5")

    assert not plan.applicable
    assert {
        "CP-MIGRATION-LEGACY-DIGEST",
        "CP-MIGRATION-OWNER-RESOLUTION",
    }.issubset(_finding_codes(plan))


def test_owner_resolution_preserves_file_through_lifecycle_and_explicit_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = installed_distribution(tmp_path)
    consumer_distribution = _owner_resolution_distribution(base)
    managed_distribution = _owner_resolution_distribution(
        consumer_distribution,
        managed_target=True,
    )
    repo = _owner_resolution_repo(tmp_path)
    workflow = repo / _OWNER_TARGET
    original = workflow.read_bytes()
    _install_owner_resolution_provider(monkeypatch)

    migration = plan_legacy_migration(repo, consumer_distribution, "5")
    assert migration.applicable, migration.findings
    assert apply_legacy_migration(migration).success
    assert workflow.read_bytes() == original
    assert all(
        unit.path.original != _OWNER_TARGET
        for unit in parse_lock((repo / ".standards/lock.toml").read_bytes()).artifacts
    )

    fixed_request = build_planner_request(repo, consumer_distribution, frozenset())
    fixed = plan_reconciliation(fixed_request)
    assert fixed.applicable, fixed.findings
    assert all(action.target != _OWNER_TARGET for action in fixed.actions)
    assert apply_reconciliation(ApplyRequest(fixed_request, fixed)).success

    for enabled in (False, True):
        set_standard_enabled(repo, "alpha", enabled)
        request = build_planner_request(repo, consumer_distribution, frozenset())
        plan = plan_reconciliation(request)
        assert plan.applicable, plan.findings
        assert all(action.target != _OWNER_TARGET for action in plan.actions)
        assert apply_reconciliation(ApplyRequest(request, plan)).success
        assert workflow.read_bytes() == original
        assert all(
            unit.path.original != _OWNER_TARGET
            for unit in parse_lock((repo / ".standards/lock.toml").read_bytes()).artifacts
        )

    _set_owner_mode(repo, "managed")
    lock_before = (repo / ".standards/lock.toml").read_bytes()
    blocked_request = build_planner_request(repo, managed_distribution, frozenset())
    blocked = plan_reconciliation(blocked_request)
    assert not blocked.applicable
    assert "CP-CONSUMER-CONFLICT" in {finding.code for finding in blocked.findings}
    assert all(action.target != _OWNER_TARGET for action in blocked.actions)
    assert all(unit.target != _OWNER_TARGET for unit in blocked.units)
    assert workflow.read_bytes() == original
    assert (repo / ".standards/lock.toml").read_bytes() == lock_before

    backup = workflow.with_name("consumer-check.consumer-owned.yml")
    workflow.rename(backup)
    replacement_request = build_planner_request(repo, managed_distribution, frozenset())
    replacement = plan_reconciliation(replacement_request)
    assert replacement.applicable, replacement.findings
    assert any(
        action.kind is ActionKind.CREATE and action.target == _OWNER_TARGET
        for action in replacement.actions
    )
    assert any(unit.path.original == _OWNER_TARGET for unit in replacement.next_lock.artifacts)
    assert apply_reconciliation(ApplyRequest(replacement_request, replacement)).success
    assert backup.read_bytes() == original
    assert workflow.read_bytes() == b"[alpha]\nenabled = true\n"

    converged_request = build_planner_request(repo, managed_distribution, frozenset())
    converged = plan_reconciliation(converged_request)
    assert converged.applicable, converged.findings
    assert all(
        action.kind in {ActionKind.NOOP, ActionKind.PRESERVE} for action in converged.actions
    )


@pytest.mark.parametrize("mutation", ["bytes", "directory", "symlink"])
def test_owner_resolution_stale_plan_rejects_target_mutation_without_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    distribution = _owner_resolution_distribution(installed_distribution(tmp_path))
    repo = _owner_resolution_repo(tmp_path)
    workflow = repo / _OWNER_TARGET
    _install_owner_resolution_provider(monkeypatch)
    plan = plan_legacy_migration(repo, distribution, "5")
    assert plan.applicable, plan.findings

    workflow.unlink()
    if mutation == "bytes":
        workflow.write_bytes(b"changed after preview\n")
    elif mutation == "directory":
        workflow.mkdir()
    else:
        workflow.symlink_to(repo / "legacy-alpha.md")

    result = apply_legacy_migration(plan)

    assert not result.success
    assert result.error_code == "CP-STALE-PLAN"
    assert not (repo / ".standards").exists()
    assert (repo / ".project-standards.yml").is_file()


def test_legacy_migration_preview_is_complete_and_performs_no_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    before = _tree(repo)

    def deny_path_mutation(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("migration preview attempted a filesystem mutation")

    def deny_network(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("migration preview attempted network access")

    for method in ("write_bytes", "write_text", "mkdir", "rename", "replace", "chmod"):
        monkeypatch.setattr(Path, method, deny_path_mutation)
    monkeypatch.setattr(socket, "socket", deny_network)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert _tree(repo) == before
    assert plan.applicable
    assert [report.package.standard_id for report in plan.reports] == ["alpha"]
    assert plan.reports[0].package.recognized_settings == ("/alpha/enabled",)
    assert parse_config(plan.config_content) == plan.desired_config
    assert parse_catalog(plan.catalog_content) == plan.catalog
    assert plan.reconciliation.next_lock.project_standards.schema_version == "1.1"
    assert plan.lock_content.startswith(b'[project_standards]\nschema_version = "1.1"\n')
    assert parse_lock(plan.lock_content) == plan.reconciliation.next_lock
    assert [action.target for action in plan.legacy_removals] == [".project-standards.yml"]
    assert any(action.target == ".standards/alpha/config.toml" for action in plan.actions)
    assert plan.reconciliation.next_lock.referenced_inputs[0].path.original == (
        "config/alpha-options.toml"
    )


def test_apply_legacy_migration_publishes_unified_state_and_retires_legacy(
    tmp_path: Path,
) -> None:
    import project_standards.control_plane.migration as migration_module

    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    retained = repo / "notes.txt"
    retained.write_text("consumer-owned\n", encoding="utf-8")
    legacy_signature = (repo / "legacy-alpha.md").read_bytes()
    plan = plan_legacy_migration(repo, distribution, "5")

    apply = getattr(migration_module, "apply_legacy_migration", None)
    assert apply is not None, "migration apply boundary is not implemented"
    result = apply(plan)

    assert result.success
    assert result.error_code is None
    assert result.lock_written
    assert not (repo / ".project-standards.yml").exists()
    assert (repo / ".standards/config.toml").read_bytes() == plan.config_content
    assert (repo / ".standards/catalog.toml").read_bytes() == plan.catalog_content
    assert (repo / ".standards/lock.toml").read_bytes() == plan.lock_content
    for target in plan.reconciliation.targets:
        assert (repo / target.target).read_bytes() == target.content
    assert retained.read_text(encoding="utf-8") == "consumer-owned\n"
    assert (repo / "legacy-alpha.md").read_bytes() == legacy_signature
    assert not tuple(repo.rglob("*.tmp"))
    assert (
        detect_control_plane_state(
            repo,
            tool_release=distribution.tool_release.value,
        ).kind
        is StateKind.INITIALIZED
    )


def test_apply_legacy_migration_refuses_a_stale_preview_without_writing(
    tmp_path: Path,
) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    plan = plan_legacy_migration(repo, distribution, "5")
    (repo / ".project-standards.yml").write_text(
        "standards_version: v4\nalpha:\n  enabled: false\n",
        encoding="utf-8",
    )

    result = apply_legacy_migration(plan)

    assert not result.success
    assert result.error_code == "CP-STALE-PLAN"
    assert not (repo / ".standards").exists()
    assert (repo / ".project-standards.yml").exists()


def test_retirement_views_reject_unobserved_claim_target(tmp_path: Path) -> None:
    import project_standards.control_plane.migration as migration_module

    installed = installed_distribution(tmp_path).load_catalog("5")
    alpha = installed.payload_map[("alpha", "2.0")]
    target = SafeRelativePath.parse("missing.md")
    signature = LegacySignatureDeclaration.model_validate(
        {
            "id": "legacy-alpha",
            "kind": "bounded-block",
            "format": "markdown",
            "targets": [target.original],
            "begin": "<!-- BEGIN legacy alpha -->",
            "end": "<!-- END legacy alpha -->",
            "known_content_digests": [_digest()],
        }
    )
    payload = InstalledPayload(
        alpha.root,
        alpha.manifest.model_copy(update={"legacy_signatures": (signature,)}),
        alpha.integrity,
    )
    report = MigrationReport(
        schema_version="1.0",
        package=MigratedPackage.model_validate(
            {
                "standard_id": "alpha",
                "version": "2.0",
                "selector": "latest",
            }
        ),
        claims=(
            LegacyClaim.model_validate(
                {
                    "signature_id": signature.id,
                    "target": target.original,
                    "observed_digest": _digest(),
                    "ownership": "managed",
                    "disposition": "remove",
                }
            ),
        ),
    )

    with pytest.raises(ControlPlaneError, match="legacy claim targets an unobserved file"):
        migration_module._retirement_views(  # pyright: ignore[reportPrivateUsage]
            (report,),
            {("alpha", "2.0"): payload},
            {},
        )


def test_bounded_block_without_replacement_target_never_removes_whole_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.providers as provider_module

    base = installed_distribution(tmp_path)
    installed = base.load_catalog("5")
    alpha = installed.payload_map[("alpha", "2.0")]
    target = SafeRelativePath.parse("legacy-bounded.md")
    begin = "<!-- BEGIN legacy alpha -->"
    end = "<!-- END legacy alpha -->"
    body = b"managed body\n"
    body_digest = Sha256Digest(f"sha256:{hashlib.sha256(body).hexdigest()}")
    signature = LegacySignatureDeclaration.model_validate(
        {
            "id": "legacy-alpha",
            "kind": "bounded-block",
            "format": "markdown",
            "targets": [target.original],
            "begin": begin,
            "end": end,
            "known_content_digests": [body_digest.value],
        }
    )
    changed_alpha = InstalledPayload(
        alpha.root,
        alpha.manifest.model_copy(update={"legacy_signatures": (signature,)}),
        alpha.integrity,
    )
    changed = InstalledCatalog(
        installed.source,
        installed.families,
        tuple(changed_alpha if payload is alpha else payload for payload in installed.payloads),
    )
    distribution = cast(
        InstalledDistribution,
        _FixtureDistribution(changed, base.consumer_catalog("5")),
    )
    original_invoke = provider_module.invoke_provider

    def bounded_remove(invocation: ProviderInvocation) -> ProviderResult:
        if invocation.operation is not ProviderOperation.MIGRATE:
            return original_invoke(invocation)
        return ProviderResult(
            effect=ProviderEffect.MIGRATION_REPORT,
            migration_report=MigrationReport(
                schema_version="1.0",
                package=MigratedPackage.model_validate(
                    {
                        "standard_id": "alpha",
                        "version": "2.0",
                        "selector": "latest",
                        "config": {"extension_path": "config/alpha-options.toml"},
                        "recognized_settings": ["/alpha/enabled"],
                    }
                ),
                claims=(
                    LegacyClaim.model_validate(
                        {
                            "signature_id": signature.id,
                            "target": target.original,
                            "observed_digest": body_digest.value,
                            "ownership": "managed",
                            "disposition": "remove",
                        }
                    ),
                ),
            ),
        )

    monkeypatch.setattr(provider_module, "invoke_provider", bounded_remove)
    repo = _legacy_repo(tmp_path)
    legacy_path = repo / target.original
    surrounding = b"consumer before\nconsumer after\n"
    original = (
        b"consumer before\n" + begin.encode() + b"\n" + body + end.encode() + b"\nconsumer after\n"
    )
    legacy_path.write_bytes(original)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.planner.retired_content == ((target, surrounding),)
    assert legacy_path.read_bytes() == original
    assert "CP-MIGRATION-BOUNDED-ORPHAN" in _finding_codes(plan)
    assert not plan.applicable
    assert not any(
        action.kind is ActionKind.REMOVE
        and action.target == target.original
        and action.adapter == "whole-file"
        and action.scope == "$file"
        for action in plan.actions
    )


def test_migration_adopts_exact_managed_whole_file_contribution_before_provider_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.providers as provider_module

    base = installed_distribution(tmp_path)
    installed = base.load_catalog("5")
    alpha = installed.payload_map[("alpha", "2.0")]
    legacy_content = b"legacy = true\n"
    legacy_digest = Sha256Digest(f"sha256:{hashlib.sha256(legacy_content).hexdigest()}")
    contribution = ContributionDeclaration.model_validate(
        {
            "id": "legacy-rendered",
            "target": "legacy-rendered.toml",
            "adapter": "whole-file",
            "scope": "$file",
            "policy": "managed",
            "provider": "render-alpha",
        }
    )
    signature = alpha.manifest.legacy_signatures[0].model_copy(
        update={
            "targets": [SafeRelativePath.parse("legacy-rendered.toml")],
            "known_content_digests": [legacy_digest],
        }
    )
    manifest = alpha.manifest.model_copy(
        update={
            "contributions": [*alpha.manifest.contributions, contribution],
            "legacy_signatures": [signature],
        }
    )
    changed_alpha = InstalledPayload(alpha.root, manifest, alpha.integrity)
    changed = InstalledCatalog(
        installed.source,
        installed.families,
        tuple(changed_alpha if payload is alpha else payload for payload in installed.payloads),
    )
    distribution = cast(
        InstalledDistribution,
        _FixtureDistribution(changed, base.consumer_catalog("5")),
    )
    original = provider_module.invoke_provider

    def migration_claim(invocation: ProviderInvocation) -> ProviderResult:
        if invocation.operation is ProviderOperation.MIGRATE:
            return ProviderResult(
                effect=ProviderEffect.MIGRATION_REPORT,
                migration_report=MigrationReport(
                    schema_version="1.0",
                    package=MigratedPackage.model_validate(
                        {
                            "standard_id": "alpha",
                            "version": "2.0",
                            "selector": "latest",
                            "config": {"extension_path": "config/alpha-options.toml"},
                            "recognized_settings": ["/alpha/enabled"],
                        }
                    ),
                    claims=(
                        LegacyClaim.model_validate(
                            {
                                "signature_id": signature.id,
                                "target": "legacy-rendered.toml",
                                "observed_digest": legacy_digest.value,
                                "ownership": "managed",
                                "disposition": "adopt",
                            }
                        ),
                    ),
                ),
            )
        return original(invocation)

    monkeypatch.setattr(provider_module, "invoke_provider", migration_claim)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        "standards_version: v4\nalpha:\n  enabled: true\n",
        encoding="utf-8",
    )
    (repo / "legacy-rendered.toml").write_bytes(legacy_content)
    extension = repo / "config/alpha-options.toml"
    extension.parent.mkdir()
    extension.write_text("consumer = true\n", encoding="utf-8")

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    seeded = next(
        unit
        for unit in plan.planner.resolution.previous_lock.artifacts
        if unit.path.original == "legacy-rendered.toml"
    )
    assert seeded.adapter.value == "whole-file"
    assert seeded.semantic_digest == legacy_digest
    result = apply_legacy_migration(plan)
    assert result.success, result
    assert (repo / "legacy-rendered.toml").read_bytes() == b"[alpha]\nenabled = true\n"
    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


@pytest.mark.parametrize(
    ("adapter", "scope", "policy", "disposition", "known", "observed_character"),
    [
        ("jsonc", "key:/owned", "managed", "adopt", True, "a"),
        ("whole-file", "$file", "create-only", "adopt", True, "a"),
        ("whole-file", "$file", "managed", "preserve", True, "a"),
        ("whole-file", "$file", "managed", "adopt", False, "a"),
        ("whole-file", "$file", "managed", "adopt", True, "b"),
    ],
)
def test_migration_does_not_bridge_unsafe_whole_file_contribution_claims(
    tmp_path: Path,
    adapter: str,
    scope: str,
    policy: str,
    disposition: str,
    known: bool,
    observed_character: str,
) -> None:
    from project_standards.control_plane.migration import (
        _adopted_legacy_units,  # pyright: ignore[reportPrivateUsage]  # exact bridge boundary
        _ObservedSignature,  # pyright: ignore[reportPrivateUsage]  # exact bridge boundary
    )

    distribution = installed_distribution(tmp_path)
    alpha = distribution.load_catalog("5").payload_map[("alpha", "2.0")]
    target = SafeRelativePath.parse("legacy-rendered.toml")
    claim_digest = Sha256Digest(_digest("a"))
    observed_digest = Sha256Digest(_digest(observed_character))
    contribution = ContributionDeclaration.model_validate(
        {
            "id": "legacy-rendered",
            "target": target.original,
            "adapter": adapter,
            "scope": scope,
            "policy": policy,
            "provider": "render-alpha",
        }
    )
    signature = alpha.manifest.legacy_signatures[0].model_copy(
        update={"targets": [target], "known_content_digests": [claim_digest]}
    )
    payload = InstalledPayload(
        alpha.root,
        alpha.manifest.model_copy(
            update={
                "contributions": [*alpha.manifest.contributions, contribution],
                "legacy_signatures": [signature],
            }
        ),
        alpha.integrity,
    )
    report = MigrationReport(
        schema_version="1.0",
        package=MigratedPackage.model_validate(
            {
                "standard_id": "alpha",
                "version": "2.0",
                "selector": "latest",
                "config": {"extension_path": "config/alpha-options.toml"},
            }
        ),
        claims=(
            LegacyClaim.model_validate(
                {
                    "signature_id": signature.id,
                    "target": target.original,
                    "observed_digest": claim_digest.value,
                    "ownership": "managed",
                    "disposition": disposition,
                }
            ),
        ),
    )
    observed = _ObservedSignature(
        "alpha",
        signature.id,
        target,
        observed_digest,
        known,
        b"legacy",
    )

    units = _adopted_legacy_units(
        (report,),
        {observed.key: observed},
        {("alpha", "2.0"): payload},
    )

    assert units == ()


def test_apply_legacy_migration_refuses_nonapplicable_foreign_and_unbound_plans(
    tmp_path: Path,
) -> None:
    distribution = installed_distribution(tmp_path)
    blocked_repo = _legacy_repo(
        tmp_path / "blocked",
        "standards_version: v4\nalpha:\n  enabled: true\nunknown: true\n",
    )
    blocked = plan_legacy_migration(blocked_repo, distribution, "5")
    assert not blocked.applicable
    assert apply_legacy_migration(blocked).error_code == "CP-STALE-PLAN"
    assert not (blocked_repo / ".standards").exists()

    repo = _legacy_repo(tmp_path / "applicable")
    plan = plan_legacy_migration(repo, distribution, "5")
    foreign_repo = tmp_path / "foreign"
    foreign_repo.mkdir()
    foreign = replace(plan, repo=foreign_repo)
    assert apply_legacy_migration(foreign).error_code == "CP-STALE-PLAN"
    assert not (foreign_repo / ".standards").exists()

    unbound = replace(plan, planner=replace(plan.planner, payloads=()))
    assert apply_legacy_migration(unbound).error_code == "CP-STALE-PLAN"
    assert not (repo / ".standards").exists()

    (repo / ".standards").mkdir()
    tampered = replace(plan, config_content=plan.config_content + b"\n")
    assert apply_legacy_migration(tampered).error_code == "CP-STALE-PLAN"
    assert not (repo / ".standards/config.toml").exists()


def test_apply_legacy_migration_faults_preserve_recoverable_authority(
    tmp_path: Path,
) -> None:
    distribution = installed_distribution(tmp_path)

    def injected_fault(expected: tuple[str, str]):
        def fail(phase: str, identity: str) -> None:
            if (phase, identity) == expected:
                raise RuntimeError("injected migration fault")

        return fail

    cases = [
        ("before-staging", "$migration"),
        ("published", ".standards/.migration-lock.toml"),
        ("published", ".editorconfig"),
        ("published", ".standards/alpha/config.toml"),
        ("published", ".standards/generated.toml"),
        ("published", ".standards/config.toml"),
        ("published", ".standards/catalog.toml"),
        ("lock", ".standards/lock.toml"),
        ("published", ".standards/lock.toml"),
        ("remove", ".project-standards.yml"),
        ("removed", ".project-standards.yml"),
    ]

    for index, expected in enumerate(cases):
        repo = _legacy_repo(tmp_path / str(index))
        plan = plan_legacy_migration(repo, distribution, "5")

        result = apply_legacy_migration(plan, fault_hook=injected_fault(expected))

        assert not result.success, expected
        if expected[0] == "removed":
            assert not (repo / ".project-standards.yml").exists()
        else:
            assert (repo / ".project-standards.yml").exists(), expected
        state = detect_control_plane_state(
            repo,
            tool_release=distribution.tool_release.value,
        )
        if expected[0] == "removed":
            assert state.kind is StateKind.INITIALIZED
        elif expected[0] == "before-staging":
            assert state.kind is StateKind.LEGACY_ONLY
        else:
            assert state.kind in {StateKind.LEGACY_ONLY, StateKind.DUAL_AUTHORITY}
        recovery_plan = (
            plan_legacy_migration(repo, distribution, "5")
            if state.kind is StateKind.LEGACY_ONLY
            else plan
        )
        recovered = apply_legacy_migration(recovery_plan)
        assert recovered.success, (expected, recovered)
        assert not (repo / ".project-standards.yml").exists()


def test_apply_legacy_migration_verification_failure_keeps_legacy_authority(
    tmp_path: Path,
) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    plan = plan_legacy_migration(repo, distribution, "5")
    reconciliation = replace(
        plan.reconciliation,
        verification_requests=(VerificationRequest("alpha", "2.0", "verify-alpha"),),
    )
    fingerprint = reconciliation_fingerprint(reconciliation)
    plan = replace(
        plan,
        reconciliation=reconciliation,
        reconciliation_fingerprint=fingerprint,
        content_fingerprint=legacy_migration_content_fingerprint(
            plan.repo,
            fingerprint,
            plan.legacy_preconditions,
            plan.config_content,
            plan.catalog_content,
            plan.lock_content,
        ),
    )
    (repo / ".standards").mkdir()

    def fail_verification(phase: str, identity: str) -> None:
        if (phase, identity) == ("verify", "verify-alpha"):
            raise RuntimeError("injected verification fault")

    failed = apply_legacy_migration(plan, fault_hook=fail_verification)

    assert not failed.success
    assert failed.error_code == "CP-VERIFY"
    assert not (repo / ".standards/lock.toml").exists()
    assert (repo / ".project-standards.yml").exists()
    assert (
        detect_control_plane_state(
            repo,
            tool_release=distribution.tool_release.value,
        ).kind
        is StateKind.DUAL_AUTHORITY
    )

    def verified(_invocation: ProviderInvocation) -> ProviderResult:
        return ProviderResult(ProviderEffect.FINDINGS)

    recovered = apply_legacy_migration(plan, verification_runner=verified)

    assert recovered.success
    assert not (repo / ".project-standards.yml").exists()


def test_apply_legacy_migration_recovery_rejects_unsafe_legacy_replacement(
    tmp_path: Path,
) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    plan = plan_legacy_migration(repo, distribution, "5")

    def fail_after_lock(phase: str, identity: str) -> None:
        if (phase, identity) == ("published", ".standards/lock.toml"):
            raise RuntimeError("injected migration fault")

    failed = apply_legacy_migration(plan, fault_hook=fail_after_lock)
    assert not failed.success
    legacy = repo / ".project-standards.yml"
    legacy.unlink()
    outside = tmp_path / "outside.yml"
    outside.write_text("standards_version: v4\n", encoding="utf-8")
    legacy.symlink_to(outside)

    recovered = apply_legacy_migration(plan)

    assert not recovered.success
    assert recovered.error_code == "CP-STALE-PLAN"
    assert legacy.is_symlink()


def test_legacy_migration_is_deterministic_across_yaml_and_file_order(
    tmp_path: Path,
) -> None:
    distribution = installed_distribution(tmp_path)
    first = _legacy_repo(tmp_path / "first")
    second = _legacy_repo(
        tmp_path / "second",
        "# retained comment\nalpha:\n  enabled: true\nstandards_version: v4\n",
    )

    first_plan = plan_legacy_migration(first, distribution, "5")
    second_plan = plan_legacy_migration(second, distribution, "5")

    assert first_plan.config_content == second_plan.config_content
    assert first_plan.catalog_content == second_plan.catalog_content
    assert first_plan.lock_content == second_plan.lock_content
    assert first_plan.to_jsonable() == second_plan.to_jsonable()


def test_package_and_provider_discovery_order_do_not_change_plan_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.providers as provider_module

    base = installed_distribution(tmp_path)
    first_distribution = _two_package_distribution(base, reverse=False)
    second_distribution = _two_package_distribution(base, reverse=True)
    first = _legacy_repo(
        tmp_path / "first-order",
        "standards_version: v4\nalpha:\n  enabled: true\nomega:\n  enabled: true\n",
    )
    second = _legacy_repo(
        tmp_path / "second-order",
        "omega:\n  enabled: true\nalpha:\n  enabled: true\nstandards_version: v4\n",
    )
    original = provider_module.invoke_provider

    def package_aware(invocation: ProviderInvocation) -> ProviderResult:
        if invocation.operation is ProviderOperation.MIGRATE and invocation.standard_id == "omega":
            report = MigrationReport(
                schema_version="1.0",
                package=MigratedPackage.model_validate(
                    {
                        "standard_id": "omega",
                        "version": "2.0",
                        "selector": "latest",
                        "config": {"extension_path": "config/alpha-options.toml"},
                        "recognized_settings": ["/omega/enabled"],
                    }
                ),
                claims=(
                    LegacyClaim.model_validate(
                        {
                            "signature_id": "legacy-alpha",
                            "target": "legacy-alpha.md",
                            "observed_digest": (
                                "sha256:c9e8af84d208648598d673f039dea59091a9141a6150c3a2efbeb458689937ca"
                            ),
                            "ownership": "consumer-owned",
                            "disposition": "preserve",
                        }
                    ),
                ),
            )
            return ProviderResult(
                effect=ProviderEffect.MIGRATION_REPORT,
                migration_report=report,
            )
        return original(invocation)

    monkeypatch.setattr(provider_module, "invoke_provider", package_aware)

    first_plan = plan_legacy_migration(
        first,
        cast(InstalledDistribution, first_distribution),
        "5",
    )
    second_plan = plan_legacy_migration(
        second,
        cast(InstalledDistribution, second_distribution),
        "5",
    )

    assert [report.package.standard_id for report in first_plan.reports] == [
        "alpha",
        "omega",
    ]
    assert first_plan.config_content == second_plan.config_content
    assert first_plan.catalog_content == second_plan.catalog_content
    assert first_plan.lock_content == second_plan.lock_content
    assert first_plan.to_jsonable() == second_plan.to_jsonable()


def test_legacy_yaml_is_read_once_and_shared_with_selected_providers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.migration as migration_module

    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    _replace_alpha_signature_target(
        distribution,
        ".project-standards.yml",
        monkeypatch,
    )
    original = migration_module._read_regular_file  # pyright: ignore[reportPrivateUsage]
    reads = 0

    def counted(path: Path, *, kind: str) -> bytes:
        nonlocal reads
        if path.name == ".project-standards.yml":
            reads += 1
        return original(path, kind=kind)

    monkeypatch.setattr(migration_module, "_read_regular_file", counted)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert reads == 1


def test_unknown_yaml_remainder_and_modified_signature_block_the_whole_plan(
    tmp_path: Path,
) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(
        tmp_path,
        "standards_version: v4\nalpha:\n  enabled: true\nunrelated:\n  token: value\n",
    )
    (repo / "legacy-alpha.md").write_text("locally modified\n", encoding="utf-8")

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert {finding.code for finding in plan.findings} == {
        "CP-MIGRATION-LEGACY-DIGEST",
        "CP-MIGRATION-UNCLAIMED-SETTING",
    }
    assert all(action.kind.value != "remove" for action in plan.legacy_removals)


def test_unknown_key_inside_a_known_namespace_remains_unclaimed(tmp_path: Path) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(
        tmp_path,
        "standards_version: v4\nalpha:\n  enabled: true\n  extra: false\n",
    )

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert any(
        finding.code == "CP-MIGRATION-UNCLAIMED-SETTING" and finding.identity == "/alpha/extra"
        for finding in plan.findings
    )


def test_descriptor_shaped_legacy_values_remain_unclaimed_settings(tmp_path: Path) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(
        tmp_path,
        (
            "standards_version: v4\n"
            "alpha:\n"
            "  enabled: true\n"
            "kind: user-data\n"
            "path: /tmp/not-a-snapshot-target\n"
        ),
    )

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    unclaimed = {
        finding.identity
        for finding in plan.findings
        if finding.code == "CP-MIGRATION-UNCLAIMED-SETTING"
    }
    assert {"/kind", "/path"} <= unclaimed


def test_provider_claim_for_missing_setting_blocks_without_hiding_the_remainder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.providers as provider_module

    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    original = provider_module.invoke_provider

    def missing_setting(invocation: ProviderInvocation) -> ProviderResult:
        result = original(invocation)
        if result.migration_report is None:
            return result
        package = result.migration_report.package.model_copy(
            update={"recognized_settings": ("/alpha/enabled/child",)}
        )
        report = result.migration_report.model_copy(update={"package": package})
        return replace(result, migration_report=report)

    monkeypatch.setattr(provider_module, "invoke_provider", missing_setting)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert {finding.code for finding in plan.findings} >= {
        "CP-MIGRATION-SETTING-MISSING",
        "CP-MIGRATION-UNCLAIMED-SETTING",
    }


def test_provider_config_is_validated_against_the_selected_payload_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.providers as provider_module

    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    original = provider_module.invoke_provider

    def invalid_config(invocation: ProviderInvocation) -> ProviderResult:
        result = original(invocation)
        assert result.migration_report is not None
        package = result.migration_report.package.model_copy(
            update={"config": {"unknown_option": True}}
        )
        report = result.migration_report.model_copy(update={"package": package})
        return replace(result, migration_report=report)

    monkeypatch.setattr(provider_module, "invoke_provider", invalid_config)

    with pytest.raises(ControlPlaneError, match="configured package options are invalid"):
        plan_legacy_migration(repo, distribution, "5")


def test_overlapping_provider_discovery_results_block_the_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.migration as migration_module

    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    original = migration_module._legacy_migrations  # pyright: ignore[reportPrivateUsage]

    def duplicate(payload: InstalledPayload) -> tuple[tuple[str, frozenset[str]], ...]:
        discovered = original(payload)
        return (*discovered, *discovered)

    monkeypatch.setattr(migration_module, "_legacy_migrations", duplicate)

    with pytest.raises(ControlPlaneError, match="overlapping results"):
        plan_legacy_migration(repo, distribution, "5")


@pytest.mark.parametrize(
    ("yaml_text", "message"),
    [
        ("alpha: [unterminated\n", "valid YAML"),
        ("base: &base\n  enabled: true\nalpha: *base\n", "anchors or aliases"),
        ("alpha: 1\nalpha: 2\n", "duplicate key"),
    ],
)
def test_legacy_migration_rejects_ambiguous_yaml_syntax(
    tmp_path: Path,
    yaml_text: str,
    message: str,
) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path, yaml_text)

    with pytest.raises(ControlPlaneError, match=message):
        plan_legacy_migration(repo, distribution, "5")


@pytest.mark.parametrize(
    ("syntax", "body", "expected"),
    [
        ("markdown", "Line one\r\nLine two\r\n", b"Line one\nLine two\n"),
        ("toml", "b = 2\r\na = 1\r\n", b'{"a":1,"b":2}'),
        ("yaml", "b: 2\r\na: 1\r\n", b'{"a":1,"b":2}'),
    ],
)
def test_bounded_signatures_hash_normalized_bodies_without_markers(
    syntax: str,
    body: str,
    expected: bytes,
) -> None:
    import project_standards.control_plane.migration as migration_module

    begin = "# BEGIN managed"
    end = "# END managed"
    signature = LegacySignatureDeclaration.model_validate(
        {
            "id": "legacy-block",
            "kind": "bounded-block",
            "format": syntax,
            "targets": ["config.txt"],
            "begin": begin,
            "end": end,
            "known_content_digests": [_digest()],
        }
    )
    content = f"prefix\r\n{begin}\r\n{body}{end}\r\nsuffix\r\n".encode()

    normalized, malformed = migration_module._bounded_block(  # pyright: ignore[reportPrivateUsage]
        content,
        signature,
    )

    assert not malformed
    assert normalized == expected


def test_migrated_config_quotes_every_non_ascii_or_empty_toml_key() -> None:
    import project_standards.control_plane.migration as migration_module

    desired = DesiredConfig.model_validate(
        {
            "project_standards": {"schema_version": "1.0", "catalog": "5"},
            "standards": {
                "demo": {
                    "enabled": True,
                    "version": "latest",
                    "config": {"": "empty", "space key": "space", "ümlaut": "unicode"},
                }
            },
        }
    )

    content = migration_module._render_config(  # pyright: ignore[reportPrivateUsage]
        desired
    )

    assert parse_config(content) == desired
    assert b'"" = "empty"' in content
    assert '"ümlaut" = "unicode"'.encode() in content


def test_migrated_config_escapes_u007f_and_round_trips() -> None:
    import project_standards.control_plane.migration as migration_module

    desired = DesiredConfig.model_validate(
        {
            "project_standards": {"schema_version": "1.0", "catalog": "5"},
            "standards": {
                "demo": {
                    "enabled": True,
                    "version": "latest",
                    "config": {"key\x7f": "value\x7f"},
                }
            },
        }
    )

    content = migration_module._render_config(  # pyright: ignore[reportPrivateUsage]
        desired
    )

    assert content.count(b"\\u007F") == 2
    assert parse_config(content) == desired


@pytest.mark.parametrize("linked", [".project-standards.yml", "legacy-alpha.md"])
def test_legacy_migration_rejects_legacy_symlinks(tmp_path: Path, linked: str) -> None:
    distribution = installed_distribution(tmp_path)
    repo = _legacy_repo(tmp_path)
    target = repo / linked
    content = target.read_bytes()
    target.unlink()
    outside = tmp_path / f"outside-{Path(linked).name}"
    outside.write_bytes(content)
    target.symlink_to(outside)

    with pytest.raises(ControlPlaneError, match="symlink"):
        plan_legacy_migration(repo, distribution, "5")


def test_legacy_migration_rejects_symlinked_signature_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = installed_distribution(tmp_path)
    _replace_alpha_signature_target(distribution, "legacy/alpha.md", monkeypatch)
    repo = _legacy_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "alpha.md").write_bytes((_FULL_ALPHA / "legacy.md").read_bytes())
    (repo / "legacy").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ControlPlaneError, match="symlink"):
        plan_legacy_migration(repo, distribution, "5")


def test_current_legacy_fixture_corpus_covers_namespaces_and_ownership_states() -> None:
    all_namespaces = yaml.safe_load(
        (_LEGACY_CORPUS / "all-namespaces/.project-standards.yml").read_text(encoding="utf-8")
    )
    assert set(all_namespaces) == {
        "standards_version",
        "markdown",
        "python_tooling",
        "markdown_tooling",
        "cli_documentation",
        "spec",
        "agent_handoff",
    }
    assert set(all_namespaces["markdown"]) == {"frontmatter", "adr"}

    unknown = (_LEGACY_CORPUS / "unknown-settings/.project-standards.yml").read_text(
        encoding="utf-8"
    )
    anchored = (_LEGACY_CORPUS / "comments-anchors/.project-standards.yml").read_text(
        encoding="utf-8"
    )
    malformed = (_LEGACY_CORPUS / "malformed/.project-standards.yml").read_text(encoding="utf-8")
    assert "unsupported_option" in unknown and "unknown_standard" in unknown
    assert "# Comments" in anchored and "&shared" in anchored and "*shared" in anchored
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(malformed)

    artifact_root = _LEGACY_CORPUS / "artifact-states"
    required = {
        ".agents/agent-handoff/manifest.json",
        ".markdownlint-cli2.jsonc",
        ".project-standards.yml",
        "AGENTS.md",
        "CLAUDE.md",
        "config/custom-rules.toml",
        "docs/STATUS.md",
    }
    assert {
        path.relative_to(artifact_root).as_posix()
        for path in artifact_root.rglob("*")
        if path.is_file()
    } == required
    assert "Consumer instructions before" in (artifact_root / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "Locally modified" in (artifact_root / "CLAUDE.md").read_text(encoding="utf-8")
