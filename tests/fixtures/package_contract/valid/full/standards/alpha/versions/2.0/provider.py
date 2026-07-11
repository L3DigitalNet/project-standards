def render(payload: dict[str, object]) -> dict[str, object]:
    return payload


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
            "config": {},
            "recognized_settings": ["/alpha"],
        },
        "claims": [],
        "findings": [],
    }
