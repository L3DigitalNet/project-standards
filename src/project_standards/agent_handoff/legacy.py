"""Repository-confined, read-only detection of legacy handoff evidence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from project_standards.agent_handoff.integrations.session_start import (
    Syntax,
    duplicate_startup_injection,
)
from project_standards.agent_handoff.model import Finding
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot
from project_standards.control_plane.codec import parse_lock
from project_standards.control_plane.diagnostics import ControlPlaneError


@dataclass(frozen=True)
class PathSignature:
    code: str
    path: str
    message: str
    guidance: str


@dataclass(frozen=True)
class TextSignature:
    code: str
    path: str
    needles: tuple[str, ...]
    message: str
    guidance: str


_PATH_SIGNATURES = (
    PathSignature(
        "AH-LEGACY-ROOT-STATUS",
        "STATUS.md",
        "legacy root status companion is present",
        "Reconcile current facts into docs/STATUS.md before removing the root file.",
    ),
    PathSignature(
        "AH-LEGACY-ROOT-TODO",
        "TODO.md",
        "legacy root task companion is present",
        "Preserve user tasks and reconcile agent work into docs/TODO.md.",
    ),
    PathSignature(
        "AH-LEGACY-DOCS-STATE",
        "docs/state.md",
        "legacy direct-docs state file is present",
        "Route active facts into docs/handoff/state.md and durable facts by lifetime.",
    ),
    PathSignature(
        "AH-LEGACY-MONOLITH",
        "docs/handoff.md",
        "legacy monolithic handoff document is present",
        "Classify each useful fact by lifetime before removing the monolith.",
    ),
    PathSignature(
        "AH-LEGACY-CLAUDE-HOOK",
        ".claude/hooks/session_start.py",
        "legacy Claude-local SessionStart hook is present",
        "Remove it only after the shared v1 hook is installed and verified.",
    ),
    PathSignature(
        "AH-LEGACY-CODEX-HOOK",
        ".codex/hooks/session_start.py",
        "legacy Codex-local SessionStart hook is present",
        "Remove it only after the shared v1 hook is installed and verified.",
    ),
    PathSignature(
        "AH-LEGACY-SKILL",
        ".agents/skills/handoff-system-v3/SKILL.md",
        "legacy handoff-system-v3 skill is present",
        "Review local changes, then replace it with the repo-local agent-handoff skill.",
    ),
    PathSignature(
        "AH-LEGACY-SKILL",
        ".agents/skills/agent-handoff-v3/SKILL.md",
        "legacy agent-handoff-v3 skill is present",
        "Review local changes, then replace it with the repo-local agent-handoff skill.",
    ),
    PathSignature(
        "AH-LEGACY-SKILL",
        ".claude/skills/handoff-system-v3/SKILL.md",
        "legacy harness-local handoff skill is present",
        "Preserve any local guidance, then use only .agents/skills/agent-handoff/.",
    ),
    PathSignature(
        "AH-LEGACY-SKILL",
        ".codex/skills/handoff-system-v3/SKILL.md",
        "legacy harness-local handoff skill is present",
        "Preserve any local guidance, then use only .agents/skills/agent-handoff/.",
    ),
)

_TEXT_SIGNATURES = (
    TextSignature(
        "AH-LEGACY-CLAUDE-REGISTRATION",
        ".claude/settings.json",
        (".claude/hooks/session_start.py",),
        "Claude settings reference a legacy per-harness hook",
        "Reconcile the SessionStart handlers before adopting the v1 Claude profile.",
    ),
    TextSignature(
        "AH-LEGACY-CODEX-REGISTRATION",
        ".codex/config.toml",
        (".codex/hooks/session_start.py",),
        "Codex config references a legacy per-harness hook",
        "Reconcile the inline SessionStart handlers before adopting the v1 Codex profile.",
    ),
    TextSignature(
        "AH-LEGACY-CODEX-REGISTRATION",
        ".codex/hooks.json",
        (".codex/hooks/session_start.py", "handoff-system-v3", "agent-handoff-v3"),
        "Codex hooks.json contains a legacy handoff registration",
        "Consolidate the project hook into the v1 inline config.toml registration.",
    ),
    TextSignature(
        "AH-LEGACY-ENGINE-REFERENCE",
        "AGENTS.md",
        ("handoff-system-v3", "agent-handoff-v3"),
        "agent instructions reference a retired handoff identity",
        "Replace the stale reference with the bounded agent-handoff instruction block.",
    ),
    TextSignature(
        "AH-LEGACY-ENGINE-REFERENCE",
        "CLAUDE.md",
        ("handoff-system-v3", "agent-handoff-v3"),
        "Claude instructions reference a retired handoff identity",
        "Replace the stale reference with the bounded agent-handoff instruction block.",
    ),
    TextSignature(
        "AH-LEGACY-ENGINE-REFERENCE",
        ".project-standards.yml",
        ("handoff-system-v3", "agent-handoff-v3", "engine_schema:"),
        "project configuration references a retired handoff identity or schema",
        "Review the old namespace and adopt the strict agent_handoff v1 configuration.",
    ),
)

# Signature codes describing startup hook and registration evidence. Only these
# defer to lock provenance (issue #90): the applied lock authenticating a unit at
# the same path proves the evidence is the current managed integration, while
# engine-reference prose scanning and every unowned path keeps its finding.
_STARTUP_EVIDENCE_CODES = frozenset(
    {
        "AH-LEGACY-CLAUDE-HOOK",
        "AH-LEGACY-CODEX-HOOK",
        "AH-LEGACY-CLAUDE-REGISTRATION",
        "AH-LEGACY-CODEX-REGISTRATION",
    }
)

# Registration containers whose SessionStart list can hold a legacy group beside
# the managed one. Lock provenance authenticates the managed unit inside these
# files, never the rest of the list, so they are inspected for overlap even when
# `_STARTUP_EVIDENCE_CODES` above defers to the lock (issues #90 and #102).
_REGISTRATION_CONTAINERS: tuple[tuple[str, Syntax], ...] = (
    (".claude/settings.json", "jsonc"),
    (".codex/config.toml", "toml"),
)

_CANONICAL_PREFIXES = (
    ".agents/agent-handoff/",
    ".agents/hooks/agent-handoff/",
    ".agents/skills/agent-handoff/",
    "docs/handoff/",
)
_KNOWN_PATHS = frozenset(signature.path for signature in _PATH_SIGNATURES)
_UNKNOWN_SCAN_ROOTS = (".agents", ".claude", ".codex")


def _is_canonical_path(relative: str) -> bool:
    return any(
        relative == prefix.rstrip("/") or relative.startswith(prefix)
        for prefix in _CANONICAL_PREFIXES
    )


def _finding(
    code: str,
    path: str,
    message: str,
    guidance: str,
    *,
    severity: Literal["error", "warning"] = "warning",
) -> Finding:
    return Finding(
        code=code,
        severity=severity,
        path=path,
        locus="legacy signature",
        message=message,
        guidance=guidance,
    )


def _path_exists(repository: RepositoryRoot, relative: str) -> bool:
    return repository.consumer_path(relative).exists()


def _read_text(repository: RepositoryRoot, relative: str) -> str | None:
    target = repository.consumer_path(relative)
    if not target.exists() or not target.is_file():
        return None
    try:
        return repository.read_bytes(relative).decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _lock_authenticated_paths(repository: RepositoryRoot) -> frozenset[str]:
    """Paths the applied central lock records as agent-handoff managed units.

    Provenance, not drift: the lock naming a managed unit at a path is what
    authenticates hook and registration evidence there as current (issue #90).
    Byte-level divergence inside a managed unit is reconciliation's authority
    (`reconcile --check`), so this report does not recompute digests. An
    absent, unreadable, or non-canonical lock authenticates nothing.
    """
    try:
        raw = repository.read_bytes(".standards/lock.toml")
    except RepositoryBoundaryError, OSError:
        return frozenset()
    try:
        lock = parse_lock(raw)
    except ControlPlaneError:
        return frozenset()
    return frozenset(
        unit.path.original for unit in lock.artifacts if "agent-handoff" in unit.owners
    )


def _unknown_candidates(repository: RepositoryRoot) -> tuple[str, ...]:
    candidates: set[str] = set()
    for entry in repository.path.iterdir():
        if entry.name == ".git":
            continue
        if "handoff" in entry.name.casefold():
            candidates.add(entry.relative_to(repository.path).as_posix())

    docs = repository.path / "docs"
    if docs.is_dir() and not docs.is_symlink():
        for entry in docs.iterdir():
            if entry.name != "handoff" and "handoff" in entry.name.casefold():
                candidates.add(entry.relative_to(repository.path).as_posix())

    for relative_root in _UNKNOWN_SCAN_ROOTS:
        try:
            scan_root = repository.consumer_path(relative_root)
        except RepositoryBoundaryError:
            continue
        if not scan_root.is_dir():
            continue
        for current, directories, files in os.walk(scan_root, followlinks=False):
            directories[:] = [name for name in directories if name != ".git"]
            base = Path(current)
            for name in [*directories, *files]:
                path = base / name
                relative = path.relative_to(repository.path).as_posix()
                if "handoff" in relative.casefold():
                    candidates.add(relative)
    return tuple(sorted(candidates))


def legacy_report(repository: RepositoryRoot) -> tuple[Finding, ...]:
    """Report recognized and unclassified repo-local evidence without mutation."""
    findings: list[Finding] = []
    recognized: set[str] = set()
    legacy_hook_evidence = False
    authenticated = _lock_authenticated_paths(repository)

    for signature in _PATH_SIGNATURES:
        if signature.code in _STARTUP_EVIDENCE_CODES and signature.path in authenticated:
            recognized.add(signature.path)
            continue
        try:
            if not _path_exists(repository, signature.path):
                continue
        except RepositoryBoundaryError:
            findings.append(
                _finding(
                    "AH-LEGACY-SYMLINK",
                    signature.path,
                    "legacy evidence path is symlinked and was not followed",
                    "Inspect the link target manually without granting the standard authority over it.",
                )
            )
            recognized.add(signature.path)
            continue
        findings.append(
            _finding(
                signature.code,
                signature.path,
                signature.message,
                signature.guidance,
            )
        )
        recognized.add(signature.path)
        if signature.code in {"AH-LEGACY-CLAUDE-HOOK", "AH-LEGACY-CODEX-HOOK"}:
            legacy_hook_evidence = True

    for signature in _TEXT_SIGNATURES:
        if signature.code in _STARTUP_EVIDENCE_CODES and signature.path in authenticated:
            recognized.add(signature.path)
            continue
        try:
            text = _read_text(repository, signature.path)
        except RepositoryBoundaryError:
            findings.append(
                _finding(
                    "AH-LEGACY-SYMLINK",
                    signature.path,
                    "legacy configuration path is symlinked and was not followed",
                    "Inspect the link manually and reconcile it outside this report.",
                )
            )
            recognized.add(signature.path)
            continue
        if text is None or not any(
            needle.casefold() in text.casefold() for needle in signature.needles
        ):
            continue
        findings.append(
            _finding(
                signature.code,
                signature.path,
                signature.message,
                signature.guidance,
            )
        )
        recognized.add(signature.path)
        if signature.code in {
            "AH-LEGACY-CLAUDE-REGISTRATION",
            "AH-LEGACY-CODEX-REGISTRATION",
        }:
            legacy_hook_evidence = True

    for relative, syntax in _REGISTRATION_CONTAINERS:
        try:
            text = _read_text(repository, relative)
        except RepositoryBoundaryError:
            continue
        if text is None or not duplicate_startup_injection(text, syntax=syntax):
            continue
        findings.append(
            _finding(
                "AH-LEGACY-DUPLICATE-HOOK",
                relative,
                "more than one SessionStart group injects handoff startup context",
                "Remove the unmanaged SessionStart registration; only the managed unit may inject.",
                severity="error",
            )
        )

    try:
        old_state = _path_exists(repository, "docs/state.md")
        new_state = _path_exists(repository, "docs/handoff/state.md")
    except RepositoryBoundaryError:
        old_state = new_state = False
    if old_state and new_state:
        findings.append(
            _finding(
                "AH-LEGACY-MIXED-LAYOUT",
                "docs/state.md",
                "legacy and canonical state files coexist",
                "Reconcile both files by fact lifetime before removing the legacy copy.",
            )
        )

    # Either launcher counts as the canonical hook: 1.1 through 1.9 install
    # `session_start.py`, 1.10 and newer install the compiled `session-start`. The
    # finding names whichever one is actually present so its path points at a real file.
    canonical_hook = None
    for candidate in (
        ".agents/hooks/agent-handoff/session-start",
        ".agents/hooks/agent-handoff/session_start.py",
    ):
        try:
            if _path_exists(repository, candidate):
                canonical_hook = candidate
                break
        except RepositoryBoundaryError:
            continue
    if canonical_hook is not None and legacy_hook_evidence:
        findings.append(
            _finding(
                "AH-LEGACY-DUPLICATE-HOOK",
                canonical_hook,
                "current and legacy startup injection evidence coexist",
                "Disable legacy registrations before enabling or trusting the v1 hook.",
                severity="error",
            )
        )

    for relative in _unknown_candidates(repository):
        if relative in recognized or relative in _KNOWN_PATHS or relative in authenticated:
            continue
        if _is_canonical_path(relative):
            continue
        findings.append(
            _finding(
                "AH-LEGACY-UNCLASSIFIED",
                relative,
                "unclassified handoff-like repository evidence is present",
                "Inspect this evidence locally; do not infer or automate a migration.",
            )
        )

    unique = {(finding.code, finding.path, finding.message): finding for finding in findings}
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (item.code, item.path, item.locus, item.message),
        )
    )
