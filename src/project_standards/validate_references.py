"""Opt-in cross-file frontmatter checks the JSON Schema cannot express: id
uniqueness, referential integrity, supersede reciprocity, date ordering, ADR
sequence. Repo-wide pass; warnings never fail the build, errors do."""

from __future__ import annotations

import argparse
import datetime
import re as _re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from project_standards.validate_frontmatter import (
    ConfigError,
    FrontmatterParseError,
    collect_paths,
    load_config,
    parse_frontmatter,
    reconfigure_output_streams,
    schema_value_is_path,
)
from project_standards.validate_id import (
    _ADR_ID_RE,  # pyright: ignore[reportPrivateUsage]  # one grammar, one owner
)

_DEFAULT_CONFIG = Path(".project-standards.yml")
_REF_FIELDS = ("related", "depends_on", "supersedes", "superseded_by")  # NOT applies_to

_ADR_NUM_RE = _re.compile(r"^adr-([0-9]{4,})-")


@dataclass
class Doc:
    path: Path
    meta: dict[str, Any]


@dataclass
class Index:
    docs: list[Doc] = field(default_factory=list)
    # id -> every path claiming it; membership doubles as the known-id set, so no
    # separate ids field exists to drift out of sync with this one.
    by_id: dict[str, list[Path]] = field(default_factory=dict)
    # Files dropped from the index (unreadable / unparseable frontmatter), as
    # ready-to-print warning lines. A dropped doc's duplicate-id violations
    # vanish and references TO it misreport as unresolved — standalone runs (no
    # validate-frontmatter alongside) would otherwise pass green on a fully
    # broken corpus with zero indication why.
    skipped: list[str] = field(default_factory=list)


def build_index(paths: list[Path]) -> Index:
    index = Index()
    for path in paths:
        try:
            meta = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError) as exc:
            index.skipped.append(f"[warning] {path}: skipped (cannot read: {exc})")
            continue
        except FrontmatterParseError as exc:
            index.skipped.append(f"[warning] {path}: skipped (invalid frontmatter: {exc})")
            continue
        if not isinstance(meta, dict):
            # No (or non-mapping) frontmatter block: silently unmanaged here —
            # whether frontmatter is REQUIRED is the schema validator's finding,
            # and warning on every excluded-by-design file would be noise.
            continue
        doc = Doc(path=path, meta=meta)
        index.docs.append(doc)
        doc_id = meta.get("id")
        if isinstance(doc_id, str) and doc_id:
            index.by_id.setdefault(doc_id, []).append(path)
    return index


def check_id_uniqueness(index: Index) -> list[str]:
    errors: list[str] = []
    for doc_id, paths in sorted(index.by_id.items()):
        if len(paths) > 1:
            joined = ", ".join(str(p) for p in sorted(paths))
            errors.append(f"[error] duplicate id '{doc_id}' in: {joined}")
    return errors


def _as_date(value: Any) -> datetime.date | None:
    """Parse a frontmatter date value, or None if absent/unparseable.

    Unparseable values are skipped, not errored: shape enforcement is the schema
    validator's job, and this tool also runs standalone where schema validation
    may not have happened — comparing such values as raw strings would order
    non-padded dates wrongly ('2026-9-1' > '2026-10-01' lexicographically).
    """
    if not isinstance(value, str):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def check_dates(index: Index) -> list[str]:
    errors: list[str] = []
    for doc in index.docs:
        created = _as_date(doc.meta.get("created"))
        updated = _as_date(doc.meta.get("updated"))
        reviewed = _as_date(doc.meta.get("reviewed"))
        if created is not None and updated is not None and created > updated:
            errors.append(f"[error] {doc.path}: created '{created}' is after updated '{updated}'")
        if reviewed is not None and created is not None and reviewed < created:
            errors.append(
                f"[error] {doc.path}: reviewed '{reviewed}' is before created '{created}'"
            )
    return errors


