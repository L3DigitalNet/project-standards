"""Read the per-bundle `adopt.toml` manifests packaged under `bundles/`.

Same packaging trick as the bundled schema/registry: paths are resolved relative to
this module's location, so they work identically from a source checkout and a wheel.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_standards.adopt.errors import ManifestError

# bundles/ sits beside this package's schemas/ — one level up from adopt/.
# Public because the engine imports it as the shared default for `bundles_dir`.
BUNDLES_DIR = Path(__file__).resolve().parent.parent / "bundles"

_KNOWN_KINDS = frozenset({"file", "workflow-caller", "fragment"})


@dataclass(frozen=True)
class Artifact:
    """One artifact a standard contributes. Exactly one of (source, shared) is set."""

    kind: str
    owner: bool
    source: str | None  # path relative to the bundle dir (owned artifact)
    shared: str | None  # path relative to bundles/ (shared artifact, e.g. "_shared/editorconfig")
    dest: str | None  # file/workflow-caller destination, relative to --dest
    target: str | None  # fragment target, relative to --dest


@dataclass(frozen=True)
class Manifest:
    id: str
    artifacts: tuple[Artifact, ...]


def available_standards(bundles_dir: Path = BUNDLES_DIR) -> list[str]:
    """Sorted ids of bundles that ship an adopt.toml (excludes `_shared`)."""
    if not bundles_dir.is_dir():
        raise ManifestError(f"bundles directory missing: {bundles_dir}")
    out: list[str] = []
    for child in sorted(bundles_dir.iterdir()):
        if child.name == "_shared":
            continue
        if (child / "adopt.toml").is_file():
            out.append(child.name)
    return out


def load_manifest(standard_id: str, bundles_dir: Path = BUNDLES_DIR) -> Manifest:
    path = bundles_dir / standard_id / "adopt.toml"
    if not path.is_file():
        raise ManifestError(f"no manifest for standard {standard_id!r} at {path}")
    try:
        raw: Any = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError(f"manifest {path} is not a TOML table")
    data = cast("dict[str, Any]", raw)

    standard = data.get("standard")
    if not isinstance(standard, dict) or cast("dict[str, Any]", standard).get("id") != standard_id:
        raise ManifestError(f"manifest {path} missing/mismatched [standard].id")

    artifacts_raw = data.get("artifact", [])
    if not isinstance(artifacts_raw, list):
        raise ManifestError(f"manifest {path} [[artifact]] is not a list")

    artifacts: list[Artifact] = []
    for i, item in enumerate(cast("list[Any]", artifacts_raw)):
        if not isinstance(item, dict):
            raise ManifestError(f"manifest {path} artifact {i} is not a table")
        a = cast("dict[str, Any]", item)
        kind = a.get("kind")
        if kind not in _KNOWN_KINDS:
            raise ManifestError(f"manifest {path} artifact {i} has unknown kind {kind!r}")
        for fld in ("source", "shared", "dest", "target"):
            val = a.get(fld)
            if val is not None and not isinstance(val, str):
                raise ManifestError(
                    f"manifest {path} artifact {i} field {fld!r} must be a string, "
                    f"got {type(val).__name__}"
                )
        source = a.get("source")
        shared = a.get("shared")
        if (source is None) == (shared is None):
            raise ManifestError(
                f"manifest {path} artifact {i} must set exactly one of source/shared"
            )
        dest = a.get("dest")
        target = a.get("target")
        if kind == "fragment" and target is None:
            raise ManifestError(f"manifest {path} fragment artifact {i} needs a target")
        if kind != "fragment" and dest is None:
            raise ManifestError(f"manifest {path} {kind} artifact {i} needs a dest")
        artifacts.append(
            Artifact(
                kind=cast("str", kind),
                owner=bool(a.get("owner", False)),
                source=cast("str | None", source),
                shared=cast("str | None", shared),
                dest=cast("str | None", dest),
                target=cast("str | None", target),
            )
        )
    return Manifest(id=standard_id, artifacts=tuple(artifacts))
