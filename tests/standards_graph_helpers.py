from __future__ import annotations

from pathlib import Path


def write_standard(
    root: Path,
    standard_id: str,
    *,
    namespaces: list[str] | None = None,
    provides: list[str] | None = None,
    consumes_platform: list[str] | None = None,
    companions: list[str] | None = None,
    extends: list[str] | None = None,
    conflicts: list[str] | None = None,
    resources: dict[str, str] | None = None,
    relation_extras: dict[str, list[str]] | None = None,
    authorities: list[dict[str, object]] | None = None,
    providers: list[dict[str, object]] | None = None,
    adoption: str = "none",
    status: str = "active",
    supported_versions: list[str] | None = None,
    latest_version: str = "1.0",
    artifact_manifest: str | None = None,
    extra_toml: str = "",
) -> Path:
    bundle = root / "standards" / standard_id
    bundle.mkdir(parents=True)
    (bundle / "README.md").write_text(f"# {standard_id}\n", encoding="utf-8")
    resource_map = {"readme": "README.md", **(resources or {})}
    for rel_path in resource_map.values():
        target = bundle / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(f"# {rel_path}\n", encoding="utf-8")

    def _array(values: list[str] | None) -> str:
        return "[" + ", ".join(f'"{value}"' for value in (values or [])) + "]"

    text = f"""[standard]
id = "{standard_id}"
name = "{standard_id.title()}"
status = "{status}"
summary = "Example standard."
adoption = "{adoption}"

[versions]
supported = {_array(supported_versions or [latest_version])}
latest = "{latest_version}"

[config]
namespaces = {_array(namespaces)}

[capabilities]
provides = {_array(provides)}
consumes_platform = {_array(consumes_platform)}

[relations]
companions = {_array(companions)}
extends = {_array(extends)}
conflicts = {_array(conflicts)}
"""
    for key, value in (relation_extras or {}).items():
        text += f"{key} = {_array(value)}\n"
    text += """
[resources]
"""
    for key, value in resource_map.items():
        text += f'{key} = "{value}"\n'
    for authority in authorities or []:
        text += "\n[[authority]]\n"
        text += f'domain = "{authority["domain"]}"\n'
        text += f'target = "{authority["target"]}"\n'
        text += f'concern = "{authority["concern"]}"\n'
        text += f'owner = "{authority["owner"]}"\n'
        text += f"mutates = {str(authority['mutates']).lower()}\n"
    for provider in providers or []:
        text += "\n[[providers]]\n"
        text += f'operation = "{provider["operation"]}"\n'
        text += f'kind = "{provider["kind"]}"\n'
        if provider.get("entrypoint") is not None:
            text += f'entrypoint = "{provider["entrypoint"]}"\n'
        if provider.get("input_schema") is not None:
            text += f'input_schema = "{provider["input_schema"]}"\n'
        if provider.get("output_schema") is not None:
            text += f'output_schema = "{provider["output_schema"]}"\n'
        text += f"optional = {str(provider['optional']).lower()}\n"
    if artifact_manifest is not None:
        text += f'\n[artifacts]\nmanifest = "{artifact_manifest}"\n'
    text += extra_toml

    manifest = bundle / "standard.toml"
    manifest.write_text(text, encoding="utf-8")
    return bundle
