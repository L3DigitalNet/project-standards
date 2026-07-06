"""Parse the bundled canonical project-spec templates into the Registry."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from project_standards.specs.model import Registry

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TIER_FILES = {
    "light": "spec-light-template.md",
    "standard": "spec-standard-template.md",
    "full": "spec-full-template.md",
}
SENTINEL = "SPEC-____"
SPEC_ID_PATTERN = r"^SPEC-[0-9A-Z]{4}$"

ID_TOKEN = re.compile(r"\b([A-Z]{1,4})-([0-9]+)\b")
NOT_AN_ID = {
    "HTTP",
    "AES",
    "SHA",
    "UTF",
    "ISO",
    "IEEE",
    "IEC",
    "WCAG",
    "RPO",
    "RTO",
    "PII",
    "API",
    "URL",
    "SPEC",
    "TLS",
    "CSRF",
    "CORS",
    "SSO",
    "WAL",
    "PITR",
    # SPDX license family prefixes that share the ID_TOKEN shape. MIT/NTP are
    # deliberately omitted — a zero-version license like MIT-0 is indistinguishable
    # from a spec-local id by shape, so a consumer lists it in spec.reference_prefixes.
    "GPL",
    "LGPL",
    "AGPL",
    "MPL",
    "BSD",
    "EPL",
    "BY",  # from CC-BY-4.0, which ID_TOKEN tokenizes as BY-4
}

# Prefixes that are real IDs in ANOTHER namespace (not spec-local), always exempt
# from the ID checks. Kept separate from NOT_AN_ID (which means "not an ID at all")
# so the two intents stay legible. ADR ids are minted by the sibling ADR standard.
BUILTIN_REFERENCE_PREFIXES = frozenset({"ADR"})


def gh_slug(text: str) -> str:
    """Return the GitHub heading-anchor slug used by the templates."""
    s = text.strip().lower().replace("`", "")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return s.strip().replace(" ", "-")


def split_front_matter(text: str) -> tuple[str, str]:
    """Return (frontmatter, body), raising ValueError for an unterminated fence."""
    if not text.startswith("---\n"):
        return "", text
    end = text.index("\n---\n", 4)
    return text[4:end], text[end + 5 :]


def _fm_keys(fm: str) -> list[str]:
    return [m.group(1) for line in fm.splitlines() if (m := re.match(r"^([A-Za-z_][\w]*):", line))]


def headings(body: str) -> list[tuple[int, str, int]]:
    """Return Markdown heading tuples as (level, title, 1-based body line)."""
    out: list[tuple[int, str, int]] = []
    for i, line in enumerate(body.splitlines(), 1):
        if m := re.match(r"^(#{2,4})\s+(.*)$", line):
            out.append((len(m.group(1)), m.group(2).rstrip(), i))
    return out


def section_numbers(hs: list[tuple[int, str, int]]) -> list[tuple[str, int]]:
    """Return ordered (number, line) pairs for numbered headings."""
    out: list[tuple[str, int]] = []
    for _lvl, text, ln in hs:
        if m := re.match(r"^([0-9]+(?:\.[0-9]+)*)\.?\s", text):
            out.append((m.group(1), ln))
    return out


def _section_headings(body: str) -> list[tuple[int, str, int]]:
    return [
        (lvl, title, line)
        for lvl, title, line in headings(body)
        if re.match(r"^([0-9]+(?:\.[0-9]+)*)\.?\s", title)
    ]


def numkey(s: str) -> list[int]:
    return [int(x) for x in s.split(".")]


_APPENDIX_HEADING = "^## Appendix "


def appendix_letters(body: str) -> list[str]:
    """Return every '## Appendix X:' letter found in body, in document order."""
    return re.findall(rf"{_APPENDIX_HEADING}([A-Z]):", body, re.M)


def appendix_pattern(letter: str) -> str:
    """Regex source matching one lettered appendix heading through its content."""
    return rf"{_APPENDIX_HEADING}{re.escape(letter)}:.*?(?=^## |\Z)"


def declared_prefixes(body: str) -> dict[str, str]:
    """Return Appendix-A prefix declarations from template/spec Markdown."""
    apx = re.search(r"## Appendix A:.*?(?=\n## |\Z)", body, re.S)
    declared: dict[str, str] = {}
    if apx:
        for row in re.finditer(
            r"^\|\s*`([A-Z]{1,4})-`\s*\|[^|]*\|\s*([^|]+?)\s*\|",
            apx.group(0),
            re.M,
        ):
            declared[row.group(1)] = row.group(2).strip()
    return declared


@cache
def load_registry() -> Registry:
    """Load the immutable registry derived from the three bundled templates."""
    tier_body: dict[str, str] = {}
    tier_fm: dict[str, str] = {}
    for tier, fname in TIER_FILES.items():
        fm, body = split_front_matter((TEMPLATES_DIR / fname).read_text(encoding="utf-8"))
        tier_body[tier] = body
        tier_fm[tier] = fm

    full = tier_body["full"]
    full_secs = section_numbers(headings(full))
    canonical = frozenset(n for n, _ in full_secs)
    titles = {
        n: t for (n, _), (_lvl, t, _ln) in zip(full_secs, _section_headings(full), strict=True)
    }
    tier_sections = {
        tier: frozenset(n for n, _ in section_numbers(headings(body)))
        for tier, body in tier_body.items()
    }
    appendices = {tier: frozenset(appendix_letters(body)) for tier, body in tier_body.items()}
    tier_prefixes = {tier: frozenset(declared_prefixes(body)) for tier, body in tier_body.items()}
    prefix_defined_in = declared_prefixes(full)

    return Registry(
        canonical_sections=canonical,
        section_titles=titles,
        appendices=appendices,
        full_only_appendices=appendices["full"] - appendices["standard"],
        prefix_defined_in=prefix_defined_in,
        frontmatter_keys=tuple(_fm_keys(tier_fm["full"])),
        tier_sections=tier_sections,
        tier_prefixes=tier_prefixes,
        sentinel=SENTINEL,
        spec_id_pattern=SPEC_ID_PATTERN,
    )
