"""Shared id-token helpers used by validate_id (id validation/fix) and
format_frontmatter (scaffold). One copy so the two tools cannot drift."""

from __future__ import annotations

import re
import secrets
import string
import unicodedata

# Base-36 alphabet (digits + lowercase letters) for the 6-char id token.
_BASE36_CHARS = string.digits + string.ascii_lowercase

# Cap for GENERATED slugs (validate-id --fix, format-frontmatter scaffolds). The
# slug is a readable hint, not the identity — uniqueness comes from the base-36
# token — so an uncapped slug from a long title only makes ids painful in
# related: lists. Validation does not enforce this bound; hand-written longer
# slugs remain valid. Documented in standards/markdown-frontmatter/README.md.
_MAX_SLUG_LENGTH = 60


def slugify(text: str) -> str:
    """Lowercase kebab-case slug: strip accents to ASCII, lowercase, collapse
    every run of non-alphanumerics to a single hyphen, trim leading/trailing.
    Slugs over 60 characters are truncated at a word boundary (never mid-word)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if len(text) > _MAX_SLUG_LENGTH:
        head = text[:_MAX_SLUG_LENGTH]
        # Cut at the last hyphen inside the window so the slug never ends
        # mid-word; a single unbroken token longer than the cap is kept as-is
        # hard-truncated (no boundary exists to prefer).
        if "-" in head:
            head = head[: head.rfind("-")]
        text = head.strip("-")
    return text


def random_token(length: int = 6) -> str:
    """A cryptographically-random base-36 token (default 6 chars)."""
    return "".join(secrets.choice(_BASE36_CHARS) for _ in range(length))
