#!/usr/bin/env python3
"""Validate YAML frontmatter in Markdown files against the project schema.

The validator is the runtime half of the Markdown Frontmatter Standard
(see standards/markdown-frontmatter/README.md). It detects a leading YAML frontmatter
block, parses it safely, and validates it against a JSON Schema (Draft 2020-12).

Usage:
    # Validate explicit files
    validate-frontmatter README.md docs/adr.md

    # Validate using the project config (default: .project-standards.yml)
    validate-frontmatter --config .project-standards.yml

    # Override the schema explicitly
    validate-frontmatter --schema src/project_standards/schemas/markdown-frontmatter.schema.json standards/markdown-frontmatter/examples/*.md

Schema resolution order: --schema (path) > config markdown.frontmatter.schema
(bundled name or path) > the bundled "markdown-frontmatter" schema.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from project_standards.registry import Registry, RegistryError, load_registry

# Frontmatter is only recognised at the very top of the file (\A anchor). A block
# that appears anywhere else is intentionally NOT treated as frontmatter, so such
# files are reported as "no frontmatter found" when frontmatter is required.
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)

_DEFAULT_SCHEMA_NAME = "markdown-frontmatter"
_DEFAULT_CONFIG = Path(".project-standards.yml")


class FrontmatterParseError(ValueError):
    """A frontmatter block is present but is not valid YAML.

    Distinct from "no block" / "non-mapping block" (which parse_frontmatter
    returns None for): this is a syntax error in an otherwise-present block, and
    must surface as a clean validation error rather than an uncaught traceback.
    """


class ConfigError(ValueError):
    """The config file exists but is not valid YAML — an operator error (exit 2)."""


# ---------------------------------------------------------------------------
# Schema location (works both from a source checkout and an installed wheel)
# ---------------------------------------------------------------------------


def find_bundled_schema(name: str) -> Path:
    """Resolve a bundled schema *name* to its on-disk path.

    The schema ships inside the package (``project_standards/schemas/``), so the
    same relative path resolves whether the validator runs from a source checkout
    or from a ``uv tool install`` wheel. A missing name returns the canonical
    on-disk location (which may not exist) so the caller surfaces a clear read error.
    """
    return Path(__file__).parent / "schemas" / f"{name}.schema.json"


def _schema_value_is_path(value: str | None) -> bool:
    """True when a config `schema` value names a filesystem path, not a bundled name.

    A bare token (e.g. "markdown-frontmatter") is a bundled schema name; anything
    with a path separator or a `.json` suffix is a path the consumer owns.
    """
    return value is not None and ("/" in value or "\\" in value or value.endswith(".json"))


def resolve_schema_path(schema_value: str | None) -> Path:
    """Resolve a config `schema` value to a path.

    A bare token is treated as a bundled schema name; anything containing a path
    separator or ending in `.json` is treated as a filesystem path.
    """
    if _schema_value_is_path(schema_value):
        return Path(cast("str", schema_value))
    return find_bundled_schema(schema_value or _DEFAULT_SCHEMA_NAME)


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
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise FrontmatterParseError(str(exc)) from exc
    if not isinstance(loaded, dict):
        return None
    return cast("dict[str, Any]", _coerce_dates(loaded))


# ---------------------------------------------------------------------------
# ADR body-structure check (opt-in; see standards/adr/README.md + DEC-5)
# ---------------------------------------------------------------------------

# The three sections MADR 4.0 marks REQUIRED. Consequences, Confirmation,
# Decision Drivers, Pros and Cons, and More Information are optional in MADR and
# are intentionally NOT demanded here — requiring them would fight MADR's
# short→large flexibility.
_ADR_REQUIRED_SECTIONS = (
    "Context and Problem Statement",
    "Considered Options",
    "Decision Outcome",
)

# A level-2 ATX heading: exactly two `#`, then whitespace, then the title. The
# `[ \t]+` after `##` excludes `###` (level 3) because the third `#` is not
# whitespace. Match is case-sensitive — MADR section titles are fixed strings.
_H2_HEADING_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$")

# A fenced-code-block delimiter (``` or ~~~, optionally indented / with a
# language). Headings inside a fence are illustrative (e.g. a template snippet),
# not the document's own structure, so they must not count as present.
_CODE_FENCE_RE = re.compile(r"^[ \t]*(?:```|~~~)")


def missing_adr_sections(text: str) -> list[str]:
    """Return the MADR-required `##` sections absent from a document, in order.

    Pure helper for the opt-in ADR body-structure check (DEC-5): scans level-2
    ATX headings — skipping any inside fenced code blocks — and reports which of
    the three required MADR 4.0 sections are missing. Returns ``[]`` when all
    three are present.
    """
    present: set[str] = set()
    in_code_fence = False
    for line in text.splitlines():
        if _CODE_FENCE_RE.match(line):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        match = _H2_HEADING_RE.match(line)
        if match:
            present.add(match.group(1))
    return [section for section in _ADR_REQUIRED_SECTIONS if section not in present]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_file(
    path: Path,
    validator: Draft202012Validator,
    *,
    require_frontmatter: bool,
    require_adr_sections: bool = False,
) -> list[str]:
    """Validate a single file; return a list of human-readable error strings.

    When ``require_adr_sections`` is set, documents with ``doc_type: adr`` are
    additionally checked for the three MADR-required ``##`` sections (DEC-5).
    Off by default, so existing callers are unaffected.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read file: {exc}"]

    try:
        meta = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        return [f"{path}: invalid YAML frontmatter: {exc}"]
    if meta is None:
        if require_frontmatter:
            return [f"{path}: no frontmatter found at top of file"]
        return []

    errors: list[str] = []
    for error in sorted(validator.iter_errors(meta), key=lambda e: list(e.path)):  # pyright: ignore[reportUnknownMemberType]
        field = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"{path}: [{field}] {error.message}")

    if require_adr_sections and meta.get("doc_type") == "adr":
        for section in missing_adr_sections(text):
            errors.append(f"{path}: missing required ADR section '## {section}'")
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

    # Exclusion matches each candidate's posix path against the patterns with fnmatch
    # rather than Path.glob. Path.glob's `**` semantics are version-dependent (on Python
    # 3.13+ a trailing `**` also matches files; on <=3.12 it matches directories only),
    # so a directory pattern like "docs/decisions/**" would silently fail to exclude the
    # files beneath it on older interpreters. fnmatch's `*` spans path
    # separators, giving consistent prefix-style exclusion on every supported
    # Python version.
    def is_excluded(path: Path) -> bool:
        posix = path.as_posix()
        return any(fnmatchcase(posix, pattern) for pattern in exclude_patterns)

    return sorted(p for p in paths if not is_excluded(p))


