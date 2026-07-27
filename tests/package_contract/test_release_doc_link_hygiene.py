"""Guard against issue #53: pinned release payloads must not link mutable refs.

A versioned payload under `standards/<family>/versions/<version>/` is byte-frozen
once released — GitHub's tag/release browsing lets a consumer stay on the exact
ref they installed, but only if the document itself links repo-relatively. A
hardcoded `https://github.com/L3DigitalNet/project-standards/blob/(main|v5)/...`
link always resolves against the CURRENT tip of that branch, so a reader on an
old pinned release is silently handed documentation, CLI behavior, or a skill
file that has moved on since the release was cut. That is exactly issue #53:
markdown-frontmatter 1.2-1.5's `adopt.md` and installed `SKILL.md` hardcoded
`blob/main`/`blob/v5` links instead of repo-relative ones.

Scoping rationale (why this is an explicit allowlist, not "newest version only"):

Released payload bytes are immutable at any release level (mutating them is
`PC-RELEASE-PAYLOAD-MUTATED`-forbidden; the only correction is a NEW payload
version — see `standards/markdown-frontmatter/versions/1.6`, the fix for #53).
A blanket "no version anywhere may contain this pattern" assertion therefore
cannot pass at HEAD: `standards/adr/versions/{1.1,1.2}`,
`standards/cli-documentation/versions/{1.1..1.4}`, and
`standards/project-spec/versions/{1.1..1.4}` independently ship the same
mutable-ref pattern and are unrelated to #53's fix. A narrower "only the
CURRENT/NEWEST version of each family must be clean" rule *also* fails at HEAD
for those three families, because their newest version IS the still-unfixed
offender (no corrective version has been authored for them yet). Neither rule
is available without either fixing unrelated families (scope creep well beyond
#53) or silently ignoring a whole family's newest version forever.

The chosen rule instead scans every file in every version of every family and
fails on any match, *except* two grandfathered exclusions:

1. A fixed, explicit, path-level allowlist of the specific already-released
   files enumerated below — added exactly once, for the state that already
   existed before this test was written. It must never grow; a corrective new
   version (as this fix did for markdown-frontmatter) is the only legitimate
   way to make a family disappear from it.
2. Any resource a version's own `payload.toml` declares with
   `role = "legacy-reference"` — a deliberate byte-for-byte historical snapshot
   of a pre-V5 artifact kept for `[[legacy_signatures]].known_content_digests`
   whole-file recognition. Its content is frozen historical fact, not authored
   prose, and "fixing" its links would break legacy-consumer recognition instead
   of fixing anything.

This is stronger than "only check the file(s) issue #53 touched" or "only check
the newest version": a *new* version directory in *any* family, not on the
allowlist, is checked unconditionally, so it fails immediately if it reintroduces
the pattern. `test_mutable_ref_scan_would_have_caught_issue_53` proves the
detector is sound against the actual historical bytes that shipped the bug.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_STANDARDS_ROOT = _ROOT / "standards"

_MUTABLE_REF_PATTERN = re.compile(
    r"github\.com/L3DigitalNet/project-standards/(?:blob|tree)/(?:main|v5)/"
)

# Grandfathered released files that already contained the mutable-ref pattern
# before this test existed (issue #53 triage sweep, 2026-07-27). Every entry is
# `family/versions/version/relative-path`. This set may only shrink — when a
# family gets its own corrective new version (as markdown-frontmatter 1.6 does
# here), remove that family's entries; never add a new one for a fresh bug.
_RELEASED_MUTABLE_REF_ALLOWLIST = frozenset(
    {
        "adr/versions/1.1/README.md",
        "adr/versions/1.2/README.md",
        "cli-documentation/versions/1.1/README.md",
        "cli-documentation/versions/1.1/examples/usage.example.md",
        "cli-documentation/versions/1.1/resources/research-notes.md",
        "cli-documentation/versions/1.2/README.md",
        "cli-documentation/versions/1.2/examples/usage.example.md",
        "cli-documentation/versions/1.2/resources/research-notes.md",
        "cli-documentation/versions/1.3/README.md",
        "cli-documentation/versions/1.3/examples/usage.example.md",
        "cli-documentation/versions/1.3/resources/research-notes.md",
        "cli-documentation/versions/1.4/README.md",
        "cli-documentation/versions/1.4/examples/usage.example.md",
        "cli-documentation/versions/1.4/resources/research-notes.md",
        "markdown-frontmatter/versions/1.2/README.md",
        "markdown-frontmatter/versions/1.2/adopt.md",
        "markdown-frontmatter/versions/1.2/artifacts/agent-summary.md",
        "markdown-frontmatter/versions/1.2/skills/markdown-frontmatter/SKILL.md",
        "markdown-frontmatter/versions/1.2/structure.md",
        "markdown-frontmatter/versions/1.3/README.md",
        "markdown-frontmatter/versions/1.3/adopt.md",
        "markdown-frontmatter/versions/1.3/artifacts/agent-summary.md",
        "markdown-frontmatter/versions/1.3/skills/markdown-frontmatter/SKILL.md",
        "markdown-frontmatter/versions/1.3/structure.md",
        "markdown-frontmatter/versions/1.4/README.md",
        "markdown-frontmatter/versions/1.4/adopt.md",
        "markdown-frontmatter/versions/1.4/artifacts/agent-summary.md",
        "markdown-frontmatter/versions/1.4/skills/markdown-frontmatter/SKILL.md",
        "markdown-frontmatter/versions/1.4/structure.md",
        "markdown-frontmatter/versions/1.5/README.md",
        "markdown-frontmatter/versions/1.5/adopt.md",
        "markdown-frontmatter/versions/1.5/artifacts/agent-summary.md",
        "markdown-frontmatter/versions/1.5/skills/markdown-frontmatter/SKILL.md",
        "markdown-frontmatter/versions/1.5/structure.md",
        "project-spec/versions/1.1/README.md",
        "project-spec/versions/1.1/resources/tooling-notes.md",
        "project-spec/versions/1.2/README.md",
        "project-spec/versions/1.2/resources/tooling-notes.md",
        "project-spec/versions/1.3/README.md",
        "project-spec/versions/1.3/resources/tooling-notes.md",
        "project-spec/versions/1.4/README.md",
        "project-spec/versions/1.4/resources/tooling-notes.md",
    }
)


def _legacy_reference_paths(version_dir: Path) -> frozenset[str]:
    """Resources this version's own payload.toml marks as frozen historical bytes.

    `role = "legacy-reference"` resources reproduce exact pre-V5 artifact
    content for `[[legacy_signatures]]` whole-file recognition; their digests
    are pinned in `known_content_digests`, so they must never be edited to
    "fix" stale links they are, by design, preserving verbatim.
    """
    payload_toml = version_dir / "payload.toml"
    if not payload_toml.is_file():
        return frozenset()
    try:
        data = tomllib.loads(payload_toml.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return frozenset()
    return frozenset(
        resource["path"]
        for resource in data.get("resources", [])
        if resource.get("role") == "legacy-reference"
    )


def _find_mutable_refs(version_dir: Path) -> list[str]:
    """Return `relative/path:lineno` for every mutable self-referential link."""
    exclude = _legacy_reference_paths(version_dir)
    violations: list[str] = []
    for path in sorted(version_dir.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(version_dir).as_posix()
        if rel in exclude:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError, OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _MUTABLE_REF_PATTERN.search(line):
                violations.append(f"{rel}:{lineno}")
    return violations


def _all_version_dirs() -> list[Path]:
    dirs: list[Path] = []
    for standard_toml in sorted(_STANDARDS_ROOT.glob("*/standard.toml")):
        versions_root = standard_toml.parent / "versions"
        if versions_root.is_dir():
            dirs.extend(sorted(p for p in versions_root.iterdir() if p.is_dir()))
    return dirs


@pytest.mark.parametrize(
    "version_dir", _all_version_dirs(), ids=lambda p: f"{p.parent.parent.name}@{p.name}"
)
def test_versioned_payload_has_no_mutable_release_ref(version_dir: Path) -> None:
    """A version-pinned payload doc must never hardcode `blob/main` or `blob/v5`.

    See module docstring for why unfixed families are an explicit, frozen
    allowlist rather than a "newest version only" exemption.
    """
    family = version_dir.parent.parent.name
    version = version_dir.name
    violations = [
        f"{family}/versions/{version}/{entry}" for entry in _find_mutable_refs(version_dir)
    ]
    unexpected = [
        v for v in violations if v.rsplit(":", 1)[0] not in _RELEASED_MUTABLE_REF_ALLOWLIST
    ]
    assert not unexpected, (
        f"{family}@{version} hardcodes a mutable project-standards ref "
        f"(blob/main or blob/v5) inside an immutable versioned payload: {unexpected}"
    )


def test_allowlist_has_no_stale_entries() -> None:
    """Every allowlisted file must still exist and still trip the scanner.

    Keeps the grandfathered list honest: once a family gets a corrective new
    version and stops shipping the pattern, its old entries should be deleted
    from the allowlist, not left to silently mask a real fix.
    """
    stale: list[str] = []
    for entry in sorted(_RELEASED_MUTABLE_REF_ALLOWLIST):
        family, _, rest = entry.partition("/versions/")
        version, _, rel = rest.partition("/")
        version_dir = _STANDARDS_ROOT / family / "versions" / version
        found = {v.rsplit(":", 1)[0] for v in _find_mutable_refs(version_dir)}
        if rel not in found:
            stale.append(entry)
    assert not stale, f"allowlist entries no longer reproduce a violation: {stale}"


def test_mutable_ref_scan_would_have_caught_issue_53() -> None:
    """Positive control: the scanner flags the exact bytes that shipped #53.

    `standards/markdown-frontmatter/versions/1.5` is released and byte-frozen
    (cannot be fixed in place — see module docstring). Scanning it directly,
    bypassing the allowlist, proves the detector logic is sound against the
    real historical bug rather than only against a synthetic fixture, and that
    it would fail CI immediately for a *new* payload doing the same thing —
    which is exactly what `test_versioned_payload_has_no_mutable_release_ref`
    now asserts for `versions/1.6`, the corrective fix.
    """
    violations = _find_mutable_refs(_STANDARDS_ROOT / "markdown-frontmatter" / "versions" / "1.5")
    assert violations, "scanner regressed: known-bad 1.5 payload must be flagged"
    assert any(v.startswith("adopt.md:") for v in violations)
    assert any(v.startswith("skills/markdown-frontmatter/SKILL.md:") for v in violations)
