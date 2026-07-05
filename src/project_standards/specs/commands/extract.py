"""Extract one markdown slice from a parsed spec."""

from __future__ import annotations

import re
from dataclasses import dataclass

from project_standards.specs.document import section_slice
from project_standards.specs.model import SpecDocument
from project_standards.specs.registry import ID_TOKEN


@dataclass(frozen=True)
class ExtractResult:
    kind: str
    found: bool
    markdown: str | None
    selector: str


def _appendix_slice(body: str, letter: str) -> str | None:
    m = re.search(rf"^## Appendix {re.escape(letter)}:.*?(?=^## |\Z)", body, re.M | re.S)
    return m.group(0).rstrip() if m else None


def _id_row(body: str, spec_id: str) -> str | None:
    for line in body.splitlines():
        if line.lstrip().startswith("|") and re.search(rf"\b{re.escape(spec_id)}\b", line):
            return line.strip()
    return None


def extract_slice(doc: SpecDocument, selector: str) -> ExtractResult:
    """Return the first matching id, section, appendix, or heading slice."""
    body = doc.body
    if ID_TOKEN.fullmatch(selector):
        row = _id_row(body, selector)
        return ExtractResult("id", row is not None, row, selector)
    if selector.startswith("§"):
        sec = section_slice(doc, selector[1:])
        return ExtractResult("section", sec is not None, sec, selector)
    if selector.lower().startswith("appendix "):
        letter = selector.split()[1].upper()
        appendix = _appendix_slice(body, letter)
        return ExtractResult("appendix", appendix is not None, appendix, selector)
    m = re.search(rf"^#+\s.*{re.escape(selector)}.*?(?=^#+\s|\Z)", body, re.M | re.S)
    heading = m.group(0).rstrip() if m else None
    return ExtractResult("heading", heading is not None, heading, selector)
