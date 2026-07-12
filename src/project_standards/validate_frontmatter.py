#!/usr/bin/env python3
"""Validate YAML frontmatter in Markdown files against the project schema.

The validator is the runtime half of the Markdown Frontmatter Standard
(see standards/markdown-frontmatter/README.md). It detects a leading YAML frontmatter
block, parses it safely, and validates it against a JSON Schema (Draft 2020-12).

Usage:
    # Validate explicit files
    validate-frontmatter README.md docs/adr.md

    # Validate using unified repository config
    validate-frontmatter

    # Override the schema explicitly
    validate-frontmatter --schema src/project_standards/schemas/markdown-frontmatter.schema.json standards/markdown-frontmatter/examples/*.md

Schema resolution order: --schema (path) > config markdown.frontmatter.schema
(bundled name or path) > the bundled "markdown-frontmatter" schema.

Exit codes: 0 = all matched files valid (or none matched); 1 = validation errors;
2 = operator error (config, schema, registry, or invocation).

This module is also the HUB of the validator family: validate_id,
validate_references, and format_frontmatter import its primitives
(parse_frontmatter, load_config, collect_paths, ConfigError,
schema_value_is_path, resolve_effective_schema, reconfigure_output_streams).
A change to any of those signatures or semantics propagates to every console
script in the package.
"""

from __future__ import annotations

import argparse
import datetime
import io
import json
import os
import re
import sys
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from project_standards._version import package_version
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    SelectedCommandPackage,
    emit_legacy_authority_warning,
    explicit_legacy_argument,
    resolve_selected_package,
    selected_command,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.locking import LockMode
from project_standards.control_plane.models import CentralLock
from project_standards.control_plane.providers import read_locked_input_bytes
from project_standards.registry import Registry, RegistryError, load_registry

# Frontmatter is only recognised at the very top of the file (\A anchor). A block
# that appears anywhere else is intentionally NOT treated as frontmatter, so such
# files are reported as "no frontmatter found" when frontmatter is required.
# Fence lines tolerate trailing spaces/tabs (Jekyll/python-frontmatter do too) so a
# stray trailing space cannot flip a valid file to "missing frontmatter".
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)

_DEFAULT_SCHEMA_NAME = "markdown-frontmatter"


class FrontmatterParseError(ValueError):
    """A frontmatter block is present but is not valid YAML.

    Distinct from "no block" / "non-mapping block" (which parse_frontmatter
    returns None for): this is a syntax error in an otherwise-present block, and
    must surface as a clean validation error rather than an uncaught traceback.
    """


class ConfigError(ValueError):
    """An operator/invocation error: unreadable or invalid config, a bad glob or
    named file, a non-string version value, or an unloadable doc_type enum.

    Every CLI boundary in the package maps this to exit 2, so raising it from a
    shared helper is the one sanctioned way to abort with a clean operator error.
    """


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


