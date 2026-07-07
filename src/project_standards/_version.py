"""Shared --version support for every installed console script (spec §8).

One helper, one distribution name: all seven [project.scripts] wrappers report the
same package version, satisfying the CLI Documentation Standard's Script-tier MUST.
"""

from __future__ import annotations

from importlib.metadata import version as _dist_version


def package_version() -> str:
    return _dist_version("project-standards")
