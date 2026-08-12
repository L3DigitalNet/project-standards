"""Cross-package control-plane proof for runner-label reachability advisories.

The three unadvertised successors must carry their warnings through the real
plan/apply boundary without changing the selected release or self-host sources.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import (
    ControlFinding,
    findings_to_jsonable,
)
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, ApplyResult, apply_reconciliation
from project_standards.control_plane.planner import (
    PlannerRequest,
    ReconciliationPlan,
    VerificationRequest,
    plan_reconciliation,
)
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
)
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    load_payload_manifest,
)
from tests.control_plane.planner_helpers import resolution_request

_ROOT = Path(__file__).resolve().parents[2]
_LABELS: list[JsonValue] = ["self-hosted", "linux", "x64", "l3digital-private"]
_VERSIONS = {
    "markdown-frontmatter": "1.11",
    "markdown-tooling": "1.15",
    "project-spec": "1.9",
}
_VERIFICATION_REQUESTS = (
    VerificationRequest("markdown-frontmatter", "1.11", "verify-runner-labels"),
    VerificationRequest("markdown-tooling", "1.15", "verify-format"),
    VerificationRequest("markdown-tooling", "1.15", "verify-lint"),
    VerificationRequest("project-spec", "1.9", "verify-runner-labels"),
)
_WARNING_IDENTITIES = (
    (
        "FM-RUNNER-LABELS-UNREACHABLE",
        "markdown-frontmatter",
        "1.11",
        ".github/workflows/validate-standards.yml",
        "key:/jobs/frontmatter",
    ),
    (
        "MT-RUNNER-LABELS-UNREACHABLE",
        "markdown-tooling",
        "1.15",
        ".github/workflows/format.yml",
        "$file",
    ),
    (
        "MT-RUNNER-LABELS-UNREACHABLE",
        "markdown-tooling",
        "1.15",
        ".github/workflows/lint-markdown.yml",
        "$file",
    ),
    (
        "PS-RUNNER-LABELS-UNREACHABLE",
        "project-spec",
        "1.9",
        ".github/workflows/validate-specs.yml",
        "$file",
    ),
)


def _payload(standard_id: str, version: str) -> InstalledPayload:
    root = _ROOT / "standards" / standard_id / "versions" / version
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _config(**values: JsonValue) -> JsonObject:
    return dict(values)


def _plan(
    tmp_path: Path,
    configs: Mapping[str, JsonObject],
) -> tuple[PlannerRequest, ReconciliationPlan]:
    repo = tmp_path / "repo"
    repo.mkdir()
    payloads = tuple(_payload(standard_id, version) for standard_id, version in _VERSIONS.items())
    request = PlannerRequest(
        repo,
        resolution_request(
            payloads,
            configs=configs,
            selected_versions=_VERSIONS,
        ),
        payloads,
    )
    control = repo / ".standards"
    control.mkdir()
    (control / "lock.toml").write_bytes(render_lock(request.resolution.previous_lock))
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert plan.verification_requests == _VERIFICATION_REQUESTS
    return request, plan


def _apply(
    tmp_path: Path,
    configs: Mapping[str, JsonObject],
    *,
    verification_runner: Callable[[ProviderInvocation], ProviderResult] | None = None,
) -> ApplyResult:
    request, plan = _plan(tmp_path, configs)
    if verification_runner is None:
        return apply_reconciliation(ApplyRequest(request, plan))
    return apply_reconciliation(
        ApplyRequest(
            request,
            plan,
            verification_runner=verification_runner,
        )
    )


def _unreachable_configs(state: str) -> dict[str, JsonObject]:
    if state == "consumer-owned":
        return {
            "markdown-frontmatter": _config(
                workflow_ownership="consumer-owned", runner_labels=_LABELS
            ),
            "markdown-tooling": _config(
                lint_workflow_ownership="consumer-owned",
                format_workflow_ownership="consumer-owned",
                runner_labels=_LABELS,
            ),
            "project-spec": _config(workflow_ownership="consumer-owned", runner_labels=_LABELS),
        }
    assert state == "self-hosted"
    return {
        standard_id: _config(workflow_mode="self-hosted", runner_labels=_LABELS)
        for standard_id in _VERSIONS
    }


def _safe_configs(case: str) -> dict[str, JsonObject]:
    if case == "consumer-owned-empty":
        return {
            "markdown-frontmatter": _config(workflow_ownership="consumer-owned", runner_labels=[]),
            "markdown-tooling": _config(
                lint_workflow_ownership="consumer-owned",
                format_workflow_ownership="consumer-owned",
                runner_labels=[],
            ),
            "project-spec": _config(workflow_ownership="consumer-owned", runner_labels=[]),
        }
    if case == "self-hosted-empty":
        return {
            standard_id: _config(workflow_mode="self-hosted", runner_labels=[])
            for standard_id in _VERSIONS
        }
    if case == "managed-with-labels":
        return {standard_id: _config(runner_labels=_LABELS) for standard_id in _VERSIONS}
    assert case == "disabled-markdown-callers"
    return {
        "markdown-frontmatter": _config(runner_labels=_LABELS),
        "markdown-tooling": _config(
            lint=False,
            format=False,
            ci=_config(lint_caller=False, format_caller=False),
            lint_workflow_ownership="consumer-owned",
            format_workflow_ownership="consumer-owned",
            runner_labels=_LABELS,
        ),
        "project-spec": _config(runner_labels=_LABELS),
    }


def _finding_identities(
    findings: tuple[ControlFinding, ...],
) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple(
        (finding.code, finding.standard_id, finding.version, finding.path, finding.identity)
        for finding in findings
    )


@pytest.mark.parametrize("state", ["consumer-owned", "self-hosted"])
def test_runner_label_advisory__unreachable_states__apply_with_exact_ordered_warnings(
    tmp_path: Path,
    state: str,
) -> None:
    result = _apply(tmp_path, _unreachable_configs(state))

    assert result.success
    assert result.error_code is None
    assert _finding_identities(result.verification_findings) == _WARNING_IDENTITIES
    assert all(finding.severity == "warning" for finding in result.verification_findings)
    reason = "consumer-owned" if state == "consumer-owned" else "self-hosted"
    remedy = "pass runner-labels" if state == "consumer-owned" else "pin its runs-on"
    assert all(reason in finding.message for finding in result.verification_findings)
    assert all(remedy in finding.hint for finding in result.verification_findings)

    serialized = findings_to_jsonable(result.verification_findings)
    round_tripped = cast("list[dict[str, object]]", json.loads(json.dumps(serialized)))
    assert [item["code"] for item in round_tripped] == [item[0] for item in _WARNING_IDENTITIES]
    assert [item["severity"] for item in round_tripped] == ["warning"] * 4


@pytest.mark.parametrize(
    "case",
    [
        "consumer-owned-empty",
        "self-hosted-empty",
        "managed-with-labels",
        "disabled-markdown-callers",
    ],
)
def test_runner_label_advisory__reachable_empty_or_disabled_controls__stay_silent(
    tmp_path: Path,
    case: str,
) -> None:
    result = _apply(tmp_path, _safe_configs(case))

    assert result.success
    assert result.error_code is None
    assert result.verification_findings == ()


def test_runner_label_advisory__mixed_markdown_ownership__warns_once(tmp_path: Path) -> None:
    configs = _safe_configs("managed-with-labels")
    configs["markdown-tooling"] = _config(
        lint_workflow_ownership="consumer-owned",
        format_workflow_ownership="managed",
        runner_labels=_LABELS,
    )

    result = _apply(tmp_path, configs)

    assert result.success
    assert _finding_identities(result.verification_findings) == (_WARNING_IDENTITIES[2],)


def test_runner_label_advisory__existing_error__still_fails_apply(tmp_path: Path) -> None:
    def inject_existing_drift(invocation: ProviderInvocation) -> ProviderResult:
        if invocation.standard_id == "markdown-tooling" and invocation.provider_id == "verify-lint":
            snapshots = dict(invocation.snapshots)
            snapshots[".markdownlint.json"] = {"kind": "absent"}
            invocation = replace(invocation, snapshots=snapshots)
        return invoke_provider(invocation)

    result = _apply(
        tmp_path,
        _unreachable_configs("consumer-owned"),
        verification_runner=inject_existing_drift,
    )

    assert not result.success
    assert result.error_code == "CP-VERIFY"
    assert [finding.code for finding in result.verification_findings].count("MT-LINT-DRIFT") == 1
    assert (
        _finding_identities(
            tuple(
                finding for finding in result.verification_findings if finding.severity == "warning"
            )
        )
        == _WARNING_IDENTITIES
    )


def test_runner_label_advisory__release_and_self_host_selections__stay_unchanged() -> None:
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    packages = cast("list[dict[str, object]]", catalog["packages"])
    advertised = {
        (str(package["id"]), str(package["version"])): str(package["role"]) for package in packages
    }
    assert advertised[("markdown-frontmatter", "1.10")] == "retained"
    assert advertised[("markdown-frontmatter", "1.11")] == "default"
    assert advertised[("markdown-tooling", "1.14")] == "retained"
    assert advertised[("markdown-tooling", "1.15")] == "default"
    assert advertised[("project-spec", "1.8")] == "retained"
    assert advertised[("project-spec", "1.9")] == "default"

    lock = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    standards = cast("dict[str, dict[str, object]]", lock["standards"])
    assert {standard_id: standards[standard_id]["resolved"] for standard_id in _VERSIONS} == {
        "markdown-frontmatter": "1.11",
        "markdown-tooling": "1.15",
        "project-spec": "1.9",
    }
    artifacts = cast("list[dict[str, object]]", lock["artifacts"])
    workflow_versions = {
        str(artifact["path"]): artifact["versions"]
        for artifact in artifacts
        if artifact["path"]
        in {
            ".github/workflows/format.yml",
            ".github/workflows/lint-markdown.yml",
            ".github/workflows/validate-markdown-frontmatter.yml",
            ".github/workflows/validate-specs.yml",
        }
    }
    assert workflow_versions == {
        ".github/workflows/format.yml": {"markdown-tooling": "1.15"},
        ".github/workflows/lint-markdown.yml": {"markdown-tooling": "1.15"},
        ".github/workflows/validate-markdown-frontmatter.yml": {"markdown-frontmatter": "1.11"},
        ".github/workflows/validate-specs.yml": {"project-spec": "1.9"},
    }

    rendered = (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
    for standard_id, version in _VERSIONS.items():
        assert (
            f"| [`{standard_id}`]({standard_id}/README.md) | active | {version} | "
            "default | consumer |"
        ) in rendered
