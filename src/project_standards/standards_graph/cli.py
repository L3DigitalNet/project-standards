"""Nested `project-standards standards` command group."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import NoReturn, cast

from project_standards.adopt.errors import ManifestError
from project_standards.cli_contract import PACKAGE_AUTHORING_COMMAND_HELP
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.locking import ControlPlaneBusyError
from project_standards.package_contract.cut_successor import CutPlan, apply_cut, plan_cut
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.standard_manifest import StandardManifestError
from project_standards.standards_graph.catalog import load_contract_defaults, render_catalog
from project_standards.standards_graph.discovery import build_graph
from project_standards.standards_graph.model import findings_to_jsonable, format_findings
from project_standards.standards_graph.validators import validate_graph

_COMMAND_HELP = {
    "list": "show the complete installed catalog inventory",
    "show": "show catalog, desired, and applied state for one standard",
    "enable": "enable one consumer-selectable standard",
    "disable": "disable one standard while preserving its configuration",
    "version": "set one standard's desired version selector",
    "validate-graph": "validate standard manifests as one graph",
    "render-catalog": "write or freshness-check standards/catalog.md",
    "cut-successor": "author a successor payload version from its predecessor",
    **PACKAGE_AUTHORING_COMMAND_HELP,
}


class _ArgparseError(Exception):
    """Raised when argparse would normally call sys.exit."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)


def _group_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="project-standards standards")
    subparsers = parser.add_subparsers(dest="command")
    for command, help_text in _COMMAND_HELP.items():
        subparsers.add_parser(command, help=help_text, add_help=False)
    return parser


def _emit_error(
    json_mode: bool,
    code: str,
    error: str | ControlPlaneError,
    *,
    exit_code: int = 2,
) -> int:
    message = str(error)
    if json_mode:
        payload: dict[str, object] = {"ok": False, "code": code, "error": message}
        if isinstance(error, ControlPlaneError):
            payload.update(error.to_jsonable())
        print(json.dumps(payload))
    else:
        print(f"error: {message}", file=sys.stderr)
    return exit_code


def _run_validate_graph(argv: list[str]) -> int:
    ap = _Parser(prog="project-standards standards validate-graph")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-all-manifests", action="store_true")
    try:
        args = ap.parse_args(argv)
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))

    try:
        graph = build_graph(args.root)
        findings = validate_graph(graph, require_all_manifests=args.require_all_manifests)
    except (OSError, ValueError, StandardManifestError, ManifestError) as exc:
        return _emit_error(args.json, "graph_load_error", str(exc))

    if args.json:
        print(
            json.dumps({"ok": not findings, "findings": findings_to_jsonable(findings)}, indent=2)
        )
    else:
        print(format_findings(findings))
    return 1 if findings else 0


def _run_render_catalog(argv: list[str]) -> int:
    ap = _Parser(prog="project-standards standards render-catalog")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--output", type=Path, default=Path("standards/catalog.md"))
    ap.add_argument("--check", action="store_true")
    try:
        args = ap.parse_args(argv)
        root = cast("Path", args.root).resolve()
        graph = build_graph(root)
        findings = validate_graph(graph, require_all_manifests=True)
        if findings:
            print(format_findings(findings), file=sys.stderr)
            return 1
        output_arg = cast("Path", args.output)
        output = output_arg if output_arg.is_absolute() else root / output_arg
        output = output.resolve()
        if not output.is_relative_to(root):
            return _emit_error(False, "bad_output", f"output escapes root: {output}")
        link_prefix = Path(os.path.relpath(root / "standards", start=output.parent)).as_posix()
        rendered = render_catalog(
            graph,
            contract_defaults=load_contract_defaults(graph),
            standards_link_prefix="" if link_prefix == "." else link_prefix,
        )
        if cast("bool", args.check):
            if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
                print(f"error: generated catalog is stale: {output}", file=sys.stderr)
                return 1
            print(f"OK generated catalog: {output.relative_to(root)}")
            return 0
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"Wrote generated catalog: {output.relative_to(root)}")
        return 0
    except _ArgparseError as exc:
        return _emit_error(False, "bad_args", str(exc))
    except (OSError, ValueError, StandardManifestError, ManifestError) as exc:
        return _emit_error(False, "catalog_error", str(exc))


def _describe_plan(plan: CutPlan) -> list[str]:
    root = plan.root
    lines = [
        f"Cut {plan.standard_id} {plan.predecessor.value} -> {plan.successor.value}",
        f"  copy      {plan.source_dir.relative_to(root)} -> {plan.target_dir.relative_to(root)}",
        f"  index     {plan.family_index.relative_to(root)}: add [[versions]] "
        f"{plan.successor.value}",
        f"  catalog   {plan.catalog_path.relative_to(root)}: add {plan.successor.value} as "
        f"{plan.successor_role.value}",
    ]
    if plan.predecessor_role_after is not plan.predecessor_role:
        lines.append(
            f"  catalog   {plan.catalog_path.relative_to(root)}: {plan.predecessor.value} "
            f"{plan.predecessor_role.value} -> {plan.predecessor_role_after.value}"
        )
    if plan.scaffold_target is not None:
        lines.append(f"  scaffold  {plan.scaffold_target.relative_to(root)}")
    lines.append("  then      standards sync-payload-projection, standards render-catalog")
    return lines