def schema_value_is_path(value: str | None) -> bool:
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
    if schema_value_is_path(schema_value):
        return Path(cast("str", schema_value))
    return find_bundled_schema(schema_value or _DEFAULT_SCHEMA_NAME)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (PyYAML otherwise keeps the
    last silently). Frontmatter with a duplicate key is a bug, not a valid doc."""


def _construct_no_duplicates(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = cast(Any, loader.construct_object(key_node, deep=True))  # pyright: ignore[reportUnknownMemberType]
        try:
            duplicate = key in mapping
        except TypeError as exc:
            # A YAML complex key (e.g. `? [a, b]`) constructs to an unhashable value.
            # PyYAML's stock constructor guards this; the override must too, or the
            # TypeError escapes parse_frontmatter's yaml.YAMLError catch as a traceback.
            raise yaml.constructor.ConstructorError(
                None, None, f"found unhashable key {key!r}", key_node.start_mark
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=True)  # pyright: ignore[reportUnknownMemberType]
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_no_duplicates
)


def _coerce_dates(obj: Any) -> Any:
    """Recursively convert datetime.date values to ISO strings.

    YAML's safe_load parses unquoted dates (2026-06-02) as datetime.date, but the
    schema validates them as strings. Coercing here lets authors write either form.
    datetime.datetime is deliberately NOT coerced: truncating the time would let a
    file whose literal content violates the YYYY-MM-DD contract pass validation,
    so it is left for the string-typed schema to reject.
    """
    if isinstance(obj, datetime.datetime):
        return obj
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
    """Return the parsed YAML frontmatter mapping, or None if absent/non-mapping.

    Raises FrontmatterParseError for a present-but-invalid block: a YAML syntax
    error, a duplicate top-level key, or a non-string key. Callers across the
    package rely on exactly this split — None means "skip / report missing",
    the exception means "report the block as broken".
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        loaded = yaml.load(match.group(1), Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise FrontmatterParseError(str(exc)) from exc
    if not isinstance(loaded, dict):
        return None
    # YAML 1.1 coerces some plain keys to non-strings (`on:` -> True, `2026:` -> int).
    # Reject them explicitly so the dict[str, Any] cast below states a real invariant
    # instead of laundering surprise key types into jsonschema and error formatting.
    for key in cast("dict[Any, Any]", loaded):
        if not isinstance(key, str):
            raise FrontmatterParseError(
                f"non-string frontmatter key {key!r} (quote YAML-coerced keys like 'on')"
            )
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
# whitespace. An optional ATX closing sequence (`## Title ##`) is stripped —
# CommonMark allows it and it must not defeat the exact-title match. Match is
# case-sensitive — MADR section titles are fixed strings.
_H2_HEADING_RE = re.compile(r"^##[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")

# A fenced-code-block delimiter (``` or ~~~, indented at most 3 spaces per
# CommonMark — deeper indentation is indented code, not a fence). Headings inside
# a fence are illustrative (e.g. a template snippet), not the document's own
# structure, so they must not count as present. The marker char and length are
# captured because a fence closes only with the SAME char at >= length: a `~~~`
# line inside a backtick fence, or three backticks inside a four-backtick fence,
# is content, not a closer.
_CODE_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_CODE_FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


def missing_adr_sections(text: str) -> list[str]:
    """Return the MADR-required `##` sections absent from a document, in order.

    Pure helper for the opt-in ADR body-structure check (DEC-5): scans level-2
    ATX headings — skipping any inside fenced code blocks — and reports which of
    the three required MADR 4.0 sections are missing. Returns ``[]`` when all
    three are present.
    """
    present: set[str] = set()
    open_fence: str | None = None  # the opening fence marker (e.g. "```" or "~~~~")
    for line in text.splitlines():
        if open_fence is not None:
            close = _CODE_FENCE_CLOSE_RE.match(line)
            if (
                close
                and close.group(1)[0] == open_fence[0]
                and len(close.group(1)) >= len(open_fence)
            ):
                open_fence = None
            continue
        fence = _CODE_FENCE_RE.match(line)
        if fence:
            open_fence = fence.group(1)
            continue
        match = _H2_HEADING_RE.match(line)
        if match:
            present.add(match.group(1))
    return [section for section in _ADR_REQUIRED_SECTIONS if section not in present]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


# Shape of the schema's date pattern. The code-level calendar check below only fires
# on values the schema pattern already accepts, so impossible dates (2026-13-40) get
# exactly one error and malformed shapes keep their schema pattern error.
_DATE_SHAPE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# The standard's top-level date fields. Custom schemas without them are a no-op here.
_DATE_FIELDS = ("created", "updated", "reviewed")


def _no_frontmatter_reason(text: str) -> str:
    """Explain why parse_frontmatter returned None, for the error message.

    A present-but-non-mapping block and an unterminated block both parse to None,
    but telling the author "no frontmatter found" while they stare at a visible
    `---` block misdiagnoses the problem. None stays the parse contract; only the
    reported reason is refined here.
    """
    if _FRONTMATTER_RE.match(text):
        return "frontmatter block is not a YAML mapping"
    # This probe is _FRONTMATTER_RE's opening fence with no closing fence; the two
    # must stay in sync or an unterminated block gets misreported as absent.
    if re.match(r"\A---[ \t]*\r?\n", text):
        return "frontmatter block is not terminated by ---"
    return "no frontmatter found at top of file"


def validate_file(
    path: Path,
    validator: Draft202012Validator,
    *,
    require_frontmatter: bool,
    require_adr_sections: bool = False,
) -> list[str]:
    """Validate a single file; return a list of human-readable error strings.

    Never raises for a bad file: unreadable, undecodable, and malformed inputs
    all degrade to returned error strings, so one broken file cannot abort a
    batch run.

    When ``require_adr_sections`` is set, documents with ``doc_type: adr`` are
    additionally checked for the three MADR-required ``##`` sections (DEC-5).
    Off by default, so existing callers are unaffected.
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        # UnicodeDecodeError is a ValueError, not an OSError: a non-UTF-8 file matched
        # by a glob must fail as one per-file error, never as an uncaught traceback.
        return [f"{path}: cannot read file: {exc}"]

    try:
        meta = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        return [f"{path}: invalid YAML frontmatter: {exc}"]
    if meta is None:
        if require_frontmatter:
            return [f"{path}: {_no_frontmatter_reason(text)}"]
        return []

    errors: list[str] = []
    # Sort key stringifies path elements: raw paths mix str keys with int array
    # indices, and comparing those raises TypeError under custom schemas whose
    # error paths diverge in type at the same position.
    for error in sorted(validator.iter_errors(meta), key=lambda e: [str(p) for p in e.path]):  # pyright: ignore[reportUnknownMemberType]
        field = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"{path}: [{field}] {error.message}")

    # The schema's date pattern accepts calendar-impossible values (2026-13-40);
    # jsonschema does not enforce format:date by default, so check it here (F36).
    for field_name in _DATE_FIELDS:
        value = meta.get(field_name)
        if isinstance(value, str) and _DATE_SHAPE_RE.fullmatch(value):
            try:
                datetime.date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: [{field_name}] '{value}' is not a real calendar date")

    if require_adr_sections and meta.get("doc_type") == "adr":
        for section in missing_adr_sections(text):
            errors.append(f"{path}: missing required ADR section '## {section}'")
    return errors


# ---------------------------------------------------------------------------
# Path collection
# ---------------------------------------------------------------------------


def _default_corpus() -> list[Path]:
    """Every Markdown file under cwd, skipping hidden and vendored trees.

    A bare Path().glob("**/*.md") is rejected here because it recurses into
    .git/, .venv/ and node_modules/ — the advertised zero-config default would
    become unusable after the first dependency install, and validate-references'
    index would fill with vendored docs. Hidden components and node_modules are
    pruned during traversal, so those trees are never walked at all. Explicit
    include patterns are untouched: a repo that wants hidden paths can name them.
    """
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        for filename in filenames:
            if filename.endswith(".md") and not filename.startswith("."):
                found.append(Path(dirpath, filename))
    return found


def _glob_files(pattern: str) -> list[Path]:
    """Glob *pattern* relative to cwd, surfacing bad patterns as operator errors.

    Path.glob raises NotImplementedError for absolute patterns (and ValueError for
    other unsupported shapes); uncaught, that exits 1 looking like a validator
    crash instead of the documented exit-2 invocation error.
    """
    try:
        return [p for p in Path().glob(pattern) if p.is_file()]
    except (NotImplementedError, ValueError) as exc:
        raise ConfigError(
            f"invalid glob pattern {pattern!r} (patterns must be relative to the repo root): {exc}"
        ) from exc


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

    Raises ConfigError for an explicitly named file that does not exist: globs and
    includes may legitimately match nothing, but silently dropping a named file
    turns a typo'd CI invocation into a green run that validated nothing.

    Pattern-dialect warning: include patterns use Path.glob semantics (`*` stops at
    `/`), but exclude patterns use fnmatch semantics where `*` ALSO spans path
    separators — `docs/*.md` excludes nested files too. This asymmetry is the price
    of version-independent `dir/**` exclusion (see the comment below); write exclude
    patterns accordingly.
    """
    paths: set[Path] = set()

    if explicit or glob_pattern:
        missing = [p for p in explicit if not p.is_file()]
        if missing:
            raise ConfigError("no such file: " + ", ".join(str(p) for p in missing))
        paths.update(explicit)
        if glob_pattern:
            paths.update(_glob_files(glob_pattern))
    elif include_patterns:
        for pattern in include_patterns:
            paths.update(_glob_files(pattern))
    else:
        paths.update(_default_corpus())

    # Exclusion matches each candidate's posix path against the patterns with fnmatch
    # rather than Path.glob. Path.glob's `**` semantics are version-dependent (on Python
    # 3.13+ a trailing `**` also matches files; on <=3.12 it matches directories only),
    # so a directory pattern like "docs/decisions/**" would silently fail to exclude the
    # files beneath it on older interpreters. fnmatch's `*` spans path
    # separators, giving consistent prefix-style exclusion on every supported
    # Python version.
    cwd = Path.cwd().resolve()

    def _match_key(path: Path) -> str:
        # Exclude patterns are written repo-root-relative; an explicitly passed
        # absolute path must not bypass them just because its string form differs.
        candidate = path if path.is_absolute() else cwd / path
        try:
            return candidate.resolve().relative_to(cwd).as_posix()
        # Unparenthesized multi-exception is PEP 758 (Python >=3.14 only) and is
        # what ruff format enforces here — re-adding parens gets stripped. Do not
        # vendor this file onto older interpreters without re-parenthesizing.
        except OSError, ValueError:
            return path.as_posix()  # outside the repo root — match the raw form

    def is_excluded(path: Path) -> bool:
        key = _match_key(path)
        return any(fnmatchcase(key, pattern) for pattern in exclude_patterns)

    return sorted(p for p in paths if not is_excluded(p))


# ---------------------------------------------------------------------------
# Config (nested markdown.{frontmatter,adr} shape)
# ---------------------------------------------------------------------------


class ProjectConfig:
    """Resolved frontmatter options from unified or explicit legacy authority.

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
        cli_documentation_version: str | None = None,
        project_spec_version: str | None = None,
        references_enabled: bool = False,
        unified_authority: bool = False,
        selected_package_version: str = "1.2",
        custom_schema_bytes: bytes | None = None,
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
        self.cli_documentation_version = cli_documentation_version
        self.project_spec_version = project_spec_version
        self.references_enabled = references_enabled
        self.unified_authority = unified_authority
        self.selected_package_version = selected_package_version
        self.custom_schema_bytes = custom_schema_bytes


def resolve_effective_schema(
    args_schema: Path | None, config: ProjectConfig, registry: Registry | None
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
    custom_path = schema_value_is_path(schema_value)
    if custom_path and config.frontmatter_version is not None and not config.unified_authority:
        raise ConfigError(
            "set markdown.frontmatter.schema (a custom path) or "
            "markdown.frontmatter.version, not both"
        )
    if custom_path:
        return Path(cast("str", schema_value))
    if config.frontmatter_version is not None:
        # Callers load the registry lazily; a configured version is one of the
        # conditions that requires it, so None here is a caller bug, not user error.
        if registry is None:
            raise RegistryError("registry required to resolve markdown.frontmatter.version")
        resolved_name = registry.frontmatter_schema_name(config.frontmatter_version)
        # A bundled NAME alongside a version is only redundant while they agree;
        # letting the version silently win would reintroduce — for names — the same
        # ambiguity the path case above rejects loudly.
        if schema_value is not None and schema_value != resolved_name:
            raise ConfigError(
                f"markdown.frontmatter.schema {schema_value!r} does not match the bundled "
                f"schema for frontmatter.version {config.frontmatter_version!r} "
                f"({resolved_name!r}); remove one or make them agree"
            )
        return find_bundled_schema(resolved_name)
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
    if schema_value_is_path(config.schema):
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


def _version_str(value: Any, key: str) -> str | None:
    """A config version value, or None when absent. Strings only — no coercion.

    str() on a YAML float silently mangles versions: an unquoted `version: 1.10`
    parses as the float 1.1 and would pin the wrong contract. Refusing non-strings
    makes the precision loss an operator error instead of a silent downgrade.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(
            f"{key} must be a quoted string (got {value!r}); "
            f"unquoted version numbers lose precision (1.10 parses as 1.1)"
        )
    return value


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
    cli_documentation_version: str | None = None
    project_spec_version: str | None = None
    references_enabled = False

    if path.exists():
        try:
            # _UniqueKeyLoader, not safe_load: a duplicated key in the config that
            # decides WHAT gets validated (two exclude: blocks, say) must error,
            # not silently last-win — the same argument that applies to frontmatter.
            raw: Any = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
        except OSError as exc:
            # exists() passed but the read failed (permissions, path is a directory):
            # an operator error that must exit 2 cleanly, not traceback.
            raise ConfigError(f"cannot read config {path}: {exc}") from exc
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
                    frontmatter_version = _version_str(
                        fm.get("version"), "markdown.frontmatter.version"
                    )
                    references = fm.get("references")
                    if isinstance(references, dict):
                        references_dict = cast("dict[str, Any]", references)
                        references_enabled = bool(references_dict.get("enabled", False))
                    else:
                        references_enabled = False
                adr = markdown_dict.get("adr")
                if isinstance(adr, dict):
                    adr_dict = cast("dict[str, Any]", adr)
                    require_adr_sections = bool(adr_dict.get("require_sections", False))
                    adr_version = _version_str(adr_dict.get("version"), "markdown.adr.version")
            python_tooling = raw_dict.get("python_tooling")
            if isinstance(python_tooling, dict):
                pt_dict = cast("dict[str, Any]", python_tooling)
                python_tooling_version = _version_str(
                    pt_dict.get("version"), "python_tooling.version"
                )
            markdown_tooling = raw_dict.get("markdown_tooling")
            if isinstance(markdown_tooling, dict):
                mt_dict = cast("dict[str, Any]", markdown_tooling)
                markdown_tooling_version = _version_str(
                    mt_dict.get("version"), "markdown_tooling.version"
                )
            cli_documentation = raw_dict.get("cli_documentation")
            if isinstance(cli_documentation, dict):
                cd_dict = cast("dict[str, Any]", cli_documentation)
                cli_documentation_version = _version_str(
                    cd_dict.get("version"), "cli_documentation.version"
                )
            spec = raw_dict.get("spec")
            if isinstance(spec, dict):
                spec_dict = cast("dict[str, Any]", spec)
                project_spec_version = _version_str(spec_dict.get("version"), "spec.version")

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
        cli_documentation_version=cli_documentation_version,
        project_spec_version=project_spec_version,
        references_enabled=references_enabled,
    )


