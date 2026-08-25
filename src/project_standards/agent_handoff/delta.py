"""Answer "what happened this session?" from Git, for handoff closeout.

Closeout agents otherwise reconstruct the answer with a handful of ad-hoc `git
log`, `git diff`, and `grep` invocations whose shape varies per session. This
module produces one deterministic report — commits, changed paths grouped by
whether they are handoff state, issue references, and the uncommitted
remainder — so the closeout write-up is derived rather than recalled.

The baseline ref is resolved through the same fail-closed path as `--since`
validation (see since.resolve_baseline_ref): an unresolvable ref is an error,
never an empty delta, because an empty delta reads as "nothing happened".

Git access goes through RepositoryRoot.run_git, which pins the working
directory and forbids repository-override arguments, so the report can never
describe a repository other than the one the caller named.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot
from project_standards.agent_handoff.since import BaselineError, resolve_baseline_ref

# Handoff state as the Agent Handoff standard lays it out: the handoff tree plus
# the two top-level documents it owns. Kept in step with the managed document set
# these commands validate; a path added there belongs here too.
_HANDOFF_PREFIX = "docs/handoff/"
_HANDOFF_FILES = frozenset({"docs/STATUS.md", "docs/TODO.md"})
_DOCS_PREFIX = "docs/"

PathGroup = Literal["handoff", "docs", "other"]

# `owner/repo#12` and bare `#12`. The lookbehind refuses a match inside a word
# or path fragment, so `abc#12` and `refs/heads/x#1` do not read as references.
_ISSUE_REFERENCE = re.compile(r"(?<![\w./-])(?:(?P<repo>[\w.-]+/[\w.-]+))?#(?P<number>\d+)(?!\w)")

_FIELD_SEPARATOR = "\x1f"
_RECORD_SEPARATOR = "\x1e"


@dataclass(frozen=True, slots=True)
class Commit:
    oid: str
    subject: str


@dataclass(frozen=True, slots=True)
class WorkingTreeChange:
    status: str
    path: str


@dataclass(frozen=True, slots=True)
class SessionDelta:
    ref: str
    resolved: str
    commits: tuple[Commit, ...]
    handoff_paths: tuple[str, ...]
    doc_paths: tuple[str, ...]
    other_paths: tuple[str, ...]
    issues: tuple[str, ...]
    uncommitted: tuple[WorkingTreeChange, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "ref": self.ref,
            "resolved": self.resolved,
            "commits": [{"oid": commit.oid, "subject": commit.subject} for commit in self.commits],
            "paths": {
                "handoff": list(self.handoff_paths),
                "docs": list(self.doc_paths),
                "other": list(self.other_paths),
            },
            "issues": list(self.issues),
            "uncommitted": [
                {"status": change.status, "path": change.path} for change in self.uncommitted
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"


def classify_path(path: str) -> PathGroup:
    """Group one repository-relative path for the delta report."""
    if path in _HANDOFF_FILES or path.startswith(_HANDOFF_PREFIX):
        return "handoff"
    if path.startswith(_DOCS_PREFIX):
        return "docs"
    return "other"


def issue_references(text: str) -> tuple[str, ...]:
    """Return the deduplicated issue references in commit prose, in stable order.

    Ordering is by repository qualifier then issue number rather than by
    appearance, so two runs over the same range agree byte for byte even when
    commit order changes underneath.
    """
    found = {
        f"{match.group('repo')}#{match.group('number')}"
        if match.group("repo")
        else f"#{match.group('number')}": (match.group("repo") or "", int(match.group("number")))
        for match in _ISSUE_REFERENCE.finditer(text)
    }
    return tuple(sorted(found, key=lambda reference: found[reference]))


def _git(repository: RepositoryRoot, *args: str) -> str:
    try:
        completed = repository.run_git(*args)
    except RepositoryBoundaryError as exc:
        raise BaselineError(f"Git command failed: git {' '.join(args)}") from exc
    if completed.returncode != 0:
        raise BaselineError(f"Git command failed: git {' '.join(args)}: {completed.stderr.strip()}")
    return completed.stdout


def _commits(repository: RepositoryRoot, resolved: str) -> tuple[tuple[Commit, ...], str]:
    """Return the commits in <resolved>..HEAD plus their concatenated prose.

    Subjects and bodies are read in one pass with control-character separators
    because a commit body is multi-line: line-oriented parsing cannot tell a
    body line from the next record.
    """
    raw = _git(
        repository,
        "log",
        f"--format=%h{_FIELD_SEPARATOR}%s{_FIELD_SEPARATOR}%b{_RECORD_SEPARATOR}",
        f"{resolved}..HEAD",
    )
    commits: list[Commit] = []
    prose: list[str] = []
    for record in raw.split(_RECORD_SEPARATOR):
        stripped = record.strip("\n")
        if not stripped:
            continue
        oid, _, remainder = stripped.partition(_FIELD_SEPARATOR)
        subject, _, body = remainder.partition(_FIELD_SEPARATOR)
        commits.append(Commit(oid=oid, subject=subject))
        prose.append(f"{subject}\n{body}")
    return tuple(commits), "\n".join(prose)


def _uncommitted(repository: RepositoryRoot) -> tuple[WorkingTreeChange, ...]:
    """Return working-tree and index changes, including untracked entries (`??`).

    Paths are Git's own porcelain-v1 display form, so a path with unusual bytes
    arrives quoted exactly as `git status` would print it.
    """
    changes: list[WorkingTreeChange] = []
    for line in _git(repository, "status", "--porcelain").splitlines():
        if len(line) < 4:
            continue
        changes.append(WorkingTreeChange(status=line[:2], path=line[3:]))
    return tuple(changes)


def collect_delta(repository: RepositoryRoot, ref: str) -> SessionDelta:
    """Collect the session delta between <ref> and HEAD.

    Raises BaselineError for an unresolvable ref or any Git failure. An empty
    delta is a success: a session that committed nothing is a legitimate answer,
    while a wrong ref must not be reported as one.
    """
    resolved = resolve_baseline_ref(repository, ref)
    commits, prose = _commits(repository, resolved)
    grouped: dict[PathGroup, list[str]] = {"handoff": [], "docs": [], "other": []}
    for path in _git(repository, "diff", "--name-only", resolved, "HEAD", "--").splitlines():
        if path:
            grouped[classify_path(path)].append(path)
    return SessionDelta(
        ref=ref,
        resolved=resolved,
        commits=commits,
        handoff_paths=tuple(sorted(grouped["handoff"])),
        doc_paths=tuple(sorted(grouped["docs"])),
        other_paths=tuple(sorted(grouped["other"])),
        issues=issue_references(prose),
        uncommitted=_uncommitted(repository),
    )


def format_delta(delta: SessionDelta) -> str:
    """Render the delta for a human or an agent reading the terminal."""
    lines = [f"delta {delta.ref} ({delta.resolved[:12]}..HEAD)"]
    lines.append(f"commits ({len(delta.commits)}):")
    lines.extend(f"  {commit.oid} {commit.subject}" for commit in delta.commits)
    for label, paths in (
        ("handoff documents", delta.handoff_paths),
        ("other docs", delta.doc_paths),
        ("code/other", delta.other_paths),
    ):
        lines.append(f"{label} ({len(paths)}):")
        lines.extend(f"  {path}" for path in paths)
    lines.append(f"issue references: {', '.join(delta.issues) if delta.issues else 'none'}")
    lines.append(f"uncommitted changes ({len(delta.uncommitted)}):")
    lines.extend(f"  {change.status} {change.path}" for change in delta.uncommitted)
    return "\n".join(lines) + "\n"