def _plan_jsonable(plan: CutPlan) -> dict[str, object]:
    return {
        "standard_id": plan.standard_id,
        "predecessor": plan.predecessor.value,
        "successor": plan.successor.value,
        "source_dir": plan.source_dir.relative_to(plan.root).as_posix(),
        "target_dir": plan.target_dir.relative_to(plan.root).as_posix(),
        "family_index": plan.family_index.relative_to(plan.root).as_posix(),
        "catalog": plan.catalog_path.relative_to(plan.root).as_posix(),
        "successor_role": plan.successor_role.value,
        "predecessor_role": plan.predecessor_role_after.value,
        "scaffold_target": (
            plan.scaffold_target.relative_to(plan.root).as_posix()
            if plan.scaffold_target is not None
            else None
        ),
    }


def _run_cut_successor(argv: list[str]) -> int:
    """Cut a successor payload version, then rerun the two generated-artifact writers.

    The follow-on `sync-payload-projection` and `render-catalog` calls go through
    the same entry points an author would type, so a cut can never produce a
    projection or catalog that differs from the one those commands generate.
    Their exit status is propagated: a cut whose generated artifacts did not
    write is not a successful cut, even though the payload bytes already landed.
    """
    ap = _Parser(prog="project-standards standards cut-successor")
    ap.add_argument("standard_id")
    ap.add_argument("version")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--from", dest="predecessor")
    ap.add_argument("--scaffold-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    json_mode = "--json" in argv
    try:
        args = ap.parse_args(argv)
        json_mode = cast("bool", args.json)
        root = cast("Path", args.root).resolve()
        plan = plan_cut(
            root,
            cast("str", args.standard_id),
            cast("str", args.version),
            predecessor=cast("str | None", args.predecessor),
            scaffold_test=cast("bool", args.scaffold_test),
        )
        if cast("bool", args.dry_run):
            if json_mode:
                print(
                    json.dumps(
                        {"ok": True, "dry_run": True, "plan": _plan_jsonable(plan)}, indent=2
                    )
                )
            else:
                print("\n".join(_describe_plan(plan)))
            return 0
        result = apply_cut(plan)
    except _ArgparseError as exc:
        return _emit_error(json_mode, "bad_args", str(exc))
    except (OSError, ValueError, PackageContractError) as exc:
        return _emit_error(json_mode, "cut_error", str(exc))

    from project_standards.package_contract.cli import run_standards

    generated = run_standards(["sync-payload-projection", "--root", str(root)])
    if generated == 0:
        generated = _run_render_catalog(["--root", str(root)])

    occurrences = [
        {"path": item.path, "line": item.line, "text": item.text} for item in result.occurrences
    ]
    if json_mode:
        print(
            json.dumps(
                {
                    "ok": generated == 0,
                    "plan": _plan_jsonable(plan),
                    "aggregate_digest": result.aggregate_digest.value,
                    "files": result.file_count,
                    "predecessor_references": occurrences,
                    "repointed_migrations": list(result.repointed_migrations),
                    "undecodable_files": list(result.undecodable),
                    "scaffold_written": (
                        result.scaffold_written.relative_to(root).as_posix()
                        if result.scaffold_written is not None
                        else None
                    ),
                },
                indent=2,
            )
        )
    else:
        print("\n".join(_describe_plan(plan)))
        print(f"  aggregate {result.aggregate_digest.value} over {result.file_count} files")
        for migration in result.repointed_migrations:
            print(f"  migration {migration}: to -> package:{plan.successor.value}")
        if result.occurrences:
            # Reported, never rewritten: only the author knows which of these name
            # the version being cut and which are correct history.
            print(
                f"REVIEW: {len(result.occurrences)} line(s) in the new tree still name "
                f"{plan.predecessor.value}:"
            )
            for item in result.occurrences:
                print(f"  {item.path}:{item.line}: {item.text}")
        else:
            print(f"REVIEW: no line in the new tree names {plan.predecessor.value}")
        for name in result.undecodable:
            print(f"  (not text, unscanned) {name}")
    return 1 if generated else 0


def _control_parser(command: str) -> _Parser:
    parser = _Parser(prog=f"project-standards standards {command}")
    if command != "list":
        parser.add_argument("standard_id")
    if command == "version":
        parser.add_argument("version")
    elif command == "enable":
        parser.add_argument("--version")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    return parser


def _standard_view(
    views: list[dict[str, object]],
    standard_id: str,
) -> dict[str, object] | None:
    return next((view for view in views if view["id"] == standard_id), None)


def _run_control_inspection(command: str, argv: list[str]) -> int:
    parser = _control_parser(command)
    try:
        args = parser.parse_args(argv)
        from project_standards.control_plane.config_edit import standard_inspection

        views, skew = standard_inspection(cast("Path", args.repo).resolve())
        # stderr regardless of --json: the note annotates the basis, and
        # writing it to stdout would corrupt the JSON document. This mirrors
        # `agent-handoff legacy-report`, which discloses an unlocked read the
        # same way in both formats.
        if skew is not None:
            committed, installed = skew
            print(
                f"note: reading the committed catalog: release {committed}; "
                f"installed release {installed} is not reconciled into this repository "
                "yet, so a package default may advance on "
                "project-standards reconcile --apply",
                file=sys.stderr,
            )
        if command == "list":
            if cast("bool", args.json):
                print(json.dumps({"ok": True, "standards": views}, indent=2))
            else:
                for view in views:
                    marker = "enabled" if view["enabled"] else "disabled"
                    role = (
                        "selectable"
                        if view["selectable"]
                        else ",".join(cast("list[str]", view["availability"]))
                    )
                    available = ",".join(cast("list[str]", view["available"]))
                    print(
                        f"{view['id']}  {marker}  {role}  available={available}  "
                        f"default={view['default'] or '-'}  "
                        f"requested={view['requested'] or '-'}  "
                        f"resolved={view['resolved'] or '-'}"
                    )
            return 0

        standard_id = cast("str", args.standard_id)
        view = _standard_view(views, standard_id)
        if view is None:
            return _emit_error(
                cast("bool", args.json),
                "unknown_standard",
                f"standard is not present in the installed catalog: {standard_id}",
            )
        if cast("bool", args.json):
            print(json.dumps({"ok": True, "standard": view}, indent=2))
        else:
            print(json.dumps(view, indent=2))
        return 0
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))
    except ControlPlaneBusyError as exc:
        return _emit_error("--json" in argv, exc.code, str(exc), exit_code=1)
    except ControlPlaneError as exc:
        return _emit_error("--json" in argv, "control_state_error", exc)
    except (OSError, ValueError) as exc:
        return _emit_error("--json" in argv, "control_state_error", str(exc))


