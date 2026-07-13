"""Version-selected Project Specification inspection and authoring providers."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping, Sequence
from datetime import date
from typing import cast

from project_standards.specs.commands.extract import extract_slice
from project_standards.specs.commands.lint import lint_document
from project_standards.specs.commands.new import NewOptions, scaffold
from project_standards.specs.commands.next_id import next_free_id
from project_standards.specs.commands.upgrade import check_upgradeable, upgrade_text
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import SpecParseError, parse_document
from project_standards.specs.model import Finding, Registry
from project_standards.specs.registry import TIER_FILES, registry_from_templates

_SELF_HOST_WORKFLOW_DIGESTS = frozenset(
    {
        "sha256:2e38ae698e0a45f9afdde997ce2fa58c827f4bdb518e108ca9d0a1f22f278cc8",
        "sha256:0be22314a96e41f9861897e75baf7bfcf35b2f3ae51870db0f9cc6e982fa5525",
    }
)


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _sequence(value: object, *, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"{name} must be an array")
    return cast("Sequence[object]", value)


def _config(request: Mapping[str, object]) -> Mapping[str, object]:
    return _table(request.get("config"), name="config")


def _templates(resources: Mapping[str, bytes]) -> dict[str, str]:
    return {
        filename: resources[f"template-{profile}"].decode("utf-8")
        for profile, filename in TIER_FILES.items()
    }


def _registry(resources: Mapping[str, bytes]) -> Registry:
    return registry_from_templates(_templates(resources))


def _prefixes(config: Mapping[str, object], registry: Registry) -> frozenset[str]:
    raw = _sequence(config.get("reference_prefixes"), name="config.reference_prefixes")
    prefixes: set[str] = set()
    canonical = set(registry.prefix_defined_in)
    for value in raw:
        if not isinstance(value, str) or not value.isalpha() or not value.isupper():
            raise ValueError(
                f"spec.reference_prefixes entry {value!r} must be 1-4 uppercase letters"
            )
        if not 1 <= len(value) <= 4:
            raise ValueError(
                f"spec.reference_prefixes entry {value!r} must be 1-4 uppercase letters"
            )
        if value in canonical:
            raise ValueError(
                f"spec.reference_prefixes entry {value!r} is a canonical spec-local prefix; "
                "listing it would disable validation of your own IDs"
            )
        prefixes.add(value)
    return frozenset(prefixes)


def _decode_document(raw: object) -> tuple[str, str]:
    document = _table(raw, name="document")
    path = document.get("path")
    encoded = document.get("content_base64")
    if not isinstance(path, str) or document.get("kind") != "regular":
        raise ValueError("document snapshot must identify a regular file")
    if not isinstance(encoded, str):
        raise ValueError("document snapshot omitted content")
    try:
        return path, base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("document snapshot is not canonical UTF-8 base64") from exc


def _documents(request: Mapping[str, object]) -> Sequence[object]:
    snapshots = _table(request.get("snapshots"), name="snapshots")
    return _sequence(snapshots.get("documents"), name="snapshots.documents")


def _finding(path: str, finding: Finding) -> dict[str, object]:
    code = finding.code
    return {
        "code": code,
        "severity": finding.severity,
        "path": path,
        "identity": finding.locus or code.lower(),
        "message": finding.message,
        "hint": "repair the document against the selected Project Specification template",
        "line": finding.line,
        "locus": finding.locus,
    }


def _run_findings(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
    *,
    lint: bool,
) -> dict[str, object]:
    config = _config(request)
    registry = _registry(resources)
    prefixes = _prefixes(config, registry)
    findings: list[dict[str, object]] = []
    for raw in _documents(request):
        try:
            path, text = _decode_document(raw)
            document = parse_document(path, text, prefixes)
        except (ValueError, SpecParseError) as exc:
            path = "<snapshot>"
            if isinstance(raw, Mapping):
                raw_table = cast("Mapping[str, object]", raw)
                if isinstance(raw_table.get("path"), str):
                    path = cast(str, raw_table.get("path"))
            findings.append(
                {
                    "code": "SV-PARSE",
                    "severity": "error",
                    "path": path,
                    "identity": "document",
                    "message": str(exc),
                    "hint": "repair the document encoding and frontmatter",
                    "line": None,
                    "locus": None,
                }
            )
            continue
        raw_findings = (
            lint_document(document, registry) if lint else validate_document(document, registry)
        )
        findings.extend(_finding(path, finding) for finding in raw_findings)
    findings.sort(key=lambda item: (str(item["path"]).encode(), str(item["identity"]).encode()))
    return {"findings": findings}


def run_validate(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Validate immutable document snapshots against payload templates."""
    return _run_findings(request, resources, lint=False)


