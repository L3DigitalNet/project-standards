"""Scope validator warnings to the lines a session added, relative to a Git baseline.

Closeout validation of append-only handoff documents re-reports warnings that
were written long before the current policy existed — the session log files
alone carry hundreds — so the findings the current session actually caused are
invisible in the noise. `--since <ref>` keeps a warning only when its line lies
inside a hunk added relative to <ref>.

Two invariants bound the suppression, because hiding a real regression is far
worse than printing a stale one:

  * Severity "error" is never suppressed. Errors decide the exit code; the
    baseline is a readability filter over advisory output, not a policy waiver.
  * A finding without a line number is never suppressed. Document-level rules
    (the hard byte cap, a missing required section) describe the whole file, so
    no added-line range can decide whether this session caused them.

Every Git failure raises BaselineError, which the CLI reports as a usage/state
error, rather than degrading to an unfiltered or unsuppressed report. A silent
fallback is the one outcome a caller cannot detect: the report would look
baseline-scoped while either hiding regressions or reporting the pre-existing
backlog it was invoked to remove.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from project_standards.agent_handoff.model import Baseline, Finding
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot


class BaselineError(ValueError):
    """A baseline ref cannot be resolved, or Git cannot answer for it."""


# `git diff -U0` emits one header per hunk; only the `+` side is read, because
# the findings being filtered carry working-tree line numbers.
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")


def added_line_ranges(diff: str) -> tuple[tuple[int, int], ...]:
    """Return the (start, count) line ranges a unified diff adds to the new file.

    Pure over `git diff -U0` text. A hunk with an explicit zero count (`+7,0`)
    is a pure deletion and adds no line, so it is dropped rather than recorded
    as an empty range. An omitted count means one line, per the unified-diff
    format.
    """
    ranges: list[tuple[int, int]] = []
    for line in diff.splitlines():
        match = _HUNK_HEADER.match(line)
        if match is None:
            continue
        raw_count = match.group("count")
        count = 1 if raw_count is None else int(raw_count)
        if count:
            ranges.append((int(match.group("start")), count))
    return tuple(ranges)


@dataclass(frozen=True, slots=True)
class AddedLines:
    """Which lines of one file are new relative to the baseline."""

    entire_file: bool
    ranges: tuple[tuple[int, int], ...]

    def contains(self, line: int) -> bool:
        if self.entire_file:
            return True
        return any(start <= line < start + count for start, count in self.ranges)


def resolve_baseline_ref(repository: RepositoryRoot, ref: str) -> str:
    """Return the commit OID <ref> names, or raise BaselineError.

    Resolution is deliberately strict: `^{commit}` rejects a ref that names a
    tree or blob, and `--end-of-options` keeps a ref that begins with a dash
    from being read as a Git option.
    """
    if not ref:
        raise BaselineError("--since requires a non-empty Git ref")
    try:
        completed = repository.run_git(
            "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"
        )
    except RepositoryBoundaryError as exc:
        raise BaselineError(f"cannot resolve baseline ref {ref!r}: Git is unavailable") from exc
    resolved = completed.stdout.strip()
    if completed.returncode != 0 or not resolved:
        raise BaselineError(f"cannot resolve baseline ref {ref!r} in this repository")
    return resolved


def _added_lines(repository: RepositoryRoot, resolved: str, path: str) -> AddedLines:
    """Return the added-line ranges for one repository-relative path.

    An untracked path is treated as entirely new: `git diff <commit> -- <path>`
    compares the baseline against the *tracked* working tree and stays silent
    about a file Git does not know, which would otherwise suppress every finding
    in a document the session just created.
    """
    try:
        tracked = repository.run_git("ls-files", "--error-unmatch", "--", path)
        if tracked.returncode != 0:
            return AddedLines(entire_file=True, ranges=())
        completed = repository.run_git(
            "diff", "-U0", "--no-color", "--no-ext-diff", resolved, "--", path
        )
    except RepositoryBoundaryError as exc:
        raise BaselineError(f"cannot diff {path!r} against the baseline") from exc
    if completed.returncode != 0:
        raise BaselineError(
            f"cannot diff {path!r} against the baseline: {completed.stderr.strip()}"
        )
    return AddedLines(entire_file=False, ranges=added_line_ranges(completed.stdout))


def suppress_pre_existing_warnings(
    repository: RepositoryRoot,
    ref: str,
    findings: tuple[Finding, ...],
) -> tuple[tuple[Finding, ...], Baseline]:
    """Drop line-anchored warnings that predate <ref>, and summarize the drop.

    Raises BaselineError for an unresolvable ref, a directory without Git, or
    any Git failure — see this module's fail-closed rationale. Errors and
    findings without a line number pass through untouched by construction.
    """
    resolved = resolve_baseline_ref(repository, ref)
    cache: dict[str, AddedLines] = {}
    kept: list[Finding] = []
    suppressed = 0
    for finding in findings:
        if finding.severity != "warning" or finding.line is None:
            kept.append(finding)
            continue
        added = cache.get(finding.path)
        if added is None:
            added = _added_lines(repository, resolved, finding.path)
            cache[finding.path] = added
        if added.contains(finding.line):
            kept.append(finding)
        else:
            suppressed += 1
    return tuple(kept), Baseline(ref=ref, resolved=resolved, suppressed=suppressed)
