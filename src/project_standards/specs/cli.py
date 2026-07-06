"""Nested `project-standards spec` command group."""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
import random
import re
import stat
import sys
import tempfile
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import NoReturn

from project_standards.specs.commands.extract import extract_slice
from project_standards.specs.commands.lint import lint_document
from project_standards.specs.commands.new import (
    FieldValueError,
    NewOptions,
    SpecIdExhausted,
    check_field,
    mint_spec_id,
    scaffold,
)
from project_standards.specs.commands.next_id import next_free_id
from project_standards.specs.commands.upgrade import check_upgradeable, upgrade_text
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.config import (
    ConfigError,
    collect_existing_spec_ids,
    collect_spec_paths,
    load_spec_config,
)
from project_standards.specs.document import SpecParseError, parse_document
from project_standards.specs.model import Finding
from project_standards.specs.registry import (
    SPEC_ID_PATTERN,
    TEMPLATES_DIR,
    TIER_FILES,
    load_registry,
)

_DEFAULT_CONFIG = Path(".project-standards.yml")
_USAGE = "usage: project-standards spec {validate|lint|extract|next|new|upgrade} ..."
_TIER_ORDER = {"light": 0, "standard": 1, "full": 2}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SpecParseError(f"{path}: not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read spec {path}: {exc}") from exc


def _findings_payload(results: list[tuple[Path, list[Finding]]]) -> list[dict[str, object]]:
    return [
        {
            "file": str(path),
            "ok": not findings,
            "findings": [dataclasses.asdict(f) for f in findings],
        }
        for path, findings in results
    ]


def _run_setwide(argv: list[str], *, lint: bool) -> int:
    ap = argparse.ArgumentParser(prog=f"project-standards spec {'lint' if lint else 'validate'}")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    reg = load_registry()
    cfg = load_spec_config(args.config)
    paths = collect_spec_paths(args.files, cfg)
    ref_pfx = frozenset(cfg.reference_prefixes)
    results: list[tuple[Path, list[Finding]]] = []
    for path in paths:
        try:
            doc = parse_document(str(path), _read(path))
            if lint:
                findings = lint_document(doc, reg)
            else:
                findings = validate_document(doc, reg, reference_prefixes=ref_pfx)
            results.append((path, findings))
        except SpecParseError as exc:
            results.append((path, [Finding(code="SV-PARSE", severity="error", message=str(exc))]))
    if args.json:
        print(json.dumps(_findings_payload(results), indent=2))
    else:
        for path, findings in results:
            state = "WARN" if lint and findings else "FAIL" if findings else "OK  "
            print(f"{state} {path}")
            for finding in findings:
                line = f" (L{finding.line})" if finding.line else ""
                print(f"   [{finding.code}] {finding.message}{line}")
    any_findings = any(findings for _, findings in results)
    if lint:
        return 1 if any_findings and args.strict else 0
    return 1 if any_findings else 0


