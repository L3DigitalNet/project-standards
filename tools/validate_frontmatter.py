#!/usr/bin/env python3
"""Validate YAML frontmatter in Markdown files against the project schema.

The validator is the runtime half of the Markdown Frontmatter Standard
(see standards/markdown-frontmatter.md). It detects a leading YAML frontmatter
block, parses it safely, and validates it against a JSON Schema (Draft 2020-12).

Usage:
    # Validate explicit files
    validate-frontmatter README.md docs/adr.md

    # Validate using the project config (default: .project-standards.yml)
    validate-frontmatter --config .project-standards.yml

    # Override the schema explicitly
    validate-frontmatter --schema schemas/markdown-frontmatter.schema.json examples/*.md

Schema resolution order: --schema (path) > config markdown.frontmatter.schema
(bundled name or path) > the bundled "markdown-frontmatter" schema.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

# Frontmatter is only recognised at the very top of the file (\A anchor). A block
# that appears anywhere else is intentionally NOT treated as frontmatter, so such
# files are reported as "no frontmatter found" when frontmatter is required.
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)

_DEFAULT_SCHEMA_NAME = "markdown-frontmatter"
_DEFAULT_CONFIG = Path(".project-standards.yml")


# ---------------------------------------------------------------------------
# Schema location (works both from a source checkout and an installed wheel)
# ---------------------------------------------------------------------------

def find_bundled_schema(name: str) -> Path:
    """Resolve a bundled schema *name* to its on-disk path.

    Two layouts are supported so the validator works whether it runs from a git
    checkout of this repo or from a `uv tool install git+...` wheel (where the
    schema is force-included under the package directory; see pyproject.toml).
    """
    filename = f"{name}.schema.json"
    candidates = [
        Path(__file__).parent.parent / "schemas" / filename,  # source checkout
        Path(__file__).parent / "schemas" / filename,         # packaged wheel
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]  # surface a clear read error against the canonical path


def resolve_schema_path(schema_value: str | None) -> Path:
    """Resolve a config `schema` value to a path.

    A bare token (e.g. "markdown-frontmatter") is treated as a bundled schema
    name; anything containing a path separator or ending in `.json` is treated
    as a filesystem path.
    """
    name = schema_value or _DEFAULT_SCHEMA_NAME
    if "/" in name or "\\" in name or name.endswith(".json"):
        return Path(name)
    return find_bundled_schema(name)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _coerce_dates(obj: Any) -> Any:
    """Recursively convert datetime.date/datetime to ISO strings.

    YAML's safe_load parses unquoted dates (2026-06-02) as datetime.date, but the
    schema validates them as strings. Coercing here lets authors write either form.
    """
    if isinstance(obj, datetime.datetime):
        return obj.date().isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, dict):
        mapping = cast(dict[str, Any], obj)
        return {k: _coerce_dates(v) for k, v in mapping.items()}
    if isinstance(obj, list):
        sequence = cast(list[Any], obj)
        return [_coerce_dates(v) for v in sequence]
    return obj


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Return the parsed YAML frontmatter mapping, or None if absent/non-mapping."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    loaded = yaml.safe_load(match.group(1))
    if not isinstance(loaded, dict):
        return None
    return cast("dict[str, Any]", _coerce_dates(loaded))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_file(
    path: Path,
    validator: Draft202012Validator,
    *,
    require_frontmatter: bool,
) -> list[str]:
    """Validate a single file; return a list of human-readable error strings."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read file: {exc}"]

    meta = parse_frontmatter(text)
    if meta is None:
        if require_frontmatter:
            return [f"{path}: no frontmatter found at top of file"]
        return []

    errors: list[str] = []
    for error in sorted(validator.iter_errors(meta), key=lambda e: list(e.path)):  # pyright: ignore[reportUnknownMemberType]
        field = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"{path}: [{field}] {error.message}")
    return errors


# ---------------------------------------------------------------------------
# Path collection
# ---------------------------------------------------------------------------