def _run_control_edit(command: str, argv: list[str]) -> int:
    parser = _control_parser(command)
    try:
        args = parser.parse_args(argv)
        from project_standards.control_plane.config_edit import (
            set_standard_selection,
            standard_views,
        )

        repo = cast("Path", args.repo).resolve()
        standard_id = cast("str", args.standard_id)
        views = standard_views(repo)
        view = _standard_view(views, standard_id)
        if view is None:
            return _emit_error(
                cast("bool", args.json),
                "unknown_standard",
                f"standard is not present in the installed catalog: {standard_id}",
            )
        if command == "enable" and not view["selectable"]:
            return _emit_error(
                cast("bool", args.json),
                "not_selectable",
                f"standard is catalog-visible but not consumer-selectable: {standard_id}",
            )

        requested_version = cast("str | None", getattr(args, "version", None))
        if requested_version not in {None, "latest"} and requested_version not in cast(
            "list[str]", view["available"]
        ):
            return _emit_error(
                cast("bool", args.json),
                "version_unavailable",
                f"version is not advertised for {standard_id}: {requested_version}",
            )

        if command == "enable":
            set_standard_selection(
                repo,
                standard_id,
                enabled=True,
                version=requested_version,
            )
        elif command == "disable":
            set_standard_selection(repo, standard_id, enabled=False)
        else:
            set_standard_selection(repo, standard_id, version=requested_version)

        result = {
            "ok": True,
            "standard_id": standard_id,
            "enabled": command == "enable" if command != "version" else view["enabled"],
            "version": requested_version if requested_version is not None else view["requested"],
            "reconciliation": "pending",
        }
        if cast("bool", args.json):
            print(json.dumps(result, indent=2))
        else:
            print(f"Updated {standard_id}; reconciliation is pending.")
        return 0
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))
    except ControlPlaneBusyError as exc:
        return _emit_error("--json" in argv, exc.code, str(exc), exit_code=1)
    except (OSError, ValueError) as exc:
        return _emit_error("--json" in argv, "config_edit_error", str(exc))


def run(argv: list[str] | None = None) -> int:
    """Run the nested standards command group."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _group_argument_parser().print_usage(sys.stderr)
        return 2
    if args[0] in {"--help", "-h"}:
        _group_argument_parser().print_help()
        return 0
    command, rest = args[0], args[1:]
    if command in {"list", "show"}:
        return _run_control_inspection(command, rest)
    if command in {"enable", "disable", "version"}:
        return _run_control_edit(command, rest)
    if command == "validate-graph":
        return _run_validate_graph(rest)
    if command == "render-catalog":
        return _run_render_catalog(rest)
    if command == "cut-successor":
        return _run_cut_successor(rest)
    if command in {
        "validate-packages",
        "render-consumer-catalog",
        "generate-package-schemas",
        "sync-payload-projection",
    }:
        from project_standards.package_contract.cli import run_standards

        return run_standards([command, *rest])
    _group_argument_parser().print_usage(sys.stderr)
    return 2
