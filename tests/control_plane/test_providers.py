from __future__ import annotations

import base64
import hashlib
import json
import socket
from pathlib import Path

import pytest

from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import (
    ProviderInvocation,
    invoke_provider,
    resolve_referenced_inputs,
)
from project_standards.control_plane.schemas import control_plane_schema_documents
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion, SafeRelativePath
from project_standards.package_contract.payload import (
    ExtensionDeclaration,
    PayloadManifest,
    ProviderEffect,
    ProviderOperation,
)


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _extension(*, preferred: bool = True) -> ExtensionDeclaration:
    return ExtensionDeclaration.model_validate(
        {
            "id": "extra-rules",
            "option": "extra_rules_file",
            "media_type": "application/toml",
            "path_policy": "repository-relative",
            **({"preferred_root": ".standards/extensions/demo/"} if preferred else {}),
        }
    )


@pytest.mark.parametrize(
    "relative",
    [".standards/extensions/demo/rules.toml", "config/custom-rules.toml"],
)
def test_referenced_input_accepts_preferred_and_conventional_paths(
    tmp_path: Path,
    relative: str,
) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text("enabled = true\n", encoding="utf-8")

    inputs = resolve_referenced_inputs(
        tmp_path,
        standard_id="demo",
        version=PackageVersion("1.2"),
        config={"extra_rules_file": relative},
        extensions=(_extension(),),
        managed_targets=(),
        enabled=True,
    )

    assert len(inputs) == 1
    assert inputs[0].path.original == relative
    assert inputs[0].standard_id == "demo"
    assert inputs[0].extension_id == "extra-rules"


@pytest.mark.parametrize(
    ("relative", "message"),
    [
        ("missing.toml", "does not exist"),
        ("../outside.toml", "repository-relative"),
        ("/tmp/absolute.toml", "repository-relative"),
        (".standards/packages/demo/input.toml", "package namespace"),
    ],
)
def test_referenced_input_rejects_unsafe_or_missing_paths(
    tmp_path: Path,
    relative: str,
    message: str,
) -> None:
    if not relative.startswith(("..", "/", "missing")):
        target = tmp_path / relative
        target.parent.mkdir(parents=True)
        target.write_text("x", encoding="utf-8")

    with pytest.raises(ControlPlaneError, match=message):
        resolve_referenced_inputs(
            tmp_path,
            standard_id="demo",
            version=PackageVersion("1.2"),
            config={"extra_rules_file": relative},
            extensions=(_extension(),),
            managed_targets=(),
            enabled=True,
        )


def test_referenced_input_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.toml"
    outside.write_text("private", encoding="utf-8")
    link = tmp_path / "rules.toml"
    link.symlink_to(outside)

    with pytest.raises(ControlPlaneError, match="symlink"):
        resolve_referenced_inputs(
            tmp_path,
            standard_id="demo",
            version=PackageVersion("1.2"),
            config={"extra_rules_file": "rules.toml"},
            extensions=(_extension(preferred=False),),
            managed_targets=(),
            enabled=True,
        )


def test_referenced_input_rejects_applied_or_planned_output_alias(tmp_path: Path) -> None:
    target = tmp_path / "config/rules.toml"
    target.parent.mkdir()
    target.write_text("x", encoding="utf-8")

    with pytest.raises(ControlPlaneError, match="managed output"):
        resolve_referenced_inputs(
            tmp_path,
            standard_id="demo",
            version=PackageVersion("1.2"),
            config={"extra_rules_file": "config/rules.toml"},
            extensions=(_extension(preferred=False),),
            managed_targets=(SafeRelativePath.parse("config/rules.toml"),),
            enabled=True,
        )


def test_referenced_input_digest_changes_without_claiming_or_rewriting_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "rules.toml"
    target.write_text("first", encoding="utf-8")
    first = resolve_referenced_inputs(
        tmp_path,
        standard_id="demo",
        version=PackageVersion("1.2"),
        config={"extra_rules_file": "rules.toml"},
        extensions=(_extension(preferred=False),),
        managed_targets=(),
        enabled=True,
    )
    target.write_text("second", encoding="utf-8")
    second = resolve_referenced_inputs(
        tmp_path,
        standard_id="demo",
        version=PackageVersion("1.2"),
        config={"extra_rules_file": "rules.toml"},
        extensions=(_extension(preferred=False),),
        managed_targets=(),
        enabled=True,
    )

    assert first[0].digest != second[0].digest
    assert target.read_text(encoding="utf-8") == "second"


