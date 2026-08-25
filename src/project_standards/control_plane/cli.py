"""Consumer reconciliation command with stable human and JSON reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn, cast

from project_standards.control_plane.catalog_refresh import (
    CatalogAdvance,
    CatalogRefreshPlan,
    plan_catalog_refresh,
)
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlFinding,
    ControlPlaneError,
    _MajorAuthorizationError,  # pyright: ignore[reportPrivateUsage]  # package-internal classification
    findings_to_jsonable,
)
from project_standards.control_plane.distribution import (
    InstalledDistribution,
    declared_transitions,
    resolution_payloads,
)
from project_standards.control_plane.executor import (
    ApplyRequest,
    ManagedRestoreApplyRequest,
    apply_managed_restore,
    apply_reconciliation,
)
from project_standards.control_plane.locking import ControlPlaneBusyError
from project_standards.control_plane.models import CentralLock
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.planner import (
    ManagedRestorePlan,
    PlannerRequest,
    ReconciliationPlan,
    plan_managed_restore,
    plan_reconciliation,
)
from project_standards.control_plane.recovery import (
    RecoveryPlan,
    RecoveryRequest,
    apply_recovery,
    plan_recovery,
)
from project_standards.control_plane.resolution import (
    MajorAuthorization,
    ResolutionRequest,
)
from project_standards.control_plane.state import (
    ControlPlaneState,
    StateKind,
    detect_control_plane_state,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.payload import (
    ProviderEffect,
    ProviderOperation,
)


class _ArgumentError(ValueError):
    """Prevent argparse from terminating the embedding process."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgumentError(message)


def _major_authorization(value: str) -> MajorAuthorization:
    standard_id, separator, raw_major = value.rpartition("@")
    if not separator:
        raise argparse.ArgumentTypeError("authorization must use STANDARD_ID@MAJOR")
    try:
        return MajorAuthorization(standard_id, int(raw_major))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "authorization must use STANDARD_ID@positive-major"
        ) from exc


def _parser() -> _Parser:
    parser = _Parser(prog="project-standards reconcile")
    parser.add_argument("--check", action="store_true", help="report drift without applying it")
    parser.add_argument("--apply", action="store_true", help="apply a conflict-free current plan")
    parser.add_argument(
        "--restore-managed",
        action="append",
        default=[],
        metavar="PATH",
        help="preview exact lock-backed restoration of one exclusively managed whole file",
    )
    parser.add_argument(
        "--allow-major",
        action="append",
        default=[],
        type=_major_authorization,
        metavar="STANDARD_ID@MAJOR",
        help="authorize one exact package and target major for this invocation",
    )
    parser.add_argument(
        "--repair-state",
        action="store_true",
        help="plan or explicitly apply sanctioned incomplete-state recovery",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="emit one structured result")
    return parser


def build_planner_request(
    repo: Path,
    distribution: InstalledDistribution,
    allowed_majors: frozenset[MajorAuthorization],
    *,
    state: ControlPlaneState | None = None,
    advance: CatalogAdvance = CatalogAdvance.NON_ADVANCING,
) -> PlannerRequest:
    """Assemble the one frozen planner request every command resolves against.

    This is the single seam where the advancing/non-advancing split is declared
    (issue #123). The default is non-advancing because building a request is a
    pure read: it resolves selections and describes the pending refresh without
    writing anything. Only the callers that go on to publish the installed
    catalog — the `--apply` routes below — pass `CatalogAdvance.ADVANCING`, which
    is what makes them, and only them, refuse over release lineage.
    """
    selected_state = state or detect_control_plane_state(
        repo, tool_release=distribution.tool_release.value
    )
    if (
        selected_state.kind is not StateKind.INITIALIZED
        or selected_state.config is None
        or selected_state.catalog is None
        or selected_state.lock is None
    ):
        raise ControlPlaneError(
            selected_state.detail or f"control-plane state is {selected_state.kind.value}",
            path=(
                f".standards/{selected_state.malformed_file}"
                if selected_state.malformed_file is not None
                else None
            ),
            line=selected_state.line,
            column=selected_state.column,
        )
    installed = distribution.load_catalog(
        selected_state.config.project_standards.catalog,
        recorded_release=selected_state.catalog.project_standards.release,
    )
    refresh = plan_catalog_refresh(
        selected_state.catalog,
        distribution.consumer_catalog(
            selected_state.config.project_standards.catalog,
            installed=installed,
        ),
        selected_state.config,
        selected_state.lock,
        advance=advance,
    )
    resolution = ResolutionRequest(
        desired=selected_state.config,
        catalog=refresh.installed,
        previous_lock=selected_state.lock,
        allowed_majors=allowed_majors,
        payloads=resolution_payloads(installed),
        transition_paths=declared_transitions(installed),
    )
    return PlannerRequest(
        selected_state.repo,
        resolution,
        installed.payloads,
        catalog_refresh=refresh,
    )


