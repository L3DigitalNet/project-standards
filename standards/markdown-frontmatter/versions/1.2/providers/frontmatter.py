"""Version-selected frontmatter providers over immutable JSON snapshots."""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from jsonschema import Draft202012Validator

from project_standards.control_plane.snapshot import EntryKind, SnapshotEntry
from project_standards.frontmatter_authoring import (
    plan_frontmatter_fix_entries,
    plan_frontmatter_format_entries,
    plan_frontmatter_id_fix_entries,
)
from project_standards.id_format import slugify
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.validate_frontmatter import FrontmatterParseError, parse_frontmatter
from project_standards.validate_id import (
    _ADR_ID_RE,  # pyright: ignore[reportPrivateUsage]  # shared public-validator grammar
    validate_id,
)
from project_standards.validate_references import (
    _ref_values,  # pyright: ignore[reportPrivateUsage]  # shared reference-field contract
)

_TOKEN = re.compile(r"^[0-9a-z]{6}$", re.ASCII)
_DATE_SHAPE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_DATE_FIELDS = ("created", "updated", "reviewed")
_ADR_NUMBER = re.compile(r"^adr-([0-9]{4,})-", re.ASCII)


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _sequence(value: object, *, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"{name} must be an array")
    return cast("Sequence[object]", value)


def _digest(content: bytes) -> Sha256Digest:
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")


def _entries(request: Mapping[str, object]) -> tuple[SnapshotEntry, ...]:
    snapshots = _table(request.get("snapshots"), name="snapshots")
    documents = _sequence(snapshots.get("documents"), name="snapshots.documents")
    entries: list[SnapshotEntry] = []
    for raw_document in documents:
        document = _table(raw_document, name="document")
        path = SafeRelativePath.parse(str(document.get("path")))
        kind = EntryKind(str(document.get("kind")))
        mode_value = document.get("mode")
        mode = mode_value if isinstance(mode_value, str) else None
        encoded = document.get("content_base64")
        content = base64.b64decode(encoded, validate=True) if isinstance(encoded, str) else None
        precondition = Sha256Digest(str(document.get("precondition_digest")))
        entries.append(
            SnapshotEntry(
                path=path,
                kind=kind,
                content=content,
                mode=mode,
                link_target=None,
                content_digest=_digest(content) if content is not None else None,
                precondition_digest=precondition,
            )
        )
    return tuple(entries)