def test_disabled_reference_is_removed_from_state_but_consumer_file_is_preserved(
    tmp_path: Path,
) -> None:
    target = tmp_path / "rules.toml"
    target.write_text("consumer-owned", encoding="utf-8")

    inputs = resolve_referenced_inputs(
        tmp_path,
        standard_id="demo",
        version=PackageVersion("1.2"),
        config={"extra_rules_file": "rules.toml"},
        extensions=(_extension(preferred=False),),
        managed_targets=(),
        enabled=False,
    )

    assert inputs == ()
    assert target.read_text(encoding="utf-8") == "consumer-owned"


def test_referenced_input__no_extensions__skips_managed_target_resolution(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "managed").symlink_to(outside, target_is_directory=True)

    inputs = resolve_referenced_inputs(
        tmp_path,
        standard_id="demo",
        version=PackageVersion("1.2"),
        config={},
        extensions=(),
        managed_targets=(SafeRelativePath.parse("managed/output.txt"),),
        enabled=True,
    )

    assert inputs == ()


def test_optional_reference_is_absent_when_nullable_option_is_unset(tmp_path: Path) -> None:
    inputs = resolve_referenced_inputs(
        tmp_path,
        standard_id="demo",
        version=PackageVersion("1.2"),
        config={"extra_rules_file": None},
        extensions=(_extension(preferred=False),),
        managed_targets=(),
        enabled=True,
    )

    assert inputs == ()


def _provider_schema(effect: ProviderEffect) -> dict[str, object]:
    if effect is ProviderEffect.MIGRATION_REPORT:
        return control_plane_schema_documents()["migration-report.schema.json"]
    if effect is ProviderEffect.MUTATION_PLAN:
        return control_plane_schema_documents()["mutation-plan.schema.json"]
    if effect is ProviderEffect.CONTENT:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "code": {"type": "string"},
                        "severity": {"enum": ["error", "warning"]},
                        "path": {"type": "string"},
                        "identity": {"type": "string"},
                        "message": {"type": "string"},
                        "hint": {"type": "string"},
                    },
                    "required": ["code", "severity", "path", "identity", "message", "hint"],
                },
            }
        },
        "required": ["findings"],
    }


