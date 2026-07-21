"""Internal JSONC sanitization for mutable runtime settings."""

from __future__ import annotations

import json


def sanitize_jsonc(source: str) -> str:
    """Return strict-JSON-compatible text without changing string contents.

    Comments and trailing commas are replaced with spaces so parse diagnostics
    retain the source line and column positions. An unterminated block comment
    raises ``JSONDecodeError`` like other malformed JSONC input.
    """
    cleaned = list(source)
    in_string = False
    escaped = False
    index = 0

    while index < len(source):
        character = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue

        if character == '"':
            in_string = True
            index += 1
            continue
        if not source.startswith("//", index) and not source.startswith("/*", index):
            index += 1
            continue

        comment_start = index
        if source.startswith("//", index):
            comment_end = index + 2
            while comment_end < len(source) and source[comment_end] not in "\r\n":
                comment_end += 1
        else:
            closing = source.find("*/", index + 2)
            if closing == -1:
                raise json.JSONDecodeError("Unterminated block comment", source, comment_start)
            comment_end = closing + 2

        # Whitespace replacement preserves offsets and cannot fuse tokens that
        # were separated by a comment into a different valid JSON token.
        for comment_index in range(comment_start, comment_end):
            if cleaned[comment_index] not in "\r\n":
                cleaned[comment_index] = " "
        index = comment_end

    in_string = False
    escaped = False
    for index, character in enumerate(cleaned):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
            continue
        if character != ",":
            continue

        previous = index - 1
        while previous >= 0 and cleaned[previous] in " \t\r\n":
            previous -= 1
        following = index + 1
        while following < len(cleaned) and cleaned[following] in " \t\r\n":
            following += 1
        if (
            previous >= 0
            and cleaned[previous] not in "{[,:"
            and following < len(cleaned)
            and cleaned[following] in "}]"
        ):
            cleaned[index] = " "

    return "".join(cleaned)
