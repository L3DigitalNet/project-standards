"""Nested `project-standards spec` command group."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import json
import os
import random
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import NoReturn, cast

from project_standards._filesystem import (
    _directory_descriptor,  # pyright: ignore[reportPrivateUsage]  # package-internal boundary
    _ParentDirectoryError,  # pyright: ignore[reportPrivateUsage]  # package-internal boundary
    _PublishedCleanupError,  # pyright: ignore[reportPrivateUsage]  # package-internal boundary
    _write_bytes,  # pyright: ignore[reportPrivateUsage]  # package-internal boundary
)
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    SelectedCommandPackage,
    selected_command,
)
from project_standards.control_plane.diagnostics import ControlFinding, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import apply_authoring_plan
from project_standards.control_plane.locking import LockMode
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
)
from project_standards.control_plane.snapshot import EntryKind, RepositorySnapshot, SnapshotEntry
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import JsonObject, JsonValue, ProviderOperation
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
    DiscoveryError,
    SpecConfig,
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


@dataclass(frozen=True, slots=True)
class _SpecRuntime:
    repo: Path
    payload: InstalledPayload | None = None
    effective_config: JsonObject | None = None


def _runtime(repo: Path, selected: SelectedCommandPackage | None) -> _SpecRuntime:
    if selected is None:
        return _SpecRuntime(repo.resolve(strict=True))
    return _SpecRuntime(selected.repo, selected.payload, selected.effective_config)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SpecParseError(f"{path}: not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read spec {path}: {exc}") from exc


def _selected_paths(
    explicit: list[Path], runtime: _SpecRuntime
) -> list[tuple[Path, SnapshotEntry]]:
    if explicit:
        return [
            (path, _selected_snapshot(path, runtime, must_exist=True)[2])
            for path in sorted(explicit)
        ]
    assert runtime.effective_config is not None
    raw_patterns = runtime.effective_config.get("include_patterns")
    if (
        not isinstance(raw_patterns, list)
        or not raw_patterns
        or not all(isinstance(pattern, str) for pattern in raw_patterns)
    ):
        raise ConfigError("selected project-spec include_patterns are invalid")
    paths: set[Path] = set()
    try:
        for pattern in cast(list[str], raw_patterns):
            if (
                Path(pattern).is_absolute()
                or "\\" in pattern
                or any(part in {".", ".."} for part in Path(pattern).parts)
            ):
                raise ValueError("include pattern escapes the consumer root")
            paths.update(
                candidate.relative_to(runtime.repo) for candidate in runtime.repo.glob(pattern)
            )
    except (NotImplementedError, ValueError) as exc:
        raise ConfigError(f"invalid selected project-spec include pattern: {exc}") from exc
    if not paths:
        if _selected_empty_corpus_is_valid(runtime):
            return []
        raise DiscoveryError("spec discovery matched no files")
    return [(path, _selected_snapshot(path, runtime, must_exist=True)[2]) for path in sorted(paths)]


def _selected_empty_corpus_is_valid(runtime: _SpecRuntime) -> bool:
    """Return whether the selected package defines configured zero matches as valid."""
    assert runtime.payload is not None
    version = runtime.payload.manifest.payload.version
    return version.major == 1 and version.minor >= 4


def _selected_snapshot(
    path: Path,
    runtime: _SpecRuntime,
    *,
    must_exist: bool,
) -> tuple[SafeRelativePath, Path, SnapshotEntry]:
    """Capture one V2 CLI path without crossing the selected consumer root."""
    if path.is_absolute():
        raise ConfigError(f"selected path must stay within the consumer root: {path}")
    try:
        relative = SafeRelativePath.parse(path.as_posix())
    except ValueError as exc:
        raise ConfigError(f"selected path must stay within the consumer root: {path}") from exc
    try:
        entry = RepositorySnapshot.capture(runtime.repo, (relative,)).entry(relative)
    except ControlPlaneError as exc:
        raise ConfigError(f"cannot inspect selected path {path}: {exc}") from exc
    if entry.kind is EntryKind.SYMLINK:
        raise ConfigError(f"selected path cannot contain a symlink: {path}")
    if must_exist and entry.kind is EntryKind.MISSING:
        raise ConfigError(f"no such file: {path}")
    allowed = {EntryKind.REGULAR} if must_exist else {EntryKind.MISSING, EntryKind.REGULAR}
    if entry.kind not in allowed:
        raise ConfigError(f"selected path is not a regular file: {path}")
    return relative, runtime.repo / relative.normalized, entry


def _selected_findings(
    paths: list[tuple[Path, SnapshotEntry]],
    runtime: _SpecRuntime,
    *,
    lint: bool,
) -> list[tuple[Path, list[ControlFinding]]]:
    assert runtime.payload is not None
    assert runtime.effective_config is not None
    documents: list[JsonValue] = []
    for display, entry in paths:
        content = entry.content
        if content is None:
            raise ConfigError(f"cannot read spec {display}: snapshot has no regular content")
        documents.append(
            {
                "path": str(display),
                "kind": "regular",
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    operation = ProviderOperation.LINT if lint else ProviderOperation.VALIDATE
    result = invoke_provider(
        ProviderInvocation(
            repo=runtime.repo,
            payload=runtime.payload,
            standard_id="project-spec",
            version=runtime.payload.manifest.payload.version,
            provider_id=operation.value,
            operation=operation,
            effective_config=runtime.effective_config,
            snapshots={"documents": documents},
        )
    )
    grouped: dict[str, list[ControlFinding]] = {str(display): [] for display, _entry in paths}
    for finding in result.findings:
        grouped.setdefault(finding.path, []).append(finding)
    return [(display, grouped[str(display)]) for display, _entry in paths]


def _finding_payload(finding: Finding | ControlFinding) -> dict[str, object]:
    return {
        "code": finding.code,
        "severity": finding.severity,
        "message": finding.message,
        "line": finding.line,
        "locus": finding.locus,
    }


def _run_setwide(argv: list[str], *, lint: bool, runtime: _SpecRuntime) -> int:
    ap = argparse.ArgumentParser(prog=f"project-standards spec {'lint' if lint else 'validate'}")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    if runtime.payload is None:
        reg = load_registry()
        cfg = load_spec_config(args.config)
        paths = collect_spec_paths(args.files, cfg)
        fn = lint_document if lint else validate_document
        legacy_results: list[tuple[Path, list[Finding]]] = []
        for path in paths:
            try:
                legacy_results.append(
                    (
                        path,
                        fn(
                            parse_document(
                                str(path), _read(path), frozenset(cfg.reference_prefixes)
                            ),
                            reg,
                        ),
                    )
                )
            except SpecParseError as exc:
                legacy_results.append(
                    (path, [Finding(code="SV-PARSE", severity="error", message=str(exc))])
                )
        results: Sequence[tuple[Path, Sequence[Finding | ControlFinding]]] = legacy_results
    else:
        try:
            paths = _selected_paths(args.files, runtime)
            selected_results = _selected_findings(paths, runtime, lint=lint) if paths else []
        except ControlPlaneError as exc:
            raise ConfigError(_provider_failure_message(exc)) from exc
        results = selected_results
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "file": str(path),
                        "ok": not findings,
                        "findings": [_finding_payload(finding) for finding in findings],
                    }
                    for path, findings in results
                ],
                indent=2,
            )
        )
    else:
        if not results and runtime.payload is not None and not args.files:
            print("OK   no specification files matched configured include patterns")
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


def _document_snapshot(path: Path, runtime: _SpecRuntime) -> JsonObject:
    entry = _selected_snapshot(path, runtime, must_exist=True)[2]
    content = entry.content
    if content is None:
        raise ConfigError(f"cannot read spec {path}: snapshot has no regular content")
    return {
        "path": str(path),
        "kind": "regular",
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


def _invoke_selected(
    runtime: _SpecRuntime,
    provider_id: str,
    operation: ProviderOperation,
    snapshots: JsonObject,
) -> ProviderResult:
    assert runtime.payload is not None
    assert runtime.effective_config is not None
    return invoke_provider(
        ProviderInvocation(
            repo=runtime.repo,
            payload=runtime.payload,
            standard_id="project-spec",
            version=runtime.payload.manifest.payload.version,
            provider_id=provider_id,
            operation=operation,
            effective_config=runtime.effective_config,
            snapshots=snapshots,
        )
    )


def _run_extract(argv: list[str], runtime: _SpecRuntime) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec extract")
    ap.add_argument("file", type=Path)
    ap.add_argument("selector")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if runtime.payload is None:
        doc = parse_document(str(args.file), _read(args.file))
        result = extract_slice(doc, args.selector)
        payload = {
            "file": str(args.file),
            "selector": result.selector,
            "kind": result.kind,
            "found": result.found,
            "markdown": result.markdown,
        }
    else:
        try:
            provider_result = _invoke_selected(
                runtime,
                "extract",
                ProviderOperation.EXTRACT,
                {
                    "document": _document_snapshot(args.file, runtime),
                    "selector": args.selector,
                },
            )
        except ControlPlaneError as exc:
            raise SpecParseError(_provider_failure_message(exc)) from exc
        structured = provider_result.structured_output
        if structured is None:
            raise ConfigError("selected extract provider returned no content")
        file = structured.get("file")
        selector = structured.get("selector")
        kind = structured.get("kind")
        found = structured.get("found")
        markdown = structured.get("markdown")
        if (
            not isinstance(file, str)
            or not isinstance(selector, str)
            or not isinstance(kind, str)
            or not isinstance(found, bool)
            or not (isinstance(markdown, str) or markdown is None)
        ):
            raise ConfigError("selected extract provider returned invalid content")
        payload = {
            "file": file,
            "selector": selector,
            "kind": kind,
            "found": found,
            "markdown": markdown,
        }
    if args.json:
        print(json.dumps(payload))
    elif payload["found"]:
        print(payload["markdown"])
    else:
        print(f"no match for {payload['selector']!r}", file=sys.stderr)
    return 0 if payload["found"] else 1


def _run_next(argv: list[str], runtime: _SpecRuntime) -> int:
    ap = argparse.ArgumentParser(prog="project-standards spec next")
    ap.add_argument("file", type=Path)
    ap.add_argument("prefix")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if runtime.payload is None:
        doc = parse_document(str(args.file), _read(args.file))
        try:
            nid = next_free_id(doc, load_registry(), args.prefix)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        try:
            result = _invoke_selected(
                runtime,
                "id-next",
                ProviderOperation.ID_NEXT,
                {
                    "document": _document_snapshot(args.file, runtime),
                    "prefix": args.prefix,
                },
            )
        except ControlPlaneError as exc:
            print(f"error: {_provider_failure_message(exc)}", file=sys.stderr)
            return 2
        structured = result.structured_output
        next_id = structured.get("next_id") if structured is not None else None
        if not isinstance(next_id, str):
            raise ConfigError("selected id-next provider returned no content")
        nid = next_id
    prefix = args.prefix.rstrip("-").upper()
    print(
        json.dumps({"file": str(args.file), "prefix": prefix, "next_id": nid}) if args.json else nid
    )
    return 0


def _run_validate(argv: list[str], runtime: _SpecRuntime) -> int:
    return _run_setwide(argv, lint=False, runtime=runtime)


def _run_lint(argv: list[str], runtime: _SpecRuntime) -> int:
    return _run_setwide(argv, lint=True, runtime=runtime)


class _ArgparseError(Exception):
    """Raised by _NewArgParser.error so a bad invocation reaches the JSON wrapper
    instead of argparse's default sys.exit(2) + stderr (which would bypass I7)."""


