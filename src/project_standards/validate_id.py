"""Validate that frontmatter ``id`` fields follow the correct format for their doc_type.

Two formats are in use; which applies depends on ``doc_type``:

**Standard format** — all doc_types except ``adr``:
``{doc_type}-{6-char base36 token}-{readable-slug}``

- ``{doc_type}``        matches the document's own ``doc_type`` field value.
- ``{base36 token}``    is exactly 6 characters from [0-9a-z] (the base-36 alphabet).
- ``{readable-slug}``   is a lowercase kebab-case hint frozen at creation time.
                        It is NOT validated against the current ``title`` — ids must be stable
                        even when documents are renamed.

Example: ``note-a3f9zk-tailscale-acl-tag-ordering-gotcha``.

**ADR format** — ``doc_type: adr``:
``adr-{NNNN}-{repo-name}-{short-title}``

- ``{NNNN}``            is a zero-padded, repo-scoped sequence number (at least 4 digits).
- ``{repo-name}``       is the repository name in kebab-case; it makes the id globally
                        unique so ADRs can be cited by id from other repositories' ``related:``
                        fields without ambiguity.
- ``{short-title}``     is a kebab-case short form of the decision title, set once at creation.

Example: ``adr-0001-homelab-use-postgresql-for-persistent-storage``.

Usage:
    validate-id FILE [FILE ...]
    validate-id
    validate-id --quiet
    validate-id --glob 'docs/**/*.md'
    validate-id --fix

When ``--schema PATH`` is provided, id-format validation is **skipped** (exit 0).
A custom schema signals non-standard id conventions; running the bundled base36 rules
against those files would produce false positives.

``--no-require-frontmatter`` is accepted for compatibility (forwarded by
``project-standards validate``) but has no effect here — id validation already
silently skips files with no frontmatter.

Exit codes: 0 = all ids valid (or skipped due to --schema); 1 = violations found;
2 = config/invocation error.

Files missing frontmatter or missing ``id`` / ``doc_type`` fields are silently
skipped — those structural gaps are the frontmatter schema validator's job.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_standards._version import package_version
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    SelectedCommandPackage,
    explicit_legacy_argument,
    selected_command,
)
from project_standards.control_plane.locking import LockMode
from project_standards.id_format import random_token, slugify
from project_standards.registry import RegistryError, load_registry
from project_standards.validate_frontmatter import (
    ConfigError,
    FrontmatterParseError,
    collect_paths,
    emit_legacy_config_warning,
    load_cli_config,
    parse_frontmatter,
    reconfigure_output_streams,
    resolve_effective_schema,
    schema_value_is_path,
)

# Default bundled schema: the doc_type enum source when no effective schema is
# resolved (direct library calls, tests). main() resolves the enum from the
# EFFECTIVE schema for the loaded config, so a consumer pinning
# markdown.frontmatter.version is checked against that contract's enum, not
# whatever the newest bundled default happens to allow.
_SCHEMA_PATH = Path(__file__).parent / "schemas" / "markdown-frontmatter.schema.json"


@functools.cache
def _load_doc_types(schema_path: Path) -> frozenset[str]:
    """The ``doc_type`` enum from *schema_path*, cached per path.

    Loaded lazily — at import time a broken wheel would kill even
    ``validate-id --help`` with a raw traceback; here a missing or malformed
    schema surfaces as ConfigError, which mains map to exit 2.
    """
    try:
        raw: Any = json.loads(schema_path.read_text(encoding="utf-8"))
        enum_values = cast("list[Any]", raw["properties"]["doc_type"]["enum"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ConfigError(f"cannot load doc_type enum from schema {schema_path}: {exc}") from exc
    doc_types = frozenset(str(v) for v in enum_values)
    # Load-bearing invariant: ids are parsed with split('-', 2), so a hyphenated
    # doc_type (e.g. 'how-to') would misparse every id of that type with confusing
    # prefix errors. A schema revision adding one must change the id grammar first;
    # fail fast at enum load rather than per-document.
    hyphenated = sorted(t for t in doc_types if "-" in t)
    if hyphenated:
        raise ConfigError(
            f"schema {schema_path} defines hyphenated doc_type values {hyphenated}; "
            f"the id grammar (split on '-') cannot parse them"
        )
    return doc_types


# Exactly 6 characters from the base-36 alphabet (digits 0-9 + lowercase letters a-z).
_BASE36_RE = re.compile(r"^[0-9a-z]{6}$")

# Non-empty lowercase kebab-case with no consecutive hyphens: each hyphen must be surrounded
# by at least one alphanumeric on each side (i.e. every segment between hyphens is non-empty).
# slugify() already guarantees this for derived slugs; this guard catches hand-crafted ids
# that would produce double hyphens (e.g. "bad--slug").
_KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# ADR id: adr-{NNNN}-{repo-name}-{short-title}
# NNNN is at least 4 zero-padded digits.  The suffix after the sequence number requires at
# least two hyphen-separated segments (repo-name and short-title); a single-segment suffix
# like "adr-0001-repo" is rejected.  Consecutive hyphens are impossible because each segment
# is [a-z0-9]+.
# Also imported by validate_references, which uses "matches this grammar but isn't
# local" to recognise cross-repo ADR citations — keep the two views of the grammar
# in this one regex.
_ADR_ID_RE = re.compile(r"^adr-[0-9]{4,}-[a-z0-9]+(-[a-z0-9]+)+$")

# Immutable payload 1.2 imports the private name, while later payloads use this
# stable public contract. Both names must continue to resolve to the same regex.
ADR_ID_RE = _ADR_ID_RE


def _validate_adr_id(doc_id: str) -> list[str]:
    """Return violation messages for an ADR id; empty list means valid.

    ADRs use ``adr-{NNNN}-{repo-name}-{short-title}`` rather than the base-36 format
    because the repo-name segment provides global uniqueness: an ADR id remains
    unambiguous when cited from another repository's ``related:`` list. A random token
    cannot provide that property.

    Title-slug consistency is not checked here — the short-title is set once at ADR
    creation and is not expected to track the mutable ``title`` field.
    """
    if not _ADR_ID_RE.match(doc_id):
        return [
            f"ADR id must match adr-{{NNNN}}-{{repo-name}}-{{short-title}} "
            f"(e.g. adr-0001-homelab-use-postgresql); got '{doc_id}'"
        ]
    return []


def validate_id(
    doc_id: str, doc_type: str, valid_doc_types: frozenset[str] | None = None
) -> list[str]:
    """Return violation messages for *doc_id*; empty list means the id is valid.

    *valid_doc_types* is the effective schema's enum; None falls back to the
    default bundled schema (direct library/test callers).

    Dispatches to ``_validate_adr_id`` for ``doc_type == 'adr'`` (sequential-number
    format) and validates the base-36 three-segment format for all other doc_types.

    Standard-format checks in order:
    1. Three segments present: ``{doc_type}-{base36}-{readable-slug}``.
    2. Segment 1 is a valid doc_type and matches the document's ``doc_type`` field.
    3. Segment 2 is exactly 6 base-36 characters ([0-9a-z]{6}).
    4. Segment 3 is non-empty lowercase kebab-case.

    The readable-slug (segment 3) is validated as well-formed kebab-case but NOT matched
    against the current ``title`` — the slug is frozen at creation time and must remain
    stable even if the title is later edited.

    Each returned string is a plain message (no path prefix); callers annotate with path.
    """
    if doc_type == "adr":
        return _validate_adr_id(doc_id)

    doc_types = valid_doc_types if valid_doc_types is not None else _load_doc_types(_SCHEMA_PATH)

    # maxsplit=2 so the readable-slug segment may itself contain hyphens.
    # e.g. "note-a3f9zk-tailscale-acl-gotcha" → ["note", "a3f9zk", "tailscale-acl-gotcha"]
    parts = doc_id.split("-", 2)

    if len(parts) < 3:
        return [
            f"must be '{doc_type}-<6-char base36>-<readable-slug>'; got '{doc_id}' (too few hyphen-separated segments)"
        ]

    id_type, id_base36, id_readable_slug = parts
    errors: list[str] = []

    # --- Segment 1: doc_type prefix ---
    if id_type not in doc_types:
        errors.append(
            f"prefix '{id_type}' is not a valid doc_type (valid: {', '.join(sorted(doc_types))})"
        )
    elif id_type != doc_type:
        # The prefix must exactly match the document's own doc_type — catching cases
        # where a document's type was changed after the id was authored.
        errors.append(f"prefix '{id_type}' does not match the document's doc_type '{doc_type}'")

    # --- Segment 2: base-36 token ---
    if not _BASE36_RE.match(id_base36):
        if len(id_base36) != 6:
            detail = f"got {len(id_base36)} chars"
        else:
            # Right length, so the failure is the charset — saying "(got 6 chars)"
            # would point the author at a length problem that does not exist.
            detail = "contains characters outside [0-9a-z]"
        errors.append(
            f"base-36 segment '{id_base36}' must be exactly 6 characters from [0-9a-z] ({detail})"
        )

    # --- Segment 3: readable slug ---
    if not id_readable_slug:
        errors.append("readable-slug segment (after the base-36 token) is empty")
    elif not _KEBAB_RE.match(id_readable_slug):
        # The message describes _KEBAB_RE in words rather than quoting a regex:
        # a quoted pattern that drifts looser than the enforced one (e.g.
        # [a-z0-9][a-z0-9-]*, which accepts bad--slug) misleads the author.
        errors.append(
            f"readable-slug '{id_readable_slug}' must be lowercase kebab-case "
            f"(alphanumeric runs separated by single hyphens; no leading, trailing, "
            f"or consecutive hyphens)"
        )

    return errors


def check_file(path: Path, valid_doc_types: frozenset[str] | None = None) -> list[str]:
    """Return formatted violation lines for *path*; empty list means the file is clean.

    Files without frontmatter, or whose ``id`` / ``doc_type`` fields are absent or
    have the wrong type, are silently skipped — those gaps are caught by the
    frontmatter schema validator rather than duplicated here. (``title`` is NOT
    inspected: a valid id without a title passes; only ``fix_file`` needs a title.)
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        # UnicodeDecodeError is a ValueError, not an OSError — see validate_file.
        return [f"{path}: cannot read: {exc}"]

    try:
        meta: dict[str, Any] | None = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        return [f"{path}: invalid YAML frontmatter: {exc}"]

    if meta is None:
        return []

    doc_types = valid_doc_types if valid_doc_types is not None else _load_doc_types(_SCHEMA_PATH)
    doc_id = meta.get("id")
    doc_type = meta.get("doc_type")

    # Skip files where the required fields are missing or have wrong types; those
    # structural violations belong to the schema validator's output, not this one's.
    if not isinstance(doc_id, str) or not doc_id:
        return []
    if not isinstance(doc_type, str) or doc_type not in doc_types:
        return []

    violations = validate_id(doc_id, doc_type, doc_types)
    return [f"{path}: [id] {msg}" for msg in violations]