def run_lint(request: Mapping[str, object], resources: Mapping[str, bytes]) -> dict[str, object]:
    """Lint immutable document snapshots against payload templates."""
    return _run_findings(request, resources, lint=True)


def run_extract(
    request: Mapping[str, object], _resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Extract one requested slice from an immutable document snapshot."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    path, text = _decode_document(snapshots.get("document"))
    selector = snapshots.get("selector")
    if not isinstance(selector, str):
        raise ValueError("extract snapshot requires a selector")
    result = extract_slice(parse_document(path, text), selector)
    return {
        "content": result.markdown or "",
        "file": path,
        "selector": result.selector,
        "kind": result.kind,
        "found": result.found,
        "markdown": result.markdown,
    }


def run_id_next(request: Mapping[str, object], resources: Mapping[str, bytes]) -> dict[str, str]:
    """Return the next ID for one selected document prefix."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    path, text = _decode_document(snapshots.get("document"))
    prefix = snapshots.get("prefix")
    if not isinstance(prefix, str):
        raise ValueError("id-next snapshot requires a prefix")
    registry = _registry(resources)
    document = parse_document(path, text, _prefixes(_config(request), registry))
    next_id = next_free_id(document, registry, prefix)
    return {
        "content": next_id,
        "file": path,
        "prefix": prefix.rstrip("-").upper(),
        "next_id": next_id,
    }


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _mutation(
    request: Mapping[str, object],
    authoring: Mapping[str, object],
    content: str,
) -> dict[str, object]:
    target = authoring.get("target")
    precondition = authoring.get("precondition_digest")
    kind = authoring.get("kind")
    if not isinstance(target, str) or not isinstance(precondition, str):
        raise ValueError("authoring snapshot omitted target precondition")
    if kind not in {"missing", "regular"}:
        raise ValueError("authoring target must be missing or regular")
    encoded = content.encode()
    action: dict[str, object] = {
        "kind": "create" if kind == "missing" else "update",
        "target": target,
        "adapter": "whole-file",
        "scope": "$file",
        "summary": f"wrote {target}",
        "precondition_digest": precondition,
        "content_digest": _digest(encoded),
        "content_base64": base64.b64encode(encoded).decode("ascii"),
    }
    mode = authoring.get("mode")
    if isinstance(mode, str):
        action["mode"] = mode
    elif mode is not None:
        raise ValueError("authoring snapshot mode is invalid")
    return {
        "schema_version": "1.0",
        "standard_id": "project-spec",
        "version": str(request.get("version")),
        "actions": [action],
    }


def _scaffold_content(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
    authoring: Mapping[str, object],
) -> str:
    config = _config(request)
    profile = authoring.get("profile", config.get("default_profile"))
    spec_id = authoring.get("spec_id")
    today = authoring.get("today")
    if profile not in TIER_FILES or not isinstance(spec_id, str) or not isinstance(today, str):
        raise ValueError("scaffold snapshot omitted profile, spec_id, or date")
    options = NewOptions(
        profile=cast(str, profile),
        spec_id=spec_id,
        title=cast(str | None, authoring.get("title")),
        owner=cast(str | None, authoring.get("owner")),
        implementer=cast(str | None, authoring.get("implementer")),
    )
    template = resources[f"template-{profile}"].decode("utf-8")
    content = scaffold(template, options, today=date.fromisoformat(today))
    registry = _registry(resources)
    findings = validate_document(
        parse_document("<scaffold>", content, _prefixes(config, registry)),
        registry,
    )
    if findings:
        raise ValueError("scaffold failed selected-package validation")
    return content


def run_scaffold(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Return a typed plan for one new specification document."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    authoring = _table(snapshots.get("authoring"), name="snapshots.authoring")
    return _mutation(request, authoring, _scaffold_content(request, resources, authoring))


def run_render_preview(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, str]:
    """Render one authoring preview without requiring or returning a live target."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    preview = _table(snapshots.get("preview"), name="snapshots.preview")
    operation = preview.get("operation")
    if operation == "scaffold":
        content = _scaffold_content(request, resources, preview)
    elif operation == "upgrade":
        content = _upgrade_content(request, resources, preview)
    else:
        raise ValueError("preview operation is not supported")
    return {"content": content}


def _upgrade_content(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
    authoring: Mapping[str, object],
) -> str:
    encoded = authoring.get("content_base64")
    target_profile = authoring.get("target_profile")
    if not isinstance(encoded, str) or target_profile not in TIER_FILES:
        raise ValueError("upgrade snapshot omitted content or target profile")
    source = base64.b64decode(encoded, validate=True).decode("utf-8")
    registry = _registry(resources)
    prefixes = _prefixes(_config(request), registry)
    document = parse_document(str(authoring.get("target")), source, prefixes)
    source_findings = validate_document(document, registry)
    if source_findings:
        raise ValueError("upgrade source failed selected-package validation")
    source_profile = document.profile
    if source_profile not in TIER_FILES:
        raise ValueError("upgrade source has no recognized profile")
    order = {"light": 0, "standard": 1, "full": 2}
    if order[source_profile] >= order[cast(str, target_profile)]:
        raise ValueError("upgrade target must be a higher additive profile")
    source_template = resources[f"template-{source_profile}"].decode("utf-8")
    if deviation := check_upgradeable(source, source_template):
        raise ValueError(deviation)
    target_template = resources[f"template-{target_profile}"].decode("utf-8")
    content = upgrade_text(source, target_template, target_tier=cast(str, target_profile))
    findings = validate_document(parse_document("<upgrade>", content, prefixes), registry)
    if findings:
        raise ValueError("upgraded document failed selected-package validation")
    return content


def run_upgrade(request: Mapping[str, object], resources: Mapping[str, bytes]) -> dict[str, object]:
    """Return a typed additive tier-upgrade plan."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    authoring = _table(snapshots.get("authoring"), name="snapshots.authoring")
    return _mutation(request, authoring, _upgrade_content(request, resources, authoring))


def run_render_workflow(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, str]:
    """Render the stable caller with a config-selected job gate."""
    if _config(request).get("workflow_mode") == "self-hosted":
        return {"content": resources["self-host-workflow"].decode()}
    enabled = "true" if _config(request).get("ci") is True else "false"
    return {
        "content": (
            "name: Validate project specs\n\n"
            "on:\n  pull_request:\n  push:\n    branches:\n      - main\n  workflow_dispatch:\n\n"
            "jobs:\n  validate-specs:\n"
            f"    if: ${{{{ {enabled} }}}}\n"
            "    uses: L3DigitalNet/project-standards/.github/workflows/validate-specs.yml@v5\n"
            '    with:\n      config-path: ".standards/config.toml"\n'
            '      standards-ref: "v5"\n      strict-lint: true\n'
        )
    }


def run_migrate(
    request: Mapping[str, object], _resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Map exact V4 spec settings and preserve ambiguous exclusions."""
    snapshots = _table(request.get("snapshots"), name="snapshots")
    legacy = _table(snapshots.get("legacy_config"), name="snapshots.legacy_config")
    spec = _table(legacy.get("spec"), name="legacy_config.spec")
    config: dict[str, object] = {}
    recognized: list[str] = []
    mapping = {
        "version": "contract_version",
        "include": "include_patterns",
        "reference_prefixes": "reference_prefixes",
    }
    for legacy_key, current_key in mapping.items():
        if legacy_key in spec:
            value = spec[legacy_key]
            if legacy_key == "version" and value == "1.0":
                value = "1.1"
            if legacy_key == "include" and isinstance(value, str):
                value = [value]
            config[current_key] = value
            recognized.append(f"/spec/{legacy_key}")
    findings: list[dict[str, str]] = []
    if "exclude" in spec:
        if spec.get("exclude") in (None, [], ()):
            recognized.append("/spec/exclude")
        else:
            findings.append(
                {
                    "code": "SPEC-LEGACY-EXCLUDE",
                    "severity": "error",
                    "path": ".project-standards.yml",
                    "identity": "legacy-exclude",
                }
            )
    claims: list[dict[str, object]] = []
    raw_signatures = snapshots.get("legacy_signatures")
    if isinstance(raw_signatures, Mapping):
        signatures = cast("Mapping[str, object]", raw_signatures)
        for signature_id, target, ownership, disposition in (
            (
                "legacy-workflow",
                ".github/workflows/validate-specs.yml",
                "managed",
                "adopt",
            ),
        ):
            raw_signature = signatures.get(signature_id)
            if not isinstance(raw_signature, Mapping):
                continue
            signature = cast("Mapping[str, object]", raw_signature)
            raw_state = signature.get(target)
            if not isinstance(raw_state, Mapping):
                continue
            state = cast("Mapping[str, object]", raw_state)
            if state.get("known") is not True:
                continue
            digest = state.get("digest")
            if isinstance(digest, str):
                if digest in _SELF_HOST_WORKFLOW_DIGESTS:
                    config["workflow_mode"] = "self-hosted"
                claims.append(
                    {
                        "signature_id": signature_id,
                        "target": target,
                        "observed_digest": digest,
                        "ownership": ownership,
                        "disposition": disposition,
                    }
                )
    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "project-spec",
            "version": str(request.get("version")),
            "selector": "latest",
            "config": config,
            "recognized_settings": sorted(recognized),
        },
        "claims": claims,
        "findings": findings,
    }
