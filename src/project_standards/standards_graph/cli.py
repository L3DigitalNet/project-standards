"""Nested `project-standards standards` command group."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import NoReturn, cast

from project_standards.adopt.errors import ManifestError
from project_standards.control_plane.locking import ControlPlaneBusyError
from project_standards.standard_manifest import StandardManifestError
from project_standards.standards_graph.catalog import load_contract_defaults, render_catalog
from project_standards.standards_graph.discovery import build_graph
from project_standards.standards_graph.model import findings_to_jsonable, format_findings
from project_standards.standards_graph.validators import validate_graph

_USAGE = (
    "usage: project-standards standards "
    "{list,show,enable,disable,version,validate-graph,render-catalog,"
    "validate-packages,render-consumer-catalog,generate-package-schemas,"
    "sync-payload-projection} ..."
)


class _ArgparseError(Exception):
    """Raised when argparse would normally call sys.exit."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)


def _emit_error(json_mode: bool, code: str, message: str, *, exit_code: int = 2) -> int:
    if json_mode:
        print(json.dumps({"ok": False, "code": code, "error": message}))
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
        from project_standards.control_plane.config_edit import standard_views

        views = standard_views(cast("Path", args.repo).resolve())
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
        print(_USAGE, file=sys.stderr)
        return 2
    if args[0] in {"--help", "-h"}:
        print(_USAGE)
        print("  list             show the complete installed catalog inventory")
        print("  show             show catalog, desired, and applied state for one standard")
        print("  enable           enable one consumer-selectable standard")
        print("  disable          disable one standard while preserving its configuration")
        print("  version          set one standard's desired version selector")
        print("  validate-graph   validate standard manifests as one graph")
        print("  render-catalog   write or freshness-check standards/catalog.md")
        print("  validate-packages          validate V2 package repositories")
        print("  render-consumer-catalog    render or check a selected V2 consumer catalog")
        print("  generate-package-schemas   write or check V2 JSON Schemas")
        print("  sync-payload-projection    write or check installed payload projection")
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
    if command in {
        "validate-packages",
        "render-consumer-catalog",
        "generate-package-schemas",
        "sync-payload-projection",
    }:
        from project_standards.package_contract.cli import run_standards

        return run_standards([command, *rest])
    print(_USAGE, file=sys.stderr)
    return 2
