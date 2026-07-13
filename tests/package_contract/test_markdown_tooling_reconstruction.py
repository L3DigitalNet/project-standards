from __future__ import annotations

import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

from project_standards.control_plane.adapters.markdown import MarkdownBlockAdapter
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import (
    apply_legacy_migration,
    plan_legacy_migration,
)
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.planner_helpers import resolution_request, write_payload
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_PAYLOAD = _ROOT / "standards/markdown-tooling/versions/1.2"
_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
_HISTORICAL_SELF_HOST_FORMAT_DIGEST = (
    "sha256:207b5463a64bc7a48e6af31620ebc5052c71118f350e18375a36435061a6e7a5"
)
_HISTORICAL_SELF_HOST_LINT_DIGEST = (
    "sha256:89ad3220574ce78a9628208d768344f300e5e1d701d7adaf16eb923f4cc8f772"
)
_CALLER_FORMAT_DIGEST = "sha256:840619f02e769bc1ad06d78473db020673eb06e665b6f549169af078e6ca9a04"
_CALLER_LINT_DIGEST = "sha256:c51375e9ded693c2148cdcb20c3bfd85b9de4f4017bd8a0b7d05099b1281b845"
_CURRENT_SELF_HOST_FORMAT_DIGEST = (
    "sha256:901639336cf3db411a0090c660d36036c2e8bc9bffd592bec3e4c064baf7cb7a"
)
_CURRENT_SELF_HOST_LINT_DIGEST = (
    "sha256:3124debdc76f2c69dce5e24029de4defb424661835ce8ffad45084276782f656"
)


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    return InstalledPayload(_PAYLOAD, manifest, validate_payload_integrity(_PAYLOAD, manifest))


def _invocation(
    provider_id: str,
    operation: ProviderOperation,
    config: JsonObject,
    *,
    snapshots: JsonObject | None = None,
) -> ProviderInvocation:
    payload = _payload()
    return ProviderInvocation(
        repo=_PAYLOAD,
        payload=payload,
        standard_id="markdown-tooling",
        version=payload.manifest.payload.version,
        provider_id=provider_id,
        operation=operation,
        effective_config=config,
        snapshots=snapshots or {},
    )


