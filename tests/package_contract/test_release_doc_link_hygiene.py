"""Guard against issue #53: pinned release payloads must not link mutable refs.

A versioned payload under `standards/<family>/versions/<version>/` is byte-frozen
once released, so every self-referential link in it must resolve to the same
bytes forever. A hardcoded
`https://github.com/L3DigitalNet/project-standards/blob/(main|v5)/...` link
always resolves against the CURRENT tip of that branch or moving major tag, so a
reader on an old pinned release is silently handed documentation, CLI behavior,
or a skill file that has moved on since the release was cut. That is exactly
issue #53: markdown-frontmatter 1.2-1.5's `adopt.md` and installed `SKILL.md`
hardcoded `blob/main`/`blob/v5` links.

The defect is the MOVING ref, not absoluteness. A repo-relative link is correct
only for a document that stays inside the repository tree; a document the payload
INSTALLS into a consumer repository (`.agents/skills/.../SKILL.md`,
`.standards/packages/.../agent-summary.md`) lands where those relative paths
resolve to nothing, or worse to the consumer's own files. Those documents must
use an immutable, version-pinned absolute URL — `blob/vX.Y.Z/...` — which this
scan therefore permits and the pattern below deliberately does not match.

Scoping rationale (why this is an explicit allowlist, not "newest version only"):

Released payload bytes are immutable at any release level (mutating them is
`PC-RELEASE-PAYLOAD-MUTATED`-forbidden; the only correction is a NEW payload
version — see `standards/markdown-frontmatter/versions/1.6`, the fix for #53).
A blanket "no version anywhere may contain this pattern" assertion therefore
cannot pass at HEAD: `standards/adr/versions/{1.1,1.2}`,
`standards/cli-documentation/versions/{1.1..1.4}`, and
`standards/project-spec/versions/{1.1..1.4}` independently ship the same
mutable-ref pattern and are unrelated to #53's fix. Issue #72 later gave those
three families their own corrective successors (`adr/versions/1.3`,
`cli-documentation/versions/1.5`, `project-spec/versions/1.5`), which is what a
fix can do: the offending released bytes stay on disk and stay allowlisted
forever, because they are immutable. Neither rule is available without either
fixing unrelated families (scope creep well beyond #53) or silently ignoring a
whole family's newest version forever.

The chosen rule instead scans every file in every version of every family and
fails on any match, *except* two grandfathered exclusions:

1. A fixed, explicit, path-level allowlist of the specific already-released
   files enumerated below — added exactly once, for the state that already
   existed before this test was written. It must never grow. It does not shrink
   when a family is fixed either: a corrective new version (markdown-frontmatter
   1.6 for #53; adr 1.3, cli-documentation 1.5, and project-spec 1.5 for #72)
   leaves the released offenders byte-frozen on disk, so their entries stay and
   `test_allowlist_has_no_stale_entries` keeps proving they still reproduce.
   An entry may only be deleted if the released file itself ceases to exist.
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

# Moving refs only: `main`, the floating `v5` major tag, and any other branch-like
# ref that can be repointed. An immutable release tag (`v5.10.0`) is the supported
# form for installed documents and must not match — the trailing `/` after the
# alternation is what keeps `blob/v5.10.0/` out of this pattern.
_MUTABLE_REF_PATTERN = re.compile(
    r"github\.com/L3DigitalNet/project-standards/(?:blob|tree)/(?:main|v5)/"
)
_PINNED_REF_PATTERN = re.compile(
    r"github\.com/L3DigitalNet/project-standards/(?:blob|tree)/v[0-9]+\.[0-9]+\.[0-9]+/"
)

# Grandfathered released files that already contained the mutable-ref pattern
# before this test existed (issue #53 triage sweep, 2026-07-27). Every entry is
# `family/versions/version/relative-path`. This set is frozen: never add an entry
# for a fresh bug, and do not delete one when a family is fixed — the corrective
# successor is a NEW version directory, and the released offender it supersedes
# keeps shipping the pattern verbatim because its bytes cannot change.
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


def test_version_pinned_refs_are_permitted() -> None:
    """An immutable release tag is the supported form, not a violation.

    A document a payload installs into a consumer repository cannot use a
    repo-relative link — it lands outside this repository's tree — so it pins an
    exact release tag instead. The scanner must accept that and still reject the
    moving forms.
    """
    pinned = "https://github.com/L3DigitalNet/project-standards/blob/v5.10.0/standards/x.md"
    moving = "https://github.com/L3DigitalNet/project-standards/blob/v5/standards/x.md"

    assert _PINNED_REF_PATTERN.search(pinned)
    assert not _MUTABLE_REF_PATTERN.search(pinned)
    assert _MUTABLE_REF_PATTERN.search(moving)


def test_installed_markdown_frontmatter_docs_pin_an_exact_release_tag() -> None:
    """The two 1.6 documents that leave this repository must be tag-pinned.

    `payload.toml` relocates them under `.agents/` and `.standards/` in the
    consumer repository, where `../README.md` resolves to a file that does not
    exist. Relative links are correct only for the documents that stay in the
    versioned payload directory, which the sibling assertion covers.
    """
    root = _STANDARDS_ROOT / "markdown-frontmatter" / "versions" / "1.6"
    installed = (
        root / "artifacts/agent-summary.md",
        root / "skills/markdown-frontmatter/SKILL.md",
    )

    for path in installed:
        text = path.read_text(encoding="utf-8")
        targets = re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text)
        assert targets, f"{path} has no links to check"
        for target in targets:
            assert _PINNED_REF_PATTERN.search(target), f"{path}: {target} is not tag-pinned"
    for path in (root / "adopt.md", root / "README.md", root / "structure.md"):
        for target in re.findall(r"(?<!!)\[[^\]]+\]\((\.\.?/[^)]+)\)", path.read_text("utf-8")):
            assert (path.parent / target).resolve().exists(), f"{path}: {target} does not resolve"


@pytest.mark.parametrize(
    ("family", "version"),
    [("adr", "1.3"), ("cli-documentation", "1.5"), ("project-spec", "1.5")],
    ids=lambda value: str(value),
)
def test_issue_72_corrective_versions_resolve_their_relative_links(
    family: str, version: str
) -> None:
    """Every rewritten link in a #72 successor must hit a real repository path.

    These three families were fixed the same way #53 fixed markdown-frontmatter,
    but none of their flagged documents is installed into a consumer repository
    (their `payload.toml`s declare only in-tree resources for those paths), so
    all rewrites are repo-relative rather than tag-pinned. A relative link is
    only correct if it resolves, and a wrong `../` depth is silent on GitHub —
    hence this assertion rather than trusting the mutable-ref scan alone.
    """
    root = _STANDARDS_ROOT / family / "versions" / version
    checked = 0
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"(?<!!)\[[^\]]+\]\((\.\.?/[^)#]+)(?:#[^)]*)?\)", text):
            checked += 1
            assert (path.parent / target).resolve().exists(), f"{path}: {target} does not resolve"
    assert checked, f"{family}@{version} has no relative links to check"
