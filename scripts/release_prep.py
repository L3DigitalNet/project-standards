#!/usr/bin/env python3
"""release_prep.py — the mechanical subset of a project-standards release cut.

`meta/versioning.md` "Release requirements" is the authority. This script automates
only the steps that have no judgment in them: the version bump plus lock, the
CHANGELOG `[Unreleased]` conversion, and the wiring/verification chain. Everything
that decides *what* a release means stays with the owner and is deliberately absent
here:

  * steps 1-2 (signed full-version tag, moving-major tag) — a tag is the release
    contract; a script must never mint or move one.
  * step 3 (in-repo `@vN` reference rewrite, MAJOR only) — versioning.md carves out
    three classes that must be reviewed individually (UPGRADING.md history, fixed
    `blob/vN` permalinks, a standard's first-shipping examples), so the default run
    *reports* stale references and rewrites none. `--apply-pins` rewrites the
    strictly mechanical subset of them, named site by site in an allow-list.
  * step 6 (UPGRADING.md prose, MAJOR only) — authored migration prose.

The script edits files and runs the mechanical wiring checks. It never commits,
tags, pushes, touches a remote, or executes the required candidate-wheel release
verification; its summary prints that operator handoff before tag instructions.

Usage (from the repository root):

    uv run python scripts/release_prep.py X.Y.Z [--dry-run]
    uv run python scripts/release_prep.py X.Y.Z --apply-pins [--dry-run]

`--dry-run` prints every planned edit and mutation command without performing any
of them; the read-only `--check` verification commands still run so the dry run
reports the true pre-bump state of the chain.

`--apply-pins` is a separate mode, not an extra step of the default run: it does
only the allow-listed pin rewrites (runbook step R3) and exits, because those land
after the version bump has been reviewed. See `run_apply_pins`.

Exit codes: 0 success, 1 a step failed, 2 bad invocation.

Stdlib only, matching scripts/check.py: these helpers must run
before the project environment is guaranteed to be in any particular state.
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parent.parent

# The control-plane paths are fixed by the V5 consumer contract (SPEC-CP01), not
# discovered: `.standards/catalog.toml` is the one generated consumer-catalog
# projection this repository dogfoods, and `check-release` names it verbatim in its
# PC-RELEASE-PROJECTION finding.
CONSUMER_CATALOG = Path(".standards/catalog.toml")

# Version and changelog mutations must be committed on main before their candidate
# wheel is built; preparing elsewhere can otherwise validate bytes that are never
# tagged. Keep this in lockstep with meta/versioning.md's release ordering.
RELEASE_BRANCH = "main"

_SEMVER = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\.(?P<patch>0|[1-9][0-9]*)$"
)
# Cross-file contract: these forms and historical classifiers mirror
# package_contract/release_consistency.py. This bare-stdlib script cannot import the
# candidate package before release setup, so representative tests keep the copies aligned.
_PACKAGE_VERSION_TEXT = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
_PACKAGE_VERSION = re.compile(r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)$")
_FAMILY_ID = re.compile(r"^[a-z][a-z0-9-]*$")
_EXACT_SELECTOR = re.compile(
    rf"(?<![A-Za-z0-9_-])(?P<family>[a-z][a-z0-9-]*)@"
    rf"(?P<version>{_PACKAGE_VERSION_TEXT})(?![0-9]|\.[0-9])"
)
_FULL_VERSION_PATH = re.compile(
    rf"(?<![A-Za-z0-9_./-])standards/(?P<family>[a-z][a-z0-9-]*)/"
    rf"versions/(?P<version>{_PACKAGE_VERSION_TEXT})(?=/)"
)
_SHALLOW_VERSION_PATH = re.compile(
    rf"(?<![A-Za-z0-9_./-])versions/(?P<version>{_PACKAGE_VERSION_TEXT})(?=/)"
)
_ENABLE_COMMAND = re.compile(
    rf"project-standards\s+standards\s+enable\s+"
    rf"(?P<family>[a-z][a-z0-9-]*)\s+--version(?:=|\s+)"
    rf"(?P<version>{_PACKAGE_VERSION_TEXT})(?![0-9]|\.[0-9])"
)
_FAMILY_VERSION = re.compile(
    rf"(?<![A-Za-z0-9_-])(?P<family>[a-z][a-z0-9-]*)\s+version\s+"
    rf"`?(?P<version>{_PACKAGE_VERSION_TEXT})`?(?![0-9]|\.[0-9])",
    re.IGNORECASE,
)
_BARE_PACKAGE_VERSION = re.compile(
    rf"\b(?:Internal package|Package(?:\s+version)?)\s+`?"
    rf"(?P<version>{_PACKAGE_VERSION_TEXT})`?(?![0-9]|\.[0-9])",
    re.IGNORECASE,
)
_REFERENCE_MARKER = re.compile(
    r"<!-- release-consistency: "
    r"(?P<kind>historical|historical-characterization|catalog-range|inventory) "
    r"(?P<family>[a-z][a-z0-9-]*)"
    r"(?: (?P<source>catalog|family))? -->"
)
_HISTORICAL_SECTIONS = frozenset(
    {
        "deviations",
        "legacy boundary",
        "migration",
        "released-version errata",
        "revision history",
    }
)
_NATURAL_HISTORY_PHRASES = (
    "correction from",
    "historical #",
    "historical limitations",
    "immutable ",
    "released history",
    "remain advertised as released history",
    "migration evidence only",
    "previous behavior",
    "prior internal",
    "superseded package",
)
_CATALOG_ROLES = frozenset({"default", "retained", "candidate", "reference-only", "internal"})
_SELECTED_ROLES = frozenset({"default", "reference-only", "internal"})
_PACKAGE_REFERENCE_DOCUMENTS = ("README.md", "adopt.md", "agent-summary.md")
_RELEASE_TAG = re.compile(
    r"^v(?P<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))$"
)
# Trailing whitespace is matched as `[ \t]*`, never `\s*`: under re.MULTILINE `\s`
# also matches newlines, so `\s*$` swallows the blank line that separates a heading
# from its body and the rewritten section loses its separator.
_PROJECT_TABLE = re.compile(r"(?m)^\[project\][ \t]*$")
_NEXT_TABLE = re.compile(r"(?m)^\[")
_UNRELEASED_HEADING = re.compile(r"(?m)^## \[Unreleased\][ \t]*$")
_RELEASE_HEADING = re.compile(r"(?m)^## \[")

# House CHANGELOG format, verified against every dated section in CHANGELOG.md:
# `## [X.Y.Z] — YYYY-MM-DD` with an em dash (U+2014), and no link-reference
# definitions anywhere in the file.
_HEADING_SEPARATOR = "—"


class ReleasePrepError(Exception):
    """A precondition or mechanical edit failed; the run stops before the next step."""


@dataclass(frozen=True)
class StepResult:
    """One row of the closing summary table."""

    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class _CatalogPackage:
    family: str
    version: str
    version_key: tuple[int, int]
    role: str


@dataclass(frozen=True)
class PackageSelection:
    """One catalog-selected package version used by the review."""

    family: str
    version: str
    role: str


@dataclass(frozen=True)
class _PackageReference:
    family: str
    version: str
    kind: str


@dataclass(frozen=True)
class PackageReferenceMismatch:
    """One release-current package reference that needs owner review."""

    family: str
    path: str
    line: int
    observed: str
    expected: str
    kind: str


@dataclass(frozen=True)
class PackageReferenceReview:
    """A fully validated, immutable package-reference report plan."""

    selections: tuple[PackageSelection, ...]
    mismatches: tuple[PackageReferenceMismatch, ...]


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Version:
        match = _SEMVER.fullmatch(text)
        if match is None:
            raise ReleasePrepError(
                f"{text!r} is not a canonical SemVer release version (X.Y.Z, no pre-release or build metadata)"
            )
        return cls(int(match["major"]), int(match["minor"]), int(match["patch"]))

    @property
    def key(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


# ---- process helpers ---------------------------------------------------------


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run a fixed-argv command in the repository root, never raising on a non-zero exit.

    Callers decide what a non-zero exit means: for git preconditions it is fatal,
    for the verification chain it is a reported red row.
    """
    return subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _git(*args: str) -> str:
    result = _run(["git", *args])
    if result.returncode != 0:
        raise ReleasePrepError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