def _installed_distribution(tmp_path: Path) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    repository = copy_minimal_repository(fixture)
    family = repository / "standards/markdown-tooling"
    shutil.copytree(_PAYLOAD.parent.parent, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "markdown-tooling"
name = "Markdown Tooling Standard"
summary = "Prettier and markdownlint with semantic editor configuration."
status = "active"

[[versions]]
version = "1.2"
payload = "versions/1.2/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "markdown-tooling"
version = "1.2"
digest = "{payload.integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def test_markdown_tooling_options_are_closed_and_explicitly_typed() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    schema = load_option_schema(_PAYLOAD, manifest)

    assert schema.resolve_options({}) == {
        "contract_version": "1.1",
        "workflow_mode": "caller",
        "lint": True,
        "format": True,
        "ci": {"lint_caller": True, "format_caller": True},
        "markdown_globs": ["**/*.md"],
        "config_globs": ["**/*.json", "**/*.jsonc", "**/*.yml", "**/*.yaml"],
        "exclusions": [],
    }
    configured = schema.resolve_options(
        {
            "lint": False,
            "format": True,
            "ci": {"lint_caller": False, "format_caller": True},
            "markdown_globs": ["docs/**/*.md"],
            "config_globs": ["config/**/*.yaml"],
            "exclusions": [
                {
                    "glob": "docs/generated/**",
                    "applies_to": "both",
                    "reason": "Generated documentation is not formatter-owned.",
                }
            ],
        }
    )
    assert configured["exclusions"] == [
        {
            "glob": "docs/generated/**",
            "applies_to": "both",
            "reason": "Generated documentation is not formatter-owned.",
        }
    ]
    safe_internal_characters = schema.resolve_options(
        {
            "markdown_globs": ["docs/release notes/!important/**/*.md"],
            "config_globs": ["config/[!]special/**/*.yaml"],
            "exclusions": [
                {
                    "glob": "docs/generated output/**",
                    "applies_to": "both",
                    "reason": "Generated output has a separate owner.",
                }
            ],
        }
    )
    assert safe_internal_characters["markdown_globs"] == ["docs/release notes/!important/**/*.md"]

    invalid: tuple[JsonObject, ...] = (
        {"unknown": True},
        {"exclusions": ["docs/generated/**"]},
        {
            "exclusions": [
                {
                    "glob": "docs/generated/**",
                    "applies_to": "unknown",
                    "reason": "Generated.",
                }
            ]
        },
    )
    for options in invalid:
        with pytest.raises(PackageContractError, match="package options violate schema"):
            schema.resolve_options(options)


def test_markdown_tooling_self_host_mode_renders_immutable_workflows() -> None:
    config = load_option_schema(_PAYLOAD, _payload().manifest).resolve_options(
        {"workflow_mode": "self-hosted"}
    )
    for provider_id, resource in (
        ("render-lint-caller", "resources/self-host-lint-markdown.yml"),
        ("render-format-caller", "resources/self-host-format.yml"),
    ):
        result = invoke_provider(_invocation(provider_id, ProviderOperation.RENDER, config))
        assert result.content == (_PAYLOAD / resource).read_bytes()


def test_markdown_tooling_workflow_signature_histories_are_append_only() -> None:
    signatures = {item.id: item for item in _payload().manifest.legacy_signatures}

    assert {
        digest.value for digest in signatures["legacy-format-caller"].known_content_digests
    } == {
        _HISTORICAL_SELF_HOST_FORMAT_DIGEST,
        _CALLER_FORMAT_DIGEST,
        _CURRENT_SELF_HOST_FORMAT_DIGEST,
    }
    assert {digest.value for digest in signatures["legacy-lint-caller"].known_content_digests} == {
        _HISTORICAL_SELF_HOST_LINT_DIGEST,
        _CALLER_LINT_DIGEST,
        _CURRENT_SELF_HOST_LINT_DIGEST,
    }


@pytest.mark.parametrize(
    ("format_digest", "lint_digest"),
    [
        pytest.param(
            _HISTORICAL_SELF_HOST_FORMAT_DIGEST,
            _HISTORICAL_SELF_HOST_LINT_DIGEST,
            id="historical",
        ),
        pytest.param(
            _CURRENT_SELF_HOST_FORMAT_DIGEST,
            _CURRENT_SELF_HOST_LINT_DIGEST,
            id="current",
        ),
    ],
)
def test_markdown_tooling_complete_self_host_cohorts_select_self_hosted(
    format_digest: str,
    lint_digest: str,
) -> None:
    result = invoke_provider(
        _invocation(
            "migrate-legacy",
            ProviderOperation.MIGRATE,
            {},
            snapshots={
                "legacy_config": {"markdown_tooling": {"version": "1.1"}},
                "legacy_signatures": {
                    "legacy-format-caller": {
                        ".github/workflows/format.yml": {
                            "known": True,
                            "digest": format_digest,
                        }
                    },
                    "legacy-lint-caller": {
                        ".github/workflows/lint-markdown.yml": {
                            "known": True,
                            "digest": lint_digest,
                        }
                    },
                },
            },
        )
    )
    assert result.migration_report is not None
    assert result.migration_report.package.config == {
        "contract_version": "1.1",
        "workflow_mode": "self-hosted",
    }
    assert result.migration_report.findings == ()


@pytest.mark.parametrize(
    ("format_digest", "lint_digest"),
    [
        pytest.param(_HISTORICAL_SELF_HOST_FORMAT_DIGEST, None, id="historical-format-only"),
        pytest.param(None, _HISTORICAL_SELF_HOST_LINT_DIGEST, id="historical-lint-only"),
        pytest.param(_CURRENT_SELF_HOST_FORMAT_DIGEST, None, id="current-format-only"),
        pytest.param(None, _CURRENT_SELF_HOST_LINT_DIGEST, id="current-lint-only"),
        pytest.param(
            _HISTORICAL_SELF_HOST_FORMAT_DIGEST,
            _CURRENT_SELF_HOST_LINT_DIGEST,
            id="historical-format-current-lint",
        ),
        pytest.param(
            _CURRENT_SELF_HOST_FORMAT_DIGEST,
            _HISTORICAL_SELF_HOST_LINT_DIGEST,
            id="current-format-historical-lint",
        ),
    ],
)
def test_markdown_tooling_partial_self_host_pair_blocks_migration(
    format_digest: str | None,
    lint_digest: str | None,
) -> None:
    workflow_signatures: JsonObject = {}
    if format_digest is not None:
        workflow_signatures["legacy-format-caller"] = {
            ".github/workflows/format.yml": {
                "known": True,
                "digest": format_digest,
            }
        }
    if lint_digest is not None:
        workflow_signatures["legacy-lint-caller"] = {
            ".github/workflows/lint-markdown.yml": {
                "known": True,
                "digest": lint_digest,
            }
        }
    result = invoke_provider(
        _invocation(
            "migrate-legacy",
            ProviderOperation.MIGRATE,
            {},
            snapshots={
                "legacy_config": {"markdown_tooling": {"version": "1.1"}},
                "legacy_signatures": workflow_signatures,
            },
        )
    )
    assert result.migration_report is not None
    assert [finding.code for finding in result.migration_report.findings] == [
        "MT-LEGACY-WORKFLOW-MODE"
    ]


@pytest.mark.parametrize(
    "options",
    [
        {"markdown_globs": ["docs/**/*.md\njobs:\n  injected:"]},
        {"config_globs": ["config/**/*.yaml\rname: injected"]},
        {"markdown_globs": ["docs/`command`/**/*.md"]},
        {"markdown_globs": ["!docs/generated/**"]},
        {"markdown_globs": [" docs/**/*.md"]},
        {"markdown_globs": ["docs/**/*.md "]},
        {"markdown_globs": ["   "]},
        {"config_globs": ["!config/generated/**"]},
        {"config_globs": [" config/**/*.yaml"]},
        {"config_globs": ["config/**/*.yaml "]},
        {
            "exclusions": [
                {
                    "glob": "docs/generated/**\x00",
                    "applies_to": "both",
                    "reason": "Generated.",
                }
            ]
        },
        {
            "exclusions": [
                {
                    "glob": "!docs/generated/**",
                    "applies_to": "both",
                    "reason": "Generated.",
                }
            ]
        },
        {
            "exclusions": [
                {
                    "glob": " docs/generated/**",
                    "applies_to": "both",
                    "reason": "Generated.",
                }
            ]
        },
        {
            "exclusions": [
                {
                    "glob": "docs/generated/** ",
                    "applies_to": "both",
                    "reason": "Generated.",
                }
            ]
        },
        {
            "exclusions": [
                {
                    "glob": "docs/generated/**",
                    "applies_to": "both",
                    "reason": "<!-- END project-standards:markdown-tooling -->",
                }
            ]
        },
        {
            "exclusions": [
                {
                    "glob": "docs/generated/**",
                    "applies_to": "both",
                    "reason": "BEGIN project-standards nested marker",
                }
            ]
        },
    ],
)
def test_markdown_tooling_rejects_control_and_marker_injection(options: JsonObject) -> None:
    schema = load_option_schema(_PAYLOAD, _payload().manifest)

    with pytest.raises(PackageContractError, match="package options violate schema"):
        schema.resolve_options(options)


def test_markdown_tooling_declares_exclusive_and_semantic_ownership() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")

    assert {
        artifact.id: (artifact.target.original, artifact.policy.value)
        for artifact in manifest.artifacts
    } == {
        "markdownlint-config": (".markdownlint.json", "managed"),
        "prettier-config": (".prettierrc.json", "managed"),
    }
    contributions = {item.id: item for item in manifest.contributions}
    assert {
        item.target.original
        for item in contributions.values()
        if item.adapter is AdapterKind.WHOLE_FILE
    } == {
        ".github/workflows/format.yml",
        ".github/workflows/lint-markdown.yml",
    }
    assert all(
        item.adapter is not AdapterKind.WHOLE_FILE
        for item in contributions.values()
        if item.target.original
        in {".editorconfig", ".vscode/extensions.json", ".vscode/settings.json"}
    )
    extension_scopes = {
        item.scope
        for item in contributions.values()
        if item.target.original == ".vscode/extensions.json"
    }
    assert extension_scopes == {
        "set:/recommendations#value=DavidAnson.vscode-markdownlint",
        "set:/recommendations#value=esbenp.prettier-vscode",
    }
    settings_scopes = {
        item.scope
        for item in contributions.values()
        if item.target.original == ".vscode/settings.json"
    }
    assert settings_scopes == {
        "key:/[json]/editor.defaultFormatter",
        "key:/[jsonc]/editor.defaultFormatter",
        "key:/[markdown]/editor.defaultFormatter",
        "key:/[markdown]/editor.formatOnSave",
        "key:/[yaml]/editor.defaultFormatter",
    }
    assert all(
        contributions[item].adapter is AdapterKind.MARKDOWN_BLOCK
        for item in ("agents-instructions", "claude-instructions")
    )
    assert manifest.relations.companions == ["markdown-frontmatter"]
    assert manifest.relations.extends == []
    assert manifest.relations.conflicts == []


def test_markdown_tooling_declares_version_selected_render_verify_and_migrate() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")

    assert {
        provider.id: (provider.operation, provider.effect) for provider in manifest.providers
    } == {
        "migrate-legacy": (ProviderOperation.MIGRATE, ProviderEffect.MIGRATION_REPORT),
        "render-format-caller": (ProviderOperation.RENDER, ProviderEffect.CONTENT),
        "render-lint-caller": (ProviderOperation.RENDER, ProviderEffect.CONTENT),
        "render-semantic": (ProviderOperation.RENDER, ProviderEffect.CONTENT),
        "verify-format": (ProviderOperation.VERIFY, ProviderEffect.FINDINGS),
        "verify-lint": (ProviderOperation.VERIFY, ProviderEffect.FINDINGS),
    }
    assert [migration.from_endpoint.value for migration in manifest.migrations] == [
        "legacy:v4-markdown-tooling"
    ]
    assert {signature.id for signature in manifest.legacy_signatures} == {
        "legacy-editorconfig",
        "legacy-format-caller",
        "legacy-lint-caller",
        "legacy-markdownlint-config",
        "legacy-prettier-config",
        "legacy-vscode-extensions",
    }


def test_markdown_tooling_renders_automatic_and_manual_only_callers() -> None:
    schema = load_option_schema(_PAYLOAD, _payload().manifest)
    automatic = schema.resolve_options({})
    lint_only = schema.resolve_options(
        {"format": False, "ci": {"lint_caller": True, "format_caller": False}}
    )
    format_only = schema.resolve_options(
        {"lint": False, "ci": {"lint_caller": False, "format_caller": True}}
    )
    disabled = schema.resolve_options(
        {
            "lint": False,
            "format": False,
            "ci": {"lint_caller": False, "format_caller": False},
        }
    )

    def render(provider_id: str, config: JsonObject) -> bytes:
        result = invoke_provider(_invocation(provider_id, ProviderOperation.RENDER, config))
        assert result.content is not None
        return result.content

    auto_lint = render("render-lint-caller", automatic)
    auto_format = render("render-format-caller", automatic)
    lint_only_lint = render("render-lint-caller", lint_only)
    lint_only_format = render("render-format-caller", lint_only)
    format_only_lint = render("render-lint-caller", format_only)
    disabled_lint = render("render-lint-caller", disabled)
    disabled_format = render("render-format-caller", disabled)

    assert b"pull_request:" in auto_lint and b"push:" in auto_lint
    assert b"pull_request:" in auto_format and b"push:" in auto_format
    for manual in (lint_only_format, format_only_lint, disabled_lint, disabled_format):
        assert b"workflow_dispatch:" in manual
        assert b"pull_request:" not in manual
        assert b"push:" not in manual
    assert b"lint-markdown.yml@v5" in auto_lint
    assert b"format.yml@v5" in auto_format
    assert yaml.safe_load(auto_lint)["jobs"]["lint-markdown"]["with"]["markdownlint"] is True
    assert yaml.safe_load(lint_only_lint)["jobs"]["lint-markdown"]["with"]["markdownlint"] is True
    assert yaml.safe_load(lint_only_format)["jobs"]["format"]["with"]["prettier"] is False
    assert (
        yaml.safe_load(format_only_lint)["jobs"]["lint-markdown"]["with"]["markdownlint"] is False
    )
    assert yaml.safe_load(disabled_lint)["jobs"]["lint-markdown"]["with"]["markdownlint"] is False


def test_markdown_tooling_structurally_serializes_caller_inputs() -> None:
    schema = load_option_schema(_PAYLOAD, _payload().manifest)
    configured = schema.resolve_options(
        {
            "markdown_globs": ["docs/**/*.md"],
            "config_globs": ["config/**/*.json", "config/**/*.yaml"],
            "exclusions": [
                {
                    "glob": "docs/generated/**",
                    "applies_to": "both",
                    "reason": "Generated output has a separate owner.",
                },
                {
                    "glob": "config/snapshots/**",
                    "applies_to": "format",
                    "reason": "Snapshots preserve exact upstream bytes.",
                },
            ],
        }
    )

    lint_result = invoke_provider(
        _invocation("render-lint-caller", ProviderOperation.RENDER, configured)
    )
    format_result = invoke_provider(
        _invocation("render-format-caller", ProviderOperation.RENDER, configured)
    )
    assert lint_result.content is not None
    assert format_result.content is not None
    lint = yaml.safe_load(lint_result.content)
    formatter = yaml.safe_load(format_result.content)

    assert lint["jobs"]["lint-markdown"]["with"]["globs"] == ("docs/**/*.md\n!docs/generated/**")
    assert formatter["jobs"]["format"]["with"] == {
        "prettier": True,
        "globs": "docs/**/*.md\nconfig/**/*.json\nconfig/**/*.yaml",
        "exclusions": "config/snapshots/**\ndocs/generated/**",
    }

    disabled = schema.resolve_options(
        {"format": False, "ci": {"lint_caller": True, "format_caller": False}}
    )
    disabled_result = invoke_provider(
        _invocation("render-format-caller", ProviderOperation.RENDER, disabled)
    )
    assert disabled_result.content is not None
    assert yaml.safe_load(disabled_result.content)["jobs"]["format"]["with"]["prettier"] is False


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"markdown_globs": ["!docs/generated/**"]}, "safe include glob"),
        ({"markdown_globs": ["docs/**/*.md "]}, "safe include glob"),
        ({"config_globs": ["config/**/*.yaml "]}, "safe include glob"),
        (
            {
                "exclusions": [
                    {
                        "glob": "docs/generated/** ",
                        "applies_to": "format",
                        "reason": "Generated.",
                    }
                ]
            },
            "safe exclusion glob",
        ),
    ],
)
def test_markdown_tooling_provider_rejects_glob_boundary_bypass(
    update: JsonObject,
    message: str,
) -> None:
    hostile: JsonObject = {
        "contract_version": "1.1",
        "lint": True,
        "format": True,
        "ci": {"lint_caller": True, "format_caller": True},
        "markdown_globs": ["docs/**/*.md"],
        "config_globs": ["config/**/*.yaml"],
        "exclusions": [],
        **update,
    }

    with pytest.raises(ControlPlaneError, match="provider failed with ValueError") as caught:
        invoke_provider(_invocation("render-format-caller", ProviderOperation.RENDER, hostile))
    assert isinstance(caught.value.__cause__, ValueError)
    assert message in str(caught.value.__cause__)


