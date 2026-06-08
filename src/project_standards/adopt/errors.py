"""Adopt-engine errors. Each carries the CLI exit code it maps to (Component 3)."""

from __future__ import annotations


class AdoptError(Exception):
    """Base for adopt errors. `exit_code` is the process exit status at the CLI boundary."""

    exit_code: int = 1


class UsageError(AdoptError):
    """Bad invocation or manifest authoring bug (unknown standard, dest collision,
    unsafe destination path, non-directory --dest). Exit 2."""

    exit_code = 2


class ManifestError(AdoptError):
    """Missing prerequisite: a manifest is malformed/absent, or a source path is
    missing from the package or escapes the bundle tree; package version unresolvable.
    Exit 3."""

    exit_code = 3


class WriteError(AdoptError):
    """Recoverable I/O failure during execution (permission denied, partial write).
    Exit 1."""

    exit_code = 1