class _NewArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgparseError(message)

    def recognizes_flag(self, argument: str, *, dest: str) -> bool:
        """Return whether one option token resolves to a flag on this parser."""
        parsed = self._parse_optional(argument)
        if parsed is None or len(parsed) != 1:
            return False
        action, _option_string, _separator, explicit_argument = parsed[0]
        return action is not None and action.dest == dest and explicit_argument is None


def _new_argument_parser(*, add_help: bool = True) -> _NewArgParser:
    parser = _NewArgParser(prog="project-standards spec new", add_help=add_help)
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--profile", required=True, choices=("light", "standard", "full"))
    parser.add_argument("--id", dest="spec_id")
    parser.add_argument("--title")
    parser.add_argument("--owner")
    parser.add_argument("--implementer")
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    return parser


def _upgrade_argument_parser(*, add_help: bool = True) -> _NewArgParser:
    parser = _NewArgParser(prog="project-standards spec upgrade", add_help=add_help)
    parser.add_argument("src", type=Path)
    parser.add_argument("--to", required=True, choices=("standard", "full"))
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--in-place", "-i", action="store_true", dest="in_place")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--config", type=Path, default=None)
    return parser


def _parser_flag_present(parser: _NewArgParser, argv: list[str], *, dest: str) -> bool:
    for argument in argv:
        if argument == "--":
            break
        if not argument.startswith("-"):
            continue
        try:
            if parser.recognizes_flag(argument, dest=dest):
                return True
        except _ArgparseError:
            continue
    return False


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


