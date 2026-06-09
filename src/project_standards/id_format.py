"""Shared id-token helpers used by validate_id (id validation/fix) and
format_frontmatter (scaffold). One copy so the two tools cannot drift."""

from __future__ import annotations

import re
import secrets
import string
import unicodedata

# Base-36 alphabet (digits + lowercase letters) for the 6-char id token.
_BASE36_CHARS = string.digits + string.ascii_lowercase


def slugify(text: str) -> str:
    """Lowercase kebab-case slug: strip accents to ASCII, lowercase, collapse
    every run of non-alphanumerics to a single hyphen, trim leading/trailing."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def random_token(length: int = 6) -> str:
    """A cryptographically-random base-36 token (default 6 chars)."""
    return "".join(secrets.choice(_BASE36_CHARS) for _ in range(length))