def test_markdown_tooling_renders_typed_exclusions_into_bounded_guidance() -> None:
    config = load_option_schema(_PAYLOAD, _payload().manifest).resolve_options(
        {
            "exclusions": [
                {
                    "glob": "docs/generated/**",
                    "applies_to": "both",
                    "reason": "Generated output has a separate byte owner.",
                }
            ]
        }
    )
    snapshots: JsonObject = {
        "planned_contribution": {
            "id": "agents-instructions",
            "target": "AGENTS.md",
            "adapter": "markdown-block",
            "scope": "block:markdown-tooling",
        }
    }

    result = invoke_provider(
        _invocation(
            "render-semantic",
            ProviderOperation.RENDER,
            config,
            snapshots=snapshots,
        )
    )

    assert result.content is not None
    assert b"docs/generated/**" in result.content
    assert b"Generated output has a separate byte owner." in result.content
    assert b"BEGIN project-standards:markdown-tooling" in result.content


def test_markdown_tooling_fresh_plan_preserves_semantic_boundaries(tmp_path: Path) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    repo.mkdir()

    plan = plan_reconciliation(PlannerRequest(repo, resolution_request((payload,)), (payload,)))

    assert plan.applicable, plan.findings
    assert (
        plan.proposed_content(".markdownlint.json")
        == (_PAYLOAD / "artifacts/markdownlint.json").read_bytes()
    )
    assert (
        plan.proposed_content(".prettierrc.json")
        == (_PAYLOAD / "artifacts/prettierrc.json").read_bytes()
    )
    extensions = json.loads(plan.proposed_content(".vscode/extensions.json") or b"null")
    assert set(extensions["recommendations"]) == {
        "DavidAnson.vscode-markdownlint",
        "esbenp.prettier-vscode",
    }
    settings = json.loads(plan.proposed_content(".vscode/settings.json") or b"null")
    assert settings["[markdown]"]["editor.formatOnSave"] is True
    assert "python.defaultInterpreterPath" not in settings
    editorconfig = plan.proposed_content(".editorconfig")
    assert editorconfig is not None
    assert b"[*.md]" in editorconfig
    assert b"[*.{yml,yaml}]" in editorconfig
    assert b"[*.py]" not in editorconfig
    agents = plan.proposed_content("AGENTS.md")
    assert agents is not None
    assert b"BEGIN project-standards:markdown-tooling" in agents
    assert b"format.yml@v5" in (plan.proposed_content(".github/workflows/format.yml") or b"")