def _resolve_spec_options(
    args: argparse.Namespace, existing_ids: Callable[[], set[str]]
) -> NewOptions:
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

    known_ids = existing_ids()
    if args.spec_id is not None:
        if not re.match(SPEC_ID_PATTERN, args.spec_id):
            raise NewError("bad_id", f"--id {args.spec_id!r} does not match {SPEC_ID_PATTERN}")
        if args.spec_id in known_ids:
            raise NewError("id_collision", f"--id {args.spec_id} is already used in this repo")
        spec_id = args.spec_id
    else:
        try:
            spec_id = mint_spec_id(random.Random(), known_ids)
        except SpecIdExhausted as exc:
            raise NewError("id_exhausted", str(exc)) from exc

    return NewOptions(
        profile=args.profile,
        spec_id=spec_id,
        title=args.title,
        owner=args.owner,
        implementer=args.implementer,
    )


def _resolve_new_options(args: argparse.Namespace) -> tuple[NewOptions, str, SpecConfig]:
    """Resolve legacy options and return their template and loaded configuration."""
    cfg: SpecConfig | None = None

    def existing_ids() -> set[str]:
        nonlocal cfg
        try:
            cfg = load_spec_config(args.config)
            return collect_existing_spec_ids(cfg)
        except ConfigError as exc:
            raise NewError("config_error", str(exc)) from exc

    opts = _resolve_spec_options(args, existing_ids)
    assert cfg is not None
    template_text = (TEMPLATES_DIR / TIER_FILES[args.profile]).read_text(encoding="utf-8")
    return opts, template_text, cfg


