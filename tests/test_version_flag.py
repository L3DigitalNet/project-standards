"""--version contract for every installed command (spec §8, codex SA-002)."""

from __future__ import annotations

from types import ModuleType

import pytest

from project_standards import (
    cli,
    format_frontmatter,
    sync_standards_include,
    sync_vscode_colors,
    validate_frontmatter,
    validate_id,
    validate_references,
)
from project_standards._version import package_version


def test_package_version_is_nonempty_pep440ish() -> None:
    v = package_version()
    assert v and v[0].isdigit()


def test_cli_version_flag_prints_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--version"]) == 0
    out = capsys.readouterr().out
    assert out.strip() == f"project-standards {package_version()}"


@pytest.mark.parametrize(
    "module",
    [validate_frontmatter, validate_id, format_frontmatter, validate_references],
)
def test_argparse_mains_version_flag(
    module: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # In-process prog varies with sys.argv[0]; the EXACT "<script> <version>" contract
    # is asserted against the installed wrappers in tests/test_installed_wrappers.py
    # (codex CR-004) — here we only prove the flag exists and exits 0.
    with pytest.raises(SystemExit) as exc:
        module.main(["--version"])
    assert exc.value.code == 0
    assert package_version() in capsys.readouterr().out


@pytest.mark.parametrize("module", [sync_vscode_colors, sync_standards_include])
def test_sync_mains_version_flag(
    module: ModuleType, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", [module.__name__, "--version"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 0
    assert package_version() in capsys.readouterr().out


@pytest.mark.parametrize("module", [sync_vscode_colors, sync_standards_include])
@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_sync_mains_help_flag(
    module: ModuleType,
    flag: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # These mains parse raw positionals with no option library, so --help/-h must be
    # intercepted before the first argv slot is read as <standards-file> — otherwise
    # it is treated as a filename and the command exits 1 with "not found".
    monkeypatch.setattr("sys.argv", [module.__name__, flag])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 0
    assert "Usage:" in capsys.readouterr().out
