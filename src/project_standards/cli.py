"""Unified `project-standards` CLI: adopt | list | validate.

`validate` delegates to the existing validator (one implementation, two entry points —
the standalone `validate-frontmatter` console script is kept as a back-compat alias).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from project_standards import validate_frontmatter
from project_standards.adopt.engine import build_plan, execute_plan, format_report
from project_standards.adopt.errors import AdoptError
from project_standards.adopt.manifest import (
    Artifact,
    Manifest,
    available_standards,
    load_manifest,
)
from project_standards.registry import Registry, RegistryError, load_registry


def _contract_version(registry: Registry, standard_id: str) -> str | None:
    """The bundled default contract version for a standard (None if not version-tracked)."""
    return {
        "markdown-frontmatter": registry.frontmatter_default,
        "adr": registry.adr_default,
        "python-tooling": registry.python_tooling_default,
        "markdown-tooling": registry.markdown_tooling_default,
    }.get(standard_id)


# The registry's version-tracked standards (hyphenated ids), the single source for drift checks.
_REGISTRY_STANDARD_IDS = (
    "markdown-frontmatter",
    "adr",
    "python-tooling",
    "markdown-tooling",
)


def _assert_registry_bundle_parity(registry: Registry) -> None:
    """Bundles and the registry's version-tracked standards must agree in BOTH directions.

    Catches a bundle with no registry contract (would emit `contract_version: null`) AND a
    registry-known standard with no bundle (silently un-adoptable). Either way -> clean exit 2.
    """
    bundles = set(available_standards())
    registry_ids = {
        s for s in _REGISTRY_STANDARD_IDS if _contract_version(registry, s) is not None
    }
    if bundles != registry_ids:
        raise RegistryError(
            f"registry/bundle drift — registry-only: {sorted(registry_ids - bundles)}, "
            f"bundle-only: {sorted(bundles - registry_ids)}"
        )


def _artifact_entry(a: Artifact) -> dict[str, object]:
    entry: dict[str, object] = {"kind": a.kind, "owner": a.owner}
    if a.kind == "fragment":
        entry["target"] = a.target
    else:
        entry["dest"] = a.dest
    if a.source is not None:
        entry["source"] = a.source
    else:
        entry["shared"] = a.shared
    return entry


def _cmd_list(as_json: bool) -> int:
    registry = load_registry()
    _assert_registry_bundle_parity(
        registry
    )  # fail cleanly on drift before emitting anything
    entries: list[tuple[str, str | None, Manifest]] = [
        (sid, _contract_version(registry, sid), load_manifest(sid))
        for sid in available_standards()
    ]
    if as_json:
        payload = [
            {
                "id": sid,
                "contract_version": contract,
                "artifacts": [_artifact_entry(a) for a in manifest.artifacts],
            }
            for sid, contract, manifest in entries
        ]
        print(json.dumps(payload, indent=2))
        return 0
    for sid, contract, manifest in entries:
        print(f"{sid} (contract {contract})")
        for a in manifest.artifacts:
            where = a.target if a.kind == "fragment" else a.dest
            print(f"  {a.kind:<16} {where}")
    return 0


def _cmd_adopt(standards: list[str], dest: Path, force: bool, dry_run: bool) -> int:
    if not dest.is_dir():
        print(f"error: --dest is not a directory: {dest}", file=sys.stderr)
        return 2
    _assert_registry_bundle_parity(load_registry())  # same drift guard as `list`
    plan = build_plan(standards)
    report = execute_plan(plan, dest, force=force, dry_run=dry_run)
    out = format_report(report)
    if out:
        print(out)
    if dry_run:
        print("\n(dry run — no files written)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)

    # EARLY DISPATCH for `validate`: delegate every trailing arg to the validator BEFORE the
    # adopt/list parser runs. `parse_args()` + `REMAINDER` does NOT work here — argparse rejects
    # `validate --config x` as an unrecognized top-level option before REMAINDER can capture it.
    # Early dispatch lets `project-standards validate --config .project-standards.yml` pass through
    # untouched (the validator owns its own flags).
    if args_list and args_list[0] == "validate":
        return validate_frontmatter.main(args_list[1:])

    parser = argparse.ArgumentParser(prog="project-standards")
    sub = parser.add_subparsers(dest="command", required=True)
    # Registered only so top-level `--help` advertises it; real handling is the early dispatch above.
    sub.add_parser(
        "validate",
        help="validate Markdown frontmatter (delegates to validate-frontmatter)",
    )

    p_adopt = sub.add_parser("adopt", help="materialize a standard's artifacts")
    p_adopt.add_argument("standards", nargs="+", metavar="STANDARD")
    p_adopt.add_argument("--dest", type=Path, default=Path.cwd())
    p_adopt.add_argument("--force", action="store_true")
    p_adopt.add_argument("--dry-run", action="store_true")

    p_list = sub.add_parser("list", help="list adoptable standards and their artifacts")
    p_list.add_argument("--json", action="store_true")

    args = parser.parse_args(args_list)

    # `list` and `adopt` both touch bundle/registry data, so both sit inside the error
    # boundary — broken or drifted metadata must produce a clean exit code, never a traceback.
    try:
        if args.command == "list":
            return _cmd_list(args.json)
        return _cmd_adopt(args.standards, args.dest, args.force, args.dry_run)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except AdoptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