def _selected_existing_ids(runtime: _SpecRuntime) -> set[str]:
    try:
        selected = _selected_paths([], runtime)
    except DiscoveryError:
        return set()
    ids: set[str] = set()
    for display, entry in selected:
        if entry.content is None:
            continue
        try:
            document = parse_document(str(display), entry.content.decode("utf-8"))
        except UnicodeDecodeError, SpecParseError:
            continue
        spec_id = document.frontmatter.get("spec_id")
        if spec_id:
            ids.add(spec_id)
    return ids


def _selected_new_options(args: argparse.Namespace, runtime: _SpecRuntime) -> NewOptions:
    return _resolve_spec_options(args, lambda: _selected_existing_ids(runtime))


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


def _descriptor_target(target: Path) -> tuple[Path, PurePosixPath]:
    """Anchor a target for descriptor-relative mutation without changing CLI reach."""
    working_directory = Path.cwd()
    lexical = target if target.is_absolute() else working_directory / target
    normalized = Path(os.path.normpath(lexical))
    if normalized.is_relative_to(working_directory):
        # Relative paths stay bound to the process cwd descriptor even if its
        # pathname is concurrently renamed and replaced by another directory.
        root = working_directory if target.is_absolute() else Path()
        return (
            root,
            PurePosixPath(normalized.relative_to(working_directory).as_posix()),
        )

    # Absolute and explicit outside-cwd targets have always been supported. Resolve
    # their parent once before opening descriptors so an allowed symlink above cwd
    # selects a physical directory, while the final destination is never followed.
    resolved_parent = target.parent.resolve(strict=False)
    resolved_target = resolved_parent / target.name
    anchor = Path(resolved_target.anchor)
    return anchor, PurePosixPath(resolved_target.relative_to(anchor).as_posix())


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
    root, relative = _descriptor_target(target)
    try:
        with _directory_descriptor(root) as root_descriptor:
            installed = _write_bytes(
                root_descriptor,
                relative,
                text.encode("utf-8"),
                mode=None,
                replace=force or overwritten,
                temporary_prefix=".spec-write-",
            )
    except _ParentDirectoryError as exc:
        raise NewError(
            "mkdir_failed", f"cannot create parent directory for {target}: {exc}"
        ) from exc
    except _PublishedCleanupError as exc:
        temporary = target.parent / exc.temporary
        raise NewError(
            "write_failed",
            f"destination {target} was installed but staging cleanup failed for "
            f"{temporary}: {exc.cause}",
        ) from exc.cause
    except OSError as exc:
        raise NewError("write_failed", f"cannot write {target}: {exc}") from exc
    if not installed:
        raise NewError("exists", f"refusing to overwrite existing file: {target} (use --force)")
    return overwritten