def run_fix(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Return a complete format-and-id plan without reading the live repository."""
    config = _table(request.get("config"), name="config")
    if config.get("schema") == "custom":
        return {
            "schema_version": "1.0",
            "standard_id": "markdown-frontmatter",
            "version": str(request.get("version")),
            "actions": [],
        }
    snapshots = _table(request.get("snapshots"), name="snapshots")
    raw_tokens = _sequence(snapshots.get("tokens"), name="snapshots.tokens")
    tokens = iter(raw_tokens)

    def next_token() -> str:
        token = next(tokens, None)
        if not isinstance(token, str) or _TOKEN.fullmatch(token) is None:
            raise ValueError("snapshot token is missing or invalid")
        return token

    version = PackageVersion(str(request.get("version")))
    mode = snapshots.get("authoring_mode", "combined")
    if mode == "id-only":
        planned = plan_frontmatter_id_fix_entries(
            _entries(request),
            version=version,
            valid_doc_types=_doc_types(_bundled_schema(_resources)),
            token_factory=next_token,
        )
    else:
        today = snapshots.get("today")
        if not isinstance(today, str):
            raise ValueError("snapshots.today must be a string")
        if mode == "format-only":
            bump_updated = snapshots.get("bump_updated", False)
            if not isinstance(bump_updated, bool):
                raise ValueError("snapshots.bump_updated must be a boolean")
            planned = plan_frontmatter_format_entries(
                _entries(request),
                version=version,
                token_factory=next_token,
                today=today,
                bump_updated=bump_updated,
            )
        elif mode == "combined":
            planned = plan_frontmatter_fix_entries(
                _entries(request),
                version=version,
                token_factory=next_token,
                today=today,
            )
        else:
            raise ValueError("snapshots.authoring_mode is invalid")
    output = planned.plan.model_dump(mode="json")
    refused = frozenset(planned.refused_paths)
    diagnostics: list[dict[str, object]] = []
    for path, message in planned.warnings:
        refusal = path in refused
        unparseable = "duplicate top-level key" in message or "not valid UTF-8" in message
        if refusal:
            code = "FM-AUTHORING-REFUSED"
        elif unparseable:
            code = "FM-AUTHORING-UNPARSEABLE"
        else:
            code = "FM-AUTHORING-WARNING"
        diagnostics.append(
            {
                "code": code,
                "severity": "error" if refusal or unparseable else "warning",
                "path": path,
                "message": message,
                "refusal": refusal,
            }
        )
    output["diagnostics"] = diagnostics
    return output


def run_id_next(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, str]:
    """Return one caller-seeded standard document ID."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    doc_type = snapshots.get("doc_type")
    title = snapshots.get("title")
    token = snapshots.get("token")
    if not all(isinstance(value, str) for value in (doc_type, title, token)):
        raise ValueError("id-next requires string doc_type, title, and token snapshots")
    assert isinstance(doc_type, str)
    assert isinstance(title, str)
    assert isinstance(token, str)
    if doc_type not in _doc_types(_bundled_schema(resources)):
        raise ValueError("id-next doc_type is outside the selected schema enum")
    slug = slugify(title)
    if not slug or _TOKEN.fullmatch(token) is None:
        raise ValueError("id-next snapshots cannot produce a valid document id")
    return {"content": f"{doc_type}-{token}-{slug}"}


def run_render_workflow_job(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, str]:
    """Render the published or same-commit reusable-workflow job."""
    config = _table(request.get("config"), name="config")
    resource_id = (
        "workflow-job-local" if config.get("workflow_mode") == "local" else "workflow-job-caller"
    )
    return {"content": resources[resource_id].decode("utf-8")}


def _finding(
    code: str,
    path: str,
    identity: str,
    message: str,
    hint: str,
    *,
    severity: str = "error",
) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "path": path,
        "identity": identity,
        "message": message,
        "hint": hint,
    }


def _bundled_schema(resources: Mapping[str, bytes]) -> dict[str, object]:
    try:
        content = resources["frontmatter-schema"]
    except KeyError as exc:
        raise ValueError("provider requires the selected frontmatter schema resource") from exc
    return _schema_document(content)


def _schema_document(content: bytes) -> dict[str, object]:
    raw = cast(object, json.loads(content))
    if not isinstance(raw, dict):
        raise ValueError("frontmatter schema must be an object")
    parsed = cast("dict[str, object]", raw)
    Draft202012Validator.check_schema(cast("dict[str, Any]", parsed))
    return parsed


def _schema(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, object]:
    config = _table(request.get("config"), name="config")
    snapshots = _table(request.get("snapshots"), name="snapshots")
    if config.get("schema") == "custom":
        schema_path = config.get("schema_path")
        if not isinstance(schema_path, str):
            raise ValueError("custom schema config requires schema_path")
        referenced = _sequence(
            snapshots.get("referenced_input_content"),
            name="snapshots.referenced_input_content",
        )
        matching: list[Mapping[str, object]] = []
        for item in referenced:
            referenced_input = _table(item, name="referenced input")
            if (
                referenced_input.get("standard_id") == "markdown-frontmatter"
                and referenced_input.get("extension_id") == "custom-schema"
                and referenced_input.get("path") == schema_path
            ):
                matching.append(referenced_input)
        if len(matching) != 1:
            raise ValueError("custom schema requires exactly one matching referenced snapshot")
        encoded = matching[0].get("content_base64")
        if not isinstance(encoded, str):
            raise ValueError("custom schema referenced snapshot must carry content_base64")
        content = base64.b64decode(encoded, validate=True)
    else:
        return _bundled_schema(resources)
    return _schema_document(content)


