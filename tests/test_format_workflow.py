from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "format.yml"
_ROOT = _WF.parents[2]


# YAML parses the top-level `on:` key as the boolean True (the "Norway problem"),
# so the mapping is genuinely not str-keyed; dict[Any, Any] is the honest type and
# keeps basedpyright strict happy when indexing with True.
def _load() -> dict[Any, Any]:
    return cast("dict[Any, Any]", yaml.safe_load(_WF.read_text(encoding="utf-8")))


def _check_script() -> str:
    steps = _load()["jobs"]["prettier"]["steps"]
    step = next(item for item in steps if item["name"] == "Check formatting (Prettier)")
    return str(step["run"])


def _run_prettier_step(
    repo: Path,
    *,
    globs: str,
    exclusions: str = "",
) -> subprocess.CompletedProcess[str]:
    (repo / "node_modules").symlink_to(_ROOT / "node_modules", target_is_directory=True)
    environment = os.environ.copy()
    environment.update(
        {
            "FORMAT_GLOBS": globs,
            "FORMAT_EXCLUSIONS": exclusions,
            "npm_config_offline": "true",
        }
    )
    return subprocess.run(
        ["bash", "-c", _check_script()],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_workflow_is_reusable_with_boolean_prettier_input() -> None:
    data = _load()
    call = data[True]["workflow_call"]  # PyYAML parses the `on:` key as boolean True
    inp = call["inputs"]["prettier"]
    assert inp["type"] == "boolean"
    assert inp["default"] is True


def test_workflow_exposes_backward_compatible_scope_inputs() -> None:
    inputs = _load()[True]["workflow_call"]["inputs"]

    assert inputs["globs"] == {
        "description": "Newline-delimited paths or globs checked by Prettier.",
        "required": False,
        "type": "string",
        "default": ".",
    }
    assert inputs["exclusions"] == {
        "description": "Newline-delimited Prettier ignore patterns.",
        "required": False,
        "type": "string",
        "default": "",
    }


def test_still_dual_role_direct_triggers_present() -> None:
    on = _load()[True]
    assert "push" in on and "pull_request" in on and "workflow_call" in on


def test_optout_is_job_level_and_coercion_safe() -> None:
    job = _load()["jobs"]["prettier"]
    # Job-level `if:` (SA-NEW-003) using the string-safe form (SA-001).
    assert job["if"].strip() == "${{ format('{0}', inputs.prettier) != 'false' }}"


def test_prettier_check_uses_safe_arrays_and_pin_matches_package_json() -> None:
    pkg: dict[str, Any] = json.loads((_WF.parent.parent.parent / "package.json").read_text("utf-8"))
    pin = pkg["devDependencies"]["prettier"]  # SSOT for the pin (no hardcoded duplicate)
    steps = _load()["jobs"]["prettier"]["steps"]
    check = next(step for step in steps if step["name"] == "Check formatting (Prettier)")
    script = str(check["run"])

    assert check["env"] == {
        "FORMAT_GLOBS": "${{ inputs.globs || '.' }}",
        "FORMAT_EXCLUSIONS": "${{ inputs.exclusions || '' }}",
    }
    assert f"npx --yes prettier@{pin} --check" in script
    assert '"${globs[@]}"' in script
    assert '"${ignore_args[@]}"' in script
    assert "--no-error-on-unmatched-pattern" in script
    assert ".gitignore" in script
    assert ".prettierignore" in script
    assert "eval" not in script
    assert "${{ inputs." not in script
    assert not any("npm ci" in str(step.get("run", "")) for step in steps)


def test_configured_exclusion_is_anchored_to_repository_root(tmp_path: Path) -> None:
    generated = tmp_path / "generated/bad.json"
    generated.parent.mkdir()
    generated.write_text('{"bad":1}', encoding="utf-8")
    (tmp_path / "keep.json").write_text('{ "ok": true }\n', encoding="utf-8")

    result = _run_prettier_step(
        tmp_path,
        globs="**/*.json\ngenerated/**/*.json",
        exclusions="generated/**",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not tuple(tmp_path.glob(".project-standards-prettier-ignore.*"))


def test_gitignore_remains_a_separate_prettier_ignore_source(tmp_path: Path) -> None:
    ignored = tmp_path / "ignored/bad.json"
    ignored.parent.mkdir()
    ignored.write_text('{"bad":1}', encoding="utf-8")
    (tmp_path / "keep.json").write_text('{ "ok": true }\n', encoding="utf-8")
    (tmp_path / ".gitignore").write_text("ignored/**\n", encoding="utf-8")

    result = _run_prettier_step(tmp_path, globs="**/*.json")

    assert result.returncode == 0, result.stdout + result.stderr


def test_prettierignore_without_terminal_lf_stays_separate_from_exclusions(
    tmp_path: Path,
) -> None:
    ignored = tmp_path / "ignored/bad.json"
    ignored.parent.mkdir()
    ignored.write_text('{"bad":1}', encoding="utf-8")
    generated = tmp_path / "generated/bad.json"
    generated.parent.mkdir()
    generated.write_text('{"bad":1}', encoding="utf-8")
    (tmp_path / "keep.json").write_text('{ "ok": true }\n', encoding="utf-8")
    (tmp_path / ".prettierignore").write_text("ignored/**", encoding="utf-8")

    result = _run_prettier_step(
        tmp_path,
        globs="**/*.json",
        exclusions="generated/**",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_configured_file_types_do_not_fail_prettier(tmp_path: Path) -> None:
    (tmp_path / "keep.json").write_text('{ "ok": true }\n', encoding="utf-8")

    result = _run_prettier_step(tmp_path, globs="**/*.json\n**/*.yaml")

    assert result.returncode == 0, result.stdout + result.stderr


def test_trailing_space_include_is_rejected_before_prettier(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text('{"bad":1}', encoding="utf-8")

    result = _run_prettier_step(tmp_path, globs="**/*.json ")

    assert result.returncode == 2
    assert "format glob must not end in whitespace" in result.stderr
    assert "All matched files use Prettier code style" not in result.stdout


def test_trailing_space_exclusion_is_rejected_as_ineffective(tmp_path: Path) -> None:
    generated = tmp_path / "generated/bad.json"
    generated.parent.mkdir()
    generated.write_text('{"bad":1}', encoding="utf-8")

    result = _run_prettier_step(
        tmp_path,
        globs="**/*.json",
        exclusions="generated/** ",
    )

    assert result.returncode == 2
    assert "format exclusion must not end in whitespace" in result.stderr
    assert "generated/bad.json" not in result.stderr


@pytest.mark.parametrize(
    "input_value,expected_run",
    [
        (None, True),  # direct push/PR run: inputs context empty -> runs
        (True, True),  # reusable caller prettier: true -> runs
        (False, False),  # reusable caller prettier: false -> job skipped
    ],
)
def test_optout_truth_table(input_value: object, expected_run: bool) -> None:
    # Model GitHub's `format('{0}', x) != 'false'`: None -> '' , bool -> 'true'/'false'.
    rendered = "" if input_value is None else str(input_value).lower()
    runs = rendered != "false"
    assert runs is expected_run
