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
    validate-id --config .project-standards.yml
    validate-id --quiet --config .project-standards.yml
    validate-id --glob 'docs/**/*.md'
    validate-id --fix --config .project-standards.yml

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
import json
import re
import sys
from pathlib import Path
from typing import Any

from project_standards.id_format import random_token, slugify
from project_standards.validate_frontmatter import (
    ConfigError,
    FrontmatterParseError,
    collect_paths,
    load_config,
    parse_frontmatter,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")

# Load the doc_type enum directly from the bundled schema so this list never drifts.
# No valid doc_type contains a hyphen, which makes split('-', 2) safe: the first segment
# is always the doc_type prefix with no ambiguity.
_SCHEMA_PATH = Path(__file__).parent / "schemas" / "markdown-frontmatter.schema.json"
_VALID_DOC_TYPES: frozenset[str] = frozenset(
    json.loads(_SCHEMA_PATH.read_text())["properties"]["doc_type"]["enum"]
)

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
_ADR_ID_RE = re.compile(r"^adr-[0-9]{4,}-[a-z0-9]+(-[a-z0-9]+)+$")


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


def validate_id(doc_id: str, doc_type: str) -> list[str]:
    """Return violation messages for *doc_id*; empty list means the id is valid.

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
    if id_type not in _VALID_DOC_TYPES:
        errors.append(
            f"prefix '{id_type}' is not a valid doc_type "
            f"(valid: {', '.join(sorted(_VALID_DOC_TYPES))})"
        )
    elif id_type != doc_type:
        # The prefix must exactly match the document's own doc_type — catching cases
        # where a document's type was changed after the id was authored.
        errors.append(f"prefix '{id_type}' does not match the document's doc_type '{doc_type}'")

    # --- Segment 2: base-36 token ---
    if not _BASE36_RE.match(id_base36):
        errors.append(
            f"base-36 segment '{id_base36}' must be exactly 6 characters "
            f"from [0-9a-z] (got {len(id_base36)} chars)"
        )

    # --- Segment 3: readable slug ---
    if not id_readable_slug:
        errors.append("readable-slug segment (after the base-36 token) is empty")
    elif not _KEBAB_RE.match(id_readable_slug):
        errors.append(
            f"readable-slug '{id_readable_slug}' must be lowercase kebab-case ([a-z0-9][a-z0-9-]*)"
        )

    return errors


def check_file(path: Path) -> list[str]:
    """Return formatted violation lines for *path*; empty list means the file is clean.

    Files without frontmatter, or whose ``id`` / ``doc_type`` / ``title`` fields are
    absent or have the wrong type, are silently skipped — those gaps are caught by the
    frontmatter schema validator rather than duplicated here.
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

    doc_id = meta.get("id")
    doc_type = meta.get("doc_type")

    # Skip files where the required fields are missing or have wrong types; those
    # structural violations belong to the schema validator's output, not this one's.
    if not isinstance(doc_id, str) or not doc_id:
        return []
    if not isinstance(doc_type, str) or doc_type not in _VALID_DOC_TYPES:
        return []

    violations = validate_id(doc_id, doc_type)
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
        return f"id: '{new_id}'" + (m.group(3) or "")

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


def fix_file(path: Path) -> str | None:
    """Rewrite the ``id`` field in *path* to a valid standard-format id.

    Derives the new id from the document's ``doc_type`` and ``title`` fields:
    ``{doc_type}-{6-char base36 token}-{slugify(title)}``.

    Returns the new id string if the file was modified. Returns ``None`` when:
    - the id is already valid (nothing to do),
    - the ``doc_type`` is ``adr`` (repo-name cannot be auto-derived),
    - required fields (``doc_type``, ``title``) are absent or have wrong types,
    - or ``title`` slugifies to an empty string.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Normalise to LF-only for YAML parsing and _replace_frontmatter_id (which requires LF).
    # Keep the original decoded string so we can reconstruct the output line-by-line,
    # preserving each line's individual ending — including files with mixed \r\n / \n.
    text_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        meta: dict[str, Any] | None = parse_frontmatter(text_lf)
    except FrontmatterParseError:
        return None
    if meta is None:
        return None
    doc_id = meta.get("id")
    doc_type = meta.get("doc_type")
    title = meta.get("title")
    if not isinstance(doc_id, str) or not doc_id:
        return None
    if not isinstance(doc_type, str) or doc_type not in _VALID_DOC_TYPES:
        return None
    # ADR ids include a repo-name segment that cannot be derived from document fields.
    if doc_type == "adr":
        return None
    # Already valid — nothing to fix.
    if not validate_id(doc_id, doc_type):
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    token = random_token()
    slug = slugify(title)
    if not slug:
        return None
    new_id = f"{doc_type}-{token}-{slug}"
    new_text_lf = _replace_frontmatter_id(text_lf, new_id)
    if new_text_lf == text_lf:
        return None
    # Reconstruct output preserving per-line endings.  Only the id: line differs between
    # text_lf and new_text_lf; all other lines — whether \r\n, \n, or \r — are kept
    # byte-exact.  This avoids converting bare-LF lines to CRLF in mixed-ending files.
    orig_lines = text.splitlines(keepends=True)
    new_lines_lf = new_text_lf.splitlines(keepends=True)
    if len(orig_lines) != len(new_lines_lf):
        # Unexpected line-count mismatch; fall back to writing the LF-normalised content.
        path.write_bytes(new_text_lf.encode("utf-8"))
        return new_id
    output: list[str] = []
    for orig_line, new_line_lf in zip(orig_lines, new_lines_lf, strict=False):
        orig_stripped = orig_line.rstrip("\r\n")
        new_stripped = new_line_lf.rstrip("\r\n")
        if orig_stripped == new_stripped:
            output.append(orig_line)  # unchanged — keep original bytes exactly
        else:
            # Content changed: apply new content with the original line ending.
            orig_ending = orig_line[len(orig_stripped) :]
            output.append(new_stripped + orig_ending)
    path.write_bytes("".join(output).encode("utf-8"))
    return new_id


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns an exit code."""
    parser = argparse.ArgumentParser(
        prog="validate-id",
        description=(
            "Validate that frontmatter id fields follow [doc_type]-[base36-6]-[readable-slug]."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        type=Path,
        help="Markdown files to validate. Omit to use the project config include list.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        type=Path,
        default=_DEFAULT_CONFIG,
        help=f"Project config file (default: {_DEFAULT_CONFIG}).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file output; exit code only.",
    )
    parser.add_argument(
        "--glob",
        metavar="PATTERN",
        help="Additional glob pattern relative to cwd (same semantics as validate-frontmatter).",
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

    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Skip id-format validation when a custom (non-bundled) schema is in use — either
    # via the --schema CLI flag or via a config-level path.  A bare token like
    # "markdown-frontmatter" is a bundled schema name; anything containing a path
    # separator or ending in ".json" is consumer-owned and may define different id
    # conventions.  Mirrors the schema_value_is_path check in validate_frontmatter.
    config_schema = config.schema
    config_has_custom_schema = config_schema is not None and (
        "/" in config_schema or "\\" in config_schema or config_schema.endswith(".json")
    )
    if args.schema is not None or config_has_custom_schema:
        if not args.quiet:
            print("note: custom schema in use; skipping id-format validation")
        return 0

    try:
        paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.fix:
        fixed: list[tuple[Path, str]] = []
        adr_skipped: list[Path] = []
        remaining_errors: list[str] = []

        for path in paths:
            violations = check_file(path)
            if not violations:
                continue
            new_id = fix_file(path)
            if new_id is not None:
                fixed.append((path, new_id))
            else:
                # fix_file returns None for ADR files; distinguish for a clearer message.
                try:
                    meta = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
                    if isinstance(meta, dict) and meta.get("doc_type") == "adr":
                        adr_skipped.append(path)
                        continue
                except OSError, FrontmatterParseError:
                    pass
                remaining_errors.extend(violations)

        if not args.quiet:
            for path, new_id in fixed:
                print(f"fixed: {path}: id → '{new_id}'")
            for path in adr_skipped:
                print(
                    f"skipped (ADR): {path}: ADR ids require a repo-name segment "
                    f"(e.g. adr-0001-myrepo-short-title) — fix manually",
                    file=sys.stderr,
                )
            for error in remaining_errors:
                print(error)
            if remaining_errors:
                file_count = len({e.split(":")[0] for e in remaining_errors})
                print(
                    f"\n✗  {len(remaining_errors)} violation(s) remain across {file_count} file(s)"
                )
            elif fixed:
                print(f"\n✓  {len(fixed)} id(s) fixed")
            elif not adr_skipped:
                print(f"✓  {len(paths)} file(s) already valid")

        return 1 if (remaining_errors or adr_skipped) else 0

    all_errors: list[str] = []
    for path in paths:
        all_errors.extend(check_file(path))

    if not args.quiet:
        for error in all_errors:
            print(error)

    if all_errors:
        if not args.quiet:
            file_count = len({e.split(":")[0] for e in all_errors})
            print(f"\n✗  {len(all_errors)} violation(s) across {file_count} file(s)")
        return 1

    if not args.quiet:
        print(f"✓  {len(paths)} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
