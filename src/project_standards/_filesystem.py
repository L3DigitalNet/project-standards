"""Tier-neutral filesystem primitives: bounded writers and corpus selection.

Two unrelated concerns share this module for one reason — both must be callable
from the CLI tier *and* from `control_plane`, so neither may import either side.

The write helpers keep every mutable path component behind an open directory
descriptor. Callers must supply a trusted root descriptor and a validated
relative path; there is deliberately no path-based fallback because re-resolving
a name would reopen the symlink-swap window these operations close.

The selection helpers (`collect_paths`, `select_spec_paths` and their support)
decide WHICH files a standard's provider reads. They were relocated here
unchanged from `validate_frontmatter` and `specs/cli.py` in T15 so
`control_plane.provider_inputs.provider_dispatch_input` can perform provider
input selection itself: both original homes import `control_plane`, so calling
them from the control plane would be a cycle, and restating them would be the
parallel reimplementation FR-015 forbids. `ConfigError` moved with them because
they raise it; `validate_frontmatter` re-exports it, so every existing
`except ConfigError` keeps catching the same class object.

This module must stay import-free of everything but the standard library.
"""

from __future__ import annotations

import os
import secrets
import stat
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager, suppress
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import cast


class _ParentDirectoryError(OSError):
    """A parent component could not be opened or created without following links."""


class _PublishedCleanupError(OSError):
    """Publication succeeded, but its staging alias could not be removed."""

    temporary: str
    cause: OSError

    def __init__(self, temporary: str, cause: OSError) -> None:
        super().__init__(cause.errno, str(cause))
        self.temporary = temporary
        self.cause = cause


def _require_relative(relative: PurePosixPath) -> None:
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(f"unsafe descriptor-relative path: {relative}")