def _provider_code(effect: ProviderEffect, behavior: str, marker: str) -> str:
    if behavior == "write":
        body = (
            "Path('README.md').write_text('bad', encoding='utf-8')\n    return {'content': 'bad'}"
        )
        imports = "from pathlib import Path\n"
    elif behavior == "write-child":
        body = (
            "Path('docs/handoff/sessions/provider.md').write_text('bad', encoding='utf-8')"
            "\n    return {'content': 'bad'}"
        )
        imports = "from pathlib import Path\n"
    elif behavior == "network":
        body = "socket.socket()\n    return {'content': 'bad'}"
        imports = "import socket\n"
    elif behavior == "raise":
        body = "raise RuntimeError('private provider detail')"
        imports = ""
    elif behavior == "undeclared-resource":
        body = "return {'content': resources['not-declared'].decode()}"
        imports = ""
    elif behavior == "mutate-input":
        body = "request['config']['mode'] = 'changed'\n    return {'content': 'bad'}"
        imports = ""
    elif behavior == "wrong-output":
        body = "return {'unexpected': 'shape'}"
        imports = ""
    elif behavior == "undeclared-signature":
        digest = "sha256:" + ("a" * 64)
        body = (
            "return {'schema_version': '1.0', 'package': {'standard_id': 'demo', "
            f"'version': '{marker}', 'selector': 'latest', 'config': {{}}, "
            "'recognized_settings': ['/demo']}, 'claims': [{'signature_id': "
            "'undeclared-signature', 'target': 'legacy.yml', 'observed_digest': "
            f"'{digest}', 'ownership': 'managed', 'disposition': "
            "'adopt'}], 'findings': []}"
        )
        imports = ""
    elif behavior == "secret-config":
        body = (
            "return {'schema_version': '1.0', 'package': {'standard_id': 'demo', "
            f"'version': '{marker}', 'selector': 'latest', 'config': "
            "{'api_token': 'do-not-echo-this-value'}, 'recognized_settings': ['/demo']}, "
            "'claims': [], 'findings': []}"
        )
        imports = ""
    elif effect is ProviderEffect.CONTENT:
        body = (
            "print('private stdout')\n"
            "    print('private stderr', file=sys.stderr)\n"
            f"    return {{'content': '{marker}:' + request['version'] + ':' + resources['provider-data'].decode()}}"
        )
        imports = "import sys\n"
    elif effect is ProviderEffect.FINDINGS:
        body = (
            "return {'findings': [{'code': 'DEMO', 'severity': 'warning', "
            "'path': 'README.md', 'identity': 'demo', 'message': 'review', "
            "'hint': 'inspect'}]}"
        )
        imports = ""
    elif effect is ProviderEffect.MUTATION_PLAN and behavior != "success":
        replacement = b"updated\n"
        action = {
            "kind": "update",
            "target": "README.md",
            "adapter": "whole-file",
            "scope": "$file",
            "summary": "update document",
            "precondition_digest": _digest(b"repo\n"),
            "content_digest": _digest(replacement),
            "content_base64": base64.b64encode(replacement).decode("ascii"),
            "mode": "0644",
        }
        if behavior == "undeclared-target":
            action["target"] = "other.md"
        elif behavior == "wrong-precondition":
            action["precondition_digest"] = "sha256:" + ("c" * 64)
        elif behavior == "create-over-regular":
            action["kind"] = "create"
        elif behavior == "remove":
            action = {
                "kind": "remove",
                "target": "README.md",
                "adapter": "whole-file",
                "scope": "$file",
                "summary": "remove document",
                "precondition_digest": _digest(b"repo\n"),
            }
        elif behavior == "wrong-adapter":
            action["adapter"] = "toml"
            action["scope"] = "key:/document"
        actions = [action, action] if behavior == "duplicate-target" else [action]
        body = "return " + repr(
            {
                "schema_version": "1.0",
                "standard_id": "demo",
                "version": marker,
                "actions": actions,
            }
        )
        imports = ""
    elif effect is ProviderEffect.MUTATION_PLAN:
        body = (
            "return {'schema_version': '1.0', 'standard_id': 'demo', "
            f"'version': '{marker}', 'actions': []}}"
        )
        imports = ""
    else:
        body = (
            "return {'schema_version': '1.0', 'package': {'standard_id': 'demo', "
            f"'version': '{marker}', 'selector': 'latest', 'config': {{'mode': 'strict'}}, "
            "'recognized_settings': ['/demo']}, 'claims': [], 'findings': []}"
        )
        imports = ""
    return f"{imports}\ndef run(request, resources):\n    {body}\n"