def _replace_frontmatter_id(text: str, new_id: str) -> str:
    """Replace the ``id:`` value inside the leading frontmatter block.

    Only modifies the id value; all other content — including inline comments on the
    same line (e.g. ``id: 'old'  # frozen at creation``) — is preserved.
    Returns *text* unchanged if there is no frontmatter block or no ``id:`` line.

    *text* must use LF-only line endings (callers normalise before calling).
    """
    match = re.match(r"^(---[ \t]*\n)(.*?)(\n---[ \t]*(?:\n|$))", text, re.DOTALL)
    if not match:
        return text
    prefix, fm_body, suffix = match.group(1), match.group(2), match.group(3)
    rest = text[match.end() :]

    # Three capture groups:
    #   1. key prefix  (id:[ \t]*)                     — not used in replacement
    #   2. value       single-/double-quoted or lazy unquoted
    #   3. trailing    optional whitespace + inline comment
    # The lazy unquoted form [^\n]*? yields the shortest match, leaving any "  # comment"
    # suffix to group 3 rather than including it in the value.
    def _repl(m: re.Match[str]) -> str:
        trailing = m.group(3) or ""
        # For an unquoted value like `id: old#id`, YAML reads the whole scalar but
        # the lazy split assigns `#id` to the comment group with no separating
        # space. Emitting it adjacent to the quote (`id: 'new'#id`) is junk that
        # spec-strict parsers (e.g. Prettier's yaml) reject — insert the space.
        if trailing.startswith("#"):
            trailing = " " + trailing
        return f"id: '{new_id}'" + trailing

    new_fm_body = re.sub(
        r"^(id:[ \t]*)('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|[^\n]*?)"
        r"([ \t]*(?:#[^\n]*)?)$",
        _repl,
        fm_body,
        flags=re.MULTILINE,
        count=1,
    )
    if new_fm_body == fm_body:
        return text
    return prefix + new_fm_body + suffix + rest


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write atomically (mirrors format_frontmatter._atomic_write, bytes flavour).

    A plain write_bytes truncates before writing — an interruption mid-write
    leaves the document truncated. mkstemp creates the temp file 0600, so the
    source's permission bits are copied before the replace.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        with contextlib.suppress(OSError):
            tmp_path.chmod(path.stat().st_mode & 0o777)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink()
        raise