# ---------------------------------------------------------------------------
# Config (nested markdown.{frontmatter,adr} shape)
# ---------------------------------------------------------------------------


class ProjectConfig:
    """Resolved view of `.project-standards.yml`.

    Holds the `markdown.frontmatter` settings (schema/include/exclude/required)
    plus the separate, opt-in `markdown.adr` flags. The two namespaces stay
    conceptually distinct in the file; this is the validator's merged in-memory
    view of them.
    """

    def __init__(
        self,
        *,
        schema: str | None,
        include: list[str],
        exclude: list[str],
        required: bool,
        require_adr_sections: bool,
        frontmatter_version: str | None = None,
        adr_version: str | None = None,
        python_tooling_version: str | None = None,
        markdown_tooling_version: str | None = None,
    ) -> None:
        self.schema = schema
        self.include = include
        self.exclude = exclude
        self.required = required
        self.require_adr_sections = require_adr_sections
        self.frontmatter_version = frontmatter_version
        self.adr_version = adr_version
        self.python_tooling_version = python_tooling_version
        self.markdown_tooling_version = markdown_tooling_version


def resolve_effective_schema(
    args_schema: Path | None, config: ProjectConfig, registry: Registry
) -> Path:
    """Pick the schema file, honouring the documented precedence.

    Precedence (first match wins): ``--schema`` path > a custom ``schema:`` path >
    ``frontmatter.version`` (resolved via the registry to a bundled schema) >
    ``schema:`` bundled name > the default bundled schema. Version selection
    applies only to bundled schemas; a custom schema path means the consumer owns
    versioning, so combining it with ``frontmatter.version`` is rejected rather
    than silently dropping one. Raises ConfigError (ambiguity) or RegistryError
    (unknown bundled version).
    """
    if args_schema is not None:
        return args_schema
    schema_value = config.schema
    custom_path = _schema_value_is_path(schema_value)
    if custom_path and config.frontmatter_version is not None:
        raise ConfigError(
            "set markdown.frontmatter.schema (a custom path) or "
            "markdown.frontmatter.version, not both"
        )
    if custom_path:
        return Path(cast("str", schema_value))
    if config.frontmatter_version is not None:
        return find_bundled_schema(registry.frontmatter_schema_name(config.frontmatter_version))
    return resolve_schema_path(schema_value)