def run_render(
    argv: list[str] | None = None,
    *,
    distribution: InstalledDistribution | None = None,
) -> int:
    """Render one selected package provider to stdout without planning changes."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _Parser(prog="project-standards render")
    parser.add_argument("standard_id", metavar="STANDARD_ID")
    parser.add_argument("provider_id", metavar="PROVIDER_ID")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(arguments)
    except (_ArgumentError, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code == 0:
            return 0
        message = str(exc) if isinstance(exc, _ArgumentError) else "invalid arguments"
        return _emit_error("--json" in arguments, "CP-ARGUMENT", message, exit_code=2)

    json_mode = cast("bool", args.json)
    standard_id = cast("str", args.standard_id)
    provider_id = cast("str", args.provider_id)
    from project_standards.control_plane.command_resolution import (
        invoke_selected_provider,
        selected_command,
    )
    from project_standards.control_plane.locking import LockMode

    try:
        repo = cast("Path", args.repo).resolve()
        with selected_command(
            repo,
            standard_id,
            distribution,
            mode=LockMode.READ,
            require_reconciled=False,
        ) as selected:
            if selected is None:
                raise ControlPlaneError("render requires unified package authority")
            result = invoke_selected_provider(
                selected,
                ProviderOperation.RENDER,
                {},
                provider_id=provider_id,
            )
        if result.effect is not ProviderEffect.CONTENT or result.content is None:
            raise ControlPlaneError("render provider did not return content")
        try:
            content = result.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ControlPlaneError("render provider content is not UTF-8 text") from exc
        if json_mode:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "standard_id": standard_id,
                        "provider_id": provider_id,
                        "content": content,
                    },
                    indent=2,
                )
            )
        else:
            sys.stdout.write(content)
        return 0
    except ControlPlaneBusyError as exc:
        return _emit_error(json_mode, exc.code, str(exc), exit_code=1)
    except ControlPlaneError as exc:
        return _emit_error(json_mode, "CP-RENDER", exc, exit_code=2)
    except (PackageContractError, OSError, RuntimeError, ValueError) as exc:
        return _emit_error(json_mode, "CP-RENDER", str(exc), exit_code=2)


def _drift(plan: ReconciliationPlan, previous_lock: CentralLock) -> bool:
    mutating = {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
    return (
        any(action.kind in mutating for action in plan.actions) or plan.next_lock != previous_lock
    )


def _emit_error(
    json_mode: bool,
    code: str,
    error: str | ControlPlaneError,
    *,
    exit_code: int,
) -> int:
    message = str(error)
    if isinstance(error, ControlPlaneError) and error.code is not None:
        # A raiser that knows its own code outranks the command-level generic
        # one: a containment-destination refusal must not be reported as plain
        # CP-CONTROL-STATE just because it surfaced through a state read.
        code = error.code
    if json_mode:
        payload: dict[str, object] = {"ok": False, "code": code, "error": message}
        if isinstance(error, ControlPlaneError):
            payload.update(error.to_jsonable())
        print(json.dumps(payload, indent=2))
    else:
        print(f"error: {message}", file=sys.stderr)
    return exit_code


def _bounded_excerpt(value: object) -> str:
    """Render a single-line JSON excerpt capped for terminal output; JSON keeps full fidelity."""
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 120 else f"{text[:120]}…"


def _format_human_finding(finding: ControlFinding) -> str:
    """Render one actionable finding without exposing internal target sentinels."""
    path = finding.path or "."
    location = path
    if finding.line is not None:
        location += f":{finding.line}"
        if finding.column is not None:
            location += f":{finding.column}"
    identity = "" if finding.identity in {"$file", "$target"} else f" [{finding.identity}]"
    lines = [f"{finding.severity.upper()} {finding.code} {location}{identity}: {finding.message}"]
    if finding.locus is not None:
        lines.append(f"  locus: {finding.locus}")
    if finding.observed is not None:
        lines.append(f"  observed: {finding.observed}")
    if finding.limit is not None:
        lines.append(f"  limit: {finding.limit}")
    if finding.expected is not None or "expected" in finding.null_values:
        lines.append(f"  expected: {_bounded_excerpt(finding.expected)}")
    elif finding.expected_digest is not None:
        lines.append(f"  expected digest: {finding.expected_digest}")
    if finding.actual is not None or "actual" in finding.null_values:
        lines.append(f"  actual: {_bounded_excerpt(finding.actual)}")
    elif finding.actual_digest is not None:
        lines.append(f"  actual digest: {finding.actual_digest}")
    # 5.8.0 FR-012 / SPEC-CP01: the excerpt is pre-bounded package-side text; emit
    # it verbatim (no consumer bytes here) under the digest lines. Actual content
    # is never rendered — only its digest above.
    if finding.first_difference_line is not None:
        lines.append(f"  first difference: line {finding.first_difference_line}")
        lines.append(f"  expected: {finding.first_difference_expected or ''}")
    if finding.governing_options is not None:
        rendered = ", ".join(finding.governing_options) or "none declared"
        lines.append(f"  governing options: {rendered}")
    lines.append(f"  hint: {finding.hint}")
    return "\n".join(lines)


def _emit_human_findings(findings: tuple[ControlFinding, ...]) -> None:
    rendered: set[str] = set()
    for finding in findings:
        text = _format_human_finding(finding)
        if text in rendered:
            continue
        rendered.add(text)
        print(text, file=sys.stderr)


def _lock_only_drift_findings(
    plan: ReconciliationPlan,
    previous_lock: CentralLock,
) -> tuple[ControlFinding, ...]:
    if not _drift(plan, previous_lock) or any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in plan.actions
    ):
        return ()
    preserved = sorted(
        {action.target for action in plan.actions if action.kind is ActionKind.PRESERVE}
    )
    paths = preserved or [".standards/lock.toml"]
    return tuple(
        ControlFinding(
            code="CP-DRIFT",
            severity="warning",
            standard_id="project-standards",
            version="",
            path=path,
            identity="$target",
            message="reconciliation must refresh lock metadata without changing this preserved target",
            hint="run reconcile --apply to publish the refreshed lock metadata",
        )
        for path in paths
    )


def _apply_failure_message(
    error_code: str | None,
    *,
    operation: str,
    preview_command: str,
) -> str:
    code = error_code or "CP-APPLY-FAILED"
    if code in {"CP-STALE-PLAN", "CP-PRECONDITION"}:
        return (
            f"error: {operation} failed ({code}); the reviewed plan no longer matches "
            "the current repository state; "
            f"rerun {preview_command} and retry the apply"
        )
    return (
        f"error: {operation} failed ({code}); resolve the reported state, "
        f"rerun {preview_command}, and retry the apply"
    )


def _inspect_tool_mismatch(
    state: ControlPlaneState,
    *,
    apply: bool,
    json_mode: bool,
) -> int:
    detail = state.detail or "installed tool major does not match configured catalog major"
    if apply:
        return _emit_error(
            json_mode,
            "CP-CATALOG-MAJOR-MISMATCH",
            detail,
            exit_code=2,
        )
    if state.catalog is None:
        return _emit_error(json_mode, "CP-CONTROL-STATE", detail, exit_code=2)
    header = state.catalog.project_standards
    if json_mode:
        print(
            json.dumps(
                {
                    "ok": False,
                    "mode": "inspection",
                    "state": state.kind.value,
                    "mutable": False,
                    "catalog": {
                        "major": header.catalog.value,
                        "release": header.release,
                    },
                    "error": detail,
                },
                indent=2,
            )
        )
    else:
        print(
            f"Inspection only: catalog {header.catalog.value} at {header.release}; {detail}.",
            file=sys.stderr,
        )
    return 1


def _migration_plan_payload(
    plan: object,
    *,
    mode: str,
    apply_refused: bool = False,
) -> dict[str, object]:
    from project_standards.control_plane.migration import LegacyMigrationPlan

    if not isinstance(plan, LegacyMigrationPlan):
        raise TypeError("migration report requires a legacy migration plan")
    payload: dict[str, object] = {
        "ok": plan.applicable,
        "mode": mode,
        "applicable": plan.applicable,
        "plan": plan.to_jsonable(),
    }
    if apply_refused:
        payload.update({"apply_refused": True, "writes_performed": False})
    return payload


def _emit_migration_plan(
    plan: object,
    *,
    mode: str,
    json_mode: bool,
    apply_refused: bool = False,
) -> int:
    from project_standards.control_plane.migration import LegacyMigrationPlan

    if not isinstance(plan, LegacyMigrationPlan):
        raise TypeError("migration report requires a legacy migration plan")
    if json_mode:
        print(
            json.dumps(
                _migration_plan_payload(
                    plan,
                    mode=mode,
                    apply_refused=apply_refused,
                ),
                indent=2,
            )
        )
    else:
        for action in plan.actions:
            print(f"{action.kind.value:<8} {action.target}  {action.summary}")
        _emit_human_findings(plan.findings)
        if apply_refused:
            print(
                "error: migration apply refused because the plan is not applicable; "
                "no repository writes were performed",
                file=sys.stderr,
            )
    # Exit mirrors the JSON `ok`/`applicable` readiness signal: an applicable,
    # error-free preview succeeds; blocked plans and refused applies stay nonzero.
    return 0 if plan.applicable and not apply_refused else 1


def run_init(
    argv: list[str] | None = None,
    *,
    distribution: InstalledDistribution | None = None,
) -> int:
    """Initialize neutral state or explicitly preview/apply legacy migration."""
    from project_standards.control_plane.bootstrap import initialize_control_plane
    from project_standards.control_plane.migration import (
        apply_legacy_migration,
        plan_legacy_migration,
        plan_legacy_migration_recovery,
    )

    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _Parser(prog="project-standards init")

    def catalog_major(value: str) -> CatalogMajor:
        try:
            return CatalogMajor(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                "catalog must be a canonical positive integer"
            ) from exc

    parser.add_argument("--catalog", required=True, type=catalog_major)
    parser.add_argument("--migrate", action="store_true", help="preview legacy migration")
    parser.add_argument("--apply", action="store_true", help="apply an explicit migration")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(arguments)
    except (_ArgumentError, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code == 0:
            return 0
        message = str(exc) if isinstance(exc, _ArgumentError) else "invalid arguments"
        return _emit_error("--json" in arguments, "CP-ARGUMENT", message, exit_code=2)

    json_mode = cast("bool", args.json)
    if cast("bool", args.apply) and not cast("bool", args.migrate):
        return _emit_error(
            json_mode,
            "CP-ARGUMENT",
            "--apply requires --migrate",
            exit_code=2,
        )
    repo = cast("Path", args.repo).resolve()
    major = cast("CatalogMajor", args.catalog)
    try:
        selected_distribution = distribution or InstalledDistribution.current()
        if not cast("bool", args.migrate):
            result = initialize_control_plane(
                repo,
                major,
                distribution=selected_distribution,
            )
            if json_mode:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "created": result.created,
                            "repo": str(result.repo),
                            "files": [f".standards/{name}" for name in result.files],
                        },
                        indent=2,
                    )
                )
            else:
                action = "Initialized" if result.created else "OK"
                print(f"{action} standards control plane: {result.repo / '.standards'}")
            return 0

        state = detect_control_plane_state(
            repo,
            tool_release=selected_distribution.tool_release.value,
        )
        if state.kind is StateKind.INITIALIZED:
            if (
                state.config is None
                or state.catalog is None
                or state.config.project_standards.catalog != major
                or selected_distribution.consumer_catalog(major) != state.catalog
            ):
                return _emit_error(
                    json_mode,
                    "CP-MIGRATION-STATE",
                    "initialized control plane does not match the requested catalog",
                    exit_code=2,
                )
            if json_mode:
                print(json.dumps({"ok": True, "mode": "migration-noop"}, indent=2))
            else:
                print("OK legacy migration is already complete")
            return 0
        if state.kind is StateKind.LEGACY_ONLY:
            plan = plan_legacy_migration(repo, selected_distribution, major)
            mode = "migration-plan"
        elif state.kind is StateKind.DUAL_AUTHORITY:
            plan = plan_legacy_migration_recovery(repo, selected_distribution, major)
            mode = "migration-recovery-plan"
        else:
            return _emit_error(
                json_mode,
                "CP-MIGRATION-STATE",
                state.detail or f"control-plane state is {state.kind.value}",
                exit_code=2,
            )
        if not cast("bool", args.apply):
            return _emit_migration_plan(plan, mode=mode, json_mode=json_mode)
        if not plan.applicable:
            return _emit_migration_plan(
                plan,
                mode=mode,
                json_mode=json_mode,
                apply_refused=True,
            )

        result = apply_legacy_migration(plan)
        if json_mode:
            print(
                json.dumps(
                    {
                        **_migration_plan_payload(plan, mode="migration-apply"),
                        "ok": result.success,
                        "success": result.success,
                        "applied_action_ids": list(result.applied_action_ids),
                        "lock_written": result.lock_written,
                        "error_code": result.error_code,
                        "findings": findings_to_jsonable(result.verification_findings),
                    },
                    indent=2,
                )
            )
        elif result.success:
            print("Applied legacy migration; unified lock published before legacy retirement.")
        else:
            _emit_human_findings(result.verification_findings)
            print(
                _apply_failure_message(
                    result.error_code,
                    operation="migration",
                    preview_command="init --catalog CATALOG --migrate",
                ),
                file=sys.stderr,
            )
        return 0 if result.success else 1
    except ControlPlaneBusyError as exc:
        return _emit_error(json_mode, exc.code, str(exc), exit_code=1)
    except ControlPlaneError as exc:
        code = "CP-MIGRATION-STATE" if cast("bool", args.migrate) else "CP-INIT-STATE"
        return _emit_error(json_mode, code, exc, exit_code=2)
    except (PackageContractError, OSError, ValueError) as exc:
        code = "CP-MIGRATION-STATE" if cast("bool", args.migrate) else "CP-INIT-STATE"
        return _emit_error(json_mode, code, str(exc), exit_code=2)


def _catalog_refresh_advances(refresh: CatalogRefreshPlan | None) -> tuple[str, ...]:
    """Render the resolved package versions a catalog refresh moves.

    The refresh summary names only the release, but which packages advance is what
    re-renders artifacts, so it is the decision-relevant part of the documented
    pre-apply review. `--json` has always published these selections; the default
    preview discarded them at the render layer (issue #126).
    """
    if refresh is None or not refresh.changed:
        return ()
    width = max((len(change.standard_id) for change in refresh.affected_selections), default=0)
    return tuple(
        # Indented past the action's target column so each advance reads as detail
        # of the refresh line above it rather than as another planned action.
        f"{'':<9}{change.standard_id:<{width}}  "
        f"{change.previous.value if change.previous is not None else 'none'}"
        f" -> {change.current.value}"
        for change in refresh.affected_selections
    )


def _emit_plan(
    plan: ReconciliationPlan,
    previous_lock: CentralLock,
    *,
    mode: str,
    json_mode: bool,
) -> int:
    drift = _drift(plan, previous_lock)
    if json_mode:
        print(
            json.dumps(
                {
                    "ok": plan.applicable,
                    "mode": mode,
                    "drift": drift,
                    "plan": plan.to_jsonable(),
                },
                indent=2,
            )
        )
    else:
        advances = _catalog_refresh_advances(plan.catalog_refresh)
        for action in plan.actions:
            print(f"{action.kind.value:<8} {action.target}  {action.summary}")
            # `$catalog` is the refresh action's own scope, so the advances stay
            # attached to the summary line they explain wherever it is ordered.
            if action.scope == "$catalog":
                for advance in advances:
                    print(advance)
        _emit_human_findings(plan.findings)
        _emit_human_findings(_lock_only_drift_findings(plan, previous_lock))
        if not drift and plan.applicable:
            print("OK standards control plane is reconciled")
    return 1 if drift or not plan.applicable else 0


def _emit_apply(
    plan: ReconciliationPlan,
    request: ApplyRequest,
    *,
    json_mode: bool,
) -> int:
    result = apply_reconciliation(request)
    if json_mode:
        print(
            json.dumps(
                {
                    "ok": result.success,
                    "mode": "apply",
                    "success": result.success,
                    "applied_action_ids": list(result.applied_action_ids),
                    "lock_written": result.lock_written,
                    "error_code": result.error_code,
                    "findings": findings_to_jsonable(result.verification_findings),
                    "plan": plan.to_jsonable(),
                },
                indent=2,
            )
        )
    elif result.success and result.applied_action_ids:
        print(f"Applied {len(result.applied_action_ids)} repository mutation(s).")
    elif result.success and result.lock_written:
        print("Updated standards lock; no target mutations applied.")
    elif result.success:
        print("OK standards control plane is already reconciled; no mutations applied.")
    else:
        _emit_human_findings(result.verification_findings)
        print(
            _apply_failure_message(
                result.error_code,
                operation="reconciliation",
                preview_command="reconcile --check",
            ),
            file=sys.stderr,
        )
    return 0 if result.success else 1


def _recovery_json(plan: RecoveryPlan) -> dict[str, object]:
    return {
        "ok": plan.applicable,
        "mode": "recovery",
        "recovery_kind": plan.kind.value,
        "target": plan.target,
        "findings": findings_to_jsonable(plan.findings),
        "plan": plan.reconciliation.to_jsonable() if plan.reconciliation is not None else None,
    }


def _run_recovery(
    repo: Path,
    distribution: InstalledDistribution,
    allowed_majors: frozenset[MajorAuthorization],
    *,
    apply: bool,
    json_mode: bool,
) -> int:
    request = RecoveryRequest(repo, distribution, allowed_majors)
    plan = plan_recovery(request)
    if not apply:
        if json_mode:
            print(json.dumps(_recovery_json(plan), indent=2))
        elif plan.applicable:
            print(f"Recovery would restore {plan.target} ({plan.kind.value}).")
        else:
            _emit_human_findings(plan.findings)
        return 1
    result = apply_recovery(request, plan, apply=True, repair_state=True)
    if json_mode:
        print(
            json.dumps(
                {
                    **_recovery_json(plan),
                    "ok": result.success,
                    "mode": "recovery-apply",
                    "success": result.success,
                    "applied_action_ids": list(result.applied_action_ids),
                    "lock_written": result.lock_written,
                    "error_code": result.error_code,
                },
                indent=2,
            )
        )
    elif result.success:
        print(f"Recovered {plan.target}.")
    else:
        print(
            _apply_failure_message(
                result.error_code,
                operation="recovery",
                preview_command="reconcile --repair-state",
            ),
            file=sys.stderr,
        )
    return 0 if result.success else 1


def _restore_payload(
    plan: ManagedRestorePlan,
    *,
    mode: str,
) -> dict[str, object]:
    return {
        "ok": plan.applicable,
        "mode": mode,
        "restore": plan.preview.to_jsonable() if plan.preview is not None else None,
        "findings": findings_to_jsonable(plan.findings),
    }


def _run_managed_restore(
    planner: PlannerRequest,
    target: str,
    *,
    apply: bool,
    json_mode: bool,
) -> int:
    plan = plan_managed_restore(planner, target)
    if not apply:
        if json_mode:
            print(json.dumps(_restore_payload(plan, mode="restore-preview"), indent=2))
        elif plan.preview is not None:
            preview = plan.preview
            print(f"Managed restore preview: {preview.action} {preview.target}")
            print(f"  owner: {preview.owner}")
            print(f"  current state: {preview.current_state}")
            print(f"  lock digest: {preview.lock_digest}")
            print(f"  desired digest: {preview.desired_digest}")
            print(f"  apply: {preview.apply_command}")
        else:
            _emit_human_findings(plan.findings)
        return 0 if plan.applicable else 1

    if not plan.applicable:
        if json_mode:
            print(json.dumps(_restore_payload(plan, mode="restore-apply"), indent=2))
        else:
            _emit_human_findings(plan.findings)
        return 1

    result = apply_managed_restore(ManagedRestoreApplyRequest(planner=planner, expected_plan=plan))
    if json_mode:
        print(
            json.dumps(
                {
                    **_restore_payload(plan, mode="restore-apply"),
                    "ok": result.success,
                    "result": result.to_jsonable(),
                },
                indent=2,
            )
        )
    elif result.success:
        print(f"Managed restore {result.action} applied to {result.target}.")
    else:
        _emit_human_findings(result.findings)
        print(
            _apply_failure_message(
                result.error_code,
                operation="managed restore",
                preview_command=f"reconcile --restore-managed {target}",
            ),
            file=sys.stderr,
        )
    return 0 if result.success else 1


def run(
    argv: list[str] | None = None,
    *,
    distribution: InstalledDistribution | None = None,
) -> int:
    """Plan, check, apply, or recover one repository control plane."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _parser()
    try:
        args = parser.parse_args(arguments)
    except (_ArgumentError, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code == 0:
            return 0
        message = str(exc) if isinstance(exc, _ArgumentError) else "invalid arguments"
        return _emit_error("--json" in arguments, "CP-ARGUMENT", message, exit_code=2)

    repo = cast("Path", args.repo).resolve()
    json_mode = cast("bool", args.json)
    allowed_majors = frozenset(cast("list[MajorAuthorization]", args.allow_major))
    restore_paths = cast("list[str]", args.restore_managed)
    if cast("bool", args.check) and cast("bool", args.apply):
        return _emit_error(
            json_mode,
            "CP-ARGUMENT",
            "CP-ARGUMENT: --check cannot be combined with --apply",
            exit_code=2,
        )
    if len(restore_paths) > 1:
        return _emit_error(
            json_mode,
            "CP-ARGUMENT",
            "CP-ARGUMENT: --restore-managed accepts exactly one PATH",
            exit_code=2,
        )
    restore_target = restore_paths[0] if restore_paths else None
    if restore_target is not None and (
        cast("bool", args.check) or cast("bool", args.repair_state) or bool(allowed_majors)
    ):
        return _emit_error(
            json_mode,
            "CP-ARGUMENT",
            (
                "CP-ARGUMENT: --restore-managed cannot be combined with "
                "--check, --repair-state, or --allow-major"
            ),
            exit_code=2,
        )
    mode = "apply" if cast("bool", args.apply) else "check" if cast("bool", args.check) else "plan"
    # `--apply` is the only reconcile mode that publishes the installed catalog,
    # so it alone asserts release lineage; previews report the pending refresh.
    advance = CatalogAdvance.ADVANCING if cast("bool", args.apply) else CatalogAdvance.NON_ADVANCING
    try:
        selected_distribution = distribution or InstalledDistribution.current()
        state = detect_control_plane_state(
            repo,
            tool_release=selected_distribution.tool_release.value,
        )
        if restore_target is not None:
            planner = build_planner_request(
                repo,
                selected_distribution,
                frozenset(),
                state=state,
                advance=advance,
            )
            return _run_managed_restore(
                planner,
                restore_target,
                apply=cast("bool", args.apply),
                json_mode=json_mode,
            )
        if state.kind in {StateKind.INCOMPLETE, StateKind.INTERRUPTED_REFRESH}:
            if not cast("bool", args.repair_state):
                return _emit_error(
                    json_mode,
                    "CP-REPAIR-REQUIRED",
                    "control plane is incomplete; preview sanctioned recovery with --repair-state",
                    exit_code=1,
                )
            return _run_recovery(
                repo,
                selected_distribution,
                allowed_majors,
                apply=cast("bool", args.apply),
                json_mode=json_mode,
            )
        if cast("bool", args.repair_state):
            return _emit_error(
                json_mode,
                "CP-REPAIR-NOT-NEEDED",
                "control plane is not in a sanctioned incomplete state",
                exit_code=2,
            )
        if state.kind is StateKind.TOOL_MISMATCH:
            return _inspect_tool_mismatch(
                state,
                apply=cast("bool", args.apply),
                json_mode=json_mode,
            )
        planner = build_planner_request(
            repo,
            selected_distribution,
            allowed_majors,
            advance=advance,
        )
        plan = plan_reconciliation(planner)
        if cast("bool", args.apply):
            if not plan.applicable:
                return _emit_plan(
                    plan,
                    planner.resolution.previous_lock,
                    mode="apply",
                    json_mode=json_mode,
                )
            return _emit_apply(
                plan,
                ApplyRequest(planner=planner, expected_plan=plan),
                json_mode=json_mode,
            )
        return _emit_plan(
            plan,
            planner.resolution.previous_lock,
            mode=mode,
            json_mode=json_mode,
        )
    except ControlPlaneBusyError as exc:
        return _emit_error(json_mode, exc.code, str(exc), exit_code=1)
    except _MajorAuthorizationError as exc:
        message = str(exc)
        finding = ControlFinding(
            code="CP-RESOLVE-MAJOR-AUTH",
            severity="error",
            standard_id="project-standards",
            version="",
            path=".standards/config.toml",
            identity="$resolution",
            message=message,
            hint="supply a matching --allow-major STANDARD_ID@MAJOR authorization",
        )
        if json_mode:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "mode": mode,
                        "drift": True,
                        "findings": findings_to_jsonable((finding,)),
                    },
                    indent=2,
                )
            )
        else:
            _emit_human_findings((finding,))
        return 1
    except ControlPlaneError as exc:
        return _emit_error(json_mode, "CP-CONTROL-STATE", exc, exit_code=2)
    except (PackageContractError, OSError, ValueError) as exc:
        return _emit_error(json_mode, "CP-CONTROL-STATE", str(exc), exit_code=2)