def _print_new_success_json(
    args: argparse.Namespace,
    opts: NewOptions,
    *,
    overwritten: bool,
) -> None:
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


def _write_new_file(args: argparse.Namespace, opts: NewOptions, text: str) -> int:
    overwritten = _safe_atomic_write(args.path, text, force=args.force)
    if args.json:
        _print_new_success_json(args, opts, overwritten=overwritten)
    else:
        print(f"wrote {args.path}")
    return 0


def _selected_authoring_target(
    path: Path,
    runtime: _SpecRuntime,
    *,
    force: bool,
) -> tuple[Path, JsonObject, bool]:
    try:
        _relative, _raw_target, entry = _selected_snapshot(path, runtime, must_exist=False)
    except ConfigError as exc:
        code = "symlinked_parent" if "symlink" in str(exc) else "not_regular_file"
        raise NewError(code, str(exc)) from exc
    return (
        runtime.repo,
        _authoring_snapshot(path, entry, force=force),
        entry.kind is EntryKind.REGULAR,
    )


def _authoring_snapshot(path: Path, entry: SnapshotEntry, *, force: bool) -> JsonObject:
    """Bind one authoring request to the exact bytes and mode already captured."""
    if entry.kind not in {EntryKind.MISSING, EntryKind.REGULAR}:
        raise NewError("not_regular_file", f"refusing to write non-regular target: {path}")
    overwritten = entry.kind is EntryKind.REGULAR
    if overwritten and not force:
        raise NewError("exists", f"refusing to overwrite existing file: {path} (use --force)")
    return {
        "target": entry.path.original,
        "kind": entry.kind.value,
        "precondition_digest": entry.precondition_digest.value,
        "mode": entry.mode,
        "overwrite": force,
    }


def _write_selected_new(
    args: argparse.Namespace,
    opts: NewOptions,
    runtime: _SpecRuntime,
) -> int:
    executor_root, target, overwritten = _selected_authoring_target(
        args.path,
        runtime,
        force=args.force,
    )
    target.update(
        {
            "profile": opts.profile,
            "spec_id": opts.spec_id,
            "today": date.today().isoformat(),
            "title": opts.title,
            "owner": opts.owner,
            "implementer": opts.implementer,
        }
    )
    try:
        result = _invoke_selected(
            runtime,
            "scaffold",
            ProviderOperation.SCAFFOLD,
            {"authoring": target},
        )
    except ControlPlaneError as exc:
        raise NewError("self_validation_failed", str(exc)) from exc
    if result.mutation_plan is None:
        raise NewError("self_validation_failed", "selected scaffold provider returned no plan")
    applied = apply_authoring_plan(executor_root, result.mutation_plan)
    if not applied.success:
        raise NewError("write_failed", f"cannot write {args.path}: {applied.error_code}")
    if args.json:
        _print_new_success_json(args, opts, overwritten=overwritten)
    else:
        print(result.mutation_plan.actions[0].summary)
    return 0