def test_markdown_tooling_plan_preserves_vscode_setting_siblings(tmp_path: Path) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    settings_path = repo / ".vscode/settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        '{"[markdown]":{"editor.wordWrap":"on"},"consumer.setting":true}\n',
        encoding="utf-8",
    )

    plan = plan_reconciliation(PlannerRequest(repo, resolution_request((payload,)), (payload,)))

    assert plan.applicable, plan.findings
    settings = json.loads(plan.proposed_content(".vscode/settings.json") or b"null")
    assert settings["[markdown]"] == {
        "editor.wordWrap": "on",
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
    }
    assert settings["consumer.setting"] is True


def test_markdown_tooling_verify_reports_missing_managed_bytes() -> None:
    config = load_option_schema(_PAYLOAD, _payload().manifest).resolve_options({})

    lint = invoke_provider(
        _invocation("verify-lint", ProviderOperation.VERIFY, config, snapshots={})
    )
    formatter = invoke_provider(
        _invocation("verify-format", ProviderOperation.VERIFY, config, snapshots={})
    )

    assert [finding.code for finding in lint.findings] == ["MT-LINT-DRIFT", "MT-LINT-DRIFT"]
    assert [finding.code for finding in formatter.findings] == [
        "MT-FORMAT-DRIFT",
        "MT-FORMAT-DRIFT",
    ]