def _unified_string(value: object, *, option: str, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ConfigError(f"markdown-frontmatter option {option} must be a string")
    return value


def _unified_string_list(value: object, *, option: str, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list):
        raise ConfigError(f"markdown-frontmatter option {option} must be a string array")
    items = cast("list[object]", value)
    if not all(isinstance(item, str) for item in items):
        raise ConfigError(f"markdown-frontmatter option {option} must be a string array")
    return list(cast("list[str]", items))


def config_from_unified_options(
    options: Mapping[str, object],
    *,
    selected_package_version: str,
    custom_schema_bytes: bytes | None = None,
) -> ProjectConfig:
    contract_version = _unified_string(
        options.get("contract_version"),
        option="contract_version",
        default="1.1",
    )
    schema_selection = _unified_string(
        options.get("schema"),
        option="schema",
        default="markdown-frontmatter",
    )
    schema_path = options.get("schema_path")
    if schema_selection == "custom":
        if not isinstance(schema_path, str):
            raise ConfigError("custom frontmatter schema selection requires schema_path")
        schema = schema_path
    elif schema_selection == "markdown-frontmatter":
        if schema_path is not None:
            raise ConfigError("bundled frontmatter schema selection forbids schema_path")
        schema = schema_selection
    else:
        raise ConfigError(f"unknown frontmatter schema selection {schema_selection!r}")

    required = options.get("required", True)
    if not isinstance(required, bool):
        raise ConfigError("markdown-frontmatter option required must be a boolean")
    references = options.get("references", {"enabled": False})
    if not isinstance(references, dict):
        raise ConfigError("markdown-frontmatter option references must be a table")
    references_table = cast("dict[str, object]", references)
    references_enabled = references_table.get("enabled", False)
    if not isinstance(references_enabled, bool):
        raise ConfigError("markdown-frontmatter option references.enabled must be a boolean")

    return ProjectConfig(
        schema=schema,
        include=_unified_string_list(
            options.get("include"),
            option="include",
            default=["README.md", "docs/**/*.md"],
        ),
        exclude=_unified_string_list(
            options.get("exclude"),
            option="exclude",
            default=[
                "**/*.template.md",
                "AGENTS.md",
                "CLAUDE.md",
                ".agents/**",
                ".claude/**",
                ".codex/**",
                ".github/**",
                "node_modules/**",
            ],
        ),
        required=required,
        require_adr_sections=False,
        frontmatter_version=contract_version,
        references_enabled=references_enabled,
        unified_authority=True,
        selected_package_version=selected_package_version,
        custom_schema_bytes=custom_schema_bytes,
    )


def _custom_schema_bytes(
    root: Path,
    schema_path: str,
    lock: CentralLock,
) -> bytes:
    matching = [
        item
        for item in lock.referenced_inputs
        if item.standard_id == "markdown-frontmatter"
        and item.extension_id == "custom-schema"
        and item.path.original == schema_path
    ]
    if len(matching) != 1:
        raise ConfigError("custom schema requires exactly one matching locked input")
    try:
        return read_locked_input_bytes(root, matching[0])
    except ControlPlaneError as exc:
        raise ConfigError(f"custom schema locked input is invalid: {exc}") from exc


def load_cli_config(
    repo: Path,
    *,
    explicit_legacy: Path | None,
    allow_unlocked_custom_schema: bool = False,
    distribution: InstalledDistribution | None = None,
    selected_package: SelectedCommandPackage | None = None,
) -> tuple[ProjectConfig, bool]:
    """Resolve unified authority by repository root or an explicit legacy/debug file."""
    if repo.is_symlink():
        raise ConfigError(f"repository root is not a regular directory: {repo}")
    try:
        root = repo.resolve(strict=True)
    except OSError as exc:
        raise ConfigError(f"cannot resolve repository root {repo}") from exc
    if not root.is_dir() or root.is_symlink():
        raise ConfigError(f"repository root is not a regular directory: {repo}")

    default_legacy = root / ".project-standards.yml"
    try:
        selected = selected_package or resolve_selected_package(
            root,
            "markdown-frontmatter",
            distribution,
            explicit_legacy=explicit_legacy,
        )
    except CommandResolutionError as exc:
        message = str(exc)
        if "legacy and unified" in message or "explicit legacy override" in message:
            raise ConfigError(f"dual authority: {message}") from exc
        if "disabled" in message or "not present" in message:
            raise ConfigError("markdown-frontmatter is not enabled in unified config") from exc
        if "payload is unavailable" in message:
            raise ConfigError("markdown-frontmatter selected payload is unavailable") from exc
        raise ConfigError(message) from exc
    if selected is not None:
        options = cast("dict[str, object]", selected.effective_config)
        schema_content: bytes | None = None
        if options.get("schema") == "custom" and not allow_unlocked_custom_schema:
            schema_path = options.get("schema_path")
            if not isinstance(schema_path, str):
                raise ConfigError("custom frontmatter schema selection requires schema_path")
            schema_content = _custom_schema_bytes(root, schema_path, selected.lock)
        return (
            config_from_unified_options(
                options,
                selected_package_version=selected.resolved.value,
                custom_schema_bytes=schema_content,
            ),
            False,
        )

    legacy_path = explicit_legacy if explicit_legacy is not None else default_legacy
    return load_config(legacy_path), legacy_path.exists()


def emit_legacy_config_warning() -> None:
    """Emit the process-wide V5 legacy-authority warning at most once."""
    emit_legacy_authority_warning()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def reconfigure_output_streams() -> None:
    """Make the ✓/✗ summary glyphs safe on non-UTF-8 consoles.

    On a cp1252/C-locale console (Windows, mis-configured self-hosted runners) the
    summary print raises UnicodeEncodeError, turning a clean pass/fail into a
    traceback. errors="replace" degrades the glyphs instead. Streams that are not
    TextIOWrapper (harness doubles, detached pipes) are left alone. Shared by all
    three validator mains.
    """
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="replace")