@dataclass(frozen=True)
class FixResult:
    """Outcome of one ``fix_file`` call.

    ``new_id`` is set when the file was rewritten. Otherwise ``skip_reason`` says
    why the fix could not be applied — printed by ``--fix`` so a user is never
    left with 'violation(s) remain' and no clue the auto-fix was attempted.
    ``is_adr`` marks the one skip class with its own remediation message.
    """

    new_id: str | None = None
    skip_reason: str | None = None
    is_adr: bool = False


def plan_fix_content(
    raw: bytes,
    valid_doc_types: frozenset[str] | None = None,
    existing_ids: set[str] | None = None,
    *,
    token_factory: Callable[[], str] | None = None,
) -> tuple[bytes, FixResult]:
    """Return an id-repaired byte snapshot without writing the repository.

    Derives the new id from the document's ``doc_type`` and ``title`` fields:
    ``{doc_type}-{6-char base36 token}-{slugify(title)}``.

    *existing_ids* are ids already present in the corpus; the random token is
    regenerated on collision so a minted id is unique among them. (Duplicate-id
    detection lives in opt-in validate-references — a collision minted here
    could otherwise pass CI forever in a repo that never opted in.)

    The token factory is an explicit input so a provider can return deterministic
    output from immutable snapshots. The returned bytes equal *raw* whenever the
    result carries no ``new_id``.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw, FixResult(skip_reason="file is not valid UTF-8")
    # check_file reads with utf-8-sig (BOM stripped); a plain utf-8 decode keeps
    # U+FEFF, the \A--- anchor never matches, and a BOM'd file is flagged by
    # validation but silently unfixable. Strip it here and re-prepend on write so
    # the file stays byte-faithful apart from the id line.
    had_bom = text.startswith("﻿")
    if had_bom:
        text = text[1:]
    # Normalise to LF-only for YAML parsing and _replace_frontmatter_id (which requires LF).
    # Keep the original decoded string so we can reconstruct the output line-by-line,
    # preserving each line's individual ending — including files with mixed \r\n / \n.
    text_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        meta: dict[str, Any] | None = parse_frontmatter(text_lf)
    except FrontmatterParseError as exc:
        return raw, FixResult(skip_reason=f"invalid YAML frontmatter: {exc}")
    if meta is None:
        return raw, FixResult(skip_reason="no frontmatter block found")
    doc_types = valid_doc_types if valid_doc_types is not None else _load_doc_types(_SCHEMA_PATH)
    doc_id = meta.get("id")
    doc_type = meta.get("doc_type")
    title = meta.get("title")
    if not isinstance(doc_id, str) or not doc_id:
        return raw, FixResult(skip_reason="id field is missing or not a string")
    if not isinstance(doc_type, str) or doc_type not in doc_types:
        return raw, FixResult(skip_reason="doc_type field is missing or not a valid doc_type")
    # ADR ids include a repo-name segment that cannot be derived from document fields.
    if doc_type == "adr":
        return raw, FixResult(
            is_adr=True,
            skip_reason="ADR ids require a repo-name segment — fix manually",
        )
    # Already valid — nothing to fix.
    if not validate_id(doc_id, doc_type, doc_types):
        return raw, FixResult(skip_reason="id is already valid")
    if not isinstance(title, str) or not title.strip():
        return raw, FixResult(skip_reason="title is missing or empty — cannot derive a slug")
    slug = slugify(title)
    if not slug:
        return raw, FixResult(
            skip_reason="title produces an empty slug (no ASCII-translatable "
            "characters) — set an ASCII-translatable title or write the id manually"
        )
    next_token = token_factory or random_token
    new_id = f"{doc_type}-{next_token()}-{slug}"
    if existing_ids is not None:
        # 36^6 tokens make a real collision astronomically rare; the bound only
        # guards against a pathological existing_ids set.
        for _ in range(100):
            if new_id not in existing_ids:
                break
            new_id = f"{doc_type}-{next_token()}-{slug}"
        else:
            return raw, FixResult(skip_reason="could not generate an unused id (token collisions)")
    new_text_lf = _replace_frontmatter_id(text_lf, new_id)
    if new_text_lf == text_lf:
        return raw, FixResult(skip_reason="no rewritable id: line found in the frontmatter block")
    # Post-rewrite sanity check: _replace_frontmatter_id only understands
    # single-line id: values. A block-scalar id (id: >- with an indented
    # continuation) would leave the continuation orphaned — invalid YAML written
    # to disk under a 'fixed:' banner. Refuse to write anything the parser cannot
    # round-trip to the new id; the file degrades to a reported violation instead.
    unsafe_layout = FixResult(
        skip_reason="id value layout cannot be rewritten automatically "
        "(multi-line or unusual quoting) — edit the id manually"
    )
    try:
        new_meta = parse_frontmatter(new_text_lf)
    except FrontmatterParseError:
        return raw, unsafe_layout
    if not isinstance(new_meta, dict) or new_meta.get("id") != new_id:
        return raw, unsafe_layout
    # Reconstruct output preserving per-line endings.  Only the id: line differs between
    # text_lf and new_text_lf; all other lines — whether \r\n, \n, or \r — are kept
    # byte-exact.  This avoids converting bare-LF lines to CRLF in mixed-ending files.
    orig_lines = text.splitlines(keepends=True)
    new_lines_lf = new_text_lf.splitlines(keepends=True)
    bom_prefix = "﻿" if had_bom else ""
    if len(orig_lines) != len(new_lines_lf):
        # A line-count change means the rewrite did something beyond the
        # single-line id swap. Falling back to writing the LF-normalised text
        # would mass-rewrite a CRLF file's endings behind the user's back —
        # refusing keeps the preserve-endings contract (the violation stays
        # reported).
        return raw, FixResult(
            skip_reason=("rewrite would alter the file beyond the id line — edit the id manually")
        )
    output: list[str] = []
    for orig_line, new_line_lf in zip(orig_lines, new_lines_lf, strict=True):
        orig_stripped = orig_line.rstrip("\r\n")
        new_stripped = new_line_lf.rstrip("\r\n")
        if orig_stripped == new_stripped:
            output.append(orig_line)  # unchanged — keep original bytes exactly
        else:
            # Content changed: apply new content with the original line ending.
            orig_ending = orig_line[len(orig_stripped) :]
            output.append(new_stripped + orig_ending)
    return (bom_prefix + "".join(output)).encode("utf-8"), FixResult(new_id=new_id)


def fix_file(
    path: Path,
    valid_doc_types: frozenset[str] | None = None,
    existing_ids: set[str] | None = None,
) -> FixResult:
    """Plan and atomically publish one safe id repair for *path*."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return FixResult(skip_reason=f"cannot read file: {exc}")
    updated, result = plan_fix_content(raw, valid_doc_types, existing_ids)
    if result.new_id is None:
        return result
    try:
        _atomic_write_bytes(path, updated)
    except OSError as exc:
        return FixResult(skip_reason=f"cannot write file: {exc}")
    return result


