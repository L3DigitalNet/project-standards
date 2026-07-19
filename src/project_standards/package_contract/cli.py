"""CLI boundaries for V2 package authoring and release-policy operations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import NoReturn, cast

from project_standards._version import package_version
from project_standards.package_contract.catalog import (
    _discover_catalog_sources,  # pyright: ignore[reportPrivateUsage]  # package-internal discovery
    load_catalog_source,
    render_consumer_catalog,
    validate_catalog_source,
    write_consumer_catalog,
)
from project_standards.package_contract.diagnostics import (
    PackageContractError,
    PackageFinding,
    findings_to_jsonable,
    sort_findings,
)
from project_standards.package_contract.graph import validate_package_graph
from project_standards.package_contract.projection import sync_payload_projection
from project_standards.package_contract.release import (
    ReleaseClassification,
    ReleasedPayload,
    ReleaseSnapshot,
    ToolVersions,
    classify_catalog_diff,
    load_git_release_snapshot,
)
from project_standards.package_contract.repository import (
    PackageRepository,
    build_package_repository,
)
from project_standards.package_contract.schemas import generate_package_schemas

_SEMVER_TAG = re.compile(r"^v?((0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*))$")
_STANDARDS_USAGE = (
    "usage: project-standards standards "
    "{validate-packages,render-consumer-catalog,generate-package-schemas,"
    "sync-payload-projection} ..."
)
_PACKAGES_USAGE = "usage: project-standards packages {check-release} ..."


class _ArgparseError(Exception):
    """Replace argparse process exits with the repository's exit-code contract."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _emit_error(json_mode: bool, code: str, message: str) -> int:
    if json_mode:
        print(json.dumps({"ok": False, "code": code, "error": message}))
    else:
        print(f"error: {message}", file=sys.stderr)
    return 2


def _safe_root(path: Path) -> Path:
    try:
        if path.is_symlink() or not path.is_dir():
            raise PackageContractError("package repository root must be a regular directory")
        return path.resolve(strict=True)
    except OSError as exc:
        raise PackageContractError("package repository root could not be resolved") from exc


def _validated_repositories(
    root: Path,
) -> tuple[list[PackageRepository], tuple[PackageFinding, ...]]:
    """Validate canonical catalogs against one immutable package snapshot."""
    sources = _discover_catalog_sources(root)
    base = build_package_repository(root)
    repositories: list[PackageRepository] = []
    families = base.family_map
    payloads = base.payload_map
    for major, path in sources:
        try:
            catalog = validate_catalog_source(
                load_catalog_source(path),
                families,
                payloads,
            )
            findings = base.findings
        except PackageContractError as exc:
            catalog = None
            findings = tuple(
                sort_findings(
                    (
                        *base.findings,
                        PackageFinding(
                            code="PC-CATALOG-INVALID",
                            severity="error",
                            standard_id="project-standards",
                            version="",
                            path=f"catalogs/{major}.toml",
                            identity="catalog",
                            message=str(exc),
                            hint=(
                                "repair the declared V2 package source and rerun "
                                "repository validation"
                            ),
                        ),
                    )
                )
            )
        repositories.append(replace(base, catalog=catalog, findings=findings))
    if not repositories:
        repositories.append(base)
    findings = {
        finding for repository in repositories for finding in validate_package_graph(repository)
    }
    return repositories, tuple(sort_findings(findings))


def _format_findings(findings: tuple[PackageFinding, ...]) -> str:
    if not findings:
        return "OK package repository"
    lines: list[str] = []
    for finding in findings:
        version = f"@{finding.version}" if finding.version else ""
        lines.append(
            f"ERROR {finding.code} {finding.standard_id}{version} "
            f"{finding.identity}: {finding.message}"
        )
    return "\n".join(lines)


def _emit_findings(findings: tuple[PackageFinding, ...], *, json_mode: bool) -> int:
    if json_mode:
        print(
            json.dumps(
                {"ok": not findings, "findings": findings_to_jsonable(findings)},
                indent=2,
            )
        )
    else:
        stream = sys.stderr if findings else sys.stdout
        print(_format_findings(findings), file=stream)
    return 1 if findings else 0