def collect_paths(
    explicit: list[Path],
    glob_pattern: str | None,
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> list[Path]:
    """Resolve the final set of files to check.

    Explicit file arguments and/or a --glob take precedence: when either is given,
    the config `include` patterns are NOT added (naming files means "just these").
    Only when nothing is named do we fall back to config `include`, and failing
    that to every Markdown file under cwd. `exclude` is applied in all cases.
    """
    paths: set[Path] = set()

    if explicit or glob_pattern:
        paths.update(p for p in explicit if p.is_file())
        if glob_pattern:
            paths.update(p for p in Path().glob(glob_pattern) if p.is_file())
    elif include_patterns:
        for pattern in include_patterns:
            paths.update(p for p in Path().glob(pattern) if p.is_file())
    else:
        paths.update(p for p in Path().glob("**/*.md") if p.is_file())

    excluded: set[Path] = set()
    for pattern in exclude_patterns:
        excluded.update(Path().glob(pattern))

    return sorted(paths - excluded)


# ---------------------------------------------------------------------------
# Config (nested markdown.frontmatter shape)
# ---------------------------------------------------------------------------

class FrontmatterConfig:
    """Resolved view of the `markdown.frontmatter` section of the config file."""

    def __init__(
        self,
        *,
        schema: str | None,
        include: list[str],
        exclude: list[str],
        required: bool,
    ) -> None:
        self.schema = schema
        self.include = include
        self.exclude = exclude
        self.required = required


def _as_str_list(value: Any) -> list[str]:
    """Coerce a config value into a list of strings (anything else -> empty list)."""
    if isinstance(value, list):
        return [str(item) for item in cast("list[Any]", value)]
    return []


def load_config(path: Path) -> FrontmatterConfig:
    """Read the nested `markdown.frontmatter` config; missing keys fall back to defaults."""
    schema: str | None = None
    include: list[str] = []
    exclude: list[str] = []
    required = True

    if path.exists():
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw_dict = cast("dict[str, Any]", raw)
            markdown = raw_dict.get("markdown")
            if isinstance(markdown, dict):
                markdown_dict = cast("dict[str, Any]", markdown)
                frontmatter = markdown_dict.get("frontmatter")
                if isinstance(frontmatter, dict):
                    fm = cast("dict[str, Any]", frontmatter)
                    schema_val = fm.get("schema")
                    schema = schema_val if isinstance(schema_val, str) else None
                    include = _as_str_list(fm.get("include"))
                    exclude = _as_str_list(fm.get("exclude"))
                    required = bool(fm.get("required", True))

    return FrontmatterConfig(schema=schema, include=include, exclude=exclude, required=required)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        metavar="FILE",
        help="Markdown files to validate. With no files/globs/config includes, "
        "defaults to all **/*.md under cwd.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        metavar="PATH",
        help="JSON Schema file to validate against (overrides the config).",
    )
    parser.add_argument(
        "--glob",
        metavar="PATTERN",
        help="Additional glob pattern relative to cwd.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG,
        metavar="PATH",
        help=f"Project config file (default: {_DEFAULT_CONFIG}).",
    )
    parser.add_argument(
        "--no-require-frontmatter",
        action="store_true",
        help="Do not fail files that have no frontmatter block.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress success output.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)

    schema_path = args.schema if args.schema is not None else resolve_schema_path(config.schema)
    try:
        schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot load schema {schema_path}: {exc}", file=sys.stderr)
        return 2

    try:
        Draft202012Validator.check_schema(schema)  # pyright: ignore[reportUnknownMemberType]
    except SchemaError as exc:
        print(f"error: invalid schema {schema_path}: {exc.message}", file=sys.stderr)
        return 2
    validator = Draft202012Validator(schema)

    require_frontmatter = config.required and not args.no_require_frontmatter
    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)

    if not paths:
        if not args.quiet:
            print("no files matched", file=sys.stderr)
        return 0

    all_errors: list[str] = []
    for path in paths:
        all_errors.extend(validate_file(path, validator, require_frontmatter=require_frontmatter))

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        print(
            f"\n✗  {len(all_errors)} error(s) across {len(paths)} file(s)",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(f"✓  {len(paths)} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
