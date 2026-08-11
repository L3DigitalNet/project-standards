from __future__ import annotations

import hashlib
import json
import stat
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import project_standards.control_plane.planner as planner_runtime
import project_standards.control_plane.provider_subprocess as provider_subprocess
import project_standards.control_plane.providers as provider_runtime
from project_standards.control_plane.command_resolution import SelectedCommandPackage
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.provider_inputs import provider_dispatch_input
from project_standards.control_plane.provider_subprocess import (
    RESULT_LIMIT_BYTES,
    CapturedStream,
    ProviderSubprocessError,
    ProviderSubprocessOutcome,
    run_provider_subprocess,
)
from project_standards.control_plane.provider_worker import authoritative_provider_input
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
)
from project_standards.control_plane.schemas import control_plane_schema_documents
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import (
    JsonObject,
    PayloadManifest,
    ProviderEffect,
    ProviderOperation,
)
from tests.control_plane.planner_helpers import resolution_request, write_payload
from tests.control_plane.test_providers import provider_invocation, write_provider_payload


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _command_source(behavior: str, effect: ProviderEffect) -> bytes:
    success = (
        "resource = base64.b64decode(request['resources']['provider-data'], validate=True)\n"
        "result = {'content': request['schema_version'] + ':' + "
        "request['input']['version'] + ':' + resource.decode()}\n"
        if effect is ProviderEffect.CONTENT
        else "result = {'findings': []}\n"
    )
    action = {
        "success": success,
        "bad-output": "result = {'unexpected': 'shape'}\n",
        "diagnostic-path": (
            "os.write(2, b'/tmp/private-provider-path PRIVATE-CANARY\\n')\n"
            "result = {'content': 'safe'}\n"
        ),
        "nonzero": "result = {'content': 'must-not-publish'}\n",
        "slow": "time.sleep(2)\nresult = {'content': 'late'}\n",
    }[behavior]
    exit_line = "raise SystemExit(7)\n" if behavior == "nonzero" else ""
    return (
        "#!/usr/bin/python3\n"
        "import base64\nimport json\nimport os\nimport sys\nimport time\n"
        "request = json.load(sys.stdin)\n"
        f"{action}"
        "payload = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()\n"
        "os.write(int(sys.argv[1]), payload)\n"
        f"{exit_line}"
    ).encode()


def _command_payload(
    root: Path,
    *,
    behavior: str = "success",
    operation: ProviderOperation = ProviderOperation.RENDER,
    effect: ProviderEffect = ProviderEffect.CONTENT,
) -> InstalledPayload:
    original = write_provider_payload(root, operation=operation, effect=effect)
    source = _command_source(behavior, effect)
    source_path = root / "providers/run.py"
    source_path.write_bytes(source)
    raw = cast("dict[str, object]", original.manifest.model_dump(mode="json"))
    resources = cast("list[dict[str, object]]", raw["resources"])
    code = next(resource for resource in resources if resource["id"] == "provider-code")
    code["digest"] = _digest(source)
    code["media_type"] = "application/octet-stream"
    providers = cast("list[dict[str, object]]", raw["providers"])
    providers[0].update(
        {
            "kind": "command",
            "entrypoint": "payload:provider-code",
            "platforms": ["linux/amd64"],
            "mode": "0755",
        }
    )
    manifest = PayloadManifest.model_validate(raw)
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


command_payload = _command_payload


_PLAN_BOUND_CONTENT = b"command-provider-fixture|render|fixture-resource\n"
_PLAN_BOUND_TARGET = ".standards/command-provider-fixture.txt"
_PLAN_BOUND_PRECONDITION = "sha256:77ed2d5d1b55425244f0247ac95488fe1891e9667d98ce4c003790151fed6988"


