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


def _finding(
    code: str,
    path: str,
    identity: str,
    message: str,
    *,
    hint: str = "repair the ADR from the selected package template",
) -> dict[str, str]:
    return {
        "code": code,
        "severity": "error",
        "path": path,
        "identity": identity,
        "message": message,
        "hint": hint,
    }


def _relationships(metadata: Mapping[str, object], field: str) -> tuple[str, ...]:
    """Return recognized relationship IDs without duplicating schema validation."""
    project = metadata.get("project")
    if not isinstance(project, Mapping):
        return ()
    project_table = cast("Mapping[str, object]", project)
    values = project_table.get(field)
    if not isinstance(values, Sequence) or isinstance(values, str | bytes):
        return ()
    relationship_values = cast("Sequence[object]", values)
    return tuple(value for value in relationship_values if isinstance(value, str))


def _append_amendment_findings(
    records: Sequence[tuple[str, Mapping[str, object]]],
    findings: list[dict[str, str]],
) -> None:
    """Check declared amendment edges over the one immutable snapshot corpus.

    Relationship shape remains the Markdown Frontmatter companion's concern. This
    pass consumes only recognized string IDs and never infers an edge from prose or
    reads a path outside the supplied snapshots.
    """
    by_id = {
        adr_id: (path, metadata)
        for path, metadata in records
        if isinstance(adr_id := metadata.get("id"), str)
    }
    for source_path, source in records:
        source_id = source.get("id")
        if not isinstance(source_id, str):
            continue
        for target_id in _relationships(source, "amends"):
            relationship_identity = f"{source_id}.project.amends[{target_id}]"
            target = by_id.get(target_id)
            if target is None:
                findings.append(
                    _finding(
                        "ADR-AMEND-ONEWAY",
                        source_path,
                        relationship_identity,
                        f"ADR {source_id} project.amends references missing ADR {target_id}",
                        hint=(
                            f"add ADR {target_id} to the document snapshot, or remove it "
                            f"from project.amends on {source_id}"
                        ),
                    )
                )
                continue
            target_path, target_metadata = target
            if source_id not in _relationships(target_metadata, "amended_by"):
                findings.append(
                    _finding(
                        "ADR-AMEND-ONEWAY",
                        target_path,
                        f"{target_id}.project.amended_by[{source_id}]",
                        f"ADR {target_id} is missing project.amended_by entry for {source_id}",
                        hint=(
                            f"add {source_id} to project.amended_by on {target_id}, or remove "
                            f"{target_id} from project.amends on {source_id}"
                        ),
                    )
                )
            if target_metadata.get("status") == "superseded":
                findings.append(
                    _finding(
                        "ADR-AMEND-SUPERSEDED",
                        source_path,
                        relationship_identity,
                        f"ADR {source_id} amends superseded ADR {target_id}",
                        hint=(
                            f"remove {target_id} from project.amends on {source_id} and "
                            "amend the record now in force"
                        ),
                    )
                )
        for amender_id in _relationships(source, "amended_by"):
            amender = by_id.get(amender_id)
            if amender is None:
                findings.append(
                    _finding(
                        "ADR-AMEND-ONEWAY",
                        source_path,
                        f"{source_id}.project.amended_by[{amender_id}]",
                        f"ADR {source_id} project.amended_by references missing ADR {amender_id}",
                        hint=(
                            f"add ADR {amender_id} to the document snapshot, or remove it "
                            f"from project.amended_by on {source_id}"
                        ),
                    )
                )
                continue
            amender_path, amender_metadata = amender
            if source_id not in _relationships(amender_metadata, "amends"):
                findings.append(
                    _finding(
                        "ADR-AMEND-ONEWAY",
                        amender_path,
                        f"{amender_id}.project.amends[{source_id}]",
                        f"ADR {amender_id} is missing project.amends entry for {source_id}",
                        hint=(
                            f"add {source_id} to project.amends on {amender_id}, or remove "
                            f"{amender_id} from project.amended_by on {source_id}"
                        ),
                    )
                )


def run_validate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Return configured ADR findings from immutable document snapshots."""
    config = _table(request.get("config"), name="config")
    require_sections = config.get("require_sections") is True
    validate_amendments = config.get("validate_amendments") is True
    if not require_sections and not validate_amendments:
        return {"findings": []}
    snapshots = _table(request.get("snapshots"), name="snapshots")
    documents = _sequence(snapshots.get("documents"), name="snapshots.documents")
    findings: list[dict[str, str]] = []
    records: list[tuple[str, Mapping[str, object]]] = []
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
        records.append((path, metadata))
        if require_sections:
            for section in missing_adr_sections(text):
                findings.append(
                    _finding(
                        "ADR-SECTION",
                        path,
                        section,
                        f"ADR is missing required section: {section}",
                    )
                )
    if validate_amendments:
        _append_amendment_findings(records, findings)
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