def _run_new(argv: list[str], runtime: _SpecRuntime) -> int:
    ap = _new_argument_parser()
    json_mode = _parser_flag_present(ap, argv, dest="json")
    legacy_config: SpecConfig | None = None

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

        if runtime.payload is None:
            opts, template_text, legacy_config = _resolve_new_options(args)
            text = scaffold(template_text, opts, today=date.today())
        else:
            opts = _selected_new_options(args, runtime)
            if not args.stdout:
                return _write_selected_new(args, opts, runtime)
            try:
                preview = _invoke_selected(
                    runtime,
                    "render-preview",
                    ProviderOperation.RENDER,
                    {
                        "preview": {
                            "operation": "scaffold",
                            "profile": opts.profile,
                            "spec_id": opts.spec_id,
                            "today": date.today().isoformat(),
                            "title": opts.title,
                            "owner": opts.owner,
                            "implementer": opts.implementer,
                        }
                    },
                )
            except ControlPlaneError as exc:
                raise NewError("self_validation_failed", str(exc)) from exc
            if preview.content is None:
                raise NewError(
                    "self_validation_failed", "selected scaffold preview returned no content"
                )
            try:
                text = preview.content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise NewError(
                    "self_validation_failed", "selected scaffold preview was not UTF-8"
                ) from exc

        if runtime.payload is None:
            # The selected provider performs the same fail-closed check against its
            # payload templates before returning preview bytes.
            assert legacy_config is not None
            try:
                doc = parse_document("<new>", text, frozenset(legacy_config.reference_prefixes))
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
    summary: str | None = None,
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
        print(summary or f"wrote {path}")


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


def _provider_failure_message(exc: ControlPlaneError) -> str:
    cause = exc.__cause__
    return str(cause) if isinstance(cause, Exception) and str(cause) else str(exc)


def _selected_upgrade_source(
    args: argparse.Namespace,
    runtime: _SpecRuntime,
    source_text: str,
    source_entry: SnapshotEntry,
) -> tuple[str, str]:
    try:
        source_results = _selected_findings(
            [(args.src, source_entry)],
            runtime,
            lint=False,
        )
    except ControlPlaneError as exc:
        raise NewError("config_error", _provider_failure_message(exc)) from exc
    source_findings = source_results[0][1]
    if source_findings:
        raise NewError(
            "source_invalid",
            f"source has {len(source_findings)} validation finding(s); fix them before upgrading",
            [_finding_payload(finding) for finding in source_findings],
        )
    try:
        source_document = parse_document(str(args.src), source_text)
    except SpecParseError as exc:
        raise NewError("source_read_error", str(exc)) from exc
    source_profile = source_document.profile or ""
    if _TIER_ORDER.get(source_profile, -1) >= _TIER_ORDER[args.to]:
        raise NewError(
            "not_upgradeable",
            f"cannot upgrade profile {source_profile!r} to {args.to}: additive-only",
        )
    return source_profile, source_document.frontmatter.get("spec_id", "")