def _write_provider_payload(
    root: Path,
    *,
    version: str = "1.2",
    operation: ProviderOperation = ProviderOperation.RENDER,
    effect: ProviderEffect = ProviderEffect.CONTENT,
    behavior: str = "success",
    extensions: tuple[ExtensionDeclaration, ...] = (),
) -> InstalledPayload:
    root.mkdir(parents=True)
    input_schema = control_plane_schema_documents()["provider-input.schema.json"]
    output_schema = _provider_schema(effect)
    if behavior == "remote-schema":
        output_schema = {"$ref": "https://example.invalid/provider-output.json"}
    files: dict[str, bytes] = {
        "README.md": b"# Demo\n",
        "agent-summary.md": b"summary\n",
        "adopt.md": b"adopt\n",
        "config.schema.json": json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "additionalProperties": False,
                "properties": {},
            }
        ).encode(),
        "providers/run.py": _provider_code(effect, behavior, version).encode(),
        "schemas/input.json": json.dumps(input_schema).encode(),
        "schemas/output.json": json.dumps(output_schema).encode(),
        "resources/data.txt": b"declared-data",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (root / "payload.toml").write_text("fixture = true\n", encoding="utf-8")
    resources: list[dict[str, object]] = []
    roles = {
        "README.md": ("readme", "canonical-standard", "text/markdown"),
        "agent-summary.md": ("agent-summary", "agent-summary", "text/markdown"),
        "adopt.md": ("adopt", "adoption-guide", "text/markdown"),
        "config.schema.json": ("config-schema", "config-schema", "application/schema+json"),
        "providers/run.py": ("provider-code", "provider-resource", "text/x-python"),
        "schemas/input.json": ("provider-input", "provider-resource", "application/schema+json"),
        "schemas/output.json": ("provider-output", "provider-resource", "application/schema+json"),
        "resources/data.txt": ("provider-data", "provider-resource", "text/plain"),
    }
    for relative, content in files.items():
        resource_id, role, media_type = roles[relative]
        resources.append(
            {
                "id": resource_id,
                "role": role,
                "path": relative,
                "media_type": media_type,
                "digest": _digest(content),
            }
        )
    phase = {
        ProviderOperation.RENDER: "plan",
        ProviderOperation.VALIDATE: "validate",
        ProviderOperation.FIX: "authoring",
        ProviderOperation.SCAFFOLD: "authoring",
        ProviderOperation.UPGRADE: "authoring",
        ProviderOperation.MIGRATE: "plan",
    }[operation]
    manifest = PayloadManifest.model_validate(
        {
            "schema_version": "1.0",
            "payload": {"standard": "demo", "version": version, "availability": "consumer"},
            "config": {"schema_resource": "config-schema"},
            "capabilities": {"provides": [], "consumes_platform": []},
            "resources": resources,
            "providers": [
                {
                    "id": "test-provider",
                    "operation": operation.value,
                    "kind": "python",
                    "phase": phase,
                    "effect": effect.value,
                    "entrypoint": "payload:provider-code#run",
                    "input_schema": "provider-input",
                    "output_schema": "provider-output",
                    "resources": ["provider-data"],
                }
            ],
            "extensions": [extension.model_dump(mode="json") for extension in extensions],
        }
    )
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _invocation(repo: Path, payload: InstalledPayload) -> ProviderInvocation:
    return ProviderInvocation(
        repo=repo,
        payload=payload,
        standard_id="demo",
        version=payload.manifest.payload.version,
        provider_id="test-provider",
        operation=payload.manifest.providers[0].operation,
        effective_config={"mode": "strict"},
        snapshots={
            "README.md": {
                "kind": "missing",
                "precondition_digest": _digest(b"repo\n"),
            }
        },
    )


def _fix_invocation(
    repo: Path, payload: InstalledPayload, *, kind: str = "regular"
) -> ProviderInvocation:
    invocation = _invocation(repo, payload)
    return ProviderInvocation(
        repo=invocation.repo,
        payload=invocation.payload,
        standard_id=invocation.standard_id,
        version=invocation.version,
        provider_id=invocation.provider_id,
        operation=invocation.operation,
        effective_config=invocation.effective_config,
        snapshots={
            "documents": [
                {
                    "path": "README.md",
                    "kind": kind,
                    "precondition_digest": _digest(b"repo\n"),
                }
            ]
        },
    )


def _authoring_invocation(
    repo: Path,
    payload: InstalledPayload,
    *,
    kind: str,
    mode: str = "0644",
    overwrite: bool,
) -> ProviderInvocation:
    invocation = _invocation(repo, payload)
    return ProviderInvocation(
        repo=invocation.repo,
        payload=invocation.payload,
        standard_id=invocation.standard_id,
        version=invocation.version,
        provider_id=invocation.provider_id,
        operation=invocation.operation,
        effective_config=invocation.effective_config,
        snapshots={
            "authoring": {
                "target": "README.md",
                "kind": kind,
                "precondition_digest": _digest(b"repo\n"),
                "mode": mode,
                "overwrite": overwrite,
            }
        },
    )


