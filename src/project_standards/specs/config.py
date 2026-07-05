"""Read the `spec:` config block and resolve target files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from project_standards.validate_frontmatter import ConfigError, collect_paths


class DiscoveryError(ConfigError):
    """No spec source resolved any file; callers should treat this as exit 2."""


@dataclass(frozen=True)
class SpecConfig:
    include: list[str]
    exclude: list[str]
    present: bool


def _str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        raw = cast("list[object]", value)
        if all(isinstance(item, str) for item in raw):
            return cast("list[str]", raw)
    raise ConfigError("spec.include/spec.exclude must be strings or lists of strings")


def load_spec_config(path: Path) -> SpecConfig:
    """Load the optional project-spec discovery block from a config file."""
    include: list[str] = []
    exclude: list[str] = []
    present = False
    if path.exists():
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(f"cannot read config {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ConfigError(f"cannot parse config {path}: {exc}") from exc
        if isinstance(raw, dict):
            block = cast("dict[str, Any]", raw).get("spec")
            if isinstance(block, dict):
                present = True
                b = cast("dict[str, Any]", block)
                include = _str_list(b.get("include"))
                exclude = _str_list(b.get("exclude"))
    return SpecConfig(include=include, exclude=exclude, present=present)


def collect_spec_paths(explicit: list[Path], cfg: SpecConfig) -> list[Path]:
    """Resolve explicit paths or config-driven globs without a whole-repo fallback."""
    if explicit:
        missing = [p for p in explicit if not p.is_file()]
        if missing:
            raise ConfigError("no such file: " + ", ".join(str(p) for p in missing))
        return sorted(explicit)
    if not cfg.include:
        raise DiscoveryError(
            "no `spec:` config block and no paths given"
            if not cfg.present
            else "`spec:` block has no include globs"
        )
    paths = collect_paths([], None, cfg.include, cfg.exclude)
    if not paths:
        raise DiscoveryError("spec discovery matched no files")
    return paths