def frontmatter_adr_incompatibility(config: ProjectConfig, registry: Registry) -> str | None:
    """Return an error message if the configured ADR/Frontmatter pair is incompatible.

    Only meaningful when ADR is in play AND Frontmatter is a *bundled* contract — a
    custom ``schema:`` path means the consumer owns versioning, so the check is
    skipped. Assumes a configured ``frontmatter.version`` has already been validated
    as bundled by ``resolve_effective_schema`` (so this never masks an unknown
    version as an incompatibility). Returns None when compatible or not applicable;
    raises RegistryError if the configured ADR version is unknown.
    """
    if _schema_value_is_path(config.schema):
        return None
    if not (config.require_adr_sections or config.adr_version is not None):
        return None
    adr_version = config.adr_version or registry.adr_default
    effective_fm = config.frontmatter_version or registry.frontmatter_default
    supported = registry.adr_supported_frontmatter(adr_version)
    if effective_fm not in supported:
        return (
            f"ADR {adr_version} supports Frontmatter {supported}; "
            f"configured frontmatter.version is {effective_fm}"
        )
    return None


def _as_str_list(value: Any) -> list[str]:
    """Coerce a config value into a list of strings (anything else -> empty list)."""
    if isinstance(value, list):
        return [str(item) for item in cast("list[Any]", value)]
    return []


def load_config(path: Path) -> ProjectConfig:
    """Read nested `markdown.frontmatter` + `markdown.adr`; missing keys default."""
    schema: str | None = None
    include: list[str] = []
    exclude: list[str] = []
    required = True
    require_adr_sections = False
    frontmatter_version: str | None = None
    adr_version: str | None = None
    python_tooling_version: str | None = None
    markdown_tooling_version: str | None = None

    if path.exists():
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigError(f"cannot parse config {path}: {exc}") from exc
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
                    version_val = fm.get("version")
                    frontmatter_version = str(version_val) if version_val is not None else None
                adr = markdown_dict.get("adr")
                if isinstance(adr, dict):
                    adr_dict = cast("dict[str, Any]", adr)
                    require_adr_sections = bool(adr_dict.get("require_sections", False))
                    adr_version_val = adr_dict.get("version")
                    adr_version = str(adr_version_val) if adr_version_val is not None else None
            python_tooling = raw_dict.get("python_tooling")
            if isinstance(python_tooling, dict):
                pt_dict = cast("dict[str, Any]", python_tooling)
                pt_version_val = pt_dict.get("version")
                python_tooling_version = str(pt_version_val) if pt_version_val is not None else None
            markdown_tooling = raw_dict.get("markdown_tooling")
            if isinstance(markdown_tooling, dict):
                mt_dict = cast("dict[str, Any]", markdown_tooling)
                mt_version_val = mt_dict.get("version")
                markdown_tooling_version = (
                    str(mt_version_val) if mt_version_val is not None else None
                )

    return ProjectConfig(
        schema=schema,
        include=include,
        exclude=exclude,
        required=required,
        require_adr_sections=require_adr_sections,
        frontmatter_version=frontmatter_version,
        adr_version=adr_version,
        python_tooling_version=python_tooling_version,
        markdown_tooling_version=markdown_tooling_version,
    )


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

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        registry = load_registry()
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # python_tooling.version is metadata only: validated if present, never emitted.
    if config.python_tooling_version is not None and not registry.is_known_python_tooling(
        config.python_tooling_version
    ):
        print(
            f"error: unknown python_tooling.version {config.python_tooling_version!r}",
            file=sys.stderr,
        )
        return 2

    # markdown_tooling.version is metadata only: validated if present, never emitted.
    if config.markdown_tooling_version is not None and not registry.is_known_markdown_tooling(
        config.markdown_tooling_version
    ):
        print(
            f"error: unknown markdown_tooling.version {config.markdown_tooling_version!r}",
            file=sys.stderr,
        )
        return 2

    # Resolve first: this validates that a configured frontmatter.version is a known
    # bundled contract (unknown/typo versions report "unknown frontmatter version"
    # here, before the compatibility gate, so they are never masked as a combo error).
    try:
        schema_path = resolve_effective_schema(args.schema, config, registry)
    except (ConfigError, RegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # FM->ADR compatibility (bundled Frontmatter only; --schema bypasses it).
    if args.schema is None:
        try:
            incompatibility = frontmatter_adr_incompatibility(config, registry)
        except RegistryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if incompatibility is not None:
            print(f"error: {incompatibility}", file=sys.stderr)
            return 2

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
        all_errors.extend(
            validate_file(
                path,
                validator,
                require_frontmatter=require_frontmatter,
                require_adr_sections=config.require_adr_sections,
            )
        )

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
