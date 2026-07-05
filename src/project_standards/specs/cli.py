"""Nested `project-standards spec` command group."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Callable
from pathlib import Path

from project_standards.specs.commands.extract import extract_slice
from project_standards.specs.commands.lint import lint_document
from project_standards.specs.commands.next_id import next_free_id
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.config import ConfigError, collect_spec_paths, load_spec_config
from project_standards.specs.document import SpecParseError, parse_document
from project_standards.specs.model import Finding
from project_standards.specs.registry import load_registry

_DEFAULT_CONFIG = Path(".project-standards.yml")
_USAGE = "usage: project-standards spec {validate|lint|extract|next} ..."


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SpecParseError(f"{path}: not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read spec {path}: {exc}") from exc


def _findings_payload(results: list[tuple[Path, list[Finding]]]) -> list[dict[str, object]]:
    return [
        {
            "file": str(path),
            "ok": not findings,
            "findings": [dataclasses.asdict(f) for f in findings],
        }
        for path, findings in results
    ]


def _run_setwide(argv: list[str], *, lint: bool) -> int:
    ap = argparse.ArgumentParser(prog=f"project-standards spec {'lint' if lint else 'validate'}")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    reg = load_registry()
    cfg = load_spec_config(args.config)
    paths = collect_spec_paths(args.files, cfg)
    fn = lint_document if lint else validate_document
    results: list[tuple[Path, list[Finding]]] = []
    for path in paths:
        try:
            results.append((path, fn(parse_document(str(path), _read(path)), reg)))
        except SpecParseError as exc:
            results.append((path, [Finding(code="SV-PARSE", severity="error", message=str(exc))]))
    if args.json:
        print(json.dumps(_findings_payload(results), indent=2))
    else:
        for path, findings in results:
            state = "WARN" if lint and findings else "FAIL" if findings else "OK  "
            print(f"{state} {path}")
            for finding in findings:
                line = f" (L{finding.line})" if finding.line else ""
                print(f"   [{finding.code}] {finding.message}{line}")
    any_findings = any(findings for _, findings in results)
    if lint:
        return 1 if any_findings and args.strict else 0
    return 1 if any_findings else 0


def _run_extract(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec extract")
    ap.add_argument("file", type=Path)
    ap.add_argument("selector")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = parse_document(str(args.file), _read(args.file))
    result = extract_slice(doc, args.selector)
    if args.json:
        print(
            json.dumps(
                {
                    "file": str(args.file),
                    "selector": result.selector,
                    "kind": result.kind,
                    "found": result.found,
                    "markdown": result.markdown,
                }
            )
        )
    elif result.found:
        print(result.markdown)
    else:
        print(f"no match for {result.selector!r}", file=sys.stderr)
    return 0 if result.found else 1


def _run_next(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec next")
    ap.add_argument("file", type=Path)
    ap.add_argument("prefix")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = parse_document(str(args.file), _read(args.file))
    try:
        nid = next_free_id(doc, load_registry(), args.prefix)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    prefix = args.prefix.rstrip("-").upper()
    print(
        json.dumps({"file": str(args.file), "prefix": prefix, "next_id": nid}) if args.json else nid
    )
    return 0


def _run_validate(argv: list[str]) -> int:
    return _run_setwide(argv, lint=False)


def _run_lint(argv: list[str]) -> int:
    return _run_setwide(argv, lint=True)


_VERBS: dict[str, Callable[[list[str]], int]] = {
    "validate": _run_validate,
    "lint": _run_lint,
    "extract": _run_extract,
    "next": _run_next,
}


def run(argv: list[str]) -> int:
    """Run the nested spec command group."""
    if argv[:1] in (["-h"], ["--help"]):
        print(_USAGE)
        return 0
    if not argv:
        print(_USAGE, file=sys.stderr)
        return 2
    verb, rest = argv[0], argv[1:]
    if verb not in _VERBS:
        print(f"error: unknown spec verb {verb!r}", file=sys.stderr)
        return 2
    try:
        return _VERBS[verb](rest)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except SpecParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
