"""Nested `project-standards standards` command group."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

from project_standards.standard_manifest import StandardManifestError
from project_standards.standards_graph.discovery import build_graph
from project_standards.standards_graph.model import findings_to_jsonable, format_findings
from project_standards.standards_graph.validators import validate_graph

_USAGE = "usage: project-standards standards {validate-graph} ..."


class _ArgparseError(Exception):
    """Raised when argparse would normally call sys.exit."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)


def _emit_error(json_mode: bool, code: str, message: str) -> int:
    if json_mode:
        print(json.dumps({"ok": False, "code": code, "error": message}))
    else:
        print(f"error: {message}", file=sys.stderr)
    return 2


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
    except (OSError, ValueError, StandardManifestError) as exc:
        return _emit_error(args.json, "graph_load_error", str(exc))

    if args.json:
        print(
            json.dumps({"ok": not findings, "findings": findings_to_jsonable(findings)}, indent=2)
        )
    else:
        print(format_findings(findings))
    return 1 if findings else 0


def run(argv: list[str] | None = None) -> int:
    """Run the nested standards command group."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(_USAGE, file=sys.stderr)
        return 2
    if args[0] in {"--help", "-h"}:
        print(_USAGE)
        print("  validate-graph   validate standard manifests as one graph")
        return 0
    command, rest = args[0], args[1:]
    if command == "validate-graph":
        return _run_validate_graph(rest)
    print(_USAGE, file=sys.stderr)
    return 2