def _selected_upgrade_preview(
    args: argparse.Namespace,
    runtime: _SpecRuntime,
    source_text: str,
    source_entry: SnapshotEntry,
) -> tuple[str, str, str]:
    source_profile, spec_id = _selected_upgrade_source(args, runtime, source_text, source_entry)
    try:
        result = _invoke_selected(
            runtime,
            "render-preview",
            ProviderOperation.RENDER,
            {
                "preview": {
                    "operation": "upgrade",
                    "target": str(args.src),
                    "content_base64": base64.b64encode(source_text.encode()).decode("ascii"),
                    "target_profile": args.to,
                }
            },
        )
    except ControlPlaneError as exc:
        raise NewError("source_not_upgradeable", _provider_failure_message(exc)) from exc
    if result.content is None:
        raise NewError("self_validation_failed", "selected upgrade preview returned no content")
    try:
        upgraded = result.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NewError("self_validation_failed", "selected upgrade preview was not UTF-8") from exc
    return upgraded, source_profile, spec_id


def _deliver_selected_upgrade(
    args: argparse.Namespace,
    runtime: _SpecRuntime,
    source_text: str,
    source_entry: SnapshotEntry,
    output_entry: SnapshotEntry | None,
    *,
    source_profile: str,
    spec_id: str,
) -> int:
    target = args.src if args.in_place else args.output
    if target is None:
        raise NewError("flag_conflict", "selected upgrade write requires a target")
    target_entry = source_entry if args.in_place else output_entry
    if target_entry is None:
        raise NewError("flag_conflict", "selected upgrade output snapshot is missing")
    authoring = _authoring_snapshot(target, target_entry, force=args.force or args.in_place)
    authoring.update(
        {
            "content_base64": base64.b64encode(source_text.encode()).decode("ascii"),
            "target_profile": args.to,
        }
    )
    try:
        result = _invoke_selected(
            runtime,
            "upgrade",
            ProviderOperation.UPGRADE,
            {"authoring": authoring},
        )
    except ControlPlaneError as exc:
        raise NewError("source_not_upgradeable", _provider_failure_message(exc)) from exc
    if result.mutation_plan is None:
        raise NewError("self_validation_failed", "selected upgrade provider returned no plan")
    applied = apply_authoring_plan(runtime.repo, result.mutation_plan)
    if not applied.success:
        raise NewError("write_failed", f"cannot write {target}: {applied.error_code}")
    action = result.mutation_plan.actions[0]
    content = (action.content_bytes or b"").decode("utf-8")
    _upgrade_output(
        content,
        json_mode=args.json,
        source_profile=source_profile,
        target_tier=args.to,
        spec_id=spec_id,
        path=str(target),
        mode="in_place" if args.in_place else "output",
        written=True,
        summary=action.summary,
    )
    return 0


def _run_upgrade(argv: list[str], runtime: _SpecRuntime) -> int:
    ap = _upgrade_argument_parser()
    json_mode = _parser_flag_present(ap, argv, dest="json")
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

        selected_source_entry: SnapshotEntry | None = None
        selected_output_entry: SnapshotEntry | None = None
        if runtime.payload is not None:
            try:
                _source_relative, selected_source, selected_source_entry = _selected_snapshot(
                    args.src,
                    runtime,
                    must_exist=True,
                )
            except ConfigError as exc:
                raise NewError("source_not_found", str(exc)) from exc
            if args.output is not None:
                try:
                    _output_relative, selected_output, selected_output_entry = _selected_snapshot(
                        args.output,
                        runtime,
                        must_exist=False,
                    )
                except ConfigError as exc:
                    code = "symlinked_parent" if "symlink" in str(exc) else "not_regular_file"
                    raise NewError(code, str(exc)) from exc
                if selected_output_entry.kind is EntryKind.REGULAR:
                    try:
                        same_file = selected_output.samefile(selected_source)
                    except OSError as exc:
                        raise NewError(
                            "not_regular_file", f"cannot inspect output target: {args.output}"
                        ) from exc
                    if same_file:
                        raise NewError("flag_conflict", "output equals source; use --in-place")
        if runtime.payload is None and not args.src.is_file():
            raise NewError("source_not_found", f"source spec not found: {args.src}")
        if selected_source_entry is not None:
            assert selected_source_entry.content is not None
            try:
                source_text = selected_source_entry.content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise NewError("source_read_error", f"{args.src}: not valid UTF-8: {exc}") from exc
        else:
            try:
                source_text = _read(args.src)
            except (SpecParseError, ConfigError) as exc:  # _read wraps OSError/decode errors
                raise NewError("source_read_error", str(exc)) from exc

        if runtime.payload is not None:
            assert selected_source_entry is not None
            if not args.in_place and args.output is None:
                upgraded, source_profile, spec_id = _selected_upgrade_preview(
                    args,
                    runtime,
                    source_text,
                    selected_source_entry,
                )
                _upgrade_output(
                    upgraded,
                    json_mode=args.json,
                    source_profile=source_profile,
                    target_tier=args.to,
                    spec_id=spec_id,
                    path=None,
                    mode="stdout",
                    written=False,
                )
                return 0
            source_profile, spec_id = _selected_upgrade_source(
                args, runtime, source_text, selected_source_entry
            )
            return _deliver_selected_upgrade(
                args,
                runtime,
                source_text,
                selected_source_entry,
                selected_output_entry,
                source_profile=source_profile,
                spec_id=spec_id,
            )

        reg = load_registry()
        # --config is opt-in (default None): with no --config, .project-standards.yml is
        # never read, even if malformed, preserving v4.0.0 default behavior exactly (SA-001).
        try:
            refs: frozenset[str] = (
                frozenset(load_spec_config(args.config).reference_prefixes)
                if args.config is not None
                else frozenset()
            )
        except ConfigError as exc:
            raise NewError("config_error", str(exc)) from exc
        try:
            src_doc = parse_document(str(args.src), source_text, refs)
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
            out_doc = parse_document("<upgrade>", upgraded, refs)
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