@contextmanager
def _directory_descriptor(  # pyright: ignore[reportUnusedFunction]
    root: Path,
) -> Generator[int]:
    """Open one trusted directory root without following its final component."""
    descriptor = os.open(
        root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _parent_error(part: str, cause: OSError) -> _ParentDirectoryError:
    return _ParentDirectoryError(
        cause.errno,
        f"parent component {part!r} is not a safe directory: {cause}",
    )


def _open_parent_descriptor(
    root_descriptor: int,
    relative: PurePosixPath,
    *,
    create: bool,
) -> int:
    descriptor = os.dup(root_descriptor)
    try:
        for part in relative.parent.parts:
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            except FileNotFoundError as exc:
                if not create:
                    raise _parent_error(part, exc) from exc
                try:
                    os.mkdir(part, mode=0o777, dir_fd=descriptor)
                except FileExistsError:
                    # A concurrent creator is acceptable only if the no-follow
                    # open below proves that the new entry is a real directory.
                    pass
                except OSError as mkdir_exc:
                    raise _parent_error(part, mkdir_exc) from mkdir_exc
                try:
                    child = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=descriptor,
                    )
                except OSError as open_exc:
                    raise _parent_error(part, open_exc) from open_exc
            except OSError as exc:
                raise _parent_error(part, exc) from exc
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _destination_mode(
    parent_descriptor: int,
    destination: str,
    requested: int | None,
) -> tuple[int, bool]:
    if requested is not None:
        return stat.S_IMODE(requested), True
    try:
        current = os.stat(
            destination,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return 0o666, False
    if stat.S_ISREG(current.st_mode):
        return stat.S_IMODE(current.st_mode), True
    return 0o666, False


def _write_bytes(  # pyright: ignore[reportUnusedFunction]
    root_descriptor: int,
    relative: PurePosixPath,
    content: bytes,
    *,
    mode: int | None,
    replace: bool,
    temporary_prefix: str,
) -> bool:
    """Publish bytes below ``root_descriptor`` without following path components.

    Replacement uses descriptor-relative rename. No-clobber publication uses a
    hard link so a concurrently created destination wins atomically; no
    check-then-replace sequence or weaker path-based fallback is permitted.
    """
    _require_relative(relative)
    parent_descriptor = _open_parent_descriptor(
        root_descriptor,
        relative,
        create=True,
    )
    temporary: str | None = None
    staging_descriptor: int | None = None
    try:
        destination = relative.name
        destination_mode, set_exact_mode = _destination_mode(
            parent_descriptor,
            destination,
            mode,
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        while staging_descriptor is None:
            temporary = f"{temporary_prefix}{secrets.token_hex(8)}.tmp"
            try:
                staging_descriptor = os.open(
                    temporary,
                    flags,
                    destination_mode,
                    dir_fd=parent_descriptor,
                )
            except FileExistsError:
                continue
        assert temporary is not None
        staged_name = temporary
        if set_exact_mode:
            # These writers historically treat chmod as best-effort; publication
            # must not gain a new failure mode merely from sharing the safe path.
            with suppress(OSError):
                os.fchmod(staging_descriptor, destination_mode)
        stream = os.fdopen(staging_descriptor, "wb")
        staging_descriptor = None
        with stream:
            stream.write(content)

        if replace:
            os.replace(
                staged_name,
                destination,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            temporary = None
            return True

        try:
            os.link(
                staged_name,
                destination,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileExistsError:
            os.unlink(staged_name, dir_fd=parent_descriptor)
            temporary = None
            return False
        try:
            os.unlink(staged_name, dir_fd=parent_descriptor)
        except OSError as exc:
            raise _PublishedCleanupError(staged_name, exc) from exc
        temporary = None
        return True
    finally:
        if staging_descriptor is not None:
            with suppress(OSError):
                os.close(staging_descriptor)
        if temporary is not None:
            with suppress(OSError):
                os.unlink(temporary, dir_fd=parent_descriptor)
        os.close(parent_descriptor)


def _prune_empty_directory(  # pyright: ignore[reportUnusedFunction]
    root_descriptor: int,
    relative: PurePosixPath,
) -> None:
    """Remove an empty directory tree without following or unlinking any entry."""
    _require_relative(relative)
    parent_descriptor = _open_parent_descriptor(
        root_descriptor,
        relative,
        create=False,
    )
    directory_descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            relative.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
        # fwalk pins each visited directory while yielding it. rmdir is the only
        # mutation: files, links, and nonempty directories therefore make pruning
        # fail closed instead of being followed or recursively deleted.
        for _path, directory_names, _file_names, descriptor in os.fwalk(
            ".",
            topdown=False,
            follow_symlinks=False,
            dir_fd=directory_descriptor,
        ):
            for directory_name in directory_names:
                os.rmdir(directory_name, dir_fd=descriptor)
        os.close(directory_descriptor)
        directory_descriptor = None
        os.rmdir(relative.name, dir_fd=parent_descriptor)
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        os.close(parent_descriptor)


# ---------------------------------------------------------------------------
# Corpus selection (relocated unchanged in T15; see the module docstring)
# ---------------------------------------------------------------------------


class ConfigError(ValueError):
    """An operator/invocation error: unreadable or invalid config, a bad glob or
    named file, a non-string version value, or an unloadable doc_type enum.

    Every CLI boundary in the package maps this to exit 2, so raising it from a
    shared helper is the one sanctioned way to abort with a clean operator error.
    """


DEFAULT_INCLUDE: tuple[str, ...] = ("README.md", "docs/**/*.md")
DEFAULT_EXCLUDE: tuple[str, ...] = (
    "**/*.template.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/**",
    ".claude/**",
    ".codex/**",
    ".github/**",
    "node_modules/**",
)


def _default_corpus(root: Path | None = None) -> list[Path]:
    """Every Markdown file under *root* (default cwd), skipping hidden/vendored trees.

    A bare Path().glob("**/*.md") is rejected here because it recurses into
    .git/, .venv/ and node_modules/ — the advertised zero-config default would
    become unusable after the first dependency install, and validate-references'
    index would fill with vendored docs. Hidden components and node_modules are
    pruned during traversal, so those trees are never walked at all. Explicit
    include patterns are untouched: a repo that wants hidden paths can name them.
    """
    if root is None:
        found: list[Path] = []
        for dirpath, dirnames, filenames in os.walk("."):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
            for filename in filenames:
                if filename.endswith(".md") and not filename.startswith("."):
                    found.append(Path(dirpath, filename))
        return found
    rooted: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        for filename in filenames:
            if filename.endswith(".md") and not filename.startswith("."):
                rooted.append(Path(dirpath, filename).relative_to(root))
    return rooted


def _glob_files(pattern: str, root: Path | None = None) -> list[Path]:
    """Glob *pattern* under *root* (default cwd), surfacing bad patterns as operator errors.

    Path.glob raises NotImplementedError for absolute patterns (and ValueError for
    other unsupported shapes); uncaught, that exits 1 looking like a validator
    crash instead of the documented exit-2 invocation error.
    """
    try:
        if root is None:
            return [p for p in Path().glob(pattern) if p.is_file()]
        return [p.relative_to(root) for p in root.glob(pattern) if p.is_file()]
    except (NotImplementedError, ValueError) as exc:
        raise ConfigError(
            f"invalid glob pattern {pattern!r} (patterns must be relative to the repo root): {exc}"
        ) from exc


def collect_paths(
    explicit: list[Path],
    glob_pattern: str | None,
    include_patterns: list[str],
    exclude_patterns: list[str],
    *,
    on_named_excluded: Callable[[Path], None] | None = None,
    config_driven_invocation: str | None = None,
    root: Path | None = None,
) -> list[Path]:
    """Resolve the final set of files to check.

    Explicit file arguments and/or a --glob take precedence: when either is given,
    the config `include` patterns are NOT added (naming files means "just these").
    Only when nothing is named do we fall back to config `include`, and failing
    that to every Markdown file under cwd. `exclude` is applied in all cases.

    `root` selects the directory patterns resolve against and the base exclusion
    keys are computed from; the returned paths are relative to it. Omit it and
    every step uses the process working directory, which is what every CLI caller
    has always done and must keep doing — their behavior is defined by the
    directory the operator ran the command in. `control_plane.provider_inputs`
    passes the consumer root explicitly, because a composite caller (an MCP
    server process) has no reason for its working directory to be the repository
    it is answering about, and selecting that process's cwd would snapshot the
    wrong corpus (T15 review F3).

    Raises ConfigError for an explicitly named path that is not a regular file:
    globs and includes may legitimately match nothing, but silently dropping a
    named file turns a typo'd CI invocation into a green run that validated
    nothing. Explicit-file callers can set `config_driven_invocation` to render a
    distinct directory diagnostic with their supported no-positional-file command.
    Config-only callers omit it and retain the existing missing-file behavior.

    An explicitly named file that survives the existence check but is then dropped
    by `exclude` is a milder version of the same trap (5.8.0 FR-010, issue #29): the
    file exists, so no ConfigError fires, and it just vanishes from the result with
    no signal. `on_named_excluded`, when given, is called once per such path, in
    sorted order, purely for reporting — it never changes which paths are returned.
    Glob/include-derived paths are expected to be pruned by `exclude` (that is what
    exclude patterns are for) and never trigger the callback; only a path present in
    `explicit` does. Kept as an opt-in callback rather than widening the return type
    so only a caller that opts in pays for the diagnostic.

    Pattern-dialect warning: include patterns use Path.glob semantics (`*` stops at
    `/`), but exclude patterns use fnmatch semantics where `*` ALSO spans path
    separators — `docs/*.md` excludes nested files too. For parity with Path.glob,
    a leading `**/` also matches at the repository root. This asymmetry is the price
    of version-independent `dir/**` exclusion (see the comment below); write exclude
    patterns accordingly.
    """
    paths: set[Path] = set()

    if explicit or glob_pattern:
        invalid: list[tuple[Path, bool]] = []
        for path in explicit:
            try:
                mode = path.stat().st_mode
            except OSError:
                invalid.append((path, False))
                continue
            if stat.S_ISDIR(mode):
                invalid.append((path, True))
            elif not stat.S_ISREG(mode):
                invalid.append((path, False))
        messages: list[str] = []
        directories = [path for path, is_directory in invalid if is_directory]
        if directories and config_driven_invocation is not None:
            messages.append(
                "directory inputs are not supported: "
                + ", ".join(str(path) for path in directories)
                + f"; run {config_driven_invocation!r} without positional FILE arguments "
                "to use configured include patterns"
            )
            missing = [path for path, is_directory in invalid if not is_directory]
        else:
            missing = [path for path, _is_directory in invalid]
        if missing:
            messages.append("no such file: " + ", ".join(str(path) for path in missing))
        if messages:
            raise ConfigError("; ".join(messages))
        paths.update(explicit)
        if glob_pattern:
            paths.update(_glob_files(glob_pattern, root))
    elif include_patterns:
        for pattern in include_patterns:
            paths.update(_glob_files(pattern, root))
    else:
        paths.update(_default_corpus(root))

    # Exclusion matches each candidate's posix path against the patterns with fnmatch
    # rather than Path.glob. Path.glob's `**` semantics are version-dependent (on Python
    # 3.13+ a trailing `**` also matches files; on <=3.12 it matches directories only),
    # so a directory pattern like "docs/decisions/**" would silently fail to exclude the
    # files beneath it on older interpreters. fnmatch's `*` spans path
    # separators, giving consistent prefix-style exclusion on every supported
    # Python version.
    base = (Path.cwd() if root is None else root).resolve()

    def _match_key(path: Path) -> str:
        # Exclude patterns are written repo-root-relative; an explicitly passed
        # absolute path must not bypass them just because its string form differs.
        candidate = path if path.is_absolute() else base / path
        try:
            return candidate.resolve().relative_to(base).as_posix()
        # Unparenthesized multi-exception is PEP 758 (Python >=3.14 only) and is
        # what ruff format enforces here — re-adding parens gets stripped. Do not
        # vendor this file onto older interpreters without re-parenthesizing.
        except OSError, ValueError:
            return path.as_posix()  # outside the repo root — match the raw form

    def is_excluded(path: Path) -> bool:
        key = _match_key(path)
        return any(
            fnmatchcase(key, pattern)
            or (pattern.startswith("**/") and fnmatchcase(key, pattern.removeprefix("**/")))
            for pattern in exclude_patterns
        )

    if on_named_excluded is not None:
        for path in sorted(set(explicit)):
            if is_excluded(path):
                on_named_excluded(path)

    return sorted(p for p in paths if not is_excluded(p))


def select_spec_paths(
    repo: Path,
    effective_config: Mapping[str, object],
) -> list[Path]:
    """Discover the project-spec corpus declared by one selected package.

    Relocated unchanged from `specs/cli.py::_selected_paths` in T15 (the glob
    half only — path capture and the empty-corpus policy stay with the command,
    because both are reporting decisions rather than selection). Unlike
    `collect_paths`, this globs from *repo* rather than the process working
    directory; that difference is the two standards' existing behavior and is
    deliberately preserved, not harmonized.
    """
    raw_patterns = effective_config.get("include_patterns")
    if (
        not isinstance(raw_patterns, list)
        or not raw_patterns
        or not all(isinstance(pattern, str) for pattern in cast("list[object]", raw_patterns))
    ):
        raise ConfigError("selected project-spec include_patterns are invalid")
    paths: set[Path] = set()
    try:
        for pattern in cast("list[str]", raw_patterns):
            if (
                Path(pattern).is_absolute()
                or "\\" in pattern
                or any(part in {".", ".."} for part in Path(pattern).parts)
            ):
                raise ValueError("include pattern escapes the consumer root")
            paths.update(candidate.relative_to(repo) for candidate in repo.glob(pattern))
    except (NotImplementedError, ValueError) as exc:
        raise ConfigError(f"invalid selected project-spec include pattern: {exc}") from exc
    return sorted(paths)