# ---- step 1: preconditions ---------------------------------------------------


def _current_version() -> Version:
    pyproject = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise ReleasePrepError("pyproject.toml has no [project] table")
    raw = cast("dict[str, object]", project).get("version")
    if not isinstance(raw, str):
        raise ReleasePrepError("pyproject.toml [project].version is missing or not a string")
    return Version.parse(raw)


def check_preconditions(target: Version) -> tuple[Version, StepResult]:
    status = _git("status", "--porcelain").strip()
    if status:
        raise ReleasePrepError(
            "the working tree is dirty; commit or stash before preparing a release:\n"
            + "\n".join(f"  {line}" for line in status.splitlines())
        )

    current = _current_version()
    if target.key <= current.key:
        raise ReleasePrepError(
            f"{target} does not advance beyond the current pyproject version {current}"
        )

    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != RELEASE_BRANCH:
        raise ReleasePrepError(
            f"release preparation must run on {RELEASE_BRANCH!r}; found {branch!r}. "
            "Switch only after the current worktree is clean."
        )
    notes = [f"tree clean; {current} -> {target}; branch {branch}"]
    return current, StepResult("1. preconditions", "ok", "; ".join(notes))


# ---- step 2: version bump ----------------------------------------------------


def _replace_project_version(text: str, current: Version, target: Version) -> str:
    """Rewrite `version` inside the `[project]` table only.

    Scoped to the table rather than applied file-wide because pyproject.toml carries
    unrelated version-shaped keys (`target-version`, `pythonVersion`, `minversion`)
    that a global substitution could reach in a future edit.
    """
    table_start = _PROJECT_TABLE.search(text)
    if table_start is None:
        raise ReleasePrepError("pyproject.toml has no [project] table header")
    body_start = table_start.end()
    next_table = _NEXT_TABLE.search(text, body_start + 1)
    body_end = next_table.start() if next_table else len(text)

    pattern = re.compile(r'(?m)^version[ \t]*=[ \t]*"' + re.escape(str(current)) + r'"[ \t]*$')
    body, count = pattern.subn(f'version = "{target}"', text[body_start:body_end], count=1)
    if count != 1:
        raise ReleasePrepError(
            f'pyproject.toml [project] does not contain a literal version = "{current}" line'
        )
    return text[:body_start] + body + text[body_end:]