def _doc_types(schema: Mapping[str, object]) -> frozenset[str]:
    properties = _table(schema.get("properties"), name="schema.properties")
    doc_type_schema = _table(properties.get("doc_type"), name="schema.properties.doc_type")
    enum = _sequence(doc_type_schema.get("enum"), name="schema.properties.doc_type.enum")
    doc_types = frozenset(value for value in enum if isinstance(value, str))
    if len(doc_types) != len(enum):
        raise ValueError("schema doc_type enum must contain only strings")
    return doc_types


def _calendar_findings(path: str, metadata: Mapping[str, object]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for field in _DATE_FIELDS:
        value = metadata.get(field)
        if not isinstance(value, str) or _DATE_SHAPE.fullmatch(value) is None:
            continue
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            findings.append(
                _finding(
                    "FM-DATE",
                    path,
                    field,
                    "frontmatter date is not a real calendar date",
                    "use a real calendar date in YYYY-MM-DD form",
                )
            )
    return findings


def _date(value: object) -> datetime.date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _reference_resolves(
    reference: str,
    ids: Mapping[str, list[str]],
    regular_paths: frozenset[str],
) -> bool:
    if reference in ids:
        return True
    try:
        path = SafeRelativePath.parse(reference)
    except ValueError:
        return False
    return path.original in regular_paths


def _repository_findings(
    documents: Sequence[tuple[str, Mapping[str, object]]],
    regular_paths: frozenset[str],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    ids: dict[str, list[str]] = {}
    for path, metadata in documents:
        document_id = metadata.get("id")
        if isinstance(document_id, str) and document_id:
            ids.setdefault(document_id, []).append(path)

    for document_id, paths in sorted(ids.items()):
        if len(paths) > 1:
            findings.append(
                _finding(
                    "FM-DUPLICATE-ID",
                    sorted(paths)[0],
                    document_id,
                    "document id is duplicated",
                    "assign a unique stable id to each document",
                )
            )

    for path, metadata in documents:
        created = _date(metadata.get("created"))
        updated = _date(metadata.get("updated"))
        reviewed = _date(metadata.get("reviewed"))
        if created is not None and updated is not None and created > updated:
            findings.append(
                _finding(
                    "FM-DATE-ORDER",
                    path,
                    "created",
                    "created date is after updated date",
                    "make document lifecycle dates chronological",
                )
            )
        if reviewed is not None and created is not None and reviewed < created:
            findings.append(
                _finding(
                    "FM-DATE-ORDER",
                    path,
                    "reviewed",
                    "reviewed date is before created date",
                    "make document lifecycle dates chronological",
                )
            )

        for reference in _ref_values(dict(metadata)):
            if "#" in reference:
                message = "section anchors are not valid document references"
            elif _reference_resolves(reference, ids, regular_paths) or _ADR_ID_RE.match(reference):
                continue
            else:
                message = "document reference is unresolved or leaves the repository snapshot"
            findings.append(
                _finding(
                    "FM-REFERENCE",
                    path,
                    reference,
                    message,
                    "use a document id or contained regular snapshot path",
                    severity="warning",
                )
            )

    supersedes: dict[str, set[str]] = {}
    superseded_by: dict[str, set[str]] = {}
    for _path, metadata in documents:
        document_id = metadata.get("id")
        if not isinstance(document_id, str) or not document_id:
            continue
        raw_supersedes = metadata.get("supersedes")
        raw_superseded_by = metadata.get("superseded_by")
        supersedes.setdefault(document_id, set()).update(
            value for value in _string_values(raw_supersedes) if value
        )
        superseded_by.setdefault(document_id, set()).update(
            value for value in _string_values(raw_superseded_by) if value
        )
    for path, metadata in documents:
        document_id = metadata.get("id")
        if not isinstance(document_id, str) or not document_id:
            continue
        for replacement in _string_values(metadata.get("superseded_by")):
            if replacement in supersedes and document_id not in supersedes[replacement]:
                findings.append(
                    _finding(
                        "FM-RECIPROCITY",
                        path,
                        replacement,
                        "superseded_by relationship is not reciprocal",
                        "add the inverse supersedes relationship",
                        severity="warning",
                    )
                )
        for replaced in _string_values(metadata.get("supersedes")):
            if replaced in superseded_by and document_id not in superseded_by[replaced]:
                findings.append(
                    _finding(
                        "FM-RECIPROCITY",
                        path,
                        replaced,
                        "supersedes relationship is not reciprocal",
                        "add the inverse superseded_by relationship",
                        severity="warning",
                    )
                )

    adr_numbers: dict[int, list[str]] = {}
    for _path, metadata in documents:
        if metadata.get("doc_type") != "adr":
            continue
        document_id = metadata.get("id")
        match = _ADR_NUMBER.match(document_id) if isinstance(document_id, str) else None
        if match is not None:
            adr_numbers.setdefault(int(match.group(1)), []).append(match.string)
    for number, document_ids in sorted(adr_numbers.items()):
        if len(document_ids) > 1:
            findings.append(
                _finding(
                    "FM-DUPLICATE-ADR",
                    sorted(ids[document_ids[0]])[0],
                    str(number),
                    "ADR sequence number is duplicated",
                    "assign one repository-local sequence number per ADR",
                )
            )
    return findings


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in cast("list[object]", value) if isinstance(item, str))
    return ()


def run_validate(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Validate schema, ID, and optional reference facts from document snapshots."""
    config = _table(request.get("config"), name="config")
    schema = _schema(request, resources)
    validator = Draft202012Validator(cast("dict[str, Any]", schema))
    required = config.get("required", True) is True
    custom_schema = config.get("schema") == "custom"
    valid_doc_types: frozenset[str] = frozenset() if custom_schema else _doc_types(schema)
    findings: list[dict[str, str]] = []
    documents: list[tuple[str, Mapping[str, object]]] = []
    entries = _entries(request)
    regular_paths = frozenset(
        entry.path.original
        for entry in entries
        if entry.kind is EntryKind.REGULAR and entry.content is not None
    )
    for entry in sorted(entries, key=lambda item: item.path.original.encode("utf-8")):
        path = entry.path.original
        if entry.kind is not EntryKind.REGULAR or entry.content is None:
            findings.append(
                _finding(
                    "FM-PATH",
                    path,
                    "$file",
                    "managed Markdown input is not a regular file",
                    "restore a regular UTF-8 Markdown file",
                )
            )
            continue
        try:
            parsed_metadata = parse_frontmatter(entry.content.decode("utf-8-sig"))
        except UnicodeDecodeError, FrontmatterParseError:
            findings.append(
                _finding(
                    "FM-PARSE",
                    path,
                    "$frontmatter",
                    "frontmatter is not valid UTF-8 YAML",
                    "repair the leading frontmatter block",
                )
            )
            continue
        if parsed_metadata is None:
            if required:
                findings.append(
                    _finding(
                        "FM-REQUIRED",
                        path,
                        "$frontmatter",
                        "frontmatter is required",
                        "add a schema-valid leading frontmatter block",
                    )
                )
            continue
        metadata = cast("dict[str, object]", parsed_metadata)
        documents.append((path, metadata))
        schema_errors = sorted(
            validator.iter_errors(cast(Any, metadata)),  # pyright: ignore[reportUnknownMemberType]
            key=lambda error: [str(part) for part in error.path],
        )
        for schema_error in schema_errors:
            identity = ".".join(str(part) for part in schema_error.path) or "(root)"
            findings.append(
                _finding(
                    "FM-SCHEMA",
                    path,
                    identity,
                    f"[{identity}] {schema_error.message}",
                    "compare the document with the selected package contract",
                )
            )
        findings.extend(_calendar_findings(path, metadata))
        document_id = metadata.get("id")
        doc_type = metadata.get("doc_type")
        if (
            not custom_schema
            and isinstance(document_id, str)
            and isinstance(doc_type, str)
            and doc_type in valid_doc_types
        ):
            for violation in validate_id(document_id, doc_type, valid_doc_types):
                findings.append(
                    _finding(
                        "FM-ID",
                        path,
                        "id",
                        f"[id] {violation}",
                        "run project-standards fix or repair the id manually",
                    )
                )
    references = config.get("references")
    reference_enabled = (
        not custom_schema
        and isinstance(references, Mapping)
        and cast("Mapping[str, object]", references).get("enabled") is True
    )
    if reference_enabled:
        findings.extend(_repository_findings(documents, regular_paths))
    findings.sort(
        key=lambda item: (
            item["path"].encode("utf-8"),
            item["code"],
            item["identity"].encode("utf-8"),
        )
    )
    return {"findings": findings}


def run_migrate(
    request: Mapping[str, object],
    _resources: Mapping[str, bytes],
) -> dict[str, object]:
    """Map the exact v4 YAML namespace and known installed artifacts to V2 state."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    legacy = _table(snapshots.get("legacy_config"), name="snapshots.legacy_config")
    markdown = _table(legacy.get("markdown"), name="legacy_config.markdown")
    frontmatter = _table(
        markdown.get("frontmatter"),
        name="legacy_config.markdown.frontmatter",
    )
    allowed = {
        "version",
        "schema",
        "required",
        "include",
        "exclude",
        "references",
        "workflow_mode",
    }
    config: dict[str, object] = {}
    recognized: list[str] = []
    for key in sorted(frontmatter):
        if key not in allowed:
            continue
        if key == "version":
            config["contract_version"] = frontmatter[key]
            recognized.append("/markdown/frontmatter/version")
        elif key == "schema":
            schema = frontmatter[key]
            if schema == "markdown-frontmatter":
                config["schema"] = "markdown-frontmatter"
            elif isinstance(schema, str):
                config["schema"] = "custom"
                config["schema_path"] = schema
            else:
                raise ValueError("legacy frontmatter schema must be a string")
            recognized.append("/markdown/frontmatter/schema")
        elif key == "references":
            references = _table(frontmatter[key], name="legacy frontmatter references")
            if "enabled" in references:
                config["references"] = {"enabled": references["enabled"]}
                recognized.append("/markdown/frontmatter/references/enabled")
        elif key == "exclude":
            exclusions = frontmatter[key]
            if not isinstance(exclusions, Sequence) or isinstance(exclusions, str | bytes):
                raise ValueError("legacy frontmatter exclude must be an array")
            values = cast("Sequence[object]", exclusions)
            if not all(isinstance(item, str) for item in values):
                raise ValueError("legacy frontmatter exclude entries must be strings")
            config[key] = list(dict.fromkeys(("**/*.template.md", *cast("Sequence[str]", values))))
            recognized.append("/markdown/frontmatter/exclude")
        else:
            config[key] = frontmatter[key]
            recognized.append(f"/markdown/frontmatter/{key}")

    raw_signatures = _table(
        snapshots.get("legacy_signatures"),
        name="snapshots.legacy_signatures",
    )
    claims: list[dict[str, object]] = []
    workflow_disposition = "preserve" if config.get("workflow_mode") == "local" else "remove"
    dispositions = {
        "legacy-workflow": (
            ".github/workflows/validate-markdown-frontmatter.yml",
            workflow_disposition,
        ),
        "legacy-skill": (".agents/skills/markdown-frontmatter/SKILL.md", "adopt"),
        "legacy-skill-script": (
            ".agents/skills/markdown-frontmatter/scripts/new-doc-id",
            "adopt",
        ),
    }
    for signature_id, (target, disposition) in dispositions.items():
        signature = raw_signatures.get(signature_id)
        if not isinstance(signature, Mapping):
            continue
        signature_table = cast("Mapping[str, object]", signature)
        observed = signature_table.get(target)
        if (
            not isinstance(observed, Mapping)
            or cast("Mapping[str, object]", observed).get("known") is not True
        ):
            continue
        digest = cast("Mapping[str, object]", observed).get("digest")
        if not isinstance(digest, str):
            raise ValueError("known legacy signature omitted its digest")
        claims.append(
            {
                "signature_id": signature_id,
                "target": target,
                "observed_digest": digest,
                "ownership": "managed",
                "disposition": disposition,
            }
        )
    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "markdown-frontmatter",
            "version": str(request.get("version")),
            "selector": "latest",
            "config": config,
            "recognized_settings": recognized,
        },
        "claims": claims,
        "findings": [],
    }
