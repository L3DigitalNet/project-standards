"""Bundled contract-version registry for the project standards.

The validator ships one tool release that bundles a known set of *contract
versions* per standard (the two-plane model — see meta/versioning.md and
docs/superpowers/specs/2026-06-06-per-standard-versioning-design.md). This module
is the sole reader of registry.json: it maps each bundled Frontmatter contract
version to its schema name, records which Frontmatter versions each ADR contract
version supports, and lists the known Python Tooling and Markdown Tooling label
versions. It performs no document validation itself — callers in
validate_frontmatter.py use it to resolve schemas by version and to enforce the
FM->ADR compatibility contract.

Kept separate from validate_frontmatter.py so the registry shape has one owner and
the validator's schema-validation core stays untouched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

# Same packaging trick as the bundled schema: a path relative to this module
# resolves identically from a source checkout and from a uv tool install wheel.
_REGISTRY_PATH = Path(__file__).parent / "schemas" / "registry.json"


class RegistryError(ValueError):
    """registry.json is missing or malformed, or a requested version is unknown.

    Surfaces as exit code 2 (operator/packaging error) at the CLI boundary,
    mirroring ConfigError and the schema-load errors.
    """


class Registry:
    """Resolved, typed view of registry.json."""

    def __init__(
        self,
        *,
        frontmatter_default: str,
        frontmatter_versions: dict[str, str],
        adr_default: str,
        adr_supports: dict[str, list[str]],
        python_tooling_default: str,
        python_tooling_versions: list[str],
        markdown_tooling_default: str,
        markdown_tooling_versions: list[str],
    ) -> None:
        self.frontmatter_default = frontmatter_default
        self.frontmatter_versions = frontmatter_versions
        self.adr_default = adr_default
        self.adr_supports = adr_supports
        self.python_tooling_default = python_tooling_default
        self.python_tooling_versions = python_tooling_versions
        self.markdown_tooling_default = markdown_tooling_default
        self.markdown_tooling_versions = markdown_tooling_versions

    def frontmatter_schema_name(self, version: str) -> str:
        """Bundled schema *name* for a Frontmatter contract version."""
        try:
            return self.frontmatter_versions[version]
        except KeyError as exc:
            known = ", ".join(sorted(self.frontmatter_versions))
            raise RegistryError(
                f"unknown frontmatter version {version!r}; bundled: {known}"
            ) from exc

    def adr_supported_frontmatter(self, version: str) -> list[str]:
        """Frontmatter versions an ADR contract version declares support for."""
        try:
            return self.adr_supports[version]
        except KeyError as exc:
            known = ", ".join(sorted(self.adr_supports))
            raise RegistryError(
                f"unknown adr version {version!r}; bundled: {known}"
            ) from exc

    def is_known_python_tooling(self, version: str) -> bool:
        return version in self.python_tooling_versions

    def is_known_markdown_tooling(self, version: str) -> bool:
        return version in self.markdown_tooling_versions


def _require_str_map(obj: Any, where: str) -> dict[str, str]:
    if not isinstance(obj, dict):
        raise RegistryError(f"registry {where} is not an object")
    out: dict[str, str] = {}
    for key, value in cast("dict[str, Any]", obj).items():
        if not isinstance(value, str):
            raise RegistryError(f"registry {where}.{key} is not a string")
        out[str(key)] = value
    return out


def load_registry(path: Path = _REGISTRY_PATH) -> Registry:
    """Read and validate registry.json into a Registry, or raise RegistryError."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot load registry {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RegistryError(f"registry {path} is not a JSON object")
    data = cast("dict[str, Any]", raw)

    fm = data.get("frontmatter")
    adr = data.get("adr")
    pt = data.get("python_tooling")
    mt = data.get("markdown_tooling")
    if (
        not isinstance(fm, dict)
        or not isinstance(adr, dict)
        or not isinstance(pt, dict)
        or not isinstance(mt, dict)
    ):
        raise RegistryError(
            f"registry {path} missing frontmatter/adr/python_tooling/markdown_tooling objects"
        )
    fm_d = cast("dict[str, Any]", fm)
    adr_d = cast("dict[str, Any]", adr)
    pt_d = cast("dict[str, Any]", pt)
    mt_d = cast("dict[str, Any]", mt)

    fm_default = fm_d.get("default")
    adr_default = adr_d.get("default")
    pt_default = pt_d.get("default")
    mt_default = mt_d.get("default")
    if (
        not isinstance(fm_default, str)
        or not isinstance(adr_default, str)
        or not isinstance(pt_default, str)
        or not isinstance(mt_default, str)
    ):
        raise RegistryError(f"registry {path} has a non-string default")

    fm_versions = _require_str_map(fm_d.get("versions"), "frontmatter.versions")

    adr_versions_raw = adr_d.get("versions")
    if not isinstance(adr_versions_raw, dict):
        raise RegistryError("registry adr.versions is not an object")
    adr_supports: dict[str, list[str]] = {}
    for key, value in cast("dict[str, Any]", adr_versions_raw).items():
        if not isinstance(value, dict):
            raise RegistryError(f"registry adr.versions.{key} is not an object")
        supports = cast("dict[str, Any]", value).get("supports_frontmatter")
        if not isinstance(supports, list):
            raise RegistryError(
                f"registry adr.versions.{key}.supports_frontmatter is not a list"
            )
        adr_supports[str(key)] = [str(v) for v in cast("list[Any]", supports)]

    pt_versions_raw = pt_d.get("versions")
    if not isinstance(pt_versions_raw, list):
        raise RegistryError("registry python_tooling.versions is not a list")
    pt_versions = [str(v) for v in cast("list[Any]", pt_versions_raw)]

    mt_versions_raw = mt_d.get("versions")
    if not isinstance(mt_versions_raw, list):
        raise RegistryError("registry markdown_tooling.versions is not a list")
    mt_versions = [str(v) for v in cast("list[Any]", mt_versions_raw)]

    return Registry(
        frontmatter_default=fm_default,
        frontmatter_versions=fm_versions,
        adr_default=adr_default,
        adr_supports=adr_supports,
        python_tooling_default=pt_default,
        python_tooling_versions=pt_versions,
        markdown_tooling_default=mt_default,
        markdown_tooling_versions=mt_versions,
    )