def bump_version(current: Version, target: Version, *, dry_run: bool) -> StepResult:
    pyproject = REPO_ROOT / "pyproject.toml"
    original = pyproject.read_text(encoding="utf-8")
    updated = _replace_project_version(original, current, target)

    lock_command = ["uv", "lock"]
    if dry_run:
        print(f'[dry-run] pyproject.toml: version = "{current}"  ->  version = "{target}"')
        print(f"[dry-run] would run: {' '.join(lock_command)}")
        return StepResult("2. version bump", "planned", f'version = "{target}"; then uv lock')

    pyproject.write_text(updated, encoding="utf-8")
    # `uv lock` and not `uv sync`: the release commit must carry a regenerated
    # uv.lock, and re-locking is the whole requirement — syncing the local venv is a
    # side effect nobody downstream consumes.
    result = _run(lock_command)
    if result.returncode != 0:
        raise ReleasePrepError(f"uv lock failed:\n{result.stdout}{result.stderr}")
    return StepResult("2. version bump", "ok", f'pyproject version = "{target}"; uv.lock relocked')


# ---- step 3: version-reference sweep ----------------------------------------


def sweep_version_references(current: Version) -> StepResult:
    """Report, never rewrite, occurrences of the outgoing version string.

    versioning.md step 3 rewrites in-repo references only for a MAJOR, and even then
    with three review carve-outs, so an automated rewrite would be wrong in both
    directions. `packages check-release` (step 5) is the authoritative machine list —
    it classifies which references are release-current and which are deliberately
    historical; this sweep is the cheap human-readable superset printed first.
    """
    targets: list[Path] = [REPO_ROOT / "README.md"]
    targets.extend(sorted(REPO_ROOT.glob("standards/*/adopt.md")))
    # Family landing pages carry the current-payload links and version prose; all
    # four moved in the v5.16.0 release commit 8a2d1b9a.
    targets.extend(sorted(REPO_ROOT.glob("standards/*/README.md")))
    targets.extend(sorted(REPO_ROOT.glob("meta/*.md")))
    # Release-version pins the battery enforces: the activation constants and
    # the synthetic-repository catalog golden both embed the release literal
    # and fail the ordinary lane when left behind (found at v5.13.0 prep).
    targets.append(REPO_ROOT / "tests/package_contract/test_current_catalog_activation.py")
    targets.append(REPO_ROOT / "tests/fixtures/package_contract/valid/full/expected/catalog.toml")
    # FR-020: the MCP guide must state the exact installed package version.
    targets.append(REPO_ROOT / "docs/mcp-server.md")
    # versioning.md step 6: the upgrade runbook's install example names one exact
    # release every cut, not only a MAJOR one.
    targets.append(REPO_ROOT / "UPGRADING.md")
    # Consumer-facing guides in the same class as the MCP guide: each quotes an
    # install pin or a `--version` expectation a reader copies verbatim.
    targets.append(REPO_ROOT / "docs/adoption-prompt-blank.md")
    targets.append(REPO_ROOT / "docs/adoption-prompt-full.md")
    targets.append(REPO_ROOT / "docs/usage.md")
    # Reported, never rewritten: a roadmap section named for the outgoing release
    # is the signal that its planned/shipped state needs the judgment edit.
    targets.append(REPO_ROOT / "ROADMAP.md")
    # A release that re-renders a digest-pinned managed workflow amends this
    # ledger per issue; a hit here flags the amendment rather than a stale string.
    targets.append(REPO_ROOT / "tests/issue_regressions/ledger.toml")

    needle = str(current)
    hits: list[str] = []
    for path in targets:
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if needle in line:
                hits.append(f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}")

    print(f"\n-- version references to {current} (review; nothing was rewritten) --")
    if hits:
        for hit in hits:
            print(f"  {hit}")
    else:
        print("  none")
    return StepResult(
        "3. reference sweep",
        "ok",
        f"{len(hits)} occurrence(s) of {current} reported for review",
    )


# ---- step 3a: allow-listed pin rewrites --------------------------------------
#
# The sweep above deliberately rewrites nothing, which left the release runbook's R3 as a
# hand-written batch of line-addressed `sed -i` commands whose addresses had to be
# re-derived on every train (#227 E3 item 5). The addresses are the hazard: a doc leg that
# landed after the runbook was written shifts them, and a mis-addressed `sed` edits the
# wrong line silently.
#
# `--apply-pins` replaces that batch with an allow-list. Nothing is rewritten unless a
# (path, matcher) pair below names it, so every judgment site the sweep exists to surface
# — ROADMAP.md sections, UPGRADING.md history headings, `_BASELINE_REF`, package prose
# outside the two contract lines — stays reported and untouched by construction. Adding a
# matcher is the deliberate act of declaring a site mechanical.
#
# The second guard is the value: a match is rewritten only when the version it carries is
# exactly the outgoing one. A site already at the target, or naming some third version, is
# left alone rather than "corrected".

_VERSION_TEXT = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"

