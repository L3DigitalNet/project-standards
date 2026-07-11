from __future__ import annotations

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
        body = "Path('provider-wrote.txt').write_text('bad', encoding='utf-8')\n    return {'content': 'bad'}"
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
        snapshots={"README.md": {"digest": _digest(b"repo\n")}},
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