def test_markdown_tooling_migration_maps_yaml_and_exact_v1_artifacts() -> None:
    payload = _payload()
    caller_digests = {
        "legacy-format-caller": _CALLER_FORMAT_DIGEST,
        "legacy-lint-caller": _CALLER_LINT_DIGEST,
    }
    signatures: JsonObject = {
        signature.id: {
            signature.targets[0].original: {
                "known": True,
                "digest": caller_digests.get(
                    signature.id,
                    signature.known_content_digests[0].value,
                ),
            }
        }
        for signature in payload.manifest.legacy_signatures
    }

    snapshots: JsonObject = {
        "legacy_config": {
            "standards_version": "v4",
            "markdown_tooling": {"version": "1.1"},
        },
        "legacy_signatures": signatures,
    }
    result = invoke_provider(
        _invocation(
            "migrate-legacy",
            ProviderOperation.MIGRATE,
            {},
            snapshots=snapshots,
        )
    )

    assert result.migration_report is not None
    report = result.migration_report
    assert report.package.config == {"contract_version": "1.1"}
    assert report.package.recognized_settings == ("/markdown_tooling/version",)
    assert [(claim.signature_id, claim.disposition.value) for claim in report.claims] == [
        ("legacy-editorconfig", "preserve"),
        ("legacy-format-caller", "adopt"),
        ("legacy-lint-caller", "adopt"),
        ("legacy-markdownlint-config", "adopt"),
        ("legacy-prettier-config", "adopt"),
        ("legacy-vscode-extensions", "preserve"),
    ]

    modified: JsonObject = dict(signatures)
    modified["legacy-prettier-config"] = {
        ".prettierrc.json": {"known": False, "digest": f"sha256:{'a' * 64}"}
    }
    modified_snapshots: JsonObject = {
        "legacy_config": {"markdown_tooling": {"version": "1.1"}},
        "legacy_signatures": modified,
    }
    conflict = invoke_provider(
        _invocation(
            "migrate-legacy",
            ProviderOperation.MIGRATE,
            {},
            snapshots=modified_snapshots,
        )
    )
    assert conflict.migration_report is not None
    assert [
        (finding.code, finding.path.original) for finding in conflict.migration_report.findings
    ] == [("MT-LEGACY-MODIFIED", ".prettierrc.json")]