# Every matcher captures the version in a `version` group; only that group's span is
# rewritten, so surrounding prose is never touched. Each one is anchored on text that only
# ever accompanies a release pin, never on the bare version string.
_PIN_MATCHERS: dict[str, re.Pattern[str]] = {
    "install-tag": re.compile(rf"project-standards@v(?P<version>{_VERSION_TEXT})"),
    "wheel-artifact": re.compile(
        rf"project_standards-(?P<version>{_VERSION_TEXT})-py3-none-any\.whl"
    ),
    "version-report": re.compile(rf"project-standards (?P<version>{_VERSION_TEXT})"),
    "product-prose": re.compile(rf"Project Standards (?P<version>{_VERSION_TEXT})"),
    "upgrade-target": re.compile(rf"release you intend to pin\. For (?P<version>{_VERSION_TEXT}):"),
    "precommit-rev": re.compile(rf"rev: v(?P<version>{_VERSION_TEXT})"),
    "release-constant": re.compile(rf'_RELEASE_VERSION = "(?P<version>{_VERSION_TEXT})"'),
}

# The allow-list itself: path -> the matchers admitted in that file. A path missing from
# the tree is a hard error, not a skip — a renamed pin site must be re-declared here rather
# than silently dropping out of the release.
_RELEASE_PIN_SITES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "README.md",
        ("install-tag", "wheel-artifact", "version-report", "product-prose", "precommit-rev"),
    ),
    ("UPGRADING.md", ("install-tag", "version-report", "upgrade-target")),
    ("docs/mcp-server.md", ("install-tag", "wheel-artifact", "version-report")),
    ("tests/package_contract/test_current_catalog_activation.py", ("release-constant",)),
)

# meta/versioning.md pins *package* releases, not the tool release, which is why the
# release-version sweep never reported it and why markdown-tooling's line was left at 1.15
# through the whole v5.28.0 train. The expected value comes from the candidate catalog's
# own selection, so this pin follows the cut rather than a transcribed number.
_PACKAGE_PIN_PATH = "meta/versioning.md"
_PACKAGE_PIN_MATCHER = re.compile(
    r"The \*\*(?P<family>[A-Z][A-Za-z]*(?: [A-Z][A-Za-z]*)*) contract version\*\*"
    rf".*?independently from package release `(?P<version>{_PACKAGE_VERSION_TEXT})`"
)


@dataclass(frozen=True)
class PinEdit:
    """One allow-listed rewrite, reported whether or not it is written."""

    path: str
    line: int
    matcher: str
    observed: str
    expected: str


@dataclass(frozen=True)
class PinPlan:
    """A validated, not-yet-written batch of pin rewrites plus its unified diff."""

    edits: tuple[PinEdit, ...]
    updates: tuple[tuple[str, str], ...]
    diff: str


def _rewrite_line(
    line: str,
    matchers: Sequence[tuple[str, re.Pattern[str]]],
    expected_for: Callable[[re.Match[str]], str | None],
) -> tuple[str, list[tuple[str, str, str]]]:
    """Return the rewritten line and one record per replaced match.

    Spans are replaced right-to-left so an earlier replacement cannot invalidate a later
    match's offsets when two pins share a line.
    """
    replacements: list[tuple[int, int, str, str, str]] = []
    for name, pattern in matchers:
        for match in pattern.finditer(line):
            expected = expected_for(match)
            observed = match.group("version")
            if expected is None or observed == expected:
                continue
            start, end = match.span("version")
            replacements.append((start, end, name, observed, expected))

    records: list[tuple[str, str, str]] = []
    for start, end, name, observed, expected in sorted(replacements, reverse=True):
        line = line[:start] + expected + line[end:]
        records.append((name, observed, expected))
    records.reverse()
    return line, records


