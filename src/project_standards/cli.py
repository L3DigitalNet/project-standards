"""Unified `project-standards` CLI: adopt | list | validate.

`validate` runs `validate-frontmatter` (schema), `validate-id` (id format), and
`validate-references` (cross-file, opt-in) so consumers get the full contract check
from a single command.  The standalone
`validate-frontmatter` console script is kept as a back-compat alias.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from project_standards import (
    format_frontmatter,
    validate_frontmatter,
    validate_id,
    validate_references,
)
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


def _extract_config_path(args: list[str]) -> Path:
    """Pull the --config value out of a forwarded argv (default .project-standards.yml)."""
    for i, a in enumerate(args):
        if a == "--config" and i + 1 < len(args):
            return Path(args[i + 1])
        if a.startswith("--config="):
            return Path(a.split("=", 1)[1])
    return Path(".project-standards.yml")


def _has_schema_flag(args: list[str]) -> bool:
    """True if a forwarded argv passes --schema (custom-schema mode) — CR-001."""
    return any(a == "--schema" or a.startswith("--schema=") for a in args)


def _assert_registry_bundle_parity(registry: Registry) -> None:
    """Bundles and the registry's version-tracked standards must agree in BOTH directions.

    Catches a bundle with no registry contract (would emit `contract_version: null`) AND a
    registry-known standard with no bundle (silently un-adoptable). Either way -> clean exit 2.
    """
    bundles = set(available_standards())
    registry_ids = {s for s in _REGISTRY_STANDARD_IDS if _contract_version(registry, s) is not None}
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
    """List adoptable standards; fail cleanly on registry/bundle drift before emitting output."""
    registry = load_registry()
    _assert_registry_bundle_parity(registry)  # fail cleanly on drift before emitting anything
    entries: list[tuple[str, str | None, Manifest]] = [
        (sid, _contract_version(registry, sid), load_manifest(sid)) for sid in available_standards()
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
    """Materialize *standards* into *dest*; apply registry/bundle parity guard before planning."""
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
    """CLI entry point for project-standards.

    `validate` is early-dispatched before argparse runs — argparse's REMAINDER cannot
    capture flags like `--config` that look like top-level options. All other subcommands
    go through the normal argparse path inside the error boundary below.
    """
    args_list = list(sys.argv[1:] if argv is None else argv)

    # EARLY DISPATCH for `validate`: delegate every trailing arg to all three validators BEFORE the
    # adopt/list parser runs. `parse_args()` + `REMAINDER` does NOT work here — argparse rejects
    # `validate --config x` as an unrecognized top-level option before REMAINDER can capture it.
    # All three validators accept the same --config / --quiet / FILE flags, so we pass args through
    # unchanged. We return the worst exit code (2 > 1 > 0) so a schema error, id violation, or
    # reference error is never masked by another tool's success.
    if args_list and args_list[0] == "validate":
        validator_args = args_list[1:]
        # Intercept --help before forwarding — otherwise validate_frontmatter.main(["--help"])
        # calls sys.exit(0), which hides that validate-id also runs.
        if "--help" in validator_args or "-h" in validator_args:
            _p = argparse.ArgumentParser(
                prog="project-standards validate",
                description=(
                    "Run validate-frontmatter (schema), validate-id (id format), and\n"
                    "validate-references (cross-file, opt-in). All run; the worst exit\n"
                    "code is returned.\n\n"
                    "All flags are forwarded to every validator. --schema and\n"
                    "--no-require-frontmatter are frontmatter-only; --schema also causes\n"
                    "validate-id to skip (custom schemas may use different id conventions).\n\n"
                    "For the full flag set of each validator:\n"
                    "  validate-frontmatter --help\n"
                    "  validate-id --help\n"
                    "  validate-references --help"
                ),
                formatter_class=argparse.RawDescriptionHelpFormatter,
            )
            _p.add_argument("files", nargs="*", metavar="FILE", help="Markdown files to validate.")
            _p.add_argument(
                "--config",
                metavar="PATH",
                help="Project config file (default: .project-standards.yml).",
            )
            _p.add_argument(
                "--schema",
                metavar="PATH",
                help="Custom schema; also skips id-format validation.",
            )
            _p.add_argument(
                "--glob",
                metavar="PATTERN",
                help="Additional glob pattern relative to cwd.",
            )
            _p.add_argument(
                "--no-require-frontmatter",
                action="store_true",
                help="Do not fail files that have no frontmatter block.",
            )
            _p.add_argument("--quiet", "-q", action="store_true", help="Suppress per-file output.")
            _p.print_help()
            return 0
        rc_frontmatter = validate_frontmatter.main(validator_args)
        rc_id = validate_id.main(validator_args)
        rc_refs = validate_references.main(validator_args)
        return max(rc_frontmatter, rc_id, rc_refs)

    if args_list and args_list[0] == "fix":
        fix_args = args_list[1:]
        if "--help" in fix_args or "-h" in fix_args:
            print(
                "usage: project-standards fix [FILE ...] [--config PATH] [--glob PATTERN] [--quiet]\n"
                "Format frontmatter (--write), fix ids, then re-validate (incl. references).\n"
                "Skips entirely under a custom schema."
            )
            return 0
        # Custom-schema preflight (CR-001): fix is bundled-only, like format/validate-id.
        try:
            fix_cfg = validate_frontmatter.load_config(_extract_config_path(fix_args))
        except validate_frontmatter.ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if _has_schema_flag(fix_args) or validate_frontmatter.schema_value_is_path(fix_cfg.schema):
            print("note: custom schema in use; skipping fix", file=sys.stderr)
            return 0
        rc_format = format_frontmatter.main(["--write", *fix_args])
        rc_idfix = validate_id.main(["--fix", *fix_args])
        # Final postcondition = the SAME contract as `project-standards validate`,
        # references included, so a "successful" fix cannot hide a reference error (CR-001).
        rc_check = max(
            validate_frontmatter.main(fix_args),
            validate_id.main(fix_args),
            validate_references.main(fix_args),
        )
        return max(rc_format, rc_idfix, rc_check)

    parser = argparse.ArgumentParser(prog="project-standards")
    sub = parser.add_subparsers(dest="command", required=True)
    # Registered only so top-level `--help` advertises it; real handling is the early dispatch above.
    sub.add_parser(
        "validate",
        help="validate schema + id + references (validate-frontmatter, validate-id, validate-references)",
    )
    sub.add_parser("fix", help="format frontmatter + fix ids, then re-validate")

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
