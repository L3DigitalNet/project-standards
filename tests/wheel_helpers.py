"""Install test-built pure-Python wheels without invoking package-manager shims."""

from pathlib import Path
from zipfile import ZipFile


def extract_pure_python_wheel(wheel: Path, target: Path) -> None:
    """Extract one pure-Python wheel into an isolated import target.

    Test wheels in this repository contain only importable package files and
    distribution metadata; wheels requiring install-scheme relocation are outside
    this helper's contract.
    """
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(wheel) as archive:
        archive.extractall(target)
