"""Version-selected ADR validation and legacy migration providers."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from typing import cast

from project_standards.validate_frontmatter import (
    FrontmatterParseError,
    missing_adr_sections,
    parse_frontmatter,
)


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _sequence(value: object, *, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"{name} must be an array")
    return cast("Sequence[object]", value)


def _finding(code: str, path: str, identity: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "error",
        "path": path,
        "identity": identity,
        "message": message,
        "hint": "repair the ADR from the selected package template",
    }


def run_validate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Return MADR section findings from immutable document snapshots."""
    config = _table(request.get("config"), name="config")
    if config.get("require_sections") is not True:
        return {"findings": []}
    snapshots = _table(request.get("snapshots"), name="snapshots")
    documents = _sequence(snapshots.get("documents"), name="snapshots.documents")
    findings: list[dict[str, str]] = []
    for raw in documents:
        document = _table(raw, name="document")
        path = document.get("path")
        kind = document.get("kind")
        encoded = document.get("content_base64")
        if not isinstance(path, str):
            raise ValueError("document snapshot requires a path")
        if kind != "regular" or not isinstance(encoded, str):
            findings.append(
                _finding("ADR-PATH", path, "$file", "ADR snapshot is not a regular file")
            )
            continue
        try:
            text = base64.b64decode(encoded, validate=True).decode("utf-8-sig")
            metadata = parse_frontmatter(text)
        except ValueError, UnicodeDecodeError, FrontmatterParseError:
            findings.append(
                _finding("ADR-PARSE", path, "$frontmatter", "ADR frontmatter is invalid")
            )
            continue
        if metadata is None or metadata.get("doc_type") != "adr":
            continue
        for section in missing_adr_sections(text):
            findings.append(
                _finding(
                    "ADR-SECTION",
                    path,
                    section,
                    f"ADR is missing required section: {section}",
                )
            )
    findings.sort(key=lambda item: (item["path"].encode(), item["identity"].encode()))
    return {"findings": findings}


def run_migrate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Map the bounded V4 ADR namespace and exact scaffold into V2 state."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    legacy = _table(snapshots.get("legacy_config"), name="snapshots.legacy_config")
    markdown = _table(legacy.get("markdown"), name="legacy_config.markdown")
    adr = _table(markdown.get("adr"), name="legacy_config.markdown.adr")
    config: dict[str, object] = {}
    recognized: list[str] = []
    if "version" in adr:
        config["contract_version"] = adr["version"]
        recognized.append("/markdown/adr/version")
    if "require_sections" in adr:
        config["require_sections"] = adr["require_sections"]
        recognized.append("/markdown/adr/require_sections")

    claims: list[dict[str, object]] = []
    raw_signatures = _table(
        snapshots.get("legacy_signatures"),
        name="snapshots.legacy_signatures",
    )
    signature = raw_signatures.get("legacy-adr-template")
    if isinstance(signature, Mapping):
        signature_table = cast("Mapping[str, object]", signature)
        observed = signature_table.get("docs/adr/adr.template.md")
        if isinstance(observed, Mapping):
            observed_table = cast("Mapping[str, object]", observed)
            digest = observed_table.get("digest")
            if observed_table.get("known") is True:
                if not isinstance(digest, str):
                    raise ValueError("known ADR template signature omitted its digest")
                claims.append(
                    {
                        "signature_id": "legacy-adr-template",
                        "target": "docs/adr/adr.template.md",
                        "observed_digest": digest,
                        "ownership": "create-only",
                        "disposition": "preserve",
                    }
                )
    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "adr",
            "version": str(request.get("version")),
            "selector": "latest",
            "config": config,
            "recognized_settings": sorted(recognized),
        },
        "claims": claims,
        "findings": [],
    }