def validate_repository(
    repo: Path,
    *,
    distribution: InstalledDistribution | None = None,
) -> int:
    """Report unified-state drift without changing any repository path."""
    try:
        selected_distribution = distribution or InstalledDistribution.current()
        state = detect_control_plane_state(
            repo,
            tool_release=selected_distribution.tool_release.value,
        )
        if state.kind is StateKind.UNINITIALIZED:
            return 0
        if state.kind is StateKind.LEGACY_ONLY:
            from project_standards.control_plane.command_resolution import (
                emit_legacy_authority_warning,
            )

            emit_legacy_authority_warning()
            return 0
        if state.kind is not StateKind.INITIALIZED:
            error = ControlPlaneError(
                state.detail or state.kind.value,
                path=(
                    f".standards/{state.malformed_file}"
                    if state.malformed_file is not None
                    else None
                ),
                line=state.line,
                column=state.column,
            )
            print(
                f"CP-CONTROL-STATE: {error}",
                file=sys.stderr,
            )
            return 1
        planner = build_planner_request(repo.resolve(), selected_distribution, frozenset())
        plan = plan_reconciliation(planner)
        drift = _drift(plan, planner.resolution.previous_lock)
        _emit_human_findings(plan.findings)
        if drift:
            print("CP-DRIFT: unified standards state requires reconciliation", file=sys.stderr)
        return 1 if drift or not plan.applicable else 0
    except ControlPlaneBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ControlPlaneError as exc:
        print(f"CP-RESOLUTION: {exc}", file=sys.stderr)
        return 1
    except (PackageContractError, OSError, ValueError) as exc:
        print(f"error: control-plane validation failed: {exc}", file=sys.stderr)
        return 2