def _run_validate_packages(argv: list[str]) -> int:
    parser = _Parser(prog="project-standards standards validate-packages")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        root = _safe_root(cast("Path", args.root))
        _, findings = _validated_repositories(root)
        return _emit_findings(findings, json_mode=cast("bool", args.json))
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))
    except PackageContractError as exc:
        return _emit_error("--json" in argv, "package_load_error", str(exc))


def _resolved_output(root: Path, output_arg: Path) -> Path:
    candidate = output_arg if output_arg.is_absolute() else root / output_arg
    if candidate.is_symlink():
        raise PackageContractError("consumer catalog output cannot be a symlink")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise PackageContractError(f"output escapes root: {resolved}")
    return resolved


def _run_render_consumer_catalog(argv: list[str]) -> int:
    parser = _Parser(prog="project-standards standards render-consumer-catalog")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--catalog-major", type=_positive_int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tool-release", default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        json_mode = cast("bool", args.json)
        root = _safe_root(cast("Path", args.root))
        output = _resolved_output(root, cast("Path", args.output))
        repository = build_package_repository(
            root,
            catalog_major=cast("int", args.catalog_major),
        )
        findings = validate_package_graph(repository)
        if findings:
            return _emit_findings(findings, json_mode=json_mode)
        if repository.catalog is None:
            raise PackageContractError("selected catalog did not load")
        rendered = render_consumer_catalog(
            repository.catalog,
            repository.family_map,
            repository.payload_map,
            tool_release=cast("str | None", args.tool_release) or package_version(),
        )
        check = cast("bool", args.check)
        fresh = write_consumer_catalog(output, rendered, check=check)
        if not fresh:
            if json_mode:
                print(json.dumps({"ok": False, "code": "stale", "path": str(output)}))
            else:
                print(f"error: generated consumer catalog is stale: {output}", file=sys.stderr)
            return 1
        if json_mode:
            print(json.dumps({"ok": True, "path": str(output), "check": check}))
        else:
            action = "OK" if check else "Wrote"
            print(f"{action} consumer catalog: {output.relative_to(root)}")
        return 0
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))
    except (OSError, PackageContractError) as exc:
        code = "bad_output" if "output" in str(exc) else "catalog_error"
        return _emit_error("--json" in argv, code, str(exc))


def _run_generate_package_schemas(argv: list[str]) -> int:
    parser = _Parser(prog="project-standards standards generate-package-schemas")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        root = _safe_root(cast("Path", args.root))
        check = cast("bool", args.check)
        # Import upward only at this integration boundary; the lower-level
        # package schema module remains independent of the consumer plane.
        from project_standards.control_plane.schemas import (
            generate_control_plane_schemas,
        )

        package_fresh = generate_package_schemas(root, check=check)
        control_plane_fresh = generate_control_plane_schemas(root, check=check)
        fresh = package_fresh and control_plane_fresh
        if not fresh:
            if cast("bool", args.json):
                print(json.dumps({"ok": False, "code": "stale"}))
            else:
                print("error: generated package schemas are stale", file=sys.stderr)
            return 1
        if cast("bool", args.json):
            print(json.dumps({"ok": True, "check": check}))
        else:
            print("OK package schemas" if check else "Wrote package schemas")
        return 0
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))
    except PackageContractError as exc:
        return _emit_error("--json" in argv, "schema_error", str(exc))


def _run_sync_payload_projection(argv: list[str]) -> int:
    parser = _Parser(prog="project-standards standards sync-payload-projection")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        root = _safe_root(cast("Path", args.root))
        check = cast("bool", args.check)
        json_mode = cast("bool", args.json)
        findings = sync_payload_projection(root, check=check)
        if findings:
            return _emit_findings(findings, json_mode=json_mode)
        if json_mode:
            print(json.dumps({"ok": True, "check": check}))
        else:
            print("OK payload projection" if check else "Wrote payload projection")
        return 0
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))
    except PackageContractError as exc:
        return _emit_error("--json" in argv, "projection_error", str(exc))


