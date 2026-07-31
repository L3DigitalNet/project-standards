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
    `blob/vN` permalinks, a standard's first-shipping examples), so this script
    *reports* stale references and rewrites none.
  * step 6 (UPGRADING.md prose, MAJOR only) — authored migration prose.

The script edits files and runs read-only verification. It never commits, tags,
pushes, or touches a remote.

Usage (from the repository root):

    uv run python scripts/release_prep.py X.Y.Z [--dry-run]

`--dry-run` prints every planned edit and mutation command without performing any
of them; the read-only `--check` verification commands still run so the dry run
reports the true pre-bump state of the chain.

Exit codes: 0 success, 1 a step failed, 2 bad invocation.

Stdlib only, matching scripts/check.py and scripts/plan.py: these helpers must run
before the project environment is guaranteed to be in any particular state.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from collections.abc import Sequence
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

# The release branch versioning.md expects work to be staged on. Preparing
# elsewhere is legitimate (the owner sometimes preps on a worktree branch), so this
# is a warning, never a block.
EXPECTED_BRANCH = "testing"

_SEMVER = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\.(?P<patch>0|[1-9][0-9]*)$"
)
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

    notes = [f"tree clean; {current} -> {target}"]
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != EXPECTED_BRANCH:
        # Warn only: versioning.md step 0 requires the release to *land* on main, and
        # the owner preps on whatever branch the work lives on.
        print(
            f"warning: on branch {branch!r}, not {EXPECTED_BRANCH!r} — continuing", file=sys.stderr
        )
        notes.append(f"branch {branch} (expected {EXPECTED_BRANCH})")
    else:
        notes.append(f"branch {branch}")
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
    targets.extend(sorted(REPO_ROOT.glob("meta/*.md")))

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


def verify_chain(target: Version, *, dry_run: bool) -> tuple[list[StepResult], str]:
    baseline = _previous_release_tag(target)
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
    return results, baseline


# ---- step 6: summary ---------------------------------------------------------


def print_summary(
    results: Sequence[StepResult], target: Version, current: Version, baseline: str
) -> None:
    width = max(len(row.name) for row in results)
    print("\n== release prep summary ==")
    for row in results:
        print(f"  {row.name.ljust(width)}  {row.status.ljust(8)}  {row.detail}")

    print("\n-- follow-ups the chain will demand before tagging --")
    print(
        f"  Update the release-current references check-release listed (they still name {current})."
    )
    print("  Reconcile the dogfooded control plane so the catalog projection matches:")
    print("      uv run project-standards reconcile --apply")
    if target.major > current.major:
        print("  MAJOR only, per meta/versioning.md step 3 and step 6 (judgment, not automated):")
        print(f'      bump every `default: "v{current.major}"` standards-ref in .github/workflows/')
        print("      bump the @vN / standards-ref examples in README.md and standards/*/adopt.md")
        print(f'      rewrite UPGRADING.md as "Upgrading from v{current.major} to v{target.major}"')

    print("\n-- remaining manual steps (meta/versioning.md, owner only) --")
    print("  # step 0 — the release commit and both tags MUST live on main")
    print("  git switch main && git merge --ff-only <release-branch>")
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
    args = parser.parse_args(argv)
    dry_run = cast("bool", args.dry_run)

    try:
        target = Version.parse(cast("str", args.version))
        current, precondition = check_preconditions(target)
        # Every validation that can reject the run happens before the first write.
        changelog = plan_changelog(target, today=date.today().isoformat())
        results = [precondition]
        results.append(bump_version(current, target, dry_run=dry_run))
        results.append(sweep_version_references(current))
        results.append(apply_changelog(changelog, dry_run=dry_run))
    except ReleasePrepError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    try:
        chain, baseline = verify_chain(target, dry_run=dry_run)
    except ReleasePrepError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    results.extend(chain)

    print_summary(results, target, current, baseline)
    return 1 if any(row.status == "FAILED" for row in results) else 0


if __name__ == "__main__":
    sys.exit(main())
