"""Opt-in cross-file frontmatter checks the JSON Schema cannot express: id
uniqueness, referential integrity, supersede reciprocity, date ordering, ADR
sequence. Repo-wide pass; warnings never fail the build, errors do."""

from __future__ import annotations

import argparse
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
    schema_value_is_path,
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
    by_id: dict[str, list[Path]] = field(default_factory=dict)
    ids: set[str] = field(default_factory=set)


def build_index(paths: list[Path]) -> Index:
    index = Index()
    for path in paths:
        try:
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, FrontmatterParseError):
            continue
        if not isinstance(meta, dict):
            continue
        doc = Doc(path=path, meta=meta)
        index.docs.append(doc)
        doc_id = meta.get("id")
        if isinstance(doc_id, str) and doc_id:
            index.by_id.setdefault(doc_id, []).append(path)
            index.ids.add(doc_id)
    return index


def check_id_uniqueness(index: Index) -> list[str]:
    errors: list[str] = []
    for doc_id, paths in sorted(index.by_id.items()):
        if len(paths) > 1:
            joined = ", ".join(str(p) for p in sorted(paths))
            errors.append(f"[error] duplicate id '{doc_id}' in: {joined}")
    return errors


def check_dates(index: Index) -> list[str]:
    errors: list[str] = []
    for doc in index.docs:
        created = doc.meta.get("created")
        updated = doc.meta.get("updated")
        reviewed = doc.meta.get("reviewed")
        if isinstance(created, str) and isinstance(updated, str) and created > updated:
            errors.append(f"[error] {doc.path}: created '{created}' is after updated '{updated}'")
        if isinstance(reviewed, str) and isinstance(created, str) and reviewed < created:
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
        if isinstance(val, str):
            values.append(val)
        elif isinstance(val, list):
            val_list = cast("list[Any]", val)
            values.extend(v for v in val_list if isinstance(v, str) and v)
    return values


def _resolves(ref: str, index: Index, repo_root: Path) -> bool:
    if ref in index.ids:  # exact id match
        return True
    if "#" in ref:  # section anchors are not document references (standard)
        return False
    if ref.startswith(("/", "../")) or "/../" in ref:
        return False
    return (repo_root / ref).is_file()


def check_references(index: Index, repo_root: Path) -> list[str]:
    warnings: list[str] = []
    for doc in index.docs:
        for ref in _ref_values(doc.meta):
            if not _resolves(ref, index, repo_root):
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
    supersedes_map = {
        d.meta.get("id"): set(_as_list(d.meta.get("supersedes")))
        for d in index.docs
        if isinstance(d.meta.get("id"), str)
    }
    superseded_by_map = {
        d.meta.get("id"): set(_as_list(d.meta.get("superseded_by")))
        for d in index.docs
        if isinstance(d.meta.get("id"), str)
    }
    for doc in index.docs:
        a_id = doc.meta.get("id")
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
    by_num: dict[str, list[str]] = {}
    for doc in index.docs:
        if doc.meta.get("doc_type") != "adr":
            continue
        doc_id = doc.meta.get("id")
        if not isinstance(doc_id, str):
            continue
        m = _ADR_NUM_RE.match(doc_id)
        if m:
            by_num.setdefault(m.group(1), []).append(doc_id)
    return [
        f"[error] duplicate ADR number {num}: {', '.join(sorted(ids))}"
        for num, ids in sorted(by_num.items())
        if len(ids) > 1
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-references", description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, metavar="FILE")
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--glob", metavar="PATTERN")
    parser.add_argument("--no-require-frontmatter", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not config.references_enabled:
        return 0  # opt-in: disabled -> no checks
    if args.schema is not None or schema_value_is_path(config.schema):
        if not args.quiet:
            print("note: custom schema in use; skipping reference validation")
        return 0

    paths = collect_paths(list(args.files), args.glob, config.include, config.exclude)
    index = build_index(paths)
    errors: list[str] = []
    warnings: list[str] = []
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