def _run_extract(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec extract")
    ap.add_argument("file", type=Path)
    ap.add_argument("selector")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = parse_document(str(args.file), _read(args.file))
    result = extract_slice(doc, args.selector)
    if args.json:
        print(
            json.dumps(
                {
                    "file": str(args.file),
                    "selector": result.selector,
                    "kind": result.kind,
                    "found": result.found,
                    "markdown": result.markdown,
                }
            )
        )
    elif result.found:
        print(result.markdown)
    else:
        print(f"no match for {result.selector!r}", file=sys.stderr)
    return 0 if result.found else 1


def _run_next(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec next")
    ap.add_argument("file", type=Path)
    ap.add_argument("prefix")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = parse_document(str(args.file), _read(args.file))
    try:
        nid = next_free_id(doc, load_registry(), args.prefix)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    prefix = args.prefix.rstrip("-").upper()
    print(
        json.dumps({"file": str(args.file), "prefix": prefix, "next_id": nid}) if args.json else nid
    )
    return 0


def _run_validate(argv: list[str]) -> int:
    return _run_setwide(argv, lint=False)


def _run_lint(argv: list[str]) -> int:
    return _run_setwide(argv, lint=True)


class _ArgparseError(Exception):
    """Raised by _NewArgParser.error so a bad invocation reaches the JSON wrapper
    instead of argparse's default sys.exit(2) + stderr (which would bypass I7)."""


class _NewArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)


class NewError(Exception):
    """A `spec new` refusal/usage/validation failure. Carries the frozen JSON `code`."""

    def __init__(self, code: str, message: str, findings: list[dict[str, object]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.findings = findings or []


def _emit_new_failure(json_mode: bool, err: NewError) -> int:
    if json_mode:
        obj: dict[str, object] = {"ok": False, "error": err.message, "code": err.code}
        if err.findings:
            obj["findings"] = err.findings
        print(json.dumps(obj))
    else:
        print(f"error: {err.message}", file=sys.stderr)
    return 2


def _resolve_new_options(args: argparse.Namespace) -> tuple[NewOptions, str]:
    """Validate flags, resolve the spec_id (mint or --id); return (opts, template_text).
    Raises NewError for every exit-2 condition."""
    for flag, value, is_title in (
        ("title", args.title, True),
        ("owner", args.owner, False),
        ("implementer", args.implementer, False),
    ):
        if value is not None:
            try:
                check_field(flag, value, is_title=is_title)
            except FieldValueError as exc:
                raise NewError("bad_field_value", str(exc)) from exc

    try:
        cfg = load_spec_config(args.config)
        existing_ids = collect_existing_spec_ids(cfg)
    except ConfigError as exc:
        raise NewError("config_error", str(exc)) from exc

    if args.spec_id is not None:
        if not re.match(SPEC_ID_PATTERN, args.spec_id):
            raise NewError("bad_id", f"--id {args.spec_id!r} does not match {SPEC_ID_PATTERN}")
        if args.spec_id in existing_ids:
            raise NewError("id_collision", f"--id {args.spec_id} is already used in this repo")
        spec_id = args.spec_id
    else:
        try:
            spec_id = mint_spec_id(random.Random(), existing_ids)
        except SpecIdExhausted as exc:
            raise NewError("id_exhausted", str(exc)) from exc

    opts = NewOptions(
        profile=args.profile,
        spec_id=spec_id,
        title=args.title,
        owner=args.owner,
        implementer=args.implementer,
    )
    template_text = (TEMPLATES_DIR / TIER_FILES[args.profile]).read_text(encoding="utf-8")
    return opts, template_text


def _parent_chain_has_symlink(target: Path) -> bool:
    # Path.exists()/is_file() follow symlinks, so a symlinked PARENT (docs/link/spec.md)
    # could redirect the write outside the working tree — refuse it. The walk is BOUNDED to
    # the cwd like adopt/engine._has_symlinked_ancestor (which stops at dest_root) — but note
    # the parity is adaptive, not a straight port: the engine's caller (validate_dest) rejects
    # `..`/absolute and pre-normalizes containment BEFORE the walk, so its helper needs no
    # containment test. `new` has no such pre-validation of the raw args.path, so the walk
    # folds the boundary in itself via the is_relative_to check below.
    # symlinks in the invocation's own system/home ancestry ABOVE cwd (e.g. macOS
    # /var -> /private/var, a symlinked $HOME, a repo checked out under a symlinked path)
    # are the environment, not an attack surface, and must not spuriously refuse an absolute
    # PATH. Parents are inspected UNRESOLVED — Path.resolve() would follow the very symlinks
    # we mean to detect; is_symlink() is False for non-existent paths, so only real symlinked
    # ancestors within the tree trip this. An absolute PATH outside cwd gets no ancestry check
    # (the user pointed there deliberately; its layout is not ours to police).
    root = Path.cwd()
    abs_target = root / target  # relative -> under root; an absolute target overrides root
    for parent in abs_target.parents:
        if parent == root:
            break
        if not parent.is_relative_to(root):
            break  # walked above/outside cwd: no longer part of the working tree
        if parent.is_symlink():
            return True
    return False


def _target_type_conflict(target: Path) -> bool:
    if target.is_symlink():  # includes broken symlinks (never followed for writes)
        return True
    return os.path.lexists(target) and not target.is_file()  # dir / fifo / device / socket


def _safe_atomic_write(target: Path, text: str, *, force: bool) -> bool:
    """Write text atomically to target with mode preservation. Returns whether file was overwritten.

    Raises NewError for not_regular_file / symlinked_parent / exists / mkdir_failed / write_failed.
    """
    if _target_type_conflict(target):
        raise NewError("not_regular_file", f"refusing to write non-regular target: {target}")
    if _parent_chain_has_symlink(target):
        raise NewError(
            "symlinked_parent", f"refusing to write through a symlinked parent: {target}"
        )
    overwritten = target.is_file()
    if overwritten and not force:
        raise NewError("exists", f"refusing to overwrite existing file: {target} (use --force)")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise NewError(
            "mkdir_failed", f"cannot create parent directory for {target}: {exc}"
        ) from exc

    tmp: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".spec-write-", suffix=".tmp")
        tmp = Path(tmp_name)
        # Mode (mirrors adopt/engine._atomic_write): preserve on overwrite; umask-respecting
        # 0o666 for a new file, so the result is not left at mkstemp's owner-only 0600.
        if target.exists():
            with contextlib.suppress(OSError):
                tmp.chmod(target.stat().st_mode & 0o777)
        else:
            mask = os.umask(0)
            os.umask(mask)
            with contextlib.suppress(OSError):
                tmp.chmod(stat.S_IMODE(0o666 & ~mask))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, target)  # noqa: PTH105
    except OSError as exc:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise NewError("write_failed", f"cannot write {target}: {exc}") from exc
    except BaseException:
        # Full parity with adopt/engine._atomic_write: also clean up on interruption /
        # unexpected non-OSError (KeyboardInterrupt, generator-throw), then re-raise as-is.
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise
    return overwritten


def _write_new_file(args: argparse.Namespace, opts: NewOptions, text: str) -> int:
    overwritten = _safe_atomic_write(args.path, text, force=args.force)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "spec_id": opts.spec_id,
                    "profile": opts.profile,
                    "path": str(args.path),
                    "written": True,
                    "overwritten": overwritten,
                }
            )
        )
    else:
        print(f"wrote {args.path}")
    return 0