def _plan_bound_command_source() -> bytes:
    return (
        b"#!/usr/bin/python3\n"
        b"import base64\nimport json\nimport os\nimport sys\n"
        b"request = json.load(sys.stdin)\n"
        b"provider_input = request['input']\n"
        b"fixture = base64.b64decode("
        b"request['resources']['fixture-data'], validate=True).decode().strip()\n"
        b"if provider_input['operation'] == 'render':\n"
        b"    result = {'content': f'command-provider-fixture|render|{fixture}\\n'}\n"
        b"else:\n"
        b"    snapshot = provider_input['snapshots']["
        b"'.standards/command-provider-fixture.txt']\n"
        b"    content = base64.b64decode(snapshot['content_base64'], validate=True)\n"
        b"    expected = f'command-provider-fixture|render|{fixture}\\n'.encode()\n"
        b"    result = {'findings': [] if content == expected else "
        b"[{'code': 'FIXTURE', 'severity': 'error', 'message': 'wrong content'}]}\n"
        b"payload = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()\n"
        b"os.write(int(sys.argv[1]), payload)\n"
    )


def _plan_bound_command_payload(root: Path) -> InstalledPayload:
    original = write_payload(
        root,
        "command-provider-fixture",
        contributions=[
            {
                "id": "render-fixture",
                "target": _PLAN_BOUND_TARGET,
                "adapter": "whole-file",
                "scope": "$file",
                "provider": "render-fixture",
            }
        ],
        render_providers=["render-fixture"],
        verify_providers=["verify-fixture"],
    )
    executable = _plan_bound_command_source()
    input_schema = json.dumps(
        control_plane_schema_documents()["provider-input.schema.json"],
        sort_keys=True,
    ).encode()
    output_schema = json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "oneOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"findings": {"type": "array"}},
                    "required": ["findings"],
                },
            ],
        },
        sort_keys=True,
    ).encode()
    files = {
        "providers/command": executable,
        "schemas/provider-input.json": input_schema,
        "schemas/provider-output.json": output_schema,
        "fixture-data.txt": b"fixture-resource\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    raw = cast("dict[str, object]", original.manifest.model_dump(mode="json"))
    resources = cast("list[dict[str, object]]", raw["resources"])
    resources.extend(
        [
            {
                "id": "provider-command",
                "role": "provider",
                "path": "providers/command",
                "media_type": "application/octet-stream",
                "digest": _digest(executable),
            },
            {
                "id": "provider-input",
                "role": "provider-input-schema",
                "path": "schemas/provider-input.json",
                "media_type": "application/schema+json",
                "digest": _digest(input_schema),
            },
            {
                "id": "provider-output",
                "role": "provider-output-schema",
                "path": "schemas/provider-output.json",
                "media_type": "application/schema+json",
                "digest": _digest(output_schema),
            },
            {
                "id": "fixture-data",
                "role": "provider-resource",
                "path": "fixture-data.txt",
                "media_type": "text/plain",
                "digest": _digest(files["fixture-data.txt"]),
            },
        ]
    )
    providers = cast("list[dict[str, object]]", raw["providers"])
    for declaration in providers:
        declaration.update(
            {
                "kind": "command",
                "entrypoint": "payload:provider-command",
                "input_schema": "provider-input",
                "output_schema": "provider-output",
                "resources": ["fixture-data"],
                "platforms": ["linux/amd64"],
                "mode": "0755",
            }
        )
    manifest = PayloadManifest.model_validate(raw)
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _plan_bound_selection(repo: Path, payload: InstalledPayload) -> SelectedCommandPackage:
    return cast(
        "SelectedCommandPackage",
        SimpleNamespace(repo=repo, payload=payload, distribution=object()),
    )


def test_plan_bound_command_input__command_render__uses_real_plan_then_target_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    target = repo / _PLAN_BOUND_TARGET
    target.parent.mkdir(parents=True)
    target.write_bytes(_PLAN_BOUND_CONTENT)
    target.chmod(0o644)
    payload = _plan_bound_command_payload(tmp_path / "payload")
    request = planner_runtime.PlannerRequest(
        repo=repo,
        resolution=resolution_request((payload,)),
        payloads=(payload,),
    )
    selected = _plan_bound_selection(repo, payload)
    plans: list[planner_runtime.ReconciliationPlan] = []
    planner_calls: list[ProviderInvocation] = []
    spawned: list[tuple[object, ...]] = []
    real_plan = planner_runtime.plan_reconciliation
    real_popen = provider_subprocess.subprocess.Popen

    def build_request(*_args: object, **_kwargs: object) -> planner_runtime.PlannerRequest:
        return request

    def record_plan(
        planner_request: planner_runtime.PlannerRequest,
    ) -> planner_runtime.ReconciliationPlan:
        plan = real_plan(planner_request)
        plans.append(plan)
        return plan

    def run_planning_provider(invocation: ProviderInvocation) -> ProviderResult:
        planner_calls.append(invocation)
        return invoke_provider(invocation)

    def counted_popen(*args: Any, **kwargs: Any) -> Any:
        spawned.append(args)
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(
        "project_standards.control_plane.cli.build_planner_request",
        build_request,
    )
    monkeypatch.setattr(planner_runtime, "plan_reconciliation", record_plan)
    monkeypatch.setattr(provider_subprocess.subprocess, "Popen", counted_popen)

    snapshots = authoritative_provider_input(
        selected,
        ProviderOperation.VERIFY,
        provider_id="verify-fixture",
        planner_runner=run_planning_provider,
    )

    assert len(plans) == 1
    assert [(call.provider_id, call.operation) for call in planner_calls] == [
        ("render-fixture", ProviderOperation.RENDER)
    ]
    assert planner_calls[0].snapshots == {
        _PLAN_BOUND_TARGET: {
            "kind": "regular",
            "precondition_digest": _PLAN_BOUND_PRECONDITION,
            "content_digest": _digest(_PLAN_BOUND_CONTENT),
            "mode": "0644",
        },
        "referenced_inputs": [],
        "planned_contribution": {
            "id": "render-fixture",
            "target": _PLAN_BOUND_TARGET,
            "adapter": "whole-file",
            "scope": "$file",
        },
    }
    assert snapshots == dict(
        provider_dispatch_input(
            None,
            ProviderOperation.VERIFY,
            repo=repo,
            standard_id="command-provider-fixture",
            plan=plans[0],
            provider_id="verify-fixture",
        )
    )
    assert snapshots is not None
    assert cast("dict[str, object]", snapshots[_PLAN_BOUND_TARGET])["content_digest"] == _digest(
        _PLAN_BOUND_CONTENT
    )
    assert len(spawned) == 1
    assert all(call.provider_id != "verify-fixture" for call in planner_calls)

    verification = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="command-provider-fixture",
            version=PackageVersion("1.0"),
            provider_id="verify-fixture",
            operation=ProviderOperation.VERIFY,
            effective_config={},
            snapshots=cast(JsonObject, snapshots),
        )
    )

    assert verification.findings == ()
    assert len(spawned) == 2


