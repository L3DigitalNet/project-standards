from __future__ import annotations

import json
import socket
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
import yaml
from pydantic import ValidationError

from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_catalog,
    parse_config,
    parse_lock,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import (
    InstalledCatalog,
    InstalledDistribution,
    InstalledPayload,
    ParsedToolRelease,
)
from project_standards.control_plane.migration import (
    LegacyClaim,
    LegacyDisposition,
    MigratedPackage,
    MigrationFinding,
    MigrationReport,
    migration_report_to_jsonable,
    plan_legacy_migration,
    render_migration_report,
)
from project_standards.control_plane.models import ConsumerCatalog, DesiredConfig
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.providers import ProviderInvocation, ProviderResult
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    LegacySignatureDeclaration,
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
        assert recorded_release is None
        return self._installed

    def consumer_catalog(self, _catalog: CatalogMajor | str) -> ConsumerCatalog:
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
    assert parse_lock(plan.lock_content) == plan.reconciliation.next_lock
    assert [action.target for action in plan.legacy_removals] == [".project-standards.yml"]
    assert any(action.target == ".standards/alpha/config.toml" for action in plan.actions)
    assert plan.reconciliation.next_lock.referenced_inputs[0].path.original == (
        "config/alpha-options.toml"
    )


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