def _ref_values(meta: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field_name in _REF_FIELDS:
        val = meta.get(field_name)
        if val is None:
            continue
        # Empty strings are schema-valid (no minLength on superseded_by) but carry
        # no reference; both the scalar and list forms ignore them — a bare
        # "unresolved reference ''" warning diagnoses nothing.
        if isinstance(val, str) and val:
            values.append(val)
        elif isinstance(val, list):
            val_list = cast("list[Any]", val)
            values.extend(v for v in val_list if isinstance(v, str) and v)
    return values


def _resolves(ref: str, index: Index, repo_root: Path) -> bool:
    if ref in index.by_id:  # exact id match
        return True
    if "#" in ref:  # section anchors are not document references (standard)
        return False
    # Containment, not textual guards: Windows drive refs (C:/x.md), backslash
    # traversal (..\\x), and symlinks pointing outside the repo all slip past
    # startswith()-style checks, but none can defeat resolve()+is_relative_to.
    # Costs a resolve() per ref, accepted at corpus scale; a symlinked path
    # INSIDE the repo that targets outside it now correctly fails to resolve.
    try:
        resolved = (repo_root / ref).resolve()
    except OSError:
        return False
    if not resolved.is_relative_to(repo_root.resolve()):
        return False
    return resolved.is_file()


def check_references(index: Index, repo_root: Path) -> list[str]:
    warnings: list[str] = []
    for doc in index.docs:
        for ref in _ref_values(doc.meta):
            if "#" in ref:
                # Ids cannot contain '#' (schema pattern), so this is a section
                # anchor. The file part may well exist — calling it "unresolved"
                # misdiagnoses; the actual rule is that the standard mandates
                # document-level links in reference fields.
                warnings.append(
                    f"[warning] {doc.path}: section anchors are not valid document "
                    f"references (use document-level links): '{ref}'"
                )
            elif _resolves(ref, index, repo_root):
                pass
            elif _ADR_ID_RE.match(ref):
                # The standard endorses citing ADR ids across repositories — the
                # repo-name segment exists for exactly that — so a well-formed ADR
                # id with no local match is assumed external, not broken. Warning
                # here would emit permanent, unsuppressible noise on every
                # documented cross-repo citation. Accepted trade-off: a dangling
                # LOCAL ADR id that still matches the format is also skipped.
                continue
            else:
                warnings.append(f"[warning] {doc.path}: unresolved reference '{ref}'")
    return warnings


def _as_list(val: Any) -> list[str]:
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        val_list = cast("list[Any]", val)
        return [v for v in val_list if isinstance(v, str)]
    return []


def check_reciprocity(index: Index) -> list[str]:
    """Both directions of the supersede invariant (CR-004): A.superseded_by=B requires
    B.supersedes=A, AND A.supersedes=B requires B.superseded_by=A. Only checked when
    the counterpart doc is local (cross-repo ids can't be inspected)."""
    warnings: list[str] = []
    # Sets are MERGED per id, not last-wins: duplicate ids are already an error
    # elsewhere in this run, but a dict comprehension would compute reciprocity
    # from an arbitrary one of the duplicates, making these warnings unreliable
    # noise in exactly the run that reports the duplicate.
    supersedes_map: dict[str, set[str]] = {}
    superseded_by_map: dict[str, set[str]] = {}
    for d in index.docs:
        d_id = d.meta.get("id")
        if not isinstance(d_id, str):
            continue
        supersedes_map.setdefault(d_id, set()).update(_as_list(d.meta.get("supersedes")))
        superseded_by_map.setdefault(d_id, set()).update(_as_list(d.meta.get("superseded_by")))
    for doc in index.docs:
        a_id = doc.meta.get("id")
        # A doc with supersede fields but no usable id of its own cannot satisfy
        # reciprocity; warning would interpolate None ("'None' is superseded_by
        # ...") — diagnosing nothing. The missing id itself is the schema
        # validator's finding, not this pass's.
        if not isinstance(a_id, str) or not a_id:
            continue
        for b_id in _as_list(doc.meta.get("superseded_by")):
            if b_id in supersedes_map and a_id not in supersedes_map[b_id]:
                warnings.append(
                    f"[warning] {doc.path}: '{a_id}' is superseded_by '{b_id}', "
                    f"but '{b_id}' does not list it in supersedes"
                )
        for b_id in _as_list(doc.meta.get("supersedes")):
            if b_id in superseded_by_map and a_id not in superseded_by_map[b_id]:
                warnings.append(
                    f"[warning] {doc.path}: '{a_id}' supersedes '{b_id}', "
                    f"but '{b_id}' does not list it in superseded_by"
                )
    return warnings


def check_adr_sequence(index: Index) -> list[str]:
    # Keyed by the numeric value, not the digit string: the id grammar allows 4+
    # zero-padded digits, so adr-0001-... and adr-00001-... are both ADR number 1
    # and must collide here even though their raw strings differ.
    by_num: dict[int, list[str]] = {}
    for doc in index.docs:
        if doc.meta.get("doc_type") != "adr":
            continue
        doc_id = doc.meta.get("id")
        if not isinstance(doc_id, str):
            continue
        m = _ADR_NUM_RE.match(doc_id)
        if m:
            by_num.setdefault(int(m.group(1)), []).append(doc_id)
    return [
        f"[error] duplicate ADR number {num}: {', '.join(sorted(ids))}"
        for num, ids in sorted(by_num.items())
        if len(ids) > 1
    ]


def main(argv: list[str] | None = None) -> int:
    reconfigure_output_streams()
    _base_desc = __doc__ or ""
    parser = argparse.ArgumentParser(
        prog="validate-references",
        description=(
            _base_desc
            + "\n\nNote: FILE and --glob do not scope the cross-file checks — the pass is always"
            " whole-repo (FILE/--glob are forwarded by `project-standards validate` but ignored"
            " here; the full configured set is always indexed)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
    # Default None so an operator-typed --config that does not exist exits 2; for
    # THIS validator a silently defaulted config is the worst case — references
    # stay disabled and the whole pass no-ops green.
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--glob", metavar="PATTERN")
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args(argv)

    if args.config is not None and not args.config.exists():
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        return 2
    try:
        config = load_config(args.config if args.config is not None else _DEFAULT_CONFIG)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not config.references_enabled:
        return 0  # opt-in: disabled -> no checks
    if args.schema is not None or schema_value_is_path(config.schema):
        if not args.quiet:
            print("note: custom schema in use; skipping reference validation")
        return 0

    # validate-references is a REPO-WIDE invariant pass (duplicate ids / ADR numbers,
    # cross-file references), so the index MUST cover the full configured set even when
    # the caller scopes to specific FILE / --glob (project-standards validate forwards
    # them) — otherwise a duplicate in an unselected doc is silently missed (codex P2).
    try:
        paths = collect_paths([], None, config.include, config.exclude)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    index = build_index(paths)
    errors: list[str] = []
    warnings: list[str] = []
    warnings += index.skipped
    errors += check_id_uniqueness(index)
    errors += check_dates(index)
    warnings += check_references(index, Path.cwd())
    warnings += check_reciprocity(index)
    errors += check_adr_sequence(index)

    for w in warnings:
        print(w, file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        print(f"\n✗  {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"✓  references valid ({len(index.docs)} docs, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
