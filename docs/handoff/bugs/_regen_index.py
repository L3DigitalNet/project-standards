#!/usr/bin/env python3
"""Regenerate docs/handoff/bugs/INDEX.md from bug frontmatter."""

import re
from pathlib import Path

BUGS = Path(__file__).parent


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"')
    return fields


def main() -> None:
    rows = []
    for path in sorted(BUGS.glob("[0-9][0-9][0-9]-*.md")):
        fields = parse_frontmatter(path.read_text(encoding="utf-8"))
        rows.append(
            (
                fields.get("bug_id", "?"),
                fields.get("date", "?"),
                fields.get("title", "?"),
                fields.get("services", "[]").strip("[]"),
                fields.get("status", "?"),
            )
        )

    lines = [
        "# Bug Index",
        "",
        "Generated from frontmatter. Regenerate with `python3 docs/handoff/bugs/_regen_index.py`.",
        "",
    ]
    if not rows:
        lines.append("_No bugs recorded._")
    else:
        lines.extend(
            [
                "| # | Date | Title | Services | Status |",
                "|---|---|---|---|---|",
            ]
        )
        for row in rows:
            lines.append("| " + " | ".join(str(item) for item in row) + " |")

    (BUGS / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