def _run_new(argv: list[str]) -> int:
    json_mode = "--json" in argv  # known even if parsing fails, so usage errors stay JSON (I7)
    ap = _NewArgParser(prog="project-standards spec new")
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--profile", required=True, choices=("light", "standard", "full"))
    ap.add_argument("--id", dest="spec_id")
    ap.add_argument("--title")
    ap.add_argument("--owner")
    ap.add_argument("--implementer")
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)

    try:
        try:
            args = ap.parse_args(argv)
        except _ArgparseError as exc:
            raise NewError("usage", str(exc)) from exc

        if args.path is not None and args.stdout:
            raise NewError("flag_conflict", "--stdout writes to stdout; do not also pass PATH")
        if args.path is None and not args.stdout:
            raise NewError("flag_conflict", "PATH is required unless --stdout")
        if args.stdout and args.force:
            raise NewError("flag_conflict", "--force has no meaning with --stdout")

        opts, template_text = _resolve_new_options(args)
        text = scaffold(template_text, opts, today=date.today())

        # Fail-closed self-validation (I1): never emit a spec validate would reject, and
        # map a parse failure of our OWN output to self_validation_failed (not exit 1).
        try:
            doc = parse_document("<new>", text)
        except SpecParseError as exc:
            raise NewError(
                "self_validation_failed", f"generated scaffold did not parse: {exc}"
            ) from exc
        findings = validate_document(doc, load_registry())
        if findings:
            raise NewError(
                "self_validation_failed",
                "generated scaffold failed self-validation",
                [dataclasses.asdict(f) for f in findings],
            )

        if args.stdout:
            if args.json:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "spec_id": opts.spec_id,
                            "profile": opts.profile,
                            "path": None,
                            "written": False,
                            "content": text,
                        }
                    )
                )
            else:
                sys.stdout.write(text)
            return 0

        return _write_new_file(args, opts, text)  # Task 6
    except NewError as err:
        return _emit_new_failure(json_mode, err)


def _upgrade_output(
    text: str,
    *,
    json_mode: bool,
    source_profile: str,
    target_tier: str,
    spec_id: str,
    path: str | None,
    mode: str,
    written: bool,
) -> None:
    if json_mode:
        obj: dict[str, object] = {
            "ok": True,
            "spec_id": spec_id,
            "from_profile": source_profile,
            "to_profile": target_tier,
            "path": path,
            "written": written,
            "mode": mode,
        }
        if mode == "stdout":
            obj["content"] = text
        print(json.dumps(obj))
    elif mode == "stdout":
        sys.stdout.write(text)
    else:
        print(f"wrote {path}")


def _deliver_upgrade(
    args: argparse.Namespace, text: str, *, source_profile: str, spec_id: str
) -> int:
    if args.in_place:
        target, mode = args.src, "in_place"
    elif args.output is not None:
        if args.output.exists() and args.src.exists() and args.output.samefile(args.src):
            raise NewError("flag_conflict", "output equals source; use --in-place")
        target, mode = args.output, "output"
    else:
        _upgrade_output(
            text,
            json_mode=args.json,
            source_profile=source_profile,
            target_tier=args.to,
            spec_id=spec_id,
            path=None,
            mode="stdout",
            written=False,
        )
        return 0
    # -i overwrites the source as the normal path; -o refuses an existing target unless --force.
    _safe_atomic_write(target, text, force=args.force or args.in_place)
    _upgrade_output(
        text,
        json_mode=args.json,
        source_profile=source_profile,
        target_tier=args.to,
        spec_id=spec_id,
        path=str(target),
        mode=mode,
        written=True,
    )
    return 0