def test_markdown_tooling_composes_with_frontmatter_and_synthetic_python(
    tmp_path: Path,
) -> None:
    markdown = _payload()
    frontmatter_root = _ROOT / "standards/markdown-frontmatter/versions/1.2"
    frontmatter_manifest = load_payload_manifest(frontmatter_root / "payload.toml")
    frontmatter = InstalledPayload(
        frontmatter_root,
        frontmatter_manifest,
        validate_payload_integrity(frontmatter_root, frontmatter_manifest),
    )
    synthetic_python = write_payload(
        tmp_path / "python-tooling",
        "python-tooling",
        contributions=(
            {
                "id": "shared-root",
                "target": ".editorconfig",
                "adapter": "editorconfig",
                "scope": "property:$global#root",
                "content": b"root = true\n",
                "shared_identity": "editorconfig/root",
            },
            {
                "id": "python-indent",
                "target": ".editorconfig",
                "adapter": "editorconfig",
                "scope": "property:*.py#indent_size",
                "content": b"[*.py]\nindent_size = 4\n",
            },
            {
                "id": "python-extension",
                "target": ".vscode/extensions.json",
                "adapter": "jsonc",
                "scope": "set:/recommendations#value=ms-python.python",
                "content": b'{"recommendations":["ms-python.python"]}',
            },
        ),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()

    plan = plan_reconciliation(
        PlannerRequest(
            repo,
            resolution_request((markdown, frontmatter, synthetic_python)),
            (markdown, frontmatter, synthetic_python),
        )
    )

    assert plan.applicable, plan.findings
    editorconfig = plan.proposed_content(".editorconfig")
    assert editorconfig is not None
    assert b"root = true" in editorconfig
    assert editorconfig.count(b"root = true") == 1
    assert b"[*.md]" in editorconfig and b"[*.py]" in editorconfig
    extensions = json.loads(plan.proposed_content(".vscode/extensions.json") or b"null")
    assert set(extensions["recommendations"]) == {
        "DavidAnson.vscode-markdownlint",
        "esbenp.prettier-vscode",
        "ms-python.python",
    }
    workflow = plan.proposed_content(".github/workflows/validate-standards.yml")
    assert workflow is not None and b"frontmatter:" in workflow


def test_markdown_tooling_apply_disable_and_second_apply_converge(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "markdown-tooling", True)

    request = build_planner_request(repo, distribution, frozenset())
    first = plan_reconciliation(request)
    assert first.applicable, first.findings
    applied = apply_reconciliation(ApplyRequest(request, first))
    assert applied.success, applied
    assert (repo / ".markdownlint.json").is_file()
    assert (repo / ".prettierrc.json").is_file()
    assert (repo / ".github/workflows/lint-markdown.yml").is_file()
    assert (repo / ".github/workflows/format.yml").is_file()

    second_request = build_planner_request(repo, distribution, frozenset())
    second = plan_reconciliation(second_request)
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )
    assert apply_reconciliation(ApplyRequest(second_request, second)).success

    set_standard_enabled(repo, "markdown-tooling", False)
    disabled_request = build_planner_request(repo, distribution, frozenset())
    disabled = plan_reconciliation(disabled_request)
    assert disabled.applicable, disabled.findings
    assert apply_reconciliation(ApplyRequest(disabled_request, disabled)).success
    assert not (repo / ".markdownlint.json").exists()
    assert not (repo / ".prettierrc.json").exists()
    assert not (repo / ".github/workflows/lint-markdown.yml").exists()
    assert not (repo / ".github/workflows/format.yml").exists()