def test_command_provider_receives_canonical_input_and_declared_resource_bytes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _command_payload(tmp_path / "payload")

    result = invoke_provider(provider_invocation(repo, payload))

    assert result.content == b"1.0:1.2:declared-data"


def test_command_provider_materializes_verified_bytes_at_0755_with_closed_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _command_payload(tmp_path / "payload")
    installed = payload.root / "providers/run.py"
    observed_path: Path | None = None

    def run(
        argv: tuple[str, ...],
        request: bytes,
        *,
        timeout: float,
        environment: dict[str, str],
        validate_status: bool = True,
    ) -> ProviderSubprocessOutcome:
        nonlocal observed_path
        assert timeout == 30
        assert not validate_status
        assert environment == {}
        assert len(argv) == 1
        observed_path = Path(argv[0])
        assert observed_path != installed
        assert observed_path.read_bytes() == installed.read_bytes()
        assert stat.S_IMODE(observed_path.stat().st_mode) == 0o755
        assert _digest(observed_path.read_bytes()) == _digest(installed.read_bytes())
        decoded = json.loads(request)
        assert list(decoded) == ["input", "resources", "schema_version"]
        assert decoded["schema_version"] == "1.0"
        assert set(decoded["resources"]) == {"provider-data"}
        assert (
            request
            == json.dumps(
                decoded,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
        )
        return ProviderSubprocessOutcome(
            cast(JsonObject, {"content": "ok"}),
            CapturedStream("stdout", 8192),
            CapturedStream("stderr", 8192),
            0,
        )

    monkeypatch.setattr(provider_runtime, "run_provider_subprocess", run)

    result = invoke_provider(provider_invocation(repo, payload))

    assert result.content == b"ok"
    assert observed_path is not None
    assert not observed_path.exists()
    assert installed.exists()


def test_command_provider_refuses_unsupported_platform_before_materialization_or_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _command_payload(tmp_path / "payload")
    spawned = False

    def reject_spawn(*_args: object, **_kwargs: object) -> ProviderSubprocessOutcome:
        nonlocal spawned
        spawned = True
        raise AssertionError("unsupported platform spawned")

    monkeypatch.setattr(provider_runtime, "_host_command_platform", lambda: "linux/arm64")
    monkeypatch.setattr(provider_runtime, "run_provider_subprocess", reject_spawn)

    with pytest.raises(ControlPlaneError, match="unsupported command provider platform") as raised:
        invoke_provider(provider_invocation(repo, payload))

    assert not spawned
    assert str(payload.root) not in str(raised.value)


@pytest.mark.parametrize(
    ("behavior", "message"),
    [
        ("bad-output", "declared schema"),
        ("nonzero", "nonzero status"),
    ],
)
def test_command_provider_rejects_invalid_output_or_nonzero_exit(
    tmp_path: Path,
    behavior: str,
    message: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _command_payload(tmp_path / "payload", behavior=behavior)

    with pytest.raises(ControlPlaneError, match=message):
        invoke_provider(provider_invocation(repo, payload))


def test_command_provider_redacts_untrusted_path_diagnostics(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _command_payload(tmp_path / "payload", behavior="diagnostic-path")

    result = invoke_provider(provider_invocation(repo, payload))

    assert result.content == b"safe"
    assert result.output_notice == (
        "the failure detail was withheld because it named a filesystem path"
    )
    assert "PRIVATE-CANARY" not in result.output_notice


def test_command_provider_honors_shared_execution_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _command_payload(tmp_path / "payload", behavior="slow")
    monkeypatch.setattr(provider_runtime, "PROVIDER_TIMEOUT_SECONDS", 0.1)

    with pytest.raises(ControlPlaneError, match="execution bound"):
        invoke_provider(provider_invocation(repo, payload))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"content":"first","content":"second"}',
        b'{"content":"value"} trailing',
        b"\xff",
        b"[]",
    ],
)
def test_command_result_rejects_duplicate_trailing_non_utf8_or_non_object(
    raw: bytes,
) -> None:
    source = "import os,sys; os.write(int(sys.argv[1]), " + repr(raw) + ")"

    with pytest.raises(ProviderSubprocessError, match="result"):
        run_provider_subprocess(
            (sys.executable, "-c", source),
            b"",
            timeout=5,
            environment={},
            validate_status=False,
        )


@pytest.mark.parametrize("extra", [0, 1])
def test_command_result_uses_exact_shared_transport_cap(extra: int) -> None:
    prefix = b'{"content":"'
    suffix = b'"}'
    source = (
        "import os,sys; "
        f"raw={prefix!r}+b'x'*({RESULT_LIMIT_BYTES}-{len(prefix)}-{len(suffix)}+{extra})+"
        f"{suffix!r}; os.write(int(sys.argv[1]), raw)"
    )

    if extra:
        with pytest.raises(ProviderSubprocessError, match="transport limit"):
            run_provider_subprocess(
                (sys.executable, "-c", source),
                b"",
                timeout=5,
                environment={},
                validate_status=False,
            )
    else:
        outcome = run_provider_subprocess(
            (sys.executable, "-c", source),
            b"",
            timeout=5,
            environment={},
            validate_status=False,
        )
        assert len(cast(str, outcome.frame["content"])) == (
            RESULT_LIMIT_BYTES - len(prefix) - len(suffix)
        )