def _run_upgrade(argv: list[str]) -> int:
    json_mode = "--json" in argv  # known even if parsing fails, so usage errors stay JSON (I7)
    ap = _NewArgParser(prog="project-standards spec upgrade")
    ap.add_argument("src", type=Path)
    ap.add_argument("--to", required=True, choices=("standard", "full"))
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--output", "-o", type=Path)
    ap.add_argument("--in-place", "-i", action="store_true", dest="in_place")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    try:
        try:
            args = ap.parse_args(argv)
        except _ArgparseError as exc:
            raise NewError("usage", str(exc)) from exc

        # Flag matrix (Task 9 tests -i/-o cases; wire it all here).
        if args.in_place and args.output is not None:
            raise NewError("flag_conflict", "choose one of --in-place or --output")
        if args.in_place and args.stdout:
            raise NewError("flag_conflict", "--stdout previews; do not also pass --in-place")
        if args.stdout and args.output is not None:
            raise NewError("flag_conflict", "choose one of --stdout or --output")
        if args.force and not args.output:
            raise NewError("flag_conflict", "--force only applies to --output")

        if not args.src.is_file():
            raise NewError("source_not_found", f"source spec not found: {args.src}")
        try:
            source_text = _read(args.src)
        except (SpecParseError, ConfigError) as exc:  # _read wraps OSError/decode errors
            raise NewError("source_read_error", str(exc)) from exc

        reg = load_registry()
        try:
            src_doc = parse_document(str(args.src), source_text)
        except SpecParseError as exc:
            raise NewError("source_read_error", str(exc)) from exc

        # Gate 1: validate-clean.
        findings = validate_document(src_doc, reg)
        if findings:
            raise NewError(
                "source_invalid",
                f"source has {len(findings)} validation finding(s); fix them before upgrading",
                [dataclasses.asdict(f) for f in findings],
            )

        # Tier direction (additive-only). profile is a valid tier here (validate passed).
        source_profile = src_doc.profile or ""
        if _TIER_ORDER.get(source_profile, -1) >= _TIER_ORDER[args.to]:
            raise NewError(
                "not_upgradeable",
                f"cannot upgrade profile {source_profile!r} to {args.to}: additive-only",
            )

        # Gate 2: upgradeability precheck (design decision 10).
        source_template = (TEMPLATES_DIR / TIER_FILES[source_profile]).read_text(encoding="utf-8")
        deviation = check_upgradeable(source_text, source_template)
        if deviation is not None:
            raise NewError("source_not_upgradeable", deviation)

        template_text = (TEMPLATES_DIR / TIER_FILES[args.to]).read_text(encoding="utf-8")
        upgraded = upgrade_text(source_text, template_text, target_tier=args.to)

        # Gate 3: output self-validation (fail-closed, U6).
        try:
            out_doc = parse_document("<upgrade>", upgraded)
        except SpecParseError as exc:
            raise NewError("self_validation_failed", f"upgraded spec did not parse: {exc}") from exc
        out_findings = validate_document(out_doc, reg)
        if out_findings:
            raise NewError(
                "self_validation_failed",
                "upgraded spec failed self-validation",
                [dataclasses.asdict(f) for f in out_findings],
            )

        return _deliver_upgrade(
            args,
            upgraded,
            source_profile=source_profile,
            spec_id=src_doc.frontmatter.get("spec_id", ""),
        )
    except NewError as err:
        return _emit_new_failure(json_mode, err)


_VERBS: dict[str, Callable[[list[str]], int]] = {
    "validate": _run_validate,
    "lint": _run_lint,
    "extract": _run_extract,
    "next": _run_next,
    "new": _run_new,
    "upgrade": _run_upgrade,
}


def run(argv: list[str]) -> int:
    """Run the nested spec command group."""
    if argv[:1] in (["-h"], ["--help"]):
        print(_USAGE)
        return 0
    if not argv:
        print(_USAGE, file=sys.stderr)
        return 2
    verb, rest = argv[0], argv[1:]
    if verb not in _VERBS:
        print(f"error: unknown spec verb {verb!r}", file=sys.stderr)
        return 2
    try:
        return _VERBS[verb](rest)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except SpecParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