def test_markdown_tooling_real_apply_materializes_custom_formatter_scope(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    (repo / ".standards/config.toml").write_text(
        """[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.markdown-tooling]
enabled = true
version = "latest"

[standards.markdown-tooling.config]
contract_version = "1.1"
lint = true
format = true
markdown_globs = ["docs/**/*.md"]
config_globs = ["config/**/*.json", "config/**/*.yaml"]
exclusions = [
  { glob = "docs/generated/**", applies_to = "both", reason = "Generated output has a separate owner." },
  { glob = "config/snapshots/**", applies_to = "format", reason = "Snapshots preserve exact upstream bytes." },
]

[standards.markdown-tooling.config.ci]
lint_caller = true
format_caller = true
""",
        encoding="utf-8",
    )

    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)

    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    formatter = yaml.safe_load((repo / ".github/workflows/format.yml").read_text(encoding="utf-8"))
    assert formatter["jobs"]["format"]["with"] == {
        "prettier": True,
        "globs": "docs/**/*.md\nconfig/**/*.json\nconfig/**/*.yaml",
        "exclusions": "config/snapshots/**\ndocs/generated/**",
    }


def test_markdown_tooling_real_v4_migration_applies_and_converges(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        'standards_version: "v4"\nmarkdown_tooling:\n  version: "1.1"\n',
        encoding="utf-8",
    )
    sources = {
        ".markdownlint.json": _PAYLOAD / "artifacts/markdownlint.json",
        ".prettierrc.json": _PAYLOAD / "artifacts/prettierrc.json",
        ".editorconfig": _PAYLOAD / "resources/legacy-editorconfig",
        ".vscode/extensions.json": _PAYLOAD / "resources/legacy-vscode-extensions.json",
        ".github/workflows/lint-markdown.yml": (
            _PAYLOAD / "resources/legacy-lint-markdown.caller.yml"
        ),
        ".github/workflows/format.yml": _PAYLOAD / "resources/legacy-format.caller.yml",
    }
    for target, source in sources.items():
        destination = repo / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    result = apply_legacy_migration(plan)
    assert result.success, result
    assert not (repo / ".project-standards.yml").exists()
    assert b"@v5" in (repo / ".github/workflows/lint-markdown.yml").read_bytes()
    assert b"@v5" in (repo / ".github/workflows/format.yml").read_bytes()
    assert b"[*.py]" in (repo / ".editorconfig").read_bytes()
    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