def plan_pins(current: Version, target: Version) -> PinPlan:
    """Compute every allow-listed pin rewrite, reading files but writing none.

    The whole batch is planned before anything is written, so a missing allow-listed path
    or an unreadable file aborts with the tree untouched instead of half-rewritten.
    """
    selections = {selection.family: selection.version for selection in _catalog_selections(target)}

    _Expected = Callable[[re.Match[str]], str | None]
    sites: list[tuple[str, Sequence[tuple[str, re.Pattern[str]]], _Expected]] = []
    for path, matcher_names in _RELEASE_PIN_SITES:
        matchers = [(name, _PIN_MATCHERS[name]) for name in matcher_names]
        # Only the outgoing release moves. Anything else at a pin site is either already
        # done or a number this release does not own.
        sites.append(
            (
                path,
                matchers,
                lambda match: str(target) if match["version"] == str(current) else None,
            )
        )

    def _package_expected(match: re.Match[str]) -> str | None:
        family = match["family"].casefold().replace(" ", "-")
        return selections.get(family)

    sites.append(
        (_PACKAGE_PIN_PATH, [("package-contract-prose", _PACKAGE_PIN_MATCHER)], _package_expected)
    )

    edits: list[PinEdit] = []
    updates: list[tuple[str, str]] = []
    diff_chunks: list[str] = []
    for path, matchers, expected_for in sites:
        absolute = REPO_ROOT / path
        if not absolute.is_file():
            raise ReleasePrepError(
                f"allow-listed pin site {path} does not exist; update _RELEASE_PIN_SITES "
                "before preparing the release"
            )
        try:
            original = absolute.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ReleasePrepError(f"cannot read pin site {path}: {error}") from error

        lines = original.splitlines(keepends=True)
        rewritten: list[str] = []
        changed = False
        for number, line in enumerate(lines, start=1):
            new_line, records = _rewrite_line(line, matchers, expected_for)
            rewritten.append(new_line)
            for matcher, observed, expected in records:
                edits.append(PinEdit(path, number, matcher, observed, expected))
                changed = True
        if not changed:
            continue
        updated = "".join(rewritten)
        updates.append((path, updated))
        diff_chunks.extend(
            difflib.unified_diff(
                lines,
                rewritten,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
    return PinPlan(tuple(edits), tuple(updates), "".join(diff_chunks))


def apply_pins(plan: PinPlan, *, dry_run: bool) -> StepResult:
    """Print the pin diff and, unless this is a dry run, write it."""
    label = "3a. pin rewrites"
    print("\n-- allow-listed pin rewrites --")
    if not plan.edits:
        print("  none: every allow-listed pin already carries the target version")
        return StepResult(label, "ok", "no pin site needed rewriting")

    for edit in plan.edits:
        print(
            f"  {edit.path}:{edit.line}: matcher={edit.matcher} {edit.observed} -> {edit.expected}"
        )
    print()
    sys.stdout.write(plan.diff)

    if dry_run:
        return StepResult(
            label,
            "planned",
            f"{len(plan.edits)} pin(s) in {len(plan.updates)} file(s); nothing written",
        )
    for path, text in plan.updates:
        (REPO_ROOT / path).write_text(text, encoding="utf-8")
    return StepResult(
        label, "ok", f"{len(plan.edits)} pin(s) rewritten in {len(plan.updates)} file(s)"
    )


def run_apply_pins(target: Version, *, dry_run: bool) -> int:
    """Standalone `--apply-pins` mode: rewrite the allow-listed pins and nothing else.

    Runs as its own step rather than inside the release run because the runbook does: the
    version bump (step 2) has to land and be reviewed first, and by then the tree is dirty
    and pyproject.toml already reads the target, so neither `check_preconditions` nor
    `_current_version` can supply the outgoing version. The highest release tag below the
    target is that version, and it reads the same before and after the bump.

    The RELEASE_BRANCH guard applies to the write, not to the dry run: writing pins is a
    release mutation and belongs on the release branch like every other, while a dry run
    produces only a diff on stdout and is exactly what a release engineer wants to read
    from the working branch before the train starts.
    """
    baseline = _previous_release_tag(target)
    current = Version.parse(baseline[1:])
    if not dry_run:
        branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
        if branch != RELEASE_BRANCH:
            raise ReleasePrepError(
                f"pin rewrites must be applied on {RELEASE_BRANCH!r}; found {branch!r}. "
                "Use --dry-run to review the diff from another branch."
            )
    plan = plan_pins(current, target)
    result = apply_pins(plan, dry_run=dry_run)
    print(f"\n== pin rewrite summary ==\n  {result.name}  {result.status}  {result.detail}")
    print(f"  outgoing version taken from the previous release tag: {baseline}")
    return 0


def _parse_package_version(text: str, *, context: str) -> tuple[int, int]:
    match = _PACKAGE_VERSION.fullmatch(text)
    if match is None:
        raise ReleasePrepError(f"{context} has non-canonical package version {text!r}")
    return (int(match["major"]), int(match["minor"]))


def _catalog_selections(target: Version) -> tuple[PackageSelection, ...]:
    path = REPO_ROOT / "catalogs" / f"{target.major}.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ReleasePrepError(
            f"cannot read candidate catalog {path.relative_to(REPO_ROOT)}: {error}"
        ) from error

    catalog_major = data.get("catalog_major")
    if type(catalog_major) is not int or catalog_major != target.major:
        raise ReleasePrepError(
            f"{path.relative_to(REPO_ROOT)} catalog_major must equal target major {target.major}"
        )
    raw_packages = data.get("packages")
    if not isinstance(raw_packages, list):
        raise ReleasePrepError(f"{path.relative_to(REPO_ROOT)} packages must be an array of tables")

    by_family: dict[str, list[_CatalogPackage]] = {}
    identities: set[tuple[str, str]] = set()
    for index, raw_package in enumerate(raw_packages, start=1):
        if not isinstance(raw_package, dict):
            raise ReleasePrepError(f"candidate catalog package row {index} must be a table")
        package = cast("dict[str, object]", raw_package)
        family = package.get("id")
        version = package.get("version")
        role = package.get("role")
        if not isinstance(family, str) or _FAMILY_ID.fullmatch(family) is None:
            raise ReleasePrepError(f"candidate catalog package row {index} has invalid id")
        if not isinstance(version, str):
            raise ReleasePrepError(f"candidate catalog package row {index} has invalid version")
        version_key = _parse_package_version(version, context=f"package row {index}")
        if not isinstance(role, str) or role not in _CATALOG_ROLES:
            raise ReleasePrepError(f"candidate catalog package row {index} has invalid role")
        identity = (family, version)
        if identity in identities:
            raise ReleasePrepError(
                f"candidate catalog duplicates package/version {family}@{version}"
            )
        identities.add(identity)
        by_family.setdefault(family, []).append(_CatalogPackage(family, version, version_key, role))

    selections: list[PackageSelection] = []
    for family, packages in sorted(by_family.items()):
        selected_roles = {package.role for package in packages if package.role in _SELECTED_ROLES}
        defaults = [package for package in packages if package.role == "default"]
        if len(defaults) > 1 or len(selected_roles) > 1:
            raise ReleasePrepError(f"candidate catalog has ambiguous selection for {family}")
        selected: _CatalogPackage | None = None
        if defaults:
            selected = defaults[0]
        elif selected_roles:
            role = next(iter(selected_roles))
            selected = max(
                (package for package in packages if package.role == role),
                key=lambda package: package.version_key,
            )
        if selected is not None:
            selections.append(PackageSelection(family, selected.version, selected.role))
    return tuple(selections)


def _marker_before(lines: list[str], index: int) -> re.Match[str] | None:
    previous = index - 1
    while previous >= 0 and not lines[previous].strip():
        previous -= 1
    if previous < 0:
        return None
    return _REFERENCE_MARKER.fullmatch(lines[previous].strip())


def _historical_package_reference(lines: list[str], index: int, family: str) -> bool:
    marker = _marker_before(lines, index)
    if marker is not None and marker.group("family") == family:
        return True
    for line in reversed(lines[: index + 1]):
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading is not None:
            if heading.group(2).strip().casefold() in _HISTORICAL_SECTIONS:
                return True
            break
    folded = lines[index].casefold()
    return any(phrase in folded for phrase in _NATURAL_HISTORY_PHRASES)


def _package_references(
    line: str,
    *,
    shallow_family: str,
    selections: dict[str, PackageSelection],
) -> tuple[_PackageReference, ...]:
    references: list[_PackageReference] = []
    for expression, kind in (
        (_EXACT_SELECTOR, "exact-selector"),
        (_FULL_VERSION_PATH, "versioned-link"),
        (_ENABLE_COMMAND, "enable-command"),
        (_FAMILY_VERSION, "family-prose"),
    ):
        for match in expression.finditer(line):
            family = match.group("family").casefold()
            if family in selections:
                references.append(_PackageReference(family, match.group("version"), kind))

    for expression, kind in (
        (_SHALLOW_VERSION_PATH, "versioned-link"),
        (_BARE_PACKAGE_VERSION, "family-prose"),
    ):
        for match in expression.finditer(line):
            references.append(_PackageReference(shallow_family, match.group("version"), kind))

    folded = line.casefold()
    for family in selections:
        display_name = family.replace("-", " ")
        for match in re.finditer(
            rf"(?<![a-z0-9_-]){re.escape(display_name)}\s+`?"
            rf"(?P<version>{_PACKAGE_VERSION_TEXT})`?(?![0-9]|\.[0-9])",
            folded,
        ):
            references.append(_PackageReference(family, match.group("version"), "named-prose"))

    unique: dict[tuple[str, str, str], _PackageReference] = {}
    for reference in references:
        unique[(reference.family, reference.version, reference.kind)] = reference
    return tuple(unique.values())


def plan_package_version_references(target: Version) -> PackageReferenceReview:
    """Validate and compute the package-reference review without writing files.

    Catalog selection and every document read finish before release mutation, so a
    malformed candidate or unsafe root document cannot leave a partial release tree.
    """
    selections = _catalog_selections(target)
    by_family = {selection.family: selection for selection in selections}
    mismatches: list[PackageReferenceMismatch] = []
    for selection in selections:
        family_root = REPO_ROOT / "standards" / selection.family
        for name in _PACKAGE_REFERENCE_DOCUMENTS:
            path = family_root / name
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_symlink() or not path.is_file():
                raise ReleasePrepError(
                    f"package reference surface is not a regular file: "
                    f"{path.relative_to(REPO_ROOT)}"
                )
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as error:
                raise ReleasePrepError(
                    f"cannot read package reference surface {path.relative_to(REPO_ROOT)}: {error}"
                ) from error
            relative = path.relative_to(REPO_ROOT).as_posix()
            for index, line in enumerate(lines):
                for reference in _package_references(
                    line,
                    shallow_family=selection.family,
                    selections=by_family,
                ):
                    expected = by_family[reference.family].version
                    if reference.version == expected or _historical_package_reference(
                        lines, index, reference.family
                    ):
                        continue
                    mismatches.append(
                        PackageReferenceMismatch(
                            reference.family,
                            relative,
                            index + 1,
                            reference.version,
                            expected,
                            reference.kind,
                        )
                    )
    mismatches.sort(
        key=lambda mismatch: (
            mismatch.family,
            mismatch.path,
            mismatch.line,
            mismatch.observed,
            mismatch.kind,
        )
    )
    return PackageReferenceReview(selections, tuple(mismatches))


def report_package_version_references(review: PackageReferenceReview) -> StepResult:
    """Print the prepared package-reference review without reading or writing files."""
    print("\n-- package-version references (review; nothing was rewritten) --")
    if review.mismatches:
        for mismatch in review.mismatches:
            print(
                f"  {mismatch.path}:{mismatch.line}: family={mismatch.family} "
                f"observed={mismatch.observed} expected={mismatch.expected} "
                f"reason=current {mismatch.kind}"
            )
    else:
        print("  none")
    return StepResult(
        "3b. package reference review",
        "ok",
        f"{len(review.mismatches)} package-version mismatch occurrence(s) reported for review",
    )


# ---- step 4: CHANGELOG conversion --------------------------------------------


@dataclass(frozen=True)
class ChangelogPlan:
    """A validated, not-yet-written CHANGELOG conversion."""

    text: str
    heading: str
    summary: str


def plan_changelog(target: Version, *, today: str) -> ChangelogPlan:
    """Validate and compute the conversion without touching the file.

    Planned before step 2 runs, so a malformed CHANGELOG aborts the run while the
    tree is still pristine rather than after pyproject.toml and uv.lock are bumped.
    """
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    heading = f"## [{target}] {_HEADING_SEPARATOR} {today}"
    if re.search(r"(?m)^## \[" + re.escape(str(target)) + r"\]", text):
        raise ReleasePrepError(f"CHANGELOG.md already contains a [{target}] section")

    matches = list(_UNRELEASED_HEADING.finditer(text))
    if not matches:
        raise ReleasePrepError(
            "CHANGELOG.md has no `## [Unreleased]` section to convert; record the "
            "release entries under one before preparing the release"
        )
    if len(matches) > 1:
        raise ReleasePrepError("CHANGELOG.md contains more than one `## [Unreleased]` heading")
    match = matches[0]

    next_section = _RELEASE_HEADING.search(text, match.end())
    body = text[match.end() : next_section.start() if next_section else len(text)]
    if not body.strip():
        raise ReleasePrepError(
            "the `## [Unreleased]` section is empty; there is nothing to release"
        )

    # Keep-a-Changelog scaffold: the retitled section keeps its authored body, and a
    # fresh empty `## [Unreleased]` takes its place at the top of the log.
    updated = f"{text[: match.start()]}## [Unreleased]\n\n{heading}{text[match.end() :]}"
    return ChangelogPlan(updated, heading, f"[Unreleased] -> [{target}] {today}")


def apply_changelog(plan: ChangelogPlan, *, dry_run: bool) -> StepResult:
    if dry_run:
        print("\n[dry-run] CHANGELOG.md: `## [Unreleased]` becomes")
        print("[dry-run]   ## [Unreleased]")
        print("[dry-run]")
        print(f"[dry-run]   {plan.heading}")
        return StepResult("4. changelog", "planned", plan.summary)

    (REPO_ROOT / "CHANGELOG.md").write_text(plan.text, encoding="utf-8")
    return StepResult("4. changelog", "ok", plan.summary)


# ---- step 5: wiring verification chain ---------------------------------------


def _previous_release_tag(target: Version) -> str:
    """Highest `vX.Y.Z` tag strictly below the target — the check-release baseline."""
    candidates: list[tuple[tuple[int, int, int], str]] = []
    for line in _git("tag", "--list", "v*").splitlines():
        tag = line.strip()
        match = _RELEASE_TAG.fullmatch(tag)
        if match is None:
            continue
        version = Version.parse(match["version"])
        if version.key < target.key:
            candidates.append((version.key, tag))
    if not candidates:
        raise ReleasePrepError(f"no released vX.Y.Z tag below {target} to use as a baseline")
    return max(candidates)[1]


def _runtime_version() -> str | None:
    result = _run(["uv", "run", "project-standards", "--version"])
    if result.returncode != 0:
        return None
    parts = result.stdout.split()
    return parts[-1] if parts else None


def verify_chain(target: Version, baseline: str, *, dry_run: bool) -> list[StepResult]:
    commands: list[tuple[str, list[str]]] = [
        ("validate-packages", ["standards", "validate-packages", "--root", ".", "--json"]),
        (
            "validate-graph",
            ["standards", "validate-graph", "--root", ".", "--require-all-manifests", "--json"],
        ),
        (
            "generate-package-schemas",
            ["standards", "generate-package-schemas", "--root", ".", "--check", "--json"],
        ),
        (
            "sync-payload-projection",
            ["standards", "sync-payload-projection", "--root", ".", "--check", "--json"],
        ),
        (
            "render-consumer-catalog",
            [
                "standards",
                "render-consumer-catalog",
                "--root",
                ".",
                "--catalog-major",
                str(target.major),
                "--output",
                CONSUMER_CATALOG.as_posix(),
                "--check",
                "--json",
            ],
        ),
    ]
    release_command = ["packages", "check-release", "--root", ".", "--baseline", baseline, "--json"]

    if not dry_run:
        # `check-release` and `render-consumer-catalog` read the *installed*
        # distribution version, not pyproject.toml. A stale extracted candidate wheel
        # first on PYTHONPATH (the repository's dogfood runtime) therefore shadows the
        # bump and makes check-release report a spurious PC-RELEASE-LEVEL. Say so
        # rather than letting the owner debug the wrong finding.
        runtime = _runtime_version()
        if runtime is not None and runtime != str(target):
            print(
                f"warning: `project-standards --version` reports {runtime}, not {target} — "
                "rebuild the candidate wheel runtime (uv build --wheel; extract to "
                "build/wheel-runtime) or drop it from PYTHONPATH, or check-release "
                "will classify against the wrong version",
                file=sys.stderr,
            )

    results: list[StepResult] = []
    print("\n-- wiring verification chain --")
    for name, argv in [*commands, ("check-release", release_command)]:
        full = ["uv", "run", "project-standards", *argv]
        printable = " ".join(full)
        if dry_run and name == "check-release":
            # The only chain member whose answer depends on the bump having landed;
            # running it pre-bump would report PC-RELEASE-LEVEL and mean nothing.
            print(f"\n$ {printable}")
            print("[dry-run] skipped: requires the applied version bump")
            results.append(StepResult("5. check-release", "skipped", "needs the applied bump"))
            continue
        print(f"\n$ {printable}")
        result = _run(full)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        results.append(
            StepResult(
                f"5. {name}",
                "ok" if result.returncode == 0 else "FAILED",
                f"exit {result.returncode}",
            )
        )
    return results


# ---- step 6: summary ---------------------------------------------------------


def print_summary(
    results: Sequence[StepResult], target: Version, current: Version, baseline: str
) -> None:
    candidate_wheel = Path("build/release-wheel") / f"project_standards-{target}-py3-none-any.whl"
    width = max(len(row.name) for row in results)
    print("\n== release prep summary ==")
    for row in results:
        print(f"  {row.name.ljust(width)}  {row.status.ljust(8)}  {row.detail}")

    print("\n-- follow-ups the chain will demand before tagging --")
    print(
        f"  Update the release-current references check-release listed (they still name {current})."
    )
    print("  The mechanical subset of them is an allow-listed rewrite; review the diff first:")
    print(f"      uv run python scripts/release_prep.py {target} --apply-pins --dry-run")
    print(f"      uv run python scripts/release_prep.py {target} --apply-pins")
    print("  Reconcile the dogfooded control plane so the catalog projection matches:")
    print("      uv run project-standards reconcile --apply")
    if target.major > current.major:
        print("  MAJOR only, per meta/versioning.md step 3 and step 6 (judgment, not automated):")
        print(f'      bump every `default: "v{current.major}"` standards-ref in .github/workflows/')
        print("      bump the @vN / standards-ref examples in README.md and standards/*/adopt.md")
        print(f'      rewrite UPGRADING.md as "Upgrading from v{current.major} to v{target.major}"')

    print("\n-- remaining manual steps (meta/versioning.md, owner only) --")
    print("  # step 0 — review and commit the prepared release on main before building it")
    print("  git diff --check")
    print("  git status --short")
    print(f'  PROJECT_STANDARDS_RELEASE_COMMIT=1 git commit -am "release: prepare v{target}"')
    print("  # mandatory pre-tag verification — run on that release commit before either tag")
    print("  uv sync --all-groups --locked")
    print("  npm ci")
    print("  uv run project-standards standards sync-payload-projection --root . --check --json")
    print("  uv build --clear --wheel --out-dir build/release-wheel")
    print("  rm -rf -- build/wheel-runtime")
    print(f"  uv run python -m zipfile -e {candidate_wheel} build/wheel-runtime")
    print('  export PYTHONPATH="$PWD/build/wheel-runtime"')
    print("  scripts/verify.sh --full")
    print("  uv run project-standards validate")
    print("  uv run project-standards standards validate-packages --root . --json")
    print(
        "  uv run project-standards standards validate-graph --root . --require-all-manifests --json"
    )
    print("  uv run project-standards standards generate-package-schemas --root . --check --json")
    print("  uv run project-standards standards render-catalog --root . --check")
    print(
        f"  uv run project-standards packages check-release --root . --baseline {baseline} --json"
    )
    print("  # step 1 — annotated, GPG-signed, immutable full-version tag")
    print(f'  git tag -as v{target} -m "project-standards v{target}"')
    print(f"  git push origin v{target}")
    print("  # step 2 — advance the moving major tag by delete-and-re-push, never --force")
    print(
        f'  git tag -fs v{target.major} -m "project-standards v{target.major} (-> v{target})" <release-commit>'
    )
    print(f"  git push origin :refs/tags/v{target.major}")
    print(f"  git push origin v{target.major}")
    print("  # publication")
    print(
        f'  gh release create v{target} --title "project-standards v{target}" --notes-file <notes>'
    )
    print(f"\n  check-release baseline used this run: {baseline}")


# ---- entry point -------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release_prep.py",
        description="Perform the mechanical release-preparation steps from meta/versioning.md.",
    )
    parser.add_argument("version", help="target release version, canonical SemVer X.Y.Z")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print every planned edit and mutation without performing it",
    )
    parser.add_argument(
        "--apply-pins",
        action="store_true",
        help=(
            "rewrite only the allow-listed release pins (runbook step R3) and exit; "
            "combine with --dry-run to print the diff without writing"
        ),
    )
    args = parser.parse_args(argv)
    dry_run = cast("bool", args.dry_run)
    apply_pins_mode = cast("bool", args.apply_pins)

    try:
        target = Version.parse(cast("str", args.version))
        if apply_pins_mode:
            return run_apply_pins(target, dry_run=dry_run)
        current, precondition = check_preconditions(target)
        # Every validation that can reject the run happens before the first
        # write — including the check-release baseline lookup, whose "no prior
        # release tag" failure is a precondition, not a step outcome.
        changelog = plan_changelog(target, today=date.today().isoformat())
        baseline = _previous_release_tag(target)
        package_references = plan_package_version_references(target)
        results = [precondition]
        results.append(bump_version(current, target, dry_run=dry_run))
        results.append(sweep_version_references(current))
        results.append(report_package_version_references(package_references))
        results.append(apply_changelog(changelog, dry_run=dry_run))
        results.extend(verify_chain(target, baseline, dry_run=dry_run))
    except ReleasePrepError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print_summary(results, target, current, baseline)
    return 1 if any(row.status == "FAILED" for row in results) else 0


if __name__ == "__main__":
    sys.exit(main())