_VERBS = frozenset({"validate", "lint", "extract", "next", "new", "upgrade"})


def _explicit_config(argv: list[str]) -> Path | None:
    """Return an operator-typed debug config without interpreting verb syntax."""
    for index, argument in enumerate(argv):
        if argument == "--config" and index + 1 < len(argv):
            return Path(argv[index + 1])
        if argument.startswith("--config="):
            value = argument.removeprefix("--config=")
            if not value:
                raise CommandResolutionError("--config requires a non-empty path")
            return Path(value)
    return None


def _operation_lock_mode(verb: str, argv: list[str]) -> LockMode:
    """Select exclusivity from the command's actual write authorization."""
    if verb == "new":
        parser = _new_argument_parser(add_help=False)
    elif verb == "upgrade":
        parser = _upgrade_argument_parser(add_help=False)
    else:
        return LockMode.READ

    try:
        args = parser.parse_args(argv)
    except _ArgparseError, SystemExit:
        return LockMode.WRITE
    if verb == "new":
        return LockMode.READ if args.stdout else LockMode.WRITE
    return LockMode.WRITE if args.in_place or args.output is not None else LockMode.READ


def run(
    argv: list[str],
    *,
    repo: Path | None = None,
    distribution: InstalledDistribution | None = None,
) -> int:
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
        root = repo or Path.cwd()
        mode = _operation_lock_mode(verb, rest)
        with selected_command(
            root,
            "project-spec",
            distribution,
            mode=mode,
            explicit_legacy=_explicit_config(rest),
        ) as selected:
            runtime = _runtime(root, selected)
            if verb == "validate":
                return _run_validate(rest, runtime)
            if verb == "lint":
                return _run_lint(rest, runtime)
            if verb == "extract":
                return _run_extract(rest, runtime)
            if verb == "next":
                return _run_next(rest, runtime)
            if verb == "new":
                return _run_new(rest, runtime)
            if verb == "upgrade":
                return _run_upgrade(rest, runtime)
            raise AssertionError(f"unhandled spec verb: {verb}")
    except CommandResolutionError as exc:
        message = str(exc)
        if "disabled" in message or "not present" in message:
            message = "project-spec package is disabled or not selected"
        elif "payload is unavailable" in message:
            message = "selected project-spec payload is unavailable"
        if verb in {"new", "upgrade"} and "--json" in rest:
            return _emit_new_failure(True, NewError("config_error", message))
        print(f"error: {message}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except SpecParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