def test_provider_is_selected_from_exact_integrity_checked_payload(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    v1 = _write_provider_payload(tmp_path / "payload-1", version="1.2")
    v2 = _write_provider_payload(tmp_path / "payload-2", version="2.0")

    first = invoke_provider(_invocation(repo, v1))
    second = invoke_provider(_invocation(repo, v2))

    assert first.content == b"1.2:1.2:declared-data"
    assert second.content == b"2.0:2.0:declared-data"
    assert first.output_notice == "provider output suppressed (stdout, stderr)"


def test_provider_rejects_operation_mismatch_before_invocation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(tmp_path / "payload")
    invocation = _invocation(repo, payload)

    with pytest.raises(ControlPlaneError, match="operation"):
        invoke_provider(
            ProviderInvocation(
                repo=invocation.repo,
                payload=invocation.payload,
                standard_id=invocation.standard_id,
                version=invocation.version,
                provider_id=invocation.provider_id,
                operation=ProviderOperation.VALIDATE,
                effective_config=invocation.effective_config,
                snapshots=invocation.snapshots,
            )
        )


@pytest.mark.parametrize(
    ("standard_id", "extension_id", "path", "message"),
    [
        ("other", "extra-rules", "rules.toml", "selected package"),
        ("demo", "undeclared", "rules.toml", "undeclared extension"),
        ("demo", "extra-rules", "other.toml", "configured path"),
    ],
)
def test_provider_rejects_unscoped_referenced_input_before_reading(
    tmp_path: Path,
    standard_id: str,
    extension_id: str,
    path: str,
    message: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "rules.toml").write_text("safe", encoding="utf-8")
    payload = _write_provider_payload(
        tmp_path / "payload",
        extensions=(_extension(preferred=False),),
    )
    invocation = _invocation(repo, payload)

    with pytest.raises(ControlPlaneError, match=message):
        invoke_provider(
            ProviderInvocation(
                repo=invocation.repo,
                payload=invocation.payload,
                standard_id=invocation.standard_id,
                version=invocation.version,
                provider_id=invocation.provider_id,
                operation=invocation.operation,
                effective_config={"extra_rules_file": "rules.toml"},
                snapshots={
                    "referenced_inputs": [
                        {
                            "standard_id": standard_id,
                            "extension_id": extension_id,
                            "path": path,
                            "digest": _digest(b"safe"),
                        }
                    ]
                },
            )
        )


@pytest.mark.parametrize(
    ("behavior", "message"),
    [
        ("wrong-output", "declared schema"),
        ("remote-schema", "reference must remain local"),
    ],
)
def test_provider_rejects_wrong_effect_shape_and_remote_schema_reference(
    tmp_path: Path,
    behavior: str,
    message: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(tmp_path / "payload", behavior=behavior)

    with pytest.raises(ControlPlaneError, match=message):
        invoke_provider(_invocation(repo, payload))


@pytest.mark.parametrize("behavior", ["mutate-input", "undeclared-resource"])
def test_provider_receives_immutable_input_and_only_declared_resource_bytes(
    tmp_path: Path,
    behavior: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(tmp_path / "payload", behavior=behavior)

    with pytest.raises(ControlPlaneError, match="provider failed"):
        invoke_provider(_invocation(repo, payload))


def test_provider_returns_typed_findings_mutation_plan_and_migration_report(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    findings_payload = _write_provider_payload(
        tmp_path / "findings",
        operation=ProviderOperation.VALIDATE,
        effect=ProviderEffect.FINDINGS,
    )
    plan_payload = _write_provider_payload(
        tmp_path / "plan",
        version="2.0",
        operation=ProviderOperation.FIX,
        effect=ProviderEffect.MUTATION_PLAN,
    )
    migration_payload = _write_provider_payload(
        tmp_path / "migration",
        version="2.0",
        operation=ProviderOperation.MIGRATE,
        effect=ProviderEffect.MIGRATION_REPORT,
    )

    findings = invoke_provider(_invocation(repo, findings_payload))
    plan = invoke_provider(_invocation(repo, plan_payload))
    migration = invoke_provider(_invocation(repo, migration_payload))

    assert findings.findings[0].code == "DEMO"
    assert findings.findings[0].standard_id == "demo"
    assert plan.mutation_plan is not None
    assert plan.mutation_plan.version.value == "2.0"
    assert migration.migration_report is not None
    assert migration.migration_report.package.version.value == "2.0"


def test_fix_mutation_plan_is_bound_to_immutable_document_snapshot(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(
        tmp_path / "plan",
        operation=ProviderOperation.FIX,
        effect=ProviderEffect.MUTATION_PLAN,
        behavior="valid-update",
    )

    result = invoke_provider(_fix_invocation(repo, payload))

    assert result.mutation_plan is not None
    assert result.mutation_plan.actions[0].target.original == "README.md"


@pytest.mark.parametrize(
    ("behavior", "message"),
    [
        ("undeclared-target", "undeclared target"),
        ("duplicate-target", "duplicate target"),
        ("wrong-precondition", "precondition"),
        ("create-over-regular", "action kind"),
        ("remove", "removal"),
        ("wrong-adapter", "whole-file"),
    ],
)
def test_fix_mutation_plan_rejects_actions_not_bound_to_document_snapshot(
    tmp_path: Path,
    behavior: str,
    message: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(
        tmp_path / behavior,
        operation=ProviderOperation.FIX,
        effect=ProviderEffect.MUTATION_PLAN,
        behavior=behavior,
    )

    with pytest.raises(ControlPlaneError, match=message):
        invoke_provider(_fix_invocation(repo, payload))


def test_fix_mutation_plan_allows_create_only_for_missing_snapshot(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(
        tmp_path / "create",
        operation=ProviderOperation.FIX,
        effect=ProviderEffect.MUTATION_PLAN,
        behavior="create-over-regular",
    )

    result = invoke_provider(_fix_invocation(repo, payload, kind="missing"))

    assert result.mutation_plan is not None
    assert result.mutation_plan.actions[0].kind.value == "create"


def test_authoring_mutation_plan_is_bound_to_mode_and_overwrite_authorization(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(
        tmp_path / "plan",
        operation=ProviderOperation.SCAFFOLD,
        effect=ProviderEffect.MUTATION_PLAN,
        behavior="valid-update",
    )

    result = invoke_provider(_authoring_invocation(repo, payload, kind="regular", overwrite=True))

    assert result.mutation_plan is not None
    assert result.mutation_plan.actions[0].mode == "0644"


@pytest.mark.parametrize(
    ("mode", "overwrite", "message"),
    [
        ("0600", True, "mode"),
        ("0644", False, "overwrite authorization"),
    ],
)
def test_authoring_mutation_plan_rejects_caller_authority_expansion(
    tmp_path: Path,
    mode: str,
    overwrite: bool,
    message: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(
        tmp_path / "plan",
        operation=ProviderOperation.SCAFFOLD,
        effect=ProviderEffect.MUTATION_PLAN,
        behavior="valid-update",
    )

    with pytest.raises(ControlPlaneError, match=message):
        invoke_provider(
            _authoring_invocation(
                repo,
                payload,
                kind="regular",
                mode=mode,
                overwrite=overwrite,
            )
        )


@pytest.mark.parametrize(
    ("behavior", "message", "hidden"),
    [
        ("undeclared-signature", "undeclared legacy signature", None),
        ("secret-config", "invalid report", "do-not-echo-this-value"),
    ],
)
def test_migration_provider_rejects_undeclared_signatures_and_secret_values(
    tmp_path: Path,
    behavior: str,
    message: str,
    hidden: str | None,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(
        tmp_path / "migration",
        operation=ProviderOperation.MIGRATE,
        effect=ProviderEffect.MIGRATION_REPORT,
        behavior=behavior,
    )

    with pytest.raises(ControlPlaneError, match=message) as caught:
        invoke_provider(_invocation(repo, payload))

    if hidden is not None:
        assert hidden not in str(caught.value)


@pytest.mark.parametrize("behavior", ["raise", "network"])
def test_provider_exception_and_denied_network_are_content_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    behavior: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(tmp_path / "payload", behavior=behavior)
    if behavior == "network":

        def deny_socket(*_args: object, **_kwargs: object) -> socket.socket:
            raise OSError("denied")

        monkeypatch.setattr(socket, "socket", deny_socket)

    with pytest.raises(ControlPlaneError) as exc_info:
        invoke_provider(_invocation(repo, payload))

    assert "private provider detail" not in str(exc_info.value)


def test_observed_live_write_is_integrity_incident_and_prior_lock_is_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    prior_lock = b"prior-lock"
    (repo / "lock.toml").write_bytes(prior_lock)
    payload = _write_provider_payload(tmp_path / "payload", behavior="write")
    monkeypatch.chdir(repo)

    with pytest.raises(ControlPlaneError, match="CP-PROVIDER-INTEGRITY"):
        invoke_provider(_invocation(repo, payload))

    assert (repo / "lock.toml").read_bytes() == prior_lock


def test_provider_integrity_checks_single_document_snapshot_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(tmp_path / "payload", behavior="write")
    invocation = _invocation(repo, payload)
    document_invocation = ProviderInvocation(
        repo=invocation.repo,
        payload=invocation.payload,
        standard_id=invocation.standard_id,
        version=invocation.version,
        provider_id=invocation.provider_id,
        operation=invocation.operation,
        effective_config=invocation.effective_config,
        snapshots={
            "document": {
                "path": "README.md",
                "kind": "missing",
                "precondition_digest": _digest(b"repo\n"),
            }
        },
    )
    monkeypatch.chdir(repo)

    with pytest.raises(ControlPlaneError, match="CP-PROVIDER-INTEGRITY"):
        invoke_provider(document_invocation)


def test_provider_integrity_checks_legacy_evidence_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(tmp_path / "payload", behavior="write")
    invocation = _invocation(repo, payload)
    legacy_invocation = ProviderInvocation(
        repo=invocation.repo,
        payload=invocation.payload,
        standard_id=invocation.standard_id,
        version=invocation.version,
        provider_id=invocation.provider_id,
        operation=invocation.operation,
        effective_config=invocation.effective_config,
        snapshots={"legacy_evidence": {"findings": [{"path": "README.md"}]}},
    )
    monkeypatch.chdir(repo)

    with pytest.raises(ControlPlaneError, match="CP-PROVIDER-INTEGRITY"):
        invoke_provider(legacy_invocation)


def test_provider_integrity_checks_preview_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _write_provider_payload(tmp_path / "payload", behavior="write")
    invocation = _invocation(repo, payload)
    preview_invocation = ProviderInvocation(
        repo=invocation.repo,
        payload=invocation.payload,
        standard_id=invocation.standard_id,
        version=invocation.version,
        provider_id=invocation.provider_id,
        operation=invocation.operation,
        effective_config=invocation.effective_config,
        snapshots={"preview": {"target": "README.md"}},
    )
    monkeypatch.chdir(repo)

    with pytest.raises(ControlPlaneError, match="CP-PROVIDER-INTEGRITY"):
        invoke_provider(preview_invocation)


def test_provider_integrity_checks_children_of_declared_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    sessions = repo / "docs/handoff/sessions"
    sessions.mkdir(parents=True)
    payload = _write_provider_payload(tmp_path / "payload", behavior="write-child")
    invocation = _invocation(repo, payload)
    directory_invocation = ProviderInvocation(
        repo=invocation.repo,
        payload=invocation.payload,
        standard_id=invocation.standard_id,
        version=invocation.version,
        provider_id=invocation.provider_id,
        operation=invocation.operation,
        effective_config=invocation.effective_config,
        snapshots={
            "docs/handoff/sessions": {
                "kind": "directory",
                "precondition_digest": _digest(b"directory"),
            }
        },
    )
    monkeypatch.chdir(repo)

    with pytest.raises(ControlPlaneError, match="CP-PROVIDER-INTEGRITY"):
        invoke_provider(directory_invocation)


def test_provider_integrity_check_does_not_scan_undeclared_repository_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "unrelated.txt").write_text("not a provider input\n", encoding="utf-8")
    payload = _write_provider_payload(tmp_path / "payload")

    def reject_recursive_scan(_path: Path, _pattern: str) -> object:
        raise AssertionError("provider runner scanned the repository")

    monkeypatch.setattr(Path, "rglob", reject_recursive_scan)

    result = invoke_provider(_invocation(repo, payload))

    assert result.content == b"1.2:1.2:declared-data"
