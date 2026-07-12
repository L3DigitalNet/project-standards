def render(
    _request: dict[str, object],
    _resources: dict[str, bytes],
) -> dict[str, object]:
    return {"content": "[alpha]\nenabled = true\n"}


def migrate(
    _request: dict[str, object],
    _resources: dict[str, bytes],
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "alpha",
            "version": "2.0",
            "selector": "latest",
            "config": {"extension_path": "config/alpha-options.toml"},
            "recognized_settings": ["/alpha/enabled"],
        },
        "claims": [
            {
                "signature_id": "legacy-alpha",
                "target": "legacy-alpha.md",
                "observed_digest": "sha256:c9e8af84d208648598d673f039dea59091a9141a6150c3a2efbeb458689937ca",
                "ownership": "consumer-owned",
                "disposition": "preserve",
            }
        ],
        "findings": [],
    }
