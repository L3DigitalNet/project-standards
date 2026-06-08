"""Validate that frontmatter ``id`` fields follow the correct format for their doc_type.

Two formats are in use; which applies depends on ``doc_type``:

**Standard format** — all doc_types except ``adr``:
``{doc_type}-{6-char base36 token}-{title-slug}``

- ``{doc_type}``       matches the document's own ``doc_type`` field value.
- ``{base36 token}``   is exactly 6 characters from [0-9a-z] (the base-36 alphabet).
- ``{title-slug}``     is the document's ``title`` lowercased, with non-alphanumeric runs
                       collapsed to single hyphens, and leading/trailing hyphens stripped.

Example: ``note-a3f9zk-tailscale-acl-tag-ordering-gotcha``.

**ADR format** — ``doc_type: adr``:
``adr-{NNNN}-{repo-name}-{short-title}``

- ``{NNNN}``           is a zero-padded, repo-scoped sequence number (at least 4 digits).
- ``{repo-name}``      is the repository name in kebab-case; it makes the id globally
                       unique so ADRs can be cited by id from other repositories' ``related:``
                       fields without ambiguity.
- ``{short-title}``    is a kebab-case short form of the decision title.

Example: ``adr-0001-homelab-use-postgresql-for-persistent-storage``.

Usage:
    validate-id FILE [FILE ...]
    validate-id --config .project-standards.yml
    validate-id --quiet --config .project-standards.yml

Exit codes: 0 = all ids valid; 1 = violations found; 2 = config/invocation error.

Note: files missing frontmatter or missing the ``id`` / ``doc_type`` / ``title`` fields are
silently skipped — those structural gaps are the frontmatter schema validator's job.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from project_standards.validate_frontmatter import (
    ConfigError,
    FrontmatterParseError,
    collect_paths,
    load_config,
    parse_frontmatter,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")

# Valid doc_type values. Must stay in sync with the ``doc_type`` enum in
# src/project_standards/schemas/markdown-frontmatter.schema.json.
# No valid doc_type contains a hyphen, which is what makes split('-', 2)
# safe for splitting an id into its three segments.
_VALID_DOC_TYPES: frozenset[str] = frozenset(
    {
        "index",
        "note",
        "concept",
        "reference",
        "runbook",
        "spec",
        "plan",
        "adr",
        "decision",
        "research",
        "template",
        "log",
        "prompt",
        "schema",
    }
)

# Exactly 6 characters from the base-36 alphabet (digits 0-9 + lowercase letters a-z).
_BASE36_RE = re.compile(r"^[0-9a-z]{6}$")

# Non-empty lowercase kebab-case: starts with alphanumeric, rest is alphanumeric or hyphens.
_KEBAB_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# ADR id: adr-{NNNN}-{repo-name}-{short-title}
# NNNN is at least 4 zero-padded digits; the repo-name + short-title together form a
# non-empty kebab-case suffix. No minimum length is imposed on the suffix — the repo-name
# and short-title boundary is semantic, not structurally detectable by regex.
_ADR_ID_RE = re.compile(r"^adr-[0-9]{4,}-[a-z0-9][a-z0-9-]*$")


def slugify(text: str) -> str:
    """Convert *text* to a lowercase kebab-case slug.

    Normalises Unicode to ASCII, lowercases, then collapses any run of
    non-alphanumeric characters to a single hyphen. This is the canonical transform
    for deriving the title-slug portion of a document ``id``.

    Examples::

        slugify("Tailscale ACL tag ordering gotcha")
        # → "tailscale-acl-tag-ordering-gotcha"

        slugify("Standards Adoption & Compliance Procedure")
        # → "standards-adoption-compliance-procedure"
    """
    # Strip accent marks (e.g. é → e) before lowercasing.
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # Collapse any run of non-alphanumeric characters (spaces, punctuation, symbols)
    # to a single hyphen, then strip leading/trailing hyphens.
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


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


def validate_id(doc_id: str, doc_type: str, title: str) -> list[str]:
    """Return violation messages for *doc_id*; empty list means the id is valid.

    Dispatches to ``_validate_adr_id`` for ``doc_type == 'adr'`` (sequential-number
    format) and validates the base-36 three-segment format for all other doc_types.

    Standard-format checks in order:
    1. Three segments present: ``{doc_type}-{base36}-{title-slug}``.
    2. Segment 1 is a valid doc_type and matches the document's ``doc_type`` field.
    3. Segment 2 is exactly 6 base-36 characters ([0-9a-z]{6}).
    4. Segment 3 is non-empty lowercase kebab-case.
    5. Segment 3 matches ``slugify(title)``.

    Each returned string is a plain message (no path prefix); callers annotate with path.
    """
    if doc_type == "adr":
        return _validate_adr_id(doc_id)

    # maxsplit=2 so the title-slug segment may itself contain hyphens.
    # e.g. "note-a3f9zk-tailscale-acl-gotcha" → ["note", "a3f9zk", "tailscale-acl-gotcha"]
    parts = doc_id.split("-", 2)

    if len(parts) < 3:
        expected = f"{doc_type}-<6-char base36>-{slugify(title)}"
        return [f"must be '{expected}'; got '{doc_id}' (too few hyphen-separated segments)"]

    id_type, id_base36, id_title_slug = parts
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

    # --- Segment 3: title slug ---
    if not id_title_slug:
        errors.append("title-slug segment (after the base-36 token) is empty")
    elif not _KEBAB_RE.match(id_title_slug):
        errors.append(
            f"title-slug '{id_title_slug}' must be lowercase kebab-case ([a-z0-9][a-z0-9-]*)"
        )
    else:
        expected_slug = slugify(title)
        if id_title_slug != expected_slug:
            # A mismatch usually means the title was edited after the id was set, or the
            # id was generated from a different title string. The fix is to regenerate the
            # slug portion; the base-36 token stays the same.
            errors.append(
                f"title-slug '{id_title_slug}' does not match expected '{expected_slug}' "
                f"(derived from title: '{title}')"
            )

    return errors


def check_file(path: Path) -> list[str]:
    """Return formatted violation lines for *path*; empty list means the file is clean.

    Files without frontmatter, or whose ``id`` / ``doc_type`` / ``title`` fields are
    absent or have the wrong type, are silently skipped — those gaps are caught by the
    frontmatter schema validator rather than duplicated here.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read: {exc}"]

    try:
        meta: dict[str, Any] | None = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        return [f"{path}: invalid YAML frontmatter: {exc}"]

    if meta is None:
        return []

    doc_id = meta.get("id")
    doc_type = meta.get("doc_type")
    title = meta.get("title")

    # Skip files where the required fields are missing or have wrong types; those
    # structural violations belong to the schema validator's output, not this one's.
    if not isinstance(doc_id, str) or not doc_id:
        return []
    if not isinstance(doc_type, str) or doc_type not in _VALID_DOC_TYPES:
        return []
    if not isinstance(title, str) or not title:
        return []

    violations = validate_id(doc_id, doc_type, title)
    return [f"{path}: [id] {msg}" for msg in violations]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns an exit code."""
    parser = argparse.ArgumentParser(
        prog="validate-id",
        description=(
            "Validate that frontmatter id fields follow [doc_type]-[base36-6]-[title-slug]."
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

    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Pass None for glob_pattern — this tool has no --glob flag; explicit FILE args
    # or config include patterns are the only two path sources.
    paths = collect_paths(list(args.files), None, config.include, config.exclude)

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