def test_markdown_tooling_instruction_block_is_prettier_stable(tmp_path: Path) -> None:
    binary = _ROOT / "node_modules/.bin/prettier"
    if not binary.is_file():
        pytest.skip("lockfile-installed Prettier is unavailable")
    payload = _payload()
    repo = tmp_path / "consumer"
    repo.mkdir()
    plan = plan_reconciliation(PlannerRequest(repo, resolution_request((payload,)), (payload,)))
    content = plan.proposed_content("AGENTS.md")
    assert content is not None
    path = repo / "AGENTS.md"
    path.write_bytes(content)
    adapter = MarkdownBlockAdapter()
    before = adapter.inspect(content, ("block:markdown-tooling",)).units[0]

    subprocess.run(
        [
            str(binary),
            "--config",
            str(_PAYLOAD / "artifacts/prettierrc.json"),
            "--write",
            str(path),
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    after = adapter.inspect(path.read_bytes(), ("block:markdown-tooling",)).units[0]
    assert after.semantic_digest == before.semantic_digest


def test_markdown_tooling_payload_docs_have_only_relocatable_local_links() -> None:
    root = _PAYLOAD.resolve()
    for document in _PAYLOAD.rglob("*.md"):
        for raw in _LINK.findall(document.read_text(encoding="utf-8")):
            path_text = raw.split("#", maxsplit=1)[0]
            if not path_text or "://" in path_text:
                continue
            target = (document.parent / path_text).resolve()
            assert target.is_relative_to(root), raw
            assert target.exists(), raw


def test_markdown_tooling_v2_docs_do_not_present_v1_copy_adoption_as_current() -> None:
    documents = {
        path.name: path.read_text(encoding="utf-8")
        for path in (_PAYLOAD / "README.md", _PAYLOAD / "adopt.md", _PAYLOAD / "agent-summary.md")
    }
    stale = ("Copy-adopt configs", "Recommended copy", "Copy this into `AGENTS.md`")

    for name, content in documents.items():
        for phrase in stale:
            assert phrase not in content, f"{name} contains stale V1 instruction: {phrase}"
    readme = documents["README.md"].lower()
    for expected in (
        "managed caller",
        "manual-only",
        "central lock",
        "per-setting",
        "delegated lifecycle",
    ):
        assert expected in readme
    assert "markdownlint-cli2-action@v24" in documents["README.md"]
    assert "separate `--ignore-path` arguments" in documents["README.md"]
    assert "combines package exclusions" not in documents["README.md"]


def test_markdown_tooling_payload_is_byte_identical_in_built_wheel(tmp_path: Path) -> None:
    project = copy_minimal_repository(tmp_path)
    family = project / "standards/markdown-tooling"
    shutil.copytree(_PAYLOAD.parent.parent, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "markdown-tooling"
name = "Markdown Tooling Standard"
summary = "Prettier and markdownlint with semantic editor configuration."
status = "active"

[[versions]]
version = "1.2"
payload = "versions/1.2/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    package = project / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """[project]
name = "project-standards"
version = "5.0.0"
requires-python = ">=3.14"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**"]
""",
        encoding="utf-8",
    )
    assert sync_payload_projection(project, check=False) == ()
    distribution = project / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(distribution)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (wheel,) = distribution.glob("*.whl")
    prefix = "project_standards/payloads/markdown-tooling/1.2/"
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
    source_files = {
        path.relative_to(_PAYLOAD).as_posix(): path.read_bytes()
        for path in _PAYLOAD.rglob("*")
        if path.is_file()
    }
    assert wheel_files == source_files