def _release_snapshot(repository: PackageRepository) -> ReleaseSnapshot:
    if repository.catalog is None:
        raise PackageContractError("current release catalog did not load")
    payloads = tuple(
        ReleasedPayload(
            standard_id=payload.manifest.payload.standard,
            version=payload.manifest.payload.version,
            aggregate_digest=payload.integrity.aggregate_digest,
            files=payload.integrity.inventory,
        )
        for payload in repository.payloads
    )
    return ReleaseSnapshot(catalog=repository.catalog, payloads=payloads)


def _previous_version(baseline: str, explicit: str | None) -> str:
    if explicit is not None:
        return explicit
    match = _SEMVER_TAG.fullmatch(baseline)
    if match is None:
        raise PackageContractError(
            "--previous-version is required when baseline is not a version tag"
        )
    return match.group(1)


def _run_check_release(argv: list[str]) -> int:
    parser = _Parser(prog="project-standards packages check-release")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--previous-version")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        json_mode = cast("bool", args.json)
        root = _safe_root(cast("Path", args.root))
        baseline = cast("str", args.baseline)
        previous_version = _previous_version(
            baseline,
            cast("str | None", args.previous_version),
        )
        current_version = package_version()
        current_major = int(current_version.split(".", 1)[0])
        previous_major = int(previous_version.split(".", 1)[0])
        repository = build_package_repository(root, catalog_major=current_major)
        graph_findings = validate_package_graph(repository)
        if graph_findings:
            return _emit_findings(graph_findings, json_mode=json_mode)
        previous = load_git_release_snapshot(root, baseline, previous_major)
        result = classify_catalog_diff(
            previous,
            _release_snapshot(repository),
            ToolVersions(previous=previous_version, current=current_version),
        )
        if json_mode:
            print(
                json.dumps(
                    {
                        "ok": result.classification is not ReleaseClassification.FORBIDDEN,
                        "classification": result.classification.value,
                        "findings": findings_to_jsonable(result.findings),
                    },
                    indent=2,
                )
            )
        else:
            print(f"Release classification: {result.classification.value}")
            if result.findings:
                print(_format_findings(result.findings), file=sys.stderr)
        return 1 if result.classification is ReleaseClassification.FORBIDDEN else 0
    except _ArgparseError as exc:
        return _emit_error("--json" in argv, "bad_args", str(exc))
    except (OSError, ValueError, PackageContractError) as exc:
        return _emit_error("--json" in argv, "release_error", str(exc))


def run_standards(argv: list[str]) -> int:
    """Run V2 commands nested under `project-standards standards`."""
    if not argv:
        print(_STANDARDS_USAGE, file=sys.stderr)
        return 2
    if argv[0] in {"--help", "-h"}:
        print(_STANDARDS_USAGE)
        print("  validate-packages          validate V2 package repositories")
        print("  render-consumer-catalog    render or check a selected V2 consumer catalog")
        print("  generate-package-schemas   write or check V2 JSON Schemas")
        print("  sync-payload-projection    write or check installed payload projection")
        return 0
    command, rest = argv[0], argv[1:]
    if command == "validate-packages":
        return _run_validate_packages(rest)
    if command == "render-consumer-catalog":
        return _run_render_consumer_catalog(rest)
    if command == "generate-package-schemas":
        return _run_generate_package_schemas(rest)
    if command == "sync-payload-projection":
        return _run_sync_payload_projection(rest)
    print(_STANDARDS_USAGE, file=sys.stderr)
    return 2


def run_packages(argv: list[str]) -> int:
    """Run repository-only package release workflows."""
    if not argv:
        print(_PACKAGES_USAGE, file=sys.stderr)
        return 2
    if argv[0] in {"--help", "-h"}:
        print(_PACKAGES_USAGE)
        print("  check-release   compare working payloads with a released tag")
        return 0
    if argv[0] == "check-release":
        return _run_check_release(argv[1:])
    print(_PACKAGES_USAGE, file=sys.stderr)
    return 2