def main(
    argv: list[str] | None = None,
    *,
    _command_locked: bool = False,
    _selected_package: SelectedCommandPackage | None = None,
) -> int:
    """CLI entry point; returns an exit code (0 valid / 1 violations / 2 operator error)."""
    reconfigure_output_streams()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not _command_locked and not any(
        option in arguments for option in {"--help", "-h", "--version"}
    ):
        try:
            with selected_command(
                Path.cwd(),
                "markdown-frontmatter",
                mode=LockMode.READ,
                explicit_legacy=explicit_legacy_argument(arguments),
            ) as selected:
                if selected is not None:
                    return main(
                        arguments,
                        _command_locked=True,
                        _selected_package=selected,
                    )
        except (CommandResolutionError, OSError, RuntimeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if _selected_package is not None:
        from project_standards.frontmatter_commands import run_locked_standalone_validate

        return run_locked_standalone_validate(
            arguments,
            _selected_package,
            surface="validate-frontmatter",
        )
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version()}")
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
        help="Validate files matching PATTERN (relative to cwd) instead of the "
        "config include list; combines with explicit FILE arguments.",
    )
    # None selects unified repository authority. An operator-typed legacy/debug
    # path that does not exist must still exit 2.
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help="Explicit legacy/debug config; unified config resolves from .standards/.",
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
    args = parser.parse_args(arguments)

    if args.config is not None and not args.config.exists():
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        return 2
    try:
        config, legacy = load_cli_config(
            Path.cwd(),
            explicit_legacy=args.config,
            allow_unlocked_custom_schema=args.schema is not None,
            selected_package=_selected_package,
        )
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if legacy:
        emit_legacy_config_warning()

    # The registry is loaded only when a gate actually consults it (version keys,
    # ADR flags). A wheel with a corrupted registry.json must not break the
    # --schema escape hatch or plain unversioned runs that never need it.
    needs_registry = (
        config.python_tooling_version is not None
        or config.markdown_tooling_version is not None
        or config.cli_documentation_version is not None
        or config.project_spec_version is not None
        or config.frontmatter_version is not None
        or config.adr_version is not None
        or config.require_adr_sections
    )
    registry: Registry | None = None
    if needs_registry:
        try:
            registry = load_registry()
        except RegistryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    # python_tooling.version is metadata only: validated if present, never emitted.
    # (The registry guards below are type-narrowing no-ops: needs_registry loads it
    # whenever the corresponding version key is set.)
    if (
        registry is not None
        and config.python_tooling_version is not None
        and not registry.is_known_python_tooling(config.python_tooling_version)
    ):
        print(
            f"error: unknown python_tooling.version {config.python_tooling_version!r}",
            file=sys.stderr,
        )
        return 2

    # markdown_tooling.version is metadata only: validated if present, never emitted.
    if (
        registry is not None
        and config.markdown_tooling_version is not None
        and not registry.is_known_markdown_tooling(config.markdown_tooling_version)
    ):
        print(
            f"error: unknown markdown_tooling.version {config.markdown_tooling_version!r}",
            file=sys.stderr,
        )
        return 2

    # cli_documentation.version is metadata only: validated if present, never emitted.
    if (
        registry is not None
        and config.cli_documentation_version is not None
        and not registry.is_known_cli_documentation(config.cli_documentation_version)
    ):
        print(
            f"error: unknown cli_documentation.version {config.cli_documentation_version!r}",
            file=sys.stderr,
        )
        return 2

    # spec.version is metadata for the Project Specification Standard and must be
    # known whenever present; the spec subcommand validates the same key directly.
    if (
        registry is not None
        and config.project_spec_version is not None
        and not registry.is_known_project_spec(config.project_spec_version)
    ):
        print(
            f"error: unknown spec.version {config.project_spec_version!r}",
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
    # registry None implies no ADR keys are set, making the gate not applicable.
    if args.schema is None and registry is not None:
        try:
            incompatibility = frontmatter_adr_incompatibility(config, registry)
        except RegistryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if incompatibility is not None:
            print(f"error: {incompatibility}", file=sys.stderr)
            return 2

    try:
        if args.schema is None and config.custom_schema_bytes is not None:
            schema = cast(
                "dict[str, Any]",
                json.loads(config.custom_schema_bytes.decode("utf-8")),
            )
        else:
            schema = cast("dict[str, Any]", json.loads(schema_path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: cannot load schema {schema_path}: {exc}", file=sys.stderr)
        return 2

    try:
        Draft202012Validator.check_schema(schema)  # pyright: ignore[reportUnknownMemberType]
    except SchemaError as exc:
        print(f"error: invalid schema {schema_path}: {exc.message}", file=sys.stderr)
        return 2
    validator = Draft202012Validator(schema)

    require_frontmatter = config.required and not args.no_require_frontmatter
    try:
        paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

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