def main(
    argv: list[str] | None = None,
    *,
    _command_locked: bool = False,
    _selected_package: SelectedCommandPackage | None = None,
) -> int:
    """CLI entry point; returns an exit code."""
    reconfigure_output_streams()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not _command_locked and not any(
        option in arguments for option in {"--help", "-h", "--version"}
    ):
        try:
            with selected_command(
                Path.cwd(),
                "markdown-frontmatter",
                mode=LockMode.WRITE if "--fix" in arguments else LockMode.READ,
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
        if "--fix" in arguments:
            from project_standards.frontmatter_commands import run_locked_standalone_fix

            return run_locked_standalone_fix(
                arguments,
                _selected_package,
                surface="validate-id",
            )
        from project_standards.frontmatter_commands import run_locked_standalone_validate

        return run_locked_standalone_validate(
            arguments,
            _selected_package,
            surface="validate-id",
        )
    parser = argparse.ArgumentParser(
        prog="validate-id",
        description=(
            "Validate that frontmatter id fields follow [doc_type]-[base36-6]-[readable-slug]."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version()}")
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        type=Path,
        help="Markdown files to validate. Omit to use the project config include list.",
    )
    # Default None so an operator-typed --config that does not exist exits 2
    # instead of silently validating with defaults (see validate_frontmatter).
    parser.add_argument(
        "--config",
        metavar="PATH",
        type=Path,
        default=None,
        help="Explicit legacy/debug config; unified config resolves from .standards/.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file output; exit code only.",
    )
    parser.add_argument(
        "--glob",
        metavar="PATTERN",
        help="Validate files matching PATTERN (relative to cwd) instead of the "
        "config include list; combines with explicit FILE arguments "
        "(same semantics as validate-frontmatter).",
    )
    parser.add_argument(
        "--schema",
        metavar="PATH",
        type=Path,
        default=None,
        help=(
            "Custom JSON Schema override (see validate-frontmatter). "
            "When provided, id-format validation is skipped entirely — "
            "custom schemas may define different id conventions."
        ),
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Fix non-compliant ids in place, deriving the new id from doc_type and title: "
            "{doc_type}-{base36-token}-{slugify(title)}. "
            "ADR ids (which require a repo-name segment) are skipped with a warning."
        ),
    )
    # Accepted for compatibility when project-standards validate forwards its full argv.
    # Has no effect here: id validation already silently skips files without frontmatter.
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)

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

    # Skip id-format validation when a custom (non-bundled) schema is in use — either
    # via the --schema CLI flag or via a config-level path. Custom schemas are
    # consumer-owned and may define different id conventions.
    if args.schema is not None or schema_value_is_path(config.schema):
        if not args.quiet:
            print("note: custom schema in use; skipping id-format validation")
        return 0

    # Resolve the doc_type enum from the EFFECTIVE schema (a pinned
    # markdown.frontmatter.version selects its own bundled contract). The registry
    # is only needed to translate a version pin — mirrors validate-frontmatter's
    # lazy-load so a broken registry cannot fail unversioned runs.
    try:
        registry = load_registry() if config.frontmatter_version is not None else None
        schema_path = resolve_effective_schema(None, config, registry)
        valid_doc_types = _load_doc_types(schema_path)
    except (ConfigError, RegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.fix:
        from project_standards.control_plane.executor import apply_authoring_plan
        from project_standards.frontmatter_authoring import plan_frontmatter_id_fix
        from project_standards.package_contract.paths import PackageVersion

        try:
            planned = plan_frontmatter_id_fix(
                Path.cwd(),
                tuple(paths),
                version=PackageVersion(config.selected_package_version),
                valid_doc_types=valid_doc_types,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if planned.refused_paths:
            for path, reason in planned.warnings:
                if path in planned.refused_paths:
                    print(f"cannot auto-fix: {path}: {reason}", file=sys.stderr)
            return 2
        applied = apply_authoring_plan(Path.cwd(), planned.plan)
        if not applied.success:
            print(f"error: id repair apply failed: {applied.error_code}", file=sys.stderr)
            return 2

        fixed = [(Path(path), document_id) for path, document_id in planned.fixed_ids]
        adr_skipped = [
            Path(path) for path, reason in planned.warnings if reason.startswith("ADR ids require")
        ]
        skip_notes = [
            (Path(path), reason)
            for path, reason in planned.warnings
            if not reason.startswith("ADR ids require")
        ]
        remaining_errors: list[str] = []
        remaining_files: set[Path] = set()
        adr_names = {path.as_posix() for path in adr_skipped}
        root = Path.cwd()
        for path in paths:
            relative = path.relative_to(root) if path.is_absolute() else path
            if relative.as_posix() in adr_names:
                continue
            violations = check_file(path, valid_doc_types)
            if violations:
                remaining_files.add(path)
                remaining_errors.extend(violations)

        # Stream contract (matches validate-frontmatter and the README's exit-code
        # documentation): violations and ✗ failure summaries go to stderr; success
        # output stays on stdout.
        if not args.quiet:
            for path, new_id in fixed:
                print(f"fixed: {path}: id → '{new_id}'")
            for path in adr_skipped:
                print(
                    f"skipped (ADR): {path}: ADR ids require a repo-name segment "
                    f"(e.g. adr-0001-myrepo-short-title) — fix manually",
                    file=sys.stderr,
                )
            for path, reason in skip_notes:
                print(f"cannot auto-fix: {path}: {reason}", file=sys.stderr)
            for error in remaining_errors:
                print(error, file=sys.stderr)
            if remaining_errors:
                print(
                    f"\n✗  {len(remaining_errors)} violation(s) remain "
                    f"across {len(remaining_files)} file(s)",
                    file=sys.stderr,
                )
            elif fixed:
                print(f"\n✓  {len(fixed)} id(s) fixed")
            elif not adr_skipped:
                print(f"✓  {len(paths)} file(s) already valid")
            # The exit code is 1 whenever ADRs were skipped; without this line a
            # run that fixed everything else ends with a green ✓ and a red exit
            # code — an explicit ✗ names the reason.
            if adr_skipped:
                print(
                    f"\n✗  {len(adr_skipped)} ADR id(s) require manual fix",
                    file=sys.stderr,
                )

        return 1 if (remaining_errors or adr_skipped) else 0

    all_errors: list[str] = []
    failing_files: set[Path] = set()
    for path in paths:
        errors = check_file(path, valid_doc_types)
        if errors:
            # Count files structurally — deriving them by splitting the formatted
            # strings on ':' miscounts any path containing a colon (every Windows
            # drive path).
            failing_files.add(path)
            all_errors.extend(errors)

    # Stream contract (matches validate-frontmatter and the README's exit-code
    # documentation): violations and the ✗ summary go to stderr.
    if not args.quiet:
        for error in all_errors:
            print(error, file=sys.stderr)

    if all_errors:
        if not args.quiet:
            print(
                f"\n✗  {len(all_errors)} violation(s) across {len(failing_files)} file(s)",
                file=sys.stderr,
            )
        return 1

    if not args.quiet:
        print(f"✓  {len(paths)} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
